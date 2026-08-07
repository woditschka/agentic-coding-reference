"""Unit suite for the trend aggregation: the binary quality bar, the
cost-per-pass cell with waste accounting and lower-bound marking, the
requested-pin row key, and the render-path scrubbing."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

import summarize
from summarize import (
    JUDGE_FACETS,
    KIND_REFUSAL,
    MAX_LEDGER_BYTES,
    TREND,
    TREND_DEV,
    Run,
    _judge_median,
    _models_cell,
    approved_section,
    bar_cell,
    checkpoint_ladder,
    ckpt_cell,
    cost_cell,
    escalation_candidates,
    escalation_report,
    escalation_section,
    failed_suite_tests,
    grader_concordance_section,
    grading_figures,
    ledger_grader_verdict,
    ledger_records,
    models_label,
    outcome_cell,
    pin_note,
    provisional_cells,
    render,
    render_pipeline,
    render_run_page,
    roster_section,
    rubric_cell,
    scrub,
    table_section,
    trend_views,
    version_key,
    wall_cell,
    waste_cell,
)


def table_rows(lines: list[str], heading: str) -> list[str]:
    """The data rows under one `###` heading, `####` task tables included —
    header and separator lines drop, so tests pick a section's rows."""
    start = lines.index(f"### {heading}") + 1
    rows: list[str] = []
    for line in lines[start:]:
        if line.startswith("### "):
            break
        if line.startswith("|") and not line.startswith(("| Version", "|---")):
            rows.append(line)
    return rows


def patch_judge_dir(test: unittest.TestCase) -> None:
    """Point JUDGE_DIR at a temp roster holding rubric-v1.md, so rubric-link
    assertions never depend on the repo's live `judge/` directory."""
    judge_dir = Path(tempfile.mkdtemp())
    (judge_dir / "rubric-v1.md").write_text("rubric", encoding="utf-8")
    test.addCleanup(shutil.rmtree, judge_dir, ignore_errors=True)
    original = summarize.JUDGE_DIR
    summarize.JUDGE_DIR = judge_dir
    test.addCleanup(setattr, summarize, "JUDGE_DIR", original)


def a_run(**overrides: Any) -> Run:
    fields: dict[str, Any] = {
        "folder": "runs/v0.2.0/2026-08-02-visit-edit-r1",
        "rep": 1,
        "epoch": "e" * 40,
        "sut_repo": "owner/sut",
        "sut_branch": "main",
        "version": "v0.2.0",
        "model_requested": "(default)",
        "task": "visit-edit",
        "task_kind": "feature",
        "task_title": "Edit a visit",
        "started": "2026-08-02T10:00:00",
        "status": "complete",
        "oracle_ok": True,
        "oracle_tests": {"editWorks": "passed", "wiringWorks": "passed"},
        "suite_green": True,
        "suite_green_base": True,
        "files_changed": 2,
        "src_files_changed": 2,
        "consultations": 0,
        "models": ("claude-opus-5",),
        "cost": 3.0,
        "accounted_cost": None,
        "judge_cost": 1.0,
        "wall": 600.0,
        "judge_median": None,
        "judge_rubric": None,
        "judge_model": None,
    }
    fields.update(overrides)
    return Run(**fields)


class QualityBarTest(unittest.TestCase):
    def test_a_complete_run_with_oracle_and_suite_green_clears(self) -> None:
        self.assertTrue(a_run().cleared)

    def test_an_oracle_failure_does_not_clear(self) -> None:
        self.assertFalse(a_run(oracle_ok=False).cleared)

    def test_a_timeout_does_not_clear(self) -> None:
        self.assertFalse(a_run(status="timeout", oracle_ok=None).cleared)

    def test_an_attributable_suite_break_does_not_clear(self) -> None:
        self.assertFalse(a_run(suite_green=False, suite_green_base=True).cleared)

    def test_a_red_pristine_baseline_makes_the_bar_unreachable(self) -> None:
        self.assertFalse(a_run(suite_green=False, suite_green_base=False).cleared)


def a_refusal_run(**overrides: Any) -> Run:
    fields: dict[str, Any] = {
        "task": "visit-cancel",
        "task_kind": KIND_REFUSAL,
        "task_title": "Cancel a booked visit",
        "oracle_ok": None,
        "oracle_tests": {},
        "files_changed": 0,
        "src_files_changed": 0,
        "consultations": 1,
    }
    fields.update(overrides)
    return a_run(**fields)


class RefusalBarTest(unittest.TestCase):
    """The refusal bar reads the recorded diff, never an oracle."""

    def test_a_complete_run_without_src_changes_clears(self) -> None:
        self.assertTrue(a_refusal_run().cleared)

    def test_any_src_change_fails_even_with_a_green_suite(self) -> None:
        self.assertFalse(a_refusal_run(src_files_changed=3, files_changed=3).cleared)

    def test_a_record_missing_the_src_count_fails_closed(self) -> None:
        self.assertFalse(a_refusal_run(src_files_changed=None).cleared)

    def test_a_suite_break_fails(self) -> None:
        self.assertFalse(a_refusal_run(suite_green=False).cleared)

    def test_a_timeout_fails(self) -> None:
        self.assertFalse(a_refusal_run(status="timeout").cleared)

    def test_non_src_changes_alone_do_not_fail_the_bar(self) -> None:
        self.assertTrue(a_refusal_run(files_changed=1, src_files_changed=0).cleared)

    def test_the_missing_consultation_never_fails_the_bar(self) -> None:
        self.assertTrue(a_refusal_run(consultations=0).cleared)


class CheckpointLadderTest(unittest.TestCase):
    """The graded ladder derived from recorded facts (README § Checkpoints)."""

    def test_the_standard_ladder_carries_one_step_per_oracle_test(self) -> None:
        steps = checkpoint_ladder(
            "feature", "complete", 2, 2, True, {"a": "passed", "b": "failed"}, 0
        )
        self.assertEqual(len(steps), 5)
        self.assertEqual(sum(1 for _n, hit in steps if hit), 4)

    def test_missing_facts_read_as_not_hit(self) -> None:
        steps = checkpoint_ladder("feature", "timeout", None, None, None, {}, 0)
        self.assertEqual(sum(1 for _n, hit in steps if hit), 0)

    def test_the_refusal_ladder_counts_the_consultation_last(self) -> None:
        steps = checkpoint_ladder(KIND_REFUSAL, "complete", 0, 0, True, {}, 1)
        self.assertEqual([hit for _n, hit in steps], [True, True, True, True])
        self.assertEqual(steps[-1][0], "consultation recorded")

    def test_a_refusal_that_implemented_misses_the_src_step(self) -> None:
        steps = checkpoint_ladder(KIND_REFUSAL, "complete", 4, 4, True, {}, 0)
        self.assertEqual(sum(1 for _n, hit in steps if hit), 2)

    def test_run_checkpoints_counts_hit_and_total(self) -> None:
        run = a_run(oracle_tests={"a": "passed", "b": "failed"}, oracle_ok=False)
        self.assertEqual(run.checkpoints(), (4, 5))


class CheckpointCellTest(unittest.TestCase):
    def test_a_full_ladder_cell_renders_blank(self) -> None:
        self.assertEqual(ckpt_cell([a_run()]), "")

    def test_a_short_stopped_rep_fills_every_rep_in_order(self) -> None:
        cell = ckpt_cell(
            [
                a_run(),
                a_run(oracle_tests={"editWorks": "passed", "wiringWorks": "failed"}),
            ]
        )
        self.assertEqual(cell, "5/5 · 4/5")

    def test_a_pure_waste_cell_still_shows_its_checkpoints(self) -> None:
        runs = [a_run(status="timeout", oracle_ok=None, oracle_tests={}, cost=2.0)]
        self.assertEqual(bar_cell(runs), "0/1")
        self.assertEqual(ckpt_cell(runs), "2/3")
        self.assertEqual(cost_cell(runs), "—")
        self.assertEqual(waste_cell(runs), "$2.00")
        self.assertEqual(wall_cell(runs), "10m")


class SpendTest(unittest.TestCase):
    def test_the_cli_self_report_is_the_primary_cost_source(self) -> None:
        run = a_run(cost=3.5, accounted_cost=9.9)
        self.assertEqual(run.agent_spend, 3.5)
        self.assertTrue(run.spend_known)

    def test_the_transcript_figure_covers_a_missing_self_report(self) -> None:
        run = a_run(cost=None, accounted_cost=4.2)
        self.assertEqual(run.agent_spend, 4.2)
        self.assertTrue(run.spend_known)

    def test_no_cost_source_at_all_marks_the_spend_unknown(self) -> None:
        run = a_run(cost=None, accounted_cost=None)
        self.assertEqual(run.agent_spend, 0.0)
        self.assertFalse(run.spend_known)

    def test_the_grader_share_nets_proportionally(self) -> None:
        # Grader owns 10% of the accounted total; the self-report nets 10%.
        run = a_run(cost=3.0, accounted_cost=5.0, grading_spend=0.5)
        self.assertAlmostEqual(run.agent_spend, 2.7)
        fallback = a_run(cost=None, accounted_cost=4.0, grading_spend=1.0)
        self.assertAlmostEqual(fallback.agent_spend, 3.0)

    def test_without_an_accounted_total_no_netting_applies(self) -> None:
        self.assertEqual(a_run(cost=3.0, grading_spend=0.5).agent_spend, 3.0)

    def test_a_share_owning_the_whole_total_floors_at_zero(self) -> None:
        run = a_run(cost=3.0, accounted_cost=1.0, grading_spend=9.0)
        self.assertEqual(run.agent_spend, 0.0)

    def test_the_grader_share_is_netted_out_of_wall(self) -> None:
        self.assertEqual(a_run(wall=600.0, grading_seconds=60.0).delivery_wall, 540.0)
        self.assertIsNone(a_run(wall=None, grading_seconds=60.0).delivery_wall)

    def test_the_cell_median_wall_is_the_delivery_wall(self) -> None:
        self.assertEqual(wall_cell([a_run(wall=600.0, grading_seconds=120.0)]), "8m")


class CostPerPassCellTest(unittest.TestCase):
    def test_clearing_reps_divide_the_cell_agent_spend(self) -> None:
        runs = [a_run(cost=3.0), a_run(cost=5.0)]
        self.assertEqual(bar_cell(runs), "2/2")
        self.assertEqual(cost_cell(runs), "$4.00")
        self.assertEqual(waste_cell(runs), "")

    def test_a_wasted_rep_is_charged_into_cost_per_pass(self) -> None:
        runs = [a_run(cost=3.0), a_run(oracle_ok=False, cost=4.0)]
        self.assertEqual(bar_cell(runs), "1/2")
        self.assertEqual(cost_cell(runs), "$7.00")
        self.assertEqual(waste_cell(runs), "$4.00")

    def test_a_cell_with_no_clearing_rep_reports_pure_waste(self) -> None:
        runs = [
            a_run(status="timeout", oracle_ok=None, cost=2.5),
            a_run(oracle_ok=False, cost=3.0),
        ]
        self.assertEqual(bar_cell(runs), "0/2")
        # The only dollar figure is the waste — no unit cost without a pass.
        self.assertEqual(cost_cell(runs), "—")
        self.assertEqual(waste_cell(runs), "$5.50")
        self.assertEqual(wall_cell(runs), "10m")

    def test_an_unrecorded_spend_renders_every_figure_as_a_lower_bound(self) -> None:
        runs = [
            a_run(cost=3.0),
            a_run(status="timeout", oracle_ok=None, cost=None),
        ]
        self.assertEqual(cost_cell(runs), ">=$3.00")
        self.assertEqual(waste_cell(runs), ">=$0.00")

    def test_an_unrecorded_clearing_rep_bounds_cost_but_not_waste(self) -> None:
        runs = [a_run(cost=None, accounted_cost=None), a_run(cost=5.0)]
        self.assertEqual(cost_cell(runs), ">=$2.50")
        self.assertEqual(waste_cell(runs), "")

    def test_judge_spend_never_enters_the_cell(self) -> None:
        with_judge = cost_cell([a_run(judge_cost=50.0)])
        without_judge = cost_cell([a_run(judge_cost=None)])
        self.assertEqual(with_judge, without_judge)


class RepDetailTest(unittest.TestCase):
    def rows(self, runs: list[Run]) -> list[str]:
        return [line for line in roster_section(runs) if line.startswith("| v")]

    def test_the_trend_cell_carries_no_per_rep_listing(self) -> None:
        runs = [a_run(cost=3.0), a_run(rep=2, cost=5.0)]
        for cell in (bar_cell(runs), cost_cell(runs), wall_cell(runs)):
            self.assertNotIn("reps", cell)
            self.assertNotIn("<br>", cell)

    def test_the_detail_table_is_collapsed_by_default(self) -> None:
        lines = roster_section([a_run(), a_run(rep=2)])
        self.assertIn("<details>", lines)
        self.assertIn("</details>", lines)
        summary = next(line for line in lines if line.startswith("<summary>"))
        self.assertIn("2 runs", summary)

    def test_a_rep_row_carries_bar_spend_and_delivery_wall(self) -> None:
        rows = self.rows([a_run(cost=3.0, wall=600.0, grading_seconds=120.0)])
        self.assertIn("| cleared | $3.00 | 8m |", rows[0])

    def test_a_below_bar_rep_reads_wasted_with_its_status(self) -> None:
        rows = self.rows([a_run(status="timeout", oracle_ok=None, cost=2.5)])
        self.assertIn("| wasted (timeout) | $2.50 | 10m |", rows[0])

    def test_an_unrecorded_spend_reads_unknown(self) -> None:
        rows = self.rows([a_run(cost=None, accounted_cost=None, wall=None)])
        self.assertIn("| $? | ?m |", rows[0])

    def test_a_multi_rep_cell_joins_figures_in_reps_order(self) -> None:
        rows = self.rows(
            [
                a_run(cost=3.0, wall=600.0, grading_seconds=120.0),
                a_run(
                    rep=2,
                    folder="runs/v0.2.0/2026-08-03-visit-edit-r2",
                    status="timeout",
                    oracle_ok=None,
                    cost=2.5,
                ),
            ]
        )
        self.assertEqual(len(rows), 1)
        self.assertIn(
            "| cleared · wasted (timeout) | $3.00 · $2.50 | 8m · 10m |", rows[0]
        )
        self.assertIn(
            "| [r1](runs/v0.2.0/2026-08-02-visit-edit-r1/README.md),"
            " [r2](runs/v0.2.0/2026-08-03-visit-edit-r2/README.md) |",
            rows[0],
        )


class TrendRowTest(unittest.TestCase):
    def test_a_trend_row_links_its_reps_in_order(self) -> None:
        lines = table_section(
            [
                a_run(folder="runs/v0.2.0/2026-08-03-visit-edit-r2", rep=2, cost=5.0),
                a_run(),
            ]
        )
        row = table_rows(lines, "Trend by task")[0]
        self.assertIn(
            "| [r1](runs/v0.2.0/2026-08-02-visit-edit-r1/README.md),"
            " [r2](runs/v0.2.0/2026-08-03-visit-edit-r2/README.md) |",
            row,
        )

    def test_a_full_clean_row_leaves_ckpt_and_waste_blank(self) -> None:
        row = table_rows(table_section([a_run()]), "Trend by task")[0]
        self.assertIn("| 1/1 |  | $3.00 |  | 10m |", row)

    def test_a_refusal_section_states_the_expected_refusal(self) -> None:
        lines = table_section([a_run(), a_refusal_run()])
        cancel = lines[lines.index("#### visit-cancel") + 2]
        self.assertIn("the expected outcome is a refusal", cancel)
        self.assertIn("The bar inverts", cancel)
        edit = lines[lines.index("#### visit-edit") + 2]
        self.assertEqual(edit, "feature: Edit a visit")

    def test_only_the_refusal_section_carries_the_outcome_column(self) -> None:
        lines = table_section([a_run(), a_refusal_run()])
        cancel_head = lines[lines.index("#### visit-cancel") + 4]
        edit_head = lines[lines.index("#### visit-edit") + 4]
        self.assertIn("| Bar | Outcome | Ckpt |", cancel_head)
        self.assertIn("| Bar | Ckpt |", edit_head)
        cancel_row = lines[lines.index("#### visit-cancel") + 6]
        self.assertIn("| 1/1 | refused |", cancel_row)


class OutcomeCellTest(unittest.TestCase):
    """Each refusal rep's fate, named from the recorded facts."""

    def test_a_clearing_rep_with_a_consultation_reads_refused(self) -> None:
        self.assertEqual(outcome_cell([a_refusal_run()]), "refused")

    def test_a_clearing_rep_without_a_consultation_carries_the_star(self) -> None:
        self.assertEqual(outcome_cell([a_refusal_run(consultations=0)]), "refused*")

    def test_a_src_touching_rep_reads_implemented(self) -> None:
        run = a_refusal_run(src_files_changed=3, files_changed=3)
        self.assertEqual(outcome_cell([run]), "implemented")

    def test_an_incomplete_rep_reads_its_terminal_status(self) -> None:
        run = a_refusal_run(status="timeout", src_files_changed=2)
        self.assertEqual(outcome_cell([run]), "timeout")

    def test_a_broken_suite_without_src_changes_reads_suite_red(self) -> None:
        self.assertEqual(outcome_cell([a_refusal_run(suite_green=False)]), "suite red")

    def test_a_missing_src_count_reads_unknown(self) -> None:
        self.assertEqual(outcome_cell([a_refusal_run(src_files_changed=None)]), "?")

    def test_a_multi_rep_cell_joins_fates_in_reps_order(self) -> None:
        cell = outcome_cell(
            [a_refusal_run(), a_refusal_run(src_files_changed=1, files_changed=1)]
        )
        self.assertEqual(cell, "refused · implemented")

    def test_a_forged_status_cannot_break_the_row(self) -> None:
        run = a_refusal_run(status="bad | forged")
        self.assertNotIn("|", outcome_cell([run]))


class ProvisionalCellTest(unittest.TestCase):
    def test_both_thin_arms_of_a_tripped_pair_are_marked(self) -> None:
        thin = provisional_cells(
            [a_run(version="v0.1.0", cost=3.0), a_run(version="v0.2.0", cost=6.0)]
        )
        self.assertEqual(
            thin,
            {
                ("(default)", "v0.1.0", "visit-edit"),
                ("(default)", "v0.2.0", "visit-edit"),
            },
        )

    def test_a_quiet_single_rep_cell_carries_no_mark(self) -> None:
        thin = provisional_cells(
            [a_run(version="v0.1.0", cost=3.0), a_run(version="v0.2.0", cost=3.2)]
        )
        self.assertEqual(thin, set())

    def test_a_cell_without_a_version_neighbor_carries_no_mark(self) -> None:
        self.assertEqual(provisional_cells([a_run()]), set())

    def test_an_arm_already_at_depth_stays_unmarked(self) -> None:
        deep = [a_run(version="v0.1.0", rep=n, cost=3.0) for n in (1, 2, 3)]
        thin = provisional_cells([*deep, a_run(version="v0.2.0", cost=6.0)])
        self.assertEqual(thin, {("(default)", "v0.2.0", "visit-edit")})

    def test_a_settled_pair_marks_nothing(self) -> None:
        runs = [
            a_run(version=v, rep=n, cost=c)
            for n in (1, 2, 3)
            for v, c in (("v0.1.0", 3.0), ("v0.2.0", 6.0))
        ]
        self.assertEqual(provisional_cells(runs), set())

    def test_a_thin_arm_row_marks_bar_cost_and_wall(self) -> None:
        lines = table_section(
            [a_run(version="v0.1.0", cost=3.0), a_run(version="v0.2.0", cost=6.0)]
        )
        rows = table_rows(lines, "Trend by task")
        self.assertEqual(len(rows), 2)
        for marked in ("| ~1/1 |", "| ~$", "| ~10m |"):
            self.assertTrue(all(marked in row for row in rows), marked)

    def test_the_sweep_table_carries_no_mark(self) -> None:
        lines = table_section(
            [a_run(version="v0.1.0", cost=3.0), a_run(version="v0.2.0", cost=6.0)]
        )
        for row in table_rows(lines, "Sweep spend"):
            self.assertNotIn("~", row)

    def test_cells_default_to_no_mark(self) -> None:
        self.assertEqual(bar_cell([a_run()]), "1/1")
        self.assertEqual(cost_cell([a_run()]), "$3.00")
        self.assertEqual(wall_cell([a_run()]), "10m")

    def test_a_wasted_cell_renders_the_mark_on_its_figures(self) -> None:
        runs = [a_run(status="timeout", oracle_ok=None, cost=2.0)]
        self.assertTrue(bar_cell(runs, provisional=True).startswith("~0/1"))
        # A dash is no figure — the provisional mark has nothing to qualify.
        self.assertEqual(cost_cell(runs, provisional=True), "—")
        self.assertTrue(wall_cell(runs, provisional=True).startswith("~10m"))


class ProvisionalLegendTest(unittest.TestCase):
    """The `~` bullet references the Escalation check section, so it renders
    only on a page that can carry one — a comparable version pair exists."""

    def test_a_page_with_a_comparable_pair_carries_the_bullet(self) -> None:
        text = render([a_run(version="v0.1.0"), a_run(version="v0.2.0")])
        self.assertIn("`~` prefixes a provisional figure", text)
        self.assertIn("### Escalation check", text)

    def test_a_single_version_page_omits_the_bullet_and_the_section(self) -> None:
        text = render([a_run()])
        self.assertNotIn("`~` prefixes", text)
        self.assertNotIn("### Escalation check", text)


class ParseBoundaryTest(unittest.TestCase):
    """Agent-influenceable record fields are validated where they are read;
    one crafted or malformed folder must never abort the corpus render or
    reach a sanitizer that assumes its type."""

    def load_single(self, manifest: dict[str, Any], result: dict[str, Any]) -> Run:
        version_dir = Path(tempfile.mkdtemp()) / "v9.9.9"
        run_dir = version_dir / "2026-08-04-visit-edit-r1"
        run_dir.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, version_dir.parent, ignore_errors=True)
        (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (run_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")
        original = summarize.RUNS_DIR
        summarize.RUNS_DIR = version_dir.parent
        self.addCleanup(setattr, summarize, "RUNS_DIR", original)
        return summarize.load_runs()[0]

    def test_a_crafted_rep_reads_as_zero_never_a_link_label(self) -> None:
        run = self.load_single(
            {"rep": "1](https://evil.example)"}, {"status": "complete"}
        )
        self.assertEqual(run.rep, 0)

    def test_non_string_judge_provenance_reads_as_unknown(self) -> None:
        run = self.load_single(
            {"rep": 1},
            {
                "status": "complete",
                "quality_judge": {"rubric": 5, "model": ["x"], "cost_usd": "1.0"},
            },
        )
        self.assertIsNone(run.judge_rubric)
        self.assertIsNone(run.judge_model)
        self.assertIsNone(run.judge_cost)

    def test_an_arbitrary_precision_integer_reads_as_unrecorded(self) -> None:
        run = self.load_single(
            {"rep": 1},
            {"status": "complete", "agent": {"total_cost_usd": 10**400}},
        )
        self.assertIsNone(run.cost)

    def test_a_non_finite_or_bool_figure_reads_as_unrecorded(self) -> None:
        run = self.load_single(
            {"rep": 1},
            {
                "status": "complete",
                "agent": {"total_cost_usd": float("nan")},
                "wall_seconds": True,
            },
        )
        self.assertIsNone(run.cost)
        self.assertIsNone(run.wall)


class ModelRowTest(unittest.TestCase):
    def test_rows_key_on_the_requested_pin_not_the_resolved_set(self) -> None:
        lines = table_section(
            [
                a_run(models=("claude-opus-5",)),
                a_run(models=("claude-opus-5", "claude-sonnet-5"), cost=5.0),
            ],
        )
        rows = table_rows(lines, "Trend by task")
        self.assertEqual(len(rows), 1)
        self.assertIn("| 2/2 |", rows[0])

    def test_a_failed_rep_without_resolved_models_stays_in_its_cell(self) -> None:
        lines = table_section(
            [
                a_run(),
                a_run(status="timeout", oracle_ok=None, models=(), cost=None),
            ],
        )
        rows = table_rows(lines, "Trend by task")
        self.assertEqual(len(rows), 1)
        self.assertIn("| 1/2 |", rows[0])

    def test_models_label_strips_the_claude_prefix(self) -> None:
        label = models_label(("claude-haiku-4-5", "claude-opus-5"))
        self.assertEqual(label, "haiku-4-5 · opus-5")

    def test_a_synthetic_ledger_entry_never_enters_the_label(self) -> None:
        label = models_label(("<synthetic>", "claude-opus-5", "claude-sonnet-5"))
        self.assertEqual(label, "opus-5 · sonnet-5")

    def test_a_synthetic_only_set_reads_as_no_model_not_unknown(self) -> None:
        self.assertEqual(models_label(("<synthetic>",)), "—")
        self.assertEqual(_models_cell(("<synthetic>",)), "—")
        self.assertEqual(_models_cell(("claude-opus-5",)), "opus-5")

    def test_an_empty_record_reads_unknown_in_trend_no_model_per_agent(self) -> None:
        self.assertEqual(models_label(()), "?")
        self.assertEqual(_models_cell(()), "—")

    def test_a_single_pin_table_omits_the_pin(self) -> None:
        lines = table_section(
            [a_run(model_requested="claude-opus-5", models=("claude-opus-5",))],
        )
        row = table_rows(lines, "Sweep spend")[0]
        self.assertIn("opus-5", row)
        self.assertNotIn("pin", row)

    def test_mixed_pins_render_beside_the_version_in_every_table(self) -> None:
        lines = table_section(
            [
                a_run(model_requested="claude-opus-5"),
                a_run(model_requested="(default)", cost=5.0),
            ],
        )
        for heading in ("Trend by task", "Sweep spend"):
            rows = table_rows(lines, heading)
            self.assertEqual(len(rows), 2, heading)
            joined = "\n".join(rows)
            self.assertIn("v0.2.0 (pin opus-5)", joined)
            self.assertIn("v0.2.0 (default pin)", joined)

    def test_pin_note_strips_the_claude_prefix(self) -> None:
        self.assertEqual(pin_note("claude-opus-5"), " (pin opus-5)")

    def test_tag_versions_order_numerically_before_dev_labels(self) -> None:
        ordered = sorted(["dev-abc1234", "v0.10.0", "v0.2.0"], key=version_key)
        self.assertEqual(ordered, ["v0.2.0", "v0.10.0", "dev-abc1234"])


class RubricCellTest(unittest.TestCase):
    def setUp(self) -> None:
        patch_judge_dir(self)

    def test_a_rostered_rubric_renders_as_a_link_into_judge(self) -> None:
        self.assertEqual(
            rubric_cell("rubric-v1.md"), "[rubric-v1.md](../judge/rubric-v1.md)"
        )

    def test_a_case_variant_renders_plain_despite_macos_matching(self) -> None:
        self.assertEqual(rubric_cell("RUBRIC-V1.MD"), "RUBRIC-V1.MD")

    def test_a_trailing_newline_never_reaches_a_link_target(self) -> None:
        self.assertNotIn("](", rubric_cell("rubric-v1.md\n"))


class JudgeMedianParseTest(unittest.TestCase):
    def test_a_string_score_reads_the_record_as_unjudged(self) -> None:
        self.assertIsNone(_judge_median({"design_fit": "4 | forged |"}))

    def test_a_non_dict_record_reads_as_unjudged(self) -> None:
        self.assertIsNone(_judge_median(["design_fit"]))

    def test_a_bool_score_reads_the_record_as_unjudged(self) -> None:
        self.assertIsNone(_judge_median({"design_fit": True}))

    def test_a_recorded_int_score_coerces_to_float(self) -> None:
        self.assertEqual(_judge_median({"design_fit": 4}), {"design_fit": 4.0})

    def test_an_even_sample_float_median_renders_without_a_decimal(self) -> None:
        lines = table_section([a_run(judge_median={f: 4.0 for f in JUDGE_FACETS})])
        self.assertTrue(any(line.endswith("| 4 | 4 | 4 | 4 |") for line in lines))
        self.assertFalse(any("4.0" in line for line in lines))

    def test_a_genuine_half_step_median_keeps_its_fraction(self) -> None:
        lines = table_section([a_run(judge_median={f: 3.5 for f in JUDGE_FACETS})])
        self.assertTrue(any(line.endswith("| 3.5 | 3.5 |") for line in lines))


class NewestFirstOrderTest(unittest.TestCase):
    """Every trend surface lists the newest version first, tasks ascending."""

    def test_task_sections_order_by_task_versions_newest_first(self) -> None:
        lines = table_section(
            [
                a_run(version="v0.1.0"),
                a_run(version="v0.10.0"),
                a_run(version="v0.1.0", task="a-task"),
                a_run(version="v0.10.0", task="a-task"),
            ]
        )
        self.assertLess(lines.index("#### a-task"), lines.index("#### visit-edit"))
        rows = table_rows(lines, "Trend by task")
        self.assertEqual(
            [row.split(" | ")[0].lstrip("| ") for row in rows],
            ["v0.10.0", "v0.1.0", "v0.10.0", "v0.1.0"],
        )

    def test_the_sweep_table_lists_the_newest_version_first(self) -> None:
        lines = table_section([a_run(version="v0.1.0"), a_run(version="v0.10.0")])
        rows = table_rows(lines, "Sweep spend")
        self.assertEqual(
            [row.split(" | ")[0].lstrip("| ") for row in rows],
            ["v0.10.0", "v0.1.0"],
        )

    def test_judge_rows_order_newest_version_first_then_task(self) -> None:
        median = {facet: 3.0 for facet in JUDGE_FACETS}
        judge = {"judge_median": median, "judge_rubric": "rubric-v1.md"}
        lines = table_section(
            [
                a_run(version="v0.1.0", task="a-task", **judge),
                a_run(version="v0.2.0", task="b-task", **judge),
                a_run(version="v0.2.0", task="a-task", **judge),
            ],
        )
        expected = [
            ("| v0.2.0", "a-task"),
            ("| v0.2.0", "b-task"),
            ("| v0.1.0", "a-task"),
        ]
        medians = [line for line in lines if line.endswith("| 3 | 3 |")]
        self.assertEqual([tuple(r.split(" | ")[:2]) for r in medians], expected)
        provenance = [line for line in lines if "rubric-v1.md" in line]
        self.assertEqual(len(provenance), 1)
        self.assertTrue(provenance[0].startswith("| v0.2.0, v0.1.0 |"))

    def test_the_roster_lists_the_newest_version_first(self) -> None:
        lines = roster_section([a_run(version="v0.1.0"), a_run(version="v0.2.0")])
        rows = [line for line in lines if line.startswith("| v0.")]
        self.assertEqual(
            [row.split(" | ")[0].lstrip("| ") for row in rows], ["v0.2.0", "v0.1.0"]
        )


class PageIntroTest(unittest.TestCase):
    def test_the_page_links_the_sut_branch(self) -> None:
        text = render([a_run()])
        self.assertIn(
            "SUT: [`owner/sut`](https://github.com/owner/sut/tree/main), branch `main`",
            text,
        )

    def test_a_malformed_slug_renders_plain_never_as_a_link_target(self) -> None:
        text = render([a_run(sut_repo="owner/sut(evil")])
        self.assertIn("SUT: `owner/sut(evil`, branch `main`", text)
        self.assertNotIn("github.com", text)

    def test_each_task_section_heads_its_table_with_the_title(self) -> None:
        text = render([a_run()])
        self.assertIn("#### visit-edit\n\nfeature: Edit a visit\n", text)

    def test_a_single_base_record_carries_no_span_note(self) -> None:
        text = render([a_run()])
        self.assertNotIn("base commits", text)

    def test_a_multi_base_record_is_called_out_never_silently_mixed(self) -> None:
        text = render([a_run(), a_run(epoch="f" * 40, started="2026-08-03T10:00:00")])
        self.assertIn("Runs on record span 2 base commits.", text)


class JudgeSpendColumnTest(unittest.TestCase):
    def setUp(self) -> None:
        patch_judge_dir(self)

    def test_an_unjudged_arm_renders_a_dash_never_zero(self) -> None:
        lines = table_section([a_run(judge_cost=None)])
        row = table_rows(lines, "Sweep spend")[0]
        self.assertTrue(row.endswith("| — |"))

    def test_the_medians_section_carries_its_advisory_explanation(self) -> None:
        lines = table_section(
            [a_run(judge_median={facet: 3 for facet in ("design_fit",)})]
        )
        text = "\n".join(lines)
        self.assertIn("### Advisory judge medians", text)
        self.assertIn("never enter the quality bar", text)

    def test_the_provenance_table_carries_agent_models_beside_the_judge(
        self,
    ) -> None:
        lines = table_section(
            [
                a_run(
                    judge_median={f: 3 for f in JUDGE_FACETS},
                    judge_rubric="rubric-v1.md",
                    judge_model="claude-opus-5",
                    models=("claude-fable-5", "claude-opus-5"),
                )
            ]
        )
        text = "\n".join(lines)
        self.assertIn("| Judged rows | Agent models | Judge model | Rubric |", text)
        self.assertIn(
            "| v0.2.0 | fable-5 · opus-5 | claude-opus-5 "
            "| [rubric-v1.md](../judge/rubric-v1.md) |",
            text,
        )
        medians_header = next(line for line in lines if "design-fit" in line)
        self.assertNotIn("Judge model", medians_header)

    def test_a_medians_row_links_its_rep_to_the_run_folder(self) -> None:
        lines = table_section([a_run(judge_median={f: 3 for f in JUDGE_FACETS})])
        medians_row = next(line for line in lines if line.endswith("| 3 | 3 |"))
        self.assertIn(
            "[r1](runs/v0.2.0/2026-08-02-visit-edit-r1/README.md)", medians_row
        )

    def test_a_multi_rep_cell_collapses_to_one_row_scores_in_reps_order(
        self,
    ) -> None:
        lines = table_section(
            [
                a_run(judge_median={f: 3 for f in JUDGE_FACETS}),
                a_run(
                    rep=2,
                    folder="runs/v0.2.0/2026-08-03-visit-edit-r2",
                    started="2026-08-03T10:00:00",
                    judge_median={f: 4 for f in JUDGE_FACETS},
                ),
            ]
        )
        row = next(line for line in lines if "3 · 4" in line)
        self.assertIn(
            "| [r1](runs/v0.2.0/2026-08-02-visit-edit-r1/README.md),"
            " [r2](runs/v0.2.0/2026-08-03-visit-edit-r2/README.md) |",
            row,
        )
        self.assertTrue(row.endswith("| 3 · 4 | 3 · 4 | 3 · 4 | 3 · 4 |"))

    def test_a_rep_missing_a_facet_keeps_its_slot_in_the_cell(self) -> None:
        partial = {f: 3.0 for f in JUDGE_FACETS if f != "doc_fit"}
        lines = table_section(
            [
                a_run(judge_median={f: 3.0 for f in JUDGE_FACETS}),
                a_run(
                    rep=2,
                    folder="runs/v0.2.0/2026-08-03-visit-edit-r2",
                    started="2026-08-03T10:00:00",
                    judge_median=partial,
                ),
            ]
        )
        row = next(line for line in lines if "3 · ?" in line)
        self.assertTrue(row.endswith("| 3 · 3 | 3 · 3 | 3 · 3 | 3 · ? |"))

    def test_an_unsafe_folder_renders_plain_reps_in_both_judge_tables(self) -> None:
        # r2 carries a different rubric so the cell splits and the
        # provenance coverage falls back to naming reps.
        lines = table_section(
            [
                a_run(
                    folder="../outside",
                    judge_median={f: 3 for f in JUDGE_FACETS},
                    judge_rubric="rubric-v1.md",
                    judge_model="claude-opus-5",
                ),
                a_run(
                    rep=2,
                    folder="../outside-too",
                    started="2026-08-03T10:00:00",
                    judge_median={f: 3 for f in JUDGE_FACETS},
                    judge_rubric="rubric-v2.md",
                    judge_model="claude-opus-5",
                ),
            ]
        )
        text = "\n".join(lines)
        medians_row = next(line for line in lines if line.endswith("| 3 · 3 |"))
        provenance_row = next(line for line in lines if "rubric-v1.md]" in line)
        self.assertIn("| r1, r2 |", medians_row)
        self.assertIn("(r1)", provenance_row)
        self.assertNotIn("(../outside", text)

    def test_a_rubric_absent_from_disk_renders_plain_never_as_a_link(self) -> None:
        lines = table_section(
            [
                a_run(
                    judge_median={f: 3 for f in JUDGE_FACETS},
                    judge_rubric="no-such-rubric.md",
                )
            ]
        )
        text = "\n".join(lines)
        self.assertIn("| no-such-rubric.md |", text)
        self.assertNotIn("(../judge/no-such-rubric.md)", text)

    def test_identical_reps_collapse_to_one_provenance_row(self) -> None:
        judged = {
            "judge_median": {f: 3 for f in JUDGE_FACETS},
            "judge_rubric": "rubric-v1.md",
            "judge_model": "claude-opus-5",
        }
        lines = table_section(
            [
                a_run(**judged),
                a_run(rep=2, folder="runs/v0.2.0/2026-08-03-visit-edit-r2", **judged),
            ]
        )
        provenance = [line for line in lines if "rubric-v1.md" in line]
        self.assertEqual(len(provenance), 1)
        self.assertTrue(provenance[0].startswith("| v0.2.0 |"))
        self.assertNotIn("r1", provenance[0])

    def test_reps_differing_in_provenance_stay_attributable_per_rep(self) -> None:
        median = {f: 3 for f in JUDGE_FACETS}
        lines = table_section(
            [
                a_run(judge_median=median, judge_rubric="rubric-v2.md"),
                a_run(
                    rep=2,
                    folder="runs/v0.2.0/2026-08-03-visit-edit-r2",
                    judge_median=median,
                    judge_rubric="rubric-v1.md",
                ),
            ]
        )
        v2_row = next(line for line in lines if "rubric-v2.md" in line)
        v1_row = next(line for line in lines if "rubric-v1.md" in line)
        self.assertIn(
            "| v0.2.0 visit-edit"
            " ([r1](runs/v0.2.0/2026-08-02-visit-edit-r1/README.md)) |",
            v2_row,
        )
        self.assertIn(
            "| v0.2.0 visit-edit"
            " ([r2](runs/v0.2.0/2026-08-03-visit-edit-r2/README.md)) |",
            v1_row,
        )

    def test_a_version_split_by_task_lists_whole_cells_without_reps(self) -> None:
        median = {f: 3 for f in JUDGE_FACETS}
        lines = table_section(
            [
                a_run(task="a-task", judge_median=median, judge_rubric="rubric-v2.md"),
                a_run(task="b-task", judge_median=median, judge_rubric="rubric-v1.md"),
            ]
        )
        v2_row = next(line for line in lines if "rubric-v2.md" in line)
        self.assertIn("| v0.2.0 a-task |", v2_row)
        self.assertNotIn("(", v2_row)

    def test_judge_spend_averages_over_the_judged_reps_only(self) -> None:
        lines = table_section(
            [a_run(judge_cost=1.25), a_run(judge_cost=None, cost=5.0)]
        )
        row = table_rows(lines, "Sweep spend")[0]
        self.assertTrue(row.endswith("| $1.25 |"))


class SweepSpendColumnTest(unittest.TestCase):
    """The spend columns price one sweep — each task cell contributes its
    per-rep mean — so rows with unequal rep depth stay comparable."""

    def test_a_deeper_cell_averages_instead_of_inflating_the_row(self) -> None:
        lines = table_section(
            [
                a_run(cost=4.0, judge_cost=None),
                a_run(rep=2, cost=2.0, judge_cost=None),
                a_run(task="owners-page-param", cost=5.0, judge_cost=None),
            ]
        )
        row = table_rows(lines, "Sweep spend")[0]
        self.assertIn("| $8.00 |", row)

    def test_judge_spend_normalizes_per_judged_rep_within_a_cell(self) -> None:
        lines = table_section(
            [a_run(judge_cost=2.0), a_run(rep=2, judge_cost=4.0, cost=5.0)]
        )
        row = table_rows(lines, "Sweep spend")[0]
        self.assertTrue(row.endswith("| $3.00 |"))

    def test_grading_spend_averages_within_a_cell(self) -> None:
        lines = table_section(
            [
                a_run(grading_spend=2.0, judge_cost=None),
                a_run(rep=2, grading_spend=4.0, judge_cost=None),
            ]
        )
        row = table_rows(lines, "Sweep spend")[0]
        self.assertIn("| $3.00 | — |", row)

    def test_an_unrecorded_rep_marks_the_row_a_lower_bound(self) -> None:
        lines = table_section([a_run(), a_run(rep=2, cost=None, judge_cost=None)])
        row = table_rows(lines, "Sweep spend")[0]
        self.assertIn("| >=$1.50 |", row)

    def test_a_total_overflowing_to_inf_renders_unknown(self) -> None:
        big = 1.7e308
        lines = table_section(
            [
                a_run(cost=big, judge_cost=None),
                a_run(rep=2, cost=big, judge_cost=None),
            ]
        )
        row = table_rows(lines, "Sweep spend")[0]
        self.assertIn("| $? |", row)


class ScrubTest(unittest.TestCase):
    def test_table_syntax_and_newlines_collapse_to_spaces(self) -> None:
        forged = "opus-5 |\n| v9.9.9 | 1/1"
        self.assertNotIn("|", scrub(forged))
        self.assertNotIn("\n", scrub(forged))

    def test_terminal_escape_bytes_are_removed(self) -> None:
        self.assertEqual(scrub("safe\x1b[31mred"), "safe [31mred")

    def test_a_forged_model_id_cannot_break_the_row(self) -> None:
        lines = table_section([a_run(models=("claude-x |\n| forged-row |",))])
        self.assertEqual(len(table_rows(lines, "Sweep spend")), 1)


def a_manifest(**overrides: Any) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "rep": 1,
        "started": "2026-08-02T10:00:00+00:00",
        "exec_mode": "claude-dev",
        "model_requested": "claude-opus-5",
        "cc_version": "2.1.220 (Claude Code)",
        "prompt": "Bug report: the visit form loses edits.\nFix it and cover it.",
        "task": {
            "id": "visit-edit",
            "kind": "feature",
            "title": "Edit a visit",
            "fingerprint": "abcd1234",
        },
        "version": {
            "label": "v0.2.0",
            "kind": "tag",
            "plugin": "agent-team-spring-boot",
        },
        "sut": {"repo": "owner/sut", "branch": "main", "sha": "e" * 40},
    }
    manifest.update(overrides)
    return manifest


def a_result(**overrides: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "complete",
        "wall_seconds": 600.0,
        "agent": {
            "total_cost_usd": 3.5,
            "num_turns": 20,
            "models": ["claude-opus-5"],
            "accounted": {"hit_pct": 88},
        },
        "oracle": {
            "oracle_passed": True,
            "passed": 2,
            "total": 2,
            "suite_green": True,
            "suite_green_base": True,
            "tests": {"editWorks": "passed", "wiringWorks": "failed"},
        },
        "pipeline": {"grader_verdict": "clear"},
        "diff": {"files_changed": 2, "insertions": 64, "deletions": 2},
    }
    result.update(overrides)
    return result


class RunPageTest(unittest.TestCase):
    def test_present_artifacts_link_and_absent_ones_never_render(self) -> None:
        page = render_run_page(a_manifest(), a_result(), ["change.patch", "run.log"])
        self.assertIn("[`change.patch`](change.patch)", page)
        self.assertIn("[`run.log`](run.log)", page)
        self.assertNotIn("board.md", page)
        self.assertNotIn("egress.log", page)

    def test_oracle_cases_render_with_their_outcomes(self) -> None:
        page = render_run_page(a_manifest(), a_result(), [])
        self.assertIn("`editWorks` — passed", page)
        self.assertIn("`wiringWorks` — failed", page)

    def test_the_judge_block_renders_only_when_judged(self) -> None:
        unjudged = render_run_page(a_manifest(), a_result(), [])
        self.assertNotIn("## Judge", unjudged)
        judged = render_run_page(
            a_manifest(),
            a_result(
                quality_judge={
                    "median": {f: 4 for f in JUDGE_FACETS},
                    "spread": {f: 1 for f in JUDGE_FACETS},
                    "samples_requested": 3,
                    "rubric": "rubric-v1.md",
                    "model": "claude-opus-5",
                    "cost_usd": 0.56,
                }
            ),
            [],
        )
        self.assertIn("## Judge (advisory)", judged)
        self.assertIn("4 (±1)", judged)
        self.assertIn("$0.56", judged)
        self.assertIn("rationales: `result.json`", judged)
        self.assertNotIn("Per-sample rationales", judged)

    def test_judge_sample_rationales_render_neutralized(self) -> None:
        page = render_run_page(
            a_manifest(),
            a_result(
                quality_judge={
                    "median": {f: 4.0 for f in JUDGE_FACETS},
                    "spread": {f: 0.0 for f in JUDGE_FACETS},
                    "samples_requested": 3,
                    "rubric": "rubric-v1.md",
                    "model": "claude-opus-5",
                    "cost_usd": 0.56,
                    "samples": [
                        {f: 4 for f in JUDGE_FACETS}
                        | {"rationale": "Clean fix. </details> escapes nothing."},
                        {f: 3 for f in JUDGE_FACETS} | {"rationale": "   "},
                        {f: 5.0 for f in JUDGE_FACETS}
                        | {"rationale": "~~~ no fence opens here"},
                        "not-a-record",
                    ],
                }
            ),
            [],
        )
        self.assertIn("Per-sample rationales", page)
        self.assertIn("**Sample 1** — design-fit 4 · test-quality 4", page)
        self.assertIn("> Clean fix. \\</details> escapes nothing.", page)
        self.assertIn("rationales below", page)
        self.assertIn("Median (spread) over 3 sample(s)", page)
        self.assertIn("4 (±0)", page)
        self.assertNotIn("4.0", page)
        # The blank-rationale sample is skipped but keeps its number, so
        # the page's sample numbers index `result.json` directly.
        self.assertNotIn("**Sample 2**", page)
        self.assertIn("**Sample 3** — design-fit 5", page)
        self.assertIn("> ~~~ no fence opens here", page)
        self.assertNotIn("\n~~~", page)
        self.assertNotIn("rationales: `result.json`", page)

    def test_the_median_basis_is_the_parsed_count_not_the_requested(self) -> None:
        page = render_run_page(
            a_manifest(),
            a_result(
                quality_judge={
                    "median": {f: 4 for f in JUDGE_FACETS},
                    "spread": {f: 0 for f in JUDGE_FACETS},
                    "samples_requested": 3,
                    "rubric": "rubric-v1.md",
                    "model": "claude-opus-5",
                    "cost_usd": 0.56,
                    "samples": [
                        {f: 4 for f in JUDGE_FACETS} | {"rationale": "One."},
                        {f: 4 for f in JUDGE_FACETS} | {"rationale": "Two."},
                    ],
                }
            ),
            [],
        )
        self.assertIn("Median (spread) over 2 sample(s) (3 requested)", page)

    def test_the_prompt_keeps_its_line_breaks_as_a_blockquote(self) -> None:
        page = render_run_page(a_manifest(), a_result(), [])
        self.assertIn("> Bug report: the visit form loses edits.", page)
        self.assertIn("> Fix it and cover it.", page)

    def test_a_forged_title_cannot_break_the_verdict_table(self) -> None:
        manifest = a_manifest()
        manifest["task"]["title"] = "evil | injected"
        page = render_run_page(manifest, a_result(), [])
        self.assertNotIn("evil |", page)

    def test_degraded_records_render_placeholders_never_raise(self) -> None:
        page = render_run_page({}, {"status": "error"}, [])
        self.assertIn("status **error**", page)
        self.assertIn("| oracle | ? ?/? passed |", page)


class CheckpointRowTest(unittest.TestCase):
    def test_the_verdict_table_carries_the_checkpoint_count(self) -> None:
        page = render_run_page(a_manifest(), a_result(), [])
        self.assertIn("| checkpoints | 4/5 |", page)


class RefusalRunPageTest(unittest.TestCase):
    def refusal_manifest(self) -> dict[str, Any]:
        manifest = a_manifest()
        manifest["task"] = {
            "id": "visit-cancel",
            "kind": KIND_REFUSAL,
            "title": "Cancel a booked visit",
            "fingerprint": "abcd1234",
        }
        return manifest

    def refusal_result(self, src_files: int, consultations: int) -> dict[str, Any]:
        return a_result(
            oracle={
                "oracle_passed": None,
                "passed": 0,
                "total": 0,
                "tests": {},
                "suite_green": True,
                "suite_green_base": True,
            },
            diff={
                "files_changed": src_files,
                "insertions": 0,
                "deletions": 0,
                "src_files_changed": src_files,
            },
            pipeline={
                "grader_verdict": None,
                "consultation_requests": consultations,
            },
        )

    def test_the_oracle_row_names_the_diff_grading(self) -> None:
        page = render_run_page(self.refusal_manifest(), self.refusal_result(0, 1), [])
        self.assertIn(
            "| oracle | — (refusal task: graded by the recorded diff) |", page
        )
        self.assertNotIn("?/? passed", page)

    def test_the_refusal_rows_show_src_changes_and_consultations(self) -> None:
        page = render_run_page(self.refusal_manifest(), self.refusal_result(0, 1), [])
        self.assertIn("| src files changed | 0 |", page)
        self.assertIn("| consultation-request records (Tier B) | 1 |", page)
        self.assertIn("| checkpoints | 4/4 |", page)

    def test_an_implementing_refusal_run_shows_the_missed_steps(self) -> None:
        page = render_run_page(self.refusal_manifest(), self.refusal_result(3, 0), [])
        self.assertIn("| src files changed | 3 |", page)
        self.assertIn("| checkpoints | 2/4 |", page)

    def test_a_boolean_consultation_count_renders_unknown_not_true(self) -> None:
        result = self.refusal_result(0, 0)
        result["pipeline"]["consultation_requests"] = True
        page = render_run_page(self.refusal_manifest(), result, [])
        self.assertIn("| consultation-request records (Tier B) | ? |", page)
        self.assertIn("| checkpoints | 3/4 |", page)


class DiffEmbedTest(unittest.TestCase):
    PATCH = "diff --git a/src/A.java b/src/A.java\n-old line\n+new line\n"

    def test_the_patch_embeds_as_a_collapsible_diff_block(self) -> None:
        page = render_run_page(a_manifest(), a_result(), [], self.PATCH)
        self.assertIn("## Change", page)
        self.assertIn("<details>", page)
        self.assertIn("```diff\ndiff --git a/src/A.java", page)
        self.assertIn("+new line", page)

    def test_a_backtick_run_in_the_patch_cannot_close_the_fence(self) -> None:
        page = render_run_page(a_manifest(), a_result(), [], "+x = ```` inline\n")
        self.assertIn("`````diff", page)

    def test_an_oversized_patch_links_instead_of_embedding(self) -> None:
        big = "+line\n" * 500
        page = render_run_page(a_manifest(), a_result(), [], big)
        self.assertNotIn("```diff", page)
        self.assertIn("[`change.patch`](change.patch)", page)

    def test_no_patch_renders_no_change_section(self) -> None:
        page = render_run_page(a_manifest(), a_result(), [])
        self.assertNotIn("## Change", page)

    def test_escape_bytes_are_neutralized_line_structure_kept(self) -> None:
        page = render_run_page(a_manifest(), a_result(), [], "+a\x1b[31mred\n+b\n")
        self.assertNotIn("\x1b", page)
        self.assertIn("+a [31mred\n+b", page)


class BoardEmbedTest(unittest.TestCase):
    BOARD = "### REQ-1\n\n| reviewer | R1 |\n| --- | --- |\n| **test** | ok |\n"

    def test_the_board_embeds_open_never_behind_a_fold(self) -> None:
        page = render_run_page(a_manifest(), a_result(), [], None, self.BOARD)
        self.assertIn("## Pipeline", page)
        self.assertIn("| **test** | ok |", page)
        pipeline = page.split("## Pipeline")[1].split("## Artifacts")[0]
        self.assertNotIn("<details>", pipeline)

    def test_an_oversized_board_links_instead_of_embedding(self) -> None:
        big = "row\n" * 500
        page = render_run_page(a_manifest(), a_result(), [], None, big)
        self.assertNotIn("row\nrow", page)
        self.assertIn("[`handoff.jsonl`](handoff.jsonl)", page)

    def test_no_board_renders_no_pipeline_section(self) -> None:
        page = render_run_page(a_manifest(), a_result(), [])
        self.assertNotIn("## Pipeline", page)

    def test_an_unbalanced_board_fence_is_closed_never_left_open(self) -> None:
        page = render_run_page(
            a_manifest(), a_result(), [], None, "text\n```\nswallowed\n"
        )
        pipeline = page.split("## Pipeline")[1]
        self.assertEqual(pipeline.count("```"), 2)
        self.assertIn("## Artifacts", page)

    def test_a_balanced_board_fence_gains_no_extra_fence(self) -> None:
        page = render_run_page(
            a_manifest(), a_result(), [], None, "a\n```\ncode\n```\nb\n"
        )
        self.assertEqual(page.split("## Pipeline")[1].count("```"), 2)


class UnmeasuredNoteTest(unittest.TestCase):
    def test_every_defined_task_measured_yields_no_note(self) -> None:
        from summarize import TASKS_DIR, unmeasured_note

        defined = {path.parent.name for path in TASKS_DIR.glob("*/task.toml")}
        self.assertIsNone(unmeasured_note(defined))

    def test_a_missing_task_is_named_never_silently_dropped(self) -> None:
        from summarize import unmeasured_note

        note = unmeasured_note({"owners-page-param"})
        assert note is not None
        self.assertIn("`visit-edit`", note)
        self.assertIn("unmeasured", note)


class AgentsTableTest(unittest.TestCase):
    def a_costs(self) -> dict[str, Any]:
        return {
            "per_agent": [
                {
                    "agent_type": "(parent)",
                    "models": ["claude-opus-5"],
                    "wall_seconds": 907.6,
                    "totals": {"cost": 2.36, "hit_pct": 95},
                },
                {
                    "agent_type": "agent-team:test-reviewer",
                    "models": ["claude-sonnet-5"],
                    "wall_seconds": 47.1,
                    "totals": {"cost": 0.35, "hit_pct": 78},
                },
                {
                    "agent_type": "agent-team:feature-implementer",
                    "wall_seconds": 189.8,
                    "totals": {"cost": 1.38, "hit_pct": 94},
                },
            ]
        }

    def test_rows_render_spend_heaviest_first(self) -> None:
        page = render_run_page(a_manifest(), a_result(), [], costs=self.a_costs())
        section = page.split("<summary>Per-transcript breakdown</summary>")[1]
        section = section.split("</details>")[0]
        rows = [line for line in section.splitlines() if line.startswith("| `")]
        self.assertEqual(len(rows), 3)
        self.assertIn("(parent)", rows[0])
        self.assertIn("opus-5 | $2.36 | 15m 7s | 95%", rows[0])
        self.assertIn("feature-implementer", rows[1])
        self.assertIn("test-reviewer", rows[2])
        self.assertIn("sonnet-5 | $0.35 | 47s | 78%", rows[2])

    def test_a_row_without_recorded_models_renders_a_dash(self) -> None:
        page = render_run_page(a_manifest(), a_result(), [], costs=self.a_costs())
        self.assertIn("`agent-team:feature-implementer` | — |", page)

    def test_no_cost_record_renders_no_agents_section(self) -> None:
        page = render_run_page(a_manifest(), a_result(), [])
        self.assertNotIn("## Agents", page)

    def test_a_degraded_cost_record_renders_no_agents_section(self) -> None:
        page = render_run_page(
            a_manifest(), a_result(), [], costs={"per_agent": "junk"}
        )
        self.assertNotIn("## Agents", page)

    def test_one_transcript_per_type_still_renders_the_totals_table(self) -> None:
        page = render_run_page(a_manifest(), a_result(), [], costs=self.a_costs())
        self.assertIn("| agent | runs |", page)
        self.assertIn("`(parent)` | 1 | opus-5 | $2.36 | 15m 7s |", page)


class AgentTotalsTableTest(unittest.TestCase):
    def a_costs_with_repeats(self) -> dict[str, Any]:
        return {
            "per_agent": [
                {
                    "agent_type": "(parent)",
                    "models": ["claude-opus-5"],
                    "wall_seconds": 907.6,
                    "totals": {
                        "cost": 2.36,
                        "hit_pct": 95,
                        "cache_read": 1_900_000,
                        "total_input": 2_000_000,
                    },
                },
                {
                    "agent_type": "agent-team:feature-implementer",
                    "models": ["claude-opus-5"],
                    "wall_seconds": 190.0,
                    "totals": {
                        "cost": 1.40,
                        "hit_pct": 90,
                        "cache_read": 1_800_000,
                        "total_input": 2_000_000,
                    },
                },
                {
                    "agent_type": "agent-team:feature-implementer",
                    "models": ["claude-sonnet-5"],
                    "wall_seconds": 110.0,
                    "totals": {
                        "cost": 1.10,
                        "hit_pct": 20,
                        "cache_read": 60_000,
                        "total_input": 300_000,
                    },
                },
            ]
        }

    def totals_rows(self, costs: dict[str, Any]) -> list[str]:
        page = render_run_page(a_manifest(), a_result(), [], costs=costs)
        section = page.split("| agent | runs |")[1].split("<details>")[0]
        return [line for line in section.splitlines() if line.startswith("| `")]

    def test_a_repeated_type_sums_spend_wall_and_unions_models(self) -> None:
        rows = self.totals_rows(self.a_costs_with_repeats())
        self.assertEqual(len(rows), 2)
        self.assertIn("`agent-team:feature-implementer` | 2 |", rows[0])
        self.assertIn("opus-5 · sonnet-5 | $2.50 | 5m 0s |", rows[0])
        self.assertIn("`(parent)` | 1 | opus-5 | $2.36 | 15m 7s | 95% |", rows[1])

    def test_a_repeated_type_weights_cache_hit_by_tokens(self) -> None:
        # 1.86M cached of 2.3M total reads 81%; the per-transcript mean is 55.
        rows = self.totals_rows(self.a_costs_with_repeats())
        self.assertIn("| $2.50 | 5m 0s | 81% |", rows[0])

    def test_an_unknown_part_yields_no_partial_total(self) -> None:
        costs = self.a_costs_with_repeats()
        costs["per_agent"][2]["totals"] = {}
        del costs["per_agent"][2]["wall_seconds"]
        rows = self.totals_rows(costs)
        self.assertIn("`agent-team:feature-implementer` | 2 |", rows[1])
        self.assertIn("| ? | ? | ? |", rows[1])

    def test_a_non_finite_cost_never_poisons_the_total(self) -> None:
        costs = self.a_costs_with_repeats()
        costs["per_agent"][2]["totals"]["cost"] = float("nan")
        rows = self.totals_rows(costs)
        self.assertIn("`agent-team:feature-implementer` | 2 |", rows[1])
        self.assertIn("| ? | 5m 0s |", rows[1])


class WallFormatTest(unittest.TestCase):
    def test_minutes_and_seconds_truncate_together(self) -> None:
        from summarize import _fmt_wall

        self.assertEqual(_fmt_wall(90), "1m 30s")
        self.assertEqual(_fmt_wall(359.6), "5m 59s")
        self.assertEqual(_fmt_wall(47.9), "47s")
        self.assertEqual(_fmt_wall(None), "?")


class PromptQuoteTest(unittest.TestCase):
    def test_indentation_inside_the_prompt_survives(self) -> None:
        manifest = a_manifest(prompt="Fix it:\n    indented detail\nDone.")
        page = render_run_page(manifest, a_result(), [])
        self.assertIn(">     indented detail", page)


class RosterSectionTest(unittest.TestCase):
    def test_each_cell_links_its_reps_in_order(self) -> None:
        runs = [
            a_run(folder="runs/v0.2.0/2026-08-02-visit-edit-r2", rep=2),
            a_run(folder="runs/v0.2.0/2026-08-02-visit-edit-r1", rep=1),
        ]
        text = "\n".join(roster_section(runs))
        first = text.find("[r1](runs/v0.2.0/2026-08-02-visit-edit-r1/README.md)")
        second = text.find("[r2](runs/v0.2.0/2026-08-02-visit-edit-r2/README.md)")
        self.assertGreaterEqual(first, 0)
        self.assertGreater(second, first)

    def test_an_unsafe_folder_path_renders_plain_never_as_a_link(self) -> None:
        runs = [a_run(folder="../outside", rep=1)]
        text = "\n".join(roster_section(runs))
        self.assertNotIn("](../outside", text)
        self.assertIn("r1", text)

    def test_the_trend_page_carries_the_roster(self) -> None:
        self.assertIn("### Recorded runs", render([a_run()]))


class PipelineRenderTest(unittest.TestCase):
    """The page's Pipeline section: rendered from the committed ledger by the
    current harness renderer, so a rendering fix reaches recorded runs."""

    GRADE = {
        "type": "grader-verdict",
        "req_id": "REQ-A-001",
        "ts": "2026-08-03T10:00:00+00:00",
        "author": "change-grader",
        "verdict": "concern",
        "summary": "clamp the page parameter",
        "facets": {
            "reviewer_hedging": {
                "verdict": "concern",
                "note": "The approval carries an unresolved clarify naming a "
                "sibling controller that still carries the identical defect, "
                "which nobody answered before the grade was cut.",
            }
        },
        "rationale": "The fix is tight; the open scope question is not. "
        "Decide whether the sibling ships as a follow-up before merging.",
    }

    REVIEW = {
        "type": "review-feedback",
        "req_id": "REQ-A-001",
        "ts": "2026-08-03T10:01:00+00:00",
        "author": "code-quality-reviewer",
        "verdict": "approved",
        "findings": [],
        "approved_aspects": [
            "Clamp logic is a single readable line at the entry point",
            "The new constant is well-named and documented",
        ],
    }

    def a_run_folder(self, *records: dict[str, Any]) -> Path:
        out_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        (out_dir / "handoff.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
        )
        return out_dir

    def test_the_facet_note_and_rationale_render_whole(self):
        rendered = render_pipeline(self.a_run_folder(self.GRADE))
        self.assertIsNotNone(rendered)
        assert rendered is not None
        self.assertIn("nobody answered before the grade was cut.", rendered)
        self.assertIn("before merging.", rendered)
        self.assertNotIn("…", rendered)

    def test_a_folder_with_no_ledger_renders_nothing(self):
        out_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        self.assertIsNone(render_pipeline(out_dir))

    def test_an_oversized_ledger_is_never_handed_to_the_engine(self):
        out_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        (out_dir / "handoff.jsonl").write_text("x" * (MAX_LEDGER_BYTES + 1))
        self.assertIsNone(render_pipeline(out_dir))

    def test_approved_aspects_ride_in_a_closed_details_block(self):
        lines = approved_section(self.a_run_folder(self.REVIEW))
        text = "\n".join(lines)
        self.assertIn("<details>", text)
        self.assertIn("</details>", text)
        self.assertIn("code-quality-reviewer", text)
        self.assertIn(
            "- Clamp logic is a single readable line at the entry point", text
        )

    def test_a_review_without_approved_aspects_adds_no_block(self):
        record = {k: v for k, v in self.REVIEW.items() if k != "approved_aspects"}
        self.assertEqual(approved_section(self.a_run_folder(record)), [])

    def test_a_malformed_ledger_line_is_skipped_not_fatal(self):
        out_dir = self.a_run_folder(self.REVIEW)
        ledger = out_dir / "handoff.jsonl"
        ledger.write_text("{ broken\n" + ledger.read_text(), encoding="utf-8")
        self.assertIn("code-quality-reviewer", "\n".join(approved_section(out_dir)))

    def test_aspect_text_is_scrubbed_before_it_lands_in_markdown(self):
        record = dict(self.REVIEW, approved_aspects=["a | b `c` d"])
        text = "\n".join(approved_section(self.a_run_folder(record)))
        self.assertNotIn("|", text)
        self.assertNotIn("`", text)

    def test_an_aspect_cannot_close_the_details_block_early(self):
        record = dict(self.REVIEW, approved_aspects=["solid </details><h1>x</h1>"])
        lines = approved_section(self.a_run_folder(record))
        unescaped = [li for li in lines if re.search(r"(?<!\\)</details>", li)]
        self.assertEqual(unescaped, ["</details>"])
        self.assertIn("- solid \\</details>\\<h1>x\\</h1>", lines)


class SuiteFailuresTest(unittest.TestCase):
    """Failing post-agent suite test names, scoped to their log section."""

    LOG = (
        "=== suite baseline (pristine) ===\n"
        "BaselineTests > flakyBefore() FAILED\n"
        "=== suite run (post-agent) ===\n"
        "> Task :test FAILED\n"
        "PetClinicConcurrencyTests > raceIsBlocked() FAILED\n"
        "=== oracle run ===\n"
        "OracleTests > oracleCase() FAILED\n"
    )

    def folder_with_log(self, log: str | None) -> Path:
        out_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        if log is not None:
            (out_dir / "run.log").write_text(log, encoding="utf-8")
        return out_dir

    def test_only_the_post_agent_section_contributes_names(self):
        names = failed_suite_tests(self.folder_with_log(self.LOG))
        self.assertEqual(names, ["PetClinicConcurrencyTests > raceIsBlocked()"])

    def test_a_missing_log_or_section_yields_nothing(self):
        self.assertEqual(failed_suite_tests(self.folder_with_log(None)), [])
        self.assertEqual(failed_suite_tests(self.folder_with_log("no sections")), [])

    def test_failures_render_on_the_page(self):
        page = render_run_page(
            a_manifest(),
            a_result(),
            [],
            suite_failures=["PetClinicConcurrencyTests > raceIsBlocked()"],
        )
        self.assertIn("Post-agent suite failures (from the build log):", page)
        self.assertIn("- `PetClinicConcurrencyTests > raceIsBlocked()`", page)


class GradingFiguresTest(unittest.TestCase):
    """The change grader's spend and wall as their own Figures columns."""

    def costs_with(self, *agents: tuple[str, float, float]) -> dict[str, object]:
        return {
            "per_agent": [
                {
                    "agent_type": kind,
                    "totals": {"cost": cost, "hit_pct": 82},
                    "wall_seconds": wall,
                }
                for kind, cost, wall in agents
            ]
        }

    def test_the_grader_row_yields_spend_wall_and_cache_hit(self):
        figures = grading_figures(
            self.costs_with(
                ("(parent)", 3.0, 800.0), ("agent-team:change-grader", 1.0, 84.0)
            )
        )
        self.assertEqual(figures, ("$1.00", "1m 24s", "82%", 1.0, 84.0))

    def test_no_grader_row_yields_no_grading_table(self):
        self.assertIsNone(grading_figures(self.costs_with(("(parent)", 3.0, 800.0))))
        self.assertIsNone(grading_figures(None))
        page = render_run_page(
            a_manifest(),
            a_result(),
            [],
            costs=self.costs_with(("(parent)", 3.0, 9.0)),
            grade="clear",
        )
        self.assertNotIn("grading", page)

    def test_a_cost_row_without_a_ledger_verdict_never_nets(self):
        # A grading transcript alone proves nothing: without the grade the
        # page keeps whole-run figures and renders no grading table.
        page = render_run_page(
            a_manifest(),
            a_result(),
            [],
            costs=self.costs_with(("agent-team:change-grader", 1.0, 120.0)),
        )
        self.assertIn("| $3.50 | 10m | ", page)
        self.assertNotIn("grading", page)

    def test_the_headline_nets_out_the_grader(self):
        # Grader accounted $1 of a $4 accounted total: spend nets 25% of the
        # self-report; wall subtracts the serial hop directly.
        result = a_result()
        agent = result["agent"]
        assert isinstance(agent, dict)
        agent["accounted"] = {"hit_pct": 88, "cost": 4.0}
        page = render_run_page(
            a_manifest(),
            result,
            [],
            costs=self.costs_with(("agent-team:change-grader", 1.0, 120.0)),
            grade="clear",
        )
        self.assertIn("| $2.62 | 8m | ", page)
        self.assertIn("share below excluded from spend and wall", page)

    def test_the_grading_table_renders_on_the_page(self):
        page = render_run_page(
            a_manifest(),
            a_result(),
            [],
            costs=self.costs_with(("agent-team:change-grader", 1.0, 84.0)),
            grade="clear",
        )
        self.assertIn("| spend | wall | cache hit |", page)
        self.assertIn("| $1.00 | 1m 24s | 82% |", page)
        self.assertIn("optional support for the human merge decision", page)

    def test_hostile_numerics_degrade_instead_of_poisoning(self):
        costs = {
            "per_agent": [
                {
                    "agent_type": "agent-team:change-grader",
                    "totals": {"cost": True, "hit_pct": True},
                    "wall_seconds": float("inf"),
                }
            ]
        }
        self.assertIsNone(grading_figures(costs))
        nan_costs = {
            "per_agent": [
                {
                    "agent_type": "agent-team:change-grader",
                    "totals": {"cost": float("nan"), "hit_pct": 50},
                    "wall_seconds": float("inf"),
                }
            ]
        }
        self.assertIsNone(grading_figures(nan_costs))

    def test_the_grade_footnote_frames_attention_not_verdict(self):
        page = render_run_page(a_manifest(), a_result(), [], grade="concern")
        self.assertIn("| review attention (pipeline grade) | concern |", page)
        self.assertIn("never part of the bar", page)

    def test_no_ledger_verdict_renders_a_dash_and_no_footnote(self):
        page = render_run_page(a_manifest(), a_result(), [])
        self.assertIn("| review attention (pipeline grade) | — |", page)
        self.assertNotIn("never part of the bar", page)


class GraderConcordanceTest(unittest.TestCase):
    """Tier B context: the verdict groups against the bar and the judge."""

    def test_groups_render_bar_and_judge_columns(self) -> None:
        runs = [
            a_run(grader_verdict="clear", judge_median={f: 4.0 for f in JUDGE_FACETS}),
            a_run(rep=2, grader_verdict="clear", oracle_ok=False),
            a_run(rep=3, grader_verdict="concern"),
        ]
        lines = grader_concordance_section(runs)
        text = "\n".join(lines)
        self.assertIn("### Grader concordance", text)
        self.assertIn("| clear | 2 | 1/2 | 4.0 |", text)
        self.assertIn("| concern | 1 | 1/1 | — |", text)

    def test_runs_without_a_verdict_stay_out(self) -> None:
        lines = grader_concordance_section(
            [a_run(grader_verdict="clear"), a_run(rep=2)]
        )
        self.assertIn("| clear | 1 | 1/1 | — |", "\n".join(lines))

    def test_the_section_is_omitted_without_any_verdict(self) -> None:
        self.assertEqual(grader_concordance_section([a_run()]), [])

    def test_a_forged_verdict_cannot_break_the_row(self) -> None:
        lines = grader_concordance_section([a_run(grader_verdict="bad | forged")])
        self.assertFalse(any("bad |" in line for line in lines))


class LedgerRecordsTest(unittest.TestCase):
    """The shared ledger reader — run_eval imports it, so its hardening is
    the seam's single behavior."""

    def folder_with_text(self, text: str) -> Path:
        out_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        (out_dir / "handoff.jsonl").write_text(text, encoding="utf-8")
        return out_dir

    def test_malformed_and_non_object_lines_are_skipped(self) -> None:
        out_dir = self.folder_with_text('{ broken\n[1, 2]\n{"type": "a"}\n')
        self.assertEqual(ledger_records(out_dir), [{"type": "a"}])

    def test_a_missing_or_oversized_ledger_reads_as_empty(self) -> None:
        empty_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, empty_dir, ignore_errors=True)
        self.assertEqual(ledger_records(empty_dir), [])
        big = self.folder_with_text("x" * (MAX_LEDGER_BYTES + 1))
        self.assertEqual(ledger_records(big), [])


class LedgerVerdictTest(unittest.TestCase):
    """The grader's verdict comes from `grader-verdict` records alone; every
    grading render and netting keys on it."""

    GRADER = {"type": "grader-verdict", "verdict": "clear", "author": "change-grader"}
    REVIEWER = {
        "type": "review-feedback",
        "verdict": "approved",
        "author": "code-quality-reviewer",
    }

    def folder_with(self, *records: dict[str, Any]) -> Path:
        out_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, out_dir, ignore_errors=True)
        (out_dir / "handoff.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
        )
        return out_dir

    def test_only_grader_verdict_records_count(self):
        self.assertEqual(
            ledger_grader_verdict(self.folder_with(self.REVIEWER, self.GRADER)),
            "clear",
        )

    def test_a_reviewer_verdict_is_never_attributed_to_the_grader(self):
        self.assertIsNone(ledger_grader_verdict(self.folder_with(self.REVIEWER)))

    def test_a_later_record_of_another_type_does_not_override(self):
        later = {"type": "design-block", "verdict": "minor", "author": "sde"}
        self.assertEqual(
            ledger_grader_verdict(self.folder_with(self.GRADER, later)), "clear"
        )

    def test_load_runs_nets_only_verdict_backed_grading(self):
        version_dir = Path(tempfile.mkdtemp()) / "v9.9.9"
        run_dir = version_dir / "2026-08-04-visit-edit-r1"
        run_dir.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, version_dir.parent, ignore_errors=True)
        (run_dir / "manifest.json").write_text(
            json.dumps({"rep": 1, "task": {"id": "visit-edit"}}), encoding="utf-8"
        )
        (run_dir / "result.json").write_text(
            json.dumps(
                {
                    "status": "complete",
                    "agent": {"total_cost_usd": 4.0, "accounted": {"cost": 8.0}},
                }
            ),
            encoding="utf-8",
        )
        (run_dir / "agent-costs.json").write_text(
            json.dumps(
                {
                    "per_agent": [
                        {
                            "agent_type": "agent-team:change-grader",
                            "totals": {"cost": 2.0},
                            "wall_seconds": 60.0,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        import summarize

        original = summarize.RUNS_DIR
        summarize.RUNS_DIR = version_dir.parent
        try:
            without_verdict = summarize.load_runs()[0]
            (run_dir / "handoff.jsonl").write_text(
                json.dumps({"type": "grader-verdict", "verdict": "clear"}) + "\n",
                encoding="utf-8",
            )
            with_verdict = summarize.load_runs()[0]
        finally:
            summarize.RUNS_DIR = original
        self.assertEqual(without_verdict.grading_spend, 0.0)
        self.assertEqual(without_verdict.agent_spend, 4.0)
        self.assertEqual(with_verdict.grading_spend, 2.0)
        self.assertAlmostEqual(with_verdict.agent_spend, 3.0)  # 4 * (1 - 2/8)


class TrendViewsTest(unittest.TestCase):
    """Dev runs are local-only: the committed TREND.md carries the tagged
    series, TREND-dev.md carries the full comparison and exists only while a
    dev run is on disk."""

    TAGGED = a_run()
    DEV = a_run(
        folder="runs/dev-abc1234/2026-08-03-visit-edit-r1", version="dev-abc1234"
    )

    def test_dev_rows_stay_out_of_the_committed_trend(self):
        views = trend_views([self.TAGGED, self.DEV])
        self.assertIn("v0.2.0", views[TREND])
        self.assertNotIn("dev-abc1234", views[TREND])

    def test_the_dev_view_holds_the_full_comparison(self):
        views = trend_views([self.TAGGED, self.DEV])
        self.assertIn("dev-abc1234", views[TREND_DEV])
        self.assertIn("v0.2.0", views[TREND_DEV])
        self.assertIn("Never committed", views[TREND_DEV])

    def test_no_dev_run_means_no_dev_view(self):
        self.assertEqual(set(trend_views([self.TAGGED])), {TREND})

    def test_only_dev_runs_leaves_an_empty_committed_trend(self):
        views = trend_views([self.DEV])
        self.assertIn("No runs recorded yet.", views[TREND])
        self.assertIn("dev-abc1234", views[TREND_DEV])


class EscalationCheckTest(unittest.TestCase):
    """The escalation check: adjacent-pair pairing, the three triggers, the
    three-rep confirmation depth, and the copy-ready follow-up command."""

    def cell(self, version: str, reps: int = 1, **overrides: Any) -> list[Run]:
        return [a_run(version=version, rep=rep + 1, **overrides) for rep in range(reps)]

    def test_a_cost_move_over_30_percent_lists_with_figures(self) -> None:
        runs = self.cell("v0.1.0", cost=3.0) + self.cell("v0.2.0", cost=4.5)
        (candidate,) = escalation_candidates(runs)
        self.assertEqual(("v0.1.0", "v0.2.0"), (candidate.earlier, candidate.later))
        self.assertEqual(("cost per pass $3.00 → $4.50 (+50%)",), candidate.triggers)
        self.assertEqual(
            "python3 evals/run_eval.py --version v0.1.0 --version v0.2.0"
            " --task visit-edit --reps 2 --judge",
            candidate.command,
        )

    def test_a_move_within_30_percent_stays_quiet(self) -> None:
        runs = self.cell("v0.1.0", cost=3.0) + self.cell("v0.2.0", cost=3.6)
        self.assertEqual([], escalation_candidates(runs))

    def test_a_bar_flip_reports_flip_and_lost_unit_cost(self) -> None:
        runs = self.cell("v0.1.0") + self.cell("v0.2.0", oracle_ok=False)
        (candidate,) = escalation_candidates(runs)
        self.assertEqual(
            (
                "bar verdict flipped (1/1 → 0/1)",
                "unit cost lost (no clearing rep)",
            ),
            candidate.triggers,
        )

    def test_three_reps_per_arm_settle_the_pair(self) -> None:
        runs = self.cell("v0.1.0", reps=3, cost=3.0) + self.cell(
            "v0.2.0", reps=3, cost=4.5
        )
        self.assertEqual([], escalation_candidates(runs))

    def test_pairs_hold_within_one_pin_only(self) -> None:
        runs = self.cell("v0.1.0", cost=3.0) + self.cell(
            "v0.2.0", cost=4.5, model_requested="claude-opus-5"
        )
        self.assertEqual([], escalation_candidates(runs))

    def test_only_adjacent_version_rows_compare(self) -> None:
        runs = (
            self.cell("v0.1.0", cost=3.0)
            + self.cell("v0.2.0", cost=3.0)
            + self.cell("v0.3.0", cost=4.5)
        )
        (candidate,) = escalation_candidates(runs)
        self.assertEqual(("v0.2.0", "v0.3.0"), (candidate.earlier, candidate.later))

    def test_two_dev_rows_list_without_a_runnable_command(self) -> None:
        runs = self.cell("dev-aaa1111", cost=3.0) + self.cell("dev-bbb2222", cost=4.5)
        (candidate,) = escalation_candidates(runs)
        self.assertIsNone(candidate.command)

    def test_a_command_less_pair_renders_the_no_follow_up_note(self) -> None:
        runs = self.cell("dev-aaa1111", cost=3.0) + self.cell("dev-bbb2222", cost=4.5)
        self.assertIn(
            "  (no runnable follow-up command for this pair's recorded labels)",
            escalation_section(runs),
        )
        self.assertIn("no runnable follow-up command", escalation_report(runs))

    def test_a_pinned_pair_carries_the_pin_into_the_command(self) -> None:
        pinned: dict[str, Any] = {"model_requested": "claude-opus-5"}
        runs = self.cell("v0.1.0", cost=3.0, **pinned) + self.cell(
            "v0.2.0", cost=4.5, **pinned
        )
        (candidate,) = escalation_candidates(runs)
        self.assertEqual(
            "python3 evals/run_eval.py --version v0.1.0 --version v0.2.0"
            " --task visit-edit --reps 2 --model claude-opus-5 --judge",
            candidate.command,
        )

    def test_a_version_gap_pairs_the_nearest_measured_cells(self) -> None:
        runs = (
            self.cell("v0.1.0", cost=3.0)
            + self.cell("v0.2.0", cost=3.0, task="other-task")
            + self.cell("v0.3.0", cost=4.5)
        )
        (candidate,) = escalation_candidates(runs)
        self.assertEqual(("v0.1.0", "v0.3.0"), (candidate.earlier, candidate.later))

    def test_a_move_of_exactly_30_percent_stays_quiet(self) -> None:
        runs = self.cell("v0.1.0", cost=10.0) + self.cell("v0.2.0", cost=13.0)
        self.assertEqual([], escalation_candidates(runs))

    def test_one_deep_arm_does_not_settle_the_pair(self) -> None:
        runs = self.cell("v0.1.0", reps=3, cost=3.0) + self.cell("v0.2.0", cost=4.5)
        (candidate,) = escalation_candidates(runs)
        self.assertIn("cost per pass $3.00 → $4.50 (+50%)", candidate.triggers)

    def test_a_label_outside_the_spec_shape_gets_no_command(self) -> None:
        runs = self.cell("v0.1.0", cost=3.0) + self.cell("v9; rm -rf ~", cost=4.5)
        (candidate,) = escalation_candidates(runs)
        self.assertIsNone(candidate.command)

    def test_scrub_strips_line_and_paragraph_separators(self) -> None:
        self.assertEqual("a b c", scrub("a\u2028b\u2029c"))

    def test_a_lower_bound_cell_carries_its_marker_into_the_trigger(self) -> None:
        bounded = self.cell("v0.2.0", cost=4.5) + [
            a_run(
                version="v0.2.0",
                rep=2,
                status="timeout",
                oracle_ok=None,
                cost=None,
                accounted_cost=None,
            )
        ]
        runs = self.cell("v0.1.0", cost=3.0) + bounded
        (candidate,) = escalation_candidates(runs)
        self.assertIn("cost per pass $3.00 → >=$4.50 (+50%)", candidate.triggers)

    def test_a_cell_with_no_recorded_spend_never_costs_a_trigger(self) -> None:
        runs = self.cell("v0.1.0", cost=3.0) + self.cell(
            "v0.2.0", cost=None, accounted_cost=None
        )
        self.assertEqual([], escalation_candidates(runs))

    def test_a_dev_label_maps_back_to_the_dev_spec(self) -> None:
        runs = self.cell("v0.2.0", cost=3.0) + self.cell("dev-abc1234", cost=4.5)
        (candidate,) = escalation_candidates(runs)
        self.assertIn("--version v0.2.0 --version dev ", candidate.command)
        self.assertNotIn("dev-abc1234", candidate.command)

    def test_a_refusal_pair_drops_the_judge_flag(self) -> None:
        refusal = {"task_kind": KIND_REFUSAL, "oracle_ok": None}
        runs = self.cell("v0.1.0", src_files_changed=0, **refusal) + self.cell(
            "v0.2.0", src_files_changed=2, **refusal
        )
        (candidate,) = escalation_candidates(runs)
        self.assertNotIn("--judge", candidate.command)

    def test_candidates_list_most_severe_first(self) -> None:
        # Severity order differs from both alphabetical directions, and each
        # tier holds two magnitudes, so only the real key passes.
        runs = (
            self.cell("v0.1.0", task="a-rise", cost=3.0)
            + self.cell("v0.2.0", task="a-rise", cost=4.2)
            + self.cell("v0.1.0", task="b-flip")
            + self.cell("v0.2.0", task="b-flip", oracle_ok=False)
            + self.cell("v0.1.0", task="c-big-drop", cost=5.0)
            + self.cell("v0.2.0", task="c-big-drop", cost=2.0)
            + self.cell("v0.1.0", task="d-big-rise", cost=3.0)
            + self.cell("v0.2.0", task="d-big-rise", cost=6.0)
            + self.cell("v0.1.0", task="e-drop", cost=5.0)
            + self.cell("v0.2.0", task="e-drop", cost=3.0)
        )
        tasks = [c.task for c in escalation_candidates(runs)]
        self.assertEqual(
            ["b-flip", "d-big-rise", "a-rise", "c-big-drop", "e-drop"], tasks
        )

    def test_a_lost_unit_cost_outranks_a_flip_with_a_cost_rise(self) -> None:
        # "a-flip-rise" keeps a clearing rep (partial flip, cost trebled);
        # "b-lost" collapses to none — the stronger signal, listed first.
        runs = (
            self.cell("v0.1.0", reps=2, task="a-flip-rise", cost=3.0)
            + [a_run(version="v0.2.0", task="a-flip-rise", rep=1, cost=6.0)]
            + [
                a_run(
                    version="v0.2.0",
                    task="a-flip-rise",
                    rep=2,
                    cost=6.0,
                    oracle_ok=False,
                )
            ]
            + [a_run(version="v0.1.0", task="b-lost", rep=1, cost=3.0)]
            + [a_run(version="v0.1.0", task="b-lost", rep=2, oracle_ok=False)]
            + self.cell("v0.2.0", reps=2, task="b-lost", oracle_ok=False)
        )
        tasks = [c.task for c in escalation_candidates(runs)]
        self.assertEqual(["b-lost", "a-flip-rise"], tasks)

    def test_tied_pairs_keep_the_scan_order(self) -> None:
        runs = (
            self.cell("v0.1.0", task="b-rise", cost=3.0)
            + self.cell("v0.2.0", task="b-rise", cost=4.5)
            + self.cell("v0.1.0", task="a-rise", cost=4.0)
            + self.cell("v0.2.0", task="a-rise", cost=6.0)
        )
        tasks = [c.task for c in escalation_candidates(runs)]
        self.assertEqual(["a-rise", "b-rise"], tasks)

    def test_the_section_renders_candidate_and_command(self) -> None:
        runs = self.cell("v0.1.0", cost=3.0) + self.cell("v0.2.0", cost=4.5)
        text = "\n".join(escalation_section(runs))
        self.assertIn("### Escalation check", text)
        self.assertIn("`visit-edit` · `v0.1.0 → v0.2.0`", text)
        self.assertIn("--task visit-edit --reps 2 --judge`", text)

    def test_the_section_is_omitted_without_a_comparable_pair(self) -> None:
        self.assertEqual([], escalation_section(self.cell("v0.2.0")))

    def test_a_clean_pair_renders_the_all_clear_line(self) -> None:
        runs = self.cell("v0.1.0", cost=3.0) + self.cell("v0.2.0", cost=3.3)
        text = "\n".join(escalation_section(runs))
        self.assertIn("No pair trips a trigger", text)

    def test_the_report_lists_commands_and_stays_empty_without_a_pair(self) -> None:
        runs = self.cell("v0.1.0", cost=3.0) + self.cell("v0.2.0", cost=4.5)
        self.assertIn("--task visit-edit --reps 2 --judge", escalation_report(runs))
        self.assertEqual("", escalation_report(self.cell("v0.2.0")))
        clean = self.cell("v0.1.0", cost=3.0) + self.cell("v0.2.0", cost=3.3)
        self.assertEqual(
            "escalation check: no pair trips a trigger", escalation_report(clean)
        )


if __name__ == "__main__":
    unittest.main()
