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
| `seed` | Push template into a downstream project (init + upgrade modes) |
| `harvest` | Pull generalizable improvements from a downstream project back into the template |
| `lint-docs` | On-demand documentation validation |

Report any skill present in one project but missing from the other.

### 5. Template Placeholder Check

Grep for unfilled template placeholders in both projects:

```
{{PROJECT_NAME}}
{{PROJECT_DESCRIPTION}}
```

**Expected matches** (placeholders live here by design — seed fills them when copying to downstream projects):

- `<project>/CLAUDE.md` Project Overview header
- `<project>/.claude/skills/seed/SKILL.md`, `<project>/.claude/skills/harvest/SKILL.md` (template-management skills)
- Any file listed in the seed skill's Step 2 ("Copy Structure") or Step 4 ("Copy Documentation Scaffolding")
- `<project>/Makefile` — if it provides a `seed`/`init` target using sed on placeholders
- Root `README.md` and root `.claude/skills/audit-consistency/SKILL.md` — documentation about the template system

Any match **outside** the expected set is a bug (e.g., a placeholder that was never filled after a real seed run, or a placeholder leaked into an agent/skill body).

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

### 10. Principles Doc Drift

Each sample project carries a local copy of the cross-cutting principles docs (for self-contained teaching). The generic principles must stay close to the root version; language-specific application may be appended.

| Root | Sample copies | Equivalence rule |
|---|---|---|
| `docs/tdd-principles.md` | `go/docs/tdd-principles.md`, `java-spring-boot/docs/tdd-principles.md` | Byte-equivalent to root |
| `docs/ddd-principles.md` | `go/docs/ddd-principles.md`, `java-spring-boot/docs/ddd-principles.md` | Byte-equivalent to root |
| `docs/testing-principles.md` | `go/docs/testing-principles.md`, `java-spring-boot/docs/testing-principles.md` | Generic sections match root; language-specific sections allowed after principles |

For byte-equivalent docs, check with `diff -q`. Any difference is drift — resolve by updating the root version and propagating.

For `testing-principles.md`, verify the generic principle sections (Tests Are Specifications, Four-Phase Test Structure, Test Pyramid, Mocking Policy, Test Naming, Three-Tier Data Naming Convention, Test Data Construction, Derived Expectations, Assertions, Cleanup, Testing Vocabulary, Edge Case and Boundary Testing, Agent Decision Checklist) are in sync with root wording. Language-specific content (e.g., AssertJ playbook, Go test table conventions) lives below the principles and is project-specific.

### 11. Seed Coverage

Keep each project's `.claude/skills/seed/SKILL.md` in sync with the template filesystem. Run two checks.

**Check A — every entry in the seed skill resolves to a real path.** Parse the seed skill's Step 2 ("Copy Structure") and Step 4 ("Copy Documentation Scaffolding"), plus the Gradle branch of "Build Tool Variant: Maven" Step 3 (Java only). For each file or glob, verify at least one template path matches. Unmatched entries are stale.

**Check B — every file that must be seeded is listed in the seed skill.** For each expected entry below, grep `SKILL.md` for the path. Missing entries mean freshly seeded projects will lack that file — the exact bug class Section 11 exists to prevent.

**Expected Step 2 entries (both projects):**

| Entry | Pattern to grep in SKILL.md |
|---|---|
| Root rules file | `CLAUDE.md` |
| Claude Code agents | `.claude/agents/` |
| Skills | `.claude/skills/` |
| Templates | `.claude/templates/` |
| Settings | `.claude/settings.local.json` |
| OpenCode agents | `.opencode/agents/` |
| Copilot agents | `.github/agents/` |

**Expected Step 2 build files (Java, Gradle branch):** `build.gradle`, `settings.gradle`, `gradlew`, `gradlew.bat`, `gradle/`

**Expected Step 4 entries (both projects):**

| Entry | Pattern |
|---|---|
| Product requirements | `docs/prd.md` |
| System design | `docs/system-design.md` |
| Documentation guide | `docs/documentation.md` |
| DDD principles | `docs/ddd-principles.md` |
| TDD principles | `docs/tdd-principles.md` |
| Testing principles | `docs/testing-principles.md` |
| ADR index | `docs/adr/` |

**Explicit non-seed files** (must **not** appear in Step 2 or Step 4; they're listed under "Files That Stay in Template Only" or are user code):
- `.claude/skills/harvest/`, `.claude/skills/seed/` — template management
- `src/`, `internal/`, `main.go`, `testdata/`, `bin/`, `build/`, `target/` — user code or build output
- `README.md` — project-specific (the seeded project writes its own)

**Cross-check with Upgrade Mode.** The diff category table in seed.md Upgrade Mode Step 1 must list every expected entry too, plus a **Build files** row (Java: Gradle + Maven paths; Go: either a Build files row or an explicit note that build files are not diffed). A file that Init copies but Upgrade ignores will silently drift forever in existing targets.

Report format:
- `[OK] Seed coverage — N entries listed, all resolve, all expected entries present`
- `[ISSUE] seed skill Step 2 missing: <expected-entry>`
- `[ISSUE] seed skill Step 2 references non-existent path: <listed-entry>`
- `[ISSUE] seed skill Upgrade Mode Step 1 missing category for: <expected-entry>`
- `[ISSUE] seed skill lists <path> but it's in the explicit non-seed set`

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
- [OK] Both projects have 18 skills
- [ISSUE] go/.claude/skills/tdd-workflow/ missing (present in java-spring-boot)

### Template Placeholders
- [OK] No unfilled placeholders
- [ISSUE] java-spring-boot/docs/documentation.md:7 — contains {{PROJECT_NAME}}

### Cross-Tool Parity
- [OK] All agents have matching personas across tools
- [ISSUE] go/.opencode/agents/security-reviewer.md — missing review process step 3 (present in .claude/ version)

### Principles Doc Drift
- [OK] tdd-principles.md matches root in both projects
- [ISSUE] go/docs/ddd-principles.md diverges from root at line 42

### Quality Gate
- [OK] Go: build + test + lint consistent
- [ISSUE] Java: settings.local.json missing checkJavaFormat permission

### CLAUDE.md Skills Table
- [OK] All skills listed

### Agents README
- [OK] All agents and skills listed

### Seed Coverage
- [OK] seed skill Step 2 / Step 4 entries all resolve and cover expected set
- [ISSUE] go/.claude/skills/seed/SKILL.md Step 2 missing: CLAUDE.md
- [ISSUE] java-spring-boot/.claude/skills/seed/SKILL.md Upgrade Mode diff table missing category: Copilot agents

### Summary
- X checks passed
- Y issues found
```
