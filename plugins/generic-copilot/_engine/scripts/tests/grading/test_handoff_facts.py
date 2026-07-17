"""Tests for grading.handoff_facts — the handoff-log gateway.

Every class binds a synthetic log by patching handoff_facts.HANDOFF, so the
suite is stack-agnostic and runs everywhere.

Run (from the scripts dir): python3 -m unittest tests.grading.test_handoff_facts
Stdlib only.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from grading import config, handoff_facts


class TestReadHandoffReviewers(unittest.TestCase):
    """The reviewers row starts from the mandatory floor (always present, null
    when silent) and adds any other review-feedback author — a declared extra
    reviewer's verdict must never be dropped from the feature row."""

    def _bind_log(self, records):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        log = tmp / "handoff.jsonl"
        log.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        saved = handoff_facts.HANDOFF
        handoff_facts.HANDOFF = log
        self.addCleanup(lambda: setattr(handoff_facts, "HANDOFF", saved))

    def _read(self, records):
        self._bind_log(records)
        return handoff_facts.read_handoff("REQ-AB-001")

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
        for who in config.REVIEWERS:
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

    def test_read_handoff_surfaces_plan_roster(self):
        # The latest review-plan's roster enters the row, so a floor reviewer
        # silent because a focused plan scoped it out is not misread as a hedge.
        self._bind_log(
            [
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
        )
        row = handoff_facts.read_handoff("REQ-AB-001")
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
        saved = handoff_facts.HANDOFF
        handoff_facts.HANDOFF = log
        self.addCleanup(lambda: setattr(handoff_facts, "HANDOFF", saved))

    def test_read_handoff_nulls_on_invalid_utf8(self):
        self._bind(b"\xff\xfe not utf-8\n")
        row = handoff_facts.read_handoff(self.REQ)
        self.assertIsNone(row["build_passed"])
        self.assertIsNone(row["reviewers"])

    def test_load_records_empty_on_invalid_utf8(self):
        self._bind(b"\xff\xfe not utf-8\n")
        self.assertEqual(handoff_facts.load_records(self.REQ), [])

    def test_duplicate_key_line_skipped_not_last_wins(self):
        # handoff.py rejects duplicate keys; plain json.loads would keep the last
        # value and include the line. The reader must skip it instead.
        self._bind(
            '{"req_id": "REQ-AB-001", "note": "a", "note": "b"}\n'
            '{"type": "build-pass", "req_id": "REQ-AB-001"}\n'
        )
        recs = handoff_facts.load_records(self.REQ)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0][1].get("type"), "build-pass")

    def test_non_object_line_skipped_not_crash(self):
        # A bare JSON value (123) parses but is not a record; skip it rather
        # than call .get on an int.
        self._bind('123\n{"type": "build-pass", "req_id": "REQ-AB-001"}\n')
        recs = handoff_facts.load_records(self.REQ)
        self.assertEqual([r.get("type") for _, r in recs], ["build-pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
