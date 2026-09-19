#!/usr/bin/env python3
"""The two views over the board: the terminal lines and their Markdown twin."""

import re
import unittest

from handoff import (
    FACET_WIDTH,
    IMPLEMENTER,
    NO_RECORDS_EXIT,
    ROSTER_FLOOR,
    ROUTINE_IMPLEMENTER,
    BoardOptions,
    render_view,
    render_view_md,
)

from tests.support import (
    SOME_COST_TEXT,
    SOME_REQ_ID,
    SOME_TS,
    FakeCostLookup,
    a_slice_record,
    entries,
    timed_fixture,
    view_fixture,
    vrec,
)

ANSI = re.compile(r"\x1b\[[0-9;]*m")
A_LONG_TITLE = (
    "Owner search: a page before the first lists the first page rather "
    "than failing outright"
)
TEXT_WITH_CONTROL_BYTES = "Innocent\x1b]0;title\x07\x1b[8m hidden\x00\ttail"
A_GRADE = {
    "type": "grader-verdict",
    "req_id": "REQ-A-001",
    "ts": SOME_TS,
    "author": "change-grader",
    "verdict": "scrutinize",
    "summary": "clamp the page parameter",
    "facets": {
        "reviewer_hedging": {
            "verdict": "scrutinize",
            "note": (
                "The security reviewer's approval carries an unresolved "
                "clarify naming the identical defect in a sibling controller."
            ),
        }
    },
    "rationale": (
        "The fix itself is tight. What stays open is a scope question "
        "nobody answered; decide before merging."
    ),
}
A_DIRTY_LINE = "line 2: invalid JSON (Expecting value)"
A_TERMINAL_WIDTH = 80
A_NON_STRING = 7
A_DANGLING_NO = 99
TIMED_STEPS_IN_FIXTURE = 4
DISPATCH_MINUTE = 6
CLEAN_BUILD_MINUTE = 10
ABORT_MINUTE = 11
DESIGNER = "system-design-expert"
PRODUCT = "product-requirements-expert"


def at(minute):
    return f"2026-07-06T10:{minute:02d}:00Z"


def duration(start_minute, end_minute):
    return f"◷ {end_minute - start_minute}m"


def text_view(*raws, errors=(), **options):
    lines, _ = render_view(
        entries(*raws),
        list(errors),
        BoardOptions(**{"roster": ROSTER_FLOOR, **options}),
    )
    return "\n".join(lines) + "\n"


def text_view_with_code(*raws, **options):
    lines, code = render_view(
        entries(*raws), [], BoardOptions(**{"roster": ROSTER_FLOOR, **options})
    )
    return "\n".join(lines) + "\n", code


def markdown_view(*raws, errors=(), **options):
    lines, _ = render_view_md(
        entries(*raws),
        list(errors),
        BoardOptions(**{"roster": ROSTER_FLOOR, **options}),
    )
    return "\n".join(lines) + "\n"


def a_design(ts=None):
    return vrec("design-block", DESIGNER, ts or at(0), verdict="covered")


def a_dispatch(author, ts, responding_to=(0,)):
    return vrec("dispatch-start", author, ts, responding_to=list(responding_to))


def a_pass(ts):
    return vrec("build-pass", IMPLEMENTER, ts, gate_checks_run=["test"])


def a_dissent(author, ts, tag="autofix", location="prd.md:9"):
    return vrec(
        "review-feedback",
        author,
        ts,
        verdict="changes_requested",
        findings=[{"tag": tag, "location": location, "description": "stale"}],
    )


def a_session_with_response(pointer):
    return (
        a_slice_record("dispatch-start", author=IMPLEMENTER),
        a_slice_record(
            "consultation-request", author=IMPLEMENTER, target=DESIGNER, question="q"
        ),
        a_slice_record(
            "consultation-response", author=DESIGNER, in_response_to=pointer, answer="a"
        ),
        a_slice_record("build-pass", author=IMPLEMENTER),
    )


def a_fix_round():
    return (
        a_design(),
        a_dispatch(IMPLEMENTER, at(5), (1,)),
        a_pass(at(10)),
        a_dissent("code-quality-reviewer", at(20), "blocked", "limiter.py:42"),
        a_dissent("doc-reviewer", at(21)),
        a_dispatch("security-reviewer", at(30), (3,)),
        a_dispatch(IMPLEMENTER, at(31), (4,)),
        a_dispatch(PRODUCT, at(32), (5,)),
        a_pass(at(40)),
    )


def a_log_with_control_bytes():
    return (
        a_slice_record("prd-entry", title=TEXT_WITH_CONTROL_BYTES),
        a_slice_record("build-pass", gate_checks_run=[TEXT_WITH_CONTROL_BYTES]),
        a_slice_record(
            "review-feedback",
            author="doc\x1b[2J-reviewer",
            verdict="changes_requested",
            findings=[
                {
                    "tag": "autofix",
                    "location": TEXT_WITH_CONTROL_BYTES,
                    "description": TEXT_WITH_CONTROL_BYTES,
                    "fix": TEXT_WITH_CONTROL_BYTES,
                }
            ],
        ),
    )


def two_slices():
    return (
        a_slice_record("prd-entry", title="Original"),
        a_slice_record(
            "prd-entry", req_id="REQ-B-002", title="Refactor sibling", author=DESIGNER
        ),
    )


class TerminalTimeline(unittest.TestCase):
    def test_an_intake_decision_renders_its_own_line(self):
        out = text_view(
            a_slice_record(
                "intake-decision",
                author="human",
                request="add visit editing \x1b[31mplain\x1b[0m",
                decisions=["NG-5 is narrowed"],
            )
        )

        self.assertIn(
            "◇ intake  add visit editing [31mplain[0m  (1 decision)  (human)", out
        )
        self.assertNotIn("\x1b", out)

    def test_records_render_in_append_order_not_timestamp_order(self):
        out = text_view(*view_fixture())

        self.assertLess(out.index("◇ prd-entry"), out.index("◈ design-block"))

    def test_rounds_group_by_reviewer_reappearance(self):
        out = text_view(*view_fixture())

        self.assertIn("R1     R2     R3", out)
        self.assertIn("code-quality  ✎ (2)  ✎ (1)  ✔", out)
        self.assertIn("security      ✔ (1)  ·      ·", out)

    def test_dispatch_starts_and_grader_features_never_render(self):
        out = text_view(*view_fixture())

        self.assertNotIn("dispatch-start", out)
        self.assertNotIn("grader-features", out)

    def test_an_implementer_fix_opens_a_session_and_a_doc_fix_stays_flat(self):
        out = text_view(*a_fix_round())

        self.assertIn("↻ implement  (implementer)  ← code-quality", out)
        self.assertIn("↻ fix  prd-expert  ← doc  (1 finding)\n", out)
        self.assertGreater(
            out.index("↻ fix  prd-expert"),
            out.index("↻ implement  (implementer)  ← code-quality"),
        )
        self.assertEqual(out.count("↻ fix"), 1)
        self.assertEqual(out.count("◆ implement"), 1)

    def test_a_fresh_implement_session_ends_in_its_clean_build(self):
        out = text_view(
            a_design(at(DISPATCH_MINUTE - 1)),
            a_dispatch(IMPLEMENTER, at(DISPATCH_MINUTE), (1,)),
            a_pass(at(CLEAN_BUILD_MINUTE)),
        )
        session_time = duration(DISPATCH_MINUTE, CLEAN_BUILD_MINUTE)

        self.assertIn(f"◆ implement  (implementer)  {session_time}", out)
        self.assertIn("  └ ▲ build  ✓ clean", out)
        self.assertEqual(out.count("◆ implement"), 1)
        self.assertGreater(out.index("└ ▲ build"), out.index("◆ implement"))
        self.assertGreater(out.index("◆ implement"), out.index("design-block"))

    def test_a_retry_nests_under_one_implement_session(self):
        out = text_view(
            a_design(at(DISPATCH_MINUTE - 1)),
            a_dispatch(IMPLEMENTER, at(DISPATCH_MINUTE), (1,)),
            vrec(
                "build-failure",
                IMPLEMENTER,
                at(DISPATCH_MINUTE + 1),
                retry=1,
                failed_check="test",
            ),
            a_dispatch(IMPLEMENTER, at(DISPATCH_MINUTE + 2), (3,)),
            a_pass(at(CLEAN_BUILD_MINUTE)),
        )
        session_time = duration(DISPATCH_MINUTE, CLEAN_BUILD_MINUTE)

        self.assertEqual(out.count("◆ implement"), 1)
        self.assertIn(f"◆ implement  (implementer)  {session_time}", out)
        self.assertIn("  ├ ▲ build  ✗ test failed  retry 1", out)
        self.assertIn("  └ ▲ build  ✓ clean", out)

    def test_an_abort_closes_the_session_with_its_duration_and_cost(self):
        out = text_view(
            a_design(),
            a_dispatch(IMPLEMENTER, at(DISPATCH_MINUTE), (1,)),
            vrec(
                "build-failure",
                IMPLEMENTER,
                at(ABORT_MINUTE),
                abort_reason="design-mismatch",
            ),
            vrec(
                "consultation-request",
                IMPLEMENTER,
                at(ABORT_MINUTE + 1),
                target=DESIGNER,
                question="Re-triage?",
            ),
            req_id=SOME_REQ_ID,
            cost_lookup=FakeCostLookup(),
        )
        session_time = duration(DISPATCH_MINUTE, ABORT_MINUTE)

        self.assertIn(
            f"◆ implement  (implementer)  {session_time}{SOME_COST_TEXT}", out
        )
        self.assertIn("  └ ▲ build  ✗ aborted: design-mismatch", out)
        self.assertIn("↳ consult  implementer → design", out)
        self.assertNotIn("└ ↳ consult", out)

    def test_an_open_session_stays_untimed(self):
        out = text_view(
            a_design(),
            a_dispatch(IMPLEMENTER, at(DISPATCH_MINUTE), (1,)),
            vrec(
                "build-failure",
                IMPLEMENTER,
                at(ABORT_MINUTE),
                retry=1,
                failed_check="test",
            ),
        )

        self.assertIn("◆ implement  (implementer)\n", out)
        self.assertNotIn("(implementer)  ◷", out)

    def test_record_producing_steps_show_their_duration_and_the_grade_stays_untimed(
        self,
    ):
        out = text_view(*timed_fixture())

        self.assertIn("(prd-expert)  ◷ 3m", out)
        self.assertIn("(design)  ◷ 2m", out)
        self.assertIn("◆ implement  (implementer)  ◷ 15m", out)
        self.assertIn("review  code-quality  approved  ◷ 2m", out)
        self.assertIn("◆ grade  SKIM  done", out)
        self.assertNotIn("done  ◷", out)

    def test_a_doc_fix_carries_no_duration(self):
        out = text_view(
            a_design(),
            a_dispatch(IMPLEMENTER, at(0), (1,)),
            a_pass(at(5)),
            a_dissent("doc-reviewer", at(10)),
            a_dispatch(PRODUCT, at(11), (4,)),
            vrec(
                "review-feedback",
                "doc-reviewer",
                at(25),
                verdict="approved",
                findings=[],
            ),
        )

        self.assertIn("↻ fix  prd-expert  ← doc  (1 finding)\n", out)

    def test_a_sibling_consult_renders_flat_with_its_own_author(self):
        out = text_view(
            a_design(),
            a_dissent("doc-reviewer", at(20)),
            a_dispatch(IMPLEMENTER, at(31), (2,)),
            a_dispatch(PRODUCT, at(32), (2,)),
            vrec(
                "consultation-request",
                PRODUCT,
                at(33),
                target=DESIGNER,
                question="Fixed burst size?",
            ),
            a_pass(at(40)),
        )

        self.assertIn("↳ consult  prd-expert → design", out)
        self.assertNotIn("├ ↳ consult", out)
        self.assertIn("↻ fix  prd-expert  ← doc", out)

    def test_an_autofix_inside_a_session_hoists_below_it(self):
        out = text_view(
            a_design(),
            a_dispatch(IMPLEMENTER, at(DISPATCH_MINUTE), (1,)),
            vrec(
                "prd-autofix",
                "claude",
                at(DISPATCH_MINUTE + 1),
                file="docs/prd.md",
                category="writing-standards",
            ),
            a_pass(at(CLEAN_BUILD_MINUTE)),
        )
        session_time = duration(DISPATCH_MINUTE, CLEAN_BUILD_MINUTE)

        self.assertIn(f"◆ implement  (implementer)  {session_time}", out)
        self.assertIn("  └ ▲ build  ✓ clean", out)
        self.assertIn("✚ prd-autofix  docs/prd.md  writing-standards  (claude)", out)
        self.assertNotIn("── ▲ build-pass", out)

    def test_a_re_engaged_review_carries_no_duration(self):
        out = text_view(
            a_dispatch("code-quality-reviewer", at(DISPATCH_MINUTE)),
            a_dissent("code-quality-reviewer", at(ABORT_MINUTE), "blocked", "a.py:1"),
            vrec(
                "review-feedback",
                "code-quality-reviewer",
                at(CLEAN_BUILD_MINUTE + 25),
                verdict="approved",
                findings=[],
            ),
        )
        review_time = duration(DISPATCH_MINUTE, ABORT_MINUTE)

        self.assertIn(f"changes_requested  (1 finding)  {review_time}", out)
        self.assertNotIn("approved  ◷", out)

    def test_consecutive_gates_are_told_apart_by_their_clock_face(self):
        out = text_view(
            a_slice_record("prd-entry", title="t"),
            a_slice_record(
                "build-pass", ts="2026-07-06T13:32:00Z", gate_checks_run=["test"]
            ),
            a_slice_record(
                "build-pass", ts="2026-07-06T14:10:00Z", gate_checks_run=["test"]
            ),
        )

        self.assertIn("▲ build-pass 13:32", out)
        self.assertIn("▲ build-pass 14:10", out)

    def test_supersedes_abort_dangling_response_and_blocked_verdict_render(self):
        out = text_view(
            a_slice_record(
                "design-block", author=DESIGNER, verdict="minor", supersedes_record_at=1
            ),
            a_slice_record(
                "build-failure", author=IMPLEMENTER, abort_reason="design-mismatch"
            ),
            a_slice_record(
                "consultation-response",
                author=DESIGNER,
                in_response_to=A_DANGLING_NO,
                answer="a",
            ),
            a_slice_record(
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

        self.assertIn("supersedes L1", out)
        self.assertIn("abort: design-mismatch", out)
        self.assertIn("design → ?", out)
        self.assertIn("✖", out)

    def test_missing_fields_and_unknown_types_still_render(self):
        out = text_view(
            a_slice_record(
                "review-feedback",
                author="code-quality-reviewer",
                verdict="changes_requested",
                findings=["not-a-dict", {"location": A_NON_STRING}],
            ),
            a_slice_record(
                "review-feedback",
                author="test-reviewer",
                verdict=["approved"],
                findings=[],
            ),
            a_slice_record(
                "review-feedback",
                author="doc-reviewer",
                verdict={"v": "approved"},
                findings=[],
            ),
            a_slice_record(
                "grader-verdict",
                author="change-grader",
                facets={"blast_radius": "not-a-dict"},
            ),
            {"type": "prd-entry", "req_id": "REQ-A-001", "ts": SOME_TS},
            {"type": None, "req_id": "REQ-A-001"},
        )

        self.assertIn("(untitled)", out)
        self.assertIn("blast_radius", out)
        self.assertEqual(out.count("review  "), 3)

    def test_a_consult_response_with_a_list_pointer_inside_a_session_renders(self):
        out = text_view(*a_session_with_response([2]))

        self.assertIn("◆ implement", out)
        self.assertIn("↲ consult", out)

    def test_a_float_line_pointer_nests_the_implementers_consult_response(self):
        out = text_view(*a_session_with_response(2.0))

        self.assertIn("↲ consult  ← design", out)
        self.assertNotIn("↲ consult  design →", out)

    def test_a_completed_pass_with_scalar_findings_renders_the_ladder(self):
        out = text_view(
            a_slice_record("build-pass", author=IMPLEMENTER),
            a_slice_record(
                "review-feedback",
                author="code-quality-reviewer",
                verdict="changes_requested",
                findings=A_NON_STRING,
            ),
            a_slice_record("build-pass", author=IMPLEMENTER),
        )

        self.assertEqual(out.count("build-pass"), 3)

    def test_records_without_a_req_id_render_under_the_unnamed_header(self):
        out = text_view(
            {"type": "prd-entry", "ts": SOME_TS, "author": "tester", "title": "T"}
        )

        self.assertIn("(no req_id)", out)
        self.assertIn("T", out)


class TerminalHeaderAndGrade(unittest.TestCase):
    def test_no_grader_verdict_renders_no_grade_yet(self):
        self.assertIn(
            "no grade yet",
            text_view(
                a_slice_record("prd-entry", title="t"), a_slice_record("build-pass")
            ),
        )

    def test_grading_off_renders_grading_disabled(self):
        out = text_view(
            a_slice_record("prd-entry", title="t"),
            a_slice_record("build-pass"),
            auto_grade=False,
        )

        self.assertIn("grading disabled", out)
        self.assertNotIn("no grade yet", out)

    def test_an_older_ledger_renders_the_current_grade_words(self):
        older = dict(
            A_GRADE,
            verdict="con" + "cern",
            facets={"reviewer_hedging": {"verdict": "cl" + "ear", "note": "n"}},
        )

        out = text_view(older)

        self.assertIn("grade  SCRUTINIZE", out)
        self.assertIn("reviewer_hedging  skim", out)
        self.assertNotIn("CONCERN", out)

    def test_a_stray_facet_verdict_is_sanitized_and_clipped(self):
        stray = dict(
            A_GRADE,
            facets={
                "reviewer_hedging": {
                    "verdict": "x" * (FACET_WIDTH + 1) + "\x1b[31m",
                    "note": "n",
                }
            },
        )

        out = text_view(stray)

        self.assertNotIn("\x1b", out)
        self.assertIn("reviewer_hedging  " + "x" * FACET_WIDTH + "  n", out)

    def test_verbose_prints_the_whole_facet_note_and_the_rationale(self):
        out = text_view(A_GRADE, verbose=True)

        self.assertIn("naming the identical defect in a sibling controller.", out)
        self.assertIn("why: The fix itself is tight.", out)

    def test_the_default_board_gists_the_note_and_omits_the_rationale(self):
        out = text_view(A_GRADE)

        self.assertNotIn("naming the identical defect", out)
        self.assertNotIn("why:", out)

    def test_a_grade_without_a_rationale_renders_no_why_line(self):
        out = text_view(
            {k: v for k, v in A_GRADE.items() if k != "rationale"}, verbose=True
        )

        self.assertIn("reviewer_hedging", out)
        self.assertNotIn("why:", out)

    def test_verbose_prints_the_full_description_then_the_fix(self):
        out = text_view(*view_fixture(), verbose=True)

        self.assertLess(
            out.index("observe a single remaining token and pass."),
            out.index("fix: Hold the lock across the refill and the take."),
        )

    def test_verbose_prints_a_consultation_question_whole(self):
        question = (
            "Does the vets listing belong in this slice, or does it become a "
            "follow-up requirement of its own?"
        )
        request = a_slice_record(
            "consultation-request",
            author="security-reviewer",
            target=PRODUCT,
            question=question,
        )

        self.assertIn(
            "follow-up requirement of its own", text_view(request, verbose=True)
        )
        self.assertNotIn("follow-up requirement of its own", text_view(request))

    def test_verbose_prints_a_prd_entry_title_whole(self):
        out = text_view(a_slice_record("prd-entry", title=A_LONG_TITLE), verbose=True)

        self.assertIn("rather than failing outright", out)

    def test_the_header_box_keeps_its_title_bounded(self):
        out = text_view(a_slice_record("prd-entry", title=A_LONG_TITLE), verbose=True)

        self.assertIn("…", out.splitlines()[1])
        self.assertLessEqual(
            max(len(line) for line in out.splitlines()[:3]), A_TERMINAL_WIDTH
        )

    def test_an_extra_roster_reviewer_gets_an_idle_lane(self):
        out = text_view(
            a_slice_record(
                "review-feedback",
                author="code-quality-reviewer",
                verdict="approved",
                findings=[],
            ),
            roster=[*ROSTER_FLOOR, "perf-reviewer"],
        )

        perf_lane = [line for line in out.splitlines() if line.startswith("perf")]
        self.assertEqual(len(perf_lane), 1, out)
        self.assertIn("·", perf_lane[0])
        self.assertNotIn("✔", perf_lane[0])


class SliceSelection(unittest.TestCase):
    def test_no_req_id_renders_every_slice_oldest_first_with_its_own_box(self):
        out = text_view(*two_slices())

        self.assertLess(out.index("REQ-A-001"), out.index("REQ-B-002"))
        self.assertIn("Refactor sibling", out)
        self.assertNotIn("also in log", out)
        self.assertEqual(out.count("╭"), 2)

    def test_a_req_id_selects_one_slice_and_names_the_others(self):
        out = text_view(*two_slices(), req_id="REQ-A-001")

        self.assertIn("Original", out)
        self.assertNotIn("Refactor sibling", out)
        self.assertIn("also in log: REQ-B-002", out)

    def test_an_unknown_req_id_exits_three_and_lists_the_log(self):
        out, code = text_view_with_code(
            a_slice_record("prd-entry", title="T"), req_id="REQ-NOPE-999"
        )

        self.assertEqual(code, NO_RECORDS_EXIT)
        self.assertIn("no records for REQ-NOPE-999", out)
        self.assertIn("in log: REQ-A-001", out)

    def test_a_req_id_against_an_empty_log_exits_three(self):
        out, code = text_view_with_code(req_id="REQ-NOPE-999")

        self.assertEqual(code, NO_RECORDS_EXIT)
        self.assertIn("no records for REQ-NOPE-999", out)

    def test_an_empty_log_renders_its_message(self):
        self.assertIn("handoff log is empty", text_view())

    def test_a_dirty_log_renders_parsed_records_with_a_footer(self):
        out = text_view(a_slice_record("prd-entry", title="T"), errors=[A_DIRTY_LINE])

        self.assertIn("prd-entry", out)
        self.assertIn("! 1 problem line skipped:", out)
        self.assertIn("  " + A_DIRTY_LINE, out)


class TerminalAlignment(unittest.TestCase):
    def test_the_header_box_lines_share_one_width(self):
        out = text_view(*view_fixture())

        box = [line for line in out.splitlines() if line and line[0] in "╭│╰"]
        self.assertEqual({len(line) for line in box}, {len(box[0])})

    def test_idle_matrix_lanes_are_padded_to_the_round_columns(self):
        out = text_view(*view_fixture())

        lanes = [line for line in out.splitlines() if line.startswith(("test", "doc"))]
        self.assertEqual(
            lanes, ["test          ·      ·      ·", "doc           ·      ·      ·"]
        )

    def test_a_long_description_is_clipped_with_an_ellipsis(self):
        out = text_view(*view_fixture())

        self.assertIn("two workers can both observe a singl…", out)

    def test_a_bool_line_pointer_resolves_no_requester(self):
        out = text_view(
            a_slice_record(
                "consultation-request",
                author=IMPLEMENTER,
                target=DESIGNER,
                question="q",
            ),
            a_slice_record(
                "consultation-response",
                author=DESIGNER,
                in_response_to=True,
                answer="a",
            ),
        )

        self.assertIn("↲ consult  design → ?", out)


class TerminalSafety(unittest.TestCase):
    def test_control_bytes_in_log_content_never_reach_the_terminal(self):
        for verbose in (False, True):
            out = text_view(*a_log_with_control_bytes(), verbose=verbose)

            self.assertNotIn("\x1b", out)
            self.assertNotIn("\x00", out)
            self.assertIn("Innocent", out)

    def test_a_req_id_with_escape_sequences_renders_stripped_in_the_in_log_line(self):
        req_id_with_escapes = "\x1b]0;title\x07\x1b[2Jgood"
        out, code = text_view_with_code(
            {
                "type": "prd-entry",
                "req_id": req_id_with_escapes,
                "ts": SOME_TS,
                "author": "tester",
                "title": "x",
            },
            req_id="REQ-MISSING-000",
        )

        self.assertEqual(code, NO_RECORDS_EXIT)
        self.assertNotIn("\x1b", out)
        self.assertIn("in log:", out)

    def test_colored_output_aligns_with_plain(self):
        plain = text_view(*view_fixture(), req_id=SOME_REQ_ID)
        colored = text_view(*view_fixture(), req_id=SOME_REQ_ID, color=True)

        self.assertEqual(ANSI.sub("", colored), plain)
        self.assertIn("\x1b[", colored)


class TerminalCostOverlay(unittest.TestCase):
    def test_the_cost_tail_rides_every_timed_step_and_the_header(self):
        out = text_view(
            *timed_fixture(), req_id=SOME_REQ_ID, cost_lookup=FakeCostLookup()
        )

        self.assertEqual(out.count(SOME_COST_TEXT.strip()), TIMED_STEPS_IN_FIXTURE + 1)
        self.assertIn("◆ implement  (implementer)  ◷ 15m" + SOME_COST_TEXT, out)
        self.assertIn("(prd-expert)  ◷ 3m" + SOME_COST_TEXT, out)
        self.assertIn("│ ◷ 26m" + SOME_COST_TEXT, out)

    def test_no_lookup_renders_durations_without_cost(self):
        out = text_view(*timed_fixture(), req_id=SOME_REQ_ID)

        self.assertNotIn("⛁", out)
        self.assertIn("◷ 15m", out)

    def test_a_lookup_without_figures_omits_the_cost(self):
        out = text_view(
            *timed_fixture(),
            req_id=SOME_REQ_ID,
            cost_lookup=FakeCostLookup(figures=None),
        )

        self.assertNotIn("⛁", out)
        self.assertIn("◷ 3m", out)

    def test_cost_rides_the_session_parent_not_its_build_children(self):
        out = text_view(
            a_dispatch(IMPLEMENTER, at(DISPATCH_MINUTE)),
            vrec(
                "build-failure",
                IMPLEMENTER,
                at(DISPATCH_MINUTE + 1),
                retry=1,
                failed_check="test",
            ),
            a_pass(at(CLEAN_BUILD_MINUTE)),
            req_id=SOME_REQ_ID,
            cost_lookup=FakeCostLookup(),
        )
        session_time = duration(DISPATCH_MINUTE, CLEAN_BUILD_MINUTE)

        build_lines = [line for line in out.splitlines() if "▲ build" in line]
        self.assertTrue(all(SOME_COST_TEXT.strip() not in line for line in build_lines))
        self.assertIn(
            f"◆ implement  (implementer)  {session_time}{SOME_COST_TEXT}", out
        )


class TerminalEffortTier(unittest.TestCase):
    DISPATCH_NO = 2

    def a_slice(self):
        return (
            a_slice_record(
                "design-block", verdict="covered", implementation_effort="routine"
            ),
            a_slice_record("dispatch-start", author=IMPLEMENTER, responding_to=[1]),
            a_slice_record("build-pass"),
        )

    def test_a_routine_window_annotates_the_session_opener(self):
        out = text_view(
            *self.a_slice(), window_tiers={self.DISPATCH_NO: ROUTINE_IMPLEMENTER}
        )

        self.assertIn("(implementer · routine)", out)

    def test_an_unmarked_window_stays_plain(self):
        out = text_view(*self.a_slice())

        self.assertIn("(implementer)", out)
        self.assertNotIn("· routine", out)

    def test_a_tier_mismatch_is_flagged_on_the_opener(self):
        out = text_view(
            *self.a_slice(),
            window_tiers={self.DISPATCH_NO: ROUTINE_IMPLEMENTER},
            cost_lookup=FakeCostLookup(figures=None, tiers=(IMPLEMENTER,)),
        )

        self.assertIn("✗ tier mismatch: ran base", out)

    def test_a_base_prediction_with_a_routine_transcript_is_flagged(self):
        out = text_view(
            *self.a_slice(),
            cost_lookup=FakeCostLookup(figures=None, tiers=(ROUTINE_IMPLEMENTER,)),
        )

        self.assertIn("✗ tier mismatch: ran routine", out)

    def test_an_agreeing_transcript_stays_quiet(self):
        out = text_view(
            *self.a_slice(),
            window_tiers={self.DISPATCH_NO: ROUTINE_IMPLEMENTER},
            cost_lookup=FakeCostLookup(figures=None, tiers=(ROUTINE_IMPLEMENTER,)),
        )

        self.assertNotIn("tier mismatch", out)
        self.assertIn("· routine", out)


class MarkdownBoard(unittest.TestCase):
    def test_the_header_is_an_h3_with_a_selectively_bold_summary(self):
        out = markdown_view(*view_fixture())

        self.assertIn("### REQ-DEMO-001 — Rate-limit the API\n", out)
        self.assertIn(
            "3 review rounds · 2 build-passes · **1 build-failure** · grade **SKIM**\n",
            out,
        )
        self.assertNotIn("**3 review rounds", out)
        self.assertNotIn("╭", out)

    def test_the_grade_line_reads_no_grade_yet_or_grading_disabled(self):
        pending = markdown_view(
            a_slice_record("prd-entry", title="t"), a_slice_record("build-pass")
        )
        disabled = markdown_view(
            a_slice_record("prd-entry", title="t"),
            a_slice_record("build-pass"),
            auto_grade=False,
        )

        self.assertIn("0 review rounds · 1 build-pass · no grade yet\n", pending)
        self.assertIn("- ▲ **build-pass** 10:00\n", pending)
        self.assertIn("· grading disabled\n", disabled)

    def test_an_older_ledger_renders_the_current_grade_words(self):
        older = dict(
            A_GRADE,
            verdict="con" + "cern",
            facets={"reviewer_hedging": {"verdict": "cl" + "ear", "note": "n"}},
        )

        out = markdown_view(older)

        self.assertIn("grade SCRUTINIZE", out)
        self.assertIn("**skim**", out)
        self.assertNotIn("CONCERN", out)

    def test_the_matrix_renders_as_a_table(self):
        out = markdown_view(*view_fixture())

        self.assertIn("| reviewer | R1 | R2 | R3 |\n", out)
        self.assertIn("| --- | --- | --- | --- |\n", out)
        self.assertIn("| **code-quality** | ✎ (2) | ✎ (1) | **✔** |\n", out)
        self.assertIn("| **security** | **✔** (1) | · | · |\n", out)
        self.assertIn("| **test** | · | · | · |\n", out)

    def test_the_timeline_renders_as_bullets_with_nested_children(self):
        out = markdown_view(*view_fixture())

        self.assertIn("- ◇ **prd-entry** Rate-limit the API · (prd-expert)\n", out)
        self.assertIn("- ◈ **design-block** **minor** · (design)\n", out)
        self.assertIn("- ◆ **implement** (implementer) · ***◷ 15m***\n", out)
        self.assertIn("  - ↳ consult → **design** · Per-tenant or per-endpoint?\n", out)
        self.assertIn("  - ↲ consult ← **design** · Per-tenant.\n", out)
        self.assertIn("  - ▲ **build ✗ unit-test failed** · retry 1\n", out)
        self.assertIn("  - ▲ **build ✓ clean** · fmt · test\n", out)
        self.assertIn(
            "- ✎ **review code-quality** · **changes_requested** · (2 findings)\n", out
        )
        self.assertIn("  - **[blocked]** `limiter.py:42` The bucket refill races", out)
        self.assertIn("  - **[escalate]** `limiter.py:88`", out)
        self.assertIn("  - [autofix] `limiter.py:12`", out)
        self.assertIn("  - [clarify] `prd.md:9`", out)
        self.assertIn(
            "- ↻ **implement** (implementer) ← code-quality · (1 finding) · ***◷ 4m***\n",
            out,
        )
        self.assertIn(
            "- ✚ **doc-autofix** `docs/system-design.md` · stale-reference · (claude)\n",
            out,
        )
        self.assertIn("- ◆ **grade SKIM** · Small, well-tested limiter.\n", out)
        self.assertIn("  - blast_radius — **skim** — one package\n", out)
        self.assertIn(
            "  - scope_deviation — **scrutinize** — persistence escalated\n", out
        )
        self.assertIn("- • mystery-record (someone-new)\n", out)
        self.assertNotIn("├", out)
        self.assertNotIn("└", out)

    def test_an_intake_decision_renders_its_own_bullet(self):
        out = markdown_view(
            a_slice_record(
                "intake-decision",
                author="human",
                request="add editing",
                decisions=["NG-5 is narrowed"],
            )
        )

        self.assertIn("- ◇ **intake** add editing · (1 decision) · (human)\n", out)

    def test_a_prd_autofix_row_renders_like_its_design_twin(self):
        out = markdown_view(
            vrec(
                "prd-autofix",
                "claude",
                at(8),
                file="docs/prd.md",
                category="writing-standards",
            )
        )

        self.assertIn(
            "- ✚ **prd-autofix** `docs/prd.md` · writing-standards · (claude)\n", out
        )

    def test_a_fix_anchor_bolds_the_kind_and_the_fixer(self):
        out = markdown_view(
            a_dissent("doc-reviewer", at(20)),
            a_dispatch(PRODUCT, at(32), (1,)),
        )

        self.assertIn("- ↻ **fix prd-expert** ← doc · (1 finding)\n", out)

    def test_the_cost_tail_renders_italic_with_bold_highlights(self):
        out = markdown_view(
            *timed_fixture(), req_id=SOME_REQ_ID, cost_lookup=FakeCostLookup()
        )

        self.assertIn("· ***◷ 3m** │ Σ ▲1.2M ▼7k **$2.50** │ ⛁ 88% $71%*", out)
        self.assertIn(
            "- ◆ **implement** (implementer) · ***◷ 15m** │ Σ ▲1.2M ▼7k **$2.50** │ ⛁ 88% $71%*",
            out,
        )
        self.assertIn(
            "grade **SKIM**  \n***◷ 26m** │ Σ ▲1.2M ▼7k **$2.50** │ ⛁ 88% $71%*", out
        )

    def test_an_abort_closed_session_carries_its_tail_and_an_open_one_stays_bare(self):
        closed = markdown_view(
            vrec("dispatch-start", IMPLEMENTER, at(DISPATCH_MINUTE)),
            vrec(
                "build-failure",
                IMPLEMENTER,
                at(ABORT_MINUTE),
                abort_reason="design-mismatch",
            ),
            req_id=SOME_REQ_ID,
            cost_lookup=FakeCostLookup(),
        )
        still_open = markdown_view(
            vrec("dispatch-start", IMPLEMENTER, at(DISPATCH_MINUTE)),
            vrec("build-failure", IMPLEMENTER, at(ABORT_MINUTE), retry=1),
            req_id=SOME_REQ_ID,
            cost_lookup=FakeCostLookup(),
        )
        session_time = duration(DISPATCH_MINUTE, ABORT_MINUTE)

        self.assertIn(
            f"- ◆ **implement** (implementer) · ***{session_time}** │ Σ ▲1.2M ▼7k **$2.50** │ ⛁ 88% $71%*",
            closed,
        )
        self.assertIn("- ◆ **implement** (implementer)\n", still_open)

    def test_record_text_is_escaped(self):
        out = markdown_view(
            a_slice_record("prd-entry", title="# fake heading"),
            a_slice_record(
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

        self.assertIn("— \\# fake heading", out)
        self.assertIn("| **weird\\|name** | ✎ (1) |", out)
        # The renderer swaps a backtick inside a span for the modifier apostrophe.
        self.assertIn("`aʼb.py:7`", out)  # noqa: RUF001
        self.assertIn("uses \\<script> here", out)

    def test_the_header_takes_the_whole_title_under_verbose(self):
        out = markdown_view(
            a_slice_record("prd-entry", title=A_LONG_TITLE), verbose=True
        )

        self.assertIn("### REQ-A-001 — " + A_LONG_TITLE, out)

    def test_verbose_carries_the_facet_note_and_the_rationale(self):
        out = markdown_view(A_GRADE, verbose=True)

        self.assertIn("naming the identical defect in a sibling controller.", out)
        self.assertIn("why — ", out)
        self.assertNotIn("why — ", markdown_view(A_GRADE))

    def test_verbose_omits_the_rationale_when_the_grade_has_no_facets(self):
        out = markdown_view(
            a_slice_record(
                "grader-verdict",
                author="change-grader",
                verdict="skim",
                summary="s",
                rationale="because",
                facets={},
            ),
            verbose=True,
        )

        self.assertIn("grade SKIM", out)
        self.assertNotIn("why —", out)

    def test_a_routine_window_annotates_the_session(self):
        out = markdown_view(
            a_slice_record("dispatch-start", author=IMPLEMENTER, responding_to=[0]),
            a_slice_record("build-pass"),
            window_tiers={1: ROUTINE_IMPLEMENTER},
        )

        self.assertIn("implementer · routine", out)

    def test_slices_separate_with_a_rule(self):
        out = markdown_view(*two_slices())

        self.assertIn("### REQ-A-001 — Original", out)
        self.assertIn("### REQ-B-002 — Refactor sibling", out)
        self.assertIn("\n\n---\n\n", out)

    def test_an_unknown_req_id_exits_three(self):
        lines, code = render_view_md(
            entries(a_slice_record("prd-entry", title="T")),
            [],
            BoardOptions(req_id="REQ-NOPE-999"),
        )

        self.assertEqual(code, NO_RECORDS_EXIT)
        self.assertEqual(
            lines, ["no records for REQ-NOPE-999", "", "in log: REQ-A-001"]
        )

    def test_a_dirty_log_lists_problems_as_plain_lines(self):
        out = markdown_view(
            a_slice_record("prd-entry", title="T"), errors=[A_DIRTY_LINE]
        )

        self.assertIn("! 1 problem line skipped:", out)
        self.assertIn("- " + A_DIRTY_LINE, out)

    def test_control_bytes_never_reach_the_document(self):
        for verbose in (False, True):
            out = markdown_view(*a_log_with_control_bytes(), verbose=verbose)

            self.assertNotIn("\x1b", out)
            self.assertNotIn("\x00", out)
            self.assertIn("Innocent", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
