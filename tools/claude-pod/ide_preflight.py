#!/usr/bin/env python3
"""ide_preflight — enumerate a JetBrains IDE's MCP tools and check them against policy.

A JetBrains IDE (2025.2+) serves MCP over SSE on a loopback port. It has no
authentication: the only gate is a `Host: localhost` check, which is DNS-rebinding
protection, not auth. On macOS the loopback bind does NOT confine it to the host —
every container on the Docker/Rancher VM reaches it through the gateway.

So the exposed tool set is the only real boundary, and it drifts: an IDE upgrade can
add a tool and enable it without asking. This script reports the drift.

Exit codes (the interface `claude-pod` branches on):
    0  OK          — exposed set is within the policy set
    1  DRIFT       — exposed set contains tools outside policy
    2  UNREACHABLE — no IDE answered on that port
    3  PROTOCOL    — reachable but the MCP handshake failed

Usage:
    ide_preflight.py --discover
    ide_preflight.py --port 64342
    ide_preflight.py --port 64342 --host 192.168.5.2 --json
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

# The IDE's own Auto-Configure writes its MCP endpoint into ~/.claude.json under
# these names. The port is IDE-assigned and machine-specific — never assume 64342.
# Reading it back is what makes this "probed, not declared": nothing is committed.
IDE_SERVER_NAMES = ("idea", "goland")

# Why there is no port allowlist. IntelliJ derives a default from
# BASE_MCP_PORT=64342 plus a per-IDE offset of PORT_STEP=20 (McpServerSettings.kt),
# but the result is only a *default*: mcpServerPort is a persisted, user-editable
# setting, and observed reality already diverges — a GoLand 2026.1.4 answering on
# 64343 where that scheme predicts 64422. Any port is legitimate, so a range check
# would reject working configurations while stopping no attack (an attacker picks a
# port inside the range).
#
# The check that does work is identity. ~/.claude.json is writable by the pod, so a
# compromised session could repoint an entry at any host loopback service and use
# the relay as a tunnel to it. Requiring the target to prove it is a JetBrains MCP
# server — handshake, then serverInfo — validates the thing rather than the number.
_JETBRAINS_SERVER_MARKER = "mcp server"


def is_jetbrains_mcp_server(server_info: dict) -> bool:
    """True if serverInfo identifies a JetBrains IDE MCP server.

    Not an authentication check — a local process could claim the name. It stops
    the relay from being pointed at an unrelated loopback service by a rewritten
    config, which is the realistic failure, and it costs nothing.
    """
    name = server_info.get("name")
    return isinstance(name, str) and _JETBRAINS_SERVER_MARKER in name.lower()

# The harness's documented exposure policy — see
# harness/stacks/*/.claude/skills/*/*-mcp-integration.md, "The exposed tool set".
# A tool earns a slot only if it carries information plain text cannot reconstruct,
# and neither writes files nor executes code.
#
# build_project is deliberately absent. It refreshes nothing (the IDE's compile
# action does not refresh source VFS/PSI), so it never was the coherence mechanism
# the docs claimed; get_file_problems is. And with Gradle delegation on — the
# default — it executes build.gradle, which turns one injected line into host code
# execution from inside a confined pod. ./gradlew build returns the same compiler
# errors from the same disk and is the canonical gate regardless.
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
# specific — the check is a strict subset test, so an unknown tool is drift too.
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

# The IDE rejects any request whose Host is not localhost — DNS-rebinding
# protection. Sending it explicitly is what lets us reach the IDE by gateway IP.
_HOST_HEADER = "localhost"


class MCPError(Exception):
    """The port answered, but not as a working MCP server."""


def _build_opener() -> urllib.request.OpenerDirector:
    """An opener that can only speak plain HTTP, and never follows redirects.

    Built by hand rather than via build_opener(), which would install FileHandler,
    FTPHandler and HTTPSHandler as well. Two properties we want structurally rather
    than by convention:

    * No file:/ftp: handler — a URL from ~/.claude.json (which the pod can write)
      cannot be turned into a local-file read. loopback_sse_port() already rejects
      those schemes; this makes it impossible rather than merely checked.
    * No redirect handler — a 3xx cannot walk us off loopback to an address the
      scheme check already approved.
    """
    opener = urllib.request.OpenerDirector()
    opener.add_handler(urllib.request.HTTPHandler())
    opener.add_handler(urllib.request.HTTPErrorProcessor())
    opener.add_handler(urllib.request.HTTPDefaultErrorHandler())
    # UnknownHandler is what makes an unhandled scheme *raise*. Without it,
    # OpenerDirector.open() returns None for file:/ftp:/https:, which callers then
    # dereference — a crash path rather than a clean, catchable failure.
    opener.add_handler(urllib.request.UnknownHandler())
    return opener


_OPENER = _build_opener()


# ── pure logic (unit-tested; no I/O) ──────────────────────────────────────────


def sse_payload(line: str) -> str | None:
    """Return the payload of an SSE `data:` line, or None for any other line."""
    if not line.startswith("data:"):
        return None
    return line[len("data:") :].lstrip()


def classify(exposed: set[str], allowed: frozenset[str] | set[str]) -> tuple[int, list[str]]:
    """Compare an exposed tool set against policy.

    Returns (exit_code, sorted_extras). Strict subset test: a tool nobody has heard
    of is drift, which is the point — the docs do not list every tool the IDE ships.
    """
    extras = sorted(exposed - set(allowed))
    return (DRIFT if extras else OK), extras


def describe(tool: str) -> str:
    return KNOWN_DANGEROUS.get(tool, "not in the policy set")


def sanitize(text: str) -> str:
    """Strip terminal-spoofing characters from server-supplied strings.

    serverInfo.name, version, and tool names come from an unauthenticated server
    and are printed to a real terminal. Left raw, an ANSI/OSC escape in a tool
    name could rewrite the clipboard or move the cursor to overwrite the very
    DRIFT warning this tool prints; a bidi override or zero-width character could
    make a dangerous tool name render as a benign one. Keep printable text and
    tab; drop C0/C1 controls and the invisible format/separator classes (Cf, Zl,
    Zp — bidi controls, zero-width chars, BOM, line/paragraph separators).
    """
    return "".join(
        c
        for c in text
        if c == "\t"
        or (ord(c) >= 0x20 and not 0x7F <= ord(c) <= 0x9F and unicodedata.category(c) not in ("Cf", "Zl", "Zp"))
    )


def loopback_sse_port(url: str) -> int | None:
    """Return the port of a loopback SSE URL, or None if it is not one.

    Only loopback URLs qualify: a server the IDE published elsewhere is not the
    local IDE this tool reasons about, and must not be probed or relayed.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return None
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        return None
    try:
        port = parsed.port
    except ValueError:
        return None  # malformed port
    # Sanity bound only, not an allowlist: a privileged port is never where an IDE
    # publishes, and refusing it keeps the relay away from host system services.
    if port is None or not (1024 <= port <= 65535):
        return None
    return port


def discover_servers(config: dict) -> list[tuple[str, int]]:
    """Find (name, port) for each IDE MCP server the config carries.

    Reads whatever port the IDE actually assigned rather than assuming a default.
    Scoped to the known IDE server names so an unrelated local MCP server in the
    same config is never probed or relayed.

    Both config scopes count: the IDE's Auto-Configure writes top-level
    `mcpServers`, but `claude mcp add` defaults to local scope, which lands under
    `projects.<path>.mcpServers` — the exposure is identical, so skipping that
    scope would silently skip the check for exactly those users.
    """
    scopes = [config.get("mcpServers")]
    projects = config.get("projects")
    if isinstance(projects, dict):
        scopes.extend(p.get("mcpServers") for p in projects.values() if isinstance(p, dict))
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
            if port is not None and (name, port) not in found:
                found.append((name, port))
    return found


def load_claude_config(path: pathlib.Path) -> dict:
    """Read ~/.claude.json. A missing or malformed file means no IDE configured."""
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


# ── MCP over SSE (I/O) ────────────────────────────────────────────────────────


# Hard caps on what we will read from an unauthenticated, possibly-hostile server.
# The socket timeout is per-recv, so a service that dribbles one line every few
# seconds keeps each recv fast while the stream never ends — a wall-clock deadline
# is what actually bounds it. Without these a repointed ~/.claude.json entry could
# hang the pod launch (the caller reads this via `read < <(...)`) or exhaust memory.
_MAX_LINES = 10_000
_MAX_LINE_BYTES = 1 << 20  # 1 MiB — an SSE line is small JSON; more is abuse
_MAX_TOOL_PAGES = 16  # an IDE ships dozens of tools, not 16 pages' worth


class Session:
    """Minimal MCP SSE client.

    The transport is a long-lived GET that streams responses, plus one short POST
    per request. Both directions are plain HTTP, so urllib handles the chunked
    framing; and because every POST is its own connection, the flow stays
    sequential — post, then read the stream until the matching id arrives.

    Every read is bounded by a wall-clock deadline and byte/line caps: the server
    is unauthenticated and may be hostile (a config entry can be repointed at any
    loopback service), so it is never trusted to end the stream.
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
        # Assemble lines from bounded chunk reads rather than readline(): an
        # unbounded readline() buffers a newline-free stream forever, and both the
        # byte cap and the deadline would only run after it returned. read1()
        # returns as soon as any bytes arrive, so the deadline is re-checked at
        # most one socket-timeout apart and the buffer never exceeds the line cap.
        buf = b""
        count = 0
        while True:
            newline = buf.find(b"\n")
            if newline != -1:
                raw, buf = buf[:newline], buf[newline + 1 :]
                count += 1
                if count > _MAX_LINES:
                    raise MCPError(f"server streamed more than {_MAX_LINES} lines without a usable response")
                yield raw.decode("utf-8", "replace").rstrip("\r")
                continue
            if len(buf) > _MAX_LINE_BYTES:
                raise MCPError("server sent an oversized SSE line")
            if time.monotonic() > self.deadline:
                raise MCPError(f"no usable response within {self.timeout:.0f}s (server stalled)")
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

        Only a response counts — a message carrying `result` or `error`. A
        server-initiated *request* (e.g. `ping`) may reuse the same id number in
        the server's own id space; matching it would hand a method call to
        `_result_of` and fail the probe on a healthy server.
        """
        for line in self._lines():
            payload = sse_payload(line)
            if not payload or not payload.startswith("{"):
                continue
            try:
                msg = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if isinstance(msg, dict) and msg.get("id") == want and ("result" in msg or "error" in msg):
                return msg
        raise MCPError(f"stream closed before a response to request id={want}")

    def close(self) -> None:
        self.stream.close()


def _result_of(msg: dict, what: str) -> dict:
    """Pull a dict `result` out of a JSON-RPC response, or fail cleanly.

    The server is untrusted, so `result` may be absent, null, or a non-object.
    Every non-dict shape becomes an MCPError rather than an AttributeError later.
    """
    if not isinstance(msg, dict):
        raise MCPError(f"{what}: response was not a JSON object")
    result = msg.get("result")
    if not isinstance(result, dict):
        raise MCPError(f"{what} failed or returned no result object: {json.dumps(msg)[:200]}")
    return result


def enumerate_tools(host: str, port: int, timeout: float) -> tuple[dict, set[str]]:
    """Handshake and return (serverInfo, exposed tool names)."""
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

        sess.post({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        # tools/list is paginated in the MCP spec (nextCursor). Follow every page:
        # classifying page 1 alone would report OK while a dangerous tool hides on
        # page 2 — the exact silent false-OK this script exists to prevent. The
        # page cap keeps a hostile server from feeding cursors forever; hitting it
        # fails loud rather than trusting a partial list.
        names: set[str] = set()
        cursor: str | None = None
        for page in range(_MAX_TOOL_PAGES):
            params = {} if cursor is None else {"cursor": cursor}
            sess.post({"jsonrpc": "2.0", "id": 2 + page, "method": "tools/list", "params": params})
            result = _result_of(sess.await_id(2 + page), "tools/list")
            tools = result.get("tools")
            if not isinstance(tools, list):
                raise MCPError("tools/list returned no tools array")
            # Each entry may be anything; only dicts with a string name count.
            names |= {t["name"] for t in tools if isinstance(t, dict) and isinstance(t.get("name"), str)}
            cursor = result.get("nextCursor")
            if not isinstance(cursor, str) or not cursor:
                return server_info, names
        raise MCPError(f"tools/list still paginating after {_MAX_TOOL_PAGES} pages — refusing a partial tool list")
    finally:
        sess.close()


def check_port(host: str, port: int, allowed, timeout: float, connect_timeout: float = 1.0) -> dict:
    """Probe one port and return a result record. Never raises.

    The cheap TCP pre-probe is what keeps pod launch fast when no IDE is
    running: a closed loopback port refuses instantly, and a filtered or
    stalling one costs at most connect_timeout — never the full session timeout.
    """
    try:
        socket.create_connection((host, port), timeout=connect_timeout).close()
    except OSError:
        return {"status": "unreachable", "port": port, "code": UNREACHABLE}
    try:
        server_info, exposed = enumerate_tools(host, port, timeout)
    except urllib.error.HTTPError as exc:
        # Something is listening and speaking HTTP — it is just not an MCP server.
        # Distinct from unreachable: "no IDE there" would send you hunting the
        # wrong problem when a config entry points at an unrelated local service.
        return {
            "status": "protocol_error",
            "port": port,
            "error": f"HTTP {exc.code} — not an MCP server",
            "code": PROTOCOL,
        }
    except (urllib.error.URLError, OSError):
        return {"status": "unreachable", "port": port, "code": UNREACHABLE}
    except (MCPError, http.client.HTTPException, json.JSONDecodeError, KeyError, AttributeError, TypeError) as exc:
        # AttributeError/TypeError belt-and-suspenders: enumerate_tools guards
        # every dereference, but check_port's contract is "never raises", so any
        # malformed-response shape must still become a clean PROTOCOL result.
        return {"status": "protocol_error", "port": port, "error": sanitize(str(exc)), "code": PROTOCOL}

    code, extras = classify(exposed, allowed)
    return {
        "status": "drift" if extras else "ok",
        "port": port,
        "server": server_info.get("name", "unknown"),
        "version": server_info.get("version", "unknown"),
        "exposed": sorted(exposed),
        "extras": extras,
        # The set the comparison actually used — the report shows it so the
        # operator knows what the checkboxes should look like, not just what
        # to remove.
        "allowed": sorted(allowed),
        "code": code,
    }


# ── CLI ───────────────────────────────────────────────────────────────────────


def _relay_line(result: dict) -> str:
    """One machine-line per relayable server: `port<TAB>server label`.

    claude-pod splits on the tab, validates the port, and uses the label only in
    its own user-facing messages — never in a shell command. The label is
    server-supplied, so it is sanitized here like everything else it prints.
    """
    label = sanitize(f"{result.get('server', 'unknown')} {result.get('version', '')}").strip()
    return f"{result['port']}\t{label}"


def _report(result: dict, host: str, label: str = "", stream=None, compact: bool = False) -> None:
    """Print one server's verdict. `compact` collapses a healthy server to one
    line — the every-launch case — while drift always gets the full block."""
    out = stream or sys.stdout
    port = result["port"]
    tag = f"{label} " if label else ""
    if result["status"] == "unreachable":
        print(f"ide-preflight: {tag}no IDE on {host}:{port} — oracle unavailable", file=out)
        return
    if result["status"] == "protocol_error":
        print(f"ide-preflight: {tag}{host}:{port} answered but is not a usable oracle — {result['error']}", file=out)
        return

    # server/version/tool names are server-supplied — sanitize before the terminal.
    # Raw names still drove the policy comparison in classify(), so a name that
    # only looks like a policy tool (control chars added) was already flagged as
    # drift; here we only make it safe to display.
    server = sanitize(result["server"])
    version = sanitize(result["version"])
    exposed = [sanitize(t) for t in result["exposed"]]
    if compact and not result["extras"]:
        print(
            f"ide-preflight: {tag}{server} {version} on {host}:{port} — "
            f"OK: exposed set within policy ({len(exposed)} tools)",
            file=out,
        )
        return
    print(f"ide-preflight: {tag}{server} {version} on {host}:{port}", file=out)
    print(f"  exposed: {len(exposed)} tool(s) — {', '.join(exposed)}", file=out)
    if not result["extras"]:
        print("  verdict: OK — exposed set is within policy", file=out)
        return

    print(f"  verdict: DRIFT — {len(result['extras'])} tool(s) outside policy:", file=out)
    for tool in result["extras"]:
        # describe() keys on the raw name; the label prints the sanitized one.
        print(f"    - {sanitize(tool)}: {describe(tool)}", file=out)
    print(file=out)
    print("  These are reachable from any container on the Docker VM, with or without", file=out)
    print("  a relay: the IDE's MCP server has no authentication and its loopback bind", file=out)
    print("  does not confine it. Remove them in the IDE to actually restrict access:", file=out)
    print("    Settings -> Tools -> MCP Server -> Exposed Tools", file=out)
    print("  Keep exactly these enabled (the read-only policy set):", file=out)
    for tool in result.get("allowed", []):
        print(f"    [x] {tool}", file=out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="127.0.0.1", help="IDE host (default 127.0.0.1)")
    ap.add_argument("--port", type=int, help="IDE MCP port; omit with --discover")
    ap.add_argument(
        "--discover",
        action="store_true",
        help="read the IDE-assigned ports from ~/.claude.json instead of assuming them",
    )
    ap.add_argument("--config", default=None, help="path to ~/.claude.json (default: $HOME/.claude.json)")
    ap.add_argument("--timeout", type=float, default=10.0, help="handshake deadline once connected")
    ap.add_argument(
        "--connect-timeout",
        type=float,
        default=1.0,
        help="TCP connect bound — keeps pod launch fast when no IDE is running (default 1s)",
    )
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument(
        "--relay-ports",
        action="store_true",
        help="print one 'port<TAB>server label' line per policy-conforming server on "
        "stdout, reports on stderr (the interface claude-pod consumes)",
    )
    args = ap.parse_args(argv)

    if not args.discover and args.port is None:
        ap.error("one of --port or --discover is required")

    # The policy is POLICY_TOOLS, full stop — deliberately not a flag. A runtime
    # override would let a launch wrapper widen the set and still print "OK",
    # which is exactly the false green this tool exists to prevent. Changing the
    # policy means changing this file, where the harness-docs coupling test sees it.
    allowed = POLICY_TOOLS

    # --relay-ports keeps stdout machine-only so bash can read ports from it; the
    # human/JSON report moves to stderr. This holds in every mode — --port and
    # --json included — so no flag combination silently drops the port list.
    report_to = sys.stderr if args.relay_ports else sys.stdout

    if not args.discover:
        result = check_port(args.host, args.port, allowed, args.timeout, args.connect_timeout)
        if args.json:
            print(json.dumps({k: v for k, v in result.items() if k != "code"}), file=report_to)
        else:
            _report(result, args.host, stream=report_to, compact=args.relay_ports)
        if args.relay_ports and result["code"] == OK and result["status"] == "ok":
            print(_relay_line(result))
        return result["code"]

    config_path = pathlib.Path(args.config) if args.config else pathlib.Path(os.path.expanduser("~/.claude.json"))
    servers = discover_servers(load_claude_config(config_path))
    if not servers:
        if args.json:
            print(json.dumps({"servers": []}), file=report_to)
        elif not args.relay_ports:
            print(f"ide-preflight: no IDE MCP server configured in {config_path} — nothing to check")
        return OK  # nothing configured is not a failure; the oracle is optional

    results = []
    for name, port in servers:
        result = check_port(args.host, port, allowed, args.timeout, args.connect_timeout)
        result["name"] = name
        results.append(result)

    # Exit code across several servers: DRIFT is the state that needs action, so
    # it outranks a merely absent or unreachable IDE. Below DRIFT the order is a
    # deterministic max, not first-wins — PROTOCOL (3) over UNREACHABLE (2) over OK.
    codes = [r["code"] for r in results]
    worst = DRIFT if DRIFT in codes else max(codes)

    if args.json:
        print(json.dumps({"servers": [{k: v for k, v in r.items() if k != "code"} for r in results]}), file=report_to)
    else:
        for result in results:
            # An unreachable IDE is the normal case (it just is not running) — saying
            # so on every pod launch would be noise. Anything else is worth a line.
            if args.relay_ports and result["status"] == "unreachable":
                continue
            _report(result, args.host, label=f"[{result['name']}]", stream=report_to, compact=args.relay_ports)

    if args.relay_ports:
        # Only policy-conforming servers get relayed. A drifting IDE stays reachable
        # from the pod regardless — the warning above says so — but we will not make
        # it convenient by wiring it up.
        for result in results:
            if result["code"] == OK and result["status"] == "ok":
                print(_relay_line(result))
    return worst


if __name__ == "__main__":
    sys.exit(main())
