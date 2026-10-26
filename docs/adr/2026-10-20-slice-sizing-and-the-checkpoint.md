# The Implementer Keeps No Plan File and the Checkpoint Runs the Gate

**Status:** Accepted

## Context

`.scratch/implementation-plan.md` was the one markdown artifact the ledger decision left outside the ledger, justified as implementer self-tracking. It then became a handoff: the route spec handed it to retries and continuations, the one unvalidated input a fresh context window consumed. Its sections restated `design-block` paths, duplicated every `consultation-request`, and mirrored the build records the router reads; only the cycle list was unique. Its Domain Model and per-cycle "what code to write" lines decided Green before Red had failed, anchoring tests to an implementation. The bench's scope coverage series showed files outside the triage in 83 of 270 tagged reps with the plan in place.

The planned checkpoint had a flaw its first readings hid. The gate normally runs once, at the end, so at the checkpoint it had never run and the literal reading was "always stop". The recorded series holds 29 partial records across 219 implementing reps since v0.2.2, 26 of them handed off over passing targeted tests. With the plan retired, N became one cycle per owed test. The first arm rep set fired the checkpoint in three of four implementing reps, each costing a continuation at about $0.50 and three to five minutes.

The Pre-Check's `Pre-Check:` transcript line was then not written: 15 of 23 implementer dispatches in v0.4.9, 3 of 25 on the dev arm, 2 of 24 in v0.4.10. The behavior behind it held: the checkpoint gate ran where due in 8 of 9 multi-cycle dispatches, and every scope stop was a record. Nothing read the line.

## Options Considered

1. **Keep the plan file and template.** Rejected: the exemption's premise no longer held; the file was the last mutable, unvalidated handoff.
2. **Slim the file to a test list.** Rejected as the first choice; kept as the fallback had the acceptance arm regressed.
3. **An `implementation-plan` ledger record.** Rejected: an append-once record is the wrong shape for a test list revised every cycle.
4. **No plan file and no plan record.** Chosen: every function the file served has a home that already exists.
5. **Leave the checkpoint contract as written, or name one only when the estimate exceeds the budget.** Rejected: a partial over green tests buys only a re-dispatch. The estimate is the introspection the contract distrusts.
6. **Run the gate at the checkpoint and fix in place on red.** Rejected: a second red-gate semantics mid-slice would make the retry trail ambiguous.
7. **Run the gate at the checkpoint; continue on green, hand off on red.** Chosen.
8. **Re-anchor the `Pre-Check:` line, or carry the estimate on the build record.** Rejected: a guess about model behavior for a line with no reader. A retrospective number is not a pre-edit estimate.
9. **Retire the line, keep the check.** Chosen.

## Decision

**The implementer keeps no plan file; the planned checkpoint runs the quality gate and continues on green; the scope decision and the checkpoint are held in the dispatch, not written.**

| The plan's former function | Its home |
|---|---|
| The first concrete test | `prd-entry.test_names`, a required field |
| The target file set | `design-block.primary_paths`, `supporting_paths`, `patterns[*].ref`; exhaustive, widened only by consultation; each file opened once before its first edit, a scripted edit included |
| The slice-size gate | The cycle estimate held in the dispatch, and a count past 10 honest cycles aborts `wrong-shape-slice`; post hoc, the optional `cycles` integer on `build-pass` and `build-failure`, summed per slice as a lower bound |
| The Feedback Log | The ledger's `consultation-request` records |
| Progress and continuation context | The working tree, the active `prd-entry`, the latest `design-block` and `build-failure` |
| The Refactor outcome | One transcript line per cycle naming what was cleaned up or why nothing needed it |

- **One Pre-Check order.** The `dispatch-start` append is the first tool call. The reads follow: the inbound records, the role's durable memory, the implementer's target set. The check closes before the first edit, finding, or record draft, without a transcript line. A scope stop leaves the `dispatch-start` standing and closes with a `consultation-request`. The trace is the checkpoint gate run in the transcript, `cycles` on the build records, and the scope stop's record.
- **The checkpoint.** Every dispatch of two or more cycles names one at the end of cycle ⌈N/2⌉. On a re-dispatch N counts the cycles left, so a retry or fix round gets its own. A one-cycle slice's final gate is its checkpoint. The gate is the full `code-quality-gate`, the stack's formatter first. Green appends nothing; `build-pass` waits for the final gate. Red appends the partial-artifact `build-failure` with `failed_check` and `error_output`, then stops. An estimate over `toolCallBudget` no longer forces a handoff; a cap hit after a green checkpoint recovers as a truncation.
- **Unchanged neighbors.** The reviewers' Partial-Artifact Contract keeps its partial `review-feedback`. The router reads `partial: true` as a progress handoff with the retry counter ticking. A fix round applies every finding's edit, then runs the gate once; red is record-and-exit, as at the final gate.
- The self-review walk checks the call sites of a renamed symbol or changed signature, framework-bound names included. The template path sits in `harness/retired-paths.txt`; the doctor's fresh-eyes check keeps its slug for project-owned reviewers written against an older harness.

## Consequences

**Positive:**
- Every cross-dispatch input is a validated record or the working tree; the first interface decision is made from the caller's side.
- A red checkpoint hands off with gate output. A green one costs one gate run, about a minute on the Gradle SUT and seconds on Go, instead of a re-dispatch.
- The contract describes what runs; one obligation with no consumer left every creator and verifier dispatch.

**Negative:**
- The upfront enumeration was a forcing function against scope drift. The prd-entry's criteria, the self-review walk, and the reviewers cover the same ground, watched by the scope coverage and required-tests series.
- An arm sweep without the open-before-edit precondition (`dev-d80578fd`, 2026-10-24) rewrote `OwnerController.java` by scripted replacement unopened and renamed a bound request parameter. The fix and second review round cost about $1.09. The precondition answers it; the `page-param-rebound` defect probe watches for recurrence.
- One gate run per multi-cycle dispatch counts against `toolCallBudget`. A dispatch truncated after a green checkpoint leaves no partial record; the continuation reads the tree. The `cycles` sum has no router reader. The pre-edit estimate trace is gone; drift is read from where the gate run sits.

### Acceptance arm

Removing the plan was a demotion under the resilience-first doctrine, so it shipped behind a measured `--version dev` sweep interleaved with v0.4.9, three reps per task. The readings: the bar, the design-fit facet, the review-round count, and the scope coverage series.

**Result, 2026-10-25.** Arm `dev-f81f0b9b`, three reps per task interleaved with v0.4.9 on 2026-10-24 and 25, clears all three readings. The bar: 12 of 12 feature reps against v0.4.9's 11 of 12. Design-fit medians by task: 5, 4, 5, 5 against 5, 4, 4, 5. Reps with a file outside the triage: 5 of 12 against the pooled share's 4.3 in 12; three are the `PetTests.java` file every recorded visit-edit rep touches. Partial records 0 against 2; plan-file writes 0 against 8 of 12 reps. Every build record carries its cycle count. Every multi-cycle dispatch ran a gate before its final one. No dispatch edited an existing file it had not opened. Review rounds 24 against 23 per rep set. Required tests delivered 67 of 74 against 53 of 58. Cost per pass per rep set $18.73 against $18.88; wall equal at 63 minutes. Test-quality means 3.83 against 3.92, one sample apart.

## Implementation

`harness/core/.claude/skills/tdd-workflow/` (§ Scoping Pre-Check, § Partial-Artifact Contract, the self-review walk); the three stacks' `feature-implementer` bodies. `harness/core/schemas/scratch/build-pass.schema.json` and `build-failure.schema.json` (`cycles`, `partial`). `harness/core/.claude/skills/handoff-routing/route-spec.md` § Partial-record paths and § Truncation Recovery; the `review-workflow` and `handoff-append` skills. `harness/retired-paths.txt`; the `page-param-rebound` probe in `evals/`.

## References

- [The Handoff Ledger](2026-05-08-the-handoff-ledger.md) — the plan file was the exemption this decision closes.
- [Dispatch Lifecycle](2026-06-04-dispatch-lifecycle.md) — the two-axes rule and the truncation recovery a cap hit after a green checkpoint falls to.
- [Fresh-Eyes Review Changeset](2026-06-21-fresh-eyes-review-changeset.md) — reviewers never read the implementer's working memory; the doctor check kept here.
- [Resilience-First Improvement Doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — why a demotion carries a measured arm.
- [Test Conventions at Write Time](2026-09-03-test-conventions-at-write-time.md) — the companion test doctrine the arm measured alongside, and the same lesson that an output without a consumer is not produced.
- [The Eval Bench](2026-07-15-the-eval-bench.md) — the sweeps and series the arm was read on.
- [`evals/README.md` § Scope coverage](../../evals/README.md#scope-coverage) — the series that showed the plan did not hold scope.
