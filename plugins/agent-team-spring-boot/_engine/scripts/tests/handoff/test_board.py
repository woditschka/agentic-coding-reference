#!/usr/bin/env python3
"""The board model: sessions, tails, rounds, fix sources, and the display vocabulary."""

import unittest

from handoff import (
    DESIGNER,
    IMPLEMENTER,
    PRODUCT,
    ROSTER_FLOOR,
    ROUTINE_IMPLEMENTER,
    BoardOptions,
    BuildFailure,
    BuildPass,
    FixSources,
    Session,
    Step,
    Tail,
    agent_label,
    build_board,
    entry_at,
    facet_rows,
    fix_sources,
    grade_word,
    in_slice,
    ladder_round,
    matrix_authors,
    producer_dispatch,
    requester_of,
    review_rounds,
    session_span,
    session_tail,
    slice_grade,
    slice_order,
    slice_tail,
    slice_title,
    step_tail,
    tier_mismatch,
)

from tests.support import SOME_FIGURES, SOME_REQ_ID, FakeCostLookup, a_record, entries

REVIEWER = ROSTER_FLOOR[0]
OTHER_REVIEWER = ROSTER_FLOOR[3]
OFF_ROSTER_AUTHOR = "perf-reviewer"
OTHER_REQ_ID = "REQ-B-002"
A_FINDING = {"tag": "autofix", "location": "src/widget.py:1", "description": "d"}
NO_CYCLE_START = 0


def at(minute):
    return f"2026-07-06T10:{minute:02d}:00Z"


def a_dispatch(author=IMPLEMENTER, minute=0, responding_to=(0,), req_id=SOME_REQ_ID):
    return a_record(
        "dispatch-start",
        author=author,
        ts=at(minute),
        responding_to=list(responding_to),
        req_id=req_id,
    )


def a_pass(minute=0, req_id=SOME_REQ_ID):
    return a_record(
        "build-pass",
        author=IMPLEMENTER,
        ts=at(minute),
        gate_checks_run=["test"],
        req_id=req_id,
    )


def a_failure(minute=0, **fields):
    return a_record(
        "build-failure", author=IMPLEMENTER, ts=at(minute), **{"retry": 1, **fields}
    )


def a_review(
    author=REVIEWER, verdict="changes_requested", findings=(A_FINDING,), minute=0
):
    return a_record(
        "review-feedback",
        author=author,
        verdict=verdict,
        findings=list(findings),
        ts=at(minute),
    )


def an_approval(author=REVIEWER, minute=0):
    return a_review(author, "approved", (), minute)


def a_prd(title="Rate-limit the API", minute=0):
    return a_record("prd-entry", author=PRODUCT, title=title, ts=at(minute))


def a_design(minute=0, **fields):
    return a_record(
        "design-block",
        author=DESIGNER,
        ts=at(minute),
        **{"verdict": "covered", **fields},
    )


def a_request(author=IMPLEMENTER, minute=0):
    return a_record(
        "consultation-request",
        author=author,
        target=DESIGNER,
        question="q",
        ts=at(minute),
    )


def a_response(in_response_to, minute=0):
    return a_record(
        "consultation-response",
        author=DESIGNER,
        in_response_to=in_response_to,
        answer="a",
        ts=at(minute),
    )


def an_autofix(minute=0):
    return a_record(
        "design-doc-autofix",
        author="claude",
        file="docs/system-design.md",
        ts=at(minute),
    )


def a_grade(verdict="skim", facets=None):
    return a_record(
        "grader-verdict", author="change-grader", verdict=verdict, facets=facets
    )


def by_no_of(log):
    return {entry.no: entry for entry in log}


class AgentLabels(unittest.TestCase):
    def test_a_pipeline_agent_has_its_short_label(self):
        self.assertEqual(agent_label(IMPLEMENTER), "implementer")

    def test_a_reviewer_drops_its_suffix(self):
        self.assertEqual(agent_label("code-quality-reviewer"), "code-quality")

    def test_an_unknown_author_is_shown_as_written(self):
        self.assertEqual(agent_label("someone-new"), "someone-new")

    def test_a_missing_or_non_string_author_is_a_question_mark(self):
        self.assertEqual(
            (agent_label(None), agent_label(7), agent_label("")), ("?", "?", "?")
        )

    def test_control_characters_are_dropped(self):
        self.assertEqual(agent_label("evil\x1b[2Jer-reviewer"), "evil[2Jer")


class GradeWords(unittest.TestCase):
    def test_an_older_vocabulary_maps_to_the_current(self):
        self.assertEqual(
            (grade_word("clear"), grade_word("concern")), ("skim", "scrutinize")
        )

    def test_a_current_word_passes_through(self):
        self.assertEqual(grade_word("skim"), "skim")

    def test_a_non_string_passes_through(self):
        self.assertEqual(grade_word(["x"]), ["x"])


class FacetRows(unittest.TestCase):
    def test_facets_keep_the_records_order(self):
        (entry,) = entries(
            a_grade(facets={"zeta": {"verdict": "skim"}, "alpha": {"verdict": "skim"}})
        )

        self.assertEqual([name for name, _ in facet_rows(entry)], ["zeta", "alpha"])

    def test_a_scalar_facet_keeps_an_empty_row(self):
        (entry,) = entries(a_grade(facets={"blast_radius": "not-a-dict"}))

        self.assertEqual(facet_rows(entry), [("blast_radius", {})])

    def test_empty_or_missing_facets_have_no_rows(self):
        without, empty = entries(a_grade(), a_grade(facets={}))

        self.assertEqual((facet_rows(without), facet_rows(empty)), ([], []))

    def test_a_non_grade_entry_has_no_rows(self):
        (entry,) = entries(a_pass())

        self.assertEqual(facet_rows(entry), [])


class SliceFacts(unittest.TestCase):
    def test_the_latest_string_title_wins(self):
        log = entries(a_prd("first"), a_prd("second"), a_prd(title=7))

        self.assertEqual(slice_title(log), "second")

    def test_no_prd_entry_means_no_title(self):
        self.assertIsNone(slice_title(entries(a_pass())))

    def test_the_latest_grade_wins_in_the_current_vocabulary(self):
        log = entries(a_grade("skim"), a_grade("concern"))

        self.assertEqual(slice_grade(log), "scrutinize")

    def test_a_non_string_latest_grade_means_no_grade(self):
        log = entries(a_grade("skim"), a_grade(verdict=["skim"]))

        self.assertIsNone(slice_grade(log))


class SliceOrder(unittest.TestCase):
    def test_slices_keep_first_appearance_order(self):
        log = entries(
            a_pass(req_id=OTHER_REQ_ID), a_pass(), a_pass(req_id=OTHER_REQ_ID)
        )

        self.assertEqual(slice_order(log), [OTHER_REQ_ID, SOME_REQ_ID])

    def test_the_unnamed_group_comes_last(self):
        log = entries(a_record("build-pass", req_id=None), a_pass())

        self.assertEqual(slice_order(log), [SOME_REQ_ID, None])

    def test_an_empty_req_id_joins_the_unnamed_group(self):
        (entry,) = entries(a_record("build-pass", req_id=""))

        self.assertTrue(in_slice(entry, None))

    def test_a_named_entry_is_only_in_its_own_slice(self):
        (entry,) = entries(a_pass())

        self.assertTrue(in_slice(entry, SOME_REQ_ID))
        self.assertFalse(in_slice(entry, None))


class ReviewRounds(unittest.TestCase):
    def test_a_reappearing_reviewer_opens_a_round(self):
        log = entries(
            a_review(REVIEWER), an_approval(OTHER_REVIEWER), an_approval(REVIEWER)
        )

        rounds = review_rounds(log)

        self.assertEqual(
            [sorted(round_) for round_ in rounds],
            [sorted([OTHER_REVIEWER, REVIEWER]), [REVIEWER]],
        )

    def test_an_unnamed_author_rounds_as_unknown(self):
        (log,) = [entries(a_record("review-feedback", author=7, verdict="approved"))]

        self.assertEqual(list(review_rounds(log)[0]), ["?"])

    def test_off_roster_authors_follow_the_roster_in_the_matrix(self):
        rounds = review_rounds(
            entries(an_approval(OFF_ROSTER_AUTHOR), an_approval(REVIEWER))
        )

        self.assertEqual(
            matrix_authors(rounds, ROSTER_FLOOR), [*ROSTER_FLOOR, OFF_ROSTER_AUTHOR]
        )

    def test_the_ladder_round_counts_completed_passes_with_dissent(self):
        log = entries(a_pass(), a_review(REVIEWER), a_pass())

        self.assertEqual(ladder_round(log, ROSTER_FLOOR), 2)


class ProducerDispatch(unittest.TestCase):
    def test_a_record_is_timed_from_its_authors_dispatch(self):
        log = entries(a_dispatch(REVIEWER), a_review(REVIEWER))

        self.assertIs(producer_dispatch(log[1], log), log[0])

    def test_a_dispatch_in_another_slice_never_pairs(self):
        log = entries(a_dispatch(REVIEWER, req_id=OTHER_REQ_ID), a_review(REVIEWER))

        self.assertIsNone(producer_dispatch(log[1], log))

    def test_a_re_engaged_author_carries_no_start(self):
        log = entries(a_dispatch(REVIEWER), a_review(REVIEWER), an_approval(REVIEWER))

        self.assertIsNone(producer_dispatch(log[2], log))

    def test_an_authorless_record_carries_no_start(self):
        log = entries(a_dispatch(REVIEWER), a_record("review-feedback", author=None))

        self.assertIsNone(producer_dispatch(log[1], log))


class StepTails(unittest.TestCase):
    def test_a_timed_step_carries_its_elapsed_time(self):
        log = entries(a_dispatch(REVIEWER, minute=0), a_review(REVIEWER, minute=5))

        self.assertEqual(step_tail(log[1], log, None), Tail("5m", None))

    def test_the_cost_rides_when_the_lookup_answers(self):
        log = entries(a_dispatch(REVIEWER, minute=0), a_review(REVIEWER, minute=5))

        self.assertEqual(
            step_tail(log[1], log, FakeCostLookup()), Tail("5m", SOME_FIGURES)
        )

    def test_a_step_without_a_dispatch_carries_no_tail(self):
        log = entries(a_review(REVIEWER, minute=5))

        self.assertIsNone(step_tail(log[0], log, FakeCostLookup()))

    def test_a_record_older_than_its_dispatch_carries_no_tail(self):
        log = entries(a_dispatch(REVIEWER, minute=9), a_review(REVIEWER, minute=5))

        self.assertIsNone(step_tail(log[1], log, None))


class SessionSpans(unittest.TestCase):
    def span_of(self, *raws):
        log = entries(*raws)
        return log, session_span(log, 0, by_no_of(log))

    def test_a_clean_build_closes_the_session(self):
        log, span = self.span_of(a_dispatch(), a_failure(), a_pass(), an_approval())

        self.assertEqual(
            (span.children, span.closer, span.next_index), ((log[1], log[2]), log[2], 3)
        )

    def test_an_abort_closes_the_session_and_stops_absorbing(self):
        log, span = self.span_of(
            a_dispatch(), a_failure(abort_reason="design-mismatch"), a_request()
        )

        self.assertEqual((span.closer, span.next_index), (log[1], 2))

    def test_a_retry_dispatch_is_absorbed(self):
        log, span = self.span_of(
            a_dispatch(), a_failure(), a_dispatch(responding_to=(2,)), a_pass()
        )

        self.assertEqual((span.children, span.siblings), ((log[1], log[3]), ()))

    def test_a_doc_owner_fix_is_a_sibling(self):
        log, span = self.span_of(
            a_review(OTHER_REVIEWER),
            a_dispatch(),
            a_dispatch(PRODUCT, responding_to=(1,)),
            a_pass(),
        )
        span = session_span(log, 1, by_no_of(log))

        self.assertEqual(span.siblings, (log[2],))

    def test_a_foreign_consult_is_a_sibling(self):
        log, span = self.span_of(a_dispatch(), a_request(author=PRODUCT), a_pass())

        self.assertEqual((span.siblings, span.children), ((log[1],), (log[2],)))

    def test_the_implementers_own_consult_is_a_child(self):
        log, span = self.span_of(a_dispatch(), a_request(), a_response(2), a_pass())

        self.assertEqual(span.children, (log[1], log[2], log[3]))

    def test_an_autofix_is_hoisted_as_a_sibling(self):
        log, span = self.span_of(a_dispatch(), an_autofix(), a_pass())

        self.assertEqual((span.siblings, span.closer), ((log[1],), log[2]))

    def test_an_open_session_has_no_closer(self):
        _, span = self.span_of(a_dispatch(), a_failure())

        self.assertIsNone(span.closer)


class SessionTails(unittest.TestCase):
    def test_a_closed_session_is_timed_from_opener_to_closer(self):
        log = entries(a_dispatch(minute=6), a_pass(minute=10))

        self.assertEqual(session_tail(log[0], log[1], None), Tail("4m", None))

    def test_the_cost_rides_the_closed_session(self):
        log = entries(a_dispatch(minute=6), a_pass(minute=10))

        self.assertEqual(
            session_tail(log[0], log[1], FakeCostLookup()), Tail("4m", SOME_FIGURES)
        )

    def test_an_open_session_carries_no_tail(self):
        log = entries(a_dispatch(minute=6))

        self.assertIsNone(session_tail(log[0], None, FakeCostLookup()))


class TierMismatch(unittest.TestCase):
    def mismatch(self, ran, *, routine):
        log = entries(a_dispatch(), a_pass())
        return tier_mismatch(log[0], log[1], FakeCostLookup(tiers=ran), routine=routine)

    def test_a_routine_prediction_with_a_base_transcript_ran_base(self):
        self.assertEqual(self.mismatch((IMPLEMENTER,), routine=True), "ran base")

    def test_a_base_prediction_with_a_routine_transcript_ran_routine(self):
        self.assertEqual(
            self.mismatch((ROUTINE_IMPLEMENTER,), routine=False), "ran routine"
        )

    def test_an_agreeing_transcript_draws_no_verdict(self):
        self.assertIsNone(self.mismatch((ROUTINE_IMPLEMENTER,), routine=True))

    def test_an_ambiguous_or_absent_transcript_draws_no_verdict(self):
        for ran in ((), (IMPLEMENTER, ROUTINE_IMPLEMENTER), None):
            self.assertIsNone(self.mismatch(ran, routine=True))

    def test_an_open_session_is_not_audited(self):
        log = entries(a_dispatch())

        self.assertIsNone(
            tier_mismatch(
                log[0], None, FakeCostLookup(tiers=(IMPLEMENTER,)), routine=True
            )
        )


class FixSourceResolution(unittest.TestCase):
    def test_only_dissenting_reviews_count(self):
        log = entries(
            a_review(REVIEWER),
            an_approval(OTHER_REVIEWER),
            a_dispatch(responding_to=(1, 2)),
        )

        self.assertEqual(
            fix_sources(log[2], by_no_of(log)), FixSources(("code-quality",), 1)
        )

    def test_findings_sum_across_sources(self):
        log = entries(
            a_review(REVIEWER, findings=(A_FINDING, A_FINDING)),
            a_review(OTHER_REVIEWER),
            a_dispatch(responding_to=(1, 2)),
        )

        self.assertEqual(
            fix_sources(log[2], by_no_of(log)), FixSources(("code-quality", "doc"), 3)
        )

    def test_a_dispatch_answering_no_dissent_has_no_sources(self):
        log = entries(an_approval(), a_dispatch(responding_to=(1,)))

        self.assertIsNone(fix_sources(log[1], by_no_of(log)))

    def test_a_non_dispatch_answers_nothing(self):
        log = entries(a_review(), a_pass())

        self.assertIsNone(fix_sources(log[1], by_no_of(log)))


class Pointers(unittest.TestCase):
    def test_a_float_pointer_resolves_under_number_equality(self):
        log = entries(a_request(), a_response(1.0))

        self.assertIs(entry_at(by_no_of(log), 1.0), log[0])

    def test_a_bool_pointer_resolves_nothing(self):
        log = entries(a_request())

        self.assertIsNone(entry_at(by_no_of(log), True))

    def test_a_dangling_pointer_resolves_nothing(self):
        log = entries(a_request())

        self.assertIsNone(entry_at(by_no_of(log), 99))

    def test_a_response_returns_to_its_requester(self):
        log = entries(a_request(author=PRODUCT), a_response(1))

        self.assertEqual(requester_of(log[1], by_no_of(log)), PRODUCT)

    def test_a_response_to_a_non_request_has_no_requester(self):
        log = entries(a_pass(), a_response(1))

        self.assertIsNone(requester_of(log[1], by_no_of(log)))


class SliceTails(unittest.TestCase):
    def test_fewer_than_two_timed_records_have_no_roll_up(self):
        self.assertIsNone(slice_tail(entries(a_pass()), FakeCostLookup()))

    def test_no_lookup_means_no_roll_up(self):
        self.assertIsNone(slice_tail(entries(a_pass(0), a_pass(15)), None))

    def test_the_roll_up_spans_first_to_last_timed_record(self):
        tail = slice_tail(entries(a_pass(0), a_pass(15)), FakeCostLookup())

        self.assertEqual(tail, Tail("15m", SOME_FIGURES))

    def test_a_lookup_without_figures_means_no_roll_up(self):
        self.assertIsNone(
            slice_tail(entries(a_pass(0), a_pass(15)), FakeCostLookup(figures=None))
        )


class BuildingTheBoard(unittest.TestCase):
    def board_of(self, *raws, **options):
        log = entries(*raws)
        return build_board(
            log,
            SOME_REQ_ID,
            BoardOptions(roster=ROSTER_FLOOR, **options),
            [OTHER_REQ_ID],
        )

    def test_passes_and_failures_are_counted(self):
        board = self.board_of(a_failure(), a_pass(), a_pass())

        self.assertEqual((board.passes, board.failures), (2, 1))

    def test_other_slices_are_carried(self):
        self.assertEqual(self.board_of(a_pass()).other_slices, (OTHER_REQ_ID,))

    def test_grader_features_never_reach_the_timeline(self):
        board = self.board_of(a_record("grader-features", features={}), a_pass())

        self.assertIsInstance(board.timeline[0].entry.record, BuildPass)
        self.assertEqual(len(board.timeline), 1)

    def test_an_implementer_dispatch_opens_a_session(self):
        board = self.board_of(
            a_dispatch(minute=6), a_failure(minute=8), a_pass(minute=10)
        )

        (session,) = board.timeline
        self.assertIsInstance(session, Session)
        self.assertEqual(session.tail, Tail("4m", None))
        self.assertIsInstance(session.children[0].record, BuildFailure)

    def test_a_routine_window_marks_the_session(self):
        board = self.board_of(
            a_dispatch(), a_pass(), window_tiers={1: ROUTINE_IMPLEMENTER}
        )

        self.assertTrue(board.timeline[0].routine)

    def test_a_flat_row_is_a_step_with_its_requester(self):
        board = self.board_of(a_request(author=PRODUCT), a_response(1))

        response = board.timeline[1]
        self.assertIsInstance(response, Step)
        self.assertEqual(response.requester, PRODUCT)


if __name__ == "__main__":
    unittest.main()
