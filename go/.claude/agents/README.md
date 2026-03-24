# Agent Team

Agent definitions for reference. Each agent has a specific role in the feature development pipeline.

## Architecture

**Agents own behavior.** Each agent is a thin wrapper: persona, tool permissions, model selection. Domain expertise stays in the agent definition.

**Skills own knowledge.** Portable workflow logic lives in `.claude/skills/`. All three tools (Claude Code, OpenCode, GitHub Copilot) read skills from this location.

**Project docs own truth.** Requirements (`docs/prd.md`), architecture (`docs/system-design.md`), and decisions (`docs/adr/`) are the authoritative sources.

## Agents

| Agent | Role | Model | Outputs |
|-------|------|-------|---------|
| **pipeline-coordinator** | Classify requests, check state, route to agents | Sonnet | Routing recommendations |
| **product-requirements-expert** | Define and clarify feature requirements | Opus | `docs/prd.md`, `.scratch/current-feature.md` |
| **system-design-expert** | Validate architectural fit | Opus | `docs/system-design.md`, `.scratch/design-notes.md` |
| **feature-implementer** | TDD/DDD implementation | Opus | Code, tests, `cmd/config.example.yaml`, `.scratch/implementation-plan.md` |
| **code-quality-reviewer** | Readability, Go style guide | Sonnet | `.scratch/reviews/code-quality.md` |
| **test-reviewer** | Test pyramid, coverage | Sonnet | `.scratch/reviews/test-coverage.md` |
| **security-reviewer** | OWASP, vulnerabilities | Sonnet | `.scratch/reviews/security.md` |
| **doc-reviewer** | Doc coherence, structure, writing | Sonnet | `.scratch/reviews/doc-review.md` |

## Skills

Pipeline routing, quality gates, and templates live in portable skills:

| Skill | Purpose | Used By |
|-------|---------|---------|
| `pipeline-handoff` | Routing table, handoff conditions, blocking rules | pipeline-coordinator |
| `prd-authoring` | PRD format, boundary rules, requirement template | product-requirements-expert |
| `tdd-workflow` | TDD cycle process, design-check decision tree, document ownership | feature-implementer |
| `code-quality-gate` | Build/test/lint requirements, completion criteria | feature-implementer, reviewers |
| `review-checklist` | Feedback tags, issue classification, review output format, review process | All reviewers, feature-implementer |
| `code-quality-review` | Go code quality checklist (Google Go Style Guide) | code-quality-reviewer |
| `test-review` | Test quality checklist, security testing, dynamic analysis | test-reviewer |
| `security-review` | Security checklists, threat model, severity, supply chain verification | security-reviewer |
| `design-validation` | Architectural validation checklist for feature approval | system-design-expert |
| `adr-template` | ADR format, naming conventions | system-design-expert |
| `new-feature` | Clear scratch directory, start fresh context | pipeline-coordinator |
| `audit-agents` | Audit agent config for consistency, coherence, cross-tool parity | Human / any agent |
| `feature-eval` | Score completed features: tests, reviews, retry count | pipeline-coordinator |
| `doc-review` | Documentation review checklist, validation categories, review process | doc-reviewer |
| `doc-sync` | Synchronize documentation with codebase after implementation | Human / any agent |

## When to Use Each Agent

| Scenario | Agent | Why |
|----------|-------|-----|
| "Add user authentication" | **pipeline-coordinator** | New feature needs full pipeline |
| "Does REQ-XX-003 cover edge cases?" | **product-requirements-expert** | Requirement clarification (shortcut) |
| "Where should the retry logic live?" | **system-design-expert** | Architectural decision (shortcut) |
| "Implement REQ-XX-001" | **feature-implementer** | Clear requirement, ready to build |
| "Fix the connection timeout bug" | **feature-implementer** | Bug with known location (shortcut) |
| "Review my PR" | All four reviewers | Parallel review invocation |

For the full routing table, see the `pipeline-handoff` skill.

## Cross-Tool Compatibility

This workflow targets three tools: Claude Code (primary), OpenCode (experimental), GitHub Copilot.

### Rules

1. **No `AGENTS.md` file.** `CLAUDE.md` is the single rules file. All three tools read it. An `AGENTS.md` causes OpenCode to stop reading `CLAUDE.md`.
2. **Skills in `.claude/skills/` only.** This is the only location all three tools discover. Do not create `.opencode/skills/` or `.github/skills/`.
3. **Agent definitions are tool-specific.** Claude Code agents live in `.claude/agents/`. OpenCode equivalents go in `.opencode/agents/`. Copilot equivalents go in `.github/agents/`. Do not try to make agent files portable.
4. **Project docs are tool-agnostic.** `docs/` is read by all tools with no special discovery. Keep requirements, architecture, and ADRs here.
5. **Pipeline state is tool-agnostic.** `.scratch/` files use plain markdown with status strings. Any tool can read and write them.

### What Each Tool Reads

| Location | Claude Code | OpenCode | Copilot |
|----------|:-----------:|:--------:|:-------:|
| `CLAUDE.md` | Yes | Yes (if no AGENTS.md) | Yes |
| `.claude/skills/*/SKILL.md` | Yes | Yes | Yes |
| `.claude/agents/*.md` | Yes | No | No |
| `.opencode/agents/*.md` | No | Yes | No |
| `.github/agents/*.agent.md` | No | No | Yes |
| `docs/` | Yes | Yes | Yes |
| `.scratch/` | Yes | Yes | Yes |

### Adding OpenCode Support

1. Create `.opencode/agents/` with translated agent definitions (different YAML format).
2. Do not create `AGENTS.md`.
3. Skills and docs work without changes.

### Adding Copilot Support

1. Create `.github/agents/` with `.agent.md` files (different YAML format).
2. Skills and docs work without changes.
3. Do not create `.github/copilot-instructions.md` — Copilot CLI reads `CLAUDE.md` natively.

## Maturity Levels

The pipeline follows a maturity progression. Each level builds on the previous.

| Level | Name | Status | How It Works |
|-------|------|--------|-------------|
| 1 | Manual Pipeline | Superseded | User invokes each agent, checks `.scratch/`, triggers next agent manually |
| 2 | Coordinator + Skills | **Current** | Coordinator agent reads state and routes. Skills carry workflow logic. User reviews between stages |
| 3 | Parallel Reviewers | Available | Coordinator spawns all four reviewers as parallel subagents. Each writes to `.scratch/reviews/` independently |
| 4 | Agent Teams | Experimental | Reviewers run as an Agent Team with peer-to-peer messaging. Claude Code only, Opus model, ~5x token cost |
| 5 | Full Team Orchestration | Future | Entire pipeline runs as coordinated team. Blocked by: experimental status, single-model constraint, no cross-tool support |

### Progression Guidance

- **Stay at Level 2-3** until Agent Teams exits experimental status.
- The file-based state machine (`.scratch/`) is more portable, transparent, and reliable than Agent Teams for sequential pipelines.
- When ready for Level 4: enable Agent Teams for the review phase first (lowest risk, highest value from cross-referencing findings).
- Keep the file-based handoff system as the coordination backbone at all levels.

## Scratch Directory

The `.scratch/` directory holds temporary files for the current feature cycle. It is git-ignored. Delete all files after feature merge.

### Structure

```
.scratch/
├── current-feature.md        # Active feature scope (from PRD agent)
├── design-notes.md           # Architecture guidance (from system-design agent)
├── implementation-plan.md    # TDD cycle plan (from feature-implementer)
├── build-failure.md          # Quality gate failure output (deleted on success)
├── review-summary.md         # Consolidated reviewer feedback
├── escalations.md            # Items requiring human decision
├── eval-<feature-name>.md    # Feature evaluation scorecard
├── tmp/                      # Intermediate computation files (auto-cleaned)
└── reviews/
    ├── code-quality.md       # Style and readability findings
    ├── test-coverage.md      # Test quality findings
    ├── security.md           # Vulnerability findings
    └── doc-review.md         # Documentation coherence findings
```

### File Lifecycle

See the `pipeline-handoff` skill for which agent creates and consumes each file.

### File Templates

Templates for all scratch files are in `.claude/templates/`:

| Template | Used By | When |
|----------|---------|------|
| `current-feature.md` | product-requirements-expert | Feature scope approved |
| `design-notes.md` | system-design-expert | Architecture validated |
| `implementation-plan.md` | feature-implementer | Before coding |
| `review.md` | reviewer agents | After implementation |
| `review-summary.md` | feature-implementer | After processing reviews |
| `escalations.md` | feature-implementer | When [ESCALATE] items exist |

### Rules

1. **One feature at a time** — Clear scratch before starting new feature.
2. **Agents own their files** — Only the designated agent writes to each file.
3. **Read before write** — Agents read upstream files before creating their own.
4. **Status tracking** — Each file includes a Status field.
5. **Traceability** — Every file references the requirement ID (REQ-XX-NNN).
6. **No system /tmp** — Use `.scratch/tmp/` for intermediate computation files.
