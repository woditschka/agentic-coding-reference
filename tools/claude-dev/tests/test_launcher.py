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


if __name__ == "__main__":
    unittest.main()
