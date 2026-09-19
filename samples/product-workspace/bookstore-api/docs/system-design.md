<!-- harness: 2026-09-17 -->
# System Design Document: bookstore-api

<!-- AGENT: Current state only. The path to each decision lives in adr/. This is a module design: it refers up to the product design in ../bookstore/docs/system-design.md for the module map and every contract, and never defines a contract. -->

## Overview

The contract member. It holds the catalog proto and publishes the generated Java stubs as `bookstore:bookstore-api`, so the provider and the consumer compile against one artifact without reading each other's trees. It carries no application code and no tests of its own; the contract's meaning is stated in the product design.

## Package Structure

```
src/main/proto/bookstore/v1/catalog.proto   The contract source; java_package bookstore.api
build.gradle                                 protobuf plugin; publishToMavenLocal is the publish step
```

## Contracts Implemented

Publishes `bookstore.v1.Catalog` as defined in the [product design § Contracts](../../bookstore/docs/system-design.md#contracts). The proto's field numbers are the wire contract; a change bumps the artifact version.

## Principles

The product's testing, architecture, and security briefs apply as written ([`../../bookstore/docs/`](../../bookstore/docs/)); this module adds no extension to them. A module that deviates states only the deviation in a brief of the same name here.

## Dependency Policy

The product's policy applies ([product design § Dependency Policy](../../bookstore/docs/system-design.md#dependency-policy)): Spring Boot's managed versions, the contract artifact from the local Maven repository, nothing read from a neighbor's tree.

## Threat Model

| Threat | Attack Vector | Mitigation |
|--------|--------------|------------|
| A contract change breaking a consumer | Renumbered or retyped field | The artifact version bumps with the proto; consumers pin it |
