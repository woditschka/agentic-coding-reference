---
name: init
description: Scaffold the project-owned files this harness plugin needs — CLAUDE.md, .claude/settings.json, scripts/layout.toml, the seven docs/ briefs, and the .gitignore block — from the plugin's bundled skeletons. Marketplace channel by construction; no clone of the reference needed. Run once before marketplace-setup on a project that lacks these files; it never overwrites an existing one.
---

# Plugin init (marketplace)

This plugin bundles the harness `init` scaffolder, so a new project onboards without a clone of the reference. It lays down only what the **project owns and commits**: the `CLAUDE.md` rules file (managed chapters filled), `.claude/settings.json`, `scripts/layout.toml` — with `channel = "marketplace"` declared by construction — the seven `docs/` briefs, and the `.gitignore` runtime block. It never overwrites a file that already exists; re-running only fills gaps. The runtime surfaces stay in the plugin cache; the engine sliver arrives via `marketplace-setup` afterward.

In Claude Code it carries the shared skill namespace: `/agent-team:init`.

## Process

1. Confirm the target is this plugin's stack (go): the build marker must already exist — this scaffolder adopts a project, it never generates build files. A different stack means a different `agent-team-*` plugin.
2. Gather identity, inferring where possible and asking only on a miss: the project name (build files, or the directory name — confirm it) and a one-line description.
3. Ask which tool surfaces to declare (claude always on; copilot, opencode, junie optional).
4. Run the bundled scaffolder — the channel argument is pinned to `marketplace`, never inferred:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/init.py" go "$PWD" "<name>" "<description>" "" "<tools-csv>" marketplace
   ```

5. Tell the user what landed and what is theirs to fill (the briefs carry `{{FILL}}` slots; the doctor names every gap), then run `/agent-team:marketplace-setup` to install the engine sliver and verify.

## Notes

- A project that already has the files: nothing is overwritten; the run reports the gaps it filled, if any.
- The declared channel makes a later `/materialize` from a reference clone install only the engine sliver — the plugin surfaces are never duplicated into the tree.
- Scaffolding from a reference clone (`/init <path> marketplace`) remains equivalent; this skill exists so the clone is not required.
