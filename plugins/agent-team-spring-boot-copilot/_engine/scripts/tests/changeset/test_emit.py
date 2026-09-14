"""The base-ref rule and the change set the arguments name, over a real repository."""

import contextlib
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from changeset.config import ChangeSetError
from changeset.emit import changeset_for, cmd_changeset, default_base
from changeset.git_facts import WORKTREE

SOME_COMMIT = "abc1234"
NO_GLOBS = ()


def arguments(base=None, head=WORKTREE, base_tree=None, name_only=False):
    return Namespace(base=base, head=head, base_tree=base_tree, name_only=name_only)


class DefaultBase(unittest.TestCase):
    def test_a_working_tree_head_defaults_to_head(self):
        self.assertEqual(default_base(arguments()), "HEAD")

    def test_an_explicit_base_is_kept(self):
        self.assertEqual(default_base(arguments(base="main")), "main")

    def test_a_committed_head_without_a_base_is_refused(self):
        with self.assertRaises(ChangeSetError):
            default_base(arguments(head=SOME_COMMIT))


class ChangeSetForArguments(unittest.TestCase):
    """A repository with one base commit, one later commit, and an edit in the working tree."""

    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo)
        cwd = Path.cwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, cwd)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        (self.repo / ".gitignore").write_text(".scratch/\n")
        (self.repo / "keep.txt").write_text("a\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.first = self.git("rev-parse", "HEAD")
        (self.repo / "keep.txt").write_text("b\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "second")
        self.second = self.git("rev-parse", "HEAD")
        (self.repo / "keep.txt").write_text("c\n")

    def git(self, *args):
        done = subprocess.run(
            ["git", *args], check=True, capture_output=True, text=True
        )
        return done.stdout.strip()

    def test_the_working_tree_diffs_against_head_by_default(self):
        changeset = changeset_for(arguments(), NO_GLOBS)

        self.assertEqual((changeset.base, changeset.tip), (self.second, self.second))
        self.assertEqual(changeset.head_kind, "worktree")
        self.assertNotEqual(changeset.head, self.git("rev-parse", "HEAD^{tree}"))

    def test_a_committed_range_narrows_its_base_to_the_merge_base(self):
        changeset = changeset_for(arguments(base=self.first, head="HEAD"), NO_GLOBS)

        self.assertEqual(changeset.merge_base, self.first)
        self.assertEqual((changeset.base, changeset.head), (self.first, self.second))
        self.assertEqual(changeset.head_kind, "commit")

    def test_a_tree_override_diffs_the_raw_tree_with_no_tip(self):
        tree = self.git("rev-parse", "HEAD^{tree}")

        changeset = changeset_for(arguments(base_tree=tree), NO_GLOBS)

        self.assertEqual((changeset.base, changeset.tip), (tree, None))
        self.assertTrue(changeset.resolved)

    def test_a_symbolic_tree_override_is_refused(self):
        with self.assertRaises(ChangeSetError):
            changeset_for(arguments(base_tree="HEAD"), NO_GLOBS)

    def test_an_unresolvable_base_leaves_the_set_unresolved(self):
        changeset = changeset_for(arguments(base="nope"), NO_GLOBS)

        self.assertIsNone(changeset.base)
        self.assertFalse(changeset.resolved)

    def test_the_emit_lists_the_changed_paths_with_name_only(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = cmd_changeset(arguments(name_only=True), NO_GLOBS)

        self.assertEqual(code, 0)
        self.assertEqual(stdout.getvalue().split(), ["keep.txt"])

    def test_the_emit_refuses_an_unresolvable_base(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = cmd_changeset(arguments(base="nope"), NO_GLOBS)

        self.assertEqual(code, 1)
        self.assertIn("unresolved", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
