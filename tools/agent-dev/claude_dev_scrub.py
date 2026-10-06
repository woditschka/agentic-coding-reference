#!/usr/bin/env python3
"""Emit the container-private ~/.claude.json replica, scrubbed to one launch project."""

import json
import sys
from pathlib import Path


def overlaps(a: str, b: str) -> bool:
    """Tell whether two absolute paths coincide or nest, in either direction."""
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def scrub_replica(data: dict[str, object], cwd: str) -> dict[str, object]:
    """Keep only the projects entries that overlap the launch cwd."""
    # Ancestors carry the trust verdict Claude Code looks up; subtrees are
    # worktrees and subdirectory sessions. Sibling projects stay on the host.
    projects = data.get("projects")
    if not isinstance(projects, dict):
        return data
    kept = {key: value for key, value in projects.items() if overlaps(key, cwd)}
    return {**data, "projects": kept}


def replica_text(source: Path, cwd: str) -> str:
    """Render the replica for one launch, degrading every input defect to {}."""
    # The failure direction is state loss, never exposure: a host file Claude
    # Code could not have read replicates as empty. Compact separators keep
    # a projects-free file byte-identical to the host copy.
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return "{}"
    if not isinstance(data, dict):
        return "{}"
    return json.dumps(scrub_replica(data, cwd), separators=(",", ":"))


def main(argv: list[str] | None = None) -> int:
    """Write the replica for the given host file and cwd to stdout."""
    args = sys.argv[1:] if argv is None else argv
    try:
        host_file, cwd = args
    except ValueError:
        print("usage: claude_dev_scrub.py <host-claude-json> <cwd>", file=sys.stderr)
        return 2
    sys.stdout.write(replica_text(Path(host_file), cwd))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
