#!/usr/bin/env python3
"""PreToolUse hook — constrain SendMessage to a bare continuation.

Resume of an interrupted sub-agent is allowed ONLY as the literal "continue".
This preserves recovery-by-continuation while making payload smuggling
impossible: an allowlist (only "continue" passes; everything else is denied by
default) means no phrasing can inject a new, unrouted instruction through the
resume channel. New work is routed as a fresh Agent dispatch, on the ledger.

exit 2 is the blocking contract (stderr is surfaced to the model). Any other
non-zero exit is treated as a NON-blocking error by the harness. This script
only ever exits 0 (allow) or 2 (deny): malformed stdin, a missing message
field, and a non-string message all normalize to an empty string and DENY
(fails CLOSED). Normalization is lowercase plus ASCII-whitespace collapse — a
quoted, decorated, or Unicode-whitespace-padded "continue" is denied, which
errs closed. The only fail-OPEN path
is the harness being unable to launch this script at all — file missing,
`CLAUDE_PROJECT_DIR` unset, or no python3 — e.g. if .claude/settings.json
(which enables the flag and references this hook) is committed without this
file. Commit the two together. It is a Layer-2 backstop, not a sole control;
Layer 1 (doctrine) and Layer 3 (the audit-agents review) cover it.

Stdlib only. Tested by test_sendmessage_continue_only.py alongside this file.
"""

import json
import re
import sys

DENY_MESSAGE = (
    "SendMessage may only carry the literal 'continue' (bare resume of an "
    "interrupted sub-agent). Route new instructions as a fresh Agent dispatch "
    "— resume cannot smuggle new work."
)

ALLOWED = frozenset(("continue", "continue."))

# ASCII whitespace only. str.split() would also collapse Unicode whitespace
# (NBSP, U+2028, …), silently widening the allowlist to decorated forms the
# allowlist never vetted — any non-ASCII-whitespace character must survive
# normalization and hit the deny arm.
_ASCII_WS = re.compile(r"[ \t\r\n\f\v]+")


def normalized_message(payload_text):
    """The message lowercased and ASCII-whitespace-collapsed; '' on any malformation."""
    try:
        payload = json.loads(payload_text)
        message = payload.get("tool_input", {}).get("message", "")
    except (json.JSONDecodeError, AttributeError):
        return ""
    if not isinstance(message, str):
        return ""
    return _ASCII_WS.sub(" ", message).strip(" ").lower()


def decide(payload_text):
    """0 to allow, 2 to deny — the only two exits this hook ever takes."""
    return 0 if normalized_message(payload_text) in ALLOWED else 2


def main():
    try:
        code = decide(sys.stdin.read())
    except Exception:  # unexpected failure still fails CLOSED
        code = 2
    if code != 0:
        print(DENY_MESSAGE, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
