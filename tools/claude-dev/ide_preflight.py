#!/usr/bin/env python3
"""ide_preflight — enumerate a JetBrains IDE's MCP tools and check them against policy.

A JetBrains IDE (2025.2+) serves MCP over SSE on a loopback port. It has no
authentication: the only gate is a `Host: localhost` check, which is DNS-rebinding
protection, not auth. On macOS the loopback bind does NOT confine it to the host —
every container on the Docker/Rancher VM reaches it through the gateway.

So the exposed tool set is the only real boundary, and it drifts: an IDE upgrade can
add a tool and enable it without asking. This script reports the drift.

Exit codes (the interface `claude-dev` branches on):
    0  OK          — exposed set is within the policy set
    1  DRIFT       — exposed set contains tools outside policy
    2  UNREACHABLE — no configured IDE answered
    3  PROTOCOL    — reachable but the MCP handshake failed

--project <path> additionally asks each policy-conforming IDE whether that path
resolves to an open project (the IDE's own containment resolution — a
subdirectory of an open project counts). The verdict never changes the exit
code. It gates the --bridge-ports output instead: only servers with the project
verifiably open emit a bridge line. claude-dev builds its exactly-one rule on
those lines. A drifting server is never probed — it could not earn a bridge
line anyway.

Usage:
    ide_preflight.py --discover
    ide_preflight.py --discover --bridge-ports --project /path/to/project
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import pathlib
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

# The IDE's own Auto-Configure writes its MCP endpoint into ~/.claude.json
# under these names. The port is IDE-assigned and machine-specific — never
# assume 64342.
IDE_SERVER_NAMES = ("idea", "goland")

# No port allowlist: the port is a persisted, user-editable setting, so a range
# check would reject working configurations while stopping no attack. The check
# that works is identity — ~/.claude.json is pod-writable, so the target must
# prove it is a JetBrains MCP server (handshake, then serverInfo).
_JETBRAINS_SERVER_MARKER = "mcp server"


def is_jetbrains_mcp_server(server_info: dict) -> bool:
    """True if serverInfo identifies a JetBrains IDE MCP server.

    Not authentication — a local process could claim the name. It stops a
    rewritten config from pointing the bridge at an unrelated loopback service,
    which is the realistic failure.
    """
    name = server_info.get("name")
    return isinstance(name, str) and _JETBRAINS_SERVER_MARKER in name.lower()


# The harness's documented exposure policy — see
# harness/stacks/*/.claude/skills/*/*-mcp-integration.md, "The exposed tool set".
# A tool earns a slot only if it carries information plain text cannot
# reconstruct, and neither writes files nor executes code. build_project is
# deliberately absent: with Gradle delegation on (the default) it executes
# build.gradle — host code execution from inside a confined pod — and
# ./gradlew build returns the same compiler errors from the same disk.
POLICY_TOOLS = frozenset(
    {
        "get_file_problems",
        "get_project_dependencies",
        "get_project_modules",
        "get_symbol_info",
        "search_symbol",
    }
)

# Tools known to write files or execute code. Named only to make the warning
# specific — the check is a subset test, so an unknown tool is drift too.
KNOWN_DANGEROUS = {
    "apply_patch": "writes files (undocumented; Codex patch format)",
    "execute_tool": "dynamic dispatcher — can reach other tools",
    "execute_terminal_command": "runs shell commands on the host",
    "execute_run_configuration": "runs a run configuration on the host",
    "build_project": "executes the build toolchain (arbitrary code via build config)",
    "create_new_file": "writes files",
    "replace_text_in_file": "writes files",
    "reformat_file": "writes files",
    "rename_refactoring": "writes files",
    "runNotebookCell": "executes notebook code",
    "run_inspection_kts": "compiles and runs an inspection script",
    "validate_inspection_kts": "compiles and runs an inspection script",
}

OK, DRIFT, UNREACHABLE, PROTOCOL = 0, 1, 2, 3

# Project-check probes, in preference order. Both are policy tools whose only
# argument is projectPath, so the probe is exactly the call it predicts.
_PROJECT_PROBE_TOOLS = ("get_project_modules", "get_project_dependencies")
_PROBE_ID = 100  # clear of the handshake (1) and the tools/list pages (2..17)

# The IDE rejects any request whose Host is not localhost (DNS-rebinding
# protection); http.client would send the connect address, so send this.
_HOST_HEADER = "localhost"

# Where a JetBrains MCP server binds, and where its ports are published.
# Neither is a flag: the server binds loopback deliberately, and a port the
# IDE did not write into this file is not one an agent would reach either.
HOST = "127.0.0.1"
CLAUDE_CONFIG = "~/.claude.json"


class MCPError(Exception):
    """The port answered, but not as a working MCP server."""


def _build_opener() -> urllib.request.OpenerDirector:
    """An opener that can only speak plain HTTP, and never follows redirects.

    Built by hand rather than via build_opener(): no file:/ftp: handler, so a
    URL from the pod-writable ~/.claude.json cannot become a local-file read;
    no redirect handler, so a 3xx cannot walk the probe off loopback.
    """
    opener = urllib.request.OpenerDirector()
    opener.add_handler(urllib.request.HTTPHandler())
    opener.add_handler(urllib.request.HTTPErrorProcessor())
    opener.add_handler(urllib.request.HTTPDefaultErrorHandler())
    # UnknownHandler makes an unhandled scheme raise; without it open()
    # returns None for file:/ftp:/https: and callers dereference a crash.
    opener.add_handler(urllib.request.UnknownHandler())
    return opener


_OPENER = _build_opener()


# ── pure logic (unit-tested; no I/O) ──────────────────────────────────────────


def sse_payload(line: str) -> str | None:
    """Return the payload of an SSE `data:` line, or None for any other line."""
    if not line.startswith("data:"):
        return None
    return line[len("data:") :].lstrip()


def classify(
    exposed: set[str], allowed: frozenset[str] | set[str]
) -> tuple[int, list[str]]:
    """Compare an exposed tool set against policy; returns (code, extras).

    Subset test: an unknown tool is drift, which is the point — the docs do
    not list every tool the IDE ships.
    """
    extras = sorted(exposed - set(allowed))
    return (DRIFT if extras else OK), extras


def describe(tool: str) -> str:
    return KNOWN_DANGEROUS.get(tool, "not in the policy set")


def sanitize(text: str) -> str:
    """Strip terminal-spoofing characters from server-supplied strings.

    An ANSI/OSC escape could overwrite the very DRIFT warning this tool
    prints; a bidi override or zero-width character could render a dangerous
    tool name as a benign one. Keep printable text and tab; drop C0/C1
    controls and the invisible format/separator classes (Cf, Zl, Zp).
    """
    return "".join(
        c
        for c in text
        if c == "\t"
        or (
            ord(c) >= 0x20
            and not 0x7F <= ord(c) <= 0x9F
            and unicodedata.category(c) not in ("Cf", "Zl", "Zp")
        )
    )


def loopback_sse_port(url: str) -> int | None:
    """Return the port of a loopback SSE URL, or None if it is not one.

    Only loopback URLs qualify: a server the IDE published elsewhere is not the
    local IDE this tool reasons about, and must not be probed or bridged.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return None
    if parsed.scheme != "http" or parsed.hostname not in (
        "127.0.0.1",
        "localhost",
        "::1",
    ):
        return None
    try:
        port = parsed.port
    except ValueError:
        return None  # malformed port
    # Sanity bound only, not an allowlist: a privileged port is never where an IDE
    # publishes, and refusing it keeps the bridge away from host system services.
    if port is None or not (1024 <= port <= 65535):
        return None
    return port


def discover_servers(config: dict) -> list[tuple[str, int]]:
    """Find (name, port) for each IDE MCP server the config carries.

    Scoped to the known IDE server names so an unrelated local MCP server is
    never probed or bridged. Both config scopes count: Auto-Configure writes
    top-level `mcpServers`, but `claude mcp add` defaults to local scope under
    `projects.<path>.mcpServers` — the exposure is identical.
    """
    scopes = [config.get("mcpServers")]
    projects = config.get("projects")
    if isinstance(projects, dict):
        scopes.extend(
            p.get("mcpServers") for p in projects.values() if isinstance(p, dict)
        )
    found: list[tuple[str, int]] = []
    for servers in scopes:
        if not isinstance(servers, dict):
            continue
        for name in IDE_SERVER_NAMES:
            entry = servers.get(name)
            if not isinstance(entry, dict):
                continue
            url = entry.get("url")
            if not isinstance(url, str):
                continue
            port = loopback_sse_port(url)
            # Dedupe by port alone: two IDEs cannot share one, so `idea` and
            # `goland` entries on the same port are one server under two names.
            # Counting it twice would make the exactly-one bridge rule refuse a
            # single open IDE as "2 qualify".
            if port is not None and all(port != p for _, p in found):
                found.append((name, port))
    return found


def load_claude_config(path: pathlib.Path) -> dict:
    """Read ~/.claude.json. A missing or malformed file means no IDE configured."""
    # The file is pod-writable: ValueError covers malformed JSON and invalid
    # UTF-8, RecursionError deeply nested JSON — every parse runs on this path.
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, RecursionError):
        return {}
    return data if isinstance(data, dict) else {}


# ── MCP over SSE (I/O) ────────────────────────────────────────────────────────


# Hard caps on reads from an unauthenticated, possibly-hostile server. The
# socket timeout is per-recv, so only a wall-clock deadline bounds a dribbling
# stream; without these a repointed ~/.claude.json entry could hang the pod
# launch or exhaust memory.
_MAX_LINES = 10_000
_MAX_LINE_BYTES = 1 << 20  # 1 MiB — an SSE line is small JSON; more is abuse
_MAX_TOOL_PAGES = 16  # an IDE ships dozens of tools, not 16 pages' worth


class Session:
    """Minimal MCP SSE client.

    A long-lived GET streams responses; each request is one short POST. The
    flow stays sequential — post, then read the stream until the matching id
    arrives. Every read is bounded by a wall-clock deadline and byte/line
    caps: the server is never trusted to end the stream.
    """

    def __init__(self, host: str, port: int, timeout: float):
        self.base = f"http://{host}:{port}"
        self.timeout = timeout
        self.deadline = time.monotonic() + timeout
        self.stream = _OPENER.open(
            urllib.request.Request(
                f"{self.base}/sse",
                headers={"Host": _HOST_HEADER, "Accept": "text/event-stream"},
            ),
            timeout=timeout,
        )
        # If reading the endpoint fails, close the stream here — the caller's
        # `finally: sess.close()` never runs when the constructor raises, so an
        # un-closed stream would leak the socket until GC.
        try:
            self.endpoint = self._read_endpoint()
        except BaseException:
            self.close()
            raise

    def _lines(self):
        # Bounded chunk reads rather than readline(): an unbounded readline()
        # buffers a newline-free stream forever, past both caps. read1()
        # returns as soon as any bytes arrive, so the deadline is re-checked
        # at most one socket-timeout apart.
        buf = b""
        count = 0
        while True:
            newline = buf.find(b"\n")
            if newline != -1:
                raw, buf = buf[:newline], buf[newline + 1 :]
                count += 1
                if count > _MAX_LINES:
                    raise MCPError(
                        f"server streamed more than {_MAX_LINES} lines without a usable response"
                    )
                yield raw.decode("utf-8", "replace").rstrip("\r")
                continue
            if len(buf) > _MAX_LINE_BYTES:
                raise MCPError("server sent an oversized SSE line")
            if time.monotonic() > self.deadline:
                raise MCPError(
                    f"no usable response within {self.timeout:.0f}s (server stalled)"
                )
            chunk = self.stream.read1(8192)
            if not chunk:
                if buf:
                    yield buf.decode("utf-8", "replace").rstrip("\r")
                return
            buf += chunk

    def _read_endpoint(self) -> str:
        for line in self._lines():
            payload = sse_payload(line)
            if payload and payload.startswith("/"):
                return payload
        raise MCPError("stream closed before the endpoint event — not an MCP server")

    def post(self, payload: dict) -> None:
        req = urllib.request.Request(
            f"{self.base}{self.endpoint}",
            data=json.dumps(payload).encode(),
            headers={"Host": _HOST_HEADER, "Content-Type": "application/json"},
            method="POST",
        )
        _OPENER.open(req, timeout=self.timeout).close()

    def await_id(self, want: int) -> dict:
        """Read the stream until the response with this id arrives.

        Only a message carrying `result` or `error` counts: a server-initiated
        request (e.g. `ping`) may reuse the same id number in its own id space,
        and matching it would fail the probe on a healthy server.
        """
        for line in self._lines():
            payload = sse_payload(line)
            if not payload or not payload.startswith("{"):
                continue
            try:
                msg = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(msg, dict)
                and msg.get("id") == want
                and ("result" in msg or "error" in msg)
            ):
                return msg
        raise MCPError(f"stream closed before a response to request id={want}")

    def close(self) -> None:
        self.stream.close()


def _result_of(msg: dict, what: str) -> dict:
    """Pull a dict `result` out of a JSON-RPC response, or fail cleanly.

    `result` may be absent, null, or a non-object; every non-dict shape
    becomes an MCPError rather than an AttributeError later.
    """
    if not isinstance(msg, dict):
        raise MCPError(f"{what}: response was not a JSON object")
    result = msg.get("result")
    if not isinstance(result, dict):
        raise MCPError(
            f"{what} failed or returned no result object: {json.dumps(msg)[:200]}"
        )
    return result


# Distinct verdicts because the operator's fix differs: "no_probe_tool" sends
# them to Exposed Tools, the other two say the IDE misbehaved. All three map
# to project_open=null — never bridged.
_UNVERIFIABLE_REASONS = {
    "no_probe_tool": f"no probe tool exposed ({'/'.join(_PROJECT_PROBE_TOOLS)})",
    "probe_failed": "the probe call failed",
    "unusable_response": "the probe response was unusable",
}


def probe_project(sess: Session, exposed: set[str], project: str) -> str:
    """Ask the IDE whether `project` resolves to an open project.

    One call to the cheapest exposed probe tool with projectPath — the verdict
    is the IDE's own containment resolution, so a subdirectory of an open
    project counts as open. Returns "open", "not_open", or an
    _UNVERIFIABLE_REASONS key. Never raises past a completed policy check: a
    stalled probe degrades to "probe_failed" — the probe verdict must never
    change the policy verdict or the exit code.
    """
    tool = next((t for t in _PROJECT_PROBE_TOOLS if t in exposed), None)
    if tool is None:
        return "no_probe_tool"
    try:
        sess.post(
            {
                "jsonrpc": "2.0",
                "id": _PROBE_ID,
                "method": "tools/call",
                "params": {"name": tool, "arguments": {"projectPath": project}},
            }
        )
        result = sess.await_id(_PROBE_ID).get("result")
    except (MCPError, OSError, http.client.HTTPException, RecursionError):
        # RecursionError: a deeply nested probe response degrades like any
        # probe failure — it must never flip the completed policy verdict.
        return "probe_failed"
    # "Open" needs positive evidence, not just an absent isError: a real
    # tools/call success carries a content array. A degenerate {} stays
    # unverifiable — bridge only what is verified.
    if not isinstance(result, dict) or not isinstance(result.get("content"), list):
        return "unusable_response"
    return "not_open" if result.get("isError") else "open"


def enumerate_tools(
    host: str,
    port: int,
    timeout: float,
    project: str | None = None,
    allowed: frozenset[str] | set[str] | None = None,
) -> tuple[dict, set[str], str | None]:
    """Handshake and return (serverInfo, exposed tool names, probe verdict).

    The probe runs on the same session, after the tool listing; None when no
    project was given. With `allowed`, only a policy-conforming set is probed:
    a drifting server could never earn a bridge line, so it gets no extra
    interaction either.
    """
    sess = Session(host, port, timeout)
    try:
        sess.post(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "ide-preflight", "version": "1"},
                },
            }
        )
        init_result = _result_of(sess.await_id(1), "initialize")
        server_info = init_result.get("serverInfo")
        if not isinstance(server_info, dict):
            server_info = {}
        if not is_jetbrains_mcp_server(server_info):
            raise MCPError(
                f"not a JetBrains IDE MCP server (serverInfo.name="
                f"{server_info.get('name')!r}) — refusing to treat it as the oracle"
            )

        sess.post(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        )
        # tools/list is paginated (nextCursor). Follow every page — a
        # dangerous tool could hide on page 2. The page cap stops an endless
        # cursor feed; hitting it fails loud rather than trusting a partial list.
        names: set[str] = set()
        cursor: str | None = None
        for page in range(_MAX_TOOL_PAGES):
            params = {} if cursor is None else {"cursor": cursor}
            sess.post(
                {
                    "jsonrpc": "2.0",
                    "id": 2 + page,
                    "method": "tools/list",
                    "params": params,
                }
            )
            result = _result_of(sess.await_id(2 + page), "tools/list")
            tools = result.get("tools")
            if not isinstance(tools, list):
                raise MCPError("tools/list returned no tools array")
            # Each entry may be anything; only dicts with a string name count.
            names |= {
                t["name"]
                for t in tools
                if isinstance(t, dict) and isinstance(t.get("name"), str)
            }
            cursor = result.get("nextCursor")
            if not isinstance(cursor, str) or not cursor:
                probe = None
                if project is not None and (
                    allowed is None or not (names - set(allowed))
                ):
                    probe = probe_project(sess, names, project)
                return server_info, names, probe
        raise MCPError(
            f"tools/list still paginating after {_MAX_TOOL_PAGES} pages — refusing a partial tool list"
        )
    finally:
        sess.close()


def check_port(
    host: str,
    port: int,
    allowed: frozenset[str] | set[str],
    timeout: float,
    connect_timeout: float = 1.0,
    project: str | None = None,
) -> dict:
    """Probe one port and return a result record. Never raises.

    The cheap TCP pre-probe keeps pod launch fast when no IDE is running: a
    closed port refuses instantly, a filtered or stalling one costs at most
    connect_timeout — never the full session timeout.
    """
    try:
        socket.create_connection((host, port), timeout=connect_timeout).close()
    except OSError:
        return {"status": "unreachable", "port": port, "code": UNREACHABLE}
    try:
        server_info, exposed, probe = enumerate_tools(
            host, port, timeout, project, allowed
        )
    except urllib.error.HTTPError as exc:
        # Something is listening and speaking HTTP — just not an MCP server.
        # Distinct from unreachable: "no IDE there" would send the operator
        # hunting the wrong problem.
        return {
            "status": "protocol_error",
            "port": port,
            "error": f"HTTP {exc.code} — not an MCP server",
            "code": PROTOCOL,
        }
    except (urllib.error.URLError, OSError):
        return {"status": "unreachable", "port": port, "code": UNREACHABLE}
    except (
        MCPError,
        http.client.HTTPException,
        json.JSONDecodeError,
        KeyError,
        AttributeError,
        TypeError,
        RecursionError,
    ) as exc:
        # AttributeError/TypeError back the "never raises" contract;
        # RecursionError so deeply nested JSON cannot take down the rest.
        return {
            "status": "protocol_error",
            "port": port,
            "error": sanitize(str(exc)),
            "code": PROTOCOL,
        }

    code, extras = classify(exposed, allowed)
    record = {
        "status": "drift" if extras else "ok",
        "port": port,
        "server": server_info.get("name", "unknown"),
        "version": server_info.get("version", "unknown"),
        "exposed": sorted(exposed),
        "extras": extras,
        # The set the comparison used — shown so the operator knows what the
        # checkboxes should look like, not just what to remove.
        "allowed": sorted(allowed),
        "code": code,
    }
    if probe is not None:
        record["project"] = project
        # true/false/null in JSON; null = unverifiable, which bridging treats as
        # not qualified — bridge only what is verified.
        record["project_open"] = {"open": True, "not_open": False}.get(probe)
        if record["project_open"] is None:
            record["project_unverifiable"] = _UNVERIFIABLE_REASONS.get(probe, probe)
    return record


# ── CLI ───────────────────────────────────────────────────────────────────────


def _bridgeable(result: dict, project_required: bool) -> bool:
    """Whether a server has earned a bridge line.

    Policy-conforming always; with --project, additionally verified project-open.
    Unverifiable (null) does not qualify: bridge only what is verified.
    """
    if result["code"] != OK or result["status"] != "ok":
        return False
    return not project_required or result.get("project_open") is True


def _project_note(result: dict) -> str:
    """One clause describing the project verdict; empty when no check ran."""
    if "project_open" not in result:
        return ""
    path = sanitize(result.get("project") or "")
    if result["project_open"] is True:
        return f"project {path} is open"
    if result["project_open"] is False:
        return f"project {path} is NOT open"
    return f"project {path} unverifiable — {result.get('project_unverifiable', 'unknown cause')}"


def _bridge_line(result: dict) -> str:
    """One machine-line per bridgeable server: `port<TAB>server label`.

    claude-dev splits on the tab, validates the port, and uses the label only in
    its own user-facing messages — never in a shell command. The label is
    server-supplied, so it is sanitized here like everything else it prints.
    """
    label = sanitize(
        f"{result.get('server', 'unknown')} {result.get('version', '')}"
    ).strip()
    return f"{result['port']}\t{label}"


def _report(
    result: dict, host: str, label: str = "", stream=None, compact: bool = False
) -> None:
    """Print one server's verdict. `compact` collapses a healthy server to one
    line — the every-launch case — while drift always gets the full block."""
    out = stream or sys.stdout
    port = result["port"]
    tag = f"{label} " if label else ""
    if result["status"] == "unreachable":
        print(
            f"ide-preflight: {tag}no IDE on {host}:{port} — oracle unavailable",
            file=out,
        )
        return
    if result["status"] == "protocol_error":
        print(
            f"ide-preflight: {tag}{host}:{port} answered but is not a usable oracle — {result['error']}",
            file=out,
        )
        return

    # Server-supplied names are sanitized for display only — the raw names
    # already drove classify(), so a name that merely looks like a policy tool
    # (control chars added) was flagged as drift there.
    server = sanitize(result["server"])
    version = sanitize(result["version"])
    exposed = [sanitize(t) for t in result["exposed"]]
    note = _project_note(result)
    if compact and not result["extras"]:
        print(
            f"ide-preflight: {tag}{server} {version} on {host}:{port} — "
            f"OK: exposed set within policy ({len(exposed)} tools)"
            + (f"; {note}" if note else ""),
            file=out,
        )
        return
    print(f"ide-preflight: {tag}{server} {version} on {host}:{port}", file=out)
    print(f"  exposed: {len(exposed)} tool(s) — {', '.join(exposed)}", file=out)
    if note:
        print(f"  {note}", file=out)
    if not result["extras"]:
        print("  verdict: OK — exposed set is within policy", file=out)
        return

    print(
        f"  verdict: DRIFT — {len(result['extras'])} tool(s) outside policy:", file=out
    )
    for tool in result["extras"]:
        # describe() keys on the raw name; the label prints the sanitized one.
        print(f"    - {sanitize(tool)}: {describe(tool)}", file=out)
    print(file=out)
    print(
        "  These are reachable from any container on the Docker VM, with or without",
        file=out,
    )
    print(
        "  a bridge: the IDE's MCP server has no authentication and its loopback bind",
        file=out,
    )
    print(
        "  does not confine it. Remove them in the IDE to actually restrict access:",
        file=out,
    )
    print("    Settings -> Tools -> MCP Server -> Exposed Tools", file=out)
    print("  Keep exactly these enabled (the read-only policy set):", file=out)
    for tool in result.get("allowed", []):
        print(f"    [x] {tool}", file=out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # Discovery is the only mode — the port is IDE-assigned and published in
    # ~/.claude.json, never guessed. The flag stays required so a bare
    # invocation is a loud usage error, never a silent probe.
    ap.add_argument(
        "--discover",
        action="store_true",
        required=True,
        help=f"read the IDE-assigned ports from {CLAUDE_CONFIG} (the only mode)",
    )
    ap.add_argument(
        "--timeout", type=float, default=10.0, help="handshake deadline once connected"
    )
    ap.add_argument(
        "--connect-timeout",
        type=float,
        default=1.0,
        help="TCP connect bound — keeps pod launch fast when no IDE is running (default 1s)",
    )
    ap.add_argument(
        "--bridge-ports",
        action="store_true",
        help="print one 'port<TAB>server label' line per policy-conforming server on "
        "stdout, reports on stderr (the interface claude-dev consumes)",
    )
    ap.add_argument(
        "--project",
        default=None,
        help="verify this path resolves to an open project in each conforming IDE; "
        "with --bridge-ports, only verified-open servers emit a bridge line",
    )
    args = ap.parse_args(argv)

    # Deliberately not a flag: a runtime override would let a launch wrapper
    # widen the set and still print "OK". Changing the policy means changing
    # this file, where the harness-docs coupling test sees it.
    allowed = POLICY_TOOLS

    # --bridge-ports keeps stdout machine-only so bash can read ports from it;
    # the human report moves to stderr in every mode.
    report_to = sys.stderr if args.bridge_ports else sys.stdout

    config_path = pathlib.Path(os.path.expanduser(CLAUDE_CONFIG))
    servers = discover_servers(load_claude_config(config_path))
    if not servers:
        if not args.bridge_ports:
            print(
                f"ide-preflight: no IDE MCP server configured in {config_path} — nothing to check"
            )
        return OK  # nothing configured is not a failure; the oracle is optional

    results = []
    for name, port in servers:
        result = check_port(
            HOST, port, allowed, args.timeout, args.connect_timeout, args.project
        )
        result["name"] = name
        results.append(result)

    # DRIFT needs action, so it outranks a merely absent or unreachable IDE;
    # below it the order is a deterministic max — PROTOCOL over UNREACHABLE.
    codes = [r["code"] for r in results]
    worst = DRIFT if DRIFT in codes else max(codes)

    for result in results:
        # An unreachable IDE is the normal case (it just is not running);
        # saying so on every launch would be noise.
        if args.bridge_ports and result["status"] == "unreachable":
            continue
        _report(
            result,
            HOST,
            label=f"[{result['name']}]",
            stream=report_to,
            compact=args.bridge_ports,
        )

    if args.bridge_ports:
        # A drifting IDE stays reachable from the pod regardless — the warning
        # above says so — but it does not get the convenience of a bridge.
        for result in results:
            if _bridgeable(result, args.project is not None):
                print(_bridge_line(result))
    return worst


if __name__ == "__main__":
    sys.exit(main())
