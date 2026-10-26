# The Doctor Is a Project-Side Engine; audit-docs Runs It First

**Status:** Accepted

## Context

Docs validation splits into two engines by design. The doctor runs deterministic, blocking, CI-runnable structural checks against the brief roster. A judgment pass reviews principle form, enforceability, and cross-document coherence, and only advises.

Two faults in how that split surfaced. The doctor skill bundled an executable engine (`brief_doctor.py`, its expectations manifest, and tests) invoked at `.claude/skills/doctor/scripts/`. Under the marketplace channel skills live in a read-only plugin cache, so that path does not resolve; every other skill was pure instructions referencing the project-side engine sliver. The judgment skill was named `brief-review`, precise inside the harness vocabulary but undiscoverable to a user asking to check the docs against a high bar. The earlier `/lint-docs` had been dissolved into the doctor, `brief-review`, and `audit-agents`, leaving no command whose name matched the intent.

## Options Considered

1. **Keep the engine inside the skill and invoke it through `${CLAUDE_PLUGIN_ROOT}`.** Rejected: the variable is Claude-specific; project-relative paths resolve identically for every tool and channel.
2. **Keep two separately named skills, doctor and `brief-review`.** Rejected: a user experiences one task, and the structural pass was easy to forget.
3. **Keep `brief-review` as an alias of the renamed skill.** Rejected: the harness retires names rather than carrying a stale second one, as with `/seed`.
4. **Merge the doctor into the judgment skill as one engine.** Rejected: CI wants the bare model-free script; the deterministic-versus-judgment boundary stays at the mechanism level.

## Decision

**The doctor engine lives project-side in `scripts/`, and `audit-docs` is the one command that runs the doctor first and the judgment review second, reporting both.**

- The engine is `scripts/doctor.py` with `scripts/doctor-expectations.toml`, beside `handoff.py` and `grading.py`. It is stdlib-only, Python 3.11+, and harness-owned, so manifest and marketplace keep it untracked through the runtime paths and the `.gitignore` block.
- The `doctor` skill keeps `SKILL.md` and `templates/`, instructions and brief-scaffolding data, and invokes `python3 scripts/doctor.py check`. It validates roster existence, required sections, data slots, naming conventions, channel invariants, and the reviewer roster.
- `audit-docs` runs the doctor; on a structurally valid brief it adds the judgment pass over each document alone and in combination. It reports the doctor's pass/fail line and the judgment findings together. The structural verdict gates; the judgment findings advise and never judge philosophical direction.
- The doctor stays invocable on its own for CI and for `materialize`'s final validation.

## Consequences

**Positive:**
- Every skill is pure instructions; the plugin-versus-project split is uniform across the runtime.
- The doctor resolves at a project-relative path under every channel and every tool.
- The structural pass cannot be forgotten: it is the first step of the audit.
- Naming is consistent across the `audit-*` skills.

**Negative:**
- The engine's tests reach one level up to read the brief templates, which stay in the skill.
- "Audit" reads gate-like while the judgment half advises; the skill's description states which half gates.
- Two ways exist to run the structural check: the bare script for CI, the one-command audit for people.

## References

- [2026-06-12-docs-as-harness-project-api](2026-06-12-docs-as-harness-project-api.md) — the contract the doctor enforces and the deterministic-versus-judgment split it preserves.
- [2026-06-14-distribution-channels](2026-06-14-distribution-channels.md) — the marketplace cache that forced engines project-side and the untracked-runtime invariant the doctor checks.
- [2026-06-11-materialize](2026-06-11-materialize.md) — runs the doctor as its final validation and orphan-cleans the relocated engine.
- [2026-06-14-layout-declares-the-project](2026-06-14-layout-declares-the-project.md) — the `layout.toml` facts, channel included, the doctor's invariants read.
- [2026-06-13-documentation-standards](2026-06-13-documentation-standards.md) — the bar the judgment pass reviews against.
- [Harness project API](../harness-project-api.md) — the brief contract the doctor's expectations manifest encodes.
