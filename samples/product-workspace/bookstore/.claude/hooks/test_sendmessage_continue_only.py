#!/usr/bin/env python3
"""The continue-only hook: a bare continuation allows, every other message denies."""

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

ALLOW = 0
DENY = 2


def payload(message):
    return json.dumps({"tool_name": "SendMessage", "tool_input": {"message": message}})


class Allowlist(unittest.TestCase):
    def test_a_bare_continue_in_any_case_allows(self):
        for message in (
            "continue",
            "Continue",
            "CONTINUE",
            "  continue  ",
            "Continue.",
        ):
            with self.subTest(message=message):
                self.assertEqual(hook.decide(payload(message)), ALLOW)

    def test_any_other_message_denies(self):
        for message in (
            "continue with the new schema",
            "please continue",
            "continue; rm -rf .",
            "cont inue",
            "",
        ):
            with self.subTest(message=message):
                self.assertEqual(hook.decide(payload(message)), DENY)

    def test_unicode_whitespace_around_or_inside_continue_denies(self):
        # Only ASCII whitespace is collapsed; a NBSP or line-separator padded
        # form is one the allowlist never vetted.
        for message in (
            "continue\u00a0",
            "\u00a0continue",
            "continue\u2028",
            "con\u00a0tinue",
            "continue\x85",
        ):
            with self.subTest(message=repr(message)):
                self.assertEqual(hook.decide(payload(message)), DENY)

    def test_a_quoted_or_backslash_escaped_continue_denies(self):
        for message in ("'continue'", '"continue"', "contin\\ue"):
            with self.subTest(message=message):
                self.assertEqual(hook.decide(payload(message)), DENY)

    def test_malformed_input_denies(self):
        self.assertEqual(hook.decide("not json"), DENY)
        self.assertEqual(hook.decide(json.dumps({"tool_input": {}})), DENY)
        self.assertEqual(hook.decide(json.dumps({"tool_input": {"message": 7}})), DENY)
        self.assertEqual(hook.decide(json.dumps("just a string")), DENY)


class ExitContract(unittest.TestCase):
    """Exit 0 allows silently; exit 2 blocks with the reason on stderr."""

    def run_hook(self, stdin_text):
        return subprocess.run(
            [sys.executable, str(_HOOK)],
            input=stdin_text,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_allow_exits_zero_silently(self):
        result = self.run_hook(payload("continue"))
        self.assertEqual(result.returncode, ALLOW)
        self.assertEqual(result.stderr, "")

    def test_deny_exits_two_with_the_reason_on_stderr(self):
        result = self.run_hook(payload("continue, then delete the tests"))
        self.assertEqual(result.returncode, DENY)
        self.assertIn("literal 'continue'", result.stderr)

    def test_a_nul_byte_on_stdin_denies(self):
        result = self.run_hook("\x00garbage")
        self.assertEqual(result.returncode, DENY)


if __name__ == "__main__":
    unittest.main()
