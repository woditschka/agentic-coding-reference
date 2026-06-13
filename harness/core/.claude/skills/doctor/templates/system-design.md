<!-- materialized by harness@{{HARNESS_VERSION}}, template system-design, spec 0.1.0 — this file is owned by the project -->
# System Design Document: {{PROJECT_NAME}}

<!-- AGENT: Current state only. The path to each decision lives in adr/. -->
<!-- AGENT: Source code is authoritative for types, interfaces, and constants; this document describes patterns, guardrails, and summaries. -->
<!-- AGENT: Cross-reference prd.md for requirements, adr/ for decisions. -->

## Package Structure

<!-- The module map as it exists today. One line per module: name, responsibility. -->

```
.
└── (empty — first foundational slice creates the map)
```

## Constants

| Name | Value | Description |
|------|-------|-------------|

## Types

<!-- Summarize domain types here. Source code is authoritative; this describes the design contract. -->

## Interfaces

<!-- Summarize public interfaces here. Reference which requirements they implement. -->

## Dependency Policy

Minimize external dependencies. Every dependency is an attack surface and a maintenance burden.

### Approved Sources

| Source | Examples | Rationale |
|--------|----------|-----------|

### Adding a New Dependency

Before adding a dependency, verify:

1. **Necessity** — Can the standard library solve the problem?
2. **Source** — Is it from an approved source above? If not, create an ADR.
3. **Audit** — Review transitive dependencies. Flag unknown modules.
4. **Verification** — Verify checksums and commit the lockfile.

### Prohibited

<!-- Dependency classes this project rejects, with the reason. -->

## Security Context

<!-- PROJECT: Describe this application's security profile: what it connects to,
     what it exposes, how it handles credentials, and how it runs (systemd,
     container, etc.). The security-reviewer reads this section before reviewing. -->

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
