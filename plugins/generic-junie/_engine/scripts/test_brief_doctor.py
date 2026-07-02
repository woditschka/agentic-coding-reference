#!/usr/bin/env python3
"""Characterization tests for brief_doctor.py.

The anchor test proves the doctor's own templates pass its own checks: a
freshly materialized project is healthy by construction. The remaining tests
characterize each failure mode.

Run: python3 test_brief_doctor.py
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brief_doctor

# The engine, its manifest, and this test live together in scripts/. The brief
# templates stay in the doctor skill (.claude/skills/doctor/templates), one level
# up from scripts/ — read relative to the project root the test runs from.
MANIFEST = Path(__file__).resolve().parent / "brief-expectations.toml"
TEMPLATES = Path(__file__).resolve().parent.parent / ".claude/skills/doctor/templates"

TEMPLATE_TARGETS = {
    "prd.md": "docs/prd.md",
    "system-design.md": "docs/system-design.md",
    "ubiquitous-language.md": "docs/ubiquitous-language.md",
    "testing-principles.md": "docs/testing-principles.md",
    "architecture-principles.md": "docs/architecture-principles.md",
    "security-principles.md": "docs/security-principles.md",
    "adr-README.md": "docs/adr/README.md",
}

DEFAULT_TOOLS = ("claude", "copilot", "opencode", "junie")
FLOOR_REVIEWERS = ("code-quality-reviewer", "test-reviewer",
                   "security-reviewer", "doc-reviewer")
REVIEWER_TOOL_DIRS = {
    "claude": ".claude/agents/{name}.md",
    "copilot": ".github/agents/{name}.agent.md",
    "opencode": ".opencode/agents/{name}.md",
    "junie": ".junie/agents/{name}.md",
}


def reviewer_paths(name, tools=DEFAULT_TOOLS):
    """The agent-body paths for a reviewer across the given tool surfaces."""
    return [REVIEWER_TOOL_DIRS[t].format(name=name) for t in tools]


def write_reviewer_bodies(root, names, tools=DEFAULT_TOOLS):
    for name in names:
        for rel in reviewer_paths(name, tools):
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {name}\n", encoding="utf-8")


def materialize(root, channel="copy", spec_version="0.1.0", extensions=None,
                tools=DEFAULT_TOOLS, extra_reviewers=None, write_bodies=True):
    for template, target in TEMPLATE_TARGETS.items():
        text = (TEMPLATES / template).read_text(encoding="utf-8")
        text = text.replace("{{PROJECT_NAME}}", "sample")
        text = text.replace("{{HARNESS_DATE}}", "2026-01-01")
        path = root / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    scripts = root / "scripts"
    scripts.mkdir(exist_ok=True)
    toml = f'[harness]\nchannel = "{channel}"\nspec_version = "{spec_version}"\n'
    toml += "tools = [" + ", ".join(f'"{t}"' for t in tools) + "]\n"
    if extensions is not None:
        items = ", ".join(f'"{e}"' for e in extensions)
        toml += f"extensions = [{items}]\n"
    if extra_reviewers is not None:
        items = ", ".join(f'"{r}"' for r in extra_reviewers)
        toml += f"extra_reviewers = [{items}]\n"
    (scripts / "layout.toml").write_text(toml, encoding="utf-8")
    # CLAUDE.md carries each harness-managed chapter, filled, plus the harness date
    # stamp on line 1. The doctor's required-chapter and harness-stamp checks
    # require both on every channel.
    chapters = "\n\n".join(f"{t}\n\nDoctrine." for t in brief_doctor.REQUIRED_CHAPTERS)
    (root / "CLAUDE.md").write_text(
        f"<!-- harness: 2026-01-01 -->\n# CLAUDE.md\n\n{chapters}\n\n## Toolchain\n\nBuild.\n",
        encoding="utf-8")
    # A materialized copy/manifest project carries the floor reviewer bodies in
    # its tree; marketplace ships them in the plugin instead. The channel-only
    # tests opt out via write_bodies=False to keep their git fixtures minimal.
    if write_bodies and channel != "marketplace":
        write_reviewer_bodies(root, FLOOR_REVIEWERS, tools)


class BriefDoctorTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        materialize(self.root)

    def failures(self):
        results = brief_doctor.run(self.root, MANIFEST)
        return [r for r in results if r[0] == brief_doctor.FAIL]

    def assert_failure_mentions(self, fragment):
        failures = self.failures()
        self.assertTrue(
            any(fragment in detail for _, _, detail in failures),
            f"expected a failure mentioning {fragment!r}, got: {failures}",
        )

    def edit(self, target, old, new):
        path = self.root / target
        text = path.read_text(encoding="utf-8")
        assert old in text, f"{old!r} not found in {target}"
        path.write_text(text.replace(old, new), encoding="utf-8")

    # -- the anchor invariant ------------------------------------------------

    def test_fresh_materialized_project_passes(self):
        self.assertEqual(self.failures(), [])

    # -- existence -----------------------------------------------------------

    def test_missing_layout_toml_fails_without_crash(self):
        (self.root / "scripts/layout.toml").unlink()
        self.assert_failure_mentions("scripts/layout.toml missing")

    def test_unparseable_layout_toml_fails_without_crash(self):
        (self.root / "scripts/layout.toml").write_text("[harness\n", encoding="utf-8")
        self.assert_failure_mentions("scripts/layout.toml unparseable")

    def test_missing_roster_file_fails(self):
        (self.root / "docs/testing-principles.md").unlink()
        self.assert_failure_mentions("materialize templates/testing-principles.md")

    def test_missing_adr_readme_fails(self):
        (self.root / "docs/adr/README.md").unlink()
        self.assert_failure_mentions("README.md missing")

    # -- sections and slots --------------------------------------------------

    def test_missing_required_section_fails(self):
        self.edit("docs/system-design.md", "## Threat Model", "## Threats")
        self.assert_failure_mentions("'## Threat Model' missing")

    def test_coverage_without_number_fails(self):
        self.edit("docs/testing-principles.md", "80% line coverage", "high line coverage")
        self.assert_failure_mentions("'Coverage' lacks required data")

    # -- naming conventions --------------------------------------------------

    def test_nonconforming_adr_filename_fails(self):
        (self.root / "docs/adr/notes.md").write_text("# Notes\n", encoding="utf-8")
        self.assert_failure_mentions("notes.md violates entry naming")

    def test_conforming_adr_filename_passes(self):
        (self.root / "docs/adr/2026-01-01-first-decision.md").write_text(
            "# First Decision\n", encoding="utf-8"
        )
        self.assertEqual(self.failures(), [])

    # -- cross-doc -----------------------------------------------------------

    def test_unknown_req_id_in_system_design_fails(self):
        self.edit("docs/system-design.md", "## Threat Model",
                  "Realizes REQ-AB-999.\n\n## Threat Model")
        self.assert_failure_mentions("REQ-AB-999")

    def test_defined_req_id_passes(self):
        # New PRD format: the requirement is narrative prose tagged inline, plus a
        # "Done when" acceptance bullet carrying the same ID (the bounded contract).
        self.edit(
            "docs/prd.md", "## Open Questions",
            "<a id=\"req-ab-999\"></a>\nThe system does a sample thing `[REQ-AB-999]`.\n\n"
            "**Done when:**\n- `[REQ-AB-999]` given input, when run, then output.\n\n"
            "## Open Questions",
        )
        self.edit("docs/system-design.md", "## Threat Model",
                  "Realizes REQ-AB-999.\n\n## Threat Model")
        self.assertEqual(self.failures(), [])

    # -- doc word budgets ----------------------------------------------------

    def test_doc_over_word_budget_fails(self):
        self.edit("docs/system-design.md", "## Overview",
                  "## Overview\n\n" + ("word " * 13000))
        self.assert_failure_mentions("over the 12000-word ceiling")

    def test_doc_budget_override_raises_ceiling(self):
        self.edit("docs/system-design.md", "## Overview",
                  "## Overview\n\n" + ("word " * 13000))
        layout = self.root / "scripts/layout.toml"
        layout.write_text(
            layout.read_text(encoding="utf-8") + "system_design_max_words = 50000\n",
            encoding="utf-8",
        )
        budget = [r for r in brief_doctor.run(self.root, MANIFEST)
                  if r[1] == "doc-budget" and "system-design" in r[2]]
        self.assertTrue(budget and all(r[0] == brief_doctor.PASS for r in budget), budget)
        self.assertIn("override", budget[0][2])

    # -- field tables (system-design) ----------------------------------------

    def test_field_table_in_system_design_fails(self):
        self.edit(
            "docs/system-design.md", "## Contracts",
            "## Contracts\n\n| Field | Type | Description |\n|---|---|---|\n"
            "| id | string | the id |\n",
        )
        self.assert_failure_mentions("field/parameter table")

    def test_field_table_inside_code_fence_passes(self):
        # A field table shown as an illustrative example inside a fenced block is
        # not a live schema mirror, so it is skipped.
        self.edit(
            "docs/system-design.md", "## Contracts",
            "## Contracts\n\n```\n| Field | Type |\n| id | string |\n```\n",
        )
        ft = [r for r in brief_doctor.run(self.root, MANIFEST) if r[1] == "field-tables"]
        self.assertTrue(ft and all(r[0] == brief_doctor.PASS for r in ft), ft)

    # -- requirement acceptance bullets (PRD) --------------------------------

    def test_req_only_in_prose_fails(self):
        self.edit("docs/prd.md", "## Open Questions",
                  "Some narrative names `[REQ-AB-001]` but never bounds it.\n\n## Open Questions")
        self.assert_failure_mentions("mentioned only in prose")

    def test_req_with_acceptance_bullet_passes(self):
        self.edit(
            "docs/prd.md", "## Open Questions",
            "Narrative for `[REQ-AB-001]`.\n\n**Done when:**\n"
            "- `[REQ-AB-001]` given x, when run, then y.\n\n## Open Questions",
        )
        ra = [r for r in brief_doctor.run(self.root, MANIFEST) if r[1] == "req-acceptance"]
        self.assertTrue(ra and all(r[0] == brief_doctor.PASS for r in ra), ra)

    def test_req_in_code_fence_not_flagged(self):
        # A REQ-ID shown only inside a fenced example is illustrative, not a live
        # requirement — it must not be flagged as a prose-only orphan.
        self.edit("docs/prd.md", "## Open Questions",
                  "```\nThe system does X `[REQ-AB-002]`.\n```\n\n## Open Questions")
        ra = [r for r in brief_doctor.run(self.root, MANIFEST) if r[1] == "req-acceptance"]
        self.assertTrue(ra and all(r[0] == brief_doctor.PASS for r in ra), ra)

    # -- handbook self-sufficiency -------------------------------------------

    def test_handbook_reference_fails(self):
        self.edit("docs/prd.md", "## Open Questions",
                  "See agentic-harness.md for the loop model.\n\n## Open Questions")
        self.assert_failure_mentions("agentic-harness.md")

    def test_handbook_doc_present_in_docs_fails(self):
        # A migration leftover: a harness-owned handbook doc copied into docs/.
        (self.root / "docs/tdd-principles.md").write_text("# stale\n", encoding="utf-8")
        self.assert_failure_mentions("harness-owned handbook doc")

    # -- hook registration ---------------------------------------------------

    def _write_hook(self, name="handoff-allow.sh"):
        d = self.root / ".claude/hooks"
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")

    def _write_settings(self, body):
        (self.root / ".claude/settings.json").write_text(body, encoding="utf-8")

    def test_registered_hook_passes(self):
        self._write_hook()
        self._write_settings(
            '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command",'
            '"command":"bash \\"${CLAUDE_PROJECT_DIR}/.claude/hooks/handoff-allow.sh\\""}]}]}}'
        )
        self.assertEqual(self.failures(), [])

    def test_unregistered_hook_fails(self):
        self._write_hook()
        self._write_settings('{"hooks":{"PreToolUse":[]}}')
        self.assert_failure_mentions(
            "handoff-allow.sh present in .claude/hooks/ but not registered")

    def test_hook_without_settings_fails(self):
        self._write_hook()
        self.assert_failure_mentions("no .claude/settings.json to register them")

    def test_substring_hook_name_not_falsely_registered(self):
        # A short hook whose basename is a substring of a longer registered
        # hook's name must still FAIL — the match is a path segment, not a
        # bare substring.
        self._write_hook("allow.sh")
        self._write_hook("handoff-allow.sh")
        self._write_settings(
            '{"hooks":{"PreToolUse":[{"matcher":"Bash","hooks":[{"type":"command",'
            '"command":"bash \\"${CLAUDE_PROJECT_DIR}/.claude/hooks/handoff-allow.sh\\""}]}]}}'
        )
        self.assert_failure_mentions(
            "allow.sh present in .claude/hooks/ but not registered")

    # -- required harness-managed chapters -----------------------------------

    def test_missing_claude_md_fails(self):
        (self.root / "CLAUDE.md").unlink()
        self.assert_failure_mentions("no CLAUDE.md in project root")

    def test_claude_md_without_chapter_fails(self):
        (self.root / "CLAUDE.md").write_text(
            "# CLAUDE.md\n\nNo managed chapter here.\n", encoding="utf-8")
        self.assert_failure_mentions("no '## Agent Usage (Mandatory)' chapter")

    def test_empty_chapter_fails(self):
        (self.root / "CLAUDE.md").write_text(
            "# CLAUDE.md\n\n## Agent Usage (Mandatory)\n\n## Toolchain\n\nBuild.\n",
            encoding="utf-8")
        self.assert_failure_mentions("'## Agent Usage (Mandatory)' chapter is empty")

    def test_heading_only_in_code_fence_fails(self):
        # A managed heading that appears only inside a ```fence``` is illustrative
        # text, not a real chapter — it must not satisfy the check.
        chapters = "\n\n".join(f"{t}\n\nDoctrine." for t in brief_doctor.REQUIRED_CHAPTERS[1:])
        (self.root / "CLAUDE.md").write_text(
            "# CLAUDE.md\n\n```markdown\n## Agent Usage (Mandatory)\n```\n\n"
            f"{chapters}\n\n## Toolchain\n\nBuild.\n", encoding="utf-8")
        self.assert_failure_mentions("no '## Agent Usage (Mandatory)' chapter")

    def test_duplicate_chapter_fails(self):
        # A second copy of a managed heading is a stale duplicate render leaves
        # behind (it refreshes only the first); the doctor must not mask it.
        chapters = "\n\n".join(f"{t}\n\nDoctrine." for t in brief_doctor.REQUIRED_CHAPTERS)
        (self.root / "CLAUDE.md").write_text(
            f"# CLAUDE.md\n\n{chapters}\n\n## Agent Usage (Mandatory)\n\nStale copy.\n",
            encoding="utf-8")
        self.assert_failure_mentions("'## Agent Usage (Mandatory)' chapters — keep one")

    # -- harness date stamp --------------------------------------------------

    def test_missing_harness_stamp_fails(self):
        self.edit("CLAUDE.md", "<!-- harness: 2026-01-01 -->\n", "")
        self.assert_failure_mentions("has no '<!-- harness: <YYYY-MM-DD> -->' stamp")

    def test_malformed_harness_stamp_fails(self):
        self.edit("CLAUDE.md", "<!-- harness: 2026-01-01 -->",
                  "<!-- harness: June 2026 -->")
        self.assert_failure_mentions("harness stamp is malformed")

    def test_duplicate_harness_stamp_fails(self):
        self.edit("CLAUDE.md", "<!-- harness: 2026-01-01 -->",
                  "<!-- harness: 2026-01-01 -->\n<!-- harness: 2026-01-01 -->")
        self.assert_failure_mentions("harness stamps — keep one")

    def test_real_date_stamp_passes(self):
        self.edit("CLAUDE.md", "<!-- harness: 2026-01-01 -->",
                  "<!-- harness: 2026-06-26 -->")
        self.assertEqual(self.failures(), [])

    def test_retired_semver_token_not_accepted(self):
        # The retired `harness-version:` token must not satisfy the date stamp —
        # it guards the regex boundary against the old semver scheme reappearing.
        self.edit("CLAUDE.md", "<!-- harness: 2026-01-01 -->",
                  "<!-- harness-version: 0.1.0 -->")
        self.assert_failure_mentions("has no '<!-- harness: <YYYY-MM-DD> -->' stamp")

    def test_crlf_claude_md_reports_crlf_not_missing_stamp(self):
        # refresh-chapters.sh refuses to stamp a CRLF file, so a stamp-less CRLF
        # CLAUDE.md must point at CRLF, not send the user into a /materialize loop.
        cm = self.root / "CLAUDE.md"
        text = cm.read_text(encoding="utf-8").replace("<!-- harness: 2026-01-01 -->\n", "")
        cm.write_text(text.replace("\n", "\r\n"), encoding="utf-8")
        self.assert_failure_mentions("CRLF line endings")

    def test_shaped_but_invalid_date_passes_by_design(self):
        # The check validates shape, not calendar ranges — the value is machine-
        # written from VERSION-DATE. Pinning this guards the intentional boundary
        # against a well-meaning regex tightening.
        self.edit("CLAUDE.md", "<!-- harness: 2026-01-01 -->",
                  "<!-- harness: 2026-13-99 -->")
        self.assertEqual(self.failures(), [])

    # -- project data --------------------------------------------------------

    def test_missing_harness_table_fails(self):
        (self.root / "scripts/layout.toml").write_text("[test]\n", encoding="utf-8")
        self.assert_failure_mentions("harness.channel missing")

    def test_invalid_channel_fails(self):
        materialize(self.root, channel="floppy")
        self.assert_failure_mentions("channel must be one of")

    def test_spec_version_mismatch_fails(self):
        materialize(self.root, spec_version="9.9.9")
        self.assert_failure_mentions("spec_version 9.9.9")

    # -- channel invariants --------------------------------------------------

    def test_marketplace_without_git_skips(self):
        materialize(self.root, channel="marketplace")
        results = brief_doctor.run(self.root, MANIFEST)
        channel_results = [r for r in results if r[1] == "channel"]
        self.assertEqual(len(channel_results), 1)
        self.assertIn(channel_results[0][0], (brief_doctor.SKIP, brief_doctor.PASS))

    def test_marketplace_with_tracked_runtime_fails(self):
        git = shutil.which("git")
        if git is None:
            self.skipTest("git unavailable")
        materialize(self.root, channel="marketplace")
        skill = self.root / ".claude/skills/sample/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: sample\n---\n", encoding="utf-8")
        env_safe = dict(
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
            PATH="/usr/bin:/bin:/usr/local/bin",
        )
        subprocess.run([git, "init", "-q"], cwd=self.root, check=True, env=env_safe)
        subprocess.run([git, "add", "."], cwd=self.root, check=True, env=env_safe)
        self.assert_failure_mentions("harness runtime file(s) tracked")

    def test_manifest_with_tracked_runtime_fails(self):
        git = shutil.which("git")
        if git is None:
            self.skipTest("git unavailable")
        materialize(self.root, channel="manifest")
        skill = self.root / ".claude/skills/sample/SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("---\nname: sample\n---\n", encoding="utf-8")
        env_safe = dict(
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
            PATH="/usr/bin:/bin:/usr/local/bin",
        )
        subprocess.run([git, "init", "-q"], cwd=self.root, check=True, env=env_safe)
        subprocess.run([git, "add", "."], cwd=self.root, check=True, env=env_safe)
        self.assert_failure_mentions("harness runtime file(s) tracked")

    def _git_add_all(self):
        git = shutil.which("git")
        if git is None:
            self.skipTest("git unavailable")
        env_safe = dict(
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
            PATH="/usr/bin:/bin:/usr/local/bin",
        )
        subprocess.run([git, "init", "-q"], cwd=self.root, check=True, env=env_safe)
        subprocess.run([git, "add", "."], cwd=self.root, check=True, env=env_safe)

    def test_manifest_declared_extension_stays_tracked_passes(self):
        # A tracked file under a declared extension is the project's own work and
        # must not trip the untracked-runtime invariant.
        materialize(self.root, channel="manifest",
                    extensions=[".claude/skills/pricing-refresh"],
                    write_bodies=False)
        # On the manifest channel the runtime (including reviewer bodies) is
        # gitignored; simulate that by clearing what setUp's copy fixture wrote.
        for d in (".claude/agents", ".github/agents",
                  ".opencode/agents", ".junie/agents"):
            shutil.rmtree(self.root / d, ignore_errors=True)
        ext = self.root / ".claude/skills/pricing-refresh/SKILL.md"
        ext.parent.mkdir(parents=True)
        ext.write_text("---\nname: pricing-refresh\n---\n", encoding="utf-8")
        self._git_add_all()
        results = brief_doctor.run(self.root, MANIFEST)
        channel = [r for r in results if r[1] == "channel"]
        self.assertEqual(len(channel), 1)
        self.assertEqual(channel[0][0], brief_doctor.PASS, channel[0][2])
        self.assertIn("declared extension", channel[0][2])

    def test_manifest_extension_does_not_excuse_other_runtime(self):
        # The exclusion is scoped: a tracked harness file outside the declared
        # extension still fails.
        materialize(self.root, channel="manifest",
                    extensions=[".claude/skills/pricing-refresh"])
        (self.root / ".claude/skills/pricing-refresh").mkdir(parents=True)
        (self.root / ".claude/skills/pricing-refresh/SKILL.md").write_text(
            "---\nname: pricing-refresh\n---\n", encoding="utf-8")
        stray = self.root / ".claude/skills/tdd-workflow/SKILL.md"
        stray.parent.mkdir(parents=True)
        stray.write_text("---\nname: tdd-workflow\n---\n", encoding="utf-8")
        self._git_add_all()
        self.assert_failure_mentions("harness runtime file(s) tracked")

    # -- reviewer roster ------------------------------------------------------

    def test_missing_floor_reviewer_fails(self):
        # The four-reviewer floor is mandatory; deleting one fails the doctor.
        (self.root / ".claude/agents/security-reviewer.md").unlink()
        self.assert_failure_mentions("four-reviewer floor is mandatory")

    def test_declared_extra_reviewer_passes(self):
        materialize(self.root, extra_reviewers=["perf-reviewer"],
                    extensions=reviewer_paths("perf-reviewer"))
        write_reviewer_bodies(self.root, ["perf-reviewer"])
        self.assertEqual(self.failures(), [])

    def test_reviewer_reading_working_memory_fails(self):
        # Fresh-eyes invariant: a reviewer body naming the implementer's plan
        # must fail the doctor — even without the `.md` suffix, since the bare
        # slug trips the guard. Reviewers read the change set, not the plan.
        self.edit(
            ".claude/agents/security-reviewer.md",
            "# security-reviewer\n",
            "# security-reviewer\nRead the implementation-plan for context.\n",
        )
        self.assert_failure_mentions("fresh-eyes invariant")

    def test_extra_reviewer_not_in_extensions_fails(self):
        # Declared and present, but absent from extensions: /materialize would
        # prune it on the next upgrade, silently shrinking the roster.
        materialize(self.root, extra_reviewers=["perf-reviewer"])
        write_reviewer_bodies(self.root, ["perf-reviewer"])
        self.assert_failure_mentions("/materialize would prune it")

    def test_extra_reviewer_missing_body_fails(self):
        materialize(self.root, extra_reviewers=["perf-reviewer"],
                    extensions=reviewer_paths("perf-reviewer"))
        self.assert_failure_mentions("extra reviewer body missing")

    def test_floor_name_as_extra_reviewer_fails(self):
        # Re-declaring a floor reviewer in extra_reviewers is a mistake.
        materialize(self.root, extra_reviewers=["doc-reviewer"])
        self.assert_failure_mentions("is a floor reviewer and must not be listed")

    def test_drift_scans_undeclared_surface(self):
        # A *-reviewer body in a surface the project did not declare still must
        # be flagged — it would silently never gate.
        materialize(self.root, tools=("claude",))
        rogue = self.root / ".github/agents/rogue-reviewer.agent.md"
        rogue.parent.mkdir(parents=True, exist_ok=True)
        rogue.write_text("# rogue\n", encoding="utf-8")
        self.assert_failure_mentions("it will not gate; declare it or remove it")

    def test_extra_reviewer_bad_name_fails(self):
        # A declared extra reviewer must follow the *-reviewer convention.
        materialize(self.root, extra_reviewers=["perf"],
                    extensions=[".claude/agents/perf.md"])
        self.assert_failure_mentions("*-reviewer naming convention")

    def test_undeclared_reviewer_in_tree_fails(self):
        # Drift check: a *-reviewer body that is neither floor nor declared
        # would silently never gate.
        write_reviewer_bodies(self.root, ["payment-reviewer"])
        self.assert_failure_mentions("it will not gate; declare it or remove it")

    def test_marketplace_skips_reviewer_roster(self):
        # On marketplace the bodies ship in the plugin, not the tree.
        materialize(self.root, channel="marketplace",
                    extra_reviewers=["perf-reviewer"])
        results = brief_doctor.run(self.root, MANIFEST)
        roster = [r for r in results if r[1] in ("reviewer-roster", "reviewer-floor")]
        self.assertTrue(roster)
        self.assertTrue(all(r[0] == brief_doctor.SKIP for r in roster))


if __name__ == "__main__":
    unittest.main(verbosity=2)
