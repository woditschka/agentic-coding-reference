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

Create an ADR when a decision constrains future slices or reverses a recorded one:

- A pattern, library, or approach chosen over a reasonable alternative that later work must not silently re-open.
- A rejected alternative a later reader would otherwise re-litigate.
- A reversal or narrowing of a recorded decision (supersede or amend the old ADR).

Do not create an ADR for a choice with no trade-off, or for one a single slice contains. That rationale is one clause on the current-state line in `docs/system-design.md`. ADRs are the project's decision log for people; agents execute from the current-state docs and read an ADR by back-link.

## What an ADR Owns

An ADR owns:

- Context for each architectural decision
- Options considered with trade-offs
- Decision outcome and rationale
- Consequences (positive and negative)
- Implementation mapping (which requirements, which files)

It does not own:

- Detailed implementation (lives in `docs/system-design.md`)
- Requirement specifications (live in `docs/prd.md`)

## Template, Guidelines, and Index

See `docs/adr/README.md` for the ADR template, naming convention (`YYYY-MM-DD-title-in-kebab-case.md`), guidelines, and index table. The filename pattern and the README's presence are harness-project API requirements; the `doctor` skill enforces them deterministically. The decision log itself is project-owned: harness upgrades never write here.

ADR prose follows the writing standards in the [`document-writing`](../document-writing/documentation-standards.md) skill — the same discipline as every other project document.

## Non-Goal ADRs

A non-goal ADR captures a *product* decision not to build something — distinct from an architectural ADR that records a *how* decision. Two conventions apply:

1. **Filename:** `YYYY-MM-DD-non-goal-<slug>.md` (the `non-goal-` infix is load-bearing — it scopes write access).
2. **Implementation section:** use `**Non-goal:** NG-X` instead of `**Requirements:** REQ-XX-NNN`.

**Ownership.** Non-goal ADRs may be authored by `product-requirements-expert` (the agent's write scope explicitly includes `docs/adr/*-non-goal-*.md`). All other ADRs are owned by `system-design-expert`.
