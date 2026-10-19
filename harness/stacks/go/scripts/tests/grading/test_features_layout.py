"""The module strategies the Go slice exercises, on synthetic layouts; the skeleton layout is pinned in the reference's producer suite."""

import unittest

from grading import config, features

SRC_TREE_PATTERN = "regex:((?:.*?/)?src)/(?:main|test)/[^/]+/"


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
