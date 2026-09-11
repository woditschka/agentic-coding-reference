# The Security Reviewer Follows the Surface on High Plans

**Status:** Accepted (absence rule inverted and the gray plan bound to the probe by the [in-file amendment](2026-09-07-security-review-follows-the-surface.md#amendment-2026-09-09-the-stack-ships-the-probe-the-gray-plan-reads-it))

> **Amended.** The decision below keeps the reviewer on every high plan when a project declares no probe. The amendment ships the probe with the stack, so an absent declaration reads the stack's list, and the planner's gray trim reads the same fact. Everything else stands.

## Context

Across the committed v0.3.x runs the security reviewer was dispatched 120 times and returned three fixable findings and two informational ones. Every first-pass plan rated high dispatched it, and nine of twelve feature slices in the v0.3.9 sweep rated high on the 80-line oversize trigger alone. It runs on Opus at $0.67 a dispatch, about five percent of a sweep, and sits on the critical path of every full battery. Its one substantive finding in v0.3.9 named a request-derived string composed into an emitted URL: a surface the diff text shows.

The model-tier decision keeps security review premium because it hunts what no checklist names. The risk-proportional decision sends every high plan to the full battery so review is never less by accident. Neither says that a change with no security surface needs a security read.

## Options Considered

1. **Keep the unconditional dispatch.** Rejected: the spend buys no finding on the recorded slices, and the doctrine gates dispatch on evidence.
2. **Move the reviewer to the mid tier.** Rejected: the model-tier decision holds that a judgment reviewer never sits below the implementer.
3. **Gate the dispatch on a declared security surface, fail closed** (chosen).

## Decision

**On a high first-pass plan the security reviewer is dispatched when the change carries a security surface. Otherwise the rest of the roster runs.** A surface is any of the following. A sensitive path. A config-surface file. An unclassifiable or binary path. A prior critical. A hit of the layout's `[review] security_surface` probe over the change's added production lines. The probe is the stack's syntax for a new entry point, a request-derived value, a query, a process or file operation, or a security-configuration change. The Java and Go skeletons ship one (moved to the stack's shipped defaults by the amendment below). A project that declares no probe keeps the reviewer on every high plan, and a null probe result reads as a hit (absence rule inverted by the amendment below). The feature row records the probe's hits as `security_surface_paths`; the plan's rationale names the omission. Fix rounds are unchanged: a slice that touched sensitive paths keeps the reviewer, and a security-raised critical draws the full battery.

## Consequences

**Positive:** the five percent moves to where the surface is, and the critical path of a size-only high plan loses its slowest reviewer.

**Negative:** a probe is only as good as its patterns. A stack whose entry-point syntax the probe misses loses a read it would have had; the fail-closed defaults and the sensitive globs are the floor under that. The additive-roster decision's "never subtracted" now reads per plan, as the risk-proportional decision already made it.

## Implementation

`grading/config.py` (`security_surface` in `validate_review`), `grading/features.py` (`security_surface_paths`), `grading/planner.py` (`_security_relevant`), the grader-features schema, the three layout skeletons and sample layouts, `review-workflow`, and the project API's `[review]` paragraph.

## Amendment (2026-09-09): The stack ships the probe; the gray plan reads it

The v0.3.10 sweep showed the decision above inert. The system under test's committed `layout.toml` predates the probe. `security_surface_paths` read empty on every run, and the fail-closed default kept the reviewer on every high plan. The same sweep dispatched the planner six times against once in v0.3.9, since cleaner slice histories leave the engine without triggers. The planner resolved every gray plan to a roster of three or four and never left the security reviewer off.

The root cause is placement, not the consumer. The probe is stack syntax: the same regexes sit in every Java consumer's layout. A project-owned file is by contract never rewritten on upgrade, so every consumer falls behind the moment the harness learns a new pattern. Three changes.

- **The stack ships its syntax.** `scripts/layout-defaults.toml` is harness-owned and replaced on every materialize or plugin upgrade. It carries the stack's `[review] security_surface` and the four `[conventions]` keys, and nothing else: a project fact there fails the load. The engine merges each key under the project's `layout.toml`: a declared key wins, an absent key reads the default. An explicitly empty probe stays empty, so fail closed remains the project's call. The generic stack ships an empty probe. The init skeletons no longer restate the syntax, and the doctor names the probe in effect and warns when a project restates a default.
- **Every plan records the probe's result** in `basis.security_surface` (`declared`, `paths`). The planner judges from the fact the high-plan rule reads instead of re-deriving it from the diff.
- **The planner's gray default follows the rule.** A probe in effect with no hit leaves the security reviewer off. The exceptions are narrow and each is named in the rationale: the diff adds a secret, changes a dependency, or reaches an input or sink that no pattern in the probe's list matches. The planner reads that list from the shipped defaults and the project's override, so the exception is a checked fact. New logic over an input the probe already covers is not an exception; a removed or weakened check is one. The probe itself reads removed production lines as well as added ones, since a deleted match is a weakened guard. An empty probe or a null result keeps the reviewer, as on a high plan.

This inverts the decision's absence rule. A Java or Go project that declares no probe now reads the stack's, so on its next upgrade a no-hit high or gray plan runs without the security reviewer. That is the intended effect of the decision, delivered by the harness instead of by a hand edit in every consumer. A project that wants the reviewer on every plan declares `security_surface = []`; the doctor shows which of the three states is in effect. A project whose layout restates the old list keeps its copy and is warned. An older install without the defaults file sees no change.

The boundary the change draws: syntax the engine matches is the stack's and ships with the harness. Where a project's files live, how it builds, and what it treats as sensitive stay project data.

Implementation: `scripts/layout-defaults.toml` per stack, `grading/config.py` (`load_stack_defaults`, `merged_table`, `shadowed_keys`), the doctor's `layout-review` and `layout-defaults` checks, the runtime roster and the init `.gitignore` block, the three skeletons, and the review-plan schema's `basis.security_surface`.

## References

- [2026-06-11 model-tier-assignment](2026-06-11-model-tier-assignment.md): the premium tier this decision leaves in place.
- [2026-06-18 additive-reviewer-roster](2026-06-18-additive-reviewer-roster.md) and [2026-07-09 risk-proportional-review](2026-07-09-risk-proportional-review.md): the roster and ladder this decision narrows.
- [2026-09-01 evidence-gated-dynamic-tiering](2026-09-01-evidence-gated-dynamic-tiering.md): the doctrine of gating dispatch on evidence.
