---
name: security-review
description: >-
  Security review checklists, threat model, severity classification,
  and supply chain verification for Go applications.
  Load when conducting security reviews.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## Core Security Principles

### Security as Emergent Property
Security cannot be bolted on later. Verify that security considerations are present from initial design, not added as an afterthought.

### Defense in Depth
Multiple overlapping controls. No single mechanism should be the only protection. Check for:
- Input validation at entry points AND internal processing
- TLS for transport AND credential protection at rest
- Timeout enforcement at multiple layers

### Least Privilege
Grant minimal necessary permissions:
- Code accesses only required resources
- Credentials scoped to specific operations
- No unnecessary capabilities in container/service

### Fail Secure
When errors occur, system should remain secure:
- Connection failures should not expose credentials
- Parsing errors should not bypass validation
- Resource exhaustion should not disable security checks

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

## Severity Classification

### CRITICAL (BLOCKED)
- Credential exposure in logs or errors
- Remote code execution vectors
- Authentication bypass
- Unvalidated external input to sensitive operations

### HIGH
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
