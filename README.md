# Agentic Coding Reference

**The problem:** AI coding agents face the same two challenges human engineers always have: keeping **long-term memory** across sessions, and running **multi-scale feedback loops** that catch drift before it compounds. The difference is degree, not kind. A human forgets between Friday and Monday; an agent forgets between one message and the next. Within days — not years — an agentic project that skips the disciplines that compensate starts drifting. Terms get picked inconsistently session-to-session, settled decisions get re-litigated, architectural choices contradict the ones made last week.

**The approach:** treat the disciplines human teams already developed for these problems as the **memory and feedback substrate**. The substrate includes documentation standards, DDD, TDD, ADRs, ubiquitous language, and XP-style nested feedback loops. Humans and agents both rely on this substrate when working on the same codebase. A file-based specialist pipeline writes to and reads from it as it works: eight agents with one job each. Coordination flows through an append-only JSONL handoff log, validated against per-record JSON Schemas at every transition. Living specs (`prd.md`, `system-design.md`, `ubiquitous-language.md`, `adr/`) are the long-term memory. One rules file (`CLAUDE.md`) works across Claude Code, Copilot CLI, OpenCode, and Junie CLI.

A common assumption is that AI lets us skip the boring rigor. The opposite is true. The rigor is what lets an agent on session 12 know what an agent on session 1 decided. It tracks which term the codebase uses for *Customer* and which approaches have already been rejected. The disciplines pay off whether or not anyone is using an agent that day: better PRs, clearer onboarding, decisions that stay decided. They land for human-only teams too.

**What's here:** two working reference implementations (Go, Spring Boot), portable skills, and enforceable documentation standards. A bidirectional `/seed` + `/harvest` loop adopts the pattern in your own project and feeds improvements back.

**Who it's for:** anyone running an agentic coding workflow over more than a few sessions, in three flavors. A solo developer driving an agent team past what fits in one conversation. A team where each developer drives their own agent team on a shared codebase. A human-only team that wants the same discipline against the slower drift humans face. The failure modes are the same; only the speed differs.

**Maturity:** the architecture, principles docs, and reference implementations are stable and in active use. The specialist pipeline machinery (JSONL contract, four-reviewer fan-out, maturity levels) is operational; its cost-effectiveness is still being measured and will be revised as evidence accumulates. Treat the disciplines as the validated core; treat the pipeline machinery as one reference implementation of the shape the harness can take.

→ Deep dive: [`agentic-harness.md`](docs/agentic-harness.md) covers the loop model and handoff contract. [`specialist-agent-workflow.md`](docs/specialist-agent-workflow.md) covers the full architecture and migration playbook. [`documentation-standards.md`](docs/documentation-standards.md) covers the writing rules that keep agents from guessing.

## Project History

- **2026-03-24** — Launch specialist agent pattern with Go and Spring Boot reference implementations.
- **2026-04-14** — Surface maturity levels; add bidirectional `/seed` + `/harvest` template sync.
- **2026-04-17** — Codify cross-tool compatibility for Claude Code, Copilot CLI, and OpenCode.
- **2026-05-08** — Switch handoff coordination to schema-validated JSONL append log.
- **2026-05-17** — Add pipeline quality bar and design-doc autofix.
- **2026-05-22** — Reframe harness around memory and feedback; add four-loop model, consultation roundtrips, cache tooling.
- **2026-05-23** — Add `history-update` skill to the root maintenance cluster.
- **2026-05-24** — Sharpen harness feedback loop: statusline diagnostics, cache-report skill, auto-cleanup.
- **2026-05-25** — Add Junie CLI as fourth tool in samples; scope root maintenance to Claude Code only.

## What It Looks Like in Practice

You type one sentence. The coordinator routes it. Agents read and update long-term memory as they go.

```text
You: "Let's discuss the feature for rate-limiting the public API"

→ coordinator reads .scratch/handoff.jsonl, sees no active feature
→ routes to product-requirements-expert
  ├─ reads  docs/prd.md, docs/ubiquitous-language.md     (existing memory)
  ├─ interviews you on goals + constraints
  ├─ writes docs/prd.md                                  (appends REQ-RL-001…004)
  ├─ writes docs/ubiquitous-language.md                  (appends terms inline as they resolve)
  └─ appends prd-entry record                            (validated against prd-entry.schema.json)

→ coordinator routes to system-design-expert (triage)
  ├─ reads  docs/system-design.md, docs/adr/, docs/ubiquitous-language.md
  ├─ runs the five-signal foundational check
  ├─ verdict: "new" — genuinely new design ground for this slice
  ├─ writes docs/system-design.md                        (token-bucket section)
  ├─ writes docs/adr/0007-rate-limiting.md               (why token-bucket over leaky-bucket)
  └─ appends design-block record                         (verdict: new)

→ coordinator routes to feature-implementer
  ├─ reads  prd.md + system-design.md + ubiquitous-language.md + latest prd-entry/design-block — modifies none
  ├─ TDD inner loop: red → green → refactor              (design discovery; tests accrue as behavioral memory)
  ├─ if implementer hits a question the triage didn't anticipate:
  │   ├─ appends consultation-request to system-design-expert
  │   ├─ coordinator dispatches system-design-expert in consultation mode
  │   ├─ system-design-expert appends consultation-response (possibly with memory_updates)
  │   └─ coordinator routes control BACK to the implementer (not forward)
  └─ appends build-pass record                           (quality gate: build, test, lint, deps-check)

→ coordinator spawns 4 reviewers in parallel
  └─ security, code-quality, tests, docs → review-feedback records (one per author)

→ coordinator routes to eval → PASS → writes .scratch/eval-<req-id>.md
→ doc-sync verifies prd.md / system-design.md / ubiquitous-language.md / code have not drifted
```

**Long-term memory** lives in `docs/` — durable specs that evolve across features. **Working memory** lives in `.scratch/` (handoff log, implementation plan, escalations, eval scorecard) — the within-feature state, cleared after merge. The implementer reads both but writes to long-term memory only through the agent that owns each document. If a question appears mid-TDD, it routes through a consultation-request rather than guessing.

## Disciplines as Memory and Feedback

Each durable artifact plays a memory role, a feedback role, or both. Together they give the project a continuous mental model that no single session has to hold.

| Artifact | Memory role | Feedback role |
|---|---|---|
| `docs/prd.md` | What the system is meant to do | Acceptance criteria for the inner loop |
| `docs/system-design.md` | How the system is structured — invariants, patterns, guardrails | Triage validates new slices against it |
| `docs/adr/*.md` | Why decisions were made; what was rejected (including non-goal ADRs) | Architectural review catches drift from committed decisions |
| `docs/ubiquitous-language.md` | Project vocabulary; terms to avoid; relationships | Inline term-drift challenge catches misuse mid-conversation |
| Tests (TDD) | Behavioral expectations that survive | Red → green → refactor at seconds-to-minutes |
| Quality gate (build, test, lint, deps-check) | Records what currently passes | Catches regressions on every build |
| Review records (`review-feedback`) | Audit trail of objections raised | Block merge until addressed |
| Handoff log (`.scratch/handoff.jsonl`) | Per-feature audit trail of every transition | Each record is schema-validated before the next dispatch |

The handoff log is the project's **working memory**. The documents under `docs/` are its **long-term memory** — durable across features.

## Nested Feedback Loops Drive Design Discovery

TDD produces good code when each cycle is fast enough to test a design hypothesis. Nested feedback loops at multiple timescales — the structure XP introduced — supply that rhythm. The harness runs four concentric loops; each surfaces a different layer of design question. Good interfaces, good architecture, and good tests fall out of running these loops with discipline; the tests are the evidence of decisions made, not the goal of the practice.

| Loop | Timescale | What design question it surfaces |
|---|---|---|
| Inner | seconds–minutes | What does this behavior need? (Interface design via red → green → refactor) |
| Middle | hours | What does this slice deliver? (Acceptance design + system-design adjustments) |
| Outer | days | What slice should we build next? (Feature design + slice sizing) |
| Architectural | months | Is the whole codebase still well-shaped? (Structural review — planned) |

The design block from the middle-loop triage is a **starting hypothesis**, not a contract. The inner loop is free — and expected — to discover better shape; consultation-request routes mid-loop discoveries back to the system-design-expert when they're worth crystallizing as long-term memory.

## Agent Pipeline

The core pattern is a file-based specialist pipeline. Each agent has one job, reads defined inputs, and writes to known outputs — record producers append to a shared handoff log, the coordinator routes from it. The filesystem is the coordination layer — auditable, interruptible, tool-agnostic.

```text
User Request
  │
  ▼
Pipeline Coordinator ─── validates each record against its JSON Schema, routes to next agent
  │
  ▼
Product Requirements Expert ──→ prd-entry record (+ ubiquitous-language updates)
  │
  ▼
System Design Expert (triage) ──→ design-block record
  │     verdict: covered | minor | new | refactor-first | foundational | conflicting
  │     conflicting → halts; user decides
  ▼
Feature Implementer ──→ quality gate (build, test, lint, deps-check)
  │     │
  │     │ (build-pass)
  │     ▼
  │   4 Reviewers (parallel) ──→ review-feedback records (one per author)
  │     │
  │     ▼
  │   Evaluation ──→ .scratch/eval-<req-id>.md
  │
  │  ↺ consultation roundtrip (mid-inner-loop)
  │    ├─ implementer appends consultation-request
  │    ├─ coordinator dispatches system-design-expert in consultation mode
  │    ├─ system-design-expert appends consultation-response (+ memory edits)
  │    └─ coordinator routes control BACK to implementer
  │
  └─ build-failure: up to 3 retries → system-design-expert re-triage; new design-block supersedes prior
```

Each arrow is an append to `.scratch/handoff.jsonl`. The coordinator validates each new record against `schemas/scratch/<type>.schema.json` before routing — malformed or missing records bounce back to the upstream agent without dispatching the next specialist. The coordinator only routes, never implements.

Every transition writes to one of two memory tiers — **long-term memory** (the durable specs in `docs/`) or **working memory** (the per-feature handoff log in `.scratch/`).

```text
agent N completes its job
  │
  ├──→ updates docs/{prd,system-design,adr,ubiquitous-language}.md   (long-term memory; owner-only)
  │
  └──→ appends record to .scratch/handoff.jsonl                       (working memory)
         │
         ▼
       coordinator picks up new record
         │
         ├─ validates against schemas/scratch/<type>.schema.json
         │    ├─ invalid → bounces back to agent N; no dispatch
         │    └─ valid   → applies routing rules
         │
         └──→ dispatches agent N+1 (back to top)
```

The system-design-expert plays the **principal-or-senior-engineer archetype**: most of the cross-feature mental model stays in its head, and only the load-bearing parts get crystallized into `system-design.md` and `adr/`. Two demand-driven modes — *triage* on every slice (returns one of six verdicts), and *consultation* on demand when the implementer hits a question mid-loop. Consultation roundtrips preserve the implementer's active state: after a consultation-response, the coordinator routes back to the implementer, not forward to the next pipeline stage.

If the implementer fails the quality gate, it appends a `build-failure` record. The coordinator retries with that error context for up to 3 attempts, then re-triages with the system-design-expert; the resulting design-block supersedes the prior one and the retry counter resets.

## Spec-Driven Development

The pipeline is driven by four living documents — the project's **long-term memory** — that agents treat as authoritative across sessions:

| Document | Role | Owner Agent | Describes |
|----------|------|-------------|-----------|
| `docs/prd.md` | Strategic truth | product-requirements-expert | **What** to build — goals, requirements, acceptance criteria, constraints |
| `docs/system-design.md` | Tactical truth | system-design-expert | **How** to build — architecture, invariants, patterns, guardrails |
| `docs/adr/*.md` | Decision records | system-design-expert (architectural ADRs); product-requirements-expert (non-goal ADRs) | **Why** — trade-offs, alternatives considered, what was rejected |
| `docs/ubiquitous-language.md` | Vocabulary truth | product-requirements-expert | **Words** — domain terms, relationships, terms to avoid |

Each document has a single owner agent. Only the owner writes to it. The feature-implementer reads all four but modifies none — when it encounters a question mid-loop, it routes through a consultation-request rather than guessing.

The boundary rule is simple: **if it would change when switching languages, it belongs in system-design.md, not the PRD.** The PRD uses behavioral language ("the system retries the operation"), never code ("call `Retry()`"). System-design.md describes contracts and structure, never duplicates runnable source code. The ubiquitous language updates inline as terms resolve during requirements interviews — drift is challenged mid-conversation, not absorbed silently. See [`documentation-standards.md`](docs/documentation-standards.md) for the full ownership matrix and cross-reference rules.

## Writing for Agents and Humans

Agents read documentation before every task, and humans read it before every review. Vague prose and ambiguous boundaries degrade both — but agents degrade faster, because they do not ask for clarification when confused. They guess. The same rules that make docs clear for agents make them clear for humans.

The [documentation standards](docs/documentation-standards.md) turn this into enforceable rules:

| Area | Rule |
|------|------|
| **Writing** | Maximum 30 words per sentence. Replace adjectives with data. Prohibited-words list blocks claims without supporting measurements. |
| **Abstraction** | Five document levels — Meta (`CLAUDE.md`), Strategic (`prd.md`), Decision (`adr/`), Tactical (`system-design.md`), Language (`ubiquitous-language.md`). One owner per level, no overlap. |
| **Structure** | Every section opens with a Level 1 prose summary (≤200 words) before detail. Each level is self-contained — a reader can stop anywhere and walk away informed. |
| **Agent optimization** | Tables over prose for structured data. HTML anchors on requirement IDs. Parseable section templates for PRD entries, ADRs, and state machines. |
| **Validation** | Pre-merge checklist covering structure, cross-document coherence, abstraction level, and writing standards. |

See [prohibited patterns](docs/documentation-standards.md#prohibited-patterns) for the full list of what not to write.

## Quick Start

### Try a reference implementation

```bash
# Go
cd go/
make ci                      # tidy, fmt, vet, lint, deps-check, test, build

# Java Spring Boot
cd java-spring-boot/
./gradlew build              # compile, format check, test, package
```

### Use with an agent tool

Open either project directory. Configuration loads automatically.

```bash
cd go/          # or cd java-spring-boot/
claude          # Claude Code
copilot         # Copilot CLI
opencode        # OpenCode
junie           # Junie CLI
```

## Adopt in Your Own Project

Each implementation ships two skills that form a bidirectional loop between this reference and real projects. All are invokable in all four tools (Claude Code, Copilot CLI, OpenCode, Junie CLI). `/seed` works in two modes. **Init** runs on an empty target to scaffold a new project. **Upgrade** runs on an existing project to pull in template improvements without overwriting domain work. `/harvest` runs in the opposite direction, pulling generalizable improvements from your project back into the template.

| Command | Direction | What it does |
|---------|-----------|--------------|
| `/seed <project-path>` | Reference → your project | **Init mode** (fresh target): copy agents, skills, and doc scaffolding; fill `{{PROJECT_NAME}}` and `{{PROJECT_DESCRIPTION}}`. **Upgrade mode** (existing target): section-level merge that pushes template improvements while preserving domain customizations — filled Security Context, real `REQ-*` IDs, real file paths. |
| `/harvest <project-path>` | Your project → reference | Diff a real project against the template. Classify each change as **harvest** (generic improvement), **skip** (domain-specific), or **ask** (ambiguous). Auto-generalize domain patterns on the way back (`REQ-DL-*` → `REQ-XX-*`, `internal/render/render.go` → `internal/example/handler.go`). |

### Examples

Skills run inside the agent tool, from the reference implementation directory, via `/skill-name <args>`. Examples use Claude Code; Copilot CLI (`copilot`), OpenCode (`opencode`), and Junie CLI (`junie`) have equivalent flows.

```bash
# Init — scaffold a new project (empty target)
$ cd go/
$ claude
> /seed ../my-service                # prompts for name + description

$ cd java-spring-boot/
$ claude
> /seed ../my-app                    # also prompts for build tool (gradle | maven)

# Upgrade — raise the bar on an existing project (auto-detects name,
# description, and build tool from the target; no prompts if already filled)
$ cd go/                             # or cd java-spring-boot/
$ claude
> /seed ../my-existing-service

# Harvest — pull improvements from your project back into the reference
$ cd ../my-existing-service
$ claude
> /harvest ../agentic-coding-reference/go
```

The Java examples show Gradle defaults. `/seed` also supports Maven targets in both modes. In init mode, picking `maven` at the prompt generates an idiomatic `pom.xml` via [start.spring.io](https://start.spring.io) and writes Maven equivalents to `CLAUDE.md` Build Commands and `settings.local.json` permissions. In upgrade mode, seed auto-detects `pom.xml` and translates template pushes to Maven commands.

Improvements discovered while shipping real features flow back into the template. Template improvements flow out to every downstream project. Neither direction overwrites domain work.

## Principles

The [`docs/`](docs/) directory contains cross-cutting principles — the memory schema that both implementations write to and read from.

| Document | Covers |
|----------|--------|
| [`agentic-harness.md`](docs/agentic-harness.md) | The four-loop model, slice definition, agent roster, handoff contract, triage and consultation modes |
| [`specialist-agent-workflow.md`](docs/specialist-agent-workflow.md) | Pipeline architecture, cross-tool compatibility, maturity levels, migration playbook |
| [`documentation-standards.md`](docs/documentation-standards.md) | Writing for agents, document ownership, validation checklist |
| [`tdd-principles.md`](docs/tdd-principles.md) | TDD as design discovery via the inner loop (XP-rooted), eight-clause conjunctive bar |
| [`testing-principles.md`](docs/testing-principles.md) | Test pyramid, no-mock policy, four-phase structure |
| [`ddd-principles.md`](docs/ddd-principles.md) | Modulith architecture, domain types, aggregate structure, naming conventions |

## Reference Implementations

Go and Spring Boot represent different paradigms — explicit vs convention-driven. When a pattern works in both, it transfers. When they diverge, the differences are instructive.

| | Go ([`go/`](go/)) | Java Spring Boot ([`java-spring-boot/`](java-spring-boot/)) |
|---|---|---|
| **Toolchain** | Go 1.26, golangci-lint, Make | Java 25, Gradle 9.5.0, Spring Boot 4.0.6 |
| **Agents** | 8 specialists across 4 tools | 8 specialists across 4 tools |
| **Skills** | 20 portable skills | 20 portable skills |
| **Entry point** | [`go/CLAUDE.md`](go/CLAUDE.md) | [`java-spring-boot/CLAUDE.md`](java-spring-boot/CLAUDE.md) |

Each implementation is self-contained. The project `CLAUDE.md` is the authoritative source for build commands, conventions, and agent workflow within that directory.

## Cross-Tool Compatibility

All four major AI coding tools read `CLAUDE.md` natively or via configuration. Skills in `.claude/skills/` are discovered by all four. Agent definitions are tool-specific — each tool has its own directory; bodies stay identical, only frontmatter differs.

| Location | Claude Code | Copilot CLI | OpenCode | Junie CLI |
|----------|:-----------:|:-----------:|:--------:|:---------:|
| `CLAUDE.md` | Yes | Yes (native) | Yes (fallback) | Yes (config) |
| `.claude/skills/*/SKILL.md` | Yes | Yes | Yes | Yes |
| `.claude/agents/*.md` | Yes | — | — | — |
| `.github/agents/*.agent.md` | — | Yes | — | — |
| `.opencode/agents/*.md` | — | — | Yes | — |
| `.junie/agents/*.md` | — | — | — | Yes |

Creating `AGENTS.md` breaks OpenCode's fallback to `CLAUDE.md`. Creating `copilot-instructions.md` causes additive merging. One rules file avoids both problems.

For JetBrains, Cursor, or Windsurf plugin users, see [IDE Compatibility](docs/specialist-agent-workflow.md#3-ide-compatibility) for the symlink-based extension path.

## Maturity Levels

The pipeline is an adoption ladder, not a fixed architecture. Each level describes a *capability shipped*. Whether moving to a higher level *pays off* for your workload is a separate question — measure with the `feature-eval` scorecards before committing.

| Level | Name | What changes |
|:-:|------|--------------|
| 1 | Manual Pipeline | Human invokes each specialist agent by hand. Validates the pattern. |
| 2 | Coordinator + Automated Routing | A coordinator agent reads `.scratch/handoff.jsonl`, validates each new record against its schema, and routes to the next specialist. |
| 3 | Parallel Reviewers | Four reviewers run as parallel subagents. Sub-5-minute review cycles. |
| 4 | Agent Teams Collaborative Review (experimental) | Reviewers communicate directly. Requires Claude Code v2.1.32+, Opus 4.6, opt-in flag. |
| 5 | Architectural Review Loop (planned) | Periodic (months-cadence) structural-decay audit. The fourth nested loop in the XP-style structure (see [`agentic-harness.md`](docs/agentic-harness.md)). |

See [§4 of the workflow doc](docs/specialist-agent-workflow.md#4-maturity-progression) for when to use each level, when to move on, and the tradeoffs.

## Pipeline Maintenance

Two patterns keep the pipeline healthy between features:

| Pattern | Purpose |
|---------|---------|
| `doc-sync` | Detect and fix drift between `docs/prd.md`, `docs/system-design.md`, `docs/ubiquitous-language.md`, and the codebase after features merge. |
| `feature-eval` | Scorecard written after each feature. PASS/FAIL verdict plus retry-cost assessment. Creates an audit trail that surfaces systemic issues — repeated build failures point to design problems; repeated review cycles point to unclear requirements. |

See [§7 of the workflow doc](docs/specialist-agent-workflow.md#7-pipeline-maintenance-patterns) for the full process.

## Reference Upkeep

Five root-level skills keep this reference itself consistent:

| Skill | Purpose |
|-------|---------|
| `research-update` | Fetch upstream tool docs, compare claims against current state, report drift. |
| `audit-consistency` | Verify both implementations match root docs and each other. |
| `deps-upgrade` | Check pinned tool/plugin/dependency versions against upstream, bump and verify. |
| `harness-stats-setup` | Install or update the user-level statusline and cache-report tooling from `tools/harness-stats/` into `~/.claude/`. |
| `history-update` | Refresh the Project History section in the README with executive-level milestones since the last entry. |

## Harness Stats

Optional user-level tooling that surfaces whether the specialist constellation is using prompt caching efficiently. Repeated specialist fires only pay off when fires cluster tightly enough to amortize the 1.25× cache-write premium across many 0.10× cache reads — the tooling makes that visible.

Two artifacts installed into `~/.claude/`: a live statusline and an on-demand per-agent report. The statusline shows session-wide token totals, cache hit %, parallel-fan-out count, the most recently finished agent's contribution, and per-agent tool-cap pressure — with an alert when a parallel subagent approaches the per-response truncation limit. The report shows which specialists are paying off and which are paying the write premium without amortizing.

| Skill | Purpose |
|-------|---------|
| `harness-stats-setup` | Install or update the tooling. Detects drift between this repo and `~/.claude/`, applies on approval, merges the `statusLine` block into `~/.claude/settings.json` without clobbering other keys. |
| `cache-report` | Run the per-agent report on demand (installed by the setup skill). |

See [`tools/harness-stats/README.md`](tools/harness-stats/README.md) for installation, output formats, metric definitions, and the rationale for why repeated specialist fires make this measurement worth caring about.

## Repository Structure

```text
.
├── docs/                              # Cross-cutting principles
├── go/                                # Go reference implementation
│   ├── CLAUDE.md                      # Project rules (all 4 tools read this)
│   ├── .claude/agents/                # 8 Claude Code agents
│   ├── .claude/skills/                # 20 portable skills
│   ├── .opencode/agents/              # 8 OpenCode agents
│   ├── .github/agents/                # 8 Copilot agents
│   └── .junie/agents/                 # 8 Junie agents
├── java-spring-boot/                  # Spring Boot reference implementation
│   ├── CLAUDE.md
│   ├── .claude/agents/
│   ├── .claude/skills/
│   ├── .opencode/agents/
│   ├── .github/agents/
│   └── .junie/agents/
├── tools/                             # Optional companion tooling
│   └── harness-stats/                 # Cache-efficiency statusline + report
├── .claude/skills/                    # Root-level maintenance skills
└── CLAUDE.md                          # Monorepo instructions
```

## Disclaimer

This is a personal learning project. It documents patterns and ideas the author explored while experimenting with AI coding agents.

Use anything here freely under the [MIT License](LICENSE), but at your own risk. Evaluate everything yourself before applying it to your own work.

This project is not affiliated with, endorsed by, or sponsored by Anthropic, GitHub, or any other tool vendor mentioned in this repository. All product names, trademarks, and registered trademarks are the property of their respective owners and are used here solely for identification and descriptive purposes.

## License

[MIT License](LICENSE)
