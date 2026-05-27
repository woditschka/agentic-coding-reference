---
name: new-feature
description: >-
  Clear the scratch directory and start a fresh feature context.
  Load when starting a new feature or resetting pipeline state.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
metadata:
  version: "1.0"
  author: team
---

# New Feature

Clear the `.scratch/` directory and start a fresh feature context.

## Instructions

1. Remove the entire `.scratch/` directory.
2. Recreate `.scratch/tmp/`. The `handoff.jsonl` file is created on first append by the product-requirements-expert; do not pre-create it.
3. Report what was cleared and confirm the directory is ready.
4. Invoke the `pipeline-coordinator` agent to classify the user's request and route to the correct specialist agent.

## Execution

```bash
rm -rf .scratch && mkdir -p .scratch/tmp
```
