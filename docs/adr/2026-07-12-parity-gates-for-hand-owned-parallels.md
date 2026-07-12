# Roster and Vocabulary Gates for Hand-Owned Parallel Files

**Status:** Accepted

## Context

The stacks carry hand-owned parallel files that legitimately diverge: the GoLand/IntelliJ skill trio and the three per-stack review checklists. Measured deltas are product tokens interleaved inside doctrine sentences, plus deliberate stack adaptations. Their contract-bearing parts — section rosters, feedback tags, severity levels — must not drift, yet no battery step gates them.

## Options Considered

1. **Whole-document render**, per the mirror-bodies precedent. Rejected: the similarity is ancestry, not contract; every genuine divergence becomes an overlay exception, coupling what evolves apart.
2. **Strict text-equality gates on shared sections.** Rejected: verification found product tokens inside doctrine sentences and legitimate content divergence; equality forces false parallels or a growing whitelist.
3. **No gate.** Rejected: discipline has held (one shared edit since both IDE skills exist), but the shared tokens are contract-bearing — a drifted feedback tag breaks review processing silently.
4. **Roster and vocabulary parity gates** (chosen).

## Decision

**Hand-owned parallel files are gated at the level a contract forces identical — section rosters and shared vocabularies, never prose.** Three checks join the battery:

- The GoLand and IntelliJ IDE skills carry the same `##` section roster. A product-prose heading pair may be pinned as expected divergence, scoped to its file pair. Editing either heading fails the gate until the pin is updated — an edit-reviewed decision, not a growing whitelist.
- Feedback tags used in any stack skill belong to the canonical set in core `review-workflow` § Feedback Tags.
- The severity-level headings match across the three `security-review` copies.

## Consequences

- A doctrine section added to one IDE skill without its twin fails the battery.
- Prose stays free to diverge per stack; a legitimate divergence never fights a template.
- Sentence-level drift inside shared doctrine stays discipline-covered; revisit gating there if an edit ever ships one-sided.

## Implementation

The checks join `harness/check-sync.py`'s parity family.

## References

- [Resilience-First Doctrine for Harness Improvements](2026-07-12-resilience-first-improvement-doctrine.md) — this decision applies its identity test: gate rosters and vocabularies where prose legitimately diverges.
- [Rendered Agent Mirror Bodies](2026-07-03-rendered-agent-mirror-bodies.md) — the render precedent; it covers contract-identical copies, which these files are not.
