---
name: handoff-view
description: >-
  The reader view of the handoff log: render one slice of
  .scratch/handoff.jsonl as a terminal status view via
  scripts/handoff.py view. Load when the user asks where the pipeline
  stands, for a slice status, or for a review-progress summary.
  The writer side lives in handoff-append; routing lives in handoff-routing.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
metadata:
  version: "1.0"
  author: team
---

## One Command

```bash
python3 scripts/handoff.py view --color [--req-id <id>] [--verbose]
```

Renders three sections for one slice, top to bottom:

1. **Header** — `req_id`, the slice title from its `prd-entry`, counts of review rounds, build-passes, and build-failures, and the grade verdict.
2. **Review convergence matrix** — rows are the reviewer roster (the floor, `layout.toml` extras, plus any other feedback author), columns are review rounds. A lane reading `✎ ✎ ✔` shows the rework.
3. **Timeline** — the slice's records in append order: build gates as separators, review findings nested under their review, grader facets expanded, consultations as detours. `dispatch-start` and `grader-features` are omitted as noise.

`--req-id` selects the slice; it defaults to the latest record's `req_id`. Records carrying no `req_id` render unfiltered under a `(no req_id)` header. `--verbose` prints full finding descriptions and fixes instead of one-line gists.

Pass `--color` when you run the view for the user: your shell tool pipes stdout, auto-detection sees no TTY, and the board renders monochrome without it. The terminal displaying the conversation renders the ANSI styling. Auto-detection (no flag) suits a real TTY; `--no-color` forces plain output for logs or diffs. `NO_COLOR` disables auto-detection but an explicit `--color` beats it.

The view reads, it never gates. A missing or dirty log renders what parses and lists the problems; a malformed `layout.toml` falls back to the floor roster. Only `--req-id` with no records exits 3.

## When to Render

- The user asks where the pipeline stands, what reviewers found, or how a slice converged.
- A dispatch cycle ends and the user wants a summary instead of raw records.

## Presenting the Board

The terminal collapses long tool output; the user expands it in place (ctrl+o in Claude Code). So after running the command, do not re-echo the board into your reply — the copy loses the ANSI styling and doubles the content. Follow it with one or two plain sentences: the slice's state and anything that needs the user's attention (an unresolved concern, a stalled reviewer, the grade). If the output was collapsed, say the full board sits in the tool output above.

## Read-Only Discipline

The view is display, never a routing input. Routing decisions come from `scripts/handoff.py route` per the `handoff-routing` skill; machine questions about single records use `latest`. Never parse view output — it is formatted for humans and its layout may change. For raw record inspection, `show` pretty-prints records as JSON.
