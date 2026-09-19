#!/usr/bin/env python3
"""Deny a raw write to the handoff log, and defer everything else.

A PreToolUse backstop over the write tools and Bash: the only sanctioned write
is `python3 scripts/handoff.py append`, and a malformed payload defers. The
deterministic control on every tool is `handoff.py validate` in the quality gate.
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

# The log path as a file-path target: absolute and nested forms count,
# foo.scratch/... does not. MULTILINE keeps per-line semantics, so a path
# argument smuggling the log name after a newline still denies.
FILE_PATH_TARGET = re.compile(r"(^|/)\.scratch/handoff\.jsonl$", re.MULTILINE)

# The log path as a shell token, scanned per physical line: preceded by a
# token start or a slash, followed by a hard token end.
_WS = r"[^\S\n]"
PATH_SEG = r"(\S*/)?\.scratch/handoff\.jsonl(" + _WS + r"|[;&|)]|$)"
REDIRECT_SIGNATURE = re.compile(r">{1,2}" + _WS + r"*" + PATH_SEG)
TEE_SIGNATURE = re.compile(
    r"(^|[;&|]|" + _WS + r")tee" + _WS + r"+((-a|--append)" + _WS + r"+)?" + PATH_SEG
)

# A quoted heredoc's body is inert data. The greedy leading .* picks the last
# heredoc marker on the line; `<<-` closes on a tab-indented delimiter.
QUOTED_HEREDOC = re.compile(r".*<<-?['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]")
DASHED_HEREDOC = re.compile(r"<<-['\"]")

SANCTIONED_PREFIX = "python3 scripts/handoff.py "
SANCTIONED_LINE_METACHARS = re.compile(r"[;&|>()$`]")

# A quote pair spanning a newline is not stripped, so a multi-line quoted
# mention still denies: a recoverable false positive, never a bypass.
SINGLE_QUOTED = re.compile(r"'[^'\n]*'")
DOUBLE_QUOTED = re.compile(r'"[^"\n]*"')


def drop_quoted_heredoc_body(first: str, rest: str) -> str:
    """Return the lines of `rest` after a quoted heredoc body, delimiter included."""
    # An unquoted heredoc expands and stays scanned; lines after the closing
    # delimiter stay scanned in every case.
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


def strip_quoted(line: str) -> str:
    """Return the line with its single-line quoted segments removed."""
    # A quoted-path redirect is therefore missed by design; the gate's
    # validate step catches it.
    return DOUBLE_QUOTED.sub("", SINGLE_QUOTED.sub("", line))


def bash_command_denies(command: str) -> bool:
    """Report whether the command carries a raw redirect or tee onto the log."""
    first, _, rest = command.partition("\n")
    first = first.lstrip()
    rest = drop_quoted_heredoc_body(first, rest)
    # A sanctioned handoff.py first line free of shell metacharacters is the
    # allow hook's jurisdiction and leaves the scan with its inert record
    # body; its trailing lines stay, so a redirect chained after the heredoc
    # closer still denies.
    if first.startswith(SANCTIONED_PREFIX) and not SANCTIONED_LINE_METACHARS.search(
        first
    ):
        scan = rest
    else:
        scan = first + "\n" + rest if rest else first
    return any(_line_writes_log(strip_quoted(line)) for line in scan.split("\n"))


def _line_writes_log(line: str) -> bool:
    return bool(REDIRECT_SIGNATURE.search(line) or TEE_SIGNATURE.search(line))


def decide(payload_text: str) -> str | None:
    """Return the deny decision for one hook payload, or None to defer."""
    try:
        payload = json.loads(payload_text)
        tool = payload.get("tool_name", "")
        tool_input = payload.get("tool_input", {})
    except (json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(tool_input, dict):
        return None
    if tool in WRITE_TOOLS:
        denies = _write_targets_log(tool_input)
    elif tool == "Bash":
        denies = _bash_writes_log(tool_input)
    else:
        denies = False
    return DENY_DECISION if denies else None


def _write_targets_log(tool_input: dict[str, object]) -> bool:
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    return isinstance(file_path, str) and FILE_PATH_TARGET.search(file_path) is not None


def _bash_writes_log(tool_input: dict[str, object]) -> bool:
    command = tool_input.get("command", "")
    return isinstance(command, str) and bool(command) and bash_command_denies(command)


def main() -> int:
    """Print the decision for the payload on stdin, or nothing to defer."""
    try:
        decision = decide(sys.stdin.read())
    except Exception:  # noqa: BLE001 — a backstop never crashes the permission chain; it defers
        return 0
    if decision is not None:
        print(decision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
