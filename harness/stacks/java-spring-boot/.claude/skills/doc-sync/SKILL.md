---
name: doc-sync
description: >-
  Synchronize documentation with the current codebase. Fix drift between
  docs/prd.md, docs/system-design.md, and actual source code.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/prd.md
  - docs/system-design.md
metadata:
  version: "1.0"
  author: team
---

# Doc Sync

Synchronize `docs/prd.md` and `docs/system-design.md` with the current codebase. Fix drift, add missing items, remove stale references.

## When to Run

- After implementing features or refactoring code
- Before starting a new feature cycle
- Periodically to prevent documentation drift

## Instructions

### Phase 1: Explore Current Codebase

Use the Explore agent to build a complete picture of what is implemented:

1. Read all Java source files under `src/main/java/` -- note every class, record, field, method
2. Read `src/main/resources/application.yml` for configuration properties
3. Read all template files under `src/main/resources/templates/`
4. Read all test files to understand tested behavior
5. Read all ADR files under `docs/adr/`

Capture: class names (exact casing), record fields (exact types), public vs package-private visibility, module dependencies, pipeline step ordering, CLI arguments, configuration properties, template features.

### Phase 2: Diff Against Documentation

Read `docs/prd.md` and `docs/system-design.md`.

Compare the codebase snapshot against both documents. Identify:

**In PRD:**
- Features implemented but not documented (missing requirement IDs)
- Features documented but not implemented (stale requirements)
- Configuration properties that changed, were added, or were removed
- CLI arguments that changed
- Behavioral details that drifted (thresholds, defaults, fallback logic)
- Data files that changed

**In System Design:**
- Class names that changed (case matters)
- Record fields that were added, removed, or retyped
- Module structure changes (new classes, moved classes, visibility changes)
- Pipeline step ordering drift
- Error handling changes
- Contracts-table entries out of sync with source (records or services renamed, added, or removed)

### Phase 3: Update Documents

Apply all fixes. Follow these rules strictly:

**Document boundaries** (per the harness-project API roster; form rules in the `document-writing` skill):
- PRD = *what* the system does. No Java code, class names, method names, annotations, or implementation constructs.
- System design = *how* it is built: contracts (purpose plus source pointer), module structure, pipeline, error handling. Source is authoritative for record and service definitions; never copy them.

**Writing standards** (from the `document-writing` skill):
- No prohibited words: "significant", "arguably", "might", "would help", "should result in"
- No "some", "many", "most" without percentages
- No vague adjectives without data
- 70% of sentences under 20 words, max 30 words
- Acronyms defined on first use
- One idea per sentence

**Preservation rules:**
- Keep existing requirement IDs stable
- Add new IDs at the end of their section
- Never renumber existing IDs (downstream references depend on them)

### Phase 4: Validate

Invoke the `doc-reviewer` agent with this preamble:

> You are a read-only reviewer. Inspect files with Read, Glob, and Grep. Only permitted Bash commands: `./gradlew build`, `./gradlew test`. Do not write code, scripts, or temporary files. Never use system `/tmp`; use `.scratch/tmp/` for any temporary output.

The reviewer validates against the `document-writing` skill's checklist:
1. Structural checks (cross-references, tables, code blocks)
2. Cross-document coherence (requirement IDs, config properties, record fields, tech stack versions, class names)
3. Writing standards (prohibited words, sentence length, acronyms)
4. Document boundaries (PRD has no Java; system-design has no copied source)

### Phase 5: Fix Review Issues

Apply fixes for any `[AUTOFIX]` or `[BLOCKED]` issues the reviewer found. Re-run the reviewer if changes were substantial. Stop when the reviewer returns APPROVED.

## Maintenance Rules

| Change | Documents touched |
|--------|-------------------|
| Adding a feature | PRD: requirement with ID, contracts, acceptance criteria. ADR: only if an architectural decision is involved. system-design.md: summaries, patterns, constants reference. CLAUDE.md: only if build commands or workflow change. |
| Changing a constraint | Source code is authoritative; update the system-design.md reference. Verify the PRD constraint reference still holds. New ADR only for an architectural decision. |
| Fixing a bug | Code first. PRD only if acceptance criteria were wrong. system-design.md only if the implementation pattern changes. ADR only if the fix represents an architectural decision. |

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

**Never drop:** an active requirement's intent, a REQ-ID's resolvability (keep the anchor or the superseded mapping), or an invariant carrying an ADR back-link. After compaction, re-run the doctor and the `doc-reviewer` (Phase 4) to confirm the budget passes and no dangling reference remains.

## Format Migration

A project adopting the narrative format — or upgrading from an older harness — carries `docs/prd.md` and `docs/system-design.md` in the previous structured shape: `### REQ-XX-NNN` headings, `Input`/`Output`/`Constraints` blocks, separate `Types`/`Interfaces` sections, a per-requirement `Status` field. The doctor flags that shape (`doc-budget`, `field-tables`, `req-acceptance`). This is the one-time procedure that converts it. It is the explore-reconcile-rewrite loop above applied to *form*, not drift, so it runs the same Phase 1 exploration, then reshapes.

**Source of truth, in order.** The migrated docs are a current-state projection, so derive them from the most authoritative source first:

1. **Code and tests** — authoritative for what exists and what is verified. Real records, services, and interfaces become the Contracts table, one row each (purpose, source file, the REQ-IDs they implement). Existing tests are executable specifications: use them to ground each requirement's "Done when" bullet — a behavior a test asserts is a behavior the bullet states and a reviewer checks.
2. **The existing prd.md / system-design.md** — authoritative for what code cannot tell you: intent and the Context narrative, requirements not yet built, non-goals, and which requirements are retired. Preserve every REQ-ID and its anchor verbatim; downstream links and handoff records depend on them. Never renumber.
3. **ADRs** — the *why*. Link them with `**ADR:**`; never inline the rationale.

**Procedure.**

1. **Explore** (Phase 1 above): read all source, tests, config, ADRs, and both existing docs.
2. **Reconcile into a requirement set.** For each existing REQ-ID decide *active* (still wanted, whether or not code exists yet) or *superseded* (retired, no longer the contract). Map each active requirement to the behavior that proves it — a test where one exists, otherwise the code path, otherwise "not yet built".
3. **Rewrite prd.md.** Emit a `## Context` narrative from the old intro, carry over `## Goals` / `## Non-Goals`, then write the requirements under `## Requirements` as narrative prose grouped by capability area. Tag each requirement inline `[REQ-XX-NNN]` and give it one "Done when" bullet grounded in its test or behavior. Move every retired ID to `## Superseded` as `REQ-OLD → REQ-NEW` or the withdrawal reason. Lift all mechanism out — flag/exit-code tables, output layouts, file-format schemas go to system-design.md, linked with `**Design:**`. Drop the per-requirement `Status` field; active means present in the narrative.
4. **Rewrite system-design.md.** Emit a `## Overview` narrative, the real `## Package Structure`, a `## Constants` table (name plus source file, never the value), and a `## Contracts` table built from the actual source — one row per contract, never field-by-field. Carry over Dependency Policy, Threat Model, and each imperative guardrail with its ADR back-link.
5. **Validate and loop.** Run the doctor; it must go green (required sections, `doc-budget`, `field-tables`, `req-acceptance`, cross-doc). Then run the `doc-reviewer` (Phase 4). Iterate until both pass.

**Never lose a requirement.** Every REQ-ID present in the pre-migration doc must resolve in the new one — as an active requirement (narrative plus "Done when" bullet) or a `## Superseded` entry. A dropped ID is a dropped contract.

## Output

Report a summary of changes made:
- Lines added/removed/changed per document
- New requirement IDs added
- Stale items removed
- Review result (APPROVED or remaining issues)
