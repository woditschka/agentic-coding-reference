---
name: doctor
description: >-
  Deterministic, blocking validation of the project's docs/ brief against the
  harness-project API: roster existence, required sections, data slots, naming
  conventions, and channel invariants. Load when onboarding a project, after a
  harness upgrade, or before starting pipeline work. Model-free, CI-runnable.
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

The harness reads the project's `docs/` folder as its brief. The doctor is the
blocking validator of that contract: a deterministic stdlib script, no model
involved, same verdict in CI as in a session. It checks the machine-checkable
subset of the harness-project API. Judgment checks (rationale quality,
contradictions, enforceability) belong to the `audit-docs` skill, not here.

## Layout

The doctor's engine, manifest, and tests live in the project-side `scripts/`
directory, beside `handoff.py` and `score-change.py`; this skill holds the
instructions and the brief templates. Keeping the engine in `scripts/` means it
resolves at a project-relative path under every channel. That includes
marketplace, where the skill itself ships in the plugin cache.

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

Exit 0: all checks pass. Exit 1: at least one failure, each printed as
`FAIL <check>: <detail>`. Exit 2: doctor misconfiguration (bad manifest path,
unparseable manifest).

## What it checks

1. **Project data** — `scripts/layout.toml` declares a `[harness]` table with
   `channel` (`copy`, `manifest`, or `marketplace`) and a `spec_version` matching the manifest.
2. **Roster existence** — all six brief files exist.
3. **Required sections** — exact `##` headings per the manifest.
4. **Slots** — required data inside sections (numeric pyramid ratios, numeric
   coverage target).
5. **ADR conventions** — `docs/adr/README.md` exists; entries match
   `YYYY-MM-DD-kebab.md`.
6. **Cross-doc** — every REQ-ID cited in `docs/system-design.md` is defined in
   `docs/prd.md`.
7. **Handbook references** — no roster file references a harness-owned
   document; the brief stays self-sufficient.
8. **Channel invariants** — on the marketplace channel, no harness runtime
   files are tracked by git.

## Remedies

- **Missing file** — offer to materialize the matching template: fill
  `{{PROJECT_NAME}}` and `{{HARNESS_VERSION}}`, keep the provenance first line.
  Materializing is the only remedy for absence — never an invisible fallback.
- **Existing file fails** — report the finding and route the fix to the file's
  owning agent as a consented diff. The doctor never edits a roster file, and
  re-materializing over an existing file is forbidden (channel rule).
- **New failures after a harness upgrade** — that is the upgrade surfacing new
  expectations. Pair each finding with the shipped default and an offer to
  draft the project's own stance.
