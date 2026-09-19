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
MAX_PLAN_ATTEMPTS = 60


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


def a_workspace_project():
    generator = fuzz.Generator(SOME_SEED)
    while True:
        project = generator.project()
        if project.members:
            return project


class Workspaces(unittest.TestCase):
    def test_the_single_repository_switch_generates_no_members(self):
        generator = fuzz.Generator(SOME_SEED, workspaces=False)
        projects = [generator.project() for _ in range(MAX_PLAN_ATTEMPTS)]

        self.assertTrue(all(not p.members for p in projects))

    def test_some_projects_declare_members_and_the_layout_classifies_their_paths(self):
        project = a_workspace_project()

        self.assertIn("[workspace.members]", project.layout)
        for member in project.members:
            self.assertIn(f'path = "{member.path}"', project.layout)
            self.assertIn(f'"{member.path}/', project.layout)

    def test_present_members_are_built_beside_the_repository_and_absent_ones_are_not(
        self,
    ):
        project = a_workspace_project()
        with tempfile.TemporaryDirectory() as tmp:
            fixture = fuzz.build_repository(project, Path(tmp) / "repo")

            for member in project.members:
                built = fuzz.member_directory(fixture.path, member)
                self.assertEqual((built / ".git").is_dir(), member.present)
                self.assertEqual(member.name in fixture.member_trees, member.present)

    def test_the_installed_layout_locates_the_members_by_the_fixtures_name(self):
        project = a_workspace_project()
        with tempfile.TemporaryDirectory() as tmp:
            fixture = fuzz.build_repository(project, Path(tmp) / "repo")
            copy = Path(tmp) / "copy"
            copy.mkdir()
            fuzz.install_runtime(REPO, project, copy, fixture.path.name)

            layout = (copy / "scripts" / "layout.toml").read_text()
            self.assertNotIn(fuzz.MEMBER_ROOT, layout)
            self.assertIn('path = "../repo-', layout)

    def test_a_workspace_run_records_the_member_map_in_its_plan(self):
        generator = fuzz.Generator(SOME_SEED)
        for attempt in range(MAX_PLAN_ATTEMPTS):
            project = generator.project()
            if not project.members:
                continue
            with tempfile.TemporaryDirectory() as tmp:
                fixture = fuzz.build_repository(project, Path(tmp) / "repo")
                outcomes = dict(
                    fuzz.run_project(
                        REPO, project, fixture, Path(tmp) / f"copy-{attempt}"
                    )
                )
                if outcomes["review-plan"].code != 0:
                    continue
                ledger = outcomes["ledger"].stdout
                for member in project.members:
                    self.assertIn(f'"{member.name}": {{"path": "../repo-', ledger)
                return
        self.fail("no workspace project produced a review plan")


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
