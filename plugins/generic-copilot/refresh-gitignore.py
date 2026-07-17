#!/usr/bin/env python3
"""Ensure the harness runtime gitignore lines are present in a consumer's .gitignore.

The deterministic, marker-free analogue of refresh-chapters for gitignore
lines: it makes the harness-owned lines current without writing any BEGIN/END
sentinel into the project file.

    refresh-gitignore.py <target-gitignore> <block-source> <channel>

block-source is harness/init/core/gitignore-runtime.txt — the canonical set of
harness runtime paths plus the .scratch/ ledger, one per line (comments and
blanks ignored). Harness ownership is identified by exact match against this
template, which is what lets the refresh stay marker-free and baseline-free:
no sentinels, no recorded version.

The operation is ENSURE-PRESENT, and only that:
  - a template line the target lacks is appended (a new engine file that must
    be ignored now reaches an existing project);
  - a project's own ignores and its "!<extension>/" re-includes are never
    touched, removed, or reordered.
It never removes a line: a path the template dropped lingers as a harmless
over-broad ignore, left for the advisory reconciliation or a human to prune.

Channel-aware. Under "copy" the runtime is committed, so only the .scratch/
ledger is ensured. Under manifest/marketplace the runtime is out-of-band, so
every runtime path is ensured too. The channel is read, never changed.

Stdlib only. Tested by test_refresh_gitignore.py.
"""

import sys
from pathlib import Path

USAGE = "usage: refresh-gitignore.py <target-gitignore> <block-source> <channel>"

# Added once, the first time any line is appended to a file that carries no
# harness-runtime marker yet — so a fresh or minimal .gitignore does not gain
# a bare, contextless path.
HEADER = "\n# harness runtime (harness-owned; kept current on upgrade)\n"


def desired_lines(template_text, channel):
    """The template lines this channel must carry (comments and blanks skipped)."""
    lines = []
    for line in template_text.splitlines():
        if not line or line.startswith("#"):
            continue
        if line != ".scratch/" and channel == "copy":
            continue
        lines.append(line)
    return lines


def refreshed_text(existing_text, template_text, channel):
    """The target's new content and the number of lines appended."""
    existing = set(existing_text.splitlines())
    missing = [l for l in desired_lines(template_text, channel) if l not in existing]
    if not missing:
        return existing_text, 0

    out = existing_text
    # Guarantee the target ends in a newline before appending, so a missing
    # path can never merge onto an unterminated final line (silent corruption
    # of a project ignore).
    if out and not out.endswith("\n"):
        out += "\n"
    if "harness runtime" not in out.lower():
        out += HEADER
    out += "\n".join(missing) + "\n"
    return out, len(missing)


def main(argv):
    if len(argv) != 4:
        print(USAGE, file=sys.stderr)
        return 2
    target, source, channel = Path(argv[1]), Path(argv[2]), argv[3]

    if not source.is_file():
        print(f"refresh-gitignore: missing block source {source}", file=sys.stderr)
        return 1

    existing_text = target.read_text(encoding="utf-8") if target.is_file() else ""
    out, added = refreshed_text(
        existing_text, source.read_text(encoding="utf-8"), channel
    )
    if added or not target.is_file():
        target.write_text(out, encoding="utf-8")

    print(f"gitignore: {added} path(s) added")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
