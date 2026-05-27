---
name: prd-authoring
description: >-
  PRD format conventions, boundary rules, and template references.
  Load when writing or reviewing product requirements.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
metadata:
  version: "1.0"
  author: team
---

## Pipeline Position

This skill operates inside the **middle loop** of the four-nested-loop pipeline (inner / middle / outer / architectural). A `prd-entry` record scopes one slice for the inner loop to implement. See [`docs/agentic-harness.md`](../../../docs/agentic-harness.md) for the loop model and the slice definition.

## PRD Location

The PRD lives at `docs/prd.md`. The canonical domain vocabulary lives at `docs/ubiquitous-language.md`.

## Ubiquitous Language Discipline

The ubiquitous language is durable memory — the agent's vocabulary across sessions and across other developers' agent teams. Treat it as load-bearing.

**Inline updates.** When a domain term resolves during a requirements interview, append it to `docs/ubiquitous-language.md` right then. Do not batch; do not defer to a second-use gate. A term has resolved when the user has committed to a specific word for a specific concept and the conversation has used it intentionally.

**Term-drift challenge.** When the user introduces a term that conflicts with an existing entry in `docs/ubiquitous-language.md`, call it out mid-conversation: name the existing definition, name the apparent new meaning, ask which is intended. Do not silently absorb the drift into the PRD.

**Entry format.** Each entry has a one-sentence definition; an optional `Relationships:` line; an optional `Avoid:` line listing terms-not-to-use for the same concept. An example dialogue at the bottom of the file shows several terms interacting in a worked exchange. See `docs/ubiquitous-language.md` itself for the format header.

**Forbidden:** drafting the PRD with terms not in `docs/ubiquitous-language.md`. If a needed term is missing, write it first.

## PRD Boundary Rule

The PRD describes *what* the system does. It must not contain *how*. It must not contain *why* — rationale lives in ADRs, referenced via the `**Design Rationale:**` link.

**Litmus test (what/how):** If it would change when switching from Java to another language, it belongs in `docs/system-design.md`, not the PRD.

**Litmus test (state/history):** If it explains *why* a decision was made (alternatives considered, trade-offs evaluated), it belongs in an ADR, not the PRD.

When the PRD needs to reference implementation details:
```markdown
**Implementation:** See [system-design.md#section](system-design.md#section)
```

When the PRD needs to reference the rationale for a decision:
```markdown
**Design Rationale:** See [ADR: Title](adr/YYYY-MM-DD-title.md)
```

## Two Layers: Requirements and Slices

**Requirements live in `docs/prd.md`.** Each REQ-XX-NNN captures one coherent product capability — what users eventually get. A requirement may carry many acceptance criteria and may take multiple sessions to fully implement. The PRD is the durable, current-complete-state projection of what the system does; it is not segmented by slices.

**Slices live in `.scratch/handoff.jsonl` as `prd-entry` records.** Each record is one unit of implementation work the inner loop can complete in one cycle. Multiple `prd-entry` records may target the same `req_id` over time — each shipping one slice of the requirement.

A `prd-entry` record may carry a *subset* of its REQ-XX-NNN's `acceptance_criteria` — the subset that's being implemented in this round. The PRD entry stays domain-coherent; the handoff record stays inner-loop-sized.

## Slice-Sizing Rule

The slice rule applies to **`prd-entry` records** (units of work), not to REQ entries (units of intent). Each `prd-entry` is a **right-sized vertical slice** — it cuts through every architectural layer the behavior actually touches, and is small enough to ship in one inner-loop sequence while large enough that coordination overhead pays for itself.

A right-sized vertical slice satisfies all six:

- Cuts through every architectural layer the behavior actually touches — no layer-only slices ("just the repository", "just the controller").
- Has a **single primary deliverable surface** — one of: code change, documentation change, schema change, configuration change. Tests for the primary surface count as part of it. A slice that bundles multiple surfaces ("implement the code AND update the PRD AND write an ADR AND regenerate goldens") burns the inner loop's context budget on surface-switching rather than depth — split it.
- The `acceptance_criteria` you include ship as a single unit — no useful subset ships earlier.
- Implementable in one TDD plan, typically **3–10 cycles**.
- Behaviorally named (the `title` would make sense to a stranger reading it cold — "User can log in with email and password," not "Add LoginController").
- Independently reviewable and mergeable.

Both ends of the size range are failure modes:

- **Too big.** Inner loop can't complete in one session; design churns mid-implementation. **Splitting tests:** (1) if a strict subset of the included `acceptance_criteria` could ship standalone and be useful, append a second `prd-entry` record covering the second slice (same `req_id` is fine — you're slicing one requirement across multiple work cycles); (2) if the slice spans multiple deliverable surfaces, split by surface — each surface becomes its own `prd-entry`.
- **Too small.** Pipeline overhead (PRD lookup + design + TDD + 4 reviews + eval) dominates the work. **Batching test:** if the slice would honestly take only 1–2 TDD cycles AND only makes sense alongside a sibling, write one `prd-entry` covering the combined work instead of two trivial ones.

Slice-sizing is enforced at this skill (write-time, when authoring a `prd-entry`); the `next` skill applies the same tests at selection time. See [`docs/agentic-harness.md`](../../../docs/agentic-harness.md) for the full loop model and the two-layer model.

## Prohibited Patterns in PRD

| Pattern | Severity | Fix |
|---|---|---|
| Java code blocks (` ```java `) | Critical | Move to system-design.md, link from PRD |
| Java-specific constructs (annotations, streams, lambdas, Spring APIs) | Critical | Describe behavior, not mechanism |
| Rationale prose (paragraphs explaining *why* a requirement or non-goal exists) | Critical | Move reasoning to an ADR; reference via `**Design Rationale:** [ADR link]` (link only, no inline reasoning) |
| Internal code references (class names, method names, variable names) | High | Use behavioral language |
| Algorithm formulas or pseudocode | High | State behavioral constraints, move formulas to system-design.md |
| Regex patterns | High | Describe behavior, not mechanism |
| Hardcoded constant values | Medium | Reference system-design.md#constants |

## Requirement Format

Use the "Parseable Section Templates" requirement format in `docs/documentation-standards.md`.

## Feature Handoff Record (product-requirements-expert → system-design-expert)

When a feature is approved, append one record to `.scratch/handoff.jsonl` describing the scope. The record is the structured contract that system-design-expert consumes; the markdown PRD entry in `docs/prd.md` remains the human-authored source of truth.

**File:** `.scratch/handoff.jsonl` (append-only; one JSON object per line, terminated by `\n`).

**Schema:** [`schemas/scratch/prd-entry.schema.json`](../../../schemas/scratch/prd-entry.schema.json). The pipeline-coordinator validates each record against the schema at the product-requirements-expert→system-design-expert transition; malformed records bounce back to you without consuming an system-design-expert dispatch.

**Required fields:**

| Field | Type | Notes |
|---|---|---|
| `type` | `"prd-entry"` | Discriminator. |
| `req_id` | string `^REQ-[A-Z]+-[0-9]{3}$` | Matches the PRD heading. |
| `ts` | ISO 8601 string | Timestamp at append. |
| `author` | `"product-requirements-expert"` | Pinned. |
| `title` | string | Short requirement title. |
| `summary` | string ≤ 400 chars | One- or two-sentence statement. No implementation details. |
| `acceptance_criteria` | array of strings | Testable conditions. At least one. |
| `file_targets` | array of strings | Paths likely to be touched. At least one. Best-effort; system-design-expert may revise. |
| `test_names` | array of strings matching `^[a-z][A-Za-z0-9_]*$` | JUnit test methods expected to exist (camelCase, e.g. `theResultShouldContainNewItems`). At least one. |

**Optional fields:** `non_goals`, `dependencies` (other req_ids), `notes`.

**Append-only discipline:** Read the file first if it exists. Preserve every prior line verbatim. Append your new record as the last line. Never edit, reorder, or delete prior records. If a prior record has a mistake, append a new record that supersedes it.

**Why JSONL, not markdown:** see [`docs/adr/2026-05-08-append-only-jsonl-handoffs.md`](../../../docs/adr/2026-05-08-append-only-jsonl-handoffs.md). The structural-rejection gate this enables converts system-design-expert retries into cheap upstream bounces before a Sonnet/Opus dispatch is consumed.

### Example Record

```json
{"type":"prd-entry","req_id":"REQ-XX-099","ts":"2026-05-08T12:00:00Z","author":"product-requirements-expert","title":"Cache miss diagnostics","summary":"Surface per-component cache miss rate so operators can spot reinjection hotspots.","acceptance_criteria":["report renders cacheMissRate per component","value matches cacheCreation/(cacheCreation+cacheRead)"],"file_targets":["src/main/java/com/example/reference/report/SummaryReport.java","src/test/java/com/example/reference/report/SummaryReportTest.java"],"test_names":["theSummaryShouldRenderCacheMissRate"],"non_goals":["historical trend"]}
```

## Writing Standards

Follow the Writing Standards section in `docs/documentation-standards.md`.
