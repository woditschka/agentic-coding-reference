# Bookstore

The product umbrella. It owns what every module team needs to know: the requirements, the module map, and the contracts between modules. It builds nothing itself.

## Module map

| Module | Responsibility | Depends on |
|---|---|---|
| `api` | The catalog contract: `Catalog.ListBooks` returns each book's title and subtitle | — |
| `backend` | Serves the catalog over gRPC | `api` |
| `web` | Renders the catalog as one page | `api`, a running `backend` |

## Contract

`bookstore.v1.Catalog` in `../bookstore-api/src/main/proto/bookstore/v1/catalog.proto`. One unary call, `ListBooks`, returning `repeated Book books`, each a `title` and a `subtitle`. The contract is owned here and implemented in `api`; `backend` provides it and `web` consumes it. A change to it is a slice that checks out both sides.

## Workspace

`scripts/layout.toml` declares the members. Each key names the member in the review plan and the gate. Each path is relative to the umbrella and prefixes every change-set path of that member. The contract member declares its contract paths; the two consumers declare their dependency on it.

```toml
[workspace.members]
api     = { path = "../bookstore-api",     stack = "java-spring-boot", contracts = ["src/main/proto/**"] }
backend = { path = "../bookstore-backend", stack = "java-spring-boot", depends_on = ["api"] }
web     = { path = "../bookstore-web",     stack = "java-spring-boot", depends_on = ["api"] }
```

The harness runtime and the product-tier briefs are in place under `docs/`; each member's `docs/` holds its module tier. The grants that let a session reach the members sit in `.claude/settings.json` (Claude Code and the native sandbox) and `opencode.json` (OpenCode); Copilot CLI's grant is per machine.
