#!/usr/bin/env python3
"""Tests for refresh-gitignore.py (stdlib only).

Run: python3 harness/test_refresh_gitignore.py

Pins the ensure-present contract: channel-aware line selection, exact-line
matching, the one-time header, the final-newline guard, idempotence, and the
never-remove rule.
"""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPT = _HERE / "refresh-gitignore.py"


def _load():
    spec = importlib.util.spec_from_file_location("refresh_gitignore", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rg = _load()

TEMPLATE = (
    "# Handoff ledger\n.scratch/\n\n# runtime\n.claude/skills/*\nscripts/handoff.py\n"
)


class DesiredLines(unittest.TestCase):
    def test_copy_channel_ensures_only_the_ledger(self):
        self.assertEqual(rg.desired_lines(TEMPLATE, "copy"), [".scratch/"])

    def test_offcopy_channels_ensure_every_runtime_path(self):
        for channel in ("manifest", "marketplace"):
            with self.subTest(channel=channel):
                self.assertEqual(
                    rg.desired_lines(TEMPLATE, channel),
                    [".scratch/", ".claude/skills/*", "scripts/handoff.py"],
                )

    def test_comments_and_blanks_are_skipped(self):
        self.assertNotIn("# runtime", rg.desired_lines(TEMPLATE, "manifest"))


class RefreshedText(unittest.TestCase):
    def test_empty_target_gains_header_and_lines(self):
        out, added = rg.refreshed_text("", TEMPLATE, "manifest")
        self.assertEqual(added, 3)
        self.assertIn(
            "# harness runtime (harness-owned; kept current on upgrade)\n", out
        )
        self.assertIn(".scratch/\n", out)
        self.assertTrue(out.endswith("scripts/handoff.py\n"))

    def test_existing_lines_are_not_duplicated(self):
        first, _ = rg.refreshed_text("", TEMPLATE, "manifest")
        second, added = rg.refreshed_text(first, TEMPLATE, "manifest")
        self.assertEqual(added, 0)
        self.assertEqual(second, first)

    def test_header_is_added_once(self):
        first, _ = rg.refreshed_text("", TEMPLATE, "copy")
        second, added = rg.refreshed_text(first, TEMPLATE, "manifest")
        self.assertEqual(added, 2)
        self.assertEqual(second.count("# harness runtime"), 1)

    def test_project_lines_and_reincludes_are_kept_verbatim(self):
        project = "node_modules/\n!.claude/skills/my-extension/\n"
        out, _ = rg.refreshed_text(project, TEMPLATE, "manifest")
        self.assertTrue(out.startswith(project))

    def test_unterminated_final_line_is_not_corrupted(self):
        out, _ = rg.refreshed_text("node_modules/", TEMPLATE, "copy")
        self.assertIn("node_modules/\n", out)
        self.assertNotIn("node_modules/.scratch/", out)

    def test_newline_guard_holds_when_the_header_is_suppressed(self):
        # The header's own leading newline masks the guard on most inputs; a
        # target already carrying the "harness runtime" token suppresses the
        # header, so ONLY the guard keeps the appended path off the project's
        # unterminated final line. Deleting the guard fails here.
        out, _ = rg.refreshed_text(
            "# my harness runtime notes\nmy-own/", TEMPLATE, "manifest"
        )
        self.assertIn("my-own/\n", out)
        self.assertNotIn("my-own/.scratch/", out)
        self.assertEqual(out.count("# harness runtime (harness-owned"), 0)

    def test_exact_line_match_not_substring(self):
        # ".scratch/x" in the target must not mask the ".scratch/" template line.
        out, added = rg.refreshed_text(".scratch/x\n", TEMPLATE, "copy")
        self.assertEqual(added, 1)
        self.assertIn("\n.scratch/\n", out)

    def test_template_dropped_line_is_never_removed(self):
        stale = (
            "# harness runtime (harness-owned; kept current on upgrade)\nold/path.py\n"
        )
        out, added = rg.refreshed_text(stale, TEMPLATE, "copy")
        self.assertIn("old/path.py\n", out)
        self.assertEqual(added, 1)


class CommandLineContract(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(_SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_creates_missing_target_and_reports_count(self):
        with tempfile.TemporaryDirectory() as td:
            template = Path(td) / "block.txt"
            template.write_text(TEMPLATE, encoding="utf-8")
            target = Path(td) / ".gitignore"
            result = self.run_script(str(target), str(template), "manifest")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "gitignore: 3 path(s) added")
            self.assertTrue(target.is_file())

    def test_missing_block_source_fails_loud(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.run_script(
                str(Path(td) / ".gitignore"), str(Path(td) / "no.txt"), "copy"
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("missing block source", result.stderr)

    def test_usage_error(self):
        result = self.run_script("only-one-arg")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
