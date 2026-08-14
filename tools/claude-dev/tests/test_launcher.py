#!/usr/bin/env python3
"""Tests for the launcher's mount-source fence, driven through the real script.

The `access` verb assembles the launch plan with the launcher's own code and
exits before any docker object is created, so each case runs the shipped
bash end to end. HOME and CLAUDE_DEV_HOME point into a per-test temp tree:
the launcher's ~/.claude bootstrap and state writes never touch the invoking
user's home, and the fence comparisons see only paths the test laid out.
"""

import os
import pathlib
import subprocess
import tempfile
import unittest

LAUNCHER = pathlib.Path(__file__).resolve().parent.parent / "claude-dev"


class MountFence(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = pathlib.Path(self._tmp.name).resolve()
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
            timeout=60,
        )

    def assert_refused(self, result, *needles: str):
        self.assertNotEqual(result.returncode, 0)
        for needle in ("may not mount", *needles):
            self.assertIn(needle, result.stderr)

    # ── a source inside the data dir (the fence that predates the ancestor rule) ──

    def test_rw_source_inside_the_data_dir_is_refused(self):
        inside = self.data / "auth"
        inside.mkdir()
        self.assert_refused(self.access("--rw", str(inside)))

    # ── a source containing the data dir ──

    def test_rw_source_containing_the_data_dir_is_refused(self):
        outer = self.tmp / "outer"
        nested = outer / "claude-dev-home"
        nested.mkdir(parents=True)
        result = self.access("--rw", str(outer), data=nested)
        self.assert_refused(result, "it contains", str(nested))

    def test_ro_source_containing_the_data_dir_is_refused(self):
        outer = self.tmp / "outer"
        nested = outer / "claude-dev-home"
        nested.mkdir(parents=True)
        result = self.access("--ro", str(outer), data=nested)
        self.assert_refused(result, "it contains", str(nested))

    # ── a writable source containing ~/.claude ──

    def test_rw_source_containing_home_claude_is_refused(self):
        # self.data sits outside self.tmp/"nest", so the data-dir rules stay
        # quiet and the refusal exercised is the ~/.claude ancestor one.
        nest = self.tmp / "nest"
        self.home = nest / "home"
        self.home.mkdir(parents=True)
        result = self.access("--rw", str(nest))
        self.assert_refused(result, "it contains", str(self.home / ".claude"))

    def test_ro_source_containing_home_claude_is_shareable(self):
        # The ~/.claude fence is write-only by design: read-only sharing of
        # behavior config is the documented mechanism.
        nest = self.tmp / "nest"
        self.home = nest / "home"
        self.home.mkdir(parents=True)
        result = self.access("--ro", str(nest))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nest", result.stdout)

    # ── the filesystem root ──

    def test_rw_root_is_refused(self):
        self.assert_refused(self.access("--rw", "/"), "filesystem root")

    # ── the fence does not over-refuse ──

    def test_plain_extra_ro_source_is_listed(self):
        extra = self.tmp / "shared-assets"
        extra.mkdir()
        result = self.access("--ro", str(extra))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("shared-assets", result.stdout)


class CleanupVerb(unittest.TestCase):
    """The cleanup verb, driven through a stub docker on PATH.

    The stub records every docker invocation and answers `ps -a` with one
    dead-launcher and one live-launcher container, so the assertions pin
    the verb's whole engine surface: reap by launcher label and liveness,
    prune by the image label, no unscoped removal. A stub ps(1) makes the
    liveness probe deterministic: exactly one PID reads as alive. Running
    from $HOME shows the verb exits before the project-directory fences.
    """

    LIVE_PID = 4242
    DEAD_PID = 99999

    def _run_cleanup(
        self, *flags: str, image_labeled: bool = True
    ) -> tuple["subprocess.CompletedProcess[str]", list[str]]:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp).resolve()
            home = tmp_path / "home"
            data = tmp_path / "data"
            bin_dir = tmp_path / "bin"
            for d in (home, data, bin_dir):
                d.mkdir()
            (data / "host-id").write_text("testhost\n")
            log = tmp_path / "docker.log"
            stub = bin_dir / "docker"
            stub.write_text(
                "#!/usr/bin/env bash\n"
                'printf \'%s\\n\' "$*" >> "$DOCKER_LOG"\n'
                '[ "$1" = context ] && exit 1\n'  # no rancher-desktop context: bare `docker`
                'if [ "$1" = ps ]; then\n'
                f"  printf 'claude-dev-stale\\ttesthost:{self.DEAD_PID}\\n'\n"
                f"  printf 'claude-dev-live\\ttesthost:{self.LIVE_PID}\\n'\n"
                "fi\n"
                'if [ "$1" = image ] && [ "$2" = inspect ]; then\n'
                f'  echo "{("1" if image_labeled else "")}"\n'
                "fi\n"
                "exit 0\n"
            )
            stub.chmod(0o755)
            # The launcher probes liveness with `ps -p <pid>`; this stub makes
            # the probe deterministic (and sandbox-independent): only LIVE_PID
            # reads as alive.
            ps_stub = bin_dir / "ps"
            ps_stub.write_text(
                "#!/usr/bin/env bash\n"
                f'[ "$1" = -p ] && [ "$2" = {self.LIVE_PID} ] && exit 0\n'
                "exit 1\n"
            )
            ps_stub.chmod(0o755)
            env = {
                "PATH": f"{bin_dir}:{os.environ.get('PATH', '/usr/bin:/bin')}",
                "HOME": str(home),
                "CLAUDE_DEV_HOME": str(data),
                "DOCKER_LOG": str(log),
            }
            result = subprocess.run(
                [str(LAUNCHER), "cleanup", *flags],
                cwd=str(home),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            calls = log.read_text().splitlines() if log.exists() else []
            return result, calls

    def test_cleanup_reaps_and_prunes_by_label_only(self):
        result, calls = self._run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cleanup done", result.stderr)
        self.assertIn("image prune -f --filter label=claude-dev.image", calls)
        self.assertTrue(
            any(
                c.startswith("ps -a --filter label=claude-dev.launcher") for c in calls
            ),
            calls,
        )
        # The reaper removes the dead launcher's container and spares the live one.
        self.assertIn("rm -f claude-dev-stale", calls)
        self.assertNotIn("rm -f claude-dev-live", calls)
        unscoped = [
            c for c in calls if "prune" in c and "label=claude-dev.image" not in c
        ]
        self.assertEqual(unscoped, [], "cleanup must never prune outside its label")

    def test_cleanup_all_adds_engine_wide_prune_sparing_the_image(self):
        result, calls = self._run_cleanup("--all")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("cleanup --all done", result.stderr)
        # The scoped pass still runs first ...
        self.assertIn("image prune -f --filter label=claude-dev.image", calls)
        # ... then exactly one engine-wide prune, filtered to keep the image.
        system_prunes = [c for c in calls if c.startswith("system prune")]
        self.assertEqual(
            system_prunes,
            ["system prune -a -f --volumes --filter label!=claude-dev.image"],
            calls,
        )

    def test_cleanup_all_refuses_while_current_image_is_unlabeled(self):
        # A pre-label image is not spared by label!= — the verb must refuse
        # rather than prune the tool's own current image.
        result, calls = self._run_cleanup("--all", image_labeled=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("predates the claude-dev.image label", result.stderr)
        self.assertEqual([c for c in calls if c.startswith("system prune")], [])


if __name__ == "__main__":
    unittest.main()
