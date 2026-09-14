"""The feature model's classification and numstat folding over a synthetic layout."""

import os
import shutil
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from changeset import config as changeset_config
from grading.config import NAMED_MODULE_LAYOUTS, Layout, ModuleRule, validate_review
from grading.features import (
    DiffRange,
    diff_features,
    module_of,
    parse_numstat,
    review_kind,
    security_surface_paths,
)

A_PROBE = r"@\w+Mapping\("
A_SOURCE_FILE = "app/src/main/code/pkg/file.ext"
ITS_TEST = "app/src/test/code/pkg/file_test.ext"
A_SIBLING_MODULE_FILE = "lib/src/main/code/pkg/file.ext"
A_ROOT_TREE_FILE = "src/main/code/pkg/file.ext"
A_ROOT_TREE_TEST = "src/test/code/pkg/sub/file.ext"
A_FILE_OUTSIDE_THE_TREE = "app/notes.ext"


def a_layout():
    return Layout(
        test_globs=("**/*_test.txt", "*_test.txt"),
        prod_roots=("src/",),
        sensitive=("**/auth/**",),
        module_rules=(),
        extra_reviewers=(),
        review={},
        conventions={},
    )


def a_review_config():
    return validate_review({"docs": ["*.md"], "config": ["*.toml"]}, ())


def module_under(strategy, path):
    """Derive the path's module through one rule that matches everything."""
    layout = replace(a_layout(), module_rules=(ModuleRule("*", strategy),))
    return module_of(path, layout)


class ReviewKind(unittest.TestCase):
    def test_precedence_is_docs_test_config_prod_unknown(self):
        cases = [
            ("docs/x.md", "docs"),
            ("a_test.txt", "test"),
            ("c.toml", "config"),
            ("src/m.txt", "prod"),
            ("notes.dat", "unknown"),
            ("src/notes.md", "docs"),
        ]
        for path, kind in cases:
            with self.subTest(path=path):
                self.assertEqual(review_kind(path, a_layout(), a_review_config()), kind)


class NamedModuleLayouts(unittest.TestCase):
    def test_maven_and_gradle_derive_the_module_root(self):
        self.assertEqual(module_under("maven", A_SOURCE_FILE), "app/src")
        self.assertEqual(module_under("gradle", A_SOURCE_FILE), "app/src")

    def test_a_prod_file_and_its_test_derive_one_module(self):
        self.assertEqual(
            module_under("gradle", A_SOURCE_FILE), module_under("gradle", ITS_TEST)
        )
        self.assertNotEqual(
            module_under("gradle", A_SOURCE_FILE),
            module_under("gradle", A_SIBLING_MODULE_FILE),
        )

    def test_a_repo_root_tree_derives_the_module_root_without_a_prefix(self):
        self.assertEqual(module_under("gradle", A_ROOT_TREE_FILE), "src")
        self.assertEqual(module_under("gradle", A_ROOT_TREE_TEST), "src")

    def test_a_named_layout_falls_back_to_the_parent_directory(self):
        self.assertEqual(module_under("maven", A_FILE_OUTSIDE_THE_TREE), "app")

    def test_an_unparticipating_group_falls_back_to_the_parent_directory(self):
        self.assertEqual(module_under("regex:a/foo(bar)?", "a/foox"), "a")

    def test_an_empty_capture_falls_back_to_the_parent_directory(self):
        self.assertEqual(module_under("regex:(x*)", "a/bc.ext"), "a")

    def test_every_name_equals_its_expanded_regex(self):
        paths = (A_SOURCE_FILE, "lib/src/test/code/pkg/file_test.ext", "settings.ext")
        for name, pattern in NAMED_MODULE_LAYOUTS.items():
            for path in paths:
                with self.subTest(name=name, path=path):
                    self.assertEqual(
                        module_under(name, path), module_under(f"regex:{pattern}", path)
                    )


class ParseNumstat(unittest.TestCase):
    def fold(self, numstat):
        return parse_numstat(numstat, a_layout(), a_review_config())

    def test_only_prod_and_test_lines_count_toward_the_size(self):
        out = self.fold(
            "3\t1\tsrc/m.txt\n2\t2\ta_test.txt\n40\t0\tdocs/x.md\n"
            "5\t0\tc.toml\n6\t0\tsrc/app.toml\n"
        )

        self.assertEqual(out["lines"], 14)
        self.assertEqual(
            out["paths"],
            ["src/m.txt", "a_test.txt", "docs/x.md", "c.toml", "src/app.toml"],
        )
        self.assertEqual(out["kinds"][-1], "config")
        self.assertFalse(out["binary"])

    def test_a_binary_row_flags_and_does_not_count(self):
        out = self.fold("-\t-\tsrc/blob.bin\n1\t0\tsrc/m.txt\n")

        self.assertTrue(out["binary"])
        self.assertEqual(out["lines"], 1)

    def test_an_undocumented_shape_keeps_the_path_and_counts_nothing(self):
        out = self.fold("weird\t?\tsrc/m.txt\n2\t0\tsrc/n.txt\n")

        self.assertEqual(out["lines"], 2)
        self.assertEqual(out["paths"], ["src/m.txt", "src/n.txt"])

    def test_a_sensitive_path_flags_the_delta(self):
        self.assertTrue(self.fold("1\t0\tsrc/auth/k.txt\n")["sensitive"])


class DiffFeatures(unittest.TestCase):
    """The row over a real repository: one prod file, its test, a binary, and a doc."""

    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.repo)
        cwd = Path.cwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, cwd)
        saved = changeset_config.layout
        changeset_config.layout = SimpleNamespace(EXCLUDE=[])
        self.addCleanup(setattr, changeset_config, "layout", saved)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "a.txt").write_text("one\ntwo\n")
        (self.repo / "a_test.txt").write_text("check\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")

    def git(self, *args):
        done = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return done.stdout.strip()

    def test_the_row_derives_its_totals_from_the_classified_files(self):
        (self.repo / "src" / "a.txt").write_text("one\ntwo\nthree\n")
        (self.repo / "a_test.txt").write_text("check\nagain\n")
        (self.repo / "src" / "blob.bin").write_bytes(b"\x00\x01")
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "x.md").write_text("# x\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "change")
        head = self.git("rev-parse", "HEAD")

        row = diff_features(
            a_layout(), a_review_config(), DiffRange(self.base, head, head)
        )

        self.assertEqual(
            [f["path"] for f in row["files"]],
            ["a_test.txt", "docs/x.md", "src/a.txt", "src/blob.bin"],
        )
        self.assertEqual((row["prod_lines"], row["test_lines"]), (1, 1))
        self.assertEqual(row["test_prod_ratio"], 1.0)
        self.assertEqual((row["binary_files"], row["hunks"]), (1, 3))
        self.assertEqual(row["unknown_paths"], ["docs/x.md"])
        self.assertEqual((row["modules"], row["module_count"]), ([], 0))
        self.assertEqual(row["churn"], {"commits": 1, "authors": 1})

    def test_no_churn_tip_leaves_churn_null(self):
        row = diff_features(
            a_layout(), a_review_config(), DiffRange(self.base, self.base, None)
        )

        self.assertIsNone(row["churn"])
        self.assertEqual(row["files_changed"], 0)

    def test_an_unresolved_base_yields_the_null_row(self):
        row = diff_features(
            a_layout(), a_review_config(), DiffRange(None, "head", None)
        )

        self.assertEqual(set(row.values()), {None})
        self.assertIn("security_surface_paths", row)


class SecuritySurfaceProbe(unittest.TestCase):
    DIFF = (
        "--- a/src/app/handler.txt\n+++ b/src/app/handler.txt\n@@ -1,0 +1,2 @@\n"
        '+@GetMapping("/owners")\n+int x = 1;\n'
        "--- a/src/app/handler_test.txt\n+++ b/src/app/handler_test.txt\n@@ -1,0 +1,1 @@\n"
        '+@GetMapping("/nope")\n'
        "--- a/src/app/quiet.txt\n+++ b/src/app/quiet.txt\n@@ -1,0 +1,1 @@\n+int y = 2;\n"
    )

    @staticmethod
    def kind_of(path):
        return "test" if path.endswith("_test.txt") else "prod"

    def test_hits_only_production_files(self):
        hits = security_surface_paths(self.DIFF, [A_PROBE], self.kind_of)

        self.assertEqual(hits, ["src/app/handler.txt"])

    def test_header_mimicking_content_cannot_reroute_the_probe(self):
        diff = (
            "diff --git a/src/app/h.txt b/src/app/h.txt\n"
            "--- a/src/app/h.txt\n+++ b/src/app/h.txt\n@@ -1,0 +1,2 @@\n"
            '+++ b/README.md\n+@GetMapping("/x")\n'
        )

        hits = security_surface_paths(diff, [A_PROBE], self.kind_of)

        self.assertEqual(hits, ["src/app/h.txt"])

    def test_a_removed_match_hits_like_an_added_one(self):
        diff = (
            "diff --git a/src/a.txt b/src/a.txt\n--- a/src/a.txt\n+++ b/src/a.txt\n"
            "@@ -1,2 +1,1 @@\n-@PreAuthorize(x)\n context\n"
        )

        hits = security_surface_paths(diff, [r"@PreAuthorize"], self.kind_of)

        self.assertEqual(hits, ["src/a.txt"])

    def test_a_deleted_production_file_still_hits(self):
        diff = (
            "diff --git a/src/a.txt b/src/a.txt\n--- a/src/a.txt\n+++ /dev/null\n"
            "@@ -1,2 +0,0 @@\n-@PreAuthorize(x)\n-body\n"
        )

        hits = security_surface_paths(diff, [r"@PreAuthorize"], self.kind_of)

        self.assertEqual(hits, ["src/a.txt"])

    def test_an_empty_probe_hits_nothing(self):
        self.assertEqual(security_surface_paths(self.DIFF, [], self.kind_of), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
