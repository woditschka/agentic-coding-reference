---
name: adr-template
description: >-
  Architecture Decision Record format, naming conventions, and
  when to create ADRs. Load when making or documenting architectural decisions.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## When to Create an ADR

Create an ADR when:

- Choosing between alternatives (library, pattern, approach).
- Introducing a new architectural pattern.
- Rejecting a reasonable alternative (document why not).
- Changing a previous decision (supersede the old ADR).

Do not create an ADR for straightforward implementation choices with no trade-offs.

## Template, Guidelines, and Index

See `docs/adr/README.md` for the ADR template, naming convention (`YYYY-MM-DD-title-in-kebab-case.md`), guidelines, and index table.

For non-goal ADRs, use `**Non-goal:** NG-X` instead of Requirements in the Implementation section.
