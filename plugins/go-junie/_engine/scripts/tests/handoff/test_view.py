#!/usr/bin/env python3
"""Board-renderer suite: the TTY board, its Markdown twin, and the cost
overlay — handoff.view, exercised through render_view/render_view_md and the
CLI entry point (ADR 2026-07-17 runtime-package-layout)."""

import contextlib
import io
import json
import os
import re
import unittest
import unittest.mock

from tests.support import (
    REQ,
    TS,
    VIEW_SNAPSHOT,
    HandoffCase,
    entry,
    handoff,
    rec,
    timed_fixture,
    view_fixture,
    vrec,
)


class TestView(HandoffCase):
    def setUp(self):
        super().setUp()
        # Hermetic cost overlay: point the transcript index at an empty tree so
        # the board's per-step cost never depends on the host's real Claude
        # Code history. TestBoardCost supplies its own synthetic transcripts.
        patcher = unittest.mock.patch.dict(
            os.environ, {"CLAUDE_PROJECTS_ROOT": str(self.log.parent / "no-projects")}
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def view(self, *extra):
        # --layout points at a nonexistent file so a real scripts/layout.toml
        # in the invoking project cannot leak extra reviewers into the matrix.
        return self.run_cli(
            "view",
            "--file",
            str(self.log),
            "--no-color",
            "--layout",
            str(self.log.parent / "layout.toml"),
            *extra,
        )

    def test_missing_log_renders_a_message(self):
        code, out, err = self.view()
        self.assertEqual(code, 0, err)
        self.assertIn("no handoff log", out)

    def test_empty_log_renders_without_error(self):
        self.log.write_text("")
        code, out, _ = self.view()
        self.assertEqual(code, 0)
        self.assertIn("handoff log is empty", out)

    def test_plain_output_is_byte_stable(self):
        self.write_log(*view_fixture())
        code, out, err = self.view()
        self.assertEqual(code, 0, err)
        self.assertEqual(out, VIEW_SNAPSHOT)

    def test_orders_by_append_position_not_ts(self):
        # The design-block carries the earliest ts in the fixture yet must
        # render after the prd-entry: file position is the only clock.
        self.write_log(*view_fixture())
        _, out, _ = self.view()
        self.assertLess(out.index("◇ prd-entry"), out.index("◈ design-block"))

    def test_rounds_group_by_reviewer_reappearance(self):
        self.write_log(*view_fixture())
        _, out, _ = self.view()
        self.assertIn("R1     R2     R3", out)
        self.assertIn("code-quality  ✎ (2)  ✎ (1)  ✔", out)
        self.assertIn("security      ✔ (1)  ·      ·", out)

    def test_dispatch_start_and_grader_features_are_filtered(self):
        self.write_log(*view_fixture())
        _, out, _ = self.view()
        self.assertNotIn("dispatch-start", out)
        self.assertNotIn("grader-features", out)

    def test_implementer_fix_opens_a_session_sibling_doc_fix_stays_flat(self):
        # In a fix round the coordinator dispatches the implementer AND a
        # doc-owner concurrently, so the doc-owner's dispatch interleaves INTO
        # the implementer's session window (between its opener and its build).
        # It is a SIBLING, not session plumbing: it must hoist to a flat ↻ fix
        # line, not be absorbed. The implementer's fix opens the session; the
        # reviewer fan-out dispatch stays suppressed.
        self.write_log(
            vrec(
                "design-block",
                "system-design-expert",
                "2026-07-06T10:00:00Z",
                verdict="covered",
            ),  # L1
            vrec(
                "dispatch-start",
                "feature-implementer",
                "2026-07-06T10:05:00Z",
                responding_to=[1],
            ),  # L2 S1 opener
            vrec(
                "build-pass",
                "feature-implementer",
                "2026-07-06T10:10:00Z",
                gate_checks_run=["test"],
            ),  # L3 closes S1
            vrec(
                "review-feedback",
                "code-quality-reviewer",
                "2026-07-06T10:20:00Z",
                verdict="changes_requested",
                findings=[
                    {
                        "tag": "blocked",
                        "location": "limiter.py:42",
                        "description": "race",
                    }
                ],
            ),  # L4
            vrec(
                "review-feedback",
                "doc-reviewer",
                "2026-07-06T10:21:00Z",
                verdict="changes_requested",
                findings=[
                    {"tag": "autofix", "location": "prd.md:9", "description": "stale"}
                ],
            ),  # L5
            vrec(
                "dispatch-start",
                "security-reviewer",
                "2026-07-06T10:30:00Z",
                responding_to=[3],
            ),  # L6 noise
            vrec(
                "dispatch-start",
                "feature-implementer",
                "2026-07-06T10:31:00Z",
                responding_to=[4],
            ),  # L7 S2 fix opener
            vrec(
                "dispatch-start",
                "product-requirements-expert",
                "2026-07-06T10:32:00Z",
                responding_to=[5],
            ),  # L8 sibling doc fix
            vrec(
                "build-pass",
                "feature-implementer",
                "2026-07-06T10:40:00Z",
                gate_checks_run=["test"],
            ),  # L9 closes S2
        )
        _, out, _ = self.view()
        self.assertIn("↻ implement  (implementer)  ← code-quality", out)
        # The interleaved sibling survives, hoisted flat after the session. Its
        # dimension is never re-approved here, so it carries no duration — the
        # line ends at the finding count.
        self.assertIn("↻ fix  prd-expert  ← doc  (1 finding)\n", out)
        self.assertGreater(
            out.index("↻ fix  prd-expert"),
            out.index("↻ implement  (implementer)  ← code-quality"),
        )
        self.assertEqual(out.count("↻ fix"), 1)  # only the doc-owner
        self.assertEqual(out.count("◆ implement"), 1)  # only the fresh S1
        self.assertNotIn("↻ fix  security", out)  # reviewer dispatch suppressed

    def test_fresh_implement_opens_a_session_with_its_clean_build(self):
        # A fresh implementer dispatch opens a ◆ implement session; its
        # build-pass renders as the closing └ ▲ build ✓ clean child — the build
        # names no author, so the parent is where the implementer surfaces.
        self.write_log(
            vrec(
                "prd-entry",
                "product-requirements-expert",
                "2026-07-06T10:00:00Z",
                title="t",
            ),  # L1
            vrec(
                "design-block",
                "system-design-expert",
                "2026-07-06T10:05:00Z",
                verdict="covered",
            ),  # L2
            vrec(
                "dispatch-start",
                "feature-implementer",
                "2026-07-06T10:06:00Z",
                responding_to=[2],
            ),  # opener
            vrec(
                "build-pass",
                "feature-implementer",
                "2026-07-06T10:10:00Z",
                gate_checks_run=["test"],
            ),  # L4
        )
        _, out, _ = self.view()
        # The parent carries the session elapsed (10:06 → 10:10 = 4m), not a
        # start time; the build child carries no timestamp.
        self.assertIn("◆ implement  (implementer)  ◷ 4m", out)
        self.assertIn("  └ ▲ build  ✓ clean", out)
        self.assertEqual(out.count("◆ implement"), 1)
        # The clean build is the session's closing child, below its opener.
        self.assertGreater(out.index("└ ▲ build"), out.index("◆ implement"))
        self.assertGreater(out.index("◆ implement"), out.index("design-block"))

    def test_retry_nests_under_one_implement_session(self):
        # A build retry re-dispatches the implementer, but that interior
        # dispatch is absorbed: the session shows ONE ◆ implement opener with
        # the failed build as a ├ child and the clean build as the └ child.
        self.write_log(
            vrec(
                "design-block",
                "system-design-expert",
                "2026-07-06T10:05:00Z",
                verdict="covered",
            ),  # L1
            vrec(
                "dispatch-start",
                "feature-implementer",
                "2026-07-06T10:06:00Z",
                responding_to=[1],
            ),  # opener
            vrec(
                "build-failure",
                "feature-implementer",
                "2026-07-06T10:08:00Z",
                retry=1,
                failed_check="test",
            ),  # L3
            vrec(
                "dispatch-start",
                "feature-implementer",
                "2026-07-06T10:09:00Z",
                responding_to=[3],
            ),  # retry (absorbed)
            vrec(
                "build-pass",
                "feature-implementer",
                "2026-07-06T10:10:00Z",
                gate_checks_run=["test"],
            ),  # L5
        )
        _, out, _ = self.view()
        self.assertEqual(out.count("◆ implement"), 1)
        self.assertIn("◆ implement  (implementer)  ◷ 4m", out)  # 10:06 → 10:10
        self.assertIn("  ├ ▲ build  ✗ test failed  retry 1", out)
        self.assertIn("  └ ▲ build  ✓ clean", out)

    def test_abort_closed_session_carries_duration_and_stops_absorption(self):
        # An aborting build-failure closes the session like a clean build: the
        # parent carries the opener → abort elapsed (and the cost when a lookup
        # attributes), and nothing after the abort is absorbed — the
        # implementer's own trailing consult renders flat, not as a child.
        self.write_log(
            vrec(
                "design-block",
                "system-design-expert",
                "2026-07-06T10:00:00Z",
                verdict="covered",
            ),  # L1
            vrec(
                "dispatch-start",
                "feature-implementer",
                "2026-07-06T10:06:00Z",
                responding_to=[1],
            ),  # opener
            vrec(
                "build-failure",
                "feature-implementer",
                "2026-07-06T10:11:00Z",
                abort_reason="design-mismatch",
            ),  # closes
            vrec(
                "consultation-request",
                "feature-implementer",
                "2026-07-06T10:12:00Z",
                target="system-design-expert",
                context="c",
                question="Re-triage?",
            ),  # after close
        )
        _, out, _ = self.view()
        self.assertIn("◆ implement  (implementer)  ◷ 5m", out)
        self.assertIn("  └ ▲ build  ✗ aborted: design-mismatch", out)
        self.assertIn("↳ consult  implementer → design", out)  # flat
        self.assertNotIn("└ ↳ consult", out)
        cost = " │ Σ ▲7.5M ▼17k $4.66 │ ⛁ 99% $89%"
        entries, errors = handoff.parse_log(str(self.log))
        lines, _ = handoff.render_view(
            entries,
            errors,
            REQ,
            list(handoff.ROSTER_FLOOR),
            color=False,
            verbose=False,
            cost_lookup=lambda at, s, e: [(cost, handoff.DIM)],
        )
        self.assertIn("◆ implement  (implementer)  ◷ 5m" + cost, "\n".join(lines))

    def test_retry_only_session_stays_bare(self):
        # A plain retry failure does not close the session; with no closer in
        # the log (truncated/still running) the parent keeps the omission —
        # timing it would guess at an unfinished span.
        self.write_log(
            vrec(
                "design-block",
                "system-design-expert",
                "2026-07-06T10:00:00Z",
                verdict="covered",
            ),  # L1
            vrec(
                "dispatch-start",
                "feature-implementer",
                "2026-07-06T10:06:00Z",
                responding_to=[1],
            ),  # opener
            vrec(
                "build-failure",
                "feature-implementer",
                "2026-07-06T10:11:00Z",
                retry=1,
                failed_check="test",
            ),  # child
        )
        _, out, _ = self.view()
        self.assertIn("◆ implement  (implementer)\n", out)
        self.assertNotIn("(implementer)  ◷", out)

    def test_record_producing_steps_show_dispatch_to_output_duration(self):
        # Every step that emits a record is timed from its author's
        # dispatch-start to that record: prd-entry, design-block, the implement
        # session, and each review. The grade stays untimed by contract.
        self.write_log(*timed_fixture())
        _, out, _ = self.view()
        self.assertIn("(prd-expert)  ◷ 3m", out)
        self.assertIn("(design)  ◷ 2m", out)
        self.assertIn("◆ implement  (implementer)  ◷ 15m", out)
        self.assertIn("review  code-quality  approved  ◷ 2m", out)
        # The grade is untimed by contract — no dispatch can name its author.
        self.assertIn("◆ grade  CLEAR  done", out)
        self.assertNotIn("done  ◷", out)

    def test_producer_dispatch_does_not_pair_across_slices(self):
        # A step's start is a dispatch in its OWN slice. A code-quality review
        # in slice B whose only same-author dispatch lives in slice A must show
        # no duration, not borrow slice A's dispatch for an inflated span.
        self.write_log(
            vrec(
                "dispatch-start",
                "code-quality-reviewer",
                "2026-07-06T09:00:00Z",
                req_id="REQ-A",
                responding_to=[0],
            ),
            vrec(
                "build-pass",
                "feature-implementer",
                "2026-07-06T09:05:00Z",
                req_id="REQ-A",
                gate_checks_run=["test"],
            ),
            vrec(
                "review-feedback",
                "code-quality-reviewer",
                "2026-07-06T10:00:00Z",
                req_id="REQ-B",
                verdict="approved",
                findings=[],
            ),
        )
        _, out, _ = self.view()
        self.assertNotIn("code-quality  approved  ◷", out)

    def test_doc_fix_carries_no_duration(self):
        # A doc-owner fix emits no record, so it has no dispatch → output span
        # like the timed steps; ◷ means work time everywhere, so the fix line
        # stays bare even when its dimension is later re-approved.
        self.write_log(
            vrec(
                "design-block",
                "system-design-expert",
                "2026-07-06T10:00:00Z",
                verdict="covered",
            ),  # L1
            vrec(
                "dispatch-start",
                "feature-implementer",
                "2026-07-06T10:00:00Z",
                responding_to=[1],
            ),  # L2
            vrec(
                "build-pass",
                "feature-implementer",
                "2026-07-06T10:05:00Z",
                gate_checks_run=["test"],
            ),  # L3
            vrec(
                "review-feedback",
                "doc-reviewer",
                "2026-07-06T10:10:00Z",
                verdict="changes_requested",
                findings=[
                    {"tag": "autofix", "location": "prd.md:9", "description": "stale"}
                ],
            ),  # L4 findings
            vrec(
                "dispatch-start",
                "product-requirements-expert",
                "2026-07-06T10:11:00Z",
                responding_to=[4],
            ),  # L5 doc fix
            vrec(
                "review-feedback",
                "doc-reviewer",
                "2026-07-06T10:25:00Z",
                verdict="approved",
                findings=[],
            ),  # L6
        )
        _, out, _ = self.view()
        # No ◷ on the fix line — it ends at the finding count.
        self.assertIn("↻ fix  prd-expert  ← doc  (1 finding)\n", out)
        self.assertNotIn("← doc  (1 finding)  ◷", out)

    def test_sibling_consult_stays_flat_with_its_author(self):
        # A sibling doc-owner's mid-window consult is not the implementer's:
        # it hoists out of the session as a flat line naming its author. A
        # `├ ↳` child would misattribute the question to the implementer.
        self.write_log(
            vrec(
                "design-block",
                "system-design-expert",
                "2026-07-06T10:00:00Z",
                verdict="covered",
            ),  # L1
            vrec(
                "review-feedback",
                "doc-reviewer",
                "2026-07-06T10:20:00Z",
                verdict="changes_requested",
                findings=[
                    {"tag": "autofix", "location": "prd.md:9", "description": "stale"}
                ],
            ),  # L2
            vrec(
                "dispatch-start",
                "feature-implementer",
                "2026-07-06T10:31:00Z",
                responding_to=[2],
            ),  # opener
            vrec(
                "dispatch-start",
                "product-requirements-expert",
                "2026-07-06T10:32:00Z",
                responding_to=[2],
            ),  # sibling fix
            vrec(
                "consultation-request",
                "product-requirements-expert",
                "2026-07-06T10:33:00Z",
                target="system-design-expert",
                context="c",
                question="Fixed burst size?",
            ),  # sibling consult
            vrec(
                "build-pass",
                "feature-implementer",
                "2026-07-06T10:40:00Z",
                gate_checks_run=["test"],
            ),  # closes session
        )
        _, out, _ = self.view()
        self.assertIn("↳ consult  prd-expert → design", out)  # flat, real author
        self.assertNotIn("├ ↳ consult", out)  # not a session child
        self.assertIn("↻ fix  prd-expert  ← doc", out)  # sibling fix survives

    def test_doc_autofix_inside_session_hoists_instead_of_truncating(self):
        # A root-applied design-doc-autofix interleaving between the opener
        # and the clean build is a sibling, not a session ender: the session
        # keeps its duration and its └ ✓ clean child, and the autofix renders
        # flat after it.
        self.write_log(
            vrec(
                "design-block",
                "system-design-expert",
                "2026-07-06T10:00:00Z",
                verdict="covered",
            ),  # L1
            vrec(
                "dispatch-start",
                "feature-implementer",
                "2026-07-06T10:06:00Z",
                responding_to=[1],
            ),  # opener
            vrec(
                "design-doc-autofix",
                "claude",
                "2026-07-06T10:08:00Z",
                file="docs/system-design.md",
                category="stale-reference",
                source_finding="x",
                old_content="a",
                new_content="b",
                lines_changed=1,
                chars_changed=2,
            ),  # interleaved
            vrec(
                "build-pass",
                "feature-implementer",
                "2026-07-06T10:10:00Z",
                gate_checks_run=["test"],
            ),  # L4
        )
        _, out, _ = self.view()
        self.assertIn("◆ implement  (implementer)  ◷ 4m", out)
        self.assertIn("  └ ▲ build  ✓ clean", out)
        self.assertIn("✚ doc-autofix", out)  # hoisted, still visible
        self.assertNotIn("── ▲ build-pass", out)  # no flat fallback

    def test_re_engaged_review_carries_no_duration(self):
        # A reviewer re-engaged for round 2 (a SendMessage continue) appends
        # no fresh dispatch-start. Pairing review#2 with the round-1 dispatch
        # would span the implementer's rework and re-sum round-1 spend, so
        # the dispatch times only the first record of a type: review#2 shows
        # no ◷ rather than a wrong one.
        self.write_log(
            vrec(
                "dispatch-start",
                "code-quality-reviewer",
                "2026-07-06T10:00:00Z",
                responding_to=[0],
            ),  # L1
            vrec(
                "review-feedback",
                "code-quality-reviewer",
                "2026-07-06T10:05:00Z",
                verdict="changes_requested",
                findings=[{"tag": "blocked", "location": "a.py:1", "description": "x"}],
            ),  # L2 → 5m
            vrec(
                "review-feedback",
                "code-quality-reviewer",
                "2026-07-06T10:35:00Z",
                verdict="approved",
                findings=[],
            ),  # L3 re-engaged
        )
        _, out, _ = self.view()
        self.assertIn("changes_requested  (1 finding)  ◷ 5m", out)
        self.assertNotIn("approved  ◷", out)

    def test_consecutive_identical_gates_are_distinguished_by_time(self):
        # Two build-passes with the same checks (e.g. one per findings-owner
        # dispatch) must not render as an inexplicable doubled line.
        self.write_log(
            rec("prd-entry", title="t"),
            rec("build-pass", ts="2026-07-06T13:32:00Z", gate_checks_run=["test"]),
            rec("build-pass", ts="2026-07-06T14:10:00Z", gate_checks_run=["test"]),
        )
        _, out, _ = self.view()
        self.assertIn("▲ build-pass 13:32", out)
        self.assertIn("▲ build-pass 14:10", out)

    def test_no_grader_verdict_renders_no_grade_yet_by_default(self):
        self.write_log(rec("prd-entry", title="t"), rec("build-pass"))
        _, out, _ = self.view()
        self.assertIn("no grade yet", out)

    def test_auto_grade_false_renders_grading_disabled(self):
        # With grading off no grade is coming; "yet" would read as pending.
        (self.log.parent / "layout.toml").write_text("[harness]\nauto_grade = false\n")
        self.write_log(rec("prd-entry", title="t"), rec("build-pass"))
        _, out, _ = self.view()
        self.assertIn("grading disabled", out)
        self.assertNotIn("no grade yet", out)

    def test_color_flag_forces_ansi_through_a_pipe(self):
        # An agent's shell tool pipes stdout (no TTY); --color must still
        # emit ANSI so the conversation terminal can render the styling.
        self.write_log(rec("prd-entry", title="t"), rec("build-pass"))
        code, out, err = self.run_cli(
            "view",
            "--file",
            str(self.log),
            "--color",
            "--layout",
            str(self.log.parent / "layout.toml"),
        )
        self.assertEqual(code, 0, err)
        self.assertIn("\x1b[", out)

    def test_color_flag_beats_no_color_env(self):
        # NO_COLOR suppresses auto-detection; an explicit --color is the
        # user requesting color and wins (per the NO_COLOR spec).
        self.write_log(rec("prd-entry", title="t"), rec("build-pass"))
        old = os.environ.get("NO_COLOR")
        os.environ["NO_COLOR"] = "1"
        try:
            code, out, err = self.run_cli(
                "view",
                "--file",
                str(self.log),
                "--color",
                "--layout",
                str(self.log.parent / "layout.toml"),
            )
        finally:
            if old is None:
                del os.environ["NO_COLOR"]
            else:
                os.environ["NO_COLOR"] = old
        self.assertEqual(code, 0, err)
        self.assertIn("\x1b[", out)

    def test_color_and_no_color_are_mutually_exclusive(self):
        self.write_log(rec("prd-entry", title="t"))
        code, _, err = self.run_cli(
            "view",
            "--file",
            str(self.log),
            "--color",
            "--no-color",
        )
        self.assertEqual(code, 2)
        self.assertIn("not allowed with", err)

    def test_verbose_prints_full_description_then_fix(self):
        self.write_log(*view_fixture())
        _, out, _ = self.view("--verbose")
        self.assertLess(
            out.index("observe a single remaining token and pass."),
            out.index("fix: Hold the lock across the refill and the take."),
        )

    def test_no_req_id_renders_every_slice_oldest_first(self):
        self.write_log(
            rec("prd-entry", title="Original"),
            rec(
                "prd-entry",
                req_id="REQ-B-002",
                title="Refactor sibling",
                author="system-design-expert",
            ),
        )
        _, out, _ = self.view()
        # Both slices render as their own board, in append order — the older
        # REQ-A-001 first — and no "also in log" pointer survives.
        self.assertLess(out.index("REQ-A-001"), out.index("REQ-B-002"))
        self.assertIn("Original", out)
        self.assertIn("Refactor sibling", out)
        self.assertNotIn("also in log", out)

    def test_no_req_id_gives_each_slice_its_own_header_box(self):
        self.write_log(
            rec("prd-entry", title="Original"),
            rec(
                "prd-entry",
                req_id="REQ-B-002",
                title="Refactor sibling",
                author="system-design-expert",
            ),
        )
        _, out, _ = self.view()
        self.assertEqual(out.count("╭"), 2)

    def test_req_id_flag_selects_a_slice(self):
        self.write_log(
            rec("prd-entry", title="Original"),
            rec(
                "prd-entry",
                req_id="REQ-B-002",
                title="Refactor sibling",
                author="system-design-expert",
            ),
        )
        _, out, _ = self.view("--req-id", "REQ-A-001")
        self.assertIn("Original", out)
        self.assertNotIn("Refactor sibling", out)

    def test_unknown_req_id_exits_three(self):
        self.write_log(rec("prd-entry", title="T"))
        code, out, _ = self.view("--req-id", "REQ-NOPE-999")
        self.assertEqual(code, 3)
        self.assertIn("no records for REQ-NOPE-999", out)
        self.assertIn("in log: REQ-A-001", out)

    def test_req_id_against_empty_log_exits_three(self):
        self.log.write_text("")
        code, out, _ = self.view("--req-id", "REQ-NOPE-999")
        self.assertEqual(code, 3)
        self.assertIn("no records for REQ-NOPE-999", out)

    def test_extra_reviewer_from_layout_gets_a_lane(self):
        # The extra reviewer files no review: only the roster wiring can put
        # its idle lane in the matrix, so this cannot pass vacuously.
        (self.log.parent / "layout.toml").write_text(
            '[harness]\nextra_reviewers = ["perf-reviewer"]\n'
        )
        self.write_log(
            rec(
                "review-feedback",
                author="code-quality-reviewer",
                verdict="approved",
                findings=[],
            ),
        )
        _, out, _ = self.view()
        perf_lane = [l for l in out.splitlines() if l.startswith("perf")]
        self.assertEqual(len(perf_lane), 1, out)
        self.assertIn("·", perf_lane[0])
        self.assertNotIn("✔", perf_lane[0])

    def test_malformed_layout_falls_back_to_the_floor(self):
        (self.log.parent / "layout.toml").write_text(
            '[harness]\nextra_reviewers = "oops"\n'
        )
        self.write_log(rec("review-feedback", verdict="approved", findings=[]))
        code, out, _ = self.view()
        self.assertEqual(code, 0)
        self.assertIn("code-quality", out)

    def test_missing_fields_and_unknown_types_render(self):
        self.write_log(
            rec(
                "review-feedback",
                author="code-quality-reviewer",
                verdict="changes_requested",
                findings=["not-a-dict", {"location": 7}],
            ),
            # Unhashable verdicts must fall through the glyph lookup, not raise.
            rec(
                "review-feedback",
                author="test-reviewer",
                verdict=["approved"],
                findings=[],
            ),
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict={"v": "approved"},
                findings=[],
            ),
            rec(
                "grader-verdict",
                author="change-grader",
                facets={"blast_radius": "not-a-dict"},
            ),
            {"type": "prd-entry", "req_id": "REQ-A-001", "ts": TS},
            {"type": None, "req_id": "REQ-A-001"},
        )
        code, out, err = self.view()
        self.assertEqual(code, 0, err)
        self.assertIn("(untitled)", out)
        self.assertIn("blast_radius", out)
        self.assertEqual(out.count("review  "), 3)

    def test_dirty_log_renders_parsed_records_with_a_footer(self):
        self.log.write_text(json.dumps(rec("prd-entry", title="T")) + "\nnot json\n")
        code, out, _ = self.view()
        self.assertEqual(code, 0)
        self.assertIn("prd-entry", out)
        self.assertIn("problem line", out)
        self.assertIn("line 2", out)

    def test_remaining_renderer_branches(self):
        self.write_log(
            rec(
                "design-block",
                author="system-design-expert",
                verdict="minor",
                supersedes_record_at=1,
            ),
            rec(
                "build-failure",
                author="feature-implementer",
                abort_reason="design-mismatch",
            ),
            rec(
                "consultation-response",
                author="system-design-expert",
                in_response_to=99,
                answer="a",
            ),
            rec(
                "review-feedback",
                author="doc-reviewer",
                verdict="blocked",
                findings=[
                    {
                        "tag": "blocked",
                        "location": "x",
                        "description": "d",
                        "severity": "critical",
                    }
                ],
            ),
        )
        code, out, _ = self.view()
        self.assertEqual(code, 0)
        self.assertIn("supersedes L1", out)
        self.assertIn("abort: design-mismatch", out)
        self.assertIn("design → ?", out)  # dangling in_response_to
        self.assertIn("✖", out)

    def test_records_without_req_id_render_unfiltered(self):
        self.write_log(
            {"type": "prd-entry", "ts": TS, "author": "tester", "title": "T"}
        )
        code, out, _ = self.view()
        self.assertEqual(code, 0)
        self.assertIn("(no req_id)", out)
        self.assertIn("T", out)

    def test_color_follows_tty_and_no_color_env(self):
        self.write_log(rec("prd-entry", title="T"))

        class Tty(io.StringIO):
            def isatty(self):
                return True

        argv = [
            "view",
            "--file",
            str(self.log),
            "--layout",
            str(self.log.parent / "layout.toml"),
        ]
        saved = os.environ.pop("NO_COLOR", None)
        try:
            out = Tty()
            with contextlib.redirect_stdout(out):
                entry.main(argv)
            self.assertIn("\x1b[", out.getvalue())
            os.environ["NO_COLOR"] = "1"
            out = Tty()
            with contextlib.redirect_stdout(out):
                entry.main(argv)
            self.assertNotIn("\x1b[", out.getvalue())
        finally:
            os.environ.pop("NO_COLOR", None)
            if saved is not None:
                os.environ["NO_COLOR"] = saved

    def test_log_content_cannot_inject_terminal_escapes(self):
        # The log is agent-authored: a record embedding raw escape bytes
        # (window title, hidden text) must never reach the terminal.
        hostile = "Innocent\x1b]0;pwned\x07\x1b[8m hidden\x00\ttail"
        self.write_log(
            rec("prd-entry", title=hostile),
            rec("build-pass", gate_checks_run=[hostile]),
            rec(
                "review-feedback",
                author="evil\x1b[2Jer-reviewer",
                verdict="changes_requested",
                findings=[
                    {
                        "tag": "autofix",
                        "location": hostile,
                        "description": hostile,
                        "fix": hostile,
                    }
                ],
            ),
        )
        for flags in ((), ("--verbose",)):
            code, out, _ = self.view(*flags)
            self.assertEqual(code, 0)
            self.assertNotIn("\x1b", out)
            self.assertNotIn("\x00", out)
            self.assertIn("Innocent", out)

    def test_hostile_req_id_cannot_inject_via_the_in_log_line(self):
        # The "in log:" and "no records for" lines print agent-authored
        # req_ids: an escape byte there must not reach the terminal either.
        self.write_log(
            {
                "type": "prd-entry",
                "req_id": "\x1b]0;pwned\x07\x1b[2Jgood",
                "ts": TS,
                "author": "tester",
                "title": "x",
            },
        )
        code, out, _ = self.view("--req-id", "REQ-MISSING-000")
        self.assertEqual(code, 3)
        self.assertNotIn("\x1b", out)
        self.assertIn("in log:", out)

    def test_colored_output_aligns_with_plain(self):
        # Padding is computed on plain text before escapes are added, so
        # stripping the escapes must reproduce the plain rendering exactly.
        self.write_log(*view_fixture())
        entries, errors = handoff.parse_log(str(self.log))
        roster = list(handoff.ROSTER_FLOOR)
        plain, _ = handoff.render_view(
            entries, errors, REQ, roster, color=False, verbose=False
        )
        colored, _ = handoff.render_view(
            entries, errors, REQ, roster, color=True, verbose=False
        )
        ansi = re.compile(r"\x1b\[[0-9;]*m")
        self.assertEqual([ansi.sub("", line) for line in colored], plain)
        self.assertTrue(any("\x1b[" in line for line in colored))


class TestViewMarkdown(HandoffCase):
    """view --markdown: the same board as Markdown, for agent transcripts that
    strip ANSI but render Markdown. Grouping is shared with the TTY renderer;
    these tests pin the Markdown line composition and the escaping rules."""

    def setUp(self):
        super().setUp()
        patcher = unittest.mock.patch.dict(
            os.environ, {"CLAUDE_PROJECTS_ROOT": str(self.log.parent / "no-projects")}
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def mdview(self, *extra):
        return self.run_cli(
            "view",
            "--file",
            str(self.log),
            "--markdown",
            "--layout",
            str(self.log.parent / "layout.toml"),
            *extra,
        )

    def test_header_is_h3_with_selective_bold_summary(self):
        # Only what ANSI highlights is bold: the failure count and the grade.
        self.write_log(*view_fixture())
        code, out, err = self.mdview()
        self.assertEqual(code, 0, err)
        self.assertIn("### REQ-DEMO-001 — Rate-limit the API\n", out)
        self.assertIn(
            "3 review rounds · 2 build-passes · **1 build-failure**"
            " · grade **CLEAR**\n",
            out,
        )
        self.assertNotIn("**3 review rounds", out)
        self.assertNotIn("╭", out)
        self.assertNotIn("\x1b[", out)

    def test_grade_line_variants(self):
        self.write_log(rec("prd-entry", title="t"), rec("build-pass"))
        _, out, _ = self.mdview()
        self.assertIn("0 review rounds · 1 build-pass · no grade yet\n", out)
        # The flat gate line is colored in ANSI: its kind token is bold here.
        self.assertIn("- ▲ **build-pass** 10:00\n", out)
        (self.log.parent / "layout.toml").write_text("[harness]\nauto_grade = false\n")
        _, out, _ = self.mdview()
        self.assertIn("· grading disabled\n", out)
        self.assertNotIn("no grade yet", out)

    def test_matrix_renders_as_table(self):
        # Anchor layer: reviewer names bold, settled ✔/✖ outcomes bold;
        # ✎ rounds-in-progress and absent · stay plain.
        self.write_log(*view_fixture())
        _, out, _ = self.mdview()
        self.assertIn("| reviewer | R1 | R2 | R3 |\n", out)
        self.assertIn("| --- | --- | --- | --- |\n", out)
        self.assertIn("| **code-quality** | ✎ (2) | ✎ (1) | **✔** |\n", out)
        self.assertIn("| **security** | **✔** (1) | · | · |\n", out)
        self.assertIn("| **test** | · | · | · |\n", out)  # absent cells

    def test_timeline_bullets_with_nested_children(self):
        self.write_log(*view_fixture())
        _, out, _ = self.mdview()
        # Anchor layer: known step kinds bold — fused with their actor on
        # review/grade lines; the ANSI floor keeps verdicts and outcomes bold.
        self.assertIn("- ◇ **prd-entry** Rate-limit the API · (prd-expert)\n", out)
        self.assertIn("- ◈ **design-block** **minor** · (design)\n", out)
        # The implement session keeps its grouping: the parent bullet carries
        # the session elapsed italic, the children nest without glyphs.
        self.assertIn("- ◆ **implement** (implementer) · ***◷ 15m***\n", out)
        # The consult peer is the bold token (BOLD in ANSI), scaffolding plain.
        self.assertIn("  - ↳ consult → **design** · Per-tenant or per-endpoint?\n", out)
        self.assertIn("  - ↲ consult ← **design** · Per-tenant.\n", out)
        # `build` shares the outcome's ANSI color, so it rides the bold span.
        self.assertIn("  - ▲ **build ✗ unit-test failed** · retry 1\n", out)
        self.assertIn("  - ▲ **build ✓ clean** · fmt · test\n", out)
        self.assertIn(
            "- ✎ **review code-quality** · **changes_requested** · (2 findings)\n", out
        )
        self.assertIn("- ✔ **review security** · **approved** · (1 finding)\n", out)
        # Findings nest under the review: [tag] + code location + gist; only
        # the red-family tags (blocked, escalate) carry bold.
        self.assertIn("  - **[blocked]** `limiter.py:42` The bucket refill races", out)
        self.assertIn("  - **[escalate]** `limiter.py:88`", out)
        self.assertIn("  - [autofix] `limiter.py:12`", out)
        self.assertIn("  - [clarify] `prd.md:9`", out)
        # The rework anchor is the kind; its `←` source stays plain.
        self.assertIn(
            "- ↻ **implement** (implementer) ← code-quality"
            " · (1 finding) · ***◷ 4m***\n",
            out,
        )
        self.assertIn(
            "- ✚ **doc-autofix** `docs/system-design.md`"
            " · stale-reference · (claude)\n",
            out,
        )
        # Grade: kind + verdict as one bold unit; facet verdicts bold.
        self.assertIn("- ◆ **grade CLEAR** · Small, well-tested limiter.\n", out)
        self.assertIn("  - blast_radius — **clear** — one package\n", out)
        self.assertIn(
            "  - scope_deviation — **concern** — persistence escalated\n", out
        )
        # Unknown kinds get no anchor: the fallback row stays fully plain.
        self.assertIn("- • mystery-record (someone-new)\n", out)
        self.assertNotIn("├", out)
        self.assertNotIn("└", out)

    def test_fix_anchor_bolds_kind_and_fixer(self):
        # A doc-owner fix dispatch: kind + fixer one bold unit, source plain.
        self.write_log(
            vrec(
                "review-feedback",
                "doc-reviewer",
                "2026-07-06T10:20:00Z",
                verdict="changes_requested",
                findings=[
                    {"tag": "autofix", "location": "prd.md:9", "description": "stale"}
                ],
            ),
            vrec(
                "dispatch-start",
                "product-requirements-expert",
                "2026-07-06T10:32:00Z",
                responding_to=[1],
            ),
        )
        _, out, _ = self.mdview()
        self.assertIn("- ↻ **fix prd-expert** ← doc · (1 finding)\n", out)

    def test_cost_tail_renders_italic_with_bold_highlights(self):
        # The tails are DIM in ANSI overall (italic here), but the elapsed and
        # the $ cost are GREEN there — bold inside the italic, on the steps
        # AND as the header roll-up riding the summary line via a hard break.
        cost_dim = " │ Σ ▲1.2M ▼7k "
        cache_dim = " │ ⛁ 88% $71%"

        def spans():
            return [
                (cost_dim, handoff.DIM),
                ("$2.50", handoff.GREEN),
                (cache_dim, handoff.DIM),
            ]

        def lookup(agent_type, start_rec, end_rec):
            return spans()

        lookup.slice_lookup = lambda agent_types, s, e: spans()
        self.write_log(*timed_fixture())
        entries, errors = handoff.parse_log(str(self.log))
        lines, _ = handoff.render_view_md(
            entries,
            errors,
            REQ,
            list(handoff.ROSTER_FLOOR),
            verbose=False,
            cost_lookup=lookup,
        )
        out = "\n".join(lines)
        self.assertIn("· ***◷ 3m** │ Σ ▲1.2M ▼7k **$2.50** │ ⛁ 88% $71%*", out)
        self.assertIn(
            "- ◆ **implement** (implementer)"
            " · ***◷ 15m** │ Σ ▲1.2M ▼7k **$2.50** │ ⛁ 88% $71%*",
            out,
        )
        self.assertIn(
            "grade **CLEAR**  \n***◷ 26m** │ Σ ▲1.2M ▼7k **$2.50** │ ⛁ 88% $71%*", out
        )

    def test_abort_closed_session_carries_its_tail(self):
        # The shared grouping closes a session on an aborting build-failure, so
        # the Markdown parent carries the opener → abort elapsed and cost too;
        # a plain retry failure closes nothing and its parent stays bare.
        cost = [
            (" │ Σ ▲7.5M ▼17k ", handoff.DIM),
            ("$4.66", handoff.GREEN),
            (" │ ⛁ 99% $89%", handoff.DIM),
        ]
        self.write_log(
            vrec("dispatch-start", "feature-implementer", "2026-07-06T10:06:00Z"),
            vrec(
                "build-failure",
                "feature-implementer",
                "2026-07-06T10:11:00Z",
                abort_reason="design-mismatch",
            ),
        )
        entries, errors = handoff.parse_log(str(self.log))
        lines, _ = handoff.render_view_md(
            entries,
            errors,
            REQ,
            list(handoff.ROSTER_FLOOR),
            verbose=False,
            cost_lookup=lambda at, s, e: cost,
        )
        self.assertIn(
            "- ◆ **implement** (implementer)"
            " · ***◷ 5m** │ Σ ▲7.5M ▼17k **$4.66** │ ⛁ 99% $89%*",
            "\n".join(lines),
        )

        self.write_log(
            vrec("dispatch-start", "feature-implementer", "2026-07-06T10:06:00Z"),
            vrec(
                "build-failure", "feature-implementer", "2026-07-06T10:11:00Z", retry=1
            ),
        )
        entries, errors = handoff.parse_log(str(self.log))
        lines, _ = handoff.render_view_md(
            entries,
            errors,
            REQ,
            list(handoff.ROSTER_FLOOR),
            verbose=False,
            cost_lookup=lambda at, s, e: cost,
        )
        self.assertIn("- ◆ **implement** (implementer)\n", "\n".join(lines) + "\n")

    def test_record_text_is_escaped(self):
        # A `|` in a table cell, a backtick in a code span, raw HTML, and a
        # structure-forming leading character must all stay inert.
        self.write_log(
            rec("prd-entry", title="# fake heading"),
            rec(
                "review-feedback",
                author="weird|name-reviewer",
                verdict="changes_requested",
                findings=[
                    {
                        "tag": "blocked",
                        "location": "a`b.py:7",
                        "description": "uses <script> here",
                    }
                ],
            ),
        )
        code, out, err = self.mdview()
        self.assertEqual(code, 0, err)
        self.assertIn("— \\# fake heading", out)
        self.assertIn("| **weird\\|name** | ✎ (1) |", out)
        self.assertIn("`aʼb.py:7`", out)
        self.assertIn("uses \\<script> here", out)

    def test_markdown_and_color_are_mutually_exclusive(self):
        self.write_log(rec("prd-entry", title="t"))
        for flag in ("--color", "--no-color"):
            code, _, err = self.run_cli(
                "view", "--file", str(self.log), "--markdown", flag
            )
            self.assertEqual(code, 2)
            self.assertIn("not allowed with", err)

    def test_unknown_req_id_exits_three(self):
        self.write_log(rec("prd-entry", title="T"))
        code, out, _ = self.mdview("--req-id", "REQ-NOPE-999")
        self.assertEqual(code, 3)
        self.assertIn("no records for REQ-NOPE-999", out)
        self.assertIn("in log: REQ-A-001", out)

    def test_slices_separate_with_a_rule(self):
        self.write_log(
            rec("prd-entry", title="Original"),
            rec(
                "prd-entry",
                req_id="REQ-B-002",
                title="Refactor sibling",
                author="system-design-expert",
            ),
        )
        _, out, _ = self.mdview()
        self.assertIn("### REQ-A-001 — Original", out)
        self.assertIn("### REQ-B-002 — Refactor sibling", out)
        self.assertIn("\n\n---\n\n", out)
        self.assertLess(out.index("REQ-A-001"), out.index("REQ-B-002"))

    def test_dirty_log_lists_problems_as_plain_lines(self):
        self.log.write_text(json.dumps(rec("prd-entry", title="T")) + "\nnot json\n")
        code, out, _ = self.mdview()
        self.assertEqual(code, 0)
        self.assertIn("! 1 problem line skipped:", out)
        self.assertIn("- line 2:", out)

    def test_control_bytes_never_reach_the_document(self):
        hostile = "Innocent\x1b]0;pwned\x07\x1b[8m hidden\x00\ttail"
        self.write_log(
            rec("prd-entry", title=hostile),
            rec(
                "review-feedback",
                author="evil\x1b[2Jer-reviewer",
                verdict="changes_requested",
                findings=[
                    {
                        "tag": "autofix",
                        "location": hostile,
                        "description": hostile,
                        "fix": hostile,
                    }
                ],
            ),
        )
        for flags in ((), ("--verbose",)):
            code, out, _ = self.mdview(*flags)
            self.assertEqual(code, 0)
            self.assertNotIn("\x1b", out)
            self.assertNotIn("\x00", out)
            self.assertIn("Innocent", out)


class TestBoardCost(HandoffCase):
    """The per-step cost overlay on the timeline. The render-level tests inject
    a cost_lookup directly (render_view stays pure); the end-to-end test drives
    cmd_view against a synthetic Claude Code projects tree so the whole wiring
    — slug derivation, window match, tail formatting — is exercised once."""

    COST = " │ Σ ▲1.2M ▼7k $2.50 │ ⛁ 88% $71%"

    def _render(self, records, cost_lookup):
        self.write_log(*records)
        entries, errors = handoff.parse_log(str(self.log))
        lines, _ = handoff.render_view(
            entries,
            errors,
            REQ,
            list(handoff.ROSTER_FLOOR),
            color=False,
            verbose=False,
            cost_lookup=cost_lookup,
        )
        return "\n".join(lines)

    def test_cost_tail_rides_every_timed_step(self):
        out = self._render(timed_fixture(), lambda at, s, e: [(self.COST, handoff.DIM)])
        # prd, design, the implement session, review — four timed steps (the
        # grade is untimed by contract, so no tail can ride it).
        self.assertEqual(out.count(self.COST.strip()), 4)
        # Glued right after the ◷ duration marker.
        self.assertIn("◆ implement  (implementer)  ◷ 15m" + self.COST, out)
        self.assertIn("(prd-expert)  ◷ 3m" + self.COST, out)

    def test_no_lookup_renders_no_cost(self):
        out = self._render(timed_fixture(), None)
        self.assertNotIn("$2.50", out)
        self.assertNotIn("⛁", out)
        self.assertIn("◷ 15m", out)  # duration still renders

    def test_lookup_returning_none_omits_cost(self):
        # Off Claude Code, or an ambiguous window: durations show, cost does not
        # — the same degradation as a missing bounding timestamp.
        out = self._render(timed_fixture(), lambda at, s, e: None)
        self.assertNotIn("⛁", out)
        self.assertIn("◷ 3m", out)

    def test_cost_only_on_dispatched_steps(self):
        # view_fixture's prd/design/reviews carry no dispatch-start, so no
        # duration and no cost; only the two implement sessions are timed.
        out = self._render(view_fixture(), lambda at, s, e: [(self.COST, handoff.DIM)])
        self.assertEqual(out.count(self.COST.strip()), 2)

    def test_cost_on_parent_not_build_children(self):
        out = self._render(
            [
                vrec(
                    "dispatch-start",
                    "feature-implementer",
                    "2026-07-06T10:00:00Z",
                    responding_to=[0],
                ),
                vrec(
                    "build-failure",
                    "feature-implementer",
                    "2026-07-06T10:02:00Z",
                    retry=1,
                    failed_check="test",
                ),
                vrec(
                    "build-pass",
                    "feature-implementer",
                    "2026-07-06T10:05:00Z",
                    gate_checks_run=["test"],
                ),
            ],
            lambda at, s, e: [(self.COST, handoff.DIM)],
        )
        self.assertEqual(out.count(self.COST.strip()), 1)  # the parent only
        for line in out.splitlines():
            if "▲ build" in line:
                self.assertNotIn(self.COST.strip(), line)

    def _synthetic_project(self, usage_dict):
        """A synthetic ~/.claude/projects tree keyed on this process's own cwd
        slug — derived via the module's slug_for so the test tracks Claude
        Code's real encoding — holding one implementer message at 10:10."""
        slug = handoff.accounting.slug_for(os.getcwd())
        sub = self.log.parent / "projects" / slug / "sess1" / "subagents"
        sub.mkdir(parents=True)
        msg = {
            "type": "assistant",
            "timestamp": "2026-07-06T10:10:00Z",
            "message": {"model": "claude-opus-4-8", "usage": usage_dict},
        }
        (sub / "agent-x.jsonl").write_text(json.dumps(msg) + "\n")
        (sub / "agent-x.meta.json").write_text(
            json.dumps({"agentType": "feature-implementer"})
        )

    def _view_with_projects(self):
        with unittest.mock.patch.dict(
            os.environ, {"CLAUDE_PROJECTS_ROOT": str(self.log.parent / "projects")}
        ):
            self.write_log(
                vrec(
                    "dispatch-start",
                    "feature-implementer",
                    "2026-07-06T10:05:00Z",
                    responding_to=[0],
                ),
                vrec(
                    "build-pass",
                    "feature-implementer",
                    "2026-07-06T10:20:00Z",
                    gate_checks_run=["test"],
                ),
            )
            return self.run_cli(
                "view",
                "--file",
                str(self.log),
                "--no-color",
                "--layout",
                str(self.log.parent / "layout.toml"),
            )

    def test_end_to_end_cost_from_synthetic_transcripts(self):
        # Drive cmd_view against a synthetic projects tree so the whole wiring
        # — slug derivation, window match, tail formatting — is exercised once.
        self._synthetic_project(
            {"input_tokens": 1000, "output_tokens": 500, "cache_read_input_tokens": 0}
        )
        code, out, err = self._view_with_projects()
        self.assertEqual(code, 0, err)
        # opus (1000*5 + 500*25)/1e6 = 0.0175 -> $0.02; total_input 1000 -> 1k.
        self.assertIn("◷ 15m │ Σ ▲1k ▼500 $0.02 │ ⛁ 0%", out)

    def test_header_shows_whole_slice_roll_up(self):
        # The header's third line aggregates the slice's own authors over the
        # first→last record window. A foreign agent type active in the same
        # window (here: Explore, never a record author) must not pollute it —
        # the figure stays ▲1k, not ▲78k.
        self._synthetic_project(
            {"input_tokens": 1000, "output_tokens": 500, "cache_read_input_tokens": 0}
        )
        slug = handoff.accounting.slug_for(os.getcwd())
        sub = self.log.parent / "projects" / slug / "sess1" / "subagents"
        msg = {
            "type": "assistant",
            "timestamp": "2026-07-06T10:11:00Z",
            "message": {"model": "claude-opus-4-8", "usage": {"input_tokens": 77000}},
        }
        (sub / "agent-y.jsonl").write_text(json.dumps(msg) + "\n")
        (sub / "agent-y.meta.json").write_text(json.dumps({"agentType": "Explore"}))
        code, out, err = self._view_with_projects()
        self.assertEqual(code, 0, err)
        self.assertIn("│ ◷ 15m │ Σ ▲1k ▼500 $0.02 │ ⛁ 0%", out)

    def test_malformed_usage_degrades_never_crashes(self):
        # A transcript message whose usage carries a non-numeric count must
        # drop into the degraded figures, never traceback the render — the
        # board reads, it never gates, and the transcripts are host data the
        # project does not control.
        self._synthetic_project({"input_tokens": "1200", "output_tokens": 500})
        code, out, err = self._view_with_projects()
        self.assertEqual(code, 0, err)
        self.assertNotIn("Traceback", err)
        self.assertIn("◷ 15m", out)  # the duration still renders


if __name__ == "__main__":
    unittest.main(verbosity=2)
