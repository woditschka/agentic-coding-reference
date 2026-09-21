#!/usr/bin/env python3
"""Pin the scaffold contract of init.py: create once, fill without leaks, honor the declared layout."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import ROOT, load

_INIT = ROOT / "init.py"

init_mod = load("init_mod", "init.py")

SOME_PROJECT_NAME = "Widget"
SOME_DESCRIPTION = "A demo service"
HARNESS_STAMP = r"^<!-- harness: \d{4}-\d{2}-\d{2} -->$"
EXECUTABLE_MODE = 0o755
UNKNOWN_TOOL = "copilott"
UNKNOWN_CHANNEL = "floppy"
SLUGS_OUTSIDE_REGISTRY = ("java", "", "..", "../core", "/etc")
LEGACY_LAYOUT = 'test_name_pattern = "^Test"\n'
LEDGER_IGNORE = ".scratch/"
A_RUNTIME_IGNORE = "scripts/doctor.py"
RUNTIME_SKILLS_IGNORE = ".claude/skills/*"
MANAGED_CHAPTER = "## Agent Usage (Mandatory)"
REALIZATION_HEADING = "## Language Realization"
REALIZATION_SLOT_COMMENT = "<!-- How this project implements"
A_FILLED_CHAPTER_MIN_CHARS = 100
SCAFFOLDED_FILES = (
    "CLAUDE.md",
    "docs/prd.md",
    "docs/system-design.md",
    "docs/adr/README.md",
    "scripts/layout.toml",
    ".claude/settings.json",
)


def token(name):
    # Assembled at runtime: a literal token in this file would trip the
    # battery's placeholder gate, which allows tokens only in templates.
    return "{{" + name + "}}"


def init_result(target, stack, *, tools="", channel=""):
    return subprocess.run(
        [
            sys.executable,
            str(_INIT),
            stack,
            str(target),
            SOME_PROJECT_NAME,
            SOME_DESCRIPTION,
            "",
            tools,
            channel,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def run_init(target, stack, *, tools="", channel=""):
    result = init_result(target, stack, tools=tools, channel=channel)
    if result.returncode != 0:
        raise AssertionError(f"init failed: {result.stderr}")
    return result


class Scaffold(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.target = Path(td.name)

    def read(self, rel):
        return (self.target / rel).read_text(encoding="utf-8")

    def write_layout(self, text):
        (self.target / "scripts").mkdir()
        (self.target / "scripts/layout.toml").write_text(text, encoding="utf-8")

    def test_shipped_backlog_skeleton_is_unbound(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "backlog_engine", ROOT / "core" / "scripts" / "backlog.py"
        )
        assert spec is not None and spec.loader is not None
        engine = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(engine)
        skeleton = ROOT / "init" / "core" / "scripts" / "backlog.sh"
        mode, items = engine.board_items(skeleton, self.target)
        self.assertEqual((mode, items), ("unbound", []))

    def test_greenfield_scaffold_fills_placeholders(self):
        result = run_init(self.target, "go")
        self.assertIn("created, 0 pre-existing kept", result.stdout)
        claude_md = self.read("CLAUDE.md")
        self.assertIn(SOME_PROJECT_NAME, claude_md)
        self.assertIn(SOME_DESCRIPTION, claude_md)
        for rel in SCAFFOLDED_FILES:
            self.assertTrue((self.target / rel).is_file(), rel)
            self.assertNotIn("{{", self.read(rel), rel)

    def test_fill_reports_unmapped_tokens_and_ignores_fill_marker(self):
        unmapped = "HARNESS_DATE"
        p = self.target / "doc.md"
        p.write_text(
            f"{token('PROJECT_NAME')} {token(unmapped)} {token('FILL')}\n",
            encoding="utf-8",
        )
        with init_mod.write_guard.write_scope(self.target):
            leaks = init_mod.fill(p, {"PROJECT_NAME": SOME_PROJECT_NAME})
        self.assertEqual(leaks, [unmapped])
        self.assertIn(SOME_PROJECT_NAME, self.read("doc.md"))

    def test_fill_preserves_the_executable_bit(self):
        p = self.target / "stack.sh"
        p.write_text(
            f"#!/usr/bin/env bash\n# {token('PROJECT_NAME')}\n", encoding="utf-8"
        )
        p.chmod(EXECUTABLE_MODE)
        with init_mod.write_guard.write_scope(self.target):
            init_mod.fill(p, {"PROJECT_NAME": SOME_PROJECT_NAME})
        self.assertEqual(p.stat().st_mode & 0o777, EXECUTABLE_MODE)

    def test_unknown_stack_fails_loud_and_scaffolds_nothing(self):
        # "", "..", and an absolute slug are the pathlib traps membership
        # must also reject.
        for slug in SLUGS_OUTSIDE_REGISTRY:
            with self.subTest(slug=slug), tempfile.TemporaryDirectory() as td:
                target = Path(td)
                result = init_result(target, slug)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unknown stack", result.stderr)
                self.assertIn("java-spring-boot", result.stderr)
                self.assertFalse((target / "CLAUDE.md").exists())

    def test_unknown_tool_fails_loud_and_scaffolds_nothing(self):
        result = init_result(self.target, "go", tools=f"claude, {UNKNOWN_TOOL}")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(UNKNOWN_TOOL, result.stderr)
        self.assertIn("valid:", result.stderr)
        self.assertFalse((self.target / "CLAUDE.md").exists())

    def test_rerun_never_overwrites(self):
        run_init(self.target, "go")
        (self.target / "CLAUDE.md").write_text("# mine\n", encoding="utf-8")
        result = run_init(self.target, "go")
        lines = self.read("CLAUDE.md").splitlines()
        self.assertRegex(lines[0], HARNESS_STAMP)
        self.assertEqual(lines[1:], ["# mine"])
        self.assertIn("0 created", result.stdout)

    def test_fresh_layout_normalized_to_requested_channel_and_tools(self):
        run_init(self.target, "generic", tools="claude, opencode", channel="manifest")
        layout = self.read("scripts/layout.toml")
        self.assertIn('channel = "manifest"', layout)
        self.assertIn('tools = ["claude", "opencode"]', layout)

    def test_claude_is_forced_on(self):
        run_init(self.target, "generic", tools="opencode", channel="copy")
        self.assertIn(
            'tools = ["claude", "opencode"]', self.read("scripts/layout.toml")
        )

    def test_legacy_layout_gains_harness_table_additively(self):
        self.write_layout(LEGACY_LAYOUT)
        result = run_init(self.target, "go", channel="manifest")
        self.assertIn("harness-table-injected=1", result.stdout)
        layout = self.read("scripts/layout.toml")
        self.assertTrue(layout.startswith(LEGACY_LAYOUT))
        self.assertIn("[harness]", layout)
        self.assertIn('channel = "manifest"', layout)

    def test_marketplace_settings_carry_no_project_hook_matchers(self):
        # The plugin registers its hooks via its own hooks.json; a project-side
        # matcher would name a script that never exists on disk there.
        run_init(self.target, "go", channel="marketplace")
        settings = json.loads(self.read(".claude/settings.json"))
        self.assertNotIn("hooks", settings)
        self.assertIn("env", settings)

    def test_copy_settings_keep_the_hook_matchers(self):
        run_init(self.target, "go")
        self.assertIn(
            ".claude/hooks/handoff-allow.py", self.read(".claude/settings.json")
        )

    def test_conflicting_channel_argument_fails_loud(self):
        run_init(self.target, "generic", channel="copy")
        (self.target / "docs/prd.md").unlink()
        result = init_result(self.target, "generic", channel="marketplace")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("never flips", result.stderr)
        self.assertFalse((self.target / "docs/prd.md").exists())
        self.assertIn('channel = "copy"', self.read("scripts/layout.toml"))

    def test_rerun_adopts_declared_channel_in_summary_and_gitignore(self):
        run_init(self.target, "generic", channel="manifest")
        (self.target / ".gitignore").unlink()
        result = run_init(self.target, "generic")
        self.assertIn("channel=manifest", result.stdout)
        self.assertIn(RUNTIME_SKILLS_IGNORE, self.read(".gitignore"))

    def test_invalid_declared_channel_fails_loud(self):
        run_init(self.target, "generic")
        layout = self.target / "scripts/layout.toml"
        layout.write_text(
            layout.read_text(encoding="utf-8").replace(
                'channel = "copy"', f'channel = "{UNKNOWN_CHANNEL}"'
            ),
            encoding="utf-8",
        )
        result = init_result(self.target, "generic")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(UNKNOWN_CHANNEL, result.stderr)

    def test_declared_unknown_tool_fails_loud_before_writes(self):
        self.write_layout(f'[harness]\ntools = ["claude", "{UNKNOWN_TOOL}"]\n')
        result = init_result(self.target, "go")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"unknown tool(s) {UNKNOWN_TOOL}", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.target / "CLAUDE.md").exists())

    def test_declared_malformed_extensions_fails_loud_before_writes(self):
        self.write_layout("[harness]\nextensions = [123]\n")
        result = init_result(self.target, "go")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("extensions must be a list of strings", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.target / "CLAUDE.md").exists())

    @unittest.skipIf(os.geteuid() == 0, "root reads through chmod 000")
    def test_unreadable_layout_reports_one_clean_line(self):
        self.write_layout('[harness]\nchannel = "copy"\n')
        lt = self.target / "scripts/layout.toml"
        lt.chmod(0o000)
        try:
            result = init_result(self.target, "go")
        finally:
            lt.chmod(0o644)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unreadable", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_gitignore_copy_channel_ignores_only_the_ledger(self):
        run_init(self.target, "go")
        gitignore = self.read(".gitignore")
        self.assertIn(LEDGER_IGNORE, gitignore.splitlines())
        self.assertNotIn(RUNTIME_SKILLS_IGNORE, gitignore)

    def test_gitignore_manifest_channel_appends_runtime_block_once(self):
        run_init(self.target, "go", channel="manifest")
        first = self.read(".gitignore")
        self.assertIn(A_RUNTIME_IGNORE, first.splitlines())
        run_init(self.target, "go", channel="manifest")
        self.assertEqual(self.read(".gitignore"), first)

    def test_refresh_then_init_shares_one_gitignore_sentinel(self):
        # A detection-token mismatch between the two writers would append
        # the whole runtime block a second time.
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "refresh-gitignore.py"),
                str(self.target / ".gitignore"),
                str(ROOT / "init/core/gitignore-runtime.txt"),
                "manifest",
            ],
            check=True,
            capture_output=True,
        )
        run_init(self.target, "go", tools="claude", channel="manifest")
        lines = self.read(".gitignore").splitlines()
        self.assertEqual(lines.count(LEDGER_IGNORE), 1)
        self.assertEqual(lines.count(A_RUNTIME_IGNORE), 1)

    def test_tracked_runtime_reports_untrack_note(self):
        skill = self.target / ".claude/skills/tdd-workflow/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.target)], check=True)
        subprocess.run(["git", "-C", str(self.target), "add", "-A"], check=True)
        result = run_init(self.target, "go", channel="manifest")
        self.assertIn("tracked-runtime-file(s)-need-untracking", result.stdout)
        self.assertIn("git", result.stderr)
        self.assertIn("rm -r --cached --ignore-unmatch", result.stderr)

    def test_invalid_channel_argument_fails(self):
        result = init_result(self.target, "go", channel=UNKNOWN_CHANNEL)
        self.assertEqual(result.returncode, 1)
        self.assertIn("channel must be", result.stderr)

    def test_managed_chapters_are_filled(self):
        run_init(self.target, "go")
        claude_md = self.read("CLAUDE.md")
        self.assertIn(MANAGED_CHAPTER, claude_md)
        agent_usage = claude_md.split(MANAGED_CHAPTER, 1)[1]
        body = agent_usage.split("\n## ", 1)[0]
        self.assertGreater(len(body.strip()), A_FILLED_CHAPTER_MIN_CHARS)

    def test_language_realization_filled_from_the_stack_fragment(self):
        run_init(self.target, "java-spring-boot")
        brief = self.read("docs/architecture-principles.md")
        fragment = (
            ROOT / "stacks/java-spring-boot" / init_mod.TEMPLATES_REL
        ) / "architecture-principles.realization.md"
        self.assertIn(REALIZATION_HEADING, brief)
        self.assertIn(fragment.read_text(encoding="utf-8").strip("\n"), brief)
        self.assertNotIn(REALIZATION_SLOT_COMMENT, brief)

    def test_language_realization_slot_kept_without_a_fragment(self):
        run_init(self.target, "go")
        brief = self.read("docs/architecture-principles.md")
        self.assertIn(REALIZATION_HEADING, brief)
        self.assertIn(REALIZATION_SLOT_COMMENT, brief)

    def test_realize_replaces_only_the_section_body(self):
        text = "# T\n\n## A\n\na\n\n## Language Realization\n\nold\n\n## B\n\nb\n"
        realized = init_mod.realize(text, "new\n")
        self.assertEqual(
            realized,
            "# T\n\n## A\n\na\n\n## Language Realization\n\nnew\n\n## B\n\nb\n",
        )

    def test_realize_returns_none_without_the_section(self):
        self.assertIsNone(init_mod.realize("# T\n\n## A\n\na\n", "new"))

    def test_a_fragment_without_a_slot_in_its_template_fails_loud(self):
        templates = self.target / "templates"
        stack_templates = self.target / "stack"
        templates.mkdir()
        stack_templates.mkdir()
        (templates / "prd.md").write_text("# P\n\n## Goals\n", encoding="utf-8")
        (stack_templates / "prd.realization.md").write_text("body\n", encoding="utf-8")
        dest = self.target / "prd.md"
        dest.write_text(
            (templates / "prd.md").read_text(encoding="utf-8"), encoding="utf-8"
        )
        plan = init_mod.Plan(
            request=init_mod.Request(
                "go", str(self.target), SOME_PROJECT_NAME, SOME_DESCRIPTION, "", "", ""
            ),
            target=self.target,
            channel="copy",
            templates=templates,
            stack_templates=stack_templates,
            toml_array='["claude"]',
            replacements={},
            layout=self.target / "scripts/layout.toml",
            layout_preexisting=False,
        )
        with self.assertRaises(init_mod.InitError) as raised:
            init_mod._fill_realization(plan, "prd.md", dest)
        self.assertIn(REALIZATION_HEADING, raised.exception.message)

    def test_harness_date_stamped_on_line_one(self):
        run_init(self.target, "go")
        first_line = self.read("CLAUDE.md").splitlines()[0]
        self.assertRegex(first_line, HARNESS_STAMP)


if __name__ == "__main__":
    unittest.main()
