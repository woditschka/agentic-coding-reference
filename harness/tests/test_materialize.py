#!/usr/bin/env python3
"""Pin the materialize contract: roster parity, extras, layout gating, channel slivers, verify, and the plan."""

import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import ROOT, load

_SCRIPT = ROOT / "materialize.py"

materialize = load("materialize", "materialize.py")
doctor = load("doctor", "core/scripts/doctor.py")
refresh_chapters = load("refresh_chapters", "claude-md/refresh-chapters.py")
registry = load("registry", "registry.py")

ANY_CONTENT = "x\n"
COPY_LAYOUT = '[harness]\nchannel = "copy"\n'
MARKETPLACE_LAYOUT = (
    '[harness]\nchannel = "marketplace"\nspec_version = "0.1.0"\n'
    'tools = ["claude", "copilot"]\nextensions = []\n'
)
DUPLICATE_KEY_LAYOUT = '[harness]\nchannel = "marketplace"\nchannel = "copy"\n'
NON_TABLE_LAYOUT = 'harness = "copy"\n'
TYPO_CHANNEL = "marketplce"
UNKNOWN_TOOL = "copilott"
SLUGS_OUTSIDE_REGISTRY = ("java", "", "..", "../core", "/etc")
MALFORMED_TOOLS_VALUES = ('"claude"', '["claude", 42]', "[]")
RETIRED_NOTE = "  [retired — harness/retired-paths.txt]"
A_RETIRED_ENGINE = "scripts/score-change.py"
A_RETIRED_SKILL = ".claude/skills/doc-review/SKILL.md"
A_RETIRED_TOOL_SURFACE = ".junie"
INSTALLED_SPEC_VERSION = "0.9.9"
STALE_SPEC_VERSION = "0.1.0"
TOOL_SURFACES = (
    ".claude/skills",
    ".claude/agents",
    ".claude/hooks",
    ".github/agents",
    ".opencode/agents",
)
ENGINE_SLIVER = (
    "scripts/handoff.py",
    "scripts/doctor.py",
    "scripts/doctor-expectations.toml",
    "schemas/scratch/prd-entry.schema.json",
    ".claude/templates/implementation-plan.md",
)
A_PASSING_SUITE = (
    "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n"
    "        pass\n"
)
A_FAILING_SUITE = (
    "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_bad(self):\n"
    "        self.fail('boom')\n"
)
A_PASSING_HOOK_SUITE = "import sys\n\nsys.exit(0)\n"
AN_ALL_SKIPPED_SUITE = (
    "import unittest\n\n\ndef setUpModule():\n"
    '    raise unittest.SkipTest("channel")\n\n\n'
    "class T(unittest.TestCase):\n    def test_ok(self):\n        pass\n"
)
AN_EXTENSION_SKILL = ".claude/skills/perf-review"
AN_EXTENSION_AGENT = ".claude/agents/perf-reviewer.md"


def run_script(*argv):
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *argv],
        capture_output=True,
        text=True,
        check=False,
    )


def run_materialize(stack, target):
    # --no-verify keeps these tests fast; VerifyRuntime covers the suite run.
    result = run_script(stack, str(target), "--no-verify")
    if result.returncode != 0:
        raise AssertionError(f"materialize failed: {result.stderr}")
    return result.stdout


def extras_of(stdout):
    """Return the extras block of a materialize run, one path per line."""
    m = re.search(
        r"^--- extras: .*? ---\n(.*?)^--- end extras ---$",
        stdout,
        re.DOTALL | re.MULTILINE,
    )
    return [line for line in (m.group(1).splitlines() if m else []) if line]


def a_target(case, layout=None):
    holder = tempfile.TemporaryDirectory()
    case.addCleanup(holder.cleanup)
    target = Path(holder.name)
    if layout is not None:
        (target / "scripts").mkdir()
        (target / "scripts/layout.toml").write_text(layout, encoding="utf-8")
    return target


def plant(target, rel, content=ANY_CONTENT):
    path = target / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class RosterParity(unittest.TestCase):
    def test_extras_scan_roots_derive_from_doctor_runtime_paths(self):
        dirs = materialize.runtime_dirs()
        expected = [p for p in doctor.RUNTIME_PATHS if "." not in p.rsplit("/", 1)[-1]]
        self.assertEqual(dirs, expected)
        self.assertIn(".claude/skills", dirs)
        self.assertIn("schemas/scratch", dirs)
        self.assertNotIn("scripts/handoff.py", dirs)

    def test_gitignore_runtime_matches_doctor_runtime_paths(self):
        # .scratch/ is per-session state, deliberately absent from the doctor.
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
        # The path below scripts/ is kept, not the basename: flattening would
        # let a subdirectory file hide behind a same-named top-level entry.
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
        for tool, row in registry.TOOLS.items():
            self.assertIn(row["agents_dir"], doctor.RUNTIME_PATHS, tool)
            for surface in row["surfaces"]:
                prefix = surface.rstrip("/")
                self.assertTrue(
                    any(
                        p == prefix or p.startswith(prefix + "/")
                        for p in doctor.RUNTIME_PATHS
                    ),
                    f"{tool}: {surface}",
                )

    def test_doctor_required_chapters_match_managed_chapters_headings(self):
        source = (ROOT / "claude-md/managed-chapters.md").read_text(encoding="utf-8")
        headings = refresh_chapters.chapter_titles(source.splitlines())
        self.assertEqual(sorted(set(headings)), sorted(set(doctor.REQUIRED_CHAPTERS)))


class ExtrasDetection(unittest.TestCase):
    def test_planted_extras_are_reported_and_project_owned_files_are_not(self):
        target = a_target(self)
        run_materialize("go", target)
        self.assertEqual(extras_of(run_materialize("go", target)), [])

        extras = (
            ".claude/skills/tdd-workflow/STALE.md",
            ".claude/skills/custom-x/SKILL.md",
            "scripts/retired-engine.py",
            "scripts/stack.sh",
        )
        project_owned = ("scripts/layout.toml", "scripts/backlog.sh")
        for rel in extras:
            plant(target, rel)
        plant(target, "scripts/layout.toml", COPY_LAYOUT)
        plant(target, "scripts/backlog.sh")

        reported = extras_of(run_materialize("go", target))
        for rel in extras:
            self.assertIn(rel, reported)
        for rel in project_owned:
            self.assertNotIn(rel, reported)

    def test_manifest_covered_extra_is_annotated_retired(self):
        target = a_target(self)
        run_materialize("go", target)
        plant(target, A_RETIRED_ENGINE)
        plant(target, A_RETIRED_SKILL)
        plant(target, "scripts/my-own-tool.py")
        reported = extras_of(run_materialize("go", target))
        self.assertIn(A_RETIRED_ENGINE + RETIRED_NOTE, reported)
        self.assertIn(A_RETIRED_SKILL + RETIRED_NOTE, reported)
        self.assertIn("scripts/my-own-tool.py", reported)

    def test_a_retired_directory_outside_the_runtime_dirs_is_reported(self):
        # A retired tool surface is no runtime dir any more, so the extras
        # scan must walk it from the manifest or the leftover tree persists.
        target = a_target(self)
        run_materialize("go", target)
        leftovers = (
            f"{A_RETIRED_TOOL_SURFACE}/agents/x.md",
            f"{A_RETIRED_TOOL_SURFACE}/config.json",
        )
        for rel in leftovers:
            plant(target, rel)
        reported = extras_of(run_materialize("go", target))
        for rel in leftovers:
            self.assertIn(rel + RETIRED_NOTE, reported)

    def test_generic_stack_owns_its_stack_sh(self):
        target = a_target(self)
        run_materialize("generic", target)
        plant(target, "scripts/stack.sh")
        self.assertNotIn(
            "scripts/stack.sh", extras_of(run_materialize("generic", target))
        )


class LayoutParsing(unittest.TestCase):
    def test_unparseable_layout_fails_loud_and_installs_nothing(self):
        target = a_target(self, DUPLICATE_KEY_LAYOUT)
        result = run_script("go", str(target))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unparseable", result.stderr)
        self.assertFalse((target / ".claude/skills").exists())

    def test_unknown_stack_fails_loud_and_installs_nothing(self):
        # The empty, "..", and absolute slugs are the pathlib traps: an
        # is_dir() guard would pass while the install copied core alone.
        for slug in SLUGS_OUTSIDE_REGISTRY:
            with self.subTest(slug=slug):
                target = a_target(self, COPY_LAYOUT)
                result = run_script(slug, str(target))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unknown stack", result.stderr)
                self.assertIn("java-spring-boot", result.stderr)
                self.assertFalse((target / ".claude").exists())

    def test_non_table_harness_key_fails_loud(self):
        target = a_target(self, NON_TABLE_LAYOUT)
        result = run_script("go", str(target))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[harness] is not a table", result.stderr)

    def test_invalid_channel_value_fails_loud_and_installs_nothing(self):
        # A typo'd channel would install the full runtime into a marketplace
        # project; the doctor flags the enum only after the damaging install.
        target = a_target(self, f'[harness]\nchannel = "{TYPO_CHANNEL}"\n')
        result = run_script("go", str(target))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(TYPO_CHANNEL, result.stderr)
        self.assertFalse((target / ".claude/skills").exists())

    def test_malformed_tools_value_fails_loud_and_installs_nothing(self):
        for value in MALFORMED_TOOLS_VALUES:
            with self.subTest(value=value):
                target = a_target(self, COPY_LAYOUT + f"tools = {value}\n")
                result = run_script("go", str(target))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("non-empty list of strings", result.stderr)
                self.assertFalse((target / ".claude/skills").exists())

    def test_unknown_declared_tool_fails_loud_and_installs_nothing(self):
        target = a_target(self, COPY_LAYOUT + f'tools = ["claude", "{UNKNOWN_TOOL}"]\n')
        result = run_script("go", str(target))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(UNKNOWN_TOOL, result.stderr)
        self.assertFalse((target / ".claude/skills").exists())


class MarketplaceChannel(unittest.TestCase):
    def test_marketplace_installs_the_engine_sliver_and_no_tool_surface(self):
        target = a_target(self, MARKETPLACE_LAYOUT)
        run_materialize("go", target)
        for surface in TOOL_SURFACES:
            files = (
                list((target / surface).rglob("*"))
                if (target / surface).is_dir()
                else []
            )
            self.assertEqual([f for f in files if f.is_file()], [], surface)
        for engine in ENGINE_SLIVER:
            self.assertTrue((target / engine).is_file(), engine)


class SpecVersionRestamp(unittest.TestCase):
    """The one deterministic layout.toml write follows the installed doctor manifest."""

    def target_with_layout(self, body):
        target = a_target(self, body)
        (target / "scripts" / "doctor-expectations.toml").write_text(
            f'spec_version = "{INSTALLED_SPEC_VERSION}"\n', encoding="utf-8"
        )
        return target

    def test_a_stale_declaration_is_restamped(self):
        target = self.target_with_layout(
            COPY_LAYOUT + f'spec_version = "{STALE_SPEC_VERSION}"\n'
        )
        status = materialize.restamp_spec_version(target)
        self.assertIn(f"restamped to {INSTALLED_SPEC_VERSION}", status)
        text = (target / "scripts" / "layout.toml").read_text(encoding="utf-8")
        self.assertIn(f'spec_version = "{INSTALLED_SPEC_VERSION}"', text)
        self.assertIn('channel = "copy"', text)

    def test_a_current_declaration_is_left_byte_identical(self):
        body = COPY_LAYOUT + f'spec_version = "{INSTALLED_SPEC_VERSION}"\n'
        target = self.target_with_layout(body)
        status = materialize.restamp_spec_version(target)
        self.assertIn("current", status)
        self.assertEqual(
            (target / "scripts" / "layout.toml").read_text(encoding="utf-8"), body
        )

    def test_a_missing_declaration_reports_and_writes_nothing(self):
        target = self.target_with_layout(COPY_LAYOUT)
        status = materialize.restamp_spec_version(target)
        self.assertIn("left for /init", status)
        self.assertEqual(
            (target / "scripts" / "layout.toml").read_text(encoding="utf-8"),
            COPY_LAYOUT,
        )

    def test_a_full_run_restamps_the_scaffolded_layout(self):
        target = a_target(
            self, COPY_LAYOUT + f'spec_version = "{STALE_SPEC_VERSION}"\n'
        )
        stdout = run_materialize("generic", target)
        self.assertIn("spec_version: restamped to", stdout)


class VerifyRuntime(unittest.TestCase):
    """The install-time suite run, the one place the vendored runtime is tested on the consumer's host."""

    def _target(self, **files):
        target = a_target(self)
        for rel, body in files.items():
            plant(target, rel, body)
        return target

    def test_passing_suites_verify_clean(self):
        target = self._target(
            **{
                "scripts/tests/__init__.py": "",
                "scripts/tests/test_a.py": A_PASSING_SUITE,
                ".claude/hooks/test_b.py": A_PASSING_HOOK_SUITE,
            }
        )
        suites = ["scripts/tests/test_a.py", ".claude/hooks/test_b.py"]
        self.assertEqual(materialize.verify_runtime(target, suites), 0)

    def test_failing_suite_is_counted(self):
        target = self._target(
            **{
                "scripts/tests/__init__.py": "",
                "scripts/tests/test_a.py": A_PASSING_SUITE,
                "scripts/tests/test_bad.py": A_FAILING_SUITE,
            }
        )
        suites = ["scripts/tests/test_a.py", "scripts/tests/test_bad.py"]
        self.assertEqual(materialize.verify_runtime(target, suites), 1)

    def test_project_authored_test_is_never_executed(self):
        target = self._target(
            **{
                "scripts/tests/__init__.py": "",
                "scripts/tests/test_a.py": A_PASSING_SUITE,
                "scripts/tests/test_project_own.py": A_FAILING_SUITE,
                "scripts/test_project_root.py": A_FAILING_SUITE,
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

    def test_nested_suite_runs_as_a_named_module(self):
        target = self._target(
            **{
                "scripts/tests/__init__.py": "",
                "scripts/tests/handoff/__init__.py": "",
                "scripts/tests/handoff/test_bad.py": A_FAILING_SUITE,
            }
        )
        suites = ["scripts/tests/handoff/test_bad.py"]
        self.assertEqual(materialize.verify_runtime(target, suites), 1)

    def test_missing_suite_fails_instead_of_silently_skipping(self):
        target = self._target(**{"scripts/tests/__init__.py": ""})
        suites = ["scripts/tests/test_gone.py"]
        self.assertEqual(materialize.verify_runtime(target, suites), 1)

    def test_scripts_root_suite_runs_as_a_named_module(self):
        target = self._target(**{"scripts/test_top.py": A_FAILING_SUITE})
        self.assertEqual(materialize.verify_runtime(target, ["scripts/test_top.py"]), 1)

    def test_truncated_suite_counts_as_failure(self):
        # An empty suite file imports clean and runs nothing; it must fail on
        # either branch (exit 5 on 3.12+, the zero-tests check on 3.11).
        target = self._target(
            **{"scripts/tests/__init__.py": "", "scripts/tests/test_a.py": ""}
        )
        self.assertEqual(
            materialize.verify_runtime(target, ["scripts/tests/test_a.py"]), 1
        )

    def test_all_skipped_suite_is_not_a_failure(self):
        target = self._target(
            **{
                "scripts/tests/__init__.py": "",
                "scripts/tests/test_a.py": AN_ALL_SKIPPED_SUITE,
            }
        )
        self.assertEqual(
            materialize.verify_runtime(target, ["scripts/tests/test_a.py"]), 0
        )

    def test_forced_color_output_still_counts_runs_and_skips(self):
        # Python 3.13+ colorizes unittest output under FORCE_COLOR, which -E
        # does not strip; the counters must read through the SGR escapes.
        target = self._target(
            **{
                "scripts/tests/__init__.py": "",
                "scripts/tests/test_a.py": AN_ALL_SKIPPED_SUITE,
            }
        )
        with mock.patch.dict(os.environ, {"FORCE_COLOR": "1"}):
            self.assertEqual(
                materialize.verify_runtime(target, ["scripts/tests/test_a.py"]), 0
            )

    def test_stale_pycache_is_purged_before_the_run(self):
        # copy2 preserves mtime and size, the pyc invalidation key, so a
        # pre-existing cache artifact could stay import-valid across the install.
        target = self._target(
            **{
                "scripts/tests/__init__.py": "",
                "scripts/tests/test_a.py": A_PASSING_SUITE,
                "scripts/tests/__pycache__/test_a.cpython-311.pyc": ANY_CONTENT,
            }
        )
        self.assertEqual(
            materialize.verify_runtime(target, ["scripts/tests/test_a.py"]), 0
        )
        self.assertFalse((target / "scripts/tests/__pycache__").exists())

    def test_caller_pythonpath_is_ignored(self):
        pythonpath_only = a_target(self)
        (pythonpath_only / "helper_only_on_pythonpath.py").write_text(
            "VALUE = 1\n", encoding="utf-8"
        )
        target = self._target(
            **{
                "scripts/tests/__init__.py": "",
                "scripts/tests/test_a.py": "import helper_only_on_pythonpath\n"
                + A_PASSING_SUITE,
            }
        )
        with mock.patch.dict(os.environ, {"PYTHONPATH": str(pythonpath_only)}):
            self.assertEqual(
                materialize.verify_runtime(target, ["scripts/tests/test_a.py"]), 1
            )

    def test_diagnostic_tail_strips_control_characters(self):
        # Suite output is target-influenced; a raw ESC in the failure tail
        # could rewrite the operator's terminal.
        stderr = "early line\n" + "AssertionError: boom \x1b]0;t\x07\x9btail\n"
        tail = materialize._diagnostic_tail(stderr)
        self.assertEqual(tail, ["early line", "AssertionError: boom ]0;ttail"])
        target = self._target(
            **{
                "scripts/tests/__init__.py": "",
                "scripts/tests/test_bad.py": A_FAILING_SUITE,
            }
        )
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured):
            self.assertEqual(
                materialize.verify_runtime(target, ["scripts/tests/test_bad.py"]), 1
            )
        text = captured.getvalue()
        self.assertIn("FAILED", text)
        self.assertFalse(re.search(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]", text))

    def test_an_install_with_no_suites_verifies_clean(self):
        self.assertEqual(materialize.verify_runtime(self._target(), []), 0)

    def test_no_verify_flag_skips_the_run(self):
        target = a_target(self, COPY_LAYOUT)
        out = run_materialize("generic", target)
        self.assertNotIn("verified:", out)


class RecordExtension(unittest.TestCase):
    """The durable-keep primitive: a layout entry plus the channel-aware .gitignore re-include."""

    def _target(self, channel):
        target = a_target(self, f'[harness]\nchannel = "{channel}"\nextensions = []\n')
        plant(target, f"{AN_EXTENSION_SKILL}/SKILL.md")
        plant(target, AN_EXTENSION_AGENT)
        return target

    def _record(self, target, path):
        return run_script("record-extension", str(target), path)

    def _layout(self, target):
        return (target / "scripts/layout.toml").read_text()

    def test_a_directory_and_a_file_get_their_gitignore_reinclude_forms(self):
        target = self._target("manifest")
        r1 = self._record(target, AN_EXTENSION_SKILL)
        r2 = self._record(target, AN_EXTENSION_AGENT)
        self.assertEqual((r1.returncode, r2.returncode), (0, 0), r1.stderr + r2.stderr)
        self.assertIn(
            f'extensions = ["{AN_EXTENSION_SKILL}", "{AN_EXTENSION_AGENT}"]',
            self._layout(target),
        )
        gi = (target / ".gitignore").read_text().splitlines()
        self.assertIn(f"!{AN_EXTENSION_SKILL}/", gi)
        self.assertIn(f"!{AN_EXTENSION_AGENT}", gi)

    def test_a_second_record_is_a_noop_and_the_copy_channel_writes_no_gitignore(self):
        target = self._target("copy")
        self._record(target, AN_EXTENSION_SKILL)
        r = self._record(target, AN_EXTENSION_SKILL)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("already recorded", r.stdout)
        self.assertEqual(self._layout(target).count(AN_EXTENSION_SKILL), 1)
        self.assertFalse((target / ".gitignore").exists())

    def test_missing_path_fails_loud(self):
        target = self._target("manifest")
        r = self._record(target, ".claude/skills/no-such-skill")
        self.assertEqual(r.returncode, 1)
        self.assertIn("does not exist", r.stderr)

    def test_a_quote_newline_or_dot_dot_path_is_rejected(self):
        # The path lands verbatim in layout.toml and .gitignore, so a quote
        # or newline would add config lines and dot-dot would leave the target.
        target = self._target("manifest")
        quoted_dir = '.claude/skills/q", "uoted'
        (target / quoted_dir).mkdir(parents=True)
        for path in (
            quoted_dir,
            '.claude/skills/x"]\nsize_threshold = 9',
            "../outside",
            "/etc/passwd",
        ):
            r = self._record(target, path)
            self.assertEqual(r.returncode, 1, path)
        self.assertIn("extensions = []", self._layout(target))

    def test_comma_backslash_and_degenerate_paths_are_rejected(self):
        # A comma corrupts the array's comma-joined re-parse on the next
        # record; a backslash is a TOML escape; "" and "." would record the
        # whole target as one extension.
        target = self._target("manifest")
        (target / ".claude/skills/a,b").mkdir(parents=True)
        (target / ".claude/skills/a\\b").mkdir(parents=True)
        for path in (".claude/skills/a,b", ".claude/skills/a\\b", ".", "/", "./"):
            r = self._record(target, path)
            self.assertEqual(r.returncode, 1, path)
        self.assertIn("extensions = []", self._layout(target))

    def test_dead_reinclude_under_bare_dir_ignore_fails_loud(self):
        # git never descends into a dir ignored by the bare "dir/" form, so
        # a "!path/" re-include under it is silently dead.
        target = self._target("manifest")
        subprocess.run(
            ["git", "init", "-q"], cwd=target, check=True, capture_output=True
        )
        (target / ".gitignore").write_text(".claude/\n")
        r = self._record(target, AN_EXTENSION_SKILL)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("still gitignored", r.stderr)


class PlanInstall(unittest.TestCase):
    """The --dry-run plan: the source tree stat against the target's disk, no install required."""

    def snapshot(self, target):
        return {
            p.relative_to(target).as_posix(): p.read_bytes()
            for p in target.rglob("*")
            if p.is_file()
        }

    def test_greenfield_is_all_created(self):
        created, overwritten = materialize.plan_install("go", a_target(self), [])
        self.assertEqual(overwritten, [])
        self.assertIn(".claude/agents/README.md", created)
        self.assertEqual(created, sorted(set(created)))

    def test_present_file_moves_to_overwritten(self):
        target = a_target(self)
        rel = ".claude/agents/README.md"
        plant(target, rel)
        created, overwritten = materialize.plan_install("go", target, [])
        self.assertIn(rel, overwritten)
        self.assertNotIn(rel, created)

    def test_core_stack_overlap_counted_once(self):
        created, overwritten = materialize.plan_install("go", a_target(self), [])
        allrels = created + overwritten
        self.assertEqual(len(allrels), len(set(allrels)))

    def test_dry_run_writes_nothing(self):
        target = a_target(self)
        result = run_script("go", str(target), "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dry run — nothing written", result.stdout)
        self.assertIn("--- plan create:", result.stdout)
        self.assertEqual(list(target.iterdir()), [])

    def test_dry_run_leaves_populated_target_byte_identical(self):
        # A populated target gives every refresh writer and the runtime copy
        # something to touch; the plan must still write nothing.
        target = a_target(self, COPY_LAYOUT)
        plant(target, "CLAUDE.md", "# Widget\n\ncontent\n")
        plant(target, ".gitignore", "*.tmp\n")
        plant(target, ".claude/agents/README.md")
        plant(target, ".claude/skills/mine/SKILL.md")
        before = self.snapshot(target)
        result = run_script("go", str(target), "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--- plan overwrite:", result.stdout)
        self.assertEqual(self.snapshot(target), before)


if __name__ == "__main__":
    unittest.main()
