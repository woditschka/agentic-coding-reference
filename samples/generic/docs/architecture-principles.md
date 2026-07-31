<!-- harness: 2026-06-26 -->
# Architecture Principles

This document carries the tactical pattern catalog this project builds with. It specializes the strategic properties the harness works from — one canonical vocabulary, bounded modules, an isolated unit-testable domain core, and the state-vs-history document split.

**This brief is the single surface for adapting the architecture style**, and it has two layers. The **closed properties** under *Domain Core* are the kernel every brief realizes but does not rewrite. The **open pattern catalog** below them ships an opinionated default the project is free to adapt. The `design-validation` skill reads this file and enforces it as written — it holds no competing copy, so changing a pattern here changes what is enforced.

## Design Principles

The high-level laws designs are evaluated against. The `design-validation` skill enforces them at triage. Rewrite the list to fit this project; keep it short and enforceable.

1. **Security and reliability are emergent** — must be designed in, not retrofitted.
2. **Consistency over novelty** — match existing patterns unless there is a compelling reason.
3. **Explicit dependencies** — every integration point documented.
4. **Layer respect** — features belong in appropriate architectural layers.
5. **Minimal surface** — prefer module-internal visibility.
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

These properties are **closed**: adapt the *how* in the Pattern Catalog, not these.

| Property | Rationale |
|----------|-----------|
| Domain objects are immutable; collections use defensive copies; no setters | Eliminates shared-mutable-state bugs; safe to pass between pipeline steps without synchronization |
| Invariants are enforced when a domain object is first constructed; rebuilding one from stored state restores an already-valid instance | The domain is valid by construction, and only valid states are ever persisted |
| The domain core holds no infrastructure logic — no I/O, queries, transactions, or DI wiring | The same model runs under any infrastructure; swap the store and the domain is unchanged |
| Aggregates are the consistency boundary: outside code enters only through the root, and aggregates reference each other by identity | Invariants enforced in one place; boundaries stay boundaries |
| Anti-corruption guards every boundary the project does not control; infrastructure mechanics never dictate domain shape | The domain is the fixed point; infrastructure is a swappable boundary |
| Configuration is typed and immutable, validated at startup | Fail fast on invalid configuration; no hidden defaults buried in code |
| Errors flow outward; each layer wraps with context; log only at boundaries | Callers decide handling; no double-logging; per-item failure never aborts a batch |

## Pattern Catalog

The tactical patterns in force in this project — the harness's **opinionated default**, and **open** to adapt. Replace a pattern only with one that still realizes the closed properties above.

| Pattern | Rule | Realizes |
|---------|------|----------|
| **Value object** | Immutable data defined by its attributes; equality by value; no identity | Cheap real objects for tests; no shared mutable state |
| **Aggregate** | Root owns the consistency boundary for its children; outside code enters only through the root | Invariants enforced in one place |
| **Repository** | Persistence gateway, one per aggregate root; the default persistence boundary | The core never touches I/O directly |
| **Domain service** | Stateless; business logic that belongs to no single entity | Logic stays in the testable core |
| **Application service** | Thin; sequences the use case and owns the transaction boundary; no business logic | Orchestration never absorbs the core; one place opens and closes the transaction |
| **Anti-corruption mapper** | A single pure function taking the source values as arguments and returning the mapped object, or an error / fallback; imports no foreign type | A foreign-format change touches one mapper, never the domain |

### Persistence and boundary mapping

Persistence is a spectrum; choose per project, and the domain core is identical across all of them:

1. **Event-sourced / in-memory** — the model object graph is materialized by folding an event stream (e.g. a log or broker), with no other persistence layer. A relational store is equally valid; neither is privileged.
2. **Repository with an anti-corruption mapper** — the default when the store's shape diverges from the model.
3. **Direct mapping** — when the project **owns both ends** and persistence **follows the model closely**, the model may carry persistence or serialization mapping metadata directly. This is the sanctioned substitute for a hand-written mapper at that controlled boundary — compliant, not a missing anti-corruption layer.

Direct mapping has two gates: the project owns both ends, **and** the stored shape tracks the model closely enough that a separate mapper would be pure boilerplate. Otherwise keep a separate persistence model behind a mapper. Anti-corruption is mandatory only at boundaries the project does **not** control — external APIs, foreign schemas, another system's events.

## Naming

Names come from the project's canonical vocabulary (`ubiquitous-language.md`): if the PRD calls it a "feed item", the code says `FeedItem`, never `Entry` or `Record`.

| Concept | Rule |
|---------|------|
| Value objects, aggregates | Domain noun, no suffix |
| Repositories | Suffix `Repository`, one per aggregate root |
| Domain services | Verb or action name, stateless |
| Anti-corruption mappers | `from{Source}()` / `to{Target}()`, static, pure; source values in, mapped object or fallback out |
| Configuration | Suffix `Properties` or `Config`, immutable after construction |

**Prohibited suffixes:** `Manager`, `Helper`, `Utility`, `Handler`, `Processor`, `Base`, `Info`, `Data` (as a type suffix). These names are vague, attract unrelated responsibilities, and grow into god objects. Use specific domain nouns and verbs instead.

## Design Validation Checklist

Before approving a design, verify:

- [ ] Placement follows the module structure; no reach into another module's internals
- [ ] No circular dependencies introduced; the modularity test passes
- [ ] New types follow the naming rules; no prohibited suffixes
- [ ] Value objects immutable and equal by value; aggregates enforce invariants at construction, entered only through the root, referenced by identity
- [ ] Anti-corruption guards every boundary the project does not control; an owned, closely-tracked model may be mapped directly
- [ ] Persistence/serialization choices follow this brief's catalog; the domain core holds no infrastructure logic
- [ ] Domain logic testable without framework context; real objects usable in tests
- [ ] New dependencies justified against the dependency policy
- [ ] Terms match the canonical vocabulary
