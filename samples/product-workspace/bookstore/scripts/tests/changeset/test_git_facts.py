"""The change set's git gateway: the exclude pathspecs, the ref hardening, and the canonical run."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from changeset.git_facts import (
    diff_prefix_options,
    exclude_pathspecs,
    globs_for,
    prefix_listing,
    prefix_numstat,
    resolve_ref,
    resolve_tree,
    run_git,
    snapshot_worktree,
)

SOME_GLOBS = ("vendor/**", "gen/*.generated")
A_MEMBER_PATH = "../product-api"
A_MEMBER_PREFIX = f"{A_MEMBER_PATH}/"
A_MEMBER_GLOB = f"{A_MEMBER_PREFIX}gen/**"
LATIN1_BYTES = b"caf\xe9\n"
SHA_LENGTH = 40
A_NON_STRING = 1234


class ExcludePathspecs(unittest.TestCase):
    def test_no_globs_yield_no_pathspec(self):
        self.assertEqual(exclude_pathspecs(()), [])

    def test_globs_become_top_level_exclude_pathspecs(self):
        self.assertEqual(
            exclude_pathspecs(SOME_GLOBS),
            [
                "--",
                ":(top)",
                ":(top,glob,exclude)vendor/**",
                ":(top,glob,exclude)gen/*.generated",
            ],
        )


class Repository(unittest.TestCase):
    """A repository whose second commit changes a kept file, a vendored file, and a Latin-1 file."""

    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo)
        cwd = Path.cwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, cwd)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        (self.repo / "keep.txt").write_text("a\n")
        (self.repo / "vendor").mkdir()
        (self.repo / "vendor" / "lib.txt").write_text("a\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        (self.repo / "keep.txt").write_text("b\n")
        (self.repo / "vendor" / "lib.txt").write_text("b\n")
        (self.repo / "latin1.txt").write_bytes(LATIN1_BYTES)
        self.git("add", "-A")
        self.git("commit", "-qm", "change")

    def git(self, *args):
        subprocess.run(["git", *args], check=True, capture_output=True, text=True)

    def changed_names(self, globs):
        out = run_git(
            "diff", "--name-only", "HEAD~1", "HEAD", *exclude_pathspecs(globs)
        )
        return out.split()

    def test_no_globs_show_every_changed_path(self):
        self.assertEqual(
            self.changed_names(()), ["keep.txt", "latin1.txt", "vendor/lib.txt"]
        )

    def test_a_glob_drops_its_paths_and_keeps_the_rest(self):
        self.assertEqual(self.changed_names(("vendor/**",)), ["keep.txt", "latin1.txt"])

    def test_output_in_another_encoding_is_replaced_never_fatal(self):
        self.assertEqual(run_git("show", "HEAD:latin1.txt"), "caf�\n")

    def test_a_failing_command_raises_with_its_stderr(self):
        with self.assertRaises(RuntimeError) as raised:
            run_git("rev-parse", "--verify", "nope")

        self.assertIn("nope", str(raised.exception))


class PathSpelling(unittest.TestCase):
    """How a member's paths are spelled from the project, and which globs reach its repository."""

    def test_the_project_keeps_only_the_globs_that_stay_inside_it(self):
        self.assertEqual(globs_for((*SOME_GLOBS, A_MEMBER_GLOB), ""), SOME_GLOBS)

    def test_a_member_keeps_its_own_globs_spelled_relative_to_itself(self):
        self.assertEqual(
            globs_for((*SOME_GLOBS, A_MEMBER_GLOB), A_MEMBER_PREFIX), ("gen/**",)
        )

    def test_a_wildcard_member_segment_reaches_the_member_it_matches(self):
        self.assertEqual(
            globs_for(("../product-*/gen/**",), A_MEMBER_PREFIX), ("gen/**",)
        )
        self.assertEqual(globs_for(("../other-*/gen/**",), A_MEMBER_PREFIX), ())

    def test_a_glob_naming_only_the_member_applies_to_nothing_inside_it(self):
        self.assertEqual(globs_for(("../product-api",), A_MEMBER_PREFIX), ())

    def test_the_project_adds_no_diff_options(self):
        self.assertEqual(diff_prefix_options(""), [])

    def test_a_member_spells_both_header_sides_under_its_path(self):
        self.assertEqual(
            diff_prefix_options(A_MEMBER_PREFIX),
            [f"--src-prefix=a/{A_MEMBER_PREFIX}", f"--dst-prefix=b/{A_MEMBER_PREFIX}"],
        )

    def test_a_listing_gains_the_prefix_on_every_path(self):
        self.assertEqual(
            prefix_listing("a.txt\nsrc/b.txt\n", A_MEMBER_PREFIX),
            f"{A_MEMBER_PREFIX}a.txt\n{A_MEMBER_PREFIX}src/b.txt\n",
        )

    def test_a_numstat_gains_the_prefix_on_its_path_column_only(self):
        self.assertEqual(
            prefix_numstat("3\t1\tsrc/b.txt\n-\t-\tblob.bin\n", A_MEMBER_PREFIX),
            f"3\t1\t{A_MEMBER_PREFIX}src/b.txt\n-\t-\t{A_MEMBER_PREFIX}blob.bin\n",
        )

    def test_an_empty_prefix_returns_every_listing_unchanged(self):
        self.assertEqual(prefix_listing("a.txt\n", ""), "a.txt\n")
        self.assertEqual(prefix_numstat("3\t1\ta.txt\n", ""), "3\t1\ta.txt\n")


class MemberRepository(unittest.TestCase):
    """A project repository with a sibling member repository beside it; the process runs in the project."""

    def setUp(self):
        parent = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, parent)
        self.project = parent / "product"
        self.member = parent / "product-api"
        for repo in (self.project, self.member):
            repo.mkdir()
            self.git(repo, "init", "-q")
            self.git(repo, "config", "user.email", "t@example.com")
            self.git(repo, "config", "user.name", "t")
            (repo / "keep.txt").write_text("a\n")
            self.git(repo, "add", "-A")
            self.git(repo, "commit", "-qm", "base")
        cwd = Path.cwd()
        os.chdir(self.project)
        self.addCleanup(os.chdir, cwd)

    def git(self, repo, *args):
        done = subprocess.run(
            ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
        )
        return done.stdout.strip()

    def test_a_root_runs_the_command_in_the_member_not_the_project(self):
        (self.member / "api.txt").write_text("x\n")
        self.git(self.member, "add", "-A")
        self.git(self.member, "commit", "-qm", "api")

        names = run_git(
            "diff", "--name-only", "HEAD~1", "HEAD", root=Path(A_MEMBER_PATH)
        )

        self.assertEqual(names.split(), ["api.txt"])

    def test_a_member_snapshot_is_its_own_tree_and_leaves_its_index_alone(self):
        (self.member / "new.txt").write_text("x\n")

        tree = snapshot_worktree(Path(A_MEMBER_PATH))

        self.assertNotEqual(tree, self.git(self.member, "rev-parse", "HEAD^{tree}"))
        self.assertEqual(self.git(self.member, "status", "--porcelain"), "?? new.txt")
        self.assertFalse(list((self.project / ".scratch" / "tmp").glob("*.index")))


class RefHardening(unittest.TestCase):
    """The guards run before git; no repository is needed."""

    def test_a_dash_prefixed_ref_is_refused_before_git(self):
        self.assertIsNone(resolve_ref("--output=/tmp/out"))

    def test_an_empty_or_absent_ref_resolves_to_nothing(self):
        self.assertIsNone(resolve_ref(""))
        self.assertIsNone(resolve_ref(None))

    def test_a_symbolic_or_dash_prefixed_tree_name_is_refused(self):
        for bad in (
            "HEAD",
            "@{-1}",
            ":/regex",
            "-x",
            "main",
            "abc123",
            "z" * SHA_LENGTH,
        ):
            with self.subTest(name=bad):
                self.assertIsNone(resolve_tree(bad))

    def test_a_non_string_tree_name_is_refused(self):
        self.assertIsNone(resolve_tree(None))
        self.assertIsNone(resolve_tree(A_NON_STRING))


if __name__ == "__main__":
    unittest.main()
