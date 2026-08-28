"""Tests for render_figure.py — the eval-trend figure generator.

Pins the trend-data.json contract consumption (cells, refusal kinds,
judge medians), the success-only cost arithmetic, the full-window
smoother rule, and the emitted figure's stamped subtitle. The live-tree
test proves the committed data view still loads; the figure itself stays
a dated snapshot outside the battery (update-diagrams skill)."""

from __future__ import annotations

import copy
import datetime
import json
import unittest
from typing import Any

import render_figure
from render_figure import Cell, from_payload, render_figure as render

PAYLOAD = {
    "spec_version": "0.1.0",
    "versions": ["v0.1.1", "v0.1.5", "v0.2.0"],
    "reps": [
        {
            "task": "a-task",
            "task_kind": "feature",
            "version": "v0.1.1",
            "model_pin": "(default)",
            "models": ["claude-opus-5"],
            "rep": 1,
            "cleared": True,
            "agent_spend_usd": 9.0,
            "spend_known": True,
            "wall_seconds": 600.0,
            "delivery_wall_seconds": 570.0,
            "judge_facet_medians": {"design_fit": 3, "doc_fit": 3},
            "run_folder": "runs/v0.1.1/a-r1",
        },
        {
            "task": "a-task",
            "task_kind": "feature",
            "version": "v0.1.1",
            "model_pin": "(default)",
            "models": ["claude-opus-5"],
            "rep": 2,
            "cleared": True,
            "agent_spend_usd": 9.0,
            "spend_known": True,
            "wall_seconds": 600.0,
            "delivery_wall_seconds": 570.0,
            "judge_facet_medians": {"design_fit": 3, "doc_fit": 3},
            "run_folder": "runs/v0.1.1/a-r2",
        },
        {
            "task": "a-task",
            "task_kind": "feature",
            "version": "v0.1.1",
            "model_pin": "(default)",
            "models": ["claude-opus-5"],
            "rep": 3,
            "cleared": False,
            "agent_spend_usd": 6.0,
            "spend_known": True,
            "wall_seconds": 600.0,
            "delivery_wall_seconds": 570.0,
            "judge_facet_medians": None,
            "run_folder": "runs/v0.1.1/a-r3",
        },
        {
            "task": "a-task",
            "task_kind": "feature",
            "version": "v0.1.5",
            "model_pin": "(default)",
            "models": ["claude-opus-5"],
            "rep": 1,
            "cleared": True,
            "agent_spend_usd": 11.0,
            "spend_known": True,
            "wall_seconds": 600.0,
            "delivery_wall_seconds": 570.0,
            "judge_facet_medians": None,
            "run_folder": "runs/v0.1.5/a-r1",
        },
        {
            "task": "a-task",
            "task_kind": "feature",
            "version": "v0.2.0",
            "model_pin": "(default)",
            "models": ["claude-opus-5"],
            "rep": 1,
            "cleared": True,
            "agent_spend_usd": 10.0,
            "spend_known": True,
            "wall_seconds": 600.0,
            "delivery_wall_seconds": 570.0,
            "judge_facet_medians": {"design_fit": 4, "doc_fit": 5},
            "run_folder": "runs/v0.2.0/a-r1",
        },
        {
            "task": "r-task",
            "task_kind": "refusal",
            "version": "v0.1.1",
            "model_pin": "(default)",
            "models": ["claude-opus-5"],
            "rep": 1,
            "cleared": False,
            "agent_spend_usd": 20.0,
            "spend_known": True,
            "wall_seconds": 600.0,
            "delivery_wall_seconds": 570.0,
            "judge_facet_medians": None,
            "run_folder": "runs/v0.1.1/r-r1",
        },
        {
            "task": "r-task",
            "task_kind": "refusal",
            "version": "v0.1.5",
            "model_pin": "(default)",
            "models": ["claude-opus-5"],
            "rep": 1,
            "cleared": True,
            "agent_spend_usd": 1.1,
            "spend_known": True,
            "wall_seconds": 600.0,
            "delivery_wall_seconds": 570.0,
            "judge_facet_medians": None,
            "run_folder": "runs/v0.1.5/r-r1",
        },
        {
            "task": "r-task",
            "task_kind": "refusal",
            "version": "v0.2.0",
            "model_pin": "(default)",
            "models": ["claude-opus-5"],
            "rep": 1,
            "cleared": True,
            "agent_spend_usd": 1.0,
            "spend_known": True,
            "wall_seconds": 600.0,
            "delivery_wall_seconds": 570.0,
            "judge_facet_medians": None,
            "run_folder": "runs/v0.2.0/r-r1",
        },
    ],
}


class PayloadTest(unittest.TestCase):
    def test_reps_aggregate_to_cells_and_refusal_kinds(self) -> None:
        data = from_payload(PAYLOAD)
        self.assertEqual(data.versions, ("v0.1.1", "v0.1.5", "v0.2.0"))
        self.assertEqual(data.refusal_tasks, frozenset({"r-task"}))
        self.assertEqual(
            data.cells[("a-task", "v0.1.1")],
            Cell(2, 3, 24.0, 6.0, wall=9.5, burn=round(9.0 / 9.5, 3)),
        )

    def test_success_cost_is_the_clearing_reps_mean_spend(self) -> None:
        self.assertEqual(Cell(2, 3, 24.0, 6.0).success_cost, 9.00)
        self.assertIsNone(Cell(0, 1, 20.0, 20.0).success_cost)

    def test_quality_is_the_median_of_the_versions_judge_scores(self) -> None:
        data = from_payload(PAYLOAD)
        self.assertEqual(data.quality["v0.2.0"], 4.5)
        self.assertEqual(data.quality["v0.1.1"], 3)
        self.assertIsNone(data.quality["v0.1.5"])


class WallPanelTest(unittest.TestCase):
    def test_a_cell_wall_is_the_clearing_reps_median_in_minutes(self) -> None:
        data = from_payload(PAYLOAD)
        # v0.1.1 a-task: two clearing reps at 570s, one failed rep ignored.
        self.assertEqual(data.cells[("a-task", "v0.1.1")].wall, 9.5)

    def test_a_cell_burn_rate_is_the_median_per_rep_ratio(self) -> None:
        data = from_payload(PAYLOAD)
        # v0.1.1 a-task: two clearing reps at $9.00 over 9.5 delivery minutes.
        self.assertEqual(data.cells[("a-task", "v0.1.1")].burn, round(9.0 / 9.5, 3))

    def test_the_burn_panel_mirrors_the_cost_encoding(self) -> None:
        text = render(from_payload(PAYLOAD), datetime.date(2026, 8, 21))
        self.assertIn('id="plE"', text)
        self.assertIn('id="btrend_a-task"', text)
        self.assertIn('id="bline_r-task"', text)
        self.assertIn('id="brl_a-task"', text)

    def test_a_cell_without_a_clearing_rep_has_no_wall(self) -> None:
        self.assertIsNone(Cell(0, 1, 5.0, 5.0).wall)

    def test_the_panel_mirrors_the_cost_encoding(self) -> None:
        text = render(from_payload(PAYLOAD), datetime.date(2026, 8, 21))
        self.assertIn('id="plD"', text)
        self.assertIn('id="wtrend_a-task"', text)
        self.assertIn('id="wline_r-task"', text)
        self.assertNotIn('id="wtrend_r-task"', text)
        self.assertIn('id="wrl_a-task"', text)


class HardeningTest(unittest.TestCase):
    def test_a_declared_version_no_row_carries_is_dropped(self) -> None:
        payload = dict(PAYLOAD, versions=[*PAYLOAD["versions"], "v9.9.9"])
        self.assertEqual(from_payload(payload).versions, ("v0.1.1", "v0.1.5", "v0.2.0"))

    def test_a_series_with_no_clearing_rep_fails_loud(self) -> None:
        reps = [dict(r, cleared=False) for r in PAYLOAD["reps"]]
        with self.assertRaises(SystemExit):
            render(from_payload(dict(PAYLOAD, reps=reps)), datetime.date(2026, 8, 21))

    def test_a_rep_version_missing_from_the_axis_fails_loud(self) -> None:
        reps = [*PAYLOAD["reps"], dict(PAYLOAD["reps"][0], version="v9.9.9")]
        with self.assertRaises(SystemExit):
            from_payload(dict(PAYLOAD, reps=reps))


class BoundMarkerTest(unittest.TestCase):
    def test_a_lower_bound_cell_renders_a_hollow_dot(self) -> None:
        reps = [
            dict(r, spend_known=False) if r["run_folder"] == "runs/v0.2.0/a-r1" else r
            for r in PAYLOAD["reps"]
        ]
        text = render(
            from_payload(dict(PAYLOAD, reps=reps)), datetime.date(2026, 8, 21)
        )
        hollow = next(line for line in text.splitlines() if 'id="d_a-task_2"' in line)
        self.assertIn("fillColor=none", hollow)


class InterpolationTest(unittest.TestCase):
    def test_the_curve_passes_through_every_anchor(self) -> None:
        anchors = [(0.0, 1.0), (10.0, 5.0), (20.0, 2.0)]
        dense = render_figure._pchip(anchors)
        for a in anchors:
            self.assertIn(a, dense)

    def test_the_curve_never_overshoots_between_anchors(self) -> None:
        dense = render_figure._pchip([(0.0, 1.0), (10.0, 5.0), (20.0, 2.0)])
        ys = [y for _, y in dense]
        self.assertGreaterEqual(min(ys), 1.0)
        self.assertLessEqual(max(ys), 5.0)


class SmootherTest(unittest.TestCase):
    def test_the_line_starts_and_ends_exactly_on_the_data(self) -> None:
        rolled = render_figure._roll([1.0, 2.0, 3.0, 8.0])
        self.assertEqual(
            rolled, [(0, 1.0), (1, 2.0), (2, sum((2.0, 3.0, 8.0)) / 3), (3, 8.0)]
        )

    def test_a_missing_version_contributes_no_point(self) -> None:
        rolled = render_figure._roll([1.0, None, 3.0])
        self.assertEqual(rolled, [(0, 1.0), (2, 3.0)])

    def test_a_leading_gap_still_starts_on_the_recorded_cell(self) -> None:
        rolled = render_figure._roll([None, 2.0, 3.0, 8.0])
        self.assertEqual(rolled[0], (1, 2.0))
        self.assertEqual(rolled[-1], (3, 8.0))

    def test_a_point_beside_an_interior_gap_keeps_a_symmetric_window(self) -> None:
        rolled = render_figure._roll([1.0, None, 9.0, 3.0])
        self.assertEqual(rolled, [(0, 1.0), (2, 9.0), (3, 3.0)])


class RenderTest(unittest.TestCase):
    def test_the_subtitle_stamps_the_latest_version_and_date(self) -> None:
        text = render(from_payload(PAYLOAD), datetime.date(2026, 8, 21))
        self.assertIn("snapshot through v0.2.0 (2026-08-21)", text)

    def test_a_refusal_task_gets_a_dashed_raw_line_never_a_trend(self) -> None:
        text = render(from_payload(PAYLOAD), datetime.date(2026, 8, 21))
        self.assertIn("line_r-task", text)
        self.assertNotIn("trend_r-task", text)

    def test_the_trend_line_reaches_the_first_and_last_version(self) -> None:
        text = render(from_payload(PAYLOAD), datetime.date(2026, 8, 21))
        trend = next(line for line in text.splitlines() if 'id="trend_a-task"' in line)
        self.assertIn('x="80', trend)
        self.assertIn('x="740', trend)

    def test_attribute_values_and_ids_escape_the_quote(self) -> None:
        cell = render_figure._text('an"id', 'a "label"', "text;", 0, 0, 10, 10)
        self.assertNotIn('"an"id"', cell)
        self.assertIn("an&quot;id", cell)
        self.assertIn("a &quot;label&quot;", cell)

    def test_a_root_pin_change_draws_one_rule_with_a_derived_label(self) -> None:
        payload: dict[str, Any] = copy.deepcopy(PAYLOAD)
        for rep in payload["reps"]:
            old = rep["version"] == "v0.1.1"
            rep["model_pin"] = "claude-opus-4-8" if old else "claude-opus-5"
            rep["models"] = (
                ["claude-opus-4-8", "claude-sonnet-4-6"]
                if old
                else ["claude-opus-5", "claude-sonnet-5"]
            )
        data = from_payload(payload)
        self.assertEqual(data.pin_boundaries, (1,))
        text = render(data, datetime.date(2026, 8, 21))
        self.assertEqual(text.count('id="pin0'), 5)  # one segment per panel
        self.assertEqual(text.count('id="pinlabel0"'), 1)
        self.assertNotIn('id="pin1', text)
        label = next(line for line in text.splitlines() if 'id="pinlabel0"' in line)
        self.assertIn("models → opus-5 · sonnet-5", label)
        self.assertIn("fillColor=#FFFFFF", label)  # solid ground over the grid
        rule = next(line for line in text.splitlines() if 'id="pin0a"' in line)
        # Midway between the first two columns (80 and 410): the gap.
        self.assertIn('x="245', rule)

    def test_a_uniform_pin_draws_no_rule(self) -> None:
        text = render(from_payload(PAYLOAD), datetime.date(2026, 8, 21))
        self.assertNotIn('id="pin0', text)
        self.assertNotIn("models →", text)

    def test_a_cell_without_a_clearing_rep_renders_no_dot(self) -> None:
        text = render(from_payload(PAYLOAD), datetime.date(2026, 8, 21))
        self.assertNotIn("d_r-task_0", text)
        self.assertIn("d_r-task_1", text)
        self.assertIn("d_r-task_2", text)


class LiveTreeTest(unittest.TestCase):
    SCHEMA = render_figure.HERE / "trend-data.schema.json"

    def test_the_committed_data_view_loads_and_renders(self) -> None:
        payload = json.loads(render_figure.TREND_DATA.read_text(encoding="utf-8"))
        data = from_payload(payload)
        self.assertGreaterEqual(len(data.versions), 1)
        text = render(data, datetime.date(2026, 8, 21))
        self.assertIn("cost of a clearing rep", text)

    def test_the_committed_data_view_conforms_to_its_schema(self) -> None:
        # The schema's required/properties lists are the oracle: every row
        # carries exactly the contract's fields — no missing, no extras.
        schema = json.loads(self.SCHEMA.read_text(encoding="utf-8"))
        payload = json.loads(render_figure.TREND_DATA.read_text(encoding="utf-8"))
        self.assertEqual(set(payload), set(schema["required"]))
        row_schema = schema["properties"]["reps"]["items"]
        for row in payload["reps"]:
            self.assertEqual(set(row), set(row_schema["required"]))


if __name__ == "__main__":
    unittest.main()
