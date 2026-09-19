"""Run every git command of the change set under one canonical environment, and resolve the set itself.

The gateway: refs and tree names are hardened before they reach git argv, the
working tree is snapshotted without touching the real index, and the base
narrows to the merge-base so a diff is the delta and never a superset.
"""

import fnmatch
import os
import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

WORKTREE = "WORKTREE"
PARENT_STEP = ".."
HeadKind = Literal["worktree", "commit"]

# 40 (SHA-1) or 64 (SHA-256) lowercase hex digits: the only accepted tree name,
# so an agent-authored value can neither smuggle an option nor name a symbolic
# revision.
_TREE_SHA = re.compile(r"^[0-9a-f]{40,64}$")
_GIT_ENV = {**os.environ, "LC_ALL": "C", "TZ": "UTC", "GIT_PAGER": "cat"}
_SNAPSHOT_DIR = Path(".scratch") / "tmp"
_SNAPSHOT_INDEX = _SNAPSHOT_DIR / "grader.index"
_NUMSTAT_COLUMNS = 3
_INDEX_SLUG = re.compile(r"[^A-Za-z0-9]+")


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
    # A member's set names the member's directory relative to the project;
    # the project's own set names none.
    member_path: str | None = None

    @property
    def resolved(self) -> bool:
        """Return whether both ends name an object."""
        return self.base is not None and self.head is not None

    @property
    def root(self) -> Path | None:
        """Return the repository every git call of this set runs in; None for the project itself."""
        return None if self.member_path is None else Path(self.member_path)

    @property
    def prefix(self) -> str:
        """Return what every path of this set carries in front of git's own spelling."""
        return "" if self.member_path is None else f"{self.member_path}/"

    @property
    def pathspecs(self) -> list[str]:
        """Return the git pathspec arguments that drop the excluded paths, spelled for this set's repository."""
        return exclude_pathspecs(globs_for(self.exclude_globs, self.prefix))

    @property
    def diff_options(self) -> list[str]:
        """Return the diff options that make git spell this set's paths with the prefix."""
        return diff_prefix_options(self.prefix)


def globs_for(globs: Sequence[str], prefix: str) -> tuple[str, ...]:
    """Return the globs that apply inside one set's repository, with the set's prefix removed.

    A project-relative glob applies to the project's own set. A glob under a
    parent step applies to the members whose path its first segment matches,
    spelled relative to each; the segment may carry a wildcard, so one glob
    can reach every member of one product.
    """
    if not prefix:
        return tuple(g for g in globs if not g.startswith(f"{PARENT_STEP}/"))
    member = prefix.rstrip("/")
    applicable = []
    for glob in globs:
        if not glob.startswith(f"{PARENT_STEP}/"):
            continue
        head, separator, rest = glob[len(PARENT_STEP) + 1 :].partition("/")
        if separator and rest and fnmatch.fnmatchcase(member, f"{PARENT_STEP}/{head}"):
            applicable.append(rest)
    return tuple(applicable)


def diff_prefix_options(prefix: str) -> list[str]:
    """Return the git diff options spelling every header path under the prefix; none for the project itself."""
    if not prefix:
        return []
    return [f"--src-prefix=a/{prefix}", f"--dst-prefix=b/{prefix}"]


def prefix_listing(listing: str, prefix: str) -> str:
    """Return a name-only listing with the prefix in front of every path."""
    if not prefix:
        return listing
    return "".join(f"{prefix}{line}\n" for line in listing.splitlines() if line)


def prefix_numstat(numstat: str, prefix: str) -> str:
    """Return a numstat listing with the prefix in front of every path column."""
    if not prefix:
        return numstat
    rows = []
    for line in numstat.splitlines():
        columns = line.split("\t", _NUMSTAT_COLUMNS - 1)
        if len(columns) == _NUMSTAT_COLUMNS:
            columns[-1] = f"{prefix}{columns[-1]}"
        rows.append("\t".join(columns))
    return "".join(f"{row}\n" for row in rows)


def run_git(
    *args: str,
    check: bool = True,
    env: dict[str, str] | None = None,
    root: Path | None = None,
) -> str:
    """Run one git command under the canonical environment, in the root's repository, and return its stdout.

    Output decodes with replacement, so a file git reads as text in another
    encoding never takes the command down.
    """
    location = [] if root is None else ["-C", str(root)]
    result = subprocess.run(
        [
            "git",
            *location,
            "-c",
            "core.quotepath=false",
            "-c",
            "core.renames=true",
            *args,
        ],
        capture_output=True,
        text=True,
        errors="replace",
        env=_GIT_ENV if env is None else env,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def resolve_ref(ref: str | None, root: Path | None = None) -> str | None:
    """Return the commit a ref names, or None; a dash-prefixed value is refused before git sees it."""
    if not ref or ref.startswith("-"):
        return None
    out = run_git(
        "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False, root=root
    )
    return out.strip() or None


def resolve_tree(sha: object, root: Path | None = None) -> str | None:
    """Return the tree a bare hexadecimal object name resolves to, or None for any other shape."""
    if not isinstance(sha, str) or not _TREE_SHA.match(sha):
        return None
    out = run_git(
        "rev-parse", "--verify", "--quiet", f"{sha}^{{tree}}", check=False, root=root
    )
    return out.strip() or None


def snapshot_worktree(root: Path | None = None) -> str | None:
    """Write a working tree, untracked files included, as a tree object and return its name; None on failure.

    The staging happens in a throwaway index under the project's .scratch/tmp,
    one per repository, so no real index and no working tree is ever read or
    written.
    """
    index = _snapshot_index(root)
    index.parent.mkdir(parents=True, exist_ok=True)
    try:
        index.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        return None
    # git resolves a relative GIT_INDEX_FILE against the repository top level,
    # not the working directory.
    env = {**_GIT_ENV, "GIT_INDEX_FILE": str(index.resolve())}
    try:
        run_git("add", "-A", env=env, root=root)
        tree = run_git("write-tree", env=env, root=root).strip()
    except RuntimeError:
        return None
    finally:
        try:
            index.unlink()
        except OSError:
            pass
    return tree or None


def _snapshot_index(root: Path | None) -> Path:
    if root is None:
        return _SNAPSHOT_INDEX
    return _SNAPSHOT_DIR / f"grader-{_INDEX_SLUG.sub('-', str(root)).strip('-')}.index"


def head_kind(head: str) -> HeadKind:
    """Return whether the head argument names the working tree or a commit."""
    return "worktree" if head == WORKTREE else "commit"


def resolve_changeset(
    base: str,
    head: str,
    exclude_globs: Sequence[str],
    member_path: str | None = None,
) -> ChangeSet:
    """Resolve both ends of one repository's change set, snapshotting a working-tree head, and narrow the base to the merge-base."""
    root = None if member_path is None else Path(member_path)
    base_sha = resolve_ref(base, root)
    tip = resolve_ref("HEAD", root) if head == WORKTREE else resolve_ref(head, root)
    head_sha = snapshot_worktree(root) if head == WORKTREE else tip
    merge_base = None
    if base_sha and tip:
        merge_base = (
            run_git("merge-base", base_sha, tip, check=False, root=root).strip() or None
        )
    return ChangeSet(
        base=merge_base or base_sha,
        head=head_sha,
        tip=tip,
        head_kind=head_kind(head),
        merge_base=merge_base,
        exclude_globs=tuple(exclude_globs),
        member_path=member_path,
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
