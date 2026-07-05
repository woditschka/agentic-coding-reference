# Documentation Standards

The language-agnostic standard for every project document: the writing rules, the five-document architecture and ownership boundaries, the within-document structure model, and the cross-reference and maintenance rules. Authors follow it; the `doc-reviewer` enforces it, together with the stack-specific checks in [`review-checks.md`](review-checks.md). `review-checks.md` is a stack overlay: each stack ships its own copy beside this skill, so the stack-agnostic core source carries none. The companion [`SKILL.md`](SKILL.md) carries the agent obligations and the author's validation checklist — this file is the rulebook both consume.

## Why Documentation Standards Matter for Agents

AI coding agents read your documentation before every task. Vague prose, ambiguous boundaries, and inconsistent structure degrade agent output the same way they degrade human understanding — but faster, because agents don't ask for clarification when confused. They guess.

Clear documentation sets a ceiling on agent output quality. Agents read docs before every task; vague docs guarantee vague work.

## Writing Standards

Clear writing reflects clear thinking. These rules apply to all documentation, code comments, and PRDs.

### Sentence Structure

- Maximum 30 words per sentence. Target 70% under 20 words.
- Use subject-verb-object form. Use strong verbs. Remove filler.
- One idea per sentence.

**Replace wordy phrases:**

| Do Not Write | Write Instead |
|--------------|---------------|
| "due to the fact that" | "because" |
| "lacked the ability to" | "could not" |
| "with the possible exception of" | "except" |
| "until such time as" | "until" |
| "for the purpose of" | "for" |

### Line Wrapping

- Do not hard-wrap Markdown prose to a fixed column. Write one logical line per block — a paragraph, list item, or table cell — and let the editor soft-wrap it.
- Hard-wrapping fights every later edit, because the column re-raggeds. It also invites a mid-word hyphen break at a line end (`reser-` then `vations`), which mis-renders: a Markdown soft break becomes a space, giving "reser- vations".
- Never break a word across two lines with a hyphen.
- One exception, YAML frontmatter: keep a multi-line `description` as a `>-` folded block scalar. That is idiomatic YAML — the fold collapses the lines into one string — not prose hard-wrapping.
- Code fences and tables stay verbatim; their line structure is significant.

### Replace Adjectives with Data

Adjectives are imprecise. Data is credible. If you cannot quantify the claim, reconsider making it.

| Do Not Write | Write Instead |
|--------------|---------------|
| "much faster" | "reduced from 10ms to 1ms" |
| "nearly all" | "87%" |
| "significantly better" | "+25 basis points" |
| "very reliable" | "99.9% uptime" |
| "sales increased significantly" | "sales increased 40% in Q4" |

### Prohibited Words

Never use without supporting data: "significant", "substantial", "remarkable", "arguably", "might", "would help", "should result in", "some", "many", "most", "several", "various", "often", "usually", "probably", "very", "extremely", "fairly", "quite".

### Be Objective

No subjective language. No buzzwords. No unsupported claims.

### Voice and Register

Write peer-to-peer, at the level of an experienced engineer addressing another. State structure, decisions, and trade-offs. Do not narrate the reader's experience, reassure them, or explain how to feel about a fact. Assert once and move on.

| Do Not Write | Write Instead |
|--------------|---------------|
| "The agent earns the word *collaborator* in that bounded sense" | "The agent improves the inputs to a decision, not the decision" |
| "which is a fast way to build judgment" | *(cut — state the mechanism, not the encouragement)* |
| "You should think of the harness as a force multiplier" | "The harness is a force multiplier" |
| "It's worth noting that the loop is fast" | "The loop runs in seconds" |

- Prefer declarative statements over second-person coaching, except where addressing the reader aids a procedure (e.g. Quick Start steps).
- Cut self-justifying and motivational phrasing. State the fact and its consequence.

### Pass the "So What?" Test

Every paragraph must justify its existence:
- If deleted, would the reader miss it?
- Does it enrich the reader's understanding?
- What are the implications?

If a paragraph fails, rewrite or remove it.

### Answer Questions Directly

Start with the answer. Do not warm up. Do not build suspense. Use one of four answers: Yes. No. A number (with context). "I don't know" (with follow-up).

### Rationale Clauses for Judgment Instructions

Instructions split into two kinds. A **hard contract** — a schema field, a routing rule, a write scope — is a bare imperative: state it and stop. A **judgment instruction** — a classification, a sizing test, an escalate-or-proceed call — carries one compact rationale clause. That clause is the *why* the agent generalizes from when a case falls outside the listed ones. One clause, not a paragraph. Mechanical contracts gain no added prose. See [`agentic-harness.md`](../handoff-routing/agentic-harness.md) § Principles Over Rigid Rules for the taxonomy and its basis in Anthropic's [Claude constitution](https://www.anthropic.com/news/claude-new-constitution).

### Use Inclusive Language

| Do Not Write | Write Instead |
|--------------|---------------|
| "whitelist" | "allowlist" |
| "blacklist" | "denylist" or "blocklist" |
| "master/slave" | "primary/replica" or "leader/follower" |
| "sanity check" | "confidence check" or "validation" |

### Avoid Jargon

Write for clarity, not exclusivity. Define technical terms on first use. Define acronyms on first use: "Product Requirements Document (PRD)". Do not assume shared context.

## Documentation Architecture

Documentation for an agentic project spreads across two axes: several documents, and several levels of abstraction within each document. This section defines both — the five document levels and their owners, the internal level structure every document follows, and the ownership boundaries that keep each fact in one place. When these hold, drift has fewer places to hide.

### Abstraction Levels (Across Documents)

Every agentic project needs documentation at five levels. Each level has a distinct audience and scope. Mixing levels causes drift, duplication, and agent confusion.

| Level | Document | Concerns | Audience |
|-------|----------|----------|----------|
| **Meta** | `CLAUDE.md` | Build commands, commit conventions, agent workflow | Contributors, agents |
| **Strategic** | `docs/prd.md` | Goals, requirements, constraints, acceptance criteria | Product owners, reviewers |
| **Decision** | `docs/adr/*.md` | Design trade-offs, alternatives considered, rationale | Architects, maintainers |
| **Tactical** | `docs/system-design.md` | Architecture, patterns, guardrails, file pointers | Developers, agents |
| **Language** | `docs/ubiquitous-language.md` | Canonical domain vocabulary, term definitions, terms to avoid | All docs, agents, developers |

Beyond the five levels, a project owns three principles briefs — `docs/testing-principles.md`, `docs/architecture-principles.md`, and `docs/security-principles.md` — which it customizes within the kernel (see the harness-project API for the full seven-file roster). The harness's own methodology is not mirrored into a project. It ships with the runtime, read from the skill tree or dissolved into skills and personas, never committed as a project document.

### Structure Within a Document

Every document — and every section longer than 200 words — is organized into 2–4 internal levels of abstraction, ordered highest to lowest. Each level is longer and more specific than the one before. A reader stops at any level and walks away with a useful understanding.

| Level | Name | Length | Content | Audience |
|-------|------|--------|---------|----------|
| 1 | Executive summary (what & why) | 1–3 paragraphs, ≤200 words, narrative prose | Purpose, key conclusion or recommendation, scope. No jargon, no implementation detail. | Decision-makers, first-time readers |
| 2 | Approach and structure (how) | 3–5× Level 1 | Method, architecture, plan, reasoning. Subheadings allowed; focus on concepts over specifics. | Planners, reviewers |
| 3 | Detail (show me) | As long as needed | Full technical or operational detail: specs, data, procedures, code, evidence. Navigable; not expected to be read linearly. | Implementers |
| 4 | Reference (optional) | As long as needed | Appendices, raw data, logs, extended examples. Supports Level 3 claims; not expected to be read end-to-end. | Auditors, deep debuggers |

**Rules:**

1. **Each level is self-contained.** Never require a reader to go deeper to understand the current level. If a Level 1 paragraph only makes sense after reading Level 3, the Level 1 is broken.
2. **Signal what's below.** End each level with a brief pointer to the next (e.g., "Implementation details follow in Section 3"). Readers who stop should know what they skip.
3. **Scale length gradually.** Aim for a 3–5× word-count multiplier between adjacent levels. A 15× jump (e.g., 200 words to 3,000) exceeds this ratio — insert a Level 2 that bridges them.
4. **Match audience to level.** Level 1 serves decision-makers, Level 2 serves planners, Levels 3–4 serve implementers. Do not mix audiences within a single level.
5. **Narrative at the top, structure at the bottom.** Level 1 reads as flowing prose. Lower levels may use lists, tables, diagrams, and headings freely.

**Applying the rules:**

- **CLAUDE.md:** The one-paragraph project overview is Level 1. Agent usage and toolchain sections are Level 2. Build commands, lint troubleshooting, commit conventions are Level 3. No Level 4.
- **docs/prd.md:** The Context narrative, goals/non-goals, and primary use case form Level 1. Capability-area headings with their opening prose are Level 2. The narrative requirement statements (tagged inline `[REQ-XX-NNN]`) and their "Done when" acceptance bullets are Level 3. See the `prd-authoring` skill § Requirement Format for the narrative-plus-tagged-bullet format.
- **docs/system-design.md:** The Overview and package-structure map are Level 1. Section headings (Contracts, Constants, Dependency Policy, Threat Model) are Level 2. The contract-table rows and per-invariant notes are Level 3. Implementation-order and state-machine tables are Level 4.
- **docs/adr/*.md:** Context + Decision are Level 1. Rationale and Alternatives are Level 2. Consequences and References are Level 3. ADRs are short enough to skip Level 4.

One failure pattern recurs: a new section opens with implementation detail and no Level 1 paragraph. When reviewing, look at the first 200 words of each top-level heading and ask: does a non-specialist understand the purpose, conclusion, and scope from this alone?

### The Ownership Principle

Each document owns specific concerns. No overlap. Duplicated information drifts; one copy will become wrong. Each document's detailed boundary lives in the skill that governs that document; the table below is the cross-document map.

| Document | Owns (in brief) | Detailed boundary |
|---|---|---|
| `CLAUDE.md` (Meta) | Project overview, build/test commands, agent workflow, commit conventions, doc pointers | This section, below — no governing skill |
| `docs/prd.md` (Strategic) | Goals, non-goals, requirements with contracts, constraints, acceptance criteria | `prd-authoring` skill — § PRD Boundary Rule, § Prohibited Patterns in PRD |
| `docs/ubiquitous-language.md` (Language) | Canonical domain vocabulary, one-line definitions, avoid-list | `prd-authoring` skill — § Ubiquitous Language Discipline |
| `docs/adr/*.md` (Decision) | Context, options with trade-offs, decision and rationale, consequences, implementation mapping | `adr-template` skill — § What an ADR Owns |
| `docs/system-design.md` (Tactical) | Conventions, invariants, constants, structure, type summaries, state tables | § Abstraction Level, below |

**CLAUDE.md (Meta Level)** owns the project overview, build and test commands, agent workflow and skills reference, commit conventions, and pointers to other docs. It does not own requirements (PRD), design rationale (ADRs), implementation details (system-design.md), or the writing standards (this skill).

### Abstraction Level (system-design.md)

`docs/system-design.md` owns the project's conventions, architectural invariants and guardrails (each imperative line — Do/Don't/Always/Never/Require — carries an inline ADR back-link), the constants reference table, package and module structure, domain-model and type summaries with source pointers, state-machine tables, and checklists for new components. It does not own type or interface definitions (source is authoritative), decision rationale or trade-off discussions (ADRs), what to build (PRD), or build commands (CLAUDE.md).

**Abstraction rule:** system-design.md describes design artifacts — contracts, invariants, ordering rules, atomicity guarantees, and fail-secure behaviors. It names each type, interface, and function once, says what contract it holds and which requirement it implements, and points at the source file. It does not replicate field lists, parameter lists, constant literals, or rule listings that already live in source — those rot silently when code changes and add no design information the reader cannot get from the code.

**Prose enumeration is the same violation as a field table.** Naming every field of a struct, every key of a config section, or every parameter of a function *in running prose* rots exactly like the table form — it is just harder to spot. The doctor's `field-tables` check catches the literal `| Field | … |` header; the prose form is the doc-reviewer's catch. Both fix the same way: one purpose sentence, an `Implements:` line, a source pointer.

**Per-contract budget:** a contract earns a table row — `Contract | Purpose | Source | Implements` — not paragraphs. Add a prose note above the table only for an invariant a row cannot carry. If a contract needs more than a row plus a sentence, the detail belongs in source or in an ADR. The whole doc carries a word budget the doctor enforces (`prd.md` and `system-design.md`; see the `doctor` skill); the budget is a backstop, this per-contract discipline is the primary lever.

**Self-test before adding content to system-design.md:** Read the paragraph you are about to add. Then ask: "If I renamed a field, added a parameter, or changed a constant in source, would this paragraph become wrong without anyone noticing?" If yes, the paragraph is at the wrong level — either delete it (source is authoritative) or rewrite it as an invariant that survives the rename.

**Example — wrong level (delete):**

```markdown
### SessionState

| Field | Type | Description |
|-------|------|-------------|
| `token` | `string` | The opaque session token. |
| `expiresAt` | timestamp | When the session lapses. |
| ... 11 more rows ...
```

**Example — right level (keep):**

```markdown
### RequestContext

Value object carrying everything a handler needs to serve one request: the
authenticated principal, the deadline, the cancellation signal, and the
resolved configuration. See the request-context source file.

**Implements:** REQ-RC-001, REQ-AUTH-002
```

## Cross-Reference Rules

Documents reference each other. Use consistent formats so agents can follow links programmatically.

### PRD References

When the PRD mentions a constraint value, reference a `Constants` section in `system-design.md` (create the section on first constant):
```markdown
**Constraints:**
- Buffer capacity: 10,000 points (see [system-design.md#constants](system-design.md#constants))
```

When PRD depends on a design decision:
```markdown
**ADR:** See [ADR: Title](adr/YYYY-MM-DD-title.md)
```

### system-design.md References

When referencing a requirement implementation:
```markdown
**Implements:** REQ-XX-001, REQ-XX-002

See `path/to/source/file` for the interface.
```

When following an ADR:
```markdown
Per [ADR: Decision Title](adr/YYYY-MM-DD-title.md), the system does X.
```

### ADR References

Each ADR includes an Implementation section with linked requirements:
```markdown
## Implementation

**Requirements:** REQ-XX-002, REQ-YY-002

## References

- [system-design.md#section](../system-design.md#section) — description
- [REQ-XX-002: Name](../prd.md#req-xx-002)
```

Use em-dashes to separate links from descriptions, not hyphens.

### Reference Format Summary

```markdown
# Within same document
See [Section Name](#section-name)

# To another document
See [prd.md#req-xx-001](prd.md#req-xx-001)

# From ADR to PRD requirement
[REQ-XX-002: Name](../prd.md#req-xx-002)

# From ADR to system-design section
[Constants](../system-design.md#constants) — description of what's there
```

Anchor IDs use lowercase with hyphens. For requirements, use the short ID anchor (e.g., `#req-xx-002`).

## Maintenance Rules

Documentation drifts when a change touches code but not the specs that describe it. These rules fix the order of updates for the three common changes — adding a feature, changing a constraint, fixing a bug — so each document stays current and no document duplicates another's job.

### When Adding a Feature

1. **PRD:** Add the requirement as narrative prose tagged inline `[REQ-XX-NNN]`, with a "Done when" acceptance bullet and `**ADR:**`/`**Design:**` links where they exist (see the `prd-authoring` skill § Requirement Format)
2. **ADR:** Create ADR if an architectural decision is involved (new pattern, trade-off, rejection of alternatives)
3. **system-design.md:** Add summaries, patterns, constants reference, implementation notes
4. **CLAUDE.md:** Update only if build commands or workflow changes
5. **ubiquitous-language.md:** Append new domain terms as they resolve; flag terms to avoid

### When Changing a Constraint

1. **Source code:** Update the constant value (authoritative). Update system-design.md reference if needed.
2. **PRD:** Verify constraint reference still valid
3. **ADR:** Create new ADR if the change represents an architectural decision

### When Fixing a Bug

1. **Code:** Fix the bug
2. **PRD:** Only update if acceptance criteria was wrong
3. **system-design.md:** Only update if implementation pattern changes
4. **ADR:** Only create if the fix represents an architectural decision

## Agent Optimization

All documentation in `docs/` should be optimized for consumption by AI agents. Agents parse markdown structure, not visual layout.

### Structural Requirements

| Rule | Rationale |
|------|-----------|
| HTML anchors for requirement IDs | Stable linking across heading renames |
| No version numbers in documents | Git handles versioning |
| Tables over prose for structured data | Tables are extractable; bullets are ambiguous |
| ASCII art diagrams are informational only | Agents cannot parse them reliably; use tables for state machines |
| Language tags on code blocks | Enables syntax detection |
| Em-dashes for reference list separators | Distinguishes link from description |

### Parseable Section Templates

Each document's section template lives with the skill that governs that document — one home per template:

- **PRD requirement:** `prd-authoring` skill — § Requirement Format.
- **ADR (Implementation and References sections, non-goal variant):** `adr-template` skill; the ADR body template itself lives in `docs/adr/README.md`.

The system-design state-machine template has no governing skill, so it lives here. Tables are the authoritative format for state machines; ASCII diagrams are supplementary.

**State Transitions (system-design.md):**
```markdown
**State Flow (parseable format):**

| # | From | Event | To |
|---|------|-------|----|
| 1 | (start) | Connect() called | CONNECTING |
| 2 | CONNECTING | Success | CONNECTED |
| 3 | CONNECTING | Failure | DISCONNECTED |

**Visual representation (informational only):**
[ASCII diagram here - not parsed by agents]
```

## Prohibited Patterns

The patterns below recur across agentic projects. Each places content at the wrong abstraction level — implementation detail in a strategic document, or a constant value duplicated from source — where it drifts from source and misleads agents. The table lists each pattern, its severity, and the fix.

| Pattern | Severity | Solution |
|---------|----------|----------|
| Implementation pseudocode in PRD | **Critical** | Move to system-design.md, link from PRD |
| Language-specific code blocks in PRD | **Critical** | Move to system-design.md, link from PRD |
| A document granting itself a blanket exemption ("reviewers may skip check X here") | **Critical** | A document cannot disable a reviewer check; fix the content or escalate per-instance |
| Language-specific constructs in PRD | **Critical** | Describe behavior, not mechanism (severity per `prd-authoring` § Prohibited Patterns in PRD, the canonical PRD table) |
| Field/parameter/key enumeration in system-design.md **prose** (naming each field of a struct, key of a config block, or parameter in running text) | **High** | Same as the field-table row — one purpose sentence plus a source pointer |
| Mechanism tables in PRD (CLI flags, exit codes, output-directory layouts, file-format schemas) | **High** | Move to system-design.md; state behavior in prose, link with `**Design:**` |
| Per-requirement contract scaffolding in PRD (`Input`/`Output`/`Constraints`/`Depends On` blocks) | **High** | State the outcome in a "Done when" bullet; signature in source, constants in system-design.md |
| Internal code references in PRD | **High** | Use behavioral language |
| Algorithm formulas in PRD | **High** | State behavioral constraints in PRD, move formulas to system-design.md |
| Duplicated type definitions across docs | **High** | Source code is authoritative; reference source files |
| Field tables in system-design.md (`\| Field \| Type \| Description \|` for a struct, record, or class) | **High** | Replace with a one-paragraph purpose summary and a `See source-file` pointer |
| Function or method parameter tables in system-design.md | **High** | Describe the contract in prose; the signature lives in source |
| Constant literal values in system-design.md | **High** | Name the constant and cite the source file; do not copy the value |
| Exhaustive rule listings in system-design.md (iptables, SQL, shell) | **Medium** | State the invariant; source is authoritative for the full listing |
| Hardcoded constants in PRD | **Medium** | Reference a `Constants` section in `system-design.md` (create the section on first constant) |
| "Why" explanations in system-design.md | **Medium** | Create ADR |
| Implementation details in ADR | **Medium** | Reference system-design.md |
| Build commands in PRD | **Medium** | Keep in CLAUDE.md |
| Hyphens in ADR reference lists | **Medium** | Use em-dashes |
| Hard-wrapped Markdown prose, or a word broken across lines with a hyphen | **Medium** | One logical line per block; let the editor wrap (YAML frontmatter `>-` excepted) |
| Version numbers in documents | **Medium** | Use git for versioning |
