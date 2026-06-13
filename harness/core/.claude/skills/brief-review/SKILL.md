---
name: brief-review
description: >-
  Advisory judgment review of the project's docs/ brief: principle form,
  enforceability, contradictions, and agreement between briefs and project
  data. Load after the doctor passes — at onboarding, after a harness upgrade,
  or on request. Never blocking; judges form, never philosophical direction.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/prd.md
  - docs/system-design.md
  - docs/adr/
  - docs/ubiquitous-language.md
  - docs/testing-principles.md
  - docs/architecture-principles.md
metadata:
  version: "1.0"
  author: team
---

## What this reviews, and what it does not

The doctor checks that the brief is structurally present; this review judges
whether the brief can do its job: can an agent adopt these documents as
convictions and enforce them consistently? It is advisory — findings, never
gates.

One boundary is load-bearing: **the review judges form, never direction.**
Whether the project's stances are wise is the project's call; whether they are
stated so an agent can enforce them is the harness's call. The criteria below
contain no philosophy terms — verifiable by grep.

## Checks

Walk each roster file:

1. **Principle form.** Each principle entry states the principle, why it
   holds, and how to apply it. A bare rule with no rationale is an orphan-rule
   finding: an agent cannot extend it to a case the rule does not name.
2. **Probe questions.** For each major section ask: can an agent reason from
   this text to a case the text does not cover? If not, name the gap as a
   finding.
3. **Enforceability.** A reviewer reading an entry can decide pass or fail.
   Unmeasurable qualifiers without supporting data are findings.
4. **Internal consistency.** No entry contradicts another in the same file.
5. **Cross-doc consistency.** No entry contradicts another roster file. Terms
   match the canonical spellings in `docs/ubiquitous-language.md`.
6. **Brief-data agreement.** Where a brief states a convention that project
   data (`scripts/layout.toml`) also encodes operationally, the prose and the
   data must agree. The brief carries the principle; the data file carries the
   operational form.
7. **Kernel fit.** A brief specializes its discipline; it never replaces it.
   Express such a finding structurally — "this entry makes section X
   unenforceable" — never as a verdict on the stance itself.

## Findings format

One finding per issue, tagged by routing action:

| Tag | Use |
|-----|-----|
| `autofix` | Style-only: writing standards, formatting. Offer the diff; apply only on consent. |
| `clarify` | A question the owning agent or the user must answer. |
| `escalate` | Structural problem needing a project decision: contradictions between briefs, an unenforceable core section. |

Style-only findings are autofix offers, never lectures. Every edit to a roster
file routes through its owning agent as a consented diff — this review never
writes project docs.

## Upgrade path

When the harness ships a new expectation, it arrives here as review feedback:
the finding names the new expectation, includes the shipped default text, and
offers to draft the project's own stance instead. The project chooses; the
review records nothing on its behalf.
