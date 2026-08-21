#!/usr/bin/env python3
"""Tests for render-adr-index.py (stdlib only).

Run: python3 harness/tests/test_render_adr_index.py

Pins the generator guards: a malformed ADR filename, a file without an H1
or status line, a control character or link-breaking bracket in a derived
cell, image syntax in a status, and any non-table line after '## Index'
all fail loudly
(never a partial or truncating render); the live tree renders drift-free
with a plausible row count; and the row shape derives date, title link,
and status exactly. Guard fixtures live in a temp directory — the tests
never write into the live docs/adr/ tree.
"""

import shutil
import sys
import tempfile
import unittest
import unittest.mock as mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import load  # noqa: E402

rai = load("render_adr_index", "render-adr-index.py")


class RowDerivation(unittest.TestCase):
    def test_live_rows_have_the_derived_shape(self):
        rows = rai.adr_rows()
        # The 2026-08-21 log holds 94 decisions; the log only grows.
        self.assertGreaterEqual(len(rows), 94)
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
        return mock.patch.object(rai, "ADR_DIR", d)

    def test_a_malformed_filename_fails_loud(self):
        with (
            self._adr_dir_with("2026-8-1-bad-name.md", "# T\n\n**Status:** Accepted\n"),
            self.assertRaises(SystemExit),
        ):
            rai.adr_rows()

    def test_a_file_without_status_fails_loud(self):
        with (
            self._adr_dir_with("2026-08-21-no-status.md", "# Title\n\nBody only.\n"),
            self.assertRaises(SystemExit),
        ):
            rai.adr_rows()

    def test_a_file_without_h1_fails_loud(self):
        with (
            self._adr_dir_with("2026-08-21-no-title.md", "**Status:** Accepted\n"),
            self.assertRaises(SystemExit),
        ):
            rai.adr_rows()

    def test_a_control_character_in_the_status_fails_loud(self):
        content = "# Title\n\n**Status:** Accepted\x1b[31m\n"
        with (
            self._adr_dir_with("2026-08-21-esc-status.md", content),
            self.assertRaises(SystemExit),
        ):
            rai.adr_rows()

    def test_a_bracket_in_the_title_fails_loud(self):
        content = "# T](x.md) forged\n\n**Status:** Accepted\n"
        with (
            self._adr_dir_with("2026-08-21-bracket-title.md", content),
            self.assertRaises(SystemExit),
        ):
            rai.adr_rows()

    def test_image_syntax_in_the_status_fails_loud(self):
        content = "# Title\n\n**Status:** Accepted ![](https://example.test/p)\n"
        with (
            self._adr_dir_with("2026-08-21-image-status.md", content),
            self.assertRaises(SystemExit),
        ):
            rai.adr_rows()

    def test_a_status_link_stays_allowed(self):
        # Supersession pointers legitimately render as links in the status
        # cell; the injection guards must not refuse them.
        content = "# Title\n\n**Status:** Superseded by [x](2026-01-01-x.md)\n"
        with self._adr_dir_with("2026-08-21-linked-status.md", content):
            (row,) = rai.adr_rows()
        self.assertIn("[x](2026-01-01-x.md)", row)


class RenderAndCheck(unittest.TestCase):
    def test_the_live_tree_is_drift_free(self):
        # The committed README must equal a fresh render — the same
        # comparison battery step 3l runs.
        self.assertEqual(rai.render(), rai.README.read_text(encoding="utf-8"))

    def _render_with_tail(self, extra):
        broken = rai.README.read_text(encoding="utf-8") + extra
        with (
            mock.patch.object(rai.Path, "read_text", return_value=broken),
            self.assertRaises(SystemExit),
        ):
            rai.render()

    def test_a_heading_after_the_index_fails_loud(self):
        self._render_with_tail("\n## Stray Section\n")

    def test_prose_after_the_index_fails_loud(self):
        self._render_with_tail("\nA stray sentence.\n")

    def test_a_status_legend_after_the_index_fails_loud(self):
        # A regenerate rebuilds the tail from the rows alone; a waved-through
        # legend line would vanish silently, so it must refuse instead.
        self._render_with_tail("\n**Status:** values are Accepted or Superseded.\n")


if __name__ == "__main__":
    unittest.main()
