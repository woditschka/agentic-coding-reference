"""Resolve the change set the arguments name and emit it.

The verb layer: the base-ref rule the grading commands share, the tree
override a fix-delta review reads, and the emit verb changeset.py launches.
"""

import argparse
import sys
from collections.abc import Sequence

from .config import ChangeSetError
from .git_facts import (
    WORKTREE,
    ChangeSet,
    head_kind,
    resolve_changeset,
    resolve_ref,
    resolve_tree,
    run_git,
    snapshot_worktree,
)


def default_base(args: argparse.Namespace) -> str:
    """Return the base to diff against: the one given, or HEAD for a working-tree head.

    A committed head with no base would diff a commit against itself and
    emit an empty range, so it is refused.
    """
    if args.base is not None:
        return str(args.base)
    if args.head == WORKTREE:
        return "HEAD"
    raise ChangeSetError(
        "a committed --head needs an explicit --base (the start of the range to grade)"
    )


def changeset_for(args: argparse.Namespace, exclude_globs: Sequence[str]) -> ChangeSet:
    """Return the change set the arguments name; a tree override diffs a raw tree against the head."""
    base_tree = getattr(args, "base_tree", None)
    if not base_tree:
        return resolve_changeset(default_base(args), args.head, exclude_globs)
    tree = resolve_tree(base_tree)
    if tree is None:
        raise ChangeSetError(f"--base-tree {base_tree!r} is not a valid tree object")
    head = snapshot_worktree() if args.head == WORKTREE else resolve_ref(args.head)
    return ChangeSet(
        base=tree,
        head=head,
        tip=None,
        head_kind=head_kind(args.head),
        merge_base=None,
        exclude_globs=tuple(exclude_globs),
    )


def cmd_changeset(args: argparse.Namespace, exclude_globs: Sequence[str]) -> int:
    """Print the change set's unified diff, or its changed paths, and return the exit code."""
    try:
        changeset = changeset_for(args, exclude_globs)
    except ChangeSetError as exc:
        report(str(exc))
        return 1
    if not changeset.resolved:
        report("base ref or working-tree snapshot unresolved; no diff emitted")
        return 1
    listing = ["--name-only"] if args.name_only else []
    try:
        out = run_git(
            "diff",
            *listing,
            "--find-renames",
            str(changeset.base),
            str(changeset.head),
            *changeset.pathspecs,
        )
    except RuntimeError as exc:
        report(f"git command failed: {exc}")
        return 1
    sys.stdout.write(out)
    return 0


def report(message: str) -> None:
    """Write one changeset message to stderr."""
    print(f"changeset: {message}", file=sys.stderr)
