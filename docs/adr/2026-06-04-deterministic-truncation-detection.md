# Deterministic Truncation Detection via Dispatch-Start

**Status:** Accepted

## Context

The pipeline recovers from a truncated `feature-implementer` dispatch — one that ends before writing a `build-pass` or `build-failure`. Recovery must first *detect* truncation. An earlier design could not: from `.scratch/handoff.jsonl` alone, "implementer dispatched and truncated" was indistinguishable from "implementer not yet dispatched." Recovery therefore fired only when root signalled truncation out of band, which broke the harness's "observable from filesystem state alone" goal and left routing dependent on a human.

The `dispatch-start` record — every substantive agent appends one as its first tool call — closes that gap, but the decision was never recorded as an ADR. The mechanism landed in the `pipeline-handoff` skill and `agentic-harness.md`, while the `pipeline-coordinator` agent kept describing the superseded root-signal trigger. That contradiction persisted across all eight tool variants because no audit check compared the coordinator against the skill on this point.

## Options Considered

1. **Root-signal trigger (status quo before dispatch-start)** — recovery waits for an out-of-band human signal. Portable but non-deterministic; routing stalls without a human.
2. **Transcript / runtime telemetry** — read tool-call traces to detect a dead dispatch. Deterministic but runtime-specific, violating tool-agnostic invariant 2.
3. **Dispatch-start sentinel** — every substantive agent writes a `dispatch-start` first; a start with no subsequent substantive record for the same `(req_id, author)` is the signal. Deterministic and readable from state alone, portable across runtimes.

## Decision

We adopt option 3. Truncation is detected from `.scratch/handoff.jsonl` alone, by the Dispatch Truncation Detection rule in the `pipeline-handoff` skill. The root-signal trigger is superseded. The coordinator detects truncation from state rather than waiting for an out-of-band signal.

## Consequences

**Positive:**
- Routing is deterministic and needs no human in the recovery path.
- The detection rule is cause-agnostic — cap-hit, mid-stream truncation, abandonment, or network drop all read the same.
- An `audit-agents` § Truncation Detection Semantics check now flags any file that contradicts the skill on the mechanism, preventing the drift from recurring.

**Negative:**
- Detection depends on every substantive agent reliably writing `dispatch-start` first — itself an unenforced prose contract. A skipped `dispatch-start` reopens the original ambiguity.

## Implementation

**Non-goal:** This is a harness coordination decision, not a feature requirement. The rule lives in the `pipeline-handoff` skill (§ Dispatch Truncation Detection) and `docs/agentic-harness.md` (§ Dispatch-Event Contract and Recovery Paths); the coordinator agents detect from state across all four tool variants.

## References

- [`agentic-harness.md`](../agentic-harness.md) — § Dispatch-Event Contract and Recovery Paths
- [`2026-05-08-append-only-jsonl-handoffs.md`](2026-05-08-append-only-jsonl-handoffs.md) — the handoff log this detection reads
- [`2026-06-03-principles-over-rigid-rules.md`](2026-06-03-principles-over-rigid-rules.md) — `dispatch-start`-first is a hard contract under that taxonomy
