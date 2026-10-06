#!/usr/bin/env python3
"""Enumerate a JetBrains IDE's MCP tools and hold them to the harness's exposure policy.

Exit codes, the interface claude-dev branches on: 0 the exposed set is within
policy, 1 it drifts outside policy, 2 no configured IDE answered, 3 one
answered but the MCP handshake failed.
"""

import argparse
import http.client
import json
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, NamedTuple, TextIO

# The IDE's own Auto-Configure writes its MCP endpoint into ~/.claude.json
# under these names; the port is IDE-assigned and machine-specific.
IDE_SERVER_NAMES = ("idea", "goland")

# The port is a persisted, user-editable setting, so identity is the check
# that works: the target must prove it is a JetBrains MCP server.
_JETBRAINS_SERVER_MARKER = "mcp server"

# The exposure policy documented in the stacks' MCP-integration skills: a
# tool earns a slot only if it carries information plain text cannot
# reconstruct and neither writes files nor executes code. build_project is
# absent because with Gradle delegation it executes build.gradle.
POLICY_TOOLS = frozenset(
    {
        "get_file_problems",
        "get_project_dependencies",
        "get_project_modules",
        "get_symbol_info",
        "search_symbol",
    }
)

# Named only to make the warning specific; the check is a subset test.
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

# Project-check probes in preference order: policy tools whose only argument
# is projectPath, so the probe is exactly the call it predicts.
_PROJECT_PROBE_TOOLS = ("get_project_modules", "get_project_dependencies")
_INITIALIZE_ID = 1
_FIRST_PAGE_ID = 2
_PROBE_ID = 100
_PROTOCOL_VERSION = "2024-11-05"

# The IDE rejects any request whose Host is not localhost.
_HOST_HEADER = "localhost"
_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
_UNPRIVILEGED_PORTS = range(1024, 65536)

HOST = "127.0.0.1"
CLAUDE_CONFIG = "~/.claude.json"

# Caps on reads from an unauthenticated, possibly hostile server: the socket
# timeout is per-recv, so only a wall-clock deadline bounds a dribbling
# stream.
_MAX_LINES = 10_000
_MAX_LINE_BYTES = 1 << 20
_MAX_TOOL_PAGES = 16
_READ_CHUNK_BYTES = 8192
_ERROR_EXCERPT_CHARS = 200

_PRINTABLE_START = 0x20
_C1_CONTROLS = range(0x7F, 0xA0)
_INVISIBLE_CATEGORIES = ("Cf", "Zl", "Zp")

JsonObject = dict[str, Any]


class MCPError(Exception):
    """The port answered, but not as a working MCP server."""


def _build_opener() -> urllib.request.OpenerDirector:
    """Build an opener that speaks plain HTTP only and never follows a redirect."""
    # No file: or ftp: handler, so a URL from the pod-writable ~/.claude.json
    # cannot become a local-file read; no redirect handler, so a 3xx cannot
    # walk the probe off loopback. UnknownHandler makes an unhandled scheme
    # raise instead of returning None.
    opener = urllib.request.OpenerDirector()
    opener.add_handler(urllib.request.HTTPHandler())
    opener.add_handler(urllib.request.HTTPErrorProcessor())
    opener.add_handler(urllib.request.HTTPDefaultErrorHandler())
    opener.add_handler(urllib.request.UnknownHandler())
    return opener


_OPENER = _build_opener()


def is_jetbrains_mcp_server(server_info: JsonObject) -> bool:
    """Tell whether serverInfo identifies a JetBrains IDE MCP server."""
    name = server_info.get("name")
    return isinstance(name, str) and _JETBRAINS_SERVER_MARKER in name.lower()


def sse_payload(line: str) -> str | None:
    """Return the payload of an SSE data line, or None for any other line."""
    if not line.startswith("data:"):
        return None
    return line[len("data:") :].lstrip()


def classify(
    exposed: set[str], allowed: frozenset[str] | set[str]
) -> tuple[int, list[str]]:
    """Compare an exposed tool set against policy, returning the code and the extras."""
    extras = sorted(exposed - set(allowed))
    return (DRIFT if extras else OK), extras


def describe(tool: str) -> str:
    """Name why a tool sits outside policy."""
    return KNOWN_DANGEROUS.get(tool, "not in the policy set")


def _is_displayable(char: str) -> bool:
    """Tell whether a character may reach the terminal unchanged."""
    code = ord(char)
    return char == "\t" or (
        code >= _PRINTABLE_START
        and code not in _C1_CONTROLS
        and unicodedata.category(char) not in _INVISIBLE_CATEGORIES
    )


def sanitize(text: str) -> str:
    """Strip terminal-spoofing characters from a server-supplied string."""
    # An escape could overwrite the DRIFT warning; a bidi override or
    # zero-width character could render a dangerous tool name as benign.
    return "".join(char for char in text if _is_displayable(char))


def loopback_sse_port(url: str) -> int | None:
    """Return the port of a loopback SSE URL, or None when the URL is not one."""
    # A server the IDE published elsewhere is not the local IDE and must not
    # be probed or bridged; a privileged port is never where an IDE publishes.
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return None
    if parsed.scheme != "http" or parsed.hostname not in _LOOPBACK_HOSTS:
        return None
    try:
        port = parsed.port
    except ValueError:
        return None
    if port is None or port not in _UNPRIVILEGED_PORTS:
        return None
    return port


def _server_scopes(config: JsonObject) -> list[Any]:
    """List every mcpServers map the config carries, top-level and per project."""
    scopes = [config.get("mcpServers")]
    projects = config.get("projects")
    if isinstance(projects, dict):
        scopes.extend(
            project.get("mcpServers")
            for project in projects.values()
            if isinstance(project, dict)
        )
    return scopes


def discover_servers(config: JsonObject) -> list[tuple[str, int]]:
    """Find the (name, port) of each IDE MCP server the config carries."""
    # Two IDEs cannot share a port, so the same port under two names is one
    # server; counting it twice would break the exactly-one bridge rule.
    found: list[tuple[str, int]] = []
    for servers in _server_scopes(config):
        if not isinstance(servers, dict):
            continue
        for name in IDE_SERVER_NAMES:
            entry = servers.get(name)
            url = entry.get("url") if isinstance(entry, dict) else None
            port = loopback_sse_port(url) if isinstance(url, str) else None
            if port is not None and all(port != known for _, known in found):
                found.append((name, port))
    return found


def load_claude_config(path: Path) -> JsonObject:
    """Read ~/.claude.json, reading a missing or malformed file as no IDE configured."""
    # ValueError covers malformed JSON and invalid UTF-8, RecursionError a
    # deeply nested document.
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError, RecursionError):
        return {}
    return data if isinstance(data, dict) else {}


class Session:
    """Speak minimal MCP over SSE: one long-lived stream, one short POST per request."""

    def __init__(self, host: str, port: int, timeout: float) -> None:
        """Open the stream and read the endpoint event within the deadline."""
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
        # The caller's close never runs when the constructor raises.
        try:
            self.endpoint = self._read_endpoint()
        except BaseException:
            self.close()
            raise

    def _lines(self) -> Iterator[str]:
        """Yield stream lines under the byte, line, and deadline caps."""
        # Bounded chunk reads rather than readline, which would buffer a
        # newline-free stream forever, past both caps.
        buffer = b""
        count = 0
        while True:
            newline = buffer.find(b"\n")
            if newline != -1:
                raw, buffer = buffer[:newline], buffer[newline + 1 :]
                count += 1
                if count > _MAX_LINES:
                    raise MCPError(
                        f"server streamed more than {_MAX_LINES} lines without a usable response"
                    )
                yield raw.decode("utf-8", "replace").rstrip("\r")
                continue
            if len(buffer) > _MAX_LINE_BYTES:
                raise MCPError("server sent an oversized SSE line")
            if time.monotonic() > self.deadline:
                raise MCPError(
                    f"no usable response within {self.timeout:.0f}s (server stalled)"
                )
            chunk = self.stream.read1(_READ_CHUNK_BYTES)
            if not chunk:
                if buffer:
                    yield buffer.decode("utf-8", "replace").rstrip("\r")
                return
            buffer += chunk

    def _read_endpoint(self) -> str:
        for line in self._lines():
            payload = sse_payload(line)
            if payload and payload.startswith("/"):
                return payload
        raise MCPError("stream closed before the endpoint event — not an MCP server")

    def post(self, payload: JsonObject) -> None:
        """Send one JSON-RPC message to the endpoint."""
        request = urllib.request.Request(
            f"{self.base}{self.endpoint}",
            data=json.dumps(payload).encode(),
            headers={"Host": _HOST_HEADER, "Content-Type": "application/json"},
            method="POST",
        )
        _OPENER.open(request, timeout=self.timeout).close()

    def await_id(self, want: int) -> JsonObject:
        """Read the stream until the response carrying this id arrives."""
        # Only a message with result or error counts: a server-initiated
        # request may reuse the id number in its own id space.
        for line in self._lines():
            payload = sse_payload(line)
            if not payload or not payload.startswith("{"):
                continue
            try:
                message = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(message, dict)
                and message.get("id") == want
                and ("result" in message or "error" in message)
            ):
                return message
        raise MCPError(f"stream closed before a response to request id={want}")

    def close(self) -> None:
        """Close the stream."""
        self.stream.close()


def _result_of(message: JsonObject, what: str) -> JsonObject:
    """Return the object result of a JSON-RPC response, or raise MCPError."""
    if not isinstance(message, dict):
        raise MCPError(f"{what}: response was not a JSON object")
    result = message.get("result")
    if not isinstance(result, dict):
        raise MCPError(
            f"{what} failed or returned no result object: "
            f"{json.dumps(message)[:_ERROR_EXCERPT_CHARS]}"
        )
    return result


# Distinct verdicts because the operator's fix differs; all three map to an
# unverifiable project, which is never bridged.
_UNVERIFIABLE_REASONS = {
    "no_probe_tool": f"no probe tool exposed ({'/'.join(_PROJECT_PROBE_TOOLS)})",
    "probe_failed": "the probe call failed",
    "unusable_response": "the probe response was unusable",
}


def probe_project(session: Session, exposed: set[str], project: str) -> str:
    """Ask the IDE whether project resolves to an open project, never raising."""
    # The verdict is the IDE's own containment resolution, so a subdirectory
    # of an open project counts. A stalled probe degrades to probe_failed and
    # never changes the completed policy verdict.
    tool = next((name for name in _PROJECT_PROBE_TOOLS if name in exposed), None)
    if tool is None:
        return "no_probe_tool"
    try:
        session.post(
            {
                "jsonrpc": "2.0",
                "id": _PROBE_ID,
                "method": "tools/call",
                "params": {"name": tool, "arguments": {"projectPath": project}},
            }
        )
        result = session.await_id(_PROBE_ID).get("result")
    except (MCPError, OSError, http.client.HTTPException, RecursionError):
        return "probe_failed"
    # Open needs positive evidence: a real success carries a content array.
    if not isinstance(result, dict) or not isinstance(result.get("content"), list):
        return "unusable_response"
    return "not_open" if result.get("isError") else "open"


def _initialize(session: Session) -> JsonObject:
    """Run the MCP handshake and return the serverInfo of a JetBrains server."""
    session.post(
        {
            "jsonrpc": "2.0",
            "id": _INITIALIZE_ID,
            "method": "initialize",
            "params": {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "ide-preflight", "version": "1"},
            },
        }
    )
    init_result = _result_of(session.await_id(_INITIALIZE_ID), "initialize")
    server_info = init_result.get("serverInfo")
    if not isinstance(server_info, dict):
        server_info = {}
    if not is_jetbrains_mcp_server(server_info):
        raise MCPError(
            f"not a JetBrains IDE MCP server (serverInfo.name="
            f"{server_info.get('name')!r}) — refusing to treat it as the oracle"
        )
    session.post(
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    )
    return server_info


def _tool_names(session: Session) -> set[str]:
    """List every exposed tool name across the paginated tools/list."""
    # A dangerous tool could hide on page 2; hitting the page cap fails loud
    # rather than trusting a partial list.
    names: set[str] = set()
    cursor: str | None = None
    for page in range(_MAX_TOOL_PAGES):
        request_id = _FIRST_PAGE_ID + page
        params = {} if cursor is None else {"cursor": cursor}
        session.post(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/list",
                "params": params,
            }
        )
        result = _result_of(session.await_id(request_id), "tools/list")
        tools = result.get("tools")
        if not isinstance(tools, list):
            raise MCPError("tools/list returned no tools array")
        names |= {
            tool["name"]
            for tool in tools
            if isinstance(tool, dict) and isinstance(tool.get("name"), str)
        }
        cursor = result.get("nextCursor")
        if not isinstance(cursor, str) or not cursor:
            return names
    raise MCPError(
        f"tools/list still paginating after {_MAX_TOOL_PAGES} pages — refusing a partial tool list"
    )


@dataclass(frozen=True, slots=True)
class Probe:
    """One port to check, with the policy and the deadlines to hold it to."""

    host: str
    port: int
    allowed: frozenset[str] | set[str]
    timeout: float
    connect_timeout: float = 1.0
    project: str | None = None


def enumerate_tools(probe: Probe) -> tuple[JsonObject, set[str], str | None]:
    """Handshake and return the serverInfo, the exposed tool names, and the probe verdict."""
    # Only a policy-conforming set is probed for the project: a drifting
    # server could never earn a bridge line.
    session = Session(probe.host, probe.port, probe.timeout)
    try:
        server_info = _initialize(session)
        names = _tool_names(session)
        verdict = None
        if probe.project is not None and not (names - set(probe.allowed)):
            verdict = probe_project(session, names, probe.project)
        return server_info, names, verdict
    finally:
        session.close()


@dataclass(frozen=True, slots=True)
class PortResult:
    """The verdict of one probed port."""

    status: str
    host: str
    port: int
    code: int
    error: str = ""
    server: str = "unknown"
    version: str = "unknown"
    exposed: list[str] = field(default_factory=list)
    extras: list[str] = field(default_factory=list)
    allowed: list[str] = field(default_factory=list)
    project: str | None = None
    project_open: bool | None = None
    project_unverifiable: str | None = None
    name: str = ""


class _ProjectVerdict(NamedTuple):
    """The project fields a probe verdict yields."""

    project: str | None
    project_open: bool | None
    project_unverifiable: str | None


def _project_verdict(probe: Probe, verdict: str | None) -> _ProjectVerdict:
    """Translate a probe verdict into the result's project fields."""
    if verdict is None:
        return _ProjectVerdict(None, None, None)
    project_open = {"open": True, "not_open": False}.get(verdict)
    unverifiable = (
        None
        if project_open is not None
        else _UNVERIFIABLE_REASONS.get(verdict, verdict)
    )
    return _ProjectVerdict(probe.project, project_open, unverifiable)


def check_port(probe: Probe) -> PortResult:
    """Probe one port and return its result, never raising."""
    # The TCP pre-probe keeps pod launch fast when no IDE runs: a closed port
    # refuses instantly, a filtered one costs at most connect_timeout.
    try:
        socket.create_connection(
            (probe.host, probe.port), timeout=probe.connect_timeout
        ).close()
    except OSError:
        return PortResult("unreachable", probe.host, probe.port, UNREACHABLE)
    try:
        server_info, exposed, verdict = enumerate_tools(probe)
    except urllib.error.HTTPError as exc:
        # Something speaks HTTP there, just not MCP; distinct from
        # unreachable so the operator hunts the right problem.
        return PortResult(
            "protocol_error",
            probe.host,
            probe.port,
            PROTOCOL,
            error=f"HTTP {exc.code} — not an MCP server",
        )
    except (urllib.error.URLError, OSError):
        return PortResult("unreachable", probe.host, probe.port, UNREACHABLE)
    except (
        MCPError,
        http.client.HTTPException,
        json.JSONDecodeError,
        KeyError,
        AttributeError,
        TypeError,
        RecursionError,
    ) as exc:
        return PortResult(
            "protocol_error", probe.host, probe.port, PROTOCOL, error=sanitize(str(exc))
        )
    code, extras = classify(exposed, probe.allowed)
    project = _project_verdict(probe, verdict)
    return PortResult(
        "drift" if extras else "ok",
        probe.host,
        probe.port,
        code,
        server=server_info.get("name", "unknown"),
        version=server_info.get("version", "unknown"),
        exposed=sorted(exposed),
        extras=extras,
        allowed=sorted(probe.allowed),
        project=project.project,
        project_open=project.project_open,
        project_unverifiable=project.project_unverifiable,
    )


def _bridgeable(result: PortResult, *, project_required: bool) -> bool:
    """Tell whether a server has earned a bridge line."""
    # Unverifiable does not qualify: bridge only what is verified.
    if result.code != OK or result.status != "ok":
        return False
    return not project_required or result.project_open is True


def _project_note(result: PortResult) -> str:
    """Describe the project verdict in one clause, empty when no check ran."""
    if result.project is None:
        return ""
    path = sanitize(result.project)
    if result.project_open is True:
        return f"project {path} is open"
    if result.project_open is False:
        return f"project {path} is NOT open"
    return f"project {path} unverifiable — {result.project_unverifiable or 'unknown cause'}"


def _bridge_line(result: PortResult) -> str:
    """Render the machine line for one bridgeable server: port, tab, server label."""
    # claude-dev uses the label only in its own messages, never in a command;
    # it is server-supplied, so it is sanitized like everything printed.
    label = sanitize(f"{result.server} {result.version}").strip()
    return f"{result.port}\t{label}"


_DRIFT_ADVICE = (
    "",
    "  These are reachable from any container on the Docker VM, with or without",
    "  a bridge: the IDE's MCP server has no authentication and its loopback bind",
    "  does not confine it. Remove them in the IDE to actually restrict access:",
    "    Settings -> Tools -> MCP Server -> Exposed Tools",
    "  Keep exactly these enabled (the read-only policy set):",
)


def _report_lines(result: PortResult, *, label: str, compact: bool) -> list[str]:
    """Render one server's verdict; compact collapses a healthy server to one line."""
    where = f"{result.host}:{result.port}"
    tag = f"{label} " if label else ""
    if result.status == "unreachable":
        return [f"ide-preflight: {tag}no IDE on {where} — oracle unavailable"]
    if result.status == "protocol_error":
        return [
            f"ide-preflight: {tag}{where} answered but is not a usable oracle — {result.error}"
        ]
    # Names are sanitized for display only; the raw names already drove
    # classify, so a look-alike name was flagged as drift there.
    server = sanitize(result.server)
    version = sanitize(result.version)
    exposed = [sanitize(tool) for tool in result.exposed]
    note = _project_note(result)
    if compact and not result.extras:
        return [
            f"ide-preflight: {tag}{server} {version} on {where} — "
            f"OK: exposed set within policy ({len(exposed)} tools)"
            + (f"; {note}" if note else "")
        ]
    lines = [
        f"ide-preflight: {tag}{server} {version} on {where}",
        f"  exposed: {len(exposed)} tool(s) — {', '.join(exposed)}",
    ]
    if note:
        lines.append(f"  {note}")
    if not result.extras:
        lines.append("  verdict: OK — exposed set is within policy")
        return lines
    lines.append(f"  verdict: DRIFT — {len(result.extras)} tool(s) outside policy:")
    lines.extend(f"    - {sanitize(tool)}: {describe(tool)}" for tool in result.extras)
    lines.extend(_DRIFT_ADVICE)
    lines.extend(f"    [x] {tool}" for tool in result.allowed)
    return lines


def _report(
    result: PortResult,
    *,
    label: str = "",
    stream: TextIO | None = None,
    compact: bool = False,
) -> None:
    """Print one server's verdict."""
    out = stream or sys.stdout
    for line in _report_lines(result, label=label, compact=compact):
        print(line, file=out)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # Discovery is the only mode; the flag stays required so a bare
    # invocation is a loud usage error, never a silent probe.
    parser.add_argument(
        "--discover",
        action="store_true",
        required=True,
        help=f"read the IDE-assigned ports from {CLAUDE_CONFIG} (the only mode)",
    )
    parser.add_argument(
        "--timeout", type=float, default=10.0, help="handshake deadline once connected"
    )
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=1.0,
        help="TCP connect bound — keeps pod launch fast when no IDE is running (default 1s)",
    )
    parser.add_argument(
        "--bridge-ports",
        action="store_true",
        help="print one 'port<TAB>server label' line per policy-conforming server on "
        "stdout, reports on stderr (the interface claude-dev consumes)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="verify this path resolves to an open project in each conforming IDE; "
        "with --bridge-ports, only verified-open servers emit a bridge line",
    )
    return parser.parse_args(argv)


def _worst_code(results: list[PortResult]) -> int:
    """Pick the exit code: drift outranks everything, then protocol over unreachable."""
    codes = [result.code for result in results]
    return DRIFT if DRIFT in codes else max(codes)


def main(argv: list[str] | None = None) -> int:
    """Check every configured IDE and return the worst verdict."""
    args = _parse_args(argv)
    # The policy is not a flag: a runtime override would let a launch wrapper
    # widen the set and still print OK.
    allowed = POLICY_TOOLS
    # --bridge-ports keeps stdout machine-only so bash can read ports from it.
    report_to = sys.stderr if args.bridge_ports else sys.stdout
    # The failure direction is degrade, never raise: an unresolvable home
    # reads as no IDE configured.
    try:
        config_path = Path(CLAUDE_CONFIG).expanduser()
    except RuntimeError:
        config_path = Path(CLAUDE_CONFIG)
    servers = discover_servers(load_claude_config(config_path))
    if not servers:
        if not args.bridge_ports:
            print(
                f"ide-preflight: no IDE MCP server configured in {config_path} — nothing to check"
            )
        return OK
    results = [
        replace(
            check_port(
                Probe(
                    HOST,
                    port,
                    allowed,
                    args.timeout,
                    args.connect_timeout,
                    args.project,
                )
            ),
            name=name,
        )
        for name, port in servers
    ]
    for result in results:
        # An unreachable IDE is the normal case when it is not running.
        if args.bridge_ports and result.status == "unreachable":
            continue
        _report(
            result,
            label=f"[{result.name}]",
            stream=report_to,
            compact=args.bridge_ports,
        )
    if args.bridge_ports:
        # A drifting IDE stays reachable regardless, as the warning says, but
        # it does not get the convenience of a bridge.
        for result in results:
            if _bridgeable(result, project_required=args.project is not None):
                print(_bridge_line(result))
    return _worst_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
