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
# Channel-aware (read from scripts/layout.toml [harness] channel). Under "copy"
# and "manifest" the full runtime is installed. Under "marketplace" the
# tool-discovered surfaces (skills, agents, hooks) ship as a plugin and are NOT
# installed here; only the non-discovered engine sliver (scripts, schemas,
# templates, tool config) is materialized — at project-relative paths every tool
# resolves identically. See docs/adr/2026-06-14-marketplace-plugin-channel.md.
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

# shellcheck source=harness/helpers.sh
. "$here/helpers.sh"   # ALL_TOOLS roster

# Harness-owned runtime directories: the directory entries of RUNTIME_PATHS in
# harness/core/scripts/brief_doctor.py. These trees are
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
channel="copy"
if [ -f "$lt" ]; then
  tools_line="$(sed -n 's/^[[:space:]]*tools[[:space:]]*=[[:space:]]*\[\(.*\)\].*/\1/p' "$lt" | head -1)"
  _ch="$(sed -n 's/^[[:space:]]*channel[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$lt" | head -1)"
  [ -n "$_ch" ] && channel="$_ch"
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
  TOOLS=("${ALL_TOOLS[@]}")                        # greenfield / no signal: all four
fi
has_tool() { local t; for t in "${TOOLS[@]}"; do [ "$t" = "$1" ] && return 0; done; return 1; }

# Gated paths of tools NOT selected — skipped during the copy.
EXCLUDE=()
has_tool claude   || EXCLUDE+=(".claude/agents/" ".claude/hooks/")
has_tool copilot  || EXCLUDE+=(".github/agents/")
has_tool opencode || EXCLUDE+=(".opencode/agents/")
has_tool junie    || EXCLUDE+=(".junie/")

# Marketplace channel: the tool-discovered surfaces (skills, agents, hooks) are
# delivered by the plugin, not materialized here. Exclude them; keep the engine
# sliver (scripts, schemas, templates) and tool config (.junie/config.json) at
# project-relative paths. OpenCode is not a plugin target — under marketplace it
# is already excluded above unless the project also lists it as a tool.
if [ "$channel" = "marketplace" ]; then
  EXCLUDE+=(
    ".claude/skills/" ".claude/agents/" ".claude/hooks/"
    ".github/agents/" ".opencode/agents/" ".junie/agents/"
  )
fi
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

echo "materialized stack=$stack channel=$channel tools=${TOOLS[*]}: $copied file(s) into $target"

# Refresh the harness-managed chapters in the project-owned CLAUDE.md. CLAUDE.md
# itself is the project's (scaffolded once, never overwritten), but several
# chapters are stack-agnostic harness doctrine (Agent Usage, Memory, Writing
# Standards, Scratch Directory, Documentation Updates), each identified by its
# heading — the same managed-region contract as the .gitignore runtime block. We
# rewrite only those chapters (heading to the next "## ") from the single source
# (harness/claude-md/managed-chapters.md); every other chapter is untouched. A
# missing heading (a greenfield or legacy file) is reported as "absent" and left
# for /init (greenfield) or the /materialize reconciliation (legacy) — never a
# silent edit.
if [ -f "$target/CLAUDE.md" ]; then
  # Fail fast on a broken harness tree, like init.sh — refresh would otherwise
  # skip the stamp and only the later doctor would catch it.
  [ -s "$here/VERSION-DATE" ] || { echo "materialize: missing or empty $here/VERSION-DATE — cannot stamp CLAUDE.md" >&2; exit 1; }
  ch_status="$(bash "$here/claude-md/refresh-chapters.sh" "$target/CLAUDE.md" "$here")"
  echo "managed chapters: $ch_status"
fi

# Refresh the harness-owned lines of two more project-owned files, the same way
# the managed CLAUDE.md chapters above are refreshed: deterministically, in
# place, marker-free — the harness owns those lines, the project owns the rest.
#   - .gitignore: the runtime paths (channel-aware; copy commits them so only the
#     .scratch/ ledger is ensured). A new engine file reaches an existing project.
#   - .claude/settings.json: the agent-teams env flag and the PreToolUse matcher
#     for each delivered hook. A newly-shipped hook wires itself.
# Both are ENSURE-PRESENT and additive: project-authored ignores, keys, and hooks
# are never rewritten. Files the project fills with judgment (layout.toml data,
# docs/ briefs, non-doctrine CLAUDE.md chapters) are NOT touched here — the
# /materialize skill reconciles those advisorily.
gi_status="$(bash "$here/refresh-gitignore.sh" "$target/.gitignore" "$here/init/core/gitignore-runtime.txt" "$channel")"
echo "$gi_status"
if command -v python3 >/dev/null 2>&1; then
  set_status="$(python3 "$here/refresh-settings.py" "$target/.claude/settings.json" "$here/init/core/.claude/settings.json" "$target")"
  echo "$set_status"
else
  echo "settings: skipped (python3 unavailable)"
fi

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
