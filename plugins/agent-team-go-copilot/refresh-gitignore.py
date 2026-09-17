#!/usr/bin/env python3
"""Ensure the harness runtime ignore lines are present in a consumer's .gitignore.

    refresh-gitignore.py <target-gitignore> <block-source> <channel>

The marker-free analogue of the chapter refresh: ownership is exact match
against the shipped block, so no sentinel and no recorded version enter the
project file. Ensure-present only: a missing line is appended, and a
project's own ignores and re-includes are never touched. Stdlib only.
"""

import sys
from pathlib import Path

USAGE = "usage: refresh-gitignore.py <target-gitignore> <block-source> <channel>"
ARGS = 4
USAGE_EXIT = 2
FAILURE_EXIT = 1
LEDGER = ".scratch/"

# Added once, the first time a line is appended to a file with no runtime
# marker yet, so a minimal .gitignore never gains a bare, contextless path.
HEADER = "\n# harness runtime (harness-owned; kept current on upgrade)\n"
MARKER = "harness runtime"


def desired_lines(template_text: str, channel: str) -> list[str]:
    """Return the template lines this channel must carry, comments and blanks skipped."""
    # Under copy the runtime is committed, so only the ledger is ensured.
    lines: list[str] = []
    for line in template_text.splitlines():
        if not line or line.startswith("#"):
            continue
        if line != LEDGER and channel == "copy":
            continue
        lines.append(line)
    return lines


def refreshed_text(
    existing_text: str, template_text: str, channel: str
) -> tuple[str, int]:
    """Return the target's new content and the number of lines appended."""
    existing = set(existing_text.splitlines())
    missing = [
        line for line in desired_lines(template_text, channel) if line not in existing
    ]
    if not missing:
        return existing_text, 0
    out = existing_text
    # A missing path must never merge onto an unterminated final line.
    if out and not out.endswith("\n"):
        out += "\n"
    if MARKER not in out.lower():
        out += HEADER
    out += "\n".join(missing) + "\n"
    return out, len(missing)


def main(argv: list[str]) -> int:
    """Refresh the target from the command line and return the exit code."""
    if len(argv) != ARGS:
        print(USAGE, file=sys.stderr)
        return USAGE_EXIT
    target, source, channel = Path(argv[1]), Path(argv[2]), argv[3]
    if not source.is_file():
        print(f"refresh-gitignore: missing block source {source}", file=sys.stderr)
        return FAILURE_EXIT
    existing_text = target.read_text(encoding="utf-8") if target.is_file() else ""
    out, added = refreshed_text(
        existing_text, source.read_text(encoding="utf-8"), channel
    )
    if added or not target.is_file():
        target.write_text(out, encoding="utf-8")
    print(f"gitignore: {added} path(s) added")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
