#!/usr/bin/env python3
"""The handoff fuzz: a seed reproduces its ledgers, every kind generates, and a tree fuzzed against itself yields no difference."""

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

USAGE_EXIT = 2
DAMAGED_LINE = "not json"
FIRST_LEDGER = 0
SOME_SEED = 7
ANOTHER_SEED = 8
SOME_LINE = 3
SOME_KIND = "build-pass"
SOME_COUNT = 3


class Reproducibility(unittest.TestCase):
    def test_the_same_seed_yields_the_same_ledgers(self):
        first = [fuzz.Generator(SOME_SEED).ledger() for _ in range(SOME_COUNT)]
        second = [fuzz.Generator(SOME_SEED).ledger() for _ in range(SOME_COUNT)]

        self.assertEqual(first, second)

    def test_different_seeds_yield_different_ledgers(self):
        self.assertNotEqual(
            [fuzz.Generator(SOME_SEED).ledger() for _ in range(SOME_COUNT)],
            [fuzz.Generator(ANOTHER_SEED).ledger() for _ in range(SOME_COUNT)],
        )


class Records(unittest.TestCase):
    def test_every_known_kind_has_a_field_generator(self):
        self.assertEqual(set(fuzz._FIELDS), set(fuzz.KINDS))

    def test_a_record_carries_its_kind(self):
        raw = fuzz.Generator(SOME_SEED).record(SOME_KIND, SOME_LINE)

        self.assertEqual(raw["type"], SOME_KIND)

    def test_a_ledger_is_json_lines_with_possible_damage(self):
        text = fuzz.Generator(SOME_SEED).ledger()

        for line in text.replace("\r\n", "\n").split("\n"):
            if line and line != DAMAGED_LINE:
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

            self.assertEqual(
                fuzz.compare_ledger(generator, FIRST_LEDGER, trees, Path(tmp)), []
            )

    def test_a_tree_without_the_entry_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                fuzz.main(["fuzz-handoff.py", "--baseline", tmp]), USAGE_EXIT
            )


if __name__ == "__main__":
    unittest.main()
