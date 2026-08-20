---
name: marketplace-setup
description: Set up or upgrade this harness plugin's project-side half. Installs the engine sliver (scripts, schemas, templates) into your project and gitignores it, and refreshes the managed CLAUDE.md chapters. Run after installing the plugin and again after every plugin update.
---

# Marketplace setup

This plugin ships the harness **surfaces** — skills, agents, and hooks — into your tool's read-only plugin cache. Its skills invoke deterministic **engines** by project-relative paths: `scripts/handoff.py`, `scripts/doctor.py`, `schemas/scratch/…`. Those engines must live in *your project*, not the cache. This step installs them and keeps them untracked — the marketplace channel keeps the harness runtime out of git.

Plugin skills load at session start, so **restart your tool after installing** before you invoke this. In Claude Code it carries the shared skill namespace: `/{{PLUGIN_NAMESPACE}}:marketplace-setup`.

## Run it (Claude Code)

Run the bundled installer through the Bash tool now, from the project root:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/setup.sh"
```

Claude Code expands `${CLAUDE_PLUGIN_ROOT}` when the skill loads; the script defaults its target to the working directory. The run costs one permission prompt. Not an injected auto-run on purpose: an injected command aborts the whole invocation on any permission check short of allow. The skill also ships no `allowed-tools` pre-approval: a plugin-shipped standing grant would bypass the user's own permission review.

## Run it (any tool)

From your project root, run the bundled installer with the plugin's install directory:

    bash <plugin-install-dir>/setup.sh

Find `<plugin-install-dir>` in your tool's plugin cache — Claude exposes it as `$CLAUDE_PLUGIN_ROOT`. Cache directories are keyed by the **marketplace entry name** (e.g. `{{PLUGIN_NAMESPACE}}/agent-team-go/<version>`), never by the shared skill namespace. The script self-locates, copies its bundled `_engine/` into your project, and appends the gitignore block.

## What it installs

- `scripts/` — the engines (`handoff.py`, `doctor.py`, `grading.py`), their tests, and the doctor manifest.
- `schemas/scratch/` — the handoff record schemas.
- `.claude/templates/` — the plan and escalation templates.

All gitignored, so they stay untracked like every harness runtime file.

It also **refreshes the harness-managed chapters** of your `CLAUDE.md` (Agent Usage, Memory, Writing Standards, Scratch Directory, Documentation Updates) from the bundled source, in place by heading — the marketplace equivalent of the copy channel's automatic refresh. Only those chapters are written; the rest of `CLAUDE.md` is yours. If you have no `CLAUDE.md` yet, this step skips it; scaffold it first (next section), then re-run setup.

## After setup

The plugin's skills now resolve their engine calls against your project. The remaining **project-owned** files — `scripts/layout.toml` and the `docs/` briefs, plus `CLAUDE.md` if you have not created it — are yours to provide. Scaffold them with the plugin's own init skill, `/{{PLUGIN_NAMESPACE}}:init` — it runs from this plugin's bundled skeletons, fills the managed chapters, and declares `channel = "marketplace"` by construction. Re-run this setup afterward — it verifies the declaration and brings the engines and chapters current. Then the pipeline is ready.

Scaffolding from a reference clone (`/init <your-project-path> marketplace`) remains equivalent. There, never omit the `marketplace` argument: a bare `/init` infers `manifest` from the gitignored runtime, and a later `/materialize` would then install the full runtime beside the plugin.

## Upgrading

A plugin update advances only the cached surfaces; your project's engine sliver and managed chapters stay at the old version until this setup re-runs. After every plugin update:

1. Update the plugin from the marketplace — for Claude Code refresh the marketplace, then update the plugin; other tools use their update command — and restart the tool.
2. Re-run this skill (or `setup.sh` by hand, § Run it).

The doctor surfaces a missed re-run: on this channel run it as `python3 scripts/doctor.py check --plugin-version-date <plugin-root>/VERSION-DATE` (Claude Code: `${CLAUDE_PLUGIN_ROOT}`; other tools: the plugin cache directory named above). A stamp/plugin mismatch reports an advisory `WARN version-skew` naming this skill.

Re-runs also **prune retired files**: the plugin bundles the harness's cumulative retired-paths manifest, and setup removes listed paths — reporting each removal. Deletion stays inside the engine-sliver namespaces (`scripts/`, `schemas/scratch/`, `.claude/templates/`); a listed path elsewhere is reported for hand removal, never deleted. The guards on the rest:

- a path the current engine still produces is never touched (reintroduction wins);
- a declared `[harness] extensions` entry is kept and reported;
- nothing under `.claude/agents/` is pruned;
- a path resolving outside the project (a symlink) is skipped;
- an unparseable `layout.toml` prunes nothing. A removal is permanent — retired paths are gitignored and no longer shipped — so declare a file of the project's own in `[harness] extensions` before re-running setup.

**Upgrade note — the shared-namespace release (ADR 2026-08-01 in the reference).** Earlier plugins were installed under `<stack>-<tool>` entries and namespaced skills the same way (`/go-claude:marketplace-setup`). From this release one name covers everything: skills share the `{{PLUGIN_NAMESPACE}}` namespace — type `/{{PLUGIN_NAMESPACE}}:…` — entry names lead with it (`{{PLUGIN_NAMESPACE}}-<stack>` for Claude Code, `{{PLUGIN_NAMESPACE}}-<stack>-<tool>` for Copilot and Junie), and the marketplace itself registers as `{{PLUGIN_NAMESPACE}}`. A registration or install keyed by an old name (`agentic-harness`, `spring-boot-claude@agentic-harness`) no longer matches. Migrate once: uninstall the old entry, remove the `agentic-harness` marketplace, re-add the repo (it registers as `{{PLUGIN_NAMESPACE}}`), install the new entry, and move any `extraKnownMarketplaces` and `enabledPlugins` keys to the new names.

**Upgrade note — the package-layout release (ADR 2026-07-17 runtime-package-layout in the reference).** The flat engine layout retired; the engine internals now live in packages (`scripts/handoff/`, `scripts/grading/`, `scripts/changeset/`) behind unchanged `scripts/` launchers, and the suites in `scripts/tests/`. The release also renamed two engines: `score-change.py` became `grading.py` and `cc_accounting.py` became `accounting.py`. All the retired flat files are in the bundled retired-paths manifest, so re-running this setup removes any your `scripts/` still carries — no hand-deletion needed.
