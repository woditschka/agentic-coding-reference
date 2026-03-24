---
name: review-checklist
description: >-
  Review process overview, feedback tag definitions, and output format.
  Load when conducting or processing code reviews.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## Review Phase

After the feature-implementer passes the quality gate, invoke all four reviewers in parallel:

| Reviewer | Output File | Focus |
|---|---|---|
| code-quality-reviewer | `.scratch/reviews/code-quality.md` | Readability, Java style |
| test-reviewer | `.scratch/reviews/test-coverage.md` | Test pyramid, coverage, edge cases |
| security-reviewer | `.scratch/reviews/security.md` | OWASP, vulnerabilities |
| doc-reviewer | `.scratch/reviews/doc-review.md` | Documentation coherence, structure |

## Feedback Tags

| Tag | Meaning | Action |
|---|---|---|
| `[AUTOFIX]` | Clear fix, no decision needed | Route to artifact owner |
| `[BLOCKED]` | Critical issue, must fix before merge | Route to artifact owner; escalate if unclear |
| `[ESCALATE]` | Needs human decision | Write to `.scratch/escalations.md` |
| `[CLARIFY:prd]` | Requirement unclear | Route to product-requirements-expert |
| `[CLARIFY:system-design]` | Architecture question | Route to system-design-expert |
| `[CLARIFY:security-reviewer]` | Security question | Route to security-reviewer |
| `[CLARIFY:doc-reviewer]` | Documentation question | Route to doc-reviewer |

## Artifact Ownership

Review feedback targets the artifact, not a fixed agent. Route fixes to the owning agent:

| Artifact | Owner Agent |
|---|---|
| `docs/prd.md` | product-requirements-expert |
| `docs/system-design.md`, `docs/adr/*.md` | system-design-expert |
| `src/main/java/**/*.java` | feature-implementer |
| `src/test/java/**/*.java` | feature-implementer |
| Resource files, templates | feature-implementer |

Do not bundle doc fixes into a feature-implementer call. Do not send code fixes to doc agents.

## Review Output Format

Each reviewer writes to their output file using the template in `.claude/templates/review.md`.

## Issue Classification

| Checklist Category | Default Severity | Tag |
|--------------------|-----------------|-----|
| Cross-document coherence | Critical | `[BLOCKED]` |
| PRD boundary violations (Java code, class references, internal code names) | Critical | `[BLOCKED]` |
| Security vulnerabilities (CRITICAL/HIGH per `security-review` skill) | Critical | `[BLOCKED]` |
| Structural issues (missing anchors, broken links) | Fixable | `[AUTOFIX]` |
| Writing standards | Fixable | `[AUTOFIX]` |

## Processing Reviews

After all reviewers complete:

1. feature-implementer reads all four review files.
2. `[AUTOFIX]` items: fix immediately.
3. `[BLOCKED]` items: fix immediately; escalate if fix is unclear.
4. `[ESCALATE]` items: write to `.scratch/escalations.md`.
5. `[CLARIFY:agent]` items: request clarification from specified agent.
6. Write consolidated results to `.scratch/review-summary.md`.
7. If all reviewers approve, feature is complete.
8. If changes were needed, re-run quality gate and re-invoke reviewers.
