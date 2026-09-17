#!/usr/bin/env python3
"""Tests for the launcher's mount fence and cleanup verb, driven through the shipped script."""

import os
import pathlib
import subprocess
import tempfile
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
