#!/usr/bin/env python3
"""Tests for open_weight_preflight: the tag comparison and the exit codes the launcher branches on."""

import contextlib
import http.server
import io
import json
import pathlib
import socket
import threading
import time
import unittest
from typing import ClassVar
from unittest import mock

import open_weight_preflight as p

LOCALHOST = "127.0.0.1"
SOME_OPUS_TAG = "glm-5.3:cloud"
SOME_SONNET_TAG = "glm-5.3-flash:cloud"
UNSUFFIXED_TAG = "qwen3-coder"
REGISTRY_TAG = "hf.co/org/model:q8"
REGISTRY_TAG_WITH_PORT = "registry.local:5000/org/model"
SHORT_TIMEOUT_S = 1.0
# How often a fixture server looks for its shutdown request.
SHUTDOWN_POLL_S = 0.01
# The trickling peer needs many times the deadline to finish its listing, and
# each byte arrives well inside the socket timeout.
SHORT_DEADLINE_S = 0.2
TRICKLE_INTERVAL_S = 0.05
# Nested as deep as the size cap admits, past any interpreter's recursion limit.
DEEPLY_NESTED_JSON = b"[" * p.MAX_LISTING_BYTES

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

    def test_a_sized_cloud_tag_is_a_cloud_tag_too(self):
        # Ollama spells some cloud tags with a size before the suffix.
        self.assertEqual(p.verdict(["gpt-oss:120b-cloud"]), p.EXIT_CLOUD_MISSING)

    def test_a_tag_that_only_contains_the_word_is_local(self):
        for tag in ("cloudy:latest", "glm-5.3:cloud-preview", "x-cloud:7b"):
            with self.subTest(tag=tag):
                self.assertEqual(p.verdict([tag]), p.EXIT_LOCAL_MISSING)

    def test_the_launcher_marks_the_same_tag_shapes_as_cloud(self):
        # The launcher's note on where prompts go reads the suffixes in shell.
        engine = (pathlib.Path(p.__file__).parent / "agent-dev").read_text()
        patterns = "|".join(f"*{suffix}" for suffix in p.CLOUD_SUFFIXES)
        self.assertIn(f'case "$t" in {patterns}) OW_CLOUD=1;;', engine)


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


class _RoutedPeer(http.server.BaseHTTPRequestHandler):
    """Answer each path from a table of (status, body); an absent path is a 404."""

    routes: ClassVar[dict[str, tuple[int, bytes]]] = {}

    def do_GET(self):
        status, body = self.routes.get(self.path, (404, b"{}"))
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


class _Redirector(http.server.BaseHTTPRequestHandler):
    """Answer every path with a redirect to the same path on another port."""

    target_port: int = 0

    def do_GET(self):
        self.send_response(302)
        self.send_header(
            "Location", f"http://{LOCALHOST}:{self.target_port}{self.path}"
        )
        self.end_headers()

    def log_message(self, *_):
        pass


class _TricklingPeer(http.server.BaseHTTPRequestHandler):
    """Send the body one byte at a time and record whether all of it left."""

    body: bytes = b""
    finished: threading.Event

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        try:
            for byte in self.body:
                self.wfile.write(bytes([byte]))
                time.sleep(TRICKLE_INTERVAL_S)
        except OSError:
            return
        self.finished.set()

    def log_message(self, *_):
        pass


class PeerCase(unittest.TestCase):
    """A local listing server and main run against it."""

    def start(self, handler: type[http.server.BaseHTTPRequestHandler]) -> int:
        server = http.server.HTTPServer((LOCALHOST, 0), handler)
        threading.Thread(
            target=server.serve_forever,
            kwargs={"poll_interval": SHUTDOWN_POLL_S},
            daemon=True,
        ).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server.server_address[1]

    def serve(self, body: bytes) -> int:
        return self.start(type("Handler", (_Peer,), {"body": body}))

    def route(self, routes: dict[str, tuple[int, bytes]]) -> int:
        return self.start(type("Handler", (_RoutedPeer,), {"routes": routes}))

    def closed_port(self) -> int:
        server = http.server.HTTPServer((LOCALHOST, 0), _Peer)
        server.server_close()
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

    def run_reporting(self, port: int, *tags: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = self.run_main(port, *tags)
        return code, out.getvalue()


class AgainstAPeer(PeerCase):
    """The verdicts, driven through main against a local listing server."""

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
        self.assertEqual(
            self.run_main(self.closed_port(), SOME_OPUS_TAG), p.EXIT_NO_ANSWER
        )

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
        _, report = self.run_reporting(port, LOCAL_TAG)
        self.assertNotIn("\x1b", report)
        self.assertIn("evil?]0;owned?:latest", report)

    def test_a_long_listing_is_shown_up_to_the_cap_and_counted_beyond_it(self):
        beyond = 5
        names = [f"model-{n:02}:latest" for n in range(p.MAX_NAMES_SHOWN + beyond)]
        port = self.serve(json.dumps(listing(*names)).encode())
        _, report = self.run_reporting(port, LOCAL_TAG)
        self.assertIn(f"{names[p.MAX_NAMES_SHOWN - 1]}, +{beyond} more)", report)
        self.assertNotIn(names[p.MAX_NAMES_SHOWN], report)

    def test_deeply_nested_json_exits_two_with_a_one_line_report(self):
        port = self.serve(DEEPLY_NESTED_JSON)
        code, report = self.run_reporting(port, SOME_OPUS_TAG)
        self.assertEqual(code, p.EXIT_NO_ANSWER)
        self.assertEqual(report.count("\n"), 1)

    def test_a_listing_that_outlasts_the_deadline_is_abandoned_while_it_arrives(self):
        # Every byte arrives inside the socket timeout, so only the deadline
        # ends the fetch; a complete listing would name the tag.
        finished = threading.Event()
        body = json.dumps(listing(SOME_OPUS_TAG)).encode()
        port = self.start(
            type("Handler", (_TricklingPeer,), {"body": body, "finished": finished})
        )
        with mock.patch.object(p, "DEADLINE_S", SHORT_DEADLINE_S):
            code = self.run_main(port, SOME_OPUS_TAG)
        self.assertEqual(code, p.EXIT_NO_ANSWER)
        self.assertFalse(finished.is_set())

    def test_a_redirect_is_not_followed_to_another_host(self):
        # The peer is operator policy; where its answer points is not.
        elsewhere = self.serve(json.dumps(listing(SOME_OPUS_TAG)).encode())
        port = self.start(type("Handler", (_Redirector,), {"target_port": elsewhere}))
        self.assertEqual(self.run_main(port, SOME_OPUS_TAG), p.EXIT_NO_ANSWER)


SOME_OPENAI_ID = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
SOME_OTHER_OPENAI_ID = "meta-llama/Llama-3.3-70B-Instruct"


def openai_listing(*ids: str) -> bytes:
    return json.dumps({"object": "list", "data": [{"id": i} for i in ids]}).encode()


class OpenAIStyleIds(unittest.TestCase):
    def test_ids_are_read_from_the_data_array(self):
        self.assertEqual(p.served_ids(json.loads(openai_listing("a", "b"))), {"a", "b"})

    def test_a_listing_without_a_data_array_is_refused(self):
        with self.assertRaises(p.PeerError):
            p.served_ids({"models": []})

    def test_malformed_entries_are_skipped(self):
        self.assertEqual(
            p.served_ids({"data": [{"id": "a"}, {"id": 3}, "x", {}]}), {"a"}
        )

    def test_an_id_is_compared_as_written_not_as_a_latest_tag(self):
        self.assertEqual(
            p.missing([SOME_OPENAI_ID], {SOME_OPENAI_ID}, ollama=False), []
        )
        self.assertEqual(
            p.missing([SOME_OPENAI_ID], {SOME_OPENAI_ID}, ollama=True),
            [SOME_OPENAI_ID],
        )


class AgainstANonOllamaPeer(PeerCase):
    """A peer that is not Ollama answers the OpenAI listing, and the preflight follows it."""

    def test_an_openai_only_server_lists_every_mapped_id(self):
        port = self.route({p.MODELS_PATH: (200, openai_listing(SOME_OPENAI_ID))})
        self.assertEqual(self.run_main(port, SOME_OPENAI_ID), p.EXIT_LISTED)

    def test_an_openai_only_server_missing_an_id_exits_one(self):
        port = self.route({p.MODELS_PATH: (200, openai_listing(SOME_OPENAI_ID))})
        self.assertEqual(
            self.run_main(port, SOME_OTHER_OPENAI_ID), p.EXIT_LOCAL_MISSING
        )

    def test_an_openai_only_server_missing_a_cloud_shaped_id_exits_one(self):
        # Serving a tag on first use is Ollama's behavior.
        port = self.route({p.MODELS_PATH: (200, openai_listing(SOME_OPENAI_ID))})
        self.assertEqual(self.run_main(port, CLOUD_TAG), p.EXIT_LOCAL_MISSING)

    def test_ollamas_listing_is_tried_first(self):
        port = self.route(
            {
                p.TAGS_PATH: (200, json.dumps(listing(SOME_OPUS_TAG)).encode()),
                p.MODELS_PATH: (200, openai_listing("something-else")),
            }
        )
        self.assertEqual(self.run_main(port, SOME_OPUS_TAG), p.EXIT_LISTED)

    def test_an_answer_of_another_shape_falls_back_to_the_openai_listing(self):
        port = self.route(
            {
                p.TAGS_PATH: (200, b'{"unexpected": true}'),
                p.MODELS_PATH: (200, openai_listing(SOME_OPENAI_ID)),
            }
        )
        self.assertEqual(self.run_main(port, SOME_OPENAI_ID), p.EXIT_LISTED)

    def test_an_answer_that_is_not_json_falls_back_to_the_openai_listing(self):
        port = self.route(
            {
                p.TAGS_PATH: (200, b"<html>not a listing</html>"),
                p.MODELS_PATH: (200, openai_listing(SOME_OPENAI_ID)),
            }
        )
        self.assertEqual(self.run_main(port, SOME_OPENAI_ID), p.EXIT_LISTED)

    def test_a_server_with_neither_listing_exits_two(self):
        port = self.route({})
        self.assertEqual(self.run_main(port, SOME_OPENAI_ID), p.EXIT_NO_ANSWER)

    def test_a_dropped_connection_does_not_try_the_second_endpoint(self):
        # The first connection is closed unanswered and a second one would be
        # served the OpenAI listing: a connection failure is the answer.
        sock = socket.socket()
        sock.bind((LOCALHOST, 0))
        sock.listen(2)
        self.addCleanup(sock.close)
        answer = (
            b"HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n"
            + openai_listing(SOME_OPENAI_ID)
        )

        def drop_then_serve():
            dropped, _ = sock.accept()
            dropped.close()
            # No second connection arrives; the cleanup's close ends the wait.
            with contextlib.suppress(OSError):
                served, _ = sock.accept()
                with served:
                    served.recv(1024)
                    served.sendall(answer)

        threading.Thread(target=drop_then_serve, daemon=True).start()
        self.assertEqual(
            self.run_main(sock.getsockname()[1], SOME_OPENAI_ID), p.EXIT_NO_ANSWER
        )


if __name__ == "__main__":
    unittest.main()
