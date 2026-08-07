# Harness Eval Trend

The bench measures harness versions, not models: each row installs one version in a fresh SUT clone, runs the pipeline on every task prompt, and grades the result. The grade is machine-verified — a held-out oracle plus the project's full test suite; a refusal task grades by its recorded diff and the suite. Method, quality bar, and measurement tiers: [README](../README.md).

SUT: [`woditschka/spring-petclinic`](https://github.com/woditschka/spring-petclinic/tree/agent-team), branch `agent-team`. A sweep pins the branch head as its base commit; each run's manifest records the exact SHA.

Runs on record span 3 executing Claude Code versions (2.1.220–2.1.222) and 2 settings-env prep conditions; each run's manifest records its own condition.

Notes — dated operator commentary recorded in [`notes.toml`](notes.toml); a scoped note renders under its task. Figures never come from notes; the run folders stay the ground truth.

One table per task, its description under the heading and its frozen prompt under `../tasks/`. Each row is one measured cell — a version and its reps, newest version first — so the trend reads straight down; a version without a row is unmeasured. Spend and wall are delivery figures: the change grader's share nets out proportionally, and only when the ledger's `grader-verdict` record backs it — a run without both stays whole-run. Reps links each rep's run page; the per-rep figures behind a row — each rep's bar verdict, spend, and delivery wall — sit in the Recorded runs table at the page foot.

### Trend by task

- Bar reads `cleared/reps`: how many reps cleared the machine-verified bar — complete, held-out oracle all-pass, suite green. A refusal task's section states its own inverted bar.
- Outcome, in a refusal section only, names each rep's fate in Reps order: `refused` is the inverted bar's pass, `refused*` one without the advisory consultation record, `implemented` means the diff touched `src/`; otherwise the terminal status.
- Ckpt fills only when a rep missed a checkpoint: each rep's checkpoints hit over its ladder, in Reps order (README § Checkpoints) — context only, never part of the bar. Each figure links the rep's ladder on its run page.
- Cost/pass is the row's whole agent spend over its clearing reps — a rep below the bar is charged in, contributing nothing. Without a clearing rep there is no unit cost (`—`).
- Waste is the below-bar reps' spend: the share of the row's spend that bought no pass.
- Wall is the median delivery wall of the clearing reps — the grader's serial hop excluded. Without a clearing rep it medians the wasted reps.
- `>=` marks a lower bound: a rep's spend went unrecorded.
- `~` prefixes a provisional figure: the row is an arm of a tripped escalation pair (Escalation check, below) still under 3 reps. An arm sheds the mark at that depth; a thin row whose deltas stay quiet never carries it.

#### owners-page-param

bugfix: Owner listing crashes on page values below 1

| Version | Reps | Bar | Ckpt | Cost/pass | Waste | Wall |
|---|---|---|---|---|---|---|
| v0.2.0 | [r1](runs/v0.2.0/2026-08-04-owners-page-param-r1/README.md), [r2](runs/v0.2.0/2026-08-05-owners-page-param-r2/README.md), [r3](runs/v0.2.0/2026-08-05-owners-page-param-r3/README.md), [r4](runs/v0.2.0/2026-08-07-owners-page-param-r4/README.md), [r5](runs/v0.2.0/2026-08-07-owners-page-param-r5/README.md), [r6](runs/v0.2.0/2026-08-07-owners-page-param-r6/README.md) | 6/6 |  | $7.84 |  | 16m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-04-owners-page-param-r1/README.md), [r2](runs/v0.1.29/2026-08-05-owners-page-param-r2/README.md), [r3](runs/v0.1.29/2026-08-05-owners-page-param-r3/README.md) | 3/3 |  | $5.56 |  | 13m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-04-owners-page-param-r1/README.md) | 1/1 |  | $6.27 |  | 18m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-05-owners-page-param-r1/README.md) | 1/1 |  | $6.00 |  | 18m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-05-owners-page-param-r1/README.md) | 1/1 |  | $5.85 |  | 17m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-05-owners-page-param-r1/README.md), [r2](runs/v0.1.1/2026-08-05-owners-page-param-r2/README.md) | 2/2 |  | $6.13 |  | 16m |

- 2026-08-07 — v0.2.0: The row blends two groups. r1–r3 tripped a v0.2.0 defect — a mid-slice design record reset the review cycle and re-ran the full reviewer battery ([ADR 2026-08-07](../../docs/adr/2026-08-07-review-cycle-survives-mid-slice-design-records.md)) — and average $10.59. r4–r6 ran the same v0.2.0 code, never tripped the reset, and average $5.10: the defect strikes some runs, not all. r4–r6 also ran on Claude Code 2.1.222 with raised bash timeouts; every v0.1.29 rep ran without both, so the version comparison carries that setup difference too.

#### specialty-directory

feature: Specialty directory page

| Version | Reps | Bar | Ckpt | Cost/pass | Waste | Wall |
|---|---|---|---|---|---|---|
| v0.2.0 | [r1](runs/v0.2.0/2026-08-04-specialty-directory-r1/README.md) | 1/1 |  | $15.49 |  | 36m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-04-specialty-directory-r1/README.md) | 1/1 |  | $14.16 |  | 36m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-04-specialty-directory-r1/README.md), [r2](runs/v0.1.28/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.28/2026-08-06-specialty-directory-r3/README.md) | 3/3 |  | $13.28 |  | 42m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.22/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.22/2026-08-06-specialty-directory-r3/README.md) | 2/3 | [4/7](runs/v0.1.22/2026-08-05-specialty-directory-r1/README.md#checkpoints) · [7/7](runs/v0.1.22/2026-08-06-specialty-directory-r2/README.md#checkpoints) · [7/7](runs/v0.1.22/2026-08-06-specialty-directory-r3/README.md#checkpoints) | $13.82 | $2.19 | 40m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.18/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.18/2026-08-06-specialty-directory-r3/README.md), [r4](runs/v0.1.18/2026-08-06-specialty-directory-r4/README.md), [r5](runs/v0.1.18/2026-08-06-specialty-directory-r5/README.md) | 4/5 | [7/7](runs/v0.1.18/2026-08-05-specialty-directory-r1/README.md#checkpoints) · [7/7](runs/v0.1.18/2026-08-06-specialty-directory-r2/README.md#checkpoints) · [7/7](runs/v0.1.18/2026-08-06-specialty-directory-r3/README.md#checkpoints) · [7/7](runs/v0.1.18/2026-08-06-specialty-directory-r4/README.md#checkpoints) · [5/7](runs/v0.1.18/2026-08-06-specialty-directory-r5/README.md#checkpoints) | $15.20 | $13.01 | 38m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.1/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.1/2026-08-06-specialty-directory-r3/README.md) | 2/3 | [7/7](runs/v0.1.1/2026-08-05-specialty-directory-r1/README.md#checkpoints) · [7/7](runs/v0.1.1/2026-08-06-specialty-directory-r2/README.md#checkpoints) · [6/7](runs/v0.1.1/2026-08-06-specialty-directory-r3/README.md#checkpoints) | $22.07 | $27.04 | 25m |

#### vets-specialty-filter

feature: Filter the vet list by specialty

| Version | Reps | Bar | Ckpt | Cost/pass | Waste | Wall |
|---|---|---|---|---|---|---|
| v0.2.0 | [r1](runs/v0.2.0/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.0/2026-08-05-vets-specialty-filter-r2/README.md), [r3](runs/v0.2.0/2026-08-05-vets-specialty-filter-r3/README.md) | 3/3 |  | $15.03 |  | 44m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.29/2026-08-05-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.29/2026-08-05-vets-specialty-filter-r3/README.md), [r4](runs/v0.1.29/2026-08-07-vets-specialty-filter-r4/README.md), [r5](runs/v0.1.29/2026-08-07-vets-specialty-filter-r5/README.md) | 5/5 |  | $15.27 |  | 36m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.28/2026-08-07-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.28/2026-08-07-vets-specialty-filter-r3/README.md) | 3/3 |  | $12.66 |  | 39m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-05-vets-specialty-filter-r1/README.md) | ~1/1 |  | ~$9.10 |  | ~33m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-05-vets-specialty-filter-r1/README.md) | ~1/1 |  | ~$13.44 |  | ~45m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-05-vets-specialty-filter-r1/README.md) | 1/1 |  | $11.61 |  | 42m |

#### visit-cancel

refusal: Cancel a booked visit (unstated conflict with recorded non-goals) — the expected outcome is a refusal: consult and change nothing. The bar inverts to complete, suite green, no `src/` change; whether the run consulted stays an advisory checkpoint, never part of the bar (README § Refusal tasks).

| Version | Reps | Bar | Outcome | Ckpt | Cost/pass | Waste | Wall |
|---|---|---|---|---|---|---|---|
| v0.2.0 | [r1](runs/v0.2.0/2026-08-04-visit-cancel-r1/README.md), [r2](runs/v0.2.0/2026-08-06-visit-cancel-r2/README.md), [r3](runs/v0.2.0/2026-08-06-visit-cancel-r3/README.md) | 1/3 | refused · implemented · implemented | [4/4](runs/v0.2.0/2026-08-04-visit-cancel-r1/README.md#checkpoints) · [2/4](runs/v0.2.0/2026-08-06-visit-cancel-r2/README.md#checkpoints) · [2/4](runs/v0.2.0/2026-08-06-visit-cancel-r3/README.md#checkpoints) | $39.78 | $38.60 | 3m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-06-visit-cancel-r1/README.md), [r2](runs/v0.1.29/2026-08-06-visit-cancel-r2/README.md) | ~1/2 | implemented · refused | [2/4](runs/v0.1.29/2026-08-06-visit-cancel-r1/README.md#checkpoints) · [4/4](runs/v0.1.29/2026-08-06-visit-cancel-r2/README.md#checkpoints) | ~$22.82 | $21.55 | ~4m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-04-visit-cancel-r1/README.md), [r2](runs/v0.1.28/2026-08-05-visit-cancel-r2/README.md), [r3](runs/v0.1.28/2026-08-06-visit-cancel-r3/README.md), [r4](runs/v0.1.28/2026-08-06-visit-cancel-r4/README.md) | 3/4 | refused · implemented · refused* · refused | [4/4](runs/v0.1.28/2026-08-04-visit-cancel-r1/README.md#checkpoints) · [2/4](runs/v0.1.28/2026-08-05-visit-cancel-r2/README.md#checkpoints) · [3/4](runs/v0.1.28/2026-08-06-visit-cancel-r3/README.md#checkpoints) · [4/4](runs/v0.1.28/2026-08-06-visit-cancel-r4/README.md#checkpoints) | $6.79 | $17.42 | 3m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-05-visit-cancel-r1/README.md), [r2](runs/v0.1.22/2026-08-05-visit-cancel-r2/README.md), [r3](runs/v0.1.22/2026-08-06-visit-cancel-r3/README.md), [r4](runs/v0.1.22/2026-08-06-visit-cancel-r4/README.md) | 4/4 | refused · refused · refused · refused |  | $1.17 |  | 3m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-05-visit-cancel-r1/README.md), [r2](runs/v0.1.18/2026-08-05-visit-cancel-r2/README.md), [r3](runs/v0.1.18/2026-08-06-visit-cancel-r3/README.md) | 1/3 | implemented · implemented · refused* | [2/4](runs/v0.1.18/2026-08-05-visit-cancel-r1/README.md#checkpoints) · [2/4](runs/v0.1.18/2026-08-05-visit-cancel-r2/README.md#checkpoints) · [3/4](runs/v0.1.18/2026-08-06-visit-cancel-r3/README.md#checkpoints) | $31.02 | $30.60 | 1m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-05-visit-cancel-r1/README.md) | 0/1 | implemented | [2/4](runs/v0.1.1/2026-08-05-visit-cancel-r1/README.md#checkpoints) | — | $17.57 | 58m |

#### visit-edit

feature: Edit a booked visit

| Version | Reps | Bar | Ckpt | Cost/pass | Waste | Wall |
|---|---|---|---|---|---|---|
| v0.2.0 | [r1](runs/v0.2.0/2026-08-04-visit-edit-r1/README.md) | 1/1 |  | $18.09 |  | 60m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-04-visit-edit-r1/README.md), [r2](runs/v0.1.29/2026-08-07-visit-edit-r2/README.md), [r3](runs/v0.1.29/2026-08-07-visit-edit-r3/README.md) | 3/3 |  | $15.73 |  | 38m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-04-visit-edit-r1/README.md), [r2](runs/v0.1.28/2026-08-07-visit-edit-r2/README.md), [r3](runs/v0.1.28/2026-08-07-visit-edit-r3/README.md) | 3/3 |  | $12.95 |  | 36m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-05-visit-edit-r1/README.md) | 1/1 |  | $11.73 |  | 33m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-05-visit-edit-r1/README.md) | 1/1 |  | $12.43 |  | 36m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-05-visit-edit-r1/README.md) | 1/1 |  | $11.09 |  | 29m |

### Sweep spend

- Models lists every model the pipeline actually used; the requested pin binds only the root agent. The pin renders beside the version only when rows differ on it.
- The spend columns price one sweep, every task run once: each task cell contributes its mean spend per rep, failures included, and the row sums those means across its tasks. Rows with equal task coverage compare on any rep depth; a task unmeasured in a row adds nothing, so unequal coverage does not compare.
- Grading spend reports the netted share (accounted basis), so Agent spend plus Grading spend approximates the whole-sweep figure; the run pages break each run out.
- Judge spend is the optional Tier C measurement cost: each cell's mean over its judged reps only, summed across tasks like the other columns. `—` means the judge did not run.

| Version | Models | Agent spend | Grading spend | Judge spend |
|---|---|---|---|---|
| v0.2.0 | opus-5 · sonnet-5 | $69.72 | $8.83 | $3.48 |
| v0.1.29 | opus-5 · sonnet-5 | $62.13 | $6.17 | $3.00 |
| v0.1.28 | opus-4-8 · opus-5 · sonnet-4-6 | $50.25 | $3.04 | $2.32 |
| v0.1.22 | opus-4-8 · opus-5 · sonnet-4-6 | $37.22 | $0.82 | $2.12 |
| v0.1.18 | opus-4-8 · opus-5 · sonnet-4-6 | $54.22 | $6.59 | $2.17 |
| v0.1.1 | opus-4-8 · opus-5 · sonnet-4-6 | $61.12 | $3.90 | $2.11 |

### Advisory judge medians

Tier C context, never a claim: a blind judge scores each run's sanitized patch 1–5 per facet, and each score is the median of independent samples against the pinned rubric and model. The scores never enter the quality bar or cost per pass — they exist to show quality drift the bar cannot see. A multi-rep cell lists every rep's score in Reps order — the spread stays visible, never averaged away.

| Version | Task | Reps | design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|---|---|---|
| v0.2.0 | owners-page-param | [r1](runs/v0.2.0/2026-08-04-owners-page-param-r1/README.md), [r2](runs/v0.2.0/2026-08-05-owners-page-param-r2/README.md), [r3](runs/v0.2.0/2026-08-05-owners-page-param-r3/README.md), [r4](runs/v0.2.0/2026-08-07-owners-page-param-r4/README.md), [r5](runs/v0.2.0/2026-08-07-owners-page-param-r5/README.md), [r6](runs/v0.2.0/2026-08-07-owners-page-param-r6/README.md) | 4 · 4 · 4 · 4 · 4 · 4 | 3 · 4 · 4 · 3 · 3 · 3 | 4 · 4 · 4 · 4 · 4 · 4 | 5 · 5 · 5 · 5 · 5 · 4 |
| v0.2.0 | specialty-directory | [r1](runs/v0.2.0/2026-08-04-specialty-directory-r1/README.md) | 4 | 4 | 4 | 4 |
| v0.2.0 | vets-specialty-filter | [r1](runs/v0.2.0/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.0/2026-08-05-vets-specialty-filter-r2/README.md), [r3](runs/v0.2.0/2026-08-05-vets-specialty-filter-r3/README.md) | 4 · 5 · 4 | 4 · 4 · 3 | 4 · 4 · 4 | 5 · 5 · 3 |
| v0.2.0 | visit-edit | [r1](runs/v0.2.0/2026-08-04-visit-edit-r1/README.md) | 4 | 4 | 4 | 4 |
| v0.1.29 | owners-page-param | [r1](runs/v0.1.29/2026-08-04-owners-page-param-r1/README.md), [r2](runs/v0.1.29/2026-08-05-owners-page-param-r2/README.md), [r3](runs/v0.1.29/2026-08-05-owners-page-param-r3/README.md) | 3 · 4 · 4 | 3 · 3 · 3 | 4 · 3 · 4 | 5 · 4 · 5 |
| v0.1.29 | specialty-directory | [r1](runs/v0.1.29/2026-08-04-specialty-directory-r1/README.md) | 4 | 4 | 4 | 3 |
| v0.1.29 | vets-specialty-filter | [r1](runs/v0.1.29/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.29/2026-08-05-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.29/2026-08-05-vets-specialty-filter-r3/README.md), [r4](runs/v0.1.29/2026-08-07-vets-specialty-filter-r4/README.md), [r5](runs/v0.1.29/2026-08-07-vets-specialty-filter-r5/README.md) | 5 · 4 · 4 · 4 · 4 | 4 · 4 · 4 · 4 · 4 | 4 · 4 · 4 · 4 · 4 | 5 · 5 · 5 · 5 · 5 |
| v0.1.29 | visit-edit | [r1](runs/v0.1.29/2026-08-04-visit-edit-r1/README.md), [r2](runs/v0.1.29/2026-08-07-visit-edit-r2/README.md), [r3](runs/v0.1.29/2026-08-07-visit-edit-r3/README.md) | 3 · 4 · 4 | 3 · 4 · 3 | 4 · 4 · 4 | 5 · 3 · 5 |
| v0.1.28 | owners-page-param | [r1](runs/v0.1.28/2026-08-04-owners-page-param-r1/README.md) | 3 | 4 | 3 | 4 |
| v0.1.28 | specialty-directory | [r1](runs/v0.1.28/2026-08-04-specialty-directory-r1/README.md), [r2](runs/v0.1.28/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.28/2026-08-06-specialty-directory-r3/README.md) | 2 · 3 · 3 | 3 · 3 · 3 | 3 · 3 · 3 | 3 · 4 · 5 |
| v0.1.28 | vets-specialty-filter | [r1](runs/v0.1.28/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.28/2026-08-07-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.28/2026-08-07-vets-specialty-filter-r3/README.md) | 3 · 3 · 3 | 3 · 3 · 3 | 4 · 3 · 4 | 5 · 4 · 5 |
| v0.1.28 | visit-edit | [r1](runs/v0.1.28/2026-08-04-visit-edit-r1/README.md), [r2](runs/v0.1.28/2026-08-07-visit-edit-r2/README.md), [r3](runs/v0.1.28/2026-08-07-visit-edit-r3/README.md) | 3 · 4 · 3 | 4 · 3 · 3 | 4 · 4 · 3 | 5 · 5 · 5 |
| v0.1.22 | owners-page-param | [r1](runs/v0.1.22/2026-08-05-owners-page-param-r1/README.md) | 4 | 3 | 4 | 5 |
| v0.1.22 | specialty-directory | [r1](runs/v0.1.22/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.22/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.22/2026-08-06-specialty-directory-r3/README.md) | 1 · 3 · 3 | 1 · 3 · 4 | 1 · 3 · 3 | 3 · 5 · 4 |
| v0.1.22 | vets-specialty-filter | [r1](runs/v0.1.22/2026-08-05-vets-specialty-filter-r1/README.md) | 4 | 3 | 4 | 5 |
| v0.1.22 | visit-edit | [r1](runs/v0.1.22/2026-08-05-visit-edit-r1/README.md) | 4 | 4 | 4 | 5 |
| v0.1.18 | owners-page-param | [r1](runs/v0.1.18/2026-08-05-owners-page-param-r1/README.md) | 4 | 4 | 3 | 5 |
| v0.1.18 | specialty-directory | [r1](runs/v0.1.18/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.18/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.18/2026-08-06-specialty-directory-r3/README.md), [r4](runs/v0.1.18/2026-08-06-specialty-directory-r4/README.md), [r5](runs/v0.1.18/2026-08-06-specialty-directory-r5/README.md) | 3 · 3 · 3 · 3 · 2 | 3 · 3 · 3 · 3 · 2.5 | 3 · 3 · 4 · 3 · 2 | 4 · 3 · 5 · 3 · 3 |
| v0.1.18 | vets-specialty-filter | [r1](runs/v0.1.18/2026-08-05-vets-specialty-filter-r1/README.md) | 4 | 3 | 4 | 5 |
| v0.1.18 | visit-edit | [r1](runs/v0.1.18/2026-08-05-visit-edit-r1/README.md) | 4 | 4 | 4 | 5 |
| v0.1.1 | owners-page-param | [r2](runs/v0.1.1/2026-08-05-owners-page-param-r2/README.md) | 4 | 3 | 4 | 5 |
| v0.1.1 | specialty-directory | [r1](runs/v0.1.1/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.1/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.1/2026-08-06-specialty-directory-r3/README.md) | 3 · 3 · 2 | 3 · 3 · 3 | 3 · 3 · 3 | 3 · 4 · 4 |
| v0.1.1 | vets-specialty-filter | [r1](runs/v0.1.1/2026-08-05-vets-specialty-filter-r1/README.md) | 2 | 3 | 4 | 3 |
| v0.1.1 | visit-edit | [r1](runs/v0.1.1/2026-08-05-visit-edit-r1/README.md) | 3 | 4 | 4 | 5 |

The models behind the judged rows — one row per distinct provenance: the run's agent models, the pinned judge, the rubric. A version listed whole shares the row across every judged rep; a cell judged under two provenances names its reps, so a rubric or judge change mid-cell stays attributable:

| Judged rows | Agent models | Judge model | Rubric |
|---|---|---|---|
| v0.2.0, v0.1.29 | opus-5 · sonnet-5 | claude-opus-5 | [rubric-v1.md](../judge/rubric-v1.md) |
| v0.1.28, v0.1.22, v0.1.18, v0.1.1 | opus-4-8 · opus-5 · sonnet-4-6 | claude-opus-5 | [rubric-v1.md](../judge/rubric-v1.md) |

### Grader concordance

Tier B context, never a claim: the change grader's verdict is the system under test's self-assessment of its own change. The table asks one question — does a `concern` verdict track the machine-verified bar or the advisory judge? Judge quality is a run's mean over its facet medians; the cell holds the median of those means across the group's judged runs, `—` when the judge ran on none.

| Verdict | Runs | Bar cleared | Median judge quality |
|---|---|---|---|
| clear | 20 | 20/20 | 3.8 |
| concern | 13 | 11/13 | 4.0 |

### Escalation check

Derived candidates for the escalation rule, which stays operator-applied (README § Cost accounting and statistical discipline). A pair of adjacent version rows sharing pin and task lists while a trigger trips and either cell holds fewer than 3 reps. Each command re-runs both arms, keeping the added reps adjacent in time. A `~` row in the trend table is an arm of a listed pair still under that depth. Pairs list most severe first — a lost unit cost, then a bar flip, then cost rises, then falls, larger moves first — so the list reads as a backfill queue.

- `visit-cancel` · `v0.1.28 → v0.1.29`: cost per pass $6.79 → $22.82 (+236%)
  `python3 evals/run_eval.py --version v0.1.28 --version v0.1.29 --task visit-cancel --reps 2 --model claude-opus-5`
- `visit-cancel` · `v0.1.29 → v0.2.0`: cost per pass $22.82 → $39.78 (+74%)
  `python3 evals/run_eval.py --version v0.1.29 --version v0.2.0 --task visit-cancel --reps 2 --model claude-opus-5`
- `vets-specialty-filter` · `v0.1.22 → v0.1.28`: cost per pass $9.10 → $12.66 (+39%)
  `python3 evals/run_eval.py --version v0.1.22 --version v0.1.28 --task vets-specialty-filter --reps 2 --model claude-opus-5 --judge`
- `vets-specialty-filter` · `v0.1.18 → v0.1.22`: cost per pass $13.44 → $9.10 (-32%)
  `python3 evals/run_eval.py --version v0.1.18 --version v0.1.22 --task vets-specialty-filter --reps 2 --model claude-opus-5 --judge`

### Recorded runs

<details>
<summary>Per-rep detail — 71 runs, the spread behind each trend cell</summary>

Each run folder carries a generated `README.md` presenting the run; the folder's records are the ground truth. Spend and wall are the delivery figures the trend cells aggregate. A multi-rep cell lists every rep's figures in Reps order.

| Version | Task | Reps | Bar | Spend | Wall |
|---|---|---|---|---|---|
| v0.2.0 | owners-page-param | [r1](runs/v0.2.0/2026-08-04-owners-page-param-r1/README.md), [r2](runs/v0.2.0/2026-08-05-owners-page-param-r2/README.md), [r3](runs/v0.2.0/2026-08-05-owners-page-param-r3/README.md), [r4](runs/v0.2.0/2026-08-07-owners-page-param-r4/README.md), [r5](runs/v0.2.0/2026-08-07-owners-page-param-r5/README.md), [r6](runs/v0.2.0/2026-08-07-owners-page-param-r6/README.md) | cleared · cleared · cleared · cleared · cleared · cleared | $9.29 · $13.10 · $9.38 · $4.78 · $5.83 · $4.70 | 24m · 32m · 16m · 13m · 16m · 14m |
| v0.2.0 | specialty-directory | [r1](runs/v0.2.0/2026-08-04-specialty-directory-r1/README.md) | cleared | $15.49 | 36m |
| v0.2.0 | vets-specialty-filter | [r1](runs/v0.2.0/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.0/2026-08-05-vets-specialty-filter-r2/README.md), [r3](runs/v0.2.0/2026-08-05-vets-specialty-filter-r3/README.md) | cleared · cleared · cleared | $20.37 · $10.12 · $14.60 | 58m · 30m · 44m |
| v0.2.0 | visit-cancel | [r1](runs/v0.2.0/2026-08-04-visit-cancel-r1/README.md), [r2](runs/v0.2.0/2026-08-06-visit-cancel-r2/README.md), [r3](runs/v0.2.0/2026-08-06-visit-cancel-r3/README.md) | cleared · wasted (complete) · wasted (complete) | $1.17 · $15.42 · $23.18 | 3m · 41m · 65m |
| v0.2.0 | visit-edit | [r1](runs/v0.2.0/2026-08-04-visit-edit-r1/README.md) | cleared | $18.09 | 60m |
| v0.1.29 | owners-page-param | [r1](runs/v0.1.29/2026-08-04-owners-page-param-r1/README.md), [r2](runs/v0.1.29/2026-08-05-owners-page-param-r2/README.md), [r3](runs/v0.1.29/2026-08-05-owners-page-param-r3/README.md) | cleared · cleared · cleared | $5.95 · $5.71 · $5.01 | 13m · 13m · 15m |
| v0.1.29 | specialty-directory | [r1](runs/v0.1.29/2026-08-04-specialty-directory-r1/README.md) | cleared | $14.16 | 36m |
| v0.1.29 | vets-specialty-filter | [r1](runs/v0.1.29/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.29/2026-08-05-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.29/2026-08-05-vets-specialty-filter-r3/README.md), [r4](runs/v0.1.29/2026-08-07-vets-specialty-filter-r4/README.md), [r5](runs/v0.1.29/2026-08-07-vets-specialty-filter-r5/README.md) | cleared · cleared · cleared · cleared · cleared | $12.66 · $20.13 · $19.57 · $13.09 · $10.89 | 36m · 47m · 63m · 35m · 31m |
| v0.1.29 | visit-cancel | [r1](runs/v0.1.29/2026-08-06-visit-cancel-r1/README.md), [r2](runs/v0.1.29/2026-08-06-visit-cancel-r2/README.md) | wasted (complete) · cleared | $21.55 · $1.27 | 48m · 4m |
| v0.1.29 | visit-edit | [r1](runs/v0.1.29/2026-08-04-visit-edit-r1/README.md), [r2](runs/v0.1.29/2026-08-07-visit-edit-r2/README.md), [r3](runs/v0.1.29/2026-08-07-visit-edit-r3/README.md) | cleared · cleared · cleared | $19.70 · $13.68 · $13.80 | 45m · 36m · 38m |
| v0.1.28 | owners-page-param | [r1](runs/v0.1.28/2026-08-04-owners-page-param-r1/README.md) | cleared | $6.27 | 18m |
| v0.1.28 | specialty-directory | [r1](runs/v0.1.28/2026-08-04-specialty-directory-r1/README.md), [r2](runs/v0.1.28/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.28/2026-08-06-specialty-directory-r3/README.md) | cleared · cleared · cleared | $13.57 · $11.61 · $14.66 | 42m · 35m · 49m |
| v0.1.28 | vets-specialty-filter | [r1](runs/v0.1.28/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.28/2026-08-07-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.28/2026-08-07-vets-specialty-filter-r3/README.md) | cleared · cleared · cleared | $10.49 · $14.40 · $13.09 | 31m · 54m · 39m |
| v0.1.28 | visit-cancel | [r1](runs/v0.1.28/2026-08-04-visit-cancel-r1/README.md), [r2](runs/v0.1.28/2026-08-05-visit-cancel-r2/README.md), [r3](runs/v0.1.28/2026-08-06-visit-cancel-r3/README.md), [r4](runs/v0.1.28/2026-08-06-visit-cancel-r4/README.md) | cleared · wasted (complete) · cleared · cleared | $1.30 · $17.42 · $0.53 · $1.11 | 3m · 56m · 1m · 3m |
| v0.1.28 | visit-edit | [r1](runs/v0.1.28/2026-08-04-visit-edit-r1/README.md), [r2](runs/v0.1.28/2026-08-07-visit-edit-r2/README.md), [r3](runs/v0.1.28/2026-08-07-visit-edit-r3/README.md) | cleared · cleared · cleared | $12.19 · $14.02 · $12.65 | 34m · 40m · 36m |
| v0.1.22 | owners-page-param | [r1](runs/v0.1.22/2026-08-05-owners-page-param-r1/README.md) | cleared | $6.00 | 18m |
| v0.1.22 | specialty-directory | [r1](runs/v0.1.22/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.22/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.22/2026-08-06-specialty-directory-r3/README.md) | wasted (complete) · cleared · cleared | $2.19 · $11.82 · $13.64 | 7m · 41m · 39m |
| v0.1.22 | vets-specialty-filter | [r1](runs/v0.1.22/2026-08-05-vets-specialty-filter-r1/README.md) | cleared | $9.10 | 33m |
| v0.1.22 | visit-cancel | [r1](runs/v0.1.22/2026-08-05-visit-cancel-r1/README.md), [r2](runs/v0.1.22/2026-08-05-visit-cancel-r2/README.md), [r3](runs/v0.1.22/2026-08-06-visit-cancel-r3/README.md), [r4](runs/v0.1.22/2026-08-06-visit-cancel-r4/README.md) | cleared · cleared · cleared · cleared | $1.10 · $1.06 · $1.18 · $1.35 | 3m · 3m · 3m · 4m |
| v0.1.22 | visit-edit | [r1](runs/v0.1.22/2026-08-05-visit-edit-r1/README.md) | cleared | $11.73 | 33m |
| v0.1.18 | owners-page-param | [r1](runs/v0.1.18/2026-08-05-owners-page-param-r1/README.md) | cleared | $5.85 | 17m |
| v0.1.18 | specialty-directory | [r1](runs/v0.1.18/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.18/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.18/2026-08-06-specialty-directory-r3/README.md), [r4](runs/v0.1.18/2026-08-06-specialty-directory-r4/README.md), [r5](runs/v0.1.18/2026-08-06-specialty-directory-r5/README.md) | cleared · cleared · cleared · cleared · wasted (timeout) | $9.12 · $13.42 · $13.22 · $12.03 · $13.01 | 25m · 43m · 44m · 33m · 131m |
| v0.1.18 | vets-specialty-filter | [r1](runs/v0.1.18/2026-08-05-vets-specialty-filter-r1/README.md) | cleared | $13.44 | 45m |
| v0.1.18 | visit-cancel | [r1](runs/v0.1.18/2026-08-05-visit-cancel-r1/README.md), [r2](runs/v0.1.18/2026-08-05-visit-cancel-r2/README.md), [r3](runs/v0.1.18/2026-08-06-visit-cancel-r3/README.md) | wasted (complete) · wasted (complete) · cleared | $14.45 · $16.15 · $0.42 | 45m · 48m · 1m |
| v0.1.18 | visit-edit | [r1](runs/v0.1.18/2026-08-05-visit-edit-r1/README.md) | cleared | $12.43 | 36m |
| v0.1.1 | owners-page-param | [r1](runs/v0.1.1/2026-08-05-owners-page-param-r1/README.md), [r2](runs/v0.1.1/2026-08-05-owners-page-param-r2/README.md) | cleared · cleared | $5.71 · $6.56 | 14m · 18m |
| v0.1.1 | specialty-directory | [r1](runs/v0.1.1/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.1/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.1/2026-08-06-specialty-directory-r3/README.md) | cleared · cleared · wasted (timeout) | $6.52 · $10.58 · $27.04 | 20m · 31m · 127m |
| v0.1.1 | vets-specialty-filter | [r1](runs/v0.1.1/2026-08-05-vets-specialty-filter-r1/README.md) | cleared | $11.61 | 42m |
| v0.1.1 | visit-cancel | [r1](runs/v0.1.1/2026-08-05-visit-cancel-r1/README.md) | wasted (complete) | $17.57 | 58m |
| v0.1.1 | visit-edit | [r1](runs/v0.1.1/2026-08-05-visit-edit-r1/README.md) | cleared | $11.09 | 29m |

</details>
