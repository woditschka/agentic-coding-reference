# Principles Over Rigid Rules in Harness Prose

**Status:** Accepted

## Context

Harness prose — agent personas, skills, and `docs/agentic-harness.md` — instructs the agents that run the pipeline. Two failure modes pull in opposite directions. Over-rigid prose lists cases and stops; when an agent meets a case the list never named, it guesses or stalls. Over-loose prose explains everything; it bloats context, raises token cost, and erodes the deterministic coordination the pipeline depends on.

Anthropic's [Claude constitution](https://www.anthropic.com/news/claude-new-constitution) faces the same tension and resolves it with a layered model: keep hard constraints for high-stakes behaviors, and for the rest explain *why* a behavior is wanted so the model generalizes. The article notes that rigid rules misfire when a situation falls outside what their authors foresaw, or when they are obeyed too literally.

The harness already explained the *why* in places — the "Design Is Discovered" section, the Confirmation Discipline, "Trust the Handoff." But the eight persona openings were thin, and core judgment surfaces — the six triage verdicts, the design-check tree, review tags, and security severity — stated the *what* with no *why*; others, like slice-sizing, already carried their rationale.

## Options Considered

1. **Status quo** — leave prose as a flat list of imperatives. Cheapest; weakest generalization at judgment surfaces.
2. **Constitution-style throughout** — rewrite all prose as narrative reasoning. Strongest generalization; breaks determinism and violates the project's terse writing standard.
3. **Layered split** — classify each instruction as hard contract or judgment; keep contracts imperative, attach one compact rationale clause to judgment instructions.

## Decision

We adopt option 3. Every harness instruction is one of two kinds:

- **Hard contract** — schema shapes, append-only records, `dispatch-start`-first, the routing-signal table, write scopes, the three harness invariants. Written as bare imperatives. Not softened.
- **Judgment** — classification, sizing, and escalate-or-proceed calls where no enumeration is complete. Each carries one compact rationale clause.

The taxonomy and its authoring rule live in [`agentic-harness.md`](../agentic-harness.md) § Principles Over Rigid Rules; the writing-standard reconciliation lives in [`documentation-standards.md`](../documentation-standards.md).

## Consequences

**Positive:**
- Judgment surfaces carry intent an agent can apply to an unlisted case. This is the design aim, not a measured result — the constitution notes principle-training is unproven, so revisit if behavior does not improve.
- The deterministic spine stays rigid; coordination correctness is unaffected.
- The split is a durable authoring rule applied to every future harness edit, enforced by the `audit-agents` § Principle Taxonomy check.

**Negative:**
- Judgment prose costs a few lines per instruction; the one-clause cap bounds the growth.
- Enriched personas add prose loaded on every dispatch; kept to a few tight sentences each and offset by cache reuse of the stable prefix.
- "Hard contract versus judgment" is itself a judgment call at the margin; the taxonomy lists the clear cases on each side.

## Implementation

**Non-goal:** This is a harness authoring decision, not a feature requirement of the project. Application lives in `.claude/agents/`, `.claude/skills/`, and `docs/agentic-harness.md`.

## References

- [Claude's Constitution](https://www.anthropic.com/news/claude-new-constitution) — the layered principles-over-rules model this ADR adapts
- [`agentic-harness.md`](../agentic-harness.md) — § Principles Over Rigid Rules (the taxonomy)
- [`documentation-standards.md`](../documentation-standards.md) — § Rationale Clauses for Judgment Instructions
- [`2026-03-22-skill-based-agent-architecture.md`](2026-03-22-skill-based-agent-architecture.md) — establishes the agents this rule governs
