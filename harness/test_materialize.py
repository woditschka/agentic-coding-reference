#!/usr/bin/env python3
"""Tests for materialize.py (stdlib only).

Run: python3 harness/test_materialize.py

Covers:
  1. Roster parity — the extras-scan roots derive from brief_doctor.py's
     RUNTIME_PATHS; gitignore-runtime.txt, the shipped scripts/ fileset, and
     the doctor's REQUIRED_CHAPTERS stay in lockstep with their sources.
  2. Extras detection — a clean re-install reports zero extras; a planted
     orphan, an extension, a retired scripts/ engine, and a stray stack.sh on
     a non-generic stack are all reported; the project-owned layout.toml is
     not, nor is stack.sh on the generic stack.
  3. The marketplace channel installs only the engine sliver (scripts,
     schemas, templates, tool config), never the plugin-delivered surfaces.

The refresh writers' own contracts live in their sibling suites
(test_refresh_gitignore.py, test_refresh_chapters.py, test_refresh_settings.py).
"""

import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPT = _HERE / "materialize.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


materialize = _load("materialize", _SCRIPT)
brief_doctor = _load("brief_doctor", _HERE / "core/scripts/brief_doctor.py")
refresh_chapters = _load("refresh_chapters", _HERE / "claude-md/refresh-chapters.py")
helpers = _load("helpers", _HERE / "helpers.py")


def run_materialize(stack, target):
    # --no-verify keeps these tests fast; TestVerifyRuntime covers the
    # install-time suite run directly.
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), stack, str(target), "--no-verify"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"materialize failed: {result.stderr}")
    return result.stdout


def extras_of(stdout):
    """The extras block of a materialize run, one path per line."""
    m = re.search(r"^--- extras: .*? ---\n(.*?)^--- end extras ---$",
                  stdout, re.S | re.M)
    return [l for l in (m.group(1).splitlines() if m else []) if l]


class RosterParity(unittest.TestCase):
    def test_extras_scan_roots_derive_from_doctor_runtime_paths(self):
        dirs = materialize.runtime_dirs()
        expected = [p for p in brief_doctor.RUNTIME_PATHS
                    if "." not in p.rsplit("/", 1)[-1]]
        self.assertEqual(dirs, expected)
        self.assertIn(".claude/skills", dirs)
        self.assertIn("schemas/scratch", dirs)
        self.assertNotIn("scripts/handoff.py", dirs)   # files are not scan roots

    def test_gitignore_runtime_matches_doctor_runtime_paths(self):
        # Directories only in check 1; this compares every entry: gitignore
        # paths normalized (strip trailing /* and /), .scratch/ excluded
        # (per-session state, deliberately absent from the doctor).
        template = (_HERE / "init/core/gitignore-runtime.txt").read_text(encoding="utf-8")
        gi_paths = sorted(
            line.removesuffix("/*").removesuffix("/")
            for line in template.splitlines()
            if line and not line.startswith("#") and line != ".scratch/"
        )
        self.assertEqual(gi_paths, sorted(set(brief_doctor.RUNTIME_PATHS)))

    def test_every_shipped_script_is_in_doctor_runtime_paths(self):
        # The rosters must agree with the shipped fileset: a new engine file
        # added to core/scripts/ or stacks/*/scripts/ but not to the roster
        # fails here instead of shipping tracked to manifest consumers. The
        # path below scripts/ is kept, not the basename: flattening would let
        # a subdirectory file hide behind a same-named top-level entry.
        shipped = set()
        for scripts_dir in [_HERE / "core/scripts",
                            *(_HERE / "stacks").glob("*/scripts")]:
            for f in scripts_dir.rglob("*"):
                if f.is_file() and f.suffix != ".pyc" and "__pycache__" not in f.parts:
                    shipped.add(f"scripts/{f.relative_to(scripts_dir).as_posix()}")
        doctor_scripts = {p for p in brief_doctor.RUNTIME_PATHS if p.startswith("scripts/")}
        self.assertEqual(shipped, doctor_scripts)

    def test_tool_registry_surfaces_covered_by_doctor_runtime_paths(self):
        # helpers.TOOLS is the producer-side registry; the shipped doctor's
        # RUNTIME_PATHS (and, via the gitignore test above, the .gitignore
        # skeleton) hand-code the same tool surfaces. A tool added to the
        # registry without a doctor row fails here — instead of shipping a
        # surface that is neither doctor-validated nor gitignored on the
        # out-of-band channels.
        for tool, row in helpers.TOOLS.items():
            self.assertIn(row["agents_dir"], brief_doctor.RUNTIME_PATHS,
                          f"{tool}: agents_dir missing from RUNTIME_PATHS")
            for surface in row["surfaces"]:
                prefix = surface.rstrip("/")
                self.assertTrue(
                    any(p == prefix or p.startswith(prefix + "/")
                        for p in brief_doctor.RUNTIME_PATHS),
                    f"{tool}: surface {surface} uncovered by RUNTIME_PATHS")

    def test_doctor_required_chapters_match_managed_chapters_headings(self):
        # The managed-chapter set is the real (non-fenced) `## ` headings of
        # managed-chapters.md; the doctor's required-chapter check must list
        # the same, or the refresh and the doctor disagree on what is managed.
        source = (_HERE / "claude-md/managed-chapters.md").read_text(encoding="utf-8")
        headings = refresh_chapters.chapter_titles(source.splitlines())
        self.assertEqual(sorted(set(headings)),
                         sorted(set(brief_doctor.REQUIRED_CHAPTERS)))


class ExtrasDetection(unittest.TestCase):
    def test_extras_reported_exactly(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            run_materialize("go", target)
            self.assertEqual(extras_of(run_materialize("go", target)), [],
                             "clean re-install reported extras")

            # An orphan in a harness-managed skill, an extension, a retired
            # engine, a stray stack.sh (project-owned on generic only), and
            # the project-owned layout.toml.
            (target / ".claude/skills/tdd-workflow/STALE.md").write_text("stale\n")
            (target / ".claude/skills/custom-x").mkdir(parents=True)
            (target / ".claude/skills/custom-x/SKILL.md").write_text("custom\n")
            (target / "scripts/retired-engine.py").write_text("stale\n")
            (target / "scripts/layout.toml").write_text('[harness]\nchannel = "copy"\n')
            (target / "scripts/stack.sh").write_text("#!/bin/sh\n")

            reported = extras_of(run_materialize("go", target))
            for path in (".claude/skills/tdd-workflow/STALE.md",
                         ".claude/skills/custom-x/SKILL.md",
                         "scripts/retired-engine.py",
                         "scripts/stack.sh"):
                self.assertIn(path, reported)
            self.assertNotIn("scripts/layout.toml", reported,
                             "project-owned layout.toml reported as extra")

    def test_generic_stack_owns_its_stack_sh(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            run_materialize("generic", target)
            (target / "scripts/stack.sh").write_text("#!/bin/sh\n")
            self.assertNotIn("scripts/stack.sh",
                             extras_of(run_materialize("generic", target)))


class LayoutParsing(unittest.TestCase):
    def test_unparseable_layout_fails_loud_and_installs_nothing(self):
        # Silently defaulting to copy + all tools would install the full
        # runtime into a project whose channel declaration just went
        # unreadable — the declaration must gate the install.
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            (target / "scripts").mkdir()
            (target / "scripts/layout.toml").write_text(
                '[harness]\nchannel = "marketplace"\nchannel = "copy"\n')
            result = subprocess.run(
                [sys.executable, str(_SCRIPT), "go", str(target)],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unparseable", result.stderr)
            self.assertFalse((target / ".claude/skills").exists(),
                             "runtime installed despite an unreadable declaration")

    def test_unknown_stack_fails_loud_and_installs_nothing(self):
        # A slug with no harness/stacks/<stack>/ must error, not silently
        # install core alone and report success — which would strand the stack
        # reviewer roster. The empty, "..", and absolute cases are the pathlib
        # traps: `HERE/"stacks"/slug` resolves to a real directory for each, so
        # an is_dir() guard would pass while install()'s relative
        # f"stacks/{slug}" still copied core alone — the same silent-success
        # failure the guard exists to close. Membership must reject them all.
        for slug in ("java", "", "..", "../core", "/etc"):
            with self.subTest(slug=slug), tempfile.TemporaryDirectory() as td:
                target = Path(td)
                (target / "scripts").mkdir()
                (target / "scripts/layout.toml").write_text(
                    '[harness]\nchannel = "copy"\n')
                result = subprocess.run(
                    [sys.executable, str(_SCRIPT), slug, str(target)],
                    capture_output=True, text=True, check=False,
                )
                self.assertNotEqual(result.returncode, 0,
                                    f"slug {slug!r} was accepted")
                self.assertIn("unknown stack", result.stderr)
                self.assertIn("java-spring-boot", result.stderr)  # valid slugs
                self.assertFalse((target / ".claude").exists(),
                                 f"runtime installed for bad slug {slug!r}")

    def test_non_table_harness_key_fails_loud(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            (target / "scripts").mkdir()
            (target / "scripts/layout.toml").write_text('harness = "copy"\n')
            result = subprocess.run(
                [sys.executable, str(_SCRIPT), "go", str(target)],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("[harness] is not a table", result.stderr)


class MarketplaceChannel(unittest.TestCase):
    def test_engine_sliver_only(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            (target / "scripts").mkdir()
            (target / "scripts/layout.toml").write_text(
                '[harness]\nchannel = "marketplace"\nspec_version = "0.1.0"\n'
                'tools = ["claude", "copilot", "junie"]\nextensions = []\n'
            )
            run_materialize("go", target)
            for surface in (".claude/skills", ".claude/agents", ".claude/hooks",
                            ".github/agents", ".opencode/agents", ".junie/agents"):
                files = list((target / surface).rglob("*")) if (target / surface).is_dir() else []
                self.assertEqual([f for f in files if f.is_file()], [],
                                 f"marketplace installed tool surface {surface}")
            for engine in ("scripts/handoff.py", "scripts/brief_doctor.py",
                           "scripts/brief-expectations.toml",
                           "schemas/scratch/prd-entry.schema.json",
                           ".claude/templates/implementation-plan.md",
                           ".junie/config.json"):
                self.assertTrue((target / engine).is_file(),
                                f"marketplace omitted engine sliver: {engine}")


class TestVerifyRuntime(unittest.TestCase):
    """The install-time suite run — the one place the vendored runtime is
    tested on the consumer's host (project builds do not run harness suites;
    ADR 2026-07-13)."""

    PASS = "import sys\nsys.exit(0)\n"
    FAIL = "import sys\nsys.stderr.write('boom\\n')\nsys.exit(1)\n"

    def _target(self, **files):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        target = Path(td.name)
        for rel, body in files.items():
            path = target / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        return target

    def test_passing_suites_verify_clean(self):
        target = self._target(**{"scripts/test_a.py": self.PASS,
                                 ".claude/hooks/test_b.py": self.PASS})
        suites = ["scripts/test_a.py", ".claude/hooks/test_b.py"]
        self.assertEqual(materialize.verify_runtime(target, suites), 0)

    def test_failing_suite_is_counted(self):
        target = self._target(**{"scripts/test_a.py": self.PASS,
                                 "scripts/test_bad.py": self.FAIL})
        suites = ["scripts/test_a.py", "scripts/test_bad.py"]
        self.assertEqual(materialize.verify_runtime(target, suites), 1)

    def test_project_authored_test_is_never_executed(self):
        # The suite list derives from the install's own file set, never a
        # target-tree glob: a project's own (failing) test_*.py sitting in
        # scripts/ is neither executed nor blamed on the install.
        target = self._target(**{"scripts/test_a.py": self.PASS,
                                 "scripts/test_project_own.py": self.FAIL})
        self.assertEqual(
            materialize.verify_runtime(target, ["scripts/test_a.py"]), 0)

    def test_installed_suites_filters_to_test_files(self):
        installed = {"scripts/handoff.py", "scripts/test_handoff.py",
                     ".claude/hooks/test_handoff_allow.py",
                     ".claude/hooks/handoff-allow.py",
                     ".claude/skills/doctor/test_data.md",
                     "schemas/scratch/build-pass.schema.json"}
        self.assertEqual(sorted(materialize._installed_suites(installed)),
                         [".claude/hooks/test_handoff_allow.py",
                          "scripts/test_handoff.py"])

    def test_no_suites_is_clean(self):
        # A target whose install produced no suites has nothing to run;
        # nothing to run is not a failure.
        self.assertEqual(materialize.verify_runtime(self._target(), []), 0)

    def test_no_verify_flag_skips_the_run(self):
        # run_materialize passes --no-verify; the output must carry no
        # verification line, proving the flag reaches main.
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            (target / "scripts").mkdir()
            (target / "scripts/layout.toml").write_text(
                '[harness]\nchannel = "copy"\n')
            out = run_materialize("generic", target)
            self.assertNotIn("verified:", out)


if __name__ == "__main__":
    unittest.main()
