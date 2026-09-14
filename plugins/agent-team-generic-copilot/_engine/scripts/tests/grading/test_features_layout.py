"""Classification against synthetic layouts (generic).

The generic stack's shipped layout.toml is a placeholder the project replaces,
so the classification table freezes the kind / module / sensitive contract the
change-grading skill documents against a synthetic layout, and stays green
after the project fills in its real layout. The module strategies pin against
one-rule layouts. The stack-agnostic review-kind and numstat pins live in core
(tests/grading/test_features.py).

Run (from the scripts dir): python3 -m unittest tests.grading.test_features_layout
Stdlib only.
"""

import unittest
from dataclasses import replace

from grading import config, features

# (path, kind, module, sensitive): test wins over a production root, a path
# under neither is unknown, and sensitivity is an independent overlay.
CASES = [
    ("src/billing/invoice.py", "prod", "src/billing", False),
    ("src/billing/invoice_test.py", "test", "src/billing", False),
    ("src/auth/session.py", "prod", "src/auth", True),
    ("src/auth/session_test.py", "test", "src/auth", True),
    ("docs/prd.md", "unknown", None, False),
    ("main_test.py", "test", None, False),
]


def a_layout():
    """Return a layout that classifies nothing."""
    return config.Layout(
        test_globs=(),
        prod_roots=(),
        sensitive=(),
        module_rules=(),
        extra_reviewers=(),
        review={},
        conventions={},
    )


def _one_rule_layout(match, strategy):
    """Return a layout carrying one module rule; nothing else classifies."""
    return replace(a_layout(), module_rules=(config.ModuleRule(match, strategy),))


class Classification(unittest.TestCase):
    def setUp(self):
        self.layout = replace(
            a_layout(),
            test_globs=("**/*_test.*", "*_test.*"),
            prod_roots=("src/",),
            sensitive=("**/auth/**",),
            module_rules=(config.ModuleRule("src/**", "dir"),),
        )

    def test_every_path_classifies_as_the_contract_documents(self):
        for path, kind, module, sensitive in CASES:
            with self.subTest(path=path, field="kind"):
                self.assertEqual(features.classify_kind(path, self.layout), kind)
            with self.subTest(path=path, field="module"):
                self.assertEqual(features.module_of(path, self.layout), module)
            with self.subTest(path=path, field="sensitive"):
                self.assertEqual(features.is_sensitive(path, self.layout), sensitive)


class ModuleStrategies(unittest.TestCase):
    def test_the_regex_strategy_derives_its_first_group(self):
        layout = _one_rule_layout("**/src/**", "regex:(.*?/src/[^/]+)/")

        self.assertEqual(
            features.module_of("app/src/core/mod.py", layout), "app/src/core"
        )

    def test_a_non_matching_regex_falls_back_to_the_parent_directory(self):
        layout = _one_rule_layout("src/**", "regex:(.*?/src/[^/]+)/")

        self.assertEqual(features.module_of("src/core/mod.py", layout), "src/core")

    def test_the_dir_strategy_derives_the_parent_directory(self):
        layout = _one_rule_layout("src/**", "dir")

        self.assertEqual(
            features.module_of("src/report/summary.py", layout), "src/report"
        )

    def test_first_segment_after_keeps_the_prefix_in_the_module_id(self):
        layout = _one_rule_layout("packages/**", "first-segment-after:packages/")

        self.assertEqual(
            features.module_of("packages/ui/src/index.ts", layout), "packages/ui"
        )

    def test_an_unmatched_path_has_no_module(self):
        layout = _one_rule_layout("packages/**", "dir")

        self.assertIsNone(features.module_of("docs/readme.md", layout))


if __name__ == "__main__":
    unittest.main(verbosity=2)
