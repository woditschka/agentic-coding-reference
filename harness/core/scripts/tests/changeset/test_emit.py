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
from changeset.emit import (
    base_trees,
    changeset_for,
    changesets_for,
    cmd_changeset,
    default_base,
)
from changeset.git_facts import WORKTREE
from changeset.workspace import Member

SOME_COMMIT = "abc1234"
NO_GLOBS = ()
A_MEMBER_PATH = "../product-api"
A_TREE = "a" * 40
ANOTHER_TREE = "b" * 40


def a_member(key="api", path=A_MEMBER_PATH):
    return Member(key=key, path=path, stack="generic", contracts=(), depends_on=())


def arguments(base=None, head=WORKTREE, base_tree=None, name_only=False):
    return Namespace(base=base, head=head, base_tree=base_tree, name_only=name_only)


class BaseTrees(unittest.TestCase):
    def test_no_override_names_no_tree(self):
        self.assertEqual(dict(base_trees(arguments(), ())), {})

    def test_a_bare_tree_is_the_projects(self):
        self.assertEqual(
            dict(base_trees(arguments(base_tree=A_TREE), ())), {None: A_TREE}
        )

    def test_a_keyed_tree_is_the_members_and_may_join_the_projects(self):
        given = arguments(base_tree=[A_TREE, f"api={ANOTHER_TREE}"])
        self.assertEqual(
            dict(base_trees(given, (a_member(),))), {None: A_TREE, "api": ANOTHER_TREE}
        )

    def test_a_key_naming_no_declared_member_is_refused(self):
        with self.assertRaises(ChangeSetError):
            base_trees(arguments(base_tree=f"web={A_TREE}"), (a_member(),))

    def test_an_empty_tree_after_the_key_is_refused(self):
        with self.assertRaises(ChangeSetError):
            base_trees(arguments(base_tree="api="), (a_member(),))

    def test_a_repeated_bare_tree_is_refused(self):
        with self.assertRaises(ChangeSetError):
            base_trees(arguments(base_tree=[A_TREE, ANOTHER_TREE]), ())


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


class WorkspaceChangeSets(unittest.TestCase):
    """A project repository and one sibling member, each with a base commit and a working-tree edit."""

    def setUp(self):
        parent = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, parent)
        self.project = parent / "product"
        self.member = parent / "product-api"
        for repo, name in ((self.project, "keep.txt"), (self.member, "api.txt")):
            repo.mkdir()
            self.git(repo, "init", "-q")
            self.git(repo, "config", "user.email", "t@example.com")
            self.git(repo, "config", "user.name", "t")
            (repo / ".gitignore").write_text(".scratch/\n")
            (repo / name).write_text("a\n")
            self.git(repo, "add", "-A")
            self.git(repo, "commit", "-qm", "base")
            (repo / name).write_text("b\n")
        cwd = Path.cwd()
        os.chdir(self.project)
        self.addCleanup(os.chdir, cwd)

    def git(self, repo, *args):
        done = subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
        )
        return done.stdout.strip()

    def emitted(self, members, **kwargs):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = cmd_changeset(arguments(**kwargs), NO_GLOBS, members)
        self.assertEqual(code, 0)
        return stdout.getvalue()

    def test_a_present_member_adds_its_own_set_after_the_projects(self):
        sets = changesets_for(arguments(), NO_GLOBS, (a_member(),))

        self.assertEqual([c.member_path for c in sets], [None, A_MEMBER_PATH])
        self.assertTrue(all(c.resolved for c in sets))

    def test_an_absent_member_adds_no_set(self):
        sets = changesets_for(arguments(), NO_GLOBS, (a_member(path="../missing"),))

        self.assertEqual([c.member_path for c in sets], [None])

    def test_the_listing_spells_a_members_paths_from_the_project(self):
        out = self.emitted((a_member(),), name_only=True)

        self.assertEqual(out.split(), ["keep.txt", f"{A_MEMBER_PATH}/api.txt"])

    def test_the_diff_headers_spell_a_members_paths_from_the_project(self):
        out = self.emitted((a_member(),))

        self.assertIn("+++ b/keep.txt", out)
        self.assertIn(f"+++ b/{A_MEMBER_PATH}/api.txt", out)

    def test_an_exclude_glob_reaching_no_member_is_refused(self):
        with self.assertRaises(ChangeSetError):
            changesets_for(arguments(), ("../nobody/**",), (a_member(),))

    def test_a_keyed_tree_override_rebases_the_member_only(self):
        member_tree = self.git(self.member, "rev-parse", "HEAD^{tree}")

        sets = changesets_for(
            arguments(base_tree=[f"api={member_tree}"]), NO_GLOBS, (a_member(),)
        )

        self.assertEqual((sets[0].tip is not None, sets[1].tip), (True, None))
        self.assertEqual(sets[1].base, member_tree)


if __name__ == "__main__":
    unittest.main()
