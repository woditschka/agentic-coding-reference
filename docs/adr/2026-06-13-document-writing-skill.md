# The document-writing Skill: Documentation Standards Ship as Runtime, Not Handbook

**Status:** Accepted

## Context

Two problems sat together. First, `doc-review` was a reviewer-named skill living in `stacks/`, yet authoring agents (PRE, system-design-expert, adr-template) referenced it for the writing standards they had to *follow* — authors reaching into the reviewer's rulebook. Second, the writing standards existed twice: as the root handbook `documentation-standards.md` and as the skill's `§ Writing Standards`, kept aligned only by an audit check.

The deeper issue: `documentation-standards.md` was the richer, 520-line artifact — the five-document architecture, ownership boundaries, cross-reference and maintenance rules, worked examples — but it was **root-only handbook, never installed**. A deployed agent only ever saw the thin operational subset. The fuller standard could not raise the bar on agent output because agents never received it.

## Options Considered

1. **Keep the handbook, point authors at the reviewer skill** — status quo wiring; the standard stays uninstalled and the author↔reviewer coupling stays backwards.
2. **Keep the handbook, enrich the skill toward it** — agents get more, but two substantive copies now drift.
3. **Move the full standard into one skill and delete the handbook** — single source, installed everywhere; the handbook stops existing as a separate document.

## Decision

Option 3.

- Rename `doc-review` → **`document-writing`**: one skill, two consumers. Every author **follows** it; the `doc-reviewer` **enforces** it. The `doc-reviewer` agent and its `author` enum are unchanged.
- The skill spans both layers, merged at materialize: `core/.../document-writing/` carries the language-agnostic standard in `documentation-standards.md` (the rules) plus `SKILL.md` (the agent obligations and author validation checklist); `stacks/<stack>/.../document-writing/review-checks.md` carries the stack-specific review checklist (prohibited-pattern rows, path-coherence checks, the review process).
- The root `documentation-standards.md` handbook is deleted; its content moves into the skill — shipped as the skill's own `documentation-standards.md` companion, neutralized for the stack-agnostic core, with `SKILL.md` as the operational entry that follows the same `SKILL.md` + named-companion shape as `tdd-workflow`. Every reference repoints to the committed skill source.
- Ownership detail follows its own rule — one home per fact. Each document's boundary lives in the skill that governs it (`prd-authoring`, `adr-template`); `document-writing` keeps the cross-document **map** and the CLAUDE.md and system-design boundaries that no other skill owns.

## Consequences

**Positive:**
- The full standard ships into every project; agents author against the architecture, ownership, and cross-reference rules they never had before.
- One source for the writing standards — the handbook↔skill duplication is gone.
- Authors and the reviewer read the same rulebook; the backwards coupling is resolved.
- The universal standard de-duplicates across stacks (one core copy, not two).

**Negative:**
- The standard is less prominent as a *human* document — it lives in a skill path, surfaced via README links rather than a top-level handbook.
- The standard is large (~330 lines in `documentation-standards.md`); it loads into agent context whenever the skill is invoked.
- The skill restates concerns the governing skills own; the ownership-as-map split contains the overlap, and the audit guards drift.

## References

- [Project History](../../README.md#project-history) — the what/when timeline
- [`2026-06-12-docs-as-harness-project-api.md`](2026-06-12-docs-as-harness-project-api.md) — listed `documentation-standards.md` among harness-owned handbook docs; this ADR collapses it into the runtime skill
- [`2026-06-03-principles-over-rigid-rules.md`](2026-06-03-principles-over-rigid-rules.md) — its writing-standard reconciliation now points at the skill
