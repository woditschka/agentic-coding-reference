---
name: feature-eval
description: >-
  Score a completed feature against quality criteria and write an evaluation
  scorecard. Load after all four reviewers approve to produce
  .scratch/eval-<feature-name>.md.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
metadata:
  version: "1.0"
  author: team
---

## When to Run

Run after each of the four reviewers has appended a `review-feedback` record with `verdict: "approved"` to `.scratch/handoff.jsonl` for the active `req_id` (latest record per reviewer). The coordinator loads this skill and writes the scorecard before declaring the feature complete.

## Inputs

`.scratch/handoff.jsonl` — the append-only handoff log; all data the scorecard needs is in the records below, filtered by the active `req_id`.

| Record | Purpose |
|---|---|
| Latest `prd-entry` | Feature name (from `req_id`); requirement title |
| Latest `design-block` per `req_id` | Triage verdict (`covered` / `minor` / `new` / `foundational` / `conflicting` / `refactor-first`); revision history (count records that carry `supersedes_record_at`) |
| All `build-failure` records for `req_id` | Retry cycles (count records since the latest `design-block`) |
| Latest `build-pass` for `req_id` | Quality-gate-passed marker |
| Latest `review-feedback` per reviewer for `req_id` | Reviewer verdicts |

## Scoring Criteria

| Criterion | Score | How to Determine |
|---|---|---|
| Tests pass | Yes / No | A `build-pass` record exists for `req_id` after all `build-failure` records |
| Security approved | Yes / No | Latest `review-feedback` with `author: "security-reviewer"` has `verdict: "approved"` |
| Code quality approved | Yes / No | Latest `review-feedback` with `author: "code-quality-reviewer"` has `verdict: "approved"` |
| Test coverage approved | Yes / No | Latest `review-feedback` with `author: "test-reviewer"` has `verdict: "approved"` |
| Doc review approved | Yes / No | Latest `review-feedback` with `author: "doc-reviewer"` has `verdict: "approved"` |
| All 4 reviewers approved | Yes / No | All four above are Yes |
| Build retry cycles | 0–3+ | Count of `build-failure` records for `req_id` since the latest `design-block` |
| Design revisions | 0–N | Count of `design-block` records for `req_id` that carry `supersedes_record_at` (re-triage after build-failure escalations) |

When reviewers raise findings with the optional `bar_clause` field set, list the clauses that were flagged in the Notes block — that surfaces which parts of the bar required rework without requiring a separate scoring pass.

## Output Format

Write to `.scratch/eval-<feature-name>.md` where `<feature-name>` is the `req_id` field of the latest `type: "prd-entry"` record in `.scratch/handoff.jsonl`, lowercased (e.g. `eval-req-xx-058.md`).

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
- **Bar clauses that required rework:** [list slugs from `bar_clause`-tagged findings, or "none"]
- **Notes:** [any observations about the pipeline run]
```

## Rules

- PASS requires: tests pass AND all 4 reviewers approved.
- A feature that required design revision is still a PASS if it ultimately succeeds, but note the revision in the summary.
- Do not modify any other `.scratch/` files. This skill is read-only except for the eval file.
