#!/usr/bin/env python3
"""The allow hook: sanctioned handoff.py commands allow, everything else defers, nothing denies."""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HOOK = _HERE / "handoff-allow.py"


def _load():
    spec = importlib.util.spec_from_file_location("handoff_allow", _HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hook = _load()

HOOK_EXIT = 0
SILENCE = ""


def payload(command):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


CANONICAL_APPEND = (
    "python3 scripts/handoff.py append build-failure <<'EOF'\n"
    '{"type": "build-failure", "req_id": "REQ-DEMO-001"}\n'
    "EOF"
)


class SanctionedCommands(unittest.TestCase):
    def assert_allows(self, command):
        self.assertEqual(hook.decide(payload(command)), hook.ALLOW_DECISION)

    def test_a_read_query_allows(self):
        self.assert_allows(
            "python3 scripts/handoff.py latest review-feedback REQ-DEMO-001"
        )

    def test_the_route_query_allows(self):
        self.assert_allows("python3 scripts/handoff.py route")

    def test_the_canonical_heredoc_append_allows(self):
        self.assert_allows(CANONICAL_APPEND)

    def test_a_double_quoted_delimiter_allows(self):
        self.assert_allows(
            'python3 scripts/handoff.py append prd-entry <<"EOF"\n{}\nEOF'
        )

    def test_blank_lines_after_the_delimiter_allow(self):
        self.assert_allows(CANONICAL_APPEND + "\n   \n\t\n")

    def test_leading_whitespace_on_the_command_line_allows(self):
        self.assert_allows("  python3 scripts/handoff.py validate")

    def test_stdin_redirect_is_the_documented_metachar_exception(self):
        self.assert_allows("python3 scripts/handoff.py validate < input.json")

    def test_a_trailing_blank_line_without_a_heredoc_allows(self):
        self.assert_allows("python3 scripts/handoff.py validate\n  ")


class DeferredCommands(unittest.TestCase):
    def assert_defers(self, command):
        self.assertIsNone(hook.decide(payload(command)))

    def test_every_forbidden_metacharacter_defers(self):
        for meta in "$`;&|>()":
            with self.subTest(meta=meta):
                self.assert_defers(f"python3 scripts/handoff.py latest x{meta}")

    def test_another_script_defers(self):
        self.assert_defers("python3 scripts/other.py latest")

    def test_a_bare_invocation_without_arguments_defers(self):
        self.assert_defers("python3 scripts/handoff.py")

    def test_a_longer_script_name_sharing_the_prefix_defers(self):
        self.assert_defers("python3 scripts/handoff.pyx latest")

    def test_an_unquoted_heredoc_delimiter_defers(self):
        self.assert_defers("python3 scripts/handoff.py append rec <<EOF\n{}\nEOF")

    def test_mismatched_heredoc_quotes_defer(self):
        # The (?P=quote) backreference: <<'EOF" is not a quoted delimiter.
        self.assert_defers("python3 scripts/handoff.py append rec <<'EOF\"\n{}\nEOF")

    def test_a_quoted_heredoc_operator_as_an_argument_defers(self):
        # A quoted <<'EOF' is a literal string to the shell, so the lines
        # after it are real commands, not an inert body.
        self.assert_defers(
            "python3 scripts/handoff.py append x \"<<'EOF'\"\nrm -rf .\nEOF"
        )

    def test_a_noncanonical_heredoc_line_defers(self):
        self.assert_defers(
            "python3 scripts/handoff.py append rec extra-arg <<'EOF'\n{}\nEOF"
        )

    def test_a_command_after_the_closing_delimiter_defers(self):
        self.assert_defers(CANONICAL_APPEND + "\nrm -rf .")

    def test_an_unterminated_heredoc_defers(self):
        self.assert_defers("python3 scripts/handoff.py append rec <<'EOF'\n{}")

    def test_a_trailing_command_line_without_a_heredoc_defers(self):
        self.assert_defers("python3 scripts/handoff.py validate\nrm -rf .")

    def test_an_empty_command_defers(self):
        self.assert_defers("")

    def test_a_missing_command_defers(self):
        self.assertIsNone(
            hook.decide(json.dumps({"tool_name": "Bash", "tool_input": {}}))
        )

    def test_a_non_string_command_defers(self):
        self.assertIsNone(
            hook.decide(json.dumps({"tool_input": {"command": ["python3"]}}))
        )

    def test_a_malformed_payload_defers(self):
        self.assertIsNone(hook.decide("not json"))

    def test_a_non_object_payload_defers(self):
        self.assertIsNone(hook.decide(json.dumps("just a string")))


class ExitContract(unittest.TestCase):
    """The hook process only ever exits 0; ALLOW is stdout JSON, DEFER is silence."""

    def run_hook(self, stdin_text):
        return subprocess.run(
            [sys.executable, str(_HOOK)],
            input=stdin_text,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_allow_prints_the_decision_and_exits_zero(self):
        result = self.run_hook(payload("python3 scripts/handoff.py route"))
        self.assertEqual(result.returncode, HOOK_EXIT)
        self.assertEqual(json.loads(result.stdout), json.loads(hook.ALLOW_DECISION))

    def test_defer_is_silent_and_exits_zero(self):
        result = self.run_hook(payload("rm -rf ."))
        self.assertEqual(result.returncode, HOOK_EXIT)
        self.assertEqual(result.stdout, SILENCE)

    def test_a_nul_byte_on_stdin_defers(self):
        result = self.run_hook("\x00garbage")
        self.assertEqual(result.returncode, HOOK_EXIT)
        self.assertEqual(result.stdout, SILENCE)


if __name__ == "__main__":
    unittest.main()
