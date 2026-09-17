"""The grading fuzz: a seed reproduces its projects, every stack has its tables, and a tree fuzzed against itself yields no difference."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _loader import ROOT, load

REPO = ROOT.parent

fuzz = load("fuzz_grading", "fuzz-grading.py")
differential = load("differential", "differential.py")

USAGE_EXIT = 2
FIRST_PROJECT = 0
SOME_SEED = 7
ANOTHER_SEED = 8
SOME_COUNT = 3


class Reproducibility(unittest.TestCase):
    def test_the_same_seed_yields_the_same_projects(self):
        first = [fuzz.Generator(SOME_SEED).project() for _ in range(SOME_COUNT)]
        second = [fuzz.Generator(SOME_SEED).project() for _ in range(SOME_COUNT)]

        self.assertEqual(first, second)

    def test_different_seeds_yield_different_projects(self):
        self.assertNotEqual(
            [fuzz.Generator(SOME_SEED).project() for _ in range(SOME_COUNT)],
            [fuzz.Generator(ANOTHER_SEED).project() for _ in range(SOME_COUNT)],
        )


class Projects(unittest.TestCase):
    def test_every_stack_has_a_path_pool_a_classification_and_a_module_table(self):
        for table in (fuzz.PATHS, fuzz.CLASSIFICATION, fuzz.MODULES, fuzz.GATE):
            self.assertEqual(set(table), set(fuzz.STACKS))

    def test_a_project_changes_at_least_one_file(self):
        project = fuzz.Generator(SOME_SEED).project()

        self.assertTrue(project.changed_files)
        self.assertIn(project.stack, fuzz.STACKS)

    def test_the_repository_carries_the_change_and_the_ledger(self):
        project = fuzz.Generator(SOME_SEED).project()
        with tempfile.TemporaryDirectory() as tmp:
            fixture = fuzz.build_repository(project, Path(tmp) / "repo")

            self.assertRegex(fixture.base, r"^[0-9a-f]{40,64}$")
            self.assertRegex(fixture.base_tree, r"^[0-9a-f]{40,64}$")
            self.assertTrue((fixture.path / ".scratch" / "handoff.jsonl").is_file())
            self.assertNotIn(
                "BASE_TREE", (fixture.path / ".scratch" / "handoff.jsonl").read_text()
            )


class Comparison(unittest.TestCase):
    def test_a_tree_against_itself_yields_no_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            generator = fuzz.Generator(SOME_SEED)
            trees = differential.Trees(REPO, REPO)

            self.assertEqual(
                fuzz.compare_project(generator, FIRST_PROJECT, trees, Path(tmp)), []
            )

    def test_a_tree_without_the_entry_is_a_usage_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                fuzz.main(["fuzz-grading.py", "--baseline", tmp]), USAGE_EXIT
            )


if __name__ == "__main__":
    unittest.main()
