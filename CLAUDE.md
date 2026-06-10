# CLAUDE.md

This file provides guidance to Claude Code when working in this monorepo.

## Project Overview

Agentic Coding Reference: a living reference for agentic coding principles, demonstrated through production-ready agent configurations in Go and Java Spring Boot.

This is a **documentation and reference** project, not an application. The primary output is guidance, patterns, and working agent configurations that others can learn from and adapt.

## Repository Structure

```
.
├── docs/                          # Cross-cutting principles and architecture
│   ├── specialist-agent-workflow.md
│   ├── agentic-harness.md
│   ├── documentation-standards.md
│   ├── testing-principles.md
│   ├── tdd-principles.md
│   ├── ddd-principles.md
│   └── adr/                       # Decision log: why the harness evolved

├── tools/                         # Repo-level tooling shared across samples
│   └── harness-stats/             # Statusline + cache-report scripts (user-level install)
├── go/                            # Self-contained Go implementation
│   ├── CLAUDE.md                  # Go-specific agent instructions (authoritative)
│   └── ...
├── java-spring-boot/              # Self-contained Spring Boot implementation
│   ├── CLAUDE.md                  # Spring Boot-specific agent instructions (authoritative)
│   └── ...
└── README.md
```

## Self-Contained Implementations

The `go/` and `java-spring-boot/` directories are **self-contained projects** with their own `CLAUDE.md`, agents, skills, and build toolchains. When working inside either:

- Follow that project's `CLAUDE.md` — it is the authoritative source for build commands, conventions, and agent workflow.
- Do not apply Go conventions to Java or vice versa.
- Each project has its own `.claude/agents/`, `.claude/skills/`, `.github/agents/`, `.opencode/agents/`, and `.junie/agents/`.

## What to Do at the Root Level

At the monorepo root, work is limited to:

- **Editing `docs/`** — Cross-cutting principles, the specialist agent workflow guide, and any new documentation.
- **Editing `docs/adr/`** — The reference's decision log: why the harness evolved. Record harness-level architecture decisions here, not in the samples (the samples ship a single consolidated seed ADR). Pair each milestone with a Project History entry in `README.md`.
- **Editing `README.md`** — The project overview and navigation.
- **Editing this file** — Monorepo-level instructions.
- **Cross-project consistency** — Ensuring patterns described in `docs/` are reflected in both implementations.

The root carries no harness-running machinery (specialist agents, the `.scratch/` handoff ledger, the agent-teams continue-hook); that lives in the samples that demonstrate the harness. The root only *maintains* the reference.

## Root-Level Skills

| Skill | Purpose |
|-------|---------|
| `audit-consistency` | Audit Go and Java projects for consistency with root docs and each other |
| `research-update` | Check upstream tool docs for changes that affect `docs/specialist-agent-workflow.md` |
| `deps-upgrade` | Check pinned tool/plugin/dependency versions in Go and Java samples against upstream, bump and verify |
| `harness-stats-setup` | Install or update the user-level statusline and cache-report tooling from `tools/harness-stats/` into `~/.claude/` |
| `history-update` | Update the Project History section in the root README with executive-level milestones since the last entry |

**Update cycle:** `research-update` to find drift, edit the root doc, then `audit-consistency` to propagate to projects.

## Pipeline Shape

The pipeline runs as four concentric loops — inner (TDD cycle), middle (PRD + design triage and review-until-approved for the slice), outer (slice selection), and architectural (structural review, planned). The inner loop routes to the middle loop via consultation-request records when it discovers a question the triage didn't anticipate; the coordinator routes control back to the requester after the matching consultation-response. See [`docs/agentic-harness.md`](docs/agentic-harness.md) for the loop model and the definition of a slice. Each sample carries a byte-equivalent copy.

## Cross-Tool Compatibility

The root project is maintained with **Claude Code only**. The sample projects (`go/` and `java-spring-boot/`) support four AI coding tools, and the compatibility rules from [`docs/specialist-agent-workflow.md`](docs/specialist-agent-workflow.md) apply there:

1. **`CLAUDE.md` is the single rules file.** Do not create `AGENTS.md` in the samples — it breaks OpenCode's fallback. Junie CLI is configured to read `CLAUDE.md` via each sample's `.junie/config.json`.
2. **Skills live in `.claude/skills/` only.** All four tools (Claude Code, Copilot CLI, OpenCode, Junie CLI) discover skills there.
3. **Agent definitions are tool-specific.** Claude Code uses `.claude/agents/`, Copilot uses `.github/agents/`, OpenCode uses `.opencode/agents/`, Junie uses `.junie/agents/`. Bodies stay identical across tools; only frontmatter differs.

## Writing Standards

All documentation must follow [`docs/documentation-standards.md`](docs/documentation-standards.md) — document ownership boundaries, cross-reference rules, prohibited patterns, and the validation checklist. Two rules govern every root edit:

- Maximum 30 words per sentence. No filler.
- Replace adjectives with data. No prohibited words without supporting measurements.

## Commit Convention

Format: `<type>(<scope>): <subject>`

| Type | Use When |
|------|----------|
| `feat` | New content or capability |
| `fix` | Correction to existing content |
| `docs` | Documentation changes (most commits here) |
| `refactor` | Restructuring without changing meaning |
| `chore` | Maintenance, tooling, repo config |

Scopes: `go`, `java`, `docs`, `root`. Omit for cross-cutting changes.

Subject line: imperative mood, lowercase, no period, max 50 characters.
