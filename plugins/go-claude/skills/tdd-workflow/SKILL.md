---
name: tdd-workflow
description: >-
  TDD cycle process and design-check decision tree for feature implementation.
  Load when implementing features using test-driven development.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/system-design.md
  - docs/architecture-principles.md
  - docs/testing-principles.md
  - docs/security-principles.md
metadata:
  version: "1.0"
  author: team
---

For principles and rationale behind this cycle — including the nine-clause bar a passing cycle must meet — see [`tdd-principles.md`](tdd-principles.md) (§ Scope Discipline, § Code That Reads Cold, § Operationally Honest, § Secure by Design, § The Conjunctive Bar).

## Pipeline Position

This skill drives the **inner loop** of the four-nested-loop pipeline (inner / middle / outer / architectural). The design-check decision tree in step 2 is the consultation interface to the middle loop (system-design-expert) and the outer loop (product-requirements-expert). See [`agentic-harness.md`](../handoff-routing/agentic-harness.md) for the loop model.

## Design is Discovered, Not Planned

The `design-block` record from the middle-loop triage is a **starting hypothesis**, not a contract. The inner loop is free — and expected — to discover better shape as red → green → refactor cycles run. Tests force interface decisions; refactoring at each green forces structural improvement. When the loop discovers something worth recording in durable memory, route it back through a consultation-request (see step 2 below) so the system-design-expert can crystallize it for the next slice to inherit.

What the inner loop must not do is silently absorb a discovery that contradicts durable memory. That's how drift takes hold. Surface it via consultation.

## TDD Cycle

1. **Plan** — break the slice into TDD cycles. Write the plan to `.scratch/implementation-plan.md` using the template in `.claude/templates/implementation-plan.md`. The plan's target file set is the union of `design-block.primary_paths`, `supporting_paths`, and `patterns[*].location` — treat that union as exhaustive. Widening it is a Requirement or Design gap (step 2), not an exploration task: append a `consultation-request` rather than `grep`ping for additional files. **Slice-size sanity check:** if the plan honestly needs more than 10 cycles, the slice was mis-sized at intake — log a Requirement gap and route to product-requirements-expert for splitting before starting Red. If the plan needs only 1–2 cycles and the slice is not a coherent standalone behavior, consider batching with a sibling slice instead.
2. **Design check** — before each cycle, verify the current design supports the behavior:
   - **Ready** — proceed to Red.
   - **Small code gap** — refactor first (keep tests green), then Red.
   - **Design gap** — append a `consultation-request` to `.scratch/handoff.jsonl` targeting `system-design-expert`. Pause work; resume the inner loop when the matching `consultation-response` arrives. Schema: [`schemas/scratch/consultation-request.schema.json`](../../../schemas/scratch/consultation-request.schema.json).
   - **Requirement gap** — log in Feedback Log; append a `consultation-request` targeting `product-requirements-expert`. Includes "slice too big realized mid-stream" — if the cycle count is climbing past the plan's estimate, the slice was mis-sized at intake; split rather than push through.
   - **Architecture misfit** — stop. Append a `consultation-request` to `system-design-expert` flagged as architectural; the triage on the next slice will likely return `conflicting` or `foundational` if the misfit is real.

   Each branch routes by who owns the gap: a code gap is yours to refactor, a design gap the system-design-expert's, a requirement gap the product-requirements-expert's. An architecture misfit is a design gap large enough to re-triage the slice. The inner loop surfaces a decision that isn't its to make; it never absorbs one silently, because silent absorption is how drift takes hold.
3. **Red** — write a failing test.
4. **Green** — write minimum code to pass.
5. **Refactor** — clean up, keep tests green.
6. **Next cycle** — return to step 2.

### Fast inner-loop verification (optional)

When your toolchain provides an IDE semantic oracle, use it between cycles for a fast inspection pre-check instead of a full build every iteration, and to ground a Refactor's "matches the existing pattern" decision by resolving the neighbor rather than recalling it. The oracle reads and inspects; it does not compile — the toolchain gate does that. The inspection pre-check is optional, but the pattern decision is not: when an oracle is connected, a "reuses pattern X" / "matches the existing pattern" justification **must cite the symbol-resolution call** that resolves the neighbor — without an oracle, cite the grep and label it the weaker basis. Accelerator only otherwise: tests and the canonical quality gate (`code-quality-gate`) are unchanged. Where a stack provides oracle mechanics, they live in that stack's IDE-oracle skill.

## Self-Review Pass

After the last TDD cycle and before invoking reviewers, walk the nine clauses of the conjunctive bar against the diff. The canonical slug list and the clauses themselves live in [`tdd-principles.md`](tdd-principles.md) (§§ Scope Discipline, Code That Reads Cold, Operationally Honest, Secure by Design). For each clause, ask the question and fix any honest "no":

| Clause | Question |
|---|---|
| `fit-for-purpose` | Anything here that the spec did not ask for? |
| `spec-grounded` | Is every change traceable to a requirement, or am I drifting? |
| `legible-cold` | Would a stranger reading this in two years understand intent without me? |
| `correct` | Does the code handle every spec case and every listed failure mode? |
| `tested-as-spec` | Do test names read as the spec? Any tests of implementation detail? Any mocks inside the boundary? |
| `consistent-with-codebase` | Does the change match neighboring patterns? Any unjustified deviations? |
| `operationally-honest` | Do errors carry 3am-debuggable context? Is resource use reasonable? |
| `human-maintainable` | Would this still be comfortable to own with the agents turned off? |
| `secure-by-design` | Does any input, boundary, secret, or privilege appear in this diff? If so: does it validate at the boundary, keep secrets out of logs and errors, grant least privilege, and fail closed? |

The pass is one walk through the diff — minutes, not a record. It is mandatory because it is where most quality comes from and is far cheaper than a reviewer-driven retry. No `.scratch/` file is required; if reviewers later flag something a clause walk would have caught, the gap is yours to close in the next round.

## Scoping Pre-Check

Every creator and verifier dispatch — including this one — runs a three-step Scoping Pre-Check before the first tool call:

1. **Read the inbound and the durable memory.** Read the active `prd-entry`, `design-block`, and any `review-feedback` records for the current `req_id`. Read the durable memory the role normally reads (for the feature-implementer that is `docs/system-design.md`, `docs/architecture-principles.md`, and the files named in `design-block.primary_paths` + `supporting_paths` + `patterns[*].location`).
2. **Estimate by category.** Break the dispatch down by tool category — reads, edits, bash invocations, writes — and sum. Single-digit precision is sufficient; the goal is to catch 3× overruns, not to forecast accurately.
3. **Decide.** Run two independent checks:
   - **Scope (semantic, budget-free).** Does the work span more than one behavior or bounded context? Answer it from the inbound records, *not* from the step-2 estimate — a two-behavior slice is mis-sized even when it would fit the budget. If yes, **stop and append a `consultation-request`** instead of starting — target `product-requirements-expert` when the slice itself is too big, `system-design-expert` when the design surface is too broad. The request body names the behaviors driving the re-scope.
   - **Length (effort).** For a single-behavior slice, write the step-2 estimate as one or two sentences before the first tool call (the dispatch transcript carries it for offline analysis). If it fits `toolCallBudget`, proceed. If it exceeds `toolCallBudget`, still proceed — a single behavior has nothing to split — but name the planned checkpoint (§ Partial-Artifact Contract below) so the dispatch hands off a partial-artifact record and a continuation re-dispatch completes the same slice.

   `toolCallBudget` governs only the length check; the scope check never references it.

The pre-check is prompt-side discipline. There is no runtime enforcement and no separate record type — the estimate sentences in the dispatch transcript are the audit trail.

## Partial-Artifact Contract

The model cannot count its own tool calls precisely. The contract is therefore **planned-checkpoint**, not running-count: at Scoping Pre-Check time, name one explicit milestone in the plan where you will checkpoint regardless of whether the work feels close to done. The checkpoint is the trigger; the model's own tool-call count is not.

**Choosing the checkpoint.** For an N-cycle plan, set the checkpoint at the end of cycle ⌈N/2⌉. For a one-cycle slice, set it at "after the first failing test compiles" or "after the first edit touches the primary path." Write the checkpoint as one of the Pre-Check sentences before the first tool call so the transcript carries it.

**At the checkpoint, the decision is unconditional.** If the quality gate has already run green, proceed — no partial record needed. If the gate has not run, append the partial-artifact `build-failure` record below, then stop. Do not assess "am I close to done" — that assessment is exactly the introspection the contract rejects.

**Record shape.** Copy this, fill in the fields, append it via `python3 scripts/handoff.py append build-failure` (`handoff-append` skill):

```json
{"type":"build-failure","req_id":"<active req>","author":"feature-implementer","retry":<count>,"partial":true,"failed_check":"<gate step not yet reached, e.g. test or build>","attempted":"<one-sentence summary of what the dispatch was working on>","error_output":"<progress description: which tests pass, which files have been edited, which acceptance criteria remain>"}
```

- **`partial: true`** signals to the router that the record is a progress handoff, not a quality-gate failure. The retry counter still ticks (1 → 2 → 3 → re-triage), so a runaway partial-artifact stream eventually surfaces to the system-design-expert the same way three real failures do.
- **`failed_check`** carries the gate step that did not yet run. When no gate step has been reached, use `build`.
- **`error_output`** is read by the next dispatch to start from inspectable progress instead of from scratch.

The contract complement to a clean `build-pass` is this partial `build-failure`. Both are first-class outputs of a dispatch; neither is a failure mode.

## Wrong-Shape Slice Abort

The implementer may discover mid-loop that the slice cannot be implemented as triaged — not because the quality gate failed, but because the slice's shape is wrong, the design-block's design does not fit the code, or an external prerequisite is missing. Burning the full 3-retry cycle to surface this is wasteful. The implementer instead appends a `build-failure` record with the `abort_reason` field set, then exits. Build-Failure Recovery (`route`) short-circuits past the retry counter on these records.

**Trigger:** stop and write the abort record when, before completing TDD cycle 2, you have concluded that one of the three abort reasons applies. After cycle 2 the cost of one more retry is comparable to the abort overhead — finish the cycle and let the normal recovery path run.

**The three `abort_reason` values:**

- **`wrong-shape-slice`** — the slice scope is wrong (too big, two unrelated behaviors bundled, or the deliverable surface is mis-identified).
- **`design-mismatch`** — the design-block's `architectural_fit`, `primary_paths`, or `patterns` do not match the codebase as it actually is. Triage was based on stale or wrong information.
- **`prerequisite-missing`** — an external prerequisite (dependency upgrade, schema migration, third-party API change, operator action) blocks the slice.

Where each value routes is owned by `handoff-routing` § Build-Failure Recovery.

**Record shape.** Copy this, fill in the fields, append it via `python3 scripts/handoff.py append build-failure` (`handoff-append` skill):

```json
{"type":"build-failure","req_id":"<active req>","author":"feature-implementer","retry":<count>,"failed_check":"<gate step not reached, e.g. build>","attempted":"<one-sentence summary of what the dispatch discovered>","error_output":"<diagnosis: why the slice cannot proceed as-is, what specifically blocks it, what re-scoping/re-triaging/escalation should address>","abort_reason":"<wrong-shape-slice | design-mismatch | prerequisite-missing>"}
```

- The `retry` field SHOULD be set to the value it would have on a normal failure, so the retry trail remains coherent. The router ignores it when `abort_reason` is set.
- `error_output` carries the diagnosis (not an error stacktrace) — it is the next dispatch's primary input.
- `partial: true` and `abort_reason` are mutually exclusive — a wrong-shape abort is not a partial-artifact handoff. If both apply (the dispatch ran out of budget while discovering the slice is wrong-shape), choose `abort_reason` and surface the budget exhaustion in `error_output`.

## Document Ownership

Never modify `docs/prd.md`, `docs/system-design.md`, `docs/ubiquitous-language.md`, or `docs/adr/` directly. Route through the owning agent by appending a `consultation-request` targeting them; the owning agent updates durable memory through its `consultation-response` if the discovery warrants crystallizing. Log all consultations in the Feedback Log of `.scratch/implementation-plan.md`.
