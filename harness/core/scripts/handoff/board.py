"""Build the board: one typed model of a slice that the text and Markdown views render.

A middle layer over handoff.ledger, handoff.records, handoff.text, handoff.timestamps, and
handoff.cost, beside handoff.routing; the board reads and never gates.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import NamedTuple, TypeAlias

from .cost import CostFigures, CostLookup
from .ledger import Entry, cycle_round, cycle_start, entry_at, latest_of
from .records import (
    DESIGNER,
    GRADER,
    IMPLEMENTER,
    PRODUCT,
    ROSTER_FLOOR,
    ROUTINE_IMPLEMENTER,
    BuildFailure,
    BuildPass,
    ConsultationRequest,
    ConsultationResponse,
    DesignBlock,
    DesignDocAutofix,
    DispatchStart,
    Finding,
    GraderFeatures,
    GraderVerdict,
    PrdAutofix,
    PrdEntry,
    ReviewFeedback,
)
from .schema import sanitize
from .timestamps import elapsed, seconds_of

COORDINATOR = "pipeline-coordinator"
UNKNOWN_LABEL = "?"
AGENT_LABELS = {
    IMPLEMENTER: "implementer",
    DESIGNER: "design",
    PRODUCT: "prd-expert",
    COORDINATOR: "coord",
    GRADER: "grader",
}
# A ledger written under an earlier grade vocabulary renders in the current one.
GRADE_ALIASES = {"clear": "skim", "concern": "scrutinize"}
_MIN_TIMED_ENTRIES = 2

# The record types timed from their author's dispatch-start; an implement
# session times itself from opener to closer.
_TIMED_TYPES = (PrdEntry, DesignBlock, ReviewFeedback)
_SESSION_CHILDREN = (BuildFailure, BuildPass, ConsultationRequest, ConsultationResponse)
_DOC_AUTOFIXES = (DesignDocAutofix, PrdAutofix)


# --- the model -----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BoardOptions:
    """Everything the view command decides for one render."""

    req_id: str | None = None
    roster: Sequence[str] = ROSTER_FLOOR
    color: bool = False
    verbose: bool = False
    auto_grade: bool = True
    cost_lookup: CostLookup | None = None
    window_tiers: Mapping[int, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Tail:
    """The elapsed time a timed line carries, and the cost that rode the same window."""

    elapsed: str
    cost: CostFigures | None = None


class FixSources(NamedTuple):
    """The dissenting reviews a fix dispatch answers, as labels and a finding count."""

    reviewers: tuple[str, ...]
    findings: int


@dataclass(frozen=True, slots=True)
class Step:
    """One flat timeline row."""

    entry: Entry
    tail: Tail | None = None
    fix: FixSources | None = None
    requester: object = None


@dataclass(frozen=True, slots=True)
class Session:
    """One implement session: the opener, its nested children, and the hoisted siblings."""

    opener: Entry
    routine: bool
    fix: FixSources | None
    tail: Tail | None
    tier_note: str | None
    children: tuple[Entry, ...]
    siblings: tuple[Step, ...]


TimelineItem: TypeAlias = Step | Session


@dataclass(frozen=True, slots=True)
class Board:
    """One slice as the views render it: header facts, review rounds, and the timeline."""

    req_id: str | None
    title: str | None
    grade: str | None
    passes: int
    failures: int
    rounds: tuple[Mapping[str, Entry], ...]
    ladder_round: int
    slice_tail: Tail | None
    other_slices: tuple[str, ...]
    timeline: tuple[TimelineItem, ...]


@dataclass(frozen=True, slots=True)
class SessionSpan:
    """The records one implement session consumes."""

    children: tuple[Entry, ...]
    siblings: tuple[Entry, ...]
    closer: Entry | None
    next_index: int


@dataclass(frozen=True, slots=True)
class _TimelineInputs:
    """What every timeline builder reads."""

    log: Sequence[Entry]
    by_no: Mapping[int, Entry]
    options: BoardOptions


# --- building the board --------------------------------------------------------


def build_board(
    log: Sequence[Entry],
    req_id: str | None,
    options: BoardOptions,
    other_slices: Sequence[str],
) -> Board:
    """Build the board of one slice from the whole log."""
    by_no = {entry.no: entry for entry in log}
    entries = [entry for entry in log if in_slice(entry, req_id)]
    return Board(
        req_id=req_id,
        title=slice_title(entries),
        grade=slice_grade(entries),
        passes=sum(1 for entry in entries if isinstance(entry.record, BuildPass)),
        failures=sum(1 for entry in entries if isinstance(entry.record, BuildFailure)),
        rounds=review_rounds(entries),
        ladder_round=ladder_round(entries, options.roster),
        slice_tail=slice_tail(entries, options.cost_lookup),
        other_slices=tuple(other_slices),
        timeline=_timeline(entries, _TimelineInputs(log, by_no, options)),
    )


def slice_title(entries: Sequence[Entry]) -> str | None:
    """Return the latest prd-entry title in the slice, or None."""
    title: str | None = None
    for entry in entries:
        if isinstance(entry.record, PrdEntry) and isinstance(entry.record.title, str):
            title = entry.record.title
    return title


def slice_grade(entries: Sequence[Entry]) -> str | None:
    """Return the latest grade in the current vocabulary, or None when the slice has no grade word."""
    grade: object = None
    for entry in entries:
        if isinstance(entry.record, GraderVerdict):
            grade = grade_word(entry.record.verdict)
    return grade if isinstance(grade, str) else None


def slice_tail(entries: Sequence[Entry], cost_lookup: CostLookup | None) -> Tail | None:
    """Return the whole-slice roll-up from first to last timed record, only when the cost attributes."""
    timed = [
        (entry, seconds)
        for entry in entries
        if (seconds := entry_seconds(entry)) is not None
    ]
    if len(timed) < _MIN_TIMED_ENTRIES:
        return None
    first = min(seconds for _, seconds in timed)
    last = max(seconds for _, seconds in timed)
    span = elapsed(first, last)
    if not span or cost_lookup is None:
        return None
    authors = [entry.author for entry in entries if isinstance(entry.author, str)]
    figures = cost_lookup.slice_window(authors, first, last)
    return Tail(span, figures) if figures is not None else None


# --- the timeline --------------------------------------------------------------


def _timeline(
    slice_entries: Sequence[Entry], inputs: _TimelineInputs
) -> tuple[TimelineItem, ...]:
    """Walk one slice in append order: implement sessions consume their records, the rest is flat."""
    items: list[TimelineItem] = []
    index = 0
    while index < len(slice_entries):
        entry = slice_entries[index]
        if isinstance(entry.record, GraderFeatures):
            index += 1
            continue
        if (
            isinstance(entry.record, DispatchStart)
            and entry.record.author == IMPLEMENTER
        ):
            session, index = _session(slice_entries, index, inputs)
            items.append(session)
            continue
        items.append(_step(entry, inputs, timed=True))
        index += 1
    return tuple(items)


def _session(
    slice_entries: Sequence[Entry], start: int, inputs: _TimelineInputs
) -> tuple[Session, int]:
    """Build one implement session from its opener; return it with the index after it."""
    opener = slice_entries[start]
    span = session_span(slice_entries, start, inputs.by_no)
    cost_lookup = inputs.options.cost_lookup
    routine = inputs.options.window_tiers.get(opener.no) == ROUTINE_IMPLEMENTER
    session = Session(
        opener,
        routine,
        fix_sources(opener, inputs.by_no),
        session_tail(opener, span.closer, cost_lookup),
        tier_mismatch(opener, span.closer, cost_lookup, routine=routine),
        span.children,
        tuple(_step(sibling, inputs, timed=False) for sibling in span.siblings),
    )
    return session, span.next_index


def session_tail(
    opener: Entry, closer: Entry | None, cost_lookup: CostLookup | None
) -> Tail | None:
    """Return the session's elapsed time and cost from opener to closer; an open session has none."""
    if closer is None:
        return None
    first, last = entry_seconds(opener), entry_seconds(closer)
    span = elapsed(first, last)
    if not span:
        return None
    figures = cost_lookup.window(IMPLEMENTER, first, last) if cost_lookup else None
    return Tail(span, figures)


def tier_mismatch(
    opener: Entry,
    closer: Entry | None,
    cost_lookup: CostLookup | None,
    *,
    routine: bool,
) -> str | None:
    """Return the tier the transcripts say ran when it contradicts the prediction, else None."""
    if cost_lookup is None or closer is None:
        return None
    ran = cost_lookup.window_types(entry_seconds(opener), entry_seconds(closer))
    if not ran or len(ran) != 1:
        return None
    ran_routine = ran[0] != IMPLEMENTER
    if ran_routine == routine:
        return None
    return "ran routine" if ran_routine else "ran base"


def session_span(
    slice_entries: Sequence[Entry], start: int, by_no: Mapping[int, Entry]
) -> SessionSpan:
    """Consume the records of the implement session opening at `start`."""
    children: list[Entry] = []
    siblings: list[Entry] = []
    closer: Entry | None = None
    index = start + 1
    while index < len(slice_entries):
        entry = slice_entries[index]
        record = entry.record
        if isinstance(record, DispatchStart):
            # A doc-owner's fix dispatched in the same round is a sibling; the
            # implementer's own retries and consult targets are absorbed.
            if record.author != IMPLEMENTER and fix_sources(entry, by_no):
                siblings.append(entry)
            index += 1
            continue
        if isinstance(record, _DOC_AUTOFIXES):
            siblings.append(entry)
            index += 1
            continue
        if not isinstance(record, _SESSION_CHILDREN):
            break
        if isinstance(
            record, (ConsultationRequest, ConsultationResponse)
        ) and not _own_consult(entry, by_no):
            siblings.append(entry)
            index += 1
            continue
        children.append(entry)
        index += 1
        aborted = isinstance(record, BuildFailure) and isinstance(
            record.abort_reason, str
        )
        if isinstance(record, BuildPass) or aborted:
            closer = entry
            break
    return SessionSpan(tuple(children), tuple(siblings), closer, index)


def _own_consult(entry: Entry, by_no: Mapping[int, Entry]) -> bool:
    """Return whether a consult inside a session window belongs to the implementer."""
    record = entry.record
    if isinstance(record, ConsultationRequest):
        return record.author == IMPLEMENTER
    if isinstance(record, ConsultationResponse):
        request = entry_at(by_no, record.in_response_to)
        return request is not None and request.author == IMPLEMENTER
    return False


def _step(entry: Entry, inputs: _TimelineInputs, *, timed: bool) -> Step:
    """Build one flat row; only rows on the slice walk carry a tail."""
    tail = (
        step_tail(entry, inputs.log, inputs.options.cost_lookup)
        if timed and isinstance(entry.record, _TIMED_TYPES)
        else None
    )
    return Step(
        entry,
        tail,
        fix_sources(entry, inputs.by_no),
        requester_of(entry, inputs.by_no),
    )


def step_tail(
    entry: Entry, log: Sequence[Entry], cost_lookup: CostLookup | None
) -> Tail | None:
    """Return the duration and cost of one timed record from its author's dispatch, or None."""
    start = producer_dispatch(entry, log)
    if start is None:
        return None
    first, last = entry_seconds(start), entry_seconds(entry)
    span = elapsed(first, last)
    if not span:
        return None
    figures = cost_lookup.window(entry.author, first, last) if cost_lookup else None
    return Tail(span, figures)


def producer_dispatch(entry: Entry, log: Sequence[Entry]) -> Entry | None:
    """Return the dispatch-start that spawned the entry's author within its slice, if it timed nothing earlier."""
    author = entry.author
    if not author:
        return None
    req_id = entry.req_id
    record_type = type(entry.record)
    start: Entry | None = None
    for candidate in log:
        if candidate.no >= entry.no:
            break
        if (
            isinstance(candidate.record, DispatchStart)
            and candidate.author == author
            and candidate.req_id == req_id
        ):
            start = candidate
    if start is None:
        return None
    # A re-engaged author appends no fresh dispatch, so an intervening record
    # of the same type already consumed this start.
    for candidate in log:
        if candidate.no <= start.no:
            continue
        if candidate.no >= entry.no:
            break
        if (
            type(candidate.record) is record_type
            and candidate.author == author
            and candidate.req_id == req_id
        ):
            return None
    return start


def fix_sources(entry: Entry, by_no: Mapping[int, Entry]) -> FixSources | None:
    """Return the dissenting reviews a dispatch answers, or None when it answers none."""
    if not isinstance(entry.record, DispatchStart):
        return None
    sources = [
        by_no[target]
        for target in entry.record.responding_to
        if isinstance(target, int) and _is_dissenting_review(by_no.get(target))
    ]
    if not sources:
        return None
    reviewers: list[str] = []
    for source in sources:
        label = agent_label(source.author)
        if label not in reviewers:
            reviewers.append(label)
    return FixSources(
        tuple(reviewers), sum(len(findings_of(source)) for source in sources)
    )


def _is_dissenting_review(entry: Entry | None) -> bool:
    return (
        entry is not None
        and isinstance(entry.record, ReviewFeedback)
        and entry.record.verdict != "approved"
    )


def requester_of(entry: Entry, by_no: Mapping[int, Entry]) -> object:
    """Return the author a consultation-response returns to, or None."""
    if not isinstance(entry.record, ConsultationResponse):
        return None
    request = entry_at(by_no, entry.record.in_response_to)
    if request is None or not isinstance(request.record, ConsultationRequest):
        return None
    return request.author


def entry_seconds(entry: Entry) -> float | None:
    """Return the entry's timestamp as POSIX seconds, or None."""
    return seconds_of(entry.ts)


# --- rounds and slices ---------------------------------------------------------


def review_rounds(entries: Sequence[Entry]) -> tuple[dict[str, Entry], ...]:
    """Group review feedback into rounds: a reviewer reappearing starts a new round."""
    rounds: list[dict[str, Entry]] = []
    current: dict[str, Entry] = {}
    for entry in entries:
        if not isinstance(entry.record, ReviewFeedback):
            continue
        author = entry.author if isinstance(entry.author, str) else UNKNOWN_LABEL
        if author in current:
            rounds.append(current)
            current = {}
        current[author] = entry
    if current:
        rounds.append(current)
    return tuple(rounds)


def ladder_round(entries: Sequence[Entry], roster: Sequence[str]) -> int:
    """Return the router's convergence round for the slice's current pass."""
    last_pass = latest_of(entries, BuildPass)
    return cycle_round(
        entries, cycle_start(entries), last_pass[0].no if last_pass else 0, roster
    )


def matrix_authors(
    rounds: Sequence[Mapping[str, Entry]], roster: Sequence[str]
) -> list[str]:
    """Return the matrix rows: the roster first, then off-roster authors as they appear."""
    authors = list(roster)
    for round_ in rounds:
        authors.extend(author for author in round_ if author not in authors)
    return authors


def in_slice(entry: Entry, req_id: str | None) -> bool:
    """Return whether the entry belongs to the slice; None is the group without a req_id."""
    value = entry.req_id
    if req_id is None:
        return not (isinstance(value, str) and value)
    return bool(value == req_id)


def slice_order(log: Sequence[Entry]) -> list[str | None]:
    """Return the slice keys in first-appearance order, the req_id-less group last."""
    order: list[str | None] = []
    seen: set[str] = set()
    has_none = False
    for entry in log:
        value = entry.req_id
        if isinstance(value, str) and value:
            if value not in seen:
                seen.add(value)
                order.append(value)
        else:
            has_none = True
    if has_none:
        order.append(None)
    return order


# --- record vocabulary for display ---------------------------------------------


def agent_label(author: object) -> str:
    """Return the short display label for an author."""
    if not isinstance(author, str) or not author:
        return UNKNOWN_LABEL
    if author in AGENT_LABELS:
        return AGENT_LABELS[author]
    if author.endswith("-reviewer"):
        return sanitize(author[: -len("-reviewer")])
    return sanitize(author)


def grade_word(value: object) -> object:
    """Return the current vocabulary's word for a recorded grade."""
    if isinstance(value, str):
        return GRADE_ALIASES.get(value, value)
    return value


def findings_of(entry: Entry) -> tuple[Finding, ...]:
    """Return the entry's findings when it is a review, else an empty tuple."""
    return entry.record.findings if isinstance(entry.record, ReviewFeedback) else ()


def facet_rows(entry: Entry) -> list[tuple[str, Mapping[str, object]]]:
    """Return a grade's facets as written, name and object per row, malformed values as empty."""
    # The board renders the record's own facet keys in their own order, so it
    # reads the raw object; a value that is not an object still earns its row.
    facets = (
        entry.raw.get("facets") if isinstance(entry.record, GraderVerdict) else None
    )
    if not isinstance(facets, dict) or not facets:
        return []
    return [
        (str(name), facet if isinstance(facet, dict) else {})
        for name, facet in facets.items()
    ]
