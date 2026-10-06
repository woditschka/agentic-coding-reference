#!/usr/bin/env python3
"""Tests for open_weight_preflight: the tag comparison and the exit codes the launcher branches on."""

import contextlib
import http.server
import io
import json
import socket
import threading
import unittest

import open_weight_preflight as p

LOCALHOST = "127.0.0.1"
SOME_OPUS_TAG = "glm-5.3:cloud"
SOME_SONNET_TAG = "glm-5.3-flash:cloud"
UNSUFFIXED_TAG = "qwen3-coder"
REGISTRY_TAG = "hf.co/org/model:q8"
REGISTRY_TAG_WITH_PORT = "registry.local:5000/org/model"
SHORT_TIMEOUT_S = 1.0

CLOUD_TAG = "glm-5.3:cloud"
LOCAL_TAG = "qwen3-coder:30b"
ESCAPE_NAME = "evil\x1b]0;owned\x07:latest"


def listing(*names: str) -> dict:
    return {"models": [{"name": n, "model": n} for n in names]}


class Verdicts(unittest.TestCase):
    def test_nothing_missing_is_listed(self):
        self.assertEqual(p.verdict([]), p.EXIT_LISTED)

    def test_a_missing_local_tag_fails(self):
        self.assertEqual(p.verdict([LOCAL_TAG]), p.EXIT_LOCAL_MISSING)
        self.assertEqual(p.verdict([CLOUD_TAG, LOCAL_TAG]), p.EXIT_LOCAL_MISSING)

    def test_only_missing_cloud_tags_warn(self):
        # The daemon fetches a cloud tag on first use, so the listing may
        # not carry it yet.
        self.assertEqual(p.verdict([CLOUD_TAG]), p.EXIT_CLOUD_MISSING)


class Sanitizing(unittest.TestCase):
    def test_control_bytes_and_non_ascii_become_question_marks(self):
        self.assertEqual(p.sanitize(ESCAPE_NAME), "evil?]0;owned?:latest")
        self.assertEqual(p.sanitize("caf\u00e9"), "caf?")

    def test_a_long_name_is_capped(self):
        shown = p.sanitize("x" * (p.MAX_NAME_LENGTH + 5))
        self.assertEqual(len(shown), p.MAX_NAME_LENGTH + 3)
        self.assertTrue(shown.endswith("..."))


class TagSpelling(unittest.TestCase):
    def test_an_unsuffixed_tag_means_latest(self):
        self.assertEqual(p.canonical(UNSUFFIXED_TAG), f"{UNSUFFIXED_TAG}:latest")

    def test_a_suffixed_tag_is_kept(self):
        self.assertEqual(p.canonical(SOME_OPUS_TAG), SOME_OPUS_TAG)

    def test_a_registry_port_is_not_a_suffix(self):
        self.assertEqual(
            p.canonical(REGISTRY_TAG_WITH_PORT), f"{REGISTRY_TAG_WITH_PORT}:latest"
        )
        self.assertEqual(p.canonical(REGISTRY_TAG), REGISTRY_TAG)


class Comparison(unittest.TestCase):
    def test_every_listed_tag_is_present(self):
        served = p.served_tags(listing(SOME_OPUS_TAG, SOME_SONNET_TAG))
        self.assertEqual(p.missing([SOME_OPUS_TAG, SOME_SONNET_TAG], served), [])

    def test_absent_tags_are_named_in_map_order(self):
        served = p.served_tags(listing(SOME_OPUS_TAG))
        self.assertEqual(
            p.missing([LOCAL_TAG, SOME_OPUS_TAG, SOME_SONNET_TAG], served),
            [LOCAL_TAG, SOME_SONNET_TAG],
        )

    def test_an_unsuffixed_map_value_matches_the_latest_listing(self):
        served = p.served_tags(listing(f"{UNSUFFIXED_TAG}:latest"))
        self.assertEqual(p.missing([UNSUFFIXED_TAG], served), [])

    def test_a_listing_without_a_models_array_is_refused(self):
        for document in ({}, {"models": "x"}, [], None):
            with self.subTest(document=document), self.assertRaises(p.PeerError):
                p.served_tags(document)

    def test_malformed_entries_are_skipped(self):
        served = p.served_tags({"models": [1, {"name": 2}, {"name": SOME_OPUS_TAG}]})
        self.assertEqual(served, {SOME_OPUS_TAG})


class _Peer(http.server.BaseHTTPRequestHandler):
    body: bytes = b""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_):
        pass


class AgainstAPeer(unittest.TestCase):
    """The verdicts, driven through main against a local listing server."""

    def serve(self, body: bytes) -> int:
        handler = type("Handler", (_Peer,), {"body": body})
        server = http.server.HTTPServer((LOCALHOST, 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server.server_address[1]

    def run_main(self, port: int, *tags: str) -> int:
        argv = [
            "--peer",
            LOCALHOST,
            "--port",
            str(port),
            "--timeout",
            str(SHORT_TIMEOUT_S),
        ]
        for tag in tags:
            argv += ["--tag", tag]
        return p.main(argv)

    def test_a_complete_map_exits_zero(self):
        port = self.serve(json.dumps(listing(SOME_OPUS_TAG, SOME_SONNET_TAG)).encode())
        self.assertEqual(
            self.run_main(port, SOME_OPUS_TAG, SOME_SONNET_TAG), p.EXIT_LISTED
        )

    def test_a_missing_local_tag_exits_one(self):
        port = self.serve(json.dumps(listing(SOME_OPUS_TAG)).encode())
        self.assertEqual(
            self.run_main(port, SOME_OPUS_TAG, LOCAL_TAG), p.EXIT_LOCAL_MISSING
        )

    def test_a_missing_cloud_tag_exits_three(self):
        port = self.serve(json.dumps(listing(LOCAL_TAG)).encode())
        self.assertEqual(self.run_main(port, CLOUD_TAG), p.EXIT_CLOUD_MISSING)

    def test_a_peer_that_does_not_answer_exits_two(self):
        # A closed port: the server is created and shut before the probe.
        server = http.server.HTTPServer((LOCALHOST, 0), _Peer)
        port = server.server_address[1]
        server.server_close()
        self.assertEqual(self.run_main(port, SOME_OPUS_TAG), p.EXIT_NO_ANSWER)

    def test_a_peer_answering_garbage_exits_two(self):
        port = self.serve(b"<html>not a listing</html>")
        self.assertEqual(self.run_main(port, SOME_OPUS_TAG), p.EXIT_NO_ANSWER)

    def test_a_peer_that_does_not_speak_http_exits_two(self):
        # A wrong port or a TLS-only listener answers with bytes that are not
        # a status line; that is "did not answer", never "tag missing".
        sock = socket.socket()
        sock.bind((LOCALHOST, 0))
        sock.listen(1)
        self.addCleanup(sock.close)

        def answer():
            conn, _ = sock.accept()
            with conn:
                conn.recv(1024)
                conn.sendall(b"\x16\x03\x01 not http\r\n\r\n")

        threading.Thread(target=answer, daemon=True).start()
        self.assertEqual(
            self.run_main(sock.getsockname()[1], SOME_OPUS_TAG), p.EXIT_NO_ANSWER
        )

    def test_an_oversized_listing_exits_two(self):
        body = json.dumps({"models": [{"name": "x" * p.MAX_LISTING_BYTES}]}).encode()
        port = self.serve(body)
        self.assertEqual(self.run_main(port, SOME_OPUS_TAG), p.EXIT_NO_ANSWER)

    def test_a_served_name_reaches_the_terminal_sanitized(self):
        port = self.serve(json.dumps(listing(ESCAPE_NAME)).encode())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.run_main(port, LOCAL_TAG)
        self.assertNotIn("\x1b", out.getvalue())
        self.assertIn("evil?]0;owned?:latest", out.getvalue())


if __name__ == "__main__":
    unittest.main()
