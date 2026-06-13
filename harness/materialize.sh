#!/usr/bin/env bash
# Materialize the harness runtime into a consumer project.
#
#   harness/materialize.sh <stack> <target-dir>
#
# Copies harness/core/ then harness/stacks/<stack>/ into the target, preserving
# permissions. The stack layer is applied last, so it wins on any overlap. This
# is a byte-identical copy, not a render: every materialized file already exists
# in the tree in its final form (agents are pre-expanded per tool surface).
#
# The target's own files — docs/ briefs, scripts/layout.toml, settings, build
# files — are project-owned and never touched here.
set -euo pipefail

stack="${1:?usage: materialize.sh <stack> <target-dir>}"
target_arg="${2:?usage: materialize.sh <stack> <target-dir>}"

here="$(cd "$(dirname "$0")" && pwd)"
target="$(cd "$target_arg" && pwd)"

copied=0
for layer in core "stacks/$stack"; do
  src="$here/$layer"
  [ -d "$src" ] || continue
  while IFS= read -r -d '' rel; do
    rel="${rel#./}"
    dest="$target/$rel"
    mkdir -p "$(dirname "$dest")"
    cp -p "$src/$rel" "$dest"
    copied=$((copied + 1))
  done < <(cd "$src" && find . -type f -print0)
done

echo "materialized stack=$stack: $copied file(s) into $target"
