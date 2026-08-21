# Cross-Tool Compatibility, Maturity Levels, and the Scratch Directory

The stack-agnostic half of the agents README, shipped once from the harness core; each stack's `README.md` carries the stack head (roster, skills, model pins) and points here. Not an agent definition — the producer tooling skips `README*` files in this directory.

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

1. Create `.junie/agents/` with `.md` files using Junie's YAML frontmatter format — the shipped `.junie/agents/*.md` files are the key reference.
2. Add `.junie/config.json` so Junie reads `CLAUDE.md` and discovers `.claude/skills/`.
3. Skills and docs work without changes.

## Maturity Levels

These levels track pipeline *execution* maturity — how the pipeline runs, from manual steps to coordinated parallel dispatch. Each level builds on the previous.

| Level | Name | Status | How It Works |
|-------|------|--------|-------------|
| 1 | Manual Pipeline | Superseded | User invokes each agent, checks `.scratch/`, triggers next agent manually |
| 2 | Coordinator + Skills | Superseded | Coordinator routes via skills, but review is manual between stages — superseded by Level 3's automated dispatch |
| 3 | Parallel Reviewers | **Current** | Root dispatches the `review-plan`'s roster as parallel subagents on `route`'s decision — the four-reviewer floor plus declared `extra_reviewers`, narrowed per pass by the plan. Each appends a `review-feedback` record to `.scratch/handoff.jsonl` independently |
| 4 | Agent Teams | Experimental | Reviewers run as an Agent Team with peer-to-peer messaging. Claude Code only, Opus model, ~3–7x token cost |
| 5 | Full Team Orchestration | Future | Entire pipeline runs as coordinated team. Blocked by: experimental status, single-model constraint, no cross-tool support |

### Progression Guidance

- **Level 3 is the current default** — `route` decides every handoff deterministically, the coordinator resolves escalations, and the plan's roster dispatches in parallel.
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
| `intake-decision` | `human` via root — the `intake` skill's exit, or headless seeding from the task prompt | `schemas/scratch/intake-decision.schema.json` |
| `prd-entry` | product-requirements-expert | `schemas/scratch/prd-entry.schema.json` |
| `design-block` | system-design-expert | `schemas/scratch/design-block.schema.json` |
| `consultation-request` | feature-implementer (or any specialist mid-work) | `schemas/scratch/consultation-request.schema.json` |
| `consultation-response` | the consulted specialist, or `human` via root on an elicitation pause | `schemas/scratch/consultation-response.schema.json` |
| `build-failure` | feature-implementer | `schemas/scratch/build-failure.schema.json` |
| `build-pass` | feature-implementer | `schemas/scratch/build-pass.schema.json` |
| `review-feedback` | each reviewer | `schemas/scratch/review-feedback.schema.json` |
| `review-plan` | the `build-pass` append (composing `scripts/grading.py review-plan`, `author: review-plan-engine`); review-planner on the gray path | `schemas/scratch/review-plan.schema.json` |
| `design-doc-autofix` | root | `schemas/scratch/design-doc-autofix.schema.json` |
| `prd-autofix` | root | `schemas/scratch/prd-autofix.schema.json` |
| `dispatch-start` | every substantive agent (as its first tool call); `pipeline-coordinator` and `change-grader` exempt | `schemas/scratch/dispatch-start.schema.json` |
| `grader-features` | change-grader (`scripts/grading.py extract`) | `schemas/scratch/grader-features.schema.json` |
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
