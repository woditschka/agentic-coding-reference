#!/usr/bin/env python3
"""Pin the agent-mirror render, prune, and variant contracts on a throwaway layer."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import ROOT

_SCRIPT = ROOT / "render-agent-mirrors.py"

BASE_LINK_PREFIX = "../skills/"
MIRROR_LINK_PREFIX = "../../.claude/skills/"
IN_BODY_RULE_LINE = "A rule above this line is body content, not a fence."

BASE = f"""---
name: sample
tools:
  - Read
---
# Sample Agent

Read [the handoff rules]({BASE_LINK_PREFIX}handoff-routing/SKILL.md) first.

---

{IN_BODY_RULE_LINE}
"""

OPENCODE_FRONTMATTER = "---\nmode: subagent\npermission:\n  edit: deny\n---\n"
OPENCODE = OPENCODE_FRONTMATTER + "Stale opencode body.\n"
COPILOT = (
    "---\nname: Sample\nmodel: Claude Opus 4.7 (copilot)\n---\nStale copilot body.\n"
)

MIRRORS = (
    ".opencode/agents/sample.md",
    ".github/agents/sample.agent.md",
)

VARIANT = """---
name: sample-routine
variant-of: sample
effort: medium
---
"""

SOME_README = "roster notes\n"
ANY_TEXT = "x\n"


def an_agent_file(name):
    return f"---\nname: {name}\n---\nold\n"


def body_of(text):
    lines = text.splitlines()
    fences = 0
    for i, line in enumerate(lines):
        if line.rstrip(" \t") == "---" and line.lstrip(" \t") == "---":
            fences += 1
            if fences == 2:
                return lines[i + 1 :]
    return []


class MirrorRender(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.layer = self.root / "layer"
        for d in (
            ".claude/agents",
            ".opencode/agents",
            ".github/agents",
        ):
            (self.layer / d).mkdir(parents=True)
        self.write(".claude/agents/sample.md", BASE)
        self.write(".claude/agents/README.md", SOME_README)
        self.write(".opencode/agents/sample.md", OPENCODE)
        self.write(".github/agents/sample.agent.md", COPILOT)

    def write(self, relpath, text):
        (self.layer / relpath).write_text(text, encoding="utf-8")

    def read(self, relpath):
        return (self.layer / relpath).read_text(encoding="utf-8")

    def run_render(self, layer=None):
        return subprocess.run(
            [sys.executable, str(_SCRIPT), str(layer or self.layer)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_a_drifted_mirror_takes_the_base_body_with_mirror_links(self):
        result = self.run_render()
        self.assertEqual(result.returncode, 0)
        self.assertIn(
            f"{len(MIRRORS)} rendered, 0 already current, 0 pruned", result.stdout
        )

        expected_body = [
            line.replace(BASE_LINK_PREFIX, MIRROR_LINK_PREFIX) for line in body_of(BASE)
        ]
        for mirror in MIRRORS:
            text = self.read(mirror)
            self.assertEqual(body_of(text), expected_body, mirror)
            self.assertIn(f"{MIRROR_LINK_PREFIX}handoff-routing", text)
            self.assertIn(IN_BODY_RULE_LINE, text)
        self.assertTrue(
            self.read(".opencode/agents/sample.md").startswith(OPENCODE_FRONTMATTER)
        )

    def test_second_render_is_a_byte_stable_noop(self):
        self.run_render()
        snapshot = [self.read(m) for m in MIRRORS]
        result = self.run_render()
        self.assertIn(
            f"0 rendered, {len(MIRRORS)} already current, 0 pruned", result.stdout
        )
        self.assertEqual([self.read(m) for m in MIRRORS], snapshot)

    def test_readme_is_never_a_base(self):
        # README has no mirrors; a clean run proves it was skipped.
        self.assertEqual(self.run_render().returncode, 0)

    def test_missing_mirror_fails_loud(self):
        (self.layer / ".opencode/agents/sample.md").unlink()
        result = self.run_render()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing mirror", result.stderr)

    def test_base_with_mirror_link_form_fails(self):
        self.write(
            ".claude/agents/sample.md",
            f"---\nname: sample\n---\nBad [link]({MIRROR_LINK_PREFIX}x/SKILL.md).\n",
        )
        result = self.run_render()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mirror link form", result.stderr)

    def test_base_with_broken_two_up_skill_link_fails(self):
        self.write(
            ".claude/agents/sample.md",
            "---\nname: sample\n---\nBad [link](../../skills/x/SKILL.md).\n",
        )
        result = self.run_render()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("../../skills/", result.stderr)

    def test_malformed_base_and_empty_body_fail(self):
        self.write(".claude/agents/sample.md", "name: sample\nno fences\n")
        self.assertIn("no frontmatter fence pair", self.run_render().stderr)
        self.write(".claude/agents/sample.md", "---\nname: sample\n---\n")
        self.assertIn("empty body", self.run_render().stderr)

    def test_orphaned_mirrors_pruned_readmes_and_strays_survive(self):
        orphans = (
            ".opencode/agents/retired.md",
            ".github/agents/retired.agent.md",
        )
        kept = (
            ".github/agents/README.md",
            ".opencode/agents/README.md",
            ".opencode/agents/notes.txt",
        )
        for orphan in orphans:
            self.write(orphan, an_agent_file("retired"))
        for path in kept:
            self.write(path, ANY_TEXT)
        result = self.run_render()
        self.assertIn(
            f"{len(MIRRORS)} rendered, 0 already current, {len(orphans)} pruned",
            result.stdout,
        )
        for orphan in orphans:
            self.assertFalse((self.layer / orphan).exists(), orphan)
        for path in kept:
            self.assertTrue((self.layer / path).is_file(), path)

    def test_prune_skipped_while_the_layer_fails(self):
        self.write(".opencode/agents/orphan.md", an_agent_file("orphan"))
        (self.layer / ".opencode/agents/sample.md").unlink()
        result = self.run_render()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.layer / ".opencode/agents/orphan.md").is_file())
        self.write(".opencode/agents/sample.md", OPENCODE)
        self.run_render()
        self.assertFalse((self.layer / ".opencode/agents/orphan.md").exists())

    def test_empty_roster_fails_and_prunes_nothing(self):
        empty = self.root / "empty-layer"
        for d in (
            ".claude/agents",
            ".opencode/agents",
            ".github/agents",
        ):
            (empty / d).mkdir(parents=True)
        (empty / ".claude/agents/README.md").write_text(SOME_README, encoding="utf-8")
        keeper = empty / ".opencode/agents/keeper.md"
        keeper.write_text(an_agent_file("keeper"), encoding="utf-8")
        result = self.run_render(layer=empty)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("roster empty or path renamed", result.stderr)
        self.assertTrue(keeper.is_file())

    def test_missing_agents_dir_fails(self):
        result = self.run_render(layer=self.root / "nowhere")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no .claude/agents under", result.stderr)

    def add_variant_with_mirrors(self, name="sample-routine", frontmatter=VARIANT):
        self.write(f".claude/agents/{name}.md", frontmatter)
        self.write(f".opencode/agents/{name}.md", OPENCODE)
        self.write(f".github/agents/{name}.agent.md", COPILOT)

    def test_variant_body_renders_from_base_and_keeps_its_frontmatter(self):
        self.add_variant_with_mirrors()
        result = self.run_render()
        self.assertEqual(result.returncode, 0, result.stderr)
        variant = self.read(".claude/agents/sample-routine.md")
        self.assertTrue(variant.startswith(VARIANT.rstrip("\n") + "\n"))
        self.assertEqual(body_of(variant), body_of(BASE))
        mirror = self.read(".opencode/agents/sample-routine.md")
        self.assertIn(f"{MIRROR_LINK_PREFIX}handoff-routing/SKILL.md", mirror)
        again = self.run_render()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("0 rendered", again.stdout)
        self.assertEqual(self.read(".claude/agents/sample-routine.md"), variant)

    def test_variant_missing_target_fails(self):
        self.add_variant_with_mirrors(
            frontmatter=VARIANT.replace("variant-of: sample", "variant-of: nowhere")
        )
        result = self.run_render()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has no base", result.stderr)

    def test_variant_not_named_target_routine_is_refused_unrewritten(self):
        self.add_variant_with_mirrors()
        self.add_variant_with_mirrors(
            name="sample-slow",
            frontmatter="---\nname: sample-slow\nvariant-of: sample\n---\n",
        )
        result = self.run_render()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is not named sample-routine", result.stderr)
        self.assertNotIn("Sample Agent", self.read(".claude/agents/sample-slow.md"))

    def test_variant_chain_fails(self):
        self.add_variant_with_mirrors()
        self.add_variant_with_mirrors(
            name="sample-turbo",
            frontmatter="---\nname: sample-turbo\nvariant-of: sample-routine\n---\n",
        )
        result = self.run_render()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("chains variant-of", result.stderr)


if __name__ == "__main__":
    unittest.main()
