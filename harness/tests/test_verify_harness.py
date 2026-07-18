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
battery (the aggregator), checks.lint / checks.faithful / checks.suites (the
step functions). ROOT here is the harness/ toolbox root (_loader), which is
exactly verify_harness.text.HERE; the repo root is verify_harness.text.ROOT.
"""

import sys
import tempfile
import unittest
from pathlib import Path

from _loader import ROOT

sys.path.insert(0, str(ROOT))

import helpers  # noqa: E402
from verify_harness import battery, text  # noqa: E402
from verify_harness.checks import faithful, lint, suites  # noqa: E402

STACKS = helpers.STACKS


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


class HelperRosterParity(unittest.TestCase):
    def test_helpers_sh_rosters_match_helpers_py(self):
        # helpers.py is the source; helpers.sh mirrors only STACKS — the one
        # roster a bash orchestrator still consumes (bootstrap.sh). The tool
        # rosters live in helpers.py alone. Two hand-maintained copies need a
        # gate — this is it.
        sh = (ROOT / "helpers.sh").read_text(encoding="utf-8")
        import re

        for name in ("STACKS",):
            m = re.search(rf"^{name}=\(([^)]*)\)", sh, re.M)
            self.assertIsNotNone(m, f"{name} roster missing from helpers.sh")
            self.assertEqual(
                tuple(m.group(1).split()),
                getattr(helpers, name),
                f"{name} drifted between helpers.sh and helpers.py",
            )
        self.assertNotIn("ALL_TOOLS", sh, "tool rosters must live only in helpers.py")
        self.assertNotIn(
            "PLUGIN_TOOLS", sh, "tool rosters must live only in helpers.py"
        )


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
                self.assertIsNotNone(faithful.PH_ALLOW.match(path))

    def test_runtime_content_is_not_allowed(self):
        for path in (
            "harness/core/.claude/skills/tdd-workflow/SKILL.md",
            "docs/agentic-harness.md",
            "samples/go/docs/testing-principles.md",
            "README.md",
        ):
            with self.subTest(path=path):
                self.assertIsNone(faithful.PH_ALLOW.match(path))

    def test_tokens_are_built_by_concatenation(self):
        # The battery source must never contain the literal token, or the
        # placeholder gate would flag its own scanner. The source is now the
        # launcher plus the verify_harness package.
        sources = [
            ROOT / "verify-harness.py",
            *sorted((ROOT / "verify_harness").rglob("*.py")),
        ]
        for token in faithful.PH_TOKENS:
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
        for skill_pair, pins in faithful.IDE_HEADING_DELTA.items():
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
        for rel_path, pins in faithful.STACK_PARALLEL_PINNED.items():
            self.assertIn(rel_path, faithful.STACK_PARALLEL_FILES)
            live = {}
            for s in STACKS:
                content = (ROOT / "stacks" / s / rel_path).read_text(encoding="utf-8")
                live[s] = set(text.h2_headings(text.strip_frontmatter(content)))
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

    def test_stack_parallel_files_exist_in_every_stack(self):
        # The roster gate skips a file missing from two stacks (len < 2
        # guard); pin the premise that all nine parallels ship three copies.
        for rel_path in faithful.STACK_PARALLEL_FILES:
            for s in STACKS:
                self.assertTrue(
                    (ROOT / "stacks" / s / rel_path).is_file(),
                    f"stacks/{s}/{rel_path} missing",
                )


class DetectStack(unittest.TestCase):
    # The marker-priority contract is load-bearing for bootstrap.sh, /init,
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
        return helpers.detect_stack(self.root)

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
                self.assertEqual(helpers.detect_stack(self.root), stack)
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

    def test_retry_cap_matches_every_stack_schema(self):
        handoff = self._load_handoff_pkg()
        import json

        for s in STACKS:
            schema = json.loads(
                (
                    ROOT / "stacks" / s / "schemas/scratch/build-failure.schema.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                handoff.RETRY_CAP,
                schema["properties"]["retry"]["maximum"],
                f"stacks/{s} build-failure retry.maximum drifted from RETRY_CAP",
            )

    def test_channel_enum_matches_doctor_manifest(self):
        self.assertEqual(
            list(helpers.CHANNELS),
            self._manifest()["project_data"]["channel_values"],
            "helpers.CHANNELS and the doctor manifest disagree",
        )


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
        pod = Path(root) / "tools/claude-pod"
        pod.mkdir(parents=True)
        (pod / "Dockerfile").write_text(
            f"RUN pip install 'ruff=={ruff_pin}' 'mypy==2.3.0' 'bandit==1.9.4'\n",
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
            df = Path(root) / "tools/claude-pod/Dockerfile"
            df.write_text(
                "RUN pip install 'ruff==0.15.22' mypy 'bandit==1.9.4'\n",
                encoding="utf-8",
            )
            failed, err = self._run(root)
            self.assertTrue(failed)
            self.assertIn("==-pin mypy", err)


class ImportBoundaries(unittest.TestCase):
    """1g gates the scripts composition root's one-way import graph (ADR
    2026-07-17 runtime-package-layout) and the battery's own verify_harness
    package (ADR 2026-07-18 check-sync-decomposition). It passes on the real
    tree and bites a forbidden edge with a file:line message."""

    def _run(self, here):
        import contextlib
        import io
        import unittest.mock as mock

        b = battery.Battery(quick=False, strict=True)
        err = io.StringIO()
        with (
            mock.patch.object(lint, "HERE", Path(here)),
            mock.patch.object(text, "ROOT", Path(here)),
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
