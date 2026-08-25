# Harness Eval Trend

The bench measures harness versions, not models: each row installs one version in a fresh SUT clone, runs the pipeline on every task prompt, and grades the result. The grade is machine-verified — a held-out oracle plus the project's full test suite; a refusal task grades by its recorded diff and the suite. Method, quality bar, and measurement tiers: [README](../README.md).

SUT: [`woditschka/spring-petclinic`](https://github.com/woditschka/spring-petclinic/tree/agent-team), branch `agent-team`. A sweep pins the branch head as its base commit; each run's manifest records the exact SHA.

Runs on record span 6 executing Claude Code versions (2.1.226–2.1.238); each run's manifest records its own condition.

<p align="center">
  <img src="../../docs/images/eval-trend.drawio.png" width="720" alt="Three aligned panels across every measured harness version: cost of a clearing rep per task, share of reps clearing the bar, and the blind-judge quality median">
</p>

*The figure is a dated snapshot the `update-diagrams` skill redraws at story changes; the tables below are the live series.*

Machine-readable series: [`trend-data.json`](trend-data.json) — the same cells as the tables below, regenerated with this page.

Notes — dated operator commentary recorded in [`notes.toml`](notes.toml); a scoped note renders under its task. Figures never come from notes; the run folders stay the ground truth.

- 2026-08-07 — The three feature prompts were clarified after a discarded v0.2.1 vets-specialty-filter run stalled at the design gate. The prompt had left a control question undecided, and a headless run answers no question. Each prompt now decides its visible entry point (none is in scope) and closes with the unattended clause (README § task contract). Oracle bytes are unchanged, so each task keeps its id; fingerprints change from the next sweep onward.
- 2026-08-11 — Every security review on record ran under a substituted skill. On the plugin channel the bare security-review name in the reviewer's frontmatter resolves to Claude Code's bundled skill of the same name, never the harness checklist. All 49 surviving session transcripts show the substitution, spanning v0.1.1–v0.2.4 and Claude Code 2.1.220–2.1.227. Every affected run still appended its review-feedback record; two ledgers record the observation (v0.2.2 owners-page-param r1, v0.2.4 specialty-directory r3). The condition is uniform across rows, so version comparisons stand, but no recorded security review worked the stack checklist. The skill ships renamed security-checks from the next version onward.
- 2026-08-15 — The judge's patch sanitizer now strips the inline  (confirmed YYYY-MM-DD)  mark as a token instead of dropping its whole line; the  > Provenance:  and  <!-- harness  lines still drop whole. The owners-page-param v0.3.1 note records the doc-fit score the line-drop cost. Judged rows before this date saw line-dropped patches; rows from the next sweep onward see token-stripped ones. Rubric and judge model are unchanged.
- 2026-08-15 — Every claude-dev-mode run through the v0.3.2 sweep executed with the plugin hooks inert: Claude Code creates  plugins/data/<plugin>  before running a plugin hook, the container's read-only plugins share failed that mkdir, and the hook died unrun with a non-blocking exit. The condition is uniform across those rows, so version comparisons stand; no recorded run had the handoff guards or the intake Stop guard active. The launcher fixed and reinstalled 2026-08-15 mounts a private writable overlay at  plugins/data ; hooks are active from the next run. Refusal-task consultation checkpoints across this boundary measure different machinery and never mix.
- 2026-08-16 — The v0.3.3 sweep is the first with the contracts-sync gate check:  gate_checks_run  names it in all twelve feature reps, no rep trips its abort, and the requirement-id-absence critical — the dominant class of the two prior sweeps — produces zero findings ([contracts-sync ADR](../../docs/adr/2026-08-15-contracts-sync-joins-the-gate.md)). Doc-fit judge medians read 5 on all four feature tasks. Whole-sweep agent spend falls to $50.90, below the pre-front-door v0.3.0 row's $52.46. The vets-specialty-filter wall lengthens 47m to 61m while its cost falls 16% — unattributed; a watch item, not a believed shift.

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
| v0.3.8 | [r1](runs/v0.3.8/2026-08-21-owners-page-param-r1/README.md), [r2](runs/v0.3.8/2026-08-21-owners-page-param-r2/README.md), [r3](runs/v0.3.8/2026-08-21-owners-page-param-r3/README.md) | 3/3 |  | $5.62 |  | 14m |
| v0.3.5 | [r1](runs/v0.3.5/2026-08-17-owners-page-param-r1/README.md), [r2](runs/v0.3.5/2026-08-17-owners-page-param-r2/README.md), [r3](runs/v0.3.5/2026-08-18-owners-page-param-r3/README.md) | 3/3 |  | $6.14 |  | 13m |
| v0.3.3 | [r1](runs/v0.3.3/2026-08-15-owners-page-param-r1/README.md), [r2](runs/v0.3.3/2026-08-16-owners-page-param-r2/README.md), [r3](runs/v0.3.3/2026-08-16-owners-page-param-r3/README.md) | 3/3 |  | $7.25 |  | 18m |
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-owners-page-param-r1/README.md), [r2](runs/v0.3.2/2026-08-15-owners-page-param-r2/README.md), [r3](runs/v0.3.2/2026-08-15-owners-page-param-r3/README.md) | 3/3 |  | $7.58 |  | 18m |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-14-owners-page-param-r1/README.md), [r2](runs/v0.3.1/2026-08-14-owners-page-param-r2/README.md), [r3](runs/v0.3.1/2026-08-14-owners-page-param-r3/README.md), [r4](runs/v0.3.1/2026-08-14-owners-page-param-r4/README.md), [r5](runs/v0.3.1/2026-08-14-owners-page-param-r5/README.md) | 5/5 |  | $6.61 |  | 16m |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-owners-page-param-r1/README.md), [r2](runs/v0.3.0/2026-08-12-owners-page-param-r2/README.md), [r3](runs/v0.3.0/2026-08-12-owners-page-param-r3/README.md), [r4](runs/v0.3.0/2026-08-13-owners-page-param-r4/README.md), [r5](runs/v0.3.0/2026-08-14-owners-page-param-r5/README.md), [r6](runs/v0.3.0/2026-08-14-owners-page-param-r6/README.md) | 6/6 |  | $4.49 |  | 13m |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-10-owners-page-param-r1/README.md), [r2](runs/v0.2.4/2026-08-12-owners-page-param-r2/README.md), [r3](runs/v0.2.4/2026-08-13-owners-page-param-r3/README.md) | 3/3 |  | $4.41 |  | 12m |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-10-owners-page-param-r1/README.md), [r2](runs/v0.2.3/2026-08-10-owners-page-param-r2/README.md) | ~2/2 |  | ~$7.18 |  | ~19m |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-owners-page-param-r1/README.md) | 1/1 |  | $5.88 |  | 14m |
| v0.2.1 | [r1](runs/v0.2.1/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.2.1/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.2.1/2026-08-23-owners-page-param-r3/README.md) | 3/3 |  | $7.70 |  | 12m |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.2.0/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.2.0/2026-08-23-owners-page-param-r3/README.md) | 3/3 |  | $6.47 |  | 17m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.29/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.29/2026-08-23-owners-page-param-r3/README.md) | 3/3 |  | $10.36 |  | 18m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.28/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.28/2026-08-23-owners-page-param-r3/README.md) | 3/3 |  | $4.36 |  | 14m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.22/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.22/2026-08-23-owners-page-param-r3/README.md) | 3/3 |  | $5.25 |  | 14m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.18/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.18/2026-08-23-owners-page-param-r3/README.md) | 3/3 |  | $4.11 |  | 13m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.1/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.1/2026-08-23-owners-page-param-r3/README.md) | 3/3 |  | $4.52 |  | 11m |

- 2026-08-15 — v0.3.1: Cost per pass rises $4.49 to $6.58 against v0.3.0, resolved at 5+ reps per arm; the escalation pair cleared at that depth. The growth is two ledger-visible mechanisms, not rework. The intake front door adds the requirements and design stages — $1.7 and $1.3 per rep — that earlier eval flows seeded past ([root-channel ADR](../../docs/adr/2026-08-14-the-root-is-a-channel-not-an-author.md)). The review-plan classifies the change high and draws the four-reviewer floor, where every v0.3.0 rep narrowed to two reviewers. The fixed cost lands hardest on this $4.49 task; the same stages move the $17–19 tasks by 2% or less. The bar clears 5/5; judge medians hold. r5's doc-fit 2 is a sanitizer artifact, not a doc defect. The rep's rewritten PRD paragraph carries  (confirmed 2026-08-14) , and the judge's patch filter drops whole provenance-marked lines. The judge saw the paragraph deleted with nothing added; the committed patch holds the full replacement. The filter needs to strip the mark token, never the line.

#### specialty-directory

feature: Specialty directory page

| Version | Reps | Bar | Ckpt | Cost/pass | Waste | Wall |
|---|---|---|---|---|---|---|
| v0.3.8 | [r1](runs/v0.3.8/2026-08-21-specialty-directory-r1/README.md), [r2](runs/v0.3.8/2026-08-21-specialty-directory-r2/README.md), [r3](runs/v0.3.8/2026-08-21-specialty-directory-r3/README.md) | 3/3 |  | $14.25 |  | 38m |
| v0.3.5 | [r1](runs/v0.3.5/2026-08-17-specialty-directory-r1/README.md), [r2](runs/v0.3.5/2026-08-17-specialty-directory-r2/README.md), [r3](runs/v0.3.5/2026-08-18-specialty-directory-r3/README.md) | 3/3 |  | $16.16 |  | 36m |
| v0.3.3 | [r1](runs/v0.3.3/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.3/2026-08-16-specialty-directory-r2/README.md), [r3](runs/v0.3.3/2026-08-16-specialty-directory-r3/README.md) | 3/3 |  | $12.21 |  | 29m |
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.2/2026-08-15-specialty-directory-r2/README.md), [r3](runs/v0.3.2/2026-08-15-specialty-directory-r3/README.md) | 3/3 |  | $13.05 |  | 38m |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.1/2026-08-15-specialty-directory-r2/README.md), [r3](runs/v0.3.1/2026-08-15-specialty-directory-r3/README.md) | 3/3 |  | $12.80 |  | 32m |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-specialty-directory-r1/README.md), [r2](runs/v0.3.0/2026-08-12-specialty-directory-r2/README.md) | 2/2 |  | $11.72 |  | 33m |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-11-specialty-directory-r1/README.md), [r2](runs/v0.2.4/2026-08-11-specialty-directory-r2/README.md), [r3](runs/v0.2.4/2026-08-11-specialty-directory-r3/README.md) | 3/3 |  | $13.34 |  | 36m |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-10-specialty-directory-r1/README.md), [r2](runs/v0.2.3/2026-08-11-specialty-directory-r2/README.md), [r3](runs/v0.2.3/2026-08-11-specialty-directory-r3/README.md) | 3/3 |  | $14.65 |  | 47m |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-specialty-directory-r1/README.md), [r2](runs/v0.2.2/2026-08-08-specialty-directory-r2/README.md), [r3](runs/v0.2.2/2026-08-09-specialty-directory-r3/README.md) | 3/3 |  | $14.46 |  | 38m |
| v0.2.1 | [r1](runs/v0.2.1/2026-08-23-specialty-directory-r1/README.md), [r2](runs/v0.2.1/2026-08-24-specialty-directory-r2/README.md), [r3](runs/v0.2.1/2026-08-24-specialty-directory-r3/README.md) | 3/3 |  | $13.34 |  | 32m |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.2.0/2026-08-24-specialty-directory-r2/README.md) | 2/2 |  | $14.34 |  | 38m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.29/2026-08-24-specialty-directory-r2/README.md), [r3](runs/v0.1.29/2026-08-24-specialty-directory-r3/README.md) | 3/3 |  | $14.21 |  | 37m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.28/2026-08-24-specialty-directory-r2/README.md), [r3](runs/v0.1.28/2026-08-24-specialty-directory-r3/README.md) | 3/3 |  | $14.27 |  | 48m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.22/2026-08-23-specialty-directory-r2/README.md), [r3](runs/v0.1.22/2026-08-24-specialty-directory-r3/README.md) | 3/3 |  | $11.02 |  | 31m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.18/2026-08-23-specialty-directory-r2/README.md), [r3](runs/v0.1.18/2026-08-24-specialty-directory-r3/README.md) | 2/3 | [6/7](runs/v0.1.18/2026-08-22-specialty-directory-r1/README.md#checkpoints) · [7/7](runs/v0.1.18/2026-08-23-specialty-directory-r2/README.md#checkpoints) · [7/7](runs/v0.1.18/2026-08-24-specialty-directory-r3/README.md#checkpoints) | $12.11 | $7.55 | 24m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.1/2026-08-23-specialty-directory-r2/README.md), [r3](runs/v0.1.1/2026-08-24-specialty-directory-r3/README.md) | 3/3 |  | $9.68 |  | 28m |

- 2026-08-21 — v0.3.5: The +33% against v0.3.3 ($12.09 to $16.12 per rep, 33 to 47 dispatches across the reps) is review-escalation churn, not a per-dispatch cost change. Every v0.3.5 review pass classified high (oversize, design-revision, then prior-critical). Doc-reviewer criticals in two reps — a literal route restated in the PRD's Done-when, the undefined noun "holder" spanning two briefs, then its half-resolved fix — forced PRD re-entries and full-battery repeats. r2 adds three build failures, one a truncation partial. The other tasks moved -16% to +5%, so the sweep delta is this task's tail. One deliberate bar-raise plausibly contributes: v0.3.4 tightened the documentation-standards ownership clause ("a reference is a link plus at most one orienting clause"), and both criticals sit in exactly that class; no other commit between the tags touches review or PRD behavior. The cost is the recorded escalation ladder firing on real findings ([risk-proportional-review ADR](../../docs/adr/2026-07-09-risk-proportional-review.md)).

#### vets-specialty-filter

feature: Filter the vet list by specialty

| Version | Reps | Bar | Ckpt | Cost/pass | Waste | Wall |
|---|---|---|---|---|---|---|
| v0.3.8 | [r1](runs/v0.3.8/2026-08-21-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.8/2026-08-21-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.8/2026-08-21-vets-specialty-filter-r3/README.md) | 3/3 |  | $16.47 |  | 44m |
| v0.3.5 | [r1](runs/v0.3.5/2026-08-17-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.5/2026-08-18-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.5/2026-08-18-vets-specialty-filter-r3/README.md) | 3/3 |  | $14.24 |  | 39m |
| v0.3.3 | [r1](runs/v0.3.3/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.3/2026-08-16-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.3/2026-08-16-vets-specialty-filter-r3/README.md) | 3/3 |  | $14.58 |  | 61m |
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.2/2026-08-15-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.2/2026-08-15-vets-specialty-filter-r3/README.md) | 3/3 |  | $17.35 |  | 47m |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.1/2026-08-15-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.1/2026-08-15-vets-specialty-filter-r3/README.md) | 3/3 |  | $17.75 |  | 47m |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.0/2026-08-12-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.0/2026-08-12-vets-specialty-filter-r3/README.md), [r4](runs/v0.3.0/2026-08-13-vets-specialty-filter-r4/README.md) | 4/4 |  | $17.35 |  | 43m |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-11-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.4/2026-08-13-vets-specialty-filter-r2/README.md) | 2/2 |  | $14.83 |  | 40m |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-11-vets-specialty-filter-r1/README.md) | 1/1 |  | $13.67 |  | 34m |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-vets-specialty-filter-r1/README.md) | 1/1 |  | $15.56 |  | 39m |
| v0.2.1 | [r1](runs/v0.2.1/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.1/2026-08-25-vets-specialty-filter-r2/README.md) | 2/2 |  | $14.44 |  | 42m |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.0/2026-08-25-vets-specialty-filter-r2/README.md) | 2/2 |  | $19.09 |  | 52m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.29/2026-08-25-vets-specialty-filter-r2/README.md) | 2/2 |  | $18.26 |  | 52m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.28/2026-08-24-vets-specialty-filter-r2/README.md) | ~2/2 |  | ~$15.22 |  | ~47m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.22/2026-08-24-vets-specialty-filter-r2/README.md) | ~2/2 |  | ~$9.54 |  | ~32m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.18/2026-08-24-vets-specialty-filter-r2/README.md) | 2/2 |  | $9.85 |  | 34m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.1/2026-08-24-vets-specialty-filter-r2/README.md) | 2/2 |  | $10.55 |  | 30m |

#### visit-cancel

refusal: Cancel a booked visit (unstated conflict with recorded non-goals) — the expected outcome is a refusal: consult and change nothing. The bar inverts to complete, suite green, no `src/` change; whether the run consulted stays an advisory checkpoint, never part of the bar (README § Refusal tasks).

| Version | Reps | Bar | Outcome | Ckpt | Cost/pass | Waste | Wall |
|---|---|---|---|---|---|---|---|
| v0.3.8 | [r1](runs/v0.3.8/2026-08-21-visit-cancel-r1/README.md), [r2](runs/v0.3.8/2026-08-21-visit-cancel-r2/README.md), [r3](runs/v0.3.8/2026-08-21-visit-cancel-r3/README.md) | 3/3 | refused · refused · refused |  | $1.03 |  | 2m |
| v0.3.5 | [r1](runs/v0.3.5/2026-08-17-visit-cancel-r1/README.md), [r2](runs/v0.3.5/2026-08-17-visit-cancel-r2/README.md), [r3](runs/v0.3.5/2026-08-17-visit-cancel-r3/README.md) | 3/3 | refused · refused · refused |  | $1.12 |  | 2m |
| v0.3.3 | [r1](runs/v0.3.3/2026-08-15-visit-cancel-r1/README.md), [r2](runs/v0.3.3/2026-08-16-visit-cancel-r2/README.md), [r3](runs/v0.3.3/2026-08-16-visit-cancel-r3/README.md) | 3/3 | refused · refused · refused |  | $1.07 |  | 2m |
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-visit-cancel-r1/README.md), [r2](runs/v0.3.2/2026-08-15-visit-cancel-r2/README.md), [r3](runs/v0.3.2/2026-08-15-visit-cancel-r3/README.md) | 3/3 | refused* · refused · refused | [3/4](runs/v0.3.2/2026-08-15-visit-cancel-r1/README.md#checkpoints) · [4/4](runs/v0.3.2/2026-08-15-visit-cancel-r2/README.md#checkpoints) · [4/4](runs/v0.3.2/2026-08-15-visit-cancel-r3/README.md#checkpoints) | $0.83 |  | 2m |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-14-visit-cancel-r1/README.md), [r2](runs/v0.3.1/2026-08-14-visit-cancel-r2/README.md), [r3](runs/v0.3.1/2026-08-15-visit-cancel-r3/README.md), [r4](runs/v0.3.1/2026-08-15-visit-cancel-r4/README.md), [r5](runs/v0.3.1/2026-08-15-visit-cancel-r5/README.md) | 5/5 | refused · refused · refused* · refused · refused* | [4/4](runs/v0.3.1/2026-08-14-visit-cancel-r1/README.md#checkpoints) · [4/4](runs/v0.3.1/2026-08-14-visit-cancel-r2/README.md#checkpoints) · [3/4](runs/v0.3.1/2026-08-15-visit-cancel-r3/README.md#checkpoints) · [4/4](runs/v0.3.1/2026-08-15-visit-cancel-r4/README.md#checkpoints) · [3/4](runs/v0.3.1/2026-08-15-visit-cancel-r5/README.md#checkpoints) | $0.95 |  | 3m |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-visit-cancel-r1/README.md), [r2](runs/v0.3.0/2026-08-12-visit-cancel-r2/README.md) | 2/2 | refused · refused |  | $1.21 |  | 3m |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-11-visit-cancel-r1/README.md) | 1/1 | refused |  | $1.16 |  | 3m |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-11-visit-cancel-r1/README.md) | 1/1 | refused |  | $1.11 |  | 2m |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-visit-cancel-r1/README.md), [r2](runs/v0.2.2/2026-08-10-visit-cancel-r2/README.md), [r3](runs/v0.2.2/2026-08-10-visit-cancel-r3/README.md) | 3/3 | refused · refused* · refused | [4/4](runs/v0.2.2/2026-08-08-visit-cancel-r1/README.md#checkpoints) · [3/4](runs/v0.2.2/2026-08-10-visit-cancel-r2/README.md#checkpoints) · [4/4](runs/v0.2.2/2026-08-10-visit-cancel-r3/README.md#checkpoints) | $1.02 |  | 2m |
| v0.2.1 | [r1](runs/v0.2.1/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.2.1/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.2.1/2026-08-23-visit-cancel-r3/README.md) | 3/3 | refused · refused · refused |  | $0.96 |  | 3m |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.2.0/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.2.0/2026-08-23-visit-cancel-r3/README.md) | 3/3 | refused · refused · refused |  | $0.84 |  | 2m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.1.29/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.1.29/2026-08-23-visit-cancel-r3/README.md) | 3/3 | refused · refused · refused |  | $0.92 |  | 2m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.1.28/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.1.28/2026-08-23-visit-cancel-r3/README.md) | 3/3 | refused · refused · refused |  | $0.81 |  | 3m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.1.22/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.1.22/2026-08-23-visit-cancel-r3/README.md) | 3/3 | refused · refused · refused |  | $0.75 |  | 2m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.1.18/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.1.18/2026-08-23-visit-cancel-r3/README.md) | 3/3 | refused* · refused* · refused* | [3/4](runs/v0.1.18/2026-08-23-visit-cancel-r1/README.md#checkpoints) · [3/4](runs/v0.1.18/2026-08-23-visit-cancel-r2/README.md#checkpoints) · [3/4](runs/v0.1.18/2026-08-23-visit-cancel-r3/README.md#checkpoints) | $1.03 |  | 4m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.1.1/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.1.1/2026-08-23-visit-cancel-r3/README.md) | 3/3 | refused* · refused* · refused* | [3/4](runs/v0.1.1/2026-08-23-visit-cancel-r1/README.md#checkpoints) · [3/4](runs/v0.1.1/2026-08-23-visit-cancel-r2/README.md#checkpoints) · [3/4](runs/v0.1.1/2026-08-23-visit-cancel-r3/README.md#checkpoints) | $0.88 |  | 2m |

- 2026-08-08 — Every implementing rep on record (v0.1.18 through v0.2.1) shares one ledger-documented mechanism: the intake expert narrowed NG-4/NG-5 itself, citing the SUT PRD's derived-from-absence hedge as license. Three changes land after the v0.2.1 row and form a condition boundary. Gate 1's scope-lock requires the owner's quoted decision for any Non-Goals row change ([scope-lock ADR](../../docs/adr/2026-08-08-scope-lock-the-request-is-never-the-override.md)). The SUT PRD confirms NG-4/NG-5 as deliberate. An unattended scope conflict halts as a recorded consultation-request instead of an intake decline ([resumable-pauses ADR](../../docs/adr/2026-08-08-unattended-refusals-are-resumable-pauses.md)). A recorded refusal costs more per rep than an intake decline; that ADR carries the figures. A delta across this boundary measures those rules plus the firmed brief, not model judgment. The task keeps its id; the prompt and its fingerprint are unchanged.
- 2026-08-15 — v0.3.1: Two of five reps refuse without the advisory consultation record ( refused* ): each declines at intake in about a minute for $0.45–0.56, appending no consultation-request. The inverted bar passes 5/5 either way, and cost per pass falls $1.21 to $0.95. A consult-less refusal leaves no resumable pause, so the recorded-pause mechanism ([resumable-pauses ADR](../../docs/adr/2026-08-08-unattended-refusals-are-resumable-pauses.md)) engaged in three of five reps.
- 2026-08-16 — v0.3.3: First rows past the plugin-hook boundary: all three reps refuse as recorded consultations at $0.96–1.17, checkpoints full. The transcripts show no EROFS and no Stop-guard block — root dispatched the expert on the  intake-ready  reason alone, so the hook stands as an unexercised backstop. Cost per pass rises $0.83 to $1.07 against the v0.3.2 row's mixed declines — the recorded-pause price ([resumable-pauses ADR](../../docs/adr/2026-08-08-unattended-refusals-are-resumable-pauses.md)).

#### visit-edit

feature: Edit a booked visit

| Version | Reps | Bar | Ckpt | Cost/pass | Waste | Wall |
|---|---|---|---|---|---|---|
| v0.3.8 | [r1](runs/v0.3.8/2026-08-21-visit-edit-r1/README.md), [r2](runs/v0.3.8/2026-08-21-visit-edit-r2/README.md), [r3](runs/v0.3.8/2026-08-21-visit-edit-r3/README.md) | 3/3 |  | $15.79 |  | 37m |
| v0.3.5 | [r1](runs/v0.3.5/2026-08-17-visit-edit-r1/README.md), [r2](runs/v0.3.5/2026-08-18-visit-edit-r2/README.md), [r3](runs/v0.3.5/2026-08-18-visit-edit-r3/README.md) | 3/3 |  | $16.81 |  | 38m |
| v0.3.3 | [r1](runs/v0.3.3/2026-08-16-visit-edit-r1/README.md), [r2](runs/v0.3.3/2026-08-16-visit-edit-r2/README.md), [r3](runs/v0.3.3/2026-08-16-visit-edit-r3/README.md) | 3/3 |  | $15.94 |  | 41m |
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-visit-edit-r1/README.md), [r2](runs/v0.3.2/2026-08-15-visit-edit-r2/README.md) | 2/2 |  | $16.78 |  | 35m |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-15-visit-edit-r1/README.md), [r2](runs/v0.3.1/2026-08-15-visit-edit-r2/README.md), [r3](runs/v0.3.1/2026-08-15-visit-edit-r3/README.md) | 3/3 |  | $16.91 |  | 43m |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-visit-edit-r1/README.md), [r2](runs/v0.3.0/2026-08-12-visit-edit-r2/README.md), [r3](runs/v0.3.0/2026-08-12-visit-edit-r3/README.md) | 3/3 |  | $17.69 |  | 53m |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-11-visit-edit-r1/README.md), [r2](runs/v0.2.4/2026-08-12-visit-edit-r2/README.md), [r3](runs/v0.2.4/2026-08-12-visit-edit-r3/README.md) | 3/3 |  | $15.63 |  | 37m |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-11-visit-edit-r1/README.md) | 1/1 |  | $18.11 |  | 49m |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-visit-edit-r1/README.md) | 1/1 |  | $16.90 |  | 43m |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-23-visit-edit-r1/README.md) | 1/1 |  | $20.14 |  | 57m |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-23-visit-edit-r1/README.md) | 1/1 |  | $17.38 |  | 47m |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-23-visit-edit-r1/README.md) | 1/1 |  | $11.62 |  | 31m |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-23-visit-edit-r1/README.md) | ~1/1 |  | ~$12.26 |  | ~35m |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-23-visit-edit-r1/README.md) | ~1/1 |  | ~$7.90 |  | ~28m |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-23-visit-edit-r1/README.md) | 1/1 |  | $9.03 |  | 22m |

- 2026-08-13 — v0.3.0: The cell runs 16m longer than v0.2.4 at equal depth and spends $2.01 more per pass. The growth sits in the root agent: 94–106k output tokens per rep against v0.2.4's 51–85k, with reviewer wall spans level. Review volume matches — 8–9 review-feedback records per run in both arms. v0.3.0 adds the round ladder's dispatch context, which the root relays serially (round, finding bar, recommendations). Judge medians hold; the bar clears 3/3.
- 2026-08-15 — v0.3.1: The root growth the v0.3.0 note records reverses: root output falls to a 46k-token mean per rep against v0.3.0's 94–106k, root spend $7.40 to $5.08, wall 53m to 43m.  route  now composes each reviewer dispatch's prompt_note and the root appends it verbatim ([root-channel ADR](../../docs/adr/2026-08-14-the-root-is-a-channel-not-an-author.md)). The root saving scales with review traffic — largest here, 4% on the refusal task — and offsets the front door's added stages on the large tasks. The bar clears 3/3; judge medians hold.

### Sweep spend

- Models lists every model the pipeline actually used; the requested pin binds only the root agent. The pin renders beside a version only when the record holds that version under more than one pin.
- The spend columns price one sweep, every task run once: each task cell contributes its mean spend per rep, failures included, and the row sums those means across its tasks. Rows with equal task coverage compare on any rep depth; a task unmeasured in a row adds nothing, so unequal coverage does not compare.
- Grading spend reports the netted share (accounted basis), so Agent spend plus Grading spend approximates the whole-sweep figure; the run pages break each run out.
- Judge spend is the optional Tier C measurement cost: each cell's mean over its judged reps only, summed across tasks like the other columns. `—` means the judge did not run.

| Version | Models | Agent spend | Grading spend | Judge spend |
|---|---|---|---|---|
| v0.3.8 | opus-5 · sonnet-5 | $53.17 | $4.19 | $2.86 |
| v0.3.5 | opus-5 · sonnet-5 | $54.47 | $3.25 | $3.09 |
| v0.3.3 | opus-5 · sonnet-5 | $51.05 | $3.00 | $3.14 |
| v0.3.2 | opus-5 · sonnet-5 | $55.59 | $3.65 | $3.14 |
| v0.3.1 | opus-5 · sonnet-5 | $55.01 | $2.79 | $3.61 |
| v0.3.0 | opus-5 · sonnet-5 | $52.45 | $2.58 | $2.48 |
| v0.2.4 | opus-5 · sonnet-5 | $49.38 | $2.47 | $2.39 |
| v0.2.3 | opus-5 · sonnet-5 | $54.71 | $2.37 | $2.36 |
| v0.2.2 | opus-5 · sonnet-5 | $53.81 | $1.77 | $2.32 |
| v0.2.1 | opus-5 · sonnet-5 | $36.45 | $2.22 | $1.83 |
| v0.2.0 | opus-5 · sonnet-5 | $60.87 | $3.69 | $2.51 |
| v0.1.29 | opus-5 · sonnet-5 | $61.13 | $4.91 | $2.53 |
| v0.1.28 | opus-4-8 · sonnet-4-6 | $46.28 | $2.19 | $2.11 |
| v0.1.22 | opus-4-8 · sonnet-4-6 | $38.82 | $1.61 | $2.07 |
| v0.1.18 | opus-4-8 · sonnet-4-6 | $30.95 | $1.86 | $2.07 |
| v0.1.1 | opus-4-8 · sonnet-4-6 | $34.65 | $2.30 | $2.06 |

### Advisory judge medians

Tier C context, never a claim: a blind judge scores each run's sanitized patch 1–5 per facet, and each score is the median of independent samples against the pinned rubric and model. The scores never enter the quality bar or cost per pass — they exist to show quality drift the bar cannot see. A multi-rep cell lists every rep's score in Reps order — the spread stays visible, never averaged away.

#### owners-page-param

| Version | Reps | design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|---|---|
| v0.3.8 | [r1](runs/v0.3.8/2026-08-21-owners-page-param-r1/README.md), [r2](runs/v0.3.8/2026-08-21-owners-page-param-r2/README.md), [r3](runs/v0.3.8/2026-08-21-owners-page-param-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.3.5 | [r1](runs/v0.3.5/2026-08-17-owners-page-param-r1/README.md), [r2](runs/v0.3.5/2026-08-17-owners-page-param-r2/README.md), [r3](runs/v0.3.5/2026-08-18-owners-page-param-r3/README.md) | 4 · 4 · 4 | 3 · 3 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.3.3 | [r1](runs/v0.3.3/2026-08-15-owners-page-param-r1/README.md), [r2](runs/v0.3.3/2026-08-16-owners-page-param-r2/README.md), [r3](runs/v0.3.3/2026-08-16-owners-page-param-r3/README.md) | 4 · 3 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 3 · 5 |
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-owners-page-param-r1/README.md), [r2](runs/v0.3.2/2026-08-15-owners-page-param-r2/README.md), [r3](runs/v0.3.2/2026-08-15-owners-page-param-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 3 | 4 · 4 · 4 | 5 · 4 · 5 |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-14-owners-page-param-r1/README.md), [r2](runs/v0.3.1/2026-08-14-owners-page-param-r2/README.md), [r3](runs/v0.3.1/2026-08-14-owners-page-param-r3/README.md), [r4](runs/v0.3.1/2026-08-14-owners-page-param-r4/README.md), [r5](runs/v0.3.1/2026-08-14-owners-page-param-r5/README.md) | 4 · 4 · 3 · 3 · 4 | 4 · 4 · 3 · 4 · 3 | 4 · 4 · 4 · 4 · 4 | 4 · 5 · 4 · 4 · 2 |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-owners-page-param-r1/README.md), [r2](runs/v0.3.0/2026-08-12-owners-page-param-r2/README.md), [r3](runs/v0.3.0/2026-08-12-owners-page-param-r3/README.md), [r4](runs/v0.3.0/2026-08-13-owners-page-param-r4/README.md), [r5](runs/v0.3.0/2026-08-14-owners-page-param-r5/README.md), [r6](runs/v0.3.0/2026-08-14-owners-page-param-r6/README.md) | 3 · 3.5 · 4 · 4 · 4 · 4 | 3 · 4 · 4 · 4 · 3 · 3 | 3 · 4 · 4 · 4 · 4 · 4 | 4 · 4.5 · 5 · 5 · 5 · 4 |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-10-owners-page-param-r1/README.md), [r2](runs/v0.2.4/2026-08-12-owners-page-param-r2/README.md), [r3](runs/v0.2.4/2026-08-13-owners-page-param-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 3 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-10-owners-page-param-r1/README.md), [r2](runs/v0.2.3/2026-08-10-owners-page-param-r2/README.md) | 4 · 4 | 4 · 3 | 4 · 4 | 5 · 4 |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-owners-page-param-r1/README.md) | 4 | 3 | 4 | 5 |
| v0.2.1 | [r1](runs/v0.2.1/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.2.1/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.2.1/2026-08-23-owners-page-param-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 4 |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.2.0/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.2.0/2026-08-23-owners-page-param-r3/README.md) | 4 · 4 · 4 | 3 · 4 · 3 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.29/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.29/2026-08-23-owners-page-param-r3/README.md) | 4 · 4 · 4 | 3 · 3 · 3 | 4 · 3 · 4 | 4 · 5 · 5 |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.28/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.28/2026-08-23-owners-page-param-r3/README.md) | 3 · 4 · 3 | 4 · 3 · 4 | 3 · 4 · 4 | 5 · 5 · 4 |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.22/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.22/2026-08-23-owners-page-param-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 3 | 3 · 4 · 4 | 5 · 5 · 5 |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.18/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.18/2026-08-23-owners-page-param-r3/README.md) | 3 · 3 · 4 | 3 · 3 · 4 | 3 · 3 · 4 | 5 · 5 · 5 |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.1/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.1/2026-08-23-owners-page-param-r3/README.md) | 3.5 · 4 · 4 | 4 · 3 · 3 | 3.5 · 3 · 4 | 4.5 · 5 · 5 |

#### specialty-directory

| Version | Reps | design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|---|---|
| v0.3.8 | [r1](runs/v0.3.8/2026-08-21-specialty-directory-r1/README.md), [r2](runs/v0.3.8/2026-08-21-specialty-directory-r2/README.md), [r3](runs/v0.3.8/2026-08-21-specialty-directory-r3/README.md) | 3 · 5 · 4 | 3 · 4 · 4 | 3 · 4 · 4 | 4 · 5 · 5 |
| v0.3.5 | [r1](runs/v0.3.5/2026-08-17-specialty-directory-r1/README.md), [r2](runs/v0.3.5/2026-08-17-specialty-directory-r2/README.md), [r3](runs/v0.3.5/2026-08-18-specialty-directory-r3/README.md) | 5 · 5 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 5 · 4 |
| v0.3.3 | [r1](runs/v0.3.3/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.3/2026-08-16-specialty-directory-r2/README.md), [r3](runs/v0.3.3/2026-08-16-specialty-directory-r3/README.md) | 4 · 4 · 5 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.2/2026-08-15-specialty-directory-r2/README.md), [r3](runs/v0.3.2/2026-08-15-specialty-directory-r3/README.md) | 3 · 4 · 4 | 4 · 4 · 4 | 4 · 3 · 4 | 4 · 5 · 5 |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.1/2026-08-15-specialty-directory-r2/README.md), [r3](runs/v0.3.1/2026-08-15-specialty-directory-r3/README.md) | 5 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-specialty-directory-r1/README.md), [r2](runs/v0.3.0/2026-08-12-specialty-directory-r2/README.md) | 4 · 5 | 4 · 4 | 4 · 5 | 5 · 5 |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-11-specialty-directory-r1/README.md) | 5 | 4 | 4 | 5 |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-10-specialty-directory-r1/README.md) | 4 | 4 | 4 | 5 |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-specialty-directory-r1/README.md), [r2](runs/v0.2.2/2026-08-08-specialty-directory-r2/README.md), [r3](runs/v0.2.2/2026-08-09-specialty-directory-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 4 |
| v0.2.1 | [r1](runs/v0.2.1/2026-08-23-specialty-directory-r1/README.md), [r2](runs/v0.2.1/2026-08-24-specialty-directory-r2/README.md), [r3](runs/v0.2.1/2026-08-24-specialty-directory-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 5 · 4 |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.2.0/2026-08-24-specialty-directory-r2/README.md) | 4 · 4 | 4 · 4 | 4 · 4 | 5 · 5 |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.29/2026-08-24-specialty-directory-r2/README.md), [r3](runs/v0.1.29/2026-08-24-specialty-directory-r3/README.md) | 5 · 5 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.28/2026-08-24-specialty-directory-r2/README.md), [r3](runs/v0.1.28/2026-08-24-specialty-directory-r3/README.md) | 3 · 3 · 2 | 3 · 3 · 3 | 3 · 3 · 3 | 5 · 4 · 4 |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.22/2026-08-23-specialty-directory-r2/README.md), [r3](runs/v0.1.22/2026-08-24-specialty-directory-r3/README.md) | 4 · 3 · 3 | 4 · 3 · 4 | 3 · 3 · 4 | 3 · 4 · 5 |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.18/2026-08-23-specialty-directory-r2/README.md), [r3](runs/v0.1.18/2026-08-24-specialty-directory-r3/README.md) | 3 · 3 · 3 | 3 · 3 · 3 | 3 · 3 · 3 | 3 · 4 · 4 |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.1/2026-08-23-specialty-directory-r2/README.md), [r3](runs/v0.1.1/2026-08-24-specialty-directory-r3/README.md) | 3 · 3 · 4 | 4 · 3 · 4 | 4 · 3 · 3 | 4 · 4 · 5 |

#### vets-specialty-filter

| Version | Reps | design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|---|---|
| v0.3.8 | [r1](runs/v0.3.8/2026-08-21-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.8/2026-08-21-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.8/2026-08-21-vets-specialty-filter-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 5 · 5 |
| v0.3.5 | [r1](runs/v0.3.5/2026-08-17-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.5/2026-08-18-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.5/2026-08-18-vets-specialty-filter-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.3.3 | [r1](runs/v0.3.3/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.3/2026-08-16-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.3/2026-08-16-vets-specialty-filter-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.2/2026-08-15-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.2/2026-08-15-vets-specialty-filter-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.1/2026-08-15-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.1/2026-08-15-vets-specialty-filter-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 3 · 5 · 5 |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.0/2026-08-12-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.0/2026-08-12-vets-specialty-filter-r3/README.md), [r4](runs/v0.3.0/2026-08-13-vets-specialty-filter-r4/README.md) | 4 · 4 · 4 · 4 | 4 · 4 · 4 · 4 | 4 · 4 · 5 · 4 | 4 · 5 · 4 · 5 |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-11-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.4/2026-08-13-vets-specialty-filter-r2/README.md) | 4 · 4 | 4 · 4 | 4 · 4 | 5 · 5 |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-11-vets-specialty-filter-r1/README.md) | 4 | 4 | 4 | 5 |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-vets-specialty-filter-r1/README.md) | 4 | 4 | 4 | 4 |
| v0.2.1 | [r1](runs/v0.2.1/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.1/2026-08-25-vets-specialty-filter-r2/README.md) | 4 · 4 | 4 · 4 | 4 · 4 | 5 · 5 |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.0/2026-08-25-vets-specialty-filter-r2/README.md) | 4 · 4 | 4 · 4 | 4 · 4 | 5 · 5 |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.29/2026-08-25-vets-specialty-filter-r2/README.md) | 4 · 4 | 4 · 4 | 4 · 4 | 5 · 5 |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.28/2026-08-24-vets-specialty-filter-r2/README.md) | 4 · 4 | 4 · 4 | 4 · 4 | 5 · 5 |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.22/2026-08-24-vets-specialty-filter-r2/README.md) | 4 · 4 | 4 · 3 | 4 · 4 | 5 · 5 |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.18/2026-08-24-vets-specialty-filter-r2/README.md) | 3 · 3 | 3 · 3 | 3 · 4 | 5 · 4 |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.1/2026-08-24-vets-specialty-filter-r2/README.md) | 2 · 4 | 4 · 3 | 3 · 4 | 5 · 4 |

#### visit-edit

| Version | Reps | design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|---|---|
| v0.3.8 | [r1](runs/v0.3.8/2026-08-21-visit-edit-r1/README.md), [r2](runs/v0.3.8/2026-08-21-visit-edit-r2/README.md), [r3](runs/v0.3.8/2026-08-21-visit-edit-r3/README.md) | 4 · 4 · 5 | 4 · 3 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.3.5 | [r1](runs/v0.3.5/2026-08-17-visit-edit-r1/README.md), [r2](runs/v0.3.5/2026-08-18-visit-edit-r2/README.md), [r3](runs/v0.3.5/2026-08-18-visit-edit-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 4 |
| v0.3.3 | [r1](runs/v0.3.3/2026-08-16-visit-edit-r1/README.md), [r2](runs/v0.3.3/2026-08-16-visit-edit-r2/README.md), [r3](runs/v0.3.3/2026-08-16-visit-edit-r3/README.md) | 4 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.3.2 | [r1](runs/v0.3.2/2026-08-15-visit-edit-r1/README.md), [r2](runs/v0.3.2/2026-08-15-visit-edit-r2/README.md) | 4 · 4 | 3 · 4 | 4 · 4 | 5 · 5 |
| v0.3.1 | [r1](runs/v0.3.1/2026-08-15-visit-edit-r1/README.md), [r2](runs/v0.3.1/2026-08-15-visit-edit-r2/README.md), [r3](runs/v0.3.1/2026-08-15-visit-edit-r3/README.md) | 5 · 4 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 3 · 4 · 5 |
| v0.3.0 | [r1](runs/v0.3.0/2026-08-11-visit-edit-r1/README.md), [r2](runs/v0.3.0/2026-08-12-visit-edit-r2/README.md), [r3](runs/v0.3.0/2026-08-12-visit-edit-r3/README.md) | 4 · 5 · 4 | 4 · 4 · 4 | 4 · 4 · 4 | 5 · 5 · 5 |
| v0.2.4 | [r1](runs/v0.2.4/2026-08-11-visit-edit-r1/README.md), [r2](runs/v0.2.4/2026-08-12-visit-edit-r2/README.md), [r3](runs/v0.2.4/2026-08-12-visit-edit-r3/README.md) | 4 · 4 · 4 | 4 · 3 · 4 | 4 · 4 · 4 | 4 · 4 · 5 |
| v0.2.3 | [r1](runs/v0.2.3/2026-08-11-visit-edit-r1/README.md) | 4 | 4 | 4 | 5 |
| v0.2.2 | [r1](runs/v0.2.2/2026-08-08-visit-edit-r1/README.md) | 4 | 4 | 4 | 5 |
| v0.2.0 | [r1](runs/v0.2.0/2026-08-23-visit-edit-r1/README.md) | 4 | 4 | 4 | 4 |
| v0.1.29 | [r1](runs/v0.1.29/2026-08-23-visit-edit-r1/README.md) | 4 | 4 | 4 | 4 |
| v0.1.28 | [r1](runs/v0.1.28/2026-08-23-visit-edit-r1/README.md) | 3 | 4 | 4 | 5 |
| v0.1.22 | [r1](runs/v0.1.22/2026-08-23-visit-edit-r1/README.md) | 3 | 3 | 4 | 4 |
| v0.1.18 | [r1](runs/v0.1.18/2026-08-23-visit-edit-r1/README.md) | 3 | 3 | 3 | 5 |
| v0.1.1 | [r1](runs/v0.1.1/2026-08-23-visit-edit-r1/README.md) | 3 | 3 | 3 | 5 |

The models behind the judged rows — one row per distinct provenance: the run's agent models, the pinned judge, the rubric. A version listed whole shares the row across every judged rep; a cell judged under two provenances names its reps, so a rubric or judge change mid-cell stays attributable:

| Judged rows | Agent models | Judge model | Rubric |
|---|---|---|---|
| v0.3.8, v0.3.5 owners-page-param, v0.3.5 specialty-directory, v0.3.5 vets-specialty-filter ([r1](runs/v0.3.5/2026-08-17-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.5/2026-08-18-vets-specialty-filter-r2/README.md)), v0.3.5 visit-edit, v0.3.3, v0.3.2, v0.3.1, v0.3.0, v0.2.4, v0.2.3, v0.2.2, v0.2.1, v0.2.0, v0.1.29 | opus-5 · sonnet-5 | claude-opus-5 | [rubric-v1.md](../judge/rubric-v1.md) |
| v0.3.5 vets-specialty-filter ([r3](runs/v0.3.5/2026-08-18-vets-specialty-filter-r3/README.md)) | opus-5 | claude-opus-5 | [rubric-v1.md](../judge/rubric-v1.md) |
| v0.1.28, v0.1.22, v0.1.18, v0.1.1 | opus-4-8 · sonnet-4-6 | claude-opus-5 | [rubric-v1.md](../judge/rubric-v1.md) |

### Grader concordance

Tier B context, never a claim: the change grader's verdict is the system under test's self-assessment of its own change. The table asks one question — does a `concern` verdict track the machine-verified bar or the advisory judge? Judge quality is a run's mean over its facet medians; the cell holds the median of those means across the group's judged runs, `—` when the judge ran on none.

| Verdict | Runs | Bar cleared | Median judge quality |
|---|---|---|---|
| clear | 69 | 69/69 | 4.0 |
| concern | 68 | 67/68 | 4.2 |

### Escalation check

Derived candidates for the escalation rule, which stays operator-applied (README § Cost accounting and statistical discipline). A pair of adjacent version rows sharing pin and task lists while a trigger trips and either cell holds fewer than 3 reps. Each command re-runs both arms, keeping the added reps adjacent in time. A `~` row in the trend table is an arm of a listed pair still under that depth. Pairs list most severe first — a lost unit cost, then a bar flip, then cost rises, then falls, larger moves first — so the list reads as a backfill queue.

- `vets-specialty-filter` · `v0.1.22 → v0.1.28`: cost per pass $9.54 → $15.22 (+60%)
  `python3 evals/run_eval.py --version v0.1.22 --version v0.1.28 --task vets-specialty-filter --reps 2 --model claude-opus-4-8 --judge`
- `visit-edit` · `v0.1.18 → v0.1.22`: cost per pass $7.90 → $12.26 (+55%)
  `python3 evals/run_eval.py --version v0.1.18 --version v0.1.22 --task visit-edit --reps 2 --model claude-opus-4-8 --judge`
- `owners-page-param` · `v0.2.3 → v0.2.4`: cost per pass $7.18 → $4.41 (-39%)
  `python3 evals/run_eval.py --version v0.2.3 --version v0.2.4 --task owners-page-param --reps 2 --model claude-opus-5 --judge`

### Settled moves without a note

Settled pairs — both arms at the confirmation depth, so the escalation queue no longer lists them — whose cost per pass moved past 30% of the earlier cell with no explaining operator note: one scoped to the task and either of the pair's versions, or a task-wide condition note; dated no earlier than the younger cell's first rep (both rows existed when it was written), and matching the pair's pin when it names a model. The README's rule is the reason this renders: a rise with no named mechanism is a regression at any percentage. A `>=` figure is a lower bound — a rep's spend went unrecorded. Dev rows never list: a pre-release move is resolved by the release decision, not a note. Resolve a row by attributing the move from the committed ledgers and landing the note; rows list rises before falls, larger moves first.

- `owners-page-param` · `v0.1.29 → v0.2.0`: cost per pass $10.36 → $6.47 (-38%), no explaining note

### Recorded runs

<details>
<summary>Per-rep detail — 206 runs, the spread behind each trend cell</summary>

Each run folder carries a generated `README.md` presenting the run; the folder's records are the ground truth. Spend and wall are the delivery figures the trend cells aggregate. A multi-rep cell lists every rep's figures in Reps order.

| Version | Task | Reps | Bar | Spend | Wall |
|---|---|---|---|---|---|
| v0.3.8 | owners-page-param | [r1](runs/v0.3.8/2026-08-21-owners-page-param-r1/README.md), [r2](runs/v0.3.8/2026-08-21-owners-page-param-r2/README.md), [r3](runs/v0.3.8/2026-08-21-owners-page-param-r3/README.md) | cleared · cleared · cleared | $4.82 · $6.44 · $5.60 | 14m · 20m · 14m |
| v0.3.8 | specialty-directory | [r1](runs/v0.3.8/2026-08-21-specialty-directory-r1/README.md), [r2](runs/v0.3.8/2026-08-21-specialty-directory-r2/README.md), [r3](runs/v0.3.8/2026-08-21-specialty-directory-r3/README.md) | cleared · cleared · cleared | $11.33 · $16.65 · $14.79 | 51m · 34m · 38m |
| v0.3.8 | vets-specialty-filter | [r1](runs/v0.3.8/2026-08-21-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.8/2026-08-21-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.8/2026-08-21-vets-specialty-filter-r3/README.md) | cleared · cleared · cleared | $16.94 · $17.42 · $15.06 | 53m · 44m · 36m |
| v0.3.8 | visit-cancel | [r1](runs/v0.3.8/2026-08-21-visit-cancel-r1/README.md), [r2](runs/v0.3.8/2026-08-21-visit-cancel-r2/README.md), [r3](runs/v0.3.8/2026-08-21-visit-cancel-r3/README.md) | cleared · cleared · cleared | $1.02 · $0.98 · $1.10 | 2m · 2m · 3m |
| v0.3.8 | visit-edit | [r1](runs/v0.3.8/2026-08-21-visit-edit-r1/README.md), [r2](runs/v0.3.8/2026-08-21-visit-edit-r2/README.md), [r3](runs/v0.3.8/2026-08-21-visit-edit-r3/README.md) | cleared · cleared · cleared | $18.23 · $16.51 · $12.64 | 42m · 37m · 29m |
| v0.3.5 | owners-page-param | [r1](runs/v0.3.5/2026-08-17-owners-page-param-r1/README.md), [r2](runs/v0.3.5/2026-08-17-owners-page-param-r2/README.md), [r3](runs/v0.3.5/2026-08-18-owners-page-param-r3/README.md) | cleared · cleared · cleared | $4.33 · $5.13 · $8.94 | 13m · 12m · 18m |
| v0.3.5 | specialty-directory | [r1](runs/v0.3.5/2026-08-17-specialty-directory-r1/README.md), [r2](runs/v0.3.5/2026-08-17-specialty-directory-r2/README.md), [r3](runs/v0.3.5/2026-08-18-specialty-directory-r3/README.md) | cleared · cleared · cleared | $14.99 · $18.04 · $15.43 | 36m · 42m · 36m |
| v0.3.5 | vets-specialty-filter | [r1](runs/v0.3.5/2026-08-17-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.5/2026-08-18-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.5/2026-08-18-vets-specialty-filter-r3/README.md) | cleared · cleared · cleared | $16.74 · $13.08 · $12.90 | 42m · 35m · 39m |
| v0.3.5 | visit-cancel | [r1](runs/v0.3.5/2026-08-17-visit-cancel-r1/README.md), [r2](runs/v0.3.5/2026-08-17-visit-cancel-r2/README.md), [r3](runs/v0.3.5/2026-08-17-visit-cancel-r3/README.md) | cleared · cleared · cleared | $1.41 · $0.93 · $1.04 | 3m · 2m · 2m |
| v0.3.5 | visit-edit | [r1](runs/v0.3.5/2026-08-17-visit-edit-r1/README.md), [r2](runs/v0.3.5/2026-08-18-visit-edit-r2/README.md), [r3](runs/v0.3.5/2026-08-18-visit-edit-r3/README.md) | cleared · cleared · cleared | $16.87 · $16.73 · $16.84 | 38m · 35m · 40m |
| v0.3.3 | owners-page-param | [r1](runs/v0.3.3/2026-08-15-owners-page-param-r1/README.md), [r2](runs/v0.3.3/2026-08-16-owners-page-param-r2/README.md), [r3](runs/v0.3.3/2026-08-16-owners-page-param-r3/README.md) | cleared · cleared · cleared | $7.75 · $7.82 · $6.18 | 16m · 18m · 19m |
| v0.3.3 | specialty-directory | [r1](runs/v0.3.3/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.3/2026-08-16-specialty-directory-r2/README.md), [r3](runs/v0.3.3/2026-08-16-specialty-directory-r3/README.md) | cleared · cleared · cleared | $12.31 · $11.27 · $13.04 | 29m · 27m · 35m |
| v0.3.3 | vets-specialty-filter | [r1](runs/v0.3.3/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.3/2026-08-16-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.3/2026-08-16-vets-specialty-filter-r3/README.md) | cleared · cleared · cleared | $12.22 · $16.10 · $15.42 | 32m · 68m · 61m |
| v0.3.3 | visit-cancel | [r1](runs/v0.3.3/2026-08-15-visit-cancel-r1/README.md), [r2](runs/v0.3.3/2026-08-16-visit-cancel-r2/README.md), [r3](runs/v0.3.3/2026-08-16-visit-cancel-r3/README.md) | cleared · cleared · cleared | $1.08 · $0.96 · $1.17 | 2m · 2m · 3m |
| v0.3.3 | visit-edit | [r1](runs/v0.3.3/2026-08-16-visit-edit-r1/README.md), [r2](runs/v0.3.3/2026-08-16-visit-edit-r2/README.md), [r3](runs/v0.3.3/2026-08-16-visit-edit-r3/README.md) | cleared · cleared · cleared | $13.46 · $15.70 · $18.68 | 35m · 46m · 41m |
| v0.3.2 | owners-page-param | [r1](runs/v0.3.2/2026-08-15-owners-page-param-r1/README.md), [r2](runs/v0.3.2/2026-08-15-owners-page-param-r2/README.md), [r3](runs/v0.3.2/2026-08-15-owners-page-param-r3/README.md) | cleared · cleared · cleared | $9.70 · $5.99 · $7.05 | 18m · 14m · 18m |
| v0.3.2 | specialty-directory | [r1](runs/v0.3.2/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.2/2026-08-15-specialty-directory-r2/README.md), [r3](runs/v0.3.2/2026-08-15-specialty-directory-r3/README.md) | cleared · cleared · cleared | $10.93 · $12.70 · $15.52 | 24m · 38m · 65m |
| v0.3.2 | vets-specialty-filter | [r1](runs/v0.3.2/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.2/2026-08-15-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.2/2026-08-15-vets-specialty-filter-r3/README.md) | cleared · cleared · cleared | $17.07 · $19.20 · $15.79 | 47m · 42m · 48m |
| v0.3.2 | visit-cancel | [r1](runs/v0.3.2/2026-08-15-visit-cancel-r1/README.md), [r2](runs/v0.3.2/2026-08-15-visit-cancel-r2/README.md), [r3](runs/v0.3.2/2026-08-15-visit-cancel-r3/README.md) | cleared · cleared · cleared | $0.48 · $1.07 · $0.94 | 1m · 2m · 2m |
| v0.3.2 | visit-edit | [r1](runs/v0.3.2/2026-08-15-visit-edit-r1/README.md), [r2](runs/v0.3.2/2026-08-15-visit-edit-r2/README.md) | cleared · cleared | $17.46 · $16.11 | 39m · 31m |
| v0.3.1 | owners-page-param | [r1](runs/v0.3.1/2026-08-14-owners-page-param-r1/README.md), [r2](runs/v0.3.1/2026-08-14-owners-page-param-r2/README.md), [r3](runs/v0.3.1/2026-08-14-owners-page-param-r3/README.md), [r4](runs/v0.3.1/2026-08-14-owners-page-param-r4/README.md), [r5](runs/v0.3.1/2026-08-14-owners-page-param-r5/README.md) | cleared · cleared · cleared · cleared · cleared | $8.66 · $5.82 · $4.70 · $7.39 · $6.46 | 18m · 15m · 12m · 16m · 28m |
| v0.3.1 | specialty-directory | [r1](runs/v0.3.1/2026-08-15-specialty-directory-r1/README.md), [r2](runs/v0.3.1/2026-08-15-specialty-directory-r2/README.md), [r3](runs/v0.3.1/2026-08-15-specialty-directory-r3/README.md) | cleared · cleared · cleared | $17.19 · $12.03 · $9.17 | 47m · 32m · 31m |
| v0.3.1 | vets-specialty-filter | [r1](runs/v0.3.1/2026-08-15-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.1/2026-08-15-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.1/2026-08-15-vets-specialty-filter-r3/README.md) | cleared · cleared · cleared | $18.95 · $17.24 · $17.06 | 47m · 56m · 46m |
| v0.3.1 | visit-cancel | [r1](runs/v0.3.1/2026-08-14-visit-cancel-r1/README.md), [r2](runs/v0.3.1/2026-08-14-visit-cancel-r2/README.md), [r3](runs/v0.3.1/2026-08-15-visit-cancel-r3/README.md), [r4](runs/v0.3.1/2026-08-15-visit-cancel-r4/README.md), [r5](runs/v0.3.1/2026-08-15-visit-cancel-r5/README.md) | cleared · cleared · cleared · cleared · cleared | $1.30 · $1.14 · $0.56 · $1.28 · $0.45 | 3m · 3m · 1m · 3m · 1m |
| v0.3.1 | visit-edit | [r1](runs/v0.3.1/2026-08-15-visit-edit-r1/README.md), [r2](runs/v0.3.1/2026-08-15-visit-edit-r2/README.md), [r3](runs/v0.3.1/2026-08-15-visit-edit-r3/README.md) | cleared · cleared · cleared | $18.38 · $17.36 · $15.00 | 43m · 49m · 34m |
| v0.3.0 | owners-page-param | [r1](runs/v0.3.0/2026-08-11-owners-page-param-r1/README.md), [r2](runs/v0.3.0/2026-08-12-owners-page-param-r2/README.md), [r3](runs/v0.3.0/2026-08-12-owners-page-param-r3/README.md), [r4](runs/v0.3.0/2026-08-13-owners-page-param-r4/README.md), [r5](runs/v0.3.0/2026-08-14-owners-page-param-r5/README.md), [r6](runs/v0.3.0/2026-08-14-owners-page-param-r6/README.md) | cleared · cleared · cleared · cleared · cleared · cleared | $3.61 · $3.98 · $4.99 · $3.00 · $4.02 · $7.32 | 13m · 12m · 14m · 9m · 11m · 23m |
| v0.3.0 | specialty-directory | [r1](runs/v0.3.0/2026-08-11-specialty-directory-r1/README.md), [r2](runs/v0.3.0/2026-08-12-specialty-directory-r2/README.md) | cleared · cleared | $12.04 · $11.40 | 32m · 34m |
| v0.3.0 | vets-specialty-filter | [r1](runs/v0.3.0/2026-08-11-vets-specialty-filter-r1/README.md), [r2](runs/v0.3.0/2026-08-12-vets-specialty-filter-r2/README.md), [r3](runs/v0.3.0/2026-08-12-vets-specialty-filter-r3/README.md), [r4](runs/v0.3.0/2026-08-13-vets-specialty-filter-r4/README.md) | cleared · cleared · cleared · cleared | $21.44 · $15.21 · $16.48 · $16.26 | 60m · 40m · 38m · 46m |
| v0.3.0 | visit-cancel | [r1](runs/v0.3.0/2026-08-11-visit-cancel-r1/README.md), [r2](runs/v0.3.0/2026-08-12-visit-cancel-r2/README.md) | cleared · cleared | $1.17 · $1.26 | 3m · 4m |
| v0.3.0 | visit-edit | [r1](runs/v0.3.0/2026-08-11-visit-edit-r1/README.md), [r2](runs/v0.3.0/2026-08-12-visit-edit-r2/README.md), [r3](runs/v0.3.0/2026-08-12-visit-edit-r3/README.md) | cleared · cleared · cleared | $19.59 · $15.27 · $18.20 | 65m · 42m · 53m |
| v0.2.4 | owners-page-param | [r1](runs/v0.2.4/2026-08-10-owners-page-param-r1/README.md), [r2](runs/v0.2.4/2026-08-12-owners-page-param-r2/README.md), [r3](runs/v0.2.4/2026-08-13-owners-page-param-r3/README.md) | cleared · cleared · cleared | $5.32 · $4.48 · $3.44 | 12m · 15m · 11m |
| v0.2.4 | specialty-directory | [r1](runs/v0.2.4/2026-08-11-specialty-directory-r1/README.md), [r2](runs/v0.2.4/2026-08-11-specialty-directory-r2/README.md), [r3](runs/v0.2.4/2026-08-11-specialty-directory-r3/README.md) | cleared · cleared · cleared | $12.64 · $15.68 · $11.70 | 34m · 42m · 36m |
| v0.2.4 | vets-specialty-filter | [r1](runs/v0.2.4/2026-08-11-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.4/2026-08-13-vets-specialty-filter-r2/README.md) | cleared · cleared | $16.47 · $13.20 | 46m · 33m |
| v0.2.4 | visit-cancel | [r1](runs/v0.2.4/2026-08-11-visit-cancel-r1/README.md) | cleared | $1.16 | 3m |
| v0.2.4 | visit-edit | [r1](runs/v0.2.4/2026-08-11-visit-edit-r1/README.md), [r2](runs/v0.2.4/2026-08-12-visit-edit-r2/README.md), [r3](runs/v0.2.4/2026-08-12-visit-edit-r3/README.md) | cleared · cleared · cleared | $14.73 · $18.39 · $13.77 | 37m · 46m · 37m |
| v0.2.3 | owners-page-param | [r1](runs/v0.2.3/2026-08-10-owners-page-param-r1/README.md), [r2](runs/v0.2.3/2026-08-10-owners-page-param-r2/README.md) | cleared · cleared | $9.52 · $4.84 | 24m · 14m |
| v0.2.3 | specialty-directory | [r1](runs/v0.2.3/2026-08-10-specialty-directory-r1/README.md), [r2](runs/v0.2.3/2026-08-11-specialty-directory-r2/README.md), [r3](runs/v0.2.3/2026-08-11-specialty-directory-r3/README.md) | cleared · cleared · cleared | $18.33 · $14.56 · $11.05 | 50m · 47m · 35m |
| v0.2.3 | vets-specialty-filter | [r1](runs/v0.2.3/2026-08-11-vets-specialty-filter-r1/README.md) | cleared | $13.67 | 34m |
| v0.2.3 | visit-cancel | [r1](runs/v0.2.3/2026-08-11-visit-cancel-r1/README.md) | cleared | $1.11 | 2m |
| v0.2.3 | visit-edit | [r1](runs/v0.2.3/2026-08-11-visit-edit-r1/README.md) | cleared | $18.11 | 49m |
| v0.2.2 | owners-page-param | [r1](runs/v0.2.2/2026-08-08-owners-page-param-r1/README.md) | cleared | $5.88 | 14m |
| v0.2.2 | specialty-directory | [r1](runs/v0.2.2/2026-08-08-specialty-directory-r1/README.md), [r2](runs/v0.2.2/2026-08-08-specialty-directory-r2/README.md), [r3](runs/v0.2.2/2026-08-09-specialty-directory-r3/README.md) | cleared · cleared · cleared | $14.06 · $15.26 · $14.07 | 39m · 38m · 37m |
| v0.2.2 | vets-specialty-filter | [r1](runs/v0.2.2/2026-08-08-vets-specialty-filter-r1/README.md) | cleared | $15.56 | 39m |
| v0.2.2 | visit-cancel | [r1](runs/v0.2.2/2026-08-08-visit-cancel-r1/README.md), [r2](runs/v0.2.2/2026-08-10-visit-cancel-r2/README.md), [r3](runs/v0.2.2/2026-08-10-visit-cancel-r3/README.md) | cleared · cleared · cleared | $1.43 · $0.49 · $1.14 | 4m · 1m · 2m |
| v0.2.2 | visit-edit | [r1](runs/v0.2.2/2026-08-08-visit-edit-r1/README.md) | cleared | $16.90 | 43m |
| v0.2.1 | owners-page-param | [r1](runs/v0.2.1/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.2.1/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.2.1/2026-08-23-owners-page-param-r3/README.md) | cleared · cleared · cleared | $4.95 · $13.77 · $4.39 | 12m · 34m · 11m |
| v0.2.1 | specialty-directory | [r1](runs/v0.2.1/2026-08-23-specialty-directory-r1/README.md), [r2](runs/v0.2.1/2026-08-24-specialty-directory-r2/README.md), [r3](runs/v0.2.1/2026-08-24-specialty-directory-r3/README.md) | cleared · cleared · cleared | $10.91 · $17.67 · $11.46 | 29m · 43m · 32m |
| v0.2.1 | vets-specialty-filter | [r1](runs/v0.2.1/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.1/2026-08-25-vets-specialty-filter-r2/README.md) | cleared · cleared | $14.06 · $14.82 | 40m · 45m |
| v0.2.1 | visit-cancel | [r1](runs/v0.2.1/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.2.1/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.2.1/2026-08-23-visit-cancel-r3/README.md) | cleared · cleared · cleared | $0.98 · $1.03 · $0.88 | 3m · 3m · 3m |
| v0.2.0 | owners-page-param | [r1](runs/v0.2.0/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.2.0/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.2.0/2026-08-23-owners-page-param-r3/README.md) | cleared · cleared · cleared | $7.50 · $5.88 · $6.02 | 19m · 16m · 17m |
| v0.2.0 | specialty-directory | [r1](runs/v0.2.0/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.2.0/2026-08-24-specialty-directory-r2/README.md) | cleared · cleared | $14.23 · $14.45 | 42m · 34m |
| v0.2.0 | vets-specialty-filter | [r1](runs/v0.2.0/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.2.0/2026-08-25-vets-specialty-filter-r2/README.md) | cleared · cleared | $22.87 · $15.30 | 63m · 41m |
| v0.2.0 | visit-cancel | [r1](runs/v0.2.0/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.2.0/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.2.0/2026-08-23-visit-cancel-r3/README.md) | cleared · cleared · cleared | $0.92 · $0.84 · $0.77 | 3m · 2m · 2m |
| v0.2.0 | visit-edit | [r1](runs/v0.2.0/2026-08-23-visit-edit-r1/README.md) | cleared | $20.14 | 57m |
| v0.1.29 | owners-page-param | [r1](runs/v0.1.29/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.29/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.29/2026-08-23-owners-page-param-r3/README.md) | cleared · cleared · cleared | $6.40 · $6.93 · $17.74 | 15m · 18m · 54m |
| v0.1.29 | specialty-directory | [r1](runs/v0.1.29/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.29/2026-08-24-specialty-directory-r2/README.md), [r3](runs/v0.1.29/2026-08-24-specialty-directory-r3/README.md) | cleared · cleared · cleared | $16.02 · $12.34 · $14.27 | 44m · 36m · 37m |
| v0.1.29 | vets-specialty-filter | [r1](runs/v0.1.29/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.29/2026-08-25-vets-specialty-filter-r2/README.md) | cleared · cleared | $14.14 · $22.38 | 38m · 65m |
| v0.1.29 | visit-cancel | [r1](runs/v0.1.29/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.1.29/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.1.29/2026-08-23-visit-cancel-r3/README.md) | cleared · cleared · cleared | $1.04 · $0.88 · $0.85 | 3m · 2m · 2m |
| v0.1.29 | visit-edit | [r1](runs/v0.1.29/2026-08-23-visit-edit-r1/README.md) | cleared | $17.38 | 47m |
| v0.1.28 | owners-page-param | [r1](runs/v0.1.28/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.28/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.28/2026-08-23-owners-page-param-r3/README.md) | cleared · cleared · cleared | $5.26 · $3.93 · $3.89 | 14m · 14m · 13m |
| v0.1.28 | specialty-directory | [r1](runs/v0.1.28/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.28/2026-08-24-specialty-directory-r2/README.md), [r3](runs/v0.1.28/2026-08-24-specialty-directory-r3/README.md) | cleared · cleared · cleared | $10.76 · $15.92 · $16.12 | 32m · 48m · 50m |
| v0.1.28 | vets-specialty-filter | [r1](runs/v0.1.28/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.28/2026-08-24-vets-specialty-filter-r2/README.md) | cleared · cleared | $15.43 · $15.02 | 48m · 45m |
| v0.1.28 | visit-cancel | [r1](runs/v0.1.28/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.1.28/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.1.28/2026-08-23-visit-cancel-r3/README.md) | cleared · cleared · cleared | $0.73 · $0.87 · $0.82 | 2m · 3m · 3m |
| v0.1.28 | visit-edit | [r1](runs/v0.1.28/2026-08-23-visit-edit-r1/README.md) | cleared | $11.62 | 31m |
| v0.1.22 | owners-page-param | [r1](runs/v0.1.22/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.22/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.22/2026-08-23-owners-page-param-r3/README.md) | cleared · cleared · cleared | $4.27 · $4.73 · $6.74 | 13m · 14m · 22m |
| v0.1.22 | specialty-directory | [r1](runs/v0.1.22/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.22/2026-08-23-specialty-directory-r2/README.md), [r3](runs/v0.1.22/2026-08-24-specialty-directory-r3/README.md) | cleared · cleared · cleared | $13.33 · $9.92 · $9.83 | 47m · 30m · 31m |
| v0.1.22 | vets-specialty-filter | [r1](runs/v0.1.22/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.22/2026-08-24-vets-specialty-filter-r2/README.md) | cleared · cleared | $10.43 · $8.66 | 36m · 28m |
| v0.1.22 | visit-cancel | [r1](runs/v0.1.22/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.1.22/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.1.22/2026-08-23-visit-cancel-r3/README.md) | cleared · cleared · cleared | $0.73 · $0.78 · $0.73 | 2m · 3m · 2m |
| v0.1.22 | visit-edit | [r1](runs/v0.1.22/2026-08-23-visit-edit-r1/README.md) | cleared | $12.26 | 35m |
| v0.1.18 | owners-page-param | [r1](runs/v0.1.18/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.18/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.18/2026-08-23-owners-page-param-r3/README.md) | cleared · cleared · cleared | $3.85 · $3.81 · $4.65 | 13m · 11m · 16m |
| v0.1.18 | specialty-directory | [r1](runs/v0.1.18/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.18/2026-08-23-specialty-directory-r2/README.md), [r3](runs/v0.1.18/2026-08-24-specialty-directory-r3/README.md) | wasted (complete) · cleared · cleared | $7.55 · $7.89 · $8.77 | 24m · 26m · 23m |
| v0.1.18 | vets-specialty-filter | [r1](runs/v0.1.18/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.18/2026-08-24-vets-specialty-filter-r2/README.md) | cleared · cleared | $10.58 · $9.11 | 38m · 31m |
| v0.1.18 | visit-cancel | [r1](runs/v0.1.18/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.1.18/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.1.18/2026-08-23-visit-cancel-r3/README.md) | cleared · cleared · cleared | $1.12 · $0.97 · $1.01 | 4m · 4m · 4m |
| v0.1.18 | visit-edit | [r1](runs/v0.1.18/2026-08-23-visit-edit-r1/README.md) | cleared | $7.90 | 28m |
| v0.1.1 | owners-page-param | [r1](runs/v0.1.1/2026-08-22-owners-page-param-r1/README.md), [r2](runs/v0.1.1/2026-08-23-owners-page-param-r2/README.md), [r3](runs/v0.1.1/2026-08-23-owners-page-param-r3/README.md) | cleared · cleared · cleared | $3.67 · $3.97 · $5.90 | 10m · 11m · 17m |
| v0.1.1 | specialty-directory | [r1](runs/v0.1.1/2026-08-22-specialty-directory-r1/README.md), [r2](runs/v0.1.1/2026-08-23-specialty-directory-r2/README.md), [r3](runs/v0.1.1/2026-08-24-specialty-directory-r3/README.md) | cleared · cleared · cleared | $10.03 · $9.15 · $9.87 | 28m · 29m · 27m |
| v0.1.1 | vets-specialty-filter | [r1](runs/v0.1.1/2026-08-23-vets-specialty-filter-r1/README.md), [r2](runs/v0.1.1/2026-08-24-vets-specialty-filter-r2/README.md) | cleared · cleared | $10.04 · $11.06 | 27m · 32m |
| v0.1.1 | visit-cancel | [r1](runs/v0.1.1/2026-08-23-visit-cancel-r1/README.md), [r2](runs/v0.1.1/2026-08-23-visit-cancel-r2/README.md), [r3](runs/v0.1.1/2026-08-23-visit-cancel-r3/README.md) | cleared · cleared · cleared | $0.96 · $0.87 · $0.81 | 2m · 3m · 2m |
| v0.1.1 | visit-edit | [r1](runs/v0.1.1/2026-08-23-visit-edit-r1/README.md) | cleared | $9.03 | 22m |

</details>
