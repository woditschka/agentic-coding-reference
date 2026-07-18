#!/usr/bin/env python3
"""Tests for refresh-chapters.py (stdlib only).

Run: python3 harness/tests/claude-md/test_refresh_chapters.py

Pins the chapter algebra (fence-aware heading detection, extraction with
trailing-blank trim, in-place replacement with a single separating blank),
the stamp upsert, the malformed-source pre-flight (fail before any write),
the CRLF refusal, symlink preservation, and the report line format.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Run as a standalone script, sys.path[0] is this claude-md/ subdir; the
# shared loader lives one level up in tests/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _loader import ROOT, load  # noqa: E402

_SCRIPT = ROOT / "claude-md/refresh-chapters.py"

rc = load("refresh_chapters", "claude-md/refresh-chapters.py")

SOURCE = """## Memory

Managed memory doctrine, v2.

## Scratch Directory

Managed scratch doctrine, v2.

```text
## Not A Chapter
```
"""

TARGET = """# CLAUDE.md

Project prose.

## Memory

Old memory doctrine.

## Build Commands

```bash
make test
## Memory
```

## Scratch Directory

Old scratch doctrine.
"""


class ChapterAlgebra(unittest.TestCase):
    def test_titles_are_fence_aware(self):
        self.assertEqual(
            rc.chapter_titles(SOURCE.splitlines()),
            ["## Memory", "## Scratch Directory"],
        )

    def test_heading_present_ignores_fenced_mentions(self):
        lines = TARGET.splitlines()
        self.assertTrue(rc.heading_present(lines, "## Memory"))
        self.assertFalse(rc.heading_present(lines, "## Absent"))
        # "## Memory" also appears inside the bash fence; remove the real one
        # and the fenced mention must not count.
        without = [l for i, l in enumerate(lines) if not (l == "## Memory" and i < 8)]
        self.assertFalse(rc.heading_present(without, "## Memory"))

    def test_extract_trims_trailing_blanks_and_keeps_fences(self):
        chapter = rc.extract_chapter(SOURCE.splitlines(), "## Scratch Directory")
        self.assertEqual(chapter[0], "## Scratch Directory")
        self.assertEqual(chapter[-1], "```")
        self.assertIn("## Not A Chapter", chapter)

    def test_replace_swaps_only_the_named_chapter(self):
        out = rc.replace_chapter(
            TARGET.splitlines(),
            ["## Memory", "", "Managed memory doctrine, v2."],
            "## Memory",
        )
        text = "\n".join(out)
        self.assertIn("Managed memory doctrine, v2.", text)
        self.assertNotIn("Old memory doctrine.", text)
        self.assertIn("Old scratch doctrine.", text)  # untouched sibling
        self.assertIn("make test", text)  # fenced block intact
        self.assertIn("Project prose.", text)

    def test_replace_keeps_single_blank_before_next_heading(self):
        out = rc.replace_chapter(
            TARGET.splitlines(), ["## Memory", "", "New."], "## Memory"
        )
        i = out.index("New.")
        self.assertEqual(out[i + 1], "")
        self.assertEqual(out[i + 2], "## Build Commands")

    def test_replace_at_end_of_file(self):
        out = rc.replace_chapter(
            TARGET.splitlines(),
            ["## Scratch Directory", "", "New scratch."],
            "## Scratch Directory",
        )
        self.assertEqual(out[-1], "New scratch.")


class StampUpsert(unittest.TestCase):
    def test_stamp_prepends_and_replaces(self):
        lines = ["<!-- harness: 2026-01-01 -->", "# CLAUDE.md"]
        out = rc.stamp_date(lines, "2026-07-05")
        self.assertEqual(out[0], "<!-- harness: 2026-07-05 -->")
        self.assertEqual(out.count("<!-- harness: 2026-07-05 -->"), 1)
        self.assertNotIn("<!-- harness: 2026-01-01 -->", out)

    def test_stamp_removes_indented_stale_stamp(self):
        out = rc.stamp_date(["  <!-- harness: 2026-01-01 -->", "# X"], "2026-07-05")
        self.assertEqual(out, ["<!-- harness: 2026-07-05 -->", "# X"])


class ApplyContract(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / "claude-md").mkdir()
        (self.root / "claude-md" / "managed-chapters.md").write_text(
            SOURCE, encoding="utf-8"
        )
        self.claude = self.root / "CLAUDE.md"
        self.claude.write_text(TARGET, encoding="utf-8")

    def tearDown(self):
        self.td.cleanup()

    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, str(_SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_refresh_reports_and_replaces(self):
        result = self.run_script(str(self.claude), str(self.root))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            result.stdout.strip(),
            "2 refreshed, date not stamped (no VERSION-DATE)",
        )
        text = self.claude.read_text(encoding="utf-8")
        self.assertIn("Managed memory doctrine, v2.", text)
        self.assertIn("Managed scratch doctrine, v2.", text)

    def test_version_date_is_read_from_root_and_stamped(self):
        (self.root / "VERSION-DATE").write_text("2026-07-05\n", encoding="utf-8")
        result = self.run_script(str(self.claude), str(self.root))
        self.assertIn(", date 2026-07-05 stamped", result.stdout)
        first = self.claude.read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(first, "<!-- harness: 2026-07-05 -->")

    def test_refresh_is_idempotent(self):
        self.run_script(str(self.claude), str(self.root))
        once = self.claude.read_text(encoding="utf-8")
        self.run_script(str(self.claude), str(self.root))
        self.assertEqual(self.claude.read_text(encoding="utf-8"), once)

    def test_absent_chapter_is_reported_and_left_for_init(self):
        self.claude.write_text("# P\n\n## Memory\n\nold\n", encoding="utf-8")
        result = self.run_script(str(self.claude), str(self.root))
        self.assertEqual(
            result.stdout.strip(),
            "1 refreshed, 1 absent: ## Scratch Directory, date not stamped (no VERSION-DATE)",
        )

    def test_duplicate_source_heading_fails_before_any_write(self):
        (self.root / "claude-md" / "managed-chapters.md").write_text(
            "## Memory\n\nfirst\n\n## Memory\n\ndup\n", encoding="utf-8"
        )
        before = self.claude.read_text(encoding="utf-8")
        result = self.run_script(str(self.claude), str(self.root))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate", result.stderr)
        self.assertEqual(self.claude.read_text(encoding="utf-8"), before)

    def test_crlf_target_refused_loudly_and_untouched(self):
        self.claude.write_bytes(b"# P\r\n## Memory\r\nold\r\n")
        before = self.claude.read_bytes()
        result = self.run_script(str(self.claude), str(self.root))
        self.assertEqual(result.returncode, 0)
        self.assertIn("CRLF", result.stdout)
        self.assertEqual(self.claude.read_bytes(), before)

    def test_source_not_starting_with_heading_fails(self):
        (self.root / "claude-md" / "managed-chapters.md").write_text(
            "prose first\n\n## Memory\n", encoding="utf-8"
        )
        result = self.run_script(str(self.claude), str(self.root))
        self.assertEqual(result.returncode, 1)
        self.assertIn("must start with a '## ' heading", result.stderr)

    def test_symlinked_target_updates_backing_file_and_stays_a_link(self):
        real = self.root / "real-CLAUDE.md"
        os.replace(self.claude, real)
        self.claude.symlink_to(real.name)
        result = self.run_script(str(self.claude), str(self.root))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.claude.is_symlink())
        self.assertIn("Managed memory doctrine, v2.", real.read_text(encoding="utf-8"))

    def test_symlink_cycle_fails_loud_instead_of_hanging(self):
        # The 10-link bound in resolve_symlink: a cycle previously walked
        # forever. Unit-level — via the CLI the existence check refuses a
        # cyclic target first (a cycle stats as missing); the bound guards
        # the write path, where the cycle can appear after that check.
        a = self.root / "a.md"
        b = self.root / "b.md"
        a.symlink_to(b.name)
        b.symlink_to(a.name)
        with self.assertRaises(SystemExit) as ctx:
            rc.resolve_symlink(a)
        self.assertIn("symlink chain", str(ctx.exception))
        self.assertIn(str(a), str(ctx.exception))

    def test_symlink_chain_within_bound_still_resolves(self):
        # Off-by-one guard on the bound: a legal 10-link chain resolves to
        # the backing file; only the 11th resolution fails.
        real = self.root / "real-CLAUDE.md"
        os.replace(self.claude, real)
        prev = real
        for i in range(10):
            link = self.root / f"link{i}.md"
            link.symlink_to(prev.name)
            prev = link
        result = self.run_script(str(prev), str(self.root))
        self.assertEqual(result.returncode, 0)
        self.assertIn("Managed memory doctrine, v2.", real.read_text(encoding="utf-8"))

    def test_missing_target_and_missing_source_fail(self):
        self.assertEqual(
            self.run_script(str(self.root / "no.md"), str(self.root)).returncode, 1
        )
        result = self.run_script(str(self.claude), str(self.root / "nowhere"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing chapter source", result.stderr)


if __name__ == "__main__":
    unittest.main()
