# Non-Goal: Purchasing

**Status:** Accepted

## Context

A bookstore page invites the question of buying. The product exists to show the shape of a multi-repository product under the harness, and a catalog is enough to show it.

## Options Considered

1. **A cart and checkout in the web module.** Rejected: it adds state, payments, and accounts to a sample whose point is the module split.
2. **List only** (chosen).

## Decision

The product lists the catalog and sells nothing.

## Consequences

The stock carries no price and no quantity; the ubiquitous language has no order term. A later product may add selling as its own requirements.

## Implementation

**Non-goal:** NG-1

## References

- [`prd.md` § Non-Goals](../prd.md#non-goals)
