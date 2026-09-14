#!/usr/bin/env python3
"""The append-time gates: the review anchor, the design sync, the responding-to pointers, the design-block coverage."""

import unittest

from handoff import (
    DESIGNER,
    PRODUCT,
    Entry,
    changes_prd,
    design_block_uncovered,
    design_sync_missing,
    parse_record,
    responding_to_dangling,
    review_anchor_missing,
)

from tests.support import A_DESIGN_DOC, FakeRepository, a_record, entries

A_REVIEWER = "doc-reviewer"
OTHER_SLICE = "REQ-OTHER-009"
A_PRD_UPDATE = {"path": "docs/prd.md", "summary": "edge case added"}
A_DESIGN_UPDATE = {"path": "docs/system-design.md", "summary": "row added"}
LOG_LINES = 3


def a_build_pass(**fields):
    return a_record("build-pass", **fields)


def a_start(author=A_REVIEWER, **fields):
    return a_record("dispatch-start", author=author, **fields)


def a_feedback(author=A_REVIEWER, **fields):
    return parse_record(
        a_record("review-feedback", author=author, verdict="approved", **fields)
    )


def a_response(author=PRODUCT, updates=(A_PRD_UPDATE,), **fields):
    return a_record(
        "consultation-response", author=author, memory_updates=list(updates), **fields
    )


def a_design_block(**fields):
    return a_record("design-block", verdict="minor", **fields)


class ReviewAnchor(unittest.TestCase):
    def test_a_log_without_a_build_pass_has_nothing_to_anchor_to(self):
        self.assertIsNone(review_anchor_missing(entries(a_start()), a_feedback()))

    def test_a_review_with_its_start_since_the_build_pass_lands(self):
        self.assertIsNone(
            review_anchor_missing(entries(a_build_pass(), a_start()), a_feedback())
        )

    def test_a_re_review_without_its_start_is_refused_naming_the_build_pass(self):
        refusal = review_anchor_missing(
            entries(a_build_pass(), a_start(), a_build_pass()), a_feedback()
        )

        self.assertEqual(
            refusal,
            f"review-feedback by {A_REVIEWER} has no dispatch-start since the "
            "build-pass at line 3; append a dispatch-start "
            "(handoff-append skill § Dispatch-Start) and retry",
        )

    def test_another_reviewer_s_start_does_not_anchor(self):
        refusal = review_anchor_missing(
            entries(a_build_pass(), a_start("other")), a_feedback()
        )

        self.assertIsNotNone(refusal)
        self.assertIn("no dispatch-start since the build-pass at line 1", refusal)

    def test_another_slice_is_ignored(self):
        log = entries(a_build_pass(req_id=OTHER_SLICE))

        self.assertIsNone(review_anchor_missing(log, a_feedback()))

    def test_the_author_is_sanitized_in_the_refusal(self):
        refusal = review_anchor_missing(
            entries(a_build_pass()), a_feedback(author="\x1bbad")
        )

        self.assertNotIn("\x1b", refusal)


class DesignSync(unittest.TestCase):
    def missing(self, *raws):
        return design_sync_missing(entries(*raws), parse_record(a_build_pass()))

    def test_a_prd_change_with_no_design_answer_is_refused(self):
        refusal = self.missing(a_response())

        self.assertIsNotNone(refusal)
        self.assertIn(
            "consultation-response at line 1, which changed docs/prd.md", refusal
        )

    def test_a_design_answer_after_the_prd_change_clears_it(self):
        self.assertIsNone(
            self.missing(
                a_response(), a_response(author=DESIGNER, updates=(A_DESIGN_UPDATE,))
            )
        )

    def test_a_re_triage_after_the_prd_change_clears_it(self):
        self.assertIsNone(self.missing(a_response(), a_design_block()))

    def test_a_re_triage_before_the_prd_change_does_not_clear_it(self):
        refusal = self.missing(a_design_block(), a_response())

        self.assertIn("consultation-response at line 2", refusal)

    def test_two_prd_changes_name_the_later_line(self):
        refusal = self.missing(
            a_response(), a_response(author=DESIGNER, updates=()), a_response()
        )

        self.assertIn("consultation-response at line 3", refusal)

    def test_another_slice_is_skipped(self):
        self.assertIsNone(self.missing(a_response(req_id=OTHER_SLICE)))

    def test_a_requirements_answer_that_left_the_prd_alone_passes(self):
        adr = {"path": "docs/adr/2026-01-01-x.md", "summary": "non-goal ADR"}

        self.assertIsNone(
            self.missing(a_response(updates=(adr,)), a_response(updates=()))
        )


class ChangesPrd(unittest.TestCase):
    def changes(self, *paths):
        updates = [{"path": p, "summary": "s"} for p in paths]
        return changes_prd(parse_record(a_response(updates=updates)))

    def test_the_prd_path_counts(self):
        self.assertTrue(self.changes("docs/prd.md"))

    def test_a_dot_slash_prefix_is_stripped(self):
        self.assertTrue(self.changes("./docs/prd.md"))

    def test_an_anchor_into_the_prd_counts(self):
        self.assertTrue(self.changes("docs/prd.md#non-goals"))

    def test_a_sibling_file_does_not_count(self):
        self.assertFalse(self.changes("docs/prd.md.bak"))

    def test_a_non_string_path_does_not_count(self):
        self.assertFalse(self.changes(None, 7))


class RespondingTo(unittest.TestCase):
    def dangling(self, *targets):
        record = parse_record(a_start(responding_to=list(targets)))
        return responding_to_dangling(record, LOG_LINES)

    def test_existing_lines_and_the_zero_sentinel_pass(self):
        self.assertIsNone(self.dangling(0, 1, LOG_LINES))

    def test_a_line_beyond_the_log_is_refused_with_the_count(self):
        self.assertEqual(
            self.dangling(LOG_LINES + 1),
            f"responding_to references non-existent log line(s) [{LOG_LINES + 1}] (log has {LOG_LINES} line(s))",
        )

    def test_a_negative_line_is_refused(self):
        self.assertIn("[-1]", self.dangling(-1))

    def test_a_boolean_is_refused(self):
        self.assertIn("[True]", self.dangling(True))

    def test_a_non_integer_is_refused(self):
        self.assertIn("['1']", self.dangling("1"))

    def test_a_bad_value_is_sanitized_in_the_message(self):
        refusal = self.dangling("\x1b[31m9")

        self.assertIn("non-existent log line(s)", refusal)
        self.assertNotIn("\x1b", refusal)

    def test_a_non_list_reads_as_nothing_to_check(self):
        record = parse_record(a_start(responding_to="5"))

        self.assertIsNone(responding_to_dangling(record, LOG_LINES))


class DesignBlockCoverage(unittest.TestCase):
    def refusal(self, repository, **paths):
        log = entries(a_record("prd-entry"))
        raw = a_design_block(**paths)
        candidate = Entry(len(log) + 1, raw, parse_record(raw))
        return design_block_uncovered(log, candidate, repository)

    def test_an_unlisted_dirty_design_doc_is_refused_by_name(self):
        refusal = self.refusal(
            FakeRepository(dirty=(A_DESIGN_DOC,)), primary_paths=["src/x.py"]
        )

        self.assertIsNotNone(refusal)
        self.assertIn(f"covering record: {A_DESIGN_DOC}", refusal)

    def test_a_listed_dirty_design_doc_passes(self):
        refusal = self.refusal(
            FakeRepository(dirty=(A_DESIGN_DOC,)), supporting_paths=[A_DESIGN_DOC]
        )

        self.assertIsNone(refusal)

    def test_a_clean_tree_passes(self):
        self.assertIsNone(self.refusal(FakeRepository()))

    def test_an_unreadable_repository_leaves_the_gate_open_for_the_audit(self):
        self.assertIsNone(self.refusal(FakeRepository(repo_state=None)))

    def test_the_named_path_is_sanitized(self):
        refusal = self.refusal(FakeRepository(dirty=("docs/adr/\x1bx.md",)))

        self.assertNotIn("\x1b", refusal)


if __name__ == "__main__":
    unittest.main()
