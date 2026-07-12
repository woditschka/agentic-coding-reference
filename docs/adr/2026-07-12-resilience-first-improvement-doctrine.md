# Resilience-First Doctrine for Harness Improvements

**Status:** Accepted

## Context

Repeated multi-angle reviews of the harness produce competing proposals: trim dispatch context, deduplicate contracts, relocate rules, retire surfaces. Measured token savings are small — cents per slice with prompt caching. The same reviews found drift channels policed by audit checks instead of removed by construction. Each review re-derived the same judgment from scratch, with no recorded rule to hold it steady.

## Options Considered

1. **Judge each proposal ad hoc** — flexible, but five reviews re-derived the same reasoning and risked inconsistent trades. Rejected: repeated cost, drift in judgment.
2. **Cost-driven optimization** — accept any token saving with plausible quality survival. Rejected: violates the project invariants; output quality and pipeline autonomy are never traded away.
3. **Resilience-first doctrine with cost as tiebreaker** (chosen).

## Decision

**Every improvement proposal is judged by its effect on enforcement, not by its token delta.**

- **Invariants.** Output quality and pipeline autonomy are non-negotiable. No change may weaken a behavioral guarantee or add a human touchpoint to save cost.
- **Enforcement tiers.** A rule is enforced by deterministic code, by co-loaded text (in context when the rule fires), or by an on-demand pointer — in strictly descending strength.
- **Classification.** Each proposal is a *deduplication* (N hand-synced copies become one source plus derivation), a *relocation* (text moves nearer its point of use, tier unchanged), or a *demotion* (a rule drops a tier).
- **Rule.** Deduplication is accepted on its own merit: it removes drift by construction. Relocation is accepted when the consumer provably loads the target. Demotion is accepted only when code enforces the rule underneath, or a measured before/after run proves quality holds.
- **Identity test.** Deduplication applies only where a contract forces the copies identical. Similarity by ancestry is not identity by contract: where prose legitimately diverges, gate the shared vocabulary or section roster instead of rendering the text. Verify the measured delta shape before accepting the structural work.
- **Anchor rule.** Every removed text copy leaves a named pointer (`skill § section`) where it stood, so cuts stay reversible and reviewable.
- **Cost is a tiebreaker.** Token savings order otherwise-equal options; they never justify a demotion alone.

## Consequences

- Drift-policing audit checks shrink as their duplicated targets collapse into single sources.
- Cheap-but-risky context trims are blocked by rule rather than re-litigated per review.
- Demotions gain a measurement cost: a golden-slice before/after run must precede that class of change.

## Implementation

The `review-harness` root skill applies this doctrine to every finding it reports. Dispositions that outlive the report land in `docs/adr/` — a new ADR or an amendment — with rejected alternatives in § Options Considered. A skill-local disposition file was rejected: accepted-but-unlanded work re-surfaces on its own, and re-deriving a small rejection costs one skeptic pass.

## References

- [Deterministic Mid-Slice Routing via handoff.py route](2026-07-06-deterministic-mid-slice-routing.md) — the tier model generalizes this move: code enforcement outranks prose.
- [Executable Pipeline Contracts](2026-07-02-executable-pipeline-contracts.md) — prior art for contracts-in-code over synchronized prose.
- [Rendered Agent Mirror Bodies](2026-07-03-rendered-agent-mirror-bodies.md) — the deduplication class's precedent: derivation replacing hand-synced copies.
