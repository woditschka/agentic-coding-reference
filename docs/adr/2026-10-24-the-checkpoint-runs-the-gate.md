# The Planned Checkpoint Runs the Quality Gate

**Status:** Accepted

## Context

The [cap-hit recovery decision](2026-06-10-cap-hit-recovery-is-continuation.md) gave every implementer dispatch a planned checkpoint, a milestone named before the first tool call. At it the dispatch hands off a partial-artifact `build-failure` unless the quality gate has already run green. The checkpoint is planned because the model cannot count its own tool calls, so a running count would be introspection the contract rejects.

The contract carried a flaw its first readings hid. The gate normally runs once, at the end of the slice. At the checkpoint it has therefore never run, and the literal reading is "always stop". Under the plan file the implementer grouped tests into few coarse cycles. The checkpoint sat at cycle 2 of 3 or 3 of 6 and fired in about one implementing rep in eight. The recorded series shows 29 partial records across 219 implementing reps since v0.2.2, 6 of 16 in v0.4.7. Twenty-six handed off over passing targeted tests; two fired inside the Red phase of a one-cycle slice, and one on a fix round before the gate ran.

The [plan-file retirement](2026-10-20-the-implementer-keeps-no-plan-file.md) made N honest, one cycle per owed test name. Its acceptance arm's first rep set (arm `dev-fa42bcbf-dirty`, 2026-10-23, local) then fired the checkpoint in three of four implementing reps. Each partial reported its targeted tests green and stopped at ⌈N/2⌉ with budget to spare. Each cost one continuation dispatch: a re-read of the briefs, about $0.50 and three to five minutes. One baseline implementer, with a plan, read the same text differently: it ran the gate at its checkpoint, saw green, and continued. That reading is the one this ADR adopts.

The Pre-Check's length rule also disagreed with the contract. The rule named a checkpoint only when the estimate exceeded `toolCallBudget`; the contract named one in every case. The implementers followed the contract.

## Options Considered

1. **Leave the contract as written.** Rejected. A partial over green tests buys nothing but a re-dispatch. With an honest N it fires on every slice of two or more tests.
2. **Name a checkpoint only when the estimate exceeds the budget.** Rejected. The estimate is the introspection the contract distrusts. A misestimate leaves a long dispatch with no checkpoint at all.
3. **Run the gate at the checkpoint; continue on green, hand off on red.** Chosen. The trigger stays mechanical. The action gains the one fact a gate run can establish: whether the tree builds.
4. **Run the gate at the checkpoint; fix in place on red.** Rejected. The harness already treats a red gate as a record-and-exit event at the final gate, with the retry trail as the diagnostic. A second red-gate semantics mid-slice would make that trail ambiguous.

## Decision

**We adopt option 3. At the planned checkpoint the implementer runs the quality gate. Green means proceed with no record. Red means append the partial-artifact `build-failure` with the gate output, then stop.**

- The checkpoint is named in every dispatch of two or more cycles, in the Pre-Check length sentence, at the end of cycle ⌈N/2⌉. On a re-dispatch N counts the cycles left, read from the coverage map and the last gate run. A retry or a fix round therefore gets a checkpoint of its own. The length rule now says so, and the contract is the single statement.
- A one-cycle slice names no checkpoint; its final gate is the checkpoint. The gate at a checkpoint is the full `code-quality-gate`; green appends no `build-pass`, which waits for the final gate. A red check whose procedure prescribes its own record appends that record, never a partial.
- An estimate over `toolCallBudget` no longer forces a handoff. The checkpoint's gate run catches a red tree halfway. A cap hit after a green one falls to `route-spec.md` § Truncation Recovery, which re-dispatches on the tree as the dispatch left it. A marker value for `failed_check` was rejected: the field is enum-bound to each project's own `gate.verbs`, so a new value would break every installed consumer.
- The stack's formatter runs before the checkpoint gate where the gate names one, so a format-only red does not spend a retry.
- `failed_check` carries the gate step that failed; `error_output` carries the gate output beside the progress description.
- The reviewers' Partial-Artifact Contract is unchanged: a review has no gate to run, and its checkpoint keeps the partial `review-feedback`.
- The router's reading of `partial: true` is unchanged: a progress handoff, retry counter ticking, continuation on the same slice.

## Consequences

**Positive:**
- A red checkpoint hands off with the gate output, which the former contract's partials over green tests never carried. A green one costs one gate run instead of a re-dispatch.
- The 2026-10-23 arm's three partials would have been three green gate runs, about a minute of wall each on the Gradle SUT and seconds on Go. The re-dispatches they caused cost about $1.50 and twelve minutes.
- The honest N from the plan-file retirement stays honest; nothing in the slice-size gate changes.

**Negative:**
- One gate run per dispatch of two or more cycles: wall, and the gate's four to six tool calls against `toolCallBudget`, which the length estimate counts.
- A dispatch truncated after a green checkpoint leaves no partial record, and an over-budget estimate no longer forces one. `route-spec.md` § Truncation Recovery re-dispatches under its three-truncation ceiling on the tree as the dispatch left it, which may hold edits past the checkpoint. The continuation reads the tree and the coverage map instead of a progress description. The `cycles` sum over a slice's records is a lower bound for the same reason: a dispatch truncated without a record, before or after the checkpoint, contributes nothing.

## Implementation

**Non-goal:** This is harness coordination doctrine, not a feature requirement. The contract lives in the `tdd-workflow` skill (§ Scoping Pre-Check, § Partial-Artifact Contract). The three stacks' `feature-implementer` agents and `agentic-harness.md` § Budget restate it. The partial record's meaning is restated in `route-spec.md` § Partial-record paths, the `build-failure` schema's `partial` description, the three `code-quality-gate` skills, and the glossary. The pinned Pre-Check text is re-pinned with the length rule's new sentence. The plan-file ADR's acceptance arm measures the combined change, this decision included. It reads the partial count per implementing rep beside its three readings, counted from the `partial: true` build-failure records in each run's `handoff.jsonl`. The expected reading: no partial over a green tree, and the implementer wall back in the plan arm's range.

## References

- [Cap-Hit Recovery Is Continuation](2026-06-10-cap-hit-recovery-is-continuation.md) — the contract this ADR amends
- [The Implementer Keeps No Plan File](2026-10-20-the-implementer-keeps-no-plan-file.md) — the change whose acceptance arm exposed the flaw
- [`route-spec.md` § Truncation Recovery](../../harness/core/.claude/skills/handoff-routing/route-spec.md) — the re-dispatch that covers a cap-hit after a green checkpoint
