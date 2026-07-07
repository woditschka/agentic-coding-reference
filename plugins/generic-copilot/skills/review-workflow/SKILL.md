---
name: review-workflow
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
  - docs/security-principles.md
metadata:
  version: "1.0"
  author: team
---

## Review Phase

After the feature-implementer appends a `build-pass` record to `.scratch/handoff.jsonl`, invoke all reviewers in the roster in parallel. The roster is the mandatory four-reviewer floor below plus any `extra_reviewers` declared in `scripts/layout.toml [harness]`:

| Reviewer | `author` value | Focus |
|---|---|---|
| code-quality-reviewer | `"code-quality-reviewer"` | Readability, project style guide |
| test-reviewer | `"test-reviewer"` | Test pyramid, coverage, edge cases |
| security-reviewer | `"security-reviewer"` | OWASP, vulnerabilities, supply chain |
| doc-reviewer | `"doc-reviewer"` | Documentation coherence, structure |

The floor cannot be dropped; a project only adds reviewers. A declared extra reviewer is named `*-reviewer` and focuses on the dimension it is built for. It joins the gate exactly like a floor reviewer: its `review-feedback` record must read `approved` before the feature is complete. Each reviewer appends one `review-feedback` record. Schema: [`schemas/scratch/review-feedback.schema.json`](../../../schemas/scratch/review-feedback.schema.json).

## Reviewer Read-Set (Fresh Eyes)

A reviewer judges the **change set** under review against **long-term memory** (`docs/` — PRD, system-design, ubiquitous-language, ADRs, and the principles briefs), reading the wider project on demand. It does not take the implementer's plan (`.scratch/implementation-plan.md`) as review input. It reads `.scratch/handoff.jsonl` only to anchor its dispatch — the `build-pass` line it responds to — not to mine the design triage or the implementer's reasoning.

The reviewer is the first proxy for every future reader who will see this code with only the durable docs and the diff — never the author's plan. Reading the implementer's narrative forfeits exactly the cold read that review exists to perform.

Obtain the change set through `scripts/changeset.sh` — the single definition the change-grader also resolves, so a reviewer's view and the grader's row agree. `scripts/changeset.sh --name-only` lists the changed files (the review scope); `scripts/changeset.sh` emits the unified diff (the hunks). Read full files from the working tree on demand for context the diff omits.

## Output Protocol (Reviewers)

Your sole deliverable is the appended `review-feedback` record. The pipeline cannot proceed without it.

1. **Read** `.scratch/handoff.jsonl` first. If the file does not exist, the implementer has not signalled gate-pass — abort and report the missing precondition.
2. **Append one line** to `.scratch/handoff.jsonl`: a single JSON object conforming to the `review-feedback` schema. Feed it to `append` through a quoted heredoc placed **directly on the `python3` command**, per the `handoff-append` skill:

   ```bash
   python3 scripts/handoff.py append review-feedback <<'EOF'
   {"type":"review-feedback","req_id":"<req-id>","ts":"<iso-8601>","author":"<your-reviewer-name>","verdict":"<approved|changes_requested|blocked>","findings":[…]}
   EOF
   ```

   Required fields: `type` (`"review-feedback"`), `req_id`, `ts`, `author` (your reviewer name), `verdict` (`approved` | `changes_requested` | `blocked`), `findings` (array, possibly empty when `verdict: "approved"`).
3. Each finding requires `tag`, `location`, `description`. Add `fix` for `tag: "autofix"`. Add `clarify_target` for `tag: "clarify"`. Severity is optional (`critical` | `fixable`).
4. **Append-only is non-negotiable** — never edit, reorder, or delete prior records.
5. **Verify**: `append` prints the new record's line number on success; a non-zero exit means the record was rejected — fix the record, never the file.
6. Your reply to the caller MUST be exactly one line: `Appended review-feedback (<verdict>) for <req_id>`.
7. Do NOT include review content, summaries, or analysis in your reply. The caller reads the record.

**Why:** when review content lands in the reply instead of the file, the dispatcher cannot route fixes, artifact-owner agents cannot read findings, and the audit trail is lost. Stopping before the append forces the user to re-run the review — this is a recurring reviewer failure mode.

### Example Record

```json
{"type":"review-feedback","req_id":"REQ-XX-099","ts":"2026-05-08T16:30:00Z","author":"code-quality-reviewer","verdict":"changes_requested","findings":[{"tag":"autofix","location":"report/summary:142","description":"Loop variable `r` shadows an outer binding of the same name.","fix":"Rename loop variable to `row`."},{"tag":"blocked","location":"report/summary:160","description":"Possible divide-by-zero when the denominator (cache-eligible token count) is 0.","severity":"critical"}],"approved_aspects":["Test naming follows conventions","Errors wrapped with context"]}
```

## Feedback Tags

| Tag | Meaning | Action |
|---|---|---|
| `autofix` | Clear fix, no decision needed | Route to artifact owner |
| `blocked` | Critical issue, must fix before merge | Route to artifact owner; escalate if unclear |
| `escalate` | Needs human decision | Append to `.scratch/escalations.md` |
| `clarify` (with `clarify_target`) | Requirement, design, or review question | Route to the named agent |
| `truncation` | Reviewer reached its planned checkpoint mid-review | Nothing to fix — the record's `blocked` verdict routes the partial findings to the implementer; the re-run cycle re-invokes the reviewer for the unreviewed surface |

Choose the tag by what the finding needs next, not by its severity. `autofix` when the fix is mechanical and decision-free; `blocked` when merging would ship a defect; `escalate` when only a human can decide; `clarify` when the finding is really a question for another agent. The tag is a routing decision — pick the one that moves the finding to whoever can resolve it. `truncation` is reserved for the partial-record checkpoint below — a progress marker, not an escalation; it needs no human and never halts the pipeline.

## Quality-Bar Clause Mapping (`bar_clause` field)

The nine clauses below are the conjunctive "done" definition for any change. The clauses themselves are defined in [`tdd-principles.md`](../tdd-workflow/tdd-principles.md) (§ Scope Discipline, § Code That Reads Cold, § Operationally Honest, § Secure by Design), with mechanics in [`docs/testing-principles.md`](../../../docs/testing-principles.md), [`docs/architecture-principles.md`](../../../docs/architecture-principles.md), and [`docs/security-principles.md`](../../../docs/security-principles.md). This skill owns the *canonical slug list* — the schema enum on `review-feedback.bar_clause` references back to this table.

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
| `secure-by-design` | Unvalidated input crossing a trust boundary, secrets reaching logs/errors/URLs, excess privilege, error paths that fail open | security | `tdd-principles` § Secure by Design; `security-principles` |

Procedural findings (lint, typo, missing language tag on a fence) carry `tag` but no `bar_clause` — they are mechanical and do not target a clause. A single finding may carry both `tag` and `bar_clause` when both apply: a `blocked` finding for a missing rollback note also carries `bar_clause: "operationally-honest"`.

## Artifact Ownership

Review feedback targets the artifact, not a fixed agent. Route fixes to the owning agent:

| Artifact | Owner Agent | Autofix Exception |
|---|---|---|
| `docs/prd.md` | product-requirements-expert | — |
| `docs/system-design.md`, `docs/adr/*.md` | system-design-expert | Root applies `tag: "autofix"` per `handoff-routing` § Root-Applied Autofix on Design Docs; all other tags route to system-design-expert |
| Production source (`prod_roots` in `scripts/layout.toml`) | feature-implementer | — |
| Test source | feature-implementer | — |
| Resource/config files, templates | feature-implementer | — |

Do not bundle doc fixes into a feature-implementer call. Do not send code fixes to doc agents.

## Root-Applied Autofix Eligibility

Root may apply `tag: "autofix"` findings on `docs/system-design.md` and `docs/adr/*.md` directly, without redispatching system-design-expert — the apply procedure, its bounds, and the `design-doc-autofix` audit record live in the `handoff-routing` skill § Root-Applied Autofix on Design Docs. What the reviewer owns is eligibility: the rules live in the `document-writing` skill's stack overlay, `review-checks.md` § Autofix on Design-Doc Paths. Doc-reviewer never tags a finding `autofix` on a design-doc path unless every condition there holds. The quality bar lives in the `blocked` and `clarify` (with `clarify_target: "system-design-expert"`) paths, which still route to system-design-expert.

## Issue Classification

| Checklist Category | Default Severity | Tag |
|--------------------|-----------------|-----|
| Cross-document coherence | Critical | `blocked` |
| PRD boundary violations (source code, signatures, internal references) | Critical | `blocked` |
| PRD carrying mechanism (flag/exit-code tables, output layouts) or per-requirement scaffolding (`Input`/`Output`/`Constraints`/`Depends On`) | Critical | `blocked` |
| system-design.md mirroring source — field/parameter/key enumeration in a table OR in prose | Critical | `blocked` |
| A document granting itself a reviewer-check exemption ("reviewers may skip X here") | Critical | `blocked` |
| Security vulnerabilities (CRITICAL/HIGH per `security-review` skill) | Critical | `blocked` |
| Structural issues (missing anchors, broken links) | Fixable | `autofix` |
| Writing standards | Fixable | `autofix` |

## Processing Reviews

After all reviewers complete — and after root's Reviewer Stall Check (`handoff-routing` skill § Reviewer Stall Check) confirms every roster record is present:

1. feature-implementer reads all `review-feedback` records in the roster (latest per reviewer for the active `req_id`).
2. `tag: "autofix"` findings: fix immediately using the `fix` field.
3. `tag: "blocked"` findings: fix immediately; escalate if fix is unclear.
4. `tag: "escalate"` findings: append the description to `.scratch/escalations.md`.
5. `tag: "clarify"` findings: request clarification from the agent named in `clarify_target`.
6. `tag: "truncation"` findings: nothing to fix — the finding marks unreviewed surface; step 9's re-run re-invokes the reviewer for it.
7. (No consolidated summary file needed; the roster's `review-feedback` records are the canonical record.)
8. If every roster reviewer's `verdict` is `"approved"`, feature is complete.
9. If any `verdict` is `"changes_requested"` or `"blocked"`, re-run the quality gate (append fresh `build-failure`/`build-pass` records) and re-invoke reviewers.

## Partial-Artifact Contract

Reviewers carry the verifier half of the partial-artifact contract. Two halves: a Scoping Pre-Check before the first tool call, and a planned checkpoint named in that pre-check.

### Scoping Pre-Check (reviewer)

Before the first tool call, run the three-step pre-check defined in the `tdd-workflow` skill § Scoping Pre-Check, adapted to the review surface:

1. Read the latest `build-pass` record for the active `req_id`, then the change set under review — `scripts/changeset.sh --name-only` for the changed files, `scripts/changeset.sh` for their diff (§ Reviewer Read-Set). Do not read the implementer's working memory.
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
- One additional `truncation` finding naming the checkpoint:

```json
{"tag":"truncation","location":"<review surface, e.g. internal/report/>","description":"Reviewer reached planned checkpoint with <unreviewed surface> not yet reviewed. Findings above cover <reviewed surface> only."}
```

The downstream loop (feature-implementer processing findings) sees a real record with inspectable partial progress instead of a missing reviewer. The `truncation` tag is a progress marker, not an escalation: it never touches `.scratch/escalations.md`. § Blocking in `handoff-routing` does not apply to it; that halt is for `escalate` findings — human decisions.

The contract complement to an `approved` `review-feedback` is this `blocked` + truncation finding. Both are first-class outputs of a dispatch; neither is a failure mode. The review-feedback routing (`handoff-routing` Gate 4) already handles `blocked` verdicts by dispatching the feature-implementer for findings processing — no new routing is needed.
