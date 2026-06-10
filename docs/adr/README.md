# Architecture Decision Records

This directory is the reference's **decision log** — why the agentic harness is shaped the way it is, and how it evolved. Each ADR records the options considered, the trade-offs, and the choice.

These are decisions about the **reference harness itself** (the methodology described in [`../agentic-harness.md`](../agentic-harness.md) and [`../specialist-agent-workflow.md`](../specialist-agent-workflow.md)). The implementations that realize them live in the `go/` and `java-spring-boot/` samples. The samples ship a single consolidated architecture ADR for seeding; they do not carry this evolution history.

This log pairs with the [Project History](../../README.md#project-history) in the root README: the history is the *what/when* timeline; these ADRs are the *why*.

**Governance:** See [`../documentation-standards.md`](../documentation-standards.md) for when to create ADRs and how they relate to other documents.

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
| 2026-06-07 | [ADR Placement: Single Seed ADR in Samples, Decision Log at Root](2026-06-07-adr-placement.md) | Accepted |
| 2026-06-10 | [Cap-Hit Recovery Is Continuation: Slice Size Decoupled from Dispatch Budget](2026-06-10-cap-hit-recovery-is-continuation.md) | Accepted |
| 2026-06-10 | [Continue-Only Resume: SendMessage Allowlist as the Continuation Fast Path](2026-06-10-continue-only-resume.md) | Accepted |
