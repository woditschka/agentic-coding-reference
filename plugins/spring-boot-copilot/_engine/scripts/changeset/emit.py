"""changeset.emit — the change set under review: its resolution and its emit.

The change set is the single definition a reviewer and the grader both resolve,
so they judge byte-identical content: the uncommitted working-tree delta against
HEAD (the delta on whatever branch), narrowed by exclude_globs, or a post-hoc
committed range. This module owns the base-ref defaulting rule (`base_arg`), the
base/head resolution (`_resolve_changeset`), and the emit verb (`cmd_changeset`)
that `changeset.py` launches. The grading engine's extract and review-plan reuse
`base_arg` for the same defaulting, so the grader's row and the reviewer's diff
share one base rule.

Stdlib only.
"""

import sys
from typing import Any

from .git_facts import (
    exclude_pathspecs,
    resolve_ref,
    resolve_tree,
    run_git,
    snapshot_worktree,
)


def base_arg(args: Any) -> tuple[Any, str | None]:
    """The base ref to diff against, or (None, error).

    Defaults to HEAD for the live worktree flow — the uncommitted delta on
    whatever branch. A committed --head with no explicit --base is an error: the
    HEAD default would diff that commit against itself (merge-base(HEAD, HEAD) is
    HEAD) and silently emit an empty range, hiding the change instead of grading
    it. Post-hoc grading therefore requires the caller to name the range's start.
    Shared by the changeset emit and by the grader's extract/review-plan.
    """
    if args.base is not None:
        return args.base, None
    if args.head == "WORKTREE":
        return "HEAD", None
    return None, (
        "a committed --head needs an explicit --base (the start of the range to grade)"
    )


def _resolve_changeset(args: Any) -> tuple[str | None, str | None, str | None]:
    """Resolve (base_sha, head_sha, error) for the change set.

    Snapshot the working tree (default) or resolve a committed --head, then
    narrow base to the merge-base so the diff is the delta, not a superset. base
    defaults to HEAD for the live worktree flow; a committed --head with no
    --base is rejected (see base_arg). --base-tree overrides all of this: it
    diffs a raw tree (a review-plan's tree_sha) against the worktree with no
    commit resolution or merge-base — the fix-delta scope a re-review reads. On
    error the shas are None and error is a message.
    """
    base_tree = getattr(args, "base_tree", None)
    if base_tree:
        tree = resolve_tree(base_tree)
        if tree is None:
            return None, None, f"--base-tree {base_tree!r} is not a valid tree object"
        head_sha = (
            snapshot_worktree() if args.head == "WORKTREE" else resolve_ref(args.head)
        )
        return tree, head_sha, None
    base, base_err = base_arg(args)
    if base_err:
        return None, None, base_err
    base_sha = resolve_ref(base)
    tip = resolve_ref(args.head) if args.head != "WORKTREE" else resolve_ref("HEAD")
    head_sha = snapshot_worktree() if args.head == "WORKTREE" else tip
    if base_sha and tip:
        mb = run_git("merge-base", base_sha, tip, check=False).strip()
        if mb:
            base_sha = mb
    return base_sha, head_sha, None


def cmd_changeset(args: Any) -> int:
    """Emit the change set under review — the reviewer/grader shared definition.

    Default: the uncommitted working tree vs HEAD, filtered by exclude_globs.
    --name-only prints changed paths (the review's scope); otherwise the unified
    diff (the hunks). A reviewer reads this instead of an ad-hoc `git diff`, so
    its view matches the grader's row exactly. Unresolved base or a failed
    snapshot exits non-zero rather than emitting a misleading empty diff.
    """
    base_sha, head_sha, err = _resolve_changeset(args)
    if err:
        print(f"changeset: {err}", file=sys.stderr)
        return 1
    if base_sha is None or head_sha is None:
        print(
            "changeset: base ref or working-tree snapshot unresolved; no diff emitted",
            file=sys.stderr,
        )
        return 1
    ex = exclude_pathspecs()
    try:
        if args.name_only:
            out = run_git(
                "diff", "--name-only", "--find-renames", base_sha, head_sha, *ex
            )
        else:
            out = run_git("diff", "--find-renames", base_sha, head_sha, *ex)
    except RuntimeError as exc:
        print(f"changeset: git command failed: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(out)
    return 0
