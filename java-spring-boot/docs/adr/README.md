# Architecture Decision Records

<!-- AGENT: ADRs optimized for agent consumption per docs/documentation-standards.md -->
<!-- AGENT: Implementation tables use separate Type and File columns for parsing -->
<!-- AGENT: Reference format: [prd.md#req-xx-nnn](../prd.md#req-xx-nnn) -->

This directory contains Architecture Decision Records (ADRs) for this project.

ADRs document the path to decisions — the options considered, trade-offs evaluated, and rationale for the choice. The current state of all accepted decisions is reflected in [`system-design.md`](../system-design.md), which serves as the authoritative reference for implementation agents.

**Governance:** See [`documentation-standards.md`](../documentation-standards.md) for when to create ADRs and how they relate to other documents.

## Format

Each ADR is a markdown file named `YYYY-MM-DD-title-in-kebab-case.md`.

### Template

```markdown
# [Title]

**Status:** Proposed | Accepted | Deprecated | Superseded by [ADR-YYYY-MM-DD]

## Context

[Why is this decision needed? What problem are we solving?]

## Options Considered

1. **Option A** — [Brief description]
2. **Option B** — [Brief description]
3. **Option C** — [Brief description]

## Decision

[What did we choose and why?]

## Consequences

[What are the results? Both positive and negative.]

## Implementation

**Requirements:** REQ-XX-NNN

## References

- [system-design.md#section](../system-design.md#section) — description
- [REQ-XX-NNN: Name](../prd.md#req-xx-nnn-name)
```

### Guidelines

- One decision per file
- Document the path: what options existed, why we chose this one
- Keep it concise: aim for under 60 lines
- Write in present tense ("We use X" not "We will use X")
- Link to related ADRs when decisions interact
- Reference the system-design.md section where this decision is implemented
- Update status when decisions change; don't delete old ADRs

### Non-Goal ADRs

A non-goal ADR records a *product* decision not to build something — distinct from an architectural ADR. Two conventions apply:

- **Filename:** `YYYY-MM-DD-non-goal-<slug>.md` — the `non-goal-` infix is load-bearing because the product-requirements-expert agent's write scope matches this pattern; standard ADRs remain owned by system-design-expert.
- **Implementation section:** use `**Non-goal:** NG-X` (referencing the PRD's Non-Goals table) instead of `**Requirements:** REQ-XX-NNN`.

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
