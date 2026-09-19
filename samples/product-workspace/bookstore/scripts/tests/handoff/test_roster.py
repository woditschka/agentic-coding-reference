#!/usr/bin/env python3
"""The reviewer roster from the layout, the auto-grade switch, and the pass roster from the active plan."""

import unittest

from handoff import (
    PLAN_ENGINE,
    PLANNER,
    ROSTER_FLOOR,
    PassRoster,
    PlannerStep,
    RosterResult,
    active_plan,
    auto_grade,
    pass_roster,
    reviewer_roster,
)

from tests.support import a_record, entries

FLOOR = tuple(ROSTER_FLOOR)
FIRST, SECOND = FLOOR[0], FLOOR[1]
EXTRA = "compliance-reviewer"
OUTSIDER = "someone-else"
BUILD_PASS_LINE = 1
GRAY_PLAN_LINE = BUILD_PASS_LINE + 1
PLANNER_PLAN_LINE = GRAY_PLAN_LINE + 1
A_NON_NAME = 3
MALFORMED_ROSTER_ERROR = (
    "harness.extra_reviewers in scripts/layout.toml must be a list of reviewer names"
)


def layout(**harness):
    return {"harness": harness}


def a_build_pass():
    return a_record("build-pass")


def a_plan(author=PLAN_ENGINE, risk="low", roster=(FIRST,), **fields):
    return a_record(
        "review-plan", author=author, risk=risk, roster=list(roster), **fields
    )


def a_gray_plan(author=PLAN_ENGINE):
    return a_record("review-plan", author=author, risk="gray")


def a_planner_start():
    return a_record("dispatch-start", author=PLANNER)


def roster_after(*raws):
    return pass_roster(entries(a_build_pass(), *raws), BUILD_PASS_LINE, FLOOR)


class ReviewerRoster(unittest.TestCase):
    def test_no_declaration_is_the_floor(self):
        self.assertEqual(reviewer_roster({}), RosterResult(FLOOR))

    def test_extras_join_the_floor_in_declared_order_without_duplicates(self):
        result = reviewer_roster(layout(extra_reviewers=[EXTRA, FIRST, EXTRA]))

        self.assertEqual(result, RosterResult((*FLOOR, EXTRA)))

    def test_a_non_list_declaration_is_an_error(self):
        result = reviewer_roster(layout(extra_reviewers=EXTRA))

        self.assertEqual(result, RosterResult(None, MALFORMED_ROSTER_ERROR))

    def test_a_list_with_a_non_name_is_an_error(self):
        for extras in ([""], [EXTRA, A_NON_NAME]):
            with self.subTest(extras=extras):
                self.assertEqual(
                    reviewer_roster(layout(extra_reviewers=extras)),
                    RosterResult(None, MALFORMED_ROSTER_ERROR),
                )


class AutoGrade(unittest.TestCase):
    def test_only_an_explicit_false_turns_grading_off(self):
        self.assertFalse(auto_grade(layout(auto_grade=False)))

    def test_absent_true_or_a_non_bool_keep_grading_on(self):
        for value in ({}, layout(auto_grade=True), layout(auto_grade="no")):
            with self.subTest(layout=value):
                self.assertTrue(auto_grade(value))


class ActivePlan(unittest.TestCase):
    def test_the_latest_plan_after_the_build_pass_is_active(self):
        build_pass_line = 2
        log = entries(
            a_plan(roster=(SECOND,)), a_build_pass(), a_plan(), a_plan(roster=(SECOND,))
        )

        found = active_plan(log, build_pass_line)

        self.assertIsNotNone(found)
        self.assertEqual(found[0].no, len(log))
        self.assertEqual(found[1].roster, (SECOND,))

    def test_a_plan_before_the_build_pass_is_not_active(self):
        log = entries(a_plan(), a_build_pass())

        self.assertIsNone(active_plan(log, len(log)))


class PassRosterFromPlan(unittest.TestCase):
    def test_no_plan_fails_closed_to_the_full_roster(self):
        self.assertEqual(roster_after(), PassRoster(FLOOR, "no-plan"))

    def test_an_engine_plan_narrows_to_its_roster_in_roster_order(self):
        self.assertEqual(
            roster_after(a_plan(roster=(SECOND, FIRST))), PassRoster((FIRST, SECOND))
        )

    def test_a_plan_naming_an_outsider_fails_closed(self):
        self.assertEqual(
            roster_after(a_plan(roster=(FIRST, OUTSIDER))),
            PassRoster(FLOOR, "invalid-plan"),
        )

    def test_an_empty_engine_roster_fails_closed(self):
        self.assertEqual(
            roster_after(a_plan(roster=())), PassRoster(FLOOR, "invalid-plan")
        )

    def test_a_plan_from_an_unknown_author_fails_closed(self):
        self.assertEqual(
            roster_after(a_plan(author=OUTSIDER)), PassRoster(FLOOR, "unauthored-plan")
        )


class GrayPlanLadder(unittest.TestCase):
    def test_an_engine_deferral_dispatches_the_planner(self):
        self.assertEqual(
            roster_after(a_gray_plan()), PlannerStep("plan-gray", GRAY_PLAN_LINE)
        )

    def test_a_gray_plan_from_anyone_else_is_invalid(self):
        self.assertEqual(
            roster_after(a_gray_plan(author=PLANNER)),
            PlannerStep("plan-gray-invalid", GRAY_PLAN_LINE),
        )

    def test_one_silent_planner_start_retries_once(self):
        self.assertEqual(
            roster_after(a_gray_plan(), a_planner_start()),
            PlannerStep("planner-stall-retry", GRAY_PLAN_LINE),
        )

    def test_two_silent_planner_starts_stall(self):
        self.assertEqual(
            roster_after(a_gray_plan(), a_planner_start(), a_planner_start()),
            PlannerStep("planner-stalled", GRAY_PLAN_LINE),
        )


class PlannerPlan(unittest.TestCase):
    def test_a_planner_plan_after_a_deferral_narrows_the_roster(self):
        self.assertEqual(
            roster_after(a_gray_plan(), a_plan(author=PLANNER, roster=(SECOND,))),
            PassRoster((SECOND,)),
        )

    def test_a_planner_plan_without_a_deferral_fails_closed(self):
        self.assertEqual(
            roster_after(a_plan(author=PLANNER)), PassRoster(FLOOR, "unauthored-plan")
        )

    def test_a_deferral_from_an_earlier_pass_does_not_invite_the_plan(self):
        build_pass_line = 2
        log = entries(a_gray_plan(), a_build_pass(), a_plan(author=PLANNER))

        self.assertEqual(
            pass_roster(log, build_pass_line, FLOOR),
            PassRoster(FLOOR, "unauthored-plan"),
        )

    def test_a_roster_less_planner_plan_is_bounced_once(self):
        self.assertEqual(
            roster_after(a_gray_plan(), a_plan(author=PLANNER, roster=())),
            PlannerStep("plan-roster-invalid", PLANNER_PLAN_LINE),
        )

    def test_a_second_roster_less_planner_plan_fails_closed(self):
        self.assertEqual(
            roster_after(
                a_gray_plan(),
                a_plan(author=PLANNER, roster=()),
                a_plan(author=PLANNER, roster=()),
            ),
            PassRoster(FLOOR, "invalid-plan"),
        )


if __name__ == "__main__":
    unittest.main()
