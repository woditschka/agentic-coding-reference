---
name: audit-agents
description: >-
  Audit the agentic configuration for consistency, coherence, and conciseness.
  Load when modifying agent definitions, skills, or pipeline structure,
  or to verify cross-tool parity.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "2.0"
  author: team
---

## When to Run

Run this audit after any change to:
- Agent definitions (`.claude/agents/`, `.opencode/agents/`, `.github/agents/`)
- Skills (`.claude/skills/`)
- Pipeline state files or templates (`.claude/templates/`)
- CLAUDE.md agent-related sections
- `.claude/agents/README.md`

## Audit Checklist

### 1. Skills Coverage

- [ ] CLAUDE.md skills table lists every skill in `.claude/skills/` — no missing, no extras.
- [ ] `.claude/agents/README.md` skills table matches CLAUDE.md.
- [ ] Every skill referenced in an agent file (`Load the X skill`) resolves to an existing `.claude/skills/X/SKILL.md`.

### 2. Agent Thinness

For each agent in `.claude/agents/`, `.opencode/agents/`, and `.github/agents/`:
- [ ] No inline checklists, standards, or examples that exist in a skill or doc.
- [ ] No inline design principles (belongs in `design-validation` skill).
- [ ] No duplicated build-failure handling steps (belongs in `pipeline-handoff` skill; agents reference it).
- [ ] No inline review process steps that duplicate a review skill.
- [ ] Body contains only: persona, skill references, doc references, write scope, brief process overview.
- [ ] Domain expertise lives in skills (e.g., `security-review`, `doc-review`), not inlined.
- [ ] Every reviewer agent has a dedicated domain skill.

**Grep patterns to detect violations:**

| Pattern | Where to Search | Violation |
|---|---|---|
| `\| \.scratch/` | Agent body | Inline state detection table (belongs in `pipeline-handoff` skill) |
| `- \[ \]` | Agent body | Inline checklist (belongs in a skill) |
| `\*\*Red\*\*.*failing test` | Agent body | Inline TDD process (belongs in `tdd-workflow` skill) |
| `## Review Focus` | Agent body | Inline review criteria (belongs in review skill) |
| `## PRD Boundary` | Agent body | Inline validation rules (belongs in `prd-authoring` skill) |
| `## Output Format` with template | Agent body | Inline output template (belongs in `.claude/templates/` or skill) |
| Numbered list 5+ steps duplicating skill | Agent body | Inline process (belongs in a skill) |
| `## Principles` with numbered items | Agent body (design expert) | Inline design principles (belongs in `design-validation` skill) |

### 3. Cross-Tool Parity

For each agent, compare all three tool versions (`.claude/`, `.opencode/`, `.github/`):
- [ ] Same persona text (first paragraph after frontmatter).
- [ ] Same skill references (identical skill names in body).
- [ ] Same document references (same files and sections).
- [ ] Same write scope (if defined in any version, must be in all).
- [ ] Same review process steps (same numbered list).
- [ ] Correct model mapping (sonnet→claude-sonnet-4→Claude Sonnet 4.6, opus→claude-opus-4→Claude Opus 4.6).
- [ ] Tool permissions match intent (reviewers need write for output file).

### 4. Reference Integrity

- [ ] All `docs/X.md` references point to existing files.
- [ ] All `docs/X.md#anchor` references point to existing headings.
- [ ] All `.claude/templates/X.md` references point to existing files.
- [ ] All `.scratch/` file references are consistent across agents, skills, and README.

### 5. Review Output Files

Verify these filenames match across all locations:
- Reviewer agent files (all three tools)
- `review-checklist` skill reviewer table
- `.claude/agents/README.md` agent table
- `.claude/templates/review.md` (output format)

Expected filenames:
- `code-quality-reviewer` writes `.scratch/reviews/code-quality.md`
- `test-reviewer` writes `.scratch/reviews/test-coverage.md`
- `security-reviewer` writes `.scratch/reviews/security.md`
- `doc-reviewer` writes `.scratch/reviews/doc-review.md`

### 6. No Duplication

- [ ] No skill duplicates content from another skill.
- [ ] No agent inlines content that exists in a skill it references.
- [ ] CLAUDE.md does not duplicate skill content (pointers only).
- [ ] Agent Maintenance Rules appear only in CLAUDE.md (not in README or agents).

### 7. State File Consistency

Verify state file names match across:
- `pipeline-handoff` skill state files table
- `.claude/agents/README.md` scratch directory structure
- `.claude/templates/` directory

Expected state files:
- `.scratch/current-feature.md` (product-requirements-expert)
- `.scratch/design-notes.md` (system-design-expert)
- `.scratch/implementation-plan.md` (feature-implementer)
- `.scratch/build-failure.md` (feature-implementer, deleted on success)
- `.scratch/reviews/*.md` (reviewer agents)
- `.scratch/review-summary.md` (feature-implementer)
- `.scratch/escalations.md` (feature-implementer)
- `.scratch/eval-*.md` (coordinator via feature-eval skill)

### 8. Quality Gate Consistency

Verify the quality gate matches across all locations:
- [ ] CLAUDE.md "Quality Gate" section lists all required checks.
- [ ] `.claude/skills/code-quality-gate/SKILL.md` required checks table matches CLAUDE.md.
- [ ] Code-quality-reviewer agent permitted commands include all gate checks.
- [ ] `make ci` / `./gradlew build` pipeline includes all required checks.

### 9. Pipeline Philosophy Enforcement

Verify the pipeline-handoff skill contains:
- [ ] Coordinator output format (structured recommendation template).
- [ ] Coordinator rules (no skipping stages, stale state detection, escalation reporting).
- [ ] State detection logic (file existence + status → next agent).

Verify agents do NOT contain:
- [ ] Coordinator output format (belongs in pipeline-handoff skill).
- [ ] Routing rules or state detection tables (belongs in pipeline-handoff skill).
- [ ] TDD cycle steps (belongs in tdd-workflow skill).

### 10. Reviewer Conduct

For each reviewer agent (code-quality, test, security, doc) in all three tool directories:
- [ ] Reviewer Conduct section present.
- [ ] Includes `/tmp` prohibition: "Never use system `/tmp`; use `.scratch/tmp/`".
- [ ] Lists permitted commands explicitly.
- [ ] Specifies write-only output file.

### 11. Skill Cross-References

- [ ] `doc-reviewer` agent references `doc-review` skill (for validation categories and review process).
- [ ] `doc-reviewer` agent references `prd-authoring` skill (for PRD boundary enforcement).
- [ ] `doc-reviewer` agent references `review-checklist` skill (for output format).
- [ ] `feature-implementer` agent references `tdd-workflow` skill.
- [ ] `feature-implementer` agent references `code-quality-gate` skill.
- [ ] `feature-implementer` agent references `review-checklist` skill.
- [ ] `pipeline-coordinator` agent references `pipeline-handoff` skill.
- [ ] `pipeline-coordinator` agent references `feature-eval` skill.
- [ ] `system-design-expert` agent references `design-validation` skill (for principles and checklist).

## Output Format

Report each item as:
- `[OK]` — checked and correct
- `[ISSUE]` file:line — description and fix
- `[DUPLICATION]` file:line — what is duplicated and where
