#!/usr/bin/env python3
"""Tests for handoff-log-guard.py (stdlib only).

Run: python3 .claude/hooks/test_handoff_log_guard.py

Pins the safety model: DENY only a direct Edit/Write on the handoff log or an
unquoted redirect/tee signature targeting it — scanned outside single-line
quoted strings and outside a quoted heredoc body — and DEFER everything else.
The sanctioned handoff.py first line is handoff-allow.py's jurisdiction and
leaves the scan; its trailing lines stay in it.
"""

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HOOK = _HERE / "handoff-log-guard.py"


def _load():
    spec = importlib.util.spec_from_file_location("handoff_log_guard", _HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hook = _load()


def bash_payload(command):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def write_payload(tool, file_path, key="file_path"):
    return json.dumps({"tool_name": tool, "tool_input": {key: file_path}})


class FileToolTargets(unittest.TestCase):
    def test_denies_every_write_tool_on_the_log(self):
        for tool in ("Write", "Edit", "MultiEdit"):
            with self.subTest(tool=tool):
                self.assertEqual(
                    hook.decide(write_payload(tool, ".scratch/handoff.jsonl")),
                    hook.DENY_DECISION,
                )

    def test_denies_notebook_path(self):
        self.assertEqual(
            hook.decide(
                write_payload("NotebookEdit", ".scratch/handoff.jsonl", key="notebook_path")
            ),
            hook.DENY_DECISION,
        )

    def test_denies_absolute_and_nested_forms(self):
        for path in ("/repo/.scratch/handoff.jsonl", "sub/dir/.scratch/handoff.jsonl"):
            with self.subTest(path=path):
                self.assertEqual(
                    hook.decide(write_payload("Write", path)), hook.DENY_DECISION
                )

    def test_denies_log_path_smuggled_after_a_newline(self):
        # grep's per-line semantics, kept via re.MULTILINE: a path argument
        # carrying the log name on a second line still denies.
        self.assertEqual(
            hook.decide(write_payload("Write", "x\n.scratch/handoff.jsonl")),
            hook.DENY_DECISION,
        )

    def test_denies_notebook_path_when_file_path_is_empty(self):
        # The bash original's jq `//` treated "" as truthy and deferred; the
        # port falls through to notebook_path — a deliberate tightening.
        payload = json.dumps({"tool_name": "NotebookEdit", "tool_input": {
            "file_path": "", "notebook_path": ".scratch/handoff.jsonl"}})
        self.assertEqual(hook.decide(payload), hook.DENY_DECISION)

    def test_defers_lookalike_directory(self):
        self.assertIsNone(hook.decide(write_payload("Write", "foo.scratch/handoff.jsonl")))

    def test_defers_other_files(self):
        self.assertIsNone(hook.decide(write_payload("Edit", ".scratch/notes.md")))

    def test_defers_missing_file_path(self):
        self.assertIsNone(hook.decide(json.dumps({"tool_name": "Write", "tool_input": {}})))


class BashRedirectSignatures(unittest.TestCase):
    def assert_denies(self, command):
        self.assertEqual(hook.decide(bash_payload(command)), hook.DENY_DECISION)

    def assert_defers(self, command):
        self.assertIsNone(hook.decide(bash_payload(command)))

    def test_denies_append_and_truncate_redirects(self):
        self.assert_denies("echo x >> .scratch/handoff.jsonl")
        self.assert_denies("echo x > .scratch/handoff.jsonl")

    def test_denies_tee_variants(self):
        self.assert_denies("echo x | tee .scratch/handoff.jsonl")
        self.assert_denies("echo x | tee -a .scratch/handoff.jsonl")
        self.assert_denies("echo x | tee --append .scratch/handoff.jsonl")

    def test_denies_absolute_target_and_trailing_chain(self):
        self.assert_denies("echo x >> /repo/.scratch/handoff.jsonl; echo done")

    def test_defers_redirect_to_other_files(self):
        self.assert_defers("echo x >> .scratch/other.jsonl")
        self.assert_defers("echo x >> handoff.jsonl")

    def test_defers_lookalike_tee_command(self):
        self.assert_defers("xtee .scratch/handoff.jsonl")

    def test_defers_quoted_mention(self):
        self.assert_defers("git commit -m 'fix: stop echo >> .scratch/handoff.jsonl'")
        self.assert_defers('git commit -m "fix: stop echo >> .scratch/handoff.jsonl"')

    def test_quoted_path_redirect_is_missed_by_design(self):
        # Documented miss: a quoted-path redirect is data to this scan; the
        # gate's `handoff.py validate` step is the deterministic backstop.
        self.assert_defers("echo x >> '.scratch/handoff.jsonl'")

    def test_multiline_quoted_mention_still_denies(self):
        # A quote pair spanning a newline is not stripped: a recoverable
        # false positive, never a bypass.
        self.assert_denies(
            "git commit -m 'line one\necho x >> .scratch/handoff.jsonl\nline three'"
        )

    def test_defers_other_tools_and_malformed_input(self):
        self.assertIsNone(hook.decide(json.dumps({"tool_name": "Glob", "tool_input": {}})))
        self.assertIsNone(hook.decide("not json"))
        self.assertIsNone(hook.decide(json.dumps({"tool_input": "not a dict"})))


class HeredocHandling(unittest.TestCase):
    def assert_denies(self, command):
        self.assertEqual(hook.decide(bash_payload(command)), hook.DENY_DECISION)

    def assert_defers(self, command):
        self.assertIsNone(hook.decide(bash_payload(command)))

    def test_sanctioned_append_with_forbidden_string_in_body_defers(self):
        self.assert_defers(
            "python3 scripts/handoff.py append rec <<'EOF'\n"
            '{"note": "echo x >> .scratch/handoff.jsonl"}\n'
            "EOF"
        )

    def test_redirect_chained_after_heredoc_closer_denies(self):
        self.assert_denies(
            "python3 scripts/handoff.py append rec <<'EOF'\n"
            "{}\n"
            "EOF\n"
            "echo x >> .scratch/handoff.jsonl"
        )

    def test_quoted_heredoc_body_of_any_command_is_inert(self):
        self.assert_defers(
            "cat <<'DOC'\necho x >> .scratch/handoff.jsonl\nDOC"
        )

    def test_unquoted_heredoc_body_stays_scanned(self):
        self.assert_denies(
            "cat <<DOC\necho x >> .scratch/handoff.jsonl\nDOC"
        )

    def test_dash_heredoc_closes_on_tab_indented_delimiter(self):
        self.assert_defers(
            "cat <<-'DOC'\n\techo x >> .scratch/handoff.jsonl\n\tDOC"
        )

    def test_sanctioned_line_with_metacharacters_stays_scanned(self):
        self.assert_denies(
            "python3 scripts/handoff.py latest x > .scratch/handoff.jsonl"
        )


class CrossHookInterlock(unittest.TestCase):
    """The load-bearing invariant both docstrings state: handoff-allow.py only
    ALLOWS commands this guard DEFERS on — a deny here can never override its
    ALLOW. Run both deciders over a shared sanctioned corpus so either regex
    drifting into a conflict fails loud."""

    def test_guard_defers_on_everything_the_allow_hook_allows(self):
        spec = importlib.util.spec_from_file_location(
            "handoff_allow", _HERE / "handoff-allow.py")
        allow_hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(allow_hook)
        sanctioned = (
            "python3 scripts/handoff.py route",
            "python3 scripts/handoff.py latest review-feedback REQ-DEMO-001",
            "python3 scripts/handoff.py validate",
            "python3 scripts/handoff.py append rec <<'EOF'\n"
            '{"note": "echo x >> .scratch/handoff.jsonl"}\n'
            "EOF",
            "python3 scripts/handoff.py append rec <<\"EOF\"\n{}\nEOF\n  \n",
        )
        for command in sanctioned:
            with self.subTest(command=command.splitlines()[0]):
                self.assertIsNotNone(allow_hook.decide(bash_payload(command)),
                                     "corpus entry is not actually allowed")
                self.assertIsNone(hook.decide(bash_payload(command)),
                                  "guard denies a command the allow hook allows")


class ExitContract(unittest.TestCase):
    """The hook process only ever exits 0; DENY is stdout JSON, DEFER is silence."""

    def run_hook(self, stdin_text):
        return subprocess.run(
            [sys.executable, str(_HOOK)],
            input=stdin_text, capture_output=True, text=True, check=False,
        )

    def test_deny_prints_decision_and_exits_zero(self):
        result = self.run_hook(bash_payload("echo x >> .scratch/handoff.jsonl"))
        self.assertEqual(result.returncode, 0)
        decision = json.loads(result.stdout)
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("handoff.py append", decision["hookSpecificOutput"]["permissionDecisionReason"])

    def test_defer_is_silent_and_exits_zero(self):
        result = self.run_hook(bash_payload("ls -la"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_garbage_stdin_defers(self):
        result = self.run_hook("\x00garbage")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
