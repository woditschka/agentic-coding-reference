---
name: document-writing
description: >-
  How to write and review project documents: the language-agnostic writing
  standards, the five-document architecture and ownership boundaries, the
  document-structure model, cross-reference and maintenance rules, and the
  review checklist the doc-reviewer enforces. Load when authoring or reviewing
  any PRD, system-design doc, ADR, brief, or CLAUDE.md.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/prd.md
  - docs/system-design.md
  - docs/ubiquitous-language.md
metadata:
  version: "1.0"
  author: team
---

This skill is the single home of documentation discipline, serving two consumers from one source. The standard itself — the writing rules, the five-document architecture, the ownership boundaries, and the cross-reference and maintenance rules — lives in [`documentation-standards.md`](documentation-standards.md). Every document-producing agent and skill **follows** it when authoring; the `doc-reviewer` **enforces** it on review, together with the stack-specific checks in [`review-checks.md`](review-checks.md) — a stack overlay each stack ships beside this skill (the stack-agnostic core source carries none). This file carries the agent obligations and the author's validation checklist. Author and reviewer read the same rulebook.

## Agent Guidelines

These rules bind any agent that reads or writes project documentation. They restate the ownership and abstraction boundaries from [`documentation-standards.md`](documentation-standards.md) as direct obligations.

Agents must:
- Read PRD requirements before implementing
- Reference system-design.md for types and interfaces
- Check ADRs for design constraints before proposing alternatives
- Never duplicate type definitions across documents
- Never add code or language-specific constructs to PRD
- Never reference internal code in PRD (no class names, function names, or variable names)
- Use behavioral language in PRD ("the system retries the operation" not "`Retry()` calls `continue`")
- When PRD needs to reference implementation details, add a link: `**Design:** See [system-design.md#section](system-design.md#section)`

## Validation Checklist

This is the author's self-check before merging a documentation change. The `doc-reviewer` enforces the same bar at review time, with stack-specific additions, from [`review-checks.md`](review-checks.md). Before merging, verify:

### Structural Checks

- [ ] All requirement IDs have HTML anchors (`<a id="req-xx-nnn"></a>`)
- [ ] A new requirement ID reuses its capability area's prefix and takes the number after the highest under it (an ID is never reused); a new prefix appears only with a new capability group (`prd-authoring` skill)
- [ ] No implementation pseudocode in PRD
- [ ] No language-specific code blocks in PRD
- [ ] No language-specific constructs in PRD
- [ ] All cross-references use full paths with anchors
- [ ] Tables have headers and consistent column counts
- [ ] No relative references ("above", "below", "previous")
- [ ] No version numbers in documents
- [ ] ADR References use em-dashes
- [ ] ADR Implementation section includes **Requirements:** or **Non-goal:**
- [ ] Code blocks have language tags

### Cross-Document Coherence Checks

- [ ] Every requirement ID in system-design.md exists in prd.md
- [ ] Deprecated requirements are absent from system-design.md
- [ ] No principle-brief rule reads unconditionally where system-design.md assigns the case; the rule names its scope and the design's assignment governs
- [ ] Constants referenced in prd.md are defined in system-design.md
- [ ] Domain terms used in prd.md and system-design.md are defined in ubiquitous-language.md (or added there in the same change)
- [ ] All document links resolve to valid anchors

### Abstraction Level Checks (system-design.md)

- [ ] No struct field tables (`| Field | Type | Description |` rows). Purpose paragraph plus source pointer instead.
- [ ] No function parameter tables (`| Parameter | Type | Description |` rows). Contract prose plus source pointer instead.
- [ ] No constant literal values. Name the constant, cite the source file.
- [ ] No exhaustive rule listings (iptables, SQL, shell). State the invariant; source is authoritative for the full listing.
- [ ] Self-test: for each paragraph, would a field rename, parameter addition, or constant change in source silently invalidate it? If yes, rewrite or delete.

### Structure Within a Document Checks

Per [Structure Within a Document](documentation-standards.md#structure-within-a-document):

- [ ] Each top-level heading opens with a Level 1 paragraph (≤200 words, narrative prose, no jargon) that states purpose, conclusion, and scope.
- [ ] A non-specialist can read the first 200 words of any major section and walk away with a useful understanding.
- [ ] No section jumps from Level 1 to Level 3 with more than a 5× length ratio — insert a Level 2 bridge when the gap is larger.
- [ ] Each level is self-contained: no forward references ("as explained in Section 3 below") required to understand the current level.
- [ ] Lower-level sections may use lists, tables, and diagrams, but Level 1 paragraphs are prose.

### Writing Standards Checks

- [ ] No prohibited words without data
- [ ] No vague adjectives without measurements
- [ ] No second-person address or authorial "we" in descriptive prose — exceptions per § Voice and Register (action-directing text, a deliberate pitch, ADR decision voice)
- [ ] Sentences under 30 words; 70% under 20 words
- [ ] No wordy phrases
- [ ] Markdown prose is not hard-wrapped to a column; no word is broken across lines with a hyphen (YAML frontmatter `>-` excepted)
- [ ] Every paragraph passes the "So what?" test
- [ ] Answers start with the answer
- [ ] Acronyms defined on first use
- [ ] No subjective language or buzzwords

## Reviewing Documents

The `doc-reviewer` enforces every standard in [`documentation-standards.md`](documentation-standards.md). The stack-specific review checklist — the prohibited-pattern instantiations for this stack, project-specific coherence checks, and the review process — lives in [`review-checks.md`](review-checks.md), which extends these checks to the stack's concrete paths and constructs. The autofix eligibility rules it applies are core-shipped beside it in [`autofix-protocol.md`](autofix-protocol.md). The reviewer loads all three files.
