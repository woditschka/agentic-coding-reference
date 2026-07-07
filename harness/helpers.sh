# Shared rosters and helpers for the harness/*.sh tooling. Source it, never run
# it. Producer-side only: nothing here ships to a sample or a plugin.
#
#   here="$(cd "$(dirname "$0")" && pwd)"
#   . "$here/helpers.sh"
#
# The rosters mirror helpers.py (the source) for the remaining bash
# orchestrators; check-sync's HelperRosterParity test gates the copies.
# Everything else — stack detection, tool→directory mappings — lives ONLY in
# helpers.py (the TOOLS registry); shell callers shell out to it.
# shellcheck shell=bash

# --- rosters --------------------------------------------------------------
# shellcheck disable=SC2034  # consumed by the sourcing scripts
STACKS=(go java-spring-boot generic)
# shellcheck disable=SC2034
PLUGIN_TOOLS=(claude copilot junie)          # OpenCode is not a plugin target
# shellcheck disable=SC2034
ALL_TOOLS=(claude copilot opencode junie)

# --- helpers ---------------------------------------------------------------
note() { printf '== %s ==\n' "$1"; }

# read_stamp <file> <caller-label> — print a VERSION/VERSION-DATE stamp,
# whitespace-stripped; fail loud on a missing or empty file.
read_stamp() {
  local v
  [ -f "$1" ] || { echo "$2: missing $1" >&2; return 1; }
  v="$(tr -d '[:space:]' < "$1")"
  [ -n "$v" ] || { echo "$2: $1 is empty" >&2; return 1; }
  printf '%s\n' "$v"
}

# empty_chapter <claude-md> <heading> — blank a managed chapter's body in
# place, keeping the heading (test helper: simulates a consumer whose chapter
# content was lost, so a re-run of the refresh must refill it). The heading is
# matched by exact string equality; awk -v processes backslash escapes, so pass
# backslash-free headings only.
empty_chapter() {
  awk -v h="$2" '$0==h{print; skip=1; next} skip&&/^## /{skip=0} skip{next} {print}' \
    "$1" > "$1.x" && mv "$1.x" "$1"
}
