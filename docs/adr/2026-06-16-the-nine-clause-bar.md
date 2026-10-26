# The Nine-Clause Bar Carries Security and Workload Fit as Producer Law

**Status:** Accepted

## Context

The feature-implementer authors against principle briefs and walks the conjunctive bar in a mandatory self-review before any reviewer runs. Architecture, testing, and legibility each had a producer-facing principle layer the self-review reached. Security did not: its principles lived only in the `security-review` checklist, which the producer never loads. The security reviewer was the first agent to reason about abuse, in the one dimension where findings were avoidable upstream.

Two gaps surfaced after the clause shipped. In the v0.3.10 eval sweep the security reviewer approved one mass-assignment defect in five of six visit-edit reps. Each approval closed with "this is the same pattern" as an existing handler. The checklist's consistency rule said a secured concern is secured the same way; it never said an unsecured one does not pass by matching. On a brownfield codebase that rule inherits every weakness the codebase carries. Separately, the bar asked one sentence of resource use, "reasonable for the workload". It gave no method for choosing a structure, no basis for judging it, and no home for the workload facts. The quadratic loop, the list scanned for membership, and the map shared across threads all passed as written.

Four constraints bound every addition. Reviewers judge against the project briefs and never mine the design triage. The implementer reads but never writes the design record. `fit-for-purpose` and the Green phase's minimum-code rule forbid speculative optimization. Cost per pass is measured per version, so an addition adds no pass, no reviewer, and no record type.

## Options Considered

1. **Security principles stay inside the reviewer skill.** Rejected: leaves security the one dimension the producer designs blind.
2. **Load the full `security-review` checklist into the implementer.** Rejected: the producer writes to the reviewer's rubric, eroding reviewer independence and bloating generation-time context.
3. **A producer brief plus a conjunctive-bar clause.** Chosen: principles reach the producer; the reviewer keeps the exhaustive checklist.
4. **Add the mass-assignment defect to the reviewer checklist only.** Rejected: catches one class at the most expensive stage and leaves the doctrine that let it through.
5. **Drop the consistency rules.** Rejected: one way per concern is what makes divergence visible.
6. **State the consistency carve-out at every stage and add the binding law as a harness-owned law.** Chosen.
7. **A performance reviewer.** Rejected: a fifth floor reviewer costs a dispatch per pass; structure selection is a property the code-quality reviewer already reads.
8. **A tenth bar clause, `fit-for-workload`.** Rejected: a slug fans out into the schema enum, the clause mapping, the self-review pass, and the grader's hedge facet.
9. **An eighth brief, `performance-principles.md`.** Rejected: the roster fans out into the doctor, `derive-briefs`, `init`, and every reviewer's read list.
10. **A `scale` field on the design-block.** Rejected: reviewers do not read the design-block, so implementer and reviewer would judge against different bases.
11. **A silent brief routes `clarify` on every scaling path.** Rejected: `clarify` on an approved verdict routes nowhere; a fresh consumer's brief is silent on every path.
12. **The design owner writes the workload row at triage, marking an unknown figure as bounded.** Chosen.

## Decision

**The conjunctive bar has nine clauses; `secure-by-design` is the ninth, and workload fit is a facet of `operationally-honest`. In both, the law is harness-owned and the facts are project-owned.**

- **Harness-owned laws.** `tdd-principles.md` § Secure by Design holds four laws: security as an emergent property, defense in depth, least privilege, fail secure. A fifth sits beside them. A request binds into a request-scoped object or through an allow-list, never a persisted type whole. "Persisted type" is the one noun across core and stacks. A stack specializes the binder, never the concept. The laws re-materialize on every upgrade and are denylisted from project rosters: a project decides how it meets them, never whether.
- **Project-owned facts.** `docs/security-principles.md` is a brief of `kind = "default"`, peer to the testing and architecture briefs. It carries the trust-boundary map and the stack's high-bar defaults, derived from the project's dependency policy and threat model. `docs/system-design.md` § Scale and Load carries one row per scaling path: size, growth, access pattern, chosen form. The design owner writes the row at triage; an unknown figure reads "unrecorded, treated as bounded", so the simplest correct form is the recorded design until corrected. The dependency policy's necessity step carries the buy-or-build default for a single function: justified when the function exceeds a few lines of tested code and the library is established. The security brief is on the doctor roster with `Trust Boundaries` as its required section; § Scale and Load is not doctor-required.
- **Consistency judges how a secured concern is secured, never whether an unsecured one passes.** A change that extends a pre-existing weakness to a new path is a finding. The description names the existing scope, and the new reach sets the severity. The carve-out lives in the `consistent-with-codebase` clause and its self-review question. It also lives in the scaffolded architecture brief's consistency principle and every stack's Pattern Consistency section.
- **Fit for the workload**, closed in `tdd-principles` § Fit for the Workload. Three facts per path that scales with data decide the structure: dominant operations, realistic size, access pattern. The implementer works from the row the design record cites; an unforeseen path is a design gap routed through consultation. Buy before build: standard library, then the project's approved sources, then an ADR. The simplest correct form needs no reason; the more complex form needs a row. The free tier is a test, clarity, never a shape list. A performance claim lives in the row or an ADR and names its measurement or says it is reasoned. A hot-path row states its form's time and space bound; every other row names the form alone. Inefficiency outside the slice is a recommendation, never a fix.
- **Design stage.** `design-validation` reads the security brief and validates trust-boundary placement against it. The design-block's `integration_points` carries one entry per new entry point naming its binding target.
- **Review stage.** `security-checks` references the brief and keeps the exhaustive checklist, severity table, and supply-chain steps; every stack's input-validation checklist carries the binding law. `code-quality-review` § Workload Fit judges structure choice. A mismatch with a row is `blocked`, severity `fixable`, `critical` only on a hot path or a limit. A path no row covers is `clarify` on `changes_requested` with no `bar_clause`. An unbounded load stays the security reviewer's item, filed once under `secure-by-design`. A hand-written structure is a recorded exception, an ADR linked from its row, with case-table tests for the test reviewer.
- **Routing.** The fix-round planner maps `operationally-honest` to the code-quality reviewer and `secure-by-design` to the security reviewer, so a workload finding no longer forces the security reviewer's cold full re-read.

## Consequences

**Positive:**
- Security is shaped into the first draft and self-reviewed before the gate. The binding law reaches the implementer before a line is written and the design expert before the implementer. The reviewer's finding becomes the exception; the eval bench's named-defect probe measures the effect across the series.
- Producer and reviewer reference one brief; the checklist no longer duplicates the principles, and the validator keeps a list the producer never optimized to.
- A consumer specializes controls but cannot weaken a law, because the laws live in re-materialized runtime, not an editable brief.
- Workload fit adds static prose in files every side already loads plus one planner map entry: no pass, reviewer, record type, or slug. Implementer and reviewer read the same row, so a disagreement is about a recorded fact. A finding that asks for the more complex form without a row is itself out of bar.

**Negative:**
- Every slice walks the ninth clause, including slices with no security surface, where it holds trivially; the one-line self-review question bounds the cost.
- A consumer's architecture and system-design briefs are project-owned. The consistency sentence and the Scale and Load section arrive only when the owner edits them, and the doctor does not prompt. The harness-owned clauses govern regardless.
- The planner remap changes the fix-round roster wherever `operationally-honest` is filed by a reviewer other than code-quality. Neither oracle covers it: the ledger replay routes recorded plans without recomputing them, and the grading fuzz emits no `bar_clause`. One recorded ledger, v0.3.5 vets-specialty-filter r1, would plan a different roster; the unit suite pins the mapping.
- The stack shape lists drift as idioms move; `harvest` and `review-harness` refresh them. A benchmark harness is not a project dependency by default, so a Spring Boot claim is more often reasoned than measured.

## Implementation

`tdd-workflow/tdd-principles.md` (§ Secure by Design, § Fit for the Workload, the clause rows) and `tdd-workflow/SKILL.md` (the self-review questions). The doctor's `security-principles.md`, `architecture-principles.md`, and `system-design.md` templates. `design-validation`, `security-checks`, and `code-quality-review` in every stack. The `bar_clause` schema enum, `review-workflow/reference.md` § Quality-Bar Clause Mapping, and the fix-round planner's clause map.

## References

- [Principles Over Rigid Rules](2026-06-03-principles-over-rigid-rules.md) — the producer-principles / validator-checklist split every clause here follows
- [Model Tiering](2026-06-11-model-tiering.md) — the floor/ceiling reasoning that keeps the reviewer an independent reasoner, and the cost-per-pass discipline the workload addition had to hold
- [Docs as the Harness–Project API](2026-06-12-docs-as-harness-project-api.md) — the project-owned roster the security brief joins and the system-design brief belongs to
- [The Reviewer Roster](2026-06-18-the-reviewer-roster.md) — the dispatch rule that decides who reads a slice; this decision states what a reader may not excuse
- [Resilience-First Improvement Doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — quality is never traded for cost; the fix round a caught defect costs is the bar working
- [The Eval Bench](2026-07-15-the-eval-bench.md) — the named-defect probe that measures the binding law's effect
