<!-- harness: 2026-09-17 -->
# System Design Document: bookstore-web

<!-- AGENT: Current state only. The path to each decision lives in adr/. This is a module design: it refers up to the product design in ../bookstore/docs/system-design.md for the module map and every contract, and never defines a contract. -->

## Overview

A Spring Boot application with two Modulith modules. `catalog` holds the `Book` value, `CatalogService`, and under `internal/` the outbound port `CatalogClient` with its gRPC adapter, whose static mapper keeps the wire shape out of the domain. `books` holds the page controller, which sees only the service. The adapter carries the product's resilience rules: a deadline per call, a retry with backoff because the read is idempotent, a concurrency limit, and a `CatalogUnavailable` failure the page turns into a notice.

## Package Structure

```
bookstore.web
├── WebApplication                @SpringBootApplication @Modulithic
├── catalog/
│   ├── Book                      Value: a title, never blank, and a subtitle
│   ├── CatalogService            The module's public face
│   ├── CatalogUnavailable        The domain failure the page degrades on
│   └── internal/
│       ├── CatalogClient         The outbound port
│       ├── GrpcCatalogClient     The adapter: deadline, @Retryable, @ConcurrencyLimit; fromResponse() maps inward
│       └── GrpcCatalogConfig     Imports the stub on the channel named in application.yml
└── books/
    └── BookController            GET / renders books.html; catches CatalogUnavailable
```

`ModularityTests` fails the build on a boundary breach; the resilience proxies are class proxies ([ADR](adr/2026-09-19-class-proxies-for-resilience.md)).

## Contracts Implemented

Consumes `bookstore.v1.Catalog.ListBooks` from the [product design § Contracts](../../bookstore/docs/system-design.md#contracts) through `GrpcCatalogClient`. The consumer-driven contract test is `GrpcCatalogClientTests`, which pins the mapping from the published stubs into `Book`. Implements REQ-BOOK-001 and REQ-BOOK-002.

## Principles

The product's testing, architecture, and security briefs apply as written ([`../../bookstore/docs/`](../../bookstore/docs/)); this module adds no extension to them. A module that deviates states only the deviation in a brief of the same name here.

## Dependency Policy

The product's policy applies ([product design § Dependency Policy](../../bookstore/docs/system-design.md#dependency-policy)): Spring Boot's managed versions, the contract artifact from the local Maven repository, nothing read from a neighbor's tree.

## Threat Model

| Threat | Attack Vector | Mitigation |
|--------|--------------|------------|
| A hostile or absent backend | Slow, failing, or malformed answers | Deadline, bounded retry, concurrency limit; the mapper drops a blank title; the page degrades to a notice |
