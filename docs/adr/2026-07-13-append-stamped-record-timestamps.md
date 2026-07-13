# Append-Stamped Record Timestamps

**Status:** Accepted

## Context

Every handoff record carries a `ts` field, and the board derives two figures from it: step durations (dispatch-start → record) and the cost overlay's transcript window. The field was author-supplied: each agent composed an ISO 8601 value into the record it piped to `append`. A model cannot read the clock, so those values were invented. One observed slice logged an 8.5-hour timeline of round-number timestamps for a run whose subagent transcripts span 55 minutes. Every duration on that board was fiction, and the cost lookup found zero transcript messages inside the fabricated windows. The two engine-authored record types (`review-plan`, `grader-features`) already stamp `datetime.now(timezone.utc)` programmatically and were the only accurate timestamps in the log.

## Options Considered

1. **Instruct agents to run `date -u` before composing.** Rejected: an instruction is not a guarantee; the failure mode returns whenever an agent skips the step, and nothing detects it.
2. **Validate plausibility at append** (reject a `ts` far from the wall clock). Rejected: it keeps the composed field and adds a tolerance knob; a value inside the tolerance is still wrong for durations.
3. **Stamp `ts` in `handoff.py append`** (chosen). Every record already passes through the one sanctioned write, so the choke point exists; append time equals event time because records are appended when their event happens.

## Decision

**`ts` is engine-stamped at the append boundary; author-supplied values are overwritten.** `cmd_append` sets `record["ts"] = datetime.now(timezone.utc).isoformat()` after parsing and before validation. The schemas keep `ts` required — the stamp satisfies them, and the `validate` sweep still rejects a legacy or raw-written record with a missing or malformed value. Record templates in the skills no longer show a `ts` field. The engine writers that bypass the stdin CLI (`score-change.py`) keep stamping their own real time under the same clock.

## Consequences

- Ledger time is wall-clock time by construction; board durations and cost windows measure real work.
- `ts` moves across the trust boundary: it joins line numbers and canonical form as appender-owned, leaving agents authoring payload only.
- A record composed with a `ts` still appends cleanly — the value is discarded, so no migration or agent retraining is load-bearing.
- Append time, not event-start time, is what the stamp captures; the dispatch-event contract (record appended at the event) keeps the difference to seconds.

## Implementation

`harness/core/scripts/handoff.py` (`ts_now`, `cmd_append`), `test_handoff.py` (stamp pinned in fixtures; overwrite and fill covered), the record templates in `handoff-append`, `tdd-workflow`, `review-workflow`, `prd-authoring`, `change-grading`, and `design-validation`, the schema `ts` descriptions, `score-change.py` (engine writers stamp through `ts_now` in `_append_validated`), the `handoff-board` skill's duration prose, `docs/agentic-harness.md` with its installed copy, and the `handbook-delta.expected` re-pin.

## References

- [Handoff Log Access: Single Deterministic Tool, Not Free-Form Writes](2026-06-11-handoff-log-access-tool.md) — the choke point this decision builds on; stamping is only sound because every write passes through `append`.
- [Single Pricing Source as a Gated Vendored Copy](2026-07-13-single-pricing-source-vendored-copy.md) — the cost overlay whose transcript windows key on `ts`.
