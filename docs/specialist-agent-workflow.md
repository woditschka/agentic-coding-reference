# Specialist Agent Workflow: Architecture & Migration

The architecture behind the agent team, and the staged path to adopting it. The filesystem is the coordination layer: every handoff is a file write, auditable and tool-agnostic, so the pipeline survives sessions, crashes, and tool switches. Adoption is staged: a team stops at the capability level its workload needs. The sections: design principles (§ 1), capability progression (§ 2), canonical layout (§ 3), the per-tool agent pattern (§ 4), maintenance (§ 5), the migration playbook (§ 6).

**Status:** Validated core — architecture, principles, document architecture, cross-tool portability. Reference machinery (specialist pipeline, JSONL handoff contract, reviewer-roster fan-out) is operational. Cost-effectiveness is measured two ways: Harness Stats (root README § Harness Stats) instruments the live session; the eval bench (`evals/README.md`) tracks cost per pass across versions.

> **Scope note:** The version-stamped tool comparison — rules-file, skill, and agent matrices, model pins, IDE paths, tool choice, sources — lives in [`cross-tool-strategy.md`](cross-tool-strategy.md), refreshed by `update-research`. The same skill refreshes the stamped surfaces kept here: the § 1 Agent Teams status and cost claims, and the § 6 install steps.

---

## 1. Architecture Overview

### Design Principles

This architecture treats the filesystem as the coordination layer. Not memory. Not message passing. Not shared context windows. Files on disk are auditable, interruptible, tool-agnostic, and survive session crashes. Every handoff between agents is a file write. Every blocking condition is a status string in a known location.

The pipeline enforces separation of concerns: agents that think about *what* to build never touch code. Agents that write code never decide *what* to build. The coordinator never implements anything. Once that boundary breaks, context pollution makes every agent worse.

The pipeline runs as four concentric, nested loops. The loop model, the handoff contract, the blocking signals, and the recovery paths are methodology and live in [`agentic-harness.md`](agentic-harness.md). Each sample carries a trimmed agent-facing copy at `.claude/skills/handoff-routing/agentic-harness.md` (divergence pinned in `harness/handbook-delta.expected`). Document ownership lives in [`harness-project-api.md`](harness-project-api.md#file-roster) and the [`document-writing` skill](../harness/core/.claude/skills/document-writing/documentation-standards.md). This section keeps only what those homes do not carry.

**The what/how boundary, by example.** The PRD describes behavior in language-agnostic terms. The `prd-authoring` skill enforces the litmus test: if it would change when switching languages, it belongs in `system-design.md`. Three contrasts show the line:

| PRD (What) | System Design (How) |
|---|---|
| "The system retries failed connections up to 3 times" | "RetryPolicy struct with exponential backoff; see `internal/client/retry.go`" |
| "Constraint: buffer holds 10,000 points" | "Constants: `MaxBufferSize = 10_000` in `internal/config/defaults.go`" |
| Acceptance criteria in Given/When/Then | Package structure, interface contracts, state machine tables |

**Shortcuts** — illustrative; the routing contract is the `handoff-routing` skill's (the coordinator decides, and not every request runs the full pipeline):

```text
Bug fix         → feature-implementer → reviewer roster (parallel)
Arch question   → system-design-expert (standalone)
Review only     → any single reviewer (standalone)
```

**Why JSONL over per-stage markdown.** A single append-only log with typed records makes schema validation uniform: one gate at every transition, not a different check per stage. Append-only records also give a replayable audit trail, where mutable per-stage markdown lost history on overwrite. Full rationale: [the JSONL-handoffs ADR](adr/2026-05-08-append-only-jsonl-handoffs.md).

### Why File-Based Coordination

Agent Teams (Claude Code's experimental multi-session feature) uses direct messaging between teammates and a shared task list. It works. It also requires enabling an experimental capability, burns 3–7x the tokens of a single session, and has known limitations around session resumption and shutdown. The file-based state machine works with any model, any tool, any provider. It costs nothing extra. It is inspectable with `cat`. It survives session crashes. It is version-controllable with git.

The samples do enable the experimental agent-teams capability, but for one narrow purpose, not for coordination. A `PreToolUse` hook (`.claude/hooks/sendmessage-continue-only.py`) constrains the teammate-messaging channel to the literal string `continue`, used only to resume a truncated dispatch in place. The hook denies every other message and fails closed, so no new instructions can ride the channel. All new work still enters as a schema-validated record on `.scratch/handoff.jsonl`; file-based coordination remains the architecture.

Real-time cross-referencing between reviewers (a security finding reshaping the code-quality review) is out of scope here. The `.scratch/` state machine does the job.

### How Specs Flow Through the Pipeline

Two tiers of memory carry a feature from intent to code: durable specs the agents own, and a short-lived handoff log they append to per feature. The figure traces one feature through both.

<p align="center">
  <img src="images/spec-flow.drawio.png" width="660" alt="Spec flow with a durable long-term memory band on top (docs/prd.md, ubiquitous-language.md, docs/system-design.md) feeding a nested per-feature pipeline: the product-requirements-expert and system-design-expert read and write those specs, then append a record (prd-entry, design-block) to the short-term .scratch/handoff.jsonl band inside the pipeline; the feature-implementer reads both records and the full specs, and routes a requirement or design gap back to the owning agent as a consultation-request — it never edits long-term memory directly.">
</p>

*The product-requirements-expert also writes `docs/ubiquitous-language.md`, appending the terms the intake discussion resolved, recorded as quoted decisions in the `intake-decision` record. The diagram shows the prd flow as the canonical example.*

The implementer reads the handoff records and the full specs, but never modifies `docs/prd.md`, `docs/system-design.md`, or `docs/ubiquitous-language.md` directly. When it discovers a requirement gap or design conflict during TDD, the `tdd-workflow` skill's design-check decision tree routes a `consultation-request` to the owning agent. One tier member matters to cross-tool use specifically. `schemas/scratch/*.json` is committed long-term memory: the JSON Schema for each handoff record type, read identically by every tool.

---

## 2. Capability Progression

The harness grew from a single prompt by adding one capability at a time, each closing a specific failure of the stage before it. This section traces that path from unaided prompt to coordinated specialist pipeline, so the cost of every layer is legible. A team can stop where its workload is met. Higher is not better. The current operating point is stage 5: coordinated routing with the reviewer roster run in parallel. The `review-plan` names the floor reviewers each pass dispatches; they run concurrently after every `build-pass`. The far end is this project's demonstration, not a universal target. The tables below also mark where the current harness ends and the frontier begins. The project stops short of capabilities it judges unproven, by choice, not oversight.

### The path

Each stage keeps everything below it. Stages 0–4 each add a capability; stage 5 changes only how that roster runs: the same reviewers, dispatched in parallel.

| Stage | Capability | Problem it closes | Memory or feedback it adds |
|:-:|---|---|---|
| 0 | Single generalist prompt | — | Nothing persists; output drifts within one session |
| 1 | Rules file (`CLAUDE.md`) | Re-explaining conventions every session | First long-term memory |
| 2 | Skills | Pasting the same procedure into prompts | Reusable procedural memory |
| 3 | Specialist subagents | One context juggling PRD, design, code, and review | Separation of concerns; isolated contexts |
| 4 | Coordinated routing — coordinator + handoff log + per-record schemas | A human hand-routing every handoff | Auditable working memory |
| **5** | **Roster run in parallel** — the planned reviewers dispatch concurrently | Sequential roster review is the latency bottleneck | Same reviewers, same tokens — feedback in ~1 reviewer's wall-clock, not N |

**Current operating point: stage 5.** A script (`handoff.py route`) automates table-decided routing; a coordinator resolves escalations. The reviewer roster ([glossary](glossary.md)), the four-reviewer floor narrowed per pass by the `review-plan`, runs in parallel after every `build-pass`. The roster is the mandatory floor (`agentic-harness.md` § Specialist Agents); the table row above carries the parallelism economics. The terminal `change-grader`'s advisory grade surfaces where a layer is or is not paying off before adding the next. Beyond stage 5 the harness stops by choice; the frontier table below marks what it does not build.

### The architectural loop (running today, scoped to the reference)

Around the per-feature pipeline runs a slower review loop, the outermost of the four nested loops (see [`agentic-harness.md`](agentic-harness.md)). It catches drift on a periodic cadence and writes back to long-term memory. Today it reviews the reference itself, not application code:

| Skill | Reviews for drift in |
|---|---|
| `audit-harness` (Layer 2) | Semantic drift the `verify-harness.py` battery cannot see: agent depth, cross-tool semantics, routing, samples vs. the handbook |
| `doctor` + `audit-docs` (per sample) | The `docs/` roster against the harness-project API; brief quality |
| `audit-agents` | Agent-config consistency and cross-tool parity |
| `update-research` | Upstream tool changes vs. [`cross-tool-strategy.md`](cross-tool-strategy.md) |
| `upgrade-deps` | Pinned tool and dependency versions vs. upstream |

The loop is real and running, scoped to documentation and harness integrity.

### Beyond the current bar

The harness stops short of these by choice. None is built today.

| Frontier capability | Status | Why not here |
|---|---|---|
| Code-architecture structural review | Open extension | The same architectural loop pointed at application code: detect modules drifting from their invariants, propose refactors, feed the system-design-expert. The reference is a documentation project with minimal demo code, so structural decay has little to act on. |
| Grade-closed optimization | Not built | The `change-grader`'s advisory grades are descriptive; nothing yet feeds them back to tune the harness automatically. |
| Agent-Teams review | Experimental, not adopted | Reviewers as an Agent Team with peer-to-peer messaging — Claude Code only, one model tier, ~3–7× token cost. The file-based handoff stays the coordination backbone by choice; a team adopting it starts with the review phase (lowest risk). |
| Full team orchestration | Out of scope | The entire pipeline as one coordinated team. Blocked by the row above's experimental status, the single-model constraint, and the missing cross-tool support. |
| Long-horizon autonomous loops | Out of scope | Agents running unattended for hours or days. |
| Deterministic orchestration engine | Out of scope | Coordination runs through files, not a programmatic engine that guarantees control flow. |

Claiming the harness has reached the highest bar would contradict the project's own stance: the disciplines are the validated core; the machinery is one reference implementation, measured before trusted.

## 3. Project Structure

One layout serves all four tools. The tree is the canonical shape of an adopted project. It holds the project's rules file and briefs, the portable skills, the per-tool agent definitions, and the committed schemas and scripts the engines read. The gitignored `.scratch/` working state sits beside them. The per-tool tags mark which tool reads each surface.

```text
your-project/
├── CLAUDE.md            # [CC][CP][OC*][JU**] Project rules — the single source of truth
├── .claude/
│   ├── agents/          # [CC] The eleven pipeline agents (roster: agentic-harness.md § Specialist Agents)
│   ├── hooks/           # [CC] Hook guards — handoff append + raw-write deny, resume channel, intake stop
│   ├── skills/          # [CC][CP][OC][JU] The portable skills — every tool reads this one tree;
│   │                    #   the sample CLAUDE.md skills table is the battery-gated roster
│   └── settings.json    # [CC] Hooks, env vars, permissions
├── .github/agents/      # [CP] Same eleven agents, `.agent.md` suffix
├── .opencode/agents/    # [OC] Same eleven agents
├── .junie/              # [JU] config.json points at CLAUDE.md + .claude/skills/; agents/ holds the same eleven
├── .scratch/            # [ALL] Pipeline state, gitignored — handoff.jsonl, implementation-plan.md,
│                        #   escalations.md, tmp/
├── schemas/scratch/     # [ALL] One <type>.schema.json per handoff record — committed;
│                        #   the roster lives in the handoff-routing skill § State Files
├── scripts/             # [ALL] Deterministic engines — handoff.py, grading.py, changeset.sh,
│                        #   accounting.py, doctor.py, their packages and mirror tests, layout.toml
├── docs/                # [ALL] Project-owned briefs — the seven-file roster
│                        #   (harness-project-api.md § File Roster) plus adr/
└── src/                 # Application source code
```

**Legend:** `[CC]` = Claude Code, `[CP]` = GitHub Copilot CLI, `[OC]` = OpenCode (`*` fallback), `[JU]` = Junie CLI (`**` via `.junie/config.json`), `[ALL]` = tool-agnostic

The tree stops at two levels by design: the file-level truth is the committed samples themselves. Browsing `samples/go/` or `samples/java-spring-boot/` is reading the canonical layout, and it cannot go stale.

**What to gitignore:** `.scratch/` is ephemeral pipeline state. Gitignore it. Agent definitions and skills are configuration; commit them.

---

## 4. Reference Implementations

The pipeline is three file types: a **rules file** (`CLAUDE.md`), portable **skills** (`.claude/skills/`), and per-tool **agent definitions**. The live, authoritative copies live in the Go and Java samples; the handoff contract is the Handoff Contract section of [`agentic-harness.md`](agentic-harness.md#handoff-contract). This section shows the one pattern worth seeing up close: the same agent ported across four tools, where the prompt **body is identical** and only the **frontmatter** differs.

### Skills and routing

Skills are tool-agnostic: all four tools read `.claude/skills/`. The `handoff-routing` skill carries the routing contract and state-file inventory; the executable table lives in its `route-spec.md` companion. The skill lives in each sample. No per-tool variant exists.

### Agents: one body, four frontmatters

Every agent is a shared markdown body plus tool-specific frontmatter. Canonical example: the `pipeline-coordinator` body and its Claude Code frontmatter:

```yaml
---
name: pipeline-coordinator
description: >-
  Orchestrates the feature delivery pipeline. Use for new features
  or when unsure which agent to invoke.
tools:
  - Read
  - Grep
  - Glob
  - Bash
disallowedTools:
  - Edit
  - Write
model: claude-sonnet-5
effort: low
maxTurns: 20
toolCallBudget: 14
skills:
  - handoff-routing
---
```

```markdown
You are the judgment arm of a two-part router. `python3 scripts/handoff.py
route` executes the Handoff Conditions table deterministically; root follows
it without dispatching you. You are dispatched for what `route` cannot
decide: classifying untriaged fresh intake, and every `escalate` decision it
emits. Start by running `route` — its decision names the state you are
resolving.
```

The body is byte-identical across tools; only the frontmatter changes. The per-tool matrix is the version-stamped [`cross-tool-strategy.md` § Agents / Subagents](cross-tool-strategy.md#agents--subagents). It covers file paths, frontmatter vocabularies, tool-grant forms, model-pin syntax with the Copilot fallback chain, effort and turn-cap mappings, and invocation differences. The `audit-agents` skill in each sample owns the parity rules and flags any deviation.

---

## 5. Pipeline Maintenance Patterns

One optional pattern keeps the pipeline healthy between features: doc-sync (align docs with code). The change-grader is the terminal pipeline stage, dispatched by default after the roster approves; a project may disable the automatic run (`auto_grade` — key semantics: [`harness-project-api.md`](harness-project-api.md)). This section covers only how its grade feeds the maintenance loop.

### Documentation Synchronization (`doc-sync`)

After features merge, long-term memory (`docs/prd.md`, `docs/system-design.md`, `docs/ubiquitous-language.md`) drifts from the codebase. The `doc-sync` skill owns the detect-and-fix process and states when to run it.

### Terminal Advisory Change-Grade (`change-grader`)

The grader's role, records, and advisory-only doctrine are owned by [`agentic-harness.md` § Specialist Agents](agentic-harness.md#specialist-agents), which points to the `change-grading` skill for the protocol. This guide adds only the maintenance-loop reading: the grade's rendered report is the merge-point attention signal, and a stream of `concern` grades is the cue to inspect the upstream stages.

---

## 6. Migration Playbook

Three phases move a project from a single rules file to the full pipeline: Claude Code only, then the remaining specialists, then further tools one at a time. Each phase is a valid stopping point. Adopt the next phase when the current one's failure mode appears: § 2's rule for adding a capability, applied to phases.

### Phase 1: Claude Code Only (Week 1–2)

**Do first:**
1. Create `CLAUDE.md` in project root with build commands, conventions, and forbidden patterns
2. Create `.claude/skills/handoff-routing/` with SKILL.md (routing contract) and route-spec.md (the executable table)
3. Define two agents: `pipeline-coordinator` and one specialist (start with `feature-implementer`)
4. Create `schemas/scratch/` and commit the five record schemas (`prd-entry`, `design-block`, `build-failure`, `build-pass`, `review-feedback`) — the routing gate validates inbound records against these
5. Create `.scratch/` directory (containing the empty `handoff.jsonl`) and add `.scratch/` to `.gitignore`
6. Run the pipeline manually, without the coordinator, for two weeks to validate the pattern

**Do not:**
- Create all eleven agents at once — start with two, add as needed
- Skip the manual phase — routing decisions must be observed before they are automated
- Skip schema validation — without the gate, malformed records reach the next agent unchecked (see §1 *Why JSONL over per-stage markdown*)
- Over-engineer record schemas — start with the five canonical types, add fields when needed

### Phase 2: Add Remaining Specialists (Week 3–4)

**Do next:**
1. Add `product-requirements-expert` and `system-design-expert` agents
2. Add the four reviewer agents
3. Add the coordinator for automated routing (stage 4) via the `handoff-routing` skill
4. Test the full pipeline end-to-end on a real feature
5. Run the reviewer roster in parallel (stage 5) to reach the current operating point — same tokens, less wall-clock

**Checkpoint:** Before moving on, verify that:
- The coordinator correctly classifies requests 90%+ of the time
- Handoff files contain enough context for the next agent
- Reviews are independent (no cross-reviewer dependencies)

### Phase 3: Add Further Tools (Week 5–8, one tool at a time)

The steps are the same for every additional tool: install and authenticate, verify it reads `CLAUDE.md`, verify it discovers skills in `.claude/skills/`, and create its agent definitions. The definitions keep the same personas under tool-specific frontmatter. Each tool's distinct win and the choice framework live in [`cross-tool-strategy.md` § Tool Choice](cross-tool-strategy.md).

| Tool | Agent definitions | Tool-specific setup |
|---|---|---|
| OpenCode | `.opencode/agents/` | Per-agent model selection in `opencode.json` |
| Copilot CLI | `.github/agents/` (`.agent.md`) | Optional: org-level agents in `.github-private` (Enterprise); path-specific `.instructions.md` under `.github/instructions/` |
| Junie CLI | `.junie/agents/` | `.junie/config.json` pointing at `CLAUDE.md` and `.claude/skills/` (see [`cross-tool-strategy.md`](cross-tool-strategy.md)) |

### What to Avoid at Every Phase

- **Do not create extra rules files.** No `AGENTS.md`, no `copilot-instructions.md`. `CLAUDE.md` is the single source of truth (see [`cross-tool-strategy.md` §1](cross-tool-strategy.md#1-cross-tool-compatibility)).
- **Do not duplicate skills across paths.** `.claude/skills/` is the portable location. Period.
- **Do not put workflow logic in agent definitions.** Skills are portable; agents are not. Keep agents thin.
- **Do not skip the manual phase.** Watch the pipeline run before automating it.
- **Do not over-invest in frontier capabilities today.** The tooling is moving fast. Build for coordinated routing with parallel review (stages 4–5) and design for upward evolution.
