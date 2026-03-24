---
name: security-review
description: >-
  Security review checklists, threat model, severity classification,
  and dependency verification for Java/Spring Boot applications.
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

### Path Traversal and File Operations
- [ ] Input paths resolved to absolute path before use
- [ ] No directory traversal via crafted input (`../`, symlinks)
- [ ] File operations restricted to configured directories
- [ ] Symlinks not followed (or explicitly validated)
- [ ] Output files written only to expected locations
- [ ] No file writes outside the designated directory tree
- [ ] Agent/development temp files only in `.scratch/tmp/`, never system `/tmp`

### Input Injection
- [ ] User-derived content escaped before inclusion in output (HTML, JSON, etc.)
- [ ] No inputs passed to shell commands or `Runtime.exec()` / `ProcessBuilder`
- [ ] No inputs used in string interpolation for SQL, LDAP, or other query languages
- [ ] Regex patterns bounded (no ReDoS via catastrophic backtracking)
- [ ] Log injection prevented (newlines stripped/escaped in log values)

### HTML Output Safety (if applicable)
- [ ] All user-derived content escaped before HTML insertion
- [ ] `<`, `>`, `&`, `"`, `'` properly escaped in text content and attributes
- [ ] No inline JavaScript in generated HTML
- [ ] No external resource loading (`<script>`, `<link>`, `<img>` with remote URLs)
- [ ] `href` attributes use relative paths only, not `javascript:` or `data:` URIs

### JSON Safety
- [ ] Jackson configured with safe defaults (no polymorphic deserialization)
- [ ] No `@JsonTypeInfo` annotations that enable arbitrary class instantiation
- [ ] Corrupted data files handled gracefully (not crash)
- [ ] JSON parsing uses safe defaults

### Credential and Sensitive Data Handling
- [ ] Tokens never logged (even at debug level)
- [ ] Credentials not hardcoded in source
- [ ] Credentials loaded from environment/config, not CLI args (ps shows args)
- [ ] Sensitive data not included in error messages
- [ ] No credentials in URLs (use headers instead)

### Input Validation
- [ ] Paths validated (exists, correct type, readable/writable)
- [ ] Date strings validated before parsing
- [ ] Configuration values validated at startup
- [ ] No integer overflow in size or count handling

### Network Security (if applicable)
- [ ] Connection timeouts set on all HTTP operations
- [ ] No hardcoded URLs
- [ ] TLS configuration appropriate for deployment context
- [ ] Responses from external services treated as untrusted

### Resource Management
- [ ] No unbounded memory allocation
- [ ] File handles properly closed (try-with-resources)
- [ ] Stream operations do not hold references to large collections
- [ ] Graceful behavior under high load

### Dependency Security
- [ ] Framework versions checked for known CVEs
- [ ] Jackson version checked for deserialization vulnerabilities
- [ ] No unnecessary dependencies in `build.gradle`
- [ ] Dependencies from approved sources only (see `docs/system-design.md`)

### Logging Safety
- [ ] No sensitive data in log output
- [ ] SLF4J parameterized logging (no string concatenation that evaluates eagerly)
- [ ] No `System.out.println` or `System.err.println`
- [ ] Log messages include sufficient context for debugging

## Severity Classification

### CRITICAL (BLOCKED)
- Credential exposure in logs or errors
- Remote code execution vectors (unsafe Jackson deserialization, shell injection)
- Authentication bypass
- Unvalidated external input to sensitive operations

### HIGH (BLOCKED)
- Path traversal allowing writes outside designated directories
- Missing input validation on external data
- Unbounded memory allocation (response size limits)
- File handles leaked (no try-with-resources)
- ReDoS-vulnerable regex patterns

### MEDIUM
- Sensitive data in verbose error messages
- Missing timeouts on network operations
- Missing Content-Security-Policy in generated HTML
- Verbose logging in production default

### LOW
- Information disclosure in health endpoints
- Missing rate limiting
- Dependency not on latest patch version

## Detection Patterns

Use Grep to search for dangerous code patterns during review:

| Pattern | What It Detects |
|---|---|
| `append\|concat\|format\|printf\|+.*html\|\.write(` in `src/main/java/` | Unescaped output |
| `Runtime\|ProcessBuilder\|exec(` in `src/main/java/` | Shell execution |
| `enableDefaultTyping\|JsonTypeInfo\|WRAPPER_ARRAY` in `src/main/java/` | Unsafe Jackson config |
| `Files\.\|FileWriter\|FileOutputStream\|BufferedWriter` in `src/main/java/` | File operations |
| `followLinks\|NOFOLLOW` in `src/main/java/` | Symlink handling |
| `/tmp/` in `src/main/java/` | System tmp usage (should use `.scratch/tmp/`) |
