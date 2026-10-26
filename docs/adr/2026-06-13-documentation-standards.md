# Documentation Standards Ship as Runtime, With a Budget, Provenance, and Stack Fragments

**Status:** Accepted

## Context

The writing standards began as a 520-line root handbook that no project ever installed. A deployed agent saw only the thin `§ Writing Standards` subset inside `doc-review`, a reviewer-named skill the authoring agents reached into. Two copies drifted, aligned only by an audit check, and the fuller standard could not raise agent output because agents never received it.

Three forces then acted on the briefs the standard governs. First, size: a downstream project's `docs/prd.md` reached 81,706 words (4,892 lines) and its `docs/system-design.md` 80,956 words (2,995 lines). The standards bounded a sentence at 30 words but never a document. The design doc mirrored source field by field in prose (2,090 lines of Interfaces), and the PRD's per-requirement tables restated the `prd-entry` record. The PRD had also granted itself an exemption from a reviewer check. Second, brownfield onboarding: `/init` scaffolds four briefs as structure-only stubs, nobody transcribes the code into them, and the pipeline runs its first slice against a PRD with no requirements. A survey that writes observed behavior as settled intent manufactures institutional memory. Third, the stack realization: the core `architecture-principles` template is stack-agnostic by the battery's rule. The Spring realization of the catalog lived only in the Spring sample's prose, enforcers carried tactics of their own, and a downstream sharpening had no path back.

## Options Considered

1. **Keep the handbook, point authors at the reviewer skill.** Rejected: the standard stays uninstalled and the author-reviewer coupling stays backwards.
2. **Keep the handbook, enrich the skill toward it.** Rejected: two substantive copies drift.
3. **Move the full standard into one skill and delete the handbook.** Chosen.
4. **Remediate the one bloated project, or tighten authoring prose only, or a budget gate only.** Rejected in turn: a one-off slim does not stop the next project. Unenforced prose is what failed. A budget without a digestible format pushes every project to the override.
5. **Enforce, prevent, and restructure together.** Chosen: a deterministic budget, hardened authoring rules, and a narrative format digestible by construction.
6. **Leave brownfield onboarding to the owner.** Rejected: empty stubs are the largest adoption cost, where a project's history is richest.
7. **Fold derivation into `/materialize`.** Rejected: materialize is a deterministic runtime replacement that never writes project-owned content.
8. **Survey into a side artifact, promoting statements once ratified.** Rejected: the briefs stay empty until a human works a parallel document, the transcription nobody does today.
9. **A survey skill whose every statement carries its provenance.** Chosen.
10. **The realization in the sample's prose, in the core template in neutral words, or in a stack overlay replacing the whole template.** Rejected in turn: the sample drifts unnoticed. Neutral words carry Spring-shaped reasoning into Go. An overlay duplicates the catalog.
11. **A stack fragment that fills one section of the core template.** Chosen.

## Decision

**The documentation standard is the `document-writing` skill, installed in every project: every author follows it and the `doc-reviewer` enforces it. The briefs it governs are bounded by the doctor, derived with provenance on brownfield projects, and realized per stack through a fragment.**

- **One skill, two consumers.** `core/.claude/skills/document-writing/documentation-standards.md` carries the language-agnostic standard: the five-document architecture, the cross-document map, ownership boundaries, cross-reference and maintenance rules. `SKILL.md` carries the agent obligations and the author checklist; `stacks/<stack>/.../review-checks.md` carries the stack review checklist. Each document's own boundary lives in the skill that governs it (`prd-authoring`, `adr-template`); one home per fact. Prose describes the current state, and unusual inputs are named by their shape.
- **Format.** The PRD is narrative prose annotated inline with `[REQ-XX-NNN]` tags. Each requirement carries one "Done when" bullet that is its testable contract, and retired IDs move to a `## Superseded` mapping. The system-design doc names each contract once in a `Contract | Purpose | Source | Implements` table, never field by field. Prose enumeration is the same violation as a field table. The PRD carries no mechanism and no contract scaffolding, and no document grants itself a reviewer-check exemption.
- **Budget.** The doctor gates a word budget, default PRD 18,000 and system-design 12,000, overridable per project in `layout.toml [harness]` (`prd_max_words`, `system_design_max_words`) as a recorded opt-out. A `field-tables` check rejects `| Field | … |` headers in the design doc; a `req-acceptance` check fails any REQ-ID without an acceptance bullet. `doc-sync` carries a Compaction phase and a Format Migration that rebuilds both docs preserving every REQ-ID.
- **Provenance.** `derive-briefs` drafts the briefs from an existing codebase, docs-only, marking every statement *derived*, *confirmed* (with the date), or *not recoverable*. Observed behavior is not an intended requirement; the PRD's Goals and Non-Goals and each ADR's Context and Options Considered are named as unrecoverable from code. A defect, a gap against a principle brief, and an open question stay three findings; a defect becomes a later slice. The filled principles briefs are derived against, every edit a consented diff. `design-validation`'s foundational check treats a brief carrying only derived marks as still unanswered.
- **Stack fragments.** The core `architecture-principles` and `security-principles` templates carry a `## Language Realization` slot, not doctor-required. A stack ships `<brief>.realization.md` beside its doctor templates; `init.py` writes it into the slot and fails loudly when the slot is missing. `/materialize` diffs an existing brief against template plus fragment and proposes the delta as a consented edit. The Spring fragment maps each building block to the stereotype marking its bean role or to a plain class, and places internals in role-named sub-packages behind the Modulith verify test. No enforcer states a tactic. The battery holds every enforcer line naming a building block or framework annotation without citing the brief to `harness/enforcer-tactics.expected`. It also pins each stack sample's section to its fragment verbatim.

## Consequences

**Positive:**
- The full standard ships into every project, one source, read by authors and reviewer alike.
- A requirement drops from about ten structured fields to a sentence, one tagged bullet, and two links; accumulation is caught deterministically, and raising a budget is a visible diff.
- Brownfield adoption gains a first draft whose unrecoverable reasoning stays visibly unrecovered. The spring-petclinic trial recovered 16 requirements, 25 contracts, seven domain terms, and seven ADRs, and exposed an unnamed MySQL constraint no test observes.
- A stack's style ships as a default, reaches new projects at init and existing ones on upgrade, and stays open to the project's edit.

**Negative:**
- The standard loads about 330 lines into agent context whenever the skill is invoked, and is less prominent as a human document.
- A migrating project's docs fail the new checks until reworked; the budget defaults are calibration estimates.
- Provenance marking is judgment-enforced, and a derived `system-design.md` gates new code from the moment it lands.
- The marketplace channel has no `/materialize`, so its fragment upgrade is a human reading a diff. `/harvest` compares only each brief's `## Language Realization` section against the stack's fragment; an improvement elsewhere in a brief stays project-owned with no path back. The pin is a vocabulary match; a tactic phrased without the catalog's words passes it.
- The Go and generic samples carry an empty realization slot; a Go fragment arrives with a Go preference, never as a placeholder.

## Implementation

`harness/core/.claude/skills/document-writing/`, `derive-briefs/`, `doc-sync/`, and `prd-authoring/`; the doctor engine's `doc-budget`, `field-tables`, and `req-acceptance` checks with `doctor-expectations.toml` (`budget_override_key` per budgeted file); `harness/init.py` and `verify_harness/checks/sync.py`; `harness/stacks/java-spring-boot/.claude/skills/doctor/templates/architecture-principles.realization.md`; `harness/enforcer-tactics.expected`.

## References

- [Docs as the Harness–Project API](2026-06-12-docs-as-harness-project-api.md) — the project-owned roster the standard governs, the budget bounds, and the survey fills
- [Principles Over Rigid Rules](2026-06-03-principles-over-rigid-rules.md) — the budget is a backstop with a rationale clause; the per-contract discipline is the lever
- [The Handoff Ledger](2026-05-08-the-handoff-ledger.md) — the `prd-entry` record that carries the slice's machine contract, which the narrative PRD no longer duplicates
- [The Product Expert and the Root Conversation](2026-06-19-the-product-expert-and-the-root-conversation.md) — the requirements interview that produces the narrative prose
- [Fresh-Eyes Review Over a Canonical Change Set](2026-06-21-fresh-eyes-review-changeset.md) — the reviewer that judges against `docs/`, why the testable bar lives in the PRD
- [Materialize](2026-06-11-materialize.md) — the deterministic upgrade that derivation stays outside of and whose diff-check reads the fragment
- [The Doctor](2026-06-14-the-doctor.md) — the structural gate and the docs audit the survey draft is handed to
- [DDD Open-Closed](2026-06-26-ddd-open-closed.md) — the single adaptation surface the fragment fills; its judgment guard gains a mechanical half here
- [Test Conventions at Write Time](2026-09-03-test-conventions-at-write-time.md) — the decision that added the current-state and input-shape rules to the standard
- [`../ddd-principles.md`](../ddd-principles.md) — the kernel/tactical taxonomy the fragment sits under
