---
name: doc-review
description: >-
  Documentation review checklist, validation categories, and review process
  for Go projects. Load when conducting documentation reviews.
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
- No Go code blocks in PRD
- No Go-specific constructs in PRD (channels, goroutines, function signatures)
- All cross-references use full paths with anchors
- Tables have headers and consistent column counts
- ADR references use em-dashes (not hyphens)
- Code blocks have language tags

### 2. Cross-Document Coherence Checks

- Every requirement ID in `docs/system-design.md` exists in `docs/prd.md`
- Deprecated requirements are absent from `docs/system-design.md`
- Constants referenced in `docs/prd.md` are defined in `docs/system-design.md`
- All document links resolve to valid anchors
- Metric names, types, and constants match between documents and source code

### 3. Project-Specific Coherence

- `cmd/config.example.yaml` reflects all config fields from `internal/config/config.go` and `docs/prd.md`
- Package structure in `docs/system-design.md` matches actual `internal/` directory layout
- Dependency policy in `docs/system-design.md` matches `make deps-check` rules

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
5. For coherence checks that reference code (metric names, types), read relevant source files.
6. For ADR checks, read all files in `docs/adr/`.
7. Verify `cmd/config.example.yaml` reflects all config fields from `internal/config/config.go` and `docs/prd.md`.
8. Execute every checklist item. Report each with file path and line number.
9. Write findings to `.scratch/reviews/doc-review.md` using the template in `.claude/templates/review.md`.

## Rules

- Do not invent additional rules. Follow the `docs/documentation.md` checklist exactly.
- Report findings with file path and line number.
- Use feedback tags from the `review-checklist` skill.
