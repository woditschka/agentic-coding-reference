# Review Workflow Reference

Consulted on demand from the `review-workflow` skill — when a finding needs a `bar_clause` slug, a severity default, or an owner to route to, and when the feature-implementer processes findings. Routine dispatches (a clean `approved` record) never need this file.

## Quality-Bar Clause Mapping (`bar_clause` field)

The nine clauses below are the conjunctive "done" definition for any change. The clauses themselves are defined in [`tdd-principles.md`](../tdd-workflow/tdd-principles.md) (§ Scope Discipline, § Code That Reads Cold, § Operationally Honest, § Secure by Design), with mechanics in [`docs/testing-principles.md`](../../../docs/testing-principles.md), [`docs/architecture-principles.md`](../../../docs/architecture-principles.md), and [`docs/security-principles.md`](../../../docs/security-principles.md). This file owns the *canonical slug list* — the schema enum on `review-feedback.bar_clause` references back to this table.

When a finding violates one of these clauses, set the optional `bar_clause` field on the finding to the matching slug. The `change-grader`'s reviewer_hedging facet reads the flagged clauses as a hedge signal; reviewers and operators thereby get a shared frame for what part of the bar came under pressure.

| `bar_clause` | Set when the finding shows… | Reviewers that typically raise it | Defined in |
|---|---|---|---|
| `fit-for-purpose` | Speculative generality, abstractions without two real call sites, defensive code for impossible cases, scope creep | code-quality, test, security | `tdd-principles` § Scope Discipline |
| `spec-grounded` | Behavior outside the requirement, silently absorbed scope drift, unresolved spec ambiguity | code-quality, doc | `tdd-principles` § Scope Discipline |
| `legible-cold` | Inaccurate names, structure that obscures intent, non-obvious decisions without why-comments or ADRs | code-quality, doc | `tdd-principles` § Code That Reads Cold |
| `correct` | Spec cases not handled, listed failure modes not handled, boundary inputs not validated | test, security | `tdd-principles` § Code That Reads Cold; `testing-principles` § Edge Case and Boundary Testing |
| `tested-as-spec` | Tests of implementation detail, mocks of internal code, test names that do not read as specification, missing failure-mode coverage | test | `tdd-principles` § Code That Reads Cold; `testing-principles` § Tests Are Specifications, § Test Naming, § Mocking Policy |
| `consistent-with-codebase` | Pattern or naming mismatch with neighboring code, unjustified style deviation | code-quality | `tdd-principles` § Scope Discipline; `architecture-principles` § Naming |
| `operationally-honest` | Errors without actionable context, unreasonable resource use for workload, missing rollback note where required | security, code-quality | `tdd-principles` § Operationally Honest; `architecture-principles` § Domain Core |
| `human-maintainable` | Artifacts that only make sense to re-prompt, comments addressed to the agent, code shape that depends on the harness being present | doc, code-quality | `tdd-principles` § Operationally Honest |
| `secure-by-design` | Unvalidated input crossing a trust boundary, secrets reaching logs/errors/URLs, excess privilege, error paths that fail open | security | `tdd-principles` § Secure by Design; `security-principles` |

Procedural findings (lint, typo, missing language tag on a fence) carry `tag` but no `bar_clause` — they are mechanical and do not target a clause. A single finding may carry both `tag` and `bar_clause` when both apply: a `blocked` finding for a missing rollback note also carries `bar_clause: "operationally-honest"`.

## Artifact Ownership

Review feedback targets the artifact, not a fixed agent. Route fixes to the owning agent:

| Artifact | Owner Agent | Autofix Exception |
|---|---|---|
| `docs/prd.md` | product-requirements-expert | — |
| `docs/system-design.md`, `docs/adr/*.md` | system-design-expert | Root applies `tag: "autofix"` per `handoff-routing` § Root-Applied Autofix on Design Docs; all other tags route to system-design-expert |
| Production source (`prod_roots` in `scripts/layout.toml`) | feature-implementer | — |
| Test source | feature-implementer | — |
| Resource/config files, templates | feature-implementer | — |

Do not bundle doc fixes into a feature-implementer call. Do not send code fixes to doc agents.

## Root-Applied Autofix Eligibility

Root may apply `tag: "autofix"` findings on `docs/system-design.md` and `docs/adr/*.md` directly, without redispatching system-design-expert — the apply procedure, its bounds, and the `design-doc-autofix` audit record live in the `handoff-routing` skill § Root-Applied Autofix on Design Docs. What the reviewer owns is eligibility: the rules live in the `document-writing` skill's stack overlay, `review-checks.md` § Autofix on Design-Doc Paths. Doc-reviewer never tags a finding `autofix` on a design-doc path unless every condition there holds. The quality bar lives in the `blocked` and `clarify` (with `clarify_target: "system-design-expert"`) paths, which still route to system-design-expert.

## Issue Classification

| Checklist Category | Default Severity | Tag |
|--------------------|-----------------|-----|
| Cross-document coherence | Critical | `blocked` |
| PRD boundary violations (source code, signatures, internal references) | Critical | `blocked` |
| PRD carrying mechanism (flag/exit-code tables, output layouts) or per-requirement scaffolding (`Input`/`Output`/`Constraints`/`Depends On`) | Critical | `blocked` |
| system-design.md mirroring source — field/parameter/key enumeration in a table OR in prose | Critical | `blocked` |
| A document granting itself a reviewer-check exemption ("reviewers may skip X here") | Critical | `blocked` |
| Security vulnerabilities (CRITICAL/HIGH per `security-review` skill) | Critical | `blocked` |
| Structural issues (missing anchors, broken links) | Fixable | `autofix` |
| Writing standards | Fixable | `autofix` |

## Processing Reviews

After all reviewers complete — and after root's Reviewer Stall Check (`handoff-routing` skill § Reviewer Stall Check) confirms every roster record is present:

1. feature-implementer reads all `review-feedback` records in the roster (latest per reviewer for the active `req_id`).
2. `tag: "autofix"` findings: fix immediately using the `fix` field.
3. `tag: "blocked"` findings: fix immediately; escalate if fix is unclear.
4. `tag: "escalate"` findings: append the description to `.scratch/escalations.md`.
5. `tag: "clarify"` findings: request clarification from the agent named in `clarify_target`.
6. `tag: "truncation"` findings: nothing to fix — the finding marks unreviewed surface; step 9's re-run re-invokes the reviewer for it.
7. (No consolidated summary file needed; the roster's `review-feedback` records are the canonical record.)
8. If every roster reviewer's `verdict` is `"approved"`, feature is complete.
9. If any `verdict` is `"changes_requested"` or `"blocked"`, re-run the quality gate (append fresh `build-failure`/`build-pass` records) and re-invoke reviewers.
