#!/usr/bin/env python3
"""Tests for ide_preflight — pure logic plus end-to-end probes of the I/O path.

The pure helpers are unit-tested. The Session/enumerate_tools/check_port path is
tested end-to-end against a loopback stub standing in for a (possibly hostile)
MCP server — no container, no real IDE. That path is where a repointed
~/.claude.json entry lands, so it is exercised against malformed and adversarial
responses, not just a well-behaved one.
"""

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


def run_main_discover(port, *extra):
    """Drive main() in discover mode against a config naming only this port.

    Returns (exit code, stdout, stderr). CLAUDE_CONFIG is patched to a temp
    file, so the test never reads the real ~/.claude.json.
    """
    with tempfile.TemporaryDirectory() as d:
        cfg = pathlib.Path(d) / "claude.json"
        cfg.write_text(
            json.dumps(
                {"mcpServers": {"idea": {"url": f"http://127.0.0.1:{port}/sse"}}}
            )
        )
        out, err = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(p, "CLAUDE_CONFIG", str(cfg)),
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
        ):
            code = p.main(["--discover", "--bridge-ports", "--timeout", "5", *extra])
        return code, out.getvalue(), err.getvalue()


class MockMCPServer:
    """A loopback HTTP/SSE server that plays a scripted MCP role.

    Configured with the serverInfo and tool list to advertise, or with a "mode"
    that misbehaves (malformed result, dribble, non-JetBrains identity). Used to
    drive check_port the way a repointed config entry would.
    """

    def __init__(
        self,
        *,
        server_name="IntelliJ IDEA MCP Server",
        version="2026.1.4",
        tools=("search_symbol",),
        mode="ok",
        project_mode=None,
    ):
        self.server_name = server_name
        self.version = version
        self.tools = list(tools)
        self.mode = mode
        # None | "open" | "not_open" | "null_result" | "empty_result"
        # | "deep_nesting"
        self.project_mode = project_mode
        self.posts = []  # decoded JSON-RPC bodies, so tests can assert the requests sent
        self._sock = socket.socket()
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self.port = self._sock.getsockname()[1]
        self._sock.listen(8)
        self._stop = False
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        while not self._stop:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _chunk(self, body: bytes) -> bytes:
        return hex(len(body))[2:].encode() + b"\r\n" + body + b"\r\n"

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

    def _handle_inner(self, conn):
        req = b""
        while b"\r\n\r\n" not in req:
            part = conn.recv(4096)
            if not part:
                return
            req += part
        if not req.startswith(
            b"GET"
        ):  # POST — capture the body so tests can assert requests
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
            return
        conn.sendall(
            b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n"
            b"Transfer-Encoding: chunked\r\n\r\n"
        )
        if self.mode == "unterminated_blob":
            # One SSE line that never ends: 2 MiB, no newline. Only the byte cap
            # bounds this — a reader that buffers until newline never returns.
            conn.sendall(self._chunk(b"data: " + b"a" * (2 * 1024 * 1024)))
            time.sleep(0.3)
            return
        if self.mode == "trickle_no_newline":
            # A newline-free line fed a few bytes at a time: each recv is fast,
            # the line never completes — only the wall-clock deadline ends this.
            conn.sendall(self._chunk(b"data: "))
            while not self._stop:
                try:
                    conn.sendall(self._chunk(b"aaaa"))
                except OSError:
                    return
                time.sleep(0.05)
            return
        conn.sendall(
            self._chunk(b"event: endpoint\r\ndata: /message?sessionId=x\r\n\r\n")
        )
        if self.mode == "dribble":
            # Lines that never satisfy the reader, each recv fast — only a
            # wall-clock deadline ends this.
            while not self._stop:
                conn.sendall(self._chunk(b"event: ping\r\ndata: keep-alive\r\n\r\n"))
                time.sleep(0.2)
            return
        if self.mode == "ping_before_response":
            # A server-initiated request whose id collides with the client's
            # pending request id. It is not a response and must be skipped.
            conn.sendall(self._sse({"jsonrpc": "2.0", "id": 1, "method": "ping"}))
        if self.mode == "null_result_init":
            init = {"jsonrpc": "2.0", "id": 1, "result": None}
        else:
            init = {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "serverInfo": {"name": self.server_name, "version": self.version},
                },
            }
        conn.sendall(self._sse(init))
        listed = None
        if self.mode == "null_tools":
            listed = {"jsonrpc": "2.0", "id": 2, "result": {"tools": None}}
        elif self.mode == "list_result_tools":
            listed = {"jsonrpc": "2.0", "id": 2, "result": []}
        elif self.mode == "scalar_tool":
            listed = {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"tools": [42, {"name": "search_symbol"}]},
            }
        elif self.mode == "paginated":
            # Policy tools on page 1, the dangerous tool on page 2: classifying
            # page 1 alone would report OK.
            conn.sendall(
                self._sse(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "result": {
                            "tools": [{"name": n} for n in self.tools],
                            "nextCursor": "page2",
                        },
                    }
                )
            )
            conn.sendall(
                self._sse(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "result": {"tools": [{"name": "apply_patch"}]},
                    }
                )
            )
        elif self.mode == "cursor_loop":
            # nextCursor forever — the client must give up loudly, never trust
            # the partial list it has.
            for i in range(2, 40):
                conn.sendall(
                    self._sse(
                        {
                            "jsonrpc": "2.0",
                            "id": i,
                            "result": {"tools": [], "nextCursor": f"p{i}"},
                        }
                    )
                )
        elif self.mode in ("ok", "ansi", "ping_before_response"):
            listed = {
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"tools": [{"name": n} for n in self.tools]},
            }
        if listed is not None:
            conn.sendall(self._sse(listed))
        # The project probe (id 100) follows the tool listing on the same stream.
        # Sent proactively like everything else: the client reads until its id
        # matches, so an unconsumed probe response is harmless.
        if self.project_mode == "open":
            conn.sendall(
                self._sse(
                    {
                        "jsonrpc": "2.0",
                        "id": 100,
                        "result": {
                            "content": [{"type": "text", "text": '{"modules":[]}'}]
                        },
                    }
                )
            )
        elif self.project_mode == "not_open":
            # The real IDE error shape, roster tail included — the client must
            # take the verdict from isError alone and never parse this text.
            text = (
                "`projectPath`=`/pod/work` doesn't correspond to any open project.\n"
                ' Currently open projects: {"projects":[{"path":"/Users/x/other"}]}'
            )
            conn.sendall(
                self._sse(
                    {
                        "jsonrpc": "2.0",
                        "id": 100,
                        "result": {
                            "isError": True,
                            "content": [{"type": "text", "text": text}],
                        },
                    }
                )
            )
        elif self.project_mode == "null_result":
            conn.sendall(self._sse({"jsonrpc": "2.0", "id": 100, "result": None}))
        elif self.project_mode == "empty_result":
            # No isError, but no content either — not positive evidence of "open".
            conn.sendall(self._sse({"jsonrpc": "2.0", "id": 100, "result": {}}))
        elif self.project_mode == "deep_nesting":
            # Deeply nested JSON in the probe response: json.loads raises
            # RecursionError, which must degrade the probe, not the verdict.
            conn.sendall(
                self._chunk(b'data: {"id":100,"result":' + b"[" * 100_000 + b"\r\n\r\n")
            )
        # Hold the stream open briefly so the client reads before close.
        time.sleep(0.3)

    def close(self):
        self._stop = True
        try:
            self._sock.close()
        except OSError:
            pass


class TestCheckPortEndToEnd(unittest.TestCase):
    """check_port must survive a hostile server and always return a clean record."""

    def _check(self, server, **kw):
        return p.check_port(
            "127.0.0.1", server.port, p.POLICY_TOOLS, kw.get("timeout", 5.0)
        )

    def test_healthy_server_is_ok(self):
        s = MockMCPServer(tools=["search_symbol", "get_file_problems"])
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["code"], p.OK)
        self.assertEqual(r["server"], "IntelliJ IDEA MCP Server")

    def test_drift_is_reported(self):
        s = MockMCPServer(tools=["search_symbol", "apply_patch"])
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["code"], p.DRIFT)
        self.assertIn("apply_patch", r["extras"])

    def test_drift_report_names_the_target_configuration(self):
        # Actionable, not just diagnostic: the operator opening Exposed Tools
        # must see what the checkboxes SHOULD look like, not only what to remove.
        s = MockMCPServer(tools=["search_symbol", "apply_patch"])
        try:
            r = self._check(s)
        finally:
            s.close()
        buf = io.StringIO()
        p._report(r, "127.0.0.1", stream=buf)
        report = buf.getvalue()
        self.assertIn("Settings -> Tools -> MCP Server -> Exposed Tools", report)
        self.assertIn("Keep exactly these enabled", report)
        for tool in sorted(p.POLICY_TOOLS):
            self.assertIn(f"[x] {tool}", report)

    def test_non_jetbrains_identity_is_refused(self):
        s = MockMCPServer(server_name="totally-not-jetbrains")
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["code"], p.PROTOCOL)
        self.assertNotEqual(r["code"], p.DRIFT)  # must not collide with the drift code

    def test_null_result_does_not_raise(self):
        s = MockMCPServer(mode="null_result_init")
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(
            r["code"], p.PROTOCOL
        )  # clean, not an AttributeError traceback

    def test_null_tools_array_does_not_raise(self):
        s = MockMCPServer(mode="null_tools")
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["code"], p.PROTOCOL)

    def test_result_is_a_list_does_not_raise(self):
        s = MockMCPServer(mode="list_result_tools")
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["code"], p.PROTOCOL)

    def test_non_dict_tool_element_is_skipped_not_crashed(self):
        # A scalar in the tools array must not throw; the valid entry still counts.
        s = MockMCPServer(mode="scalar_tool")
        try:
            r = self._check(s)
        finally:
            s.close()
        # search_symbol is the only valid tool -> subset of policy -> OK
        self.assertEqual(r["code"], p.OK)
        self.assertEqual(r["exposed"], ["search_symbol"])

    def test_dribbling_server_hits_the_wall_clock_deadline(self):
        s = MockMCPServer(mode="dribble")
        try:
            start = time.monotonic()
            r = p.check_port("127.0.0.1", s.port, p.POLICY_TOOLS, 2.0)
            elapsed = time.monotonic() - start
        finally:
            s.close()
        self.assertEqual(r["code"], p.PROTOCOL)  # bounded, not a hang
        self.assertLess(elapsed, 10.0, "deadline did not bound a dribbling server")

    def test_newline_free_blob_is_bounded_by_the_byte_cap(self):
        # A single SSE line that never ends must hit the byte cap, not buffer
        # without bound: readline()-style reading would sit here forever.
        s = MockMCPServer(mode="unterminated_blob")
        try:
            start = time.monotonic()
            r = p.check_port("127.0.0.1", s.port, p.POLICY_TOOLS, 5.0)
            elapsed = time.monotonic() - start
        finally:
            s.close()
        self.assertEqual(r["code"], p.PROTOCOL)
        self.assertLess(elapsed, 10.0, "byte cap did not bound a newline-free blob")

    def test_newline_free_trickle_hits_the_wall_clock_deadline(self):
        # Bytes keep arriving so no socket timeout fires, and the line never
        # completes so no per-line check runs — the deadline must still bound it.
        s = MockMCPServer(mode="trickle_no_newline")
        try:
            start = time.monotonic()
            r = p.check_port("127.0.0.1", s.port, p.POLICY_TOOLS, 1.5)
            elapsed = time.monotonic() - start
        finally:
            s.close()
        self.assertEqual(r["code"], p.PROTOCOL)
        self.assertLess(elapsed, 8.0, "deadline did not bound a newline-free trickle")

    def test_paginated_tools_list_is_fully_enumerated(self):
        # apply_patch hides on page 2; reading only page 1 would report OK.
        s = MockMCPServer(mode="paginated", tools=["search_symbol"])
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["code"], p.DRIFT)
        self.assertIn("apply_patch", r["extras"])
        self.assertIn("search_symbol", r["exposed"])

    def test_endless_cursor_fails_loud_never_trusts_a_partial_list(self):
        s = MockMCPServer(mode="cursor_loop")
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["code"], p.PROTOCOL)

    def test_server_initiated_request_with_colliding_id_is_skipped(self):
        # {"id": 1, "method": "ping"} is a request in the server's id space, not
        # the client's response — matching it would fail a healthy handshake.
        s = MockMCPServer(mode="ping_before_response", tools=["search_symbol"])
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["code"], p.OK)

    def test_ansi_in_tool_name_is_drift_and_report_is_sanitized(self):
        # A tool name with an escape must NOT match a policy name (stays drift),
        # and _report must strip the escape before printing.
        s = MockMCPServer(tools=["search_symbol\x1b]52;c;whatever\x07"])
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["code"], p.DRIFT)
        buf = io.StringIO()
        p._report(r, "127.0.0.1", stream=buf)
        self.assertNotIn("\x1b", buf.getvalue())
        self.assertNotIn("\x07", buf.getvalue())

    def test_unreachable_port_is_clean_and_fast(self):
        # Bind then close to get a definitely-dead port. No IDE running is the
        # everyday case and the preflight runs on every pod launch, so deciding
        # "unreachable" must cost near-nothing, never a handshake timeout.
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        dead = s.getsockname()[1]
        s.close()
        start = time.monotonic()
        r = p.check_port("127.0.0.1", dead, p.POLICY_TOOLS, 30.0, connect_timeout=1.0)
        elapsed = time.monotonic() - start
        self.assertEqual(r["code"], p.UNREACHABLE)
        self.assertLess(
            elapsed, 2.0, "a dead port must never draw on the handshake budget"
        )


class TestBridgePortsFlagContract(unittest.TestCase):
    """--bridge-ports must hold in every mode: `port<TAB>label` lines on stdout,
    report elsewhere. The label lets claude-dev name WHAT it bridges."""

    def test_discover_mode_prints_port_and_label_on_stdout_and_report_on_stderr(self):
        s = MockMCPServer(tools=["search_symbol"])
        try:
            code, out, err = run_main_discover(s.port)
        finally:
            s.close()
        self.assertEqual(code, p.OK)
        port, label = out.rstrip("\n").split("\t")
        self.assertEqual(port, str(s.port))
        self.assertEqual(label, "IntelliJ IDEA MCP Server 2026.1.4")
        # The healthy every-launch report is one compact line, identity first.
        report = err.strip().splitlines()
        self.assertEqual(len(report), 1)
        self.assertIn("IntelliJ IDEA MCP Server 2026.1.4", report[0])
        self.assertIn("OK: exposed set within policy", report[0])

    def test_drifting_server_gets_no_bridge_port(self):
        s = MockMCPServer(tools=["search_symbol", "apply_patch"])
        try:
            code, out, err = run_main_discover(s.port)
        finally:
            s.close()
        self.assertEqual(code, p.DRIFT)
        self.assertEqual(out, "")
        self.assertIn("DRIFT", err)

    def test_bare_invocation_is_a_usage_error(self):
        # Discovery must be asked for explicitly: a bare run is a loud usage
        # error, never a silent probe of the real ~/.claude.json.
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            p.main([])


class TestProjectProbe(unittest.TestCase):
    """The --project check: the verdict is the IDE's own resolution, probed with a
    read-only policy tool on the same session as the policy check."""

    def _check(self, server, project="/pod/work"):
        return p.check_port(
            "127.0.0.1", server.port, p.POLICY_TOOLS, 5.0, project=project
        )

    def test_open_project_is_verified(self):
        s = MockMCPServer(
            tools=["search_symbol", "get_project_modules"], project_mode="open"
        )
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["code"], p.OK)
        self.assertIs(r["project_open"], True)
        self.assertEqual(r["project"], "/pod/work")
        # The verdict must come from the request the docs promise: one
        # tools/call naming the probe tool, carrying the path as projectPath.
        calls = [
            m
            for m in s.posts
            if isinstance(m, dict) and m.get("method") == "tools/call"
        ]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["params"]["name"], "get_project_modules")
        self.assertEqual(calls[0]["params"]["arguments"], {"projectPath": "/pod/work"})

    def test_not_open_is_false(self):
        s = MockMCPServer(tools=["get_project_modules"], project_mode="not_open")
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertIs(r["project_open"], False)

    def test_fallback_probe_tool_is_used(self):
        # get_project_modules absent; get_project_dependencies must carry the probe.
        s = MockMCPServer(tools=["get_project_dependencies"], project_mode="open")
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertIs(r["project_open"], True)
        calls = [
            m
            for m in s.posts
            if isinstance(m, dict) and m.get("method") == "tools/call"
        ]
        self.assertEqual(
            [c["params"]["name"] for c in calls], ["get_project_dependencies"]
        )

    def test_no_probe_tool_is_unverifiable_not_open(self):
        # Policy-conforming but neither probe tool exposed: cannot verify, and
        # unverifiable must never count as open (bridge only what is verified).
        s = MockMCPServer(tools=["search_symbol"], project_mode="open")
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["code"], p.OK)
        self.assertIsNone(r["project_open"])
        self.assertIn("no probe tool exposed", r["project_unverifiable"])
        # No tool call may be attempted without a probe tool to carry it.
        self.assertEqual(
            [
                m
                for m in s.posts
                if isinstance(m, dict) and m.get("method") == "tools/call"
            ],
            [],
        )

    def test_null_probe_result_is_unverifiable(self):
        s = MockMCPServer(tools=["get_project_modules"], project_mode="null_result")
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertIsNone(r["project_open"])
        # The tool WAS exposed — the reason must blame the response, not the checkboxes.
        self.assertIn("response", r["project_unverifiable"])

    def test_empty_dict_result_is_unverifiable_not_open(self):
        # isError absent is not enough: "open" needs the positive evidence of a
        # content array, or a flaky {} would earn a bridge.
        s = MockMCPServer(tools=["get_project_modules"], project_mode="empty_result")
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertIsNone(r["project_open"])

    def test_probe_stall_degrades_to_unverifiable_never_protocol_error(self):
        # A conforming server that never answers the probe (an indexing IDE):
        # the policy verdict and exit code must survive; only the probe degrades.
        s = MockMCPServer(tools=["get_project_modules"], project_mode=None)
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["code"], p.OK)
        self.assertIsNone(r["project_open"])
        self.assertIn("probe call failed", r["project_unverifiable"])

    def test_deeply_nested_probe_response_degrades_to_unverifiable(self):
        # RecursionError out of the probe response's json.loads must degrade
        # like any probe failure — never flip a completed OK to PROTOCOL.
        s = MockMCPServer(tools=["get_project_modules"], project_mode="deep_nesting")
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["code"], p.OK)
        self.assertIsNone(r["project_open"])

    def test_drifting_server_is_never_probed(self):
        # A drifting server cannot earn a bridge line, so it gets no extra call.
        s = MockMCPServer(
            tools=["get_project_modules", "apply_patch"], project_mode="open"
        )
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["code"], p.DRIFT)
        self.assertNotIn("project_open", r)
        self.assertEqual(
            [
                m
                for m in s.posts
                if isinstance(m, dict) and m.get("method") == "tools/call"
            ],
            [],
        )

    def test_without_project_no_fields_are_added(self):
        s = MockMCPServer(tools=["get_project_modules"], project_mode="open")
        try:
            r = p.check_port("127.0.0.1", s.port, p.POLICY_TOOLS, 5.0)
        finally:
            s.close()
        self.assertNotIn("project_open", r)
        self.assertNotIn("project", r)

    def test_project_verdict_never_changes_the_exit_code(self):
        # Not-open is claude-dev's decision to act on, not drift — OK stays OK.
        s = MockMCPServer(tools=["get_project_modules"], project_mode="not_open")
        try:
            r = self._check(s)
        finally:
            s.close()
        self.assertEqual(r["code"], p.OK)

    def test_report_states_the_verdict(self):
        s = MockMCPServer(tools=["get_project_modules"], project_mode="not_open")
        try:
            r = self._check(s)
        finally:
            s.close()
        buf = io.StringIO()
        p._report(r, "127.0.0.1", stream=buf)
        self.assertIn("NOT open", buf.getvalue())


class TestBridgeGateOnProject(unittest.TestCase):
    """With --project, a bridge line means 'verified open' — nothing less."""

    def _main(self, server):
        return run_main_discover(server.port, "--project", "/pod/work")

    def test_open_project_emits_the_bridge_line(self):
        s = MockMCPServer(tools=["get_project_modules"], project_mode="open")
        try:
            code, out, err = self._main(s)
        finally:
            s.close()
        self.assertEqual(code, p.OK)
        self.assertEqual(out.split("\t")[0], str(s.port))
        self.assertIn("project /pod/work is open", err)

    def test_not_open_emits_no_bridge_line(self):
        s = MockMCPServer(tools=["get_project_modules"], project_mode="not_open")
        try:
            code, out, err = self._main(s)
        finally:
            s.close()
        self.assertEqual(code, p.OK)  # exit code is policy's, not the project's
        self.assertEqual(out, "")
        self.assertIn("NOT open", err)

    def test_unverifiable_emits_no_bridge_line(self):
        s = MockMCPServer(tools=["search_symbol"], project_mode="open")
        try:
            code, out, err = self._main(s)
        finally:
            s.close()
        self.assertEqual(code, p.OK)
        self.assertEqual(out, "")
        self.assertIn("unverifiable", err)

    def test_without_project_the_old_contract_holds(self):
        s = MockMCPServer(tools=["get_project_modules"])
        try:
            code, out, _ = run_main_discover(s.port)
        finally:
            s.close()
        self.assertEqual(code, p.OK)
        self.assertEqual(out.split("\t")[0], str(s.port))


class TestSanitize(unittest.TestCase):
    def test_strips_ansi_escape(self):
        self.assertEqual(p.sanitize("a\x1b[31mb"), "a[31mb")

    def test_strips_osc_and_bell(self):
        self.assertEqual(p.sanitize("x\x1b]52;c;zzz\x07y"), "x]52;c;zzzy")

    def test_strips_c1_controls(self):
        self.assertEqual(p.sanitize("a\x9bb\x85c"), "abc")

    def test_keeps_tab_and_printable_unicode(self):
        self.assertEqual(p.sanitize("a\tb→c"), "a\tb→c")

    def test_drops_del(self):
        self.assertEqual(p.sanitize("a\x7fb"), "ab")

    def test_strips_bidi_overrides_and_isolates(self):
        # U+202E (RLO) and the U+2066-2069 isolates reorder rendered text — a
        # dangerous tool name could display as a benign one in the DRIFT report.
        self.assertEqual(p.sanitize("a\u202eb\u2066c\u2069d"), "abcd")

    def test_strips_zero_width_and_bom(self):
        self.assertEqual(p.sanitize("a\u200bb\u200dc\ufeffd"), "abcd")

    def test_strips_line_and_paragraph_separators(self):
        self.assertEqual(p.sanitize("a\u2028b\u2029c"), "abc")


class TestLoopbackSSEPort(unittest.TestCase):
    def test_extracts_port(self):
        self.assertEqual(p.loopback_sse_port("http://127.0.0.1:64342/sse"), 64342)

    def test_accepts_localhost_and_ipv6_loopback(self):
        self.assertEqual(p.loopback_sse_port("http://localhost:64343/sse"), 64343)
        self.assertEqual(p.loopback_sse_port("http://[::1]:64343/sse"), 64343)

    def test_any_port_is_accepted_no_range_check(self):
        # IntelliJ's mcpServerPort is user-settable and observed reality already
        # diverges from the source's offset scheme — a range check would reject
        # working configurations. Only loopback and non-privileged are enforced.
        self.assertEqual(p.loopback_sse_port("http://127.0.0.1:64422/sse"), 64422)
        self.assertEqual(p.loopback_sse_port("http://127.0.0.1:12345/sse"), 12345)

    def test_rejects_non_loopback(self):
        # A rewritten config must not send the bridge off-box.
        self.assertIsNone(p.loopback_sse_port("http://192.168.5.2:64342/sse"))
        self.assertIsNone(p.loopback_sse_port("http://evil.example:64342/sse"))

    def test_rejects_privileged_port(self):
        self.assertIsNone(p.loopback_sse_port("http://127.0.0.1:22/sse"))
        self.assertIsNone(p.loopback_sse_port("http://127.0.0.1:80/sse"))

    def test_rejects_non_http_scheme(self):
        self.assertIsNone(p.loopback_sse_port("https://127.0.0.1:64342/sse"))
        self.assertIsNone(p.loopback_sse_port("file:///etc/passwd"))

    def test_rejects_missing_port(self):
        self.assertIsNone(p.loopback_sse_port("http://127.0.0.1/sse"))

    def test_rejects_garbage(self):
        self.assertIsNone(p.loopback_sse_port("not a url"))


class TestDiscoverServers(unittest.TestCase):
    def test_finds_both_ides_at_their_assigned_ports(self):
        cfg = {
            "mcpServers": {
                "idea": {"type": "sse", "url": "http://127.0.0.1:64342/sse"},
                "goland": {"type": "sse", "url": "http://127.0.0.1:64343/sse"},
            }
        }
        self.assertEqual(p.discover_servers(cfg), [("idea", 64342), ("goland", 64343)])

    def test_reads_a_nondefault_port(self):
        # The whole point: the port is IDE-assigned, never assumed.
        cfg = {"mcpServers": {"idea": {"url": "http://127.0.0.1:64999/sse"}}}
        self.assertEqual(p.discover_servers(cfg), [("idea", 64999)])

    def test_ignores_unrelated_mcp_servers(self):
        cfg = {
            "mcpServers": {
                "idea": {"url": "http://127.0.0.1:64342/sse"},
                "some-other-local-server": {"url": "http://127.0.0.1:5432/sse"},
            }
        }
        self.assertEqual(p.discover_servers(cfg), [("idea", 64342)])

    def test_ignores_an_entry_repointed_off_loopback(self):
        cfg = {"mcpServers": {"idea": {"url": "http://192.168.5.2:64342/sse"}}}
        self.assertEqual(p.discover_servers(cfg), [])

    def test_empty_and_malformed_configs(self):
        self.assertEqual(p.discover_servers({}), [])
        self.assertEqual(p.discover_servers({"mcpServers": None}), [])
        self.assertEqual(p.discover_servers({"mcpServers": {"idea": "nonsense"}}), [])
        self.assertEqual(p.discover_servers({"mcpServers": {"idea": {}}}), [])
        self.assertEqual(p.discover_servers({"mcpServers": {"idea": {"url": 42}}}), [])

    def test_finds_a_project_scoped_server(self):
        # `claude mcp add` defaults to local scope, which lands under
        # projects.<path>.mcpServers — the exposure is the same, so the check
        # must find it there too.
        cfg = {
            "projects": {
                "/Users/x/proj": {
                    "mcpServers": {"goland": {"url": "http://127.0.0.1:64343/sse"}}
                }
            }
        }
        self.assertEqual(p.discover_servers(cfg), [("goland", 64343)])

    def test_dedupes_the_same_server_across_scopes(self):
        cfg = {
            "mcpServers": {"idea": {"url": "http://127.0.0.1:64342/sse"}},
            "projects": {
                "/a": {"mcpServers": {"idea": {"url": "http://127.0.0.1:64342/sse"}}},
                "/b": {"mcpServers": {"idea": {"url": "http://127.0.0.1:60000/sse"}}},
            },
        }
        # Same (name, port) collapses; a different port is a distinct server.
        self.assertEqual(p.discover_servers(cfg), [("idea", 64342), ("idea", 60000)])

    def test_malformed_projects_scope_is_ignored(self):
        cfg = {"projects": {"/a": "nonsense", "/b": {"mcpServers": None}}}
        self.assertEqual(p.discover_servers(cfg), [])

    def test_two_names_on_one_port_count_once(self):
        # Two IDEs cannot share a port, so stale `idea` + `goland` entries on
        # the same port are one server. Counting it twice would make the
        # exactly-one bridge rule refuse a single open IDE as "2 qualify".
        cfg = {
            "mcpServers": {
                "idea": {"url": "http://127.0.0.1:64342/sse"},
                "goland": {"url": "http://127.0.0.1:64342/sse"},
            }
        }
        self.assertEqual(p.discover_servers(cfg), [("idea", 64342)])


class TestLoadClaudeConfig(unittest.TestCase):
    def test_reads_a_config(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "c.json"
            f.write_text(
                json.dumps(
                    {"mcpServers": {"idea": {"url": "http://127.0.0.1:1234/sse"}}}
                )
            )
            self.assertEqual(
                p.discover_servers(p.load_claude_config(f)), [("idea", 1234)]
            )

    def test_missing_file_is_not_an_error(self):
        self.assertEqual(p.load_claude_config(pathlib.Path("/nonexistent/c.json")), {})

    def test_malformed_json_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "c.json"
            f.write_text("{not json")
            self.assertEqual(p.load_claude_config(f), {})

    def test_deeply_nested_json_is_not_an_error(self):
        # The file is pod-writable and parsed on every invocation: deep
        # nesting's RecursionError must read as "no IDE configured", not a crash.
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "c.json"
            f.write_text("[" * 1_000_000)
            self.assertEqual(p.load_claude_config(f), {})

    def test_invalid_utf8_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "c.json"
            f.write_bytes(b'\xff\xfe{"a":1}')
            self.assertEqual(p.load_claude_config(f), {})


class TestRestrictedOpener(unittest.TestCase):
    """The opener must be unable to speak anything but plain HTTP.

    ~/.claude.json is writable by the pod, so a URL reaching the opener is not
    fully trusted. These assert the structural guarantee, not the scheme check —
    swapping _OPENER back to urllib.request.urlopen would fail them.
    """

    def test_cannot_open_file_scheme(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("secret")
            path = fh.name
        with self.assertRaises(urllib.error.URLError):
            p._OPENER.open(f"file://{path}", timeout=2)

    def test_cannot_open_ftp_scheme(self):
        with self.assertRaises(urllib.error.URLError):
            p._OPENER.open("ftp://127.0.0.1/x", timeout=2)

    def test_cannot_open_https_scheme(self):
        with self.assertRaises(urllib.error.URLError):
            p._OPENER.open("https://127.0.0.1/x", timeout=2)

    def test_has_no_redirect_handler(self):
        # A 3xx must not walk the client off loopback after the scheme check.
        handlers = [type(h).__name__ for h in p._OPENER.handlers]
        self.assertNotIn("HTTPRedirectHandler", handlers)
        self.assertNotIn("FileHandler", handlers)
        self.assertNotIn("FTPHandler", handlers)


class TestIsJetBrainsMCPServer(unittest.TestCase):
    def test_accepts_the_real_server_names(self):
        self.assertTrue(p.is_jetbrains_mcp_server({"name": "IntelliJ IDEA MCP Server"}))
        self.assertTrue(p.is_jetbrains_mcp_server({"name": "GoLand MCP Server"}))

    def test_rejects_an_unrelated_server(self):
        # The realistic failure: a rewritten config points the bridge at something
        # else on host loopback.
        self.assertFalse(p.is_jetbrains_mcp_server({"name": "some-other-tool"}))

    def test_rejects_missing_or_non_string_name(self):
        self.assertFalse(p.is_jetbrains_mcp_server({}))
        self.assertFalse(p.is_jetbrains_mcp_server({"name": None}))
        self.assertFalse(p.is_jetbrains_mcp_server({"name": 7}))


class TestSSEPayload(unittest.TestCase):
    def test_extracts_data_payload(self):
        self.assertEqual(p.sse_payload('data: {"id":1}'), '{"id":1}')

    def test_handles_no_space_after_colon(self):
        self.assertEqual(p.sse_payload("data:/endpoint"), "/endpoint")

    def test_event_line_is_not_a_payload(self):
        self.assertIsNone(p.sse_payload("event: message"))

    def test_blank_line_is_not_a_payload(self):
        self.assertIsNone(p.sse_payload(""))

    def test_empty_data_line_yields_empty_string(self):
        self.assertEqual(p.sse_payload("data:"), "")


class TestClassify(unittest.TestCase):
    def test_exact_policy_set_is_ok(self):
        code, extras = p.classify(set(p.POLICY_TOOLS), p.POLICY_TOOLS)
        self.assertEqual(code, p.OK)
        self.assertEqual(extras, [])

    def test_subset_is_ok(self):
        # GoLand exposing fewer tools than policy is not drift.
        code, extras = p.classify({"search_symbol"}, p.POLICY_TOOLS)
        self.assertEqual(code, p.OK)
        self.assertEqual(extras, [])

    def test_undocumented_write_tool_is_drift(self):
        # The real case: IDEA 2026.1.4 ships apply_patch enabled, undocumented.
        exposed = set(p.POLICY_TOOLS) | {"apply_patch"}
        code, extras = p.classify(exposed, p.POLICY_TOOLS)
        self.assertEqual(code, p.DRIFT)
        self.assertEqual(extras, ["apply_patch"])

    def test_extras_are_sorted(self):
        exposed = set(p.POLICY_TOOLS) | {"execute_tool", "apply_patch"}
        _, extras = p.classify(exposed, p.POLICY_TOOLS)
        self.assertEqual(extras, ["apply_patch", "execute_tool"])

    def test_unknown_tool_is_drift_even_though_harmless(self):
        # Strict subset: what JetBrains has not documented cannot be
        # enumerated, so anything unrecognised fails closed.
        code, extras = p.classify({"get_all_open_file_paths"}, p.POLICY_TOOLS)
        self.assertEqual(code, p.DRIFT)
        self.assertEqual(extras, ["get_all_open_file_paths"])

    def test_build_project_coming_back_is_drift(self):
        # It was removed from Exposed Tools deliberately. Settings Sync can move
        # that state from another machine, so the check must catch its return.
        exposed = set(p.POLICY_TOOLS) | {"build_project"}
        code, extras = p.classify(exposed, p.POLICY_TOOLS)
        self.assertEqual(code, p.DRIFT)
        self.assertEqual(extras, ["build_project"])

    def test_empty_exposed_is_ok(self):
        code, extras = p.classify(set(), p.POLICY_TOOLS)
        self.assertEqual(code, p.OK)
        self.assertEqual(extras, [])


class TestDescribe(unittest.TestCase):
    def test_known_dangerous_tool_gets_a_reason(self):
        self.assertIn("writes files", p.describe("apply_patch"))

    def test_unknown_tool_gets_the_generic_reason(self):
        self.assertEqual(p.describe("some_new_tool"), "not in the policy set")


class TestPolicySet(unittest.TestCase):
    def test_policy_matches_the_documented_five(self):
        # Guards against a silent edit here drifting from the skill docs.
        self.assertEqual(
            set(p.POLICY_TOOLS),
            {
                "get_file_problems",
                "get_project_dependencies",
                "get_project_modules",
                "get_symbol_info",
                "search_symbol",
            },
        )

    def test_apply_patch_is_not_policy(self):
        self.assertNotIn("apply_patch", p.POLICY_TOOLS)

    def test_no_policy_tool_is_known_dangerous(self):
        # The invariant the docs should state: no exposed tool writes or executes.
        # This is the machine-checked version of that claim.
        self.assertEqual(set(p.POLICY_TOOLS) & set(p.KNOWN_DANGEROUS), set())

    def test_policy_is_not_overridable_from_the_cli(self):
        # Deliberate: a runtime override could widen the set and still print OK
        # — the false green this tool exists to prevent. Policy changes are code
        # changes, where the harness-docs coupling test sees them.
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            p.main(["--discover", "--allow", "apply_patch"])


class TestPolicyMatchesTheHarnessDocs(unittest.TestCase):
    """Couple POLICY_TOOLS to the "Exposed (five)" roster in the harness docs.

    The ADR's thesis is verify-don't-assert; a third hand-maintained copy of the
    five would betray it. This reads the roster the integration docs publish and
    asserts POLICY_TOOLS equals it. Skips when the harness tree is absent —
    claude-dev ships standalone, so the docs are only present in the repo.
    """

    # tools/claude-dev/tests/test_ide_preflight.py -> repo root is three
    # parents up.
    _ROOT = pathlib.Path(__file__).resolve().parents[3]
    _DOCS = [
        _ROOT
        / "harness/stacks/java-spring-boot/.claude/skills/intellij-idea/intellij-mcp-integration.md",
        _ROOT / "harness/stacks/go/.claude/skills/goland/goland-mcp-integration.md",
    ]

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

    def test_each_doc_roster_equals_policy(self):
        present = [d for d in self._DOCS if d.exists()]
        if not present:
            self.skipTest("harness docs not present (standalone claude-dev checkout)")
        for doc in present:
            with self.subTest(doc=doc.name):
                exposed = self._exposed_tools(doc.read_text(encoding="utf-8"))
                self.assertEqual(
                    exposed,
                    set(p.POLICY_TOOLS),
                    f"{doc.name} 'Exposed' roster {sorted(exposed)} != POLICY_TOOLS {sorted(p.POLICY_TOOLS)}",
                )


if __name__ == "__main__":
    unittest.main()
