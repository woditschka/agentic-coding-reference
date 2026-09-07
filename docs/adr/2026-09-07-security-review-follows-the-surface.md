# The Security Reviewer Follows the Surface on High Plans

**Status:** Accepted

## Context

Across the committed v0.3.x runs the security reviewer was dispatched 120 times and returned three fixable findings and two informational ones. Every first-pass plan rated high dispatched it, and nine of twelve feature slices in the v0.3.9 sweep rated high on the 80-line oversize trigger alone. It runs on Opus at $0.67 a dispatch, about five percent of a sweep, and sits on the critical path of every full battery. Its one substantive finding in v0.3.9 named a request-derived string composed into an emitted URL: a surface the diff text shows.

The model-tier decision keeps security review premium because it hunts what no checklist names. The risk-proportional decision sends every high plan to the full battery so review is never less by accident. Neither says that a change with no security surface needs a security read.

## Options Considered

1. **Keep the unconditional dispatch.** Rejected: the spend buys no finding on the recorded slices, and the doctrine gates dispatch on evidence.
2. **Move the reviewer to the mid tier.** Rejected: the model-tier decision holds that a judgment reviewer never sits below the implementer.
3. **Gate the dispatch on a declared security surface, fail closed** (chosen).

## Decision

**On a high first-pass plan the security reviewer is dispatched when the change carries a security surface. Otherwise the rest of the roster runs.** A surface is any of the following. A sensitive path. A config-surface file. An unclassifiable or binary path. A prior critical. A hit of the layout's `[review] security_surface` probe over the change's added production lines. The probe is the stack's syntax for a new entry point, a request-derived value, a query, a process or file operation, or a security-configuration change. The Java and Go skeletons ship one. A project that declares no probe keeps the reviewer on every high plan, and a null probe result reads as a hit. The feature row records the probe's hits as `security_surface_paths`; the plan's rationale names the omission. Fix rounds are unchanged: a slice that touched sensitive paths keeps the reviewer, and a security-raised critical draws the full battery.

## Consequences

**Positive:** the five percent moves to where the surface is, and the critical path of a size-only high plan loses its slowest reviewer.

**Negative:** a probe is only as good as its patterns. A stack whose entry-point syntax the probe misses loses a read it would have had; the fail-closed defaults and the sensitive globs are the floor under that. The additive-roster decision's "never subtracted" now reads per plan, as the risk-proportional decision already made it.

## Implementation

`grading/config.py` (`security_surface` in `validate_review`), `grading/features.py` (`security_surface_paths`), `grading/planner.py` (`_security_relevant`), the grader-features schema, the three layout skeletons and sample layouts, `review-workflow`, and the project API's `[review]` paragraph.

## References

- [2026-06-11 model-tier-assignment](2026-06-11-model-tier-assignment.md): the premium tier this decision leaves in place.
- [2026-06-18 additive-reviewer-roster](2026-06-18-additive-reviewer-roster.md) and [2026-07-09 risk-proportional-review](2026-07-09-risk-proportional-review.md): the roster and ladder this decision narrows.
- [2026-09-01 evidence-gated-dynamic-tiering](2026-09-01-evidence-gated-dynamic-tiering.md): the doctrine of gating dispatch on evidence.
