# Digestible Narrative Docs With an Enforced Budget

**Status:** Accepted

## Context

`docs/prd.md` and `docs/system-design.md` accumulate across slices and grow unbounded. A downstream project reached a PRD of 81,706 words (4,892 lines) and a system-design of 80,956 words (2,995 lines) — each an order of magnitude past what a human reads or an agent parses cheaply. Three forces drove the growth, and the harness countered none of them.

First, no size discipline. The writing standards bound a *sentence* (≤30 words) and the abstraction ladder, but nothing bounded a *document*, and no check measured one. A doc could balloon, or grant itself an exemption, and nothing pushed back.

Second, the system-design doc mirrored source. The standards already say "source is authoritative" and flag `| Field | Type |` tables, but the prose form — naming every field, config key, and parameter in running text — evaded a reviewer scanning for table syntax. The bloated doc's Interfaces section was 2,090 lines of field-by-field prose that falsifies the moment code changes.

Third, the PRD format was heavy and duplicative. Per-requirement `Input` / `Output` / `Constraints` / `Depends On` tables restated the `prd-entry` handoff record and the source signatures, and they are field tables in disguise. Worse, the bloated PRD invented a self-authorizing deviation — prose telling reviewers to *skip* the rationale-prose check — and nothing forbade it.

The rules to prevent all three already existed in the `document-writing` skill. The gap was enforcement and an authoring format that did not invite the bloat.

## Options Considered

1. **Status quo.** Rejected: the rules exist but nothing measures size or catches the prose form, so accumulation continues.
2. **Remediate the one downstream project.** Rejected: a one-off slim does not stop the next project from ballooning.
3. **Tighten authoring prose only.** Rejected: unenforced prose is exactly what already failed.
4. **A measurable gate only.** Rejected: a budget without a digestible format pushes every project to the override; the format is the primary lever, the budget the backstop.
5. **Enforce, prevent, and restructure together** — a deterministic budget, hardened authoring rules, and a narrative format that is digestible by construction.

## Decision

**We adopt option 5 across three layers.**

- **Format — narrative PRD, contract-table system-design.** The PRD is narrative prose annotated inline with `[REQ-XX-NNN]` tags; each requirement carries one "Done when" acceptance bullet that is its bounded, testable contract. The prose is intent, the bullet is the bar the fresh-eyes reviewer judges against. A requirement is active by being in the narrative — no per-requirement `Status` field; retired IDs move to a `## Superseded` mapping. The per-requirement `Input`/`Output`/`Constraints`/`Depends On` scaffolding is retired. system-design names each contract once in a `Contract | Purpose | Source | Implements` table, never field-by-field. PRD-outbound links name their target: `**ADR:**` (the decision) and `**Design:**` (system-design).
- **Enforce — deterministic doctor gates.** A word budget (default PRD 18,000 / system-design 12,000), overridable per project in `layout.toml [harness]` (`prd_max_words`, `system_design_max_words`) — a recorded, reviewable opt-out for genuine scale, never silent drift. A field-table check rejects `| Field | … |` headers in system-design. A req-acceptance check fails any REQ-ID that has no acceptance bullet. The PRD and design docs are identified by the existing `[cross_doc]` roles, so the checks need no per-file flags.
- **Prevent — hardened authoring rules.** `document-writing` and `prd-authoring` rule that prose enumeration is the same violation as a field table, that the PRD carries no mechanism (flag/exit-code tables, output layouts) and no contract scaffolding, and that a document may not grant itself a reviewer-check exemption. The `doc-reviewer` raises these; the budget is a backstop, the per-contract discipline the primary lever.
- **Restructure — compaction.** `doc-sync` gains a Compaction phase: when a doc nears its budget, remove source-owned detail and collapse superseded entries, never an active requirement's intent.

## Consequences

**Positive:**
- A requirement drops from ~10 structured fields to a prose sentence plus one tagged bullet plus two links — more digestible for human and agent, every machine contract intact.
- Accumulation is caught deterministically and cannot be silently ignored; raising a budget is a visible decision in the diff.
- The prose form of source-mirroring is now a named, reviewer-caught violation, not a blind spot.
- IDs, anchors, the `cross_doc` check, and the `prd-entry` schema are unchanged — traceability holds.

**Negative:**
- A migrating project's docs fail the new checks until reworked. Accepted: that is the upgrade surfacing the new contract, the same path every harness expectation takes. The `doc-sync` skill § Format Migration is the remedy — it rebuilds both docs in the new format from code, tests, and the existing docs, preserving every REQ-ID, and loops until the doctor is green.
- The budget defaults are calibration estimates. Accepted: they are a backstop, tunable per project, and the prevention layer carries the real load.
- A narrative requirement's boundary is fuzzier than a structured block. Mitigated: the tagged "Done when" bullet is the bound, the prose is context — a rule stated in `prd-authoring`.

## Implementation

**Requirements:** the doctor engine (`brief_doctor.py`) gains `doc-budget`, `field-tables`, and `req-acceptance` checks; `brief-expectations.toml` carries the budgets; the `prd.md` and `system-design.md` templates, the `prd-authoring`, `document-writing`, `review-checklist`, `audit-docs`, and `doc-sync` skills, and both samples' briefs adopt the format.

## References

- [Append-Only JSONL Handoffs](2026-05-08-append-only-jsonl-handoffs.md) — the `prd-entry` record that carries the slice's machine contract, which the narrative PRD no longer duplicates
- [PRD as Discussion Partner](2026-06-19-prd-discussion-partner.md) — the requirements interview that now produces narrative prose
- [Fresh-Eyes Review Over a Canonical Change Set](2026-06-21-fresh-eyes-review-changeset.md) — the reviewer that judges against `docs/`, why the testable bar must live in the PRD, not the handoff
- [Principles Over Rigid Rules in Harness Prose](2026-06-03-principles-over-rigid-rules.md) — the budget is a backstop with a rationale clause; the per-contract discipline is the lever
