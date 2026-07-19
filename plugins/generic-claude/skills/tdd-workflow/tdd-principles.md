# Test-Driven Development Principles for Agentic Projects

This document defines the TDD methodology for agentic projects — the development cycle that agents follow when building features. For how to write tests (structure, naming, assertions, data conventions), see [`testing-principles.md`](../../../docs/testing-principles.md).

TDD here is the XP-rooted practice that uses the red-green-refactor cycle as **design discovery**, not as test-after with extra steps. Good interfaces, good structure, and good tests fall out together when the cycle runs tight enough to test a design hypothesis. The TDD cycle is the **inner loop** of the four-nested-loop pipeline; the middle, outer, and architectural loops, and the design-check mechanism that connects them, are defined in [`agentic-harness.md`](../handoff-routing/agentic-harness.md).

## The TDD Cycle

Every feature is built through strict Red-Green-Refactor cycles. Agents never write production code without a failing test first.

### Cycle Steps

| Step | Action | Rule |
|------|--------|------|
| **Plan** | Break the feature into TDD cycles | Write plan to `.scratch/implementation-plan.md` |
| **Design check** | Verify the current design supports the behavior | Gate before every cycle (see below) |
| **Red** | Write a failing test | Test must fail for the right reason |
| **Green** | Write minimum code to pass | No more code than the test demands |
| **Refactor** | Clean up, keep tests green | No new behavior during refactor |
| **Next cycle** | Return to design check | Repeat until feature complete |

### Design Check Gate

Before each Red phase, evaluate the codebase:

| Assessment | Action |
|------------|--------|
| **Ready** | Proceed to Red |
| **Small code gap** | Refactor first (keep tests green), then Red |
| **Design gap** | Append a `consultation-request` to the handoff log targeting `system-design-expert`. Resume the inner loop when the matching `consultation-response` arrives |
| **Requirement gap** | Append a `consultation-request` targeting `product-requirements-expert`. Resume when the response arrives |
| **Architecture misfit** | Stop. Append a `consultation-request` to `system-design-expert` flagged as architectural; the triage will likely return `conflicting` or `foundational` |

The design check prevents agents from forcing code into a design that cannot support it. Without this gate, agents accumulate technical debt by working around structural problems instead of fixing them. Consultation roundtrips preserve the implementer's active state — control returns to the inner loop after the response is recorded.

## Why TDD for Agents

TDD gives agents four things they lack by default:

1. **Design discovery at the smallest timescale.** Each failing test forces an interface decision. The refactor phase forces structural improvement. Good design isn't planned ahead — it's discovered through the loop. Tests are the *evidence* of decisions made; not the goal of the practice.
2. **A concrete definition of "done."** The failing test is the specification for the step. When it passes, the step is complete.
3. **A fast feedback loop.** Agents detect mistakes in seconds, not after a full implementation.
4. **Incremental progress.** Each cycle produces a working, tested increment. If the agent session ends mid-feature, the completed cycles are still valid.

Without TDD, agents write multiple functions before any test exists, guess at requirements, and produce code that passes no tests on first run.

## Scope Discipline

The Green Phase rule "write the minimum code to make the failing test pass" combines with three additional scope rules. They apply to every cycle, not just Green.

| Rule | Slug | What it means |
|---|---|---|
| **Fit-for-purpose** | `fit-for-purpose` | Solves the stated problem, nothing more. No speculative generality. **No abstractions without two real call sites** — wait for the second use before introducing the abstraction. No defensive code for impossible cases — boundary validation belongs at boundaries; internal code trusts its contracts. |
| **Spec-grounded** | `spec-grounded` | Work starts from a clear outcome and stays within stated scope. If the spec is ambiguous, ask before coding (route through `product-requirements-expert` per the Design Check Gate). Drift outside scope is surfaced via the Feedback Log, not silently absorbed. |
| **Consistent with the codebase** | `consistent-with-codebase` | Matches existing patterns, naming, and conventions before introducing new ones. Read neighboring code before writing. Deviations are justified inline. |

The slugs feed the `bar_clause` field on `review-feedback` records — they are not decorative.

## Code That Reads Cold

The Red and Green phases produce tests and code; the Refactor phase has one job beyond keeping tests green: ensure the result reads cold. A competent engineer reading the code in two years, without context, should understand what it does and why.

| Rule | Slug | What it means |
|---|---|---|
| **Legible cold** | `legible-cold` | Names are accurate. Structure reflects intent. Non-obvious decisions carry a why-comment or an ADR. Comments explain WHY, not WHAT — well-named identifiers cover the WHAT. |
| **Tested as specification** | `tested-as-spec` | See [`testing-principles.md`](../../../docs/testing-principles.md) — test names read as a specification of the system; no tests of implementation detail; mocking follows the brief's § Mocking Policy. |
| **Correct under stated conditions** | `correct` | Behaves correctly for every case in the spec, including listed failure modes. Boundaries validate inputs; internal code trusts its contracts. See [`testing-principles.md`](../../../docs/testing-principles.md) § Edge Case and Boundary Testing for the test side. |

## Operationally Honest

Code that passes tests can still fail in production. Two properties guard against this.

| Rule | Slug | What it means |
|---|---|---|
| **Operationally honest** | `operationally-honest` | Errors carry actionable context for the person debugging at 3am (see [`architecture-principles.md`](../../../docs/architecture-principles.md) § Domain Core). Resource use (memory, I/O, external calls, cost) is reasonable for the workload. Rollback is possible — for breaking or stateful changes, a rollback note lives in the commit message body (a `Rollback:` footer) for simple cases, or in an ADR alongside the change for procedures that need standalone documentation. |
| **Human-maintainable without the agent** | `human-maintainable` | If the agents were turned off tomorrow, the code would still be comfortable to own. No artifacts that only make sense to re-prompt: no comments addressed to future agents, no scaffolding that depends on the harness being present, no code shape that requires regenerating rather than editing. |

## Secure by Design

Security is an emergent property of the design, not a layer added after the tests pass. The implementer reasons about how the change could be abused while shaping it, not only after.

**Four non-negotiable laws** govern every change. They are harness-owned and not a project's to weaken; a project specializes *how* it meets them — its trust boundaries and stack high-bar defaults in [`security-principles.md`](../../../docs/security-principles.md) — never *whether*.

1. **Security as emergent property** — security is present from the first interface decision, not retrofitted. A change that needs a security retrofit was designed wrong.
2. **Defense in depth** — no single control is the only protection. Validate at the entry point and again where the value is used; protect data in transit and at rest.
3. **Least privilege** — code, credentials, and processes hold only the access the task requires. Scope a permission to the operation, never to convenience.
4. **Fail secure** — when an operation errors, the system stays closed. A failure leaks no secret, bypasses no check, and disables no protection.

| Rule | Slug | What it means |
|---|---|---|
| **Secure by design** | `secure-by-design` | The four laws above hold. Input at a trust boundary is validated there; secrets never reach committed source, logs, errors, URLs, or process arguments; the change grants least privilege and fails secure. A failure leaves the system no more exposed than before. Internal code past the boundary trusts its contracts. The project's trust-boundary map and stack high-bar defaults live in [`security-principles.md`](../../../docs/security-principles.md). |

A slice with no new input, boundary, secret, or privilege satisfies this clause trivially — the question is asked every cycle, not only on security features.

## The Conjunctive Bar

A change is not done unless **all** nine clauses above (`fit-for-purpose`, `spec-grounded`, `legible-cold`, `correct`, `tested-as-spec`, `consistent-with-codebase`, `operationally-honest`, `human-maintainable`, `secure-by-design`) hold. A passing test suite is necessary but not sufficient.

The self-review pass before the quality gate (`tdd-workflow` § Self-Review Pass) walks the nine clauses against the diff. The reviewer agents tag findings with the violated clause via `bar_clause` on `review-feedback` findings, and the `change-grader`'s reviewer_hedging facet reads the flagged clauses as a hedge signal. The canonical slug list and the typical reviewer-to-clause mapping live in the `review-workflow` skill's `reference.md` § Quality-Bar Clause Mapping.

## Red Phase Rules

- Write exactly one test that fails.
- The test must fail for the right reason — a missing method, wrong return value, or unhandled case. Not a compilation error in unrelated code.
- The test must follow the conventions in [`testing-principles.md`](../../../docs/testing-principles.md): four-phase structure, three-tier data naming, factory methods, derived expectations.
- Run the test and confirm it fails before proceeding.

## Green Phase Rules

- Write the minimum code to make the failing test pass.
- Do not generalize. Do not optimize. Do not handle cases the test does not cover.
- Run all tests after each change. If any test breaks, fix it before continuing.
- "Minimum" means the simplest implementation that satisfies the test, including hard-coded return values when a single test case allows it. Subsequent cycles will drive the design toward the correct abstraction.

## Refactor Phase Rules

- Refactor only when all tests are green.
- No new behavior during refactor. If the refactoring introduces a new code path, it needs its own Red-Green cycle.
- Apply the testing vocabulary patterns from [`testing-principles.md`](../../../docs/testing-principles.md): extract factory methods, promote constants, compose higher-level factories.
- Run all tests after each refactoring step.
- Record the outcome on the plan's `Refactor` line: what was cleaned up, or why none was needed. The plan is self-tracking; no reviewer reads it.

## Quality Gate

Before invoking reviewers, all checks must pass:

| Check | Purpose |
|-------|---------|
| Build | Project compiles without errors |
| Test | All tests pass |
| Format | Code meets formatting standards (language-specific) |
| Lint | Static analysis rules pass (language-specific) |

No exceptions. Fix failures before requesting review.

## Bug Fixes Start with a Test

Every bug fix begins with a reproducing test — a test that fails because of the bug. Fix the bug. Confirm the test passes. This prevents regressions and documents the fix.

## Document Ownership During TDD

The feature-implementer agent writes code and tests. It does not modify documentation directly.

| Need | Action |
|------|--------|
| Requirement unclear | Append `consultation-request` targeting `product-requirements-expert` |
| Design needs updating | Append `consultation-request` targeting `system-design-expert` |
| Architecture misfit | Append `consultation-request` to `system-design-expert`; triage will likely return `conflicting` or `foundational` |

This separation ensures documentation changes go through the owning agent, not through ad-hoc edits during implementation. The consultation roundtrip is recorded in the handoff log; control returns to the implementer after the response is appended.

## How This Relates to Project-Level Docs

This document defines the methodology. The stack-supplied `feature-implementer` agent (`.claude/agents/feature-implementer.md`) applies it with the project's conventions and quality gate.
