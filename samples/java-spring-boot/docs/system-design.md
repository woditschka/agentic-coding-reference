<!-- materialized by harness@0.1.0, template system-design, spec 0.1.0 — this file is owned by the project -->
# System Design Document: {{PROJECT_NAME}}

<!-- AGENT: Current state only. The path to each decision lives in adr/. -->
<!-- AGENT: Source code is authoritative for types, interfaces, and constants; this document describes patterns, guardrails, and summaries. -->
<!-- AGENT: Cross-reference prd.md for requirements, adr/ for decisions. -->
<!-- AGENT: Design principles and pattern rules live in architecture-principles.md; this document maps how this system applies them. -->

## Architecture Overview

<!-- High-level description of the system architecture. Include an ASCII diagram if helpful. -->

## Tech Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Framework | Spring Boot | 4.1.0 | |
| Build tool | Gradle (Groovy DSL) | 9.5.1 | |
| Language | Java | 25 | |
| JSON | Jackson | *(via Spring Boot)* | |
| Logging | SLF4J + Logback | *(via Spring Boot)* | |
| Testing | JUnit 5 + AssertJ | *(via Spring Boot)* | |

## Package Structure

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

Naming conventions for the types inside each module — pattern suffixes, prohibited suffixes, vocabulary rules — live in [`architecture-principles.md`](architecture-principles.md).

## Domain Model

### Java Records

<!-- Define after requirements are clear -->

```java
// Example structure:
// public record EntityName(
//     Type field1,
//     Type field2
// ) {}
```

### Data Mappers

| Boundary | Direction | Mapper | Location |
|----------|-----------|--------|----------|
| | | | |

## Processing Pipeline

<!-- Define the steps your application follows -->

## Configuration

### `application.yml`

```yaml
spring:
  application:
    name: reference
```

See `src/main/resources/application.yml` for the authoritative configuration.

## Error Handling

| Scenario | Behavior | Log Level |
|----------|----------|-----------|
| | | |

## Dependency Policy

Minimize external dependencies. Every dependency is an attack surface and a maintenance burden.

### Approved Sources

| Source | Examples | Rationale |
|--------|----------|-----------|
| Spring Boot BOM | `spring-boot-starter-webmvc`, `spring-modulith` | Curated and version-managed by the framework |
| Spring Boot test starters | JUnit 5, AssertJ | Test toolchain pinned by the BOM |

### Adding a New Dependency

Before adding a dependency, verify:

1. **Necessity** — Can the JDK or an existing starter solve the problem?
2. **Source** — Is the artifact managed by the Spring Boot BOM? If not, create an ADR.
3. **Audit** — Review transitive dependencies via `./gradlew dependencies`. Flag unknown artifacts.
4. **Verification** — Pin versions through the BOM; never float versions in `build.gradle`.

### Prohibited

- Mock frameworks (Mockito, EasyMock) — construct real records instead; see [`testing-principles.md`](testing-principles.md#mocking-policy)
- Lombok — records and modern Java remove the need for generated boilerplate
- Assertion libraries other than AssertJ

## Threat Model

| Threat | Attack Vector | Mitigation |
|--------|--------------|------------|
<!-- Add rows as the system's attack surface grows. -->

## Build Configuration

### `settings.gradle`

```groovy
rootProject.name = 'reference'
```

See `settings.gradle` for the authoritative configuration.

### `build.gradle` (Groovy DSL)

<!-- Fill in after tech stack is decided -->

## Implementation Order

| ID | Name | Depends On |
|----|------|------------|

## State Machine

<!-- Define state transitions as parseable tables when the system carries state. -->
