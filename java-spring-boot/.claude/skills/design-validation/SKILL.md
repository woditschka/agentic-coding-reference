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

This skill operates inside the **middle loop** of the three-nested-loop pipeline. The `prd-entry` record scopes one slice; you produce a `design-block` record that confirms (or revises) the design for that slice. The inner loop's design-check decision tree may call you back mid-cycle when a `Design gap` appears — that callback is the loop nesting, not rework. See [`docs/agentic-harness.md`](../../../docs/agentic-harness.md) for the loop model.

## Input Contract

The active feature scope arrives as a `type: "prd-entry"` record in `.scratch/handoff.jsonl` (one JSON object per line, append-only). Schema: [`schemas/scratch/prd-entry.schema.json`](../../../schemas/scratch/prd-entry.schema.json).

**Read discipline:**

1. Read `.scratch/handoff.jsonl`. Take the last `type: "prd-entry"` record as the active scope.
2. The pipeline-coordinator validates the record against the schema before dispatching you; you may assume the required fields are present and well-typed. If the record is missing or fails a sanity check (e.g. `req_id` does not match the PRD), append a `design-block` record with `verdict: "escalated"` rather than papering over malformed input.
3. Use `acceptance_criteria`, `file_targets`, and `test_names` from the record verbatim when producing your `design-block` record. Do not re-derive them; that is the rework loop the JSONL handoff exists to break.
4. If a required structural field is missing or contradicts the PRD, the right action is to bounce back via `verdict: "needs_changes"` (or `"escalated"` for unresolvable conflicts), not to fill in guesses.

**Forbidden:** re-reading `docs/prd.md` to reconstruct scope when the prd-entry record is present. The record is the contract.

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

Append one `design-block` record to `.scratch/handoff.jsonl` per dispatch. Schema: [`schemas/scratch/design-block.schema.json`](../../../schemas/scratch/design-block.schema.json).

**Required fields:**

| Field | Type | Notes |
|---|---|---|
| `type` | `"design-block"` | Discriminator. |
| `req_id` | string `^REQ-[A-Z]+-[0-9]{3}$` | Same as the prd-entry being implemented. |
| `ts` | ISO 8601 string | Timestamp at append. |
| `author` | `"system-design-expert"` | Pinned. |
| `verdict` | enum | `approved` (initial design ready), `needs_changes` (PRE/SDE rework needed), `blocked` (cannot proceed), `revised` (design updated after build-failure escalation), `escalated` (human decision needed). |
| `architectural_fit` | string | How the feature integrates with `docs/system-design.md`. |
| `primary_paths` | array of paths | At least one. The starting target set for the implementer. |

**Optional fields:** `supporting_paths`, `integration_points`, `patterns` (each `{ref, description}`), `risks` (each `{risk, mitigation}`), `escalations` (required when `verdict == "escalated"`), `supersedes_record_at` (line number of the prior design-block this revision supersedes; required when `verdict == "revised"`), `notes`.

**Append-only discipline:** Read `.scratch/handoff.jsonl` first. Preserve every prior line verbatim. Append your record as the last line, terminated by `\n`. Never edit, reorder, or delete prior records — `supersedes_record_at` is how you correct a prior decision.

### Example Record

```json
{"type":"design-block","req_id":"REQ-XX-099","ts":"2026-05-08T14:00:00Z","author":"system-design-expert","verdict":"approved","architectural_fit":"Cache miss diagnostics live in the report module alongside existing per-component rates; no new module, extends SummaryReport.","primary_paths":["src/main/java/com/example/reference/report/SummaryReport.java","src/test/java/com/example/reference/report/SummaryReportTest.java"],"integration_points":["summary report row gains a cacheMissRate column derived from CacheMeasure"],"patterns":[{"ref":"src/main/java/com/example/reference/report/SummaryReport.java:120","description":"existing per-component rate computation pattern"}],"risks":[{"risk":"divisor zero when cacheEligibleTokenCount is 0","mitigation":"emit null with insufficientData flag"}]}
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

1. **Pipeline integrity** — the processing pipeline is the backbone; features must fit within it.
2. **Consistency over novelty** — match existing patterns unless there is a compelling reason.
3. **Explicit dependencies** — every integration point documented.
4. **Granular failure** — errors should be as granular as possible.
5. **Records for data, components for behavior** — keep the data model clean.
6. **Test-data driven** — every input handling change must work against test data.

## Validation Checklist

Before approving a feature for implementation:

### Architectural Fit
- [ ] Feature aligns with project goals
- [ ] Feature not in Non-Goals or Out of Scope
- [ ] Package placement follows existing module structure (see `docs/system-design.md`)
- [ ] New types use Java records for data, Spring components for services
- [ ] Error handling follows system-design.md patterns
- [ ] No circular dependencies between modules
- [ ] No access to another module's `internal/` sub-packages
- [ ] Pipeline step ordering preserved
- [ ] Integration points identified
- [ ] New dependencies justified and from approved sources (see `docs/system-design.md`); ADR required for exceptions

### DDD and Modulith Alignment

See `docs/ddd-principles.md` for full principles.

- [ ] Value objects are immutable records with no framework annotations
- [ ] Aggregates enforce their own invariants
- [ ] Data mappers are stateless and pure at all boundaries
- [ ] New module has public API at package root, internals in sub-packages
- [ ] Cross-module orchestration uses module APIs, not internal types
- [ ] Modularity verification test passes (`ModularityTests.java`)

### Security by Design
- [ ] Credentials handled per existing patterns (config, not hardcoded)
- [ ] Input validation specified
- [ ] Error messages don't leak sensitive data
- [ ] Logging follows redaction patterns
- [ ] Network operations use TLS

### Reliability by Design

**Robustness:**
- [ ] Failure modes enumerated
- [ ] Failure in one item does not prevent processing others
- [ ] Corrupted data/state files handled gracefully
- [ ] Unparseable inputs handled (logged, not silently dropped)
- [ ] I/O errors caught at appropriate granularity
- [ ] Granular error handling (per-item, not per-batch where possible)
- [ ] Resource limits defined (buffers, connections)
- [ ] Graceful shutdown behavior specified (if applicable)

**Idempotency:**
- [ ] Running twice with no changes produces identical output
- [ ] State and output files consistent after every run
- [ ] No partial writes leave the system in a broken state

### Understandability

**Decomposition:**
- [ ] Feature maps to a clear package and class
- [ ] Single responsibility: one class does one thing
- [ ] No hidden dependencies between packages
- [ ] Component can be understood in isolation

**Clear Interfaces:**
- [ ] Methods accept typed parameters (no raw `Object` or `Map<String, Object>`)
- [ ] Return types express failure clearly (`Optional` for absence, exceptions for errors)
- [ ] Records used for data transfer between steps

**Predictable Behavior:**
- [ ] Error handling matches the table in system-design.md
- [ ] State changes are explicit
- [ ] Side effects limited to defined output locations
- [ ] No implicit dependencies

### Data Model Integrity
- [ ] New records follow naming conventions
- [ ] State file schema remains backward-compatible (or migration path defined)
- [ ] JSON serialization round-trips correctly
- [ ] UTF-8 encoding maintained throughout

### Testability
- [ ] Unit-testable without filesystem dependencies
- [ ] Integration tests can use test data
- [ ] Edge cases covered by parameterized tests
