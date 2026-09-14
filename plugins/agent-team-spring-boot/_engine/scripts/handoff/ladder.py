"""Place each pass reviewer on the review ladder and detect a pass that is not converging.

A leaf over handoff.ledger, handoff.records, handoff.findings, and handoff.roster.
"""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, NamedTuple, TypeAlias

from .findings import ESCALATE_TAG, carries_capped_dissent, escalate_count, raw_findings
from .ledger import (
    APPROVED,
    Entry,
    has_substantive_dissent,
    is_substantive_dissent,
    pass_windows,
    silent_starts,
)
from .records import REVIEW_ROUND_CAP, BuildPass, DispatchStart, ReviewFeedback
from .roster import SILENT_STARTS_BEFORE_STALL, RosterGap

# A reviewer's third substantive dissent within one pass ends the pass.
PASS_DISSENT_CAP = 3
# The third consecutive truncation-only pass ends the cycle.
TRUNCATION_RUN_CAP = 3
DISSENTING_VERDICTS = ("changes_requested", "blocked")
CeilingCause: TypeAlias = Literal[
    "empty-findings", "pass-churn", "round-cap", "truncation-run"
]


@dataclass(frozen=True, slots=True)
class ReviewPass:
    """The current review pass: its records, build-pass, cycle, round, and rosters."""

    records: tuple[Entry, ...]
    build_pass_line: int
    cycle_start: int
    round_no: int
    reviewers: tuple[str, ...]
    roster_gap: RosterGap | None
    roster: tuple[str, ...]

    @property
    def critical_only(self) -> bool:
        """Return whether this round admits dissent only for a critical defect or a channel finding."""
        return self.round_no >= REVIEW_ROUND_CAP

    def round_context(self) -> dict[str, Any]:
        """Return the round fields every reviewer dispatch carries."""
        context: dict[str, Any] = {"round": self.round_no}
        if self.critical_only:
            context["finding_bar"] = "critical-only"
            context["prompt_note"] = (
                f"Review round {self.round_no}: critical-only. A defect that must not merge "
                "is severity critical; residual polish rides recommendations on "
                "an approved verdict; a question rides clarify, a human decision "
                "rides escalate."
            )
        else:
            context["prompt_note"] = f"Review round {self.round_no}."
        return context

    def feedback_since_build_pass(self) -> Iterator[tuple[Entry, ReviewFeedback]]:
        """Yield every review-feedback entry after this pass's build-pass."""
        for entry in self.records:
            if entry.no > self.build_pass_line and isinstance(
                entry.record, ReviewFeedback
            ):
                yield entry, entry.record


@dataclass(frozen=True, slots=True)
class ReviewerLadder:
    """Where each pass reviewer stands since the build-pass."""

    feedback: dict[str, Entry]
    retry_once: tuple[str, ...]
    stalled: tuple[str, ...]
    undispatched: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Ceiling:
    """Why a pass stops converging: the cause and the reviewers it names."""

    cause: CeilingCause
    reviewers: tuple[str, ...]
    escalate_findings: int = 0


class OutstandingDissent(NamedTuple):
    """Cycle reviewers the pass roster dropped while their latest verdict still dissents."""

    reviewers: tuple[str, ...]
    stalled: tuple[str, ...]


def reviewer_ladder(review: ReviewPass) -> ReviewerLadder:
    """Classify each pass reviewer by its feedback and silent dispatch-starts."""
    feedback: dict[str, Entry] = {}
    retry_once: list[str] = []
    stalled: list[str] = []
    undispatched: list[str] = []
    for reviewer in review.reviewers:
        current: Entry | None = None
        starts = 0
        for entry in review.records:
            if entry.no <= review.build_pass_line or entry.author != reviewer:
                continue
            if isinstance(entry.record, ReviewFeedback):
                current = entry
                starts = 0
            elif isinstance(entry.record, DispatchStart):
                starts += 1
        if starts == 0 and current is not None:
            feedback[reviewer] = current
        elif starts == 0:
            undispatched.append(reviewer)
        elif starts < SILENT_STARTS_BEFORE_STALL:
            retry_once.append(reviewer)
        else:
            stalled.append(reviewer)
    return ReviewerLadder(
        feedback, tuple(retry_once), tuple(stalled), tuple(undispatched)
    )


def escalate_precedes_pass(records: Sequence[Entry], build_pass_line: int) -> bool:
    """Return whether the previous pass ended on an escalate finding no review has followed."""
    previous_pass_line = max(
        (
            entry.no
            for entry in records
            if entry.no < build_pass_line and isinstance(entry.record, BuildPass)
        ),
        default=0,
    )
    prior_escalate = any(
        previous_pass_line < entry.no < build_pass_line
        and isinstance(entry.record, ReviewFeedback)
        and any(f.tag == ESCALATE_TAG for f in entry.record.findings)
        for entry in records
    )
    feedback_since = any(
        entry.no > build_pass_line and isinstance(entry.record, ReviewFeedback)
        for entry in records
    )
    return prior_escalate and not feedback_since


def dissent_ceiling(
    review: ReviewPass, verdicts: Mapping[str, ReviewFeedback]
) -> Ceiling | None:
    """Name why a pass is not converging: empty dissent, pass churn, the round cap, a truncation run."""
    non_approved = {r: fb for r, fb in verdicts.items() if fb.verdict != APPROVED}
    empty = [
        r
        for r in review.reviewers
        if r in non_approved and not non_approved[r].findings
    ]
    if empty:
        return Ceiling("empty-findings", tuple(empty))
    churned = churned_reviewers(review)
    if churned:
        return Ceiling("pass-churn", tuple(churned))
    substantive = sorted(
        r for r, fb in non_approved.items() if is_substantive_dissent(fb)
    )
    if review.round_no > REVIEW_ROUND_CAP and substantive:
        return Ceiling("round-cap", tuple(substantive), escalate_count(verdicts))
    if (
        non_approved
        and not substantive
        and truncation_only_passes(review) >= TRUNCATION_RUN_CAP
    ):
        return Ceiling("truncation-run", tuple(sorted(non_approved)))
    return None


def churned_reviewers(review: ReviewPass) -> list[str]:
    """List the roster reviewers whose substantive dissents in this pass reached the cap."""
    dissents: dict[str, int] = {}
    for entry, feedback in review.feedback_since_build_pass():
        author = entry.author
        if isinstance(author, str) and is_substantive_dissent(feedback):
            dissents[author] = dissents.get(author, 0) + 1
    return sorted(r for r in review.roster if dissents.get(r, 0) >= PASS_DISSENT_CAP)


def truncation_only_passes(review: ReviewPass) -> int:
    """Count the consecutive passes, this one included, whose only dissent is a truncation checkpoint."""
    run = 1
    windows = pass_windows(
        review.records, review.cycle_start, review.build_pass_line, review.roster
    )
    for window in reversed(windows):
        dissent = {a: fb for a, fb in window.items() if fb.verdict != APPROVED}
        if dissent and not has_substantive_dissent(dissent):
            run += 1
        else:
            break
    return run


def dissents_below_bar(review: ReviewPass, entry: Entry, findings: list[Any]) -> bool:
    """Return whether the feedback dissents on polish alone during a critical-only round."""
    return (
        review.critical_only
        and isinstance(entry.record, ReviewFeedback)
        and entry.record.verdict in DISSENTING_VERDICTS
        and bool(findings)
        and not carries_capped_dissent(findings)
    )


def prior_below_bar_dissent(review: ReviewPass, reviewer: str, entry: Entry) -> bool:
    """Return whether the reviewer already dissented below the bar earlier in this pass."""
    return any(
        earlier.no < entry.no
        and earlier.author == reviewer
        and feedback.verdict != APPROVED
        and feedback.findings
        and not carries_capped_dissent(raw_findings(earlier))
        for earlier, feedback in review.feedback_since_build_pass()
    )


def outstanding_dissent(review: ReviewPass) -> OutstandingDissent | None:
    """Find cycle reviewers the pass roster dropped while their latest verdict still dissents."""
    latest_verdict: dict[str, str | None] = {}
    latest_line: dict[str, int] = {}
    for entry in review.records:
        if entry.no > review.cycle_start and isinstance(entry.record, ReviewFeedback):
            author = entry.record.author
            if isinstance(author, str) and author:
                latest_verdict[author] = entry.record.verdict
                latest_line[author] = entry.no
    reviewers = tuple(
        r
        for r in review.roster
        if r not in review.reviewers and latest_verdict.get(r) not in (None, APPROVED)
    )
    if not reviewers:
        return None
    stalled = tuple(
        r
        for r in reviewers
        if silent_starts(review.records, latest_line[r], r)
        >= SILENT_STARTS_BEFORE_STALL
    )
    return OutstandingDissent(reviewers, stalled)
