# The Implementer Keeps No Plan File

**Status:** Accepted (the `Pre-Check:` line in the replacement table retired by [2026-10-25 the-pre-check-line-is-retired](2026-10-25-the-pre-check-line-is-retired.md))

> The cycle estimate is held, not written; the post-hoc `cycles` count and the wrong-shape abort stand as the gate's observables.

## Context

The [append-only JSONL handoffs decision](2026-05-08-append-only-jsonl-handoffs.md) moved every cross-agent artifact into the ledger and left `.scratch/implementation-plan.md` as markdown. Its stated reason: implementer self-tracking, no handoff gate, no rework loop. Three things changed since.

First, the file became a handoff. The route spec handed it to the re-dispatched implementer on a build-failure retry and on a truncation continuation. A file a fresh context window consumes is a handoff, whatever the role name. It was the one unvalidated input left in the pipeline.

Second, the template duplicated the ledger. Its file and integration sections restated `primary_paths`, `supporting_paths`, and `integration_points`; the TDD skill defined the plan's file set as that union, so the section could only drift from its source. Its Feedback Log was double entry beside every `consultation-request`. Its Status line duplicated `build-pass` and `build-failure`, which the router reads. Only the cycle list carried information that existed nowhere else.

Third, the file was mutable state by re-edit. The skill asked for one write before coding and one edit per cycle: tick the boxes, fill the Refactor line. No deterministic reader consumed the ticked state. The continuation dispatch received it, but a tick lags a truncation, so the route spec already told that dispatch to trust the working tree. The [fresh-eyes decision](2026-06-21-fresh-eyes-review-changeset.md) bars reviewers from it, the grader ignores it. The retry-trail argument for append-only did not apply either: the file was gitignored and deleted at merge.

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
| The target file set | `design-block.primary_paths`, `supporting_paths`, `patterns[*].ref`; still exhaustive, still widened only by consultation. The rule moves from the retired Plan step to the first step of the TDD cycle, "Start from the contract". Each file in the set is opened once in the dispatch before its first edit, a scripted shell edit included |
| The slice-size gate | The cycle estimate in the `Pre-Check:` line, written after the reads and before the first edit. Post hoc, the `cycles` count each `build-pass` and `build-failure` carries, summed per slice from the ledger. The sum is a lower bound, since a dispatch truncated without a record adds nothing |
| The Feedback Log | The ledger's `consultation-request` records, which were already the log |
| Progress | The working tree, which the retry and continuation paths already read |
| The retry and continuation prompt context | The active `prd-entry` beside the latest `design-block` and `build-failure` |
| The Refactor outcome line | One transcript line per cycle naming what was cleaned up or why nothing needed it; a prompt instruction, not a file edit |

The read that precedes an edit is owed, not exploration. The implementer's bias toward fewer reads runs against reading beyond the file map, never against reading the map itself: fewer reads, never zero. The self-review walk checks the call sites of a renamed symbol or changed signature, a framework-bound name such as a request parameter included.

Both build records gain an optional `cycles` integer. The doctor's fresh-eyes check keeps its slug: a project-owned reviewer written against an older harness may still name the retired file.

## Consequences

**Positive:**
- Every cross-dispatch input is a validated record or the working tree.
- The TDD skill stops asking for pre-decided implementation lines and progress edits nobody reads; an instruction an agent learns it can skip weakens the instructions around it.
- The first interface decision is made from the caller's side, before any implementation exists to anchor on.
- Each build record carries its dispatch's cycle count.

**Negative:**
- The upfront enumeration was a forcing function against scope drift and missed criteria. The prd-entry's acceptance criteria and test names, the nine-clause self-review, and the reviewers cover the same ground; that is an argument, not yet evidence. The scope coverage and required-tests series are the instruments that turn it into one.
- Without the Plan step, an edit can precede any read of its file. An arm sweep on the change without the precondition (arm `dev-d80578fd`, 2026-10-24, stopped after five cells) did so on the owners-page-param task. The implementer rewrote `OwnerController.java` by scripted string replacement without opening it and renamed the bound request parameter. Three reviewers flagged the broken `?page=` contract as critical; the fix round and a second review round cost about $1.09. Every earlier recorded initial pass on that task opened the controller first. The open-before-edit precondition and the rename check in the Decision answer it, and the task's `page-param-rebound` defect probe watches for a recurrence.
- A continuation dispatch loses the implementer's own notes. It keeps the contract and the working tree, which the route spec already told it to trust.
- The slice-size signal has no reader: the sum is recorded, and no router or report acts on it.
- The cost change is a rounding error: the implementer was 16% of spend in the v0.4.8 sweep, and this removes its plan write and one edit per cycle. The precondition adds at most one read per target-set file, which the read-each-once budget already allowed.

## Implementation

Surfaces edited: the TDD skill and its principles; the scratch contract; the handoff-routing state table and route spec; the review-workflow fresh-eyes paragraph. Also the doctor's check description and the audit-agents, prd-authoring, and marketplace setup skills. Also the three implementer bodies with their Trust the Handoff bounds, their agent READMEs, and the TDD skill's self-review walk. Also the review-planner body, the managed orchestrator chapter, the root handbook with its installed copy, the two build-record schemas and their record classes. The template file is deleted and listed in `harness/retired-paths.txt`. The owners-page-param eval task gains the `page-param-rebound` defect probe.

**Acceptance arm.** Removing the plan is a demotion under the [resilience-first doctrine](2026-07-12-resilience-first-improvement-doctrine.md), so it ships behind a measured before-and-after. The arm gates the next `/release-version`: no tagged version carries this decision unmeasured. It measures the change as it ships, the open-before-edit precondition included, with two companion decisions of the same feature. They are [2026-10-24 the-checkpoint-runs-the-gate](2026-10-24-the-checkpoint-runs-the-gate.md) with its Pre-Check order and the test doctrine of [2026-10-24 one-sentence-per-table](2026-10-24-one-sentence-per-table.md). The arm is a `--version dev` sweep interleaved with v0.4.9, three reps per task, with the judge. It is read on the bar, the design-fit facet, the review-round count, and the scope coverage series. The review-round count and the partial count are hand counts over the committed ledgers; the other readings are bench figures. It fails on any of three readings. Any rep misses the bar. The design-fit median falls by 0.5 or more on any task. The reps with a file outside the triage exceed the pooled v0.4.7 and v0.4.8 share, 10 of 28, by more than two reps in twelve. Beside the readings, the partial count shows the checkpoint rule's effect and the test count and test quality the table doctrine's. A first rep set, one rep per task on 2026-10-23 and 24 against v0.4.8, cleared the first two readings. The third needs the twelve-rep depth. That set's partials over green tests and its test shapes informed the two companion decisions. The sweep's result is recorded below. A failed reading is attributed by its instrument before option 2 applies. On failure, option 2 replaces the file removal while the rest stands. Its shape: a template holding the owed test names only, written once; the route spec hands it to retries and continuations again. The retired-paths entry is removed so materialize stops pruning it; the doctor's slug is unchanged.

**Result, 2026-10-25.** Arm `dev-f81f0b9b`, three reps per task interleaved with v0.4.9 on 2026-10-24 and 25, clears all three readings. The bar: 12 of 12 feature reps against v0.4.9's 11 of 12. Design-fit medians by task: 5, 4, 5, 5 against 5, 4, 4, 5. Reps with a file outside the triage: 5 of 12 against the pooled share's 4.3 in 12; three are the `PetTests.java` file every recorded visit-edit rep touches. Beside the readings, read from the committed ledgers and the local transcripts: partial records 0 against 2; plan-file writes 0 against 8 of 12 reps; every build record carries its cycle count; every multi-cycle dispatch ran a gate before its final one; no dispatch edited an existing file it had not opened. Review rounds 24 against 23 per rep set. Required tests delivered 67 of 74 against 53 of 58. Cost per pass per rep set $18.73 against $18.88; wall equal at 63 minutes. Test-quality means 3.83 against 3.92, one sample apart. One observable fell short: a transcript line beginning `Pre-Check:` appears in 3 of 25 dev dispatches, against the old pre-read form in 15 of 23. The gate it anchors ran regardless; re-anchoring the line is follow-up work, not a reading.

## References

- [`2026-05-08-append-only-jsonl-handoffs.md`](2026-05-08-append-only-jsonl-handoffs.md) — the exemption this decision closes
- [`2026-06-21-fresh-eyes-review-changeset.md`](2026-06-21-fresh-eyes-review-changeset.md) — reviewers never read the implementer's working memory; the doctor check this decision keeps
- [`2026-07-12-resilience-first-improvement-doctrine.md`](2026-07-12-resilience-first-improvement-doctrine.md) — why a demotion carries a measured arm
- [`2026-10-24-the-checkpoint-runs-the-gate.md`](2026-10-24-the-checkpoint-runs-the-gate.md) — a companion decision the acceptance arm measures; it answers the planned-checkpoint partials the first rep set showed
- [`2026-10-24-one-sentence-per-table.md`](2026-10-24-one-sentence-per-table.md) — a companion decision the acceptance arm measures; the first rep set's test shapes informed it
- `evals/README.md` § Scope coverage — the series the arm is read on
