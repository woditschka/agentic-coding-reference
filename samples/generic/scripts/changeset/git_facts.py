"""Run every git command of the change set under one canonical environment, and resolve the set itself.

The gateway: refs and tree names are hardened before they reach git argv, the
working tree is snapshotted without touching the real index, and the base
narrows to the merge-base so a diff is the delta and never a superset.
"""

import os
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

WORKTREE = "WORKTREE"
HeadKind = Literal["worktree", "commit"]

# 40 (SHA-1) or 64 (SHA-256) lowercase hex digits: the only accepted tree name,
# so an agent-authored value can neither smuggle an option nor name a symbolic
# revision.
_TREE_SHA = re.compile(r"^[0-9a-f]{40,64}$")
_GIT_ENV = {**os.environ, "LC_ALL": "C", "TZ": "UTC", "GIT_PAGER": "cat"}
_SNAPSHOT_INDEX = Path(".scratch") / "tmp" / "grader.index"


@dataclass(frozen=True, slots=True)
class ChangeSet:
    """The change set under review: its resolved ends, the commit the head sits on, and the paths every diff drops.

    The head is a commit, or the tree of a working-tree snapshot; the tip is
    the commit the head sits on, which bounds the churn log. The base is the
    merge-base of the requested base and the tip when one exists.
    """

    base: str | None
    head: str | None
    tip: str | None
    head_kind: HeadKind
    merge_base: str | None
    exclude_globs: tuple[str, ...]

    @property
    def resolved(self) -> bool:
        """Return whether both ends name an object."""
        return self.base is not None and self.head is not None

    @property
    def pathspecs(self) -> list[str]:
        """Return the git pathspec arguments that drop the excluded paths."""
        return exclude_pathspecs(self.exclude_globs)


def run_git(*args: str, check: bool = True, env: dict[str, str] | None = None) -> str:
    """Run one git command under the canonical environment and return its stdout.

    Output decodes with replacement, so a file git reads as text in another
    encoding never takes the command down.
    """
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "-c", "core.renames=true", *args],
        capture_output=True,
        text=True,
        errors="replace",
        env=_GIT_ENV if env is None else env,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def resolve_ref(ref: str | None) -> str | None:
    """Return the commit a ref names, or None; a dash-prefixed value is refused before git sees it."""
    if not ref or ref.startswith("-"):
        return None
    out = run_git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False)
    return out.strip() or None


def resolve_tree(sha: object) -> str | None:
    """Return the tree a bare hexadecimal object name resolves to, or None for any other shape."""
    if not isinstance(sha, str) or not _TREE_SHA.match(sha):
        return None
    out = run_git("rev-parse", "--verify", "--quiet", f"{sha}^{{tree}}", check=False)
    return out.strip() or None


def snapshot_worktree() -> str | None:
    """Write the working tree, untracked files included, as a tree object and return its name; None on failure.

    The staging happens in a throwaway index under .scratch/tmp, so the real
    index and working tree are never read or written.
    """
    _SNAPSHOT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    try:
        _SNAPSHOT_INDEX.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        return None
    # git resolves a relative GIT_INDEX_FILE against the repository top level,
    # not the working directory.
    env = {**_GIT_ENV, "GIT_INDEX_FILE": str(_SNAPSHOT_INDEX.resolve())}
    try:
        run_git("add", "-A", env=env)
        tree = run_git("write-tree", env=env).strip()
    except RuntimeError:
        return None
    finally:
        try:
            _SNAPSHOT_INDEX.unlink()
        except OSError:
            pass
    return tree or None


def head_kind(head: str) -> HeadKind:
    """Return whether the head argument names the working tree or a commit."""
    return "worktree" if head == WORKTREE else "commit"


def resolve_changeset(base: str, head: str, exclude_globs: Sequence[str]) -> ChangeSet:
    """Resolve both ends of the change set, snapshotting a working-tree head, and narrow the base to the merge-base."""
    base_sha = resolve_ref(base)
    tip = resolve_ref("HEAD") if head == WORKTREE else resolve_ref(head)
    head_sha = snapshot_worktree() if head == WORKTREE else tip
    merge_base = None
    if base_sha and tip:
        merge_base = run_git("merge-base", base_sha, tip, check=False).strip() or None
    return ChangeSet(
        base=merge_base or base_sha,
        head=head_sha,
        tip=tip,
        head_kind=head_kind(head),
        merge_base=merge_base,
        exclude_globs=tuple(exclude_globs),
    )


def exclude_pathspecs(globs: Sequence[str]) -> list[str]:
    """Return the pathspec arguments dropping the globs from a diff; none for no globs.

    Top-level and glob magic make the filter the same from any working
    directory, with `/` significant and `**` crossing directories as the
    layout documents for every other list.
    """
    if not globs:
        return []
    return ["--", ":(top)", *(f":(top,glob,exclude){g}" for g in globs)]
