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

1. **Security and reliability are emergent** — must be designed in, not retrofitted.
2. **Consistency over novelty** — match existing patterns unless there is a compelling reason.
3. **Explicit dependencies** — every integration point documented.
4. **Layer respect** — features belong in appropriate architectural layers.
5. **Minimal surface** — prefer internal packages.
6. **Understandable systems** — if it cannot be reasoned about, it cannot be secured.
7. **Fail secure** — errors leave the system in a safe state.

## Validation Checklist

Before approving a feature for implementation:

### Architectural Fit
- [ ] Feature aligns with project goals
- [ ] Feature not in Non-Goals or Out of Scope
- [ ] Package placement follows existing `internal/` structure
- [ ] Error handling matches `fmt.Errorf("context: %w", err)` pattern
- [ ] New types follow existing naming conventions
- [ ] No circular dependencies between packages
- [ ] Integration points identified
- [ ] New dependencies from approved sources (see `docs/system-design.md`); ADR required for exceptions

### DDD Alignment

See `docs/ddd-principles.md` (monorepo root) for full principles.

- [ ] Value objects are immutable with no framework dependencies
- [ ] Aggregates enforce their own invariants
- [ ] Data mappers are stateless and pure at all boundaries
- [ ] One aggregate per package
- [ ] Dependencies flow inward (infrastructure → service → domain)
- [ ] `make deps-check` passes

### Security by Design
- [ ] Credentials handled per existing patterns (config, not hardcoded)
- [ ] Input validation specified
- [ ] Error messages don't leak sensitive data
- [ ] Logging follows redaction patterns
- [ ] Network operations use TLS

### Reliability by Design
- [ ] Failure modes enumerated
- [ ] Timeouts specified for all blocking operations
- [ ] Resource limits defined (buffers, connections)
- [ ] Graceful shutdown behavior specified
- [ ] Context cancellation propagated

### Understandability
- [ ] Component can be understood in isolation
- [ ] State changes are explicit
- [ ] Interfaces are minimal and typed
- [ ] No implicit dependencies
