---
name: security-review
description: >-
  Security review checklists, threat model, severity classification,
  and supply chain verification for Go applications.
  Load when conducting security reviews.
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

This review enforces four non-negotiable laws: security as an emergent property, defense in depth, least privilege, fail secure. They are harness-owned, defined in [`tdd-principles.md`](../tdd-workflow/tdd-principles.md) § Secure by Design. How this project meets them — its trust boundaries and the stack's high-bar defaults — lives in the project-owned [`docs/security-principles.md`](../../../docs/security-principles.md), the same brief the feature-implementer designs against. Read both before reviewing and enforce what they say, not remembered defaults. This skill holds the exhaustive checklist that turns the laws and defaults into specific, gradeable items.

## Security Checklist

### Input Validation
- [ ] External responses validated before use
- [ ] Numeric values range-checked (no NaN/Inf in display)
- [ ] HTML template output properly escaped (no XSS)
- [ ] Regex patterns bounded (no ReDoS via catastrophic backtracking)
- [ ] JSON parsing uses safe defaults

### Injection Prevention
- [ ] No command injection (no shell execution with user input)
- [ ] Log injection prevented (newlines stripped/escaped in log values)
- [ ] Template injection prevented if using text templates

### Credential and Sensitive Data Handling
- [ ] Tokens never logged (even at debug level)
- [ ] Credentials not hardcoded in source
- [ ] Credentials loaded from environment/config, not CLI args (ps shows args)
- [ ] Sensitive data not included in error messages
- [ ] No credentials in URLs (use headers instead)

### Network Security
- [ ] Connection timeouts set on all HTTP operations
- [ ] No hardcoded URLs
- [ ] TLS configuration appropriate for deployment context

### Resource Management
- [ ] Memory bounds enforced (response size limits for external calls)
- [ ] Goroutine leaks prevented
- [ ] Context cancellation propagated
- [ ] HTTP server timeouts configured (read, write, idle)
- [ ] File descriptors properly closed (defer close patterns)

### Container/Deployment Security
- [ ] Container image builds successfully (`make podman-build`)
- [ ] Runs as non-root user
- [ ] No unnecessary capabilities
- [ ] Read-only filesystem
- [ ] Health endpoints don't expose sensitive information
- [ ] Secrets mounted from external source, not baked into image

### Data Flow Constraints
- [ ] No sensitive data in logs or served responses
- [ ] Error messages contain no internal details in served responses

### Supply Chain Security
- [ ] `go mod verify` passes
- [ ] go.sum committed
- [ ] No unnecessary dependencies
- [ ] New dependencies from approved sources only (see `docs/system-design.md`)
- [ ] Container base image from trusted registry
- [ ] Multi-stage build separates build and runtime

## Go-Specific Security Checks

### Concurrency Safety
- [ ] No data races (run `go test -race`)
- [ ] Sync primitives not copied
- [ ] Channel operations won't deadlock
- [ ] Context cancellation handled in all goroutines

### Error Handling
- [ ] Errors checked, not ignored
- [ ] Error messages don't leak internal details to external callers
- [ ] Wrapped errors preserve chain for internal debugging
- [ ] Panic recovery at API boundaries

### Type Safety
- [ ] No unsafe package usage without clear justification
- [ ] Interface assertions checked (`val, ok := x.(Type)`)
- [ ] Nil pointer checks before dereference
- [ ] Slice bounds checking

## IDE-Assisted Checks (optional)

When an IDE semantic oracle is available, use it to complement (never replace) the Grep patterns above: check the *resolved* dependency set for the Supply Chain checks, and answer access-control / data-flow questions by resolving security-relevant symbols and their references rather than text-matching. The latter is required, not optional: when the oracle is connected, an access-control / data-flow claim that turns on how a symbol or its references resolve (e.g. "this handler is the only caller that skips the auth check", "every write to this path passes through the validator") **must cite the `search_symbol` / `get_symbol_info` call** that backs it (see `goland` § Cite the call that backs a claim) — without the oracle, cite the grep and label it the weaker basis. The resolved-dependency check stays an accelerator; a client without an oracle relies on Grep alone. Tool mechanics live in the `goland` skill.

## Severity Classification

Rate by reachability and the harm an attacker gains, not by which bucket the issue's name suggests. Severity drives the `blocked` gate, so a reachable medium outranks an unreachable critical.

### CRITICAL (BLOCKED)
- Credential exposure in logs or errors
- Remote code execution vectors
- Authentication bypass
- Unvalidated external input to sensitive operations

### HIGH (BLOCKED)
- TLS validation disabled without justification
- Missing input validation on external data
- Resource exhaustion without bounds
- Data races in security-critical code

### MEDIUM
- Sensitive data in verbose error messages
- Missing timeouts on network operations
- Overly permissive container configuration
- Audit logging gaps

### LOW
- Information disclosure in health endpoints
- Missing rate limiting
- Verbose logging in production default

## Supply Chain Verification

### Automated Checks (via Makefile)

```bash
go mod verify
```

Verifies downloaded modules match go.sum checksums. Must pass. If it fails, the review is **BLOCKED**.

If govulncheck is available:

```bash
govulncheck ./...
```

Checks for known CVEs, reports if vulnerable code is actually called.

### Manual Checks

After automated checks pass:

1. **Dependency inventory**:
   ```bash
   go list -m all
   ```
   Review for unexpected packages, typosquatting, unknown sources.

### govulncheck Output Interpretation

`govulncheck` reports vulnerabilities with two dimensions:

**1. Reachability** (reported by govulncheck):
- **Called** — vulnerable function is executed by your code
- **Imported** — package imported but vulnerable function not called
- **Required** — module in go.mod but vulnerable package not imported

**2. CVE Severity** (check vuln.go.dev for each vulnerability ID):
- CRITICAL, HIGH, MEDIUM, LOW per standard CVE scoring

**Prioritization matrix:**

| Reachability | + CRITICAL/HIGH CVE | + MEDIUM/LOW CVE |
|--------------|---------------------|------------------|
| Called | Fix immediately | Fix this release |
| Imported | Fix this release | Fix when convenient |
| Required | Fix when convenient | Backlog |
