#!/usr/bin/env python3
"""Tests for init.py (stdlib only).

Run: python3 harness/test_init.py

Pins the scaffold contract: project-owned files created once and never
overwritten, placeholder fill with no {{ leaks, channel/tool normalization on
a fresh layout.toml, the additive [harness] injection on a legacy one, the
channel-aware .gitignore block sharing one sentinel with refresh-gitignore,
and the tracked-runtime migration note.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_INIT = _HERE / "init.py"


def run_init(target, stack, *args, check=True):
    result = subprocess.run(
        [sys.executable, str(_INIT), stack, str(target), *args],
        capture_output=True, text=True, check=False,
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
        for rel in ("CLAUDE.md", "docs/prd.md", "docs/system-design.md",
                    "docs/adr/README.md", "scripts/layout.toml",
                    ".claude/settings.json"):
            self.assertTrue((self.target / rel).is_file(), rel)
            self.assertNotIn("{{", self.read(rel), f"placeholder leaked in {rel}")

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
            'test_name_pattern = "^Test"\n', encoding="utf-8")
        result = run_init(self.target, "go", "W", "d", "", "", "manifest")
        self.assertIn("harness-table-injected=1", result.stdout)
        layout = self.read("scripts/layout.toml")
        self.assertTrue(layout.startswith('test_name_pattern = "^Test"\n'),
                        "existing project key was touched")
        self.assertIn("[harness]", layout)
        self.assertIn('channel = "manifest"', layout)

    def test_gitignore_copy_channel_ignores_only_the_ledger(self):
        run_init(self.target, "go", "W", "d")
        gitignore = self.read(".gitignore")
        self.assertIn(".scratch/", gitignore.splitlines())
        self.assertNotIn(".claude/skills/*", gitignore)

    def test_gitignore_manifest_channel_appends_runtime_block_once(self):
        run_init(self.target, "go", "W", "d", "", "", "manifest")
        first = self.read(".gitignore")
        self.assertIn("scripts/brief_doctor.py", first.splitlines())
        run_init(self.target, "go", "W", "d", "", "", "manifest")
        self.assertEqual(self.read(".gitignore"), first, "block re-appended")

    def test_refresh_then_init_shares_one_gitignore_sentinel(self):
        # The refresh writes its terse "harness runtime" header; init run
        # second must RECOGNIZE that block and not re-append the whole thing.
        # A detection-token mismatch double-appends every runtime path.
        subprocess.run(
            [sys.executable, str(_HERE / "refresh-gitignore.py"),
             str(self.target / ".gitignore"),
             str(_HERE / "init/core/gitignore-runtime.txt"), "manifest"],
            check=True, capture_output=True,
        )
        run_init(self.target, "go", "W", "d", "", "claude", "manifest")
        lines = self.read(".gitignore").splitlines()
        self.assertEqual(lines.count(".scratch/"), 1)
        self.assertEqual(lines.count("scripts/brief_doctor.py"), 1)

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
