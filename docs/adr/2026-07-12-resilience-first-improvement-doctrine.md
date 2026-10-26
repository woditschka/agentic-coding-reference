# Improvement Proposals Are Judged by Enforcement, With Cost as Tiebreaker

**Status:** Accepted

## Context

Multi-angle reviews of the harness produce competing proposals: trim dispatch context, deduplicate contracts, relocate rules, retire surfaces. The token savings are cents per slice under prompt caching. The same reviews find drift channels policed by audit checks instead of removed by construction. Without a recorded rule, each review re-derives the same judgment and risks trading it differently.

Outside reviews add a second force. A settled decision that is re-examined only when its context changes suppresses a stronger argument on the same context, so hand-run outside reviews surface decisions the encoded review never questions. An external review on 2026-08-16 rated the architecture strong and made ten recommendations; a declined one needs a recorded disposition, or the next review re-litigates it. The deciding constraints: a single-maintainer budget where an eval rep costs $4–19, Claude Code as the primary target, and the kernel's admission test.

## Options Considered

1. **Judge each proposal ad hoc.** Rejected: five reviews re-derived the same reasoning; repeated cost and drift in judgment.
2. **Cost-driven optimization**, accepting any token saving with plausible quality survival. Rejected: output quality and pipeline autonomy are project invariants, never traded.
3. **Re-examine a settled decision only on changed context.** Rejected: a stronger argument without new context was suppressed, and outside reviews kept finding it.
4. **A skill-local disposition file** for review findings. Rejected: accepted-but-unlanded work resurfaces on its own, and re-deriving a small rejection costs one skeptic pass.
5. **Resilience-first doctrine, rebuttable presumption, dispositions in the decision log** (chosen).

## Decision

**Every improvement proposal is judged by its effect on enforcement, not by its token delta.**

- **Invariants.** Output quality and pipeline autonomy are non-negotiable. No change weakens a behavioral guarantee or adds a human touchpoint to save cost.
- **Enforcement tiers.** A rule is enforced by deterministic code, by co-loaded text, or by an on-demand pointer, in strictly descending strength.
- **Classification.** Each proposal is one of three kinds. A *deduplication* turns N hand-synced copies into one source plus derivation. A *relocation* moves text nearer its use, tier unchanged. A *demotion* drops a rule a tier.
- **Rule.** Deduplication is accepted on its own merit. Relocation is accepted when the consumer provably loads the target. Demotion is accepted only when code enforces the rule underneath, or a measured before/after run proves quality holds.
- **Identity test.** Deduplication applies only where a contract forces the copies identical. Where prose legitimately diverges, the shared vocabulary or section roster is gated instead of the text rendered. Verify the measured delta shape before accepting the structural work.
- **Anchor rule.** Every removed text copy leaves a named pointer (`skill § section`) where it stood, so cuts stay reversible.
- **Cost is a tiebreaker.** Token savings order otherwise-equal options; they never justify a demotion alone.
- **Rebuttable presumption.** A settled decision is challenged when the challenge engages the recorded rationale: what changed, or what the rationale missed. A challenge bringing no new argument is suppressed at synthesis and named in the report, never dropped silently. `/review-harness challenge` drops the ADR anchoring from the agent prompts; agents judge against the README's stated philosophy, and synthesis cites each challenged ADR for the disposition, never for suppression. This doctrine is challengeable under the same bar.
- **Dispositions land in the decision log.** A finding that outlives its report gets one of four dispositions in `docs/adr/`. They are landed, queued, deferred with a trigger, or declined with a reason. A rejection below ADR grain lives only in its report.

The 2026-08-16 external review's dispositions, as they stand:

| Recommendation | Disposition |
|---|---|
| A request-to-merge walkthrough | Landed: `docs/feature-walkthrough.md` narrates a committed eval run |
| Per-kind cost judgment | Landed: the rise verdict scopes to the task's declared `kind` (`evals/README.md` § Cost accounting) |
| Routing state table generated from the source, plus routing invariant tests | Landed: `handoff-routing/route-rules.md`, rendered by `harness/render-route-rules.py`; `RoutingInvariants` in `scripts/tests/handoff/test_routing.py` |
| Handbook legibility pass (Level-1 openers) | Queued, after the routing table |
| A Go SUT and broader eval task diversity | Deferred; trigger: the first Go-stack harness change needing eval feedback |
| Continuous cross-tool conformance | Deferred; a manual smoke check when cross-tool surfaces change, no standing accounts or CI |
| Bootstrap confidence intervals, p50/p90 | Declined: meaningless at 3–6 reps per cell; ledger-named mechanism attribution stays the practice |
| Runtime profiles (`core`/`team`/`full`) | Declined: contradicts the kernel admission test and multiplies the tested surface |
| Generated `AGENTS.md` shims | Declined: every supported tool reads `CLAUDE.md`; revisit when a target tool does not |
| Go/Java build jobs in server-side CI | Declined: the samples build locally and the bench exercises the Java stack |
| Router code generated from a declarative source | Declined: the table and docs generate from the source; the router stays hand-written, typed, `assert_never`-exhausted |

API stabilization toward 1.0 is accepted as direction: reduce contract churn before widening the roster.

## Consequences

**Positive:**

- Drift-policing audit checks shrink as their duplicated targets collapse into single sources.
- Cheap-but-risky context trims are blocked by rule rather than re-litigated per review.
- A declined recommendation carries its reason, so the next review argues against a recorded position.

**Negative:**

- Demotions carry a measurement cost: a golden-slice before/after run precedes that class of change.
- Anti-churn is weaker by one grain: a sub-ADR rejection costs one skeptic pass to re-derive.
- Deferred items depend on their triggers being noticed; nothing mechanical watches for them.

## Implementation

The `review-harness` root skill applies the doctrine to every finding and runs the challenge mode; `audit-harness` gates defects against the current bar. Dispositions land as an ADR or an ADR edit with rejected alternatives under § Options Considered.

## References

- [Deterministic routing engines](2026-07-02-deterministic-routing-engines.md) — the top enforcement tier in practice: code outranks prose, and the router stays hand-written.
- [The handoff ledger](2026-05-08-the-handoff-ledger.md) — the external review's concurrency finding, decided as lock-free appends.
- [Materialize](2026-06-11-materialize.md) — the external review's install-verification finding, decided as exact-module verification.
- [The eval bench](2026-07-15-the-eval-bench.md) — the per-rep cost and the per-kind rise verdict the dispositions lean on.
- [The decision log](2026-06-07-the-decision-log.md) — where dispositions that outlive a report land.
- [Tiered maintainer workflow](2026-07-02-tiered-maintainer-workflow.md) — the loop in which `review-harness` and `audit-harness` run.
- `docs/feature-walkthrough.md`, `evals/README.md` — the two landed documentation dispositions.
