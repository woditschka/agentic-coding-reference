#!/usr/bin/env python3
"""Tests for init.py (stdlib only).

Run: python3 harness/tests/test_init.py

Pins the scaffold contract: project-owned files created once and never
overwritten, placeholder fill with no {{ leaks, channel/tool normalization on
a fresh layout.toml, the additive [harness] injection on a legacy one, the
channel-aware .gitignore block sharing one sentinel with refresh-gitignore,
and the tracked-runtime migration note.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import ROOT, load

_INIT = ROOT / "init.py"


def run_init(target, stack, *args, check=True):
    result = subprocess.run(
        [sys.executable, str(_INIT), stack, str(target), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"init failed: {result.stderr}")
    return result


class InitTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.target = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def read(self, rel):
        return (self.target / rel).read_text(encoding="utf-8")

    def test_greenfield_scaffold_fills_placeholders(self):
        result = run_init(self.target, "go", "Widget", "A demo service")
        self.assertIn("created, 0 pre-existing kept", result.stdout)
        claude_md = self.read("CLAUDE.md")
        self.assertIn("Widget", claude_md)
        self.assertIn("A demo service", claude_md)
        for rel in (
            "CLAUDE.md",
            "docs/prd.md",
            "docs/system-design.md",
            "docs/adr/README.md",
            "scripts/layout.toml",
            ".claude/settings.json",
        ):
            self.assertTrue((self.target / rel).is_file(), rel)
            self.assertNotIn("{{", self.read(rel), f"placeholder leaked in {rel}")

    def test_fill_reports_unmapped_tokens_and_ignores_fill_marker(self):
        # The self-verify contract: a skeleton token outside the replacement
        # map surfaces as a leak; the consumer-completed {{FILL}} never does.
        mod = load("init_mod", "init.py")
        # Tokens assembled at runtime: a literal in this file would trip the
        # battery's placeholder gate, which allows tokens only in templates.
        tok = lambda name: "{{" + name + "}}"  # noqa: E731
        p = self.target / "doc.md"
        p.write_text(
            f"{tok('PROJECT_NAME')} {tok('HARNESS_DATE')} {tok('FILL')}\n",
            encoding="utf-8",
        )
        leaks = mod.fill(p, {"PROJECT_NAME": "Widget"})
        self.assertEqual(leaks, ["HARNESS_DATE"])
        self.assertIn("Widget", self.read("doc.md"))

    def test_unknown_stack_fails_loud_and_scaffolds_nothing(self):
        # The same guard materialize.py carries: a slug outside registry.STACKS
        # must error, not silently scaffold the core layer alone (the overlay
        # loop skips a missing stacks/<stack>) and report success — the
        # java-vs-java-spring-boot trap. "", "..", and absolute slugs are the
        # pathlib traps membership must also reject.
        for slug in ("java", "", "..", "../core", "/etc"):
            with self.subTest(slug=slug), tempfile.TemporaryDirectory() as td:
                target = Path(td)
                result = run_init(target, slug, "Widget", "A demo service", check=False)
                self.assertNotEqual(result.returncode, 0, f"slug {slug!r} was accepted")
                self.assertIn("unknown stack", result.stderr)
                self.assertIn("java-spring-boot", result.stderr)  # valid slugs
                self.assertFalse(
                    (target / "CLAUDE.md").exists(),
                    f"scaffold ran for bad slug {slug!r}",
                )

    def test_unknown_tool_fails_loud_and_scaffolds_nothing(self):
        # The tools twin of the stack-slug guard: a typo'd tool name written
        # into layout.toml would make every later materialize silently drop
        # that tool's surfaces (the doctor filters unknown names without
        # failing). Reject it at scaffold time, where it is fixable.
        result = run_init(
            self.target,
            "go",
            "Widget",
            "A demo service",
            "",
            "claude, copilott",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("copilott", result.stderr)
        self.assertIn("valid:", result.stderr)
        self.assertFalse(
            (self.target / "CLAUDE.md").exists(), "scaffold ran despite an unknown tool"
        )

    def test_rerun_never_overwrites(self):
        run_init(self.target, "go", "Widget", "A demo service")
        (self.target / "CLAUDE.md").write_text("# mine\n", encoding="utf-8")
        result = run_init(self.target, "go", "Widget", "A demo service")
        # The project's content is kept; only the harness date stamp (an
        # upsert refresh-chapters owns) is prepended.
        lines = self.read("CLAUDE.md").splitlines()
        self.assertRegex(lines[0], r"^<!-- harness: \d{4}-\d{2}-\d{2} -->$")
        self.assertEqual(lines[1:], ["# mine"])
        self.assertIn("0 created", result.stdout)

    def test_fresh_layout_normalized_to_requested_channel_and_tools(self):
        run_init(self.target, "generic", "W", "d", "", "claude, junie", "manifest")
        layout = self.read("scripts/layout.toml")
        self.assertIn('channel = "manifest"', layout)
        self.assertIn('tools = ["claude", "junie"]', layout)

    def test_claude_is_forced_on(self):
        run_init(self.target, "generic", "W", "d", "", "junie", "copy")
        self.assertIn('tools = ["claude", "junie"]', self.read("scripts/layout.toml"))

    def test_legacy_layout_gains_harness_table_additively(self):
        (self.target / "scripts").mkdir()
        (self.target / "scripts/layout.toml").write_text(
            'test_name_pattern = "^Test"\n', encoding="utf-8"
        )
        result = run_init(self.target, "go", "W", "d", "", "", "manifest")
        self.assertIn("harness-table-injected=1", result.stdout)
        layout = self.read("scripts/layout.toml")
        self.assertTrue(
            layout.startswith('test_name_pattern = "^Test"\n'),
            "existing project key was touched",
        )
        self.assertIn("[harness]", layout)
        self.assertIn('channel = "manifest"', layout)

    def test_conflicting_channel_argument_fails_loud(self):
        # A declared channel is authoritative (init never flips it); an
        # explicit conflicting argument must error before any file is
        # written — proceeding would report the argument as applied while
        # layout.toml keeps the old value.
        run_init(self.target, "generic", "W", "d", "", "", "copy")
        (self.target / "docs/prd.md").unlink()
        result = run_init(
            self.target, "generic", "W", "d", "", "", "marketplace", check=False
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("never flips", result.stderr)
        self.assertFalse(
            (self.target / "docs/prd.md").exists(),
            "files were written despite the channel conflict",
        )
        self.assertIn('channel = "copy"', self.read("scripts/layout.toml"))

    def test_rerun_adopts_declared_channel_in_summary_and_gitignore(self):
        # A bare re-run on a manifest project must not fall back to the copy
        # default: the declared channel drives the summary and the gitignore
        # handling, so the report matches what stays on disk.
        run_init(self.target, "generic", "W", "d", "", "", "manifest")
        (self.target / ".gitignore").unlink()
        result = run_init(self.target, "generic", "W", "d")
        self.assertIn("channel=manifest", result.stdout)
        self.assertIn(".claude/skills/*", self.read(".gitignore"))

    def test_invalid_declared_channel_fails_loud(self):
        # The enum guard materialize.py applies, at scaffold time: adopting a
        # typo'd declaration would propagate it into the summary and the
        # channel-dependent steps.
        run_init(self.target, "generic", "W", "d")
        layout = self.target / "scripts/layout.toml"
        layout.write_text(
            layout.read_text(encoding="utf-8").replace(
                'channel = "copy"', 'channel = "floppy"'
            ),
            encoding="utf-8",
        )
        result = run_init(self.target, "generic", "W", "d", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("floppy", result.stderr)

    def _write_layout(self, text):
        (self.target / "scripts").mkdir()
        (self.target / "scripts/layout.toml").write_text(text, encoding="utf-8")

    def test_declared_unknown_tool_fails_loud_before_writes(self):
        # The shared reader lifts init to materialize's tools validation
        # (ADR 2026-07-18): a stale or typo'd declared tool fails loud at
        # scaffold time — a silent read would let every later materialize
        # drop that tool's surfaces.
        self._write_layout('[harness]\ntools = ["claude", "bogus-tool"]\n')
        result = run_init(self.target, "go", "W", "d", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown tool(s) bogus-tool", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(
            (self.target / "CLAUDE.md").exists(), "scaffold ran on a bad declaration"
        )

    def test_declared_malformed_extensions_fails_loud_before_writes(self):
        self._write_layout("[harness]\nextensions = [123]\n")
        result = run_init(self.target, "go", "W", "d", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("extensions must be a list of strings", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.target / "CLAUDE.md").exists())

    @unittest.skipIf(os.geteuid() == 0, "root reads through chmod 000")
    def test_unreadable_layout_reports_one_clean_line(self):
        # OSError parity with the pre-reader init: a permission-denied
        # layout.toml prints one clean diagnostic, never a traceback.
        self._write_layout('[harness]\nchannel = "copy"\n')
        lt = self.target / "scripts/layout.toml"
        lt.chmod(0o000)
        try:
            result = run_init(self.target, "go", "W", "d", check=False)
        finally:
            lt.chmod(0o644)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unreadable", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_gitignore_copy_channel_ignores_only_the_ledger(self):
        run_init(self.target, "go", "W", "d")
        gitignore = self.read(".gitignore")
        self.assertIn(".scratch/", gitignore.splitlines())
        self.assertNotIn(".claude/skills/*", gitignore)

    def test_gitignore_manifest_channel_appends_runtime_block_once(self):
        run_init(self.target, "go", "W", "d", "", "", "manifest")
        first = self.read(".gitignore")
        self.assertIn("scripts/doctor.py", first.splitlines())
        run_init(self.target, "go", "W", "d", "", "", "manifest")
        self.assertEqual(self.read(".gitignore"), first, "block re-appended")

    def test_refresh_then_init_shares_one_gitignore_sentinel(self):
        # The refresh writes its terse "harness runtime" header; init run
        # second must RECOGNIZE that block and not re-append the whole thing.
        # A detection-token mismatch double-appends every runtime path.
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
        run_init(self.target, "go", "W", "d", "", "claude", "manifest")
        lines = self.read(".gitignore").splitlines()
        self.assertEqual(lines.count(".scratch/"), 1)
        self.assertEqual(lines.count("scripts/doctor.py"), 1)

    def test_tracked_runtime_reports_untrack_note(self):
        skill = self.target / ".claude/skills/tdd-workflow/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(self.target)], check=True)
        subprocess.run(["git", "-C", str(self.target), "add", "-A"], check=True)
        result = run_init(self.target, "go", "W", "d", "", "", "manifest")
        self.assertIn("tracked-runtime-file(s)-need-untracking", result.stdout)
        self.assertIn("git", result.stderr)
        self.assertIn("rm -r --cached --ignore-unmatch", result.stderr)

    def test_invalid_channel_fails(self):
        result = run_init(self.target, "go", "W", "d", "", "", "sidecar", check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("channel must be", result.stderr)

    def test_managed_chapters_are_filled(self):
        run_init(self.target, "go", "W", "d")
        claude_md = self.read("CLAUDE.md")
        self.assertIn("## Agent Usage (Mandatory)", claude_md)
        # the chapter body comes from managed-chapters.md, not an empty skeleton
        agent_usage = claude_md.split("## Agent Usage (Mandatory)", 1)[1]
        body = agent_usage.split("\n## ", 1)[0]
        self.assertGreater(len(body.strip()), 100, "managed chapter left empty")

    def test_harness_date_stamped_on_line_one(self):
        run_init(self.target, "go", "W", "d")
        first_line = self.read("CLAUDE.md").splitlines()[0]
        self.assertRegex(first_line, r"^<!-- harness: \d{4}-\d{2}-\d{2} -->$")


if __name__ == "__main__":
    unittest.main()
