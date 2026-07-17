#!/usr/bin/env python3
"""PreToolUse(Write|Edit|MultiEdit|NotebookEdit + Bash) hook — deny raw writes
to the handoff log, defer everything else.

The pipeline's only sanctioned write to .scratch/handoff.jsonl is `python3
scripts/handoff.py append` (the handoff-allow.py hook pre-approves exactly
that form). This guard closes the other direction: an agent that tries to
write the log directly — an Edit/Write tool call on the file, or a shell
redirection / tee onto it — is DENIED with a message naming the sanctioned
path. A raw write skips schema validation and canonical formatting; one
missing trailing newline glues two records onto a line and the log stops
parsing.

Safety model. The guard denies ONLY unquoted redirect/tee signatures that
target the log path, scanned outside single-line quoted strings and outside
a quoted heredoc body (both are inert data — a command may legitimately
*mention* the forbidden form, e.g. a commit message or a doc edit; a quote
pair spanning a newline is NOT stripped, so a multi-line quoted mention
still denies — a recoverable false positive, never a bypass). A sanctioned
`python3 scripts/handoff.py` first line free of shell metacharacters is
handoff-allow.py's jurisdiction and is dropped from the scan — but its
trailing lines stay scanned, so a redirect chained after the heredoc closer
is still denied. handoff-allow.py only ALLOWS when nothing follows the
closer, so a deny here can never override its ALLOW. Everything else DEFERS
(exit 0, no decision) to the normal permission rules.

Fail direction: malformed stdin or a signature hidden in a shape the scan
does not parse DEFERS or is missed — the guard is a convenience backstop,
not the sole control. The deterministic, cross-tool backstop is the quality
gate's `python3 scripts/handoff.py validate` step, which fails on any
corrupted log regardless of which tool or agent wrote it. Commit this hook
together with .claude/settings.json.

Stdlib only. Tested by test_handoff_log_guard.py alongside this file.
"""

import json
import re
import sys

DENY_REASON = (
    "Raw writes to .scratch/handoff.jsonl are prohibited. Append through the "
    "logic layer instead: python3 scripts/handoff.py append <type> with the "
    "record on stdin via a quoted heredoc (see the handoff-append skill)."
)

DENY_DECISION = json.dumps(
    {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": DENY_REASON,
        }
    },
    separators=(",", ":"),
)

WRITE_TOOLS = frozenset(("Write", "Edit", "MultiEdit", "NotebookEdit"))

# The log path as a file-path target: absolute and nested forms count;
# foo.scratch/... does not. MULTILINE keeps grep's per-line semantics — a
# path argument smuggling the log name after a newline still denies.
FILE_PATH_TARGET = re.compile(r"(^|/)\.scratch/handoff\.jsonl$", re.MULTILINE)

# The log path as a shell token: preceded by start-of-token or a slash,
# followed by a hard token end. Scanned per physical line; _WS is any
# whitespace except newline.
_WS = r"[^\S\n]"
PATH_SEG = r"(\S*/)?\.scratch/handoff\.jsonl(" + _WS + r"|[;&|)]|$)"
REDIRECT_SIGNATURE = re.compile(r">{1,2}" + _WS + r"*" + PATH_SEG)
TEE_SIGNATURE = re.compile(
    r"(^|[;&|]|" + _WS + r")tee" + _WS + r"+((-a|--append)" + _WS + r"+)?" + PATH_SEG
)

# A quoted heredoc on the command line: its body is inert data. The greedy
# leading .* picks the LAST heredoc marker on the line, matching the original
# scan. `<<-` closes on a tab-indented delimiter.
QUOTED_HEREDOC = re.compile(r".*<<-?['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]")
DASHED_HEREDOC = re.compile(r"<<-['\"]")

SANCTIONED_PREFIX = "python3 scripts/handoff.py "
SANCTIONED_LINE_METACHARS = re.compile(r"[;&|>()$`]")

SINGLE_QUOTED = re.compile(r"'[^'\n]*'")
DOUBLE_QUOTED = re.compile(r'"[^"\n]*"')


def drop_quoted_heredoc_body(first, rest):
    """The lines of `rest` after a quoted heredoc body, delimiter included.

    A quoted heredoc body is inert data and leaves the scan; an unquoted
    heredoc expands and stays scanned. Lines after the closing delimiter stay
    scanned in every case.
    """
    match = QUOTED_HEREDOC.match(first)
    if not match or not rest:
        return rest
    delimiter = match.group(1)
    dashed = DASHED_HEREDOC.search(first) is not None
    kept = []
    seen = False
    for line in rest.split("\n"):
        if seen:
            kept.append(line)
            continue
        candidate = line.lstrip("\t") if dashed else line
        if candidate == delimiter:
            seen = True
    return "\n".join(kept)


def strip_quoted(line):
    """The line with single-line quoted segments removed (inert data).

    A quoted-path redirect is therefore missed by design — the gate's
    validate step catches it. A quote pair spanning a newline is not
    stripped, so a multi-line quoted mention still denies.
    """
    return DOUBLE_QUOTED.sub("", SINGLE_QUOTED.sub("", line))


def bash_command_denies(command):
    """True iff the command carries a raw redirect/tee onto the log."""
    first, _, rest = command.partition("\n")
    first = first.lstrip()

    rest = drop_quoted_heredoc_body(first, rest)

    # A sanctioned handoff.py first line free of shell metacharacters is
    # handoff-allow.py's jurisdiction — drop the line and its inert record
    # body from the scan. Its trailing lines stay: a redirect chained after
    # the heredoc closer must still deny.
    if first.startswith(SANCTIONED_PREFIX) and not SANCTIONED_LINE_METACHARS.search(
        first
    ):
        scan = rest
    else:
        scan = first + "\n" + rest if rest else first

    for line in scan.split("\n"):
        line = strip_quoted(line)
        if REDIRECT_SIGNATURE.search(line) or TEE_SIGNATURE.search(line):
            return True
    return False


def decide(payload_text):
    """The deny decision for one hook payload, or None to defer."""
    try:
        payload = json.loads(payload_text)
        tool = payload.get("tool_name", "")
        tool_input = payload.get("tool_input", {})
    except (json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(tool_input, dict):
        return None

    if tool in WRITE_TOOLS:
        file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if isinstance(file_path, str) and FILE_PATH_TARGET.search(file_path):
            return DENY_DECISION
        return None

    if tool == "Bash":
        command = tool_input.get("command", "")
        if isinstance(command, str) and command and bash_command_denies(command):
            return DENY_DECISION
        return None

    return None


def main():
    try:
        decision = decide(sys.stdin.read())
    except Exception:  # backstop, not sole control — defer, never crash the chain
        return 0
    if decision is not None:
        print(decision)
    return 0


if __name__ == "__main__":
    sys.exit(main())
