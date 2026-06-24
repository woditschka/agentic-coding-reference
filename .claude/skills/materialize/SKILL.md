---
name: materialize
description: >-
  Install or upgrade a project's harness by completely replacing its
  harness-owned runtime with the current /harness. Auto-detects the stack (Go,
  Java Spring Boot, or the generic fallback) from the build marker, scaffolds project-owned files via
  /init when they are missing, replaces the runtime, removes stale orphans,
  preserves genuine project extensions (asking when unsure), respects the
  project's declared distribution channel, and validates with the doctor. Load
  when the user invokes `/materialize <project-path>`.
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

  <project-path>   path to the target project (required). A go.mod (Go) or
                   build.gradle / .kts / pom.xml (Java) marker selects that
                   stack; anything else falls back to the generic stack.

What it does:
  • detects the stack from the build marker
  • scaffolds project-owned files via /init when missing (greenfield)
  • replaces the runtime, removes stale orphans, keeps project extensions
    (asks when unsure)
  • refreshes the harness-managed chapters in CLAUDE.md from the single
    source — found by heading, no prompt — then runs the doctor

Options live in the target's scripts/layout.toml [harness] table; /init resolves
them on a new project, and /materialize respects them on an upgrade:
  • channel = "copy"        (runtime committed into the repo — the default)
             | "manifest"    (runtime materialized + gitignored, not committed)
             | "marketplace" (tool surfaces ship as a plugin; only the engine
                              sliver materializes project-side, gitignored)
    Resolved by /init (detected, not asked); /materialize never flips it.
    Marketplace is declaration-only — never inferred (its tree mirrors manifest).
  • tools = ["claude", ...]   surfaces installed; claude always on, copilot,
            opencode, junie optional — never added on upgrade
  • extensions = [paths]      project-owned skills/agents kept, never pruned

Examples:
  /materialize ../my-service      onboard or upgrade a project
  /materialize samples/go         re-materialize a sample (idempotent)
```

Complete replacement means: install the current harness runtime, **remove** any harness file an older harness installed that the current one no longer produces (orphans), and **keep** files the project added that the harness never owned (extensions). The runtime is the only thing replaced. Two bounded exceptions touch `CLAUDE.md`, both safe: the **harness-managed chapters** (Agent Usage, Memory, Writing Standards, Scratch Directory, Documentation Updates) are refreshed in place from the single source (step 4) — harness-owned chapters inside a project-owned file, each identified by its heading, the same managed-region contract as the `.gitignore` runtime block — and the **consented migrations** of steps 7–9 edit project-owned text only on approval. Everything else project-owned (`docs/` briefs, `scripts/layout.toml`, `settings*.json`, and every other chapter of `CLAUDE.md`) is untouched.

## Precondition: detect the stack

The stack is detected from the target's build marker — the same detection `/init` and `bootstrap.sh` use. An unrecognized stack is not an error; it falls back to `generic`:

| Marker in target | Stack (`<stack>`) |
|---|---|
| `go.mod` | `go` |
| `build.gradle`, `build.gradle.kts`, or `pom.xml` | `java-spring-boot` |
| More than one marker | Ask which is authoritative |
| No recognized marker | `generic` — the technology-free stack; the project binds its build system in `scripts/stack.sh`. |

## Process

1. **Read the target** from `$ARGUMENTS`. **If no path is given, print the Usage block above verbatim and stop** — never guess a target or operate on the current directory. Otherwise verify the path exists and detect the stack (table above).

2. **Scaffold if needed.** If the target has no `CLAUDE.md`, or its `scripts/layout.toml` has no `[harness]` table (or no `layout.toml` at all), the project-owned files are missing or predate the `[harness]` table — run **`/init <target>`** first. `/init` scaffolds the committed files, asks which **tool surfaces** to install (claude always on; copilot, opencode, junie optional), and **resolves the channel** — detected from the project's git state, defaulting a greenfield target to **copy** (runtime committed); it does not prompt. Both are written to the `[harness]` table. A fully set-up project skips this step.

3. **Read the channel and tools** from `scripts/layout.toml` `[harness]`. `channel` (`copy`, `manifest`, or `marketplace`) governs orphan removal (step 6); marketplace behaves like manifest (runtime gitignored, not committed). `tools` is the surface set; on an upgrade `materialize.sh` installs only these (or auto-detects the present surfaces when the key is absent) and **never adds a tool the project lacks**. To add or drop a tool, edit `[harness] tools` and re-run.

4. **Replace the runtime.** Run the install:
   ```bash
   harness/materialize.sh <stack> <target>
   ```
   It copies `core ∪ stacks/<stack>` for the resolved tools (overwriting harness-owned files = the "replace"), prints `tools=…`, and prints an **extras** block — files under the harness-owned runtime directories that this install did **not** produce, one path per line between `--- extras: N … ---` and `--- end extras ---`. The script never deletes; classification is yours.

   It also **refreshes the harness-managed chapters** in `CLAUDE.md`: the stack-agnostic harness doctrine — Agent Usage, Memory, Writing Standards, Scratch Directory, Documentation Updates — lives in the single source `harness/claude-md/managed-chapters.md`, whose `## ` chapters are the managed set, in canonical order. Each chapter is found by its heading and rewritten in place — from that heading to the next `## ` heading. Every other chapter is untouched, including the project-owned `## Stack-specific skills` and all build/toolchain/convention chapters. This is automatic and needs no prompt — these chapters are harness-owned, like the runtime. The script prints `managed chapters: N refreshed`. A heading that is absent (a legacy file with a renamed/missing chapter) is reported as `absent` and left for step 9 to convert once.

5. **Classify each extra.** Check the declared extensions first, then disambiguate by harness *history* — history is what tells a renamed-away harness unit apart from a genuine project addition:
   - **Already a declared extension** (the path is under a `[harness] extensions` entry) → **keep**, no further checks. These are the project's own, recorded.
   - **Stray file inside a harness-owned unit** (a file in a skill or agent directory the current harness still owns, that this install did not produce) → **orphan → remove**.
   - **A unit the harness once owned but no longer does** (a whole directory renamed away or dropped, e.g. `doc-review/` after the rename to the freshly-installed `document-writing/`) → **stale orphan → remove**. Confirm with the harness source history: `git -C <harness-root> log --oneline -- '*/.claude/skills/<name>/*' 'harness/*/<name>/*'` returns commits ⇒ the name *was* a harness unit. (When the source is a plugin with no history, fall back to the obvious rename successor this install just added, and ask if unclear.)
   - **A self-contained unit the harness never owned** — a whole skill directory whose name appears nowhere in harness history, or an agent with no harness counterpart and no harness past → **new project extension → keep, and record it** (step 6).
   - **Ambiguous** — when history is unclear or you cannot place it → **ask** the user keep-or-remove. Default to keeping over deleting.

   The current harness unit set is `harness/core ∪ harness/stacks/<stack>`; the *former* set is that plus what harness history shows was renamed or removed. A name in the former-but-not-current set is an orphan, not an extension.

6. **Record extensions, then apply removals.**
   - **Record new extensions.** For each kept unit not yet listed, add its runtime-relative path to `[harness] extensions` in `scripts/layout.toml`, and append a `!<path>/` line to the `.gitignore` runtime block so new files inside it stay visible. This makes the keep durable: the doctor excludes declared extensions from the untracked check, and the next materialize keeps them without re-asking.
   - **Remove orphans** — channel-aware, but the channel is **never changed** (switching is a manual, documented step — see `/init`'s "Channel: detect, never prompt"). Only the confirmed orphan paths are touched:
     - **manifest** (runtime gitignored): remove confirmed orphans directly (`rm`). They are recoverable by re-materialize, so this is safe.
     - **copy** (runtime committed): the orphan files are tracked, so remove them from the working tree *and* the index with a scoped `git rm` (the orphan paths only — never the whole runtime):
       ```bash
       git -C <target> rm -r --ignore-unmatch <orphan paths>
       ```
       This stages the deletion for the project's next commit; declared extensions are not in the orphan set, so they are untouched. Warn on any local runtime modifications (`git status` on the orphan paths) before deleting, so the user does not lose hand-edits unknowingly.

7. **Propose removing harness-originated docs (migration).** A project migrating from an older harness often carries handbook docs an earlier harness copied into `docs/`. That content now ships *with the harness* — as installed skills, or as reference-only docs. The `docs/` copies are stale duplicates, and they are why a freshly migrated project's doctor reports `handbook-refs` failures. Detect and **propose** their removal (never auto-delete — `docs/` is project-owned):
   - A non-roster `docs/*.md` whose basename is in the doctor's handbook denylist (`harness/core/scripts/brief-expectations.toml` `[handbook] denylist` — `agentic-harness.md`, `specialist-agent-workflow.md`, `tdd-principles.md`, `ddd-principles.md`, `documentation-standards.md`, `harness-project-api.md`) → **moved to the harness**.
   - A non-roster `docs/*.md` whose content matches an installed runtime doc — by name under `.claude/skills/` (excluding `.claude/skills/doctor/templates/`) or a high-similarity diff → **heavily overlaps the harness**. Example: `docs/intellij-mcp-integration.md` vs the `intellij-idea` skill copy. The template exclusion matters: the roster briefs legitimately match their own doctor templates — that is their source, not overlap.

   List each candidate with its new harness home and ask the user to remove them. The roster briefs (`prd.md`, `system-design.md`, `ubiquitous-language.md`, `testing-principles.md`, `architecture-principles.md`, `adr/`) are never proposed. When the user agrees, delete the files and clean the now-dangling references the doctor's `handbook-refs` check flags. Remove or reword them in the citing briefs and ADRs — that prose is project-owned, so confirm the edits or hand them to `/audit-docs`.

8. **Propose registering delivered hooks (migration).** The hook scripts under `.claude/hooks/` are harness-owned runtime this install just replaced, but their registration is a `PreToolUse` matcher in project-owned `.claude/settings.json`, which materialize never edits on its own. So an upgrade can deliver a new hook the project never wires, leaving it inert. For each hook script not referenced in `.claude/settings.json` — the doctor's `hook-registration` check (step 10) flags exactly these — **propose** the additive matcher and apply it only on the user's consent. Like the doc-removal proposal above, this is a consented edit to a project-owned file, never a silent one. A greenfield project scaffolded by `/init` already carries the registration and needs nothing here.

9. **Review the materialized CLAUDE.md (advisory).** Step 4's refresh is deterministic: it overwrites each managed chapter from its heading to the next `## `. That is correct for the chapter's *doctrine*, but a heading-bounded overwrite cannot see what else the edit did to the file. Review the result before moving on. On a tracked `CLAUDE.md`, `git diff -- CLAUDE.md` is the precise signal — read it, and read the whole file once. If the diff is empty (an idempotent re-materialize), there is nothing to review; skip. Otherwise check four things and **propose** every fix — `CLAUDE.md` is project-owned, so confirm before editing, the same contract as steps 7–8:
   - **Accidental loss.** In the diff's removed (`-`) lines, flag any that are *project-authored* content, not harness doctrine — they lived inside a managed chapter and the refresh overwrote them. Propose moving them to a project-owned chapter rather than losing them. This is the one failure the deterministic replace cannot prevent: a managed chapter is harness-owned, so anything a project puts *inside* it is overwritten by design.
   - **Repetition.** Any managed chapter's doctrine appearing a second time outside its chapter — a stray `### Confirmation Discipline`, a duplicated memory or writing-standards note. Usually a legacy artifact. Propose removing the duplicate so the managed chapter is the single copy.
   - **Contradiction.** A project chapter that fights a managed one — a Build/Quality-Gate chapter that re-states confirmation rules differently, a local writing rule against the managed Writing Standards. Propose reconciling it.
   - **Structure.** Headings well-formed; chapters in a sensible order (match the skeleton's relative layout — Memory and Agent Usage near the top; Writing Standards, Scratch Directory, Documentation Updates beside their related project chapters); no orphaned fragment left by an old edit.

   **Absent headings (legacy migration).** A chapter step 4 reported `absent` had a renamed or missing heading, so the deterministic replace had no target. Locate the equivalent section, **propose** inserting the matching chapter from `harness/claude-md/managed-chapters.md` under its canonical heading (placed to match skeleton order), and remove the old copy. Preserve genuine divergence: project-rewritten text stays as its own chapter; stack-specific skills (an IDE oracle) belong in `## Stack-specific skills`, not inside a managed one.

   This review is advisory and never gates the doctor. Ongoing — outside an upgrade — `/audit-docs` can run the same four checks. It is also the forward edge of `/harvest`: harvest pulls a generic improvement up from one project into the source; the managed chapters push it back down to every project, automatically once the headings are in place.

10. **Validate and summarize.** Run the doctor from the target:
   ```bash
   ( cd <target> && python3 scripts/brief_doctor.py check )
   ```
   Then print a **tools / changed / preserved / removed** summary:
   - **tools** — the surface set installed (from `materialize.sh`'s `tools=…` line).
   - **changed** — N runtime files installed (the materialize count).
   - **preserved** — project extensions kept (list them, or "none").
   - **removed** — orphans deleted (list them, or "none").
   - **doctor** — the pass/fail line. A roster failure here is the project's own brief debt; point the user at `/audit-docs`, since materialize never silently edits project-owned files. A `hook-registration` failure is resolved by step 8's consented edit, not `/audit-docs`.

## Project-owned files and version drift

Materialize replaces **runtime only**, plus the harness-managed chapters. When a newer harness changes a project-owned *contract* — a brief gains a required section, `layout.toml` needs a new key — the **doctor** flags it and the human fixes it via `/audit-docs`. When it improves the *harness doctrine*, that doctrine lives in the managed chapters, so step 4 refreshes them automatically on every upgrade — no proposal, no drift. There is still no migration engine for project-owned *content*: the runtime and the managed chapters are made current by replacement, contract drift is doctor-flagged, and the one-time legacy reconciliation (step 9) is consented. The doctor's `required-chapter` check fails if any managed chapter is missing or empty.

## What materialize does NOT do

- **Silently edit project-owned content.** Briefs, `layout.toml`, `settings*.json`, and the project-owned chapters of `CLAUDE.md` are never edited on materialize's own initiative. Scaffolding gaps are `/init`'s job (step 2); content is the owner's. The exceptions are bounded: the harness-managed chapters in `CLAUDE.md` are refreshed automatically (step 4) — harness-owned content, not project content — and the consented migrations the user approves are the doc removals (step 7), the hook registration (step 8), and the one-time legacy reconciliation (step 9).
- **Delete extensions.** A skill or agent the project added and the harness never owned is preserved (and recorded in `[harness] extensions`); at most it is surfaced for a decision.
- **Add a tool surface on upgrade.** It installs only the project's declared (or already-present) tools; opting into a new tool is an explicit `[harness] tools` edit, then a re-run.
- **Build files.** `go.mod`, `Makefile`, `build.gradle`, `pom.xml`, wrappers — the target brings its own (they are how the stack is detected).
- **Change the distribution channel.** It respects whatever `[harness] channel` declares and never flips it. Switching copy↔manifest is a manual, documented step (see `/init`'s "Channel: detect, never prompt"). On the copy channel it stages orphan deletions with a scoped `git rm` (orphan paths only), leaving the commit to the user; it never untracks the whole runtime.

## Relationship to other skills

- **`/init`** scaffolds the project-owned committed files; materialize calls it when they are missing. Init out, materialize out, **`/harvest`** back. A greenfield target is just `/materialize` on an unscaffolded project (step 2 runs `/init`, step 4 installs).
- **`harness/bootstrap.sh`** is the dumb multi-target installer (detect stack → `materialize.sh`); it has no extras classification. Use it for a fast re-install of the monorepo samples; use `/materialize` for the smart, complete-replacement experience on a real project.
