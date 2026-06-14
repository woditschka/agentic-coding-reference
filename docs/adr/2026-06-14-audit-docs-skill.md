# The Docs Audit Is One Command: `brief-review` Becomes `audit-docs` and Runs the Doctor

**Status:** Accepted

## Context

The harness splits docs validation into two engines by design ([docs-as-API](2026-06-12-docs-as-harness-project-api.md)): the `doctor` skill runs deterministic, blocking, CI-runnable structural checks, and the `brief-review` skill runs the advisory judgment pass — principle form, enforceability, cross-document coherence. The split is correct; its surfacing was not.

Two problems compounded:

1. **`brief-review` was undiscoverable.** The name is precise inside the harness's vocabulary: the `docs/` roster *is* the project's "brief." But nobody asking "check my docs against a high bar, individually and against each other" thinks the word "brief." Users reached for a docs audit and did not find it.
2. **The old `/lint-docs` was dissolved** into the doctor, `brief-review`, and `audit-agents`, removing the one obvious entry point and leaving no command whose name matched the intent. The result: two separately-named skills, neither resonant, for what a user experiences as one task.

## Decision

**Rename `brief-review` → `audit-docs`, and make the renamed skill run the full audit: the doctor first, then the judgment review, reporting both.**

- **The name matches the intent and the family.** `audit-docs` says what it does and sits beside the existing `audit-agents` and (root) `audit-consistency` skills.
- **One command, two passes.** `audit-docs` runs the doctor (structural, deterministic) first; on a structurally-valid brief it adds the judgment pass (each document individually, and in combination). It reports the doctor's pass/fail line and the judgment findings together.
- **The engines stay separate underneath.** The doctor remains a standalone, model-free script — still the blocking gate, still CI-runnable on its own. `audit-docs` is the human-facing orchestrator over it, not a replacement. The deterministic-vs-judgment boundary the docs-as-API ADR established is preserved at the mechanism level.
- **No alias is kept.** `brief-review` is gone, not aliased — consistent with retiring `/seed` rather than carrying a stale second name. ADRs and the README Project History keep the old name as historical record.

## Consequences

**Positive:**
- A single resonant command audits the docs the way users describe the task — individually and against each other.
- The structural pass can no longer be forgotten: it is the first step of the audit, not a separate command a user must remember to run first.
- Naming is consistent across the `audit-*` skills.

**Negative:**
- "Audit" reads slightly gate-like, while the judgment half is advisory. Mitigated in the skill's description and prose: the doctor gates, the judgment pass advises.
- The doctor is still invocable on its own (for CI), so there are two ways to run the structural check. Acceptable: CI wants the bare deterministic script; humans want the one-command audit.
- The rename touched `harness/core`, the stack agent rosters, both samples (re-materialized), and the root docs. ADRs keep the old name, so historical references stay accurate.

## Notes

Renames the judgment skill introduced in [docs-as-API](2026-06-12-docs-as-harness-project-api.md) and referenced by [complete-replacement materialize](2026-06-13-materialize-complete-replacement.md). Those records stand as written; this ADR changes the skill's name and folds the doctor run into it.
