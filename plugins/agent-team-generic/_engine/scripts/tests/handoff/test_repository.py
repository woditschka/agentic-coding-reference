#!/usr/bin/env python3
"""The git repository gateway, exercised against a throwaway repository."""

import os
import subprocess
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from handoff import (
    PRD_PATH,
    Baseline,
    GitRepository,
)

from tests.support import A_DESIGN_DOC

COMMIT_DATE = "2026-01-01T00:00:00Z"
COMMIT_SECONDS = 1_767_225_600.0
AN_ADR = "docs/adr/0001-x.md"
GIT_ENV = {
    **os.environ,
    "GIT_COMMITTER_DATE": COMMIT_DATE,
    "GIT_AUTHOR_DATE": COMMIT_DATE,
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
}


def git(*argv, env=None):
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *argv],
        check=True,
        env=env or GIT_ENV,
        capture_output=True,
        text=True,
    )


def write(path, text):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


class RepositoryCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.addCleanup(os.chdir, Path.cwd())
        os.chdir(self.root)
        self.repository = GitRepository()

    def seed_commit(self):
        write(A_DESIGN_DOC, "design\n")
        write(AN_ADR, "adr\n")
        write(PRD_PATH, "prd\n")
        git("init", "-q")
        git("add", ".")
        git("commit", "-q", "-m", "seed")


class State(RepositoryCase):
    def test_a_committed_repository_is_ok(self):
        self.seed_commit()

        self.assertEqual(self.repository.state(), "ok")

    def test_a_repository_without_a_commit_is_unborn(self):
        git("init", "-q")

        self.assertEqual(self.repository.state(), "unborn")

    def test_a_plain_directory_is_no_repository(self):
        self.assertEqual(self.repository.state(), "no-repo")

    def test_a_git_that_cannot_run_reads_as_none(self):
        with unittest.mock.patch.object(
            subprocess, "run", side_effect=OSError("no git")
        ):
            self.assertIsNone(self.repository.state())


class CommittedPrd(RepositoryCase):
    def test_the_prd_at_head_is_read_by_lines(self):
        self.seed_commit()
        write(PRD_PATH, "edited\n")

        self.assertEqual(self.repository.committed_prd_lines(), ["prd"])

    def test_a_prd_untracked_at_head_reads_as_empty(self):
        write(A_DESIGN_DOC, "design\n")
        git("init", "-q")
        git("add", ".")
        git("commit", "-q", "-m", "seed")
        write(PRD_PATH, "prd\n")

        self.assertEqual(self.repository.committed_prd_lines(), [])

    def test_a_nested_checkout_reads_its_own_prd(self):
        self.seed_commit()
        write("apps/svc/docs/prd.md", "nested prd\n")
        git("add", ".")
        git("commit", "-q", "-m", "svc")
        os.chdir(self.root / "apps" / "svc")

        self.assertEqual(self.repository.committed_prd_lines(), ["nested prd"])

    def test_no_repository_reads_as_none(self):
        self.assertIsNone(self.repository.committed_prd_lines())


class WorktreePrd(RepositoryCase):
    def test_a_present_prd_is_read(self):
        write(PRD_PATH, "prd\n")

        self.assertEqual(self.repository.worktree_prd_text(), "prd\n")

    def test_an_absent_prd_reads_as_empty(self):
        self.assertEqual(self.repository.worktree_prd_text(), "")

    def test_a_prd_at_the_size_cap_is_read(self):
        write(PRD_PATH, "prd\n")

        self.assertEqual(GitRepository(prd_size_cap=4).worktree_prd_text(), "prd\n")

    def test_a_prd_over_the_size_cap_reads_as_none(self):
        write(PRD_PATH, "prd\n")

        self.assertIsNone(GitRepository(prd_size_cap=3).worktree_prd_text())


class DirtyDesignDocs(RepositoryCase):
    def test_a_clean_tree_has_no_dirty_paths(self):
        self.seed_commit()

        self.assertEqual(self.repository.dirty_design_doc_paths(), [])

    def test_a_tracked_edit_an_untracked_file_and_an_ignored_file_are_all_dirty(self):
        self.seed_commit()
        write(A_DESIGN_DOC, "edited\n")
        write("docs/adr/0002-new.md", "new\n")
        write(".gitignore", "docs/adr/*-ignored.md\n")
        write("docs/adr/0003-ignored.md", "ignored\n")

        self.assertEqual(
            self.repository.dirty_design_doc_paths(),
            ["docs/adr/0002-new.md", "docs/adr/0003-ignored.md", A_DESIGN_DOC],
        )

    def test_the_prd_is_outside_the_audited_docs(self):
        self.seed_commit()
        write(PRD_PATH, "edited\n")

        self.assertEqual(self.repository.dirty_design_doc_paths(), [])

    def test_a_nested_checkout_reports_project_relative_paths(self):
        self.seed_commit()
        write("apps/svc/docs/system-design.md", "design\n")
        git("add", ".")
        git("commit", "-q", "-m", "svc")
        os.chdir(self.root / "apps" / "svc")
        write(A_DESIGN_DOC, "edited\n")

        self.assertEqual(self.repository.dirty_design_doc_paths(), [A_DESIGN_DOC])

    def test_no_repository_reads_as_none(self):
        self.assertIsNone(self.repository.dirty_design_doc_paths())


class DesignDocsBaseline(RepositoryCase):
    def test_the_last_commit_touching_the_docs_is_the_baseline(self):
        self.seed_commit()

        self.assertEqual(
            self.repository.design_docs_baseline(), Baseline(True, COMMIT_SECONDS)
        )

    def test_a_commit_elsewhere_does_not_move_the_baseline(self):
        self.seed_commit()
        write("unrelated.txt", "x\n")
        later = {
            **GIT_ENV,
            "GIT_COMMITTER_DATE": "2026-02-01T00:00:00Z",
            "GIT_AUTHOR_DATE": "2026-02-01T00:00:00Z",
        }
        git("add", ".", env=later)
        git("commit", "-q", "-m", "x", env=later)

        self.assertEqual(
            self.repository.design_docs_baseline(), Baseline(True, COMMIT_SECONDS)
        )

    def test_no_commit_touching_the_docs_is_readable_without_seconds(self):
        write("other.txt", "x\n")
        git("init", "-q")
        git("add", ".")
        git("commit", "-q", "-m", "seed")

        self.assertEqual(self.repository.design_docs_baseline(), Baseline(True, None))

    def test_no_repository_is_unreadable(self):
        self.assertEqual(self.repository.design_docs_baseline(), Baseline(False))


if __name__ == "__main__":
    unittest.main()
