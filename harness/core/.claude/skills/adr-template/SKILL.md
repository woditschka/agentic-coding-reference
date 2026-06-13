---
name: adr-template
description: >-
  Architecture Decision Record format, naming conventions, and
  when to create ADRs. Load when making or documenting architectural decisions.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/adr/
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

See `docs/adr/README.md` for the ADR template, naming convention (`YYYY-MM-DD-title-in-kebab-case.md`), guidelines, and index table. The filename pattern and the README's presence are harness-project API requirements; the `doctor` skill enforces them deterministically. The decision log itself is project-owned: harness upgrades never write here.

## Non-Goal ADRs

A non-goal ADR captures a *product* decision not to build something — distinct from an architectural ADR that records a *how* decision. Two conventions apply:

1. **Filename:** `YYYY-MM-DD-non-goal-<slug>.md` (the `non-goal-` infix is load-bearing — it scopes write access).
2. **Implementation section:** use `**Non-goal:** NG-X` instead of `**Requirements:** REQ-XX-NNN`.

**Ownership.** Non-goal ADRs may be authored by `product-requirements-expert` (the agent's write scope explicitly includes `docs/adr/*-non-goal-*.md`). All other ADRs are owned by `system-design-expert`.
