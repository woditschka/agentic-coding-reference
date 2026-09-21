<!-- harness: 2026-09-17 -->
# Security Principles

This brief specializes the harness's non-negotiable security laws for this project. The four laws — security as an emergent property, defense in depth, least privilege, fail secure — are harness-owned: a project decides *how* it meets them, never *whether*. This document carries that "how": the project's trust-boundary map and the stack's state-of-the-art security defaults. The feature-implementer designs against it; the security-reviewer enforces it; the exhaustive item-by-item checklist lives in the `security-checks` skill.

## Trust Boundaries

A trust boundary is any point where data or control crosses from less-trusted to more-trusted. Every boundary the change introduces or crosses gets the same treatment.

| At the boundary | The rule |
|---|---|
| External input arrives (request, file, env, message) | Validate type, range, and shape before use; reject what the contract does not allow |
| A secret is read (token, key, password) | It never reaches a log, an error message, a URL, or a process argument |
| A secret is stored | It lives in the environment or a secret store, never in committed source |
| A privilege is exercised (file, network, process, query) | Grant the minimum scope; deny by default |
| An error crosses back out | The message carries debugging context inward, never internal detail outward |

Internal code, past the boundary, trusts its contracts — defensive checks belong at the boundary, not scattered through the core.

## Language Realization

The product's trust boundaries run between its members, so this section states them; a member adds a brief of its own only where it has a boundary of its own.

| Boundary | Class at risk | Control |
|---|---|---|
| The page's HTTP surface | Injection through rendered values | Thymeleaf escapes every rendered value; the page renders domain records, never raw wire strings |
| The catalog contract, provider side | Untrusted request shape | The generated stubs reject a malformed message before the endpoint runs; the endpoint reads no request field |
| The catalog contract, consumer side | Untrusted response content and a hostile or absent peer | The mapper validates each book into a domain value; deadline, retry, and concurrency limit bound the call |

## Standing Gaps

- No dependency scanner runs in any member's build; the versions come from Spring Boot's BOM and the `upgrade-deps` skill checks them against upstream.
- Transport security is not configured (NG-2).
