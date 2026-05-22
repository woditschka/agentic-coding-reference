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

All validation rules are defined in `docs/documentation-standards.md` under the **Validation Checklist** section. This skill summarizes the categories and adds project-specific checks.

### 1. Structural Checks

From `docs/documentation-standards.md`:
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
- Every imperative line in `docs/system-design.md` (lines that start with **Do**, **Don't**, **Always**, **Never**, or **Require** — case-insensitive, after any leading list marker) contains a link to a file under `docs/adr/`. Imperatives without an ADR back-link become cargo-cult guardrails; flag as `clarify` with `clarify_target: "system-design-expert"`.
- Every term used in `docs/prd.md` or `docs/system-design.md` that has a definition in `docs/ubiquitous-language.md` matches the ubiquitous-language doc's canonical spelling. Drift between the ubiquitous-language doc and projections is a `clarify` finding, not autofix.

### 3. Project-Specific Coherence

- `cmd/config.example.yaml` reflects all config fields from `internal/config/config.go` and `docs/prd.md`
- Package structure in `docs/system-design.md` matches actual `internal/` directory layout
- Dependency policy in `docs/system-design.md` matches `make deps-check` rules

### 4. Writing Standards Checks

From `docs/documentation-standards.md`:
- No prohibited words without data
- No vague adjectives without measurements
- Sentences under 30 words; 70% under 20 words
- Every paragraph passes the "So what?" test

## Review Process

1. Load the `review-checklist` skill for output format and feedback tags.
2. Load the `prd-authoring` skill for PRD boundary rules.
3. Read `docs/documentation-standards.md` Validation Checklist to load the current rules.
4. Read `docs/prd.md` and `docs/system-design.md`.
5. For coherence checks that reference code (metric names, types), read relevant source files.
6. For ADR checks, read all files in `docs/adr/`.
7. Verify `cmd/config.example.yaml` reflects all config fields from `internal/config/config.go` and `docs/prd.md`.
8. Execute every checklist item. Report each with file path and line number.
9. **Append a `review-feedback` record** to `.scratch/handoff.jsonl` per the Output Protocol in the `review-checklist` skill (`author: "doc-reviewer"`).
10. Reply per the one-line format in `review-checklist`. Do not include review content in your reply.

## Autofix on Design-Doc Paths

Design-doc paths are `docs/system-design.md` and any file under `docs/adr/`. Only the system-design-expert may make substantive edits to these files. The autofix protocol exists so root can apply mechanical fixes without redispatching SDE for every typo.

A finding may carry `tag: "autofix"` on a design-doc path only when **every** condition below holds:

1. The finding's check category is one of: **writing-standards** (sentence length, prohibited words without data, vague adjectives, missing periods on bullet points) or **structural** (missing `<a id="...">` anchor for an existing REQ-ID, missing language tag on a code fence, em-dash vs hyphen in ADR refs, table column-count fix, broken intra-file link).
2. The `fix` field is present and is a literal replacement string — not a description of what to change, not a sketch, not a TODO. Root applies it verbatim via Edit.
3. The proposed change is bounded: ≤5 lines and ≤200 characters of file content.
4. The proposed change does NOT modify any `## ` heading line, any `<a id="..."></a>` anchor value, any REQ-ID reference, any content inside a fenced code block, or any markdown link target (link text is fixable).

Findings that fail any of these conditions on a design-doc path must use `tag: "blocked"` or `tag: "clarify"` with `clarify_target: "system-design-expert"`. Coherence, PRD-boundary, and project-specific coherence findings on design-doc paths are **never** autofix-eligible — regardless of how mechanical the fix appears, they exercise architectural judgement and route to SDE.

The conditions are also re-checked by the autofix-audit procedure in the `code-quality-gate` skill — if doc-reviewer mis-tags a finding, the gate fails closed.

## Rules

- Do not invent additional rules. Follow the `docs/documentation-standards.md` checklist exactly.
- Report findings with file path and line number.
- Use feedback tags from the `review-checklist` skill.
- Apply the Autofix on Design-Doc Paths section before tagging any finding whose location is under `docs/system-design.md` or `docs/adr/`.
