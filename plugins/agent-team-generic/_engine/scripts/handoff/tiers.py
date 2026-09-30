"""Fold the tier ladder: the implementer tier the next dispatch runs, and the tier each window ran.

A leaf over handoff.ledger, handoff.records, and handoff.findings.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal, NamedTuple, TypeAlias

from .findings import AUTOFIX_TAG, ESCALATE_TAG, TRUNCATION_TAG, finding_owner
from .ledger import APPROVED, Entry
from .records import (
    IMPLEMENTER,
    ROUTINE_IMPLEMENTER,
    BuildFailure,
    BuildPass,
    DesignBlock,
    DispatchStart,
    ReviewFeedback,
)

ImplementMode: TypeAlias = Literal["fresh", "retry", "reviewed", "fix"]
BaseMode: TypeAlias = Literal["fresh", "retry", "reviewed"]

UNRATED_REASON = "effort:unrated"
ROUTINE_INITIAL_REASON = "initial:rated-routine"
RETIRED_REASON = "routine-retired"
ALL_AUTOFIX_REASON = "fix-round:all-autofix"
MIXED_REASON = "fix-round:mixed"
ROUTINE_RATING = "routine"
_BASE_TIER_REASON: dict[BaseMode, str] = {
    "fresh": "initial",
    "reviewed": "no-substantive-dissent",
    "retry": "recovery",
}


class TierChoice(NamedTuple):
    """The implementer the next dispatch runs and the ladder state that chose it."""

    agent: str
    reason: str


def implementer_tier(records: Sequence[Entry]) -> TierChoice:
    """Return the implementer tier for the slice's next dispatch."""
    return _tier_fold(records).choice()


def window_tiers(records: Sequence[Entry]) -> dict[int, str]:
    """Map each implementer dispatch-start line to the tier its window ran."""
    return _tier_fold(records).windows


def _tier_fold(records: Sequence[Entry]) -> "_TierWalk":
    """Walk one slice's records through the tier ladder."""
    walk = _TierWalk()
    for entry in records:
        record = entry.record
        if isinstance(record, DesignBlock):
            walk.design_block(record)
        elif isinstance(record, DispatchStart) and record.author == IMPLEMENTER:
            walk.implementer_start(entry.no)
        elif isinstance(record, BuildFailure):
            walk.build_failure()
        elif isinstance(record, BuildPass):
            walk.build_pass()
        elif isinstance(record, ReviewFeedback):
            walk.review_feedback(entry, record)
    return walk


@dataclass(slots=True)
class _TierWalk:
    """The fold state of the tier ladder while it walks one slice."""

    retired: bool = False
    active: bool = False
    rating: str | None = None
    mode: ImplementMode = "fresh"
    round_ok: bool | None = None
    pending: str | None = None
    pending_initial: bool = False
    last_window: str | None = None
    last_window_initial: bool = False
    windows: dict[int, str] = field(default_factory=dict)

    def choice(self) -> TierChoice:
        """Return the tier a dispatch in the current state runs, and why."""
        self._settle_routine_initial()
        if not self.active:
            return TierChoice(IMPLEMENTER, UNRATED_REASON)
        if self.retired:
            return TierChoice(IMPLEMENTER, RETIRED_REASON)
        if self.mode == "fix":
            if self.round_ok:
                return TierChoice(ROUTINE_IMPLEMENTER, ALL_AUTOFIX_REASON)
            return TierChoice(IMPLEMENTER, MIXED_REASON)
        if self.mode == "fresh" and self.rating == ROUTINE_RATING:
            return TierChoice(ROUTINE_IMPLEMENTER, ROUTINE_INITIAL_REASON)
        return TierChoice(IMPLEMENTER, _BASE_TIER_REASON[self.mode])

    def _settle_routine_initial(self) -> None:
        # A routine initial's pass is judged on the whole review pass: a
        # mixed round retires routine, an all-autofix round runs the variant
        # again. The judgment waits until the next decision, when every
        # feedback of the pass is in.
        if (
            self.mode == "fix"
            and self.last_window == ROUTINE_IMPLEMENTER
            and self.last_window_initial
            and self.round_ok is False
        ):
            self.retired = True

    def design_block(self, block: DesignBlock) -> None:
        self._settle_routine_initial()
        # The latest triage's rating decides the initial; an unrated re-triage
        # reads as involved.
        rated = isinstance(block.implementation_effort, str)
        self.active = self.active or rated
        self.rating = block.implementation_effort if rated else None
        self.mode = "fresh"
        self.round_ok = None
        self.pending = None
        self.pending_initial = False

    def implementer_start(self, line: int) -> None:
        if self.pending is None:
            self.pending_initial = self.mode == "fresh"
            self.pending = self.choice().agent
            self.windows[line] = self.pending

    def build_failure(self) -> None:
        # A failure in a routine window, or in a window the fold cannot
        # attribute, retires routine for the slice.
        if self.pending != IMPLEMENTER:
            self.retired = True
        self.mode = "retry"

    def build_pass(self) -> None:
        self.last_window = self.pending
        self.last_window_initial = self.pending_initial
        self.pending = None
        self.pending_initial = False
        self.round_ok = None
        self.mode = "reviewed"

    def review_feedback(self, entry: Entry, feedback: ReviewFeedback) -> None:
        if self.round_ok is None:
            self.round_ok = True
        findings = feedback.findings
        # The lenient lift drops non-object findings; a record that lost some
        # is not mechanical work.
        raw_findings = entry.raw.get("findings")
        dropped = not isinstance(raw_findings, list) or len(raw_findings) != len(
            findings
        )
        if dropped or any(f.tag == ESCALATE_TAG for f in findings):
            self.round_ok = False
        substantive = not findings or any(f.tag != TRUNCATION_TAG for f in findings)
        if feedback.verdict == APPROVED or not substantive:
            return
        if not findings:
            self.round_ok = False
        # Dissent on a routine fix window's pass retires routine at once; a
        # routine initial's pass is settled on the whole round instead.
        if self.last_window != IMPLEMENTER and not self.last_window_initial:
            self.retired = True
        self.mode = "fix"
        if any(
            finding_owner(f) == IMPLEMENTER and f.tag != AUTOFIX_TAG for f in findings
        ):
            self.round_ok = False
