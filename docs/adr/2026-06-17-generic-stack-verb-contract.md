# Generic Stack: a Lifecycle-Verb Contract as the Single Binding Surface

**Status:** Accepted

## Context

The harness shipped two opinionated stacks — `go` and `java-spring-boot`. Adding a third meant studying an existing sample and inferring which parts were essential versus incidental. The variable surface was wide: the quality-gate commands, the file-classification globs, the language clauses in the review skills, the reviewer command lists. The binding surface between the stack-agnostic pipeline and a concrete technology was real but implicit, so the cost of supporting a new technology was "reverse-engineer a working stack."

Two facts shaped the design. First, the inner TDD loop is already stack-agnostic; the only thing it asks of a stack is "run the tests." Second, the quality gate is the actual verb surface. `code-quality-gate` bound each abstract check (tidy, format, lint, test, build) to a concrete command in prose, duplicated in `CLAUDE.md`. The coordinator ran the gate by reading that prose. There was no command-resolution layer; agents named tools directly (`go test`, `make ci`, `./gradlew`), so "the pipeline is stack-agnostic" held only because each stack re-stated the commands.

## Options Considered

1. **Documentation-only template.** A `stacks/generic/` skeleton mirroring go/java with `{{FILL}}` placeholders in the command tables. Faithful to existing structure, but the verb surface stays split across the gate skill and `CLAUDE.md`, and "agents speak verbs, not tools" remains aspirational.
2. **A TOML verb→command manifest plus a resolution engine.** Most "self-describing," but a flat map cannot express what real gates do (`make ci`, multi-step sequences, conditional checks), and retrofitting go/java onto it would touch the opinionated stacks.
3. **A single project-owned verb script behind a harness-owned dispatcher.** One shell file of verb functions the owner fills in; a harness-owned dispatcher defines the verb list, run order, and the fail-honest rule. Shell functions hold arbitrary command sequences, so real gates fit. This mirrors the existing `score-change.py` (engine, harness-owned) / `layout.toml` (data, project-owned) split.

## Decision

**Add a `generic` stack whose single binding surface is a lifecycle-verb contract: a harness-owned dispatcher plus a project-owned verb script. The opinionated stacks are not changed; generic is the fallback when no stack marker is recognized.**

- **The verb contract.** `scripts/gate.sh` (harness-owned, materialized, replaced on upgrade) defines the canonical verbs — `deps, format, lint, test, build` — their gate order, the aggregate `verify`, and the rule that an unimplemented verb fails. `scripts/stack.sh` (project-owned, scaffolded by `/init`, never overwritten) holds the verb function bodies. The project owner fills only `stack.sh`.
- **Verbs, never tool names.** The `code-quality-gate` skill, `CLAUDE.md`, and the agents call `scripts/gate.sh <verb>`. No harness file in the generic stack names a build tool. That indirection makes "the pipeline drives any technology unchanged" a real, enforced property, checked by `test-generic-stack.sh`.
- **Fail honestly.** An unbound verb prints "not implemented yet" and returns non-zero; a missing `stack.sh` fails; only a verb a stack deliberately does not need is an explicit `return 0` no-op. A half-adapted stack cannot pass a gate it has not satisfied.
- **Structurally complete, content fill-in.** The generic stack scaffolds the full `docs/` brief roster and review skills as language-agnostic, structurally complete templates with `{{FILL}}` slots. The doctor passes on structure immediately; content depth is the project's job (advisory, via `audit-docs`).
- **Detection falls back to generic.** `bootstrap.sh`, `/init`, and `/materialize` resolve an unrecognized marker to `generic` rather than stopping. The fallback is the terminal branch: a recognized marker always wins, so `generic` never shadows an opinionated stack, and a new opinionated stack is added exactly as go and java were — a `stacks/<name>/` tree plus a marker rule above the fallback.
- **The opinionated stacks are untouched.** `go` and `java-spring-boot` keep their command-based gates byte-for-byte. The dispatcher lives in the generic stack layer, not `core/`, so nothing new ships into the opinionated stacks.
- **Materialized alongside the others.** The generic stack ships as a committed sample (`samples/generic/`, re-materialized by `bootstrap.sh` and gated by `check-sync` like go and java) and as a per-tool plugin set (`generic × {claude, copilot, junie}`, rendered by `package-marketplace.sh`). The sample is a starting point to inspect and copy, not a working application: its verbs are unbound and its briefs carry `{{FILL}}` slots. This makes generic adoptable on either channel — copy the sample, or `claude plugin add` the plugin — uniformly with the opinionated stacks.

## Consequences

**Positive:**
- Supporting a new technology drops to "fill in the verb functions in one file," not "reverse-engineer a sample."
- The verbs-not-tools invariant is now machine-checked for the generic stack.
- The fallback means any project — TypeScript, Python, Rust, anything — can adopt the methodology without a bespoke stack.
- The opinionated stacks stay opinionated; nothing about them changes.

**Negative:**
- The generic stack uses a different gate mechanism (script dispatch) than the opinionated stacks (prose commands), so the three are not uniform. Accepted: uniformity would require retrofitting go/java, which the constraint forbids; the generic stack is explicitly a different kind of artifact.
- Its review skills carry language-agnostic principles, not a curated per-language checklist, until the adopter enriches them. Accepted: structure is complete and enforceable; depth is the adopter's to add.

## References

- The verb contract: `harness/stacks/generic/scripts/gate.sh` and `harness/init/stacks/generic/scripts/stack.sh`.
- The self-test: `harness/test-generic-stack.sh`, wired into `harness/check-sync.sh`.
- Mirrors the engine/data split established in [layout-sourced schema patterns](2026-06-14-layout-sourced-schema-patterns.md): a harness-owned engine (`gate.sh`) reads project-owned data (`stack.sh` verb bodies), exactly as `score-change.py` reads `layout.toml`.
