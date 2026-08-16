# The Route-Rule Inventory Is Generated from the Source

**Status:** Accepted

## Context

`route`'s JSON decision names a matched rule, but no document enumerated the rules: 23 of the 51 rule names the router can emit appeared in neither `route-spec.md` nor the `handoff-routing` skill. The route-spec header's maintenance contract — editing the spec means extending `route` and its tests in the same change — was enforced by nothing mechanical. An external review (2026-08-16) recommended generating routing documentation from the source with a drift gate; the [dispositions ADR](2026-08-16-external-review-dispositions.md) queued it. The routing source is imperative — decisions are constructor calls (`_dispatch`, `_bounce`, `_blocked`, `_escalate`) inside if-chains and `match` arms — so no importable table exists to walk.

## Options Considered

1. **Hand-maintain a rule table in route-spec.md.** Rejected: a 51-row hand copy of source facts is the drift the ownership principle prohibits — the 23 missing rules are the evidence.
2. **Generate the router from a declarative table.** Rejected by the dispositions ADR: a generation layer whose correctness must itself be gated, replacing a hand-written, typed, `assert_never`-exhausted router that works.
3. **Generate the inventory from the source by AST, gate drift in the battery.** Chosen.

## Decision

**`harness/render-route-rules.py` renders `route-rules.md` into the `handoff-routing` skill, and battery step 3j fails on drift.** The generator AST-walks the four decision constructors, resolves module-level name constants to agent names, merges duplicate rules, and errors on any non-literal rule argument — a partial inventory never renders. The file ships with the skill, so a consumer reading a rule name in a `route` decision has the lookup in the same directory; it carries a generated-file marker and materializes to every channel like any skill file. Routing invariant tests were found already present (`TestRoutingInvariants`: grade neutrality, roster exactness, cap termination, totality); no new invariant tests were needed.

## Consequences

**Positive:** every rule the router can print is documented, permanently — a new rule lands in the inventory or the battery fails. The route-spec's maintenance contract gains its first mechanical backstop.

**Negative:** the extractor is coupled to the constructor idiom; a refactor away from the four constructors must update the generator in the same change (step 3j makes the miss loud). Dispatch targets computed at decision time render as *(computed)*, not resolved values.

## Implementation

`harness/render-route-rules.py`, `harness/core/.claude/skills/handoff-routing/route-rules.md` (generated), `harness/verify_harness/checks/sync.py` `check_route_rules` (step 3j), `harness/tests/test_render_route_rules.py`, and the route-spec header's inventory pointer.

## References

- [ADR 2026-08-16: External-Review Recommendations: Dispositions](2026-08-16-external-review-dispositions.md) — the queue entry this decision lands
- [ADR 2026-07-06: Deterministic Mid-Slice Routing](2026-07-06-deterministic-mid-slice-routing.md) — the router this inventory documents
- [ADR 2026-07-14: Mechanical Promises into Engines](2026-07-14-mechanical-promises-into-engines.md) — the same doctrine, applied here to a documentation promise
