---
name: deps-upgrade
description: >-
  Check pinned tool, plugin, and dependency versions across the Go and
  Java Spring Boot samples against upstream stable releases. Reports
  drift as a table, applies approved bumps to build files and version
  tables, and verifies each project's build after the change.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## Scope

| Scope | What It Checks |
|-------|---------------|
| *(all)* | Both Go and Java samples |
| `go` | `go/go.mod`, `go/Makefile`, `go/README.md`, `go/CLAUDE.md` |
| `java` | `java-spring-boot/build.gradle`, `java-spring-boot/gradle/wrapper/gradle-wrapper.properties`, `java-spring-boot/README.md`, `java-spring-boot/CLAUDE.md` |

## Pinned Versions (source of truth)

### Go sample

| Item | Pinned In | Upstream source |
|------|-----------|-----------------|
| Go release line | `go/go.mod` (`go` directive), `go/README.md`, `go/CLAUDE.md` | https://go.dev/doc/devel/release |
| golangci-lint | `go/Makefile` (`GOLANGCI_LINT_VERSION`), `go/README.md`, `go/CLAUDE.md` | https://github.com/golangci/golangci-lint/releases |
| Direct Go modules | `go/go.mod` (require block) | `go list -m -u all` |
| Container base images | `go/deploy/Dockerfile` (`FROM ...`) | Image registry (Docker Hub / gcr.io) |

Note: Dockerfile tags like `golang:1.26` and `distroless/static-debian12:nonroot` are deliberate floats — they track the latest patch within a pinned minor/distro line. Bump the minor/distro suffix only when the Go directive in `go.mod` moves or when distroless upstream changes its default distro.

### Java Spring Boot sample

| Item | Pinned In | Upstream source |
|------|-----------|-----------------|
| Java toolchain | `build.gradle` (`languageVersion`), `README.md`, `CLAUDE.md` | *(none — held at current LTS; see Java rule in Step 2)* |
| Gradle wrapper | `gradle/wrapper/gradle-wrapper.properties` (`distributionUrl`), `README.md`, `CLAUDE.md` | https://gradle.org/releases/ |
| Spring Boot plugin | `build.gradle` (`org.springframework.boot`), `README.md`, `CLAUDE.md` | https://github.com/spring-projects/spring-boot/releases |
| Spring Dependency Management plugin | `build.gradle` (`io.spring.dependency-management`) | https://github.com/spring-gradle-plugins/dependency-management-plugin/releases |
| Spotless plugin | `build.gradle` (`com.diffplug.spotless`) | https://github.com/diffplug/spotless/releases |
| google-java-format | `build.gradle` (`googleJavaFormat(...)`) | https://github.com/google/google-java-format/releases |
| Spring Modulith BOM | `build.gradle` (`mavenBom 'org.springframework.modulith:spring-modulith-bom:X'`) | https://github.com/spring-projects/spring-modulith/releases |
| Starter/BOM-managed deps | `build.gradle` dependencies | Spring Boot / Modulith BOM (no explicit version) |

## Process

### 1. Collect Current Pins

Read the files listed above. Extract each version string exactly as it appears. Record where each string lives — every pin may be duplicated in `CLAUDE.md` and `README.md` tables.

### 2. Fetch Upstream Latest Stable

Fetch the upstream source listed for each item. Rules:

- Prefer the project's releases/changelog page over third-party aggregators.
- Use only stable releases — ignore `-M`, `-RC`, `-alpha`, `-beta`, snapshot tags.
- For Spring Boot, match the pinned major.minor line unless the user explicitly opts into a new major (4.0.x → 4.0.latest by default; 4.0 → 4.1 needs confirmation).
- **For Java, do not fetch upstream.** The pinned version is held at the current LTS by policy. The LTS cadence is every 4 years (JDK 21 → 25 → 29). If today's date is past the next LTS GA window, note "new LTS may be available — confirm before bump" in the report; otherwise list Java as up to date without a network call.

### 3. Produce a Drift Report

Present findings before editing anything:

```
## Dependency Drift Report: [date]

### Scope: [all | go | java]

### Drift
| Item | Pinned | Latest | Released | Notes |
|------|--------|--------|----------|-------|
| Spring Boot | 4.0.5 | 4.0.6 | 2026-04-15 | patch — safe |
| Spotless    | 8.4.0 | 8.5.1 | 2026-04-10 | minor — review changelog |

### Up to Date
- Gradle wrapper 9.4.1
- Go 1.26
- golangci-lint v2.11.4

### Major/Risky Bumps (needs explicit opt-in)
- Java 25 → 26 (new release line)
- Spring Boot 4.0.x → 4.1.x (minor line bump)
```

### 4. Get Approval

Do NOT edit without explicit user approval. Call out risky bumps separately. A bundled "upgrade everything" response is approval for patch/minor bumps only — major-line moves always need a second confirmation.

### 5. Apply Edits

For each approved item:

1. Update the authoritative pin (build file or wrapper).
2. Update every `README.md` / `CLAUDE.md` table that mirrors the version.
3. If a Spring Boot major/minor moves, check for dependency rename announcements (e.g., `spring-boot-starter-web` → `spring-boot-starter-webmvc` in 4.0) and adjust `build.gradle` accordingly.

Never edit `go.sum` by hand — let `go mod tidy` regenerate it.

### 6. Verify (mandatory — blocks Step 7)

After every edit in Step 5, run the affected project's full build+test gate. This step is **not optional**: a bump is not considered applied until its project builds clean.

| Project edited | Command | Run from | Covers |
|----------------|---------|----------|--------|
| Go (`go/**`) | `make ci` | `go/` | tidy, fmt, vet, lint, deps-check, test, build |
| Java (`java-spring-boot/**`) | `./gradlew clean build` | `java-spring-boot/` | compile, spotlessCheck, test, bootJar |

Rules:

1. **Always run the verify command, even for "trivial" patch bumps.** A Spotless point release has broken formatting rules before; a Spring Boot patch has shifted a transitive BOM version before. Build verification is the only check that catches these.
2. **If both projects were edited, run both verify commands** — never assume one result covers the other.
3. **Use `clean` on Gradle** to force plugin and BOM resolution against the new versions; Gradle's configuration cache can otherwise reuse stale metadata.
4. **For `golangci-lint` bumps**, remove the installed binary first (`rm -f $(go env GOPATH)/bin/golangci-lint`) so the Makefile reinstalls at the new pinned version. The Makefile's install target only fires when the binary is missing. Then run `make ci`.
5. **For Gradle wrapper bumps**, use `./gradlew wrapper --gradle-version <new-version>` (run twice — once to update `gradle-wrapper.properties`, again to regenerate `gradle-wrapper.jar`). Then run the full verify. Commit both the properties file and the jar.
6. **On failure, do not "fix forward" silently.** Report the failure with the exact output, identify which bump caused it (bisect if multiple), and either revert that single bump or propose a follow-up code change (e.g., a starter rename). Do not ship a half-working update.
7. **Do not skip hooks or checks** (`--no-verify`, `-x test`, `-x spotlessCheck`) to make a bump appear to succeed.

A bump is only "done" when its verify command exits 0 with all checks green.

### 7. Report

Summarize what changed, what stayed, and the **build result from Step 6** (quote the exit status and the last line of build output per project). Include exact file/line references for each edit. If any verify run failed, the report must say so — do not claim success without a clean build.

## What This Skill Does NOT Do

- **CVE scanning** — that is the `security-review` skill's job. This skill does not check advisories before recommending upgrades; it assumes patch/minor bumps are safe and flags major moves for review.
- **Adding new dependencies** — this skill only bumps what is already pinned.
- **Dependency policy enforcement** — see `go/docs/system-design.md#dependency-policy` for the approved-sources list.
- **Renovate/Dependabot replacement** — this is a one-shot manual workflow, not continuous automation.

## Handling Ambiguity

- If upstream releases a new major while the sample is still on an older line, report it as "Major available" but do not propose it unless asked.
- If a plugin changes its coordinates (group:artifact), treat it like a code change: propose the rename, explain the upstream rationale, and require explicit approval.
- If a BOM-managed transitive version is pinned explicitly, flag it — the BOM may have moved but the explicit pin overrides it.

## Commit Convention

Use `build:` for dependency/tool changes, scoped to `go` or `java`:

```
build(java): bump spring boot 4.0.5 → 4.0.6 and spotless 8.4.0 → 8.5.1
build(go): bump golangci-lint v2.7.2 → v2.11.4
```

Bundle related bumps in one commit when they were validated by the same build run; split when a bump required a code change (starter rename, BOM migration).
