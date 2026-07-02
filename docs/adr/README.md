# Architecture Decision Records

This directory is the reference's **decision log** — why the agentic harness is shaped the way it is, and how it evolved. Each ADR records the options considered, the trade-offs, and the choice.

These are decisions about the **reference harness itself** (the methodology described in [`../agentic-harness.md`](../agentic-harness.md) and [`../specialist-agent-workflow.md`](../specialist-agent-workflow.md)). The implementations that realize them live under `samples/`. The samples ship no ADRs — a consumer's `docs/adr/` starts with only the README stub, and its decision log is its own; they do not carry this evolution history.

This log pairs with the [Project History](../../README.md#project-history) in the root README: the history is the *what/when* timeline; these ADRs are the *why*.

**Governance:** See the [`document-writing` skill](../../harness/core/.claude/skills/document-writing/documentation-standards.md) for how documents relate and cross-reference; see the `adr-template` skill for when to create ADRs.

## Format

Each ADR is a markdown file named `YYYY-MM-DD-title-in-kebab-case.md`. Keep it concise (aim under 60 lines), write in present tense, and link related ADRs when decisions interact. Update status when a decision changes; supersede rather than delete.

## Index

| Date | Decision | Status |
|------|----------|--------|
| 2026-03-22 | [Skill-Based Agent Architecture](2026-03-22-skill-based-agent-architecture.md) | Accepted |
| 2026-05-08 | [Append-Only JSONL Handoffs](2026-05-08-append-only-jsonl-handoffs.md) | Accepted |
| 2026-06-03 | [Principles Over Rigid Rules in Harness Prose](2026-06-03-principles-over-rigid-rules.md) | Accepted |
| 2026-06-04 | [Deterministic Truncation Detection via Dispatch-Start](2026-06-04-deterministic-truncation-detection.md) | Accepted |
| 2026-06-05 | [Change Grader: Always-On Advisory Risk Read](2026-06-05-change-grader.md) | Accepted |
| 2026-06-05 | [Change-Grade Report: Per-Facet Notes and a Clear/Concern Verdict](2026-06-05-change-grade-report.md) | Accepted |
| 2026-06-05 | [Change-Grade Extractor Reads the Uncommitted Working Tree](2026-06-05-change-grade-extractor-worktree.md) | Accepted |
| 2026-06-07 | [ADR Placement: Single Seed ADR in Samples, Decision Log at Root](2026-06-07-adr-placement.md) | Accepted (sample-seed clause superseded by 2026-06-12 — samples ship no ADRs) |
| 2026-06-10 | [Cap-Hit Recovery Is Continuation: Slice Size Decoupled from Dispatch Budget](2026-06-10-cap-hit-recovery-is-continuation.md) | Accepted |
| 2026-06-10 | [Continue-Only Resume: SendMessage Allowlist as the Continuation Fast Path](2026-06-10-continue-only-resume.md) | Accepted |
| 2026-06-11 | [Model Tier Assignment: Judgment Roles Premium, Checklist Roles Mid-Tier](2026-06-11-model-tier-assignment.md) | Accepted |
| 2026-06-11 | [Handoff Log Access: Single Deterministic Tool, Not Free-Form Writes](2026-06-11-handoff-log-access-tool.md) | Accepted |
| 2026-06-11 | [Seed and Harvest Move to the Root with Stack Auto-Detection](2026-06-11-root-seed-harvest.md) | Accepted |
| 2026-06-12 | [Docs as the Harness–Project API: Project-Owned Briefs, Two Distribution Channels](2026-06-12-docs-as-harness-project-api.md) | Accepted |
| 2026-06-13 | [The document-writing Skill: Documentation Standards Ship as Runtime, Not Handbook](2026-06-13-document-writing-skill.md) | Accepted |
| 2026-06-13 | [Materialize Is a Complete Replacement, Not an Additive Copy](2026-06-13-materialize-complete-replacement.md) | Accepted |
| 2026-06-13 | [The Project Declares What It Owns: Extensions and Tool Surfaces](2026-06-13-extensions-and-tool-surfaces.md) | Accepted |
| 2026-06-14 | [Copy Is the Default Channel; the Channel Is Detected, Not Asked](2026-06-14-copy-channel-default.md) | Accepted |
| 2026-06-14 | [The Docs Audit Is One Command: `brief-review` Becomes `audit-docs` and Runs the Doctor](2026-06-14-audit-docs-skill.md) | Accepted |
| 2026-06-14 | [A Decoupled Harness Artifact Version](2026-06-14-decoupled-artifact-version.md) | Accepted (provenance stamp amended by 2026-06-27) |
| 2026-06-14 | [Layout-Sourced Schema Patterns via `patternFrom`](2026-06-14-layout-sourced-schema-patterns.md) | Accepted |
| 2026-06-14 | [The Marketplace Channel: Per-Tool Plugins, Project-Owned Engines](2026-06-14-marketplace-plugin-channel.md) | Accepted |
| 2026-06-14 | [The Doctor Engine Lives in `scripts/`, Not Inside Its Skill](2026-06-14-doctor-engine-in-scripts.md) | Accepted |
| 2026-06-16 | [Security Principles as a Producer Brief and a Ninth Conjunctive Clause](2026-06-16-security-principles-brief.md) | Accepted |
| 2026-06-17 | [Generic Stack: a Lifecycle-Verb Contract as the Single Binding Surface](2026-06-17-generic-stack-verb-contract.md) | Accepted |
| 2026-06-18 | [Additive Reviewer Roster: a Mandatory Four-Reviewer Floor, Extended Never Subtracted](2026-06-18-additive-reviewer-roster.md) | Accepted |
| 2026-06-19 | [The PRD Specialist Is a Discussion Partner, Gated by the Human, Not a Script](2026-06-19-prd-discussion-partner.md) | Accepted |
| 2026-06-20 | [The Handoff Append Is Pre-Approved Per Tool, via a Hook on Claude Code](2026-06-20-handoff-append-pre-approval.md) | Accepted |
| 2026-06-21 | [Fresh-Eyes Review Over a Canonical Change Set](2026-06-21-fresh-eyes-review-changeset.md) | Accepted |
| 2026-06-22 | [Digestible Narrative Docs With an Enforced Budget](2026-06-22-digestible-narrative-docs.md) | Accepted |
| 2026-06-23 | [Materialize Proposes Skeleton Improvements to a Project's CLAUDE.md](2026-06-23-materialize-rules-reconciliation.md) | Superseded by 2026-06-24 |
| 2026-06-24 | [Harness Doctrine Lives in Managed Chapters of CLAUDE.md](2026-06-24-claude-md-managed-chapters.md) | Accepted |
| 2026-06-26 | [Open-Closed DDD: An Opinionated Default Over a Closed Kernel](2026-06-26-ddd-open-closed.md) | Accepted |
| 2026-06-27 | [Stamp the Harness Release Date into Every Session via CLAUDE.md](2026-06-27-harness-version-stamp.md) | Accepted |
| 2026-07-01 | [Materialize Keeps Every Template-Seeded File Current: Deterministic Additions, Advisory Residual](2026-07-01-generalized-template-reconciliation.md) | Accepted |
| 2026-07-02 | [Executable Pipeline Contracts](2026-07-02-executable-pipeline-contracts.md) | Accepted |
