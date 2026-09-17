#!/usr/bin/env python3
"""The differential runner: normalization masks stamps and crashes, and one tree against itself is no difference."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import ROOT, load

REPO = ROOT.parent

differential = load("differential", "differential.py")

STAMP_MASK = "T"
SOME_STAMP = "2026-06-11T10:00:00Z"
A_STAMPED_LINE = f'{{"type": "build-pass", "ts": "{SOME_STAMP}"}}'
A_TRACEBACK = "Traceback (most recent call last):\n  File x\nValueError: boom\n"
A_LABEL = "ledger 1 route"


class Normalization(unittest.TestCase):
    def test_a_stamped_timestamp_is_masked(self):
        self.assertEqual(
            differential.normalize(A_STAMPED_LINE),
            A_STAMPED_LINE.replace(SOME_STAMP, STAMP_MASK),
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
        baseline = differential.Outcome(0, "a", "")
        candidate = differential.Outcome(1, "b", "err")
        difference = differential.Difference(A_LABEL, baseline, candidate)

        text = differential.report(difference)

        self.assertIn(f"DIFF {A_LABEL}", text)
        self.assertIn(f"baseline:  rc={baseline.code}", text)
        self.assertIn(f"candidate: rc={candidate.code}", text)


if __name__ == "__main__":
    unittest.main()
