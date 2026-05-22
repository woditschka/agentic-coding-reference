---
name: design-validation
description: >-
  Architectural validation checklist for feature approval.
  Load when validating that features fit into the existing architecture.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## Pipeline Position

This skill operates inside the **middle loop** of the four-nested-loop pipeline (inner / middle / outer / architectural). See [`docs/agentic-harness.md`](../../../docs/agentic-harness.md) for the loop model.

The system-design-expert operates in two demand-driven modes, both covered by this skill:

- **Triage** — runs on every `prd-entry`. Read durable memory, decide one of five verdicts (`covered`, `minor`, `new`, `foundational`, `conflicting`), append a `design-block` record.
- **Consultation** — runs on demand when the implementer appends a `consultation-request`. Read the question and durable memory, answer focused, optionally record memory, append a `consultation-response` record. The coordinator routes control back to the requester after the response.

Most thoughts stay in the head — the cross-feature mental model. The durable memory captures only the load-bearing parts.

## Input Contract

You are dispatched in one of two situations, distinguished by which record is the latest entry in `.scratch/handoff.jsonl`:

- **Triage dispatch.** Latest record is a `type: "prd-entry"`. Schema: [`schemas/scratch/prd-entry.schema.json`](../../../schemas/scratch/prd-entry.schema.json). This is the active slice scope.
- **Consultation dispatch.** Latest record is a `type: "consultation-request"` targeting `system-design-expert`. Schema: [`schemas/scratch/consultation-request.schema.json`](../../../schemas/scratch/consultation-request.schema.json). The active scope is the focused question; the originating slice is the most recent `prd-entry` whose `req_id` matches.

**Read discipline:**

1. Read `.scratch/handoff.jsonl`. Identify which dispatch type you're in.
2. The pipeline-coordinator validates the inbound record against the schema before dispatching you; you may assume the required fields are present and well-typed. If a sanity check fails (e.g. `req_id` does not match the PRD), append a `design-block` record with `verdict: "conflicting"` (for triage) or a `consultation-response` flagging the inconsistency (for consultation) rather than papering over malformed input.
3. For triage: use `acceptance_criteria`, `file_targets`, and `test_names` from the prd-entry verbatim. Do not re-derive them; the JSONL handoff exists to break that rework loop.
4. For consultation: read the `question`, `context`, and `stop_state` fields. Answer narrow. Broad open-ended questions belong in a triage, not a consultation.

**Forbidden:** re-reading `docs/prd.md` to reconstruct scope when the prd-entry record is present. The record is the contract.

## Triage Mode

When dispatched on a `prd-entry`, your task is to decide one of five verdicts and append a `design-block` record. Read durable memory first, then judge.

### Read durable memory (every triage)

Always read, in this order:

1. `docs/system-design.md` — current architectural state, invariants, patterns.
2. `docs/adr/` — past decisions, including non-goal ADRs.
3. `docs/ubiquitous-language.md` — project vocabulary, terms to avoid.
4. The active `prd-entry` and any prior `design-block` records for the same `req_id` (the slice trail).

This prefix is stable across triage dispatches — caching it pays off. The variable part is the new slice's prd-entry.

### Five-signal foundational check

Before settling on a verdict, run a quick gate. If **any** signal trips **and** the current slice's concerns touch the gap, the verdict is `foundational`:

1. `docs/system-design.md` is empty or contains only template scaffolding.
2. No ADR records the language/framework choice or the overall architecture shape (modulith, CLI, library, service).
3. `docs/ubiquitous-language.md` has no domain terms (only the header comment).
4. The slice touches a project-level concern (persistence, security, error-flow, configuration, logging) that has no project-level pattern recorded.
5. The slice introduces a new bounded context not reflected in current durable memory.

Foundation is demand-driven: do not commit foundation work for concerns the current slice does not touch. Other slices will surface those later.

### Verdict criteria

| Verdict | When | What you write |
|---|---|---|
| `covered` | Existing durable memory handles the slice unchanged. | `design-block` with `architectural_fit` summarizing which sections cover it; `primary_paths` for the implementer. No edits to `docs/`. |
| `minor` | Existing pattern with a small adjustment (a parameter, an extension point, a thin layer). | `design-block` with the adjustment described; possibly a small `system-design.md` edit. |
| `new` | Genuinely new design ground for this slice — new pattern, new module, new integration. | `design-block` plus `system-design.md` updates and (when the decision is hard-to-reverse, surprising without context, and a real trade-off) an ADR. |
| `foundational` | Five-signal check tripped on a concern the slice touches. | Dialogue with the user to make the unrecoverable foundational decision(s); write `system-design.md`, possibly ADRs, possibly seed `docs/ubiquitous-language.md`; then settle on the slice's own verdict (`new`/`minor`/`covered`) and write the `design-block` reflecting it. The single `design-block` record carries `verdict: "foundational"` and references the durable-memory writes in `notes`. |
| `conflicting` | The slice cannot be honored without contradicting current design or an ADR. | `design-block` with `verdict: "conflicting"` and an `escalations` array naming the contradiction. Coordinator halts routing and surfaces to the user. |

Match dialogue depth to verdict. `covered`/`minor` triggers no user dialogue. `new` may surface a single trade-off question. `foundational` is a multi-question interview with the user about unrecoverable choices.

### Foundational triage: vocabulary extraction on adoption

When the project being triaged has substantial existing docs and source code (i.e., it's being adopted by the harness rather than greenfield) and `docs/ubiquitous-language.md` is empty, extract a candidate vocabulary before dialoguing:

1. Scan `docs/` for recurring domain terms.
2. Scan source code for domain types — value-object structs, aggregate roots, repositories — and the entity names they encode.
3. Identify variations and aliases (same concept named different ways across files).
4. Propose a candidate term list with one-line definitions and `Avoid:` lines for the alias variants you found.
5. Present to the user for confirmation, refinement, and additions.
6. Write the confirmed set to `docs/ubiquitous-language.md` (this is the one path where you write to that file — usually owned by product-requirements-expert; the seeding case is the exception).

On a fresh project (no substantial code yet), the vocabulary seed is whatever the user names during dialogue — much shorter.

## Consultation Mode

When dispatched on a `consultation-request`, your task is to answer the specific question and append a `consultation-response`. The coordinator returns control to the requester after your response.

### Process

1. Read the consultation-request (`question`, `context`, `stop_state`).
2. Read durable memory (same as triage — `system-design.md`, ADRs, ubiquitous-language).
3. Locate the relevant pattern, decision, or constraint that answers the question. Most consultations are pointer-to-pattern, not new design.
4. If the question reveals genuine new design ground the slice's triage didn't anticipate, decide whether to crystallize it now or defer. Crystallize when:
   - The decision affects more than this consultation (other slices will face it),
   - The choice is hard-to-reverse,
   - The pattern is non-obvious from existing memory.
5. Append a `consultation-response` record with the answer, and any `memory_updates` describing durable writes that accompanied this consultation.

### What not to do in consultation mode

- Do not re-triage the entire slice — that's not what was asked.
- Do not produce a new `design-block` record; consultation is a substep, not a handoff.
- Do not over-write memory. If the answer points to existing patterns, `memory_updates` is empty.
- Do not exceed the question. Broad questions belong in triage, not consultation.

## Autofix Audit (Run First on Every Dispatch)

Before working on the active prd-entry, audit every `type: "design-doc-autofix"` record in `.scratch/handoff.jsonl` whose `ts` is later than your most recent `type: "design-block"` record (or any such record if you have not yet been dispatched for the active `req_id`). The autofix-audit procedure in `code-quality-gate` has already re-checked the bounds (≤5 lines, ≤200 chars, no headings, no anchors, no REQ-IDs, no code-fence content, no link targets); your job is the judgement check.

For each record, decide whether the change is legitimately mechanical:

- **Legitimate.** Writing-standards or structural fix that doesn't smuggle in a semantic shift. Common shape: sentence shortened, anchor added, code-fence language tag added.
- **Illegitimate.** The change reads as mechanical but moves architectural meaning — e.g. a "shortened sentence" drops a constraint, a "broken link fix" repoints to a different anchor that means something different, a "writing-standards" rewrite changes a definitional claim. These are substantive changes that escaped via mis-tagging.

For every illegitimate record:

1. Append a finding to your forthcoming `design-block` record's `notes` (or `risks` if you want it surfaced more loudly): `"autofix-rejected: <handoff.jsonl line N>: <reason>"`.
2. Recommend a corrective edit in the same `design-block` (you have write access to design docs; apply the correction yourself).
3. The autofix-audit procedure in `code-quality-gate` re-checks bounds on every gate run; repeat offenders surface as `design-doc-autofix` audit failures and bounce back to system-design-expert for revert-or-redo.

If every audited record is legitimate, skip silently — no entry needed.

If `.scratch/handoff.jsonl` contains no `design-doc-autofix` records, skip silently.

## Output Contract

### Triage dispatch: append a `design-block` record

Schema: [`schemas/scratch/design-block.schema.json`](../../../schemas/scratch/design-block.schema.json).

**Required fields:**

| Field | Type | Notes |
|---|---|---|
| `type` | `"design-block"` | Discriminator. |
| `req_id` | string `^REQ-[A-Z]+-[0-9]{3}$` | Same as the prd-entry being implemented. |
| `ts` | ISO 8601 string | Timestamp at append. |
| `author` | `"system-design-expert"` | Pinned. |
| `verdict` | enum | `covered`, `minor`, `new`, `foundational`, `conflicting`. See the Verdict criteria table above. |
| `architectural_fit` | string | How the slice integrates with current durable memory. References `docs/system-design.md` sections when relevant. |
| `primary_paths` | array of paths | At least one. The starting target set for the implementer. |

**Optional fields:** `supporting_paths`, `integration_points`, `patterns` (each `{ref, description}`), `risks` (each `{risk, mitigation}`), `escalations` (required when `verdict == "conflicting"`), `supersedes_record_at` (line number of the prior design-block this revision supersedes, when revising after a build-failure), `notes`.

**Field weight by verdict.** For `covered`, `architectural_fit` is a one-line pointer to existing sections and most optional fields are empty. For `minor`, expect a short adjustment in `architectural_fit` and possibly a small `system-design.md` update. For `new` and `foundational`, expect full content — integration points, patterns, risks — plus accompanying writes to `docs/system-design.md` and possibly `docs/adr/`. For `conflicting`, `escalations` is required.

### Consultation dispatch: append a `consultation-response` record

Schema: [`schemas/scratch/consultation-response.schema.json`](../../../schemas/scratch/consultation-response.schema.json).

**Required fields:** `type`, `req_id`, `ts`, `author`, `in_response_to` (line number of the matching consultation-request), `answer`.

**Optional fields:** `memory_updates` (array of `{path, summary}` describing durable-memory writes that accompanied this consultation; usually empty), `notes`.

### Append-only discipline (both dispatch types)

Read `.scratch/handoff.jsonl` first. Preserve every prior line verbatim. Append your record as the last line, terminated by `\n`. Never edit, reorder, or delete prior records — `supersedes_record_at` is how you correct a prior decision.

### Example Records

`design-block` for a `covered` verdict (most slices on a mature codebase):

```json
{"type":"design-block","req_id":"REQ-XX-099","ts":"2026-05-08T14:00:00Z","author":"system-design-expert","verdict":"covered","architectural_fit":"Cache miss diagnostics fit the existing per-agent rate pattern in internal/report/summary.go (§3.4 of system-design); no new package or pattern needed.","primary_paths":["internal/report/summary.go","internal/report/summary_test.go"]}
```

`design-block` for a `new` verdict (genuinely new design ground):

```json
{"type":"design-block","req_id":"REQ-XX-099","ts":"2026-05-08T14:00:00Z","author":"system-design-expert","verdict":"new","architectural_fit":"Cache miss diagnostics live in the report layer alongside existing per-agent rates; new sub-package internal/report/cachemiss/ introduced to encapsulate the calculation.","primary_paths":["internal/report/cachemiss/cachemiss.go","internal/report/cachemiss/cachemiss_test.go"],"supporting_paths":["internal/cache/measure.go"],"integration_points":["summary report row gains a cache_miss_rate column derived from internal/cache/measure"],"patterns":[{"ref":"internal/report/summary.go:120","description":"existing per-agent rate computation pattern"}],"risks":[{"risk":"divisor zero when cache_eligible_token_count is 0","mitigation":"emit null with insufficient_data flag"}]}
```

`consultation-response`:

```json
{"type":"consultation-response","req_id":"REQ-XX-099","ts":"2026-05-08T15:00:00Z","author":"system-design-expert","in_response_to":42,"answer":"Use the existing rate-computation pattern from internal/report/summary.go:120. The cache_miss case is structurally identical to per-agent rates — same divisor-zero handling, same null-on-insufficient-data convention.","memory_updates":[]}
```

## Documentation Discipline

When updating `docs/system-design.md`, follow the state-vs-history split: the doc captures *current state* only; the *why* lives in ADRs.

| Pattern | Severity | Fix |
|---|---|---|
| "Why" prose in `docs/system-design.md` (paragraphs explaining a decision's rationale) | Critical | Move to a new ADR or extend an existing one; replace with a short rule + ADR back-link |
| Imperative line in `docs/system-design.md` (Do/Don't/Always/Never/Require) without an ADR back-link | High | Add the ADR link inline; if no ADR exists, write one before landing the rule |
| Trade-off discussion in `docs/system-design.md` | High | Move to the ADR's Decision + Consequences sections |
| Resolve domain terms against `docs/ubiquitous-language.md` | — | Use canonical ubiquitous-language terms in `architectural_fit` and `notes`; add new terms to the ubiquitous-language doc when introducing them |

The canonical document-ownership table in `docs/documentation-standards.md` defines the split. `doc-review` enforces the ADR back-link rule on every imperative line.

## Design Principles

Apply these principles when evaluating features:

1. **Security and reliability are emergent** — must be designed in, not retrofitted.
2. **Consistency over novelty** — match existing patterns unless there is a compelling reason.
3. **Explicit dependencies** — every integration point documented.
4. **Layer respect** — features belong in appropriate architectural layers.
5. **Minimal surface** — prefer internal packages.
6. **Understandable systems** — if it cannot be reasoned about, it cannot be secured.
7. **Fail secure** — errors leave the system in a safe state.

## Validation Checklist

Before approving a feature for implementation:

### Architectural Fit
- [ ] Feature aligns with project goals
- [ ] Feature not in Non-Goals or Out of Scope
- [ ] Package placement follows existing `internal/` structure
- [ ] Error handling matches `fmt.Errorf("context: %w", err)` pattern
- [ ] New types follow existing naming conventions
- [ ] No circular dependencies between packages
- [ ] Integration points identified
- [ ] New dependencies from approved sources (see `docs/system-design.md`); ADR required for exceptions

### DDD Alignment

See `docs/ddd-principles.md` for full principles.

- [ ] Value objects are immutable with no framework dependencies
- [ ] Aggregates enforce their own invariants
- [ ] Data mappers are stateless and pure at all boundaries
- [ ] One aggregate per package
- [ ] Dependencies flow inward (infrastructure → service → domain)
- [ ] `make deps-check` passes

### Security by Design
- [ ] Credentials handled per existing patterns (config, not hardcoded)
- [ ] Input validation specified
- [ ] Error messages don't leak sensitive data
- [ ] Logging follows redaction patterns
- [ ] Network operations use TLS

### Reliability by Design
- [ ] Failure modes enumerated
- [ ] Timeouts specified for all blocking operations
- [ ] Resource limits defined (buffers, connections)
- [ ] Graceful shutdown behavior specified
- [ ] Context cancellation propagated

### Understandability
- [ ] Component can be understood in isolation
- [ ] State changes are explicit
- [ ] Interfaces are minimal and typed
- [ ] No implicit dependencies
