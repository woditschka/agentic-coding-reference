"""Tests for grading.features against this stack's real layout.toml (Java Spring Boot).

TestClassification freezes the classification contract (kind / module /
sensitive) against this project's own layout.toml, so the layout-config
storage format can change underneath the engine without altering the feature
row it emits; it skips on a pre-init tree. TestModuleStrategies injects
synthetic layouts and runs everywhere, but the strategies this stack exercises
are its own, so it stays here. The stack-agnostic review-kind and numstat pins
live in core (tests/grading/test_features.py).

Run (from the scripts dir): python3 -m unittest tests.grading.test_features_layout
Stdlib only.
"""

import unittest
from pathlib import Path
from types import SimpleNamespace

from grading import config, features

# The scripts dir (tests/grading/ lives two levels under it).
_LAYOUT = Path(__file__).resolve().parent.parent.parent / "layout.toml"

# (path, expected_kind, expected_module, expected_sensitive). These freeze the
# semantics the Java/Gradle layout encodes today; they must not change when the
# layout source changes shape. Module ids come from the "gradle" named layout:
# the module id is the source-set root, with or without a module prefix — a
# repo-root single-module tree derives "src/<set>/<lang>" directly. The
# parent-directory fallback covers only paths outside the source-set shape.
CASES = [
    ("src/main/java/com/example/Foo.java", "prod", "src/main/java", False),
    (
        "src/test/java/com/example/FooTest.java",
        "test",
        "src/test/java",
        False,
    ),  # test wins
    (
        "src/test/java/com/example/FooTests.java",
        "test",
        "src/test/java",
        False,
    ),  # **/*Tests.java
    (
        "src/test/java/com/example/FooIT.java",
        "test",
        "src/test/java",
        False,
    ),  # **/*IT.java
    (
        "src/main/java/com/example/security/SecurityConfig.java",
        "prod",
        "src/main/java",
        True,
    ),  # **/security/**
    (
        "src/main/java/com/example/auth/Session.java",
        "prod",
        "src/main/java",
        True,
    ),  # **/auth/**
    (
        "src/test/java/com/example/auth/SessionTest.java",
        "test",
        "src/test/java",
        True,
    ),  # test wins, still sensitive
    # One case per remaining sensitive glob, each path chosen to match *only*
    # its intended pattern so a silent deletion of that glob fails this test.
    (
        "src/main/java/com/example/secretstore/Load.java",
        "prod",
        "src/main/java",
        True,
    ),  # **/secret*/**
    (
        "src/main/java/com/example/credentials/Store.java",
        "prod",
        "src/main/java",
        True,
    ),  # **/cred*/**
    (
        "src/main/java/com/example/apikeys/Signer.java",
        "prod",
        "src/main/java",
        True,
    ),  # **/*key*/**
    (
        "src/main/java/com/example/apitoken/Mint.java",
        "prod",
        "src/main/java",
        True,
    ),  # **/*token*/**
    ("docs/prd.md", "unknown", None, False),  # under no PROD_ROOT, no TEST glob
    ("scripts/grading.py", "unknown", None, False),
]


@unittest.skipUnless(
    _LAYOUT.is_file(), "scripts/layout.toml not scaffolded yet (run the harness init)"
)
class TestClassification(unittest.TestCase):
    def test_kind_module_sensitive(self):
        for path, kind, module, sensitive in CASES:
            with self.subTest(path=path, field="kind"):
                self.assertEqual(features.classify_kind(path), kind)
            with self.subTest(path=path, field="module"):
                self.assertEqual(features.module_of(path), module)
            with self.subTest(path=path, field="sensitive"):
                self.assertEqual(features.is_sensitive(path), sensitive)


class TestModuleStrategies(unittest.TestCase):
    """This repo's own layout exercises the `gradle` named layout; the path
    primitives (`dir`, `first-segment-after:`, `regex:`) are covered here
    against synthetic layouts. The `regex:` cases pin the Gradle/Maven
    source-set pattern the named layout expands to, so the multi-module
    derivation must work before an adopter relies on it (the name-to-pattern
    equivalence itself pins in core: TestNamedModuleLayouts). Each subtest
    swaps the loaded `layout` in grading.config for a one-rule namespace,
    then restores it."""

    def _with_module_rules(self, rules):
        """Swap the loaded layout for a one-rule namespace for this test.

        Call at most once per test method: `saved` is captured at call time, so
        a second call would snapshot the already-patched layout and the cleanups
        would not restore the original.
        """
        saved = config.layout
        config.layout = SimpleNamespace(
            TEST=[], PROD_ROOTS=[], SENSITIVE=[], MODULE=rules
        )
        self.addCleanup(lambda: setattr(config, "layout", saved))

    def test_gradle_named_layout_derives_source_set_root(self):
        # The named layout this stack's layout.toml uses, on real Java paths:
        # multi-module derivation must work before an adopter relies on it.
        self._with_module_rules([{"match": "**/src/main/**", "from": "gradle"}])
        self.assertEqual(
            features.module_of("app/src/main/java/com/acme/Foo.java"),
            "app/src/main/java",
        )

    def test_regex_strategy_derives_gradle_maven_source_set_root(self):
        # The documented multi-module Gradle/Maven pattern from this stack's
        # layout.toml: group 1 is the source-set root.
        self._with_module_rules(
            [
                {
                    "match": "**/src/main/**",
                    "from": "regex:((?:.*?/)?src/(?:main|test)/[^/]+)/",
                }
            ]
        )
        self.assertEqual(
            features.module_of("app/src/main/java/com/acme/Foo.java"),
            "app/src/main/java",
        )

    def test_regex_strategy_test_tree(self):
        self._with_module_rules(
            [
                {
                    "match": "**/src/test/**",
                    "from": "regex:((?:.*?/)?src/(?:main|test)/[^/]+)/",
                }
            ]
        )
        self.assertEqual(
            features.module_of("svc/src/test/java/com/acme/BarTest.java"),
            "svc/src/test/java",
        )

    def test_regex_strategy_repo_root_derives_the_source_set_root(self):
        # The source-set regex takes an optional module prefix: a
        # repo-root-relative path (no segment before "src/") derives the
        # source-set root directly. The per-package parent fallback it
        # previously hit inflated module counts on single-module trees.
        self._with_module_rules(
            [
                {
                    "match": "src/main/**",
                    "from": "regex:((?:.*?/)?src/(?:main|test)/[^/]+)/",
                }
            ]
        )
        self.assertEqual(
            features.module_of("src/main/java/com/acme/Foo.java"),
            "src/main/java",
        )

    def test_dir_strategy(self):
        self._with_module_rules([{"match": "internal/**", "from": "dir"}])
        self.assertEqual(
            features.module_of("internal/report/summary.go"), "internal/report"
        )

    def test_first_segment_after_strategy(self):
        self._with_module_rules(
            [{"match": "packages/**", "from": "first-segment-after:packages/"}]
        )
        # The module id keeps its path prefix (so cross-stack changes read as
        # wider scatter), so the result is "packages/ui", not bare "ui".
        self.assertEqual(features.module_of("packages/ui/src/index.ts"), "packages/ui")

    def test_unmatched_path_yields_none(self):
        self._with_module_rules([{"match": "packages/**", "from": "dir"}])
        self.assertIsNone(features.module_of("docs/readme.md"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
