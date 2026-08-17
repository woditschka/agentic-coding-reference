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

1. Guard the removal: when `.scratch/handoff.jsonl` exists, run `python3 scripts/handoff.py route` first — `no-active-slice` clears it; any other decision surfaces to the user before anything is wiped. A `blocked` `human-consultation` is a paused elicitation awaiting the human's answer, never stale state.
2. Remove the entire `.scratch/` directory.
3. Recreate `.scratch/tmp/`. The `handoff.jsonl` file is created on first append by the product-requirements-expert; do not pre-create it.
4. Report what was cleared and confirm the directory is ready.
5. When the request needs discussion, load the `intake` skill: the discussion runs in this session under the product expert's contract and exits by recording an `intake-decision` — the owner's request and decisions, quoted verbatim. `route` then dispatches `product-requirements-expert` on the record (`intake-ready`). When no reply can arrive, skip the discussion and seed the `intake-decision` from the request as stated (`source: "task-prompt"`). Never seed while a `consultation-request` targeting `human` is pending — that pause resolves only through the human's reply. Invoke the `pipeline-coordinator` only for intake that neither the `intake` skill nor the `next` triage covers.

## Execution

```bash
rm -rf .scratch && mkdir -p .scratch/tmp
```
