#!/usr/bin/env python3
"""The shared ledger questions: typed lines, the latest-of query, and the review cycle arithmetic."""

import unittest

from handoff import (
    DISPATCH_EXEMPT,
    HUMAN,
    IMPLEMENTER,
    ROSTER_FLOOR,
    BuildPass,
    DesignBlock,
    LogEntry,
    cycle_round,
    cycle_start,
    entry_at,
    failures_since,
    has_substantive_dissent,
    is_substantive_dissent,
    latest_of,
    pass_windows,
    pending_human_request,
    silent_starts,
    superseded_design_block,
    truncation_run,
    typed_log,
    unresolved_refactor,
    unstarted_substantive,
)

from tests.support import a_record, entries

REVIEWER = ROSTER_FLOOR[0]
OTHER_REVIEWER = ROSTER_FLOOR[1]
OFF_ROSTER_AUTHOR = "someone-new"
AN_AGENT_TARGET = "system-design-expert"
ANOTHER_SLICE = "REQ-B-002"
A_LINE_BEYOND_THE_LOG = 9
A_FIRST_SLICE = "REQ-A-001"
A_RESOLVED_SLICE = "REQ-C-003"
A_FINDING = {"tag": "autofix", "location": "src/widget.py:1", "description": "d"}
A_CHECKPOINT = {"tag": "truncation", "location": "src/", "description": "checkpoint"}
NO_CYCLE_START = 0


def a_build_pass():
    return a_record("build-pass")


def a_design_block(**fields):
    return a_record("design-block", **{"verdict": "minor", **fields})


def a_dissent(author=REVIEWER, findings=(A_FINDING,)):
    return a_record(
        "review-feedback",
        author=author,
        verdict="changes_requested",
        findings=list(findings),
    )


def an_approval(author=REVIEWER, findings=()):
    return a_record(
        "review-feedback", author=author, verdict="approved", findings=list(findings)
    )


def feedback_of(raw):
    return typed_log([LogEntry(1, raw)])[0].record


class TypedLines(unittest.TestCase):
    def test_every_line_is_lifted_with_its_number(self):
        log = entries(a_build_pass(), a_design_block())

        self.assertEqual([entry.no for entry in log], [1, 2])
        self.assertIsInstance(log[0].record, BuildPass)
        self.assertIsInstance(log[1].record, DesignBlock)

    def test_a_known_record_reads_its_author_from_the_record(self):
        (entry,) = entries(a_dissent(author=REVIEWER))

        self.assertEqual(entry.author, REVIEWER)

    def test_an_unknown_type_reads_its_author_from_the_raw_line(self):
        (entry,) = entries({"type": "mystery", "author": OFF_ROSTER_AUTHOR})

        self.assertEqual(entry.author, OFF_ROSTER_AUTHOR)

    def test_req_id_and_type_name_read_the_raw_values(self):
        raw = a_build_pass()
        (entry,) = entries(raw)

        self.assertEqual(entry.req_id, raw["req_id"])
        self.assertEqual(entry.type_name, "build-pass")


class LatestOf(unittest.TestCase):
    def test_the_last_matching_entry_is_returned_with_its_record(self):
        log = entries(a_design_block(), a_build_pass(), a_design_block(verdict="new"))

        found = latest_of(log, DesignBlock)

        self.assertEqual(found[0].no, 3)
        self.assertEqual(found[1].verdict, "new")

    def test_no_matching_entry_is_none(self):
        log = entries(a_build_pass())

        self.assertIsNone(latest_of(log, DesignBlock))


class CycleStart(unittest.TestCase):
    def test_no_superseding_design_block_starts_at_zero(self):
        log = entries(a_design_block(), a_build_pass())

        self.assertEqual(cycle_start(log), NO_CYCLE_START)

    def test_the_latest_valid_superseding_block_starts_the_cycle(self):
        log = entries(
            a_design_block(),
            a_build_pass(),
            a_design_block(supersedes_record_at=1),
            a_design_block(supersedes_record_at=3),
        )

        self.assertEqual(cycle_start(log), 4)

    def test_a_forward_pointer_does_not_start_a_cycle(self):
        log = entries(
            a_design_block(supersedes_record_at=A_LINE_BEYOND_THE_LOG), a_design_block()
        )

        self.assertEqual(cycle_start(log), NO_CYCLE_START)

    def test_a_boolean_pointer_does_not_start_a_cycle(self):
        log = entries(a_design_block(), a_design_block(supersedes_record_at=True))

        self.assertEqual(cycle_start(log), NO_CYCLE_START)

    def test_a_pointer_to_a_non_design_record_does_not_start_a_cycle(self):
        log = entries(a_build_pass(), a_design_block(supersedes_record_at=1))

        self.assertEqual(cycle_start(log), NO_CYCLE_START)

    def test_a_valid_pointer_names_the_superseded_block(self):
        log = entries(a_design_block(), a_design_block(supersedes_record_at=1))
        by_line = {entry.no: entry for entry in log}

        self.assertIs(superseded_design_block(log[1], by_line), log[0])

    def test_a_non_design_entry_supersedes_nothing(self):
        log = entries(a_design_block(), a_build_pass())
        by_line = {entry.no: entry for entry in log}

        self.assertIsNone(superseded_design_block(log[1], by_line))


class PassWindows(unittest.TestCase):
    def setUp(self):
        self.log = entries(
            a_build_pass(),  # 1
            an_approval(REVIEWER),  # 2
            a_dissent(OTHER_REVIEWER),  # 3
            a_build_pass(),  # 4
            an_approval(OTHER_REVIEWER),  # 5
            a_build_pass(),  # 6
        )

    def windows(self, start=NO_CYCLE_START, build_pass_line=6):
        return pass_windows(self.log, start, build_pass_line, ROSTER_FLOOR)

    def test_consecutive_build_passes_bound_one_window_each(self):
        windows = self.windows()

        self.assertEqual(
            [sorted(window) for window in windows],
            [[REVIEWER, OTHER_REVIEWER], [OTHER_REVIEWER]],
        )

    def test_only_the_latest_feedback_per_reviewer_is_kept(self):
        log = entries(
            a_build_pass(), a_dissent(REVIEWER), an_approval(REVIEWER), a_build_pass()
        )

        (window,) = pass_windows(log, NO_CYCLE_START, 4, ROSTER_FLOOR)

        self.assertEqual(window[REVIEWER].verdict, "approved")

    def test_off_roster_feedback_is_excluded(self):
        log = entries(a_build_pass(), a_dissent(OFF_ROSTER_AUTHOR), a_build_pass())

        (window,) = pass_windows(log, NO_CYCLE_START, 3, ROSTER_FLOOR)

        self.assertEqual(window, {})

    def test_passes_before_the_cycle_start_are_excluded(self):
        windows = self.windows(start=3)

        self.assertEqual([sorted(window) for window in windows], [[OTHER_REVIEWER]])

    def test_passes_after_the_current_line_are_excluded(self):
        windows = self.windows(build_pass_line=4)

        self.assertEqual(len(windows), 1)


class CycleRound(unittest.TestCase):
    def a_round(self, log, build_pass_line):
        return cycle_round(log, NO_CYCLE_START, build_pass_line, ROSTER_FLOOR)

    def test_the_first_pass_is_round_one(self):
        log = entries(a_build_pass())

        self.assertEqual(self.a_round(log, 1), 1)

    def test_each_earlier_pass_with_substantive_dissent_adds_a_round(self):
        log = entries(
            a_build_pass(),
            a_dissent(),
            a_build_pass(),
            a_dissent(),
            a_build_pass(),
        )

        self.assertEqual(self.a_round(log, 5), 3)

    def test_a_pass_with_approvals_only_does_not_advance_the_round(self):
        log = entries(a_build_pass(), an_approval(), a_build_pass())

        self.assertEqual(self.a_round(log, 3), 1)

    def test_a_truncation_only_dissent_does_not_advance_the_round(self):
        log = entries(
            a_build_pass(), a_dissent(findings=(A_CHECKPOINT,)), a_build_pass()
        )

        self.assertEqual(self.a_round(log, 3), 1)


class SubstantiveDissent(unittest.TestCase):
    def test_a_dissenting_verdict_with_a_finding_is_substantive(self):
        self.assertTrue(is_substantive_dissent(feedback_of(a_dissent())))

    def test_an_approved_verdict_with_findings_is_not_dissent(self):
        self.assertFalse(
            is_substantive_dissent(feedback_of(an_approval(findings=(A_FINDING,))))
        )

    def test_a_truncation_only_dissent_is_not_substantive(self):
        self.assertFalse(
            is_substantive_dissent(feedback_of(a_dissent(findings=(A_CHECKPOINT,))))
        )

    def test_a_dissent_without_findings_is_not_substantive(self):
        self.assertFalse(is_substantive_dissent(feedback_of(a_dissent(findings=()))))

    def test_a_window_with_one_substantive_dissent_dissents(self):
        window = {
            REVIEWER: feedback_of(an_approval()),
            OTHER_REVIEWER: feedback_of(a_dissent()),
        }

        self.assertTrue(has_substantive_dissent(window))


def a_start(author=IMPLEMENTER):
    return a_record("dispatch-start", author=author)


def a_request(target=HUMAN, **fields):
    return a_record("consultation-request", target=target, author=IMPLEMENTER, **fields)


def a_response(**fields):
    return a_record("consultation-response", in_response_to=1, **fields)


class SilentStarts(unittest.TestCase):
    def test_the_author_starts_after_the_line_are_counted(self):
        log = entries(
            a_start(), a_build_pass(), a_start(), a_start(REVIEWER), a_start()
        )

        self.assertEqual(silent_starts(log, 2, IMPLEMENTER), 2)

    def test_the_line_itself_is_excluded(self):
        log = entries(a_start())

        self.assertEqual(silent_starts(log, 1, IMPLEMENTER), 0)


class FailuresSince(unittest.TestCase):
    def test_build_failures_after_the_line_are_counted(self):
        log = entries(
            a_record("build-failure"),
            a_design_block(),
            a_record("build-failure"),
            a_record("build-failure"),
        )

        self.assertEqual(failures_since(log, 2), 2)

    def test_a_failure_at_the_line_itself_is_excluded(self):
        log = entries(a_record("build-failure"), a_record("build-failure"))

        self.assertEqual(failures_since(log, 1), 1)


class TruncationRun(unittest.TestCase):
    def test_trailing_starts_of_the_author_form_the_run(self):
        log = entries(a_design_block(), a_start(), a_start())

        self.assertEqual(truncation_run(log, 1, IMPLEMENTER), 2)

    def test_any_own_record_resets_the_run(self):
        log = entries(
            a_design_block(),
            a_start(),
            a_record("build-failure", author=IMPLEMENTER),
            a_start(),
        )

        self.assertEqual(truncation_run(log, 1, IMPLEMENTER), 1)

    def test_records_of_other_authors_do_not_reset_it(self):
        log = entries(
            a_design_block(),
            a_start(),
            a_record("prd-autofix", author="root"),
            a_start(),
        )

        self.assertEqual(truncation_run(log, 1, IMPLEMENTER), 2)

    def test_starts_at_or_before_the_line_are_ignored(self):
        log = entries(a_start(), a_start(), a_start())

        self.assertEqual(truncation_run(log, 3, IMPLEMENTER), 0)
        self.assertEqual(truncation_run(log, 2, IMPLEMENTER), 1)


class EntryAt(unittest.TestCase):
    def setUp(self):
        self.by_no = {
            entry.no: entry for entry in entries(a_build_pass(), a_design_block())
        }

    def test_an_integer_pointer_finds_its_line(self):
        self.assertEqual(entry_at(self.by_no, 2).no, 2)

    def test_a_float_equal_to_a_line_number_finds_it_too(self):
        self.assertEqual(entry_at(self.by_no, 2.0).no, 2)

    def test_a_boolean_pointer_finds_nothing(self):
        self.assertIsNone(entry_at(self.by_no, True))

    def test_a_missing_or_non_numeric_pointer_finds_nothing(self):
        self.assertIsNone(entry_at(self.by_no, A_LINE_BEYOND_THE_LOG))
        self.assertIsNone(entry_at(self.by_no, "1"))


class PendingHumanRequest(unittest.TestCase):
    def test_an_unanswered_human_request_is_pending(self):
        log = entries(a_request())

        self.assertEqual(pending_human_request(log).no, 1)

    def test_a_request_to_an_agent_is_not_pending(self):
        log = entries(a_request(target=AN_AGENT_TARGET))

        self.assertIsNone(pending_human_request(log))

    def test_a_later_response_of_the_slice_answers_it(self):
        log = entries(a_request(), a_response())

        self.assertIsNone(pending_human_request(log))

    def test_only_the_latest_request_per_slice_counts(self):
        log = entries(a_request(), a_response(), a_request(target=AN_AGENT_TARGET))

        self.assertIsNone(pending_human_request(log))

    def test_the_target_spelling_is_forgiven_for_the_pause(self):
        log = entries(a_request(target=" Human "))

        self.assertEqual(pending_human_request(log).no, 1)

    def test_the_earliest_pending_request_across_slices_wins(self):
        log = entries(a_request(req_id=ANOTHER_SLICE), a_request())

        self.assertEqual(pending_human_request(log).no, 1)

    def test_a_request_without_a_req_id_is_ignored(self):
        log = entries(a_request(req_id=None))

        self.assertIsNone(pending_human_request(log))


class UnstartedSubstantive(unittest.TestCase):
    def test_a_substantive_record_without_a_start_is_listed(self):
        log = entries(a_build_pass())

        self.assertEqual([entry.no for entry in unstarted_substantive(log)], [1])

    def test_a_start_by_the_same_author_on_the_same_slice_silences_it(self):
        log = entries(a_start(), a_record("build-pass", author=IMPLEMENTER))

        self.assertEqual(unstarted_substantive(log), [])

    def test_a_start_by_another_author_does_not_count(self):
        log = entries(a_start(REVIEWER), a_record("build-pass", author=IMPLEMENTER))

        self.assertEqual([entry.no for entry in unstarted_substantive(log)], [2])

    def test_a_start_on_another_slice_does_not_count(self):
        log = entries(
            a_start(), a_record("build-pass", author=IMPLEMENTER, req_id=ANOTHER_SLICE)
        )

        self.assertEqual([entry.no for entry in unstarted_substantive(log)], [2])

    def test_a_start_after_the_record_does_not_count(self):
        log = entries(a_record("build-pass", author=IMPLEMENTER), a_start())

        self.assertEqual([entry.no for entry in unstarted_substantive(log)], [1])

    def test_exempt_authors_are_never_listed(self):
        log = entries(
            *(
                a_record("review-plan", author=author)
                for author in sorted(DISPATCH_EXEMPT)
            )
        )

        self.assertEqual(unstarted_substantive(log), [])

    def test_a_non_substantive_record_is_never_listed(self):
        log = entries(a_record("prd-autofix", author="root"))

        self.assertEqual(unstarted_substantive(log), [])


class UnresolvedRefactor(unittest.TestCase):
    def test_slices_whose_latest_verdict_is_refactor_first_are_listed_sorted(self):
        log = entries(
            a_design_block(verdict="refactor-first", req_id=ANOTHER_SLICE),
            a_design_block(verdict="refactor-first", req_id=A_FIRST_SLICE),
            a_design_block(verdict="refactor-first", req_id=A_RESOLVED_SLICE),
            a_design_block(verdict="covered", req_id=A_RESOLVED_SLICE),
        )

        self.assertEqual(unresolved_refactor(log), [A_FIRST_SLICE, ANOTHER_SLICE])

    def test_no_refactor_verdicts_list_nothing(self):
        self.assertEqual(unresolved_refactor(entries(a_design_block())), [])


if __name__ == "__main__":
    unittest.main()
