<!-- harness: 2026-06-26 -->
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

## Java Realization

State-of-the-art defaults for this Spring Boot (webmvc + Modulith) project, derived from its dependency policy and threat model (`docs/system-design.md`). These are the bar a change starts from, not a floor to argue down.

| Class | Principle at risk | High-bar default |
|---|---|---|
| Supply-chain surface | Least privilege | Spring Boot BOM only; versions pinned through the BOM, never floated in `build.gradle`; new artifacts ADR-gated; transitive deps audited via `./gradlew dependencies`. See `docs/system-design.md` § Dependency Policy |
| Deserialization | Fail secure | Jackson with safe defaults; no `enableDefaultTyping`, no untrusted `@JsonTypeInfo`; never Java native `Serializable` for external data |
| Web input validation | Defense in depth | Treat request bodies, params, and headers as untrusted; validate at the controller boundary and reject before a service sees them. If a validation starter is added, enforce with Bean Validation (`jakarta.validation`) |
| Injection | Fail secure | No external input in `Runtime.exec`/`ProcessBuilder`; no user input evaluated as SpEL; if persistence is added, bind query parameters, never string-build them |
| Output & headers | Defense in depth | Escape user-derived content before rendering; set Content-Security-Policy and HSTS; SLF4J parameterized logging with no sensitive fields |
| Secrets & configuration | Least privilege | Secrets externalized from `application.yml`, never committed; loaded from env or a secret manager |
| Module boundaries | Least privilege | Cross-module access only through a module's public API; the Modulith boundary test fails the build on a violation |
| Resources | Fail secure | Bounded allocations and request size limits; try-with-resources; graceful behavior under load |

The exhaustive item-by-item sweep — detection patterns, dependency verification, and the full severity table — lives in the `security-review` skill, which the security-reviewer runs.
