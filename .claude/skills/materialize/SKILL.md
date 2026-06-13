---
name: materialize
description: >-
  Install or upgrade a project's harness by completely replacing its
  harness-owned runtime with the current /harness. Auto-detects the stack (Go or
  Java Spring Boot) from the build marker, scaffolds project-owned files via
  /init when they are missing, replaces the runtime, removes stale orphans,
  preserves genuine project extensions (asking when unsure), migrates a
  copy-channel project to manifest, and validates with the doctor. Load when the
  user invokes `/materialize <project-path>`.
compatibility:
  - claude-code
metadata:
  version: "1.0"
  author: team
---

# Materialize

Bring a project's harness to the current `/harness` by **completely replacing its harness-owned runtime**. This is the "out" leg of the steady-state loop — *materialize out → evolve in the project → harvest back*. Runs from the monorepo root; `/harness` is the source (in future, the installed plugin — same flow, different source).

**Usage:** `/materialize <project-path>` (e.g., `/materialize ../widget`, or `samples/go` for a sample).

When invoked with **no argument**, print this block and stop:

```
/materialize <project-path> — install or upgrade a project's harness by
completely replacing its harness-owned runtime with the current /harness.

  <project-path>   path to the target project (required). Must hold a build
                   marker: go.mod (Go) or build.gradle / .kts / pom.xml (Java).

What it does:
  • detects the stack from the build marker
  • scaffolds project-owned files via /init when missing (greenfield or
    copy→manifest migration)
  • replaces the runtime, removes stale orphans, keeps project extensions
    (asks when unsure), then runs the doctor

Options live in the target's scripts/layout.toml [harness] table; /init asks
for them on a new project, and /materialize respects them on an upgrade:
  • channel = "manifest" (runtime materialized + gitignored, not committed)
             | "copy"     (runtime committed into the repo)
  • tools = ["claude", ...]   surfaces installed; claude always on, copilot,
            opencode, junie optional — never added on upgrade
  • extensions = [paths]      project-owned skills/agents kept, never pruned

Examples:
  /materialize ../my-service      onboard or upgrade a project
  /materialize samples/go         re-materialize a sample (idempotent)

Aliases: /seed is the same command.
```

Complete replacement means: install the current harness runtime, **remove** any harness file an older harness installed that the current one no longer produces (orphans), and **keep** files the project added that the harness never owned (extensions). The runtime is the only thing replaced — project-owned files (`CLAUDE.md`, `docs/` briefs, `scripts/layout.toml`, `settings*.json`) are never touched here.

## Precondition: the target has a build marker

The stack is detected from the target's build marker — the same detection `/init` and `bootstrap.sh` use:

| Marker in target | Stack (`<stack>`) |
|---|---|
| `go.mod` | `go` |
| `build.gradle`, `build.gradle.kts`, or `pom.xml` | `java-spring-boot` |
| More than one marker | Ask which is authoritative |
| No marker | **Stop.** The target must be a buildable skeleton first (`go mod init`, `gradle init`, or Spring Initializr). |

## Process

1. **Read the target** from `$ARGUMENTS`. **If no path is given, print the Usage block above verbatim and stop** — never guess a target or operate on the current directory. Otherwise verify the path exists and detect the stack (table above).

2. **Scaffold if needed.** If the target has no `CLAUDE.md`, or its `scripts/layout.toml` has no `[harness]` table (or no `layout.toml` at all), the project-owned files are missing or pre-manifest — run **`/init <target>`** first. `/init` scaffolds the committed files, asks which **tool surfaces** to install (claude always on; copilot, opencode, junie optional) and which **channel** to use — **manifest** (runtime gitignored, not committed) or **copy** (runtime committed into the repo) — and writes both to the `[harness]` table. A fully set-up project skips this step.

3. **Read the channel and tools** from `scripts/layout.toml` `[harness]`. `channel` (`manifest` or `copy`) governs orphan removal (step 6). `tools` is the surface set; on an upgrade `materialize.sh` installs only these (or auto-detects the present surfaces when the key is absent) and **never adds a tool the project lacks**. To add or drop a tool, edit `[harness] tools` and re-run.

4. **Replace the runtime.** Run the install:
   ```bash
   harness/materialize.sh <stack> <target>
   ```
   It copies `core ∪ stacks/<stack>` for the resolved tools (overwriting harness-owned files = the "replace"), prints `tools=…`, and prints an **extras** block — files under the harness-owned runtime directories that this install did **not** produce, one path per line between `--- extras: N … ---` and `--- end extras ---`. The script never deletes; classification is yours.

5. **Classify each extra.** Check the declared extensions first, then disambiguate by harness *history* — history is what tells a renamed-away harness unit apart from a genuine project addition:
   - **Already a declared extension** (the path is under a `[harness] extensions` entry) → **keep**, no further checks. These are the project's own, recorded.
   - **Stray file inside a harness-owned unit** (a file in a skill or agent directory the current harness still owns, that this install did not produce) → **orphan → remove**.
   - **A unit the harness once owned but no longer does** (a whole directory renamed away or dropped, e.g. `doc-review/` after the rename to the freshly-installed `document-writing/`) → **stale orphan → remove**. Confirm with the harness source history: `git -C <harness-root> log --oneline -- '*/.claude/skills/<name>/*' 'harness/*/<name>/*'` returns commits ⇒ the name *was* a harness unit. (When the source is a plugin with no history, fall back to the obvious rename successor this install just added, and ask if unclear.)
   - **A self-contained unit the harness never owned** — a whole skill directory whose name appears nowhere in harness history, or an agent with no harness counterpart and no harness past → **new project extension → keep, and record it** (step 6).
   - **Ambiguous** — when history is unclear or you cannot place it → **ask** the user keep-or-remove. Default to keeping over deleting.

   The current harness unit set is `harness/core ∪ harness/stacks/<stack>`; the *former* set is that plus what harness history shows was renamed or removed. A name in the former-but-not-current set is an orphan, not an extension.

6. **Record extensions, then apply removals.**
   - **Record new extensions.** For each kept unit not yet listed, add its runtime-relative path to `[harness] extensions` in `scripts/layout.toml`, and append a `!<path>/` line to the `.gitignore` runtime block so new files inside it stay visible. This makes the keep durable: the doctor excludes declared extensions from the untracked check, and the next materialize keeps them without re-asking.
   - **Remove orphans** — channel-aware:
     - **manifest** (runtime gitignored): remove confirmed orphans directly (`rm`). They are recoverable by re-materialize, so this is safe.
     - **copy** (runtime committed): a removal touches tracked files. Drive the copy→manifest transition — untrack the harness runtime **excluding declared extensions** so the project keeps its own skills/agents:
       ```bash
       git -C <target> rm -r --cached --ignore-unmatch <runtime paths> :!<ext1> :!<ext2>
       ```
       Then delete the orphans. Warn on any local runtime modifications (`git status` on the runtime paths) before deleting, so the user does not lose hand-edits unknowingly.

7. **Propose removing harness-originated docs (migration).** A project migrating from an older harness often carries handbook docs an earlier harness copied into `docs/`. That content now ships *with the harness* — as installed skills, or as reference-only docs. The `docs/` copies are stale duplicates, and they are why a freshly migrated project's doctor reports `handbook-refs` failures. Detect and **propose** their removal (never auto-delete — `docs/` is project-owned):
   - A non-roster `docs/*.md` whose basename is in the doctor's handbook denylist (`harness/core/.claude/skills/doctor/brief-expectations.toml` `[handbook] denylist` — `agentic-harness.md`, `specialist-agent-workflow.md`, `tdd-principles.md`, `ddd-principles.md`, `documentation-standards.md`, `harness-project-api.md`) → **moved to the harness**.
   - A non-roster `docs/*.md` whose content matches an installed runtime doc — by name under `.claude/skills/` (excluding `.claude/skills/doctor/templates/`) or a high-similarity diff → **heavily overlaps the harness**. Example: `docs/intellij-mcp-integration.md` vs the `intellij-idea` skill copy. The template exclusion matters: the roster briefs legitimately match their own doctor templates — that is their source, not overlap.

   List each candidate with its new harness home and ask the user to remove them. The roster briefs (`prd.md`, `system-design.md`, `ubiquitous-language.md`, `testing-principles.md`, `architecture-principles.md`, `adr/`) are never proposed. When the user agrees, delete the files and clean the now-dangling references the doctor's `handbook-refs` check flags. Remove or reword them in the citing briefs and ADRs — that prose is project-owned, so confirm the edits or hand them to `/brief-review`.

8. **Validate and summarize.** Run the doctor from the target:
   ```bash
   ( cd <target> && python3 .claude/skills/doctor/scripts/brief_doctor.py check )
   ```
   Then print a **tools / changed / preserved / removed** summary:
   - **tools** — the surface set installed (from `materialize.sh`'s `tools=…` line).
   - **changed** — N runtime files installed (the materialize count).
   - **preserved** — project extensions kept (list them, or "none").
   - **removed** — orphans deleted (list them, or "none").
   - **doctor** — the pass/fail line. A roster failure here is the project's own brief debt; point the user at `/brief-review`, since materialize never edits project-owned files.

## Project-owned files and version drift

Materialize replaces **runtime only**. When a newer harness changes a project-owned contract — a brief gains a required section, `layout.toml` needs a new key — the **doctor** flags it and the human fixes it via `/brief-review`. There is no migration engine here, by design: the runtime is always made current by replacement, and project-owned content stays the owner's to evolve.

## What materialize does NOT do

- **Edit project-owned files.** Briefs, `layout.toml`, `CLAUDE.md`, `settings*.json` — never touched. Scaffolding gaps are `/init`'s job (step 2); content is the owner's.
- **Delete extensions.** A skill or agent the project added and the harness never owned is preserved (and recorded in `[harness] extensions`); at most it is surfaced for a decision.
- **Add a tool surface on upgrade.** It installs only the project's declared (or already-present) tools; opting into a new tool is an explicit `[harness] tools` edit, then a re-run.
- **Build files.** `go.mod`, `Makefile`, `build.gradle`, `pom.xml`, wrappers — the target brings its own (they are how the stack is detected).
- **Run git against the repo for copy→manifest.** It prints the `git rm --cached` command (via `/init`); the user runs it.

## Relationship to other skills

- **`/init`** scaffolds the project-owned committed files; materialize calls it when they are missing. Init out, materialize out, **`/harvest`** back.
- **`/seed`** is a compatibility alias for this skill — a greenfield target is just `/materialize` on an unscaffolded project (step 2 runs `/init`, step 4 installs).
- **`harness/bootstrap.sh`** is the dumb multi-target installer (detect stack → `materialize.sh`); it has no extras classification. Use it for a fast re-install of the monorepo samples; use `/materialize` for the smart, complete-replacement experience on a real project.
