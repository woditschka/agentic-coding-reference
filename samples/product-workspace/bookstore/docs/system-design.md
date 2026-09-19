<!-- harness: 2026-09-17 -->
# System Design Document: bookstore

<!-- AGENT: Current state only. The path to each decision lives in adr/. -->
<!-- AGENT: Source code is authoritative for types, interfaces, parameters, and constant values. Name each contract once, say what it guarantees and which requirement it implements, and point at the source file. Do not transcribe fields, parameters, or constant literals — in a table OR in prose. They rot when the code changes and add no design information. -->
<!-- AGENT: Cross-reference prd.md for requirements, adr/ for decisions. -->

## Overview

Three modules in three repositories, checked out beside this umbrella. The contract member publishes the catalog's gRPC contract as a library; the backend provides it from a fixed stock; the web module consumes it and renders the page. Each module's internal design lives in that module's own `docs/system-design.md`; this document owns what crosses a module boundary: the map, the contract, the dependency direction, and the cross-cutting rules. Deployment topology is two processes on one machine for the sample, stated here and in no layout.

## Package Structure

<!-- The module map as it exists today. One line per module: name, responsibility. -->

| Member | Responsibility | Depends on | Module design |
|---|---|---|---|
| `api` | Owns the catalog contract's artifact: the proto and its generated stubs, published to the local Maven repository | — | [`bookstore-api/docs/system-design.md`](../../bookstore-api/docs/system-design.md) |
| `backend` | Provides the catalog contract over gRPC from its stock | `api` | [`bookstore-backend/docs/system-design.md`](../../bookstore-backend/docs/system-design.md) |
| `web` | Consumes the catalog contract and renders the page | `api`, a running `backend` | [`bookstore-web/docs/system-design.md`](../../bookstore-web/docs/system-design.md) |

References run one way: a module design refers up to this map and to the contracts it implements, and never defines one. Whatever another module's team would need to know is written here.

## Constants

<!-- Name each constant and cite the source file that owns its value; do not copy the value (source is authoritative). -->

| Name | Source | Description |
|------|--------|-------------|

## Contracts

<!-- One row per public type, interface, or function. Purpose in one line; the source file owns the signature; Implements names the requirement(s). No field or parameter lists — those live in source. Add a short prose note above the table only for an invariant a row cannot carry. -->

| Contract | Purpose | Source | Implements |
|----------|---------|--------|------------|
| `bookstore.v1.Catalog.ListBooks` | One unary call returning every stocked book as a title and a subtitle, in stock order | `../bookstore-api/src/main/proto/bookstore/v1/catalog.proto` | REQ-BOOK-001 |

The contract's description and ownership live here; its artifact lives in the `api` member. A change to the contract is a slice across this document and both sides, with both members checked out. Integration between provider and consumer is the consumer's contract test against the published stubs, never a shared checkout.

## Scale and Load

<!-- PROJECT: The workload the code is sized for. The design owner writes each row at triage; the implementer selects against it and the code-quality reviewer judges against the same row. A figure nobody knows is written as "unrecorded, treated as bounded" and corrected here when the real figure arrives. "Bounded" is a complete row. -->

| Data set or path | Realistic size | Growth | Access pattern | Form |
|------------------|----------------|--------|----------------|------|
| The stock | 3 books | bounded, fixed at build time | shared read-mostly | an immutable list in the backend |
| Page requests | unrecorded, treated as bounded | bounded | request-private | one gRPC call per page request, capped at 8 in flight |
<!-- One row per collection or path that scales with use: rows, requests per second, payload size. Access pattern: request-private, shared read-mostly, shared read-write. Form: the structure or algorithm chosen. On a hot path it carries its time and space bound with its kind (worst-case, average, amortized). A hand-written one, or a measured claim, links its ADR. -->

- **Hot paths:** the page request, one gRPC round trip with a 2-second deadline.
- **Limits:** 8 concurrent catalog calls per web instance; the backend holds no connection to anything.

## Dependency Policy

Minimize external dependencies. Every dependency is an attack surface and a maintenance burden.

### Approved Sources

| Source | Examples | Rationale |
|--------|----------|-----------|
| Spring Boot's managed dependencies | the web, Thymeleaf, gRPC server and client starters, Modulith | One BOM pins every version; the members restate none |
| The contract artifact from the local Maven repository | `bookstore:bookstore-api` | The one product-owned library; published by the `api` member's build |
| Maven Central, through the BOM | grpc-java, protobuf-java | The versions Spring Boot manages for the pinned release |

### Adding a New Dependency

Before adding a dependency, verify:

1. **Necessity** — Can the standard library solve the problem? A dependency for one function is justified only when the function is more than a few lines of tested code and the library is established. The decision weighs writing and maintaining the code against the dependency and its transitive tree.
2. **Source** — Is it from an approved source above? If not, create an ADR.
3. **Audit** — Review transitive dependencies. Flag unknown modules.
4. **Verification** — Verify checksums and commit the lockfile.

### Prohibited

- A member reading another member's sources or build outputs from disk: the contract is consumed as a published artifact, so a member builds without its neighbor checked out.
- A resilience library: Spring Framework 7 carries retry and concurrency limits.

## Security Context

<!-- PROJECT: Describe this application's security profile: what it connects to, what it exposes, how it handles credentials, and how it runs (systemd, container, etc.). The security-reviewer reads this section before reviewing. -->

- **Inputs it processes:** HTTP page requests to the web module; gRPC calls to the backend on the loopback interface.
- **Outputs it produces:** one HTML page.
- **External services it connects to:** none; the backend holds its stock in memory.
- **Credential handling:** none exist.
- **Runtime:** two JVM processes on one machine, started by the umbrella's run script; plaintext gRPC by decision (NG-2).

## Threat Model

| Threat | Attack Vector | Mitigation |
|--------|--------------|------------|
| Malformed catalog data reaching the page | A served book with a blank title | The web adapter's mapper drops it; a blank title never becomes a domain value |
| A slow or absent backend exhausting the web module | Page requests piling up on a hanging gRPC call | Per-call deadline, bounded retries, a concurrency limit, and the degraded page |
| Wire-level eavesdropping | Plaintext gRPC | Accepted for the sample on one machine (NG-2); a deployment adds TLS through SSL bundles |

## Implementation Order

| ID | Name | Depends On |
|----|------|------------|
| 1 | The contract member publishes the catalog proto | — |
| 2 | The backend serves the stock over the contract | 1 |
| 3 | The web module renders the catalog and degrades without it | 1 |

## State Machine

The product carries no state beyond the fixed stock.
