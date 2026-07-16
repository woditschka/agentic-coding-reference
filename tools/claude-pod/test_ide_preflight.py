#!/usr/bin/env python3
"""Tests for ide_preflight — pure logic plus end-to-end probes of the I/O path.

The pure helpers are unit-tested. The Session/enumerate_tools/check_port path is
tested end-to-end against a loopback stub standing in for a (possibly hostile)
MCP server — no container, no real IDE. That path is where a repointed
~/.claude.json entry lands, so it is exercised against malformed and adversarial
responses, not just a well-behaved one.
"""

import json
import pathlib
import re
import socket
import tempfile
import threading
import time
import unittest
import urllib.error

import ide_preflight as p


class MockMCPServer:
    """A loopback HTTP/SSE server that plays a scripted MCP role.

    Configured with the serverInfo and tool list to advertise, or with a "mode"
    that misbehaves (malformed result, dribble, non-JetBrains identity). Used to
    drive check_port the way a repointed config entry would.
    """

    def __init__(self, *, server_name="IntelliJ IDEA MCP Server", version="2026.1.4",
                 tools=("search_symbol",), mode="ok"):
        self.server_name = server_name
        self.version = version
        self.tools = list(tools)
        self.mode = mode
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
        return self._chunk(b"event: message\r\ndata: " + json.dumps(obj).encode() + b"\r\n\r\n")

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
        if not req.startswith(b"GET"):  # POST
            conn.sendall(b"HTTP/1.1 202 Accepted\r\nContent-Length: 8\r\n\r\nAccepted")
            return
        conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n"
                     b"Transfer-Encoding: chunked\r\n\r\n")
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
        conn.sendall(self._chunk(b"event: endpoint\r\ndata: /message?sessionId=x\r\n\r\n"))
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
            init = {"jsonrpc": "2.0", "id": 1,
                    "result": {"protocolVersion": "2024-11-05", "capabilities": {},
                               "serverInfo": {"name": self.server_name, "version": self.version}}}
        conn.sendall(self._sse(init))
        listed = None
        if self.mode == "null_tools":
            listed = {"jsonrpc": "2.0", "id": 2, "result": {"tools": None}}
        elif self.mode == "list_result_tools":
            listed = {"jsonrpc": "2.0", "id": 2, "result": []}
        elif self.mode == "scalar_tool":
            listed = {"jsonrpc": "2.0", "id": 2, "result": {"tools": [42, {"name": "search_symbol"}]}}
        elif self.mode == "paginated":
            # Policy tools on page 1, the dangerous tool on page 2: classifying
            # page 1 alone would report OK.
            conn.sendall(self._sse({"jsonrpc": "2.0", "id": 2,
                                    "result": {"tools": [{"name": n} for n in self.tools],
                                               "nextCursor": "page2"}}))
            conn.sendall(self._sse({"jsonrpc": "2.0", "id": 3,
                                    "result": {"tools": [{"name": "apply_patch"}]}}))
        elif self.mode == "cursor_loop":
            # nextCursor forever — the client must give up loudly, never trust
            # the partial list it has.
            for i in range(2, 40):
                conn.sendall(self._sse({"jsonrpc": "2.0", "id": i,
                                        "result": {"tools": [], "nextCursor": f"p{i}"}}))
        elif self.mode in ("ok", "ansi", "ping_before_response"):
            listed = {"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": n} for n in self.tools]}}
        if listed is not None:
            conn.sendall(self._sse(listed))
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
        return p.check_port("127.0.0.1", server.port, p.POLICY_TOOLS, kw.get("timeout", 5.0))

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
        import io
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
        self.assertEqual(r["code"], p.PROTOCOL)  # clean, not an AttributeError traceback

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
        # the response to ours — matching it would fail a healthy handshake.
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
        import io
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
        self.assertLess(elapsed, 2.0, "a dead port must never draw on the handshake budget")


class TestRelayPortsFlagContract(unittest.TestCase):
    """--relay-ports must hold in every mode: `port<TAB>label` lines on stdout,
    report elsewhere. The label lets claude-pod name WHAT it bridges."""

    def test_port_mode_prints_port_and_label_on_stdout_and_report_on_stderr(self):
        import contextlib
        import io
        s = MockMCPServer(tools=["search_symbol"])
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = p.main(["--port", str(s.port), "--relay-ports", "--timeout", "5"])
        finally:
            s.close()
        self.assertEqual(code, p.OK)
        port, label = out.getvalue().rstrip("\n").split("\t")
        self.assertEqual(port, str(s.port))
        self.assertEqual(label, "IntelliJ IDEA MCP Server 2026.1.4")
        # The healthy every-launch report is one compact line, identity first.
        report = err.getvalue().strip().splitlines()
        self.assertEqual(len(report), 1)
        self.assertIn("IntelliJ IDEA MCP Server 2026.1.4", report[0])
        self.assertIn("OK: exposed set within policy", report[0])

    def test_json_with_relay_ports_still_prints_ports(self):
        import contextlib
        import io
        s = MockMCPServer(tools=["search_symbol"])
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = p.main(["--port", str(s.port), "--relay-ports", "--json", "--timeout", "5"])
        finally:
            s.close()
        self.assertEqual(code, p.OK)
        self.assertEqual(out.getvalue().split("\t")[0], str(s.port))
        self.assertIn('"status"', err.getvalue())

    def test_drifting_server_gets_no_relay_port(self):
        import contextlib
        import io
        s = MockMCPServer(tools=["search_symbol", "apply_patch"])
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = p.main(["--port", str(s.port), "--relay-ports", "--timeout", "5"])
        finally:
            s.close()
        self.assertEqual(code, p.DRIFT)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("DRIFT", err.getvalue())


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
        # A rewritten config must not send the relay off-box.
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
                "/Users/x/proj": {"mcpServers": {"goland": {"url": "http://127.0.0.1:64343/sse"}}}
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


class TestLoadClaudeConfig(unittest.TestCase):
    def test_reads_a_config(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "c.json"
            f.write_text(json.dumps({"mcpServers": {"idea": {"url": "http://127.0.0.1:1234/sse"}}}))
            self.assertEqual(p.discover_servers(p.load_claude_config(f)), [("idea", 1234)])

    def test_missing_file_is_not_an_error(self):
        self.assertEqual(p.load_claude_config(pathlib.Path("/nonexistent/c.json")), {})

    def test_malformed_json_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "c.json"
            f.write_text("{not json")
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
        # A 3xx must not be able to walk us off loopback after the scheme check.
        handlers = [type(h).__name__ for h in p._OPENER.handlers]
        self.assertNotIn("HTTPRedirectHandler", handlers)
        self.assertNotIn("FileHandler", handlers)
        self.assertNotIn("FTPHandler", handlers)


class TestIsJetBrainsMCPServer(unittest.TestCase):
    def test_accepts_the_real_server_names(self):
        self.assertTrue(p.is_jetbrains_mcp_server({"name": "IntelliJ IDEA MCP Server"}))
        self.assertTrue(p.is_jetbrains_mcp_server({"name": "GoLand MCP Server"}))

    def test_rejects_an_unrelated_server(self):
        # The realistic failure: a rewritten config points the relay at something
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
        # Strict subset: we cannot enumerate what JetBrains has not documented,
        # so anything unrecognised fails closed.
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
        import contextlib
        import io
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            p.main(["--port", "1", "--allow", "apply_patch"])


class TestPolicyMatchesTheHarnessDocs(unittest.TestCase):
    """Couple POLICY_TOOLS to the "Exposed (five)" roster in the harness docs.

    The ADR's thesis is verify-don't-assert; a third hand-maintained copy of the
    five would betray it. This reads the roster the integration docs publish and
    asserts POLICY_TOOLS equals it. Skips when the harness tree is absent —
    claude-pod ships standalone, so the docs are only present in the repo.
    """

    # tools/claude-pod/test_ide_preflight.py -> repo root is two parents up.
    _ROOT = pathlib.Path(__file__).resolve().parents[2]
    _DOCS = [
        _ROOT / "harness/stacks/java-spring-boot/.claude/skills/intellij-idea/intellij-mcp-integration.md",
        _ROOT / "harness/stacks/go/.claude/skills/goland/goland-mcp-integration.md",
    ]

    @staticmethod
    def _exposed_tools(md: str) -> set[str]:
        """Parse the backticked tool names from the '### Exposed (…)' table."""
        section = re.search(r"### Exposed \([^\)]*\)\s*\n(.*?)(?:\n### |\n## )", md, re.DOTALL)
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
            self.skipTest("harness docs not present (standalone claude-pod checkout)")
        for doc in present:
            with self.subTest(doc=doc.name):
                exposed = self._exposed_tools(doc.read_text(encoding="utf-8"))
                self.assertEqual(
                    exposed, set(p.POLICY_TOOLS),
                    f"{doc.name} 'Exposed' roster {sorted(exposed)} != POLICY_TOOLS {sorted(p.POLICY_TOOLS)}",
                )


if __name__ == "__main__":
    unittest.main()
