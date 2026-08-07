---
name: goland
description: >-
  How to use GoLand's MCP tools as a read-only semantic oracle
  while coding Go. Use this skill WHENEVER the GoLand MCP server is connected and
  the task involves understanding or validating the codebase — finding where a
  symbol is used, understanding a type, or checking for problems. Consult it
  before reaching for grep on a Go-symbol question, and
  after any batch of edits. The agent is the sole writer; GoLand never mutates
  files and never runs code.
compatibility:
  - claude-code
  - github-copilot
metadata:
  version: "1.1"
  author: team
---

# GoLand (MCP)

GoLand is a **read-only semantic oracle**, not a second editor and not a build tool. It never mutates files and never runs code — you, the agent, are the sole writer, using the native `Edit` / `Write` tools, and the Go toolchain is the only thing that compiles. Reach for the IDE tools only when they reveal something text can't: types, references, inspections.

These five tools **add** capability rather than duplicate it: none of them reads, searches, or edits files — native `Read` / `Grep` / `Glob` / `Edit` / `Write` already do that, and remain your default for all of it. So there is no "prefer the IDE over the native tool" choice to make and no fallback table — the two sets don't overlap. The IDE tools answer questions native text tools *can't* (what a symbol resolves to, what the inspections say); use them for exactly those questions and nothing else.

The tools below are named bare — `search_symbol`, `get_file_problems`, and the rest. Call each one as it appears in your own tool list. **Your tool list is the authority on what exists, not this table** — the server's exposed set is an IDE setting that can drift. If a tool isn't in your list, you don't have it on this run: skip the IDE step and use the `go`/native baseline. Every chokepoint (§ Where the workflow calls this in) degrades that way, so nothing breaks when the oracle is absent.

## Available tools (this server)

This GoLand MCP server exposes five tools. There are **no** IDE-side file-read, content-search, edit, create, rename, reformat, build, or syntax-tree tools here. If one appears in your tool list anyway, that is a misconfiguration — say so rather than calling it (see [`goland-mcp-integration.md`](goland-mcp-integration.md) § The exposed tool set).

| Tool | What it does |
|------|--------------|
| `search_symbol` | Find types/functions/methods/vars by identifier fragment. `include_external=true` also searches SDK/dependency symbols. `paths` filters by glob. |
| `get_symbol_info` | Quick-doc for the symbol at a file position (1-based line/column): name, signature, type, docs, and the declaration code when resolvable. |
| `get_file_problems` | GoLand inspections for one file (unresolved references, unused declarations, shadowing, unchecked errors, vet-class issues). `errorsOnly` to drop warnings. Also the only tool that refreshes the IDE's view of disk — see § Coherence. |
| `get_project_modules` | List Go modules and their types. |
| `get_project_dependencies` | List resolved module dependencies. |

Always pass `projectPath` (the absolute path to this repository's root) to cut ambiguous calls.

## Routing — which tool for which question

**Semantic insight (only the IDE can answer these) — Go symbols only:**

- "Where is X / who declares this / what implements this interface" → `search_symbol` to locate, then read the results with your own `Read`. It resolves the identifier semantically — a different question than `Grep`'s text match, not a faster version of it. Use `Grep` when you want literal text; use `search_symbol` when you want the symbol.
- "What is this symbol — type, signature, contract" → `get_symbol_info` at the symbol's position.
- "What does this dependency/stdlib function actually do" → `search_symbol` with `include_external=true` to locate it, then `get_symbol_info`, which returns the declaration code when available. (There is no decompiled-source file-read tool on this server.)

**Problems & verification (the backbone):**

- After any edit batch → `get_file_problems` on the touched files. It returns GoLand's inspections *and* refreshes the IDE's view of disk, so it must come before any `search_symbol` / `get_symbol_info` you intend to trust (§ Coherence). Treat it as a fast pre-check on the way to the canonical gate (§ The Go toolchain stays canonical).
- Compiler truth → `go build ./...`. The IDE does not compile for you; there is no build tool on this server.

**Project shape:**

- Modules / dependencies at a glance → `get_project_modules` / `get_project_dependencies` (the resolved model, vs. `Read go.mod` for the declared source — use whichever the question calls for).

**Renaming (propose, don't perform):** This server has no rename refactoring tool. Symbol-aware rename is the *correct* way to rename — text find-and-replace over- and under-matches references — so **propose** the rename and ask the user to run it through GoLand's UI (preview, conflict resolution, undo). If the user explicitly wants you to do it with text edits, change every call site with `Edit`, then verify with `Grep` for the old name and compile with `go build ./...`.

**Do NOT route through GoLand:**

- Ordinary file read/edit, text/glob/regex search → native `Read` / `Edit` / `Write` / `Grep` / `Glob` (faster, unambiguous, and the only writers).
- Git (`git log` / `status` / `diff`) → the shell. Git history is the authority for `/next` candidate computation and reviews.
- The quality gate (`go vet ./...` / `make lint` / `go test ./...` / `go build`) → the shell.

## Coherence — keep in sync

All five IDE tools are read-only and you are the sole writer, so the only drift is **index lag**: after a native `Edit` / `Write` or a shell mutation (`gofmt -w`, `mv`, `sed`), GoLand's in-memory index trails disk. A stale index can hold phantom symbols for renamed/deleted files and report a **false green**. Guard against it:

1. **Call `get_file_problems` first — it is the refresh.** Of the five tools it is the only one that catches the IDE up to disk: it triggers a VFS refresh and waits for indexing before analysing. The other four read cached index and PSI state and will answer from *before* your edits. So after an edit batch, call `get_file_problems` on a touched file before trusting any `search_symbol` / `get_symbol_info` result.
2. **Cross-check structural changes with `Grep`.** After a rename/move/delete done via text edits, grep the old name; any hit means the change is incomplete regardless of what `search_symbol` reports.
3. **Re-read only after an out-of-band rewrite.** A shell mutation (`gofmt -w`, `sed`, `mv`) or a user hand-edit changes the file on disk behind your context — re-read then. After your own native `Edit` / `Write`, you already hold the new content; re-reading it buys nothing. The IDE never mutates code, so it is never a reason to re-read — `get_file_problems` (step 1) is how the IDE catches up to you.
4. **One writer at a time.** Don't edit a file the user is hand-editing in the IDE; take turns.

The refresh in step 1 depends on the IDE's file watcher having noticed the write, so it is not a guarantee. A missed watcher event degrades to a stale answer with no error. The Go toolchain reads disk directly and is unaffected, which is the other reason it stays canonical (§ The Go toolchain stays canonical).

## Connection health check — connected ≠ usable

A responding server is not a usable oracle. The tools can answer while bound to a project model that never loaded the Go module — a bare-directory open, GOPATH/module sync not finished, or a second IDE instance that isn't the one you compile in. In that state `search_symbol` returns nothing, `get_symbol_info` resolves no candidates, and `get_file_problems` emits **false reds** ("Unresolved reference") on code that `go build ./...` compiles cleanly. Trusting it fails the IDE-static-analysis gate on good code, and "not connected" mis-describes it — the remedy is a resync, not wiring.

So there are **three** states, not two:

| State | Symptom | Action |
|---|---|---|
| **Not connected** | calls error or time out | Drop the semantic step; native + `go` baseline (§ Default posture). |
| **Connected, model broken** | calls succeed, but deps empty / project symbols empty / inspections all-red | Same fallback as not-connected — but say so precisely ("IDE connected but Go module not loaded") and surface the resync. |
| **Healthy** | deps populated, a known symbol resolves | Trust the oracle; use it at the chokepoints. |

**Health check** — run before trusting any semantic result. The `goland-doctor` skill is the runner; this is the contract:

1. `search_symbol` on one symbol you know exists — the **portable primary**, available to every IDE-enabled agent. Resolves to a `filePath` under this repo → healthy; empty → broken model (or wrong project). This alone distinguishes the states.
2. `get_project_dependencies` — the **un-fakeable corroboration**, but declared only for the orchestrator and system-design-expert. When you have it, an empty `[]` on a module with dependencies confirms "no module model → unusable" and splits an empty symbol result into *not-loaded* vs *wrong-project*. Agents without it rely on step 1 and mark this `n/a`.

Do **not** use `get_project_modules` as the health check: a bare module lists fine on a broken model — a **false green**. `get_project_dependencies` is the one that is hardest to fake, because it reflects the resolved module graph rather than a directory listing.

**Remedy** (one-time, in the IDE the MCP is attached to): *File → Reload Project / Sync* (or invalidate caches and restart), confirm `GOROOT`/`GOPATH` and module mode are set, and confirm only one IDE instance is open for this repo. Surfacing this resync is the documented exception to § Default posture's "don't ask the user to start the IDE" — offer it as an option, never as a blocker.

## The Go toolchain stays canonical

`go vet ./... && make lint && go test ./... && go build -o bin/reference` (vet + lint + tests + build) is the authoritative quality gate — see the `code-quality-gate` skill. It is also the **only** compiler signal: this server exposes no build tool, deliberately. Compiler errors are exactly the information `go build` already reconstructs from disk, so an IDE build earns no slot under the exposure policy (see [`goland-mcp-integration.md`](goland-mcp-integration.md) § Excluded by policy). The toolchain also reads disk directly where the IDE's index may lag.

GoLand's `get_file_problems` is a fast **pre-check** while iterating — inspections the toolchain cannot give you. It never replaces the toolchain gate that runs before code review and in CI: a clean `get_file_problems` does not substitute for a green toolchain gate, and after out-of-band edits it may be a false green (see § Coherence).

## Report only checks you actually ran

The transcript is the ground truth: a check counts only when it appears as an actual IDE tool call in it (Claude Code's `⇲` statusline cell counts these). Never write "inspections clean" or "IDE pre-check passed" unless you actually invoked that tool **this run**. If the MCP server isn't connected, or you simply didn't call it, report what you *did* run instead — e.g. "verified via `go build ./...`; IDE not consulted."

Overclaiming an IDE check is worse than skipping it: it reads as a passed gate, survives into the `build-pass` record and the eval as a false signal, and hides the very gap a reviewer would otherwise catch. When the oracle is connected, the chokepoints in § Where the workflow calls this in are the moments to *call* the tool — not to narrate calling it. One real `get_file_problems` beats a paragraph describing one.

## Cite the call that backs a claim

Some claims assert that code *resolves* a certain way — "reuses the existing `parseInput(...)` pattern", "mirrors `exampleStore`", "this is the only caller of X". Grep matches text; only the oracle confirms a symbol resolves as the claim assumes. So **when the oracle is connected, a resolution claim must cite the `search_symbol` / `get_symbol_info` call that backs it** — the call is the evidence, the claim is the conclusion. This is where the oracle earns its keep over grep, so it's the one place real use is *required* rather than optional.

**Cite only where a Go symbol is the evidence — don't tick the box on every slice.** The citation is required when the claim genuinely turns on how a Go symbol resolves. When the load-bearing evidence is something the Go-symbol oracle cannot see — a config file, a text template, an embedded asset, generated code, a pure-data slice — do **not** fire a tangential `search_symbol` to satisfy the rule. That is the ritual the § Default posture warns against, and it reads as a passed check while proving nothing. State instead that the oracle is N/A for this evidence and name what you used (`Read` of the file, `Grep`, `go build`). "Oracle N/A here — verified the config keys via `Read`" is a stronger, honester signal than a `search_symbol` on a symbol that wasn't the evidence.

Without the oracle (not connected), fall back to a `Grep` citation and label it as the weaker basis — "grep-confirmed, IDE not consulted". An uncited resolution claim is an overclaim under § Report only checks you actually ran.

This requirement binds at four chokepoints (§ Where the workflow calls this in): a `covered` / `minor` triage verdict whose `architectural_fit` names the covering code (`design-validation`), the design-check / Refactor "reuses pattern X" decision (`tdd-workflow`), a reviewer's `consistent-with-codebase` finding (`code-quality-review`), and an access-control / data-flow reference claim (`security-review`). It is scoped to those resolution claims only — it does not ask for an oracle call on every edit, which would be the ritual the § Default posture warns against.

## Default posture

Native tools are the baseline for everything — reading, editing, text search, git, the build gate. Add an IDE call only for the narrow band it uniquely serves: **Go symbol resolution, type info, and inspections.** If a question isn't one of those, you don't need the IDE.

Keep tool use minimal and purposeful: fewer, sharper calls beat many. If the MCP server is not connected — or connected but failing the health check (§ Connection health check) — the semantic step simply isn't available; drop it and proceed on the native baseline (for compile/problem checks, that's `go build` / `go vet` / `make lint`). Don't ask the user to start the IDE (the § Connection health check resync is the one exception).

## Where the workflow calls this in

These chokepoints reference the IDE tools as a when-connected accelerator, with one exception: the resolution-claim citation (§ Cite the call that backs a claim) is *required* when the oracle is connected, not optional. Every chokepoint falls back to the native/`go` baseline when no IDE MCP server is connected, so clients without it — and CI — are unaffected:

| Skill / step | IDE use |
|---|---|
| `code-quality-gate` § IDE Static Analysis | `get_file_problems` on the diff before the gate passes — inspection errors fail the gate; warnings seed self-review findings. Compilation is the toolchain gate's job, not the IDE's. |
| `design-validation` § Verdict criteria | `search_symbol` / `get_symbol_info` to confirm a `covered` / `minor` verdict's `architectural_fit` still resolves as memory recalls it (**required citation**). |
| `tdd-workflow` § Fast inner-loop verification | `get_file_problems` for per-cycle inspections (the cycle's own `go test ./...` already carries compiler truth); `search_symbol` / `get_symbol_info` to ground a Refactor's "matches the pattern" decision (**required citation**). |
| `code-quality-review` § IDE-Assisted Review | `get_file_problems` as a mechanical pre-filter; `search_symbol` / `get_symbol_info` to verify `consistent-with-codebase` claims (**required citation**). |
| `security-review` § IDE-Assisted Checks | `search_symbol` / `get_symbol_info` for access-control / data-flow reference claims (**required citation**); the resolved dep graph is not granted to this role — read `go.mod` for the declared set. |

## Setup and other clients

Connecting the server, the exposed-tool rationale, and per-client status (Copilot, OpenCode, Junie) are maintainer concerns, not runtime ones — see [`goland-mcp-integration.md`](goland-mcp-integration.md). At runtime you need none of it: use the tools your frontmatter grants, fall back when they're absent.
