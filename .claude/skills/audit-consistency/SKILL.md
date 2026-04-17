---
name: audit-consistency
description: >-
  Audit Go and Java Spring Boot implementations for consistency with
  root-level documentation and with each other. Load when modifying
  root docs, agent definitions, skills, or pipeline structure, or to
  verify cross-project alignment.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## When to Run

- After editing `docs/specialist-agent-workflow.md`
- After adding or changing agents or skills in either project
- After migrating content from an upstream template
- Periodically to catch drift

## Audit Checklist

### 1. Root Doc Alignment

Verify both projects match the naming and structure in `docs/specialist-agent-workflow.md`.

**Scratch file names:**

| Root Doc Name | Expected In Projects |
|---|---|
| `.scratch/current-feature.md` | product-requirements-expert output |
| `.scratch/design-notes.md` | system-design-expert output |
| `.scratch/implementation-plan.md` | feature-implementer output |
| `.scratch/review-summary.md` | feature-implementer consolidation |
| `.scratch/escalations.md` | feature-implementer escalations |
| `.scratch/reviews/security.md` | security-reviewer output |
| `.scratch/reviews/code-quality.md` | code-quality-reviewer output |
| `.scratch/reviews/test-coverage.md` | test-reviewer output |
| `.scratch/reviews/doc-review.md` | doc-reviewer output |
| `.scratch/build-failure.md` | feature-implementer failure output (deleted on success) |
| `.scratch/eval-*.md` | coordinator evaluation scorecard (via feature-eval skill) |

Check these names in: pipeline-handoff skill, pipeline-coordinator agent, agents README, templates directory.

**Agent names:**

| Root Doc Name | File Stem |
|---|---|
| pipeline-coordinator | `pipeline-coordinator` |
| product-requirements-expert | `product-requirements-expert` |
| system-design-expert | `system-design-expert` |
| feature-implementer | `feature-implementer` |
| security-reviewer | `security-reviewer` |
| code-quality-reviewer | `code-quality-reviewer` |
| test-reviewer | `test-reviewer` |
| doc-reviewer | `doc-reviewer` |

Verify all 8 exist in `.claude/agents/`, `.opencode/agents/`, and `.github/agents/`.

**Reviewer names in root doc Section 5 (Project Structure):**
- `.claude/agents/`: `test-reviewer.md`, `doc-reviewer.md` (not `test-coverage-reviewer`, `documentation-reviewer`)
- `.opencode/agents/`: same stems
- `.github/agents/`: same stems with `.agent.md` suffix

### 2. Cross-Tool Compatibility Rules

From `docs/specialist-agent-workflow.md` Section 2:

- [ ] No `AGENTS.md` file exists in either project
- [ ] No `.github/copilot-instructions.md` exists in either project
- [ ] Skills live in `.claude/skills/` only (no `.opencode/skills/`, no `.github/skills/`)
- [ ] Agent definitions exist per-tool: `.claude/agents/`, `.opencode/agents/`, `.github/agents/`
- [ ] `CLAUDE.md` is the single rules file in each project

### 3. Agent Thinness

From `docs/specialist-agent-workflow.md` Section 2 and Section 8:

> "Keep the workflow intelligence in skills (portable) and keep agent definitions thin — just persona, tool restrictions, and model choice."

For each agent in both projects, verify:

- [ ] No inline checklists (review criteria, validation rules, security checks)
- [ ] No state detection tables (belongs in `pipeline-handoff` skill)
- [ ] No output format templates (belongs in `.claude/templates/` or skills)
- [ ] No TDD process steps (belongs in `tdd-workflow` skill)
- [ ] No routing rules (belongs in `pipeline-handoff` skill)
- [ ] No inline design principles (belongs in `design-validation` skill)
- [ ] No duplicated build-failure handling steps (belongs in `pipeline-handoff` skill; agents reference the skill)
- [ ] No inline review process steps that duplicate a review skill (e.g., `doc-review`, `security-review`)
- [ ] Body contains only: persona, skill references, doc references, write scope, brief process overview pointing to skills
- [ ] Every reviewer agent has a dedicated domain skill (code-quality-review, test-review, security-review, doc-review)

**Grep patterns to detect violations:**

| Pattern | Location | Violation |
|---|---|---|
| `\| .scratch/` in agent files | Agent body | Inline state detection table |
| `- \[ \]` in agent files | Agent body | Inline checklist |
| `\*\*Red\*\*.*failing test` | Agent body | Inline TDD process |
| `## Review Focus` | Agent body | Inline review criteria |
| `## PRD Boundary` | Agent body | Inline validation rules |
| `## Output Format` with markdown template | Agent body | Inline output template |
| Numbered list with 5+ steps duplicating skill content | Agent body | Inline process that belongs in a skill |
| `## Principles` with numbered items | Agent body (design expert) | Inline design principles (belongs in `design-validation` skill) |

**Write Scope check:**

Every agent that writes files must have a `## Write Scope` section listing permitted paths and an explicit prohibition. Verify:
- [ ] product-requirements-expert: writes `docs/prd.md`, `.scratch/current-feature.md`
- [ ] system-design-expert: writes `docs/system-design.md`, `docs/adr/`, `.scratch/design-notes.md`
- [ ] feature-implementer: writes source code, `.scratch/implementation-plan.md`, `.scratch/build-failure.md`
- [ ] Reviewer agents: write only `.scratch/reviews/{name}.md`

### 4. Skill Parity

Both projects must have the same set of portable skills. Compare `.claude/skills/` directories.

**Expected skills (both projects):**

| Skill | Purpose |
|---|---|
| `pipeline-handoff` | Routing table, handoff conditions, build-failure recovery, state files |
| `tdd-workflow` | TDD cycle, design-check decision tree, document ownership |
| `prd-authoring` | PRD format, boundary rules |
| `code-quality-gate` | Build/test/lint requirements, completion criteria |
| `review-checklist` | Feedback tags, review output format, review process |
| `code-quality-review` | Language-specific code quality checklist |
| `test-review` | Test quality checklist |
| `security-review` | Security checklists, threat model, severity |
| `doc-review` | Documentation review checklist, validation categories |
| `design-validation` | Design principles, architectural validation checklist |
| `feature-eval` | Feature evaluation scorecard after review gate |
| `new-feature` | Clear scratch directory |
| `adr-template` | ADR format and governance |
| `audit-agents` | Agent config consistency |
| `doc-sync` | Synchronize docs with codebase |

Report any skill present in one project but missing from the other.

### 5. Template Placeholder Check

Grep for unfilled template placeholders in both projects:

```
{{PROJECT_NAME}}
{{PROJECT_DESCRIPTION}}
```

Any match outside of template/seed command files is a bug.

### 6. Cross-Tool Parity (per project)

For each agent, verify the three tool versions (`.claude/`, `.opencode/`, `.github/`) have:

- [ ] Same persona text (first paragraph after frontmatter)
- [ ] Same skill references
- [ ] Same reference documents
- [ ] Same write scope (if defined in any version, must be in all)
- [ ] Reviewer conduct section present in all reviewer agents
- [ ] Appropriate model mapping (opus→opus, sonnet→sonnet)
- [ ] Appropriate tool permission mapping

### 7. Quality Gate Consistency

Verify the quality gate in each project matches across all locations:

**Go project:**
- `CLAUDE.md` "Quality Gate" section
- `.claude/skills/code-quality-gate/SKILL.md` required checks
- code-quality-reviewer agent permitted Bash commands

**Java project (must include format check):**
- `CLAUDE.md` "Quality Gate" section
- `.claude/skills/code-quality-gate/SKILL.md` required checks (must include `checkJavaFormat`)
- code-quality-reviewer agent permitted Bash commands (must include `checkJavaFormat`)
- `.claude/settings.local.json` permissions (must include `formatJava` and `checkJavaFormat`)

### 8. CLAUDE.md Skills Table

Verify the skills table in each project's `CLAUDE.md` lists every skill in `.claude/skills/`.

- [ ] Every directory in `.claude/skills/` has a row in the table
- [ ] No table row references a skill that doesn't exist

### 9. Agents README Consistency

Verify `.claude/agents/README.md` in each project:

- [ ] Agent table lists all 8 agents
- [ ] Skills table lists all skills
- [ ] Scratch directory structure matches `pipeline-handoff` skill state files
- [ ] No `{{PROJECT_NAME}}` placeholders

## Output Format

```
## Sync Audit: [date]

### Root Doc Alignment
- [OK] Scratch file names match
- [ISSUE] go/.claude/agents/pipeline-coordinator.md:42 — references `.scratch/prd-handoff.md`, should be `.scratch/current-feature.md`

### Cross-Tool Compatibility
- [OK] No AGENTS.md
- [OK] Skills in .claude/skills/ only

### Agent Thinness
- [OK] All agents are thin
- [ISSUE] go/.claude/agents/code-quality-reviewer.md:38 — inline Review Focus checklist (belongs in code-quality-review skill)

### Skill Parity
- [OK] Both projects have 15 skills
- [ISSUE] go/.claude/skills/tdd-workflow/ missing (present in java-spring-boot)

### Template Placeholders
- [OK] No unfilled placeholders
- [ISSUE] java-spring-boot/docs/documentation.md:7 — contains {{PROJECT_NAME}}

### Cross-Tool Parity
- [OK] All agents have matching personas across tools
- [ISSUE] go/.opencode/agents/security-reviewer.md — missing review process step 3 (present in .claude/ version)

### Quality Gate
- [OK] Go: build + test + lint consistent
- [ISSUE] Java: settings.local.json missing checkJavaFormat permission

### CLAUDE.md Skills Table
- [OK] All skills listed

### Agents README
- [OK] All agents and skills listed

### Summary
- X checks passed
- Y issues found
```
