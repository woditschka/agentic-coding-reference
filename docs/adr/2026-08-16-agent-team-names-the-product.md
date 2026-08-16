# Agent-Team Names the Product; the Harness Stays the Machinery

**Status:** Accepted

## Context

Three names circulate for overlapping things: *the reference* (this repository), *the harness* (the runtime and its `/harness` source), and *agent-team* (the marketplace namespace unified on 2026-08-01). Consumer-facing surfaces mix the registers: the front door leads with the repository name, the project overview describes "a living reference" (`CLAUDE.md`), the adoption guide installs `agent-team-<stack>` plugins, and the architecture docs speak of "the harness". A first-time reader meets three names before meeting the thing they name. An external review of the repository (2026-08-16) independently flagged the conceptual surface a new reader must cross.

What a consumer adopts, installs, and converses with is the team of specialists — not the repository and not the source tree. The distribution already leads with `agent-team`; the prose does not.

## Options Considered

1. **Rename everything to agent-team** — retire "harness" across docs, scripts, and skills. Rejected: churn across `verify-harness.py`, `/harness`, the battery, and the decision log buys no consumer clarity; ADRs keep their decision-time voice regardless, so the old name survives in history either way.
2. **Keep the status quo** — three names, relationship undeclared. Rejected: the front door is the reader's first surface, so an undeclared vocabulary misleads from the first paragraph; the glossary owns every other term but not these three.
3. **Layered naming, declared once** — one register per audience, pinned in the glossary and stated on the front door. Chosen.

## Decision

**Each name keeps one register, and the front door declares the relationship.** *Agent-team* is the product: what a consumer installs, runs, and talks to — the leading name on consumer-facing surfaces (README front door, adoption guide, feature walkthrough, marketplace). *The harness* is the machinery inside it: runtime, routing, engines, schemas, and the `/harness` source — the standing term in architecture docs, ADRs, scripts, and maintainer tooling. *The reference* is this repository: it builds, measures, and distributes agent-team.

No file, script, or skill is renamed. The change is register, not identity: which name leads on which surface.

## Consequences

**Positive:** A first-screen reader meets one product name with the relationship stated. The glossary pins all three terms, so the register cannot drift silently. Zero mechanical churn.

**Negative:** Two names remain in active use, and the boundary between "consumer-facing" and "builder-facing" surfaces takes judgment at the margin — the glossary entries carry the tiebreaker.

## Implementation

README front door (product declaration paragraph), the [adoption guide](../adoption-guide.md)'s lead, [`glossary.md`](../glossary.md) entries **Agent-team**, **Harness**, **Reference**, and the [feature walkthrough](../feature-walkthrough.md)'s voice.

## References

- [ADR 2026-08-01: Shared Plugin Namespace](2026-08-01-shared-plugin-namespace.md) — the distribution unification this decision extends into prose
- [ADR 2026-08-14: The Root Is a Channel, Not an Author](2026-08-14-the-root-is-a-channel-not-an-author.md) — the same product-vs-machinery boundary, drawn for authorship rather than naming
