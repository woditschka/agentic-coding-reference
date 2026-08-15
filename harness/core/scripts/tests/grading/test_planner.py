"""Tests for grading.planner — the pure risk ladder.

Every class is stack-agnostic: each injects a synthetic layout and passes an
explicit review config, so the same blocks pin the engine identically in every
stack test file. The planner's two git-backed reads (the fix delta, a capped
basis's reviewed surface) are injected callables, so each case passes plain
fakes — no monkeypatching, no git fixture.

Run (from the scripts dir): python3 -m unittest tests.grading.test_planner
Stdlib only.
"""

import unittest
from types import SimpleNamespace

from grading import config, planner


class TestSurfaceRoster(unittest.TestCase):
    """Surface → roster mapping: a reviewer joins only for its surface; an
    extra named in the declared map is surface-scoped, an unmapped extra
    always joins (fail-closed)."""

    def setUp(self):
        self.cfg = {
            "docs": ["*.md"],
            "config": ["*.toml"],
            "size_threshold": 80,
            "mode": "risk",
            "surface_reviewers": {
                k: list(v) for k, v in config.SURFACE_REVIEWERS.items()
            },
        }
        self.roster = list(config.REVIEWERS)

    def test_surface_roster_docs_only(self):
        self.assertEqual(
            planner.surface_roster(["docs"], self.roster, self.cfg), ["doc-reviewer"]
        )

    def test_surface_roster_test_only(self):
        self.assertEqual(
            planner.surface_roster(["test"], self.roster, self.cfg),
            ["code-quality-reviewer", "test-reviewer"],
        )

    def test_surface_roster_config_only(self):
        self.assertEqual(
            planner.surface_roster(["config"], self.roster, self.cfg),
            ["code-quality-reviewer", "security-reviewer"],
        )

    def test_surface_roster_extras_always_join(self):
        roster = self.roster + ["perf-reviewer"]
        self.assertEqual(
            planner.surface_roster(["docs"], roster, self.cfg),
            ["doc-reviewer", "perf-reviewer"],
        )

    def test_surface_map_override_scopes_the_pass(self):
        cfg = dict(self.cfg)
        cfg["surface_reviewers"] = {
            **cfg["surface_reviewers"],
            "docs": ["doc-reviewer", "code-quality-reviewer"],
        }
        self.assertEqual(
            planner.surface_roster(["docs"], self.roster, cfg),
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
            planner.surface_roster(["docs"], roster, cfg),
            ["doc-reviewer", "style-reviewer"],
        )
        self.assertEqual(
            planner.surface_roster(["config"], roster, cfg),
            ["code-quality-reviewer", "security-reviewer"],
        )


class TestReviewPlanLadder(unittest.TestCase):
    """The risk-proportional review ladder — first-pass triggers and the
    fix-cycle delta re-review. The delta and reviewed-surface reads are the
    injected fakes `_derive` builds from each case's arguments."""

    def setUp(self):
        self._saved = config.layout
        config.layout = SimpleNamespace(
            TEST=["**/*_test.txt", "*_test.txt"],
            PROD_ROOTS=["src/"],
            SENSITIVE=["**/auth/**"],
            MODULE=[],
            REVIEW={},
            EXTRA_REVIEWERS=[],
        )
        self.addCleanup(lambda: setattr(config, "layout", self._saved))
        self.cfg = {
            "docs": ["*.md"],
            "config": ["*.toml"],
            "size_threshold": 80,
            "mode": "risk",
            "surface_reviewers": {
                k: list(v) for k, v in config.SURFACE_REVIEWERS.items()
            },
        }
        self.roster = list(config.REVIEWERS)

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

    def _derive(self, features, ctx=None, history=None, delta=None, tree_files=None):
        """Run derive_plan with fakes for the injected git reads: `delta` is
        what the delta reader returns, `tree_files` what the reviewed-surface
        recompute returns."""
        return planner.derive_plan(
            features,
            history or self._hist(),
            ctx or self._ctx(),
            self.roster,
            self.cfg,
            "tree1",
            lambda prev, cur, cfg: delta,
            lambda base, tree: tree_files,
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

    def test_test_only_oversize_defers_to_the_planner(self):
        # Excess entirely in test lines: gray, not a forced full battery —
        # the planner reads the diff and may still answer high.
        r = self._derive(self._features(["src/a.txt"], prod_lines=20, test_lines=69))
        self.assertEqual(r["risk"], "gray")
        self.assertEqual(r["triggers"], ["oversize"])
        self.assertIsNone(r["roster"])

    def test_prod_lines_at_threshold_with_test_push_over_is_gray(self):
        # Pins the <= boundary: prod exactly at the threshold, tests carrying
        # the total over, still defers.
        r = self._derive(self._features(["src/a.txt"], prod_lines=80, test_lines=10))
        self.assertEqual(r["risk"], "gray")
        self.assertEqual(r["triggers"], ["oversize"])

    def test_autofix_round_test_only_oversize_defers_too(self):
        # A dissenter-less fix pass is judged over slice features; the
        # test-only deferral applies on every pass that reads them.
        r = self._derive(
            self._features(["src/a.txt"], prod_lines=20, test_lines=69),
            ctx=self._ctx("fix"),
        )
        self.assertEqual(r["risk"], "gray")
        self.assertEqual(r["triggers"], ["oversize"])

    def test_test_only_oversize_with_a_second_trigger_stays_high(self):
        r = self._derive(
            self._features(
                ["src/auth/s.txt"],
                prod_lines=20,
                test_lines=69,
                sensitive=["src/auth/s.txt"],
            )
        )
        self.assertEqual(r["risk"], "high")
        self.assertIn("oversize", r["triggers"])
        self.assertIn("sensitive", r["triggers"])

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

    # --- fix-cycle delta re-review (delta injected per case) ---

    def test_fix_contained_reruns_dissenters_only(self):
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
            self._features(["c.toml"]),
            ctx=ctx,
            delta={
                "paths": ["c.toml"],
                "kinds": ["config"],
                "sensitive": False,
                "binary": False,
            },
        )
        self.assertEqual((r["risk"], r["scope"]), ("low", "fix-delta"))
        self.assertEqual(r["roster"], ["code-quality-reviewer"])

    def test_fix_escaped_surface_is_high_full_read(self):
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
            self._features(["c.toml", "src/new.txt"], prod_lines=2),
            ctx=ctx,
            delta={
                "paths": ["src/new.txt"],
                "kinds": ["prod"],
                "sensitive": False,
                "binary": False,
            },
        )
        self.assertEqual((r["risk"], r["scope"]), ("high", "full-diff"))
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("delta-escaped-surface", r["triggers"])

    def test_fix_docs_escape_widens_doc_reviewer(self):
        # A fix round routinely adds a PRD bullet or a design-doc note the
        # first pass never reviewed. That escape widens the pass with the
        # docs surface's reviewer — it does not re-run the full battery cold.
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["src/a.txt"],
            dissenters=["test-reviewer"],
            open_findings=[
                {
                    "reviewer": "test-reviewer",
                    "location": "src/a.txt:1",
                    "bar_clause": None,
                }
            ],
        )
        r = self._derive(
            self._features(["src/a.txt", "docs/prd.md"], prod_lines=2),
            ctx=ctx,
            delta={
                "paths": ["src/a.txt", "docs/prd.md"],
                "kinds": ["prod", "docs"],
                "sensitive": False,
                "binary": False,
            },
        )
        self.assertEqual((r["risk"], r["scope"]), ("low", "fix-delta"))
        self.assertEqual(r["roster"], ["test-reviewer", "doc-reviewer"])
        self.assertIn("unreviewed docs surface", r["rationale"])

    def test_fix_config_escape_widens_config_reviewers(self):
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["src/a.txt"],
            dissenters=["test-reviewer"],
            open_findings=[
                {
                    "reviewer": "test-reviewer",
                    "location": "src/a.txt:1",
                    "bar_clause": None,
                }
            ],
        )
        r = self._derive(
            self._features(["src/a.txt", "c.toml"], prod_lines=2),
            ctx=ctx,
            delta={
                "paths": ["c.toml"],
                "kinds": ["config"],
                "sensitive": False,
                "binary": False,
            },
        )
        self.assertEqual((r["risk"], r["scope"]), ("low", "fix-delta"))
        self.assertEqual(
            r["roster"],
            ["code-quality-reviewer", "test-reviewer", "security-reviewer"],
        )

    def test_fix_mixed_prod_docs_escape_is_high(self):
        # The surface widening covers docs/test/config escapes only: an escape
        # that also reaches production files keeps the fail-closed full read.
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["src/a.txt"],
            dissenters=["test-reviewer"],
            open_findings=[
                {
                    "reviewer": "test-reviewer",
                    "location": "src/a.txt:1",
                    "bar_clause": None,
                }
            ],
        )
        r = self._derive(
            self._features(["src/a.txt", "src/new.txt", "docs/prd.md"], prod_lines=4),
            ctx=ctx,
            delta={
                "paths": ["src/new.txt", "docs/prd.md"],
                "kinds": ["prod", "docs"],
                "sensitive": False,
                "binary": False,
            },
        )
        self.assertEqual((r["risk"], r["scope"]), ("high", "full-diff"))
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("delta-escaped-surface", r["triggers"])

    def test_fix_runtime_escape_is_high_despite_docs_kind(self):
        # The harness runtime classifies as docs/config by extension, but it
        # is trust surface: an escape into it never takes the widening.
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["src/a.txt"],
            dissenters=["test-reviewer"],
            open_findings=[
                {
                    "reviewer": "test-reviewer",
                    "location": "src/a.txt:1",
                    "bar_clause": None,
                }
            ],
        )
        r = self._derive(
            self._features(["src/a.txt", ".claude/skills/x/SKILL.md"], prod_lines=2),
            ctx=ctx,
            delta={
                "paths": [".claude/skills/x/SKILL.md"],
                "kinds": ["docs"],
                "sensitive": False,
                "binary": False,
            },
        )
        self.assertEqual((r["risk"], r["scope"]), ("high", "full-diff"))
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("delta-escaped-surface", r["triggers"])

    def test_fix_docs_escape_with_prior_critical_keeps_delta_scope(self):
        # A confined docs escape on a round following a critical finding:
        # the trigger takes the full roster, the scope stays the delta read
        # (never full-diff), and the surface widening does not leak.
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["src/a.txt"],
            dissenters=["test-reviewer"],
            critical_prior=True,
            open_findings=[
                {
                    "reviewer": "test-reviewer",
                    "location": "src/a.txt:1",
                    "bar_clause": None,
                }
            ],
        )
        r = self._derive(
            self._features(["src/a.txt", "docs/prd.md"], prod_lines=2),
            ctx=ctx,
            delta={
                "paths": ["src/a.txt", "docs/prd.md"],
                "kinds": ["prod", "docs"],
                "sensitive": False,
                "binary": False,
            },
        )
        self.assertEqual((r["risk"], r["scope"]), ("high", "fix-delta"))
        self.assertEqual(r["roster"], self.roster)
        self.assertEqual(r["triggers"], ["prior-critical"])

    def test_fix_bar_clause_widens_to_approved_reviewer(self):
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
        r = self._derive(
            self._features(["c.toml"]),
            ctx=ctx,
            delta={
                "paths": ["c.toml"],
                "kinds": ["config"],
                "sensitive": False,
                "binary": False,
            },
        )
        self.assertEqual(r["risk"], "low")
        self.assertEqual(r["roster"], ["code-quality-reviewer", "security-reviewer"])

    def test_fix_slice_triggers_do_not_escalate(self):
        # The slice is oversize, multi-module, and has noisy history — all
        # fired the full battery on the first pass. A contained, clean fix
        # delta stays dissenters-only: fix-round risk is sized over the delta,
        # never the accumulated slice or the slice's history.
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
            delta={
                "paths": ["src/a.txt"],
                "kinds": ["prod"],
                "sensitive": False,
                "binary": False,
                "lines": 4,
            },
        )
        self.assertEqual((r["risk"], r["scope"]), ("low", "fix-delta"))
        self.assertEqual(r["roster"], ["code-quality-reviewer"])

    def test_fix_delta_oversize_is_full_roster_delta_read(self):
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
            self._features(["src/a.txt"], prod_lines=100),
            ctx=ctx,
            delta={
                "paths": ["src/a.txt"],
                "kinds": ["prod"],
                "sensitive": False,
                "binary": False,
                "lines": 100,
            },
        )
        self.assertEqual((r["risk"], r["scope"]), ("high", "fix-delta"))
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("delta-oversize", r["triggers"])

    def test_fix_prior_critical_is_full_roster(self):
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
        r = self._derive(
            self._features(["c.toml"]),
            ctx=ctx,
            delta={
                "paths": ["c.toml"],
                "kinds": ["config"],
                "sensitive": False,
                "binary": False,
                "lines": 2,
            },
        )
        self.assertEqual((r["risk"], r["scope"]), ("high", "fix-delta"))
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("prior-critical", r["triggers"])

    def test_fix_delta_unavailable_fails_closed_to_full_read(self):
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
        r = self._derive(self._features(["c.toml"]), ctx=ctx, delta=None)
        self.assertEqual((r["risk"], r["scope"]), ("high", "full-diff"))
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("delta-unavailable", r["triggers"])

    def test_fix_sensitive_slice_retains_security_reviewer(self):
        # The slice touched sensitive paths; the fix delta is clean, contained,
        # and non-sensitive. The security reviewer stays aboard the fix round
        # anyway — a non-sensitive fix can still break behavior the sensitive
        # surface depends on.
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
            delta={
                "paths": ["src/m.txt"],
                "kinds": ["prod"],
                "sensitive": False,
                "binary": False,
                "lines": 3,
            },
        )
        self.assertEqual((r["risk"], r["scope"]), ("low", "fix-delta"))
        self.assertEqual(r["roster"], ["code-quality-reviewer", "security-reviewer"])

    def test_fix_dissenter_outside_roster_fails_closed(self):
        # A dissent recorded by an author no longer in the roster must not
        # yield a low plan with an empty roster ("nobody reviews").
        ctx = self._ctx(
            "fix",
            prev_tree_sha="t0",
            reviewed_files=["c.toml"],
            dissenters=["retired-extra-reviewer"],
            open_findings=[],
        )
        r = self._derive(
            self._features(["c.toml"]),
            ctx=ctx,
            delta={
                "paths": ["c.toml"],
                "kinds": ["config"],
                "sensitive": False,
                "binary": False,
                "lines": 2,
            },
        )
        self.assertEqual(r["risk"], "high")
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("no-dissenter-in-roster", r["triggers"])

    # --- capped basis: reviewed surface recomputed, never assumed empty ---

    def test_fix_capped_basis_recomputes_reviewed_surface(self):
        # A prior plan whose basis exceeded the cap stores files: null. The
        # reviewed surface is recomputed via the injected tree-files reader, so
        # a contained fix on a large slice stays dissenters-only instead of
        # false-firing escape.
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
        r = self._derive(
            self._features(["src/m.txt"], prod_lines=10),
            ctx=ctx,
            delta={
                "paths": ["src/m.txt"],
                "kinds": ["prod"],
                "sensitive": False,
                "binary": False,
                "lines": 3,
            },
            tree_files=["src/m.txt", "src/other.txt"],
        )
        self.assertEqual((r["risk"], r["scope"]), ("low", "fix-delta"))
        self.assertEqual(r["roster"], ["code-quality-reviewer"])

    def test_fix_capped_basis_unrecomputable_fails_closed(self):
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
        r = self._derive(
            self._features(["src/m.txt"], prod_lines=10),
            ctx=ctx,
            delta={
                "paths": ["src/m.txt"],
                "kinds": ["prod"],
                "sensitive": False,
                "binary": False,
                "lines": 3,
            },
            tree_files=None,
        )
        self.assertEqual((r["risk"], r["scope"]), ("high", "full-diff"))
        self.assertEqual(r["roster"], self.roster)
        self.assertIn("reviewed-surface-unavailable", r["triggers"])


class TestPlanContext(unittest.TestCase):
    """First vs fix detection from already-loaded log records — a pure fold,
    no log file involved."""

    def test_plan_context_first_pass(self):
        recs = [(1, {"type": "build-pass", "req_id": "R"})]
        ctx = planner.plan_context(recs)
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
        ctx = planner.plan_context(recs)
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
        ctx = planner.plan_context(recs)
        self.assertEqual(ctx["pass"], "fix")
        self.assertEqual(ctx["prev_tree_sha"], "T1")
        self.assertEqual(ctx["reviewed_files"], ["c.toml"])
        self.assertEqual(ctx["dissenters"], ["code-quality-reviewer"])
        self.assertTrue(ctx["critical_prior"])
        self.assertEqual(len(ctx["open_findings"]), 1)

    def test_plan_context_initial_design_block_is_not_a_reset(self):
        # A design-block without supersedes_record_at landing mid-slice (a
        # fix-round design record) keeps the review history: the next pass
        # stays a fix pass and the cycle's dissent survives (ADR 2026-08-07).
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
                            "tag": "autofix",
                            "location": "c.toml:1",
                            "severity": "fixable",
                        }
                    ],
                },
            ),
            (4, {"type": "design-block", "author": "system-design-expert"}),
            (5, {"type": "build-pass"}),
        ]
        ctx = planner.plan_context(recs)
        self.assertEqual(ctx["pass"], "fix")
        self.assertEqual(ctx["dissenters"], ["code-quality-reviewer"])
        self.assertEqual(ctx["prev_tree_sha"], "T1")

    def test_plan_context_superseding_design_block_resets(self):
        # A re-triage (supersedes_record_at set) starts a new cycle: the prior
        # plan and dissent are void, and the pass reads as first.
        recs = [
            (1, {"type": "design-block", "author": "system-design-expert"}),
            (2, {"type": "build-pass"}),
            (
                3,
                {
                    "type": "review-plan",
                    "author": "review-plan-engine",
                    "basis": {"tree_sha": "T1", "files": [{"path": "c.toml"}]},
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
                            "tag": "autofix",
                            "location": "c.toml:1",
                            "severity": "fixable",
                        }
                    ],
                },
            ),
            (
                5,
                {
                    "type": "design-block",
                    "author": "system-design-expert",
                    "supersedes_record_at": 1,
                },
            ),
            (6, {"type": "build-pass"}),
        ]
        ctx = planner.plan_context(recs)
        self.assertEqual(ctx["pass"], "first")
        self.assertEqual(ctx["dissenters"], [])

    def test_plan_context_forged_supersedes_is_not_a_reset(self):
        # Gate 2 validates the pointer only when the design-block is the
        # latest substantive record, so the boundary re-checks its shape: a
        # pointer at a non-design-block line must not void the cycle.
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
                            "tag": "autofix",
                            "location": "c.toml:1",
                            "severity": "fixable",
                        }
                    ],
                },
            ),
            (
                4,
                {
                    "type": "design-block",
                    "author": "system-design-expert",
                    "supersedes_record_at": 1,
                },
            ),
            (5, {"type": "build-pass"}),
        ]
        ctx = planner.plan_context(recs)
        self.assertEqual(ctx["pass"], "fix")
        self.assertEqual(ctx["dissenters"], ["code-quality-reviewer"])

    def test_plan_context_interrupted_round_keeps_dissent_and_basis(self):
        # A round interrupted before its reviews ran (a mid-slice prd-entry or
        # design record landed and a fresh build-pass followed) must not orphan
        # the earlier dissent, and the basis stays the tree that dissent
        # reviewed — the dissenter's re-read covers everything since it spoke.
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
                            "tag": "autofix",
                            "location": "c.toml:1",
                            "severity": "fixable",
                        }
                    ],
                },
            ),
            (4, {"type": "build-pass"}),
            (
                5,
                {
                    "type": "review-plan",
                    "author": "review-plan-engine",
                    "basis": {"tree_sha": "T2", "files": [{"path": "c.toml"}]},
                },
            ),
            (6, {"type": "build-pass"}),
        ]
        ctx = planner.plan_context(recs)
        self.assertEqual(ctx["pass"], "fix")
        self.assertEqual(ctx["dissenters"], ["code-quality-reviewer"])
        self.assertEqual(ctx["prev_tree_sha"], "T1")

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
        ctx = planner.plan_context(recs)
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
        ctx = planner.plan_context(recs)
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
        ctx = planner.plan_context(recs)
        self.assertFalse(ctx["critical_prior"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
