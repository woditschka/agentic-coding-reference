"""Tests for grading.config — the layout-config ACL (stack-agnostic slice).

TestReviewConfigValidation injects synthetic layouts and asserts the engine
rejects malformed [review] / [harness] declarations, so it runs identically in
every stack. It lives here in core, single-sourced, and materializes out. The
layout-dependent classes that read a stack's own scripts/layout.toml
(TestLayoutConfig, TestModuleRuleValidation) stay per-stack in
tests/grading/test_config_layout.py.

Run (from the scripts dir): python3 -m unittest tests.grading.test_config
Stdlib only.
"""

import unittest
from types import SimpleNamespace

from grading import config


class TestReviewConfigValidation(unittest.TestCase):
    """Malformed [review] / [harness] declarations fail loudly at load — no
    plan is appended, so route falls closed to the full battery — never a
    silently wrong roster."""

    def setUp(self):
        self._saved = config.layout
        self.addCleanup(lambda: setattr(config, "layout", self._saved))

    def _inject(self, review=None, extras=None):
        config.layout = SimpleNamespace(
            TEST=[],
            PROD_ROOTS=["src/"],
            SENSITIVE=[],
            MODULE=[],
            REVIEW=review or {},
            EXTRA_REVIEWERS=extras or [],
        )

    def test_defaults_pass_unchanged(self):
        self._inject()
        cfg = config.review_config()
        self.assertEqual(
            cfg["surface_reviewers"],
            {k: list(v) for k, v in config.SURFACE_REVIEWERS.items()},
        )

    def test_bad_size_threshold_raises(self):
        self._inject({"size_threshold": "80"})
        with self.assertRaises(ValueError):
            config.review_config()

    def test_bad_mode_raises(self):
        self._inject({"mode": "sometimes"})
        with self.assertRaises(ValueError):
            config.review_config()

    def test_unknown_surface_raises(self):
        self._inject({"surface_reviewers": {"binary": ["doc-reviewer"]}})
        with self.assertRaises(ValueError):
            config.review_config()

    def test_prod_surface_is_not_overridable(self):
        # A prod mapping would be dead config (production changes never take
        # the surface path) that still marks its extras "mapped" and silently
        # narrows their always-join — rejected loudly instead.
        self._inject({"surface_reviewers": {"prod": ["code-quality-reviewer"]}})
        with self.assertRaises(ValueError):
            config.review_config()

    def test_non_roster_map_target_raises(self):
        self._inject({"surface_reviewers": {"docs": ["stranger-reviewer"]}})
        with self.assertRaises(ValueError):
            config.review_config()

    def test_declared_extra_is_a_valid_map_target(self):
        self._inject(
            {"surface_reviewers": {"docs": ["doc-reviewer", "style-reviewer"]}},
            extras=["style-reviewer"],
        )
        cfg = config.review_config()
        self.assertEqual(
            cfg["surface_reviewers"]["docs"], ["doc-reviewer", "style-reviewer"]
        )

    def test_malformed_extras_raise(self):
        with self.assertRaises(ValueError):
            config.validate_reviewer_extras(["style-reviewer", 3])


if __name__ == "__main__":
    unittest.main(verbosity=2)
