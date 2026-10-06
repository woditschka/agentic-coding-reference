#!/usr/bin/env python3
"""Tests for the launcher's mount fence and cleanup verb, driven through the shipped script."""

import http.server
import json
import os
import pathlib
import re
import subprocess
import tempfile
import threading
import unittest

from agent_dev_config import project_shadow_key

TOOLS_DIR = pathlib.Path(__file__).resolve().parent.parent
LAUNCHER = TOOLS_DIR / "claude-dev"
LAUNCH_TIMEOUT_S = 60

SOME_HOST_ID = "testhost"
LIVE_PID = 4242
DEAD_PID = 99999
LIVE_CONTAINER = "claude-dev-live"
STALE_CONTAINER = "claude-dev-stale"
IMAGE_LABEL = "label=claude-dev.image"
LAUNCHER_LABEL = "label=claude-dev.launcher"


def write_executable(path: pathlib.Path, script: str) -> None:
    path.write_text(script)
    path.chmod(0o755)


def docker_stub(*, unlabeled: tuple[str, ...] = ()) -> str:
    """Log every call; answer ps with one dead and one live launcher container."""
    # `image inspect -f <template> <tag>` prints the shared label's value: empty
    # for a tag named as unlabeled.
    return (
        "#!/usr/bin/env bash\n"
        'printf \'%s\\n\' "$*" >> "$DOCKER_LOG"\n'
        '[ "$1" = context ] && exit 1\n'
        'if [ "$1" = ps ]; then\n'
        f"  printf '{STALE_CONTAINER}\\t{SOME_HOST_ID}:{DEAD_PID}\\n'\n"
        f"  printf '{LIVE_CONTAINER}\\t{SOME_HOST_ID}:{LIVE_PID}\\n'\n"
        "fi\n"
        'if [ "$1" = image ] && [ "$2" = inspect ]; then\n'
        f'  case " {" ".join(unlabeled)} " in *" $5 "*) echo;; *) echo 1;; esac\n'
        "fi\n"
        "exit 0\n"
    )


def ps_stub(*, usable: bool = True) -> str:
    """Report every PID but one as alive, independent of the sandbox's process view."""
    if not usable:
        return "#!/usr/bin/env bash\nexit 127\n"
    return (
        "#!/usr/bin/env bash\n"
        f'[ "$1" = -p ] && [ "$2" = {DEAD_PID} ] && exit 1\n'
        "exit 0\n"
    )


class MountFence(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name).resolve()
        self.home = self.tmp / "home"
        self.data = self.tmp / "data"
        self.project = self.tmp / "project"
        for d in (self.home, self.data, self.project):
            d.mkdir(parents=True)

    def access(self, *flags: str, data: pathlib.Path | None = None):
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "CLAUDE_DEV_HOME": str(data if data is not None else self.data),
            # The sibling tool's data dir is fenced too; keep it outside any
            # path a test mounts.
            "OPENCODE_DEV_HOME": str(self.tmp / "opencode-data"),
        }
        return subprocess.run(
            [str(LAUNCHER), "access", *flags],
            cwd=str(self.project),
            env=env,
            capture_output=True,
            text=True,
            timeout=LAUNCH_TIMEOUT_S,
            check=False,
        )

    def assert_refused(self, result, *needles: str):
        self.assertNotEqual(result.returncode, 0)
        for needle in ("may not mount", *needles):
            self.assertIn(needle, result.stderr)

    def test_a_rw_source_inside_the_data_dir_is_refused(self):
        inside = self.data / "auth"
        inside.mkdir()
        self.assert_refused(self.access("--rw", str(inside)))

    def test_a_rw_source_containing_the_data_dir_is_refused(self):
        outer = self.tmp / "outer"
        nested = outer / "claude-dev-home"
        nested.mkdir(parents=True)
        result = self.access("--rw", str(outer), data=nested)
        self.assert_refused(result, "it contains", str(nested))

    def test_a_ro_source_containing_the_data_dir_is_refused(self):
        outer = self.tmp / "outer"
        nested = outer / "claude-dev-home"
        nested.mkdir(parents=True)
        result = self.access("--ro", str(outer), data=nested)
        self.assert_refused(result, "it contains", str(nested))

    def test_a_rw_source_containing_home_claude_is_refused(self):
        # The data dir stays outside the nest, so only the ~/.claude rule fires.
        nest = self.tmp / "nest"
        self.home = nest / "home"
        self.home.mkdir(parents=True)
        result = self.access("--rw", str(nest))
        self.assert_refused(result, "it contains", str(self.home / ".claude"))

    def test_a_ro_source_containing_home_claude_is_shareable(self):
        # The ~/.claude fence is write-only: read-only sharing of behavior
        # config is the documented mechanism.
        nest = self.tmp / "nest"
        self.home = nest / "home"
        self.home.mkdir(parents=True)
        result = self.access("--ro", str(nest))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(nest.name, result.stdout)

    def test_a_policy_mount_whose_name_ends_in_an_equals_sign_keeps_it(self):
        extra = self.tmp / "data="
        extra.mkdir()
        (self.data / "claude-dev.toml").write_text(
            f'[mounts]\nro = ["{extra}"]\n[egress]\nallow = ["api.anthropic.com"]\n'
        )
        result = self.access()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(
            result.stdout, rf"ro  {re.escape(str(extra))} +operator policy"
        )

    def test_open_egress_is_one_flag_for_this_run(self):
        result = self.access("--open-egress")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("egress: open", result.stdout)

    def test_the_allowlist_flag_overrides_a_policy_of_open_egress(self):
        (self.data / "claude-dev.toml").write_text(
            '[egress]\nmode = "open"\nallow = ["api.anthropic.com"]\n'
        )
        self.assertIn("egress: open", self.access().stdout)
        result = self.access("--allowlist-egress")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("egress: allow-list", result.stdout)

    def test_a_symlink_planted_as_a_shadow_parent_is_unlinked_not_followed(self):
        # The session writes its shadow. A link it leaves where the launcher
        # creates <shadow>/projects/<key> would aim that at a host directory.
        shadow = (
            self.data / "state" / "claude-state" / project_shadow_key(str(self.project))
        )
        shadow.mkdir(parents=True)
        outside = self.tmp / "outside"
        outside.mkdir()
        project_key = re.sub(r"[^a-zA-Z0-9]", "-", str(self.project))
        (outside / project_key).write_text("a host file")
        (shadow / "projects").symlink_to(outside)
        result = self.access()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((outside / project_key).read_text(), "a host file")
        self.assertFalse((shadow / "projects").is_symlink())

    def test_the_filesystem_root_is_refused_as_a_rw_source(self):
        self.assert_refused(self.access("--rw", "/"), "filesystem root")

    def test_a_plain_extra_ro_source_is_listed(self):
        extra = self.tmp / "shared-assets"
        extra.mkdir()
        result = self.access("--ro", str(extra))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(extra.name, result.stdout)

    def test_the_plugins_data_overlay_is_rw_and_private(self):
        # Plugin hooks need Claude Code's plugins/data mkdir to succeed, so the
        # overlay is writable and shadow-backed, never a host share.
        (self.home / ".claude" / "plugins").mkdir(parents=True)
        result = self.access()
        self.assertEqual(result.returncode, 0, result.stderr)
        row = next(
            line for line in result.stdout.splitlines() if "plugins/data" in line
        )
        self.assertTrue(row.startswith("rw"), row)
        self.assertIn("private plugin state", row)

    def test_no_plugins_dir_means_no_overlay(self):
        result = self.access()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("plugins/data", result.stdout)

    def test_a_missing_host_plugins_data_dir_is_created(self):
        # The overlay's mountpoint lives beneath the read-only plugins share,
        # where the engine cannot create it; an absent dir would abort the launch.
        (self.home / ".claude" / "plugins").mkdir(parents=True)
        result = self.access()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.home / ".claude" / "plugins" / "data").is_dir())


class OwFlag(unittest.TestCase):
    """--ow through the access verb: the plan it prints and the refusal without a table."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name).resolve()
        self.home = self.tmp / "home"
        self.data = self.tmp / "data"
        self.project = self.tmp / "project"
        for d in (self.home, self.data, self.project):
            d.mkdir(parents=True)

    def write_config(self, ow_table: str) -> None:
        (self.data / "claude-dev.toml").write_text(
            '[egress]\nallow = ["api.anthropic.com"]\n' + ow_table
        )

    def access(self, *flags: str):
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "CLAUDE_DEV_HOME": str(self.data),
        }
        return subprocess.run(
            [str(LAUNCHER), "access", *flags],
            cwd=str(self.project),
            env=env,
            capture_output=True,
            text=True,
            timeout=LAUNCH_TIMEOUT_S,
            check=False,
        )

    def test_without_a_table_the_flag_refuses_by_name(self):
        self.write_config("")
        result = self.access("--ow")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[open-weight] table", result.stderr)

    def test_the_plan_names_the_reverse_port_the_shape_and_the_map(self):
        self.write_config(
            '[open-weight]\n[open-weight.models]\n"claude-opus-5-5" = "glm-5.3:cloud"\n'
        )
        result = self.access("--ow")
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("proxy:3129 -> host.docker.internal:11434", out)
        self.assertIn("allow  POST /v1/messages", out)
        self.assertIn("model  glm-5.3:cloud <- claude-opus-5-5 (session)", out)
        self.assertIn("the stored login is not mounted", out)
        # The credential directory is not in the mount table under --ow.
        self.assertNotIn("credentials (private", out)

    def test_a_lan_peer_is_named_and_flagged_as_leaving_the_machine(self):
        self.write_config(
            '[open-weight]\npeer = "192.168.1.123"\n'
            '[open-weight.models]\n"claude-opus-5-5" = "glm-5.3:cloud"\n'
        )
        result = self.access("--ow")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("-> 192.168.1.123:11434", result.stdout)
        self.assertIn("leave it in plain HTTP", result.stdout)

    def test_without_the_flag_a_valid_table_changes_nothing(self):
        self.write_config(
            '[open-weight]\n[open-weight.models]\n"claude-opus-5-5" = "glm-5.3:cloud"\n'
        )
        result = self.access()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("open_weight:", result.stdout)
        self.assertIn("credentials (private", result.stdout)

    def test_without_the_flag_an_invalid_table_still_refuses_by_name(self):
        # The file is read whole on every launch: a defect is never left
        # looking like policy, flag or not.
        self.write_config("[open-weight]\n")
        result = self.access()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("open-weight.models", result.stderr)


class _Listing(http.server.BaseHTTPRequestHandler):
    body = json.dumps({"models": [{"name": "glm-5.3:cloud"}]}).encode()

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *_):
        pass


def engine_stub() -> str:
    """Accept every call; answer the subnet read so the launch reaches the session."""
    return (
        "#!/usr/bin/env bash\n"
        'printf \'%s\\n\' "$*" >> "$DOCKER_LOG"\n'
        '[ "$1" = context ] && exit 1\n'
        # The replica is discarded with the run directory, so keep a copy.
        'for a in "$@"; do case "$a" in */replica.json:*) cp "${a%%:*}" "$DOCKER_LOG.replica";; esac; done\n'
        'if [ "$1" = network ] && [ "$2" = inspect ] && [ "$3" = -f ] && [[ "$4" == *Subnet* ]]; then\n'
        "  echo 172.30.0.0/16\n"
        "fi\n"
        "exit 0\n"
    )


class OwLaunch(unittest.TestCase):
    """A --ow launch driven to the session exec against a stub engine and a local listing."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name).resolve()
        self.home = self.tmp / "home"
        self.data = self.tmp / "data"
        self.project = self.tmp / "project"
        self.bin_dir = self.tmp / "bin"
        for d in (self.home, self.data, self.project, self.bin_dir):
            d.mkdir()
        (self.data / "host-id").write_text(f"{SOME_HOST_ID}\n")
        self.log = self.tmp / "docker.log"
        write_executable(self.bin_dir / "ps", ps_stub())
        write_executable(self.bin_dir / "docker", engine_stub())
        server = http.server.HTTPServer(("127.0.0.1", 0), _Listing)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.peer_port = server.server_address[1]

    def launch(self, *flags: str, cwd: pathlib.Path | None = None, **env_extra: str):
        (self.data / "claude-dev.toml").write_text(
            '[egress]\nallow = ["api.anthropic.com"]\n'
            f'[open-weight]\npeer = "127.0.0.1"\nport = {self.peer_port}\n'
            '[open-weight.models]\n"claude-opus-5-5" = "glm-5.3:cloud"\n'
        )
        env = {
            "PATH": f"{self.bin_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}",
            "HOME": str(self.home),
            "CLAUDE_DEV_HOME": str(self.data),
            "DOCKER_LOG": str(self.log),
            **env_extra,
        }
        # One launch, one record: a second launch in the same test starts clean.
        self.log.unlink(missing_ok=True)
        result = subprocess.run(
            [str(LAUNCHER), *flags],
            cwd=str(cwd or self.project),
            env=env,
            capture_output=True,
            text=True,
            timeout=LAUNCH_TIMEOUT_S,
            check=False,
            stdin=subprocess.DEVNULL,
        )
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return result, calls

    def test_the_session_gets_the_settings_document_and_no_credential(self):
        result, calls = self.launch("--ow")
        self.assertEqual(result.returncode, 0, result.stderr)
        session_exec = next(
            c for c in calls if c.startswith("exec -i ") and " claude " in c
        )
        self.assertIn('"ANTHROPIC_BASE_URL":"http://proxy:3129"', session_exec)
        self.assertIn(
            '"modelOverrides":{"claude-opus-5-5":"glm-5.3:cloud"}', session_exec
        )
        session_run = next(c for c in calls if c.startswith("run --rm"))
        self.assertNotIn(str(self.data / "auth"), session_run)
        self.assertIn("CLAUDE_SECURESTORAGE_CONFIG_DIR=", session_run)
        self.assertIn("NO_PROXY=localhost,127.0.0.1,proxy", session_run)
        self.assertIn(f"model server: 127.0.0.1:{self.peer_port};", result.stderr)
        self.assertIn("--ow glm-5.3:cloud <- claude-opus-5-5 (session)", result.stderr)
        self.assertIn('"model":"claude-opus-5-5"', session_exec)

    def test_without_the_flag_the_credential_mount_and_proxy_bypass_are_as_before(self):
        result, calls = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        session_run = next(c for c in calls if c.startswith("run --rm"))
        self.assertIn(f"{self.data}/auth:{self.data}/auth", session_run)
        self.assertIn("NO_PROXY=localhost,127.0.0.1 ", session_run)
        session_exec = next(
            c for c in calls if c.startswith("exec -i ") and " claude " in c
        )
        self.assertNotIn("modelOverrides", session_exec)


class PermissionPosture(OwLaunch):
    """The launcher injects auto mode unless a passed-through flag names the posture."""

    def session_exec(self, *flags: str) -> str:
        result, calls = self.launch(*flags)
        self.assertEqual(result.returncode, 0, result.stderr)
        return next(c for c in calls if c.startswith("exec -i ") and " claude " in c)

    def test_auto_mode_is_injected_by_default(self):
        self.assertIn(" claude --permission-mode auto --settings ", self.session_exec())

    def test_either_spelling_of_the_mode_flag_replaces_the_default(self):
        for flags in (("--permission-mode", "plan"), ("--permission-mode=plan",)):
            with self.subTest(flags=flags):
                call = self.session_exec(*flags)
                self.assertNotIn("--permission-mode auto", call)
                self.assertTrue(call.endswith(" ".join(flags)), call)

    def test_the_skip_flag_replaces_the_default(self):
        call = self.session_exec("--dangerously-skip-permissions")
        self.assertNotIn("--permission-mode auto", call)

    def test_a_flag_that_only_starts_like_one_keeps_the_default(self):
        # The skip flag is boolean, so an `=` form is not that flag; neither is
        # a longer name that begins with the mode flag's.
        for flag in ("--dangerously-skip-permissions=1", "--permission-modes"):
            with self.subTest(flag=flag):
                self.assertIn("--permission-mode auto", self.session_exec(flag))

    def test_an_unrelated_flag_passes_through_beside_the_default(self):
        call = self.session_exec("--model", "x")
        self.assertIn("--permission-mode auto", call)
        self.assertTrue(call.endswith("--model x"), call)


class SessionEnvironment(OwLaunch):
    def session_run(self, *flags: str) -> str:
        result, calls = self.launch(*flags)
        self.assertEqual(result.returncode, 0, result.stderr)
        return next(c for c in calls if c.startswith("run --rm"))

    def test_claude_code_gets_both_proxy_variables_in_both_cases(self):
        run = self.session_run()
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            with self.subTest(name=name):
                self.assertIn(f"-e {name}=http://proxy:3128", run)

    def test_no_nested_tmpfs_is_added_when_every_root_sits_at_home_level(self):
        self.assertEqual(self.session_run().count("--tmpfs "), 1)

    def test_a_launch_on_a_cloud_tag_says_prompts_leave_through_the_peer(self):
        result, _ = self.launch("--ow")
        self.assertIn("--ow note: a cloud tag", result.stderr)


class ProjectShadow(OwLaunch):
    """The private ~/.claude is one shadow per project, and another under --ow."""

    def shadow(self, *flags: str, cwd: pathlib.Path | None = None) -> str:
        result, calls = self.launch(*flags, cwd=cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        run = next(c for c in calls if c.startswith("run --rm"))
        return re.search(rf"-v (\S+):{re.escape(str(self.home))}/\.claude ", run)[1]

    def test_two_projects_get_two_shadows_under_the_state_directory(self):
        other = self.tmp / "other-project"
        other.mkdir()
        first, second = self.shadow(), self.shadow(cwd=other)
        self.assertNotEqual(first, second)
        for shadow in (first, second):
            self.assertTrue(
                shadow.startswith(f"{self.data}/state/claude-state/"), shadow
            )

    def test_one_project_keeps_its_shadow_across_launches(self):
        self.assertEqual(self.shadow(), self.shadow())

    def test_a_session_on_a_peer_gets_a_shadow_of_its_own(self):
        plain, on_peer = self.shadow(), self.shadow("--ow")
        self.assertEqual(on_peer, plain + ".ow")

    def test_a_new_project_is_not_announced_as_a_first_login(self):
        # The login lives in the relocated store, one for every project.
        (self.data / "auth").mkdir()
        (self.data / "auth" / ".credentials.json").write_text("{}")
        result, _ = self.launch()
        self.assertNotIn("first run", result.stderr)


class Replica(OwLaunch):
    """The ~/.claude.json replica a session receives, with and without --ow."""

    def replica(self, *flags: str) -> dict:
        (self.home / ".claude.json").write_text(
            json.dumps(
                {
                    "theme": "dark",
                    "primaryApiKey": "a-stored-key",
                    "mcpServers": {
                        "x": {"headers": {"Authorization": "a-token"}},
                        "ide": {"type": "sse", "url": "http://127.0.0.1:64342/sse"},
                    },
                    "projects": {
                        str(self.project): {
                            "hasTrustDialogAccepted": True,
                            "mcpServers": {"y": {"env": {"TOKEN": "another"}}},
                        }
                    },
                }
            )
        )
        result, _ = self.launch(*flags)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(pathlib.Path(f"{self.log}.replica").read_text())

    def test_a_session_on_a_peer_receives_no_stored_key_and_no_mcp_table(self):
        replica = self.replica("--ow")
        self.assertNotIn("a-stored-key", json.dumps(replica))
        self.assertNotIn("a-token", json.dumps(replica))
        self.assertNotIn("another", json.dumps(replica))
        self.assertEqual(list(replica["mcpServers"]), ["ide"])
        self.assertEqual(replica["theme"], "dark")
        self.assertTrue(
            replica["projects"][str(self.project)]["hasTrustDialogAccepted"]
        )

    def test_a_credentialed_session_receives_the_file_scrubbed_to_the_project_only(
        self,
    ):
        replica = self.replica()
        self.assertEqual(replica["primaryApiKey"], "a-stored-key")
        self.assertIn("mcpServers", replica["projects"][str(self.project)])


class LinkedPaths(OwLaunch):
    """What a launch mounts when a path is reached through a link."""

    def test_a_linked_file_mounts_its_target_at_the_links_own_path(self):
        real = self.tmp / "dotfiles" / "statusline-real.sh"
        real.parent.mkdir()
        real.write_text("#!/bin/sh\n")
        link = self.tmp / "statusline.sh"
        link.symlink_to(real)
        result, calls = self.launch("--ro", str(link))
        self.assertEqual(result.returncode, 0, result.stderr)
        run = next(c for c in calls if c.startswith("run --rm"))
        self.assertIn(f"-v {real}:{link}:ro", run)

    def test_a_project_reached_through_a_link_is_named_at_launch(self):
        link = self.tmp / "project-link"
        link.symlink_to(self.project)
        result, calls = self.launch(cwd=link, PWD=str(link))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            f"the project directory is {self.project} (reached as {link})",
            result.stderr,
        )
        run = next(c for c in calls if c.startswith("run --rm"))
        self.assertIn(f"-v {self.project}:{self.project} ", run)

    def test_a_project_entered_directly_gets_no_such_line(self):
        result, _ = self.launch(PWD=str(self.project))
        self.assertNotIn("the project directory is", result.stderr)


class RunDirectories(OwLaunch):
    """A killed launcher leaves its run directory; the next launch of this install reaps it."""

    def leftover(self, pid: int) -> pathlib.Path:
        path = self.data / "run" / f"{SOME_HOST_ID}.{pid}.abc123"
        (path / "state" / "x").mkdir(parents=True)
        (path / "state" / "x" / "file").write_text("left behind")
        return path

    def test_a_dead_launchers_run_directory_is_removed(self):
        dead = self.leftover(DEAD_PID)
        self.launch()
        self.assertFalse(dead.exists())

    def test_a_read_only_leftover_is_still_removed(self):
        dead = self.leftover(DEAD_PID)
        (dead / "state" / "x").chmod(0o555)
        self.launch()
        self.assertFalse(dead.exists())

    def test_a_ps_that_cannot_run_keeps_every_run_directory(self):
        # A probe that cannot see this launcher cannot call another one dead.
        write_executable(self.bin_dir / "ps", ps_stub(usable=False))
        dead = self.leftover(DEAD_PID)
        self.launch()
        self.assertTrue(dead.exists())

    def test_a_live_launchers_run_directory_is_kept(self):
        live = self.leftover(LIVE_PID)
        self.launch()
        self.assertTrue(live.exists())

    def test_another_installs_run_directory_is_kept(self):
        foreign = self.data / "run" / f"otherhost.{DEAD_PID}.abc123"
        foreign.mkdir(parents=True)
        self.launch()
        self.assertTrue(foreign.exists())

    def test_this_launch_leaves_no_run_directory_behind(self):
        self.launch()
        self.assertEqual(list((self.data / "run").iterdir()), [])


class CleanupVerb(unittest.TestCase):
    """The cleanup verb against a stub docker and a stub ps, run from $HOME."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name).resolve()
        self.home = self.tmp / "home"
        self.data = self.tmp / "data"
        self.bin_dir = self.tmp / "bin"
        for d in (self.home, self.data, self.bin_dir):
            d.mkdir()
        (self.data / "host-id").write_text(f"{SOME_HOST_ID}\n")
        self.log = self.tmp / "docker.log"
        write_executable(self.bin_dir / "ps", ps_stub())

    def _run_cleanup(
        self, *flags: str, unlabeled: tuple[str, ...] = ()
    ) -> tuple["subprocess.CompletedProcess[str]", list[str]]:
        write_executable(self.bin_dir / "docker", docker_stub(unlabeled=unlabeled))
        env = {
            "PATH": f"{self.bin_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}",
            "HOME": str(self.home),
            "CLAUDE_DEV_HOME": str(self.data),
            "DOCKER_LOG": str(self.log),
        }
        result = subprocess.run(
            [str(LAUNCHER), "cleanup", *flags],
            cwd=str(self.home),
            env=env,
            capture_output=True,
            text=True,
            timeout=LAUNCH_TIMEOUT_S,
            check=False,
        )
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return result, calls

    def test_cleanup_reaps_dead_launchers_and_prunes_by_label_only(self):
        result, calls = self._run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cleanup done", result.stderr)
        self.assertIn(f"image prune -f --filter {IMAGE_LABEL}", calls)
        self.assertTrue(
            any(c.startswith(f"ps -a --filter {LAUNCHER_LABEL}") for c in calls),
            calls,
        )
        self.assertIn(f"rm -f {STALE_CONTAINER}", calls)
        self.assertNotIn(f"rm -f {LIVE_CONTAINER}", calls)
        unscoped = [c for c in calls if "prune" in c and IMAGE_LABEL not in c]
        self.assertEqual(unscoped, [])

    def test_cleanup_all_adds_one_engine_wide_prune_sparing_the_image(self):
        result, calls = self._run_cleanup("--all")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cleanup --all done", result.stderr)
        self.assertIn(f"image prune -f --filter {IMAGE_LABEL}", calls)
        system_prunes = [c for c in calls if c.startswith("system prune")]
        self.assertEqual(
            system_prunes,
            ["system prune -a -f --volumes --filter label!=agent-dev.image"],
            calls,
        )

    def test_cleanup_all_names_exactly_one_spare_filter(self):
        # Docker spares an image only when it carries every label the label!=
        # filters name, so a filter per tool would spare no image at all.
        result, calls = self._run_cleanup("--all")
        self.assertEqual(result.returncode, 0, result.stderr)
        prune = next(c for c in calls if c.startswith("system prune"))
        self.assertEqual(prune.count("label!="), 1, prune)

    def test_cleanup_all_refuses_while_any_tool_image_is_unlabeled(self):
        # An image without the shared label is not spared by label!=, so the
        # verb refuses rather than prune a tool's current image: its own, or
        # the other tool's, which the same engine-wide prune would take.
        for tool in ("claude-dev", "opencode-dev"):
            with self.subTest(tool=tool):
                self.log.unlink(missing_ok=True)
                result, calls = self._run_cleanup(
                    "--all", unlabeled=(f"{tool}:latest",)
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    f"{tool}:latest lacks the agent-dev.image label", result.stderr
                )
                self.assertIn(f"run '{tool} update' first", result.stderr)
                self.assertEqual([c for c in calls if c.startswith("system prune")], [])

    def test_a_ps_that_cannot_run_reaps_no_container(self):
        write_executable(self.bin_dir / "ps", ps_stub(usable=False))
        result, calls = self._run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([c for c in calls if c.startswith("rm -f")], [])


if __name__ == "__main__":
    unittest.main()
