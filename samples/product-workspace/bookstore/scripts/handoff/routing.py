"""Decide the next pipeline step from the ledger, deterministically and fail-closed.

A middle layer over the ledger and the routing leaves (findings, tiers, roster, ladder,
scope_lock); never imports handoff.view.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, TypeAlias, TypeVar, assert_never

from .findings import (
    OWNER_ORDER,
    escalate_count,
    finding_shape_errors,
    owner_split,
    raw_findings,
)
from .ladder import (
    Ceiling,
    ReviewerLadder,
    ReviewPass,
    dissent_ceiling,
    dissents_below_bar,
    escalate_precedes_pass,
    outstanding_dissent,
    prior_below_bar_dissent,
    reviewer_ladder,
)
from .ledger import (
    APPROVED,
    Entry,
    cycle_round,
    cycle_start,
    entry_at,
    failures_since,
    latest_of,
    pending_human_request,
    superseded_design_block,
    truncation_run,
    typed_log,
    unresolved_refactor,
)
from .records import (
    DESIGNER,
    GRADER,
    HUMAN,
    IMPLEMENTER,
    PLANNER,
    PRODUCT,
    RETRY_CAP,
    REVIEW_ROUND_CAP,
    SUBSTANTIVE_CLASSES,
    BuildFailure,
    BuildPass,
    ConsultationRequest,
    ConsultationResponse,
    DesignBlock,
    DesignDocAutofix,
    DispatchStart,
    GraderFeatures,
    GraderVerdict,
    HandoffRecord,
    IntakeDecision,
    PrdAutofix,
    PrdEntry,
    ReviewFeedback,
    ReviewPlan,
    UnknownRecord,
)
from .roster import (
    PassRoster,
    PlannerStep,
    RosterGap,
    auto_grade,
    pass_roster,
    reviewer_roster,
)
from .schema import LogEntry, SchemaError, load_schema, validate_record
from .scope_lock import OverrideSources, scope_lock_errors
from .tiers import implementer_tier

DecisionKind: TypeAlias = Literal["dispatch", "blocked", "escalate"]

IMPLEMENTABLE_VERDICTS = frozenset({"covered", "minor", "new", "foundational"})
CONFLICTING_VERDICT = "conflicting"
REFACTOR_FIRST_VERDICT = "refactor-first"

_RecordT = TypeVar("_RecordT", bound=HandoffRecord)


# --- the decision ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Decision:
    """One route decision: its kind, rule, and reason, with the slice and payload the JSON carries."""

    kind: DecisionKind
    rule: str
    reason: str
    req_id: str | None = None
    next: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    context: Mapping[str, object] = field(default_factory=dict)

    def as_json(self) -> dict[str, Any]:
        """Return the object `route` prints, keys in the order the contract fixes."""
        out: dict[str, Any] = {"decision": self.kind}
        if self.kind == "dispatch":
            out["next"] = list(self.next)
        out["rule"] = self.rule
        out["reason"] = self.reason
        if self.req_id:
            out["req_id"] = self.req_id
        if self.errors:
            out["errors"] = list(self.errors)
        if self.context:
            out["context"] = dict(self.context)
        return out


def dispatch(
    next_agents: Sequence[str],
    rule: str,
    reason: str,
    req_id: str | None,
    **context: object,
) -> Decision:
    """Build a dispatch decision naming the next agents."""
    return Decision("dispatch", rule, reason, req_id, tuple(next_agents), (), context)


def blocked(
    rule: str,
    reason: str,
    req_id: str | None = None,
    errors: list[str] | None = None,
    **context: object,
) -> Decision:
    """Build a blocked decision: the slice halts for the human."""
    return Decision("blocked", rule, reason, req_id, (), tuple(errors or ()), context)


def escalate(
    rule: str, reason: str, req_id: str | None = None, **context: object
) -> Decision:
    """Build an escalate decision: the coordinator judges the state."""
    return Decision("escalate", rule, reason, req_id, (), (), context)


# --- the route --------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RouteInput:
    """Everything one route decision reads."""

    entries: Sequence[LogEntry]
    req_id: str | None
    schemas_dir: str
    layout: dict[str, Any]
    non_goal_delta: tuple[str, ...] | None


class GateChecker(Protocol):
    """The schema check every gating record passes before its row routes."""

    def errors(self, entry: Entry, record_type: str) -> list[str]:
        """Return the record's violations; a schema that fails to load is one."""
        ...


@dataclass(frozen=True, slots=True)
class SchemaGate:
    """The schema check loaded per record type from the schemas directory."""

    schemas_dir: str
    layout: dict[str, Any]

    def errors(self, entry: Entry, record_type: str) -> list[str]:
        """Schema-check one gating record; a schema that fails to load is a gate failure."""
        try:
            schema = load_schema(self.schemas_dir, record_type, self.layout)
        except SchemaError as exc:
            return [str(exc)]
        return validate_record(entry.raw, schema)


@dataclass(frozen=True, slots=True)
class RouteContext:
    """The parsed log narrowed to one slice, with the gate and the decision forms."""

    log: tuple[Entry, ...]
    records: tuple[Entry, ...]
    req_id: str
    roster: tuple[str, ...]
    layout: dict[str, Any]
    non_goal_delta: tuple[str, ...] | None
    unresolved_refactor: tuple[str, ...]
    gate: GateChecker

    def latest(self, cls: type[_RecordT]) -> tuple[Entry, _RecordT] | None:
        """Return the slice's latest entry whose record is a `cls`."""
        return latest_of(self.records, cls)

    @property
    def by_line(self) -> dict[int, Entry]:
        """Return the slice's entries keyed by line number."""
        return {entry.no: entry for entry in self.records}

    def entry_at(self, pointer: object) -> Entry | None:
        """Return the slice entry a line pointer names, or None for a boolean or a missing line."""
        return entry_at(self.by_line, pointer)

    def gate_errors(self, entry: Entry, record_type: str) -> list[str]:
        """Return the gate's violations for one record of the slice."""
        return self.gate.errors(entry, record_type)

    def dispatch(
        self, next_agents: Sequence[str], rule: str, reason: str, **context: object
    ) -> Decision:
        """Dispatch the named agents for this slice."""
        return dispatch(next_agents, rule, reason, self.req_id, **context)

    def bounce(
        self,
        upstream: str,
        rule: str,
        reason: str,
        errors: list[str],
        **context: object,
    ) -> Decision:
        """Dispatch the producing agent with the exact gate errors."""
        return dispatch([upstream], rule, reason, self.req_id, errors=errors, **context)

    def blocked(
        self, rule: str, reason: str, errors: list[str] | None = None, **context: object
    ) -> Decision:
        """Halt this slice for the human."""
        return blocked(rule, reason, self.req_id, errors, **context)

    def escalate(self, rule: str, reason: str, **context: object) -> Decision:
        """Hand this slice to the coordinator's judgment."""
        return escalate(rule, reason, self.req_id, **context)


def route_decision(request: RouteInput, gate: GateChecker | None = None) -> Decision:
    """Decide the next step for one slice of the ledger."""
    checker = gate or SchemaGate(request.schemas_dir, request.layout)
    context = route_context(request, checker)
    if isinstance(context, Decision):
        return context
    return route_slice(context)


def route_context(request: RouteInput, gate: GateChecker) -> RouteContext | Decision:
    """Parse the log once and narrow it to the routed slice, or decide why that fails."""
    entries = request.entries
    if not entries:
        return escalate(
            "no-active-slice",
            "handoff log has no records; classify the request per the Agent Selection table",
        )
    req_id = request.req_id or entries[-1].raw.get("req_id")
    if not isinstance(req_id, str) or not req_id:
        return blocked(
            "missing-req-id", f"latest record (line {entries[-1].no}) carries no req_id"
        )
    log = typed_log(entries)
    records = tuple(entry for entry in log if entry.req_id == req_id)
    if not records:
        return blocked("unknown-req-id", f"no records for {req_id}", req_id)
    roster = reviewer_roster(request.layout)
    if roster.error or roster.roster is None:
        return blocked("layout-invalid", roster.error or "", req_id)
    return RouteContext(
        log=log,
        records=records,
        req_id=req_id,
        roster=roster.roster,
        layout=request.layout,
        non_goal_delta=request.non_goal_delta,
        unresolved_refactor=tuple(r for r in unresolved_refactor(log) if r != req_id),
        gate=gate,
    )


def route_slice(ctx: RouteContext) -> Decision:
    """Route one slice through its rows in precedence order."""
    return (
        _human_pause(ctx)
        or _last_record_row(ctx)
        or _truncation_row(ctx)
        or _pending_request_row(ctx)
        or _substantive_row(ctx)
    )


# --- the rows ---------------------------------------------------------------------


def _human_pause(ctx: RouteContext) -> Decision | None:
    """Hold the sticky pause of an unanswered human consultation anywhere on the log."""
    pending = pending_human_request(ctx.log)
    if pending is None or pending is ctx.records[-1]:
        return None
    request = pending.record
    assert isinstance(request, ConsultationRequest)
    req_id = pending.req_id
    return blocked(
        "human-consultation",
        f"consultation-request at line {pending.no} targets the human and "
        "has no response; the pause resolves only through the human's "
        'reply transcribed as the consultation-response (author "human") '
        "— a later record never supersedes it",
        req_id if isinstance(req_id, str) else None,
        requester=request.author,
        question=request.question,
    )


def _last_record_row(ctx: RouteContext) -> Decision | None:
    """Route on the slice's last record when its type alone decides."""
    last = ctx.records[-1]
    match last.record:
        case ConsultationRequest() as request:
            return _consultation_dispatch(ctx, last, request)
        case ConsultationResponse() as response:
            return _consultation_return(ctx, last, response)
        case GraderVerdict(verdict=verdict):
            return _graded_row(ctx, verdict)
        case GraderFeatures():
            return ctx.dispatch(
                [GRADER],
                "grade-continue",
                "grader-features recorded without a grader-verdict; re-dispatch the change-grader",
            )
        case (
            BuildPass()
            | BuildFailure()
            | ReviewFeedback()
            | ReviewPlan()
            | DesignBlock()
            | PrdEntry()
            | IntakeDecision()
            | DispatchStart()
            | DesignDocAutofix()
            | PrdAutofix()
            | UnknownRecord()
        ):
            return None
        case _ as unreachable:
            assert_never(unreachable)


def _graded_row(ctx: RouteContext, verdict: str | None) -> Decision:
    """Close the slice on its grader verdict, or resume the refactor it unblocked."""
    if ctx.unresolved_refactor:
        return ctx.dispatch(
            [DESIGNER],
            "refactor-resume",
            "refactor slice complete; re-triage the original slice with supersedes_record_at",
            original_req_id=ctx.unresolved_refactor[0],
            verdict=verdict,
        )
    return ctx.blocked(
        "feature-complete",
        "change-grader recorded its advisory verdict; human merge decision",
        verdict=verdict,
    )


def _truncation_row(ctx: RouteContext) -> Decision | None:
    """Recover a dispatch-start that no substantive record followed."""
    latest_start = ctx.latest(DispatchStart)
    if latest_start is None:
        return None
    grader_line = max(
        (
            e.no
            for e in ctx.records
            if isinstance(e.record, GraderVerdict | GraderFeatures)
        ),
        default=0,
    )
    followed = max(
        _line_of_entry(_latest_substantive(ctx)),
        _line_of_entry(_entry_of(ctx.latest(ConsultationRequest))),
        _line_of_entry(_entry_of(ctx.latest(ConsultationResponse))),
        grader_line,
    )
    if latest_start[0].no <= followed:
        return None
    author = latest_start[1].author
    if author == IMPLEMENTER:
        return _truncation_state(ctx)
    if author in ctx.roster or author == PLANNER:
        return _review_state(ctx)
    return ctx.escalate(
        "truncation-undefined",
        f"dispatch-start from {author} with no subsequent substantive record; no recovery row is defined for this agent",
        author=author,
    )


def _pending_request_row(ctx: RouteContext) -> Decision | None:
    """Dispatch a consultation-request newer than every substantive record and response."""
    latest_request = ctx.latest(ConsultationRequest)
    if latest_request is None:
        return None
    request_line = latest_request[0].no
    if request_line > _line_of_entry(
        _latest_substantive(ctx)
    ) and request_line > _line_of_entry(_entry_of(ctx.latest(ConsultationResponse))):
        return _consultation_dispatch(ctx, latest_request[0], latest_request[1])
    return None


def _substantive_row(ctx: RouteContext) -> Decision:
    """Route on the latest substantive record of the slice."""
    entry = _latest_substantive(ctx)
    if entry is None:
        return ctx.escalate(
            "no-substantive-record",
            "records exist but none is substantive; classify the state manually",
        )
    decision: Decision
    match entry.record:
        case BuildPass() | ReviewFeedback() | ReviewPlan():
            decision = _review_state(ctx)
        case BuildFailure():
            decision = _build_failure_state(ctx)
        case DesignBlock() as block:
            decision = _design_block_row(ctx, entry, block)
        case PrdEntry() as prd_entry:
            decision = _prd_entry_row(ctx, entry, prd_entry)
        case ConsultationResponse() as response:
            decision = _consultation_return(ctx, entry, response)
        case IntakeDecision():
            decision = _intake_row(ctx, entry)
        case (
            DispatchStart()
            | ConsultationRequest()
            | GraderVerdict()
            | GraderFeatures()
            | DesignDocAutofix()
            | PrdAutofix()
            | UnknownRecord()
        ):
            # Unreachable through the substantive selection; the arm keeps the
            # match exhaustive and the runtime fallback closed.
            decision = ctx.escalate(
                "unroutable-state",
                f"latest substantive record type '{entry.type_name}' matched no table row",
            )
        case _ as unreachable:
            assert_never(unreachable)
    return decision


def _latest_substantive(ctx: RouteContext) -> Entry | None:
    return next(
        (e for e in reversed(ctx.records) if isinstance(e.record, SUBSTANTIVE_CLASSES)),
        None,
    )


def _line_of_entry(entry: Entry | None) -> int:
    return entry.no if entry else 0


def _entry_of(found: tuple[Entry, HandoffRecord] | None) -> Entry | None:
    return found[0] if found else None


# --- the review phase -------------------------------------------------------------


def _review_state(ctx: RouteContext) -> Decision:
    """Route the phase after a build-pass: reviews, findings, grading, completion."""
    build_pass = ctx.latest(BuildPass)
    if build_pass is None:
        return ctx.escalate(
            "review-without-build-pass",
            "review activity with no build-pass record for this slice",
        )
    build_pass_line = build_pass[0].no
    errors = ctx.gate_errors(build_pass[0], "build-pass")
    if errors:
        return ctx.bounce(
            IMPLEMENTER,
            "build-record-invalid",
            f"build-pass at line {build_pass_line} failed its gate; re-dispatch the implementer",
            errors,
        )
    if escalate_precedes_pass(ctx.records, build_pass_line):
        return ctx.blocked(
            "escalate-finding-halt",
            "an escalate finding preceded this build-pass; the human decides before reviews re-run",
        )
    roster = pass_roster(ctx.records, build_pass_line, ctx.roster)
    if isinstance(roster, PlannerStep):
        return _planner_decision(ctx, roster)
    review = _review_pass(ctx, build_pass_line, roster)
    ladder = reviewer_ladder(review)
    decision = _ladder_decision(ctx, review, ladder) or _feedback_gate(
        ctx, review, ladder.feedback
    )
    if decision is not None:
        return decision
    verdicts = {
        reviewer: entry.record
        for reviewer, entry in ladder.feedback.items()
        if isinstance(entry.record, ReviewFeedback)
    }
    return (
        _ceiling_decision(ctx, review, verdicts)
        or _findings_dispatch(ctx, review, verdicts)
        or _outstanding_dissent_decision(ctx, review)
        or _completion(ctx, review)
    )


def _review_pass(
    ctx: RouteContext, build_pass_line: int, roster: PassRoster
) -> ReviewPass:
    """Assemble the current pass from the slice's cycle and the resolved roster."""
    start = cycle_start(ctx.records)
    return ReviewPass(
        ctx.records,
        build_pass_line,
        start,
        cycle_round(ctx.records, start, build_pass_line, ctx.roster),
        roster.reviewers,
        roster.gap,
        ctx.roster,
    )


def _planner_decision(ctx: RouteContext, step: PlannerStep) -> Decision:
    """Turn the planner's ladder step into its dispatch, bounce, or halt."""
    match step.kind:
        case "plan-gray-invalid":
            return ctx.bounce(
                PLANNER,
                "plan-gray-invalid",
                f"review-plan at line {step.plan_line} is gray but not engine-authored; only the engine defers",
                ["review-planner emitted risk 'gray'; it must resolve to low or high"],
            )
        case "plan-gray":
            return ctx.dispatch(
                [PLANNER],
                "plan-gray",
                "review-plan is gray; dispatch the review-planner to resolve the roster",
            )
        case "planner-stall-retry":
            return ctx.dispatch(
                [PLANNER],
                "planner-stall-retry",
                "review-planner returned without a plan; re-dispatch once",
            )
        case "planner-stalled":
            return ctx.blocked(
                "planner-stalled",
                "review-planner produced no plan after the stall retry; resolve manually",
            )
        case "plan-roster-invalid":
            return ctx.bounce(
                PLANNER,
                "plan-roster-invalid",
                f"review-plan at line {step.plan_line} from the planner names no roster; "
                "it must name a non-empty subset of the full roster",
                ["review-planner emitted a plan with no roster field"],
            )
        case _ as unreachable:
            assert_never(unreachable)


def _ladder_decision(
    ctx: RouteContext, review: ReviewPass, ladder: ReviewerLadder
) -> Decision | None:
    """Dispatch or block on the reviewer ladder; None when every reviewer has current feedback."""
    if ladder.stalled:
        return ctx.blocked(
            "reviewer-stalled",
            "reviewer(s) produced no current review-feedback record after the stall retry; append the escalation and stop",
            stalled=list(ladder.stalled),
        )
    round_context = review.round_context()
    if ladder.undispatched and not ladder.feedback and not ladder.retry_once:
        return ctx.dispatch(
            review.reviewers,
            "reviews-needed",
            _reviews_needed_reason(review.roster_gap),
            **round_context,
        )
    if ladder.retry_once:
        return ctx.dispatch(
            [*ladder.retry_once, *ladder.undispatched],
            "reviewer-stall-retry",
            "reviewer(s) returned without a current review-feedback record; re-dispatch once per the Reviewer Stall Check",
            **round_context,
        )
    if ladder.undispatched:
        return ctx.dispatch(
            ladder.undispatched,
            "reviews-needed",
            "roster reviewer(s) have not been dispatched since build-pass",
            **round_context,
        )
    return None


def _reviews_needed_reason(gap: RosterGap | None) -> str:
    """Name the fail-closed gap so a full battery is never mistaken for a deliberate one."""
    match gap:
        case "no-plan":
            return "build-pass gated with no review-plan on record; fail-closed to the full battery"
        case "invalid-plan":
            return (
                "build-pass gated on a review-plan with an empty or unknown "
                "roster; fail-closed to the full battery"
            )
        case "unauthored-plan":
            return (
                "build-pass gated on a review-plan neither the engine nor a "
                "dispatched planner authored; fail-closed to the full battery"
            )
        case None:
            return "build-pass gated; dispatch the resolved pass roster in parallel"
        case _ as unreachable:
            assert_never(unreachable)


def _feedback_gate(
    ctx: RouteContext, review: ReviewPass, feedback: Mapping[str, Entry]
) -> Decision | None:
    """Bounce the first reviewer whose feedback fails Gate 4; block a repeated below-bar dissent."""
    for reviewer, entry in feedback.items():
        errors = ctx.gate_errors(entry, "review-feedback")
        findings = raw_findings(entry)
        errors.extend(finding_shape_errors(entry, findings))
        if dissents_below_bar(review, entry, findings):
            if prior_below_bar_dissent(review, reviewer, entry):
                return ctx.blocked(
                    "review-non-convergence",
                    "reviewer re-dissented below the critical-only bar after its "
                    "bounce; the human settles the severity disagreement",
                    cause="bounce-repeat",
                    reviewer=reviewer,
                    round=review.round_no,
                )
            errors.append(
                f"non-critical dissent on a critical-only round (round {review.round_no}): a "
                "defect that must not merge is severity critical; residual polish "
                "rides recommendations on an approved verdict; a question rides "
                "clarify, a human decision rides escalate"
            )
        if errors:
            return ctx.bounce(
                reviewer,
                "review-record-invalid",
                f"review-feedback at line {entry.no} failed its gate; re-dispatch the reviewer",
                errors,
                **review.round_context(),
            )
    return None


def _ceiling_decision(
    ctx: RouteContext, review: ReviewPass, verdicts: Mapping[str, ReviewFeedback]
) -> Decision | None:
    """Stop a pass that is not converging, naming the cause the ladder found."""
    ceiling = dissent_ceiling(review, verdicts)
    if ceiling is None:
        return None
    match ceiling.cause:
        case "empty-findings":
            return ctx.dispatch(
                list(ceiling.reviewers),
                "reviewer-empty-findings",
                "non-approved verdict with no findings is not actionable; re-dispatch the reviewer",
                **review.round_context(),
            )
        case "pass-churn":
            return ctx.blocked(
                "review-non-convergence",
                "a reviewer dissented three times within one pass; the within-pass "
                "loop is not converging and the human decides",
                cause="pass-churn",
                round=review.round_no,
                dissenters=list(ceiling.reviewers),
            )
        case "round-cap":
            return _round_cap_block(ctx, review, ceiling)
        case "truncation-run":
            return ctx.blocked(
                "review-non-convergence",
                "three consecutive passes carried truncation-only dissent; the "
                "reviewer budget does not fit this surface — the human "
                "re-sizes the slice or re-triages",
                cause="truncation-run",
                round=review.round_no,
                dissenters=list(ceiling.reviewers),
            )
        case _ as unreachable:
            assert_never(unreachable)


def _round_cap_block(
    ctx: RouteContext, review: ReviewPass, ceiling: Ceiling
) -> Decision:
    """Block for the human once substantive dissent outlives the fix rounds a cycle buys."""
    context: dict[str, Any] = {
        "cause": "round-cap",
        "round": review.round_no,
        "dissenters": list(ceiling.reviewers),
    }
    if ceiling.escalate_findings:
        context["escalate_findings"] = ceiling.escalate_findings
    return ctx.blocked(
        "review-non-convergence",
        f"substantive dissent after {REVIEW_ROUND_CAP} fix rounds in this "
        "review cycle; the human decides — overrule, fix by hand, or "
        "order a re-triage (a superseding design-block resets the cycle); "
        "root appends any escalate findings to the escalations file first",
        **context,
    )


def _findings_dispatch(
    ctx: RouteContext, review: ReviewPass, verdicts: Mapping[str, ReviewFeedback]
) -> Decision | None:
    """Dispatch dissenting findings to their artifact owners; None when every verdict approves cleanly."""
    non_approved = {r: fb for r, fb in verdicts.items() if fb.verdict != APPROVED}
    escalate_tags = escalate_count(verdicts)
    if not non_approved:
        if escalate_tags:
            return ctx.blocked(
                "escalate-on-approved",
                "approved verdicts carry escalate-tagged finding(s); root appends the escalation entry and halts",
                escalate_findings=escalate_tags,
            )
        return None
    split = owner_split(verdicts, non_approved)
    owners = [o for o in OWNER_ORDER if o in split.owners]
    if not owners:
        return ctx.escalate(
            "autofix-only-round",
            "every finding is a root-applied doc autofix; root applies them and the coordinator decides the re-review",
            root_autofix=split.root_autofix,
        )
    context: dict[str, Any] = {
        "reviewers": sorted(non_approved),
        "escalate_findings": escalate_tags,
        "root_autofix": split.root_autofix,
        "round": review.round_no,
    }
    if escalate_tags:
        context["halt_after"] = True
    if IMPLEMENTER in owners:
        tier = implementer_tier(review.records)
        owners[owners.index(IMPLEMENTER)] = tier.agent
        context["tier_reason"] = tier.reason
    return ctx.dispatch(
        owners,
        "process-findings",
        "findings dispatch to their artifact owners; halt after processing when an escalate finding is present",
        **context,
    )


def _outstanding_dissent_decision(
    ctx: RouteContext, review: ReviewPass
) -> Decision | None:
    """Re-dispatch a cycle reviewer whose latest verdict dissents and whom the pass roster dropped."""
    outstanding = outstanding_dissent(review)
    if outstanding is None:
        return None
    if outstanding.stalled:
        return ctx.blocked(
            "reviewer-stalled",
            "outstanding dissenter(s) produced no fresh review-feedback after "
            "re-dispatch; append the escalation and stop",
            stalled=list(outstanding.stalled),
        )
    # No finding bar rides this dispatch: Gate 4 never checks this path's
    # records, so an advertised bar would go unenforced.
    return ctx.dispatch(
        list(outstanding.reviewers),
        "outstanding-dissent",
        "prior reviewer(s) dissented and the plan did not re-include them; "
        "dispatch them to resolve before completion",
        round=review.round_no,
        prompt_note=f"Review round {review.round_no}.",
    )


def _completion(ctx: RouteContext, review: ReviewPass) -> Decision:
    """Grade an approved pass, or close the slice when grading is done or disabled."""
    unresolved = ctx.unresolved_refactor
    graded = ctx.latest(GraderVerdict)
    if graded is not None and graded[0].no > review.build_pass_line:
        if unresolved:
            return ctx.dispatch(
                [DESIGNER],
                "refactor-resume",
                "refactor slice complete; re-triage the original slice with supersedes_record_at",
                original_req_id=unresolved[0],
                verdict=graded[1].verdict,
            )
        return ctx.blocked(
            "feature-complete",
            "all roster reviewers approved and the change-grader recorded its advisory verdict; human merge decision",
            verdict=graded[1].verdict,
        )
    if not auto_grade(ctx.layout):
        if unresolved:
            return ctx.dispatch(
                [DESIGNER],
                "refactor-resume",
                "refactor slice complete (grading disabled); re-triage the original slice with supersedes_record_at",
                original_req_id=unresolved[0],
            )
        return ctx.blocked(
            "feature-complete",
            "all roster reviewers approved; change grading disabled (auto_grade = false) — "
            "run the change-grading skill by hand if wanted; human merge decision",
        )
    return ctx.dispatch(
        [GRADER],
        "grade",
        "all roster reviewers approved; dispatch the terminal advisory change-grader",
    )


# --- consultations ----------------------------------------------------------------


def _consultation_dispatch(
    ctx: RouteContext, entry: Entry, request: ConsultationRequest
) -> Decision:
    """Dispatch a consultation-request's target, or halt for the human."""
    errors = ctx.gate_errors(entry, "consultation-request")
    target = request.target
    if not isinstance(target, str) or not target:
        errors.append("consultation-request names no target specialist")
    if errors:
        return _request_invalid(
            ctx,
            request,
            errors,
            f"consultation-request at line {entry.no} failed its gate",
        )
    assert isinstance(target, str)
    if target.strip().casefold() == HUMAN:
        return _human_consultation(ctx, entry, request, target)
    return ctx.dispatch(
        [target],
        "consultation-dispatch",
        "pending consultation-request; dispatch the target in consultation mode",
        requester=request.author,
    )


def _request_invalid(
    ctx: RouteContext, request: ConsultationRequest, errors: list[str], reason: str
) -> Decision:
    """Bounce the author of an invalid consultation-request, or block when it names none."""
    author = request.author
    if isinstance(author, str) and author:
        return ctx.bounce(
            author, "consultation-invalid", reason + "; re-dispatch its author", errors
        )
    return ctx.blocked("consultation-invalid", reason, errors)


def _human_consultation(
    ctx: RouteContext, entry: Entry, request: ConsultationRequest, target: str
) -> Decision:
    """Halt for the human's reply; the contract wants the exact target spelling."""
    if request.author == HUMAN:
        return ctx.blocked(
            "consultation-invalid",
            f'consultation-request at line {entry.no} is authored by "human"; no agent to resume',
        )
    if target != HUMAN:
        message = (
            f'consultation-request at line {entry.no} target must be exactly "human"'
        )
        return _request_invalid(ctx, request, [message], message)
    return ctx.blocked(
        "human-consultation",
        f"consultation-request at line {entry.no} targets the human; converse, then append "
        'the consultation-response (author "human") transcribing the reply; '
        "absent a reply the halt stands — root never answers on the human's behalf",
        requester=request.author,
        question=request.question,
    )


def _consultation_return(
    ctx: RouteContext, entry: Entry, response: ConsultationResponse
) -> Decision:
    """Route control back to the specialist whose request the response answers."""
    errors = ctx.gate_errors(entry, "consultation-response")
    request_entry = ctx.entry_at(response.in_response_to)
    request = request_entry.record if request_entry is not None else None
    if not isinstance(request, ConsultationRequest):
        errors.append(
            f"in_response_to ({response.in_response_to}) does not point at a consultation-request line"
        )
    elif response.author != request.target:
        errors.append(
            "consultation-response author does not match the request's target"
        )
    elif not isinstance(request.author, str) or not request.author:
        errors.append(
            "the corresponding consultation-request names no author to return to"
        )
    if errors:
        return _response_invalid(ctx, entry, request_entry, errors)
    assert isinstance(request, ConsultationRequest)
    assert isinstance(request.author, str)
    if request.author == HUMAN:
        return ctx.blocked(
            "consultation-invalid",
            f"consultation-request at line {response.in_response_to} is authored by "
            '"human"; no agent to resume',
        )
    return ctx.dispatch(
        [request.author],
        "consultation-return",
        "route control back to the requesting specialist; do not advance the pipeline",
        resume=True,
    )


def _response_invalid(
    ctx: RouteContext, entry: Entry, request_entry: Entry | None, errors: list[str]
) -> Decision:
    """Bounce the responder the pointed-at line names, or block when it names none."""
    # The pointed-at record need not be a request, yet its raw target still
    # names the responder to re-dispatch.
    responder = request_entry.raw.get("target") if request_entry is not None else None
    reason = f"consultation-response at line {entry.no} failed its gate"
    if isinstance(responder, str) and responder:
        return ctx.bounce(
            responder,
            "consultation-invalid",
            reason + "; re-dispatch the responder",
            errors,
        )
    return ctx.blocked("consultation-invalid", reason, errors)


# --- recovery states ---------------------------------------------------------------


def _build_failure_state(ctx: RouteContext) -> Decision:
    """Route after a build-failure: abort, retry, or re-triage."""
    found = ctx.latest(BuildFailure)
    assert found is not None
    entry, failure = found
    errors = ctx.gate_errors(entry, "build-failure")
    if errors:
        return ctx.bounce(
            IMPLEMENTER,
            "build-record-invalid",
            f"build-failure at line {entry.no} failed its gate; re-dispatch the implementer",
            errors,
        )
    if failure.abort_reason:
        return _abort_decision(ctx, failure.abort_reason)
    design = ctx.latest(DesignBlock)
    if design is None:
        return ctx.escalate(
            "failure-without-design",
            "build-failure exists but no design-block precedes it",
        )
    failures = failures_since(ctx.records, design[0].no)
    if failures < RETRY_CAP:
        tier = implementer_tier(ctx.records)
        return ctx.dispatch(
            [tier.agent],
            "build-retry",
            f"quality gate failed; re-dispatch with error context (this is retry {failures} of {RETRY_CAP})",
            retry=failures,
            partial=bool(failure.partial),
            tier_reason=tier.reason,
        )
    return ctx.dispatch(
        [DESIGNER],
        "build-non-convergence",
        "three gate failures since the latest design-block; re-triage with supersedes_record_at",
        failures=failures,
    )


def _abort_decision(ctx: RouteContext, abort_reason: str) -> Decision:
    """Route an implementer abort to the owner of the mismatch it names."""
    if abort_reason == "wrong-shape-slice":
        return ctx.dispatch(
            [PRODUCT],
            "abort-wrong-shape",
            "implementer aborted: slice cannot be implemented as scoped; re-split",
        )
    if abort_reason == "design-mismatch":
        return ctx.dispatch(
            [DESIGNER],
            "abort-design-mismatch",
            "implementer aborted: design does not match reality; re-triage with supersedes_record_at",
        )
    if abort_reason == "prd-mismatch":
        return ctx.dispatch(
            [PRODUCT],
            "abort-prd-mismatch",
            "autofix audit failed on a prd-autofix record; the PRD owner reconciles and a superseding prd-entry restarts the gate",
        )
    if abort_reason == "prerequisite-missing":
        return ctx.blocked(
            "abort-prerequisite",
            "implementer aborted on a missing external prerequisite; root appends the escalation and halts",
        )
    return ctx.escalate(
        "abort-unknown",
        f"build-failure carries unrecognized abort_reason '{abort_reason}'",
    )


def _truncation_state(ctx: RouteContext) -> Decision:
    """Continue a truncated implementer dispatch, or re-triage after a run of them."""
    design = ctx.latest(DesignBlock)
    if design is None:
        return ctx.escalate(
            "truncation-before-design",
            "implementer dispatch-start with no design-block on record",
        )
    run = truncation_run(ctx.records, design[0].no, IMPLEMENTER)
    if run < RETRY_CAP:
        # Recovery always runs the base pin: a truncation is a budget signal.
        return ctx.dispatch(
            [IMPLEMENTER],
            "truncation-continue",
            f"dispatch truncated before a substantive record; continue the same slice (continuation {run} of {RETRY_CAP})",
            continuation=run,
            tier_reason="recovery",
        )
    return ctx.dispatch(
        [DESIGNER],
        "truncation-non-convergence",
        "three consecutive truncated dispatches with no implementer record; re-triage per Truncation Recovery",
        continuations=run,
    )


# --- the gates --------------------------------------------------------------------


def _intake_row(ctx: RouteContext, entry: Entry) -> Decision:
    """Gate the intake decision; its author is the human, so a failure halts for the owner."""
    errors = ctx.gate_errors(entry, "intake-decision")
    if errors:
        return ctx.blocked(
            "intake-record-invalid",
            f"intake-decision at line {entry.no} failed its gate; the owner re-records the intake",
            errors=errors,
        )
    return ctx.dispatch(
        [PRODUCT],
        "intake-ready",
        "intake decisions recorded; author the slice grounded in the "
        "quoted intake. A request conflicting with recorded non-goals "
        "still dispatches: the expert's recorded consultation-request "
        "is the only refusal exit",
    )


def _design_block_row(ctx: RouteContext, entry: Entry, block: DesignBlock) -> Decision:
    """Gate 2: dispatch the implementer on an implementable verdict, else bounce or halt."""
    verdict = block.verdict
    if verdict == CONFLICTING_VERDICT:
        escalations = entry.raw.get("escalations", [])
        gap = (
            None
            if escalations
            else [
                "conflicting design-block carries no escalations (Gate 2 requires a non-empty array)"
            ]
        )
        return ctx.blocked(
            "design-conflict",
            "design-block verdict is conflicting; halt and surface the escalations to the user",
            errors=gap,
            escalations=escalations,
        )
    if verdict == REFACTOR_FIRST_VERDICT:
        return ctx.escalate(
            "refactor-first",
            "refactor-first verdict: the coordinator orders the refactor slice ahead of this one",
        )
    errors = ctx.gate_errors(entry, "design-block")
    errors.extend(_supersedes_errors(ctx, entry, block))
    if not errors and verdict not in IMPLEMENTABLE_VERDICTS:
        errors = [f"unknown design-block verdict '{verdict}'"]
    if errors:
        return ctx.bounce(
            DESIGNER,
            "design-gate-failed",
            f"design-block at line {entry.no} failed its gate; re-dispatch upstream",
            errors,
        )
    tier = implementer_tier(ctx.records)
    return ctx.dispatch(
        [tier.agent],
        "design-approved",
        f"design-block verdict '{verdict}' passed its gate; dispatch the implementer",
        verdict=verdict,
        tier_reason=tier.reason,
    )


def _supersedes_errors(
    ctx: RouteContext, entry: Entry, block: DesignBlock
) -> list[str]:
    """Require a supersedes pointer to name a prior design-block line of this slice."""
    superseded = block.supersedes_record_at
    if superseded is None or superseded_design_block(entry, ctx.by_line) is not None:
        return []
    return [
        f"supersedes_record_at ({superseded!r}) does not point "
        "at a prior design-block line for this slice"
    ]


def _prd_entry_row(ctx: RouteContext, entry: Entry, prd_entry: PrdEntry) -> Decision:
    """Gate 1: dispatch the designer on a passing prd-entry, else bounce the product expert."""
    if prd_entry.author == DESIGNER:
        return ctx.escalate(
            "refactor-first",
            "designer-authored sibling prd-entry: the coordinator orders the refactor slice ahead of the original",
        )
    errors = ctx.gate_errors(entry, "prd-entry") or _scope_lock_errors(ctx, entry)
    if errors:
        return ctx.bounce(
            PRODUCT,
            "prd-gate-failed",
            f"prd-entry at line {entry.no} failed its gate; re-dispatch upstream",
            errors,
        )
    return ctx.dispatch(
        [DESIGNER],
        "prd-approved",
        "prd-entry passed its gate; dispatch the system-design-expert for triage",
    )


def _scope_lock_errors(ctx: RouteContext, entry: Entry) -> list[str]:
    """Check the prd-entry's scope overrides against the Non-Goals delta and the log's sources."""
    has_intake = any(
        isinstance(e.record, IntakeDecision) and e.record.author == HUMAN
        for e in ctx.log
    )
    sources = OverrideSources(ctx.req_id, has_intake, ctx.by_line)
    return scope_lock_errors(
        entry.raw.get("scope_overrides"), ctx.non_goal_delta, sources
    )
