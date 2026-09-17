#!/usr/bin/env python3
"""Tests for ide_preflight: pure helpers, and check_port end to end against a scripted loopback MCP server."""

import contextlib
import io
import json
import pathlib
import re
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
from unittest import mock

import ide_preflight as p

JETBRAINS_SERVER_NAME = "IntelliJ IDEA MCP Server"
ANOTHER_JETBRAINS_SERVER_NAME = "GoLand MCP Server"
SOME_OTHER_SERVER_NAME = "some-other-tool"
SOME_VERSION = "2026.1.4"

A_POLICY_TOOL = "search_symbol"
ANOTHER_POLICY_TOOL = "get_file_problems"
PROBE_TOOL, FALLBACK_PROBE_TOOL = p._PROJECT_PROBE_TOOLS
A_WRITE_TOOL = "apply_patch"
ANOTHER_WRITE_TOOL = "execute_tool"
BUILD_TOOL = "build_project"
AN_UNDOCUMENTED_READ_TOOL = "get_all_open_file_paths"
DOCUMENTED_POLICY_ROSTER = {
    "get_file_problems",
    "get_project_dependencies",
    "get_project_modules",
    "get_symbol_info",
    "search_symbol",
}

IDEA_PORT = 64342
GOLAND_PORT = 64343
SOME_PORT = 1234
ANOTHER_PORT = 60000
SOME_UNRELATED_PORT = 5432
A_PRIVILEGED_PORT = p._UNPRIVILEGED_PORTS.start - 1
OFF_BOX_ADDRESS = "192.168.5.2"
OFF_BOX_NAME = "remote.example"

SOME_PROJECT = "/pod/work"
SOME_OTHER_PROJECT = "/Users/x/other"
SOME_ENDPOINT = "/message?sessionId=x"
SOME_PROBE_PAYLOAD = '{"modules":[]}'
SOME_TEXT = "secret"
DEEPLY_NESTED_JSON = "[" * 100_000

HANDSHAKE_TIMEOUT_S = 5.0
SHORT_DEADLINE_S = 2.0
CONNECT_TIMEOUT_S = 1.0
# How far past its deadline a bounded check may run before it counts as a hang.
DEADLINE_GRACE_S = 5.0
STREAM_HOLD_S = 0.3
TRICKLE_INTERVAL_S = 0.05
DRIBBLE_INTERVAL_S = 0.2


def sse_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/sse"


def a_config(*servers: tuple[str, int]) -> dict:
    return {
        "mcpServers": {name: {"url": sse_url(p.HOST, port)} for name, port in servers}
    }


def tool_calls(server: "ScriptedMCPServer") -> list[dict]:
    return [
        m
        for m in server.posts
        if isinstance(m, dict) and m.get("method") == "tools/call"
    ]


def run_main_discover(port, *extra):
    """Drive main() in discover mode against a config naming only this port."""
    with tempfile.TemporaryDirectory() as d:
        cfg = pathlib.Path(d) / "claude.json"
        cfg.write_text(json.dumps(a_config(("idea", port))))
        out, err = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(p, "CLAUDE_CONFIG", str(cfg)),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            code = p.main(
                [
                    "--discover",
                    "--bridge-ports",
                    "--timeout",
                    str(HANDSHAKE_TIMEOUT_S),
                    *extra,
                ]
            )
        return code, out.getvalue(), err.getvalue()


def report_of(result) -> str:
    buf = io.StringIO()
    p._report(result, stream=buf)
    return buf.getvalue()


def response(request_id: int, result) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


class ScriptedMCPServer:
    """A loopback HTTP/SSE server that plays a scripted MCP role, well-behaved or hostile."""

    def __init__(
        self,
        *,
        identity=(JETBRAINS_SERVER_NAME, SOME_VERSION),
        tools=(A_POLICY_TOOL,),
        mode="ok",
        project_mode=None,
    ):
        self.server_name, self.version = identity
        self.tools = list(tools)
        self.mode = mode
        self.project_mode = project_mode
        self.posts = []
        self._sock = socket.socket()
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((p.HOST, 0))
        self.port = self._sock.getsockname()[1]
        self._sock.listen(8)
        self._stop = False
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _serve(self):
        while not self._stop:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _chunk(self, body: bytes) -> bytes:
        return f"{len(body):x}".encode() + b"\r\n" + body + b"\r\n"

    def _sse(self, obj) -> bytes:
        return self._chunk(
            b"event: message\r\ndata: " + json.dumps(obj).encode() + b"\r\n\r\n"
        )

    def _handle(self, conn):
        try:
            self._handle_inner(conn)
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _read_head(self, conn):
        req = b""
        while b"\r\n\r\n" not in req:
            part = conn.recv(4096)
            if not part:
                return None
            req += part
        return req

    def _accept_post(self, conn, req):
        head, _, body = req.partition(b"\r\n\r\n")
        m = re.search(rb"content-length:\s*(\d+)", head, re.IGNORECASE)
        want = int(m.group(1)) if m else 0
        while len(body) < want:
            part = conn.recv(4096)
            if not part:
                break
            body += part
        try:
            self.posts.append(json.loads(body.decode("utf-8", "replace")))
        except ValueError:
            self.posts.append(None)
        conn.sendall(b"HTTP/1.1 202 Accepted\r\nContent-Length: 8\r\n\r\nAccepted")

    def _stall_before_endpoint(self, conn):
        if self.mode == "oversized_line":
            conn.sendall(self._chunk(b"data: " + b"a" * (2 * p._MAX_LINE_BYTES)))
            time.sleep(STREAM_HOLD_S)
            return
        # Each recv is fast and the line never completes, so only the
        # wall-clock deadline ends this.
        conn.sendall(self._chunk(b"data: "))
        while not self._stop:
            try:
                conn.sendall(self._chunk(b"aaaa"))
            except OSError:
                return
            time.sleep(TRICKLE_INTERVAL_S)

    def _dribble(self, conn):
        while not self._stop:
            conn.sendall(self._chunk(b"event: ping\r\ndata: keep-alive\r\n\r\n"))
            time.sleep(DRIBBLE_INTERVAL_S)

    def _init_message(self):
        if self.mode == "null_result_init":
            return response(p._INITIALIZE_ID, None)
        return response(
            p._INITIALIZE_ID,
            {
                "protocolVersion": p._PROTOCOL_VERSION,
                "capabilities": {},
                "serverInfo": {"name": self.server_name, "version": self.version},
            },
        )

    def _listing(self):
        if self.mode == "null_tools":
            return response(p._FIRST_PAGE_ID, {"tools": None})
        if self.mode == "list_result_tools":
            return response(p._FIRST_PAGE_ID, [])
        if self.mode == "scalar_tool":
            return response(p._FIRST_PAGE_ID, {"tools": [42, {"name": A_POLICY_TOOL}]})
        if self.mode in ("ok", "ping_before_response"):
            return response(
                p._FIRST_PAGE_ID, {"tools": [{"name": n} for n in self.tools]}
            )
        return None

    def _send_pages(self, conn):
        if self.mode == "paginated":
            # The write tool hides on page 2; page 1 alone reads as OK.
            first = {"tools": [{"name": n} for n in self.tools], "nextCursor": "page2"}
            conn.sendall(self._sse(response(p._FIRST_PAGE_ID, first)))
            second = {"tools": [{"name": A_WRITE_TOOL}]}
            conn.sendall(self._sse(response(p._FIRST_PAGE_ID + 1, second)))
        elif self.mode == "cursor_loop":
            first_id = p._FIRST_PAGE_ID
            for i in range(first_id, first_id + 2 * p._MAX_TOOL_PAGES):
                page = {"tools": [], "nextCursor": f"p{i}"}
                conn.sendall(self._sse(response(i, page)))
        listed = self._listing()
        if listed is not None:
            conn.sendall(self._sse(listed))

    def _send_probe(self, conn):
        # Sent proactively like everything else: the client reads until its
        # id matches, so an unconsumed probe response is harmless.
        if self.project_mode == "open":
            content = {"content": [{"type": "text", "text": SOME_PROBE_PAYLOAD}]}
            conn.sendall(self._sse(response(p._PROBE_ID, content)))
        elif self.project_mode == "not_open":
            # The real IDE error shape, roster tail included; the verdict
            # comes from isError alone, never from this text.
            text = (
                f"`projectPath`=`{SOME_PROJECT}` doesn't correspond to any open project.\n"
                f' Currently open projects: {{"projects":[{{"path":"{SOME_OTHER_PROJECT}"}}]}}'
            )
            error = {"isError": True, "content": [{"type": "text", "text": text}]}
            conn.sendall(self._sse(response(p._PROBE_ID, error)))
        elif self.project_mode == "null_result":
            conn.sendall(self._sse(response(p._PROBE_ID, None)))
        elif self.project_mode == "empty_result":
            conn.sendall(self._sse(response(p._PROBE_ID, {})))
        elif self.project_mode == "deep_nesting":
            nested = DEEPLY_NESTED_JSON.encode()
            conn.sendall(
                self._chunk(
                    b'data: {"id":%d,"result":' % p._PROBE_ID + nested + b"\r\n\r\n"
                )
            )

    def _handle_inner(self, conn):
        req = self._read_head(conn)
        if req is None:
            return
        if not req.startswith(b"GET"):
            self._accept_post(conn, req)
            return
        conn.sendall(
            b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n"
        )
        if self.mode in ("oversized_line", "trickle_no_newline"):
            self._stall_before_endpoint(conn)
            return
        conn.sendall(
            self._chunk(
                b"event: endpoint\r\ndata: " + SOME_ENDPOINT.encode() + b"\r\n\r\n"
            )
        )
        if self.mode == "dribble":
            self._dribble(conn)
            return
        if self.mode == "ping_before_response":
            # A server-initiated request whose id collides with the client's
            # pending request id.
            ping = {"jsonrpc": "2.0", "id": p._INITIALIZE_ID, "method": "ping"}
            conn.sendall(self._sse(ping))
        conn.sendall(self._sse(self._init_message()))
        self._send_pages(conn)
        self._send_probe(conn)
        # Hold the stream open so the client reads before close.
        time.sleep(STREAM_HOLD_S)

    def close(self):
        self._stop = True
        try:
            self._sock.close()
        except OSError:
            pass


def check(server, timeout=HANDSHAKE_TIMEOUT_S, **fields):
    return p.check_port(p.Probe(p.HOST, server.port, p.POLICY_TOOLS, timeout, **fields))


def timed_check(server, timeout):
    start = time.monotonic()
    result = check(server, timeout)
    return result, time.monotonic() - start


class CheckPortEndToEnd(unittest.TestCase):
    """check_port survives a hostile server and always returns a clean record."""

    def test_a_healthy_server_is_ok(self):
        with ScriptedMCPServer(tools=[A_POLICY_TOOL, ANOTHER_POLICY_TOOL]) as s:
            r = check(s)
        self.assertEqual(r.code, p.OK)
        self.assertEqual(r.server, JETBRAINS_SERVER_NAME)

    def test_a_write_tool_outside_policy_is_drift(self):
        with ScriptedMCPServer(tools=[A_POLICY_TOOL, A_WRITE_TOOL]) as s:
            r = check(s)
        self.assertEqual(r.code, p.DRIFT)
        self.assertIn(A_WRITE_TOOL, r.extras)

    def test_the_drift_report_names_the_target_configuration(self):
        # The operator opening Exposed Tools needs to see what the checkboxes
        # should look like, not only what to remove.
        with ScriptedMCPServer(tools=[A_POLICY_TOOL, A_WRITE_TOOL]) as s:
            r = check(s)
        report = report_of(r)
        self.assertIn("Settings -> Tools -> MCP Server -> Exposed Tools", report)
        self.assertIn("Keep exactly these enabled", report)
        for tool in sorted(p.POLICY_TOOLS):
            self.assertIn(f"[x] {tool}", report)

    def test_a_non_jetbrains_identity_is_refused_without_reading_as_drift(self):
        with ScriptedMCPServer(identity=(SOME_OTHER_SERVER_NAME, SOME_VERSION)) as s:
            r = check(s)
        self.assertEqual(r.code, p.PROTOCOL)
        self.assertNotEqual(r.code, p.DRIFT)

    def test_a_null_initialize_result_is_a_protocol_error(self):
        with ScriptedMCPServer(mode="null_result_init") as s:
            r = check(s)
        self.assertEqual(r.code, p.PROTOCOL)

    def test_a_null_tools_array_is_a_protocol_error(self):
        with ScriptedMCPServer(mode="null_tools") as s:
            r = check(s)
        self.assertEqual(r.code, p.PROTOCOL)

    def test_a_list_where_the_result_object_belongs_is_a_protocol_error(self):
        with ScriptedMCPServer(mode="list_result_tools") as s:
            r = check(s)
        self.assertEqual(r.code, p.PROTOCOL)

    def test_a_scalar_tool_element_is_skipped_and_the_valid_entry_counts(self):
        with ScriptedMCPServer(mode="scalar_tool") as s:
            r = check(s)
        self.assertEqual(r.code, p.OK)
        self.assertEqual(r.exposed, [A_POLICY_TOOL])

    def test_a_dribbling_server_hits_the_wall_clock_deadline(self):
        with ScriptedMCPServer(mode="dribble") as s:
            r, elapsed = timed_check(s, SHORT_DEADLINE_S)
        self.assertEqual(r.code, p.PROTOCOL)
        self.assertLess(elapsed, SHORT_DEADLINE_S + DEADLINE_GRACE_S)

    def test_a_newline_free_oversized_sse_line_is_bounded_by_the_byte_cap(self):
        with ScriptedMCPServer(mode="oversized_line") as s:
            r, elapsed = timed_check(s, HANDSHAKE_TIMEOUT_S)
        self.assertEqual(r.code, p.PROTOCOL)
        self.assertLess(elapsed, HANDSHAKE_TIMEOUT_S + DEADLINE_GRACE_S)

    def test_a_trickle_without_newline_hits_the_wall_clock_deadline(self):
        # Bytes keep arriving so no socket timeout fires, and the line never
        # completes so no per-line check runs.
        with ScriptedMCPServer(mode="trickle_no_newline") as s:
            r, elapsed = timed_check(s, SHORT_DEADLINE_S)
        self.assertEqual(r.code, p.PROTOCOL)
        self.assertLess(elapsed, SHORT_DEADLINE_S + DEADLINE_GRACE_S)

    def test_a_paginated_tools_list_is_fully_enumerated(self):
        with ScriptedMCPServer(mode="paginated", tools=[A_POLICY_TOOL]) as s:
            r = check(s)
        self.assertEqual(r.code, p.DRIFT)
        self.assertIn(A_WRITE_TOOL, r.extras)
        self.assertIn(A_POLICY_TOOL, r.exposed)

    def test_an_endless_cursor_fails_loud_rather_than_trust_a_partial_list(self):
        with ScriptedMCPServer(mode="cursor_loop") as s:
            r = check(s)
        self.assertEqual(r.code, p.PROTOCOL)

    def test_a_server_initiated_request_with_a_colliding_id_is_skipped(self):
        with ScriptedMCPServer(mode="ping_before_response", tools=[A_POLICY_TOOL]) as s:
            r = check(s)
        self.assertEqual(r.code, p.OK)

    def test_an_escape_sequence_in_a_tool_name_is_drift_and_the_report_is_sanitized(
        self,
    ):
        with ScriptedMCPServer(tools=[A_POLICY_TOOL + "\x1b]52;c;whatever\x07"]) as s:
            r = check(s)
        self.assertEqual(r.code, p.DRIFT)
        report = report_of(r)
        self.assertNotIn("\x1b", report)
        self.assertNotIn("\x07", report)

    def test_an_unreachable_port_is_clean_and_never_draws_on_the_handshake_budget(
        self,
    ):
        # No IDE running is the everyday case and the preflight runs on every
        # pod launch, so an unreachable verdict costs a connect, not a handshake.
        s = socket.socket()
        s.bind((p.HOST, 0))
        dead = s.getsockname()[1]
        s.close()
        long_budget = 10 * HANDSHAKE_TIMEOUT_S
        start = time.monotonic()
        r = p.check_port(
            p.Probe(
                p.HOST,
                dead,
                p.POLICY_TOOLS,
                long_budget,
                connect_timeout=CONNECT_TIMEOUT_S,
            )
        )
        elapsed = time.monotonic() - start
        self.assertEqual(r.code, p.UNREACHABLE)
        self.assertLess(elapsed, 2 * CONNECT_TIMEOUT_S)


class BridgePortsFlagContract(unittest.TestCase):
    """--bridge-ports prints `port<TAB>label` lines on stdout and the report elsewhere."""

    def test_discover_mode_prints_port_and_label_on_stdout_and_the_report_on_stderr(
        self,
    ):
        with ScriptedMCPServer(tools=[A_POLICY_TOOL]) as s:
            code, out, err = run_main_discover(s.port)
        label = f"{JETBRAINS_SERVER_NAME} {SOME_VERSION}"
        self.assertEqual(code, p.OK)
        self.assertEqual(out.rstrip("\n").split("\t"), [str(s.port), label])
        report = err.strip().splitlines()
        self.assertEqual(len(report), 1)
        self.assertIn(label, report[0])
        self.assertIn("OK: exposed set within policy", report[0])

    def test_a_drifting_server_gets_no_bridge_port(self):
        with ScriptedMCPServer(tools=[A_POLICY_TOOL, A_WRITE_TOOL]) as s:
            code, out, err = run_main_discover(s.port)
        self.assertEqual(code, p.DRIFT)
        self.assertEqual(out, "")
        self.assertIn("DRIFT", err)

    def test_a_bare_invocation_is_a_usage_error(self):
        # A bare run never probes the real ~/.claude.json silently.
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            p.main([])


class ProjectProbe(unittest.TestCase):
    """The --project verdict is the IDE's own resolution, probed with a read-only policy tool on the same session."""

    def test_an_open_project_is_verified_by_one_tools_call_carrying_the_path(self):
        with ScriptedMCPServer(
            tools=[A_POLICY_TOOL, PROBE_TOOL], project_mode="open"
        ) as s:
            r = check(s, project=SOME_PROJECT)
            calls = tool_calls(s)
        self.assertEqual(r.code, p.OK)
        self.assertIs(r.project_open, True)
        self.assertEqual(r.project, SOME_PROJECT)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["params"]["name"], PROBE_TOOL)
        self.assertEqual(calls[0]["params"]["arguments"], {"projectPath": SOME_PROJECT})

    def test_a_project_the_ide_reports_not_open_reads_false(self):
        with ScriptedMCPServer(tools=[PROBE_TOOL], project_mode="not_open") as s:
            r = check(s, project=SOME_PROJECT)
        self.assertIs(r.project_open, False)

    def test_the_fallback_probe_tool_carries_the_probe_when_the_first_is_absent(self):
        with ScriptedMCPServer(tools=[FALLBACK_PROBE_TOOL], project_mode="open") as s:
            r = check(s, project=SOME_PROJECT)
            calls = tool_calls(s)
        self.assertIs(r.project_open, True)
        self.assertEqual([c["params"]["name"] for c in calls], [FALLBACK_PROBE_TOOL])

    def test_no_probe_tool_is_unverifiable_and_never_counts_as_open(self):
        with ScriptedMCPServer(tools=[A_POLICY_TOOL], project_mode="open") as s:
            r = check(s, project=SOME_PROJECT)
            calls = tool_calls(s)
        self.assertEqual(r.code, p.OK)
        self.assertIsNone(r.project_open)
        self.assertIn("no probe tool exposed", r.project_unverifiable)
        self.assertEqual(calls, [])

    def test_a_null_probe_result_is_unverifiable_and_blames_the_response(self):
        with ScriptedMCPServer(tools=[PROBE_TOOL], project_mode="null_result") as s:
            r = check(s, project=SOME_PROJECT)
        self.assertIsNone(r.project_open)
        self.assertIn("response", r.project_unverifiable)

    def test_an_empty_dict_result_is_unverifiable_not_open(self):
        # "open" needs the positive evidence of a content array, or a flaky {}
        # would earn a bridge.
        with ScriptedMCPServer(tools=[PROBE_TOOL], project_mode="empty_result") as s:
            r = check(s, project=SOME_PROJECT)
        self.assertIsNone(r.project_open)

    def test_a_probe_stall_degrades_to_unverifiable_never_to_a_protocol_error(self):
        # A conforming server that never answers the probe, such as an
        # indexing IDE, keeps its policy verdict and exit code.
        with ScriptedMCPServer(tools=[PROBE_TOOL], project_mode=None) as s:
            r = check(s, project=SOME_PROJECT)
        self.assertEqual(r.status, "ok")
        self.assertEqual(r.code, p.OK)
        self.assertIsNone(r.project_open)
        self.assertIn("probe call failed", r.project_unverifiable)

    def test_deeply_nested_json_in_the_probe_response_degrades_to_unverifiable(self):
        with ScriptedMCPServer(tools=[PROBE_TOOL], project_mode="deep_nesting") as s:
            r = check(s, project=SOME_PROJECT)
        self.assertEqual(r.status, "ok")
        self.assertEqual(r.code, p.OK)
        self.assertIsNone(r.project_open)

    def test_a_drifting_server_is_never_probed(self):
        with ScriptedMCPServer(
            tools=[PROBE_TOOL, A_WRITE_TOOL], project_mode="open"
        ) as s:
            r = check(s, project=SOME_PROJECT)
            calls = tool_calls(s)
        self.assertEqual(r.code, p.DRIFT)
        self.assertIsNone(r.project_open)
        self.assertEqual(calls, [])

    def test_without_a_project_no_project_fields_are_set(self):
        with ScriptedMCPServer(tools=[PROBE_TOOL], project_mode="open") as s:
            r = check(s)
        self.assertIsNone(r.project_open)
        self.assertIsNone(r.project)

    def test_the_project_verdict_never_changes_the_exit_code(self):
        with ScriptedMCPServer(tools=[PROBE_TOOL], project_mode="not_open") as s:
            r = check(s, project=SOME_PROJECT)
        self.assertEqual(r.code, p.OK)

    def test_the_report_states_the_verdict(self):
        with ScriptedMCPServer(tools=[PROBE_TOOL], project_mode="not_open") as s:
            r = check(s, project=SOME_PROJECT)
        self.assertIn("NOT open", report_of(r))


class BridgeGateOnProject(unittest.TestCase):
    """With --project, a bridge line means verified open and nothing less."""

    def _main(self, server):
        return run_main_discover(server.port, "--project", SOME_PROJECT)

    def test_an_open_project_emits_the_bridge_line(self):
        with ScriptedMCPServer(tools=[PROBE_TOOL], project_mode="open") as s:
            code, out, err = self._main(s)
        self.assertEqual(code, p.OK)
        self.assertEqual(out.split("\t")[0], str(s.port))
        self.assertIn(f"project {SOME_PROJECT} is open", err)

    def test_a_project_not_open_emits_no_bridge_line(self):
        with ScriptedMCPServer(tools=[PROBE_TOOL], project_mode="not_open") as s:
            code, out, err = self._main(s)
        self.assertEqual(code, p.OK)
        self.assertEqual(out, "")
        self.assertIn("NOT open", err)

    def test_an_unverifiable_project_emits_no_bridge_line(self):
        with ScriptedMCPServer(tools=[A_POLICY_TOOL], project_mode="open") as s:
            code, out, err = self._main(s)
        self.assertEqual(code, p.OK)
        self.assertEqual(out, "")
        self.assertIn("unverifiable", err)


class Sanitize(unittest.TestCase):
    def test_an_ansi_escape_is_stripped(self):
        self.assertEqual(p.sanitize("a\x1b[31mb"), "a[31mb")

    def test_an_osc_sequence_and_its_bell_are_stripped(self):
        self.assertEqual(p.sanitize("x\x1b]52;c;zzz\x07y"), "x]52;c;zzzy")

    def test_c1_controls_are_stripped(self):
        self.assertEqual(p.sanitize("a\x9bb\x85c"), "abc")

    def test_a_tab_and_printable_unicode_are_kept(self):
        self.assertEqual(p.sanitize("a\tb→c"), "a\tb→c")

    def test_the_del_byte_is_dropped(self):
        self.assertEqual(p.sanitize("a\x7fb"), "ab")

    def test_bidi_overrides_and_isolates_are_stripped(self):
        # A reordered tool name could display as a policy one in the report.
        self.assertEqual(p.sanitize("a\u202eb\u2066c\u2069d"), "abcd")

    def test_zero_width_characters_and_the_bom_are_stripped(self):
        self.assertEqual(p.sanitize("a\u200bb\u200dc\ufeffd"), "abcd")

    def test_line_and_paragraph_separators_are_stripped(self):
        self.assertEqual(p.sanitize("a\u2028b\u2029c"), "abc")


class LoopbackSSEPort(unittest.TestCase):
    def test_the_port_is_read_from_a_loopback_sse_url(self):
        self.assertEqual(p.loopback_sse_port(sse_url(p.HOST, IDEA_PORT)), IDEA_PORT)

    def test_localhost_and_the_ipv6_loopback_are_accepted(self):
        self.assertEqual(
            p.loopback_sse_port(sse_url("localhost", GOLAND_PORT)), GOLAND_PORT
        )
        self.assertEqual(
            p.loopback_sse_port(sse_url("[::1]", GOLAND_PORT)), GOLAND_PORT
        )

    def test_any_unprivileged_port_is_accepted_without_a_range_check(self):
        # The IDE's port is user-settable and already diverges from the
        # source's offset scheme, so a range check would reject working configs.
        for port in (ANOTHER_PORT, SOME_PORT):
            self.assertEqual(p.loopback_sse_port(sse_url(p.HOST, port)), port)

    def test_a_non_loopback_host_is_rejected(self):
        self.assertIsNone(p.loopback_sse_port(sse_url(OFF_BOX_ADDRESS, IDEA_PORT)))
        self.assertIsNone(p.loopback_sse_port(sse_url(OFF_BOX_NAME, IDEA_PORT)))

    def test_a_privileged_port_is_rejected(self):
        self.assertIsNone(p.loopback_sse_port(sse_url(p.HOST, A_PRIVILEGED_PORT)))

    def test_a_non_http_scheme_is_rejected(self):
        self.assertIsNone(p.loopback_sse_port(f"https://{p.HOST}:{IDEA_PORT}/sse"))
        self.assertIsNone(p.loopback_sse_port("file:///etc/passwd"))

    def test_a_missing_port_is_rejected(self):
        self.assertIsNone(p.loopback_sse_port(f"http://{p.HOST}/sse"))

    def test_garbage_is_rejected(self):
        self.assertIsNone(p.loopback_sse_port("not a url"))


class DiscoverServers(unittest.TestCase):
    def test_both_ides_are_found_at_their_assigned_ports(self):
        cfg = a_config(("idea", IDEA_PORT), ("goland", GOLAND_PORT))
        self.assertEqual(
            p.discover_servers(cfg), [("idea", IDEA_PORT), ("goland", GOLAND_PORT)]
        )

    def test_a_nondefault_port_is_read_from_the_entry(self):
        cfg = a_config(("idea", ANOTHER_PORT))
        self.assertEqual(p.discover_servers(cfg), [("idea", ANOTHER_PORT)])

    def test_unrelated_mcp_servers_are_ignored(self):
        cfg = a_config(("idea", IDEA_PORT), ("some-other-server", SOME_UNRELATED_PORT))
        self.assertEqual(p.discover_servers(cfg), [("idea", IDEA_PORT)])

    def test_an_entry_repointed_off_loopback_is_ignored(self):
        cfg = {"mcpServers": {"idea": {"url": sse_url(OFF_BOX_ADDRESS, IDEA_PORT)}}}
        self.assertEqual(p.discover_servers(cfg), [])

    def test_an_empty_or_malformed_config_yields_nothing(self):
        self.assertEqual(p.discover_servers({}), [])
        self.assertEqual(p.discover_servers({"mcpServers": None}), [])
        self.assertEqual(p.discover_servers({"mcpServers": {"idea": "nonsense"}}), [])
        self.assertEqual(p.discover_servers({"mcpServers": {"idea": {}}}), [])
        self.assertEqual(p.discover_servers({"mcpServers": {"idea": {"url": 42}}}), [])

    def test_a_project_scoped_server_is_found(self):
        # `claude mcp add` defaults to local scope, which lands under
        # projects.<path>.mcpServers with the same exposure.
        cfg = {"projects": {SOME_OTHER_PROJECT: a_config(("goland", GOLAND_PORT))}}
        self.assertEqual(p.discover_servers(cfg), [("goland", GOLAND_PORT)])

    def test_the_same_server_across_scopes_counts_once_and_a_new_port_is_distinct(
        self,
    ):
        cfg = {
            **a_config(("idea", IDEA_PORT)),
            "projects": {
                "/a": a_config(("idea", IDEA_PORT)),
                "/b": a_config(("idea", ANOTHER_PORT)),
            },
        }
        self.assertEqual(
            p.discover_servers(cfg), [("idea", IDEA_PORT), ("idea", ANOTHER_PORT)]
        )

    def test_a_malformed_projects_scope_is_ignored(self):
        cfg = {"projects": {"/a": "nonsense", "/b": {"mcpServers": None}}}
        self.assertEqual(p.discover_servers(cfg), [])

    def test_two_names_on_one_port_count_once(self):
        # Two IDEs cannot share a port, so stale entries on one port are one
        # server; counted twice, the exactly-one bridge rule would refuse it.
        cfg = a_config(("idea", IDEA_PORT), ("goland", IDEA_PORT))
        self.assertEqual(p.discover_servers(cfg), [("idea", IDEA_PORT)])


class LoadClaudeConfig(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = pathlib.Path(tmp.name) / "c.json"

    def test_a_config_is_read(self):
        self.path.write_text(json.dumps(a_config(("idea", SOME_PORT))))
        self.assertEqual(
            p.discover_servers(p.load_claude_config(self.path)), [("idea", SOME_PORT)]
        )

    def test_a_missing_file_reads_as_empty(self):
        self.assertEqual(p.load_claude_config(self.path), {})

    def test_malformed_json_reads_as_empty(self):
        self.path.write_text("{not json")
        self.assertEqual(p.load_claude_config(self.path), {})

    def test_deeply_nested_json_reads_as_empty(self):
        # The file is pod-writable and parsed on every invocation.
        self.path.write_text(DEEPLY_NESTED_JSON)
        self.assertEqual(p.load_claude_config(self.path), {})

    def test_invalid_utf8_reads_as_empty(self):
        self.path.write_bytes(b'\xff\xfe{"a":1}')
        self.assertEqual(p.load_claude_config(self.path), {})


class RestrictedOpener(unittest.TestCase):
    """The opener speaks plain HTTP only, structurally rather than by a scheme check."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = pathlib.Path(tmp.name)

    def test_the_file_scheme_cannot_be_opened(self):
        path = self.dir / "local.txt"
        path.write_text(SOME_TEXT)
        with self.assertRaises(urllib.error.URLError):
            p._OPENER.open(f"file://{path}", timeout=SHORT_DEADLINE_S)

    def test_the_ftp_scheme_cannot_be_opened(self):
        with self.assertRaises(urllib.error.URLError):
            p._OPENER.open(f"ftp://{p.HOST}/x", timeout=SHORT_DEADLINE_S)

    def test_the_https_scheme_cannot_be_opened(self):
        with self.assertRaises(urllib.error.URLError):
            p._OPENER.open(f"https://{p.HOST}/x", timeout=SHORT_DEADLINE_S)

    def test_no_redirect_file_or_ftp_handler_is_installed(self):
        # A 3xx must not walk the client off loopback after the scheme check.
        handlers = [type(h).__name__ for h in p._OPENER.handlers]
        self.assertNotIn("HTTPRedirectHandler", handlers)
        self.assertNotIn("FileHandler", handlers)
        self.assertNotIn("FTPHandler", handlers)


class IsJetBrainsMCPServer(unittest.TestCase):
    def test_the_real_server_names_are_accepted(self):
        self.assertTrue(p.is_jetbrains_mcp_server({"name": JETBRAINS_SERVER_NAME}))
        self.assertTrue(
            p.is_jetbrains_mcp_server({"name": ANOTHER_JETBRAINS_SERVER_NAME})
        )

    def test_an_unrelated_server_is_rejected(self):
        self.assertFalse(p.is_jetbrains_mcp_server({"name": SOME_OTHER_SERVER_NAME}))

    def test_a_missing_or_non_string_name_is_rejected(self):
        self.assertFalse(p.is_jetbrains_mcp_server({}))
        self.assertFalse(p.is_jetbrains_mcp_server({"name": None}))
        self.assertFalse(p.is_jetbrains_mcp_server({"name": 7}))


class SSEPayload(unittest.TestCase):
    def test_a_data_line_yields_its_payload(self):
        self.assertEqual(p.sse_payload('data: {"id":1}'), '{"id":1}')

    def test_a_data_line_without_a_space_after_the_colon_yields_its_payload(self):
        self.assertEqual(p.sse_payload("data:/endpoint"), "/endpoint")

    def test_an_event_line_is_not_a_payload(self):
        self.assertIsNone(p.sse_payload("event: message"))

    def test_a_blank_line_is_not_a_payload(self):
        self.assertIsNone(p.sse_payload(""))

    def test_an_empty_data_line_yields_the_empty_string(self):
        self.assertEqual(p.sse_payload("data:"), "")


class Classify(unittest.TestCase):
    def test_the_exact_policy_set_is_ok(self):
        code, extras = p.classify(set(p.POLICY_TOOLS), p.POLICY_TOOLS)
        self.assertEqual(code, p.OK)
        self.assertEqual(extras, [])

    def test_a_subset_of_policy_is_ok(self):
        code, extras = p.classify({A_POLICY_TOOL}, p.POLICY_TOOLS)
        self.assertEqual(code, p.OK)
        self.assertEqual(extras, [])

    def test_an_undocumented_write_tool_is_drift(self):
        exposed = set(p.POLICY_TOOLS) | {A_WRITE_TOOL}
        code, extras = p.classify(exposed, p.POLICY_TOOLS)
        self.assertEqual(code, p.DRIFT)
        self.assertEqual(extras, [A_WRITE_TOOL])

    def test_extras_are_sorted(self):
        exposed = set(p.POLICY_TOOLS) | {ANOTHER_WRITE_TOOL, A_WRITE_TOOL}
        _, extras = p.classify(exposed, p.POLICY_TOOLS)
        self.assertEqual(extras, sorted([A_WRITE_TOOL, ANOTHER_WRITE_TOOL]))

    def test_an_unknown_tool_is_drift_even_though_harmless(self):
        # What JetBrains has not documented cannot be enumerated, so anything
        # unrecognised fails closed.
        code, extras = p.classify({AN_UNDOCUMENTED_READ_TOOL}, p.POLICY_TOOLS)
        self.assertEqual(code, p.DRIFT)
        self.assertEqual(extras, [AN_UNDOCUMENTED_READ_TOOL])

    def test_the_build_tool_coming_back_is_drift(self):
        # Settings Sync can move Exposed Tools state from another machine.
        exposed = set(p.POLICY_TOOLS) | {BUILD_TOOL}
        code, extras = p.classify(exposed, p.POLICY_TOOLS)
        self.assertEqual(code, p.DRIFT)
        self.assertEqual(extras, [BUILD_TOOL])

    def test_an_empty_exposed_set_is_ok(self):
        code, extras = p.classify(set(), p.POLICY_TOOLS)
        self.assertEqual(code, p.OK)
        self.assertEqual(extras, [])


class Describe(unittest.TestCase):
    def test_a_known_dangerous_tool_gets_its_reason(self):
        self.assertIn("writes files", p.describe(A_WRITE_TOOL))

    def test_an_unknown_tool_gets_the_generic_reason(self):
        self.assertEqual(p.describe("some_new_tool"), "not in the policy set")


class PolicySet(unittest.TestCase):
    def test_the_policy_matches_the_documented_roster(self):
        self.assertEqual(set(p.POLICY_TOOLS), DOCUMENTED_POLICY_ROSTER)

    def test_no_policy_tool_is_known_dangerous(self):
        self.assertEqual(set(p.POLICY_TOOLS) & set(p.KNOWN_DANGEROUS), set())

    def test_the_policy_is_not_overridable_from_the_cli(self):
        # A runtime override could widen the set and still print OK, the false
        # green this tool exists to prevent.
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            p.main(["--discover", "--allow", A_WRITE_TOOL])


class PolicyMatchesTheHarnessDocs(unittest.TestCase):
    """POLICY_TOOLS equals the Exposed roster each stack's MCP-integration skill publishes."""

    # tools/claude-dev/tests/<file> -> the repo root is three parents up.
    _ROOT = pathlib.Path(__file__).resolve().parents[3]
    _DOCS = (
        _ROOT
        / "harness/stacks/java-spring-boot/.claude/skills/intellij-idea/intellij-mcp-integration.md",
        _ROOT / "harness/stacks/go/.claude/skills/goland/goland-mcp-integration.md",
    )

    @staticmethod
    def _exposed_tools(md: str) -> set[str]:
        """Parse the backticked tool names from the '### Exposed (…)' table."""
        section = re.search(
            r"### Exposed \([^\)]*\)\s*\n(.*?)(?:\n### |\n## )", md, re.DOTALL
        )
        if not section:
            return set()
        names = set()
        for line in section.group(1).splitlines():
            row = line.strip()
            if not row.startswith("|"):
                continue
            first_col = row.split("|")[1].strip()
            m = re.fullmatch(r"`([a-z_]+)`", first_col)
            if m:
                names.add(m.group(1))
        return names

    def test_each_doc_roster_equals_the_policy(self):
        present = [d for d in self._DOCS if d.exists()]
        if not present:
            self.skipTest("harness docs not present (standalone claude-dev checkout)")
        for doc in present:
            with self.subTest(doc=doc.name):
                exposed = self._exposed_tools(doc.read_text(encoding="utf-8"))
                self.assertEqual(exposed, set(p.POLICY_TOOLS))


if __name__ == "__main__":
    unittest.main()
