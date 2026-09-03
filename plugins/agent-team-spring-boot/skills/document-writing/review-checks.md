# Document Review Checks (Java Spring Boot)

Stack-specific review checks for Java Spring Boot projects. The universal writing standards live in [`documentation-standards.md`](documentation-standards.md); this file carries the structural, coherence, abstraction-level, prohibited-pattern, and process checks the `doc-reviewer` applies on top of them.

## Review Categories

This skill is the authoritative home of the doc-form rules. The `doctor` skill owns the deterministic roster and section checks; `audit-docs` owns judgment review of brief content; this checklist owns document form, abstraction levels, and cross-document coherence.

### 1. Structural Checks

- All requirement IDs have HTML anchors (`<a id="req-xx-nnn"></a>`)
- A new requirement ID reuses its capability area's prefix and takes the number after the highest under it (an ID is never reused); a new prefix appears only with a new capability group (`prd-authoring` skill)
- No implementation pseudocode in PRD
- No Java code blocks in PRD
- No Java-specific constructs in PRD (streams, lambdas, Spring annotations)
- All cross-references use full paths with anchors
- No relative references ("above", "below", "previous")
- No version numbers in documents (git handles versioning)
- Tables have headers and consistent column counts
- ADR references use em-dashes (not hyphens); ADR Implementation section includes **Requirements:** or **Non-goal:**
- Code blocks have language tags

### 2. Cross-Document Coherence Checks

- Every requirement ID in `docs/system-design.md` exists in `docs/prd.md`
- [ ] The Contracts rows of the types the change touched carry the slice's requirement id — presence anywhere in the file is the gate's floor; row fidelity is this check.
- Deprecated requirements are absent from `docs/system-design.md`
- A principle-brief rule the slice's review invoked reads unconditionally where `docs/system-design.md` assigns the case. The design doc's assignment governs; raise `clarify` against the brief so it names its scope, never dissent against the code
- Constants referenced in `docs/prd.md` are defined in `docs/system-design.md`
- All document links resolve to valid anchors
- Configuration properties, record fields, and tech stack versions match between documents and source code
- Every imperative line in `docs/system-design.md` (lines that start with **Do**, **Don't**, **Always**, **Never**, or **Require** — case-insensitive, after any leading list marker) contains a link to a file under `docs/adr/`. Imperatives without an ADR back-link become cargo-cult guardrails; flag as `clarify` with `clarify_target: "system-design-expert"`.
- Every term used in `docs/prd.md` or `docs/system-design.md` that has a definition in `docs/ubiquitous-language.md` matches the ubiquitous-language doc's canonical spelling. Drift between the ubiquitous-language doc and projections is a `clarify` finding, not autofix.

### 3. Project-Specific Coherence

- Configuration properties in `docs/system-design.md` match `src/main/resources/application.yml`
- Package structure in `docs/system-design.md` matches actual `src/main/java/` directory layout
- Record definitions referenced in `docs/system-design.md` exist in source code
- Testing principles references in `docs/testing-principles.md` match actual test patterns

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
| Implementation pseudocode or Java code blocks in PRD | **Critical** | Move to system-design.md, link from PRD |
| Rationale prose in PRD (paragraphs explaining *why*) | **Critical** | Move to ADR; PRD carries only the `**ADR:**` link |
| "Why" explanations in system-design.md | **Critical** | Create ADR; system-design.md carries only the rule plus an ADR back-link |
| Java-specific constructs in PRD | **Critical** | Describe behavior, not mechanism |
| Internal code references in PRD | **High** | Use behavioral language |
| Algorithm formulas in PRD | **High** | State behavioral constraints; move formulas to system-design.md |
| Duplicated type definitions | **High** | Source code is the source of truth; reference source files |
| Record field / parameter tables or constant literals in system-design.md | **High** | Purpose summary plus source pointer |
| Imperative line in system-design.md without ADR back-link | **High** | Add inline ADR link; if no ADR exists, write one before landing the rule |
| Hardcoded constants in PRD | **Medium** | Reference a `Constants` section in system-design.md |
| Implementation details in ADR | **Medium** | Reference system-design.md |
| Build commands in PRD | **Medium** | Keep in CLAUDE.md |
| Hyphens in ADR reference lists | **Medium** | Use em-dashes (—) |
| Version numbers in documents | **Medium** | Git handles versioning |

## Review Process

1. Load the `review-workflow` skill for output format and feedback tags.
2. Read the `prd-authoring` skill's `boundary-rules.md` for the PRD boundary rules.
3. Load the writing standards from [`documentation-standards.md`](documentation-standards.md), and the Review Categories and Prohibited Patterns in this file.
4. Read `docs/prd.md` and `docs/system-design.md`.
5. For ADR checks, read all files in `docs/adr/` (if directory exists).
6. For coherence checks, verify config properties and type definitions match between documents and source code.
7. Execute every checklist item. Report each with file path and line number.
8. **Append a `review-feedback` record** to `.scratch/handoff.jsonl` per the Output Protocol in the `review-workflow` skill (`author: "doc-reviewer"`).
9. Reply per the one-line format in `review-workflow`. Do not include review content in your reply.

## Autofix Eligibility

The closed autofix eligibility rules for the expert-owned doc paths — § Autofix on Design-Doc Paths and § Autofix on the PRD Path — live in [`autofix-protocol.md`](autofix-protocol.md), shipped beside this file from the harness core.

## Rules

- Do not invent additional rules; follow this skill's checklist exactly. Doc-form review is deliberately closed: an improvised style opinion is indistinguishable from the standards and erodes them. A real doc defect outside the checklist is still a finding — report it against the documentation standards it violates, never as a new rule.
- Report findings with file path and line number.
- Use feedback tags from the `review-workflow` skill.
- Apply `autofix-protocol.md` § Autofix on Design-Doc Paths before tagging any finding whose location is under `docs/system-design.md` or `docs/adr/`; apply its § Autofix on the PRD Path for `docs/prd.md`.
