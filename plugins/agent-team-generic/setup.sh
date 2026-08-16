#!/usr/bin/env bash
# Install the harness engine sliver into the consuming project.
#
#   bash <plugin>/setup.sh [target-project-dir]   # default: $PWD
#
# Run this after installing an agent-team plugin from the marketplace,
# and AGAIN after every plugin update: the plugin cache advances on update,
# but the project-side engines and managed chapters advance only here.
# The plugin (skills, agents, hooks) lives in the tool's read-only plugin cache;
# its skills invoke deterministic engines by PROJECT-relative paths — scripts/
# handoff.py, scripts/doctor.py, schemas/scratch/…. Those engines must
# live in the project, not the cache, so the references resolve. This script
# copies them — bundled in the plugin under _engine/ — into the project, then
# ensures the gitignore block present so they stay untracked (the marketplace
# channel keeps the harness runtime out of git, like the manifest channel). The
# gitignore refresh is ensure-present and re-runs on every upgrade, so a newly
# added runtime path reaches an already-installed project.
#
# Self-locating via $0: it copies its own sibling _engine/ payload, so it needs
# no environment variable. The marketplace-setup skill runs it with the plugin
# root expanded; or run it by hand from the project root.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
target_arg="${1:-$PWD}"
target="$(cd "$target_arg" && pwd)"
src="$here/_engine"
[ -d "$src" ] || { echo "setup: bundled engine payload not found at $src" >&2; exit 1; }

# Channel sanity: this script is the marketplace channel's installer. A
# layout.toml declaring another channel means a later /materialize would
# install the full runtime beside the plugin's namespaced surfaces (skills,
# agents, and hooks all loaded twice). Advisory only — the declaration is
# project-owned and setup never edits it. Runs BEFORE install and verify: the
# vendored suites enforce channel invariants inside the target, so on a
# mis-declared channel they fail — this warning must reach the consumer first,
# or the verify failure below misreads as host breakage.
layout="$target/scripts/layout.toml"
if [ -f "$layout" ]; then
  # Scope to the [harness] table (first sed range), so a 'channel' key in a
  # project-owned table cannot satisfy or confuse the check. Tolerate
  # whitespace, single or double quotes, and a trailing comment; the trailing
  # .* also keeps any bytes after the value out of the echo below.
  declared="$(sed -n '/^\[harness\]/,/^\[/p' "$layout" \
    | sed -n "s/^[[:space:]]*channel[[:space:]]*=[[:space:]]*[\"']\([a-z]*\)[\"'].*/\1/p" \
    | head -n 1)"
  if [ "${declared:-}" != "marketplace" ]; then
    echo "WARNING: $layout declares channel = \"${declared:-<unset>}\" — this is a marketplace install." >&2
    echo "         Set '[harness] channel = \"marketplace\"' or a later /materialize will install the full runtime beside the plugin." >&2
    echo "         If the install-time verification below fails, fix the declaration first — the vendored suites enforce channel invariants." >&2
  fi
fi

# Pre-v0.2.0 registration keys: the agent-team rename made any settings entry
# keyed on the old agentic-harness marketplace dead config — updates silently
# stop matching. Advisory; the doctor's legacy-keys check repeats it.
for settings in "$target/.claude/settings.json" "$target/.claude/settings.local.json"; do
  if [ -f "$settings" ] && grep -q 'agentic-harness' "$settings"; then
    echo "WARNING: $settings still references the pre-v0.2.0 'agentic-harness' marketplace." >&2
    echo "         Migrate once: remove that marketplace, add agent-team, reinstall the plugin, re-run this setup (adoption guide § Upgrading)." >&2
  fi
done

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
# One bound on that parity: setup copies additively and never removes a retired
# engine file — a leftover stays gitignored and inert until removed by hand.
gi="$target/.gitignore"
if [ -f "$here/refresh-gitignore.py" ] && [ -f "$src/.gitignore-block" ]; then
  gi_status="$(python3 "$here/refresh-gitignore.py" "$gi" "$src/.gitignore-block" marketplace)"
  echo "$gi_status"
fi

echo "harness engines installed: $copied file(s) into $target (gitignored, untracked)"

# Install-time verification — the marketplace twin of materialize.py's
# verify_runtime (ADR 2026-07-13 in the reference: project builds run no
# harness suites; the install verifies what it copied). The scripts suites run
# as one `unittest` invocation naming exactly the sliver's own modules (ADR
# 2026-08-16 exact-module-install-verification), so a project-authored test
# module under scripts/tests/ is never run as a suite; the suites still import
# from the target tree, so the trust boundary on the target stands. A failure
# means the installed runtime is broken on this host (broken copy, python
# incompatibility) — fail loud now, not mid-pipeline.
fails=0
suites=0
script_count=0
script_modules=()
hook_suites=()
while IFS= read -r -d '' f; do
  f="${f#./}"
  # Same suite contract as materialize.py's _installed_suites: a file under
  # scripts/ or .claude/hooks/ whose NAME starts test_ and ends .py — the
  # basename check keeps the two twins agreeing on nested paths.
  case "$f" in scripts/*|.claude/hooks/*) ;; *) continue ;; esac
  case "${f##*/}" in test_*.py) ;; *) continue ;; esac
  suites=$((suites + 1))
  case "$f" in
    scripts/*)
      # scripts/tests/handoff/test_x.py -> tests.handoff.test_x
      m="${f#scripts/}"; m="${m%.py}"; m="${m//\//.}"
      script_modules+=("$m")
      script_count=$((script_count + 1))
      ;;
    .claude/hooks/*) hook_suites+=("$f") ;;
  esac
done < <(cd "$src" && find . -type f -print0)
# Run from the scripts dir so `import handoff` and `import tests.*` resolve
# (ADR 2026-07-17 runtime-package-layout). A missing suite file is an import
# error the run reports; a package missing its __init__.py resolves as a
# namespace package and its suites still run — the doctor's runtime roster
# pins every shipped __init__.py. The zero-tests check catches a truncated
# copy that imports clean and runs nothing; an all-skipped run is not a
# failure. Diagnostics mirror materialize.py's: keep the last stderr lines
# so a failure names its cause.
# The script_count check is load-bearing twice over: `python3 -m unittest`
# with no module arguments IS `discover` over the target's tests tree — the
# exact thing the exact-module contract forbids — and on bash 3.2 (stock
# macOS) with `set -u`, expanding an empty array is an unbound-variable
# error. The `--` keeps a module name from ever parsing as an option.
# The interpreter must see only the bytes this install laid down: a stale
# __pycache__ artifact can stay import-valid across the mtime-preserving
# copy. Purge before running anything.
for d in "$target/scripts" "$target/.claude/hooks"; do
  if [ -d "$d" ]; then
    find "$d" -type d -name __pycache__ -prune -exec rm -rf {} +
  fi
done
if [ "$script_count" -gt 0 ]; then
  # Sort for a deterministic argv matching materialize.py's sorted() twin;
  # module names are dot/word characters, so line-splitting is safe. -E
  # ignores PYTHON* env vars: the caller's PYTHONPATH must never put foreign
  # roots on the verification interpreter's sys.path; -B keeps the run
  # from writing __pycache__ into the consumer's tree.
  sorted_modules=()
  while IFS= read -r m; do sorted_modules+=("$m"); done \
    < <(printf '%s\n' "${script_modules[@]}" | sort)
  if ! err="$( (cd "$target/scripts" && python3 -E -B -m unittest -- "${sorted_modules[@]}") 2>&1 >/dev/null )"; then
    echo "verify: scripts/tests suite run FAILED" >&2
    # Suite output is target-influenced; strip control characters (C0 minus
    # tab, and DEL) so a raw ESC cannot rewrite the operator's terminal.
    printf '%s\n' "$err" | tail -n 5 | tr -d '\000-\010\013-\037\177' | sed 's/^/  /' >&2
    fails=$((fails + 1))
  elif ! printf '%s\n' "$err" | grep -Eq 'Ran [1-9][0-9]* tests?' \
      && ! printf '%s\n' "$err" | grep -Eq '\(skipped=[0-9]+\)'; then
    echo "verify: scripts/tests suite run ran zero tests — suites empty or truncated" >&2
    fails=$((fails + 1))
  fi
fi
# hook_suites may be empty (today's engine sliver ships no hooks); the guarded
# expansion keeps `set -u` happy on bash 3.2 (stock macOS), where expanding an
# empty array is an unbound-variable error.
for f in ${hook_suites[@]+"${hook_suites[@]}"}; do
  if ! err="$( (cd "$target" && python3 -E -B "$f") 2>&1 >/dev/null )"; then
    echo "verify: $f FAILED" >&2
    printf '%s\n' "$err" | tail -n 5 | tr -d '\000-\010\013-\037\177' | sed 's/^/  /' >&2
    fails=$((fails + 1))
  fi
done
if [ "$fails" -gt 0 ]; then
  echo "setup: $fails installed suite(s) failed — the runtime is not healthy on this host" >&2
  exit 1
fi
echo "verified: $suites vendored suite(s) pass on this host"

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

echo "next: if the project has no CLAUDE.md / scripts/layout.toml / docs/ briefs yet, scaffold the project-owned files via the plugin's init skill (it fills the managed chapters and pins the marketplace channel), then re-run this setup."
echo "upgrades: after every 'plugin update', re-run this setup — the update advances only the cached plugin surfaces; the project-side engines and chapters update here."
