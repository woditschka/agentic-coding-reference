# Architecture Decision Records

This directory is the reference's **decision log** — why the agentic harness is shaped the way it is, and how it evolved. Each ADR records the options considered, the trade-offs, and the choice.

These are decisions about the **reference harness itself** (the methodology described in [`../agentic-harness.md`](../agentic-harness.md) and [`../specialist-agent-workflow.md`](../specialist-agent-workflow.md)). The implementations that realize them live under `samples/`. The samples ship no ADRs — a consumer's `docs/adr/` starts with only the README stub, and its decision log is its own; they do not carry this evolution history.

This log pairs with the [Project History](../../README.md#project-history) in the root README: the history is the *what/when* timeline; these ADRs are the *why*.

**Governance:** See the [`document-writing` skill](../../harness/core/.claude/skills/document-writing/documentation-standards.md) for how documents relate and cross-reference; see the [`adr-template` skill](../../harness/core/.claude/skills/adr-template/SKILL.md) for when to create ADRs.

## Format

Each ADR is a markdown file named `YYYY-MM-DD-title-in-kebab-case.md`. Keep it concise (aim under 60 lines), write in present tense, and link related ADRs when decisions interact. Update status when a decision changes; supersede rather than delete.

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

`Status` values: `Accepted`, `Accepted (<qualifier>)` when a later ADR amends part of it, or `Superseded by <linked ADR>`. When a later decision amends or supersedes an earlier one, update the earlier file's status line and mirror it in the index below. Add a short blockquote note under the status saying what changed and what still holds.

Older entries predate this skeleton — some carry `## Notes` instead of `## References`, omit `## Options Considered`, or phrase their status free-form. They stay as written; the skeleton governs new ADRs.

## Index

| Date | Decision | Status |
|------|----------|--------|
| 2026-03-22 | [Skill-Based Agent Architecture](2026-03-22-skill-based-agent-architecture.md) | Accepted |
| 2026-05-08 | [Append-Only JSONL Handoffs with Schema Validation Gate](2026-05-08-append-only-jsonl-handoffs.md) | Accepted |
| 2026-06-03 | [Principles Over Rigid Rules in Harness Prose](2026-06-03-principles-over-rigid-rules.md) | Accepted (revisit item closed by 2026-07-14) |
| 2026-06-04 | [Deterministic Truncation Detection via Dispatch-Start](2026-06-04-deterministic-truncation-detection.md) | Accepted |
| 2026-06-05 | [Change Grader: Always-On Advisory Risk Read](2026-06-05-change-grader.md) | Accepted (vocabulary amended by 2026-06-05 change-grade-report; always-on made optional by 2026-07-06 optional-change-grading) |
| 2026-06-05 | [Change-Grade Report: Per-Facet Notes and a Clear/Concern Verdict](2026-06-05-change-grade-report.md) | Accepted |
| 2026-06-05 | [Change-Grade Extractor Reads the Uncommitted Working Tree](2026-06-05-change-grade-extractor-worktree.md) | Accepted (base default amended by 2026-06-21) |
| 2026-06-07 | [ADR Placement: Single Seed ADR in Samples, Decision Log at Root](2026-06-07-adr-placement.md) | Accepted (sample-seed clause superseded by 2026-06-12 — samples ship no ADRs) |
| 2026-06-10 | [Cap-Hit Recovery Is Continuation: Slice Size Decoupled from Dispatch Budget](2026-06-10-cap-hit-recovery-is-continuation.md) | Accepted |
| 2026-06-10 | [Continue-Only Resume: SendMessage Allowlist as the Continuation Fast Path](2026-06-10-continue-only-resume.md) | Accepted |
| 2026-06-11 | [Model Tier Assignment: Judgment Roles Premium, Checklist Roles Mid-Tier](2026-06-11-model-tier-assignment.md) | Accepted |
| 2026-06-11 | [Handoff Log Access: Single Deterministic Tool, Not Free-Form Writes](2026-06-11-handoff-log-access-tool.md) | Accepted (build wiring superseded by 2026-07-13 materialize-time-runtime-verification) |
| 2026-06-11 | [Seed and Harvest Move to the Root with Stack Auto-Detection](2026-06-11-root-seed-harvest.md) | Accepted (seed folded into /materialize by 2026-06-13) |
| 2026-06-12 | [Docs as the Harness–Project API: Project-Owned Briefs, Two Distribution Channels](2026-06-12-docs-as-harness-project-api.md) | Accepted (four details amended by the 2026-06-14 ADRs) |
| 2026-06-13 | [The document-writing Skill: Documentation Standards Ship as Runtime, Not Handbook](2026-06-13-document-writing-skill.md) | Accepted |
| 2026-06-13 | [Materialize Is a Complete Replacement, Not an Additive Copy](2026-06-13-materialize-complete-replacement.md) | Accepted (/seed alias retired; template-edge amended by 2026-07-01; channel default by 2026-06-14) |
| 2026-06-13 | [The Project Declares What It Owns: Extensions and Tool Surfaces](2026-06-13-extensions-and-tool-surfaces.md) | Accepted (channel default and migration amended by 2026-06-14) |
| 2026-06-14 | [Copy Is the Default Channel; the Channel Is Detected, Not Asked](2026-06-14-copy-channel-default.md) | Accepted |
| 2026-06-14 | [The Docs Audit Is One Command: `brief-review` Becomes `audit-docs` and Runs the Doctor](2026-06-14-audit-docs-skill.md) | Accepted |
| 2026-06-14 | [A Decoupled Harness Artifact Version](2026-06-14-decoupled-artifact-version.md) | Accepted (provenance stamp amended by 2026-06-27) |
| 2026-06-14 | [Layout-Sourced Schema Patterns via `patternFrom`](2026-06-14-layout-sourced-schema-patterns.md) | Accepted |
| 2026-06-14 | [The Marketplace Channel: Per-Tool Plugins, Project-Owned Engines](2026-06-14-marketplace-plugin-channel.md) | Accepted (plugin count and namespace since amended; see notes) |
| 2026-06-14 | [The Doctor Engine Lives in `scripts/`, Not Inside Its Skill](2026-06-14-doctor-engine-in-scripts.md) | Accepted |
| 2026-06-16 | [Security Principles as a Producer Brief and a Ninth Conjunctive Clause](2026-06-16-security-principles-brief.md) | Accepted |
| 2026-06-17 | [Generic Stack: a Lifecycle-Verb Contract as the Single Binding Surface](2026-06-17-generic-stack-verb-contract.md) | Accepted |
| 2026-06-18 | [Additive Reviewer Roster: a Mandatory Four-Reviewer Floor, Extended Never Subtracted](2026-06-18-additive-reviewer-roster.md) | Accepted (unconditional-dispatch clause amended by 2026-07-09; marketplace skip narrowed 2026-07-12) |
| 2026-06-19 | [The PRD Specialist Is a Discussion Partner, Gated by the Human, Not a Script](2026-06-19-prd-discussion-partner.md) | Accepted (execution surface amended by 2026-07-11) |
| 2026-06-20 | [The Handoff Append Is Pre-Approved Per Tool, via a Hook on Claude Code](2026-06-20-handoff-append-pre-approval.md) | Accepted (registration made deterministic by 2026-07-01) |
| 2026-06-21 | [Fresh-Eyes Review Over a Canonical Change Set](2026-06-21-fresh-eyes-review-changeset.md) | Accepted |
| 2026-06-22 | [Digestible Narrative Docs With an Enforced Budget](2026-06-22-digestible-narrative-docs.md) | Accepted |
| 2026-06-23 | [Materialize Proposes Skeleton Improvements to a Project's CLAUDE.md](2026-06-23-materialize-rules-reconciliation.md) | Superseded by 2026-06-24; Option 4 revived by 2026-07-01 |
| 2026-06-24 | [Harness Doctrine Lives in Managed Chapters of CLAUDE.md](2026-06-24-claude-md-managed-chapters.md) | Accepted |
| 2026-06-26 | [Open-Closed DDD: An Opinionated Default Over a Closed Kernel](2026-06-26-ddd-open-closed.md) | Accepted |
| 2026-06-27 | [Stamp the Harness Release Date into Every Session via CLAUDE.md](2026-06-27-harness-version-stamp.md) | Accepted |
| 2026-07-01 | [Materialize Keeps Every Template-Seeded File Current: Deterministic Additions, Advisory Residual](2026-07-01-generalized-template-reconciliation.md) | Accepted |
| 2026-07-02 | [Executable Pipeline Contracts](2026-07-02-executable-pipeline-contracts.md) | Accepted |
| 2026-07-02 | [Tiered Maintainer Workflow: One Judgment Skill, Scripted Propagation](2026-07-02-tiered-maintainer-workflow.md) | Accepted |
| 2026-07-03 | [Agent Mirror Bodies Are Rendered from the Claude Base](2026-07-03-rendered-agent-mirror-bodies.md) | Accepted |
| 2026-07-05 | [Split the Handoff Contract by Role; Guard the Log Mechanically](2026-07-05-handoff-skill-split.md) | Accepted |
| 2026-07-06 | [Deterministic Mid-Slice Routing via handoff.py route](2026-07-06-deterministic-mid-slice-routing.md) | Accepted |
| 2026-07-06 | [Logic in Python, Orchestration in Bash](2026-07-06-logic-in-python-orchestration-in-bash.md) | Accepted (typed-code standard added by 2026-07-17; script-shape clause amended by 2026-07-17 runtime-package-layout) |
| 2026-07-06 | [The Audit Carries a Security Lens, Deterministic and Judgment](2026-07-06-security-lens-in-the-audit.md) | Accepted |
| 2026-07-06 | [Change Grading Is Pipeline-Optional via auto_grade](2026-07-06-optional-change-grading.md) | Accepted |
| 2026-07-07 | [State Runtime Prose Once; Move the Route Spec Out of the Loaded Skill](2026-07-07-route-spec-companion.md) | Accepted |
| 2026-07-09 | [Risk-Proportional Review Dispatch](2026-07-09-risk-proportional-review.md) | Accepted (fix-cycle sizing amended by 2026-07-14) |
| 2026-07-11 | [Conversations Run in Root; Dispatches Produce Artifacts](2026-07-11-conversations-stay-in-root.md) | Accepted |
| 2026-07-12 | [Resilience-First Doctrine for Harness Improvements](2026-07-12-resilience-first-improvement-doctrine.md) | Accepted |
| 2026-07-12 | [Roster and Vocabulary Gates for Hand-Owned Parallel Files](2026-07-12-parity-gates-for-hand-owned-parallels.md) | Accepted (doc-sync split carve-out added 2026-08-06) |
| 2026-07-13 | [Materialize-Time Runtime Verification](2026-07-13-materialize-time-runtime-verification.md) | Accepted |
| 2026-07-13 | [Single Pricing Source as a Gated Vendored Copy](2026-07-13-single-pricing-source-vendored-copy.md) | Accepted |
| 2026-07-13 | [Append-Stamped Record Timestamps](2026-07-13-append-stamped-record-timestamps.md) | Accepted |
| 2026-07-13 | [The Battery Gates Every Push: A Pre-Push Hook and Server-Side CI](2026-07-13-server-side-battery-enforcement.md) | Accepted |
| 2026-07-14 | [Delta-Sized Fix Cycles and Class-Exhaustive Findings](2026-07-14-delta-sized-fix-cycles.md) | Accepted |
| 2026-07-14 | [Mechanical Promises Move Into Engines](2026-07-14-mechanical-promises-into-engines.md) | Accepted |
| 2026-07-15 | [The Transcript File as the Unit of Cost Attribution](2026-07-15-transcript-file-cost-attribution.md) | Accepted |
| 2026-07-15 | [Continuous Scanning Sits Beside the Deterministic Battery, Not Inside It](2026-07-15-continuous-scanning-beside-the-battery.md) | Accepted |
| 2026-07-16 | [The Exposed Tool Set Is a Setting, Not an Invariant](2026-07-16-exposed-tool-set-is-a-setting.md) | Accepted (pod-reachability premise amended by 2026-07-17) |
| 2026-07-17 | [The Pod Denies Host Egress by Default; the Preflight Opens One Port](2026-07-17-default-deny-pod-host-egress.md) | Superseded by [2026-07-29](2026-07-29-proxy-enforced-egress.md) |
| 2026-07-17 | [A Typed, Checker-Enforced Standard for the Harness Python Core](2026-07-17-typed-python-core.md) | Accepted (single-file clause and script-shape bullet amended by 2026-07-17 runtime-package-layout; tools/ scope recorded 2026-08-06) |
| 2026-07-17 | [The Shipped Runtime Becomes Domain Packages Under a Composition Root](2026-07-17-runtime-package-layout.md) | Accepted |
| 2026-07-17 | [Module Derivation: Named Layouts over a Regex Primitive](2026-07-17-module-derivation-named-layouts.md) | Accepted |
| 2026-07-18 | [PRD Autofix: In-Round Root-Applied Fixes on docs/prd.md](2026-07-18-prd-autofix.md) | Accepted |
| 2026-07-18 | [One Layout Reader; Materialize Previews a Transient Plan](2026-07-18-materialize-previewable-plan.md) | Accepted |
| 2026-07-18 | [Producer-Side Toolboxes Separate Tests From Source, Without Packaging](2026-07-18-producer-side-tests-subdir.md) | Accepted |
| 2026-07-18 | [check-sync.py Becomes a Thin Launcher Over a `check_sync/` Package](2026-07-18-check-sync-decomposition.md) | Accepted |
| 2026-07-18 | [The Deterministic Battery Is Renamed `verify-harness`](2026-07-18-verify-harness-rename.md) | Accepted |
| 2026-07-18 | [Producer-Side Script Names Encode Scope: `-harness` for the Whole, the Tree for One](2026-07-18-producer-script-naming.md) | Accepted |
| 2026-07-19 | [The Harness Glue Is Provably Confined: No Network, Writes Only to Declared Roots](2026-07-19-network-write-confinement-gate.md) | Accepted |
| 2026-07-20 | [The Pod Image Verifies Claude's Channel, Floats the Toolchains, Runs Non-Root](2026-07-20-pod-image-supply-chain.md) | Accepted |
| 2026-07-29 | [Egress Is Enforced by an External Proxy, Not by the Workload](2026-07-29-proxy-enforced-egress.md) | Accepted |
| 2026-07-31 | [The Default Permission Posture Is Auto Mode, Not Skip](2026-07-31-auto-permission-mode-default.md) | Accepted |
| 2026-07-31 | [Local Binding Is Granted, and Its Localhost Egress Accepted](2026-07-31-local-binding-residual.md) | Accepted |
| 2026-07-31 | [Brownfield Briefs Are Derived With Provenance, Never Reconstructed](2026-07-31-derived-briefs-carry-provenance.md) | Accepted |
| 2026-08-01 | [All Plugins Share One Skill Namespace: agent-team](2026-08-01-shared-plugin-namespace.md) | Accepted |
