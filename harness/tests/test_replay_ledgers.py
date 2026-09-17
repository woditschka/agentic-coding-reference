#!/usr/bin/env python3
"""The ledger replay: every prefix in path order, and a tree replayed against itself yields no difference."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import ROOT, load

REPO = ROOT.parent

replay = load("replay_ledgers", "replay-ledgers.py")
differential = load("differential", "differential.py")

USAGE_EXIT = 2
A_LINE = '{"type": "prd-entry", "req_id": "REQ-A-001", "author": "product-requirements-expert"}'
ANOTHER_LINE = '{"type": "design-block", "req_id": "REQ-A-001", "verdict": "covered"}'


def a_runs_directory(tmp):
    runs = Path(tmp) / "runs"
    for version, name in (
        ("v0.4.1", "b-task"),
        ("v0.4.1", "a-task"),
        ("v0.3.0", "z-task"),
    ):
        folder = runs / version / name
        folder.mkdir(parents=True)
        (folder / "handoff.jsonl").write_text(A_LINE + "\n", encoding="utf-8")
    return runs


class Prefixes(unittest.TestCase):
    def test_every_prefix_is_yielded_newline_terminated(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "handoff.jsonl"
            ledger.write_text(A_LINE + "\n" + ANOTHER_LINE, encoding="utf-8")

            self.assertEqual(
                list(replay.prefixes(ledger)),
                [
                    (1, (A_LINE + "\n").encode()),
                    (2, (A_LINE + "\n" + ANOTHER_LINE + "\n").encode()),
                ],
            )

    def test_an_empty_ledger_has_no_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "handoff.jsonl"
            ledger.write_bytes(b"")

            self.assertEqual(list(replay.prefixes(ledger)), [])


class Ledgers(unittest.TestCase):
    def test_run_folders_are_found_in_path_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = a_runs_directory(tmp)

            found = [str(p.relative_to(runs)) for p in replay.ledgers(runs)]

            self.assertEqual(
                found,
                [
                    "v0.3.0/z-task/handoff.jsonl",
                    "v0.4.1/a-task/handoff.jsonl",
                    "v0.4.1/b-task/handoff.jsonl",
                ],
            )


class Replay(unittest.TestCase):
    def test_a_tree_against_itself_yields_no_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "handoff.jsonl"
            ledger.write_text(A_LINE + "\n" + ANOTHER_LINE + "\n", encoding="utf-8")
            trees = differential.Trees(REPO, REPO)

            self.assertEqual(replay.replay(ledger, trees, Path(tmp)), [])

    def test_a_tree_without_the_entry_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                replay.main(["replay-ledgers.py", "--baseline", tmp]), USAGE_EXIT
            )

    def test_an_empty_runs_directory_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = replay.main(
                ["replay-ledgers.py", "--baseline", str(REPO), "--ledgers", tmp]
            )

            self.assertEqual(code, USAGE_EXIT)


if __name__ == "__main__":
    unittest.main()
