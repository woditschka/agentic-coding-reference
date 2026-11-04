"""Read the ledger as typed lines and answer the questions every reader shares.

A leaf over handoff.records and handoff.schema: the typed line, the latest-of query, and the review
cycle arithmetic the router decides on and the board displays.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from typing import Any, TypeVar

from .records import (
    GRADER,
    HUMAN,
    PLAN_ENGINE,
    SUBSTANTIVE_CLASSES,
    BuildFailure,
    BuildPass,
    ConsultationRequest,
    ConsultationResponse,
    DesignBlock,
    DispatchStart,
    HandoffRecord,
    IntakeDecision,
    PrdEntry,
    ReviewFeedback,
    UnknownRecord,
    parse_record,
)
from .schema import LogEntry

# Authors that never run as a dispatch: the engine, the human, and the terminal grader.
DISPATCH_EXEMPT = frozenset({PLAN_ENGINE, HUMAN, GRADER})
APPROVED = "approved"
TRUNCATION_TAG = "truncation"

_RecordT = TypeVar("_RecordT", bound=HandoffRecord)


@dataclass(frozen=True, slots=True)
class Entry:
    """One ledger line: its number, its raw object, and its typed record."""

    no: int
    raw: dict[str, Any]
    record: HandoffRecord

    @property
    def author(self) -> object:
        """Return the author, falling back to the raw value for an unknown type."""
        record = self.record
        return (
            self.raw.get("author")
            if isinstance(record, UnknownRecord)
            else record.author
        )

    @property
    def req_id(self) -> object:
        """Return the raw req_id value."""
        return self.raw.get("req_id")

    @property
    def type_name(self) -> object:
        """Return the raw type value."""
        return self.raw.get("type")

    @property
    def ts(self) -> object:
        """Return the raw ts value."""
        return self.raw.get("ts")


def typed_log(entries: Iterable[LogEntry]) -> tuple[Entry, ...]:
    """Lift every parsed log line into a typed entry."""
    return tuple(Entry(no, raw, parse_record(raw)) for no, raw in entries)


def cycle_round(
    records: Sequence[Entry], start: int, build_pass_line: int, roster: Sequence[str]
) -> int:
    """Return the current pass's round: one plus the earlier passes with substantive dissent."""
    windows = pass_windows(records, start, build_pass_line, roster)
    return 1 + sum(1 for window in windows if has_substantive_dissent(window))


def pass_windows(
    records: Sequence[Entry], start: int, build_pass_line: int, roster: Sequence[str]
) -> list[dict[object, ReviewFeedback]]:
    """Return the latest feedback per roster reviewer for each completed pass of the cycle."""
    pass_lines = [
        entry.no
        for entry in records
        if isinstance(entry.record, BuildPass) and start < entry.no <= build_pass_line
    ]
    return [
        _roster_feedback_between(records, first, last, roster)
        for first, last in pairwise(pass_lines)
    ]


def _roster_feedback_between(
    records: Sequence[Entry], first: int, last: int, roster: Sequence[str]
) -> dict[object, ReviewFeedback]:
    """Return the latest feedback per roster reviewer strictly between two lines."""
    window: dict[object, ReviewFeedback] = {}
    for entry in records:
        if (
            first < entry.no < last
            and isinstance(entry.record, ReviewFeedback)
            and entry.author in roster
        ):
            window[entry.author] = entry.record
    return window


def cycle_start(records: Sequence[Entry]) -> int:
    """Return the line the slice's current review cycle counts from, or 0.

    A design-block that supersedes an earlier one starts a cycle; so does a
    prd-entry that opens a later slice of a split, whose review rounds are
    its own and never inherit the earlier slice's dissent.
    """
    by_line = {entry.no: entry for entry in records}
    start, seen_index = 0, 1
    for entry in records:
        if superseded_design_block(entry, by_line) is not None:
            start = entry.no
            continue
        index = _slice_index(entry.record)
        if index is not None and index > seen_index:
            # A new later slice opens; its fix-round repeat does not.
            start, seen_index = entry.no, index
    return start


def _slice_index(record: HandoffRecord) -> int | None:
    """Return a prd-entry's slice_of index, or None when it carries none."""
    if not isinstance(record, PrdEntry) or record.slice_of is None:
        return None
    index = record.slice_of.index
    if isinstance(index, bool) or not isinstance(index, int):
        return None
    return index


def superseded_design_block(entry: Entry, by_line: Mapping[int, Entry]) -> Entry | None:
    """Return the earlier design-block a design-block validly supersedes, or None."""
    if not isinstance(entry.record, DesignBlock):
        return None
    pointer = entry.record.supersedes_record_at
    # bool is excluded: True passes isinstance(int).
    if not isinstance(pointer, int) or isinstance(pointer, bool) or pointer >= entry.no:
        return None
    target = by_line.get(pointer)
    if target is None or not isinstance(target.record, DesignBlock):
        return None
    return target


def has_substantive_dissent(feedback: Mapping[object, ReviewFeedback]) -> bool:
    """Return whether any feedback in a pass window dissents substantively."""
    return any(is_substantive_dissent(record) for record in feedback.values())


def is_substantive_dissent(feedback: ReviewFeedback) -> bool:
    """Return whether one feedback dissents with a finding other than a truncation checkpoint."""
    return feedback.verdict != APPROVED and any(
        finding.tag != TRUNCATION_TAG for finding in feedback.findings
    )


def latest_of(
    entries: Iterable[Entry], cls: type[_RecordT]
) -> tuple[Entry, _RecordT] | None:
    """Return the latest (entry, record) whose record is a `cls`, or None."""
    found: tuple[Entry, _RecordT] | None = None
    for entry in entries:
        if isinstance(entry.record, cls):
            found = (entry, entry.record)
    return found


# --- dispatch and recovery arithmetic -----------------------------------------


def silent_starts(records: Sequence[Entry], after_line: int, author: object) -> int:
    """Count the author's dispatch-starts after a line."""
    return sum(
        1
        for entry in records
        if entry.no > after_line
        and isinstance(entry.record, DispatchStart)
        and entry.record.author == author
    )


def failures_since(records: Sequence[Entry], line: int) -> int:
    """Count the build-failures after a line."""
    return sum(
        1
        for entry in records
        if entry.no > line and isinstance(entry.record, BuildFailure)
    )


def truncation_run(records: Sequence[Entry], line: int, author: object) -> int:
    """Count the author's trailing consecutive dispatch-starts after a line; any other record of theirs resets it."""
    run = 0
    for entry in records:
        if entry.no <= line or entry.author != author:
            continue
        run = run + 1 if isinstance(entry.record, DispatchStart) else 0
    return run


def entry_at(by_no: Mapping[int, Entry], pointer: object) -> Entry | None:
    """Return the entry a line pointer names under number equality, or None for any other value."""
    if isinstance(pointer, bool):
        return None
    return next((entry for entry in by_no.values() if entry.no == pointer), None)


def owner_present_for(log: Sequence[Entry], req_id: str, before: int) -> bool:
    """Return whether the slice's latest intake-decision before line `before` records a reachable owner.

    No such record, or no field, reads present. An intake appended after the
    request it would release is never consulted: a re-seeded intake cannot
    dissolve a pause the way a human reply does.
    """
    present = True
    for entry in log:
        if entry.no >= before:
            break
        if entry.req_id == req_id and isinstance(entry.record, IntakeDecision):
            present = entry.record.owner_present is not False
    return present


def pending_human_request(log: Sequence[Entry]) -> Entry | None:
    """Return the earliest human-targeted consultation-request left unanswered, or None."""
    return next(iter(pending_human_requests(log)), None)


def pending_human_requests(log: Sequence[Entry]) -> list[Entry]:
    """Return every unanswered human-targeted consultation-request, earliest first.

    A request is answered by a later consultation-response on its slice. It
    is superseded by a later request from the same author that targets a
    specialist: that author moved on. Another agent's request supersedes
    nothing, and a later human-targeted request supersedes nothing, since
    both wait on the same human.
    """
    pending: dict[str, list[Entry]] = {}
    for entry in log:
        req_id = entry.req_id
        if not isinstance(req_id, str):
            continue
        record = entry.record
        if isinstance(record, ConsultationRequest):
            target = record.target
            if isinstance(target, str) and target.strip().casefold() == HUMAN:
                pending.setdefault(req_id, []).append(entry)
            else:
                pending[req_id] = [
                    held
                    for held in pending.get(req_id, [])
                    if held.record.author != record.author  # type: ignore[union-attr]
                ]
        elif isinstance(record, ConsultationResponse):
            pending[req_id] = []
    return sorted(
        (entry for entries in pending.values() for entry in entries),
        key=lambda entry: entry.no,
    )


def unstarted_substantive(log: Sequence[Entry]) -> list[Entry]:
    """List the substantive records whose author never appended a dispatch-start for their slice."""
    started: set[tuple[object, object]] = set()
    unstarted: list[Entry] = []
    for entry in log:
        key = (entry.req_id, entry.author)
        if isinstance(entry.record, DispatchStart):
            started.add(key)
        elif (
            isinstance(entry.record, SUBSTANTIVE_CLASSES)
            and entry.author not in DISPATCH_EXEMPT
            and key not in started
        ):
            unstarted.append(entry)
    return unstarted


def unresolved_refactor(log: Sequence[Entry]) -> list[str]:
    """List the req_ids whose latest design-block verdict is still refactor-first."""
    latest: dict[str, str | None] = {}
    for entry in log:
        if isinstance(entry.record, DesignBlock) and isinstance(
            entry.record.req_id, str
        ):
            latest[entry.record.req_id] = entry.record.verdict
    return sorted(req for req, verdict in latest.items() if verdict == "refactor-first")
