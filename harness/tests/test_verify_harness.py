#!/usr/bin/env python3
"""Tests for the battery's pure helpers (stdlib only).

Run: python3 harness/tests/test_verify_harness.py

The battery's dynamic steps prove themselves against the live tree on every
run; what needs pinning are the parsing helpers whose subtle rules a refactor
could silently weaken: frontmatter stripping (a body's own "---" rules are
content), link normalization, section-scoped table rows, binary detection,
and the placeholder allowlist.

The helpers live in the verify_harness package (ADR 2026-07-18
check-sync-decomposition) and are imported by name: text (pure helpers),
battery (the aggregator), checks.lint / checks.sync / checks.suites (the
step functions). The confinement gate (checks.confinement) has its own
mirror suite, test_confinement.py. ROOT here is the harness/ toolbox root
(_loader), which is exactly verify_harness.text.HERE; the repo root is
verify_harness.text.ROOT.
"""

import sys
import tempfile
import unittest
from pathlib import Path

from _loader import ROOT

sys.path.insert(0, str(ROOT))

import registry  # noqa: E402
from verify_harness import battery, text  # noqa: E402
from verify_harness.checks import lint, suites, sync  # noqa: E402

STACKS = registry.STACKS


class StripFrontmatter(unittest.TestCase):
    def test_only_the_first_fence_pair_is_stripped(self):
        content = "---\nname: x\n---\nbody\n\n---\n\nrule stays\n"
        self.assertEqual(
            text.strip_frontmatter(content), ["body", "", "---", "", "rule stays"]
        )

    def test_no_fence_pair_yields_empty_body(self):
        self.assertEqual(text.strip_frontmatter("no fences here\n"), [])
        self.assertEqual(text.strip_frontmatter("---\nunclosed\n"), [])

    def test_fence_tolerates_trailing_whitespace_only(self):
        self.assertEqual(text.strip_frontmatter("--- \na\n---\t\nbody\n"), ["body"])
        self.assertEqual(text.strip_frontmatter("--- x\na\n"), [])


class NormLinks(unittest.TestCase):
    def test_sibling_form_normalizes_to_base_form(self):
        self.assertEqual(
            text.norm_links(["see [x](../../.claude/skills/foo/SKILL.md)"]),
            ["see [x](../skills/foo/SKILL.md)"],
        )

    def test_base_form_is_untouched(self):
        self.assertEqual(
            text.norm_links(["[x](../skills/foo/SKILL.md)"]),
            ["[x](../skills/foo/SKILL.md)"],
        )


class FrontmatterParsing(unittest.TestCase):
    FM = (
        "---\n"
        "description: >-\n"
        "  Reviews things\n"
        "  carefully.\n"
        "mode: subagent\n"
        "steps: 40\n"
        "permission:\n"
        "  read: allow\n"
        '  "mymcp_*": deny\n'
        "  edit: deny\n"
        "tools:\n"
        "  - Bash\n"
        "---\n"
        "body: a body line, not frontmatter\n"
    )

    def test_top_keys_skip_block_scalars_and_list_items(self):
        self.assertEqual(
            text.frontmatter_top_keys(self.FM),
            ["description", "mode", "steps", "permission", "tools"],
        )

    def test_unfenced_text_has_no_keys(self):
        self.assertEqual(text.frontmatter_top_keys("name: x\n"), [])

    def test_unclosed_fence_has_no_keys(self):
        self.assertEqual(text.frontmatter_top_keys("---\nname: x\n"), [])

    def test_block_returns_subkeys_of_named_key_only_unquoted(self):
        self.assertEqual(
            text.frontmatter_block(self.FM, "permission"),
            [("read", "allow"), ("mymcp_*", "deny"), ("edit", "deny")],
        )

    def test_block_absent_or_scalar_key_is_empty(self):
        self.assertEqual(text.frontmatter_block(self.FM, "hooks"), [])
        self.assertEqual(text.frontmatter_block(self.FM, "mode"), [])

    def test_block_values_lose_comments_and_quotes(self):
        fm = '---\npermission:\n  read: allow  # note\n  edit: "deny"\n---\n'
        self.assertEqual(
            text.frontmatter_block(fm, "permission"),
            [("read", "allow"), ("edit", "deny")],
        )

    def test_block_nested_map_lines_stay_out(self):
        fm = (
            "---\n"
            "permission:\n"
            "  bash:\n"
            '    "git push": ask\n'
            "    ify: deny\n"
            "  edit: deny\n"
            "---\n"
        )
        self.assertEqual(
            text.frontmatter_block(fm, "permission"),
            [("bash", ""), ("edit", "deny")],
        )

    def test_scalar_probe_sees_flow_style_and_ignores_block_form(self):
        flow = "---\npermission: {read: allow}\n---\n"
        self.assertEqual(text.frontmatter_scalar(flow, "permission"), "{read: allow}")
        self.assertEqual(text.frontmatter_scalar(self.FM, "permission"), "")
        self.assertEqual(text.frontmatter_scalar(self.FM, "absent"), "")


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
        rows = text.section_rows(self.TEXT, r"^## (Agent Usage|Stack-specific skills)")
        self.assertEqual(rows, ["handoff-routing", "goland"])

    def test_commit_type_rows_stay_out(self):
        self.assertNotIn(
            "feat",
            text.section_rows(self.TEXT, r"^## (Agent Usage|Stack-specific skills)"),
        )


class BinaryDetection(unittest.TestCase):
    def test_nul_byte_marks_binary(self):
        with tempfile.TemporaryDirectory() as td:
            binary = Path(td) / "img.png"
            binary.write_bytes(b"\x89PNG\0\0")
            doc = Path(td) / "doc.md"
            doc.write_text("plain text\n", encoding="utf-8")
            self.assertTrue(text.is_binary(binary))
            self.assertFalse(text.is_binary(doc))


class RegistryShRosterFree(unittest.TestCase):
    def test_registry_sh_carries_no_roster(self):
        # registry.py is the sole roster home; registry.sh holds only shell
        # helpers. The last bash consumer (materialize-samples.sh) now shells
        # out for STACKS, so a roster reappearing here would be a second
        # hand-synced copy — the drift channel this collapse retired by
        # construction.
        sh = (ROOT / "registry.sh").read_text(encoding="utf-8")
        for name in ("STACKS", "ALL_TOOLS", "PLUGIN_TOOLS"):
            self.assertNotIn(
                f"{name}=(", sh, f"{name} roster must live only in registry.py"
            )
            self.assertNotIn(f"{name}=", sh, f"{name} must live only in registry.py")


class StackParallelCompleteness(unittest.TestCase):
    def test_every_three_way_parallel_is_gated(self):
        # STACK_PARALLEL_FILES is hand-maintained; this pins it to the tree.
        # A markdown file present in every stack's .claude tree IS a three-way
        # parallel — a new one must join the roster gate, not drift silently.
        per_stack = [
            {
                p.relative_to(ROOT / "stacks" / s).as_posix()
                for p in (ROOT / "stacks" / s / ".claude").rglob("*.md")
            }
            for s in STACKS
        ]
        self.assertEqual(set.intersection(*per_stack), set(sync.STACK_PARALLEL_FILES))


class FrontmatterSkills(unittest.TestCase):
    def test_block_list_values_are_returned_in_order(self):
        fm = "---\nname: x\nskills:\n  - handoff-append\n  - security-checks\n---\nbody"
        self.assertEqual(
            sync._frontmatter_skills(fm), ["handoff-append", "security-checks"]
        )

    def test_absent_key_or_frontmatter_is_empty(self):
        self.assertEqual(sync._frontmatter_skills("no frontmatter"), [])
        self.assertEqual(sync._frontmatter_skills("---\nname: x\n---\n"), [])

    def test_list_ends_at_the_next_top_level_key(self):
        fm = "---\nskills:\n  - a\ntools:\n  - Bash\n---\n"
        self.assertEqual(sync._frontmatter_skills(fm), ["a"])


class BundledSkillDenylist(unittest.TestCase):
    def test_the_proven_collision_is_pinned(self):
        # security-review is the transcript-proven substitution (ADR
        # 2026-08-11); the denylist must never lose it.
        self.assertIn("security-review", sync.CLAUDE_CODE_BUNDLED_SKILLS)

    def test_no_shipped_preload_names_a_bundled_skill(self):
        # The live-tree half of check 2g, pinned as a unit test: every
        # skills-list entry on every agent surface stays off the roster.
        surfaces = ((".claude/agents", ".md"),) + tuple(registry.mirror_surfaces())
        layers = [ROOT / "core"] + [ROOT / "stacks" / s for s in STACKS]
        for layer in layers:
            for agents_dir, suffix in surfaces:
                base = layer / agents_dir
                if not base.is_dir():
                    continue
                for path in sorted(base.glob(f"*{suffix}")):
                    names = sync._frontmatter_skills(path.read_text(encoding="utf-8"))
                    with self.subTest(path=str(path.relative_to(ROOT))):
                        self.assertEqual(
                            set(names) & sync.CLAUDE_CODE_BUNDLED_SKILLS, set()
                        )


class StackSchemasDoNotShadowCore(unittest.TestCase):
    def test_no_stack_schema_shadows_a_core_schema(self):
        # materialize copies core then stack, stack winning on overlap: a
        # stack schema named like a core one would silently re-fork the
        # single-sourced copy (the prd-entry dedup) — gate the channel shut.
        core = {p.name for p in (ROOT / "core" / "schemas" / "scratch").glob("*.json")}
        for s in STACKS:
            names = {
                p.name
                for p in (ROOT / "stacks" / s / "schemas" / "scratch").glob("*.json")
            }
            self.assertEqual(
                names & core,
                set(),
                f"stacks/{s} shadows core schemas: {sorted(names & core)}",
            )


class PlaceholderAllowlist(unittest.TestCase):
    def test_documented_locations_are_allowed(self):
        for path in (
            "harness/init/stacks/go/CLAUDE.md",
            "harness/core/.claude/skills/doctor/templates/prd.md",
            "samples/go/CLAUDE.md",
            "samples/java-spring-boot/docs/prd.md",
            "plugins/agent-team-go/skills/doctor/templates/prd.md",
            ".claude/skills/init/SKILL.md",
            "samples/go/Makefile",
        ):
            with self.subTest(path=path):
                self.assertIsNotNone(sync.PH_ALLOW.match(path))

    def test_runtime_content_is_not_allowed(self):
        for path in (
            "harness/core/.claude/skills/tdd-workflow/SKILL.md",
            "docs/agentic-harness.md",
            "samples/go/docs/testing-principles.md",
            "README.md",
        ):
            with self.subTest(path=path):
                self.assertIsNone(sync.PH_ALLOW.match(path))

    def test_tokens_are_built_by_concatenation(self):
        # The battery source must never contain the literal token, or the
        # placeholder gate would flag its own scanner. The source is now the
        # launcher plus the verify_harness package.
        sources = [
            ROOT / "verify-harness.py",
            *sorted((ROOT / "verify_harness").rglob("*.py")),
        ]
        for token in sync.PH_TOKENS:
            for src in sources:
                self.assertNotIn(token, src.read_text(encoding="utf-8"), str(src))


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
        self.assertEqual(
            text.h2_headings(self.BODY), ["One", "Severity Classification", "After"]
        )

    def test_severity_headings_scoped_to_their_section(self):
        self.assertEqual(
            text.severity_headings(self.BODY), ["CRITICAL (BLOCKED)", "LOW"]
        )

    def test_tag_findings_passes_canonical_tags_and_skips_prose(self):
        sample = (
            "fix [AUTOFIX] then [CLARIFY:security-reviewer]; "
            "regex [A-Z], id [REQ-XX-NNN], and [BLOCKED]; "
            "a [link](somewhere) is text, not a tag; see [docs]"
        )
        self.assertEqual(text.tag_findings(sample, self.CANON), (3, []))

    def test_tag_findings_flags_unknown_uppercase_head(self):
        judged, problems = text.tag_findings("todo: [BOGUS]", self.CANON)
        self.assertEqual((judged, len(problems)), (1, 1))
        self.assertIn("not in review-workflow's canonical set", problems[0])

    def test_tag_findings_judges_variant_forms_not_skips(self):
        # A case-variant head, a spaced colon, and a link-styled tag reach
        # judgment; non-vocabulary links and prose brackets never do.
        for sample, fragment in (
            ("[Blocked]", "case-variant head"),
            ("[autofix]", "case-variant head"),
            ("[CLARIFY :security-reviewer]", "whitespace before the colon"),
            ("[AUTOFIX](note)", "styled as a markdown link"),
        ):
            judged, problems = text.tag_findings(sample, self.CANON)
            self.assertEqual((judged, len(problems)), (1, 1), sample)
            self.assertIn(fragment, problems[0])
        for benign in ("[README](x)", "see [docs] for more", "[A-Z]"):
            self.assertEqual(text.tag_findings(benign, self.CANON), (0, []), benign)

    def test_tag_findings_malformed_targets_reach_judgment(self):
        # A wrong-case, digits-first, empty, or whitespace-carrying target
        # must reach the judge, never silently fall out of the scan.
        for bad in (
            "[CLARIFY:Security-Reviewer]",
            "[CLARIFY:2fast]",
            "[CLARIFY:]",
            "[CLARIFY: security-reviewer]",
        ):
            judged, problems = text.tag_findings(bad, self.CANON)
            self.assertEqual((judged, len(problems)), (1, 1), bad)
            self.assertIn("malformed target", problems[0])
        self.assertIsNotNone(text.TAG_TARGET.match("security-reviewer"))

    def test_live_tree_carries_judged_tags(self):
        # The vocabulary gate's anti-vacuity floor rests on the stack skills
        # actually carrying tags; pin that premise so carrier drift surfaces
        # here before it silently empties the gate.
        canon = set(
            text.section_rows(
                (ROOT / "core/.claude/skills/review-workflow/SKILL.md").read_text(
                    encoding="utf-8"
                ),
                r"^## Feedback Tags",
            )
        )
        total = sum(
            text.tag_findings(f.read_text(encoding="utf-8"), canon)[0]
            for f in (ROOT / "stacks").glob("*/.claude/skills/**/*.md")
        )
        self.assertGreater(total, 0)

    def test_pinned_ide_delta_still_names_live_headings(self):
        # A stale pin would silently allow a divergence nobody decided; the
        # pin is scoped per pair and must name headings live in that pair.
        for skill_pair, pins in sync.IDE_HEADING_DELTA.items():
            rosters = [
                text.h2_headings(
                    text.strip_frontmatter(
                        (ROOT / rel_path).read_text(encoding="utf-8")
                    )
                )
                for rel_path in skill_pair
            ]
            for go_heading, java_heading in pins:
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
        for rel_path, pins in sync.STACK_PARALLEL_PINNED.items():
            self.assertIn(rel_path, sync.STACK_PARALLEL_FILES)
            live = {}
            for s in STACKS:
                content = (ROOT / "stacks" / s / rel_path).read_text(encoding="utf-8")
                # Mirror the gate's body(): frontmatter is stripped only when
                # the file opens with a fence — the agents README carries none.
                lines = content.splitlines()
                if lines and text.FENCE.match(lines[0]):
                    lines = text.strip_frontmatter(content)
                live[s] = text.h2_headings(lines)
            for heading, carriers in pins.items():
                self.assertTrue(
                    set(carriers) < set(STACKS),
                    f"pin '{heading}' must name a proper subset "
                    f"of STACKS, got {carriers!r}",
                )
                self.assertTrue(carriers, f"pin '{heading}' names no carrier")
                for s in STACKS:
                    self.assertEqual(
                        heading in live[s],
                        s in carriers,
                        f"pin '{heading}' ({rel_path}) disagrees with stacks/{s}",
                    )
                    # Pinned headings sit outside the ordered roster compare,
                    # so the gate (and this guard) must catch duplication.
                    self.assertLessEqual(
                        live[s].count(heading),
                        1,
                        f"pin '{heading}' ({rel_path}) duplicated in stacks/{s}",
                    )

    def test_stack_parallel_files_exist_in_every_stack(self):
        # The roster gate skips a file missing from two stacks (len < 2
        # guard); pin the premise that every listed parallel ships three copies.
        for rel_path in sync.STACK_PARALLEL_FILES:
            for s in STACKS:
                self.assertTrue(
                    (ROOT / "stacks" / s / rel_path).is_file(),
                    f"stacks/{s}/{rel_path} missing",
                )


class DetectStack(unittest.TestCase):
    # The marker-priority contract is load-bearing for materialize-samples.sh, /init,
    # and /materialize but was exercised only implicitly on the three
    # single-marker samples: go wins on multi-marker trees, any java marker
    # maps to java-spring-boot, and no marker falls back to generic.

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)

    def tearDown(self):
        self._td.cleanup()

    def _detect(self, *markers):
        for m in markers:
            (self.root / m).write_text("", encoding="utf-8")
        return registry.detect_stack(self.root)

    def test_single_markers(self):
        for marker, stack in (
            ("go.mod", "go"),
            ("build.gradle", "java-spring-boot"),
            ("build.gradle.kts", "java-spring-boot"),
            ("pom.xml", "java-spring-boot"),
        ):
            with self.subTest(marker=marker):
                d = self.root / marker
                d.write_text("", encoding="utf-8")
                self.assertEqual(registry.detect_stack(self.root), stack)
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
    def _load_handoff_pkg():
        # The public API surface is the handoff package (ROSTER_FLOOR, RETRY_CAP
        # re-exported), not the entry launcher (ADR 2026-07-17
        # runtime-package-layout).
        import importlib

        scripts = str(ROOT / "core/scripts")
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        return importlib.import_module("handoff")

    @staticmethod
    def _manifest():
        import tomllib

        return tomllib.loads(
            (ROOT / "core/scripts/doctor-expectations.toml").read_text(encoding="utf-8")
        )

    def test_reviewer_floor_agrees_across_router_grader_doctor(self):
        handoff = self._load_handoff_pkg()
        # The grader's floor lives in grading.config (ADR 2026-07-17
        # runtime-package-layout); the package resolves via the same
        # scripts-root sys.path entry _load_handoff_pkg installs.
        import importlib

        grading_config = importlib.import_module("grading.config")
        self.assertEqual(
            handoff.ROSTER_FLOOR,
            grading_config.REVIEWERS,
            "router and grader disagree on the reviewer floor",
        )
        self.assertEqual(
            list(handoff.ROSTER_FLOOR),
            self._manifest()["reviewers"]["floor"],
            "router and doctor manifest disagree on the floor",
        )

    def test_retry_cap_matches_the_core_schema(self):
        # One core build-failure schema since the enumFrom dedup (ADR
        # 2026-08-02 gate-facts): the retry pin is a two-site parity now.
        handoff = self._load_handoff_pkg()
        import json

        schema = json.loads(
            (ROOT / "core/schemas/scratch/build-failure.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            handoff.RETRY_CAP,
            schema["properties"]["retry"]["maximum"],
            "core build-failure retry.maximum drifted from RETRY_CAP",
        )

    def test_channel_enum_matches_doctor_manifest(self):
        self.assertEqual(
            list(registry.CHANNELS),
            self._manifest()["project_data"]["channel_values"],
            "registry.CHANNELS and the doctor manifest disagree",
        )


class QuickSuiteSkipProof(unittest.TestCase):
    """Steps 6b/6bc skip under --quick only on the joint clean-tree proof
    over tools/ and evals/ — a pending change in either tree runs both steps
    (the eval suites are the only executable coverage of
    tools/harness-stats/accounting.py). Gitignored dev-run artifacts are
    invisible to the proof, so 6bc still validates the derived views when any
    exists. These pins keep the skip from widening: no per-tree skip, no
    skip outside --quick, no silent skip past a dev artifact."""

    def _battery(self, quick):
        return battery.Battery(quick=quick, strict=False)

    def _quiet(self):
        import contextlib
        import io

        sink = io.StringIO()
        return contextlib.redirect_stdout(sink), sink

    def test_no_proof_outside_quick(self):
        import unittest.mock as mock

        with mock.patch.object(suites, "git_status", return_value=""):
            self.assertIsNone(suites._quick_skip_proof(self._battery(quick=False)))

    def test_pending_change_blocks_the_proof(self):
        import unittest.mock as mock

        with mock.patch.object(
            suites, "git_status", return_value="?? tools/x.py\n"
        ) as gs:
            self.assertIsNone(suites._quick_skip_proof(self._battery(quick=True)))
        gs.assert_called_once_with("tools/", "evals/")  # the probe stays joint

    def test_clean_trees_yield_the_proof_in_quick(self):
        import unittest.mock as mock

        with mock.patch.object(suites, "git_status", return_value=""):
            self.assertIsNotNone(suites._quick_skip_proof(self._battery(quick=True)))

    def test_tools_suites_skip_runs_nothing(self):
        import unittest.mock as mock

        b = self._battery(quick=True)
        redirect, _ = self._quiet()
        with (
            mock.patch.object(suites, "git_status", return_value=""),
            mock.patch.object(
                suites.subprocess, "run", side_effect=AssertionError("ran a suite")
            ),
            redirect,
        ):
            suites.check_tools_suites(b)
        self.assertFalse(b.failed)

    def test_eval_suites_skip_runs_nothing_without_dev_artifacts(self):
        import unittest.mock as mock

        b = self._battery(quick=True)
        redirect, _ = self._quiet()
        with (
            mock.patch.object(suites, "git_status", return_value=""),
            mock.patch.object(suites, "_dev_artifacts", return_value=[]),
            mock.patch.object(
                suites.subprocess, "run", side_effect=AssertionError("ran a suite")
            ),
            redirect,
        ):
            suites.check_eval_suites(b)
        self.assertFalse(b.failed)

    def test_eval_suites_validate_views_when_dev_artifacts_exist(self):
        import subprocess as sp
        import unittest.mock as mock

        b = self._battery(quick=True)
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return sp.CompletedProcess(cmd, 0, stdout="", stderr="")

        redirect, out = self._quiet()
        with (
            mock.patch.object(suites, "git_status", return_value=""),
            mock.patch.object(
                suites,
                "_dev_artifacts",
                return_value=["evals/results/TREND-dev.md"],
            ),
            mock.patch.object(suites.subprocess, "run", side_effect=fake_run),
            redirect,
        ):
            suites.check_eval_suites(b)
        self.assertFalse(b.failed)
        self.assertEqual(len(calls), 1)  # the derived-view gate, nothing else
        self.assertIn("--check", calls[0])
        self.assertIn("git-invisible", out.getvalue())

    def test_eval_suites_fail_on_drifted_dev_views(self):
        import subprocess as sp
        import unittest.mock as mock

        b = self._battery(quick=True)
        import contextlib
        import io

        sink = io.StringIO()
        with (
            mock.patch.object(suites, "git_status", return_value=""),
            mock.patch.object(
                suites,
                "_dev_artifacts",
                return_value=["evals/results/runs/dev-x"],
            ),
            mock.patch.object(
                suites.subprocess,
                "run",
                return_value=sp.CompletedProcess([], 1, stdout="", stderr="drift"),
            ),
            contextlib.redirect_stdout(sink),
            contextlib.redirect_stderr(sink),
        ):
            suites.check_eval_suites(b)
        self.assertTrue(b.failed)


class RetiredPathsCheck(unittest.TestCase):
    """Step 3k's failure branches, pinned: a manifest entry the source
    produces again must FAIL (setup.sh prunes listed paths), a runtime path
    the last tag produced that is gone without a manifest entry must FAIL
    with the mechanical fix named, and a tagless checkout must FAIL under
    --strict (the push-time gates) instead of silently disarming."""

    def _run(self, strict, produced_now, retired, describe_rc=0):
        import contextlib
        import io
        import subprocess as sp
        import unittest.mock as mock

        import retired_paths

        b = battery.Battery(quick=False, strict=strict)
        describe = sp.CompletedProcess([], describe_rc, stdout="v9.9.9\n", stderr="")
        sink = io.StringIO()
        with (
            mock.patch.object(
                retired_paths, "produced_paths", return_value=produced_now
            ),
            mock.patch.object(retired_paths, "retired_since", return_value=retired),
            mock.patch.object(sync.subprocess, "run", return_value=describe),
            contextlib.redirect_stdout(sink),
            contextlib.redirect_stderr(sink),
        ):
            sync.check_retired_paths(b)
        return b.failed, sink.getvalue()

    def test_live_manifest_entry_fails(self):
        # scripts/score-change.py is a seed entry; producing it again must FAIL.
        failed, out = self._run(
            strict=False,
            produced_now={"scripts/score-change.py"},
            retired=set(),
        )
        self.assertTrue(failed)
        self.assertIn("reintroduced", out)

    def test_uncovered_deletion_fails_and_names_the_fix(self):
        failed, out = self._run(
            strict=False,
            produced_now=set(),
            retired={"scripts/brand-new-retirement.py"},
        )
        self.assertTrue(failed)
        self.assertIn("retired_paths.py update", out)

    def test_covered_state_passes(self):
        failed, _ = self._run(strict=False, produced_now=set(), retired=set())
        self.assertFalse(failed)

    def test_tagless_checkout_fails_only_under_strict(self):
        failed, out = self._run(
            strict=True, produced_now=set(), retired=set(), describe_rc=128
        )
        self.assertTrue(failed)
        self.assertIn("fetch-depth", out)
        failed, out = self._run(
            strict=False, produced_now=set(), retired=set(), describe_rc=128
        )
        self.assertFalse(failed)
        self.assertIn("not checked", out)


class StrictToolPresence(unittest.TestCase):
    """--strict turns a missing SAST tool into a FAIL, not a SKIP — the
    property the two push-time gates rest on. Without it, an absent linter
    skips with a note (the dev-machine default)."""

    def _failed_when_absent(self, check, strict):
        import contextlib
        import io
        import unittest.mock as mock

        b = battery.Battery(quick=False, strict=strict)
        sink = io.StringIO()
        with (
            mock.patch.object(lint.shutil, "which", return_value=None),
            contextlib.redirect_stdout(sink),
            contextlib.redirect_stderr(sink),
        ):
            check(b)
        return b.failed

    # The ruff and mypy steps (ADR 2026-07-17) join the same contract: a
    # missing tool is a SKIP on a dev machine, a FAIL under the push-time
    # --strict gate.
    _GATED = (
        lint.check_bandit,
        lint.check_shellcheck,
        lint.check_ruff_format,
        lint.check_ruff_lint,
        lint.check_mypy,
    )

    def test_missing_tool_fails_under_strict(self):
        for check in self._GATED:
            with self.subTest(check=check.__name__):
                self.assertTrue(self._failed_when_absent(check, strict=True))

    def test_missing_tool_only_skips_without_strict(self):
        for check in self._GATED:
            with self.subTest(check=check.__name__):
                self.assertFalse(self._failed_when_absent(check, strict=False))


class MypyScope(unittest.TestCase):
    """The mypy step reads its scope from the root pyproject [tool.mypy].files
    (ADR 2026-07-17). Slice 2 ships an empty scope that passes trivially;
    slice 3 grows it module by module."""

    def test_scope_is_a_list_from_pyproject(self):
        self.assertIsInstance(lint._mypy_scope(), list)

    def test_empty_scope_still_checks_the_entry(self):
        # mypy installed but the pyproject scope cleared: the scope run is a
        # trivial pass, but the entry solo run still executes — clearing the
        # files list must never silently disarm the launcher's strict check.
        import contextlib
        import io
        import types
        import unittest.mock as mock

        b = battery.Battery(quick=False, strict=True)
        sink = io.StringIO()
        clean = types.SimpleNamespace(returncode=0, stdout="", stderr="")
        with (
            mock.patch.object(lint.shutil, "which", return_value="/usr/bin/mypy"),
            mock.patch.object(lint, "_mypy_scope", return_value=[]),
            mock.patch.object(lint.subprocess, "run", return_value=clean) as run,
            contextlib.redirect_stdout(sink),
            contextlib.redirect_stderr(sink),
        ):
            lint.check_mypy(b)
        self.assertFalse(b.failed)
        self.assertEqual(run.call_count, len(lint.ENTRY_MODULES))
        self.assertEqual(
            [c.args[0] for c in run.call_args_list],
            [["mypy", entry] for entry in lint.ENTRY_MODULES],
        )


class TestAnchorHelpers(unittest.TestCase):
    """github_slug + heading_anchors feed the link-integrity anchor check."""

    def test_slug_strips_markdown_and_punctuation(self):
        self.assertEqual(
            text.github_slug("Risk-Proportional Roster (the review-plan)"),
            "risk-proportional-roster-the-review-plan",
        )
        self.assertEqual(text.github_slug("`code` in a Heading!"), "code-in-a-heading")
        self.assertEqual(text.github_slug("[Linked](x.md) Title"), "linked-title")

    def test_duplicate_headings_get_github_suffixes(self):
        sample = "## Setup\n\ntext\n\n## Setup\n"
        self.assertEqual(text.heading_anchors(sample), {"setup", "setup-1"})

    def test_fenced_headings_and_a_ids_handled(self):
        sample = '# Real\n\n```\n# commented heading\n```\n\n<a id="pinned"></a>\n'
        self.assertEqual(text.heading_anchors(sample), {"real", "pinned"})


class PodToolchainPins(unittest.TestCase):
    """The pod Dockerfile's python toolchain pins stay parity-gated against
    pyproject's ruff required-version (ADR 2026-07-12: a hand-owned parallel
    gets a gate); mypy and bandit must be ==-pinned at all."""

    def _run(self, root):
        import contextlib
        import io
        import unittest.mock as mock

        b = battery.Battery(quick=False, strict=True)
        err = io.StringIO()
        with (
            mock.patch.object(suites, "ROOT", Path(root)),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(err),
        ):
            suites.check_pod_toolchain_pins(b)
        return b.failed, err.getvalue()

    def _write(self, root, ruff_pin):
        pod = Path(root) / "tools/claude-dev"
        pod.mkdir(parents=True)
        (pod / "Dockerfile").write_text(
            f"RUN pip install 'ruff=={ruff_pin}' 'mypy==2.3.0' 'bandit==1.9.4'\n"
            "RUN apt-get install -y squid socat\n",
            encoding="utf-8",
        )
        (pod / "claude-dev").write_text(
            "CMD+=(--settings"
            ' \'{"sandbox":{"enabled":false,"failIfUnavailable":false}}\')\n',
            encoding="utf-8",
        )
        (Path(root) / "pyproject.toml").write_text(
            '[tool.ruff]\nrequired-version = "0.15.22"\n', encoding="utf-8"
        )

    def test_real_repo_pins_agree(self):
        self.assertEqual(suites.check_pod_toolchain_pins.__doc__[:4], "6bb.")
        failed, err = self._run(text.ROOT)
        self.assertFalse(failed, err)

    def test_matching_synthetic_pins_pass(self):
        with tempfile.TemporaryDirectory() as root:
            self._write(root, "0.15.22")
            failed, err = self._run(root)
            self.assertFalse(failed, err)

    def test_ruff_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as root:
            self._write(root, "9.9.9")
            failed, err = self._run(root)
            self.assertTrue(failed)
            self.assertIn("required-version", err)

    def test_unpinned_mypy_fails(self):
        with tempfile.TemporaryDirectory() as root:
            self._write(root, "0.15.22")
            df = Path(root) / "tools/claude-dev/Dockerfile"
            df.write_text(
                "RUN pip install 'ruff==0.15.22' mypy 'bandit==1.9.4'\n"
                "RUN apt-get install -y squid socat\n",
                encoding="utf-8",
            )
            failed, err = self._run(root)
            self.assertTrue(failed)
            self.assertIn("==-pin mypy", err)

    def test_dropped_sandbox_override_fails(self):
        # bubblewrap cannot create a user namespace under the default seccomp
        # profile, so dropping the override would revive a startup refusal.
        with tempfile.TemporaryDirectory() as root:
            self._write(root, "0.15.22")
            launcher = Path(root) / "tools/claude-dev/claude-dev"
            launcher.write_text("CMD=(claude)\n", encoding="utf-8")
            failed, err = self._run(root)
            self.assertTrue(failed)
            self.assertIn("sandbox-off --settings injection", err)

    def test_dropped_confinement_binary_fails(self):
        for binary in ("squid", "socat"):
            with self.subTest(binary=binary), tempfile.TemporaryDirectory() as root:
                self._write(root, "0.15.22")
                df = Path(root) / "tools/claude-dev/Dockerfile"
                kept = [b for b in ("squid", "socat") if b != binary]
                df.write_text(
                    "RUN pip install 'ruff==0.15.22' 'mypy==2.3.0' 'bandit==1.9.4'\n"
                    f"RUN apt-get install -y {' '.join(kept)}\n",
                    encoding="utf-8",
                )
                failed, err = self._run(root)
                self.assertTrue(failed, binary)
                self.assertIn(binary, err)

    def test_pipe_to_shell_install_fails(self):
        for tail in ("| bash", "| sudo bash", "|/bin/sh", "| env zsh", "| dash"):
            with self.subTest(tail=tail), tempfile.TemporaryDirectory() as root:
                self._write(root, "0.15.22")
                df = Path(root) / "tools/claude-dev/Dockerfile"
                df.write_text(
                    "RUN pip install 'ruff==0.15.22' 'mypy==2.3.0' 'bandit==1.9.4'\n"
                    "RUN apt-get install -y squid socat\n"
                    f"RUN curl -fsSL https://example.com/install.sh {tail}\n",
                    encoding="utf-8",
                )
                failed, err = self._run(root)
                self.assertTrue(failed, tail)
                self.assertIn("pipes into a shell", err)


class ImportBoundaries(unittest.TestCase):
    """1g gates the scripts composition root's one-way import graph (ADR
    2026-07-17 runtime-package-layout) and the battery's own verify_harness
    package (ADR 2026-07-18 check-sync-decomposition). It passes on the real
    tree and bites a forbidden edge with a file:line message."""

    def _run(self, here):
        import contextlib
        import io
        import unittest.mock as mock

        # Resolve the synthetic root: rel() resolves each file before
        # relative_to(ROOT), so an unresolved macOS tempdir (/var/folders is a
        # symlink to /private/var/folders) would fall outside the patched ROOT.
        here = Path(here).resolve()
        b = battery.Battery(quick=False, strict=True)
        err = io.StringIO()
        with (
            mock.patch.object(lint, "HERE", here),
            mock.patch.object(text, "ROOT", here),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(err),
        ):
            lint.check_import_boundaries(b)
        return b.failed, err.getvalue()

    def _copy_trees(self, root):
        # Both gated trees: the scripts composition root and the verify_harness
        # package (the gate fails loudly on a table entry with no file, so a
        # synthetic HERE must carry both).
        import shutil

        ignore = shutil.ignore_patterns("__pycache__")
        scripts = Path(root) / "core/scripts"
        shutil.copytree(lint.HERE / "core/scripts", scripts, ignore=ignore)
        shutil.copytree(
            lint.HERE / "verify_harness", Path(root) / "verify_harness", ignore=ignore
        )
        return scripts

    def test_real_repo_graph_is_intact(self):
        self.assertEqual(lint.check_import_boundaries.__doc__[:3], "1g.")
        failed, err = self._run(lint.HERE)
        self.assertFalse(failed, err)

    def test_forbidden_edge_bites_with_file_line(self):
        with tempfile.TemporaryDirectory() as td:
            scripts = self._copy_trees(td)
            routing = scripts / "handoff/routing.py"
            routing.write_text(
                "from .view import render_view\n" + routing.read_text(),
                encoding="utf-8",
            )
            failed, err = self._run(td)
            self.assertTrue(failed)
            self.assertIn("handoff/routing.py:1", err)
            self.assertIn("handoff.view", err)

    def test_bare_import_in_entry_is_named(self):
        with tempfile.TemporaryDirectory() as td:
            scripts = self._copy_trees(td)
            entry = scripts / "handoff.py"
            entry.write_text("import handoff\n" + entry.read_text(), encoding="utf-8")
            failed, err = self._run(td)
            self.assertTrue(failed)
            self.assertIn("submodule-form", err)
            self.assertIn("runtime-package-layout", err)

    def test_new_untabled_module_fails_loudly(self):
        with tempfile.TemporaryDirectory() as td:
            self._copy_trees(td)
            scripts = Path(td) / "core/scripts"
            (scripts / "newthing.py").write_text("x = 1\n", encoding="utf-8")
            failed, err = self._run(td)
            self.assertTrue(failed)
            self.assertIn("newthing.py", err)

    def test_verify_harness_leaf_importing_upward_bites(self):
        # text is the leaf: an edge back into the aggregator inverts the
        # one-way graph and must fail with the file:line message.
        with tempfile.TemporaryDirectory() as td:
            self._copy_trees(td)
            leaf = Path(td) / "verify_harness/text.py"
            leaf.write_text(
                "from verify_harness.battery import Battery\n" + leaf.read_text(),
                encoding="utf-8",
            )
            failed, err = self._run(td)
            self.assertTrue(failed)
            self.assertIn("verify_harness/text.py:1", err)
            self.assertIn("verify_harness.battery", err)


if __name__ == "__main__":
    unittest.main()
