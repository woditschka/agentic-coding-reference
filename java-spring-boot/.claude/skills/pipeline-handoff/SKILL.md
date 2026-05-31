---
name: pipeline-handoff
description: >-
  Pipeline routing rules and handoff conditions between specialist agents.
  Load when coordinating feature delivery, checking pipeline state,
  or determining which agent to invoke next.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
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

All transitions are gated on the latest record per `(req_id, type)` in `.scratch/handoff.jsonl`. The Validation Gates section below defines each gate's structural checks.

| Current Agent | Trigger | Next Agent |
|---|---|---|
| product-requirements-expert | latest `prd-entry` record passes the Validation Gate | system-design-expert |
| system-design-expert | latest `design-block` record has `verdict` in {`covered`, `minor`, `new`, `foundational`} and passes the Validation Gate | feature-implementer |
| system-design-expert | latest `design-block` record has `verdict: "conflicting"` | Halt pipeline; surface to user |
| Any specialist | latest record is a `consultation-request` | target specialist (consultation mode) |
| Any specialist | latest record is a `consultation-response` | **back to the requesting specialist** (resume; do not advance the pipeline) |
| feature-implementer | latest `build-pass` record exists and post-dates any `build-failure` for the same `req_id` | All reviewers (parallel) |
| feature-implementer | latest `build-failure` record has `retry < 3` | feature-implementer (retry with error context) |
| feature-implementer | latest `build-failure` record has `retry == 3` | system-design-expert (re-triage) |
| feature-implementer | a `dispatch-start` for `(req_id, feature-implementer)` exists with no subsequent substantive record from the same `(req_id, author)` (deterministic per § Dispatch Truncation Detection) | product-requirements-expert (re-split per Truncation Recovery) |
| feature-implementer | latest `build-failure` record has `abort_reason` set | routed per § Build-Failure Recovery → Abort-Reason Short-Circuit |
| system-design-expert | latest `design-block` record has `verdict: "refactor-first"` and a sibling refactor `prd-entry` (newer `ts`, different `req_id`) | feature-implementer for the refactor `req_id` first; resume original `req_id` triage via `supersedes_record_at` after the refactor's `build-pass` |
| All four reviewers | each reviewer's latest `review-feedback` record has `verdict: "approved"` | Feature complete |
| Any reviewer | latest `review-feedback` record has `verdict: "changes_requested"` or `"blocked"` with non-empty findings | feature-implementer (process findings) |

## Validation Gates

Each agent transition validates the inbound record(s) against a schema before dispatching the next specialist. Malformed or missing records bounce back to the upstream agent without consuming a downstream dispatch.

### Common Procedure

1. **Discover.** Run `Glob .scratch/**/*` to enumerate state files. Then `Read .scratch/handoff.jsonl` only if it appears in the Glob result. Do not `Read` directories.
2. **Gate.** If `handoff.jsonl` is missing or empty when a record is required, the gate fails — route back to the upstream agent.
3. **Filter.** Records by `req_id` and `type`. The **latest** record for each `(req_id, type)` is the active state.
4. **Check.** Required fields, types, and pattern constraints per the schema.
5. **Decide.** If every check passes: dispatch the next agent. If any check fails: route back upstream with a `Blocked` recommendation naming the specific failed check.

### Gate 1: product-requirements-expert → system-design-expert (`prd-entry`)

Schema: [`schemas/scratch/prd-entry.schema.json`](../../../schemas/scratch/prd-entry.schema.json). Required checks:

- `type == "prd-entry"`, `author == "product-requirements-expert"`.
- `req_id` matches `^REQ-[A-Z]+-[0-9]{3}$`. `ts` is a non-empty ISO 8601 string.
- `title`, `summary` are non-empty strings.
- `acceptance_criteria`, `file_targets`, `test_names` are non-empty arrays of non-empty strings.
- Each `test_names` entry matches `^[a-z][A-Za-z0-9_]*$` (Java method naming).

### Gate 2: system-design-expert → implementer (`design-block`)

Schema: [`schemas/scratch/design-block.schema.json`](../../../schemas/scratch/design-block.schema.json). Required checks:

- `type == "design-block"`, `author == "system-design-expert"`, valid `req_id` and `ts`.
- `verdict` is one of: `covered`, `minor`, `new`, `foundational`, `conflicting`, `refactor-first`.
- `architectural_fit` is non-empty; `primary_paths` is a non-empty array of non-empty strings.
- When `verdict == "conflicting"`: `escalations` array is present and non-empty.
- When `supersedes_record_at` is present (revising after a build-failure): it points to a prior `design-block` record line in the file.

Routing:

- `covered`, `minor`, `new`, or `foundational` → dispatch feature-implementer. A record with `supersedes_record_at` set resets the build-failure retry counter for that `req_id`.
- `conflicting` → halt the pipeline; human decides.
- `refactor-first` → dispatch feature-implementer for the sibling refactor `prd-entry` first; resume the original slice's triage via a new `design-block` with `supersedes_record_at` after the refactor's `build-pass`. See the Handoff Conditions table row for the full trigger.

### Gate 2b: Consultation roundtrip (`consultation-request` / `consultation-response`)

Schemas: [`schemas/scratch/consultation-request.schema.json`](../../../schemas/scratch/consultation-request.schema.json), [`schemas/scratch/consultation-response.schema.json`](../../../schemas/scratch/consultation-response.schema.json).

When the latest record is a `consultation-request`:

- Validate `type`, `req_id`, `ts`, `author` (the requesting specialist), `target` (the specialist to consult), `context`, `question`.
- Dispatch the `target` agent in consultation mode (it reads the request and the relevant durable memory, then appends a `consultation-response`).

When the latest record is a `consultation-response`:

- Validate `type`, `req_id`, `ts`, `author` (must match the `target` of the corresponding request), `in_response_to` (1-indexed line number pointing to the request), `answer`.
- Route control **back to the requesting specialist named in the corresponding request**. Do not advance the pipeline stage. The requester resumes its main work; the pipeline advances only when the requester's main work reaches its own next handoff.

### Gate 3: implementer → reviewers (`build-pass`)

Schema: [`schemas/scratch/build-pass.schema.json`](../../../schemas/scratch/build-pass.schema.json). Required checks:

- The latest `build-*` record for `req_id` is `type == "build-pass"`.
- `author == "feature-implementer"`, valid `req_id` and `ts`.

If the latest is a `build-failure`, apply Build-Failure Recovery instead.

### Gate 4: reviewers → next step (`review-feedback`)

Schema: [`schemas/scratch/review-feedback.schema.json`](../../../schemas/scratch/review-feedback.schema.json). For each of the four reviewers, the latest `review-feedback` record (filtered by `req_id` and `author`) must:

- Have `type == "review-feedback"`, valid `req_id` and `ts`.
- `author` is one of: `code-quality-reviewer`, `test-reviewer`, `security-reviewer`, `doc-reviewer`.
- `verdict` is one of: `approved`, `changes_requested`, `blocked`.
- `findings` is an array; when `verdict != "approved"`, it should be non-empty (warn but do not hard-fail; an empty findings list with a non-approved verdict means the reviewer did not produce actionable output and should be re-dispatched).
- Each finding has `tag`, `location`, `description`. When `tag == "clarify"`, `clarify_target` is required.

Routing:

- All four `verdict == "approved"` → feature complete; load `feature-eval` skill.
- Any `verdict == "changes_requested"` or `"blocked"` → split the union of findings by artifact owner (see `review-checklist` § Artifact Ownership), then dispatch each owner agent with the relevant slice. **Exception:** `tag == "autofix"` findings whose `location` is a design-doc path (`docs/system-design.md` or `docs/adr/*.md`) are applied by root directly per `review-checklist` § Root-Applied Autofix on Design Docs — they do NOT redispatch system-design-expert. Every other finding on those paths still routes to system-design-expert.
- Any `tag == "escalate"` finding → also append an entry to `.scratch/escalations.md`.

### What the gates do NOT check

- Content quality (are the acceptance criteria *good*? are the findings *correct*?). That is the consuming agent's judgement.
- Cross-record consistency beyond `req_id` linkage (e.g. whether `design-block.primary_paths` overlaps `prd-entry.file_targets`). Consumers may surface mismatches as findings; gates do not.

The gates are structural: required fields present, types correct, patterns match. Every check must catch deterministically.

## Blocking

If any gate fails, if a `design-block` record carries `verdict: "conflicting"`, or if a `review-feedback` record carries a `tag: "escalate"` finding, stop the pipeline and resolve before continuing.

## Build-Failure Recovery

When the feature-implementer runs the quality gate (`./gradlew build && ./gradlew test && ./gradlew checkJavaFormat`) and it fails, the implementer appends a `build-failure` record to `.scratch/handoff.jsonl` with the error output and retry count, then exits. Schema: [`schemas/scratch/build-failure.schema.json`](../../../schemas/scratch/build-failure.schema.json).

### Coordinator retry logic

0. **Abort-Reason Short-Circuit.** If the latest `build-failure` record's `abort_reason` field is set, the implementer is aborting because the slice cannot be implemented as triaged — not because the gate failed. Skip the retry counter and route based on the value:

   - `wrong-shape-slice` → `product-requirements-expert` for re-split. Pass `error_output` as the diagnosis input. Same destination as Truncation Recovery, but with the implementer's explicit reasoning.
   - `design-mismatch` → `system-design-expert` for re-triage. The next `design-block` carries `supersedes_record_at` pointing to the prior design-block.
   - `prerequisite-missing` → halt the pipeline, append the issue to `.scratch/escalations.md`, surface to user.

   If the latest `build-failure` record has no `abort_reason` (the normal quality-gate failure case), proceed to step 1.

1. Read `.scratch/handoff.jsonl`. Take the latest `build-failure` record for the active `req_id`.
2. If `retry < 3`, route back to feature-implementer with this prompt context:
   - The latest `build-failure` record (the error output).
   - The latest `design-block` record (the original design).
   - `.scratch/implementation-plan.md` (what was planned).
   - Instruction: "Fix the build failure described in the latest `build-failure` record. This is retry N of 3."
3. If `retry == 3`, route back to system-design-expert for re-triage with this prompt context:
   - All `build-failure` records for the active `req_id` since the latest `design-block` (the failure trail).
   - The latest `design-block` record.
   - Instruction: "The implementer failed 3 times. Re-triage the slice; the prior design block may need revision."
   - The system-design-expert re-triages and appends a new `design-block` record with one of the six verdicts (`covered` / `minor` / `new` / `foundational` / `conflicting` / `refactor-first`) and `supersedes_record_at` set to the line number of the prior design-block.
4. A new `design-block` with `supersedes_record_at` set resets the retry counter — the next `build-failure` record starts at `retry: 1`. If the new verdict is `conflicting`, the pipeline halts and surfaces to the user instead.

### Retry rules

- The implementer increments `retry` in each new `build-failure` record (1, 2, 3). Compute the next value by counting `build-failure` records for the active `req_id` appended *after* the latest `design-block` line, then setting `retry = count + 1`. The first failure after a fresh `design-block` (whether the latest is the original or a record with `supersedes_record_at` set) is `retry: 1`. Append-only — never edit a prior record.
- On success, the implementer appends a `build-pass` record. Prior `build-failure` records remain in the file as the diagnostic retry trail.
- The coordinator never modifies records — it only reads them for routing decisions.
- Maximum 3 retries per design cycle. A new `design-block` with `supersedes_record_at` starts a fresh cycle.

## Truncation Recovery

When the feature-implementer's dispatch ends without appending a `build-pass` or `build-failure` record for the active `req_id`, the implementer truncated before reaching the quality gate. The slice was scoped beyond a single cap-bounded turn. **Never re-dispatch the implementer with the original scope wrapped in a "resume," "continue," or "finish this pass" prompt.** That pattern re-runs the over-scope: the implementer rebuilds full context from scratch and re-truncates at the same cap, doubling the cost without progress.

### Dispatch Truncation Detection

Every dispatched project-defined agent except `pipeline-coordinator` appends a `dispatch-start` record as its first tool call. Schema: [`schemas/scratch/dispatch-start.schema.json`](../../../schemas/scratch/dispatch-start.schema.json). Substantive records (the closed enum below) act as the implicit stop signal. **Deterministic detection rule:**

> A `dispatch-start` record for `(req_id, author)` with no subsequent substantive record from the same `(req_id, author)` after that `dispatch-start`'s line signals an interrupted dispatch.

Substantive records (closed enum): `build-pass`, `build-failure`, `review-feedback`, `prd-entry`, `design-block`, `consultation-response`. `consultation-request`, `design-doc-autofix`, and `dispatch-start` itself are explicitly NOT substantive.

`pipeline-coordinator` is exempt from the contract — its output is a routing recommendation in the response stream, not a substantive `.scratch/` record, so "start without substantive record" would always fire. Built-in agents not defined under `.claude/agents/` (e.g. `general-purpose`, `Explore`) are out of scope for this contract; root carries the dispatch-discipline for those per `CLAUDE.md` § Tool-call budget.

### Coordinator routing

1. Detect: apply the **Dispatch Truncation Detection** rule above. A `dispatch-start` for `(req_id, feature-implementer)` exists with no subsequent substantive record from `feature-implementer` for that `req_id` — the implementer's dispatch was interrupted before it could write a `build-pass` or `build-failure`.
2. Route back to product-requirements-expert with the instruction to append a new `prd-entry` record covering **one deliverable surface and at most three remaining acceptance criteria**. The new record naturally becomes the active scope under the "latest record per `(req_id, type)`" rule; the prior `prd-entry` remains in the file as part of the append-only trail.
3. The new `prd-entry` flows through Gate 1 → system-design-expert → feature-implementer like any other slice. Remaining acceptance criteria from the original requirement may ship as subsequent `prd-entry` records.
4. If the truncated work is genuinely indivisible (rare — challenge first), product-requirements-expert documents why in the new `prd-entry`'s `notes` field and the pipeline halts for human review.

The coordinator never dispatches feature-implementer without a fresh `prd-entry` validated through Gate 1. Resume-with-original-scope is structurally unavailable.

### Partial-record paths

Two partial-record paths route through existing recovery — they do NOT trigger Truncation Recovery:

- **`build-failure` with `partial: true`** (feature-implementer reached `toolCallBudget` before the quality gate ran). The record flows through Build-Failure Recovery above: `retry < 3` re-dispatches the implementer with the partial-progress description in `error_output`; `retry == 3` re-triages via system-design-expert. The implementer's next dispatch starts from the recorded progress instead of from scratch.
- **`review-feedback` with `verdict: "blocked"` plus a `tag: "escalate"` truncation finding** (a reviewer reached `toolCallBudget` mid-review). The record routes through Gate 4's existing `changes_requested` / `blocked` path: feature-implementer processes findings, then the cycle re-runs the gate and re-invokes reviewers.

Truncation Recovery (this section) covers only the residual case — the dispatch ended with **no new record at all** for the active `req_id`. The partial-artifact contract shrinks that population by structurally giving creator and verifier dispatches a way to leave evidence behind before exiting.

### Known gap (closed): detection mechanism

This procedure previously fired only when root explicitly signalled truncation, because state files could not distinguish *implementer dispatched and truncated* from *implementer not yet dispatched*. The `dispatch-start` record (see § Dispatch Truncation Detection above) is now the deterministic trigger: a `dispatch-start` for `(req_id, feature-implementer)` with no subsequent substantive record from the same `(req_id, author)` is the unambiguous truncation signal.

## Mid-Implementation Consultation

The feature-implementer may need a focused answer from product-requirements-expert or system-design-expert during TDD cycles when the inner loop discovers a question the triage didn't anticipate. The implementer appends a `consultation-request` targeting the specialist; the coordinator dispatches that specialist in consultation mode; the specialist appends a `consultation-response`; the coordinator routes control back to the implementer.

Consultations are substeps, not handoffs. They preserve the implementer's active state — the pipeline advances only when the implementer's own next handoff (`build-pass` or `build-failure`) appears.

## Review Feedback Actions

See the `review-checklist` skill for feedback tag definitions and the review process.

## State Files

| File | Created By | Consumed By |
|---|---|---|
| `.scratch/handoff.jsonl` | product-requirements-expert, system-design-expert, feature-implementer, four reviewers, root (all append-only) | coordinator (validation gates), all consumer agents |
| `.scratch/implementation-plan.md` | feature-implementer | feature-implementer (self-tracking) |
| `.scratch/escalations.md` | feature-implementer | Human |
| `.scratch/eval-*.md` | coordinator (via feature-eval skill) | Human |

`.scratch/handoff.jsonl` is the append-only structured handoff log; one JSON object per line, each carrying a `type` discriminator. Record types:

| Record `type` | Producer | Purpose |
|---|---|---|
| `prd-entry` | product-requirements-expert | Active feature scope for system-design-expert and implementer. |
| `design-block` | system-design-expert | Triage verdict and implementation guidance. |
| `consultation-request` | any specialist mid-work | Focused question to another specialist that does not advance the pipeline. |
| `consultation-response` | the consulted specialist | Focused answer; routes control back to the requester. |
| `review-feedback` | each of the four reviewer agents | Per-reviewer verdict and findings. |
| `build-failure` | feature-implementer | Quality-gate failure with error context and retry counter. |
| `build-pass` | feature-implementer | Quality-gate success marker. |
| `design-doc-autofix` | root (coordinator) | Audit trail for root-applied autofixes on design-doc paths (see `review-checklist` § Root-Applied Autofix on Design Docs). |
| `dispatch-start` | every project-defined agent except `pipeline-coordinator` (as its first tool call) | Half of the dispatch-event contract; "no subsequent substantive record from same `(req_id, author)`" is the deterministic truncation signal. Not substantive — does not satisfy the implicit stop. |

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
4. Report all `design-block` records with `verdict: "conflicting"` and all `review-feedback` findings tagged `escalate`.
5. If the latest `build-*` record for the active `req_id` is a `build-failure`, apply the retry logic in the "Build-Failure Recovery" section.
6. If a feature-implementer dispatch ended without appending a `build-pass` or `build-failure` record, apply the "Truncation Recovery" procedure — never re-dispatch with the original scope.
7. After all four reviewers' latest `review-feedback` verdicts are `"approved"`, load the `feature-eval` skill and write the evaluation scorecard.

## Pipeline Flow

```
User Request
    |
    v
Pipeline Coordinator (classifies request, validates latest handoff.jsonl records)
    |
    +--- New feature ------> product-requirements-expert
    |                              | (appends prd-entry record)
    |                              v
    |                        system-design-expert
    |                              | (appends design-block; verdict: covered | minor | new | foundational)
    |                              v
    |                        feature-implementer
    |                              | (may consult system-design-expert/product-requirements-expert mid-loop via consultation-request/response — does NOT advance pipeline)
    |                              | (appends build-failure or build-pass; absent → see Truncation Recovery)
    |                     +--------+--------+
    |                     |                 |
    |                     v (build-pass)    v (build-failure, retry < 3)
    |               All reviewers      feature-implementer
    |                  (parallel)       (retry with error context)
    |                     |                 |
    |                     |                 v (build-failure, retry == 3)
    |                     |           system-design-expert (re-triage)
    |                     |           (new design-block with supersedes_record_at)
    |                     |                 |
    |                     |                 v (retry reset)
    |                     |           feature-implementer
    |                     |
    |                     v (all four review-feedback verdicts: approved)
    |               Feature eval → .scratch/eval-<name>.md
    |                     |
    |                     v
    |               Feature complete
    |
    +--- Bug fix (known) --> feature-implementer (shortcut)
    +--- Architecture Q ---> system-design-expert (single agent)
    +--- Code review ------> All reviewers (parallel)
```
