# Class Proxies for the Resilience Annotations

**Status:** Accepted

## Context

`GrpcCatalogClient` implements the `CatalogClient` port and carries `@Retryable` and `@ConcurrencyLimit` on its method. Spring's default proxies an interface-implementing bean through the interface, where the annotations are not declared, and the concurrency-limit interceptor then fails with "No @ConcurrencyLimit annotation found".

## Options Considered

1. **Annotate the port's method.** Rejected: the port would carry a transport policy.
2. **Class proxies for the resilience interceptors** (chosen): `@EnableResilientMethods(proxyTargetClass = true)`.

## Decision

The resilience interceptors proxy the class, so the annotations stay on the adapter and the port stays a plain contract.

## Consequences

The adapter needs a non-private constructor for the generated subclass, which it has. Every resilient bean in this module is proxied by class.

## Implementation

**Requirements:** REQ-BOOK-002

## References

- [`system-design.md` § Package Structure](../system-design.md#package-structure)
