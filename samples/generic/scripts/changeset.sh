#!/usr/bin/env bash
# changeset.sh — emit the change set under review: the uncommitted working tree
# against HEAD (the delta on whatever branch), filtered by layout.toml
# exclude_globs. This is the SINGLE definition the reviewer roster and the
# change-grader both resolve, so a reviewer and the grader judge byte-identical
# content. A thin wrapper over the engine so reviewers have one verb instead of
# an ad-hoc `git diff` with an undefined base.
#
# Usage:
#   scripts/changeset.sh                 # the unified diff (the hunks to review)
#   scripts/changeset.sh --name-only     # changed paths only (the review scope)
#   scripts/changeset.sh --base <ref>    # post-hoc: diff against a committed ref
#   scripts/changeset.sh --base-tree <sha>  # fix-delta: diff against a review-plan's tree_sha
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$here/score-change.py" changeset "$@"
