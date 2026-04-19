# Documentation Governance

<!-- AGENT: This is the authoritative source for documentation rules -->
<!-- AGENT: Read "Agent Optimization Guidelines" section before processing other docs -->
<!-- AGENT: Validation checklist at end of document for verifying compliance -->

This document defines documentation structure, writing standards, and maintenance rules for this project. All contributors and agents must follow these guidelines.

## Writing Standards

All documentation, comments, and PRDs must follow these rules. Clear writing reflects clear thinking.

### Sentence Structure

- Maximum 30 words per sentence. Target 70% under 20 words.
- Use subject-verb-object form. Use strong verbs. Remove filler.
- One idea per sentence. No ambiguity.

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

Never use without data: "significant", "substantial", "remarkable", "arguably", "might", "would help", "should result in", "some", "many", "most", "several", "various", "often", "usually", "probably", "very", "extremely", "fairly", "quite".

### Be Objective

No subjective language. No buzzwords. No unsupported claims. Data supports decision-making; adjectives do not.

### Pass the "So What?" Test

Every paragraph must justify its existence. Ask:
- If deleted, would the reader miss it?
- Does it enrich the reader's understanding?
- What are the implications?

If a paragraph fails, rewrite or remove it.

### Answer Questions Directly

Start with the answer. Do not warm up. Do not build suspense. Use one of four answers: Yes. No. A number (with context). "I don't know" (with follow-up).

### Use Inclusive Language

Use inclusive terminology. Avoid terms with exclusionary origins.

| Do Not Write | Write Instead |
|--------------|---------------|
| "whitelist" | "allowlist" |
| "blacklist" | "denylist" or "blocklist" |
| "master/slave" | "primary/replica" or "leader/follower" |
| "sanity check" | "confidence check" or "validation" |

### Avoid Jargon

Write for clarity, not exclusivity. Define technical terms on first use. Define acronyms on first use: "Product Requirements Document (PRD)". Do not assume shared context.

## Abstraction Levels (Across Documents)

| Level | Document | Concerns | Audience |
|-------|----------|----------|----------|
| **Meta** | `CLAUDE.md` | Build commands, commit conventions, agent workflow | Contributors, agents |
| **Strategic** | `docs/prd.md` | Goals, requirements, constraints, acceptance criteria | Product owners, reviewers |
| **Decision** | `docs/adr/*.md` | Design trade-offs, alternatives considered, rationale | Architects, maintainers |
| **Tactical** | `docs/system-design.md` | Architecture, patterns, guardrails, file pointers | Developers, agents |
| **Tactical** | `docs/testing-principles.md` | Test structure, refactoring patterns, data naming, agent checklist | Developers, agents |

### Structure Within a Document

Every document — and every non-trivial section — is organized into 2–4 internal levels of abstraction, ordered highest to lowest. Each level is longer and more specific than the one before. A reader stops at any level and walks away with a useful understanding.

| Level | Name | Length | Content | Audience |
|-------|------|--------|---------|----------|
| 1 | Executive summary (what & why) | 1–3 paragraphs, ≤200 words, narrative prose | Purpose, key conclusion or recommendation, scope. No jargon, no implementation detail. | Decision-makers, first-time readers |
| 2 | Approach and structure (how) | 3–5× Level 1 | Method, architecture, plan, reasoning. Subheadings allowed; focus on concepts over specifics. | Planners, reviewers |
| 3 | Detail (show me) | As long as needed | Full technical or operational detail: specs, data, procedures, code, evidence. Navigable; not expected to be read linearly. | Implementers |
| 4 | Reference (optional) | As long as needed | Appendices, raw data, logs, extended examples. Supports Level 3 claims; not expected to be read end-to-end. | Auditors, deep debuggers |

**Rules:**

1. **Each level is self-contained.** Never require a reader to go deeper to understand the current level. If a Level 1 paragraph only makes sense after reading Level 3, the Level 1 is broken.
2. **Signal what's below.** End each level with a brief pointer to the next (e.g., "Implementation details follow in Section 3"). Readers who stop should know what they skip.
3. **Scale length gradually.** Aim for a 3–5× word-count multiplier between adjacent levels. A jump from 200 words to 3,000 is too abrupt; insert a Level 2 that bridges them.
4. **Match audience to level.** Level 1 serves decision-makers, Level 2 serves planners, Levels 3–4 serve implementers. Do not mix audiences within a single level.
5. **Narrative at the top, structure at the bottom.** Level 1 reads as flowing prose. Lower levels may use lists, tables, diagrams, and headings freely.

**Applying the rules:**

- **CLAUDE.md:** The one-paragraph project overview is Level 1. Agent usage and toolchain sections are Level 2. Build commands, commit conventions are Level 3. No Level 4.
- **docs/prd.md:** Motivation, primary use case, goals/non-goals, and document map form Level 1. Functional group headings with their opening paragraphs are Level 2. Individual requirements (`### REQ-XX-NNN`) are Level 3; acceptance criteria are supporting detail at the same level.
- **docs/system-design.md:** The package structure diagram and overview paragraph are Level 1. Section headings for types, interfaces, and modules are Level 2. Per-type and per-method detail blocks are Level 3. Implementation order tables are Level 4.
- **docs/adr/*.md:** Context + Decision are Level 1. Rationale and Alternatives are Level 2. Consequences and References are Level 3. ADRs are short enough to skip Level 4.

The most common failure is starting a new section with implementation detail and no Level 1 paragraph. When reviewing, look at the first 200 words of each top-level heading and ask: does a non-specialist understand the purpose, conclusion, and scope from this alone?

## Document Ownership

### CLAUDE.md (Meta Level)

**Owns:**
- Project overview (one paragraph)
- Build and test commands
- Writing standards reference (→ documentation.md)
- Agent workflow and skills reference (→ `.claude/agents/README.md`, `.claude/skills/`)
- Commit conventions
- Testing strategy references

**Does not own:**
- Requirements (→ PRD)
- Type definitions (→ source code)
- Design rationale (→ ADRs)
- Implementation details (→ system-design.md)
- Writing standards rules (→ documentation.md)
- Document maintenance rules (→ documentation.md)
- PRD/system-design boundary rules (→ documentation.md)

### docs/prd.md (Strategic Level)

**Owns:**
- Goals with success metrics
- Non-goals with rationale
- Requirements with:
  - Status
  - Input/output contracts (what, not how)
  - Constraints (values reference system-design.md)
  - Acceptance criteria
  - Dependency graph
- Example configuration
- Out of scope list

**Does not own:**
- Implementation code or pseudocode (→ system-design.md)
- Java record definitions (→ system-design.md)
- Java-specific constructs: streams, lambdas, Spring annotations (→ system-design.md)
- Internal code references: class names, method names, variable names (→ system-design.md)
- Algorithm formulas or pseudocode (→ system-design.md; PRD states behavioral outcome only)
- Constant values (reference system-design.md)
- Design rationale (→ ADRs)
- Test implementation patterns (→ system-design.md)

### docs/adr/*.md (Decision Level)

**Owns:**
- Context for each architectural decision
- Options considered with trade-offs
- Decision outcome and rationale
- Consequences (positive and negative)
- Implementation mapping (which requirements, which files)

**Does not own:**
- Detailed implementation (→ system-design.md)
- Requirement specifications (→ PRD)

### docs/system-design.md (Tactical Level)

**Owns:**
- Java conventions for this project (prescriptive style examples)
- Architectural invariants and guardrails
- Constants reference table (groups, source files, key values)
- Package structure (file paths)
- Domain model (Java records, single source of truth for types)
- Interface and type summaries with source file pointers
- Implementation order (ID, Name, Depends On columns)
- State machine tables and transitions
- Error handling table
- Checklists for adding new components
- Test fixtures and examples

**Does not own:**
- Type definitions (→ source code is the source of truth)
- Interface definitions (→ source code is the source of truth)
- Constant values (→ source code is the source of truth)
- Why decisions were made (→ ADRs)
- What should be built (→ PRD)
- Build commands (→ CLAUDE.md)

**Abstraction rule:** system-design.md describes design artifacts — contracts, invariants, ordering rules, atomicity guarantees, and fail-secure behaviors. It names each type, interface, and method once, says what contract it holds and which requirement it implements, and points at the source file. It does not replicate field lists, parameter lists, constant literals, or rule listings that already live in source — those rot silently when code changes and add no design information the reader cannot get from the code.

**Self-test before adding content to system-design.md:** Read the paragraph you are about to add and ask: "If I renamed a field, added a parameter, or changed a constant in source, would this paragraph become wrong without anyone noticing?" If yes, the paragraph is at the wrong level — either delete it (source is authoritative) or rewrite it as an invariant that survives the rename.

**Example — wrong level (delete):**

```markdown
### ParserConfig

| Field | Type | Description |
|-------|------|-------------|
| `inputPath` | `Path` | Absolute path to the input file. |
| `outputFormat` | `OutputFormat` | Target format for parsed output. |
| ... 8 more rows ...
```

**Example — right level (keep):**

```markdown
### ParserConfig

Record carrying every parameter `ParserService.parse()` needs: the resolved
input path, output format policy, resource limits, and injected dependencies
for testability. See `src/main/java/com/example/parser/ParserConfig.java`.

**Implements:** REQ-PA-001, REQ-PA-003
```

## Cross-Reference Rules

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

When system-design.md references a requirement implementation:
```markdown
**Implements:** REQ-XX-001, REQ-XX-002

See `src/main/java/com/example/project/package/Class.java` for the interface.
```

When system-design.md follows an ADR:
```markdown
## Section

Per [ADR: Decision Title](adr/YYYY-MM-DD-title.md), the system does X.
```

### ADR References

Each ADR must include an Implementation section with linked requirements:
```markdown
## Implementation

**Requirements:** REQ-XX-002, REQ-YY-002

## References

- [system-design.md#section](../system-design.md#section) — description
- [REQ-XX-002: Name](../prd.md#req-xx-002)
```

Note: Use em-dashes (—) to separate links from descriptions, not hyphens.

## Maintenance Rules

### When Adding a Feature

1. **PRD:** Add requirement with ID, status, contracts, constraints, acceptance criteria
2. **ADR:** Create ADR if architectural decision involved (new pattern, trade-off, rejection of alternatives)
3. **system-design.md:** Add summaries, patterns, constants reference, implementation notes
4. **CLAUDE.md:** Update only if build commands or workflow changes

### When Changing a Constraint

1. **Source code:** Update constant value (authoritative). Update system-design.md reference if needed.
2. **PRD:** Verify constraint reference still valid
3. **ADR:** Create new ADR if change represents architectural decision

### When Fixing a Bug

1. **Code:** Fix the bug
2. **PRD:** Only update if acceptance criteria was wrong
3. **system-design.md:** Only update if implementation pattern changes
4. **ADR:** Only create if fix represents architectural decision

### Agent Guidelines

Agents must:
- Read PRD requirements before implementing
- Reference system-design.md for types and interfaces
- Check ADRs for design constraints before proposing alternatives
- Never duplicate type definitions across documents
- Never add pseudocode or Java code to PRD (use contracts only)
- Never add Java-specific constructs to PRD (streams, annotations, Spring APIs)
- Never reference internal code in PRD (no class names, method names, or variable names)
- Use behavioral language in PRD ("the system retries the operation" not "`Retry()` calls `continue`")
- When PRD needs to reference implementation details, add a link: `**Implementation:** See [system-design.md#section](system-design.md#section)`

## Document Map

```
CLAUDE.md (Meta)
├── References: docs/prd.md (for requirements)
├── References: docs/documentation.md (for writing standards, maintenance, boundaries)
├── References: docs/system-design.md (for patterns, guardrails, dependencies)
├── References: .claude/agents/README.md (for agent roles, cross-tool rules, maturity)
├── References: .claude/skills/ (for portable workflow knowledge)
└── Does not duplicate: writing rules, boundary rules, pipeline routing, or maintenance rules

docs/prd.md (Strategic)
├── Has: HTML anchors (<a id="req-xx-nnn">) for stable linking
├── References: docs/system-design.md (for implementation details)
├── References: docs/adr/*.md (for design rationale)
└── Does not contain: implementation pseudocode

docs/adr/*.md (Decision)
├── Has: Implementation section with **Requirements:** or **Non-goal:**
├── Has: References section with full markdown links and em-dashes
├── References: docs/prd.md (linked requirements)
├── References: docs/system-design.md (implementation location)
└── Does not contain: detailed implementation

docs/system-design.md (Tactical)
├── Has: Package structure (file paths)
├── Has: Implementation order (ID, Name, Depends On)
├── References: docs/prd.md (requirements implemented)
├── References: docs/adr/*.md (decisions followed)
└── Describes: patterns, guardrails, summaries (source code is authoritative)

docs/testing-principles.md (Tactical)
├── Has: Four-phase test structure (Arrange/Act/Assert/Cleanup)
├── Has: Refactoring playbook (assertions, cleanup, setup, duplication)
├── Has: Three-tier data naming (MEANINGFUL / IRRELEVANT / MYSTERY)
├── Has: Agent decision checklist (14-point pre-commit check)
└── Referenced by: CLAUDE.md, docs/system-design.md
```

## Prohibited Patterns

| Pattern | Severity | Solution |
|---------|----------|----------|
| Implementation pseudocode in PRD | **Critical** | Move to system-design.md, link from PRD |
| Java code blocks in PRD | **Critical** | Move to system-design.md, link from PRD |
| Java-specific constructs in PRD (streams, annotations, Spring APIs) | **High** | Describe behavior in PRD, mechanism in system-design.md |
| Internal code references in PRD (class names, method names, variable names) | **High** | Use behavioral language |
| Algorithm formulas in PRD | **High** | State behavioral constraints in PRD, move formulas to system-design.md |
| Duplicated type definitions | **High** | Source code is the source of truth; reference source files |
| Record field tables in system-design.md (`| Field | Type | Description |`) | **High** | Replace with a one-paragraph purpose summary and a `See source-file` pointer |
| Method parameter tables in system-design.md (`| Parameter | Type | Description |`) | **High** | Describe the contract in prose; the signature lives in source |
| Constant literal values in system-design.md | **High** | Name the constant and cite the source file; do not copy the value |
| Exhaustive rule listings in system-design.md (SQL, YAML, shell) | **Medium** | State the invariant; source is authoritative for the full listing |
| Hardcoded constants in PRD | **Medium** | Reference system-design.md#constants |
| "Why" explanations in system-design.md | **Medium** | Create ADR |
| Implementation details in ADR | **Medium** | Reference system-design.md |
| Build commands in PRD | **Medium** | Keep in CLAUDE.md |
| Hyphens in ADR reference lists | **Medium** | Use em-dashes (—) |
| Version numbers in documents | **Medium** | Use git for versioning; no "Version: 1.0" fields |

## Agent Optimization Guidelines

All documentation in `docs/` is optimized for consumption by AI agents. Follow these rules to maintain parseability.

### Structural Requirements

| Rule | Rationale | Example |
|------|-----------|---------|
| HTML anchors for requirement IDs | Stable linking across heading changes | `<a id="req-xx-001"></a>` before heading |
| No version numbers | Git handles versioning | Remove "Version: 1.0" fields |
| Tables over prose lists | Structured data is extractable | Use tables for constraints, not bullets |
| ASCII art diagrams informational only | Cannot be parsed programmatically | Use tables for state transitions |
| Language tags on code blocks | Enables syntax detection | ` ```java` not ` ``` ` |
| Em-dashes for list separators | Distinguishes link from description | `[Link](url) — description` |

### Reference Format

Use consistent cross-reference format throughout:

```markdown
# Within same document
See [Section Name](#section-name)

# To another document (from docs/ subdirectory)
See [prd.md#req-xx-001](prd.md#req-xx-001)

# From ADR to PRD requirement
[REQ-XX-002: Name](../prd.md#req-xx-002)

# From ADR to system-design section (with description)
[Constants](../system-design.md#constants) — `DefaultTimeout`, `MaxRetries`

# Inline requirement reference
Implements REQ-XX-001
```

Note: Anchor IDs use lowercase with hyphens. For requirements, use the short ID anchor (e.g., `#req-xx-002`).

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
[Prose description. No code, no Java constructs, no internal function names. Describe what happens, not how.]

**Implementation:** See [system-design.md#section](system-design.md#section)

**Constraints:** (values in [system-design.md#constants](system-design.md#constants))
- Constraint name: `ConstantName` (value)

**Acceptance Criteria:**
1. Given X, when Y, then Z
2. Given A, when B, then C

**Depends On:** REQ-XX-NNN, REQ-YY-MMM
```

Note: HTML anchors (`<a id="...">`) enable stable linking. Anchor IDs use lowercase with hyphens.

**ADR Structure:**
```markdown
## Implementation

**Requirements:** REQ-XX-NNN, REQ-YY-MMM

## References

- [system-design.md#section](../system-design.md#section) — description
- [REQ-XX-NNN: Name](../prd.md#req-xx-nnn-name)
```

Note: For ADRs relating to non-goals, use `**Non-goal:** NG-X` instead of Requirements.

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

Note: Tables are the authoritative format for state machines. ASCII diagrams are supplementary.

### Validation Checklist

Before merging documentation changes, verify all three categories below. The `doc-reviewer` agent (`.claude/agents/doc-reviewer.md`) automates these checks. The `/lint-docs` command invokes the same checks on demand.

#### Structural Checks

- [ ] All requirement IDs have HTML anchors (`<a id="req-xx-nnn"></a>`)
- [ ] No implementation pseudocode in PRD
- [ ] No Java code blocks (` ```java `) in PRD
- [ ] No Java-specific constructs in PRD (streams, annotations, Spring APIs, class references)
- [ ] All cross-references use full paths with anchors
- [ ] Tables have headers and consistent column counts
- [ ] No relative references ("above", "below", "previous")
- [ ] No version numbers in documents (git handles versioning)
- [ ] ADR References use em-dashes (—) to separate links from descriptions
- [ ] ADR Implementation section includes **Requirements:** or **Non-goal:**
- [ ] Code blocks have language tags (` ```java ` not ` ``` `)

#### Abstraction Level Checks (system-design.md)

- [ ] No record field tables (`| Field | Type | Description |` rows). Purpose paragraph plus source pointer instead.
- [ ] No method parameter tables (`| Parameter | Type | Description |` rows). Contract prose plus source pointer instead.
- [ ] No constant literal values. Name the constant, cite the source file.
- [ ] No exhaustive rule listings (SQL, YAML, shell). State the invariant; source is authoritative for the full listing.
- [ ] Self-test: for each paragraph, would a field rename, parameter addition, or constant change in source silently invalidate it? If yes, rewrite or delete.

#### Structure Within a Document Checks

Per [Structure Within a Document](#structure-within-a-document):

- [ ] Each top-level heading opens with a Level 1 paragraph (≤200 words, narrative prose, no jargon) that states purpose, conclusion, and scope.
- [ ] A non-specialist can read the first 200 words of any major section and walk away with a useful understanding.
- [ ] No section jumps from Level 1 to Level 3 with more than a 5× length ratio — insert a Level 2 bridge when the gap is larger.
- [ ] Each level is self-contained: no forward references ("as explained in Section 3 below") required to understand the current level.
- [ ] Lower-level sections may use lists, tables, and diagrams, but Level 1 paragraphs are prose.

#### Cross-Document Coherence Checks

- [ ] Every REQ-XX-NNN in system-design.md exists in prd.md. Deprecated requirements absent from system-design.md.
- [ ] Constants referenced in prd.md are defined in system-design.md Constants section.
- [ ] All document links between prd.md and system-design.md resolve to valid anchors.
- [ ] Edge cases in prd.md have corresponding entries in system-design.md. Numbering is identical.
- [ ] Configuration properties in prd.md match `application.yml` in system-design.md.
- [ ] Processing pipeline steps in system-design.md cover all requirements from prd.md.

#### Writing Standards Checks

Per [Writing Standards](#writing-standards) above:

- [ ] No prohibited words without data: "significant", "substantial", "remarkable", "arguably", "might", "would help", "should result in", "some", "many", "most", "several", "various", "often", "usually", "probably", "very", "extremely", "fairly", "quite"
- [ ] No vague adjectives without data (replace with measurements)
- [ ] Sentences under 30 words maximum; 70% under 20 words
- [ ] No wordy phrases ("due to the fact that" → "because")
- [ ] Every paragraph passes the "So what?" test
- [ ] Answers start with the answer, not warmup
- [ ] Acronyms defined on first use
- [ ] No subjective language or buzzwords
