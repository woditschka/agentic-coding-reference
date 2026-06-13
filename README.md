# Agentic Coding Reference

*Agentic coding that amplifies an engineer's judgment instead of replacing it.*

Ship in days what would otherwise die in triage: work worth trying but not worth weeks, built and tested against real users instead of shelved. The machinery that makes that repeatable — durable specs and nested feedback loops that keep every agent, session, and person pointed the same way — is the substance underneath.

AI coding agents face the same two challenges human engineers always have: keeping **long-term memory** across sessions, and running **multi-scale feedback loops** that catch drift before it compounds. The difference is degree, not kind — a human forgets between Friday and Monday; an agent forgets between one message and the next. Within days, not years, an agentic project that skips the disciplines that compensate starts drifting: terms picked inconsistently session-to-session, settled decisions re-litigated, this week's architecture contradicting last week's.

The fix is to treat the disciplines human teams already built for these problems as the **memory and feedback substrate** — documentation standards, DDD, TDD, ADRs, ubiquitous language, and XP-style nested loops. Every agent, every session, and every person on the codebase reads and writes the same durable specs, so all stay pointed the same direction. A file-based specialist pipeline of nine one-job agents operates it, building one vertical slice at a time, and a single rules file (`CLAUDE.md`) carries it across Claude Code, Copilot CLI, OpenCode, and Junie CLI.

Two working reference implementations (Go, Spring Boot), portable skills, and enforceable documentation standards demonstrate the pattern; a bidirectional `/seed` + `/harvest` loop adopts it in your own project and feeds improvements back.

It is for anyone running an agentic coding workflow over more than a few sessions: a solo developer driving an agent team past what fits in one conversation, a team where each developer drives their own agent team on a shared codebase, or a human-only team that wants the same discipline against the slower drift humans face. The failure modes are the same; only the speed differs.

The architecture, principles docs, and reference implementations are stable and in active use. The specialist pipeline machinery (JSONL contract, four-reviewer fan-out, capability progression) is operational, though its cost-effectiveness is still being measured (with [Harness Stats](#harness-stats)) and will be revised as evidence accumulates. Treat the disciplines as the validated core and the pipeline machinery as one reference implementation of the shape the harness can take.

→ Deep dive: [`agentic-harness.md`](docs/agentic-harness.md) covers the loop model and handoff contract. [`specialist-agent-workflow.md`](docs/specialist-agent-workflow.md) covers the full architecture and migration playbook. the [`document-writing` skill](harness/core/.claude/skills/document-writing/documentation-standards.md) covers the writing rules that keep agents from guessing.

The sections move from **how it works** to **trying it** to **reference** — read top-down, or jump to what you need.

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

The payoff is a build-ship-watch loop measured in days, not weeks — short enough to keep pace with how user needs actually surface. The harness is the fixed cost that makes this repeatable: paid once, it holds every feature to your standards across sessions, so speed never costs direction.

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

→ coordinator routes to change-grader (terminal, advisory)
  └─ reads the diff, writes grader-verdict record (clear | concern) — surfaced to you; nothing auto-merges
→ doc-sync verifies prd.md / system-design.md / ubiquitous-language.md / code have not drifted
```

Each step either updates a durable spec in `docs/` or appends to the per-feature log in `.scratch/` — the project's two memory tiers.

## Memory and Feedback

The substrate has two faces. As **memory**, each durable artifact records a decision so no single session has to hold it. As **feedback**, the same artifacts and the nested loops catch drift while it is still cheap to fix. **Long-term memory** lives in `docs/` — durable specs that evolve across features. **Working memory** lives in `.scratch/` — the per-feature handoff log and implementation plan, cleared after merge.

Each artifact plays a memory role, a feedback role, or both:

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

Feedback runs in four nested loops — the structure XP introduced. Where flight levels are coordination scope, these loops are design scope: what each cycle settles, not who aligns on it. What separates them is the unit each one iterates over and the question it answers:

| Loop | Iterates over | What design question it surfaces |
|---|---|---|
| Inner | one behavior — red → green → refactor | What does this behavior need? (Interface design) |
| Middle | one slice — triage, consultation, and review until all approve | What does this slice deliver? (Acceptance design + system-design adjustments) |
| Outer | the queue of slices | What slice should we build next? (Feature design + slice sizing) |
| Architectural | the whole codebase | Is the whole codebase still well-shaped? (Structural review — planned) |

The design block from the middle-loop triage is a **starting hypothesis**, not a contract. The inner loop is free — and expected — to discover better shape; a consultation-request routes mid-loop discoveries back to the system-design-expert when they are worth crystallizing as long-term memory. Good interfaces and tests fall out of the inner loop; the larger architecture takes shape in the dialogue the outer loops frame.

## The Pipeline

The core pattern is a file-based specialist pipeline. Each agent has one job, reads defined inputs, and writes to known outputs — record producers append to a shared handoff log, the coordinator routes from it. The filesystem is the coordination layer: auditable, interruptible, tool-agnostic.

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
  │
  │  ↻ inner loop — TDD: red → green → refactor; tests accrue as behavioral memory
  │
  │  ↺ middle loop — consultation roundtrip (mid-inner-loop)
  │    ├─ implementer appends consultation-request
  │    ├─ coordinator dispatches system-design-expert in consultation mode
  │    ├─ system-design-expert appends consultation-response (+ memory edits)
  │    └─ coordinator routes control BACK to implementer
  │
  │  ✗ middle loop — build-failure: up to 3 retries → system-design-expert
  │       re-triage; new design-block supersedes prior
  │
  │ (build-pass)
  ▼
4 Reviewers (parallel) ──→ review-feedback records (one per author)
  │
  │  ↺ middle loop — review cycle: any changes_requested / blocked →
  │       owner agent processes findings → re-run quality gate → re-invoke reviewers
  │
  │ (all four approved)
  ▼
Change Grader (terminal, advisory) ──→ grader-verdict record (clear | concern)
  │
  ▼
Human reads the grade and merges — nothing auto-merges
  │
  ╰──↺ outer loop — coordinator selects the next slice, back to the top
```

Inner, middle, and outer are three of the four nested loops described above; an **architectural loop** wraps all three (see [Capability Progression](#capability-progression)).

Each arrow is an append to `.scratch/handoff.jsonl`. The coordinator validates each new record against its per-type JSON Schema in `schemas/scratch/` before routing. A malformed or missing record bounces back to the upstream agent; the next specialist is not dispatched. The coordinator only routes, never implements.

Four living documents are the pipeline's long-term memory, each with a single owner agent that alone writes to it:

| Document | Role | Owner Agent | Describes |
|----------|------|-------------|-----------|
| `docs/prd.md` | Strategic truth | product-requirements-expert | **What** to build — goals, requirements, acceptance criteria, constraints |
| `docs/system-design.md` | Tactical truth | system-design-expert | **How** to build — architecture, invariants, patterns, guardrails |
| `docs/adr/*.md` | Decision records | system-design-expert (architectural ADRs); product-requirements-expert (non-goal ADRs) | **Why** — trade-offs, alternatives considered, what was rejected |
| `docs/ubiquitous-language.md` | Vocabulary truth | product-requirements-expert | **Words** — domain terms, relationships, terms to avoid |

The feature-implementer reads all four but modifies none. The boundary rule is simple: **if it would change when switching languages, it belongs in `system-design.md`, not the PRD.** The PRD uses behavioral language ("the system retries the operation"), never code ("call `Retry()`"). The ubiquitous language updates inline as terms resolve during requirements interviews — drift is challenged mid-conversation, not absorbed silently. See the [`document-writing` skill](harness/core/.claude/skills/document-writing/documentation-standards.md) for the full ownership matrix and cross-reference rules.

The system-design-expert plays the **principal-or-senior-engineer archetype**: the cross-feature mental model stays in its head, and only the load-bearing parts get crystallized into `system-design.md` and `adr/`. It runs in two demand-driven modes — *triage* on every slice (returns one of six verdicts), and *consultation* when the implementer hits a question mid-loop. After a consultation-response, the coordinator routes back to the implementer, not forward to the next pipeline stage.

If the implementer fails the quality gate, it appends a `build-failure` record. The coordinator retries with that error context for up to three attempts, then re-triages with the system-design-expert; the new design-block supersedes the prior one and the retry counter resets.

Agents read these documents before every task and guess when they are vague. So the docs follow enforceable standards: a 30-word sentence cap, one owner per level, tables over prose, parseable templates for PRD entries, ADRs, and state machines. The same rules that make docs clear for agents make them clear for humans. See [prohibited patterns](harness/core/.claude/skills/document-writing/documentation-standards.md#prohibited-patterns) for what not to write.

## Change Grading

After the four reviewers approve, they have answered *is this change correct*. A terminal `change-grader` answers a different question the gate does not: **how much human attention this passing change deserves before it merges.** It reads the actual diff — a deterministic extractor produces a structural row (files, modules, churn, sensitive paths, test/prod ratio, reviewer and retry history) that maps *where to look*, never the verdict — and grades five facets: blast radius, semantic surprise, test adequacy, reviewer hedging, and scope deviation. Each facet definition lives in [`docs/agentic-harness.md`](docs/agentic-harness.md#change-grading-in-depth).

Aggregation is **worst-facet, never average.** Any facet of concern makes the whole change a `concern`; all clear makes it `clear`. The grade is **advisory-only**: nothing routes on the verdict, nothing auto-merges — a human always makes the merge click. The point is to concentrate scarce review on the changes where judgment pays off and let the obvious-safe ones move fast, without ever rubber-stamping a clean-looking row unread.

The grader returns a rendered report — the surface a human reads at the merge point. The verdict leads (a reader can stop there); the facet sections are the evidence. One `Concern` facet flips the whole grade:

```markdown
# Change Grade — REQ-014: tighten retry-counter reset

## Verdict — Concern: semantic surprise
Reset now fires on partial-build failures too, not just clean ones — ...
_Advisory only; nothing auto-merges._

Extracted: 2 files, internal/pipeline · +31/−4 · no sensitive paths · build ✓ · 4/4 approved · 0 retries

## Blast Radius — Clear
Contained to one module; no public API ...

## Semantic Surprise — Concern
Counter reset widened to the partial-failure ...

## Test Adequacy — Clear
New test exercises the partial-failure ...

## Reviewer Hedging — Clear
Four clean approvals, no ...

## Scope Deviation — Clear
Matches the prd-entry slice ...
```

## Tool-Use Limits and Continuation

Each agent dispatch runs under a tool-call cap, and the SDK truncates a dispatch that reaches it. Two mechanisms keep long dispatches recoverable.

**Before** the dispatch, a Scoping Pre-Check runs two independent checks. **Scope** asks whether the work spans more than one behavior — answered from the inbound records, not the budget; a multi-behavior slice bounces back to re-scope. **Length** lets a single-behavior dispatch that simply runs long proceed, naming a checkpoint where it hands off a partial-artifact record.

**After** a truncation, recovery **continues the same slice.** A fresh re-dispatch reads the working tree and the partial-artifact record and picks up where it stopped, rather than re-splitting. Re-split is reserved for genuine over-scope, and repeated non-convergence escalates to a design re-triage. So a dispatch that hits the ceiling loses little work and resumes deterministically, instead of restarting from scratch.

In Claude Code, the continuation can resume the *same* sub-agent in place instead of re-dispatching. The samples enable the experimental agent-teams capability for this (set in `.claude/settings.json`), then constrain the resume channel with a `PreToolUse` hook that accepts only the literal `continue` (`.claude/hooks/sendmessage-continue-only.sh`). The reason is the auditable-ledger invariant: a resume must never smuggle new, unrouted instructions — all new work goes through a fresh, schema-validated dispatch on the handoff log. The hook fails closed, so a non-`continue` resume is denied, never silently accepted.

## Model Tier Assignment

Each specialist's model is pinned in its agent definition. The split follows task type, under a fixed objective ordering: quality bar first, cost second, wall-clock time third.

| Tier | Agents |
|------|--------|
| Opus 4.8 | product-requirements-expert, system-design-expert, feature-implementer, security-reviewer, change-grader |
| Sonnet 4.6 | pipeline-coordinator, code-quality-reviewer, test-reviewer, doc-reviewer |

Judgment roles get the premium tier. Requirements framing, architecture triage, TDD implementation, off-checklist vulnerability hunting, and the terminal merge-attention grade are open-ended reasoning; their errors compound downstream.

Checklist and routing roles sit one tier below. Verifying a diff against an explicit rubric is an easier task than generating the code. The quality gate (build, test, lint) runs as a mechanical correctness oracle before any reviewer. The coordinator routes against JSON Schemas, so a misroute costs a re-triage hop, not a shipped defect. At $3/$15 per million tokens against Opus at $5/$25, the mixed reviewer fan-out costs 70% of a uniform-Opus one.

Two rules keep the split stable across model releases. Judgment reviewers (security-reviewer, change-grader) move with the implementer's tier — never below it. The test-reviewer is the watch item: a defect that escapes an approved test review promotes it to the judgment tier.

Models are pinned to explicit versions, not aliases, so a release never shifts pipeline behavior silently; bumps happen through a deliberate `deps-upgrade` run. Rationale and rejected alternatives: [`docs/adr/2026-06-11-model-tier-assignment.md`](docs/adr/2026-06-11-model-tier-assignment.md).

## Quick Start

### Try a reference implementation

```bash
# Go
cd samples/go/
make ci                      # tidy, fmt, vet, lint, deps-check, test, build

# Java Spring Boot
cd samples/java-spring-boot/
./gradlew build              # compile, format check, test, package
```

### Use with an agent tool

Open either project directory. Configuration loads automatically.

```bash
cd samples/go/          # or cd samples/java-spring-boot/
claude          # Claude Code
copilot         # Copilot CLI
opencode        # OpenCode
junie           # Junie CLI
```

## Adopt in Your Own Project

The monorepo root ships two skills that form a bidirectional loop between this reference and real projects. Both run from the root in Claude Code and select the matching sample for existing targets: `go.mod` picks the Go template, `pom.xml` or `build.gradle` picks the Spring Boot template. An empty init target is asked for its stack. `/seed` works in two modes. **Init** runs on an empty target to scaffold a new project. **Upgrade** runs on an existing project to pull in template improvements without overwriting domain work. `/harvest` runs in the opposite direction, pulling generalizable improvements from your project back into the templates — language-agnostic findings land in both samples.

| Command | Direction | What it does |
|---------|-----------|--------------|
| `/seed <project-path>` | Reference → your project | **Init mode** (fresh target): copy agents, skills, and doc scaffolding; fill `{{PROJECT_NAME}}` and `{{PROJECT_DESCRIPTION}}`. **Upgrade mode** (existing target): section-level merge that pushes template improvements while preserving domain customizations — filled Security Context, real `REQ-*` IDs, real file paths. |
| `/harvest <project-path>` | Your project → reference | Diff a real project against the matching sample. Classify each change as **harvest** (generic improvement), **skip** (domain-specific), or **ask** (ambiguous). Auto-generalize domain patterns on the way back (`REQ-DL-*` → `REQ-XX-*`, `internal/render/render.go` → `internal/example/handler.go`); route language-agnostic improvements to both samples. |

### Examples

Both skills run inside Claude Code, from the monorepo root, via `/skill-name <args>`.

```bash
$ cd agentic-coding-reference
$ claude

# Init — scaffold a new project (empty target; asks go | java, and for java gradle | maven)
> /seed ../my-service                # prompts for name + description

# Upgrade — raise the bar on an existing project (auto-detects stack, name,
# description, and build tool from the target; no prompts if already filled)
> /seed ../my-existing-service

# Harvest — pull improvements from your project back into the reference
> /harvest ../my-existing-service
```

`/seed` supports Maven targets in both modes. In init mode, picking `maven` at the prompt generates an idiomatic `pom.xml` via [start.spring.io](https://start.spring.io) and writes Maven equivalents to `CLAUDE.md` Build Commands and `settings.local.json` permissions. In upgrade mode, seed auto-detects `pom.xml` and translates template pushes to Maven commands.

Improvements discovered while shipping real features flow back into the template. Template improvements flow out to every downstream project. Neither direction overwrites domain work.

## The Harness–Project Contract

The dependency runs both ways. Agents enforce a project's briefs as their own convictions, so a vague or self-contradicting brief degrades every dispatch that reads it. The project, in turn, accumulates truth no upgrade may clobber: requirements, decisions, policies. The boundary that protects both is a versioned API — [`harness-project-api.md`](docs/harness-project-api.md), spec 0.1.0 — not a convention. Why an API rather than shared documents: [the docs-as-API ADR](docs/adr/2026-06-12-docs-as-harness-project-api.md).

A project owns six briefs under `docs/`: `prd.md`, `system-design.md`, `adr/`, `ubiquitous-language.md`, `testing-principles.md`, and `architecture-principles.md`. The first four arrive as structure only — the requirements, design, decisions, and vocabulary are yours; the harness ships no opinion on them. The last two arrive filled with the harness's house policy — pyramid ratios, mocking rules, module discipline — as a working default. Rewrite them to your team's values; a rewritten default is policy, not drift. The harness materializes a missing brief from its template and never writes an existing one. Upgrades replace only the runtime: skills, agents, hooks, schemas, scripts.

Underneath the briefs, four disciplines are kernel — fixed because the machinery breaks without them:

| Kernel discipline | What is fixed | What stays project-owned |
|---|---|---|
| **TDD-first** | A failing test precedes production code; the eight-clause quality bar | Pyramid ratios, coverage target, mocking policy, test-naming style |
| **Strategic DDD** | Four properties: ubiquitous language, bounded modules, an isolated unit-testable domain core, the state-vs-history split (design docs carry what is, ADRs carry why) | The tactical pattern catalog realizing them — repositories, mappers, naming rules |
| **Spec-driven delivery** | PRD before design before code; the append-only handoff ledger and its record, tag, and verdict vocabularies | All content: requirements, design, decisions |
| **Form contract** | Principles over rules; 30-word sentences; data over adjectives | The content the form carries |

The admission test: a discipline enters the kernel only when the machinery breaks without it, never because we like it. The kernel closes *properties*; briefs carry *patterns*. A team can reject the word "repository" — it cannot reject "the domain core is testable without infrastructure."

Enforcement follows the same ownership split. The `doctor` skill is deterministic and blocking: all six briefs present, required sections and numeric slots filled — 29 checks in stdlib Python, CI-runnable. It verifies structure, never your choices. `brief-review` is judgment and advisory: it asks whether your principles are enforceable, contradiction-free, and carry their rationale. It can question a policy; it cannot override one. It is also how harness evolution reaches a project-owned file: a new expectation arrives as a finding with an offered draft, applied only on your consent — never as a write.

Facts enforced by judgment live in briefs; facts consumed by deterministic engines live in `scripts/layout.toml` — test file globs, the test-name regex, the channel declaration. Each skill declares the briefs it reads in frontmatter; the doctor audits those declarations against the expectations manifest.

The contract holds on every distribution channel. **Copy** commits the runtime into the project. **Manifest** materializes the runtime from a pinned source — the `/harness` tree — into the project's native tool locations, gitignored and doctor-enforced untracked; this is the mode both samples use, with `/init` (or `/seed`) to onboard, `materialize` to upgrade, and `/harvest` to push improvements back to the source. **Marketplace** ships it as a plugin (planned). The project-owned files stay committed on all three; only the delivery of the runtime differs. Both samples are consumers of their own harness and pass their own doctor.

## Reference Documentation

The [`docs/`](docs/) directory is the harness's own documentation, grouped by role below — all read-only reference: the contract, how the machinery works, and why each kernel discipline is fixed. The default briefs a project receives (testing and architecture) ship as doctor templates in the harness, not as files here; the kernel rationale behind them lives in `tdd-principles.md` and `ddd-principles.md` below.

| Document | Role | Covers |
|----------|------|--------|
| [`harness-project-api.md`](docs/harness-project-api.md) | Contract | The harness–project API: six-file brief roster, required sections, validation contract (spec 0.1.0) |
| [`agentic-harness.md`](docs/agentic-harness.md) | Internals | The four-loop model, slice definition, agent roster, handoff contract, triage and consultation modes |
| [`specialist-agent-workflow.md`](docs/specialist-agent-workflow.md) | Internals | Pipeline architecture, cross-tool compatibility, capability progression, migration playbook |
| [`document-writing` skill](harness/core/.claude/skills/document-writing/documentation-standards.md) | Internals | Writing for agents, document ownership, validation checklist |
| [`adr/`](docs/adr/) | Internals | Decision log — why the harness evolved (options, trade-offs); the *why* behind the Project History timeline |
| [`tdd-principles.md`](harness/core/.claude/skills/tdd-workflow/tdd-principles.md) | Kernel rationale | TDD as design discovery via the inner loop (XP-rooted), eight-clause conjunctive bar |
| [`ddd-principles.md`](docs/ddd-principles.md) | Kernel rationale | Strategic DDD: the four kernel properties and why tactical patterns are brief-variable |

## Reference Implementations

Go and Spring Boot represent different paradigms — explicit vs convention-driven. When a pattern works in both, it transfers. When they diverge, the differences are instructive.

| | Go ([`samples/go/`](samples/go/)) | Java Spring Boot ([`samples/java-spring-boot/`](samples/java-spring-boot/)) |
|---|---|---|
| **Toolchain** | Go 1.26, golangci-lint, Make | Java 25, Gradle 9.5.1, Spring Boot 4.1.0 |
| **Agents** | 9 specialists across 4 tools | 9 specialists across 4 tools |
| **Skills** | 19 portable skills | 21 portable skills (incl. 2 IntelliJ oracle skills) |
| **Entry point** | [`samples/go/CLAUDE.md`](samples/go/CLAUDE.md) | [`samples/java-spring-boot/CLAUDE.md`](samples/java-spring-boot/CLAUDE.md) |

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

For JetBrains, Cursor, or Windsurf plugin users, see [IDE Compatibility](docs/specialist-agent-workflow.md#3-ide-compatibility) for the symlink-based extension path. That section also covers using IntelliJ IDEA's MCP server as a read-only semantic oracle and verifier. It is optional and demonstrated in the Java Spring Boot sample ([setup and rationale](samples/java-spring-boot/.claude/skills/intellij-idea/intellij-mcp-integration.md)): wired and working for Claude Code, and wired for Copilot CLI ahead of an upstream fix.

## Capability Progression

The harness grew from a single prompt by adding one capability at a time, each closing a specific failure of the one before it. Add a capability when you hit the failure it closes — not before. The far end is this reference's demonstration, not a target; measure with Harness Stats before adding any layer.

- **Single generalist prompt:** One model, one context, no persistence. Nothing survives between messages; every session restarts from zero. The baseline the others improve on.
- **Rules file (`CLAUDE.md`):** The first long-term memory. Conventions, build commands, and workflow persist across sessions, so the agent stops re-deriving the project's basics every time it starts.
- **Skills:** Reusable, invokable workflow knowledge. Procedures the agent would otherwise improvise — auditing, reviewing, releasing — become named, repeatable operations shared across every tool.
- **Specialist subagents:** One job each, in isolated contexts. A requirements agent, a design agent, an implementer — so no single context carries every concern and drifts under the load.
- **Coordinated routing:** A coordinator reads the handoff log, validates each record, and routes to the next specialist. Working memory becomes auditable and interruptible — the point where the pipeline coordinates itself.
- **Parallel review fan-out:** Four reviewers run concurrently against one diff — security, quality, tests, docs — trading more review-phase tokens for faster, wider feedback before a feature lands.

Around this runs a slower **architectural loop** — periodic drift review that writes back to long-term memory. Today it reviews the reference itself (cross-project consistency, docs, agent parity, upstream changes, versions); pointing it at application-code structural decay is the open extension. See [§4 of the workflow doc](docs/specialist-agent-workflow.md#4-capability-progression) for the full path and the frontier beyond it.

## Pipeline Maintenance

One pattern keeps the pipeline healthy between features:

| Pattern | Purpose |
|---------|---------|
| `doc-sync` | Detect and fix drift between `docs/prd.md`, `docs/system-design.md`, `docs/ubiquitous-language.md`, and the codebase after features merge. |

See [§7 of the workflow doc](docs/specialist-agent-workflow.md#7-pipeline-maintenance-patterns) for the full process.

## Reference Upkeep

Five root-level skills keep this reference itself consistent (the `seed`/`harvest` template skills are covered in [Adopt in Your Own Project](#adopt-in-your-own-project)):

| Skill | Purpose |
|-------|---------|
| `research-update` | Fetch upstream tool docs, compare claims against current state, report drift. |
| `audit-consistency` | Verify both implementations match root docs and each other. |
| `deps-upgrade` | Check pinned tool/plugin/dependency versions against upstream, bump and verify. |
| `harness-stats-setup` | Install or update the user-level statusline and cache-report tooling from `tools/harness-stats/` into `~/.claude/`. |
| `history-update` | Refresh the Project History section in the README with executive-level milestones since the last entry. |

## IntelliJ Semantic Oracle

Optional tooling that connects IntelliJ IDEA's MCP server to the agent as a **read-only semantic oracle and verifier**. The motivation is grounding. An agent reasons over text, so it answers semantic questions from its priors — plausible guesses that need not match this codebase. *What does this name resolve to? Where is it really used? Does this Spring bean wire up? Does the edit compile?* The oracle replaces the guess with the IDE's computed answer.

What the agent gains, ordered by how firmly each holds:

| Gain | What it means |
|------|---------------|
| **Grounded information** | Answers come from the IDE's resolved model of *this* project: inferred types, semantic usages, the compiler's verdict, framework-aware inspections (Spring wiring, JPA, nullability), and the resolved transitive dependency graph. None of this is readable off disk — a text-only agent would have to simulate the compiler and type-checker. The agent acts on facts, not priors. |
| **Determinism** | The same code yields the same answer — a lookup, not a probabilistic judgment. |
| **Fewer detours** | A compact resolved answer can spare the agent from reading and reasoning across multiple files to reconstruct the same fact. |

The server is read-only by policy: no exposed tool mutates a file. The agent stays the sole writer, so the oracle adds a verification signal without a new failure mode. It is optional and degrades cleanly. When the IDE is absent or its index is stale, every workflow falls back to native tools plus the project build — the canonical gate. The grounding is only as fresh as the IDE's index, so a one-command health check (`intellij-idea-doctor`) guards against trusting a stale model.

Today the oracle is wired and working for Claude Code and wired for Copilot CLI (gated by an upstream bug). Junie CLI runs in headless mode on the native baseline; OpenCode is the next wiring target. The oracle is demonstrated in the Java Spring Boot sample; the Go sample is not wired. See [`samples/java-spring-boot/.claude/skills/intellij-idea/intellij-mcp-integration.md`](samples/java-spring-boot/.claude/skills/intellij-idea/intellij-mcp-integration.md) for the exposed tool set, the exposure policy, setup, and per-client status.

**Consider it if** your agents work in an IDE-backed language and you want a grounded, deterministic check in the loop. The pattern transfers to any editor exposing an MCP server; the Java sample is one instance.

## Harness Stats

Running a constellation of specialists has a cost the chat UI does not surface. How many tokens are flowing? Is the prompt cache amortizing the repeated specialist fires? Which subagent is about to hit its tool ceiling and truncate? Harness Stats makes it visible — a live statusline on every turn and an on-demand per-agent report. This is the feedback loop turned on the harness itself: the instrument for the cost-effectiveness question raised up front.

A statusline mid-fan-out, with agent teams enabled (project shown as `sample`):

```text
sample ⎇ main │ opus ▤ 47% │ Σ ▲4.2M ▼91k $11.40 │ ⛁ 95% ⊖3.9M ⊕210k $84% │ ⇲ 12 context7·8 │ ⇉ 3 │ ⟳ 9 │ ↺ doc-reviewer ⊕9k ⚒18 ⟳2 │ ↗ feature-implementer ⚒54 ⟳7
```

Read left to right:

- Project directory and git branch.
- Parent model and context-window usage (`▤`), color-coded as it fills.
- Session totals (`Σ`) — input (`▲`), output (`▼`), and list-price API cost (`$`), summed across the parent and every subagent.
- Cache (`⛁`) — hit rate, tokens read (`⊖`) versus written (`⊕`), and spend change versus uncached (`$%`).
- MCP usage (`⇲`) — total calls and the busiest server, shown only when the session calls MCP.
- Parallel fan-out (`⇉`) — distinct subagent types active in the last 5 minutes.
- Continuation total (`⟳`) — session-wide accepted re-engagements, shown only when agent teams is on.
- Last turn (`↺`) and any at-risk hot agent (`↗`) — agent name, cache writes (`⊕`), cumulative tool count (`⚒`), and continues (`⟳`) when agent teams re-engages it.

A subagent nearing the SDK's per-invocation tool ceiling turns its `⚒` count yellow then red, with a `⚠` when it hits — unless agent teams is actively re-engaging it (`⟳`), in which case the count is coordinator-driven and the alarm is suppressed. The on-demand `cache-report` breaks the same figures down per agent — runs, warm-start %, net savings % — exposing which specialists pay for their cache writes and which fire too sporadically to amortize.

| Skill | Purpose |
|-------|---------|
| `harness-stats-setup` | Install or update the tooling. Detects drift between this repo and `~/.claude/`, applies on approval, merges the `statusLine` block into `~/.claude/settings.json` without clobbering other keys. |
| `cache-report` | Run the per-agent report on demand (installed by the setup skill). |

See [`tools/harness-stats/README.md`](tools/harness-stats/README.md) for the full cell reference, metric formulas, and platform support.

## Repository Structure

```text
.
├── docs/                              # Cross-cutting principles + decision log (adr/)
├── harness/                           # Single canonical harness source — samples materialize from here
│   ├── core/                          # Runtime shared by every stack
│   ├── stacks/<stack>/                # Stack-specific runtime (go, java-spring-boot)
│   ├── init/                          # Skeletons for the files a project owns (not runtime)
│   ├── materialize.sh                 # Install the runtime into a target
│   ├── init.sh                        # Scaffold the project-owned files
│   └── bootstrap.sh                   # Detect each target's stack, then materialize
├── samples/                           # Materialized instances of the harness (manifest channel)
│   ├── go/                            # Go reference implementation
│   │   ├── CLAUDE.md                  # Project rules — committed (all 4 tools read this)
│   │   ├── docs/                      # Project briefs — committed, project-owned
│   │   ├── scripts/layout.toml        # Channel + module rules — committed
│   │   └── .claude/ .github/ .opencode/ .junie/   # Runtime — materialized from /harness, gitignored
│   └── java-spring-boot/              # Spring Boot reference implementation (same shape as go/)
├── tools/                             # Optional companion tooling
│   └── harness-stats/                 # Cache-efficiency statusline + report
├── .claude/skills/                    # Root maintenance skills (init, seed, harvest, audit-consistency, …)
└── CLAUDE.md                          # Monorepo instructions
```

## Project History

- **2026-03-24** — Launch specialist agent pattern with Go and Spring Boot reference implementations.
- **2026-04 → 2026-05** — Build out template upkeep: maturity levels, bidirectional `/seed` + `/harvest` template sync, pipeline quality bar, design-doc autofix, statusline and cache diagnostics, doc-conformance audits.
- **2026-04-17 → 2026-05-25** — Codify cross-tool compatibility; grow the samples to four supported tools (Claude Code, Copilot CLI, OpenCode, Junie CLI); keep root maintenance Claude Code-only.
- **2026-05-08** — Switch handoff coordination to schema-validated JSONL append log.
- **2026-05-22** — Reframe harness around memory and feedback; add four-loop model, consultation roundtrips, cache tooling.
- **2026-05-27** — Bound dispatches with budgets and start/stop events; add refactor-first verdict, harness invariants, per-tool `/seed` selection.
- **2026-05-31** — Add IntelliJ MCP integration as a read-only semantic oracle and verifier.
- **2026-06-03** — Adopt Anthropic's principles-over-rules model; enrich agent personas and add the judgment-rationale audit gate.
- **2026-06-07** — Add change-grader advisory grade; recover truncation by continuing the slice, with hook-gated in-place agent resume.
- **2026-06-10** — Codify cap-hit recovery as continuation: decouple slice size from dispatch budget, continue-only resume.
- **2026-06-11** — Pin model tiers by task type: judgment roles premium, checklist roles mid-tier, quality-first ordering.
- **2026-06-11** — Add deterministic handoff-log tool; unify `/seed` + `/harvest` at the root with stack auto-detection.
- **2026-06-11** — Tier project history by recency: detail up front, era rollups behind, landmarks survive.
- **2026-06-12** — Decide docs-as-API architecture: project-owned briefs, expectation-spec contract, dual-channel plugin distribution.
- **2026-06-13** — Land the harness-project API: spec 0.1.0, doctor + brief-review validators, project-owned briefs; both samples pass their own doctor.
- **2026-06-13** — Make `/harness` the single source via the manifest channel: runtime materialized from a canonical `core/` plus per-stack tree, gitignored and doctor-enforced untracked; both samples cross to manifest.
- **2026-06-13** — Split onboarding into `init` (project-owned scaffolding) and `materialize` (runtime), reducing `/seed` to a wrapper; support copy→manifest migration of existing projects.
- **2026-06-13** — Begin de-stackify: lift language tokens into project data and briefs so universal agents and skills collapse into one stack-agnostic `core/`. The IntelliJ-coupled surface and language-substance review skills stay per-stack, pending an optional-capability system.
- **2026-06-13** — Unify documentation discipline in the `document-writing` skill (renamed from `doc-review`): authors follow it, the reviewer enforces it. Collapse the root `documentation-standards.md` handbook into it so the full standard ships installed, single-sourced, with ownership detail delegated to each governing skill.

## Disclaimer

This is a personal learning project. It documents patterns and ideas the author explored while experimenting with AI coding agents.

Use anything here freely under the [MIT License](LICENSE), but at your own risk. Evaluate everything yourself before applying it to your own work.

This project is not affiliated with, endorsed by, or sponsored by Anthropic, GitHub, or any other tool vendor mentioned in this repository. All product names, trademarks, and registered trademarks are the property of their respective owners and are used here solely for identification and descriptive purposes.

## License

[MIT License](LICENSE)
