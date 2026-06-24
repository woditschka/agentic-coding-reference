# Harness Doctrine Lives in Managed Chapters of CLAUDE.md

**Status:** Accepted

## Context

[Materialize Proposes Skeleton Improvements](2026-06-23-materialize-rules-reconciliation.md) added an advisory pass: on upgrade, `/materialize` diffed the target `CLAUDE.md` against the current skeleton and proposed adopting improved orchestrator rules through an adopt/skip/ask flow. It shipped as step 9.

The pass managed the friction; it did not remove it. The root cause is an ownership mismatch. Several `CLAUDE.md` chapters are stack-agnostic harness doctrine, not project preference — `## Agent Usage` (relay discipline, orchestrator economy, confirmation gates, the tool-call budget), `## Memory`, `## Writing Standards`, `## Scratch Directory`, `## Documentation Updates`. But they physically live inside `CLAUDE.md`, which is project-owned and never overwritten. So every improvement to that doctrine can only reach an onboarded project through a consented edit. The day after step 9 shipped, the cost stood: each future rule change re-triggers the same per-section proposal, on every project, forever.

A measurement made the duplication concrete. Those chapters were byte-identical across the `go`, `java-spring-boot`, and `generic` skeletons — five chapters copy-pasted three ways and maintained by hand. The Agent Usage chapter alone had already drifted in eight small spots (a build-command example, a few skill-table descriptions, the IDE-oracle rows).

The constraint that shapes the fix: this doctrine must sit in the one file all four supported tools read as their rules file. Claude Code, Copilot CLI, OpenCode, and Junie all read `CLAUDE.md`. It must always be in context (it governs every turn), so it cannot move to an on-demand skill.

## Options Considered

1. **Keep step 9 (advisory reconciliation).** Rejected: it re-prompts on every doctrine improvement, on every project. The friction is permanent, only made polite.
2. **`@import` a separate harness-owned file.** Cleanest ownership on paper: `CLAUDE.md` keeps a one-line import to a runtime file replaced freely. Rejected: `@import` is a Claude Code feature. OpenCode, Copilot, and Junie do not expand it. The doctrine would silently fail to load for three of four tools — actively lowering the bar where today all four carry it.
3. **Make all of `CLAUDE.md` harness-owned.** Rejected for the same reason the prior ADR rejected it: the file carries the project's build commands, conventions, and local rules. Wholesale replacement clobbers legitimate customization.
4. **Marker-comment blocks.** Wrap each managed region in `<!-- BEGIN/END -->` comments. Rejected: it adds machine syntax to a human-facing file, and a chapter already has a natural identity — its `## ` heading.
5. **Harness-managed chapters, identified by heading.** Each managed chapter is found by its `## ` heading and replaced in place, from that heading to the next `## ` heading. Single-source each; materialize replaces only those chapters on every upgrade. Every other chapter stays project-owned, interleaved in the project's own order.

## Decision

**Option 5.** The harness doctrine becomes a set of managed chapters, each identified by its heading and refreshed automatically.

- **One source file, copied verbatim.** The managed set is exactly the `## ` chapters of `harness/claude-md/managed-chapters.md` — Agent Usage, Memory, Writing Standards, Scratch Directory, Documentation Updates — in canonical order. The source mirrors the shipped `CLAUDE.md`: what you read there, in that order, is what materializes, so a coherence or dedup review of the doctrine is a single-file read. Adding a managed chapter is adding a `## ` section; removing one is deleting it. The content is byte-identical for every stack: no per-stack template, no token substitution. The Agent Usage chapter's eight stack-specific tokens are eliminated two ways. Genericizing the prose removes most — which also obeys the harness's "no runtime-specific numbers in generic doctrine" invariant. Splitting the catalog removes the rest: the stack-agnostic core skills stay in the chapter, while stack-specific skills (the IDE oracle) move to their own project-owned `## Stack-specific skills` chapter.
- **Refreshed on every channel, no prompt.** `materialize.sh` (copy/manifest) finds each managed heading and rewrites its chapter through to the next `## ` heading. `init.sh` fills them at scaffold time. On the marketplace channel, the plugin bundles `claude-md/` and `setup.sh` runs the same refresh against the consumer's `CLAUDE.md`. All three share one helper, `harness/claude-md/refresh-chapters.sh`. That content is harness-owned — refreshing it is not an edit to project-owned text, the same contract as the `.gitignore` runtime block. Chapters stay interleaved with project-owned ones because each is replaced independently by its heading.
- **Order is set once, never disturbed.** The in-place refresh never reorders. The skeleton (`harness/init/stacks/<stack>/CLAUDE.md`) is the canonical layout for a greenfield project, and step 9 places a migrated chapter to match it. Position is a project-owned, one-time decision; the harness only keeps each chapter's *content* current.
- **The chapters must exist.** A new doctor check, `required-chapter`, fails if any managed heading is missing or its chapter is empty. The doctor's chapter list is held in lockstep with the source file's headings by a parity guard in `test-materialize.sh`. "Must exist" is enforced, not assumed.
- **Cross-tool by construction.** The chapters are plain markdown in the one file all four tools read. No tool is left behind, which `@import` could not guarantee.
- **Post-refresh review (advisory).** A heading-bounded overwrite is correct for a chapter's doctrine but cannot see the rest of the file. So the `/materialize` skill reviews the result, keyed on `git diff -- CLAUDE.md`. It catches four things the deterministic layer can't: lost project content, repeated doctrine, contradiction with a project chapter, and bad order. Findings are proposed, never auto-applied. The deterministic core stays pure: `bootstrap` and the scripts never run the review.
- **Step 9 is demoted to a one-time migration.** Most legacy files already carry the exact managed headings, so the first materialize replaces them in place with no migration at all. Only a renamed or missing heading needs the consented conversion — insert the chapter, lift the old inlined copy, preserve genuine customization. No recurring prompt, no per-section reconciliation, no `declined_reconciliations` key.
- **`CLAUDE.md` becomes a hybrid file.** Harness-managed chapters interleaved with project-owned chapters — the same conceptual model as `.gitignore` today. The harness-project API records the new boundary.

## Consequences

**Positive:**
- Doctrine improvements reach every project and every tool automatically, with zero prompts — the friction is removed, not managed.
- The three-way duplication of five chapters collapses to one source each; the stacks can no longer drift.
- The mechanism is simpler than what it replaces: a verbatim heading-bounded copy from one source file, versus a model-driven section-by-section diff. Scaling from one managed chapter to five added no mechanism — just more `## ` sections in the one source file.
- The project-owned boundary is sharper: a managed chapter is explicitly harness-owned, like the runtime, so "never silently edit project content" still holds.
- Drift is impossible to ship silently: the samples' faithfulness check, the doctor's `required-chapter` check, and the source-vs-doctor parity guard all guard it.
- The human-facing file stays clean — no marker comments. Each chapter heading carries the identity.

**Negative:**
- `CLAUDE.md` is no longer purely project-owned; readers must know which chapters are harness-managed. Mitigated by the `.gitignore` precedent and the doctor check.
- The boundary depends on heading structure. A renamed heading loses the link (caught by the `required-chapter` check). A managed chapter must be `## `-bounded, which is why stack-specific skills became their own chapter. Adding a brand-new managed chapter to a project that predates it needs the heading as an anchor — absent it, step 9 places it once.
- A project that puts its own content *inside* a managed chapter loses it on refresh — by design, since a managed chapter is harness-owned. The deterministic layer cannot prevent this; the post-refresh review (step 9) catches it in the diff and proposes relocating the content to a project-owned chapter.
- Stack-specific skill rows (the IDE oracle catalog) now live in a project-owned table and do not auto-upgrade — the original drift problem, scoped to a low-stakes catalog. Accepted deliberately as the core/extension split.
- Genericizing the prose drops a few stack-flavored phrasings (e.g. the `60`-tool-call number) from `go`/`java`. Judged an improvement, not a loss: it aligns with the no-runtime-numbers invariant.
- Consolidating five chapter files into one source drops per-file git history: a chapter's evolution no longer isolates to its own file. Minor — `git log -L` or a path filter still recovers per-chapter history, and the single-file coherence review outweighs it.

## Implementation

**Requirements:** a source-only tree `harness/claude-md/` holds two files. It sits outside `core/` and `stacks/`, so materialize never copies it into a target as runtime. `managed-chapters.md` is the single source — its `## ` chapters are the managed set, in canonical order. `refresh-chapters.sh` is the heading-bounded in-place writer that slices the source by heading. `materialize.sh` and `init.sh` call `refresh-chapters.sh` to refresh the chapters. `bootstrap.sh` propagates them to the samples. `package-marketplace.sh` bundles `claude-md/` into each plugin, and `marketplace/setup.sh` runs the same refresh, so the marketplace channel stays current too. The three init skeletons and three samples carry the managed headings; go/java add a `## Stack-specific skills` chapter. `brief_doctor.py` gains the `required-chapter` check with `REQUIRED_CHAPTERS`, kept in lockstep with the source file's headings by a parity guard in `test-materialize.sh`. The doctor tests cover present, missing, and empty. The `/materialize` skill demotes step 9 to the one-time legacy conversion, adds the duplicate-outside LLM scan, and documents the automatic refresh in step 4. No new tracked manifest; the source on disk remains the authoritative baseline, consistent with the complete-replacement ADR.

## References

- [Materialize Proposes Skeleton Improvements to a Project's CLAUDE.md](2026-06-23-materialize-rules-reconciliation.md) — the advisory pass this supersedes; its problem analysis still holds
- [Materialize Is a Complete Replacement, Not an Additive Copy](2026-06-13-materialize-complete-replacement.md) — the runtime-only invariant this extends with harness-owned chapters
- [Docs as the Harness–Project API](2026-06-12-docs-as-harness-project-api.md) — the project-owned/runtime split the managed chapters refine
- [Project History](../../README.md#project-history) — the what/when timeline
