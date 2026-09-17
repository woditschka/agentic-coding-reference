"""Unit suite for the one-command trend refresh's step composition."""

import unittest
from collections.abc import Callable

import refresh_trend

VIEWS_STEP = "views"
FIGURE_STEP = "figure"
SOME_FAILURE_CODE = 3


def a_step(ran: list[str], name: str, code: int = 0) -> Callable[[], int]:
    def step() -> int:
        ran.append(name)
        return code

    return step


class Composition(unittest.TestCase):
    def test_steps_run_in_order(self) -> None:
        ran: list[str] = []
        rc = refresh_trend.main([a_step(ran, VIEWS_STEP), a_step(ran, FIGURE_STEP)])
        self.assertEqual(rc, 0)
        self.assertEqual(ran, [VIEWS_STEP, FIGURE_STEP])

    def test_a_failing_step_stops_the_chain_with_its_code(self) -> None:
        ran: list[str] = []
        rc = refresh_trend.main(
            [a_step(ran, VIEWS_STEP, SOME_FAILURE_CODE), a_step(ran, FIGURE_STEP)]
        )
        self.assertEqual(rc, SOME_FAILURE_CODE)
        self.assertEqual(ran, [VIEWS_STEP])

    def test_the_default_steps_are_the_two_renderers(self) -> None:
        self.assertEqual(len(refresh_trend.default_steps()), 2)


if __name__ == "__main__":
    unittest.main()
