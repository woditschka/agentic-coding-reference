#!/usr/bin/env python3
"""Gate 1's scope lock: every changed Non-Goals row needs an override quoting the owner's decision."""

import unittest

from handoff import (
    HUMAN,
    OverrideSources,
    scope_lock_errors,
)

from tests.support import SOME_REQ_ID, a_record, entries

NG_ROW = "NG-5"
OTHER_ROW = "NG-4"
DECISION = "Cancelling only is in scope"
OTHER_SLICE = "REQ-OTHER-009"
NO_INTAKE_YET = False


def an_override(non_goal_id=NG_ROW, owner_decision=DECISION, source="dispatch"):
    return {
        "non_goal_id": non_goal_id,
        "owner_decision": owner_decision,
        "source": source,
    }


def a_human_intake(**fields):
    return a_record(
        "intake-decision",
        **{
            "author": HUMAN,
            "request": "please cancel records",
            "decisions": [DECISION],
            **fields,
        },
    )


def a_human_response(**fields):
    return a_record(
        "consultation-response",
        **{
            "author": HUMAN,
            "in_response_to": 1,
            "answer": f"Yes. {DECISION}.",
            **fields,
        },
    )


def sources_over(*raws, has_intake=None):
    log = entries(*raws)
    intake_seen = any(
        entry.type_name == "intake-decision" and entry.author == HUMAN for entry in log
    )
    return OverrideSources(
        SOME_REQ_ID,
        intake_seen if has_intake is None else has_intake,
        {entry.no: entry for entry in log},
    )


def errors_of(overrides, delta=(NG_ROW,), sources=None):
    return scope_lock_errors(overrides, delta, sources or sources_over())


class Baseline(unittest.TestCase):
    def test_an_unreadable_baseline_fails_closed(self):
        self.assertEqual(
            errors_of([], delta=None),
            ["cannot read the docs/prd.md scope-lock baseline; the check fails closed"],
        )

    def test_no_changed_rows_and_no_overrides_pass(self):
        self.assertEqual(errors_of([], delta=()), [])
        self.assertEqual(errors_of(None, delta=()), [])

    def test_a_changed_row_without_an_override_is_named(self):
        self.assertEqual(
            errors_of([], delta=(NG_ROW,)),
            [
                f"Non-Goals row {NG_ROW} changed in docs/prd.md with no "
                "scope_overrides entry recording the owner's decision"
            ],
        )

    def test_only_the_uncovered_rows_are_named(self):
        errors = errors_of([an_override()], delta=(OTHER_ROW, NG_ROW))

        self.assertEqual(len(errors), 1)
        self.assertIn(OTHER_ROW, errors[0])


class OverrideShape(unittest.TestCase):
    def test_a_non_object_item_is_reported_by_index(self):
        self.assertEqual(
            errors_of(["x", an_override()]), ["scope_overrides item 1 is not an object"]
        )

    def test_a_missing_row_id_is_reported_by_index(self):
        errors = errors_of([an_override(non_goal_id="")])

        self.assertEqual(errors[0], "scope_overrides item 1: non_goal_id missing")

    def test_an_override_naming_an_unchanged_row_is_padding(self):
        self.assertEqual(
            errors_of([an_override(non_goal_id=OTHER_ROW), an_override()]),
            [
                f"scope_overrides names {OTHER_ROW}, but no such Non-Goals row "
                "changed in docs/prd.md"
            ],
        )

    def test_an_empty_quote_is_an_error(self):
        for quote in ("   ", None):
            with self.subTest(quote=quote):
                self.assertEqual(
                    errors_of([an_override(owner_decision=quote)]),
                    [f"scope_overrides {NG_ROW}: owner_decision quote is empty"],
                )

    def test_a_malformed_source_is_an_error(self):
        for source in ("intake", "intake:0", "intake:1234567890", 7):
            with self.subTest(source=source):
                self.assertEqual(
                    errors_of([an_override(source=source)]),
                    [
                        f"scope_overrides {NG_ROW}: source must be 'dispatch', "
                        "'consultation:<line>', or 'intake:<line>'"
                    ],
                )


class DispatchSource(unittest.TestCase):
    def test_dispatch_passes_before_any_intake_exists(self):
        self.assertEqual(errors_of([an_override()]), [])

    def test_dispatch_is_rejected_once_a_human_intake_exists(self):
        self.assertEqual(
            errors_of([an_override()], sources=sources_over(has_intake=True)),
            [
                f"scope_overrides {NG_ROW}: source 'dispatch' is not valid "
                "once a human intake-decision exists on the log; cite "
                "intake:<line>"
            ],
        )


class IntakeSource(unittest.TestCase):
    def test_a_quoted_decision_of_a_human_intake_passes(self):
        sources = sources_over(a_human_intake())

        self.assertEqual(
            errors_of([an_override(source="intake:1")], sources=sources), []
        )

    def test_a_partial_quote_of_a_decision_passes(self):
        sources = sources_over(a_human_intake())

        self.assertEqual(
            errors_of(
                [an_override(owner_decision="Cancelling only", source="intake:1")],
                sources=sources,
            ),
            [],
        )

    def test_the_quote_must_appear_in_a_decision(self):
        sources = sources_over(a_human_intake())

        self.assertEqual(
            errors_of(
                [an_override(owner_decision="something else", source="intake:1")],
                sources=sources,
            ),
            [
                f"scope_overrides {NG_ROW}: owner_decision quote not found in "
                "intake:1's decisions"
            ],
        )

    def test_a_non_intake_line_is_rejected(self):
        sources = sources_over(a_record("prd-entry"))

        self.assertEqual(
            errors_of([an_override(source="intake:1")], sources=sources),
            [
                f"scope_overrides {NG_ROW}: intake:1 is not a human "
                "intake-decision for this req_id"
            ],
        )

    def test_an_agent_authored_intake_is_rejected(self):
        sources = sources_over(a_human_intake(author="product-requirements-expert"))

        errors = errors_of([an_override(source="intake:1")], sources=sources)

        self.assertIn("not a human intake-decision", errors[0])

    def test_an_intake_of_another_slice_is_rejected(self):
        sources = sources_over(a_human_intake(req_id=OTHER_SLICE))

        errors = errors_of([an_override(source="intake:1")], sources=sources)

        self.assertIn("not a human intake-decision for this req_id", errors[0])


class ConsultationSource(unittest.TestCase):
    def test_a_quote_from_a_human_answer_passes(self):
        sources = sources_over(a_human_response())

        self.assertEqual(
            errors_of([an_override(source="consultation:1")], sources=sources), []
        )

    def test_the_quote_must_appear_in_the_answer(self):
        sources = sources_over(a_human_response(answer="No."))

        self.assertEqual(
            errors_of([an_override(source="consultation:1")], sources=sources),
            [
                f"scope_overrides {NG_ROW}: owner_decision quote not found in "
                "consultation:1's answer"
            ],
        )

    def test_a_non_human_response_is_rejected(self):
        sources = sources_over(a_human_response(author="system-design-expert"))

        self.assertEqual(
            errors_of([an_override(source="consultation:1")], sources=sources),
            [
                f"scope_overrides {NG_ROW}: consultation:1 is not a human "
                "consultation-response for this req_id"
            ],
        )

    def test_a_response_of_another_slice_is_rejected(self):
        sources = sources_over(a_human_response(req_id=OTHER_SLICE))

        errors = errors_of([an_override(source="consultation:1")], sources=sources)

        self.assertIn("not a human consultation-response for this req_id", errors[0])

    def test_an_answer_that_is_not_text_is_rejected(self):
        sources = sources_over(a_human_response(answer=["yes"]))

        errors = errors_of([an_override(source="consultation:1")], sources=sources)

        self.assertIn("quote not found in consultation:1's answer", errors[0])


if __name__ == "__main__":
    unittest.main()
