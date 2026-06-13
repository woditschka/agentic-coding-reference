# Domain-Driven Design Principles

This handbook document explains the strategic Domain-Driven Design (DDD) layer the harness is built on. It is harness-owned: its method ships dissolved into the runtime's skills and personas (e.g. `design-validation`, the system-design-expert), never as a committed project document. The tactical patterns that realize it are project-owned and live in each project's `docs/architecture-principles.md` brief; the default catalog ships as a doctor template.

## Why DDD for Agentic Coding

AI coding agents generate better code when domain boundaries are explicit. Without clear boundaries, agents mix concerns: persistence logic leaks into domain objects, framework annotations invade value types, and data mapping gets inlined wherever it's convenient. DDD gives agents a structural vocabulary: when an agent sees "Value Object" in a brief, it knows — immutable, no framework dependencies, equality by value. No guessing.

The harness is DDD-entangled by design, not by preference. Module identity drives triage and blast-radius computation (`layout.toml` module derivation). Term resolution drives the requirements interview. The isolated domain core is what makes TDD-first achievable. Strategic DDD is therefore kernel, alongside TDD, the spec-driven delivery loop, and the form contract.

## The Four Kernel Properties

Every project running the harness holds these four properties. The harness machinery depends on them; a project may rewrite every pattern in its briefs, but not the properties the patterns realize.

| Property | What it fixes | Where the harness depends on it |
|----------|---------------|--------------------------------|
| **Ubiquitous language** | One canonical vocabulary shared by stakeholders, docs, and code | `docs/ubiquitous-language.md` is roster-required; term-drift is challenged at triage and review |
| **Bounded modules** | The unit of architecture is a module with a public API and hidden internals | Module identity feeds triage, blast radius, and the scatter count in change grading |
| **Isolated unit-testable domain core** | Business logic testable without infrastructure | The TDD inner loop assumes a core that real objects can exercise without framework context |
| **State-vs-history document split** | `system-design.md` carries current state; `adr/` carries the path to each decision | Triage checks slices against system-design for coverage; doc-review enforces the ADR back-link rule |

## Properties Are Kernel; Patterns Are Brief-Variable

Repositories, thin application services, anti-corruption mappers, aggregates — these are *realizations*. A team can reject the word "repository" and use a different persistence boundary; it cannot reject "the domain core is testable without infrastructure." The admission test for the kernel: a discipline enters only when the machinery breaks without it, not when we merely like it.

| Layer | Owner | Examples |
|-------|-------|----------|
| Strategic properties (this doc) | Harness kernel — closed | The four properties above |
| Tactical pattern catalog | Project brief (`docs/architecture-principles.md`) | Value objects, aggregates, repositories, domain services, data mappers, naming rules |
| Language realization | Project brief, language section | Java records with `List.copyOf()`; Go packages under `internal/` |

The default tactical catalog — immutability by default, zero framework dependencies in the core, stateless mappers at boundaries, the suffix rules — ships as the `architecture-principles` doctor template. A fresh project starts with it and owns it from the first materialization.

## Consumers

- The **system-design-expert** triages every slice against the project's module map and pattern brief; it enforces the brief's patterns as its own convictions and raises brief-defect findings when the brief contradicts itself or the codebase.
- The **feature-implementer** refactors toward the brief's discipline after each green test.
- The **doctor** verifies the roster carries `architecture-principles.md` and `ubiquitous-language.md`; **brief-review** judges whether the brief's patterns still realize the four properties.
