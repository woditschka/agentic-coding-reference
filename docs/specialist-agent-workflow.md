# Specialist Agent Workflow: Architecture & Cross-Tool Strategy

**Version:** March 2026  
**Status:** Production-ready (Levels 1–3), Experimental (Level 4), Speculative (Level 5)  
**Primary Tool:** Claude Code · **Secondary:** OpenCode, GitHub Copilot CLI

---

## 1. Architecture Overview

### Design Principles

This architecture treats the filesystem as the coordination layer. Not memory. Not message passing. Not shared context windows. Files on disk are auditable, interruptible, tool-agnostic, and survive session crashes. Every handoff between agents is a file write. Every blocking condition is a status string in a known location.

The pipeline enforces separation of concerns: agents that think about *what* to build never touch code. Agents that write code never decide *what* to build. The coordinator never implements anything. Violate this boundary and context pollution makes every agent worse.

### Pipeline Flow

**Full pipeline** (new features, happy path):

```
coordinator → product-requirements-expert → system-design-expert → feature-implementer → 4 reviewers (parallel) → eval
                .scratch/current-feature.md    .scratch/design-notes.md    .scratch/implementation-plan.md     .scratch/reviews/*.md    .scratch/eval-*.md
```

**Failure-recovery loop** (build/test fails):

```
feature-implementer (quality gate fails)
    → .scratch/build-failure.md (Retry 1–2) → coordinator → feature-implementer (retry with error context)
    → .scratch/build-failure.md (Retry 3)   → coordinator → system-design-expert (revise or [ESCALATE])
    → .scratch/design-notes.md (Status: REVISED) → coordinator → feature-implementer (retry reset)
```

**Shortcuts** (coordinator decides):

```
Bug fix         → feature-implementer → 4 reviewers (parallel)
Arch question   → system-design-expert (standalone)
Review only     → any single reviewer (standalone)
```

Each arrow is a `.scratch/` file write. Any `NEEDS_CHANGES`, `BLOCKED`, or `[ESCALATE]` status in a handoff file stops the pipeline. `BUILD_FAILED` triggers the retry loop. The coordinator reads state, routes, and never implements.

### Handoff Signals

Every `.scratch/` handoff file uses this header format:

```markdown
---
Pipeline: feature-auth-flow
Stage: design → implementation
Author: system-design-expert
Timestamp: 2026-03-22T14:30:00Z
Status: Ready for Implementation
Recommendation: APPROVED
---
```

**Blocking statuses that halt the pipeline:**

- `NEEDS_CHANGES` — the previous agent must revise before the next stage runs
- `BLOCKED` — an external dependency or decision is required; no agent can proceed
- `[ESCALATE]` — human intervention required; the coordinator surfaces this immediately
- `BUILD_FAILED` — quality gate failed; triggers the retry loop (see Build-Failure Recovery below)

### Why File-Based Coordination

Agent Teams (Claude Code's experimental multi-session feature) uses direct messaging between teammates and a shared task list. It works. It also requires Opus 4.6, burns 3–7x the tokens of a single session, has known limitations around session resumption and shutdown, and is experimental. The file-based state machine works with any model, any tool, any provider. It costs nothing extra. It's inspectable with `cat`. It survives session crashes. It's version-controllable with git.

Use Agent Teams when your reviewers genuinely need real-time cross-referencing — for example, when a security finding changes the code-quality review. Until then, the `.scratch/` state machine does the job.

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

```
docs/prd.md (persistent)          docs/system-design.md (persistent)
    │                                        │
    ▼                                        ▼
product-requirements-expert         system-design-expert
    │                                        │
    ▼                                        ▼
.scratch/current-feature.md ──→ .scratch/design-notes.md ──→ feature-implementer
   (what to build)                 (how it fits)              (reads both, modifies neither)
```

The pipeline creates ephemeral handoff files in `.scratch/` that extract the relevant slice of the persistent specs for the current feature. The implementer reads the handoffs and the full specs, but never modifies `docs/prd.md` or `docs/system-design.md` directly. When it discovers a requirement gap or design conflict during TDD, it invokes the owning agent:

- **Requirement gap** → invoke product-requirements-expert. Log in the implementation plan's Feedback Log.
- **Design gap** → invoke system-design-expert. Wait for approval before proceeding.
- **Architecture misfit** → stop, invoke system-design-expert with `[ESCALATE]`.

This routing is defined in the `tdd-workflow` skill's design-check decision tree, which runs before each TDD cycle.

#### Persistent vs Ephemeral Docs

| Type | Location | Lifecycle | Purpose |
|---|---|---|---|
| Persistent | `docs/prd.md`, `docs/system-design.md`, `docs/adr/` | Committed to git, evolves across features | Source of truth for requirements and architecture |
| Ephemeral | `.scratch/current-feature.md`, `.scratch/design-notes.md` | Gitignored, cleared between features | Scoped handoff for the current feature cycle |

The persistent docs grow over time. The ephemeral handoffs extract the relevant slice for one feature. After a feature merges, the owning agents update the persistent docs to reflect what was built — the `doc-sync` skill coordinates this.

---

## 2. Cross-Tool Compatibility

### Rules Files

| Feature | Claude Code | OpenCode | GitHub Copilot CLI |
|---|---|---|---|
| **Primary rules file** | `CLAUDE.md` (project root) | `AGENTS.md` (project root) | `CLAUDE.md`, `AGENTS.md`, or `.github/copilot-instructions.md` |
| **Reads `CLAUDE.md`?** | Yes (native) | Yes (fallback if no `AGENTS.md`) | Yes (always-on, native) |
| **Reads `AGENTS.md`?** | No | Yes (native, takes precedence) | Yes (always-on, additive) |
| **Global rules** | `~/.claude/CLAUDE.md` | `~/.config/opencode/AGENTS.md` | `COPILOT_CUSTOM_INSTRUCTIONS_DIRS` env var |
| **Nested/directory rules** | `CLAUDE.md` in subdirs | Glob patterns in `opencode.json` | `*.instructions.md` files in `.github/instructions/` (with `applyTo` frontmatter) |

**Decision: Use `CLAUDE.md` only. Do not create `AGENTS.md` or `copilot-instructions.md`.**

All three tools read `CLAUDE.md` at the project root natively. Claude Code reads it as the primary rules file. OpenCode reads it as a fallback when no `AGENTS.md` exists. Copilot CLI reads it as always-on instructions.

Creating `AGENTS.md` breaks this: OpenCode stops reading `CLAUDE.md`, Copilot CLI merges both additively (duplication or conflict), and Claude Code never reads `AGENTS.md` at all. Creating `.github/copilot-instructions.md` has the same problem — Copilot CLI merges it with `CLAUDE.md`, and there is nothing it can hold that `CLAUDE.md` cannot. One file. Three tools. Zero duplication.

**Path-specific instructions are the exception.** If you need different rules for different file types (e.g., stricter security rules for `src/auth/**`), use `.github/instructions/*.instructions.md` files with `applyTo` YAML frontmatter. These are Copilot-only, load only when matching files are active, and supplement `CLAUDE.md` without duplicating it:

```markdown
---
applyTo: "src/auth/**"
---
All authentication code must use parameterized queries. Never concatenate user input into SQL strings.
```

### Skills

| Feature | Claude Code | OpenCode | GitHub Copilot CLI |
|---|---|---|---|
| **Skill format** | `SKILL.md` + YAML frontmatter | `SKILL.md` + YAML frontmatter | `SKILL.md` + YAML frontmatter |
| **Project path** | `.claude/skills/*/SKILL.md` | `.claude/skills/*/SKILL.md` (fallback), `.opencode/skills/*/SKILL.md`, `.agents/skills/*/SKILL.md` | `.claude/skills/*/SKILL.md`, `.github/skills/*/SKILL.md` |
| **Global path** | `~/.claude/skills/*/SKILL.md` | `~/.claude/skills/*/SKILL.md` (fallback), `~/.config/opencode/skills/*/SKILL.md` | `~/.claude/skills/*/SKILL.md`, `~/.copilot/skills/*/SKILL.md` |
| **Auto-invocation** | Yes (by description match) | Yes (by description match) | Yes (by description match) |
| **Slash command** | `/skill-name` | `/skill-name` | `/skill-name` |
| **Supporting files** | Scripts, templates, references in skill dir | Scripts, templates in skill dir | Scripts, examples in skill dir |

**Decision: Use `.claude/skills/` as the single canonical location.**

All three tools discover skills at `.claude/skills/*/SKILL.md`. OpenCode also checks `.opencode/skills/` and `.agents/skills/`, but `.claude/skills/` works everywhere. Don't duplicate. The Agent Skills open standard means the same `SKILL.md` file with the same YAML frontmatter is portable across all three tools.

### Agents / Subagents

| Feature | Claude Code | OpenCode | GitHub Copilot CLI |
|---|---|---|---|
| **Agent format** | `.md` with YAML frontmatter | `.md` with YAML frontmatter or JSON in `opencode.json` | `.agent.md` with YAML frontmatter |
| **Project path** | `.claude/agents/*.md` | `.opencode/agents/*.md` | `.github/agents/*.agent.md` |
| **Global path** | `~/.claude/agents/*.md` | `~/.config/opencode/agents/*.md` | `~/.copilot/agents/*.agent.md` |
| **Key frontmatter** | `name`, `description`, `tools`, `disallowedTools`, `model`, `effort`, `maxTurns`, `hooks`, `skills`, `isolation`, `background` | `description`, `mode`, `model`, `temperature`, `permissions`, `hidden`, `top_p`, `color`, `max_steps` | `name`, `description`, `tools`, `model` (supports fallback chains), `hooks`, `mcp-servers` |
| **Subagent spawning** | Automatic (by description) or explicit | Automatic or `@mention` | Automatic or explicit |
| **Multi-agent coord** | Agent Teams (experimental) | Not built-in | `/fleet` (parallel subagents) |
| **Background delegation** | `background` frontmatter field | Not built-in | `&` prefix delegates to cloud agent |
| **Built-in subagents** | Explore, Plan, General-purpose, Bash | Build, Plan, General, Explore | Explore, Task, Code Review, Plan |

**Decision: Agents are NOT portable. Define them per-tool.**

Agent definitions are tool-specific. The YAML frontmatter fields differ. The tool permissions differ. The model selection syntax differs. Don't try to make one file work everywhere. Instead, keep the workflow intelligence in skills (portable) and keep agent definitions thin — just persona, tool restrictions, and model choice.

### The Gotchas

1. **Multiple rules files cause additive merging in Copilot CLI and fallback loss in OpenCode.** If `AGENTS.md` exists, OpenCode stops reading `CLAUDE.md`. Copilot CLI reads all of `CLAUDE.md`, `AGENTS.md`, and `copilot-instructions.md` additively — conflicting guidance produces non-deterministic behavior. The fix: `CLAUDE.md` only.

2. **Copilot CLI skills path duality.** Copilot CLI checks both `.github/skills/` and `.claude/skills/`. Use `.claude/skills/` for cross-tool portability, but know that Copilot-specific skills (those using Copilot-only features) should go in `.github/skills/`.

3. **OpenCode `tools` vs `permissions` split.** In JSON config (`opencode.json`), use `tools` with boolean values (`write: true`). In markdown agent files, use `permissions` with `allow`/`deny`/`ask` values. The `mode` config option for switching modes is deprecated — configure modes through the `agent` option instead.

4. **Agent Teams requires explicit opt-in.** Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in your environment or `settings.json`. Without this, team-related tools don't appear.

5. **Copilot path-specific instructions are Copilot-only.** `.github/instructions/*.instructions.md` files with `applyTo` are supported by Copilot coding agent, Copilot code review, and Copilot CLI. They aren't read by Claude Code or OpenCode.

### IDE Compatibility

This architecture is filesystem-based. Nothing is terminal-specific. The same project structure works unchanged in IDE environments — IntelliJ, VS Code, Eclipse, Xcode — with the Claude and Copilot plugins.

| File/Path | Claude plugin (any IDE) | Copilot plugin (any IDE) |
|---|---|---|
| `CLAUDE.md` | Yes (native) | Yes (always-on) |
| `.claude/skills/*/SKILL.md` | Yes | Yes |
| `.claude/agents/*.md` | Yes | No |
| `.github/agents/*.agent.md` | No | Yes |
| `.scratch/*` | Yes (filesystem) | Yes (filesystem) |
| `docs/*` | Yes (filesystem) | Yes (filesystem) |

The `.scratch/` state machine is plain markdown files. Any tool that can read and write files — CLI or IDE — can participate in the pipeline without modification.

---

## 3. Maturity Progression

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

**Recommendation: Most teams should target Level 2 as their steady state.** It provides the best ratio of automation to complexity.

---

### Level 3: Parallel Reviewer Subagents

**What you get:** Four reviewers (security, code quality, test coverage, documentation) run as parallel subagents, each writing to `.scratch/reviews/`. The coordinator waits for all four to complete, then aggregates results.

**What it costs:** 4x token usage during the review phase (each reviewer has its own context window). Slight coordination complexity — you need to check that all four review files exist before proceeding.

**How it works:** The coordinator spawns four subagents simultaneously using Claude Code's parallel subagent capability. Each reviewer reads the implementation handoff and the relevant source files, writes its review to `.scratch/reviews/{reviewer-name}.md`, and exits. The coordinator polls for completion (all four files exist with a `Recommendation:` line), then aggregates.

**Alternative:** Copilot CLI's `/fleet` command can also decompose a review task into parallel subagents. If your team is GitHub-native and prefers Copilot, this is a viable alternative for the parallel review gate — though Claude Code's subagent architecture offers tighter control over tool access and model selection per reviewer.

**When to use:** Review is your bottleneck. You want sub-5-minute review cycles on medium PRs. You're comfortable with the token cost.

**When to move on:** Your reviewers are finding issues that require cross-referencing — the security reviewer's findings change the code-quality reviewer's assessment, or test coverage gaps relate to documentation gaps.

**Stay here if:** Your reviews are independent. Security doesn't need to talk to code quality. This is the case for most teams.

---

### Level 4: Agent Teams for Collaborative Review (Experimental)

**What you get:** Reviewers that communicate directly with each other. The security reviewer can message the code-quality reviewer: "I found an auth bypass in the middleware — check if the error handling path has the same issue." The test-coverage reviewer can ask the documentation reviewer: "Is the retry behavior I'm testing actually documented?"

**What it costs:** Agent Teams is experimental. It requires Claude Code v2.1.32+, Opus 4.6, and explicit opt-in via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Token usage is 3–7x a single session. Session resumption has known limitations. Shutdown behavior is imperfect.

**How it works:** The coordinator creates a team with four reviewers as teammates. Each teammate loads project context from `CLAUDE.md` and skills. They claim tasks from a shared task list, communicate via direct messages, and report results back to the lead.

**When to use:** Cross-layer changes where findings in one domain affect another. Large refactors touching auth, data, and API layers simultaneously. When you've measured that Level 3 misses cross-cutting issues.

**Don't use yet if:** Your reviews are independent. You're cost-sensitive. You need reliable session resumption. You're not on Opus 4.6.

**Honest assessment:** Agent Teams is impressive technology with real rough edges. Wait for it to exit experimental status before depending on it for production workflows.

---

### Level 5: Full Team Orchestration (Future)

**What it would look like:** The coordinator itself is an Agent Teams lead. It spawns specialist teammates for each pipeline stage, manages dependencies, handles re-routing when NEEDS_CHANGES occurs, and synthesizes final results. The human provides a feature request and reviews a completed PR.

**Current blockers:**
- Agent Teams can't reliably resume after session interruption
- No built-in dependency graph between teammates (you'd build this in the task list)
- Token costs at this scale (coordinator + 7 specialist teammates) are ~15x a single session
- No cross-tool orchestration — Agent Teams is Claude Code only

**Recommendation:** Don't build for Level 5 today. Design your Level 2–3 architecture so that it *could* evolve to Level 5 when the tooling matures. This means: keep skills portable, keep agents thin, keep state in files.

---

## 4. Project Structure

```
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
│   │   ├── feature-eval/
│   │   │   └── SKILL.md              # Feature evaluation scorecard after review gate
│   │   ├── review-checklist/
│   │   │   └── SKILL.md              # Quality gates for all reviewers
│   │   └── adr-template/
│   │       └── SKILL.md              # Architecture Decision Record format
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
│   ├── current-feature.md            # Output of product-requirements-expert
│   ├── design-notes.md               # Output of system-design-expert
│   ├── implementation-plan.md        # Output of feature-implementer
│   ├── build-failure.md              # Quality gate failure output (deleted on success)
│   ├── review-summary.md             # Consolidated reviewer feedback
│   ├── escalations.md                # Items requiring human decision
│   ├── eval-<feature-name>.md        # Feature evaluation scorecard
│   └── reviews/                      # Parallel reviewer outputs
│       ├── security.md
│       ├── code-quality.md
│       ├── test-coverage.md
│       └── doc-review.md
│
├── docs/                              # [ALL] Project knowledge — agents read on demand
│   ├── prd.md                        # Current product requirements
│   ├── system-design.md             # Current system design
│   ├── adr/                          # Architecture Decision Records
│   │   ├── 001-database-choice.md
│   │   └── 002-auth-strategy.md
│   └── DOCUMENTATION.md             # Documentation standards
│
└── src/                               # Application source code
```

**Legend:** `[CC]` = Claude Code, `[OC]` = OpenCode, `[CP]` = GitHub Copilot CLI, `[ALL]` = tool-agnostic

**What to gitignore:** `.scratch/` is ephemeral pipeline state. Gitignore it. Agent definitions and skills are configuration — commit them.

---

## 5. Reference Implementations

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

### product-requirements-expert → system-design-expert
- **Trigger:** `.scratch/current-feature.md` exists with `Status: Ready for Implementation`
- **Blocks on:** `NEEDS_CHANGES`, `BLOCKED`, `[ESCALATE]`
- **Input:** `.scratch/current-feature.md` + `docs/prd.md` (if updated)
- **Output:** `.scratch/design-notes.md`

### system-design-expert → feature-implementer
- **Trigger:** `.scratch/design-notes.md` exists with `Recommendation: APPROVED` or `Status: REVISED`
- **Blocks on:** `NEEDS_CHANGES`, `BLOCKED`, `[ESCALATE]`
- **Input:** `.scratch/design-notes.md` + `docs/system-design.md` (if updated)
- **Output:** `.scratch/implementation-plan.md`

### feature-implementer → parallel reviewers (happy path)
- **Trigger:** Quality gate passes (build, test, lint)
- **Blocks on:** `NEEDS_CHANGES`, `BLOCKED`, `[ESCALATE]`
- **Input:** `.scratch/implementation-plan.md` + changed source files
- **Output:** `.scratch/reviews/{reviewer}.md` (one per reviewer)

### feature-implementer → retry loop (failure path)
- **Trigger:** Quality gate fails — implementer writes `.scratch/build-failure.md` with `Status: BUILD_FAILED`
- **Retry < 3:** Coordinator routes back to feature-implementer with `.scratch/build-failure.md` (error output), `.scratch/design-notes.md`, and `.scratch/implementation-plan.md`
- **Retry = 3:** Coordinator escalates to system-design-expert. Design expert writes `Status: REVISED` in `.scratch/design-notes.md` or `[ESCALATE]` for human intervention. A design revision resets the retry counter to 0.
- **On success:** Implementer deletes `.scratch/build-failure.md` and proceeds to reviewers

### Review gate → evaluation → completion
- **Trigger:** All four files in `.scratch/reviews/` exist with `Recommendation:` line
- **Pass condition:** All four recommendations are `APPROVED` → coordinator writes `.scratch/eval-<feature-name>.md` using the `feature-eval` skill
- **Fail condition:** Any recommendation is `NEEDS_CHANGES` → route back to feature-implementer
- **Escalate condition:** Any recommendation is `[ESCALATE]` → halt pipeline, notify human

## State File Inventory

| File | Written By | Read By |
|---|---|---|
| `.scratch/current-feature.md` | product-requirements-expert | system-design-expert, coordinator |
| `.scratch/design-notes.md` | system-design-expert | feature-implementer, coordinator |
| `.scratch/implementation-plan.md` | feature-implementer | all reviewers, coordinator |
| `.scratch/reviews/security.md` | security-reviewer | coordinator |
| `.scratch/reviews/code-quality.md` | code-quality-reviewer | coordinator |
| `.scratch/reviews/test-coverage.md` | test-reviewer | coordinator |
| `.scratch/reviews/doc-review.md` | doc-reviewer | coordinator |
| `.scratch/review-summary.md` | feature-implementer | human (final check) |
| `.scratch/escalations.md` | feature-implementer | human |
| `.scratch/build-failure.md` | feature-implementer | coordinator, feature-implementer (retry), system-design-expert (escalation) |
| `.scratch/eval-*.md` | coordinator (via feature-eval skill) | human |

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

### The `pipeline-coordinator` Agent — Three Formats

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

**Shared system prompt body** (used in all three, after the frontmatter):

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
6. If the PRD represents a significant change, update docs/prd.md.

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

---

## 6. Tool Comparison: Decision Framework

### When to Use Claude Code

**Use it when:**
- Your primary workflow is terminal-based coding
- You need parallel subagent execution (Level 3)
- You want Agent Teams for collaborative review (Level 4)
- Your team standardizes on Anthropic models
- You need the deepest skill and agent ecosystem

**Where it's strongest:**
- Subagent architecture is the most mature — built-in Explore, Plan, General-purpose, Bash agents handle 80% of delegation needs
- Richest subagent configuration surface — `effort`, `maxTurns`, `disallowedTools`, inline `hooks`, `skills` preloading, `isolation: worktree` for conflict-free parallel work, `background` mode
- Skills system is the most fully-featured — `context: fork`, `agent:` delegation, dynamic context injection, `allowed-tools` scoping
- Agent Teams is the only production-ready multi-session orchestration for AI coding agents
- Hooks (`PreToolUse`, `PostToolUse`, `Stop`, `SubagentStop`, `SessionStart`) give fine-grained control, including agent-based hooks that spawn verification subagents
- Plugin ecosystem with marketplaces for distributing skills, agents, hooks, and MCP servers
- 4% of all GitHub commits — the largest real-world usage of any AI coding tool

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
- Community-driven, not backed by model provider — updates lag behind Claude Code features
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
- Premium request economics — subagent spawning multiplies request costs

### Cross-Tool Strategy Matrix

| Scenario | Recommended Tool | Why |
|---|---|---|
| Full pipeline execution (Levels 2–3) | Claude Code | Most mature subagent architecture, skills integration, coordinator pattern |
| Parallel review execution | Claude Code or Copilot CLI | CC subagents for tight integration; CLI `/fleet` for GitHub-native workflows |
| Cost-sensitive exploration | OpenCode | Route to Haiku/Gemini Flash for read-only tasks |
| Terminal-native autonomous work | Copilot CLI or Claude Code | CLI autopilot + `/fleet` for GitHub-integrated flow; CC for Anthropic-native flow |
| Async PR creation from issues | Copilot CLI | `&` delegates to cloud coding agent; `/resume` pulls results back |
| Cross-model quality comparison | OpenCode or Copilot CLI | Both support multi-model; OpenCode has 75+ providers, CLI has Claude/GPT/Gemini |
| Enterprise-wide standards | Copilot CLI | Organization agents via `.github-private`, instruction inheritance, policy controls |
| Experimental collaborative review | Claude Code | Agent Teams is the only option for inter-agent communication |
| Cloud-delegated background tasks | Copilot CLI | `&` prefix delegates to cloud agent, freeing terminal; `/resume` to check progress |

---

## 7. Migration Playbook

### Phase 1: Claude Code Only (Week 1–2)

**Do first:**
1. Create `CLAUDE.md` in project root with build commands, conventions, and forbidden patterns
2. Create `.claude/skills/pipeline-handoff/SKILL.md` with the routing table
3. Define two agents: `pipeline-coordinator` and one specialist (start with `feature-implementer`)
4. Create `.scratch/` directory and add it to `.gitignore`
5. Run the pipeline manually (Level 1) for two weeks to validate the pattern

**Do not:**
- Create all eight agents at once — start with two, add as needed
- Skip the manual phase — you need to see routing decisions before automating them
- Over-engineer `.scratch/` state files — start simple, add fields when you need them

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

**The key win:** Copilot CLI's `/fleet` gives you a second parallel execution engine alongside Claude Code subagents. Cloud delegation with `&` lets you offload long-running tasks while keeping your terminal free. Multi-model support means you can run the same pipeline with different models to compare quality.

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

## 8. Sources

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

