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
    "adr-README.md": "docs/adr/README.md",
}


def materialize(root, channel="copy", spec_version="0.1.0", extensions=None):
    for template, target in TEMPLATE_TARGETS.items():
        text = (TEMPLATES / template).read_text(encoding="utf-8")
        text = text.replace("{{PROJECT_NAME}}", "sample")
        text = text.replace("{{HARNESS_VERSION}}", "0.0.0")
        path = root / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    scripts = root / "scripts"
    scripts.mkdir(exist_ok=True)
    toml = f'[harness]\nchannel = "{channel}"\nspec_version = "{spec_version}"\n'
    if extensions is not None:
        items = ", ".join(f'"{e}"' for e in extensions)
        toml += f"extensions = [{items}]\n"
    (scripts / "layout.toml").write_text(toml, encoding="utf-8")


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
        self.edit("docs/prd.md", "## Out of Scope",
                  "### REQ-AB-999: Sample\n\n## Out of Scope")
        self.edit("docs/system-design.md", "## Threat Model",
                  "Realizes REQ-AB-999.\n\n## Threat Model")
        self.assertEqual(self.failures(), [])

    # -- handbook self-sufficiency -------------------------------------------

    def test_handbook_reference_fails(self):
        self.edit("docs/prd.md", "## Out of Scope",
                  "See agentic-harness.md for the loop model.\n\n## Out of Scope")
        self.assert_failure_mentions("agentic-harness.md")

    def test_handbook_doc_present_in_docs_fails(self):
        # A migration leftover: a harness-owned handbook doc copied into docs/.
        (self.root / "docs/tdd-principles.md").write_text("# stale\n", encoding="utf-8")
        self.assert_failure_mentions("harness-owned handbook doc")

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
                    extensions=[".claude/skills/pricing-refresh"])
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
