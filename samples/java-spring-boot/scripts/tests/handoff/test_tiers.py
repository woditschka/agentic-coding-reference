#!/usr/bin/env python3
"""The effort ladder: the tier the next implementer dispatch runs, and the tier each window ran."""

import unittest

from handoff import (
    ALL_AUTOFIX_REASON,
    IMPLEMENTER,
    MIXED_REASON,
    RETIRED_REASON,
    ROUTINE_IMPLEMENTER,
    UNRATED_REASON,
    TierChoice,
    implementer_tier,
    window_tiers,
)

from tests.support import a_record, entries

REVIEWER = "code-quality-reviewer"
A_CODE_AUTOFIX = {
    "tag": "autofix",
    "location": "src/widget.py:1",
    "description": "d",
    "severity": "minor",
}
A_DOC_AUTOFIX = {**A_CODE_AUTOFIX, "location": "docs/prd.md:3"}
A_CODE_BLOCKER = {**A_CODE_AUTOFIX, "tag": "blocked"}
AN_ESCALATION = {**A_CODE_AUTOFIX, "tag": "escalate"}
A_CHECKPOINT = {**A_CODE_AUTOFIX, "tag": "truncation"}


def a_rated_design(effort="routine", **fields):
    return a_record(
        "design-block", verdict="covered", implementation_effort=effort, **fields
    )


def an_unrated_design():
    return a_record("design-block", verdict="covered")


def an_implementer_start():
    return a_record("dispatch-start", author=IMPLEMENTER)


def a_build_pass():
    return a_record("build-pass")


def a_build_failure():
    return a_record("build-failure")


def a_dissent(*findings):
    return a_record(
        "review-feedback",
        author=REVIEWER,
        verdict="changes_requested",
        findings=list(findings),
    )


def an_approval(*findings):
    return a_record(
        "review-feedback", author=REVIEWER, verdict="approved", findings=list(findings)
    )


def tier_of(*raws):
    return implementer_tier(entries(*raws))


class ImplementerTier(unittest.TestCase):
    def test_no_records_is_unrated(self):
        self.assertEqual(tier_of(), TierChoice(IMPLEMENTER, UNRATED_REASON))

    def test_an_unrated_design_never_activates_the_ladder(self):
        log = (
            an_unrated_design(),
            an_implementer_start(),
            a_build_pass(),
            a_dissent(A_CODE_AUTOFIX),
        )

        self.assertEqual(tier_of(*log), TierChoice(IMPLEMENTER, UNRATED_REASON))

    def test_a_rated_first_dispatch_runs_the_base(self):
        self.assertEqual(
            tier_of(a_rated_design("routine")), TierChoice(IMPLEMENTER, "initial")
        )

    def test_a_reviewed_pass_without_dissent_names_its_state(self):
        log = (a_rated_design(), an_implementer_start(), a_build_pass(), an_approval())

        self.assertEqual(
            tier_of(*log), TierChoice(IMPLEMENTER, "no-substantive-dissent")
        )

    def test_a_truncation_only_dissent_is_not_a_fix_round(self):
        log = (
            a_rated_design(),
            an_implementer_start(),
            a_build_pass(),
            a_dissent(A_CHECKPOINT),
        )

        self.assertEqual(
            tier_of(*log), TierChoice(IMPLEMENTER, "no-substantive-dissent")
        )

    def test_a_build_failure_reads_as_recovery(self):
        log = (a_rated_design(), an_implementer_start(), a_build_failure())

        self.assertEqual(tier_of(*log), TierChoice(IMPLEMENTER, "recovery"))

    def test_an_all_autofix_round_runs_the_routine_variant(self):
        log = (
            a_rated_design(),
            an_implementer_start(),
            a_build_pass(),
            a_dissent(A_CODE_AUTOFIX, A_DOC_AUTOFIX),
        )

        self.assertEqual(
            tier_of(*log), TierChoice(ROUTINE_IMPLEMENTER, ALL_AUTOFIX_REASON)
        )

    def test_a_round_with_a_code_blocker_is_mixed(self):
        log = (
            a_rated_design(),
            an_implementer_start(),
            a_build_pass(),
            a_dissent(A_CODE_BLOCKER),
        )

        self.assertEqual(tier_of(*log), TierChoice(IMPLEMENTER, MIXED_REASON))

    def test_an_escalate_finding_forces_the_base_even_on_an_approval(self):
        log = (
            a_rated_design(),
            an_implementer_start(),
            a_build_pass(),
            an_approval(AN_ESCALATION),
            a_dissent(A_CODE_AUTOFIX),
        )

        self.assertEqual(tier_of(*log), TierChoice(IMPLEMENTER, MIXED_REASON))

    def test_a_dissent_without_findings_is_mixed(self):
        log = (a_rated_design(), an_implementer_start(), a_build_pass(), a_dissent())

        self.assertEqual(tier_of(*log), TierChoice(IMPLEMENTER, MIXED_REASON))

    def test_a_record_that_lost_findings_in_the_lift_is_mixed(self):
        dissent = a_dissent(A_CODE_AUTOFIX)
        dissent["findings"].append("not an object")
        log = (a_rated_design(), an_implementer_start(), a_build_pass(), dissent)

        self.assertEqual(tier_of(*log), TierChoice(IMPLEMENTER, MIXED_REASON))

    def test_a_dissent_after_a_routine_window_retires_routine(self):
        log = (
            a_rated_design(),
            an_implementer_start(),
            a_build_pass(),
            a_dissent(A_CODE_AUTOFIX),
            an_implementer_start(),
            a_build_pass(),
            a_dissent(A_CODE_AUTOFIX),
        )

        self.assertEqual(tier_of(*log), TierChoice(IMPLEMENTER, RETIRED_REASON))

    def test_a_build_failure_in_a_routine_window_retires_routine(self):
        log = (
            a_rated_design(),
            an_implementer_start(),
            a_build_pass(),
            a_dissent(A_CODE_AUTOFIX),
            an_implementer_start(),
            a_build_failure(),
        )

        self.assertEqual(tier_of(*log), TierChoice(IMPLEMENTER, RETIRED_REASON))

    def test_a_failure_in_an_unattributed_window_retires_routine(self):
        log = (a_rated_design(), a_build_failure())

        self.assertEqual(tier_of(*log), TierChoice(IMPLEMENTER, RETIRED_REASON))

    def test_a_dissent_after_an_unattributed_window_retires_routine(self):
        log = (a_rated_design(), a_build_pass(), a_dissent(A_CODE_AUTOFIX))

        self.assertEqual(tier_of(*log), TierChoice(IMPLEMENTER, RETIRED_REASON))

    def test_retirement_survives_a_re_triage(self):
        log = (
            a_rated_design(),
            an_implementer_start(),
            a_build_pass(),
            a_dissent(A_CODE_AUTOFIX),
            an_implementer_start(),
            a_build_failure(),
            a_rated_design(supersedes_record_at=1),
        )

        self.assertEqual(tier_of(*log), TierChoice(IMPLEMENTER, RETIRED_REASON))

    def test_a_re_triage_resets_the_mode_to_fresh(self):
        log = (
            a_rated_design(),
            an_implementer_start(),
            a_build_pass(),
            a_dissent(A_CODE_BLOCKER),
            a_rated_design(supersedes_record_at=1),
        )

        self.assertEqual(tier_of(*log), TierChoice(IMPLEMENTER, "initial"))

    def test_only_implementer_starts_open_a_window(self):
        log = (
            a_rated_design(),
            a_record("dispatch-start", author=REVIEWER),
            a_build_pass(),
            a_dissent(A_CODE_AUTOFIX),
        )

        self.assertEqual(tier_of(*log), TierChoice(IMPLEMENTER, RETIRED_REASON))


class WindowTiers(unittest.TestCase):
    def test_each_first_start_of_a_window_is_mapped_to_its_predicted_tier(self):
        log = (
            a_rated_design(),  # 1
            an_implementer_start(),  # 2
            a_build_pass(),  # 3
            a_dissent(A_CODE_AUTOFIX),  # 4
            an_implementer_start(),  # 5
            an_implementer_start(),  # 6 a continuation inside the same window
            a_build_pass(),  # 7
        )

        self.assertEqual(
            window_tiers(entries(*log)), {2: IMPLEMENTER, 5: ROUTINE_IMPLEMENTER}
        )

    def test_an_unrated_slice_maps_every_window_to_the_base(self):
        log = (
            an_unrated_design(),
            an_implementer_start(),
            a_build_pass(),
            a_dissent(A_CODE_AUTOFIX),
            an_implementer_start(),
        )

        self.assertEqual(window_tiers(entries(*log)), {2: IMPLEMENTER, 5: IMPLEMENTER})

    def test_no_starts_map_nothing(self):
        self.assertEqual(window_tiers(entries(a_rated_design())), {})


if __name__ == "__main__":
    unittest.main()
