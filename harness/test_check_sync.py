#!/usr/bin/env python3
"""Tests for check-sync.py's pure helpers (stdlib only).

Run: python3 harness/test_check_sync.py

The battery's dynamic steps prove themselves against the live tree on every
run; what needs pinning are the parsing helpers whose subtle rules a refactor
could silently weaken: frontmatter stripping (a body's own "---" rules are
content), link normalization, section-scoped table rows, binary detection,
and the placeholder allowlist.
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load():
    spec = importlib.util.spec_from_file_location("check_sync", _HERE / "check-sync.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cs = _load()


class StripFrontmatter(unittest.TestCase):
    def test_only_the_first_fence_pair_is_stripped(self):
        text = "---\nname: x\n---\nbody\n\n---\n\nrule stays\n"
        self.assertEqual(cs.strip_frontmatter(text),
                         ["body", "", "---", "", "rule stays"])

    def test_no_fence_pair_yields_empty_body(self):
        self.assertEqual(cs.strip_frontmatter("no fences here\n"), [])
        self.assertEqual(cs.strip_frontmatter("---\nunclosed\n"), [])

    def test_fence_tolerates_trailing_whitespace_only(self):
        self.assertEqual(cs.strip_frontmatter("--- \na\n---\t\nbody\n"), ["body"])
        self.assertEqual(cs.strip_frontmatter("--- x\na\n"), [])


class NormLinks(unittest.TestCase):
    def test_sibling_form_normalizes_to_base_form(self):
        self.assertEqual(
            cs.norm_links(["see [x](../../.claude/skills/foo/SKILL.md)"]),
            ["see [x](../skills/foo/SKILL.md)"],
        )

    def test_base_form_is_untouched(self):
        self.assertEqual(cs.norm_links(["[x](../skills/foo/SKILL.md)"]),
                         ["[x](../skills/foo/SKILL.md)"])


class SectionRows(unittest.TestCase):
    TEXT = (
        "## Agent Usage (Mandatory)\n"
        "| `handoff-routing` | routing |\n"
        "## Commit Convention\n"
        "| `feat` | new content |\n"
        "## Stack-specific skills\n"
        "| `goland` | oracle |\n"
    )

    def test_rows_scoped_to_matching_sections_only(self):
        rows = cs.section_rows(self.TEXT, r"^## (Agent Usage|Stack-specific skills)")
        self.assertEqual(rows, ["handoff-routing", "goland"])

    def test_commit_type_rows_stay_out(self):
        self.assertNotIn("feat", cs.section_rows(
            self.TEXT, r"^## (Agent Usage|Stack-specific skills)"))


class BinaryDetection(unittest.TestCase):
    def test_nul_byte_marks_binary(self):
        with tempfile.TemporaryDirectory() as td:
            binary = Path(td) / "img.png"
            binary.write_bytes(b"\x89PNG\0\0")
            text = Path(td) / "doc.md"
            text.write_text("plain text\n", encoding="utf-8")
            self.assertTrue(cs.is_binary(binary))
            self.assertFalse(cs.is_binary(text))


class HelperRosterParity(unittest.TestCase):
    def test_helpers_sh_rosters_match_helpers_py(self):
        # helpers.py is the source; helpers.sh mirrors only STACKS — the one
        # roster a bash orchestrator still consumes (bootstrap.sh). The tool
        # rosters live in helpers.py alone. Two hand-maintained copies need a
        # gate — this is it.
        sh = (_HERE / "helpers.sh").read_text(encoding="utf-8")
        import re
        import sys
        sys.path.insert(0, str(_HERE))
        import helpers
        for name in ("STACKS",):
            m = re.search(rf"^{name}=\(([^)]*)\)", sh, re.M)
            self.assertIsNotNone(m, f"{name} roster missing from helpers.sh")
            self.assertEqual(tuple(m.group(1).split()), getattr(helpers, name),
                             f"{name} drifted between helpers.sh and helpers.py")
        self.assertNotIn("ALL_TOOLS", sh, "tool rosters must live only in helpers.py")
        self.assertNotIn("PLUGIN_TOOLS", sh, "tool rosters must live only in helpers.py")


class PlaceholderAllowlist(unittest.TestCase):
    def test_documented_locations_are_allowed(self):
        for path in (
            "harness/init/stacks/go/CLAUDE.md",
            "harness/core/.claude/skills/doctor/templates/prd.md",
            "samples/go/CLAUDE.md",
            "samples/java-spring-boot/docs/prd.md",
            "plugins/go-claude/skills/doctor/templates/prd.md",
            ".claude/skills/init/SKILL.md",
            "samples/go/Makefile",
        ):
            with self.subTest(path=path):
                self.assertIsNotNone(cs.PH_ALLOW.match(path))

    def test_runtime_content_is_not_allowed(self):
        for path in (
            "harness/core/.claude/skills/tdd-workflow/SKILL.md",
            "docs/agentic-harness.md",
            "samples/go/docs/testing-principles.md",
            "README.md",
        ):
            with self.subTest(path=path):
                self.assertIsNone(cs.PH_ALLOW.match(path))

    def test_tokens_are_built_by_concatenation(self):
        # The battery source must never contain the literal token, or the
        # placeholder gate would flag its own scanner.
        source = (_HERE / "check-sync.py").read_text(encoding="utf-8")
        for token in cs.PH_TOKENS:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
