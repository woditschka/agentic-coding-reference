#!/usr/bin/env python3
"""The log guard: a raw write onto the handoff log denies, everything else defers."""

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

LOG = ".scratch/handoff.jsonl"
HOOK_EXIT = 0
SILENCE = ""


def bash_payload(command):
    return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})


def write_payload(tool, file_path, key="file_path"):
    return json.dumps({"tool_name": tool, "tool_input": {key: file_path}})


class FileToolTargets(unittest.TestCase):
    def test_denies_every_write_tool_on_the_log(self):
        for tool in ("Write", "Edit", "MultiEdit"):
            with self.subTest(tool=tool):
                self.assertEqual(
                    hook.decide(write_payload(tool, LOG)), hook.DENY_DECISION
                )

    def test_denies_the_log_as_a_notebook_path(self):
        self.assertEqual(
            hook.decide(write_payload("NotebookEdit", LOG, key="notebook_path")),
            hook.DENY_DECISION,
        )

    def test_denies_absolute_and_nested_forms(self):
        for path in (f"/repo/{LOG}", f"sub/dir/{LOG}"):
            with self.subTest(path=path):
                self.assertEqual(
                    hook.decide(write_payload("Write", path)), hook.DENY_DECISION
                )

    def test_denies_the_log_path_on_a_second_line_of_the_argument(self):
        self.assertEqual(
            hook.decide(write_payload("Write", f"x\n{LOG}")),
            hook.DENY_DECISION,
        )

    def test_denies_the_notebook_path_when_the_file_path_is_empty(self):
        payload = json.dumps(
            {
                "tool_name": "NotebookEdit",
                "tool_input": {"file_path": "", "notebook_path": LOG},
            }
        )
        self.assertEqual(hook.decide(payload), hook.DENY_DECISION)

    def test_defers_a_lookalike_directory(self):
        self.assertIsNone(hook.decide(write_payload("Write", f"foo{LOG}")))

    def test_defers_other_files(self):
        self.assertIsNone(hook.decide(write_payload("Edit", ".scratch/notes.md")))

    def test_defers_a_missing_file_path(self):
        self.assertIsNone(
            hook.decide(json.dumps({"tool_name": "Write", "tool_input": {}}))
        )


class BashRedirectSignatures(unittest.TestCase):
    def assert_denies(self, command):
        self.assertEqual(hook.decide(bash_payload(command)), hook.DENY_DECISION)

    def assert_defers(self, command):
        self.assertIsNone(hook.decide(bash_payload(command)))

    def test_denies_append_and_truncate_redirects(self):
        self.assert_denies(f"echo x >> {LOG}")
        self.assert_denies(f"echo x > {LOG}")

    def test_denies_every_tee_form(self):
        self.assert_denies(f"echo x | tee {LOG}")
        self.assert_denies(f"echo x | tee -a {LOG}")
        self.assert_denies(f"echo x | tee --append {LOG}")

    def test_denies_an_absolute_target_followed_by_a_chained_command(self):
        self.assert_denies(f"echo x >> /repo/{LOG}; echo done")

    def test_defers_a_redirect_to_other_files(self):
        self.assert_defers("echo x >> .scratch/other.jsonl")
        self.assert_defers("echo x >> handoff.jsonl")

    def test_defers_a_lookalike_tee_command(self):
        self.assert_defers(f"xtee {LOG}")

    def test_defers_a_quoted_mention(self):
        self.assert_defers(f"git commit -m 'fix: stop echo >> {LOG}'")
        self.assert_defers(f'git commit -m "fix: stop echo >> {LOG}"')

    def test_a_quoted_path_redirect_is_missed_by_design(self):
        # A quoted path is data to this scan; `handoff.py validate` in the
        # gate is the deterministic backstop.
        self.assert_defers(f"echo x >> '{LOG}'")

    def test_a_quote_pair_spanning_a_newline_still_denies(self):
        # Not stripped: a recoverable false positive, never a bypass.
        self.assert_denies(f"git commit -m 'line one\necho x >> {LOG}\nline three'")

    def test_defers_other_tools_and_malformed_input(self):
        self.assertIsNone(
            hook.decide(json.dumps({"tool_name": "Glob", "tool_input": {}}))
        )
        self.assertIsNone(hook.decide("not json"))
        self.assertIsNone(hook.decide(json.dumps({"tool_input": "not a dict"})))


class HeredocHandling(unittest.TestCase):
    def assert_denies(self, command):
        self.assertEqual(hook.decide(bash_payload(command)), hook.DENY_DECISION)

    def assert_defers(self, command):
        self.assertIsNone(hook.decide(bash_payload(command)))

    def test_a_sanctioned_append_with_a_forbidden_string_in_the_body_defers(self):
        self.assert_defers(
            "python3 scripts/handoff.py append rec <<'EOF'\n"
            f'{{"note": "echo x >> {LOG}"}}\n'
            "EOF"
        )

    def test_a_redirect_chained_after_the_heredoc_closer_denies(self):
        self.assert_denies(
            f"python3 scripts/handoff.py append rec <<'EOF'\n{{}}\nEOF\necho x >> {LOG}"
        )

    def test_a_quoted_heredoc_body_of_any_command_is_inert(self):
        self.assert_defers(f"cat <<'DOC'\necho x >> {LOG}\nDOC")

    def test_an_unquoted_heredoc_body_stays_scanned(self):
        self.assert_denies(f"cat <<DOC\necho x >> {LOG}\nDOC")

    def test_a_dash_heredoc_closes_on_a_tab_indented_delimiter(self):
        self.assert_defers(f"cat <<-'DOC'\n\techo x >> {LOG}\n\tDOC")

    def test_a_sanctioned_line_with_metacharacters_stays_scanned(self):
        self.assert_denies(f"python3 scripts/handoff.py latest x > {LOG}")


class CrossHookInterlock(unittest.TestCase):
    """A deny here can never override the allow hook: both deciders run over one sanctioned corpus."""

    def test_the_guard_defers_on_everything_the_allow_hook_allows(self):
        spec = importlib.util.spec_from_file_location(
            "handoff_allow", _HERE / "handoff-allow.py"
        )
        allow_hook = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(allow_hook)
        sanctioned = (
            "python3 scripts/handoff.py route",
            "python3 scripts/handoff.py latest review-feedback REQ-DEMO-001",
            "python3 scripts/handoff.py validate",
            "python3 scripts/handoff.py append rec <<'EOF'\n"
            f'{{"note": "echo x >> {LOG}"}}\n'
            "EOF",
            'python3 scripts/handoff.py append rec <<"EOF"\n{}\nEOF\n  \n',
        )
        for command in sanctioned:
            with self.subTest(command=command.splitlines()[0]):
                self.assertIsNotNone(allow_hook.decide(bash_payload(command)))
                self.assertIsNone(hook.decide(bash_payload(command)))


class ExitContract(unittest.TestCase):
    """The hook process only ever exits 0; DENY is stdout JSON, DEFER is silence."""

    def run_hook(self, stdin_text):
        return subprocess.run(
            [sys.executable, str(_HOOK)],
            input=stdin_text,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_deny_prints_the_decision_with_its_reason_and_exits_zero(self):
        result = self.run_hook(bash_payload(f"echo x >> {LOG}"))
        self.assertEqual(result.returncode, HOOK_EXIT)
        self.assertEqual(json.loads(result.stdout), json.loads(hook.DENY_DECISION))

    def test_defer_is_silent_and_exits_zero(self):
        result = self.run_hook(bash_payload("ls -la"))
        self.assertEqual(result.returncode, HOOK_EXIT)
        self.assertEqual(result.stdout, SILENCE)

    def test_a_nul_byte_on_stdin_defers(self):
        result = self.run_hook("\x00garbage")
        self.assertEqual(result.returncode, HOOK_EXIT)
        self.assertEqual(result.stdout, SILENCE)


if __name__ == "__main__":
    unittest.main()
