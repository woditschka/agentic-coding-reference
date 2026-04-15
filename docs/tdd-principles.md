# Test-Driven Development Principles for Agentic Projects

This document defines the TDD methodology for agentic projects — the development cycle that agents follow when building features. For how to write tests (structure, naming, assertions, data conventions), see [`testing-principles.md`](testing-principles.md).

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
| **Design gap** | Invoke system-design-expert agent. Wait for approval |
| **Requirement gap** | Log feedback, invoke product-requirements-expert agent |
| **Architecture misfit** | Stop. Escalate to system-design-expert with `[ESCALATE]` |

The design check prevents agents from forcing code into a design that cannot support it. Without this gate, agents accumulate technical debt by working around structural problems instead of fixing them.

## Why TDD for Agents

TDD gives agents three things they lack by default:

1. **A concrete definition of "done."** The failing test is the specification. When it passes, the step is complete.
2. **A fast feedback loop.** Agents detect mistakes in seconds, not after a full implementation.
3. **Incremental progress.** Each cycle produces a working, tested increment. If the agent session ends mid-feature, the completed cycles are still valid.

Without TDD, agents write multiple functions before any test exists, guess at requirements, and produce code that passes no tests on first run.

## Red Phase Rules

- Write exactly one test that fails.
- The test must fail for the right reason — a missing method, wrong return value, or unhandled case. Not a compilation error in unrelated code.
- The test must follow the conventions in [`testing-principles.md`](testing-principles.md): four-phase structure, three-tier data naming, factory methods, derived expectations.
- Run the test and confirm it fails before proceeding.

## Green Phase Rules

- Write the minimum code to make the failing test pass.
- Do not generalize. Do not optimize. Do not handle cases the test does not cover.
- Run all tests after each change. If any test breaks, fix it before continuing.
- "Minimum" means the simplest implementation that satisfies the test, including hard-coded return values when a single test case allows it. Subsequent cycles will drive the design toward the correct abstraction.

## Refactor Phase Rules

- Refactor only when all tests are green.
- No new behavior during refactor. If the refactoring introduces a new code path, it needs its own Red-Green cycle.
- Apply the testing vocabulary patterns from [`testing-principles.md`](testing-principles.md): extract factory methods, promote constants, compose higher-level factories.
- Run all tests after each refactoring step.

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
| Requirement unclear | Log feedback, invoke product-requirements-expert |
| Design needs updating | Invoke system-design-expert |
| Architecture misfit | Escalate to system-design-expert with `[ESCALATE]` |

This separation ensures documentation changes go through the owning agent, not through ad-hoc edits during implementation.

## How This Relates to Project-Level Docs

This document defines the methodology. Each implementation applies it:

- **Go:** [`go/.claude/agents/feature-implementer.md`](../go/.claude/agents/feature-implementer.md) — TDD process with Go idioms, `make ci` quality gate
- **Java Spring Boot:** [`java-spring-boot/.claude/agents/feature-implementer.md`](../java-spring-boot/.claude/agents/feature-implementer.md) — TDD process with Spring Boot conventions, `./gradlew build` quality gate
