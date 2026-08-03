"""Tests for grading.features — the structural feature model (stack-agnostic slice).

TestReviewKind, TestNamedModuleLayouts, and TestParseNumstat inject a synthetic
layout and pass an explicit review config, so they pin the engine identically
in every stack. They
live here in core, single-sourced, and materialize out. The layout-dependent
classes that read a stack's own scripts/layout.toml (TestClassification,
TestModuleStrategies) stay per-stack in tests/grading/test_features_layout.py.

Run (from the scripts dir): python3 -m unittest tests.grading.test_features
Stdlib only.
"""

import unittest
from types import SimpleNamespace

from grading import config, features


class TestReviewKind(unittest.TestCase):
    """Review-surface classification (docs > test > config > prod > unknown).
    Stack-agnostic: injects a synthetic layout and passes an explicit review
    config, so one core-homed block pins the engine identically for every
    stack."""

    def setUp(self):
        self._saved = config.layout
        config.layout = SimpleNamespace(
            TEST=["**/*_test.txt", "*_test.txt"],
            PROD_ROOTS=["src/"],
            SENSITIVE=["**/auth/**"],
            MODULE=[],
            REVIEW={},
            EXTRA_REVIEWERS=[],
        )
        self.addCleanup(lambda: setattr(config, "layout", self._saved))
        self.cfg = {
            "docs": ["*.md"],
            "config": ["*.toml"],
            "size_threshold": 80,
            "mode": "risk",
            "surface_reviewers": {
                k: list(v) for k, v in config.SURFACE_REVIEWERS.items()
            },
        }

    def test_review_kind_precedence(self):
        cases = [
            ("docs/x.md", "docs"),
            ("a_test.txt", "test"),
            ("c.toml", "config"),
            ("src/m.txt", "prod"),
            ("notes.dat", "unknown"),
            ("src/notes.md", "docs"),  # docs beats a production root
        ]
        for path, kind in cases:
            with self.subTest(path=path):
                self.assertEqual(features.review_kind(path, self.cfg), kind)


class TestNamedModuleLayouts(unittest.TestCase):
    """A named layout is pure sugar for the regex primitive: same match, same
    parent-directory fallback. Stack-agnostic — the table is core data, so the
    equivalence pins once, here."""

    def _module_of(self, strategy, path):
        saved = config.layout
        config.layout = SimpleNamespace(
            TEST=[],
            PROD_ROOTS=[],
            SENSITIVE=[],
            MODULE=[{"match": "*", "from": strategy}],
            REVIEW={},
            EXTRA_REVIEWERS=[],
        )
        try:
            return features.module_of(path)
        finally:
            config.layout = saved

    def test_maven_and_gradle_derive_the_source_set_root(self):
        # The source-set convention is language-blind: src/<set>/<lang> with
        # any <lang> segment, so the pins stay stack-neutral here in core.
        for name in ("maven", "gradle"):
            with self.subTest(name=name):
                self.assertEqual(
                    self._module_of(name, "app/src/main/code/pkg/file.ext"),
                    "app/src/main/code",
                )

    def test_a_repo_root_tree_derives_the_source_set_root_without_a_prefix(self):
        # A single-module tree has no segment before src/; the same rule
        # derives the source-set root instead of falling back to per-package
        # parent directories (which inflated module counts).
        self.assertEqual(
            self._module_of("gradle", "src/main/code/pkg/file.ext"),
            "src/main/code",
        )
        self.assertEqual(
            self._module_of("gradle", "src/test/code/pkg/sub/file.ext"),
            "src/test/code",
        )

    def test_named_layout_falls_back_to_parent_directory(self):
        self.assertEqual(self._module_of("maven", "app/notes.ext"), "app")

    def test_regex_unparticipating_group_falls_back_to_parent_directory(self):
        # The pattern matches but its optional group 1 does not participate:
        # the path falls back to its parent directory — a module id is never
        # None on a matching path.
        self.assertEqual(self._module_of("regex:a/foo(bar)?", "a/foox"), "a")

    def test_regex_empty_capture_falls_back_to_parent_directory(self):
        # Group 1 captures "": treated as a non-match, so the module set never
        # carries an empty id.
        self.assertEqual(self._module_of("regex:(x*)", "a/bc.ext"), "a")

    def test_every_name_equals_its_expanded_regex(self):
        # The sugar contract: `from = "<name>"` and `from = "regex:<pattern>"`
        # must derive identically on match, fallback, and test trees.
        paths = (
            "app/src/main/code/pkg/file.ext",
            "lib/src/test/code/pkg/file_test.ext",
            "settings.ext",
        )
        for name, pattern in config.NAMED_MODULE_LAYOUTS.items():
            for path in paths:
                with self.subTest(name=name, path=path):
                    self.assertEqual(
                        self._module_of(name, path),
                        self._module_of(f"regex:{pattern}", path),
                    )


class TestParseNumstat(unittest.TestCase):
    """Numstat folding (parse_numstat — pure, no git fixture). Stack-agnostic:
    the same synthetic layout and review config as TestReviewKind, so one
    core-homed block pins the engine identically for every stack."""

    def setUp(self):
        self._saved = config.layout
        config.layout = SimpleNamespace(
            TEST=["**/*_test.txt", "*_test.txt"],
            PROD_ROOTS=["src/"],
            SENSITIVE=["**/auth/**"],
            MODULE=[],
            REVIEW={},
            EXTRA_REVIEWERS=[],
        )
        self.addCleanup(lambda: setattr(config, "layout", self._saved))
        self.cfg = {
            "docs": ["*.md"],
            "config": ["*.toml"],
            "size_threshold": 80,
            "mode": "risk",
            "surface_reviewers": {
                k: list(v) for k, v in config.SURFACE_REVIEWERS.items()
            },
        }

    def test_parse_numstat_counts_prod_and_test_lines_only(self):
        # Size uses the first-pass metric (classify_kind): src/app.toml is
        # "config" for roster matching but sits under a prod root, so its
        # lines count — the first pass would count them toward oversize too.
        out = features.parse_numstat(
            "3\t1\tsrc/m.txt\n2\t2\ta_test.txt\n40\t0\tdocs/x.md\n"
            "5\t0\tc.toml\n6\t0\tsrc/app.toml\n",
            self.cfg,
        )
        self.assertEqual(out["lines"], 14)
        self.assertEqual(
            out["paths"],
            ["src/m.txt", "a_test.txt", "docs/x.md", "c.toml", "src/app.toml"],
        )
        self.assertEqual(out["kinds"][-1], "config")
        self.assertFalse(out["binary"])

    def test_parse_numstat_binary_rows_flag_not_count(self):
        out = features.parse_numstat("-\t-\tsrc/blob.bin\n1\t0\tsrc/m.txt\n", self.cfg)
        self.assertTrue(out["binary"])
        self.assertEqual(out["lines"], 1)

    def test_parse_numstat_undocumented_shape_counts_nothing(self):
        # Non-numeric, non-dash columns: keep the path (containment still
        # judges it) but count no lines — never crash.
        out = features.parse_numstat("weird\t?\tsrc/m.txt\n2\t0\tsrc/n.txt\n", self.cfg)
        self.assertEqual(out["lines"], 2)
        self.assertEqual(out["paths"], ["src/m.txt", "src/n.txt"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
