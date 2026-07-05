"""Characterization tests for score-change.py's file classifier — generic stack.

These freeze the classification contract (kind / module / sensitive) the
change-grading skill documents: test wins over prod, unknown fallback, and the
sensitive overlay. The generic stack's shipped layout.toml is a placeholder the
project replaces, so every classification case here runs against a synthetic
layout injected into the engine — the suite pins the engine's semantics, never
any particular project's globs, and stays green after the project fills in its
real layout.

Run: python3 scripts/test_score_change.py
Stdlib only.
"""

import importlib.util
import json
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


def _inject_layout(case, **overrides):
    """Swap the engine's layout for a synthetic namespace for this test case.

    Call at most once per test method: the original is captured at call time,
    so a second call would snapshot the already-patched layout and the cleanups
    would not restore the original.
    """
    saved = ENGINE.layout
    fields = dict(TEST=[], PROD_ROOTS=[], SENSITIVE=[], EXCLUDE=[], MODULE=[])
    fields.update(overrides)
    ENGINE.layout = SimpleNamespace(**fields)
    case.addCleanup(lambda: setattr(ENGINE, "layout", saved))


class TestClassificationContract(unittest.TestCase):
    """The contract the change-grading skill documents, against a synthetic
    layout: test wins over prod_roots, no-match yields unknown (never prod),
    sensitive is an independent overlay flag."""

    def setUp(self):
        _inject_layout(
            self,
            TEST=["**/*_test.*", "*_test.*"],
            PROD_ROOTS=["src/"],
            SENSITIVE=["**/auth/**"],
            MODULE=[{"match": "src/**", "from": "dir"}],
        )

    # (path, expected_kind, expected_module, expected_sensitive)
    CASES = [
        ("src/billing/invoice.py", "prod", "src/billing", False),
        ("src/billing/invoice_test.py", "test", "src/billing", False),  # test wins
        ("src/auth/session.py", "prod", "src/auth", True),  # sensitive overlay
        ("src/auth/session_test.py", "test", "src/auth", True),  # test wins, still sensitive
        ("docs/prd.md", "unknown", None, False),  # under no prod root, no test glob
        ("main_test.py", "test", None, False),  # top-level test, no module rule
    ]

    def test_kind_module_sensitive(self):
        for path, kind, module, sensitive in self.CASES:
            with self.subTest(path=path, field="kind"):
                self.assertEqual(ENGINE._classify_kind(path), kind)
            with self.subTest(path=path, field="module"):
                self.assertEqual(ENGINE._module_of(path), module)
            with self.subTest(path=path, field="sensitive"):
                self.assertEqual(ENGINE._sensitive(path), sensitive)


class TestModuleStrategies(unittest.TestCase):
    """Module-derivation strategies against synthetic layouts. The engine's
    third strategy (the nested-src-tree one) is deliberately absent here: its
    identifier trips this stack's language-token gate, and the other stacks'
    suites pin it."""

    def test_dir_strategy(self):
        _inject_layout(self, MODULE=[{"match": "src/**", "from": "dir"}])
        self.assertEqual(ENGINE._module_of("src/report/summary.py"), "src/report")

    def test_first_segment_after_strategy(self):
        _inject_layout(
            self, MODULE=[{"match": "packages/**", "from": "first-segment-after:packages/"}]
        )
        # The module id keeps its path prefix (so cross-stack changes read as
        # wider scatter), so the result is "packages/ui", not bare "ui".
        self.assertEqual(ENGINE._module_of("packages/ui/src/index.ts"), "packages/ui")

    def test_unmatched_path_yields_none(self):
        _inject_layout(self, MODULE=[{"match": "packages/**", "from": "dir"}])
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
            ENGINE._validate_module_rules([{"match": "x/**", "from": "dirr"}])

    def test_known_strategies_pass(self):
        # Accepted forms must survive validation unchanged; this pins the
        # validator to strategies _module_of implements (the nested-src-tree
        # strategy is pinned by the other stacks' suites — see class docstring).
        good = [
            {"match": "a/**", "from": "dir"},
            {"match": "c/**", "from": "first-segment-after:c/"},
        ]
        self.assertEqual(ENGINE._validate_module_rules(good), good)


class TestExcludePathspecs(unittest.TestCase):
    """exclude_globs becomes git exclude pathspecs applied to every diff the
    change set is read through (numstat, unified, name-only), so the reviewer's
    view through changeset.sh and the grader's row drop the same paths. An empty
    list yields no pathspec — the whole diff."""

    def test_empty_yields_no_pathspec(self):
        _inject_layout(self, EXCLUDE=[])
        self.assertEqual(ENGINE._exclude_pathspecs(), [])

    def test_globs_become_exclude_pathspecs(self):
        _inject_layout(self, EXCLUDE=["vendor/**", "gen/*.generated"])
        # Repo-root-relative (:(top)) so the change set is cwd-independent, with
        # glob magic so '**' crosses directories as layout.toml documents.
        self.assertEqual(
            ENGINE._exclude_pathspecs(),
            ["--", ":(top)",
             ":(top,glob,exclude)vendor/**", ":(top,glob,exclude)gen/*.generated"],
        )


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
    """The engine exposes the loaded layout as `layout` with five list-valued
    attributes, whatever values the project filled in. Value assertions stay
    out: the shipped layout.toml is a placeholder the project edits, and this
    suite must stay green after it does."""

    def setUp(self):
        # The layout global is loaded lazily; trigger the load so these tests
        # read a populated `layout` regardless of test ordering or isolation.
        ENGINE._get_layout()

    def test_five_attributes_are_lists(self):
        for attr in ("TEST", "PROD_ROOTS", "SENSITIVE", "EXCLUDE", "MODULE"):
            self.assertIsInstance(getattr(ENGINE.layout, attr), list, attr)


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
        _inject_layout(self, EXCLUDE=globs)
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


class TestReadHandoffReviewers(unittest.TestCase):
    """The reviewers row starts from the mandatory floor (always present, null
    when silent) and adds any other review-feedback author — a declared extra
    reviewer's verdict must never be dropped from the feature row."""

    def _read(self, records):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        log = tmp / "handoff.jsonl"
        log.write_text(
            "".join(json.dumps(r) + "\n" for r in records), encoding="utf-8"
        )
        saved = ENGINE.HANDOFF
        ENGINE.HANDOFF = log
        self.addCleanup(lambda: setattr(ENGINE, "HANDOFF", saved))
        return ENGINE._read_handoff("REQ-AB-001")

    def _feedback(self, author, verdict):
        return {"type": "review-feedback", "req_id": "REQ-AB-001",
                "author": author, "verdict": verdict}

    def test_extra_reviewer_verdict_enters_the_row(self):
        row = self._read([
            self._feedback("code-quality-reviewer", "approved"),
            self._feedback("perf-reviewer", "blocking"),
        ])
        self.assertEqual(row["reviewers"]["code-quality-reviewer"], "approved")
        self.assertEqual(row["reviewers"]["perf-reviewer"], "blocking")

    def test_floor_keys_present_and_null_when_silent(self):
        row = self._read([self._feedback("perf-reviewer", "approved")])
        for who in ENGINE._REVIEWERS:
            self.assertIn(who, row["reviewers"])
            self.assertIsNone(row["reviewers"][who])

    def test_last_verdict_per_author_wins(self):
        row = self._read([
            self._feedback("perf-reviewer", "blocking"),
            self._feedback("perf-reviewer", "approved"),
        ])
        self.assertEqual(row["reviewers"]["perf-reviewer"], "approved")


if __name__ == "__main__":
    unittest.main(verbosity=2)
