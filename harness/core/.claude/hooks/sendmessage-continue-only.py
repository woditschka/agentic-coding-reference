#!/usr/bin/env python3
"""Constrain SendMessage to a bare "continue", the resume of an interrupted sub-agent.

A PreToolUse backstop that fails closed: anything but the literal continuation,
malformed input included, exits 2 with the reason on stderr, so no phrasing can
smuggle new work through the resume channel.
"""

import json
import re
import sys

ALLOW_EXIT = 0
# Claude Code surfaces the stderr of exit 2 to the model and treats any other
# non-zero exit as a non-blocking error, so the deny is 2 and nothing else.
DENY_EXIT = 2

DENY_MESSAGE = (
    "SendMessage may only carry the literal 'continue' (bare resume of an "
    "interrupted sub-agent). Route new instructions as a fresh Agent dispatch "
    "— resume cannot smuggle new work."
)

ALLOWED = frozenset(("continue", "continue."))

# ASCII whitespace only: str.split() would also collapse Unicode whitespace
# and widen the allowlist to decorated forms it never vetted.
_ASCII_WS = re.compile(r"[ \t\r\n\f\v]+")


def normalized_message(payload_text: str) -> str:
    """Return the message lowercased and whitespace-collapsed, or '' on any malformation."""
    try:
        payload = json.loads(payload_text)
        message = payload.get("tool_input", {}).get("message", "")
    except (json.JSONDecodeError, AttributeError):
        return ""
    if not isinstance(message, str):
        return ""
    return _ASCII_WS.sub(" ", message).strip(" ").lower()


def decide(payload_text: str) -> int:
    """Return the exit code for one payload: allow the bare continuation, deny anything else."""
    return ALLOW_EXIT if normalized_message(payload_text) in ALLOWED else DENY_EXIT


def main() -> int:
    """Decide for the payload on stdin and print the reason when denying."""
    try:
        code = decide(sys.stdin.read())
    except Exception:  # noqa: BLE001 — an unexpected failure still fails closed
        code = DENY_EXIT
    if code != ALLOW_EXIT:
        print(DENY_MESSAGE, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
