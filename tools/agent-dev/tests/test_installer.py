#!/usr/bin/env python3
"""Tests for install.sh: per-tool installs, the policy file's protection, and retired files."""

import os
import pathlib
import subprocess
import tempfile
import unittest

TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent
INSTALLER = TOOLS_DIR / "install.sh"
TIMEOUT_S = 60
ENGINE_FILES = (
    "agent-dev",
    "agent_dev.py",
    "agent_dev_config.py",
    "agent_dev_profiles.py",
    "Dockerfile",
    "open_weight_preflight.py",
)
# command -> (tool argument, files only that tool installs, files a tool once installed)
TOOLS = {
    "claude-dev": (
        "claude",
        ("claude_dev_scrub.py", "ide_preflight.py"),
        ("claude_dev_config.py",),
    ),
    "opencode-dev": ("opencode", (), ()),
}


class InstallerTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = pathlib.Path(tmp.name).resolve()
        self.bin = self.home / "bin"

    def run_installer(self, *args: str):
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "BIN": str(self.bin),
        }
        return subprocess.run(
            [str(INSTALLER), *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            check=False,
        )

    def data(self, command: str) -> pathlib.Path:
        return self.home / ".config" / command


class Apply(InstallerTests):
    def test_each_tool_installs_its_command_its_engine_and_its_own_files(self):
        for command, (tool, own, _) in TOOLS.items():
            with self.subTest(command=command):
                result = self.run_installer(tool, "apply")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((self.bin / command).is_file())
                for name in (*ENGINE_FILES, *own, f"{command}.toml"):
                    self.assertTrue((self.data(command) / name).is_file(), name)

    def test_the_engine_is_executable_and_the_modules_are_not(self):
        self.run_installer("claude", "apply")
        self.assertTrue(os.access(self.data("claude-dev") / "agent-dev", os.X_OK))
        self.assertFalse(os.access(self.data("claude-dev") / "agent_dev.py", os.X_OK))

    def test_installing_one_tool_leaves_the_other_untouched(self):
        self.run_installer("claude", "apply")
        self.run_installer("opencode", "apply")
        self.assertFalse((self.data("claude-dev") / "opencode-dev.toml").exists())
        self.assertFalse((self.data("opencode-dev") / "claude_dev_scrub.py").exists())
        self.assertFalse((self.data("opencode-dev") / "ide_preflight.py").exists())

    def test_an_installed_command_answers_help(self):
        self.run_installer("opencode", "apply")
        result = subprocess.run(
            [str(self.bin / "opencode-dev"), "help"],
            env={
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                "HOME": str(self.home),
            },
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("opencode-dev [options]", result.stdout)

    def test_an_existing_policy_file_is_kept(self):
        self.run_installer("opencode", "apply")
        policy = self.data("opencode-dev") / "opencode-dev.toml"
        policy.write_text("# the operator's own\n")
        result = self.run_installer("opencode", "apply")
        self.assertIn("kept existing", result.stdout)
        self.assertEqual(policy.read_text(), "# the operator's own\n")

    def test_retired_files_an_earlier_version_installed_are_removed(self):
        for command, (tool, _, retired) in TOOLS.items():
            with self.subTest(command=command):
                self.data(command).mkdir(parents=True)
                for name in retired:
                    (self.data(command) / name).write_text("old")
                result = self.run_installer(tool, "apply")
                self.assertEqual(result.returncode, 0, result.stderr)
                for name in retired:
                    self.assertFalse((self.data(command) / name).exists(), name)
                    self.assertIn(
                        f"removed retired: {self.data(command) / name}", result.stdout
                    )


class Check(InstallerTests):
    def test_a_fresh_home_reports_everything_missing(self):
        result = self.run_installer("claude", "check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("missing", result.stdout)
        self.assertNotIn("identical", result.stdout)

    def test_after_apply_every_managed_file_reads_identical(self):
        self.run_installer("opencode", "apply")
        out = self.run_installer("opencode", "check").stdout
        self.assertEqual(out.count("identical"), 8)
        self.assertNotIn("missing", out)

    def test_check_changes_nothing_and_reports_a_retired_file(self):
        self.data("claude-dev").mkdir(parents=True)
        stale = self.data("claude-dev") / "claude_dev_config.py"
        stale.write_text("old")
        out = self.run_installer("claude", "check").stdout
        self.assertIn("retired (removed on apply)", out)
        self.assertTrue(stale.exists())
        self.assertFalse(self.bin.exists())

    def test_a_policy_this_version_refuses_is_reported_before_apply(self):
        self.run_installer("claude", "apply")
        (self.data("claude-dev") / "claude-dev.toml").write_text(
            '[egress]\nallow = ["a.com"]\n[no-such-table]\nkey = 1\n'
        )
        out = self.run_installer("claude", "check").stdout
        self.assertIn("REFUSED by this version", out)
        self.assertIn("[no-such-table]", out)


class ResetConfig(InstallerTests):
    def test_the_old_policy_is_kept_as_bak_and_the_shipped_one_restored(self):
        self.run_installer("opencode", "apply")
        policy = self.data("opencode-dev") / "opencode-dev.toml"
        policy.write_text("# edited\n")
        result = self.run_installer("opencode", "reset-config")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(policy.with_suffix(".toml.bak").read_text(), "# edited\n")
        self.assertEqual(
            policy.read_text(), (TOOLS_DIR / "opencode-dev.toml").read_text()
        )


class Usage(InstallerTests):
    def test_a_missing_or_unknown_tool_prints_usage_and_exits_two(self):
        for args in ((), ("nonesuch",), ("claude", "bogus-mode")):
            with self.subTest(args=args):
                result = self.run_installer(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage: install.sh", result.stderr)


if __name__ == "__main__":
    unittest.main()
