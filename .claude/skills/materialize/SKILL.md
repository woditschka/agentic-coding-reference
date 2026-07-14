---
name: materialize
description: >-
  Install or upgrade a project's harness by completely replacing its
  harness-owned runtime with the current /harness. Auto-detects the stack (Go,
  Java Spring Boot, or the generic fallback) from the build marker, scaffolds project-owned files via
  /init when they are missing, replaces the runtime, removes stale orphans,
  preserves genuine project extensions (asking when unsure), respects the
  project's declared distribution channel, verifies the installed suites, and
  validates with the doctor. Load
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
    source — found by heading, no prompt
  • runs the installed test suites once (a failure means the runtime is
    broken on this host), then runs the doctor

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

Complete replacement makes three moves. It installs the current harness runtime. It **removes** orphans — files an older harness installed that the current one no longer produces. It **keeps** extensions — files the project added that the harness never owned. The runtime is the only thing replaced. Beyond the runtime, harness-owned content *inside* project-owned files is kept current in two layers — the deterministic step-4 refresh and the advisory diff-check of steps 8–9. § Project-owned files and version drift holds that contract; this section is a pointer, not a second statement of it.

## Precondition: detect the stack

The stack is detected from the target's build marker — the same detection `/init` and `bootstrap.sh` use. The marker table (including the ask-on-multiple-markers and generic-fallback rows) lives in `/init`'s "Precondition" section; the code home is `detect_stack` in `harness/helpers.py`. The ask-on-multiple rule is this skill's judgment layer — `detect_stack` itself resolves by order and never asks. No recognized marker is not an error: `generic`, the technology-free stack, binds its build in `scripts/stack.sh`.

## Process

1. **Read the target** from `$ARGUMENTS`. **If no path is given, print the Usage block above verbatim and stop** — never guess a target or operate on the current directory. Otherwise verify the path exists and detect the stack (table above).

2. **Scaffold if needed.** If the target has no `CLAUDE.md`, or its `scripts/layout.toml` has no `[harness]` table (or no `layout.toml` at all), the project-owned files are missing or predate the `[harness]` table. Run **`/init <target>`** first. `/init` scaffolds the committed files and asks which **tool surfaces** to install (claude always on; copilot, opencode, junie optional). It also **resolves the channel** without prompting — detected from the project's git state, defaulting a greenfield target to **copy** (runtime committed). Both are written to the `[harness]` table. A fully set-up project skips this step.

3. **Read the channel and tools** from `scripts/layout.toml` `[harness]`. `channel` (`copy`, `manifest`, or `marketplace`) governs orphan removal (step 6); marketplace behaves like manifest (runtime gitignored, not committed). `tools` is the surface set; on an upgrade `materialize.py` installs only these (or auto-detects the present surfaces when the key is absent) and **never adds a tool the project lacks**. To add or drop a tool, edit `[harness] tools` and re-run.

4. **Replace the runtime.** Run the install:
   ```bash
   harness/materialize.py <stack> <target>
   ```
   It copies `core ∪ stacks/<stack>` for the resolved tools (overwriting harness-owned files = the "replace") and prints `tools=…`. It then prints an **extras** block: files under the harness-owned runtime directories — plus `scripts/`, minus the project-owned `layout.toml` and, on the generic stack, `stack.sh` — that this install did **not** produce. Each path prints on its own line between `--- extras: N … ---` and `--- end extras ---`. The script never deletes; classification is yours.

   The script also runs **three deterministic, marker-free refreshes** of harness-owned content inside project-owned files (mechanics live in `materialize.py`; watch its output lines):
   - **`CLAUDE.md` managed chapters** — the doctrine chapters from `harness/claude-md/managed-chapters.md`, each found by heading and rewritten in place; every other chapter untouched. Prints `managed chapters: N refreshed`; an `absent` heading is left for step 9 to convert once.
   - **`.gitignore`** — the runtime paths from `harness/init/core/gitignore-runtime.txt`, channel-aware. Prints `gitignore: N path(s) added`.
   - **`.claude/settings.json`** — the agent-teams `env` flag and a `PreToolUse` matcher per delivered hook. Prints `settings: …`.

   The install ends with **verification**: it runs the test suites it just copied and prints `verified: N vendored suite(s) pass on this host`. A failure prints `verify: <suite> FAILED` plus the error tail and exits 1 — the installed runtime is broken on this host (broken copy, python incompatibility). Re-run the materialize; a persistent failure is a harness defect to report upstream, never the project's brief debt. The suite list is the install's own file set, so a project-authored `test_*.py` is never run as a suite. (`--no-verify` skips the run; it exists for harness-internal callers only.)

   All three refreshes are **ensure-present and additive**. Harness-owned lines and keys are matched against the shipped template — no markers, no baseline. A project's own ignores, keys, hooks, and chapters are never rewritten, and nothing is removed. Removals and deeper divergence are what step 8's diff-check exists to catch — the residual an additive pass cannot safely decide.

5. **Classify each extra.** Check the declared extensions first, then disambiguate by harness *history* — history is what tells a renamed-away harness unit apart from a genuine project addition:
   - **Already a declared extension** (the path is under a `[harness] extensions` entry) → **keep**, no further checks. These are the project's own, recorded.
   - **A declared extra reviewer body** (an agent whose name is in `[harness] extra_reviewers`) → **keep, and record it** (step 6). The additive roster lets a project add `*-reviewer` agents beside the floor; their bodies live in the harness-owned agent directories but are the project's own. This rule mirrors the doctor's `reviewer-roster` check, so the two agree.
   - **Stray file inside a harness-owned skill** (a file in a skill directory the current harness still owns, that this install did not produce) → **orphan → remove**. This applies to skill directories only — one skill is a single multi-file unit, so an unproduced file inside it is debris. An agent file is its own single-file unit, never a "stray file"; classify each agent by the per-unit rules below (renamed-away ⇒ orphan; never-owned ⇒ extension).
   - **A `scripts/` engine file the harness once shipped but no longer does** → **stale orphan → remove**. Confirm with the harness source history: `git -C <harness-root> log --oneline -- '*/scripts/<name>'` returns commits ⇒ it *was* a harness engine. A `scripts/` file with no harness past is the project's own tooling → **keep, and record it** (step 6).
   - **A unit the harness once owned but no longer does** — a whole skill directory renamed away or dropped (e.g. `doc-review/` → the installed `document-writing/`), or a single agent body → **stale orphan → remove**. Confirm with the harness source history: for a skill, `git -C <harness-root> log --oneline -- '*/.claude/skills/<name>/*' 'harness/*/<name>/*'`; for an agent, `git -C <harness-root> log --oneline -- '*/agents/<name>.md' '*/agents/<name>.agent.md'`. Commits returned ⇒ the name *was* a harness unit. (When the source is a plugin with no history, fall back to the obvious rename successor this install just added, and ask if unclear.)
   - **A self-contained unit the harness never owned** → **new project extension → keep, and record it** (step 6). This is a whole skill directory whose name appears nowhere in harness history, or a single-file agent with no harness counterpart and no harness past — an extra `*-reviewer` is exactly this case.
   - **Ambiguous** — when history is unclear or you cannot place it → **ask** the user keep-or-remove. Default to keeping over deleting.

   The current harness unit set is `harness/core ∪ harness/stacks/<stack>`; the *former* set is that plus what harness history shows was renamed or removed. A name in the former-but-not-current set is an orphan, not an extension.

6. **Record extensions, then apply removals.**
   - **Record new extensions.** For each kept unit not yet listed, run `python3 <harness-root>/harness/materialize.py record-extension <target> <runtime-path>`. The script adds the path to `[harness] extensions` in `scripts/layout.toml` and, on a gitignored-runtime channel, appends the correctly-formed `.gitignore` re-include (the directory-vs-file slash rule lives in the script). Idempotent. This makes the keep durable: the doctor excludes declared extensions from the untracked check, and the next materialize keeps them without re-asking.
   - **Remove orphans** — channel-aware, but the channel is **never changed** (switching is a manual, documented step — see `/init`'s "Channel: detect, never prompt"). Only the confirmed orphan paths are touched:
     - **manifest** (runtime gitignored): remove confirmed orphans directly (`rm`). They are recoverable by re-materialize, so this is safe.
     - **copy** (runtime committed): the orphan files are tracked. Remove them from the working tree *and* the index with a scoped `git rm` (the orphan paths only — never the whole runtime):
       ```bash
       git -C <target> rm -r --ignore-unmatch <orphan paths>
       ```
       This stages the deletion for the project's next commit; declared extensions are not in the orphan set, so they are untouched. Warn on any local runtime modifications (`git status` on the orphan paths) before deleting, so the user does not lose hand-edits unknowingly.

7. **Propose removing harness-originated docs (migration).** A project migrating from an older harness often carries handbook docs an earlier harness copied into `docs/`. That content now ships *with the harness* — as installed skills, or as reference-only docs. The `docs/` copies are stale duplicates, and they are why a freshly migrated project's doctor reports `handbook-refs` failures. Detect and **propose** their removal (never auto-delete — `docs/` is project-owned):
   - A non-roster `docs/*.md` whose basename is in the doctor's handbook denylist (`harness/core/scripts/brief-expectations.toml` `[handbook] denylist` — `agentic-harness.md`, `specialist-agent-workflow.md`, `cross-tool-strategy.md`, `adoption-guide.md`, `glossary.md`, `tdd-principles.md`, `ddd-principles.md`, `documentation-standards.md`, `harness-project-api.md`) → **moved to the harness**.
   - A non-roster `docs/*.md` whose content matches an installed runtime doc — by name under `.claude/skills/` (excluding `.claude/skills/doctor/templates/`) or a high-similarity diff → **heavily overlaps the harness**. Example: `docs/intellij-mcp-integration.md` vs the `intellij-idea` skill copy. The template exclusion matters: the roster briefs legitimately match their own doctor templates — that is their source, not overlap.

   List each candidate with its new harness home and ask the user to remove them. The roster briefs (`prd.md`, `system-design.md`, `ubiquitous-language.md`, `testing-principles.md`, `architecture-principles.md`, `security-principles.md`, `adr/`) are never proposed. When the user agrees, delete the files and clean the now-dangling references the doctor's `handbook-refs` check flags. Remove or reword them in the citing briefs and ADRs — that prose is project-owned, so confirm the edits or hand them to `/audit-docs`.

8. **Diff-check every template-seeded file against its shipped template (advisory).** Step 4's deterministic refreshes already made the harness-owned *additions* current — the `.gitignore` runtime paths and the `.claude/settings.json` keys. This step is the **completeness backstop over the same diffs**: it catches what an additive pass cannot safely decide, and covers the files step 4 does not touch at all. For each template-seeded file, diff the **shipped harness template** against the project's file, classify every delta, and **propose** each change — applying it only on the user's OK. What the diff-check surfaces beyond step 4:
   - a harness line the template **dropped** that still lingers in the project (`.gitignore` path, `settings.json` matcher for a renamed hook) → propose removing it;
   - a harness key the project **overrode** with a divergent value → surface it;
   - the fully-advisory files step 4 never touches — `scripts/layout.toml` data and the `docs/` briefs.

   **Classify each delta by intent, and protect both sides.** No markers are written and no version is stamped — the shipped template on disk is the reference, and model judgment stands in for a baseline. For every difference between the template and the project's file, decide which of three it is:
   - **A deliberate project change** — the project intentionally diverged: a customized value, a section removed on purpose, a rule of its own. The project's version is coherent and specific to this project; the template carries the generic default. → **Protect it. Do not propose reverting it to the template.**
   - **A harness migration** — the template evolved as the harness improved (a new section, a better default, a new key), and this project simply predates it. The template's version is a general improvement, not project-specific; the project's is the older default or absent. → **Propose adopting it.**
   - **A collision** — the project customized something the harness also evolved. → **Protect both: show both versions, let the human decide, never auto-resolve.**

   The rule runs both ways: never silently revert a deliberate project change, and never silently drop a harness migration. Without a baseline the classification cannot be *proven* — a project's coherent customization and a stale generic default can look alike. So the approval step, not an algorithm, is the safeguard, and a genuine collision always goes to the human. This is the same generic-vs-project call step 5 makes for orphan-vs-extension.

   | Project file | Shipped template to diff against | Harness-owned in it |
   |---|---|---|
   | `.gitignore` | `harness/init/core/gitignore-runtime.txt` | the runtime-path lines (`.claude/skills/*`, `scripts/*`, …) and the `.scratch/` ledger; the project's own ignores and the `!<extension>/` re-includes are theirs |
   | `.claude/settings.json` | `harness/init/core/.claude/settings.json` | the `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` flag and the `PreToolUse` matchers whose command is a `.claude/hooks/*.py` this install delivered (a legacy `*.sh` matcher is harness-era residue this diff-check proposes to prune); every other key and hook is the project's |
   | `scripts/layout.toml` | `harness/init/stacks/<stack>/scripts/layout.toml` | the `[harness]` table structure, any new keys, and the guiding comments (`spec_version` is a harness contract value the doctor checks); the classification *data* — globs, module rules, `extensions` — is the project's |
   | `docs/*.md` roster briefs | `harness/core/.claude/skills/doctor/templates/<brief>.md` | the skeleton structure — required headings, new sections; the filled-in prose is the project's |

   - **`.gitignore`** — step 4 already ensured the current harness paths are present, so the diff-check focuses on the *residual*. A path the template **dropped** that still lingers → propose removing it. A runtime path present on the **copy** channel, where the committed runtime should not be ignored → propose removing it. Read the channel from `[harness] channel`; never change it.
   - **`.claude/settings.json`** — step 4 already ensured the `env` flag and a matcher for every delivered hook (this **subsumes the old hook-registration proposal**, now automatic). The diff-check catches the residual. A matcher whose hook script the harness renamed or dropped, now inert → propose removing it. A harness key the project overrode with a divergent value → surface it. The doctor's `hook-registration` check (step 10) still flags any hook left unregistered.
   - **`scripts/layout.toml`** — step 4 does not touch this file; the diff-check owns it. A new `[harness]` key the template carries but the project lacks → propose it (contract drift the doctor also flags); improved guiding comments → propose them. The project's rule *data* is never rewritten.
   - **`docs/` briefs** — a required or new section the template skeleton gained but the brief lacks → propose inserting the empty section for the owner to fill. Never overwrite authored prose. Deeper brief-quality work stays with `/audit-docs`.

   **Declines are not persisted.** A proposal the user turns down is simply left alone. It re-surfaces on the next `/materialize` — acceptable for an occasionally-run upgrade, and it re-offers a change the user may since have reconsidered. An idempotent re-materialize (no template change, no divergence) finds no delta and proposes nothing, so the only thing that re-appears is a genuine, still-open divergence. If that repetition ever proves irritating, a `declined_reconciliations` skip-list in `[harness]` is the pre-authorized next step (ADR [generalized-template-reconciliation](../../../docs/adr/2026-07-01-generalized-template-reconciliation.md)) — deferred until the friction is real rather than assumed.

9. **Review the materialized CLAUDE.md (advisory).** Step 4's refresh is deterministic: it overwrites each managed chapter from its heading to the next `## `. That is correct for the chapter's *doctrine*, but a heading-bounded overwrite cannot see what else the edit did to the file. Review the result before moving on. On a tracked `CLAUDE.md`, `git diff -- CLAUDE.md` is the precise signal — read it, and read the whole file once. If the diff is empty (an idempotent re-materialize), there is nothing to review; skip. Otherwise check five things and **propose** every fix — `CLAUDE.md` is project-owned, so confirm before editing, the same contract as steps 7–8:
   - **Accidental loss.** In the diff's removed (`-`) lines, flag any that are *project-authored* content, not harness doctrine — they lived inside a managed chapter and the refresh overwrote them. Propose moving them to a project-owned chapter rather than losing them. This is the one failure the deterministic replace cannot prevent: a managed chapter is harness-owned, so anything a project puts *inside* it is overwritten by design.
   - **Repetition.** Any managed chapter's doctrine appearing a second time outside its chapter — a stray `### Confirmation Discipline`, a duplicated memory or writing-standards note. Usually a legacy artifact. Propose removing the duplicate so the managed chapter is the single copy.
   - **Contradiction.** A project chapter that fights a managed one — a Build/Quality-Gate chapter that re-states confirmation rules differently, a local writing rule against the managed Writing Standards. Propose reconciling it.
   - **Structure.** Headings well-formed. Chapters in a sensible order — match the skeleton's relative layout: Memory and Agent Usage near the top; Writing Standards, Scratch Directory, Documentation Updates beside their related project chapters. No orphaned fragment left by an old edit.
   - **Missing improvements.** A *non-doctrine* chapter the current skeleton (`harness/init/stacks/<stack>/CLAUDE.md`) gained — new build, quality-gate, or convention guidance — that the project's `CLAUDE.md` lacks → propose adding it. The call is the same generic-vs-project judgment step 8 makes. This is the `CLAUDE.md` facet of step 8's template reconciliation; the doctrine chapters are already current from step 4, so only the project-authored chapters are compared here.

   **Absent headings (legacy migration).** A chapter step 4 reported `absent` had a renamed or missing heading, so the deterministic replace had no target. Locate the equivalent section, **propose** inserting the matching chapter from `harness/claude-md/managed-chapters.md` under its canonical heading (placed to match skeleton order), and remove the old copy. Preserve genuine divergence: project-rewritten text stays as its own chapter; stack-specific skills (an IDE oracle) belong in `## Stack-specific skills`, not inside a managed one.

   This review is advisory and never gates the doctor. A proposal the user declines is not persisted — it re-surfaces next upgrade (step 8's "Declines are not persisted"). Ongoing — outside an upgrade — `/audit-docs` can run the same checks. It is also the forward edge of `/harvest`. Harvest pulls a generic improvement up from one project into the source. The managed chapters push it back down to every project automatically once the headings are in place; steps 8–9 propose the rest.

10. **Validate and summarize.** Run the doctor from the target:
   ```bash
   ( cd <target> && python3 scripts/brief_doctor.py check )
   ```
   Then print a **tools / changed / preserved / removed** summary:
   - **tools** — the surface set installed (from `materialize.py`'s `tools=…` line).
   - **changed** — N runtime files installed (the materialize count).
   - **verified** — the `verified: N vendored suite(s)` line from step 4.
   - **preserved** — project extensions kept (list them, or "none").
   - **removed** — orphans deleted (list them, or "none").
   - **doctor** — the pass/fail line. A roster failure here is the project's own brief debt; point the user at `/audit-docs`, since materialize never rewrites project-authored content. A `hook-registration` failure should not appear on a freshly materialized project — step 4's deterministic settings refresh registers every delivered hook. If it does appear, the settings refresh was skipped (unparseable `settings.json`, or `python3` unavailable). Fix that and re-run; this is not an `/audit-docs` case. A **channel-invariant** failure on manifest/marketplace (a runtime path tracked by git) usually means the path joined `RUNTIME_PATHS` after the project last upgraded, so an older gitignore never covered it. Run `git rm --cached <path>` — the file stays on disk, and the step-4 gitignore refresh keeps it untracked from then on.

## Project-owned files and version drift

Beyond wholesale **replacement** of the **runtime**, materialize keeps harness-owned content inside project-owned files current in two layers. **Deterministic refresh** (step 4) makes the harness-owned lines of three project-owned files current in place, marker-free: the `CLAUDE.md` doctrine chapters, the `.gitignore` runtime paths, and the `.claude/settings.json` harness keys. It is ensure-present and additive, so it reliably delivers a new path or hook but never removes or rewrites. **Advisory diff-check** (steps 8–9) is the completeness backstop: it diffs every template-seeded file against its shipped template and proposes each remaining delta, applying each only on approval. The deltas are the removals the additive pass left, plus `scripts/layout.toml` data, the `docs/` briefs, and the non-doctrine `CLAUDE.md` chapters. A declined proposal is not persisted; it re-surfaces on the next upgrade (a `declined_reconciliations` skip-list is the pre-authorized escape hatch if that ever chafes). There is no version stamp and no stored baseline; the shipped template is the reference, and model judgment separates a missing improvement from a deliberate divergence. *Contract* drift — a brief-required section, or a new `[harness]` key — still surfaces in the **doctor** too, so a skipped proposal is caught again at the gate. The doctor's `required-chapter` check fails if any managed chapter is missing or empty.

## What materialize does NOT do

- **Silently rewrite project-owned *authored* content.** The content a project author writes — brief prose, `layout.toml` rule data, its own `settings.json` keys and `.gitignore` ignores, the project-owned chapters of `CLAUDE.md` — is never rewritten on materialize's own initiative. Scaffolding gaps are `/init`'s job (step 2); authored content is the owner's. The two bounded exceptions — the deterministic step-4 refreshes and the consented migrations of steps 7–9 — touch harness-owned content only, per § Project-owned files and version drift.
- **Inject markers into project files.** The reconciliation of steps 8–9 is marker-free: no `BEGIN/END` sentinels are written into `.gitignore`, `settings.json`, or any other file. Harness-owned content is identified by diffing against the shipped template, not by fenced regions — the files stay clean.
- **Delete extensions.** A skill or agent the project added and the harness never owned is preserved (and recorded in `[harness] extensions`); at most it is surfaced for a decision.
- **Add a tool surface on upgrade.** It installs only the project's declared (or already-present) tools; opting into a new tool is an explicit `[harness] tools` edit, then a re-run.
- **Build files.** `go.mod`, `Makefile`, `build.gradle`, `pom.xml`, wrappers — the target brings its own (they are how the stack is detected).
- **Change the distribution channel.** It respects whatever `[harness] channel` declares and never flips it. Switching copy↔manifest is a manual, documented step (see `/init`'s "Channel: detect, never prompt"). On the copy channel it stages orphan deletions with a scoped `git rm` (orphan paths only), leaving the commit to the user; it never untracks the whole runtime.

## Relationship to other skills

- **`/init`** scaffolds the project-owned committed files; materialize calls it when they are missing. Init out, materialize out, **`/harvest`** back. A greenfield target is just `/materialize` on an unscaffolded project (step 2 runs `/init`, step 4 installs).
- **`harness/bootstrap.sh`** is the dumb multi-target installer (detect stack → `materialize.py`); it has no extras classification. Use it for a fast re-install of the monorepo samples; use `/materialize` for the smart, complete-replacement experience on a real project.
