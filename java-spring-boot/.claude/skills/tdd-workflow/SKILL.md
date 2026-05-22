---
name: tdd-workflow
description: >-
  TDD cycle process and design-check decision tree for feature implementation.
  Load when implementing features using test-driven development.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

For principles and rationale behind this cycle — including the eight-clause bar a passing cycle must meet — see [`docs/tdd-principles.md`](../../../docs/tdd-principles.md) (§ Scope Discipline, § Code That Reads Cold, § Operationally Honest, § The Conjunctive Bar).

## Pipeline Position

This skill drives the **inner loop** of the four-nested-loop pipeline (inner / middle / outer / architectural). The design-check decision tree in step 2 is the consultation interface to the middle loop (system-design-expert) and the outer loop (product-requirements-expert). See [`docs/agentic-harness.md`](../../../docs/agentic-harness.md) for the loop model.

## Design is Discovered, Not Planned

The `design-block` record from the middle-loop triage is a **starting hypothesis**, not a contract. The inner loop is free — and expected — to discover better shape as red → green → refactor cycles run. Tests force interface decisions; refactoring at each green forces structural improvement. When the loop discovers something worth recording in durable memory, route it back through a consultation-request (see step 2 below) so the system-design-expert can crystallize it for the next slice to inherit.

What the inner loop must not do is silently absorb a discovery that contradicts durable memory. That's how drift takes hold. Surface it via consultation.

## TDD Cycle

1. **Plan** — break the slice into TDD cycles. Write the plan to `.scratch/implementation-plan.md` using the template in `.claude/templates/implementation-plan.md`. **Slice-size sanity check:** if the plan honestly needs more than 10 cycles, the slice was mis-sized at intake — log a Requirement gap and route to product-requirements-expert for splitting before starting Red. If the plan needs only 1–2 cycles and the slice is not a coherent standalone behavior, consider batching with a sibling slice instead.
2. **Design check** — before each cycle, verify the current design supports the behavior:
   - **Ready** — proceed to Red.
   - **Small code gap** — refactor first (keep tests green), then Red.
   - **Design gap** — append a `consultation-request` to `.scratch/handoff.jsonl` targeting `system-design-expert`. Pause work; resume the inner loop when the matching `consultation-response` arrives. Schema: [`schemas/scratch/consultation-request.schema.json`](../../../schemas/scratch/consultation-request.schema.json).
   - **Requirement gap** — log in Feedback Log; append a `consultation-request` targeting `product-requirements-expert`. Includes "slice too big realized mid-stream" — if the cycle count is climbing past the plan's estimate, the slice was mis-sized at intake; split rather than push through.
   - **Architecture misfit** — stop. Append a `consultation-request` to `system-design-expert` flagged as architectural; the triage on the next slice will likely return `conflicting` or `foundational` if the misfit is real.
3. **Red** — write a failing test.
4. **Green** — write minimum code to pass.
5. **Refactor** — clean up, keep tests green.
6. **Next cycle** — return to step 2.

## Self-Review Pass

After the last TDD cycle and before invoking reviewers, walk the eight clauses of the conjunctive bar against the diff. The canonical slug list and the clauses themselves live in [`docs/tdd-principles.md`](../../../docs/tdd-principles.md) (§§ Scope Discipline, Code That Reads Cold, Operationally Honest). For each clause, ask the question and fix any honest "no":

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

The pass is one walk through the diff — minutes, not a record. It is mandatory because it is where most quality comes from and is far cheaper than a reviewer-driven retry. No `.scratch/` file is required; if reviewers later flag something a clause walk would have caught, the gap is yours to close in the next round.

## Document Ownership

Never modify `docs/prd.md`, `docs/system-design.md`, `docs/ubiquitous-language.md`, or `docs/adr/` directly. Route through the owning agent by appending a `consultation-request` targeting them; the owning agent updates durable memory through its `consultation-response` if the discovery warrants crystallizing. Log all consultations in the Feedback Log of `.scratch/implementation-plan.md`.
