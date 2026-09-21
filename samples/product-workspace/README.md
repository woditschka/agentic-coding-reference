# Product Workspace Sample

A product split across repositories, run by one harness. The umbrella owns the product truth; each member owns one module. In this tree the four directories share one repository; a workspace run places them side by side as four repositories, siblings of one another, never nested.

| Directory | Role | Holds |
|---|---|---|
| `bookstore/` | Umbrella | The product tier: PRD, product design with the module map and the contract, glossary, cross-module decisions, the workspace layout, the harness runtime |
| `bookstore-api/` | Member `api` | The catalog proto and its generated Java stubs, published to the local Maven repository |
| `bookstore-backend/` | Member `backend` | A Spring Boot gRPC server answering the catalog with a static list |
| `bookstore-web/` | Member `web` | A Spring Boot page listing the books it fetches over gRPC |

The shape follows the [product-workspace design](../../docs/product-workspace.md) and the [decision](../../docs/adr/2026-09-13-product-workspace-with-member-modules.md) behind it. The umbrella is a materialized generic-stack consumer. Its layout declares the three members with their contract paths and dependencies. Its `.claude/settings.json` and `opencode.json` carry the directory grants for Claude Code and OpenCode; Copilot CLI's grant is per machine. Its `stack.sh` binds every gate verb to the members' Gradle builds. Its briefs hold the product tier. The PRD carries two requirements and two non-goals; the product design carries the module map and the one contract; the glossary, the security boundaries between members, and two cross-module decisions complete it. The umbrella also states the testing, architecture, and security bar once, realized for Java. Each member holds the module tier: its own design referring up to the contract it implements, its decision log, and a one-line rules file naming the umbrella. A member adds a brief only where it deviates, and none does.

## Shape

Each Spring member is a Spring Modulith application with one `catalog` module. The module's root holds its public face, the `Book` value and `CatalogService`; role-named sub-packages hold the adapters. In the backend the gRPC endpoint and the fixed-list repository are adapters behind the service. In the web module the gRPC client is an adapter behind an outbound port, and the page controller sees only the service. A static `from…`/`to…` mapper at each adapter is the anti-corruption layer: the generated contract types never cross into a domain type. `ModularityTests` in each member fails the build on a boundary breach.

The web adapter carries the minimum distributed-system discipline for one remote call, from Spring Framework 7 and gRPC alone. A per-call deadline bounds the wait. A retry with backoff is safe because the read is idempotent. A concurrency limit keeps a slow backend from absorbing every request thread. A domain failure lets the page show a notice instead of an error.

## Run the harness

In this tree the four directories are subdirectories of one repository, so the change set would be this repository's. A harness run needs them as sibling repositories:

```bash
samples/product-workspace/materialize-workspace.sh /tmp/bookstore-ws   # four repositories, one base commit each
cd /tmp/bookstore-ws/bookstore                                          # every harness session starts here
```

From there `scripts/changeset.py --name-only` lists a member's edit as `../bookstore-backend/...`, `scripts/grading.py review-plan` records the members map, and `scripts/gate.sh verify` runs every verb in each present member, the contract member first.

## Build and run

The umbrella carries the script; the members build in dependency order and run from their boot jars:

```bash
bookstore/bookstore.sh build    # publish the contract, build backend and web
bookstore/bookstore.sh start    # backend gRPC on :9090, web on http://localhost:8080/, Ctrl-C stops both
bookstore/bookstore.sh up       # both
```

Each member is its own Gradle project on the Java sample's toolchain (Java 25, Gradle 9.7.1, Spring Boot 4.1.1), and builds alone with `./gradlew build` once the contract is published. Every build runs google-java-format before compiling, so formatting is never a separate step.

The transport carries one call, `Catalog.ListBooks`, and no TLS: the sample shows the shape, not a deployment.
