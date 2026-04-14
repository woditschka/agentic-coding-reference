# Agentic Coding Reference

Patterns for structuring projects so AI coding agents can collaborate on multi-step feature development. Demonstrated through working configurations in Go and Java Spring Boot.

This is ongoing research into the transition to agentic programming. The tooling evolves weekly, and these patterns evolve with it.

## Agent Pipeline

The core pattern is a file-based specialist pipeline. Each agent has one job, reads defined inputs, and writes to known outputs. The filesystem is the coordination layer — auditable, interruptible, tool-agnostic.

```
User Request
  │
  ▼
Pipeline Coordinator ─── reads .scratch/ state, routes to next agent
  │
  ▼
Product Requirements Expert ──→ .scratch/current-feature.md
  │
  ▼
System Design Expert ──→ .scratch/design-notes.md
  │
  ▼
Feature Implementer ──→ quality gate (build, test, lint)
  │                       │
  │ (passes)              │ (fails, up to 3 retries → escalate to design expert)
  ▼                       │
4 Reviewers (parallel) ──→ .scratch/reviews/*.md
  │
  ▼
Evaluation ──→ .scratch/eval-<feature>.md
```

Each arrow is a file write. The coordinator reads `.scratch/` state and routes to the correct specialist — it only routes, never implements. If the implementer fails the quality gate, the coordinator retries with error context (up to 3 attempts), then escalates to the design expert for revision.

The pipeline includes 8 specialist agents, 15 portable skills, and configurations for three tools (Claude Code, OpenCode, GitHub Copilot) sharing one rules file.

## Spec-Driven Development

The pipeline is driven by two living documents that agents treat as authoritative sources:

| Document | Role | Owner Agent | Describes |
|----------|------|-------------|-----------|
| `docs/prd.md` | Strategic truth | product-requirements-expert | **What** to build — goals, requirements, acceptance criteria, constraints |
| `docs/system-design.md` | Tactical truth | system-design-expert | **How** to build — architecture, patterns, types, guardrails |
| `docs/adr/*.md` | Decision records | system-design-expert | **Why** — trade-offs, alternatives considered, rationale |

Each document has a single owner agent. Only the owner writes to it. The feature-implementer reads all three but modifies none — when it encounters a requirement gap or design conflict, it routes back to the owning agent instead of guessing.

The boundary rule is simple: **if it would change when switching languages, it belongs in system-design.md, not the PRD.** The PRD uses behavioral language ("the system retries the operation"), never code ("call `Retry()`"). System-design.md describes contracts and structure, never duplicates runnable source code. See [`documentation-standards.md`](docs/documentation-standards.md) for the full ownership matrix and cross-reference rules.

## Writing for Agents and Humans

Agents read documentation before every task, and humans read it before every review. Vague prose and ambiguous boundaries degrade both — but agents degrade faster, because they do not ask for clarification when confused. They guess. The same rules that make docs clear for agents make them clear for humans.

The [documentation standards](docs/documentation-standards.md) turn this into enforceable rules:

| Area | Rule |
|------|------|
| **Writing** | Maximum 30 words per sentence. Replace adjectives with data. Prohibited-words list blocks claims without supporting measurements. |
| **Abstraction** | Four document levels — Meta (`CLAUDE.md`), Strategic (`prd.md`), Decision (`adr/`), Tactical (`system-design.md`). One owner per level, no overlap. |
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
opencode        # OpenCode
copilot         # Copilot CLI
```

## Adopt in Your Own Project

Each implementation ships two slash commands that form a bidirectional loop between this reference and real projects:

| Command | Direction | What it does |
|---------|-----------|--------------|
| `/seed <project-path>` | Reference → your project | **Init mode** (fresh target): copy agents, skills, commands, and doc scaffolding; fill `{{PROJECT_NAME}}` and `{{PROJECT_DESCRIPTION}}`. **Upgrade mode** (existing target): section-level merge that pushes template improvements while preserving domain customizations — filled Security Context, real `REQ-*` IDs, real file paths. |
| `/harvest <project-path>` | Your project → reference | Diff a real project against the template. Classify each change as **harvest** (generic improvement), **skip** (domain-specific), or **ask** (ambiguous). Auto-generalize domain patterns on the way back (`REQ-DL-*` → `REQ-XX-*`, `internal/render/render.go` → `internal/example/handler.go`). |

Improvements discovered while shipping real features flow back into the template. Template improvements flow out to every downstream project. Neither direction overwrites domain work.

## Principles

The [`docs/`](docs/) directory contains cross-cutting principles that apply to both implementations. Start with [`specialist-agent-workflow.md`](docs/specialist-agent-workflow.md) — it covers the full architecture, cross-tool strategy, and a phased migration playbook.

| Document | Covers |
|----------|--------|
| [`specialist-agent-workflow.md`](docs/specialist-agent-workflow.md) | Pipeline architecture, cross-tool compatibility, maturity levels, migration playbook |
| [`documentation-standards.md`](docs/documentation-standards.md) | Writing for agents, document ownership, validation checklist |
| [`testing-principles.md`](docs/testing-principles.md) | Test pyramid, no-mock policy, four-phase structure |
| [`tdd-principles.md`](docs/tdd-principles.md) | Red-Green-Refactor with design gates |
| [`ddd-principles.md`](docs/ddd-principles.md) | Modulith architecture, domain types, aggregate structure, naming conventions |

## Reference Implementations

Go and Spring Boot represent different paradigms — explicit vs convention-driven. When a pattern works in both, it transfers. When they diverge, the differences are instructive.

| | Go ([`go/`](go/)) | Java Spring Boot ([`java-spring-boot/`](java-spring-boot/)) |
|---|---|---|
| **Toolchain** | Go 1.26, golangci-lint, Make | Java 25, Gradle 9.4.1, Spring Boot 4.0.4 |
| **Agents** | 8 specialists across 3 tools | 8 specialists across 3 tools |
| **Skills** | 15 portable skills | 15 portable skills |
| **Entry point** | [`go/CLAUDE.md`](go/CLAUDE.md) | [`java-spring-boot/CLAUDE.md`](java-spring-boot/CLAUDE.md) |

Each implementation is self-contained. The project `CLAUDE.md` is the authoritative source for build commands, conventions, and agent workflow within that directory.

## Cross-Tool Compatibility

All three major AI coding tools read `CLAUDE.md` natively. Skills in `.claude/skills/` are discovered by all three. Agent definitions are the exception — YAML frontmatter differs per tool, so each tool gets its own agent directory.

| Location | Claude Code | OpenCode | Copilot CLI |
|----------|:-----------:|:--------:|:-----------:|
| `CLAUDE.md` | Yes | Yes (fallback) | Yes (native) |
| `.claude/skills/*/SKILL.md` | Yes | Yes | Yes |
| `.claude/agents/*.md` | Yes | — | — |
| `.opencode/agents/*.md` | — | Yes | — |
| `.github/agents/*.agent.md` | — | — | Yes |

Creating `AGENTS.md` breaks OpenCode's fallback to `CLAUDE.md`. Creating `copilot-instructions.md` causes additive merging. One rules file avoids both problems.

## Design Decisions

**Specs before code, always.** Every feature starts with a PRD requirement and a design review. The implementer never writes code without reading `.scratch/current-feature.md` (what to build) and `.scratch/design-notes.md` (how it fits). When the TDD cycle uncovers a requirement gap, the implementer stops and invokes the owning agent — it does not fill in blanks. This makes the specs the single source of truth, not the code.

**Specialist agents over generalist sessions.** A single session mixing requirements analysis with code generation dilutes both. Separate agents with focused context windows produce more consistent output. The trade-off is coordination overhead, which the file-based pipeline handles.

**File-based coordination over message passing.** Agents write handoff files to `.scratch/`. Files survive session crashes, work with any tool, and are inspectable with `cat`. Agent Teams (Claude Code's experimental multi-session feature) enables direct inter-agent communication but is less portable today. Tracked at maturity Level 4 in the workflow doc.

**Skills for portability, agents for tool-specific config.** Workflow logic in `.claude/skills/` works across all three tools. Agent definitions are thin wrappers: persona, tool permissions, model choice. Updating a review checklist is one edit in one skill, not six edits across three tool directories.

**Build-time dependency enforcement.** The Go implementation includes `make deps-check`, which fails the build if `go.mod` contains a prohibited module. This complements the documented dependency policy with automated enforcement.

## Maturity Levels

The pipeline is an adoption ladder, not a fixed architecture. Pick the level that matches your team's throughput. Level 2 is the recommended steady state. Status: Production-ready (1–3), Experimental (4), Speculative (5).

| Level | Name | Status | What changes |
|:-:|------|--------|--------------|
| 1 | Manual Pipeline | Production | Human invokes each specialist agent by hand. Validates the pattern. |
| 2 | Coordinator + Automated Routing | Production | A coordinator agent reads `.scratch/` state and routes to the next specialist. |
| 3 | Parallel Reviewers | Production | Four reviewers run as parallel subagents. Sub-5-minute review cycles. |
| 4 | Agent Teams Collaborative Review | Experimental | Reviewers communicate directly. Requires Claude Code v2.1.32+, Opus 4.6, opt-in flag. |
| 5 | Full Team Orchestration | Speculative | Coordinator-as-team-lead for the entire pipeline. Blocked on tooling maturity. |

See [§3 of the workflow doc](docs/specialist-agent-workflow.md#3-maturity-progression) for when to use each level, when to move on, and the tradeoffs.

## Pipeline Maintenance

Two patterns keep the pipeline healthy between features:

| Pattern | Purpose |
|---------|---------|
| `doc-sync` | Detect and fix drift between `docs/prd.md`, `docs/system-design.md`, and the codebase after features merge. |
| `feature-eval` | Scorecard written after each feature. PASS/FAIL verdict plus retry-cost assessment. Creates an audit trail that surfaces systemic issues — repeated build failures point to design problems; repeated review cycles point to unclear requirements. |

See [§6 of the workflow doc](docs/specialist-agent-workflow.md#6-pipeline-maintenance-patterns) for the full process.

## Reference Upkeep

Two root-level skills keep this reference itself consistent:

| Skill | Purpose |
|-------|---------|
| `research-update` | Fetch upstream tool docs, compare claims against current state, report drift. |
| `audit-consistency` | Verify both implementations match root docs and each other. |

## Repository Structure

```
.
├── docs/                              # Cross-cutting principles
├── go/                                # Go reference implementation
│   ├── CLAUDE.md                      # Project rules (all 3 tools read this)
│   ├── .claude/agents/                # 8 Claude Code agents
│   ├── .claude/skills/                # 15 portable skills
│   ├── .opencode/agents/              # 8 OpenCode agents
│   └── .github/agents/                # 8 Copilot agents
├── java-spring-boot/                  # Spring Boot reference implementation
│   ├── CLAUDE.md
│   ├── .claude/agents/
│   ├── .claude/skills/
│   ├── .opencode/agents/
│   └── .github/agents/
├── .claude/skills/                    # Root-level maintenance skills
└── CLAUDE.md                          # Monorepo instructions
```

## Disclaimer

This is a personal learning project. It documents patterns and ideas the author explored while experimenting with AI coding agents.

Use anything here freely under the [MIT License](LICENSE), but at your own risk. Evaluate everything yourself before applying it to your own work.

This project is not affiliated with, endorsed by, or sponsored by Anthropic, GitHub, or any other tool vendor mentioned in this repository. All product names, trademarks, and registered trademarks are the property of their respective owners and are used here solely for identification and descriptive purposes.

## License

[MIT License](LICENSE)
