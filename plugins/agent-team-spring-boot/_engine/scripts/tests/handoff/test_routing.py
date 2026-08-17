#!/usr/bin/env python3
"""Routing-core suite: the Handoff Conditions table, gates, recovery ladders,
consultation routing, the fail-closed damage modes, and the cross-cutting
routing invariants — handoff.routing, exercised through the CLI entry point
(ADR 2026-07-17 runtime-package-layout)."""

import json
import os
import subprocess
import unittest
import unittest.mock

from handoff.records import _RECORD_TYPES, REVIEW_ROUND_CAP

from tests.support import (
    FLOOR,
    PIPELINE_TYPES,
    TS,
    RouteCase,
    entry,
    rec,
)


class TestRouteDamageModes(RouteCase):
    def test_missing_log_escalates_no_active_slice(self):
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "no-active-slice")

    def test_dirty_log_blocks_with_parse_errors(self):
        self.log.write_text(json.dumps(rec("prd-entry")) + "\ngarbage\n")
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "dirty-log")
        self.assertIn("line 2: invalid JSON (Expecting value)", decision["errors"][0])

    def test_truncated_final_line_blocks(self):
        # An agent dying mid-append leaves no trailing newline; route must
        # refuse to guess over it.
        self.log.write_text(json.dumps(rec("prd-entry")) + "\n" + '{"type": "desi')
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "dirty-log")

    def test_missing_req_id_blocks(self):
        self.write_log({"type": "prd-entry", "ts": TS, "author": "tester"})
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "missing-req-id")

    def test_empty_existing_log_escalates_no_active_slice(self):
        self.log.write_text("")
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "no-active-slice")

    def test_unreadable_log_path_blocks_with_exit_zero(self):
        # A directory at the log path is a dirty-log error, not a traceback:
        # route keeps its exit-0-with-decision contract.
        self.log.mkdir()
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "dirty-log")
        self.assertIn("cannot read", decision["errors"][0])

    def test_unknown_req_id_blocks(self):
        self.write_log(rec("prd-entry"))
        decision = self.route("--req-id", "REQ-Z-999")
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "unknown-req-id")


class TestIntakeDecisionRow(RouteCase):
    """The intake row: a recorded intake-decision (either front door)
    dispatches the product expert deterministically; a failed gate halts for
    the owner, who authored the record."""

    def intake(self, **fields):
        base = {
            "author": "human",
            "request": "add a specialty filter to the vet list",
            "decisions": ["ship it on the existing list page"],
        }
        base.update(fields)
        return rec("intake-decision", **base)

    def test_intake_decision_dispatches_product_expert(self):
        self.write_log(self.intake())
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["rule"], "intake-ready")
        self.assertEqual(decision["next"], ["product-requirements-expert"])

    def test_invalid_intake_blocks_for_the_owner(self):
        # No agent bounce target exists for a human-authored record: the halt
        # puts the fix with the owner.
        strict = {"type": "object", "required": ["type", "request"]}
        (self.schemas / "intake-decision.schema.json").write_text(json.dumps(strict))
        no_request = self.intake()
        del no_request["request"]
        self.write_log(no_request)
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "intake-record-invalid")
        self.assertTrue(decision["errors"])

    def test_prd_entry_supersedes_the_intake_row(self):
        # Once the slice is authored the intake record is history: the
        # prd-entry row governs.
        self.write_log(
            self.intake(),
            rec("prd-entry", author="product-requirements-expert"),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-approved")
        self.assertEqual(decision["next"], ["system-design-expert"])


class TestRouteHappyPath(RouteCase):
    def test_prd_routes_to_designer(self):
        self.write_log(rec("prd-entry", author="product-requirements-expert"))
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "prd-approved")

    def test_prd_gate_failure_bounces_upstream(self):
        strict = {"type": "object", "required": ["type", "title"]}
        (self.schemas / "prd-entry.schema.json").write_text(json.dumps(strict))
        self.write_log(rec("prd-entry"))
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["product-requirements-expert"])
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertTrue(decision["context"]["errors"])

    def test_unknown_design_verdict_bounces_upstream(self):
        self.write_log(rec("design-block", verdict="bogus"))
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "design-gate-failed")

    def test_invalid_build_pass_bounces_to_implementer(self):
        strict = {"type": "object", "required": ["type", "gate_checks_run"]}
        (self.schemas / "build-pass.schema.json").write_text(json.dumps(strict))
        self.write_log(rec("build-pass"))
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "build-record-invalid")

    def test_refactor_sibling_prd_escalates(self):
        # The realistic two-record shape: refactor-first design-block plus the
        # designer-authored sibling prd-entry appended last. Route must not
        # advance the sibling on its own; ordering is the coordinator's call.
        self.write_log(
            rec("prd-entry"),
            rec("design-block", verdict="refactor-first"),
            rec("prd-entry", req_id="REQ-B-001", author="system-design-expert"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "refactor-first")

    def test_refactor_resume_after_sibling_completes(self):
        records = [
            rec("prd-entry"),
            rec("design-block", verdict="refactor-first"),
            rec("build-pass", req_id="REQ-B-001"),
        ]
        records += [
            rec(
                "review-feedback",
                req_id="REQ-B-001",
                author=r,
                verdict="approved",
                findings=[],
            )
            for r in FLOOR
        ]
        records.append(
            rec(
                "grader-verdict",
                req_id="REQ-B-001",
                author="change-grader",
                verdict="clear",
            )
        )
        self.write_log(*records)
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "refactor-resume")
        self.assertEqual(decision["context"]["original_req_id"], "REQ-A-001")

    def test_refactor_resume_on_approval_when_grading_disabled(self):
        # With auto_grade = false the refactor sibling has no grader-verdict to
        # resume on; roster approval is the completion signal instead.
        layout = self.schemas.parent / "layout.toml"
        layout.write_text("[harness]\nauto_grade = false\n")
        records = [
            rec("prd-entry"),
            rec("design-block", verdict="refactor-first"),
            rec("build-pass", req_id="REQ-B-001"),
        ]
        records += [
            rec(
                "review-feedback",
                req_id="REQ-B-001",
                author=r,
                verdict="approved",
                findings=[],
            )
            for r in FLOOR
        ]
        self.write_log(*records)
        decision = self.route("--layout", str(layout))
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "refactor-resume")
        self.assertEqual(decision["context"]["original_req_id"], "REQ-A-001")
        self.assertNotIn("verdict", decision["context"])

    def test_grader_features_without_verdict_redispatches_grader(self):
        records = [rec("build-pass")]
        records += [
            rec("review-feedback", author=r, verdict="approved", findings=[])
            for r in FLOOR
        ]
        records.append(rec("grader-features", author="change-grader", features=[]))
        self.write_log(*records)
        decision = self.route()
        self.assertEqual(decision["next"], ["change-grader"])
        self.assertEqual(decision["rule"], "grade-continue")

    def test_partial_failure_carries_partial_context(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("build-failure", retry=1, partial=True),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "build-retry")
        self.assertTrue(decision["context"]["partial"])

    def test_unreadable_layout_blocks(self):
        layout = self.schemas.parent / "layout.toml"
        layout.write_text("[harness\nbroken = ")
        self.write_log(rec("build-pass"))
        code, out, err = self.run_cli(
            "route",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
            "--layout",
            str(layout),
        )
        self.assertEqual(code, 0, err)
        decision = json.loads(out)
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "layout-unreadable")

    def test_non_list_extra_reviewers_blocks(self):
        layout = self.schemas.parent / "layout.toml"
        layout.write_text('[harness]\nextra_reviewers = "perf-reviewer"\n')
        self.write_log(rec("build-pass"))
        code, out, err = self.run_cli(
            "route",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
            "--layout",
            str(layout),
        )
        self.assertEqual(code, 0, err)
        decision = json.loads(out)
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "layout-invalid")

    def test_approved_design_routes_to_implementer(self):
        self.write_log(rec("prd-entry"), rec("design-block", verdict="covered"))
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "design-approved")

    def test_conflicting_design_blocks(self):
        self.write_log(rec("design-block", verdict="conflicting", escalations=["e1"]))
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "design-conflict")
        self.assertEqual(decision["context"]["escalations"], ["e1"])
        self.assertNotIn("errors", decision)

    def test_conflicting_without_escalations_names_the_gap(self):
        # Gate 2: conflicting requires a non-empty escalations array. Still
        # blocked; the error tells the human what the record failed to carry.
        self.write_log(rec("design-block", verdict="conflicting"))
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "design-conflict")
        self.assertIn("no escalations", decision["errors"][0])

    def test_dangling_supersedes_pointer_fails_the_design_gate(self):
        self.write_log(
            rec("prd-entry"),
            rec("design-block", verdict="covered", supersedes_record_at=99),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "design-gate-failed")
        self.assertIn("supersedes_record_at", decision["context"]["errors"][0])

    def test_valid_supersedes_pointer_passes_the_design_gate(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("build-failure", retry=1),
            rec("design-block", verdict="minor", supersedes_record_at=1),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "design-approved")

    def test_refactor_first_escalates_to_coordinator(self):
        self.write_log(rec("design-block", verdict="refactor-first"))
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "refactor-first")

    def test_build_pass_dispatches_full_roster(self):
        self.write_log(rec("design-block", verdict="covered"), rec("build-pass"))
        decision = self.route()
        self.assertEqual(decision["next"], FLOOR)
        self.assertEqual(decision["rule"], "reviews-needed")

    def test_planless_build_pass_names_the_fail_closed_gap(self):
        # Fail-closed AND named: an absent plan must be distinguishable from
        # a deliberate full battery in the decision the board renders.
        self.write_log(rec("design-block", verdict="covered"), rec("build-pass"))
        decision = self.route()
        self.assertIn("no review-plan on record", decision["reason"])

    def test_build_pass_postdating_a_build_failure_gates_reviews(self):
        # The table row: the latest build-pass post-dates any build-failure
        # for the slice — the earlier failure must not re-enter recovery.
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("build-failure", retry=1),
            rec("build-pass"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], FLOOR)
        self.assertEqual(decision["rule"], "reviews-needed")

    def test_extra_reviewer_from_layout_joins_roster(self):
        layout = self.schemas.parent / "layout.toml"
        layout.write_text('[harness]\nextra_reviewers = ["perf-reviewer"]\n')
        self.write_log(rec("build-pass"))
        code, out, err = self.run_cli(
            "route",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
            "--layout",
            str(layout),
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["next"], FLOOR + ["perf-reviewer"])

    def test_all_approved_dispatches_grader(self):
        records = [rec("build-pass")]
        records += [
            rec("review-feedback", author=r, verdict="approved", findings=[])
            for r in FLOOR
        ]
        self.write_log(*records)
        decision = self.route()
        self.assertEqual(decision["next"], ["change-grader"])
        self.assertEqual(decision["rule"], "grade")

    def test_grader_verdict_completes_feature(self):
        records = [rec("build-pass")]
        records += [
            rec("review-feedback", author=r, verdict="approved", findings=[])
            for r in FLOOR
        ]
        records.append(rec("grader-verdict", author="change-grader", verdict="clear"))
        self.write_log(*records)
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "feature-complete")
        self.assertEqual(decision["context"]["verdict"], "clear")

    def _approved_records(self):
        records = [rec("build-pass")]
        records += [
            rec("review-feedback", author=r, verdict="approved", findings=[])
            for r in FLOOR
        ]
        return records

    def test_auto_grade_false_completes_without_grader(self):
        # auto_grade = false: the approved state is terminal with no grader run.
        layout = self.schemas.parent / "layout.toml"
        layout.write_text("[harness]\nauto_grade = false\n")
        self.write_log(*self._approved_records())
        decision = self.route("--layout", str(layout))
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "feature-complete")
        self.assertNotIn("verdict", decision.get("context", {}))
        self.assertIn("grading disabled", decision["reason"])

    def test_auto_grade_false_still_honors_manual_grader_verdict(self):
        # A hand-run grader appends a grader-verdict; it still routes to
        # feature-complete carrying the verdict, grading toggle notwithstanding.
        layout = self.schemas.parent / "layout.toml"
        layout.write_text("[harness]\nauto_grade = false\n")
        records = self._approved_records()
        records.append(rec("grader-verdict", author="change-grader", verdict="clear"))
        self.write_log(*records)
        decision = self.route("--layout", str(layout))
        self.assertEqual(decision["rule"], "feature-complete")
        self.assertEqual(decision["context"]["verdict"], "clear")

    def test_auto_grade_true_explicit_dispatches_grader(self):
        layout = self.schemas.parent / "layout.toml"
        layout.write_text("[harness]\nauto_grade = true\n")
        self.write_log(*self._approved_records())
        decision = self.route("--layout", str(layout))
        self.assertEqual(decision["next"], ["change-grader"])
        self.assertEqual(decision["rule"], "grade")

    def test_auto_grade_non_bool_fails_open_to_grading(self):
        # The router fails open: a malformed value keeps grading on. The doctor
        # is the layer that flags the typo.
        layout = self.schemas.parent / "layout.toml"
        layout.write_text('[harness]\nauto_grade = "false"\n')
        self.write_log(*self._approved_records())
        decision = self.route("--layout", str(layout))
        self.assertEqual(decision["next"], ["change-grader"])
        self.assertEqual(decision["rule"], "grade")

    def test_req_id_flag_selects_slice(self):
        self.write_log(
            rec("prd-entry"),
            rec("prd-entry", req_id="REQ-B-001"),
        )
        decision = self.route("--req-id", "REQ-A-001")
        self.assertEqual(decision["req_id"], "REQ-A-001")
        self.assertEqual(decision["next"], ["system-design-expert"])


class TestRouteReviewCycle(RouteCase):
    def approved(self, reviewer):
        return rec("review-feedback", author=reviewer, verdict="approved", findings=[])

    def test_changes_requested_routes_to_implementer(self):
        finding = {
            "tag": "clarify",
            "location": "src/widget:1",
            "description": "d",
            "clarify_target": "system-design-expert",
        }
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=[finding],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "process-findings")
        self.assertEqual(decision["context"]["reviewers"], ["doc-reviewer"])

    def test_blocked_verdict_routes_like_changes_requested(self):
        finding = {
            "tag": "blocked",
            "location": "src/widget:1",
            "description": "d",
            "severity": "critical",
        }
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="blocked",
                findings=[finding],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "process-findings")

    def test_escalate_finding_in_approved_record_joins_the_split(self):
        # The escalate tag crosses the approved boundary: the implementer
        # must receive it to append .scratch/escalations.md, and the round
        # halts after processing.
        escalate = {
            "tag": "escalate",
            "location": "src/auth/session:10",
            "description": "sev",
        }
        prd = {
            "tag": "blocked",
            "location": "docs/prd.md:9",
            "description": "prd",
            "severity": "critical",
        }
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:2]],
            rec(
                "review-feedback",
                author="security-reviewer",
                verdict="approved",
                findings=[escalate],
            ),
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=[prd],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "process-findings")
        self.assertIn("feature-implementer", decision["next"])
        self.assertIn("product-requirements-expert", decision["next"])
        self.assertTrue(decision["context"]["halt_after"])
        self.assertEqual(decision["context"]["escalate_findings"], 1)

    def test_clarify_finding_without_target_bounces_the_reviewer(self):
        finding = {"tag": "clarify", "location": "src/widget:1", "description": "d"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=[finding],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["doc-reviewer"])
        self.assertEqual(decision["rule"], "review-record-invalid")
        self.assertIn("clarify_target", decision["context"]["errors"][0])

    def test_routable_finding_without_severity_bounces_the_reviewer(self):
        # severity feeds the next review-plan's prior-critical trigger; a
        # record that omits it on an autofix/blocked finding must not gate.
        finding = {"tag": "blocked", "location": "src/widget:1", "description": "d"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="blocked",
                findings=[finding],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["doc-reviewer"])
        self.assertEqual(decision["rule"], "review-record-invalid")
        self.assertIn("no severity", decision["context"]["errors"][0])

    def test_an_autofix_finding_on_an_approved_verdict_bounces(self):
        # An approved verdict with a fix-routable finding is a contradiction:
        # routing only processes findings from non-approved verdicts, so the
        # fix would be dropped silently and re-raised a round later.
        finding = {
            "tag": "autofix",
            "location": "src/widget:1",
            "description": "d",
            "fix": "rename",
            "severity": "fixable",
        }
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[finding],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["doc-reviewer"])
        self.assertEqual(decision["rule"], "review-record-invalid")
        self.assertIn("approved verdict", decision["context"]["errors"][0])

    def test_an_escalate_finding_on_an_approved_verdict_stays_valid(self):
        # Escalate deliberately crosses the approved boundary; the tightened
        # gate must not catch it.
        finding = {"tag": "escalate", "location": "src/widget:1", "description": "d"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[finding],
            ),
        )
        decision = self.route()
        self.assertNotEqual(decision["rule"], "review-record-invalid")

    def test_findings_split_by_artifact_owner(self):
        findings = [
            {
                "tag": "clarify",
                "location": "src/widget:1",
                "description": "code",
                "clarify_target": "system-design-expert",
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
                "clarify_target": "system-design-expert",
            },
            {
                "tag": "autofix",
                "location": "docs/system-design.md:7",
                "description": "typo",
                "fix": "x",
                "severity": "fixable",
            },
        ]
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=findings,
            ),
        )
        decision = self.route()
        self.assertEqual(
            decision["next"],
            [
                "feature-implementer",
                "product-requirements-expert",
                "system-design-expert",
            ],
        )
        self.assertEqual(decision["context"]["root_autofix"], 1)

    def test_autofix_only_round_escalates(self):
        finding = {
            "tag": "autofix",
            "location": "docs/system-design.md:7",
            "description": "typo",
            "fix": "x",
            "severity": "fixable",
        }
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=[finding],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "autofix-only-round")

    def test_prd_autofix_finding_is_root_applied(self):
        # The bug this pins: an autofix-tagged PRD finding must not dispatch
        # product-requirements-expert (whose prd-entry would re-flow the slice
        # from design triage). Root applies it; only the code finding routes.
        findings = [
            {
                "tag": "blocked",
                "location": "src/widget:1",
                "description": "code",
                "severity": "critical",
            },
            {
                "tag": "autofix",
                "location": "docs/prd.md:12",
                "description": "sentence split",
                "fix": "x",
                "severity": "fixable",
            },
        ]
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=findings,
            ),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["context"]["root_autofix"], 1)

    def test_prd_autofix_only_round_escalates(self):
        finding = {
            "tag": "autofix",
            "location": "docs/prd.md:12",
            "description": "sentence split",
            "fix": "x",
            "severity": "fixable",
        }
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=[finding],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "autofix-only-round")

    def test_escalate_finding_on_changes_requested_flags_halt(self):
        finding = {"tag": "escalate", "location": "src/widget:1", "description": "d"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=[finding],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "process-findings")
        self.assertEqual(decision["context"]["escalate_findings"], 1)
        self.assertTrue(decision["context"]["halt_after"])

    def test_escalate_round_halts_before_rereview(self):
        finding = {"tag": "escalate", "location": "src/widget:1", "description": "d"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=[finding],
            ),
            rec("build-pass"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "escalate-finding-halt")

    def test_stale_feedback_after_silent_start_retries(self):
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR],
            rec("dispatch-start", author="doc-reviewer"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["doc-reviewer"])
        self.assertEqual(decision["rule"], "reviewer-stall-retry")
        self.assertEqual(decision["context"]["prompt_note"], "Review round 1.")

    def test_stale_feedback_after_two_silent_starts_stalls(self):
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR],
            rec("dispatch-start", author="doc-reviewer"),
            rec("dispatch-start", author="doc-reviewer"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "reviewer-stalled")

    def test_non_approved_empty_findings_redispatches_reviewer(self):
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=[],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["doc-reviewer"])
        self.assertEqual(decision["rule"], "reviewer-empty-findings")

    def test_missing_feedback_after_one_start_retries_once(self):
        self.write_log(
            rec("build-pass"),
            *[rec("dispatch-start", author=r) for r in FLOOR],
            *[self.approved(r) for r in FLOOR[:3]],
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["doc-reviewer"])
        self.assertEqual(decision["rule"], "reviewer-stall-retry")

    def test_two_silent_starts_blocks_as_stalled(self):
        self.write_log(
            rec("build-pass"),
            *[rec("dispatch-start", author=r) for r in FLOOR],
            *[self.approved(r) for r in FLOOR[:3]],
            rec("dispatch-start", author="doc-reviewer"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "reviewer-stalled")
        self.assertEqual(decision["context"]["stalled"], ["doc-reviewer"])

    def test_escalate_finding_on_approved_blocks(self):
        finding = {"tag": "escalate", "location": "src/widget:1", "description": "d"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[finding],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "escalate-on-approved")

    def test_second_round_resets_on_new_build_pass(self):
        finding = {"tag": "clarify", "location": "src/widget:1", "description": "d"}
        self.write_log(
            rec("build-pass"),
            *[self.approved(r) for r in FLOOR[:3]],
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=[finding],
            ),
            rec("build-pass"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], FLOOR)
        self.assertEqual(decision["rule"], "reviews-needed")


class TestReviewRoundConvergence(RouteCase):
    """The review ladder (route-spec § Review Non-Convergence): the round
    counter, the critical-only gate from round REVIEW_ROUND_CAP, and the
    blocked stop past REVIEW_ROUND_CAP fix rounds."""

    def approved(self, reviewer):
        return rec("review-feedback", author=reviewer, verdict="approved", findings=[])

    def dissent(self, reviewer, severity="fixable"):
        finding = {
            "tag": "autofix",
            "location": "src/widget:1",
            "description": "d",
            "fix": "f",
            "severity": severity,
        }
        return rec(
            "review-feedback",
            author=reviewer,
            verdict="changes_requested",
            findings=[finding],
        )

    def window(self, dissenter="doc-reviewer", severity="fixable"):
        """One full review pass drawing dissent: build-pass, three approvals,
        one dissenting record."""
        others = [r for r in FLOOR if r != dissenter]
        return [
            rec("build-pass"),
            *[self.approved(r) for r in others],
            self.dissent(dissenter, severity=severity),
        ]

    def truncation_window(self, dissenter="doc-reviewer"):
        """One full review pass whose only dissent is a truncation checkpoint."""
        others = [r for r in FLOOR if r != dissenter]
        return [
            rec("build-pass"),
            *[self.approved(r) for r in others],
            rec(
                "review-feedback",
                author=dissenter,
                verdict="blocked",
                findings=[
                    {
                        "tag": "truncation",
                        "location": "src/",
                        "description": "planned checkpoint reached",
                    }
                ],
            ),
        ]

    def test_second_round_non_critical_dissent_still_processes(self):
        self.write_log(*self.window(), *self.window())
        decision = self.route()
        self.assertEqual(decision["rule"], "process-findings")
        self.assertEqual(decision["context"]["round"], 2)

    def test_round_three_non_critical_dissent_bounces_the_reviewer(self):
        # The critical-only gate: from round 3, dissent on polish alone is
        # invalid — residuals belong in recommendations on an approved verdict.
        self.write_log(*self.window(), *self.window(), *self.window())
        decision = self.route()
        self.assertEqual(decision["rule"], "review-record-invalid")
        self.assertEqual(decision["next"], ["doc-reviewer"])
        self.assertIn("critical-only round (round 3)", decision["context"]["errors"][0])

    def test_round_three_critical_dissent_processes_findings(self):
        self.write_log(
            *self.window(), *self.window(), *self.window(severity="critical")
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "process-findings")
        self.assertEqual(decision["context"]["round"], 3)

    def test_round_four_dissent_blocks_as_non_convergence(self):
        # Three fix rounds are the cap: substantive dissent on the fourth
        # round halts for the human instead of buying another cycle.
        self.write_log(
            *self.window(),
            *self.window(),
            *self.window(severity="critical"),
            *self.window(severity="critical"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "review-non-convergence")
        self.assertEqual(decision["context"]["round"], 4)
        self.assertEqual(decision["context"]["dissenters"], ["doc-reviewer"])

    def test_truncation_only_windows_do_not_advance_the_round(self):
        # A budget checkpoint is progress, not churn: three truncation-only
        # passes leave the counter at round 1, so polish dissent still gates.
        self.write_log(
            *self.truncation_window(),
            *self.truncation_window(),
            *self.truncation_window(),
            *self.window(),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "process-findings")
        self.assertEqual(decision["context"]["round"], 1)

    def test_superseding_design_block_resets_the_round(self):
        # A re-triage starts a fresh cycle: the counter restarts at 1, so
        # non-critical dissent gates again.
        design = rec("design-block", verdict="new", author="system-design-expert")
        superseding = rec(
            "design-block",
            verdict="new",
            author="system-design-expert",
            supersedes_record_at=1,
        )
        self.write_log(
            design,
            *self.window(),
            *self.window(),
            *self.window(severity="critical"),
            superseding,
            *self.window(),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "process-findings")
        self.assertEqual(decision["context"]["round"], 1)

    def test_reviews_needed_names_round_and_critical_only_bar(self):
        # The dispatch context tells root which contract the pass runs under;
        # prompt_note is the paste-ready sentence root appends verbatim.
        self.write_log(*self.window(), *self.window(), rec("build-pass"))
        decision = self.route()
        self.assertEqual(decision["rule"], "reviews-needed")
        self.assertEqual(decision["context"]["round"], 3)
        self.assertEqual(decision["context"]["finding_bar"], "critical-only")
        self.assertTrue(
            decision["context"]["prompt_note"].startswith(
                "Review round 3: critical-only."
            )
        )

    def test_first_pass_reviews_needed_carries_round_one(self):
        self.write_log(rec("build-pass"))
        decision = self.route()
        self.assertEqual(decision["rule"], "reviews-needed")
        self.assertEqual(decision["context"]["round"], 1)
        self.assertNotIn("finding_bar", decision["context"])
        self.assertEqual(decision["context"]["prompt_note"], "Review round 1.")

    def test_clarify_only_dissent_stays_legal_on_capped_rounds(self):
        # A clarify finding is a question for its owner, not polish: the
        # critical-only gate must not silence the channel.
        clarify = {
            "tag": "clarify",
            "location": "src/widget:1",
            "description": "q",
            "clarify_target": "system-design-expert",
        }
        others = [self.approved(r) for r in FLOOR[:3]]
        self.write_log(
            *self.window(),
            *self.window(),
            rec("build-pass"),
            *others,
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=[clarify],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "process-findings")
        self.assertEqual(decision["context"]["round"], 3)

    def test_escalate_only_dissent_stays_legal_on_capped_rounds(self):
        escalate = {"tag": "escalate", "location": "src/widget:1", "description": "d"}
        others = [self.approved(r) for r in FLOOR[:3]]
        self.write_log(
            *self.window(),
            *self.window(),
            rec("build-pass"),
            *others,
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=[escalate],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "process-findings")
        self.assertTrue(decision["context"]["halt_after"])

    def test_second_below_bar_record_blocks_as_bounce_repeat(self):
        # The judgment bounce has a ceiling: a reviewer re-dissenting below
        # the bar after its bounce is a severity disagreement for the human.
        others = [self.approved(r) for r in FLOOR[:3]]
        self.write_log(
            *self.window(),
            *self.window(),
            rec("build-pass"),
            *others,
            self.dissent("doc-reviewer"),
            self.dissent("doc-reviewer"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "review-non-convergence")
        self.assertEqual(decision["context"]["cause"], "bounce-repeat")

    def test_third_dissent_in_one_pass_blocks_as_pass_churn(self):
        # Within-pass loops never cross a build-pass, so the round counter
        # cannot bound them; the third dissent record in one pass halts.
        others = [self.approved(r) for r in FLOOR[:3]]
        self.write_log(
            rec("build-pass"),
            *others,
            self.dissent("doc-reviewer", severity="critical"),
            self.dissent("doc-reviewer", severity="critical"),
            self.dissent("doc-reviewer", severity="critical"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "review-non-convergence")
        self.assertEqual(decision["context"]["cause"], "pass-churn")
        self.assertEqual(decision["context"]["dissenters"], ["doc-reviewer"])

    def test_three_truncation_only_passes_block_as_truncation_run(self):
        self.write_log(
            *self.truncation_window(),
            *self.truncation_window(),
            *self.truncation_window(),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "review-non-convergence")
        self.assertEqual(decision["context"]["cause"], "truncation-run")

    def test_off_roster_records_never_tick_the_counter(self):
        # The schema shape-checks author names, never roster membership: a
        # forged or since-removed reviewer name must not advance the ladder
        # the rest of the router would never read.
        forged = [
            rec("build-pass"),
            rec(
                "review-feedback",
                author="polish-reviewer",
                verdict="changes_requested",
                findings=[
                    {
                        "tag": "autofix",
                        "location": "src/widget:1",
                        "description": "d",
                        "fix": "f",
                        "severity": "fixable",
                    }
                ],
            ),
        ]
        self.write_log(*forged, *forged, *self.window())
        decision = self.route()
        self.assertEqual(decision["rule"], "process-findings")
        self.assertEqual(decision["context"]["round"], 1)

    def test_empty_findings_dissent_keeps_its_own_diagnosis_on_capped_rounds(self):
        others = [self.approved(r) for r in FLOOR[:3]]
        self.write_log(
            *self.window(),
            *self.window(),
            rec("build-pass"),
            *others,
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="changes_requested",
                findings=[],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "reviewer-empty-findings")
        self.assertEqual(decision["context"]["round"], 3)

    def test_parallel_dissent_in_one_pass_counts_one_round(self):
        # A round is a pass, not a reviewer count: the whole floor dissenting
        # in parallel advances the counter by one, so a noisy full battery
        # never burns the cap in a single pass.
        def all_dissent():
            return [rec("build-pass"), *[self.dissent(r) for r in FLOOR]]

        self.write_log(
            *all_dissent(), *all_dissent(), *self.window(severity="critical")
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "process-findings")
        self.assertEqual(decision["context"]["round"], 3)

    def test_extra_reviewer_rides_the_same_ladder(self):
        # A declared extra advances the round like a floor reviewer and meets
        # the same critical-only gate on round 3.
        layout = self.schemas.parent / "layout.toml"
        layout.write_text('[harness]\nextra_reviewers = ["perf-reviewer"]\n')

        def extra_window(severity="fixable"):
            return [
                rec("build-pass"),
                *[self.approved(r) for r in FLOOR],
                self.dissent("perf-reviewer", severity=severity),
            ]

        self.write_log(*extra_window(), *extra_window(), *extra_window())
        code, out, err = self.run_cli(
            "route",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
            "--layout",
            str(layout),
        )
        self.assertEqual(code, 0, err)
        decision = json.loads(out)
        self.assertEqual(decision["rule"], "review-record-invalid")
        self.assertEqual(decision["next"], ["perf-reviewer"])
        self.assertIn("critical-only round (round 3)", decision["context"]["errors"][0])

    def test_extra_reviewer_dissent_trips_the_cap(self):
        # The non-convergence stop reads the whole pass roster: a declared
        # extra's persistent critical dissent halts exactly like the floor's.
        layout = self.schemas.parent / "layout.toml"
        layout.write_text('[harness]\nextra_reviewers = ["perf-reviewer"]\n')

        def extra_window(severity):
            return [
                rec("build-pass"),
                *[self.approved(r) for r in FLOOR],
                self.dissent("perf-reviewer", severity=severity),
            ]

        self.write_log(
            *extra_window("fixable"),
            *extra_window("fixable"),
            *extra_window("critical"),
            *extra_window("critical"),
        )
        code, out, err = self.run_cli(
            "route",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
            "--layout",
            str(layout),
        )
        self.assertEqual(code, 0, err)
        decision = json.loads(out)
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "review-non-convergence")
        self.assertEqual(decision["context"]["dissenters"], ["perf-reviewer"])

    def test_narrowed_fix_pass_still_gates_critical_only(self):
        # A risk-proportional fix pass dispatches only the dissenter; the
        # critical-only gate applies to that narrowed roster all the same.
        plan = rec(
            "review-plan",
            author="review-plan-engine",
            risk="low",
            roster=["doc-reviewer"],
            scope="fix-delta",
        )
        self.write_log(
            *self.window(),
            *self.window(),
            rec("build-pass"),
            plan,
            self.dissent("doc-reviewer"),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "review-record-invalid")
        self.assertEqual(decision["next"], ["doc-reviewer"])
        self.assertIn("critical-only round (round 3)", decision["context"]["errors"][0])


class TestRouteReviewPlan(RouteCase):
    """Risk-proportional review: the active review-plan names the pass's roster;
    a gray plan dispatches the planner; absent/invalid plans fail closed to the
    full battery."""

    def _plan(self, **fields):
        base = {
            "author": "review-plan-engine",
            "scope": "full-diff",
            "basis": {"tree_sha": "t1", "pass": "first"},
            "rationale": "x",
        }
        base.update(fields)
        return rec("review-plan", **base)

    def test_low_plan_dispatches_only_its_roster(self):
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["doc-reviewer"]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "reviews-needed")
        self.assertEqual(decision["next"], ["doc-reviewer"])

    def test_no_plan_fails_closed_to_full_battery(self):
        self.write_log(rec("build-pass", author="feature-implementer"))
        decision = self.route()
        self.assertEqual(decision["rule"], "reviews-needed")
        self.assertEqual(decision["next"], FLOOR)

    def test_invalid_plan_fail_closed_names_the_gap(self):
        # A plan naming an unknown reviewer fails closed AND says so — the
        # reason must not read as a deliberate full battery.
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["nobody-reviewer"]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "reviews-needed")
        self.assertEqual(decision["next"], FLOOR)
        self.assertIn("empty or unknown roster", decision["reason"])

    def test_gray_plan_dispatches_planner(self):
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="gray"),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "plan-gray")
        self.assertEqual(decision["next"], ["review-planner"])

    def test_gray_from_planner_bounces(self):
        # Only the engine may defer; a planner record with risk gray is invalid.
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="gray", author="review-planner"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["rule"], "plan-gray-invalid")
        self.assertEqual(decision["next"], ["review-planner"])

    def test_planner_stall_retry_then_block(self):
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="gray"),
            rec("dispatch-start", author="review-planner"),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "planner-stall-retry")
        self.assertEqual(decision["next"], ["review-planner"])
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="gray"),
            rec("dispatch-start", author="review-planner"),
            rec("dispatch-start", author="review-planner"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "planner-stalled")

    def test_planner_resolution_dispatches_its_roster(self):
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="gray"),
            rec("dispatch-start", author="review-planner"),
            self._plan(
                risk="low",
                author="review-planner",
                roster=["code-quality-reviewer", "test-reviewer", "security-reviewer"],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "reviews-needed")
        self.assertEqual(
            decision["next"],
            ["code-quality-reviewer", "test-reviewer", "security-reviewer"],
        )

    def test_plan_roster_completion_grades(self):
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["doc-reviewer"]),
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "grade")
        self.assertEqual(decision["next"], ["change-grader"])

    def test_invalid_plan_roster_fails_closed(self):
        # A plan naming a non-roster reviewer cannot gate; full battery instead.
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["ghost-reviewer"]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "reviews-needed")
        self.assertEqual(decision["next"], FLOOR)

    def test_plan_dropping_a_prior_dissenter_reruns_it(self):
        # Completion invariant: a fix plan that drops a reviewer still holding a
        # non-approved verdict must not grade — route re-dispatches the dissenter.
        finding = {
            "tag": "blocked",
            "location": "x:1",
            "description": "y",
            "severity": "critical",
        }
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="high", roster=FLOOR),
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "review-feedback",
                author="code-quality-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "review-feedback",
                author="test-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "review-feedback",
                author="security-reviewer",
                verdict="changes_requested",
                findings=[finding],
            ),
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["doc-reviewer"]),  # drops the dissenter
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "outstanding-dissent")
        self.assertEqual(decision["next"], ["security-reviewer"])
        # Round only, never the bar: this path's records skip Gate 4, so the
        # note must not instruct the dissenter to drop unprocessed findings.
        self.assertEqual(
            decision["context"]["prompt_note"],
            f"Review round {decision['context']['round']}.",
        )

    def test_initial_design_block_keeps_dissent_outstanding(self):
        # A design-block landing mid-slice without supersedes_record_at (a
        # fix-round design record) is not a cycle reset: a prior dissenter the
        # later plan dropped stays outstanding (ADR 2026-08-07).
        finding = {
            "tag": "blocked",
            "location": "x:1",
            "description": "y",
            "severity": "critical",
        }
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="high", roster=FLOOR),
            rec(
                "review-feedback",
                author="security-reviewer",
                verdict="changes_requested",
                findings=[finding],
            ),
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "review-feedback",
                author="code-quality-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "review-feedback",
                author="test-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec("design-block", author="system-design-expert", verdict="minor"),
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["doc-reviewer"]),
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "outstanding-dissent")
        self.assertEqual(decision["next"], ["security-reviewer"])

    def test_superseding_design_block_voids_prior_dissent(self):
        # A re-triage (supersedes_record_at set) starts a new cycle: prior
        # dissent is re-covered by the engine's design-revision full battery,
        # not by the completion invariant.
        finding = {
            "tag": "blocked",
            "location": "x:1",
            "description": "y",
            "severity": "critical",
        }
        self.write_log(
            rec("design-block", author="system-design-expert", verdict="minor"),
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="high", roster=FLOOR),
            rec(
                "review-feedback",
                author="security-reviewer",
                verdict="changes_requested",
                findings=[finding],
            ),
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "review-feedback",
                author="code-quality-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "review-feedback",
                author="test-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "design-block",
                author="system-design-expert",
                verdict="minor",
                supersedes_record_at=1,
            ),
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["doc-reviewer"]),
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "grade")
        self.assertEqual(decision["next"], ["change-grader"])

    def test_forged_supersedes_does_not_void_dissent(self):
        # The boundary re-checks the pointer in Gate-2 shape: a design-block
        # whose supersedes_record_at names a non-design-block line must not
        # move the cycle start past outstanding dissent.
        finding = {
            "tag": "blocked",
            "location": "x:1",
            "description": "y",
            "severity": "critical",
        }
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="high", roster=FLOOR),
            rec(
                "review-feedback",
                author="security-reviewer",
                verdict="changes_requested",
                findings=[finding],
            ),
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "review-feedback",
                author="code-quality-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "review-feedback",
                author="test-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "design-block",
                author="system-design-expert",
                verdict="minor",
                supersedes_record_at=1,
            ),
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["doc-reviewer"]),
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[],
            ),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "outstanding-dissent")
        self.assertEqual(decision["next"], ["security-reviewer"])

    def test_outstanding_dissenter_stalls_after_two_redispatches(self):
        # The outstanding-dissent re-dispatch has its own stall ceiling: a
        # dropped dissenter re-dispatched twice with no fresh feedback blocks,
        # rather than looping the router forever.
        finding = {
            "tag": "blocked",
            "location": "x:1",
            "description": "y",
            "severity": "critical",
        }
        self.write_log(
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="high", roster=FLOOR),
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "review-feedback",
                author="code-quality-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "review-feedback",
                author="test-reviewer",
                verdict="approved",
                findings=[],
            ),
            rec(
                "review-feedback",
                author="security-reviewer",
                verdict="changes_requested",
                findings=[finding],
            ),
            rec("build-pass", author="feature-implementer"),
            self._plan(risk="low", roster=["doc-reviewer"]),  # drops the dissenter
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="approved",
                findings=[],
            ),
            # Two re-dispatches of the outstanding dissenter, no fresh feedback.
            rec("dispatch-start", author="security-reviewer"),
            rec("dispatch-start", author="security-reviewer"),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "reviewer-stalled")
        self.assertEqual(decision["context"]["stalled"], ["security-reviewer"])


class TestRouteRecovery(RouteCase):
    def test_retry_below_three_redispatches_implementer(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("build-failure", author="feature-implementer", retry=1),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "build-retry")
        self.assertEqual(decision["context"]["retry"], 1)

    def test_three_failures_retriage_designer(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            *[rec("build-failure", retry=i) for i in (1, 2, 3)],
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "build-non-convergence")

    def test_superseding_design_block_resets_retry_counter(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            *[rec("build-failure", retry=i) for i in (1, 2, 3)],
            rec("design-block", verdict="minor", supersedes_record_at=1),
            rec("build-failure", retry=1),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["context"]["retry"], 1)

    def test_abort_reasons_route_deterministically(self):
        cases = (
            ("wrong-shape-slice", "dispatch", ["product-requirements-expert"]),
            ("design-mismatch", "dispatch", ["system-design-expert"]),
            ("prd-mismatch", "dispatch", ["product-requirements-expert"]),
            ("prerequisite-missing", "blocked", None),
        )
        for reason, expected_decision, expected_next in cases:
            with self.subTest(abort_reason=reason):
                self.write_log(
                    rec("design-block", verdict="covered"),
                    rec("build-failure", retry=1, abort_reason=reason),
                )
                decision = self.route()
                self.assertEqual(decision["decision"], expected_decision)
                if expected_next:
                    self.assertEqual(decision["next"], expected_next)

    def test_truncation_continues_same_slice(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("dispatch-start", author="feature-implementer"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "truncation-continue")
        self.assertEqual(decision["context"]["continuation"], 1)

    def test_truncation_survives_a_trailing_root_record(self):
        # The table trigger is "no subsequent SUBSTANTIVE record", not
        # "dispatch-start is the last record": a root design-doc-autofix note
        # appended after the truncated dispatch must not mask it.
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("dispatch-start", author="feature-implementer"),
            rec("design-doc-autofix", author="root", file="docs/system-design.md"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "truncation-continue")
        self.assertEqual(decision["context"]["continuation"], 1)

    def test_trailing_prd_autofix_does_not_mask_truncation(self):
        # The PRD twin of the test above: a root prd-autofix note appended
        # after the truncated dispatch must not mask it either.
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("dispatch-start", author="feature-implementer"),
            rec("prd-autofix", author="root", file="docs/prd.md"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "truncation-continue")
        self.assertEqual(decision["context"]["continuation"], 1)

    def test_grader_verdict_completes_its_own_dispatch_start(self):
        # A grader-verdict after the grader's dispatch-start is a completed
        # dispatch — a trailing root record must not turn it into a
        # truncation-undefined escalate.
        records = [rec("build-pass")]
        records += [
            rec("review-feedback", author=r, verdict="approved", findings=[])
            for r in FLOOR
        ]
        records += [
            rec("dispatch-start", author="change-grader"),
            rec("grader-verdict", author="change-grader", verdict="clear"),
            rec("design-doc-autofix", author="root", file="docs/system-design.md"),
        ]
        self.write_log(*records)
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "feature-complete")

    def test_three_consecutive_truncations_retriage(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            *[rec("dispatch-start", author="feature-implementer") for _ in range(3)],
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "truncation-non-convergence")

    def test_implementer_record_resets_truncation_run(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec("dispatch-start", author="feature-implementer"),
            rec("dispatch-start", author="feature-implementer"),
            rec(
                "consultation-request",
                author="feature-implementer",
                target="system-design-expert",
            ),
            rec(
                "consultation-response", author="system-design-expert", in_response_to=4
            ),
            rec("dispatch-start", author="feature-implementer"),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "truncation-continue")
        self.assertEqual(decision["context"]["continuation"], 1)

    def test_designer_truncation_escalates(self):
        self.write_log(
            rec("prd-entry"),
            rec("dispatch-start", author="system-design-expert"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "escalate")
        self.assertEqual(decision["rule"], "truncation-undefined")


class TestRouteConsultation(RouteCase):
    def test_request_dispatches_target(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec(
                "consultation-request",
                author="feature-implementer",
                target="system-design-expert",
            ),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-dispatch")
        self.assertEqual(decision["context"]["requester"], "feature-implementer")

    def test_response_returns_to_requester(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec(
                "consultation-request",
                author="feature-implementer",
                target="system-design-expert",
            ),
            rec(
                "consultation-response", author="system-design-expert", in_response_to=2
            ),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["feature-implementer"])
        self.assertEqual(decision["rule"], "consultation-return")
        self.assertTrue(decision["context"]["resume"])

    def test_human_request_blocks_for_conversation(self):
        # A fresh-dispatch pushback: PRE asked the human before any
        # substantive record exists. Route halts for the conversation.
        self.write_log(
            rec("dispatch-start", author="product-requirements-expert"),
            rec(
                "consultation-request",
                author="product-requirements-expert",
                target="human",
                question="Is REQ-XX-001's scope one behavior?",
            ),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "human-consultation")
        self.assertEqual(
            decision["context"]["requester"], "product-requirements-expert"
        )
        self.assertEqual(
            decision["context"]["question"], "Is REQ-XX-001's scope one behavior?"
        )

    def test_human_request_gate_failure_bounces_author(self):
        # The gate runs before the human branch: a malformed human request
        # bounces to its author, never blocks with a null question.
        strict = {"type": "object", "required": ["type", "question"]}
        (self.schemas / "consultation-request.schema.json").write_text(
            json.dumps(strict)
        )
        self.write_log(
            rec("prd-entry"),
            rec(
                "consultation-request",
                author="product-requirements-expert",
                target="human",
            ),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["product-requirements-expert"])
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_human_target_variant_bounces_author(self):
        # "Human"/" human" must not silently become an agent dispatch.
        self.write_log(
            rec("prd-entry"),
            rec("consultation-request", author="system-design-expert", target="Human"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_human_authored_request_fails_closed(self):
        self.write_log(
            rec("prd-entry"),
            rec("consultation-request", author="human", target="human"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_human_authored_variant_request_fails_closed(self):
        # The author guard precedes the exact-match bounce: a variant target
        # authored by "human" must block, never bounce to a "human" agent.
        self.write_log(
            rec("prd-entry"),
            rec("consultation-request", author="human", target=" human "),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_human_authored_request_response_fails_closed(self):
        self.write_log(
            rec("prd-entry"),
            rec("consultation-request", author="human", target="human"),
            rec("consultation-response", author="human", in_response_to=2),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_pending_human_request_is_sticky_over_later_records(self):
        # The elicitation pause resolves only through the human's reply: a
        # later substantive record never supersedes it. Recovery is appending
        # the transcribed consultation-response, never re-dispatching past it.
        self.write_log(
            rec("dispatch-start", author="product-requirements-expert"),
            rec(
                "consultation-request",
                author="product-requirements-expert",
                target="human",
            ),
            rec("prd-entry"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "human-consultation")
        self.assertEqual(
            decision["context"]["requester"], "product-requirements-expert"
        )

    def test_pending_human_request_is_sticky_over_a_reseeded_intake(self):
        # The laundering path: with the pushback pending, a re-seeded
        # intake-decision restating the request must not flip route to
        # intake-ready and orphan the question.
        self.write_log(
            rec("intake-decision", author="human", request="Add cancelling."),
            rec("dispatch-start", author="product-requirements-expert"),
            rec(
                "consultation-request",
                author="product-requirements-expert",
                target="human",
                question="Narrow NG-5?",
            ),
            rec("intake-decision", author="human", request="Add cancelling."),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "human-consultation")
        self.assertIn("never supersedes", decision["reason"])

    def test_pending_human_request_blocks_a_sibling_req_id(self):
        # Sticky across req_ids: a fresh REQ id must not route around the
        # unanswered human question.
        self.write_log(
            rec(
                "consultation-request",
                author="product-requirements-expert",
                target="human",
            ),
            rec("intake-decision", author="human", req_id="REQ-B-001"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "human-consultation")
        self.assertEqual(decision["req_id"], "REQ-A-001")

    def test_superseded_human_request_releases_the_pause(self):
        # Latest-per-req_id: a newer specialist-targeted request replaces the
        # human-targeted one, so the pause lifts and the consultation routes.
        self.write_log(
            rec(
                "consultation-request",
                author="product-requirements-expert",
                target="human",
            ),
            rec(
                "consultation-request",
                author="feature-implementer",
                target="system-design-expert",
            ),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])

    def test_answered_human_request_does_not_hold_the_pause(self):
        # The reply releases the pause for every later record.
        self.write_log(
            rec("prd-entry"),
            rec("dispatch-start", author="system-design-expert"),
            rec("consultation-request", author="system-design-expert", target="human"),
            rec("consultation-response", author="human", in_response_to=3),
            rec("dispatch-start", author="system-design-expert"),
            rec("design-block", author="system-design-expert", verdict="covered"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["feature-implementer"])

    def test_human_request_shields_truncation_detection(self):
        # The elicitation pause: a dispatch-start followed only by a
        # consultation-request targeting the human is a designed halt,
        # never truncation-undefined.
        self.write_log(
            rec("prd-entry"),
            rec("dispatch-start", author="system-design-expert"),
            rec("consultation-request", author="system-design-expert", target="human"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "human-consultation")

    def test_human_response_returns_to_requester(self):
        self.write_log(
            rec("prd-entry"),
            rec("dispatch-start", author="system-design-expert"),
            rec("consultation-request", author="system-design-expert", target="human"),
            rec("consultation-response", author="human", in_response_to=3),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-return")

    def test_response_from_wrong_author_bounces_the_responder(self):
        # A failed gate is a dispatch of the upstream agent (SKILL Routing
        # Rules): the request names the legitimate responder, so re-dispatch
        # it instead of halting.
        self.write_log(
            rec(
                "consultation-request",
                author="feature-implementer",
                target="system-design-expert",
            ),
            rec("consultation-response", author="doc-reviewer", in_response_to=1),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-invalid")
        self.assertTrue(decision["context"]["errors"])

    def test_response_with_dangling_pointer_blocks(self):
        self.write_log(
            rec("design-block", verdict="covered"),
            rec(
                "consultation-response", author="system-design-expert", in_response_to=9
            ),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_pending_request_survives_trailing_root_record(self):
        # Root's design-doc-autofix append must not orphan a live consultation.
        self.write_log(
            rec("design-block", verdict="covered"),
            rec(
                "consultation-request",
                author="feature-implementer",
                target="system-design-expert",
            ),
            rec("design-doc-autofix", author="root", file="docs/system-design.md"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-dispatch")

    def test_prd_autofix_does_not_orphan_consultation(self):
        # Root's prd-autofix append must not orphan a live consultation.
        self.write_log(
            rec("design-block", verdict="covered"),
            rec(
                "consultation-request",
                author="feature-implementer",
                target="product-requirements-expert",
            ),
            rec("prd-autofix", author="root", file="docs/prd.md"),
        )
        decision = self.route()
        self.assertEqual(decision["next"], ["product-requirements-expert"])
        self.assertEqual(decision["rule"], "consultation-dispatch")

    def test_stale_response_validation_applies_off_last_position(self):
        # A wrong-author response trailed by a root record must still fail its
        # gate — the latest-substantive path validates like the last-record
        # path — and bounce the legitimate responder.
        self.write_log(
            rec(
                "consultation-request",
                author="feature-implementer",
                target="system-design-expert",
            ),
            rec("consultation-response", author="doc-reviewer", in_response_to=1),
            rec("design-doc-autofix", author="root", file="docs/system-design.md"),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-invalid")

    def test_response_failing_its_schema_gate_bounces_the_responder(self):
        strict = {"type": "object", "required": ["type", "answer"]}
        (self.schemas / "consultation-response.schema.json").write_text(
            json.dumps(strict)
        )
        self.write_log(
            rec(
                "consultation-request",
                author="feature-implementer",
                target="system-design-expert",
            ),
            rec(
                "consultation-response", author="system-design-expert", in_response_to=1
            ),
        )
        decision = self.route()
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])
        self.assertEqual(decision["rule"], "consultation-invalid")


class TestValidateDispatchDiscipline(RouteCase):
    def validate(self):
        return self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )

    def test_substantive_without_dispatch_start_warns(self):
        self.write_log(rec("build-pass", author="feature-implementer"))
        code, out, err = self.validate()
        self.assertEqual(code, 0, err)
        self.assertIn("no prior dispatch-start", err)

    def test_dispatch_start_silences_the_warning(self):
        self.write_log(
            rec("dispatch-start", author="feature-implementer", responding_to=[0]),
            rec("build-pass", author="feature-implementer"),
        )
        code, out, err = self.validate()
        self.assertEqual(code, 0, err)
        self.assertNotIn("no prior dispatch-start", err)

    def test_engine_and_human_authors_are_exempt(self):
        self.write_log(
            rec("review-plan", author="review-plan-engine"),
            rec("consultation-response", author="human"),
        )
        code, out, err = self.validate()
        self.assertEqual(code, 0, err)
        self.assertNotIn("warning", err)

    def test_warning_sanitizes_agent_authored_fields(self):
        # author is agent-authored; an embedded ESC/BEL must not reach the
        # terminal raw (same discipline as the board's _sanitize).
        hostile = "\x1b]0;PWNED\x07\x1b[31mevil\x1b[0m"
        self.write_log(rec("build-pass", author=hostile))
        code, out, err = self.validate()
        self.assertEqual(code, 0, err)
        self.assertIn("no prior dispatch-start", err)
        self.assertNotIn("\x1b", err)
        self.assertNotIn("\x07", err)


class TestAppendRespondingTo(RouteCase):
    def test_dangling_pointer_is_rejected(self):
        # A pointer past the end of the log silently degrades the board's
        # fix-attribution; append is the one moment the referent set is known.
        code, out, err = self.append(
            rec("dispatch-start", responding_to=[5]), rtype="dispatch-start"
        )
        self.assertEqual(code, 1)
        self.assertIn("non-existent log line", err)

    def test_sentinel_zero_and_existing_lines_pass(self):
        self.write_log(rec("prd-entry"))
        code, out, err = self.append(
            rec("dispatch-start", responding_to=[0, 1]), rtype="dispatch-start"
        )
        self.assertEqual(code, 0, err)

    def test_unterminated_last_line_still_counts_as_a_referent(self):
        # The missing-trailing-newline state the writer repairs 15 lines
        # later must not undercount the referent set here.
        self.log.write_text('{"a":1}\n{"b":2}\n{"c":3}', encoding="utf-8")
        code, out, err = self.append(
            rec("dispatch-start", responding_to=[3]), rtype="dispatch-start"
        )
        self.assertEqual(code, 0, err)


class TestDuplicateKeyFailClosed(RouteCase):
    """The fail-closed consequence is intended: a log line with duplicate keys
    fails at parse — before any schema check — so validate errors and route
    blocks, neither crashes."""

    DUP_LINE = '{"type": "prd-entry", "req_id": "REQ-A-001", "req_id": "REQ-A-002"}\n'

    def test_validate_reports_duplicate_key_as_parse_error(self):
        self.log.write_text(self.DUP_LINE, encoding="utf-8")
        code, out, err = self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )
        self.assertEqual(code, 1)
        self.assertIn("invalid JSON", err)
        self.assertIn('duplicate key: "req_id"', err)
        self.assertNotIn("Traceback", err)

    def test_route_blocks_on_duplicate_key_line(self):
        self.log.write_text(self.DUP_LINE, encoding="utf-8")
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "dirty-log")
        self.assertIn('duplicate key: "req_id"', decision["errors"][0])


class TestDuplicateKeyControlBytesSanitized(RouteCase):
    """The duplicated key is agent/attacker content; a control byte in it must
    never reach the terminal raw. _reject_duplicate_keys sanitizes at message
    construction, so validate, append, and route's errors[] all inherit it."""

    # A key carrying ESC/BEL/CR, duplicated. The controls are \u-escaped so the
    # line is valid JSON; json decodes them to raw bytes before the hook runs.
    DUP = (
        '{"type": "prd-entry", "k\\u001b\\u0007\\u000dx": 1, '
        '"k\\u001b\\u0007\\u000dx": 2}\n'
    )

    def _assert_no_control_bytes(self, text):
        self.assertIn("duplicate key", text)
        for ch in ("\x1b", "\x07", "\r"):
            self.assertNotIn(ch, text)

    def test_validate_stderr_is_sanitized(self):
        self.log.write_text(self.DUP, encoding="utf-8")
        code, out, err = self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )
        self.assertEqual(code, 1)
        self._assert_no_control_bytes(err)

    def test_append_stderr_is_sanitized(self):
        code, out, err = self.run_cli(
            "append",
            "prd-entry",
            "--file",
            str(self.log),
            "--schemas",
            str(self.schemas),
            stdin=self.DUP.strip(),
        )
        self.assertEqual(code, 1)
        self._assert_no_control_bytes(err)

    def test_route_errors_entry_is_sanitized(self):
        self.log.write_text(self.DUP, encoding="utf-8")
        decision = self.route()
        self.assertEqual(decision["decision"], "blocked")
        self._assert_no_control_bytes(" ".join(decision.get("errors", [])))


class TestNonUtf8Log(RouteCase):
    """A non-UTF-8 byte in the log is a dirty-log parse error, never a
    UnicodeDecodeError traceback: parse_log caught OSError only. route blocks
    (exit 0), validate exits 1, view footers it, show degrades cleanly."""

    BAD = b'{"type": "prd-entry", "req_id": "REQ-A-001"}\n\xff\xfe\n'

    def test_route_blocks_with_exit_zero(self):
        self.log.write_bytes(self.BAD)
        decision = self.route()  # route() asserts the process exited 0
        self.assertEqual(decision["decision"], "blocked")
        self.assertEqual(decision["rule"], "dirty-log")
        self.assertIn("not valid UTF-8", " ".join(decision.get("errors", [])))

    def test_validate_exits_1_cleanly(self):
        self.log.write_bytes(self.BAD)
        code, out, err = self.run_cli(
            "validate", "--file", str(self.log), "--schemas", str(self.schemas)
        )
        self.assertEqual(code, 1)
        self.assertIn("not valid UTF-8", err)
        self.assertNotIn("Traceback", err)

    def test_view_renders_problem_footer_exit_zero(self):
        self.log.write_bytes(self.BAD)
        code, out, err = self.run_cli("view", "--file", str(self.log))
        self.assertEqual(code, 0, err)
        self.assertIn("not valid UTF-8", out)

    def test_show_degrades_without_traceback(self):
        self.log.write_bytes(self.BAD)
        code, out, err = self.run_cli("show", "--file", str(self.log))
        self.assertNotEqual(code, 0)
        self.assertIn("not valid UTF-8", err)
        self.assertNotIn("Traceback", err)


class TestScopeLockGate(RouteCase):
    """Gate 1 scope-lock: a changed or removed Non-Goals row in docs/prd.md
    routes only under a scope_overrides entry quoting the owner's decision
    (route-spec.md § Gate 1). The delta is computed by the CLI from git, so
    these cases run inside a throwaway repository."""

    PRD = (
        "# PRD\n\n## Non-Goals\n\n"
        "| ID | Non-Goal | Rationale |\n"
        "|----|----------|-----------|\n"
        "| NG-4 | Deleting a record | Stated reason |\n"
        "| NG-5 | Changing a record | Stated reason |\n"
    )

    def setUp(self):
        super().setUp()
        self.root = self.log.parent
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.root)

    def _git(self, *argv):
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", *argv],
            cwd=self.root,
            check=True,
            capture_output=True,
        )

    def _init_repo(self, prd_text):
        (self.root / "docs").mkdir(exist_ok=True)
        (self.root / "docs" / "prd.md").write_text(prd_text)
        self._git("init", "-q")
        self._git("add", "docs/prd.md")
        self._git("commit", "-q", "-m", "seed")

    def _write_prd(self, text):
        (self.root / "docs" / "prd.md").write_text(text)

    def test_ng_change_without_override_bounces(self):
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        self.write_log(rec("prd-entry"))
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn("NG-5", " ".join(decision["context"]["errors"]))

    def test_ng_change_with_dispatch_override_passes(self):
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "NG-5 is narrowed: correcting is now in.",
            "source": "dispatch",
        }
        self.write_log(rec("prd-entry", scope_overrides=[override]))
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-approved")

    def test_override_naming_unchanged_row_bounces_as_padding(self):
        self._init_repo(self.PRD)
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "quoted",
            "source": "dispatch",
        }
        self.write_log(rec("prd-entry", scope_overrides=[override]))
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn("no such Non-Goals row", " ".join(decision["context"]["errors"]))

    def test_removed_ng_row_needs_override(self):
        self._init_repo(self.PRD)
        self._write_prd(
            self.PRD.replace("| NG-4 | Deleting a record | Stated reason |\n", "")
        )
        self.write_log(rec("prd-entry"))
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn("NG-4", " ".join(decision["context"]["errors"]))

    def test_added_ng_row_is_free(self):
        self._init_repo(self.PRD)
        self._write_prd(self.PRD + "| NG-6 | New declined scope | Reason |\n")
        self.write_log(rec("prd-entry"))
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-approved")

    def test_consultation_source_requires_human_response(self):
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "Narrow NG-5 to cancellation.",
            "source": "consultation:2",
        }
        self.write_log(
            rec("consultation-request", target="human"),
            rec(
                "consultation-response",
                author="human",
                in_response_to=1,
                answer="Confirmed: Narrow NG-5 to cancellation. Proceed.",
            ),
            rec("prd-entry", scope_overrides=[override]),
        )
        self.assertEqual(self.route()["rule"], "prd-approved")

    def test_consultation_source_rejects_non_human_author(self):
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "Narrow NG-5 to cancellation.",
            "source": "consultation:2",
        }
        self.write_log(
            rec("consultation-request", target="system-design-expert"),
            rec(
                "consultation-response", author="system-design-expert", in_response_to=1
            ),
            rec("prd-entry", scope_overrides=[override]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn(
            "not a human consultation-response",
            " ".join(decision["context"]["errors"]),
        )

    def test_intake_source_with_quoted_decision_passes(self):
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "NG-5 is narrowed: correcting a visit is now in.",
            "source": "intake:1",
        }
        self.write_log(
            rec(
                "intake-decision",
                author="human",
                request="Add visit editing.",
                decisions=["NG-5 is narrowed: correcting a visit is now in."],
            ),
            rec("prd-entry", scope_overrides=[override]),
        )
        self.assertEqual(self.route()["rule"], "prd-approved")

    def test_intake_source_quote_must_appear_in_the_record(self):
        # A paraphrase is not a quote: the gate holds the verbatim-intake
        # doctrine deterministically.
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "The owner loosened NG-5.",
            "source": "intake:1",
        }
        self.write_log(
            rec(
                "intake-decision",
                author="human",
                request="Add visit editing.",
                decisions=["NG-5 is narrowed: correcting a visit is now in."],
            ),
            rec("prd-entry", scope_overrides=[override]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn(
            "quote not found in intake:1",
            " ".join(decision["context"]["errors"]),
        )

    def test_intake_request_text_is_never_the_override(self):
        # The request is context, not authority: a quote satisfied only by
        # the request (the whole task prompt in a headless seed) bounces.
        # Only a decisions item authorizes a Non-Goals change.
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "please cancel booked visits too",
            "source": "intake:1",
        }
        self.write_log(
            rec(
                "intake-decision",
                author="human",
                request="Add visit editing; please cancel booked visits too.",
                decisions=[],
            ),
            rec("prd-entry", scope_overrides=[override]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn(
            "quote not found in intake:1",
            " ".join(decision["context"]["errors"]),
        )

    def test_dispatch_source_is_rejected_once_an_intake_exists(self):
        # The legacy self-declared source loses its legality the moment a
        # verifiable home for the quote exists.
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "NG-5 is narrowed.",
            "source": "dispatch",
        }
        self.write_log(
            rec(
                "intake-decision",
                author="human",
                request="Add visit editing.",
                decisions=["NG-5 is narrowed."],
            ),
            rec("prd-entry", scope_overrides=[override]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn(
            "source 'dispatch' is not valid",
            " ".join(decision["context"]["errors"]),
        )

    def test_dispatch_source_is_rejected_across_req_ids(self):
        # Log-global: a fresh REQ id must not reopen the legacy source on a
        # project that records intake.
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "NG-5 is narrowed.",
            "source": "dispatch",
        }
        self.write_log(
            rec(
                "intake-decision",
                author="human",
                req_id="REQ-B-001",
                request="Add visit editing.",
                decisions=["NG-5 is narrowed."],
            ),
            rec("prd-entry", scope_overrides=[override]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn(
            "source 'dispatch' is not valid",
            " ".join(decision["context"]["errors"]),
        )

    def test_intake_source_rejects_a_non_intake_line(self):
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "quoted",
            "source": "intake:1",
        }
        self.write_log(
            rec("build-pass"),
            rec("prd-entry", scope_overrides=[override]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn(
            "not a human intake-decision",
            " ".join(decision["context"]["errors"]),
        )

    def test_empty_owner_decision_quote_bounces(self):
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {"non_goal_id": "NG-5", "owner_decision": "  ", "source": "dispatch"}
        self.write_log(rec("prd-entry", scope_overrides=[override]))
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn(
            "owner_decision quote is empty", " ".join(decision["context"]["errors"])
        )

    def test_no_repository_leaves_the_check_empty(self):
        # No git repository: no recorded baseline exists to protect, and the
        # build gate's audits own the loud failure in that world.
        (self.root / "docs").mkdir()
        (self.root / "docs" / "prd.md").write_text(self.PRD)
        self.write_log(rec("prd-entry"))
        self.assertEqual(self.route()["rule"], "prd-approved")

    def test_unborn_head_leaves_the_check_empty(self):
        # Fresh scaffold grace: nothing is committed, so there is no baseline
        # to expire against (mirrors the autofix audit's unborn-HEAD path).
        (self.root / "docs").mkdir()
        (self.root / "docs" / "prd.md").write_text(self.PRD)
        self._git("init", "-q")
        self.write_log(rec("prd-entry"))
        self.assertEqual(self.route()["rule"], "prd-approved")

    def test_prd_untracked_at_head_leaves_the_check_empty(self):
        (self.root / "other.txt").write_text("x")
        self._git("init", "-q")
        self._git("add", "other.txt")
        self._git("commit", "-q", "-m", "seed")
        (self.root / "docs").mkdir()
        (self.root / "docs" / "prd.md").write_text(self.PRD)
        self.write_log(rec("prd-entry"))
        self.assertEqual(self.route()["rule"], "prd-approved")

    def test_prd_deleted_from_worktree_flags_every_row(self):
        self._init_repo(self.PRD)
        (self.root / "docs" / "prd.md").unlink()
        self.write_log(rec("prd-entry"))
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        errors = " ".join(decision["context"]["errors"])
        self.assertIn("NG-4", errors)
        self.assertIn("NG-5", errors)

    def test_git_unavailable_fails_closed(self):
        # A git binary that fails to launch is not the no-repository grace
        # state: the gate must bounce, never silently pass (route-spec § Gate 1).
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        self.write_log(rec("prd-entry"))
        with unittest.mock.patch.object(
            entry.subprocess, "run", side_effect=OSError("no git")
        ):
            decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn("fails closed", " ".join(decision["context"]["errors"]))

    def test_malformed_source_bounces(self):
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {"non_goal_id": "NG-5", "owner_decision": "q", "source": "chat"}
        self.write_log(rec("prd-entry", scope_overrides=[override]))
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn("source must be", " ".join(decision["context"]["errors"]))

    def test_oversized_consultation_line_number_bounces_without_crash(self):
        # 11 digits exceeds the bounded run; the gate reports a source error
        # instead of tripping the int-from-string digit cap.
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "q",
            "source": "consultation:99999999999",
        }
        self.write_log(rec("prd-entry", scope_overrides=[override]))
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn("source must be", " ".join(decision["context"]["errors"]))

    def test_consultation_source_with_wrong_req_id_bounces(self):
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "Narrow NG-5 to cancellation.",
            "source": "consultation:2",
        }
        self.write_log(
            rec("consultation-request", target="human", req_id="REQ-B-001"),
            rec(
                "consultation-response",
                author="human",
                req_id="REQ-B-001",
                in_response_to=1,
                answer="Narrow NG-5 to cancellation.",
            ),
            rec("prd-entry", scope_overrides=[override]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn(
            "not a human consultation-response",
            " ".join(decision["context"]["errors"]),
        )

    def test_consultation_quote_must_appear_in_answer(self):
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {
            "non_goal_id": "NG-5",
            "owner_decision": "Retire NG-5 entirely.",
            "source": "consultation:2",
        }
        self.write_log(
            rec("consultation-request", target="human"),
            rec(
                "consultation-response",
                author="human",
                in_response_to=1,
                answer="No, keep NG-5 as recorded.",
            ),
            rec("prd-entry", scope_overrides=[override]),
        )
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn("quote not found", " ".join(decision["context"]["errors"]))

    def test_partial_coverage_reports_only_uncovered_row(self):
        self._init_repo(self.PRD)
        changed = self.PRD.replace("Deleting a record", "Deleting nothing").replace(
            "Changing a record", "Cancelling only"
        )
        self._write_prd(changed)
        override = {"non_goal_id": "NG-5", "owner_decision": "q", "source": "dispatch"}
        self.write_log(rec("prd-entry", scope_overrides=[override]))
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        errors = " ".join(decision["context"]["errors"])
        self.assertIn("NG-4", errors)
        self.assertNotIn("NG-5", errors)

    def test_later_prd_entry_recarries_the_override(self):
        # The delta is the uncommitted tree: a second prd-entry before the
        # slice commit re-carries the covering entry and passes.
        self._init_repo(self.PRD)
        self._write_prd(self.PRD.replace("Changing a record", "Cancelling only"))
        override = {"non_goal_id": "NG-5", "owner_decision": "q", "source": "dispatch"}
        self.write_log(
            rec("prd-entry", scope_overrides=[override]),
            rec("prd-entry", scope_overrides=[override]),
        )
        self.assertEqual(self.route()["rule"], "prd-approved")

    def test_nested_checkout_detects_row_change(self):
        # The project root sits below the git root; ls-tree must resolve the
        # prefixed path against the tree, not the cwd (--full-tree).
        proj = self.root / "proj"
        (proj / "docs").mkdir(parents=True)
        (proj / "docs" / "prd.md").write_text(self.PRD)
        self._git("init", "-q")
        self._git("add", "proj/docs/prd.md")
        self._git("commit", "-q", "-m", "seed")
        (proj / "docs" / "prd.md").write_text(
            self.PRD.replace("Changing a record", "Cancelling only")
        )
        os.chdir(proj)
        self.write_log(rec("prd-entry"))
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn("NG-5", " ".join(decision["context"]["errors"]))

    def test_indented_ng_row_is_still_guarded(self):
        indented = self.PRD.replace("| NG-5 |", "  | NG-5 |")
        self._init_repo(indented)
        self._write_prd(indented.replace("Changing a record", "Cancelling only"))
        self.write_log(rec("prd-entry"))
        decision = self.route()
        self.assertEqual(decision["rule"], "prd-gate-failed")
        self.assertIn("NG-5", " ".join(decision["context"]["errors"]))


class TestRoutingInvariants(RouteCase):
    """Cross-cutting invariants pinned as quantified properties, not single
    examples: grade neutrality, roster exactness, cap termination for any
    round past the cap, and route totality over every record type."""

    def approved(self, reviewer):
        return rec("review-feedback", author=reviewer, verdict="approved", findings=[])

    def dissent_window(self, severity="fixable", dissenter="doc-reviewer"):
        """One full review pass drawing one dissent of the given severity —
        critical from round REVIEW_ROUND_CAP on, so every round is legal and
        the counter advances past the cap."""
        finding = {
            "tag": "autofix",
            "location": "src/widget:1",
            "description": "d",
            "fix": "f",
            "severity": severity,
        }
        others = [r for r in FLOOR if r != dissenter]
        return [
            rec("build-pass"),
            *[self.approved(r) for r in others],
            rec(
                "review-feedback",
                author=dissenter,
                verdict="changes_requested",
                findings=[finding],
            ),
        ]

    def test_grader_verdict_content_never_changes_the_route(self):
        # The router may echo the verdict into context; it must never
        # branch on it — grading is advisory by contract.
        decisions = {}
        for verdict in ("clear", "concern"):
            records = [rec("build-pass")]
            records += [self.approved(r) for r in FLOOR]
            records.append(rec("grader-verdict", verdict=verdict, responding_to=[1]))
            self.write_log(*records)
            decision = self.route()
            decision.pop("verdict", None)
            decision.get("context", {}).pop("verdict", None)
            decisions[verdict] = decision
        # Anchor first: both must have taken the live grader-terminal route,
        # or the equality below would hold vacuously.
        self.assertEqual(decisions["clear"]["rule"], "feature-complete")
        self.assertEqual(decisions["clear"], decisions["concern"])

    def test_off_roster_approval_never_fills_a_roster_seat(self):
        # One floor seat outstanding; an off-roster approval must not
        # complete the review.
        records = [rec("build-pass")]
        records += [self.approved(r) for r in FLOOR[:-1]]
        records.append(self.approved("polish-reviewer"))
        self.write_log(*records)
        decision = self.route()
        self.assertEqual(decision["rule"], "reviews-needed")
        self.assertIn(FLOOR[-1], decision["next"])

    def test_off_roster_approval_beside_a_complete_roster_still_grades(self):
        records = [rec("build-pass")]
        records += [self.approved(r) for r in FLOOR]
        records.append(self.approved("polish-reviewer"))
        self.write_log(*records)
        decision = self.route()
        self.assertEqual(decision["rule"], "grade")
        self.assertEqual(decision["next"], ["change-grader"])

    def test_roster_member_latest_report_wins(self):
        # A duplicate report from a seated reviewer is one voice, and the
        # LATEST verdict is that voice — pinned in both directions.
        finding = {
            "tag": "autofix",
            "location": "src/widget:1",
            "description": "d",
            "fix": "f",
            "severity": "fixable",
        }
        dissent = rec(
            "review-feedback",
            author=FLOOR[0],
            verdict="changes_requested",
            findings=[finding],
        )
        # approved then changes_requested: the later dissent stands.
        records = [rec("build-pass")] + [self.approved(r) for r in FLOOR]
        self.write_log(*records, dissent)
        self.assertEqual(self.route()["rule"], "process-findings")
        # changes_requested then approved: the later approval stands.
        records = [rec("build-pass"), dissent] + [self.approved(r) for r in FLOOR]
        self.write_log(*records)
        self.assertEqual(self.route()["rule"], "grade")

    def test_round_cap_blocks_for_any_round_past_the_cap(self):
        # Quantified past the cap: however many rounds beyond
        # REVIEW_ROUND_CAP the log carries, the decision is the terminal
        # non-convergence block — never a further dispatch.
        for rounds in range(REVIEW_ROUND_CAP + 1, REVIEW_ROUND_CAP + 4):
            with self.subTest(rounds=rounds):
                records = []
                for n in range(rounds):
                    severity = "critical" if n + 1 >= REVIEW_ROUND_CAP else "fixable"
                    records += self.dissent_window(severity=severity)
                self.write_log(*records)
                decision = self.route()
                self.assertEqual(decision["decision"], "blocked")
                self.assertEqual(decision["rule"], "review-non-convergence")

    def test_pipeline_types_cover_every_record_type(self):
        # The totality sweep below quantifies over PIPELINE_TYPES; a new
        # record type must join it, or the sweep silently narrows.
        self.assertEqual(set(PIPELINE_TYPES), set(_RECORD_TYPES))

    def test_every_record_type_alone_routes_to_a_decision(self):
        # Totality: any single record as the whole log yields a well-formed
        # decision — dispatch, blocked, or escalate, with a rule — never a
        # crash. The auto_grade fail-open pin lives with the other layout
        # toggles (test_auto_grade_non_bool_fails_open_to_grading).
        for rtype in PIPELINE_TYPES:
            with self.subTest(rtype=rtype):
                self.write_log(rec(rtype))
                decision = self.route()
                self.assertIn(decision["decision"], {"dispatch", "blocked", "escalate"})
                self.assertIn("rule", decision)


if __name__ == "__main__":
    unittest.main(verbosity=2)
