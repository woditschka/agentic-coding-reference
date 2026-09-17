# Workload Fit Lives Inside the Existing Bar, Not as a New Reviewer, Slug, or Brief

**Status:** Accepted

## Context

The conjunctive bar asked one sentence of resource use: reasonable for the workload. It gave no method for choosing a data structure or algorithm, no basis for a reviewer to judge the choice, and no place for the workload facts. An implementer picked structures by habit and a reviewer judged them by taste. The quadratic loop over a growing collection, the list scanned for membership, the hand-written sort, and the map shared across threads all passed the bar as written.

Four constraints bounded the fix. Reviewers judge against the project briefs and never mine the design triage (`review-workflow` § Reviewer Read-Set), so the facts had to live in a brief. The implementer cannot write the design record, so a rule that asks the implementer to "name" facts needs a home the implementer reads rather than writes. The bar's counterweights, `fit-for-purpose` and the Green phase's minimum-code rule, forbid speculative optimization, so the rule had to state which way the burden of proof points. And cost per pass is measured per version, so the addition had to add no pass, no reviewer, and no record type.

## Options Considered

1. **A performance reviewer.** Rejected: a fifth floor reviewer costs a dispatch on every pass, and selection is a property of the implementer's choice the code-quality reviewer already reads.
2. **A tenth bar clause, `fit-for-workload`.** Rejected: a slug fans out into the schema enum, the clause mapping, the self-review pass, and the grader's hedge facet. The rule is one facet of `operationally-honest`.
3. **An eighth brief, `performance-principles.md`.** Rejected: the seven-file roster fans out into the doctor, `derive-briefs`, `init`, and every reviewer's read list; the facts fit one section of the system-design brief.
4. **A `scale` field on the design-block.** Rejected: reviewers do not read the design-block, so implementer and reviewer would judge against different bases.
5. **A silent brief routes `clarify` on every scaling path.** Rejected after review: a `clarify` on an approved verdict routes nowhere, and a fresh consumer's brief is silent on every path. The first effect would be added rounds rather than better selection.
6. **The design owner writes the row at triage, marking an unknown figure as bounded** (chosen).

## Decision

**Workload fit is a facet of `operationally-honest`, chosen and judged against one row of the system-design brief's § Scale and Load. It follows the security split: the law is harness-owned, the facts are project-owned.**

- **Closed, in `tdd-principles` § Fit for the Workload.** Three facts per path that scales with data decide the structure: dominant operations, realistic size, access pattern. The implementer works from the row the design record cites; a path the design did not foresee is a design gap through the existing consultation. Buy before build: standard library, then the project's approved sources, then an ADR. The burden of proof points one way: the simplest correct form needs no reason, the more complex form needs a row. The free tier is a test, clarity, never a shape list. A performance claim lives in the row or an ADR and names its measurement or says it is reasoned. A hot-path row states its form's time and space bound with its kind; every other row names the form alone. Inefficiency outside the slice is a recommendation, never a fix.
- **Open, in the brief.** `docs/system-design.md` § Scale and Load carries one row per scaling path: size, growth, access pattern, chosen form. The design owner writes the row at triage. A figure nobody knows is written as "unrecorded, treated as bounded", so the simplest correct form is the recorded design until the owner corrects the row. The dependency policy's necessity step carries the buy-or-build default for a single function. It is justified when the function is more than a few lines of tested code and the library is established. The section is not doctor-required.
- **Judged, in each stack's `code-quality-review` § Workload Fit.** A mismatch with a row is `blocked`, severity `fixable`, `critical` only on a hot path or a limit. A path no row covers is `clarify` on `changes_requested` with no `bar_clause`. An unbounded load stays the security reviewer's item, filed once. A hand-written structure is a recorded exception, an ADR linked from the row, and its case-table tests are the test-reviewer's.
- **Routed, in the fix-round planner.** `operationally-honest` implicates the code-quality reviewer, where the clause's weight now sits; the security reviewer files resource exhaustion under `secure-by-design`. Before this change the clause implicated the security reviewer, so every workload finding forced the cold full re-read.

## Consequences

**Positive:** the addition is static prose in files every side already loads, plus one entry in the planner's clause map. No new pass, reviewer, record type, or slug. Implementer and reviewer read the same row, so a disagreement is about a recorded fact, never taste. The counterweights hold by construction. A finding that asks for the more complex form without a row is itself out of bar. A bounded row ends the question in one line, and the free tier's test is clarity. Each judgment instruction carries its reason, so the shape lists generalize by their test rather than their membership.

**Negative:** an existing consumer's brief lacks the section until its owner adds it, and the doctor does not prompt for it. Until then the design owner writes each row from what the triage can see. The planner remap changes a fix-round roster wherever the clause is filed by a reviewer other than code-quality, and lifts the cold read from a code-quality critical off production paths. Neither oracle covers it: the ledger replay routes recorded plans without recomputing them, and the grading fuzz emits no `bar_clause`. One recorded ledger, v0.3.5 vets-specialty-filter r1, would plan a different roster; the unit suite pins the mapping. The stack shape lists will drift as idioms move; `harvest` and `review-harness` refresh them. A benchmark harness is not a project dependency by default, so a Spring Boot claim is more often reasoned than measured.

## References

- [2026-06-03-principles-over-rigid-rules](2026-06-03-principles-over-rigid-rules.md): the taxonomy the new text follows.
- [2026-09-01-evidence-gated-dynamic-tiering](2026-09-01-evidence-gated-dynamic-tiering.md): the cost-per-pass discipline the addition must not move.
