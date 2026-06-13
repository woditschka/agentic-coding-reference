---
name: seed
description: >-
  Compatibility wrapper that sets up a harness consumer in one step: scaffold
  the project-owned files (delegates to `init`) and then install the gitignored
  runtime (delegates to `materialize`). Detects the target's stack (Go or Java
  Spring Boot) from its build marker. Kept so `/seed <project-path>` keeps
  working; new work can call `/init` and `harness/materialize.sh` directly.
compatibility:
  - claude-code
metadata:
  version: "3.0"
  author: team
---

# Seed

Seed is a **thin compatibility wrapper**. Since the harness became a single source (`/harness`) delivered over the manifest channel, the two halves of setup are separate operations:

| Half | Operation | What it produces |
|---|---|---|
| Project-owned files | `init` (`harness/init.sh`) | `CLAUDE.md`, `.claude/settings.json`, `scripts/layout.toml`, the `docs/` brief roster, the `.gitignore` runtime block — all committed |
| Runtime | `materialize` (`harness/materialize.sh`) | `.claude/skills`, agents, hooks, `schemas/scratch/`, the `scripts/*.py` engines — gitignored, never committed |

`/seed <project-path>` runs both, in order, so a single command still onboards a project. New work can call the two directly: `/init` for the project files, `harness/materialize.sh <stack> <target>` for the runtime.

**Usage:** `/seed <project-path>` (e.g., `/seed ../widget`)

## What changed from older seed

The pre-manifest `/seed` carried an Init mode (full copy of runtime + briefs), a Maven-Initializr build generator, and an Upgrade mode that diffed and merged a project's runtime against the template. All three are gone:

- **Runtime is no longer copied or merged** — it is materialized from `/harness` and gitignored. Upgrading is a re-`materialize`, never a merge.
- **Build files are a precondition, not generated** — the target brings its own build skeleton (`go mod init`, `gradle init`, Spring Initializr); the stack is detected from it.
- **Briefs are project-owned** — scaffolded once from the doctor templates by `init`, then evolved by the project under the doctor and `brief-review`. Seed never rewrites a brief.

To raise an existing project to a newer harness: re-run `harness/materialize.sh` (runtime) and let the project's own `doctor` and `brief-review` surface brief gaps. There is no seed "upgrade" anymore. To pull a downstream improvement back into the harness, use `harvest`.

## Process

1. Read the target path from `$ARGUMENTS`. Verify it exists.
2. **Detect the stack** from the build marker — the same detection `init` and `materialize` use:

   | Marker in target | Stack (`<stack>`) |
   |---|---|
   | `go.mod` | `go` |
   | `build.gradle`, `build.gradle.kts`, or `pom.xml` | `java-spring-boot` |
   | More than one marker | Ask which is authoritative |
   | No marker | **Stop.** The target needs a build skeleton first (`go mod init <module>`, `gradle init`, or Spring Initializr); seed does not generate one. |

3. **Run `init`.** Follow the `init` skill's process: gather identity (project name, description), compute `<harness-version>` (`git rev-parse --short HEAD` here), and run `harness/init.sh <stack> <target> "<name>" "<description>" "<harness-version>"`. This lays down the project-owned files and never overwrites an existing one.
4. **Migrating a copy-channel project?** If `init` prints an untrack NOTE (the target had committed runtime), run the exact `git rm -r --cached --ignore-unmatch …` command it printed before materializing. Greenfield targets print no NOTE — skip this step. See the `init` skill's "Migrating an existing copy-channel project".
5. **Run `materialize`** to install the runtime:
   ```bash
   harness/materialize.sh <stack> <target-path>
   ```
6. **Verify:**
   - Grep the target's `CLAUDE.md` and `docs/` for `{{` — any hit is an unfilled placeholder; report it.
   - Run the target's doctor: `python3 .claude/skills/doctor/scripts/brief_doctor.py check`. It must pass the `channel: manifest` untracked-runtime check (after step 4, no runtime file is tracked). On a freshly-migrated project the doctor may still flag the project's own brief debt (missing sections, references to now-harness-owned handbook docs) — report those as the owner's cleanup, not a seed failure.
7. Print the next steps below.

## Next steps (render to the user)

```
Seeded <project-name> (<stack>): project files scaffolded, runtime materialized.

1. Run the doctor to validate the docs/ roster:
     python3 .claude/skills/doctor/scripts/brief_doctor.py check
2. Fill in your briefs — docs/prd.md (requirements), docs/system-design.md
   (architecture); review docs/testing-principles.md and
   docs/architecture-principles.md. They are yours now.
3. Review scripts/layout.toml — adjust the module rules and prod_roots to your
   package layout. Channel is "manifest" (runtime materialized, not committed).
4. Fill the Security Context in docs/system-design.md — the security profile
   (inputs, outputs, services, credentials, runtime). The security-reviewer
   reads it from the brief, not from the agent.
5. Run /brief-review for the advisory pass once the briefs have content.
6. Re-run the runtime install any time with: harness/materialize.sh <stack> <target>
```

## Files that stay in the monorepo only

Do NOT deliver these to a target — they are the reference's own maintenance tooling and documentation, not harness machinery:

- The monorepo root's `.claude/skills/` (`init`, `seed`, `harvest`, `audit-consistency`, `deps-upgrade`, `research-update`, `history-update`, `harness-stats-setup`).
- The monorepo root's `CLAUDE.md`, `README.md`, `docs/`, and `docs/adr/`.
