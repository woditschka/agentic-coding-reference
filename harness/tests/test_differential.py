#!/usr/bin/env python3
"""Tests for differential.py (stdlib only).

Run: python3 harness/tests/test_differential.py

Pins the runner's contract:
  1. Normalization masks stamped timestamps and collapses a crash to its
     exception line, so two trees that fail alike agree.
  2. A command through one tree twice is no difference; a tree without the
     handoff entry is refused.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import ROOT, load

REPO = ROOT.parent

differential = load("differential", "differential.py")

A_STAMPED_LINE = '{"type": "build-pass", "ts": "2026-06-11T10:00:00Z"}'
A_TRACEBACK = "Traceback (most recent call last):\n  File x\nValueError: boom\n"


class Normalization(unittest.TestCase):
    def test_a_stamped_timestamp_is_masked(self):
        self.assertEqual(
            differential.normalize(A_STAMPED_LINE),
            '{"type": "build-pass", "ts": "T"}',
        )

    def test_a_traceback_collapses_to_its_exception_line(self):
        self.assertEqual(differential.normalize(A_TRACEBACK), "CRASH ValueError: boom")

    def test_plain_text_passes_through(self):
        self.assertEqual(
            differential.normalize("appended at line 1\n"), "appended at line 1\n"
        )


class Comparison(unittest.TestCase):
    def test_one_tree_against_itself_is_no_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "handoff.jsonl"
            log.write_text(A_STAMPED_LINE + "\n", encoding="utf-8")
            trees = differential.Trees(REPO, REPO)

            self.assertIsNone(
                differential.compare("route", trees, ["route", "--file", str(log)])
            )

    def test_a_tree_without_the_entry_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            differential.resolve_tree(tmp)

    def test_the_reference_resolves_as_a_tree(self):
        self.assertEqual(differential.resolve_tree(str(REPO)), REPO.resolve())

    def test_a_report_names_the_label_and_both_outcomes(self):
        difference = differential.Difference(
            "ledger 1 route",
            differential.Outcome(0, "a", ""),
            differential.Outcome(1, "b", "err"),
        )

        text = differential.report(difference)

        self.assertIn("DIFF ledger 1 route", text)
        self.assertIn("baseline:  rc=0", text)
        self.assertIn("candidate: rc=1", text)


if __name__ == "__main__":
    unittest.main()
