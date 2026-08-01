"""changeset.git_facts — the change set's git gateway.

Every git invocation the change-set layer makes goes through here, under one
canonical environment (LC_ALL=C, TZ=UTC, quotepath off) so two runs over the
same refs agree byte-for-byte. The gateway also owns the untrusted-ref
hardening: a '-'-prefixed ref or a non-hex tree name is rejected before it can
smuggle a git option into an argument list. The grading engine composes this
gateway too — its feature model reads every diff through it (ADR 2026-07-17
runtime-package-layout).

Stdlib only.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from .config import get_layout

# A resolved tree object name: 40 (SHA-1) or 64 (SHA-256) lowercase hex digits.
# The same constraint the review-plan schema pins on the tree_sha fields, applied
# on the untrusted read path (a log field the schema does not re-validate).
_TREE_SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")

# Canonical environment for every git invocation — kills locale/timezone/
# quoting drift so two runs over the same refs agree byte-for-byte.
_GIT_ENV = {**os.environ, "LC_ALL": "C", "TZ": "UTC", "GIT_PAGER": "cat"}

# The throwaway snapshot index lives under the pipeline's scratch dir — the
# same .scratch/ the handoff log calls home, but a private tmp/ corner of it.
_TMP_DIR = Path(".scratch") / "tmp"


def run_git(*args: str, check: bool = True, env: dict[str, str] | None = None) -> str:
    """Run a git command under the canonical environment; return stdout.

    Pass env to override the default canonical environment — e.g. the worktree
    snapshot adds a GIT_INDEX_FILE so it stages into a throwaway index. The
    `-c core.renames=true` override is inert for commands that ignore it (add,
    write-tree), so the same wrapper serves both diff and snapshot calls.
    """
    result = subprocess.run(
        ["git", "-c", "core.quotepath=false", "-c", "core.renames=true", *args],
        capture_output=True,
        text=True,
        env=_GIT_ENV if env is None else env,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def resolve_ref(ref: str | None) -> str | None:
    """Return the resolved SHA for ref, or None if it cannot be resolved.

    A ref starting with '-' is rejected outright: it cannot name a real commit
    and could only be an attempt to smuggle a git option into the argument list.
    """
    if not ref or ref.startswith("-"):
        return None
    try:
        out = run_git(
            "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False
        )
    except RuntimeError:
        return None
    out = out.strip()
    return out or None


def resolve_tree(sha: Any) -> str | None:
    """Return the resolved tree SHA for a raw tree object, or None.

    Distinct from resolve_ref, which resolves commits: a review-plan's tree_sha
    is a bare tree (the worktree snapshot has no commit), so a fix-delta review
    diffs against it directly. Only a bare hex object name is accepted — this
    both blocks a '-'-prefixed value from smuggling a git option into the
    argument list and rejects a symbolic revision (HEAD, @{-1}, :/regex) that
    would otherwise diff the fix delta against an attacker-chosen tree and
    under-scope the roster. The engine writes only hex here (git output,
    schema-validated); the guard closes the untrusted read path the schema
    does not re-check."""
    if not isinstance(sha, str) or not _TREE_SHA_RE.match(sha):
        return None
    try:
        out = run_git(
            "rev-parse", "--verify", "--quiet", f"{sha}^{{tree}}", check=False
        )
    except RuntimeError:
        return None
    out = out.strip()
    return out or None


def snapshot_worktree() -> str | None:
    """Write a tree object capturing the full working-tree state and return its
    SHA, or None on failure.

    Stages every worktree file — tracked edits, deletions, and untracked
    non-ignored files — into a throwaway index under .scratch/tmp, then
    write-tree. `git add -A` honours .gitignore, so build output and scratch
    stay out. The real index and working tree are never read or written; the
    temp index is removed afterward. The resulting tree is content-addressed, so
    an unchanged working tree yields the same SHA on every run.
    """
    _TMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_index = _TMP_DIR / "grader.index"
    try:
        tmp_index.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        return None

    # git resolves a relative GIT_INDEX_FILE against the repo toplevel, not the
    # cwd; make it absolute so the snapshot also works from a subdirectory.
    env = {**_GIT_ENV, "GIT_INDEX_FILE": str(tmp_index.resolve())}

    try:
        run_git("add", "-A", env=env)
        tree = run_git("write-tree", env=env).strip()
    except RuntimeError:
        return None
    finally:
        try:
            tmp_index.unlink()
        except OSError:
            pass
    return tree or None


def exclude_pathspecs() -> list[str]:
    """Return git pathspec args dropping the project's `exclude_globs`, or [].

    `git add -A` in the snapshot already honours .gitignore, so build output and
    .scratch stay out. `exclude_globs` is the additional project-declared filter
    (tracked-but-irrelevant paths: vendored trees, generated-yet-committed
    files). Expressed as exclude pathspecs so the same filter applies to every
    diff the change set is read through — numstat, unified, name-only — keeping
    the reviewer's view and the grader's row identical. Empty list => no
    pathspec, i.e. the whole diff.

    The pathspec is repo-root-relative (`:(top)`) so the change set is the same
    from any working directory, and uses glob magic (`:(glob)`) so a glob means
    what layout.toml documents for every other list — `/` is significant and
    `**` crosses directories — rather than git's default pathspec matching.
    """
    globs = get_layout().EXCLUDE
    if not globs:
        return []
    return ["--", ":(top)", *(f":(top,glob,exclude){g}" for g in globs)]
