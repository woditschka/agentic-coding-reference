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

## TDD Cycle

1. **Plan** — break the feature into TDD cycles. Write plan to `.scratch/implementation-plan.md` using the template in `.claude/templates/implementation-plan.md`.
2. **Design check** — before each cycle, verify the current design supports the behavior:
   - **Ready** — proceed to Red.
   - **Small code gap** — refactor first (keep tests green), then Red.
   - **Design gap** — invoke system-design-expert. Wait for approval.
   - **Requirement gap** — log in Feedback Log, invoke product-requirements-expert.
   - **Architecture misfit** — stop, invoke system-design-expert with `[ESCALATE]`.
3. **Red** — write a failing test.
4. **Green** — write minimum code to pass.
5. **Refactor** — clean up, keep tests green.
6. **Next cycle** — return to step 2.

## Document Ownership

Never modify `docs/prd.md` or `docs/system-design.md` directly. Invoke the owning agent instead. Log all agent requests in the Feedback Log of `.scratch/implementation-plan.md`.
