# Agentic Harness

This document is the short, self-contained introduction to the specialist agent harness used by this project. It covers the harness's purpose, supporting disciplines, iteration shape, agent roles, and handoff contract.

For the inner-loop methodology, see [`tdd-principles.md`](tdd-principles.md). For the full record schemas, see [`go/schemas/scratch/`](../go/schemas/scratch/) (the Java sample carries a byte-equivalent copy).

## What the Harness Is For

AI coding agents face the same two challenges human engineers always have: keeping **long-term memory** across sessions, and running **multi-scale feedback loops** that catch drift before it compounds. The difference is degree, not kind. A human forgets between Friday and Monday; an agent forgets between one message and the next. A human catches drift through pairing, review, and CI; an agent needs the same checks, written into the same artifacts, run at the same cadences.

Within days — not years — an agentic project that skips these disciplines starts drifting. Terms get picked inconsistently session-to-session, settled decisions get re-litigated, architectural choices contradict the ones made last week. The same drift happens to human-only teams over months. Agents amplify the cost of *not* doing the disciplines that compensate.

The harness treats the engineering disciplines humans already developed — documentation standards, DDD, TDD, ADRs, ubiquitous language, XP-style nested feedback loops — as the **memory and feedback substrate**. Humans and agents both rely on this substrate when working on the same codebase. Agents write to and read from it as they work; the artifacts survive across sessions and across developers.

## Harness Invariants

The harness is the deployable product. Three invariants follow.

**1. Self-containment: no ADR or REQ references in harness prose.** Files under `.claude/` (agent prompts, skills, templates) and `schemas/scratch/` must function without `docs/adr/` or `docs/prd.md` being reachable. The harness states *what* to do; ADRs capture *why* the decision was made; the PRD captures *what is wanted*. Coupling the deployable to project-specific historical records breaks the harness when it deploys into a downstream project that does not carry them.

- Agent prompts, skills, and schema descriptions do not link to or cite `docs/adr/*.md`, nor do they cite REQ-XX-NNN identifiers from `docs/prd.md`.
- ADRs may freely reference each other, the PRD, the system-design doc, and the harness — the dependency direction is harness-from-ADR, never ADR-into-harness.
- Adding a *what* to the harness (new contract, new verdict, new field) lands with its *why* in an ADR; the harness picks up the contract by name only. The ADR's existence is not the harness's concern.
- Mentions of `docs/adr/` as a *write target* or *path pattern* are not citations and are fine (system-design-expert writes ADRs; doc-reviewer reads ADRs; the autofix protocol operates on `docs/adr/*.md`).

**2. Tool-agnostic prose: no runtime-specific numbers in harness text.** The harness must work on whatever runtime the host project uses — Claude Code, Copilot, Cursor, OpenCode. Numbers reflecting one runtime's characteristics (Claude's 60-tool-call-per-message cap, a specific `toolCallBudget` value of 40) are false on others. They belong in per-agent front-matter where they are per-deployment configuration, not in prose where they read as universal facts.

- Agent prose uses generic phrasing. Canonical: "Your tool-call budget (`toolCallBudget` in your front-matter) caps this dispatch." Variants like "your runtime's tool-call ceiling" or "within budget" fit when the cadence calls for them.
- Concrete numerical values live in agent front-matter (`toolCallBudget: NN`, `maxTurns: NN`). Per-deployment configuration.
- Skills explaining budget mechanisms refer to `toolCallBudget` as a *name* (it is a per-agent metadata field), never as a specific value.
- Harness-level structural constants (3-retry cycle, 4 reviewers, 6 verdicts) are fine — those are harness invariants, not runtime accidents.

**3. Editing the harness bypasses the harness pipeline.** Changes to files under `.claude/` and `schemas/scratch/` are applied directly by root, the human session driver. They are not routed through `product-requirements-expert` → `system-design-expert` → `feature-implementer`. Two reasons make this mandatory: the dispatched specialists *are* the artifacts being changed (circular dependency), and mid-flight contract changes would break the in-flight dispatches that the pipeline depends on. Bypassing the pipeline does not bypass the project's standards.

- The same writing standards from `docs/documentation-standards.md` apply — clear prose, no padding, sentence-level discipline.
- The same thinness applies — agents stay focused, skills cover one concern, schemas describe just enough to validate.
- Invariants 1 and 2 above apply to the new content (no ADR/REQ refs in prose; no runtime-specific numbers in prose).
- The project's quality gate still runs to verify code health even when the change touches only harness files.
- A harness change earns an ADR in `docs/adr/` for its rationale; user-visible behaviour changes also earn a PRD entry. The harness picks up the *what* by name only — the ADR's existence is not the harness's concern (per invariant 1).
- The audit trail for a bypass-edit is git (commit message + ADR), not `.scratch/handoff.jsonl` (the latter is the pipeline's medium, used only when the pipeline runs).

Together these invariants keep the harness portable (1, 2) and safely self-modifiable (3). A project adopting the harness picks up the `.claude/` and `schemas/` directories. The ADRs are optional documentation, and the per-agent budgets get tuned for the host runtime. Changes to the harness itself follow the bypass-edit discipline rather than dispatching through agents that may be mid-modification.

## Principles Over Rigid Rules

**Status:** Adopted 2026-06-03.

Harness prose carries two kinds of instruction, written differently. The split follows Anthropic's [Claude constitution](https://www.anthropic.com/news/claude-new-constitution): keep hard constraints for high-stakes behaviors, and for everything else explain *why* a behavior is wanted so the agent generalizes to cases no rule anticipated. Rigid rules "can be applied poorly in unanticipated situations or when followed too rigidly" — the failure mode a specialist hits when it meets a case the checklist never named.

- **Hard contract.** Coordination correctness depends on exact compliance — schema shapes, append-only records, `dispatch-start` as the first tool call, the routing-signal table, write scopes, and the three invariants above. Write these as bare imperatives. Do not soften them into preferences. They are the harness's high-stakes constraints; the stake is replayable, cross-runtime determinism.
- **Judgment.** The agent must classify, size, or decide where no enumeration is complete. These surfaces include the six triage verdicts, the design-check decision tree, review-feedback tags, the slice-sizing tests, the consultation push-versus-escalate call, and each agent's role scope. Attach one compact rationale clause to each such instruction. An agent that knows what a verdict protects applies it to a case the list never named; an agent given only the list guesses.

Authors classify each instruction before writing it. A hard contract stays a bare imperative. A judgment instruction carries its reason in one clause, not a paragraph. The deterministic spine stays rigid while the judgment surfaces gain enough intent to generalize. The writing standards still govern — imperative mood, one idea per sentence, no padding (see [`documentation-standards.md`](documentation-standards.md)).

## Disciplines as Memory and Feedback

Memory comes in two tiers. **Long-term memory** lives in `docs/` — durable specs that evolve across features. **Working memory** lives in `.scratch/` — the per-feature event log that holds the active state. Each artifact in either tier plays a memory role, a feedback role, or both. Together they give the project a continuous mental model that no single session has to hold.

| Artifact | Memory role | Feedback role |
|---|---|---|
| `docs/prd.md` | What the system is meant to do | Acceptance criteria for the inner loop |
| `docs/system-design.md` | How the system is structured — invariants, patterns, guardrails | Triage validates new slices against it |
| `docs/adr/*.md` | Why decisions were made; what was rejected (including non-goal ADRs) | Architectural review catches drift from committed decisions |
| `docs/ubiquitous-language.md` | Project vocabulary; terms to avoid; relationships | Inline term-drift challenge catches misuse mid-conversation |
| Tests (TDD) | Behavioral expectations that survive | Red → green → refactor at seconds-to-minutes |
| Quality gate (build, test, lint, deps-check) | Records what currently passes | Catches regressions on every build |
| Review records (`review-feedback`) | Audit trail of objections raised | Block merge until addressed |
| Handoff log (`.scratch/handoff.jsonl`) | Per-feature audit trail of every transition | Each record is schema-validated before the next dispatch |

The handoff log is the project's **working memory** — within-feature state. The documents under `docs/` are its **long-term memory** — durable across features. The implementer reads both but writes to long-term memory only through the agent that owns each document.

## Nested Feedback Loops Drive Design Discovery

TDD produces good code when each cycle is fast enough to test a design hypothesis. Nested feedback loops at multiple timescales (the structure XP introduced) supply that rhythm. Each level is tight enough that decisions get tested, refactored, and propagated before the next layer commits. The harness runs four concentric loops; each loop surfaces a different layer of design question.

| Loop | Timescale | What design question it surfaces |
|---|---|---|
| Inner | seconds–minutes | What does this behavior need? (Interface design via red → green → refactor) |
| Middle | hours | What does this slice deliver? (Acceptance design + system-design adjustments) |
| Outer | days | What slice should we build next? (Feature design + slice sizing) |
| Architectural | months | Is the whole codebase still well-shaped? (Structural review — planned) |

Good interfaces, good architecture, and good tests fall out of running these loops with discipline. The tests aren't the goal of TDD; they're the evidence of decisions made at each scale, surviving as behavioral memory for the next session. Skipping a loop doesn't just lose feedback — it loses the design discovery the loop produces.

### Design Is Discovered, Not Planned

This is a deliberate commitment. The PRD captures intent; `system-design.md` captures invariants and patterns the codebase has discovered so far; ADRs capture decisions actually made. But the shape of any given slice — its interfaces, internal structure, which abstractions earn their keep — is discovered through the inner loop, not specified upfront. The starting design block is a hypothesis the inner loop is free to revise. When the loop discovers something worth recording, the route back to `system-design-expert` updates long-term memory and the next slice inherits it.

The risk of emergent design — inconsistent patterns across slices, structural decay — is what the long-term memory (invariants, vocabulary, ADRs) and the architectural loop are for. Constraints stay locked; structure stays free to be discovered.

### Where Each Loop Lives

| Loop | Skill that drives it | Agent that owns it |
|---|---|---|
| Inner | `tdd-workflow` (including the design-check decision tree) | feature-implementer |
| Middle | `prd-authoring`, `design-validation` | product-requirements-expert, system-design-expert |
| Outer | `next` (selection); `pipeline-coordinator` routing | The human or the coordinator |
| Architectural | (planned) | system-design-expert |

The design-check decision tree in `tdd-workflow` is the mechanism that wires the inner loop to the middle and outer loops. Its branches map to the triage verdicts the system-design-expert returns (`covered`, `minor`, `new`, `foundational`, `conflicting`, `refactor-first`) plus the on-demand consultation interface.

### Requirements and Slices Are Different Layers

Slicing is an **implementation discipline**, not a way of organising the PRD. Two layers coexist:

| Layer | What it captures | Where it lives | Granularity | Lifetime |
|---|---|---|---|---|
| **Requirement** | A coherent product capability — what users eventually get | One REQ-XX-NNN section in `docs/prd.md` | One REQ per capability (may be large; may carry multiple acceptance criteria) | Durable; status evolves Proposed → Approved → Implemented |
| **Slice** | One unit of implementation work the inner loop can complete in one cycle | One `prd-entry` record in `.scratch/handoff.jsonl` | One slice per dispatch (may be a subset of a REQ's acceptance criteria) | Ephemeral; consumed by one inner-loop cycle |

`docs/prd.md` stays domain-coherent — one REQ entry per capability, preserved across multiple implementation sessions. A large REQ-XX-NNN is implemented across multiple sessions, each shipping one slice (one `prd-entry` record). Multiple `prd-entry` records may target the same `req_id` over time; the handoff log accumulates the slice trail.

### What a Slice Is

A slice is the unit of the outer loop — one `prd-entry` record. Slices are **vertical slices**. Each one cuts through every architectural layer the behavior touches — domain types, business logic, persistence, transport, wiring — and ships as a coherent, independently usable unit. The size sweet spot is small enough to complete in one inner-loop sequence, large enough that coordination overhead pays for itself.

A right-sized vertical slice:

- cuts through every architectural layer the behavior actually touches — no layer-only slices ("just the repository", "just the handler")
- carries one acceptance set (a coherent subset of one REQ's `acceptance_criteria`, all shipping together)
- ships standalone — independently grabbable, reviewable, mergeable
- fits one TDD plan — typically **3–10 TDD cycles**
- has a behavioral name a stranger could understand from the title alone

Both ends of the range are failure modes:

- **Too big.** The inner loop can't complete in one session; design changes mid-implementation; rework climbs; long diffs miss reviewer attention. Symptom: the slice becomes a unit of refactoring, not a unit of value.
- **Too small.** Overhead (PRD lookup + design triage + TDD plan + 4 reviews + eval) dominates the work. Symptom: artificial decomposition obscures intent; commits ship fragments instead of behavior.

**Splitting test (too big).** If a strict subset of the acceptance criteria could ship standalone and be useful, split. Write a second `prd-entry` record covering the second slice — same `req_id` if the REQ holds together, a new one if the REQ itself needs splitting.

**Batching test (too small).** If a candidate slice would take 1–2 TDD cycles and only makes sense alongside a sibling slice, merge into one `prd-entry` covering both. Siblings may share a `req_id` or live under related REQs.

Slice-sizing applies to the `prd-entry` record at dispatch time, not to the REQ-XX-NNN in `docs/prd.md`. The PRD captures what's wanted; the handoff record captures how much of it is being built in this round. The `prd-authoring` skill enforces this when authoring the handoff record; the `next` skill re-checks it when selecting what to work on next.

## Specialist Agents

The harness has eight agents. Each has a single role and a constrained write scope.

| Agent | Role | Writes |
|---|---|---|
| `pipeline-coordinator` | Routes work based on `.scratch/` state; never implements | `.scratch/handoff.jsonl` state only |
| `product-requirements-expert` | Captures *what* (per slice) and *what-not* (non-goals); maintains the ubiquitous language | `docs/prd.md`, `docs/ubiquitous-language.md`, non-goal ADRs, `prd-entry` records |
| `system-design-expert` | Holds the cross-feature view; triages slices against long-term memory; consulted by the implementer on demand | `docs/system-design.md`, `docs/adr/`, `design-block` records, `consultation-response` records; `prd-entry` records only as the sibling-refactor entry under the `refactor-first` verdict |
| `feature-implementer` | Runs the inner loop (TDD); only agent that writes source | source code, `.scratch/implementation-plan.md`, `build-failure` (with optional `partial` or `abort_reason`) / `build-pass` / `consultation-request` records |
| `security-reviewer` | Threat model, sensitive-data handling, supply chain | `review-feedback` records (`author: "security-reviewer"`) |
| `code-quality-reviewer` | Language-specific code quality | `review-feedback` records (`author: "code-quality-reviewer"`) |
| `test-reviewer` | Test quality, coverage, edge cases | `review-feedback` records (`author: "test-reviewer"`) |
| `doc-reviewer` | Documentation correctness, cross-document coherence | `review-feedback` records (`author: "doc-reviewer"`) |

The four reviewers run in parallel after `build-pass`. All four must approve (`verdict: "approved"`) before the feature is eval'd and the pipeline closes.

Every agent in the table except `pipeline-coordinator` also appends a `dispatch-start` record to `.scratch/handoff.jsonl` as its first tool call — see § Dispatch-Event Contract and Recovery Paths below. The coordinator is exempt because its output is a routing recommendation in the response stream, not a substantive record.

### The system-design-expert role in depth

`system-design-expert` is the principal-or-senior-engineer archetype for the codebase: it holds the high-level, cross-feature view of how the system fits together, balancing product direction, technical fit, long-term evolution, and DDD discipline. Most of that view stays in the head; only the load-bearing parts get crystallized into long-term memory.

Two interaction modes, both demand-driven:

- **Triage** runs on every slice. The system-design-expert reads `docs/system-design.md`, the ADRs, the ubiquitous language, and the slice's `prd-entry`, then returns one of six verdicts:
  - `covered` — existing memory handles this; pointer to relevant sections; no writes.
  - `minor` — existing pattern with a small adjustment; brief note; possibly a small `system-design.md` update.
  - `new` — genuinely new design ground for this slice; the system-design-expert writes design work and possibly an ADR.
  - `foundational` — project-level foundational gaps detected (no architecture shape recorded, no language/framework ADR, empty ubiquitous language, slice touches a concern with no project-level pattern). The system-design-expert dialogues with the user to make the unrecoverable foundational decisions, writes them as long-term memory, then proceeds to the slice's own triage in the populated context.
  - `conflicting` — this slice conflicts with current design; surface to user; possibly non-goal ADR or PRD revision.
  - `refactor-first` — an independently-meaningful refactor must land before this slice can be implemented; the system-design-expert appends a refactor `prd-entry` alongside the `design-block`, the coordinator dispatches the refactor through the pipeline first, and the original slice's re-triage happens via a new `design-block` with `supersedes_record_at` after the refactor's `build-pass`.

  On a mature codebase, slices that fit existing patterns return `covered` in seconds; new design ground is the exception, not the rule. The `foundational` verdict applies to both greenfield projects (first slice) and projects being adopted by the harness (foundation work that was never written down). When adopting on an existing codebase, the foundational pass reads domain types and recurring terms in the existing artifacts to propose a candidate vocabulary. The user then confirms and refines before the system-design-expert writes `docs/ubiquitous-language.md`.

- **Consultation** runs on demand. When the inner loop discovers a question the triage didn't anticipate, `feature-implementer` appends a `consultation-request` record. The coordinator dispatches the system-design-expert in consultation mode. The system-design-expert reads the request and long-term memory, answers the specific question, and appends a `consultation-response` record — optionally recording new memory if the discovery is worth crystallizing. The coordinator then routes control back to the implementer to resume the inner loop.

Triage is the contract for what enters long-term memory on slice intake; consultation is the contract for what new discoveries get recorded mid-flight.

## Handoff Contract

Every transition is an append-only JSON record on a single line of `.scratch/handoff.jsonl`. The coordinator validates each new record against its schema before dispatching the next agent.

| Record `type` | Producer | Schema |
|---|---|---|
| `prd-entry` | product-requirements-expert | `schemas/scratch/prd-entry.schema.json` |
| `design-block` | system-design-expert | `schemas/scratch/design-block.schema.json` |
| `consultation-request` | any specialist mid-work (typically feature-implementer) | `schemas/scratch/consultation-request.schema.json` |
| `consultation-response` | the consulted specialist (product-requirements-expert or system-design-expert) | `schemas/scratch/consultation-response.schema.json` |
| `build-failure` | feature-implementer | `schemas/scratch/build-failure.schema.json` |
| `build-pass` | feature-implementer | `schemas/scratch/build-pass.schema.json` |
| `review-feedback` | each reviewer (with their `author` value) | `schemas/scratch/review-feedback.schema.json` |
| `design-doc-autofix` | root coordinator (audit trail for mechanical edits on design-doc paths) | `schemas/scratch/design-doc-autofix.schema.json` |
| `dispatch-start` | every substantive agent (as its first tool call); `pipeline-coordinator` exempt | `schemas/scratch/dispatch-start.schema.json` |

The append-only discipline gives the pipeline a replayable audit trail. Malformed records bounce back to the upstream agent before the next dispatch is consumed.

Consultation roundtrips preserve the requesting specialist's active state: after a `consultation-response`, the coordinator routes back to the requester, not forward to the next pipeline stage.

## Dispatch-Event Contract and Recovery Paths

Every dispatch is observable to the coordinator through `.scratch/handoff.jsonl` alone — no runtime telemetry, no transcript reading, no tool-specific signals. The contract has three parts.

**Start.** Every project-defined agent except `pipeline-coordinator` appends a `dispatch-start` record as its first tool call. The record names the agent (`author`) and the inbound record line(s) it is responding to (`responding_to` — 1-indexed line numbers in the handoff log).

**Stop.** The agent's substantive record (`build-pass`, `build-failure`, `review-feedback`, `prd-entry`, `design-block`, or `consultation-response`) acts as the implicit stop signal. A `dispatch-start` for `(req_id, author)` with no subsequent substantive record from the same `(req_id, author)` is the deterministic truncation signal — readable from filesystem state alone, portable across runtimes.

**Budget.** Each creator and verifier agent carries a `toolCallBudget` in its front-matter and runs a Scoping Pre-Check before the first tool call. The Pre-Check writes a tool-call estimate and a planned-checkpoint milestone into the transcript. If the estimate exceeds the budget, the dispatch stops and files a `consultation-request` (slice-too-big → `product-requirements-expert`; design-too-broad → `system-design-expert`) instead of starting. If the planned checkpoint fires before the work is complete, the agent emits a partial-artifact record before exiting. The implementer emits a `build-failure` with `partial: true`; reviewers emit a `review-feedback` with `verdict: "blocked"` plus a truncation `tag: "escalate"` finding.

The coordinator routes on the signals below. Every recovery path is grounded in records already in `.scratch/handoff.jsonl` — no out-of-band channel required.

| Signal | Recovery |
|---|---|
| `dispatch-start` without subsequent substantive record from same `(req_id, author)` | Truncation; route to `product-requirements-expert` for re-split |
| `build-failure` with `partial: true` | Partial-artifact handoff; re-dispatch implementer with the recorded progress; retry counter still ticks |
| `build-failure` with `abort_reason` set | Wrong-shape abort; short-circuit the retry counter (`wrong-shape-slice` → PRE for re-split; `design-mismatch` → SDE for re-triage; `prerequisite-missing` → human escalation) |
| `build-failure` with `retry < 3` (no `abort_reason`, no `partial`) | Re-dispatch implementer with the failure context |
| `build-failure` with `retry == 3` | Re-triage via `system-design-expert` with `supersedes_record_at`; the new `design-block` resets the retry counter |
| `design-block` with `verdict: "refactor-first"` | SDE has appended a sibling refactor `prd-entry`; the coordinator dispatches the refactor through the pipeline first; the original slice's re-triage happens via a new `design-block` with `supersedes_record_at` after the refactor's `build-pass` |
| `design-block` with `verdict: "conflicting"` | Halt; surface to human |
| `review-feedback` with `verdict: "blocked"` and a truncation `tag: "escalate"` finding | Reviewer hit its budget; route findings to implementer; re-invoke reviewers after the next `build-pass` |

Per-recovery detail, the validation gates, and the per-record schemas live in the `pipeline-handoff` skill; this table is the index.

**The detection rule is cause-agnostic.** A `dispatch-start` without a subsequent substantive record means the same thing regardless of cause — runtime cap-hit, mid-stream truncation, the agent abandoning the dispatch, or a network drop. The coordinator routes on the signal, not on the cause. Recovery row 1 (truncation → PRE re-split) applies to the implementer case verbatim. Analogous re-dispatch paths for other substantive agents follow the same shape, detailed in the `pipeline-handoff` skill. Within a session, multiple successive `dispatch-start` records for the same `(req_id, author)` resolve under the "latest record" rule. The latest `dispatch-start` is the live one — the same rule the coordinator uses for other record types. Cross-session staleness — `.scratch/` carrying records from yesterday's feature — is a separate concern handled by the `new-feature` skill, which clears `.scratch/` before the next feature cycle begins.

**Prevention before recovery.** The Scoping Pre-Check and the planned-checkpoint partial-artifact emission exist so the harness leaves a substantive record *before* hitting the runtime cap. They reduce reliance on recovery after a no-record truncation. A pre-check that estimates the dispatch over budget files a `consultation-request` (cheap re-scope) instead of starting. A planned checkpoint reached mid-work writes a partial `build-failure` (or partial `review-feedback`) before exiting. The recovery table above is the residual after prevention — the cases that slip through.

## Document Architecture

The pipeline reads from and writes to a small set of long-lived documents. Each has a single owner and a defined cadence.

| Document | Captures | Owner | Cadence |
|---|---|---|---|
| `docs/ubiquitous-language.md` | Domain vocabulary (DDD) | product-requirements-expert | Slow; inline updates as terms resolve |
| `docs/prd.md` | *What* the system does (current state, per slice) | product-requirements-expert | Per slice |
| `docs/system-design.md` | *How* the system is built (invariants and patterns, current state) | system-design-expert | Triage outcomes that warrant recording |
| `docs/adr/*.md` | *Why* decisions were made (immutable log) | system-design-expert (architectural ADRs); product-requirements-expert (non-goal ADRs) | Append-only |
| `docs/documentation-standards.md` | Ownership rules, validation checklist, writing standards | Human / repo owner | Slow |
| `docs/tdd-principles.md`, `docs/ddd-principles.md`, `docs/testing-principles.md`, this doc | Methodology | Mirrored from monorepo root | Slow |

PRDs and system-design are **projections of current state** — concise, consistent, coherent, current. Rationale lives in ADRs, referenced via `**Design Rationale:** [ADR link]`. The ubiquitous language is the shared vocabulary all documents and source code use.

## Where the Deeper Docs Live

- Inner-loop methodology and the eight-clause conjunctive bar: [`tdd-principles.md`](tdd-principles.md)
- DDD application (modules, aggregates, value objects): [`ddd-principles.md`](ddd-principles.md)
- Test structure, naming, mocking policy: [`testing-principles.md`](testing-principles.md)
- Document ownership table and validation checklist: [`documentation-standards.md`](documentation-standards.md)
