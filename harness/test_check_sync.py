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


class ParityGateHelpers(unittest.TestCase):
    BODY = [
        "## One",
        "```",
        "## fenced heading stays out",
        "### CRITICAL (fenced)",
        "```",
        "  ```json",
        "## indented-fence heading stays out",
        "  ```",
        "~~~",
        "## tilde-fenced heading stays out",
        "```",
        "~~~",
        "## Severity Classification",
        "### CRITICAL (BLOCKED)",
        "  ```",
        "### indented-fenced severity stays out",
        "  ```",
        "### LOW",
        "## After",
        "### stray outside the section",
    ]
    CANON = {"autofix", "blocked", "clarify", "escalate", "truncation"}

    def test_h2_headings_skip_fenced_blocks(self):
        # Indented and ~~~ fences hide headings too; a ``` inside a ~~~
        # block is literal content, not a closing fence.
        self.assertEqual(cs.h2_headings(self.BODY),
                         ["One", "Severity Classification", "After"])

    def test_severity_headings_scoped_to_their_section(self):
        self.assertEqual(cs.severity_headings(self.BODY),
                         ["CRITICAL (BLOCKED)", "LOW"])

    def test_tag_findings_passes_canonical_tags_and_skips_prose(self):
        text = ("fix [AUTOFIX] then [CLARIFY:security-reviewer]; "
                "regex [A-Z], id [REQ-XX-NNN], and [BLOCKED]; "
                "a [link](somewhere) is text, not a tag; see [docs]")
        self.assertEqual(cs.tag_findings(text, self.CANON), (3, []))

    def test_tag_findings_flags_unknown_uppercase_head(self):
        judged, problems = cs.tag_findings("todo: [BOGUS]", self.CANON)
        self.assertEqual((judged, len(problems)), (1, 1))
        self.assertIn("not in review-workflow's canonical set", problems[0])

    def test_tag_findings_judges_variant_forms_not_skips(self):
        # A case-variant head, a spaced colon, and a link-styled tag reach
        # judgment; non-vocabulary links and prose brackets never do.
        for text, fragment in (
            ("[Blocked]", "case-variant head"),
            ("[autofix]", "case-variant head"),
            ("[CLARIFY :security-reviewer]", "whitespace before the colon"),
            ("[AUTOFIX](note)", "styled as a markdown link"),
        ):
            judged, problems = cs.tag_findings(text, self.CANON)
            self.assertEqual((judged, len(problems)), (1, 1), text)
            self.assertIn(fragment, problems[0])
        for benign in ("[README](x)", "see [docs] for more", "[A-Z]"):
            self.assertEqual(cs.tag_findings(benign, self.CANON), (0, []),
                             benign)

    def test_tag_findings_malformed_targets_reach_judgment(self):
        # A wrong-case, digits-first, empty, or whitespace-carrying target
        # must reach the judge, never silently fall out of the scan.
        for bad in ("[CLARIFY:Security-Reviewer]", "[CLARIFY:2fast]",
                    "[CLARIFY:]", "[CLARIFY: security-reviewer]"):
            judged, problems = cs.tag_findings(bad, self.CANON)
            self.assertEqual((judged, len(problems)), (1, 1), bad)
            self.assertIn("malformed target", problems[0])
        self.assertIsNotNone(cs.TAG_TARGET.match("security-reviewer"))

    def test_live_tree_carries_judged_tags(self):
        # The vocabulary gate's anti-vacuity floor rests on the stack skills
        # actually carrying tags; pin that premise so carrier drift surfaces
        # here before it silently empties the gate.
        canon = set(cs.section_rows(
            (_HERE / "core/.claude/skills/review-workflow/SKILL.md")
            .read_text(encoding="utf-8"), r"^## Feedback Tags"))
        total = sum(
            cs.tag_findings(f.read_text(encoding="utf-8"), canon)[0]
            for f in (_HERE / "stacks").glob("*/.claude/skills/**/*.md"))
        self.assertGreater(total, 0)

    def test_pinned_ide_delta_still_names_live_headings(self):
        # A stale pin would silently allow a divergence nobody decided; the
        # pin is scoped per pair and must name headings live in that pair.
        for skill_pair, pins in cs.IDE_HEADING_DELTA.items():
            rosters = [
                cs.h2_headings(cs.strip_frontmatter(
                    (_HERE / rel_path).read_text(encoding="utf-8")))
                for rel_path in skill_pair
            ]
            for (go_heading, java_heading) in pins:
                self.assertIn(go_heading, rosters[0])
                self.assertIn(java_heading, rosters[1])

    def test_stack_parallel_pins_are_exact_and_live(self):
        # Pin-hygiene guard for the stack-parallel roster gate: every pinned
        # file is on the gated roster; every pin names a non-empty PROPER
        # subset of the stacks (all three would be the ordinary roster
        # compare, none would pin a dead heading) with valid slugs; and each
        # stack's copy matches the pin exactly — the presence check the gate
        # runs, pinned here so a stale pin fails this suite, not only the
        # battery.
        for rel_path, pins in cs.STACK_PARALLEL_PINNED.items():
            self.assertIn(rel_path, cs.STACK_PARALLEL_FILES)
            live = {}
            for s in cs.STACKS:
                text = (_HERE / "stacks" / s / rel_path).read_text(
                    encoding="utf-8")
                live[s] = set(cs.h2_headings(cs.strip_frontmatter(text)))
            for heading, carriers in pins.items():
                self.assertTrue(set(carriers) < set(cs.STACKS),
                                f"pin '{heading}' must name a proper subset "
                                f"of STACKS, got {carriers!r}")
                self.assertTrue(carriers, f"pin '{heading}' names no carrier")
                for s in cs.STACKS:
                    self.assertEqual(
                        heading in live[s], s in carriers,
                        f"pin '{heading}' ({rel_path}) disagrees with "
                        f"stacks/{s}")

    def test_stack_parallel_files_exist_in_every_stack(self):
        # The roster gate skips a file missing from two stacks (len < 2
        # guard); pin the premise that all nine parallels ship three copies.
        for rel_path in cs.STACK_PARALLEL_FILES:
            for s in cs.STACKS:
                self.assertTrue(
                    (_HERE / "stacks" / s / rel_path).is_file(),
                    f"stacks/{s}/{rel_path} missing")


class DetectStack(unittest.TestCase):
    # The marker-priority contract is load-bearing for bootstrap.sh, /init,
    # and /materialize but was exercised only implicitly on the three
    # single-marker samples: go wins on multi-marker trees, any java marker
    # maps to java-spring-boot, and no marker falls back to generic.

    def setUp(self):
        import sys
        import tempfile
        sys.path.insert(0, str(_HERE))
        import helpers
        self.helpers = helpers
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _detect(self, *markers):
        for m in markers:
            (self.root / m).write_text("", encoding="utf-8")
        return self.helpers.detect_stack(self.root)

    def test_single_markers(self):
        for marker, stack in (("go.mod", "go"),
                              ("build.gradle", "java-spring-boot"),
                              ("build.gradle.kts", "java-spring-boot"),
                              ("pom.xml", "java-spring-boot")):
            with self.subTest(marker=marker):
                d = self.root / marker
                d.write_text("", encoding="utf-8")
                self.assertEqual(self.helpers.detect_stack(self.root), stack)
                d.unlink()

    def test_multi_marker_prefers_go(self):
        self.assertEqual(self._detect("go.mod", "pom.xml"), "go")

    def test_no_marker_falls_back_to_generic(self):
        self.assertEqual(self._detect(), "generic")


class HandSyncedConstantParity(unittest.TestCase):
    # Constants the shipped engines and the doctor manifest carry as
    # hand-owned copies (the ADR 2026-07-12 class). The router routes on
    # them, the grader keys its reviewers row on them, and the doctor
    # validates against them — a change landing in one copy desynchronizes
    # the three silently. These asserts are the gate. They live maintainer-
    # side on purpose: a consumer tree carries one stack and must never
    # depend on harness/stacks/*.

    @staticmethod
    def _load(path, name):
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @staticmethod
    def _manifest():
        import tomllib
        return tomllib.loads(
            (_HERE / "core/scripts/brief-expectations.toml")
            .read_text(encoding="utf-8"))

    def test_reviewer_floor_agrees_across_router_grader_doctor(self):
        handoff = self._load(_HERE / "core/scripts/handoff.py", "_parity_handoff")
        score = self._load(_HERE / "core/scripts/score-change.py", "_parity_score")
        self.assertEqual(handoff.ROSTER_FLOOR, score._REVIEWERS,
                         "router and grader disagree on the reviewer floor")
        self.assertEqual(list(handoff.ROSTER_FLOOR),
                         self._manifest()["reviewers"]["floor"],
                         "router and doctor manifest disagree on the floor")

    def test_retry_cap_matches_every_stack_schema(self):
        handoff = self._load(_HERE / "core/scripts/handoff.py", "_parity_handoff2")
        import json
        for s in cs.STACKS:
            schema = json.loads(
                (_HERE / "stacks" / s / "schemas/scratch/build-failure.schema.json")
                .read_text(encoding="utf-8"))
            self.assertEqual(
                handoff.RETRY_CAP,
                schema["properties"]["retry"]["maximum"],
                f"stacks/{s} build-failure retry.maximum drifted from RETRY_CAP")

    def test_channel_enum_matches_doctor_manifest(self):
        import sys
        sys.path.insert(0, str(_HERE))
        import helpers
        self.assertEqual(list(helpers.CHANNELS),
                         self._manifest()["project_data"]["channel_values"],
                         "helpers.CHANNELS and the doctor manifest disagree")


class StrictToolPresence(unittest.TestCase):
    """--strict turns a missing SAST tool into a FAIL, not a SKIP — the
    property the two push-time gates rest on. Without it, an absent linter
    skips with a note (the dev-machine default)."""

    def _failed_when_absent(self, check, strict):
        import contextlib
        import io
        import unittest.mock as mock
        b = cs.Battery(quick=False, strict=strict)
        sink = io.StringIO()
        with mock.patch.object(cs.shutil, "which", return_value=None), \
                contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            check(b)
        return b.failed

    def test_missing_tool_fails_under_strict(self):
        self.assertTrue(self._failed_when_absent(cs.check_bandit, strict=True))
        self.assertTrue(self._failed_when_absent(cs.check_shellcheck, strict=True))

    def test_missing_tool_only_skips_without_strict(self):
        self.assertFalse(self._failed_when_absent(cs.check_bandit, strict=False))
        self.assertFalse(self._failed_when_absent(cs.check_shellcheck, strict=False))


class TestAnchorHelpers(unittest.TestCase):
    """github_slug + heading_anchors feed the link-integrity anchor check."""

    def test_slug_strips_markdown_and_punctuation(self):
        self.assertEqual(cs.github_slug("Risk-Proportional Roster (the review-plan)"),
                         "risk-proportional-roster-the-review-plan")
        self.assertEqual(cs.github_slug("`code` in a Heading!"), "code-in-a-heading")
        self.assertEqual(cs.github_slug("[Linked](x.md) Title"), "linked-title")

    def test_duplicate_headings_get_github_suffixes(self):
        text = "## Setup\n\ntext\n\n## Setup\n"
        self.assertEqual(cs.heading_anchors(text), {"setup", "setup-1"})

    def test_fenced_headings_and_a_ids_handled(self):
        text = '# Real\n\n```\n# commented heading\n```\n\n<a id="pinned"></a>\n'
        self.assertEqual(cs.heading_anchors(text), {"real", "pinned"})


if __name__ == "__main__":
    unittest.main()
