"""The change set's git gateway: the exclude pathspecs, the ref hardening, and the canonical run."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from changeset.git_facts import exclude_pathspecs, resolve_ref, resolve_tree, run_git

SOME_GLOBS = ("vendor/**", "gen/*.generated")
LATIN1_BYTES = b"caf\xe9\n"


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


class RefHardening(unittest.TestCase):
    """The guards run before git; no repository is needed."""

    def test_a_dash_prefixed_ref_is_refused_before_git(self):
        self.assertIsNone(resolve_ref("--output=/tmp/pwned"))

    def test_an_empty_or_absent_ref_resolves_to_nothing(self):
        self.assertIsNone(resolve_ref(""))
        self.assertIsNone(resolve_ref(None))

    def test_a_symbolic_or_dash_prefixed_tree_name_is_refused(self):
        for bad in ("HEAD", "@{-1}", ":/regex", "-x", "main", "abc123", "z" * 40):
            with self.subTest(name=bad):
                self.assertIsNone(resolve_tree(bad))

    def test_a_non_string_tree_name_is_refused(self):
        self.assertIsNone(resolve_tree(None))
        self.assertIsNone(resolve_tree(1234))


if __name__ == "__main__":
    unittest.main()
