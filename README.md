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

### Adopt in your own project

Each implementation includes `/seed` and `/harvest` commands for pushing the pipeline into new projects and pulling improvements back.

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

## Maintenance

| Skill | Purpose |
|-------|---------|
| `research-update` | Fetch upstream tool docs, compare claims against current state, report drift |
| `audit-consistency` | Verify both implementations match root docs and each other |

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
