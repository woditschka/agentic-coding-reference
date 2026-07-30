#!/usr/bin/env python3
"""claude_dev_scrub — emit the container-private ~/.claude.json replica.

The launcher never mounts the host ~/.claude.json into the dev container.
It runs this script on the host at every launch and mounts the output
instead: the host file scrubbed to the launch project. Only ``projects``
entries overlapping the launch cwd are kept — its ancestors (they carry the
trust verdict Claude Code looks up) and its subtrees (worktrees,
subdirectory sessions). Sibling projects' paths, per-project MCP servers,
and trust states are not this container's business and stay on the host.

A host file that is absent or does not parse as a JSON object replicates
as ``{}``: Claude Code could not have read it either, and the boundary's
failure direction is state loss, never exposure.

Usage:
    claude_dev_scrub.py <host-claude-json> <cwd>

The replica JSON lands on stdout; the launcher redirects it into the
container-private replica file. Exit is always 0 on a writable stdout —
every input defect degrades to ``{}`` by design.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def overlaps(a: str, b: str) -> bool:
    """True when two absolute paths coincide or nest, in either direction."""
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def scrub_replica(data: dict[str, object], cwd: str) -> dict[str, object]:
    """The host config minus other projects' metadata."""
    projects = data.get("projects")
    if not isinstance(projects, dict):
        return data
    kept = {k: v for k, v in projects.items() if overlaps(k, cwd)}
    return {**data, "projects": kept}


def replica_text(src: Path, cwd: str) -> str:
    """The replica's exact content for one launch. Compact separators keep
    a projects-free file byte-identical to the host copy."""
    data: object = None
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        data = None
    if not isinstance(data, dict):
        return "{}"
    return json.dumps(scrub_replica(data, cwd), separators=(",", ":"))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: claude_dev_scrub.py <host-claude-json> <cwd>", file=sys.stderr)
        return 2
    sys.stdout.write(replica_text(Path(args[0]), args[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
