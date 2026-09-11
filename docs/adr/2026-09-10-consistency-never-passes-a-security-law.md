# Consistency Never Passes a Security Law

**Status:** Accepted

## Context

In the v0.3.10 eval sweep the security reviewer approved the same mass-assignment defect in five of six visit-edit reps. The approvals show the reviewer saw it. One records that a crafted POST can bind non-identifier owner and nested pet fields and persist them, then closes with "this is the same pattern" as the existing new-visit handler. The checklist's Pattern Consistency section said a concern the codebase already secures is secured the same way here, and that divergence is a finding. It never said the converse. On a brownfield codebase that rule inherits every weakness the codebase already carries. The producer's `consistent-with-codebase` clause and the scaffolded architecture brief's "consistency over novelty" said the same thing to the implementer.

The security reviewer is the last of three stages that read the same laws. The implementer walks the `secure-by-design` and `consistent-with-codebase` clauses before its build-pass; the design expert names the boundaries a slice crosses at triage; the reviewer holds the diff to the checklist. A law wired into only the last stage costs a fix round every time it fires.

## Options Considered

1. **Add the defect to the reviewer checklist only.** Rejected: it catches one named class at the most expensive stage and leaves the doctrine that let it through.
2. **Drop the consistency rules.** Rejected: one way per concern is what makes divergence visible; the rule is right for secured concerns.
3. **State the carve-out at every stage and add the binding law as a harness-owned law** (chosen).

## Decision

**Consistency judges how a secured concern is secured, never whether an unsecured one passes.** A change that extends a pre-existing weakness to a new path is a finding; its description names the existing scope, and the new reach sets its severity. The carve-out lives in the `consistent-with-codebase` clause and its self-review question. It also lives in the scaffolded architecture brief's consistency principle and in every stack's Pattern Consistency section.

**A request binds into a request-scoped object or through an allow-list, never a persisted type whole.** The law joins the `secure-by-design` clause and its self-review question. It joins the design-block's `integration_points` contract, one entry per new entry point naming the binding target. It joins every stack's input-validation checklist.

## Consequences

**Positive:** the law reaches the implementer before a line is written and the design expert before the implementer; the reviewer's finding becomes the exception. The named-defect probe in the eval bench measures the effect across the whole series without a bar change.

**Negative:** a consumer's scaffolded architecture brief is project-owned and keeps its old sentence until the project edits it; the harness-owned clause governs regardless. "Persisted type" is the one noun across core and stacks; a stack specializes the binder, never the concept.

## Implementation

`tdd-workflow/tdd-principles.md` (both clause rows), `tdd-workflow/SKILL.md` (both self-review questions), the doctor's `architecture-principles.md` template, `design-validation` (Binding per entry point), and `security-checks` (Input Validation including the Java `@Valid` line, Pattern Consistency, the Java detection row) in every stack.

## References

- [2026-09-07 security-review-follows-the-surface](2026-09-07-security-review-follows-the-surface.md): the dispatch rule this decision complements; dispatch decides who reads, this decision what a reader may not excuse.
- [2026-07-12 resilience-first-improvement-doctrine](2026-07-12-resilience-first-improvement-doctrine.md): quality is never traded for cost; the fix round a caught defect costs is the bar working.
