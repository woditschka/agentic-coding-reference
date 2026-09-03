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
reads:
  - docs/prd.md
  - docs/ubiquitous-language.md
metadata:
  version: "1.0"
  author: team
---

## Pipeline Position

This skill operates inside the **middle loop** of the four-nested-loop pipeline (inner / middle / outer / architectural). A `prd-entry` record scopes one slice for the inner loop to implement. See [`agentic-harness.md`](../handoff-routing/agentic-harness.md) for the loop model and the slice definition.

## PRD Location

The PRD lives at `docs/prd.md`. The canonical domain vocabulary lives at `docs/ubiquitous-language.md`.

## Ubiquitous Language Discipline

The ubiquitous language is durable memory — the agent's vocabulary across sessions and across other developers' agent teams. Treat it as load-bearing.

**Inline updates.** Domain terms resolve during the intake discussion (`agentic-harness.md` § Conversations Stay in Root; the `intake` skill runs it). A term has resolved when the human has committed to a specific word for a specific concept and the conversation has used it intentionally. The intake exit records every resolved term as a quoted decision in the `intake-decision` record; the product-requirements-expert appends them to `docs/ubiquitous-language.md` at dispatch, before drafting. Do not drop a resolved term from the record; do not defer an append to a second-use gate.

**Term-drift challenge.** When the human introduces a term that conflicts with an existing entry in `docs/ubiquitous-language.md`, root calls it out mid-conversation: name the existing definition, name the apparent new meaning, ask which is intended. A drift that reaches the dispatch unresolved returns as pushback, never absorbed silently into the PRD.

**Entry format.** Each entry has a one-sentence definition; an optional `Relationships:` line; an optional `Avoid:` line listing terms-not-to-use for the same concept. An example dialogue at the bottom of the file shows several terms interacting in a worked exchange. See `docs/ubiquitous-language.md` itself for the format header.

**Forbidden:** drafting the PRD with terms not in `docs/ubiquitous-language.md`. If a needed term is missing, write it first.

## PRD Boundary and Prohibited Patterns

Read [`boundary-rules.md`](boundary-rules.md) before writing or judging any PRD content — the what/how/why boundary rule, its litmus tests, and the closed prohibited-pattern table live there, shipped beside this file.

## Two Layers: Requirements and Slices

**Requirements live in `docs/prd.md`.** Each REQ-XX-NNN captures one coherent product capability — what users eventually get. A requirement may carry many acceptance criteria and may take multiple sessions to fully implement. The PRD is the durable, current-complete-state projection of what the system does; it is not segmented by slices.

**Slices live in `.scratch/handoff.jsonl` as `prd-entry` records.** Each record is one unit of implementation work the inner loop can complete in one cycle. Multiple `prd-entry` records may target the same `req_id` over time — each shipping one slice of the requirement.

A `prd-entry` record may carry a *subset* of its REQ-XX-NNN's `acceptance_criteria` — the subset that's being implemented in this round. The PRD entry stays domain-coherent; the handoff record stays inner-loop-sized.

## Slice-Sizing Rule

The slice rule applies to **`prd-entry` records** (units of work), not to REQ entries (units of intent). Each `prd-entry` is a **right-sized vertical slice** — it cuts through every architectural layer the behavior actually touches, and is small enough to ship in one inner-loop sequence while large enough that coordination overhead pays for itself.

A right-sized vertical slice satisfies all six:

- Cuts through every architectural layer the behavior actually touches — no layer-only slices ("just the repository", "just the entry point").
- Has a **single primary deliverable surface** — one of: code change, documentation change, schema change, configuration change. Tests for the primary surface count as part of it. A slice that bundles multiple surfaces ("implement the code AND update the PRD AND write an ADR AND regenerate goldens") burns the inner loop's context budget on surface-switching rather than depth — split it.
- The `acceptance_criteria` you include ship as a single unit — no useful subset ships earlier.
- Implementable in one TDD plan, typically **3–10 cycles**.
- Behaviorally named (the `title` would make sense to a stranger reading it cold — "User can log in with email and password," not "Add a login handler").
- Independently reviewable and mergeable.

Both ends of the size range are failure modes:

- **Too big.** Inner loop can't complete in one session; design churns mid-implementation. **Splitting tests:** (1) if a strict subset of the included `acceptance_criteria` could ship standalone and be useful, append a second `prd-entry` record covering the second slice (same `req_id` if the REQ holds together — you're slicing one requirement across multiple work cycles; a new `req_id` if the REQ itself needs splitting); (2) if the slice spans multiple deliverable surfaces, split by surface — each surface becomes its own `prd-entry`.
- **Too small.** Pipeline overhead (PRD lookup + design triage + TDD plan + roster reviews + change-grade) dominates the work. **Batching test:** if the slice would honestly take only 1–2 TDD cycles AND only makes sense alongside a sibling, write one `prd-entry` covering the combined work instead of two trivial ones. Siblings may share a `req_id` or live under related REQs.

Slice-sizing is enforced at this skill (write-time, when authoring a `prd-entry`); the `next` skill applies the same tests at selection time. See [`agentic-harness.md`](../handoff-routing/agentic-harness.md) for the full loop model and the two-layer model.

## Requirement Format

The PRD is **narrative prose**, not a catalog of structured entries. Write each capability area as a few sentences a newcomer reads top to bottom, and annotate each requirement inline with its ID where the prose expresses it. The prose carries intent; a short "Done when" list carries the bounded, testable contract.

This keeps the PRD human-readable and agent-parseable at once. It retires the per-requirement scaffolding — `Input`, `Output`, `Constraints`, `Depends On` — that duplicated the `prd-entry` handoff record and rotted against source (those are field tables in disguise; see `boundary-rules.md`).

### The five parts

1. **Narrative.** Prose grouped by capability area, describing what the system does. Tag each requirement inline where the prose states it: `` ... the tool runs as one command `[REQ-XX-NNN]`, and discovers configuration by precedence `[REQ-XX-MMM]` ``. IDs follow `REQ-[A-Z]+-[0-9]{3}` — exactly three digits, the pattern every handoff schema and gate enforces. The letter segment is the capability area's prefix the neighboring IDs already use (`REQ-OWN-`, `REQ-VIS-`). A new prefix opens only with a new capability group, and the number is one past the highest under that prefix; an ID is never reused.
2. **Anchor.** At a requirement's first mention, place `<a id="req-xx-nnn"></a>` (lowercase, hyphenated) on its own line, so ADRs and system-design deep-link to `prd.md#req-xx-nnn`.
3. **"Done when" acceptance.** After each capability group, a list whose every bullet opens with a requirement's `[REQ-ID]` and states one bounded outcome in plain given/when/then language. **The bullet is the contract** — the prose is context, the bullet is what "done" means and what the fresh-eyes reviewer judges against. Every REQ-ID must appear in at least one bullet (the doctor's `req-acceptance` check enforces this).
4. **Links.** `**ADR:** [ADR: Title](adr/...)` for the decision trail; `**Design:** [system-design.md#section](system-design.md#section)` for mechanism. Each only when it exists.
5. **Edge cases** (when the capability has them). A numbered `**Edge cases:**` list beside "Done when", one bounded case per item. The numbering is stable and citable: test comments reference it, the test-reviewer checks each number has a dedicated test, and the system-design expert verifies the design accounts for each. This list is the "documented edge cases" every downstream stage names.

### Worked example

```markdown
<a id="req-xx-nnn"></a>
The tool runs as a single automatic command: one invocation reads transcripts,
updates the manifest, and regenerates every report `[REQ-XX-NNN]`. Configuration
resolves by precedence — an explicit flag wins, otherwise built-in defaults
apply, and a flag pointing at a missing file is materialized, not failed
`[REQ-XX-MMM]`.

**Done when:**
- `[REQ-XX-NNN]` a no-flag run scans the default input, writes the reports, and
  prints a one-screen summary; an unknown flag exits with a usage error.
- `[REQ-XX-MMM]` a flag value overrides the built-in default; a missing flagged
  path is created with defaults, not an error.

**ADR:** [ADR: CLI surface](adr/2026-01-01-cli-surface.md)  ·  **Design:** [system-design.md#cli](system-design.md#cli)
```

### Lifecycle, not a Status field

A requirement is **active** by being in the narrative — there is no per-requirement `Status` field and no synonym set to maintain. Retire a requirement by moving its ID to a `## Superseded` list that maps it to its successor (or the reason it was withdrawn), so existing links still resolve. Never renumber an ID. The `**ADR:**` link is mandatory whenever an ADR records the decision behind the requirement; the `**Design:**` link is mandatory whenever the requirement defers a mechanism to system-design.md.

On a derived PRD (the `derive-briefs` skill), an inline `(confirmed <date>)` clause is a provenance mark, not a status field; a rewrite keeps the mark with its requirement. A derived PRD may also carry `## Known Defects` — observed behavior that breaches or serves no requirement, recorded for a later slice.

## Autofix Audit (Run First on Every Dispatch)

Before working on the dispatch's main task, audit every `type: "prd-autofix"` record in `.scratch/handoff.jsonl` whose `ts` is later than your most recent `type: "prd-entry"` record (or any such record if you have not yet appended one). `handoff.py audit-autofix` (the `code-quality-gate` skill's autofix audit) has already re-checked the allowlist bounds mechanically; your job is the judgement check.

For each record, decide whether the change is legitimately mechanical:

- **Legitimate.** Writing-standards or structural fix that doesn't smuggle in a semantic shift. Common shape: sentence split, missing anchor added, broken intra-file link repaired.
- **Illegitimate.** The change reads as mechanical but moves requirement meaning — a "sentence split" drops a condition from a "Done when" bullet, a "writing-standards" rewrite changes an acceptance contract, a "structural" fix repoints a REQ anchor. These are substantive changes that escaped via mis-tagging.

For every illegitimate record:

1. Apply the corrective edit to `docs/prd.md` yourself — you own the file.
2. Append a superseding `prd-entry` for the affected `req_id`, noting the rejection in `notes`: `"autofix-rejected: <handoff.jsonl line N>: <reason>"`. The design re-triage this triggers is deliberate — a semantic PRD change always re-enters the pipeline at Gate 1.

If every audited record is legitimate, skip silently — no entry needed. If the log contains no `prd-autofix` records, skip silently.

## Feature Handoff Record (product-requirements-expert → system-design-expert)

When a feature is approved, append one record to `.scratch/handoff.jsonl` describing the scope. The record is the structured contract that system-design-expert consumes; the markdown PRD entry in `docs/prd.md` remains the human-authored source of truth.

**File:** `.scratch/handoff.jsonl` (append-only; one JSON object per line, terminated by `\n`).

**Schema:** [`schemas/scratch/prd-entry.schema.json`](../../../schemas/scratch/prd-entry.schema.json). The routing gate (`handoff-routing` Gate 1) validates each record at the product-requirements-expert→system-design-expert transition; malformed records bounce back to you without consuming a system-design-expert dispatch.

**Required fields:**

| Field | Type | Notes |
|---|---|---|
| `type` | `"prd-entry"` | Discriminator. |
| `req_id` | string `^REQ-[A-Z]+-[0-9]{3}$` | Matches the PRD heading. |
| `ts` | ISO 8601 string | Stamped by `append`; never composed by the author. |
| `author` | `"product-requirements-expert"` | Pinned. |
| `title` | string | Short requirement title. |
| `summary` | string ≤ 400 chars | One- or two-sentence statement. No implementation details. |
| `acceptance_criteria` | array of strings | Testable conditions. At least one. |
| `file_targets` | array of strings | Paths likely to be touched. At least one. Best-effort; system-design-expert may revise. |
| `test_names` | array of strings matching `test_name_pattern` from `scripts/layout.toml` | Test functions/methods expected to exist, matching `test_name_pattern`. At least one. Naming school: `docs/testing-principles.md` § Test Naming. The coverage map string-matches them against the test tree; a rename during the TDD cycle is legitimate when the implementer's walk notes it. |

**Optional fields:** `non_goals`, `dependencies` (other req_ids), `notes`, `scope_overrides` (required whenever the uncommitted `docs/prd.md` delta touches a Non-Goals row — see § Scope Overrides).

### Scope Overrides (Changing a Non-Goals Row)

A change to a `Non-Goals` table row in `docs/prd.md` records the owner's decision behind it in the `prd-entry`'s `scope_overrides` array. Any change to a row's line counts — a rationale reword included. One entry per affected row:

| Field | Type | Notes |
|---|---|---|
| `non_goal_id` | string `^NG-[0-9]+$` | The changed row's id. |
| `owner_decision` | string | The owner's decision on this row, quoted verbatim from its source. Never a paraphrase, never your own rationale. |
| `source` | `"intake:<line>"`, `"consultation:<line>"`, or `"dispatch"` | Where the owner said it: the slice's `intake-decision` line, a `consultation-response` line with `author: "human"` for this `req_id`, or — only while no intake record exists — the dispatch prompt. |

Gate 1 runs the scope-lock check (`handoff-routing` skill, `route-spec.md` § Gate 1) over the uncommitted `docs/prd.md` delta against the last commit. Every changed or removed row needs a covering entry. An entry naming an unchanged row bounces as padding. For an `intake:<line>` source, the quote must appear verbatim in the cited record's `decisions` — the request is context, never override authority. For a `consultation:<line>` source, the quote must appear verbatim in the cited answer. A `dispatch` source bounces once a human `intake-decision` exists for the `req_id`. The delta persists until the slice commits: a later `prd-entry` in the same tree re-carries the covering entries. After the commit, a re-carried entry bounces as padding — drop it. *Adding* a new Non-Goals row needs no entry — recording newly declined scope is normal scoping work. No dispatch text to quote means the owner has not decided: append a `consultation-request` targeting `human` instead of the `prd-entry`.

**Append-only discipline:** Append records via `python3 scripts/handoff.py append prd-entry` (heredoc form per the `handoff-append` skill). Never edit, reorder, or delete prior records. If a prior record has a mistake, append a new record that supersedes it.

### Example Record

**Why JSONL, not markdown:** the structural-rejection gate this enables converts system-design-expert retries into cheap upstream bounces before a subagent dispatch is consumed.

```json
{"type":"prd-entry","req_id":"REQ-XX-099","author":"product-requirements-expert","title":"Cache miss diagnostics","summary":"Surface per-component cache miss rate so operators can spot reinjection hotspots.","acceptance_criteria":["report renders the cache-miss-rate per component","value matches cache-creation / (cache-creation + cache-read)"],"file_targets":["report/summary","report/summary_test"],"test_names":["<name matching test_name_pattern>"],"non_goals":["historical trend"]}
```

The `test_names` value is a placeholder: use names matching this project's `test_name_pattern` in `scripts/layout.toml` — the append gate rejects any other shape.

## Writing Standards

Follow the writing standards in the [`document-writing`](../document-writing/documentation-standards.md) skill — the language-agnostic rulebook the `doc-reviewer` enforces.

**Pre-handoff self-check.** Before appending the record, re-read every brief line the dispatch wrote or changed — the PRD, `docs/ubiquitous-language.md`, and any non-goal ADR. Three checks: behavioral language only — no mechanism, no code-element name, no constant value, no rationale prose after an ADR link. Every sentence within the 30-word standard. Provenance marks preserved (`document-writing` § When Editing a Derived Brief). A violation caught here costs one edit; caught by the doc-reviewer it costs the slice a review round.
