#!/usr/bin/env python3
"""Tests for retired_paths.py (stdlib only).

Run: python3 harness/tests/test_retired_paths.py

Pins the manifest grammar (comments, duplicates, hostile shapes), the
coverage rule (exact file vs directory prefix), the consumer-path mapping the
produced-set derivation rests on, the live manifest's floor, and the update
subcommand's append-only idempotence. The git-backed derivation itself
(produced_paths at a tag) is exercised end-to-end by the battery's
retired-paths step against the real repository.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load

retired_paths = load("retired_paths", "retired_paths.py")


class ParseManifest(unittest.TestCase):
    def test_comments_and_blanks_are_skipped(self):
        entries, problems = retired_paths.parse_manifest(
            "# header\n\nscripts/a.py\n.claude/skills/x/\n"
        )
        self.assertEqual(entries, ["scripts/a.py", ".claude/skills/x/"])
        self.assertEqual(problems, [])

    def test_duplicate_is_a_problem(self):
        entries, problems = retired_paths.parse_manifest("scripts/a.py\nscripts/a.py\n")
        self.assertEqual(entries, ["scripts/a.py"])
        self.assertEqual(len(problems), 1)
        self.assertIn("duplicate", problems[0])

    def test_hostile_shapes_are_problems_and_excluded(self):
        for hostile in (
            "/etc/passwd",
            "a/../b.py",
            ".",
            "./",
            "scripts/x.py # inline comment",
            "scripts/two words.py",
        ):
            with self.subTest(hostile=hostile):
                entries, problems = retired_paths.parse_manifest(hostile + "\n")
                self.assertEqual(entries, [])
                self.assertTrue(problems)

    def test_surrounding_whitespace_is_a_problem(self):
        _, problems = retired_paths.parse_manifest("  scripts/a.py\n")
        self.assertTrue(problems)


class Covered(unittest.TestCase):
    ENTRIES = ["scripts/old.py", ".claude/skills/doc-review/"]

    def test_exact_file_entry(self):
        self.assertTrue(retired_paths.covered("scripts/old.py", self.ENTRIES))

    def test_directory_prefix_entry(self):
        self.assertTrue(
            retired_paths.covered(".claude/skills/doc-review/SKILL.md", self.ENTRIES)
        )

    def test_uncovered_paths(self):
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
    def test_live_manifest_is_well_formed_with_the_seed_floor(self):
        entries = retired_paths.read_manifest()
        # The 2026-08-20 seed holds 24 entries; the manifest is append-only,
        # so the floor never shrinks.
        self.assertGreaterEqual(len(entries), 24)

    def test_worktree_produced_set_is_consumer_relative(self):
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

    def test_ls_tree_side_mirrors_the_worktree_exclusions(self):
        # Symlinks (mode 120000), cache dirs, and .pyc never materialize, so
        # they must not count as produced at a tag — a filter asymmetry would
        # manufacture false retirements the append-only manifest keeps forever.
        import subprocess as sp

        fake = sp.CompletedProcess([], 0, stdout=self.LS_TREE, stderr="")
        with mock.patch.object(retired_paths.subprocess, "run", return_value=fake):
            produced = retired_paths.produced_paths("v0.0.1")
        self.assertEqual(
            produced,
            {"scripts/handoff.py", ".claude/skills/x/SKILL.md"},
        )

    def test_suspicious_ref_is_refused(self):
        for ref in ("--output=/tmp/x", "-v", ""):
            with self.subTest(ref=ref), self.assertRaises(SystemExit):
                retired_paths.produced_paths(ref)


class Update(unittest.TestCase):
    def test_appends_only_uncovered_paths_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            manifest = Path(td) / "retired-paths.txt"
            manifest.write_text("scripts/old.py\n")
            with mock.patch.object(
                retired_paths,
                "retired_since",
                return_value={"scripts/old.py", "scripts/gone.py"},
            ):
                appended = retired_paths.update("v0.0.1", "test", manifest)
                self.assertEqual(appended, ["scripts/gone.py"])
                text = manifest.read_text()
                self.assertIn("# retired after v0.0.1 (test)", text)
                self.assertEqual(
                    retired_paths.read_manifest(manifest),
                    ["scripts/old.py", "scripts/gone.py"],
                )
                self.assertEqual(retired_paths.update("v0.0.1", "test", manifest), [])


if __name__ == "__main__":
    unittest.main()
