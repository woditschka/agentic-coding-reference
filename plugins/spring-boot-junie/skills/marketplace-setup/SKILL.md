---
name: marketplace-setup
description: One-time setup after installing this harness plugin from the marketplace. Installs the engine sliver (scripts, schemas, templates) into your project and gitignores it. Run once per project, before using the pipeline.
---

# Marketplace setup

This plugin ships the harness **surfaces** — skills, agents, and hooks — into your tool's read-only plugin cache. Its skills invoke deterministic **engines** by project-relative paths: `scripts/handoff.py`, `scripts/brief_doctor.py`, `schemas/scratch/…`. Those engines must live in *your project*, not the cache. This one-time step installs them and keeps them untracked — the marketplace channel keeps the harness runtime out of git.

Plugin skills load at session start, so **restart your tool after installing** before you invoke this. In Claude Code it is namespaced by the plugin: `/spring-boot-junie:marketplace-setup`.

## Run it (Claude Code)

```!
bash "${CLAUDE_PLUGIN_ROOT}/setup.sh" "$PWD"
```

## Run it (any tool)

From your project root, run the bundled installer with the plugin's install directory:

    bash <plugin-install-dir>/setup.sh

Find `<plugin-install-dir>` in your tool's plugin cache — Claude exposes it as `$CLAUDE_PLUGIN_ROOT`; for Copilot CLI and Junie CLI it is the marketplace/extension cache directory for `agentic-harness`. The script self-locates, copies its bundled `_engine/` into your project, and appends the gitignore block.

## What it installs

- `scripts/` — the engines (`handoff.py`, `brief_doctor.py`, `score-change.py`), their tests, and the doctor manifest.
- `schemas/scratch/` — the handoff record schemas.
- `.claude/templates/` — the plan and escalation templates.

All gitignored, so they stay untracked like every harness runtime file.

It also **refreshes the harness-managed chapters** of your `CLAUDE.md` (Agent Usage, Memory, Writing Standards, Scratch Directory, Documentation Updates) from the bundled source, in place by heading — the marketplace equivalent of the copy channel's automatic refresh. Only those chapters are written; the rest of `CLAUDE.md` is yours. If you have no `CLAUDE.md` yet, this step skips it; scaffold it first (next section), then re-run setup.

## After setup

The plugin's skills now resolve their engine calls against your project. The remaining **project-owned** files — `scripts/layout.toml` and the `docs/` briefs, plus `CLAUDE.md` if you have not created it — are yours to provide; scaffold them with the harness `init` (which fills the managed chapters), then re-run this setup so the engines and chapters are both current. Then the pipeline is ready.
