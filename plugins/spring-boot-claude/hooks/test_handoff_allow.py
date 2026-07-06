#!/usr/bin/env python3
"""Tests for handoff-allow.py (stdlib only).

Run: python3 .claude/hooks/test_handoff_allow.py

Pins the safety model: ALLOW only for a command that is exclusively a
handoff.py invocation — read queries and the canonical quoted-heredoc append —
and DEFER for everything else, including every metacharacter that could
chain, redirect, or substitute, a fake heredoc hidden in a quoted argument,
and any content after the closing delimiter. The hook never denies.
"""

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


def payload(command):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


APPEND = (
    "python3 scripts/handoff.py append build-failure <<'EOF'\n"
    '{"type": "build-failure", "req_id": "REQ-DEMO-001"}\n'
    "EOF"
)


class SanctionedCommands(unittest.TestCase):
    def assert_allows(self, command):
        self.assertEqual(hook.decide(payload(command)), hook.ALLOW_DECISION)

    def test_read_query(self):
        self.assert_allows("python3 scripts/handoff.py latest review-feedback REQ-DEMO-001")

    def test_route_query(self):
        self.assert_allows("python3 scripts/handoff.py route")

    def test_heredoc_append(self):
        self.assert_allows(APPEND)

    def test_heredoc_append_double_quoted_delimiter(self):
        self.assert_allows(
            'python3 scripts/handoff.py append prd-entry <<"EOF"\n{}\nEOF'
        )

    def test_blank_lines_after_delimiter(self):
        self.assert_allows(APPEND + "\n   \n\t\n")

    def test_leading_whitespace_on_command_line(self):
        self.assert_allows("  python3 scripts/handoff.py validate")

    def test_stdin_redirect_is_the_documented_metachar_exception(self):
        self.assert_allows("python3 scripts/handoff.py validate < input.json")

    def test_trailing_blank_line_without_heredoc(self):
        self.assert_allows("python3 scripts/handoff.py validate\n  ")


class DeferredCommands(unittest.TestCase):
    def assert_defers(self, command):
        self.assertIsNone(hook.decide(payload(command)))

    def test_every_forbidden_metacharacter(self):
        for meta in "$`;&|>()":
            with self.subTest(meta=meta):
                self.assert_defers(f"python3 scripts/handoff.py latest x{meta}")

    def test_other_script(self):
        self.assert_defers("python3 scripts/other.py latest")

    def test_bare_invocation_without_arguments(self):
        self.assert_defers("python3 scripts/handoff.py")

    def test_prefix_smuggled_into_longer_path(self):
        self.assert_defers("python3 scripts/handoff.pyx latest")

    def test_unquoted_heredoc_delimiter(self):
        self.assert_defers(
            "python3 scripts/handoff.py append rec <<EOF\n{}\nEOF"
        )

    def test_mismatched_heredoc_quotes_defer(self):
        # The (?P=quote) backreference: <<'EOF" is not a quoted delimiter.
        self.assert_defers(
            "python3 scripts/handoff.py append rec <<'EOF\"\n{}\nEOF"
        )

    def test_heredoc_hidden_in_quoted_argument(self):
        # A quoted <<'EOF' is a literal string to the shell: the lines after
        # it are real commands, not an inert body. The whole-line match
        # rejects it.
        self.assert_defers(
            "python3 scripts/handoff.py append x \"<<'EOF'\"\nrm -rf .\nEOF"
        )

    def test_noncanonical_heredoc_line(self):
        self.assert_defers(
            "python3 scripts/handoff.py append rec extra-arg <<'EOF'\n{}\nEOF"
        )

    def test_command_after_closing_delimiter(self):
        self.assert_defers(APPEND + "\nrm -rf .")

    def test_unterminated_heredoc(self):
        self.assert_defers(
            "python3 scripts/handoff.py append rec <<'EOF'\n{}"
        )

    def test_trailing_command_line_without_heredoc(self):
        self.assert_defers("python3 scripts/handoff.py validate\nrm -rf .")

    def test_empty_command(self):
        self.assert_defers("")

    def test_missing_command(self):
        self.assertIsNone(hook.decide(json.dumps({"tool_name": "Bash", "tool_input": {}})))

    def test_non_string_command(self):
        self.assertIsNone(
            hook.decide(json.dumps({"tool_input": {"command": ["python3"]}}))
        )

    def test_malformed_payload(self):
        self.assertIsNone(hook.decide("not json"))

    def test_non_object_payload(self):
        self.assertIsNone(hook.decide(json.dumps("just a string")))


class ExitContract(unittest.TestCase):
    """The hook process only ever exits 0; ALLOW is stdout JSON, DEFER is silence."""

    def run_hook(self, stdin_text):
        return subprocess.run(
            [sys.executable, str(_HOOK)],
            input=stdin_text, capture_output=True, text=True, check=False,
        )

    def test_allow_prints_decision_and_exits_zero(self):
        result = self.run_hook(payload("python3 scripts/handoff.py route"))
        self.assertEqual(result.returncode, 0)
        decision = json.loads(result.stdout)
        self.assertEqual(
            decision["hookSpecificOutput"]["permissionDecision"], "allow"
        )

    def test_defer_is_silent_and_exits_zero(self):
        result = self.run_hook(payload("rm -rf ."))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_garbage_stdin_defers(self):
        result = self.run_hook("\x00garbage")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
