# A Prod/Test Pair Is One Module

**Status:** Accepted

## Context

Risk-proportional review shipped in v0.1.21: `grading.py review-plan` classifies each change, buys a surface-matched roster for the clear low-risk cases, and defers the gray zone to the `review-planner`. The recorded eval series says the narrowing has never fired: every committed `review-plan` is `risk: "high"`, full battery, and the dominant first-pass trigger is `multi-module`.

The cause is the named-layout pattern. `_SRC_TREE_PATTERN` captured through the source-set segment, so `src/main/java` and `src/test/java` derived as two distinct modules. Under the TDD contract every behavioral change carries its test: the pipeline's own designed output is a prod+test pair, and that pair alone counted as scatter. A trigger that fires on 100% of designed output measures nothing. The reviewer battery is 25% of accounted delivery spend (v0.2.2 sweep); the first-pass narrowing path and the `review-planner` agent were dead code on any change the pipeline produces.

`multi-module` was designed to capture scatter across components — a change spanning two bounded contexts reads as wider risk. A component's main tree and its test tree are one component.

## Options Considered

1. **Drop the `multi-module` trigger.** Rejected: real cross-component scatter is a risk signal worth the full battery.
2. **Exclude test files from the module count.** Rejected: a test-only module id still matters — a change touching two modules' tests is still scatter. The defect is the id derivation, not the counting.
3. **Fix the derivation: the module id is the module root, not the source set** (chosen). The capture group ends at `src`, so `src/main/java/**` and `src/test/java/**` both derive `src` (`app/src` in a multi-module tree). Real Gradle/Maven modules stay distinct; the prod/test pair unifies. Consumers using `from = "gradle"` / `from = "maven"` inherit the fix with no `layout.toml` edit; an explicit `regex:` rule is untouched.

## Decision

**The `gradle`/`maven` named module layouts derive the module root: the path prefix ending at `src/`, with the source-set segment normalized away. A prod file and its test derive the same module id; `multi-module` fires only on genuine cross-module scatter.**

## Consequences

- A single-module change with its tests can reach the surface-matched subset on a first pass, or the gray zone. There a small, clean production change defers to the `review-planner` as designed.
- The fail-closed guards stand unchanged: oversize (over `size_threshold` prod+test lines), sensitive paths, unclassifiable files, a noisy slice history, and the unrun-engine fallback all still buy the full battery. The floor is never subtracted; a plan only narrows which floor reviewers a pass dispatches.
- Expected effect, measured by a dev sweep against the prior tag: reviewer dispatches drop on small clean slices; the bar and the judge facets hold. A facet drop alongside the roster drop reads as narrowing bought too cheaply and reopens this decision.
- Recorded eval rows keep their meaning: each manifest pins its version, and a trend delta across this boundary measures the classifier change.
- Semver: fix (patch). No surface removed or renamed; the trigger's documented intent — scatter — is restored.

## Implementation

- `harness/core/scripts/grading/config.py` — `_SRC_TREE_PATTERN` captures the module root; the table comment carries the pair rationale.
- `harness/core/scripts/tests/grading/test_features.py` — module-root pins, plus the pair pin: a prod file and its test derive one id, distinct module prefixes stay distinct.
- `harness/stacks/java-spring-boot/scripts/tests/grading/test_features_layout.py` and `harness/stacks/go/scripts/tests/grading/test_features_layout.py` — layout pins updated to the module root.
- `harness/init/stacks/*/scripts/layout.toml` — the named-layout comment states the module root; skeleton `[[module]]` globs unchanged.
- [ADR 2026-07-17 module-derivation named layouts](2026-07-17-module-derivation-named-layouts.md) — the sugar contract (name expands to `regex:`) is unchanged; this ADR supersedes its source-set-root id.

## References

- [Module derivation: named layouts](2026-07-17-module-derivation-named-layouts.md) — the sugar table this decision re-points.
- [Eval bench: cost per pass](2026-08-02-eval-bench-cost-per-pass.md) — the measurement frame the expected effect is judged in.
