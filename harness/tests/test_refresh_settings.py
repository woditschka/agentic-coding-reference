#!/usr/bin/env python3
"""Pin the ensure-present contract of refresh-settings.py."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import ROOT

_SCRIPT = ROOT / "refresh-settings.py"
_TEMPLATE = ROOT / "init/core/.claude/settings.json"

AGENT_TEAMS_FLAG = "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"
AGENT_TEAMS_ENABLED = "1"
PROJECT_OVERRIDDEN_FLAG = "0"
NO_CHANGE_REPORT = "settings: no change"
PRE_TOOL_USE = "PreToolUse"
STOP = "Stop"

STOP_GUARD_HOOK = "intake-stop-guard.py"
HOOKS = (
    "sendmessage-continue-only.py",
    "handoff-allow.py",
    "handoff-log-guard.py",
    STOP_GUARD_HOOK,
)
LEGACY_SH_HOOK = "handoff-allow.sh"

EXPECTED_PAIRS = {
    ("SendMessage", "sendmessage-continue-only.py"),
    ("Bash", "handoff-allow.py"),
    ("Write|Edit|MultiEdit|NotebookEdit", "handoff-log-guard.py"),
    ("Bash", "handoff-log-guard.py"),
}

SOME_PROJECT_KEY = "MY_VAR"
SOME_PROJECT_VALUE = "keep"
SOME_HOOK_BODY = "#!/usr/bin/env python3\n"


def hook_command(name: str, runner: str = "python3") -> str:
    return f'{runner} "${{CLAUDE_PROJECT_DIR}}/.claude/hooks/{name}"'


def hook_entry(matcher: str, *names: str) -> dict:
    return {
        "matcher": matcher,
        "hooks": [{"type": "command", "command": hook_command(n)} for n in names],
    }


def registered_pairs(settings: dict) -> list[tuple[str, str]]:
    return [
        (entry["matcher"], hook["command"].rsplit("/", 1)[-1].rstrip('"'))
        for entry in settings.get("hooks", {}).get(PRE_TOOL_USE, [])
        for hook in entry["hooks"]
    ]


class EnsurePresentRefresh(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        (self.root / ".claude").mkdir()
        self.settings = self.root / ".claude" / "settings.json"

    def deliver_hooks(self, names=HOOKS):
        hooks_dir = self.root / ".claude" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        for name in names:
            (hooks_dir / name).write_text(SOME_HOOK_BODY, encoding="utf-8")

    def write_settings(self, settings: dict):
        self.settings.write_text(json.dumps(settings) + "\n", encoding="utf-8")

    def run_refresh(self, template: Path = _TEMPLATE):
        return subprocess.run(
            [
                sys.executable,
                str(_SCRIPT),
                str(self.settings),
                str(template),
                str(self.root),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def read_settings(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))

    def test_env_flag_and_delivered_hook_matchers_ensured_project_key_kept(self):
        self.deliver_hooks()
        self.write_settings({"env": {SOME_PROJECT_KEY: SOME_PROJECT_VALUE}})
        self.assertEqual(self.run_refresh().returncode, 0)
        settings = self.read_settings()
        self.assertEqual(settings["env"][AGENT_TEAMS_FLAG], AGENT_TEAMS_ENABLED)
        self.assertEqual(settings["env"][SOME_PROJECT_KEY], SOME_PROJECT_VALUE)
        self.assertEqual(set(registered_pairs(settings)), EXPECTED_PAIRS)

    def test_stop_event_hook_registers_when_delivered(self):
        self.deliver_hooks()
        self.write_settings({})
        self.run_refresh()
        stop = self.read_settings()["hooks"][STOP]
        commands = [h["command"] for e in stop for h in e["hooks"]]
        self.assertTrue(any(STOP_GUARD_HOOK in c for c in commands))

    def test_stop_hook_not_registered_when_not_delivered(self):
        self.deliver_hooks(tuple(h for h in HOOKS if h != STOP_GUARD_HOOK))
        self.write_settings({})
        self.run_refresh()
        self.assertNotIn(STOP, self.read_settings().get("hooks", {}))

    def test_a_second_refresh_reports_no_change(self):
        self.deliver_hooks()
        self.write_settings({})
        self.run_refresh()
        result = self.run_refresh()
        self.assertEqual(result.stdout.strip(), NO_CHANGE_REPORT)

    def test_no_delivered_hooks_means_no_matcher(self):
        self.write_settings({})
        self.run_refresh()
        settings = self.read_settings()
        self.assertEqual(settings["env"][AGENT_TEAMS_FLAG], AGENT_TEAMS_ENABLED)
        self.assertNotIn("hooks", settings)

    def test_project_overridden_flag_not_clobbered(self):
        self.write_settings({"env": {AGENT_TEAMS_FLAG: PROJECT_OVERRIDDEN_FLAG}})
        self.run_refresh()
        self.assertEqual(
            self.read_settings()["env"][AGENT_TEAMS_FLAG], PROJECT_OVERRIDDEN_FLAG
        )

    def test_partial_multi_hook_entry_appends_only_missing_hooks(self):
        # Appending the whole two-hook entry would register the first hook
        # twice, and it would run twice per tool call.
        self.deliver_hooks()
        template = self.root / "template.json"
        template.write_text(
            json.dumps(
                {
                    "hooks": {
                        PRE_TOOL_USE: [
                            hook_entry(
                                "Bash", "handoff-allow.py", "handoff-log-guard.py"
                            )
                        ]
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.write_settings(
            {"hooks": {PRE_TOOL_USE: [hook_entry("Bash", "handoff-allow.py")]}}
        )
        result = self.run_refresh(template)
        self.assertEqual(result.returncode, 0)
        pairs = registered_pairs(self.read_settings())
        self.assertEqual(pairs.count(("Bash", "handoff-allow.py")), 1)
        self.assertEqual(pairs.count(("Bash", "handoff-log-guard.py")), 1)

    def test_legacy_sh_matcher_is_kept_and_the_py_hook_still_registers(self):
        # Ensure-present never removes: the stale matcher lingers inert while
        # the delivered hook still gains its own registration.
        self.deliver_hooks()
        legacy_entry = {
            "matcher": "Bash",
            "hooks": [
                {"type": "command", "command": hook_command(LEGACY_SH_HOOK, "bash")}
            ],
        }
        self.write_settings({"hooks": {PRE_TOOL_USE: [legacy_entry]}})
        self.run_refresh()
        pairs = set(registered_pairs(self.read_settings()))
        self.assertIn(("Bash", LEGACY_SH_HOOK), pairs)
        self.assertEqual(pairs - {("Bash", LEGACY_SH_HOOK)}, EXPECTED_PAIRS)

    def test_unparseable_target_skipped_gracefully(self):
        self.settings.write_text("{ not json", encoding="utf-8")
        result = self.run_refresh()
        self.assertEqual(result.returncode, 0)
        self.assertIn("skipped", result.stdout)

    def test_missing_target_created_with_harness_keys(self):
        self.deliver_hooks()
        result = self.run_refresh()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(set(registered_pairs(self.read_settings())), EXPECTED_PAIRS)


if __name__ == "__main__":
    unittest.main()
