---
name: lint-docs
description: >-
  Audit all documentation, agent configs, skills, and CLAUDE.md for
  consistency, coherence, correct abstraction levels, and writing quality.
  Load when the user asks to lint, validate, or audit project documentation.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
metadata:
  version: "1.0"
  author: team
---

# Lint Docs

Audit all documentation, agent configs, skills, and CLAUDE.md for consistency, coherence, correct abstraction levels, and writing quality.

## Scope

### 1. System Design Abstraction (system-design.md)

Read `docs/system-design.md` and check:

- **No verbatim source code.** Package implementations, build scripts, and test bodies copied from source files are violations. Type definitions for domain records are allowed — they are the design contract.
- **Design-level descriptions only.** Sections should use contracts, algorithms, schemas, patterns, and tables — not runnable code.
- **Compare against source.** For each Go code block in system-design.md, check if a corresponding source file exists under `internal/`, `cmd/`, or at the repo root (e.g., `main.go`). If it does, the code block is a duplication that will go stale.

### 2. PRD Boundary (prd.md)

Read `docs/prd.md` and check:

- **No Go code blocks** (` ```go `).
- **No implementation language.** No package names, function signatures, type names, Go idioms (goroutines, channels, contexts), stdlib APIs, regex patterns.
- **Outcome language.** Descriptions should describe outcomes, not mechanisms.

### 3. CLAUDE.md Lean Check

Read `CLAUDE.md` and check:

- **No embedded pipeline logic.** Routing tables, handoff conditions, and feedback tags should live in skills, not CLAUDE.md.
- **No embedded writing standards.** Should be a pointer to `docs/documentation-standards.md#writing-standards`.
- **No embedded reviewer conduct.** Should be in agent definitions or skills.
- **Skills table matches.** Every skill in `.claude/skills/` appears in the CLAUDE.md skills table. No extras, no missing.

### 4. Agent Thinness

Read all files in `.claude/agents/` and check:

- **No inline checklists.** Checklists that exist in a skill (e.g., `code-quality-review`) must not be inlined in the agent.
- **Skill references resolve.** Every `Load the X skill` in an agent resolves to `.claude/skills/X/SKILL.md`.
- **Document references valid.** Each agent's referenced files exist.
- **Build commands.** Build-related commands referenced in agents (permitted Bash patterns or quality-gate prose) match the commands declared in `CLAUDE.md` Quality Gate (`make ci`, `make lint`, `make test`).

### 5. Cross-Tool Parity

Compare each agent across all four tool directories: `.claude/agents/`, `.github/agents/`, `.opencode/agents/`, and `.junie/agents/`.

- **Same persona text** (first paragraph after frontmatter).
- **Same skill references** (identical skill names).
- **Same process steps** (same numbered list).
- **Correct model mapping.** Each tier maps across tools as follows; flag only deviations from this table:

  | Tier | Claude Code | GitHub Copilot | OpenCode | Junie |
  |------|-------------|----------------|----------|-------|
  | Sonnet | `sonnet` | `Claude Sonnet 4.6 (copilot)` | `openrouter/anthropic/claude-sonnet-4` | `sonnet` |
  | Opus | `opus` | `Claude Opus 4.6 (copilot)` | `openrouter/anthropic/claude-opus-4` | `opus` |

  The minor-version asymmetry (OpenRouter alias resolves dynamically, Copilot pins explicitly) is intentional. Do not flag it.
- **Tool-name capitalization is tool-local.** Each tool's `write` / `Write` tool name is correct in its own files. Do not flag capitalization differences across tools.

### 6. Cross-Document Consistency

Verify these invariants hold across documents:

- Requirement IDs referenced in system-design.md exist in prd.md.
- State file names match across pipeline-coordinator, pipeline-handoff skill, and agents README.
- Reviewer `author` enum values match across reviewer agents, review-checklist skill, agents README, and `schemas/scratch/review-feedback.schema.json`.
- Schema files (`schemas/scratch/*.json`) are referenced consistently from the skills that produce or consume each record type.

### 7. Writing Standards

Check all documents in `docs/` and `CLAUDE.md` for:

- **Prohibited words:** "significant", "substantial", "remarkable", "arguably", "might", "would help", "should result in", "some", "many", "most", "several", "various", "often", "usually", "probably", "very", "extremely", "fairly", "quite" (without data).
- **Vague adjectives without data:** Replace with measurements per `docs/documentation-standards.md`.
- **Sentence length:** Maximum 30 words. 70% of sentences should be under 20 words.

Full validation checklist: `docs/documentation-standards.md` (Validation Checklist section).

### 8. Section Brevity

Apply the section-scope "So What?" rule from `docs/documentation-standards.md#apply-so-what-at-section-scope`.

For `docs/system-design.md` and `docs/prd.md`, count lines per section (block bounded by sibling-or-higher Markdown heading). Flag every section over 100 lines as a candidate for review. Section length alone is not a finding — Implementation Order tables, multi-axis contracts, and Level 3 detail blocks may legitimately exceed the threshold.

For each flagged section, dispatch a sub-agent to apply the section-scope "So What?" test:

- Could two adjacent paragraphs collapse to one?
- Could a prose block become a table?
- Does any rule appear in more than one section without a cross-reference?

The sub-agent returns advisory findings only (`[BREVITY]` severity). Do not block on this check; long sections that survive review are not violations.

## Output

Report findings organized by area. For each issue, state:
- **File and line** (e.g., `.claude/agents/test-reviewer.md:44`)
- **What is wrong** (e.g., "Skill reference 'code-quality-review' not found")
- **Severity**: `[STALE]` for outdated references, `[DUPLICATION]` for content that belongs elsewhere, `[BOUNDARY]` for abstraction-level violations, `[INCONSISTENCY]` for cross-document mismatches, `[PARITY]` for cross-tool mismatches, `[STYLE]` for writing standards violations, `[BREVITY]` for section-scope "So What?" findings

If all checks pass, state: "All documentation health checks passed."
