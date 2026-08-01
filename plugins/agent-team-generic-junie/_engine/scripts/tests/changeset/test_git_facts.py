"""Tests for changeset.git_facts — the change-set git gateway.

The exclude-pathspec classes inject a synthetic exclude filter into
changeset.config: the pathspec builder is a pure function of the exclude globs,
and the end-to-end class proves those pathspecs actually drop files from a real
(synthetic) git diff. TestRefHardening exercises the untrusted-ref guards
(resolve_ref, resolve_tree) that reject option-injection and symbolic revisions
before any value reaches git argv — the trust-boundary defense the review
plan's agent-authored tree_sha leans on.

Run (from the scripts dir): python3 -m unittest tests.changeset.test_git_facts
Stdlib only.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from changeset import config, git_facts


def _inject_exclude(case, globs):
    saved = config.layout
    config.layout = SimpleNamespace(EXCLUDE=globs)
    case.addCleanup(lambda: setattr(config, "layout", saved))


class TestExcludePathspecs(unittest.TestCase):
    """exclude_globs becomes git exclude pathspecs applied to every diff the
    change set is read through (numstat, unified, name-only), so the reviewer's
    view through changeset.sh and the grader's row drop the same paths. An empty
    list yields no pathspec — the whole diff."""

    def test_empty_yields_no_pathspec(self):
        _inject_exclude(self, [])
        self.assertEqual(git_facts.exclude_pathspecs(), [])

    def test_globs_become_exclude_pathspecs(self):
        _inject_exclude(self, ["vendor/**", "gen/*.generated"])
        # Repo-root-relative (:(top)) so the change set is cwd-independent, with
        # glob magic so '**' crosses directories as layout.toml documents.
        self.assertEqual(
            git_facts.exclude_pathspecs(),
            [
                "--",
                ":(top)",
                ":(top,glob,exclude)vendor/**",
                ":(top,glob,exclude)gen/*.generated",
            ],
        )


class TestExcludeBehaviorEndToEnd(unittest.TestCase):
    """The exclude pathspecs actually drop matching files from a real git diff —
    the coverage a string-construction check misses. Guards against cwd-relativity
    and glob-semantics regressions in exclude_pathspecs feeding real git."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)

        def git(*a):
            subprocess.run(
                ["git", "-C", str(self.dir), *a],
                check=True,
                capture_output=True,
                text=True,
            )

        git("init", "-q")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "t")
        (self.dir / "keep.txt").write_text("a\n")
        (self.dir / "vendor").mkdir()
        (self.dir / "vendor" / "lib.txt").write_text("a\n")
        git("add", "-A")
        git("commit", "-qm", "base")
        (self.dir / "keep.txt").write_text("b\n")
        (self.dir / "vendor" / "lib.txt").write_text("b\n")
        git("add", "-A")
        git("commit", "-qm", "change")

    def _names_with_exclude(self, globs):
        _inject_exclude(self, globs)
        out = subprocess.run(
            [
                "git",
                "-C",
                str(self.dir),
                "diff",
                "--name-only",
                "HEAD~1",
                "HEAD",
                *git_facts.exclude_pathspecs(),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return out.split()

    def test_no_exclude_shows_all(self):
        self.assertEqual(
            sorted(self._names_with_exclude([])), ["keep.txt", "vendor/lib.txt"]
        )

    def test_exclude_drops_matching_and_keeps_rest(self):
        names = self._names_with_exclude(["vendor/**"])
        self.assertIn("keep.txt", names)
        self.assertNotIn("vendor/lib.txt", names)


class TestRefHardening(unittest.TestCase):
    """The untrusted-ref guards reject option-injection and symbolic revisions
    before any value reaches git argv. A review-plan's tree_sha is agent-authored
    (the handoff-log schema types it as a bare string, no hex enforcement), so a
    '-'-prefixed ref could smuggle a git option and a symbolic revision
    (HEAD, @{-1}, :/regex) could diff the fix delta against an attacker-chosen
    tree and under-scope the roster. These guards reject BEFORE calling git, so
    the tests need no repository."""

    def test_resolve_ref_rejects_option_injection(self):
        # A '-'-prefixed value cannot name a real commit; it could only smuggle a
        # git option into the argument list. Rejected without touching git.
        self.assertIsNone(git_facts.resolve_ref("-x"))
        self.assertIsNone(git_facts.resolve_ref("--output=/tmp/pwned"))

    def test_resolve_ref_rejects_empty_and_none(self):
        self.assertIsNone(git_facts.resolve_ref(""))
        self.assertIsNone(git_facts.resolve_ref(None))

    def test_resolve_tree_rejects_symbolic_and_injection(self):
        # Only a bare 40/64-hex object name is accepted: a symbolic revision
        # would diff against an attacker-chosen tree; a '-' prefix would smuggle
        # an option. Every one of these is non-hex, so it is rejected pre-git.
        for bad in ("HEAD", "@{-1}", ":/regex", "-x", "main", "abc123", "z" * 40):
            self.assertIsNone(git_facts.resolve_tree(bad), bad)

    def test_resolve_tree_rejects_non_str(self):
        self.assertIsNone(git_facts.resolve_tree(None))
        self.assertIsNone(git_facts.resolve_tree(1234))


if __name__ == "__main__":
    unittest.main(verbosity=2)
