#!/usr/bin/env python3
"""PreToolUse(Bash) hook — auto-allow the sanctioned handoff-log tool, defer everything else.

The pipeline's only sanctioned write to .scratch/handoff.jsonl is `python3
scripts/handoff.py append`, fed its record on stdin (a quoted heredoc). The
permission layer cannot pre-approve that form with a prefix allow-rule: a
heredoc embeds the record content, so every append is a new command string no
rule matches, and "always allow" saves it verbatim. The result is flaky
permission prompts on a routine, safe, append-only operation. This hook closes
that gap by inspecting the command and AUTO-ALLOWING it iff it is solely a
handoff.py invocation — covering the read queries and the heredoc append alike.

Safety model. The hook only ever ALLOWS or DEFERS; it never denies, so it can
never block another command. It allows ONLY when the command is exclusively a
handoff.py call: the command line must start with `python3 scripts/handoff.py`
and carry no shell metacharacter that could chain, redirect to a file, or
substitute another command ($ ` ; & | > ( )). The single exception is `<<` for
a heredoc, whose delimiter MUST be quoted (`<<'EOF'`) so the body is inert
data, and whose body must be terminated with nothing following the delimiter —
no trailing command can ride after the record. Anything else DEFERS (exit 0,
no decision) to the normal permission rules, so non-handoff bash is unaffected
and a malformed or unexpected handoff command merely prompts as before.

Fail safe: malformed stdin and an empty command DEFER. The hook widens nothing
on failure — the worst case is the prompt the pipeline had before this hook
existed. Like the SendMessage hook, it is a convenience backstop, not a sole
control; the whole-tool Bash grant and normal permission rules remain in force
for everything it does not explicitly allow.

Stdlib only. Tested by test_handoff_allow.py alongside this file.
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

# No chaining / redirection-to-file / substitution metacharacter may appear on
# the command line. `<` is the sole exception (heredoc / stdin redirect, both
# safe).
FORBIDDEN_METACHARS = frozenset("$`;&|>()")

# The only safe heredoc is the canonical append form with the redirection
# operator as the whole tail of the command line: a quoted delimiter at the
# very end, after a bare type token, with no other quoting or text. The reason
# is subtle but decisive — `<<` is a heredoc operator ONLY when unquoted. A
# `<<'EOF'` hidden inside a quoted argument is a literal string to the shell,
# so the lines that follow it are real commands, not an inert body. Telling
# the two apart by substring is impossible; only a strict whole-line match
# guarantees a genuine heredoc.
HEREDOC_APPEND_LINE = re.compile(
    r"^python3 scripts/handoff\.py append [A-Za-z0-9_-]+ "
    r"<<(?P<quote>['\"])(?P<delim>[A-Za-z_][A-Za-z0-9_]*)(?P=quote)$"
)


def body_ends_at_delimiter(body, delimiter):
    """True iff the heredoc body terminates and nothing executable follows.

    Even a genuine heredoc runs any line after the closing delimiter, so the
    body must end at the delimiter line with at most blank (space/tab) lines
    following it.
    """
    seen = False
    for line in body.split("\n"):
        if seen:
            if line.strip(" \t"):
                return False
        elif line == delimiter:
            seen = True
    return seen


def is_sanctioned(command):
    """True iff the command is exclusively a handoff.py invocation."""
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

    # No heredoc: there must be no trailing physical line carrying another
    # command.
    return rest.strip() == ""


def decide(payload_text):
    """The allow decision for one hook payload, or None to defer."""
    try:
        payload = json.loads(payload_text)
        command = payload.get("tool_input", {}).get("command", "")
    except (json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(command, str) or not command:
        return None
    return ALLOW_DECISION if is_sanctioned(command) else None


def main():
    try:
        decision = decide(sys.stdin.read())
    except Exception:  # never break the permission chain — defer
        return 0
    if decision is not None:
        print(decision)
    return 0


if __name__ == "__main__":
    sys.exit(main())
