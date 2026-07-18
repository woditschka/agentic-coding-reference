#!/usr/bin/env python3
"""Tests for materialize.py (stdlib only).

Run: python3 harness/tests/test_materialize.py

Covers:
  1. Roster parity — the extras-scan roots derive from doctor.py's
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

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import ROOT, load

_SCRIPT = ROOT / "materialize.py"

materialize = load("materialize", "materialize.py")
doctor = load("doctor", "core/scripts/doctor.py")
refresh_chapters = load("refresh_chapters", "claude-md/refresh-chapters.py")
helpers = load("helpers", "helpers.py")


def run_materialize(stack, target):
    # --no-verify keeps these tests fast; TestVerifyRuntime covers the
    # install-time suite run directly.
    result = subprocess.run(
        [sys.executable, str(_SCRIPT), stack, str(target), "--no-verify"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"materialize failed: {result.stderr}")
    return result.stdout


def extras_of(stdout):
    """The extras block of a materialize run, one path per line."""
    m = re.search(
        r"^--- extras: .*? ---\n(.*?)^--- end extras ---$", stdout, re.S | re.M
    )
    return [l for l in (m.group(1).splitlines() if m else []) if l]


class RosterParity(unittest.TestCase):
    def test_extras_scan_roots_derive_from_doctor_runtime_paths(self):
        dirs = materialize.runtime_dirs()
        expected = [p for p in doctor.RUNTIME_PATHS if "." not in p.rsplit("/", 1)[-1]]
        self.assertEqual(dirs, expected)
        self.assertIn(".claude/skills", dirs)
        self.assertIn("schemas/scratch", dirs)
        self.assertNotIn("scripts/handoff.py", dirs)  # files are not scan roots

    def test_gitignore_runtime_matches_doctor_runtime_paths(self):
        # Directories only in check 1; this compares every entry: gitignore
        # paths normalized (strip trailing /* and /), .scratch/ excluded
        # (per-session state, deliberately absent from the doctor).
        template = (ROOT / "init/core/gitignore-runtime.txt").read_text(
            encoding="utf-8"
        )
        gi_paths = sorted(
            line.removesuffix("/*").removesuffix("/")
            for line in template.splitlines()
            if line and not line.startswith("#") and line != ".scratch/"
        )
        self.assertEqual(gi_paths, sorted(set(doctor.RUNTIME_PATHS)))

    def test_every_shipped_script_is_in_doctor_runtime_paths(self):
        # The rosters must agree with the shipped fileset: a new engine file
        # added to core/scripts/ or stacks/*/scripts/ but not to the roster
        # fails here instead of shipping tracked to manifest consumers. The
        # path below scripts/ is kept, not the basename: flattening would let
        # a subdirectory file hide behind a same-named top-level entry.
        shipped = set()
        for scripts_dir in [
            ROOT / "core/scripts",
            *(ROOT / "stacks").glob("*/scripts"),
        ]:
            for f in scripts_dir.rglob("*"):
                if f.is_file() and f.suffix != ".pyc" and "__pycache__" not in f.parts:
                    shipped.add(f"scripts/{f.relative_to(scripts_dir).as_posix()}")
        doctor_scripts = {p for p in doctor.RUNTIME_PATHS if p.startswith("scripts/")}
        self.assertEqual(shipped, doctor_scripts)

    def test_tool_registry_surfaces_covered_by_doctor_runtime_paths(self):
        # helpers.TOOLS is the producer-side registry; the shipped doctor's
        # RUNTIME_PATHS (and, via the gitignore test above, the .gitignore
        # skeleton) hand-code the same tool surfaces. A tool added to the
        # registry without a doctor row fails here — instead of shipping a
        # surface that is neither doctor-validated nor gitignored on the
        # out-of-band channels.
        for tool, row in helpers.TOOLS.items():
            self.assertIn(
                row["agents_dir"],
                doctor.RUNTIME_PATHS,
                f"{tool}: agents_dir missing from RUNTIME_PATHS",
            )
            for surface in row["surfaces"]:
                prefix = surface.rstrip("/")
                self.assertTrue(
                    any(
                        p == prefix or p.startswith(prefix + "/")
                        for p in doctor.RUNTIME_PATHS
                    ),
                    f"{tool}: surface {surface} uncovered by RUNTIME_PATHS",
                )

    def test_doctor_required_chapters_match_managed_chapters_headings(self):
        # The managed-chapter set is the real (non-fenced) `## ` headings of
        # managed-chapters.md; the doctor's required-chapter check must list
        # the same, or the refresh and the doctor disagree on what is managed.
        source = (ROOT / "claude-md/managed-chapters.md").read_text(encoding="utf-8")
        headings = refresh_chapters.chapter_titles(source.splitlines())
        self.assertEqual(sorted(set(headings)), sorted(set(doctor.REQUIRED_CHAPTERS)))


class ExtrasDetection(unittest.TestCase):
    def test_extras_reported_exactly(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            run_materialize("go", target)
            self.assertEqual(
                extras_of(run_materialize("go", target)),
                [],
                "clean re-install reported extras",
            )

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
            for path in (
                ".claude/skills/tdd-workflow/STALE.md",
                ".claude/skills/custom-x/SKILL.md",
                "scripts/retired-engine.py",
                "scripts/stack.sh",
            ):
                self.assertIn(path, reported)
            self.assertNotIn(
                "scripts/layout.toml",
                reported,
                "project-owned layout.toml reported as extra",
            )

    def test_generic_stack_owns_its_stack_sh(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            run_materialize("generic", target)
            (target / "scripts/stack.sh").write_text("#!/bin/sh\n")
            self.assertNotIn(
                "scripts/stack.sh", extras_of(run_materialize("generic", target))
            )


class LayoutParsing(unittest.TestCase):
    def test_unparseable_layout_fails_loud_and_installs_nothing(self):
        # Silently defaulting to copy + all tools would install the full
        # runtime into a project whose channel declaration just went
        # unreadable — the declaration must gate the install.
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            (target / "scripts").mkdir()
            (target / "scripts/layout.toml").write_text(
                '[harness]\nchannel = "marketplace"\nchannel = "copy"\n'
            )
            result = subprocess.run(
                [sys.executable, str(_SCRIPT), "go", str(target)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unparseable", result.stderr)
            self.assertFalse(
                (target / ".claude/skills").exists(),
                "runtime installed despite an unreadable declaration",
            )

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
                    '[harness]\nchannel = "copy"\n'
                )
                result = subprocess.run(
                    [sys.executable, str(_SCRIPT), slug, str(target)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0, f"slug {slug!r} was accepted")
                self.assertIn("unknown stack", result.stderr)
                self.assertIn("java-spring-boot", result.stderr)  # valid slugs
                self.assertFalse(
                    (target / ".claude").exists(),
                    f"runtime installed for bad slug {slug!r}",
                )

    def test_non_table_harness_key_fails_loud(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            (target / "scripts").mkdir()
            (target / "scripts/layout.toml").write_text('harness = "copy"\n')
            result = subprocess.run(
                [sys.executable, str(_SCRIPT), "go", str(target)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("[harness] is not a table", result.stderr)

    def test_invalid_channel_value_fails_loud_and_installs_nothing(self):
        # "marketplce" is not == "marketplace" at excluded_prefixes, so a
        # typo'd channel would install the full runtime into a marketplace
        # project; the doctor flags the enum only after the damaging install.
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            (target / "scripts").mkdir()
            (target / "scripts/layout.toml").write_text(
                '[harness]\nchannel = "marketplce"\n'
            )
            result = subprocess.run(
                [sys.executable, str(_SCRIPT), "go", str(target)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("marketplce", result.stderr)
            self.assertFalse(
                (target / ".claude/skills").exists(),
                "runtime installed despite an invalid channel",
            )

    def test_malformed_tools_value_fails_loud_and_installs_nothing(self):
        # A declared-but-malformed tools value must not fall through to the
        # every-tool default — same silent-divergence trap as an unknown name.
        for value in ('"claude"', '["claude", 42]', "[]"):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as td:
                target = Path(td)
                (target / "scripts").mkdir()
                (target / "scripts/layout.toml").write_text(
                    f'[harness]\nchannel = "copy"\ntools = {value}\n'
                )
                result = subprocess.run(
                    [sys.executable, str(_SCRIPT), "go", str(target)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(
                    result.returncode, 0, f"tools = {value} was accepted"
                )
                self.assertIn("non-empty list of strings", result.stderr)
                self.assertFalse(
                    (target / ".claude/skills").exists(),
                    f"runtime installed despite tools = {value}",
                )

    def test_unknown_declared_tool_fails_loud_and_installs_nothing(self):
        # An unknown name in [harness] tools would silently drop that tool's
        # surfaces on every materialize — same trap as the stack slug.
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            (target / "scripts").mkdir()
            (target / "scripts/layout.toml").write_text(
                '[harness]\nchannel = "copy"\ntools = ["claude", "copilott"]\n'
            )
            result = subprocess.run(
                [sys.executable, str(_SCRIPT), "go", str(target)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("copilott", result.stderr)
            self.assertFalse(
                (target / ".claude/skills").exists(),
                "runtime installed despite an unknown tool",
            )


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
            for surface in (
                ".claude/skills",
                ".claude/agents",
                ".claude/hooks",
                ".github/agents",
                ".opencode/agents",
                ".junie/agents",
            ):
                files = (
                    list((target / surface).rglob("*"))
                    if (target / surface).is_dir()
                    else []
                )
                self.assertEqual(
                    [f for f in files if f.is_file()],
                    [],
                    f"marketplace installed tool surface {surface}",
                )
            for engine in (
                "scripts/handoff.py",
                "scripts/doctor.py",
                "scripts/doctor-expectations.toml",
                "schemas/scratch/prd-entry.schema.json",
                ".claude/templates/implementation-plan.md",
                ".junie/config.json",
            ):
                self.assertTrue(
                    (target / engine).is_file(),
                    f"marketplace omitted engine sliver: {engine}",
                )


class TestVerifyRuntime(unittest.TestCase):
    """The install-time suite run — the one place the vendored runtime is
    tested on the consumer's host (project builds do not run harness suites;
    ADR 2026-07-13)."""

    # The scripts suites run via `unittest discover` under scripts/tests/, so a
    # passing/failing fixture is a discoverable TestCase (ADR 2026-07-17
    # runtime-package-layout). The hook suites still run as standalone scripts.
    PASS = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        pass\n"
    FAIL = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_bad(self):\n        self.fail('boom')\n"
    HOOK_PASS = "import sys\n\nsys.exit(0)\n"

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
        target = self._target(
            **{
                "scripts/tests/__init__.py": "",
                "scripts/tests/test_a.py": self.PASS,
                ".claude/hooks/test_b.py": self.HOOK_PASS,
            }
        )
        suites = ["scripts/tests/test_a.py", ".claude/hooks/test_b.py"]
        self.assertEqual(materialize.verify_runtime(target, suites), 0)

    def test_failing_suite_is_counted(self):
        target = self._target(
            **{
                "scripts/tests/__init__.py": "",
                "scripts/tests/test_a.py": self.PASS,
                "scripts/tests/test_bad.py": self.FAIL,
            }
        )
        suites = ["scripts/tests/test_a.py", "scripts/tests/test_bad.py"]
        self.assertEqual(materialize.verify_runtime(target, suites), 1)

    def test_project_authored_test_is_never_executed(self):
        # verify runs `unittest discover` over the harness-owned scripts/tests/
        # subtree; a project's own (failing) test_*.py sitting elsewhere in
        # scripts/ is outside that tree, so it is neither discovered nor blamed.
        target = self._target(
            **{
                "scripts/tests/__init__.py": "",
                "scripts/tests/test_a.py": self.PASS,
                "scripts/test_project_own.py": self.FAIL,
            }
        )
        self.assertEqual(
            materialize.verify_runtime(target, ["scripts/tests/test_a.py"]), 0
        )

    def test_installed_suites_filters_to_test_files(self):
        installed = {
            "scripts/handoff.py",
            "scripts/tests/test_handoff.py",
            ".claude/hooks/test_handoff_allow.py",
            ".claude/hooks/handoff-allow.py",
            ".claude/skills/doctor/test_data.md",
            "schemas/scratch/build-pass.schema.json",
        }
        self.assertEqual(
            sorted(materialize._installed_suites(installed)),
            [".claude/hooks/test_handoff_allow.py", "scripts/tests/test_handoff.py"],
        )

    def test_missing_init_fails_instead_of_silently_skipping(self):
        # Discovery skips a non-package directory without error; the guard
        # must turn that silent skip into a counted failure.
        target = self._target(
            **{
                "scripts/tests/__init__.py": "",
                "scripts/tests/handoff/test_a.py": self.PASS,
            }
        )
        suites = ["scripts/tests/handoff/test_a.py"]
        # Two counted failures: the package-chain guard names the non-package
        # dir, and the discovery run itself reports zero tests ran.
        self.assertEqual(materialize.verify_runtime(target, suites), 2)

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
            (target / "scripts/layout.toml").write_text('[harness]\nchannel = "copy"\n')
            out = run_materialize("generic", target)
            self.assertNotIn("verified:", out)


class RecordExtension(unittest.TestCase):
    """record-extension: the durable-keep primitive the /materialize skill
    calls in step 6 — layout entry plus the channel-aware .gitignore
    re-include, with the slash rule encoded in the script, not prose."""

    def _target(self, td, channel):
        target = Path(td)
        (target / "scripts").mkdir()
        (target / "scripts/layout.toml").write_text(
            f'[harness]\nchannel = "{channel}"\nextensions = []\n'
        )
        (target / ".claude/skills/perf-review").mkdir(parents=True)
        (target / ".claude/skills/perf-review/SKILL.md").write_text("x\n")
        (target / ".claude/agents").mkdir(parents=True)
        (target / ".claude/agents/perf-reviewer.md").write_text("x\n")
        return target

    def _record(self, target, path):
        return subprocess.run(
            [sys.executable, str(_SCRIPT), "record-extension", str(target), path],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_directory_and_file_gitignore_forms(self):
        with tempfile.TemporaryDirectory() as td:
            target = self._target(td, "manifest")
            r1 = self._record(target, ".claude/skills/perf-review")
            r2 = self._record(target, ".claude/agents/perf-reviewer.md")
            self.assertEqual(
                (r1.returncode, r2.returncode), (0, 0), r1.stderr + r2.stderr
            )
            layout = (target / "scripts/layout.toml").read_text()
            self.assertIn(
                'extensions = [".claude/skills/perf-review", '
                '".claude/agents/perf-reviewer.md"]',
                layout,
            )
            gi = (target / ".gitignore").read_text().splitlines()
            self.assertIn("!.claude/skills/perf-review/", gi)
            self.assertIn("!.claude/agents/perf-reviewer.md", gi)

    def test_idempotent_and_copy_channel_skips_gitignore(self):
        with tempfile.TemporaryDirectory() as td:
            target = self._target(td, "copy")
            self._record(target, ".claude/skills/perf-review")
            r = self._record(target, ".claude/skills/perf-review")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("already recorded", r.stdout)
            layout = (target / "scripts/layout.toml").read_text()
            self.assertEqual(layout.count("perf-review"), 1)
            self.assertFalse((target / ".gitignore").exists())

    def test_missing_path_fails_loud(self):
        with tempfile.TemporaryDirectory() as td:
            target = self._target(td, "manifest")
            r = self._record(target, ".claude/skills/no-such-skill")
            self.assertEqual(r.returncode, 1)
            self.assertIn("does not exist", r.stderr)

    def test_unsafe_paths_are_rejected_never_escaped(self):
        # The path lands verbatim in layout.toml and .gitignore: a quote or
        # newline would inject config lines; dot-dot would escape the target.
        with tempfile.TemporaryDirectory() as td:
            target = self._target(td, "manifest")
            evil_dir = target / '.claude/skills/evil", "injected'
            evil_dir.mkdir(parents=True)
            for path in (
                '.claude/skills/evil", "injected',
                '.claude/skills/x"]\nsize_threshold = 9',
                "../outside",
                "/etc/passwd",
            ):
                r = self._record(target, path)
                self.assertEqual(r.returncode, 1, path)
            layout = (target / "scripts/layout.toml").read_text()
            self.assertIn("extensions = []", layout)

    def test_comma_backslash_and_degenerate_paths_are_rejected(self):
        # A comma corrupts the array's comma-joined re-parse on the next
        # record; a backslash is a TOML basic-string escape; "" and "."
        # would record the whole target as one extension.
        with tempfile.TemporaryDirectory() as td:
            target = self._target(td, "manifest")
            (target / ".claude/skills/a,b").mkdir(parents=True)
            (target / ".claude/skills/a\\b").mkdir(parents=True)
            for path in (".claude/skills/a,b", ".claude/skills/a\\b", ".", "/", "./"):
                r = self._record(target, path)
                self.assertEqual(r.returncode, 1, path)
            layout = (target / "scripts/layout.toml").read_text()
            self.assertIn("extensions = []", layout)

    def test_dead_reinclude_under_bare_dir_ignore_fails_loud(self):
        # git never descends into a dir ignored by the bare "dir/" form, so
        # a "!path/" re-include under it is silently dead — the command must
        # fail loud instead of reporting the extension kept.
        with tempfile.TemporaryDirectory() as td:
            target = self._target(td, "manifest")
            subprocess.run(
                ["git", "init", "-q"], cwd=target, check=True, capture_output=True
            )
            (target / ".gitignore").write_text(".claude/\n")
            r = self._record(target, ".claude/skills/perf-review")
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertIn("still gitignored", r.stderr)


class TestPlanInstall(unittest.TestCase):
    """The --dry-run plan (ADR 2026-07-18). plan_install is unit-testable
    without a subprocess: it stats the source tree against the target's disk
    state and returns the create/overwrite split, no install required."""

    def test_greenfield_is_all_created(self):
        with tempfile.TemporaryDirectory() as td:
            created, overwritten = materialize.plan_install("go", Path(td), [])
            self.assertEqual(overwritten, [], "nothing on disk yet — no overwrites")
            self.assertIn(".claude/agents/README.md", created)
            self.assertEqual(created, sorted(set(created)), "sorted, no duplicates")

    def test_present_file_moves_to_overwritten(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            rel = ".claude/agents/README.md"
            (target / ".claude/agents").mkdir(parents=True)
            (target / rel).write_text("local edit", encoding="utf-8")
            created, overwritten = materialize.plan_install("go", target, [])
            self.assertIn(rel, overwritten, "an on-disk runtime file is overwritten")
            self.assertNotIn(rel, created)

    def test_core_stack_overlap_counted_once(self):
        # A rel produced by both core and the stack layer is one plan entry,
        # decided on the pre-run disk state — never double-listed.
        with tempfile.TemporaryDirectory() as td:
            created, overwritten = materialize.plan_install("go", Path(td), [])
            allrels = created + overwritten
            self.assertEqual(len(allrels), len(set(allrels)), "no rel appears twice")

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            result = subprocess.run(
                [sys.executable, str(_SCRIPT), "go", str(target), "--dry-run"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("dry run — nothing written", result.stdout)
            self.assertIn("--- plan create:", result.stdout)
            self.assertEqual(
                list(target.iterdir()), [], "the dry run must write nothing"
            )

    def test_dry_run_leaves_populated_target_byte_identical(self):
        # The greenfield case above proves no file is created; this one proves
        # the refresh writers (managed chapters, .gitignore, settings) and the
        # runtime copy are all skipped on a target that has content to touch —
        # a future reordering of show_plan() after any write must fail here.
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            (target / "scripts").mkdir()
            (target / "scripts/layout.toml").write_text(
                '[harness]\nchannel = "copy"\n', encoding="utf-8"
            )
            (target / "CLAUDE.md").write_text("# Widget\n\ncontent\n", encoding="utf-8")
            (target / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
            (target / ".claude/agents").mkdir(parents=True)
            (target / ".claude/agents/README.md").write_text("local", encoding="utf-8")
            (target / ".claude/skills/mine").mkdir(parents=True)
            (target / ".claude/skills/mine/SKILL.md").write_text("x", encoding="utf-8")
            before = {
                p.relative_to(target).as_posix(): p.read_bytes()
                for p in target.rglob("*")
                if p.is_file()
            }
            result = subprocess.run(
                [sys.executable, str(_SCRIPT), "go", str(target), "--dry-run"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--- plan overwrite:", result.stdout)
            after = {
                p.relative_to(target).as_posix(): p.read_bytes()
                for p in target.rglob("*")
                if p.is_file()
            }
            self.assertEqual(before, after, "the dry run modified the target")


if __name__ == "__main__":
    unittest.main()
