# The Implementer Keeps No Plan File

**Status:** Accepted (acceptance arm re-run per [2026-10-24 the-checkpoint-runs-the-gate](2026-10-24-the-checkpoint-runs-the-gate.md))

> Amendment 2026-10-24: the acceptance arm's first rep set (2026-10-23, one rep per task) cleared all three readings. Three of four implementing reps handed off a planned-checkpoint partial over green tests, which [2026-10-24 the-checkpoint-runs-the-gate](2026-10-24-the-checkpoint-runs-the-gate.md) corrects. The arm re-runs with two more variables: the checkpoint rule, which moves the partial count and cost, and the test doctrine of [2026-10-24 one-sentence-per-table](2026-10-24-one-sentence-per-table.md), which moves test count and test-quality. A failed reading is attributed by its instrument before option 2 applies.

## Context

The [append-only JSONL handoffs decision](2026-05-08-append-only-jsonl-handoffs.md) moved every cross-agent artifact into the ledger and left `.scratch/implementation-plan.md` as markdown. Its stated reason: implementer self-tracking, no handoff gate, no rework loop. Three things changed since.

First, the file became a handoff. The route spec handed it to the re-dispatched implementer on a build-failure retry and on a truncation continuation. A file a fresh context window consumes is a handoff, whatever the role name. It was the one unvalidated input left in the pipeline.

Second, the template duplicated the ledger. Its file and integration sections restated `primary_paths`, `supporting_paths`, and `integration_points`; the TDD skill defined the plan's file set as that union, so the section could only drift from its source. Its Feedback Log was double entry beside every `consultation-request`. Its Status line duplicated `build-pass` and `build-failure`, which the router reads. Only the cycle list carried information that existed nowhere else.

Third, the file was mutable state by re-edit. The skill asked for one write before coding and one edit per cycle: tick the boxes, fill the Refactor line. No deterministic reader consumed the ticked state. The continuation dispatch received it, but a tick lags a truncation, so the route spec already told that dispatch to trust the working tree. The [fresh-eyes decision](2026-06-21-fresh-eyes-review-changeset.md) bars reviewers from it, the grader ignores it, and the grader ignores it. The retry-trail argument for append-only did not apply either: the file was gitignored and deleted at merge.

The template also crossed the line the TDD skill draws under "Design is Discovered, Not Planned". A Domain Model section designed entities before the first test existed. Each cycle's "Implementation: what code to write" line decided Green before Red had failed. Test-first discovers detail and interface design from the caller's side. An agent writes autoregressively, so the first artifact anchors the rest. An implementation plan written first anchors the tests to the implementation. That premise is a hypothesis; the acceptance arm's design-fit facet is its test.

The bench's [scope coverage series](../../evals/README.md#scope-coverage), computed over every recorded run, showed the plan did not hold scope. Files outside the triage occurred in 83 of 270 tagged reps with the plan in place. The two recurring cases were test files the triage never named. The plan's slice-size check, more than ten cycles means a re-split, was its one gate, and the file threw the count away.

## Options Considered

1. **Keep the file and template as they were.** Rejected: the exemption's premise no longer held, and the file was the last unvalidated, mutable handoff.
2. **Slim the markdown to a test list** and drop the per-cycle edits. Removes the duplication and the churn; leaves an unvalidated file invisible to replay and the bench. Kept as the fallback if the acceptance arm regresses.
3. **An `implementation-plan` ledger record**, appended once. Validated and replayable, but an append-once record is the wrong shape for a living test list, which Beck's practice revises every cycle. Re-appending a superseding record per discovered test costs one record append each, against one file edit.
4. **No plan file and no plan record** (chosen). Every function the file served has a home that already exists.

## Decision

**The implementer keeps no plan file.** The template is retired and its path enters the retired-paths manifest.

| The plan's function | Its home now |
|---|---|
| The first concrete test | `prd-entry.test_names`, a required field whose purpose is to give the first cycle its target |
| The target file set | `design-block.primary_paths`, `supporting_paths`, `patterns[*].ref`; still exhaustive, still widened only by consultation. The rule moves from the retired Plan step to the first step of the TDD cycle, "Start from the contract" |
| The slice-size gate | The design expert's `implementation_effort` rating at triage; the cycle estimate in the Scoping Pre-Check sentence before the first Red; post hoc, the `cycles` count each `build-pass` and `build-failure` carries, summed per slice from the ledger; a bench series over it is a follow-up |
| The Feedback Log | The ledger's `consultation-request` records, which were already the log |
| Progress | The working tree, which the retry and continuation paths already read |
| The retry and continuation prompt context | The active `prd-entry` beside the latest `design-block` and `build-failure` |
| The Refactor outcome line | One transcript line per cycle naming what was cleaned up or why nothing needed it; a prompt instruction, not a file edit |

`build-pass` gains an optional `cycles` integer. The doctor's fresh-eyes check keeps its slug: a project-owned reviewer written against an older harness may still name the retired file.

## Consequences

**Positive:**
- Every cross-dispatch input is a validated record or the working tree.
- The TDD skill stops asking for pre-decided implementation lines and progress edits nobody reads; an instruction an agent learns it can skip weakens the instructions around it.
- The first interface decision is made from the caller's side, before any implementation exists to anchor on.
- Each build record carries its dispatch's cycle count; a bench series over it is a follow-up.

**Negative:**
- The upfront enumeration was a forcing function against scope drift and missed criteria. The prd-entry's acceptance criteria and test names, the nine-clause self-review, and the reviewers cover the same ground; that is an argument, not yet evidence. The scope coverage and required-tests series are the instruments that turn it into one.
- A continuation dispatch loses the implementer's own notes. It keeps the contract and the working tree, which the route spec already told it to trust.
- The cost change is a rounding error: the implementer was 16% of spend in the v0.4.8 sweep, and this removes its plan write and one edit per cycle.

## Implementation

Surfaces edited: the TDD skill and its principles; the scratch contract; the handoff-routing state table and route spec; the review-workflow fresh-eyes paragraph. Also the doctor's check description and the audit-agents, prd-authoring, and marketplace setup skills. Also the three implementer bodies and agent READMEs, the review-planner body, the managed orchestrator chapter, the root handbook with its installed copy, the `build-pass` schema and its record class. The template file is deleted and listed in `harness/retired-paths.txt`.

**Acceptance arm.** Removing the plan is a demotion under the [resilience-first doctrine](2026-07-12-resilience-first-improvement-doctrine.md), so it ships behind a measured before-and-after. The arm gates the next `/release-version`: no tagged version carries this decision unmeasured. The arm is a `--version dev` sweep against the v0.4.9 baseline, read on the bar, the design-fit facet, the review-round count, and the scope coverage series. It fails on any of three readings. Any rep misses the bar. The design-fit median falls by 0.5 or more on any task. The reps with a file outside the triage exceed the pooled v0.4.7 and v0.4.8 share, 10 of 28, by more than two reps in twelve. Its result lands as an in-file amendment. On failure, option 2 replaces the file removal while the rest stands. Its shape: a template holding the owed test names only, written once; the route spec hands it to retries and continuations again. The retired-paths entry is removed so materialize stops pruning it; the doctor's slug is unchanged.

## References

- [`2026-05-08-append-only-jsonl-handoffs.md`](2026-05-08-append-only-jsonl-handoffs.md) — the exemption this decision closes
- [`2026-06-21-fresh-eyes-review-changeset.md`](2026-06-21-fresh-eyes-review-changeset.md) — reviewers never read the implementer's working memory; the doctor check this decision keeps
- [`2026-07-12-resilience-first-improvement-doctrine.md`](2026-07-12-resilience-first-improvement-doctrine.md) — why a demotion carries a measured arm
- `evals/README.md` § Scope coverage — the series the arm is read on
