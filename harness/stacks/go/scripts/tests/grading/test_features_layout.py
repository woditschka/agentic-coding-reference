"""Classification against this stack's real layout.toml (Go).

The classification table freezes the kind / module / sensitive contract this
project's own layout.toml encodes, so the layout's storage format can change
without altering the feature row; it skips on a pre-init tree. The module
strategies a Go project forks onto (a Gradle/Maven or TypeScript tree) pin
against one-rule layouts. The stack-agnostic review-kind and numstat pins live
in core (tests/grading/test_features.py).

Run (from the scripts dir): python3 -m unittest tests.grading.test_features_layout
Stdlib only.
"""

import unittest
from pathlib import Path

from grading import config, features

# The scripts dir (tests/grading/ lives two levels under it).
_LAYOUT = Path(__file__).resolve().parent.parent.parent / "layout.toml"
SRC_TREE_PATTERN = "regex:((?:.*?/)?src)/(?:main|test)/[^/]+/"

# (path, kind, module, sensitive). The sensitive rows each hit exactly one
# glob, so a silently deleted glob fails the table.
CASES = [
    ("internal/report/summary.go", "prod", "internal/report", False),
    ("internal/report/summary_test.go", "test", "internal/report", False),
    ("cmd/example/main.go", "prod", "cmd/example", False),
    ("pkg/foo/bar.go", "prod", "pkg/foo", False),
    ("internal/auth/session.go", "prod", "internal/auth", True),
    ("internal/auth/session_test.go", "test", "internal/auth", True),
    ("internal/secretstore/load.go", "prod", "internal/secretstore", True),
    ("internal/credentials/store.go", "prod", "internal/credentials", True),
    ("internal/apikeys/signer.go", "prod", "internal/apikeys", True),
    ("internal/apitoken/mint.go", "prod", "internal/apitoken", True),
    ("docs/prd.md", "unknown", None, False),
    ("scripts/grading.py", "unknown", None, False),
    ("main_test.go", "test", None, False),
]


def _one_rule_layout(match, strategy):
    """Return a layout carrying one module rule; nothing else classifies."""
    return config.Layout(
        test_globs=(),
        prod_roots=(),
        sensitive=(),
        module_rules=(config.ModuleRule(match, strategy),),
        extra_reviewers=(),
        review={},
        conventions={},
    )


@unittest.skipUnless(
    _LAYOUT.is_file(), "scripts/layout.toml not scaffolded yet (run the harness init)"
)
class Classification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = config.load_layout(_LAYOUT.parent)

    def test_every_path_classifies_as_the_layout_encodes(self):
        for path, kind, module, sensitive in CASES:
            with self.subTest(path=path, field="kind"):
                self.assertEqual(features.classify_kind(path, self.layout), kind)
            with self.subTest(path=path, field="module"):
                self.assertEqual(features.module_of(path, self.layout), module)
            with self.subTest(path=path, field="sensitive"):
                self.assertEqual(features.is_sensitive(path, self.layout), sensitive)


class ModuleStrategies(unittest.TestCase):
    def test_the_source_set_regex_derives_the_module_root(self):
        layout = _one_rule_layout("**/src/main/**", SRC_TREE_PATTERN)

        self.assertEqual(
            features.module_of("app/src/main/java/com/acme/Foo.java", layout),
            "app/src",
        )

    def test_the_source_set_regex_derives_the_same_root_for_a_test(self):
        layout = _one_rule_layout("**/src/test/**", SRC_TREE_PATTERN)

        self.assertEqual(
            features.module_of("svc/src/test/kotlin/com/acme/BarTest.kt", layout),
            "svc/src",
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
