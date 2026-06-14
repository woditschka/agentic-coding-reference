# Layout-Sourced Schema Patterns via `patternFrom`

**Status:** Accepted

## Context

The harness is preparing the `marketplace` plugin channel. Before a schema becomes part of a published plugin interface, duplicated facts inside it should collapse to one source — changing them later is breaking.

The test-name shape lived in two places and had already drifted. `prd-entry.schema.json` enforced it as `test_names.items.pattern` (Go: `^Test[A-Z][A-Za-z0-9_]*$`); `layout.toml` carried `test_name_pattern` (the floor `^Test[A-Z]`). The handoff validator read the schema; other engines read the layout. The spec already names `layout.toml` the home for facts engines consume, so the schema duplicating one is an open-coded second source.

## Decision

**Schemas defer a pattern to project data via a `patternFrom` keyword.**

- **`patternFrom` sources a pattern from `layout.toml`.** A schema node carrying `patternFrom: "<key>"` resolves `<key>` from `layout.toml` and validates as if that value were its `pattern`. `handoff.py` owns the resolution: the keyword joins the supported vocabulary, the node keeps `patternFrom` (documenting the dependency) and gains a `pattern` when the key resolves. Both `prd-entry` schemas now use it; the hard-coded regex is gone.
- **Absence never blocks.** A missing `layout.toml` or unset key leaves the node without a pattern, so the shape check is skipped rather than failing — consistent with the optional-source rule.

## Consequences

**Positive:**
- The test-name shape has one source. Drift between schema and layout is now structurally impossible — the schema reads the layout value.
- `patternFrom` extends to any schema fact an engine also reads: it defers to `layout.toml` the same way, so the mechanism is not specific to test names.

**Negative:**
- Go's handoff-time test-name check loosens from the schema's full-match grammar to the layout floor `^Test[A-Z]` (a prefix match). Accepted: the floor is the declared single source, and the test framework validates real names at runtime; the handoff check is a shape gate, not a grammar. Java's floor already equalled its old schema regex, so it is unchanged.
- `handoff.py` now requires Python 3.11+ (`tomllib`) to read `layout.toml`. The doctor already required it, so the floor is unchanged in practice.

## Notes

A prerequisite for the marketplace channel, paired with [the decoupled artifact version](2026-06-14-decoupled-artifact-version.md). One latent issue remains for the plugin channel: `handoff.py` resolves `--layout` cwd-relative, which holds when the runtime is materialized into the project but must be anchored to the project root once the runtime ships inside a plugin.
