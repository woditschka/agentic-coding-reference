"""The pure risk ladder: the plan context, the surface roster, the first pass, and the fix cycle."""

import unittest
from dataclasses import replace

from grading.config import REVIEWERS, SURFACE_REVIEWERS, Layout, ReviewConfig
from grading.planner import (
    NOISY_RETRIES,
    GitReaders,
    OpenFinding,
    PlanContext,
    PlanInputs,
    cycle_start,
    derive_plan,
    placeable_path,
    plan_context,
    security_relevant,
    slice_triggers,
    surface_roster,
)

FLOOR = tuple(REVIEWERS)
CODE_REVIEWER, TEST_REVIEWER, SECURITY_REVIEWER, DOC_REVIEWER = FLOOR
EXTRA_REVIEWER = "perf-reviewer"
RETIRED_REVIEWER = "retired-extra-reviewer"
SOME_TREE = "tree1"
SOME_BASE = "base0"
SOME_PREV_TREE = "t0"
ANOTHER_PREV_TREE = "t1"
SOME_LINE = 1
SIZE_THRESHOLD = 80
SOME_LINES = 3
MANY_LINES = SIZE_THRESHOLD + 1
ONE_BINARY_FILE = 1
A_SECOND_MODULE = 2
A_DESIGN_REVISION = 1
A_NON_STRING = 7
A_LINE_AND_COLUMN = "12:3"
A_PROD_FILE = "src/a.txt"
ANOTHER_PROD_FILE = "src/new.txt"
A_SENSITIVE_FILE = "src/auth/s.txt"
A_SURFACE_FILE = "src/web/c.txt"
A_CONFIG_FILE = "c.toml"
A_DOC = "docs/prd.md"
A_TEST_FILE = "a_test.txt"
A_RUNTIME_FILE = ".claude/skills/x/SKILL.md"
AN_UNKNOWN_FILE = "notes.dat"
A_PROBE = r"@\w+Mapping\("
A_SECURITY_CLAUSE = "secure-by-design"
A_QUALITY_CLAUSE = "legible-cold"


def a_layout():
    return Layout(
        test_globs=("**/*_test.txt", "*_test.txt"),
        prod_roots=("src/",),
        sensitive=("**/auth/**",),
        module_rules=(),
        extra_reviewers=(),
        review={},
        conventions={},
    )


def located(path):
    """Return a finding location on the path at an irrelevant line."""
    return f"{path}:{SOME_LINE}"


def a_review_config(**over):
    review = ReviewConfig(
        docs=("*.md",),
        config=("*.toml",),
        size_threshold=SIZE_THRESHOLD,
        mode="risk",
        surface_reviewers=SURFACE_REVIEWERS,
        security_surface=(),
    )
    return replace(review, **over)


def a_history():
    return {"build_retries": 0, "design_revisions": 0, "consultations": 0}


def a_finding():
    return OpenFinding(CODE_REVIEWER, located(A_CONFIG_FILE), None, None, None)


def a_critical():
    return replace(a_finding(), severity="critical")


def a_fix_context():
    return PlanContext(
        "fix", SOME_PREV_TREE, (A_CONFIG_FILE,), (CODE_REVIEWER,), (a_finding(),)
    )


def features_of(paths, sensitive=(), **fields):
    return {
        "files": [
            {"path": p, "module": None, "sensitive": p in sensitive} for p in paths
        ],
        "sensitive_paths": list(sensitive),
        "binary_files": 0,
        "module_count": 1,
        "prod_lines": 0,
        "test_lines": 0,
        "hunks": 1,
        **fields,
    }


def a_delta(paths, kinds, **fields):
    return {
        "paths": paths,
        "kinds": kinds,
        "sensitive": False,
        "binary": False,
        "lines": SOME_LINES,
        **fields,
    }


def plan_inputs(features, **over):
    """The ladder's inputs with irrelevant defaults, and the fields a test cares about replaced."""
    defaults = PlanInputs(
        features,
        a_history(),
        PlanContext("first"),
        a_layout(),
        a_review_config(),
        SOME_TREE,
        SOME_BASE,
    )
    return replace(defaults, **over)


def derive(features, *, delta=None, tree_files=None, **inputs):
    """Run the ladder with fakes for the injected git reads."""
    readers = GitReaders(lambda _prev, _cur: delta, lambda _base, _tree: tree_files)
    return derive_plan(plan_inputs(features, **inputs), readers)


class SurfaceRoster(unittest.TestCase):
    def setUp(self):
        self.review = a_review_config()

    def test_a_docs_change_takes_the_doc_reviewer(self):
        self.assertEqual(surface_roster(["docs"], FLOOR, self.review), [DOC_REVIEWER])

    def test_an_unmapped_extra_always_joins(self):
        roster = [*FLOOR, EXTRA_REVIEWER]

        self.assertEqual(
            surface_roster(["docs"], roster, self.review),
            [DOC_REVIEWER, EXTRA_REVIEWER],
        )

    def test_a_declared_map_scopes_the_pass(self):
        review = a_review_config(
            surface_reviewers={"docs": (DOC_REVIEWER, CODE_REVIEWER)}
        )

        self.assertEqual(
            surface_roster(["docs"], FLOOR, review), [CODE_REVIEWER, DOC_REVIEWER]
        )

    def test_a_mapped_extra_is_surface_scoped(self):
        roster = [*FLOOR, EXTRA_REVIEWER]
        review = a_review_config(
            surface_reviewers={
                "docs": (DOC_REVIEWER,),
                "test": (TEST_REVIEWER, EXTRA_REVIEWER),
                "config": (CODE_REVIEWER,),
            }
        )

        self.assertEqual(surface_roster(["docs"], roster, review), [DOC_REVIEWER])
        self.assertEqual(
            surface_roster(["test"], roster, review), [TEST_REVIEWER, EXTRA_REVIEWER]
        )


class SliceTriggers(unittest.TestCase):
    def triggers(self, features, kinds=("prod",), history=None, context=None):
        inputs = PlanInputs(
            features,
            history or a_history(),
            context or PlanContext("first"),
            a_layout(),
            a_review_config(),
            SOME_TREE,
        )
        return slice_triggers(inputs, list(kinds))

    def test_a_clean_small_change_has_none(self):
        self.assertEqual(
            self.triggers(features_of([A_PROD_FILE], prod_lines=SOME_LINES)), []
        )

    def test_an_unknown_kind_is_a_trigger(self):
        triggers = self.triggers(features_of([AN_UNKNOWN_FILE]), kinds=("unknown",))

        self.assertEqual(triggers, ["unknown-surface"])

    def test_a_sensitive_path_is_a_trigger(self):
        features = features_of([A_SENSITIVE_FILE], sensitive=[A_SENSITIVE_FILE])

        self.assertEqual(self.triggers(features), ["sensitive"])

    def test_a_binary_file_is_a_trigger(self):
        self.assertEqual(
            self.triggers(features_of([A_PROD_FILE], binary_files=ONE_BINARY_FILE)),
            ["binary"],
        )

    def test_a_second_module_is_a_trigger(self):
        features = features_of([A_PROD_FILE], module_count=A_SECOND_MODULE)

        self.assertEqual(self.triggers(features), ["multi-module"])

    def test_lines_over_the_threshold_are_a_trigger(self):
        features = features_of(
            [A_PROD_FILE], prod_lines=SIZE_THRESHOLD, test_lines=SOME_LINES
        )

        self.assertEqual(self.triggers(features), ["oversize"])

    def test_lines_at_the_threshold_are_not(self):
        features = features_of([A_PROD_FILE], prod_lines=SIZE_THRESHOLD)

        self.assertEqual(self.triggers(features), [])

    def test_noisy_build_retries_are_a_trigger(self):
        history = {**a_history(), "build_retries": NOISY_RETRIES}

        self.assertEqual(
            self.triggers(features_of([A_PROD_FILE]), history=history),
            ["build-retries"],
        )

    def test_a_design_revision_is_a_trigger(self):
        history = {**a_history(), "design_revisions": A_DESIGN_REVISION}

        self.assertEqual(
            self.triggers(features_of([A_PROD_FILE]), history=history),
            ["design-revision"],
        )

    def test_a_prior_critical_is_a_trigger(self):
        context = PlanContext("first", open_findings=(a_critical(),))

        self.assertEqual(
            self.triggers(features_of([A_PROD_FILE]), context=context),
            ["prior-critical"],
        )

    def test_a_probe_hit_is_a_trigger(self):
        features = features_of([A_PROD_FILE], security_surface_paths=[A_PROD_FILE])

        self.assertEqual(self.triggers(features), ["security-surface"])

    def test_null_counts_read_as_zero(self):
        features = features_of(
            [A_PROD_FILE],
            prod_lines=None,
            test_lines=None,
            module_count=None,
            binary_files=None,
        )
        history = {**a_history(), "build_retries": None}

        self.assertEqual(self.triggers(features, history=history), [])


class FirstPassLadder(unittest.TestCase):
    def test_always_full_mode_is_the_full_battery_before_any_other_rung(self):
        plan = derive({"files": None}, review=a_review_config(mode="always-full"))

        self.assertEqual(
            (plan.risk, plan.roster, plan.scope), ("high", FLOOR, "full-diff")
        )
        self.assertEqual(plan.triggers, ("mode-always-full",))

    def test_a_docs_only_change_is_low_for_the_doc_reviewer(self):
        plan = derive(features_of([A_DOC]))

        self.assertEqual(
            (plan.risk, plan.roster, plan.scope), ("low", (DOC_REVIEWER,), "full-diff")
        )
        self.assertEqual(plan.triggers, ())

    def test_a_small_clean_production_change_is_gray(self):
        plan = derive(features_of([A_PROD_FILE], prod_lines=SOME_LINES))

        self.assertEqual((plan.risk, plan.roster), ("gray", None))
        self.assertIn("planner judges the roster", plan.rationale)

    def test_a_trigger_takes_the_full_battery(self):
        features = features_of(
            [A_SENSITIVE_FILE], prod_lines=SOME_LINES, sensitive=[A_SENSITIVE_FILE]
        )

        plan = derive(features)

        self.assertEqual(
            (plan.risk, plan.roster, plan.scope), ("high", FLOOR, "full-diff")
        )
        self.assertEqual(plan.triggers, ("sensitive",))
        self.assertIn("risk triggers present (sensitive)", plan.rationale)

    def test_an_oversize_carried_by_test_lines_alone_defers_to_the_planner(self):
        plan = derive(
            features_of([A_PROD_FILE], prod_lines=SOME_LINES, test_lines=MANY_LINES)
        )

        self.assertEqual((plan.risk, plan.roster), ("gray", None))
        self.assertEqual(plan.triggers, ("oversize",))

    def test_production_lines_at_the_threshold_still_defer(self):
        plan = derive(
            features_of([A_PROD_FILE], prod_lines=SIZE_THRESHOLD, test_lines=SOME_LINES)
        )

        self.assertEqual((plan.risk, plan.triggers), ("gray", ("oversize",)))

    def test_an_oversize_with_unknown_production_lines_stays_high(self):
        plan = derive(
            features_of([A_PROD_FILE], prod_lines=None, test_lines=MANY_LINES)
        )

        self.assertEqual((plan.risk, plan.triggers), ("high", ("oversize",)))

    def test_a_fix_pass_without_dissenters_is_judged_over_the_slice(self):
        plan = derive(
            features_of([A_PROD_FILE], prod_lines=SOME_LINES, test_lines=MANY_LINES),
            context=PlanContext("fix"),
        )

        self.assertEqual((plan.risk, plan.triggers), ("gray", ("oversize",)))

    def test_a_second_trigger_beside_the_test_oversize_stays_high(self):
        features = features_of(
            [A_SENSITIVE_FILE],
            prod_lines=SOME_LINES,
            test_lines=MANY_LINES,
            sensitive=[A_SENSITIVE_FILE],
        )

        plan = derive(features)

        self.assertEqual(plan.risk, "high")
        self.assertEqual(plan.triggers, ("sensitive", "oversize"))

    def test_null_features_fail_closed_to_the_full_battery(self):
        plan = derive({"files": None})

        self.assertEqual(
            (plan.risk, plan.roster, plan.triggers), ("high", FLOOR, ("null-features",))
        )

    def test_an_unresolved_tree_fails_closed_to_the_full_battery(self):
        plan = derive(features_of([A_PROD_FILE]), tree_sha=None)

        self.assertEqual((plan.risk, plan.triggers), ("high", ("null-features",)))

    def test_a_surface_no_reviewer_maps_to_fails_closed(self):
        review = a_review_config(
            surface_reviewers={"docs": (), "test": (), "config": ()}
        )

        plan = derive(features_of([A_DOC]), review=review)

        self.assertEqual(
            (plan.risk, plan.roster, plan.triggers),
            ("high", FLOOR, ("no-surface-match",)),
        )


class SecurityRelevance(unittest.TestCase):
    def setUp(self):
        self.review = a_review_config(security_surface=(A_PROBE,))
        self.features = features_of([A_PROD_FILE], security_surface_paths=[])

    def test_a_security_trigger_keeps_the_reviewer(self):
        self.assertTrue(
            security_relevant(["binary"], self.features, ["prod"], self.review)
        )

    def test_a_config_surface_keeps_the_reviewer(self):
        self.assertTrue(security_relevant([], self.features, ["config"], self.review))

    def test_an_empty_probe_keeps_the_reviewer(self):
        review = a_review_config(security_surface=())

        self.assertTrue(security_relevant([], self.features, ["prod"], review))

    def test_a_null_probe_result_keeps_the_reviewer(self):
        features = features_of([A_PROD_FILE], security_surface_paths=None)

        self.assertTrue(security_relevant([], features, ["prod"], self.review))

    def test_no_surface_at_all_releases_the_reviewer(self):
        self.assertFalse(
            security_relevant(["oversize"], self.features, ["prod"], self.review)
        )


class SecurityReviewerFollowsTheSurface(unittest.TestCase):
    def test_an_oversize_without_surface_drops_the_security_reviewer(self):
        features = features_of(
            [A_PROD_FILE], prod_lines=MANY_LINES, security_surface_paths=[]
        )

        plan = derive(features, review=a_review_config(security_surface=(A_PROBE,)))

        self.assertEqual(plan.risk, "high")
        self.assertNotIn(SECURITY_REVIEWER, plan.roster)
        self.assertIn("no security surface", plan.rationale)


class FixCycle(unittest.TestCase):
    def test_a_contained_fix_reruns_the_dissenters_only(self):
        plan = derive(
            features_of([A_CONFIG_FILE]),
            context=a_fix_context(),
            delta=a_delta([A_CONFIG_FILE], ["config"]),
        )

        self.assertEqual(
            (plan.risk, plan.scope, plan.roster), ("low", "fix-delta", (CODE_REVIEWER,))
        )
        self.assertIn("fix contained to reviewed surface", plan.rationale)

    def test_a_delta_at_the_size_threshold_stays_low(self):
        plan = derive(
            features_of([A_CONFIG_FILE]),
            context=a_fix_context(),
            delta=a_delta([A_CONFIG_FILE], ["config"], lines=SIZE_THRESHOLD),
        )

        self.assertEqual((plan.risk, plan.triggers), ("low", ()))

    def test_a_delta_on_an_open_finding_s_own_file_stays_contained(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_PROD_FILE,),
            open_findings=(replace(a_finding(), location=located(A_DOC)),),
        )

        plan = derive(
            features_of([A_PROD_FILE, A_DOC]),
            context=context,
            delta=a_delta([A_DOC], ["docs"]),
        )

        self.assertEqual((plan.risk, plan.roster), ("low", (CODE_REVIEWER,)))
        self.assertIn("fix contained to reviewed surface", plan.rationale)

    def test_an_escape_into_production_reads_cold_with_the_full_roster(self):
        plan = derive(
            features_of([A_CONFIG_FILE, ANOTHER_PROD_FILE], prod_lines=SOME_LINES),
            context=a_fix_context(),
            delta=a_delta([ANOTHER_PROD_FILE], ["prod"]),
        )

        self.assertEqual(
            (plan.risk, plan.scope, plan.roster), ("high", "full-diff", FLOOR)
        )
        self.assertIn("delta-escaped-surface", plan.triggers)

    def test_an_escape_into_docs_widens_the_pass_with_the_doc_reviewer(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_PROD_FILE,),
            dissenters=(TEST_REVIEWER,),
            open_findings=(
                replace(
                    a_finding(), reviewer=TEST_REVIEWER, location=located(A_PROD_FILE)
                ),
            ),
        )

        plan = derive(
            features_of([A_PROD_FILE, A_DOC], prod_lines=SOME_LINES),
            context=context,
            delta=a_delta([A_PROD_FILE, A_DOC], ["prod", "docs"]),
        )

        self.assertEqual((plan.risk, plan.scope), ("low", "fix-delta"))
        self.assertEqual(plan.roster, (TEST_REVIEWER, DOC_REVIEWER))
        self.assertIn("unreviewed docs surface", plan.rationale)

    def test_an_escape_reaching_production_beside_docs_reads_cold(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_PROD_FILE,),
            open_findings=(replace(a_finding(), location=located(A_PROD_FILE)),),
        )

        plan = derive(
            features_of([A_PROD_FILE, ANOTHER_PROD_FILE, A_DOC], prod_lines=SOME_LINES),
            context=context,
            delta=a_delta([ANOTHER_PROD_FILE, A_DOC], ["prod", "docs"]),
        )

        self.assertEqual(
            (plan.risk, plan.scope, plan.roster), ("high", "full-diff", FLOOR)
        )
        self.assertIn("delta-escaped-surface", plan.triggers)

    def test_an_escape_into_the_harness_runtime_reads_cold_despite_its_docs_kind(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_PROD_FILE,),
            open_findings=(replace(a_finding(), location=located(A_PROD_FILE)),),
        )

        plan = derive(
            features_of([A_PROD_FILE, A_RUNTIME_FILE], prod_lines=SOME_LINES),
            context=context,
            delta=a_delta([A_RUNTIME_FILE], ["docs"]),
        )

        self.assertEqual(
            (plan.risk, plan.scope, plan.roster), ("high", "full-diff", FLOOR)
        )
        self.assertIn("delta-escaped-surface", plan.triggers)

    def test_a_confined_escape_after_a_production_critical_keeps_the_delta_scope(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_PROD_FILE,),
            open_findings=(replace(a_critical(), location=located(A_PROD_FILE)),),
        )

        plan = derive(
            features_of([A_PROD_FILE, A_DOC], prod_lines=SOME_LINES),
            context=context,
            delta=a_delta([A_PROD_FILE, A_DOC], ["prod", "docs"]),
        )

        self.assertEqual(
            (plan.risk, plan.scope, plan.roster), ("high", "fix-delta", FLOOR)
        )
        self.assertEqual(plan.triggers, ("prior-critical",))

    def test_a_bar_clause_widens_to_the_implicated_reviewer(self):
        context = replace(
            a_fix_context(),
            open_findings=(replace(a_finding(), bar_clause=A_SECURITY_CLAUSE),),
        )

        plan = derive(
            features_of([A_CONFIG_FILE]),
            context=context,
            delta=a_delta([A_CONFIG_FILE], ["config"]),
        )

        self.assertEqual(
            (plan.risk, plan.roster), ("low", (CODE_REVIEWER, SECURITY_REVIEWER))
        )
        self.assertIn(f"widened for {SECURITY_REVIEWER}", plan.rationale)

    def test_slice_triggers_never_escalate_a_contained_fix(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_PROD_FILE,),
            open_findings=(replace(a_finding(), location=located(A_PROD_FILE)),),
        )
        history = {
            **a_history(),
            "build_retries": NOISY_RETRIES,
            "design_revisions": A_DESIGN_REVISION,
        }

        plan = derive(
            features_of(
                [A_PROD_FILE], prod_lines=MANY_LINES, module_count=A_SECOND_MODULE
            ),
            context=context,
            history=history,
            delta=a_delta([A_PROD_FILE], ["prod"]),
        )

        self.assertEqual(
            (plan.risk, plan.scope, plan.roster), ("low", "fix-delta", (CODE_REVIEWER,))
        )

    def test_an_oversize_delta_takes_the_full_roster_over_the_delta(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_PROD_FILE,),
            open_findings=(replace(a_finding(), location=located(A_PROD_FILE)),),
        )

        plan = derive(
            features_of([A_PROD_FILE], prod_lines=MANY_LINES),
            context=context,
            delta=a_delta([A_PROD_FILE], ["prod"], lines=MANY_LINES),
        )

        self.assertEqual(
            (plan.risk, plan.scope, plan.roster), ("high", "fix-delta", FLOOR)
        )
        self.assertIn("delta-oversize", plan.triggers)

    def test_a_sensitive_or_binary_delta_is_named_in_the_triggers(self):
        plan = derive(
            features_of([A_CONFIG_FILE]),
            context=a_fix_context(),
            delta=a_delta([A_CONFIG_FILE], ["config"], sensitive=True, binary=True),
        )

        self.assertEqual(plan.triggers, ("delta-sensitive", "delta-binary"))

    def test_an_unclassifiable_delta_is_named_in_the_triggers(self):
        plan = derive(
            features_of([A_CONFIG_FILE]),
            context=a_fix_context(),
            delta=a_delta([A_CONFIG_FILE], ["unknown"]),
        )

        self.assertEqual(plan.triggers, ("delta-unknown-surface",))

    def test_a_prior_critical_on_config_widens_to_its_surface(self):
        context = replace(a_fix_context(), open_findings=(a_critical(),))

        plan = derive(
            features_of([A_CONFIG_FILE]),
            context=context,
            delta=a_delta([A_CONFIG_FILE], ["config"]),
        )

        self.assertEqual((plan.risk, plan.scope), ("low", "fix-delta"))
        self.assertEqual(plan.roster, (CODE_REVIEWER, SECURITY_REVIEWER))
        self.assertEqual(plan.triggers, ())
        self.assertIn("prior critical on config surface", plan.rationale)

    def test_a_prior_critical_on_production_takes_the_full_roster(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_PROD_FILE,),
            open_findings=(replace(a_critical(), location=located(A_PROD_FILE)),),
        )

        plan = derive(
            features_of([A_PROD_FILE], prod_lines=SOME_LINES),
            context=context,
            delta=a_delta([A_PROD_FILE], ["prod"]),
        )

        self.assertEqual(
            (plan.risk, plan.scope, plan.roster), ("high", "fix-delta", FLOOR)
        )
        self.assertEqual(plan.triggers, ("prior-critical",))

    def test_a_prior_critical_in_the_harness_runtime_reads_cold(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_RUNTIME_FILE,),
            dissenters=(DOC_REVIEWER,),
            open_findings=(
                replace(
                    a_critical(),
                    reviewer=DOC_REVIEWER,
                    location=located(A_RUNTIME_FILE),
                ),
            ),
        )

        plan = derive(
            features_of([A_RUNTIME_FILE]),
            context=context,
            delta=a_delta([A_RUNTIME_FILE], ["docs"]),
        )

        self.assertEqual((plan.risk, plan.triggers), ("high", ("prior-critical",)))

    def test_a_critical_the_security_reviewer_raised_reads_cold_on_any_surface(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_DOC,),
            dissenters=(SECURITY_REVIEWER,),
            open_findings=(
                replace(
                    a_critical(), reviewer=SECURITY_REVIEWER, location=located(A_DOC)
                ),
            ),
        )

        plan = derive(
            features_of([A_DOC]), context=context, delta=a_delta([A_DOC], ["docs"])
        )

        self.assertEqual((plan.risk, plan.triggers), ("high", ("prior-critical",)))

    def test_a_critical_carrying_the_security_clause_reads_cold(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_DOC,),
            dissenters=(TEST_REVIEWER,),
            open_findings=(
                replace(
                    a_critical(),
                    reviewer=TEST_REVIEWER,
                    location=located(A_DOC),
                    bar_clause=A_SECURITY_CLAUSE,
                ),
            ),
        )

        plan = derive(
            features_of([A_DOC]), context=context, delta=a_delta([A_DOC], ["docs"])
        )

        self.assertEqual(plan.triggers, ("prior-critical",))

    def test_a_critical_keeps_its_raiser_even_off_the_dissent_list(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_DOC,),
            open_findings=(
                replace(a_critical(), reviewer=TEST_REVIEWER, location=located(A_DOC)),
            ),
        )

        plan = derive(
            features_of([A_DOC]), context=context, delta=a_delta([A_DOC], ["docs"])
        )

        self.assertEqual(plan.risk, "low")
        self.assertEqual(plan.roster, (CODE_REVIEWER, TEST_REVIEWER, DOC_REVIEWER))

    def test_a_docs_critical_with_a_production_fix_delta_reads_cold(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_DOC, A_PROD_FILE),
            dissenters=(DOC_REVIEWER,),
            open_findings=(
                replace(a_critical(), reviewer=DOC_REVIEWER, location=located(A_DOC)),
            ),
        )

        plan = derive(
            features_of([A_DOC, A_PROD_FILE], prod_lines=SOME_LINES),
            context=context,
            delta=a_delta([A_DOC, A_PROD_FILE], ["docs", "prod"]),
        )

        self.assertEqual((plan.risk, plan.triggers), ("high", ("prior-critical",)))

    def test_a_critical_with_an_unplaceable_location_reads_cold(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_DOC,),
            dissenters=(DOC_REVIEWER,),
            open_findings=(
                replace(
                    a_critical(),
                    reviewer=DOC_REVIEWER,
                    location=located(f"docs/../{A_PROD_FILE}"),
                ),
            ),
        )

        plan = derive(
            features_of([A_DOC]), context=context, delta=a_delta([A_DOC], ["docs"])
        )

        self.assertEqual(plan.triggers, ("prior-critical",))

    def test_an_unavailable_delta_fails_closed_to_the_full_read(self):
        plan = derive(features_of([A_CONFIG_FILE]), context=a_fix_context(), delta=None)

        self.assertEqual(
            (plan.risk, plan.scope, plan.roster), ("high", "full-diff", FLOOR)
        )
        self.assertIn("delta-unavailable", plan.triggers)

    def test_a_sensitive_slice_retains_the_security_reviewer(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_PROD_FILE, A_SENSITIVE_FILE),
            open_findings=(replace(a_finding(), location=located(A_PROD_FILE)),),
        )
        features = features_of(
            [A_PROD_FILE, A_SENSITIVE_FILE],
            prod_lines=SOME_LINES,
            sensitive=[A_SENSITIVE_FILE],
        )

        plan = derive(features, context=context, delta=a_delta([A_PROD_FILE], ["prod"]))

        self.assertEqual((plan.risk, plan.scope), ("low", "fix-delta"))
        self.assertEqual(plan.roster, (CODE_REVIEWER, SECURITY_REVIEWER))

    def test_a_delta_on_a_probe_hit_retains_the_security_reviewer(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_PROD_FILE, A_SURFACE_FILE),
            open_findings=(replace(a_finding(), location=located(A_SURFACE_FILE)),),
        )
        features = features_of(
            [A_PROD_FILE, A_SURFACE_FILE],
            prod_lines=SOME_LINES,
            security_surface_paths=[A_SURFACE_FILE],
        )

        plan = derive(
            features, context=context, delta=a_delta([A_SURFACE_FILE], ["prod"])
        )

        self.assertEqual((plan.risk, plan.scope), ("low", "fix-delta"))
        self.assertEqual(plan.roster, (CODE_REVIEWER, SECURITY_REVIEWER))

    def test_a_delta_off_the_probe_hits_leaves_the_security_reviewer_out(self):
        context = replace(
            a_fix_context(),
            reviewed_files=(A_PROD_FILE, A_SURFACE_FILE),
            open_findings=(replace(a_finding(), location=located(A_PROD_FILE)),),
        )
        features = features_of(
            [A_PROD_FILE, A_SURFACE_FILE],
            prod_lines=SOME_LINES,
            security_surface_paths=[A_SURFACE_FILE],
        )

        plan = derive(features, context=context, delta=a_delta([A_PROD_FILE], ["prod"]))

        self.assertEqual(
            (plan.risk, plan.scope, plan.roster), ("low", "fix-delta", (CODE_REVIEWER,))
        )

    def test_a_dissenter_outside_the_roster_fails_closed(self):
        context = replace(
            a_fix_context(), dissenters=(RETIRED_REVIEWER,), open_findings=()
        )

        plan = derive(
            features_of([A_CONFIG_FILE]),
            context=context,
            delta=a_delta([A_CONFIG_FILE], ["config"]),
        )

        self.assertEqual((plan.risk, plan.roster), ("high", FLOOR))
        self.assertEqual(plan.triggers, ("no-dissenter-in-roster",))

    def test_a_capped_basis_recomputes_the_reviewed_surface(self):
        context = replace(
            a_fix_context(),
            reviewed_files=None,
            open_findings=(replace(a_finding(), location=located(A_PROD_FILE)),),
        )

        plan = derive(
            features_of([A_PROD_FILE], prod_lines=SOME_LINES),
            context=context,
            delta=a_delta([A_PROD_FILE], ["prod"]),
            tree_files=[A_PROD_FILE, ANOTHER_PROD_FILE],
        )

        self.assertEqual(
            (plan.risk, plan.scope, plan.roster), ("low", "fix-delta", (CODE_REVIEWER,))
        )

    def test_a_capped_basis_that_cannot_be_recomputed_fails_closed(self):
        context = replace(
            a_fix_context(),
            reviewed_files=None,
            open_findings=(replace(a_finding(), location=located(A_PROD_FILE)),),
        )

        plan = derive(
            features_of([A_PROD_FILE], prod_lines=SOME_LINES),
            context=context,
            delta=a_delta([A_PROD_FILE], ["prod"]),
            tree_files=None,
        )

        self.assertEqual(
            (plan.risk, plan.scope, plan.roster), ("high", "full-diff", FLOOR)
        )
        self.assertIn("reviewed-surface-unavailable", plan.triggers)

    def test_the_open_findings_ride_the_plan(self):
        finding = a_finding()

        plan = derive(
            features_of([A_CONFIG_FILE]),
            context=replace(a_fix_context(), open_findings=(finding,)),
            delta=a_delta([A_CONFIG_FILE], ["config"]),
        )

        self.assertEqual(plan.open_findings, (finding,))


def a_review_plan(no, tree_sha=SOME_PREV_TREE, files=({"path": A_CONFIG_FILE},)):
    basis = {"tree_sha": tree_sha, "files": None if files is None else list(files)}
    return (no, {"type": "review-plan", "author": "review-plan-engine", "basis": basis})


def a_feedback(no, author=CODE_REVIEWER, verdict="changes_requested", findings=()):
    return (
        no,
        {
            "type": "review-feedback",
            "author": author,
            "verdict": verdict,
            "findings": list(findings),
        },
    )


def a_build_pass(no):
    return (no, {"type": "build-pass"})


def a_design_block(no, **fields):
    return (no, {"type": "design-block", "author": "system-design-expert", **fields})


A_RAW_FINDING = {
    "tag": "autofix",
    "location": located(A_CONFIG_FILE),
    "severity": "fixable",
}


class PlanContextFold(unittest.TestCase):
    def test_no_prior_plan_is_a_first_pass(self):
        self.assertEqual(plan_context([a_build_pass(1)]), PlanContext("first"))

    def test_the_sentinel_lives_in_the_global_line_domain(self):
        context = plan_context([a_design_block(11), a_review_plan(12)])

        self.assertEqual(
            (context.pass_, context.prev_tree_sha), ("fix", SOME_PREV_TREE)
        )

    def test_a_prior_round_is_read_into_the_context(self):
        critical = {
            "location": located(A_CONFIG_FILE),
            "bar_clause": A_QUALITY_CLAUSE,
            "severity": "critical",
        }
        records = [
            a_build_pass(1),
            a_review_plan(2),
            a_feedback(3, findings=[critical]),
            a_feedback(4, author=SECURITY_REVIEWER, verdict="approved"),
            a_build_pass(5),
        ]

        context = plan_context(records)

        self.assertEqual(
            context,
            PlanContext(
                "fix",
                SOME_PREV_TREE,
                (A_CONFIG_FILE,),
                (CODE_REVIEWER,),
                (
                    OpenFinding(
                        CODE_REVIEWER,
                        located(A_CONFIG_FILE),
                        None,
                        A_QUALITY_CLAUSE,
                        "critical",
                    ),
                ),
            ),
        )
        self.assertTrue(context.critical_prior)

    def test_an_initial_design_block_mid_slice_keeps_the_cycle(self):
        records = [
            a_build_pass(1),
            a_review_plan(2),
            a_feedback(3, findings=[A_RAW_FINDING]),
            a_design_block(4),
            a_build_pass(5),
        ]

        context = plan_context(records)

        self.assertEqual(
            (context.pass_, context.dissenters, context.prev_tree_sha),
            ("fix", (CODE_REVIEWER,), SOME_PREV_TREE),
        )

    def test_a_superseding_design_block_starts_a_new_cycle(self):
        records = [
            a_design_block(1),
            a_build_pass(2),
            a_review_plan(3),
            a_feedback(4, findings=[A_RAW_FINDING]),
            a_design_block(5, supersedes_record_at=1),
            a_build_pass(6),
        ]

        self.assertEqual(plan_context(records), PlanContext("first"))

    def test_an_interrupted_round_keeps_the_dissent_and_its_basis(self):
        records = [
            a_build_pass(1),
            a_review_plan(2),
            a_feedback(3, findings=[A_RAW_FINDING]),
            a_build_pass(4),
            a_review_plan(5, tree_sha=ANOTHER_PREV_TREE),
            a_build_pass(6),
        ]

        context = plan_context(records)

        self.assertEqual(
            (context.pass_, context.dissenters, context.prev_tree_sha),
            ("fix", (CODE_REVIEWER,), SOME_PREV_TREE),
        )

    def test_the_latest_record_per_author_wins(self):
        blocked = {"tag": "blocked", "location": located(A_CONFIG_FILE)}
        fixable = {**blocked, "severity": "fixable"}
        records = [
            a_build_pass(1),
            a_review_plan(2),
            a_feedback(3, verdict="blocked", findings=[blocked]),
            a_feedback(4, findings=[fixable]),
            a_build_pass(5),
        ]

        context = plan_context(records)

        self.assertFalse(context.critical_prior)
        self.assertEqual(context.dissenters, (CODE_REVIEWER,))
        self.assertEqual(len(context.open_findings), 1)

    def test_a_capped_basis_leaves_the_reviewed_surface_unknown(self):
        records = [a_build_pass(1), a_review_plan(2, files=None), a_build_pass(3)]

        self.assertIsNone(plan_context(records).reviewed_files)

    def test_a_non_object_finding_is_dropped(self):
        records = [
            a_build_pass(1),
            a_review_plan(2),
            a_feedback(3, findings=["not an object", A_RAW_FINDING]),
            a_build_pass(4),
        ]

        self.assertEqual(len(plan_context(records).open_findings), 1)


class CycleStart(unittest.TestCase):
    def test_no_superseding_block_starts_at_zero(self):
        self.assertEqual(cycle_start([a_design_block(1), a_build_pass(2)]), 0)

    def test_a_valid_pointer_starts_the_cycle_at_its_line(self):
        records = [a_design_block(1), a_design_block(3, supersedes_record_at=1)]

        self.assertEqual(cycle_start(records), 3)

    def test_a_boolean_pointer_is_ignored(self):
        records = [a_design_block(1), a_design_block(3, supersedes_record_at=True)]

        self.assertEqual(cycle_start(records), 0)

    def test_a_forward_pointer_is_ignored(self):
        records = [a_design_block(1, supersedes_record_at=3), a_design_block(3)]

        self.assertEqual(cycle_start(records), 0)

    def test_a_pointer_at_a_non_design_line_is_ignored(self):
        records = [a_build_pass(1), a_design_block(3, supersedes_record_at=1)]

        self.assertEqual(cycle_start(records), 0)


class OpenFindings(unittest.TestCase):
    def test_a_critical_severity_is_critical(self):
        self.assertTrue(a_critical().critical)

    def test_a_blocked_finding_without_a_severity_fails_closed_to_critical(self):
        self.assertTrue(replace(a_finding(), tag="blocked").critical)

    def test_a_blocked_finding_with_a_lesser_severity_is_not(self):
        self.assertFalse(
            replace(a_finding(), tag="blocked", severity="fixable").critical
        )

    def test_a_channel_finding_without_a_severity_is_not(self):
        self.assertFalse(replace(a_finding(), tag="clarify").critical)

    def test_the_path_is_the_text_before_the_first_colon(self):
        self.assertEqual(
            replace(a_finding(), location=f"{A_DOC}:{A_LINE_AND_COLUMN}").path, A_DOC
        )

    def test_a_non_string_location_has_no_path(self):
        self.assertIsNone(replace(a_finding(), location=None).path)

    def test_a_mapped_clause_implicates_its_reviewer(self):
        finding = replace(a_finding(), bar_clause=A_SECURITY_CLAUSE)

        self.assertEqual(finding.implicated_reviewer, SECURITY_REVIEWER)

    def test_an_unknown_clause_implicates_nobody(self):
        self.assertIsNone(replace(a_finding(), bar_clause="bogus").implicated_reviewer)

    def test_a_non_string_clause_implicates_nobody(self):
        self.assertIsNone(
            replace(a_finding(), bar_clause=A_NON_STRING).implicated_reviewer
        )

    def test_the_record_form_carries_every_field(self):
        self.assertEqual(
            replace(a_finding(), bar_clause=A_QUALITY_CLAUSE).as_dict(),
            {
                "reviewer": CODE_REVIEWER,
                "location": located(A_CONFIG_FILE),
                "tag": None,
                "bar_clause": A_QUALITY_CLAUSE,
                "severity": None,
            },
        )


class PlaceablePath(unittest.TestCase):
    def test_a_normalized_relative_path_is_placeable(self):
        self.assertEqual(placeable_path(located(A_DOC)), A_DOC)

    def test_a_traversal_is_not(self):
        self.assertIsNone(placeable_path(located(f"docs/../{A_PROD_FILE}")))

    def test_a_parent_prefix_is_not(self):
        self.assertIsNone(placeable_path(located(f"../{A_PROD_FILE}")))

    def test_a_leading_slash_is_not(self):
        self.assertIsNone(placeable_path(located(f"/{A_DOC}")))

    def test_whitespace_is_not(self):
        self.assertIsNone(
            placeable_path(f"{located(A_DOC)} and {located(A_PROD_FILE)}")
        )

    def test_a_backslash_is_not(self):
        self.assertIsNone(placeable_path(located("docs\\prd.md")))

    def test_a_non_string_is_not(self):
        self.assertIsNone(placeable_path(A_NON_STRING))


if __name__ == "__main__":
    unittest.main()
