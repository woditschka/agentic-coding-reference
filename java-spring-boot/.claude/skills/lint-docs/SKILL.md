---
name: lint-docs
description: >-
  Audit all documentation, agent configs, skills, and CLAUDE.md for
  consistency, coherence, correct abstraction levels, and writing quality.
  Load when the user asks to lint, validate, or audit project documentation.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

# Lint Docs

Audit all documentation, agent configs, skills, and CLAUDE.md for consistency, coherence, correct abstraction levels, and writing quality.

## Scope

### 1. System Design Abstraction (system-design.md)

Read `docs/system-design.md` and check:

- **No verbatim source code.** Service implementations, build scripts, and test bodies copied from source files are violations. Domain record definitions are allowed — they are the design contract.
- **Design-level descriptions only.** Sections should use contracts, algorithms, schemas, patterns, and tables — not runnable code.
- **Compare against source.** For each Java code block in system-design.md, check if a corresponding source file exists in `src/`. If it does, the code block is a duplication that will go stale.

### 2. PRD Boundary (prd.md)

Read `docs/prd.md` and check:

- **No Java code blocks** (` ```java `).
- **No implementation language.** No class names, method names, annotations, streams, Spring APIs, regex patterns.
- **Outcome language.** Descriptions should describe outcomes, not mechanisms.

### 3. CLAUDE.md Lean Check

Read `CLAUDE.md` and check:

- **No embedded pipeline logic.** Routing tables, handoff conditions, and feedback tags should live in skills, not CLAUDE.md.
- **No embedded writing standards.** Should be a pointer to `docs/documentation.md#writing-standards`.
- **No embedded reviewer conduct.** Should be in agent definitions or skills.
- **Skills table matches.** Every skill in `.claude/skills/` appears in the CLAUDE.md skills table. No extras, no missing.

### 4. Agent Thinness

Read all files in `.claude/agents/` and check:

- **No inline checklists.** Checklists that exist in a skill (e.g., `code-quality-review`) must not be inlined in the agent.
- **Skill references resolve.** Every `Load the X skill` in an agent resolves to `.claude/skills/X/SKILL.md`.
- **Document references valid.** Each agent's referenced files exist.
- **Permitted Gradle commands.** Reviewer agents must permit only `./gradlew build`, `./gradlew test`, and `./gradlew checkJavaFormat`.

### 5. Cross-Tool Parity

Compare `.claude/agents/` against `.opencode/agents/`:

- **Same persona text** (first paragraph after frontmatter).
- **Same skill references** (identical skill names).
- **Same process steps** (same numbered list).
- **Correct model mapping** (sonnet = claude-sonnet-4, opus = claude-opus-4).

### 6. Cross-Document Consistency

Verify these invariants hold across documents:

- Requirement IDs referenced in system-design.md exist in prd.md.
- Configuration properties in prd.md match `application.yml`.
- State file names match across pipeline-coordinator, pipeline-handoff skill, and agents README.
- Review output filenames match across reviewer agents, review-checklist skill, and agents README.

### 7. Writing Standards

Check all documents in `docs/` and `CLAUDE.md` for:

- **Prohibited words:** "significant", "substantial", "remarkable", "arguably", "might", "would help", "should result in", "some", "many", "most", "several", "various", "often", "usually", "probably", "very", "extremely", "fairly", "quite" (without data).
- **Vague adjectives without data:** Replace with measurements per `docs/documentation.md`.
- **Sentence length:** Maximum 30 words. 70% of sentences should be under 20 words.

Full validation checklist: `docs/documentation.md` (Validation Checklist section).

## Output

Report findings organized by area. For each issue, state:
- **File and line** (e.g., `.claude/agents/test-reviewer.md:44`)
- **What is wrong** (e.g., "Skill reference 'code-quality-review' not found")
- **Severity**: `[STALE]` for outdated references, `[DUPLICATION]` for content that belongs elsewhere, `[BOUNDARY]` for abstraction-level violations, `[INCONSISTENCY]` for cross-document mismatches, `[PARITY]` for cross-tool mismatches, `[STYLE]` for writing standards violations

If all checks pass, state: "All documentation health checks passed."
