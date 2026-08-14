#!/usr/bin/env python3
"""handoff/records.py — the typed record model (ADR 2026-07-17 runtime-package-layout).

Trust class: a bottom layer beside handoff.schema. It owns the frozen dataclass
per handoff record type, the HandoffRecord union, the lenient lifts, the
type->dataclass / type->mapper registries, and parse_record — the total,
never-raising parse boundary that turns any dict into its dataclass. It also
holds the pipeline's domain vocabulary (the agent-author names, the reviewer
floor, the substantive-type set, the retry cap) that route, view, and the CLI
share, so those constants sit below both middle layers.

Imports nothing project-local. Stdlib only, Python 3.11+.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeAlias, TypeVar

# The mandatory reviewer floor (handoff-routing skill, Gate 4). layout.toml
# [harness].extra_reviewers extends it; nothing removes a floor reviewer.
ROSTER_FLOOR = (
    "code-quality-reviewer",
    "test-reviewer",
    "security-reviewer",
    "doc-reviewer",
)
# Substantive record types (handoff-routing skill, Dispatch Truncation Detection).
# review-plan is substantive: the implementer's engine run and the planner's
# resolution both close their dispatch with one, so a dispatch-start followed by
# a review-plan is a completed dispatch, not a truncation. intake-decision is
# substantive so a freshly seeded log routes (rule intake-ready) instead of
# escalating as no-substantive-record. No dispatch closes with it; a re-intake
# recorded mid-slice deliberately re-steers the slice to the product expert.
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
DESIGNER = "system-design-expert"
HUMAN = "human"
PRODUCT = "product-requirements-expert"
PLANNER = "review-planner"
PLAN_ENGINE = "review-plan-engine"
GRADER = "change-grader"
# Both recovery ladders re-triage at the third strike: build-failure retries
# and truncation continuations (route-spec §§ Build-Failure Recovery /
# Truncation Recovery). The core build-failure schema pins retry.maximum to
# the same value — change both together.
RETRY_CAP = 3
# The review ladder converges at the same depth: a review cycle buys at most
# three fix rounds. Substantive dissent arriving after the third fix round
# blocks as review-non-convergence for the human — review buys defect removal,
# and a cycle still dissenting at that depth is churning, not converging
# (route-spec § Review Non-Convergence).
REVIEW_ROUND_CAP = 3


# ---------------------------------------------------------------------------
# Typed record model (ADR 2026-07-17).
#
# One frozen, slotted dataclass per handoff record type mirrors its JSON schema
# in schemas/scratch/. parse_record turns any dict into its dataclass through
# one lenient lift per type. Raw dicts survive at this boundary and at the
# routing core's three sanctioned uses (see Entry); logic reads typed fields.
#
# Every field is optional because every reader of the handoff log is lenient by
# contract — route gates and bounces malformed records, view renders holes,
# --schemas is caller-supplied. The model gives typed .get() semantics, not
# schema-requiredness: the schema validator above alone owns requiredness. A
# mapper never raises on a missing or ill-typed field; it lifts what fits and
# leaves the rest at its default.
#
# Field conventions: scalars are T | None, default None. Non-nullable arrays are
# tuple[X, ...], default (). A schema field typed ["array", "null"]
# (grader-features / review-plan basis, where null is a load-bearing "input
# missing" signal) stays tuple[object, ...] | None, default None. Nested objects
# are Cls | None, default None. Arrays are tuple[...], never list, so the model
# stays immutable. The schema↔dataclass field-set parity is a tested drift gate
# (test_handoff.py).
# ---------------------------------------------------------------------------


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
    """The grader-features features object. Every field is optional per the
    lenient model; scalars default None, nullable arrays default None."""

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
    churn: dict[str, Any] | None = None
    review_roster: tuple[object, ...] | None = None


@dataclass(frozen=True, slots=True)
class PlanBasis:
    """The review-plan basis object. `pass` is a Python keyword, so the field
    is `pass_`; the parity test and mapper bridge the rename."""

    tree_sha: str | None = None
    pass_: str | None = None
    prev_tree_sha: str | None = None
    files: tuple[object, ...] | None = None
    size: dict[str, Any] | None = None
    history: dict[str, Any] | None = None
    open_findings: tuple[object, ...] | None = None
    triggers: tuple[object, ...] | None = None


@dataclass(frozen=True, slots=True)
class ConsultationRequest:
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
    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    verdict: str | None = None
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
    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    responding_to: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class GraderFeatures:
    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    features: Features | None = None


@dataclass(frozen=True, slots=True)
class GraderVerdict:
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
    # roster (absent on a gray plan) is grouped last; every field is optional
    # under the lenient model, so declaration order is unconstrained.
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
    type: str | None = None
    req_id: str | None = None
    ts: str | None = None
    author: str | None = None
    gate_checks_run: tuple[str, ...] = ()
    duration_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class ScopeOverride:
    """A prd-entry scope_overrides item: the owner's recorded decision behind
    one changed Non-Goals row (Gate 1 scope-lock)."""

    non_goal_id: str | None = None
    owner_decision: str | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True)
class PrdEntry:
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
    """The recorded intake: the owner's request and decisions, quoted verbatim
    by whichever front door ran (interactive persona discussion or headless
    seeding). The prd-entry that follows grounds in these quotes."""

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
    """The graceful-degradation fallback. parse_record returns this for any dict
    whose "type" is unrecognized or whose payload does not fit its dataclass —
    never an exception. raw keeps the original dict for the reader's fallback view."""

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


_T = TypeVar("_T")


def _opt_tuple(value: Any) -> tuple[Any, ...] | None:
    """Nullable-array lenient lift: a list becomes a tuple as-is; null or any
    other shape becomes None (the union admits null as a load-bearing signal)."""
    return tuple(value) if isinstance(value, list) else None


def _scalar_tuple(value: Any) -> tuple[Any, ...]:
    """Non-nullable scalar-array lift: a list becomes a tuple as-is (items
    uncoerced — the parse boundary is Any); any other shape becomes ()."""
    return tuple(value) if isinstance(value, list) else ()


def _object_tuple(value: Any, lift: Callable[[dict[str, Any]], _T]) -> tuple[_T, ...]:
    """Object-array lift: over a list, lift each dict item and skip the rest
    (mirrors the isinstance(x, dict) guards in the consumers); else ()."""
    if isinstance(value, list):
        return tuple(lift(item) for item in value if isinstance(item, dict))
    return ()


def _opt_object(value: Any, lift: Callable[[dict[str, Any]], _T]) -> _T | None:
    """Single-nested-object lift: lift only when the raw value is a dict; else None."""
    return lift(value) if isinstance(value, dict) else None


def _memory_update(d: dict[str, Any]) -> MemoryUpdate:
    return MemoryUpdate(path=d.get("path"), summary=d.get("summary"))


def _pattern(d: dict[str, Any]) -> Pattern:
    return Pattern(ref=d.get("ref"), description=d.get("description"))


def _risk(d: dict[str, Any]) -> Risk:
    return Risk(risk=d.get("risk"), mitigation=d.get("mitigation"))


def _source_finding(d: dict[str, Any]) -> SourceFinding:
    return SourceFinding(
        review_feedback_author=d.get("review_feedback_author"),
        review_feedback_ts=d.get("review_feedback_ts"),
        tag=d.get("tag"),
        location=d.get("location"),
        description=d.get("description"),
        fix=d.get("fix"),
    )


def _finding(d: dict[str, Any]) -> Finding:
    return Finding(
        tag=d.get("tag"),
        location=d.get("location"),
        description=d.get("description"),
        fix=d.get("fix"),
        clarify_target=d.get("clarify_target"),
        severity=d.get("severity"),
        bar_clause=d.get("bar_clause"),
    )


def _facet(d: dict[str, Any]) -> Facet:
    return Facet(verdict=d.get("verdict"), note=d.get("note"))


def _facets(d: dict[str, Any]) -> Facets:
    return Facets(
        blast_radius=_opt_object(d.get("blast_radius"), _facet),
        semantic_surprise=_opt_object(d.get("semantic_surprise"), _facet),
        test_adequacy=_opt_object(d.get("test_adequacy"), _facet),
        reviewer_hedging=_opt_object(d.get("reviewer_hedging"), _facet),
        scope_deviation=_opt_object(d.get("scope_deviation"), _facet),
    )


def _features(d: dict[str, Any]) -> Features:
    return Features(
        base_ref=d.get("base_ref"),
        head_ref=d.get("head_ref"),
        head_kind=d.get("head_kind"),
        files_changed=d.get("files_changed"),
        module_count=d.get("module_count"),
        test_prod_ratio=d.get("test_prod_ratio"),
        hunks=d.get("hunks"),
        build_passed=d.get("build_passed"),
        reviewers=d.get("reviewers"),
        build_retries=d.get("build_retries"),
        consultations=d.get("consultations"),
        design_revisions=d.get("design_revisions"),
        files=_opt_tuple(d.get("files")),
        modules=_opt_tuple(d.get("modules")),
        test_lines=d.get("test_lines"),
        prod_lines=d.get("prod_lines"),
        sensitive_paths=_opt_tuple(d.get("sensitive_paths")),
        unknown_paths=_opt_tuple(d.get("unknown_paths")),
        churn=d.get("churn"),
        review_roster=_opt_tuple(d.get("review_roster")),
    )


def _plan_basis(d: dict[str, Any]) -> PlanBasis:
    return PlanBasis(
        tree_sha=d.get("tree_sha"),
        pass_=d.get("pass"),
        prev_tree_sha=d.get("prev_tree_sha"),
        files=_opt_tuple(d.get("files")),
        size=d.get("size"),
        history=d.get("history"),
        open_findings=_opt_tuple(d.get("open_findings")),
        triggers=_opt_tuple(d.get("triggers")),
    )


def _consultation_request(rec: dict[str, Any]) -> ConsultationRequest:
    return ConsultationRequest(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        target=rec.get("target"),
        context=rec.get("context"),
        question=rec.get("question"),
        stop_state=rec.get("stop_state"),
    )


def _consultation_response(rec: dict[str, Any]) -> ConsultationResponse:
    return ConsultationResponse(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        in_response_to=rec.get("in_response_to"),
        answer=rec.get("answer"),
        memory_updates=_object_tuple(rec.get("memory_updates"), _memory_update),
        notes=rec.get("notes"),
    )


def _design_block(rec: dict[str, Any]) -> DesignBlock:
    return DesignBlock(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        verdict=rec.get("verdict"),
        architectural_fit=rec.get("architectural_fit"),
        primary_paths=_scalar_tuple(rec.get("primary_paths")),
        supporting_paths=_scalar_tuple(rec.get("supporting_paths")),
        integration_points=_scalar_tuple(rec.get("integration_points")),
        patterns=_object_tuple(rec.get("patterns"), _pattern),
        risks=_object_tuple(rec.get("risks"), _risk),
        escalations=_scalar_tuple(rec.get("escalations")),
        supersedes_record_at=rec.get("supersedes_record_at"),
        notes=rec.get("notes"),
    )


def _design_doc_autofix(rec: dict[str, Any]) -> DesignDocAutofix:
    return DesignDocAutofix(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        file=rec.get("file"),
        category=rec.get("category"),
        source_finding=_opt_object(rec.get("source_finding"), _source_finding),
        old_content=rec.get("old_content"),
        new_content=rec.get("new_content"),
        lines_changed=rec.get("lines_changed"),
        chars_changed=rec.get("chars_changed"),
    )


def _prd_autofix(rec: dict[str, Any]) -> PrdAutofix:
    return PrdAutofix(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        file=rec.get("file"),
        category=rec.get("category"),
        source_finding=_opt_object(rec.get("source_finding"), _source_finding),
        old_content=rec.get("old_content"),
        new_content=rec.get("new_content"),
        lines_changed=rec.get("lines_changed"),
        chars_changed=rec.get("chars_changed"),
    )


def _dispatch_start(rec: dict[str, Any]) -> DispatchStart:
    return DispatchStart(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        responding_to=_scalar_tuple(rec.get("responding_to")),
    )


def _grader_features(rec: dict[str, Any]) -> GraderFeatures:
    return GraderFeatures(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        features=_opt_object(rec.get("features"), _features),
    )


def _grader_verdict(rec: dict[str, Any]) -> GraderVerdict:
    return GraderVerdict(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        responding_to=_scalar_tuple(rec.get("responding_to")),
        summary=rec.get("summary"),
        facets=_opt_object(rec.get("facets"), _facets),
        rationale=rec.get("rationale"),
        verdict=rec.get("verdict"),
    )


def _review_feedback(rec: dict[str, Any]) -> ReviewFeedback:
    return ReviewFeedback(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        verdict=rec.get("verdict"),
        findings=_object_tuple(rec.get("findings"), _finding),
        recommendations=_scalar_tuple(rec.get("recommendations")),
        approved_aspects=_scalar_tuple(rec.get("approved_aspects")),
    )


def _review_plan(rec: dict[str, Any]) -> ReviewPlan:
    return ReviewPlan(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        risk=rec.get("risk"),
        scope=rec.get("scope"),
        basis=_opt_object(rec.get("basis"), _plan_basis),
        rationale=rec.get("rationale"),
        roster=_scalar_tuple(rec.get("roster")),
    )


def _build_failure(rec: dict[str, Any]) -> BuildFailure:
    return BuildFailure(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        retry=rec.get("retry"),
        failed_check=rec.get("failed_check"),
        error_output=rec.get("error_output"),
        attempted=rec.get("attempted"),
        partial=rec.get("partial"),
        abort_reason=rec.get("abort_reason"),
    )


def _build_pass(rec: dict[str, Any]) -> BuildPass:
    return BuildPass(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        gate_checks_run=_scalar_tuple(rec.get("gate_checks_run")),
        duration_seconds=rec.get("duration_seconds"),
    )


def _scope_override(d: dict[str, Any]) -> ScopeOverride:
    return ScopeOverride(
        non_goal_id=d.get("non_goal_id"),
        owner_decision=d.get("owner_decision"),
        source=d.get("source"),
    )


def _intake_decision(rec: dict[str, Any]) -> IntakeDecision:
    return IntakeDecision(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        request=rec.get("request"),
        decisions=_scalar_tuple(rec.get("decisions")),
        source=rec.get("source"),
        notes=rec.get("notes"),
    )


def _prd_entry(rec: dict[str, Any]) -> PrdEntry:
    return PrdEntry(
        type=rec.get("type"),
        req_id=rec.get("req_id"),
        ts=rec.get("ts"),
        author=rec.get("author"),
        title=rec.get("title"),
        summary=rec.get("summary"),
        acceptance_criteria=_scalar_tuple(rec.get("acceptance_criteria")),
        file_targets=_scalar_tuple(rec.get("file_targets")),
        test_names=_scalar_tuple(rec.get("test_names")),
        non_goals=_scalar_tuple(rec.get("non_goals")),
        dependencies=_scalar_tuple(rec.get("dependencies")),
        notes=rec.get("notes"),
        scope_overrides=_object_tuple(rec.get("scope_overrides"), _scope_override),
    )


# Record type discriminator -> its dataclass. The parity test walks this against
# the schema files on disk; _MAPPERS below pairs each with its parse function.
_RECORD_TYPES: dict[str, type[HandoffRecord]] = {
    "consultation-request": ConsultationRequest,
    "consultation-response": ConsultationResponse,
    "design-block": DesignBlock,
    "design-doc-autofix": DesignDocAutofix,
    "prd-autofix": PrdAutofix,
    "dispatch-start": DispatchStart,
    "grader-features": GraderFeatures,
    "grader-verdict": GraderVerdict,
    "review-feedback": ReviewFeedback,
    "review-plan": ReviewPlan,
    "build-failure": BuildFailure,
    "build-pass": BuildPass,
    "prd-entry": PrdEntry,
    "intake-decision": IntakeDecision,
}

_MAPPERS: dict[str, Callable[[dict[str, Any]], HandoffRecord]] = {
    "consultation-request": _consultation_request,
    "consultation-response": _consultation_response,
    "design-block": _design_block,
    "design-doc-autofix": _design_doc_autofix,
    "prd-autofix": _prd_autofix,
    "dispatch-start": _dispatch_start,
    "grader-features": _grader_features,
    "grader-verdict": _grader_verdict,
    "review-feedback": _review_feedback,
    "review-plan": _review_plan,
    "build-failure": _build_failure,
    "build-pass": _build_pass,
    "prd-entry": _prd_entry,
    "intake-decision": _intake_decision,
}


def parse_record(rec: dict[str, Any]) -> HandoffRecord:
    """Total: any dict in, some HandoffRecord out, never an exception. A dict
    whose "type" is a known type string always returns that dataclass — the
    lenient mapper lifts what fits and leaves the rest at its default, even for
    a bare {"type": "build-pass"}. UnknownRecord is only for an unknown, missing,
    or non-string "type". The schema validator owns requiredness; this is the
    graceful-degradation parse boundary. The try/except is an unreachable
    backstop — the lenient mappers never raise — kept so a future non-lenient
    lift still degrades instead of crashing."""
    rtype = rec.get("type")
    mapper = _MAPPERS.get(rtype) if isinstance(rtype, str) else None
    if mapper is None:
        return UnknownRecord(raw=rec)
    try:
        return mapper(rec)
    except (KeyError, TypeError, ValueError, AttributeError):
        return UnknownRecord(raw=rec)


# Substantive record classes, derived from the two single sources: the
# SUBSTANTIVE type strings and the type registry. The lenient lift parses a
# known type string to its class always, so an isinstance test against this
# tuple is exactly the old string-membership test, typed.
_SUBSTANTIVE_CLASSES = tuple(_RECORD_TYPES[t] for t in sorted(SUBSTANTIVE))
