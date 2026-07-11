# Agent Team

Agent definitions for reference. Each agent has a specific role in the feature development pipeline.

## Goals

**Primary: code meets the bar.** The bar is the conjunction of nine clauses defined across the project's principles docs. The canonical slug list and reviewer-to-clause mapping lives in the `review-workflow` skill's [`reference.md`](../skills/review-workflow/reference.md) § Quality-Bar Clause Mapping. The clauses themselves are defined here:

| Slug | Defined in |
|---|---|
| `fit-for-purpose`, `spec-grounded`, `consistent-with-codebase` | [`tdd-principles.md`](../skills/tdd-workflow/tdd-principles.md) § Scope Discipline |
| `legible-cold`, `tested-as-spec`, `correct` | [`tdd-principles.md`](../skills/tdd-workflow/tdd-principles.md) § Code That Reads Cold |
| `operationally-honest`, `human-maintainable` | [`tdd-principles.md`](../skills/tdd-workflow/tdd-principles.md) § Operationally Honest |
| `secure-by-design` | [`tdd-principles.md`](../skills/tdd-workflow/tdd-principles.md) § Secure by Design |

A change is not done until all nine hold; a passing test suite is necessary but not sufficient. Every pipeline change is judged first on whether it sustains or raises adherence.

**Secondary: token economy and wall-clock.** Subject to meeting the bar, prefer the cheaper and faster path. Tokens and wall-clock are sister concerns — most of the practices below shorten both. When they conflict, the harness favors wall-clock for interactive work and tokens for batch.

| Practice | What it means |
|---|---|
| **Read narrowly** | Load specific files, symbols, or ranges. Don't enumerate directories or read whole files when a targeted lookup suffices. Re-read only when state has changed. |
| **Think proportionally** | Match deliberation to task risk. Routine changes don't need extensive planning; novel or cross-cutting changes do. Don't pad reasoning. |
| **Draft to ship, not to impress** | No commentary explaining what the code obviously does. No restating the spec back. No preambles. Output is the artifact set, not narration about producing it. |
| **Iterate where it pays** | Self-review passes are cheap and high-value — run them. Re-running the full task to fix something a targeted edit would handle is wasteful — don't. |
| **Parallelize independent work** | Reviewer dispatches, independent agent calls, and independent tool calls go in a single message. |
| **Stop at done** | Once the bar is met, stop. Polish past the bar spends tokens and wall-clock without raising quality. |

When interpreting evaluation findings, fix in this order: (1) gaps that let code below the bar through, (2) waste at constant bar adherence, (3) cosmetic report quality.

## Architecture

**Agents own behavior.** Each agent is a thin wrapper: persona, tool permissions, model selection. Domain expertise stays in the agent definition.

**Skills own knowledge.** Portable workflow logic lives in `.claude/skills/`. All four tools (Claude Code, GitHub Copilot, OpenCode, Junie CLI) read skills from this location.

**Project docs own truth.** Requirements (`docs/prd.md`), architecture (`docs/system-design.md`), and decisions (`docs/adr/`) are the authoritative sources.

## Agents

| Agent | Role | Model | Outputs |
|-------|------|-------|---------|
| **pipeline-coordinator** | Classify fresh intake, resolve `route` escalations | Sonnet | Routing recommendations |
| **product-requirements-expert** | Define and clarify feature requirements | Opus | `docs/prd.md`, `docs/ubiquitous-language.md`, non-goal ADRs, `.scratch/handoff.jsonl` (`prd-entry`, `consultation-response` records) |
| **system-design-expert** | Validate architectural fit | Opus | `docs/system-design.md`, `docs/adr/`, `docs/ubiquitous-language.md` (foundational triage only), `.scratch/handoff.jsonl` (`design-block`, `consultation-response` records) |
| **feature-implementer** | TDD/DDD implementation | Opus | Code, tests, `.scratch/handoff.jsonl` (`build-failure`, `build-pass`, `consultation-request` records), `.scratch/implementation-plan.md`, `.scratch/escalations.md` |
| **review-planner** | Resolve a gray `review-plan` into a reviewer roster (dispatched only when the engine defers a small, clean production change) | Sonnet | `.scratch/handoff.jsonl` (`review-plan` record, `author: "review-planner"`) |
| **code-quality-reviewer** | Readability, Java style | Sonnet | `.scratch/handoff.jsonl` (`review-feedback` record, `author: "code-quality-reviewer"`) |
| **test-reviewer** | Test pyramid, coverage | Sonnet | `.scratch/handoff.jsonl` (`review-feedback` record, `author: "test-reviewer"`) |
| **security-reviewer** | OWASP, vulnerabilities | Opus | `.scratch/handoff.jsonl` (`review-feedback` record, `author: "security-reviewer"`) |
| **doc-reviewer** | Doc coherence, structure, writing | Sonnet | `.scratch/handoff.jsonl` (`review-feedback` record, `author: "doc-reviewer"`) |
| **change-grader** | Grade passing changes for how much human attention they deserve before merge (terminal, advisory) | Opus | `.scratch/handoff.jsonl` (`grader-features`, `grader-verdict` records) |

## Skills

Pipeline routing, quality gates, and templates live in portable skills.

**Universal harness skills** (lift to any project adopting this harness):

| Skill | Purpose | Used By |
|-------|---------|---------|
| `handoff-routing` | Routing table, handoff conditions, blocking rules, root-applied procedures | pipeline-coordinator, root |
| `handoff-append` | Writer contract for the handoff log: sanctioned append form, append-only discipline | every record-writing agent |
| `prd-authoring` | PRD format, boundary rules, requirement template | product-requirements-expert |
| `tdd-workflow` | TDD cycle process, design-check decision tree, document ownership | feature-implementer |
| `code-quality-gate` | Build/test/lint requirements, completion criteria | feature-implementer, reviewers |
| `review-workflow` | Review process, feedback tags, output format, partial-artifact contract; reference tables in its `reference.md` | All reviewers, feature-implementer |
| `code-quality-review` | Java code quality checklist | code-quality-reviewer |
| `test-review` | Test quality checklist, security testing | test-reviewer |
| `security-review` | Security checklists, threat model, severity, dependency verification | security-reviewer |
| `design-validation` | Architectural validation checklist for feature approval | system-design-expert |
| `adr-template` | ADR format, naming conventions | system-design-expert |
| `new-feature` | Clear scratch directory, start fresh context | root (user-invoked) |
| `audit-agents` | Audit agent config for consistency, coherence, cross-tool parity | Human / any agent |
| `change-grading` | Grade a passing change for how much human attention it deserves (facets, worst-facet aggregation, advisory verdict) | change-grader |
| `document-writing` | Writing standards (authoring) + review checklist, validation categories, prohibited patterns | doc-reviewer |
| `doc-sync` | Synchronize documentation with codebase after implementation | Human / any agent |
| `doctor` | Deterministic blocking validation of `docs/` against the harness-project API | Human / any agent / CI |
| `audit-docs` | Audit `docs/` against the high bar — the doctor (structure) then the advisory judgment review, individually and cross-document | Human / any agent |
| `ship` | Run quality gate, commit, and push in one step | Human / any agent |
| `next` | Reset scratch, recommend next PRD requirement to implement | Human / any agent |

**Project-specific extensions** (this project only; not harvested into the universal harness):

| Skill | Purpose | Used By |
|-------|---------|---------|
| `intellij-idea` | IntelliJ MCP tools as a read-only semantic oracle/verifier | feature-implementer, reviewers, system-design-expert |
| `intellij-idea-doctor` | Health check for the IntelliJ MCP oracle: connected? right project? model loaded? | Human / any IDE-enabled agent |

## When to Use Each Agent

| Scenario | Agent | Why |
|----------|-------|-----|
| "Add user authentication" | **pipeline-coordinator** | New feature needs full pipeline |
| "Does REQ-XX-003 cover edge cases?" | **product-requirements-expert** | Requirement clarification (shortcut) |
| "Where should the retry logic live?" | **system-design-expert** | Architectural decision (shortcut) |
| "Implement REQ-XX-001" | **feature-implementer** | Clear requirement, ready to build |
| "Fix the connection timeout bug" | **feature-implementer** | Bug with known location (shortcut) |
| "Review my PR" | All reviewers in the roster | Parallel review invocation |

For the full routing table, see the `handoff-routing` skill.

## MCP Tools (IntelliJ oracle)

Claude Code agents call IntelliJ IDEA's MCP server as a read-only oracle; Copilot CLI agents are wired for the same tools but gated by an upstream bug; OpenCode and Junie are not wired. Tool names below are bare — each client prepends its own prefix (`mcp__idea__` in Claude Code, `idea/` in Copilot). See `.claude/skills/intellij-idea/intellij-mcp-integration.md` for per-client status and the `intellij-idea` skill for operation.

| Agent | MCP tools |
|-------|-----------|
| `feature-implementer` | build_project, get_file_problems, get_symbol_info, search_symbol |
| `code-quality-reviewer`, `test-reviewer`, `security-reviewer` | get_file_problems, get_symbol_info, search_symbol |
| `system-design-expert` | get_project_dependencies, get_project_modules, get_symbol_info, search_symbol |

## Cross-Tool Compatibility

This workflow targets four tools: Claude Code (primary), GitHub Copilot, OpenCode (experimental), Junie CLI.

### Rules

1. **No `AGENTS.md` file.** `CLAUDE.md` is the single rules file. All four tools read it; Junie is configured to read `CLAUDE.md` via `.junie/config.json`. An `AGENTS.md` causes OpenCode to stop reading `CLAUDE.md`.
2. **Skills in `.claude/skills/` only.** This is the only location all four tools discover. Do not create `.github/skills/`, `.opencode/skills/`, or `.junie/skills/`.
3. **Agent definitions are tool-specific.** Claude Code agents live in `.claude/agents/`. Copilot equivalents go in `.github/agents/`. OpenCode equivalents go in `.opencode/agents/`. Junie equivalents go in `.junie/agents/`. Do not try to make agent files portable.
4. **Project docs are tool-agnostic.** `docs/` is read by all tools with no special discovery. Keep requirements, architecture, and ADRs here.
5. **Pipeline state is tool-agnostic.** `.scratch/handoff.jsonl` is append-only JSONL (one JSON record per line) and other `.scratch/` markdown helpers use plain text. Any tool can read and write them.

### What Each Tool Reads

| Location | Claude Code | Copilot | OpenCode | Junie |
|----------|:-----------:|:-------:|:--------:|:-----:|
| `CLAUDE.md` | Yes | Yes | Yes (if no AGENTS.md) | Yes (via `.junie/config.json`) |
| `.claude/skills/*/SKILL.md` | Yes | Yes | Yes | Yes |
| `.claude/agents/*.md` | Yes | No | No | No |
| `.github/agents/*.agent.md` | No | Yes | No | No |
| `.opencode/agents/*.md` | No | No | Yes | No |
| `.junie/agents/*.md` | No | No | No | Yes |
| `docs/` | Yes | Yes | Yes | Yes |
| `.scratch/` | Yes | Yes | Yes | Yes |

### Adding Copilot Support

1. Create `.github/agents/` with `.agent.md` files (different YAML format).
2. Skills and docs work without changes.
3. Do not create `.github/copilot-instructions.md` — Copilot CLI reads `CLAUDE.md` natively.

### Adding OpenCode Support

1. Create `.opencode/agents/` with translated agent definitions (different YAML format).
2. Do not create `AGENTS.md`.
3. Skills and docs work without changes.

### Adding Junie Support

1. Create `.junie/agents/` with `.md` files using Junie's YAML frontmatter format (`name`, `tools`, `model`, `reasoningLevel`, `skills`).
2. Add `.junie/config.json` so Junie reads `CLAUDE.md` and discovers `.claude/skills/`.
3. Skills and docs work without changes.

## Maturity Levels

These levels track pipeline *execution* maturity — how the pipeline runs, from manual steps to coordinated parallel dispatch. Each level builds on the previous.

| Level | Name | Status | How It Works |
|-------|------|--------|-------------|
| 1 | Manual Pipeline | Superseded | User invokes each agent, checks `.scratch/`, triggers next agent manually |
| 2 | Coordinator + Skills | Superseded | Coordinator routes via skills, but review is manual between stages — superseded by Level 3's automated dispatch |
| 3 | Parallel Reviewers | **Current** | Coordinator spawns all roster reviewers as parallel subagents — the four-reviewer floor plus any declared `extra_reviewers`. Each appends a `review-feedback` record to `.scratch/handoff.jsonl` independently |
| 4 | Agent Teams | Experimental | Reviewers run as an Agent Team with peer-to-peer messaging. Claude Code only, Opus model, ~3–7x token cost |
| 5 | Full Team Orchestration | Future | Entire pipeline runs as coordinated team. Blocked by: experimental status, single-model constraint, no cross-tool support |

### Progression Guidance

- **Level 3 is the current default** — `route` decides every handoff deterministically, the coordinator resolves escalations, and the full roster dispatches in parallel.
- The file-based state machine (`.scratch/`) is more portable, transparent, and reliable than Agent Teams; the harness chooses it deliberately, not as a fallback.
- Level 4 (Agent Teams) is optional and unproven — higher is not automatically better. If you adopt it, enable it for the review phase first (lowest risk).
- Keep the file-based handoff system as the coordination backbone at all levels.

## Scratch Directory

The `.scratch/` directory holds temporary files for the current feature cycle. It is git-ignored. Delete all files after feature merge.

### Structure

```
.scratch/
├── handoff.jsonl             # Append-only structured handoff log (all agents)
├── implementation-plan.md    # TDD cycle plan (from feature-implementer)
├── escalations.md            # Items requiring human decision
└── tmp/                      # Intermediate computation files (auto-cleaned)
```

`handoff.jsonl` carries every cross-agent handoff, one JSON object per line:

| Record `type` | Producer | Schema |
|---|---|---|
| `prd-entry` | product-requirements-expert | `schemas/scratch/prd-entry.schema.json` |
| `design-block` | system-design-expert | `schemas/scratch/design-block.schema.json` |
| `consultation-request` | feature-implementer (or any specialist mid-work) | `schemas/scratch/consultation-request.schema.json` |
| `consultation-response` | system-design-expert (or any specialist consulted) | `schemas/scratch/consultation-response.schema.json` |
| `build-failure` | feature-implementer | `schemas/scratch/build-failure.schema.json` |
| `build-pass` | feature-implementer | `schemas/scratch/build-pass.schema.json` |
| `review-feedback` | each reviewer | `schemas/scratch/review-feedback.schema.json` |
| `review-plan` | feature-implementer (`scripts/score-change.py review-plan`, `author: review-plan-engine`); review-planner on the gray path | `schemas/scratch/review-plan.schema.json` |
| `design-doc-autofix` | root | `schemas/scratch/design-doc-autofix.schema.json` |
| `dispatch-start` | every substantive agent (as its first tool call); `pipeline-coordinator` and `change-grader` exempt | `schemas/scratch/dispatch-start.schema.json` |
| `grader-features` | change-grader (`scripts/score-change.py extract`) | `schemas/scratch/grader-features.schema.json` |
| `grader-verdict` | change-grader | `schemas/scratch/grader-verdict.schema.json` |

Markdown is kept only for self-tracking (`implementation-plan.md`) and human-facing artifacts (`escalations.md`). One append-only JSONL file is replayable, line-addressable, and easier to validate against schema than scattered per-agent markdown files.

### File Lifecycle

See the `handoff-routing` skill for which agent appends each record type and how the routing gate validates them at agent transitions.

### File Templates

Templates for human-read markdown files are in `.claude/templates/`:

| Template | Used By | When |
|----------|---------|------|
| `implementation-plan.md` | feature-implementer | Before coding |
| `escalations.md` | feature-implementer; root (prerequisite-missing aborts, reviewer stalls, escalate findings on an `approved` verdict) | When `tag: "escalate"` findings or `design-block` records with `verdict: "conflicting"` exist |

JSONL records do not use markdown templates — they are validated against the JSON Schemas in `schemas/scratch/`.

### Rules

1. **One feature at a time** — Clear scratch before starting new feature.
2. **Agents own their record types** — Each agent appends only the record types listed above.
3. **Read before write** — Agents read upstream records before appending their own.
4. **Append-only** — Never edit, reorder, or delete prior records in `handoff.jsonl`. Use `supersedes_record_at` (where supported) to correct a prior decision.
5. **Traceability** — Every record references the requirement ID (`req_id` matching `^REQ-[A-Z]+-[0-9]{3}$`).
6. **No system /tmp** — Use `.scratch/tmp/` for intermediate computation files.
