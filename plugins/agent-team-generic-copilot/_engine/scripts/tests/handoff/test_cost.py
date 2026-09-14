#!/usr/bin/env python3
"""The cost overlay: figures over one transcript index, degrading to none on any failure."""

import types
import unittest
import unittest.mock

import accounting
from handoff import (
    IMPLEMENTER,
    TranscriptOverlay,
    build_cost_lookup,
    cost as cost_module,
    seconds_of,
)

from tests.support import SOME_FIGURES, a_record, entries

SOME_START, SOME_END = 0.0, 600.0
SOME_AGENTS = [IMPLEMENTER, "code-quality-reviewer"]
SOME_TOTALS = {
    "total_input": 1_200_000,
    "output": 7_000,
    "cost": 2.5,
    "hit_pct": 88,
    "savings_pct": 71,
}
EARLIER_DISPATCH_TS = "2026-07-06T10:00:00Z"
LATER_DISPATCH_TS = "2026-07-06T10:05:00Z"


class FakeIndex:
    def __init__(self, totals=SOME_TOTALS, tiers=(IMPLEMENTER,)):
        self._totals = totals
        self._tiers = tiers

    def totals(self, _agent, _start, _end):
        return self._totals

    def slice_totals(self, _agents, _start, _end):
        return self._totals

    def window_types(self, _agent, _start, _end):
        return self._tiers


class FailingIndex:
    def totals(self, *_args):
        raise RuntimeError("no transcripts")

    slice_totals = totals
    window_types = totals


def an_overlay(index=None):
    return TranscriptOverlay(FakeIndex() if index is None else index, accounting)


def a_timed_dispatch(ts):
    return a_record("dispatch-start", author=IMPLEMENTER, ts=ts, responding_to=[0])


class WindowFigures(unittest.TestCase):
    def test_figures_are_formatted_in_the_cell_vocabulary(self):
        figures = an_overlay().window(IMPLEMENTER, SOME_START, SOME_END)

        self.assertEqual(figures, SOME_FIGURES)

    def test_missing_savings_omit_the_cell(self):
        totals = {
            key: value for key, value in SOME_TOTALS.items() if key != "savings_pct"
        }

        figures = an_overlay(FakeIndex(totals)).window(
            IMPLEMENTER, SOME_START, SOME_END
        )

        self.assertIsNone(figures.savings_pct)

    def test_an_empty_agent_yields_none(self):
        self.assertIsNone(an_overlay().window("", SOME_START, SOME_END))

    def test_empty_totals_yield_none(self):
        self.assertIsNone(
            an_overlay(FakeIndex({})).window(IMPLEMENTER, SOME_START, SOME_END)
        )

    def test_a_failing_index_yields_none(self):
        self.assertIsNone(
            an_overlay(FailingIndex()).window(IMPLEMENTER, SOME_START, SOME_END)
        )


class SliceFigures(unittest.TestCase):
    def test_the_authors_window_is_formatted(self):
        figures = an_overlay().slice_window(SOME_AGENTS, SOME_START, SOME_END)

        self.assertEqual(figures, SOME_FIGURES)

    def test_no_agents_yield_none(self):
        self.assertIsNone(an_overlay().slice_window([], SOME_START, SOME_END))

    def test_a_failing_index_yields_none(self):
        self.assertIsNone(
            an_overlay(FailingIndex()).slice_window(SOME_AGENTS, SOME_START, SOME_END)
        )


class WindowTypes(unittest.TestCase):
    def test_the_index_tiers_are_reported(self):
        self.assertEqual(
            an_overlay().window_types(SOME_START, SOME_END), (IMPLEMENTER,)
        )

    def test_a_failing_index_yields_none(self):
        self.assertIsNone(an_overlay(FailingIndex()).window_types(SOME_START, SOME_END))


class BuildingTheLookup(unittest.TestCase):
    def test_no_timed_dispatch_yields_none(self):
        log = entries(a_record("build-pass"), a_record("dispatch-start", ts=None))

        self.assertIsNone(build_cost_lookup(log))

    def test_a_missing_accounting_module_yields_none(self):
        log = entries(a_timed_dispatch(EARLIER_DISPATCH_TS))

        with unittest.mock.patch.object(cost_module, "accounting", None):
            self.assertIsNone(build_cost_lookup(log))

    def test_an_index_failure_yields_none(self):
        log = entries(a_timed_dispatch(EARLIER_DISPATCH_TS))

        def failing_index(_since_secs):
            raise OSError("no projects tree")

        fake = types.SimpleNamespace(WindowIndex=failing_index)
        with unittest.mock.patch.object(cost_module, "accounting", fake):
            self.assertIsNone(build_cost_lookup(log))

    def test_the_index_starts_at_the_earliest_dispatch(self):
        log = entries(
            a_timed_dispatch(LATER_DISPATCH_TS), a_timed_dispatch(EARLIER_DISPATCH_TS)
        )
        starts = []

        def recording_index(since_secs):
            starts.append(since_secs)
            return FakeIndex()

        fake = types.SimpleNamespace(WindowIndex=recording_index)
        with unittest.mock.patch.object(cost_module, "accounting", fake):
            lookup = build_cost_lookup(log)

        self.assertIsInstance(lookup, TranscriptOverlay)
        self.assertEqual(starts, [seconds_of(EARLIER_DISPATCH_TS)])


if __name__ == "__main__":
    unittest.main()
