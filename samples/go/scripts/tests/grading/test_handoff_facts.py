"""The grading engine's ledger reader: the history facts and how the read degrades."""

import json
import tempfile
import unittest
from pathlib import Path

from grading import config, handoff_facts

SOME_REQ_ID = "REQ-AB-001"
ANOTHER_REQ_ID = "REQ-ZZ-009"
FLOOR = tuple(config.REVIEWERS)
CODE_REVIEWER = FLOOR[0]
EXTRA_REVIEWER = "perf-reviewer"
AN_ESCAPE_BYTE = "\x1b[31m"


def bind_log(case, data):
    """Point the gateway at a temporary log holding the records or the raw text for the test's lifetime."""
    tmp = tempfile.TemporaryDirectory()
    case.addCleanup(tmp.cleanup)
    log = Path(tmp.name) / "handoff.jsonl"
    if isinstance(data, bytes):
        log.write_bytes(data)
    elif isinstance(data, str):
        with log.open("w", encoding="utf-8", newline="") as handle:
            handle.write(data)
    else:
        log.write_text("".join(json.dumps(r) + "\n" for r in data), encoding="utf-8")
    saved = handoff_facts.HANDOFF
    handoff_facts.HANDOFF = log
    case.addCleanup(setattr, handoff_facts, "HANDOFF", saved)
    return log


def a_record(record_type, **fields):
    return {"type": record_type, "req_id": SOME_REQ_ID, **fields}


def a_feedback(author=CODE_REVIEWER, verdict="approved"):
    return a_record("review-feedback", author=author, verdict=verdict)


def a_block(**fields):
    return a_record(
        "design-block",
        **{"verdict": "covered", "implementation_effort": "routine", **fields},
    )


def facts(case, records):
    bind_log(case, records)
    return handoff_facts.read_handoff(SOME_REQ_ID)


class BuildPassed(unittest.TestCase):
    """Whether a build-pass post-dates every build-failure of the slice."""

    def test_no_build_pass_is_unknown(self):
        self.assertIsNone(facts(self, [a_record("build-failure")])["build_passed"])

    def test_a_pass_after_a_failure_is_true(self):
        records = [a_record("build-failure"), a_record("build-pass")]

        self.assertTrue(facts(self, records)["build_passed"])

    def test_a_failure_after_the_pass_is_false(self):
        records = [a_record("build-pass"), a_record("build-failure")]

        self.assertFalse(facts(self, records)["build_passed"])


class BuildRetries(unittest.TestCase):
    """The build-failures since the latest design-block."""

    def test_failures_before_the_latest_design_block_are_not_counted(self):
        records = [
            a_record("build-failure"),
            a_block(),
            a_record("build-failure"),
            a_record("build-failure"),
        ]

        self.assertEqual(facts(self, records)["build_retries"], 2)

    def test_without_a_design_block_every_failure_counts(self):
        records = [a_record("build-failure"), a_record("build-pass")]

        self.assertEqual(facts(self, records)["build_retries"], 1)

    def test_consultations_are_counted(self):
        records = [a_record("consultation-request"), a_record("consultation-request")]

        self.assertEqual(facts(self, records)["consultations"], 2)


class ReviewerVerdicts(unittest.TestCase):
    """The latest verdict per review author over the floor's keys."""

    def test_an_extra_reviewer_s_verdict_enters_the_row(self):
        records = [a_feedback(), a_feedback(EXTRA_REVIEWER, "blocked")]

        verdicts = facts(self, records)["reviewers"]

        self.assertEqual(verdicts[CODE_REVIEWER], "approved")
        self.assertEqual(verdicts[EXTRA_REVIEWER], "blocked")

    def test_the_floor_is_present_and_null_when_silent(self):
        verdicts = facts(self, [a_feedback(EXTRA_REVIEWER)])["reviewers"]

        self.assertEqual(verdicts, {**dict.fromkeys(FLOOR), EXTRA_REVIEWER: "approved"})

    def test_the_last_verdict_per_author_wins(self):
        records = [a_feedback(EXTRA_REVIEWER, "blocked"), a_feedback(EXTRA_REVIEWER)]

        self.assertEqual(facts(self, records)["reviewers"][EXTRA_REVIEWER], "approved")

    def test_no_review_at_all_is_null(self):
        self.assertIsNone(facts(self, [a_record("build-pass")])["reviewers"])


class PlanRoster(unittest.TestCase):
    """The latest review-plan's roster, the reviewers the pass dispatched."""

    def test_the_latest_plan_s_roster_enters_the_row(self):
        records = [
            a_record("build-pass"),
            a_record("review-plan", risk="low", roster=[FLOOR[3]]),
        ]

        self.assertEqual(facts(self, records)["review_roster"], [FLOOR[3]])

    def test_a_plan_without_a_list_roster_reads_as_none(self):
        records = [a_record("review-plan", risk="gray", roster="x")]

        self.assertIsNone(facts(self, records)["review_roster"])

    def test_no_plan_reads_as_none(self):
        self.assertIsNone(facts(self, [a_record("build-pass")])["review_roster"])


class DesignRevisions(unittest.TestCase):
    """A superseding design-block counts when it could void review history."""

    def revisions(self, records):
        return facts(self, records)["design_revisions"]

    def test_a_pre_build_correction_of_the_record_is_not_a_revision(self):
        records = [
            a_block(),
            a_record("build-failure", failed_check="autofix-audit"),
            a_block(supersedes_record_at=1),
            a_record("build-pass"),
        ]

        self.assertEqual(self.revisions(records), 0)

    def test_a_post_build_supersession_is_a_revision(self):
        records = [a_block(), a_record("build-pass"), a_block(supersedes_record_at=1)]

        self.assertEqual(self.revisions(records), 1)

    def test_a_pre_build_verdict_change_is_a_revision(self):
        records = [
            a_block(verdict="minor"),
            a_block(verdict="new", supersedes_record_at=1),
            a_record("build-pass"),
        ]

        self.assertEqual(self.revisions(records), 1)

    def test_a_pointer_outside_the_slice_fails_closed_to_a_revision(self):
        records = [
            {"type": "design-block", "req_id": ANOTHER_REQ_ID, "verdict": "covered"},
            a_block(supersedes_record_at=1),
            a_record("build-pass"),
        ]

        self.assertEqual(self.revisions(records), 1)


class LedgerDegradation(unittest.TestCase):
    """The readers degrade to null facts or an empty slice; a bad line is skipped, never fatal."""

    def test_a_missing_log_reads_as_null_facts_and_no_records(self):
        log = bind_log(self, [])
        log.unlink()

        self.assertEqual(
            handoff_facts.read_handoff(SOME_REQ_ID), handoff_facts.NULL_FACTS
        )
        self.assertEqual(handoff_facts.load_records(SOME_REQ_ID), [])

    def test_an_empty_log_reads_as_null_facts(self):
        bind_log(self, "")

        self.assertEqual(
            handoff_facts.read_handoff(SOME_REQ_ID), handoff_facts.NULL_FACTS
        )

    def test_invalid_utf8_reads_as_an_unreadable_log(self):
        bind_log(self, b"\xff\xfe not utf-8\n")

        self.assertEqual(
            handoff_facts.read_handoff(SOME_REQ_ID), handoff_facts.NULL_FACTS
        )
        self.assertEqual(handoff_facts.load_records(SOME_REQ_ID), [])

    def test_a_duplicate_key_line_is_skipped(self):
        bind_log(
            self,
            f'{{"req_id": "{SOME_REQ_ID}", "note": "a", "note": "b"}}\n'
            f'{{"type": "build-pass", "req_id": "{SOME_REQ_ID}"}}\n',
        )

        records = handoff_facts.load_records(SOME_REQ_ID)

        self.assertEqual([r.get("type") for _, r in records], ["build-pass"])

    def test_a_nan_line_is_skipped(self):
        bind_log(
            self,
            f'{{"type": "build-failure", "req_id": "{SOME_REQ_ID}", "retry": NaN}}\n'
            f'{{"type": "build-pass", "req_id": "{SOME_REQ_ID}"}}\n',
        )

        records = handoff_facts.load_records(SOME_REQ_ID)

        self.assertEqual([r.get("type") for _, r in records], ["build-pass"])

    def test_a_non_object_line_is_skipped(self):
        bind_log(self, f'123\n{{"type": "build-pass", "req_id": "{SOME_REQ_ID}"}}\n')

        records = handoff_facts.load_records(SOME_REQ_ID)

        self.assertEqual([r.get("type") for _, r in records], ["build-pass"])

    def test_a_truncated_last_line_is_still_read(self):
        bind_log(self, f'{{"type": "build-pass", "req_id": "{SOME_REQ_ID}"}}')

        self.assertEqual(
            [r.get("type") for _, r in handoff_facts.load_records(SOME_REQ_ID)],
            ["build-pass"],
        )

    def test_crlf_endings_keep_the_line_numbers(self):
        bind_log(
            self,
            f'{{"type": "build-pass", "req_id": "{SOME_REQ_ID}"}}\r\n'
            f'{{"type": "build-failure", "req_id": "{SOME_REQ_ID}"}}\r\n',
        )

        self.assertEqual(
            [no for no, _ in handoff_facts.load_records(SOME_REQ_ID)], [1, 2]
        )

    def test_control_bytes_in_a_field_pass_through_untouched(self):
        bind_log(self, [a_record("build-pass", author=f"{AN_ESCAPE_BYTE}root")])

        ((_no, record),) = handoff_facts.load_records(SOME_REQ_ID)

        self.assertEqual(record["author"], f"{AN_ESCAPE_BYTE}root")

    def test_another_slice_s_records_are_not_read(self):
        bind_log(self, [{"type": "build-pass", "req_id": ANOTHER_REQ_ID}])

        self.assertEqual(handoff_facts.load_records(SOME_REQ_ID), [])


if __name__ == "__main__":
    unittest.main()
