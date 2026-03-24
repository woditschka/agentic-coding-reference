---
name: prd-authoring
description: >-
  PRD format conventions, boundary rules, and template references.
  Load when writing or reviewing product requirements.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## PRD Location

The PRD lives at `docs/prd.md`.

## PRD Boundary Rule

The PRD describes *what* the system does. It must not contain *how*.

**Litmus test:** If it would change when switching from Go to Rust, it belongs in `docs/system-design.md`, not the PRD.

When the PRD needs to reference implementation details:
```markdown
**Implementation:** See [system-design.md#section](system-design.md#section)
```

## Prohibited Patterns in PRD

| Pattern | Severity | Fix |
|---|---|---|
| Go code blocks (` ```go `) | Critical | Move to system-design.md, link from PRD |
| Go function signatures (`func (`, `chan [`, `*Type`) | Critical | Describe behavior, not mechanism |
| Internal code references (function names, variable names) | High | Use behavioral language |
| Algorithm formulas or pseudocode | High | State behavioral constraints, move formulas to system-design.md |
| Go-specific constructs (channels, goroutines, tickers, mutexes) | High | Describe behavior, not mechanism |
| Hardcoded constant values | Medium | Reference system-design.md#constants |

## Requirement Format

Use the "Parseable Section Templates" requirement format in `docs/documentation.md`.

## Current Feature Scope

When a feature is approved, write the scope to `.scratch/current-feature.md` using the template in `.claude/templates/current-feature.md`.

## Writing Standards

Follow the Writing Standards section in `docs/documentation.md`.
