#!/usr/bin/env bash
# Harness-owned quality-gate dispatcher — the lifecycle verb contract.
#
#   scripts/gate.sh <verb>     run one lifecycle verb
#   scripts/gate.sh verify     run every verb in gate order (the full quality gate)
#   scripts/gate.sh list       print the canonical verb surface
#
# This file is owned by the harness. It defines WHICH verbs exist, the order
# `verify` runs them in, and the rule that an unimplemented verb fails. It is
# replaced on every materialize; do not edit it. Bind the verbs to a technology
# by implementing the verb_<name> functions in scripts/stack.sh — the one file
# a project owner fills in.
#
# The pipeline, the agents, and the code-quality-gate skill speak only in these
# verbs, never in tool names. That indirection is what keeps the harness
# stack-agnostic: the same pipeline drives any technology once stack.sh binds
# the verbs to it.
set -uo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

# The canonical verb surface, in gate order. `verify` runs them top to bottom.
# Adding or reordering a verb is a harness-level change, not a project one.
VERBS=(deps format lint test build)

usage() {
  printf 'usage: %s <%s|verify|list>\n' "${0##*/}" "$(IFS='|'; echo "${VERBS[*]}")" >&2
}

# Fail-honest default: a verb with no verb_<name> in stack.sh is unimplemented.
# It must fail, never silently pass — a half-adapted stack cannot clear a gate
# it has not satisfied.
run_verb() {
  local verb="$1"
  if ! declare -F "verb_${verb}" >/dev/null 2>&1; then
    printf 'gate: verb %q has no verb_%s in scripts/stack.sh — not implemented yet\n' "$verb" "$verb" >&2
    return 1
  fi
  # Run in a subshell so a verb body that calls `exit` (instead of `return`)
  # cannot abort the dispatcher and mask the verbs after it — `verify` must run
  # every verb to completion and report them all.
  ( "verb_${verb}" )
}

# stack.sh holds the project-owned bodies. Its absence is itself a failure: an
# unbound stack must not pass.
stack="$here/stack.sh"
if [ ! -f "$stack" ]; then
  printf 'gate: scripts/stack.sh not found — the stack is not bound yet\n' >&2
  exit 1
fi
# shellcheck source=/dev/null
. "$stack"

cmd="${1:-verify}"
case "$cmd" in
  list)
    printf '%s\n' "${VERBS[@]}"
    ;;
  verify)
    # Run every verb so the report names every failure at once — including each
    # unimplemented verb on a freshly bound stack. Verbs are independent; a
    # failure does not abort the run, it sets the exit code.
    rc=0
    for v in "${VERBS[@]}"; do
      printf '== %s ==\n' "$v"
      if run_verb "$v"; then
        printf 'gate: %s OK\n' "$v"
      else
        printf 'gate: %s FAILED\n' "$v" >&2
        rc=1
      fi
    done
    if [ "$rc" -ne 0 ]; then
      printf 'gate: quality gate FAILED — see failing verbs above\n' >&2
    else
      printf 'gate: quality gate passed\n'
    fi
    exit "$rc"
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    for v in "${VERBS[@]}"; do
      if [ "$v" = "$cmd" ]; then
        run_verb "$cmd"
        exit $?
      fi
    done
    printf 'gate: unknown verb %q\n' "$cmd" >&2
    usage
    exit 2
    ;;
esac
