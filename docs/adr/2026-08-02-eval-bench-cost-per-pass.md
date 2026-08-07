# The Eval Bench Measures Cost per Pass Against a Fixed SUT, per Version

**Status:** Accepted

## Context

Claims about the harness rested on Harness Stats session snapshots — real numbers, no controlled comparison. A release needed an answer to one question: does harness version X beat version Y on the same work, at what cost? Any credible answer must survive agent-influenced artifacts: the pipeline under test writes the ledger, the docs, and the patch the measurement reads.

## Options Considered

1. **Composite quality score across facets** — one headline number per run. Rejected: it hides which tier moved, and mixes machine-verified facts with judge opinion.
2. **LLM judge inside the pass bar** — quality gates on graded scores. Rejected: the cost series would inherit judge noise; a rubric or model change would silently break the series.
3. **Partition the trend by SUT epoch, re-running versions per base update** — comparisons only within one base commit. Rejected: the operator does not re-run versions when the base moves; permanent partitions would render one row per section forever. The epoch stays recorded per run, and a multi-base record is called out in the trend.
4. **Discard obviously broken runs** — keep the series clean by operator judgment. Rejected: a discard mechanism is a thumb on the scale. Only two pre-commit exceptions exist: a run that never engaged the harness (infrastructure defect) and a task later shown defective.
5. **Cost per pass over a binary machine-verified bar, disaggregated tiers** (chosen).

## Decision

**The bench measures cost per pass: agent spend per repetition clearing a binary, machine-verified quality bar.** Frozen tasks with held-out oracles run against one fixed SUT (spring-petclinic); each harness version installs from its own tag via the marketplace channel. The bar is oracle-pass plus suite-green plus run-complete — never a judge score. Metrics stay disaggregated in three tiers: A (machine-verified, carries claims), B (deterministic proxies, context only), C (blind LLM judge, advisory only). Tier C runs blind — sanitized patch, pinned rubric and model, median of independent samples — and may run post-hoc from the committed record. Run folders are the ground truth; `TREND.md` is derived and deterministic, and every rendered field is scrubbed because run-folder bytes are agent-influenceable.

## Consequences

- Version comparisons are grounded: same tasks, same bar, recorded spend — at the price of statistical power (three tasks, few reps).
- A cross-version delta can include SUT drift; the per-run manifests attribute it.
- Measurement spend (the judge) never enters the metric it measures.

## Implementation

`evals/` — `run_eval.py` (runner), `summarize.py` (trend), `tasks/`, `judge/`, committed run folders under `results/`. Methodology detail: `evals/README.md`.

## References

- [Resilience-First Doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — the bench supplies the measured evidence that doctrine's demotion bar demands.
- [Single Pricing Source as a Gated Vendored Copy](2026-07-13-single-pricing-source-vendored-copy.md) — the accounting engine the bench reuses for transcript-derived spend.
- [The Default Permission Posture Is Auto Mode, Not Skip](2026-07-31-auto-permission-mode-default.md) — the claude-dev confinement the bench runs agents (and the judge) inside.
