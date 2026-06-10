---
name: audit-consistency
description: >-
  Audit Go and Java Spring Boot implementations for consistency with
  root-level documentation and with each other. Load when modifying
  root docs, agent definitions, skills, or pipeline structure, or to
  verify cross-project alignment.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
metadata:
  version: "1.0"
  author: team
---

## When to Run

- After editing `docs/specialist-agent-workflow.md` or `docs/agentic-harness.md`
- After adding or changing agents or skills in either project
- After migrating content from an upstream template
- Periodically to catch drift

## Audit Checklist

### 1. Root Doc Alignment

Verify both projects match the naming and structure in `docs/specialist-agent-workflow.md` and `docs/agentic-harness.md`.

**Scratch state:**

| Path | Producer | Notes |
|---|---|---|
| `.scratch/handoff.jsonl` | every pipeline agent | Append-only JSONL log; record types below |
| `.scratch/implementation-plan.md` | feature-implementer | Self-tracking only, no handoff gate |
| `.scratch/escalations.md` | feature-implementer | Human-read escalations |
| `.scratch/tmp/` | any agent | Intermediate computation; never use system `/tmp` |

**Record types in `handoff.jsonl`** (one JSON object per line, schema in `schemas/scratch/<type>.schema.json`):

| Record `type` | Producer | Purpose |
|---|---|---|
| `prd-entry` | product-requirements-expert | Active slice scope handed to SDE |
| `design-block` | system-design-expert | Triage verdict and implementation guidance handed to the implementer |
| `consultation-request` | any specialist mid-work (typically feature-implementer) | Focused question to another specialist that does not advance the pipeline |
| `consultation-response` | the consulted specialist | Focused answer; coordinator routes control back to the requester |
| `dispatch-start` | every substantive agent (as its first tool call); `pipeline-coordinator` and `change-grader` exempt | Per-dispatch start marker recording the Scoping Pre-Check |
| `build-failure` | feature-implementer | Quality-gate failure with error context and retry counter |
| `build-pass` | feature-implementer | Quality-gate success marker |
| `review-feedback` | each reviewer | Per-reviewer verdict and findings |
| `design-doc-autofix` | root (coordinator) | Audit trail for root-applied autofixes on design-doc paths |
| `grader-features` | change-grader (via `scripts/score-change.py extract`) | Deterministic structural row for the change-grade; advisory, terminal, never routes |
| `grader-verdict` | change-grader | Advisory facets, rationale, and `clear`/`concern` verdict; surfaced to the human, never routes |

The `review-feedback` record's `author` enum (`code-quality-reviewer`, `test-reviewer`, `security-reviewer`, `doc-reviewer`) is the canonical reviewer identity — there are no per-reviewer markdown files.

**Verdict enums (kept distinct):**

- `design-block.verdict` ∈ `{covered, minor, new, refactor-first, foundational, conflicting}`. The retired enum values (`needs_changes`, `revised`, `escalated`) must not appear in a design-block context — flag any occurrence. (`approved` and `blocked` remain valid for `review-feedback`; see below.)
- `review-feedback.verdict` ∈ `{approved, changes_requested, blocked}`. This is a *different* enum space from `design-block.verdict`; do not conflate.

Check these names in: `pipeline-handoff` skill, `pipeline-coordinator` agent, agents README, and the schemas directory.

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
| change-grader | `change-grader` |

Verify all 9 exist in `.claude/agents/`, `.github/agents/`, `.opencode/agents/`, and `.junie/agents/`.

**Reviewer names in root doc Section 5 (Project Structure):**
- `.claude/agents/`: `test-reviewer.md`, `doc-reviewer.md` (not `test-coverage-reviewer`, `documentation-reviewer`)
- `.github/agents/`: same stems with `.agent.md` suffix
- `.opencode/agents/`: same stems
- `.junie/agents/`: same stems

### 2. Cross-Tool Compatibility Rules

From `docs/specialist-agent-workflow.md` Section 2:

- [ ] No `AGENTS.md` file exists in either project
- [ ] No `.github/copilot-instructions.md` exists in either project
- [ ] Skills live in `.claude/skills/` only (no `.github/skills/`, no `.opencode/skills/`, no `.junie/skills/`)
- [ ] Agent definitions exist per-tool: `.claude/agents/`, `.github/agents/`, `.opencode/agents/`, `.junie/agents/`
- [ ] `CLAUDE.md` is the single rules file in each project (Junie reads it via `.junie/config.json`)

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
- [ ] product-requirements-expert: writes `docs/prd.md`, `docs/ubiquitous-language.md`, `docs/adr/*-non-goal-*.md`, `.scratch/handoff.jsonl` (`prd-entry` records; may also append `consultation-response` records when consulted by the implementer on a requirement gap)
- [ ] system-design-expert: writes `docs/system-design.md`, `docs/adr/` (excluding `*-non-goal-*.md` which belongs to PRE), `docs/ubiquitous-language.md` (only during the `foundational` triage path), `.scratch/handoff.jsonl` (`design-block` and `consultation-response` records)
- [ ] feature-implementer: writes source code, `.scratch/implementation-plan.md`, `.scratch/handoff.jsonl` (`build-failure` / `build-pass` records, and `consultation-request` records when the inner loop needs an answer mid-cycle), `.scratch/escalations.md`
- [ ] Reviewer agents: write only `.scratch/handoff.jsonl` (`review-feedback` records, append-only, with the matching `author` value)

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
| `change-grading` | Terminal advisory change-grade: how much human attention a passing change deserves before merge |
| `new-feature` | Clear scratch directory |
| `adr-template` | ADR format and governance |
| `audit-agents` | Agent config consistency |
| `doc-sync` | Synchronize docs with codebase |
| `seed` | Push template into a downstream project (init + upgrade modes) |
| `harvest` | Pull generalizable improvements from a downstream project back into the template |
| `lint-docs` | On-demand documentation validation |
| `next` | Reset scratch and recommend the next PRD requirement to tackle |
| `ship` | Commit staged changes and push to remote in one step |

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

For each agent, verify the four tool versions (`.claude/`, `.github/`, `.opencode/`, `.junie/`) have:

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

- [ ] Agent table lists all 9 agents
- [ ] Skills table lists all skills
- [ ] Scratch directory structure matches `pipeline-handoff` skill state files
- [ ] No `{{PROJECT_NAME}}` placeholders

### 10. Principles Doc Drift

Each sample project carries a local copy of the cross-cutting principles docs (for self-contained teaching). Sample projects must stand completely on their own: no sample doc may reference the other sample. The generic principles must stay close to the root version; cross-sample comparison content in the root version is replaced by a single same-sample reference in each copy, and language-specific application may be appended.

| Root | Sample copies | Equivalence rule |
|---|---|---|
| `docs/tdd-principles.md` | `go/docs/tdd-principles.md`, `java-spring-boot/docs/tdd-principles.md` | Generic content matches root; the "How This Relates to Project-Level Docs" section keeps only the same-sample reference (no cross-sample bullet) |
| `docs/ddd-principles.md` | `go/docs/ddd-principles.md`, `java-spring-boot/docs/ddd-principles.md` | Same rule as above |
| `docs/testing-principles.md` | `go/docs/testing-principles.md`, `java-spring-boot/docs/testing-principles.md` | Generic sections match root; the "How This Relates" section keeps only the same-sample reference; language-specific sections allowed after principles |
| `docs/agentic-harness.md` | `go/docs/agentic-harness.md`, `java-spring-boot/docs/agentic-harness.md` | Byte-identical across all three copies; the `schemas/scratch/` reference is location-neutral prose with no relative link |

Verify with `diff` — diffs are expected only on (a) the cross-sample comparison lines that the root version carries but samples must not, and (b) local relative-link adjustments needed for the link to resolve from each location. Any other difference is drift.

**Self-containment grep.** Each sample doc must contain no reference to the other sample. From `go/docs/`, `grep -l 'java-spring-boot' *.md` must return nothing. From `java-spring-boot/docs/`, `grep -l '\bgo/' *.md` must return nothing.

For `testing-principles.md`, verify the generic principle sections (Tests Are Specifications, Four-Phase Test Structure, Test Pyramid, Mocking Policy, Test Naming, Three-Tier Data Naming Convention, Test Data Construction, Derived Expectations, Assertions, Cleanup, Testing Vocabulary, Edge Case and Boundary Testing, Agent Decision Checklist) are in sync with root wording. Language-specific content (e.g., AssertJ playbook, Go test table conventions) lives below the principles and is project-specific.

For `agentic-harness.md`, the byte-equivalence check here is necessary but not sufficient. The doc is the bar for what the deployed harness should look like; Section 15 below verifies the sample contents reflect what the doc says.

### 11. Consultation Routing Semantics

The consultation roundtrip lets a specialist mid-work (typically `feature-implementer`) get a focused answer from another specialist (typically `system-design-expert`) without advancing the pipeline. Verify the semantics are consistently described across both samples:

- [ ] `pipeline-handoff` skill: documents a gate for `consultation-request` and `consultation-response` records; states that after a `consultation-response` the coordinator routes control **back to the requesting specialist** named in the corresponding request, not forward to the next pipeline stage.
- [ ] `pipeline-coordinator` agent (all four tool versions): validation step recognizes the two consultation record types and follows the back-route semantics above.
- [ ] `tdd-workflow` skill: the design-check decision tree directs the implementer to append a `consultation-request` rather than block waiting; the inner loop resumes when the matching `consultation-response` arrives.
- [ ] `design-validation` skill: describes both triage mode (returns one of the six `design-block` verdicts) and consultation mode (returns a `consultation-response`); the agent branches on the input record type.
- [ ] `system-design-expert` agent: write scope explicitly allows appending `consultation-response` records; `docs/ubiquitous-language.md` is in scope **only** during the `foundational` triage path.
- [ ] `consultation-request.schema.json` and `consultation-response.schema.json` exist in both samples' `schemas/scratch/` directories with required fields matching the skill/agent descriptions.

### 12. SDE Triage Verdicts

Verify the six `design-block` verdicts are described consistently:

- [ ] `system-design-expert` agent (all four tool versions, both samples) names triage + consultation as the two modes and lists the six verdicts.
- [ ] `design-validation` skill enumerates the six verdicts with content guidance per verdict.
- [ ] `docs/agentic-harness.md` § The system-design-expert role in depth (root + both samples) lists the same six verdicts.
- [ ] `design-block.schema.json` (both samples) enum exactly matches the six verdict names: `covered`, `minor`, `new`, `refactor-first`, `foundational`, `conflicting`.
- [ ] The `foundational` path covers both greenfield projects and adoption (extracting candidate vocabulary from existing docs and source); same description across the SDE agent, `design-validation`, and `agentic-harness.md`.

### 13. Seed Coverage

Keep each project's `.claude/skills/seed/SKILL.md` in sync with the template filesystem. Run two checks.

**Check A — every entry in the seed skill resolves to a real path.** Parse the seed skill's Step 2 ("Copy Structure") and Step 4 ("Copy Documentation Scaffolding"), plus the Gradle branch of "Build Tool Variant: Maven" Step 3 (Java only). For each file or glob, verify at least one template path matches. Unmatched entries are stale.

**Check B — every file that must be seeded is listed in the seed skill.** For each expected entry below, grep `SKILL.md` for the path. Missing entries mean freshly seeded projects will lack that file — the exact bug class Section 13 exists to prevent.

**Expected Step 2 entries (both projects):**

| Entry | Pattern to grep in SKILL.md |
|---|---|
| Root rules file | `CLAUDE.md` |
| Claude Code agents | `.claude/agents/` |
| Skills | `.claude/skills/` |
| Templates | `.claude/templates/` |
| Settings | `.claude/settings.local.json` |
| Copilot agents | `.github/agents/` |
| OpenCode agents | `.opencode/agents/` |
| Junie agents | `.junie/agents/` |
| Junie config | `.junie/config.json` |

**Expected Step 2 build files (Java, Gradle branch):** `build.gradle`, `settings.gradle`, `gradlew`, `gradlew.bat`, `gradle/`

**Expected Step 4 entries (both projects):**

| Entry | Pattern |
|---|---|
| Product requirements | `docs/prd.md` |
| System design | `docs/system-design.md` |
| Ubiquitous language | `docs/ubiquitous-language.md` |
| Agentic harness overview | `docs/agentic-harness.md` |
| Documentation standards | `docs/documentation-standards.md` |
| DDD principles | `docs/ddd-principles.md` |
| TDD principles | `docs/tdd-principles.md` |
| Testing principles | `docs/testing-principles.md` |
| ADR index | `docs/adr/` |
| Handoff schemas | `schemas/scratch/` (11 schema files: prd-entry, design-block, consultation-request, consultation-response, dispatch-start, review-feedback, build-failure, build-pass, design-doc-autofix, grader-features, grader-verdict) |

**ADR placement** (enforces ADR `2026-06-07-adr-placement` in the root decision log). Each sample's `docs/adr/` contains exactly one ADR — the dated `*-skill-based-agent-architecture.md` seed — plus `README.md`. Flag any per-capability or build-history ADR that appears in a sample. The reference's full decision log lives at root `docs/adr/`; harness decisions are recorded there, not seeded into the samples. Grep: `ls go/docs/adr java-spring-boot/docs/adr` should each show one dated ADR + `README.md`.

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

### 14. Root Reference Integrity

The rule is uniform: **every path-shaped string in root-level files must resolve to an existing file or directory** at the project root. Path-shaped means a token containing `/` and ending in a known extension (`.md`, `.go`, `.java`, `.yaml`, `.yml`, `.json`, `.jsonl`, `.sh`) or referring to a known directory (`docs/`, `.claude/`, `tools/`, `schemas/`, `go/`, `java-spring-boot/`).

This section covers references in **root-level** files only. References inside each sample (e.g., `go/.claude/agents/...` pointing to `go/docs/...`) are handled by that sample's `audit-agents` skill. Cross-sample references from root files (e.g., a root doc linking to `go/CLAUDE.md`) are caught here.

- [ ] Every path-shaped reference in `.claude/skills/`, `CLAUDE.md`, `README.md`, `docs/`, and `tools/` resolves to a real file or directory at the project root.
- [ ] Every `docs/X.md#anchor` reference (including cross-sample anchors like `go/docs/system-design.md#section`) points to an existing heading or `<a id="...">` anchor.
- [ ] **Self-audit:** apply the same check to this skill (`.claude/skills/audit-consistency/SKILL.md`). Stale references in the audit skill itself propagate into every audit run.

Use grep to find candidates:

```
grep -rohE '[A-Za-z0-9_./-]+\.(md|go|java|ya?ml|json|jsonl|sh)' \
  .claude/ CLAUDE.md README.md docs/ tools/ | sort -u
```

Then check each against the filesystem. Same for directory references.

### 15. Sample Harness Reflects `docs/agentic-harness.md`

`docs/agentic-harness.md` is the bar for what the deployed harness (`.claude/`, `schemas/scratch/`) should look like and how it should behave. Section 10 verifies the doc itself is byte-equivalent across copies. This section is the deeper check: **read the doc and verify the sample contents reflect what it says**.

How to run the check:

1. Read `docs/agentic-harness.md` end-to-end.
2. For each claim that is checkable against sample contents — write-scope tables, record-type lists, do/don't pairs, named contracts, prohibitions stated with positive and negative examples — verify the samples reflect it.
3. Claims with explicit "do this / not this" examples turn into greps; structural claims (record schemas, verdict enums, agent roster) check against the filesystem.
4. Report anything that violates the doc's stated rules or contradicts its examples.

Two recurring patterns from the doc, as worked examples of how a claim turns into a grep:

- *Self-containment of the deployed harness.* The doc says agent prompts, skills, and schema descriptions don't cite specific ADR files or specific REQ identifiers — those couple the portable harness to a host project's historical record. Exemptions: `docs/adr/` as a write-scope or path-pattern mention is fine. Grep: `grep -rn -E 'docs/adr/[a-z0-9-]+\.md' <sample>/.claude/agents/ <sample>/.claude/skills/` and classify each match against the doc's exemption list.
- *Tool-agnostic prose.* The doc says concrete numeric budgets live in agent front-matter; prose uses generic phrasing. Skills name `toolCallBudget` without citing a value. Harness-level structural constants (retry count, reviewer count, verdict count) are fine. Grep agent bodies and skill prose for digits adjacent to `toolCallBudget`, `maxTurns`, `budget`, or `tool call`, and classify.

These illustrate the *shape* of the check; new contracts, do/don't pairs, or named rules added to the doc fall under the same mandate.

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
- [ISSUE] java-spring-boot/docs/documentation-standards.md:7 — contains {{PROJECT_NAME}}

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

### Root Reference Integrity
- [OK] All root-level path-shaped references resolve
- [ISSUE] docs/agentic-harness.md:312 — references `../tools/old-name/` (does not exist)
- [ISSUE] .claude/skills/audit-consistency/SKILL.md:NN — self-audit found broken anchor `#removed-section`

### Sample Harness Reflects docs/agentic-harness.md
- [OK] Self-containment — no specific ADR/REQ citations in agent or skill prose
- [OK] Tool-agnostic prose — numeric budgets in front-matter, generic phrasing in prose
- [ISSUE] go/.claude/skills/pipeline-handoff/SKILL.md:52 cites `docs/adr/2026-06-07-skill-based-agent-architecture.md` as rationale — doc says harness states *what*, ADRs state *why*
- [ISSUE] java-spring-boot/.claude/agents/system-design-expert.md:48 hardcodes `27` in prose — doc says concrete values stay in front-matter

### Summary
- X checks passed
- Y issues found
```
