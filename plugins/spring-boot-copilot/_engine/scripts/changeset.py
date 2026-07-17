#!/usr/bin/env python3
"""changeset.py — emit the change set under review.

The SINGLE definition the reviewer roster and the change-grader both resolve, so
a reviewer and the grader judge byte-identical content: the uncommitted
working-tree delta against HEAD (the delta on whatever branch), filtered by
layout.toml exclude_globs. A thin launcher over the changeset package's emit
verb (ADR 2026-07-17 runtime-package-layout) — reviewers invoke it through
changeset.sh instead of an ad-hoc `git diff` with an undefined base. Carved out
of grading.py so the neutral change-set definition no longer lives inside one
of its two consumers.

  scripts/changeset.sh                    the unified diff (the hunks to review)
  scripts/changeset.sh --name-only        changed paths only (the review scope)
  scripts/changeset.sh --base <ref>       post-hoc: diff against a committed ref
  scripts/changeset.sh --base-tree <sha>  fix-delta: diff against a plan's tree_sha

The change set lives in no commit by default: it snapshots the live working tree
(tracked edits plus untracked, non-ignored files) into a throwaway index and
diffs base..<that tree>; --head <ref> diffs a committed range instead. The real
index and working tree are never touched. Determinism and untrusted-ref
hardening are the changeset package's (see changeset.git_facts); this launcher
only wires argparse to changeset.emit.

Stdlib only.
"""

import argparse
import sys
from pathlib import Path

# The changeset package resolves via this script's own directory — the directory
# python already puts on sys.path when changeset.py is run as a script. When it
# is loaded by path from another cwd (a test loader), that entry is absent, so
# add it here before the package import below; this keeps the tool's
# cwd-independence (ADR 2026-07-17 runtime-package-layout).
if (_HERE := str(Path(__file__).resolve().parent)) not in sys.path:
    sys.path.insert(0, _HERE)

# This entry point is a launcher: it composes the changeset package's emit verb,
# submodule-form (never a bare `import changeset`, which a solo strict run would
# resolve to this file — see ADR 2026-07-17 runtime-package-layout).
from changeset.emit import cmd_changeset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument(
        "--base",
        default=None,
        help="base ref to diff against (default: HEAD for the live worktree; "
        "required when --head names a committed range)",
    )
    parser.add_argument(
        "--head",
        default="WORKTREE",
        help="head to diff: the default WORKTREE snapshot, or a commit ref for "
        "a post-hoc committed range",
    )
    parser.add_argument(
        "--base-tree",
        default=None,
        dest="base_tree",
        help="diff against a raw tree object (a review-plan's tree_sha) instead "
        "of a commit ref — the fix-delta scope a re-review reads",
    )
    parser.add_argument(
        "--name-only",
        action="store_true",
        dest="name_only",
        help="print changed paths only (the review's scope), not the unified diff",
    )
    args = parser.parse_args(argv)
    exit_code: int = cmd_changeset(args)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
