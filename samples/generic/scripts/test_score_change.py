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
    spec = importlib.util.spec_from_file_location(
        "score_change", _HERE / "score-change.py"
    )
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
        (
            "src/auth/session_test.py",
            "test",
            "src/auth",
            True,
        ),  # test wins, still sensitive
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
            self,
            MODULE=[{"match": "packages/**", "from": "first-segment-after:packages/"}],
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
            [
                "--",
                ":(top)",
                ":(top,glob,exclude)vendor/**",
                ":(top,glob,exclude)gen/*.generated",
            ],
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


class TestReviewConfigValidation(unittest.TestCase):
    """Malformed [review] / [harness] declarations fail loudly at load — no
    plan is appended, so route falls closed to the full battery — never a
    silently wrong roster."""

    def setUp(self):
        self._saved = ENGINE.layout
        self.addCleanup(lambda: setattr(ENGINE, "layout", self._saved))

    def _inject(self, review=None, extras=None):
        ENGINE.layout = SimpleNamespace(
            TEST=[],
            PROD_ROOTS=["src/"],
            SENSITIVE=[],
            EXCLUDE=[],
            MODULE=[],
            REVIEW=review or {},
            EXTRA_REVIEWERS=extras or [],
        )

    def test_defaults_pass_unchanged(self):
        self._inject()
        cfg = ENGINE._review_config()
        self.assertEqual(
            cfg["surface_reviewers"],
            {k: list(v) for k, v in ENGINE._SURFACE_REVIEWERS.items()},
        )

    def test_bad_size_threshold_raises(self):
        self._inject({"size_threshold": "80"})
        with self.assertRaises(ValueError):
            ENGINE._review_config()

    def test_bad_mode_raises(self):
        self._inject({"mode": "sometimes"})
        with self.assertRaises(ValueError):
            ENGINE._review_config()

    def test_unknown_surface_raises(self):
        self._inject({"surface_reviewers": {"binary": ["doc-reviewer"]}})
        with self.assertRaises(ValueError):
            ENGINE._review_config()

    def test_prod_surface_is_not_overridable(self):
        # A prod mapping would be dead config (production changes never take
        # the surface path) that still marks its extras "mapped" and silently
        # narrows their always-join — rejected loudly instead.
        self._inject({"surface_reviewers": {"prod": ["code-quality-reviewer"]}})
        with self.assertRaises(ValueError):
            ENGINE._review_config()

    def test_non_roster_map_target_raises(self):
        self._inject({"surface_reviewers": {"docs": ["stranger-reviewer"]}})
        with self.assertRaises(ValueError):
            ENGINE._review_config()

    def test_declared_extra_is_a_valid_map_target(self):
        self._inject(
            {"surface_reviewers": {"docs": ["doc-reviewer", "style-reviewer"]}},
            extras=["style-reviewer"],
        )
        cfg = ENGINE._review_config()
        self.assertEqual(
            cfg["surface_reviewers"]["docs"], ["doc-reviewer", "style-reviewer"]
        )

    def test_malformed_extras_raise(self):
        with self.assertRaises(ValueError):
            ENGINE._validate_reviewer_extras(["style-reviewer", 3])


class TestExcludeBehaviorEndToEnd(unittest.TestCase):
    """The exclude pathspecs actually drop matching files from a real git diff —
    the coverage a string-construction check misses. Guards against cwd-relativity
    and glob-semantics regressions in _exclude_pathspecs feeding real git."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir)

        def git(*a):
            subprocess.run(
                ["git", "-C", str(self.dir), *a],
                check=True,
                capture_output=True,
                text=True,
            )

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
            [
                "git",
                "-C",
                str(self.dir),
                "diff",
                "--name-only",
                "HEAD~1",
                "HEAD",
                *ENGINE._exclude_pathspecs(),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return out.split()

    def test_no_exclude_shows_all(self):
        self.assertEqual(
            sorted(self._names_with_exclude([])), ["keep.txt", "vendor/lib.txt"]
        )

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
        log.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        saved = ENGINE.HANDOFF
        ENGINE.HANDOFF = log
        self.addCleanup(lambda: setattr(ENGINE, "HANDOFF", saved))
        return ENGINE._read_handoff("REQ-AB-001")

    def _feedback(self, author, verdict):
        return {
            "type": "review-feedback",
            "req_id": "REQ-AB-001",
            "author": author,
            "verdict": verdict,
        }

    def test_extra_reviewer_verdict_enters_the_row(self):
        row = self._read(
            [
                self._feedback("code-quality-reviewer", "approved"),
                self._feedback("perf-reviewer", "blocking"),
            ]
        )
        self.assertEqual(row["reviewers"]["code-quality-reviewer"], "approved")
        self.assertEqual(row["reviewers"]["perf-reviewer"], "blocking")

    def test_floor_keys_present_and_null_when_silent(self):
        row = self._read([self._feedback("perf-reviewer", "approved")])
        for who in ENGINE._REVIEWERS:
            self.assertIn(who, row["reviewers"])
            self.assertIsNone(row["reviewers"][who])

    def test_last_verdict_per_author_wins(self):
        row = self._read(
            [
                self._feedback("perf-reviewer", "blocking"),
                self._feedback("perf-reviewer", "approved"),
            ]
        )
        self.assertEqual(row["reviewers"]["perf-reviewer"], "approved")


class TestReviewPlan(unittest.TestCase):
    """The risk-proportional review ladder. Stack-agnostic: every case injects a synthetic layout and passes
    an explicit review config, so the same block pins the engine identically in
    every stack test file. The git-touching delta read (_delta_features) is
    stubbed per test — the routing/containment logic is what these pin, not git."""

    def setUp(self):
        self._saved = ENGINE.layout
        ENGINE.layout = SimpleNamespace(
            TEST=["**/*_test.txt", "*_test.txt"],
            PROD_ROOTS=["src/"],
            SENSITIVE=["**/auth/**"],
            EXCLUDE=[],
            MODULE=[],
            REVIEW={},
            EXTRA_REVIEWERS=[],
        )
        self.addCleanup(lambda: setattr(ENGINE, "layout", self._saved))
        self.cfg = {
            "docs": ["*.md"],
            "config": ["*.toml"],
            "size_threshold": 80,
            "mode": "risk",
            "surface_reviewers": {
                k: list(v) for k, v in ENGINE._SURFACE_REVIEWERS.items()
            },
        }
        self.roster = list(ENGINE._REVIEWERS)

    def _features(
        self,
        paths,
        prod_lines=0,
        test_lines=0,
        sensitive=None,
        module_count=1,
        binary=0,
    ):
        sensitive = sensitive or []
        return {
            "files": [
                {"path": p, "module": None, "sensitive": p in sensitive} for p in paths
            ],
            "sensitive_paths": sensitive,
            "binary_files": binary,
            "module_count": module_count,
            "prod_lines": prod_lines,
            "test_lines": test_lines,
            "hunks": 1,
        }

    def _ctx(self, pass_="first", **over):
        ctx = {
            "pass": pass_,
            "prev_tree_sha": None,
            "reviewed_files": [],
            "dissenters": [],
            "open_findings": [],
            "critical_prior": False,
        }
        ctx.update(over)
        return ctx

    def _hist(self, **over):
        h = {"build_retries": 0, "design_revisions": 0, "consultations": 0}
        h.update(over)
        return h

    def _derive(self, features, ctx=None, history=None):
        return ENGINE._derive_plan(
            features,
            history or self._hist(),
            ctx or self._ctx(),
            self.roster,
            self.cfg,
            "tree1",
        )

    # --- review-kind classification (docs > test > config > prod > unknown) ---

    def test_review_kind_precedence(self):
        cases = [
            ("docs/x.md", "docs"),
            ("a_test.txt", "test"),
            ("c.toml", "config"),
            ("src/m.txt", "prod"),
            ("notes.dat", "unknown"),
            ("src/notes.md", "docs"),  # docs beats a production root
        ]
        for path, kind in cases:
            with self.subTest(path=path):
                self.assertEqual(ENGINE._review_kind(path, self.cfg), kind)

    # --- surface -> roster mapping (a reviewer joins only for its surface) ---

    def test_surface_roster_docs_only(self):
        self.assertEqual(
            ENGINE._surface_roster(["docs"], self.roster, self.cfg), ["doc-reviewer"]
        )

    def test_surface_roster_test_only(self):
        self.assertEqual(
            ENGINE._surface_roster(["test"], self.roster, self.cfg),
            ["code-quality-reviewer", "test-reviewer"],
        )

    def test_surface_roster_config_only(self):
        self.assertEqual(
            ENGINE._surface_roster(["config"], self.roster, self.cfg),
            ["code-quality-reviewer", "security-reviewer"],
        )

    def test_surface_roster_extras_always_join(self):
        roster = self.roster + ["perf-reviewer"]
        self.assertEqual(
            ENGINE._surface_roster(["docs"], roster, self.cfg),
            ["doc-reviewer", "perf-reviewer"],
        )

    def test_surface_map_override_scopes_the_pass(self):
        cfg = dict(self.cfg)
        cfg["surface_reviewers"] = {
            **cfg["surface_reviewers"],
            "docs": ["doc-reviewer", "code-quality-reviewer"],
        }
        self.assertEqual(
            ENGINE._surface_roster(["docs"], self.roster, cfg),
            ["code-quality-reviewer", "doc-reviewer"],
        )

    def test_mapped_extra_is_surface_scoped(self):
        # An extra named in the declared map joins only its surface; an
        # unmapped extra keeps the fail-closed always-join above.
        roster = self.roster + ["style-reviewer"]
        cfg = dict(self.cfg)
        cfg["surface_reviewers"] = {
            **cfg["surface_reviewers"],
            "docs": ["doc-reviewer", "style-reviewer"],
        }
        self.assertEqual(
            ENGINE._surface_roster(["docs"], roster, cfg),
            ["doc-reviewer", "style-reviewer"],
        )
        self.assertEqual(
            ENGINE._surface_roster(["config"], roster, cfg),
            ["code-quality-reviewer", "security-reviewer"],
        )

    # --- first-pass ladder ---

    def test_docs_only_is_low(self):
        r = self._derive(self._features(["docs/x.md"]))
        self.assertEqual((r["risk"], r["roster"]), ("low", ["doc-reviewer"]))
        self.assertEqual(r["scope"], "full-diff")

    def test_test_only_is_low(self):
        r = self._derive(self._features(["a_test.txt"], test_lines=10))
        self.assertEqual(r["risk"], "low")
        self.assertEqual(r["roster"], ["code-quality-reviewer", "test-reviewer"])

    def test_small_clean_prod_is_gray(self):
        r = self._derive(self._features(["src/m.txt"], prod_lines=5))
        self.assertEqual(r["risk"], "gray")
        self.assertIsNone(r["roster"])

    def test_sensitive_is_high(self):
        r = self._derive(
            self._features(
                ["src/auth/s.txt"], prod_lines=3, sensitive=["src/auth/s.txt"]
            )
        )
        self.assertEqual((r["risk"], r["roster"]), ("high", self.roster))
        self.assertIn("sensitive", r["triggers"])

    def test_unknown_surface_is_high(self):
        r = self._derive(self._features(["notes.dat"]))
        self.assertEqual(r["risk"], "high")
        self.assertIn("unknown-surface", r["triggers"])

    def test_multi_module_is_high(self):
        r = self._derive(self._features(["src/a.txt"], prod_lines=5, module_count=2))
        self.assertEqual(r["risk"], "high")
        self.assertIn("multi-module", r["triggers"])

    def test_oversize_is_high(self):
        r = self._derive(self._features(["src/a.txt"], prod_lines=100))
        self.assertEqual(r["risk"], "high")
        self.assertIn("oversize", r["triggers"])

    def test_noisy_history_is_high(self):
        r = self._derive(
            self._features(["docs/x.md"]), history=self._hist(build_retries=2)
        )
        self.assertEqual(r["risk"], "high")
        self.assertIn("build-retries", r["triggers"])

    def test_design_revision_is_high(self):
        r = self._derive(
            self._features(["docs/x.md"]), history=self._hist(design_revisions=1)
        )
        self.assertEqual(r["risk"], "high")
        self.assertIn("design-revision", r["triggers"])

    def test_null_features_fail_closed_to_high(self):
        feats = self._features(["src/a.txt"])
        feats["files"] = None
        r = self._derive(feats)
        self.assertEqual((r["risk"], r["roster"]), ("high", self.roster))
        self.assertIn("null-features", r["triggers"])

    # --- fix-cycle delta re-review (_delta_features stubbed) ---

    def _stub_delta(self, delta):
        saved = ENGINE._delta_features
        ENGINE._delta_features = lambda a, b, c: delta
        self.addCleanup(lambda: setattr(ENGINE, "_delta_features", saved))

    def test_fix_contained_reruns_dissenters_only(self):
        self._stub_delta(
            {
                "paths": ["c.toml"],
                "kinds": ["config"],
                "sensitive": False,
                "binary": False,
            }
        )
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["c.toml"],
            dissenters=["code-quality-reviewer"],
            open_findings=[
                {
                    "reviewer": "code-quality-reviewer",
                    "location": "c.toml:1",
                    "bar_clause": None,
                }
            ],
        )
        r = self._derive(self._features(["c.toml"]), ctx=ctx)
        self.assertEqual((r["risk"], r["scope"]), ("low", "fix-delta"))
        self.assertEqual(r["roster"], ["code-quality-reviewer"])

    def test_fix_escaped_surface_is_high_full_read(self):
        self._stub_delta(
            {
                "paths": ["src/new.txt"],
                "kinds": ["prod"],
                "sensitive": False,
                "binary": False,
            }
        )
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["c.toml"],
            dissenters=["code-quality-reviewer"],
            open_findings=[
                {
                    "reviewer": "code-quality-reviewer",
                    "location": "c.toml:1",
                    "bar_clause": None,
                }
            ],
        )
        r = self._derive(
            self._features(["c.toml", "src/new.txt"], prod_lines=2), ctx=ctx
        )
        self.assertEqual((r["risk"], r["scope"]), ("high", "full-diff"))
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("delta-escaped-surface", r["triggers"])

    def test_fix_bar_clause_widens_to_approved_reviewer(self):
        self._stub_delta(
            {
                "paths": ["c.toml"],
                "kinds": ["config"],
                "sensitive": False,
                "binary": False,
            }
        )
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["c.toml"],
            dissenters=["code-quality-reviewer"],
            open_findings=[
                {
                    "reviewer": "code-quality-reviewer",
                    "location": "c.toml:1",
                    "bar_clause": "secure-by-design",
                }
            ],
        )
        r = self._derive(self._features(["c.toml"]), ctx=ctx)
        self.assertEqual(r["risk"], "low")
        self.assertEqual(r["roster"], ["code-quality-reviewer", "security-reviewer"])

    def test_fix_slice_triggers_do_not_escalate(self):
        # The slice is oversize, multi-module, and has noisy history — all
        # fired the full battery on the first pass. A contained, clean fix
        # delta stays dissenters-only: fix-round risk is sized over the delta,
        # never the accumulated slice or the slice's history.
        self._stub_delta(
            {
                "paths": ["src/a.txt"],
                "kinds": ["prod"],
                "sensitive": False,
                "binary": False,
                "lines": 4,
            }
        )
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["src/a.txt"],
            dissenters=["code-quality-reviewer"],
            open_findings=[
                {
                    "reviewer": "code-quality-reviewer",
                    "location": "src/a.txt:1",
                    "bar_clause": None,
                }
            ],
        )
        r = self._derive(
            self._features(["src/a.txt"], prod_lines=200, module_count=3),
            ctx=ctx,
            history=self._hist(build_retries=2, design_revisions=1),
        )
        self.assertEqual((r["risk"], r["scope"]), ("low", "fix-delta"))
        self.assertEqual(r["roster"], ["code-quality-reviewer"])

    def test_fix_delta_oversize_is_full_roster_delta_read(self):
        self._stub_delta(
            {
                "paths": ["src/a.txt"],
                "kinds": ["prod"],
                "sensitive": False,
                "binary": False,
                "lines": 100,
            }
        )
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["src/a.txt"],
            dissenters=["code-quality-reviewer"],
            open_findings=[
                {
                    "reviewer": "code-quality-reviewer",
                    "location": "src/a.txt:1",
                    "bar_clause": None,
                }
            ],
        )
        r = self._derive(self._features(["src/a.txt"], prod_lines=100), ctx=ctx)
        self.assertEqual((r["risk"], r["scope"]), ("high", "fix-delta"))
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("delta-oversize", r["triggers"])

    def test_fix_prior_critical_is_full_roster(self):
        self._stub_delta(
            {
                "paths": ["c.toml"],
                "kinds": ["config"],
                "sensitive": False,
                "binary": False,
                "lines": 2,
            }
        )
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["c.toml"],
            dissenters=["code-quality-reviewer"],
            critical_prior=True,
            open_findings=[
                {
                    "reviewer": "code-quality-reviewer",
                    "location": "c.toml:1",
                    "bar_clause": None,
                    "severity": "critical",
                }
            ],
        )
        r = self._derive(self._features(["c.toml"]), ctx=ctx)
        self.assertEqual((r["risk"], r["scope"]), ("high", "fix-delta"))
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("prior-critical", r["triggers"])

    def test_fix_delta_unavailable_fails_closed_to_full_read(self):
        self._stub_delta(None)
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["c.toml"],
            dissenters=["code-quality-reviewer"],
            open_findings=[
                {
                    "reviewer": "code-quality-reviewer",
                    "location": "c.toml:1",
                    "bar_clause": None,
                }
            ],
        )
        r = self._derive(self._features(["c.toml"]), ctx=ctx)
        self.assertEqual((r["risk"], r["scope"]), ("high", "full-diff"))
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("delta-unavailable", r["triggers"])

    def test_fix_sensitive_slice_retains_security_reviewer(self):
        # The slice touched sensitive paths; the fix delta is clean, contained,
        # and non-sensitive. The security reviewer stays aboard the fix round
        # anyway — a non-sensitive fix can still break behavior the sensitive
        # surface depends on.
        self._stub_delta(
            {
                "paths": ["src/m.txt"],
                "kinds": ["prod"],
                "sensitive": False,
                "binary": False,
                "lines": 3,
            }
        )
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["src/m.txt", "src/auth/s.txt"],
            dissenters=["code-quality-reviewer"],
            open_findings=[
                {
                    "reviewer": "code-quality-reviewer",
                    "location": "src/m.txt:1",
                    "bar_clause": None,
                }
            ],
        )
        r = self._derive(
            self._features(
                ["src/m.txt", "src/auth/s.txt"],
                prod_lines=10,
                sensitive=["src/auth/s.txt"],
            ),
            ctx=ctx,
        )
        self.assertEqual((r["risk"], r["scope"]), ("low", "fix-delta"))
        self.assertEqual(r["roster"], ["code-quality-reviewer", "security-reviewer"])

    def test_fix_dissenter_outside_roster_fails_closed(self):
        # A dissent recorded by an author no longer in the roster must not
        # yield a low plan with an empty roster ("nobody reviews").
        self._stub_delta(
            {
                "paths": ["c.toml"],
                "kinds": ["config"],
                "sensitive": False,
                "binary": False,
                "lines": 2,
            }
        )
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["c.toml"],
            dissenters=["retired-extra-reviewer"],
            open_findings=[],
        )
        r = self._derive(self._features(["c.toml"]), ctx=ctx)
        self.assertEqual(r["risk"], "high")
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("no-dissenter-in-roster", r["triggers"])

    # --- capped basis: reviewed surface recomputed, never assumed empty ---

    def _stub_tree_files(self, files):
        saved = ENGINE._tree_files
        ENGINE._tree_files = lambda base, tree: files
        self.addCleanup(lambda: setattr(ENGINE, "_tree_files", saved))

    def test_fix_capped_basis_recomputes_reviewed_surface(self):
        # A prior plan whose basis exceeded _BASIS_FILE_CAP stores files: null.
        # The reviewed surface is recomputed from git, so a contained fix on a
        # large slice stays dissenters-only instead of false-firing escape.
        self._stub_delta(
            {
                "paths": ["src/m.txt"],
                "kinds": ["prod"],
                "sensitive": False,
                "binary": False,
                "lines": 3,
            }
        )
        self._stub_tree_files(["src/m.txt", "src/other.txt"])
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=None,
            dissenters=["code-quality-reviewer"],
            open_findings=[
                {
                    "reviewer": "code-quality-reviewer",
                    "location": "src/m.txt:1",
                    "bar_clause": None,
                }
            ],
        )
        r = self._derive(self._features(["src/m.txt"], prod_lines=10), ctx=ctx)
        self.assertEqual((r["risk"], r["scope"]), ("low", "fix-delta"))
        self.assertEqual(r["roster"], ["code-quality-reviewer"])

    def test_fix_capped_basis_unrecomputable_fails_closed(self):
        self._stub_delta(
            {
                "paths": ["src/m.txt"],
                "kinds": ["prod"],
                "sensitive": False,
                "binary": False,
                "lines": 3,
            }
        )
        self._stub_tree_files(None)
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=None,
            dissenters=["code-quality-reviewer"],
            open_findings=[
                {
                    "reviewer": "code-quality-reviewer",
                    "location": "src/m.txt:1",
                    "bar_clause": None,
                }
            ],
        )
        r = self._derive(self._features(["src/m.txt"], prod_lines=10), ctx=ctx)
        self.assertEqual((r["risk"], r["scope"]), ("high", "full-diff"))
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("reviewed-surface-unavailable", r["triggers"])

    # --- numstat parsing (_parse_numstat — pure, no git fixture) ---

    def test_parse_numstat_counts_prod_and_test_lines_only(self):
        # Size uses the first-pass metric (_classify_kind): src/app.toml is
        # "config" for roster matching but sits under a prod root, so its
        # lines count — the first pass would count them toward oversize too.
        out = ENGINE._parse_numstat(
            "3\t1\tsrc/m.txt\n2\t2\ta_test.txt\n40\t0\tdocs/x.md\n"
            "5\t0\tc.toml\n6\t0\tsrc/app.toml\n",
            self.cfg,
        )
        self.assertEqual(out["lines"], 14)
        self.assertEqual(
            out["paths"],
            ["src/m.txt", "a_test.txt", "docs/x.md", "c.toml", "src/app.toml"],
        )
        self.assertEqual(out["kinds"][-1], "config")
        self.assertFalse(out["binary"])

    def test_parse_numstat_binary_rows_flag_not_count(self):
        out = ENGINE._parse_numstat("-\t-\tsrc/blob.bin\n1\t0\tsrc/m.txt\n", self.cfg)
        self.assertTrue(out["binary"])
        self.assertEqual(out["lines"], 1)

    def test_parse_numstat_undocumented_shape_counts_nothing(self):
        # Non-numeric, non-dash columns: keep the path (containment still
        # judges it) but count no lines — never crash.
        out = ENGINE._parse_numstat("weird\t?\tsrc/m.txt\n2\t0\tsrc/n.txt\n", self.cfg)
        self.assertEqual(out["lines"], 2)
        self.assertEqual(out["paths"], ["src/m.txt", "src/n.txt"])

    # --- plan-context: first vs fix detection from the log ---

    def test_plan_context_first_pass(self):
        recs = [(1, {"type": "build-pass", "req_id": "R"})]
        ctx = ENGINE._plan_context(recs)
        self.assertEqual(ctx["pass"], "first")

    def test_plan_context_fix_pass_with_global_line_numbers(self):
        # Records carry global file line numbers, so an earlier slice in the
        # log shifts this slice's lines upward. The no-build-pass sentinel
        # must live in that domain: a record-count sentinel (len(records)+1)
        # sat below the slice's own lines and read a fix pass as a first
        # pass, dropping dissenters and prev_tree.
        recs = [
            (11, {"type": "design-block"}),
            (
                12,
                {
                    "type": "review-plan",
                    "author": "review-plan-engine",
                    "basis": {"tree_sha": "T1", "files": [{"path": "c.toml"}]},
                },
            ),
        ]
        ctx = ENGINE._plan_context(recs)
        self.assertEqual(ctx["pass"], "fix")
        self.assertEqual(ctx["prev_tree_sha"], "T1")

    def test_plan_context_fix_pass_reads_prior_round(self):
        recs = [
            (1, {"type": "build-pass"}),
            (
                2,
                {
                    "type": "review-plan",
                    "author": "review-plan-engine",
                    "basis": {"tree_sha": "T1", "files": [{"path": "c.toml"}]},
                },
            ),
            (
                3,
                {
                    "type": "review-feedback",
                    "author": "code-quality-reviewer",
                    "verdict": "changes_requested",
                    "findings": [
                        {
                            "location": "c.toml:1",
                            "bar_clause": "legible-cold",
                            "severity": "critical",
                        }
                    ],
                },
            ),
            (
                4,
                {
                    "type": "review-feedback",
                    "author": "security-reviewer",
                    "verdict": "approved",
                    "findings": [],
                },
            ),
            (5, {"type": "build-pass"}),
        ]
        ctx = ENGINE._plan_context(recs)
        self.assertEqual(ctx["pass"], "fix")
        self.assertEqual(ctx["prev_tree_sha"], "T1")
        self.assertEqual(ctx["reviewed_files"], ["c.toml"])
        self.assertEqual(ctx["dissenters"], ["code-quality-reviewer"])
        self.assertTrue(ctx["critical_prior"])
        self.assertEqual(len(ctx["open_findings"]), 1)

    def test_plan_context_blocked_without_severity_is_critical(self):
        # Gate 4 bounces a blocked finding that omits severity, but this
        # engine also runs over logs Gate 4 never validated — fail closed,
        # never narrow.
        recs = [
            (1, {"type": "build-pass"}),
            (
                2,
                {
                    "type": "review-plan",
                    "author": "review-plan-engine",
                    "basis": {"tree_sha": "T1", "files": [{"path": "c.toml"}]},
                },
            ),
            (
                3,
                {
                    "type": "review-feedback",
                    "author": "code-quality-reviewer",
                    "verdict": "blocked",
                    "findings": [{"tag": "blocked", "location": "c.toml:1"}],
                },
            ),
            (4, {"type": "build-pass"}),
        ]
        ctx = ENGINE._plan_context(recs)
        self.assertTrue(ctx["critical_prior"])

    def test_plan_context_latest_record_per_author_wins(self):
        # A reviewer re-appends after a Gate 4 bounce; the superseded record
        # must not keep the round wide (route's latest-per-reviewer rule).
        recs = [
            (1, {"type": "build-pass"}),
            (
                2,
                {
                    "type": "review-plan",
                    "author": "review-plan-engine",
                    "basis": {"tree_sha": "T1", "files": [{"path": "c.toml"}]},
                },
            ),
            (
                3,
                {
                    "type": "review-feedback",
                    "author": "code-quality-reviewer",
                    "verdict": "blocked",
                    "findings": [{"tag": "blocked", "location": "c.toml:1"}],
                },
            ),
            (
                4,
                {
                    "type": "review-feedback",
                    "author": "code-quality-reviewer",
                    "verdict": "changes_requested",
                    "findings": [
                        {
                            "tag": "blocked",
                            "location": "c.toml:1",
                            "severity": "fixable",
                        }
                    ],
                },
            ),
            (5, {"type": "build-pass"}),
        ]
        ctx = ENGINE._plan_context(recs)
        self.assertFalse(ctx["critical_prior"])
        self.assertEqual(ctx["dissenters"], ["code-quality-reviewer"])
        self.assertEqual(len(ctx["open_findings"]), 1)

    def test_plan_context_missing_severity_widens_only_blocked(self):
        # escalate/clarify findings halt or route elsewhere; a missing
        # severity there never widens the ladder.
        recs = [
            (1, {"type": "build-pass"}),
            (
                2,
                {
                    "type": "review-plan",
                    "author": "review-plan-engine",
                    "basis": {"tree_sha": "T1", "files": [{"path": "c.toml"}]},
                },
            ),
            (
                3,
                {
                    "type": "review-feedback",
                    "author": "code-quality-reviewer",
                    "verdict": "changes_requested",
                    "findings": [{"tag": "clarify", "location": "c.toml:1"}],
                },
            ),
            (4, {"type": "build-pass"}),
        ]
        ctx = ENGINE._plan_context(recs)
        self.assertFalse(ctx["critical_prior"])

    def test_read_handoff_surfaces_plan_roster(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        log = tmp / "handoff.jsonl"
        log.write_text(
            "".join(
                json.dumps(r) + "\n"
                for r in [
                    {
                        "type": "build-pass",
                        "req_id": "REQ-AB-001",
                        "author": "feature-implementer",
                    },
                    {
                        "type": "review-plan",
                        "req_id": "REQ-AB-001",
                        "author": "review-plan-engine",
                        "risk": "low",
                        "roster": ["doc-reviewer"],
                    },
                ]
            ),
            encoding="utf-8",
        )
        saved = ENGINE.HANDOFF
        ENGINE.HANDOFF = log
        self.addCleanup(lambda: setattr(ENGINE, "HANDOFF", saved))
        row = ENGINE._read_handoff("REQ-AB-001")
        self.assertEqual(row["review_roster"], ["doc-reviewer"])


class TestHandoffReadDegradation(unittest.TestCase):
    """The two log readers degrade, never raise (ADR 2026-07-17 strict-parsing
    hardening). Invalid UTF-8 reads like an unreadable log; a NaN, duplicate-key,
    or non-object line is skipped, matching handoff.py's parse definition."""

    REQ = "REQ-AB-001"

    def _bind(self, data):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        log = tmp / "handoff.jsonl"
        if isinstance(data, bytes):
            log.write_bytes(data)
        else:
            log.write_text(data, encoding="utf-8")
        saved = ENGINE.HANDOFF
        ENGINE.HANDOFF = log
        self.addCleanup(lambda: setattr(ENGINE, "HANDOFF", saved))

    def test_read_handoff_nulls_on_invalid_utf8(self):
        self._bind(b"\xff\xfe not utf-8\n")
        row = ENGINE._read_handoff(self.REQ)
        self.assertIsNone(row["build_passed"])
        self.assertIsNone(row["reviewers"])

    def test_load_records_empty_on_invalid_utf8(self):
        self._bind(b"\xff\xfe not utf-8\n")
        self.assertEqual(ENGINE._load_records(self.REQ), [])

    def test_duplicate_key_line_skipped_not_last_wins(self):
        # handoff.py rejects duplicate keys; plain json.loads would keep the last
        # value and include the line. The reader must skip it instead.
        self._bind(
            '{"req_id": "REQ-AB-001", "note": "a", "note": "b"}\n'
            '{"type": "build-pass", "req_id": "REQ-AB-001"}\n'
        )
        recs = ENGINE._load_records(self.REQ)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0][1].get("type"), "build-pass")

    def test_non_object_line_skipped_not_crash(self):
        # A bare JSON value (123) parses but is not a record; skip it rather
        # than call .get on an int.
        self._bind('123\n{"type": "build-pass", "req_id": "REQ-AB-001"}\n')
        recs = ENGINE._load_records(self.REQ)
        self.assertEqual([r.get("type") for _, r in recs], ["build-pass"])


if __name__ == "__main__":
    # The suite exercises the engine against the project's own layout.toml —
    # project-owned data no install payload can provide. A pre-init tree
    # (marketplace setup.sh runs before the scaffold) legitimately lacks it,
    # so skip loudly with a clean exit; every scaffolded project has one and
    # runs the suite in full.
    if not (Path(__file__).resolve().parent / "layout.toml").is_file():
        print(
            "scripts/layout.toml not scaffolded yet (run the harness init) "
            "— suite skipped"
        )
        raise SystemExit(0)
    unittest.main(verbosity=2)
