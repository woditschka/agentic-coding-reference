---
name: init
description: >-
  Scaffold the project-owned files a new harness consumer commits — its
  CLAUDE.md rules file, .claude/settings.json, scripts/layout.toml (with the
  manifest channel declaration), the docs/ brief roster, and the .gitignore
  runtime block. Detects the target's stack (Go or Java Spring Boot) from its
  build marker. Does NOT install the runtime; that is materialize. Never
  overwrites a project file that already exists. Load when the user invokes
  `/init <project-path>`.
compatibility:
  - claude-code
metadata:
  version: "1.0"
  author: team
---

# Init

Scaffold the **project-owned** files a harness consumer commits. Runs from the monorepo root; `/harness` is the source. Init lays down only what the project owns and edits — it never installs the runtime. The runtime (skills, agents, hooks, schemas, engines) is gitignored and delivered separately by `materialize`. A greenfield setup runs init once, then materialize once — or just `/seed`, the wrapper that does both.

**Usage:** `/init <project-path>` (e.g., `/init ../widget`)

## Precondition: the target already has a build marker

Init does **not** generate build files. The stack is detected *from* the target's existing build marker — the same detection `materialize` and `bootstrap` use — so the target must already be a buildable project skeleton:

| Marker in target | Stack (`<stack>`) |
|---|---|
| `go.mod` | `go` |
| `build.gradle`, `build.gradle.kts`, or `pom.xml` | `java-spring-boot` |
| More than one marker | Ask which is authoritative |
| No marker | **Stop.** Tell the user to create the build skeleton first (`go mod init <module>`, `gradle init`, or Spring Initializr) and re-run. |

The build skeleton is the developer's own choice of toolchain; init scaffolds the harness contract on top of it.

## What init lays down (all project-owned, all committed)

Init overlays `harness/init/core/` then `harness/init/stacks/<stack>/` (stack wins on overlap), materializes the `docs/` roster from the doctor templates, and appends the `.gitignore` runtime block. Every write is gap-filling: a file that already exists in the target is left untouched.

| Source | Target | Filled with |
|---|---|---|
| `harness/init/core/.claude/settings.json` | `.claude/settings.json` | — (agent-teams flag + hook registration; identical across stacks) |
| `harness/init/stacks/<stack>/CLAUDE.md` | `CLAUDE.md` | `{{PROJECT_NAME}}`, `{{PROJECT_DESCRIPTION}}` |
| `harness/init/stacks/<stack>/scripts/layout.toml` | `scripts/layout.toml` | — (carries `[harness] channel = "manifest"`; module rules are the project's to adjust) |
| `harness/core/.claude/skills/doctor/templates/*` | `docs/` roster (see below) | `{{PROJECT_NAME}}`, `{{HARNESS_VERSION}}` |
| `harness/init/core/gitignore-runtime.txt` | appended to `.gitignore` | — (the runtime paths + `.scratch/`) |

The `docs/` roster maps the doctor templates to project briefs; `adr-README.md` is renamed to `docs/adr/README.md`:

| Template | Target |
|---|---|
| `prd.md` | `docs/prd.md` |
| `system-design.md` | `docs/system-design.md` |
| `ubiquitous-language.md` | `docs/ubiquitous-language.md` |
| `testing-principles.md` | `docs/testing-principles.md` |
| `architecture-principles.md` | `docs/architecture-principles.md` |
| `adr-README.md` | `docs/adr/README.md` |

The briefs are **project-owned defaults** the moment they land (harness-project API: `docs/harness-project-api.md`). The project rewrites their values to fit its team; the doctor and `brief-review` guide that. The consumer's `docs/adr/` starts with only the README stub — the decision log carries the project's decisions, not the harness's.

## Migrating an existing copy-channel project

A project that predates the manifest channel commits its runtime and has no `[harness]` table. `init` migrates it additively, never overwriting a project file:

- **Injects the `[harness]` table** into an existing `scripts/layout.toml` that lacks it (the chosen `channel`, plus `spec_version`, `tools`, `extensions`) — append-only, no existing key touched. This is the one exception to "never modify an existing project file": keys the doctor requires, added without altering the project's own rules. The untrack step below applies only when the chosen channel is `manifest`; `copy` keeps the runtime committed.
- **Reports the untrack command.** The appended `.gitignore` block ignores the runtime, but files already committed stay tracked. `init.sh` detects them and prints the exact command — it never runs git against your repo:
  ```
  git -C <target> rm -r --cached --ignore-unmatch <runtime paths>
  ```
  `--ignore-unmatch` keeps it robust for a partial-tool project (one missing some tool surfaces). Migration order: `init` → run that `git rm --cached` → `materialize` → commit. The runtime is then untracked and the doctor's `channel` check passes.

**Switching channel later.** `init` injects the `[harness]` table only when it is absent, so it never flips a channel already declared. To switch an existing project, edit `[harness] channel` by hand and adjust `.gitignore` — add the runtime block for `manifest` (then run the untrack), or remove it for `copy` (then commit the runtime).

## Process

1. Read the target path from `$ARGUMENTS`. Verify it exists.
2. **Detect the stack** from the build marker (table above). If none, stop with the create-build-skeleton instruction. If more than one, ask which is authoritative.
3. **Gather identity.** Infer where possible, ask only on a miss:
   - Project name: Go `go.mod` `module <path>` (last segment); Java `settings.gradle` `rootProject.name`, `pom.xml` `<artifactId>`, or the target directory name. Confirm with the user.
   - Project description: ask the user (one sentence).
   - Tool surfaces: ask which AI tools to install — **claude** is always on; **copilot**, **opencode**, **junie** are optional. Default offered: all four. The chosen set goes to `[harness] tools`; `materialize` installs only these and never adds one on upgrade.
   - Channel: ask whether the runtime is **manifest** (default — materialized and gitignored, not committed; keeps the repo lean and pins the runtime to a source) or **copy** (committed into the repo; keeps the harness self-contained and version-controlled). The choice goes to `[harness] channel`.
4. Compute `<harness-version>`: `git rev-parse --short HEAD` in this reference repo (stamps the briefs' provenance comments).
5. **Run the scaffolder** (tools-csv omitted = all four; channel omitted = manifest):
   ```bash
   harness/init.sh <stack> <target-path> "<project-name>" "<project-description>" "<harness-version>" "<tools-csv>" "<channel>"
   ```
   It reports how many files it created and how many pre-existing ones it kept. Init never overwrites a project file, so re-running it on a partially-set-up target only fills gaps.
6. **Verify** no placeholder leaked: grep the target's `CLAUDE.md` and `docs/` for `{{` — any hit is a fill that init.sh did not cover; report it.
7. Print the next steps below.

## Next steps (render to the user)

```
Scaffolded the project-owned files for <project-name> (<stack>).

Install the runtime, then validate:
1. Materialize the harness runtime:
     harness/materialize.sh <stack> <target-path>
   (or run harness/bootstrap.sh to materialize every detected target.)
   Under the copy channel, commit the runtime afterward; under manifest it is
   gitignored.
2. Run the doctor to validate the docs/ roster:
     python3 .claude/skills/doctor/scripts/brief_doctor.py check
3. Fill in your briefs — docs/prd.md (requirements), docs/system-design.md
   (architecture), and review docs/testing-principles.md and
   docs/architecture-principles.md; they are yours now.
4. Review scripts/layout.toml — adjust the module rules and prod_roots to your
   package layout. [harness] channel = "<channel>" — manifest materializes the
   runtime gitignored (not committed); copy commits it into the repo.
5. Fill the Security Context in docs/system-design.md — the security profile
   (inputs, outputs, services, credentials, runtime). The security-reviewer
   reads it from the brief, not from the agent.
6. Run /brief-review for the advisory pass once the briefs have content.
```

## What init does NOT do

- **The runtime.** Skills, agents, hooks, `schemas/scratch/`, and the `scripts/*.py` engines are materialized by `materialize`, gitignored, never scaffolded here.
- **Build files.** `go.mod`, `Makefile`, `build.gradle`, `pom.xml`, wrappers — the target brings its own (they are how the stack is detected).
- **Upgrades.** Init only fills gaps in a project's owned files (and injects the one doctor-required `[harness]` table; see Migrating above). Raising an existing project to a newer harness is a re-`materialize` (runtime) plus the doctor/`brief-review` loop (briefs) — there is no merge step under the manifest channel.
- **Tool-surface selection.** Init scaffolds the stack-agnostic project files; the set of AI tools a project exposes is decided by which agent directories `materialize` delivers.
