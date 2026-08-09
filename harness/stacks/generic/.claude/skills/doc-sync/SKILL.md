---
name: doc-sync
description: >-
  Synchronize documentation with the current codebase. Fix drift between
  docs/prd.md, docs/system-design.md, and actual source code.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/prd.md
  - docs/system-design.md
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

Build a complete picture of what is implemented — via a read-only exploration subagent where the tool offers one (Claude Code: Explore), else by reading directly:

1. Read all production source files (the roots declared in `scripts/layout.toml`) -- note every type, interface, function, field
2. Read the project's configuration files where they exist (the config example and config module the project defines)
3. Read all test files to understand tested behavior
4. Read all ADR files under `docs/adr/`

Capture: type names (exact casing), type and interface fields (exact types), public vs internal visibility, module dependencies, pipeline step ordering, CLI arguments, configuration properties.

### Phase 2: Diff Against Documentation

Read `docs/prd.md` and `docs/system-design.md`.

Compare the codebase snapshot against both documents. Identify:

**In PRD:**
- Features implemented but not documented (missing requirement IDs)
- Features documented but not implemented (stale requirements)
- Configuration properties that changed, were added, or were removed
- CLI arguments that changed
- Behavioral details that drifted (thresholds, defaults, fallback logic)

**In System Design:**
- Type names that changed (case matters)
- Type fields that were added, removed, or retyped
- Module structure changes (new modules, moved files, visibility changes)
- Pipeline step ordering drift
- Error handling changes
- Contracts-table entries out of sync with source (types or interfaces renamed, added, or removed)

### Phase 3: Update Documents

Apply all fixes. Follow these rules strictly:

**Document boundaries** (per the harness-project API roster; form rules in the `document-writing` skill):
- PRD = *what* the system does. No source code, function names, type names, or implementation constructs.
- System design = *how* it is built: contracts (purpose plus source pointer), module structure, pipeline, error handling. Source is authoritative for type and function definitions; never copy them.

**Writing standards** (from the `document-writing` skill):
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

> You are a read-only reviewer. Inspect files read-only with your file-viewing and search tools. Only permitted Bash commands: `scripts/gate.sh verify`. Do not write code, scripts, or temporary files. Never use system `/tmp`; use `.scratch/tmp/` for any temporary output.

The reviewer validates against the `document-writing` skill's checklist:
1. Structural checks (cross-references, tables, code blocks)
2. Cross-document coherence (requirement IDs, config properties, type fields, constants)
3. Writing standards (prohibited words, sentence length, acronyms)
4. Document boundaries (PRD has no source code; system-design has no copied source)

### Phase 5: Fix Review Issues

Apply fixes for any `[AUTOFIX]` or `[BLOCKED]` issues the reviewer found. Re-run the reviewer if changes were substantial. Stop when the reviewer returns APPROVED.

## Maintenance Rules, Compaction, Format Migration

The stack-independent half of this skill lives in [`maintenance.md`](maintenance.md) beside this file: the Maintenance Rules table, the Compaction procedure, and the Format Migration procedure. Read it whenever the task is maintenance, compaction, or migration; the phases above stay stack-bound, and the Instructions above name this stack's Contracts-table constructs.

## Output

Report a summary of changes made:
- Lines added/removed/changed per document
- New requirement IDs added
- Stale items removed
- Review result (APPROVED or remaining issues)
