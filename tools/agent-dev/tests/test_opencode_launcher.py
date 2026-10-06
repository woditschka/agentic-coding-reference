#!/usr/bin/env python3
"""Tests for the opencode-dev command through the shipped scripts: the plan, the state lifetimes and the launch."""

import http.server
import os
import pathlib
import re
import subprocess
import tempfile
import threading
import unittest

from agent_dev_config import project_shadow_key

from tests.test_launcher import _Listing, engine_stub, ps_stub, write_executable

TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent
LAUNCHER = TOOLS_DIR / "opencode-dev"
POLICY = TOOLS_DIR / "opencode-dev.toml"
LAUNCH_TIMEOUT_S = 60

SOME_HOST_ID = "testhost"
# The shipped policy without its [open-weight] table, which is its last table.
POLICY_WITHOUT_OW = POLICY.read_text().split("\n[open-weight]\n")[0] + "\n"
OW_TABLE = (
    '\n[open-weight]\nmodel = "claude-opus-5.5"\n'
    '[open-weight.models]\n"claude-opus-5.5" = "glm-5.3:cloud"\n'
    '"claude-sonnet-5.5" = "glm-5.3-flash:cloud"\n'
)
RUN_SHADOWS = ("opencode-config", "opencode-state", "opencode-cache", "opencode-claude")
DISCARDED = "private shadow, discarded on exit"


def project_key(path: pathlib.Path) -> str:
    """Return the per-project shadow key the launcher derives from the physical path."""
    return project_shadow_key(str(path))


class OpenCodeLauncher(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name).resolve()
        self.home = self.tmp / "home"
        self.data = self.tmp / "data"
        self.project = self.tmp / "project"
        for d in (self.home, self.data, self.project):
            d.mkdir(parents=True)
        config = self.home / ".config" / "opencode"
        (config / "agents").mkdir(parents=True)
        (config / "AGENTS.md").write_text("rules")
        (config / "opencode.json").write_text("{}")
        claude = self.home / ".claude"
        (claude / "skills").mkdir(parents=True)
        (claude / "CLAUDE.md").write_text("rules")
        (claude / "settings.json").write_text("{}")
        (claude / "projects").mkdir()
        share = self.home / ".local" / "share" / "opencode"
        share.mkdir(parents=True)
        (share / "auth.json").write_text("{}")
        self.write_policy()

    def write_policy(self, ow_table: str | None = None) -> None:
        """Install the shipped policy, or the shipped policy with this [open-weight] table in its place."""
        text = POLICY.read_text() if ow_table is None else POLICY_WITHOUT_OW + ow_table
        (self.data / "opencode-dev.toml").write_text(text)

    def env(self) -> dict[str, str]:
        return {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "OPENCODE_DEV_HOME": str(self.data),
            # The sibling tool's data dir is fenced too; keep it outside every
            # path a test mounts.
            "CLAUDE_DEV_HOME": str(self.tmp / "claude-data"),
        }

    def run_command(self, *args: str, cwd: pathlib.Path | None = None):
        return subprocess.run(
            [str(LAUNCHER), *args],
            cwd=str(cwd or self.project),
            env=self.env(),
            capture_output=True,
            text=True,
            timeout=LAUNCH_TIMEOUT_S,
            check=False,
        )

    def access(self, *flags: str):
        return self.run_command("access", *flags)

    def rows(self, result) -> dict[str, str]:
        """Map each destination row of the mount table to its note."""
        table = {}
        for line in result.stdout.splitlines():
            parts = line.split(None, 2)
            if len(parts) == 3 and parts[0] in ("rw", "ro"):
                table[parts[1]] = parts[2]
        return table


class Plan(OpenCodeLauncher):
    def test_config_state_cache_and_claude_are_discarded_with_the_session(self):
        rows = self.rows(self.access())
        for path in (
            "~/.config/opencode",
            "~/.local/state/opencode",
            "~/.cache/opencode",
            "~/.claude",
        ):
            with self.subTest(path=path):
                self.assertEqual(rows[path], DISCARDED)

    def test_the_data_directory_is_a_private_shadow_for_this_project_alone(self):
        rows = self.rows(self.access())
        note = rows["~/.local/share/opencode"]
        self.assertTrue(note.startswith("private shadow <-"), note)
        self.assertTrue(note.endswith(project_key(self.project)), note)

    def test_under_ow_the_data_directory_is_a_different_shadow(self):
        self.write_policy(OW_TABLE)
        plain = self.rows(self.access())["~/.local/share/opencode"]
        open_weight = self.rows(self.access("--ow"))["~/.local/share/opencode"]
        self.assertNotEqual(plain, open_weight)
        self.assertTrue(
            open_weight.endswith(project_key(self.project) + ".ow"),
            open_weight,
        )

    def test_host_config_is_shared_read_only_and_only_what_exists(self):
        rows = self.rows(self.access())
        for path in (
            "~/.config/opencode/AGENTS.md",
            "~/.config/opencode/agents",
            "~/.config/opencode/opencode.json",
            "~/.claude/CLAUDE.md",
            "~/.claude/skills",
        ):
            with self.subTest(path=path):
                self.assertEqual(rows[path], "shared from host - read only")
        self.assertNotIn("~/.config/opencode/plugins", rows)

    def test_nothing_else_of_the_claude_tree_crosses(self):
        rows = self.rows(self.access())
        self.assertNotIn("~/.claude/settings.json", rows)
        self.assertNotIn("~/.claude/projects", rows)

    def test_the_hosts_own_credential_file_is_never_mounted(self):
        rows = self.rows(self.access())
        self.assertFalse([p for p in rows if p.endswith("auth.json")])

    def test_no_separate_credential_directory_exists(self):
        result = self.access()
        self.assertNotIn("credentials (private", result.stdout)
        self.assertFalse((self.data / "auth").exists())

    def test_only_the_per_project_data_shadow_persists_under_the_data_dir(self):
        self.access()
        state = self.data / "state"
        self.assertEqual([p.name for p in state.iterdir()], ["opencode-data"])
        self.assertEqual(
            [p.name for p in (state / "opencode-data").iterdir()],
            [project_key(self.project)],
        )

    def test_per_run_shadows_are_gone_when_the_command_exits(self):
        self.access()
        run_dir = self.data / "run"
        leftovers = list(run_dir.rglob("*")) if run_dir.exists() else []
        self.assertEqual(leftovers, [])

    def test_the_state_directory_is_owner_only(self):
        self.access()
        mode = (self.data / "state").stat().st_mode & 0o777
        self.assertEqual(mode, 0o700)

    def test_the_default_allow_list_reaches_the_catalog_and_names_no_provider(self):
        out = self.access().stdout
        self.assertIn("allow  models.opencode.ai", out)
        self.assertNotIn("allow  api.anthropic.com", out)

    def test_the_share_origin_is_not_on_the_default_allow_list(self):
        # opencode.ai accepts authenticated uploads from the session.
        self.assertNotIn("allow  opencode.ai\n", self.access().stdout)


class FirstRun(OpenCodeLauncher):
    """The login lives in the project's data shadow, so each project starts without one."""

    def test_an_empty_project_shadow_prints_the_login_and_allow_list_hint(self):
        result = self.access()
        self.assertIn("first run in this project", result.stderr)
        self.assertIn("/connect", result.stderr)
        self.assertIn("allow-list", result.stderr)

    def test_a_project_with_state_prints_no_hint(self):
        self.access()
        shadow = self.data / "state" / "opencode-data" / project_key(self.project)
        (shadow / "auth.json").write_text("{}")
        self.assertNotIn("first run", self.access().stderr)

    def test_a_session_on_a_peer_prints_no_login_hint(self):
        self.assertNotIn("first run", self.access("--ow").stderr)


class ProjectShadowKeys(OpenCodeLauncher):
    def test_paths_a_character_replacing_key_would_merge_get_separate_shadows(self):
        # /x/a-b and /x/a/b both became -x-a-b under the old key, sharing a login.
        flat = self.tmp / "a-b"
        nested = self.tmp / "a" / "b"
        flat.mkdir()
        nested.mkdir(parents=True)
        notes = {
            self.rows(self.run_command("access", cwd=cwd))["~/.local/share/opencode"]
            for cwd in (flat, nested)
        }
        self.assertEqual(len(notes), 2)


class OwPlan(OpenCodeLauncher):
    def test_the_plan_names_the_chat_path_and_the_map(self):
        self.write_policy(OW_TABLE)
        result = self.access("--ow")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("proxy:3129 -> host.docker.internal:11434", result.stdout)
        self.assertIn("allow  POST /v1/chat/completions", result.stdout)
        self.assertIn(
            "model  glm-5.3:cloud <- claude-opus-5.5 (session)", result.stdout
        )

    def test_the_shipped_policy_enables_the_flag_on_ollama_with_the_glm_map(self):
        result = self.access("--ow")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("proxy:3129 -> host.docker.internal:11434", result.stdout)
        self.assertIn(
            "model  glm-5.3:cloud <- claude-opus-5.5 (session)", result.stdout
        )
        self.assertIn("model  glm-5.3-flash:cloud <- claude-sonnet-5.5", result.stdout)

    def test_a_cloud_tag_is_named_as_leaving_through_the_peer(self):
        result = self.access("--ow")
        self.assertIn("a cloud tag is served by the peer's vendor", result.stdout)

    def test_a_local_map_carries_no_cloud_note(self):
        self.write_policy(
            '\n[open-weight]\n[open-weight.models]\n"claude-opus-5.5" = "qwen3-coder:30b"\n'
        )
        self.assertNotIn("cloud tag", self.access("--ow").stdout)

    def test_the_flag_refuses_by_name_without_a_table(self):
        self.write_policy("")
        result = self.access("--ow")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[open-weight] table", result.stderr)
        self.assertIn("opencode-dev.toml", result.stderr)

    def test_a_telemetry_table_is_refused_by_name(self):
        (self.data / "opencode-dev.toml").write_text(
            POLICY.read_text() + "\n[telemetry]\nenabled = true\n"
        )
        result = self.access()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[telemetry]", result.stderr)


class Fences(OpenCodeLauncher):
    def assert_refused(self, result, *needles: str):
        self.assertNotEqual(result.returncode, 0)
        for needle in ("may not mount", *needles):
            self.assertIn(needle, result.stderr)

    def test_the_ide_bridge_is_not_offered(self):
        result = self.access("--ide")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--ide is not offered by opencode-dev", result.stderr)

    def test_a_project_inside_a_protected_path_is_refused(self):
        inside = self.home / ".config" / "opencode" / "agents"
        result = self.run_command("access", cwd=inside)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not inside ~/.config/opencode", result.stderr)

    def test_the_data_dir_is_refused_in_both_directions(self):
        self.assert_refused(self.access("--rw", str(self.data)))
        self.assert_refused(self.access("--rw", str(self.tmp)), "it contains")


class Help(OpenCodeLauncher):
    def test_help_is_the_commands_own_usage_and_needs_no_config(self):
        (self.data / "opencode-dev.toml").write_text("not = = toml")
        result = self.run_command("help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("opencode-dev [options]", result.stdout)
        self.assertIn("/connect", result.stdout)
        self.assertNotIn("--ide", result.stdout)
        self.assertNotIn("claude", result.stdout.lower())


class Launch(OpenCodeLauncher):
    """A launch driven to the session exec against a stub engine and a local listing."""

    def setUp(self):
        super().setUp()
        self.bin_dir = self.tmp / "bin"
        self.bin_dir.mkdir()
        (self.data / "host-id").write_text(f"{SOME_HOST_ID}\n")
        self.log = self.tmp / "docker.log"
        write_executable(self.bin_dir / "ps", ps_stub())
        write_executable(self.bin_dir / "docker", engine_stub())
        server = http.server.HTTPServer(("127.0.0.1", 0), _Listing)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.peer_port = server.server_address[1]

    def launch(self, *flags: str):
        (self.data / "opencode-dev.toml").write_text(
            POLICY_WITHOUT_OW
            + f'\n[open-weight]\npeer = "127.0.0.1"\nport = {self.peer_port}\n'
            '[open-weight.models]\n"claude-opus-5.5" = "glm-5.3:cloud"\n'
        )
        env = self.env()
        env["PATH"] = f"{self.bin_dir}:{env['PATH']}"
        env["DOCKER_LOG"] = str(self.log)
        self.log.unlink(missing_ok=True)
        result = subprocess.run(
            [str(LAUNCHER), *flags],
            cwd=str(self.project),
            env=env,
            capture_output=True,
            text=True,
            timeout=LAUNCH_TIMEOUT_S,
            check=False,
            stdin=subprocess.DEVNULL,
        )
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return result, calls

    def session_run(self, calls: list[str]) -> str:
        return next(c for c in calls if c.startswith("run --rm"))

    def session_exec(self, calls: list[str]) -> str:
        return next(c for c in calls if c.startswith("exec -i "))

    def test_the_session_command_runs_the_prepare_step_then_opencode(self):
        # sh -c '<prepare>' sh opencode: the placeholder keeps $0 off the
        # binary, so the prepare step's `exec "$@"` still names it.
        result, calls = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        exec_call = self.session_exec(calls)
        self.assertIn(" sh -c ", exec_call)
        self.assertIn('exec "$@" sh opencode', exec_call)
        self.assertIn("/opt/opencode-seed", exec_call)

    def test_the_session_gets_https_proxy_variables_only(self):
        _, calls = self.launch()
        run = self.session_run(calls)
        self.assertIn("-e HTTPS_PROXY=http://proxy:3128", run)
        self.assertIn("-e https_proxy=http://proxy:3128", run)
        self.assertNotIn("-e HTTP_PROXY=", run)
        self.assertNotIn("-e http_proxy=", run)

    def test_the_settings_document_is_an_environment_variable_not_an_argument(self):
        _, calls = self.launch()
        self.assertIn("-e OPENCODE_CONFIG_CONTENT={", self.session_run(calls))
        self.assertNotIn("--settings", self.session_exec(calls))

    def test_no_permission_mode_is_injected(self):
        _, calls = self.launch()
        self.assertNotIn("--permission-mode", self.session_exec(calls))

    def test_no_telemetry_variable_is_declared(self):
        _, calls = self.launch()
        self.assertNotIn("DISABLE_TELEMETRY", self.session_run(calls))

    def test_no_credential_variable_or_mount_is_added(self):
        _, calls = self.launch()
        run = self.session_run(calls)
        self.assertNotIn("SECURESTORAGE", run)
        self.assertNotIn(f"{self.data}/auth", run)

    def test_the_per_run_shadows_are_mounted_from_the_run_directory(self):
        _, calls = self.launch()
        run = self.session_run(calls)
        for shadow in RUN_SHADOWS:
            with self.subTest(shadow=shadow):
                self.assertRegex(
                    run,
                    rf"{re.escape(str(self.data))}/run/{SOME_HOST_ID}\.[0-9]+\.[A-Za-z0-9]+/state/{shadow}:",
                )

    def test_the_data_shadow_is_keyed_by_project_and_separate_under_ow(self):
        key = project_key(self.project)
        _, plain = self.launch()
        _, open_weight = self.launch("--ow")
        self.assertIn(f"/state/opencode-data/{key}:", self.session_run(plain))
        self.assertIn(f"/state/opencode-data/{key}.ow:", self.session_run(open_weight))
        self.assertNotIn(f"/state/opencode-data/{key}:", self.session_run(open_weight))

    def test_under_ow_the_peer_is_the_provider(self):
        result, calls = self.launch("--ow")
        self.assertEqual(result.returncode, 0, result.stderr)
        run = self.session_run(calls)
        self.assertIn('"baseURL":"http://proxy:3129/v1"', run)
        self.assertIn('"id":"glm-5.3:cloud"', run)
        self.assertIn("NO_PROXY=localhost,127.0.0.1,proxy", run)
        self.assertIn(
            "inference requests only (POST /v1/chat/completions)", result.stderr
        )
        self.assertIn(
            "a data shadow apart from the one that holds this project's provider login",
            result.stderr,
        )

    def test_the_parents_of_each_nested_root_are_operator_owned_tmpfs(self):
        # The engine would create ~/.cache and ~/.local root-owned inside the
        # home tmpfs, and the Go build cache beside ~/.cache/opencode would fail.
        _, calls = self.launch()
        run = self.session_run(calls)
        owner = f"uid={os.getuid()},gid={os.getgid()}"
        for parent in (".config", ".local", ".local/share", ".local/state", ".cache"):
            with self.subTest(parent=parent):
                self.assertRegex(
                    run,
                    rf"--tmpfs {re.escape(str(self.home / parent))}:\S*mode=700,{owner}( |$)",
                )

    def test_a_launch_on_cloud_tags_says_prompts_leave_through_the_peer(self):
        result, _ = self.launch("--ow")
        self.assertIn("--ow note: a cloud tag", result.stderr)

    def test_the_run_directory_is_removed_after_the_launch(self):
        self.launch()
        run_dir = self.data / "run"
        self.assertEqual(list(run_dir.rglob("*")) if run_dir.exists() else [], [])


if __name__ == "__main__":
    unittest.main()
