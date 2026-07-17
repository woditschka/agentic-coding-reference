"""Tests for grading.features against this stack's real layout.toml (Go).

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
# semantics the Go-default layout encodes today; they must not change when the
# layout source changes shape.
CASES = [
    ("internal/report/summary.go", "prod", "internal/report", False),
    ("internal/report/summary_test.go", "test", "internal/report", False),  # test wins
    ("cmd/example/main.go", "prod", "cmd/example", False),
    ("pkg/foo/bar.go", "prod", "pkg/foo", False),
    ("internal/auth/session.go", "prod", "internal/auth", True),  # **/auth/**
    (
        "internal/auth/session_test.go",
        "test",
        "internal/auth",
        True,
    ),  # test wins, still sensitive
    # One case per remaining sensitive glob, each path chosen to match *only*
    # its intended pattern so a silent deletion of that glob fails this test.
    (
        "internal/secretstore/load.go",
        "prod",
        "internal/secretstore",
        True,
    ),  # **/secret*/**
    (
        "internal/credentials/store.go",
        "prod",
        "internal/credentials",
        True,
    ),  # **/cred*/**
    ("internal/apikeys/signer.go", "prod", "internal/apikeys", True),  # **/*key*/**
    ("internal/apitoken/mint.go", "prod", "internal/apitoken", True),  # **/*token*/**
    ("docs/prd.md", "unknown", None, False),  # under no PROD_ROOT, no TEST glob
    ("scripts/grading.py", "unknown", None, False),
    ("main_test.go", "test", None, False),  # top-level *_test.go, no module rule
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
    """The engine implements three module-derivation strategies. This repo's own
    layout only exercises `dir`, so `maven` and `first-segment-after:` are
    covered here against synthetic layouts — they are the strategies a Java
    (Gradle/Maven) or TypeScript adopter forks the config onto, and must work
    before that repo relies on them. Each subtest swaps the loaded `layout` in
    grading.config for a one-rule namespace, then restores it."""

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

    def test_maven_strategy(self):
        self._with_module_rules([{"match": "**/src/main/**", "from": "maven"}])
        self.assertEqual(
            features.module_of("app/src/main/java/com/acme/Foo.java"),
            "app/src/main/java",
        )

    def test_maven_strategy_test_tree(self):
        self._with_module_rules([{"match": "**/src/test/**", "from": "maven"}])
        self.assertEqual(
            features.module_of("svc/src/test/kotlin/com/acme/BarTest.kt"),
            "svc/src/test/kotlin",
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
