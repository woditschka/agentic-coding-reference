---
name: review-checklist
description: >-
  Review process overview, feedback tag definitions, and output format.
  Load when conducting or processing code reviews.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/testing-principles.md
  - docs/architecture-principles.md
metadata:
  version: "1.0"
  author: team
---

## Review Phase

After the feature-implementer appends a `build-pass` record to `.scratch/handoff.jsonl`, invoke all four reviewers in parallel:

| Reviewer | `author` value | Focus |
|---|---|---|
| code-quality-reviewer | `"code-quality-reviewer"` | Readability, Go style guide |
| test-reviewer | `"test-reviewer"` | Test pyramid, coverage, edge cases |
| security-reviewer | `"security-reviewer"` | OWASP, vulnerabilities, supply chain |
| doc-reviewer | `"doc-reviewer"` | Documentation coherence, structure |

Each reviewer appends one `review-feedback` record. Schema: [`schemas/scratch/review-feedback.schema.json`](../../../schemas/scratch/review-feedback.schema.json).

## Output Protocol (Reviewers)

Your sole deliverable is the appended `review-feedback` record. The pipeline cannot proceed without it.

1. **Read** `.scratch/handoff.jsonl` first. If the file does not exist, the implementer has not signalled gate-pass — abort and report the missing precondition.
2. **Append one line** to `.scratch/handoff.jsonl` via `python3 scripts/handoff.py append review-feedback` (`pipeline-handoff` skill § Log Access): a single JSON object conforming to the `review-feedback` schema. Required fields: `type` (`"review-feedback"`), `req_id`, `ts`, `author` (your reviewer name), `verdict` (`approved` | `changes_requested` | `blocked`), `findings` (array, possibly empty when `verdict: "approved"`).
3. Each finding requires `tag`, `location`, `description`. Add `fix` for `tag: "autofix"`. Add `clarify_target` for `tag: "clarify"`. Severity is optional (`critical` | `fixable`).
4. **Append-only is non-negotiable** — never edit, reorder, or delete prior records.
5. **Verify**: `append` prints the new record's line number on success; a non-zero exit means the record was rejected — fix the record, never the file.
6. Your reply to the caller MUST be exactly one line: `Appended review-feedback (<verdict>) for <req_id>`.
7. Do NOT include review content, summaries, or analysis in your reply. The caller reads the record.

**Why:** when review content lands in the reply instead of the file, the dispatcher cannot route fixes, artifact-owner agents cannot read findings, and the audit trail is lost. Stopping before the append forces the user to re-run the review — this is a recurring reviewer failure mode.

### Example Record

```json
{"type":"review-feedback","req_id":"REQ-XX-099","ts":"2026-05-08T16:30:00Z","author":"code-quality-reviewer","verdict":"changes_requested","findings":[{"tag":"autofix","location":"internal/report/summary.go:142","description":"Variable name `r` shadows the package-level `r`.","fix":"Rename loop variable to `row`."},{"tag":"blocked","location":"internal/report/summary.go:160","description":"Division by zero possible when cache_eligible_token_count is 0.","severity":"critical"}],"approved_aspects":["Test naming follows conventions","Error wrapping uses fmt.Errorf with %w"]}
```

## Feedback Tags

| Tag | Meaning | Action |
|---|---|---|
| `autofix` | Clear fix, no decision needed | Route to artifact owner |
| `blocked` | Critical issue, must fix before merge | Route to artifact owner; escalate if unclear |
| `escalate` | Needs human decision | Append to `.scratch/escalations.md` |
| `clarify` (with `clarify_target`) | Requirement, design, or review question | Route to the named agent |

Choose the tag by what the finding needs next, not by its severity. `autofix` when the fix is mechanical and decision-free; `blocked` when merging would ship a defect; `escalate` when only a human can decide; `clarify` when the finding is really a question for another agent. The tag is a routing decision — pick the one that moves the finding to whoever can resolve it.

## Quality-Bar Clause Mapping (`bar_clause` field)

The eight clauses below are the conjunctive "done" definition for any change. The clauses themselves are defined in [`tdd-principles.md`](../tdd-workflow/tdd-principles.md) (§ Scope Discipline, § Code That Reads Cold, § Operationally Honest), with mechanics in [`docs/testing-principles.md`](../../../docs/testing-principles.md) and [`docs/architecture-principles.md`](../../../docs/architecture-principles.md). This skill owns the *canonical slug list* — the schema enum on `review-feedback.bar_clause` references back to this table.

When a finding violates one of these clauses, set the optional `bar_clause` field on the finding to the matching slug. The `change-grader`'s reviewer_hedging facet reads the flagged clauses as a hedge signal; reviewers and operators thereby get a shared frame for what part of the bar came under pressure.

| `bar_clause` | Set when the finding shows… | Reviewers that typically raise it | Defined in |
|---|---|---|---|
| `fit-for-purpose` | Speculative generality, abstractions without two real call sites, defensive code for impossible cases, scope creep | code-quality, test, security | `tdd-principles` § Scope Discipline |
| `spec-grounded` | Behavior outside the requirement, silently absorbed scope drift, unresolved spec ambiguity | code-quality, doc | `tdd-principles` § Scope Discipline |
| `legible-cold` | Inaccurate names, structure that obscures intent, non-obvious decisions without why-comments or ADRs | code-quality, doc | `tdd-principles` § Code That Reads Cold |
| `correct` | Spec cases not handled, listed failure modes not handled, boundary inputs not validated | test, security | `tdd-principles` § Code That Reads Cold; `testing-principles` § Edge Case and Boundary Testing |
| `tested-as-spec` | Tests of implementation detail, mocks of internal code, test names that do not read as specification, missing failure-mode coverage | test | `tdd-principles` § Code That Reads Cold; `testing-principles` § Tests Are Specifications, § Test Naming, § Mocking Policy |
| `consistent-with-codebase` | Pattern or naming mismatch with neighboring code, unjustified style deviation | code-quality | `tdd-principles` § Scope Discipline; `architecture-principles` § Naming |
| `operationally-honest` | Errors without actionable context, unreasonable resource use for workload, missing rollback note where required | security, code-quality | `tdd-principles` § Operationally Honest; `architecture-principles` § Domain Core |
| `human-maintainable` | Artifacts that only make sense to re-prompt, comments addressed to the agent, code shape that depends on the harness being present | doc, code-quality | `tdd-principles` § Operationally Honest |

Procedural findings (lint, typo, missing language tag on a fence) carry `tag` but no `bar_clause` — they are mechanical and do not target a clause. A single finding may carry both `tag` and `bar_clause` when both apply: a `blocked` finding for a missing rollback note also carries `bar_clause: "operationally-honest"`.

## Artifact Ownership

Review feedback targets the artifact, not a fixed agent. Route fixes to the owning agent:

| Artifact | Owner Agent | Autofix Exception |
|---|---|---|
| `docs/prd.md` | product-requirements-expert | — |
| `docs/system-design.md`, `docs/adr/*.md` | system-design-expert | Root applies `tag: "autofix"` per the protocol below; all other tags route to system-design-expert |
| `internal/**/*.go`, `cmd/**/*.go` | feature-implementer | — |
| `internal/**/*_test.go` | feature-implementer | — |
| Templates, static assets | feature-implementer | — |

Do not bundle doc fixes into a feature-implementer call. Do not send code fixes to doc agents.

## Root-Applied Autofix on Design Docs

To keep the system-design-expert quality bar tight while removing ceremony from mechanical fixes, the root coordinator may apply `tag: "autofix"` findings on `docs/system-design.md` and `docs/adr/*.md` directly — without redispatching system-design-expert. The quality bar lives in the `blocked` and `clarify` (with `clarify_target: "system-design-expert"`) paths, which still route to system-design-expert.

The eligibility rules for autofix on design-doc paths live in the `doc-review` skill. Doc-reviewer is responsible for never tagging a finding as autofix on these paths unless every condition there holds. This section defines what root does once such a finding exists.

### Apply Procedure

1. **Validate the finding statically.** Confirm: `tag == "autofix"`; `location` falls under a design-doc path; `fix` field is present and is a literal replacement string (not a description). If any check fails, treat the finding as `blocked` and redispatch system-design-expert instead.
2. **Apply via Edit.** Use the Edit tool with the literal `fix` string as `new_string`. Read the file to obtain the exact `old_string`. Do not paraphrase or "improve" the fix — root acts as a typewriter for the doc-reviewer's verbatim proposal.
3. **Re-check the bounds after the Edit.** Confirm: ≤5 lines changed, ≤200 characters changed, no `## ` heading line modified, no `<a id="..."></a>` anchor value changed, no REQ-ID reference introduced or removed, no content inside a fenced code block touched, no markdown link target changed. If any check fails, revert (Edit back) and redispatch system-design-expert.
4. **Append a `design-doc-autofix` record** to `.scratch/handoff.jsonl` carrying: the source finding (copied verbatim), the file path, the autofix category (`writing-standards` or `structural`), `old_content`, `new_content`, `lines_changed`, `chars_changed`. Schema: [`schemas/scratch/design-doc-autofix.schema.json`](../../../schemas/scratch/design-doc-autofix.schema.json).
5. **Append-only discipline.** Preserve every prior line in `handoff.jsonl` verbatim.

### Why The Record Matters

- **Gate-time re-validation.** The autofix-audit procedure in `code-quality-gate` re-checks every `design-doc-autofix` record against the bounds in step 3, so a mis-applied autofix fails the quality gate before merge.
- **The system-design-expert audits on next dispatch.** The `design-validation` skill instructs the system-design-expert to read all `design-doc-autofix` records since its last dispatch and judge them. It may reject any by appending an `autofix-rejected` finding to the next `design-block` record.
- **Direct-edit detection.** The `code-quality-gate` autofix audit also fails if `docs/system-design.md` or `docs/adr/*` has uncommitted changes that no `design-doc-autofix` or `design-block` record covers — catching any future bypass of the protocol.

### What Root Does Not Do

- Root does NOT autofix on `docs/prd.md` (product-requirements-expert owns PRD; no autofix exception).
- Root does NOT autofix any tag other than `autofix` (blocked/clarify/escalate route as defined elsewhere).
- Root does NOT batch autofixes across artifacts — one record per finding, one Edit per finding.

## Issue Classification

| Checklist Category | Default Severity | Tag |
|--------------------|-----------------|-----|
| Cross-document coherence | Critical | `blocked` |
| PRD boundary violations (Go code, function signatures, internal references) | Critical | `blocked` |
| Security vulnerabilities (CRITICAL/HIGH per `security-review` skill) | Critical | `blocked` |
| Structural issues (missing anchors, broken links) | Fixable | `autofix` |
| Writing standards | Fixable | `autofix` |

## Processing Reviews

After all reviewers complete:

0. Verify each of the four reviewers has appended a `review-feedback` record for the current `req_id` since the latest `build-pass`. For each missing record, re-dispatch the corresponding reviewer ONCE with this prompt: `"Your previous run returned without appending a review-feedback record to .scratch/handoff.jsonl. Run the review now. Your only deliverable is that record — see Output Protocol in review-checklist."` If a record is still missing after the retry, append an entry to `.scratch/escalations.md` naming the reviewer and stop — do not proceed to step 1.
1. feature-implementer reads all four `review-feedback` records (latest per reviewer for the active `req_id`).
2. `tag: "autofix"` findings: fix immediately using the `fix` field.
3. `tag: "blocked"` findings: fix immediately; escalate if fix is unclear.
4. `tag: "escalate"` findings: append the description to `.scratch/escalations.md`.
5. `tag: "clarify"` findings: request clarification from the agent named in `clarify_target`.
6. (No consolidated summary file needed; the four `review-feedback` records are the canonical record.)
7. If all four `verdict` values are `"approved"`, feature is complete.
8. If any `verdict` is `"changes_requested"` or `"blocked"`, re-run the quality gate (append fresh `build-failure`/`build-pass` records) and re-invoke reviewers.

## Partial-Artifact Contract

Reviewers carry the verifier half of the partial-artifact contract. Two halves: a Scoping Pre-Check before the first tool call, and a planned checkpoint named in that pre-check.

### Scoping Pre-Check (reviewer)

Before the first tool call, run the three-step pre-check defined in the `tdd-workflow` skill § Scoping Pre-Check, adapted to the review surface:

1. Read the latest `build-pass` record for the active `req_id`, the changed files named in the diff (`git diff --name-only`), and the implementation plan if present.
2. Estimate the tool calls the review needs — reads (one per changed file plus the durable memory the review checklist points at), bash invocations (the specific commands listed in your review process), and the single `review-feedback` append. Each checklist is bounded; the estimate is single-digit precision.
3. Run two independent checks. **Scope (budget-free):** does the change span more than one behavior or bounded context? Answer it from the inbound records, not the estimate — a multi-behavior change is mis-sized even when it would fit the budget. If yes, **stop and append a `consultation-request`** naming the over-scope — `product-requirements-expert` when the slice itself is too big, `system-design-expert` when the diff surface is too broad; do not start the review. **Length:** for a single-behavior change, if the tool-call estimate fits your `toolCallBudget` (set in your agent front-matter) proceed; if it exceeds the budget on mechanical surface alone (many files against one checklist), do **not** re-scope — proceed with the planned checkpoint below, where a partial `review-feedback` carries the findings so far so the review completes on re-invocation. `toolCallBudget` governs only the length check.

Write the estimate as one or two sentences before the first tool call so the transcript carries it.

### Planned-checkpoint trigger

The model cannot count its own tool calls precisely. The trigger is therefore a **planned checkpoint** named at Pre-Check time, not a running count.

**Choosing the checkpoint.** For a review of K changed files, set the checkpoint at "after reviewing ⌈K/2⌉ files." For a checklist-driven review (security threat model, dynamic-analysis run), set it at "after completing the first half of the checklist steps." Write the checkpoint as one of the Pre-Check sentences before the first tool call.

**At the checkpoint, the decision is unconditional.** If the review is complete, write the final `review-feedback` as normal. If not, **append a partial `review-feedback` record now** with the findings collected so far, then stop. Do not assess "am I close to done" — that assessment is the introspection the contract rejects.

**Partial-record shape.** The `review-feedback` carries:

- `verdict: "blocked"`
- `findings`: every finding collected so far, in their normal shape
- One additional `escalate` finding naming the truncation:

```json
{"tag":"escalate","location":"<review surface, e.g. internal/report/>","description":"Reviewer reached planned checkpoint with <unreviewed surface> not yet reviewed. Findings above cover <reviewed surface> only.","severity":"critical"}
```

The downstream loop (feature-implementer processing findings) sees a real record with inspectable partial progress instead of a missing reviewer, and the `escalate` tag routes the truncation finding to `.scratch/escalations.md` per the existing Feedback Tags table.

The contract complement to an `approved` `review-feedback` is this `blocked` + truncation finding. Both are first-class outputs of a dispatch; neither is a failure mode. The pipeline-coordinator's review-feedback routing already handles `blocked` verdicts by dispatching the feature-implementer for findings processing — no new routing is needed.
