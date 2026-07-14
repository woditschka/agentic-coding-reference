---
name: design-validation
description: >-
  Architectural validation checklist for feature approval.
  Load when validating that features fit into the existing architecture.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/architecture-principles.md
  - docs/security-principles.md
  - docs/system-design.md
  - docs/prd.md
  - docs/ubiquitous-language.md
metadata:
  version: "1.0"
  author: team
---

## Pipeline Position

This skill operates inside the **middle loop** of the four-nested-loop pipeline (inner / middle / outer / architectural). See [`agentic-harness.md`](../handoff-routing/agentic-harness.md) for the loop model.

The system-design-expert operates in two demand-driven modes, both covered by this skill:

- **Triage** — runs on every `prd-entry`. Read durable memory, decide one of six verdicts (`covered`, `minor`, `new`, `foundational`, `conflicting`, `refactor-first`), append a `design-block` record.
- **Consultation** — runs on demand when the implementer appends a `consultation-request`. Read the question and durable memory, answer focused, optionally record memory, append a `consultation-response` record. The router routes control back to the requester after the response.

Most thoughts stay in the head — the cross-feature mental model. The durable memory captures only the load-bearing parts.

## Input Contract

You are dispatched in one of two situations, distinguished by which record is the latest entry in `.scratch/handoff.jsonl`:

- **Triage dispatch.** Latest record is a `type: "prd-entry"`. Schema: [`schemas/scratch/prd-entry.schema.json`](../../../schemas/scratch/prd-entry.schema.json). This is the active slice scope.
- **Consultation dispatch.** Latest record is a `type: "consultation-request"` targeting `system-design-expert`. Schema: [`schemas/scratch/consultation-request.schema.json`](../../../schemas/scratch/consultation-request.schema.json). The active scope is the focused question; the originating slice is the most recent `prd-entry` whose `req_id` matches.

**Read discipline:**

1. Read `.scratch/handoff.jsonl`. Identify which dispatch type you're in.
2. The routing gate validates the inbound record against the schema before dispatching you; you may assume the required fields are present and well-typed. If a sanity check fails (e.g. `req_id` does not match the PRD), append a `design-block` record with `verdict: "conflicting"` (for triage) or a `consultation-response` flagging the inconsistency (for consultation) rather than papering over malformed input.
3. For triage: use `acceptance_criteria`, `file_targets`, and `test_names` from the prd-entry verbatim. Do not re-derive them; the JSONL handoff exists to break that rework loop.
4. For consultation: read the `question`, `context`, and `stop_state` fields. Answer narrow. Broad open-ended questions belong in a triage, not a consultation.

**Forbidden:** re-reading `docs/prd.md` to reconstruct scope when the prd-entry record is present. The record is the contract.

## Triage Mode

When dispatched on a `prd-entry`, your task is to decide one of six verdicts and append a `design-block` record. Read durable memory first, then judge.

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
| `foundational` | Five-signal check tripped on a concern the slice touches. | Append a `consultation-request` targeting `human` with the unrecoverable foundational question(s); root interviews the user (`agentic-harness.md` § Conversations Stay in Root) and the response re-dispatches you. Then write `system-design.md`, possibly ADRs, possibly seed `docs/ubiquitous-language.md`; then settle on the slice's own verdict (`new`/`minor`/`covered`) and write the `design-block` reflecting it. The single `design-block` record carries `verdict: "foundational"` and references the durable-memory writes in `notes`. |
| `conflicting` | The slice cannot be honored without contradicting current design or an ADR. | `design-block` with `verdict: "conflicting"` and an `escalations` array naming the contradiction. `route` blocks (`design-conflict`) and surfaces the escalations to the user; typical remediation is a non-goal ADR or a PRD revision. |
| `refactor-first` | An independently-meaningful refactor must land before this slice can be implemented (existing abstraction is wrong; forcing the slice through would ship a non-orthogonal extension or fold refactor + feature into one cycle). The refactor must have a one-sentence behavioural justification — not for incidental cleanup the implementer can fold into TDD Refactor steps. | `design-block` with `verdict: "refactor-first"` PLUS a sibling refactor `prd-entry` (new `req_id`, scoped to the refactor only). The refactor runs first (`route` escalates the ordering); `refactor-resume` re-triages the original via a new `design-block` with `supersedes_record_at` after the refactor completes. |

Match dialogue depth to verdict. `covered`/`minor` triggers no user dialogue. `new` may surface a single trade-off question. `foundational` is a multi-question interview about unrecoverable choices, run by root between your two dispatches.

Pick the verdict by the question it answers, not by the row whose wording is closest. `covered`: does durable memory already handle this unchanged? `minor`: does one small adjustment suffice? `new`: is this fresh ground worth recording? `foundational`: is a project-level decision missing that the slice needs? `conflicting`: does honoring the slice contradict a committed decision? `refactor-first`: must the ground be reshaped before the slice can land cleanly? A slice that sits between two verdicts belongs to whichever question it truly answers — making that judgment is the point of having six verdicts instead of a checklist.

### Foundational triage: vocabulary extraction on adoption

When the project being triaged has substantial existing docs and source code (i.e., it's being adopted by the harness rather than greenfield) and `docs/ubiquitous-language.md` is empty, extract a candidate vocabulary before appending the `consultation-request`:

1. Scan `docs/` for recurring domain terms.
2. Scan source code for domain types — value objects, aggregate roots, repositories — and the entity names they encode.
3. Identify variations and aliases (same concept named different ways across files).
4. Propose a candidate term list with one-line definitions and `Avoid:` lines for the alias variants you found.
5. Include the candidate list in the `consultation-request` with the foundational questions; root presents it for confirmation, refinement, and additions.
6. On the re-dispatch, write the confirmed set to `docs/ubiquitous-language.md` (this is the one path where you write to that file — usually owned by product-requirements-expert; the seeding case is the exception).

On a fresh project (no substantial code yet), the vocabulary seed is whatever the user names during root's interview — much shorter.

## Consultation Mode

When dispatched on a `consultation-request`, your task is to answer the specific question and append a `consultation-response`. The router returns control to the requester after your response.

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

Before working on the active prd-entry, audit every `type: "design-doc-autofix"` record in `.scratch/handoff.jsonl` whose `ts` is later than your most recent `type: "design-block"` record (or any such record if you have not yet been dispatched for the active `req_id`). `handoff.py audit-autofix` (the `code-quality-gate` skill's autofix audit) has already re-checked the allowlist bounds mechanically; your job is the judgement check.

For each record, decide whether the change is legitimately mechanical:

- **Legitimate.** Writing-standards or structural fix that doesn't smuggle in a semantic shift. Common shape: sentence shortened, anchor added, code-fence language tag added.
- **Illegitimate.** The change reads as mechanical but moves architectural meaning — e.g. a "shortened sentence" drops a constraint, a "broken link fix" repoints to a different anchor that means something different, a "writing-standards" rewrite changes a definitional claim. These are substantive changes that escaped via mis-tagging.

For every illegitimate record:

1. Append a finding to your forthcoming `design-block` record's `notes` (or `risks` if you want it surfaced more loudly): `"autofix-rejected: <handoff.jsonl line N>: <reason>"`.
2. Recommend a corrective edit in the same `design-block` (you have write access to design docs; apply the correction yourself).
3. `handoff.py audit-autofix` re-checks bounds on every gate run; repeat offenders surface as `design-doc-autofix` audit failures and bounce back to system-design-expert for revert-or-redo.

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
| `ts` | ISO 8601 string | Stamped by `append`; never composed by the author. |
| `author` | `"system-design-expert"` | Pinned. |
| `verdict` | enum | `covered`, `minor`, `new`, `foundational`, `conflicting`, `refactor-first`. See the Verdict criteria table above. |
| `architectural_fit` | string | How the slice integrates with current durable memory. References `docs/system-design.md` sections when relevant. |
| `primary_paths` | array of paths | At least one. The starting target set for the implementer. |

**Optional fields:** `supporting_paths`, `integration_points`, `patterns` (each `{ref, description}`), `risks` (each `{risk, mitigation}`), `escalations` (required when `verdict == "conflicting"`), `supersedes_record_at` (line number of the prior design-block this revision supersedes, when revising after a build-failure), `notes`.

**Field weight by verdict.** For `covered`, `architectural_fit` is a one-line pointer to existing sections and most optional fields are empty. For `minor`, expect a short adjustment in `architectural_fit` and possibly a small `system-design.md` update. For `new` and `foundational`, expect full content — integration points, patterns, risks — plus accompanying writes to `docs/system-design.md` and possibly `docs/adr/`. For `conflicting`, `escalations` is required. For `refactor-first`, `architectural_fit` names the abstraction mismatch and the refactor's one-sentence behavioural justification, and the dispatch also appends a sibling refactor `prd-entry` record (the refactor runs first; the original slice resumes via a re-triage `design-block` with `supersedes_record_at` after the refactor completes).

### Consultation dispatch: append a `consultation-response` record

Schema: [`schemas/scratch/consultation-response.schema.json`](../../../schemas/scratch/consultation-response.schema.json).

**Required fields:** `type`, `req_id`, `author`, `in_response_to` (line number of the matching consultation-request), `answer`.

**Optional fields:** `memory_updates` (array of `{path, summary}` describing durable-memory writes that accompanied this consultation; usually empty), `notes`.

### Append-only discipline (both dispatch types)

Append your record via `python3 scripts/handoff.py append <type>` — it validates against the schema and writes canonically (`handoff-append` skill). Never edit, reorder, or delete prior records — `supersedes_record_at` is how you correct a prior decision.

### Example Records

`design-block` for a `covered` verdict (most slices on a mature codebase):

```json
{"type":"design-block","req_id":"REQ-XX-099","author":"system-design-expert","verdict":"covered","architectural_fit":"Cache miss diagnostics fit the existing per-agent rate pattern in report/summary (§3.4 of system-design); no new module or pattern needed.","primary_paths":["report/summary","report/summary.test"]}
```

`design-block` for a `new` verdict (genuinely new design ground):

```json
{"type":"design-block","req_id":"REQ-XX-099","author":"system-design-expert","verdict":"new","architectural_fit":"Cache miss diagnostics live in the report layer alongside existing per-agent rates; new sub-module report/cachemiss/ introduced to encapsulate the calculation.","primary_paths":["report/cachemiss/cachemiss","report/cachemiss/cachemiss.test"],"supporting_paths":["cache/measure"],"integration_points":["summary report row gains a cache_miss_rate column derived from cache/measure"],"patterns":[{"ref":"report/summary:120","description":"existing per-agent rate computation pattern"}],"risks":[{"risk":"divisor zero when cache_eligible_token_count is 0","mitigation":"emit null with insufficient_data flag"}]}
```

`consultation-response`:

```json
{"type":"consultation-response","req_id":"REQ-XX-099","author":"system-design-expert","in_response_to":42,"answer":"Use the existing rate-computation pattern from report/summary:120. The cache_miss case is structurally identical to per-agent rates — same divisor-zero handling, same null-on-insufficient-data convention.","memory_updates":[]}
```

## Documentation Discipline

When updating `docs/system-design.md`, follow the state-vs-history split: the doc captures *current state* only; the *why* lives in ADRs.

| Pattern | Severity | Fix |
|---|---|---|
| "Why" prose in `docs/system-design.md` (paragraphs explaining a decision's rationale) | Critical | Move to a new ADR or extend an existing one; replace with a short rule + ADR back-link |
| Imperative line in `docs/system-design.md` (Do/Don't/Always/Never/Require) without an ADR back-link | High | Add the ADR link inline; if no ADR exists, write one before landing the rule |
| Trade-off discussion in `docs/system-design.md` | High | Move to the ADR's Decision + Consequences sections |
| Resolve domain terms against `docs/ubiquitous-language.md` | — | Use canonical ubiquitous-language terms in `architectural_fit` and `notes`; add new terms to the ubiquitous-language doc when introducing them |

The split is the kernel state-vs-history property: `docs/system-design.md` carries current state; `docs/adr/` carries the path to each decision. `document-writing` enforces the ADR back-link rule on every imperative line.

## Design Principles

Apply the principles in `docs/architecture-principles.md` § Design Principles when evaluating features. The brief is project-owned: enforce the project's principles as written, not a remembered list. If the brief contradicts itself or the codebase, raise a brief-defect finding instead of silently picking a side.

## Validation Checklist

Before approving a feature for implementation:

### Architectural Fit
- [ ] Feature aligns with project goals
- [ ] Feature not declined in Non-Goals or retired in Superseded
- [ ] Module placement follows the existing structure (the production roots declared in `scripts/layout.toml`)
- [ ] Error handling follows the error-flow rule in `docs/architecture-principles.md`
- [ ] New types follow existing naming conventions
- [ ] No circular dependencies between modules
- [ ] Integration points identified
- [ ] New dependencies from approved sources (see `docs/system-design.md`); ADR required for exceptions

### DDD Alignment

The closed-kernel checks below hold in every project. Every other tactical choice conforms to `docs/architecture-principles.md` as written, not a remembered default — see that brief for the full pattern catalog.

- [ ] Value objects immutable, equal by value; invariants enforced at construction
- [ ] Aggregates are the consistency boundary: entered only through the root, referenced by identity
- [ ] Domain core free of infrastructure logic; business logic in the model, not orchestration
- [ ] Dependencies flow inward (infrastructure → service → domain)
- [ ] Anti-corruption guards every boundary the project does not control; an owned, closely-tracked model may be mapped directly
- [ ] All other tactical choices — mapping, persistence, ACL, annotation, aggregate granularity, naming — conform to `docs/architecture-principles.md` as written

### Security by Design

See `docs/security-principles.md` — the project's trust-boundary map (§ Trust Boundaries) and the stack's high-bar defaults (its Realization table). Validate the design against the brief, not a remembered list:

- [ ] Every trust boundary the slice introduces or crosses is identified, with validation placed at it
- [ ] Secrets stay out of logs, errors, URLs, and process arguments
- [ ] The design grants least privilege and fails closed on error
- [ ] The vulnerability classes the brief flags for this stack are addressed where the slice touches them

### Reliability by Design
- [ ] Failure modes enumerated
- [ ] Timeouts specified for all blocking operations
- [ ] Resource limits defined (buffers, connections)
- [ ] Graceful shutdown / cancellation of long-running work specified

### Understandability
- [ ] Component can be understood in isolation
- [ ] State changes are explicit
- [ ] Interfaces are minimal and typed
- [ ] No implicit dependencies
