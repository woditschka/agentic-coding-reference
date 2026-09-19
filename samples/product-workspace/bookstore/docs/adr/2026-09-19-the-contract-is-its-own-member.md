# The Contract Is Its Own Member, Consumed as a Published Artifact

**Status:** Accepted

## Context

The page and the backend live in separate repositories and share one gRPC contract. The proto file needs a home, and each side needs the generated stubs at build time. Whichever side holds the proto, the other side must reach it without depending on a neighbor being checked out beside it.

## Options Considered

1. **The proto in the backend, the web build reading `../bookstore-backend`.** Rejected: the web member could no longer build alone, which is the coupling checkout on demand exists to prevent.
2. **The proto in the backend, published stubs consumed by the web member.** Workable, but the backend then owns a contract two modules share, and every consumer change reviews the provider's repository.
3. **A contract member owning the proto and publishing the stubs** (chosen). Both sides consume the same artifact from the local Maven repository; neither reads the other's tree.

## Decision

The `api` member holds `catalog.proto` and publishes `bookstore:bookstore-api`. The backend and the web module depend on that artifact. This document, not the member, owns the contract's description and its ownership.

## Consequences

Positive: each member builds alone once the artifact is published; a contract change is visibly a three-repository slice, this document plus both sides. Negative: a publish step precedes the consumers' builds, which the umbrella's gate runs first.

## Implementation

**Requirements:** REQ-BOOK-001

## References

- [`system-design.md` § Contracts](../system-design.md#contracts)
