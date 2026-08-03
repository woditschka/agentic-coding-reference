#!/usr/bin/env python3
"""Routing-core suite: the Handoff Conditions table, gates, recovery ladders,
consultation routing, and the fail-closed damage modes — handoff.routing,
exercised through the CLI entry point (ADR 2026-07-17 runtime-package-layout)."""

import json
import unittest

from tests.support import (
    FLOOR,
    TS,
    RouteCase,
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

    def test_stale_human_request_does_not_refire(self):
        # Root re-dispatched after the conversation without appending the
        # response; the newer substantive record wins.
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
        self.assertEqual(decision["decision"], "dispatch")
        self.assertEqual(decision["next"], ["system-design-expert"])

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
