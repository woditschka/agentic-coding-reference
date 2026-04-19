---
name: design-validation
description: >-
  Architectural validation checklist for feature approval.
  Load when validating that features fit into the existing architecture.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## Design Principles

Apply these principles when evaluating features:

1. **Pipeline integrity** — the processing pipeline is the backbone; features must fit within it.
2. **Consistency over novelty** — match existing patterns unless there is a compelling reason.
3. **Explicit dependencies** — every integration point documented.
4. **Granular failure** — errors should be as granular as possible.
5. **Records for data, components for behavior** — keep the data model clean.
6. **Test-data driven** — every input handling change must work against test data.

## Validation Checklist

Before approving a feature for implementation:

### Architectural Fit
- [ ] Feature aligns with project goals
- [ ] Feature not in Non-Goals or Out of Scope
- [ ] Package placement follows existing module structure (see `docs/system-design.md`)
- [ ] New types use Java records for data, Spring components for services
- [ ] Error handling follows system-design.md patterns
- [ ] No circular dependencies between modules
- [ ] No access to another module's `internal/` sub-packages
- [ ] Pipeline step ordering preserved
- [ ] Integration points identified
- [ ] New dependencies justified and from approved sources (see `docs/system-design.md`); ADR required for exceptions

### DDD and Modulith Alignment

See `docs/ddd-principles.md` for full principles.

- [ ] Value objects are immutable records with no framework annotations
- [ ] Aggregates enforce their own invariants
- [ ] Data mappers are stateless and pure at all boundaries
- [ ] New module has public API at package root, internals in sub-packages
- [ ] Cross-module orchestration uses module APIs, not internal types
- [ ] Modularity verification test passes (`ModularityTests.java`)

### Security by Design
- [ ] Credentials handled per existing patterns (config, not hardcoded)
- [ ] Input validation specified
- [ ] Error messages don't leak sensitive data
- [ ] Logging follows redaction patterns
- [ ] Network operations use TLS

### Reliability by Design

**Robustness:**
- [ ] Failure modes enumerated
- [ ] Failure in one item does not prevent processing others
- [ ] Corrupted data/state files handled gracefully
- [ ] Unparseable inputs handled (logged, not silently dropped)
- [ ] I/O errors caught at appropriate granularity
- [ ] Granular error handling (per-item, not per-batch where possible)
- [ ] Resource limits defined (buffers, connections)
- [ ] Graceful shutdown behavior specified (if applicable)

**Idempotency:**
- [ ] Running twice with no changes produces identical output
- [ ] State and output files consistent after every run
- [ ] No partial writes leave the system in a broken state

### Understandability

**Decomposition:**
- [ ] Feature maps to a clear package and class
- [ ] Single responsibility: one class does one thing
- [ ] No hidden dependencies between packages
- [ ] Component can be understood in isolation

**Clear Interfaces:**
- [ ] Methods accept typed parameters (no raw `Object` or `Map<String, Object>`)
- [ ] Return types express failure clearly (`Optional` for absence, exceptions for errors)
- [ ] Records used for data transfer between steps

**Predictable Behavior:**
- [ ] Error handling matches the table in system-design.md
- [ ] State changes are explicit
- [ ] Side effects limited to defined output locations
- [ ] No implicit dependencies

### Data Model Integrity
- [ ] New records follow naming conventions
- [ ] State file schema remains backward-compatible (or migration path defined)
- [ ] JSON serialization round-trips correctly
- [ ] UTF-8 encoding maintained throughout

### Testability
- [ ] Unit-testable without filesystem dependencies
- [ ] Integration tests can use test data
- [ ] Edge cases covered by parameterized tests
