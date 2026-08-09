# Gate Facts Declare Once in layout.toml; Build Schemas Defer via enumFrom

**Status:** Accepted

## Context

The build-pass and build-failure schemas existed as six hand-owned files — two per stack — byte-identical except two data slots: the gate command inside a description and the gate-verb enum. The shared routing core parses every stack's records into one dataclass model, so structural identity is forced by contract; a comment in the routing core even instructed "change all of them together." The gate command itself was restated across 5–16 prose sites per stack with no declared home. The 2026-08-02 review confirmed both findings (the prose-restatement half is dispositioned in the 2026-08-09 amendment below); the parity-gates ADR's identity test routes contract-identical copies to derivation, not gating.

## Options Considered

1. **Render the six files at propagate time from a template plus per-stack facts.** Rejected: adds a render path for two files when a resolution mechanism already ships — and a rendered enum is still frozen per install, not project-tunable.
2. **A cross-stack structural parity battery check.** Rejected as primary: polices drift instead of removing the channel; kept only as the construction check below.
3. **One core schema pair deferring to project data via `enumFrom`** (chosen), extending the `patternFrom` precedent (ADR 2026-06-14).

## Decision

**The gate's facts — command and verb vocabulary — declare once per project in `layout.toml [gate]`; one core build-pass/build-failure schema pair defers to them.** The validator gains `enumFrom`, the exact sibling of `patternFrom`: a node carrying it validates against the layout value when the key resolves to a non-empty string list, and stays unconstrained otherwise — absence never blocks. The six stack schema copies are deleted; the init skeletons and samples declare `[gate]` per stack. The battery now checks the construction (both core nodes defer to `gate.verbs`) and each skeleton's declaration (non-empty verbs, non-empty command) instead of comparing six enums. `spec_version` advances to 0.2.0: `[gate]` is an optional documented key, additive with shipped defaults.

## Consequences

- A gate-verb change is one layout edit; schema drift across stacks is impossible by construction, and consumers can extend their gate vocabulary without touching harness-owned files.
- A project without `[gate]` loses the verb-vocabulary shape check until it declares one — the optional-source rule, matching `patternFrom`.
- The spec bump makes every consumer's doctor flag the version mismatch until re-materialize restamps it (the 2026-08-02 deterministic restamp).

## Implementation

`harness/core/schemas/scratch/build-{pass,failure}.schema.json`, `apply_layout_sources` in `handoff/schema.py`, `[gate]` in `harness/init/stacks/*/scripts/layout.toml` and the samples, the reworked battery check in `verify_harness/checks/sync.py`.

## References

- [Layout-Sourced Schema Patterns via patternFrom](2026-06-14-layout-sourced-schema-patterns.md) — the mechanism this extends, keyword for keyword.
- [Roster and Vocabulary Gates for Hand-Owned Parallel Files](2026-07-12-parity-gates-for-hand-owned-parallels.md) — its identity test routes these contract-identical copies here, not to its gates.
- [Rendered Agent Mirror Bodies](2026-07-03-rendered-agent-mirror-bodies.md) — the derivation precedent for contract-identical copies.

## Amendment (2026-08-09): Prose Restatement Is Deliberate

The gate command also appears in the prose homes the audit's root-doc-and-quality-gate-alignment check gates: the consumer `CLAUDE.md` Quality Gate chapter, the `code-quality-gate` skill, and the reviewer's permitted commands. That restatement stays. Agents read those surfaces at the point of use; a pointer into `layout.toml` would trade one read for two on every gate run. `layout.toml [gate]` remains the single *declared* home — schemas and engines read only it. Prose agreement is checked by judgment (that same audit check), never by the battery.
