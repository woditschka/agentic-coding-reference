# Module Derivation: Named Layouts Expand to a Regex Primitive

**Status:** Accepted

## Context

The change grader derives a module id for each changed file from a `[[module]]` rule in `layout.toml`. `multi-module` is one of its risk triggers: a change spanning two components reads as wider risk and buys the full reviewer battery.

The derivation shipped three strategies. Two were pure path mechanics, `dir` and `first-segment-after:<prefix>`. The third, `maven`, hardcoded the Gradle/Maven source-set regex in engine code, the one build-system fact wired into matching logic. Purging the name would force consumers to paste a regex where one readable word served and break released `from = "maven"` configs.

Its pattern captured through the source-set segment, so `src/main/java` and `src/test/java` derived as two modules. Under the TDD contract every behavioral change carries its test, so the pipeline's own designed output counted as scatter. Every committed `review-plan` in the recorded eval series was `risk: "high"` with `multi-module` the dominant first-pass trigger. The reviewer battery was 25% of accounted delivery spend in the v0.2.2 sweep, and the first-pass narrowing path shipped in v0.1.21 had never fired.

## Options Considered

1. **Keep `maven` as engine code.** Rejected: the next layout means another engine branch.
2. **Only a generic `regex:<pattern>` primitive, no names.** Rejected: an opaque regex for the common case, and released `maven` configs break at load.
3. **Drop the `multi-module` trigger.** Rejected: cross-component scatter is a risk signal worth the full battery.
4. **Exclude test files from the module count.** Rejected: a change touching two modules' tests is still scatter; the defect was the id derivation, not the counting.
5. **A regex primitive plus a curated named-layout table deriving the module root** (chosen).

## Decision

**Module derivation is three path primitives plus a curated table of named layouts that expand to the regex primitive.** The `gradle` and `maven` names derive the module root. A production file and its test therefore share one module id.

- The primitives are `dir`, `first-segment-after:<prefix>`, and `regex:<pattern>`. For `regex:`, group 1 of the match is the module id; a non-matching path falls back to the file's parent directory. The pattern must compile and capture a group, failing at load otherwise.
- A named layout is pure sugar: `from = "gradle"` behaves exactly as `from = "regex:<its pattern>"`, same match, same fallback. The equivalence is test-pinned in core.
- `maven` and `gradle` alias one pattern, `((?:.*?/)?src)/(?:main|test)/[^/]+/`, whose capture ends at `src`. `src/main/java/**` and `src/test/java/**` both derive `src` (`app/src` in a multi-module tree); distinct module prefixes stay distinct. The Java/Spring Boot skeleton writes `from = "gradle"`; a released `from = "maven"` keeps working and inherits the module-root fix without a `layout.toml` edit. An explicit `regex:` rule is untouched.
- Build-system knowledge lives only in the table's data, never in matching logic. A new layout is one table line, and each table pattern must satisfy the primitive contract, test-enforced over the table.
- `multi-module` fires only on cross-module scatter. The fail-closed guards stand: oversize, sensitive paths, unclassifiable files, a noisy slice history, and the unrun-engine fallback all still buy the full battery. The floor is never subtracted; a plan only narrows which floor reviewers a pass dispatches.

## Consequences

**Positive:**
- Readable config for the common case, the generic primitive for every other shape, and no breaking change for released configs.
- A single-module change with its tests can reach the surface-matched subset on a first pass, or defer to the `review-planner` in the gray zone as designed.
- Recorded eval rows keep their meaning: each manifest pins its version, and a trend delta across the v0.2.4 boundary measures the classifier change.

**Negative:**
- Core carries build-system names as data; the core stack-token gate does not police the table.
- A facet drop in the judge alongside the reviewer-roster drop reads as narrowing bought too cheaply and reopens the module-root derivation.

## Implementation

`NAMED_MODULE_LAYOUTS` and `_SRC_TREE_PATTERN` in `harness/core/scripts/grading/config.py`; the primitive, equivalence, and prod/test-pair pins in `harness/core/scripts/tests/grading/test_features.py`; the per-stack layout pins in `harness/stacks/{go,java-spring-boot}/scripts/tests/grading/test_features_layout.py`; the `[[module]]` rules and their module-root comment in `harness/init/stacks/*/scripts/layout.toml`.

## References

- [2026-06-05-the-change-grader](2026-06-05-the-change-grader.md) — the grader whose `review-plan` reads the module id and the `multi-module` trigger.
- [2026-06-18-the-reviewer-roster](2026-06-18-the-reviewer-roster.md) — the surface-matched subset and the `review-planner` the narrowing dispatches to.
- [2026-06-14-layout-declares-the-project](2026-06-14-layout-declares-the-project.md) — `layout.toml` as the home of the `[[module]]` rules the grader consumes.
- [2026-07-06-the-python-core](2026-07-06-the-python-core.md) — the validation-at-load posture and the test-homing rule the pins follow.
- [2026-07-15-the-eval-bench](2026-07-15-the-eval-bench.md) — the measurement frame for the reviewer-dispatch effect.
- [2026-09-13-product-workspace-with-member-modules](2026-09-13-product-workspace-with-member-modules.md) — member modules, the derivation's workspace extension.
