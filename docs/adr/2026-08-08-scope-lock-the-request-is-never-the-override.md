# Scope-Lock: The Request Is Never the Override

**Status:** Accepted

## Context

The eval bench's refusal task exposed a judgment coin-flip at the middle loop's intake. `visit-cancel` asks for work conflicting with two recorded non-goals (the SUT's NG-4, NG-5) and states no owner override; the designed outcome is a consultation and no change. Recorded refusal rates fell from 4/4 (v0.1.22) to 1/3 (v0.2.0) and 0/1 (v0.2.1). A correct refusal costs ~$1.20 in 3 minutes; an implementing rep costs $15–23 in 40–65 minutes.

The ledgers show one mechanism, uniformly. Every implementing rep ran the boundary check, found both rows, and then overrode them itself — narrowing each via a dated non-goal ADR and continuing. Each cited the same license: the SUT PRD's Non-Goals preamble records the rows as derived from observed absence, part of an open consultation. The agents read the feature request as the answer that settles it. The refusing reps read the same text and consulted — the v0.2.0 r1 request names the options, recommends one, and stops.

The agent instruction contained its own counter-argument. "Push back at artifact level" demanded a consultation on any contradiction; "Record what the human owns" sanctioned resolving a decision-to-proceed into a non-goal ADR. With the dispatch doctrine declaring the prompt carries "the distilled decisions" of a root elicitation, the request itself was readable as the owner's decision. Downstream nets fire too late: a reviewer's `escalate` halt lands after implementation, and the refusal bar reads the diff.

## Options Considered

1. **Prose only: sharpen the agent instruction.** Rejected as the whole fix: the flip is a judgment call under a genuinely ambiguous rulebook, and prose alone leaves the loophole's shape — silent narrowing — representable in the ledger.
2. **Require a human `consultation-response` for every Non-Goals change.** Rejected: a dispatch that already states the owner's decision (the `visit-edit` prompt names NG-5 and narrows it) would force a pointless round-trip; headless runs with a stated override would fail outright.
3. **Firm up the SUT's PRD hedge.** Out of scope here: that edits the eval subject, not the harness. It remains open as eval-validity work; this decision must hold for any consumer whose briefs carry honest provenance hedges.
4. **Doctrine plus a fail-closed gate with a dispatch-carried override arm** (chosen).

## Decision

**A recorded Non-Goals row changes only under the owner's quoted decision. The request is never the override; Gate 1 bounces a silent narrowing.**

- **Doctrine.** The product-requirements-expert proceeds against a recorded requirement or Non-Goals row only when the dispatch names that row and states the owner's decision on it. Anything less — a plausible reading, an agent-supplied rationale, a provenance hedge on the row — is a contradiction and exits via a `consultation-request` targeting `human`. Provenance uncertainty strengthens the obligation: whether an absence was deliberate is exactly what only the owner knows.
- **Calibration, not caution.** The same section instructs the opposite default for reversible questions: decide, record, move on; consult once per dispatch, carrying options, one recommendation, and the consequence of each answer. The gate binds only the irreversible kind — rewriting the recorded scope boundary.
- **Mechanics.** The `prd-entry` record gains an optional `scope_overrides` array. Per changed row it carries the `non_goal_id`, the owner's decision quoted verbatim, and its source. A source is `dispatch`, or `consultation:<line>` pointing at a `consultation-response` with `author: "human"` for the same `req_id`; a cited answer must contain the quote. Gate 1's scope-lock check compares the worktree's `docs/prd.md` Non-Goals rows against `HEAD`: an uncovered change or removal bounces, an entry naming an unchanged row bounces as padding, added rows pass free. An unreadable baseline — git failing to launch, a non-UTF-8 or oversized file — fails closed. No repository, an unborn `HEAD`, or an untracked `prd.md` leaves no baseline and the check empty. A `prd-autofix` touching a Non-Goals row is rejected by the autofix audit, so the mechanical-fix lane cannot dirty the delta.
- **Layering holds.** The routing core stays deterministic over its inputs: `handoff.py` computes the Non-Goals delta (the one impure read) and passes it into `_route_decision`, mirroring how the CLI already owns the autofix audit's git reads.
- **Honesty bound, stated.** The `dispatch` source is the agent's own attestation — the dispatch prompt is not in the ledger, so no gate can verify the quote against it. A forged `author: "human"` consultation-response sits in the same trust class: a plain JSONL file cannot prove authorship. A mid-slice `git commit` moves the `HEAD` baseline and empties the delta; no hook blocks it today, so that barrier is instruction-only. The gate's claim is therefore narrower than tamper-proof: silent narrowing becomes unrepresentable at Gate 1. A false override is a fabricated first-class record — visible to the reviewers' diff reads and the human reading the ledger, where a rationalization in `notes` prose was not.

## Consequences

- A headless run whose dispatch states the override (`visit-edit`) passes unchanged; one whose dispatch does not (`visit-cancel`) has no compliant path to a Non-Goals edit — the designed exit is the consultation, and the run ends without a diff.
- Interactive intake is unchanged for decided scope: root's elicitation distillate names the row and the decision, and the expert quotes it. Undecided scope now costs one designed round-trip — the elicitation pause the pipeline already models.
- A cross-version eval delta spanning this change measures the rule, not model judgment; the trend's fingerprint and notes machinery attributes it.

## Implementation

- `harness/core/.claude/agents/product-requirements-expert.md` § Working from a Root Elicitation — the override bright line, the consult-once calibration, the quoted-decision rule, the qualified elicitation-distillate sentence.
- `harness/core/.claude/skills/prd-authoring/SKILL.md` § Scope Overrides — the field contract, the uncommitted-delta binding, the carry-forward rule.
- `harness/core/schemas/scratch/prd-entry.schema.json` — `scope_overrides` (patterns and length caps); `harness/core/scripts/handoff/records.py` — `ScopeOverride`; `harness/core/scripts/handoff/__init__.py` — the export.
- `harness/core/scripts/handoff.py` — `_ng_delta` (the impure read) and the Non-Goals bound in the autofix audit; `harness/core/scripts/handoff/routing.py` — `_scope_lock_errors` in Gate 1.
- `harness/core/.claude/skills/handoff-routing/SKILL.md` § Validation Gates, `route-spec.md` § Gate 1, `harness/stacks/*/.claude/skills/document-writing/review-checks.md` § Autofix on the PRD, `docs/glossary.md` — the prose contract.
- `harness/core/scripts/tests/handoff/test_routing.py` — pins for coverage both directions, source validation, the quote-in-answer rule, padding, carry-forward, the fail-closed branch, nested checkouts, and every grace state.

## References

- [Append-only handoff records](2026-05-08-append-only-jsonl-handoffs.md) — the ledger the gate reads.
- [Typed Python core](2026-07-17-typed-python-core.md) — the sanctioned raw sites the gate's reads use.
- [The eval bench measures cost per pass](2026-08-02-eval-bench-cost-per-pass.md) — the instrument that exposed the flakiness.
- [Brownfield briefs carry provenance](2026-07-31-derived-briefs-carry-provenance.md) — the honest hedge the doctrine now closes against.
