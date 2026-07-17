"""Tests for grading.features against this stack's synthetic layouts (generic).

TestClassificationContract freezes the classification contract (kind / module /
sensitive) the change-grading skill documents against a synthetic layout, since
the generic stack's shipped layout.toml is a placeholder the project replaces;
the suite pins the engine's semantics, never any particular project's globs, and
stays green after the project fills in its real layout. TestModuleStrategies
injects synthetic layouts and runs everywhere, but the strategies this stack
exercises are its own, so it stays here. The stack-agnostic review-kind and
numstat pins live in core (tests/grading/test_features.py).

Run (from the scripts dir): python3 -m unittest tests.grading.test_features_layout
Stdlib only.
"""

import unittest
from types import SimpleNamespace

from grading import config, features


def _inject_layout(case, **overrides):
    """Swap the loaded layout for a synthetic namespace for this test case.

    Call at most once per test method: the original is captured at call time,
    so a second call would snapshot the already-patched layout and the cleanups
    would not restore the original.
    """
    saved = config.layout
    fields = dict(TEST=[], PROD_ROOTS=[], SENSITIVE=[], MODULE=[])
    fields.update(overrides)
    config.layout = SimpleNamespace(**fields)
    case.addCleanup(lambda: setattr(config, "layout", saved))


class TestClassificationContract(unittest.TestCase):
    """The contract the change-grading skill documents, against a synthetic
    layout: test wins over prod_roots, no-match yields unknown (never prod),
    sensitive is an independent overlay flag."""

    def setUp(self):
        _inject_layout(
            self,
            TEST=["**/*_test.*", "*_test.*"],
            PROD_ROOTS=["src/"],
            SENSITIVE=["**/auth/**"],
            MODULE=[{"match": "src/**", "from": "dir"}],
        )

    # (path, expected_kind, expected_module, expected_sensitive)
    CASES = [
        ("src/billing/invoice.py", "prod", "src/billing", False),
        ("src/billing/invoice_test.py", "test", "src/billing", False),  # test wins
        ("src/auth/session.py", "prod", "src/auth", True),  # sensitive overlay
        (
            "src/auth/session_test.py",
            "test",
            "src/auth",
            True,
        ),  # test wins, still sensitive
        ("docs/prd.md", "unknown", None, False),  # under no prod root, no test glob
        ("main_test.py", "test", None, False),  # top-level test, no module rule
    ]

    def test_kind_module_sensitive(self):
        for path, kind, module, sensitive in self.CASES:
            with self.subTest(path=path, field="kind"):
                self.assertEqual(features.classify_kind(path), kind)
            with self.subTest(path=path, field="module"):
                self.assertEqual(features.module_of(path), module)
            with self.subTest(path=path, field="sensitive"):
                self.assertEqual(features.is_sensitive(path), sensitive)


class TestModuleStrategies(unittest.TestCase):
    """The three path primitives against synthetic layouts: `dir`,
    `first-segment-after:<prefix>`, and `regex:<pattern>`. The named layouts
    that expand to `regex:` pin in core (TestNamedModuleLayouts)."""

    def test_regex_strategy(self):
        _inject_layout(
            self,
            MODULE=[{"match": "**/src/**", "from": "regex:(.*?/src/[^/]+)/"}],
        )
        # Group 1 of the pattern is the module id.
        self.assertEqual(features.module_of("app/src/core/mod.py"), "app/src/core")

    def test_regex_strategy_falls_back_to_parent(self):
        _inject_layout(
            self,
            MODULE=[{"match": "src/**", "from": "regex:(.*?/src/[^/]+)/"}],
        )
        # The pattern needs a segment before "src/"; a repo-root path has none,
        # so derivation falls back to the file's parent directory.
        self.assertEqual(features.module_of("src/core/mod.py"), "src/core")

    def test_dir_strategy(self):
        _inject_layout(self, MODULE=[{"match": "src/**", "from": "dir"}])
        self.assertEqual(features.module_of("src/report/summary.py"), "src/report")

    def test_first_segment_after_strategy(self):
        _inject_layout(
            self,
            MODULE=[{"match": "packages/**", "from": "first-segment-after:packages/"}],
        )
        # The module id keeps its path prefix (so cross-stack changes read as
        # wider scatter), so the result is "packages/ui", not bare "ui".
        self.assertEqual(features.module_of("packages/ui/src/index.ts"), "packages/ui")

    def test_unmatched_path_yields_none(self):
        _inject_layout(self, MODULE=[{"match": "packages/**", "from": "dir"}])
        self.assertIsNone(features.module_of("docs/readme.md"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
