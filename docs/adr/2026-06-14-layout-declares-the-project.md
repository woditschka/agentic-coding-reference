# layout.toml Declares the Project; Engines and Schemas Read It

**Status:** Accepted

## Context

The spec names `scripts/layout.toml` as the home for the facts engines consume. Before a schema joins a published plugin interface, every fact it duplicates must collapse to one source, because changing a published schema later is breaking.

Two duplications had already drifted. The test-name shape lived in `prd-entry.schema.json` as a full-match regex and in `layout.toml` as the floor `^Test[A-Z]`; the handoff validator read one, the other engines read the other. The build-pass and build-failure schemas existed as six hand-owned files, two per stack, byte-identical except the gate command and the gate-verb enum. The shared routing core parses every stack's records into one dataclass model, so structural identity is forced by contract.

The binding surface between the stack-agnostic pipeline and a concrete technology was implicit. The `go` and `java-spring-boot` stacks bound each quality-gate check to a command in prose, duplicated in `CLAUDE.md`. Adding a third technology meant reverse-engineering a working sample. The inner TDD loop asks a stack for one thing: run the tests.

## Options Considered

1. **Keep the regex and the enums inside the schemas.** Rejected: a second open-coded source of a fact `layout.toml` already declares; drift had already happened.
2. **Render the six build schemas at propagate time from a template plus per-stack facts.** Rejected: a resolution mechanism already ships, and a rendered enum stays frozen per install.
3. **A cross-stack structural parity check on the schema copies.** Rejected as primary: polices drift instead of removing the channel; kept only as the construction check.
4. **A documentation-only generic stack with `{{FILL}}` command tables.** Rejected: the verb surface stays split across the gate skill and `CLAUDE.md`, and "agents speak verbs" stays aspirational.
5. **A TOML verb-to-command manifest plus a resolution engine.** Rejected: a flat map cannot express multi-step or conditional gates, and retrofitting would touch the opinionated stacks.
6. **Point the prose homes at `layout.toml` instead of restating the gate command.** Rejected: agents read those surfaces at the point of use; a pointer doubles the reads per gate run.

## Decision

**`layout.toml` is the single declared home for every fact an engine or schema consumes; schemas defer to it by keyword, and the generic stack binds through one project-owned verb script.**

- **`patternFrom`.** A schema node carrying `patternFrom: "<key>"` validates as if the `layout.toml` value were its `pattern`. The `prd-entry` schema's `test_names` items defer to `test_name_pattern`.
- **`enumFrom`.** Its exact sibling: a node validates against the layout value when the key resolves to a non-empty string list. One core build-pass/build-failure schema pair defers to `gate.verbs`; the six stack copies are gone.
- **Absence never blocks.** A missing `layout.toml` or unset key leaves the node unconstrained, so the shape check is skipped. `[gate]` is an optional documented key with shipped defaults; `spec_version` is 0.2.0.
- **`[gate]` declares the gate's facts once per project:** the command and the verb vocabulary. The init skeletons and the samples declare it per stack. The consumer `CLAUDE.md` Quality Gate chapter, the `code-quality-gate` skill, and the reviewer's permitted commands restate the command on purpose. Schemas and engines read only the layout; the audit checks prose agreement by judgment, never the battery.
- **The generic stack's verb contract.** `scripts/gate.sh` (harness-owned, replaced on upgrade) defines the verbs `deps, format, lint, test, build`, their gate order, the aggregate `verify`, and the fail-honest rule. An unbound verb prints "not implemented yet" and returns non-zero. `scripts/stack.sh` (project-owned, scaffolded by `init`, never overwritten) holds the verb bodies. No harness file in the generic stack names a build tool; a missing `stack.sh` fails; only a deliberately unneeded verb is an explicit `return 0`.
- **Generic is the fallback, never a shadow.** `init` and `materialize` resolve an unrecognized build marker to `generic`; a recognized marker always wins. The `go` and `java-spring-boot` stacks keep their command-based gates unchanged; the dispatcher lives in the generic stack layer, not `core/`.
- **Structurally complete, content fill-in.** The generic stack scaffolds the full brief roster and review skills as language-agnostic templates with `{{FILL}}` slots. The doctor passes on structure; content depth is advisory through `audit-docs`.

## Consequences

**Positive:**
- A gate-verb change is one layout edit; schema drift across stacks is impossible by construction, and a consumer extends its gate vocabulary without touching harness-owned files.
- Supporting a new technology drops to filling the verb functions in one file, checked by `test-generic-stack.sh`.
- Any project without a bespoke stack adopts the pipeline on either channel: copy `samples/generic/` or install the `agent-team-generic` plugin.

**Negative:**
- Go's handoff-time test-name check loosened from a full-match grammar to the layout floor `^Test[A-Z]`; the test framework validates real names at runtime. Java's floor already equalled its schema regex.
- A project without `[gate]` loses the verb-vocabulary shape check until it declares one.
- The generic stack gates by script dispatch while the opinionated stacks gate by prose commands; the three are not uniform.
- The generic review skills carry language-agnostic principles, not a per-language checklist, until the adopter enriches them.
- The validator requires Python 3.11+ (`tomllib`); the doctor already required it.

## Implementation

`with_layout_sources` in `harness/core/scripts/handoff/schema.py` resolves both keywords through `layout_pattern` and `layout_enum`. `harness/core/schemas/scratch/prd-entry.schema.json` carries `patternFrom`; `harness/core/schemas/scratch/build-{pass,failure}.schema.json` carry `enumFrom`. `[gate]` lives in `harness/init/stacks/*/scripts/layout.toml` and the samples. The verb contract is `harness/stacks/generic/scripts/gate.sh` and `harness/init/stacks/generic/scripts/stack.sh`, tested by `harness/tests/test-generic-stack.sh`. `harness/verify_harness/checks/sync.py` checks that both core nodes defer to `gate.verbs` and that each skeleton declares non-empty verbs and command.

## References

- [2026-06-14-distribution-channels](2026-06-14-distribution-channels.md) — the `[harness] channel` key `layout.toml` also declares, and the plugin set the generic stack joined.
- [2026-06-11-materialize](2026-06-11-materialize.md) — the stack detection whose terminal branch is `generic`.
- [2026-06-14-the-doctor](2026-06-14-the-doctor.md) — passes the generic stack on structure and reads the channel invariants from the layout.
- [2026-06-12-docs-as-harness-project-api](2026-06-12-docs-as-harness-project-api.md) — the `spec_version` contract the `[gate]` key advanced.
- [2026-07-02-deterministic-routing-engines](2026-07-02-deterministic-routing-engines.md) — the validator that applies the layout-sourced keywords to every record.
- [2026-07-17-module-derivation](2026-07-17-module-derivation.md) — another layout-declared fact: the `[[module]]` derivation the grader reads.
- [2026-09-13-product-workspace-with-member-modules](2026-09-13-product-workspace-with-member-modules.md) — the umbrella's `layout.toml` declares its members the same way.
- [Harness project API](../harness-project-api.md) — the contract that names `layout.toml` the home of engine-consumed facts.
