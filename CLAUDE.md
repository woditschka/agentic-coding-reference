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
│   ├── documentation-standards.md
│   ├── testing-principles.md
│   ├── tdd-principles.md
│   └── ddd-principles.md
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
- Each project has its own `.claude/agents/`, `.claude/skills/`, `.opencode/agents/`, and `.github/agents/`.

## What to Do at the Root Level

At the monorepo root, work is limited to:

- **Editing `docs/`** — Cross-cutting principles, the specialist agent workflow guide, and any new documentation.
- **Editing `README.md`** — The project overview and navigation.
- **Editing this file** — Monorepo-level instructions.
- **Cross-project consistency** — Ensuring patterns described in `docs/` are reflected in both implementations.

## Root-Level Skills

| Skill | Purpose |
|-------|---------|
| `audit-consistency` | Audit Go and Java projects for consistency with root docs and each other |
| `research-update` | Check upstream tool docs for changes that affect `docs/specialist-agent-workflow.md` |

**Update cycle:** `research-update` to find drift, edit the root doc, then `audit-consistency` to propagate to projects.

## Cross-Tool Compatibility

This project supports three AI coding tools. The compatibility rules from [`docs/specialist-agent-workflow.md`](docs/specialist-agent-workflow.md) apply:

1. **`CLAUDE.md` is the single rules file.** Do not create `AGENTS.md` — it breaks OpenCode's fallback.
2. **Skills live in `.claude/skills/` only.** All three tools discover skills there.
3. **Agent definitions are tool-specific.** Claude Code agents in `.claude/agents/`, OpenCode agents in `.opencode/agents/`, Copilot agents in `.github/agents/`.

## Writing Standards

All documentation must follow [`docs/documentation-standards.md`](docs/documentation-standards.md). Key rules:

- Use clear, direct prose. No filler. Maximum 30 words per sentence.
- Replace adjectives with data. No prohibited words without supporting measurements.
- Imperative mood for instructions ("Run this", not "You should run this").
- When documenting tool differences, use comparison tables.
- Include version dates and maturity status on evolving content.
- Every claim about tool behavior should be verifiable against the tool's documentation.

See the full standards for document ownership boundaries, cross-reference rules, prohibited patterns, and the validation checklist.

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
