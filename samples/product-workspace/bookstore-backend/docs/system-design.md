<!-- harness: 2026-09-17 -->
# System Design Document: bookstore-backend

<!-- AGENT: Current state only. The path to each decision lives in adr/. This is a module design: it refers up to the product design in ../bookstore/docs/system-design.md for the module map and every contract, and never defines a contract. -->

## Overview

A Spring Boot application with one Modulith module, `catalog`. The module's root holds the `Book` value and `CatalogService`; `internal/` holds the gRPC endpoint that provides the contract and the fixed-list repository behind the service. The endpoint's static mapper is the anti-corruption layer: a contract type never reaches a domain type.

## Package Structure

```
bookstore.backend
├── BackendApplication            @SpringBootApplication @Modulithic
└── catalog/                      The one module; public API at its root
    ├── Book                      Value: a title, never blank, and a subtitle
    ├── CatalogService            The module's public face
    └── internal/
        ├── BookRepository        The persistence port
        ├── StaticBookRepository  The fixed stock behind the port
        └── CatalogEndpoint       @GrpcService providing the contract; toResponse() maps outward
```

`ModularityTests` fails the build on a boundary breach.

## Contracts Implemented

Provides `bookstore.v1.Catalog.ListBooks` from the [product design § Contracts](../../bookstore/docs/system-design.md#contracts) through `CatalogEndpoint`, which serves whatever `CatalogService` returns in stock order. Implements REQ-BOOK-001.

## Principles

The product's testing, architecture, and security briefs apply as written ([`../../bookstore/docs/`](../../bookstore/docs/)); this module adds no extension to them. A module that deviates states only the deviation in a brief of the same name here.

## Dependency Policy

The product's policy applies ([product design § Dependency Policy](../../bookstore/docs/system-design.md#dependency-policy)): Spring Boot's managed versions, the contract artifact from the local Maven repository, nothing read from a neighbor's tree.

## Threat Model

| Threat | Attack Vector | Mitigation |
|--------|--------------|------------|
| A caller flooding the endpoint | Many concurrent ListBooks calls | The stock is an immutable in-memory list; each call is allocation-only, and the sample sets no further limit (NG-2 territory for a deployment) |
