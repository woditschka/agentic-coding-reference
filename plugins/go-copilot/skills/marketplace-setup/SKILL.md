---
name: marketplace-setup
description: Set up or upgrade this harness plugin's project-side half. Installs the engine sliver (scripts, schemas, templates) into your project and gitignores it, and refreshes the managed CLAUDE.md chapters. Run after installing the plugin and again after every plugin update.
---

# Marketplace setup

This plugin ships the harness **surfaces** — skills, agents, and hooks — into your tool's read-only plugin cache. Its skills invoke deterministic **engines** by project-relative paths: `scripts/handoff.py`, `scripts/brief_doctor.py`, `schemas/scratch/…`. Those engines must live in *your project*, not the cache. This step installs them and keeps them untracked — the marketplace channel keeps the harness runtime out of git.

Plugin skills load at session start, so **restart your tool after installing** before you invoke this. In Claude Code it is namespaced by the plugin: `/go-copilot:marketplace-setup`.

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

The plugin's skills now resolve their engine calls against your project. The remaining **project-owned** files — `scripts/layout.toml` and the `docs/` briefs, plus `CLAUDE.md` if you have not created it — are yours to provide. Scaffold them with the harness `init`, which runs from a clone of the reference, not from this plugin:

    git clone https://github.com/woditschka/agentic-coding-reference
    cd agentic-coding-reference && claude
    /init <your-project-path> marketplace

`init` fills the managed chapters, and the explicit `marketplace` argument writes the channel declaration. Never omit it: marketplace is declaration-only, and a bare `/init` infers `manifest` from the gitignored runtime — a later `/materialize` would then install the full runtime beside the plugin. Re-run this setup afterward — it verifies the declaration and brings the engines and chapters current. Then the pipeline is ready.

## Upgrading

A plugin update advances only the cached surfaces; your project's engine sliver and managed chapters stay at the old version until this setup re-runs. After every plugin update:

1. Update the plugin from the marketplace — for Claude Code refresh the marketplace, then update the plugin; other tools use their update command — and restart the tool.
2. Re-run this skill (or `setup.sh` by hand, § Run it).

The doctor surfaces a missed re-run: on this channel run it as `python3 scripts/brief_doctor.py check --plugin-version-date <plugin-root>/VERSION-DATE` (Claude Code: `${CLAUDE_PLUGIN_ROOT}`; other tools: the plugin cache directory named above). A stamp/plugin mismatch reports an advisory `WARN version-skew` naming this skill.

Re-runs are additive: an update that retires an engine file leaves the old copy behind, gitignored and inert. Delete it by hand when an upgrade note names one — setup never removes files it did not just copy.
