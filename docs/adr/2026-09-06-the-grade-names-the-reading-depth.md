# The Grade Names the Reading Depth

**Status:** Accepted

## Context

The change grader answers one question: how closely a human reads a
passing change before merging it. Its verdict enum was `clear` /
`concern`, and the five facets carried the same words plus `unknown`.
The pipeline board renders the bare enum on one line. An operator
reading `grader-verdict · REQ-VIS-003 — concern` learns that something
is wrong, not what to do.

The [report ADR](2026-06-05-change-grade-report.md) chose those words
on purpose: they state what the grader found rather than command the
human, fitting an advisory node. That rationale did not survive use.
The verdict's only consumer is the human at the merge click, and a
state word reads as an alarm without an action. Naming the human's
reading depth is the advisory content, not a command: nothing routes
on it and nothing merges on it.

The rename touches a recorded contract. Every committed eval run folder
carries the old words in its ledger and result file. The run folders are
the bench's ground truth and are never rewritten.

## Options Considered

1. **Keep the enum, label the display** — rejected. The board and the
   run pages would carry a vocabulary the schema does not, and the
   skill's prose would teach words the reader never sees.
2. **`routine` / `engaged`** — rejected. `routine` is the implementer's
   effort tier in the same ledger ([tiering ADR](2026-09-01-evidence-gated-dynamic-tiering.md)).
   One word would sit on two axes: predicted effort before the work and
   required attention after it. `engaged` names no action.
3. **`confirm` / `inspect`** — rejected. They name the human's action,
   not the depth of the read, and `inspect` does not say how closely.
4. **`skim` / `scrutinize`** (chosen): two imperatives naming the reading
   depth, with `unknown` unchanged as the third facet value.

## Decision

**The grade's vocabulary is `skim` and `scrutinize`, and every ledger
reader maps the recorded words at its parse boundary.** `skim` means a
glance confirms the change. `scrutinize` means read the flagged hunks
before deciding. Worst-facet aggregation holds unchanged: any facet
`scrutinize` or `unknown` makes the verdict `scrutinize`; all five
`skim` make it `skim`. The schema, the grading skill, the agent
description, the board colors, the glossary, and the pipeline figure
carry the new words.

Committed run folders stay as recorded. Two readers map `clear` to
`skim` and `concern` to `scrutinize` when they read a ledger. One is
the board renderer in the shipped runtime, which the run pages embed.
The other is the eval reader in `summarize.py`, which feeds the grader
concordance table and the run page header. Every derived view
therefore speaks one vocabulary. The mapping is permanent, since the
rows it serves stay on the trend page.

## Consequences

**Positive.** The board line answers the operator's question on its own.
The facet rows gain the same meaning: `semantic_surprise: scrutinize`
points at the hunk to read. A ledger written under the earlier words
renders in the current ones, in the terminal and on the run pages.

**Negative.** The recorded words outlive the schema that accepts them.
A reader opening a pre-rename `handoff.jsonl` or `result.json` directly
sees `clear` and `concern` beside the pages' `skim` and `scrutinize`.
The runtime never validates a committed eval ledger, so only the two
readers carry the mapping. The grade is now the one ledger enum whose
values are imperatives; the other enums name states.

## References

- [Change grader ADR](2026-06-05-change-grader.md) — the verdict this renames, and the advisory-only doctrine it keeps.
- [Change grade report ADR](2026-06-05-change-grade-report.md) — the state-not-command rationale this decision rebuts; its report headings now read `Skim` and `Scrutinize`.
- [Evidence-gated dynamic tiering ADR](2026-09-01-evidence-gated-dynamic-tiering.md) — the `routine` tier the rejected pair collided with.
- [Eval bench README](../../evals/README.md) — the rule that run folders are ground truth and are never rewritten.
