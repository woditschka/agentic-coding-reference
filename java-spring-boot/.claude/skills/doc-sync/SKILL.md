---
name: doc-sync
description: >-
  Synchronize documentation with the current codebase. Fix drift between
  docs/prd.md, docs/system-design.md, and actual source code.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

# Doc Sync

Synchronize `docs/prd.md` and `docs/system-design.md` with the current codebase. Fix drift, add missing items, remove stale references.

## When to Run

- After implementing features or refactoring code
- Before starting a new feature cycle
- Periodically to prevent documentation drift

## Instructions

### Phase 1: Explore Current Codebase

Use the Explore agent to build a complete picture of what is implemented:

1. Read all Java source files under `src/main/java/` -- note every class, record, field, method
2. Read `src/main/resources/application.yml` for configuration properties
3. Read all template files under `src/main/resources/templates/`
4. Read all test files to understand tested behavior
5. Read all ADR files under `docs/adr/`

Capture: class names (exact casing), record fields (exact types), public vs package-private visibility, module dependencies, pipeline step ordering, CLI arguments, configuration properties, template features.

### Phase 2: Diff Against Documentation

Read `docs/prd.md`, `docs/system-design.md`, and `docs/documentation.md`.

Compare the codebase snapshot against both documents. Identify:

**In PRD:**
- Features implemented but not documented (missing requirement IDs)
- Features documented but not implemented (stale requirements)
- Configuration properties that changed, were added, or were removed
- CLI arguments that changed
- Behavioral details that drifted (thresholds, defaults, fallback logic)
- Data files that changed

**In System Design:**
- Class names that changed (case matters)
- Record fields that were added, removed, or retyped
- Module structure changes (new classes, moved classes, visibility changes)
- Pipeline step ordering drift
- Error handling changes
- Missing or stale type definitions

### Phase 3: Update Documents

Apply all fixes. Follow these rules strictly:

**Document boundaries** (from `docs/documentation.md`):
- PRD = *what* the system does. No Java code, class names, method names, annotations, or implementation constructs.
- System design = *how* it is built. Record definitions, module structure, pipeline, error handling. No verbatim service implementations.

**Writing standards** (from `CLAUDE.md`):
- No prohibited words: "significant", "arguably", "might", "would help", "should result in"
- No "some", "many", "most" without percentages
- No vague adjectives without data
- 70% of sentences under 20 words, max 30 words
- Acronyms defined on first use
- One idea per sentence

**Preservation rules:**
- Keep existing requirement IDs stable
- Add new IDs at the end of their section
- Never renumber existing IDs (downstream references depend on them)

### Phase 4: Validate

Invoke the `doc-reviewer` agent with this preamble:

> You are a read-only reviewer. Inspect files with Read, Glob, and Grep. Only permitted Bash commands: `./gradlew build`, `./gradlew test`. Do not write code, scripts, or temporary files. Never use system `/tmp`; use `.scratch/tmp/` for any temporary output.

The reviewer validates against `docs/documentation.md` checklist:
1. Structural checks (cross-references, tables, code blocks)
2. Cross-document coherence (requirement IDs, config properties, record fields, tech stack versions, class names)
3. Writing standards (prohibited words, sentence length, acronyms)
4. Document boundaries (PRD has no Java; system-design has no copied source)

### Phase 5: Fix Review Issues

Apply fixes for any `[AUTOFIX]` or `[BLOCKED]` issues the reviewer found. Re-run the reviewer if changes were substantial. Stop when the reviewer returns APPROVED.

## Output

Report a summary of changes made:
- Lines added/removed/changed per document
- New requirement IDs added
- Stale items removed
- Review result (APPROVED or remaining issues)
