---
name: intake
description: >-
  Run slice intake as a live discussion under the product expert's contract,
  then record the owner's request and decisions verbatim as an intake-decision
  record. Load when the user brings a feature request for discussion or
  invokes /intake.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/prd.md
metadata:
  version: "1.0"
  author: team
---

# Intake

The intake discussion runs in the current root session under the product expert's judgment contract — no clearing, no fresh session, no dispatch while the discussion is live. The exit appends one `intake-decision` record: the owner's request and decisions, quoted verbatim. Root records the discussion's outcome; it never authors a product statement — the `product-requirements-expert` dispatch that follows grounds the slice in the record's quotes, not in root's memory of the chat.

Headless runs skip the discussion and seed the same record from the task prompt's decision clauses (`source: "task-prompt"`). Both front doors produce one contract; everything downstream is identical.

## Instructions

1. **Adopt the contract.** Load the `prd-authoring` skill and hold the product expert's judgment for the discussion: the PRD boundary, the non-goal discipline, the slice-sizing rule. When the discussion turns structural (trade-offs, integration, feasibility), also load `design-validation` and hold both. Skills ship on every channel; the specialists' write scopes stay theirs.
2. **Run the discussion** under the elicitation doctrine in [`agentic-harness.md`](../handoff-routing/agentic-harness.md) § Conversations Stay in Root: push back asymmetrically, hold once, surface every contradiction, own the stop.
3. **Name the exit** and let the owner confirm it. *Resolved* proceeds to steps 4–6. *Out of scope for this slice* leaves the question open — it resurfaces as a `consultation-request` if implementation needs it.
4. **Mint the `req_id`.** A `next`-triaged pick carries its REQ; otherwise take the next free `REQ-XX-NNN` per the `docs/prd.md` conventions (`prd-authoring` skill).
5. **Record the intake.** Append one `intake-decision` record via `python3 scripts/handoff.py append` (`handoff-append` skill). Fields: `author: "human"`; `request` — the owner's request, quoted verbatim; `decisions` — each decision the owner stated, quoted verbatim; `source: "intake-discussion"`; `notes` — points the owner deliberately left unsettled. Only `decisions` text can authorize a scope override at Gate 1; the request is context, never authority. Schema: `schemas/scratch/intake-decision.schema.json`.
6. **Route.** Run `python3 scripts/handoff.py route`. The `intake-ready` decision dispatches `product-requirements-expert`; its prompt names the record, never restates it.

## Rules

- A quote is the owner's words. When a position emerged in discussion but the owner never stated it compactly, ask the owner to state the decision and quote the answer — a distillate is authorship, not relay.
- A decision the owner has not stated is an open question, never a `decisions` entry.
- The record binds the human, never the specialist: the product expert judges the quoted intake cold against the PRD and may push back via a `consultation-request` targeting `human`.
- One record per intake exit. A re-opened discussion ends in a fresh `intake-decision`; the latest record governs.
