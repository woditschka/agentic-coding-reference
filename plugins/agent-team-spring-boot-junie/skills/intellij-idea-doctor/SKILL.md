---
name: intellij-idea-doctor
description: >-
  One-command health check for the IntelliJ IDEA MCP oracle: is it connected, is
  the right project bound, and is the project model loaded correctly (Gradle
  imported)? Load when the user asks to check / diagnose / verify the IntelliJ
  (IDE / MCP / oracle) connection or status, or when an agent is about to rely on
  the IDE oracle's semantic results and needs to confirm they are trustworthy.
compatibility:
  - claude-code
  - github-copilot
metadata:
  version: "1.2"
  author: team
---

# intellij-idea-doctor — diagnose the IntelliJ MCP oracle

A responding MCP server is **not** the same as a usable oracle. The tools can answer while bound to a project that never imported Gradle, or to a *different* project than the one you are working in — and then `search_symbol` returns nothing and `get_file_problems` emits false "Cannot resolve symbol" errors on code that `./gradlew build` compiles cleanly. This skill runs the minimal probe set that tells the three states apart and prints a plain verdict.

For the *why* behind each probe and the fallback rules, see the `intellij-idea` skill (§ Connection health check). This skill is the **runner**; that skill is the **reference** — keep interpretation logic in sync with it.

## Procedure

`PROJECT=<absolute path to this repository's root>` (pass as `projectPath` on every call). Tool names below are bare — call each as it appears in your own tool list.

Run the probes your agent actually has (see § Tool availability per agent). `search_symbol` is the **portable primary** — every IDE-enabled agent has it, and it alone distinguishes all the states. `get_project_dependencies` is the **un-fakeable corroboration**, available only to the orchestrator and system-design-expert.

1. **Pick a known repo class** so the "right project" check is robust to renames. Glob `src/main/java/**/*.java`, take any one file, and use its simple class name (any `@Service`, `@Entity`, `@RestController`, or other class you can confirm exists). Note its real path — that is what a healthy oracle must echo back.

2. **Primary probe — symbol resolution (every IDE-enabled agent has this).** `search_symbol(q=<known class>, projectPath=PROJECT)`
   - Hit whose `filePath` is under this repo (matches step 1) → the **right project** is bound and its sources are indexed → healthy.
   - Hit whose `filePath` is *outside* this repo → **wrong project** bound.
   - `{"items":[]}` → sources not in the model: model not loaded (Gradle not imported) or wrong project — disambiguate with step 3 if you can.
   - Call errors / times out → server **not connected**.

3. **Corroborating probe — dependencies (only if your agent declares it).** `get_project_dependencies(projectPath=PROJECT)`
   - Non-empty (`spring-boot-*`, `jackson-*`, …) → Gradle model imported; confirms a healthy `search_symbol`.
   - `{"dependencies":[]}` on this Spring project → **model not loaded** (no classpath). The un-fakeable signal: a Spring app cannot compile without its libraries. Use it to split a `[]` symbol result into *not-loaded* vs *wrong-project*.
   - If your agent cannot call this tool, say so and rely on `search_symbol` alone — never report a dependency count you did not observe.

4. **Do NOT use `get_project_modules` as a health signal.** A bare module lists fine on a broken model — a **false green**. Run it only for extra detail, never as the verdict.

## Tool availability per agent

The IDE tools are partitioned by role, so not every caller can run every probe. `search_symbol` (with `get_symbol_info`) is the common denominator — this skill is built around it for that reason.

| Caller | `search_symbol` (primary) | `get_project_dependencies` (corroboration) |
|---|:--:|:--:|
| Orchestrator (main loop) | ✅ | ✅ |
| system-design-expert | ✅ | ✅ |
| feature-implementer | ✅ | ❌ |
| code / test / security reviewers | ✅ | ❌ |
| doc-reviewer / coordinator / PRD | ❌ (no IDE tools) | ❌ |

A caller with no `search_symbol` at all cannot run this check — it reports "IDE not consulted (no oracle tools in this agent)" and proceeds on the native + Gradle baseline. A caller with `search_symbol` but not `get_project_dependencies` runs the primary probe and marks the corroboration `n/a`.

## Verdict mapping (primary axis = `search_symbol`)

| `search_symbol(known class)` | `get_project_dependencies` (if available) | Verdict |
|---|---|---|
| call errors / times out | — | **NOT CONNECTED** |
| hit, `filePath` under this repo | populated *or* n/a | **HEALTHY** |
| hit, `filePath` outside this repo | — | **WRONG PROJECT BOUND** |
| `[]` | `[]` | **CONNECTED — MODEL NOT LOADED** (Gradle not imported) |
| `[]` | populated | **PARTIAL** (deps loaded but symbols unindexed — indexing in progress or stale; re-run shortly) |
| `[]` | n/a (agent lacks the tool) | **NOT USABLE** — symbols don't resolve and there's no deps probe to say why. Treat as unusable (fall back to grep + `./gradlew`); have the orchestrator or system-design-expert re-run with `get_project_dependencies`, or check the IDE directly (§ Without Claude Code). |

A repo-local `search_symbol` hit is sufficient for **HEALTHY** on its own — the dependencies probe corroborates it but is not required. The deps probe earns its keep only on a `[]` symbol result, where it separates *not-loaded* from *unindexed*.

## Output format

Print this block verbatim, filled in:

```
IntelliJ MCP Oracle — Status
  Connection:    <connected | NOT CONNECTED>
  Project model: <loaded (Gradle imported) | NOT LOADED | unknown>
  Right project: <yes — KnownClass resolves at <path> | WRONG project | cannot confirm>
  Verdict:       <HEALTHY | CONNECTED — MODEL NOT LOADED | WRONG PROJECT BOUND | PARTIAL | NOT USABLE | NOT CONNECTED>
  Probes:        search_symbol(<KnownClass>)=<M hits>, get_project_dependencies=<N libs | n/a for this agent>
  Trust oracle?  <YES — use at the chokepoints | NO — fall back to grep + ./gradlew>
  Remedy:        <none | the matching remedy below>
```

## Remedies

- **MODEL NOT LOADED** — in the IDE the MCP is attached to: Gradle tool window → *Reload All Gradle Projects*; confirm *External Libraries* populates under the Project view. Then re-run `intellij-idea-doctor`.
- **WRONG PROJECT BOUND** — close the stray project/instance, or ensure only one IDE window is open for this repo; the MCP binds to the running IDE.
- **NOT CONNECTED** — confirm the IDE is running with the MCP server enabled (IntelliJ: *Settings → Tools → AI Assistant / MCP*, or the MCP plugin's status indicator). Do not block work on it — fall back to native + Gradle.

## Without Claude Code (human-only check)

Anyone can sanity-check from the IDE directly, no agent needed:

1. **Connected?** IntelliJ *Settings → Tools* (AI Assistant / MCP) shows the MCP server running.
2. **Right project + loaded?** The Project view shows this repo, the **Gradle** tool window lists this project, and **External Libraries** lists Spring/Jackson jars. If External Libraries is empty or the Gradle tool window is absent, the project was opened as a plain folder — *Reload All Gradle Projects* (or reopen `build.gradle` as a project).

## Rules

- Read-only. This skill never edits files; it only probes and reports.
- Report only probes you actually ran (see `intellij-idea` § Report only checks you actually ran). Never narrate a green you did not observe.
- A `get_project_modules` success is **not** a passing verdict on its own — the verdict comes from symbol resolution (primary), corroborated by dependencies when the caller has that tool.
