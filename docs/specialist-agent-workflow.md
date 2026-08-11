# Specialist Agent Workflow: Architecture & Migration

**Status:** Validated core — architecture, principles, document architecture, cross-tool portability. Reference machinery (specialist pipeline, JSONL handoff contract, reviewer-roster fan-out) is operational. Cost-effectiveness is measured two ways: Harness Stats (root README § Harness Stats) instruments the live session; the eval bench (`evals/README.md`) tracks cost per pass across versions.

> **Scope note:** This document carries the durable architecture: design principles, the capability progression, the canonical project layout, the per-tool agent pattern, maintenance patterns, and the migration playbook. The version-stamped tool comparison — rules-file matrices, IDE paths, tool choice, sources — lives in [`cross-tool-strategy.md`](cross-tool-strategy.md), refreshed by `update-research`. The same skill refreshes the version-stamped surfaces kept here: the § 1 Agent Teams status and cost claims, the § 4 model-pin matrix, and the § 6 install steps.

---

## 1. Architecture Overview

### Design Principles

This architecture treats the filesystem as the coordination layer. Not memory. Not message passing. Not shared context windows. Files on disk are auditable, interruptible, tool-agnostic, and survive session crashes. Every handoff between agents is a file write. Every blocking condition is a status string in a known location.

The pipeline enforces separation of concerns: agents that think about *what* to build never touch code. Agents that write code never decide *what* to build. The coordinator never implements anything. Violate this boundary and context pollution makes every agent worse.

The pipeline runs as four concentric loops — inner (TDD cycle), middle (PRD + design triage and review-until-approved), outer (slice selection), architectural (structural review). The loop model, the handoff contract, the blocking signals, and the recovery paths are methodology and live in [`agentic-harness.md`](agentic-harness.md); each sample carries a trimmed agent-facing copy at `.claude/skills/handoff-routing/agentic-harness.md` (divergence pinned in `harness/handbook-delta.expected`). Document ownership lives in [`harness-project-api.md`](harness-project-api.md#file-roster) and the [`document-writing` skill](../harness/core/.claude/skills/document-writing/documentation-standards.md). This section keeps only what those homes do not carry.

**The what/how boundary, by example.** The PRD describes behavior in language-agnostic terms; the litmus test — if it would change when switching languages, it belongs in `system-design.md` — is enforced by the `prd-authoring` skill. Three contrasts show the line:

| PRD (What) | System Design (How) |
|---|---|
| "The system retries failed connections up to 3 times" | "RetryPolicy struct with exponential backoff; see `internal/client/retry.go`" |
| "Constraint: buffer holds 10,000 points" | "Constants: `MaxBufferSize = 10_000` in `internal/config/defaults.go`" |
| Acceptance criteria in Given/When/Then | Package structure, interface contracts, state machine tables |

**Shortcuts** (coordinator decides — not every request runs the full pipeline):

```text
Bug fix         → feature-implementer → reviewer roster (parallel)
Arch question   → system-design-expert (standalone)
Review only     → any single reviewer (standalone)
```

**Why JSONL over per-stage markdown.** A single append-only log with typed records makes schema validation uniform — one gate at every transition, not a different check per stage. Append-only records also give a replayable audit trail, where mutable per-stage markdown lost history on overwrite. Full rationale: [the JSONL-handoffs ADR](adr/2026-05-08-append-only-jsonl-handoffs.md).

### Why File-Based Coordination

Agent Teams (Claude Code's experimental multi-session feature) uses direct messaging between teammates and a shared task list. It works. It also requires enabling an experimental capability, burns 3–7x the tokens of a single session, and has known limitations around session resumption and shutdown. The file-based state machine works with any model, any tool, any provider. It costs nothing extra. It's inspectable with `cat`. It survives session crashes. It's version-controllable with git.

The samples do enable the experimental agent-teams capability — but for one narrow purpose, not for coordination. A `PreToolUse` hook (`.claude/hooks/sendmessage-continue-only.py`) constrains the teammate-messaging channel to the literal string `continue`, used only to resume a truncated dispatch in place. The hook denies every other message and fails closed, so no new instructions can ride the channel. All new work still enters as a schema-validated record on `.scratch/handoff.jsonl`; file-based coordination remains the architecture.

Real-time cross-referencing between reviewers — a security finding reshaping the code-quality review — is out of scope here; the `.scratch/` state machine does the job.

### How Specs Flow Through the Pipeline

Two tiers of memory carry a feature from intent to code: durable specs the agents own, and a short-lived handoff log they append to per feature. The figure traces one feature through both.

<p align="center">
  <img src="images/spec-flow.drawio.png" width="660" alt="Spec flow with a durable long-term memory band on top (docs/prd.md, ubiquitous-language.md, docs/system-design.md) feeding a nested per-feature pipeline: the product-requirements-expert and system-design-expert read and write those specs, then append a record (prd-entry, design-block) to the short-term .scratch/handoff.jsonl band inside the pipeline; the feature-implementer reads both records and the full specs, and routes a requirement or design gap back to the owning agent as a consultation-request — it never edits long-term memory directly.">
</p>

*The product-requirements-expert also writes `docs/ubiquitous-language.md`, appending the terms the root elicitation resolved — the diagram shows the prd flow as the canonical example.*

The implementer reads the handoff records and the full specs, but never modifies `docs/prd.md`, `docs/system-design.md`, or `docs/ubiquitous-language.md` directly. When it discovers a requirement gap or design conflict during TDD, the `tdd-workflow` skill's design-check decision tree routes a `consultation-request` to the owning agent. One tier member matters to cross-tool use specifically: `schemas/scratch/*.json` is committed long-term memory — the JSON Schema for each handoff record type, read identically by every tool.

---

## 2. Capability Progression

The harness grew from a single prompt by adding one capability at a time, each closing a specific failure of the stage before it. This section traces that path — unaided prompt to coordinated specialist pipeline — so the cost of every layer is legible and a team can stop where its workload is met. Higher is not better. The current operating point is stage 5 — coordinated routing with the reviewer roster run in parallel. The `review-plan` names the floor reviewers each pass dispatches; they run concurrently after every `build-pass`. The far end is this project's demonstration, not a universal target. The tables below also mark where the current harness ends and the frontier begins — the project stops short of capabilities it judges unproven, by choice, not oversight.

### The path

Each stage keeps everything below it. Stages 0–4 each add a capability; stage 5 changes only how that roster runs — the same reviewers, dispatched in parallel. (The agent configs carry a separate execution-maturity ladder — manual to coordinated dispatch — whose level numbers track a different axis and do not map onto these stages.)

| Stage | Capability | Problem it closes | Memory or feedback it adds |
|:-:|---|---|---|
| 0 | Single generalist prompt | — | Nothing persists; output drifts within one session |
| 1 | Rules file (`CLAUDE.md`) | Re-explaining conventions every session | First long-term memory |
| 2 | Skills | Pasting the same procedure into prompts | Reusable procedural memory |
| 3 | Specialist subagents | One context juggling PRD, design, code, and review | Separation of concerns; isolated contexts |
| 4 | Coordinated routing — coordinator + handoff log + per-record schemas | A human hand-routing every handoff | Auditable working memory |
| **5** | **Roster run in parallel** — the planned reviewers dispatch concurrently | Sequential roster review is the latency bottleneck | Same reviewers, same tokens — feedback in ~1 reviewer's wall-clock, not N |

**Current operating point: stage 5.** A script (`handoff.py route`) automates table-decided routing — a coordinator resolves escalations — and the reviewer roster ([glossary](glossary.md)), the four-reviewer floor narrowed per pass by the `review-plan`, runs in parallel after every `build-pass`. The roster is the mandatory floor (`agentic-harness.md` § Specialist Agents). It costs ~4× a single reviewer's tokens; running it in parallel collapses that into ~1 reviewer's wall-clock at no extra tokens. The terminal `change-grader` — an advisory grade of how much human attention a passing change deserves — surfaces where a layer is or isn't paying off before adding the next. Beyond stage 5 the harness stops by choice; the frontier table below marks what it does not build.

### The architectural loop (running today, scoped to the reference)

Around the per-feature pipeline runs a slower review loop — the outermost of the four nested loops (see [`agentic-harness.md`](agentic-harness.md)). It catches drift on a periodic cadence and writes back to long-term memory. Today it reviews the reference itself, not application code:

| Skill | Reviews for drift in |
|---|---|
| `audit-harness` (Layer 2) | Semantic drift the `verify-harness.py` battery cannot see: agent depth, cross-tool semantics, routing, samples vs. the handbook |
| `doctor` + `audit-docs` (per sample) | The `docs/` roster against the harness-project API; brief quality |
| `audit-agents` | Agent-config consistency and cross-tool parity |
| `update-research` | Upstream tool changes vs. [`cross-tool-strategy.md`](cross-tool-strategy.md) |
| `upgrade-deps` | Pinned tool and dependency versions vs. upstream |

The loop is real and running — scoped to documentation and harness integrity.

### Beyond the current bar

The harness stops short of these by choice. None is built today.

| Frontier capability | Status | Why not here |
|---|---|---|
| Code-architecture structural review | Open extension | The same architectural loop pointed at application code: detect modules drifting from their invariants, propose refactors, feed the system-design-expert. The reference is a documentation project with minimal demo code, so structural decay has little to act on. |
| Grade-closed optimization | Not built | The `change-grader`'s advisory grades are descriptive; nothing yet feeds them back to tune the harness automatically. |
| Long-horizon autonomous loops | Out of scope | Agents running unattended for hours or days. |
| Deterministic orchestration engine | Out of scope | Coordination runs through files, not a programmatic engine that guarantees control flow. |

Claiming the harness has reached the highest bar would contradict the project's own stance: the disciplines are the validated core; the machinery is one reference implementation, measured before trusted.

## 3. Project Structure

```text
your-project/
├── CLAUDE.md                          # [CC][CP][OC*][JU**] Project rules — the single source of truth
│                                      # CC=Claude Code, CP=Copilot CLI (always-on), OC=OpenCode (* fallback), JU=Junie (** via .junie/config.json)
│
├── .claude/
│   ├── agents/                        # [CC] Claude Code subagents — the ten pipeline agents
│   │   ├── pipeline-coordinator.md
│   │   ├── product-requirements-expert.md
│   │   ├── system-design-expert.md
│   │   ├── feature-implementer.md
│   │   ├── review-planner.md
│   │   ├── security-reviewer.md
│   │   ├── code-quality-reviewer.md
│   │   ├── test-reviewer.md
│   │   ├── doc-reviewer.md
│   │   └── change-grader.md
│   ├── hooks/                         # [CC] PreToolUse guards (handoff append + raw-write deny, resume channel)
│   │   ├── handoff-allow.py
│   │   ├── handoff-log-guard.py
│   │   └── sendmessage-continue-only.py
│   ├── skills/                        # [CC][CP][OC][JU] Portable skills — all tools read this
│   │   ├── handoff-routing/
│   │   │   ├── SKILL.md              # Routing rules, gates, recovery, root-applied procedures
│   │   │   ├── route-spec.md         # The `route` engine's executable spec (companion, loaded on demand)
│   │   │   └── agentic-harness.md    # Trimmed agent-facing handbook copy
│   │   ├── handoff-append/
│   │   │   └── SKILL.md              # Writer contract: sanctioned append form, append-only discipline
│   │   ├── handoff-board/
│   │   │   └── SKILL.md              # Reader board: per-slice header, matrix, timeline
│   │   ├── tdd-workflow/
│   │   │   └── SKILL.md              # TDD cycle process, design-check decision tree
│   │   ├── prd-authoring/
│   │   │   └── SKILL.md              # PRD format, boundary rules, requirement template
│   │   ├── code-quality-gate/
│   │   │   └── SKILL.md              # Build/test/lint requirements, completion criteria
│   │   ├── review-workflow/
│   │   │   ├── SKILL.md              # Review process, feedback tags, output format
│   │   │   └── reference.md          # Detailed review procedures and templates
│   │   ├── code-quality-review/
│   │   │   └── SKILL.md              # Language-specific code quality checklist
│   │   ├── test-review/
│   │   │   └── SKILL.md              # Test quality checklist, security testing
│   │   ├── security-checks/
│   │   │   └── SKILL.md              # Security checklists, threat model, severity
│   │   ├── document-writing/
│   │   │   ├── SKILL.md              # Documentation review checklist, validation
│   │   │   ├── documentation-standards.md  # Writing standards, ownership boundaries
│   │   │   └── review-checks.md      # Prohibited patterns, review severity table
│   │   ├── design-validation/
│   │   │   └── SKILL.md              # Architectural validation checklist
│   │   ├── change-grading/
│   │   │   └── SKILL.md              # Terminal advisory change-grade after review gate
│   │   ├── new-feature/
│   │   │   └── SKILL.md              # Clear scratch directory, start fresh context
│   │   ├── next/
│   │   │   └── SKILL.md              # Reset scratch, recommend the next PRD requirement
│   │   ├── ship/
│   │   │   └── SKILL.md              # Quality gate, commit, and push in one step
│   │   ├── adr-template/
│   │   │   └── SKILL.md              # Architecture Decision Record format
│   │   ├── audit-agents/
│   │   │   └── SKILL.md              # Agent config consistency checks
│   │   ├── doctor/
│   │   │   ├── SKILL.md              # Deterministic docs/ roster validation (blocking)
│   │   │   └── templates/            # Materialization source for the seven roster files (engine lives in scripts/)
│   │   ├── derive-briefs/
│   │   │   └── SKILL.md              # Draft the briefs from an existing codebase, provenance marked
│   │   ├── audit-docs/
│   │   │   └── SKILL.md              # Advisory judgment review of the project briefs
│   │   └── doc-sync/
│   │       └── SKILL.md              # Synchronize docs with codebase after implementation
│   └── settings.json                  # [CC] Claude Code hooks, env vars, permissions
│
├── .github/
│   ├── agents/                        # [CP] Copilot CLI custom agents — same ten agents, `.agent.md` suffix
│   ├── instructions/                  # [CP] Optional: path-specific Copilot instructions (a project's own; not materialized)
│   └── skills/                        # [CP] Optional: Copilot-only skills (a project's own; not materialized)
│
├── .opencode/
│   └── agents/                        # [OC] OpenCode agent definitions — same ten agents
│
├── .junie/
│   ├── config.json                    # [JU] Points Junie at CLAUDE.md and .claude/skills/
│   └── agents/                        # [JU] Junie agent definitions — same ten agents
│
├── .scratch/                          # [ALL] Pipeline state — gitignored
│   ├── handoff.jsonl                 # Append-only structured handoff log (all agents)
│   ├── implementation-plan.md        # TDD cycle plan (feature-implementer self-tracking)
│   ├── escalations.md                # Items requiring human decision
│   └── tmp/                          # Intermediate computation files
│
├── schemas/                           # [ALL] Handoff record schemas — committed, thirteen record types
│   └── scratch/
│       ├── prd-entry.schema.json
│       ├── design-block.schema.json
│       ├── consultation-request.schema.json
│       ├── consultation-response.schema.json
│       ├── dispatch-start.schema.json
│       ├── review-feedback.schema.json
│       ├── review-plan.schema.json
│       ├── build-failure.schema.json
│       ├── build-pass.schema.json
│       ├── design-doc-autofix.schema.json
│       ├── prd-autofix.schema.json
│       ├── grader-features.schema.json
│       └── grader-verdict.schema.json
│
├── scripts/                           # [ALL] Deterministic harness helpers
│   ├── handoff.py                    # CLI launcher — sole write/query path for .scratch/handoff.jsonl
│   ├── handoff/                      # The handoff package: schema, records, routing, view
│   ├── grading.py                    # Change-grade entry composing grading/ (extract, review-plan)
│   ├── grading/                      # The grading package: config, features, handoff_facts, planner
│   ├── changeset.sh                  # Canonical change set for fresh-eyes review
│   ├── changeset.py                  # Change-set entry composing changeset/ (behind changeset.sh)
│   ├── changeset/                    # The changeset package: config, git_facts, emit
│   ├── accounting.py                 # Claude Code usage accounting (the board's cost overlay)
│   ├── doctor.py                     # Docs/ roster validator (the doctor skill's engine)
│   ├── doctor-expectations.toml      # The doctor's machine-checkable manifest
│   ├── tests/                        # Mirror test tree (tests/handoff/, test_doctor, …)
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

## 4. Reference Implementations

The pipeline is three file types: a **rules file** (`CLAUDE.md`), portable **skills** (`.claude/skills/`), and per-tool **agent definitions**. The live, authoritative copies live in the Go and Java samples; the handoff contract is the Handoff Contract section of [`agentic-harness.md`](agentic-harness.md#handoff-contract). This section shows the one pattern worth seeing up close: the same agent ported across four tools, where the prompt **body is identical** and only the **frontmatter** differs.

### Skills and routing

Skills are tool-agnostic — all four tools read `.claude/skills/`. The `handoff-routing` skill carries the routing contract and state-file inventory; the executable table lives in its `route-spec.md` companion. It lives in each sample. No per-tool variant exists.

### Agents: one body, four frontmatters

Every agent is a shared markdown body plus tool-specific frontmatter. Canonical example — the `pipeline-coordinator` body and its Claude Code frontmatter:

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

The body is byte-identical across tools. Only the frontmatter changes:

| Field | Claude Code | OpenCode | GitHub Copilot | Junie |
|---|---|---|---|---|
| File path | `.claude/agents/<name>.md` | `.opencode/agents/<name>.md` | `.github/agents/<name>.agent.md` | `.junie/agents/<name>.md` |
| Role marker | (none) | `mode: primary` / `subagent` | (none) | (none) |
| Tool grants | `tools:` + `disallowedTools:` | `permission:` map, wildcard-matched (`edit` deny also denies the write tool — reviewer scratch output rides the bash grant) | `tools:` list | `tools:` + `disallowedTools:` |
| Sonnet pin | `claude-sonnet-5` | `openrouter/anthropic/claude-sonnet-5` | `['Claude Sonnet 5 (copilot)', 'Claude Sonnet 4.6 (copilot)']` | `sonnet` |
| Opus pin | `claude-opus-5` | `openrouter/anthropic/claude-opus-5` | `['Claude Opus 5 (copilot)', 'Claude Opus 4.8 (copilot)']` | `opus` |
| Effort | `effort: low` / `high` | (no faithful counterpart; `temperature` governs sampling, not reasoning depth) | (model-managed) | `reasoningLevel: low` / `high` |
| Turn cap | `maxTurns` | `steps` | (none) | global `time-limit` |
| Skills | `skills:` list | `permission.skill` (available; the harness relies on `.claude/skills/` auto-discovery) | (derived from body) | `skills:` list |

Claude Code, OpenCode, and Copilot pin the same Opus 5 release; Junie uses the alias form. The Copilot pin is a two-entry fallback chain: Copilot silently substitutes its session default for an unavailable model, so the chain pins the fallback to the prior same-tier release. The `audit-agents` skill in each sample owns the parity rules and flags any deviation.

### Per-tool invocation differences
- **Claude Code:** invoke skills with `/<skill>`; delegate with the Agent tool.
- **OpenCode:** reference skills at `.claude/skills/<skill>/SKILL.md`; delegate with `@mention`.
- **Copilot CLI:** reference skills at `.claude/skills/`; use `/fleet` for parallel review.
- **Junie CLI:** reference skills via `skill-locations` in `.junie/config.json`; delegate by description match.

---

## 5. Pipeline Maintenance Patterns

One optional pattern keeps the pipeline healthy between features: doc-sync (align docs with code). The change-grader is the terminal pipeline stage, dispatched by default after the roster approves; a project may disable that automatic run with `layout.toml [harness] auto_grade = false` (key semantics: [`harness-project-api.md`](harness-project-api.md)). This section covers only how its grade feeds the maintenance loop.

### Documentation Synchronization (`doc-sync`)

After features merge, long-term memory (`docs/prd.md`, `docs/system-design.md`, `docs/ubiquitous-language.md`) drifts from the codebase. The `doc-sync` skill defines the structured process to detect and fix this drift. Snapshot the codebase, diff it against the three documents, apply fixes within the document boundaries, then validate with the `doc-reviewer` agent until it returns APPROVED. The full process lives in the skill.

**When to run:** After implementing features or refactoring code. Before starting a new feature cycle. Periodically to prevent documentation drift.

### Terminal Advisory Change-Grade (`change-grader`)

After every reviewer in the roster approves a feature, a terminal `change-grader` reads the diff and grades how much human attention the passing change deserves before a human merges. The grade is **advisory only**; the doctrine (never a gate, what a `concern` stream signals) is owned by [`agentic-harness.md` § Change grading in depth](agentic-harness.md#change-grading-in-depth), which points to the `change-grading` skill for the protocol. This section covers only how it fits the maintenance loop and what it reads.

**Inputs** — the dispatch conditions `handoff.py route` checks deterministically before the terminal dispatch; the engine, not this table, decides them. All derive from the latest record per `(req_id, type)` in `.scratch/handoff.jsonl`, plus the diff:

| Input | How to Determine |
|---|---|
| Tests pass | Latest `build-pass` record exists for `req_id` (no later `build-failure`) |
| Reviewers approved | Every reviewer with feedback in the current review cycle (reset only by a superseding `design-block`) holds a latest `verdict: "approved"` — the pass roster the review-plan resolved, not unconditionally all four |
| Build retry cycles | Count of `build-failure` records for `req_id` since the latest `design-block` (or feature start) |
| Design revisions | Count of `design-block` records for `req_id` that carry `supersedes_record_at` (re-triage after build-failure escalations) |

**Output:** two records appended to `.scratch/handoff.jsonl` — a `grader-features` record (the deterministic structural row extracted from the diff) and a `grader-verdict` record carrying the `clear`-versus-`concern` advisory verdict and its rationale. The grader renders the change-grade report from the verdict record and returns it in the dispatch reply; a human reads the report and merges.

**Rule:** The change-grade runs only after the latest `build-pass` record exists AND every reviewer with feedback in the current review cycle holds a latest `verdict: "approved"` (`route-spec.md` § Gate 5). A narrowed plan may not dispatch every floor reviewer. `handoff.py route` enforces the rule; the grade advises attention, it does not pass or fail the change.

---

## 6. Migration Playbook

### Phase 1: Claude Code Only (Week 1–2)

**Do first:**
1. Create `CLAUDE.md` in project root with build commands, conventions, and forbidden patterns
2. Create `.claude/skills/handoff-routing/` with SKILL.md (routing contract) and route-spec.md (the executable table)
3. Define two agents: `pipeline-coordinator` and one specialist (start with `feature-implementer`)
4. Create `schemas/scratch/` and commit the five record schemas (`prd-entry`, `design-block`, `build-failure`, `build-pass`, `review-feedback`) — the routing gate validates inbound records against these
5. Create `.scratch/` directory (containing the empty `handoff.jsonl`) and add `.scratch/` to `.gitignore`
6. Run the pipeline manually — without the coordinator — for two weeks to validate the pattern

**Do not:**
- Create all ten agents at once — start with two, add as needed
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

The steps are the same for every additional tool: install and authenticate, verify it reads `CLAUDE.md` (never create `AGENTS.md` or another rules file), verify it discovers skills in `.claude/skills/`, create its agent definitions — same personas, tool-specific frontmatter — and adopt its per-tool win.

| Tool | Agent definitions | Tool-specific setup | The key win |
|---|---|---|---|
| OpenCode | `.opencode/agents/` | Per-agent model selection in `opencode.json` | Route exploration to cheaper models (Gemini Flash, Haiku) while implementation stays on Claude via Claude Code |
| Copilot CLI | `.github/agents/` (`.agent.md`) | Optional: org-level agents in `.github-private` (Enterprise); path-specific `.instructions.md` under `.github/instructions/` | `/fleet` as a second parallel review engine; `&` cloud delegation for tasks exceeding interactive limits |
| Junie CLI | `.junie/agents/` | `.junie/config.json` pointing at `CLAUDE.md` and `.claude/skills/` (see [`cross-tool-strategy.md`](cross-tool-strategy.md)) | A JetBrains-native surface: the same pipeline for teams living in IntelliJ/GoLand |

### What to Avoid at Every Phase

- **Don't create extra rules files.** No `AGENTS.md`, no `copilot-instructions.md`. `CLAUDE.md` is the single source of truth (see [`cross-tool-strategy.md` §1](cross-tool-strategy.md#1-cross-tool-compatibility)).
- **Don't duplicate skills across paths.** `.claude/skills/` is the portable location. Period.
- **Don't put workflow logic in agent definitions.** Skills are portable; agents are not. Keep agents thin.
- **Don't skip the manual phase.** Watch the pipeline run before automating it.
- **Don't over-invest in frontier capabilities today.** The tooling is moving fast. Build for coordinated routing with parallel review (stages 4–5) and design for upward evolution.
