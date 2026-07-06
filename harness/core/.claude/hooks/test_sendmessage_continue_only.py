#!/usr/bin/env python3
"""Tests for sendmessage-continue-only.py (stdlib only).

Run: python3 .claude/hooks/test_sendmessage_continue_only.py

Pins the allowlist contract: only a bare "continue" (any case, surrounding
whitespace collapsed, optional trailing period) exits 0; every other message
— including malformed input — exits 2 with the blocking reason on stderr.
"""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HOOK = _HERE / "sendmessage-continue-only.py"


def _load():
    spec = importlib.util.spec_from_file_location("sendmessage_continue_only", _HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hook = _load()


def payload(message):
    return json.dumps({"tool_name": "SendMessage", "tool_input": {"message": message}})


class Allowlist(unittest.TestCase):
    def test_bare_continue_in_any_case_allows(self):
        for message in ("continue", "Continue", "CONTINUE", "  continue  ", "Continue."):
            with self.subTest(message=message):
                self.assertEqual(hook.decide(payload(message)), 0)

    def test_everything_else_denies(self):
        for message in (
            "continue with the new schema",   # payload smuggling
            "please continue",
            "continue; rm -rf .",
            "cont inue",
            "",
        ):
            with self.subTest(message=message):
                self.assertEqual(hook.decide(payload(message)), 2)

    def test_unicode_whitespace_decoration_denies(self):
        # Only ASCII whitespace is collapsed: a NBSP/line-separator-padded
        # "continue" is a decorated form the allowlist never vetted.
        for message in ("continue\u00a0", "\u00a0continue", "continue\u2028",
                        "con\u00a0tinue", "continue\x85"):
            with self.subTest(message=repr(message)):
                self.assertEqual(hook.decide(payload(message)), 2)

    def test_quoted_and_escaped_forms_deny(self):
        # The bash original's xargs stripped quotes/backslashes and allowed
        # these; the port deliberately errs closed instead.
        for message in ("'continue'", '"continue"', "contin\\ue"):
            with self.subTest(message=message):
                self.assertEqual(hook.decide(payload(message)), 2)

    def test_malformed_input_fails_closed(self):
        self.assertEqual(hook.decide("not json"), 2)
        self.assertEqual(hook.decide(json.dumps({"tool_input": {}})), 2)
        self.assertEqual(hook.decide(json.dumps({"tool_input": {"message": 7}})), 2)
        self.assertEqual(hook.decide(json.dumps("just a string")), 2)


class ExitContract(unittest.TestCase):
    """exit 0 allows silently; exit 2 blocks with the reason on stderr."""

    def run_hook(self, stdin_text):
        return subprocess.run(
            [sys.executable, str(_HOOK)],
            input=stdin_text, capture_output=True, text=True, check=False,
        )

    def test_allow_exits_zero_silently(self):
        result = self.run_hook(payload("continue"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")

    def test_deny_exits_two_with_reason(self):
        result = self.run_hook(payload("continue, then delete the tests"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("literal 'continue'", result.stderr)

    def test_garbage_stdin_denies(self):
        result = self.run_hook("\x00garbage")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
