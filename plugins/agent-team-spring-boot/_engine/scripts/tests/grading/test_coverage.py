"""The slice's test-coverage map over the shipped PRD form."""

import os
import tempfile
import unittest
from pathlib import Path

from grading.coverage import coverage_map, done_when_bullets, edge_cases_for, render

SOME_REQ_ID = "REQ-OWN-001"
ANOTHER_REQ_ID = "REQ-OWN-002"
A_REQ_ID_WITHOUT_EDGE_CASES = "REQ-VIS-001"
AN_UNLISTED_REQ_ID = "REQ-PET-001"
OWNER_GROUP = "Owner records"
OWNER_EDGE_CASE_NUMBERS = [1, 2]
A_PRESENT_TEST = "theListingShouldShowPageOne"
A_MISSING_TEST = "theListingShouldRefuseAMissingOwner"
TEST_GLOBS = ["**/*_test.txt"]

# The shipped PRD form: backticked ids in the Done-when list, a bold
# "Edge cases:" label, capability groups under ### headings.
PRD = f"""## Requirements

Owners `[{SOME_REQ_ID}]` are the first capability; edge cases are listed per group.

### {OWNER_GROUP}

<a id="{SOME_REQ_ID.lower()}"></a>
Owners are listed `[{SOME_REQ_ID}]` and edited `[{ANOTHER_REQ_ID}]`.

**Done when:**
- `[{SOME_REQ_ID}]` given a page below the first, when the listing renders, then it shows page one.
- `[{ANOTHER_REQ_ID}]` given an edit, when saved, then the record updates.

**Edge cases:**
1. A search whose text is entirely spaces behaves as an empty search.
2. A request for an owner that does not exist is refused.

**Notes:**
1. This numbered list is not an edge case.

### Visits

Visits are booked `[{A_REQ_ID_WITHOUT_EDGE_CASES}]`.

## Open Questions

1. Not an edge case either.
"""


class CoverageMap(unittest.TestCase):
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
            done_when_bullets(PRD, SOME_REQ_ID),
            [
                "given a page below the first, when the listing renders, then it shows page one."
            ],
        )
        self.assertEqual(
            done_when_bullets("- **[REQ-X-001]** bold form", "REQ-X-001"), ["bold form"]
        )
        self.assertEqual(done_when_bullets(PRD, A_REQ_ID_WITHOUT_EDGE_CASES), [])

    def test_edge_cases_come_from_the_anchored_group_and_stop_at_the_next_label(self):
        # The preamble mentions the id too; the anchored ### section wins.
        group, cases = edge_cases_for(PRD, SOME_REQ_ID)
        self.assertEqual(group, OWNER_GROUP)
        self.assertEqual([n for n, _ in cases], OWNER_EDGE_CASE_NUMBERS)
        self.assertEqual(edge_cases_for(PRD, ANOTHER_REQ_ID)[0], OWNER_GROUP)
        self.assertEqual(
            edge_cases_for(PRD, A_REQ_ID_WITHOUT_EDGE_CASES), ("Visits", [])
        )
        self.assertEqual(edge_cases_for(PRD, AN_UNLISTED_REQ_ID), (None, []))

    def test_a_prose_mention_of_edge_cases_opens_no_list(self):
        prd = "### G\n`[REQ-G-001]`\nEdge cases are handled by the service.\n\n**Steps:**\n1. one\n"
        self.assertEqual(edge_cases_for(prd, "REQ-G-001"), ("G", []))

    def test_map_pairs_names_with_the_files_defining_them_and_lists_edge_cases(self):
        self._test_file("owner_test.txt", f"{A_PRESENT_TEST}()\n")
        declared = [A_PRESENT_TEST, A_MISSING_TEST]
        cm = coverage_map(SOME_REQ_ID, self.root, TEST_GLOBS, declared)
        self.assertEqual(
            cm.declared,
            ((A_PRESENT_TEST, ("src/test/owner_test.txt",)), (A_MISSING_TEST, ())),
        )
        self.assertEqual([n for n, _ in cm.edge_cases], OWNER_EDGE_CASE_NUMBERS)
        self.assertEqual(len(cm.done_when), 1)
        text = render(cm)
        self.assertIn(f"Done-when bullets ({len(cm.done_when)})", text)
        self.assertIn(f"Declared tests: 1 of {len(declared)} present", text)
        self.assertIn(
            f"Edge cases of {OWNER_GROUP} ({len(OWNER_EDGE_CASE_NUMBERS)})"
            " — each needs a test or a walk note",
            text,
        )
        self.assertIn(f"✗ {A_MISSING_TEST}", text)

    def test_skip_dirs_apply_to_the_relative_path_only(self):
        # A checkout under a directory named `build` still maps its tests.
        root = self.root / "build" / "proj"
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "prd.md").write_text(PRD, encoding="utf-8")
        (root / "t").mkdir()
        (root / "t" / "a_test.txt").write_text("aTest()\n", encoding="utf-8")
        (root / "target").mkdir()
        (root / "target" / "b_test.txt").write_text("aTest()\n", encoding="utf-8")
        cm = coverage_map(SOME_REQ_ID, root, TEST_GLOBS, ["aTest"])
        self.assertEqual(cm.declared, (("aTest", ("t/a_test.txt",)),))

    def test_missing_inputs_map_with_notes_never_an_error(self):
        (self.root / "docs" / "prd.md").unlink()
        missing_inputs = ("is absent", "no prd-entry", "no test files")
        cm = coverage_map(SOME_REQ_ID, self.root, TEST_GLOBS, None)
        self.assertEqual((cm.done_when, cm.edge_cases, cm.declared), ((), (), None))
        self.assertEqual(len(cm.notes), len(missing_inputs))
        for missing in missing_inputs:
            with self.subTest(missing):
                self.assertTrue(any(missing in note for note in cm.notes))
        self.assertIn("Declared tests: none on record", render(cm))

    def test_an_unreadable_test_file_lands_in_the_notes(self):
        if os.geteuid() == 0:
            self.skipTest("root reads everything")
        self._test_file("locked_test.txt", "aTest()\n")
        locked = self.root / "src" / "test" / "locked_test.txt"
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o644)
        cm = coverage_map(SOME_REQ_ID, self.root, TEST_GLOBS, ["aTest"])
        self.assertTrue(any("unreadable" in n for n in cm.notes))
        self.assertEqual(cm.declared, (("aTest", ()),))

    def test_render_strips_control_characters(self):
        cm = coverage_map(SOME_REQ_ID, self.root, TEST_GLOBS, ["a\x1b[31mTest"])
        self.assertNotIn("\x1b", render(cm))


if __name__ == "__main__":
    unittest.main(verbosity=2)
