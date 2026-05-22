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

This skill drives the **inner loop** of the three-nested-loop pipeline. The design-check decision tree in step 2 is the callback edge to the middle loop (system-design-expert) and the outer loop (product-requirements-expert). See [`docs/agentic-harness.md`](../../../docs/agentic-harness.md) for the loop model.

## TDD Cycle

1. **Plan** — break the slice into TDD cycles. Write the plan to `.scratch/implementation-plan.md` using the template in `.claude/templates/implementation-plan.md`. **Slice-size sanity check:** if the plan honestly needs more than 10 cycles, the slice was mis-sized at intake — log a Requirement gap and route to product-requirements-expert for splitting before starting Red. If the plan needs only 1–2 cycles and the slice is not a coherent standalone behavior, consider batching with a sibling slice instead.
2. **Design check** — before each cycle, verify the current design supports the behavior:
   - **Ready** — proceed to Red.
   - **Small code gap** — refactor first (keep tests green), then Red.
   - **Design gap** — invoke system-design-expert. Wait for approval.
   - **Requirement gap** — log in Feedback Log, invoke product-requirements-expert. Includes "slice too big realized mid-stream" — if the cycle count is climbing past the plan's estimate, the slice was mis-sized at intake; split rather than push through.
   - **Architecture misfit** — stop, invoke system-design-expert with `[ESCALATE]`.
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

Never modify `docs/prd.md` or `docs/system-design.md` directly. Invoke the owning agent instead. Log all agent requests in the Feedback Log of `.scratch/implementation-plan.md`.
