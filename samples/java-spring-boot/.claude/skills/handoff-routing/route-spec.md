# Route Spec — the deterministic routing contract

The normative definition of what `python3 scripts/handoff.py route` decides:
the Handoff Conditions table, the validation gates' field checks, Build-Failure
Recovery, and Truncation Recovery. `route` executes this spec and
`scripts/test_handoff.py` pins each rule to a decision — editing this file
means extending `route` and its tests in the same change.

No dispatched agent preloads this file. The `handoff-routing` skill
(`SKILL.md` in this directory) carries the judgment-facing summaries under the
same section names; root reads a recovery section here on demand when a rule
name points at it. `route`'s JSON decision carries the matched rule and the
exact gate errors — consumers follow the decision; they never re-derive it
from this spec.

## Handoff Conditions

All transitions are gated on the latest record per `(req_id, type)` in
`.scratch/handoff.jsonl`. `route` evaluates the table below and prints one
JSON decision:

- **`dispatch`** names the next agent(s), the matched rule, and the prompt
  context. A failed gate is a `dispatch` of the upstream agent carrying the
  exact errors — the bounce, expressed as the re-dispatch it is.
- **`blocked`** always halts for a human: a dirty log, a `conflicting`
  verdict, a stalled reviewer, a `human-consultation`, feature-complete.
- **`escalate`** marks a state the table does not decide; the coordinator
  resolves it. The escalate arm is enumerated in `SKILL.md` § Handoff
  Conditions.

Route is fail-closed: it never repairs a log and never guesses past a failed
check. Each rule string names the matched condition. Where a section of that
name exists, it defines the dispatch's prompt context: `build-retry` under
§ Build-Failure Recovery, `truncation-continue` under § Truncation Recovery,
`reviewer-stall-retry` under `SKILL.md` § Reviewer Stall Check. A
`process-findings` decision with `halt_after: true` carries an escalate
finding — root halts after that dispatch per `SKILL.md` § Blocking.

| Current Agent | Trigger | Next Agent |
|---|---|---|
| product-requirements-expert | latest `prd-entry` record passes the Validation Gate | system-design-expert |
| system-design-expert | latest `design-block` record has `verdict` in {`covered`, `minor`, `new`, `foundational`} and passes the Validation Gate | feature-implementer |
| system-design-expert | latest `design-block` record has `verdict: "conflicting"` | Halt pipeline; surface to user |
| Any specialist | latest record is a `consultation-request` | target specialist (consultation mode); `target: "human"` blocks for the root conversation (`human-consultation`) |
| Any specialist | latest record is a `consultation-response` | **back to the requesting specialist** (resume; do not advance the pipeline) |
| feature-implementer | latest `build-pass` record exists and post-dates any `build-failure` for the same `req_id` | the active `review-plan`'s roster (parallel); see Gate 5 for plan resolution |
| review-plan-engine | latest `review-plan` after the build-pass has `risk: "gray"` | `review-planner` (resolve the roster); `planner-stall-retry` then `planner-stalled` on a silent planner |
| review-planner | latest `review-plan` after the build-pass has `risk` in {`low`, `high`} with a roster | that roster (parallel) |
| feature-implementer | fewer than 3 `build-failure` records since the latest `design-block` (the § Build-Failure Recovery counter) | feature-implementer (retry with error context) |
| feature-implementer | the § Build-Failure Recovery counter reaches 3 `build-failure` records since the latest `design-block` | system-design-expert (re-triage) |
| feature-implementer | a `dispatch-start` for `(req_id, feature-implementer)` exists with no subsequent substantive record from the same `(req_id, author)` (deterministic per § Dispatch Truncation Detection) | feature-implementer (continue the same slice per § Truncation Recovery; system-design-expert on non-convergence) |
| feature-implementer | latest `build-failure` record has `abort_reason` set | routed per § Build-Failure Recovery step 0 (abort-reason short-circuit) |
| system-design-expert | latest `design-block` record has `verdict: "refactor-first"` and a sibling refactor `prd-entry` (newer `ts`, different `req_id`) | feature-implementer for the refactor `req_id` first (`route` escalates the ordering); `refactor-resume` re-triages the original via `supersedes_record_at` after the refactor completes |
| All reviewers in the roster | each reviewer's latest `review-feedback` record has `verdict: "approved"` | Feature complete → dispatch `change-grader` (terminal, advisory), unless `layout.toml [harness] auto_grade = false` — then feature-complete directly |
| Any reviewer | latest `review-feedback` record has `verdict: "changes_requested"` or `"blocked"` with non-empty findings | the findings' artifact owners per Gate 4's split (root applies design-doc autofixes; an all-autofix round escalates as `autofix-only-round`) |

## Validation Gates

Each agent transition validates the inbound record(s) against a schema before
dispatching the next specialist. Malformed or missing records bounce back to
the upstream agent without consuming a downstream dispatch. The discovery
discipline agents apply when reading state is `SKILL.md` § Common Procedure;
the field checks below are `route`'s.

### Gate 1: product-requirements-expert → system-design-expert (`prd-entry`)

Schema: [`schemas/scratch/prd-entry.schema.json`](../../../schemas/scratch/prd-entry.schema.json). Required checks:

- `type == "prd-entry"`, `author == "product-requirements-expert"` (`system-design-expert` for the refactor-first sibling entry).
- `req_id` matches `^REQ-[A-Z]+-[0-9]{3}$`. `ts` is a non-empty ISO 8601 string.
- `title`, `summary` are non-empty strings.
- `acceptance_criteria`, `file_targets`, `test_names` are non-empty arrays of non-empty strings.
- Each `test_names` entry matches the `test_name_pattern` regex declared in `scripts/layout.toml`.

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
- `refactor-first` → dispatch feature-implementer for the sibling refactor `prd-entry` first. Resume the original slice's triage via a new `design-block` with `supersedes_record_at` once the refactor completes: its `grader-verdict`, or roster approval when `auto_grade = false` leaves no grader run. `route` escalates both sibling shapes and emits `refactor-resume` on that completion. See the Handoff Conditions table row for the full trigger.

### Gate 2b: Consultation roundtrip (`consultation-request` / `consultation-response`)

Schemas: [`schemas/scratch/consultation-request.schema.json`](../../../schemas/scratch/consultation-request.schema.json), [`schemas/scratch/consultation-response.schema.json`](../../../schemas/scratch/consultation-response.schema.json).

When the latest record is a `consultation-request`:

- Validate `type`, `req_id`, `ts`, `author` (the requesting specialist), `target` (the specialist to consult), `context`, `question`.
- Dispatch the `target` agent in consultation mode (it reads the request and the relevant durable memory, then appends a `consultation-response`).
- `target: "human"` instead yields `blocked` (rule `human-consultation`): root runs the conversation per `agentic-harness.md` § Conversations Stay in Root, then appends the `consultation-response` with `author: "human"`. This is the elicitation pause made durable. The questions and the decisions both live in the log; a later session resumes the conversation instead of guessing between pause and truncation.

When the latest record is a `consultation-response`:

- Validate `type`, `req_id`, `ts`, `author` (must match the `target` of the corresponding request), `in_response_to` (1-indexed line number pointing to the request), `answer`.
- Route control **back to the requesting specialist named in the corresponding request**. Do not advance the pipeline stage. The requester resumes its main work; the pipeline advances only when the requester's main work reaches its own next handoff.

### Gate 3: implementer → reviewers (`build-pass`)

Schema: [`schemas/scratch/build-pass.schema.json`](../../../schemas/scratch/build-pass.schema.json). Required checks:

- The latest `build-*` record for `req_id` is `type == "build-pass"`.
- `author == "feature-implementer"`, valid `req_id` and `ts`.

If the latest is a `build-failure`, apply § Build-Failure Recovery instead.

### Gate 4: reviewers → next step (`review-feedback`)

The gate waits on the **active pass's roster** — resolved by Gate 5 from the
`review-plan` record, defaulting to the full four-reviewer floor plus any
`extra_reviewers` declared in `scripts/layout.toml [harness]` when no plan is
present; the roster's definition lives in `review-workflow` § Review Phase. Every
reference to "the roster" below is the resolved pass roster, not necessarily the
full floor.

Schema: [`schemas/scratch/review-feedback.schema.json`](../../../schemas/scratch/review-feedback.schema.json). For each reviewer in the roster, the latest `review-feedback` record (filtered by `req_id` and `author`) must:

- Have `type == "review-feedback"`, valid `req_id` and `ts`.
- `author` is a reviewer in the roster: a floor reviewer (`code-quality-reviewer`, `test-reviewer`, `security-reviewer`, `doc-reviewer`) or a declared extra reviewer (named `*-reviewer`).
- `verdict` is one of: `approved`, `changes_requested`, `blocked`.
- `findings` is an array; when `verdict != "approved"`, it should be non-empty (warn but do not hard-fail; an empty findings list with a non-approved verdict means the reviewer did not produce actionable output and should be re-dispatched).
- Each finding has `tag`, `location`, `description`. When `tag == "clarify"`, `clarify_target` is required.

Routing:

- Every roster reviewer `verdict == "approved"` → feature complete; dispatch the `change-grader` agent (terminal, advisory — it grades how much human attention the change deserves and its verdict does not route). A project may opt out with `layout.toml [harness] auto_grade = false`: `route` then reaches feature-complete on approval without the grader run. The grader stays runnable by hand (the `change-grading` skill), and a hand-run `grader-verdict` still routes normally.
- When any roster record is missing, run `SKILL.md` § Reviewer Stall Check before either branch below.
- Any `verdict == "changes_requested"` or `"blocked"` → split the union of findings by artifact owner (see the `review-workflow` skill's `reference.md` § Artifact Ownership) and dispatch each owner agent with the relevant slice. **Exception:** `tag == "autofix"` findings whose `location` is a design-doc path (`docs/system-design.md` or `docs/adr/*.md`) are applied by root directly per `SKILL.md` § Root-Applied Autofix on Design Docs — they do NOT redispatch system-design-expert. Every other finding on those paths still routes to system-design-expert.
- Any `tag == "escalate"` finding → the feature-implementer also appends the entry to `.scratch/escalations.md` while processing findings (the `review-workflow` skill's `reference.md` § Processing Reviews); the pipeline then halts per `SKILL.md` § Blocking. The routing decision surfaces the finding (`escalate_findings`, `halt_after`); the coordinator reports it when dispatched (Coordinator Rule 4). Neither writes anything.

### What the gates do NOT check

- Content quality (are the acceptance criteria *good*? are the findings *correct*?). That is the consuming agent's judgement.
- Cross-record consistency beyond `req_id` linkage (e.g. whether `design-block.primary_paths` overlaps `prd-entry.file_targets`). Consumers may surface mismatches as findings; gates do not.

The gates are structural: required fields present, types correct, patterns match. Every check must catch deterministically.

### Gate 5: build-pass → reviewers via `review-plan` (roster resolution)

The reviewer dispatch after a `build-pass` is proportional to a logged risk estimate. The feature-implementer appends a `review-plan` record (author `review-plan-engine`, via `scripts/score-change.py review-plan`) as the final step of gate-pass; `route` reads it to resolve the roster for this pass. Schema: [`schemas/scratch/review-plan.schema.json`](../../../schemas/scratch/review-plan.schema.json). Resolution, from the latest `review-plan` after the current `build-pass`:

- **No plan** → fail closed to the full roster (the four-reviewer floor plus declared extras). This reproduces pre-plan behavior, so a project that never runs the engine, and every pre-existing log, dispatches the full battery.
- **`risk` in {`low`, `high`} with a `roster`** → gate on that roster. Its members must be a non-empty subset of the full roster; a plan naming an unknown reviewer fails closed to the full roster.
- **`risk: "gray"`, author `review-plan-engine`** → dispatch `review-planner` (rule `plan-gray`) to resolve the roster. A silent planner (a `review-planner` `dispatch-start` after the gray plan with no later `review-plan`) earns one retry (`planner-stall-retry`); a second returns `planner-stalled` (blocked). The planner appends a `review-plan` (author `review-planner`) with `risk` `low`/`high` and a roster; the latest plan then governs.
- **`risk: "gray"`, author `review-planner`** → bounce (`plan-gray-invalid`): only the engine may defer; the planner must resolve to `low` or `high`.

Gate 4 then waits on the resolved pass roster. On a re-review cycle the implementer appends a fresh `review-plan` whose engine-computed roster is the fix delta's dissenters plus `bar_clause`-implicated reviewers. The engine escalates to the full roster when the fix delta is itself risky or escapes the reviewed surface. `review-workflow` § Risk-Proportional Roster holds the ladder; `route` only reads the resulting roster. A reviewer whose latest verdict for the slice is already `approved` and who is not on the current pass roster keeps that verdict — feature-complete requires every reviewer dispatched since the latest `design-block` to hold a latest `approved`, and `route` re-dispatches any the plan dropped. Across a re-triage the engine's `design-revision` trigger re-runs the full battery, so a superseded-cycle dissent is re-covered by that escalation, not by this gate.

## Build-Failure Recovery

When the feature-implementer runs the quality gate and it fails (build error, test failure, format/lint failure), the implementer appends a `build-failure` record to `.scratch/handoff.jsonl` with the error output and retry count, then exits. Schema: [`schemas/scratch/build-failure.schema.json`](../../../schemas/scratch/build-failure.schema.json). `route` executes the recovery steps below deterministically; the prose is their normative definition.

### Recovery steps

0. **Abort-Reason Short-Circuit.** If the latest `build-failure` record's `abort_reason` field is set, the implementer is aborting because retrying cannot help — the slice cannot be implemented as triaged, or the autofix audit failed. Skip the retry counter and route based on the value:

   - `wrong-shape-slice` → `product-requirements-expert` for re-split. Pass `error_output` as the diagnosis input. This is the over-size remedy reached directly via the implementer's explicit diagnosis — the re-split that § Truncation Recovery otherwise reaches only on non-convergence.
   - `design-mismatch` → `system-design-expert` for re-triage. The next `design-block` carries `supersedes_record_at` pointing to the prior design-block. This route also covers a failed autofix audit (`failed_check: "autofix-audit"`): the expert reconciles the design-doc state, and its superseding `design-block` restarts the gate.
   - `prerequisite-missing` → halt the pipeline and surface to user; root appends the issue to `.scratch/escalations.md` on the `blocked` decision — the router writes nothing.

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
   - Instruction: "The implementer did not converge in 3 attempts (gate failures and/or truncations). Re-triage the slice; the prior design block may need revision."
   - The system-design-expert re-triages and appends a new `design-block` record with one of the six verdicts (`covered` / `minor` / `new` / `foundational` / `conflicting` / `refactor-first`) and `supersedes_record_at` set to the line number of the prior design-block.
4. A new `design-block` with `supersedes_record_at` set resets the retry counter — `build-failure` records are counted only after the latest `design-block`, so the next attempt starts at `retry: 1`. If the new verdict is `conflicting`, the pipeline halts and surfaces to the user instead.

### Retry rules

- The implementer increments `retry` in each new `build-failure` record (1, 2, 3). Compute the next value by counting `build-failure` records for the active `req_id` appended *after* the latest `design-block` line, then setting `retry = count + 1`. `python3 scripts/handoff.py next-retry --req-id <id>` implements exactly this counting rule. The first failure after a fresh `design-block` is `retry: 1`, whether the latest is the original or a record with `supersedes_record_at` set.
- Count `build-failure` records, **not** `dispatch-start` records. Every implementer dispatch writes a `dispatch-start` — fresh dispatch, review-feedback processing, retry, consultation resume. A dispatch-start count would inflate `retry` on a normal slice that goes through review cycles and escalate it spuriously.
- `retry` bounds gate-failure retries; the continue-truncate loop is bounded separately by § Truncation Recovery's consecutive-truncation count. Append-only — never edit a prior record.
- On success, the implementer appends a `build-pass` record. Prior `build-failure` records remain in the file as the diagnostic retry trail.
- The coordinator never modifies records — it only reads them for routing decisions.
- Maximum 3 retries per design cycle. A new `design-block` with `supersedes_record_at` starts a fresh cycle.

## Truncation Recovery

When a feature-implementer dispatch ends without appending a `build-pass` or `build-failure` record for the active `req_id`, the implementer truncated before reaching the quality gate — the dispatch ran longer than one cap-bounded turn. Truncation alone does **not** mean the slice is over-scoped. The Scoping Pre-Check re-scopes a multi-behavior slice *before* dispatch. A slice that reaches dispatch and then truncates is presumed correctly sized and simply long — one coherent behavior whose mechanical surface exceeded one turn.

**The default recovery is to continue the same slice.** A continuation re-dispatch is a fresh dispatch that reads the ledger and the working tree — portable across every runtime. Where the runtime offers in-place resume of the stopped sub-agent (a bare `continue`, admitted by an allowlist that admits only `continue` and so cannot smuggle new instructions), that is an optional fast-path for the same continuation: same slice, same ledger trail, no context re-derivation. Re-split is reserved for two cases: the Pre-Check's over-size branch (a multi-behavior slice caught before dispatch), and **non-convergence** — continuation re-dispatches that keep truncating without producing a `build-pass`.

### Dispatch Truncation Detection

Every dispatched project-defined agent except `pipeline-coordinator` and the terminal `change-grader` appends a `dispatch-start` record as its first tool call. Schema: [`schemas/scratch/dispatch-start.schema.json`](../../../schemas/scratch/dispatch-start.schema.json). Substantive records (the closed enum below) act as the implicit stop signal. **Deterministic detection rule:**

> A `dispatch-start` record for `(req_id, author)` with no subsequent substantive record from the same `(req_id, author)` after that `dispatch-start`'s line signals an interrupted dispatch.

Substantive records (closed enum): `build-pass`, `build-failure`, `review-feedback`, `review-plan`, `prd-entry`, `design-block`, `consultation-response`. `review-plan` closes the review-planner's dispatch; engine-authored plans have no dispatch to close. `consultation-request`, `design-doc-autofix`, and `dispatch-start` itself are explicitly NOT substantive. A pending `consultation-request` still closes its author's dispatch for detection — the rule compares the `dispatch-start` against the latest substantive, request, and response lines. A consultation-raising dispatch therefore routes as a consultation, never a truncation.

An earlier design gated recovery on an out-of-band signal from root; the `dispatch-start` record supersedes that trigger. Detection reads `.scratch/handoff.jsonl` alone; `route` fires the implementer's recovery rows the moment the rule is satisfied, and the coordinator fires recovery on `escalate` states.

`pipeline-coordinator` is exempt from the contract — its output is a routing recommendation in the response stream, not a substantive `.scratch/` record, so "start without substantive record" would always fire. The terminal `change-grader` is exempt because nothing routes on its records — the truncation signal would have no consumer; root re-dispatches it on a missing `grader-verdict`. Built-in agents not defined under `.claude/agents/` (e.g. `general-purpose`, `Explore`) are out of scope for this contract; root carries the dispatch-discipline for those per `CLAUDE.md` § Tool-call budget.

### Continuation steps

`route` executes steps 1–4 below deterministically for the feature-implementer; truncation of an agent with no recovery row here escalates to the coordinator.

1. Detect: apply the **Dispatch Truncation Detection** rule above. A `dispatch-start` for `(req_id, feature-implementer)` exists with no subsequent substantive record from `feature-implementer` for that `req_id` — the implementer's dispatch was interrupted before it could write a `build-pass` or `build-failure`.
2. Count **consecutive truncations**: the run of `feature-implementer` `dispatch-start` records since the latest `design-block`, ending at this one, with **no intervening `feature-implementer` record of any kind** (no `build-pass`, `build-failure`, or `consultation-request`) between them. Any implementer record resets the run to zero. This counter is independent of the `build-failure` `retry` counter and is immune to review-feedback-processing and consultation-resume dispatches (those leave records) — it measures only a genuine continue-truncate loop.
3. If the consecutive-truncation count `< 3`, re-dispatch the implementer to **continue the same slice**, with this prompt context:
   - The latest `design-block` record (the original design).
   - `.scratch/implementation-plan.md` (what was planned).
   - The partial-artifact `build-failure` record if one was left, else the instruction to re-derive progress from the working tree.
   - Instruction: "Continue the slice. Read the working tree to see what already landed, finish the remaining work, and reach the quality gate. This is continuation N of 3."
   Where the runtime offers in-place `continue`, root may use it as the fast-path instead of a fresh re-dispatch — same continuation, same ledger trail.
4. If the consecutive-truncation count `== 3` (non-convergence — a run of three truncated dispatches produced no record), route to system-design-expert for re-triage, the same destination § Build-Failure Recovery reaches at `retry == 3`. The re-triage decides among three outcomes: a revised `design-block`; a genuine re-split via a new `prd-entry` from product-requirements-expert if the slice is multi-behavior after all; or, for a single behavior that is legitimately wider than one dispatch, the signal that the agent's `toolCallBudget` is mis-calibrated for that behavior — a budget-tuning decision, not a re-split (a single behavior has nothing to split). **Re-split is one non-convergence outcome, not the first response.**

### Partial-record paths

Two partial-record paths route through existing recovery — they do NOT trigger Truncation Recovery:

- **`build-failure` with `partial: true`** (feature-implementer reached `toolCallBudget` before the quality gate ran). The record flows through § Build-Failure Recovery above: `retry < 3` re-dispatches the implementer with the partial-progress description in `error_output`; `retry == 3` re-triages via system-design-expert. The implementer's next dispatch starts from the recorded progress instead of from scratch.
- **`review-feedback` with `verdict: "blocked"` plus a `tag: "truncation"` finding** (a reviewer reached `toolCallBudget` mid-review). The record routes through Gate 4's existing `changes_requested` / `blocked` path: feature-implementer processes findings, then the cycle re-runs the gate and re-invokes reviewers. The `truncation` tag is a progress marker, not an escalation — `SKILL.md` § Blocking does not apply to it.

Truncation Recovery (this section) covers only the residual case — the dispatch ended with **no new record at all** for the active `req_id`. The partial-artifact contract shrinks that population by structurally giving creator and verifier dispatches a way to leave evidence behind before exiting.

The elicitation pause ([`agentic-harness.md`](agentic-harness.md) § Conversations Stay in Root) never reaches this section. A `product-requirements-expert` raising artifact-level pushback, or a `system-design-expert` raising `foundational` interview questions, appends a `consultation-request` with `target: "human"`. Gate 2b halts for the conversation (`human-consultation`); the `consultation-response` resumes the requester. The record exists because a bare pause would be log-indistinguishable from a genuine truncation, and the questions would die with the session; recovery would re-pay the dispatch to re-derive them.

## Pipeline Flow

```
User Request
    |
    v
Router: handoff.py route validates and decides; coordinator classifies untriaged fresh intake + escalations
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
    |                     v (all roster review-feedback verdicts: approved)
    |               change-grader (terminal, advisory)
    |               (extract → grade diff → record grader-verdict)
    |                     |
    |                     v
    |               Feature complete (human merges; grader verdict is advisory)
    |
    +--- Bug fix (known) --> feature-implementer (shortcut)
    +--- Architecture Q ---> root elicitation, then system-design-expert records the outcome
    +--- Code review ------> All reviewers (parallel)
```
