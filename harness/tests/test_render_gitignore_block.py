#!/usr/bin/env python3
"""The gitignore-block renderer: line shapes, block order, the doctor roster, and the render-then-check contract."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load

rgb = load("render_gitignore_block", "render-gitignore-block.py")

RENDERED = 0
DRIFT_EXIT = 1
USAGE_EXIT = 2
SOME_PATHS = [".claude/skills", "scripts/handoff.py", "schemas/scratch"]


class IgnoreLines(unittest.TestCase):
    def test_a_directory_ignores_its_contents(self):
        self.assertEqual(rgb.ignore_line(".claude/skills"), ".claude/skills/*")

    def test_a_file_is_ignored_by_name(self):
        self.assertEqual(rgb.ignore_line("scripts/handoff.py"), "scripts/handoff.py")

    def test_a_dotted_directory_segment_does_not_make_a_file(self):
        self.assertEqual(rgb.ignore_line(".claude/agents"), ".claude/agents/*")


class Rendering(unittest.TestCase):
    def test_the_block_is_the_header_then_the_roster_in_order(self):
        content = rgb.render(SOME_PATHS)

        self.assertTrue(content.startswith(rgb.HEADER))
        self.assertEqual(
            content[len(rgb.HEADER) :].splitlines(),
            [".claude/skills/*", "scripts/handoff.py", "schemas/scratch/*"],
        )

    def test_the_ledger_line_leads_the_header(self):
        self.assertIn(f"\n{rgb.LEDGER_LINE}\n", rgb.HEADER)


class DoctorRoster(unittest.TestCase):
    def test_the_roster_reads_from_the_doctor(self):
        paths = rgb.runtime_paths(rgb.DOCTOR)

        self.assertIn("scripts/handoff.py", paths)
        self.assertIn(".claude/skills", paths)

    def test_a_doctor_without_a_roster_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "doctor.py"
            stub.write_text("RUNTIME_PATHS = 'x'\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                rgb.runtime_paths(stub)


class RenderThenCheck(unittest.TestCase):
    def test_the_committed_block_matches_the_roster(self):
        self.assertEqual(rgb.main(["render-gitignore-block.py", "--check"]), RENDERED)

    def test_a_drifted_copy_fails_the_check_until_rerendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "gitignore-runtime.txt"
            output.write_text("stale\n", encoding="utf-8")
            original = rgb.OUTPUT
            rgb.OUTPUT = output
            try:
                self.assertEqual(
                    rgb.main(["render-gitignore-block.py", "--check"]), DRIFT_EXIT
                )
                self.assertEqual(rgb.main(["render-gitignore-block.py"]), RENDERED)
                self.assertEqual(
                    rgb.main(["render-gitignore-block.py", "--check"]), RENDERED
                )
            finally:
                rgb.OUTPUT = original

    def test_an_unknown_flag_is_a_usage_error(self):
        self.assertEqual(rgb.main(["render-gitignore-block.py", "--bogus"]), USAGE_EXIT)


if __name__ == "__main__":
    unittest.main()
