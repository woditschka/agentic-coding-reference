#!/usr/bin/env python3
"""Tests for render-agent-mirrors.py (stdlib only), on a throwaway fixture layer.

Run: python3 harness/tests/test_render_agent_mirrors.py

Pins the renderer guards:
  1. A drifted mirror body is rewritten to the base body, with skill links
     rewritten to the mirror form; the mirror's frontmatter stays byte-exact.
  2. A "---" rule inside the body is content, not a fence — it survives.
  3. The render is idempotent: a second run reports 0 rendered, no byte change.
  4. A missing mirror fails; frontmatter is authored, never generated.
  5. A base carrying the mirror link form fails (it would double-rewrite).
  6. README.md is exempt: never treated as an agent base.
  7. A mirror whose base is gone is pruned; READMEs and strays survive.
  7b. Prune never fires on a layer with failures: a renamed base must not
      cost its mirrors' authored frontmatter in the same failing run.
  8. A layer with an empty agent roster fails AND its mirrors survive —
     the mass-deletion path (renamed .claude/agents) stays pinned.
  9. A base linking ../../skills/ fails (the render would over-rewrite it).
  10. A `variant-of:` base renders its body from the named plain base before
      the mirror pass (frontmatter kept, second run byte-stable); a missing
      target and a variant-of chain both fail loud.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import ROOT

_SCRIPT = ROOT / "render-agent-mirrors.py"

BASE = """---
name: sample
tools:
  - Read
---
# Sample Agent

Read [the handoff rules](../skills/handoff-routing/SKILL.md) first.

---

A rule above this line is body content, not a fence.
"""

JUNIE = "---\nname: sample\nmodel: opus\n---\nStale junie body.\n"
OPENCODE = "---\nmode: subagent\npermission:\n  edit: deny\n---\nStale opencode body.\n"
COPILOT = (
    "---\nname: Sample\nmodel: Claude Opus 4.7 (copilot)\n---\nStale copilot body.\n"
)

MIRRORS = (
    ".junie/agents/sample.md",
    ".opencode/agents/sample.md",
    ".github/agents/sample.agent.md",
)


VARIANT = """---
name: sample-routine
variant-of: sample
effort: medium
---
"""


def body_of(text):
    lines = text.splitlines()
    fences = 0
    for i, line in enumerate(lines):
        if line.rstrip(" \t") == "---" and line.lstrip(" \t") == "---":
            fences += 1
            if fences == 2:
                return lines[i + 1 :]
    return []


class RendererTest(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.layer = Path(self.td.name) / "layer"
        for d in (
            ".claude/agents",
            ".junie/agents",
            ".opencode/agents",
            ".github/agents",
        ):
            (self.layer / d).mkdir(parents=True)
        self.write(".claude/agents/sample.md", BASE)
        self.write(".claude/agents/README.md", "Roster notes — not an agent.\n")
        self.write(".junie/agents/sample.md", JUNIE)
        self.write(".opencode/agents/sample.md", OPENCODE)
        self.write(".github/agents/sample.agent.md", COPILOT)

    def tearDown(self):
        self.td.cleanup()

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

    def test_render_fixes_drift_keeps_frontmatter_rewrites_links(self):
        result = self.run_render()
        self.assertEqual(result.returncode, 0)
        self.assertIn("3 rendered, 0 already current, 0 pruned", result.stdout)

        expected_body = [
            l.replace("../skills/", "../../.claude/skills/") for l in body_of(BASE)
        ]
        for mirror in MIRRORS:
            text = self.read(mirror)
            self.assertEqual(body_of(text), expected_body, mirror)
            self.assertIn("../../.claude/skills/handoff-routing", text)
            self.assertIn("body content, not a fence", text)  # in-body --- survives
        # mirror frontmatter untouched
        self.assertIn(
            "edit: deny",
            "\n".join(self.read(".opencode/agents/sample.md").splitlines()[:4]),
        )

    def test_second_render_is_a_byte_stable_noop(self):
        self.run_render()
        snapshot = [self.read(m) for m in MIRRORS]
        result = self.run_render()
        self.assertIn("0 rendered, 3 already current, 0 pruned", result.stdout)
        self.assertEqual([self.read(m) for m in MIRRORS], snapshot)

    def test_readme_is_never_a_base(self):
        # README has no mirrors; a clean run proves it was skipped.
        self.assertEqual(self.run_render().returncode, 0)

    def test_missing_mirror_fails_loud(self):
        (self.layer / ".junie/agents/sample.md").unlink()
        result = self.run_render()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing mirror", result.stderr)

    def test_base_with_mirror_link_form_fails(self):
        self.write(
            ".claude/agents/sample.md",
            "---\nname: sample\n---\nBad [link](../../.claude/skills/x/SKILL.md).\n",
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
        self.write(".junie/agents/retired.md", "---\nname: retired\n---\nold\n")
        self.write(".opencode/agents/retired.md", "---\nname: retired\n---\nold\n")
        self.write(".github/agents/retired.agent.md", "---\nname: Retired\n---\nold\n")
        self.write(".github/agents/README.md", "roster notes\n")
        self.write(".junie/agents/README.md", "roster notes\n")
        self.write(".junie/agents/notes.txt", "stray\n")
        result = self.run_render()
        self.assertIn("3 rendered, 0 already current, 3 pruned", result.stdout)
        for orphan in (
            ".junie/agents/retired.md",
            ".opencode/agents/retired.md",
            ".github/agents/retired.agent.md",
        ):
            self.assertFalse((self.layer / orphan).exists(), orphan)
        for kept in (
            ".github/agents/README.md",
            ".junie/agents/README.md",
            ".junie/agents/notes.txt",
        ):
            self.assertTrue((self.layer / kept).is_file(), kept)

    def test_prune_skipped_while_the_layer_fails(self):
        self.write(".junie/agents/orphan.md", "---\nname: orphan\n---\nold\n")
        (self.layer / ".junie/agents/sample.md").unlink()  # failure: missing mirror
        result = self.run_render()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(
            (self.layer / ".junie/agents/orphan.md").is_file(),
            "prune fired on a failing layer — authored frontmatter at risk",
        )
        # once the layer is clean again, the prune fires
        self.write(".junie/agents/sample.md", "---\nname: sample\n---\nx\n")
        self.run_render()
        self.assertFalse((self.layer / ".junie/agents/orphan.md").exists())

    def test_empty_roster_fails_and_prunes_nothing(self):
        empty = Path(self.td.name) / "empty-layer"
        for d in (
            ".claude/agents",
            ".junie/agents",
            ".opencode/agents",
            ".github/agents",
        ):
            (empty / d).mkdir(parents=True)
        (empty / ".claude/agents/README.md").write_text(
            "roster notes\n", encoding="utf-8"
        )
        keeper = empty / ".junie/agents/keeper.md"
        keeper.write_text("---\nname: keeper\n---\nk\n", encoding="utf-8")
        result = self.run_render(layer=empty)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("roster empty or path renamed", result.stderr)
        self.assertTrue(keeper.is_file(), "empty roster mass-deleted mirrors")

    def test_missing_agents_dir_fails(self):
        result = self.run_render(layer=Path(self.td.name) / "nowhere")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no .claude/agents under", result.stderr)

    def add_variant_with_mirrors(self):
        self.write(".claude/agents/sample-routine.md", VARIANT)
        self.write(".junie/agents/sample-routine.md", JUNIE)
        self.write(".opencode/agents/sample-routine.md", OPENCODE)
        self.write(".github/agents/sample-routine.agent.md", COPILOT)

    def test_variant_body_renders_from_base_frontmatter_kept(self):
        self.add_variant_with_mirrors()
        result = self.run_render()
        self.assertEqual(result.returncode, 0, result.stderr)
        variant = self.read(".claude/agents/sample-routine.md")
        self.assertTrue(variant.startswith(VARIANT.rstrip("\n") + "\n"))
        self.assertEqual(body_of(variant), body_of(BASE))
        # The variant's mirrors render from the variant's fresh body, links
        # rewritten to the mirror form, in the same run.
        mirror = self.read(".junie/agents/sample-routine.md")
        self.assertIn("../../.claude/skills/handoff-routing/SKILL.md", mirror)
        # Idempotent: a second run is a byte-stable noop.
        snapshot = self.read(".claude/agents/sample-routine.md")
        again = self.run_render()
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertIn("0 rendered", again.stdout)
        self.assertEqual(self.read(".claude/agents/sample-routine.md"), snapshot)

    def test_variant_missing_target_fails(self):
        self.add_variant_with_mirrors()
        self.write(
            ".claude/agents/sample-routine.md",
            VARIANT.replace("variant-of: sample", "variant-of: nowhere"),
        )
        result = self.run_render()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("has no base", result.stderr)

    def test_variant_wrong_name_fails(self):
        # variant-of on a base not named <target>-routine must refuse: one
        # frontmatter line must not silently replace another agent's body.
        self.add_variant_with_mirrors()
        self.write(
            ".claude/agents/sample-slow.md",
            "---\nname: sample-slow\nvariant-of: sample\n---\n",
        )
        self.write(".junie/agents/sample-slow.md", JUNIE)
        self.write(".opencode/agents/sample-slow.md", OPENCODE)
        self.write(".github/agents/sample-slow.agent.md", COPILOT)
        result = self.run_render()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("is not named sample-routine", result.stderr)
        # The mis-named base's body was not rewritten.
        self.assertNotIn("Sample Agent", self.read(".claude/agents/sample-slow.md"))

    def test_variant_chain_fails(self):
        self.add_variant_with_mirrors()
        self.write(
            ".claude/agents/sample-turbo.md",
            "---\nname: sample-turbo\nvariant-of: sample-routine\n---\n",
        )
        self.write(".junie/agents/sample-turbo.md", JUNIE)
        self.write(".opencode/agents/sample-turbo.md", OPENCODE)
        self.write(".github/agents/sample-turbo.agent.md", COPILOT)
        result = self.run_render()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("chains variant-of", result.stderr)


if __name__ == "__main__":
    unittest.main()
