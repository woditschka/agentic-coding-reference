# An Approved Verdict Carries No Fix-Routable Finding

**Status:** Accepted

## Context

The record contract allowed findings on an `approved` review verdict, while Gate 4 processes findings only from non-approved verdicts; only `escalate` deliberately crossed the boundary. An approved record's `autofix` finding was therefore dropped silently. The eval bench's first sweep recorded the consequence: the reviewer re-raised the unchanged finding as a `changes_requested` dissent one round later. The other branch is worse — a consistent re-approval reaches feature-complete with a known fixable finding dropped.

## Options Considered

1. **Route approved-record autofix findings to owners without flipping the verdict.** Rejected: with no re-review, the carrying record stays the reviewer's latest, so the router re-dispatches the same findings forever or needs new processed-state; and a post-approval edit invalidates exactly what the approval covered.
2. **Forbid all findings on approval.** Rejected: `escalate` crosses the boundary by design, `clarify` is a question rather than a fix, and `approved_aspects` notes stay valuable.
3. **Bounce approved records carrying `autofix` or `blocked` findings at the record gate** (chosen).

## Decision

**Gate 4 rejects a `review-feedback` record whose verdict is `approved` and whose findings carry tag `autofix` or `blocked`.** The bounce re-dispatches the reviewer like every other record-gate defect: the reviewer drops the note or records `changes_requested`. `escalate` and `clarify` findings stay legal on approval.

## Consequences

- Wanting a fix now costs the honest `changes_requested` round; the silent-drop-then-delayed-dissent path is closed by construction.
- A mis-tagged advisory note costs one bounce round; the message names the choice.

## Implementation

The record gate in `harness/core/scripts/handoff/routing.py`, pinned by `tests/handoff/test_routing.py`; stated once each in `route-spec.md` § record gates and `review-workflow` § record contract.

## References

- [Deterministic Mid-Slice Routing via handoff.py route](2026-07-06-deterministic-mid-slice-routing.md) — the gate this rule joins; code enforcement over prose.
- [The Eval Bench Measures Cost per Pass](2026-08-02-eval-bench-cost-per-pass.md) — the measurement that surfaced the dropped-finding round.
