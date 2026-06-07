# Change-Grade Report: Per-Facet Notes and a Clear/Concern Verdict

**Status:** Accepted

## Context

The change-grader ([`2026-06-05-change-grader.md`](2026-06-05-change-grader.md))
surfaced its result as a compact aligned block: each facet as a bare
`ok`/`concern`/`unknown`, plus a one-sentence rationale, with the verdict named
`auto`/`review`. Three problems showed up in use.

- **It flattened the grader's reasoning.** The grader forms a per-facet judgment
  while reading the diff, but the block kept only the one-word result. The
  explanation that makes the verdict actionable was discarded.
- **The verdict named an internal state, not an action.** `auto`/`review` does
  not tell the human what to do, and `review` collided with the four reviewers
  who already reviewed the change for correctness.
- **The call was buried.** The block led with the five facets and put the verdict
  last, so the reader scanned evidence before the answer.

## Options Considered

1. **Keep the compact aligned block.** Rejected: it discards the per-facet
   reasoning, names the verdict in internal terms, and orders evidence before the
   answer.
2. **Numeric or scored output.** Already rejected in the original ADR (judges
   cluster mid-scale; a hard gate wants a categorical call). Unchanged here.
3. **Surface the full deterministic feature row.** Deferred. The extractor diffs
   committed `base..HEAD`, but the grader runs before the commit, so the row is
   empty in the normal flow. The `Extracted:` line therefore renders only when
   the row is non-empty; a separate change makes the extractor read the
   uncommitted change, after which the line populates.

## Decision

The grader returns a Markdown report, and the record carries the reasoning behind
it.

**Verdict-first report.** The report leads with the answer: a title carrying a
plain-language change summary, then `## Verdict — Clear` (or
`## Verdict — Concern: <facets>`) with a prose rationale and the advisory line,
then a one-line `Extracted:` facts line, then one `## <Facet> — <Verdict>`
section per facet with a plain-prose note. A reader can stop after the verdict.

**One shared vocabulary.** Facet verdicts are `clear`/`concern`/`unknown`; the
overall verdict is `clear`/`concern`. This replaces `ok` and `auto`/`review`.
The words state what the grader found rather than command the human — fitting an
advisory node — and a `concern` verdict names the facet that fired, so the human
sees what and where before reading prose.

**The record holds the reasoning.** The `grader-verdict` record carries a
`summary`, a `{verdict, note}` pair per facet, and a prose `rationale`. The
produced order stays facet-notes → rationale → verdict (reason before
concluding); only the rendered order is verdict-first.

The worst-facet rule is unchanged in substance: any facet `concern` or `unknown`
makes the verdict `concern`; all five `clear` make it `clear`.

## Consequences

**Positive.**

- The per-facet reasoning is preserved in the record and surfaced in the report.
- The verdict states the action and names the flagged facet; the human reads what
  and where at a glance.
- Record and report share one vocabulary, so there is no internal-to-display
  mapping to keep straight.
- The answer leads; the evidence follows.

**Negative / accepted.**

- The report is more verbose than the one-line block on the trivial `clear` bulk.
  The scannable `## Facet — Verdict` headings keep it usable: read the headings,
  drop into prose only for a `concern`.
- The `Extracted:` line stays absent until the extractor-blindness fix lands.

## Implementation

**Non-goal:** This is a harness output decision, not a feature requirement.
Implementation lives in
`.claude/skills/change-grading/SKILL.md`
(the report format and the renamed vocabulary) and
`schemas/scratch/grader-verdict.schema.json`
(the `summary` field and the `{verdict, note}` facet shape). No code under
`internal/` or `cmd/` changes. The extractor-blindness fix and the populated
`Extracted:` line are a follow-up.

## References

- [`2026-06-05-change-grader.md`](2026-06-05-change-grader.md) — the original change-grader decision this refines
- `.claude/skills/change-grading/SKILL.md` — the grading protocol and report format
- `schemas/scratch/grader-verdict.schema.json` — the verdict record schema
