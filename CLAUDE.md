# CLAUDE.md

This file provides guidance to Claude Code when working in this monorepo.

## Project Overview

Agentic Coding Reference: a living reference for agentic coding principles, demonstrated through production-ready agent configurations in Go and Java Spring Boot.

This is a **documentation and reference** project, not an application. The primary output is guidance, patterns, and working agent configurations that others can learn from and adapt.

## Repository Structure

```
.
├── docs/                          # Cross-cutting principles and architecture
│   ├── agentic-harness.md         # The loop model and handoff contract (the handbook)
│   ├── specialist-agent-workflow.md   # Architecture, capability progression, migration
│   ├── cross-tool-strategy.md     # Version-stamped tool comparison (research-update's surface)
│   ├── adoption-guide.md          # Consumer-facing onboarding, channels, contract
│   ├── glossary.md                # The harness vocabulary; each entry links its canonical home
│   ├── harness-project-api.md
│   ├── ddd-principles.md
│   └── adr/                       # Decision log: why the harness evolved
├── harness/                       # Single canonical harness source — samples materialize from here
│   ├── core/                      # Runtime shared by every stack
│   ├── stacks/<stack>/            # Stack-specific runtime (go, java-spring-boot, generic)
│   ├── init/                      # Skeletons for project-owned files (not runtime)
│   ├── marketplace/               # Producer-side assets for the marketplace channel (setup.sh, setup-skill.md)
│   ├── claude-md/                 # Managed-chapter source for consumer CLAUDE.md files
│   └── *.py, *.sh                 # Maintainer scripts and test suites — see harness/README.md
├── tools/                         # Repo-level tooling shared across samples
│   ├── harness-stats/             # Statusline + cache-report scripts (user-level install)
│   └── claude-pod/                # Container-confined Claude Code for permission-skipped runs (user-level install)
├── samples/                       # Materialized instances of the harness (copy channel)
│   ├── go/                        # Materialized Go instance
│   │   ├── CLAUDE.md              # Go-specific agent instructions (authoritative)
│   │   └── ...                    # docs/ + scripts/layout.toml + runtime all committed
│   ├── java-spring-boot/          # Materialized Spring Boot instance
│   │   ├── CLAUDE.md              # Spring Boot-specific agent instructions (authoritative)
│   │   └── ...
│   └── generic/                   # Materialized generic-stack instance (no build toolchain; binds via scripts/stack.sh)
├── .claude-plugin/                # Generated: marketplace.json (the reference IS a marketplace)
├── plugins/                       # Generated: per-tool plugins, rendered by package-marketplace.py
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
- **Editing `harness/`** — The canonical harness source (`core/`, `stacks/<stack>/`, `init/`) the samples materialize from. Harness changes go here, then `harness/bootstrap.sh` re-materializes all three samples; never hand-edit a sample's committed runtime. Keep `core/` stack-agnostic (no language-specific fact) and the shipped runtime stdlib-only (no third-party import, no dependency manifest).
- **Regenerating the marketplace** — `.claude-plugin/` and `plugins/` are *generated* by `harness/package-marketplace.py` from `/harness`. After a harness change, re-run it; never hand-edit the generated plugins (same rule as the samples). `check-sync.py` fails if the committed marketplace drifts from source.
- **Editing `README.md`** — The project overview and navigation.
- **Editing this file** — Monorepo-level instructions.
- **Cross-project consistency** — Ensuring patterns described in `docs/` are reflected in the sample implementations.

The root carries the canonical harness *source* (`harness/`) but never *runs* the harness — no live pipeline, no `.scratch/` handoff ledger, no agent-teams continue-hook; those run in the samples that demonstrate it. The root authors and maintains the harness; the samples execute it.

## Root-Level Skills

| Skill | Purpose |
|-------|---------|
| `audit-harness` | Hold the reference to a high bar: the deterministic battery (`check-sync.py`), then the six-check consistency audit (`/audit-agents` depth, cross-tool parity, routing, samples-reflect-handbook), then an adversarial review of the diff. Default run scopes judgment to the diff; `full` runs all six checks across the samples. One verdict |
| `review-harness` | Find where the bar could move: five parallel read-only research agents (tooling, docs, runtime cost, duplication, consumer surface), synthesis judged by the resilience-first doctrine (ADR 2026-07-12), a skeptic pass on structural findings, and ADR-recorded dispositions that outlive the report. One prioritized report; never edits |
| `release-version` | Cut one lockstep version: evaluate the semver bump from commits since the last `v*` tag, confirm with the user, then run `harness/release-version.sh`. The script stamps `harness/VERSION` (restamps all plugins), runs release-prep, and creates the `chore(release)` commit plus annotated `v<VERSION>` tag. Stops before push |
| `research-update` | Check upstream tool docs for changes that affect `docs/cross-tool-strategy.md` |
| `deps-upgrade` | Check pinned tool/plugin/dependency versions in the Go and Java samples, the init skeletons and root README that restate them, the SHA-pinned actions in the root CI workflow, and the dated pricing override in the harness-stats accounting against upstream, bump and verify |
| `harness-stats-setup` | Install or update the user-level statusline and cache-report tooling into `~/.claude/` (front-end for `tools/harness-stats/install.sh`) |
| `claude-pod-setup` | Install or update the user-level claude-pod tooling into `~/.local/bin` and `~/.config/claude-pod` (front-end for `tools/claude-pod/install.sh`) |
| `history-update` | Update the Project History section in the root README with executive-level milestones since the last entry |
| `diagram-update` | Regenerate the reference's figures (pipeline flow, lifecycle, spec flow, research arc) when the harness changes, holding one house style; owns the `docs/images/*.drawio` sources, the draw.io export, and the embeddings |
| `init` | Scaffold the project-owned files a consumer commits (CLAUDE.md, settings.json, layout.toml, docs/ briefs, .gitignore block) from `/harness`; detects the stack from the target's build marker; never installs the runtime |
| `materialize` | Install or upgrade a consumer by completely replacing its harness-owned runtime: detect stack, scaffold via `init` when missing, replace the runtime, remove stale orphans, preserve project extensions (ask when unsure), respect the declared channel, verify the installed suites, validate with the doctor |
| `harvest` | Pull generalizable improvements from a downstream project back into the `/harness` source; routes language-agnostic changes to `core/`, stack-specific ones to `stacks/<stack>/` |

**Maintainer loop** — the canonical statement of the order; other docs reference it, never restate it:

1. Edit the source: `/harness`, root `docs/`, or a root skill. (`research-update` finds upstream drift worth an edit.)
2. Tier 0, after every edit: `harness/check-sync.py`. After a `/harness` edit, `harness/release-prep.sh` instead — it renders the agent mirrors, propagates to the samples and the marketplace, then runs the same battery. For an edit outside `/harness`, the samples, and the marketplace (docs, root skills, `tools/`), `harness/check-sync.py --quick` runs only the static checks. It refuses while any derived tree is dirty, so it can never skip an affected check.
3. Tier 1, before committing a substantive change: `/audit-harness` (judgment scoped to the diff). Tier 2, before a release or periodically: `/audit-harness full`. A mechanical edit (typo, version pin) commits on tier 0. A rename, retirement, or default change that fans out across many surfaces warrants tier 2 even between releases.
4. Commit.
5. To ship: `/release-version` cuts the tagged lockstep version; then push.

## Pipeline Shape

The pipeline runs as four concentric loops — inner (TDD cycle), middle (PRD + design triage and review-until-approved for the slice), outer (slice selection), and architectural (structural review — planned for application code; runs today over the reference itself). The inner loop routes to the middle loop via consultation-request records when it discovers a question the triage didn't anticipate; the router returns control to the requester after the matching consultation-response. See [`docs/agentic-harness.md`](docs/agentic-harness.md) for the loop model and the definition of a slice. Each sample carries a trimmed agent-facing copy at `.claude/skills/handoff-routing/agentic-harness.md`; the intentional divergence is pinned in `harness/handbook-delta.expected`.

## Cross-Tool Compatibility

The root project is maintained with **Claude Code only**. The sample projects under `samples/` support four AI coding tools, and the compatibility rules from [`docs/cross-tool-strategy.md`](docs/cross-tool-strategy.md) apply there:

1. **`CLAUDE.md` is the single rules file.** Do not create `AGENTS.md` in the samples — it breaks OpenCode's fallback. Junie CLI is configured to read `CLAUDE.md` via each sample's `.junie/config.json`.
2. **Skills live in `.claude/skills/` only.** All four tools (Claude Code, Copilot CLI, OpenCode, Junie CLI) discover skills there.
3. **Agent definitions are tool-specific.** Claude Code uses `.claude/agents/`, Copilot uses `.github/agents/`, OpenCode uses `.opencode/agents/`, Junie uses `.junie/agents/`. Bodies stay identical across tools; only frontmatter differs. In `/harness`, edit only the `.claude` copy — `harness/refresh-agent-bodies.py` renders the mirror bodies and prunes mirrors whose base is gone; the battery gates a forgotten render.

## Writing Standards

All documentation must follow the [`document-writing` skill](harness/core/.claude/skills/document-writing/documentation-standards.md) — document ownership boundaries, cross-reference rules, prohibited patterns, and the validation checklist. Two rules govern every root edit:

- Maximum 30 words per sentence. No filler.
- Replace adjectives with data. No prohibited words without supporting measurements.

## Python Code Standards

Harness Python follows the typed standard from [ADR 2026-07-17](docs/adr/2026-07-17-typed-python-core.md):

- Records are frozen dataclasses; raw dicts survive only at the parse boundary and the routing core's sanctioned raw sites (gates, decision payloads, gate-message indexes).
- Every `match` over a record union ends in `typing.assert_never` — exhaustiveness is checker-enforced.
- Full annotations, `mypy --strict` clean, ruff-formatted. The battery gates all three (skip-if-missing; required under `--strict`).
- The typed scope covers both sides: the shipped runtime core and the producer-side maintainer tooling (`harness/*.py`). Producer-side sits at the grading-tier bar — complete annotations, `Any` only at parse boundaries — not the frozen-dataclass/`assert_never` rigor of the two bullets above. A new or edited maintainer script must land `mypy --strict` clean before it commits. See the [producer-side amendment](docs/adr/2026-07-17-typed-python-core.md#amendment-2026-07-18-producer-side-typed-scope).
- The shipped contract is unchanged: stdlib-only, Python 3.11+, `unittest`. `scripts/` is a composition root — root files are applications or single-file modules, directories are domain packages (`handoff/`, `changeset/`, `grading/`), and a battery gate (check-sync 1g) enforces the one-way import graph. Tests mirror the source under `scripts/tests/`. See [ADR 2026-07-17 runtime-package-layout](docs/adr/2026-07-17-runtime-package-layout.md).

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
