#!/usr/bin/env python3
"""The retired-paths manifest: its grammar, the coverage rule, the produced-set derivation, and the append-only update."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load

retired_paths = load("retired_paths", "retired_paths.py")

SEED_FLOOR = 24
SOME_TAG = "v0.0.1"
SOME_LABEL = "test"


class ParseManifest(unittest.TestCase):
    def test_comments_and_blanks_are_skipped(self):
        entries, problems = retired_paths.parse_manifest(
            "# header\n\nscripts/a.py\n.claude/skills/x/\n"
        )
        self.assertEqual(entries, ["scripts/a.py", ".claude/skills/x/"])
        self.assertEqual(problems, [])

    def test_a_duplicate_is_a_problem(self):
        entries, problems = retired_paths.parse_manifest("scripts/a.py\nscripts/a.py\n")
        self.assertEqual(entries, ["scripts/a.py"])
        self.assertEqual(len(problems), 1)
        self.assertIn("duplicate", problems[0])

    def test_absolute_parent_dot_and_spaced_entries_are_problems_and_excluded(self):
        for entry in (
            "/etc/passwd",
            "a/../b.py",
            ".",
            "./",
            "scripts/x.py # inline comment",
            "scripts/two words.py",
        ):
            with self.subTest(entry=entry):
                entries, problems = retired_paths.parse_manifest(entry + "\n")
                self.assertEqual(entries, [])
                self.assertTrue(problems)

    def test_surrounding_whitespace_is_a_problem(self):
        _, problems = retired_paths.parse_manifest("  scripts/a.py\n")
        self.assertTrue(problems)


class Covered(unittest.TestCase):
    ENTRIES = ("scripts/old.py", ".claude/skills/doc-review/")

    def test_an_exact_file_entry_covers_the_file(self):
        self.assertTrue(retired_paths.covered("scripts/old.py", self.ENTRIES))

    def test_a_directory_entry_covers_its_contents(self):
        self.assertTrue(
            retired_paths.covered(".claude/skills/doc-review/SKILL.md", self.ENTRIES)
        )

    def test_an_extended_name_or_a_sibling_is_not_covered(self):
        for path in (
            "scripts/old.pyc",
            ".claude/skills/doc-reviewer/SKILL.md",
            "scripts/new.py",
        ):
            with self.subTest(path=path):
                self.assertFalse(retired_paths.covered(path, self.ENTRIES))


class ConsumerPathMapping(unittest.TestCase):
    def test_core_and_stack_files_map_to_consumer_paths(self):
        self.assertEqual(
            retired_paths._consumer_path("harness/core/scripts/handoff.py"),
            "scripts/handoff.py",
        )
        self.assertEqual(
            retired_paths._consumer_path(
                "harness/stacks/go/.claude/skills/test-review/SKILL.md"
            ),
            ".claude/skills/test-review/SKILL.md",
        )

    def test_paths_outside_the_layers_map_to_none(self):
        for path in (
            "harness/init/core/CLAUDE.md",
            "docs/adr/README.md",
            "harness/stacks/go",
        ):
            with self.subTest(path=path):
                self.assertIsNone(retired_paths._consumer_path(path))


class LiveManifest(unittest.TestCase):
    def test_the_live_manifest_is_well_formed_and_holds_the_seed_floor(self):
        # The manifest is append-only, so the seed's count never shrinks.
        entries = retired_paths.read_manifest()
        self.assertGreaterEqual(len(entries), SEED_FLOOR)

    def test_the_worktree_produced_set_is_consumer_relative(self):
        produced = retired_paths.produced_paths(None)
        self.assertIn("scripts/handoff.py", produced)
        self.assertIn(".claude/skills/handoff-routing/SKILL.md", produced)
        self.assertFalse(any(p.startswith("harness/") for p in produced))


class ProducedAtRef(unittest.TestCase):
    LS_TREE = (
        "100644 blob aaaa\tharness/core/scripts/handoff.py\n"
        "120000 blob bbbb\tharness/core/scripts/link.py\n"
        "100644 blob cccc\tharness/core/scripts/__pycache__/x.pyc\n"
        "100644 blob dddd\tharness/core/scripts/stale.pyc\n"
        "100644 blob eeee\tharness/stacks/go/.claude/skills/x/SKILL.md\n"
        "040000 tree ffff\tharness/stacks/go\n"
    )

    def test_the_ls_tree_side_mirrors_the_worktree_exclusions(self):
        # Symlinks, cache dirs, and .pyc never materialize; counting them as
        # produced at a tag would manufacture retirements the append-only
        # manifest keeps forever.
        fake = subprocess.CompletedProcess([], 0, stdout=self.LS_TREE, stderr="")
        with mock.patch.object(retired_paths.subprocess, "run", return_value=fake):
            produced = retired_paths.produced_paths(SOME_TAG)
        self.assertEqual(
            produced,
            {"scripts/handoff.py", ".claude/skills/x/SKILL.md"},
        )

    def test_a_dash_prefixed_or_empty_ref_is_refused(self):
        for ref in ("--output=/tmp/x", "-v", ""):
            with self.subTest(ref=ref), self.assertRaises(SystemExit):
                retired_paths.produced_paths(ref)


class Update(unittest.TestCase):
    def test_only_uncovered_paths_are_appended_and_a_rerun_appends_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "retired-paths.txt"
            manifest.write_text("scripts/old.py\n")
            with mock.patch.object(
                retired_paths,
                "retired_since",
                return_value={"scripts/old.py", "scripts/gone.py"},
            ):
                appended = retired_paths.update(SOME_TAG, SOME_LABEL, manifest)
                self.assertEqual(appended, ["scripts/gone.py"])
                text = manifest.read_text()
                self.assertIn(f"# retired after {SOME_TAG} ({SOME_LABEL})", text)
                self.assertEqual(
                    retired_paths.read_manifest(manifest),
                    ["scripts/old.py", "scripts/gone.py"],
                )
                self.assertEqual(
                    retired_paths.update(SOME_TAG, SOME_LABEL, manifest), []
                )


if __name__ == "__main__":
    unittest.main()
