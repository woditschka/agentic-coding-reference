#!/usr/bin/env python3
"""Pin the battery's parsing helpers and the failure branches of its checks."""

import ast
import contextlib
import importlib.util
import io
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import ROOT, load

sys.path.insert(0, str(ROOT))

import registry
from verify_harness import battery, text
from verify_harness.checks import lint, suites, sync

STACKS = registry.STACKS
SOME_TAG = "v9.9.9\n"
GIT_DESCRIBE_NO_TAG = 128
PENDING_TOOLS_CHANGE = "?? tools/x.py\n"
CLEAN_TREE = ""
SOME_MYPY_PATH = "/usr/bin/mypy"
SOME_DEV_VIEW = "evals/results/TREND-dev.md"
SOME_DEV_RUN = "evals/results/runs/dev-x"
SEED_RETIRED_PATH = "scripts/score-change.py"
PYPROJECT_RUFF_PIN = "0.15.22"
MISMATCHED_RUFF_PIN = "9.9.9"
CONFINEMENT_BINARIES = ("squid", "socat")


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
        sh = (ROOT / "registry.sh").read_text(encoding="utf-8")
        for name in ("STACKS", "ALL_TOOLS", "PLUGIN_TOOLS"):
            self.assertNotIn(f"{name}=(", sh)
            self.assertNotIn(f"{name}=", sh)


class StackParallelCompleteness(unittest.TestCase):
    def test_every_three_way_parallel_is_gated(self):
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
        self.assertIn("security-review", sync.CLAUDE_CODE_BUNDLED_SKILLS)

    def test_no_shipped_preload_names_a_bundled_skill(self):
        surfaces = ((".claude/agents", ".md"), *registry.mirror_surfaces())
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
        # materialize copies core then stack with stack winning on overlap.
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
        # A literal token in the battery source would flag its own scanner.
        sources = [
            ROOT / "verify-harness.py",
            *sorted((ROOT / "verify_harness").rglob("*.py")),
        ]
        for token in sync.PH_TOKENS:
            for src in sources:
                self.assertNotIn(token, src.read_text(encoding="utf-8"), str(src))


class ParityGateHelpers(unittest.TestCase):
    BODY = (
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
    )
    CANON = frozenset({"autofix", "blocked", "clarify", "escalate", "truncation"})

    def test_h2_headings_skip_fenced_blocks(self):
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

    def test_tag_findings_judges_variant_forms_instead_of_skipping_them(self):
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

    def test_stack_parallel_pins_name_a_proper_subset_and_match_each_stack(self):
        for rel_path, pins in sync.STACK_PARALLEL_PINNED.items():
            self.assertIn(rel_path, sync.STACK_PARALLEL_FILES)
            live = {}
            for s in STACKS:
                content = (ROOT / "stacks" / s / rel_path).read_text(encoding="utf-8")
                # Like the gate, frontmatter is stripped only behind an opening fence.
                lines = content.splitlines()
                if lines and text.FENCE.match(lines[0]):
                    lines = text.strip_frontmatter(content)
                live[s] = text.h2_headings(lines)
            for heading, carriers in pins.items():
                self.assertTrue(set(carriers) < set(STACKS), (heading, carriers))
                self.assertTrue(carriers, heading)
                for s in STACKS:
                    self.assertEqual(heading in live[s], s in carriers, (heading, s))
                    self.assertLessEqual(live[s].count(heading), 1, (heading, s))

    def test_stack_parallel_files_exist_in_every_stack(self):
        for rel_path in sync.STACK_PARALLEL_FILES:
            for s in STACKS:
                self.assertTrue(
                    (ROOT / "stacks" / s / rel_path).is_file(), (s, rel_path)
                )


class StackDetection(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.root = Path(self._td.name)

    def _detect(self, *markers):
        for m in markers:
            (self.root / m).write_text("", encoding="utf-8")
        return registry.detect_stack(self.root)

    def test_each_single_marker_maps_to_its_stack(self):
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
    """Constants the router, the grader, and the doctor manifest carry as hand-owned copies agree."""

    @staticmethod
    def _load_handoff_pkg():
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
        import importlib

        grading_config = importlib.import_module("grading.config")
        self.assertEqual(handoff.ROSTER_FLOOR, grading_config.REVIEWERS)
        self.assertEqual(
            list(handoff.ROSTER_FLOOR), self._manifest()["reviewers"]["floor"]
        )

    def test_retry_cap_matches_the_core_schema(self):
        handoff = self._load_handoff_pkg()
        import json

        schema = json.loads(
            (ROOT / "core/schemas/scratch/build-failure.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(handoff.RETRY_CAP, schema["properties"]["retry"]["maximum"])

    def test_channel_enum_matches_doctor_manifest(self):
        self.assertEqual(
            list(registry.CHANNELS),
            self._manifest()["project_data"]["channel_values"],
        )


class QuickSuiteSkipProof(unittest.TestCase):
    """The tools and eval suites skip under --quick only on a joint clean-tree proof."""

    def _battery(self, quick):
        return battery.Battery(quick=quick, strict=False)

    def _quiet(self):
        import contextlib
        import io

        sink = io.StringIO()
        return contextlib.redirect_stdout(sink), sink

    def test_no_proof_outside_quick(self):
        import unittest.mock as mock

        with mock.patch.object(suites, "git_status", return_value=CLEAN_TREE):
            self.assertIsNone(suites._quick_skip_proof(self._battery(quick=False)))

    def test_pending_change_blocks_the_proof(self):
        import unittest.mock as mock

        with mock.patch.object(
            suites, "git_status", return_value=PENDING_TOOLS_CHANGE
        ) as gs:
            self.assertIsNone(suites._quick_skip_proof(self._battery(quick=True)))
        gs.assert_called_once_with("tools/", "evals/")

    def test_clean_trees_yield_the_proof_in_quick(self):
        import unittest.mock as mock

        with mock.patch.object(suites, "git_status", return_value=CLEAN_TREE):
            self.assertIsNotNone(suites._quick_skip_proof(self._battery(quick=True)))

    def test_tools_suites_skip_runs_nothing(self):
        import unittest.mock as mock

        b = self._battery(quick=True)
        redirect, _ = self._quiet()
        with (
            mock.patch.object(suites, "git_status", return_value=CLEAN_TREE),
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
            mock.patch.object(suites, "git_status", return_value=CLEAN_TREE),
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

        def fake_run(cmd, **_kwargs):
            calls.append(cmd)
            return sp.CompletedProcess(cmd, 0, stdout="", stderr="")

        redirect, out = self._quiet()
        with (
            mock.patch.object(suites, "git_status", return_value=CLEAN_TREE),
            mock.patch.object(
                suites,
                "_dev_artifacts",
                return_value=[SOME_DEV_VIEW],
            ),
            mock.patch.object(suites.subprocess, "run", side_effect=fake_run),
            redirect,
        ):
            suites.check_eval_suites(b)
        self.assertFalse(b.failed)
        self.assertEqual(len(calls), 1)
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
            mock.patch.object(suites, "git_status", return_value=CLEAN_TREE),
            mock.patch.object(
                suites,
                "_dev_artifacts",
                return_value=[SOME_DEV_RUN],
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
    """The retired-paths check fails on a reintroduced entry, an uncovered deletion, and a tagless strict checkout."""

    def _run(self, strict, produced_now, retired, describe_rc=0):
        import contextlib
        import io
        import subprocess as sp
        import unittest.mock as mock

        import retired_paths

        b = battery.Battery(quick=False, strict=strict)
        describe = sp.CompletedProcess([], describe_rc, stdout=SOME_TAG, stderr="")
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

    def test_a_reproduced_manifest_entry_fails(self):
        failed, out = self._run(
            strict=False, produced_now={SEED_RETIRED_PATH}, retired=set()
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
            strict=True,
            produced_now=set(),
            retired=set(),
            describe_rc=GIT_DESCRIBE_NO_TAG,
        )
        self.assertTrue(failed)
        self.assertIn("fetch-depth", out)
        failed, out = self._run(
            strict=False,
            produced_now=set(),
            retired=set(),
            describe_rc=GIT_DESCRIBE_NO_TAG,
        )
        self.assertFalse(failed)
        self.assertIn("not checked", out)


class StrictToolPresence(unittest.TestCase):
    """A missing lint tool fails under --strict and skips without it."""

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
    """The mypy step reads its scope from the root pyproject and always checks the entries."""

    def test_scope_is_a_list_from_pyproject(self):
        self.assertIsInstance(lint._mypy_scope(), list)

    def test_an_empty_scope_still_checks_every_entry_module(self):
        import contextlib
        import io
        import types
        import unittest.mock as mock

        b = battery.Battery(quick=False, strict=True)
        sink = io.StringIO()
        clean = types.SimpleNamespace(returncode=0, stdout="", stderr="")
        with (
            mock.patch.object(lint.shutil, "which", return_value=SOME_MYPY_PATH),
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


class AnchorHelpers(unittest.TestCase):
    """github_slug and heading_anchors feed the link-integrity anchor check."""

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

    def test_fenced_headings_are_skipped_and_anchor_ids_are_collected(self):
        sample = '# Real\n\n```\n# commented heading\n```\n\n<a id="pinned"></a>\n'
        self.assertEqual(text.heading_anchors(sample), {"real", "pinned"})


def _pod_dockerfile(
    ruff="'ruff==" + PYPROJECT_RUFF_PIN + "'",
    mypy="'mypy==2.3.0'",
    binaries=CONFINEMENT_BINARIES,
    extra_line="",
):
    return (
        f"RUN pip install {ruff} {mypy} 'bandit==1.9.4'\n"
        f"RUN apt-get install -y {' '.join(binaries)}\n" + extra_line
    )


class PodToolchainPins(unittest.TestCase):
    """The pod Dockerfile's toolchain pins agree with the pyproject and stay ==-pinned."""

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

    def _write(self, root, dockerfile=None):
        pod = Path(root) / "tools/claude-dev"
        pod.mkdir(parents=True)
        (pod / "Dockerfile").write_text(
            dockerfile if dockerfile is not None else _pod_dockerfile(),
            encoding="utf-8",
        )
        (pod / "claude-dev").write_text(
            "CMD+=(--settings"
            ' \'{"sandbox":{"enabled":false,"failIfUnavailable":false}}\')\n',
            encoding="utf-8",
        )
        (Path(root) / "pyproject.toml").write_text(
            f'[tool.ruff]\nrequired-version = "{PYPROJECT_RUFF_PIN}"\n',
            encoding="utf-8",
        )
        # The workflow mirrors the image's pins, so a test that drifts the
        # image against pyproject still exercises that comparison alone.
        image = (pod / "Dockerfile").read_text(encoding="utf-8")
        pins = re.findall(r"'(ruff|mypy|bandit)==([0-9][0-9.]*)'", image)
        workflow = Path(root) / ".github/workflows"
        workflow.mkdir(parents=True)
        (workflow / "checks.yml").write_text(
            "".join(f'pipx install "{tool}=={version}"\n' for tool, version in pins),
            encoding="utf-8",
        )

    def test_real_repo_pins_agree(self):
        failed, err = self._run(text.ROOT)
        self.assertFalse(failed, err)

    def test_matching_synthetic_pins_pass(self):
        with tempfile.TemporaryDirectory() as root:
            self._write(root)
            failed, err = self._run(root)
            self.assertFalse(failed, err)

    def test_a_ruff_pin_off_the_pyproject_version_fails(self):
        with tempfile.TemporaryDirectory() as root:
            self._write(root, _pod_dockerfile(ruff=f"'ruff=={MISMATCHED_RUFF_PIN}'"))
            failed, err = self._run(root)
            self.assertTrue(failed)
            self.assertIn("required-version", err)

    def test_an_unpinned_mypy_fails(self):
        with tempfile.TemporaryDirectory() as root:
            self._write(root, _pod_dockerfile(mypy="mypy"))
            failed, err = self._run(root)
            self.assertTrue(failed)
            self.assertIn("==-pin mypy", err)

    def test_a_dropped_sandbox_override_fails(self):
        # bubblewrap cannot create a user namespace under the default seccomp
        # profile, so dropping the override would revive a startup refusal.
        with tempfile.TemporaryDirectory() as root:
            self._write(root)
            launcher = Path(root) / "tools/claude-dev/claude-dev"
            launcher.write_text("CMD=(claude)\n", encoding="utf-8")
            failed, err = self._run(root)
            self.assertTrue(failed)
            self.assertIn("sandbox-off --settings injection", err)

    def test_a_dropped_confinement_binary_fails(self):
        for binary in CONFINEMENT_BINARIES:
            with self.subTest(binary=binary), tempfile.TemporaryDirectory() as root:
                kept = [b for b in CONFINEMENT_BINARIES if b != binary]
                self._write(root, _pod_dockerfile(binaries=kept))
                failed, err = self._run(root)
                self.assertTrue(failed, binary)
                self.assertIn(binary, err)

    def test_an_install_piped_into_a_shell_fails(self):
        for tail in ("| bash", "| sudo bash", "|/bin/sh", "| env zsh", "| dash"):
            with self.subTest(tail=tail), tempfile.TemporaryDirectory() as root:
                curl = f"RUN curl -fsSL https://example.com/install.sh {tail}\n"
                self._write(root, _pod_dockerfile(extra_line=curl))
                failed, err = self._run(root)
                self.assertTrue(failed, tail)
                self.assertIn("pipes into a shell", err)


class ImportBoundaries(unittest.TestCase):
    """The import-boundary check passes on the real tree and names a forbidden edge by file and line."""

    def _run(self, here):
        import contextlib
        import io
        import unittest.mock as mock

        # The check resolves each file before relative_to(ROOT), so an
        # unresolved macOS tempdir would fall outside the patched root.
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
        # The gate fails on a table entry with no file, so both trees are copied.
        import shutil

        ignore = shutil.ignore_patterns("__pycache__")
        scripts = Path(root) / "core/scripts"
        shutil.copytree(lint.HERE / "core/scripts", scripts, ignore=ignore)
        shutil.copytree(
            lint.HERE / "verify_harness", Path(root) / "verify_harness", ignore=ignore
        )
        return scripts

    def test_real_repo_graph_is_intact(self):
        failed, err = self._run(lint.HERE)
        self.assertFalse(failed, err)

    def test_a_forbidden_edge_fails_with_its_file_and_line(self):
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
            self.assertIn("resolves to the entry itself", err)

    def test_a_module_missing_from_the_table_fails(self):
        with tempfile.TemporaryDirectory() as td:
            self._copy_trees(td)
            scripts = Path(td) / "core/scripts"
            (scripts / "newthing.py").write_text("x = 1\n", encoding="utf-8")
            failed, err = self._run(td)
            self.assertTrue(failed)
            self.assertIn("newthing.py", err)

    def test_a_leaf_importing_the_aggregator_fails_with_its_file_and_line(self):
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


class AnnotationProbe(unittest.TestCase):
    """The probe imports a scripts tree and evaluates every annotation on this interpreter."""

    PROBE = ROOT / "verify_harness" / "probe_annotations.py"

    GUARDED_IMPORT = (
        "try:\n"
        "    from engine import Config\n"
        "except ImportError:\n"
        "    pass\n\n"
        "if TYPE_CHECKING:\n"
        "    from engine import Config\n\n\n"
    )

    def probe(self, source, *, by_path=False):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        scripts = Path(tmp.name)
        (scripts / "entry.py").write_text(source, encoding="utf-8")
        (scripts / "engine").mkdir()
        (scripts / "engine" / "__init__.py").write_text(
            "class Config:\n    pass\n", encoding="utf-8"
        )
        entry = str(scripts / "entry.py")
        return subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(self.PROBE),
                str(scripts),
                entry,
                *(["--by-path", entry] if by_path else []),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_a_stub_only_generic_in_a_signature_fails_the_probe(self):
        done = self.probe(
            "import argparse\n\n\n"
            "def build(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:\n"
            "    return None\n"
        )

        self.assertEqual(done.returncode, 1)
        self.assertIn("entry.py: TypeError", done.stdout)

    def test_a_signature_that_evaluates_passes_the_probe(self):
        done = self.probe(
            "import re\n\n\n"
            "def build(pattern: re.Pattern[str]) -> list[str]:\n"
            "    return []\n"
        )

        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("1 annotated objects across 1 modules", done.stdout)

    def test_a_name_bound_only_under_a_guarded_import_fails_the_by_path_load(self):
        done = self.probe(
            "from typing import TYPE_CHECKING\n\n"
            + self.GUARDED_IMPORT
            + "def build(config: Config) -> None:\n    return None\n",
            by_path=True,
        )

        self.assertEqual(done.returncode, 1)
        self.assertIn("entry.py (loaded by path): NameError", done.stdout)

    def test_the_string_form_of_a_guarded_name_passes_the_by_path_load(self):
        done = self.probe(
            "from typing import TYPE_CHECKING\n\n"
            + self.GUARDED_IMPORT
            + 'def build(config: "Config") -> None:\n    return None\n',
            by_path=True,
        )

        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("1 of them loaded by path as well", done.stdout)


def _load_launcher():
    spec = importlib.util.spec_from_file_location(
        "verify_harness_launcher", ROOT / "verify-harness.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalized(label):
    return "".join(ch for ch in re.sub(r"\(.*?\)", "", label).lower() if ch.isalnum())


def _header_steps(source):
    """Return the header's (id, label) pairs in step order, read from both columns."""
    header = source.split('"""')[1]
    table = header.split("re-enumerating:\n", 1)[1].split("\n\n", 1)[0]
    steps = []
    for line in table.splitlines():
        for column in (line[:41], line[41:]):
            match = re.match(r"^\s*(\d)([a-z]*)\s+(.+?)\s*$", column)
            if match:
                steps.append(((int(match.group(1)), match.group(2)), match.group(3)))
    return [label for _, label in sorted(steps, key=lambda step: step[0])]


def _dispatched_titles(source):
    """Return the note title of every step `_run_steps` dispatches, in order."""
    tree = ast.parse(source)
    run_steps = next(
        n
        for n in tree.body
        if isinstance(n, ast.FunctionDef) and n.name == "_run_steps"
    )
    titles = []
    for call in (
        s.value
        for s in run_steps.body
        if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call)
    ):
        if isinstance(call.func, ast.Attribute):
            titles.append(call.args[0].value)
        else:
            titles.append(_note_title(call.func.id))
    return titles


def _note_title(function_name):
    for path in (ROOT / "verify_harness" / "checks").glob("*.py"):
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                for call in ast.walk(node):
                    if (
                        isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and call.func.attr == "note"
                    ):
                        argument = call.args[0]
                        if isinstance(argument, ast.JoinedStr):
                            argument = argument.values[0]
                        return argument.value
    raise AssertionError(f"no note title for {function_name}")


class LauncherHeader(unittest.TestCase):
    def test_the_header_lists_every_dispatched_step_in_order(self):
        source = (ROOT / "verify-harness.py").read_text()
        labels = _header_steps(source)
        titles = _dispatched_titles(source)
        self.assertEqual(len(labels), len(titles))
        for label, title in zip(labels, titles, strict=True):
            self.assertTrue(
                _normalized(title).startswith(_normalized(label)), (label, title)
            )


class LauncherVerdict(unittest.TestCase):
    def test_an_unknown_flag_is_a_usage_failure_with_exit_two(self):
        launcher = _load_launcher()
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = launcher.main(["verify-harness.py", "--bogus"])
        self.assertEqual(code, 2)
        self.assertTrue(err.getvalue().startswith("FAIL: usage:"))

    def test_a_failed_run_ends_with_the_verdict_line(self):
        launcher = _load_launcher()
        b = battery.Battery(quick=False)
        b.failed = True
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = launcher._verdict(b)
        self.assertEqual(code, 1)
        self.assertIn("FAIL: verify-harness: see failures above", err.getvalue())


class ShippedProseGates(unittest.TestCase):
    def _run(self, check, layer_text, suffix=".md"):
        import tempfile
        from unittest import mock

        with tempfile.TemporaryDirectory() as td:
            layer = Path(td) / "core"
            skill = layer / ".claude" / "skills" / "one"
            skill.mkdir(parents=True)
            (skill / f"SKILL{suffix}").write_text(layer_text, encoding="utf-8")
            b = battery.Battery(quick=False)
            err = io.StringIO()
            with (
                mock.patch.object(sync, "LAYERS", (layer,)),
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(err),
            ):
                check(b)
            return b.failed, err.getvalue()

    def test_clean_prose_passes_both_gates(self):
        text = "---\ntoolCallBudget: 12\n---\nRead docs/adr/ before writing. The placeholder is REQ-XX-001.\n"
        self.assertFalse(self._run(sync.check_prose_self_containment, text)[0])
        self.assertFalse(self._run(sync.check_runtime_number_free_prose, text)[0])

    def test_a_dated_decision_record_citation_fails(self):
        failed, err = self._run(
            sync.check_prose_self_containment,
            "See docs/adr/2026-07-19-network-write-confinement-gate.md.\n",
        )
        self.assertTrue(failed)
        self.assertIn("decision record", err)

    def test_a_concrete_requirement_id_fails(self):
        failed, err = self._run(
            sync.check_prose_self_containment, "Implements REQ-AUTH-002.\n"
        )
        self.assertTrue(failed)
        self.assertIn("requirement id", err)

    def test_the_schema_placeholder_and_a_write_scope_path_pass(self):
        text = '{"pattern": "docs/adr/2026-01-01-...md"}'
        self.assertFalse(
            self._run(sync.check_prose_self_containment, text, suffix=".json")[0]
        )

    def test_a_numeric_budget_outside_frontmatter_fails(self):
        failed, err = self._run(
            sync.check_runtime_number_free_prose,
            "---\nname: x\n---\nStop after 40 tool calls.\n",
        )
        self.assertTrue(failed)
        self.assertIn("runtime number", err)

    def test_enforcer_tactic_lines_are_checklist_lines_without_a_citation(self):
        text = (
            "- [ ] `@Service` for stateless services\n"
            "- [ ] `@Entity` only where the Brief's § Language Realization says\n"
            "- [ ] Aggregates are the consistency boundary\n"
            "- [ ] Early returns for edge cases\n"
            "A `@Service` named in prose is not a checklist line.\n"
        )
        self.assertEqual(
            sync.enforcer_tactic_lines(text),
            [
                "- [ ] `@Service` for stateless services",
                "- [ ] Aggregates are the consistency boundary",
            ],
        )

    def test_enforcer_tactic_annotation_match_is_case_sensitive(self):
        text = (
            "- [ ] Javadoc carries no `@param` tag restating the signature\n"
            "- [ ] Contact `owner@example.com` on a failure\n"
            "- [ ] `@Repository` per aggregate root\n"
        )
        self.assertEqual(
            sync.enforcer_tactic_lines(text), ["- [ ] `@Repository` per aggregate root"]
        )

    def test_section_body_reads_back_what_init_realizes_across_a_fenced_heading(self):
        init_mod = load("init_for_pin", "init.py")
        body = "Rows.\n\n```text\n## not a heading\n```\n\nMore rows.\n"
        template = "# T\n\n## Language Realization\n\n<!-- slot -->\n\n## Naming\n\nn\n"
        realized = init_mod.realize(template, body)
        self.assertEqual(
            sync._section_body(realized, "## Language Realization"), body.strip("\n")
        )
        self.assertEqual(init_mod.realize(realized, body), realized)

    def test_pinned_multiset_reports_each_side_of_a_divergence(self):
        with tempfile.TemporaryDirectory() as td:
            expected = Path(td) / "x.expected"
            expected.write_text("# header\n\nkept\ngone\n", encoding="utf-8")
            live = sync.Counter({"kept": 1, "new": 1})
            self.assertEqual(
                sync._pinned_multiset_problems(
                    expected, sync.Counter({"kept": 1, "gone": 1}), "s", "f"
                ),
                [],
            )
            (problem,) = sync._pinned_multiset_problems(expected, live, "s", "Fix it")
            self.assertIn("    - gone\n    + new\nFix it", problem)
            self.assertIn(
                "missing",
                sync._pinned_multiset_problems(Path(td) / "none", live, "s", "f")[0],
            )

    def test_the_live_tree_passes_both_gates(self):
        for check in (
            sync.check_prose_self_containment,
            sync.check_runtime_number_free_prose,
        ):
            b = battery.Battery(quick=False)
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                check(b)
            self.assertFalse(b.failed, check.__name__)


if __name__ == "__main__":
    unittest.main()
