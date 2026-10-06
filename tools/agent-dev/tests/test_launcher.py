#!/usr/bin/env python3
"""Tests for the launcher's mount fence and cleanup verb, driven through the shipped script."""

import http.server
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import threading
import unittest

LAUNCHER = pathlib.Path(__file__).resolve().parent.parent / "claude-dev"
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


def docker_stub(*, image_labeled: bool) -> str:
    """Log every call; answer ps with one dead and one live launcher container."""
    return (
        "#!/usr/bin/env bash\n"
        'printf \'%s\\n\' "$*" >> "$DOCKER_LOG"\n'
        '[ "$1" = context ] && exit 1\n'
        'if [ "$1" = ps ]; then\n'
        f"  printf '{STALE_CONTAINER}\\t{SOME_HOST_ID}:{DEAD_PID}\\n'\n"
        f"  printf '{LIVE_CONTAINER}\\t{SOME_HOST_ID}:{LIVE_PID}\\n'\n"
        "fi\n"
        'if [ "$1" = image ] && [ "$2" = inspect ]; then\n'
        f'  echo "{("1" if image_labeled else "")}"\n'
        "fi\n"
        "exit 0\n"
    )


def ps_stub() -> str:
    """Report exactly one PID as alive, independent of the sandbox's process view."""
    return (
        "#!/usr/bin/env bash\n"
        f'[ "$1" = -p ] && [ "$2" = {LIVE_PID} ] && exit 0\n'
        "exit 1\n"
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


class InProjectCopy(unittest.TestCase):
    """A command script inside the project it would mount is refused, whichever engine it would run."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = pathlib.Path(tmp.name).resolve()
        self.home = self.tmp / "home"
        self.data = self.tmp / "data"
        self.project = self.tmp / "project"
        for d in (self.home, self.data, self.project):
            d.mkdir(parents=True)
        # An installed engine exists, as on a machine that ran install.sh.
        for name in (
            "agent-dev",
            "agent_dev.py",
            "agent_dev_config.py",
            "agent_dev_profiles.py",
            "claude-dev.toml",
        ):
            shutil.copy(LAUNCHER.parent / name, self.data / name)
        self.copy = self.project / "claude-dev"
        shutil.copy(LAUNCHER, self.copy)

    def run_copy(self, *args: str):
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "CLAUDE_DEV_HOME": str(self.data),
        }
        return subprocess.run(
            [str(self.copy), *args],
            cwd=str(self.project),
            env=env,
            capture_output=True,
            text=True,
            timeout=LAUNCH_TIMEOUT_S,
            check=False,
        )

    def test_the_copy_is_refused_even_with_an_installed_engine(self):
        result = self.run_copy("access")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing to run the copy at", result.stderr)

    def test_help_still_answers(self):
        result = self.run_copy("help")
        self.assertEqual(result.returncode, 0, result.stderr)


class OpenWeightFlag(unittest.TestCase):
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
        self.assertIn("no credential mounted", out)
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
        self.assertNotIn("open-weight:", result.stdout)
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
        'if [ "$1" = network ] && [ "$2" = inspect ] && [ "$3" = -f ] && [[ "$4" == *Subnet* ]]; then\n'
        "  echo 172.30.0.0/16\n"
        "fi\n"
        "exit 0\n"
    )


class OpenWeightLaunch(unittest.TestCase):
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

    def launch(self, *flags: str):
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
        }
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
        self, *flags: str, image_labeled: bool = True
    ) -> tuple["subprocess.CompletedProcess[str]", list[str]]:
        write_executable(
            self.bin_dir / "docker", docker_stub(image_labeled=image_labeled)
        )
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
            [f"system prune -a -f --volumes --filter {IMAGE_LABEL.replace('=', '!=')}"],
            calls,
        )

    def test_cleanup_all_refuses_while_the_current_image_is_unlabeled(self):
        # A pre-label image is not spared by label!=, so the verb refuses
        # rather than prune the tool's own current image.
        result, calls = self._run_cleanup("--all", image_labeled=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("predates the claude-dev.image label", result.stderr)
        self.assertEqual([c for c in calls if c.startswith("system prune")], [])


if __name__ == "__main__":
    unittest.main()
