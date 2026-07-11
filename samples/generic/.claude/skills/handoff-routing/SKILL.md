---
name: handoff-routing
description: >-
  Pipeline routing rules and handoff conditions between specialist agents:
  gates, recovery, and the root-applied procedures. Load when coordinating
  feature delivery, checking pipeline state, or determining which agent to
  invoke next. The writer side of the log lives in handoff-append.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
metadata:
  version: "2.1"
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
| Code review request | All reviewers in the roster | Yes — parallel invocation |

**Skip agents for:** git operations, answering questions, running one-off commands, summarizing an already-completed change. Formal review of a completed change routes to the reviewers in the roster per the table above.

## Handoff Conditions

All transitions are gated on the latest record per `(req_id, type)` in `.scratch/handoff.jsonl`. The Handoff Conditions table is executable: `python3 scripts/handoff.py route` evaluates it and prints one JSON decision. The table itself, the gates' field checks, and the recovery steps live in [`route-spec.md`](route-spec.md) — the normative spec `route` executes and `scripts/test_handoff.py` pins rule by rule. No consumer re-derives it: root runs `route` after each dispatch returns and follows its decision.

Three decisions exist. `dispatch` names the next agent(s), the matched rule, and the prompt context. A failed gate is a `dispatch` of the upstream agent carrying the exact errors — the bounce, expressed as the re-dispatch it is. Root assembles each recovery dispatch's prompt from the section its rule maps to: `reviewer-stall-retry` from § Reviewer Stall Check; `build-retry` from `route-spec.md` § Build-Failure Recovery; `truncation-continue` from `route-spec.md` § Truncation Recovery, read on demand. `blocked` always halts for a human: a dirty log, a `conflicting` verdict, a stalled reviewer, feature-complete. `escalate` marks a state the table does not decide; the `pipeline-coordinator` is dispatched only on `escalate` and for untriaged fresh-intake classification. Route is fail-closed: it never repairs a log and never guesses past a failed check. A `process-findings` decision with `halt_after: true` carries an escalate finding — root halts after that dispatch per § Blocking.

The `escalate` arm covers the judgment states: no active slice, `refactor-first` sibling ordering, truncation of an agent with no recovery row, an autofix-only findings round (`autofix-only-round`), and any state matching no table row. Both `refactor-first` log shapes escalate; `refactor-resume` then re-triages the original deterministically. A `no-active-slice` escalate on a pick the `next` skill already triaged is pre-resolved: root dispatches `product-requirements-expert` directly, skipping the coordinator.

## Validation Gates

Each transition validates the inbound record(s) against a schema before dispatching the next specialist; malformed or missing records bounce back to the upstream agent without consuming a downstream dispatch. The gates are structural — required fields, types, patterns — and every check catches deterministically. `route` enforces them; the per-gate field checks are `route-spec.md` § Validation Gates. Content quality (are the acceptance criteria *good*?) is the consuming agent's judgement; cross-record consistency beyond `req_id` linkage is a consumer finding, not a gate check.

| Gate | Transition | Record | Schema |
|---|---|---|---|
| 1 | product-requirements-expert → system-design-expert | `prd-entry` | [`prd-entry.schema.json`](../../../schemas/scratch/prd-entry.schema.json) |
| 2 | system-design-expert → implementer | `design-block` | [`design-block.schema.json`](../../../schemas/scratch/design-block.schema.json) |
| 2b | consultation roundtrip (either direction) | `consultation-request` / `consultation-response` | [`consultation-request.schema.json`](../../../schemas/scratch/consultation-request.schema.json), [`consultation-response.schema.json`](../../../schemas/scratch/consultation-response.schema.json) |
| 3 | implementer → reviewers | `build-pass` | [`build-pass.schema.json`](../../../schemas/scratch/build-pass.schema.json) |
| 5 | build-pass → reviewers (roster resolution) | `review-plan` | [`review-plan.schema.json`](../../../schemas/scratch/review-plan.schema.json) |
| 4 | reviewers → next step | `review-feedback`, one per pass-roster reviewer | [`review-feedback.schema.json`](../../../schemas/scratch/review-feedback.schema.json) |

Gate 2b routes a `consultation-response` **back to the requesting specialist**, never forward (§ Mid-Implementation Consultation). Gate 5 resolves the pass roster from the `review-plan` the implementer appends at gate-pass. A `low`/`high` plan gates on its roster; a `gray` plan dispatches the `review-planner` to resolve it; a missing or invalid plan fails closed to the full battery (`route-spec.md` § Gate 5). Gate 4 then waits on that resolved roster — the four-reviewer floor plus declared extras is the default and the fail-closed fallback, defined in `review-workflow` § Review Phase. The feature is complete when every pass-roster reviewer is `approved` and every reviewer ever dispatched for the slice holds a latest `approved`; the `change-grader` is then dispatched (terminal, advisory; skipped when `layout.toml [harness] auto_grade = false`). On any `changes_requested` or `blocked`, findings split by artifact owner (`review-workflow` § Artifact Ownership) — except design-doc autofixes, which root applies per § Root-Applied Autofix on Design Docs. An escalate-tagged finding halts per § Blocking.

### Common Procedure

1. **Discover.** Run `Glob .scratch/**/*` to enumerate state files. Then `Read .scratch/handoff.jsonl` only if it appears in the Glob result. Do not `Read` directories.
2. **Gate.** If `handoff.jsonl` is missing or empty when a record is required, the gate fails — route back to the upstream agent.
3. **Filter.** Records by `req_id` and `type`. The **latest** record for each `(req_id, type)` is the active state.
4. **Check.** Required fields, types, and pattern constraints per the schema.
5. **Decide.** If every check passes: dispatch the next agent. If any check fails: bounce upstream — `route` emits a dispatch of the producing agent carrying the errors; the coordinator names the failed check in a `Blocked` recommendation.

## Blocking

If any gate fails, if a `design-block` record carries `verdict: "conflicting"`, or if a `review-feedback` record carries a `tag: "escalate"` finding, stop the pipeline and resolve before continuing. For an escalate finding, the halt follows the findings-processing dispatch that records the entry in `.scratch/escalations.md` (Gate 4). On an `approved` verdict no findings-processing runs — root appends the entry before halting. `route` enforces the escalate halt twice: `process-findings` carries `halt_after: true`, and `escalate-finding-halt` blocks re-review until a reviewer record follows the human's decision.

## Build-Failure Recovery

A failed quality gate (build error, test failure, format/lint failure) ends the implementer dispatch with a `build-failure` record carrying the error output and retry count. Schema: [`schemas/scratch/build-failure.schema.json`](../../../schemas/scratch/build-failure.schema.json). `route` executes the recovery deterministically; `route-spec.md` § Build-Failure Recovery is the normative definition. The shape:

- An `abort_reason` short-circuits the retry counter: `wrong-shape-slice` → product-requirements-expert for re-split; `design-mismatch` (also a failed autofix audit) → system-design-expert for re-triage; `prerequisite-missing` → halt for the human. The record shape and trigger live in `tdd-workflow` § Wrong-Shape Slice Abort.
- Otherwise `retry < 3` re-dispatches the implementer with the error trail; `retry == 3` re-triages via system-design-expert, whose superseding `design-block` resets the counter. `build-failure` records count only after the latest `design-block`; `python3 scripts/handoff.py next-retry --req-id <id>` implements the rule.

## Truncation Recovery

A feature-implementer dispatch that ends without a `build-pass` or `build-failure` for the active `req_id` truncated before the quality gate. Truncation alone does **not** mean the slice is over-scoped: the Scoping Pre-Check re-scopes a multi-behavior slice *before* dispatch. A slice that reaches dispatch and then truncates is presumed correctly sized and simply long. **The default recovery is to continue the same slice** — up to 3 consecutive truncations, then re-triage via system-design-expert (non-convergence). Re-split is reserved for the Pre-Check's over-size branch and for non-convergence — and even there it is one outcome, not the first response. `route` executes the steps; `route-spec.md` § Truncation Recovery is the normative definition. It also defines the two partial-record paths (`build-failure` with `partial: true`; `review-feedback` carrying a `truncation` finding), which route through existing recovery instead.

### Dispatch Truncation Detection

Every dispatched project-defined agent except `pipeline-coordinator` and the terminal `change-grader` appends a `dispatch-start` record as its first tool call. Schema: [`schemas/scratch/dispatch-start.schema.json`](../../../schemas/scratch/dispatch-start.schema.json). Detection is deterministic and reads `.scratch/handoff.jsonl` alone:

> A `dispatch-start` record for `(req_id, author)` with no subsequent substantive record from the same `(req_id, author)` after that `dispatch-start`'s line signals an interrupted dispatch.

Substantive records (closed enum): `build-pass`, `build-failure`, `review-feedback`, `review-plan`, `prd-entry`, `design-block`, `consultation-response`. Built-in agents not defined under `.claude/agents/` (e.g. `general-purpose`, `Explore`) are out of scope for this contract; root carries the dispatch-discipline for those per `CLAUDE.md` § Tool-call budget.

## Mid-Implementation Consultation

The feature-implementer may need a focused answer from product-requirements-expert or system-design-expert during TDD cycles when the inner loop discovers a question the triage didn't anticipate. The implementer appends a `consultation-request` targeting the specialist; `route` dispatches that specialist in consultation mode (`consultation-dispatch`); the specialist appends a `consultation-response`; `route` returns control to the implementer (`consultation-return`).

Consultations are substeps, not handoffs. They preserve the implementer's active state — the pipeline advances only when the implementer's own next handoff (`build-pass` or `build-failure`) appears.

Consult when another agent owns the answer; escalate to `.scratch/escalations.md` only when a human must act — an external prerequisite, or a conflict no agent can resolve. The test is who can unblock you — routing a human-only decision through consultation just burns a dispatch.

## Review Feedback Actions

See the `review-workflow` skill for feedback tag definitions and the review process. The two root-applied procedures — the reviewer stall check and design-doc autofixes — live below, because root executes them while routing.

### Reviewer Stall Check (root)

After the reviewer dispatches return: verify each reviewer in the roster has appended a `review-feedback` record for the current `req_id` since the latest `build-pass`. For each missing record, re-dispatch the corresponding reviewer ONCE with this prompt: `"Your previous run returned without appending a review-feedback record to .scratch/handoff.jsonl. Run the review now. Your only deliverable is that record — see Output Protocol in review-workflow."` If a record is still missing after the retry, root appends an entry to `.scratch/escalations.md` naming the reviewer and stops — do not proceed to findings processing. Only root runs this check; specialists cannot re-dispatch agents. `route` executes the ladder deterministically: one silent `dispatch-start` since `build-pass` earns the single retry; a second returns `reviewer-stalled`.

### Root-Applied Autofix on Design Docs

To keep the system-design-expert quality bar tight while removing ceremony from mechanical fixes, root may apply `tag: "autofix"` findings on `docs/system-design.md` and `docs/adr/*.md` directly — without redispatching system-design-expert. The quality bar lives in the `blocked` and `clarify` (with `clarify_target: "system-design-expert"`) paths, which still route to system-design-expert.

The eligibility rules for autofix on design-doc paths live in the `document-writing` skill's stack overlay, `review-checks.md` § Autofix on Design-Doc Paths. Doc-reviewer is responsible for never tagging a finding as autofix on these paths unless every condition there holds (`review-workflow` § Root-Applied Autofix Eligibility). This section defines what root does once such a finding exists.

#### Apply Procedure

1. **Validate the finding statically.** Confirm: `tag == "autofix"`; `location` falls under a design-doc path; `fix` field is present and is a literal replacement string (not a description). If any check fails, treat the finding as `blocked` and redispatch system-design-expert instead.
2. **Apply via Edit.** Use the Edit tool with the literal `fix` string as `new_string`. Read the file to obtain the exact `old_string`. Do not paraphrase or "improve" the fix — root acts as a typewriter for the doc-reviewer's verbatim proposal.
3. **Re-check the bounds after the Edit.** Confirm: ≤5 lines changed, ≤200 characters changed, no `## ` heading line modified, no `<a id="..."></a>` anchor value changed, no REQ-ID reference introduced or removed, no content inside a fenced code block touched, no markdown link target changed. If any check fails, revert (Edit back) and redispatch system-design-expert.
4. **Append a `design-doc-autofix` record** to `.scratch/handoff.jsonl` carrying: the source finding (copied verbatim), the file path, the autofix category (`writing-standards` or `structural`), `old_content`, `new_content`, `lines_changed`, `chars_changed`. Schema: [`schemas/scratch/design-doc-autofix.schema.json`](../../../schemas/scratch/design-doc-autofix.schema.json). Append per the `handoff-append` skill.
5. **Append-only discipline.** Preserve every prior line in `handoff.jsonl` verbatim.

#### Why The Record Matters

- **Gate-time re-validation.** The autofix-audit procedure in `code-quality-gate` re-checks every `design-doc-autofix` record against the bounds in step 3, so a mis-applied autofix fails the quality gate before merge.
- **The system-design-expert audits on next dispatch.** The `design-validation` skill instructs the system-design-expert to read all `design-doc-autofix` records since its last dispatch and judge them. It may reject any by appending an `autofix-rejected` finding to the next `design-block` record.
- **Direct-edit detection.** The `code-quality-gate` autofix audit also fails if `docs/system-design.md` or `docs/adr/*` has uncommitted changes that no `design-doc-autofix` or `design-block` record covers — catching any future bypass of the protocol.

#### What Root Does Not Do

- Root does NOT autofix on `docs/prd.md` (product-requirements-expert owns PRD; no autofix exception).
- Root does NOT autofix any tag other than `autofix` (blocked/clarify/escalate route as defined elsewhere).
- Root does NOT batch autofixes across artifacts — one record per finding, one Edit per finding.

## State Files

| File | Created By | Consumed By |
|---|---|---|
| `.scratch/handoff.jsonl` | product-requirements-expert, system-design-expert, feature-implementer, review-planner, the roster reviewers, change-grader, root (all append-only) | the router — `route` and, on `escalate`, the coordinator (validation gates); all consumer agents |
| `.scratch/implementation-plan.md` | feature-implementer | feature-implementer (self-tracking) |
| `.scratch/escalations.md` | feature-implementer (escalate-tag findings, mid-loop escalations); root on the router's `blocked` decision (prerequisite-missing aborts; reviewer stalls per § Reviewer Stall Check; escalate findings on an `approved` verdict per § Blocking) — never the coordinator itself | Human |

`.scratch/handoff.jsonl` is the append-only structured handoff log; one JSON object per line, each carrying a `type` discriminator. Record types:

| Record `type` | Producer | Purpose |
|---|---|---|
| `prd-entry` | product-requirements-expert (system-design-expert: the refactor-first sibling entry) | Active feature scope for system-design-expert and implementer. |
| `design-block` | system-design-expert | Triage verdict and implementation guidance. |
| `consultation-request` | any specialist mid-work | Focused question to another specialist that does not advance the pipeline. |
| `consultation-response` | the consulted specialist | Focused answer; routes control back to the requester. |
| `review-feedback` | each reviewer agent in the roster | Per-reviewer verdict and findings. |
| `build-failure` | feature-implementer | Quality-gate failure with error context and retry counter. |
| `build-pass` | feature-implementer | Quality-gate success marker. |
| `review-plan` | `score-change.py review-plan` (author `review-plan-engine`); `review-planner` for the gray zone | Names the reviewer roster and read scope for a review pass; fail-closed to the full battery when absent or invalid. |
| `design-doc-autofix` | root | Audit trail for root-applied autofixes on design-doc paths (see § Root-Applied Autofix on Design Docs). |
| `dispatch-start` | every project-defined agent except `pipeline-coordinator` and `change-grader` (as its first tool call) | Half of the dispatch-event contract; "no subsequent substantive record from same `(req_id, author)`" is the deterministic truncation signal. Not substantive — does not satisfy the implicit stop. |
| `grader-features` | change-grader (`score-change.py extract`) | change-grader (the grading read). Deterministic structural row; advisory, terminal — does not route. |
| `grader-verdict` | change-grader | Advisory facets + rationale + `clear`/`concern` verdict; surfaced to the session, recorded, never routed. Not substantive for truncation detection. |

## Log Access

The coordinator never writes records — it only reads them for routing decisions. All writes to `.scratch/handoff.jsonl` go through `scripts/handoff.py` per the `handoff-append` skill, which holds the writer contract, the full command table, and the exit codes. Reading the whole log with the `Read` tool for context is fine; decisions that gate routing use the query subcommands below.

| Operation | Command |
|---|---|
| Routing decision | `python3 scripts/handoff.py route [--req-id <id>]` |
| Latest record for a gate | `python3 scripts/handoff.py latest --type <type> [--req-id <id>]` |
| Next retry counter | `python3 scripts/handoff.py next-retry --req-id <id>` |
| Whole-file check | `python3 scripts/handoff.py validate` |

`route` exits 0 whenever a decision was computed — including `blocked` and `escalate`; the decision field carries the state. The human-inspection surface (`show`, and `view` via the `handoff-board` skill) is listed in `handoff-append` § Writer Commands.

## Human Checkpoints

Routing is deterministic: a passed gate names the next agent per the Handoff Conditions table, without waiting for approval. Human attention concentrates at four points — two advisory, two blocking:

1. **After PRD update** *(advisory)* — Review that the requirement captures intent. The pipeline proceeds; to intervene, halt and route back to product-requirements-expert to append a superseding `prd-entry`.
2. **After design notes** *(advisory)* — Review the architectural approach. Same intervention path, via system-design-expert.
3. **After escalations** *(blocking)* — The pipeline halts until the human decides each `[ESCALATE]` item. A `design-block` with `verdict: "conflicting"` halts the same way (Handoff Conditions table).
4. **After feature complete** *(blocking)* — The change-grader's verdict is advisory; only the human approves the merge.

## Coordinator Output Format

The coordinator handles what `route` cannot: untriaged fresh-intake classification and every `escalate` decision; a `next`-triaged pick dispatches `product-requirements-expert` directly. Its recommendation follows the same table; `route`'s JSON is the deterministic fast-path for the rows the table decides alone.

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

These rules bind the coordinator when it is dispatched — fresh intake and `escalate` states. On the routine path `route` applies the same table.

1. Never skip pipeline stages for new features.
2. Shortcuts are allowed only per the agent selection table above.
3. If `.scratch/` contains stale state from a previous feature, recommend clearing it first.
4. Report all `design-block` records with `verdict: "conflicting"` and all `review-feedback` findings tagged `escalate`.
5. If the latest `build-*` record for the active `req_id` is a `build-failure`, apply the retry logic in § Build-Failure Recovery.
6. If a feature-implementer dispatch ended without appending a `build-pass` or `build-failure` record, apply § Truncation Recovery — continue the same slice; re-split only on the Pre-Check over-size branch or on non-convergence.
7. After every roster reviewer's latest `review-feedback` verdict is `"approved"`, the feature is complete: recommend dispatching the `change-grader` agent (terminal, advisory). With `layout.toml [harness] auto_grade = false`, skip that recommendation — `route` reports feature-complete directly. The grader assesses how much human attention the passing change deserves; its `clear`/`concern` verdict is recorded and surfaced to the session, but it does **not** route and is **not** a merge or correctness gate. Do not consume its verdict for any routing decision.
