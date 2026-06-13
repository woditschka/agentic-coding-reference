#!/usr/bin/env bash
# Scaffold the project-OWNED files a harness consumer commits.
#
#   harness/init.sh <stack> <target-dir> <project-name> <project-description> <harness-version>
#
# This lays down only what the PROJECT owns and commits — its CLAUDE.md rules
# file, .claude/settings.json, scripts/layout.toml (with the channel
# declaration), the docs/ brief roster, and the .gitignore runtime block. It
# does NOT install the harness runtime: that is materialize.sh, which delivers
# the gitignored .claude/skills, agents, schemas, and scripts.
#
# init never overwrites a project file that already exists — re-running it only
# fills gaps. A greenfield setup runs init once, then materialize once (or just
# /seed, the wrapper that does both).
#
# Sources live in harness/init/ (core overlaid with stacks/<stack>) and the
# doctor's brief templates (harness/core/.claude/skills/doctor/templates).
set -euo pipefail

stack="${1:?usage: init.sh <stack> <target> <project-name> <project-description> <harness-version>}"
target_arg="${2:?usage: init.sh <stack> <target> <project-name> <project-description> <harness-version>}"
PROJECT_NAME="${3:?missing project-name}"
PROJECT_DESCRIPTION="${4:?missing project-description}"
HARNESS_VERSION="${5:?missing harness-version}"

here="$(cd "$(dirname "$0")" && pwd)"
target="$(cd "$target_arg" && pwd)"
init_src="$here/init"
tpl="$here/core/.claude/skills/doctor/templates"

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
  printf '\n# Harness identity (added by init): distribution channel + harness-project API revision.\n[harness]\nchannel = "manifest"\nspec_version = "%s"\n' "$spec" >> "$lt"
  harness_injected=1
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
materialize_brief adr-README.md              docs/adr/README.md

# 3. .gitignore: append the runtime block (and .scratch/) once, by sentinel.
gi="$target/.gitignore"
touch "$gi"
appended=0
if ! grep -qF 'Harness runtime — materialized from /harness' "$gi"; then
  printf '\n' >> "$gi"
  cat "$init_src/core/gitignore-runtime.txt" >> "$gi"
  appended=1
fi

# 4. Migration aid. Under the manifest channel the runtime is gitignored, but a
# project migrating from the copy channel still has those files git-TRACKED (a
# new .gitignore does not untrack what is already committed). We never run git
# against the user's repo; we report the exact command to untrack them.
tracked_note=""
if git -C "$target" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  runtime_paths=()
  while IFS= read -r line; do
    case "$line" in ''|\#*|.scratch/) continue ;; esac
    runtime_paths+=("$line")
  done < "$init_src/core/gitignore-runtime.txt"
  if [ ${#runtime_paths[@]} -gt 0 ]; then
    tracked="$(git -C "$target" ls-files -- "${runtime_paths[@]}" 2>/dev/null || true)"
    if [ -n "$tracked" ]; then
      n=$(printf '%s\n' "$tracked" | grep -c .)
      tracked_note=", $n tracked-runtime-file(s)-need-untracking"
      echo "init: NOTE $n harness runtime file(s) are git-tracked; untrack them for the manifest channel:" >&2
      # --ignore-unmatch: a partial-tool project lacks some runtime paths;
      # without it git rm fails atomically on the first non-matching pathspec.
      echo "  git -C \"$target\" rm -r --cached --ignore-unmatch ${runtime_paths[*]}" >&2
    fi
  fi
fi

echo "init stack=$stack: $created created, $skipped pre-existing kept, gitignore-block-appended=$appended, harness-table-injected=$harness_injected$tracked_note → $target"
