# Module Derivation: Named Layouts over a Regex Primitive

**Status:** Accepted — the module-id derivation is superseded by [A Prod/Test Pair Is One Module](2026-08-10-a-prod-test-pair-is-one-module.md); the sugar contract stands

## Context

grading.features shipped three module-derivation strategies. Two were pure path mechanics: `dir` and `first-segment-after:<prefix>`. The third, `maven`, hardcoded the Gradle/Maven source-set regex `(.*?/src/(?:main|test)/[^/]+)/` in engine code — the one build-system fact wired into the engine's matching logic. Purging the name outright was considered: it removes the token but forces consumers to paste a regex where one readable word served, and breaks released `from = "maven"` configs. The maintainer's call: consumer readability and compatibility outrank token purity.

## Options Considered

1. **Keep `maven` as engine code** — rejected: the derivation pattern stays welded into a match branch; the next layout means another engine branch.
2. **Only a generic `regex:<pattern>` primitive, drop the names** — rejected: consumers paste an opaque regex for the common case; released `maven` configs break at load.
3. **A regex primitive plus a curated named-layout table** (chosen) — the engine implements the mechanism; names are data that expand to it. Readable config, no breaking change.

## Decision

**Module derivation is three path primitives — `dir`, `first-segment-after:<prefix>`, `regex:<pattern>` — plus a curated table of named layouts (`NAMED_MODULE_LAYOUTS`) that expand to the regex primitive.**

- `regex:<pattern>`: group 1 of the match is the module id; a non-matching path falls back to the file's parent directory. Validation requires the pattern to compile and to capture a group, failing loudly at load.
- A named layout is pure sugar: `from = "gradle"` behaves exactly as `from = "regex:<its pattern>"` — same match, same fallback. The equivalence is test-pinned in core (TestNamedModuleLayouts).
- The table ships two names for one pattern: `maven` and `gradle` alias the source-set root derivation, since both build systems share the `src/<set>/<lang>` convention. The Java/Spring Boot skeleton writes `from = "gradle"`; a consumer's released `from = "maven"` keeps working.
- Build-system knowledge lives only in the table's data, never in matching logic. A future stack with a common shape adds one table line, not an engine branch.
- Each table pattern must itself satisfy the regex-primitive contract, test-enforced over the table — a broken curated pattern fails in core tests, not in a consumer's diff loop.

## Consequences

- Positive: readable config for the common case; the generic primitive covers every other shape; no breaking change for released configs; a new layout is one data line.
- Negative: core carries build-system names as data — accepted deliberately; the core stack-token gate does not police the table.

## References

- [The Shipped Runtime Becomes Domain Packages Under a Composition Root](2026-07-17-runtime-package-layout.md) — the test-homing rule the core-pinned equivalence tests follow.
- [A Typed, Checker-Enforced Standard for the Harness Python Core](2026-07-17-typed-python-core.md) — the validation-at-load posture the named forms join.
