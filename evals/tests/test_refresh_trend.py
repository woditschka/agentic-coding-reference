"""Tests for refresh_trend.py — the one-command trend refresh.

Pins the composition contract: the steps run in order, and a failing
step stops the chain with its exit code. Steps inject as parameters
(no patching); the real steps are summarize and render_figure, each
tested in its own suite."""

from __future__ import annotations

import unittest

import refresh_trend


class CompositionTest(unittest.TestCase):
    def test_steps_run_in_order(self) -> None:
        ran: list[str] = []
        rc = refresh_trend.main(
            [lambda: (ran.append("views"), 0)[1], lambda: (ran.append("figure"), 0)[1]]
        )
        self.assertEqual(rc, 0)
        self.assertEqual(ran, ["views", "figure"])

    def test_a_failing_step_stops_the_chain_with_its_code(self) -> None:
        ran: list[str] = []
        rc = refresh_trend.main(
            [lambda: (ran.append("views"), 3)[1], lambda: (ran.append("figure"), 0)[1]]
        )
        self.assertEqual(rc, 3)
        self.assertEqual(ran, ["views"])

    def test_the_default_steps_are_the_two_renderers(self) -> None:
        self.assertEqual(len(refresh_trend.default_steps()), 2)


if __name__ == "__main__":
    unittest.main()
