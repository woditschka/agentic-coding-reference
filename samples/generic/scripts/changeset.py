#!/usr/bin/env python3
"""Emit the change set under review: the one diff every reviewer and the grader read.

  python3 scripts/changeset.py                    the unified diff
  python3 scripts/changeset.py --name-only        changed paths only
  python3 scripts/changeset.py --base <ref>       post-hoc: diff against a committed ref
  python3 scripts/changeset.py --base-tree <sha>  fix-delta: diff against a plan's tree_sha

By default the change set is the uncommitted working tree against HEAD,
narrowed by the layout's exclude globs; --head diffs a committed range
instead. The composition root over the changeset package; stdlib only.
"""

import argparse
import sys
from pathlib import Path

# The package resolves through this script's own directory, which python
# puts on sys.path only when the script runs as a script; a loader by path
# from another working directory needs the entry added.
if (_HERE := str(Path(__file__).resolve().parent)) not in sys.path:
    sys.path.insert(0, _HERE)

from changeset.config import ChangeSetError, load_exclude_globs
from changeset.emit import cmd_changeset, report
from changeset.git_facts import WORKTREE
from changeset.workspace import WorkspaceError, load_members

SCRIPTS_DIR = Path(_HERE)


def main(argv: list[str] | None = None) -> int:
    """Parse the arguments, load the exclude filter, and emit the change set."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument(
        "--base",
        default=None,
        help="base ref to diff against (default: HEAD for the live worktree; "
        "required when --head names a committed range)",
    )
    parser.add_argument(
        "--head",
        default=WORKTREE,
        help="head to diff: the default WORKTREE snapshot, or a commit ref for "
        "a post-hoc committed range",
    )
    parser.add_argument(
        "--base-tree",
        action="append",
        default=None,
        dest="base_tree",
        help="diff against a raw tree object (a review-plan's tree_sha) instead "
        "of a commit ref — the fix-delta scope a re-review reads; repeat with "
        "<member>=<sha> for each present workspace member",
    )
    parser.add_argument(
        "--name-only",
        action="store_true",
        dest="name_only",
        help="print changed paths only (the review's scope), not the unified diff",
    )
    args = parser.parse_args(argv)
    try:
        exclude_globs = load_exclude_globs(SCRIPTS_DIR)
        members = load_members(SCRIPTS_DIR)
    except (ChangeSetError, WorkspaceError) as exc:
        report(str(exc))
        return 1
    return cmd_changeset(args, exclude_globs, members)


if __name__ == "__main__":
    raise SystemExit(main())
