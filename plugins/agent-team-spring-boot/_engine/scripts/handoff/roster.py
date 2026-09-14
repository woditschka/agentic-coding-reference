"""Resolve the reviewer roster from the layout, and the pass roster from the active review plan.

A leaf over handoff.ledger, handoff.records, and handoff.schema.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, NamedTuple, TypeAlias

from .ledger import Entry, latest_of, silent_starts
from .records import PLAN_ENGINE, PLANNER, ROSTER_FLOOR, ReviewPlan
from .schema import layout_lookup

RosterGap: TypeAlias = Literal["no-plan", "invalid-plan", "unauthored-plan"]
PlannerStepKind: TypeAlias = Literal[
    "plan-gray-invalid",
    "plan-gray",
    "planner-stall-retry",
    "planner-stalled",
    "plan-roster-invalid",
]
GRAY = "gray"
# A second silent dispatch-start after the one stall retry means stalled.
SILENT_STARTS_BEFORE_STALL = 2


@dataclass(frozen=True, slots=True)
class RosterResult:
    """The layout's reviewer roster, or the error naming its malformed declaration."""

    roster: tuple[str, ...] | None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PassRoster:
    """The reviewers gated in this pass and the fail-closed gap, when one fired."""

    reviewers: tuple[str, ...]
    gap: RosterGap | None = None


class PlannerStep(NamedTuple):
    """The step the planner's ladder takes before a pass has a roster."""

    kind: PlannerStepKind
    plan_line: int


def reviewer_roster(layout: dict[str, Any]) -> RosterResult:
    """Return the reviewer roster from the layout, or the error naming the malformed declaration."""
    extras = layout_lookup(layout, "harness.extra_reviewers")
    if extras is None:
        return RosterResult(ROSTER_FLOOR)
    if not isinstance(extras, list) or any(
        not isinstance(extra, str) or not extra for extra in extras
    ):
        return RosterResult(
            None,
            "harness.extra_reviewers in scripts/layout.toml must be a list of reviewer names",
        )
    roster = list(ROSTER_FLOOR)
    roster.extend(extra for extra in extras if extra not in roster)
    return RosterResult(tuple(roster))


def auto_grade(layout: dict[str, Any]) -> bool:
    """Return whether the pipeline dispatches the change-grader once the roster approves."""
    return layout_lookup(layout, "harness.auto_grade") is not False


def pass_roster(
    records: Sequence[Entry], build_pass_line: int, roster: Sequence[str]
) -> PassRoster | PlannerStep:
    """Resolve this pass's roster from the active plan, or name the planner step that obtains one."""
    plan = active_plan(records, build_pass_line)
    if plan is None:
        return PassRoster(tuple(roster), "no-plan")
    plan_entry, plan_record = plan
    if plan_record.risk == GRAY:
        return _gray_plan_step(records, plan_entry, plan_record)
    if plan_record.author == PLANNER:
        earlier_plans = _plans_between(records, build_pass_line, plan_entry.no)
        outcome = _planner_plan_check(
            earlier_plans, plan_record, plan_entry.no, tuple(roster)
        )
        if outcome is not None:
            return outcome
    elif plan_record.author != PLAN_ENGINE:
        return PassRoster(tuple(roster), "unauthored-plan")
    plan_roster = plan_record.roster
    if not plan_roster or any(r not in roster for r in plan_roster):
        return PassRoster(tuple(roster), "invalid-plan")
    return PassRoster(tuple(r for r in roster if r in plan_roster))


def active_plan(
    records: Sequence[Entry], build_pass_line: int
) -> tuple[Entry, ReviewPlan] | None:
    """Return the latest review-plan after the current build-pass, or None."""
    after = (entry for entry in records if entry.no > build_pass_line)
    return latest_of(after, ReviewPlan)


def _gray_plan_step(
    records: Sequence[Entry], plan_entry: Entry, plan_record: ReviewPlan
) -> PlannerStep:
    """Walk the planner's stall ladder for a gray plan."""
    if plan_record.author != PLAN_ENGINE:
        return PlannerStep("plan-gray-invalid", plan_entry.no)
    starts = silent_starts(records, plan_entry.no, PLANNER)
    if starts == 0:
        return PlannerStep("plan-gray", plan_entry.no)
    if starts < SILENT_STARTS_BEFORE_STALL:
        return PlannerStep("planner-stall-retry", plan_entry.no)
    return PlannerStep("planner-stalled", plan_entry.no)


def _plans_between(
    records: Sequence[Entry], after_line: int, before_line: int
) -> list[ReviewPlan]:
    """Return the review-plans strictly between two lines, in ledger order."""
    return [
        entry.record
        for entry in records
        if after_line < entry.no < before_line and isinstance(entry.record, ReviewPlan)
    ]


def _planner_plan_check(
    earlier_plans: Sequence[ReviewPlan],
    plan_record: ReviewPlan,
    plan_line: int,
    roster: tuple[str, ...],
) -> PassRoster | PlannerStep | None:
    """Fail a planner plan closed unless an engine deferral in this pass invited it."""
    deferred = any(p.risk == GRAY and p.author == PLAN_ENGINE for p in earlier_plans)
    if not deferred:
        return PassRoster(roster, "unauthored-plan")
    if plan_record.roster:
        return None
    # The planner's one deliverable is the roster; it redoes a roster-less
    # plan once, then the pass fails closed to the full battery.
    redone = any(p.author == PLANNER and not p.roster for p in earlier_plans)
    if redone:
        return PassRoster(roster, "invalid-plan")
    return PlannerStep("plan-roster-invalid", plan_line)
