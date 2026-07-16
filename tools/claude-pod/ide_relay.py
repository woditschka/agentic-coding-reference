#!/usr/bin/env python3
"""ide_relay — make a host JetBrains IDE's MCP port reachable from inside the pod.

Runs INSIDE the pod. Listens on 127.0.0.1:<port> and forwards to the Docker VM
gateway on the same port, rewriting the request head on the way: Host (see
below) and `Connection: close`, so a pooling client re-connects per request and
every request head — not just the first per connection — gets the rewrite.

Why it exists. The IDE writes its own MCP config into ~/.claude.json as
`http://127.0.0.1:64342/sse`. That file is bind-mounted into the pod, where
127.0.0.1 is the container itself — so the entry is present and broken. Listening
on the same port inside the pod makes the host's own config true here, with no
rewritten URL, no --mcp-config, and no name collision.

Why it rewrites Host. The IDE rejects any request whose Host is not localhost
(DNS-rebinding protection). Reaching it by gateway IP means sending Host:
host.docker.internal, which it refuses. We put localhost back.

Why it needs no SSE parsing. The IDE's endpoint event carries a RELATIVE path
(`data: /message?sessionId=...`), so the client resolves it against its own base —
this relay — and posts back here. Nothing needs URL rewriting, so this stays a byte
pump rather than an MCP proxy.

What it is NOT: a security boundary. The pod can already reach the gateway itself
(the IDE's loopback bind does not confine it on macOS, and it has no auth), so this
relay grants the pod nothing it lacked. It is plumbing. The only real control over
what the pod can do to the IDE is the IDE's own Exposed Tools setting — see
ide_preflight.py and the README's Security Model.

Usage:
    ide_relay.py --port 64342 [--port 64343] [--gateway host.docker.internal]
"""

from __future__ import annotations

import argparse
import re
import socket
import socketserver
import sys
import threading

# Requests are forwarded verbatim except these headers. The IDE's DNS-rebinding
# guard only accepts localhost, and we arrive via the gateway IP.
_HOST_LINE = re.compile(rb"^Host:[^\r\n]*\r\n", re.IGNORECASE | re.MULTILINE)
_CONNECTION_LINE = re.compile(rb"^Connection:[^\r\n]*\r\n", re.IGNORECASE | re.MULTILINE)

HEADER_END = b"\r\n\r\n"
MAX_HEADER = 64 * 1024


class HeaderTooLarge(Exception):
    pass


# ── pure logic (unit-tested; no I/O) ──────────────────────────────────────────


def rewrite_host(head: bytes, host: str = "localhost") -> bytes:
    """Replace the Host header's value. Adds one if the request carries none."""
    replacement = f"Host: {host}\r\n".encode()
    if _HOST_LINE.search(head):
        return _HOST_LINE.sub(replacement, head, count=1)
    # No Host at all (HTTP/1.0): insert directly after the request line.
    line_end = head.find(b"\r\n")
    if line_end == -1:
        return head
    return head[: line_end + 2] + replacement + head[line_end + 2 :]


def rewrite_head(head: bytes, host: str = "localhost") -> bytes:
    """Rewrite the Host header and force one request per connection.

    Only the FIRST request on a connection passes through this rewrite — after
    the head, the handler is a verbatim byte pump. A keep-alive client would
    reuse the connection for a second request whose Host arrives unrewritten and
    is refused by the IDE's DNS-rebinding guard. Forcing `Connection: close`
    makes the transport match the handler: the IDE closes after the response,
    the client opens a fresh connection per request, and every head is rewritten.
    The SSE stream is unaffected — its single response never ends anyway.
    """
    head = _CONNECTION_LINE.sub(b"", rewrite_host(head, host))
    if not head.endswith(HEADER_END):
        return head
    return head[: -len(HEADER_END)] + b"\r\nConnection: close" + HEADER_END


def split_head(buf: bytes) -> tuple[bytes, bytes] | None:
    """Split a buffer at the end of the request head. None if not yet complete."""
    idx = buf.find(HEADER_END)
    if idx == -1:
        if len(buf) > MAX_HEADER:
            raise HeaderTooLarge(f"request head exceeded {MAX_HEADER} bytes")
        return None
    return buf[: idx + len(HEADER_END)], buf[idx + len(HEADER_END) :]


# ── relay (I/O) ───────────────────────────────────────────────────────────────


def _pump(src: socket.socket, dst: socket.socket) -> None:
    """Copy bytes until either side closes. Both directions run one of these."""
    try:
        while True:
            chunk = src.recv(65536)
            if not chunk:
                break
            dst.sendall(chunk)
    except OSError:
        pass
    finally:
        for s in (src, dst):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass


class _Handler(socketserver.BaseRequestHandler):
    gateway: str
    port: int

    def handle(self) -> None:
        client = self.request
        buf = b""
        try:
            while True:
                chunk = client.recv(8192)
                if not chunk:
                    return  # client hung up before sending a full head
                buf += chunk
                split = split_head(buf)
                if split:
                    head, rest = split
                    break
        except (OSError, HeaderTooLarge):
            return

        try:
            upstream = socket.create_connection((self.gateway, self.port), timeout=10)
        except OSError:
            return  # IDE went away mid-session; the client sees a closed connection

        # Own the upstream socket for the whole handler: shutdown alone (in _pump)
        # leaves the FD open until GC, which leaks descriptors over a long-lived
        # relay. socketserver closes `client` for us; upstream is ours to close.
        try:
            try:
                upstream.sendall(rewrite_head(head) + rest)
            except OSError:
                return
            # SSE streams stay open for the session's life, so both directions must
            # run concurrently — the client posts on other connections while this
            # one is still streaming events back.
            t = threading.Thread(target=_pump, args=(upstream, client), daemon=True)
            t.start()
            _pump(client, upstream)
            t.join(timeout=5)
        finally:
            upstream.close()


class _Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve(port: int, gateway: str) -> _Server:
    handler = type("Handler", (_Handler,), {"gateway": gateway, "port": port})
    # Loopback only: nothing outside this container should reach the relay.
    srv = _Server(("127.0.0.1", port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, action="append", required=True, help="port to relay (repeatable)")
    ap.add_argument("--gateway", default="host.docker.internal", help="host gateway name or IP")
    args = ap.parse_args(argv)

    servers = []
    for port in args.port:
        try:
            servers.append(serve(port, args.gateway))
        except OSError as exc:
            print(f"ide-relay: cannot listen on 127.0.0.1:{port} — {exc}", file=sys.stderr)
            return 1
        print(f"ide-relay: 127.0.0.1:{port} -> {args.gateway}:{port}", file=sys.stderr)

    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        for srv in servers:
            srv.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
