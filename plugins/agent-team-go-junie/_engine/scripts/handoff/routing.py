#!/usr/bin/env python3
"""handoff/routing.py — the deterministic routing core (ADR 2026-07-17 runtime-package-layout).

Trust class: a middle layer over handoff.records and handoff.schema. It owns the
Entry lift, the latest-by-type query, the decision constructors, every gate and
recovery state, both assert_never tables, and _route_decision — the one match
over the typed union that executes the Handoff Conditions table. Route is
fail-closed: it never repairs a log and never guesses past a failed check.

Imports handoff.records and handoff.schema only; never handoff.view. Stdlib
only, Python 3.11+.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TypeAlias, TypeVar, assert_never

from .records import (
    _SUBSTANTIVE_CLASSES,
    DESIGNER,
    HUMAN,
    IMPLEMENTER,
    PLAN_ENGINE,
    PLANNER,
    PRODUCT,
    RETRY_CAP,
    ROSTER_FLOOR,
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
    HandoffRecord,
    PrdAutofix,
    PrdEntry,
    ReviewFeedback,
    ReviewPlan,
    UnknownRecord,
    parse_record,
)
from .schema import (
    LogEntry,
    SchemaError,
    layout_lookup,
    load_schema,
    validate_record,
)

# A routing decision: a JSON object keyed by "decision" plus rule-specific
# fields. It is honestly heterogeneous, so dict[str, Any] (ADR 2026-07-17).
Decision: TypeAlias = dict[str, Any]

_RecT = TypeVar("_RecT", bound=HandoffRecord)


@dataclass(frozen=True, slots=True)
class Entry:
    """One log line in the routing core: line number, raw dict, typed record.

    The raw dict serves exactly three uses — schema gates, values copied into
    decision payloads (which must stay raw JSON values), and gate-layer error
    loops whose messages index raw findings. Every other read is typed."""

    no: int
    raw: dict[str, Any]
    rec: HandoffRecord

    @property
    def author(self) -> Any:
        """The record's author: the typed field, or the raw read for an
        unknown type — an unknown record still resets scan runs, as before."""
        rec = self.rec
        return self.raw.get("author") if isinstance(rec, UnknownRecord) else rec.author


def _latest_of(entries: list[Entry], cls: type[_RecT]) -> tuple[Entry, _RecT] | None:
    """Latest (entry, typed record) whose record is a cls instance, or None.
    Under the lenient lift this is the old latest-by-type-string query."""
    found: tuple[Entry, _RecT] | None = None
    for e in entries:
        if isinstance(e.rec, cls):
            found = (e, e.rec)
    return found


def _dispatch(
    next_agents: Sequence[str],
    rule: str,
    reason: str,
    req_id: Any,
    **context: Any,
) -> Decision:
    out: Decision = {
        "decision": "dispatch",
        "next": list(next_agents),
        "rule": rule,
        "reason": reason,
    }
    if req_id:
        out["req_id"] = req_id
    if context:
        out["context"] = context
    return out


def _blocked(
    rule: str,
    reason: str,
    req_id: Any = None,
    errors: list[str] | None = None,
    **context: Any,
) -> Decision:
    out: Decision = {"decision": "blocked", "rule": rule, "reason": reason}
    if req_id:
        out["req_id"] = req_id
    if errors:
        out["errors"] = errors
    if context:
        out["context"] = context
    return out


def _bounce(
    upstream: str, rule: str, reason: str, req_id: Any, errors: list[str]
) -> Decision:
    """A failed gate bounces upstream: a dispatch of the producing agent with
    the exact errors, consuming no downstream dispatch."""
    return _dispatch([upstream], rule, reason, req_id, errors=errors)


def _finding_owner(finding: Finding) -> str | None:
    """Artifact owner for one review finding (Gate 4 split). None means the
    finding is a root-applied doc autofix (design-doc or PRD path), not a
    dispatch target. Lenient location may be None or non-str; that falls
    through to the implementer, exactly as the old empty-default read did."""
    location = finding.location if isinstance(finding.location, str) else ""
    path = location.split(":", 1)[0]
    if path.startswith("docs/prd.md"):
        return None if finding.tag == "autofix" else PRODUCT
    if path.startswith("docs/system-design.md") or path.startswith("docs/adr/"):
        return None if finding.tag == "autofix" else DESIGNER
    return IMPLEMENTER


def _unresolved_refactor(entries: list[Entry]) -> list[str]:
    """req_ids whose latest design-block verdict is refactor-first (no
    superseding design-block yet) — the original slices awaiting re-triage.

    Scans every req_id in the log. The pipeline runs one feature at a time
    (new-feature clears .scratch/), so cross-feature leftovers cannot occur
    in a well-run log; a stale record from a never-cleared feature would
    surface here and is the operator's cue to run /new-feature."""
    latest: dict[str, Any] = {}
    for e in entries:
        if isinstance(e.rec, DesignBlock) and isinstance(e.rec.req_id, str):
            latest[e.rec.req_id] = e.rec.verdict
    return sorted(r for r, v in latest.items() if v == "refactor-first")


def _escalate(rule: str, reason: str, req_id: Any = None, **context: Any) -> Decision:
    out: Decision = {"decision": "escalate", "rule": rule, "reason": reason}
    if req_id:
        out["req_id"] = req_id
    if context:
        out["context"] = context
    return out


def _gate_errors(
    record: dict[str, Any], rtype: str, schemas_dir: str, layout: dict[str, Any]
) -> list[str]:
    """Schema-check one gating record; any loading failure is a gate failure."""
    try:
        schema = load_schema(schemas_dir, rtype, layout)
    except (SchemaError, json.JSONDecodeError) as exc:
        return [str(exc)]
    return validate_record(record, schema)


def _roster(layout: dict[str, Any]) -> tuple[list[str] | None, str | None]:
    """The reviewer roster, or an error string. Gate 4 makes declared extras
    part of the gate, so a malformed declaration fails closed."""
    extras = layout_lookup(layout, "harness.extra_reviewers")
    if extras is None:
        return list(ROSTER_FLOOR), None
    if not isinstance(extras, list) or any(
        not isinstance(e, str) or not e for e in extras
    ):
        return (
            None,
            "harness.extra_reviewers in scripts/layout.toml must be a list of reviewer names",
        )
    roster = list(ROSTER_FLOOR)
    for extra in extras:
        if extra not in roster:
            roster.append(extra)
    return roster, None


def _auto_grade(layout: dict[str, Any]) -> bool:
    """Whether the pipeline auto-dispatches the terminal change-grader once the
    roster approves. Fails open: an absent or non-boolean key leaves grading on,
    so a project keeps grading across upgrades unless it opts out with
    `auto_grade = false`. This gates only the automatic dispatch — the
    change-grader agent and change-grading skill stay runnable by hand either
    way, and a hand-run grader-verdict still routes normally."""
    return layout_lookup(layout, "harness.auto_grade") is not False


def _active_plan(recs: list[Entry], bp_line: int) -> tuple[Entry, ReviewPlan] | None:
    """Latest (entry, review-plan) after the current build-pass, or None.

    The implementer appends the engine's plan as the final step of gate-pass, so
    a plan after the build-pass is the risk estimate for this review pass. On the
    gray path the planner appends a second, later plan — this returns whichever
    is latest, so the planner's resolution supersedes the engine's deferral."""
    plan: tuple[Entry, ReviewPlan] | None = None
    for e in recs:
        if e.no > bp_line and isinstance(e.rec, ReviewPlan):
            plan = (e, e.rec)
    return plan


def _resolve_review_roster(
    recs: list[Entry],
    plan: tuple[Entry, ReviewPlan] | None,
    full_roster: Sequence[str],
    req_id: Any,
) -> tuple[list[str] | None, Decision | None]:
    """Resolve the roster for this review pass from the active plan, or a
    routing decision when the plan is unresolved.

    Returns (review_roster, decision). Exactly one is non-None: a review_roster
    to gate on, or a decision that must be returned as-is (dispatch the planner,
    bounce a bad plan, block a stalled planner). Fail-closed: no plan, or a plan
    whose roster names an unknown reviewer, gates on the full battery — the
    pre-plan behavior."""
    if plan is None:
        return list(full_roster), None
    plan_e, plan_rec = plan
    plan_no = plan_e.no
    if plan_rec.risk == "gray":
        if plan_rec.author != PLAN_ENGINE:
            return None, _bounce(
                PLANNER,
                "plan-gray-invalid",
                f"review-plan at line {plan_no} is gray but not engine-authored; only the engine defers",
                req_id,
                ["review-planner emitted risk 'gray'; it must resolve to low or high"],
            )
        starts = sum(
            1
            for e in recs
            if e.no > plan_no
            and isinstance(e.rec, DispatchStart)
            and e.rec.author == PLANNER
        )
        if starts == 0:
            return None, _dispatch(
                [PLANNER],
                "plan-gray",
                "review-plan is gray; dispatch the review-planner to resolve the roster",
                req_id,
            )
        if starts == 1:
            return None, _dispatch(
                [PLANNER],
                "planner-stall-retry",
                "review-planner returned without a plan; re-dispatch once",
                req_id,
            )
        return None, _blocked(
            "planner-stalled",
            "review-planner produced no plan after the stall retry; resolve manually",
            req_id,
        )
    # The lenient lift turns a non-list roster into (), so emptiness covers the
    # old isinstance(list) check with the same fail-closed result.
    plan_roster = plan_rec.roster
    if not plan_roster or any(r not in full_roster for r in plan_roster):
        # A plan naming an unknown reviewer cannot gate; fail closed to the
        # full battery rather than gate on a partial or bogus roster.
        return list(full_roster), None
    return [r for r in full_roster if r in plan_roster], None


def _consultation_dispatch(
    e: Entry,
    req: ConsultationRequest,
    schemas_dir: str,
    layout: dict[str, Any],
    req_id: Any,
) -> Decision:
    no = e.no
    errors = _gate_errors(e.raw, "consultation-request", schemas_dir, layout)
    # Lenient fields hold the raw value uncoerced, so every guard below is
    # load-bearing exactly as it was on the dict reads.
    target = req.target
    if not isinstance(target, str) or not target:
        errors.append("consultation-request names no target specialist")
    if errors:
        author = req.author
        if isinstance(author, str) and author:
            return _bounce(
                author,
                "consultation-invalid",
                f"consultation-request at line {no} failed its gate; re-dispatch its author",
                req_id,
                errors,
            )
        return _blocked(
            "consultation-invalid",
            f"consultation-request at line {no} failed its gate",
            req_id,
            errors,
        )
    # Past the error gate, the guard above proved target a non-empty str.
    assert isinstance(target, str)
    if target.strip().casefold() == HUMAN:
        # The elicitation pause: the specialist asked the human. Halt for the
        # conversation in root; the root-appended consultation-response
        # (author "human") resumes the requester via consultation-return.
        # Exact-match the contract: a case/whitespace variant would otherwise
        # read as an agent name and root would dispatch a nonexistent agent.
        author = req.author
        if author == HUMAN:
            # Checked before the exact-match bounce: a "human"-authored record
            # must never become a bounce dispatch of a "human" agent.
            return _blocked(
                "consultation-invalid",
                f'consultation-request at line {no} is authored by "human"; no agent to resume',
                req_id,
            )
        if target != HUMAN:
            msg = f'consultation-request at line {no} target must be exactly "human"'
            if isinstance(author, str) and author:
                return _bounce(
                    author,
                    "consultation-invalid",
                    msg + "; re-dispatch its author",
                    req_id,
                    [msg],
                )
            return _blocked("consultation-invalid", msg, req_id, [msg])
        return _blocked(
            "human-consultation",
            f"consultation-request at line {no} targets the human; converse, then append "
            'the consultation-response (author "human") to resume the requester',
            req_id,
            requester=author,
            question=req.question,
        )
    return _dispatch(
        [target],
        "consultation-dispatch",
        "pending consultation-request; dispatch the target in consultation mode",
        req_id,
        requester=req.author,
    )


def _consultation_return(
    recs: list[Entry],
    e: Entry,
    resp: ConsultationResponse,
    schemas_dir: str,
    layout: dict[str, Any],
    req_id: Any,
) -> Decision:
    resp_no = e.no
    errors = _gate_errors(e.raw, "consultation-response", schemas_dir, layout)
    req_e = next((x for x in recs if x.no == resp.in_response_to), None)
    if req_e is None or not isinstance(req_e.rec, ConsultationRequest):
        errors.append(
            f"in_response_to ({resp.in_response_to}) does not point at a consultation-request line"
        )
    elif resp.author != req_e.rec.target:
        errors.append(
            "consultation-response author does not match the request's target"
        )
    elif not isinstance(req_e.rec.author, str) or not req_e.rec.author:
        errors.append(
            "the corresponding consultation-request names no author to return to"
        )
    if errors:
        # A failed gate is a dispatch of the upstream agent (the responder),
        # like the request side — blocked only when the dangling
        # in_response_to leaves no identifiable responder to re-dispatch.
        # Raw read: the pointed-at record need not be a consultation-request,
        # yet its raw target still names the responder, as before.
        target = req_e.raw.get("target") if req_e is not None else None
        if isinstance(target, str) and target:
            return _bounce(
                target,
                "consultation-invalid",
                f"consultation-response at line {resp_no} failed its gate; re-dispatch the responder",
                req_id,
                errors,
            )
        return _blocked(
            "consultation-invalid",
            f"consultation-response at line {resp_no} failed its gate",
            req_id,
            errors,
        )
    # Post-gate: an empty error list implies the request line resolved to a
    # ConsultationRequest with a non-empty author (the elif chain above).
    assert req_e is not None and isinstance(req_e.rec, ConsultationRequest)
    assert isinstance(req_e.rec.author, str)
    if req_e.rec.author == HUMAN:
        return _blocked(
            "consultation-invalid",
            f"consultation-request at line {resp.in_response_to} is authored by "
            '"human"; no agent to resume',
            req_id,
        )
    return _dispatch(
        [req_e.rec.author],
        "consultation-return",
        "route control back to the requesting specialist; do not advance the pipeline",
        req_id,
        resume=True,
    )


def _review_state(
    recs: list[Entry],
    roster: Sequence[str],
    schemas_dir: str,
    layout: dict[str, Any],
    req_id: Any,
    unresolved: list[str],
) -> Decision:
    """Route the post-build-pass phase: reviewer dispatch, stall handling,
    findings processing by artifact owner, grading, completion. Deterministic
    from the log: feedback older than the reviewer's latest dispatch-start is
    stale; one silent dispatch-start earns the single stall retry, a second
    blocks."""
    full_roster = list(roster)
    bp = _latest_of(recs, BuildPass)
    if bp is None:
        return _escalate(
            "review-without-build-pass",
            "review activity with no build-pass record for this slice",
            req_id,
        )
    bp_line = bp[0].no
    errors = _gate_errors(bp[0].raw, "build-pass", schemas_dir, layout)
    if errors:
        return _bounce(
            IMPLEMENTER,
            "build-record-invalid",
            f"build-pass at line {bp_line} failed its gate; re-dispatch the implementer",
            req_id,
            errors,
        )
    prev_bp_line = 0
    for e in recs:
        if e.no < bp_line and isinstance(e.rec, BuildPass):
            prev_bp_line = e.no
    prior_escalate = any(
        prev_bp_line < e.no < bp_line
        and isinstance(e.rec, ReviewFeedback)
        and any(f.tag == "escalate" for f in e.rec.findings)
        for e in recs
    )
    any_fb_since_bp = any(
        e.no > bp_line and isinstance(e.rec, ReviewFeedback) for e in recs
    )
    if prior_escalate and not any_fb_since_bp:
        return _blocked(
            "escalate-finding-halt",
            "an escalate finding preceded this build-pass; the human decides before reviews re-run",
            req_id,
        )
    # Risk-proportional review: the active plan names the roster for this pass.
    # A gray plan dispatches the planner; absent/invalid plans fail closed to the
    # full battery (see _resolve_review_roster). review_roster replaces the full
    # roster in every per-pass check below.
    review_roster, decision = _resolve_review_roster(
        recs, _active_plan(recs, bp_line), roster, req_id
    )
    if decision is not None:
        return decision
    # _resolve_review_roster returns exactly one of (roster, decision); a None
    # decision means a concrete roster. Assert it to narrow away the None.
    assert review_roster is not None
    roster = review_roster
    feedback: dict[str, Entry] = {}
    retry_once: list[str] = []
    stalled: list[str] = []
    undispatched: list[str] = []
    for reviewer in roster:
        fb: Entry | None = None
        starts = 0
        for e in recs:
            if e.no <= bp_line or e.author != reviewer:
                continue
            if isinstance(e.rec, ReviewFeedback):
                fb = e
                starts = 0
            elif isinstance(e.rec, DispatchStart):
                starts += 1
        if starts == 0 and fb is not None:
            feedback[reviewer] = fb
        elif starts == 0:
            undispatched.append(reviewer)
        elif starts == 1:
            retry_once.append(reviewer)
        else:
            stalled.append(reviewer)
    if stalled:
        return _blocked(
            "reviewer-stalled",
            "reviewer(s) produced no current review-feedback record after the stall retry; append the escalation and stop",
            req_id,
            stalled=stalled,
        )
    if undispatched and not feedback and not retry_once:
        return _dispatch(
            roster,
            "reviews-needed",
            "build-pass gated; dispatch the resolved pass roster in parallel",
            req_id,
        )
    if retry_once:
        return _dispatch(
            retry_once + undispatched,
            "reviewer-stall-retry",
            "reviewer(s) returned without a current review-feedback record; re-dispatch once per the Reviewer Stall Check",
            req_id,
        )
    if undispatched:
        return _dispatch(
            undispatched,
            "reviews-needed",
            "roster reviewer(s) have not been dispatched since build-pass",
            req_id,
        )
    for reviewer, fb_e in feedback.items():
        errors = _gate_errors(fb_e.raw, "review-feedback", schemas_dir, layout)
        # Gate-layer loops read raw findings: the lenient lift drops non-dict
        # items, which would shift the 1-based indexes in these messages. A
        # non-list value reads as absent — enumerate over it would crash, and
        # route never crashes on log content.
        raw_findings = fb_e.raw.get("findings", [])
        if not isinstance(raw_findings, list):
            raw_findings = []
        # Gate 4: a clarify finding without its target is unroutable.
        errors.extend(
            f"finding {i} has tag 'clarify' but no clarify_target"
            for i, f in enumerate(raw_findings, 1)
            if isinstance(f, dict)
            and f.get("tag") == "clarify"
            and not f.get("clarify_target")
        )
        # Gate 4: severity on a fix-routable finding drives the next
        # review-plan's prior-critical trigger (grading.py); a missing
        # value would silently read as non-critical and narrow the fix round.
        errors.extend(
            f"finding {i} has tag '{f.get('tag')}' but no severity"
            for i, f in enumerate(raw_findings, 1)
            if isinstance(f, dict)
            and f.get("tag") in ("autofix", "blocked")
            and not f.get("severity")
        )
        # Gate 4: an approved verdict with a fix-routable finding is a
        # contradiction the router would otherwise drop silently — the finding
        # never reaches an owner, and the reviewer re-raises it a round later
        # (measured in the eval bench's first sweep). Escalate and clarify
        # stay legal on approval; they route through their own paths.
        errors.extend(
            f"finding {i} is tag '{f.get('tag')}' on an approved verdict; "
            "record changes_requested or drop the finding"
            for i, f in enumerate(raw_findings, 1)
            if isinstance(f, dict)
            and fb_e.raw.get("verdict") == "approved"
            and f.get("tag") in ("autofix", "blocked")
        )
        if errors:
            return _bounce(
                reviewer,
                "review-record-invalid",
                f"review-feedback at line {fb_e.no} failed its gate; re-dispatch the reviewer",
                req_id,
                errors,
            )
    # Post-gate: every feedback record above passed its schema gate, so the
    # typed verdict/findings reads below are the old .get reads, narrowed.
    rfs = {r: e.rec for r, e in feedback.items() if isinstance(e.rec, ReviewFeedback)}
    non_approved = {r: rf for r, rf in rfs.items() if rf.verdict != "approved"}
    empty = [r for r in roster if r in non_approved and not non_approved[r].findings]
    if empty:
        return _dispatch(
            empty,
            "reviewer-empty-findings",
            "non-approved verdict with no findings is not actionable; re-dispatch the reviewer",
            req_id,
        )
    escalate_tags = sum(
        1 for rf in rfs.values() for f in rf.findings if f.tag == "escalate"
    )
    if non_approved:
        owners: list[str] = []
        root_autofix = 0
        for rf in non_approved.values():
            for f in rf.findings:
                owner = _finding_owner(f)
                if owner is None:
                    root_autofix += 1
                elif owner not in owners:
                    owners.append(owner)
        # Escalate findings cross the approved boundary: an APPROVED record's
        # escalate-tagged finding still joins the split, and the implementer
        # always rides an escalate round — it appends the entry to
        # .scratch/escalations.md while processing findings (Gate 4).
        for reviewer, rf in rfs.items():
            if reviewer in non_approved:
                continue
            for f in rf.findings:
                if f.tag == "escalate":
                    owner = _finding_owner(f) or IMPLEMENTER
                    if owner not in owners:
                        owners.append(owner)
        if escalate_tags and owners and IMPLEMENTER not in owners:
            owners.append(IMPLEMENTER)
        owners = [o for o in (IMPLEMENTER, PRODUCT, DESIGNER) if o in owners]
        if not owners:
            return _escalate(
                "autofix-only-round",
                "every finding is a root-applied doc autofix; root applies them and the coordinator decides the re-review",
                req_id,
                root_autofix=root_autofix,
            )
        context: dict[str, Any] = {
            "reviewers": sorted(non_approved),
            "escalate_findings": escalate_tags,
            "root_autofix": root_autofix,
        }
        if escalate_tags:
            context["halt_after"] = True
        return _dispatch(
            owners,
            "process-findings",
            "findings dispatch to their artifact owners; halt after processing when an escalate finding is present",
            req_id,
            **context,
        )
    if escalate_tags:
        return _blocked(
            "escalate-on-approved",
            "approved verdicts carry escalate-tagged finding(s); root appends the escalation entry and halts",
            req_id,
            escalate_findings=escalate_tags,
        )
    # Completion invariant (route-spec § Gate 5): feature-complete requires every
    # reviewer dispatched in the current design cycle to hold a latest
    # 'approved', not just the current pass roster. The cycle starts at the
    # latest *superseding* design-block — a re-triage voids prior review
    # history and the engine's design-revision trigger re-runs the full
    # battery; an initial design-block landing mid-slice keeps prior dissent
    # outstanding (ADR 2026-08-07). The engine's fix plans always re-include
    # dissenters, so this is empty on the honest path — but a malformed or
    # forged plan that drops a prior dissenter would otherwise grade with that
    # dissent unresolved. Enforce it deterministically: scan the latest verdict
    # per reviewer since the cycle start and re-dispatch any outstanding
    # dissenter the pass roster did not cover. The supersedes pointer is
    # re-checked in Gate-2 shape here: Gate 2 validates a design-block only
    # when it is the latest substantive record, so a mid-turn append can carry
    # a bogus pointer — and a boundary that honored it would let one forged
    # record void the dissent this invariant exists to protect. bool is
    # excluded — True passes isinstance(int).
    by_no = {e.no: e for e in recs}
    db_line = 0
    for e in recs:
        if not isinstance(e.rec, DesignBlock):
            continue
        sup = e.rec.supersedes_record_at
        if not isinstance(sup, int) or isinstance(sup, bool) or sup >= e.no:
            continue
        target = by_no.get(sup)
        if target is not None and isinstance(target.rec, DesignBlock):
            db_line = e.no
    latest_verdict: dict[str, Any] = {}
    latest_fb_line: dict[str, int] = {}
    for e in recs:
        if e.no > db_line and isinstance(e.rec, ReviewFeedback):
            who = e.rec.author
            if isinstance(who, str) and who:
                latest_verdict[who] = e.rec.verdict
                latest_fb_line[who] = e.no
    outstanding = [
        w
        for w in full_roster
        if w not in roster and latest_verdict.get(w) not in (None, "approved")
    ]
    if outstanding:
        # The re-dispatch runs outside the pass-roster stall ladder above, so it
        # carries its own retry-once-then-block ceiling: an outstanding dissenter
        # re-dispatched twice with no fresh review-feedback stalls, so a log that
        # keeps dropping it cannot loop the router forever.
        stalled = [
            w
            for w in outstanding
            if sum(
                1
                for e in recs
                if e.no > latest_fb_line[w]
                and isinstance(e.rec, DispatchStart)
                and e.rec.author == w
            )
            >= 2
        ]
        if stalled:
            return _blocked(
                "reviewer-stalled",
                "outstanding dissenter(s) produced no fresh review-feedback after "
                "re-dispatch; append the escalation and stop",
                req_id,
                stalled=stalled,
            )
        return _dispatch(
            outstanding,
            "outstanding-dissent",
            "prior reviewer(s) dissented and the plan did not re-include them; "
            "dispatch them to resolve before completion",
            req_id,
        )
    gv = _latest_of(recs, GraderVerdict)
    if gv is not None and gv[0].no > bp_line:
        if unresolved:
            return _dispatch(
                [DESIGNER],
                "refactor-resume",
                "refactor slice complete; re-triage the original slice with supersedes_record_at",
                req_id,
                original_req_id=unresolved[0],
                verdict=gv[1].verdict,
            )
        return _blocked(
            "feature-complete",
            "all roster reviewers approved and the change-grader recorded its advisory verdict; human merge decision",
            req_id,
            verdict=gv[1].verdict,
        )
    if not _auto_grade(layout):
        # Grading is disabled in the pipeline (layout.toml auto_grade = false):
        # the approved state is terminal with no grader run. The change-grader
        # agent/skill stay installed, so a hand-run grader-verdict still routes
        # via the branch above; the refactor slice resumes on approval instead
        # of on a grader-verdict it will never get.
        if unresolved:
            return _dispatch(
                [DESIGNER],
                "refactor-resume",
                "refactor slice complete (grading disabled); re-triage the original slice with supersedes_record_at",
                req_id,
                original_req_id=unresolved[0],
            )
        return _blocked(
            "feature-complete",
            "all roster reviewers approved; change grading disabled (auto_grade = false) — "
            "run the change-grading skill by hand if wanted; human merge decision",
            req_id,
        )
    return _dispatch(
        ["change-grader"],
        "grade",
        "all roster reviewers approved; dispatch the terminal advisory change-grader",
        req_id,
    )


def _build_failure_state(
    recs: list[Entry], req_id: Any, schemas_dir: str, layout: dict[str, Any]
) -> Decision:
    # Reached only when the latest substantive record is a build-failure, so the
    # lookup is non-None; assert it to narrow before the unpack.
    found = _latest_of(recs, BuildFailure)
    assert found is not None
    bf_e, bf = found
    errors = _gate_errors(bf_e.raw, "build-failure", schemas_dir, layout)
    if errors:
        return _bounce(
            IMPLEMENTER,
            "build-record-invalid",
            f"build-failure at line {bf_e.no} failed its gate; re-dispatch the implementer",
            req_id,
            errors,
        )
    abort = bf.abort_reason
    if abort == "wrong-shape-slice":
        return _dispatch(
            [PRODUCT],
            "abort-wrong-shape",
            "implementer aborted: slice cannot be implemented as scoped; re-split",
            req_id,
        )
    if abort == "design-mismatch":
        return _dispatch(
            [DESIGNER],
            "abort-design-mismatch",
            "implementer aborted: design does not match reality; re-triage with supersedes_record_at",
            req_id,
        )
    if abort == "prd-mismatch":
        return _dispatch(
            [PRODUCT],
            "abort-prd-mismatch",
            "autofix audit failed on a prd-autofix record; the PRD owner reconciles and a superseding prd-entry restarts the gate",
            req_id,
        )
    if abort == "prerequisite-missing":
        return _blocked(
            "abort-prerequisite",
            "implementer aborted on a missing external prerequisite; root appends the escalation and halts",
            req_id,
        )
    if abort:
        return _escalate(
            "abort-unknown",
            f"build-failure carries unrecognized abort_reason '{abort}'",
            req_id,
        )
    db = _latest_of(recs, DesignBlock)
    if db is None:
        return _escalate(
            "failure-without-design",
            "build-failure exists but no design-block precedes it",
            req_id,
        )
    count = sum(1 for e in recs if e.no > db[0].no and isinstance(e.rec, BuildFailure))
    if count < RETRY_CAP:
        return _dispatch(
            [IMPLEMENTER],
            "build-retry",
            f"quality gate failed; re-dispatch with error context (this is retry {count} of {RETRY_CAP})",
            req_id,
            retry=count,
            partial=bool(bf.partial),
        )
    return _dispatch(
        [DESIGNER],
        "build-non-convergence",
        "three gate failures since the latest design-block; re-triage with supersedes_record_at",
        req_id,
        failures=count,
    )


def _truncation_state(recs: list[Entry], req_id: Any) -> Decision:
    db = _latest_of(recs, DesignBlock)
    if db is None:
        return _escalate(
            "truncation-before-design",
            "implementer dispatch-start with no design-block on record",
            req_id,
        )
    run = 0
    for e in recs:
        if e.no <= db[0].no or e.author != IMPLEMENTER:
            continue
        if isinstance(e.rec, DispatchStart):
            run += 1
        else:
            run = 0
    if run < RETRY_CAP:
        return _dispatch(
            [IMPLEMENTER],
            "truncation-continue",
            f"dispatch truncated before a substantive record; continue the same slice (continuation {run} of {RETRY_CAP})",
            req_id,
            continuation=run,
        )
    return _dispatch(
        [DESIGNER],
        "truncation-non-convergence",
        "three consecutive truncated dispatches with no implementer record; re-triage per Truncation Recovery",
        req_id,
        continuations=run,
    )


def _route_decision(
    entries: list[LogEntry],
    req_id_arg: str | None,
    schemas_dir: str,
    layout: dict[str, Any],
) -> Decision:
    if not entries:
        return _escalate(
            "no-active-slice",
            "handoff log has no records; classify the request per the Agent Selection table",
        )
    req_id = req_id_arg or entries[-1][1].get("req_id")
    if not isinstance(req_id, str) or not req_id:
        return _blocked(
            "missing-req-id", f"latest record (line {entries[-1][0]}) carries no req_id"
        )
    # The one parse pass: from here down, dispatch is a match over the typed
    # union — under the lenient lift each class arm is exactly the old
    # type-string row, and assert_never closes the table. The checker enforces
    # this — the file is in the battery's mypy typed scope (ADR 2026-07-17).
    typed_all = [Entry(no, raw, parse_record(raw)) for no, raw in entries]
    recs = [e for e in typed_all if e.raw.get("req_id") == req_id]
    if not recs:
        return _blocked("unknown-req-id", f"no records for {req_id}", req_id)
    roster, roster_error = _roster(layout)
    if roster_error:
        return _blocked("layout-invalid", roster_error, req_id)
    # _roster returns exactly one of (roster, error); a None error means a
    # concrete roster. Assert it to narrow away the None before the reads below.
    assert roster is not None
    unresolved = [r for r in _unresolved_refactor(typed_all) if r != req_id]
    last = recs[-1]

    match last.rec:
        case ConsultationRequest() as creq:
            return _consultation_dispatch(last, creq, schemas_dir, layout, req_id)
        case ConsultationResponse() as cresp:
            return _consultation_return(recs, last, cresp, schemas_dir, layout, req_id)
        case GraderVerdict(verdict=last_verdict):
            if unresolved:
                return _dispatch(
                    [DESIGNER],
                    "refactor-resume",
                    "refactor slice complete; re-triage the original slice with supersedes_record_at",
                    req_id,
                    original_req_id=unresolved[0],
                    verdict=last_verdict,
                )
            return _blocked(
                "feature-complete",
                "change-grader recorded its advisory verdict; human merge decision",
                req_id,
                verdict=last_verdict,
            )
        case GraderFeatures():
            return _dispatch(
                ["change-grader"],
                "grade-continue",
                "grader-features recorded without a grader-verdict; re-dispatch the change-grader",
                req_id,
            )
        case (
            BuildPass()
            | BuildFailure()
            | ReviewFeedback()
            | ReviewPlan()
            | DesignBlock()
            | PrdEntry()
            | DispatchStart()
            | DesignDocAutofix()
            | PrdAutofix()
            | UnknownRecord()
        ):
            # No last-record fast-path row: fall through to the substantive
            # selection below — the old string table's default, made explicit
            # so this match stays exhaustive over the union.
            pass
        case _ as unreachable:
            assert_never(unreachable)

    latest_substantive: Entry | None = None
    for e in recs:
        if isinstance(e.rec, _SUBSTANTIVE_CLASSES):
            latest_substantive = e
    latest_request = _latest_of(recs, ConsultationRequest)
    latest_response = _latest_of(recs, ConsultationResponse)
    sub_line = latest_substantive.no if latest_substantive else 0
    req_line = latest_request[0].no if latest_request else 0
    resp_line = latest_response[0].no if latest_response else 0

    # Truncation detection follows the table trigger — a dispatch-start with
    # no subsequent substantive record — not "dispatch-start is the last
    # record": a trailing non-substantive root record (a design-doc or PRD
    # autofix note, an escalation entry) must not mask a truncated dispatch. Grader
    # records count as subsequent output here: a grader-verdict after the
    # grader's own dispatch-start is a completed dispatch, not a truncation.
    grader_line = max(
        (e.no for e in recs if isinstance(e.rec, GraderVerdict | GraderFeatures)),
        default=0,
    )
    latest_ds = _latest_of(recs, DispatchStart)
    if latest_ds is not None and latest_ds[0].no > max(
        sub_line, req_line, resp_line, grader_line
    ):
        author = latest_ds[1].author
        if author == IMPLEMENTER:
            return _truncation_state(recs, req_id)
        if author in roster or author == PLANNER:
            # A truncated reviewer or review-planner routes into the review
            # state, which applies the matching stall ladder from the log.
            return _review_state(recs, roster, schemas_dir, layout, req_id, unresolved)
        return _escalate(
            "truncation-undefined",
            f"dispatch-start from {author} with no subsequent substantive record; no recovery row is defined for this agent",
            req_id,
            author=author,
        )

    if latest_request is not None and req_line > sub_line and req_line > resp_line:
        return _consultation_dispatch(
            latest_request[0], latest_request[1], schemas_dir, layout, req_id
        )
    if latest_substantive is None:
        return _escalate(
            "no-substantive-record",
            "records exist but none is substantive; classify the state manually",
            req_id,
        )
    sub = latest_substantive

    match sub.rec:
        case BuildPass() | ReviewFeedback() | ReviewPlan():
            return _review_state(recs, roster, schemas_dir, layout, req_id, unresolved)
        case BuildFailure():
            return _build_failure_state(recs, req_id, schemas_dir, layout)
        case DesignBlock(verdict=verdict) as db_rec:
            return _design_block_row(
                sub, db_rec, verdict, recs, schemas_dir, layout, req_id
            )
        case PrdEntry(author=prd_author):
            return _prd_entry_row(sub, prd_author, schemas_dir, layout, req_id)
        case ConsultationResponse() as sub_resp:
            return _consultation_return(
                recs, sub, sub_resp, schemas_dir, layout, req_id
            )
        case (
            DispatchStart()
            | ConsultationRequest()
            | GraderVerdict()
            | GraderFeatures()
            | DesignDocAutofix()
            | PrdAutofix()
            | UnknownRecord()
        ):
            # Unreachable via the substantive selection above; kept explicit
            # so the union match stays exhaustive — a new record type fails
            # the type check at this table (the file is in the battery's
            # mypy typed scope), and the runtime fallback stays fail-closed.
            return _escalate(
                "unroutable-state",
                f"latest substantive record type '{sub.raw.get('type')}' matched no table row",
                req_id,
            )
        case _ as unreachable:
            assert_never(unreachable)


def _design_block_row(
    sub: Entry,
    db_rec: DesignBlock,
    verdict: Any,
    recs: list[Entry],
    schemas_dir: str,
    layout: dict[str, Any],
    req_id: Any,
) -> Decision:
    """The design-block rows of the Handoff Conditions table (Gate 2)."""
    if verdict == "conflicting":
        # Decision payloads stay raw JSON values.
        escalations = sub.raw.get("escalations", [])
        # Gate 2: a conflicting verdict must carry its escalations — an
        # empty array leaves the human nothing to decide on. Still
        # blocked either way; the error names the gap.
        gap = (
            None
            if escalations
            else [
                "conflicting design-block carries no escalations (Gate 2 requires a non-empty array)"
            ]
        )
        return _blocked(
            "design-conflict",
            "design-block verdict is conflicting; halt and surface the escalations to the user",
            req_id,
            errors=gap,
            escalations=escalations,
        )
    if verdict == "refactor-first":
        return _escalate(
            "refactor-first",
            "refactor-first verdict: the coordinator orders the refactor slice ahead of this one",
            req_id,
        )
    errors = _gate_errors(sub.raw, "design-block", schemas_dir, layout)
    # Gate 2: a supersedes_record_at pointer must reference a prior
    # design-block line of this slice. The lenient field holds the raw value
    # uncoerced, so the isinstance guard stays load-bearing.
    sup = db_rec.supersedes_record_at
    if sup is not None:
        target = next((e for e in recs if e.no == sup), None)
        if (
            not isinstance(sup, int)
            or sup >= sub.no
            or target is None
            or not isinstance(target.rec, DesignBlock)
        ):
            errors.append(
                f"supersedes_record_at ({sup!r}) does not point "
                "at a prior design-block line for this slice"
            )
    if errors or verdict not in ("covered", "minor", "new", "foundational"):
        if not errors:
            errors = [f"unknown design-block verdict '{verdict}'"]
        return _bounce(
            DESIGNER,
            "design-gate-failed",
            f"design-block at line {sub.no} failed its gate; re-dispatch upstream",
            req_id,
            errors,
        )
    return _dispatch(
        [IMPLEMENTER],
        "design-approved",
        f"design-block verdict '{verdict}' passed its gate; dispatch the implementer",
        req_id,
        verdict=verdict,
    )


def _prd_entry_row(
    sub: Entry,
    prd_author: Any,
    schemas_dir: str,
    layout: dict[str, Any],
    req_id: Any,
) -> Decision:
    """The prd-entry rows of the Handoff Conditions table (Gate 1)."""
    if prd_author == DESIGNER:
        return _escalate(
            "refactor-first",
            "designer-authored sibling prd-entry: the coordinator orders the refactor slice ahead of the original",
            req_id,
        )
    errors = _gate_errors(sub.raw, "prd-entry", schemas_dir, layout)
    if errors:
        return _bounce(
            PRODUCT,
            "prd-gate-failed",
            f"prd-entry at line {sub.no} failed its gate; re-dispatch upstream",
            req_id,
            errors,
        )
    return _dispatch(
        [DESIGNER],
        "prd-approved",
        "prd-entry passed its gate; dispatch the system-design-expert for triage",
        req_id,
    )
