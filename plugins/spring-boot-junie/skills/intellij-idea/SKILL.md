---
name: intellij-idea
description: >-
  How to use IntelliJ IDEA's MCP tools as a read-only semantic oracle and
  verifier while coding Java/Spring Boot. Use this skill WHENEVER the IntelliJ
  MCP server is connected and the task involves understanding
  or validating the codebase — finding where a symbol is used, understanding a
  type, checking for problems, or confirming edits compile. Consult it before
  reaching for grep on a Java question, and after any batch of edits. The agent
  is the sole writer; IntelliJ never mutates files.
compatibility:
  - claude-code
  - github-copilot
metadata:
  version: "2.2"
  author: team
---

# IntelliJ IDEA (MCP)

IntelliJ is a **read-only semantic oracle and verifier**, not a second editor. It never mutates files — you, the agent, are the sole writer, using the native `Edit` / `Write` tools. Reach for the IDE tools only when they reveal something text can't (types, references, inspections) or to confirm edits actually hold (`build_project`).

These six tools **add** capability rather than duplicate it: none of them reads, searches, or edits files — native `Read` / `Grep` / `Glob` / `Edit` / `Write` already do that, and remain your default for all of it. So there is no "prefer the IDE over the native tool" choice to make and no fallback table — the two sets don't overlap. The IDE tools answer questions native text tools *can't* (what a symbol resolves to, what the compiler/inspections say); use them for exactly those questions and nothing else.

The tools below are named bare — `search_symbol`, `build_project`, and the rest. Call each one as it appears in your own tool list. If a tool isn't in your list, you don't have the oracle on this run: skip the IDE step and use the Gradle/native baseline. Every chokepoint (§ Where the workflow calls this in) degrades that way, so nothing breaks when the oracle is absent.

## Available tools (this server)

This IntelliJ MCP server exposes exactly six tools. There are **no** IDE-side file-read, content-search, edit, create, rename, reformat, or PSI-tree tools here — do not call them; they do not exist on this server.

| Tool | What it does |
|------|--------------|
| `search_symbol` | Find classes/methods/fields by identifier fragment. `include_external=true` also searches SDK/library symbols. `paths` filters by glob. |
| `get_symbol_info` | Quick-doc for the symbol at a file position (1-based line/column): name, signature, type, docs, and the declaration code when resolvable. |
| `get_file_problems` | IntelliJ inspections for one file (Spring wiring, JPA, nullability, syntax). `errorsOnly` to drop warnings. |
| `build_project` | Compile the project (or `filesToRebuild`); returns compiler errors. Compiler truth, not index guesswork. |
| `get_project_modules` | List modules and their types. |
| `get_project_dependencies` | List project library names. |

Always pass `projectPath` (the absolute path to this repository's root) to cut ambiguous calls.

## Routing — which tool for which question

**Semantic insight (only the IDE can answer these) — Java only:**

- "Where is X / who declares this / what implements this" → `search_symbol` to locate, then read the results with your own `Read`. It resolves the identifier semantically — a different question than `Grep`'s text match, not a faster version of it. Use `Grep` when you want literal text; use `search_symbol` when you want the symbol.
- "What is this symbol — type, signature, contract" → `get_symbol_info` at the symbol's position.
- "What does this library/framework class actually do" → `search_symbol` with `include_external=true` to locate it, then `get_symbol_info`, which returns the declaration code when available. (There is no decompiled-source file-read tool on this server.)

**Problems & verification (the backbone):**

- After any edit batch → `build_project` (compiler truth) **and** `get_file_problems` on the touched files (inspections). Treat both as a fast pre-check on the way to the canonical gate (see § Gradle Stays Canonical).

**Project shape:**

- Modules / dependencies at a glance → `get_project_modules` / `get_project_dependencies` (the resolved model, vs. `Read build.gradle` for the declared source — use whichever the question calls for).

**Renaming (propose, don't perform):** This server has no rename refactoring tool. Symbol-aware rename is the *correct* way to rename — text find-and-replace over- and under-matches references — so **propose** the rename and ask the user to run it through IntelliJ's UI (preview, conflict resolution, undo). If the user explicitly wants you to do it with text edits, change every call site with `Edit`, then verify with `Grep` for the old name and compile with `./gradlew build`.

**Do NOT route through IntelliJ:**

- Ordinary file read/edit, text/glob/regex search → native `Read` / `Edit` / `Write` / `Grep` / `Glob` (faster, unambiguous, and the only writers).
- Git (`git log` / `status` / `diff`) → the shell. Git history is the authority for `/next` candidate computation and reviews.
- The quality gate (`./gradlew build` / `test` / `formatJava`) → the shell.
- **Spring structure** (bean graph, endpoints, conditionals) → Spring Boot Actuator at runtime (`/actuator/beans`, `/mappings`, `/conditions`) — more accurate than static analysis.

## Coherence — keep in sync

All six IDE tools are read-only and you are the sole writer, so the only drift is **index lag**: after a native `Edit` / `Write` or a shell mutation (`./gradlew formatJava`, `mv`, `sed`), IntelliJ's in-memory index trails disk. A stale index can hold phantom symbols for renamed/deleted files and report a **false green**. Guard against it:

1. **Trust `build_project` over the index after edits.** Compiler output reads the project model, not a possibly-stale search index — it is the more reliable post-edit signal of the two IDE checks.
2. **Cross-check structural changes with `Grep`.** After a rename/move/delete done via text edits, grep the old name; any hit means the change is incomplete regardless of what `search_symbol` reports.
3. **Re-read only after an out-of-band rewrite.** A shell mutation (`./gradlew formatJava`, `sed`, `mv`) or a user hand-edit changes the file on disk behind your context — re-read then. After your own native `Edit` / `Write`, you already hold the new content; re-reading it buys nothing. The IDE never mutates code, so it is never a reason to re-read — `build_project` (step 1) is how the IDE catches up to you.
4. **One writer at a time.** Don't edit a file the user is hand-editing in the IDE; take turns.

## Connection health check — connected ≠ usable

A responding server is not a usable oracle. The tools can answer while bound to a project model that never imported Gradle — a bare-directory open, or a second IDE instance that isn't the one you compile in. In that state `search_symbol` returns nothing, `get_symbol_info` resolves no candidates, and `get_file_problems` emits **false reds** ("Cannot resolve symbol 'String'") on code that `./gradlew build` compiles cleanly. Trusting it fails the IDE-static-analysis gate on good code, and "not connected" mis-describes it — the remedy is a reimport, not wiring.

So there are **three** states, not two:

| State | Symptom | Action |
|---|---|---|
| **Not connected** | calls error or time out | Drop the semantic step; native + Gradle baseline (§ Default posture). |
| **Connected, model broken** | calls succeed, but deps empty / project symbols empty / inspections all-red | Same fallback as not-connected — but say so precisely ("IDE connected but project model not imported") and surface the reimport. |
| **Healthy** | deps populated, a known class resolves | Trust the oracle; use it at the chokepoints. |

**Health check** — run before trusting any semantic result. The `intellij-idea-doctor` skill is the runner; this is the contract:

1. `search_symbol` on one class you know exists — the **portable primary**, available to every IDE-enabled agent. Resolves to a `filePath` under this repo → healthy; empty → broken model (or wrong project). This alone distinguishes the states.
2. `get_project_dependencies` — the **un-fakeable corroboration**, but declared only for the orchestrator and system-design-expert. When you have it, an empty `[]` on a Gradle project confirms "no classpath → unusable" and splits an empty symbol result into *not-loaded* vs *wrong-project*. Agents without it rely on step 1 and mark this `n/a`.

Do **not** use `get_project_modules` or `build_project` as the health check: a bare module lists fine, and an already-built project's incremental `build_project` returns `isSuccess:true` with nothing to compile — both are **false greens** on a broken model. `get_project_dependencies` is the one that can't be faked, because a Spring app cannot compile without its libraries on the classpath.

**Remedy** (one-time, in the IDE the MCP is attached to): Gradle tool window → *Reload All Gradle Projects*, and confirm only one IDE instance is open for this repo. Surfacing this reimport is the documented exception to § Default posture's "don't ask the user to start the IDE" — offer it as an option, never as a blocker.

## Gradle Stays Canonical

`./gradlew build && ./gradlew test && ./gradlew checkJavaFormat` (build + tests + format check) is the authoritative quality gate — see the `code-quality-gate` skill. IntelliJ's `build_project` and `get_file_problems` are a fast **pre-check** while iterating; they never replace the Gradle gate that runs before code review and in CI. A clean `get_file_problems` or green `build_project` does not substitute for a green Gradle gate, and after out-of-band edits it may be a false green (see § Coherence).

## Report only checks you actually ran

The transcript is the ground truth: a check counts only when it appears as an actual IDE tool call in it (Claude Code's `⇲` statusline cell counts these). Never write "build_project clean", "inspections clean", or "IDE pre-check passed" unless you actually invoked that tool **this run**. If the MCP server isn't connected, or you simply didn't call it, report what you *did* run instead — e.g. "verified via `./gradlew build`; IDE not consulted."

Overclaiming an IDE check is worse than skipping it: it reads as a passed gate, survives into the `build-pass` record and the eval as a false signal, and hides the very gap a reviewer would otherwise catch. When the oracle is connected, the chokepoints in § Where the workflow calls this in are the moments to *call* the tool — not to narrate calling it. One real `build_project` beats a paragraph describing one.

## Cite the call that backs a claim

Some claims assert that code *resolves* a certain way — "reuses the existing `parseInput(...)` pattern", "mirrors `ExampleRepository`", "this is the only caller of X". Grep matches text; only the oracle confirms a symbol resolves as the claim assumes. So **when the oracle is connected, a resolution claim must cite the `search_symbol` / `get_symbol_info` call that backs it** — the call is the evidence, the claim is the conclusion. This is where the oracle earns its keep over grep, so it's the one place real use is *required* rather than optional.

**Cite only where a Java symbol is the evidence — don't tick the box on every slice.** The citation is required when the claim genuinely turns on how a Java symbol resolves. When the load-bearing evidence is something the Java-only oracle cannot see — template/HTML structure, CSS classes, message bundles, configuration, a presentation or pure-template slice — do **not** fire a tangential `search_symbol` to satisfy the rule. That is the ritual the § Default posture warns against, and it reads as a passed check while proving nothing. State instead that the oracle is N/A for this evidence and name what you used (`Read` of the templates, `Grep`, `./gradlew build`). "Oracle N/A here — verified the grid classes via `Read`" is a stronger, honester signal than a `search_symbol` on a symbol that wasn't the evidence.

Without the oracle (not connected), fall back to a `Grep` citation and label it as the weaker basis — "grep-confirmed, IDE not consulted". An uncited resolution claim is an overclaim under § Report only checks you actually ran.

This requirement binds at four chokepoints (§ Where the workflow calls this in): a `covered` / `minor` triage verdict whose `architectural_fit` names the covering code (`design-validation`), the design-check / Refactor "reuses pattern X" decision (`tdd-workflow`), a reviewer's `consistent-with-codebase` finding (`code-quality-review`), and a route / access-control reference claim (`security-review`). It is scoped to those resolution claims only — it does not ask for an oracle call on every edit, which would be the ritual the § Default posture warns against.

## Default posture

Native tools are the baseline for everything — reading, editing, text search, git, the build gate. Add an IDE call only for the narrow band it uniquely serves: **Java symbol resolution, type info, inspections, and compiler verification.** If a question isn't one of those, you don't need the IDE.

Keep tool use minimal and purposeful: fewer, sharper calls beat many. If the MCP server is not connected — or connected but failing the health check (§ Connection health check) — the semantic step simply isn't available; drop it and proceed on the native baseline (for compile/problem checks, that's `./gradlew`). Don't ask the user to start the IDE (the § Connection health check reimport is the one exception).

## Where the workflow calls this in

These chokepoints reference the IDE tools as a when-connected accelerator, with one exception: the resolution-claim citation (§ Cite the call that backs a claim) is *required* when the oracle is connected, not optional. Every chokepoint falls back to the native/Gradle baseline when no IDE MCP server is connected, so clients without it — and CI — are unaffected:

| Skill / step | IDE use |
|---|---|
| `code-quality-gate` § IDE Static Analysis | `build_project` + `get_file_problems` on the diff before the gate passes — inspection errors fail the gate; warnings seed self-review findings. |
| `design-validation` § Verdict criteria | `search_symbol` / `get_symbol_info` to confirm a `covered` / `minor` verdict's `architectural_fit` still resolves as memory recalls it (**required citation**). |
| `tdd-workflow` § Fast inner-loop verification | `build_project` for per-cycle compiler truth; `search_symbol` / `get_symbol_info` to ground a Refactor's "matches the pattern" decision (**required citation**). |
| `code-quality-review` § IDE-Assisted Review | `get_file_problems` as a mechanical pre-filter; `search_symbol` / `get_symbol_info` to verify `consistent-with-codebase` claims (**required citation**). |
| `security-review` § IDE-Assisted Checks | `get_project_dependencies` for the resolved dep set; `search_symbol` / `get_symbol_info` for route/access-control reference claims (**required citation**). |

## Setup and other clients

Connecting the server, the exposed-tool rationale, and per-client status (Copilot, OpenCode, Junie) are maintainer concerns, not runtime ones — see [`intellij-mcp-integration.md`](intellij-mcp-integration.md). At runtime you need none of it: use the tools your frontmatter grants, fall back when they're absent.
