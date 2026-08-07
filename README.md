<a href="https://github.com/woditschka/agentic-coding-reference/actions/workflows/checks.yml?query=branch%3Amain+event%3Apush"><img align="right" src="https://github.com/woditschka/agentic-coding-reference/actions/workflows/checks.yml/badge.svg?branch=main&amp;event=push" alt="checks"></a>

# Agentic Coding Reference

*Agentic coding that amplifies an engineer's judgment instead of replacing it.*

**Ship in days what would otherwise die in triage — and hold a high bar for years.** The work worth trying but never worth weeks gets built and tested against real users instead of shelved. The bar holds because durable specs and nested feedback loops keep every agent, session, and person pointed the same way.

> **TL;DR** — The interface is a conversation; the machinery behind it is deep. A file-based pipeline of ten one-job specialist agents builds one vertical slice at a time. Each appends a schema-validated record to a shared log, a deterministic router dispatches from it, and a reviewer roster gates every change; an advisory change-grader then flags where human attention pays — nothing auto-merges. The work runs through four nested feedback loops, from the inner TDD cycle out to whole-codebase review, so drift is caught before it compounds. Durable specs — PRD, system design, ADRs, ubiquitous language — are the shared memory every agent, session, and person reads and writes. One `CLAUDE.md` carries it across four agent tools; `/materialize` and `/harvest` adopt it in your project and feed improvements back.

**You don't use the agents directly.** Adopt the harness, start a conversation, and describe the feature — the right specialists are selected for you, behind the scenes. It's an engineering team you collaborate with, not a toolbox you operate. The depth documented below is for building and extending the harness itself; to adopt it, the [Quick Start](#quick-start) is enough.

## Why This Exists

An agent forgets between one message and the next, the way a human forgets between Friday and Monday — and within days, not years, a project that skips the compensating disciplines drifts: inconsistent terms, re-litigated decisions, this week's architecture contradicting last week's. The harness treats the disciplines human teams already built — documentation standards, DDD, TDD, ADRs, ubiquitous language, XP-style nested loops — as the **memory and feedback substrate** every agent, session, and person reads and writes ([the full statement](docs/agentic-harness.md#what-the-harness-is-for)). A file-based specialist pipeline of ten one-job agents operates it, building one vertical slice at a time. A single rules file (`CLAUDE.md`) carries it across Claude Code, Copilot CLI, OpenCode, and Junie CLI.

Two working reference implementations (Go, Spring Boot), portable skills, and enforceable documentation standards demonstrate the pattern; a bidirectional `/materialize` + `/harvest` loop adopts it in your own project and feeds improvements back.

<p align="center">
  <img src="docs/images/pipeline-flow.drawio.png" width="640" alt="The agentic harness pipeline in three layers: a long-term memory band of durable specs (prd.md, system-design.md, adr/, ubiquitous-language) on top; a vertical specialist flow — product-requirements, system-design, feature-implementer, reviewer roster, change-grader, human — inside four nested loop bands, with requested-flow arrows for consultation, rework, and next-slice; and a short-term memory band of the append-only handoff.jsonl record stream on the bottom. A slim routing layer (route script plus coordinator) sits between the flow and the log it reads.">
</p>

It is for anyone running an agentic coding workflow over more than a few sessions:

- a solo developer driving an agent team past what fits in one conversation;
- a team where each developer drives their own agent team on a shared codebase;
- a human-only team that wants the same discipline against the slower drift humans face.

The failure modes are the same; only the speed differs.

The architecture, principles docs, and reference implementations are stable and in active use. The specialist pipeline machinery (JSONL contract, reviewer-roster fan-out, capability progression) is operational, and its cost is now measured two ways: [Harness Stats](#harness-stats) instruments the live session, and the [eval bench](evals/README.md) tracks cost per pass across harness versions against a fixed subject project. Treat the disciplines as the validated core and the pipeline machinery as one reference implementation of the shape the harness can take.

→ Deep dive: [`agentic-harness.md`](docs/agentic-harness.md) covers the loop model and handoff contract. [`specialist-agent-workflow.md`](docs/specialist-agent-workflow.md) covers the full architecture and migration playbook. The [`document-writing` skill](harness/core/.claude/skills/document-writing/documentation-standards.md) covers the writing rules that keep agents from guessing.

The sections move from **how it works** to **trying it** to **reference**.

## The Force Multiplier and Your Part in It

An agent multiplies whatever it is pointed at. Judgment is the scarce input — you supply the design and the standards; the harness supplies the memory, discipline, and execution that amplify them. The disciplines that keep the multiplier raising quality rather than noise — TDD, DDD, owned specs, ADRs — matter more at this speed, not less.

How the work divides:

- **You decide.** Requirements, design, and standards are yours; the agent does not set them.
- **The agent researches and critiques.** It proves or disproves a direction, researches the ground, and surfaces options you had not weighed — widening the choice space you decide within. It improves the inputs to a decision, not the decision.
- **Design is discovered in the dialogue,** and against real user feedback once a slice ships — not in the inner loop, which only settles interface shape. What the dialogue produces is captured as memory at three levels: **what** to build (`prd.md`), **how** it is structured (`system-design.md`), and **why** it won over the alternatives (`adr/`). That separation is what lets a decision outlast the session that made it.

The same collaboration runs at three flight levels, each writing the memory that keeps agents, sessions, and people pointed the same way:

| Flight level | Who decides | The agent's work | What holds the direction |
|---|---|---|---|
| Within a slice | the engineer | proposes, challenges, builds | tests · `system-design.md` |
| Across slices | the team | drives each slice; surfaces conflicts | `prd.md` · ubiquitous language |
| Whole codebase | the architect seat | sweeps for drift at machine speed | `adr/` · `system-design.md` |

The top level is the one teams skip under deadline: whole-codebase coherence review costs days of legwork. The agent does that legwork at machine speed; the architect seat brings the judgment. The multiplier makes the review affordable — it does not remove the seat.

Range is rewarded, not required. The harness amplifies whatever judgment it is given. An engineer who reads the customer, the system, and the code at once catches drift at every level the agent moves through. A less experienced engineer gets the same scaffolding around their own decisions. What it will not do, at any level, is supply judgment that is not there.

The payoff is a build-ship-watch loop measured in days, not weeks — short enough to keep pace with how user needs surface. The harness is the fixed cost that makes this repeatable: paid once, it holds every feature to your standards across sessions, so speed never costs direction.

## What It Looks Like in Practice

You type one sentence. The router dispatches each hop — a script for decided transitions, a coordinator for untriaged intake and escalations. Agents read and update long-term memory as they go.

```text
You: "Let's discuss the feature for rate-limiting the public API"

→ root loads prd-authoring and interviews you directly     (goals, constraints, non-goals)
  └─ you confirm the exit; the decisions are distilled

→ root dispatches product-requirements-expert with the distilled decisions
  ├─ reads  docs/prd.md, docs/ubiquitous-language.md     (existing memory)
  ├─ judges the distillate cold — pushback returns as a consultation-request targeting human
  ├─ writes docs/prd.md                                  (appends REQ-RL-001…004)
  ├─ writes docs/ubiquitous-language.md                  (appends the terms the interview resolved)
  └─ appends prd-entry record                            (validated against prd-entry.schema.json)

→ route dispatches system-design-expert (triage)
  ├─ reads  docs/system-design.md, docs/adr/, docs/ubiquitous-language.md
  ├─ runs the five-signal foundational check
  ├─ verdict: "new" — genuinely new design ground for this slice
  ├─ writes docs/system-design.md                        (token-bucket section)
  ├─ writes docs/adr/2026-07-02-rate-limiting.md         (why token-bucket over leaky-bucket)
  └─ appends design-block record                         (verdict: new)

→ route dispatches feature-implementer
  ├─ reads  prd.md + system-design.md + ubiquitous-language.md + latest prd-entry/design-block — modifies none
  ├─ TDD inner loop: red → green → refactor              (design discovery; tests accrue as behavioral memory)
  ├─ if implementer hits a question the triage didn't anticipate:
  │   ├─ appends consultation-request to system-design-expert
  │   ├─ route dispatches system-design-expert in consultation mode
  │   ├─ system-design-expert appends consultation-response (possibly with memory_updates)
  │   └─ route returns control BACK to the implementer (not forward)
  └─ appends build-pass record                           (quality gate: build, test, lint, deps-check)

→ route dispatches the reviewer roster in parallel
  └─ security, code-quality, tests, docs → review-feedback records (one per author)

→ route dispatches change-grader (terminal, advisory; default-on)
  └─ reads the diff, writes grader-verdict record (clear | concern) — surfaced to you; nothing auto-merges
→ doc-sync verifies prd.md / system-design.md / ubiquitous-language.md / code have not drifted
```

Each step either updates a durable spec in `docs/` or appends to the per-feature log in `.scratch/` — the project's two memory tiers.

## Memory and Feedback

The substrate has two faces. As **memory**, each durable artifact records a decision so no single session has to hold it. As **feedback**, the same artifacts and the nested loops catch drift while it is still cheap to fix. **Long-term memory** lives in `docs/` — durable specs that evolve across features. **Working memory** lives in `.scratch/` — the per-feature handoff log and implementation plan, cleared after merge. Each artifact plays a memory role, a feedback role, or both; the [`agentic-harness.md`](docs/agentic-harness.md#disciplines-as-memory-and-feedback) artifact table lists every one.

Feedback runs in four nested loops, the structure XP introduced. Each iterates over a different unit, from the inner TDD cycle over one behavior out to the architectural loop over the whole codebase. The full loop model — the unit and the design question each one settles — is in [`agentic-harness.md`](docs/agentic-harness.md#nested-feedback-loops-drive-design-discovery).

The design block from the middle-loop triage is a **starting hypothesis**, not a contract. The inner loop is free — and expected — to discover better shape; a consultation-request routes mid-loop discoveries back to the system-design-expert when they are worth crystallizing as long-term memory. Good interfaces and tests fall out of the inner loop; the larger architecture takes shape in the dialogue the outer loops frame.

## The Pipeline

The core pattern is a file-based specialist pipeline. Each agent has one job, reads defined inputs, and writes to known outputs — record producers append to a shared handoff log, the router dispatches from it. The filesystem is the coordination layer: auditable, interruptible, tool-agnostic. The figure near the top of this page shows the shape: requirements → design triage → TDD implementation → parallel review → advisory grade, with consultation and rework loops between the stages.

Each handoff is an append to `.scratch/handoff.jsonl`, validated against its per-type JSON Schema before routing. A malformed or missing record bounces back to the upstream agent; the next specialist is not dispatched. `handoff.py route` decides every table-decided transition; the coordinator resolves only untriaged intake and escalations, and neither implements. Four living documents are the pipeline's long-term memory — `prd.md` (**what**), `system-design.md` (**how**), `adr/` (**why**), and `ubiquitous-language.md` (**words**) — each with a single owner agent (the documented carve-outs live with the roster). The boundary rule is simple: **if it would change when switching languages, it belongs in `system-design.md`, not the PRD.** The triage verdicts, retry and recovery paths, and consultation mechanics live in [`agentic-harness.md`](docs/agentic-harness.md). The owner-per-document roster is in [`harness-project-api.md`](docs/harness-project-api.md#file-roster).

Agents read these documents before every task and guess when they are vague. So the docs follow enforceable standards: a 30-word sentence cap, one owner per level, tables over prose, parseable templates for PRD entries, ADRs, and state machines. The same rules that make docs clear for agents make them clear for humans. See [prohibited patterns](harness/core/.claude/skills/document-writing/documentation-standards.md#prohibited-patterns) for what not to write.

## Change Grading

After the reviewers approve, they have answered *is this change correct*. A terminal `change-grader` answers a different question the gate does not: **how much human attention this passing change deserves before it merges.** The grade is **advisory-only**: nothing routes on the verdict, nothing auto-merges — a human always makes the merge click. Because nothing routes on it, the automatic run is optional: `layout.toml [harness] auto_grade = false` skips it, and the grader stays runnable by hand. The five facets, the worst-facet aggregation, and the report format live in the [`change-grading` skill](harness/core/.claude/skills/change-grading/SKILL.md).

## Tool-Use Limits and Continuation

Each agent dispatch runs under a tool-call cap, and the SDK truncates a dispatch that reaches it. A Scoping Pre-Check before the dispatch separates *scope* from *length*. Work spanning more than one behavior bounces back for a re-scope; a single long behavior proceeds, naming a checkpoint for a partial-artifact handoff. After a truncation, recovery **continues the same slice** rather than re-splitting. In Claude Code the continuation resumes the same sub-agent in place, constrained by a fail-closed hook that accepts only the literal `continue`. The detection rule, the full recovery table, and the budget contract are in [`agentic-harness.md`](docs/agentic-harness.md#dispatch-event-contract-and-recovery-paths).

## Model Tier Assignment

Each specialist's model is pinned in its agent definition. The split follows task type, under a fixed objective ordering: quality bar first, cost second, wall-clock time third.

| Tier | Agents |
|------|--------|
| Opus 5 | product-requirements-expert, system-design-expert, feature-implementer, security-reviewer, change-grader |
| Sonnet 5 | pipeline-coordinator, review-planner, code-quality-reviewer, test-reviewer, doc-reviewer |

Judgment roles get the premium tier because their errors compound downstream; checklist and routing roles sit one tier below. The mixed fan-out costs about 70% of a uniform-Opus one. Models are pinned to explicit versions, not aliases, so a release never shifts behavior silently; bumps run through `deps-upgrade`. The full split rules, cost math, and rejected alternatives: [`docs/adr/2026-06-11-model-tier-assignment.md`](docs/adr/2026-06-11-model-tier-assignment.md).

## Quick Start

### Try a reference implementation

```bash
# Go
cd samples/go/
make ci                      # the full quality gate

# Java Spring Boot
cd samples/java-spring-boot/
./gradlew build              # compile, format check, test, package
```

### Use with an agent tool

Open any sample directory. Configuration loads automatically.

```bash
cd samples/go/          # or samples/java-spring-boot/, samples/generic/
claude          # Claude Code
copilot         # Copilot CLI
opencode        # OpenCode
junie           # Junie CLI
```

### Adopt in your own project

The same commands onboard a new project and upgrade an existing one. They run from this reference's root in Claude Code:

```bash
$ cd agentic-coding-reference
$ git fetch --tags && git checkout $(git describe --tags --abbrev=0 origin/main)   # latest release, not main
$ claude

# Onboard or upgrade — completely replaces the harness runtime, keeps your files.
> /materialize ../my-service

# Pull improvements from your project back into the reference.
> /harvest ../my-service
```

The steps, the project-controlled options, customization after onboarding, the ownership contract, and what checks the runtime before it reaches your machine are in the [Adoption Guide](docs/adoption-guide.md).

## One Source, Three Channels

<p align="center">
  <img src="docs/images/harness-lifecycle.drawio.png" width="720" alt="One /harness source fans into three channels — copy, manifest, and per-stack-per-tool marketplace plugins — feeding a consumer project, with a harvest return path back to the source.">
</p>

One `/harness` source reaches a consumer three ways: **copy** — runtime committed into the project, the default; **manifest** — runtime materialized and gitignored; **marketplace** — per-stack, per-tool plugins. The reference repo *is* the marketplace. The project-owned files stay committed on every channel, and `/harvest` closes the loop by pulling generalizable improvements back into the source. Channel semantics, switching, and the marketplace install: [Adoption Guide § Distribution channels](docs/adoption-guide.md#distribution-channels).

## Reference Implementations

Go and Spring Boot represent different paradigms — explicit vs convention-driven. When a pattern works in both, it transfers. When they diverge, the differences are instructive.

| | Go ([`samples/go/`](samples/go/)) | Java Spring Boot ([`samples/java-spring-boot/`](samples/java-spring-boot/)) |
|---|---|---|
| **Toolchain** | Go 1.26, golangci-lint, Make | Java 25, Gradle 9.6.1, Spring Boot 4.1.0 |
| **Agents** | 10 specialists across 4 tools | 10 specialists across 4 tools |
| **Skills** | 24 portable skills (incl. 2 GoLand oracle skills) | 24 portable skills (incl. 2 IntelliJ oracle skills) |
| **Entry point** | [`samples/go/CLAUDE.md`](samples/go/CLAUDE.md) | [`samples/java-spring-boot/CLAUDE.md`](samples/java-spring-boot/CLAUDE.md) |

Each implementation is self-contained. The project `CLAUDE.md` is the authoritative source for build commands, conventions, and agent workflow within that directory. A third, technology-free instance ([`samples/generic/`](samples/generic/)) binds its build through `scripts/stack.sh` verb stubs.

## Cross-Tool Compatibility

One `CLAUDE.md` and one `.claude/skills/` tree serve all four tools. Agent definitions are per-tool with identical bodies and tool-specific frontmatter:

| Location | Claude Code | Copilot CLI | OpenCode | Junie CLI |
|----------|:-----------:|:-----------:|:--------:|:---------:|
| `CLAUDE.md` | Yes | Yes (native) | Yes (fallback) | Yes (config) |
| `.claude/skills/*/SKILL.md` | Yes | Yes | Yes | Yes |
| `.claude/agents/*.md` | Yes | — | — | — |
| `.github/agents/*.agent.md` | — | Yes | — | — |
| `.opencode/agents/*.md` | — | — | Yes | — |
| `.junie/agents/*.md` | — | — | — | Yes |

Do not create `AGENTS.md` or `copilot-instructions.md`; both break the single-rules-file model. The full rules-file, skills, and agent matrices, the IDE extension paths, the gotchas, and the tool-choice framework are in [`cross-tool-strategy.md`](docs/cross-tool-strategy.md). An optional JetBrains MCP oracle grounds semantic questions in the IDE's resolved model — see the [Adoption Guide](docs/adoption-guide.md#jetbrains-semantic-oracle).

## Capability Progression

The harness grew from a single prompt by adding one capability at a time, each closing a specific failure of the one before it. It runs through a rules file (`CLAUDE.md`), skills, specialist subagents, and coordinated routing, each adding the memory or feedback the stage before it lacked. The reviewer roster runs in parallel — latency relief at no extra tokens. Add a capability when you hit the failure it closes — not before. The far end is this reference's demonstration, not a target; measure with Harness Stats before adding any layer.

Around this runs a slower **architectural loop** — periodic drift review that writes back to long-term memory. Today it reviews the reference itself (cross-project consistency, docs, agent parity, upstream changes, versions); pointing it at application-code structural decay is the open extension. The full stage-by-stage path, the per-layer cost, and the frontier beyond it are in [§2 of the workflow doc](docs/specialist-agent-workflow.md#2-capability-progression).

## Harness Stats

Running a constellation of specialists has a cost the chat UI does not surface. Harness Stats makes it visible — a live statusline on every turn (tokens, cost, cache hit rate, parallel fan-out, at-risk agents) and an on-demand per-agent cache report. This is the feedback loop turned on the harness itself: the in-session instrument for the cost-effectiveness question raised up front. The cross-version instrument is the [eval bench](evals/README.md). The statusline cell reference, the report, and setup live in the [Adoption Guide § Harness Stats](docs/adoption-guide.md#harness-stats) and [`tools/harness-stats/README.md`](tools/harness-stats/README.md).

## The Eval Bench

Claims about agent harnesses are cheap; measurements are not. The [eval bench](evals/README.md) prices every harness version against one fixed subject project: frozen prompts, a machine-verified bar (held-out oracle plus full suite), and cost per pass. [`TREND.md`](evals/results/TREND.md) holds the series — one table per task, every figure regenerated from the committed run folders, never hand-edited. An advisory blind judge scores each passing change so quality drift the binary bar cannot see stays visible.

The loop closes on this repository itself. The v0.2.0 sweep caught a +90% cost-per-pass regression on the bench's cheapest task. The run ledgers named the mechanism — a review-cycle reset re-running the full reviewer battery — and the fix landed as [ADR 2026-08-07](docs/adr/2026-08-07-review-cycle-survives-mid-slice-design-records.md) with engine tests pinning it. When the harness changes, a dev sweep can price the candidate against the tagged series before the version is cut.

## Where to Go Next

| You want to… | Read |
|---|---|
| Understand the machinery in depth | [`agentic-harness.md`](docs/agentic-harness.md) — the four-loop model, slice definition, agent roster, handoff contract, grading, recovery |
| Adopt the harness in your project | [Adoption Guide](docs/adoption-guide.md) — onboarding, upgrading, channels, the ownership contract, optional tooling |
| Study the architecture or migrate stepwise | [`specialist-agent-workflow.md`](docs/specialist-agent-workflow.md) — design principles, capability progression, canonical layout, migration playbook |
| Compare or configure the four agent tools | [`cross-tool-strategy.md`](docs/cross-tool-strategy.md) — rules-file/skill/agent matrices, IDE paths, tool-choice framework |
| Check the contract a project owns | [`harness-project-api.md`](docs/harness-project-api.md) — the seven-brief roster and validation contract (spec 0.2.0) |
| Write documents agents can execute | [`document-writing` skill](harness/core/.claude/skills/document-writing/documentation-standards.md) — writing standards, ownership, prohibited patterns |
| Measure a harness version | [`evals/README.md`](evals/README.md) — cost per pass against a fixed SUT; results in [`TREND.md`](evals/results/TREND.md) |
| Look up a harness term | [Glossary](docs/glossary.md) — the working vocabulary, each entry linking its canonical home |
| Understand why the harness evolved this way | [`docs/adr/`](docs/adr/) — the decision log; pairs with [Project History](#project-history) below |
| See why the kernel disciplines are fixed | [`tdd-principles.md`](harness/core/.claude/skills/tdd-workflow/tdd-principles.md) · [`ddd-principles.md`](docs/ddd-principles.md) |
| Maintain this reference | [`CLAUDE.md`](CLAUDE.md) — the maintainer loop and root skills · [`harness/README.md`](harness/README.md) — the source tree, scripts, and battery |

## Repository Structure

```text
.
├── docs/                              # Principles, guides, and the decision log (adr/)
├── harness/                           # Single canonical harness source — samples materialize from here
│                                      #   core/ + stacks/<stack>/ + init/ + claude-md/ + marketplace/ + *.py/*.sh — see harness/README.md
├── samples/                           # Materialized instances of the harness (copy channel)
│   ├── go/                            # Go reference implementation
│   ├── java-spring-boot/              # Spring Boot reference implementation
│   └── generic/                       # Technology-free starting template — verbs unbound, briefs {{FILL}}
├── evals/                             # Harness eval bench: frozen tasks vs. a fixed SUT, per version (results/TREND.md)
├── tools/                             # Optional user-level tooling (installs to ~, never into a project)
│   ├── harness-stats/                 # Cache-efficiency statusline + report
│   └── claude-dev/                    # Container-confined Claude Code for reduced-approval runs
├── .claude-plugin/                    # Generated: marketplace.json (the reference IS a marketplace)
├── plugins/                           # Generated: per-tool plugins, rendered by package-marketplace.py
├── .claude/skills/                    # Root maintenance skills (init, materialize, harvest, audit-harness, …)
└── CLAUDE.md                          # Monorepo instructions + the maintainer loop
```

## Project History

### Before This Project

The research did not begin with a harness. It began in a chat box and moved through four phases as the tooling — and the ambition — grew:

- **From 2022** — *Simple prompting.* ChatGPT (Nov 2022) and Claude (Mar 2023) make coding help a single prompt in a chat window: one question, one answer, no memory between them.
- **From ~Aug 2025** — *Agents and skills.* With Claude Code (research preview Feb 2025, general availability May 2025) and Agent Skills (Oct 2025) in hand, experimentation moves from one-shot prompts to agent-driven coding and reusable skills.
- **Late 2025** — *Subagents.* Around Claude Opus 4.5 (Nov 24, 2025), deeper subagent experiments start producing results worth keeping — the output satisfied; the ad-hoc setup around it did not.
- **Early 2026** — *The harness.* To hold that quality bar repeatably while cutting cost, the experiments harden into a harness, driven by three values: insist on the highest standards, invent and simplify, stay frugal. This project captures and documents the result.

<p align="center">
  <img src="docs/images/research-arc.drawio.png" width="820" alt="A schematic slope chart — an overview with directional trends drawn from agent-session logs and project milestones, not to scale — across nine milestones from the project history: Simple prompting (2022), Agents + skills (2025), Subagents (late 2025, the pivot at about one-third from the left), then Specialist pipeline (Mar 2026 launch), JSONL handoff, Harness Stats, Change-grader, Model tiering, and Frugal harness (Jul 2026). A muted note in the pre-pivot region reads 'coding still mostly manual — few tokens per feature.' Quality of output and autonomy hold flat and low through the pivot, rise steeply into the launch, and plateau high afterward, with autonomy ending just above quality. The accent tokens-per-feature line rises into a flat roof at the launch that sits below the quality and autonomy plateau, holds there until the JSONL handoff — the first cost reduction — then steps down in stages across the later cost milestones. A steel-blue harness-maintainability line begins at the launch at about 40 percent height and climbs as a staircase rather than a straight ramp — a small step near the JSONL handoff for the schema-validated log and portable upkeep skills, an observability step at Harness Stats, a step at the change-grader and decision log, the largest step at the mid-June single-source harness API, and a final climb through the July refactor and tested-Python-port cluster — settling just below quality of output and crossing the descending cost line mid-timeline, between Harness Stats and Change-grader. Both axes are directional; the milestones are labelled along the bottom in two staggered rows.">
</p>

> The arc is grounded in observation — the trends are drawn from agent-session logs and the milestones listed below. Read the shapes as directional: they capture how quality, autonomy, cost, and maintainability moved across the project, conveying the trend rather than exact values.

The goal throughout: learn how to build and maintain an effective, efficient harness over the long term — one that produces code to the author's standards, session after session. The thinking was shaped as much by conversations as by tooling — at the [XP × AI Unconference](https://xpunconf.org/) (Berlin, Sep 2025), Devoxx Belgium 2025, and Spring I/O (Barcelona, 2025 and 2026). Chip Huyen's [*AI Engineering*](https://www.oreilly.com/library/view/ai-engineering/9781098166298/) (O'Reilly, 2025) substantially shaped the understanding underneath it. The dated milestones below start where that build began.

### Milestones

- **2026-03-24** — Launch the specialist-agent pattern with Go and Spring Boot reference implementations.
- **2026-04-17** — Add the IDE-compatibility path for JetBrains, Cursor, and Windsurf plugin users.
- **2026-04-21** — Move template upkeep to portable skills: seed, harvest, lint-docs, and dependency upgrades.
- **2026-05-08** — Switch handoff coordination to a schema-validated JSONL append log.
- **2026-05-17** — Add the pipeline quality bar and design-doc autofix.
- **2026-05-22** — Reframe the harness around memory and feedback: the nested-loop model, slice-sizing, and consultation roundtrips.
- **2026-05-22** — Add Harness Stats — the cache-efficiency statusline and per-agent report.
- **2026-05-25** — Add Junie CLI as the fourth supported tool.
- **2026-05-27** — Formalize the dispatch-event contract: dispatch-start records, tool-call budgets, and the six triage verdicts.
- **2026-05-31** — Add the IntelliJ MCP server as a read-only semantic oracle.
- **2026-06-03** — Adopt Anthropic's principles-over-rules model; add the judgment-rationale audit gate.
- **2026-06-04** — Detect dispatch truncation deterministically from filesystem state.
- **2026-06-05** — Add the change-grader: an always-on advisory read of how much review a passing change deserves.
- **2026-06-07** — Establish the root decision log (ADRs) and continue-the-slice truncation recovery.
- **2026-06-10** — Make cap-hit recovery a continuation, gated by a continue-only resume hook.
- **2026-06-11** — Pin models by task tier; add the deterministic handoff-log tool; move seed and harvest to the root.
- **2026-06-12** — Decide the docs-as-API architecture: project-owned briefs behind a versioned contract.
- **2026-06-13** — Land the harness–project API (spec 0.1.0): one stack-agnostic `/harness`, materialized behind a blocking doctor.
- **2026-06-14** — Publish the harness as a plugin marketplace; tag the first release (v0.1.1).
- **2026-06-16** — Make security first-class: secure-by-design as the ninth bar clause and a security-principles brief (v0.1.2).
- **2026-06-17** — Add a generic, technology-free fallback stack via a lifecycle-verb contract (v0.1.3).
- **2026-06-18** — Extend the review gate with an additive reviewer roster over the mandatory four-reviewer floor.
- **2026-06-19** — Reframe the PRD specialist from scribe to discussion partner: asymmetric pushback, feature-derived angles, a human-held veto.
- **2026-06-20** — Pre-approve the handoff append per tool: a Claude Code hook auto-allows the sanctioned log write, with documented setup for Copilot and Junie.
- **2026-06-22** — Extend the JetBrains semantic oracle to the Go stack: GoLand wired as a read-only oracle, matching the Java IntelliJ integration across all four tools.
- **2026-06-22** — Make the PRD and system-design docs digestible: narrative PRD with inline `[REQ-XX-NNN]` tags, a system-design contract table, and doctor-enforced word budgets.
- **2026-06-23** — Trim orchestrator cost without lowering the bar: scope IDE re-reads to out-of-band rewrites, and add a thin-orchestrator economy directive to the rules skeleton.
- **2026-06-23** — Add the materialize reconciliation pass: propose improved orchestrator rules from the skeleton into a project's `CLAUDE.md`, advisory and confirmation-gated.
- **2026-06-24** — Move the generic harness rules into managed `CLAUDE.md` chapters, refreshed on every materialize and doctor-enforced.
- **2026-06-26** — Make the DDD architecture style an open-closed default: one adaptation surface (`architecture-principles.md`) over a closed kernel (v0.1.10).
- **2026-06-27** — Stamp the harness release date into every session: a greppable `CLAUDE.md` line refreshed on materialize and doctor-enforced, raising version attribution from ~3% of transcripts to all.
- **2026-07-01** — Keep template-seeded files current on upgrade: deterministically refresh the `.gitignore` paths and `settings.json` hooks across all three channels, and advisory-propose the rest (`layout.toml`, briefs, non-doctrine `CLAUDE.md` chapters).
- **2026-07-02** — Make the pipeline contracts executable: a dedicated `truncation` tag, pattern-validated dispatch authors, an implementer-run autofix audit, and a single escalations-writer roster with the coordinator's Write grant removed.
- **2026-07-02** — Tier the maintainer workflow: one audit skill with a diff-scoped default and `full` mode; battery-gate the root skill tables.
- **2026-07-03** — Render the per-tool agent mirror bodies from the `.claude` base, cutting every agent-body edit from four copies to one.
- **2026-07-03** — Restructure the docs into a persona-routed set: landing-page README, adoption guide, cross-tool strategy, glossary.
- **2026-07-05** — Split the handoff contract by role (`handoff-append`, `handoff-routing`, `review-workflow`), cutting ~5k preloaded tokens per writer dispatch; deny raw log writes with a committed hook and a gate-run `validate` backstop.
- **2026-07-06** — Make mid-slice routing deterministic: `handoff.py route` executes the Handoff Conditions table with a fail-closed three-way decision, reserving the coordinator for escalations and fresh intake.
- **2026-07-06** — Port the harness tooling from bash to tested Python (hooks, materialize/init, packaging, the tier-0 battery); bash remains only for thin orchestration.
- **2026-07-06** — Add a `handoff.py view` reader that renders a slice as a terminal status board — header, review-convergence matrix, append-ordered timeline — sanitizing agent-authored log content before it reaches the terminal.
- **2026-07-06** — Give the harness audit a security dimension: bandit as tier-0 battery step 1b and a standing Layer 3 security lens, after log-content escape injection reached the terminal unsanitized.
- **2026-07-06** — Make the terminal change-grader pipeline-optional: `layout.toml [harness] auto_grade = false` skips the automatic run, keeping the grader runnable by hand.
- **2026-07-07** — Deduplicate the runtime prose: one canonical statement per contract, and the executable route spec moved out of the loaded skill.
- **2026-07-09** — Make review dispatch risk-proportional: a deterministic `review-plan` sizes each pass's roster to the change (docs-only draws one reviewer), defers ambiguous production changes to a `review-planner`, re-reviews only the fix delta, and fails closed to the full battery.
- **2026-07-10** — Widen the handoff board from one slice to the whole pipeline, surfacing every slice and its fix dispatches by default.
- **2026-07-10** — Add claude-pod: a container-confined Claude Code runner for unattended permission-skipped runs, installed as user-level tooling by a setup skill.
- **2026-07-11** — Trim the fixed context loaded per dispatch: `/next-confirmed` dispatches the requirements expert directly, and the review-planner and stack agents drop always-on preloads for conditional loads.
- **2026-07-11** — Move expert conversations into root: the human talks to the expert role directly; the specialist is dispatched once, with the distilled decisions, to author the artifact.
- **2026-07-11** — Give specialists a durable mid-dispatch escalation to the human: the elicitation pause appends a schema-validated consultation-request targeting the human, replacing a record-less pause indistinguishable from truncation.
- **2026-07-11** — Cut per-dispatch fixed context again: compress the agent-usage doctrine and split the review-workflow skill's tables into a consult-on-demand reference.
- **2026-07-12** — Add the review-harness improvement scan: five research angles judged by a resilience-first doctrine, adversarially verified, dispositions recorded as ADRs.
- **2026-07-12** — Gate hand-owned parallels deterministically: shared skill rosters, a canonical feedback-tag vocabulary, matching severity headings across copies.
- **2026-07-12** — Harden every claude-pod run: all Linux capabilities dropped and setuid escalation blocked, by runtime flags alone.
- **2026-07-13** — Show implement sessions, step durations, and per-step cost on the handoff board, priced from one gated accounting module.
- **2026-07-13** — Decouple project builds from harness self-tests: the runtime is verified once at materialize time.
- **2026-07-13** — Enforce the deterministic battery at push time via a local pre-push hook and server-side CI, with SAST fail-closed under `--strict`.
- **2026-07-14** — Size fix-round review escalation over the fix delta, not the accumulated slice, and make reviewer findings class-exhaustive per round.
- **2026-07-14** — Demote every mechanical gate promise into engines, schemas, and battery steps; prose keeps the why and points at the command.
- **2026-07-15** — Price a handoff-board step by its whole dispatch transcript, so a step's cost stops omitting the dispatch's front and the board can rank its agents.
- **2026-07-15** — Scan continuously beside the deterministic battery rather than inside it, and gate the stdlib-only runtime contract that until now held by discipline.
- **2026-07-16** — Retire the IDE oracle's `build_project`, tighten its policy to read-and-inspect-only, and verify the live exposed tool set on every claude-pod launch against a setting that upgrades can silently widen.
- **2026-07-16** — Bridge the host JetBrains IDE into the pod with `claude-pod --ide`: an in-pod relay makes the host's own MCP config resolve unchanged.
- **2026-07-16** — Give the marketplace channel an upgrade lifecycle: re-run setup after a plugin update, with drift warned and the channel declared.
- **2026-07-17** — Default-deny the pod's host egress with init-container nftables rules; a kernel DNAT bridge replaces the in-pod relay.
- **2026-07-18** — Extend root-applied autofix to the PRD: a `prd-autofix` record resolves doc-only fixes in-round instead of re-flowing the slice.
- **2026-07-18** — Extend the `mypy --strict` gate to the producer-side maintainer tooling, so both sides of the harness are type-checked.
- **2026-07-18** — Preview a materialize run before it writes: a transient `--dry-run` plan over one shared layout reader, surfacing creates, overwrites, and kept extras.
- **2026-07-19** — Encode the challenge posture into review-harness: settled ADR decisions become rebuttable, and a `challenge` arg adds a zero-based mode.
- **2026-07-19** — Confine the harness glue with two battery gates and a write choke-point: no network, writes only to declared roots.
- **2026-07-20** — Harden the pod image supply chain: signed-apt Claude install behind a pinned key fingerprint, non-root default, Debian 13 base.
- **2026-07-29** — Move egress enforcement out of the workload: an internal Docker network and an external proxy replace the in-container packet filter, retiring every privileged capability.
- **2026-07-29** — Default-deny the container's `~/.claude`: enumerated crossings only, a per-project scrubbed `~/.claude.json` replica, and credentials that never touch the host config.
- **2026-07-29** — Rename the tool `claude-dev` and restore Claude Code's in-process sandbox inside it as an inner boundary.
- **2026-07-31** — Default claude-dev to the auto permission mode, keeping skip-permissions as an explicit opt-in.
- **2026-07-31** — Move the specialist roster to the Claude 5 model generation, adding same-tier fallback chains to the Copilot pins.
- **2026-07-31** — Record the localhost egress the native sandbox's local-binding grant opens, as a named residual with an ADR.
- **2026-07-31** — Add `/derive-briefs`: draft a brownfield project's `docs/` briefs from its code, every statement marked derived, confirmed, or not recoverable.
- **2026-07-31** — Wire provenance marks into every brief-editing stage: marks survive edits, and a derived-only brief still reaches a human.
- **2026-08-01** — Unify distribution under one `agent-team` name: the shared skill namespace, the marketplace entries leading with it, and the marketplace registration itself.
- **2026-08-02** — Land the harness eval bench: cost per pass against a fixed SUT per version, machine-verified bar, advisory blind judge.

## Disclaimer

This is a personal learning project. It documents patterns and ideas the author explored while experimenting with AI coding agents.

Use anything here freely under the [MIT License](LICENSE), but at your own risk. Evaluate everything yourself before applying it to your own work.

This project is not affiliated with, endorsed by, or sponsored by Anthropic, GitHub, or any other tool vendor mentioned in this repository. All product names, trademarks, and registered trademarks are the property of their respective owners and are used here solely for identification and descriptive purposes.

## License

[MIT License](LICENSE)
