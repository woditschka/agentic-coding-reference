# Design Truth Holds Mid-Slice Without a Pipeline Re-Flow

**Status:** Accepted

## Context

The briefs change while a slice is in flight. The changes are a reviewer's writing-standards finding on `docs/prd.md`, a fix round that edits the PRD or `docs/system-design.md`, and a consultation whose answer adds a Done-when bullet. Five measured costs followed from rules written when design records only opened a slice.

A design-doc autofix resolved in its round, but a PRD finding of the same shape could only route to the product-requirements-expert. Its `prd-entry` re-entered the pipeline at Gate 1: one sentence-split finding cost 5 extra dispatches. Any `design-block` reset the review cycle, so a fix-round brief edit re-ran the full battery cold. The `owners-page-param` cost per pass rose from $5.56 (v0.1.29) to $10.59 (v0.2.0), with reviewers noting a diff "byte-identical to the pass-1 diff already approved". The v0.3.1 and v0.3.2 sweeps showed one dominant critical: the slice's requirement id absent from the design doc. It cost about two reviewer dispatches per instance, with round-1 oracles passing in every rep. In v0.3.9, 9 of 12 implementing reps failed the autofix audit on the first build. The design expert's own block omitted a path its dispatch wrote, or the PRD expert's non-goal ADR had no covering record. Each bounce cost a superseding block at $1.08 on average. On `dev-7e6fdc4f`, a PRD change made in consultation reached review unmirrored in the design doc: $6.14 of a $21.54 rep for one row.

## Options Considered

1. **Status quo on the PRD, or one generalized `doc-autofix` record.** Rejected: a zero-semantic fix re-flowed the slice; a rename forces log migration and blurs which expert audits which path.
2. **Suppress mid-slice design triage, or accept the reset cost as the price of provenance.** Rejected: the triage of a changed requirement is deliberate. The cost sat in the reset, +90% on a one-line clamp.
3. **A self-review clause alone for the design-doc id; or parse the Contracts table row by row.** Rejected: a grep-checkable fact needs no prose. Row parsing is brittle for a judgment the doc-reviewer renders well.
4. **Teach the expert to list its paths; or widen the audit to accept any expert record.** Rejected: a prose rule missed nine times in twelve. The audit's value is that a record names the path it claims.
5. **Doctrine only for the consultation gap; or a router-side design dispatch.** Rejected: a skipped bullet costs the cascade; a synthetic `consultation-request` has no author to return to.
6. **An additive `prd-autofix` record, a review cycle bounded by supersession, a presence check in the gate, coverage checked at the expert's append, and a build-pass gate on PRD-changing consultations.** Chosen.

## Decision

**A mid-slice brief edit lands as a bounded, recorded change that engines check at append and gate time; only a superseding `design-block` resets the review cycle.**

- **PRD autofix.** Root applies an autofix-tagged finding on `docs/prd.md` verbatim and appends a `prd-autofix` record. The record carries `author: "root"`, `file: "docs/prd.md"`, and category `writing-standards` or `structural`. The 5-line and 200-character caps apply, with no heading, anchor, REQ-ID, fence, or link change. The PRD expert judges every record on its next dispatch; an illegitimate one gets a corrective edit and a superseding `prd-entry`, a failed mechanical audit aborts with `abort_reason: "prd-mismatch"`. The audit closes at the latest `prd-entry`, the design-doc audit at the latest `design-block`. Direct-edit detection stays design-doc-scoped; a test pins the deferral. The record is not substantive.
- **The review cycle.** It starts at the latest `design-block` carrying `supersedes_record_at`; the pointer is validated where honored (integer, earlier line, a design-block of the slice). An initial `design-block`, a `prd-entry`, or an interrupted round leaves review history live. Dissent is cycle-wide, the latest `review-feedback` per reviewer, and `prior-critical` decays with that reviewer's next verdict. The fix basis is the plan of the oldest outstanding dissent; a dissent no plan precedes fails closed as `delta-unavailable`. A docs, test, or config escape adds that surface's reviewers at `low` over `fix-delta`; a prod, unknown, or harness-runtime escape stays cold. Build retries still count from any `design-block`. A superseding block before the first build-pass with the same verdict and effort is a correction of record, not a design revision. A pointer outside the slice fails closed to a revision.
- **Presence in the gate.** `python3 scripts/grading.py contracts-sync --feature <req_id>` fails the gate when the id is absent from `docs/prd.md` or `docs/system-design.md`, vacuous when the design brief is absent. `contracts-sync` is a `[gate]` verb in `layout.toml`; a failure appends `build-failure` with `abort_reason: "design-mismatch"`, routed to the system-design-expert, since the implementer never edits the design doc. Row fidelity stays doc-reviewer judgment. The check can tighten to row-level verification if the presence floor proves too permissive. The self-review walk traces every Done-when bullet, PRD edge case, and named design risk to a test.
- **Experts record what they write.** `handoff.py append design-block` refuses a block that leaves an uncommitted design-doc path uncovered. The check applies the audit's own step-two rule with the candidate block in the entry set. An unreadable git state skips the check; the gate audit still fails closed. A `prd-entry` carrying `scope_overrides` covers the non-goal ADR it records; `docs/adr/README.md` is covered whenever every other dirty ADR path is. ADRs are documentation: the implementer reads the design doc, the PRD entry, the two principle briefs, and the ubiquitous language, never the ADR directory. The design expert follows an ADR back-link only when a slice touches a line that cites one. An ADR is written when a decision constrains future slices or reverses a recorded one; a smaller rationale is one clause on the current-state line.
- **The design sync gate.** `append build-pass` refuses while a product-requirements-expert `consultation-response` since the last `design-block` names `docs/prd.md` in `memory_updates` and no system-design-expert response or `design-block` follows. The refusal names the line and the consultation to raise; the implementer raises it, the design expert's consultation mode writes the mirrored rows, and the build-pass lands on resume. The scan mirrors the review-feedback anchor gate: one linear pass keyed by `req_id`, malformed lines skipped.

## Consequences

**Positive:**
- A doc-only PRD fix resolves in its round; `prd-entry` regains its meaning as a semantic-change signal.
- A fix round after a brief edit costs the dissenters plus the doc surface's reviewer, not four cold re-reads; roster resolution no longer depends on append order.
- The dominant doc critical became a gate failure resolved before reviewers dispatch. The autofix-audit correction round disappeared at its source. The design expert's triage read shrank by the ADR directory.
- Where the consultation cascade fired, the replacement costs about $1.70 against $6.14.

**Negative:**
- A fourth `abort_reason` and a thirteenth record type widen the closed enums; an uncovered direct edit to `docs/prd.md` stays undetected.
- A docs-only escape is reviewed by the doc surface alone at `low`, and "cycle" names two boundaries, retry and review, which `route-spec.md` distinguishes.
- A req_id present for the wrong reason, a stray mention or a stale row, passes `contracts-sync`.
- A `design-block` append runs two git reads; design-doc dirt from another in-flight slice is refused at the append instead of the gate.
- A consultation with nothing to carry costs about $1.70; an unrelated design answer after the PRD change clears the gate, which doctrine covers.
- The maven/gradle module rule once fired `multi-module` on every prod-plus-test first pass; [Module Derivation](2026-07-17-module-derivation.md) resolved it on 2026-08-10 by deriving a prod/test pair as one module.

## Implementation

The implementation spans these surfaces. `harness/core/scripts/handoff/` (`autofix.py`, `gates.py`, `findings.py`, `routing.py`) and `harness/core/scripts/grading/` (`planner.py`, `contracts.py`, `handoff_facts.py`) with their tests. `harness/core/schemas/scratch/` (`prd-autofix`, `review-plan`, `build-failure`). `route-spec.md` § Gate 2b, § Gate 3, § Gate 5. The `handoff-routing`, `handoff-append`, `prd-authoring`, `review-workflow`, and `tdd-workflow` skills. The stacks' `design-validation` and `code-quality-gate` skills. The product-requirements-expert and system-design-expert agents. The `layout.toml` gate-verbs vocabulary and the `CLAUDE.md` Quality Gate chapters.

## References

- [Deterministic Routing Engines](2026-07-02-deterministic-routing-engines.md) — the autofix audit command and the routing table these decisions extend.
- [Review Convergence](2026-07-14-review-convergence.md) — the risk-proportional plan engine and fix-round ladder whose cycle boundary and escape scope are set here.
- [The Reviewer Roster](2026-06-18-the-reviewer-roster.md) — the `surface_reviewers` map a widened escape draws on.
- [The Product Expert and the Root Conversation](2026-06-19-the-product-expert-and-the-root-conversation.md) — scope-lock's quoted `scope_overrides` and the consultation with a position.
- [Docs as Harness Project API](2026-06-12-docs-as-harness-project-api.md) — the briefs these engines keep in agreement.
- [Test Conventions at Write Time](2026-09-03-test-conventions-at-write-time.md) — the self-review walk the coverage-trace clauses join.
- [Module Derivation](2026-07-17-module-derivation.md) — resolved the maven/gradle `multi-module` false trigger on 2026-08-10, a prod/test pair deriving one module.
- [The Eval Bench](2026-07-15-the-eval-bench.md) — the sweeps that priced each cascade.
- [Resilience-First Improvement Doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — why the direct-edit scan extension stays deferred.
