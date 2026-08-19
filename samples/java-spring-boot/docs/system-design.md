<!-- harness: 2026-06-26 -->
# System Design Document: {{PROJECT_NAME}}

<!-- AGENT: Current state only. The path to each decision lives in adr/. -->
<!-- AGENT: Source code is authoritative for types, interfaces, parameters, and constant values. Name each contract once, say what it guarantees and which requirement it implements, and point at the source file. Do not transcribe fields, parameters, or constant literals — in a table OR in prose. They rot when the code changes and add no design information. -->
<!-- AGENT: Cross-reference prd.md for requirements, adr/ for decisions. -->
<!-- AGENT: Design principles and pattern rules live in architecture-principles.md; this document maps how this system applies them. -->

## Overview

<!-- A short narrative: the shape of the system and the principles that hold it together. Prose, not bullets. A reader who stops here understands the architecture. -->

## Tech Stack

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Framework | Spring Boot | 4.1.0 | |
| Build tool | Gradle (Groovy DSL) | 9.7.1 | |
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

## Constants

<!-- Name each constant and cite the source file that owns its value; do not copy the value (source is authoritative). -->

| Name | Source | Description |
|------|--------|-------------|

## Contracts

<!-- One row per public type, interface, or function. Purpose in one line; the source file owns the signature; Implements names the requirement(s). No field or parameter lists — those live in source. Add a short prose note above the table only for an invariant a row cannot carry. -->

| Contract | Purpose | Source | Implements |
|----------|---------|--------|------------|

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

## Security Context

<!-- PROJECT: Describe this application's security profile: what it connects to, what it exposes, how it handles credentials, and how it runs (systemd, container, etc.). The security-reviewer reads this section before reviewing. -->

- **Inputs it processes:** <!-- files, network, user input -->
- **Outputs it produces:** <!-- files, network, UI -->
- **External services it connects to:** <!-- APIs, datastores, brokers -->
- **Credential handling:** <!-- where secrets come from, how they are stored -->
- **Runtime:** <!-- who runs it and where (systemd, container, serverless) -->

## Threat Model

| Threat | Attack Vector | Mitigation |
|--------|--------------|------------|
<!-- Add rows as the system's attack surface grows. -->

## Implementation Order

| ID | Name | Depends On |
|----|------|------------|

## State Machine

<!-- Define state transitions as parseable tables when the system carries state. -->
