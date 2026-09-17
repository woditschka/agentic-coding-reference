#!/usr/bin/env python3
"""The ADR index renderer: every malformed input fails loud, the live tree renders drift-free, and rows derive their shape exactly."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load

rai = load("render_adr_index", "render-adr-index.py")

DECISION_FLOOR = 94


class RowDerivation(unittest.TestCase):
    def test_live_rows_have_the_derived_shape(self):
        # The decision log only grows, so its count never drops below the floor.
        rows = rai.adr_rows()
        self.assertGreaterEqual(len(rows), DECISION_FLOOR)
        for row in rows:
            self.assertRegex(
                row, r"^\| \d{4}-\d{2}-\d{2} \| \[[^]]+\]\([a-z0-9.-]+\.md\) \| .+ \|$"
            )

    def test_rows_are_date_ordered(self):
        dates = [row.split(" | ")[0].lstrip("| ") for row in rai.adr_rows()]
        self.assertEqual(dates, sorted(dates))


class Guards(unittest.TestCase):
    def _adr_dir_with(self, name, content):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        (d / name).write_text(content)
        return d

    def test_a_malformed_filename_fails_loud(self):
        with self.assertRaises(SystemExit):
            rai.adr_rows(
                self._adr_dir_with(
                    "2026-8-1-bad-name.md", "# T\n\n**Status:** Accepted\n"
                )
            )

    def test_a_file_without_status_fails_loud(self):
        with self.assertRaises(SystemExit):
            rai.adr_rows(
                self._adr_dir_with("2026-08-21-no-status.md", "# Title\n\nBody only.\n")
            )

    def test_a_file_without_h1_fails_loud(self):
        with self.assertRaises(SystemExit):
            rai.adr_rows(
                self._adr_dir_with("2026-08-21-no-title.md", "**Status:** Accepted\n")
            )

    def test_a_control_character_in_the_status_fails_loud(self):
        content = "# Title\n\n**Status:** Accepted\x1b[31m\n"
        with self.assertRaises(SystemExit):
            rai.adr_rows(self._adr_dir_with("2026-08-21-esc-status.md", content))

    def test_a_bracket_in_the_title_fails_loud(self):
        content = "# T](x.md) forged\n\n**Status:** Accepted\n"
        with self.assertRaises(SystemExit):
            rai.adr_rows(self._adr_dir_with("2026-08-21-bracket-title.md", content))

    def test_image_syntax_in_the_status_fails_loud(self):
        content = "# Title\n\n**Status:** Accepted ![](https://example.test/p)\n"
        with self.assertRaises(SystemExit):
            rai.adr_rows(self._adr_dir_with("2026-08-21-image-status.md", content))

    def test_a_status_link_stays_allowed(self):
        # A supersession pointer legitimately renders as a link in the status cell.
        content = "# Title\n\n**Status:** Superseded by [x](2026-01-01-x.md)\n"
        (row,) = rai.adr_rows(
            self._adr_dir_with("2026-08-21-linked-status.md", content)
        )
        self.assertIn("[x](2026-01-01-x.md)", row)


class RenderAndCheck(unittest.TestCase):
    def test_the_live_tree_is_drift_free(self):
        self.assertEqual(rai.render(), rai.README.read_text(encoding="utf-8"))

    def _render_with_tail(self, extra):
        broken = Path(tempfile.mkdtemp()) / "README.md"
        self.addCleanup(shutil.rmtree, broken.parent, ignore_errors=True)
        broken.write_text(rai.README.read_text(encoding="utf-8") + extra)
        with self.assertRaises(SystemExit):
            rai.render(readme=broken)

    def test_a_heading_after_the_index_fails_loud(self):
        self._render_with_tail("\n## Stray Section\n")

    def test_prose_after_the_index_fails_loud(self):
        self._render_with_tail("\nA stray sentence.\n")

    def test_a_status_legend_after_the_index_fails_loud(self):
        # A regenerate rebuilds the tail from the rows alone, so a waved-through
        # legend line would vanish silently.
        self._render_with_tail("\n**Status:** values are Accepted or Superseded.\n")


if __name__ == "__main__":
    unittest.main()
