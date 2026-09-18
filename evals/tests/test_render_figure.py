"""Unit suite for the eval-trend figure generator: the trend-data.json contract,
the success-only cost arithmetic, the smoother, and the stamped subtitle."""

import datetime
import json
import unittest
from typing import Any

import render_figure
from render_figure import Cell, from_payload, render_figure as render

VERSIONS = ("v0.1.1", "v0.1.5", "v0.2.0")
FIRST, MIDDLE, LATEST = VERSIONS
UNMEASURED_VERSION = "v9.9.9"
FEATURE_TASK = "a-task"
REFUSAL_TASK = "r-task"
SOME_MODEL = "claude-opus-5"
OLD_MODELS = ["claude-opus-4-8", "claude-sonnet-4-6"]
NEW_MODELS = ["claude-opus-5", "claude-sonnet-5"]
SNAPSHOT_DATE = datetime.date(2026, 8, 21)
PANEL_COUNT = 5
# Midway between the first two of three equally spaced columns on the plot.
PIN_RULE_X_FOR_THREE_VERSIONS = 245.0
WALL_SECONDS = 600.0
DELIVERY_SECONDS = 570.0
DELIVERY_MINUTES = DELIVERY_SECONDS / render_figure.SECONDS_PER_MINUTE
CLEARING_SPEND = 9.0
FAILED_SPEND = 6.0
EARLY_SCORES = {"design_fit": 3, "doc_fit": 3}
LATE_SCORES = {"design_fit": 4, "doc_fit": 5}
RESCORED = {"design_fit": 5, "doc_fit": 4}
LOW_SCORE = 2


def a_rep(**overrides: Any) -> dict[str, Any]:
    rep: dict[str, Any] = {
        "task": FEATURE_TASK,
        "task_kind": "feature",
        "version": FIRST,
        "model_pin": "(default)",
        "models": [SOME_MODEL],
        "rep": 1,
        "cleared": True,
        "agent_spend_usd": CLEARING_SPEND,
        "spend_known": True,
        "wall_seconds": WALL_SECONDS,
        "delivery_wall_seconds": DELIVERY_SECONDS,
        "judge_facet_medians": None,
    }
    rep.update(overrides)
    rep["run_folder"] = f"runs/{rep['version']}/{rep['task']}-r{rep['rep']}"
    return rep


def a_refusal_rep(**overrides: Any) -> dict[str, Any]:
    return a_rep(task=REFUSAL_TASK, task_kind="refusal", **overrides)


PAYLOAD: dict[str, Any] = {
    "spec_version": "0.1.0",
    "versions": list(VERSIONS),
    "reps": [
        a_rep(judge_facet_medians=dict(EARLY_SCORES)),
        a_rep(rep=2, judge_facet_medians=dict(EARLY_SCORES)),
        a_rep(rep=3, cleared=False, agent_spend_usd=FAILED_SPEND),
        a_rep(version=MIDDLE, agent_spend_usd=11.0),
        a_rep(
            version=LATEST, agent_spend_usd=10.0, judge_facet_medians=dict(LATE_SCORES)
        ),
        a_refusal_rep(cleared=False, agent_spend_usd=20.0),
        a_refusal_rep(version=MIDDLE, agent_spend_usd=1.1),
        a_refusal_rep(version=LATEST, agent_spend_usd=1.0),
    ],
}


def payload_with(match: dict[str, Any], **changes: Any) -> dict[str, Any]:
    """PAYLOAD with every rep matching `match` updated by `changes`."""
    reps = [
        dict(rep, **changes) if all(rep[k] == v for k, v in match.items()) else rep
        for rep in PAYLOAD["reps"]
    ]
    return dict(PAYLOAD, reps=reps)


def first_line_with(text: str, needle: str) -> str:
    return next(line for line in text.splitlines() if needle in line)


class Payload(unittest.TestCase):
    def test_reps_aggregate_to_cells_and_refusal_kinds(self) -> None:
        data = from_payload(PAYLOAD)
        self.assertEqual(data.versions, VERSIONS)
        self.assertEqual(data.refusal_tasks, frozenset({REFUSAL_TASK}))
        self.assertEqual(
            data.cells[(FEATURE_TASK, FIRST)],
            Cell(
                2,
                3,
                2 * CLEARING_SPEND + FAILED_SPEND,
                FAILED_SPEND,
                wall=DELIVERY_MINUTES,
                burn=round(CLEARING_SPEND / DELIVERY_MINUTES, 3),
            ),
        )

    def test_success_cost_is_the_clearing_reps_mean_spend(self) -> None:
        cleared, spend, waste = 2, 24.0, 6.0
        self.assertEqual(
            Cell(cleared, 3, spend, waste).success_cost, (spend - waste) / cleared
        )
        self.assertIsNone(Cell(0, 1, FAILED_SPEND, FAILED_SPEND).success_cost)

    def test_quality_is_the_mean_per_facet_of_the_versions_judge_scores(self) -> None:
        data = from_payload(PAYLOAD)
        self.assertEqual(data.facets, tuple(EARLY_SCORES))
        for facet, early in EARLY_SCORES.items():
            self.assertEqual(
                data.quality[facet], [float(early), None, float(LATE_SCORES[facet])]
            )


class QualityPanel(unittest.TestCase):
    def test_the_panel_draws_one_labeled_raw_line_per_facet(self) -> None:
        text = render(from_payload(PAYLOAD), SNAPSHOT_DATE)
        self.assertIn('id="qline_design_fit"', text)
        self.assertIn('id="qline_doc_fit"', text)
        self.assertIn('id="qrl_design-fit"', text)
        self.assertIn('id="qrl_doc-fit"', text)
        # The middle version has no judged rep, so it draws no dot.
        self.assertNotIn(f'id="qd_design_fit_{VERSIONS.index(MIDDLE)}"', text)
        self.assertIn(f'id="qd_design_fit_{VERSIONS.index(LATEST)}"', text)

    def test_facets_keep_the_tables_order_and_an_unstyled_one_still_draws(self) -> None:
        reps = [
            dict(r, judge_facet_medians={"novel": 4, **r["judge_facet_medians"]})
            if r["judge_facet_medians"]
            else r
            for r in PAYLOAD["reps"]
        ]
        data = from_payload(dict(PAYLOAD, reps=reps))
        self.assertEqual(data.facets, (*EARLY_SCORES, "novel"))
        text = render(data, SNAPSHOT_DATE)
        self.assertIn('id="qline_novel"', text)
        self.assertIn('id="qrl_novel"', text)

    def test_facet_styles_follow_the_judge_roster(self) -> None:
        self.assertEqual(tuple(render_figure.FACET_STYLE), render_figure.JUDGE_FACETS)

    def test_the_quality_axis_is_the_rubrics_fixed_range(self) -> None:
        # The axis never zooms to the recorded means: a move reads at its
        # true share of the 1-5 scale whatever the lowest mean is.
        text = render(from_payload(PAYLOAD), SNAPSHOT_DATE)
        self.assertIn('id="ytC1"', text)
        self.assertIn('id="ytC3"', text)
        self.assertIn('id="ytC5"', text)
        low = render(
            from_payload(
                payload_with(
                    {"task": FEATURE_TASK, "version": FIRST, "rep": 1},
                    judge_facet_medians={"design_fit": LOW_SCORE, "doc_fit": 3},
                )
            ),
            SNAPSHOT_DATE,
        )
        self.assertIn('id="ytC1"', low)
        self.assertNotIn(f'id="ytC{LOW_SCORE}"', low)

    def test_a_facet_mean_averages_the_versions_judged_reps(self) -> None:
        data = from_payload(
            payload_with(
                {"task": FEATURE_TASK, "version": FIRST, "rep": 2},
                judge_facet_medians=dict(RESCORED),
            )
        )
        for facet, early in EARLY_SCORES.items():
            self.assertEqual(data.quality[facet][0], (early + RESCORED[facet]) / 2)


class KnownDefectLine(unittest.TestCase):
    """The reliability panel's known-defect clear rate: the share of probed reps
    clearing every named defect."""

    def _payload_with_probes(self) -> dict[str, Any]:
        reps = []
        for r in PAYLOAD["reps"]:
            if r["task"] != FEATURE_TASK:
                reps.append(dict(r, known_defects=None))
            elif r["version"] == FIRST:
                reps.append(dict(r, known_defects={"p": r["rep"] != 1}))
            else:
                reps.append(dict(r, known_defects={"p": False}))
        return dict(PAYLOAD, reps=reps)

    def test_a_payload_without_probes_draws_no_line_and_the_axis_runs_from_zero(
        self,
    ) -> None:
        data = from_payload(PAYLOAD)
        self.assertEqual(data.defect_clear, (None, None, None))
        text = render(data, SNAPSHOT_DATE)
        self.assertNotIn('id="dline"', text)
        self.assertIn('id="ytB0"', text)

    def test_the_clear_rate_is_the_probed_reps_share(self) -> None:
        data = from_payload(self._payload_with_probes())
        self.assertAlmostEqual(data.defect_clear[0] or 0.0, 100 / 3, places=1)
        self.assertEqual(data.defect_clear[2], 100.0)

    def test_the_rate_draws_in_the_reliability_panel_from_zero(self) -> None:
        text = render(from_payload(self._payload_with_probes()), SNAPSHOT_DATE)
        self.assertIn('id="dline"', text)
        self.assertIn('id="ytB0"', text)
        self.assertIn('id="ytC1"', text)
        self.assertIn(f'id="prl_{render_figure.DEFECT_LABEL}"', text)
        self.assertIn(f'id="prl_{render_figure.BAR_LABEL}"', text)
        self.assertIn("known-defect clear rate", text)


class WallPanel(unittest.TestCase):
    def test_a_cell_wall_is_the_clearing_reps_median_in_minutes(self) -> None:
        data = from_payload(PAYLOAD)
        self.assertEqual(data.cells[(FEATURE_TASK, FIRST)].wall, DELIVERY_MINUTES)

    def test_a_cell_burn_rate_is_the_median_per_rep_ratio(self) -> None:
        data = from_payload(PAYLOAD)
        self.assertEqual(
            data.cells[(FEATURE_TASK, FIRST)].burn,
            round(CLEARING_SPEND / DELIVERY_MINUTES, 3),
        )

    def test_a_refusal_cell_has_no_burn_rate(self) -> None:
        data = from_payload(PAYLOAD)
        self.assertIsNone(data.cells[(REFUSAL_TASK, MIDDLE)].burn)

    def test_the_burn_panel_mirrors_the_cost_encoding_without_the_refusal_line(
        self,
    ) -> None:
        text = render(from_payload(PAYLOAD), SNAPSHOT_DATE)
        self.assertIn('id="plE"', text)
        self.assertIn(f'id="btrend_{FEATURE_TASK}"', text)
        self.assertNotIn(f'id="bline_{REFUSAL_TASK}"', text)
        self.assertNotIn(f'id="brl_{REFUSAL_TASK}"', text)
        self.assertIn(f'id="brl_{FEATURE_TASK}"', text)

    def test_a_cell_without_a_clearing_rep_has_no_wall(self) -> None:
        self.assertIsNone(Cell(0, 1, FAILED_SPEND, FAILED_SPEND).wall)

    def test_the_panel_mirrors_the_cost_encoding(self) -> None:
        text = render(from_payload(PAYLOAD), SNAPSHOT_DATE)
        self.assertIn('id="plD"', text)
        self.assertIn(f'id="wtrend_{FEATURE_TASK}"', text)
        self.assertIn(f'id="wline_{REFUSAL_TASK}"', text)
        self.assertNotIn(f'id="wtrend_{REFUSAL_TASK}"', text)
        self.assertIn(f'id="wrl_{FEATURE_TASK}"', text)


class Hardening(unittest.TestCase):
    def test_a_declared_version_no_row_carries_is_dropped(self) -> None:
        payload = dict(PAYLOAD, versions=[*VERSIONS, UNMEASURED_VERSION])
        self.assertEqual(from_payload(payload).versions, VERSIONS)

    def test_a_series_with_no_clearing_rep_fails_loud(self) -> None:
        with self.assertRaises(ValueError):
            render(from_payload(payload_with({}, cleared=False)), SNAPSHOT_DATE)

    def test_a_rep_version_missing_from_the_axis_fails_loud(self) -> None:
        reps = [*PAYLOAD["reps"], a_rep(version=UNMEASURED_VERSION)]
        with self.assertRaises(ValueError):
            from_payload(dict(PAYLOAD, reps=reps))


class BoundMarker(unittest.TestCase):
    def test_a_lower_bound_cell_renders_a_hollow_dot(self) -> None:
        payload = payload_with(
            {"task": FEATURE_TASK, "version": LATEST}, spend_known=False
        )
        text = render(from_payload(payload), SNAPSHOT_DATE)
        hollow = first_line_with(
            text, f'id="d_{FEATURE_TASK}_{VERSIONS.index(LATEST)}"'
        )
        self.assertIn("fillColor=none", hollow)


ANCHORS = [(0.0, 1.0), (10.0, 5.0), (20.0, 2.0)]


class Interpolation(unittest.TestCase):
    def test_the_curve_passes_through_every_anchor(self) -> None:
        dense = render_figure.pchip(ANCHORS)
        for anchor in ANCHORS:
            self.assertIn(anchor, dense)

    def test_the_curve_never_overshoots_between_anchors(self) -> None:
        dense = render_figure.pchip(ANCHORS)
        ys = [y for _, y in dense]
        self.assertGreaterEqual(min(ys), min(y for _, y in ANCHORS))
        self.assertLessEqual(max(ys), max(y for _, y in ANCHORS))


class Smoother(unittest.TestCase):
    def test_the_line_starts_and_ends_exactly_on_the_data(self) -> None:
        rolled = render_figure.rolling_mean([1.0, 2.0, 3.0, 8.0])
        self.assertEqual(
            rolled, [(0, 1.0), (1, 2.0), (2, sum((2.0, 3.0, 8.0)) / 3), (3, 8.0)]
        )

    def test_a_missing_version_contributes_no_point(self) -> None:
        rolled = render_figure.rolling_mean([1.0, None, 3.0])
        self.assertEqual(rolled, [(0, 1.0), (2, 3.0)])

    def test_a_leading_gap_still_starts_on_the_recorded_cell(self) -> None:
        rolled = render_figure.rolling_mean([None, 2.0, 3.0, 8.0])
        self.assertEqual(rolled[0], (1, 2.0))
        self.assertEqual(rolled[-1], (3, 8.0))

    def test_a_point_beside_an_interior_gap_keeps_a_symmetric_window(self) -> None:
        rolled = render_figure.rolling_mean([1.0, None, 9.0, 3.0])
        self.assertEqual(rolled, [(0, 1.0), (2, 9.0), (3, 3.0)])


class RenderedFigure(unittest.TestCase):
    def test_the_subtitle_stamps_the_latest_version_and_date(self) -> None:
        text = render(from_payload(PAYLOAD), SNAPSHOT_DATE)
        self.assertIn(f"snapshot through {LATEST} ({SNAPSHOT_DATE.isoformat()})", text)

    def test_a_refusal_task_gets_a_dashed_raw_line_never_a_trend(self) -> None:
        text = render(from_payload(PAYLOAD), SNAPSHOT_DATE)
        self.assertIn(f"line_{REFUSAL_TASK}", text)
        self.assertNotIn(f"trend_{REFUSAL_TASK}", text)

    def test_the_trend_line_reaches_the_first_and_last_version(self) -> None:
        text = render(from_payload(PAYLOAD), SNAPSHOT_DATE)
        trend = first_line_with(text, f'id="trend_{FEATURE_TASK}"')
        self.assertIn(f'x="{render_figure.PLOT_LEFT}', trend)
        self.assertIn(f'x="{render_figure.PLOT_RIGHT}', trend)

    def test_attribute_values_and_ids_escape_the_quote(self) -> None:
        cell = render_figure.text_cell(
            'an"id', 'a "label"', "text;", render_figure.Box(0, 0, 10, 10)
        )
        self.assertNotIn('"an"id"', cell)
        self.assertIn("an&quot;id", cell)
        self.assertIn("a &quot;label&quot;", cell)

    def test_a_root_pin_change_draws_one_rule_with_a_derived_label(self) -> None:
        def repinned(rep: dict[str, Any]) -> dict[str, Any]:
            models = OLD_MODELS if rep["version"] == FIRST else NEW_MODELS
            return dict(rep, model_pin=models[0], models=list(models))

        data = from_payload(
            dict(PAYLOAD, reps=[repinned(rep) for rep in PAYLOAD["reps"]])
        )
        self.assertEqual(data.pin_boundaries, (VERSIONS.index(MIDDLE),))
        text = render(data, SNAPSHOT_DATE)
        self.assertEqual(text.count('id="pin0'), PANEL_COUNT)
        self.assertEqual(text.count('id="pinlabel0"'), 1)
        self.assertNotIn('id="pin1', text)
        label = first_line_with(text, 'id="pinlabel0"')
        short_names = " · ".join(m.removeprefix("claude-") for m in NEW_MODELS)
        self.assertIn(f"models → {short_names}", label)
        # Solid ground over the grid keeps the label legible.
        self.assertIn("fillColor=#FFFFFF", label)
        rule = first_line_with(text, 'id="pin0a"')
        self.assertIn(f'x="{PIN_RULE_X_FOR_THREE_VERSIONS}"', rule)

    def test_a_uniform_pin_draws_no_rule(self) -> None:
        text = render(from_payload(PAYLOAD), SNAPSHOT_DATE)
        self.assertNotIn('id="pin0', text)
        self.assertNotIn("models →", text)

    def test_a_cell_without_a_clearing_rep_renders_no_dot(self) -> None:
        text = render(from_payload(PAYLOAD), SNAPSHOT_DATE)
        self.assertNotIn(f"d_{REFUSAL_TASK}_{VERSIONS.index(FIRST)}", text)
        self.assertIn(f"d_{REFUSAL_TASK}_{VERSIONS.index(MIDDLE)}", text)
        self.assertIn(f"d_{REFUSAL_TASK}_{VERSIONS.index(LATEST)}", text)


class LiveTree(unittest.TestCase):
    SCHEMA = render_figure.HERE / "trend-data.schema.json"

    def test_the_committed_data_view_loads_and_renders(self) -> None:
        payload = json.loads(render_figure.TREND_DATA.read_text(encoding="utf-8"))
        data = from_payload(payload)
        self.assertGreaterEqual(len(data.versions), 1)
        text = render(data, SNAPSHOT_DATE)
        self.assertIn("cost of a clearing rep", text)

    def test_the_committed_data_view_conforms_to_its_schema(self) -> None:
        # The schema's required lists are the oracle: every row carries
        # exactly the contract's fields.
        schema = json.loads(self.SCHEMA.read_text(encoding="utf-8"))
        payload = json.loads(render_figure.TREND_DATA.read_text(encoding="utf-8"))
        self.assertEqual(set(payload), set(schema["required"]))
        row_schema = schema["properties"]["reps"]["items"]
        for row in payload["reps"]:
            self.assertEqual(set(row), set(row_schema["required"]))


if __name__ == "__main__":
    unittest.main()
