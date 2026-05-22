# Agentic Harness

This document is the short, self-contained introduction to the specialist agent harness used by this project. It defines what the harness is, the iteration shape it runs, the agents that play roles in it, and the handoff contract that connects them.

For the inner-loop methodology, see [`tdd-principles.md`](tdd-principles.md). For the full record schemas, see [`../schemas/scratch/`](../schemas/scratch/).

## What the Harness Gives You

A pipeline of specialist agents — each with isolated context, a single responsibility, and a defined handoff contract — that turns a feature request into reviewed, tested, mergeable code. The coordinator routes; the specialists produce. Every handoff is a file on disk so the pipeline is auditable, interruptible, and survives session crashes.

The harness is **shape-stable, content-agnostic**: the same loop model, the same agent roles, the same JSONL contract apply whether the codebase is Go, Java, Rust, or anything else. Language-specific behavior lives in the per-project skills (`code-quality-review`, `test-review`, `prd-authoring`).

## The Three Nested Loops

The pipeline runs as three concentric loops, not a linear handoff. Each has one entry, one defined iteration unit, and one exit.

| Loop | Entry | Iterates over | Exit |
|---|---|---|---|
| Outer | User request or open work | One slice at a time | Slice committed, gates passed |
| Middle | A selected slice | The acceptance criterion that defines the slice | `prd-entry` + `design-block` records in `.scratch/handoff.jsonl` |
| Inner | Design approved for the slice | One behavior at a time (Red → Green → Refactor) | All tests green, self-review walked, quality gate passed |

### The Callback Property

The inner loop's design-check step may call back to the middle loop (system-design-expert) or the outer loop (product-requirements-expert) mid-cycle. That callback **is the loop nesting — it is not rework**.

A genuine rework signal is a reviewer rejection of a committed artifact (a `review-feedback` record with `verdict: "changes_requested"`), not an upstream callback from an in-flight inner cycle.

This distinction matters for interpreting pipeline metrics: a high count of system-design-expert dispatches across a feature's lifetime usually reflects the nested-loop callbacks working as designed, not the design being repeatedly rejected.

### Requirements and Slices Are Different Layers

Slicing is an **implementation discipline**, not a way of organising the PRD. Two layers coexist:

| Layer | What it captures | Where it lives | Granularity | Lifetime |
|---|---|---|---|---|
| **Requirement** | A coherent product capability — what users eventually get | One REQ-XX-NNN section in `docs/prd.md` | One REQ per capability (may be large; may carry many acceptance criteria) | Durable; status evolves Proposed → Approved → Implemented |
| **Slice** | One unit of implementation work the inner loop can complete in one cycle | One `prd-entry` record in `.scratch/handoff.jsonl` | One slice per dispatch (may be a subset of a REQ's acceptance criteria) | Ephemeral; consumed by one inner-loop cycle |

`docs/prd.md` stays domain-coherent — one REQ entry per capability, preserved across many implementation sessions. A large REQ-XX-NNN is implemented across multiple sessions, each shipping one slice (one `prd-entry` record). Multiple `prd-entry` records may target the same `req_id` over time; the handoff log accumulates the slice trail.

### What a Slice Is

A slice is the unit of the outer loop — one `prd-entry` record. Slices are **Goldilocks-sized** — small enough to ship in one inner-loop sequence, large enough that coordination overhead pays for itself.

A right-sized slice:

- carries one acceptance set (a coherent subset of one REQ's `acceptance_criteria`, all shipping together)
- ships standalone — independently grabbable, reviewable, mergeable
- fits one TDD plan — typically **3–10 TDD cycles**
- has a behavioral name a stranger could understand from the title alone

Both ends of the range are failure modes:

- **Too big.** The inner loop can't complete in one session; design changes mid-implementation; rework climbs; long diffs miss reviewer attention. Symptom: the slice becomes a unit of refactoring, not a unit of value.
- **Too small.** Overhead (PRD lookup + design block + TDD plan + 4 reviews + eval) dominates the work. Symptom: artificial decomposition obscures intent; commits ship fragments instead of behavior.

**Splitting test (too big).** If a strict subset of the slice's acceptance criteria could ship standalone and be useful, split: write a second `prd-entry` record (same `req_id` or a new one, depending on whether the REQ itself needs to be split) covering the second slice.

**Batching test (too small).** If a candidate slice would take 1–2 TDD cycles and only makes sense alongside a sibling slice (whether under the same REQ or a related REQ), merge into one `prd-entry` covering both.

Slice-sizing applies to the `prd-entry` record at dispatch time, not to the REQ-XX-NNN in `docs/prd.md`. The PRD captures what's wanted; the handoff record captures how much of it is being built in this round. The `prd-authoring` skill enforces this when authoring the handoff record; the `next` skill re-checks it when selecting what to work on next.

### Where Each Loop Lives

| Loop | Skill that drives it | Agent that owns it |
|---|---|---|
| Outer | `next` (selection); `pipeline-coordinator` agent's routing | The human or the coordinator |
| Middle | `prd-authoring`, `design-validation` | product-requirements-expert, system-design-expert |
| Inner | `tdd-workflow` (including the design-check decision tree) | feature-implementer |

The design-check decision tree in `tdd-workflow` is the mechanism that wires the inner loop to the middle and outer loops. Its five branches (Ready, Small code gap, Design gap, Requirement gap, Architecture misfit) are the callback edges of the nesting.

## Specialist Agents

The harness has eight agents. Each has a single role and a constrained write scope.

| Agent | Role | Writes |
|---|---|---|
| `pipeline-coordinator` | Routes work based on `.scratch/` state; never implements | `.scratch/handoff.jsonl` state only |
| `product-requirements-expert` | Captures *what* (per slice) and *what-not* (non-goals) | `docs/prd.md`, `docs/ubiquitous-language.md`, non-goal ADRs, `prd-entry` records |
| `system-design-expert` | Captures *how* (architecture, patterns, guardrails) | `docs/system-design.md`, `docs/adr/`, `design-block` records |
| `feature-implementer` | Runs the inner loop (TDD); only agent that writes source | source code, `.scratch/implementation-plan.md`, `build-failure` / `build-pass` records |
| `security-reviewer` | Threat model, sensitive-data handling, supply chain | `review-feedback` records (`author: "security-reviewer"`) |
| `code-quality-reviewer` | Language-specific code quality | `review-feedback` records (`author: "code-quality-reviewer"`) |
| `test-reviewer` | Test quality, coverage, edge cases | `review-feedback` records (`author: "test-reviewer"`) |
| `doc-reviewer` | Documentation correctness, cross-document coherence | `review-feedback` records (`author: "doc-reviewer"`) |

The four reviewers run in parallel after `build-pass`. All four must approve (`verdict: "approved"`) before the feature is eval'd and the pipeline closes.

## Handoff Contract

Every transition is an append-only JSON record on a single line of `.scratch/handoff.jsonl`. The coordinator validates each new record against its schema before dispatching the next agent.

| Record `type` | Producer | Schema |
|---|---|---|
| `prd-entry` | product-requirements-expert | `schemas/scratch/prd-entry.schema.json` |
| `design-block` | system-design-expert | `schemas/scratch/design-block.schema.json` |
| `build-failure` | feature-implementer | `schemas/scratch/build-failure.schema.json` |
| `build-pass` | feature-implementer | `schemas/scratch/build-pass.schema.json` |
| `review-feedback` | each reviewer (with their `author` value) | `schemas/scratch/review-feedback.schema.json` |

The append-only discipline gives the pipeline a replayable audit trail. Malformed records bounce back to the upstream agent before the next dispatch is consumed.

## Document Architecture

The pipeline reads from and writes to a small set of long-lived documents. Each has a single owner and a defined cadence.

| Document | Captures | Owner | Cadence |
|---|---|---|---|
| `docs/ubiquitous-language.md` | Domain vocabulary (DDD) | product-requirements-expert | Slow |
| `docs/prd.md` | *What* the system does (current state, per slice) | product-requirements-expert | Per slice |
| `docs/system-design.md` | *How* the system is built (current state, guardrails) | system-design-expert | Architectural events |
| `docs/adr/*.md` | *Why* decisions were made (immutable log) | system-design-expert (architectural ADRs); product-requirements-expert (non-goal ADRs) | Append-only |
| `docs/documentation-standards.md` | Ownership rules, validation checklist, writing standards | Human / repo owner | Slow |
| `docs/tdd-principles.md`, `docs/ddd-principles.md`, `docs/testing-principles.md`, this doc | Methodology | Mirrored from monorepo root | Slow |

PRDs and system-design are **projections of current state** — concise, consistent, coherent, current. Rationale lives in ADRs, referenced via `**Design Rationale:** [ADR link]`. The ubiquitous language is the shared vocabulary all documents and source code use.

## Where the Deeper Docs Live

- Inner-loop methodology and the eight-clause conjunctive bar: [`tdd-principles.md`](tdd-principles.md)
- DDD application (modules, aggregates, value objects): [`ddd-principles.md`](ddd-principles.md)
- Test structure, naming, mocking policy: [`testing-principles.md`](testing-principles.md)
- Document ownership table and validation checklist: [`documentation-standards.md`](documentation-standards.md)
