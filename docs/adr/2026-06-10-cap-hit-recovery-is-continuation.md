# Cap-Hit Recovery Is Continuation: Slice Size Decoupled from Dispatch Budget

**Status:** Accepted

## Context

Each creator and verifier agent carries a `toolCallBudget` and runs a Scoping Pre-Check before its first tool call. The original rule keyed both decisions to the same number: a pre-check estimate over budget stopped the dispatch and filed a `consultation-request` for re-scoping. A truncated dispatch likewise routed toward re-split. That conflated two different questions. Whether a slice holds more than one behavior is semantic; whether one behavior fits one dispatch is mechanical. A single coherent behavior can exceed any budget on file count or test-matrix breadth alone — and it has nothing to split, so re-scoping it produces artificial fragments. The `tdd-workflow` and `review-checklist` skills already carried the decoupled rule; `agentic-harness.md` still stated the old remedy.

## Options Considered

1. **Keep budget-keyed re-scoping** — any overrun files a `consultation-request`. Simple, but re-splits single behaviors into fragments and makes the budget a scope authority it cannot be.
2. **Raise budgets until overruns vanish** — hides the problem; budgets stop being a checkpoint-planning signal at all.
3. **Decouple the axes (chosen)** — slice size is judged from the inbound records, budget-free; `toolCallBudget` governs only dispatch length. A length overrun proceeds with a planned checkpoint and is completed by continuation; only a multi-behavior slice re-scopes.

## Decision

We adopt option 3. The Scoping Pre-Check judges two orthogonal axes with different remedies. **Slice size:** a slice spanning more than one behavior or bounded context stops before starting and files a `consultation-request` — mis-sized even when it would fit the budget. **Dispatch length:** a single-behavior overrun is not a re-scope; the dispatch proceeds with its planned checkpoint, hands off a partial-artifact record, and a continuation completes the same slice. A cap-hit is a length signal, not a scope verdict. Re-split is reserved for the Pre-Check's over-size branch and for non-convergence.

## Consequences

**Positive:**
- Single behaviors stay whole; commits ship behavior, not fragments of an artificial decomposition.
- The budget becomes purely a checkpoint-planning device, which is the only thing a tool-call count can honestly measure.
- Truncation recovery and budget doctrine agree: both continue the same slice.

**Negative:**
- A chronically over-wide behavior no longer surfaces as a re-scope request; it surfaces later, as non-convergence or as a budget-tuning signal at re-triage.

## Implementation

**Non-goal:** This is harness coordination doctrine, not a feature requirement. The two-axes rule lives in the `tdd-workflow` skill (§ Scoping Pre-Check), the `review-checklist` skill (§ Partial-Artifact Contract), and `agentic-harness.md` (§ Dispatch-Event Contract and Recovery Paths, "Budget"). Both samples carry it.

## References

- [`agentic-harness.md`](../agentic-harness.md) — § Dispatch-Event Contract and Recovery Paths
- [`2026-06-04-deterministic-truncation-detection.md`](2026-06-04-deterministic-truncation-detection.md) — the detection rule whose recovery action this re-aims
- [`2026-06-10-continue-only-resume.md`](2026-06-10-continue-only-resume.md) — the runtime fast-path for the continuation this ADR makes the default
