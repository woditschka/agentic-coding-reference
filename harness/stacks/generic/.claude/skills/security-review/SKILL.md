---
name: security-review
description: >-
  Security-review checklist, threat model, severity classification, and
  supply chain verification — language-agnostic, with per-section slots a
  stack fills in. Load when conducting security reviews.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
metadata:
  version: "1.0"
  author: team
---

## Core Security Principles

This review enforces four non-negotiable laws: security as an emergent property, defense in depth, least privilege, fail secure. They are harness-owned, defined in [`tdd-principles.md`](../tdd-workflow/tdd-principles.md) § Secure by Design. How this project meets them — its trust boundaries and the stack's high-bar defaults — lives in the project-owned [`docs/security-principles.md`](../../../docs/security-principles.md), the same brief the feature-implementer designs against. Read both before reviewing and enforce what they say, not remembered defaults. This skill holds the language-agnostic checklist; the **Stack-specific checks** slots are where this project records the vulnerability classes and controls its technology imposes.

## Security Checklist

### Input Validation
- [ ] External responses validated before use
- [ ] Numeric values range-checked
- [ ] Output encoded/escaped for its sink (no injection into HTML, SQL, shell, logs)
- [ ] Pattern matching bounded (no catastrophic backtracking)
- [ ] Structured-input parsing uses safe defaults

### Injection Prevention
- [ ] No command injection (no shell execution with untrusted input)
- [ ] Log injection prevented (newlines and control characters stripped from logged values)
- [ ] Template and query injection prevented (parameterized, never concatenated)

### Credential and Sensitive Data Handling
- [ ] Secrets never logged, even at debug level
- [ ] No credentials hardcoded in source
- [ ] Credentials loaded from environment or a secret store, not command-line arguments
- [ ] Sensitive data not included in error messages
- [ ] No credentials in URLs (use headers or a secret store)

### Network Security
- [ ] Connection timeouts set on all outbound operations
- [ ] No hardcoded endpoints
- [ ] Transport security configured appropriately for the deployment context

### Resource Management
- [ ] Memory and response-size bounds enforced for external calls
- [ ] Concurrent-unit leaks prevented
- [ ] Cancellation propagated through the call tree
- [ ] Server timeouts configured (read, write, idle)
- [ ] File descriptors and handles closed deterministically

### Container / Deployment Security
- [ ] Container image builds successfully (via the stack's container build, if any)
- [ ] Runs as a non-root user
- [ ] No unnecessary capabilities
- [ ] Read-only filesystem where possible
- [ ] Health endpoints expose no sensitive information
- [ ] Secrets mounted from an external source, not baked into the image

### Data Flow Constraints
- [ ] No sensitive data in logs or served responses
- [ ] Served error messages contain no internal details

### Supply Chain Security
- [ ] Dependency integrity verified (lockfile checksums match)
- [ ] The lockfile is committed
- [ ] No unnecessary dependencies
- [ ] New dependencies from approved sources only (see `docs/system-design.md`)
- [ ] Container base image from a trusted registry
- [ ] Multi-stage build separates build and runtime, where applicable

## Stack-Specific Security Checks

The classes below recur in every language but take a stack-specific form. Record this stack's concrete checks in each slot, or in `docs/security-principles.md` § Realization.

### Concurrency Safety
- [ ] No data races; shared state is synchronized or avoided
- [ ] Cancellation handled in every concurrent unit
- [ ] **Stack-specific checks:** {{FILL: race tooling, concurrency primitives}}

### Error Handling
- [ ] Errors checked, never silently ignored
- [ ] Error messages do not leak internal detail to external callers
- [ ] Failures at API boundaries are contained, not propagated as crashes
- [ ] **Stack-specific checks:** {{FILL: error/exception idioms, boundary recovery}}

### Type and Memory Safety
- [ ] Unsafe or low-level constructs justified, or absent
- [ ] Type conversions and casts are checked
- [ ] Null/absent and bounds conditions guarded before access
- [ ] **Stack-specific checks:** {{FILL: unsafe constructs, null/bounds idioms}}

## Severity Classification

Rate by reachability and the harm an attacker gains, not by which bucket the issue's name suggests. Severity drives the `blocked` gate, so a reachable medium outranks an unreachable critical.

### CRITICAL (BLOCKED)
- Credential exposure in logs or errors
- Remote code execution vectors
- Authentication bypass
- Unvalidated external input to sensitive operations

### HIGH (BLOCKED)
- Transport security disabled without justification
- Missing input validation on external data
- Resource exhaustion without bounds
- Data races in security-critical code

### MEDIUM
- Sensitive data in verbose error messages
- Missing timeouts on network operations
- Overly permissive container configuration
- Audit-logging gaps

### LOW
- Information disclosure in health endpoints
- Missing rate limiting
- Verbose logging in the production default

## Supply Chain Verification

### Automated Checks

Run dependency hygiene through the gate:

```bash
scripts/gate.sh deps
```

It must pass. If integrity verification fails, the review is **BLOCKED**. If the stack provides a vulnerability scanner, bind it into `verb_deps` (or document it in `CLAUDE.md`) and run it here; it checks for known advisories and, where possible, whether vulnerable code is actually called.

- [ ] **Stack-specific checks:** {{FILL: integrity command, vulnerability scanner, advisory source}}

### Manual Checks

After automated checks pass, inventory the resolved dependency tree and review for unexpected packages, typosquatting, and unknown sources.

### Advisory Output Interpretation

Prioritize each advisory along two dimensions — reachability and severity:

**Reachability:**
- **Reachable** — vulnerable code is executed by this project
- **Present, not called** — dependency present, vulnerable path not invoked
- **Declared, not used** — declared in the manifest, vulnerable package not imported

**Severity:** CRITICAL, HIGH, MEDIUM, LOW per standard scoring.

**Prioritization matrix:**

| Reachability | + CRITICAL/HIGH | + MEDIUM/LOW |
|--------------|-----------------|--------------|
| Reachable | Fix immediately | Fix this release |
| Present, not called | Fix this release | Fix when convenient |
| Declared, not used | Fix when convenient | Backlog |
