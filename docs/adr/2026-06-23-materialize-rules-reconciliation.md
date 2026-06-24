# Materialize Proposes Skeleton Improvements to a Project's CLAUDE.md

**Status:** Superseded by [Harness Doctrine Lives in Managed Chapters of CLAUDE.md](2026-06-24-claude-md-managed-chapters.md)

> **Superseded (2026-06-24).** The advisory reconciliation pass managed the friction with a polite per-upgrade prompt; it did not remove it. Every future improvement to the orchestrator rules re-triggered the proposal. The successor ADR moves the doctrine into harness-managed chapters inside `CLAUDE.md` — each identified by its `## ` heading, refreshed in place automatically on every materialize, no prompt, identical across all four tools. Step 9 is demoted from a recurring reconciliation to a one-time legacy-CLAUDE.md conversion. The analysis below remains valid; only the chosen option (4) is replaced.

## Context

`CLAUDE.md` is project-owned. `/init` scaffolds it once from `harness/init/stacks/<stack>/CLAUDE.md` and never overwrites an existing file; `/materialize` replaces the runtime and leaves project-owned files untouched. [Materialize Is a Complete Replacement](2026-06-13-materialize-complete-replacement.md) fixed this in place: "materialize replaces runtime only; it never edits briefs or `layout.toml`," and deferred project-owned drift — "no migration-playbook engine is built until a real breaking change exists."

The motivating case has now arrived, and it is not a breaking change — it is a beneficial *improvement* to the orchestrator rules in the skeleton. On 2026-06-23 the skeleton gained an "Orchestrator economy" directive that trims orchestrator prose. On a downstream project that prose was the largest cost line — the orchestrator accounted for 44.6% of project spend. Because the skeleton is scaffolded once, that directive reaches only greenfield consumers. The very project that motivated it never sees it.

The gap is structural, not a bug. The samples demonstrated it the same day: `bootstrap.sh` re-materialized their runtime, but their `CLAUDE.md` stayed unchanged and the directive had to be hand-ported. `check-sync` does not verify skeleton-to-consumer `CLAUDE.md` parity, and it cannot become a hard gate. A consumer's `CLAUDE.md` is authoritative for that project and is *expected* to diverge, so a parity check would fail on every legitimate customization. The doctor catches *contract* drift (a missing required section), not a *missing improvement*: a `CLAUDE.md` that predates a new orchestration rule is structurally valid and passes every gate.

So skeleton improvements reach only the projects onboarded after them, and rot for the installed base. That defeats the living-reference premise — the value is that better orchestration patterns propagate, not that they are frozen at scaffold time.

## Options Considered

1. **Status quo.** Rejected: skeleton improvements reach only greenfield consumers; the installed base, including the project that motivated a change, never receives it.
2. **Make `CLAUDE.md` harness-owned — materialize replaces it.** Rejected: `CLAUDE.md` carries the project's build commands, conventions, and project-specific rules. Wholesale replacement clobbers legitimate customization and breaks the project-owned/runtime split the whole upgrade model rests on.
3. **Version-stamped canonical-section manifest.** Stamp the harness version into `layout.toml` at scaffold; ship a manifest of canonical orchestrator sections with per-version hashes; compare and notify. Rejected: the stamp is a weak proxy. A consumer who scaffolds at a version that *has* a section and then deletes it is indistinguishable from one who never had it. The manifest is a new drift surface `check-sync` must guard, and the current skeleton already shipped with the tooling is the baseline the model can diff against directly. Machinery without enough payoff.
4. **Advisory LLM reconciliation in `/materialize`.** Diff the target `CLAUDE.md` against the current shipped skeleton; the model classifies each difference as a generic harness improvement or project-specific divergence and proposes adoptions through the `harvest` adopt/skip/ask flow. Never writes without confirmation.

## Decision

**Option 4.** `/materialize` gains an advisory `CLAUDE.md` reconciliation pass — the forward edge of the `harvest` classify-and-ask model, run from source toward the consumer.

- **Reconcile against the live skeleton, not a manifest.** After replacing runtime, the skill reads the target `CLAUDE.md` and the current `init` skeleton for the stack. It identifies sections present or improved in the skeleton but absent or divergent in the target. Each is classified: a generic orchestrator rule is a **proposal**, a project-specific section is **left alone**. Classification is model judgment against the skeleton — the same heuristic `/materialize` already uses for orphan-vs-extension, with no new persistent artifact.
- **No version stamp, no manifest.** The current skeleton, shipped with the tooling, is the baseline. This holds the no-stored-manifest stance of the [complete-replacement ADR](2026-06-13-materialize-complete-replacement.md): the authoritative unit set is the source on disk, not recorded state.
- **The project-owned invariant is preserved.** The pass *proposes*; it never silently writes a project-owned file. The 2026-06-13 invariant changes only by gaining a confirmation-gated proposal step — runtime is still the only thing materialize writes unasked.
- **Three-way conflicts go to the human.** A section the consumer both customized and the source improved is shown with both versions and reconciled by the human, never auto-applied. This is the one case a manifest could not decide; model judgment plus `harvest`'s ask resolves it.
- **The skeleton ships with the tooling.** For a marketplace or copy-channel consumer with no local `/harness`, the current `init` skeleton travels with the upgrade so there is a baseline to diff. One packaging obligation the runtime-only materialize did not carry.
- **Optional idempotence.** A `declined_reconciliations` list in `layout.toml [harness]` records sections the consumer skipped, so a deliberate decline does not re-prompt each upgrade. Polish, not core — ship without it, add it if re-prompting proves irritating.
- **Advisory only, never a gate.** Skeleton-to-consumer parity is not a doctor check; expected divergence would make it fail falsely. Reconciliation is a proposal at upgrade time.

## Consequences

**Positive:**
- Skeleton improvements reach the installed base, not only greenfield consumers — the living-reference premise holds.
- The project-owned boundary is intact: propose-and-confirm, never clobber.
- No version system and no new tracked artifact; the baseline is the shipped skeleton, consistent with the prior ADR.
- The hardest case — customized *and* improved — is handed to the human with both versions, decided by judgment rather than a hash match.

**Negative:**
- Generic-vs-project is a judgment call, not a deterministic diff — the same risk class as orphan-vs-extension. Safeguard: ask, never auto-write.
- Without the optional skip-memory, a deliberately declined section re-prompts each upgrade. Mitigated by `declined_reconciliations` when wanted.
- The pass runs a model analysis over `CLAUDE.md` on every materialize. Bounded: one file of roughly 100 lines, and `/materialize` is already a model-driven skill.
- The skeleton must ship with the tooling for distributed consumers — a packaging obligation runtime-only materialize avoided.

## Implementation

**Requirements:** the `/materialize` skill gains a reconciliation phase. It reads the target `CLAUDE.md` and the current `init` skeleton, classifies section deltas, and proposes adoptions via adopt/skip/ask, with three-way conflicts handed to the human. The `init` skeleton ships with the materialize tooling on the marketplace and copy channels. `layout.toml [harness]` optionally carries `declined_reconciliations`. No doctor or engine change — the pass is advisory and model-driven. Implemented as step 9 of the `/materialize` skill, modeled on the existing steps 7–8 consented-migration proposals.

## References

- [Materialize Is a Complete Replacement, Not an Additive Copy](2026-06-13-materialize-complete-replacement.md) — sets the runtime-only invariant and defers project-owned drift; this ADR resolves that deferral without breaking the invariant
- [Docs as the Harness–Project API](2026-06-12-docs-as-harness-project-api.md) — defines the project-owned/runtime split and the channels the skeleton must travel on
- [Seed and Harvest at the Root](2026-06-11-root-seed-harvest.md) — the harvest classify-and-ask model this runs in the forward direction
- [Project History](../../README.md#project-history) — the what/when timeline
