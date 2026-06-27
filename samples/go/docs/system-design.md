<!-- harness: 2026-06-26 -->
# System Design Document: {{PROJECT_NAME}}

<!-- AGENT: Current state only. The path to each decision lives in adr/. -->
<!-- AGENT: Source code is authoritative for types, interfaces, parameters, and constant values. Name each contract once, say what it guarantees and which requirement it implements, and point at the source file. Do not transcribe fields, parameters, or constant literals — in a table OR in prose. They rot when the code changes and add no design information. -->
<!-- AGENT: Cross-reference prd.md for requirements, adr/ for decisions. -->

## Overview

<!-- A short narrative: the shape of the system and the principles that hold it together. Prose, not bullets. A reader who stops here understands the architecture. -->

## Package Structure

<!-- The module map as it exists today. One line per module: name, responsibility. -->

```
.
├── main.go                  # Entry point
├── internal/                # Internal packages
│   └── testutil/            # Shared test helpers
└── testdata/                # Test fixture files
```

## Constants

<!-- Name each constant and cite the source file that owns its value; do not copy the value (source is authoritative). -->

| Name | Source | Description |
|------|--------|-------------|

## Contracts

<!-- One row per public type, interface, or function. Purpose in one line; the source file owns the signature; Implements names the requirement(s). No field or parameter lists — those live in source. Add a short prose note above the table only for an invariant a row cannot carry. -->

| Contract | Purpose | Source | Implements |
|----------|---------|--------|------------|

## Dependency Policy

Minimize external dependencies. Every dependency is an attack surface and a maintenance burden. Where a dependency is needed, trust is inherited from provenance. Prefer the standard library, then libraries that well-recognized, security-conscious projects already depend on and have validated; flag anything outside that vetted set for an ADR. This is the project's `secure-by-design` posture — see [`security-principles.md`](security-principles.md) § Go Realization.

### Approved Sources

| Source | Examples | Rationale |
|--------|----------|-----------|
| Go standard library | `net/http`, `encoding/json`, `log/slog` | Zero supply chain risk |
| `github.com/google/*` | `go-cmp` | Google-maintained, widely audited |
| `golang.org/x/*` | `vuln`, `sync` | Go team extended stdlib |
| `gopkg.in/yaml.v3` | YAML parsing | De facto standard, stable API |

### Adding a New Dependency

Before adding a dependency, verify:

1. **Necessity** — Can the standard library solve the problem?
2. **Source** — Is the module from an approved source above? If not, create an ADR.
3. **Audit** — Check `go list -m all` for transitive dependencies. Flag unknown modules.
4. **Verification** — Run `go mod verify` and commit `go.sum`.

### Prohibited

- Assertion libraries (`testify`, `gomega`) — use standard `if/t.Errorf`
- Logging frameworks (`zap`, `logrus`) — use `log/slog`
- HTTP routers (`gin`, `chi`, `mux`) — use `net/http` (Go 1.22+ routing)
- DI frameworks (`wire`, `dig`) — use constructor functions
- Mock generators (`mockgen`, `mockery`) — hand-write mocks at system boundaries
- Prometheus client (`github.com/prometheus/*`) — 40+ transitive deps; use `expvar` or OpenTelemetry stdlib bridge
- Kubernetes client (`k8s.io/*`, `sigs.k8s.io/*`) — 100+ transitive deps; if K8s integration is required, create an ADR justifying the attack surface

### Supply Chain Controls

| Control | Mechanism |
|---------|-----------|
| Checksum verification | `go.sum` committed, `go mod verify` in CI |
| Vulnerability scanning | `govulncheck` in `make security` |
| Dependency review | `go list -m all` reviewed on changes |
| Minimal transitive deps | Prefer stdlib; fewer deps = smaller attack surface |

## Security Context

<!-- PROJECT: Describe this application's security profile: what it connects to, what it exposes, how it handles credentials, and how it runs (systemd, container, etc.). The security-reviewer reads this section before reviewing. -->

- **Inputs it processes:** <!-- files, network, user input -->
- **Outputs it produces:** <!-- files, network, UI -->
- **External services it connects to:** <!-- APIs, datastores, brokers -->
- **Credential handling:** <!-- where secrets come from, how they are stored -->
- **Runtime:** <!-- who runs it and where (systemd, container, serverless) -->

## Threat Model

| Threat | Attack Vector | Mitigation |
|--------|--------------|------------|
<!-- Add rows as the system's attack surface grows. -->

## Implementation Order

| ID | Name | Depends On |
|----|------|------------|

## State Machine

<!-- Define state transitions as parseable tables when the system carries state. -->
