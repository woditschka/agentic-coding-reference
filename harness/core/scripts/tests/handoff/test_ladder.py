#!/usr/bin/env python3
"""The reviewer ladder of one pass, the dissent ceilings, and the dissent a narrowed roster left outstanding."""

import unittest

from handoff import (
    REVIEW_ROUND_CAP,
    ROSTER_FLOOR,
    Ceiling,
    OutstandingDissent,
    ReviewerLadder,
    ReviewPass,
    churned_reviewers,
    dissent_ceiling,
    dissents_below_bar,
    escalate_precedes_pass,
    outstanding_dissent,
    prior_below_bar_dissent,
    reviewer_ladder,
    truncation_only_passes,
)

from tests.support import a_record, entries

FLOOR = tuple(ROSTER_FLOOR)
FIRST, SECOND = FLOOR[0], FLOOR[1]
OUTSIDER = "someone-else"
A_POLISH = {
    "tag": "autofix",
    "location": "src/w.py:1",
    "description": "d",
    "severity": "minor",
}
A_CRITICAL = {**A_POLISH, "severity": "critical"}
A_CLARIFY = {
    "tag": "clarify",
    "location": "src/w.py:1",
    "description": "d",
    "clarify_target": "x",
}
AN_ESCALATION = {**A_POLISH, "tag": "escalate"}
A_CHECKPOINT = {**A_POLISH, "tag": "truncation"}
NO_CYCLE_START = 0
ROUND_ONE = 1
CAPPED_ROUND = REVIEW_ROUND_CAP
PAST_THE_CAP = REVIEW_ROUND_CAP + 1


def a_build_pass():
    return a_record("build-pass")


def a_start(author=FIRST):
    return a_record("dispatch-start", author=author)


def a_dissent(author=FIRST, findings=(A_POLISH,), verdict="changes_requested"):
    return a_record(
        "review-feedback", author=author, verdict=verdict, findings=list(findings)
    )


def an_approval(author=FIRST, findings=()):
    return a_record(
        "review-feedback", author=author, verdict="approved", findings=list(findings)
    )


PASS_SHAPE = {
    "build_pass_line": 1,
    "round_no": ROUND_ONE,
    "reviewers": FLOOR,
    "roster": FLOOR,
    "cycle_start": NO_CYCLE_START,
    "gap": None,
}


def a_pass(*raws, **shape):
    """Build a pass over the records; the shape defaults to a build-pass at line one and the floor."""
    form = {**PASS_SHAPE, **shape}
    return ReviewPass(
        entries(*raws),
        form["build_pass_line"],
        form["cycle_start"],
        form["round_no"],
        tuple(form["reviewers"]),
        form["gap"],
        tuple(form["roster"]),
    )


def verdicts_of(review):
    return {
        reviewer: entry.record
        for reviewer, entry in reviewer_ladder(review).feedback.items()
    }


class RoundContext(unittest.TestCase):
    def test_a_round_below_the_cap_carries_only_its_number(self):
        context = a_pass(a_build_pass(), round_no=2).round_context()

        self.assertEqual(context, {"round": 2, "prompt_note": "Review round 2."})

    def test_the_capped_round_is_critical_only(self):
        self.assertTrue(a_pass(a_build_pass(), round_no=CAPPED_ROUND).critical_only)
        self.assertFalse(
            a_pass(a_build_pass(), round_no=CAPPED_ROUND - 1).critical_only
        )

    def test_the_capped_round_advertises_the_critical_only_bar(self):
        context = a_pass(a_build_pass(), round_no=CAPPED_ROUND).round_context()
        self.assertEqual(context["finding_bar"], "critical-only")
        self.assertTrue(
            context["prompt_note"].startswith(
                f"Review round {CAPPED_ROUND}: critical-only."
            )
        )

    def test_feedback_since_build_pass_yields_typed_records_after_the_line(self):
        review = a_pass(a_dissent(), a_build_pass(), an_approval(), build_pass_line=2)

        yielded = list(review.feedback_since_build_pass())

        self.assertEqual([entry.no for entry, _ in yielded], [3])
        self.assertEqual(yielded[0][1].verdict, "approved")


class TheLadder(unittest.TestCase):
    def test_reviewers_with_no_record_since_the_build_pass_are_undispatched(self):
        ladder = reviewer_ladder(a_pass(a_build_pass()))

        self.assertEqual(ladder, ReviewerLadder({}, (), (), FLOOR))

    def test_current_feedback_places_a_reviewer_on_the_feedback_rung(self):
        ladder = reviewer_ladder(
            a_pass(a_build_pass(), an_approval(FIRST), reviewers=(FIRST,))
        )

        self.assertEqual(list(ladder.feedback), [FIRST])
        self.assertEqual(ladder.feedback[FIRST].no, 2)
        self.assertEqual(
            (ladder.retry_once, ladder.stalled, ladder.undispatched), ((), (), ())
        )

    def test_the_latest_feedback_of_a_reviewer_wins(self):
        ladder = reviewer_ladder(
            a_pass(
                a_build_pass(), a_dissent(FIRST), an_approval(FIRST), reviewers=(FIRST,)
            )
        )

        self.assertEqual(ladder.feedback[FIRST].no, 3)

    def test_one_silent_start_is_a_retry(self):
        ladder = reviewer_ladder(
            a_pass(a_build_pass(), a_start(FIRST), reviewers=(FIRST,))
        )

        self.assertEqual(ladder.retry_once, (FIRST,))

    def test_a_silent_start_after_feedback_makes_the_feedback_stale(self):
        ladder = reviewer_ladder(
            a_pass(
                a_build_pass(), an_approval(FIRST), a_start(FIRST), reviewers=(FIRST,)
            )
        )

        self.assertEqual(ladder.feedback, {})
        self.assertEqual(ladder.retry_once, (FIRST,))

    def test_two_silent_starts_stall(self):
        ladder = reviewer_ladder(
            a_pass(a_build_pass(), a_start(FIRST), a_start(FIRST), reviewers=(FIRST,))
        )

        self.assertEqual(ladder.stalled, (FIRST,))

    def test_feedback_after_starts_resets_the_count(self):
        ladder = reviewer_ladder(
            a_pass(
                a_build_pass(),
                a_start(FIRST),
                a_start(FIRST),
                an_approval(FIRST),
                reviewers=(FIRST,),
            )
        )

        self.assertEqual(list(ladder.feedback), [FIRST])
        self.assertEqual(ladder.stalled, ())

    def test_records_before_the_build_pass_are_ignored(self):
        ladder = reviewer_ladder(
            a_pass(
                an_approval(FIRST),
                a_start(FIRST),
                a_build_pass(),
                build_pass_line=3,
                reviewers=(FIRST,),
            )
        )

        self.assertEqual(ladder.undispatched, (FIRST,))

    def test_only_pass_reviewers_are_placed(self):
        ladder = reviewer_ladder(
            a_pass(a_build_pass(), an_approval(SECOND), reviewers=(FIRST,))
        )

        self.assertEqual(ladder, ReviewerLadder({}, (), (), (FIRST,)))


class EscalateHalt(unittest.TestCase):
    def test_an_escalate_finding_in_the_previous_pass_halts_the_next(self):
        log = entries(
            a_build_pass(), a_dissent(FIRST, findings=(AN_ESCALATION,)), a_build_pass()
        )

        self.assertTrue(escalate_precedes_pass(log, 3))

    def test_feedback_after_the_build_pass_lifts_the_halt(self):
        log = entries(
            a_build_pass(),
            a_dissent(FIRST, findings=(AN_ESCALATION,)),
            a_build_pass(),
            an_approval(FIRST),
        )

        self.assertFalse(escalate_precedes_pass(log, 3))

    def test_an_escalate_finding_two_passes_back_does_not_halt(self):
        log = entries(
            a_build_pass(),
            a_dissent(FIRST, findings=(AN_ESCALATION,)),
            a_build_pass(),
            an_approval(FIRST),
            a_build_pass(),
        )

        self.assertFalse(escalate_precedes_pass(log, 5))

    def test_a_previous_pass_without_an_escalate_does_not_halt(self):
        log = entries(a_build_pass(), a_dissent(FIRST), a_build_pass())

        self.assertFalse(escalate_precedes_pass(log, 3))


class DissentCeiling(unittest.TestCase):
    def test_a_converging_pass_has_no_ceiling(self):
        review = a_pass(a_build_pass(), a_dissent(FIRST), an_approval(SECOND))

        self.assertIsNone(dissent_ceiling(review, verdicts_of(review)))

    def test_a_dissent_without_findings_is_not_actionable(self):
        review = a_pass(
            a_build_pass(),
            a_dissent(FIRST, findings=()),
            a_dissent(SECOND, findings=()),
        )

        self.assertEqual(
            dissent_ceiling(review, verdicts_of(review)),
            Ceiling("empty-findings", (FIRST, SECOND)),
        )

    def test_a_third_substantive_dissent_in_one_pass_is_churn(self):
        review = a_pass(
            a_build_pass(), a_dissent(FIRST), a_dissent(FIRST), a_dissent(FIRST)
        )

        self.assertEqual(
            dissent_ceiling(review, verdicts_of(review)),
            Ceiling("pass-churn", (FIRST,)),
        )

    def test_substantive_dissent_past_the_round_cap_hits_the_cap(self):
        review = a_pass(
            a_build_pass(),
            a_dissent(FIRST, findings=(AN_ESCALATION, A_CRITICAL)),
            round_no=PAST_THE_CAP,
        )

        self.assertEqual(
            dissent_ceiling(review, verdicts_of(review)),
            Ceiling("round-cap", (FIRST,), 1),
        )

    def test_substantive_dissent_on_the_capped_round_is_not_yet_the_cap(self):
        review = a_pass(a_build_pass(), a_dissent(FIRST), round_no=CAPPED_ROUND)

        self.assertIsNone(dissent_ceiling(review, verdicts_of(review)))

    def test_the_round_cap_names_every_substantive_dissenter_sorted(self):
        review = a_pass(
            a_build_pass(), a_dissent(SECOND), a_dissent(FIRST), round_no=PAST_THE_CAP
        )

        self.assertEqual(
            dissent_ceiling(review, verdicts_of(review)).reviewers,
            tuple(sorted((FIRST, SECOND))),
        )

    def test_truncation_only_dissent_past_the_cap_is_not_the_cap(self):
        review = a_pass(
            a_build_pass(),
            a_dissent(FIRST, findings=(A_CHECKPOINT,)),
            round_no=PAST_THE_CAP,
        )

        self.assertIsNone(dissent_ceiling(review, verdicts_of(review)))

    def test_three_truncation_only_passes_are_a_run(self):
        review = a_pass(
            a_build_pass(),  # 1
            a_dissent(FIRST, findings=(A_CHECKPOINT,)),  # 2
            a_build_pass(),  # 3
            a_dissent(FIRST, findings=(A_CHECKPOINT,)),  # 4
            a_build_pass(),  # 5
            a_dissent(FIRST, findings=(A_CHECKPOINT,)),  # 6
            build_pass_line=5,
        )

        self.assertEqual(
            dissent_ceiling(review, verdicts_of(review)),
            Ceiling("truncation-run", (FIRST,)),
        )

    def test_two_truncation_only_passes_are_not_yet_a_run(self):
        review = a_pass(
            a_build_pass(),
            a_dissent(FIRST, findings=(A_CHECKPOINT,)),
            a_build_pass(),
            a_dissent(FIRST, findings=(A_CHECKPOINT,)),
            build_pass_line=3,
        )

        self.assertIsNone(dissent_ceiling(review, verdicts_of(review)))

    def test_empty_findings_win_over_churn(self):
        review = a_pass(
            a_build_pass(),
            a_dissent(FIRST),
            a_dissent(FIRST),
            a_dissent(FIRST, findings=()),
        )

        self.assertEqual(
            dissent_ceiling(review, verdicts_of(review)).cause, "empty-findings"
        )


class ChurnedReviewers(unittest.TestCase):
    def test_dissents_are_counted_per_roster_reviewer_since_the_build_pass(self):
        review = a_pass(
            a_dissent(FIRST),
            a_build_pass(),
            a_dissent(FIRST),
            a_dissent(FIRST),
            a_dissent(FIRST),
            build_pass_line=2,
        )

        self.assertEqual(churned_reviewers(review), [FIRST])

    def test_two_dissents_do_not_churn(self):
        review = a_pass(a_build_pass(), a_dissent(FIRST), a_dissent(FIRST))

        self.assertEqual(churned_reviewers(review), [])

    def test_an_off_roster_author_never_churns(self):
        review = a_pass(
            a_build_pass(),
            a_dissent(OUTSIDER),
            a_dissent(OUTSIDER),
            a_dissent(OUTSIDER),
        )

        self.assertEqual(churned_reviewers(review), [])

    def test_truncation_only_dissents_do_not_count(self):
        review = a_pass(
            a_build_pass(),
            *(a_dissent(FIRST, findings=(A_CHECKPOINT,)) for _ in range(3)),
        )

        self.assertEqual(churned_reviewers(review), [])


class TruncationOnlyPasses(unittest.TestCase):
    def test_the_current_pass_counts_one(self):
        self.assertEqual(truncation_only_passes(a_pass(a_build_pass())), 1)

    def test_each_earlier_truncation_only_pass_adds_one(self):
        review = a_pass(
            a_build_pass(),
            a_dissent(FIRST, findings=(A_CHECKPOINT,)),
            a_build_pass(),
            a_dissent(FIRST, findings=(A_CHECKPOINT,)),
            a_build_pass(),
            build_pass_line=5,
        )

        self.assertEqual(truncation_only_passes(review), 3)

    def test_a_substantive_or_approved_pass_ends_the_run(self):
        review = a_pass(
            a_build_pass(),
            a_dissent(FIRST, findings=(A_CHECKPOINT,)),
            a_build_pass(),
            an_approval(FIRST),
            a_build_pass(),
            build_pass_line=5,
        )

        self.assertEqual(truncation_only_passes(review), 1)


class BelowTheBar(unittest.TestCase):
    def dissent_entry(self, *findings, verdict="changes_requested"):
        return entries(a_dissent(FIRST, findings=findings, verdict=verdict))[0]

    def test_polish_dissent_on_a_capped_round_is_below_the_bar(self):
        entry = self.dissent_entry(A_POLISH)

        self.assertTrue(
            dissents_below_bar(
                a_pass(a_build_pass(), round_no=CAPPED_ROUND), entry, [A_POLISH]
            )
        )

    def test_a_blocked_verdict_rides_the_same_bar(self):
        entry = self.dissent_entry(A_POLISH, verdict="blocked")

        self.assertTrue(
            dissents_below_bar(
                a_pass(a_build_pass(), round_no=CAPPED_ROUND), entry, [A_POLISH]
            )
        )

    def test_the_same_dissent_below_the_cap_is_fine(self):
        entry = self.dissent_entry(A_POLISH)

        self.assertFalse(
            dissents_below_bar(a_pass(a_build_pass(), round_no=2), entry, [A_POLISH])
        )

    def test_a_critical_or_channel_finding_clears_the_bar(self):
        entry = self.dissent_entry(A_CRITICAL)

        self.assertFalse(
            dissents_below_bar(
                a_pass(a_build_pass(), round_no=CAPPED_ROUND), entry, [A_CRITICAL]
            )
        )

    def test_an_empty_dissent_is_not_below_the_bar(self):
        entry = self.dissent_entry()

        self.assertFalse(
            dissents_below_bar(a_pass(a_build_pass(), round_no=CAPPED_ROUND), entry, [])
        )

    def test_a_prior_polish_dissent_of_the_same_reviewer_in_the_pass_is_found(self):
        review = a_pass(
            a_build_pass(), a_dissent(FIRST), a_dissent(FIRST), round_no=CAPPED_ROUND
        )
        current = review.records[2]

        self.assertTrue(prior_below_bar_dissent(review, FIRST, current))

    def test_another_reviewer_or_an_earlier_pass_does_not_count(self):
        review = a_pass(
            a_dissent(FIRST),
            a_build_pass(),
            a_dissent(SECOND),
            a_dissent(FIRST),
            build_pass_line=2,
            round_no=CAPPED_ROUND,
        )
        current = review.records[3]

        self.assertFalse(prior_below_bar_dissent(review, FIRST, current))

    def test_a_prior_critical_dissent_is_not_below_the_bar(self):
        review = a_pass(
            a_build_pass(),
            a_dissent(FIRST, findings=(A_CRITICAL,)),
            a_dissent(FIRST),
            round_no=CAPPED_ROUND,
        )
        current = review.records[2]

        self.assertFalse(prior_below_bar_dissent(review, FIRST, current))


class Outstanding(unittest.TestCase):
    def test_a_dropped_dissenter_is_outstanding(self):
        review = a_pass(
            a_build_pass(),
            a_dissent(SECOND),
            a_build_pass(),
            build_pass_line=3,
            reviewers=(FIRST,),
        )

        self.assertEqual(outstanding_dissent(review), OutstandingDissent((SECOND,), ()))

    def test_a_dropped_approver_is_not(self):
        review = a_pass(
            a_build_pass(),
            an_approval(SECOND),
            a_build_pass(),
            build_pass_line=3,
            reviewers=(FIRST,),
        )

        self.assertIsNone(outstanding_dissent(review))

    def test_dissent_before_the_cycle_start_is_void(self):
        review = a_pass(
            a_build_pass(),
            a_dissent(SECOND),
            a_build_pass(),
            build_pass_line=3,
            reviewers=(FIRST,),
            cycle_start=2,
        )

        self.assertIsNone(outstanding_dissent(review))

    def test_a_reviewer_on_the_pass_roster_is_never_outstanding(self):
        review = a_pass(
            a_build_pass(), a_dissent(SECOND), a_build_pass(), build_pass_line=3
        )

        self.assertIsNone(outstanding_dissent(review))

    def test_two_silent_starts_after_the_dissent_stall_the_dissenter(self):
        review = a_pass(
            a_build_pass(),
            a_dissent(SECOND),
            a_build_pass(),
            a_start(SECOND),
            a_start(SECOND),
            build_pass_line=3,
            reviewers=(FIRST,),
        )

        self.assertEqual(
            outstanding_dissent(review), OutstandingDissent((SECOND,), (SECOND,))
        )

    def test_an_off_roster_dissenter_is_never_outstanding(self):
        review = a_pass(
            a_build_pass(),
            a_dissent(OUTSIDER),
            a_build_pass(),
            build_pass_line=3,
            reviewers=(FIRST,),
        )

        self.assertIsNone(outstanding_dissent(review))


if __name__ == "__main__":
    unittest.main()
