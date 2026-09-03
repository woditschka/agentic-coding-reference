"""Tests for grading.coverage — the slice's test-coverage map.

Run (from the scripts dir): python3 -m unittest tests.grading.test_coverage
Stdlib only.
"""

import os
import tempfile
import unittest
from pathlib import Path

from grading.coverage import coverage_map, done_when_bullets, edge_cases_for, render

# The shipped PRD form (doctor template): backticked ids in the Done-when
# list, a bold "Edge cases:" label, capability groups under ### headings.
PRD = """## Requirements

Owners `[REQ-OWN-001]` are the first capability; edge cases are listed per group.

### Owner records

<a id="req-own-001"></a>
Owners are listed `[REQ-OWN-001]` and edited `[REQ-OWN-002]`.

**Done when:**
- `[REQ-OWN-001]` given a page below the first, when the listing renders, then it shows page one.
- `[REQ-OWN-002]` given an edit, when saved, then the record updates.

**Edge cases:**
1. A search whose text is entirely spaces behaves as an empty search.
2. A request for an owner that does not exist is refused.

**Notes:**
1. This numbered list is not an edge case.

### Visits

Visits are booked `[REQ-VIS-001]`.

## Open Questions

1. Not an edge case either.
"""


class TestCoverageMap(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "docs" / "prd.md").write_text(PRD, encoding="utf-8")
        (self.root / "src" / "test").mkdir(parents=True)

    def _test_file(self, name, body):
        (self.root / "src" / "test" / name).write_text(body, encoding="utf-8")

    def test_done_when_bullets_match_the_shipped_backticked_form(self):
        self.assertEqual(
            done_when_bullets(PRD, "REQ-OWN-001"),
            [
                "given a page below the first, when the listing renders, then it shows page one."
            ],
        )
        self.assertEqual(
            done_when_bullets("- **[REQ-X-001]** bold form", "REQ-X-001"), ["bold form"]
        )
        self.assertEqual(done_when_bullets(PRD, "REQ-VIS-001"), [])

    def test_edge_cases_come_from_the_anchored_group_and_stop_at_the_next_label(self):
        # The preamble mentions REQ-OWN-001 too; the anchored ### section wins,
        # and the Notes list after the edge cases is never captured.
        group, cases = edge_cases_for(PRD, "REQ-OWN-001")
        self.assertEqual(group, "Owner records")
        self.assertEqual([n for n, _ in cases], [1, 2])
        self.assertEqual(edge_cases_for(PRD, "REQ-OWN-002")[0], "Owner records")
        self.assertEqual(edge_cases_for(PRD, "REQ-VIS-001"), ("Visits", []))
        self.assertEqual(edge_cases_for(PRD, "REQ-PET-001"), (None, []))

    def test_a_prose_mention_of_edge_cases_opens_no_list(self):
        prd = "### G\n`[REQ-G-001]`\nEdge cases are handled by the service.\n\n**Steps:**\n1. one\n"
        self.assertEqual(edge_cases_for(prd, "REQ-G-001"), ("G", []))

    def test_map_pairs_names_with_the_files_defining_them_and_lists_edge_cases(self):
        self._test_file("owner_test.txt", "theListingShouldShowPageOne()\n")
        cm = coverage_map(
            "REQ-OWN-001",
            self.root,
            ["**/*_test.txt"],
            ["theListingShouldShowPageOne", "theListingShouldRefuseAMissingOwner"],
        )
        self.assertEqual(
            cm.declared,
            (
                ("theListingShouldShowPageOne", ("src/test/owner_test.txt",)),
                ("theListingShouldRefuseAMissingOwner", ()),
            ),
        )
        self.assertEqual([n for n, _ in cm.edge_cases], [1, 2])
        self.assertEqual(len(cm.done_when), 1)
        text = render(cm)
        self.assertIn("Done-when bullets (1)", text)
        self.assertIn("Declared tests: 1 of 2 present", text)
        self.assertIn(
            "Edge cases of Owner records (2) — each needs a test or a walk note", text
        )
        self.assertIn("✗ theListingShouldRefuseAMissingOwner", text)

    def test_skip_dirs_apply_to_the_relative_path_only(self):
        # A checkout under a directory named `build` still maps its tests.
        root = self.root / "build" / "proj"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "prd.md").write_text(PRD, encoding="utf-8")
        (root / "t").mkdir()
        (root / "t" / "a_test.txt").write_text("aTest()\n", encoding="utf-8")
        (root / "target").mkdir()
        (root / "target" / "b_test.txt").write_text("aTest()\n", encoding="utf-8")
        cm = coverage_map("REQ-OWN-001", root, ["**/*_test.txt"], ["aTest"])
        self.assertEqual(cm.declared, (("aTest", ("t/a_test.txt",)),))

    def test_missing_inputs_map_with_notes_never_an_error(self):
        (self.root / "docs" / "prd.md").unlink()
        cm = coverage_map("REQ-OWN-001", self.root, ["**/*_test.txt"], None)
        self.assertEqual((cm.done_when, cm.edge_cases, cm.declared), ((), (), None))
        self.assertEqual(len(cm.notes), 3)
        self.assertIn("Declared tests: none on record", render(cm))

    def test_an_unreadable_test_file_lands_in_the_notes(self):
        if os.geteuid() == 0:
            self.skipTest("root reads everything")
        self._test_file("locked_test.txt", "aTest()\n")
        locked = self.root / "src" / "test" / "locked_test.txt"
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o644)
        cm = coverage_map("REQ-OWN-001", self.root, ["**/*_test.txt"], ["aTest"])
        self.assertTrue(any("unreadable" in n for n in cm.notes))
        self.assertEqual(cm.declared, (("aTest", ()),))

    def test_render_strips_control_characters(self):
        cm = coverage_map(
            "REQ-OWN-001", self.root, ["**/*_test.txt"], ["a\x1b[31mTest"]
        )
        self.assertNotIn("\x1b", render(cm))


if __name__ == "__main__":
    unittest.main(verbosity=2)
