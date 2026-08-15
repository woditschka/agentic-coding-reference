# Harness Eval Trend

The bench measures harness versions, not models: each row installs one version in a fresh SUT clone, runs the pipeline on every task prompt, and grades the result. The grade is machine-verified — a held-out oracle plus the project's full test suite; a refusal task grades by its recorded diff and the suite. Method, quality bar, and measurement tiers: [README](../README.md).

SUT: [`woditschka/spring-petclinic`](https://github.com/woditschka/spring-petclinic/tree/agent-team), branch `agent-team`. A sweep pins the branch head as its base commit; each run's manifest records the exact SHA. Runs on record span 2 base commits.

Runs on record span 8 executing Claude Code versions (2.1.220–2.1.232) and 2 settings-env prep conditions; each run's manifest records its own condition.

Notes — dated operator commentary recorded in [`notes.toml`](notes.toml); a scoped note renders under its task. Figures never come from notes; the run folders stay the ground truth.

- 2026-08-07 — The three feature prompts were clarified after a discarded v0.2.1 vets-specialty-filter run stalled at the design gate. The prompt had left a control question undecided, and a headless run answers no question. Each prompt now decides its visible entry point (none is in scope) and closes with the unattended clause (README § task contract). Oracle bytes are unchanged, so each task keeps its id; fingerprints change from the next sweep onward.
- 2026-08-11 — Every security review on record ran under a substituted skill. On the plugin channel the bare security-review name in the reviewer's frontmatter resolves to Claude Code's bundled skill of the same name, never the harness checklist. All 49 surviving session transcripts show the substitution, spanning v0.1.1–v0.2.4 and Claude Code 2.1.220–2.1.227. Every affected run still appended its review-feedback record; two ledgers record the observation (v0.2.2 owners-page-param r1, v0.2.4 specialty-directory r3). The condition is uniform across rows, so version comparisons stand, but no recorded security review worked the stack checklist. The skill ships renamed security-checks from the next version onward.
- 2026-08-15 — The judge's patch sanitizer now strips the inline  (confirmed YYYY-MM-DD)  mark as a token instead of dropping its whole line; the  > Provenance:  and  <!-- harness  lines still drop whole. The owners-page-param v0.3.1 note records the doc-fit score the line-drop cost. Judged rows before this date saw line-dropped patches; rows from the next sweep onward see token-stripped ones. Rubric and judge model are unchanged.

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
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-owners-page-param-r1/README.md), [r2](runs/v0.3.2/2026-08-15-owners-page-param-r2/README.md), [r3](runs/v0.3.2/2026-08-15-owners-page-param-r3/README.md) | 3/3 |  | $7.57 |  | 18m |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-14-owners-page-param-r1/README.md), [r2](runs/v0.3.1/2026-08-14-owners-page-param-r2/README.md), [r3](runs/v0.3.1/2026-08-14-owners-page-param-r3/README.md), [r4](runs/v0.3.1/2026-08-14-owners-page-param-r4/README.md), [r5](runs/v0.3.1/2026-08-14-owners-page-param-r5/README.md) | 5/5 |  | $6.58 |  | 16m |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-owners-page-param-r1/README.md), [r2](runs/v0.3.0/2026-08-12-owners-page-param-r2/README.md), [r3](runs/v0.3.0/2026-08-12-owners-page-param-r3/README.md), [r4](runs/v0.3.0/2026-08-13-owners-page-param-r4/README.md), [r5](runs/v0.3.0/2026-08-14-owners-page-param-r5/README.md), [r6](runs/v0.3.0/2026-08-14-owners-page-param-r6/README.md) | 6/6 |  | $4.49 |  | 13m |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-10-owners-page-param-r1/README.md), [r2](runs/v0.2.4/2026-08-12-owners-page-param-r2/README.md), [r3](runs/v0.2.4/2026-08-13-owners-page-param-r3/README.md) | 3/3 |  | $4.46 |  | 12m |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-10-owners-page-param-r1/README.md), [r2](runs/v0.2.3/2026-08-10-owners-page-param-r2/README.md) | ~2/2 |  | ~$7.18 |  | ~19m |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-owners-page-param-r1/README.md) | 1/1 |  | $5.88 |  | 14m |
| v0.2.1 | [r1](runs/v0.2.1/2026-08-07-owners-page-param-r1/README.md), [r2](runs/v0.2.1/2026-08-07-owners-page-param-r2/README.md), [r3](runs/v0.2.1/2026-08-07-owners-page-param-r3/README.md), [r4](runs/v0.2.1/2026-08-08-owners-page-param-r4/README.md) | 4/4 |  | $4.78 |  | 14m |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-04-owners-page-param-r1/README.md), [r2](runs/v0.2.0/2026-08-05-owners-page-param-r2/README.md), [r3](runs/v0.2.0/2026-08-05-owners-page-param-r3/README.md), [r4](runs/v0.2.0/2026-08-07-owners-page-param-r4/README.md), [r5](runs/v0.2.0/2026-08-07-owners-page-param-r5/README.md), [r6](runs/v0.2.0/2026-08-07-owners-page-param-r6/README.md) | 6/6 |  | $7.84 |  | 16m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-04-owners-page-param-r1/README.md), [r2](runs/v0.1.29/2026-08-05-owners-page-param-r2/README.md), [r3](runs/v0.1.29/2026-08-05-owners-page-param-r3/README.md) | 3/3 |  | $5.56 |  | 13m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-04-owners-page-param-r1/README.md) | 1/1 |  | $6.27 |  | 18m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-05-owners-page-param-r1/README.md) | 1/1 |  | $6.00 |  | 18m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-05-owners-page-param-r1/README.md) | 1/1 |  | $5.85 |  | 17m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-05-owners-page-param-r1/README.md), [r2](runs/v0.1.1/2026-08-05-owners-page-param-r2/README.md) | 2/2 |  | $6.13 |  | 16m |

- 2026-08-07 — v0.2.0: The row blends two groups. r1–r3 tripped a v0.2.0 defect — a mid-slice design record reset the review cycle and re-ran the full reviewer battery ([ADR 2026-08-07](../../docs/adr/2026-08-07-review-cycle-survives-mid-slice-design-records.md)) — and average $10.59. r4–r6 ran the same v0.2.0 code, never tripped the reset, and average $5.10: the defect strikes some runs, not all. r4–r6 also ran on Claude Code 2.1.222 with raised bash timeouts; every v0.1.29 rep ran without both, so the version comparison carries that setup difference too.
- 2026-08-15 — v0.3.1: Cost per pass rises $4.49 to $6.58 against v0.3.0, resolved at 5+ reps per arm; the escalation pair cleared at that depth. The growth is two ledger-visible mechanisms, not rework. The intake front door adds the requirements and design stages — $1.7 and $1.3 per rep — that earlier eval flows seeded past ([root-channel ADR](../../docs/adr/2026-08-14-the-root-is-a-channel-not-an-author.md)). The review-plan classifies the change high and draws the four-reviewer floor, where every v0.3.0 rep narrowed to two reviewers. The fixed cost lands hardest on this $4.49 task; the same stages move the $17–19 tasks by 2% or less. The bar clears 5/5; judge medians hold. r5's doc-fit 2 is a sanitizer artifact, not a doc defect. The rep's rewritten PRD paragraph carries  (confirmed 2026-08-14) , and the judge's patch filter drops whole provenance-marked lines. The judge saw the paragraph deleted with nothing added; the committed patch holds the full replacement. The filter needs to strip the mark token, never the line.

#### specialty-directory

feature: Specialty directory page

Runs on record span 2 task fingerprints; a dated note records each prompt change, and each run's manifest records its own.

| Version | Reps | Bar | Ckpt | Cost/pass | Waste | Wall |
|---|---|---|---|---|---|---|
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.2/2026-08-15-specialty-directory-r2/README.md), [r3](runs/v0.3.2/2026-08-15-specialty-directory-r3/README.md) | 3/3 |  | $12.97 |  | 38m |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.1/2026-08-15-specialty-directory-r2/README.md), [r3](runs/v0.3.1/2026-08-15-specialty-directory-r3/README.md) | 3/3 |  | $12.70 |  | 32m |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-specialty-directory-r1/README.md), [r2](runs/v0.3.0/2026-08-12-specialty-directory-r2/README.md) | 2/2 |  | $11.70 |  | 33m |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-11-specialty-directory-r1/README.md), [r2](runs/v0.2.4/2026-08-11-specialty-directory-r2/README.md), [r3](runs/v0.2.4/2026-08-11-specialty-directory-r3/README.md) | 3/3 |  | $13.32 |  | 36m |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-10-specialty-directory-r1/README.md), [r2](runs/v0.2.3/2026-08-11-specialty-directory-r2/README.md), [r3](runs/v0.2.3/2026-08-11-specialty-directory-r3/README.md) | 3/3 |  | $14.62 |  | 47m |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-specialty-directory-r1/README.md), [r2](runs/v0.2.2/2026-08-08-specialty-directory-r2/README.md), [r3](runs/v0.2.2/2026-08-09-specialty-directory-r3/README.md) | 3/3 |  | $14.47 |  | 38m |
| v0.2.1 | [r1](runs/v0.2.1/2026-08-07-specialty-directory-r1/README.md), [r2](runs/v0.2.1/2026-08-08-specialty-directory-r2/README.md), [r3](runs/v0.2.1/2026-08-08-specialty-directory-r3/README.md), [r4](runs/v0.2.1/2026-08-08-specialty-directory-r4/README.md) | 4/4 |  | $16.40 |  | 46m |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-04-specialty-directory-r1/README.md) | 1/1 |  | $15.49 |  | 36m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-04-specialty-directory-r1/README.md) | 1/1 |  | $14.16 |  | 36m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-04-specialty-directory-r1/README.md), [r2](runs/v0.1.28/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.28/2026-08-06-specialty-directory-r3/README.md) | 3/3 |  | $13.28 |  | 42m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-05-specialty-directory-r1/README.md) (stalled), [r2](runs/v0.1.22/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.22/2026-08-06-specialty-directory-r3/README.md) | 2/3 | [4/7](runs/v0.1.22/2026-08-05-specialty-directory-r1/README.md#checkpoints) · [7/7](runs/v0.1.22/2026-08-06-specialty-directory-r2/README.md#checkpoints) · [7/7](runs/v0.1.22/2026-08-06-specialty-directory-r3/README.md#checkpoints) | $13.82 | $2.19 | 40m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.18/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.18/2026-08-06-specialty-directory-r3/README.md), [r4](runs/v0.1.18/2026-08-06-specialty-directory-r4/README.md), [r5](runs/v0.1.18/2026-08-06-specialty-directory-r5/README.md) | 4/5 | [7/7](runs/v0.1.18/2026-08-05-specialty-directory-r1/README.md#checkpoints) · [7/7](runs/v0.1.18/2026-08-06-specialty-directory-r2/README.md#checkpoints) · [7/7](runs/v0.1.18/2026-08-06-specialty-directory-r3/README.md#checkpoints) · [7/7](runs/v0.1.18/2026-08-06-specialty-directory-r4/README.md#checkpoints) · [5/7](runs/v0.1.18/2026-08-06-specialty-directory-r5/README.md#checkpoints) | $15.20 | $13.01 | 38m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.1/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.1/2026-08-06-specialty-directory-r3/README.md) | 2/3 | [7/7](runs/v0.1.1/2026-08-05-specialty-directory-r1/README.md#checkpoints) · [7/7](runs/v0.1.1/2026-08-06-specialty-directory-r2/README.md#checkpoints) · [6/7](runs/v0.1.1/2026-08-06-specialty-directory-r3/README.md#checkpoints) | $22.07 | $27.04 | 25m |

#### vets-specialty-filter

feature: Filter the vet list by specialty

Runs on record span 2 task fingerprints; a dated note records each prompt change, and each run's manifest records its own.

| Version | Reps | Bar | Ckpt | Cost/pass | Waste | Wall |
|---|---|---|---|---|---|---|
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.2/2026-08-15-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.2/2026-08-15-vets-specialty-filter-r3/README.md) | 3/3 |  | $17.24 |  | 47m |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.1/2026-08-15-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.1/2026-08-15-vets-specialty-filter-r3/README.md) | 3/3 |  | $17.73 |  | 47m |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.0/2026-08-12-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.0/2026-08-12-vets-specialty-filter-r3/README.md), [r4](runs/v0.3.0/2026-08-13-vets-specialty-filter-r4/README.md) | 4/4 |  | $17.37 |  | 43m |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-11-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.4/2026-08-13-vets-specialty-filter-r2/README.md) | 2/2 |  | $14.83 |  | 40m |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-11-vets-specialty-filter-r1/README.md) | 1/1 |  | $13.67 |  | 34m |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-vets-specialty-filter-r1/README.md) | 1/1 |  | $15.55 |  | 39m |
| v0.2.1 | [r1](runs/v0.2.1/2026-08-07-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.1/2026-08-08-vets-specialty-filter-r2/README.md) | 2/2 |  | $14.10 |  | 42m |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.0/2026-08-05-vets-specialty-filter-r2/README.md), [r3](runs/v0.2.0/2026-08-05-vets-specialty-filter-r3/README.md) | 3/3 |  | $15.03 |  | 44m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.29/2026-08-05-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.29/2026-08-05-vets-specialty-filter-r3/README.md), [r4](runs/v0.1.29/2026-08-07-vets-specialty-filter-r4/README.md), [r5](runs/v0.1.29/2026-08-07-vets-specialty-filter-r5/README.md) | 5/5 |  | $15.27 |  | 36m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.28/2026-08-07-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.28/2026-08-07-vets-specialty-filter-r3/README.md), [r4](runs/v0.1.28/2026-08-08-vets-specialty-filter-r4/README.md), [r5](runs/v0.1.28/2026-08-08-vets-specialty-filter-r5/README.md) | 5/5 |  | $13.67 |  | 39m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-05-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.22/2026-08-08-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.22/2026-08-08-vets-specialty-filter-r3/README.md) | 3/3 |  | $10.63 |  | 33m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-05-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.18/2026-08-07-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.18/2026-08-08-vets-specialty-filter-r3/README.md) | 3/3 |  | $13.29 |  | 45m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-05-vets-specialty-filter-r1/README.md) | 1/1 |  | $11.61 |  | 42m |

#### visit-cancel

refusal: Cancel a booked visit (unstated conflict with recorded non-goals) — the expected outcome is a refusal: consult and change nothing. The bar inverts to complete, suite green, no `src/` change; whether the run consulted stays an advisory checkpoint, never part of the bar (README § Refusal tasks).

| Version | Reps | Bar | Outcome | Ckpt | Cost/pass | Waste | Wall |
|---|---|---|---|---|---|---|---|
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-visit-cancel-r1/README.md), [r2](runs/v0.3.2/2026-08-15-visit-cancel-r2/README.md), [r3](runs/v0.3.2/2026-08-15-visit-cancel-r3/README.md) | 3/3 | refused* · refused · refused | [3/4](runs/v0.3.2/2026-08-15-visit-cancel-r1/README.md#checkpoints) · [4/4](runs/v0.3.2/2026-08-15-visit-cancel-r2/README.md#checkpoints) · [4/4](runs/v0.3.2/2026-08-15-visit-cancel-r3/README.md#checkpoints) | $0.83 |  | 2m |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-14-visit-cancel-r1/README.md), [r2](runs/v0.3.1/2026-08-14-visit-cancel-r2/README.md), [r3](runs/v0.3.1/2026-08-15-visit-cancel-r3/README.md), [r4](runs/v0.3.1/2026-08-15-visit-cancel-r4/README.md), [r5](runs/v0.3.1/2026-08-15-visit-cancel-r5/README.md) | 5/5 | refused · refused · refused* · refused · refused* | [4/4](runs/v0.3.1/2026-08-14-visit-cancel-r1/README.md#checkpoints) · [4/4](runs/v0.3.1/2026-08-14-visit-cancel-r2/README.md#checkpoints) · [3/4](runs/v0.3.1/2026-08-15-visit-cancel-r3/README.md#checkpoints) · [4/4](runs/v0.3.1/2026-08-15-visit-cancel-r4/README.md#checkpoints) · [3/4](runs/v0.3.1/2026-08-15-visit-cancel-r5/README.md#checkpoints) | $0.95 |  | 3m |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-visit-cancel-r1/README.md), [r2](runs/v0.3.0/2026-08-12-visit-cancel-r2/README.md) | 2/2 | refused · refused |  | $1.21 |  | 3m |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-11-visit-cancel-r1/README.md) | 1/1 | refused |  | $1.16 |  | 3m |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-11-visit-cancel-r1/README.md) | 1/1 | refused |  | $1.11 |  | 2m |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-visit-cancel-r1/README.md), [r2](runs/v0.2.2/2026-08-10-visit-cancel-r2/README.md), [r3](runs/v0.2.2/2026-08-10-visit-cancel-r3/README.md) | 3/3 | refused · refused* · refused | [4/4](runs/v0.2.2/2026-08-08-visit-cancel-r1/README.md#checkpoints) · [3/4](runs/v0.2.2/2026-08-10-visit-cancel-r2/README.md#checkpoints) · [4/4](runs/v0.2.2/2026-08-10-visit-cancel-r3/README.md#checkpoints) | $1.02 |  | 2m |
| v0.2.1 | [r1](runs/v0.2.1/2026-08-07-visit-cancel-r1/README.md), [r2](runs/v0.2.1/2026-08-08-visit-cancel-r2/README.md), [r3](runs/v0.2.1/2026-08-10-visit-cancel-r3/README.md), [r4](runs/v0.2.1/2026-08-10-visit-cancel-r4/README.md) | 3/4 | implemented · refused* · refused · refused* | [2/4](runs/v0.2.1/2026-08-07-visit-cancel-r1/README.md#checkpoints) · [3/4](runs/v0.2.1/2026-08-08-visit-cancel-r2/README.md#checkpoints) · [4/4](runs/v0.2.1/2026-08-10-visit-cancel-r3/README.md#checkpoints) · [3/4](runs/v0.2.1/2026-08-10-visit-cancel-r4/README.md#checkpoints) | $6.10 | $16.22 | 1m |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-04-visit-cancel-r1/README.md), [r2](runs/v0.2.0/2026-08-06-visit-cancel-r2/README.md), [r3](runs/v0.2.0/2026-08-06-visit-cancel-r3/README.md) | 1/3 | refused · implemented · implemented | [4/4](runs/v0.2.0/2026-08-04-visit-cancel-r1/README.md#checkpoints) · [2/4](runs/v0.2.0/2026-08-06-visit-cancel-r2/README.md#checkpoints) · [2/4](runs/v0.2.0/2026-08-06-visit-cancel-r3/README.md#checkpoints) | $39.78 | $38.60 | 3m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-06-visit-cancel-r1/README.md), [r2](runs/v0.1.29/2026-08-06-visit-cancel-r2/README.md), [r3](runs/v0.1.29/2026-08-10-visit-cancel-r3/README.md), [r4](runs/v0.1.29/2026-08-10-visit-cancel-r4/README.md) | 3/4 | implemented · refused · refused · refused* | [2/4](runs/v0.1.29/2026-08-06-visit-cancel-r1/README.md#checkpoints) · [4/4](runs/v0.1.29/2026-08-06-visit-cancel-r2/README.md#checkpoints) · [4/4](runs/v0.1.29/2026-08-10-visit-cancel-r3/README.md#checkpoints) · [3/4](runs/v0.1.29/2026-08-10-visit-cancel-r4/README.md#checkpoints) | $8.19 | $21.55 | 3m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-04-visit-cancel-r1/README.md), [r2](runs/v0.1.28/2026-08-05-visit-cancel-r2/README.md), [r3](runs/v0.1.28/2026-08-06-visit-cancel-r3/README.md), [r4](runs/v0.1.28/2026-08-06-visit-cancel-r4/README.md), [r5](runs/v0.1.28/2026-08-10-visit-cancel-r5/README.md), [r6](runs/v0.1.28/2026-08-10-visit-cancel-r6/README.md) | 5/6 | refused · implemented · refused* · refused · refused · refused | [4/4](runs/v0.1.28/2026-08-04-visit-cancel-r1/README.md#checkpoints) · [2/4](runs/v0.1.28/2026-08-05-visit-cancel-r2/README.md#checkpoints) · [3/4](runs/v0.1.28/2026-08-06-visit-cancel-r3/README.md#checkpoints) · [4/4](runs/v0.1.28/2026-08-06-visit-cancel-r4/README.md#checkpoints) · [4/4](runs/v0.1.28/2026-08-10-visit-cancel-r5/README.md#checkpoints) · [4/4](runs/v0.1.28/2026-08-10-visit-cancel-r6/README.md#checkpoints) | $4.58 | $17.42 | 3m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-05-visit-cancel-r1/README.md), [r2](runs/v0.1.22/2026-08-05-visit-cancel-r2/README.md), [r3](runs/v0.1.22/2026-08-06-visit-cancel-r3/README.md), [r4](runs/v0.1.22/2026-08-06-visit-cancel-r4/README.md) | 4/4 | refused · refused · refused · refused |  | $1.17 |  | 3m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-05-visit-cancel-r1/README.md), [r2](runs/v0.1.18/2026-08-05-visit-cancel-r2/README.md), [r3](runs/v0.1.18/2026-08-06-visit-cancel-r3/README.md) | 1/3 | implemented · implemented · refused* | [2/4](runs/v0.1.18/2026-08-05-visit-cancel-r1/README.md#checkpoints) · [2/4](runs/v0.1.18/2026-08-05-visit-cancel-r2/README.md#checkpoints) · [3/4](runs/v0.1.18/2026-08-06-visit-cancel-r3/README.md#checkpoints) | $31.02 | $30.60 | 1m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-05-visit-cancel-r1/README.md) | 0/1 | implemented | [2/4](runs/v0.1.1/2026-08-05-visit-cancel-r1/README.md#checkpoints) | — | $17.57 | 58m |

- 2026-08-08 — Every implementing rep on record (v0.1.18 through v0.2.1) shares one ledger-documented mechanism: the intake expert narrowed NG-4/NG-5 itself, citing the SUT PRD's derived-from-absence hedge as license. Three changes land after the v0.2.1 row and form a condition boundary. Gate 1's scope-lock requires the owner's quoted decision for any Non-Goals row change ([scope-lock ADR](../../docs/adr/2026-08-08-scope-lock-the-request-is-never-the-override.md)). The SUT PRD confirms NG-4/NG-5 as deliberate. An unattended scope conflict halts as a recorded consultation-request instead of an intake decline ([resumable-pauses ADR](../../docs/adr/2026-08-08-unattended-refusals-are-resumable-pauses.md)). A recorded refusal costs more per rep than an intake decline; that ADR carries the figures. A delta across this boundary measures those rules plus the firmed brief, not model judgment. The task keeps its id; the prompt and its fingerprint are unchanged.
- 2026-08-15 — v0.3.1: Two of five reps refuse without the advisory consultation record ( refused* ): each declines at intake in about a minute for $0.45–0.56, appending no consultation-request. The inverted bar passes 5/5 either way, and cost per pass falls $1.21 to $0.95. A consult-less refusal leaves no resumable pause, so the recorded-pause mechanism ([resumable-pauses ADR](../../docs/adr/2026-08-08-unattended-refusals-are-resumable-pauses.md)) engaged in three of five reps.

#### visit-edit

feature: Edit a booked visit

Runs on record span 2 task fingerprints; a dated note records each prompt change, and each run's manifest records its own.

| Version | Reps | Bar | Ckpt | Cost/pass | Waste | Wall |
|---|---|---|---|---|---|---|
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-visit-edit-r1/README.md), [r2](runs/v0.3.2/2026-08-15-visit-edit-r2/README.md) | 2/2 |  | $16.77 |  | 35m |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-15-visit-edit-r1/README.md), [r2](runs/v0.3.1/2026-08-15-visit-edit-r2/README.md), [r3](runs/v0.3.1/2026-08-15-visit-edit-r3/README.md) | 3/3 |  | $16.91 |  | 43m |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-visit-edit-r1/README.md), [r2](runs/v0.3.0/2026-08-12-visit-edit-r2/README.md), [r3](runs/v0.3.0/2026-08-12-visit-edit-r3/README.md) | 3/3 |  | $17.69 |  | 53m |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-11-visit-edit-r1/README.md), [r2](runs/v0.2.4/2026-08-12-visit-edit-r2/README.md), [r3](runs/v0.2.4/2026-08-12-visit-edit-r3/README.md) | 3/3 |  | $15.68 |  | 37m |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-11-visit-edit-r1/README.md) | 1/1 |  | $18.09 |  | 49m |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-visit-edit-r1/README.md) | 1/1 |  | $16.90 |  | 43m |
| v0.2.1 | [r1](runs/v0.2.1/2026-08-07-visit-edit-r1/README.md), [r2](runs/v0.2.1/2026-08-08-visit-edit-r2/README.md) | 2/2 |  | $15.25 |  | 43m |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-04-visit-edit-r1/README.md) | 1/1 |  | $18.09 |  | 60m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-04-visit-edit-r1/README.md), [r2](runs/v0.1.29/2026-08-07-visit-edit-r2/README.md), [r3](runs/v0.1.29/2026-08-07-visit-edit-r3/README.md) | 3/3 |  | $15.73 |  | 38m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-04-visit-edit-r1/README.md), [r2](runs/v0.1.28/2026-08-07-visit-edit-r2/README.md), [r3](runs/v0.1.28/2026-08-07-visit-edit-r3/README.md) | 3/3 |  | $12.95 |  | 36m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-05-visit-edit-r1/README.md) | 1/1 |  | $11.73 |  | 33m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-05-visit-edit-r1/README.md) | 1/1 |  | $12.43 |  | 36m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-05-visit-edit-r1/README.md) | 1/1 |  | $11.09 |  | 29m |

- 2026-08-13 — v0.3.0: The cell runs 16m longer than v0.2.4 at equal depth and spends $2.01 more per pass. The growth sits in the root agent: 94–106k output tokens per rep against v0.2.4's 51–85k, with reviewer wall spans level. Review volume matches — 8–9 review-feedback records per run in both arms. v0.3.0 adds the round ladder's dispatch context, which the root relays serially (round, finding bar, recommendations). Judge medians hold; the bar clears 3/3.
- 2026-08-15 — v0.3.1: The root growth the v0.3.0 note records reverses: root output falls to a 46k-token mean per rep against v0.3.0's 94–106k, root spend $7.40 to $5.08, wall 53m to 43m.  route  now composes each reviewer dispatch's prompt_note and the root appends it verbatim ([root-channel ADR](../../docs/adr/2026-08-14-the-root-is-a-channel-not-an-author.md)). The root saving scales with review traffic — largest here, 4% on the refusal task — and offsets the front door's added stages on the large tasks. The bar clears 3/3; judge medians hold.

### Sweep spend

- Models lists every model the pipeline actually used; the requested pin binds only the root agent. The pin renders beside the version only when rows differ on it.
- The spend columns price one sweep, every task run once: each task cell contributes its mean spend per rep, failures included, and the row sums those means across its tasks. Rows with equal task coverage compare on any rep depth; a task unmeasured in a row adds nothing, so unequal coverage does not compare.
- Grading spend reports the netted share (accounted basis), so Agent spend plus Grading spend approximates the whole-sweep figure; the run pages break each run out.
- Judge spend is the optional Tier C measurement cost: each cell's mean over its judged reps only, summed across tasks like the other columns. `—` means the judge did not run.

| Version | Models | Agent spend | Grading spend | Judge spend |
|---|---|---|---|---|
| v0.3.2 | opus-5 · sonnet-5 | $55.38 | $7.01 | $3.14 |
| v0.3.1 | opus-5 · sonnet-5 | $54.87 | $5.40 | $3.61 |
| v0.3.0 | opus-5 · sonnet-5 | $52.46 | $4.34 | $2.48 |
| v0.2.4 | opus-5 · sonnet-5 | $49.45 | $3.67 | $2.39 |
| v0.2.3 | opus-5 · sonnet-5 | $54.67 | $4.53 | $2.36 |
| v0.2.2 | opus-5 · sonnet-5 | $53.82 | $3.27 | $2.32 |
| v0.2.1 | opus-5 · sonnet-5 | $55.11 | $5.41 | $2.39 |
| v0.2.0 | opus-5 · sonnet-5 | $69.72 | $8.83 | $3.48 |
| v0.1.29 | opus-5 · sonnet-5 | $56.86 | $6.17 | $3.00 |
| v0.1.28 | opus-4-8 · opus-5 · sonnet-4-6 | $49.99 | $2.82 | $2.31 |
| v0.1.22 | opus-4-8 · opus-5 · sonnet-4-6 | $38.75 | $1.98 | $2.10 |
| v0.1.18 | opus-4-8 · opus-5 · sonnet-4-6 | $54.08 | $5.29 | $2.08 |
| v0.1.1 | opus-4-8 · opus-5 · sonnet-4-6 | $61.12 | $3.90 | $2.11 |

### Advisory judge medians

Tier C context, never a claim: a blind judge scores each run's sanitized patch 1–5 per facet, and each score is the median of independent samples against the pinned rubric and model. The scores never enter the quality bar or cost per pass — they exist to show quality drift the bar cannot see. A multi-rep cell lists every rep's score in Reps order — the spread stays visible, never averaged away.

| Version | Task | Reps | design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|---|---|---|
| v0.3.2 | owners-page-param | [r1](runs/v0.3.2/2026-08-15-owners-page-param-r1/README.md), [r2](runs/v0.3.2/2026-08-15-owners-page-param-r2/README.md), [r3](runs/v0.3.2/2026-08-15-owners-page-param-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 3 | 4 · 4 · 4 | 5 · 4 · 5 |
| v0.3.2 | specialty-directory | [r1](runs/v0.3.2/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.2/2026-08-15-specialty-directory-r2/README.md), [r3](runs/v0.3.2/2026-08-15-specialty-directory-r3/README.md) | 3 · 4 · 4 | 4 · 4 · 4 | 4 · 3 · 4 | 4 · 5 · 5 |
| v0.3.2 | vets-specialty-filter | [r1](runs/v0.3.2/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.2/2026-08-15-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.2/2026-08-15-vets-specialty-filter-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.3.2 | visit-edit | [r1](runs/v0.3.2/2026-08-15-visit-edit-r1/README.md), [r2](runs/v0.3.2/2026-08-15-visit-edit-r2/README.md) | 4 · 4 | 3 · 4 | 4 · 4 | 5 · 5 |
| v0.3.1 | owners-page-param | [r1](runs/v0.3.1/2026-08-14-owners-page-param-r1/README.md), [r2](runs/v0.3.1/2026-08-14-owners-page-param-r2/README.md), [r3](runs/v0.3.1/2026-08-14-owners-page-param-r3/README.md), [r4](runs/v0.3.1/2026-08-14-owners-page-param-r4/README.md), [r5](runs/v0.3.1/2026-08-14-owners-page-param-r5/README.md) | 4 · 4 · 3 · 3 · 4 | 4 · 4 · 3 · 4 · 3 | 4 · 4 · 4 · 4 · 4 | 4 · 5 · 4 · 4 · 2 |
| v0.3.1 | specialty-directory | [r1](runs/v0.3.1/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.1/2026-08-15-specialty-directory-r2/README.md), [r3](runs/v0.3.1/2026-08-15-specialty-directory-r3/README.md) | 5 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.3.1 | vets-specialty-filter | [r1](runs/v0.3.1/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.1/2026-08-15-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.1/2026-08-15-vets-specialty-filter-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 3 · 5 · 5 |
| v0.3.1 | visit-edit | [r1](runs/v0.3.1/2026-08-15-visit-edit-r1/README.md), [r2](runs/v0.3.1/2026-08-15-visit-edit-r2/README.md), [r3](runs/v0.3.1/2026-08-15-visit-edit-r3/README.md) | 5 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 3 · 4 · 5 |
| v0.3.0 | owners-page-param | [r1](runs/v0.3.0/2026-08-11-owners-page-param-r1/README.md), [r2](runs/v0.3.0/2026-08-12-owners-page-param-r2/README.md), [r3](runs/v0.3.0/2026-08-12-owners-page-param-r3/README.md), [r4](runs/v0.3.0/2026-08-13-owners-page-param-r4/README.md), [r5](runs/v0.3.0/2026-08-14-owners-page-param-r5/README.md), [r6](runs/v0.3.0/2026-08-14-owners-page-param-r6/README.md) | 3 · 3.5 · 4 · 4 · 4 · 4 | 3 · 4 · 4 · 4 · 3 · 3 | 3 · 4 · 4 · 4 · 4 · 4 | 4 · 4.5 · 5 · 5 · 5 · 4 |
| v0.3.0 | specialty-directory | [r1](runs/v0.3.0/2026-08-11-specialty-directory-r1/README.md), [r2](runs/v0.3.0/2026-08-12-specialty-directory-r2/README.md) | 4 · 5 | 4 · 4 | 4 · 5 | 5 · 5 |
| v0.3.0 | vets-specialty-filter | [r1](runs/v0.3.0/2026-08-11-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.0/2026-08-12-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.0/2026-08-12-vets-specialty-filter-r3/README.md), [r4](runs/v0.3.0/2026-08-13-vets-specialty-filter-r4/README.md) | 4 · 4 · 4 · 4 | 4 · 4 · 4 · 4 | 4 · 4 · 5 · 4 | 4 · 5 · 4 · 5 |
| v0.3.0 | visit-edit | [r1](runs/v0.3.0/2026-08-11-visit-edit-r1/README.md), [r2](runs/v0.3.0/2026-08-12-visit-edit-r2/README.md), [r3](runs/v0.3.0/2026-08-12-visit-edit-r3/README.md) | 4 · 5 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.2.4 | owners-page-param | [r1](runs/v0.2.4/2026-08-10-owners-page-param-r1/README.md), [r2](runs/v0.2.4/2026-08-12-owners-page-param-r2/README.md), [r3](runs/v0.2.4/2026-08-13-owners-page-param-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 3 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.2.4 | specialty-directory | [r1](runs/v0.2.4/2026-08-11-specialty-directory-r1/README.md) | 5 | 4 | 4 | 5 |
| v0.2.4 | vets-specialty-filter | [r1](runs/v0.2.4/2026-08-11-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.4/2026-08-13-vets-specialty-filter-r2/README.md) | 4 · 4 | 4 · 4 | 4 · 4 | 5 · 5 |
| v0.2.4 | visit-edit | [r1](runs/v0.2.4/2026-08-11-visit-edit-r1/README.md), [r2](runs/v0.2.4/2026-08-12-visit-edit-r2/README.md), [r3](runs/v0.2.4/2026-08-12-visit-edit-r3/README.md) | 4 · 4 · 4 | 4 · 3 · 4 | 4 · 4 · 4 | 4 · 4 · 5 |
| v0.2.3 | owners-page-param | [r1](runs/v0.2.3/2026-08-10-owners-page-param-r1/README.md), [r2](runs/v0.2.3/2026-08-10-owners-page-param-r2/README.md) | 4 · 4 | 4 · 3 | 4 · 4 | 5 · 4 |
| v0.2.3 | specialty-directory | [r1](runs/v0.2.3/2026-08-10-specialty-directory-r1/README.md) | 4 | 4 | 4 | 5 |
| v0.2.3 | vets-specialty-filter | [r1](runs/v0.2.3/2026-08-11-vets-specialty-filter-r1/README.md) | 4 | 4 | 4 | 5 |
| v0.2.3 | visit-edit | [r1](runs/v0.2.3/2026-08-11-visit-edit-r1/README.md) | 4 | 4 | 4 | 5 |
| v0.2.2 | owners-page-param | [r1](runs/v0.2.2/2026-08-08-owners-page-param-r1/README.md) | 4 | 3 | 4 | 5 |
| v0.2.2 | specialty-directory | [r1](runs/v0.2.2/2026-08-08-specialty-directory-r1/README.md), [r2](runs/v0.2.2/2026-08-08-specialty-directory-r2/README.md), [r3](runs/v0.2.2/2026-08-09-specialty-directory-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 4 |
| v0.2.2 | vets-specialty-filter | [r1](runs/v0.2.2/2026-08-08-vets-specialty-filter-r1/README.md) | 4 | 4 | 4 | 4 |
| v0.2.2 | visit-edit | [r1](runs/v0.2.2/2026-08-08-visit-edit-r1/README.md) | 4 | 4 | 4 | 5 |
| v0.2.1 | owners-page-param | [r1](runs/v0.2.1/2026-08-07-owners-page-param-r1/README.md), [r2](runs/v0.2.1/2026-08-07-owners-page-param-r2/README.md), [r3](runs/v0.2.1/2026-08-07-owners-page-param-r3/README.md), [r4](runs/v0.2.1/2026-08-08-owners-page-param-r4/README.md) | 4 · 4 · 4 · 4 | 3 · 3 · 3 · 3 | 4 · 4 · 4 · 4 | 5 · 5 · 5 · 5 |
| v0.2.1 | specialty-directory | [r1](runs/v0.2.1/2026-08-07-specialty-directory-r1/README.md), [r2](runs/v0.2.1/2026-08-08-specialty-directory-r2/README.md), [r3](runs/v0.2.1/2026-08-08-specialty-directory-r3/README.md), [r4](runs/v0.2.1/2026-08-08-specialty-directory-r4/README.md) | 4 · 5 · 5 · 5 | 4 · 4 · 4 · 4 | 4 · 4 · 4 · 4 | 3 · 4 · 4 · 5 |
| v0.2.1 | vets-specialty-filter | [r1](runs/v0.2.1/2026-08-07-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.1/2026-08-08-vets-specialty-filter-r2/README.md) | 4 · 4 | 4 · 4 | 4 · 4 | 4 · 5 |
| v0.2.1 | visit-edit | [r1](runs/v0.2.1/2026-08-07-visit-edit-r1/README.md), [r2](runs/v0.2.1/2026-08-08-visit-edit-r2/README.md) | 4 · 4 | 4 · 4 | 4 · 4 | 4 · 5 |
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
| v0.1.28 | vets-specialty-filter | [r1](runs/v0.1.28/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.28/2026-08-07-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.28/2026-08-07-vets-specialty-filter-r3/README.md), [r4](runs/v0.1.28/2026-08-08-vets-specialty-filter-r4/README.md), [r5](runs/v0.1.28/2026-08-08-vets-specialty-filter-r5/README.md) | 3 · 3 · 3 · 4 · 4 | 3 · 3 · 3 · 3 · 3 | 4 · 3 · 4 · 4 · 4 | 5 · 4 · 5 · 4 · 4 |
| v0.1.28 | visit-edit | [r1](runs/v0.1.28/2026-08-04-visit-edit-r1/README.md), [r2](runs/v0.1.28/2026-08-07-visit-edit-r2/README.md), [r3](runs/v0.1.28/2026-08-07-visit-edit-r3/README.md) | 3 · 4 · 3 | 4 · 3 · 3 | 4 · 4 · 3 | 5 · 5 · 5 |
| v0.1.22 | owners-page-param | [r1](runs/v0.1.22/2026-08-05-owners-page-param-r1/README.md) | 4 | 3 | 4 | 5 |
| v0.1.22 | specialty-directory | [r1](runs/v0.1.22/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.22/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.22/2026-08-06-specialty-directory-r3/README.md) | 1 · 3 · 3 | 1 · 3 · 4 | 1 · 3 · 3 | 3 · 5 · 4 |
| v0.1.22 | vets-specialty-filter | [r1](runs/v0.1.22/2026-08-05-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.22/2026-08-08-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.22/2026-08-08-vets-specialty-filter-r3/README.md) | 4 · 3 · 3 | 3 · 4 · 3 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.1.22 | visit-edit | [r1](runs/v0.1.22/2026-08-05-visit-edit-r1/README.md) | 4 | 4 | 4 | 5 |
| v0.1.18 | owners-page-param | [r1](runs/v0.1.18/2026-08-05-owners-page-param-r1/README.md) | 4 | 4 | 3 | 5 |
| v0.1.18 | specialty-directory | [r1](runs/v0.1.18/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.18/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.18/2026-08-06-specialty-directory-r3/README.md), [r4](runs/v0.1.18/2026-08-06-specialty-directory-r4/README.md), [r5](runs/v0.1.18/2026-08-06-specialty-directory-r5/README.md) | 3 · 3 · 3 · 3 · 2 | 3 · 3 · 3 · 3 · 2.5 | 3 · 3 · 4 · 3 · 2 | 4 · 3 · 5 · 3 · 3 |
| v0.1.18 | vets-specialty-filter | [r1](runs/v0.1.18/2026-08-05-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.18/2026-08-07-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.18/2026-08-08-vets-specialty-filter-r3/README.md) | 4 · 4 · 4 | 3 · 3 · 4 | 4 · 4 · 4 | 5 · 5 · 4 |
| v0.1.18 | visit-edit | [r1](runs/v0.1.18/2026-08-05-visit-edit-r1/README.md) | 4 | 4 | 4 | 5 |
| v0.1.1 | owners-page-param | [r2](runs/v0.1.1/2026-08-05-owners-page-param-r2/README.md) | 4 | 3 | 4 | 5 |
| v0.1.1 | specialty-directory | [r1](runs/v0.1.1/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.1/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.1/2026-08-06-specialty-directory-r3/README.md) | 3 · 3 · 2 | 3 · 3 · 3 | 3 · 3 · 3 | 3 · 4 · 4 |
| v0.1.1 | vets-specialty-filter | [r1](runs/v0.1.1/2026-08-05-vets-specialty-filter-r1/README.md) | 2 | 3 | 4 | 3 |
| v0.1.1 | visit-edit | [r1](runs/v0.1.1/2026-08-05-visit-edit-r1/README.md) | 3 | 4 | 4 | 5 |

The models behind the judged rows — one row per distinct provenance: the run's agent models, the pinned judge, the rubric. A version listed whole shares the row across every judged rep; a cell judged under two provenances names its reps, so a rubric or judge change mid-cell stays attributable:

| Judged rows | Agent models | Judge model | Rubric |
|---|---|---|---|
| v0.3.2, v0.3.1, v0.3.0, v0.2.4, v0.2.3, v0.2.2, v0.2.1, v0.2.0, v0.1.29 | opus-5 · sonnet-5 | claude-opus-5 | [rubric-v1.md](../judge/rubric-v1.md) |
| v0.1.28, v0.1.22, v0.1.18, v0.1.1 | opus-4-8 · opus-5 · sonnet-4-6 | claude-opus-5 | [rubric-v1.md](../judge/rubric-v1.md) |

### Grader concordance

Tier B context, never a claim: the change grader's verdict is the system under test's self-assessment of its own change. The table asks one question — does a `concern` verdict track the machine-verified bar or the advisory judge? Judge quality is a run's mean over its facet medians; the cell holds the median of those means across the group's judged runs, `—` when the judge ran on none.

| Verdict | Runs | Bar cleared | Median judge quality |
|---|---|---|---|
| clear | 39 | 39/39 | 4.0 |
| concern | 51 | 49/51 | 4.0 |

### Escalation check

Derived candidates for the escalation rule, which stays operator-applied (README § Cost accounting and statistical discipline). A pair of adjacent version rows sharing pin and task lists while a trigger trips and either cell holds fewer than 3 reps. Each command re-runs both arms, keeping the added reps adjacent in time. A `~` row in the trend table is an arm of a listed pair still under that depth. Pairs list most severe first — a lost unit cost, then a bar flip, then cost rises, then falls, larger moves first — so the list reads as a backfill queue.

- `owners-page-param` · `v0.2.3 → v0.2.4`: cost per pass $7.18 → $4.46 (-38%)
  `python3 evals/run_eval.py --version v0.2.3 --version v0.2.4 --task owners-page-param --reps 2 --model claude-opus-5 --judge`

### Recorded runs

<details>
<summary>Per-rep detail — 176 runs, the spread behind each trend cell</summary>

Each run folder carries a generated `README.md` presenting the run; the folder's records are the ground truth. Spend and wall are the delivery figures the trend cells aggregate. A multi-rep cell lists every rep's figures in Reps order.

| Version | Task | Reps | Bar | Spend | Wall |
|---|---|---|---|---|---|
| v0.3.2 | owners-page-param | [r1](runs/v0.3.2/2026-08-15-owners-page-param-r1/README.md), [r2](runs/v0.3.2/2026-08-15-owners-page-param-r2/README.md), [r3](runs/v0.3.2/2026-08-15-owners-page-param-r3/README.md) | cleared · cleared · cleared | $9.70 · $5.97 · $7.05 | 18m · 14m · 18m |
| v0.3.2 | specialty-directory | [r1](runs/v0.3.2/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.2/2026-08-15-specialty-directory-r2/README.md), [r3](runs/v0.3.2/2026-08-15-specialty-directory-r3/README.md) | cleared · cleared · cleared | $10.91 · $12.51 · $15.49 | 24m · 38m · 65m |
| v0.3.2 | vets-specialty-filter | [r1](runs/v0.3.2/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.2/2026-08-15-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.2/2026-08-15-vets-specialty-filter-r3/README.md) | cleared · cleared · cleared | $17.02 · $19.11 · $15.59 | 47m · 42m · 48m |
| v0.3.2 | visit-cancel | [r1](runs/v0.3.2/2026-08-15-visit-cancel-r1/README.md), [r2](runs/v0.3.2/2026-08-15-visit-cancel-r2/README.md), [r3](runs/v0.3.2/2026-08-15-visit-cancel-r3/README.md) | cleared · cleared · cleared | $0.48 · $1.07 · $0.94 | 1m · 2m · 2m |
| v0.3.2 | visit-edit | [r1](runs/v0.3.2/2026-08-15-visit-edit-r1/README.md), [r2](runs/v0.3.2/2026-08-15-visit-edit-r2/README.md) | cleared · cleared | $17.51 · $16.03 | 39m · 31m |
| v0.3.1 | owners-page-param | [r1](runs/v0.3.1/2026-08-14-owners-page-param-r1/README.md), [r2](runs/v0.3.1/2026-08-14-owners-page-param-r2/README.md), [r3](runs/v0.3.1/2026-08-14-owners-page-param-r3/README.md), [r4](runs/v0.3.1/2026-08-14-owners-page-param-r4/README.md), [r5](runs/v0.3.1/2026-08-14-owners-page-param-r5/README.md) | cleared · cleared · cleared · cleared · cleared | $8.59 · $5.87 · $4.65 · $7.35 · $6.46 | 18m · 15m · 12m · 16m · 28m |
| v0.3.1 | specialty-directory | [r1](runs/v0.3.1/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.1/2026-08-15-specialty-directory-r2/README.md), [r3](runs/v0.3.1/2026-08-15-specialty-directory-r3/README.md) | cleared · cleared · cleared | $17.03 · $12.03 · $9.03 | 47m · 32m · 31m |
| v0.3.1 | vets-specialty-filter | [r1](runs/v0.3.1/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.1/2026-08-15-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.1/2026-08-15-vets-specialty-filter-r3/README.md) | cleared · cleared · cleared | $18.91 · $17.25 · $17.04 | 47m · 56m · 46m |
| v0.3.1 | visit-cancel | [r1](runs/v0.3.1/2026-08-14-visit-cancel-r1/README.md), [r2](runs/v0.3.1/2026-08-14-visit-cancel-r2/README.md), [r3](runs/v0.3.1/2026-08-15-visit-cancel-r3/README.md), [r4](runs/v0.3.1/2026-08-15-visit-cancel-r4/README.md), [r5](runs/v0.3.1/2026-08-15-visit-cancel-r5/README.md) | cleared · cleared · cleared · cleared · cleared | $1.30 · $1.14 · $0.56 · $1.28 · $0.45 | 3m · 3m · 1m · 3m · 1m |
| v0.3.1 | visit-edit | [r1](runs/v0.3.1/2026-08-15-visit-edit-r1/README.md), [r2](runs/v0.3.1/2026-08-15-visit-edit-r2/README.md), [r3](runs/v0.3.1/2026-08-15-visit-edit-r3/README.md) | cleared · cleared · cleared | $18.38 · $17.32 · $15.04 | 43m · 49m · 34m |
| v0.3.0 | owners-page-param | [r1](runs/v0.3.0/2026-08-11-owners-page-param-r1/README.md), [r2](runs/v0.3.0/2026-08-12-owners-page-param-r2/README.md), [r3](runs/v0.3.0/2026-08-12-owners-page-param-r3/README.md), [r4](runs/v0.3.0/2026-08-13-owners-page-param-r4/README.md), [r5](runs/v0.3.0/2026-08-14-owners-page-param-r5/README.md), [r6](runs/v0.3.0/2026-08-14-owners-page-param-r6/README.md) | cleared · cleared · cleared · cleared · cleared · cleared | $3.70 · $3.95 · $5.00 · $2.94 · $4.04 · $7.32 | 13m · 12m · 14m · 9m · 11m · 23m |
| v0.3.0 | specialty-directory | [r1](runs/v0.3.0/2026-08-11-specialty-directory-r1/README.md), [r2](runs/v0.3.0/2026-08-12-specialty-directory-r2/README.md) | cleared · cleared | $12.04 · $11.37 | 32m · 34m |
| v0.3.0 | vets-specialty-filter | [r1](runs/v0.3.0/2026-08-11-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.0/2026-08-12-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.0/2026-08-12-vets-specialty-filter-r3/README.md), [r4](runs/v0.3.0/2026-08-13-vets-specialty-filter-r4/README.md) | cleared · cleared · cleared · cleared | $21.44 · $15.18 · $16.58 · $16.26 | 60m · 40m · 38m · 46m |
| v0.3.0 | visit-cancel | [r1](runs/v0.3.0/2026-08-11-visit-cancel-r1/README.md), [r2](runs/v0.3.0/2026-08-12-visit-cancel-r2/README.md) | cleared · cleared | $1.17 · $1.26 | 3m · 4m |
| v0.3.0 | visit-edit | [r1](runs/v0.3.0/2026-08-11-visit-edit-r1/README.md), [r2](runs/v0.3.0/2026-08-12-visit-edit-r2/README.md), [r3](runs/v0.3.0/2026-08-12-visit-edit-r3/README.md) | cleared · cleared · cleared | $19.59 · $15.27 · $18.20 | 65m · 42m · 53m |
| v0.2.4 | owners-page-param | [r1](runs/v0.2.4/2026-08-10-owners-page-param-r1/README.md), [r2](runs/v0.2.4/2026-08-12-owners-page-param-r2/README.md), [r3](runs/v0.2.4/2026-08-13-owners-page-param-r3/README.md) | cleared · cleared · cleared | $5.33 · $4.53 · $3.51 | 12m · 14m · 11m |
| v0.2.4 | specialty-directory | [r1](runs/v0.2.4/2026-08-11-specialty-directory-r1/README.md), [r2](runs/v0.2.4/2026-08-11-specialty-directory-r2/README.md), [r3](runs/v0.2.4/2026-08-11-specialty-directory-r3/README.md) | cleared · cleared · cleared | $12.64 · $15.61 · $11.70 | 34m · 42m · 36m |
| v0.2.4 | vets-specialty-filter | [r1](runs/v0.2.4/2026-08-11-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.4/2026-08-13-vets-specialty-filter-r2/README.md) | cleared · cleared | $16.47 · $13.20 | 46m · 33m |
| v0.2.4 | visit-cancel | [r1](runs/v0.2.4/2026-08-11-visit-cancel-r1/README.md) | cleared | $1.16 | 3m |
| v0.2.4 | visit-edit | [r1](runs/v0.2.4/2026-08-11-visit-edit-r1/README.md), [r2](runs/v0.2.4/2026-08-12-visit-edit-r2/README.md), [r3](runs/v0.2.4/2026-08-12-visit-edit-r3/README.md) | cleared · cleared · cleared | $14.89 · $18.39 · $13.77 | 37m · 46m · 37m |
| v0.2.3 | owners-page-param | [r1](runs/v0.2.3/2026-08-10-owners-page-param-r1/README.md), [r2](runs/v0.2.3/2026-08-10-owners-page-param-r2/README.md) | cleared · cleared | $9.58 · $4.78 | 24m · 14m |
| v0.2.3 | specialty-directory | [r1](runs/v0.2.3/2026-08-10-specialty-directory-r1/README.md), [r2](runs/v0.2.3/2026-08-11-specialty-directory-r2/README.md), [r3](runs/v0.2.3/2026-08-11-specialty-directory-r3/README.md) | cleared · cleared · cleared | $18.33 · $14.53 · $11.01 | 50m · 47m · 35m |
| v0.2.3 | vets-specialty-filter | [r1](runs/v0.2.3/2026-08-11-vets-specialty-filter-r1/README.md) | cleared | $13.67 | 34m |
| v0.2.3 | visit-cancel | [r1](runs/v0.2.3/2026-08-11-visit-cancel-r1/README.md) | cleared | $1.11 | 2m |
| v0.2.3 | visit-edit | [r1](runs/v0.2.3/2026-08-11-visit-edit-r1/README.md) | cleared | $18.09 | 49m |
| v0.2.2 | owners-page-param | [r1](runs/v0.2.2/2026-08-08-owners-page-param-r1/README.md) | cleared | $5.88 | 14m |
| v0.2.2 | specialty-directory | [r1](runs/v0.2.2/2026-08-08-specialty-directory-r1/README.md), [r2](runs/v0.2.2/2026-08-08-specialty-directory-r2/README.md), [r3](runs/v0.2.2/2026-08-09-specialty-directory-r3/README.md) | cleared · cleared · cleared | $14.06 · $15.26 · $14.11 | 39m · 38m · 36m |
| v0.2.2 | vets-specialty-filter | [r1](runs/v0.2.2/2026-08-08-vets-specialty-filter-r1/README.md) | cleared | $15.55 | 39m |
| v0.2.2 | visit-cancel | [r1](runs/v0.2.2/2026-08-08-visit-cancel-r1/README.md), [r2](runs/v0.2.2/2026-08-10-visit-cancel-r2/README.md), [r3](runs/v0.2.2/2026-08-10-visit-cancel-r3/README.md) | cleared · cleared · cleared | $1.43 · $0.49 · $1.14 | 4m · 1m · 2m |
| v0.2.2 | visit-edit | [r1](runs/v0.2.2/2026-08-08-visit-edit-r1/README.md) | cleared | $16.90 | 43m |
| v0.2.1 | owners-page-param | [r1](runs/v0.2.1/2026-08-07-owners-page-param-r1/README.md), [r2](runs/v0.2.1/2026-08-07-owners-page-param-r2/README.md), [r3](runs/v0.2.1/2026-08-07-owners-page-param-r3/README.md), [r4](runs/v0.2.1/2026-08-08-owners-page-param-r4/README.md) | cleared · cleared · cleared · cleared | $5.31 · $4.42 · $4.86 · $4.52 | 16m · 11m · 14m · 13m |
| v0.2.1 | specialty-directory | [r1](runs/v0.2.1/2026-08-07-specialty-directory-r1/README.md), [r2](runs/v0.2.1/2026-08-08-specialty-directory-r2/README.md), [r3](runs/v0.2.1/2026-08-08-specialty-directory-r3/README.md), [r4](runs/v0.2.1/2026-08-08-specialty-directory-r4/README.md) | cleared · cleared · cleared · cleared | $12.05 · $19.42 · $18.93 · $15.22 | 37m · 58m · 53m · 38m |
| v0.2.1 | vets-specialty-filter | [r1](runs/v0.2.1/2026-08-07-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.1/2026-08-08-vets-specialty-filter-r2/README.md) | cleared · cleared | $13.30 · $14.90 | 37m · 46m |
| v0.2.1 | visit-cancel | [r1](runs/v0.2.1/2026-08-07-visit-cancel-r1/README.md), [r2](runs/v0.2.1/2026-08-08-visit-cancel-r2/README.md), [r3](runs/v0.2.1/2026-08-10-visit-cancel-r3/README.md), [r4](runs/v0.2.1/2026-08-10-visit-cancel-r4/README.md) | wasted (complete) · cleared · cleared · cleared | $16.22 · $0.34 · $1.31 · $0.42 | 43m · 1m · 3m · 1m |
| v0.2.1 | visit-edit | [r1](runs/v0.2.1/2026-08-07-visit-edit-r1/README.md), [r2](runs/v0.2.1/2026-08-08-visit-edit-r2/README.md) | cleared · cleared | $13.85 · $16.66 | 35m · 52m |
| v0.2.0 | owners-page-param | [r1](runs/v0.2.0/2026-08-04-owners-page-param-r1/README.md), [r2](runs/v0.2.0/2026-08-05-owners-page-param-r2/README.md), [r3](runs/v0.2.0/2026-08-05-owners-page-param-r3/README.md), [r4](runs/v0.2.0/2026-08-07-owners-page-param-r4/README.md), [r5](runs/v0.2.0/2026-08-07-owners-page-param-r5/README.md), [r6](runs/v0.2.0/2026-08-07-owners-page-param-r6/README.md) | cleared · cleared · cleared · cleared · cleared · cleared | $9.29 · $13.10 · $9.38 · $4.78 · $5.83 · $4.70 | 24m · 32m · 16m · 13m · 16m · 14m |
| v0.2.0 | specialty-directory | [r1](runs/v0.2.0/2026-08-04-specialty-directory-r1/README.md) | cleared | $15.49 | 36m |
| v0.2.0 | vets-specialty-filter | [r1](runs/v0.2.0/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.0/2026-08-05-vets-specialty-filter-r2/README.md), [r3](runs/v0.2.0/2026-08-05-vets-specialty-filter-r3/README.md) | cleared · cleared · cleared | $20.37 · $10.12 · $14.60 | 58m · 30m · 44m |
| v0.2.0 | visit-cancel | [r1](runs/v0.2.0/2026-08-04-visit-cancel-r1/README.md), [r2](runs/v0.2.0/2026-08-06-visit-cancel-r2/README.md), [r3](runs/v0.2.0/2026-08-06-visit-cancel-r3/README.md) | cleared · wasted (complete) · wasted (complete) | $1.17 · $15.42 · $23.18 | 3m · 41m · 65m |
| v0.2.0 | visit-edit | [r1](runs/v0.2.0/2026-08-04-visit-edit-r1/README.md) | cleared | $18.09 | 60m |
| v0.1.29 | owners-page-param | [r1](runs/v0.1.29/2026-08-04-owners-page-param-r1/README.md), [r2](runs/v0.1.29/2026-08-05-owners-page-param-r2/README.md), [r3](runs/v0.1.29/2026-08-05-owners-page-param-r3/README.md) | cleared · cleared · cleared | $5.95 · $5.71 · $5.01 | 13m · 13m · 15m |
| v0.1.29 | specialty-directory | [r1](runs/v0.1.29/2026-08-04-specialty-directory-r1/README.md) | cleared | $14.16 | 36m |
| v0.1.29 | vets-specialty-filter | [r1](runs/v0.1.29/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.29/2026-08-05-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.29/2026-08-05-vets-specialty-filter-r3/README.md), [r4](runs/v0.1.29/2026-08-07-vets-specialty-filter-r4/README.md), [r5](runs/v0.1.29/2026-08-07-vets-specialty-filter-r5/README.md) | cleared · cleared · cleared · cleared · cleared | $12.66 · $20.13 · $19.57 · $13.09 · $10.89 | 36m · 47m · 63m · 35m · 31m |
| v0.1.29 | visit-cancel | [r1](runs/v0.1.29/2026-08-06-visit-cancel-r1/README.md), [r2](runs/v0.1.29/2026-08-06-visit-cancel-r2/README.md), [r3](runs/v0.1.29/2026-08-10-visit-cancel-r3/README.md), [r4](runs/v0.1.29/2026-08-10-visit-cancel-r4/README.md) | wasted (complete) · cleared · cleared · cleared | $21.55 · $1.27 · $1.24 · $0.51 | 48m · 4m · 3m · 1m |
| v0.1.29 | visit-edit | [r1](runs/v0.1.29/2026-08-04-visit-edit-r1/README.md), [r2](runs/v0.1.29/2026-08-07-visit-edit-r2/README.md), [r3](runs/v0.1.29/2026-08-07-visit-edit-r3/README.md) | cleared · cleared · cleared | $19.70 · $13.68 · $13.80 | 45m · 36m · 38m |
| v0.1.28 | owners-page-param | [r1](runs/v0.1.28/2026-08-04-owners-page-param-r1/README.md) | cleared | $6.27 | 18m |
| v0.1.28 | specialty-directory | [r1](runs/v0.1.28/2026-08-04-specialty-directory-r1/README.md), [r2](runs/v0.1.28/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.28/2026-08-06-specialty-directory-r3/README.md) | cleared · cleared · cleared | $13.57 · $11.61 · $14.66 | 42m · 35m · 49m |
| v0.1.28 | vets-specialty-filter | [r1](runs/v0.1.28/2026-08-04-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.28/2026-08-07-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.28/2026-08-07-vets-specialty-filter-r3/README.md), [r4](runs/v0.1.28/2026-08-08-vets-specialty-filter-r4/README.md), [r5](runs/v0.1.28/2026-08-08-vets-specialty-filter-r5/README.md) | cleared · cleared · cleared · cleared · cleared | $10.49 · $14.40 · $13.09 · $13.00 · $17.36 | 31m · 54m · 39m · 38m · 57m |
| v0.1.28 | visit-cancel | [r1](runs/v0.1.28/2026-08-04-visit-cancel-r1/README.md), [r2](runs/v0.1.28/2026-08-05-visit-cancel-r2/README.md), [r3](runs/v0.1.28/2026-08-06-visit-cancel-r3/README.md), [r4](runs/v0.1.28/2026-08-06-visit-cancel-r4/README.md), [r5](runs/v0.1.28/2026-08-10-visit-cancel-r5/README.md), [r6](runs/v0.1.28/2026-08-10-visit-cancel-r6/README.md) | cleared · wasted (complete) · cleared · cleared · cleared · cleared | $1.30 · $17.42 · $0.53 · $1.11 · $1.18 · $1.37 | 3m · 56m · 1m · 3m · 3m · 4m |
| v0.1.28 | visit-edit | [r1](runs/v0.1.28/2026-08-04-visit-edit-r1/README.md), [r2](runs/v0.1.28/2026-08-07-visit-edit-r2/README.md), [r3](runs/v0.1.28/2026-08-07-visit-edit-r3/README.md) | cleared · cleared · cleared | $12.19 · $14.02 · $12.65 | 34m · 40m · 36m |
| v0.1.22 | owners-page-param | [r1](runs/v0.1.22/2026-08-05-owners-page-param-r1/README.md) | cleared | $6.00 | 18m |
| v0.1.22 | specialty-directory | [r1](runs/v0.1.22/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.22/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.22/2026-08-06-specialty-directory-r3/README.md) | wasted (stalled) · cleared · cleared | $2.19 · $11.82 · $13.64 | 7m · 41m · 39m |
| v0.1.22 | vets-specialty-filter | [r1](runs/v0.1.22/2026-08-05-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.22/2026-08-08-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.22/2026-08-08-vets-specialty-filter-r3/README.md) | cleared · cleared · cleared | $9.10 · $11.48 · $11.30 | 33m · 33m · 37m |
| v0.1.22 | visit-cancel | [r1](runs/v0.1.22/2026-08-05-visit-cancel-r1/README.md), [r2](runs/v0.1.22/2026-08-05-visit-cancel-r2/README.md), [r3](runs/v0.1.22/2026-08-06-visit-cancel-r3/README.md), [r4](runs/v0.1.22/2026-08-06-visit-cancel-r4/README.md) | cleared · cleared · cleared · cleared | $1.10 · $1.06 · $1.18 · $1.35 | 3m · 3m · 3m · 4m |
| v0.1.22 | visit-edit | [r1](runs/v0.1.22/2026-08-05-visit-edit-r1/README.md) | cleared | $11.73 | 33m |
| v0.1.18 | owners-page-param | [r1](runs/v0.1.18/2026-08-05-owners-page-param-r1/README.md) | cleared | $5.85 | 17m |
| v0.1.18 | specialty-directory | [r1](runs/v0.1.18/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.18/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.18/2026-08-06-specialty-directory-r3/README.md), [r4](runs/v0.1.18/2026-08-06-specialty-directory-r4/README.md), [r5](runs/v0.1.18/2026-08-06-specialty-directory-r5/README.md) | cleared · cleared · cleared · cleared · wasted (timeout) | $9.12 · $13.42 · $13.22 · $12.03 · $13.01 | 25m · 43m · 44m · 33m · 131m |
| v0.1.18 | vets-specialty-filter | [r1](runs/v0.1.18/2026-08-05-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.18/2026-08-07-vets-specialty-filter-r2/README.md), [r3](runs/v0.1.18/2026-08-08-vets-specialty-filter-r3/README.md) | cleared · cleared · cleared | $13.44 · $11.80 · $14.65 | 45m · 36m · 48m |
| v0.1.18 | visit-cancel | [r1](runs/v0.1.18/2026-08-05-visit-cancel-r1/README.md), [r2](runs/v0.1.18/2026-08-05-visit-cancel-r2/README.md), [r3](runs/v0.1.18/2026-08-06-visit-cancel-r3/README.md) | wasted (complete) · wasted (complete) · cleared | $14.45 · $16.15 · $0.42 | 45m · 48m · 1m |
| v0.1.18 | visit-edit | [r1](runs/v0.1.18/2026-08-05-visit-edit-r1/README.md) | cleared | $12.43 | 36m |
| v0.1.1 | owners-page-param | [r1](runs/v0.1.1/2026-08-05-owners-page-param-r1/README.md), [r2](runs/v0.1.1/2026-08-05-owners-page-param-r2/README.md) | cleared · cleared | $5.71 · $6.56 | 14m · 18m |
| v0.1.1 | specialty-directory | [r1](runs/v0.1.1/2026-08-05-specialty-directory-r1/README.md), [r2](runs/v0.1.1/2026-08-06-specialty-directory-r2/README.md), [r3](runs/v0.1.1/2026-08-06-specialty-directory-r3/README.md) | cleared · cleared · wasted (timeout) | $6.52 · $10.58 · $27.04 | 20m · 31m · 127m |
| v0.1.1 | vets-specialty-filter | [r1](runs/v0.1.1/2026-08-05-vets-specialty-filter-r1/README.md) | cleared | $11.61 | 42m |
| v0.1.1 | visit-cancel | [r1](runs/v0.1.1/2026-08-05-visit-cancel-r1/README.md) | wasted (complete) | $17.57 | 58m |
| v0.1.1 | visit-edit | [r1](runs/v0.1.1/2026-08-05-visit-edit-r1/README.md) | cleared | $11.09 | 29m |

</details>
