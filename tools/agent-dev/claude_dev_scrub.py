#!/usr/bin/env python3
"""Emit the container-private ~/.claude.json replica, scrubbed to one launch project."""

import json
import re
import sys
from pathlib import Path


def overlaps(a: str, b: str) -> bool:
    """Tell whether two absolute paths coincide or nest, in either direction."""
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


# What a session on an open-weight peer must not receive from ~/.claude.json:
# the stored API key, and every MCP server entry that can hold a token in its
# headers, env, arguments or URL. A bare loopback endpoint holds none, and it
# is the entry an IDE writes for its own MCP server, so it stays.
STORED_KEY = "primaryApiKey"
MCP_SERVERS = "mcpServers"
BARE_ENDPOINT_KEYS = frozenset({"type", "url"})
# Plain http to a loopback host, an optional port and a path: no user, no
# query string and no fragment, since each of those can carry a token.
BARE_LOOPBACK_URL = re.compile(
    r"http://(127\.0\.0\.1|localhost)(:[0-9]{1,5})?(/[A-Za-z0-9._~/-]*)?"
)


def is_bare_loopback_endpoint(server: object) -> bool:
    """Tell whether an MCP server entry is a type and a loopback URL, nothing else."""
    if not isinstance(server, dict) or not set(server) <= BARE_ENDPOINT_KEYS:
        return False
    url = server.get("url")
    return isinstance(url, str) and BARE_LOOPBACK_URL.fullmatch(url) is not None


def without_credentials(table: dict[str, object]) -> dict[str, object]:
    """Drop the stored key and every credential-capable MCP entry of one table."""
    kept = {key: value for key, value in table.items() if key != STORED_KEY}
    servers = kept.pop(MCP_SERVERS, None)
    if isinstance(servers, dict):
        bare = {
            name: server
            for name, server in servers.items()
            if is_bare_loopback_endpoint(server)
        }
        if bare:
            kept[MCP_SERVERS] = bare
    return kept


def scrub_replica(
    data: dict[str, object], cwd: str, *, open_weight: bool = False
) -> dict[str, object]:
    """Keep only the projects entries that overlap the launch cwd."""
    # Ancestors carry the trust verdict Claude Code looks up; subtrees are
    # worktrees and subdirectory sessions. Sibling projects stay on the host.
    # A session on an open-weight peer holds no credential, so its replica
    # also loses the credential-bearing entries, top-level and per project.
    scrubbed = without_credentials(data) if open_weight else data
    projects = scrubbed.get("projects")
    if not isinstance(projects, dict):
        return scrubbed
    kept = {key: value for key, value in projects.items() if overlaps(key, cwd)}
    if open_weight:
        kept = {
            key: without_credentials(value) if isinstance(value, dict) else value
            for key, value in kept.items()
        }
    return {**scrubbed, "projects": kept}


def replica_text(source: Path, cwd: str, *, open_weight: bool = False) -> str:
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
    return json.dumps(
        scrub_replica(data, cwd, open_weight=open_weight), separators=(",", ":")
    )


def main(argv: list[str] | None = None) -> int:
    """Write the replica for the given host file and cwd to stdout."""
    args = list(sys.argv[1:] if argv is None else argv)
    open_weight = args[:1] == ["--ow"]
    if open_weight:
        del args[0]
    try:
        host_file, cwd = args
    except ValueError:
        print(
            "usage: claude_dev_scrub.py [--ow] <host-claude-json> <cwd>",
            file=sys.stderr,
        )
        return 2
    sys.stdout.write(replica_text(Path(host_file), cwd, open_weight=open_weight))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
