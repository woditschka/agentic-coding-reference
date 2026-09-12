# A PRD Change Made in Consultation Reaches the Design Doc Before Review

**Status:** Accepted

## Context

The inner loop consults the product-requirements-expert on a requirement gap and resumes under its answer. When that answer edits `docs/prd.md`, a new Done-when bullet, an edge case, or a known defect, the design doc mirrors none of it. `docs/system-design.md` carries the Known Defects table, the Contracts rows, and the Invariants the PRD's entries trace to. Gate 2b returns control to the requester, so nothing dispatches the system-design-expert, and the slice enters review with the two documents disagreeing.

The dev row `dev-7e6fdc4f` recorded the cost on visit-edit. The security reviewer's empty-date finding went to the requirements expert as a scope question, which is the routing the reviewer doctrine asks for. The expert recorded a known defect in the PRD. One round later the doc-reviewer blocked the missing design row as a coherence critical, the design expert re-triaged twice, and the full roster re-ran: $6.14 of a $21.54 rep, for a row one consultation would have written.

## Options Considered

1. **Doctrine only.** The implementer raises a second consultation on resume. Rejected as the sole measure: the rule lives in one bullet of one skill, and a skipped bullet costs the cascade again.
2. **A router-side dispatch.** `route` sends the design expert after a PRD-changing response. Rejected: the design expert's consultation mode answers a `consultation-request`, and a synthetic request has no author to return to; the roundtrip contract would need a second shape.
3. **An append-time gate on the build-pass** (chosen), beside the doctrine.

## Decision

**`append build-pass` refuses while a `product-requirements-expert` consultation-response since the last `design-block` names `docs/prd.md` in `memory_updates` and no `system-design-expert` consultation-response or `design-block` follows it.** The refusal names the line and the consultation to raise, then the implementer stops; the build-pass lands on resume after the consultation returns. The implementer's requirement-gap step raises that consultation, the design expert's consultation mode answers it by writing the mirrored rows, and the requirements expert names the file when its answer edits the PRD. A `design-block` clears the gate because a re-triage rewrites the design doc.

The gate mirrors the review-feedback anchor gate: one linear scan of the ledger keyed by `req_id`, malformed lines skipped, no log content echoed.

## Consequences

**Positive:** the design doc never enters review lagging the PRD. Where the cascade fired, the replacement path costs one design consultation and a resume, about $1.70 against $6.14. The rule is enforced where the miss was observed, on every channel and tool.

**Negative:** when the design expert has nothing to carry, the consultation is $1.70 of overhead. An unrelated design answer after the PRD change clears the gate; the doctrine, not the scan, carries that case.

## Implementation

- `harness/core/scripts/handoff.py` — the gate and its refusal; `tests/test_handoff.py` pins the ordering cases.
- `tdd-workflow` § TDD Cycle step 2, the three stacks' `design-validation` § Consultation Mode, the product-requirements-expert agent, `handoff-append`, `handoff-routing`, and `route-spec.md` § Gate 2b and § Gate 3 carry the rule.

**Requirements:** none; a harness-level routing decision.

## References

- [2026-09-07 experts-record-what-they-write](2026-09-07-experts-record-what-they-write.md) — the append-time refusal as the enforcement shape.
- [2026-08-08 scope-lock](2026-08-08-scope-lock-the-request-is-never-the-override.md) — Gate 1's precedent for a PRD-side check at the gate.
