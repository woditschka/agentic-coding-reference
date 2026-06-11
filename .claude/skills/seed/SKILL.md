---
name: seed
description: >-
  Push a sample template into a target project. Detects the target's stack
  (Go or Java Spring Boot, Gradle or Maven) and selects the matching sample
  as template automatically; init mode scaffolds a new empty target and asks
  which AI coding tools to seed (default: all four); upgrade mode raises the
  bar on an existing project by merging template improvements while
  preserving domain customizations. Load when the user invokes
  `/seed <project-path>`.
compatibility:
  - claude-code
metadata:
  version: "2.0"
  author: team
---

# Seed

Push a sample template's setup into a target project. Runs from the monorepo root. The samples (`go/`, `java-spring-boot/`) are the templates; this skill selects one per target.

**Usage:** `/seed <project-path>` (e.g., `/seed ../new-project`)

## Template Selection

Detect the target's stack before anything else. Check the target root for build markers:

| Signal in target | Template (`<template>`) | Variant |
|---|---|---|
| `go.mod` | `go/` | — |
| `pom.xml` | `java-spring-boot/` | Maven |
| `build.gradle` or `build.gradle.kts` | `java-spring-boot/` | Gradle |
| More than one marker | Ask the user which stack is authoritative | — |
| No marker | Ask: `go` or `java`; for `java`, also `gradle` (default) or `maven` | — |

The marker selects the template only; the Modes table below decides the mode. A target with `.claude/` but no build marker is an Upgrade-mode target whose stack you must ask for.

Every template path below resolves relative to `<template>`. Target paths resolve relative to the target root. Sections marked **[Go]** or **[Java]** apply only when that template is selected.

## Modes

Detect automatically based on target state:

| Target State | Mode | Behavior |
|---|---|---|
| No `.claude/` directory | **Init** | Full copy, ask for project details |
| Has `.claude/` but outdated | **Upgrade** | Diff and merge, preserve domain content |

## Tool Surfaces

The templates carry agent definitions for four AI coding tools. The set of tools to seed is decided differently per mode:

- **Init Mode:** ask the user (see Init Step 1). Default offered: all four.
- **Upgrade Mode:** auto-detect from which tool directories exist in the target. Never add a tool surface the target opted out of, and never remove one the target has.

### Always copied/diffed (the shared substrate, regardless of selection)

| Path | Reason |
|---|---|
| `CLAUDE.md` | Single rules file all tools read (Copilot reads it natively; OpenCode falls back to it; Junie reads it via `.junie/config.json`) |
| `.claude/skills/` | All four tools discover skills here |
| `.claude/templates/` | Shared agent templates |
| `.claude/settings.local.json` | Bash permission list (tool-agnostic) |
| `schemas/scratch/` | Handoff schemas (tool-agnostic) |
| `scripts/` | Harness tooling: handoff-log access tool and change-grader extractor (tool-agnostic) |
| `docs/` | Documentation scaffolding (tool-agnostic) |
| `.gitignore` | |

### Tool-gated paths

The four tools are equal first-class targets, listed below in the canonical order used everywhere in this skill (claude → copilot → opencode → junie). Detection is uniform: each tool's presence is signaled by its `<tool-dir>/agents/` directory existing.

| Tool | Paths | Init detection key | Upgrade detection key |
|---|---|---|---|
| Claude Code | `.claude/agents/`, `.claude/settings.json`, `.claude/hooks/` | user picks `claude` | `.claude/agents/` exists in target |
| Copilot CLI | `.github/agents/` | user picks `copilot` | `.github/agents/` exists in target |
| OpenCode | `.opencode/agents/` | user picks `opencode` | `.opencode/agents/` exists in target |
| Junie CLI | `.junie/agents/`, `.junie/config.json` | user picks `junie` | `.junie/agents/` exists in target |

## Init Mode

### 1. Gather Project Details

Ask the user for:

| Field | Placeholder / Value | Example |
|---|---|---|
| Project name | `{{PROJECT_NAME}}` | `home-status-page` |
| Project description | `{{PROJECT_DESCRIPTION}}` | `CLI tool for home infrastructure` |
| Build tool **[Java]** | `gradle` (default) or `maven` | `maven` |
| Tools to seed | Subset of `claude,copilot,opencode,junie` (default: all four) | `junie` or `claude,junie` |

Gradle is the canonical build for the Java template. If the user picks `maven`, follow the "Build Tool Variant: Maven" section below when copying.

For the Tools question, present the four options in canonical order (claude, copilot, opencode, junie) as a multi-select with all four pre-selected. Record the chosen set as `<selected-tools>` — Step 2 gates per-tool directories on it.

**Validate non-empty:** if the user deselects all four and confirms, re-ask. A seed with zero tools produces a directory that has skills and rules but no agents to invoke them — refuse to proceed until at least one tool is selected.

### 2. Copy Structure

Copy these directories and files from `<template>` to the target. Items tagged **[tool: X]** are copied only when tool X was selected in Step 1 (see the Tool Surfaces section for the full table).

```
CLAUDE.md                  (root rules file; placeholders filled in step 3)

.claude/
├── agents/*.md          [tool: claude] (all agents including README.md)
├── hooks/*.sh           [tool: claude] (continue-only SendMessage guard)
├── skills/*/SKILL.md    (all skills)
├── templates/*.md        (all templates)
├── settings.json        [tool: claude] (agent-teams flag + hook registration)
└── settings.local.json

.github/
└── agents/*.agent.md    [tool: copilot] (Copilot agents)

.opencode/
└── agents/*.md          [tool: opencode] (all agents)

.junie/
├── agents/*.md          [tool: junie] (all agents)
└── config.json          [tool: junie] (Junie's pointer to CLAUDE.md and .claude/skills/)

schemas/
└── scratch/*.json        (JSON Schemas for .scratch/handoff.jsonl record types)

scripts/
├── handoff.py            (deterministic handoff-log access: append, validate, latest, next-retry, show)
├── test_handoff.py
├── score-change.py       (change-grader extractor)
├── test_score_change.py
└── layout.toml           (extractor path-classification config — module rules are project-specific; review after seeding)
```

`schemas/scratch/` carries the per-record-type JSON Schemas that the pipeline-coordinator uses to gate agent transitions on `.scratch/handoff.jsonl`. Copy verbatim — these are language-specific (the regex patterns assume the template's conventions, e.g. Go test naming or JUnit `@Test`-tagged method names) and should not be modified during seed.

`scripts/handoff.py` preserves the executable bit. The target wires the two test files into its own gate: `make test-scripts` for Go targets, a Gradle `Exec` task on `check` for Gradle targets, `exec-maven-plugin` or equivalent for Maven. Report this wiring as a next step — build files are the target's own (see Build files below).

`.claude/settings.json` and `.claude/hooks/sendmessage-continue-only.sh` are a pair. The settings file enables the agent-teams flag and registers the hook that restricts `SendMessage` resumes to a bare `continue`. Copy both or neither — a registered hook whose script is missing fails the guard open.

**Build files:**
- **[Go]** No build files are copied. The target owns `go.mod` and `Makefile`; the template's `Makefile` serves as reference for the `ci` and `test-scripts` targets.
- **[Java, Gradle]** Copy `build.gradle`, `settings.gradle`, `gradlew`, `gradlew.bat`, `gradle/` directory.
- **[Java, Maven]** Skip all Gradle files. See "Build Tool Variant: Maven" below.

### 3. Fill Placeholders

Replace in all copied files:
- `{{PROJECT_NAME}}` → user-provided project name
- `{{PROJECT_DESCRIPTION}}` → user-provided description

### 4. Copy Documentation Scaffolding

For each file below, if it does not exist in the target, copy it from `<template>`. Files that already exist in the target are not touched in Init Mode — Upgrade Mode handles drift.

```
docs/
├── prd.md
├── system-design.md
├── ubiquitous-language.md
├── agentic-harness.md
├── documentation-standards.md
├── ddd-principles.md
├── tdd-principles.md
├── testing-principles.md
└── adr/
    └── README.md
```

Fill `{{PROJECT_NAME}}` and `{{PROJECT_DESCRIPTION}}` in any newly-copied files. The `ubiquitous-language.md` starts as an empty template; domain vocabulary accumulates as the PRD develops.

### 5. Update .gitignore

Ensure the target's `.gitignore` includes:
```
.scratch/
```

If no `.gitignore` exists, copy the template's `.gitignore`.
If one exists, append `.scratch/` if missing.

**Maven variant only:** replace `build/` with `target/` in the copied `.gitignore` (Gradle build directory → Maven build directory). Remove any `!gradle/wrapper/gradle-wrapper.jar` line.

### 6. Prompt for Security Context

After copying, render the "Next steps" message below to the user. The four security-reviewer paths under step 2 are tool-gated — drop the bullets whose `[if ... selected]` marker does not match `<selected-tools>`, and do not output the `[if ... selected]` text itself. The user should see a clean list with only their chosen tools' paths.

```
Next steps:
1. Review CLAUDE.md — confirm the Toolchain, Build Commands, and Testing Strategy sections match your project
2. Fill in the Security Context in:
   - .claude/agents/security-reviewer.md           [if claude selected]
   - .github/agents/security-reviewer.agent.md     [if copilot selected]
   - .opencode/agents/security-reviewer.md         [if opencode selected]
   - .junie/agents/security-reviewer.md            [if junie selected]
   (replace the <!-- PROJECT --> comment with your application's security profile)
3. Wire scripts/test_score_change.py and scripts/test_handoff.py into your build's test target
4. Review scripts/layout.toml — adjust module rules to your package layout
5. Review docs/prd.md and fill in your requirements
6. Review docs/system-design.md and fill in your architecture
7. Run /lint-docs to validate documentation coherence
```

## Build Tool Variant: Maven [Java]

Gradle is canonical. If the user selected `maven` in Step 1, generate the Maven variant via the Spring Initializr API (`start.spring.io`) so the output is idiomatic and matches Spring's own scaffolding.

### 1. Derive Initializr parameters from the template's `build.gradle`

Read the template `build.gradle` once and extract:

| Gradle source | Initializr param | Notes |
|---|---|---|
| `id 'org.springframework.boot' version 'X.Y.Z'` | `bootVersion=X.Y.Z` | Spring Boot version |
| `java.toolchain.languageVersion = JavaLanguageVersion.of(N)` | `javaVersion=N` | |
| `group = 'com.example'` | `groupId=com.example` | Or ask user |
| `dependencies { implementation 'org.springframework.boot:spring-boot-starter-webmvc' }` | `dependencies=web` | |
| `implementation 'org.springframework.modulith:spring-modulith-api'` | add `modulith` | |
| (default) | `type=maven-project`, `language=java`, `packaging=jar` | Fixed values |
| `{{PROJECT_NAME}}` (from Step 1) | `artifactId`, `name`, `baseDir` | |
| `{{PROJECT_DESCRIPTION}}` | `description` | URL-encoded |
| Derive from name | `packageName=com.example.<slug>` | Slug: lowercase, alphanum only |

### 2. Call Initializr

```bash
curl -sSf https://start.spring.io/starter.zip \
  -d type=maven-project \
  -d language=java \
  -d bootVersion={{boot-version}} \
  -d javaVersion={{java-version}} \
  -d groupId={{group-id}} \
  -d artifactId={{project-name}} \
  -d name={{project-name}} \
  -d description={{project-description}} \
  -d packageName={{package-name}} \
  -d packaging=jar \
  -d dependencies=web,modulith \
  -o .scratch/tmp/initializr.zip
```

Extract `.scratch/tmp/initializr.zip` into a staging directory.

### 3. Take only the build scaffolding

From the extracted archive, copy to the target:
- `pom.xml`
- `mvnw`, `mvnw.cmd`
- `.mvn/wrapper/` (whole directory)
- `.gitignore` patterns specific to Maven (`target/`, `.mvn/wrapper/maven-wrapper.properties` rules) — merge with the target `.gitignore` if one exists

Do **not** copy the Initializr-generated `src/` — the template's source (or the target's existing source) is authoritative.

### 4. Patch `pom.xml` with template-specific build concerns

Initializr does not configure formatters. Add the Spotless plugin under `<build><plugins>` in the generated `pom.xml` so it matches Gradle's `googleJavaFormat` setup:

```xml
<plugin>
  <groupId>com.diffplug.spotless</groupId>
  <artifactId>spotless-maven-plugin</artifactId>
  <version>{{spotless-maven-version}}</version>
  <configuration>
    <java>
      <googleJavaFormat>
        <version>{{gjf-version-from-gradle}}</version>
      </googleJavaFormat>
    </java>
  </configuration>
  <executions>
    <execution>
      <goals><goal>check</goal></goals>
      <phase>verify</phase>
    </execution>
  </executions>
</plugin>
```

Versions:
- `{{gjf-version-from-gradle}}` — take from the template `build.gradle` `googleJavaFormat('X.Y.Z')` call. The formatter version is identical across Gradle and Maven Spotless plugins.
- `{{spotless-maven-version}}` — **do not reuse the Gradle plugin version.** Spotless's Gradle plugin and Maven plugin have independent version lines. Resolve the latest release from Maven Central's metadata and use that:

  ```bash
  curl -sSf https://repo.maven.apache.org/maven2/com/diffplug/spotless/spotless-maven-plugin/maven-metadata.xml \
    | tr -d '\n' \
    | sed -n 's|.*<release>\([^<]*\)</release>.*|\1|p'
  ```

  The `<release>` element holds the latest non-snapshot version. Use it in the `<version>` field above. If the command fails (network error) or returns empty output (metadata schema changed), stop and report the failure to the user — do not fall back to a hardcoded version.

Verify `spring-modulith-starter-test` and `junit-platform-launcher` are present in test scope; if Initializr omitted them, add them (coordinates match the Gradle file).

Verify the web starter coordinate matches the template `build.gradle`: Initializr's `web` dependency resolves to `spring-boot-starter-web`, but Spring Boot 4.x uses `spring-boot-starter-webmvc` (renamed). If Gradle uses `-webmvc` and the generated `pom.xml` has `-web`, adjust the coordinate to match.

### 5. Derive CLAUDE.md Maven sections

Replace the following sections in the copied `CLAUDE.md` (before Step 3 placeholder replacement runs):

**Toolchain table:**

| Tool | Version | Notes |
|------|---------|-------|
| Java | {{java-version}} | Toolchain managed via Maven |
| Maven | 3.9.x (via wrapper) | Use `./mvnw` |
| Spring Boot | {{boot-version}} | |

**Build Commands:**

```bash
./mvnw verify           # Build, test, and run spotless check
./mvnw test             # Run all tests
./mvnw spotless:apply   # Format all Java files
./mvnw spotless:check   # Check formatting (fails if unformatted)
./mvnw spring-boot:run  # Run the application
./mvnw package          # Build fat JAR
```

**Quality Gate:** `./mvnw verify` (single command runs build + test + spotless:check via the verify phase binding added in Step 4).

### 6. Update `.claude/settings.local.json` permissions

Substitute Gradle command patterns with Maven equivalents:

| Gradle permission | Maven permission |
|---|---|
| `Bash(./gradlew build:*)` | `Bash(./mvnw verify:*)` |
| `Bash(./gradlew test:*)` | `Bash(./mvnw test:*)` |
| `Bash(./gradlew formatJava:*)` | `Bash(./mvnw spotless:apply:*)` |
| `Bash(./gradlew spotlessApply:*)` | `Bash(./mvnw spotless:apply:*)` |
| `Bash(./gradlew checkJavaFormat:*)` | `Bash(./mvnw spotless:check:*)` |
| `Bash(./gradlew spotlessCheck:*)` | `Bash(./mvnw spotless:check:*)` |
| `Bash(./gradlew bootRun:*)` | `Bash(./mvnw spring-boot:run:*)` |
| `Bash(./gradlew *:*)` | `Bash(./mvnw *:*)` (catch-all, if present) |

### 7. Verify

- Run `./mvnw --version` in the target to confirm the wrapper resolves.
- Run `./mvnw verify` to confirm build + test + spotless pass.
- If either fails, report to the user with the exact command and output; do not silently retry with different parameters.

## Upgrade Mode

### 1. Identify What Changed

**First, auto-detect target metadata.** Do not ask the user for values that can be inferred from the target; only prompt if inference fails.

| Value | Detection order |
|---|---|
| Project name | 1. Parse `CLAUDE.md` `## Project Overview` first non-empty line as `<name>: <description>`; 2. **[Go]** `go.mod` `module <path>` (last path segment); **[Java]** `pom.xml` `<artifactId>` or `settings.gradle` `rootProject.name`; 3. target directory name. If any yields `{{PROJECT_NAME}}`, treat as unfilled and ask user. |
| Project description | 1. Same line, after `: `; 2. **[Java]** `pom.xml` `<description>` or `build.gradle` `description = '...'`; 3. `README.md` first heading line. If unfilled or `{{PROJECT_DESCRIPTION}}`, ask user. |
| Build tool **[Java]** | 1. `pom.xml` at target root → `maven`; 2. `build.gradle` or `build.gradle.kts` → `gradle`; 3. Both → ask which is authoritative. |

Upgrade **never switches stacks or build tools**. The Template Selection table fixed the stack; if the target is Gradle, keep Gradle; if Maven, keep Maven. Migrating between stacks or build tools is out of scope — the user must start a fresh Init Mode run for that.

**Second, auto-detect which tools the target uses.** Per the Tool Surfaces table, presence of each tool's `agents/` directory is the signal:

| Tool | Present in target if... |
|---|---|
| Claude Code | `.claude/agents/` exists |
| Copilot CLI | `.github/agents/` exists |
| OpenCode | `.opencode/agents/` exists |
| Junie CLI | `.junie/agents/` exists |

Record the set as `<target-tools>` and report it to the user before proceeding: `Detected tools: claude, junie. To add another tool, create its agents/ directory first (see below) and re-run.` This single line prevents the surprise of a user re-running `/seed` to change their tool set and finding nothing happens.

Upgrade Mode only diffs and pushes to tool surfaces in `<target-tools>`. A tool absent from the target is treated as a deliberate opt-out — never add it.

**To add a tool surface to an existing target:** create an empty `agents/` directory marker before running `/seed` — for example, `mkdir -p <target>/.junie/agents` to opt Junie in, or `mkdir -p <target>/.github/agents` for Copilot. Auto-detection then sees the tool as present, missing-scaffolding fills its files as new-copy, and subsequent runs diff it normally.

**Third, check for missing scaffolding.** A target seeded by an older version of this command may be missing files within a tool surface that *is* in `<target-tools>`, or missing tool-agnostic files entirely. For each item in Init Mode Step 2 and Step 4 that is **not** gated by a tool absent from `<target-tools>`, if the target is missing it, mark as **new-copy** (follow Init Mode rules for that item using the auto-detected values above).

Common missing-scaffolding cases (pre-fix targets):
- No `CLAUDE.md` at target root
- No `docs/ddd-principles.md`, `docs/tdd-principles.md`, or `docs/testing-principles.md`
- No `scripts/handoff.py` alongside an existing `schemas/scratch/` (handoff access tool added in a later template version)
- Missing files within a present tool surface (e.g., `.junie/agents/` exists but `.junie/config.json` was added in a later template version)
- No `.claude/settings.json` or `.claude/hooks/` alongside an existing `.claude/agents/` (continuation guard added in a later template version)

**Fourth, diff each category** between `<template>` and the target project. Skip categories whose **Required tool** column lists a tool absent from `<target-tools>`.

| Category | Required tool | Template | Target |
|---|---|---|---|
| Rules file | — | `CLAUDE.md` | `<project>/CLAUDE.md` |
| Skills | — | `.claude/skills/*/SKILL.md` | `<project>/.claude/skills/*/SKILL.md` |
| Claude Code agents | `claude` | `.claude/agents/*.md` | `<project>/.claude/agents/*.md` |
| Copilot agents | `copilot` | `.github/agents/*.agent.md` | `<project>/.github/agents/*.agent.md` |
| OpenCode agents | `opencode` | `.opencode/agents/*.md` | `<project>/.opencode/agents/*.md` |
| Junie agents | `junie` | `.junie/agents/*.md` | `<project>/.junie/agents/*.md` |
| Junie config | `junie` | `.junie/config.json` | `<project>/.junie/config.json` |
| Templates | — | `.claude/templates/*.md` | `<project>/.claude/templates/*.md` |
| Settings | — | `.claude/settings.local.json` | `<project>/.claude/settings.local.json` |
| Agent-teams settings | `claude` | `.claude/settings.json` | `<project>/.claude/settings.json` |
| Hooks | `claude` | `.claude/hooks/*.sh` | `<project>/.claude/hooks/*.sh` |
| Scratch schemas | — | `schemas/scratch/*.json` | `<project>/schemas/scratch/*.json` |
| Harness scripts | — | `scripts/{handoff,test_handoff,score-change}.py` | `<project>/scripts/` — push verbatim, preserve executable bits |
| Extractor tests | — | `scripts/test_score_change.py` | `<project>/scripts/test_score_change.py` — informational diff only; fixtures are layout-coupled, the target's version is authoritative |
| Extractor config | — | `scripts/layout.toml` | `<project>/scripts/layout.toml` — informational diff only; the target's module rules are authoritative |
| Principles docs | — | `docs/{ddd,tdd,testing}-principles.md`, `docs/agentic-harness.md` | `<project>/docs/{ddd,tdd,testing}-principles.md`, `<project>/docs/agentic-harness.md` |
| Doc scaffolding | — | `docs/{prd,system-design,ubiquitous-language,documentation-standards}.md`, `docs/adr/README.md` | `<project>/docs/...` — structural diff only; target's filled-in requirements and architecture are authoritative |
| Gitignore | — | `.gitignore` | `<project>/.gitignore` — ensure `.scratch/` is present (append if missing); never remove target entries |
| Generic ADRs | — | `docs/adr/YYYY-MM-DD-*.md` (template-authored decisions only) | `<project>/docs/adr/YYYY-MM-DD-*.md` — push template ADRs by filename match; target ADRs not in template are always preserved. No filename match → check the target for a renamed or adapted equivalent by title; found → Conflict (ask), never copy a duplicate |

Build files are not diffed — the target's build config is authoritative and seed never pushes changes to it. **[Go]** `go.mod`, `go.sum`, `Makefile`. **[Java]** `build.gradle`, `settings.gradle`, `gradlew*`, `gradle/`, or `pom.xml`, `mvnw*`, `.mvn/`. When a pushed script change needs build wiring (a new test file, a renamed target), report the exact line for the user to add — do not edit the build file without asking.

Doc scaffolding diff is **structural only**: push template changes to section headers, `<!-- AGENT: ... -->` comments, and table stubs; never overwrite filled-in requirements, architecture, or ADRs. Target's domain content wins every conflict.

Generic ADR diff: only push ADRs that originated in the template (decisions about workflow architecture, agent pipelines, schemas, etc. — not project-specific decisions). Match by filename. Target ADRs that aren't in the template are **always preserved** — those are the target project's own architectural decisions and seed must never overwrite them.

Scratch schemas (`schemas/scratch/*.json`) follow the same diff-and-merge logic as skills: push template changes verbatim. The target may have added downstream schemas (e.g. project-specific record types) or renamed the `$id` namespace — those are preserved.

Agent-teams settings and hooks push as a pair. Push hook scripts verbatim, preserving the executable bit. Merge `settings.json` at key level: push the template's `env` flag and `SendMessage` `PreToolUse` entry, preserve keys the target added. Never push one file of the pair without the other.

### 2. Classify Differences

For every difference, classify. Decide by one principle: the template owns generic structure, the target owns its domain, and on conflict the target's domain content wins. The buckets below list the common cases; when a diff matches none, fall back to that principle.

**Template is newer** (push to target):
- New skill not in target
- Improved agent structure (new section, better process, added tool)
- New template file
- New permission in settings
- Structural fixes (consistency, parity)

**Authoritative push** (overwrite target; no domain content preserved):
- `docs/ddd-principles.md` — must be byte-equivalent to the template
- `docs/tdd-principles.md` — must be byte-equivalent to the template
- `docs/testing-principles.md` generic sections only (see Merge Protocol — language-specific sections below the generic block are preserved)
- Harness scripts (`scripts/handoff.py`, `test_handoff.py`, `score-change.py`) — template-owned tooling. `test_score_change.py` is layout-coupled: the target's fixtures are authoritative, like `layout.toml`.

**Target has customization** (preserve):
- Filled-in `<!-- PROJECT -->` blocks
- `{{PROJECT_NAME}}` already replaced with real name
- Real requirement IDs (`REQ-DL-*`) replacing `REQ-XX-*`
- Real file paths replacing generic paths
- Security Context filled in
- Threat model added
- Project-specific config references
- Trimmed tool-surface prose (a claude-only target dropping cross-tool references is an opt-out, not drift)
- CLAUDE.md sections marked "Preserve target" in the Merge Protocol section classification table below

**Conflict** (ask user):
- Both template and target changed the same section
- Target removed something the template still has
- Target added content to a section the template also changed

### 3. Present Plan

Show the user what will change:

```
## Seed Plan: <project-name>  (template: <template>)

### Push (template improvements)
1. **[category] file** — description
   ```diff
   ...
   ```

### Preserve (domain customizations)
- **file** — what's preserved

### Conflicts
1. **file** — both changed. Show both versions, ask which to keep.

### New Files
- **file** — new in template, will be copied

### Summary
- X files to update
- Y customizations preserved
- Z conflicts to resolve
- W new files to copy
```

### 4. Apply

After user confirms:
1. Apply template improvements, preserving domain content.
2. For new skills/agents, copy directly (no domain content to preserve).
3. For upgraded files, merge: keep domain sections, update generic sections.
4. For missing scaffolding (from Step 1), copy as in Init Mode and fill placeholders using auto-detected values. **Globbed Init Step 2 items (e.g., `.claude/agents/*.md`) iterate per-file**: if any specific template file is missing in the target, copy it. An empty marker directory therefore gets fully populated from the template.
5. **Maven targets:** every push that includes a Gradle command (`./gradlew <task>`) must be translated to the Maven equivalent from the mapping table in "Build Tool Variant: Maven" Step 6 before writing. Applies to `CLAUDE.md` Build Commands/Quality Gate, `.claude/settings.local.json` permissions, and any agent or skill that lists build commands. Do not write Gradle commands into a Maven target.
6. Verify: grep the target for `{{PROJECT_NAME}}` and `{{PROJECT_DESCRIPTION}}`. Any hit outside files listed in `audit-consistency` Section 5 means a placeholder was left unfilled — report to the user.
7. Run the target's `audit-agents` skill to verify consistency.

## Merge Protocol for Upgraded Files

When updating a file that has domain customizations:

1. **Section-level merge**: Compare by `##` headings, not line-by-line.
2. **Preserve blocks between `<!-- PROJECT -->` markers**: Never overwrite.
3. **Preserve filled placeholders**: If `{{PROJECT_NAME}}` is already `home-status-page`, keep it.
4. **Preserve added sections**: If the target added a `## Security Context` section, keep it.
5. **Update generic sections**: If the template improved `## Review Process` steps, push the update.
6. **Add new sections**: If the template added a new `## Skills` reference, add it.
7. **Never delete target-only content**: If the target has extra sections not in template, keep them.

### CLAUDE.md section classification

CLAUDE.md mixes domain content with generic workflow content. Apply per-section rules:

| Section | Treatment |
|---|---|
| `## Project Overview` | Preserve target (real project name/description replaces `{{PROJECT_NAME}}: {{PROJECT_DESCRIPTION}}`) |
| `## Toolchain` | Preserve target (project-specific versions) |
| `## Build Commands` | Preserve target (project-specific build targets) |
| `## Lint Troubleshooting` **[Go]** | Preserve target if customized; push template improvements if target is still generic |
| `## Testing Strategy` body | Preserve target if customized; push template structure if target is still generic |
| `## Architecture` | Preserve target |
| `## Agent Usage` | Push template (generic workflow) |
| Skills table (under `### Skills`) | Push template — must list every `.claude/skills/` directory |
| `## Writing Standards` | Push template (generic) |
| `## Quality Gate` | Push template structure; preserve target's project-specific commands |
| `## Scratch Directory` | Push template (generic) |
| `## Documentation Updates` | Push template (generic) |
| `## Commit Convention` | Push template (generic) |

### Principles docs (authoritative push)

- `docs/ddd-principles.md` and `docs/tdd-principles.md`: overwrite target with template content. No merge. Target changes are treated as drift.
- `docs/testing-principles.md`: push generic sections (per `audit-consistency` Section 10 list); preserve language-specific content below the generic block.

## Files That Stay in the Monorepo Only

Do NOT copy these to the target:
- The monorepo root's `.claude/skills/` (this skill, `harvest`, `audit-consistency`, `deps-upgrade`, `research-update`, `history-update`, `harness-stats-setup`) — reference maintenance tooling, not harness machinery
- The monorepo root's `CLAUDE.md`, `README.md`, `docs/`, and `docs/adr/` — the reference's own documentation and decision log
