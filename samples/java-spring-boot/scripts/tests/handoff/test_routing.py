#!/usr/bin/env python3
"""The routing core: one test per rule of the Handoff Conditions table, the gates, the
recovery ladders, the consultation roundtrip, and the cross-cutting routing invariants.

handoff.routing, exercised in process through `route`; the command line is
`tests/test_handoff.py`'s. `unroutable-state` is the exhaustive-match fallback of the
substantive row and is unreachable through the substantive selection, so no test names it.
"""

import dataclasses
import unittest

from handoff import (
    DESIGNER,
    GRADER,
    HUMAN,
    IMPLEMENTER,
    PLAN_ENGINE,
    PLANNER,
    PRODUCT,
    RECORD_TYPES,
    REVIEW_ROUND_CAP,
    ROUTINE_IMPLEMENTER,
    Decision,
    blocked,
    dispatch,
    escalate,
)

from tests.support import (
    A_SLICE,
    FLOOR,
    PIPELINE_TYPES,
    SOME_TS,
    FakeGate,
    a_slice_record,
    route,
)

ROOT = "root"
A_REVIEWER = "doc-reviewer"
ANOTHER_REVIEWER = "security-reviewer"
OFF_ROSTER_REVIEWER = "polish-reviewer"
EXTRA_REVIEWER = "perf-reviewer"
FULL_ROSTER = tuple(FLOOR)
OTHER_REVIEWERS = tuple(r for r in FULL_ROSTER if r != A_REVIEWER)
THIS_REQ_ID = A_SLICE
OTHER_REQ_ID = "REQ-B-001"
SOME_ERRORS = ["a gate error"]
SOME_DELTA = ("NG-5",)
SOME_QUESTION = "Is REQ-XX-001's scope one behavior?"

EXTRA_REVIEWER_LAYOUT = {"harness": {"extra_reviewers": [EXTRA_REVIEWER]}}
GRADING_OFF = {"harness": {"auto_grade": False}}
GRADING_ON = {"harness": {"auto_grade": True}}
GRADING_MISTYPED = {"harness": {"auto_grade": "false"}}

CRITICAL_BLOCKED = {
    "tag": "blocked",
    "location": "src/widget:1",
    "description": "d",
    "severity": "critical",
}
CLARIFY = {
    "tag": "clarify",
    "location": "src/widget:1",
    "description": "d",
    "clarify_target": DESIGNER,
}
ESCALATE = {"tag": "escalate", "location": "src/widget:1", "description": "d"}
TRUNCATION = {
    "tag": "truncation",
    "location": "src/",
    "description": "planned checkpoint reached",
}


def autofix(severity="fixable", location="src/widget:1"):
    return {
        "tag": "autofix",
        "location": location,
        "description": "d",
        "fix": "f",
        "severity": severity,
    }


AUTOFIX = autofix()


def approved(reviewer):
    return a_slice_record(
        "review-feedback", author=reviewer, verdict="approved", findings=[]
    )


def approvals(reviewers=FULL_ROSTER):
    return [approved(r) for r in reviewers]


def dissent(reviewer=A_REVIEWER, findings=(AUTOFIX,), verdict="changes_requested"):
    return a_slice_record(
        "review-feedback", author=reviewer, verdict=verdict, findings=list(findings)
    )


def review_pass(dissenter=A_REVIEWER, severity="fixable"):
    """One full review pass: build-pass, every other reviewer approving, one dissent."""
    others = [r for r in FULL_ROSTER if r != dissenter]
    return [
        a_slice_record("build-pass"),
        *approvals(others),
        dissent(dissenter, (autofix(severity),)),
    ]


def truncation_pass(dissenter=A_REVIEWER):
    """One full review pass whose only dissent is a truncation checkpoint."""
    others = [r for r in FULL_ROSTER if r != dissenter]
    return [
        a_slice_record("build-pass"),
        *approvals(others),
        dissent(dissenter, (TRUNCATION,), verdict="blocked"),
    ]


def a_plan(**fields):
    base = {
        "author": PLAN_ENGINE,
        "scope": "full-diff",
        "basis": {"tree_sha": "t1", "pass": "first"},
        "rationale": "x",
    }
    base.update(fields)
    return a_slice_record("review-plan", **base)


def implementer_start():
    return a_slice_record("dispatch-start", author=IMPLEMENTER, responding_to=[1])


def an_intake(**fields):
    base = {
        "author": HUMAN,
        "request": "add a specialty filter to the vet list",
        "decisions": ["ship it on the existing list page"],
    }
    base.update(fields)
    return a_slice_record("intake-decision", **base)


def a_request(author=IMPLEMENTER, target=DESIGNER, **fields):
    return a_slice_record(
        "consultation-request", author=author, target=target, **fields
    )


def a_response(author=DESIGNER, in_response_to=2, **fields):
    return a_slice_record(
        "consultation-response", author=author, in_response_to=in_response_to, **fields
    )


class DecisionJson(unittest.TestCase):
    def test_a_dispatch_lists_its_keys_in_contract_order(self):
        decision = dispatch([IMPLEMENTER], "a-rule", "why", THIS_REQ_ID, round=1)

        payload = decision.as_json()

        self.assertEqual(
            list(payload), ["decision", "next", "rule", "reason", "req_id", "context"]
        )
        self.assertEqual(payload["next"], [IMPLEMENTER])

    def test_a_bounce_carries_its_errors_first_inside_the_context(self):
        decision = dispatch(
            [IMPLEMENTER], "a-rule", "why", THIS_REQ_ID, errors=SOME_ERRORS, round=1
        )

        payload = decision.as_json()

        self.assertNotIn("errors", payload)
        self.assertEqual(list(payload["context"]), ["errors", "round"])

    def test_a_blocked_decision_lists_errors_before_the_context(self):
        decision = blocked("a-rule", "why", THIS_REQ_ID, SOME_ERRORS, cause="x")

        self.assertEqual(
            list(decision.as_json()),
            ["decision", "rule", "reason", "req_id", "errors", "context"],
        )

    def test_an_escalate_lists_its_keys_in_contract_order(self):
        decision = escalate("a-rule", "why", THIS_REQ_ID, author="x")

        self.assertEqual(
            list(decision.as_json()),
            ["decision", "rule", "reason", "req_id", "context"],
        )

    def test_empty_payload_fields_are_omitted(self):
        payload = escalate("a-rule", "why").as_json()

        self.assertEqual(
            payload, {"decision": "escalate", "rule": "a-rule", "reason": "why"}
        )

    def test_a_falsy_req_id_is_omitted(self):
        self.assertNotIn("req_id", blocked("a-rule", "why", "").as_json())


class SliceSelection(unittest.TestCase):
    def test_an_empty_log_escalates_with_no_active_slice(self):
        decision = route()

        self.assertEqual(decision.kind, "escalate")
        self.assertEqual(decision.rule, "no-active-slice")

    def test_a_latest_record_without_a_req_id_blocks(self):
        decision = route({"type": "prd-entry", "ts": SOME_TS, "author": "tester"})

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "missing-req-id")

    def test_an_unknown_req_id_blocks(self):
        decision = route(a_slice_record("prd-entry"), req_id="REQ-Z-999")

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "unknown-req-id")
        self.assertEqual(decision.req_id, "REQ-Z-999")

    def test_the_req_id_argument_selects_the_slice(self):
        decision = route(
            a_slice_record("prd-entry"),
            a_slice_record("prd-entry", req_id=OTHER_REQ_ID),
            req_id=THIS_REQ_ID,
        )

        self.assertEqual(decision.req_id, THIS_REQ_ID)
        self.assertEqual(decision.next, (DESIGNER,))

    def test_the_latest_record_names_the_slice_by_default(self):
        decision = route(
            a_slice_record("prd-entry"),
            a_slice_record("prd-entry", req_id=OTHER_REQ_ID),
        )

        self.assertEqual(decision.req_id, OTHER_REQ_ID)

    def test_a_malformed_reviewer_roster_blocks_as_layout_invalid(self):
        layout = {"harness": {"extra_reviewers": EXTRA_REVIEWER}}

        decision = route(a_slice_record("build-pass"), layout=layout)

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "layout-invalid")

    def test_a_log_of_root_notes_alone_escalates_with_no_substantive_record(self):
        note = a_slice_record(
            "design-doc-autofix", author=ROOT, file="docs/system-design.md"
        )

        decision = route(note)

        self.assertEqual(decision.kind, "escalate")
        self.assertEqual(decision.rule, "no-substantive-record")


class IntakeRow(unittest.TestCase):
    def test_an_intake_decision_dispatches_the_product_expert(self):
        decision = route(an_intake())

        self.assertEqual(decision.kind, "dispatch")
        self.assertEqual(decision.rule, "intake-ready")
        self.assertEqual(decision.next, (PRODUCT,))

    def test_an_invalid_intake_blocks_for_the_owner(self):
        # No agent bounce target exists for a human-authored record: the halt
        # puts the fix with the owner.
        decision = route(an_intake(), gate=FakeGate(intake_decision=SOME_ERRORS))

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "intake-record-invalid")
        self.assertEqual(decision.errors, tuple(SOME_ERRORS))

    def test_a_prd_entry_supersedes_the_intake_row(self):
        decision = route(an_intake(), a_slice_record("prd-entry", author=PRODUCT))

        self.assertEqual(decision.rule, "prd-approved")
        self.assertEqual(decision.next, (DESIGNER,))


class PrdGate(unittest.TestCase):
    def test_a_passing_prd_entry_dispatches_the_designer(self):
        decision = route(a_slice_record("prd-entry", author=PRODUCT))

        self.assertEqual(decision.kind, "dispatch")
        self.assertEqual(decision.rule, "prd-approved")
        self.assertEqual(decision.next, (DESIGNER,))

    def test_a_gate_failure_bounces_the_product_expert_with_the_errors(self):
        decision = route(
            a_slice_record("prd-entry"), gate=FakeGate(prd_entry=SOME_ERRORS)
        )

        self.assertEqual(decision.kind, "dispatch")
        self.assertEqual(decision.rule, "prd-gate-failed")
        self.assertEqual(decision.next, (PRODUCT,))
        self.assertEqual(decision.context["errors"], SOME_ERRORS)

    def test_a_changed_non_goal_without_an_override_bounces(self):
        decision = route(a_slice_record("prd-entry"), delta=SOME_DELTA)

        self.assertEqual(decision.rule, "prd-gate-failed")
        self.assertIn("NG-5", " ".join(decision.context["errors"]))

    def test_a_dispatch_override_after_an_intake_on_any_slice_bounces(self):
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "yes",
            "source": "dispatch",
        }
        decision = route(
            an_intake(req_id=OTHER_REQ_ID),
            a_slice_record("prd-entry", scope_overrides=[override]),
            delta=SOME_DELTA,
        )

        self.assertEqual(decision.rule, "prd-gate-failed")
        self.assertIn(
            "not valid once a human intake-decision exists",
            decision.context["errors"][0],
        )

    def test_an_unreadable_scope_lock_baseline_fails_closed(self):
        decision = route(a_slice_record("prd-entry"), delta=None)

        self.assertEqual(decision.rule, "prd-gate-failed")
        self.assertIn("fails closed", " ".join(decision.context["errors"]))

    def test_a_designer_authored_sibling_prd_entry_escalates_as_refactor_first(self):
        # Route must not advance the sibling on its own; ordering is the
        # coordinator's call.
        decision = route(
            a_slice_record("prd-entry"),
            a_slice_record("design-block", verdict="refactor-first"),
            a_slice_record("prd-entry", req_id=OTHER_REQ_ID, author=DESIGNER),
        )

        self.assertEqual(decision.kind, "escalate")
        self.assertEqual(decision.rule, "refactor-first")


class DesignGate(unittest.TestCase):
    def test_an_implementable_verdict_dispatches_the_implementer(self):
        decision = route(
            a_slice_record("prd-entry"),
            a_slice_record("design-block", verdict="covered"),
        )

        self.assertEqual(decision.rule, "design-approved")
        self.assertEqual(decision.next, (IMPLEMENTER,))
        self.assertEqual(decision.context["verdict"], "covered")

    def test_a_rated_first_dispatch_runs_the_base_tier(self):
        decision = route(
            a_slice_record(
                "design-block", verdict="covered", implementation_effort="routine"
            )
        )

        self.assertEqual(decision.rule, "design-approved")
        self.assertEqual(decision.next, (IMPLEMENTER,))
        self.assertEqual(decision.context["tier_reason"], "initial")

    def test_an_unknown_verdict_bounces_the_designer(self):
        decision = route(a_slice_record("design-block", verdict="bogus"))

        self.assertEqual(decision.kind, "dispatch")
        self.assertEqual(decision.rule, "design-gate-failed")
        self.assertEqual(decision.next, (DESIGNER,))

    def test_a_gate_failure_bounces_the_designer_with_the_errors(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            gate=FakeGate(design_block=SOME_ERRORS),
        )

        self.assertEqual(decision.rule, "design-gate-failed")
        self.assertEqual(decision.context["errors"], SOME_ERRORS)

    def test_a_boolean_supersedes_pointer_fails_the_gate(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_slice_record(
                "design-block", verdict="covered", supersedes_record_at=True
            ),
        )

        self.assertEqual(decision.rule, "design-gate-failed")
        self.assertIn("supersedes_record_at (True)", decision.context["errors"][0])

    def test_a_dangling_supersedes_pointer_fails_the_gate(self):
        decision = route(
            a_slice_record("prd-entry"),
            a_slice_record("design-block", verdict="covered", supersedes_record_at=99),
        )

        self.assertEqual(decision.next, (DESIGNER,))
        self.assertEqual(decision.rule, "design-gate-failed")
        self.assertIn("supersedes_record_at", decision.context["errors"][0])

    def test_a_valid_supersedes_pointer_passes_the_gate(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_slice_record("build-failure", retry=1),
            a_slice_record("design-block", verdict="minor", supersedes_record_at=1),
        )

        self.assertEqual(decision.next, (IMPLEMENTER,))
        self.assertEqual(decision.rule, "design-approved")

    def test_a_conflicting_verdict_blocks_with_its_escalations(self):
        decision = route(
            a_slice_record("design-block", verdict="conflicting", escalations=["e1"])
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "design-conflict")
        self.assertEqual(decision.context["escalations"], ["e1"])
        self.assertEqual(decision.errors, ())

    def test_a_conflicting_verdict_without_escalations_names_the_gap(self):
        decision = route(a_slice_record("design-block", verdict="conflicting"))

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "design-conflict")
        self.assertIn("no escalations", decision.errors[0])

    def test_a_refactor_first_verdict_escalates_to_the_coordinator(self):
        decision = route(a_slice_record("design-block", verdict="refactor-first"))

        self.assertEqual(decision.kind, "escalate")
        self.assertEqual(decision.rule, "refactor-first")


class BuildPassRow(unittest.TestCase):
    def test_a_build_pass_dispatches_the_full_roster(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_slice_record("build-pass"),
        )

        self.assertEqual(decision.next, FULL_ROSTER)
        self.assertEqual(decision.rule, "reviews-needed")

    def test_a_first_pass_carries_round_one_without_a_bar(self):
        decision = route(a_slice_record("build-pass"))

        self.assertEqual(decision.rule, "reviews-needed")
        self.assertEqual(decision.context["round"], 1)
        self.assertNotIn("finding_bar", decision.context)
        self.assertEqual(decision.context["prompt_note"], "Review round 1.")

    def test_a_planless_build_pass_names_the_fail_closed_gap(self):
        # An absent plan must be distinguishable from a deliberate full
        # battery in the decision the board renders.
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_slice_record("build-pass"),
        )

        self.assertIn("no review-plan on record", decision.reason)

    def test_a_build_pass_after_a_build_failure_gates_reviews(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_slice_record("build-failure", retry=1),
            a_slice_record("build-pass"),
        )

        self.assertEqual(decision.next, FULL_ROSTER)
        self.assertEqual(decision.rule, "reviews-needed")

    def test_a_layout_extra_reviewer_joins_the_roster(self):
        decision = route(a_slice_record("build-pass"), layout=EXTRA_REVIEWER_LAYOUT)

        self.assertEqual(decision.next, (*FULL_ROSTER, EXTRA_REVIEWER))

    def test_an_invalid_build_pass_bounces_the_implementer(self):
        decision = route(
            a_slice_record("build-pass"), gate=FakeGate(build_pass=SOME_ERRORS)
        )

        self.assertEqual(decision.kind, "dispatch")
        self.assertEqual(decision.next, (IMPLEMENTER,))
        self.assertEqual(decision.rule, "build-record-invalid")
        self.assertEqual(decision.context["errors"], SOME_ERRORS)

    def test_review_activity_without_a_build_pass_escalates(self):
        decision = route(approved(A_REVIEWER))

        self.assertEqual(decision.kind, "escalate")
        self.assertEqual(decision.rule, "review-without-build-pass")


class FindingsDispatch(unittest.TestCase):
    def test_changes_requested_routes_to_the_implementer(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[CLARIFY]),
        )

        self.assertEqual(decision.next, (IMPLEMENTER,))
        self.assertEqual(decision.rule, "process-findings")
        self.assertEqual(decision.context["reviewers"], [A_REVIEWER])

    def test_a_blocked_verdict_routes_like_changes_requested(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[CRITICAL_BLOCKED], verdict="blocked"),
        )

        self.assertEqual(decision.next, (IMPLEMENTER,))
        self.assertEqual(decision.rule, "process-findings")

    def test_an_escalate_finding_in_an_approved_record_joins_the_split(self):
        # The escalate tag crosses the approved boundary: the implementer
        # receives it to append the escalations file, and the round halts
        # after processing.
        escalate_finding = {
            "tag": "escalate",
            "location": "src/auth/session:10",
            "description": "sev",
        }
        prd_finding = {
            "tag": "blocked",
            "location": "docs/prd.md:9",
            "description": "prd",
            "severity": "critical",
        }

        decision = route(
            a_slice_record("build-pass"),
            *approvals(FULL_ROSTER[:2]),
            dissent(ANOTHER_REVIEWER, [escalate_finding], verdict="approved"),
            dissent(findings=[prd_finding]),
        )

        self.assertEqual(decision.rule, "process-findings")
        self.assertIn(IMPLEMENTER, decision.next)
        self.assertIn(PRODUCT, decision.next)
        self.assertTrue(decision.context["halt_after"])
        self.assertEqual(decision.context["escalate_findings"], 1)

    def test_findings_split_by_artifact_owner(self):
        findings = [
            {
                "tag": "clarify",
                "location": "src/widget:1",
                "description": "code",
                "clarify_target": DESIGNER,
            },
            {
                "tag": "blocked",
                "location": "docs/prd.md:9",
                "description": "prd",
                "severity": "critical",
            },
            {
                "tag": "clarify",
                "location": "docs/adr/x.md:3",
                "description": "adr",
                "clarify_target": DESIGNER,
            },
            autofix(location="docs/system-design.md:7"),
        ]

        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=findings),
        )

        self.assertEqual(decision.next, (IMPLEMENTER, PRODUCT, DESIGNER))
        self.assertEqual(decision.context["root_autofix"], 1)

    def test_an_autofix_only_round_escalates(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[autofix(location="docs/system-design.md:7")]),
        )

        self.assertEqual(decision.kind, "escalate")
        self.assertEqual(decision.rule, "autofix-only-round")

    def test_a_prd_autofix_finding_is_root_applied(self):
        # An autofix-tagged PRD finding must not dispatch the product expert,
        # whose prd-entry would re-flow the slice from design triage.
        findings = [
            {
                "tag": "blocked",
                "location": "src/widget:1",
                "description": "code",
                "severity": "critical",
            },
            autofix(location="docs/prd.md:12"),
        ]

        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=findings),
        )

        self.assertEqual(decision.next, (IMPLEMENTER,))
        self.assertEqual(decision.context["root_autofix"], 1)

    def test_an_escalate_finding_on_changes_requested_flags_the_halt(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[ESCALATE]),
        )

        self.assertEqual(decision.rule, "process-findings")
        self.assertEqual(decision.context["escalate_findings"], 1)
        self.assertTrue(decision.context["halt_after"])

    def test_an_escalate_round_halts_before_the_re_review(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[ESCALATE]),
            a_slice_record("build-pass"),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "escalate-finding-halt")

    def test_feedback_after_the_build_pass_lifts_the_escalate_halt(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[ESCALATE]),
            a_slice_record("build-pass"),
            approved(A_REVIEWER),
        )

        self.assertEqual(decision.rule, "reviews-needed")
        self.assertEqual(decision.next, OTHER_REVIEWERS)

    def test_an_escalate_finding_on_approved_verdicts_blocks(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[ESCALATE], verdict="approved"),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "escalate-on-approved")
        self.assertEqual(decision.context["escalate_findings"], 1)

    def test_an_all_autofix_round_on_a_rated_slice_dispatches_the_routine_fix(self):
        decision = route(
            a_slice_record(
                "design-block", verdict="covered", implementation_effort="involved"
            ),
            implementer_start(),
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[AUTOFIX]),
        )

        self.assertEqual(decision.rule, "process-findings")
        self.assertEqual(decision.next, (ROUTINE_IMPLEMENTER,))
        self.assertEqual(decision.context["tier_reason"], "fix-round:all-autofix")

    def test_a_new_build_pass_starts_the_next_round(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[CLARIFY]),
            a_slice_record("build-pass"),
        )

        self.assertEqual(decision.next, FULL_ROSTER)
        self.assertEqual(decision.rule, "reviews-needed")


class FeedbackGate(unittest.TestCase):
    def test_a_schema_gate_failure_bounces_the_reviewer_with_the_errors(self):
        decision = route(
            a_slice_record("build-pass"),
            a_plan(risk="low", roster=[A_REVIEWER]),
            approved(A_REVIEWER),
            gate=FakeGate(review_feedback=SOME_ERRORS),
        )

        self.assertEqual(decision.next, (A_REVIEWER,))
        self.assertEqual(decision.rule, "review-record-invalid")
        self.assertEqual(decision.context["errors"], SOME_ERRORS)
        self.assertEqual(decision.context["round"], 1)

    def test_a_clarify_finding_without_a_target_bounces_the_reviewer(self):
        finding = {"tag": "clarify", "location": "src/widget:1", "description": "d"}

        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[finding]),
        )

        self.assertEqual(decision.next, (A_REVIEWER,))
        self.assertEqual(decision.rule, "review-record-invalid")
        self.assertIn("clarify_target", decision.context["errors"][0])

    def test_a_routable_finding_without_a_severity_bounces_the_reviewer(self):
        finding = {"tag": "blocked", "location": "src/widget:1", "description": "d"}

        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[finding], verdict="blocked"),
        )

        self.assertEqual(decision.next, (A_REVIEWER,))
        self.assertEqual(decision.rule, "review-record-invalid")
        self.assertIn("no severity", decision.context["errors"][0])

    def test_an_autofix_finding_on_an_approved_verdict_bounces(self):
        # Routing only processes findings from non-approved verdicts, so the
        # fix would be dropped silently and re-raised a round later.
        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[AUTOFIX], verdict="approved"),
        )

        self.assertEqual(decision.next, (A_REVIEWER,))
        self.assertEqual(decision.rule, "review-record-invalid")
        self.assertIn("approved verdict", decision.context["errors"][0])

    def test_an_escalate_finding_on_an_approved_verdict_stays_valid(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[ESCALATE], verdict="approved"),
        )

        self.assertNotEqual(decision.rule, "review-record-invalid")


class ReviewerLadder(unittest.TestCase):
    def test_a_silent_start_after_feedback_retries_the_reviewer_once(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(),
            a_slice_record("dispatch-start", author=A_REVIEWER),
        )

        self.assertEqual(decision.next, (A_REVIEWER,))
        self.assertEqual(decision.rule, "reviewer-stall-retry")
        self.assertEqual(decision.context["prompt_note"], "Review round 1.")

    def test_two_silent_starts_block_as_stalled(self):
        decision = route(
            a_slice_record("build-pass"),
            *[a_slice_record("dispatch-start", author=r) for r in FULL_ROSTER],
            *approvals(OTHER_REVIEWERS),
            a_slice_record("dispatch-start", author=A_REVIEWER),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "reviewer-stalled")
        self.assertEqual(decision.context["stalled"], [A_REVIEWER])

    def test_a_dissent_without_findings_re_dispatches_the_reviewer(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[]),
        )

        self.assertEqual(decision.next, (A_REVIEWER,))
        self.assertEqual(decision.rule, "reviewer-empty-findings")


class ReviewRoundConvergence(unittest.TestCase):
    """The review ladder: the round counter, the critical-only gate from round
    REVIEW_ROUND_CAP, and the blocked stop past REVIEW_ROUND_CAP fix rounds."""

    def test_second_round_non_critical_dissent_still_processes(self):
        decision = route(*review_pass(), *review_pass())

        self.assertEqual(decision.rule, "process-findings")
        self.assertEqual(decision.context["round"], 2)

    def test_round_three_non_critical_dissent_bounces_the_reviewer(self):
        decision = route(*review_pass(), *review_pass(), *review_pass())

        self.assertEqual(decision.rule, "review-record-invalid")
        self.assertEqual(decision.next, (A_REVIEWER,))
        self.assertIn("critical-only round (round 3)", decision.context["errors"][0])

    def test_round_three_critical_dissent_processes_findings(self):
        decision = route(
            *review_pass(), *review_pass(), *review_pass(severity="critical")
        )

        self.assertEqual(decision.rule, "process-findings")
        self.assertEqual(decision.context["round"], 3)

    def test_round_four_dissent_blocks_as_non_convergence(self):
        decision = route(
            *review_pass(),
            *review_pass(),
            *review_pass(severity="critical"),
            *review_pass(severity="critical"),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "review-non-convergence")
        self.assertEqual(decision.context["cause"], "round-cap")
        self.assertEqual(decision.context["round"], 4)
        self.assertEqual(decision.context["dissenters"], [A_REVIEWER])

    def test_a_superseding_design_block_resets_the_round(self):
        design = a_slice_record("design-block", verdict="new", author=DESIGNER)
        superseding = a_slice_record(
            "design-block", verdict="new", author=DESIGNER, supersedes_record_at=1
        )

        decision = route(
            design,
            *review_pass(),
            *review_pass(),
            *review_pass(severity="critical"),
            superseding,
            *review_pass(),
        )

        self.assertEqual(decision.rule, "process-findings")
        self.assertEqual(decision.context["round"], 1)

    def test_reviews_needed_names_the_round_and_the_critical_only_bar(self):
        decision = route(*review_pass(), *review_pass(), a_slice_record("build-pass"))

        self.assertEqual(decision.rule, "reviews-needed")
        self.assertEqual(decision.context["round"], 3)
        self.assertEqual(decision.context["finding_bar"], "critical-only")
        self.assertTrue(
            decision.context["prompt_note"].startswith("Review round 3: critical-only.")
        )

    def test_clarify_only_dissent_stays_legal_on_capped_rounds(self):
        decision = route(
            *review_pass(),
            *review_pass(),
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[CLARIFY]),
        )

        self.assertEqual(decision.rule, "process-findings")
        self.assertEqual(decision.context["round"], 3)

    def test_escalate_only_dissent_stays_legal_on_capped_rounds(self):
        decision = route(
            *review_pass(),
            *review_pass(),
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[ESCALATE]),
        )

        self.assertEqual(decision.rule, "process-findings")
        self.assertTrue(decision.context["halt_after"])

    def test_a_second_below_bar_record_blocks_as_bounce_repeat(self):
        decision = route(
            *review_pass(),
            *review_pass(),
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(),
            dissent(),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "review-non-convergence")
        self.assertEqual(decision.context["cause"], "bounce-repeat")

    def test_a_third_dissent_in_one_pass_blocks_as_pass_churn(self):
        critical = (autofix("critical"),)

        decision = route(
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=critical),
            dissent(findings=critical),
            dissent(findings=critical),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "review-non-convergence")
        self.assertEqual(decision.context["cause"], "pass-churn")
        self.assertEqual(decision.context["dissenters"], [A_REVIEWER])

    def test_three_truncation_only_passes_block_as_a_truncation_run(self):
        decision = route(*truncation_pass(), *truncation_pass(), *truncation_pass())

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "review-non-convergence")
        self.assertEqual(decision.context["cause"], "truncation-run")

    def test_off_roster_records_never_tick_the_counter(self):
        forged = [a_slice_record("build-pass"), dissent(OFF_ROSTER_REVIEWER)]

        decision = route(*forged, *forged, *review_pass())

        self.assertEqual(decision.rule, "process-findings")
        self.assertEqual(decision.context["round"], 1)

    def test_empty_findings_dissent_keeps_its_own_diagnosis_on_capped_rounds(self):
        decision = route(
            *review_pass(),
            *review_pass(),
            a_slice_record("build-pass"),
            *approvals(OTHER_REVIEWERS),
            dissent(findings=[]),
        )

        self.assertEqual(decision.rule, "reviewer-empty-findings")
        self.assertEqual(decision.context["round"], 3)

    def extra_pass(self, severity="fixable"):
        return [
            a_slice_record("build-pass"),
            *approvals(),
            dissent(EXTRA_REVIEWER, (autofix(severity),)),
        ]

    def test_an_extra_reviewer_rides_the_same_ladder(self):
        decision = route(
            *self.extra_pass(),
            *self.extra_pass(),
            *self.extra_pass(),
            layout=EXTRA_REVIEWER_LAYOUT,
        )

        self.assertEqual(decision.rule, "review-record-invalid")
        self.assertEqual(decision.next, (EXTRA_REVIEWER,))
        self.assertIn("critical-only round (round 3)", decision.context["errors"][0])

    def test_an_extra_reviewer_dissent_trips_the_cap(self):
        decision = route(
            *self.extra_pass(),
            *self.extra_pass(),
            *self.extra_pass("critical"),
            *self.extra_pass("critical"),
            layout=EXTRA_REVIEWER_LAYOUT,
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "review-non-convergence")
        self.assertEqual(decision.context["dissenters"], [EXTRA_REVIEWER])

    def test_a_narrowed_fix_pass_still_gates_critical_only(self):
        decision = route(
            *review_pass(),
            *review_pass(),
            a_slice_record("build-pass"),
            a_plan(risk="low", roster=[A_REVIEWER], scope="fix-delta"),
            dissent(),
        )

        self.assertEqual(decision.rule, "review-record-invalid")
        self.assertEqual(decision.next, (A_REVIEWER,))
        self.assertIn("critical-only round (round 3)", decision.context["errors"][0])


class ReviewPlan(unittest.TestCase):
    """Risk-proportional review: the active review-plan names the pass's roster;
    a gray plan dispatches the planner; absent or invalid plans fail closed to
    the full battery."""

    def test_a_low_plan_dispatches_only_its_roster(self):
        decision = route(
            a_slice_record("build-pass"), a_plan(risk="low", roster=[A_REVIEWER])
        )

        self.assertEqual(decision.rule, "reviews-needed")
        self.assertEqual(decision.next, (A_REVIEWER,))

    def test_no_plan_fails_closed_to_the_full_battery(self):
        decision = route(a_slice_record("build-pass"))

        self.assertEqual(decision.rule, "reviews-needed")
        self.assertEqual(decision.next, FULL_ROSTER)

    def test_an_invalid_plan_fails_closed_and_names_the_gap(self):
        decision = route(
            a_slice_record("build-pass"), a_plan(risk="low", roster=["nobody"])
        )

        self.assertEqual(decision.rule, "reviews-needed")
        self.assertEqual(decision.next, FULL_ROSTER)
        self.assertIn("empty or unknown roster", decision.reason)

    def test_a_gray_plan_dispatches_the_planner(self):
        decision = route(a_slice_record("build-pass"), a_plan(risk="gray"))

        self.assertEqual(decision.rule, "plan-gray")
        self.assertEqual(decision.next, (PLANNER,))

    def test_a_gray_plan_from_the_planner_bounces(self):
        decision = route(
            a_slice_record("build-pass"), a_plan(risk="gray", author=PLANNER)
        )

        self.assertEqual(decision.kind, "dispatch")
        self.assertEqual(decision.rule, "plan-gray-invalid")
        self.assertEqual(decision.next, (PLANNER,))

    def test_a_silent_planner_start_retries_once(self):
        decision = route(
            a_slice_record("build-pass"),
            a_plan(risk="gray"),
            a_slice_record("dispatch-start", author=PLANNER),
        )

        self.assertEqual(decision.rule, "planner-stall-retry")
        self.assertEqual(decision.next, (PLANNER,))

    def test_two_silent_planner_starts_block_as_stalled(self):
        decision = route(
            a_slice_record("build-pass"),
            a_plan(risk="gray"),
            a_slice_record("dispatch-start", author=PLANNER),
            a_slice_record("dispatch-start", author=PLANNER),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "planner-stalled")

    def test_the_planner_resolution_dispatches_its_roster(self):
        resolved = ["code-quality-reviewer", "test-reviewer", "security-reviewer"]

        decision = route(
            a_slice_record("build-pass"),
            a_plan(risk="gray"),
            a_slice_record("dispatch-start", author=PLANNER),
            a_plan(risk="low", author=PLANNER, roster=resolved),
        )

        self.assertEqual(decision.rule, "reviews-needed")
        self.assertEqual(decision.next, tuple(resolved))

    def test_a_plan_roster_completion_grades(self):
        decision = route(
            a_slice_record("build-pass"),
            a_plan(risk="low", roster=[A_REVIEWER]),
            approved(A_REVIEWER),
        )

        self.assertEqual(decision.rule, "grade")
        self.assertEqual(decision.next, (GRADER,))

    def test_a_plan_from_a_non_engine_author_fails_closed(self):
        decision = route(
            a_slice_record("build-pass"),
            a_plan(risk="low", author=IMPLEMENTER, roster=[A_REVIEWER]),
        )

        self.assertEqual(decision.rule, "reviews-needed")
        self.assertEqual(decision.next, FULL_ROSTER)
        self.assertIn("neither the engine nor a dispatched planner", decision.reason)

    def test_a_planner_plan_without_a_roster_bounces_to_the_planner(self):
        decision = route(
            a_slice_record("build-pass"),
            a_plan(risk="gray"),
            a_slice_record("dispatch-start", author=PLANNER),
            a_plan(risk="low", author=PLANNER),
        )

        self.assertEqual(decision.rule, "plan-roster-invalid")
        self.assertEqual(decision.next, (PLANNER,))


class OutstandingDissent(unittest.TestCase):
    """The completion invariant: a fix plan that drops a reviewer still holding a
    non-approved verdict never grades."""

    def first_pass_with_dissent(self):
        return [
            a_slice_record("build-pass"),
            a_plan(risk="high", roster=list(FULL_ROSTER)),
            *approvals(r for r in FULL_ROSTER if r != ANOTHER_REVIEWER),
            dissent(ANOTHER_REVIEWER, [CRITICAL_BLOCKED]),
        ]

    def narrowed_fix_pass(self):
        return [
            a_slice_record("build-pass"),
            a_plan(risk="low", roster=[A_REVIEWER]),
            approved(A_REVIEWER),
        ]

    def test_a_plan_dropping_a_prior_dissenter_re_runs_it(self):
        decision = route(*self.first_pass_with_dissent(), *self.narrowed_fix_pass())

        self.assertEqual(decision.rule, "outstanding-dissent")
        self.assertEqual(decision.next, (ANOTHER_REVIEWER,))
        # Round only, never the bar: this path's records skip Gate 4.
        self.assertEqual(
            decision.context["prompt_note"],
            f"Review round {decision.context['round']}.",
        )

    def test_an_initial_design_block_keeps_dissent_outstanding(self):
        # A fix-round design record without supersedes_record_at is not a
        # cycle reset.
        decision = route(
            *self.first_pass_with_dissent(),
            a_slice_record("design-block", author=DESIGNER, verdict="minor"),
            *self.narrowed_fix_pass(),
        )

        self.assertEqual(decision.rule, "outstanding-dissent")
        self.assertEqual(decision.next, (ANOTHER_REVIEWER,))

    def test_a_superseding_design_block_voids_prior_dissent(self):
        decision = route(
            a_slice_record("design-block", author=DESIGNER, verdict="minor"),
            *self.first_pass_with_dissent(),
            a_slice_record(
                "design-block", author=DESIGNER, verdict="minor", supersedes_record_at=1
            ),
            *self.narrowed_fix_pass(),
        )

        self.assertEqual(decision.rule, "grade")
        self.assertEqual(decision.next, (GRADER,))

    def test_a_forged_supersedes_pointer_does_not_void_dissent(self):
        # Line 1 is the build-pass, not a design-block.
        decision = route(
            *self.first_pass_with_dissent(),
            a_slice_record(
                "design-block", author=DESIGNER, verdict="minor", supersedes_record_at=1
            ),
            *self.narrowed_fix_pass(),
        )

        self.assertEqual(decision.rule, "outstanding-dissent")
        self.assertEqual(decision.next, (ANOTHER_REVIEWER,))

    def test_an_outstanding_dissenter_stalls_after_two_re_dispatches(self):
        decision = route(
            *self.first_pass_with_dissent(),
            *self.narrowed_fix_pass(),
            a_slice_record("dispatch-start", author=ANOTHER_REVIEWER),
            a_slice_record("dispatch-start", author=ANOTHER_REVIEWER),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "reviewer-stalled")
        self.assertEqual(decision.context["stalled"], [ANOTHER_REVIEWER])


class Completion(unittest.TestCase):
    def test_all_approved_dispatches_the_grader(self):
        decision = route(a_slice_record("build-pass"), *approvals())

        self.assertEqual(decision.next, (GRADER,))
        self.assertEqual(decision.rule, "grade")

    def test_a_grader_verdict_completes_the_feature(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(),
            a_slice_record("grader-verdict", author=GRADER, verdict="skim"),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "feature-complete")
        self.assertEqual(decision.context["verdict"], "skim")

    def test_grader_features_without_a_verdict_re_dispatch_the_grader(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(),
            a_slice_record("grader-features", author=GRADER, features=[]),
        )

        self.assertEqual(decision.next, (GRADER,))
        self.assertEqual(decision.rule, "grade-continue")

    def test_grading_off_completes_without_the_grader(self):
        decision = route(a_slice_record("build-pass"), *approvals(), layout=GRADING_OFF)

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "feature-complete")
        self.assertNotIn("verdict", decision.context)
        self.assertIn("grading disabled", decision.reason)

    def test_grading_off_still_honors_a_manual_grader_verdict(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(),
            a_slice_record("grader-verdict", author=GRADER, verdict="skim"),
            layout=GRADING_OFF,
        )

        self.assertEqual(decision.rule, "feature-complete")
        self.assertEqual(decision.context["verdict"], "skim")

    def test_grading_on_dispatches_the_grader(self):
        decision = route(a_slice_record("build-pass"), *approvals(), layout=GRADING_ON)

        self.assertEqual(decision.next, (GRADER,))
        self.assertEqual(decision.rule, "grade")

    def test_a_mistyped_grading_toggle_fails_open_to_grading(self):
        # The doctor is the layer that flags the typo.
        decision = route(
            a_slice_record("build-pass"), *approvals(), layout=GRADING_MISTYPED
        )

        self.assertEqual(decision.next, (GRADER,))
        self.assertEqual(decision.rule, "grade")

    def sibling_approvals(self):
        return [
            a_slice_record("prd-entry"),
            a_slice_record("design-block", verdict="refactor-first"),
            a_slice_record("build-pass", req_id=OTHER_REQ_ID),
            *[
                a_slice_record(
                    "review-feedback",
                    req_id=OTHER_REQ_ID,
                    author=r,
                    verdict="approved",
                    findings=[],
                )
                for r in FULL_ROSTER
            ],
        ]

    def test_a_graded_refactor_sibling_resumes_the_original_slice(self):
        decision = route(
            *self.sibling_approvals(),
            a_slice_record(
                "grader-verdict", req_id=OTHER_REQ_ID, author=GRADER, verdict="skim"
            ),
        )

        self.assertEqual(decision.next, (DESIGNER,))
        self.assertEqual(decision.rule, "refactor-resume")
        self.assertEqual(decision.context["original_req_id"], THIS_REQ_ID)
        self.assertEqual(decision.context["verdict"], "skim")

    def test_an_approved_refactor_sibling_resumes_when_grading_is_off(self):
        decision = route(*self.sibling_approvals(), layout=GRADING_OFF)

        self.assertEqual(decision.next, (DESIGNER,))
        self.assertEqual(decision.rule, "refactor-resume")
        self.assertEqual(decision.context["original_req_id"], THIS_REQ_ID)
        self.assertNotIn("verdict", decision.context)


class BuildFailureRecovery(unittest.TestCase):
    def test_a_failure_below_the_cap_re_dispatches_the_implementer(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_slice_record("build-failure", author=IMPLEMENTER, retry=1),
        )

        self.assertEqual(decision.next, (IMPLEMENTER,))
        self.assertEqual(decision.rule, "build-retry")
        self.assertEqual(decision.context["retry"], 1)

    def test_a_partial_failure_carries_the_partial_flag(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_slice_record("build-failure", retry=1, partial=True),
        )

        self.assertEqual(decision.rule, "build-retry")
        self.assertTrue(decision.context["partial"])

    def test_three_failures_re_triage_with_the_designer(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            *[a_slice_record("build-failure", retry=i) for i in (1, 2, 3)],
        )

        self.assertEqual(decision.next, (DESIGNER,))
        self.assertEqual(decision.rule, "build-non-convergence")
        self.assertEqual(decision.context["failures"], 3)

    def test_a_superseding_design_block_resets_the_retry_counter(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            *[a_slice_record("build-failure", retry=i) for i in (1, 2, 3)],
            a_slice_record("design-block", verdict="minor", supersedes_record_at=1),
            a_slice_record("build-failure", retry=1),
        )

        self.assertEqual(decision.next, (IMPLEMENTER,))
        self.assertEqual(decision.context["retry"], 1)

    def test_an_invalid_build_failure_bounces_the_implementer(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_slice_record("build-failure", retry=1),
            gate=FakeGate(build_failure=SOME_ERRORS),
        )

        self.assertEqual(decision.rule, "build-record-invalid")
        self.assertEqual(decision.next, (IMPLEMENTER,))
        self.assertEqual(decision.context["errors"], SOME_ERRORS)

    def test_a_failure_without_a_design_block_escalates(self):
        decision = route(a_slice_record("build-failure", retry=1))

        self.assertEqual(decision.kind, "escalate")
        self.assertEqual(decision.rule, "failure-without-design")

    def abort(self, reason):
        return route(
            a_slice_record("design-block", verdict="covered"),
            a_slice_record("build-failure", retry=1, abort_reason=reason),
        )

    def test_a_wrong_shape_abort_dispatches_the_product_expert(self):
        decision = self.abort("wrong-shape-slice")

        self.assertEqual(decision.rule, "abort-wrong-shape")
        self.assertEqual(decision.next, (PRODUCT,))

    def test_a_design_mismatch_abort_dispatches_the_designer(self):
        decision = self.abort("design-mismatch")

        self.assertEqual(decision.rule, "abort-design-mismatch")
        self.assertEqual(decision.next, (DESIGNER,))

    def test_a_prd_mismatch_abort_dispatches_the_product_expert(self):
        decision = self.abort("prd-mismatch")

        self.assertEqual(decision.rule, "abort-prd-mismatch")
        self.assertEqual(decision.next, (PRODUCT,))

    def test_a_missing_prerequisite_abort_blocks(self):
        decision = self.abort("prerequisite-missing")

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "abort-prerequisite")

    def test_an_unknown_abort_reason_escalates(self):
        decision = self.abort("solar-flare")

        self.assertEqual(decision.kind, "escalate")
        self.assertEqual(decision.rule, "abort-unknown")
        self.assertIn("solar-flare", decision.reason)


class TruncationRecovery(unittest.TestCase):
    def test_a_truncated_dispatch_continues_the_same_slice(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_slice_record("dispatch-start", author=IMPLEMENTER),
        )

        self.assertEqual(decision.next, (IMPLEMENTER,))
        self.assertEqual(decision.rule, "truncation-continue")
        self.assertEqual(decision.context["continuation"], 1)

    def test_a_continuation_runs_the_base_pin(self):
        # Recovery always runs base: a truncated routine dispatch continues
        # at the full pin.
        decision = route(
            a_slice_record(
                "design-block", verdict="covered", implementation_effort="routine"
            ),
            implementer_start(),
            implementer_start(),
        )

        self.assertEqual(decision.rule, "truncation-continue")
        self.assertEqual(decision.next, (IMPLEMENTER,))
        self.assertEqual(decision.context["tier_reason"], "recovery")

    def test_a_trailing_design_doc_autofix_does_not_mask_the_truncation(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_slice_record("dispatch-start", author=IMPLEMENTER),
            a_slice_record(
                "design-doc-autofix", author=ROOT, file="docs/system-design.md"
            ),
        )

        self.assertEqual(decision.rule, "truncation-continue")
        self.assertEqual(decision.context["continuation"], 1)

    def test_a_trailing_prd_autofix_does_not_mask_the_truncation(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_slice_record("dispatch-start", author=IMPLEMENTER),
            a_slice_record("prd-autofix", author=ROOT, file="docs/prd.md"),
        )

        self.assertEqual(decision.rule, "truncation-continue")
        self.assertEqual(decision.context["continuation"], 1)

    def test_a_grader_verdict_completes_its_own_dispatch_start(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(),
            a_slice_record("dispatch-start", author=GRADER),
            a_slice_record("grader-verdict", author=GRADER, verdict="skim"),
            a_slice_record(
                "design-doc-autofix", author=ROOT, file="docs/system-design.md"
            ),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "feature-complete")

    def test_three_consecutive_truncations_re_triage(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            *[a_slice_record("dispatch-start", author=IMPLEMENTER) for _ in range(3)],
        )

        self.assertEqual(decision.next, (DESIGNER,))
        self.assertEqual(decision.rule, "truncation-non-convergence")
        self.assertEqual(decision.context["continuations"], 3)

    def test_an_implementer_record_resets_the_truncation_run(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_slice_record("dispatch-start", author=IMPLEMENTER),
            a_slice_record("dispatch-start", author=IMPLEMENTER),
            a_request(),
            a_response(in_response_to=4),
            a_slice_record("dispatch-start", author=IMPLEMENTER),
        )

        self.assertEqual(decision.rule, "truncation-continue")
        self.assertEqual(decision.context["continuation"], 1)

    def test_an_implementer_start_without_a_design_block_escalates(self):
        decision = route(a_slice_record("dispatch-start", author=IMPLEMENTER))

        self.assertEqual(decision.kind, "escalate")
        self.assertEqual(decision.rule, "truncation-before-design")

    def test_a_truncated_designer_dispatch_escalates_as_undefined(self):
        decision = route(
            a_slice_record("prd-entry"),
            a_slice_record("dispatch-start", author=DESIGNER),
        )

        self.assertEqual(decision.kind, "escalate")
        self.assertEqual(decision.rule, "truncation-undefined")
        self.assertEqual(decision.context["author"], DESIGNER)


class Consultations(unittest.TestCase):
    def test_a_request_dispatches_its_target(self):
        decision = route(a_slice_record("design-block", verdict="covered"), a_request())

        self.assertEqual(decision.next, (DESIGNER,))
        self.assertEqual(decision.rule, "consultation-dispatch")
        self.assertEqual(decision.context["requester"], IMPLEMENTER)

    def test_a_response_returns_to_the_requester(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"), a_request(), a_response()
        )

        self.assertEqual(decision.next, (IMPLEMENTER,))
        self.assertEqual(decision.rule, "consultation-return")
        self.assertTrue(decision.context["resume"])

    def test_a_human_request_blocks_for_the_conversation(self):
        decision = route(
            a_slice_record("dispatch-start", author=PRODUCT),
            a_request(PRODUCT, HUMAN, question=SOME_QUESTION),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "human-consultation")
        self.assertEqual(decision.context["requester"], PRODUCT)
        self.assertEqual(decision.context["question"], SOME_QUESTION)

    def test_a_human_request_failing_its_gate_bounces_the_author(self):
        # The gate runs before the human branch: a malformed human request
        # bounces to its author, never blocks with a null question.
        decision = route(
            a_slice_record("prd-entry"),
            a_request(PRODUCT, HUMAN),
            gate=FakeGate(consultation_request=SOME_ERRORS),
        )

        self.assertEqual(decision.kind, "dispatch")
        self.assertEqual(decision.next, (PRODUCT,))
        self.assertEqual(decision.rule, "consultation-invalid")
        self.assertEqual(decision.context["errors"], SOME_ERRORS)

    def test_a_human_target_variant_bounces_the_author(self):
        decision = route(a_slice_record("prd-entry"), a_request(DESIGNER, "Human"))

        self.assertEqual(decision.kind, "dispatch")
        self.assertEqual(decision.next, (DESIGNER,))
        self.assertEqual(decision.rule, "consultation-invalid")

    def test_a_human_authored_request_fails_closed(self):
        decision = route(a_slice_record("prd-entry"), a_request(HUMAN, HUMAN))

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "consultation-invalid")

    def test_a_human_authored_variant_request_fails_closed(self):
        # The author guard precedes the exact-match bounce.
        decision = route(a_slice_record("prd-entry"), a_request(HUMAN, " human "))

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "consultation-invalid")

    def test_a_response_to_a_human_authored_request_fails_closed(self):
        decision = route(
            a_slice_record("prd-entry"), a_request(HUMAN, HUMAN), a_response(HUMAN, 2)
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "consultation-invalid")

    def test_a_pending_human_request_is_sticky_over_later_records(self):
        decision = route(
            a_slice_record("dispatch-start", author=PRODUCT),
            a_request(PRODUCT, HUMAN),
            a_slice_record("prd-entry"),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "human-consultation")
        self.assertEqual(decision.context["requester"], PRODUCT)

    def test_a_pending_human_request_is_sticky_over_a_reseeded_intake(self):
        decision = route(
            an_intake(request="Add cancelling."),
            a_slice_record("dispatch-start", author=PRODUCT),
            a_request(PRODUCT, HUMAN, question="Narrow NG-5?"),
            an_intake(request="Add cancelling."),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "human-consultation")
        self.assertIn("never supersedes", decision.reason)

    def test_a_pending_human_request_blocks_a_sibling_req_id(self):
        decision = route(a_request(PRODUCT, HUMAN), an_intake(req_id=OTHER_REQ_ID))

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "human-consultation")
        self.assertEqual(decision.req_id, THIS_REQ_ID)

    def test_a_superseded_human_request_releases_the_pause(self):
        decision = route(a_request(PRODUCT, HUMAN), a_request())

        self.assertEqual(decision.kind, "dispatch")
        self.assertEqual(decision.next, (DESIGNER,))

    def test_an_answered_human_request_does_not_hold_the_pause(self):
        decision = route(
            a_slice_record("prd-entry"),
            a_slice_record("dispatch-start", author=DESIGNER),
            a_request(DESIGNER, HUMAN),
            a_response(HUMAN, 3),
            a_slice_record("dispatch-start", author=DESIGNER),
            a_slice_record("design-block", author=DESIGNER, verdict="covered"),
        )

        self.assertEqual(decision.kind, "dispatch")
        self.assertEqual(decision.next, (IMPLEMENTER,))

    def test_a_human_request_shields_truncation_detection(self):
        decision = route(
            a_slice_record("prd-entry"),
            a_slice_record("dispatch-start", author=DESIGNER),
            a_request(DESIGNER, HUMAN),
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "human-consultation")

    def test_a_human_response_returns_to_the_requester(self):
        decision = route(
            a_slice_record("prd-entry"),
            a_slice_record("dispatch-start", author=DESIGNER),
            a_request(DESIGNER, HUMAN),
            a_response(HUMAN, 3),
        )

        self.assertEqual(decision.next, (DESIGNER,))
        self.assertEqual(decision.rule, "consultation-return")

    def test_a_response_from_the_wrong_author_bounces_the_responder(self):
        decision = route(a_request(), a_response(A_REVIEWER, 1))

        self.assertEqual(decision.kind, "dispatch")
        self.assertEqual(decision.next, (DESIGNER,))
        self.assertEqual(decision.rule, "consultation-invalid")
        self.assertTrue(decision.context["errors"])

    def test_a_response_with_a_dangling_pointer_blocks(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"), a_response(DESIGNER, 9)
        )

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "consultation-invalid")

    def test_a_response_with_a_boolean_pointer_blocks(self):
        decision = route(a_request(), a_response(DESIGNER, True))

        self.assertEqual(decision.kind, "blocked")
        self.assertEqual(decision.rule, "consultation-invalid")
        self.assertIn("in_response_to (True)", decision.errors[0])

    def test_a_pending_request_survives_a_trailing_design_doc_autofix(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_request(),
            a_slice_record(
                "design-doc-autofix", author=ROOT, file="docs/system-design.md"
            ),
        )

        self.assertEqual(decision.next, (DESIGNER,))
        self.assertEqual(decision.rule, "consultation-dispatch")

    def test_a_pending_request_survives_a_trailing_prd_autofix(self):
        decision = route(
            a_slice_record("design-block", verdict="covered"),
            a_request(target=PRODUCT),
            a_slice_record("prd-autofix", author=ROOT, file="docs/prd.md"),
        )

        self.assertEqual(decision.next, (PRODUCT,))
        self.assertEqual(decision.rule, "consultation-dispatch")

    def test_a_stale_response_is_validated_off_the_last_position(self):
        decision = route(
            a_request(),
            a_response(A_REVIEWER, 1),
            a_slice_record(
                "design-doc-autofix", author=ROOT, file="docs/system-design.md"
            ),
        )

        self.assertEqual(decision.kind, "dispatch")
        self.assertEqual(decision.next, (DESIGNER,))
        self.assertEqual(decision.rule, "consultation-invalid")

    def test_a_response_failing_its_schema_gate_bounces_the_responder(self):
        decision = route(
            a_request(),
            a_response(DESIGNER, 1),
            gate=FakeGate(consultation_response=SOME_ERRORS),
        )

        self.assertEqual(decision.kind, "dispatch")
        self.assertEqual(decision.next, (DESIGNER,))
        self.assertEqual(decision.rule, "consultation-invalid")
        self.assertEqual(decision.context["errors"], SOME_ERRORS)


class OffRosterRecords(unittest.TestCase):
    def test_an_off_roster_dissent_with_an_unhashable_author_still_routes(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(),
            dissent(["not", "a", "name"], [autofix()]),
        )

        self.assertEqual(decision.rule, "grade")


class RoutingInvariants(unittest.TestCase):
    """Cross-cutting invariants pinned as quantified properties: grade neutrality,
    roster exactness, cap termination for any round past the cap, and route
    totality over every record type."""

    def test_grader_verdict_content_never_changes_the_route(self):
        # The router may echo the verdict into context; it must never
        # branch on it.
        decisions = {}
        for verdict in ("skim", "scrutinize"):
            decision = route(
                a_slice_record("build-pass"),
                *approvals(),
                a_slice_record("grader-verdict", verdict=verdict, responding_to=[1]),
            )
            context = {k: v for k, v in decision.context.items() if k != "verdict"}
            decisions[verdict] = dataclasses.replace(decision, context=context)

        self.assertEqual(decisions["skim"].rule, "feature-complete")
        self.assertEqual(decisions["skim"], decisions["scrutinize"])

    def test_an_off_roster_approval_never_fills_a_roster_seat(self):
        decision = route(
            a_slice_record("build-pass"),
            *approvals(FULL_ROSTER[:-1]),
            approved(OFF_ROSTER_REVIEWER),
        )

        self.assertEqual(decision.rule, "reviews-needed")
        self.assertIn(FULL_ROSTER[-1], decision.next)

    def test_an_off_roster_approval_beside_a_complete_roster_still_grades(self):
        decision = route(
            a_slice_record("build-pass"), *approvals(), approved(OFF_ROSTER_REVIEWER)
        )

        self.assertEqual(decision.rule, "grade")
        self.assertEqual(decision.next, (GRADER,))

    def test_a_roster_member_s_latest_report_wins(self):
        later_dissent = route(
            a_slice_record("build-pass"), *approvals(), dissent(FULL_ROSTER[0])
        )
        later_approval = route(
            a_slice_record("build-pass"), dissent(FULL_ROSTER[0]), *approvals()
        )

        self.assertEqual(later_dissent.rule, "process-findings")
        self.assertEqual(later_approval.rule, "grade")

    def test_the_round_cap_blocks_for_any_round_past_the_cap(self):
        for rounds in range(REVIEW_ROUND_CAP + 1, REVIEW_ROUND_CAP + 4):
            with self.subTest(rounds=rounds):
                records = []
                for n in range(rounds):
                    severity = "critical" if n + 1 >= REVIEW_ROUND_CAP else "fixable"
                    records += review_pass(severity=severity)

                decision = route(*records)

                self.assertEqual(decision.kind, "blocked")
                self.assertEqual(decision.rule, "review-non-convergence")

    def test_pipeline_types_cover_every_record_type(self):
        self.assertEqual(set(PIPELINE_TYPES), set(RECORD_TYPES))

    def test_every_record_type_alone_routes_to_a_decision(self):
        for rtype in PIPELINE_TYPES:
            with self.subTest(rtype=rtype):
                decision = route(a_slice_record(rtype))

                self.assertIsInstance(decision, Decision)
                self.assertIn(decision.kind, {"dispatch", "blocked", "escalate"})
                self.assertTrue(decision.rule)


if __name__ == "__main__":
    unittest.main(verbosity=2)
