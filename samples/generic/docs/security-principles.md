<!-- harness: 2026-06-26 -->
# Security Principles

This brief specializes the harness's non-negotiable security laws for this project. The four laws — security as an emergent property, defense in depth, least privilege, fail secure — are harness-owned: a project decides *how* it meets them, never *whether*. This document carries that "how": the project's trust-boundary map and the stack's state-of-the-art security defaults. The feature-implementer designs against it; the security-reviewer enforces it; the exhaustive item-by-item checklist lives in the `security-checks` skill.

## Trust Boundaries

A trust boundary is any point where data or control crosses from less-trusted to more-trusted. Every boundary the change introduces or crosses gets the same treatment.

| At the boundary | The rule |
|---|---|
| External input arrives (request, file, env, message) | Validate type, range, and shape before use; reject what the contract does not allow |
| A secret is read (token, key, password) | It never reaches a log, an error message, a URL, or a process argument |
| A privilege is exercised (file, network, process, query) | Grant the minimum scope; deny by default |
| An error crosses back out | The message carries debugging context inward, never internal detail outward |

Internal code, past the boundary, trusts its contracts — defensive checks belong at the boundary, not scattered through the core.

## Realization

Specialize this section to the stack with state-of-the-art, high-bar defaults, derived from the project's own dependency policy and threat model (`docs/system-design.md`): the concrete vulnerability classes that matter here, the principle each puts at risk, and the current best-practice control that prevents it. These defaults are the bar a change starts from, not a floor to argue down. Keep it to the classes a reviewer would actually flag; the `security-checks` skill holds the exhaustive checklist.
