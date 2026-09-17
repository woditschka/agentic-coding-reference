#!/usr/bin/env python3
"""Pin the safety properties of marketplace/prune-retired.py as setup.sh runs it."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import ROOT

SCRIPT = ROOT / "marketplace" / "prune-retired.py"

BUNDLED_REGISTRY = (
    'ENGINE_SLIVER = ("scripts", "schemas/scratch", ".claude/templates")\n'
)

RETIRED_SCRIPT = "scripts/score-change.py"
RETIRED_DIR = "schemas/scratch/"
OUTSIDE_SLIVER_DIR = ".claude/skills/doc-review/"
PRODUCED_SCRIPT = "scripts/handoff.py"
EXTENSION_SCRIPT = "scripts/cc_accounting.py"
EXTENSION_FILE = "schemas/scratch/mine.json"
CONTROL_CHARACTER_NAME = "name\x1b[31mred.json"

SOME_CONTENT = "some content\n"


def layout(*extensions: str) -> str:
    quoted = ", ".join(f'"{e}"' for e in extensions)
    return f'[harness]\nchannel = "marketplace"\nextensions = [{quoted}]\n'


def make_fixture(
    tmp: Path,
    manifest: str,
    *,
    layout_text: str = layout(),
    with_registry: bool = True,
) -> tuple[Path, Path]:
    plugin = tmp / "plugin"
    target = tmp / "target"
    (plugin / "_engine" / "scripts").mkdir(parents=True)
    (plugin / "_engine" / PRODUCED_SCRIPT).write_text(SOME_CONTENT)
    (plugin / "retired-paths.txt").write_text(manifest)
    if with_registry:
        (plugin / "registry.py").write_text(BUNDLED_REGISTRY)
    (target / "scripts").mkdir(parents=True)
    (target / "scripts" / "layout.toml").write_text(layout_text)
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
                Path(td), f"{RETIRED_SCRIPT}\n{OUTSIDE_SLIVER_DIR}\n"
            )
            (target / RETIRED_SCRIPT).write_text(SOME_CONTENT)
            skill = target / OUTSIDE_SLIVER_DIR
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(SOME_CONTENT)
            result = run_prune(plugin, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((target / RETIRED_SCRIPT).exists())
            self.assertTrue((skill / "SKILL.md").exists())
            self.assertIn("not auto-removed", result.stdout)
            self.assertIn(f"removed {RETIRED_SCRIPT} (retired)", result.stdout)
            self.assertNotIn("recoverable", result.stdout)

    def test_missing_bundled_registry_reports_only(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(
                Path(td), f"{RETIRED_SCRIPT}\n", with_registry=False
            )
            (target / RETIRED_SCRIPT).write_text(SOME_CONTENT)
            result = run_prune(plugin, target)
            self.assertEqual(result.returncode, 0)
            self.assertTrue((target / RETIRED_SCRIPT).exists())
            self.assertIn("registry unreadable", result.stderr)


class SymlinkContainment(unittest.TestCase):
    def test_directory_entry_never_deletes_through_a_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            plugin, target = make_fixture(tmp, f"{RETIRED_DIR}\n")
            outside = tmp / "outside"
            outside.mkdir()
            (outside / "notes.md").write_text(SOME_CONTENT)
            (target / RETIRED_DIR).parent.mkdir()
            (target / RETIRED_DIR).symlink_to(outside)
            result = run_prune(plugin, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((outside / "notes.md").exists())

    def test_file_behind_symlinked_parent_is_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            plugin, target = make_fixture(tmp, "scripts/gone.py\n")
            outside = tmp / "real-scripts"
            outside.mkdir()
            (outside / "gone.py").write_text(SOME_CONTENT)
            shutil.rmtree(target / "scripts")
            (target / "scripts").symlink_to(outside)
            result = run_prune(plugin, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((outside / "gone.py").exists())
            self.assertIn("resolves outside the project", result.stdout)


class Guards(unittest.TestCase):
    def test_produced_path_wins_over_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(Path(td), f"{PRODUCED_SCRIPT}\n")
            (target / PRODUCED_SCRIPT).write_text(SOME_CONTENT)
            run_prune(plugin, target)
            self.assertTrue((target / PRODUCED_SCRIPT).exists())

    def test_declared_extension_is_kept_and_reported(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(
                Path(td), f"{EXTENSION_SCRIPT}\n", layout_text=layout(EXTENSION_SCRIPT)
            )
            (target / EXTENSION_SCRIPT).write_text(SOME_CONTENT)
            result = run_prune(plugin, target)
            self.assertTrue((target / EXTENSION_SCRIPT).exists())
            self.assertIn(f"kept {EXTENSION_SCRIPT}", result.stdout)

    def test_unparseable_layout_prunes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(
                Path(td), f"{RETIRED_SCRIPT}\n", layout_text="[harness\nbroken"
            )
            (target / RETIRED_SCRIPT).write_text(SOME_CONTENT)
            result = run_prune(plugin, target)
            self.assertEqual(result.returncode, 0)
            self.assertTrue((target / RETIRED_SCRIPT).exists())
            self.assertIn("unparseable", result.stderr)

    def test_project_root_manifest_entry_is_inert(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(Path(td), "./\n.\nscripts/x.py # note\n")
            (target / "README.md").write_text(SOME_CONTENT)
            (target / "scripts" / "x.py").write_text(SOME_CONTENT)
            result = run_prune(plugin, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((target / "README.md").exists())
            self.assertTrue((target / "scripts" / "x.py").exists())
            self.assertIn("no retired files removed", result.stdout)


class OutputAndCleanup(unittest.TestCase):
    def test_dry_run_removes_nothing_and_reports(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(Path(td), f"{RETIRED_SCRIPT}\n")
            (target / RETIRED_SCRIPT).write_text(SOME_CONTENT)
            result = run_prune(plugin, target, "--dry-run")
            self.assertTrue((target / RETIRED_SCRIPT).exists())
            self.assertIn(f"would remove {RETIRED_SCRIPT}", result.stdout)

    def test_control_characters_are_stripped_from_report_lines(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(Path(td), f"{RETIRED_DIR}\n")
            scratch = target / RETIRED_DIR
            scratch.mkdir(parents=True)
            (scratch / CONTROL_CHARACTER_NAME).write_text(SOME_CONTENT)
            result = run_prune(plugin, target)
            self.assertNotIn("\x1b", result.stdout)
            self.assertFalse(any(scratch.iterdir()) if scratch.is_dir() else False)

    def test_an_emptied_retired_directory_is_removed(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(
                Path(td), f"{RETIRED_DIR}\n", layout_text=layout(EXTENSION_FILE)
            )
            scratch = target / RETIRED_DIR
            (scratch / "sub").mkdir(parents=True)
            (scratch / "sub" / "old.json").write_text(SOME_CONTENT)
            run_prune(plugin, target)
            self.assertFalse(scratch.exists())

    def test_a_kept_extension_file_holds_its_retired_directory(self):
        with tempfile.TemporaryDirectory() as td:
            plugin, target = make_fixture(
                Path(td), f"{RETIRED_DIR}\n", layout_text=layout(EXTENSION_FILE)
            )
            scratch = target / RETIRED_DIR
            scratch.mkdir(parents=True)
            (target / EXTENSION_FILE).write_text(SOME_CONTENT)
            (scratch / "old.json").write_text(SOME_CONTENT)
            run_prune(plugin, target)
            self.assertTrue((target / EXTENSION_FILE).exists())
            self.assertFalse((scratch / "old.json").exists())


if __name__ == "__main__":
    os.chdir(ROOT)
    unittest.main()
