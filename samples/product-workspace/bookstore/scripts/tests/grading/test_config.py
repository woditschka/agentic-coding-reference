"""The layout loader and its validation walls: module rules, reviewer extras, [review], the stack defaults."""

import tempfile
import unittest
from pathlib import Path

from grading.config import (
    NAMED_MODULE_LAYOUTS,
    REVIEWERS,
    SURFACE_REVIEWERS,
    LayoutError,
    ModuleRule,
    load_layout,
    shadowed_keys,
    validate_module_rules,
    validate_review,
    validate_reviewer_extras,
)

A_GLOB = "x/**"
AN_EXTRA_REVIEWER = "style-reviewer"
A_STRANGER = "stranger-reviewer"
A_PROJECT_LAYOUT = 'test = ["**/*_test.txt"]\nprod_roots = ["src/"]\n'
STACK_DEFAULTS = (
    "[conventions]\ncomment_markers = ['//']\nconstruction = 'new\\s+X'\n"
    "[review]\nsecurity_surface = ['@\\w+Mapping']\n"
)


def load_from_text(project, defaults=None):
    """Load a layout from the project text and the optional stack defaults beside it."""
    with tempfile.TemporaryDirectory() as tmp:
        scripts = Path(tmp)
        (scripts / "layout.toml").write_text(project, encoding="utf-8")
        if defaults is not None:
            (scripts / "layout-defaults.toml").write_text(defaults, encoding="utf-8")
        return load_layout(scripts)


class ModuleRuleValidation(unittest.TestCase):
    def test_every_known_strategy_loads_as_a_rule(self):
        rules = [
            {"match": "a/**", "from": "dir"},
            {"match": "b/**", "from": "regex:(b/[^/]+)/"},
            {"match": "c/**", "from": "first-segment-after:c/"},
            {"match": "n/**", "from": "gradle"},
        ]

        self.assertEqual(
            validate_module_rules(rules),
            (
                ModuleRule("a/**", "dir"),
                ModuleRule("b/**", "regex:(b/[^/]+)/"),
                ModuleRule("c/**", "first-segment-after:c/"),
                ModuleRule("n/**", "gradle"),
            ),
        )

    def test_every_named_layout_is_a_valid_regex_strategy(self):
        for name, pattern in NAMED_MODULE_LAYOUTS.items():
            with self.subTest(name=name):
                validate_module_rules([{"match": A_GLOB, "from": f"regex:{pattern}"}])

    def test_a_malformed_rule_is_rejected(self):
        cases = {
            "missing from": {"match": A_GLOB},
            "missing match": {"from": "dir"},
            "non-string match": {"match": 5, "from": "dir"},
            "non-string from": {"match": A_GLOB, "from": 5},
            "unknown strategy": {"match": A_GLOB, "from": "dirr"},
            "regex that does not compile": {"match": A_GLOB, "from": "regex:(x"},
            "regex without a capture group": {"match": A_GLOB, "from": "regex:x/.*"},
        }
        for label, rule in cases.items():
            with self.subTest(label), self.assertRaises(ValueError):
                validate_module_rules([rule])

    def test_a_non_list_module_section_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_module_rules({"match": A_GLOB, "from": "dir"})


class ReviewValidation(unittest.TestCase):
    def test_defaults_pass_unchanged(self):
        review = validate_review({}, REVIEWERS)

        self.assertEqual(review.surface_reviewers, SURFACE_REVIEWERS)
        self.assertEqual(review.security_surface, ())

    def test_a_declared_extra_is_a_valid_map_target(self):
        raw = {"surface_reviewers": {"docs": ["doc-reviewer", AN_EXTRA_REVIEWER]}}

        review = validate_review(raw, [*REVIEWERS, AN_EXTRA_REVIEWER])

        self.assertEqual(
            review.surface_reviewers["docs"], ("doc-reviewer", AN_EXTRA_REVIEWER)
        )

    def test_a_malformed_table_is_rejected(self):
        cases = {
            "docs globs that are a string": {"docs": "*.md"},
            "string threshold": {"size_threshold": "80"},
            "unknown mode": {"mode": "sometimes"},
            "unknown surface": {"surface_reviewers": {"binary": ["doc-reviewer"]}},
            "prod surface": {"surface_reviewers": {"prod": ["code-quality-reviewer"]}},
            "non-roster target": {"surface_reviewers": {"docs": [A_STRANGER]}},
            "bad probe regex": {"security_surface": ["@("]},
            "non-list probe": {"security_surface": "@Get"},
        }
        for label, raw in cases.items():
            with self.subTest(label), self.assertRaises(ValueError):
                validate_review(raw, REVIEWERS)

    def test_malformed_extras_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_reviewer_extras([AN_EXTRA_REVIEWER, 3])


class LayoutLoad(unittest.TestCase):
    def test_the_roster_is_the_floor_plus_declared_extras(self):
        layout = load_from_text(
            A_PROJECT_LAYOUT + f'[harness]\nextra_reviewers = ["{AN_EXTRA_REVIEWER}"]\n'
        )

        self.assertEqual(layout.roster, (*REVIEWERS, AN_EXTRA_REVIEWER))

    def test_an_extra_restating_a_floor_reviewer_joins_the_roster_once(self):
        layout = load_from_text(
            A_PROJECT_LAYOUT + f'[harness]\nextra_reviewers = ["{REVIEWERS[-1]}"]\n'
        )

        self.assertEqual(layout.roster, REVIEWERS)

    def test_a_missing_or_unparsable_layout_is_a_layout_fault(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(LayoutError):
            load_layout(Path(tmp))
        with self.assertRaises(LayoutError):
            load_from_text("test = [\n")

    def test_a_non_list_classification_key_is_rejected(self):
        for key in ("test", "prod_roots", "sensitive"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                load_from_text(f'{key} = "src/"\n')

    def test_an_empty_classification_entry_is_rejected(self):
        for key in ("test", "prod_roots", "sensitive"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                load_from_text(f'{key} = [""]\n')

    def test_a_table_key_holding_a_scalar_is_rejected(self):
        with self.assertRaises(ValueError):
            load_from_text(A_PROJECT_LAYOUT + "review = 5\n")


class StackDefaultsMerge(unittest.TestCase):
    def test_an_absent_key_reads_the_stack_default(self):
        layout = load_from_text(A_PROJECT_LAYOUT, STACK_DEFAULTS)

        self.assertEqual(layout.review["security_surface"], [r"@\w+Mapping"])
        self.assertEqual(layout.conventions["construction"], r"new\s+X")

    def test_a_declared_key_overrides_the_default(self):
        project = A_PROJECT_LAYOUT + "[review]\nsecurity_surface = ['Handle\\(']\n"

        layout = load_from_text(project, STACK_DEFAULTS)

        self.assertEqual(layout.review["security_surface"], [r"Handle\("])

    def test_an_explicitly_empty_probe_stays_empty(self):
        project = A_PROJECT_LAYOUT + "[review]\nsecurity_surface = []\n"

        layout = load_from_text(project, STACK_DEFAULTS)

        self.assertEqual(layout.review["security_surface"], [])

    def test_the_merge_is_per_key_not_per_table(self):
        project = A_PROJECT_LAYOUT + "[conventions]\ncomment_markers = ['#']\n"

        layout = load_from_text(project, STACK_DEFAULTS)

        self.assertEqual(layout.conventions["comment_markers"], ["#"])
        self.assertEqual(layout.conventions["construction"], r"new\s+X")

    def test_no_defaults_file_reads_the_project_alone(self):
        layout = load_from_text(A_PROJECT_LAYOUT)

        self.assertEqual((layout.review, layout.conventions), ({}, {}))

    def test_a_project_fact_inside_a_defaultable_table_fails_loud(self):
        with self.assertRaises(ValueError):
            load_from_text(A_PROJECT_LAYOUT, STACK_DEFAULTS + 'docs = ["**/*"]\n')

    def test_a_foreign_table_in_the_defaults_fails_loud(self):
        with self.assertRaises(ValueError):
            load_from_text(
                A_PROJECT_LAYOUT, 'sensitive = ["**/auth/**"]\n' + STACK_DEFAULTS
            )

    def test_shadowed_keys_name_the_restated_defaults(self):
        defaults = {
            "review": {"security_surface": ["a"]},
            "conventions": {"construction": "x"},
        }
        raw = {
            "review": {"security_surface": ["a"]},
            "conventions": {"construction": "y"},
        }

        self.assertEqual(shadowed_keys(raw, defaults), ["review.security_surface"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
