#!/usr/bin/env bash
# Real-CLI local install test for the marketplace (plugin) channel.
#
# test-marketplace.sh proves the channel by SIMULATION — it copies a rendered
# plugin and runs its setup.sh. This test instead drives the ACTUAL `claude
# plugin` CLI against this repo as a LOCAL-PATH marketplace, proving the real
# `marketplace add` + `install` path lands the plugin with its bundled surfaces,
# engine payload, and setup skill — then runs that installed setup.sh end to end.
#
# It is fully ISOLATED: it runs under a throwaway HOME, so BOTH the marketplace
# registry and the plugin cache (which the CLI writes to $HOME/.claude/plugins/
# cache, ignoring CLAUDE_CONFIG_DIR) land under the temp dir — the user's real
# plugin state is never touched and cleanup is a single rm. It SKIPS cleanly
# (exit 0) when the `claude` CLI is not on PATH, so machines without it — and the
# rest of verify-harness — are unaffected.
#
#   harness/tests/test-plugin-install.sh        # needs bash, git, python3, claude
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
harness="$(cd "$here/.." && pwd)"
root="$(cd "$harness/.." && pwd)"
cd "$root"

# shellcheck source=harness/registry.sh
. "$harness/registry.sh"   # read_stamp, empty_chapter

version="$(read_stamp "$harness/VERSION" test-plugin-install)"
plugin="go-claude"   # the CLI path is plugin-agnostic; all three stacks are
                     # covered by test-marketplace.sh's simulation.

if ! command -v claude >/dev/null 2>&1; then
  echo "SKIP: claude CLI not on PATH — real plugin-install test not run"
  exit 0
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
# Isolate via HOME — the CLI writes the plugin CACHE to $HOME/.claude/plugins/cache
# regardless of CLAUDE_CONFIG_DIR, so only a throwaway HOME fully contains it.
export HOME="$tmp/home"
export CLAUDE_CONFIG_DIR="$HOME/.claude"
mkdir -p "$CLAUDE_CONFIG_DIR"

fail=0

# 1. Add this repo as a local marketplace, then install the plugin — the real CLI.
if ! claude plugin marketplace add "$root" >/dev/null 2>&1; then
  echo "FAIL: claude plugin marketplace add <repo> failed" >&2; exit 1
fi
if ! claude plugin install "${plugin}@agentic-harness" >/dev/null 2>&1; then
  echo "FAIL: claude plugin install ${plugin}@agentic-harness failed" >&2; exit 1
fi

# 2. The CLI installed it into the isolated cache with all bundled parts.
# `|| true` guards against SIGPIPE (141) from find when head closes early — under
# `set -o pipefail` that would otherwise abort the script before the empty-check.
cache="$(find "$tmp" -type d -path "*/${plugin}/${version}" 2>/dev/null | head -1 || true)"
if [ -z "$cache" ]; then
  echo "FAIL: installed plugin ${plugin}/${version} not found under the config dir" >&2; exit 1
fi
for f in setup.sh skills/marketplace-setup/SKILL.md .claude-plugin/plugin.json hooks/hooks.json; do
  [ -e "$cache/$f" ] || { echo "FAIL: installed plugin missing $f" >&2; fail=1; }
done
[ -d "$cache/_engine" ] || { echo "FAIL: installed plugin missing _engine/" >&2; fail=1; }
# the user-typed setup skill self-documents its namespaced invocation
grep -q "/${plugin}:marketplace-setup" "$cache/skills/marketplace-setup/SKILL.md" \
  || { echo "FAIL: installed setup skill missing namespaced invocation /${plugin}:marketplace-setup" >&2; fail=1; }

# 3. Run the setup.sh FROM THE INSTALLED CACHE into a fresh consumer — the real
#    post-install step a tool would take.
consumer="$tmp/consumer"
mkdir -p "$consumer"
git -C "$consumer" init -q
if ! python3 "$harness/init.py" go "$consumer" "real-install" "real cli install" "" "claude" marketplace >/dev/null 2>&1; then
  echo "FAIL: init (marketplace) failed" >&2; fail=1
elif ! bash "$cache/setup.sh" "$consumer" >/dev/null 2>&1; then
  echo "FAIL: installed setup.sh failed" >&2; fail=1
elif ! ( cd "$consumer" \
         && git check-ignore -q scripts/handoff.py \
         && python3 scripts/doctor.py check >/dev/null 2>&1 ); then
  echo "FAIL: post-install engines not gitignored, or doctor failed" >&2; fail=1
fi

# 3b. The INSTALLED cache must REFRESH the managed CLAUDE.md chapters, not just
#     install engines. init filled them from the in-repo source above; to exercise
#     the bundled managed-chapters.md + refresh-chapters.py in the real cache,
#     empty the Agent Usage chapter, re-run the cache setup.sh, and confirm it is
#     refilled — the real-CLI analogue of test-marketplace.sh's refresh assertion,
#     and the upgrade path (re-run setup after a plugin update).
if [ "$fail" -eq 0 ]; then
  empty_chapter "$consumer/CLAUDE.md" '## Agent Usage (Mandatory)'
  if grep -q 'Always use specialized agents' "$consumer/CLAUDE.md"; then
    echo "FAIL: test could not empty the Agent Usage chapter" >&2; fail=1
  elif ! bash "$cache/setup.sh" "$consumer" >/dev/null 2>&1; then
    echo "FAIL: installed setup.sh (refresh re-run) failed" >&2; fail=1
  elif ! grep -q 'Always use specialized agents' "$consumer/CLAUDE.md"; then
    echo "FAIL: installed setup.sh did not refresh the Agent Usage chapter from the bundled source" >&2; fail=1
  fi
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "PASS test-plugin-install: real marketplace add + install + setup green (${plugin}@${version})"
else
  echo "FAIL test-plugin-install: see failures above" >&2
  exit 1
fi
