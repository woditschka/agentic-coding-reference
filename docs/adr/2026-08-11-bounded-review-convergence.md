# Bounded Review Convergence

**Status:** Accepted (`prior-critical` narrowed to the critical's surface by the [2026-09-03 amendment of 2026-07-14](2026-07-14-delta-sized-fix-cycles.md#amendment-2026-09-03-prior-critical-is-scoped-to-the-criticals-surface))

## Context

The pipeline bounds two of its three recovery ladders. Build failures re-triage at the third retry; truncation continuations re-triage at the third consecutive silent dispatch. Review fix rounds had no bound: any `fixable` finding bought a full fix dispatch plus a re-review, on every round, forever.

The failure shape is a loop cycling on progressively smaller findings — fix, re-review, new minor findings, fix — until interrupted from outside. The risk-proportional roster ([2026-07-09](2026-07-09-risk-proportional-review.md), [2026-07-14](2026-07-14-delta-sized-fix-cycles.md)) cut the cost *per round*; nothing cut the *number of rounds*. The bench's recorded runs peak at 2 rounds on v0.2.2–v0.2.4, so the bound is insurance against interactive-session tails, not a fix for measured sweeps. The 3–4-round tail sits on v0.1.x–v0.2.1, before the fix-cycle and cycle-reset ADRs landed.

The bound follows long-standing results, not intuition. Software-inspection studies find each further pass over the same artifact removes fewer defects, while fixes themselves inject new ones. Estimating the remaining defects to steer the loop is unreliable with a handful of reviewers. Industrial practice encodes the same conclusion: Google's published review standard tells reviewers to approve any change that clearly leaves code health better, perfect or not, marking residual polish as an ignorable nit ([eng-practices](https://google.github.io/eng-practices/review/reviewer/standard.html)). Measurements of language models sharpen it: unguided re-iteration degrades correct work more often than it improves it ([Huang et al. 2023](https://arxiv.org/abs/2310.01798)). Model reviewers keep producing plausible minor findings indefinitely, so finding supply can never be the stop signal. Control engineering supplies the vocabulary: a severity floor is a deadband against oscillating around the target. A hard bound substitutes for a convergence proof, and a loop that still is not converging belongs with a controller that has more options — the human.

## Options Considered

1. **Prose-only reviewer guidance.** State the critical-only rule in the review skill and rely on compliance. Rejected: the harness ran this experiment — the approved-with-autofix contradiction was prose first and became a Gate 4 bounce after the eval bench measured re-raised findings. A deadband implemented as a suggestion is not a deadband.
2. **Re-triage at the cap, mirroring the build ladder.** Rejected as the destination: a superseding `design-block` resets the review cycle, so the loop can recurse — full battery, fresh rounds — with no human in sight. Re-triage remains available, but as the human's deliberate choice.
3. **Adaptive stopping on estimated remaining defects or severity trend.** Rejected: such estimates are unreliable at this roster size, and a trend heuristic is not deterministic from the ledger. The route contract requires decisions replayable from records alone.
4. **Gate on the pass kind instead of a round counter** — "on a fix-delta pass, dissent requires a defect", reusing the plan engine's first/fix classification. Simpler, but it bounds review at two passes and removes the full-contract fix round entirely. Rejected: one unrestricted fix round is deliberate scope; the counter also feeds the board and the halt's context.
5. **A `layout.toml` depth knob.** Rejected for now: the cap joins the 3-retry cycle as a structural constant, not per-project configuration. One constant (`REVIEW_ROUND_CAP`) changes it if eval evidence ever warrants; a knob is doctor surface, doc surface, and drift surface before any project needs it.
6. **Deterministic ladder with channel escapes and per-loop ceilings** (chosen below).

## Decision

**A review cycle buys at most 3 fix rounds. From round 3, dissent requires a defect that must not merge — or an open channel. Every residual loop carries its own ceiling, and every stop lands with the human.**

- **Round counter.** The current pass's round is 1 (the initial pass) plus the number of earlier passes in the review cycle that drew substantive dissent from a roster reviewer. A pass is the window between consecutive `build-pass` records; dissent is judged on the latest `review-feedback` per reviewer in the window. Off-roster authors never count — the schema shape-checks names, not membership, so an unfiltered counter is forgeable. Truncation-only passes never advance the counter; a checkpoint record that also carries substantive findings does. Only a re-triage (superseding `design-block`) resets it, the same event that resets the cycle.
- **Critical-only gate.** From round `REVIEW_ROUND_CAP` (3), a non-approved verdict needs a `critical` fix-routable finding — severity's own question, "must this block merge?" — or a `clarify`, `escalate`, or `truncation` finding. The channels stay open at every round: a question and a human decision are never polish. Anything else bounces to its reviewer, once; a second below-bar record blocks for the human (`bounce-repeat`). Residual polish rides `recommendations` on an `approved` verdict — rendered by the board, read by the change-grader's hedging facet.
- **The stops.** One `blocked` rule, `review-non-convergence`, four causes: `round-cap` (substantive dissent past 3 fix rounds), `bounce-repeat`, `pass-churn` (a reviewer's third dissent record inside one pass — bounds the doc-autofix and outstanding-dissent loops, which never cross a `build-pass`), and `truncation-run` (three consecutive truncation-only passes). The human overrules, applies findings by hand, or orders the re-triage deliberately. A `round-cap` halt carrying `escalate` findings names them in context; root appends their escalations-file entries.
- **Visibility.** Reviewer dispatches carry `round`, and `finding_bar: "critical-only"` from round 3; root copies both into the dispatch prompt (the mapped-section relay). The board renders the ladder round in the slice header and each record's `recommendations` in the timeline.

## Consequences

- Worst-case review spend per cycle is bounded on every path: three fix rounds, plus per-loop ceilings on the bounce, the within-pass churn, and the truncation run.
- The shrinking-findings loop ends at round 3: its polish dissent bounces into an approval-with-recommendations, and disagreement blocks for the human. Only genuine critical dissent reaches round 4 and the `round-cap` halt.
- A round-3 critical finding trips the plan engine's `prior-critical` trigger, so the final round re-reviews cold with the full battery. The last round is the most expensive — accepted: it fires only when a defect that must not merge appeared late.
- Late-round polish moves from the dissent channel to `recommendations`, which now has readers: the board renders it, the grader's hedging facet weighs it. Quality drift, if any, shows there and in the bench's advisory judge — the next sweep measures it.
- Human-run review processes are bounded by response-time expectations and severity tags, with a human present to break loops. This pipeline asks for human attention only where a decision requires it; between those points no bystander watches, so it bounds by round count — a deliberate divergence.
- The depth stays a structural constant. If sweeps show round-3 passes yield nothing, tightening to 2 is a one-constant change plus this ADR's amendment.

## Implementation

- `harness/core/scripts/handoff/records.py` — `REVIEW_ROUND_CAP`.
- `harness/core/scripts/handoff/routing.py` — `_cycle_start` / `_windows` / `_cycle_round` / `_substantive_dissent` / `_capped_dissent_carrier`, the Gate 4 gate with its bounce ceiling, the four-cause `review-non-convergence` block, `round` / `finding_bar` dispatch context.
- `harness/core/scripts/handoff/view.py` — the ladder-round header span and the `recommendations` timeline lines (ANSI and Markdown).
- `harness/core/scripts/tests/handoff/test_routing.py` — the ladder suite (`TestReviewRoundConvergence`).
- `harness/core/.claude/skills/handoff-routing/route-spec.md` — § Review Non-Convergence, the Gate 4 bullet, the conditions-table rows, the prompt-context mapping.
- `harness/core/.claude/skills/review-workflow/SKILL.md` — § Review-Round Convergence; `reference.md` § Issue Classification note and § Processing Reviews step 9.
- `harness/core/.claude/skills/handoff-routing/SKILL.md` — the decision vocabulary, § Blocking, § Reviewer Stall Check.
- `harness/core/.claude/skills/change-grading/SKILL.md` — the hedging facet reads `recommendations`.
- `harness/core/schemas/scratch/review-feedback.schema.json` — the `severity` and `recommendations` descriptions.
- `docs/agentic-harness.md` and the installed copy, `docs/glossary.md` — the reviewer paragraph, the loop table, the structural-constants list, the recovery-table row (root doc only), the review-round entry.

## References

- [2026-07-09 Risk-Proportional Review](2026-07-09-risk-proportional-review.md) — the roster ladder this bound completes.
- [2026-07-14 Delta-Sized Fix Cycles](2026-07-14-delta-sized-fix-cycles.md) — per-round cost reduction; this ADR bounds the round count.
- [2026-08-07 The Review Cycle Survives Mid-Slice Design Records](2026-08-07-review-cycle-survives-mid-slice-design-records.md) — the cycle-start rule the counter reuses.
- [Google eng-practices, The Standard of Code Review](https://google.github.io/eng-practices/review/reviewer/standard.html) — approve-with-nits as the industrial norm.
- [Huang et al. 2023, Large Language Models Cannot Self-Correct Reasoning Yet](https://arxiv.org/abs/2310.01798) — ungrounded re-iteration degrades correct work.
