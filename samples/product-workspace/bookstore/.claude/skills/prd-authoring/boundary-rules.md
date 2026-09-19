# PRD Boundary Rule and Prohibited Patterns

The PRD's content boundary — what belongs, what never does — shipped beside the authoring skill. The product-requirements-expert applies it when writing; the doc-reviewer enforces it when reviewing; both read this file, so author and reviewer hold one rulebook.

## PRD Boundary Rule

The PRD describes *what* the system does. It must not contain *how*. It must not contain *why* — rationale lives in ADRs, referenced via the `**ADR:**` link.

**Litmus test (what/how):** If it would change when switching to another language, it belongs in `docs/system-design.md`, not the PRD.

**Litmus test (state/history):** If it explains *why* a decision was made (alternatives considered, trade-offs evaluated), it belongs in an ADR, not the PRD.

**Discuss the *how*; record only the *what*.** The boundary governs what you *write*, not what you discuss. Explore freely how the system might work — that is how the human discovers what they mean. The record carries only requirements and non-goals, never a *how*. Do not park implementation ideas in the handoff. Mechanism is the design stage's responsibility; the human, present there too, can raise an idea worth keeping. Recording a *how*, even as a note, pre-empts that stage and leaks mechanism into the requirement.

When the PRD needs to reference implementation details:
```markdown
**Design:** See [system-design.md#section](system-design.md#section)
```

When the PRD needs to reference the rationale for a decision:
```markdown
**ADR:** See [ADR: Title](adr/YYYY-MM-DD-title.md)
```

## Prohibited Patterns in PRD

| Pattern | Severity | Fix |
|---|---|---|
| Implementation code blocks in the PRD | Critical | Move to system-design.md, link from PRD |
| Framework- or language-specific constructs | Critical | Describe behavior, not mechanism |
| Rationale prose (paragraphs explaining *why* a requirement or non-goal exists) | Critical | Move reasoning to an ADR; reference via the `**ADR:**` link (link only, no inline reasoning) |
| A blanket exemption that tells reviewers to skip a check (e.g. "doc-reviewers may skip the rationale-prose check here") | Critical | A document cannot grant itself an exemption. Fix the content or raise a per-instance escalation; never disable a reviewer check wholesale |
| Mechanism tables — CLI flag tables, exit-code tables, output-directory layouts, on-disk/file-format schemas | High | Move to system-design.md; state the behavior in prose and link with `**Design:**` |
| Per-requirement contract scaffolding (`Input` / `Output` / `Constraints` / `Depends On` blocks) | High | Field tables in disguise — state the outcome in a "Done when" bullet; the signature lives in source, the constant in system-design.md |
| Internal code references (type, method, variable names) | High | Use behavioral language |
| Algorithm formulas or pseudocode | High | State behavioral constraints, move formulas to system-design.md |
| Low-level implementation constructs (concurrency primitives, regex, framework APIs) | High | Describe behavior, not mechanism |
| Hardcoded constant values | Medium | Reference a `Constants` section in `system-design.md` (create the section on first constant) |
