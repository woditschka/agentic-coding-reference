#!/usr/bin/env python3
"""Auto-allow a Bash command that is solely a handoff.py invocation, and defer everything else.

A PreToolUse backstop: it never denies, and a malformed payload defers, so the
worst case is the permission prompt the pipeline had before it existed.
"""

import json
import re
import sys

ALLOW_DECISION = json.dumps(
    {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    },
    separators=(",", ":"),
)

SANCTIONED_PREFIX = "python3 scripts/handoff.py "

# No chaining, file redirection, or substitution metacharacter may appear on
# the command line; `<` alone is safe (a heredoc or a stdin redirect).
FORBIDDEN_METACHARS = frozenset("$`;&|>()")

# `<<` is a heredoc operator only when unquoted: a `<<'EOF'` inside a quoted
# argument is a literal string, and the lines after it are real commands. No
# substring test can tell the two apart, so only the canonical append line,
# matched whole with the quoted delimiter as its tail, counts as a heredoc.
HEREDOC_APPEND_LINE = re.compile(
    r"^python3 scripts/handoff\.py append [A-Za-z0-9_-]+ "
    r"<<(?P<quote>['\"])(?P<delim>[A-Za-z_][A-Za-z0-9_]*)(?P=quote)$"
)


def body_ends_at_delimiter(body: str, delimiter: str) -> bool:
    """Report whether the heredoc body closes at its delimiter with nothing executable after it."""
    # Even a genuine heredoc runs any line after the closing delimiter.
    seen = False
    for line in body.split("\n"):
        if seen:
            if line.strip(" \t"):
                return False
        elif line == delimiter:
            seen = True
    return seen


def is_sanctioned(command: str) -> bool:
    """Report whether the command is exclusively a handoff.py invocation."""
    first, _, rest = command.partition("\n")
    first = first.lstrip()
    if any(ch in FORBIDDEN_METACHARS for ch in first):
        return False
    if not first.startswith(SANCTIONED_PREFIX):
        return False
    if "<<" in first:
        match = HEREDOC_APPEND_LINE.match(first)
        if not match:
            return False
        return body_ends_at_delimiter(rest, match.group("delim"))
    return rest.strip() == ""


def decide(payload_text: str) -> str | None:
    """Return the allow decision for one hook payload, or None to defer."""
    try:
        payload = json.loads(payload_text)
        command = payload.get("tool_input", {}).get("command", "")
    except (json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(command, str) or not command:
        return None
    return ALLOW_DECISION if is_sanctioned(command) else None


def main() -> int:
    """Print the decision for the payload on stdin, or nothing to defer."""
    try:
        decision = decide(sys.stdin.read())
    except Exception:  # noqa: BLE001 — a backstop never breaks the permission chain; it defers
        return 0
    if decision is not None:
        print(decision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
