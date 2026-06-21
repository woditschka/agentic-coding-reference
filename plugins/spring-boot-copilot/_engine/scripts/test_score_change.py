"""Characterization tests for score-change.py's file classifier.

These freeze the classification contract (kind / module / sensitive) so the
layout-config storage format can change underneath the engine without altering
the feature row it emits. They exercise this project's Java/Gradle layout.toml
and must stay green so the engine and the config stay in lockstep.

Run: python3 scripts/test_score_change.py
Stdlib only.
"""

import importlib.util
import shutil
import subprocess
import tempfile
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
# semantics the Java/Gradle layout encodes today; they must not change when the
# layout source changes shape. Module ids come from the "maven" strategy: its
# regex requires a path segment before "src/", so a repo-root-relative
# "src/main/java/..." path falls through to the file's parent directory, while a
# nested-module "app/src/main/java/..." path resolves to the package root.
CASES = [
    ("src/main/java/com/example/Foo.java", "prod", "src/main/java/com/example", False),
    ("src/test/java/com/example/FooTest.java", "test", "src/test/java/com/example", False),  # test wins
    ("src/test/java/com/example/FooTests.java", "test", "src/test/java/com/example", False),  # **/*Tests.java
    ("src/test/java/com/example/FooIT.java", "test", "src/test/java/com/example", False),  # **/*IT.java
    ("src/main/java/com/example/security/SecurityConfig.java", "prod", "src/main/java/com/example/security", True),  # **/security/**
    ("src/main/java/com/example/auth/Session.java", "prod", "src/main/java/com/example/auth", True),  # **/auth/**
    ("src/test/java/com/example/auth/SessionTest.java", "test", "src/test/java/com/example/auth", True),  # test wins, still sensitive
    # One case per remaining sensitive glob, each path chosen to match *only*
    # its intended pattern so a silent deletion of that glob fails this test.
    ("src/main/java/com/example/secretstore/Load.java", "prod", "src/main/java/com/example/secretstore", True),  # **/secret*/**
    ("src/main/java/com/example/credentials/Store.java", "prod", "src/main/java/com/example/credentials", True),  # **/cred*/**
    ("src/main/java/com/example/apikeys/Signer.java", "prod", "src/main/java/com/example/apikeys", True),  # **/*key*/**
    ("src/main/java/com/example/apitoken/Mint.java", "prod", "src/main/java/com/example/apitoken", True),  # **/*token*/**
    ("docs/prd.md", "unknown", None, False),  # under no PROD_ROOT, no TEST glob
    ("scripts/score-change.py", "unknown", None, False),
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
    layout exercises `maven`; `dir` and `first-segment-after:` are covered here
    against synthetic layouts so the strategies a Go or TypeScript adopter forks
    the config onto stay working. Each subtest swaps the engine's loaded
    `layout` for a one-rule namespace, then restores it."""

    def _with_module_rules(self, rules):
        """Swap the engine's layout for a one-rule namespace for this test.

        Call at most once per test method: `saved` is captured at call time, so
        a second call would snapshot the already-patched layout and the cleanups
        would not restore the original.
        """
        saved = ENGINE.layout
        ENGINE.layout = SimpleNamespace(TEST=[], PROD_ROOTS=[], SENSITIVE=[], EXCLUDE=[], MODULE=rules)
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
            ENGINE._module_of("svc/src/test/java/com/acme/BarTest.java"),
            "svc/src/test/java",
        )

    def test_maven_strategy_repo_root_falls_through_to_parent(self):
        # The maven regex requires a segment before "src/"; a repo-root-relative
        # path has none, so the strategy falls through to the file's parent dir.
        self._with_module_rules([{"match": "src/main/**", "from": "maven"}])
        self.assertEqual(
            ENGINE._module_of("src/main/java/com/acme/Foo.java"),
            "src/main/java/com/acme",
        )

    def test_dir_strategy(self):
        self._with_module_rules([{"match": "internal/**", "from": "dir"}])
        self.assertEqual(ENGINE._module_of("internal/report/summary.go"), "internal/report")

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


class TestExcludePathspecs(unittest.TestCase):
    """exclude_globs becomes git exclude pathspecs applied to every diff the
    change set is read through (numstat, unified, name-only), so the reviewer's
    view through changeset.sh and the grader's row drop the same paths. An empty
    list yields no pathspec — the whole diff."""

    def _with_exclude(self, globs):
        saved = ENGINE.layout
        ENGINE.layout = SimpleNamespace(
            TEST=[], PROD_ROOTS=[], SENSITIVE=[], EXCLUDE=globs, MODULE=[]
        )
        self.addCleanup(lambda: setattr(ENGINE, "layout", saved))

    def test_empty_yields_no_pathspec(self):
        self._with_exclude([])
        self.assertEqual(ENGINE._exclude_pathspecs(), [])

    def test_globs_become_exclude_pathspecs(self):
        self._with_exclude(["vendor/**", "gen/*.pb.go"])
        # Repo-root-relative (:(top)) so the change set is cwd-independent, with
        # glob magic so '**' crosses directories as layout.toml documents.
        self.assertEqual(
            ENGINE._exclude_pathspecs(),
            ["--", ":(top)",
             ":(top,glob,exclude)vendor/**", ":(top,glob,exclude)gen/*.pb.go"],
        )

    def test_real_layout_exposes_exclude_list(self):
        # The shipped layout.toml carries exclude_globs (default empty); the
        # loader must surface it as a list so the pathspec builder never crashes.
        ENGINE._get_layout()
        self.assertIsInstance(ENGINE.layout.EXCLUDE, list)


class TestBaseDefault(unittest.TestCase):
    """base defaults to HEAD only for the live worktree flow. A committed --head
    with no --base is rejected: the HEAD default would diff a commit against
    itself and silently emit an empty range — a real post-hoc regression."""

    def test_worktree_defaults_to_head(self):
        self.assertEqual(
            ENGINE._base_arg(SimpleNamespace(base=None, head="WORKTREE")),
            ("HEAD", None),
        )

    def test_explicit_base_is_kept(self):
        self.assertEqual(
            ENGINE._base_arg(SimpleNamespace(base="main", head="WORKTREE")),
            ("main", None),
        )

    def test_committed_head_without_base_errors(self):
        base, err = ENGINE._base_arg(SimpleNamespace(base=None, head="abc1234"))
        self.assertIsNone(base)
        self.assertIsNotNone(err)


class TestLayoutConfig(unittest.TestCase):
    """The engine exposes the loaded layout as `layout` with five attributes,
    regardless of where the data came from."""

    def setUp(self):
        # The layout global is loaded lazily; trigger the load so these tests
        # read a populated `layout` regardless of test ordering or isolation.
        ENGINE._get_layout()

    def test_prod_roots(self):
        for root in ("src/main/java/", "src/main/"):
            self.assertIn(root, ENGINE.layout.PROD_ROOTS)

    def test_test_globs(self):
        for glob in ("**/*Test.java", "**/*Tests.java", "**/*IT.java", "src/test/**"):
            self.assertIn(glob, ENGINE.layout.TEST)

    def test_module_rules_are_match_from_pairs(self):
        self.assertTrue(
            any(r["match"] == "src/main/java/**" and r["from"] == "maven" for r in ENGINE.layout.MODULE),
            "expected a src/main/java/** -> maven module rule",
        )

    def test_sensitive_overlay(self):
        self.assertTrue(any("security" in g for g in ENGINE.layout.SENSITIVE))


class TestExcludeBehaviorEndToEnd(unittest.TestCase):
    """The exclude pathspecs actually drop matching files from a real git diff —
    the coverage a string-construction check misses. Guards against cwd-relativity
    and glob-semantics regressions in _exclude_pathspecs feeding real git."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)

        def git(*a):
            subprocess.run(["git", "-C", str(self.dir), *a], check=True,
                           capture_output=True, text=True)

        git("init", "-q")
        git("config", "user.email", "t@example.com")
        git("config", "user.name", "t")
        (self.dir / "keep.txt").write_text("a\n")
        (self.dir / "vendor").mkdir()
        (self.dir / "vendor" / "lib.txt").write_text("a\n")
        git("add", "-A")
        git("commit", "-qm", "base")
        (self.dir / "keep.txt").write_text("b\n")
        (self.dir / "vendor" / "lib.txt").write_text("b\n")
        git("add", "-A")
        git("commit", "-qm", "change")

    def _names_with_exclude(self, globs):
        saved = ENGINE.layout
        ENGINE.layout = SimpleNamespace(
            TEST=[], PROD_ROOTS=[], SENSITIVE=[], EXCLUDE=globs, MODULE=[]
        )
        self.addCleanup(lambda: setattr(ENGINE, "layout", saved))
        out = subprocess.run(
            ["git", "-C", str(self.dir), "diff", "--name-only", "HEAD~1", "HEAD",
             *ENGINE._exclude_pathspecs()],
            check=True, capture_output=True, text=True,
        ).stdout
        return out.split()

    def test_no_exclude_shows_all(self):
        self.assertEqual(sorted(self._names_with_exclude([])),
                         ["keep.txt", "vendor/lib.txt"])

    def test_exclude_drops_matching_and_keeps_rest(self):
        names = self._names_with_exclude(["vendor/**"])
        self.assertIn("keep.txt", names)
        self.assertNotIn("vendor/lib.txt", names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
