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
  version: "1.1"
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
| feature-implementer | a `dispatch-start` for `(req_id, feature-implementer)` exists with no subsequent substantive record from the same `(req_id, author)` (deterministic per § Dispatch Truncation Detection) | feature-implementer (continue the same slice per Truncation Recovery; system-design-expert on non-convergence) |
| feature-implementer | latest `build-failure` record has `abort_reason` set | routed per § Build-Failure Recovery → Abort-Reason Short-Circuit |
| system-design-expert | latest `design-block` record has `verdict: "refactor-first"` and a sibling refactor `prd-entry` (newer `ts`, different `req_id`) | feature-implementer for the refactor `req_id` first; resume original `req_id` triage via `supersedes_record_at` after the refactor's `build-pass` |
| All reviewers in the roster | each reviewer's latest `review-feedback` record has `verdict: "approved"` | Feature complete → dispatch `change-grader` (terminal, advisory) |
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

**The roster.** Every change is gated by the reviewer roster: the mandatory four-reviewer floor — `code-quality-reviewer`, `test-reviewer`, `security-reviewer`, `doc-reviewer` — plus any `extra_reviewers` declared in `scripts/layout.toml [harness]`. The floor is non-negotiable; a project extends the roster upward, never drops a floor reviewer. The doctor enforces this (floor present in every tool surface; each extra named `*-reviewer`, present, and kept by `extensions`). All roster reviewers run in parallel and all must approve.

Schema: [`schemas/scratch/review-feedback.schema.json`](../../../schemas/scratch/review-feedback.schema.json). For each reviewer in the roster, the latest `review-feedback` record (filtered by `req_id` and `author`) must:

- Have `type == "review-feedback"`, valid `req_id` and `ts`.
- `author` is a reviewer in the roster: a floor reviewer (`code-quality-reviewer`, `test-reviewer`, `security-reviewer`, `doc-reviewer`) or a declared extra reviewer (named `*-reviewer`).
- `verdict` is one of: `approved`, `changes_requested`, `blocked`.
- `findings` is an array; when `verdict != "approved"`, it should be non-empty (warn but do not hard-fail; an empty findings list with a non-approved verdict means the reviewer did not produce actionable output and should be re-dispatched).
- Each finding has `tag`, `location`, `description`. When `tag == "clarify"`, `clarify_target` is required.

Routing:

- Every roster reviewer `verdict == "approved"` → feature complete; dispatch the `change-grader` agent (terminal, advisory — it grades how much human attention the change deserves and its verdict does not route).
- Any `verdict == "changes_requested"` or `"blocked"` → split the union of findings by artifact owner (see `review-checklist` § Artifact Ownership), then dispatch each owner agent with the relevant slice. **Exception:** `tag == "autofix"` findings whose `location` is a design-doc path (`docs/system-design.md` or `docs/adr/*.md`) are applied by root directly per `review-checklist` § Root-Applied Autofix on Design Docs — they do NOT redispatch system-design-expert. Every other finding on those paths still routes to system-design-expert.
- Any `tag == "escalate"` finding → also append an entry to `.scratch/escalations.md`.

### What the gates do NOT check

- Content quality (are the acceptance criteria *good*? are the findings *correct*?). That is the consuming agent's judgement.
- Cross-record consistency beyond `req_id` linkage (e.g. whether `design-block.primary_paths` overlaps `prd-entry.file_targets`). Consumers may surface mismatches as findings; gates do not.

The gates are structural: required fields present, types correct, patterns match. Every check must catch deterministically.

## Blocking

If any gate fails, if a `design-block` record carries `verdict: "conflicting"`, or if a `review-feedback` record carries a `tag: "escalate"` finding, stop the pipeline and resolve before continuing.

## Build-Failure Recovery

When the feature-implementer runs the quality gate and it fails (build error, test failure, format/lint failure), the implementer appends a `build-failure` record to `.scratch/handoff.jsonl` with the error output and retry count, then exits. Schema: [`schemas/scratch/build-failure.schema.json`](../../../schemas/scratch/build-failure.schema.json).

### Coordinator retry logic

0. **Abort-Reason Short-Circuit.** If the latest `build-failure` record's `abort_reason` field is set, the implementer is aborting because the slice cannot be implemented as triaged — not because the gate failed. Skip the retry counter and route based on the value:

   - `wrong-shape-slice` → `product-requirements-expert` for re-split. Pass `error_output` as the diagnosis input. This is the over-size remedy reached directly via the implementer's explicit diagnosis — the re-split that Truncation Recovery otherwise reaches only on non-convergence.
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
   - Instruction: "The implementer did not converge in 3 attempts (gate failures and/or truncations). Re-triage the slice; the prior design block may need revision."
   - The system-design-expert re-triages and appends a new `design-block` record with one of the six verdicts (`covered` / `minor` / `new` / `foundational` / `conflicting` / `refactor-first`) and `supersedes_record_at` set to the line number of the prior design-block.
4. A new `design-block` with `supersedes_record_at` set resets the retry counter — `build-failure` records are counted only after the latest `design-block`, so the next attempt starts at `retry: 1`. If the new verdict is `conflicting`, the pipeline halts and surfaces to the user instead.

### Retry rules

- The implementer increments `retry` in each new `build-failure` record (1, 2, 3). Compute the next value by counting `build-failure` records for the active `req_id` appended *after* the latest `design-block` line, then setting `retry = count + 1`. The first failure after a fresh `design-block` (whether the latest is the original or a record with `supersedes_record_at` set) is `retry: 1`. Count `build-failure` records, **not** `dispatch-start` records: every implementer dispatch writes a `dispatch-start` (fresh dispatch, review-feedback processing, retry, consultation resume), so a dispatch-start count would inflate `retry` on a normal slice that goes through review cycles and escalate it spuriously. `retry` bounds gate-failure retries; the continue-truncate loop is bounded separately by Truncation Recovery's consecutive-truncation count. Append-only — never edit a prior record.
- On success, the implementer appends a `build-pass` record. Prior `build-failure` records remain in the file as the diagnostic retry trail.
- The coordinator never modifies records — it only reads them for routing decisions.
- Maximum 3 retries per design cycle. A new `design-block` with `supersedes_record_at` starts a fresh cycle.

## Truncation Recovery

When the feature-implementer's dispatch ends without appending a `build-pass` or `build-failure` record for the active `req_id`, the implementer truncated before reaching the quality gate — the dispatch ran longer than one cap-bounded turn. Truncation alone does **not** mean the slice is over-scoped. The Scoping Pre-Check is the scope gate: it re-scopes a multi-behavior slice *before* dispatch. A slice that reaches dispatch and then truncates is presumed correctly sized and simply long — a single coherent behavior whose mechanical surface (file count, test matrix, sweep breadth) exceeded one turn. **The default recovery is to continue the same slice**: re-dispatch the implementer to finish the work, reading the partial-artifact record if one was left and otherwise re-deriving from the inbound records and the working tree.

A continuation re-dispatch is a fresh dispatch that reads the ledger and the working tree — portable across every runtime. Where the runtime offers in-place resume of the stopped sub-agent (a bare `continue`, admitted by an allowlist that admits only `continue` and so cannot smuggle new instructions), that is an optional fast-path for the same continuation: it skips the context re-derivation and leaves the identical ledger trail. Re-split is **not** the default response to a truncation. It is reserved for two cases: the Pre-Check's over-size branch (a multi-behavior slice caught before dispatch), and **non-convergence** — continuation re-dispatches that keep truncating without producing a `build-pass`.

### Dispatch Truncation Detection

Every dispatched project-defined agent except `pipeline-coordinator` and the terminal `change-grader` appends a `dispatch-start` record as its first tool call. Schema: [`schemas/scratch/dispatch-start.schema.json`](../../../schemas/scratch/dispatch-start.schema.json). Substantive records (the closed enum below) act as the implicit stop signal. **Deterministic detection rule:**

> A `dispatch-start` record for `(req_id, author)` with no subsequent substantive record from the same `(req_id, author)` after that `dispatch-start`'s line signals an interrupted dispatch.

Substantive records (closed enum): `build-pass`, `build-failure`, `review-feedback`, `prd-entry`, `design-block`, `consultation-response`. `consultation-request`, `design-doc-autofix`, and `dispatch-start` itself are explicitly NOT substantive.

`pipeline-coordinator` is exempt from the contract — its output is a routing recommendation in the response stream, not a substantive `.scratch/` record, so "start without substantive record" would always fire. Built-in agents not defined under `.claude/agents/` (e.g. `general-purpose`, `Explore`) are out of scope for this contract; root carries the dispatch-discipline for those per `CLAUDE.md` § Tool-call budget.

### Coordinator routing

1. Detect: apply the **Dispatch Truncation Detection** rule above. A `dispatch-start` for `(req_id, feature-implementer)` exists with no subsequent substantive record from `feature-implementer` for that `req_id` — the implementer's dispatch was interrupted before it could write a `build-pass` or `build-failure`.
2. Count **consecutive truncations**: the run of `feature-implementer` `dispatch-start` records since the latest `design-block`, ending at this one, with **no intervening `feature-implementer` record of any kind** (no `build-pass`, `build-failure`, or `consultation-request`) between them. Any implementer record resets the run to zero. This counter is independent of the `build-failure` `retry` counter and is immune to review-feedback-processing and consultation-resume dispatches (those leave records) — it measures only a genuine continue-truncate loop.
3. If the consecutive-truncation count `< 3`, re-dispatch the implementer to **continue the same slice**, with this prompt context:
   - The latest `design-block` record (the original design).
   - `.scratch/implementation-plan.md` (what was planned).
   - The partial-artifact `build-failure` record if one was left, else the instruction to re-derive progress from the working tree.
   - Instruction: "Continue the slice. Read the working tree to see what already landed, finish the remaining work, and reach the quality gate. This is continuation N of 3."
   Where the runtime offers in-place `continue`, the coordinator may use it as the fast-path instead of a fresh re-dispatch — same continuation, same ledger trail.
4. If the consecutive-truncation count `== 3` (non-convergence — three continuations in a row produced no record), route to system-design-expert for re-triage, the same destination Build-Failure Recovery reaches at `retry == 3`. The re-triage decides among three outcomes: a revised `design-block`; a genuine re-split via a new `prd-entry` from product-requirements-expert if the slice is multi-behavior after all; or, for a single behavior that is legitimately wider than one dispatch, the signal that the agent's `toolCallBudget` is mis-calibrated for that behavior — a budget-tuning decision, not a re-split (a single behavior has nothing to split). **Re-split is one non-convergence outcome, not the first response.**

The coordinator continues the same slice across truncations; it routes to a re-split only when the Pre-Check flagged over-size before dispatch or when continuation fails to converge. A slice reaches the implementer only after the Pre-Check's scope gate, so a truncation means the dispatch ran long — not that the slice holds more than one behavior.

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

Consult when another agent owns the answer; escalate to `.scratch/escalations.md` only when a human must act — an external prerequisite, or a conflict no agent can resolve. The test is who can unblock you — routing a human-only decision through consultation just burns a dispatch.

## Review Feedback Actions

See the `review-checklist` skill for feedback tag definitions and the review process.

## State Files

| File | Created By | Consumed By |
|---|---|---|
| `.scratch/handoff.jsonl` | product-requirements-expert, system-design-expert, feature-implementer, the roster reviewers, change-grader, root (all append-only) | coordinator (validation gates), all consumer agents |
| `.scratch/implementation-plan.md` | feature-implementer | feature-implementer (self-tracking) |
| `.scratch/escalations.md` | feature-implementer; coordinator on escalate-tag and prerequisite-missing paths | Human |

`.scratch/handoff.jsonl` is the append-only structured handoff log; one JSON object per line, each carrying a `type` discriminator. Record types:

| Record `type` | Producer | Purpose |
|---|---|---|
| `prd-entry` | product-requirements-expert | Active feature scope for system-design-expert and implementer. |
| `design-block` | system-design-expert | Triage verdict and implementation guidance. |
| `consultation-request` | any specialist mid-work | Focused question to another specialist that does not advance the pipeline. |
| `consultation-response` | the consulted specialist | Focused answer; routes control back to the requester. |
| `review-feedback` | each reviewer agent in the roster | Per-reviewer verdict and findings. |
| `build-failure` | feature-implementer | Quality-gate failure with error context and retry counter. |
| `build-pass` | feature-implementer | Quality-gate success marker. |
| `design-doc-autofix` | root (coordinator) | Audit trail for root-applied autofixes on design-doc paths (see `review-checklist` § Root-Applied Autofix on Design Docs). |
| `dispatch-start` | every project-defined agent except `pipeline-coordinator` and `change-grader` (as its first tool call) | Half of the dispatch-event contract; "no subsequent substantive record from same `(req_id, author)`" is the deterministic truncation signal. Not substantive — does not satisfy the implicit stop. |
| `grader-features` | change-grader (`score-change.py extract`) | change-grader (the grading read). Deterministic structural row; advisory, terminal — does not route. |
| `grader-verdict` | change-grader | Advisory facets + rationale + `clear`/`concern` verdict; surfaced to the session, recorded, never routed. Not substantive for truncation detection. |

## Log Access

All writes to `.scratch/handoff.jsonl`, and all gate queries over it, go through `scripts/handoff.py` (Python 3 stdlib, same toolchain as the change-grader extractor). Writing the file directly — shell redirection onto it (`>>`, `cat >>`, `echo >>`), or a `Write`/`Edit` tool call — is prohibited. It skips validation and corrupts the log: a missing trailing newline glues two records onto one line, and the file stops parsing. This is distinct from feeding a record to `append` on its stdin. A heredoc piped into `append` is the sanctioned input mechanism, not a raw write (see the canonical form below). Reading the whole log with the `Read` tool for context is fine; decisions that gate routing use the query subcommands below.

| Operation | Command |
|---|---|
| Append a record | `python3 scripts/handoff.py append <type>` — record JSON on stdin (canonical form below) |
| Latest record for a gate | `python3 scripts/handoff.py latest --type <type> [--req-id <id>]` |
| Next retry counter | `python3 scripts/handoff.py next-retry --req-id <id>` |
| Whole-file check | `python3 scripts/handoff.py validate` |
| Human inspection | `python3 scripts/handoff.py show [--last N]` |

Append the record by piping it to stdin through a **quoted** heredoc — the quotes (`<<'EOF'`) keep the body literal so nothing in the JSON is shell-expanded:

```bash
python3 scripts/handoff.py append prd-entry <<'EOF'
{"type":"prd-entry","req_id":"<req-id>","ts":"<iso-8601>","author":"<agent>", …}
EOF
```

**The heredoc must sit directly on the `python3` command, exactly as above.** The command line must *begin* with `python3 scripts/handoff.py append <type>`. Do not wrap it as `cat <<'EOF' | python3 …`, and do not feed the record with `echo …|`, `printf …|`, or `cat file |`. A producer before the pipe makes the command start with `cat`/`echo`/`printf`, which no tool's auto-allow matches. Claude's hook defers on the pipe; Copilot's `shell(python3:*)` and Junie's `python3 scripts/handoff.py **` rules both require a `python3` prefix. The append then stalls on a permission prompt — the failure is more likely for large records, where the `cat <<'EOF' |` idiom is tempting. The direct heredoc above is the one shape every tool pre-approves, at any record size.

**Permission setup (one-time, per tool).** `append` is the pipeline's only sanctioned write, and it is safe — append-only, schema-validated, scoped to the log. Each tool's permission layer must pre-approve it so routine appends do not prompt; the agent's tool grant alone does not. Claude Code is pre-approved by a committed `PreToolUse` hook (`.claude/hooks/handoff-allow.sh`, registered in `.claude/settings.json`). It auto-allows `python3 scripts/handoff.py` invocations and defers everything else. A prefix allow-rule cannot cover the heredoc form, so the hook is required. OpenCode pipeline agents already declare `bash: allow`, which runs the command without a prompt — no extra setup. Copilot CLI and Junie keep command-approval in user space, so each needs a one-time allow entry. Launch Copilot with `--allow-tool 'shell(python3:*)'`, or add a `preToolUse` hook to its user `config.json`. For Junie, add an allowlist rule `{ "pattern": "python3 scripts/handoff.py **", "action": "allow" }` to `~/.junie/allowlist.json`, or run in brave mode.

`append` validates the record against `schemas/scratch/<type>.schema.json` before writing. An invalid record is rejected with the schema error — fix the record, never the file. Accepted records are written in canonical form: fields in schema declaration order (`type`, `req_id`, `ts`, `author` first, payload next, optional fields last), one record per line, newline-terminated. On success `append` prints the new record's line number — use it for later `responding_to` references. `next-retry` implements the Build-Failure Recovery counting rule: build-failure records for the `req_id` after the latest design-block line, plus one. Exit codes: 0 success, 1 validation or parse error, 2 usage error, 3 no matching record. The `grader-features` record is the one exception: `score-change.py extract` appends it directly under its own determinism contract.

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
6. If a feature-implementer dispatch ended without appending a `build-pass` or `build-failure` record, apply the "Truncation Recovery" procedure — continue the same slice; re-split only on the Pre-Check over-size branch or on non-convergence.
7. After every roster reviewer's latest `review-feedback` verdict is `"approved"`, the feature is complete: recommend dispatching the `change-grader` agent (terminal, advisory). The grader assesses how much human attention the passing change deserves; its `clear`/`concern` verdict is recorded and surfaced to the session, but it does **not** route and is **not** a merge or correctness gate. Do not consume its verdict for any routing decision.

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
    |                     v (all roster review-feedback verdicts: approved)
    |               change-grader (terminal, advisory)
    |               (extract → grade diff → record grader-verdict)
    |                     |
    |                     v
    |               Feature complete (human merges; grader verdict is advisory)
    |
    +--- Bug fix (known) --> feature-implementer (shortcut)
    +--- Architecture Q ---> system-design-expert (single agent)
    +--- Code review ------> All reviewers (parallel)
```
