<!-- materialized by harness@0.1.0, template security-principles, spec 0.1.0 — this file is owned by the project -->
# Security Principles

This brief specializes the harness's non-negotiable security laws for this project. The four laws — security as an emergent property, defense in depth, least privilege, fail secure — are harness-owned: a project decides *how* it meets them, never *whether*. This document carries that "how": the project's trust-boundary map and the stack's state-of-the-art security defaults. The feature-implementer designs against it; the security-reviewer enforces it; the exhaustive item-by-item checklist lives in the `security-review` skill.

## Trust Boundaries

A trust boundary is any point where data or control crosses from less-trusted to more-trusted. Every boundary the change introduces or crosses gets the same treatment.

| At the boundary | The rule |
|---|---|
| External input arrives (request, file, env, message) | Validate type, range, and shape before use; reject what the contract does not allow |
| A secret is read (token, key, password) | It never reaches a log, an error message, a URL, or a process argument |
| A privilege is exercised (file, network, process, query) | Grant the minimum scope; deny by default |
| An error crosses back out | The message carries debugging context inward, never internal detail outward |

Internal code, past the boundary, trusts its contracts — defensive checks belong at the boundary, not scattered through the core.

## Go Realization

State-of-the-art defaults for this Go project, derived from its dependency policy and threat model (`docs/system-design.md`). These are the bar a change starts from, not a floor to argue down.

| Class | Principle at risk | High-bar default |
|---|---|---|
| Dependency trust | Least privilege | Auditing every transitive dependency directly is infeasible, so trust is inherited from provenance. A library that recognized, security-conscious Go projects (e.g. Kubernetes, Prometheus) depend on and have validated is acceptable; anything outside that vetted set is flagged for an ADR. Importing those projects' own heavyweight clients is a separate concern, gated by `docs/system-design.md` § Dependency Policy for transitive surface. Prefer the standard library first |
| Supply-chain integrity | Defense in depth | `go mod verify` and `govulncheck` run in the gate; `go.sum` committed; transitive set reviewed via `go list -m all` on change |
| Untrusted input | Defense in depth | Validate decoded JSON/YAML at the boundary; bound reads with `io.LimitReader`; reject malformed input rather than trusting it |
| Command & path injection | Fail secure | Never build a shell string; `exec.Command` with an argument slice. Resolve and confine file paths; reject `..` traversal |
| Secrets | Least privilege | From env or a secret manager, never source or CLI args; never logged; compared with `subtle.ConstantTimeCompare` |
| Cryptography & randomness | Fail secure | `crypto/*` standard library only, no homegrown primitives; `crypto/rand` for tokens and salts |
| Transport security | Defense in depth | `net/http` with TLS 1.2 minimum (prefer 1.3); never `InsecureSkipVerify`; client and server timeouts always set |
| Concurrency & resources | Fail secure | `go test -race` clean; propagate `context` cancellation; `defer` every `Close`; bound allocations |
| Log & output safety | Defense in depth | `log/slog` structured fields; strip newlines from logged external values (log injection); escape any rendered output |
| Type safety | Fail secure | Check the `ok` of every assertion; check pointers before dereference; respect slice bounds |

The exhaustive item-by-item sweep — `govulncheck` interpretation, container hardening, and the full severity table — lives in the `security-review` skill, which the security-reviewer runs.
