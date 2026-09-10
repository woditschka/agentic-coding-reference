"""Tests for grading.config — the layout-config ACL (stack-agnostic slice).

TestModuleRuleValidation and TestReviewConfigValidation inject synthetic rules
and assert the engine rejects malformed [[module]] / [review] / [harness]
declarations, so they run identically in every stack. They live here in core,
single-sourced, and materialize out. The layout-dependent class that reads a
stack's own scripts/layout.toml (TestLayoutConfig) stays per-stack in
tests/grading/test_config_layout.py.

Run (from the scripts dir): python3 -m unittest tests.grading.test_config
Stdlib only.
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from grading import config


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
            config.validate_module_rules([{"match": "x/**", "from": "dirr"}])

    def test_non_string_from_raises(self):
        # A non-string strategy would hit .startswith with an AttributeError
        # mid-check — rejected as a clean ValueError instead, so the doctor's
        # layout-modules check reports it rather than crashing.
        with self.assertRaises(ValueError):
            config.validate_module_rules([{"match": "x/**", "from": 5}])

    def test_regex_strategy_must_compile(self):
        with self.assertRaises(ValueError):
            config.validate_module_rules([{"match": "x/**", "from": "regex:(x"}])

    def test_regex_strategy_needs_a_capture_group(self):
        # module_of reads group 1 as the module id; a group-less pattern would
        # raise IndexError mid-diff — rejected at load instead.
        with self.assertRaises(ValueError):
            config.validate_module_rules([{"match": "x/**", "from": "regex:x/.*"}])

    def test_every_known_strategy_passes(self):
        # Every accepted form must survive validation unchanged; this pins the
        # validator to the strategies features.module_of actually implements,
        # named layouts included.
        good = [
            {"match": "a/**", "from": "dir"},
            {"match": "b/**", "from": "regex:(b/[^/]+)/"},
            {"match": "c/**", "from": "first-segment-after:c/"},
        ] + [
            {"match": "n/**", "from": name}
            for name in sorted(config.NAMED_MODULE_LAYOUTS)
        ]
        self.assertEqual(config.validate_module_rules(good), good)

    def test_named_layout_patterns_are_valid_regex_strategies(self):
        # Each table entry must itself satisfy the regex-primitive contract
        # (compiles, captures group 1) — a broken curated pattern should fail
        # here, not mid-diff in a consumer's run.
        for name, pattern in config.NAMED_MODULE_LAYOUTS.items():
            with self.subTest(name=name):
                config.validate_module_rules(
                    [{"match": "x/**", "from": f"regex:{pattern}"}]
                )


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


class TestSecuritySurfaceValidation(unittest.TestCase):
    def test_absent_probe_is_empty(self):
        self.assertEqual(
            config.validate_review({}, list(config.REVIEWERS))["security_surface"], []
        )

    def test_bad_regex_raises(self):
        with self.assertRaises(ValueError):
            config.validate_review({"security_surface": ["@("]}, list(config.REVIEWERS))

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            config.validate_review({"security_surface": "@Get"}, list(config.REVIEWERS))


class TestStackDefaultsMerge(unittest.TestCase):
    """scripts/layout-defaults.toml (harness-owned) carries the stack's own
    syntax; the loader merges it under the project's layout.toml key by key,
    so a project never restates stack facts and never falls behind an upgrade."""

    _PROJECT = 'test = ["**/*_test.txt"]\nprod_roots = ["src/"]\n'
    _DEFAULTS = (
        "[conventions]\ncomment_markers = ['//']\nconstruction = 'new\\s+X'\n"
        "[review]\nsecurity_surface = ['@\\w+Mapping']\n"
    )

    def _load(self, project, defaults=None):
        with tempfile.TemporaryDirectory() as tmp:
            scripts = Path(tmp)
            (scripts / "layout.toml").write_text(project, encoding="utf-8")
            if defaults is not None:
                (scripts / "layout-defaults.toml").write_text(
                    defaults, encoding="utf-8"
                )
            return config._load_layout(scripts)

    def test_absent_key_reads_the_stack_default(self):
        layout = self._load(self._PROJECT, self._DEFAULTS)
        self.assertEqual(layout.REVIEW["security_surface"], [r"@\w+Mapping"])
        self.assertEqual(layout.CONVENTIONS["construction"], r"new\s+X")

    def test_declared_key_overrides_the_default(self):
        project = self._PROJECT + "[review]\nsecurity_surface = ['Handle\\(']\n"
        layout = self._load(project, self._DEFAULTS)
        self.assertEqual(layout.REVIEW["security_surface"], [r"Handle\("])

    def test_explicitly_empty_probe_stays_empty(self):
        # Fail closed is the project's call: an empty list declared in
        # layout.toml is never refilled from the stack default.
        project = self._PROJECT + "[review]\nsecurity_surface = []\n"
        layout = self._load(project, self._DEFAULTS)
        self.assertEqual(layout.REVIEW["security_surface"], [])

    def test_merge_is_per_key_not_per_table(self):
        project = self._PROJECT + "[conventions]\ncomment_markers = ['#']\n"
        layout = self._load(project, self._DEFAULTS)
        self.assertEqual(layout.CONVENTIONS["comment_markers"], ["#"])
        self.assertEqual(layout.CONVENTIONS["construction"], r"new\s+X")

    def test_no_defaults_file_reads_the_project_alone(self):
        layout = self._load(self._PROJECT)
        self.assertEqual(layout.REVIEW, {})
        self.assertEqual(layout.CONVENTIONS, {})

    def test_project_fact_inside_a_defaultable_table_fails_loud(self):
        # The allowlist is per key, not per table: a defaults file may not
        # set a surface glob, a threshold, or the mode.
        with self.assertRaises(ValueError):
            self._load(self._PROJECT, self._DEFAULTS + 'docs = ["**/*"]\n')

    def test_shadowed_keys_name_the_restated_defaults(self):
        defaults = {
            "review": {"security_surface": ["a"]},
            "conventions": {"construction": "x"},
        }
        raw = {
            "review": {"security_surface": ["a"]},
            "conventions": {"construction": "y"},
        }
        self.assertEqual(
            config.shadowed_keys(raw, defaults), ["review.security_surface"]
        )

    def test_foreign_table_in_defaults_fails_loud(self):
        # A stack default may carry only stack syntax; a project fact there
        # (test globs, sensitive paths) is misplaced and must not load.
        with self.assertRaises(ValueError):
            self._load(self._PROJECT, 'sensitive = ["**/auth/**"]\n' + self._DEFAULTS)
