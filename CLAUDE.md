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
│   ├── harness-project-api.md
│   ├── agentic-harness.md
│   ├── ddd-principles.md
│   └── adr/                       # Decision log: why the harness evolved
├── harness/                       # Single canonical harness source — samples materialize from here
│   ├── core/                      # Runtime shared by every stack
│   ├── stacks/<stack>/            # Stack-specific runtime (go, java-spring-boot, generic)
│   ├── init/                      # Skeletons for project-owned files (not runtime)
│   ├── marketplace/               # Producer-side assets for the marketplace channel (hooks.json, setup.sh, setup-skill.md)
│   └── *.sh                       # materialize / init / bootstrap / package-marketplace / check-sync
├── tools/                         # Repo-level tooling shared across samples
│   └── harness-stats/             # Statusline + cache-report scripts (user-level install)
├── samples/                       # Materialized instances of the harness (copy channel)
│   ├── go/                        # Materialized Go instance
│   │   ├── CLAUDE.md              # Go-specific agent instructions (authoritative)
│   │   └── ...                    # docs/ + scripts/layout.toml + runtime all committed
│   ├── java-spring-boot/          # Materialized Spring Boot instance
│   │   ├── CLAUDE.md              # Spring Boot-specific agent instructions (authoritative)
│   │   └── ...
│   └── generic/                   # Materialized generic-stack instance (no build toolchain; binds via scripts/stack.sh)
├── .claude-plugin/                # Generated: marketplace.json (the reference IS a marketplace)
├── plugins/                       # Generated: per-tool plugins, rendered by package-marketplace.sh
└── README.md
```

## Self-Contained Implementations

The `samples/go/`, `samples/java-spring-boot/`, and `samples/generic/` directories are **self-contained projects** — each with its own committed `CLAUDE.md`, `docs/` briefs, and `scripts/layout.toml`. Go and Java carry a full build toolchain; the generic sample binds its build through the `scripts/stack.sh` verb stubs. Their runtime (agents, skills, hooks, schemas, engines) is materialized from `/harness` on the copy channel and committed. When working inside any of them:

- Follow that project's `CLAUDE.md` — it is the authoritative source for build commands, conventions, and agent workflow.
- Do not apply Go conventions to Java or vice versa.
- The per-tool runtime (`.claude/agents/`, `.claude/skills/`, `.github/agents/`, `.opencode/agents/`, `.junie/agents/`) is materialized from `/harness` and committed on the copy channel. Edit the source in `/harness` and re-materialize; never hand-edit a sample's runtime copy.

## What to Do at the Root Level

At the monorepo root, work is limited to:

- **Editing `docs/`** — Cross-cutting principles, the specialist agent workflow guide, and any new documentation.
- **Editing `docs/adr/`** — The reference's decision log: why the harness evolved. Record harness-level architecture decisions here, not in the samples (samples ship no ADRs; a consumer's decision log is its own). Pair each milestone with a Project History entry in `README.md`.
- **Editing `harness/`** — The canonical harness source (`core/`, `stacks/<stack>/`, `init/`) the samples materialize from. Harness changes go here, then `harness/bootstrap.sh` re-materializes all three samples; never hand-edit a sample's committed runtime. Keep `core/` stack-agnostic (no language-specific fact).
- **Regenerating the marketplace** — `.claude-plugin/` and `plugins/` are *generated* by `harness/package-marketplace.sh` from `/harness`. After a harness change, re-run it; never hand-edit the generated plugins (same rule as the samples). `check-sync.sh` fails if the committed marketplace drifts from source.
- **Editing `README.md`** — The project overview and navigation.
- **Editing this file** — Monorepo-level instructions.
- **Cross-project consistency** — Ensuring patterns described in `docs/` are reflected in the sample implementations.

The root carries the canonical harness *source* (`harness/`) but never *runs* the harness — no live pipeline, no `.scratch/` handoff ledger, no agent-teams continue-hook; those run in the samples that demonstrate it. The root authors and maintains the harness; the samples execute it.

## Root-Level Skills

| Skill | Purpose |
|-------|---------|
| `audit-harness` | Hold the reference to a high bar after a change: run the deterministic battery (`check-sync.sh`), then `audit-consistency`, then an adversarial review of the diff for regressions/lost-coverage/incoherence; end with one verdict |
| `release-prep` | Roll `/harness` out to every instance, then prove it green — one call to `harness/release-prep.sh` (bootstrap + package-marketplace + the full battery). The propagate-and-verify step after a `/harness` edit; writes the tree, never commits or judges |
| `release-version` | Cut one lockstep version: evaluate the semver bump from commits since the last `v*` tag, confirm with the user, then run `harness/release-version.sh`. The script stamps `harness/VERSION` (restamps all plugins), runs release-prep, and creates the `chore(release)` commit plus annotated `v<VERSION>` tag. Stops before push |
| `audit-consistency` | Judgment-only consistency audit: `/audit-agents` depth in each sample, semantic cross-tool parity, routing semantics, samples-reflect-handbook; the mechanical consistency checks live in `check-sync.sh` |
| `research-update` | Check upstream tool docs for changes that affect `docs/specialist-agent-workflow.md` |
| `deps-upgrade` | Check pinned tool/plugin/dependency versions in Go and Java samples against upstream, bump and verify |
| `harness-stats-setup` | Install or update the user-level statusline and cache-report tooling into `~/.claude/` (front-end for `tools/harness-stats/install.sh`) |
| `history-update` | Update the Project History section in the root README with executive-level milestones since the last entry |
| `diagram-update` | Regenerate the README architecture figures (pipeline flow, build/distribute/harvest lifecycle) when the harness changes, holding one house style; owns the `docs/images/*.drawio` sources, the draw.io export, and the README embedding |
| `init` | Scaffold the project-owned files a consumer commits (CLAUDE.md, settings.json, layout.toml, docs/ briefs, .gitignore block) from `/harness`; detects the stack from the target's build marker; never installs the runtime |
| `materialize` | Install or upgrade a consumer by completely replacing its harness-owned runtime: detect stack, scaffold via `init` when missing, replace the runtime, remove stale orphans, preserve project extensions (ask when unsure), respect the declared channel, validate with the doctor |
| `harvest` | Pull generalizable improvements from a downstream project back into the `/harness` source; routes language-agnostic changes to `core/`, stack-specific ones to `stacks/<stack>/` |

**Update cycle:** `research-update` to find drift, edit the root doc, then `audit-harness` to verify the change cleared the bar before committing. Its battery carries the mechanical consistency checks; its Layer 2 runs the judgment audit (`audit-consistency`). To ship: `release-prep` propagates a `/harness` edit to the samples and the marketplace and runs the battery; `release-version` then cuts a tagged version.

## Pipeline Shape

The pipeline runs as four concentric loops — inner (TDD cycle), middle (PRD + design triage and review-until-approved for the slice), outer (slice selection), and architectural (structural review, planned). The inner loop routes to the middle loop via consultation-request records when it discovers a question the triage didn't anticipate; the coordinator routes control back to the requester after the matching consultation-response. See [`docs/agentic-harness.md`](docs/agentic-harness.md) for the loop model and the definition of a slice. Each sample carries the agent-facing copy at `.claude/skills/pipeline-handoff/agentic-harness.md` (content-equivalent; links adjusted for location).

## Cross-Tool Compatibility

The root project is maintained with **Claude Code only**. The sample projects under `samples/` support four AI coding tools, and the compatibility rules from [`docs/specialist-agent-workflow.md`](docs/specialist-agent-workflow.md) apply there:

1. **`CLAUDE.md` is the single rules file.** Do not create `AGENTS.md` in the samples — it breaks OpenCode's fallback. Junie CLI is configured to read `CLAUDE.md` via each sample's `.junie/config.json`.
2. **Skills live in `.claude/skills/` only.** All four tools (Claude Code, Copilot CLI, OpenCode, Junie CLI) discover skills there.
3. **Agent definitions are tool-specific.** Claude Code uses `.claude/agents/`, Copilot uses `.github/agents/`, OpenCode uses `.opencode/agents/`, Junie uses `.junie/agents/`. Bodies stay identical across tools; only frontmatter differs.

## Writing Standards

All documentation must follow the [`document-writing` skill](harness/core/.claude/skills/document-writing/documentation-standards.md) — document ownership boundaries, cross-reference rules, prohibited patterns, and the validation checklist. Two rules govern every root edit:

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
| `build` | Dependency or toolchain version bumps (the `deps-upgrade` skill's commits) |
| `chore` | Maintenance, tooling, repo config |

Scopes: `go`, `java`, `docs`, `root`. Omit for cross-cutting changes.

Subject line: imperative mood, lowercase, no period, max 50 characters.
