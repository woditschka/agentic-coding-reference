#!/usr/bin/env python3
"""The gitignore refresh: channel-aware ensure-present lines under a one-time header, never removing anything."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import ROOT, load

_SCRIPT = ROOT / "refresh-gitignore.py"

rg = load("refresh_gitignore", "refresh-gitignore.py")

COPY = "copy"
MANIFEST = "manifest"
OFFCOPY_CHANNELS = (MANIFEST, "marketplace")
TEMPLATE = (
    "# Handoff ledger\n.scratch/\n\n# runtime\n.claude/skills/*\nscripts/handoff.py\n"
)
COPY_LINES = [".scratch/"]
OFFCOPY_LINES = [".scratch/", ".claude/skills/*", "scripts/handoff.py"]


class DesiredLines(unittest.TestCase):
    def test_the_copy_channel_ensures_only_the_ledger(self):
        self.assertEqual(rg.desired_lines(TEMPLATE, COPY), COPY_LINES)

    def test_an_offcopy_channel_ensures_every_runtime_path(self):
        for channel in OFFCOPY_CHANNELS:
            with self.subTest(channel=channel):
                self.assertEqual(rg.desired_lines(TEMPLATE, channel), OFFCOPY_LINES)

    def test_comments_and_blanks_are_skipped(self):
        self.assertNotIn("# runtime", rg.desired_lines(TEMPLATE, MANIFEST))


class RefreshedText(unittest.TestCase):
    def test_an_empty_target_gains_the_header_and_every_line(self):
        out, added = rg.refreshed_text("", TEMPLATE, MANIFEST)
        self.assertEqual(added, len(OFFCOPY_LINES))
        self.assertIn(rg.HEADER, out)
        self.assertIn(".scratch/\n", out)
        self.assertTrue(out.endswith("scripts/handoff.py\n"))

    def test_existing_lines_are_not_duplicated(self):
        first, _ = rg.refreshed_text("", TEMPLATE, MANIFEST)
        second, added = rg.refreshed_text(first, TEMPLATE, MANIFEST)
        self.assertEqual(added, 0)
        self.assertEqual(second, first)

    def test_the_header_is_added_once(self):
        first, _ = rg.refreshed_text("", TEMPLATE, COPY)
        second, added = rg.refreshed_text(first, TEMPLATE, MANIFEST)
        self.assertEqual(added, len(OFFCOPY_LINES) - len(COPY_LINES))
        self.assertEqual(second.count(rg.MARKER), 1)

    def test_project_lines_and_reincludes_are_kept_verbatim(self):
        project = "node_modules/\n!.claude/skills/my-extension/\n"
        out, _ = rg.refreshed_text(project, TEMPLATE, MANIFEST)
        self.assertTrue(out.startswith(project))

    def test_an_unterminated_final_line_is_not_corrupted(self):
        out, _ = rg.refreshed_text("node_modules/", TEMPLATE, COPY)
        self.assertIn("node_modules/\n", out)
        self.assertNotIn("node_modules/.scratch/", out)

    def test_the_newline_guard_holds_when_the_header_is_suppressed(self):
        # A target already carrying the marker suppresses the header, whose
        # leading newline otherwise masks the guard; only the guard keeps the
        # appended path off the unterminated final line.
        out, _ = rg.refreshed_text(
            "# my harness runtime notes\nmy-own/", TEMPLATE, MANIFEST
        )
        self.assertIn("my-own/\n", out)
        self.assertNotIn("my-own/.scratch/", out)
        self.assertNotIn(rg.HEADER, out)

    def test_a_target_line_extending_a_template_line_does_not_mask_it(self):
        out, added = rg.refreshed_text(".scratch/x\n", TEMPLATE, COPY)
        self.assertEqual(added, len(COPY_LINES))
        self.assertIn("\n.scratch/\n", out)

    def test_a_line_the_template_dropped_is_never_removed(self):
        stale = rg.HEADER + "old/path.py\n"
        out, added = rg.refreshed_text(stale, TEMPLATE, COPY)
        self.assertIn("old/path.py\n", out)
        self.assertEqual(added, len(COPY_LINES))


class CommandLineContract(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(_SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_a_missing_target_is_created_and_the_count_reported(self):
        with tempfile.TemporaryDirectory() as td:
            template = Path(td) / "block.txt"
            template.write_text(TEMPLATE, encoding="utf-8")
            target = Path(td) / ".gitignore"
            result = self.run_script(str(target), str(template), MANIFEST)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                result.stdout.strip(),
                f"gitignore: {len(OFFCOPY_LINES)} path(s) added",
            )
            self.assertTrue(target.is_file())

    def test_a_missing_block_source_fails_loud(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.run_script(
                str(Path(td) / ".gitignore"), str(Path(td) / "no.txt"), COPY
            )
            self.assertEqual(result.returncode, rg.FAILURE_EXIT)
            self.assertIn("missing block source", result.stderr)

    def test_a_single_argument_is_a_usage_error(self):
        result = self.run_script("only-one-arg")
        self.assertEqual(result.returncode, rg.USAGE_EXIT)


if __name__ == "__main__":
    unittest.main()
