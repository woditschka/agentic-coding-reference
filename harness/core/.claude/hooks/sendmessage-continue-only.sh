#!/usr/bin/env bash
# PreToolUse hook — constrain SendMessage to a bare continuation.
#
# Resume of an interrupted sub-agent is allowed ONLY as the literal "continue".
# This preserves recovery-by-continuation while making payload smuggling
# impossible: an allowlist (only "continue" passes; everything else is denied by
# default) means no phrasing can inject a new, unrouted instruction through the
# resume channel. New work is routed as a fresh Agent dispatch, on the ledger.
#
# exit 2 is the blocking contract (stderr is surfaced to the model). Any other
# non-zero exit is treated as a NON-blocking error by the harness. This script
# only ever exits 0 (allow) or 2 (deny): malformed stdin, a missing message
# field, and even a missing jq all yield an empty `norm`, which hits the `*)`
# arm and DENIES (fails CLOSED). The only fail-OPEN path is the harness being
# unable to launch this script at all — file missing, `CLAUDE_PROJECT_DIR`
# unset, or no bash — e.g. if .claude/settings.json (which enables the flag and
# references this hook) is committed without this file. Commit the two together.
# It is a Layer-2 backstop, not a sole control; Layer 1 (doctrine) and Layer 3
# (the audit-agents review) cover it.
payload=$(cat)
msg=$(jq -r '.tool_input.message // empty' <<<"$payload" 2>/dev/null)
norm=$(printf '%s' "$msg" | tr '[:upper:]' '[:lower:]' | xargs 2>/dev/null)
case "$norm" in
  continue|continue.)
    exit 0 ;;
  *)
    echo "SendMessage may only carry the literal 'continue' (bare resume of an interrupted sub-agent). Route new instructions as a fresh Agent dispatch — resume cannot smuggle new work." >&2
    exit 2 ;;
esac
