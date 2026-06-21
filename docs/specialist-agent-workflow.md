# Specialist Agent Workflow: Architecture & Cross-Tool Strategy

**Status:** Validated core (architecture, principles, document architecture, cross-tool portability) · Reference machinery (specialist pipeline, JSONL handoff contract, reviewer-roster fan-out) is operational; cost-effectiveness is still being measured against internal session telemetry and will be revised as evidence accumulates.
**Primary Tool:** Claude Code · **Secondary:** GitHub Copilot CLI, OpenCode, Junie CLI

> **Scope note:** This guide describes cross-tool support for the sample projects (`samples/go/` and `samples/java-spring-boot/`). The root of this reference monorepo is itself maintained with Claude Code only — the multi-tool layout (`.github/agents/`, `.opencode/`, `.junie/`) lives inside each sample, not at the root.

---

## 1. Architecture Overview

### Design Principles

This architecture treats the filesystem as the coordination layer. Not memory. Not message passing. Not shared context windows. Files on disk are auditable, interruptible, tool-agnostic, and survive session crashes. Every handoff between agents is a file write. Every blocking condition is a status string in a known location.

The pipeline enforces separation of concerns: agents that think about *what* to build never touch code. Agents that write code never decide *what* to build. The coordinator never implements anything. Violate this boundary and context pollution makes every agent worse.

### The Four Nested Loops

The pipeline does not run as a linear handoff. It runs as four concentric loops — inner (TDD cycle), middle (PRD + design triage and review-until-approved for the slice), outer (slice selection), architectural (planned structural review). The inner loop's design-check step routes to the middle loop via consultation, so the loop nesting is a feature of the design discovery, not rework.

The four-loop structure is an agentic descendant of XP's nested feedback loops (Beck); each loop iterates over a different unit and surfaces a different layer of design question. The loop model is methodology and lives in [`agentic-harness.md`](agentic-harness.md). Each sample carries the agent-facing copy at `.claude/skills/pipeline-handoff/agentic-harness.md` (content-equivalent; links adjusted for location).

### Pipeline Flow

**Full pipeline** (new features, happy path):

```text
coordinator → product-requirements-expert → system-design-expert → feature-implementer → reviewer roster (parallel) → change-grader
                .scratch/handoff.jsonl       .scratch/handoff.jsonl    .scratch/handoff.jsonl    .scratch/handoff.jsonl    .scratch/handoff.jsonl
                (prd-entry)                  (design-block)            (build-pass)              (review-feedback, one per reviewer)   (grader-features + grader-verdict)
```

**Failure-recovery loop** (build/test fails):

```text
feature-implementer (quality gate fails)
    → handoff.jsonl: build-failure (retry 1–2) → coordinator → feature-implementer (retry with error context)
    → handoff.jsonl: build-failure (retry 3)   → coordinator → system-design-expert (re-triage)
    → handoff.jsonl: design-block (new verdict + supersedes_record_at) → coordinator → feature-implementer (retry reset)
```

**Shortcuts** (coordinator decides):

```text
Bug fix         → feature-implementer → reviewer roster (parallel)
Arch question   → system-design-expert (standalone)
Review only     → any single reviewer (standalone)
```

Each arrow is an append to `.scratch/handoff.jsonl`. The coordinator validates each new record against its JSON Schema (`schemas/scratch/<type>.schema.json`) at every transition; malformed or missing records bounce back to the upstream agent without consuming the next dispatch. A `design-block` with `verdict: "conflicting"` or a `review-feedback` finding tagged `escalate` halts the pipeline; a `build-failure` triggers the retry loop. The coordinator reads state, routes, and never implements.

### Handoff Signals

Handoff state lives in `.scratch/handoff.jsonl` — one JSON record per line, append-only. Each record carries a `type` discriminator that picks one of eleven schemas in `schemas/scratch/`. The per-type table — producer and schema for every record type — is the Handoff Contract in [`agentic-harness.md`](agentic-harness.md#handoff-contract); this section adds only what that contract does not carry.

Every record carries `type`, `req_id` (`^REQ-[A-Z]+-[0-9]{3}$`), `ts` (ISO 8601), and `author`. The active state for routing is the latest record per `(req_id, type)`. Every substantive agent appends a `dispatch-start` record as its first tool call; `pipeline-coordinator` and the terminal `change-grader` are exempt.

**Why JSONL over per-stage markdown.** A single append-only log with typed records makes the schema validation above uniform — one gate at every transition, not a different check per stage. Append-only records also give a replayable audit trail of pipeline state, where mutable per-stage markdown files lost history on overwrite.

**Consultation roundtrips preserve the requester's active state.** When a `consultation-request` is the latest record, the coordinator dispatches the target specialist in consultation mode; the matching `consultation-response` routes control back to the requester, not forward to the next stage. Consultations let the inner-loop discover design decisions worth crystallizing without advancing the pipeline.

**Blocking signals that halt the pipeline:**

- `verdict: "conflicting"` (on a `design-block`) — this slice contradicts current design; coordinator surfaces to the user with the contradiction
- A `build-failure` record — triggers the retry loop shown in the failure-recovery diagram above
- A finding with `tag: "escalate"` (on a `review-feedback`) — the coordinator appends to `.scratch/escalations.md`

### Why File-Based Coordination

Agent Teams (Claude Code's experimental multi-session feature) uses direct messaging between teammates and a shared task list. It works. It also requires enabling an experimental capability, burns 3–7x the tokens of a single session, and has known limitations around session resumption and shutdown. The file-based state machine works with any model, any tool, any provider. It costs nothing extra. It's inspectable with `cat`. It survives session crashes. It's version-controllable with git.

The samples do enable the experimental agent-teams capability — but for one narrow purpose, not for coordination. A `PreToolUse` hook (`.claude/hooks/sendmessage-continue-only.sh`) constrains the teammate-messaging channel to the literal string `continue`, used only to resume a truncated dispatch in place. The hook denies every other message and fails closed, so no new instructions can ride the channel. All new work still enters as a schema-validated record on `.scratch/handoff.jsonl`; file-based coordination remains the architecture.

Real-time cross-referencing between reviewers — a security finding reshaping the code-quality review — is out of scope here; the `.scratch/` state machine does the job.

### Spec-Driven Development

The pipeline is not just a sequence of agents — it is driven by two living specification documents that agents treat as authoritative. Without these, agents fill in blanks by guessing. With them, every implementation decision traces back to a requirement.

#### Document Authority

Each living document has a single owner agent; only the owner writes to it. When two agents can modify one file, conflicts are inevitable and neither version is authoritative. The full owner-per-document roster is defined once in [`harness-project-api.md`](harness-project-api.md#file-roster), with the memory/feedback role of each in [`agentic-harness.md`](agentic-harness.md#document-architecture). One document sits outside that roster: `CLAUDE.md` is the human-owned meta layer — build commands, agent workflow, commit conventions — read by every tool.

#### The What/How Boundary

The PRD describes behavior in language-agnostic terms. It never contains code, class names, function signatures, or language-specific constructs. The litmus test: **if it would change when switching from Go to Rust (or Java to Kotlin), it belongs in system-design.md, not the PRD.**

| PRD (What) | System Design (How) |
|---|---|
| "The system retries failed connections up to 3 times" | "RetryPolicy struct with exponential backoff; see `internal/client/retry.go`" |
| "Constraint: buffer holds 10,000 points" | "Constants: `MaxBufferSize = 10_000` in `internal/config/defaults.go`" |
| Acceptance criteria in Given/When/Then | Package structure, interface contracts, state machine tables |

Full ownership rules and cross-reference formats live in the [`document-writing` skill](../harness/core/.claude/skills/document-writing/documentation-standards.md); the roster itself is defined by [`harness-project-api.md`](harness-project-api.md).

#### How Specs Flow Through the Pipeline

Two tiers of memory carry a feature from intent to code: durable specs the agents own, and a short-lived handoff log they append to per feature. The figure traces one feature through both.

<p align="center">
  <img src="images/spec-flow.drawio.png" width="520" alt="Spec flow with a durable long-term memory band on top (docs/prd.md, ubiquitous-language.md, docs/system-design.md) feeding a nested per-feature pipeline: the product-requirements-expert and system-design-expert read and write those specs, then append a record (prd-entry, design-block) to the short-term .scratch/handoff.jsonl band inside the pipeline; the feature-implementer reads both records and the full specs, and routes a requirement or design gap back to the owning agent as a consultation-request — it never edits long-term memory directly.">
</p>

*The product-requirements-expert also writes `docs/ubiquitous-language.md` as terms resolve during requirements interviews — the diagram shows the prd flow as the canonical example.*

The pipeline writes to working memory in `.scratch/` that extracts the relevant slice of long-term memory for the current feature. The implementer reads the handoffs and the full specs, but never modifies `docs/prd.md`, `docs/system-design.md`, or `docs/ubiquitous-language.md` directly. When it discovers a requirement gap or design conflict during TDD, it routes through a consultation-request to the owning agent:

- **Requirement gap** → append `consultation-request` targeting product-requirements-expert. Log in the implementation plan's Feedback Log.
- **Design gap** → append `consultation-request` targeting system-design-expert. Pause; resume the inner loop when the matching consultation-response arrives.
- **Architecture misfit** → stop; append `consultation-request` flagged as architectural. The next triage will likely return `conflicting` or `foundational` if the misfit is real.

This routing is defined in the `tdd-workflow` skill's design-check decision tree, which runs before each TDD cycle.

#### Long-Term Memory vs Working Memory

The two-tier memory model — durable specs in `docs/` versus the per-feature handoff log in `.scratch/` — is defined in [`agentic-harness.md`](agentic-harness.md#disciplines-as-memory-and-feedback). Two tier members matter to cross-tool use specifically:

- **`schemas/scratch/*.json`** is committed long-term memory: the JSON Schema for each handoff record type, read identically by every tool.
- **`MEMORY.md`** (optional) is cross-session memory — a high-level summary of recent work that a user or tool maintains to switch between CLI tools mid-feature without losing state.

---

## 2. Cross-Tool Compatibility

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

**Path-specific instructions are the exception.** If you need different rules for different file types (e.g., stricter security rules for `src/auth/**`), use `.github/instructions/*.instructions.md` files with `applyTo` YAML frontmatter. These are Copilot-only, load only when matching files are active, and supplement `CLAUDE.md` without duplicating it:

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
| **Key frontmatter** | `name`, `description`, `tools`, `disallowedTools`, `model`, `effort`, `maxTurns`, `hooks`, `skills`, `isolation`, `background` | `name`, `description`, `tools`, `model` (supports fallback chains), `hooks`, `mcp-servers` | `description`, `mode`, `model`, `temperature`, `permissions`, `hidden`, `top_p`, `color`, `max_steps` | `name`, `description`, `tools`, `disallowedTools`, `model`, `reasoningLevel`, `skills`, `allowPromptArgument` |
| **Subagent spawning** | Automatic (by description) or explicit | Automatic or explicit | Automatic or `@mention` | Automatic (by description) |
| **Multi-agent coord** | Agent Teams (experimental) | `/fleet` (parallel subagents) | Not built-in | Automatic delegation |
| **Background delegation** | `background` frontmatter field | `&` prefix delegates to cloud agent | Not built-in | Non-interactive (headless) mode |
| **Built-in subagents** | Explore, Plan, General-purpose, Bash | Explore, Task, Code Review, Plan | Build, Plan, General, Explore | Default (reasoning), Plan |

**Decision: Thin agents, portable skills — define agents per-tool.**

Agent definitions are tool-specific. The YAML frontmatter fields differ. The tool permissions differ. The model selection syntax differs. Don't try to make one file work everywhere. Instead, keep the workflow intelligence in skills (portable) and keep agent definitions thin — just persona, tool restrictions, and model choice. This is the **thin agents, portable skills** principle, and it makes per-tool duplication cheap: each agent file is frontmatter plus a reference to a shared prompt body.

Junie CLI's tool-group vocabulary (`Read`, `Bash`, `Glob`, `Grep`, `Write`, `Edit`, `WebSearch`, `AskUserQuestion`) matches Claude Code's exactly. Porting a Claude agent to `.junie/agents/` is therefore mechanical: rename `effort` to `reasoningLevel` and drop `maxTurns`. Junie has no per-agent turn cap; the global `time-limit` in `.junie/config.json` covers it.

### The Gotchas

1. **Multiple rules files cause additive merging in Copilot CLI and fallback loss in OpenCode.** Copilot CLI reads all of `CLAUDE.md`, `AGENTS.md`, and `copilot-instructions.md` additively — conflicting guidance produces non-deterministic behavior. If `AGENTS.md` exists, OpenCode stops reading `CLAUDE.md`. The fix: `CLAUDE.md` only.

2. **Copilot CLI skills path duality.** Copilot CLI checks both `.github/skills/` and `.claude/skills/`. Use `.claude/skills/` for cross-tool portability, but know that Copilot-specific skills (those using Copilot-only features) should go in `.github/skills/`.

3. **OpenCode `tools` vs `permissions` split.** In JSON config (`opencode.json`), use `tools` with boolean values (`write: true`). In markdown agent files, use `permissions` with `allow`/`deny`/`ask` values. The `mode` config option for switching modes is deprecated — configure modes through the `agent` option instead.

4. **Copilot path-specific instructions are Copilot-only.** `.github/instructions/*.instructions.md` files with `applyTo` are supported by Copilot coding agent, Copilot code review, and Copilot CLI. They aren't read by Claude Code or OpenCode.

---

## 3. IDE Compatibility

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
- **Cursor/Windsurf native path:** `.agents/skills → .claude/skills` if you prefer native discovery over enabling the Claude-config flag.
- **Agent definitions** stay per-tool — this is §2's [thin agents, portable skills](#agents--subagents) principle. Because agents carry only persona and frontmatter, per-tool duplication is cheap, and a shared prompt-body file removes what little remains.

Symlinks work on Linux/macOS natively and on Windows with `git config core.symlinks true`. Do not commit duplicated skill content.

### IntelliJ as a Semantic Oracle (Claude Code only)

The plugin matrix above covers running the pipeline *inside* an IDE. A separate, opposite option exists: the CLI queries a running IDE's MCP server as a read-only semantic oracle and verifier. IntelliJ IDEA answers questions plain text cannot — resolved types, references, inspections — and confirms whether edits compile. The agent stays the sole writer; no exposed tool mutates a file. This removes write-coherence failure modes by construction; the one drift that remains is index lag.

This is optional harness tooling. When the server is absent, every workflow falls back to native tools plus the project build. The Java Spring Boot sample demonstrates the full setup — which six tools are exposed and why, the index-lag coherence rule, and a one-command health check.

| Concern | Where it lives |
|---|---|
| Setup and exposed-tool rationale | [`samples/java-spring-boot/.claude/skills/intellij-idea/intellij-mcp-integration.md`](../samples/java-spring-boot/.claude/skills/intellij-idea/intellij-mcp-integration.md) |
| Runtime routing and the resolution-claim citation rule | `intellij-idea` skill |
| Connection health check (connected ≠ usable) | `intellij-idea-doctor` skill |

**Maturity:** IntelliJ bundles and enables the MCP server by default since 2025.2. Claude Code is the wired-and-working client; the Java sample's Copilot CLI agents are wired ahead of an upstream fix (gated by [copilot-cli#2630](https://github.com/github/copilot-cli/issues/2630)). The Go sample does not ship this integration.

---

## 4. Capability Progression

The harness grew from a single prompt by adding one capability at a time, each closing a specific failure of the stage before it. This section traces that path — unaided prompt to coordinated specialist pipeline — so the cost of every layer is legible and a team can stop where its workload is met. Higher is not better. Coordinated routing (stage 4) is the steady state. Stage 5 only changes review execution from sequential to parallel — latency relief at no extra tokens. The far end is this project's demonstration, not a universal target. The tables below also mark where the current harness ends and the frontier begins — the project stops short of capabilities it judges unproven, by choice, not oversight.

### The path

Each stage keeps everything below it and adds one capability.

| Stage | Capability | Problem it closes | Memory or feedback it adds |
|:-:|---|---|---|
| 0 | Single generalist prompt | — | Nothing persists; output drifts within one session |
| 1 | Rules file (`CLAUDE.md`) | Re-explaining conventions every session | First long-term memory |
| 2 | Skills | Pasting the same procedure into prompts | Reusable procedural memory |
| 3 | Specialist subagents | One context juggling PRD, design, code, and review | Separation of concerns; isolated contexts |
| **4** | **Coordinated routing** — coordinator + handoff log + per-record schemas | A human hand-routing every handoff | Auditable working memory |
| 5 | Parallel review *execution* | Sequential roster review is the latency bottleneck | Faster feedback — same tokens, less wall-clock |

**Steady state: stage 4.** A coordinator automates routing. The four-reviewer roster — code-quality, test, security, doc — is the mandatory floor. It costs ~4× a single reviewer's tokens whether you run it sequentially or in parallel. Stage 5 is purely the execution mode: running that same roster in parallel trades concurrency for wall-clock, at no extra tokens. Add it once review latency is the measured bottleneck. The terminal `change-grader` — an advisory grade of how much human attention a passing change deserves — surfaces where a layer is or isn't paying off before adding any layer. The reference implementations ship the roster in parallel; an adopter may run it sequentially first and parallelize when wall-clock starts to hurt.

### The outer loop (running today)

Around the per-feature pipeline runs a slower review loop — the outermost of the four nested loops (see [`agentic-harness.md`](agentic-harness.md)). It catches drift on a periodic cadence and writes back to long-term memory. Today it reviews the reference itself, not application code:

| Skill | Reviews for drift in |
|---|---|
| `audit-consistency` | Go and Java samples vs. root docs, and vs. each other |
| `doctor` + `audit-docs` (per sample) | The `docs/` roster against the harness-project API; brief quality |
| `audit-agents` | Agent-config consistency and cross-tool parity |
| `research-update` | Upstream tool changes vs. the strategy doc |
| `deps-upgrade` | Pinned tool and dependency versions vs. upstream |

The loop is real and running — scoped to documentation and harness integrity.

### Beyond the current bar

The harness stops short of these by choice. None is built today.

| Frontier capability | Status | Why not here |
|---|---|---|
| Code-architecture structural review | Open extension | The same outer loop pointed at application code: detect modules drifting from their invariants, propose refactors, feed the system-design-expert. The reference is a documentation project with minimal demo code, so structural decay has little to act on. |
| Grade-closed optimization | Not built | The `change-grader`'s advisory grades are descriptive; nothing yet feeds them back to tune the harness automatically. |
| Long-horizon autonomous loops | Out of scope | Agents running unattended for hours or days. |
| Deterministic orchestration engine | Out of scope | Coordination runs through files, not a programmatic engine that guarantees control flow. |

Claiming the harness has reached the highest bar would contradict the project's own stance: the disciplines are the validated core; the machinery is one reference implementation, measured before trusted.

## 5. Project Structure

```text
your-project/
├── CLAUDE.md                          # [CC][CP][OC*][JU**] Project rules — the single source of truth
│                                      # CC=Claude Code, CP=Copilot CLI (always-on), OC=OpenCode (* fallback), JU=Junie (** via .junie/config.json)
│
├── .claude/
│   ├── agents/                        # [CC] Claude Code subagents — the nine pipeline agents
│   │   ├── pipeline-coordinator.md
│   │   ├── product-requirements-expert.md
│   │   ├── system-design-expert.md
│   │   ├── feature-implementer.md
│   │   ├── security-reviewer.md
│   │   ├── code-quality-reviewer.md
│   │   ├── test-reviewer.md
│   │   ├── doc-reviewer.md
│   │   └── change-grader.md
│   ├── hooks/                         # [CC] PreToolUse guard for the agent-teams resume channel
│   │   └── sendmessage-continue-only.sh
│   ├── skills/                        # [CC][CP][OC][JU] Portable skills — all tools read this
│   │   ├── pipeline-handoff/
│   │   │   └── SKILL.md              # Routing table, handoff conditions, state inventory
│   │   ├── tdd-workflow/
│   │   │   └── SKILL.md              # TDD cycle process, design-check decision tree
│   │   ├── prd-authoring/
│   │   │   └── SKILL.md              # PRD format, boundary rules, requirement template
│   │   ├── code-quality-gate/
│   │   │   └── SKILL.md              # Build/test/lint requirements, completion criteria
│   │   ├── review-checklist/
│   │   │   └── SKILL.md              # Quality gates for all reviewers
│   │   ├── code-quality-review/
│   │   │   └── SKILL.md              # Language-specific code quality checklist
│   │   ├── test-review/
│   │   │   └── SKILL.md              # Test quality checklist, security testing
│   │   ├── security-review/
│   │   │   └── SKILL.md              # Security checklists, threat model, severity
│   │   ├── document-writing/
│   │   │   └── SKILL.md              # Documentation review checklist, validation
│   │   ├── design-validation/
│   │   │   └── SKILL.md              # Architectural validation checklist
│   │   ├── change-grading/
│   │   │   └── SKILL.md              # Terminal advisory change-grade after review gate
│   │   ├── new-feature/
│   │   │   └── SKILL.md              # Clear scratch directory, start fresh context
│   │   ├── adr-template/
│   │   │   └── SKILL.md              # Architecture Decision Record format
│   │   ├── audit-agents/
│   │   │   └── SKILL.md              # Agent config consistency checks
│   │   ├── doctor/
│   │   │   ├── SKILL.md              # Deterministic docs/ roster validation (blocking)
│   │   │   └── templates/            # Materialization source for the six roster files (engine lives in scripts/)
│   │   ├── audit-docs/
│   │   │   └── SKILL.md              # Advisory judgment review of the project briefs
│   │   └── doc-sync/
│   │       └── SKILL.md              # Synchronize docs with codebase after implementation
│   └── settings.json                  # [CC] Claude Code hooks, env vars, permissions
│
├── .github/
│   ├── instructions/                  # [CP] Path-specific instructions (Copilot CLI only)
│   │   └── auth.instructions.md       # applyTo: "src/auth/**" — security-specific rules
│   ├── agents/                        # [CP] Copilot CLI custom agents — same nine agents, `.agent.md` suffix
│   └── skills/                        # [CP] Copilot-only skills (if any)
│
├── .opencode/
│   └── agents/                        # [OC] OpenCode agent definitions — same nine agents
│
├── .junie/
│   ├── config.json                    # [JU] Points Junie at CLAUDE.md and .claude/skills/
│   └── agents/                        # [JU] Junie agent definitions — same nine agents
│
├── .scratch/                          # [ALL] Pipeline state — gitignored
│   ├── handoff.jsonl                 # Append-only structured handoff log (all agents)
│   ├── implementation-plan.md        # TDD cycle plan (feature-implementer self-tracking)
│   ├── escalations.md                # Items requiring human decision
│   └── tmp/                          # Intermediate computation files
│
├── schemas/                           # [ALL] Handoff record schemas — committed, eleven record types
│   └── scratch/
│       ├── prd-entry.schema.json
│       ├── design-block.schema.json
│       ├── consultation-request.schema.json
│       ├── consultation-response.schema.json
│       ├── dispatch-start.schema.json
│       ├── review-feedback.schema.json
│       ├── build-failure.schema.json
│       ├── build-pass.schema.json
│       ├── design-doc-autofix.schema.json
│       ├── grader-features.schema.json
│       └── grader-verdict.schema.json
│
├── scripts/                           # [ALL] Deterministic harness helpers
│   ├── handoff.py                    # Sole write/query path for .scratch/handoff.jsonl
│   ├── test_handoff.py
│   ├── score-change.py               # Extracts the structural feature row from the diff
│   ├── test_score_change.py
│   ├── brief_doctor.py               # Docs/ roster validator (the doctor skill's engine)
│   ├── test_brief_doctor.py
│   ├── brief-expectations.toml       # The doctor's machine-checkable manifest
│   └── layout.toml
│
├── docs/                              # [ALL] Project-owned briefs — the harness-project API roster
│   ├── prd.md                        # Current product requirements
│   ├── system-design.md             # Current system design
│   ├── adr/                          # The project's decision log (starts empty)
│   │   └── README.md                # ADR format and index stub
│   ├── ubiquitous-language.md       # Canonical domain vocabulary
│   ├── testing-principles.md        # The project's testing policy brief
│   ├── architecture-principles.md   # The project's tactical pattern brief
│   └── security-principles.md       # The project's trust boundaries and security defaults
│
└── src/                               # Application source code
```

**Legend:** `[CC]` = Claude Code, `[CP]` = GitHub Copilot CLI, `[OC]` = OpenCode, `[JU]` = Junie CLI, `[ALL]` = tool-agnostic

**What to gitignore:** `.scratch/` is ephemeral pipeline state. Gitignore it. Agent definitions and skills are configuration — commit them.

---

## 6. Reference Implementations

The pipeline is three file types: a **rules file** (`CLAUDE.md`), portable **skills** (`.claude/skills/`), and per-tool **agent definitions**. The live, authoritative copies live in the Go and Java samples; the current handoff contract is defined in §1 (Handoff Signals). This section shows the one pattern worth seeing up close: the same agent ported across four tools, where the prompt **body is identical** and only the **frontmatter** differs.

### Skills and routing

Skills are tool-agnostic — all four tools read `.claude/skills/`. The `pipeline-handoff` skill carries the routing table, handoff conditions, and state-file inventory; its current form is defined in §1 and lives in each sample. No per-tool variant exists.

### Agents: one body, four frontmatters

Every agent is a shared markdown body plus tool-specific frontmatter. Canonical example — the `pipeline-coordinator` body and its Claude Code frontmatter:

```yaml
---
name: pipeline-coordinator
description: >
  Coordinates the specialist agent pipeline. Routes requests to the right
  specialist based on type. Reads .scratch/ state. Never implements.
tools: Read, Glob, Grep, Write, Bash
disallowedTools: Edit
model: sonnet
effort: low
---
```

```markdown
You are the pipeline coordinator. Your only job is routing work through the
specialist agent pipeline. Load the pipeline-handoff skill for the routing
table, handoff conditions, and state-file inventory. Read .scratch/handoff.jsonl
to determine current state, route to the correct specialist, and never write
code or edit source. Write is allowed only for .scratch/ state files.
```

The body is byte-identical across tools. Only the frontmatter changes:

| Field | Claude Code | OpenCode | GitHub Copilot | Junie |
|---|---|---|---|---|
| File path | `.claude/agents/<name>.md` | `.opencode/agents/<name>.md` | `.github/agents/<name>.agent.md` | `.junie/agents/<name>.md` |
| Role marker | (none) | `mode: primary` / `subagent` | (none) | (none) |
| Tool grants | `tools:` + `disallowedTools:` | `permissions: {edit, bash, mcp}` | `tools:` list | `tools:` + `disallowedTools:` |
| Sonnet pin | `claude-sonnet-4-6` | `openrouter/anthropic/claude-sonnet-4.6` | `Claude Sonnet 4.6 (copilot)` | `sonnet` |
| Opus pin | `claude-opus-4-8` | `openrouter/anthropic/claude-opus-4.8` | `Claude Opus 4.7 (copilot)` | `opus` |
| Effort | `effort: low` / `high` | `temperature` | (model-managed) | `reasoningLevel: low` / `high` |
| Turn cap | `maxTurns` | `max_steps` | (none) | global `time-limit` |
| Skills | `skills:` list | `permission.skill` | (derived from body) | `skills:` list |

The Opus tier is asymmetric by design: Claude Code and OpenCode pin 4.8, Copilot's catalog tops out at 4.7, and Junie uses the alias form. The `audit-agents` skill in each sample owns the parity rules and flags any deviation.

### Per-tool invocation differences
- **Claude Code:** invoke skills with `/<skill>`; delegate with the Agent tool.
- **OpenCode:** reference skills at `.claude/skills/<skill>/SKILL.md`; delegate with `@mention`.
- **Copilot CLI:** reference skills at `.claude/skills/`; use `/fleet` for parallel review.
- **Junie CLI:** reference skills via `skill-locations` in `.junie/config.json`; delegate by description match.

---

## 7. Pipeline Maintenance Patterns

Two patterns keep the pipeline healthy between features: doc-sync (align docs with code) and the change-grader (grade how much human attention a passing change deserves). Both are optional skills that complement the core pipeline.

### Documentation Synchronization (`doc-sync`)

After features merge, long-term memory (`docs/prd.md`, `docs/system-design.md`, `docs/ubiquitous-language.md`) drifts from the codebase. The `doc-sync` skill defines a structured process to detect and fix this drift.

**Process:**

1. **Explore current codebase.** Read all source files — note every type, interface, function, field. Read configuration files and tests.
2. **Diff against documentation.** Compare the codebase snapshot against `docs/prd.md`, `docs/system-design.md`, and `docs/ubiquitous-language.md`. Identify:
   - In PRD: features implemented but not documented, stale requirements, configuration drift, behavioral changes
   - In system design: type name changes, struct field drift, package structure changes, pipeline ordering drift, missing or stale definitions
3. **Update documents.** Apply all fixes. Respect document boundaries: PRD describes *what* (no code, no language-specific constructs); system-design.md describes *how* (no verbatim source). Keep existing requirement IDs stable. Add new IDs at the end of their section. Never renumber existing IDs.
4. **Validate.** Invoke the `doc-reviewer` agent. The reviewer checks structural correctness, cross-document coherence, and writing standards against the `document-writing` skill's checklist.
5. **Fix review issues.** Apply fixes for any `[AUTOFIX]` or `[BLOCKED]` findings. Re-run the reviewer if fixes touched more than one section. Stop when the reviewer returns APPROVED.

**When to run:** After implementing features or refactoring code. Before starting a new feature cycle. Periodically to prevent documentation drift.

### Terminal Advisory Change-Grade (`change-grader`)

After every reviewer in the roster approves a feature, a terminal `change-grader` reads the diff and grades how much human attention the passing change deserves before a human merges. The grade is **advisory only** — it never routes, and it is not a merge or correctness gate (the roster's approval already established correctness). It creates an audit trail and surfaces patterns: a change graded `concern` points the human's limited attention at the diff that warrants it; a stream of `concern` grades signals the upstream stages are letting risk through. The five facets it grades and the worst-facet aggregation rule are defined in [`agentic-harness.md`](agentic-harness.md#change-grading-in-depth); this section covers only how it fits the maintenance loop and what it reads.

**Inputs** (all derived from the latest record per `(req_id, type)` in `.scratch/handoff.jsonl`, plus the diff):

| Input | How to Determine |
|---|---|
| Tests pass | Latest `build-pass` record exists for `req_id` (no later `build-failure`) |
| Security approved | Latest `review-feedback` record with `author: "security-reviewer"` has `verdict: "approved"` |
| Code quality approved | Latest `review-feedback` record with `author: "code-quality-reviewer"` has `verdict: "approved"` |
| Test coverage approved | Latest `review-feedback` record with `author: "test-reviewer"` has `verdict: "approved"` |
| Doc review approved | Latest `review-feedback` record with `author: "doc-reviewer"` has `verdict: "approved"` |
| Build retry cycles | Count of `build-failure` records for `req_id` since the latest `design-block` (or feature start) |
| Design revisions | Count of `design-block` records for `req_id` that carry `supersedes_record_at` (re-triage after build-failure escalations) |

**Output:** two records appended to `.scratch/handoff.jsonl` — a `grader-features` record (the deterministic structural row extracted from the diff) and a `grader-verdict` record carrying the `clear`-versus-`concern` advisory verdict and its rationale. The grader renders the change-grade report from the verdict record and returns it in the dispatch reply; a human reads the report and merges.

**Rule:** The change-grade runs only after the latest `build-pass` record exists AND every roster reviewer's latest `review-feedback` record carries `verdict: "approved"` — the four-reviewer floor plus any declared `extra_reviewers`. The grade advises attention; it does not pass or fail the change.

---

## 8. Tool Comparison: Decision Framework

### When to Use Claude Code

**Use it when:**
- Your primary workflow is terminal-based coding
- You need parallel subagent execution for review fan-out
- Your team standardizes on Anthropic models
- You need the deepest skill and agent ecosystem

**Where it's strongest:**
- Subagent architecture ships four built-in agents — Explore, Plan, General-purpose, Bash — that handle 80% of delegation needs out of the box
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
- You need multi-provider flexibility (75+ providers)
- You want to use Gemini for exploration and Claude for implementation
- You're cost-optimizing by routing cheap tasks to cheaper models
- Your team has mixed model subscriptions
- You want full control over system prompts

**Where it's strongest:**
- Provider-agnostic — any model, any provider, per-agent model selection; powered by Models.dev provider list
- Fully open-source and customizable — everything is a markdown file
- Mature TUI with Vim-like keybindings; Tauri desktop app on all platforms
- Agent definitions are more granular — `permissions`, `temperature`, `max_steps`, `top_p`, `hidden`, `task` permissions for controlling which subagents an agent can invoke, `color` for UI customization
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
- You need native GitHub integration (issues → PRs → reviews) from the terminal
- You want Copilot coding agent for async cloud-based work
- You need `/fleet` parallel subagent execution with multi-model support
- Your organization has a Copilot Enterprise subscription
- You want multi-model choice (Claude Opus 4.7, GPT-5.3-Codex, Gemini 3 Pro) within a single tool

**Where it's strongest:**
- Reads `CLAUDE.md` natively — no redirect file needed, shares rules with Claude Code and OpenCode
- Full terminal-native coding agent (GA Feb 2026) with autopilot mode, `/fleet` for parallel subagent execution, built-in specialized agents (Explore, Task, Code Review, Plan), and cloud delegation with `&` prefix
- Multi-model support with model fallback chains in agent profiles: `model: ['Claude Opus 4.7', 'GPT-5.2']`
- Path-specific `.instructions.md` files with `applyTo` for granular rules per file type
- Copilot coding agent runs asynchronously in the cloud — `&` prefix delegates, `/resume` pulls results back
- Organization-level custom agents via `.github-private` repos
- Native MCP server integration in agent profiles (GitHub MCP and Playwright MCP enabled by default)
- Plugin system with marketplaces
- Plan mode → autopilot + `/fleet` workflow for large tasks

**Where it falls short:**
- CLI and coding agent are different surfaces — agent profiles aren't fully interchangeable (`argument-hint` ignored by coding agent on GitHub.com)
- Custom agents are a newer feature, less battle-tested than Claude Code's subagents
- Context window is mediated through Copilot's Agent Control Plane — not raw model context like Claude Code's 200K window
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

## 9. Migration Playbook

### Phase 1: Claude Code Only (Week 1–2)

**Do first:**
1. Create `CLAUDE.md` in project root with build commands, conventions, and forbidden patterns
2. Create `.claude/skills/pipeline-handoff/SKILL.md` with the routing table
3. Define two agents: `pipeline-coordinator` and one specialist (start with `feature-implementer`)
4. Create `schemas/scratch/` and commit the five record schemas (`prd-entry`, `design-block`, `build-failure`, `build-pass`, `review-feedback`) — the coordinator validates inbound records against these
5. Create `.scratch/` directory (containing the empty `handoff.jsonl`) and add `.scratch/` to `.gitignore`
6. Run the pipeline manually — without the coordinator — for two weeks to validate the pattern

**Do not:**
- Create all nine agents at once — start with two, add as needed
- Skip the manual phase — you need to see routing decisions before automating them
- Skip schema validation — without the gate, malformed records reach the next agent unchecked (see §1 *Why JSONL over per-stage markdown*)
- Over-engineer record schemas — start with the five canonical types, add fields when you need them

### Phase 2: Add Remaining Specialists (Week 3–4)

**Do next:**
1. Add `product-requirements-expert` and `system-design-expert` agents
2. Add the four reviewer agents
3. Add the coordinator for automated routing (stage 4) via the `pipeline-handoff` skill
4. Test the full pipeline end-to-end on a real feature
5. Once confident, run the reviewer roster in parallel (stage 5) — same tokens, less wall-clock

**Checkpoint:** Before moving on, verify that:
- The coordinator correctly classifies requests 90%+ of the time
- Handoff files contain enough context for the next agent
- Reviews are independent (no cross-reviewer dependencies)

### Phase 3: Add OpenCode (Week 5–6)

**Do next:**
1. Install OpenCode, verify it reads `CLAUDE.md` (do NOT create `AGENTS.md`)
2. Verify it discovers skills in `.claude/skills/`
3. Create OpenCode agent definitions in `.opencode/agents/` — same personas, adjusted frontmatter
4. Configure per-agent model selection in `opencode.json` — use cheaper models for exploration
5. Use OpenCode for cost-sensitive tasks: codebase exploration, quick reviews, architecture questions

**The key win:** Route Explore-type tasks to Gemini Flash or Haiku via OpenCode while keeping implementation on Claude Opus/Sonnet via Claude Code.

### Phase 4: Add GitHub Copilot CLI (Week 7–8)

**Do next:**
1. Install Copilot CLI (`npm install -g @github/copilot`) and authenticate
2. Verify Copilot CLI reads your `CLAUDE.md` — it does this natively. No extra files needed.
3. Create Copilot CLI agent profiles in `.github/agents/` — same personas, `.agent.md` format
4. Test `/fleet` for parallel review execution against Claude Code's subagent-based review
5. Use `&` prefix for cloud-delegated background tasks (long refactors, test suite fixes)
6. Set up organization-level agents in `.github-private` if on Enterprise
7. Add path-specific `.instructions.md` files in `.github/instructions/` if you need file-type-specific rules

**The key win:** Copilot CLI's `/fleet` gives you a second parallel execution engine alongside Claude Code subagents. Cloud delegation with `&` lets you offload tasks that exceed interactive session limits while keeping your terminal free. Multi-model support means you can run the same pipeline with different models to compare quality.

### What to Avoid at Every Phase

- **Don't create extra rules files.** No `AGENTS.md`, no `copilot-instructions.md`. `CLAUDE.md` is the single source of truth (see Section 2).
- **Don't duplicate skills across paths.** `.claude/skills/` is the portable location. Period.
- **Don't put workflow logic in agent definitions.** Skills are portable; agents are not. Keep agents thin.
- **Don't skip the manual phase.** You need to see the pipeline run before you automate it.
- **Don't over-invest in frontier capabilities today.** The tooling is moving fast. Build for coordinated routing with parallel review (stages 4–5) and design for upward evolution.

---

## 10. Sources

### Claude Code
- [Agent Teams documentation](https://code.claude.com/docs/en/agent-teams) — multi-session orchestration, team creation, teammate communication
- [Custom subagents](https://code.claude.com/docs/en/sub-agents) — agent format, built-in subagents, YAML frontmatter reference
- [Skills documentation](https://code.claude.com/docs/en/skills) — SKILL.md format, frontmatter fields, progressive disclosure, auto-invocation
- [Agent Skills open standard](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf) — portable skill format specification

### OpenCode
- [Rules documentation](https://opencode.ai/docs/rules/) — AGENTS.md format, CLAUDE.md fallback behavior, precedence rules
- [Agents documentation](https://opencode.ai/docs/agents/) — agent types, markdown/JSON formats, permissions, mode configuration
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

