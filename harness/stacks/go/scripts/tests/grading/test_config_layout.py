"""Tests for grading.config against this stack's real layout.toml (Go).

TestLayoutConfig reads this project's own scripts/layout.toml, so it skips on
a pre-init tree (marketplace setup.sh runs before the scaffold); every
scaffolded project runs it in full. TestModuleRuleValidation injects synthetic
module rules and runs everywhere, but its accepted-strategy set is this stack's,
so it stays here. The stack-agnostic review-config validation lives in core
(tests/grading/test_config.py).

Run (from the scripts dir): python3 -m unittest tests.grading.test_config_layout
Stdlib only.
"""

import unittest
from pathlib import Path

from grading import config

# The scripts dir (tests/grading/ lives two levels under it).
_LAYOUT = Path(__file__).resolve().parent.parent.parent / "layout.toml"


@unittest.skipUnless(
    _LAYOUT.is_file(), "scripts/layout.toml not scaffolded yet (run the harness init)"
)
class TestLayoutConfig(unittest.TestCase):
    """The loader exposes the project's layout as `layout` with the declared
    attributes, regardless of where the data came from."""

    def setUp(self):
        # The layout global is loaded lazily; trigger the load so these tests
        # read a populated `layout` regardless of test ordering or isolation.
        config.get_layout()

    def test_prod_roots(self):
        for root in ("internal/", "cmd/", "pkg/"):
            self.assertIn(root, config.layout.PROD_ROOTS)

    def test_test_globs(self):
        self.assertIn("**/*_test.go", config.layout.TEST)
        self.assertIn("*_test.go", config.layout.TEST)

    def test_module_rules_are_match_from_pairs(self):
        self.assertTrue(
            any(
                r["match"] == "internal/**" and r["from"] == "dir"
                for r in config.layout.MODULE
            ),
            "expected an internal/** -> dir module rule",
        )

    def test_sensitive_overlay(self):
        self.assertTrue(any("auth" in g for g in config.layout.SENSITIVE))


class TestModuleRuleValidation(unittest.TestCase):
    """A malformed [[module]] entry must fail cleanly at load, not as a bare
    KeyError deep in the diff loop."""

    def test_missing_from_raises(self):
        with self.assertRaises(ValueError):
            config.validate_module_rules([{"match": "x/**"}])

    def test_missing_match_raises(self):
        with self.assertRaises(ValueError):
            config.validate_module_rules([{"from": "dir"}])

    def test_unknown_strategy_raises(self):
        with self.assertRaises(ValueError):
            config.validate_module_rules([{"match": "x/**", "from": "mavenn"}])

    def test_every_known_strategy_passes(self):
        # The three accepted forms must survive validation unchanged; this pins
        # the validator to the strategies features.module_of actually implements.
        good = [
            {"match": "a/**", "from": "dir"},
            {"match": "b/**", "from": "maven"},
            {"match": "c/**", "from": "first-segment-after:c/"},
        ]
        self.assertEqual(config.validate_module_rules(good), good)


if __name__ == "__main__":
    unittest.main(verbosity=2)
