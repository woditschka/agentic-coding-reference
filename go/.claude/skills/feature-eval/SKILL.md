---
name: feature-eval
description: >-
  Score a completed feature against quality criteria and write an evaluation
  scorecard. Load after all four reviewers approve to produce
  .scratch/eval-<feature-name>.md.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## When to Run

Run after all four reviewers have approved (all `.scratch/reviews/*.md` contain `Status: APPROVED`). The coordinator loads this skill and writes the scorecard before declaring the feature complete.

## Inputs

| File | Purpose |
|---|---|
| `.scratch/current-feature.md` | Feature name (from `Pipeline:` header) |
| `.scratch/reviews/security.md` | Security reviewer verdict |
| `.scratch/reviews/code-quality.md` | Code quality reviewer verdict |
| `.scratch/reviews/test-coverage.md` | Test reviewer verdict |
| `.scratch/reviews/doc-review.md` | Doc reviewer verdict |
| `.scratch/build-failure.md` | Retry count (if file existed during pipeline; may be deleted on success) |
| `.scratch/implementation-plan.md` | Retry history (check `Retry` references) |

## Scoring Criteria

| Criterion | Score | How to Determine |
|---|---|---|
| Tests pass | Yes / No | Quality gate passed (feature reached review stage) |
| Security approved | Yes / No | `.scratch/reviews/security.md` contains `Status: APPROVED` |
| Code quality approved | Yes / No | `.scratch/reviews/code-quality.md` contains `Status: APPROVED` |
| Test coverage approved | Yes / No | `.scratch/reviews/test-coverage.md` contains `Status: APPROVED` |
| Doc review approved | Yes / No | `.scratch/reviews/doc-review.md` contains `Status: APPROVED` |
| All 4 reviewers approved | Yes / No | All four above are Yes |
| Build retry cycles | 0–3+ | Count from `Retry` field in `.scratch/build-failure.md` history, or 0 if no failures occurred |
| Design revisions | 0–N | Count `Status: REVISED` entries in `.scratch/design-notes.md` |

## Output Format

Write to `.scratch/eval-<feature-name>.md` where `<feature-name>` is the `Pipeline:` value from `.scratch/current-feature.md`, lowercased with spaces replaced by hyphens.

```markdown
---
Pipeline: [feature-name]
Stage: evaluation
Author: pipeline-coordinator
Timestamp: [ISO 8601]
---

## Feature Evaluation: [feature-name]

| Criterion | Result |
|---|---|
| Tests pass | Yes |
| Security approved | Yes / No |
| Code quality approved | Yes / No |
| Test coverage approved | Yes / No |
| Doc review approved | Yes / No |
| All 4 reviewers approved | Yes / No |
| Build retry cycles | [0-3+] |
| Design revisions | [0-N] |

## Summary

- **Overall:** PASS / FAIL
- **Retry cost:** [0 = clean, 1-2 = minor issues, 3 = design revision needed]
- **Notes:** [any observations about the pipeline run]
```

## Rules

- PASS requires: tests pass AND all 4 reviewers approved.
- A feature that required design revision is still a PASS if it ultimately succeeds, but note the revision in the summary.
- Do not modify any other `.scratch/` files. This skill is read-only except for the eval file.
