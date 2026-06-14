<!-- materialized by harness@0.1.0, template architecture-principles, spec 0.1.0 — this file is owned by the project -->
# Architecture Principles

This document carries the tactical pattern catalog this project builds with. It specializes the strategic properties the harness works from — one canonical vocabulary, bounded modules, an isolated unit-testable domain core, and the state-vs-history document split. The patterns below may be rewritten to fit this project; the properties they realize may not.

## Design Principles

The high-level laws designs are evaluated against. The `design-validation` skill enforces them at triage.

1. **Security and reliability are emergent** — must be designed in, not retrofitted.
2. **Consistency over novelty** — match existing patterns unless there is a compelling reason.
3. **Explicit dependencies** — every integration point documented.
4. **Layer respect** — features belong in appropriate architectural layers.
5. **Minimal surface** — prefer `internal/` packages.
6. **Understandable systems** — if it cannot be reasoned about, it cannot be secured.
7. **Fail secure** — errors leave the system in a safe state.

## Module Boundaries

The unit of architecture is the module: a bounded context with a public API and hidden internals.

| Rule | Rationale |
|------|-----------|
| Modules depend only on other modules' public APIs | Internal implementation changes don't cascade |
| No circular dependencies between modules | Keeps the dependency graph a hierarchy; cycles make modules un-reasonable in isolation |
| Each module owns its configuration | Prevents god-config; the module stays independently understandable |
| Cross-module orchestration lives in a dedicated service or the entry point | Modules stay independent of each other's execution order |

**Default shape: modulith.** A single deployable unit with enforced internal module boundaries. It provides the separation of microservices without network boundaries, deployment pipelines, or distributed consistency problems — costs that outweigh the benefits at single-team scale.

**Enforcement.** Module boundaries are verified at test time: a modularity test fails the build when a module reaches into another's internals or a dependency cycle appears. Boundaries are not advisory.

**Module = bounded context.** Each module typically maps to one bounded context. If two modules share domain types, decide explicitly: they are one context, or they are two contexts needing a translation layer between them.

## Domain Core

Business logic lives in the domain core, isolated from infrastructure and testable without it. Orchestration stays thin: services coordinate sequencing and error handling; the core decides. When logic leaks into orchestration, it stops being unit-testable in isolation — that is the failure signal.

| Rule | Rationale |
|------|-----------|
| Domain objects are immutable; collections use defensive copies; no setters | Eliminates shared-mutable-state bugs; safe to pass between pipeline steps without synchronization |
| Domain types carry zero framework dependencies | Portable, testable in isolation, independent of framework upgrades |
| Serialization, validation wiring, and DI configuration live outside the core | The core never changes because a framework did |
| Configuration is typed and immutable, validated at startup | Fail fast on invalid configuration; no hidden defaults buried in code |
| Errors flow outward; each layer wraps with context; log only at boundaries | Callers decide handling; no double-logging; per-item failure never aborts a batch |

## Pattern Catalog

The tactical patterns in force in this project. Each realizes a structural property; replace a pattern only with one that still realizes it.

| Pattern | Rule | Realizes |
|---------|------|----------|
| **Value object** | Immutable data defined by its attributes; equality by value; no identity | Cheap real objects for tests; no shared mutable state |
| **Aggregate** | Root container owning the consistency boundary for its children | Invariants enforced in one place |
| **Repository** | Persistence gateway; one per aggregate root | The persistence boundary: the core never touches I/O directly |
| **Domain service** | Stateless; business logic that belongs to no single entity | Logic stays in the testable core |
| **Application service** | Thin; sequencing and error handling only, no business logic | Orchestration never absorbs the core |
| **Data mapper** | Stateless pure function at every boundary crossing (file, JSON, network) | Anti-corruption: an external format change touches one mapper, never the domain |

## Naming

Names come from the project's canonical vocabulary (`ubiquitous-language.md`): if the PRD calls it a "feed item", the code says `FeedItem`, never `Entry` or `Record`.

| Concept | Rule |
|---------|------|
| Value objects, aggregates | Domain noun, no suffix |
| Repositories | Suffix `Repository`, one per aggregate root |
| Domain services | Verb or action name, stateless |
| Data mappers | `from{Source}()` / `to{Target}()`, static, pure |
| Configuration | Suffix `Properties` or `Config`, immutable after construction |

**Prohibited suffixes:** `Manager`, `Helper`, `Utility`, `Handler`, `Processor`, `Base`, `Info`, `Data` (as a type suffix). These names are vague, attract unrelated responsibilities, and grow into god objects. Use specific domain nouns and verbs instead.

## Design Validation Checklist

Before approving a design, verify:

- [ ] Placement follows the module structure; no reach into another module's internals
- [ ] No circular dependencies introduced; the modularity test passes
- [ ] New types follow the naming rules; no prohibited suffixes
- [ ] Value objects immutable, framework-free; aggregates enforce their own invariants
- [ ] Every boundary crossing goes through a stateless mapper
- [ ] Domain logic testable without framework context; real objects usable in tests
- [ ] New dependencies justified against the dependency policy
- [ ] Terms match the canonical vocabulary
