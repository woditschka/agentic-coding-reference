---
name: audit-docs
description: >-
  Audit the project's docs/ briefs against the high bar — each document on its
  own (principle form, enforceability) and in combination (cross-document
  coherence, contradictions, brief-vs-data agreement). Runs the doctor
  (deterministic structural gate) first, then the advisory judgment review, and
  reports both. Load when you want to check the docs hold up — at onboarding,
  after a harness upgrade, or on request. The judgment half is advisory: it
  judges form, never philosophical direction.
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
  - docs/security-principles.md
metadata:
  version: "1.0"
  author: team
---

## What this audits

A full docs audit has two passes, and this skill runs both:

1. **Structure (deterministic, blocking).** The doctor checks that each brief is present and well-formed — roster, required sections, data slots, naming, and channel invariants. Pass/fail, model-free, the same verdict in CI.
2. **Judgment (advisory).** This review judges whether a structurally-valid brief can do its job: can an agent adopt these documents as convictions and enforce them consistently — each on its own, and in combination?

The two are deliberately separate engines (deterministic vs judgment); this skill is the one entry point that sequences them so a single request audits the docs **individually and against each other**.

One boundary is load-bearing: **the judgment pass judges form, never direction.** Whether the project's stances are wise is the project's call; whether they are stated so an agent can enforce them is the harness's call. The criteria below contain no philosophy terms — verifiable by grep.

## How to run the audit

1. **Run the doctor first.** From the project root:
   ```bash
   python3 scripts/doctor.py check
   ```
   Report its verdict. A structural failure (`FAIL <check>`) is a hard finding — surface it and stop the judgment pass if the brief is too incomplete to judge (a missing roster file cannot be reviewed). Otherwise continue.
2. **Run the judgment checks below** across the roster, individually (per file) and in combination (across files).
3. **Report both passes together** — the doctor's pass/fail line, then the judgment findings tagged as in *Findings format*. The structural verdict gates; the judgment findings advise.

## Checks

Walk each roster file:

1. **Principle form.** Each principle entry states the principle, why it holds, and how to apply it. A bare rule with no rationale is an orphan-rule finding: an agent cannot extend it to a case the rule does not name.
2. **Probe questions.** For each major section ask: can an agent reason from this text to a case the text does not cover? If not, name the gap as a finding.
3. **Enforceability.** A reviewer reading an entry can decide pass or fail. Unmeasurable qualifiers without supporting data are findings.
4. **Internal consistency.** No entry contradicts another in the same file.
5. **Cross-doc consistency.** No entry contradicts another roster file. Terms match the canonical spellings in `docs/ubiquitous-language.md`.
6. **Brief-data agreement.** Where a brief states a convention that project data (`scripts/layout.toml`) also encodes operationally, the prose and the data must agree. The brief carries the principle; the data file carries the operational form.
7. **Kernel fit.** A brief specializes its discipline; it never replaces it. Express such a finding structurally — "this entry makes section X unenforceable" — never as a verdict on the stance itself.
8. **Abstraction level (prd.md, system-design.md).** The doctor caps each doc's word count and flags field-table headers; this pass catches what it cannot. In `system-design.md`, flag any paragraph that enumerates a type's fields, a config block's keys, or a function's parameters in prose. Apply the rename self-test (`document-writing` § Abstraction Level): if a source rename would silently falsify a paragraph, it sits at the wrong level. In `prd.md`, flag leaked mechanism: flag/exit-code tables, output layouts. Confirm each requirement reads as narrative prose with a tagged "Done when" bullet, not a re-stated structured contract. A doc near its budget with these patterns is the compaction signal (`doc-sync` § Compaction).

## Findings format

One finding per issue, tagged by routing action:

| Tag | Use |
|-----|-----|
| `autofix` | Style-only: writing standards, formatting. Offer the diff; apply only on consent. |
| `clarify` | A question the owning agent or the user must answer. |
| `escalate` | Structural problem needing a project decision: contradictions between briefs, an unenforceable core section. |

Style-only findings are autofix offers, never lectures. Every edit to a roster file routes through its owning agent as a consented diff — this review never writes project docs.

## Upgrade path

When the harness ships a new expectation, it arrives here as review feedback: the finding names the new expectation, includes the shipped default text, and offers to draft the project's own stance instead. The project chooses; the review records nothing on its behalf.
