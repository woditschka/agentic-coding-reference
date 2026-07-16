#!/usr/bin/env python3
"""Unit tests for ide_relay.

The pure header logic is tested directly. The relay itself is tested end-to-end
against a loopback stub standing in for the IDE — no container, no real IDE.
"""

import socket
import threading
import unittest

import ide_relay as r


class TestRewriteHost(unittest.TestCase):
    def test_replaces_host_value(self):
        head = b"GET /sse HTTP/1.1\r\nHost: host.docker.internal:64342\r\nAccept: text/event-stream\r\n\r\n"
        out = r.rewrite_host(head)
        self.assertIn(b"Host: localhost\r\n", out)
        self.assertNotIn(b"host.docker.internal", out)

    def test_preserves_other_headers_and_request_line(self):
        head = b"POST /message?sessionId=abc HTTP/1.1\r\nHost: 192.168.5.2:64342\r\nContent-Length: 9\r\n\r\n"
        out = r.rewrite_host(head)
        self.assertTrue(out.startswith(b"POST /message?sessionId=abc HTTP/1.1\r\n"))
        self.assertIn(b"Content-Length: 9\r\n", out)
        self.assertTrue(out.endswith(b"\r\n\r\n"))

    def test_is_case_insensitive(self):
        head = b"GET / HTTP/1.1\r\nhost: 192.168.5.2\r\n\r\n"
        out = r.rewrite_host(head)
        self.assertIn(b"Host: localhost\r\n", out)
        self.assertNotIn(b"192.168.5.2", out)

    def test_replaces_only_the_first_host(self):
        # A smuggled second Host must not survive: the IDE might read either.
        head = b"GET / HTTP/1.1\r\nHost: a\r\nX-Thing: 1\r\nHost: b\r\n\r\n"
        out = r.rewrite_host(head)
        self.assertEqual(out.count(b"Host: localhost"), 1)

    def test_inserts_host_when_absent(self):
        head = b"GET / HTTP/1.0\r\nAccept: */*\r\n\r\n"
        out = r.rewrite_host(head)
        self.assertIn(b"Host: localhost\r\n", out)
        self.assertTrue(out.startswith(b"GET / HTTP/1.0\r\n"))

    def test_does_not_touch_a_host_like_body_token(self):
        head = b"POST /m HTTP/1.1\r\nHost: gw\r\nX-Note: Host: decoy\r\n\r\n"
        out = r.rewrite_host(head)
        self.assertIn(b"X-Note: Host: decoy", out)
        self.assertIn(b"Host: localhost\r\n", out)

    def test_custom_host_value(self):
        head = b"GET / HTTP/1.1\r\nHost: gw\r\n\r\n"
        self.assertIn(b"Host: example\r\n", r.rewrite_host(head, "example"))


class TestRewriteHead(unittest.TestCase):
    """rewrite_head = rewrite_host + Connection: close.

    The handler rewrites only the FIRST head per connection, so keep-alive reuse
    would send later requests through with the wrong Host. Forcing close makes
    a pooling client reconnect per request — every head gets rewritten.
    """

    def test_injects_connection_close(self):
        head = b"POST /m HTTP/1.1\r\nHost: gw\r\nContent-Length: 2\r\n\r\n"
        out = r.rewrite_head(head)
        self.assertIn(b"Connection: close\r\n", out)
        self.assertIn(b"Host: localhost\r\n", out)
        self.assertTrue(out.endswith(b"\r\n\r\n"))

    def test_replaces_a_keep_alive_header(self):
        head = b"POST /m HTTP/1.1\r\nHost: gw\r\nConnection: keep-alive\r\n\r\n"
        out = r.rewrite_head(head)
        self.assertNotIn(b"keep-alive", out)
        self.assertEqual(out.count(b"Connection:"), 1)
        self.assertIn(b"Connection: close\r\n", out)

    def test_connection_as_last_header_still_parses(self):
        head = b"GET /sse HTTP/1.1\r\nAccept: text/event-stream\r\nConnection: keep-alive\r\nHost: gw\r\n\r\n"
        out = r.rewrite_head(head)
        self.assertTrue(out.endswith(b"\r\n\r\n"))
        self.assertIn(b"Connection: close\r\n", out)
        self.assertIn(b"Accept: text/event-stream\r\n", out)

    def test_preserves_request_line_and_other_headers(self):
        head = b"POST /message?sessionId=abc HTTP/1.1\r\nHost: gw\r\nContent-Length: 9\r\n\r\n"
        out = r.rewrite_head(head)
        self.assertTrue(out.startswith(b"POST /message?sessionId=abc HTTP/1.1\r\n"))
        self.assertIn(b"Content-Length: 9\r\n", out)


class TestSplitHead(unittest.TestCase):
    def test_returns_none_until_head_complete(self):
        self.assertIsNone(r.split_head(b"GET / HTTP/1.1\r\nHost: x\r\n"))

    def test_splits_head_from_body(self):
        head, rest = r.split_head(b"POST / HTTP/1.1\r\nHost: x\r\n\r\n{\"a\":1}")
        self.assertTrue(head.endswith(b"\r\n\r\n"))
        self.assertEqual(rest, b'{"a":1}')

    def test_empty_body(self):
        head, rest = r.split_head(b"GET / HTTP/1.1\r\nHost: x\r\n\r\n")
        self.assertEqual(rest, b"")

    def test_oversized_head_raises(self):
        with self.assertRaises(r.HeaderTooLarge):
            r.split_head(b"G" * (r.MAX_HEADER + 1))


class _Stub:
    """Stands in for the IDE: records the head it received, replies with a body."""

    def __init__(self, reply=b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nhi"):
        self.reply = reply
        self.head = None
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(1)
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self):
        conn, _ = self.sock.accept()
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
        self.head = buf
        conn.sendall(self.reply)
        conn.close()

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class TestRelayEndToEnd(unittest.TestCase):
    def test_forwards_and_rewrites_host(self):
        stub = _Stub()
        # The relay listens on the same port it forwards to, so point it at the
        # stub's port and have it "forward" to the same port on localhost.
        handler = type("H", (r._Handler,), {"gateway": "127.0.0.1", "port": stub.port})
        srv = r._Server(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        c = socket.create_connection(("127.0.0.1", srv.server_address[1]), timeout=5)
        try:
            c.sendall(b"GET /sse HTTP/1.1\r\nHost: host.docker.internal:1\r\nAccept: text/event-stream\r\n\r\n")
            resp = b""
            c.settimeout(5)
            while b"hi" not in resp:
                chunk = c.recv(4096)
                if not chunk:
                    break
                resp += chunk
        finally:
            c.close()
            srv.shutdown()
            srv.server_close()
            stub.close()

        self.assertIsNotNone(stub.head, "upstream never received the request")
        self.assertIn(b"Host: localhost\r\n", stub.head)
        self.assertNotIn(b"host.docker.internal", stub.head)
        self.assertIn(b"Accept: text/event-stream", stub.head)
        # One request per connection: a pooled second request would bypass the
        # rewrite, so the upstream must be told to close after this response.
        self.assertIn(b"Connection: close\r\n", stub.head)
        self.assertIn(b"hi", resp)

    def test_upstream_refused_closes_client_cleanly(self):
        # IDE closed mid-session: the client must see a closed connection, not a hang.
        dead = socket.socket()
        dead.bind(("127.0.0.1", 0))
        dead_port = dead.getsockname()[1]
        dead.close()

        handler = type("H", (r._Handler,), {"gateway": "127.0.0.1", "port": dead_port})
        srv = r._Server(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        c = socket.create_connection(("127.0.0.1", srv.server_address[1]), timeout=5)
        try:
            c.sendall(b"GET /sse HTTP/1.1\r\nHost: gw\r\n\r\n")
            c.settimeout(5)
            self.assertEqual(c.recv(4096), b"", "expected upstream failure to close the client")
        finally:
            c.close()
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    unittest.main()
