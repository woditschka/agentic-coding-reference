"""Read the project's repository state the ledger gates need: the PRD at HEAD and in the tree, the dirty design docs.

A leaf over the standard library; `git` runs against the current working directory. Every
read answers None when the repository cannot be read, and the callers fail closed on it.
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, TypeAlias

from .timestamps import parse_iso_seconds

RepositoryState: TypeAlias = Literal["ok", "no-repo", "unborn"]

PRD_PATH = "docs/prd.md"
ADR_INDEX = "docs/adr/README.md"
AUDITED_DOCS = ("docs/system-design.md", "docs/adr/")
# A pathological PRD fails the route-time scope-lock closed instead of loading.
PRD_SIZE_CAP = 4_000_000


@dataclass(frozen=True, slots=True)
class Baseline:
    """The last commit touching the audited docs: whether it could be read, and its seconds."""

    readable: bool
    seconds: float | None = None


class Repository(Protocol):
    """The repository reads the append gates, the scope lock, and the autofix audit make."""

    def state(self) -> RepositoryState | None:
        """Return whether HEAD exists; None when git cannot run."""
        ...

    def committed_prd_lines(self) -> list[str] | None:
        """Return the PRD's lines at HEAD, empty when HEAD holds no PRD, None when git fails."""
        ...

    def worktree_prd_text(self) -> str | None:
        """Return the working PRD's text, empty when absent, None when unreadable or oversized."""
        ...

    def dirty_design_doc_paths(self) -> list[str] | None:
        """Return every uncommitted design-doc path, tracked, untracked, or ignored; None when git fails."""
        ...

    def design_docs_baseline(self) -> Baseline:
        """Return the last commit touching the audited docs."""
        ...


@dataclass(frozen=True, slots=True)
class GitRepository:
    """The repository read through `git` from the current working directory."""

    prd_size_cap: int = PRD_SIZE_CAP

    def state(self) -> RepositoryState | None:
        """Return "ok", "no-repo", or "unborn"; None when git cannot run."""
        try:
            repo = _git("rev-parse", "--git-dir")
            head = _git("rev-parse", "--verify", "--quiet", "HEAD")
        except OSError:
            return None
        if repo.returncode != 0:
            return "no-repo"
        if head.returncode != 0:
            return "unborn"
        return "ok"

    def committed_prd_lines(self) -> list[str] | None:
        """Return the PRD's lines at HEAD, empty when HEAD holds no PRD, None when git fails."""
        # --show-prefix maps the cwd-relative path to its repo-relative one, so a
        # nested checkout reads the file the pipeline edits.
        prefix_lines = _git_lines("rev-parse", "--show-prefix")
        if prefix_lines is None:
            return None
        prefix = prefix_lines[0].strip() if prefix_lines else ""
        repo_path = f"{prefix}{PRD_PATH}"
        tracked = _git_lines(
            "ls-tree", "--full-tree", "--name-only", "HEAD", "--", repo_path
        )
        if tracked is None:
            return None
        if not any(p.strip() for p in tracked):
            return []
        return _git_lines("show", f"HEAD:{repo_path}")

    def worktree_prd_text(self) -> str | None:
        """Return the working PRD's text, empty when absent, None when unreadable or oversized."""
        prd = Path(PRD_PATH)
        try:
            if prd.is_file() and prd.stat().st_size > self.prd_size_cap:
                return None
            return prd.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""
        except (OSError, ValueError):
            return None

    def dirty_design_doc_paths(self) -> list[str] | None:
        """Return every uncommitted design-doc path, tracked, untracked, or ignored; None when git fails."""
        # --relative keeps the paths project-relative in a nested checkout, so
        # they can match the covering records.
        dirty = _git_lines(
            "diff", "--relative", "--name-only", "HEAD", "--", *AUDITED_DOCS
        )
        untracked = _git_lines(
            "ls-files", "--others", "--exclude-standard", "--", *AUDITED_DOCS
        )
        ignored = _git_lines(
            "ls-files",
            "--others",
            "--ignored",
            "--exclude-standard",
            "--",
            *AUDITED_DOCS,
        )
        if dirty is None or untracked is None or ignored is None:
            return None
        return sorted({p for p in dirty + untracked + ignored if p})

    def design_docs_baseline(self) -> Baseline:
        """Return the last commit touching the audited docs."""
        head_ts = _git_lines("log", "-1", "--format=%cI", "--", *AUDITED_DOCS)
        if head_ts is None:
            return Baseline(False)
        if not head_ts or not head_ts[0].strip():
            return Baseline(True)
        since = parse_iso_seconds(head_ts[0])
        return Baseline(since is not None, since)


def _git_lines(*argv: str) -> list[str] | None:
    """Run git and return its stdout lines, or None on any failure."""
    try:
        proc = _git(*argv)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.splitlines()


def _git(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *argv], capture_output=True, text=True, check=False)
