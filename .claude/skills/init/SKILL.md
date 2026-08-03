---
name: init
description: >-
  Scaffold the project-owned files a new harness consumer commits — its
  CLAUDE.md rules file, .claude/settings.json, scripts/layout.toml (with the
  channel declaration — copy by default), the docs/ brief roster, and the
  .gitignore block. Detects the target's stack (Go, Java Spring Boot, or the
  generic fallback) from its build marker. Does NOT install the runtime; that is materialize. Never
  overwrites a project file that already exists. Load when the user invokes
  `/init <project-path>`.
compatibility:
  - claude-code
metadata:
  version: "1.0"
  author: team
---

# Init

Scaffold the **project-owned** files a harness consumer commits. Runs from the monorepo root; `/harness` is the source. Init lays down only what the project owns and edits — it never installs the runtime. The runtime (skills, agents, hooks, schemas, engines) is delivered separately by `materialize`: committed into the repo under the **copy** channel (the default), gitignored under **manifest**, or — under **marketplace** — the tool surfaces ship as a plugin and only the engine sliver materializes project-side (gitignored). A greenfield setup runs init once, then materialize once — or just `/materialize`, which runs `/init` first when the project-owned files are missing.

**Usage:** `/init <project-path> [channel]` (e.g., `/init ../widget`; `/init ../widget marketplace` on a marketplace install)

## Precondition: the target already has a build marker

Init does **not** generate build files. The stack is detected *from* the target's existing build marker — the same detection `materialize` and `materialize-samples` use — so the target must already be a buildable project skeleton. This table is the single documented copy; the code home is `detect_stack` in `harness/registry.py`:

| Marker in target | Stack (`<stack>`) |
|---|---|
| `go.mod` | `go` |
| `build.gradle`, `build.gradle.kts`, or `pom.xml` | `java-spring-boot` |
| More than one marker | Ask which is authoritative |
| No recognized marker | `generic` — the technology-free fallback stack. The project keeps its own build system; it binds the lifecycle verbs in `scripts/stack.sh`. |

The build skeleton is the developer's own choice of toolchain; init scaffolds the harness contract on top of it. A `go` or `java-spring-boot` marker selects an opinionated stack; anything else lands on `generic`, where the binding to the project's technology is the `scripts/stack.sh` verb functions the owner fills in.

## What init lays down (all project-owned, all committed)

Init overlays `harness/init/core/` then `harness/init/stacks/<stack>/` (stack wins on overlap), materializes the `docs/` roster from the doctor templates, and appends the `.gitignore` runtime block. Every write is gap-filling: a file that already exists in the target is left untouched.

| Source | Target | Filled with |
|---|---|---|
| `harness/init/core/.claude/settings.json` | `.claude/settings.json` | — (agent-teams flag + hook registration; identical across stacks) |
| `harness/init/stacks/<stack>/CLAUDE.md` | `CLAUDE.md` | `{{PROJECT_NAME}}`, `{{PROJECT_DESCRIPTION}}` |
| `harness/init/stacks/<stack>/scripts/layout.toml` | `scripts/layout.toml` | — (carries `[harness] channel = "copy"` by default; module rules are the project's to adjust) |
| `harness/core/.claude/skills/doctor/templates/*` | `docs/` roster (see below) | `{{PROJECT_NAME}}`, `{{HARNESS_DATE}}` |
| `harness/init/core/gitignore-runtime.txt` | appended to `.gitignore` | — (manifest: the runtime paths + `.scratch/`; copy: only `.scratch/`) |

The `docs/` roster maps the doctor templates to project briefs; `adr-README.md` is renamed to `docs/adr/README.md`:

| Template | Target |
|---|---|
| `prd.md` | `docs/prd.md` |
| `system-design.md` | `docs/system-design.md` |
| `ubiquitous-language.md` | `docs/ubiquitous-language.md` |
| `testing-principles.md` | `docs/testing-principles.md` |
| `architecture-principles.md` | `docs/architecture-principles.md` |
| `security-principles.md` | `docs/security-principles.md` |
| `adr-README.md` | `docs/adr/README.md` |

The briefs are **project-owned defaults** the moment they land (harness-project API: `docs/harness-project-api.md`). The project rewrites their values to fit its team; the doctor and `audit-docs` guide that. The consumer's `docs/adr/` starts with only the README stub — the decision log carries the project's decisions, not the harness's.

## Channel: detect, never prompt

The channel is **resolved, not asked** — that question was friction on every onboard. Resolution order (step 3 below applies it):

1. **Channel passed on the invocation** (`/init <path> marketplace`) → use it verbatim; an explicit argument is a declaration, not a prompt. This and rule 2 are the only ways `marketplace` arrives — its gitignored tree mirrors manifest, so the detection rules below infer `manifest`. On that inference a later `/materialize` installs the full runtime beside the plugin. The marketplace-setup flow passes the argument here.
2. **`[harness] channel` already declared** in the target's `scripts/layout.toml` → use it verbatim, over rule 1 too: on a conflicting argument `init.py` fails loud instead of flipping or misreporting; switching stays manual (§ below).
3. **No `[harness]` table, runtime files git-tracked** (e.g. `git ls-files .claude/skills` returns matches) → the project already commits its runtime → **copy**.
4. **No `[harness]` table, runtime gitignored** (a runtime block in `.gitignore`, or the paths are untracked-and-ignored) → **manifest**.
5. **Greenfield** (no runtime present at all) → **copy** (the default — self-contained and version-controlled).
6. **Conflicting signals** (some runtime tracked, some ignored) → ask the user, default copy.

Init passes the resolved channel to `init.py`, which injects the `[harness]` table only when absent — append-only, no existing key touched. This is the one exception to "never modify an existing project file": keys the doctor requires, added without altering the project's own rules.

**Switching channel is manual** (it is rare, and auto-flipping a project's git layout is surprising). `/materialize` respects the declared channel and never changes it. The switching procedures — all three directions — are owned by the Adoption Guide § Distribution channels; this skill only resolves the channel at scaffold time.

## Process

1. Read the target path — and the optional channel argument (§ Channel, rule 1) — from `$ARGUMENTS`. Verify the path exists.
2. **Detect the stack** from the build marker (table above). No recognized marker lands on `generic`; the owner binds the verbs in `scripts/stack.sh`. If more than one, ask which is authoritative.
3. **Gather identity.** Infer where possible, ask only on a miss:
   - Project name: Go `go.mod` `module <path>` (last segment); Java `settings.gradle` `rootProject.name`, `pom.xml` `<artifactId>`, or the target directory name. Confirm with the user.
   - Project description: ask the user (one sentence).
   - Tool surfaces: ask which AI tools to install — **claude** is always on; **copilot**, **opencode**, **junie** are optional. Default offered: all four. The chosen set goes to `[harness] tools`; `materialize` installs only these and never adds one on upgrade.
   - Channel: **resolve, do not ask** — apply the resolution order under § Channel: detect, never prompt. The resolved value goes to `[harness] channel`.
4. **Harness date** stamps the briefs' provenance comments (`<!-- harness: <date> -->`). Leave it to `init.py`, which reads `harness/VERSION-DATE` — the release date written by `release-version`. The artifact version itself stays a plugin/marketplace concern; the optional harness-version argument remains only for back-compat.
5. **Run the scaffolder** (harness-version omitted; tools-csv omitted = all four; channel omitted = copy):
   ```bash
   harness/init.py <stack> <target-path> "<project-name>" "<project-description>" "" "<tools-csv>" "<channel>"
   ```
   It reports how many files it created and how many pre-existing ones it kept. Init never overwrites a project file, so re-running it on a partially-set-up target only fills gaps.
6. **Verify** the scaffold: `init.py` self-checks its own fills and exits non-zero on an unfilled token — report any failure verbatim. Intentional `{{FILL}}` rows (the consumer's to complete) are not failures.
7. Print the next steps below.

## Next steps (render to the user)

```
Scaffolded the project-owned files for <project-name> (<stack>).

Install the runtime, then validate:
1. Install the runtime: run /materialize <project-path> from the reference root
   (skip when /materialize invoked this scaffold — it installs the runtime next).
   Under the copy channel, commit the runtime afterward; under manifest it is
   gitignored.
2. Run the doctor to validate the docs/ roster:
     python3 scripts/doctor.py check
3. Fill in your briefs — docs/prd.md (requirements), docs/system-design.md
   (architecture), and review docs/testing-principles.md and
   docs/architecture-principles.md; they are yours now. On a project that
   already has code, run /derive-briefs inside it first — it drafts them
   from the source, each statement marked derived, confirmed, or not
   recoverable.
4. Review scripts/layout.toml — adjust the module rules and prod_roots to your
   package layout. [harness] channel = "<channel>" — manifest materializes the
   runtime gitignored (not committed); copy commits it into the repo.
5. Fill the Security Context in docs/system-design.md — the security profile
   (inputs, outputs, services, credentials, runtime). The security-reviewer
   reads it from the brief, not from the agent.
6. Run /audit-docs once the briefs have content — it runs the doctor (structure)
   then the judgment review, auditing each doc on its own and against the others.
7. Start your first slice: open the project in your tool and describe the
   feature you want — or run /next for a recommendation from PRD coverage.
```

## What init does NOT do

- **The runtime.** Never scaffolded here. `materialize` delivers it: committed under copy, gitignored under manifest. Under marketplace the tool surfaces ship as the plugin; only the engine sliver materializes, gitignored.
- **Build files.** `go.mod`, `Makefile`, `build.gradle`, `pom.xml`, wrappers — the target brings its own (they are how the stack is detected).
- **Upgrades.** Init only fills gaps in a project's owned files (and injects the one doctor-required `[harness]` table; see "Channel: detect, never prompt" above). Raising an existing project to a newer harness is a re-`materialize` (runtime) plus the doctor/`audit-docs` loop (briefs) — there is no merge step on either channel (copy re-commits the replaced runtime; manifest leaves it gitignored).
- **Tool-surface installation.** Init only *declares* the tool set in `[harness] tools` (step 3). Installing those surfaces — the per-tool agent directories — is `materialize`'s job.
