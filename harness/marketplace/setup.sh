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
# ensures the gitignore block present so they stay untracked (the marketplace
# channel keeps the harness runtime out of git, like the manifest channel). The
# gitignore refresh is ensure-present and re-runs on every upgrade, so a newly
# added runtime path reaches an already-installed project.
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
# bundled refresh ensures every harness runtime path present, additively: a fresh
# install gains the whole block, and a plugin UPGRADE that added a runtime path
# reaches an already-installed project (the append-once freeze this replaces did
# not). Ensure-present only — a project's own ignores are never touched. This is
# the marketplace equivalent of materialize.py's Tier-1 refresh on the copy
# channel; it re-runs on every setup, like the managed-chapters refresh below.
gi="$target/.gitignore"
if [ -f "$here/refresh-gitignore.py" ] && [ -f "$src/.gitignore-block" ]; then
  gi_status="$(python3 "$here/refresh-gitignore.py" "$gi" "$src/.gitignore-block" marketplace)"
  echo "$gi_status"
fi

echo "harness engines installed: $copied file(s) into $target (gitignored, untracked)"

# Refresh the harness-managed chapters of CLAUDE.md, if the project has one. The
# chapters (Agent Usage, Memory, Writing Standards, Scratch Directory,
# Documentation Updates) are harness-owned doctrine, identified by their heading
# — this is the marketplace equivalent of what materialize.py does on the copy
# channel. The bundled claude-md/ stays in the read-only plugin cache; only the
# project's CLAUDE.md is written, and only its managed chapters. A project with
# no CLAUDE.md yet is scaffolded by 'init' (below), which fills the chapters.
if [ -f "$target/CLAUDE.md" ] && [ -f "$here/claude-md/refresh-chapters.py" ]; then
  ch="$(python3 "$here/claude-md/refresh-chapters.py" "$target/CLAUDE.md" "$here")"
  echo "managed chapters: $ch"
fi

echo "next: if you have no CLAUDE.md / scripts/layout.toml / docs/ briefs yet, scaffold the project-owned files via the harness 'init' (it fills the managed chapters), then re-run this setup."
