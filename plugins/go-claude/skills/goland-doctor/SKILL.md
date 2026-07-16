---
name: goland-doctor
description: >-
  One-command health check for the GoLand MCP oracle: is it connected, is the
  right project bound, and is the project model loaded correctly (Go module
  synced)? Load when the user asks to check / diagnose / verify the GoLand (IDE /
  MCP / oracle) connection or status, or when an agent is about to rely on the
  IDE oracle's semantic results and needs to confirm they are trustworthy.
compatibility:
  - claude-code
  - github-copilot
metadata:
  version: "1.1"
  author: team
---

# goland-doctor — diagnose the GoLand MCP oracle

A responding MCP server is **not** the same as a usable oracle. The tools can answer while bound to a project that never synced its Go module, or to a *different* project than the one you are working in — and then `search_symbol` returns nothing and `get_file_problems` emits false "Unresolved reference" errors on code that `go build ./...` compiles cleanly. This skill runs the minimal probe set that tells the three states apart and prints a plain verdict.

For the *why* behind each probe and the fallback rules, see the `goland` skill (§ Connection health check). This skill is the **runner**; that skill is the **reference** — keep interpretation logic in sync with it.

## Procedure

`PROJECT=<absolute path to this repository's root>` (pass as `projectPath` on every call). Tool names below are bare — call each as it appears in your own tool list.

Run the probes your agent actually has (see § Tool availability per agent). `search_symbol` is the **portable primary** — every IDE-enabled agent has it, and it alone distinguishes all the states. `get_project_dependencies` is the **un-fakeable corroboration**, available only to the orchestrator and system-design-expert.

1. **Pick a known repo symbol** so the "right project" check is robust to renames. Glob `**/*.go` (skip `_test.go`), take any one file, and use an exported type or function name you can confirm exists. Note its real path — that is what a healthy oracle must echo back.

2. **Primary probe — symbol resolution (every IDE-enabled agent has this).** `search_symbol(q=<known symbol>, projectPath=PROJECT)`
   - Hit whose `filePath` is under this repo (matches step 1) → the **right project** is bound and its sources are indexed → healthy.
   - Hit whose `filePath` is *outside* this repo → **wrong project** bound.
   - `{"items":[]}` → sources not in the model: model not loaded (Go module not synced) or wrong project — disambiguate with step 3 if you can.
   - Call errors / times out → server **not connected**.

3. **Corroborating probe — dependencies (only if your agent declares it).** `get_project_dependencies(projectPath=PROJECT)`
   - Non-empty (the module's resolved `require` set) → Go module model synced; confirms a healthy `search_symbol`.
   - `{"dependencies":[]}` on a module that declares dependencies → **model not loaded** (no module graph). Use it to split a `[]` symbol result into *not-loaded* vs *wrong-project*. (A zero-dependency module is legitimately empty — corroborate with the symbol probe, not deps alone.)
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

A caller with no `search_symbol` at all cannot run this check — it reports "IDE not consulted (no oracle tools in this agent)" and proceeds on the native + `go` baseline. A caller with `search_symbol` but not `get_project_dependencies` runs the primary probe and marks the corroboration `n/a`.

## Verdict mapping (primary axis = `search_symbol`)

| `search_symbol(known symbol)` | `get_project_dependencies` (if available) | Verdict |
|---|---|---|
| call errors / times out | — | **NOT CONNECTED** |
| hit, `filePath` under this repo | populated *or* n/a | **HEALTHY** |
| hit, `filePath` outside this repo | — | **WRONG PROJECT BOUND** |
| `[]` | `[]` (module declares deps) | **CONNECTED — MODEL NOT LOADED** (Go module not synced) |
| `[]` | populated | **PARTIAL** (deps loaded but symbols unindexed — indexing in progress or stale; re-run shortly) |
| `[]` | n/a (agent lacks the tool) | **NOT USABLE** — symbols don't resolve and there's no deps probe to say why. Treat as unusable (fall back to grep + `go build`); have the orchestrator or system-design-expert re-run with `get_project_dependencies`, or check the IDE directly (§ Without Claude Code). |

A repo-local `search_symbol` hit is sufficient for **HEALTHY** on its own — the dependencies probe corroborates it but is not required. The deps probe earns its keep only on a `[]` symbol result, where it separates *not-loaded* from *unindexed*.

The `[]` / `[]` → **MODEL NOT LOADED** row holds only when the module declares dependencies. A legitimately dependency-free module (stdlib only) returns `[]` deps even when healthy, so on such a module ignore the deps probe and take the `search_symbol` verdict alone.

## Output format

Print this block verbatim, filled in:

```
GoLand MCP Oracle — Status
  Connection:    <connected | NOT CONNECTED>
  Project model: <loaded (module synced) | NOT LOADED | unknown>
  Right project: <yes — KnownSymbol resolves at <path> | WRONG project | cannot confirm>
  Verdict:       <HEALTHY | CONNECTED — MODEL NOT LOADED | WRONG PROJECT BOUND | PARTIAL | NOT USABLE | NOT CONNECTED>
  Probes:        search_symbol(<KnownSymbol>)=<M hits>, get_project_dependencies=<N libs | n/a for this agent>
  Trust oracle?  <YES — use at the chokepoints | NO — fall back to grep + go build>
  Remedy:        <none | the matching remedy below>
```

## Remedies

- **MODEL NOT LOADED** — in the IDE the MCP is attached to: *File → Reload Project* (or *File → Invalidate Caches / Restart*); confirm the **Go Modules** / **External Libraries** view populates and module mode is enabled. Then re-run `goland-doctor`.
- **WRONG PROJECT BOUND** — close the stray project/instance, or ensure only one IDE window is open for this repo; the MCP binds to the running IDE.
- **NOT CONNECTED** — confirm the IDE is running with the MCP server enabled (*Settings → Tools → MCP Server*, or the MCP plugin's status indicator). Do not block work on it — fall back to native + `go`.

## Without Claude Code (human-only check)

Anyone can sanity-check from the IDE directly, no agent needed:

1. **Connected?** GoLand *Settings → Tools → MCP Server* shows the MCP server running.
2. **Right project + loaded?** The Project view shows this repo, the **Go Modules** tool window lists this module, and **External Libraries** lists the resolved dependencies. If External Libraries is empty or the module is not listed, the project was opened as a plain folder — *Reload Project* (or reopen with Go modules enabled).

## Rules

- Read-only. This skill never edits files; it only probes and reports.
- Report only probes you actually ran (see `goland` § Report only checks you actually ran). Never narrate a green you did not observe.
- A `get_project_modules` success is **not** a passing verdict on its own — the verdict comes from symbol resolution (primary), corroborated by dependencies when the caller has that tool.
