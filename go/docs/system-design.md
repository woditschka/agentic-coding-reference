# System Design

<!-- AGENT: This is the tactical implementation reference -->
<!-- AGENT: Source code is authoritative for types, interfaces, and constants -->
<!-- AGENT: This document describes patterns, guardrails, and summaries -->
<!-- AGENT: Cross-reference PRD for requirements, ADRs for decisions -->

## Package Structure

```
.
├── main.go                  # Entry point
├── internal/                # Internal packages
│   └── testutil/            # Shared test helpers
└── testdata/                # Test fixture files
```

## Constants

| Name | Value | Description |
|------|-------|-------------|

## Types

<!-- Summarize Go types here. Source code is authoritative; this describes the design contract. -->

## Interfaces

<!-- Summarize Go interfaces here. Reference which requirements they implement. -->

## Dependency Policy

Minimize external dependencies. Every dependency is an attack surface and a maintenance burden.

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

## Threat Model

| Threat | Attack Vector | Mitigation |
|--------|--------------|------------|
<!-- Add rows as the system's attack surface grows. -->

## Implementation Order

| ID | Name | Depends On |
|----|------|------------|

## State Machine

<!-- Define state transitions using parseable tables per docs/documentation.md -->
