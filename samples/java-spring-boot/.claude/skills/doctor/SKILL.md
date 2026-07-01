---
name: doctor
description: >-
  Deterministic, blocking validation of the project's docs/ brief against the
  harness-project API: roster existence, required sections, data slots, naming
  conventions, channel invariants, and the reviewer roster. Load when onboarding
  a project, after a harness upgrade, or before starting pipeline work.
  Model-free, CI-runnable.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
metadata:
  version: "1.0"
  author: team
---

## What the doctor is

The harness reads the project's `docs/` folder as its brief. The doctor is the blocking validator of that contract: a deterministic stdlib script, no model involved, same verdict in CI as in a session. It checks the machine-checkable subset of the harness-project API. Judgment checks (rationale quality, contradictions, enforceability) belong to the `audit-docs` skill, not here.

## Layout

The doctor's engine, manifest, and tests live in the project-side `scripts/` directory, beside `handoff.py` and `score-change.py`; this skill holds the instructions and the brief templates. Keeping the engine in `scripts/` means it resolves at a project-relative path under every channel. That includes marketplace, where the skill itself ships in the plugin cache.

| File | Role |
|------|------|
| `scripts/brief_doctor.py` | The engine. Stdlib only, Python 3.11+. Project-side, like every harness engine. |
| `scripts/brief-expectations.toml` | The manifest: roster, required sections, slots, patterns. Harness-owned; consumers never edit it. |
| `scripts/test_brief_doctor.py` | Characterization tests. Also prove a freshly materialized project passes. |
| `templates/` | One template per roster file (in this skill). Defaults are complete house-style documents; stubs are structure-only. |

## Running

```bash
python3 scripts/brief_doctor.py check
python3 scripts/brief_doctor.py check --project-root /path/to/project --json
```

Exit 0: all checks pass. Exit 1: at least one failure, each printed as `FAIL <check>: <detail>`. Exit 2: doctor misconfiguration (bad manifest path, unparseable manifest).

## What it checks

1. **Project data** — `scripts/layout.toml` declares a `[harness]` table with `channel` (`copy`, `manifest`, or `marketplace`) and a `spec_version` matching the manifest.
2. **Roster existence** — all seven brief files exist.
3. **Required sections** — exact `##` headings per the manifest.
4. **Slots** — required data inside sections (numeric pyramid ratios, numeric coverage target).
5. **ADR conventions** — `docs/adr/README.md` exists; entries match `YYYY-MM-DD-kebab.md`.
6. **Cross-doc** — every REQ-ID cited in `docs/system-design.md` is defined in `docs/prd.md`.
7. **Doc word budgets** — `docs/prd.md` and `docs/system-design.md` stay under a word ceiling (default 18000 / 12000), overridable per project in `scripts/layout.toml` `[harness]` (`prd_max_words`, `system_design_max_words`). Words, not lines: under the no-hard-wrap writing standard a paragraph is one line, so a line count is blind to prose bloat. A project with genuine scale raises the ceiling deliberately — a recorded, reviewable edit, never silent drift. The ceiling is a backstop; the per-contract discipline in `document-writing` is the primary lever.
8. **Field tables** — `docs/system-design.md` carries no field/parameter table headers. Source is authoritative for field lists; a table that mirrors a struct rots when the code changes (the prose form of the same violation is the `doc-reviewer`'s catch, not the doctor's).
9. **Requirement acceptance** — every REQ-ID in `docs/prd.md` appears in at least one Markdown list item. The PRD is narrative prose tagged inline with `[REQ-XX-NNN]`; the bounded, testable contract is the requirement's "Done when" acceptance bullet. A requirement that lives only in prose has no bar for the fresh-eyes reviewer to judge against.
10. **Handbook references** — no roster file references a harness-owned document; the brief stays self-sufficient.
11. **Channel invariants** — on the marketplace channel, no harness runtime files are tracked by git.
12. **Reviewer roster** — the four-reviewer floor (code-quality, test, security, doc) has an agent body in every declared tool surface, and each `extra_reviewers` entry in `[harness]` is named `*-reviewer`, present in every surface, and listed in `extensions`. Skipped on the marketplace channel, where the bodies ship in the plugin.
13. **Hook registration** — every hook script in `.claude/hooks/` is referenced in `.claude/settings.json` (or `settings.local.json`). A delivered-but-unregistered hook never runs. This catches the upgrade gap: hook scripts are harness-owned runtime that materialize replaces. Its settings refresh wires each delivered hook the template registers (a `PreToolUse` matcher) deterministically on upgrade, so a freshly materialized project passes; the check still guards one not yet re-materialized, or a `settings.json` a human de-registered. Skipped when `.claude/hooks/` is absent — as on the marketplace channel, where hooks ship in the plugin.
14. **Managed chapters** — `CLAUDE.md` carries each harness-managed chapter (`## Agent Usage (Mandatory)`, `## Memory`, `## Writing Standards`, `## Scratch Directory`, `## Documentation Updates`), present once and non-empty. These are stack-agnostic doctrine refreshed on every materialize; a missing or empty one is a legacy file the `/materialize` migration has not converted.
15. **Harness stamp** — `CLAUDE.md` carries a single, well-formed `<!-- harness: YYYY-MM-DD -->` stamp (the harness release date) on line 1. Present in every session's context, it lets downstream analysis attribute a session to the harness that produced it. Fails if the stamp is missing, duplicated, or malformed.

## Remedies

- **Missing file** — offer to materialize the matching template: fill `{{PROJECT_NAME}}` and `{{HARNESS_DATE}}`, keep the provenance first line. Materializing is the only remedy for absence — never an invisible fallback.
- **Existing file fails** — report the finding and route the fix to the file's owning agent as a consented diff. The doctor never edits a roster file, and re-materializing over an existing file is forbidden (channel rule).
- **New failures after a harness upgrade** — that is the upgrade surfacing new expectations. Pair each finding with the shipped default and an offer to draft the project's own stance.
- **`doc-budget` / `field-tables` / `req-acceptance` failures on an upgraded project** — the docs predate the narrative format. Run the `doc-sync` skill § Format Migration: it rebuilds `prd.md` and `system-design.md` in the current format from code, tests, and the existing docs, preserving every REQ-ID, then loops until the doctor is green.
