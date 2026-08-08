# Document Review Checks (Generic Stack)

Stack-specific review checks. This is the generic stack: replace each `{{FILL: …}}` slot with the project's real language and layout facts. The universal writing standards live in [`documentation-standards.md`](documentation-standards.md); this file carries the structural, coherence, abstraction-level, prohibited-pattern, and process checks the `doc-reviewer` applies on top of them.

## Review Categories

This skill is the authoritative home of the doc-form rules. The `doctor` skill owns the deterministic roster and section checks; `audit-docs` owns judgment review of brief content; this checklist owns document form, abstraction levels, and cross-document coherence.

### 1. Structural Checks

- All requirement IDs have HTML anchors (`<a id="req-xx-nnn"></a>`)
- No implementation pseudocode in PRD
- No source-code blocks in PRD
- No language-specific constructs in PRD ({{FILL: this language's constructs — e.g. function signatures, concurrency primitives, framework annotations}})
- All cross-references use full paths with anchors
- No relative references ("above", "below", "previous")
- No version numbers in documents (git handles versioning)
- Tables have headers and consistent column counts
- ADR references use em-dashes (not hyphens); ADR Implementation section includes **Requirements:** or **Non-goal:**
- Code blocks have language tags

### 2. Cross-Document Coherence Checks

- Every requirement ID in `docs/system-design.md` exists in `docs/prd.md`
- Deprecated requirements are absent from `docs/system-design.md`
- Constants referenced in `docs/prd.md` are defined in `docs/system-design.md`
- All document links resolve to valid anchors
- Names, types, and constants match between documents and source code ({{FILL: the stack's coherence vocabulary — e.g. metric names, configuration properties, record fields}})
- Every imperative line in `docs/system-design.md` (lines that start with **Do**, **Don't**, **Always**, **Never**, or **Require** — case-insensitive, after any leading list marker) contains a link to a file under `docs/adr/`. Imperatives without an ADR back-link become cargo-cult guardrails; flag as `clarify` with `clarify_target: "system-design-expert"`.
- Every term used in `docs/prd.md` or `docs/system-design.md` that has a definition in `docs/ubiquitous-language.md` matches the ubiquitous-language doc's canonical spelling. Drift between the ubiquitous-language doc and projections is a `clarify` finding, not autofix.

### 3. Project-Specific Coherence

- The project's config example reflects all config fields from the config module and `docs/prd.md`, where those files exist ({{FILL: config example path and config module path}})
- Module structure in `docs/system-design.md` matches the actual source layout ({{FILL: the production roots declared in `scripts/layout.toml`}})
- Dependency policy in `docs/system-design.md` matches the build's dependency rules ({{FILL: the `scripts/stack.sh` verb or build target that enforces them}})

### 4. Writing Standards Checks

Per the Writing Standards in [`documentation-standards.md`](documentation-standards.md):
- No prohibited words without data
- No vague adjectives without measurements
- Sentences under 30 words; 70% under 20 words
- No wordy phrases ("due to the fact that" → "because")
- Every paragraph passes the "So what?" test; every section over 100 lines passes the section-scope review
- Answers start with the answer, not warmup
- Acronyms defined on first use
- No subjective language or buzzwords

### 5. Abstraction-Level Checks (system-design.md)

Verify the document follows the Abstraction Level guidance in [`documentation-standards.md`](documentation-standards.md): no field or parameter tables, no constant literals, no exhaustive rule listings; every paragraph survives the source-rename self-test.

### 6. Document Structure Checks

Verify the document follows the Document Structure guidance in [`documentation-standards.md`](documentation-standards.md): 2–4 abstraction levels highest-first, each top-level heading opens with a ≤200-word Level 1 prose paragraph, no level jump over 5×, self-contained levels.

## Prohibited Patterns

| Pattern | Severity | Solution |
|---------|----------|----------|
| Implementation pseudocode or source-code blocks in PRD | **Critical** | Move to system-design.md, link from PRD |
| Rationale prose in PRD (paragraphs explaining *why*) | **Critical** | Move to ADR; PRD carries only the `**ADR:**` link |
| "Why" explanations in system-design.md | **Critical** | Create ADR; system-design.md carries only the rule plus an ADR back-link |
| Language-specific constructs in PRD | **Critical** | Describe behavior, not mechanism |
| Internal code references in PRD | **High** | Use behavioral language |
| Algorithm formulas in PRD | **High** | State behavioral constraints; move formulas to system-design.md |
| Duplicated type definitions | **High** | Source code is the source of truth; reference source files |
| Type field / parameter tables or constant literals in system-design.md | **High** | Purpose summary plus source pointer |
| Imperative line in system-design.md without ADR back-link | **High** | Add inline ADR link; if no ADR exists, write one before landing the rule |
| Hardcoded constants in PRD | **Medium** | Reference a `Constants` section in system-design.md |
| Implementation details in ADR | **Medium** | Reference system-design.md |
| Build commands in PRD | **Medium** | Keep in CLAUDE.md |
| Hyphens in ADR reference lists | **Medium** | Use em-dashes (—) |
| Version numbers in documents | **Medium** | Git handles versioning |

## Review Process

1. Load the `review-workflow` skill for output format and feedback tags.
2. Load the `prd-authoring` skill for PRD boundary rules.
3. Load the writing standards from [`documentation-standards.md`](documentation-standards.md), and the Review Categories and Prohibited Patterns in this file.
4. Read `docs/prd.md` and `docs/system-design.md`.
5. For coherence checks that reference code ({{FILL: e.g. metric names, configuration properties}}), read relevant source files.
6. For ADR checks, read all files in `docs/adr/`.
7. Verify the project's config example reflects all config fields from the config module and `docs/prd.md`, where those files exist.
8. Execute every checklist item. Report each with file path and line number.
9. **Append a `review-feedback` record** to `.scratch/handoff.jsonl` per the Output Protocol in the `review-workflow` skill (`author: "doc-reviewer"`).
10. Reply per the one-line format in `review-workflow`. Do not include review content in your reply.

## Autofix on Design-Doc Paths

Design-doc paths are `docs/system-design.md` and any file under `docs/adr/`. Only the system-design-expert may make substantive edits to these files. The autofix protocol exists so root can apply mechanical fixes without redispatching system-design-expert for every typo.

A finding may carry `tag: "autofix"` on a design-doc path only when **every** condition below holds:

1. The finding's check category is one of: **writing-standards** (sentence length, prohibited words without data, vague adjectives, missing periods on bullet points) or **structural** (missing `<a id="...">` anchor for an existing REQ-ID, missing language tag on a code fence, em-dash vs hyphen in ADR refs, table column-count fix, broken intra-file link).
2. The `fix` field is present and is a literal replacement string — not a description of what to change, not a sketch, not a TODO. Root applies it verbatim via Edit.
3. The proposed change is bounded: ≤5 lines and ≤200 characters of file content.
4. The proposed change does NOT modify any `## ` heading line, any `<a id="..."></a>` anchor value, any REQ-ID reference, any provenance mark (`derive-briefs` forms), any content inside a fenced code block, or any markdown link target (link text is fixable).

Findings that fail any of these conditions on a design-doc path must use `tag: "blocked"` or `tag: "clarify"` with `clarify_target: "system-design-expert"`. Coherence, PRD-boundary, and project-specific coherence findings on design-doc paths are **never** autofix-eligible — regardless of how mechanical the fix appears, they exercise architectural judgement and route to system-design-expert.

The conditions are also re-checked mechanically at gate time by `python3 scripts/handoff.py audit-autofix` (the `code-quality-gate` skill's autofix audit) — if doc-reviewer mis-tags a finding, the gate fails closed.

## Autofix on the PRD Path

The PRD path is `docs/prd.md`. Only the product-requirements-expert may make substantive edits to this file. The same protocol applies: root fixes mechanically, recording a `prd-autofix` record. The record keeps a doc-only PRD fix in the current review round — the alternative, a fresh `prd-entry`, re-enters the pipeline at design triage.

A finding may carry `tag: "autofix"` on `docs/prd.md` only when every condition in § Autofix on Design-Doc Paths holds for the PRD path. In addition, these are **never** autofix-eligible on the PRD, regardless of how mechanical the fix appears:

1. Any change to a "Done when" bullet's meaning — its conditions, outcomes, or given/when/then content.
2. Any change to requirement scope, a non-goal, an edge-case item, or lifecycle status (the narrative's active set, the `## Superseded` list). For a Non-Goals table row this is also enforced mechanically: `audit-autofix` rejects a `prd-autofix` touching a `| NG-n |` line, and Gate 1's scope-lock reads such an edit as an uncovered row change.
3. Any PRD-boundary content — mechanism moving in or out of the PRD is a boundary finding, not a style fix.

Findings that fail any condition on the PRD path must use `tag: "blocked"` or `tag: "clarify"` with `clarify_target: "product-requirements-expert"`. The gate re-checks the mechanical bounds via the same `audit-autofix` command; the product-requirements-expert judges every applied record on its next dispatch (`prd-authoring` skill § Autofix Audit).

## Rules

- Do not invent additional rules; follow this skill's checklist exactly. Doc-form review is deliberately closed: an improvised style opinion is indistinguishable from the standards and erodes them. A real doc defect outside the checklist is still a finding — report it against the documentation standards it violates, never as a new rule.
- Report findings with file path and line number.
- Use feedback tags from the `review-workflow` skill.
- Apply the Autofix on Design-Doc Paths section before tagging any finding whose location is under `docs/system-design.md` or `docs/adr/`; apply the Autofix on the PRD Path section for `docs/prd.md`.
