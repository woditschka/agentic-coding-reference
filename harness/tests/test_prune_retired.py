#!/usr/bin/env python3
"""Tests for marketplace/prune-retired.py (stdlib only).

Run: python3 harness/tests/test_prune_retired.py

The pruner is the one consumer-side script that deletes files, so every
safety property is pinned here: the engine-sliver deletion boundary, the
symlink containment rule, the produced/extension/agents guards, the
unparseable-layout and missing-registry fail-safes, dry-run inertness,
control-character stripping, and empty-dir cleanup. Each case runs the real
script as a subprocess against a scratch plugin cache + target, the way
setup.sh runs it — the bundled-registry import resolves exactly as shipped.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import ROOT

SCRIPT = ROOT / "marketplace" / "prune-retired.py"

LAYOUT = '[harness]\nchannel = "marketplace"\nextensions = [%s]\n'


def make_fixture(
    tmp: Path,
    manifest: str,
    extensions: str = "",
    layout: str | None = None,
    with_registry: bool = True,
) -> tuple[Path, Path]:
    plugin = tmp / "plugin"
    target = tmp / "target"
    (plugin / "_engine" / "scripts").mkdir(parents=True)
    (plugin / "_engine" / "scripts" / "handoff.py").write_text("# engine\n")
    (plugin / "retired-paths.txt").write_text(manifest)
    if with_registry:
        (plugin / "registry.py").write_text(
            'ENGINE_SLIVER = ("scripts", "schemas/scratch", ".claude/templates")\n'
        )
    (target / "scripts").mkdir(parents=True)
    (target / "scripts" / "layout.toml").write_text(
        layout if layout is not None else LAYOUT % extensions
    )
    return plugin, target


def run_prune(plugin: Path, target: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), str(plugin), str(target), *flags],
        capture_output=True,
        text=True,
        cwd=plugin.parent,
        check=False,
    )


class SliverBoundary(unittest.TestCase):
    def test_sliver_path_is_removed_and_outside_path_only_reported(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(
                Path(td), "scripts/score-change.py\n.claude/skills/doc-review/\n"
            )
            (target / "scripts" / "score-change.py").write_text("stale\n")
            skill = target / ".claude" / "skills" / "doc-review"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("old\n")
            result = run_prune(plugin, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((target / "scripts" / "score-change.py").exists())
            self.assertTrue((skill / "SKILL.md").exists(), "outside-sliver deleted")
            self.assertIn("not auto-removed", result.stdout)
            self.assertIn("removed scripts/score-change.py (retired)", result.stdout)
            self.assertNotIn("recoverable", result.stdout)

    def test_missing_bundled_registry_reports_only(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(
                Path(td), "scripts/score-change.py\n", with_registry=False
            )
            (target / "scripts" / "score-change.py").write_text("stale\n")
            result = run_prune(plugin, target)
            self.assertEqual(result.returncode, 0)
            self.assertTrue((target / "scripts" / "score-change.py").exists())
            self.assertIn("registry unreadable", result.stderr)


class SymlinkContainment(unittest.TestCase):
    def test_directory_entry_never_deletes_through_a_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            plugin, target = make_fixture(tmp, "schemas/scratch/\n")
            outside = tmp / "outside"
            outside.mkdir()
            (outside / "notes.md").write_text("precious\n")
            (target / "schemas").mkdir()
            (target / "schemas" / "scratch").symlink_to(outside)
            result = run_prune(plugin, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((outside / "notes.md").exists(), "symlink escape")

    def test_file_behind_symlinked_parent_is_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            plugin, target = make_fixture(tmp, "scripts/gone.py\n")
            outside = tmp / "real-scripts"
            outside.mkdir()
            (outside / "gone.py").write_text("precious\n")
            # replace the scripts dir with a symlink to outside
            import shutil

            shutil.rmtree(target / "scripts")
            (target / "scripts").symlink_to(outside)
            result = run_prune(plugin, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((outside / "gone.py").exists(), "symlinked parent escape")
            self.assertIn("resolves outside the project", result.stdout)


class Guards(unittest.TestCase):
    def test_produced_path_wins_over_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(Path(td), "scripts/handoff.py\n")
            (target / "scripts" / "handoff.py").write_text("current\n")
            run_prune(plugin, target)
            self.assertTrue((target / "scripts" / "handoff.py").exists())

    def test_declared_extension_is_kept_and_reported(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(
                Path(td),
                "scripts/cc_accounting.py\n",
                extensions='"scripts/cc_accounting.py"',
            )
            (target / "scripts" / "cc_accounting.py").write_text("mine\n")
            result = run_prune(plugin, target)
            self.assertTrue((target / "scripts" / "cc_accounting.py").exists())
            self.assertIn("kept scripts/cc_accounting.py", result.stdout)

    def test_unparseable_layout_prunes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(
                Path(td), "scripts/score-change.py\n", layout="[harness\nbroken"
            )
            (target / "scripts" / "score-change.py").write_text("stale\n")
            result = run_prune(plugin, target)
            self.assertEqual(result.returncode, 0)
            self.assertTrue((target / "scripts" / "score-change.py").exists())
            self.assertIn("unparseable", result.stderr)

    def test_project_root_manifest_entry_is_inert(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(Path(td), "./\n.\nscripts/x.py # note\n")
            (target / "README.md").write_text("keep\n")
            (target / "scripts" / "x.py").write_text("keep\n")
            result = run_prune(plugin, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((target / "README.md").exists())
            self.assertTrue((target / "scripts" / "x.py").exists())
            self.assertIn("no retired files removed", result.stdout)


class OutputAndCleanup(unittest.TestCase):
    def test_dry_run_removes_nothing_and_reports(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(Path(td), "scripts/score-change.py\n")
            (target / "scripts" / "score-change.py").write_text("stale\n")
            result = run_prune(plugin, target, "--dry-run")
            self.assertTrue((target / "scripts" / "score-change.py").exists())
            self.assertIn("would remove scripts/score-change.py", result.stdout)

    def test_control_characters_are_stripped_from_report_lines(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(Path(td), "schemas/scratch/\n")
            scratch = target / "schemas" / "scratch"
            scratch.mkdir(parents=True)
            (scratch / "evil\x1b[31mRED.json").write_text("x\n")
            result = run_prune(plugin, target)
            self.assertNotIn("\x1b", result.stdout)
            self.assertFalse(any(scratch.iterdir()) if scratch.is_dir() else False)

    def test_emptied_retired_directory_is_removed_but_kept_files_hold_it(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(
                Path(td),
                "schemas/scratch/\n",
                extensions='"schemas/scratch/mine.json"',
            )
            scratch = target / "schemas" / "scratch"
            (scratch / "sub").mkdir(parents=True)
            (scratch / "sub" / "old.json").write_text("x\n")
            run_prune(plugin, target)
            self.assertFalse(scratch.exists(), "emptied retired dir left behind")
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(
                Path(td),
                "schemas/scratch/\n",
                extensions='"schemas/scratch/mine.json"',
            )
            scratch = target / "schemas" / "scratch"
            scratch.mkdir(parents=True)
            (scratch / "mine.json").write_text("mine\n")
            (scratch / "old.json").write_text("x\n")
            run_prune(plugin, target)
            self.assertTrue((scratch / "mine.json").exists())
            self.assertFalse((scratch / "old.json").exists())


if __name__ == "__main__":
    os.chdir(ROOT)
    unittest.main()
