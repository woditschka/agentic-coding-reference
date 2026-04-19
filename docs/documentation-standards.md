# Documentation Standards for Agentic Projects

This document defines how to write, structure, and maintain documentation in projects that use AI coding agents. These are language-agnostic principles — the Go and Java Spring Boot implementations each apply them with language-specific conventions in their own `docs/documentation.md`.

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

### Pass the "So What?" Test

Every paragraph must justify its existence:
- If deleted, would the reader miss it?
- Does it enrich the reader's understanding?
- What are the implications?

If a paragraph fails, rewrite or remove it.

### Answer Questions Directly

Start with the answer. Do not warm up. Do not build suspense. Use one of four answers: Yes. No. A number (with context). "I don't know" (with follow-up).

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

### Abstraction Levels (Across Documents)

Every agentic project needs documentation at four levels. Each level has a distinct audience and scope. Mixing levels causes drift, duplication, and agent confusion.

| Level | Document | Concerns | Audience |
|-------|----------|----------|----------|
| **Meta** | `CLAUDE.md` | Build commands, commit conventions, agent workflow | Contributors, agents |
| **Strategic** | `docs/prd.md` | Goals, requirements, constraints, acceptance criteria | Product owners, reviewers |
| **Decision** | `docs/adr/*.md` | Design trade-offs, alternatives considered, rationale | Architects, maintainers |
| **Tactical** | `docs/system-design.md` | Architecture, patterns, guardrails, file pointers | Developers, agents |

Optional additions depending on project complexity:
- `docs/testing-principles.md` — Test structure, naming, and refactoring patterns (Tactical)
- `docs/documentation.md` — Project-specific documentation governance (Meta)

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
- **docs/prd.md:** Motivation, primary use case, goals/non-goals, and document map form Level 1. Functional group headings with their opening paragraphs are Level 2. Individual requirements (`### REQ-XX-NNN`) are Level 3; acceptance criteria are supporting detail at the same level.
- **docs/system-design.md:** The package structure diagram and overview paragraph are Level 1. Section headings for types, interfaces, and command dispatch are Level 2. Per-type and per-function detail blocks are Level 3. Implementation order tables are Level 4.
- **docs/adr/*.md:** Context + Decision are Level 1. Rationale and Alternatives are Level 2. Consequences and References are Level 3. ADRs are short enough to skip Level 4.

One failure pattern recurs: a new section opens with implementation detail and no Level 1 paragraph. When reviewing, look at the first 200 words of each top-level heading and ask: does a non-specialist understand the purpose, conclusion, and scope from this alone?

### The Ownership Principle

Each document owns specific concerns. No overlap. Duplicated information drifts; one copy will become wrong.

**CLAUDE.md (Meta Level)**

Owns:
- Project overview (one paragraph)
- Build and test commands
- Agent workflow and skills reference
- Commit conventions
- Pointers to other docs

Does not own:
- Requirements (PRD)
- Design rationale (ADRs)
- Implementation details (system-design.md)
- Writing standards rules (documentation.md)

**docs/prd.md (Strategic Level)**

Owns:
- Goals with success metrics
- Non-goals with rationale
- Requirements with status, input/output contracts, constraints, acceptance criteria, and dependency graph

Does not own:
- Implementation code or pseudocode
- Language-specific constructs (Go channels, Java streams, Spring annotations)
- Internal code references (class names, function names, variable names)
- Algorithm formulas (state behavioral outcome; put formulas in system-design.md)
- Constant values (reference system-design.md)
- Design rationale (ADRs)

**docs/adr/*.md (Decision Level)**

Owns:
- Context for each architectural decision
- Options considered with trade-offs
- Decision outcome and rationale
- Consequences (positive and negative)
- Implementation mapping (which requirements, which files)

Does not own:
- Detailed implementation (system-design.md)
- Requirement specifications (PRD)

**docs/system-design.md (Tactical Level)**

Owns:
- Language conventions for this project
- Architectural invariants and guardrails
- Constants reference table
- Package/module structure (file paths)
- Domain model and type summaries with source file pointers
- State machine tables and transitions
- Checklists for adding new components

Does not own:
- Type/interface definitions (source code is authoritative)
- Why decisions were made (ADRs)
- What should be built (PRD)
- Build commands (CLAUDE.md)

**Abstraction rule:** system-design.md describes design artifacts — contracts, invariants, ordering rules, atomicity guarantees, and fail-secure behaviors. It names each type, interface, and function once, says what contract it holds and which requirement it implements, and points at the source file. It does not replicate field lists, parameter lists, constant literals, or rule listings that already live in source — those rot silently when code changes and add no design information the reader cannot get from the code.

**Self-test before adding content to system-design.md:** Read the paragraph you are about to add and ask: "If I renamed a field, added a parameter, or changed a constant in source, would this paragraph become wrong without anyone noticing?" If yes, the paragraph is at the wrong level — either delete it (source is authoritative) or rewrite it as an invariant that survives the rename.

**Example — wrong level (delete):**

```markdown
### UpOptions

| Field | Type | Description |
|-------|------|-------------|
| `WorkspaceFolder` | `string` | Absolute path to the host workspace. |
| `Config` | `config.Config` | Fully resolved config. |
| ... 11 more rows ...
```

**Example — right level (keep):**

```markdown
### UpOptions

Value object carrying every parameter `container.Up` needs: the resolved
workspace set, the post-substitution config, network and mount policy,
resource limits, and injected seams (symlink resolver, confirm callback)
for testability. See `internal/container/up.go`.

**Implements:** REQ-CO-002, REQ-MF-001, REQ-RL-001, REQ-NR-001
```

## Cross-Reference Rules

Documents reference each other. Use consistent formats so agents can follow links programmatically.

### PRD References

When PRD mentions a constraint value:
```markdown
**Constraints:**
- Buffer capacity: 10,000 points (see [system-design.md#constants](system-design.md#constants))
```

When PRD depends on a design decision:
```markdown
**Design Rationale:** See [ADR: Title](adr/YYYY-MM-DD-title.md)
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

### When Adding a Feature

1. **PRD:** Add requirement with ID, status, contracts, constraints, acceptance criteria
2. **ADR:** Create ADR if an architectural decision is involved (new pattern, trade-off, rejection of alternatives)
3. **system-design.md:** Add summaries, patterns, constants reference, implementation notes
4. **CLAUDE.md:** Update only if build commands or workflow changes

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

**Requirement (PRD):**
```markdown
<a id="req-xx-nnn"></a>
### REQ-XX-NNN: Name

[One sentence description]

**Status:** Approved | Proposed | Deprecated

**Design Rationale:**
- [ADR: Title](adr/YYYY-MM-DD-title.md)

**Input:**
- `param` (type): Description

**Output:**
- `result` (type): Description

**Behavior:**
[Prose description. No code, no language-specific constructs, no internal names.
Describe what happens, not how.]

**Implementation:** See [system-design.md#section](system-design.md#section)

**Constraints:** (values in [system-design.md#constants](system-design.md#constants))
- Constraint name: `ConstantName` (value)

**Acceptance Criteria:**
1. Given X, when Y, then Z
2. Given A, when B, then C

**Depends On:** REQ-XX-NNN, REQ-YY-MMM
```

**ADR:**
```markdown
## Implementation

**Requirements:** REQ-XX-NNN, REQ-YY-MMM

## References

- [system-design.md#section](../system-design.md#section) — description
- [REQ-XX-NNN: Name](../prd.md#req-xx-nnn-name)
```

For ADRs relating to non-goals, use `**Non-goal:** NG-X` instead of Requirements.

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

Tables are the authoritative format for state machines. ASCII diagrams are supplementary.

## Prohibited Patterns

| Pattern | Severity | Solution |
|---------|----------|----------|
| Implementation pseudocode in PRD | **Critical** | Move to system-design.md, link from PRD |
| Language-specific code blocks in PRD | **Critical** | Move to system-design.md, link from PRD |
| Language-specific constructs in PRD | **High** | Describe behavior in PRD, mechanism in system-design.md |
| Internal code references in PRD | **High** | Use behavioral language |
| Algorithm formulas in PRD | **High** | State behavioral constraints in PRD, move formulas to system-design.md |
| Duplicated type definitions across docs | **High** | Source code is authoritative; reference source files |
| Struct field tables in system-design.md (`\| Field \| Type \| Description \|`) | **High** | Replace with a one-paragraph purpose summary and a `See source-file` pointer |
| Function parameter tables in system-design.md (`\| Parameter \| Type \| Description \|`) | **High** | Describe the contract in prose; the signature lives in source |
| Constant literal values in system-design.md | **High** | Name the constant and cite the source file; do not copy the value |
| Exhaustive rule listings in system-design.md (iptables, SQL, shell) | **Medium** | State the invariant; source is authoritative for the full listing |
| Hardcoded constants in PRD | **Medium** | Reference system-design.md#constants |
| "Why" explanations in system-design.md | **Medium** | Create ADR |
| Implementation details in ADR | **Medium** | Reference system-design.md |
| Build commands in PRD | **Medium** | Keep in CLAUDE.md |
| Hyphens in ADR reference lists | **Medium** | Use em-dashes |
| Version numbers in documents | **Medium** | Use git for versioning |

## Agent Guidelines

Agents must:
- Read PRD requirements before implementing
- Reference system-design.md for types and interfaces
- Check ADRs for design constraints before proposing alternatives
- Never duplicate type definitions across documents
- Never add code or language-specific constructs to PRD
- Never reference internal code in PRD (no class names, function names, or variable names)
- Use behavioral language in PRD ("the system retries the operation" not "`Retry()` calls `continue`")
- When PRD needs to reference implementation details, add a link: `**Implementation:** See [system-design.md#section](system-design.md#section)`

## Validation Checklist

Before merging documentation changes, verify:

### Structural Checks

- [ ] All requirement IDs have HTML anchors (`<a id="req-xx-nnn"></a>`)
- [ ] No implementation pseudocode in PRD
- [ ] No language-specific code blocks in PRD
- [ ] No language-specific constructs in PRD
- [ ] All cross-references use full paths with anchors
- [ ] Tables have headers and consistent column counts
- [ ] No relative references ("above", "below", "previous")
- [ ] No version numbers in documents
- [ ] ADR References use em-dashes
- [ ] ADR Implementation section includes **Requirements:** or **Non-goal:**
- [ ] Code blocks have language tags

### Cross-Document Coherence Checks

- [ ] Every requirement ID in system-design.md exists in prd.md
- [ ] Deprecated requirements are absent from system-design.md
- [ ] Constants referenced in prd.md are defined in system-design.md
- [ ] All document links resolve to valid anchors

### Abstraction Level Checks (system-design.md)

- [ ] No struct field tables (`| Field | Type | Description |` rows). Purpose paragraph plus source pointer instead.
- [ ] No function parameter tables (`| Parameter | Type | Description |` rows). Contract prose plus source pointer instead.
- [ ] No constant literal values. Name the constant, cite the source file.
- [ ] No exhaustive rule listings (iptables, SQL, shell). State the invariant; source is authoritative for the full listing.
- [ ] Self-test: for each paragraph, would a field rename, parameter addition, or constant change in source silently invalidate it? If yes, rewrite or delete.

### Structure Within a Document Checks

Per [Structure Within a Document](#structure-within-a-document):

- [ ] Each top-level heading opens with a Level 1 paragraph (≤200 words, narrative prose, no jargon) that states purpose, conclusion, and scope.
- [ ] A non-specialist can read the first 200 words of any major section and walk away with a useful understanding.
- [ ] No section jumps from Level 1 to Level 3 with more than a 5× length ratio — insert a Level 2 bridge when the gap is larger.
- [ ] Each level is self-contained: no forward references ("as explained in Section 3 below") required to understand the current level.
- [ ] Lower-level sections may use lists, tables, and diagrams, but Level 1 paragraphs are prose.

### Writing Standards Checks

- [ ] No prohibited words without data
- [ ] No vague adjectives without measurements
- [ ] Sentences under 30 words; 70% under 20 words
- [ ] No wordy phrases
- [ ] Every paragraph passes the "So what?" test
- [ ] Answers start with the answer
- [ ] Acronyms defined on first use
- [ ] No subjective language or buzzwords

## How This Relates to Project-Level Docs

This document defines the principles. Each implementation applies them:

- **Go:** [`go/docs/documentation.md`](../go/docs/documentation.md) — adds Go-specific prohibited patterns (channels, goroutines in PRD), Go code block rules, Go file path conventions
- **Java Spring Boot:** [`java-spring-boot/docs/documentation.md`](../java-spring-boot/docs/documentation.md) — adds Java-specific prohibited patterns (streams, annotations, Spring APIs in PRD), Java code block rules, Spring conventions
