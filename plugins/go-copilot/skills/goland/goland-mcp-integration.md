# GoLand MCP Integration

GoLand serves as Claude Code's read-only semantic oracle — not a second editor and not a build tool. The agent stays the sole writer; the Go toolchain stays the only thing that compiles. GoLand answers questions plain text cannot: resolved types, references, inspections.

This is harness tooling, not product architecture, and it is optional: when the server is absent, every workflow falls back to the native tools plus `go build` / `go vet` / `make lint`. It is wired and working for Claude Code; the Copilot CLI agents are wired too but gated by an upstream bug (see [§ Connect from Copilot CLI](#connect-from-copilot-cli)).

This document covers how to connect the server and why the exposed tool set is what it is. Runtime usage — when the agent routes to each tool, index-lag coherence, the resolution-claim citation rule — lives in the [`goland` skill](SKILL.md). The connection health check lives in the [`goland-doctor` skill](../goland-doctor/SKILL.md).

## Connect the server

GoLand ships an MCP server, bundled and enabled by default since 2025.2.

1. **Settings → Tools → MCP Server → Enable MCP Server**.
2. Under **Clients Auto-Configuration**, click **Auto-Configure** for **Claude Code**. This writes the server config into Claude Code's config file.
3. **Restart Claude Code** so the config takes effect.
4. Launch Claude Code from the **IDE's project root** so both agree on the project.

Leave **brave mode** (run shell commands and run configurations without confirmation) off until you trust the loop.

## Connect from Copilot CLI

Copilot CLI reaches the same server. The agents in `.github/agents/*` already declare the oracle tools under Copilot's `goland/<tool>` namespace, mirroring the per-role partition the Claude Code agents use. Only the connection is configured client-side, the same way the IDE keeps Claude Code's entry in `~/.claude.json`:

1. **Find the SSE URL** the IDE wrote for Claude Code — the `goland` server entry in `~/.claude.json`, e.g. `http://127.0.0.1:<port>/sse`. The port is IDE-assigned and machine-specific, so this is not committed.
2. **Add the same server to `~/.copilot/mcp-config.json`** under the name `goland`:

   ```json
   {
     "mcpServers": {
       "goland": { "type": "sse", "url": "http://127.0.0.1:<port>/sse" }
     }
   }
   ```

3. **Launch Copilot CLI from the IDE's project root** so both agree on the project.

The server name **must** be `goland` so the committed `goland/<tool>` tool references in the agent frontmatter resolve.

> **Known limitation — [github/copilot-cli#2630](https://github.com/github/copilot-cli/issues/2630) (open as of 2026-05, filed against 1.0.23).** Copilot CLI does not connect an agent's MCP tools when that agent runs as a sub-agent (via the `task` tool) or non-interactively via `--prompt`. This pipeline dispatches every specialist as a sub-agent, so until the bug is fixed those dispatches fall back to the `go`/native baseline regardless of the wiring. The declarations are in place ahead of the fix; retest on the current Copilot CLI version before assuming it still fails. Claude Code is unaffected — it auto-configures the server and the interactive main loop connects normally.

## Other clients and tool namespaces

Each client exposes the same server tools under its own prefix. The agent skills name the tools bare (`search_symbol`, `get_file_problems`, …); the prefix is whatever the client prepends, and each agent calls the tool as its own frontmatter lists it.

| Client | Tool namespace | Status |
|--------|----------------|--------|
| Claude Code | `mcp__goland__<tool>` | Wired and working — the IDE auto-configures the server. |
| Copilot CLI | `goland/<tool>` | Wired in `.github/agents/*`; gated by [copilot-cli#2630](https://github.com/github/copilot-cli/issues/2630) until the sub-agent MCP bug is fixed (see above). |
| OpenCode | `goland_<tool>` | Not wired — next target. |
| Junie | native — no MCP tool names | Headless by decision. |

**OpenCode (next target).** Add the `goland` server to `opencode.json` under the top-level `mcp` key (`type: "remote"`, `url:` the same SSE endpoint as above), then grant `goland_*` per role under each agent's singular `permission` block (`allow`/`ask`/`deny` by tool-name glob — OpenCode has no `mcp` permission key). The server config commits to the repo and the partition maps directly onto per-agent permission globs.

**Junie (headless by decision).** Junie reaches IDE semantics natively, with no MCP, but only when the CLI is bridged to a running IDE. Headless Junie CLI has no live IDE and runs on the native baseline like any unconnected client. Junie stays headless until the bridge is GA and Junie is driven in-IDE against this repo; the native path would then be its own design (no tool names to cite, `/ide` as the health check, read-only as discipline since native access includes refactors), not a third MCP wiring.

Enablement stays localized to a client's agent files plus its client-side server config. The workflow skills are untouched — they gate on oracle availability, not on tool names.

## The exposed tool set

This project exposes five MCP tools, configured under **Settings → Tools → MCP Server → Exposed Tools**. The exposure policy has two tests, and a tool must pass both:

1. **It carries information plain text cannot reconstruct.** If a native tool or the Go toolchain gate already produces the same answer, the IDE earns no slot — a faster route to identical information is not new information.
2. **It neither writes files nor executes code.** Not just "does not mutate a file": *executes* is the property that matters, and the two are not the same test.

**Principle — read only, in both senses.** No exposed tool writes to disk, and none runs code. Claude Code is the sole writer through its own file edits; the Go toolchain is the only thing that compiles. This removes write-coherence failure modes — persistence uncertainty, multi-file staleness, write races — and keeps the IDE off the execution path entirely. The one drift that remains is index lag, handled by the `goland` skill.

**This is a checkbox, not an invariant.** The exposed set lives in a settings dialog. An IDE upgrade can add a tool and enable it without asking — IDEA 2026.1 shipped `apply_patch` (writes files) enabled and absent from JetBrains' documented tool list. JetBrains Settings Sync propagates the set across IDEs and machines, so a change made in another JetBrains IDE can reach this one. So the policy below is a claim about how the IDE is *configured*, not a property of the system. Verify it rather than trusting it: `ide_preflight.py --discover`, installed with claude-pod at `~/.config/claude-pod/`, enumerates the live set and reports any tool outside policy. `claude-pod` runs the same check at every pod launch.

### Exposed (five)

| Tool | Why it earns a slot |
|------|---------------------|
| `get_file_problems` | GoLand inspections per file: unresolved references, unused declarations, shadowing, unchecked errors, vet-class issues. Also the only tool that refreshes the IDE's view of disk before answering — the coherence mechanism the other four depend on. |
| `search_symbol` | Semantic symbol lookup. Resolves an identifier; `Grep` only matches text. |
| `get_symbol_info` | Quick-doc at a position: signature, type, docs, and declaration code when resolvable — the route to dependency/stdlib sources without a file-read tool. |
| `get_project_modules` | Resolved Go module list. |
| `get_project_dependencies` | Resolved module dependency set. Backs the dependency security check and the health probe. |

For what each tool returns in detail, see the [`goland` skill § Available tools](SKILL.md).

### Excluded by policy

| Group | Examples | Reason |
|-------|----------|--------|
| Writes and refactorings | `apply_patch`, `rename_refactoring`, `create_new_file`, `replace_text_in_file`, `reformat_file` | Claude Code is the sole writer. See the rename note below. |
| Duplicate of the canonical path | `build_project`, `search_text`, `search_regex`, `find_files_by_glob`, `get_file_text_by_path` | The native tools and the Go toolchain gate already produce these answers. See the `build_project` note below. |
| Off-stack and authoring | database tools, the inspection-script group | Unused by this project. The inspection-script group authors custom GoLand inspections, not application code. |

**On `build_project`.** It fails test 1 on its own terms: compiler errors are exactly what `go build ./...` reconstructs, from the same disk, and the toolchain gate is canonical anyway. The IDE build was a faster route to identical information, never new information. It fails test 2 more narrowly than the Java case does (Go has no build script to poison), but it still puts the IDE on the execution path. It runs the toolchain, and `#cgo` directives in ordinary source files pass flags to the C compiler and linker — a documented code-execution vector. Neither test needs the other.

It also never did the job its removal appears to cost. The IDE's compile action does not refresh source VFS or PSI — verified in `plugins/mcp-server/` in `JetBrains/intellij-community`, the shared platform behind GoLand — so a green `build_project` never made `search_symbol` current. `get_file_problems` is what refreshes. Losing the IDE build costs a few seconds' earlier notice inside a TDD cycle that compiles anyway when it runs its tests.

**On renames.** Symbol-aware rename is the correct way to rename; text find-and-replace over- and under-matches references. So the agent proposes a rename and the human runs it through GoLand's UI (preview, conflict resolution, undo). Rename correctness stays; Claude Code stays the only programmatic writer.

## Right-source the gaps

Specific questions are answered better outside the MCP server.

| Need | Use | Not |
|------|-----|-----|
| Go inspection problems (vet-class, unused, shadowing) | `get_file_problems` | — |
| DB schema and queries | Database Tools / DataGrip | inspections |
| Headless problem detection (CI) | `go vet` / `golangci-lint` / `staticcheck` / Qodana | the live server |

## Runtime usage and coherence

This document stops at setup and the tool-set rationale. The operating rules live in the skills:

- When to call which tool, index-lag coherence, and the resolution-claim citation rule — [`goland` skill](SKILL.md).
- The connection health check (connected ≠ usable) — [`goland-doctor` skill](../goland-doctor/SKILL.md).

Exposing a tool does not make the agent use it. The skill converts available into used.
