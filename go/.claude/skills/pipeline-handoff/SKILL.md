---
name: pipeline-handoff
description: >-
  Pipeline routing rules and handoff conditions between specialist agents.
  Load when coordinating feature delivery, checking pipeline state,
  or determining which agent to invoke next.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## Agent Selection

| User Request | Agent | Shortcut Allowed |
|---|---|---|
| New feature or enhancement | product-requirements-expert | No — full pipeline required |
| Discuss or explore feature idea | product-requirements-expert | Yes — single agent |
| Requirement clarification | product-requirements-expert | Yes — single agent |
| Architecture question | system-design-expert | Yes — single agent |
| Bug fix (known cause) | feature-implementer | Yes — skip PRD/design |
| Code review request | All four reviewers | Yes — parallel invocation |

**Skip agents for:** git operations, answering questions, running commands, reviewing already-completed changes.

## Handoff Conditions

| Current Agent | Trigger | Next Agent |
|---|---|---|
| product-requirements-expert | `.scratch/current-feature.md` contains `Status: Ready for Implementation` | system-design-expert |
| system-design-expert | `.scratch/design-notes.md` contains `Recommendation: APPROVED` or `Status: REVISED` | feature-implementer |
| feature-implementer | Quality gate passes (build, test, fmt, lint) | All reviewers (parallel) |
| feature-implementer | Quality gate fails, `Retry` < 3 | feature-implementer (retry with error context) |
| feature-implementer | Quality gate fails, `Retry` = 3 | system-design-expert (escalation) |
| Reviewers | All four contain `Status: APPROVED` | Feature complete |

## Blocking

If any agent outputs `NEEDS_CHANGES`, `BLOCKED`, or `[ESCALATE]`, stop the pipeline and resolve before continuing.

## Build-Failure Recovery

When the feature-implementer runs the quality gate and it fails (build error, test failure, lint failure), the implementer writes `.scratch/build-failure.md` with the error output, then exits.

### Failure file format

```markdown
---
Pipeline: [feature-name]
Stage: implementation (retry)
Author: feature-implementer
Timestamp: [ISO 8601]
Status: BUILD_FAILED
Retry: [1-3]
---

## Failed Check
[build | test | lint | fmt | vet | deps-check]

## Error Output
[full error output from the failing command]

## What Was Attempted
[brief description of the change that caused the failure]
```

### Coordinator retry logic

1. Read `.scratch/build-failure.md`. Extract the `Retry` count.
2. If `Retry` < 3, route back to feature-implementer with this prompt context:
   - `.scratch/build-failure.md` (the error output)
   - `.scratch/design-notes.md` (the original design)
   - `.scratch/implementation-plan.md` (what was planned)
   - Instruction: "Fix the build failure described in `.scratch/build-failure.md`. This is retry N of 3."
3. If `Retry` = 3, escalate to system-design-expert with this prompt context:
   - `.scratch/build-failure.md` (all three failure attempts)
   - `.scratch/design-notes.md`
   - Instruction: "The implementer failed 3 times. Review whether the design needs revision."
   - The design expert writes updated `.scratch/design-notes.md` with `Status: REVISED` or escalates to human with `[ESCALATE]`.
4. After a design revision (`Status: REVISED`), reset the retry counter. The coordinator routes back to the feature-implementer with `Retry: 0`.

### Retry rules

- The implementer increments `Retry` in `.scratch/build-failure.md` on each attempt.
- On success, the implementer deletes `.scratch/build-failure.md` and proceeds to reviewers.
- The coordinator never modifies `Retry` — it only reads it for routing decisions.
- Maximum 3 retries per design cycle. A design revision resets the counter.

## Mid-Implementation Feedback

The feature-implementer may invoke product-requirements-expert or system-design-expert during TDD cycles when tests uncover requirement gaps or design needs. These are not handoffs. The implementer continues with other cycles while waiting.

## Review Feedback Actions

See the `review-checklist` skill for feedback tag definitions and the review process.

## State Files

| File | Created By | Consumed By |
|---|---|---|
| `.scratch/current-feature.md` | product-requirements-expert | system-design-expert, feature-implementer |
| `.scratch/design-notes.md` | system-design-expert | feature-implementer |
| `.scratch/implementation-plan.md` | feature-implementer | feature-implementer (self-tracking) |
| `.scratch/reviews/*.md` | reviewer agents | feature-implementer |
| `.scratch/review-summary.md` | feature-implementer | Human (final check) |
| `.scratch/escalations.md` | feature-implementer | Human |
| `.scratch/build-failure.md` | feature-implementer | coordinator, feature-implementer (retry), system-design-expert (escalation) |
| `.scratch/eval-*.md` | coordinator (via feature-eval skill) | Human |

## Human Checkpoints

The human approves at these points:

1. **After PRD update** — Confirm requirement captures intent.
2. **After design notes** — Confirm architectural approach.
3. **After escalations** — Decide on `[ESCALATE]` items.
4. **After feature complete** — Final approval before merge.

## Coordinator Output Format

The pipeline coordinator responds with a structured recommendation:

```
## Pipeline State
[Current state based on .scratch/ files]

## Recommendation
**Action:** Invoke [agent-name]
**Prompt:** "[suggested prompt for the agent]"
**Shortcut:** Yes/No
**Reason:** [why this agent is next]
```

If blocked:
```
## Pipeline State
[Current state]

## Blocked
**Blocker:** [description]
**Resolution:** [what needs to happen]
```

## Coordinator Rules

1. Never skip pipeline stages for new features.
2. Shortcuts are allowed only per the agent selection table above.
3. If `.scratch/` contains stale state from a previous feature, recommend clearing it first.
4. Report all `[ESCALATE]` items found in state files.
5. If `.scratch/build-failure.md` exists, apply the retry logic in the "Build-Failure Recovery" section.
6. After all reviewers approve, load the `feature-eval` skill and write the evaluation scorecard.

## Pipeline Flow

```
User Request
    |
    v
Pipeline Coordinator (classifies request, checks .scratch/ state)
    |
    +--- New feature ------> product-requirements-expert
    |                              |
    |                              v (Status: Ready for Implementation)
    |                        system-design-expert
    |                              |
    |                              v (Recommendation: APPROVED or Status: REVISED)
    |                        feature-implementer
    |                              |
    |                     +--------+--------+
    |                     |                 |
    |                     v (passes)        v (fails, Retry < 3)
    |               All reviewers      feature-implementer
    |                  (parallel)       (retry with error context)
    |                     |                 |
    |                     |                 v (fails, Retry = 3)
    |                     |           system-design-expert
    |                     |           (revise or [ESCALATE])
    |                     |                 |
    |                     |                 v (Status: REVISED, retry reset)
    |                     |           feature-implementer
    |                     |
    |                     v (all four: Status: APPROVED)
    |               Feature eval → .scratch/eval-<name>.md
    |                     |
    |                     v
    |               Feature complete
    |
    +--- Bug fix (known) --> feature-implementer (shortcut)
    +--- Architecture Q ---> system-design-expert (single agent)
    +--- Code review ------> All reviewers (parallel)
```
