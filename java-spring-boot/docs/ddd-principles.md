# Domain-Driven Design Principles for Agentic Projects

This document defines the language-agnostic DDD principles that all implementations follow. Each project applies them with language-specific conventions in their own `docs/system-design.md`.

## Why DDD for Agentic Coding

AI coding agents generate better code when domain boundaries are explicit. Without clear boundaries, agents mix concerns: persistence logic leaks into domain objects, framework annotations invade value types, and data mapping gets inlined wherever it's convenient.

DDD gives agents a structural vocabulary. When an agent sees "Value Object" in the system-design.md naming conventions, it knows: immutable, no framework dependencies, equality by value. No guessing.

## Core Principles

### Immutability by Default

All domain objects are immutable. Collections use defensive copies. No setters, no mutable state.

| Rule | Rationale |
|------|-----------|
| Domain objects are immutable | Eliminates shared-mutable-state bugs |
| Collections use defensive copies | Prevents callers from modifying internal state |
| No setters | Mutation happens through new instances, not state changes |
| Thread-safe by construction | Immutable objects are safe to pass between pipeline steps without synchronization |

### Domain Objects Have Zero Framework Dependencies

Value objects in the domain model carry no framework annotations. No serialization annotations, no validation annotations, no DI annotations.

Serialization configuration lives in mappers, repositories, or configuration classes — not on the domain type itself.

| What | Where |
|------|-------|
| Domain type definition | `model/` package (framework-free) |
| Serialization config | Mapper or repository layer |
| Validation logic | Service layer or configuration layer |
| Framework wiring | Configuration or component layer |

This keeps domain objects portable, testable in isolation, and independent of framework upgrades.

### Stateless Data Mappers at Boundaries

All data crossing a boundary (file system, JSON, network, HTML) passes through a stateless mapper function. Mappers are pure functions: input in, output out, no side effects.

This is the anti-corruption layer. The domain model never depends on external formats. When an external format changes, one mapper changes — domain objects stay untouched.

## DDD Building Blocks

### Naming Conventions

| DDD Concept | What It Is | Rules |
|-------------|-----------|-------|
| **Value Object** | Immutable data defined by its attributes, not identity | No suffix. Named as a domain noun. Equality by value. |
| **Aggregate** | Root container for related value objects | No suffix. Owns the consistency boundary for its children. |
| **Repository** | Persistence gateway for an aggregate | Suffix: `Repository`. One per aggregate root. |
| **Domain Service** | Business logic that doesn't belong to a single entity | Named as verb or action. Stateless. |
| **Data Mapper** | Converts between external format and domain type | Named as `from{Source}()` / `to{Target}()`. Static. Pure. |
| **Configuration** | Typed application settings | Suffix: `Properties` or `Config`. Immutable after construction. |

### Prohibited Suffixes

Do not use: `Manager`, `Helper`, `Utility`, `Handler`, `Processor`, `Base`, `Info`, `Data` (as a type suffix).

These names are vague. They attract unrelated responsibilities and grow into god objects. Use specific domain nouns and verbs instead.

## Package Structure

Organize code by domain concept, not by technical layer.

### Structure Principles

| Principle | Rule |
|-----------|------|
| **Domain model isolation** | Domain types live in a dedicated package with zero external dependencies |
| **One aggregate per package** | Each aggregate and its value objects occupy a single package |
| **Dependency direction** | Dependencies flow inward: infrastructure → service → domain |
| **No circular dependencies** | If package A imports B, B must never import A |

### Typical Layout

```text
project-root/
├── model/              # Domain types (value objects, aggregates)
├── config/             # Configuration types and loading
├── {feature}/          # Feature-specific services, repositories, mappers
└── runner/             # Application entry point and wiring
```

The exact layout varies by language and framework. The principle holds: domain types are isolated and dependency-free.

## Modulith Architecture

For projects at the scale targeted by this reference (single-team, single-deployment), a modulith is the default architecture. A modulith is a single deployable unit with enforced internal module boundaries. It provides the structure of microservices without the operational overhead.

### Why Modulith

Microservices add network boundaries, deployment pipelines, and distributed consistency problems. For single-team projects, these costs outweigh the benefits. A modulith keeps deployment simple while enforcing the same separation of concerns — each module has a public API, hidden internals, and declared dependencies.

### Module Structure

Each top-level package under the application root is an application module. Modules communicate through their public API (types and services in the package root). Sub-packages are internal and inaccessible to other modules.

```text
com.example.project/
├── Application.java           # @Modulithic entry point
├── catalog/                   # Module: public API at package root
│   ├── CatalogService.java    #   Public — other modules can use
│   ├── CatalogEntry.java      #   Public — shared value object
│   └── internal/              #   Private — invisible to other modules
│       ├── CatalogParser.java
│       └── CatalogStore.java
├── inbox/                     # Module: independent domain
│   └── ...
└── index/                     # Module: independent domain
    └── ...
```

### Module Rules

| Rule | Rationale |
|------|-----------|
| Modules depend only on other modules' public APIs | Internal implementation changes don't cascade |
| No circular dependencies between modules | Build-time verification catches violations |
| Each module owns its configuration | `config/` sub-package within the module |
| Cross-module orchestration lives in a dedicated service or the application entry point | Keeps modules independent of each other's execution order |

### Orchestration

Cross-module workflows need a coordination point. This can be a dedicated orchestration service or the application entry point. The orchestration layer calls module APIs — it does not reach into module internals. Keep it thin: delegate domain logic to the modules, coordinate only sequencing and error handling.

### Verification

Module boundaries are enforced at test time. A modularity verification test checks that no module accesses another module's internals and that no circular dependencies exist. This test fails the build on violations — module boundaries are not advisory.

## Bounded Contexts

Within a modulith, bounded context principles still apply:

| Concept | Application |
|---------|-------------|
| **Ubiquitous language** | Use the same terms in code, tests, PRD, and system-design.md. If the PRD calls it a "feed item", the code uses `FeedItem`, not `Entry` or `Record`. |
| **Context boundary** | External systems (APIs, file formats, databases) are outside the context. All interaction goes through mappers. |
| **Aggregate boundaries** | Each aggregate enforces its own invariants. Cross-aggregate operations happen in domain services. |
| **Module = bounded context** | In a single-team modulith, each application module typically maps to one bounded context. If two modules share domain types, consider whether they are one context or need an anti-corruption layer. |

## Design Validation Checklist

Before approving a feature for implementation, validate DDD alignment:

### Architectural Fit
- [ ] Package placement follows existing module structure
- [ ] New types follow naming conventions (see table above)
- [ ] No circular dependencies between modules
- [ ] No access to another module's internal sub-packages
- [ ] No prohibited suffixes used
- [ ] New dependencies justified and from approved sources
- [ ] Modularity verification test passes

### Domain Integrity
- [ ] Value objects are immutable with no framework annotations
- [ ] Aggregates enforce their own invariants
- [ ] Repositories map to aggregate roots (one repository per aggregate)
- [ ] Data mappers are stateless and pure
- [ ] Configuration is typed and immutable after construction
- [ ] Ubiquitous language consistent across code, tests, and docs

### Boundary Hygiene
- [ ] External format changes cannot break domain types
- [ ] All boundary crossings go through mappers
- [ ] No serialization annotations on domain objects
- [ ] Error handling follows project patterns (see system-design.md)

### Testability
- [ ] Domain logic testable without framework context
- [ ] Real value objects used in tests (no mocks for domain types)
- [ ] Factory methods create domain objects for tests

## Error Handling Principles

| Principle | Rule |
|-----------|------|
| **Errors flow outward** | Domain logic returns errors to callers. Callers decide how to handle them. |
| **Wrap with context** | Each layer adds context when propagating errors. |
| **Fail per-item, not per-batch** | Processing multiple items continues on individual failure. |
| **Corrupted state triggers recovery** | Invalid state files or malformed data result in recovery, not crashes. |
| **Log at boundaries** | Log errors at the outermost layer that handles them. Do not log and rethrow. |

## Configuration as Typed Objects

Application configuration is a domain concern. Represent it with typed, immutable objects — not raw strings or maps.

| Rule | Rationale |
|------|-----------|
| One configuration type per concern | Prevents god-config objects |
| Immutable after construction | Configuration does not change at runtime |
| Validated at startup | Fail fast on invalid configuration |
| Default values explicit | No hidden defaults buried in code |

## How This Relates to Project-Level Docs

This document defines the principles. Each implementation applies them:

- **Go:** [`go/docs/system-design.md`](../go/docs/system-design.md) — Go interfaces for domain contracts, struct types for value objects, constructor functions for DI (no framework), dependency policy restricting external packages
- **Java Spring Boot:** [`java-spring-boot/docs/system-design.md`](../java-spring-boot/docs/system-design.md) — Java records for value objects, `@ConfigurationProperties` records for config, Spring `@Component` for services/repositories, DDD naming conventions table, fluent method chaining, modern Java idioms
