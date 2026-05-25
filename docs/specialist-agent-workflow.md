# Specialist Agent Workflow: Architecture & Cross-Tool Strategy

**Status:** Validated core (architecture, principles, document architecture, cross-tool portability) · Reference machinery (specialist pipeline, JSONL handoff contract, four-reviewer fan-out) is operational; cost-effectiveness is still being measured against internal session telemetry and will be revised as evidence accumulates.
**Primary Tool:** Claude Code · **Secondary:** OpenCode, GitHub Copilot CLI, Junie CLI

> **Scope note:** This guide describes cross-tool support for the sample projects (`go/` and `java-spring-boot/`). The root of this reference monorepo is itself maintained with Claude Code only — the multi-tool layout (`.opencode/`, `.github/agents/`, `.junie/`) lives inside each sample, not at the root.

---

## 1. Architecture Overview

### Design Principles

This architecture treats the filesystem as the coordination layer. Not memory. Not message passing. Not shared context windows. Files on disk are auditable, interruptible, tool-agnostic, and survive session crashes. Every handoff between agents is a file write. Every blocking condition is a status string in a known location.

The pipeline enforces separation of concerns: agents that think about *what* to build never touch code. Agents that write code never decide *what* to build. The coordinator never implements anything. Violate this boundary and context pollution makes every agent worse.

### The Four Nested Loops

The pipeline does not run as a linear handoff. It runs as four concentric loops — inner (TDD cycle), middle (PRD + design triage for the slice), outer (slice selection), architectural (planned, months-cadence structural review). The inner loop's design-check step routes to the middle loop via consultation, so the loop nesting is a feature of the design discovery, not rework.

The four-loop structure is an agentic descendant of XP's nested feedback loops (Beck); each loop runs at a different timescale and surfaces a different layer of design question. The loop model is methodology and lives in [`agentic-harness.md`](agentic-harness.md). Each sample project carries a byte-equivalent copy.

### Pipeline Flow

**Full pipeline** (new features, happy path):

```text
coordinator → product-requirements-expert → system-design-expert → feature-implementer → 4 reviewers (parallel) → eval
                .scratch/handoff.jsonl       .scratch/handoff.jsonl    .scratch/handoff.jsonl    .scratch/handoff.jsonl    .scratch/eval-*.md
                (prd-entry)                  (design-block)            (build-pass)              (review-feedback ×4)
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
Bug fix         → feature-implementer → 4 reviewers (parallel)
Arch question   → system-design-expert (standalone)
Review only     → any single reviewer (standalone)
```

Each arrow is an append to `.scratch/handoff.jsonl`. The coordinator validates each new record against its JSON Schema (`schemas/scratch/<type>.schema.json`) at every transition; malformed or missing records bounce back to the upstream agent without consuming the next dispatch. A `design-block` with `verdict: "conflicting"` or a `review-feedback` finding tagged `escalate` halts the pipeline; a `build-failure` triggers the retry loop. The coordinator reads state, routes, and never implements.

### Handoff Signals

Handoff state lives in `.scratch/handoff.jsonl` — one JSON record per line, append-only. Each record carries a `type` discriminator that picks one of eight schemas in `schemas/scratch/`:

| `type` | Producer | Schema |
|---|---|---|
| `prd-entry` | product-requirements-expert | `prd-entry.schema.json` |
| `design-block` | system-design-expert | `design-block.schema.json` |
| `consultation-request` | feature-implementer (or any specialist mid-work) | `consultation-request.schema.json` |
| `consultation-response` | system-design-expert (or any specialist consulted) | `consultation-response.schema.json` |
| `build-failure` | feature-implementer | `build-failure.schema.json` |
| `build-pass` | feature-implementer | `build-pass.schema.json` |
| `review-feedback` | each reviewer | `review-feedback.schema.json` |
| `design-doc-autofix` | root (coordinator) | `design-doc-autofix.schema.json` |

Every record carries `type`, `req_id` (`^REQ-[A-Z]+-[0-9]{3}$`), `ts` (ISO 8601), and `author`. The active state for routing is the latest record per `(req_id, type)`. See the JSONL handoff ADR (`docs/adr/2026-05-08-append-only-jsonl-handoffs.md` in each project) for the rationale and migration record.

**Why JSONL over per-stage markdown.** A single append-only log with typed records lets the coordinator validate each record against its JSON Schema at every transition. Malformed or missing handoffs bounce back to the upstream agent before the next specialist is dispatched. Append-only records also give a replayable audit trail of pipeline state, where mutable per-stage markdown files lost history on overwrite.

**Consultation roundtrips preserve the requester's active state.** When a `consultation-request` is the latest record, the coordinator dispatches the target specialist in consultation mode; the matching `consultation-response` routes control back to the requester, not forward to the next stage. Consultations let the inner-loop discover design decisions worth crystallizing without advancing the pipeline.

**Blocking signals that halt the pipeline:**

- `verdict: "conflicting"` (on a `design-block`) — this slice contradicts current design; coordinator surfaces to the user with the contradiction
- A `build-failure` record — triggers the retry loop shown in the failure-recovery diagram above
- A finding with `tag: "escalate"` (on a `review-feedback`) — the coordinator appends to `.scratch/escalations.md`

### Why File-Based Coordination

Agent Teams (Claude Code's experimental multi-session feature) uses direct messaging between teammates and a shared task list. It works. It also requires Opus 4.6, burns 3–7x the tokens of a single session, has known limitations around session resumption and shutdown, and is experimental. The file-based state machine works with any model, any tool, any provider. It costs nothing extra. It's inspectable with `cat`. It survives session crashes. It's version-controllable with git.

Use Agent Teams when your reviewers need real-time cross-referencing — for example, when a security finding changes the code-quality review. Until then, the `.scratch/` state machine does the job.

### Spec-Driven Development

The pipeline is not just a sequence of agents — it is driven by two living specification documents that agents treat as authoritative. Without these, agents fill in blanks by guessing. With them, every implementation decision traces back to a requirement.

#### Document Authority

| Document | Level | Owner Agent | Describes |
|----------|-------|-------------|-----------|
| `docs/prd.md` | Strategic | product-requirements-expert | **What** to build — goals, non-goals, requirements with acceptance criteria |
| `docs/system-design.md` | Tactical | system-design-expert | **How** to build — architecture, patterns, types, constants, guardrails |
| `docs/adr/*.md` | Decision | system-design-expert | **Why** — trade-offs, alternatives considered, rationale |
| `CLAUDE.md` | Meta | Human | Build commands, agent workflow, commit conventions |

Each document has a single owner. Only the owner writes to it. This prevents drift: when two agents can modify the same file, conflicts are inevitable and neither version is authoritative.

#### The What/How Boundary

The PRD describes behavior in language-agnostic terms. It never contains code, class names, function signatures, or language-specific constructs. The litmus test: **if it would change when switching from Go to Rust (or Java to Kotlin), it belongs in system-design.md, not the PRD.**

| PRD (What) | System Design (How) |
|---|---|
| "The system retries failed connections up to 3 times" | "RetryPolicy struct with exponential backoff; see `internal/client/retry.go`" |
| "Constraint: buffer holds 10,000 points" | "Constants: `MaxBufferSize = 10_000` in `internal/config/defaults.go`" |
| Acceptance criteria in Given/When/Then | Package structure, interface contracts, state machine tables |

Full ownership rules and cross-reference formats are in [`documentation-standards.md`](documentation-standards.md).

#### How Specs Flow Through the Pipeline

```text
docs/prd.md (long-term memory)    docs/system-design.md (long-term memory)
    │                                        │
    ▼                                        ▼
product-requirements-expert         system-design-expert
    │                                        │
    ▼                                        ▼
.scratch/handoff.jsonl ──→ .scratch/handoff.jsonl ──→ feature-implementer
   (prd-entry record:           (design-block record:        (reads both record types,
   what to build)                how it fits)                modifies long-term memory via owning agents)
```

*The product-requirements-expert also writes `docs/ubiquitous-language.md` as terms resolve during requirements interviews — the diagram shows the prd flow as the canonical example.*

The pipeline writes to working memory in `.scratch/` that extracts the relevant slice of long-term memory for the current feature. The implementer reads the handoffs and the full specs, but never modifies `docs/prd.md`, `docs/system-design.md`, or `docs/ubiquitous-language.md` directly. When it discovers a requirement gap or design conflict during TDD, it routes through a consultation-request to the owning agent:

- **Requirement gap** → append `consultation-request` targeting product-requirements-expert. Log in the implementation plan's Feedback Log.
- **Design gap** → append `consultation-request` targeting system-design-expert. Pause; resume the inner loop when the matching consultation-response arrives.
- **Architecture misfit** → stop; append `consultation-request` flagged as architectural. The next triage will likely return `conflicting` or `foundational` if the misfit is real.

This routing is defined in the `tdd-workflow` skill's design-check decision tree, which runs before each TDD cycle.

#### Long-Term Memory vs Working Memory

| Tier | Location | Lifecycle | Purpose |
|---|---|---|---|
| Long-term memory | `docs/prd.md`, `docs/system-design.md`, `docs/adr/`, `docs/ubiquitous-language.md` | Committed to git, evolves across features | Source of truth for requirements, architecture, and shared vocabulary |
| Cross-session memory | `MEMORY.md` (optional) | Updated by tool or user | High-level summary of recent work and state to enable seamless switching between different CLI tools |
| Long-term memory | `schemas/scratch/*.json` | Committed to git, evolves with the handoff contract | JSON Schema for each record type in `handoff.jsonl` |
| Working memory | `.scratch/handoff.jsonl` (`prd-entry`, `design-block` records) | Gitignored, cleared between features | Scoped handoff for the current feature cycle |

Long-term memory grows over time. Working memory extracts the relevant slice for one feature. After a feature merges, the owning agents update long-term memory to reflect what was built — the `doc-sync` skill coordinates this.

---

## 2. Cross-Tool Compatibility

### Rules Files

| Feature | Claude Code | OpenCode | GitHub Copilot CLI | Junie CLI |
|---|---|---|---|---|
| **Primary rules file** | `CLAUDE.md` (project root) | `AGENTS.md` (project root) | `CLAUDE.md`, `AGENTS.md`, or `.github/copilot-instructions.md` | `CLAUDE.md` or `AGENTS.md` (via config) |
| **Reads `CLAUDE.md`?** | Yes (native) | Yes (fallback if no `AGENTS.md`) | Yes (always-on, native) | Yes (via `guidelines-location`) |
| **Reads `AGENTS.md`?** | No | Yes (native, takes precedence) | Yes (always-on, additive) | Yes (native default) |
| **Global rules** | `~/.claude/CLAUDE.md` | `~/.config/opencode/AGENTS.md` | `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` env var | `~/.junie/config.json` with `guidelines-location` |
| **Nested/directory rules** | `CLAUDE.md` in subdirs | Glob patterns in `opencode.json` | `*.instructions.md` files in `.github/instructions/` (with `applyTo` frontmatter) | `guidelines-location` in `.junie/config.json` (no nested glob discovery) |

**Decision: Use `CLAUDE.md` only. Do not create `AGENTS.md` or `copilot-instructions.md`.**

All four tools read `CLAUDE.md` at the project root natively or via straightforward configuration. Claude Code reads it as the primary rules file. OpenCode reads it as a fallback when no `AGENTS.md` exists. Copilot CLI reads it as always-on instructions. Junie CLI is configured to use it via `.junie/config.json`.

Creating `AGENTS.md` breaks this: OpenCode stops reading `CLAUDE.md`, Copilot CLI merges both additively (duplication or conflict), and Claude Code never reads `AGENTS.md` at all. Creating `.github/copilot-instructions.md` has the same problem — Copilot CLI merges it with `CLAUDE.md`, and there is nothing it can hold that `CLAUDE.md` cannot. One file. Four tools. Zero duplication.

**Path-specific instructions are the exception.** If you need different rules for different file types (e.g., stricter security rules for `src/auth/**`), use `.github/instructions/*.instructions.md` files with `applyTo` YAML frontmatter. These are Copilot-only, load only when matching files are active, and supplement `CLAUDE.md` without duplicating it:

```markdown
---
applyTo: "src/auth/**"
---
All authentication code must use parameterized queries. Never concatenate user input into SQL strings.
```

### Skills

| Feature | Claude Code | OpenCode | GitHub Copilot CLI | Junie CLI |
|---|---|---|---|---|
| **Skill format** | `SKILL.md` + YAML frontmatter | `SKILL.md` + YAML frontmatter | `SKILL.md` + YAML frontmatter | `SKILL.md` + YAML frontmatter |
| **Project path** | `.claude/skills/*/SKILL.md` | `.claude/skills/*/SKILL.md` (fallback), `.opencode/skills/*/SKILL.md`, `.agents/skills/*/SKILL.md` | `.claude/skills/*/SKILL.md`, `.github/skills/*/SKILL.md` | `.junie/skills/`, `.claude/skills/` (via config) |
| **Global path** | `~/.claude/skills/*/SKILL.md` | `~/.claude/skills/*/SKILL.md` (fallback), `~/.config/opencode/skills/*/SKILL.md` | `~/.claude/skills/*/SKILL.md`, `~/.copilot/skills/*/SKILL.md` | `~/.junie/skills/` |
| **Auto-invocation** | Yes (by description match) | Yes (by description match) | Yes (by description match) | Yes (by description match) |
| **Slash command** | `/skill-name` | `/skill-name` | `/skill-name` | `/skill-name` |
| **Supporting files** | Scripts, templates, references in skill dir | Scripts, templates in skill dir | Scripts, examples in skill dir | Scripts, templates, references in skill dir |

**Decision: Use `.claude/skills/` as the single canonical location.**

All four tools discover skills at `.claude/skills/*/SKILL.md`. OpenCode also checks `.opencode/skills/` and `.agents/skills/`, but `.claude/skills/` works everywhere. Don't duplicate. The Agent Skills open standard means the same `SKILL.md` file with the same YAML frontmatter is portable across all four tools.

### Agents / Subagents

| Feature | Claude Code | OpenCode | GitHub Copilot CLI | Junie CLI |
|---|---|---|---|---|
| **Agent format** | `.md` with YAML frontmatter | `.md` with YAML frontmatter or JSON in `opencode.json` | `.agent.md` with YAML frontmatter | `.md` with YAML frontmatter |
| **Project path** | `.claude/agents/*.md` | `.opencode/agents/*.md` | `.github/agents/*.agent.md` | `.junie/agents/*.md` (also reads `.agents/`) |
| **Global path** | `~/.claude/agents/*.md` | `~/.config/opencode/agents/*.md` | `~/.copilot/agents/*.agent.md` | `~/.junie/agents/*.md` |
| **Key frontmatter** | `name`, `description`, `tools`, `disallowedTools`, `model`, `effort`, `maxTurns`, `hooks`, `skills`, `isolation`, `background` | `description`, `mode`, `model`, `temperature`, `permissions`, `hidden`, `top_p`, `color`, `max_steps` | `name`, `description`, `tools`, `model` (supports fallback chains), `hooks`, `mcp-servers` | `name`, `description`, `tools`, `disallowedTools`, `model`, `reasoningLevel`, `skills`, `allowPromptArgument` |
| **Subagent spawning** | Automatic (by description) or explicit | Automatic or `@mention` | Automatic or explicit | Automatic (by description) |
| **Multi-agent coord** | Agent Teams (experimental) | Not built-in | `/fleet` (parallel subagents) | Automatic delegation |
| **Background delegation** | `background` frontmatter field | Not built-in | `&` prefix delegates to cloud agent | Non-interactive (headless) mode |
| **Built-in subagents** | Explore, Plan, General-purpose, Bash | Build, Plan, General, Explore | Explore, Task, Code Review, Plan | Default (reasoning), Plan |

**Decision: Thin agents, portable skills — define agents per-tool.**

Agent definitions are tool-specific. The YAML frontmatter fields differ. The tool permissions differ. The model selection syntax differs. Don't try to make one file work everywhere. Instead, keep the workflow intelligence in skills (portable) and keep agent definitions thin — just persona, tool restrictions, and model choice. This is the **thin agents, portable skills** principle, and it makes per-tool duplication cheap: each agent file is frontmatter plus a reference to a shared prompt body.

Junie CLI's tool-group vocabulary (`Read`, `Bash`, `Glob`, `Grep`, `Write`, `Edit`, `WebSearch`, `AskUserQuestion`) matches Claude Code's exactly, so porting a Claude agent to `.junie/agents/` is mechanical: rename `effort` to `reasoningLevel` and drop `maxTurns` (Junie has no per-agent equivalent; the global `time-limit` in `.junie/config.json` covers it).

### The Gotchas

1. **Multiple rules files cause additive merging in Copilot CLI and fallback loss in OpenCode.** If `AGENTS.md` exists, OpenCode stops reading `CLAUDE.md`. Copilot CLI reads all of `CLAUDE.md`, `AGENTS.md`, and `copilot-instructions.md` additively — conflicting guidance produces non-deterministic behavior. The fix: `CLAUDE.md` only.

2. **Copilot CLI skills path duality.** Copilot CLI checks both `.github/skills/` and `.claude/skills/`. Use `.claude/skills/` for cross-tool portability, but know that Copilot-specific skills (those using Copilot-only features) should go in `.github/skills/`.

3. **OpenCode `tools` vs `permissions` split.** In JSON config (`opencode.json`), use `tools` with boolean values (`write: true`). In markdown agent files, use `permissions` with `allow`/`deny`/`ask` values. The `mode` config option for switching modes is deprecated — configure modes through the `agent` option instead.

4. **Agent Teams requires explicit opt-in.** Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in your environment or `settings.json`. Without this, team-related tools don't appear.

5. **Copilot path-specific instructions are Copilot-only.** `.github/instructions/*.instructions.md` files with `applyTo` are supported by Copilot coding agent, Copilot code review, and Copilot CLI. They aren't read by Claude Code or OpenCode.

---

## 3. IDE Compatibility

**This project targets CLI use.** The committed agent definitions target Claude Code, OpenCode, and GitHub Copilot CLI. This section exists for users who want to extend the same filesystem-based pipeline into an IDE workflow — it is not a maintained first-class target.

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

---

## 4. Maturity Progression

The levels below describe **capability shipped**, not **value delivered**. Cost-effectiveness of moving from one level to the next depends on workload — measure with `feature-eval` scorecards before committing to a higher level. Treat each level as a reference implementation of one shape the harness can take; per-team tuning is expected.

### Level 1: Manual Pipeline with Specialist Subagents

**What you get:** Specialist agents with isolated context windows, explicit delegation, clean separation of concerns.

**What it costs:** You (the human) are the coordinator. You read each handoff file and manually invoke the next agent.

**How it works:** Define each specialist as a subagent in `.claude/agents/`. Run Claude Code, describe the task, and say "Use the product-requirements-expert agent." Read the output in `.scratch/`, then invoke the next agent manually.

**When to use:** You're a solo developer or small team learning the pattern. You want to validate that specialist agents produce better output than a single generalist session.

**When to move on:** You find yourself typing the same routing instructions repeatedly. The pipeline is predictable enough that a coordinator could automate it.

**Stay here if:** Your work is mostly ad-hoc — bug fixes, architecture questions, one-off reviews. The full pipeline rarely runs end to end.

---

### Level 2: Coordinator Agent with Automated Routing

**What you get:** A `pipeline-coordinator` agent that reads `.scratch/` state, classifies the request, and delegates to the right specialist. You describe the work once; the coordinator handles routing.

**What it costs:** One additional agent definition. One skill (`pipeline-handoff`) that encodes the routing table and handoff conditions. Debugging is slightly harder because you're watching an agent make routing decisions.

**How it works:** The coordinator loads the `pipeline-handoff` skill, reads the current state of `.scratch/`, determines the next stage, and spawns the appropriate subagent. The coordinator never writes code, never edits files (except `.scratch/` state), and never implements features.

**When to use:** Your pipeline is predictable. You run the full PRD → design → implement → review cycle at least weekly. You trust the routing logic.

**When to move on:** Reviews are your bottleneck. Running four reviewers sequentially wastes time.

**Stay here if:** Your codebase is small enough that sequential review takes under 5 minutes. The coordinator handles 90%+ of your routing correctly.

**Recommendation: Target Level 2 as the steady state.** It adds one coordinator agent to Level 1 and handles routing automatically. This avoids both the 4× token cost of Level 3's parallel reviewers and the experimental surface area of Levels 4–5.

---

### Level 3: Parallel Reviewer Subagents

**What you get:** Four reviewers (security, code quality, test coverage, documentation) run as parallel subagents, each appending a `review-feedback` record to `.scratch/handoff.jsonl`. The coordinator waits for all four to complete, then aggregates results.

**What it costs:** 4x token usage during the review phase (each reviewer has its own context window). Slight coordination complexity — you need to check that all four `review-feedback` records exist (one per `author`) for the active `req_id` before proceeding.

**How it works:** The coordinator spawns four subagents simultaneously using Claude Code's parallel subagent capability. Each reviewer reads the latest `prd-entry`, `design-block`, and `build-pass` records plus the changed source files, then appends one `review-feedback` record (with its own `author` enum value and a `verdict`) and exits. The coordinator polls for completion by reading `handoff.jsonl` and confirming the latest `review-feedback` record exists for each of the four reviewer `author` values, then aggregates.

**Alternative:** Copilot CLI's `/fleet` command can also decompose a review task into parallel subagents. If your team is GitHub-native and prefers Copilot, this is a viable alternative for the parallel review gate — though Claude Code's subagent architecture offers tighter control over tool access and model selection per reviewer.

**When to use:** Review is your bottleneck. You want sub-5-minute review cycles on medium PRs. You're comfortable with the token cost.

**When to move on:** Your reviewers are finding issues that require cross-referencing — the security reviewer's findings change the code-quality reviewer's assessment, or test coverage gaps relate to documentation gaps.

**Stay here if:** Your reviews are independent. Security doesn't need to talk to code quality.

---

### Level 4: Agent Teams for Collaborative Review (Experimental)

**What you get:** Reviewers that communicate directly with each other. The security reviewer can message the code-quality reviewer: "I found an auth bypass in the middleware — check if the error handling path has the same issue." The test-coverage reviewer can ask the documentation reviewer: "Is the retry behavior I'm testing actually documented?"

**What it costs:** Agent Teams is experimental. It requires Claude Code v2.1.32+, Opus 4.6, and explicit opt-in via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Token usage is 3–7x a single session. Session resumption has known limitations. Shutdown behavior is imperfect.

**How it works:** The coordinator creates a team with four reviewers as teammates. Each teammate loads project context from `CLAUDE.md` and skills. They claim tasks from a shared task list, communicate via direct messages, and report results back to the lead.

**When to use:** Cross-layer changes where findings in one domain affect another. Large refactors touching auth, data, and API layers simultaneously. When you've measured that Level 3 misses cross-cutting issues.

**Don't use yet if:** Your reviews are independent. You're cost-sensitive. You need reliable session resumption. You're not on Opus 4.6.

**Honest assessment:** Agent Teams enables direct inter-agent messaging and shared task lists, but ships with documented limitations around session resumption, shutdown, and 3–7× token cost versus a single session. Wait for it to exit experimental status before depending on it for production workflows.

---

### Level 5: Architectural Review Loop (Planned)

**What it would look like:** A periodic (months-cadence) skill that audits the codebase for structural decay, surfaces patterns worth crystallizing, identifies modules that have drifted from their stated invariants, and proposes refactors. The system-design-expert reads the resulting report and updates long-term memory; the architectural loop is the outermost feedback loop in the XP-style nested structure (see [`agentic-harness.md`](agentic-harness.md)).

**Current status:** Planned addition. The four-loop structure already accounts for it; the skill that drives the loop is not yet implemented. Until then, the architectural cadence runs informally — through user-initiated audits and design discussions.

**Why this replaces "Full Team Orchestration".** Under the developer + agent-team primitive (one developer drives their own agent team; humans coordinate through ordinary engineering practices), there is no "team of agents across developers" to orchestrate. The next maturity step is *longitudinal* (architecture review across months), not *organizational* (multi-developer agent coordination).

---

## 5. Project Structure

```text
your-project/
├── CLAUDE.md                          # [CC][OC*][CP] Project rules — the single source of truth
│                                      # CC=Claude Code, OC=OpenCode (* fallback), CP=Copilot CLI (always-on)
│
├── .github/
│   ├── instructions/                  # [CP] Path-specific instructions (Copilot CLI only)
│   │   └── auth.instructions.md       # applyTo: "src/auth/**" — security-specific rules
│   ├── agents/                        # [CP] Copilot CLI custom agents
│   │   ├── pipeline-coordinator.agent.md
│   │   ├── product-requirements-expert.agent.md
│   │   ├── system-design-expert.agent.md
│   │   ├── feature-implementer.agent.md
│   │   ├── security-reviewer.agent.md
│   │   ├── code-quality-reviewer.agent.md
│   │   ├── test-reviewer.agent.md
│   │   └── doc-reviewer.agent.md
│   └── skills/                        # [CP] Copilot-only skills (if any)
│
├── .claude/
│   ├── agents/                        # [CC] Claude Code subagents
│   │   ├── pipeline-coordinator.md
│   │   ├── product-requirements-expert.md
│   │   ├── system-design-expert.md
│   │   ├── feature-implementer.md
│   │   ├── security-reviewer.md
│   │   ├── code-quality-reviewer.md
│   │   ├── test-reviewer.md
│   │   └── doc-reviewer.md
│   ├── skills/                        # [CC][OC][CP] Portable skills — all tools read this
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
│   │   ├── doc-review/
│   │   │   └── SKILL.md              # Documentation review checklist, validation
│   │   ├── design-validation/
│   │   │   └── SKILL.md              # Architectural validation checklist
│   │   ├── feature-eval/
│   │   │   └── SKILL.md              # Feature evaluation scorecard after review gate
│   │   ├── new-feature/
│   │   │   └── SKILL.md              # Clear scratch directory, start fresh context
│   │   ├── adr-template/
│   │   │   └── SKILL.md              # Architecture Decision Record format
│   │   ├── audit-agents/
│   │   │   └── SKILL.md              # Agent config consistency checks
│   │   └── doc-sync/
│   │       └── SKILL.md              # Synchronize docs with codebase after implementation
│   └── settings.json                  # [CC] Claude Code hooks, env vars, permissions
│
├── .opencode/
│   └── agents/                        # [OC] OpenCode-specific agent definitions
│       ├── pipeline-coordinator.md
│       ├── product-requirements-expert.md
│       ├── system-design-expert.md
│       ├── feature-implementer.md
│       ├── security-reviewer.md
│       ├── code-quality-reviewer.md
│       ├── test-reviewer.md
│       └── doc-reviewer.md
│
├── .scratch/                          # [ALL] Pipeline state — gitignored
│   ├── handoff.jsonl                 # Append-only structured handoff log (all agents)
│   ├── implementation-plan.md        # TDD cycle plan (feature-implementer self-tracking)
│   ├── escalations.md                # Items requiring human decision
│   ├── eval-<req-id>.md              # Feature evaluation scorecard
│   └── tmp/                          # Intermediate computation files
│
├── schemas/                           # [ALL] Handoff record schemas — committed
│   └── scratch/
│       ├── prd-entry.schema.json
│       ├── design-block.schema.json
│       ├── consultation-request.schema.json
│       ├── consultation-response.schema.json
│       ├── review-feedback.schema.json
│       ├── build-failure.schema.json
│       └── build-pass.schema.json
│
├── docs/                              # [ALL] Project knowledge — agents read on demand
│   ├── prd.md                        # Current product requirements
│   ├── system-design.md             # Current system design
│   ├── adr/                          # Architecture Decision Records
│   │   ├── 2026-03-22-skill-based-agent-architecture.md
│   │   └── 2026-05-08-append-only-jsonl-handoffs.md
│   └── documentation-standards.md   # Documentation standards
│
└── src/                               # Application source code
```

**Legend:** `[CC]` = Claude Code, `[OC]` = OpenCode, `[CP]` = GitHub Copilot CLI, `[ALL]` = tool-agnostic

**What to gitignore:** `.scratch/` is ephemeral pipeline state. Gitignore it. Agent definitions and skills are configuration — commit them.

---

## 6. Reference Implementations

> **Note:** The skill, agent, and coordinator excerpts in this section are preserved as **historical snapshots**. They retain the legacy markdown-handoff format (`.scratch/current-feature.md`, `.scratch/design-notes.md`, `.scratch/reviews/*.md`, `.scratch/build-failure.md`) and the original `design-block` verdict enum (`approved` / `needs_changes` / `blocked` / `revised` / `escalated`) for historical comparison.
>
> The **current contract** is the append-only JSONL log defined in §1 (Handoff Signals) and the JSONL ADR (`docs/adr/2026-05-08-append-only-jsonl-handoffs.md` in each project). The **current verdict enum** is `covered` / `minor` / `new` / `foundational` / `conflicting` (see the `design-validation` skill in each sample). The Go and Java sample projects in this monorepo implement the current form; the legacy snippets below remain only to show the prior architecture.

### The `pipeline-handoff` Skill

`.claude/skills/pipeline-handoff/SKILL.md`:

```yaml
---
name: pipeline-handoff
description: >
  Routes work through the specialist agent pipeline. Use when coordinating
  between product requirements, system design, implementation, and review
  stages. Reads .scratch/ state files to determine the current pipeline
  stage and the next agent to invoke.
compatibility: claude-code, opencode, github-copilot
---
```

```markdown
# Pipeline Handoff Routing

## Routing Table

| Request Type | Entry Point | Bypass Allowed |
|---|---|---|
| New feature | product-requirements-expert | No |
| Bug fix | feature-implementer | Yes — skip PRD and design |
| Architecture question | system-design-expert | Yes — standalone |
| Code review only | Any single reviewer | Yes — standalone |
| Documentation update | doc-reviewer | Yes — standalone |

## Handoff Conditions

All transitions are gated by the latest record per `(req_id, type)` in `.scratch/handoff.jsonl`. The coordinator validates each new record against its JSON Schema (`schemas/scratch/<type>.schema.json`); malformed or missing records bounce back to the upstream agent.

### product-requirements-expert → system-design-expert
- **Trigger:** Latest `prd-entry` record passes schema validation (required fields present, `req_id` matches `^REQ-[A-Z]+-[0-9]{3}$`, `test_names` non-empty)
- **Blocks on:** Schema validation failure
- **Input:** `prd-entry` record + `docs/prd.md` (if updated)
- **Output:** `design-block` record appended by system-design-expert

### system-design-expert → feature-implementer
- **Trigger:** Latest `design-block` record has `verdict: "approved"` or `"revised"` and passes schema validation
- **Blocks on:** `verdict: "needs_changes"`, `"blocked"`, or `"escalated"`
- **Input:** `design-block` record + `docs/system-design.md` (if updated)
- **Output:** `build-failure` or `build-pass` record appended by implementer

### feature-implementer → parallel reviewers (happy path)
- **Trigger:** Latest `build-pass` record exists for `req_id` (no later `build-failure`)
- **Input:** `prd-entry` + `design-block` + changed source files + `.scratch/implementation-plan.md`
- **Output:** Each reviewer appends one `review-feedback` record (with their `author` value)

### feature-implementer → retry loop (failure path)
- **Trigger:** Implementer appends a `build-failure` record (`retry: 1–3`)
- **Retry < 3:** Coordinator routes back to feature-implementer with the latest `build-failure` record, the latest `design-block` record, and `.scratch/implementation-plan.md`
- **Retry = 3:** Coordinator escalates to system-design-expert. system-design-expert appends a new `design-block` with `verdict: "revised"` (and `supersedes_record_at`) or `verdict: "escalated"`. A `verdict: "revised"` record resets the retry counter — the next `build-failure` starts at `retry: 1`.
- **On success:** Implementer appends a `build-pass` record. Prior `build-failure` records remain in the file as the diagnostic retry trail (append-only).

### Review gate → evaluation → completion
- **Trigger:** Each of the four reviewers has appended a `review-feedback` record for the active `req_id` since the latest `build-pass`
- **Pass condition:** All four latest `review-feedback` records have `verdict: "approved"` → coordinator writes `.scratch/eval-<req-id>.md` using the `feature-eval` skill
- **Fail condition:** Any latest `verdict` is `"changes_requested"` or `"blocked"` with non-empty findings → route back to feature-implementer to process findings
- **Escalate condition:** Any finding has `tag: "escalate"` → coordinator appends to `.scratch/escalations.md` and halts the pipeline

## State File Inventory

| Path / Record | Written By | Read By |
|---|---|---|
| `.scratch/handoff.jsonl` (`prd-entry` records) | product-requirements-expert | system-design-expert, feature-implementer, coordinator |
| `.scratch/handoff.jsonl` (`design-block` records) | system-design-expert | feature-implementer, coordinator |
| `.scratch/handoff.jsonl` (`build-failure` / `build-pass` records) | feature-implementer | coordinator, system-design-expert (escalation) |
| `.scratch/handoff.jsonl` (`review-feedback` records, one per reviewer) | each reviewer | feature-implementer, coordinator |
| `.scratch/implementation-plan.md` | feature-implementer | feature-implementer (self-tracking), reviewers |
| `.scratch/escalations.md` | feature-implementer / coordinator | human |
| `.scratch/eval-<req-id>.md` | coordinator (via feature-eval skill) | human |
| `schemas/scratch/<type>.schema.json` | (committed; evolves with the handoff contract) | coordinator validates inbound records against these |

## Coordinator Rules

1. Read all `.scratch/` files to determine current pipeline state.
2. Classify the incoming request using the routing table.
3. If a handoff file has a blocking status, do not proceed. Report the block.
4. If `.scratch/build-failure.md` exists, apply retry logic: route to feature-implementer (Retry < 3) or system-design-expert (Retry = 3).
5. If `.scratch/design-notes.md` contains `Status: REVISED`, route to feature-implementer with retry counter reset.
6. If the pipeline is clear, delegate to the next agent with a specific prompt
   that includes the relevant handoff file path.
7. Never implement, write code, or edit source files. You are a router.
8. After review gate passes, load the `feature-eval` skill, write `.scratch/eval-<feature-name>.md`, and declare pipeline complete.
```

### The `pipeline-coordinator` Agent — Four Formats

**Claude Code** (`.claude/agents/pipeline-coordinator.md`):

```yaml
---
name: pipeline-coordinator
description: >
  Coordinates the specialist agent pipeline. Routes requests to the right
  specialist based on type (feature, bug fix, architecture question, review).
  Reads .scratch/ state to determine pipeline stage. Never implements anything.
tools: Read, Glob, Grep, Write
disallowedTools: Edit, Bash
model: sonnet
effort: low
maxTurns: 15
---
```

**OpenCode** (`.opencode/agents/pipeline-coordinator.md`):

```yaml
---
description: >
  Coordinates the specialist agent pipeline. Routes requests to the right
  specialist based on type. Reads .scratch/ state. Never implements.
mode: primary
model: anthropic/claude-sonnet-4-20250514
temperature: 0
max_steps: 15
permissions:
  edit: deny
  bash: deny
  mcp: deny
permission:
  task:
    "*": allow
---
```

**GitHub Copilot CLI** (`.github/agents/pipeline-coordinator.agent.md`):

```yaml
---
name: Pipeline Coordinator
description: >
  Coordinates the specialist agent pipeline. Routes requests to the right
  specialist based on type. Reads .scratch/ state. Never implements.
tools:
  - read
  - search
  - fetch
model:
  - Claude Sonnet 4.5 (copilot)
  - GPT-5.2 (copilot)
---
```

**Junie CLI** (`.junie/agents/pipeline-coordinator.md`):

```yaml
---
name: pipeline-coordinator
description: >
  Coordinates the specialist agent pipeline. Routes requests to the right
  specialist based on type (feature, bug fix, architecture question, review).
  Reads .scratch/ state to determine pipeline stage. Never implements anything.
tools: Read, Glob, Grep, Write
disallowedTools: Edit, Bash
model: sonnet
reasoningLevel: low
---
```

**Shared system prompt body** (used in all four, after the frontmatter):

```markdown
You are the pipeline coordinator. Your only job is routing work through
the specialist agent pipeline.

Load the pipeline-handoff skill. It contains the routing table,
handoff conditions, and state file inventory you need.

Rules:
1. Read .scratch/ to understand current pipeline state before doing anything.
2. Classify the request: new feature, bug fix, architecture question, or review.
3. Route to the correct specialist agent per the routing table.
4. Never write code. Never edit source files. Never implement features.
5. If any handoff has a blocking status (NEEDS_CHANGES, BLOCKED, [ESCALATE]),
   report it and stop. Do not route around blocks.
6. If .scratch/build-failure.md exists, apply retry logic:
   - Retry < 3: route to feature-implementer with error context
   - Retry = 3: escalate to system-design-expert
7. If .scratch/design-notes.md has Status: REVISED, route to feature-implementer
   with retry counter reset.
8. After all reviewers approve, load the feature-eval skill and write
   .scratch/eval-<feature-name>.md before declaring completion.
9. Write is allowed ONLY for .scratch/ state files.

When delegating, include in your prompt to the subagent:
- The specific .scratch/ handoff file to read
- Any relevant docs/ files
- The expected output file path
- For retries: .scratch/build-failure.md and the retry count
```

**Per-tool invocation differences:**
- **Claude Code:** Invoke the skill with `/pipeline-handoff`. Delegate with the Agent tool.
- **OpenCode:** Reference the skill at `.claude/skills/pipeline-handoff/SKILL.md`. Delegate with `@mention` (e.g., `@product-requirements-expert`).
- **Copilot CLI:** Reference the skill at `.claude/skills/pipeline-handoff/SKILL.md`. For parallel review, use `/fleet` to decompose across reviewers.
- **Junie CLI:** Reference the skill at `.claude/skills/pipeline-handoff/SKILL.md` (via `skill-locations` in `.junie/config.json`). Delegate via automatic subagent selection by description match.

### Specialist Agent Example: `product-requirements-expert`

**Claude Code** (`.claude/agents/product-requirements-expert.md`):

```yaml
---
name: product-requirements-expert
description: >
  Analyzes feature requests and produces structured product requirements.
  Use when starting a new feature that needs a PRD. Writes output to
  .scratch/current-feature.md and optionally updates docs/prd.md.
tools: Read, Write, Glob, Grep, WebSearch, WebFetch
disallowedTools: Edit, Bash
model: opus
effort: high
maxTurns: 30
skills:
  - pipeline-handoff
  - adr-template
---
```

```markdown
You are a senior product manager. Your job is to take a feature request
and produce a structured PRD that a system designer can act on.

Process:
1. Read the existing docs/prd.md for context on current product state.
2. Read any relevant docs/adr/*.md for prior architectural decisions.
3. Analyze the feature request for completeness, feasibility, and scope.
4. Ask clarifying questions if the request is ambiguous (use AskUser tool).
5. Write a structured handoff to .scratch/current-feature.md with:
   - Feature summary
   - User stories with acceptance criteria
   - Scope boundaries (what's in, what's out)
   - Dependencies and risks
   - Status: Ready for Implementation (or NEEDS_CHANGES with explanation)
6. If the feature adds or modifies requirements, non-goals, or acceptance criteria, update docs/prd.md.

Output format for .scratch/current-feature.md:
---
Pipeline: [feature-name]
Stage: intake → design
Author: product-requirements-expert
Timestamp: [ISO 8601]
Status: Ready for Implementation
Recommendation: APPROVED
---

[Structured PRD content here]
```

**OpenCode** (`.opencode/agents/product-requirements-expert.md`):

```yaml
---
description: >
  Analyzes feature requests and produces structured product requirements.
  Writes to .scratch/current-feature.md. Use for new features needing a PRD.
mode: subagent
model: anthropic/claude-opus-4-6-20260301
temperature: 0.2
permissions:
  edit: allow
  bash: deny
permission:
  skill:
    pipeline-handoff: allow
    adr-template: allow
---
```

```markdown
You are a senior product manager. [Same instructions as Claude Code version]
```

**GitHub Copilot CLI** (`.github/agents/product-requirements-expert.agent.md`):

```yaml
---
name: Product Requirements Expert
description: >
  Analyzes feature requests and produces structured product requirements.
  Writes to .scratch/current-feature.md.
tools:
  - read
  - editFiles
  - search
  - fetch
model:
  - Claude Opus 4.5 (copilot)
  - GPT-5.2 (copilot)
---
```

```markdown
You are a senior product manager. [Same instructions as Claude Code version]
```

**Junie CLI** (`.junie/agents/product-requirements-expert.md`):

```yaml
---
name: product-requirements-expert
description: >
  Analyzes feature requests and produces structured product requirements.
  Use when starting a new feature that needs a PRD. Writes output to
  .scratch/current-feature.md and optionally updates docs/prd.md.
tools: Read, Write, Glob, Grep, WebSearch, WebFetch
disallowedTools: Edit, Bash
model: opus
reasoningLevel: high
skills:
  - pipeline-handoff
  - adr-template
---
```

```markdown
You are a senior product manager. [Same instructions as Claude Code version]
```

---

## 7. Pipeline Maintenance Patterns

Two patterns keep the pipeline healthy between features: doc-sync (align docs with code) and feature-eval (measure pipeline quality). Both are optional skills that complement the core pipeline.

### Documentation Synchronization (`doc-sync`)

After features merge, long-term memory (`docs/prd.md`, `docs/system-design.md`, `docs/ubiquitous-language.md`) drifts from the codebase. The `doc-sync` skill defines a structured process to detect and fix this drift.

**Process:**

1. **Explore current codebase.** Read all source files — note every type, interface, function, field. Read configuration files and tests.
2. **Diff against documentation.** Compare the codebase snapshot against `docs/prd.md`, `docs/system-design.md`, and `docs/ubiquitous-language.md`. Identify:
   - In PRD: features implemented but not documented, stale requirements, configuration drift, behavioral changes
   - In system design: type name changes, struct field drift, package structure changes, pipeline ordering drift, missing or stale definitions
3. **Update documents.** Apply all fixes. Respect document boundaries: PRD describes *what* (no code, no language-specific constructs); system-design.md describes *how* (no verbatim source). Keep existing requirement IDs stable. Add new IDs at the end of their section. Never renumber existing IDs.
4. **Validate.** Invoke the `doc-reviewer` agent. The reviewer checks structural correctness, cross-document coherence, and writing standards against the validation checklist in [`documentation-standards.md`](documentation-standards.md).
5. **Fix review issues.** Apply fixes for any `[AUTOFIX]` or `[BLOCKED]` findings. Re-run the reviewer if fixes touched more than one section. Stop when the reviewer returns APPROVED.

**When to run:** After implementing features or refactoring code. Before starting a new feature cycle. Periodically to prevent documentation drift.

### Feature Evaluation Scorecard (`feature-eval`)

After all reviewers approve a feature, the coordinator writes a scorecard that measures pipeline quality. This creates an audit trail and surfaces patterns — repeated build failures indicate design problems; repeated review cycles indicate unclear requirements.

**Scoring criteria** (all derived from the latest record per `(req_id, type)` in `.scratch/handoff.jsonl`):

| Criterion | How to Determine |
|---|---|
| Tests pass | Latest `build-pass` record exists for `req_id` (no later `build-failure`) |
| Security approved | Latest `review-feedback` record with `author: "security-reviewer"` has `verdict: "approved"` |
| Code quality approved | Latest `review-feedback` record with `author: "code-quality-reviewer"` has `verdict: "approved"` |
| Test coverage approved | Latest `review-feedback` record with `author: "test-reviewer"` has `verdict: "approved"` |
| Doc review approved | Latest `review-feedback` record with `author: "doc-reviewer"` has `verdict: "approved"` |
| Build retry cycles | Count of `build-failure` records for `req_id` since the latest `design-block` (or feature start) |
| Design revisions | Count of `design-block` records for `req_id` that carry `supersedes_record_at` (re-triage after build-failure escalations) |

**Output:** `.scratch/eval-<req-id>.md` with a PASS/FAIL verdict and retry cost assessment (0 = clean, 1–2 = minor issues, 3 = design revision needed).

**Rule:** PASS requires the latest `build-pass` record AND all four latest `review-feedback` records with `verdict: "approved"`. A feature that required design revision is still a PASS if it ultimately succeeds, but the revision is noted.

---

## 8. Tool Comparison: Decision Framework

### When to Use Claude Code

**Use it when:**
- Your primary workflow is terminal-based coding
- You need parallel subagent execution (Level 3)
- You want Agent Teams for collaborative review (Level 4)
- Your team standardizes on Anthropic models
- You need the deepest skill and agent ecosystem

**Where it's strongest:**
- Subagent architecture ships four built-in agents — Explore, Plan, General-purpose, Bash — that handle 80% of delegation needs out of the box
- Subagent configuration surface covers `effort`, `maxTurns`, `disallowedTools`, inline `hooks`, `skills` preloading, `isolation: worktree` for conflict-free parallel work, and `background` mode
- Skills system supports `context: fork`, `agent:` delegation, dynamic context injection, and `allowed-tools` scoping
- Agent Teams is the only production-ready multi-session orchestration for AI coding agents
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
- You want multi-model choice (Claude Opus 4.6, GPT-5.3-Codex, Gemini 3 Pro) within a single tool

**Where it's strongest:**
- Reads `CLAUDE.md` natively — no redirect file needed, shares rules with Claude Code and OpenCode
- Full terminal-native coding agent (GA Feb 2026) with autopilot mode, `/fleet` for parallel subagent execution, built-in specialized agents (Explore, Task, Code Review, Plan), and cloud delegation with `&` prefix
- Multi-model support with model fallback chains in agent profiles: `model: ['Claude Opus 4.5', 'GPT-5.2']`
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
| Full pipeline execution (Levels 2–3) | Claude Code | Four built-in subagents, skills integration, coordinator pattern |
| Parallel review execution | Claude Code or Copilot CLI | CC subagents for tight integration; CLI `/fleet` for GitHub-native workflows |
| Cost-sensitive exploration | OpenCode | Route to Haiku/Gemini Flash for read-only tasks |
| Terminal-native autonomous work | Copilot CLI or Claude Code | CLI autopilot + `/fleet` for GitHub-integrated flow; CC for Anthropic-native flow |
| Async PR creation from issues | Copilot CLI | `&` delegates to cloud coding agent; `/resume` pulls results back |
| Cross-model quality comparison | OpenCode or Copilot CLI | Both support multi-model; OpenCode has 75+ providers, CLI has Claude/GPT/Gemini |
| Enterprise-wide standards | Copilot CLI | Organization agents via `.github-private`, instruction inheritance, policy controls |
| Experimental collaborative review | Claude Code | Agent Teams is the only option for inter-agent communication |
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
6. Run the pipeline manually (Level 1) for two weeks to validate the pattern

**Do not:**
- Create all eight agents at once — start with two, add as needed
- Skip the manual phase — you need to see routing decisions before automating them
- Skip schema validation — without the gate, malformed records reach the next agent unchecked (see §1 *Why JSONL over per-stage markdown*)
- Over-engineer record schemas — start with the five canonical types, add fields when you need them

### Phase 2: Add Remaining Specialists (Week 3–4)

**Do next:**
1. Add `product-requirements-expert` and `system-design-expert` agents
2. Add the four reviewer agents
3. Upgrade the coordinator to Level 2 (automated routing via `pipeline-handoff` skill)
4. Test the full pipeline end-to-end on a real feature
5. Once confident, enable parallel reviewers (Level 3)

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

### Phase 5: Evaluate Agent Teams (Month 3+)

**Prerequisites:**
1. You're on Claude Code v2.1.32+
2. You have a Max plan ($100+/month) for sufficient Opus 4.6 usage
3. You've measured that Level 3 parallel reviews miss cross-cutting issues
4. You're comfortable with experimental features

**Do next:**
1. Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`
2. Try a single collaborative review session with two reviewer teammates
3. Compare results against Level 3 parallel reviews
4. If the quality improvement justifies the 3–7x token cost, expand to four reviewers

**Do not:**
- Migrate your entire pipeline to Agent Teams — keep the file-based state machine as the backbone
- Depend on Agent Teams for production workflows until it exits experimental
- Use Agent Teams for tasks that don't require inter-agent communication

### What to Avoid at Every Phase

- **Don't create extra rules files.** No `AGENTS.md`, no `copilot-instructions.md`. `CLAUDE.md` is the single source of truth (see Section 2).
- **Don't duplicate skills across paths.** `.claude/skills/` is the portable location. Period.
- **Don't put workflow logic in agent definitions.** Skills are portable; agents are not. Keep agents thin.
- **Don't skip the manual phase.** You need to see the pipeline run before you automate it.
- **Don't over-invest in Level 4–5 today.** The tooling is moving fast. Build for Level 2–3 and design for upward evolution.

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

### Community Resources
- [awesome-copilot](https://github.com/github/awesome-copilot) — community agents, skills, instructions for Copilot
- [Antigravity Awesome Skills](https://github.com/anthropics/skills) — 1,200+ cross-compatible skills
- [everything-claude-code](https://github.com/affaan-m/everything-claude-code) — cross-harness agent optimization

