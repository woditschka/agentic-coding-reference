#!/usr/bin/env python3
"""Tests for the command scripts: where one may run from, which engine it runs, and its help."""

import os
import shutil
import unittest

from tests.support import COMMANDS, TOOLS_DIR, CommandFixture

FAKE_ENGINE_MARK = "FAKE-ENGINE-RAN"
FAKE_ENGINE = f"#!/usr/bin/env bash\necho {FAKE_ENGINE_MARK}\n"
POISONED_MODULE = "raise SystemExit('the installed module ran')\n"


class InProjectCopy(CommandFixture):
    """A copy inside the project the session mounts read-write could be rewritten by it."""

    def copy_checkout(self, command: str):
        tools = self.project / "tools"
        tools.mkdir(exist_ok=True)
        for name in (command, "agent-dev", "agent_dev.py", "agent_dev_config.py"):
            shutil.copy(TOOLS_DIR / name, tools / name)
        shutil.copy(
            TOOLS_DIR / "agent_dev_profiles.py", tools / "agent_dev_profiles.py"
        )
        return tools / command

    def test_a_checkout_inside_the_project_is_refused(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.run_script(self.copy_checkout(command), "access")
                self.assert_refused(result, "refusing to run the copy at")

    def test_the_command_alone_inside_the_project_is_refused_by_the_installed_engine(
        self,
    ):
        # No engine beside it, so the installed one runs, and it checks where
        # the command file lives.
        for command in COMMANDS:
            with self.subTest(command=command):
                self.install(command)
                copy = self.project / command
                shutil.copy(TOOLS_DIR / command, copy)
                result = self.run_script(copy, "access")
                self.assert_refused(
                    result, "refusing to run the copy at", str(self.project)
                )

    def test_the_refusal_names_the_installer_with_its_tool(self):
        for command in COMMANDS:
            tool = command.removesuffix("-dev")
            with self.subTest(command=command):
                result = self.run_script(self.copy_checkout(command), "access")
                self.assertIn(f"tools/agent-dev/install.sh {tool})", result.stderr)

    def test_help_answers_before_the_check_as_the_usage_reference_must(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.run_script(self.copy_checkout(command), "help")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"{command} [options]", result.stdout)


class SymlinkedCommand(CommandFixture):
    """A link to a command is followed: the checks read where the file really lives."""

    def test_a_link_to_a_copy_inside_the_project_is_refused(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                self.install(command)
                target = self.project / command
                shutil.copy(TOOLS_DIR / command, target)
                link = self.tmp / f"link-{command}"
                link.symlink_to(target)
                result = self.run_script(link, "access")
                self.assert_refused(
                    result, "refusing to run the copy at", str(self.project)
                )

    def test_a_relative_link_is_followed_too(self):
        self.install("claude-dev")
        target = self.project / "claude-dev"
        shutil.copy(TOOLS_DIR / "claude-dev", target)
        link = self.tmp / "rel-link"
        link.symlink_to(os.path.relpath(target, self.tmp))
        self.assert_refused(
            self.run_script(link, "access"), "refusing to run the copy at"
        )

    def test_help_through_a_link_prints_the_header_of_the_file_it_points_at(self):
        self.install("opencode-dev")
        link = self.tmp / "named-differently"
        link.symlink_to(self.bin / "opencode-dev")
        result = self.run_script(link, "help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("opencode-dev [options]", result.stdout)


class EngineChoice(CommandFixture):
    def fake_engine(self, command: str) -> None:
        engine = self.data[command] / "agent-dev"
        engine.write_text(FAKE_ENGINE)
        engine.chmod(0o755)

    def test_a_source_checkout_runs_its_own_engine_not_an_installed_one(self):
        # The single launcher always ran itself; a silent switch to an
        # installed engine would exercise the wrong code.
        for command in COMMANDS:
            with self.subTest(command=command):
                self.fake_engine(command)
                result = self.access(command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn(FAKE_ENGINE_MARK, result.stdout)

    def test_a_source_engine_runs_the_modules_beside_it_not_installed_ones(self):
        # An engine that read another version's modules would mix two releases.
        for command in COMMANDS:
            with self.subTest(command=command):
                (self.data[command] / "agent_dev.py").write_text(POISONED_MODULE)
                result = self.access(command)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_an_installed_command_runs_the_engine_in_its_data_dir(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                installed = self.install(command)
                self.fake_engine(command)
                result = self.run_script(installed, "access")
                self.assertIn(FAKE_ENGINE_MARK, result.stdout)

    def test_an_installed_command_prints_its_plan(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.run_script(self.install(command), "access")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("the session container's bind mounts", result.stdout)

    def test_no_engine_anywhere_names_both_places_it_looked(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                alone = self.bin / command
                shutil.copy(TOOLS_DIR / command, alone)
                result = self.run_script(alone, "access")
                self.assert_refused(
                    result, "missing agent-dev", str(alone), str(self.data[command])
                )

    def test_the_engine_refuses_to_run_without_a_command(self):
        result = self.run_script(TOOLS_DIR / "agent-dev", "access")
        self.assert_refused(result, "run through a command")


if __name__ == "__main__":
    unittest.main()
