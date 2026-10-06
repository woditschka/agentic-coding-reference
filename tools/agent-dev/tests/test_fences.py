#!/usr/bin/env python3
"""Tests for the host fences: what a project or a mount may be, read through links and `..`."""

import pathlib
import subprocess
import unittest

from tests.support import COMMANDS, TOOLS_DIR, CommandFixture

HOLDS_COMMANDS = "holds the commands that run on the host"


class ProjectFences(CommandFixture):
    """The project mounts read-write, so one that is, or contains, a host-run path hands it over."""

    def test_a_project_containing_a_data_dir_is_refused_for_both_tools(self):
        self.at_default_homes()
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.access(command, cwd=self.home / ".config")
                self.assert_refused(result, "does not contain")

    def test_a_project_inside_the_other_tools_data_dir_is_refused(self):
        result = self.access("claude-dev", cwd=self.data["opencode-dev"])
        self.assert_refused(result, "not inside")

    def test_a_project_inside_another_tools_protected_path_is_refused(self):
        config = self.home / ".config" / "opencode"
        config.mkdir(parents=True)
        result = self.access("claude-dev", cwd=config)
        self.assert_refused(result, "not inside ~/.config/opencode")

    def test_a_project_that_is_or_contains_the_installed_commands_is_refused(self):
        bin_dir = self.home / ".local" / "bin"
        bin_dir.mkdir(parents=True)
        for command in COMMANDS:
            with self.subTest(command=command):
                self.assert_refused(
                    self.access(command, cwd=bin_dir), "not inside ~/.local/bin"
                )
                self.assert_refused(
                    self.access(command, cwd=self.home / ".local"),
                    "does not contain ~/.local/bin",
                )

    def test_the_filesystem_root_is_not_a_project(self):
        # bash 3.2 may put a here-document's temp file in the working
        # directory; where / is not writable the launcher stops before the guard.
        probe = subprocess.run(
            ["bash", "-c", "cat <<EOF >/dev/null\nx\nEOF"],
            cwd="/",
            env=self.env(),
            capture_output=True,
            check=False,
        )
        if probe.returncode != 0 or probe.stderr:
            self.skipTest(
                "this environment cannot create here-document temp files in /"
            )
        for command in COMMANDS:
            with self.subTest(command=command):
                self.assert_refused(self.access(command, cwd="/"), "filesystem root")

    def test_a_project_containing_only_absent_paths_is_accepted(self):
        # Nothing absent is handed over, so the containing rule asks for existence.
        parent = self.home / ".config"
        parent.mkdir()
        for command in COMMANDS:
            with self.subTest(command=command):
                self.assertEqual(self.access(command, cwd=parent).returncode, 0)


class DataDirFences(CommandFixture):
    """No session mounts any tool's data dir: it holds host-run code, the login and all state."""

    def test_the_other_tools_data_dir_is_refused_read_write_and_read_only(self):
        for command in COMMANDS:
            other = next(c for c in COMMANDS if c != command)
            (self.data[other] / "auth").mkdir(exist_ok=True)
            for flag in ("--rw", "--ro"):
                for target in (self.data[other], self.data[other] / "auth"):
                    with self.subTest(command=command, flag=flag, target=target.name):
                        self.assert_refused(
                            self.access(command, flag, str(target)),
                            f"the data directory of {other}",
                        )

    def test_a_path_containing_the_other_tools_data_dir_is_refused(self):
        result = self.access("opencode-dev", "--ro", str(self.tmp))
        self.assert_refused(result, "it contains")

    def test_the_default_location_is_fenced_when_the_variable_points_elsewhere(self):
        default = self.home / ".config" / "opencode-dev"
        default.mkdir(parents=True)
        for target in (default, self.data["opencode-dev"]):
            with self.subTest(target=target):
                self.assert_refused(
                    self.access("claude-dev", "--rw", str(target)), "opencode-dev"
                )

    def test_the_default_location_is_fenced_when_no_variable_is_set(self):
        default = self.home / ".config" / "claude-dev"
        default.mkdir(parents=True)
        env = self.env()
        del env["CLAUDE_DEV_HOME"]
        result = self.access("opencode-dev", "--ro", str(default), env=env)
        self.assert_refused(result, "the data directory of claude-dev")


class ResolvedMounts(CommandFixture):
    """A fence reads physical paths: a link or a trailing `..` must not walk around it."""

    def setUp(self):
        super().setUp()
        self.at_default_homes()
        (self.home / ".config" / "git").mkdir()

    def test_a_trailing_dot_dot_is_resolved_before_the_fence_reads_it(self):
        # ~/.config/git/.. is ~/.config, which contains both data dirs.
        for command in COMMANDS:
            for flag in ("--rw", "--ro"):
                with self.subTest(command=command, flag=flag):
                    result = self.access(
                        command, flag, str(self.home / ".config/git/..")
                    )
                    self.assert_refused(result, "may not mount", "it contains")

    def test_a_link_as_the_last_component_is_followed(self):
        for command in COMMANDS:
            link = self.tmp / f"link-{command}"
            link.symlink_to(self.data[command])
            for flag in ("--rw", "--ro"):
                with self.subTest(command=command, flag=flag):
                    self.assert_refused(
                        self.access(command, flag, str(link)), "may not mount"
                    )

    def test_a_link_to_a_protected_host_path_is_followed(self):
        target = self.home / ".claude"
        target.mkdir()
        link = self.tmp / "claude-link"
        link.symlink_to(target)
        for command in COMMANDS:
            with self.subTest(command=command):
                self.assert_refused(
                    self.access(command, "--rw", str(link)), "~/.claude decides how"
                )

    def test_a_link_to_the_installed_commands_is_followed(self):
        bin_dir = self.home / ".local" / "bin"
        bin_dir.mkdir(parents=True)
        link = self.tmp / "bin-link"
        link.symlink_to(bin_dir)
        for command in COMMANDS:
            with self.subTest(command=command):
                self.assert_refused(
                    self.access(command, "--rw", str(link)), HOLDS_COMMANDS
                )

    def test_a_mount_that_passes_is_listed_by_its_physical_path(self):
        target = self.tmp / "assets"
        target.mkdir()
        link = self.tmp / "assets-link"
        link.symlink_to(target)
        result = self.access("claude-dev", "--ro", str(link))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"ro  {target}", result.stdout)
        self.assertNotIn("assets-link", result.stdout)


class LinkedFile(CommandFixture):
    """A link to a file is seen where the link names it; the checks judge its target."""

    def link_to(self, target: pathlib.Path) -> pathlib.Path:
        link = self.tmp / "statusline.sh"
        link.symlink_to(target)
        return link

    def test_the_session_sees_the_file_at_the_links_own_path(self):
        real = self.tmp / "dotfiles" / "statusline-real.sh"
        real.parent.mkdir()
        real.write_text("#!/bin/sh\n")
        link = self.link_to(real)
        result = self.access("claude-dev", "--ro", str(link))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"ro  {link}", result.stdout)
        self.assertNotIn("statusline-real.sh", result.stdout)

    def test_a_link_into_a_data_dir_is_refused_by_its_target(self):
        inside = self.data["claude-dev"] / "host-id"
        inside.write_text("x\n")
        link = self.link_to(inside)
        for command in COMMANDS:
            with self.subTest(command=command):
                self.assert_refused(
                    self.access(command, "--ro", str(link)), "may not mount"
                )


def folds_letter_case(directory: pathlib.Path) -> bool:
    """Tell whether the filesystem holding a directory opens a name in another letter case."""
    probe = directory / "CaseProbe"
    probe.mkdir()
    try:
        return (directory / "caseprobe").exists()
    finally:
        probe.rmdir()


class LetterCase(CommandFixture):
    """Where the filesystem folds letter case, another spelling names the same path."""

    def setUp(self):
        super().setUp()
        if not folds_letter_case(self.tmp):
            self.skipTest("this filesystem distinguishes letter case")
        (self.home / ".claude").mkdir()

    def test_a_protected_path_spelled_in_another_case_is_refused_writable(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.access(command, "--rw", str(self.home / ".CLAUDE"))
                self.assert_refused(result, "may not mount", "~/.claude")

    def test_a_data_dir_spelled_in_another_case_is_refused(self):
        data = self.data["claude-dev"]
        other_spelling = data.parent / data.name.upper()
        result = self.access("opencode-dev", "--ro", str(other_spelling))
        self.assert_refused(result, "the data directory of claude-dev")

    def test_a_project_entered_in_another_case_is_still_the_protected_path(self):
        # A shell hands its own spelling of the directory down as PWD.
        typed = self.home / ".CLAUDE"
        result = self.access("claude-dev", cwd=typed, env=self.env(PWD=str(typed)))
        self.assert_refused(result, "not inside ~/.claude")

    def test_a_protected_file_spelled_in_another_case_is_refused_writable(self):
        (self.home / ".claude.json").write_text("{}")
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.access(command, "--rw", str(self.home / ".CLAUDE.JSON"))
                self.assert_refused(result, "may not mount", "~/.claude.json")

    def test_a_file_is_listed_by_the_name_its_directory_holds(self):
        (self.tmp / "Notes.txt").write_text("x\n")
        result = self.access("claude-dev", "--ro", str(self.tmp / "NOTES.TXT"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Notes.txt", result.stdout)
        self.assertNotIn("NOTES.TXT", result.stdout)


class ConfigFile(CommandFixture):
    """Claude Code's own config file decides how it runs on the host, like its config directory."""

    def test_no_command_mounts_it_writable(self):
        (self.home / ".claude.json").write_text("{}")
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.access(command, "--rw", str(self.home / ".claude.json"))
                self.assert_refused(result, "may not mount", "~/.claude.json")


class StateRootParents(CommandFixture):
    """A state root's parent directory is the session's own tmpfs; no mount lands on it."""

    def test_a_mount_at_a_nested_roots_parent_is_refused(self):
        cache = self.home / ".cache"
        cache.mkdir()
        result = self.access("opencode-dev", "--rw", str(cache))
        self.assert_refused(result, "may not mount", "own directories under it")

    def test_a_tool_without_a_nested_root_takes_the_same_mount(self):
        cache = self.home / ".cache"
        cache.mkdir()
        result = self.access("claude-dev", "--rw", str(cache))
        self.assertEqual(result.returncode, 0, result.stderr)


class SymlinkedConfigDirectory(CommandFixture):
    """Dotfile managers link ~/.config elsewhere; the fences read through the link."""

    def setUp(self):
        super().setUp()
        self.real = self.tmp / "real-config"
        for name in ("claude-dev", "opencode-dev", "opencode"):
            (self.real / name).mkdir(parents=True)
        (self.home / ".config").symlink_to(self.real)

    def env(self, **overrides: str) -> dict[str, str]:
        # Unrelocated: each tool's data dir is ~/.config/<command>, behind the link.
        env = super().env(**overrides)
        for command in COMMANDS:
            env.pop(command.upper().replace("-", "_") + "_HOME", None)
        return env

    def test_the_other_tools_data_dir_is_refused_through_the_link(self):
        for flag in ("--rw", "--ro"):
            with self.subTest(flag=flag):
                result = self.access(
                    "claude-dev", flag, str(self.home / ".config" / "opencode-dev")
                )
                self.assert_refused(result, "the data directory of opencode-dev")

    def test_a_protected_path_is_refused_through_the_link_for_both_tools(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.access(
                    command, "--rw", str(self.home / ".config" / "opencode")
                )
                self.assert_refused(result, "decides how opencode runs")

    def test_a_project_inside_the_real_directory_is_refused(self):
        result = self.access("claude-dev", cwd=self.real / "opencode-dev")
        self.assert_refused(result, "not inside")


class ProtectedPaths(CommandFixture):
    """Every tool's host config is shareable read-only and never writable, from either tool."""

    def setUp(self):
        super().setUp()
        self.paths = [
            self.home / ".claude",
            self.home / ".config" / "opencode",
            self.home / ".local" / "share" / "opencode",
        ]
        for path in self.paths:
            path.mkdir(parents=True)

    def test_each_is_refused_as_a_writable_mount_by_both_tools(self):
        for command in COMMANDS:
            for path in self.paths:
                with self.subTest(command=command, path=path.name):
                    self.assert_refused(
                        self.access(command, "--rw", str(path)), "decides how"
                    )

    def test_a_writable_parent_is_refused(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.access(command, "--rw", str(self.home / ".config"))
                self.assert_refused(result, "it contains", "decides how opencode runs")

    def test_each_is_shareable_read_only(self):
        for command in COMMANDS:
            for path in self.paths:
                with self.subTest(command=command, path=path.name):
                    self.assertEqual(
                        self.access(command, "--ro", str(path)).returncode, 0
                    )

    def test_the_refusal_names_the_tool_whose_config_it_is(self):
        result = self.access("claude-dev", "--rw", str(self.paths[1]))
        self.assert_refused(result, "~/.config/opencode decides how opencode runs")
        result = self.access("opencode-dev", "--rw", str(self.paths[0]))
        self.assert_refused(result, "~/.claude decides how opencode runs")


class HostRunCode(CommandFixture):
    """What runs on the host is never writable from a session."""

    def setUp(self):
        super().setUp()
        (self.home / ".local" / "bin").mkdir(parents=True)

    def test_the_installed_commands_cannot_be_mounted_writable(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.access(command, "--rw", str(self.home / ".local" / "bin"))
                self.assert_refused(result, f"~/.local/bin {HOLDS_COMMANDS}")

    def test_a_writable_parent_of_the_installed_commands_is_refused(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.access(command, "--rw", str(self.home / ".local"))
                self.assert_refused(result, "it contains", HOLDS_COMMANDS)

    def test_the_installed_commands_are_shareable_read_only(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.access(command, "--ro", str(self.home / ".local" / "bin"))
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_a_checkout_the_engine_runs_from_cannot_be_mounted_writable(self):
        for command in COMMANDS:
            with self.subTest(command=command):
                result = self.access(command, "--rw", str(TOOLS_DIR))
                self.assert_refused(result, "engine and modules run on the host")
                result = self.access(command, "--rw", str(TOOLS_DIR.parent))
                self.assert_refused(result, "it contains")

    def test_a_checkout_the_engine_runs_from_is_shareable_read_only(self):
        result = self.access("claude-dev", "--ro", str(TOOLS_DIR))
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
