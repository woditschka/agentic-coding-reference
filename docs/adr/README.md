# Architecture Decision Records

This directory is the reference's **decision log** — why the agentic harness is shaped the way it is, and how it evolved. Each ADR records the options considered, the trade-offs, and the choice.

These are decisions about the **reference harness itself** (the methodology described in [`../agentic-harness.md`](../agentic-harness.md) and [`../specialist-agent-workflow.md`](../specialist-agent-workflow.md)). The implementations that realize them live under `samples/`. The samples ship no ADRs — a consumer's `docs/adr/` starts with only the README stub, and its decision log is its own; they do not carry this evolution history.

This log pairs with the [Project History](../project-history.md): the history is the *what/when* timeline; these ADRs are the *why*.

**Governance:** See the [`document-writing` skill](../../harness/core/.claude/skills/document-writing/documentation-standards.md) for how documents relate and cross-reference; see the [`adr-template` skill](../../harness/core/.claude/skills/adr-template/SKILL.md) for when to create ADRs.

## Format

Each ADR is a markdown file named `YYYY-MM-DD-title-in-kebab-case.md`, one per standing decision. Keep it concise (aim under 110 lines), write in present tense, and link related ADRs when decisions interact. A published decision is one on the remote's default branch; when it changes, update the status and supersede rather than delete. An ADR not yet there is a draft and is edited in place; the `prepare-ship` skill folds a feature's drafts at feature close. At a publication boundary the maintainer may compact the published log to one ADR per standing decision ([the decision-log ADR](2026-06-07-the-decision-log.md)). A compacted ADR states the standing decision; the ADRs it replaced stay in git under their old paths. The filename date is the earliest decision the ADR holds.

New ADRs follow this skeleton:

```markdown
# <Decision as a Declarative Title>

**Status:** <see values below>

## Context              <!-- the forces; what made a decision necessary -->
## Options Considered   <!-- numbered; each rejected option carries its rejection reason -->
## Decision             <!-- the choice, bold first sentence, then the load-bearing details -->
## Consequences         <!-- Positive / Negative subsections when both exist -->
## Implementation       <!-- where the decision landed; omit when Decision already names the files -->
## References           <!-- related ADRs and docs, each with a clause saying why it relates -->
```

`Status` values: `Accepted`, `Accepted (<qualifier>)` when a later ADR amends part of it, or `Superseded by <linked ADR>`. When a later decision amends or supersedes an earlier one, update the earlier file's status line; it is the single source. The index below is generated from it (`harness/render-adr-index.py`, battery-gated), never hand-edited. Add a short blockquote note under the status saying what changed and what still holds. Keep the status line one compact clause chain (it renders as a table cell); qualify any section-anchor link with the ADR's own filename so it resolves from this index too.

Between compactions an accepted ADR is immutable apart from its status line: a new decision is a new ADR. A citation of a decision the compaction folded names the holding ADR; the folded text is read from git.

## Index

| Date | Decision | Status |
|------|----------|--------|
| 2026-03-22 | [Skill-Based Agent Architecture](2026-03-22-skill-based-agent-architecture.md) | Accepted |
| 2026-05-08 | [The Handoff Ledger Is Append-Only JSONL Written Through One Tool](2026-05-08-the-handoff-ledger.md) | Accepted |
| 2026-06-03 | [Principles Over Rigid Rules in Harness Prose](2026-06-03-principles-over-rigid-rules.md) | Accepted (revisit item closed by 2026-07-14; see note) |
| 2026-06-04 | [The Dispatch Lifecycle Is Observable From the Ledger Alone](2026-06-04-dispatch-lifecycle.md) | Accepted |
| 2026-06-05 | [The Change-Grader: A Terminal Advisory Read That Names the Reading Depth](2026-06-05-the-change-grader.md) | Accepted |
| 2026-06-07 | [The Decision Log Lives at the Root, Is Rewritable Until Published, and Is Compacted at a Boundary](2026-06-07-the-decision-log.md) | Accepted |
| 2026-06-11 | [Materialize Is a Complete Replacement Run From the Root](2026-06-11-materialize.md) | Accepted |
| 2026-06-11 | [Judgment Roles Run the Premium Tier; the Ledger Routes Routine Work to the Checklist Tier](2026-06-11-model-tiering.md) | Accepted |
| 2026-06-12 | [The Project's Docs Are the Harness–Project API](2026-06-12-docs-as-harness-project-api.md) | Accepted |
| 2026-06-13 | [Documentation Standards Ship as Runtime, With a Budget, Provenance, and Stack Fragments](2026-06-13-documentation-standards.md) | Accepted |
| 2026-06-14 | [Three Distribution Channels Deliver One Agent-Team](2026-06-14-distribution-channels.md) | Accepted |
| 2026-06-14 | [layout.toml Declares the Project; Engines and Schemas Read It](2026-06-14-layout-declares-the-project.md) | Accepted |
| 2026-06-14 | [The Doctor Is a Project-Side Engine; audit-docs Runs It First](2026-06-14-the-doctor.md) | Accepted |
| 2026-06-16 | [The Nine-Clause Bar Carries Security and Workload Fit as Producer Law](2026-06-16-the-nine-clause-bar.md) | Accepted |
| 2026-06-18 | [The Reviewer Roster: A Doctor-Enforced Floor, Dispatched in Proportion to Risk](2026-06-18-the-reviewer-roster.md) | Accepted |
| 2026-06-19 | [The Product Expert and the Root Conversation](2026-06-19-the-product-expert-and-the-root-conversation.md) | Accepted |
| 2026-06-21 | [Fresh-Eyes Review Over a Canonical Change Set](2026-06-21-fresh-eyes-review-changeset.md) | Accepted (the `scripts/changeset.sh` verb retired by the [2026-07-17 amendment](2026-07-06-the-python-core.md); callers invoke `python3 scripts/changeset.py`, and the one-definition rule stands; plan file retired by [2026-10-20](2026-10-20-slice-sizing-and-the-checkpoint.md)) |
| 2026-06-26 | [Open-Closed DDD: An Opinionated Default Over a Closed Kernel](2026-06-26-ddd-open-closed.md) | Accepted |
| 2026-07-02 | [Pipeline Contracts Are Executed by Deterministic Engines](2026-07-02-deterministic-routing-engines.md) | Accepted |
| 2026-07-02 | [The Maintainer Workflow Is Tiered: a Deterministic Battery Under One Judgment Skill](2026-07-02-tiered-maintainer-workflow.md) | Accepted |
| 2026-07-06 | [The Harness Core Is Typed, Stdlib-Only Python in Domain Packages](2026-07-06-the-python-core.md) | Accepted |
| 2026-07-12 | [Improvement Proposals Are Judged by Enforcement, With Cost as Tiebreaker](2026-07-12-resilience-first-improvement-doctrine.md) | Accepted |
| 2026-07-14 | [Review Convergence: Delta-Sized Fix Rounds, Bounded at Three, Scope Locked to the Owner's Words](2026-07-14-review-convergence.md) | Accepted |
| 2026-07-15 | [The Eval Bench Measures Cost per Pass, Attributed per Transcript File, on One Task Fingerprint](2026-07-15-the-eval-bench.md) | Accepted |
| 2026-07-16 | [Confined Agent Tools](2026-07-16-confined-agent-tools.md) | Accepted |
| 2026-07-17 | [Module Derivation: Named Layouts Expand to a Regex Primitive](2026-07-17-module-derivation.md) | Accepted |
| 2026-07-18 | [Design Truth Holds Mid-Slice Without a Pipeline Re-Flow](2026-07-18-design-truth-mid-slice.md) | Accepted |
| 2026-09-03 | [Test Conventions Are Decided at Write Time and Carry Their Evidence](2026-09-03-test-conventions-at-write-time.md) | Accepted (listing reading gated 2026-10-30; see note) |
| 2026-09-12 | [The Outer Loop Reads the Team's Board Through a Project-Owned Connector](2026-09-12-backlog-connector.md) | Accepted |
| 2026-09-13 | [A Product Workspace Holds the Product Truth; Module Repositories Are Members Checked Out on Demand](2026-09-13-product-workspace-with-member-modules.md) | Accepted (member placement decided 2026-09-18; spike half run 2026-09-18; change 1 of 3 landed 2026-09-19; see Implementation) |
| 2026-10-20 | [The Implementer Keeps No Plan File and the Checkpoint Runs the Gate](2026-10-20-slice-sizing-and-the-checkpoint.md) | Accepted |
| 2026-10-30 | [A Required Gate Check Is Checked Where the Project Declares It](2026-10-30-the-gate-vocabulary-is-checked.md) | Accepted |
