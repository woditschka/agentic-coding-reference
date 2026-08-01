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
4. When the request needs discussion, run the elicitation in root per [`agentic-harness.md`](../handoff-routing/agentic-harness.md) § Conversations Stay in Root, then dispatch `product-requirements-expert` with the distilled decisions. Invoke the `pipeline-coordinator` only for intake that neither the elicitation nor the `next` triage covers.

## Execution

```bash
rm -rf .scratch && mkdir -p .scratch/tmp
```
