<!-- harness: 2026-06-26 -->
# System Design Document: Generic Stack Template

<!-- AGENT: Current state only. The path to each decision lives in adr/. -->
<!-- AGENT: Source code is authoritative for types, interfaces, parameters, and constant values. Name each contract once, say what it guarantees and which requirement it implements, and point at the source file. Do not transcribe fields, parameters, or constant literals — in a table OR in prose. They rot when the code changes and add no design information. -->
<!-- AGENT: Cross-reference prd.md for requirements, adr/ for decisions. -->

## Overview

<!-- A short narrative: the shape of the system and the principles that hold it together. Prose, not bullets. A reader who stops here understands the architecture. -->

## Package Structure

<!-- The module map as it exists today. One line per module: name, responsibility. -->

```
.
└── (empty — first foundational slice creates the map)
```

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

### Adding a New Dependency

Before adding a dependency, verify:

1. **Necessity** — Can the standard library solve the problem?
2. **Source** — Is it from an approved source above? If not, create an ADR.
3. **Audit** — Review transitive dependencies. Flag unknown modules.
4. **Verification** — Verify checksums and commit the lockfile.

### Prohibited

<!-- Dependency classes this project rejects, with the reason. -->

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
