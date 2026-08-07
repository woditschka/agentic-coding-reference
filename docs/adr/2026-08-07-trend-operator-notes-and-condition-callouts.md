# The Trend Carries Operator Notes and Mechanical Condition Callouts

**Status:** Accepted

## Context

The audit of the 2026-08-07 `owners-page-param` reps (r4–r6) found the v0.2.0
cell blending two run conditions with no mark. r1–r3 ran Claude Code
2.1.220/.221 without prep-injected bash timeouts; r4–r6 ran 2.1.222 with them.
The blend softened the cross-version delta the review-cycle fix cites — +90%
read as +41% — and the boundary was discoverable only by opening six manifests.

Measurement showed the boundary is series-wide, not cell-specific: 14 of 30
committed cells span an instrument condition. The executing Claude Code
version drifts ambiently — 2.1.220 through 2.1.222 across the recorded
series. The bash-timeout settings-env line entered on 2026-08-05 and rides
every run from 2026-08-06 onward.

`TREND.md` is fully generated and never hand-edited; its callout policy covered
one span only — a record across several SUT bases. No channel existed for
operator commentary: the regression story lived in an ADR amendment and a
README paragraph, nowhere near the figures it explains.

## Options Considered

1. **Per-row condition callouts.** Rejected: they fire on 14 of 30 cells,
   mostly marking ambient patch drift. A callout on half the rows reads as
   background and buries the one row where it mattered.
2. **Operator notes alone.** Rejected: the failure mode is forgetting. The
   next unmarked boundary must not depend on operator diligence.
3. **Hand-edit TREND.md.** Rejected: it breaks the never-hand-edited
   invariant and the battery's derivation gate.
4. **Two channels** (chosen): a mechanical condition-span line plus an
   operator notes file as a first-class derivation input.

## Decision

**`summarize.py` derives two new surfaces: a page-level condition callout
computed from the manifests, and rendered operator notes authored in
`evals/results/notes.toml`.**

- **The condition callout is mechanical.** A record spanning several
  executing Claude Code versions or several settings-env prep conditions gets
  one page-level line — counts and version range — mirroring the multi-base
  callout. The trend still partitions by nothing; each manifest records its
  own condition.
- **Notes are input data, not edits.** `notes.toml` is TOML because the
  operator hand-writes prose: multiline strings, comments, stdlib `tomllib`.
  JSON stays the format machines record. Each note carries a date, a text,
  and an optional scope — `task` renders under that task's table, `task` plus
  `version` leads the bullet with the cell's version, neither renders in the
  page header.
- **Note prose meets the documentation standards.** The 30-word rule and the
  data-over-adjectives bar apply to note text; the audit's docs-and-skills
  lane reviews `notes.toml` like any root prose.
- **Validation fails loud.** A malformed entry, or a note naming a task or
  cell absent from the committed series, aborts the render. A note that
  outlives its rows is rot; rot never renders silently.
- **Figures never come from notes.** Notes are commentary beside the
  figures; the run folders stay the ground truth for every number.

## Consequences

**Positive:**

- An instrument boundary marks itself: the next Claude Code bump or prep
  change needs no operator to notice it.
- Discussion notes — why a cell moved, what a sweep probed — live beside the
  figures, versioned with the record. The owners-page-param regression story
  is the seed note.
- The battery's derived-views gate now covers notes: a note edit without a
  regenerate fails `--check`.

**Negative / accepted:**

- The page-level span line does not localize which reps sit on which side;
  the scoped notes and the manifests carry that.
- Note text passes the render scrub: pipes, backticks, and control bytes
  collapse. Markdown links survive; table syntax does not.
- Notes validate against the committed series only, so a dev-only cell
  cannot carry a note. Dev views are local and disposable; their commentary
  belongs in the working tree that produced them.
- Note content is not validated against derived figures: a hard-coded
  number in a note can go stale while `--check` stays green. Accepted:
  scope validation bounds the rot to a live cell, and the audit's docs lane
  reviews note figures against the table. A figure-level gate is a
  candidate follow-up.

## Implementation

- `evals/summarize.py` — `Note`, `load_notes`, `validate_notes`,
  `conditions_line`, the render threading (`render`, `table_section`,
  `_trend_lines`, `trend_views`, `main`).
- `evals/tests/test_summarize.py` — pins for parsing, validation, both
  render placements, the condition line, and deterministic ordering.
- `evals/results/notes.toml` — the seed note on the owners-page-param
  v0.2.0 cell.
- `evals/README.md` § Operator notes — the consumer-facing contract.
- The battery's existing `summarize.py --check` gate covers the new input
  with no wiring change.

## References

- [The eval bench measures cost per pass](2026-08-02-eval-bench-cost-per-pass.md) — the trend this decision annotates.
- [The review cycle survives mid-slice design records](2026-08-07-review-cycle-survives-mid-slice-design-records.md) — the regression whose evidence split motivated the notes channel; its amendment records the split the seed note renders.
