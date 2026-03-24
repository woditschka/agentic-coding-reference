# System Design Document: [Project Name]

<!--
  TEMPLATE GUIDANCE:

  This is a skeleton system design. Start a conversation with the system-design-expert agent
  to fill it in after the PRD is ready:

    Task(subagent_type="system-design-expert", prompt="Design the architecture for [feature]")

  This document describes HOW the system works: types, interfaces, algorithms, patterns.
  See docs/documentation.md for ownership rules.
-->

## 1. Architecture Overview

<!-- High-level description of the system architecture. Include an ASCII diagram if helpful. -->

### 1.1 Design Principles

| Principle | Rule | Rationale |
|-----------|------|-----------|
| **Immutability by default** | All domain objects are immutable Java records. Collections in records use defensive copies (`List.copyOf()`, `Map.copyOf()`). No setters, no mutable state. | Eliminates shared-mutable-state bugs. Records are thread-safe and safe to pass between pipeline steps. |
| **Stateless data mappers** | All data crossing a boundary (file system, JSON, network, HTML) passes through a stateless mapper function. Mappers are pure functions: input in, output out, no side effects. | Anti-corruption layer: domain model never depends on external formats. Mappers are trivially unit-testable. |
| **No annotations on domain records** | Value objects in `model/` have zero framework annotations (no Jackson, no Spring, no validation). Serialization configuration lives in the repository or mapper. | Domain records stay portable and framework-independent. |
| **Modern Java idioms** | Use current Java features: `record` for value objects, `var` for local type inference, `Stream` pipelines over `for`-loops, `Optional` over null checks, pattern matching over type casting, text blocks for multi-line strings. | Modern idioms reduce boilerplate and make intent explicit. |
| **Fluent method chaining** | Prefer chained fluent calls over imperative step-by-step mutation. Use Stream pipelines, `Optional` chains, builder patterns, and AssertJ chains for assertions. | Fluent chains read as a single declarative expression. Reduces intermediate variables and mutable state. |

**These principles apply equally to production code and test code.** Tests are first-class code: they use the same immutable records, streams, fluent chains, and modern Java idioms.

## 2. Tech Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Framework | Spring Boot | TBD | |
| Build tool | Gradle (Groovy DSL) | TBD | |
| Language | Java | TBD | |
| JSON | Jackson | *(via Spring Boot)* | |
| Logging | SLF4J + Logback | *(via Spring Boot)* | |
| Testing | JUnit 5 + AssertJ | *(via Spring Boot)* | |

## 3. Package Structure

This project uses Spring Modulith. Each top-level package is an application module with enforced boundaries. Types at the package root are the module's public API. Sub-packages (especially `internal/` and `config/`) are invisible to other modules.

```text
com.example.reference
├── ReferenceApplication.java           Main class (@SpringBootApplication, @Modulithic)
├── {module}/                           Application module (public API at root)
│   ├── {Module}Service.java            Public service
│   ├── {ValueObject}.java              Public domain type
│   ├── config/                         Module-private configuration
│   │   └── {Module}Properties.java     @ConfigurationProperties record
│   └── internal/                       Module-private implementation
│       └── ...
└── ...
```

Module boundaries are verified by `ModularityTests.java` which calls `ApplicationModules.of(...).verify()`. This test fails the build if any module accesses another module's internals or if circular dependencies exist.

### 3.1 Naming Conventions (DDD-Inspired)

| DDD Concept | Naming Convention | Implementation | Suffix | Examples |
|-------------|-------------------|----------------|--------|----------|
| Value Object | Domain concept noun; no suffix | Immutable Java `record` | None | |
| Aggregate | Root container for related value objects | Immutable Java `record` | None | |
| Repository | `{Aggregate}Repository` | Spring `@Component` | `Repository` | |
| Domain Service | `{Subject}{Verb}er` or `{Verb}{Subject}` | Spring `@Component` | None | |
| Data Mapper | `from{Source}()` or `to{Target}()` | Static method | None | |
| Configuration | `{Prefix}Properties` | `@ConfigurationProperties` record | `Properties` | |

**Test Naming (BDD):**

| Test Type | Naming Convention | Examples |
|-----------|-------------------|----------|
| Unit test class | `WhenYou{Action}` | |
| Integration test class | `{Feature}IT` | |
| Test method | `the{Subject}Should{Outcome}()` | |
| Parameterized test method | `the{Subject}Should{Outcome}()` with `@CsvSource` | |

**Prohibited Suffixes:**

Do not use: `Manager`, `Helper`, `Utility`, `Handler`, `Processor`, `Base`, `Info`, `Data` (as a class suffix).

## 4. Domain Model

### 4.1 Java Records

<!-- Define after requirements are clear -->

```java
// Example structure:
// public record EntityName(
//     Type field1,
//     Type field2
// ) {}
```

### 4.2 Data Mappers

| Boundary | Direction | Mapper | Location |
|----------|-----------|--------|----------|
| | | | |

## 5. Processing Pipeline

<!-- Define the steps your application follows -->

## 6. Configuration

### 6.1 `application.yml`

```yaml
spring:
  main:
    web-application-type: none
```

## 7. Error Handling

| Scenario | Behavior | Log Level |
|----------|----------|-----------|
| | | |

## 8. Build Configuration

### 8.1 `settings.gradle`

```groovy
rootProject.name = 'project-name'
```

### 8.2 `build.gradle` (Groovy DSL)

<!-- Fill in after tech stack is decided -->

## 9. Testing Strategy

### 9.0 Test Pyramid and Principles

```text
         ┌─────────┐
         │  E2E    │  Full pipeline tests
         │  (few)  │
        ┌┴─────────┴┐
        │Integration │  Real filesystem, real data
        │ (several)  │
       ┌┴────────────┴┐
       │  Unit Tests   │  Pure functions, no I/O
       │  (many)       │
       └───────────────┘
```

| Layer | Scope | I/O | Framework | Count |
|-------|-------|-----|-----------|-------|
| **Unit** | Single class | None -- pure functions | No Spring context | ~80% of tests |
| **Integration** | Multi-class | Real filesystem | Minimal Spring | ~15% of tests |
| **E2E** | Full pipeline | Real filesystem, real output | `@SpringBootTest` | ~5% of tests |

**No mocks. No mock framework.**

Do not use Mockito, EasyMock, or any mock/stub library. Mocks are unnecessary when:

- **Value objects are immutable records** -- constructing a real instance is a one-line call
- **Services are stateless** -- pass real inputs, assert real outputs
- **Repositories use real files** -- real I/O is fast and catches real bugs
- **Test data exists** -- no need to fabricate test doubles

If a test requires complex setup, that signals the production code needs a simpler interface.

### 9.1 Assertion Library: AssertJ

All tests use AssertJ fluent assertions. Do not use JUnit `assertEquals`, `assertTrue`, or `assertNotNull`.

| JUnit (do not use) | AssertJ (use this) |
|--------------------|--------------------|
| `assertEquals(expected, actual)` | `assertThat(actual).isEqualTo(expected)` |
| `assertTrue(condition)` | `assertThat(condition).isTrue()` |
| `assertNotNull(value)` | `assertThat(value).isNotNull()` |
| `assertEquals(3, list.size())` | `assertThat(list).hasSize(3)` |

### 9.2 Unit Tests

<!-- Define after implementation begins -->

### 9.3 Integration Tests

<!-- Define after implementation begins -->
