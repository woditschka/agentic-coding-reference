# doc-sync — Maintenance Rules, Compaction, Format Migration

The stack-independent half of the `doc-sync` skill. Each stack's `SKILL.md` carries the exploration and review phases and points here; this file carries the procedures a maintenance, compaction, or migration task follows. Stack vocabulary stays in `SKILL.md` — where this file says "the stack's production constructs", the Instructions there name them.

## Maintenance Rules

| Change | Documents touched |
|--------|-------------------|
| Adding a feature | PRD: requirement with ID, contracts, acceptance criteria. ADR: only if an architectural decision is involved. system-design.md: summaries, patterns, constants reference. CLAUDE.md: only if build commands or workflow change. |
| Changing a constraint | Source code is authoritative; update the system-design.md reference. Verify the PRD constraint reference still holds. New ADR only for an architectural decision. |
| Fixing a bug | Code first. PRD only if acceptance criteria were wrong. system-design.md only if the implementation pattern changes. ADR only if the fix represents an architectural decision. |
| Editing a derived brief | Any brief carrying provenance marks (the `derive-briefs` skill's forms). Update the statement and keep its mark. Code contradicting a *confirmed* statement is a defect to record, never drift to sync. A *not recoverable* section stays unrecovered until a human supplies the reasoning. |

## Compaction

`docs/prd.md` and `docs/system-design.md` accumulate across slices. The doctor caps each with a word budget (`doc-budget` check). When a doc approaches or crosses it, compact rather than raise the ceiling. Compaction is a current-state rewrite, not a deletion pass: it removes what source now owns and what is no longer active, never an active requirement's intent.

Run it when the doctor reports `doc-budget`, or proactively before a doc passes ~80% of its budget.

**system-design.md — remove source-owned detail.**
- Replace any field/parameter/key enumeration (table or prose) with a one-line purpose summary plus a source pointer. The `field-tables` check finds the table form; read the Contracts and Constants sections for the prose form.
- Apply the rename self-test (`document-writing` § Abstraction Level) to each paragraph: if renaming a field in source would silently falsify it, delete it or rewrite it as an invariant.
- Collapse a multi-paragraph contract write-up to one Contracts table row.

**prd.md — collapse retired and over-specified entries.**
- Move every superseded requirement to the `## Superseded` list as `REQ-OLD → REQ-NEW` (or the withdrawal reason). Drop its narrative and acceptance bullets; the ID stays resolvable through the mapping.
- Lift any mechanism (flag tables, exit codes, output layouts) out to system-design.md and link with `**Design:**`.
- Tighten each requirement narrative to intent; the bounded contract is the "Done when" bullet, not a re-statement of mechanism.

**Never drop:** an active requirement's intent, a REQ-ID's resolvability (keep the anchor or the superseded mapping), an invariant carrying an ADR back-link, or a provenance mark. After compaction, re-run the doctor and the `doc-reviewer` (SKILL.md Phase 4) to confirm the budget passes and no dangling reference remains.

## Format Migration

A project adopting the narrative format — or upgrading from an older harness — carries `docs/prd.md` and `docs/system-design.md` in the previous structured shape: `### REQ-XX-NNN` headings, `Input`/`Output`/`Constraints` blocks, separate `Types`/`Interfaces` sections, a per-requirement `Status` field. The doctor flags that shape (`doc-budget`, `field-tables`, `req-acceptance`). This is the one-time procedure that converts it. It is the explore-reconcile-rewrite loop applied to *form*, not drift, so it runs the same Phase 1 exploration (SKILL.md), then reshapes.

**Source of truth, in order.** The migrated docs are a current-state projection, so derive them from the most authoritative source first:

1. **Code and tests** — authoritative for what exists and what is verified. The stack's real production constructs (the `SKILL.md` Instructions name them) become the Contracts table, one row each (purpose, source file, the REQ-IDs they implement). Existing tests are executable specifications: use them to ground each requirement's "Done when" bullet — a behavior a test asserts is a behavior the bullet states and a reviewer checks.
2. **The existing prd.md / system-design.md** — authoritative for what code cannot tell you: intent and the Context narrative, requirements not yet built, non-goals, and which requirements are retired. Preserve every REQ-ID and its anchor verbatim; downstream links and handoff records depend on them. Never renumber.
3. **ADRs** — the *why*. Link them with `**ADR:**`; never inline the rationale.

**Procedure.**

1. **Explore** (SKILL.md Phase 1): read all source, tests, config, ADRs, and both existing docs.
2. **Reconcile into a requirement set.** For each existing REQ-ID decide *active* (still wanted, whether or not code exists yet) or *superseded* (retired, no longer the contract). Map each active requirement to the behavior that proves it — a test where one exists, otherwise the code path, otherwise "not yet built".
3. **Rewrite prd.md.** Emit a `## Context` narrative from the old intro, carry over `## Goals` / `## Non-Goals`, then write the requirements under `## Requirements` as narrative prose grouped by capability area. Tag each requirement inline `[REQ-XX-NNN]` and give it one "Done when" bullet grounded in its test or behavior. Move every retired ID to `## Superseded` as `REQ-OLD → REQ-NEW` or the withdrawal reason. Lift all mechanism out — flag/exit-code tables, output layouts, file-format schemas go to system-design.md, linked with `**Design:**`. Drop the per-requirement `Status` field; active means present in the narrative.
4. **Rewrite system-design.md.** Emit a `## Overview` narrative, the real `## Package Structure`, a `## Constants` table (name plus source file, never the value), and a `## Contracts` table built from the actual source — one row per contract, never field-by-field. Carry over Dependency Policy, Threat Model, and each imperative guardrail with its ADR back-link.
5. **Validate and loop.** Run the doctor; it must go green (required sections, `doc-budget`, `field-tables`, `req-acceptance`, cross-doc). Then run the `doc-reviewer` (SKILL.md Phase 4). Iterate until both pass.

**Never lose a requirement.** Every REQ-ID present in the pre-migration doc must resolve in the new one — as an active requirement (narrative plus "Done when" bullet) or a `## Superseded` entry. A dropped ID is a dropped contract. Provenance marks migrate with their statements — a *confirmed* clause is a human's dated answer, not reshapeable prose.
