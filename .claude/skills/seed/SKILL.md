---
name: seed
description: >-
  Compatibility alias for `/materialize`. Onboards or upgrades a harness
  consumer in one step — detects the stack, scaffolds project-owned files via
  `/init` when missing, then completely replaces the runtime. Kept so
  `/seed <project-path>` keeps working; new work should call `/materialize`.
compatibility:
  - claude-code
metadata:
  version: "4.0"
  author: team
---

# Seed

`/seed` is a **compatibility alias for [`/materialize`](../materialize/SKILL.md)**. They are the same operation: a greenfield target is just `/materialize` on an unscaffolded project — its first step runs `/init` to lay down the project-owned files, then it installs the runtime.

**Usage:** `/seed <project-path>` (e.g., `/seed ../widget`)

## What to do

Run the **`/materialize`** flow on `$ARGUMENTS` exactly as that skill describes: detect the stack from the build marker, scaffold via `/init` when `CLAUDE.md` or the `[harness]` table is missing (greenfield or copy→manifest migration), replace the runtime with `harness/materialize.sh`, classify extras (orphan → remove, extension → keep, ambiguous → ask), handle the channel, run the doctor, and print the changed / preserved / removed summary.

There is no separate seed behavior to maintain — the manifest channel collapsed onboarding (`/init` + `materialize`) and upgrading (re-materialize) into the one `/materialize` skill. The retired copy-mode Init/Upgrade/Maven-Initializr machinery is gone: runtime is materialized and gitignored (never copied or merged), build files are a precondition (never generated), and briefs are project-owned (never rewritten).
