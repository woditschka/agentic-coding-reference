"""Tests for changeset.emit — the change set's base-ref rule.

TestBaseDefault pins the base-ref defaulting rule the changeset verb and the
grader's extract/review-plan share. It injects a SimpleNamespace, so it runs
everywhere with no git or layout.toml.

Run (from the scripts dir): python3 -m unittest tests.changeset.test_emit
Stdlib only.
"""

import unittest
from types import SimpleNamespace

from changeset import emit


class TestBaseDefault(unittest.TestCase):
    """base defaults to HEAD only for the live worktree flow. A committed --head
    with no --base is rejected: the HEAD default would diff a commit against
    itself and silently emit an empty range — a real post-hoc regression."""

    def test_worktree_defaults_to_head(self):
        self.assertEqual(
            emit.base_arg(SimpleNamespace(base=None, head="WORKTREE")),
            ("HEAD", None),
        )

    def test_explicit_base_is_kept(self):
        self.assertEqual(
            emit.base_arg(SimpleNamespace(base="main", head="WORKTREE")),
            ("main", None),
        )

    def test_committed_head_without_base_errors(self):
        base, err = emit.base_arg(SimpleNamespace(base=None, head="abc1234"))
        self.assertIsNone(base)
        self.assertIsNotNone(err)


if __name__ == "__main__":
    unittest.main(verbosity=2)
