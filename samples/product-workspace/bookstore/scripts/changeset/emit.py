"""Resolve the change set the arguments name and emit it.

The verb layer: the base-ref rule the grading commands share, the tree
override a fix-delta review reads, and the emit verb changeset.py launches.
"""

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from .config import ChangeSetError
from .git_facts import (
    WORKTREE,
    ChangeSet,
    head_kind,
    prefix_listing,
    resolve_changeset,
    resolve_ref,
    resolve_tree,
    run_git,
    snapshot_worktree,
)
from .workspace import Member, unreached_globs

# A tree override names the project's tree bare, or one member's as key=sha.
_MEMBER_TREE_SEPARATOR = "="


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


def changeset_for(
    args: argparse.Namespace,
    exclude_globs: Sequence[str],
    member: Member | None = None,
) -> ChangeSet:
    """Return one repository's change set; a tree override diffs a raw tree against the head."""
    declared = () if member is None else (member,)
    tree = base_trees(args, declared).get(None if member is None else member.key)
    return _resolved(args, exclude_globs, member, tree)


def _resolved(
    args: argparse.Namespace,
    exclude_globs: Sequence[str],
    member: Member | None,
    base_tree: str | None,
) -> ChangeSet:
    """Return one repository's change set, from the tree override when one names it."""
    member_path = None if member is None else member.path
    if base_tree is None:
        return resolve_changeset(
            default_base(args), args.head, exclude_globs, member_path
        )
    root = None if member_path is None else Path(member_path)
    tree = resolve_tree(base_tree, root)
    if tree is None:
        raise ChangeSetError(f"--base-tree {base_tree!r} is not a valid tree object")
    head = (
        snapshot_worktree(root)
        if args.head == WORKTREE
        else resolve_ref(args.head, root)
    )
    return ChangeSet(
        base=tree,
        head=head,
        tip=None,
        head_kind=head_kind(args.head),
        merge_base=None,
        exclude_globs=tuple(exclude_globs),
        member_path=member_path,
    )


def changesets_for(
    args: argparse.Namespace,
    exclude_globs: Sequence[str],
    members: Sequence[Member] = (),
) -> tuple[ChangeSet, ...]:
    """Return the project's change set followed by one per present member; an absent member has none.

    An exclude glob under a parent step that reaches no declared member, and a
    tree override naming no declared member, are refused: each would silently
    widen what a review reads.
    """
    dead = unreached_globs(exclude_globs, members)
    if dead:
        raise ChangeSetError(
            f"layout.toml: exclude_globs {list(dead)!r} reach no declared workspace member"
        )
    trees = base_trees(args, members)
    project = Path.cwd()
    present = [m for m in members if m.is_present(project)]
    return (
        _resolved(args, exclude_globs, None, trees.get(None)),
        *(_resolved(args, exclude_globs, m, trees.get(m.key)) for m in present),
    )


def base_trees(
    args: argparse.Namespace, members: Sequence[Member]
) -> Mapping[str | None, str]:
    """Return the tree overrides by member key, the project's under None; a malformed or unknown one is refused."""
    given = getattr(args, "base_tree", None)
    values = [given] if isinstance(given, str) else list(given or ())
    declared = {m.key for m in members}
    trees: dict[str | None, str] = {}
    for value in values:
        key, separator, tree = value.rpartition(_MEMBER_TREE_SEPARATOR)
        owner = key if separator else None
        if separator and key not in declared:
            raise ChangeSetError(
                f"--base-tree {value!r} names no declared workspace member"
            )
        if not tree or owner in trees:
            raise ChangeSetError(f"--base-tree {value!r} is malformed or repeated")
        trees[owner] = tree
    return trees


def cmd_changeset(
    args: argparse.Namespace,
    exclude_globs: Sequence[str],
    members: Sequence[Member] = (),
) -> int:
    """Print the change set's unified diff, or its changed paths, and return the exit code."""
    try:
        changesets = changesets_for(args, exclude_globs, members)
    except ChangeSetError as exc:
        report(str(exc))
        return 1
    unresolved = [c for c in changesets if not c.resolved]
    if unresolved:
        where = unresolved[0].member_path
        location = "" if where is None else f" in {where!r}"
        report(
            f"base ref or working-tree snapshot unresolved{location}; no diff emitted"
        )
        return 1
    try:
        out = "".join(
            _emit(changeset, name_only=args.name_only) for changeset in changesets
        )
    except RuntimeError as exc:
        report(f"git command failed: {exc}")
        return 1
    sys.stdout.write(out)
    return 0


def _emit(changeset: ChangeSet, *, name_only: bool) -> str:
    """Return one repository's diff or listing, its paths spelled from the project."""
    listing = ["--name-only"] if name_only else changeset.diff_options
    out = run_git(
        "diff",
        *listing,
        "--find-renames",
        str(changeset.base),
        str(changeset.head),
        *changeset.pathspecs,
        root=changeset.root,
    )
    return prefix_listing(out, changeset.prefix) if name_only else out


def report(message: str) -> None:
    """Write one changeset message to stderr."""
    print(f"changeset: {message}", file=sys.stderr)
