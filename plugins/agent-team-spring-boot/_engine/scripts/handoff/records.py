#!/usr/bin/env python3
"""Type the ledger: one frozen record per handoff record type and the total, never-raising lift.

A leaf beside handoff.schema that also holds the pipeline vocabulary every reader shares.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, NamedTuple, TypeAlias, TypeVar

_T = TypeVar("_T")

# The mandatory reviewer floor; a layout's extra reviewers extend it.
ROSTER_FLOOR = (
    "code-quality-reviewer",
    "test-reviewer",
    "security-reviewer",
    "doc-reviewer",
)
# The record types that close a dispatch; a dispatch-start with none after it
# is a truncation.
SUBSTANTIVE = frozenset(
    (
        "build-pass",
        "build-failure",
        "review-feedback",
        "prd-entry",
        "design-block",
        "consultation-response",
        "review-plan",
        "intake-decision",
    )
)
IMPLEMENTER = "feature-implementer"
# The reduced-effort variant claims IMPLEMENTER as its record author, so this
# name appears in decisions and transcripts, never in the ledger.
ROUTINE_IMPLEMENTER = "feature-implementer-routine"
DESIGNER = "system-design-expert"
HUMAN = "human"
PRODUCT = "product-requirements-expert"
PLANNER = "review-planner"
PLAN_ENGINE = "review-plan-engine"
GRADER = "change-grader"
# Build retries and truncation continuations re-triage at the third strike;
# the build-failure schema pins the same bound.
RETRY_CAP = 3
# A review cycle buys at most this many fix rounds.
REVIEW_ROUND_CAP = 3


# Every field is optional: the lift never raises, so a reader degrades on a
# hole instead of failing on it. Scalars default None, arrays default (), a
# nullable array stays None as its own signal.


@dataclass(frozen=True, slots=True)
class MemoryUpdate:
    """A consultation-response memory_updates item."""

    path: str | None = None
    summary: str | None = None


@dataclass(frozen=True, slots=True)
class Pattern:
    """A design-block patterns item."""

    ref: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class Risk:
    """A design-block risks item."""

    risk: str | None = None
    mitigation: str | None = None


@dataclass(frozen=True, slots=True)
class SourceFinding:
    """A design-doc-autofix source_finding object."""

    review_feedback_author: str | None = None
    review_feedback_ts: str | None = None
    tag: str | None = None
    location: str | None = None
    description: str | None = None
    fix: str | None = None


@dataclass(frozen=True, slots=True)
class Finding:
    """A review-feedback findings item."""

    tag: str | None = None
    location: str | None = None
    description: str | None = None
    fix: str | None = None
    clarify_target: str | None = None
    severity: str | None = None
    bar_clause: str | None = None


@dataclass(frozen=True, slots=True)
class Facet:
    """One grader-verdict facet (#/definitions/facet)."""

    verdict: str | None = None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class Facets:
    """The grader-verdict facets container: the five named facets."""

    blast_radius: Facet | None = None
    semantic_surprise: Facet | None = None
    test_adequacy: Facet | None = None
    reviewer_hedging: Facet | None = None
    scope_deviation: Facet | None = None


@dataclass(frozen=True, slots=True)
class Features:
    """The grader-features features object."""

    base_ref: str | None = None
    head_ref: str | None = None
    head_kind: str | None = None
    files_changed: int | None = None
    module_count: int | None = None
    test_prod_ratio: float | None = None
    hunks: int | None = None
    build_passed: bool | None = None
    reviewers: dict[str, Any] | None = None
    build_retries: int | None = None
    consultations: int | None = None
    design_revisions: int | None = None
    files: tuple[object, ...] | None = None
    modules: tuple[object, ...] | None = None
    test_lines: int | None = None
    prod_lines: int | None = None
    sensitive_paths: tuple[object, ...] | None = None
    unknown_paths: tuple[object, ...] | None = None
    security_surface_paths: tuple[object, ...] | None = None
    churn: dict[str, Any] | None = None
    review_roster: tuple[object, ...] | None = None


@dataclass(frozen=True, slots=True)
class SecuritySurface:
    """The security-surface probe a plan carries: whether one is declared, and the production paths it hit."""

    declared: bool | None = None
    paths: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class PlanBasis:
    """The review-plan basis object; `pass` is a keyword, so the field is `pass_`."""

    tree_sha: str | None = None
    pass_: str | None = None
    prev_tree_sha: str | None = None
    files: tuple[object, ...] | None = None
    size: dict[str, Any] | None = None
    history: dict[str, Any] | None = None
    open_findings: tuple[object, ...] | None = None
    triggers: tuple[object, ...] | None = None
    security_surface: SecuritySurface | None = None


@dataclass(frozen=True, slots=True)
class ConsultationRequest:
    """The `consultation-request` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    target: str | None = None
    context: str | None = None
    question: str | None = None
    stop_state: str | None = None


@dataclass(frozen=True, slots=True)
class ConsultationResponse:
    """The `consultation-response` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    in_response_to: int | None = None
    answer: str | None = None
    memory_updates: tuple[MemoryUpdate, ...] = ()
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class DesignBlock:
    """The `design-block` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    verdict: str | None = None
    implementation_effort: str | None = None
    architectural_fit: str | None = None
    primary_paths: tuple[str, ...] = ()
    supporting_paths: tuple[str, ...] = ()
    integration_points: tuple[str, ...] = ()
    patterns: tuple[Pattern, ...] = ()
    risks: tuple[Risk, ...] = ()
    escalations: tuple[str, ...] = ()
    supersedes_record_at: int | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class DesignDocAutofix:
    """The `design-doc-autofix` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    file: str | None = None
    category: str | None = None
    source_finding: SourceFinding | None = None
    old_content: str | None = None
    new_content: str | None = None
    lines_changed: int | None = None
    chars_changed: int | None = None


@dataclass(frozen=True, slots=True)
class PrdAutofix:
    """The `prd-autofix` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    file: str | None = None
    category: str | None = None
    source_finding: SourceFinding | None = None
    old_content: str | None = None
    new_content: str | None = None
    lines_changed: int | None = None
    chars_changed: int | None = None


@dataclass(frozen=True, slots=True)
class DispatchStart:
    """The `dispatch-start` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    responding_to: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class GraderFeatures:
    """The `grader-features` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    features: Features | None = None


@dataclass(frozen=True, slots=True)
class GraderVerdict:
    """The `grader-verdict` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    responding_to: tuple[int, ...] = ()
    summary: str | None = None
    facets: Facets | None = None
    rationale: str | None = None
    verdict: str | None = None


@dataclass(frozen=True, slots=True)
class ReviewFeedback:
    """The `review-feedback` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    verdict: str | None = None
    findings: tuple[Finding, ...] = ()
    recommendations: tuple[str, ...] = ()
    approved_aspects: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReviewPlan:
    """The `review-plan` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    risk: str | None = None
    scope: str | None = None
    basis: PlanBasis | None = None
    rationale: str | None = None
    roster: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BuildFailure:
    """The `build-failure` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    retry: int | None = None
    failed_check: str | None = None
    error_output: str | None = None
    attempted: str | None = None
    partial: bool | None = None
    abort_reason: str | None = None


@dataclass(frozen=True, slots=True)
class BuildPass:
    """The `build-pass` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    gate_checks_run: tuple[str, ...] = ()
    duration_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class ScopeOverride:
    """One prd-entry scope override: the changed non-goal and the owner decision it quotes."""

    non_goal_id: str | None = None
    owner_decision: str | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True)
class PrdEntry:
    """The `prd-entry` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    title: str | None = None
    summary: str | None = None
    acceptance_criteria: tuple[str, ...] = ()
    file_targets: tuple[str, ...] = ()
    test_names: tuple[str, ...] = ()
    non_goals: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    notes: str | None = None
    scope_overrides: tuple[ScopeOverride, ...] = ()


@dataclass(frozen=True, slots=True)
class IntakeDecision:
    """The `intake-decision` record."""

    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    request: str | None = None
    decisions: tuple[str, ...] = ()
    source: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class UnknownRecord:
    """A record whose type is unknown, missing, or not a string; the raw object rides along."""

    raw: dict[str, Any]


HandoffRecord: TypeAlias = (
    ConsultationRequest
    | ConsultationResponse
    | DesignBlock
    | DesignDocAutofix
    | PrdAutofix
    | DispatchStart
    | GraderFeatures
    | GraderVerdict
    | ReviewFeedback
    | ReviewPlan
    | BuildFailure
    | BuildPass
    | PrdEntry
    | IntakeDecision
    | UnknownRecord
)


class RecordType(NamedTuple):
    """One registered record type: its class and the lift from a raw object."""

    cls: type[HandoffRecord]
    lift: Callable[[dict[str, Any]], HandoffRecord]


def parse_record(raw: dict[str, Any]) -> HandoffRecord:
    """Lift any object into its record; a known type always yields its class, never an exception."""
    record_type = raw.get("type")
    registered = RECORD_TYPES.get(record_type) if isinstance(record_type, str) else None
    return UnknownRecord(raw=raw) if registered is None else registered.lift(raw)


def _consultation_request(raw: dict[str, Any]) -> ConsultationRequest:
    return ConsultationRequest(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        target=raw.get("target"),
        context=raw.get("context"),
        question=raw.get("question"),
        stop_state=raw.get("stop_state"),
    )


def _consultation_response(raw: dict[str, Any]) -> ConsultationResponse:
    return ConsultationResponse(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        in_response_to=raw.get("in_response_to"),
        answer=raw.get("answer"),
        memory_updates=_object_tuple(raw.get("memory_updates"), _memory_update),
        notes=raw.get("notes"),
    )


def _design_block(raw: dict[str, Any]) -> DesignBlock:
    return DesignBlock(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        verdict=raw.get("verdict"),
        implementation_effort=raw.get("implementation_effort"),
        architectural_fit=raw.get("architectural_fit"),
        primary_paths=_scalar_tuple(raw.get("primary_paths")),
        supporting_paths=_scalar_tuple(raw.get("supporting_paths")),
        integration_points=_scalar_tuple(raw.get("integration_points")),
        patterns=_object_tuple(raw.get("patterns"), _pattern),
        risks=_object_tuple(raw.get("risks"), _risk),
        escalations=_scalar_tuple(raw.get("escalations")),
        supersedes_record_at=raw.get("supersedes_record_at"),
        notes=raw.get("notes"),
    )


def _design_doc_autofix(raw: dict[str, Any]) -> DesignDocAutofix:
    return DesignDocAutofix(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        file=raw.get("file"),
        category=raw.get("category"),
        source_finding=_opt_object(raw.get("source_finding"), _source_finding),
        old_content=raw.get("old_content"),
        new_content=raw.get("new_content"),
        lines_changed=raw.get("lines_changed"),
        chars_changed=raw.get("chars_changed"),
    )


def _prd_autofix(raw: dict[str, Any]) -> PrdAutofix:
    return PrdAutofix(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        file=raw.get("file"),
        category=raw.get("category"),
        source_finding=_opt_object(raw.get("source_finding"), _source_finding),
        old_content=raw.get("old_content"),
        new_content=raw.get("new_content"),
        lines_changed=raw.get("lines_changed"),
        chars_changed=raw.get("chars_changed"),
    )


def _dispatch_start(raw: dict[str, Any]) -> DispatchStart:
    return DispatchStart(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        responding_to=_scalar_tuple(raw.get("responding_to")),
    )


def _grader_features(raw: dict[str, Any]) -> GraderFeatures:
    return GraderFeatures(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        features=_opt_object(raw.get("features"), _features),
    )


def _grader_verdict(raw: dict[str, Any]) -> GraderVerdict:
    return GraderVerdict(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        responding_to=_scalar_tuple(raw.get("responding_to")),
        summary=raw.get("summary"),
        facets=_opt_object(raw.get("facets"), _facets),
        rationale=raw.get("rationale"),
        verdict=raw.get("verdict"),
    )


def _review_feedback(raw: dict[str, Any]) -> ReviewFeedback:
    return ReviewFeedback(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        verdict=raw.get("verdict"),
        findings=_object_tuple(raw.get("findings"), _finding),
        recommendations=_scalar_tuple(raw.get("recommendations")),
        approved_aspects=_scalar_tuple(raw.get("approved_aspects")),
    )


def _review_plan(raw: dict[str, Any]) -> ReviewPlan:
    return ReviewPlan(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        risk=raw.get("risk"),
        scope=raw.get("scope"),
        basis=_opt_object(raw.get("basis"), _plan_basis),
        rationale=raw.get("rationale"),
        roster=_scalar_tuple(raw.get("roster")),
    )


def _build_failure(raw: dict[str, Any]) -> BuildFailure:
    return BuildFailure(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        retry=raw.get("retry"),
        failed_check=raw.get("failed_check"),
        error_output=raw.get("error_output"),
        attempted=raw.get("attempted"),
        partial=raw.get("partial"),
        abort_reason=raw.get("abort_reason"),
    )


def _build_pass(raw: dict[str, Any]) -> BuildPass:
    return BuildPass(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        gate_checks_run=_scalar_tuple(raw.get("gate_checks_run")),
        duration_seconds=raw.get("duration_seconds"),
    )


def _intake_decision(raw: dict[str, Any]) -> IntakeDecision:
    return IntakeDecision(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        request=raw.get("request"),
        decisions=_scalar_tuple(raw.get("decisions")),
        source=raw.get("source"),
        notes=raw.get("notes"),
    )


def _prd_entry(raw: dict[str, Any]) -> PrdEntry:
    return PrdEntry(
        type=raw.get("type"),
        req_id=raw.get("req_id"),
        ts=raw.get("ts"),
        author=raw.get("author"),
        title=raw.get("title"),
        summary=raw.get("summary"),
        acceptance_criteria=_scalar_tuple(raw.get("acceptance_criteria")),
        file_targets=_scalar_tuple(raw.get("file_targets")),
        test_names=_scalar_tuple(raw.get("test_names")),
        non_goals=_scalar_tuple(raw.get("non_goals")),
        dependencies=_scalar_tuple(raw.get("dependencies")),
        notes=raw.get("notes"),
        scope_overrides=_object_tuple(raw.get("scope_overrides"), _scope_override),
    )


def _memory_update(raw: dict[str, Any]) -> MemoryUpdate:
    return MemoryUpdate(path=raw.get("path"), summary=raw.get("summary"))


def _pattern(raw: dict[str, Any]) -> Pattern:
    return Pattern(ref=raw.get("ref"), description=raw.get("description"))


def _risk(raw: dict[str, Any]) -> Risk:
    return Risk(risk=raw.get("risk"), mitigation=raw.get("mitigation"))


def _source_finding(raw: dict[str, Any]) -> SourceFinding:
    return SourceFinding(
        review_feedback_author=raw.get("review_feedback_author"),
        review_feedback_ts=raw.get("review_feedback_ts"),
        tag=raw.get("tag"),
        location=raw.get("location"),
        description=raw.get("description"),
        fix=raw.get("fix"),
    )


def _finding(raw: dict[str, Any]) -> Finding:
    return Finding(
        tag=raw.get("tag"),
        location=raw.get("location"),
        description=raw.get("description"),
        fix=raw.get("fix"),
        clarify_target=raw.get("clarify_target"),
        severity=raw.get("severity"),
        bar_clause=raw.get("bar_clause"),
    )


def _facet(raw: dict[str, Any]) -> Facet:
    return Facet(verdict=raw.get("verdict"), note=raw.get("note"))


def _facets(raw: dict[str, Any]) -> Facets:
    return Facets(
        blast_radius=_opt_object(raw.get("blast_radius"), _facet),
        semantic_surprise=_opt_object(raw.get("semantic_surprise"), _facet),
        test_adequacy=_opt_object(raw.get("test_adequacy"), _facet),
        reviewer_hedging=_opt_object(raw.get("reviewer_hedging"), _facet),
        scope_deviation=_opt_object(raw.get("scope_deviation"), _facet),
    )


def _features(raw: dict[str, Any]) -> Features:
    return Features(
        base_ref=raw.get("base_ref"),
        head_ref=raw.get("head_ref"),
        head_kind=raw.get("head_kind"),
        files_changed=raw.get("files_changed"),
        module_count=raw.get("module_count"),
        test_prod_ratio=raw.get("test_prod_ratio"),
        hunks=raw.get("hunks"),
        build_passed=raw.get("build_passed"),
        reviewers=raw.get("reviewers"),
        build_retries=raw.get("build_retries"),
        consultations=raw.get("consultations"),
        design_revisions=raw.get("design_revisions"),
        files=_opt_tuple(raw.get("files")),
        modules=_opt_tuple(raw.get("modules")),
        test_lines=raw.get("test_lines"),
        prod_lines=raw.get("prod_lines"),
        sensitive_paths=_opt_tuple(raw.get("sensitive_paths")),
        unknown_paths=_opt_tuple(raw.get("unknown_paths")),
        security_surface_paths=_opt_tuple(raw.get("security_surface_paths")),
        churn=raw.get("churn"),
        review_roster=_opt_tuple(raw.get("review_roster")),
    )


def _plan_basis(raw: dict[str, Any]) -> PlanBasis:
    return PlanBasis(
        tree_sha=raw.get("tree_sha"),
        pass_=raw.get("pass"),
        prev_tree_sha=raw.get("prev_tree_sha"),
        files=_opt_tuple(raw.get("files")),
        size=raw.get("size"),
        history=raw.get("history"),
        open_findings=_opt_tuple(raw.get("open_findings")),
        triggers=_opt_tuple(raw.get("triggers")),
        security_surface=_security_surface(raw.get("security_surface")),
    )


def _security_surface(raw: object) -> SecuritySurface | None:
    if not isinstance(raw, dict):
        return None
    paths = raw.get("paths")
    return SecuritySurface(
        declared=raw.get("declared"),
        paths=tuple(str(p) for p in paths) if isinstance(paths, list) else None,
    )


def _scope_override(raw: dict[str, Any]) -> ScopeOverride:
    return ScopeOverride(
        non_goal_id=raw.get("non_goal_id"),
        owner_decision=raw.get("owner_decision"),
        source=raw.get("source"),
    )


def _opt_tuple(value: object) -> tuple[Any, ...] | None:
    """Lift a nullable array: a list becomes a tuple, anything else None."""
    return tuple(value) if isinstance(value, list) else None


def _scalar_tuple(value: object) -> tuple[Any, ...]:
    """Lift a scalar array: a list becomes a tuple, anything else an empty tuple."""
    return tuple(value) if isinstance(value, list) else ()


def _object_tuple(
    value: object, lift: Callable[[dict[str, Any]], _T]
) -> tuple[_T, ...]:
    """Lift an object array: each dict item through `lift`, other items dropped."""
    if isinstance(value, list):
        return tuple(lift(item) for item in value if isinstance(item, dict))
    return ()


def _opt_object(value: object, lift: Callable[[dict[str, Any]], _T]) -> _T | None:
    """Single-nested-object lift: lift only when the raw value is a dict; else None."""
    return lift(value) if isinstance(value, dict) else None


RECORD_TYPES: dict[str, RecordType] = {
    "consultation-request": RecordType(ConsultationRequest, _consultation_request),
    "consultation-response": RecordType(ConsultationResponse, _consultation_response),
    "design-block": RecordType(DesignBlock, _design_block),
    "design-doc-autofix": RecordType(DesignDocAutofix, _design_doc_autofix),
    "prd-autofix": RecordType(PrdAutofix, _prd_autofix),
    "dispatch-start": RecordType(DispatchStart, _dispatch_start),
    "grader-features": RecordType(GraderFeatures, _grader_features),
    "grader-verdict": RecordType(GraderVerdict, _grader_verdict),
    "review-feedback": RecordType(ReviewFeedback, _review_feedback),
    "review-plan": RecordType(ReviewPlan, _review_plan),
    "build-failure": RecordType(BuildFailure, _build_failure),
    "build-pass": RecordType(BuildPass, _build_pass),
    "prd-entry": RecordType(PrdEntry, _prd_entry),
    "intake-decision": RecordType(IntakeDecision, _intake_decision),
}

SUBSTANTIVE_CLASSES = tuple(RECORD_TYPES[t].cls for t in sorted(SUBSTANTIVE))
