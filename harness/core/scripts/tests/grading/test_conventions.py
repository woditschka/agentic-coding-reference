"""Tests for grading.conventions — the change set's conventions map.

Pure functions over a unified diff and an explicit [conventions] config, so
the suite is stack-agnostic and runs everywhere.

Run (from the scripts dir): python3 -m unittest tests.grading.test_conventions
Stdlib only.
"""

import unittest

from grading import config, conventions
from grading.conventions import (
    added_lines,
    comment_blocks,
    conventions_map,
    render,
)

JAVA = {
    "comment_markers": ["//", "/*", "*", "*/"],
    "construction": r"new\s+[A-Z][A-Za-z0-9_]*\s*[<(]",
    "construction_ignore": [r"new\s+(?:PageImpl|BigDecimal|ArrayList)\b"],
    "constant_declaration": r"\bstatic\s+final\b|\b[A-Z][A-Z0-9_]{2,}\s*=",
}

DIFF = """\
diff --git a/src/main/app.txt b/src/main/app.txt
--- a/src/main/app.txt
+++ b/src/main/app.txt
@@ -1,0 +1,4 @@
+/*
+ * Copyright 2026 the original authors. Licensed under the Apache License.
+ */
+int pageToShow = Math.max(page, FIRST_PAGE);
@@ -10,2 +14,3 @@
 context line
-removed line
+// a page below the first is not a failure: the first page is listed instead
+// and the listing presents itself as that page
+return pageToShow;
diff --git a/src/test/app_test.txt b/src/test/app_test.txt
--- a/src/test/app_test.txt
+++ b/src/test/app_test.txt
@@ -5,0 +6,6 @@
+private static final int FIRST_PAGE = 1;
+@Test
+Page<Owner> page = new PageImpl<>(List.of(george(), new Owner()));
+mvc.perform(get("/owners").param("page", "0"));
+Owner irrelevant = anOwner();
+assertThat(model.currentPage()).isEqualTo(FIRST_PAGE);
diff --git a/docs/prd.md b/docs/prd.md
--- a/docs/prd.md
+++ b/docs/prd.md
@@ -1,0 +1,1 @@
+# a heading, not a comment
"""


def kind_of(path: str) -> str:
    if path.startswith("src/test/"):
        return "test"
    if path.startswith("src/main/"):
        return "prod"
    return "unknown"


class TestAddedLines(unittest.TestCase):
    def test_a_deleted_file_is_absent_from_added_and_present_in_changed(self):
        diff = (
            "diff --git a/src/a.txt b/src/a.txt\n--- a/src/a.txt\n+++ /dev/null\n"
            "@@ -1,1 +0,0 @@\n-guard\n"
        )
        self.assertEqual(conventions.added_lines(diff), {})
        self.assertEqual(conventions.changed_lines(diff), {"src/a.txt": ["guard"]})

    def test_new_file_numbers_follow_the_hunk_header(self):
        got = added_lines(DIFF)
        self.assertEqual(got["src/main/app.txt"][0], (1, "/*"))
        self.assertEqual(got["src/main/app.txt"][3][0], 4)

    def test_context_advances_and_removal_does_not(self):
        got = added_lines(DIFF)
        numbers = [no for no, _ in got["src/main/app.txt"]]
        self.assertEqual(numbers[4:], [15, 16, 17])

    def test_content_that_mimics_a_header_stays_content(self):
        diff = (
            "diff --git a/src/main/a.txt b/src/main/a.txt\n"
            "--- a/src/main/a.txt\n+++ b/src/main/a.txt\n@@ -1,0 +1,3 @@\n"
            "+/*\n+++ b/docs/x.md\n+exec(cmd)\n"
        )
        got = added_lines(diff)
        self.assertEqual(list(got), ["src/main/a.txt"])
        self.assertEqual(
            [t for _, t in got["src/main/a.txt"]], ["/*", "++ b/docs/x.md", "exec(cmd)"]
        )

    def test_deleted_file_contributes_nothing(self):
        diff = "--- a/gone.txt\n+++ /dev/null\n@@ -1,2 +0,0 @@\n-x\n-y\n"
        self.assertEqual(added_lines(diff), {})


class TestCommentBlocks(unittest.TestCase):
    def test_license_header_is_dropped_and_runs_collapse(self):
        lines = added_lines(DIFF)["src/main/app.txt"]
        blocks = comment_blocks(lines, ("//", "/*", "*", "*/"))
        self.assertEqual(len(blocks), 1)
        self.assertEqual((blocks[0].start, blocks[0].end), (15, 16))
        self.assertTrue(blocks[0].text.startswith("// a page below"))


class TestConventionsMap(unittest.TestCase):
    def setUp(self):
        self.cm = conventions_map(DIFF, kind_of, JAVA)
        self.by_path = {f.path: f for f in self.cm.files}

    def test_non_code_paths_are_not_listed(self):
        self.assertNotIn("docs/prd.md", self.by_path)

    def test_prod_file_lists_comments_only(self):
        rows = self.by_path["src/main/app.txt"]
        self.assertEqual(len(rows.comments), 1)
        self.assertEqual(rows.constructions, ())
        self.assertEqual(rows.literals, ())

    def test_test_file_lists_the_domain_construction_not_the_framework_one(self):
        rows = self.by_path["src/test/app_test.txt"]
        self.assertEqual([no for no, _ in rows.constructions], [8])
        self.assertIn("new Owner()", rows.constructions[0][1])

    def test_literal_lines_skip_constants_annotations_and_named_values(self):
        rows = self.by_path["src/test/app_test.txt"]
        self.assertEqual([no for no, _ in rows.literals], [9])

    def test_no_construction_pattern_lists_none_and_says_so(self):
        cm = conventions_map(DIFF, kind_of, {"comment_markers": ["//"]})
        rows = {f.path: f for f in cm.files}["src/test/app_test.txt"]
        self.assertEqual(rows.constructions, ())
        self.assertTrue(any("construction" in n for n in cm.notes))

    def test_render_is_printable_and_names_the_base(self):
        text = render(self.cm, "abc1234")
        self.assertIn("conventions-map: 2 code file(s) with rows", text)
        self.assertIn("(base abc1234)", text)
        self.assertIn("15-16: // a page below", text)
        self.assertIn("9: mvc.perform", text)


class TestConventionsConfigValidation(unittest.TestCase):
    def test_defaults_when_absent(self):
        cfg = config.validate_conventions({})
        self.assertIsNone(cfg["construction"])
        self.assertIn("//", cfg["comment_markers"])
        self.assertTrue(cfg["constant_declaration"])

    def test_bad_regex_raises(self):
        with self.assertRaises(ValueError):
            config.validate_conventions({"construction": "new ("})

    def test_bad_markers_raise(self):
        with self.assertRaises(ValueError):
            config.validate_conventions({"comment_markers": []})

    def test_bad_ignore_list_raises(self):
        with self.assertRaises(ValueError):
            config.validate_conventions({"construction_ignore": "new X"})


if __name__ == "__main__":
    unittest.main()
