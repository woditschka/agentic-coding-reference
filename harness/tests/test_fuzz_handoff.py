#!/usr/bin/env python3
"""Tests for fuzz-handoff.py (stdlib only).

Run: python3 harness/tests/test_fuzz_handoff.py

Pins the fuzz's contract:
  1. A seed reproduces its ledgers, so a difference can be replayed.
  2. Every record carries its type and a generator covers every known kind.
  3. A tree fuzzed against itself yields no difference; a bad baseline is a
     usage error.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import ROOT, load

REPO = ROOT.parent

fuzz = load("fuzz_handoff", "fuzz-handoff.py")
differential = load("differential", "differential.py")

SOME_SEED = 7
SOME_LINE = 3


class Reproducibility(unittest.TestCase):
    def test_the_same_seed_yields_the_same_ledgers(self):
        first = [fuzz.Generator(SOME_SEED).ledger() for _ in range(3)]
        second = [fuzz.Generator(SOME_SEED).ledger() for _ in range(3)]

        self.assertEqual(first, second)

    def test_different_seeds_yield_different_ledgers(self):
        self.assertNotEqual(
            [fuzz.Generator(1).ledger() for _ in range(5)],
            [fuzz.Generator(2).ledger() for _ in range(5)],
        )


class Records(unittest.TestCase):
    def test_every_known_kind_has_a_field_generator(self):
        self.assertEqual(set(fuzz._FIELDS), set(fuzz.KINDS))

    def test_a_record_carries_its_kind(self):
        raw = fuzz.Generator(SOME_SEED).record("build-pass", SOME_LINE)

        self.assertEqual(raw["type"], "build-pass")

    def test_a_ledger_is_json_lines_with_possible_damage(self):
        text = fuzz.Generator(SOME_SEED).ledger()

        for line in text.replace("\r\n", "\n").split("\n"):
            if line and line != "not json":
                json.loads(line)

    def test_a_candidate_names_its_type_argument(self):
        record_type, stdin = fuzz.Generator(SOME_SEED).candidate()

        self.assertIn(record_type, fuzz.KINDS)
        self.assertIsInstance(stdin, str)


class Comparison(unittest.TestCase):
    def test_a_tree_against_itself_yields_no_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            generator = fuzz.Generator(SOME_SEED)
            trees = differential.Trees(REPO, REPO)

            self.assertEqual(fuzz.compare_ledger(generator, 0, trees, Path(tmp)), [])

    def test_a_tree_without_the_entry_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(fuzz.main(["fuzz-handoff.py", "--baseline", tmp]), 2)


if __name__ == "__main__":
    unittest.main()
