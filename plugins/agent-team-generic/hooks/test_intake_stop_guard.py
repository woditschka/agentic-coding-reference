#!/usr/bin/env python3
"""Tests for intake-stop-guard.py (stdlib only).

Run: python3 .claude/hooks/test_intake_stop_guard.py

Pins the narrow-block contract: exit 2 only when route decides `dispatch`
with rule `intake-ready` on a live pipeline; every malfunction — malformed
stdin, missing log or script, route failing or emitting non-JSON — and
every other route decision exits 0 (this Stop backstop fails OPEN, unlike
the deny-by-default PreToolUse guards). `stop_hook_active` always allows,
so a block never traps a session.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HOOK = _HERE / "intake-stop-guard.py"


def _load():
    spec = importlib.util.spec_from_file_location("intake_stop_guard", _HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hook = _load()

STOP = json.dumps({"hook_event_name": "Stop", "stop_hook_active": False})
STOP_ACTIVE = json.dumps({"hook_event_name": "Stop", "stop_hook_active": True})


class _Proc:
    def __init__(self, returncode=0, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


def runner_for(decision=None, returncode=0, stdout=None, raises=None):
    def runner(*_args, **_kwargs):
        if raises is not None:
            raise raises
        if stdout is not None:
            return _Proc(returncode, stdout)
        return _Proc(returncode, json.dumps(decision or {}))

    return runner


class _Project:
    """A temp project dir with an optional handoff log and handoff script."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / ".scratch").mkdir()
        (root / ".scratch" / "handoff.jsonl").write_text("{}\n")
        (root / "scripts").mkdir()
        (root / "scripts" / "handoff.py").write_text("# stub\n")
        return str(root)

    def __exit__(self, *exc):
        self._tmp.cleanup()


class Blocks(unittest.TestCase):
    def test_intake_ready_dispatch_blocks(self):
        with _Project() as proj:
            runner = runner_for({"decision": "dispatch", "rule": "intake-ready"})
            self.assertEqual(hook.decide(STOP, proj, runner), 2)

    def test_stop_hook_active_always_allows(self):
        with _Project() as proj:
            runner = runner_for({"decision": "dispatch", "rule": "intake-ready"})
            self.assertEqual(hook.decide(STOP_ACTIVE, proj, runner), 0)


class Allows(unittest.TestCase):
    def test_other_dispatch_rules_allow(self):
        with _Project() as proj:
            for rule in ("build-pass-review", "consultation-dispatch", "gate-failure"):
                runner = runner_for({"decision": "dispatch", "rule": rule})
                self.assertEqual(hook.decide(STOP, proj, runner), 0)

    def test_non_dispatch_decisions_allow(self):
        with _Project() as proj:
            for decision in ("blocked", "escalate"):
                runner = runner_for({"decision": decision, "rule": "intake-ready"})
                self.assertEqual(hook.decide(STOP, proj, runner), 0)

    def test_missing_log_or_script_allows(self):
        with tempfile.TemporaryDirectory() as bare:
            runner = runner_for({"decision": "dispatch", "rule": "intake-ready"})
            self.assertEqual(hook.decide(STOP, bare, runner), 0)

    def test_empty_project_dir_allows(self):
        runner = runner_for({"decision": "dispatch", "rule": "intake-ready"})
        self.assertEqual(hook.decide(STOP, "", runner), 0)


class FailsOpen(unittest.TestCase):
    def test_malformed_stdin_allows(self):
        with _Project() as proj:
            runner = runner_for({"decision": "dispatch", "rule": "intake-ready"})
            self.assertEqual(hook.decide("not json", proj, runner), 0)

    def test_route_nonzero_exit_allows(self):
        with _Project() as proj:
            runner = runner_for(
                {"decision": "dispatch", "rule": "intake-ready"}, returncode=1
            )
            self.assertEqual(hook.decide(STOP, proj, runner), 0)

    def test_route_non_json_output_allows(self):
        with _Project() as proj:
            runner = runner_for(stdout="route exploded")
            self.assertEqual(hook.decide(STOP, proj, runner), 0)

    def test_route_raising_allows(self):
        with _Project() as proj:
            runner = runner_for(
                raises=subprocess.TimeoutExpired(cmd="route", timeout=30)
            )
            self.assertEqual(hook.decide(STOP, proj, runner), 0)


class EndToEnd(unittest.TestCase):
    def test_block_prints_reason_on_stderr(self):
        # No .scratch in the env's project dir: the hook allows and prints
        # nothing; the blocking path is covered above via decide().
        proc = subprocess.run(
            [sys.executable or "python3", str(_HOOK)],
            input=STOP,
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": ""},
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stderr, "")


if __name__ == "__main__":
    unittest.main()
