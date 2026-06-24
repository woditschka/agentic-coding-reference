#!/usr/bin/env bash
# Scaffold the project-OWNED files a harness consumer commits.
#
#   harness/init.sh <stack> <target-dir> <project-name> <project-description> [harness-version] [tools-csv] [channel]
#
# harness-version stamps the provenance line of every materialized file
# (harness@<version>). It is the artifact version, independent of the API
# spec_version. Omit it (or pass empty) and init reads harness/VERSION — the
# single source of truth — so callers normally do not supply it.
#
# tools-csv is the comma-separated tool surfaces to install (claude is always on;
# copilot, opencode, junie optional). Default: all four. The /init skill asks.
#
# channel is "copy" (default — runtime committed into the repo), "manifest"
# (runtime materialized and gitignored, not committed), or "marketplace" (the
# tool-discovered surfaces — skills, agents, hooks — ship as a plugin; the
# project keeps only the materialized engine sliver, gitignored). Copy keeps the
# harness self-contained and version-controlled; manifest and marketplace keep
# the repo lean and deliver the runtime out-of-band. The /init skill detects an
# existing project's channel and defaults a greenfield one to copy — no prompt.
#
# This lays down only what the PROJECT owns and commits — its CLAUDE.md rules
# file, .claude/settings.json, scripts/layout.toml (with the channel
# declaration), the docs/ brief roster, and the .gitignore block. It does NOT
# install the harness runtime: that is materialize.sh, which delivers the
# runtime (.claude/skills, agents, schemas, scripts) — committed under the copy
# channel (default), gitignored under manifest.
#
# init never overwrites a project file that already exists — re-running it only
# fills gaps. A greenfield setup runs init once, then materialize once (or just
# /materialize, which runs init first when the project-owned files are missing).
#
# Sources live in harness/init/ (core overlaid with stacks/<stack>) and the
# doctor's brief templates (harness/core/.claude/skills/doctor/templates).
set -euo pipefail

stack="${1:?usage: init.sh <stack> <target> <project-name> <project-description> [harness-version]}"
target_arg="${2:?usage: init.sh <stack> <target> <project-name> <project-description> [harness-version]}"
PROJECT_NAME="${3:?missing project-name}"
PROJECT_DESCRIPTION="${4:?missing project-description}"
HARNESS_VERSION="${5:-}"   # default below from harness/VERSION once $here is known
TOOLS_CSV="${6:-claude,copilot,opencode,junie}"
CHANNEL="${7:-copy}"
case "$CHANNEL" in
  copy|manifest|marketplace) ;;
  *) echo "init: channel must be 'copy', 'manifest', or 'marketplace', got '$CHANNEL'" >&2; exit 1 ;;
esac

# Build the TOML array string from the CSV — trim blanks, force claude on.
IFS=',' read -ra _tools <<< "$TOOLS_CSV"
_arr=()
for _t in "${_tools[@]}"; do _t="${_t// /}"; [ -n "$_t" ] && _arr+=("\"$_t\""); done
_has=0; for _t in "${_arr[@]+"${_arr[@]}"}"; do [ "$_t" = '"claude"' ] && _has=1; done
[ "$_has" -eq 0 ] && _arr=('"claude"' "${_arr[@]+"${_arr[@]}"}")
TOOLS_TOML=""; for _t in "${_arr[@]}"; do TOOLS_TOML="${TOOLS_TOML:+$TOOLS_TOML, }$_t"; done
TOOLS_TOML="[$TOOLS_TOML]"

here="$(cd "$(dirname "$0")" && pwd)"
target="$(cd "$target_arg" && pwd)"
init_src="$here/init"
tpl="$here/core/.claude/skills/doctor/templates"

# Artifact version: explicit arg 5 wins; otherwise the harness/VERSION source of
# truth. Decoupled from spec_version (which the doctor validates separately).
if [ -z "$HARNESS_VERSION" ]; then
  [ -f "$here/VERSION" ] || { echo "init: missing $here/VERSION and no [harness-version] given" >&2; exit 1; }
  HARNESS_VERSION="$(tr -d '[:space:]' < "$here/VERSION")"
  [ -n "$HARNESS_VERSION" ] || { echo "init: $here/VERSION is empty — no version to stamp" >&2; exit 1; }
fi

# Pure-bash placeholder fill: ${//} takes literal search/replace (no regex), so
# arbitrary characters in the description are safe. cat strips trailing newlines;
# printf restores a single one — fine for markdown and toml.
fill() {
  local f="$1" content
  content="$(cat "$f")"
  content="${content//\{\{PROJECT_NAME\}\}/$PROJECT_NAME}"
  content="${content//\{\{PROJECT_DESCRIPTION\}\}/$PROJECT_DESCRIPTION}"
  content="${content//\{\{HARNESS_VERSION\}\}/$HARNESS_VERSION}"
  printf '%s\n' "$content" > "$f"
}

created=0
skipped=0
lt_pre=0; [ -e "$target/scripts/layout.toml" ] && lt_pre=1   # pre-existing layout?

# 1. Project-owned skeletons: overlay init/core then init/stacks/<stack>.
for layer in core "stacks/$stack"; do
  src="$init_src/$layer"
  [ -d "$src" ] || continue
  while IFS= read -r -d '' rel; do
    rel="${rel#./}"
    [ "$rel" = "gitignore-runtime.txt" ] && continue   # appended below, not a file to copy
    dest="$target/$rel"
    if [ -e "$dest" ]; then skipped=$((skipped + 1)); continue; fi
    mkdir -p "$(dirname "$dest")"
    cp -p "$src/$rel" "$dest"
    fill "$dest"
    created=$((created + 1))
  done < <(cd "$src" && find . -type f -print0)
done

# 1a. Fill the harness-managed chapters in the scaffolded CLAUDE.md. The skeleton
# ships each managed heading with an empty body; copy the single source
# (harness/claude-md/managed-chapters.md) into them, replacing each through to the
# next "## " heading. Idempotent and a no-op ("absent") for any heading the
# skeleton omits — materialize refreshes them on every upgrade thereafter. Only
# the managed chapters are written; every other chapter is the project's.
if [ -f "$target/CLAUDE.md" ]; then
  bash "$here/claude-md/refresh-chapters.sh" "$target/CLAUDE.md" "$here" >/dev/null
fi

# 1b. Channel declaration. If the target already had scripts/layout.toml (so the
# overlay above kept it), it may predate the manifest channel and lack the
# [harness] table. Additively inject it — append-only, touching no existing key.
# This is the one exception to "never modify an existing project file": a key the
# doctor requires, added without altering the project's own rules. It is how an
# existing copy-channel project migrates to manifest.
lt="$target/scripts/layout.toml"
harness_injected=0
if [ -f "$lt" ] && ! grep -q '^\[harness\]' "$lt"; then
  spec="$(sed -n 's/^spec_version = "\(.*\)"/\1/p' "$init_src/stacks/$stack/scripts/layout.toml" | head -1)"
  spec="${spec:-0.1.0}"
  printf '\n# Harness identity (added by init): distribution channel + harness-project API revision.\n[harness]\nchannel = "%s"\nspec_version = "%s"\ntools = %s\nextensions = []\n' "$CHANNEL" "$spec" "$TOOLS_TOML" >> "$lt"
  harness_injected=1
fi

# 1c. Normalize channel and tool surfaces on a freshly scaffolded layout.toml.
# The skeleton ships channel="copy" and all four tools; set both to the
# requested values so the user's choice wins. A pre-existing project owns these
# lines — leave them untouched (the migration injection above wrote the requested
# values when it added the table).
if [ "$lt_pre" -eq 0 ] && [ -f "$lt" ]; then
  if grep -q '^channel = ' "$lt"; then
    _tmp="$(mktemp)"
    awk -v repl="channel = \"$CHANNEL\"" \
      '/^channel = / && !d {print repl; d=1; next} {print}' "$lt" > "$_tmp" && mv "$_tmp" "$lt"
  fi
  if grep -q '^tools = ' "$lt"; then
    _tmp="$(mktemp)"
    awk -v repl="tools = $TOOLS_TOML" \
      '/^tools = / && !d {print repl; d=1; next} {print}' "$lt" > "$_tmp" && mv "$_tmp" "$lt"
  fi
fi

# 2. docs/ brief roster from the doctor templates (project-owned defaults).
materialize_brief() { # <template-file> <target-rel>
  local t="$tpl/$1" d="$target/$2"
  [ -f "$t" ] || { echo "init: missing brief template $1" >&2; return 1; }
  if [ -e "$d" ]; then skipped=$((skipped + 1)); return 0; fi
  mkdir -p "$(dirname "$d")"
  cp -p "$t" "$d"
  fill "$d"
  created=$((created + 1))
}
materialize_brief prd.md                     docs/prd.md
materialize_brief system-design.md           docs/system-design.md
materialize_brief ubiquitous-language.md     docs/ubiquitous-language.md
materialize_brief testing-principles.md      docs/testing-principles.md
materialize_brief architecture-principles.md docs/architecture-principles.md
materialize_brief security-principles.md     docs/security-principles.md
materialize_brief adr-README.md              docs/adr/README.md

# 3. .gitignore. Manifest and marketplace deliver the runtime out-of-band, so it
# is materialized (or plugin-supplied) and never committed; copy commits the
# runtime, so only the handoff ledger is ignored. Both append once, guarded by a
# sentinel.
gi="$target/.gitignore"
touch "$gi"
appended=0
if [ "$CHANNEL" != "copy" ]; then
  if ! grep -qF 'Harness runtime —' "$gi"; then
    printf '\n' >> "$gi"
    cat "$init_src/core/gitignore-runtime.txt" >> "$gi"
    appended=1
  fi
else
  # copy channel: runtime is committed; ignore only the per-session ledger.
  if ! grep -qxF '.scratch/' "$gi"; then
    printf '\n# Handoff ledger (per-session, never committed)\n.scratch/\n' >> "$gi"
    appended=1
  fi
fi

# 4. Migration aid (manifest/marketplace). Under any out-of-band channel the
# runtime is gitignored, but a project migrating from the copy channel still has
# those files git-TRACKED (a new .gitignore does not untrack what is already
# committed). We never run git against the user's repo; we report the exact
# untrack command.
tracked_note=""
if [ "$CHANNEL" != "copy" ] && git -C "$target" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  runtime_paths=()
  while IFS= read -r line; do
    case "$line" in ''|\#*|.scratch/) continue ;; esac
    runtime_paths+=("${line%/\*}")            # .claude/skills/* -> .claude/skills
  done < "$init_src/core/gitignore-runtime.txt"
  # Declared extensions are project-owned and stay tracked — exclude them from the
  # untrack so the migration never strips the project's own skills/agents.
  ext_excludes=()
  if [ -f "$lt" ]; then
    ext_line="$(sed -n 's/^extensions = \[\(.*\)\].*/\1/p' "$lt" | head -1)"
    while IFS= read -r e; do [ -n "$e" ] && ext_excludes+=(":!$e"); done \
      < <(printf '%s\n' "${ext_line:-}" | grep -oE '"[^"]+"' | tr -d '"')
  fi
  if [ ${#runtime_paths[@]} -gt 0 ]; then
    tracked="$(git -C "$target" ls-files -- "${runtime_paths[@]}" ${ext_excludes[@]+"${ext_excludes[@]}"} 2>/dev/null || true)"
    if [ -n "$tracked" ]; then
      n=$(printf '%s\n' "$tracked" | grep -c .)
      tracked_note=", $n tracked-runtime-file(s)-need-untracking"
      echo "init: NOTE $n harness runtime file(s) are git-tracked; untrack them for the $CHANNEL channel:" >&2
      # --ignore-unmatch: a partial-tool project lacks some runtime paths;
      # without it git rm fails atomically on the first non-matching pathspec.
      # Quote each pathspec so the printed command survives a path with spaces.
      _hint=""
      for _p in "${runtime_paths[@]}"; do _hint+=" \"$_p\""; done
      for _e in ${ext_excludes[@]+"${ext_excludes[@]}"}; do _hint+=" \"$_e\""; done
      echo "  git -C \"$target\" rm -r --cached --ignore-unmatch$_hint" >&2
    fi
  fi
fi

echo "init stack=$stack channel=$CHANNEL tools=$TOOLS_TOML: $created created, $skipped pre-existing kept, gitignore-block-appended=$appended, harness-table-injected=$harness_injected$tracked_note → $target"
