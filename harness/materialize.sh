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
# Only the tool surfaces the project uses are installed. The project declares
# them in scripts/layout.toml [harness] tools; if the key is absent (an older
# project), the set is auto-detected from the tool agent-dirs already present —
# so an upgrade never adds a tool surface the project did not opt into. The
# shared substrate (skills, templates, schemas, scripts) installs for every tool.
#
# The target's own files — docs/ briefs, scripts/layout.toml, settings, build
# files — are project-owned and never touched here.
#
# After installing, the script REPORTS (never deletes) "extras": files under the
# harness-owned runtime directories that this install did not produce. They are
# either stale orphans from an older harness or genuine project extensions; the
# /materialize skill classifies and acts on them. This script stays a safe,
# non-destructive primitive.
set -euo pipefail

stack="${1:?usage: materialize.sh <stack> <target-dir>}"
target_arg="${2:?usage: materialize.sh <stack> <target-dir>}"

here="$(cd "$(dirname "$0")" && pwd)"
target="$(cd "$target_arg" && pwd)"

# Harness-owned runtime directories: the directory entries of RUNTIME_PATHS in
# harness/core/.claude/skills/doctor/scripts/brief_doctor.py. These trees are
# 100% harness-owned, so scanning them for extras never touches a project-owned
# file (.claude/settings*.json and scripts/layout.toml live outside them). Keep
# in sync with brief_doctor.py — harness/test-materialize.sh guards the parity.
RUNTIME_DIRS=(
  .claude/skills
  .claude/agents
  .claude/hooks
  .claude/templates
  .github/agents
  .opencode/agents
  .junie/agents
  schemas/scratch
)

# --- resolve the tool surfaces to install --------------------------------------
# Precedence: (1) the project's declared set in layout.toml [harness] tools;
# (2) an existing materialized project (a runtime dir already present) keeps its
# current surfaces — detect them, never add one (upgrade safety); (3) a greenfield
# target with no signal gets all four. claude is always on.
declare -a TOOLS=()
lt="$target/scripts/layout.toml"
tools_line=""
if [ -f "$lt" ]; then
  tools_line="$(sed -n 's/^[[:space:]]*tools[[:space:]]*=[[:space:]]*\[\(.*\)\].*/\1/p' "$lt" | head -1)"
fi
if [ -n "$tools_line" ]; then
  while IFS= read -r t; do [ -n "$t" ] && TOOLS+=("$t"); done \
    < <(printf '%s\n' "$tools_line" | grep -oE '"[a-z]+"' | tr -d '"')
elif [ -d "$target/.claude/skills" ] || [ -d "$target/.claude/agents" ]; then
  TOOLS=(claude)                                   # existing project: detect, never add
  [ -d "$target/.github/agents" ]   && TOOLS+=(copilot)
  [ -d "$target/.opencode/agents" ] && TOOLS+=(opencode)
  [ -d "$target/.junie/agents" ]    && TOOLS+=(junie)
else
  TOOLS=(claude copilot opencode junie)            # greenfield / no signal: all four
fi
has_tool() { local t; for t in "${TOOLS[@]}"; do [ "$t" = "$1" ] && return 0; done; return 1; }

# Gated paths of tools NOT selected — skipped during the copy.
EXCLUDE=()
has_tool claude   || EXCLUDE+=(".claude/agents/" ".claude/hooks/")
has_tool copilot  || EXCLUDE+=(".github/agents/")
has_tool opencode || EXCLUDE+=(".opencode/agents/")
has_tool junie    || EXCLUDE+=(".junie/")
excluded() {
  [ ${#EXCLUDE[@]} -eq 0 ] && return 1
  local p; for p in "${EXCLUDE[@]}"; do case "$1" in "$p"*) return 0 ;; esac; done
  return 1
}

installed="$(mktemp)"
present="$(mktemp)"
extras="$(mktemp)"
trap 'rm -f "$installed" "$present" "$extras"' EXIT

copied=0
for layer in core "stacks/$stack"; do
  src="$here/$layer"
  [ -d "$src" ] || continue
  while IFS= read -r -d '' rel; do
    rel="${rel#./}"
    excluded "$rel" && continue
    dest="$target/$rel"
    mkdir -p "$(dirname "$dest")"
    cp -p "$src/$rel" "$dest"
    printf '%s\n' "$rel" >> "$installed"
    copied=$((copied + 1))
  done < <(cd "$src" && find . -type f ! -name '*.pyc' ! -path '*__pycache__*' -print0)
done

echo "materialized stack=$stack tools=${TOOLS[*]}: $copied file(s) into $target"

# Extras = files under the harness-owned runtime dirs that this install did not
# produce. One path per line (relative to the target), between the markers, so
# the /materialize skill can parse them. __pycache__/*.pyc are build artifacts,
# not orphans — excluded, matching the doctor.
for d in "${RUNTIME_DIRS[@]}"; do
  [ -d "$target/$d" ] || continue
  ( cd "$target" && find "$d" -type f ! -name '*.pyc' ! -path '*__pycache__*' )
done | sort -u > "$present"
sort -u "$installed" -o "$installed"
comm -23 "$present" "$installed" > "$extras"

extra_count=$(wc -l < "$extras" | tr -d ' ')
echo "--- extras: $extra_count file(s) not produced by the harness ---"
cat "$extras"
echo "--- end extras ---"
