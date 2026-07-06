#!/usr/bin/env python3
"""Tests for refresh-settings.py (stdlib only).

Run: python3 harness/test_refresh_settings.py

Pins the ensure-present contract: the env flag and each delivered hook's
matcher are added when absent; project keys, overridden values, and
project-authored matchers are never rewritten; a hook not delivered into the
tree registers no matcher; malformed targets are skipped, never a traceback.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPT = _HERE / "refresh-settings.py"
_TEMPLATE = _HERE / "init/core/.claude/settings.json"

HOOKS = ("sendmessage-continue-only.py", "handoff-allow.py", "handoff-log-guard.py")

EXPECTED_PAIRS = {
    ("SendMessage", "sendmessage-continue-only.py"),
    ("Bash", "handoff-allow.py"),
    ("Write|Edit|MultiEdit|NotebookEdit", "handoff-log-guard.py"),
    ("Bash", "handoff-log-guard.py"),
}


def registered_pairs(settings):
    return {
        (entry["matcher"], hook["command"].rsplit("/", 1)[-1].rstrip('"'))
        for entry in settings.get("hooks", {}).get("PreToolUse", [])
        for hook in entry["hooks"]
    }


class RefreshSettingsTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / ".claude").mkdir()
        self.settings = self.root / ".claude" / "settings.json"

    def tearDown(self):
        self.td.cleanup()

    def deliver_hooks(self):
        hooks_dir = self.root / ".claude" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        for name in HOOKS:
            (hooks_dir / name).write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    def run_refresh(self):
        return subprocess.run(
            [sys.executable, str(_SCRIPT), str(self.settings), str(_TEMPLATE), str(self.root)],
            capture_output=True, text=True, check=False,
        )

    def read_settings(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))

    def test_env_flag_and_delivered_hook_matchers_ensured_project_key_kept(self):
        self.deliver_hooks()
        self.settings.write_text('{\n  "env": { "MY_VAR": "keep" }\n}\n', encoding="utf-8")
        self.assertEqual(self.run_refresh().returncode, 0)
        settings = self.read_settings()
        self.assertEqual(settings["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"], "1")
        self.assertEqual(settings["env"]["MY_VAR"], "keep")
        self.assertEqual(registered_pairs(settings), EXPECTED_PAIRS)

    def test_idempotent(self):
        self.deliver_hooks()
        self.settings.write_text("{}\n", encoding="utf-8")
        self.run_refresh()
        result = self.run_refresh()
        self.assertEqual(result.stdout.strip(), "settings: no change")

    def test_no_delivered_hooks_means_no_matcher(self):
        # Marketplace-like tree: hooks ship in the plugin, not .claude/hooks/.
        self.settings.write_text("{}\n", encoding="utf-8")
        self.run_refresh()
        settings = self.read_settings()
        self.assertEqual(settings["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"], "1")
        self.assertNotIn("hooks", settings)

    def test_project_overridden_flag_not_clobbered(self):
        self.settings.write_text(
            '{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "0" } }\n', encoding="utf-8")
        self.run_refresh()
        self.assertEqual(
            self.read_settings()["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"], "0")

    def test_legacy_sh_matcher_is_kept_and_the_py_hook_still_registers(self):
        # Ensure-present never removes: the stale .sh matcher lingers inert
        # (a human or the advisory pass prunes it) while the delivered .py
        # hook gains its own registration — an upgrade must wire the new
        # hook even on a settings file that still carries the old one.
        self.deliver_hooks()
        legacy = {
            "hooks": {"PreToolUse": [{
                "matcher": "Bash",
                "hooks": [{"type": "command",
                           "command": 'bash "${CLAUDE_PROJECT_DIR}/.claude/hooks/handoff-allow.sh"'}],
            }]}
        }
        self.settings.write_text(json.dumps(legacy), encoding="utf-8")
        self.run_refresh()
        pairs = registered_pairs(self.read_settings())
        self.assertIn(("Bash", "handoff-allow.sh"), pairs)
        self.assertEqual(pairs - {("Bash", "handoff-allow.sh")}, EXPECTED_PAIRS)

    def test_unparseable_target_skipped_gracefully(self):
        self.settings.write_text("{ not json", encoding="utf-8")
        result = self.run_refresh()
        self.assertEqual(result.returncode, 0)
        self.assertIn("skipped", result.stdout)

    def test_missing_target_created_with_harness_keys(self):
        self.deliver_hooks()
        result = self.run_refresh()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(registered_pairs(self.read_settings()), EXPECTED_PAIRS)


if __name__ == "__main__":
    unittest.main()
