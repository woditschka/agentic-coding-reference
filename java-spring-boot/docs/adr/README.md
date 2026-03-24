# Architecture Decision Records

<!-- AGENT: ADRs optimized for agent consumption per docs/documentation.md -->
<!-- AGENT: Implementation tables use separate Type and File columns for parsing -->
<!-- AGENT: Reference format: [prd.md#req-xx-nnn](../prd.md#req-xx-nnn) -->

This directory contains Architecture Decision Records (ADRs) for this project.

ADRs document the path to decisions — the options considered, trade-offs evaluated, and rationale for the choice. The current state of all accepted decisions is reflected in [`system-design.md`](../system-design.md), which serves as the authoritative reference for implementation agents.

**Governance:** See [`documentation.md`](../documentation.md) for when to create ADRs and how they relate to other documents.

## Format

Each ADR is a markdown file named `YYYY-MM-DD-title-in-kebab-case.md`.

### Template

```markdown
# [Title]

**Status:** Proposed | Accepted | Deprecated | Superseded by [ADR-YYYY-MM-DD]

## Context

[Why is this decision needed? What problem are we solving?]

## Options Considered

1. **Option A** - [Brief description]
2. **Option B** - [Brief description]
3. **Option C** - [Brief description]

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

## Index

| Date | Decision | Status |
|------|----------|--------|
| 2026-03-22 | [Skill-Based Agent Architecture](2026-03-22-skill-based-agent-architecture.md) | Accepted |
