#!/usr/bin/env python3
"""Pin the chapter algebra, stamp upsert, and apply contract of refresh-chapters.py."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Run as a standalone script, sys.path[0] is this claude-md/ subdir; the
# shared loader lives one level up in tests/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _loader import ROOT, load

_SCRIPT = ROOT / "claude-md/refresh-chapters.py"

rc = load("refresh_chapters", "claude-md/refresh-chapters.py")

MEMORY_HEADING = "## Memory"
SCRATCH_HEADING = "## Scratch Directory"
SOURCE_CHAPTERS = (MEMORY_HEADING, SCRATCH_HEADING)
FENCED_HEADING = "## Not A Chapter"

NEW_MEMORY_DOCTRINE = "Managed memory doctrine, v2."
NEW_SCRATCH_DOCTRINE = "Managed scratch doctrine, v2."
OLD_MEMORY_DOCTRINE = "Old memory doctrine."
OLD_SCRATCH_DOCTRINE = "Old scratch doctrine."
PROJECT_PROSE = "Project prose."
PROJECT_HEADING = "## Build Commands"
FENCED_COMMAND = "make test"

STALE_DATE = "2026-01-01"
NEW_DATE = "2026-07-05"
SYMLINK_BOUND = 10
NOT_STAMPED = "date not stamped (no VERSION-DATE)"

SOURCE = f"""{MEMORY_HEADING}

{NEW_MEMORY_DOCTRINE}

{SCRATCH_HEADING}

{NEW_SCRATCH_DOCTRINE}

```text
{FENCED_HEADING}
```
"""

TARGET = f"""# CLAUDE.md

{PROJECT_PROSE}

{MEMORY_HEADING}

{OLD_MEMORY_DOCTRINE}

{PROJECT_HEADING}

```bash
{FENCED_COMMAND}
{MEMORY_HEADING}
```

{SCRATCH_HEADING}

{OLD_SCRATCH_DOCTRINE}
"""


def stamp(date: str) -> str:
    return f"<!-- harness: {date} -->"


class ChapterAlgebra(unittest.TestCase):
    def test_titles_are_fence_aware(self):
        self.assertEqual(rc.chapter_titles(SOURCE.splitlines()), list(SOURCE_CHAPTERS))

    def test_heading_present_ignores_fenced_mentions(self):
        lines = TARGET.splitlines()
        self.assertTrue(rc.heading_present(lines, MEMORY_HEADING))
        self.assertFalse(rc.heading_present(lines, "## Absent"))
        real = lines.index(MEMORY_HEADING)
        without = lines[:real] + lines[real + 1 :]
        self.assertFalse(rc.heading_present(without, MEMORY_HEADING))

    def test_extract_trims_trailing_blanks_and_keeps_fences(self):
        chapter = rc.extract_chapter(SOURCE.splitlines(), SCRATCH_HEADING)
        self.assertEqual(chapter[0], SCRATCH_HEADING)
        self.assertEqual(chapter[-1], "```")
        self.assertIn(FENCED_HEADING, chapter)

    def test_replace_swaps_only_the_named_chapter(self):
        out = rc.replace_chapter(
            TARGET.splitlines(),
            [MEMORY_HEADING, "", NEW_MEMORY_DOCTRINE],
            MEMORY_HEADING,
        )
        text = "\n".join(out)
        self.assertIn(NEW_MEMORY_DOCTRINE, text)
        self.assertNotIn(OLD_MEMORY_DOCTRINE, text)
        self.assertIn(OLD_SCRATCH_DOCTRINE, text)
        self.assertIn(FENCED_COMMAND, text)
        self.assertIn(PROJECT_PROSE, text)

    def test_replace_keeps_single_blank_before_next_heading(self):
        out = rc.replace_chapter(
            TARGET.splitlines(), [MEMORY_HEADING, "", "New."], MEMORY_HEADING
        )
        i = out.index("New.")
        self.assertEqual(out[i + 1], "")
        self.assertEqual(out[i + 2], PROJECT_HEADING)

    def test_replacing_the_last_chapter_keeps_it_last(self):
        out = rc.replace_chapter(
            TARGET.splitlines(),
            [SCRATCH_HEADING, "", "New scratch."],
            SCRATCH_HEADING,
        )
        self.assertEqual(out[-1], "New scratch.")


class StampUpsert(unittest.TestCase):
    def test_stamp_prepends_and_replaces(self):
        out = rc.stamp_date([stamp(STALE_DATE), "# CLAUDE.md"], NEW_DATE)
        self.assertEqual(out[0], stamp(NEW_DATE))
        self.assertEqual(out.count(stamp(NEW_DATE)), 1)
        self.assertNotIn(stamp(STALE_DATE), out)

    def test_stamp_removes_indented_stale_stamp(self):
        out = rc.stamp_date([f"  {stamp(STALE_DATE)}", "# X"], NEW_DATE)
        self.assertEqual(out, [stamp(NEW_DATE), "# X"])


class ApplyContract(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.source = self.root / "claude-md" / "managed-chapters.md"
        self.source.parent.mkdir()
        self.source.write_text(SOURCE, encoding="utf-8")
        self.claude = self.root / "CLAUDE.md"
        self.claude.write_text(TARGET, encoding="utf-8")

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
            result.stdout.strip(), f"{len(SOURCE_CHAPTERS)} refreshed, {NOT_STAMPED}"
        )
        text = self.claude.read_text(encoding="utf-8")
        self.assertIn(NEW_MEMORY_DOCTRINE, text)
        self.assertIn(NEW_SCRATCH_DOCTRINE, text)

    def test_version_date_is_read_from_root_and_stamped(self):
        (self.root / "VERSION-DATE").write_text(f"{NEW_DATE}\n", encoding="utf-8")
        result = self.run_script(str(self.claude), str(self.root))
        self.assertIn(f", date {NEW_DATE} stamped", result.stdout)
        first = self.claude.read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(first, stamp(NEW_DATE))

    def test_refresh_is_idempotent(self):
        self.run_script(str(self.claude), str(self.root))
        once = self.claude.read_text(encoding="utf-8")
        self.run_script(str(self.claude), str(self.root))
        self.assertEqual(self.claude.read_text(encoding="utf-8"), once)

    def test_absent_chapter_is_reported_and_left_for_init(self):
        self.claude.write_text(f"# P\n\n{MEMORY_HEADING}\n\nold\n", encoding="utf-8")
        result = self.run_script(str(self.claude), str(self.root))
        self.assertEqual(
            result.stdout.strip(),
            f"1 refreshed, 1 absent: {SCRATCH_HEADING}, {NOT_STAMPED}",
        )

    def test_duplicate_source_heading_fails_before_any_write(self):
        self.source.write_text(
            f"{MEMORY_HEADING}\n\nfirst\n\n{MEMORY_HEADING}\n\ndup\n", encoding="utf-8"
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
        self.source.write_text(f"prose first\n\n{MEMORY_HEADING}\n", encoding="utf-8")
        result = self.run_script(str(self.claude), str(self.root))
        self.assertEqual(result.returncode, 1)
        self.assertIn("must start with a '## ' heading", result.stderr)

    def test_symlinked_target_updates_backing_file_and_stays_a_link(self):
        real = self.root / "real-CLAUDE.md"
        self.claude.replace(real)
        self.claude.symlink_to(real.name)
        result = self.run_script(str(self.claude), str(self.root))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(self.claude.is_symlink())
        self.assertIn(NEW_MEMORY_DOCTRINE, real.read_text(encoding="utf-8"))

    def test_symlink_cycle_fails_loud_instead_of_hanging(self):
        # Unit-level: the CLI's existence check refuses a cyclic target first,
        # so the bound is reachable only on the write path.
        a = self.root / "a.md"
        b = self.root / "b.md"
        a.symlink_to(b.name)
        b.symlink_to(a.name)
        with self.assertRaises(SystemExit) as ctx:
            rc.resolve_symlink(a)
        self.assertIn("symlink chain", str(ctx.exception))
        self.assertIn(str(a), str(ctx.exception))

    def test_symlink_chain_within_bound_still_resolves(self):
        real = self.root / "real-CLAUDE.md"
        self.claude.replace(real)
        prev = real
        for i in range(SYMLINK_BOUND):
            link = self.root / f"link{i}.md"
            link.symlink_to(prev.name)
            prev = link
        result = self.run_script(str(prev), str(self.root))
        self.assertEqual(result.returncode, 0)
        self.assertIn(NEW_MEMORY_DOCTRINE, real.read_text(encoding="utf-8"))

    def test_missing_target_and_missing_source_fail(self):
        self.assertEqual(
            self.run_script(str(self.root / "no.md"), str(self.root)).returncode, 1
        )
        result = self.run_script(str(self.claude), str(self.root / "nowhere"))
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing chapter source", result.stderr)


if __name__ == "__main__":
    unittest.main()
