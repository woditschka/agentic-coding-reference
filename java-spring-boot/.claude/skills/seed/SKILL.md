---
name: seed
description: >-
  Push this template's setup into a target project. Init mode scaffolds a new
  empty target (Gradle default, Maven via start.spring.io); upgrade mode
  raises the bar on an existing project by merging template improvements
  while preserving domain customizations. Load when the user invokes
  `/seed <project-path>`.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

# Seed

Push this template's setup into a target project.

**Usage:** `/seed <project-path>` (e.g., `/seed ../new-project`)

## Modes

Detect automatically based on target state:

| Target State | Mode | Behavior |
|---|---|---|
| No `.claude/` directory | **Init** | Full copy, ask for project details |
| Has `.claude/` but outdated | **Upgrade** | Diff and merge, preserve domain content |

## Init Mode

### 1. Gather Project Details

Ask the user for:

| Field | Placeholder / Value | Example |
|---|---|---|
| Project name | `{{PROJECT_NAME}}` | `home-status-page` |
| Project description | `{{PROJECT_DESCRIPTION}}` | `Spring Boot CLI tool for home infrastructure` |
| Build tool | `gradle` (default) or `maven` | `maven` |

Gradle is the canonical build for this template. If the user picks `maven`, follow the "Build Tool Variant: Maven" section below when copying.

### 2. Copy Structure

Copy these directories and files from this template to the target:

```
CLAUDE.md                  (root rules file; placeholders filled in step 3)

.claude/
├── agents/*.md          (all agents including README.md)
├── skills/*/SKILL.md    (all skills except `seed` and `harvest` — those stay in template)
├── templates/*.md        (all templates)
└── settings.local.json

.opencode/
└── agents/*.md           (all agents)

.github/
└── agents/*.agent.md     (Copilot agents)
```

**Build files (variant-dependent):**
- Gradle (default): copy `build.gradle`, `settings.gradle`, `gradlew`, `gradlew.bat`, `gradle/` directory.
- Maven: skip all Gradle files. See "Build Tool Variant: Maven" below.

### 3. Fill Placeholders

Replace in all copied files:
- `{{PROJECT_NAME}}` → user-provided project name
- `{{PROJECT_DESCRIPTION}}` → user-provided description

### 4. Copy Documentation Scaffolding

If the target has no `docs/` directory, copy the template structure:

```
docs/
├── prd.md
├── system-design.md
├── documentation.md
├── ddd-principles.md
├── tdd-principles.md
├── testing-principles.md
└── adr/
    └── README.md
```

Fill `{{PROJECT_NAME}}` and `{{PROJECT_DESCRIPTION}}` in these files too.

### 5. Update .gitignore

Ensure the target's `.gitignore` includes:
```
.scratch/
```

If no `.gitignore` exists, copy the template's `.gitignore`.
If one exists, append `.scratch/` if missing.

**Maven variant only:** replace `build/` with `target/` in the copied `.gitignore` (Gradle build directory → Maven build directory). Remove any `!gradle/wrapper/gradle-wrapper.jar` line.

### 6. Prompt for Security Context

After copying, remind the user:

```
Next steps:
1. Review CLAUDE.md — confirm the Toolchain, Build Commands, and Testing Strategy sections match your project
2. Fill in the Security Context in .claude/agents/security-reviewer.md,
   .opencode/agents/security-reviewer.md, and .github/agents/security-reviewer.agent.md
   (replace the <!-- PROJECT --> comment with your application's security profile)
3. Review docs/prd.md and fill in your requirements
4. Review docs/system-design.md and fill in your architecture
5. Run /lint-docs to validate documentation coherence
```

## Build Tool Variant: Maven

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
| Project name | 1. Parse `CLAUDE.md` `## Project Overview` first non-empty line as `<name>: <description>`; 2. `pom.xml` `<artifactId>`; 3. `settings.gradle` `rootProject.name`; 4. target directory name. If any yields `{{PROJECT_NAME}}`, treat as unfilled and ask user. |
| Project description | 1. Same line, after `: `; 2. `pom.xml` `<description>`; 3. `build.gradle` `description = '...'`. If unfilled or `{{PROJECT_DESCRIPTION}}`, ask user. |
| Build tool | 1. `pom.xml` at target root → `maven`; 2. `build.gradle` or `build.gradle.kts` → `gradle`; 3. Both → ask which is authoritative; 4. Neither → treat as empty and fall through to Init Mode. |

Upgrade **never switches build tools**. If the target is Gradle, keep Gradle; if Maven, keep Maven. Migrating between build tools is out of scope — the user must start a fresh Init Mode run for that.

**Second, check for missing scaffolding.** A target seeded by an older version of this command may be missing entire files or directories that Init Mode now copies. For each item in Init Mode Step 2 and Step 4, if the target is missing it, mark as **new-copy** (follow Init Mode rules for that item using the auto-detected values above).

Common missing-scaffolding cases (pre-fix targets):
- No `CLAUDE.md` at target root
- No `.github/agents/` directory
- No `docs/ddd-principles.md` or `docs/tdd-principles.md`

**Third, diff each category** between the template and the target project:

| Category | Template | Target |
|---|---|---|
| Rules file | `CLAUDE.md` | `<project>/CLAUDE.md` |
| Skills | `.claude/skills/*/SKILL.md` | `<project>/.claude/skills/*/SKILL.md` |
| Claude Code agents | `.claude/agents/*.md` | `<project>/.claude/agents/*.md` |
| OpenCode agents | `.opencode/agents/*.md` | `<project>/.opencode/agents/*.md` |
| Copilot agents | `.github/agents/*.agent.md` | `<project>/.github/agents/*.agent.md` |
| Templates | `.claude/templates/*.md` | `<project>/.claude/templates/*.md` |
| Settings | `.claude/settings.local.json` | `<project>/.claude/settings.local.json` |
| Principles docs | `docs/{ddd,tdd,testing}-principles.md` | `<project>/docs/{ddd,tdd,testing}-principles.md` |
| Doc scaffolding | `docs/{prd,system-design,documentation}.md`, `docs/adr/` | `<project>/docs/{prd,system-design,documentation}.md`, `<project>/docs/adr/` — structural diff only; target's filled-in requirements, architecture, and ADRs are authoritative |
| Build files | `build.gradle`, `settings.gradle`, `gradlew*`, `gradle/` (Gradle) — or `pom.xml`, `mvnw*`, `.mvn/` (Maven) | Same paths at `<project>/` root. Diff is informational only — target's build config is authoritative, never auto-pushed. |

### 2. Classify Differences

For every difference, classify:

**Template is newer** (push to target):
- New skill not in target
- Improved agent structure (new section, better process)
- New template file
- New permission in settings
- Structural fixes (consistency, parity)

**Authoritative push** (overwrite target; no domain content preserved):
- `docs/ddd-principles.md` — must be byte-equivalent to root
- `docs/tdd-principles.md` — must be byte-equivalent to root
- `docs/testing-principles.md` generic sections only (see Merge Protocol — language-specific sections below the generic block are preserved)

**Target has customization** (preserve):
- Filled-in `<!-- PROJECT -->` blocks
- `{{PROJECT_NAME}}` already replaced with real name
- Real requirement IDs (`REQ-DL-*`) replacing `REQ-XX-*`
- Real file paths replacing generic paths
- Security Context filled in
- Threat model added
- Project-specific config references
- CLAUDE.md sections marked "Preserve target" in the Merge Protocol section classification table below

**Conflict** (ask user):
- Both template and target changed the same section
- Target removed something the template still has
- Target added content to a section the template also changed

### 3. Present Plan

Show the user what will change:

```
## Seed Plan: <project-name>

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
4. For missing scaffolding (from Step 1), copy as in Init Mode and fill placeholders using auto-detected values.
5. **Maven targets:** every push that includes a Gradle command (`./gradlew <task>`) must be translated to the Maven equivalent from the mapping table in "Build Tool Variant: Maven" Step 6 before writing. Applies to `CLAUDE.md` Build Commands/Quality Gate, `.claude/settings.local.json` permissions, and any agent or skill that lists build commands. Do not write Gradle commands into a Maven target.
6. Verify: grep the target for `{{PROJECT_NAME}}` and `{{PROJECT_DESCRIPTION}}`. Any hit outside files listed in `audit-consistency` Section 5 means a placeholder was left unfilled — report to the user.
7. Run the `audit-agents` skill on the target to verify consistency.

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
| `## Build Commands` | Preserve target (project-specific Gradle/Make targets) |
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

## Files That Stay in Template Only

Do NOT copy these to the target:
- `.claude/skills/harvest/` — template management only
- `.claude/skills/seed/` — this skill; template management only
