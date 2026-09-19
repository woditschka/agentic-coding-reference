#!/usr/bin/env python3
"""The intake stop guard: the intake-ready dispatch blocks once, and every malfunction allows."""

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

ALLOW = 0
BLOCK = 2
SOME_TIMEOUT = 30

STOP = json.dumps({"hook_event_name": "Stop", "stop_hook_active": False})
STOP_ACTIVE = json.dumps({"hook_event_name": "Stop", "stop_hook_active": True})
INTAKE_READY_DISPATCH = {"decision": "dispatch", "rule": "intake-ready"}


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
    """A temp project dir with a handoff log and a handoff script."""

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
    def test_the_intake_ready_dispatch_blocks(self):
        with _Project() as proj:
            runner = runner_for(INTAKE_READY_DISPATCH)
            self.assertEqual(hook.decide(STOP, proj, runner), BLOCK)

    def test_an_active_stop_hook_always_allows(self):
        with _Project() as proj:
            runner = runner_for(INTAKE_READY_DISPATCH)
            self.assertEqual(hook.decide(STOP_ACTIVE, proj, runner), ALLOW)


class Allows(unittest.TestCase):
    def test_every_other_dispatch_rule_allows(self):
        with _Project() as proj:
            for rule in ("build-pass-review", "consultation-dispatch", "gate-failure"):
                runner = runner_for({"decision": "dispatch", "rule": rule})
                self.assertEqual(hook.decide(STOP, proj, runner), ALLOW)

    def test_a_non_dispatch_decision_allows(self):
        with _Project() as proj:
            for decision in ("blocked", "escalate"):
                runner = runner_for({"decision": decision, "rule": "intake-ready"})
                self.assertEqual(hook.decide(STOP, proj, runner), ALLOW)

    def test_a_project_without_the_log_or_the_script_allows(self):
        with tempfile.TemporaryDirectory() as bare:
            runner = runner_for(INTAKE_READY_DISPATCH)
            self.assertEqual(hook.decide(STOP, bare, runner), ALLOW)

    def test_an_empty_project_dir_allows(self):
        runner = runner_for(INTAKE_READY_DISPATCH)
        self.assertEqual(hook.decide(STOP, "", runner), ALLOW)


class FailsOpen(unittest.TestCase):
    def test_malformed_stdin_allows(self):
        with _Project() as proj:
            runner = runner_for(INTAKE_READY_DISPATCH)
            self.assertEqual(hook.decide("not json", proj, runner), ALLOW)

    def test_a_nonzero_route_exit_allows(self):
        with _Project() as proj:
            runner = runner_for(INTAKE_READY_DISPATCH, returncode=1)
            self.assertEqual(hook.decide(STOP, proj, runner), ALLOW)

    def test_non_json_route_output_allows(self):
        with _Project() as proj:
            runner = runner_for(stdout="route exploded")
            self.assertEqual(hook.decide(STOP, proj, runner), ALLOW)

    def test_a_raising_route_allows(self):
        with _Project() as proj:
            runner = runner_for(
                raises=subprocess.TimeoutExpired(cmd="route", timeout=SOME_TIMEOUT)
            )
            self.assertEqual(hook.decide(STOP, proj, runner), ALLOW)


class EndToEnd(unittest.TestCase):
    def test_an_unset_project_dir_allows_silently(self):
        proc = subprocess.run(
            [sys.executable or "python3", str(_HOOK)],
            input=STOP,
            capture_output=True,
            text=True,
            env={"CLAUDE_PROJECT_DIR": ""},
            timeout=SOME_TIMEOUT,
            check=False,
        )
        self.assertEqual(proc.returncode, ALLOW)
        self.assertEqual(proc.stderr, "")


if __name__ == "__main__":
    unittest.main()
