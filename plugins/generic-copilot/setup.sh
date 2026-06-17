#!/usr/bin/env bash
# Install the harness engine sliver into the consuming project.
#
#   bash <plugin>/setup.sh [target-project-dir]   # default: $PWD
#
# Run this ONCE after installing an agentic-harness plugin from the marketplace.
# The plugin (skills, agents, hooks) lives in your tool's read-only plugin cache;
# its skills invoke deterministic engines by PROJECT-relative paths — scripts/
# handoff.py, scripts/brief_doctor.py, schemas/scratch/…. Those engines must
# live in your project, not the cache, so the references resolve. This script
# copies them — bundled in the plugin under _engine/ — into the project, then
# appends the gitignore block so they stay untracked (the marketplace channel
# keeps the harness runtime out of git, like the manifest channel).
#
# Self-locating via $0: it copies its own sibling _engine/ payload, so it needs
# no environment variable. The marketplace-setup skill runs it with the plugin
# root expanded; you can also run it by hand from your project root.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
target_arg="${1:-$PWD}"
target="$(cd "$target_arg" && pwd)"
src="$here/_engine"
[ -d "$src" ] || { echo "setup: bundled engine payload not found at $src" >&2; exit 1; }

copied=0
while IFS= read -r -d '' f; do
  f="${f#./}"
  mkdir -p "$target/$(dirname "$f")"
  cp -p "$src/$f" "$target/$f"
  copied=$((copied + 1))
done < <(cd "$src" && find . -type f ! -name '.gitignore-block' -print0)

# Keep the engines untracked — the marketplace channel's doctor invariant. The
# bundled block is the canonical harness runtime gitignore; appended once.
gi="$target/.gitignore"
touch "$gi"
if [ -f "$src/.gitignore-block" ] && ! grep -qF 'Harness runtime —' "$gi"; then
  printf '\n' >> "$gi"
  cat "$src/.gitignore-block" >> "$gi"
fi

echo "harness engines installed: $copied file(s) into $target (gitignored, untracked)"
echo "next: provide the project-owned files (CLAUDE.md, scripts/layout.toml, docs/ briefs) via the harness 'init' if you have not already."
