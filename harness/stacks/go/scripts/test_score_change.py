"""Characterization tests for score-change.py's file classifier.

These freeze the classification contract (kind / module / sensitive) so the
layout-config storage format can change underneath the engine without altering
the feature row it emits. They were validated against the original `layout.py`
and must stay green now that the layout source is declarative `layout.toml`.

Run: python3 scripts/test_score_change.py
Stdlib only.
"""

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

_HERE = Path(__file__).resolve().parent


def _load_engine():
    """Load score-change.py (a hyphenated, non-importable name) by file path."""
    spec = importlib.util.spec_from_file_location("score_change", _HERE / "score-change.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ENGINE = _load_engine()

# (path, expected_kind, expected_module, expected_sensitive). These freeze the
# semantics the Go-default layout encodes today; they must not change when the
# layout source moves from Python to TOML.
CASES = [
    ("internal/report/summary.go", "prod", "internal/report", False),
    ("internal/report/summary_test.go", "test", "internal/report", False),  # test wins
    ("cmd/example/main.go", "prod", "cmd/example", False),
    ("pkg/foo/bar.go", "prod", "pkg/foo", False),
    ("internal/auth/session.go", "prod", "internal/auth", True),  # **/auth/**
    ("internal/auth/session_test.go", "test", "internal/auth", True),  # test wins, still sensitive
    # One case per remaining sensitive glob, each path chosen to match *only*
    # its intended pattern so a silent deletion of that glob fails this test.
    ("internal/secretstore/load.go", "prod", "internal/secretstore", True),  # **/secret*/**
    ("internal/credentials/store.go", "prod", "internal/credentials", True),  # **/cred*/**
    ("internal/apikeys/signer.go", "prod", "internal/apikeys", True),  # **/*key*/**
    ("internal/apitoken/mint.go", "prod", "internal/apitoken", True),  # **/*token*/**
    ("docs/prd.md", "unknown", None, False),  # under no PROD_ROOT, no TEST glob
    ("scripts/score-change.py", "unknown", None, False),
    ("main_test.go", "test", None, False),  # top-level *_test.go, no module rule
]


class TestClassification(unittest.TestCase):
    def test_kind_module_sensitive(self):
        for path, kind, module, sensitive in CASES:
            with self.subTest(path=path, field="kind"):
                self.assertEqual(ENGINE._classify_kind(path), kind)
            with self.subTest(path=path, field="module"):
                self.assertEqual(ENGINE._module_of(path), module)
            with self.subTest(path=path, field="sensitive"):
                self.assertEqual(ENGINE._sensitive(path), sensitive)


class TestModuleStrategies(unittest.TestCase):
    """The engine implements three module-derivation strategies. This repo's own
    layout only exercises `dir`, so `maven` and `first-segment-after:` are
    covered here against synthetic layouts — they are the strategies a Java
    (Gradle/Maven) or TypeScript adopter forks the config onto, and must work
    before that repo relies on them. Each subtest swaps the engine's loaded
    `layout` for a one-rule namespace, then restores it."""

    def _with_module_rules(self, rules):
        """Swap the engine's layout for a one-rule namespace for this test.

        Call at most once per test method: `saved` is captured at call time, so
        a second call would snapshot the already-patched layout and the cleanups
        would not restore the original.
        """
        saved = ENGINE.layout
        ENGINE.layout = SimpleNamespace(TEST=[], PROD_ROOTS=[], SENSITIVE=[], MODULE=rules)
        self.addCleanup(lambda: setattr(ENGINE, "layout", saved))

    def test_maven_strategy(self):
        self._with_module_rules([{"match": "**/src/main/**", "from": "maven"}])
        self.assertEqual(
            ENGINE._module_of("app/src/main/java/com/acme/Foo.java"),
            "app/src/main/java",
        )

    def test_maven_strategy_test_tree(self):
        self._with_module_rules([{"match": "**/src/test/**", "from": "maven"}])
        self.assertEqual(
            ENGINE._module_of("svc/src/test/kotlin/com/acme/BarTest.kt"),
            "svc/src/test/kotlin",
        )

    def test_first_segment_after_strategy(self):
        self._with_module_rules(
            [{"match": "packages/**", "from": "first-segment-after:packages/"}]
        )
        # The module id keeps its path prefix (so cross-stack changes read as
        # wider scatter), so the result is "packages/ui", not bare "ui".
        self.assertEqual(ENGINE._module_of("packages/ui/src/index.ts"), "packages/ui")

    def test_unmatched_path_yields_none(self):
        self._with_module_rules([{"match": "packages/**", "from": "dir"}])
        self.assertIsNone(ENGINE._module_of("docs/readme.md"))


class TestModuleRuleValidation(unittest.TestCase):
    """A malformed [[module]] entry must fail cleanly at load, not as a bare
    KeyError deep in the diff loop."""

    def test_missing_from_raises(self):
        with self.assertRaises(ValueError):
            ENGINE._validate_module_rules([{"match": "x/**"}])

    def test_missing_match_raises(self):
        with self.assertRaises(ValueError):
            ENGINE._validate_module_rules([{"from": "dir"}])

    def test_unknown_strategy_raises(self):
        with self.assertRaises(ValueError):
            ENGINE._validate_module_rules([{"match": "x/**", "from": "mavenn"}])

    def test_every_known_strategy_passes(self):
        # The three accepted forms must survive validation unchanged; this pins
        # the validator to the strategies _module_of actually implements.
        good = [
            {"match": "a/**", "from": "dir"},
            {"match": "b/**", "from": "maven"},
            {"match": "c/**", "from": "first-segment-after:c/"},
        ]
        self.assertEqual(ENGINE._validate_module_rules(good), good)


class TestLayoutConfig(unittest.TestCase):
    """The engine exposes the loaded layout as `layout` with four attributes,
    regardless of where the data came from."""

    def setUp(self):
        # The layout global is loaded lazily; trigger the load so these tests
        # read a populated `layout` regardless of test ordering or isolation.
        ENGINE._get_layout()

    def test_prod_roots(self):
        for root in ("internal/", "cmd/", "pkg/"):
            self.assertIn(root, ENGINE.layout.PROD_ROOTS)

    def test_test_globs(self):
        self.assertIn("**/*_test.go", ENGINE.layout.TEST)
        self.assertIn("*_test.go", ENGINE.layout.TEST)

    def test_module_rules_are_match_from_pairs(self):
        self.assertTrue(
            any(r["match"] == "internal/**" and r["from"] == "dir" for r in ENGINE.layout.MODULE),
            "expected an internal/** -> dir module rule",
        )

    def test_sensitive_overlay(self):
        self.assertTrue(any("auth" in g for g in ENGINE.layout.SENSITIVE))


if __name__ == "__main__":
    unittest.main(verbosity=2)
