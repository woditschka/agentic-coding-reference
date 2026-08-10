# Cross-Tool Strategy: Compatibility, IDE Paths, and Tool Choice

**Status:** Version-stamped snapshot — model names, GA dates, provider counts, and version pins reflect each tool's state as of mid-2026. `update-research` refreshes this document; the durable architecture lives in [`specialist-agent-workflow.md`](specialist-agent-workflow.md).
**Primary Tool:** Claude Code · **Secondary:** GitHub Copilot CLI, OpenCode, Junie CLI

> **Scope note:** This guide describes cross-tool support for the sample projects (`samples/go/`, `samples/java-spring-boot/`, and `samples/generic/`). The root of this reference monorepo is itself maintained with Claude Code only — the multi-tool layout (`.github/agents/`, `.opencode/`, `.junie/`) lives inside each sample, not at the root.

---

## 1. Cross-Tool Compatibility

### Rules Files

| Feature | Claude Code | GitHub Copilot CLI | OpenCode | Junie CLI |
|---|---|---|---|---|
| **Primary rules file** | `CLAUDE.md` (project root) | `CLAUDE.md`, `AGENTS.md`, or `.github/copilot-instructions.md` | `AGENTS.md` (project root) | `CLAUDE.md` or `AGENTS.md` (via config) |
| **Reads `CLAUDE.md`?** | Yes (native) | Yes (always-on, native) | Yes (fallback if no `AGENTS.md`) | Yes (via `guidelines-location`) |
| **Reads `AGENTS.md`?** | No | Yes (always-on, additive) | Yes (native, takes precedence) | Yes (native default) |
| **Global rules** | `~/.claude/CLAUDE.md` | `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` env var | `~/.config/opencode/AGENTS.md` | `~/.junie/config.json` with `guidelines-location` |
| **Nested/directory rules** | `CLAUDE.md` in subdirs | `*.instructions.md` files in `.github/instructions/` (with `applyTo` frontmatter) | Glob patterns in `opencode.json` | `guidelines-location` in `.junie/config.json` (no nested glob discovery) |

**Decision: Use `CLAUDE.md` only. Do not create `AGENTS.md` or `copilot-instructions.md`.**

All four tools read `CLAUDE.md` at the project root natively or via straightforward configuration. Claude Code reads it as the primary rules file. Copilot CLI reads it as always-on instructions. OpenCode reads it as a fallback when no `AGENTS.md` exists. Junie CLI is configured to use it via `.junie/config.json`.

Creating `AGENTS.md` breaks this: Claude Code never reads `AGENTS.md` at all, Copilot CLI merges both additively (duplication or conflict), and OpenCode stops reading `CLAUDE.md`. Creating `.github/copilot-instructions.md` has the same problem — Copilot CLI merges it with `CLAUDE.md`, and there is nothing it can hold that `CLAUDE.md` cannot. One file. Four tools. Zero duplication.

**Path-specific instructions are the exception.** When different file types need different rules (e.g., stricter security rules for `src/auth/**`), use `.github/instructions/*.instructions.md` files with `applyTo` YAML frontmatter. These are Copilot-only, load only when matching files are active, and supplement `CLAUDE.md` without duplicating it:

```markdown
---
applyTo: "src/auth/**"
---
All authentication code must use parameterized queries. Never concatenate user input into SQL strings.
```

### Skills

| Feature | Claude Code | GitHub Copilot CLI | OpenCode | Junie CLI |
|---|---|---|---|---|
| **Skill format** | `SKILL.md` + YAML frontmatter | `SKILL.md` + YAML frontmatter | `SKILL.md` + YAML frontmatter | `SKILL.md` + YAML frontmatter |
| **Project path** | `.claude/skills/*/SKILL.md` | `.claude/skills/*/SKILL.md`, `.github/skills/*/SKILL.md` | `.claude/skills/*/SKILL.md` (fallback), `.opencode/skills/*/SKILL.md`, `.agents/skills/*/SKILL.md` | `.junie/skills/`, `.claude/skills/` (via config) |
| **Global path** | `~/.claude/skills/*/SKILL.md` | `~/.claude/skills/*/SKILL.md`, `~/.copilot/skills/*/SKILL.md` | `~/.claude/skills/*/SKILL.md` (fallback), `~/.config/opencode/skills/*/SKILL.md` | `~/.junie/skills/` |
| **Auto-invocation** | Yes (by description match) | Yes (by description match) | Yes (by description match) | Yes (by description match) |
| **Slash command** | `/skill-name` | `/skill-name` | `/skill-name` | `/skill-name` |
| **Supporting files** | Scripts, templates, references in skill dir | Scripts, examples in skill dir | Scripts, templates in skill dir | Scripts, templates, references in skill dir |

**Decision: Use `.claude/skills/` as the single canonical location.**

All four tools discover skills at `.claude/skills/*/SKILL.md`. OpenCode also checks `.opencode/skills/` and `.agents/skills/`, but `.claude/skills/` works everywhere. Don't duplicate. The Agent Skills open standard means the same `SKILL.md` file with the same YAML frontmatter is portable across all four tools.

### Agents / Subagents

| Feature | Claude Code | GitHub Copilot CLI | OpenCode | Junie CLI |
|---|---|---|---|---|
| **Agent format** | `.md` with YAML frontmatter | `.agent.md` with YAML frontmatter | `.md` with YAML frontmatter or JSON in `opencode.json` | `.md` with YAML frontmatter |
| **Project path** | `.claude/agents/*.md` | `.github/agents/*.agent.md` | `.opencode/agents/*.md` | `.junie/agents/*.md` (also reads `.agents/`) |
| **Global path** | `~/.claude/agents/*.md` | `~/.copilot/agents/*.agent.md` | `~/.config/opencode/agents/*.md` | `~/.junie/agents/*.md` |
| **Key frontmatter** | `name`, `description`, `tools`, `disallowedTools`, `model`, `effort`, `maxTurns`, `hooks`, `skills`, `isolation`, `background` | `name`, `description`, `tools`, `model` (supports fallback chains), `hooks`, `mcp-servers`, `handoffs` | `description`, `mode`, `model`, `temperature`, `permission`, `steps`, `hidden`, `top_p`, `color`, `prompt`, `disable` | `name`, `description`, `tools`, `disallowedTools`, `model`, `reasoningLevel`, `skills`, `allowPromptArgument` |
| **Subagent spawning** | Automatic (by description) or explicit | Automatic or explicit | Automatic or `@mention` | Automatic (by description) |
| **Multi-agent coord** | Agent Teams (experimental) | `/fleet` (parallel subagents) | Not built-in | Automatic delegation |
| **Background delegation** | `background` frontmatter field | `&` prefix delegates to cloud agent | Not built-in | Non-interactive (headless) mode |
| **Built-in subagents** | Explore, Plan, General-purpose, Bash | Explore, Task, Code Review, Plan | Build, Plan, General, Explore | Default (reasoning), Plan |

**Decision: Thin agents, portable skills — define agents per-tool.**

Agent definitions are tool-specific. The YAML frontmatter fields differ. The tool permissions differ. The model selection syntax differs. Don't try to make one file work everywhere. Instead, keep the workflow intelligence in skills (portable) and keep agent definitions thin — just persona, tool restrictions, and model choice. This is the **thin agents, portable skills** principle, and it makes per-tool duplication cheap: each agent file is hand-owned frontmatter plus a body rendered from the `.claude` copy.

Junie CLI's tool-group vocabulary (`Read`, `Bash`, `Glob`, `Grep`, `Write`, `Edit`, `WebSearch`, `AskUserQuestion`) matches Claude Code's exactly. Porting a Claude agent to `.junie/agents/` is therefore mechanical: rename `effort` to `reasoningLevel` and drop `maxTurns`. Junie has no per-agent turn cap; the global `time-limit` in `.junie/config.json` covers it.

### The Gotchas

1. **Multiple rules files cause additive merging in Copilot CLI and fallback loss in OpenCode.** Copilot CLI reads all of `CLAUDE.md`, `AGENTS.md`, and `copilot-instructions.md` additively — conflicting guidance produces non-deterministic behavior. If `AGENTS.md` exists, OpenCode stops reading `CLAUDE.md`. The fix: `CLAUDE.md` only.

2. **Copilot CLI skills path duality.** Copilot CLI checks both `.github/skills/` and `.claude/skills/`. Use `.claude/skills/` for cross-tool portability, but know that Copilot-specific skills (those using Copilot-only features) should go in `.github/skills/`.

3. **OpenCode `permission` is singular and pattern-matched.** Markdown agents and `opencode.json` both use `permission` with `allow`/`ask`/`deny` values; keys match as wildcard patterns against tool names (`mymcp_*` denies one MCP server). The documented permission keys: `read`, `edit`, `glob`, `grep`, `bash`, `task`, `skill`, `lsp`, `question`, `webfetch`, `websearch`, `external_directory`, `doom_loop`. The `edit` key governs `write`, `edit`, and `apply_patch` — there is no separate `write` or `mcp` key. An unlisted key falls to the tool's defaults, so the harness agents state their denials explicitly. Web fetch is `webfetch`; the iteration cap is `steps`; the boolean `tools` map and `maxSteps` are deprecated. The `mode` config option is deprecated — modes configure through the `agent` option. The battery's frontmatter-vocabulary step pins these key sets for the shipped agents, plus the harness's own `toolCallBudget` metadata key. An out-of-schema key (`permissions`, `fetch`, `max_steps`) fails tier 0 in the harness source; consumer copies inherit fixes through materialize, not a local gate. The pins transcribe each tool's documentation, not a verified runtime load; `update-research` re-checks them against upstream.

4. **Copilot path-specific instructions are Copilot-only.** `.github/instructions/*.instructions.md` files with `applyTo` are supported by Copilot coding agent, Copilot code review, and Copilot CLI. They aren't read by Claude Code or OpenCode.

---

## 2. IDE Compatibility

**This project targets CLI use.** The committed agent definitions target Claude Code, GitHub Copilot CLI, OpenCode, and Junie CLI. This section exists for users who want to extend the same filesystem-based pipeline into an IDE workflow — it is not a maintained first-class target.

The pipeline runs unchanged in IDE plugins that delegate to the same CLIs: filesystem layout, skills, and `.scratch/` state are tool-agnostic. Plugin ecosystems diverge on where they look for skills and agents, and not every CLI feature (parallel subagents, `/fleet`, Agent Teams) has an IDE equivalent today.

### Plugin Matrix

| IDE plugin | `CLAUDE.md` | `.claude/skills/` | Agents path | Notes |
|---|---|---|---|---|
| Claude Code — VS Code extension | Yes | Yes | `.claude/agents/` | Wraps the Claude Code CLI; behavior identical |
| Claude Code — IntelliJ plugin (Beta) | Yes | Yes | `.claude/agents/` | Wraps the Claude Code CLI; behavior identical |
| GitHub Copilot — VS Code | Yes (+ `copilot-instructions.md`) | Yes | `.github/agents/` | Agent skills shared with Copilot CLI and cloud agent |
| GitHub Copilot — JetBrains plugin | Partial (`copilot-instructions.md` primary) | Limited | `.github/agents/` | Chat/completion focus; no `/fleet` |
| JetBrains Junie (CLI + IDE) | Yes (via config) | Yes (via config) | `.junie/agents/` | First-class integration; supports JetBrains IDE awareness via `/ide` |
| Cursor / Windsurf | AGENTS.md / CLAUDE.md via convention | Windsurf reads `.claude/skills/` with Claude-config flag; native path is `.agents/skills/` | Tool-specific | OpenSkills-style wrappers can bridge skills, but add a dependency for what a symlink solves |

### Extending to an IDE Without Duplicating Content

Keep `.claude/skills/` as the single source. Where a tool insists on its own path, symlink instead of copy:

- **Junie:** Uses `.junie/config.json` to link `CLAUDE.md` and `.claude/skills/` — zero content duplication. Agents live in `.junie/agents/` per the per-tool pattern.
- **Cursor/Windsurf native path:** `.agents/skills → .claude/skills` when native discovery is preferred over the Claude-config flag.
- **Agent definitions** stay per-tool — this is §1's [thin agents, portable skills](#agents--subagents) principle. Because agents carry only persona and frontmatter, per-tool duplication is cheap, and rendering the bodies from the `.claude` copy removes what little remains.

Symlinks work on Linux/macOS natively and on Windows with `git config core.symlinks true`. Do not commit duplicated skill content.

### A JetBrains IDE as a Semantic Oracle

The plugin matrix above covers running the pipeline *inside* an IDE. A separate, opposite option exists: the CLI queries a running IDE's MCP server — IntelliJ IDEA for Java, GoLand for Go — as a read-only semantic oracle for resolved types, references, and inspections; the project build stays the only compiler. The doctrine — the read-only policy, clean degradation to native tools, and the exposed-set drift warning — is owned by the [Adoption Guide § JetBrains Semantic Oracle](adoption-guide.md#jetbrains-semantic-oracle); this table is the cross-tool map:

| Concern | Where it lives (Java / Go) |
|---|---|
| Setup and exposed-tool rationale | [`intellij-mcp-integration.md`](../samples/java-spring-boot/.claude/skills/intellij-idea/intellij-mcp-integration.md) / [`goland-mcp-integration.md`](../samples/go/.claude/skills/goland/goland-mcp-integration.md) |
| Runtime routing and the resolution-claim citation rule | `intellij-idea` skill / `goland` skill |
| Connection health check (connected ≠ usable) | `intellij-idea-doctor` skill / `goland-doctor` skill |

**Maturity:** IntelliJ IDEA and GoLand bundle and enable the MCP server by default since 2025.2. Per-client wiring status — which clients are wired, working, or gated upstream — lives in the integration docs above, each carrying the version-stamped client table. Those two samples ship this integration — IntelliJ IDEA in Java Spring Boot, GoLand in Go.

---

## 3. Tool Comparison: Decision Framework

Each tool's capabilities below are a snapshot; the `Status:` line at the top of this document carries the date, and `update-research` refreshes it. Read the comparison for the durable shape of each tool's strengths, not the version-stamped specifics.

### When to Use Claude Code

**Use it when:**
- The primary workflow is terminal-based coding
- Review fan-out needs parallel subagent execution
- The team standardizes on Anthropic models
- The workflow leans on the skill and agent features listed below — most have no equivalent in the other three tools

**Where it's strongest:**
- Subagent architecture ships four built-in agents — Explore, Plan, General-purpose, Bash — that cover the common delegation needs out of the box
- Subagent configuration surface covers `effort`, `maxTurns`, `disallowedTools`, inline `hooks`, `skills` preloading, `isolation: worktree` for conflict-free parallel work, and `background` mode
- Skills system supports `context: fork`, `agent:` delegation, dynamic context injection, and `allowed-tools` scoping
- Hooks (`PreToolUse`, `PostToolUse`, `Stop`, `SubagentStop`, `SessionStart`) give fine-grained control, including agent-based hooks that spawn verification subagents
- Plugin ecosystem with marketplaces for distributing skills, agents, hooks, and MCP servers

**Where it falls short:**
- Claude models only — no GPT, no Gemini, no open models
- Core system prompt is not customizable without third-party tools
- Agent Teams is experimental with known limitations
- Pro plan rate limits hit quickly with parallel subagents

### When to Use OpenCode

**Use it when:**
- Multi-provider flexibility is needed (75+ providers)
- The workflow splits models — e.g. Gemini for exploration, Claude for implementation
- Cost optimization routes cheap tasks to cheaper models
- The team has mixed model subscriptions
- Full control over system prompts matters

**Where it's strongest:**
- Provider-agnostic — any model, any provider, per-agent model selection; powered by Models.dev provider list
- Fully open-source and customizable — everything is a markdown file
- TUI with Vim-like keybindings; Tauri desktop app on all platforms
- Agent definitions are more granular — `permission` (wildcard-matched per tool name), `temperature`, `steps`, `top_p`, `hidden`, `task` permission for controlling which subagents an agent can invoke, `color` for UI customization
- Skill permissions with pattern-based access control (`allow`/`deny`/`ask`) per agent
- GitHub agent for repository automation (`opencode github install`)
- ACP (Agent Client Protocol) support for integration with external tools

**Where it falls short:**
- No equivalent to Agent Teams — no built-in multi-session orchestration
- Community-driven, not backed by a model provider — new Claude Code features (skills frontmatter fields, Agent Teams, hooks surface) reach OpenCode only after a community reimplementation, if at all
- Skills ecosystem is smaller; skill frontmatter only recognizes `name`, `description`, `license`, `compatibility`, `metadata` (no `allowed-tools`, `context: fork`, or `agent:` delegation like Claude Code)
- Hooks exist only via JavaScript/TypeScript plugin system — no declarative frontmatter or JSON-config hooks like Claude Code; requires writing JS/TS code in `.opencode/plugins/`

### When to Use GitHub Copilot CLI

**Use it when:**
- Native GitHub integration (issues → PRs → reviews) from the terminal is needed
- Async cloud-based work should run through the Copilot coding agent
- `/fleet` parallel subagent execution with multi-model support is needed
- The organization has a Copilot Enterprise subscription
- One tool must offer multi-model choice (Claude Opus 5, GPT-5.3-Codex, Gemini 3 Pro)

**Where it's strongest:**
- Reads `CLAUDE.md` natively — no redirect file needed, shares rules with Claude Code and OpenCode
- Full terminal-native coding agent (GA Feb 2026) with autopilot mode, `/fleet` for parallel subagent execution, built-in specialized agents (Explore, Task, Code Review, Plan), and cloud delegation with `&` prefix
- Multi-model support with model fallback chains in agent profiles: `model: ['Claude Opus 5', 'GPT-5.3-Codex']`
- Path-specific `.instructions.md` files with `applyTo` for granular rules per file type
- Copilot coding agent runs asynchronously in the cloud — `&` prefix delegates, `/resume` pulls results back
- Organization-level custom agents via `.github-private` repos
- Native MCP server integration in agent profiles (GitHub MCP and Playwright MCP enabled by default)
- Plugin system with marketplaces
- Plan mode → autopilot + `/fleet` workflow for large tasks

**Where it falls short:**
- CLI and coding agent are different surfaces — agent profiles aren't fully interchangeable (`argument-hint` ignored by coding agent on GitHub.com)
- Custom agents are a newer feature, less battle-tested than Claude Code's subagents
- Context window is mediated through Copilot's Agent Control Plane — not raw model context like Claude Code's direct model-context window
- `/fleet` orchestration overhead may not suit small tasks
- Premium request economics — each subagent spawn counts as a separate billable request under Copilot's premium-request model

### Cross-Tool Strategy Matrix

| Scenario | Recommended Tool | Why |
|---|---|---|
| Full pipeline execution (stages 4–5) | Claude Code | Four built-in subagents, skills integration, coordinator pattern |
| Parallel review execution | Claude Code or Copilot CLI | CC subagents for tight integration; CLI `/fleet` for GitHub-native workflows |
| Cost-sensitive exploration | OpenCode | Route to Haiku/Gemini Flash for read-only tasks |
| Terminal-native autonomous work | Copilot CLI or Claude Code | CLI autopilot + `/fleet` for GitHub-integrated flow; CC for Anthropic-native flow |
| Async PR creation from issues | Copilot CLI | `&` delegates to cloud coding agent; `/resume` pulls results back |
| Cross-model quality comparison | Copilot CLI or OpenCode | Both support multi-model; OpenCode has 75+ providers, CLI has Claude/GPT/Gemini |
| Enterprise-wide standards | Copilot CLI | Organization agents via `.github-private`, instruction inheritance, policy controls |
| Cloud-delegated background tasks | Copilot CLI | `&` prefix delegates to cloud agent, freeing terminal; `/resume` to check progress |

---

## 4. Sources

### Community
- [awesome-copilot](https://github.com/github/awesome-copilot) — community agents, skills, and instructions
- [anthropics/skills](https://github.com/anthropics/skills) — cross-compatible skills marketplace
- [everything-claude-code](https://github.com/affaan-m/everything-claude-code) — cross-harness agent optimization

### Claude Code
- [Agent Teams documentation](https://code.claude.com/docs/en/agent-teams) — multi-session orchestration, team creation, teammate communication
- [Custom subagents](https://code.claude.com/docs/en/sub-agents) — agent format, built-in subagents, YAML frontmatter reference
- [Skills documentation](https://code.claude.com/docs/en/skills) — SKILL.md format, frontmatter fields, progressive disclosure, auto-invocation
- [Agent Skills open standard](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) — portable skill format specification

### OpenCode
- [Rules documentation](https://opencode.ai/docs/rules/) — AGENTS.md format, CLAUDE.md fallback behavior, precedence rules
- [Agents documentation](https://opencode.ai/docs/agents/) — agent types, markdown/JSON formats, the permission model
- [Agent Skills](https://opencode.ai/docs/skills/) — skill discovery paths, frontmatter fields, Claude Code compatibility

### GitHub Copilot CLI
- [Copilot CLI overview](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli-agents/overview) — terminal-native agents, subagents, autopilot mode
- [Fleet mode](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/fleet) — parallel subagent execution with `/fleet`
- [CLI custom agents](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-custom-agents-for-cli) — agent profiles, creation wizard, `.agent.md` format
- [CLI custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions) — CLAUDE.md, AGENTS.md, GEMINI.md support, path-specific `.instructions.md`
- [CLI agent skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/create-skills) — SKILL.md format, project/personal paths, skill discovery
- [Custom agents configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration) — full YAML reference, MCP servers, tool names
- [Custom agents concepts](https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-custom-agents) — agent profiles, organization-level agents
- [Custom instructions](https://docs.github.com/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot) — copilot-instructions.md, CLAUDE.md, AGENTS.md, instruction hierarchy
- [Autopilot mode](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/autopilot) — autonomous task completion without per-step approval
