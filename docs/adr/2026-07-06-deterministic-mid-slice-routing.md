# Deterministic Mid-Slice Routing via handoff.py route

**Status:** Accepted

## Context

The Handoff Conditions table is deterministic: a passed gate names the next agent without judgment. Yet every mid-slice transition paid a `pipeline-coordinator` dispatch — model inference re-deriving a table lookup, at roughly 10k input tokens per hop and five hops per happy-path slice. The coordinator's damage handling lived in prose, untestable and occasionally misread. The primitives were already in place: `handoff.py` parses strictly, validates against schemas, and computes the retry counter.

## Options Considered

1. **Keep the LLM coordinator on every hop** — flexible, but pays inference for decisions the table already made and cannot be regression-tested. Rejected: cost without judgment.
2. **Fully scripted routing, no coordinator** — removes the escalation surface for states the table does not decide (fresh intake, refactor-first sibling ordering). Rejected: those are genuine judgment calls.
3. **Two-part router** (chosen) — a `route` subcommand executes the table; the coordinator handles only its `escalate` arm and fresh-intake classification.

## Decision

**`python3 scripts/handoff.py route` executes the Handoff Conditions table and prints one JSON decision: `dispatch`, `blocked`, or `escalate`.** Root runs it after each dispatch returns and follows it; the coordinator is dispatched only on `escalate` and for fresh intake. Route is fail-closed: a dirty log or an unroutable slice yields `blocked` with the exact errors — it never repairs and never guesses. A failed gate is a `dispatch` of the upstream agent carrying the errors: the documented bounce. Findings dispatch to their artifact owners; an escalate finding flags `halt_after` and blocks re-review until the human decides. The `escalate` arm covers no-active-slice, `refactor-first` sibling ordering, truncation of an agent with no recovery row, and any state matching no table row. A deterministic `refactor-resume` re-triages the original once the refactor completes. Fixture tests in `test_handoff.py` pin every table row, every damage mode, and both recovery ladders; a table edit extends `route` and its tests in the same change.

## Consequences

- Four to five model dispatches per slice become one Bash call each; the coordinator's per-slice cost drops to its judgment cases.
- Recovery behavior (truncation continue, retry ladder, reviewer stall, abort short-circuits) is regression-tested instead of prose-interpreted.
- The table is now stated once and executed from that statement; coordinator prose no longer needs to restate it accurately.
- The coordinator remains the documented owner of every `escalate` state; removing it entirely stays out of scope.

## References

- [Executable Pipeline Contracts](2026-07-02-executable-pipeline-contracts.md) — the same move one level down: contracts enforced by code, not prose.
- [Deterministic Truncation Detection via Dispatch-Start](2026-06-04-deterministic-truncation-detection.md) — the detection rule `route` now executes.
- [Append-Only JSONL Handoffs](2026-05-08-append-only-jsonl-handoffs.md) — the ledger `route` reads as its only input.
