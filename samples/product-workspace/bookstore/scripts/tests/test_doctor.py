#!/usr/bin/env python3
"""The doctor's checks, each driven over a materialized project tree."""

import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import doctor

SCRIPTS = Path(__file__).resolve().parent.parent
MANIFEST = SCRIPTS / "doctor-expectations.toml"
TEMPLATES = SCRIPTS.parent / ".claude/skills/doctor/templates"


def setUpModule():
    # The marketplace channel ships the templates in the plugin cache, so the
    # suite skips there; every other channel materializes them, so their
    # absence is a broken tree. A tree with no readable layout is pre-init.
    if TEMPLATES.is_dir():
        return
    layout = SCRIPTS / "layout.toml"
    try:
        channel = (
            tomllib.loads(layout.read_text(encoding="utf-8"))
            .get("harness", {})
            .get("channel", "copy")
        )
    except (OSError, tomllib.TOMLDecodeError):
        channel = None
    if channel is None or channel == "marketplace":
        raise unittest.SkipTest(
            "doctor templates not in this tree (plugin-delivered on the "
            "marketplace channel) — suite skipped"
        )
    raise RuntimeError(
        f".claude/skills/doctor/templates missing on the '{channel}' channel — "
        "materialize the runtime (or the install is broken)"
    )


def manifest_value(*keys):
    """Read one value from the manifest, so a test never copies it."""
    node = tomllib.loads(MANIFEST.read_text(encoding="utf-8"))
    for key in keys:
        node = node[key]
    return node


def manifest_file_entry(path):
    return next(entry for entry in manifest_value("file") if entry["path"] == path)


SPEC_VERSION = manifest_value("spec_version")
SYSTEM_DESIGN_CEILING = manifest_file_entry("docs/system-design.md")["max_words"]
SOME_OTHER_SPEC_VERSION = "9.9.9"
OVERSHOOT_WORDS = 1000
RAISED_CEILING = (SYSTEM_DESIGN_CEILING + OVERSHOOT_WORDS) * 2

STAMP_DATE = "2026-01-01"
NEWER_PLUGIN_DATE = "2026-02-02"
ANOTHER_REAL_DATE = "2026-06-26"
IMPOSSIBLE_SHAPED_DATE = "2026-13-99"
SOME_PROJECT_NAME = "sample"

TEMPLATE_TARGETS = {
    "prd.md": "docs/prd.md",
    "system-design.md": "docs/system-design.md",
    "ubiquitous-language.md": "docs/ubiquitous-language.md",
    "testing-principles.md": "docs/testing-principles.md",
    "architecture-principles.md": "docs/architecture-principles.md",
    "security-principles.md": "docs/security-principles.md",
    "adr-README.md": "docs/adr/README.md",
}

DEFAULT_TOOLS = ("claude", "copilot", "opencode")
FLOOR_REVIEWERS = (
    "code-quality-reviewer",
    "test-reviewer",
    "security-reviewer",
    "doc-reviewer",
)
REVIEWER_TOOL_DIRS = {
    "claude": ".claude/agents/{name}.md",
    "copilot": ".github/agents/{name}.agent.md",
    "opencode": ".opencode/agents/{name}.md",
}
A_FLOOR_REVIEWER = "security-reviewer"
EXTRA_REVIEWER = "perf-reviewer"
UNDECLARED_REVIEWER = "payment-reviewer"
MISNAMED_EXTRA = "perf"
UNKNOWN_TOOL = "cursor"

HOOK = "handoff-allow.py"
HOOK_SUBSTRING = "allow.py"
LEGACY_SHELL_HOOK = "handoff-allow.sh"
HOOK_TEST_SIBLING = "test_handoff_allow.py"
ABSENT_HOOK = "handoff-allow.py"

SOME_EXTENSION_SKILL = ".claude/skills/pricing-refresh"
A_HARNESS_SKILL = ".claude/skills/tdd-workflow"

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
    "PATH": "/usr/bin:/bin:/usr/local/bin",
}


def matcher_for(hook):
    """The settings.json body that registers one hook script."""
    return (
        '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command",'
        f'"command":"python3 \\"${{CLAUDE_PROJECT_DIR}}/.claude/hooks/{hook}\\""}}]}}]}}}}'
    )


def reviewer_paths(name, tools=DEFAULT_TOOLS):
    """The agent-body paths for a reviewer across the given tool surfaces."""
    return [REVIEWER_TOOL_DIRS[t].format(name=name) for t in tools]


def write_reviewer_bodies(root, names, tools=DEFAULT_TOOLS, *, stanza=True):
    """Write a body per reviewer and tool; the default carries the dispatch-event contract."""
    conforming = (
        "# {name}\n\n## First Tool Call\n\nAppend one "
        "`dispatch-start` record as your first tool call.\n\n"
        "## Output\n\nAppend a `review-feedback` record per the "
        "`review-workflow` skill Output Protocol.\n"
    )
    for name in names:
        for rel in reviewer_paths(name, tools):
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            text = conforming.format(name=name) if stanza else f"# {name}\n"
            path.write_text(text, encoding="utf-8")


@dataclass(frozen=True)
class HarnessTable:
    """The [harness] table a fixture declares in scripts/layout.toml."""

    channel: str = "copy"
    spec_version: str = SPEC_VERSION
    tools: tuple = DEFAULT_TOOLS
    extensions: tuple | None = None
    extra_reviewers: tuple | None = None

    def render(self):
        text = f'[harness]\nchannel = "{self.channel}"\nspec_version = "{self.spec_version}"\n'
        text += "tools = [" + ", ".join(f'"{t}"' for t in self.tools) + "]\n"
        if self.extensions is not None:
            items = ", ".join(f'"{e}"' for e in self.extensions)
            text += f"extensions = [{items}]\n"
        if self.extra_reviewers is not None:
            items = ", ".join(f'"{r}"' for r in self.extra_reviewers)
            text += f"extra_reviewers = [{items}]\n"
        return text


A_COPY_PROJECT = HarnessTable()


def materialize(root, harness=A_COPY_PROJECT, *, write_bodies=True):
    """Lay down the briefs, the layout, a stamped CLAUDE.md, and the floor bodies."""
    for template, target in TEMPLATE_TARGETS.items():
        text = (TEMPLATES / template).read_text(encoding="utf-8")
        text = text.replace("{{PROJECT_NAME}}", SOME_PROJECT_NAME)
        text = text.replace("{{HARNESS_DATE}}", STAMP_DATE)
        path = root / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    scripts = root / "scripts"
    scripts.mkdir(exist_ok=True)
    (scripts / "layout.toml").write_text(harness.render(), encoding="utf-8")
    chapters = "\n\n".join(f"{t}\n\nDoctrine." for t in doctor.REQUIRED_CHAPTERS)
    (root / "CLAUDE.md").write_text(
        f"<!-- harness: {STAMP_DATE} -->\n# CLAUDE.md\n\n{chapters}\n\n## Toolchain\n\nBuild.\n",
        encoding="utf-8",
    )
    # Marketplace ships the floor bodies in the plugin, never the tree.
    if write_bodies and harness.channel != "marketplace":
        write_reviewer_bodies(root, FLOOR_REVIEWERS, harness.tools)


class DoctorCase(unittest.TestCase):
    """A materialized project tree with the declared [harness] table."""

    HARNESS = A_COPY_PROJECT

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        materialize(self.root, self.HARNESS)

    def results(self, **kwargs):
        return doctor.run(self.root, MANIFEST, **kwargs)

    def rows(self, check):
        return [r for r in self.results() if r.check == check]

    def statuses(self, check):
        return [r.status for r in self.rows(check)]

    def failures(self):
        return [r for r in self.results() if r.status == doctor.FAIL]

    def assert_failure_mentions(self, fragment):
        failures = self.failures()
        self.assertTrue(
            any(fragment in r.detail for r in failures),
            f"expected a failure mentioning {fragment!r}, got: {failures}",
        )

    def assert_check_passes(self, check):
        rows = self.rows(check)
        self.assertTrue(rows and all(r.status == doctor.PASS for r in rows), rows)

    def edit(self, target, old, new):
        path = self.root / target
        text = path.read_text(encoding="utf-8")
        assert old in text, f"{old!r} not found in {target}"
        path.write_text(text.replace(old, new), encoding="utf-8")

    def append_layout(self, text):
        path = self.root / "scripts/layout.toml"
        path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")

    def write_settings(self, name, body):
        (self.root / ".claude").mkdir(parents=True, exist_ok=True)
        (self.root / ".claude" / name).write_text(body, encoding="utf-8")

    def git_add_all(self):
        git = shutil.which("git")
        if git is None:
            self.skipTest("git unavailable")
        subprocess.run([git, "init", "-q"], cwd=self.root, check=True, env=GIT_ENV)
        subprocess.run([git, "add", "."], cwd=self.root, check=True, env=GIT_ENV)


class FreshMaterialization(DoctorCase):
    def test_passes_every_check(self):
        self.assertEqual(self.failures(), [])


class ProjectData(DoctorCase):
    def test_a_missing_layout_fails_without_a_crash(self):
        (self.root / "scripts/layout.toml").unlink()
        self.assert_failure_mentions("scripts/layout.toml missing")

    def test_an_unparseable_layout_fails_without_a_crash(self):
        (self.root / "scripts/layout.toml").write_text("[harness\n", encoding="utf-8")
        self.assert_failure_mentions("scripts/layout.toml unparseable")

    def test_a_layout_without_a_harness_table_fails(self):
        (self.root / "scripts/layout.toml").write_text("[test]\n", encoding="utf-8")
        self.assert_failure_mentions("harness.channel missing")

    def test_a_channel_outside_the_manifest_values_fails(self):
        materialize(self.root, HarnessTable(channel="floppy"))
        self.assert_failure_mentions("channel must be one of")

    def test_a_spec_version_other_than_the_manifests_fails(self):
        materialize(self.root, HarnessTable(spec_version=SOME_OTHER_SPEC_VERSION))
        self.assert_failure_mentions(f"spec_version {SOME_OTHER_SPEC_VERSION}")

    def test_a_quoted_auto_grade_fails(self):
        # The router fails open on a non-boolean, so this is the layer that
        # catches the typo.
        self.append_layout('auto_grade = "false"\n')
        self.assert_failure_mentions("harness.auto_grade must be a boolean")

    def test_a_boolean_auto_grade_passes(self):
        self.append_layout("auto_grade = false\n")
        self.assertEqual([f for f in self.failures() if "auto_grade" in f.detail], [])

    def test_an_unknown_tool_name_fails_instead_of_being_filtered(self):
        self.edit(
            "scripts/layout.toml",
            'tools = ["claude"',
            'tools = ["copilott", "claude"',
        )
        self.assert_failure_mentions("unknown surface 'copilott'")


class RosterFiles(DoctorCase):
    def test_a_missing_brief_fails_naming_its_template(self):
        (self.root / "docs/testing-principles.md").unlink()
        self.assert_failure_mentions("materialize templates/testing-principles.md")

    def test_a_decision_log_without_a_readme_fails(self):
        (self.root / "docs/adr/README.md").unlink()
        self.assert_failure_mentions("README.md missing")

    def test_a_missing_required_section_fails(self):
        self.edit("docs/system-design.md", "## Threat Model", "## Threats")
        self.assert_failure_mentions("'## Threat Model' missing")

    def test_a_pyramid_without_percentage_shares_fails_the_slot(self):
        brief = self.root / "docs/testing-principles.md"
        text = brief.read_text(encoding="utf-8").replace("%", "")
        brief.write_text(text, encoding="utf-8")
        self.assert_failure_mentions("'Test Pyramid' lacks required data")

    def test_an_adr_entry_outside_the_dated_kebab_shape_fails(self):
        (self.root / "docs/adr/notes.md").write_text("# Notes\n", encoding="utf-8")
        self.assert_failure_mentions("notes.md violates entry naming")

    def test_a_dated_kebab_adr_entry_passes(self):
        (self.root / "docs/adr/2026-01-01-first-decision.md").write_text(
            "# First Decision\n", encoding="utf-8"
        )
        self.assertEqual(self.failures(), [])


class RequirementIds(DoctorCase):
    def test_a_design_citation_the_prd_never_defines_fails(self):
        self.edit(
            "docs/system-design.md",
            "## Threat Model",
            "Realizes REQ-AB-999.\n\n## Threat Model",
        )
        self.assert_failure_mentions("REQ-AB-999")

    def test_a_four_digit_id_fails_at_doctor_time(self):
        # The record schemas anchor req_id to three digits; the near miss must
        # fail here, not on the first ledger append.
        self.edit(
            "docs/prd.md",
            "## Open Questions",
            "The system does a thing `[REQ-AB-1000]`.\n\n"
            "**Done when:**\n- `[REQ-AB-1000]` given input, when run, then output.\n\n"
            "## Open Questions",
        )
        self.assert_failure_mentions("REQ-AB-1000")

    def test_a_cited_id_the_prd_defines_passes(self):
        self.edit(
            "docs/prd.md",
            "## Open Questions",
            '<a id="req-ab-999"></a>\nThe system does a sample thing `[REQ-AB-999]`.\n\n'
            "**Done when:**\n- `[REQ-AB-999]` given input, when run, then output.\n\n"
            "## Open Questions",
        )
        self.edit(
            "docs/system-design.md",
            "## Threat Model",
            "Realizes REQ-AB-999.\n\n## Threat Model",
        )
        self.assertEqual(self.failures(), [])

    def test_an_id_mentioned_only_in_prose_fails(self):
        self.edit(
            "docs/prd.md",
            "## Open Questions",
            "Some narrative names `[REQ-AB-001]` but never bounds it.\n\n## Open Questions",
        )
        self.assert_failure_mentions("mentioned only in prose")

    def test_an_id_with_an_acceptance_bullet_passes(self):
        self.edit(
            "docs/prd.md",
            "## Open Questions",
            "Narrative for `[REQ-AB-001]`.\n\n**Done when:**\n"
            "- `[REQ-AB-001]` given x, when run, then y.\n\n## Open Questions",
        )
        self.assert_check_passes("req-acceptance")

    def test_an_id_inside_a_code_fence_is_not_an_orphan(self):
        self.edit(
            "docs/prd.md",
            "## Open Questions",
            "```\nThe system does X `[REQ-AB-002]`.\n```\n\n## Open Questions",
        )
        self.assert_check_passes("req-acceptance")


class DesignDocFormat(DoctorCase):
    def test_a_field_table_fails(self):
        self.edit(
            "docs/system-design.md",
            "## Contracts",
            "## Contracts\n\n| Field | Type | Description |\n|---|---|---|\n"
            "| id | string | the id |\n",
        )
        self.assert_failure_mentions("field/parameter table")

    def test_a_field_table_inside_a_code_fence_passes(self):
        self.edit(
            "docs/system-design.md",
            "## Contracts",
            "## Contracts\n\n```\n| Field | Type |\n| id | string |\n```\n",
        )
        self.assert_check_passes("field-tables")


class DocBudgets(DoctorCase):
    def pad_the_design_doc(self):
        self.edit(
            "docs/system-design.md",
            "## Overview",
            "## Overview\n\n" + ("word " * (SYSTEM_DESIGN_CEILING + OVERSHOOT_WORDS)),
        )

    def test_a_doc_over_its_ceiling_fails(self):
        self.pad_the_design_doc()
        self.assert_failure_mentions(f"over the {SYSTEM_DESIGN_CEILING}-word ceiling")

    def test_a_layout_override_raises_the_ceiling(self):
        self.pad_the_design_doc()
        self.append_layout(f"system_design_max_words = {RAISED_CEILING}\n")
        budget = [r for r in self.rows("doc-budget") if "system-design" in r.detail]
        self.assertTrue(budget and all(r.status == doctor.PASS for r in budget), budget)
        self.assertIn("override", budget[0].detail)


class HandbookBoundary(DoctorCase):
    def test_a_brief_referencing_a_handbook_doc_fails(self):
        self.edit(
            "docs/prd.md",
            "## Open Questions",
            "See agentic-harness.md for the loop model.\n\n## Open Questions",
        )
        self.assert_failure_mentions("agentic-harness.md")

    def test_a_handbook_doc_copied_into_docs_fails(self):
        (self.root / "docs/tdd-principles.md").write_text("# stale\n", encoding="utf-8")
        self.assert_failure_mentions("harness-owned handbook doc")


class HookRegistration(DoctorCase):
    def write_hook(self, name=HOOK):
        hooks = self.root / ".claude/hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        (hooks / name).write_text("#!/usr/bin/env python3\n", encoding="utf-8")

    def test_a_registered_hook_passes(self):
        self.write_hook()
        self.write_settings("settings.json", matcher_for(HOOK))
        self.assertEqual(self.failures(), [])

    def test_an_unregistered_hook_fails(self):
        self.write_hook()
        self.write_settings("settings.json", '{"hooks":{"PreToolUse":[]}}')
        self.assert_failure_mentions(
            f"{HOOK} present in .claude/hooks/ but not registered"
        )

    def test_a_legacy_shell_hook_is_still_checked(self):
        self.write_hook(LEGACY_SHELL_HOOK)
        self.write_settings("settings.json", '{"hooks":{"PreToolUse":[]}}')
        self.assert_failure_mentions(
            f"{LEGACY_SHELL_HOOK} present in .claude/hooks/ but not registered"
        )

    def test_a_test_sibling_needs_no_registration(self):
        self.write_hook()
        self.write_hook(HOOK_TEST_SIBLING)
        self.write_settings("settings.json", matcher_for(HOOK))
        self.assertEqual(self.failures(), [])

    def test_a_hook_without_any_settings_file_fails(self):
        self.write_hook()
        self.assert_failure_mentions("no .claude/settings.json to register them")

    def test_a_hook_whose_name_is_a_substring_of_a_registered_one_still_fails(self):
        self.write_hook(HOOK_SUBSTRING)
        self.write_hook(HOOK)
        self.write_settings("settings.json", matcher_for(HOOK))
        self.assert_failure_mentions(
            f"{HOOK_SUBSTRING} present in .claude/hooks/ but not registered"
        )

    def test_a_matcher_for_an_absent_script_fails(self):
        self.write_settings("settings.json", matcher_for(ABSENT_HOOK))
        self.assert_failure_mentions("the script is absent")


class LayoutTables(DoctorCase):
    def append_module_rule(self, strategy):
        self.append_layout(f'\n[[module]]\nmatch = "src/**"\nfrom = "{strategy}"\n')

    def write_defaults(self, text):
        (self.root / "scripts/layout-defaults.toml").write_text(text, encoding="utf-8")

    def test_every_module_strategy_the_engine_accepts_passes(self):
        for strategy in ("dir", "gradle", "maven", "regex:(src/[^/]+)/"):
            with self.subTest(strategy=strategy):
                self.append_module_rule(strategy)
                self.assertEqual(self.statuses("layout-modules"), [doctor.PASS])

    def test_an_unknown_module_strategy_fails_at_doctor_time(self):
        self.append_module_rule("dirr")
        self.assert_failure_mentions("unknown 'from' strategy")

    def test_a_valid_review_table_passes(self):
        self.append_layout(
            '\n[review]\nmode = "always-full"\nsize_threshold = 100\n'
            '\n[review.surface_reviewers]\ndocs = ["doc-reviewer"]\n'
        )
        self.assertEqual(self.statuses("layout-review"), [doctor.PASS])

    def test_the_review_check_validates_the_merged_probe(self):
        self.write_defaults("[review]\nsecurity_surface = ['@Get(']\n")
        rows = self.rows("layout-review")
        self.assertEqual([r.status for r in rows], [doctor.FAIL])
        self.assertIn("not a valid regex", rows[0].detail)

    def test_a_review_pass_names_the_probe_in_effect(self):
        probes = ("@Get", "@Post")
        self.write_defaults(f"[review]\nsecurity_surface = {list(probes)!r}\n")
        rows = self.rows("layout-review")
        self.assertEqual([r.status for r in rows], [doctor.PASS])
        self.assertIn(f"stack default, {len(probes)} patterns", rows[0].detail)
        self.append_layout("\n[review]\nsecurity_surface = []\n")
        self.assertIn("empty", self.rows("layout-review")[0].detail)

    def test_a_defaults_file_carrying_a_project_fact_fails(self):
        self.write_defaults("[review]\nsize_threshold = 1000\n")
        rows = self.rows("layout-defaults")
        self.assertEqual([r.status for r in rows], [doctor.FAIL])
        self.assertIn("size_threshold", rows[0].detail)

    def test_a_restated_default_warns(self):
        self.write_defaults("[conventions]\ncomment_markers = ['//']\n")
        self.append_layout("\n[conventions]\ncomment_markers = ['//']\n")
        rows = self.rows("layout-defaults")
        self.assertEqual([r.status for r in rows], [doctor.WARN])
        self.assertIn("conventions.comment_markers", rows[0].detail)

    def test_a_missing_defaults_file_skips(self):
        self.assertEqual(self.statuses("layout-defaults"), [doctor.SKIP])

    def test_a_malformed_review_mode_fails_at_doctor_time(self):
        self.append_layout('\n[review]\nmode = "sometimes"\n')
        self.assert_failure_mentions("mode must be 'risk' or 'always-full'")

    def test_a_surface_reviewer_outside_the_roster_fails(self):
        self.append_layout(
            '\n[review.surface_reviewers]\ndocs = ["stranger-reviewer"]\n'
        )
        self.assert_failure_mentions("roster reviewer names")

    def test_a_valid_gate_table_passes(self):
        self.append_layout('\n[gate]\ncommand = "make ci"\nverbs = ["build", "test"]\n')
        self.assertEqual(self.statuses("layout-gate"), [doctor.PASS])

    def test_an_absent_gate_table_is_a_visible_skip(self):
        self.assertEqual(self.statuses("layout-gate"), [doctor.SKIP])

    def test_gate_verbs_of_the_wrong_shape_fail(self):
        self.append_layout('\n[gate]\ncommand = "make ci"\nverbs = "build"\n')
        self.assert_failure_mentions("verbs must be a non-empty list of strings")

    def test_a_gate_table_without_a_command_fails(self):
        self.append_layout('\n[gate]\nverbs = ["build"]\n')
        self.assert_failure_mentions("command must be a non-empty string")


class ManagedChapters(DoctorCase):
    def test_a_missing_claude_md_fails(self):
        (self.root / "CLAUDE.md").unlink()
        self.assert_failure_mentions("no CLAUDE.md in project root")

    def test_a_claude_md_without_the_chapter_fails(self):
        (self.root / "CLAUDE.md").write_text(
            "# CLAUDE.md\n\nNo managed chapter here.\n", encoding="utf-8"
        )
        self.assert_failure_mentions("no '## Agent Usage (Mandatory)' chapter")

    def test_an_empty_chapter_fails(self):
        (self.root / "CLAUDE.md").write_text(
            "# CLAUDE.md\n\n## Agent Usage (Mandatory)\n\n## Toolchain\n\nBuild.\n",
            encoding="utf-8",
        )
        self.assert_failure_mentions("'## Agent Usage (Mandatory)' chapter is empty")

    def test_a_heading_only_inside_a_code_fence_fails(self):
        chapters = "\n\n".join(
            f"{t}\n\nDoctrine." for t in doctor.REQUIRED_CHAPTERS[1:]
        )
        (self.root / "CLAUDE.md").write_text(
            "# CLAUDE.md\n\n```markdown\n## Agent Usage (Mandatory)\n```\n\n"
            f"{chapters}\n\n## Toolchain\n\nBuild.\n",
            encoding="utf-8",
        )
        self.assert_failure_mentions("no '## Agent Usage (Mandatory)' chapter")

    def test_a_duplicated_chapter_fails(self):
        chapters = "\n\n".join(f"{t}\n\nDoctrine." for t in doctor.REQUIRED_CHAPTERS)
        (self.root / "CLAUDE.md").write_text(
            f"# CLAUDE.md\n\n{chapters}\n\n## Agent Usage (Mandatory)\n\nStale copy.\n",
            encoding="utf-8",
        )
        self.assert_failure_mentions("'## Agent Usage (Mandatory)' chapters — keep one")


class HarnessStamp(DoctorCase):
    STAMP = f"<!-- harness: {STAMP_DATE} -->"

    def test_a_missing_stamp_fails(self):
        self.edit("CLAUDE.md", self.STAMP + "\n", "")
        self.assert_failure_mentions("has no '<!-- harness: <YYYY-MM-DD> -->' stamp")

    def test_a_malformed_stamp_fails(self):
        self.edit("CLAUDE.md", self.STAMP, "<!-- harness: June 2026 -->")
        self.assert_failure_mentions("harness stamp is malformed")

    def test_a_duplicated_stamp_fails(self):
        self.edit("CLAUDE.md", self.STAMP, f"{self.STAMP}\n{self.STAMP}")
        self.assert_failure_mentions("harness stamps — keep one")

    def test_a_real_date_stamp_passes(self):
        self.edit("CLAUDE.md", self.STAMP, f"<!-- harness: {ANOTHER_REAL_DATE} -->")
        self.assertEqual(self.failures(), [])

    def test_the_retired_semver_token_is_not_a_stamp(self):
        self.edit("CLAUDE.md", self.STAMP, "<!-- harness-version: 0.1.0 -->")
        self.assert_failure_mentions("has no '<!-- harness: <YYYY-MM-DD> -->' stamp")

    def test_a_stampless_crlf_file_reports_crlf_not_a_missing_stamp(self):
        claude_md = self.root / "CLAUDE.md"
        text = claude_md.read_text(encoding="utf-8").replace(self.STAMP + "\n", "")
        claude_md.write_text(text.replace("\n", "\r\n"), encoding="utf-8")
        self.assert_failure_mentions("CRLF line endings")

    def test_a_shaped_but_impossible_date_passes_by_design(self):
        # The check validates shape, not the calendar: the value is machine-written.
        self.edit(
            "CLAUDE.md", self.STAMP, f"<!-- harness: {IMPOSSIBLE_SHAPED_DATE} -->"
        )
        self.assertEqual(self.failures(), [])


class VersionSkew(DoctorCase):
    def version_date(self, date):
        path = self.root / "VERSION-DATE"
        path.write_text(f"{date}\n", encoding="utf-8")
        return path

    def test_a_newer_plugin_warns_and_never_fails(self):
        results = self.results(plugin_version_date=self.version_date(NEWER_PLUGIN_DATE))
        skew = [r for r in results if r.check == "version-skew"]
        self.assertEqual(len(skew), 1)
        self.assertEqual(skew[0].status, doctor.WARN)
        self.assertIn("re-run", skew[0].detail)
        self.assertEqual([r for r in results if r.status == doctor.FAIL], [])

    def test_matching_dates_pass(self):
        results = self.results(plugin_version_date=self.version_date(STAMP_DATE))
        skew = [r for r in results if r.check == "version-skew"]
        self.assertEqual(skew[0].status, doctor.PASS)

    def test_an_unreadable_version_date_skips(self):
        results = self.results(plugin_version_date=self.root / "absent")
        skew = [r for r in results if r.check == "version-skew"]
        self.assertEqual(skew[0].status, doctor.SKIP)

    def test_no_row_appears_without_the_flag_off_marketplace(self):
        self.assertEqual(self.rows("version-skew"), [])


class ChannelInvariants(DoctorCase):
    def test_a_marketplace_tree_without_git_skips_or_passes(self):
        # A fresh root: the copy fixture leaves reviewer bodies on disk, which
        # the marketplace presence check flags.
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        materialize(root, HarnessTable(channel="marketplace"))
        channel = [r for r in doctor.run(root, MANIFEST) if r.check == "channel"]
        self.assertEqual(len(channel), 1)
        self.assertIn(channel[0].status, (doctor.SKIP, doctor.PASS))

    def test_runtime_on_disk_on_marketplace_fails_before_git_state(self):
        materialize(self.root, HarnessTable(channel="marketplace"))
        skill = self.root / ".claude/skills/sample/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: sample\n---\n", encoding="utf-8")
        self.assert_failure_mentions("load twice")

    def test_tracked_runtime_on_manifest_fails(self):
        materialize(self.root, HarnessTable(channel="manifest"))
        skill = self.root / ".claude/skills/sample/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: sample\n---\n", encoding="utf-8")
        self.git_add_all()
        self.assert_failure_mentions("harness runtime file(s) tracked")

    def test_a_tracked_declared_extension_on_manifest_passes(self):
        materialize(
            self.root,
            HarnessTable(channel="manifest", extensions=(SOME_EXTENSION_SKILL,)),
            write_bodies=False,
        )
        # The manifest channel gitignores the runtime; clear what the copy
        # fixture wrote.
        for surface in (".claude/agents", ".github/agents", ".opencode/agents"):
            shutil.rmtree(self.root / surface, ignore_errors=True)
        extension = self.root / SOME_EXTENSION_SKILL / "SKILL.md"
        extension.parent.mkdir(parents=True)
        extension.write_text("---\nname: pricing-refresh\n---\n", encoding="utf-8")
        self.git_add_all()
        channel = self.rows("channel")
        self.assertEqual(len(channel), 1)
        self.assertEqual(channel[0].status, doctor.PASS, channel[0].detail)
        self.assertIn("declared extension", channel[0].detail)

    def test_a_declared_extension_does_not_excuse_other_tracked_runtime(self):
        materialize(
            self.root,
            HarnessTable(channel="manifest", extensions=(SOME_EXTENSION_SKILL,)),
        )
        (self.root / SOME_EXTENSION_SKILL).mkdir(parents=True)
        (self.root / SOME_EXTENSION_SKILL / "SKILL.md").write_text(
            "---\nname: pricing-refresh\n---\n", encoding="utf-8"
        )
        stray = self.root / A_HARNESS_SKILL / "SKILL.md"
        stray.parent.mkdir(parents=True)
        stray.write_text("---\nname: tdd-workflow\n---\n", encoding="utf-8")
        self.git_add_all()
        self.assert_failure_mentions("harness runtime file(s) tracked")


class MarketplaceTree(DoctorCase):
    HARNESS = HarnessTable(channel="marketplace")

    def test_a_clean_tree_passes_the_channel_check(self):
        self.assertNotIn(doctor.FAIL, set(self.statuses("channel")))

    def test_runtime_on_disk_beside_the_plugin_fails(self):
        stale = self.root / A_HARNESS_SKILL
        stale.mkdir(parents=True)
        (stale / "SKILL.md").write_text("# stale copy\n", encoding="utf-8")
        details = [r.detail for r in self.rows("channel") if r.status == doctor.FAIL]
        self.assertTrue(any("load twice" in d for d in details), details)

    def test_a_declared_extension_on_disk_stays_healthy(self):
        materialize(
            self.root,
            HarnessTable(
                channel="marketplace", extensions=(".claude/skills/my-skill/",)
            ),
        )
        extension = self.root / ".claude/skills/my-skill"
        extension.mkdir(parents=True)
        (extension / "SKILL.md").write_text("# mine\n", encoding="utf-8")
        self.assertNotIn(doctor.FAIL, set(self.statuses("channel")))

    def test_a_leftover_hook_matcher_fails(self):
        self.write_settings("settings.json", matcher_for(HOOK))
        details = [
            r.detail for r in self.rows("hook-registration") if r.status == doctor.FAIL
        ]
        self.assertTrue(any("leftover from a channel switch" in d for d in details))

    def test_the_version_skew_absence_is_a_visible_skip(self):
        rows = self.rows("version-skew")
        self.assertEqual([rows[0].status] if rows else [], [doctor.SKIP])
        self.assertIn("--plugin-version-date", rows[0].detail)


class ReviewerRoster(DoctorCase):
    def test_a_missing_floor_body_fails(self):
        (self.root / f".claude/agents/{A_FLOOR_REVIEWER}.md").unlink()
        self.assert_failure_mentions("four-reviewer floor is mandatory")

    def test_a_declared_extra_with_bodies_passes(self):
        materialize(
            self.root,
            HarnessTable(
                extra_reviewers=(EXTRA_REVIEWER,),
                extensions=tuple(reviewer_paths(EXTRA_REVIEWER)),
            ),
        )
        write_reviewer_bodies(self.root, [EXTRA_REVIEWER])
        self.assertEqual(self.failures(), [])

    def test_a_body_reading_the_implementation_plan_fails(self):
        self.edit(
            f".claude/agents/{A_FLOOR_REVIEWER}.md",
            f"# {A_FLOOR_REVIEWER}\n",
            f"# {A_FLOOR_REVIEWER}\nRead the implementation-plan for context.\n",
        )
        self.assert_failure_mentions("fresh-eyes invariant")

    def test_an_extra_without_the_dispatch_stanza_fails(self):
        materialize(
            self.root,
            HarnessTable(
                extra_reviewers=(EXTRA_REVIEWER,),
                extensions=tuple(reviewer_paths(EXTRA_REVIEWER)),
            ),
        )
        write_reviewer_bodies(self.root, [EXTRA_REVIEWER], stanza=False)
        self.assert_failure_mentions("truncation detection is blind")

    def test_an_extra_absent_from_the_extensions_fails(self):
        materialize(self.root, HarnessTable(extra_reviewers=(EXTRA_REVIEWER,)))
        write_reviewer_bodies(self.root, [EXTRA_REVIEWER])
        self.assert_failure_mentions("not in [harness] extensions")

    def test_an_extra_without_a_body_fails(self):
        materialize(
            self.root,
            HarnessTable(
                extra_reviewers=(EXTRA_REVIEWER,),
                extensions=tuple(reviewer_paths(EXTRA_REVIEWER)),
            ),
        )
        self.assert_failure_mentions("extra reviewer body missing")

    def test_a_floor_name_listed_as_an_extra_fails(self):
        materialize(self.root, HarnessTable(extra_reviewers=(A_FLOOR_REVIEWER,)))
        self.assert_failure_mentions("is a floor reviewer and must not be listed")

    def test_a_body_in_an_undeclared_surface_fails_the_drift_scan(self):
        materialize(self.root, HarnessTable(tools=("claude",)))
        unlisted = self.root / ".github/agents/unlisted-reviewer.agent.md"
        unlisted.parent.mkdir(parents=True, exist_ok=True)
        unlisted.write_text("# unlisted\n", encoding="utf-8")
        self.assert_failure_mentions("it will not gate; declare it or remove it")

    def test_an_extra_outside_the_reviewer_name_shape_fails(self):
        materialize(
            self.root,
            HarnessTable(
                extra_reviewers=(MISNAMED_EXTRA,),
                extensions=(f".claude/agents/{MISNAMED_EXTRA}.md",),
            ),
        )
        self.assert_failure_mentions("*-reviewer naming convention")

    def test_an_undeclared_body_in_the_tree_fails(self):
        write_reviewer_bodies(self.root, [UNDECLARED_REVIEWER])
        self.assert_failure_mentions("it will not gate; declare it or remove it")

    def test_marketplace_skips_the_floor_but_fails_a_bodyless_extra(self):
        materialize(
            self.root,
            HarnessTable(channel="marketplace", extra_reviewers=(EXTRA_REVIEWER,)),
        )
        floor = self.rows("reviewer-floor")
        self.assertTrue(floor)
        self.assertTrue(all(r.status == doctor.SKIP for r in floor))
        self.assert_failure_mentions("extras never ship in a plugin")

    def test_no_known_tool_surface_fails_loud_on_every_channel(self):
        materialize(
            self.root,
            HarnessTable(
                channel="marketplace",
                tools=(UNKNOWN_TOOL,),
                extra_reviewers=(EXTRA_REVIEWER,),
            ),
        )
        self.assert_failure_mentions("names no known tool surface")
        materialize(self.root, HarnessTable(channel="copy", tools=()))
        self.assert_failure_mentions("names no known tool surface")

    def test_a_declared_extra_with_a_body_passes_on_marketplace(self):
        materialize(
            self.root,
            HarnessTable(
                channel="marketplace",
                extra_reviewers=(EXTRA_REVIEWER,),
                extensions=tuple(reviewer_paths(EXTRA_REVIEWER)),
            ),
        )
        write_reviewer_bodies(self.root, [EXTRA_REVIEWER])
        roster_failures = [
            r
            for r in self.failures()
            if r.check in ("reviewer-roster", "reviewer-floor")
        ]
        self.assertEqual(roster_failures, [])

    def test_an_undeclared_body_fails_the_drift_scan_on_marketplace(self):
        materialize(self.root, HarnessTable(channel="marketplace"))
        write_reviewer_bodies(self.root, [UNDECLARED_REVIEWER])
        self.assert_failure_mentions("it will not gate; declare it or remove it")

    def test_an_extra_body_on_marketplace_gets_the_fresh_eyes_scan(self):
        materialize(
            self.root,
            HarnessTable(
                channel="marketplace",
                extra_reviewers=(EXTRA_REVIEWER,),
                extensions=tuple(reviewer_paths(EXTRA_REVIEWER)),
            ),
        )
        write_reviewer_bodies(self.root, [EXTRA_REVIEWER])
        body = self.root / f".claude/agents/{EXTRA_REVIEWER}.md"
        body.write_text(
            body.read_text(encoding="utf-8")
            + "\nRead the implementation-plan for context.\n",
            encoding="utf-8",
        )
        self.assert_failure_mentions("fresh-eyes invariant")


class LegacyPluginKeys(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)

    def rows(self):
        return doctor.check_legacy_plugin_keys(self.root)

    def write_settings(self, name, payload):
        (self.root / ".claude").mkdir(parents=True, exist_ok=True)
        (self.root / ".claude" / name).write_text(payload, encoding="utf-8")

    def test_no_settings_file_passes(self):
        self.assertEqual(self.rows()[0].status, doctor.PASS)

    def test_current_keys_pass(self):
        self.write_settings(
            "settings.json",
            '{"enabledPlugins":{"agent-team-spring-boot@agent-team":true}}',
        )
        self.assertEqual(self.rows()[0].status, doctor.PASS)

    def test_a_legacy_enabled_plugin_warns_with_the_migration(self):
        self.write_settings(
            "settings.json",
            '{"enabledPlugins":{"spring-boot-claude@agentic-harness":true}}',
        )
        row = self.rows()[0]
        self.assertEqual(row.status, doctor.WARN)
        self.assertIn("spring-boot-claude@agentic-harness", row.detail)
        self.assertIn("marketplace-setup", row.detail)

    def test_a_legacy_marketplace_entry_in_the_local_layer_warns(self):
        self.write_settings(
            "settings.local.json",
            '{"extraKnownMarketplaces":{"agentic-harness":{}}}',
        )
        row = self.rows()[0]
        self.assertEqual(row.status, doctor.WARN)
        self.assertIn("settings.local.json", row.detail)


if __name__ == "__main__":
    unittest.main(verbosity=2)
