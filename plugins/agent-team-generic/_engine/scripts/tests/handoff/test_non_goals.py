#!/usr/bin/env python3
"""The PRD's Non-Goals table and the rows changed against HEAD."""

import unittest

from handoff import (
    changed_rows,
    ng_rows,
    non_goal_delta,
)

from tests.support import FakeRepository

A_ROW = "| NG-4 | Deleting a record | Stated reason |"
ANOTHER_ROW = "| NG-5 | Changing a record | Stated reason |"
A_HEADER = "| ID | Non-Goal | Rationale |"


class NgRows(unittest.TestCase):
    def test_rows_are_keyed_by_their_id(self):
        self.assertEqual(
            ng_rows(f"{A_HEADER}\n{A_ROW}\n{ANOTHER_ROW}\n"),
            {"NG-4": A_ROW, "NG-5": ANOTHER_ROW},
        )

    def test_up_to_three_leading_spaces_still_render_as_a_row(self):
        self.assertEqual(ng_rows(f"   {A_ROW}"), {"NG-4": A_ROW})

    def test_four_leading_spaces_are_not_a_row(self):
        self.assertEqual(ng_rows(f"    {A_ROW}"), {})

    def test_the_header_and_prose_are_not_rows(self):
        self.assertEqual(ng_rows(f"{A_HEADER}\nNG-4 is out of scope\n"), {})


class ChangedRows(unittest.TestCase):
    def test_identical_tables_change_nothing(self):
        self.assertEqual(changed_rows(A_ROW, A_ROW), ())

    def test_a_reworded_row_is_changed(self):
        self.assertEqual(
            changed_rows(A_ROW, A_ROW.replace("Deleting", "Cancelling")), ("NG-4",)
        )

    def test_a_removed_row_is_changed(self):
        self.assertEqual(changed_rows(f"{A_ROW}\n{ANOTHER_ROW}", A_ROW), ("NG-5",))

    def test_an_added_row_is_free(self):
        self.assertEqual(changed_rows(A_ROW, f"{A_ROW}\n{ANOTHER_ROW}"), ())

    def test_changed_ids_are_sorted(self):
        self.assertEqual(changed_rows(f"{ANOTHER_ROW}\n{A_ROW}", ""), ("NG-4", "NG-5"))


class NonGoalDelta(unittest.TestCase):
    def test_a_repository_git_cannot_read_fails_closed(self):
        self.assertIsNone(non_goal_delta(FakeRepository(repo_state=None)))

    def test_no_repository_has_no_delta(self):
        self.assertEqual(non_goal_delta(FakeRepository(repo_state="no-repo")), ())

    def test_a_repository_without_a_commit_has_no_delta(self):
        self.assertEqual(non_goal_delta(FakeRepository(repo_state="unborn")), ())

    def test_an_unreadable_committed_prd_fails_closed(self):
        self.assertIsNone(non_goal_delta(FakeRepository(prd_lines=None)))

    def test_an_unreadable_worktree_prd_fails_closed(self):
        self.assertIsNone(non_goal_delta(FakeRepository(prd_text=None)))

    def test_the_delta_compares_head_against_the_worktree(self):
        repository = FakeRepository(
            prd_lines=[A_HEADER, A_ROW, ANOTHER_ROW], prd_text=f"{A_HEADER}\n{A_ROW}\n"
        )

        self.assertEqual(non_goal_delta(repository), ("NG-5",))


if __name__ == "__main__":
    unittest.main()
