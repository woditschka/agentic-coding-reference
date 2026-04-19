---
name: doc-review
description: >-
  Documentation review checklist, validation categories, and review process
  for Java Spring Boot projects. Load when conducting documentation reviews.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## Review Categories

All validation rules are defined in `docs/documentation.md` under the **Validation Checklist** section. This skill summarizes the categories and adds project-specific checks.

### 1. Structural Checks

From `docs/documentation.md`:
- All requirement IDs have HTML anchors (`<a id="req-xx-nnn"></a>`)
- No implementation pseudocode in PRD
- No Java code blocks in PRD
- No Java-specific constructs in PRD (streams, lambdas, Spring annotations)
- All cross-references use full paths with anchors
- Tables have headers and consistent column counts
- ADR references use em-dashes (not hyphens)
- Code blocks have language tags

### 2. Cross-Document Coherence Checks

- Every requirement ID in `docs/system-design.md` exists in `docs/prd.md`
- Deprecated requirements are absent from `docs/system-design.md`
- Constants referenced in `docs/prd.md` are defined in `docs/system-design.md`
- All document links resolve to valid anchors
- Configuration properties, record fields, and tech stack versions match between documents and source code

### 3. Project-Specific Coherence

- Configuration properties in `docs/system-design.md` match `src/main/resources/application.yml`
- Package structure in `docs/system-design.md` matches actual `src/main/java/` directory layout
- Record definitions referenced in `docs/system-design.md` exist in source code
- Testing principles references in `docs/testing-principles.md` match actual test patterns

### 4. Writing Standards Checks

From `docs/documentation.md`:
- No prohibited words without data
- No vague adjectives without measurements
- Sentences under 30 words; 70% under 20 words
- Every paragraph passes the "So what?" test

## Review Process

1. Load the `review-checklist` skill for output format and feedback tags.
2. Load the `prd-authoring` skill for PRD boundary rules.
3. Read `docs/documentation.md` Validation Checklist to load the current rules.
4. Read `docs/prd.md` and `docs/system-design.md`.
5. For ADR checks, read all files in `docs/adr/` (if directory exists).
6. For coherence checks, verify config properties and type definitions match between documents and source code.
7. Execute every checklist item. Report each with file path and line number.
8. Write findings to `.scratch/reviews/doc-review.md` using the template in `.claude/templates/review.md`.

## Rules

- Do not invent additional rules. Follow the `docs/documentation.md` checklist exactly.
- Report findings with file path and line number.
- Use feedback tags from the `review-checklist` skill.
