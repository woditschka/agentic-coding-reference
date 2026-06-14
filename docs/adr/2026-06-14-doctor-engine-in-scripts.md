# The Doctor Engine Lives in `scripts/`, Not Inside Its Skill

**Status:** Accepted

## Context

The marketplace channel ships skills to a read-only plugin cache, while engines stay project-owned (see [the marketplace channel](2026-06-14-marketplace-plugin-channel.md)). Auditing every skill for this split surfaced one outlier: the `doctor` skill bundled an executable engine — `brief_doctor.py`, its `brief-expectations.toml` manifest, and tests — invoked by a project-relative path, `.claude/skills/doctor/scripts/brief_doctor.py`.

Under marketplace that path would not resolve. The skill lives in the plugin cache, not the project, so the invocation breaks. Every other skill is pure instructions that reference the project-side engine sliver (`scripts/handoff.py`, `schemas/`). The doctor was the only skill carrying a path-invoked engine.

## Decision

**Relocate the doctor engine to the project-side `scripts/` directory.**

- `brief_doctor.py`, `test_brief_doctor.py`, and `brief-expectations.toml` move from `.claude/skills/doctor/` to `scripts/`, beside `handoff.py` and `score-change.py`.
- The `doctor` skill keeps `SKILL.md` and `templates/` — instructions and brief-scaffolding data. It now invokes `scripts/brief_doctor.py`.
- `RUNTIME_PATHS` and the `.gitignore` runtime block gain the three files. They are harness-owned, so manifest and marketplace keep them untracked.

## Consequences

**Positive:**
- Every skill is now pure instructions; none bundles a path-invoked engine. The plugin-versus-project split is uniform across the runtime.
- The doctor resolves at a project-relative path under every channel and every tool — no Claude-specific `${CLAUDE_PLUGIN_ROOT}`.
- It aligns the doctor with the rule that engines live in `scripts/`, project-side, like `handoff.py` and `score-change.py`.

**Negative:**
- The doctor's tests reach one level up to read the brief templates, which stay in the skill. Acceptable: the templates are scaffolding data the engine never executes.
- A one-time path change: existing copy/manifest consumers see the engine move on their next materialize, orphan-cleaned by `/materialize`.

## Notes

A prerequisite for the marketplace producer-side packaging. The doctor's behaviour is unchanged — only its location and invocation path move.
