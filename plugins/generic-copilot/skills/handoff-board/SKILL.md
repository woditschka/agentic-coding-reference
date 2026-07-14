---
name: handoff-board
description: >-
  The reader board for the handoff log: render each slice of
  .scratch/handoff.jsonl — header, review-convergence matrix, timeline —
  to the terminal via scripts/handoff.py view. Load when the user asks
  where the pipeline stands, for a slice status, or for a review-progress
  summary. The writer side lives in handoff-append; routing lives in
  handoff-routing.
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

Renders one board per slice, each three sections top to bottom:

1. **Header** — `req_id`, the slice title, round and build counts, the grade verdict, and a whole-slice roll-up (elapsed plus aggregated cost) when the cost attributes.
2. **Review convergence matrix** — rows are the reviewer roster (the floor, `layout.toml` extras, plus any other feedback author), columns are review rounds. A lane reading `✎ ✎ ✔` shows the rework.
3. **Timeline** — the slice's records in append order. Implementer work groups as an implement session with its build attempts and mid-work consults nested; reviews nest their findings; grader facets expand under the grade. Fan-out noise is omitted.

Each step shows its elapsed wall-clock (`◷`, dispatch-start → record; `ts` is append-stamped, so the span is real) and — Claude Code only — its resource cost in the statusline's grouped vocabulary (`Σ` spend, `⛁` cache). Example review tail: `◷ 2m │ Σ ▲1.2M ▼4k $0.34 │ ⛁ 88% $71%`. The dollar figure is a list-price notion — usage times the pricing table in `cc_accounting.py`, the single edit point — not a bill. Both cells degrade to omission, never to a guess. A missing timestamp, an absent transcript (another tool, swept history), or an ambiguous attribution window drops that cell alone; it never gates the board. The exact session-parenting, duration-bounding, and cost-attribution rules live in `handoff.py view` — the source is their contract, and this skill deliberately does not restate them (§ Read-Only Discipline: the layout may change).

With no `--req-id`, every slice renders as its own board, oldest to newest by first-record append position — the newest slice lands at the bottom. `--req-id` narrows to one slice and adds an `also in log:` pointer to the others. Records carrying no `req_id` render last under a `(no req_id)` header. `--verbose` prints full finding descriptions and fixes instead of one-line gists.

Pass `--color` when you render the board for the user: your shell tool pipes stdout, auto-detection sees no TTY, and the board renders monochrome without it. The terminal displaying the conversation renders the ANSI styling. Auto-detection (no flag) suits a real TTY; `--no-color` forces plain output for logs or diffs. `NO_COLOR` disables auto-detection but an explicit `--color` beats it.

The board reads, it never gates. A missing or dirty log renders what parses and lists the problems; a malformed `layout.toml` falls back to the floor roster. A build with no implement session — an orphan record in a malformed log — falls back to the flat `── ▲ build-pass ──` / `── ▲ build-failure ──` rule. Only `--req-id` with no records exits 3.

## When to Render

- The user asks where the pipeline stands, what reviewers found, or how a slice converged.
- A dispatch cycle ends and the user wants a summary instead of raw records.

## Presenting the Board

The terminal collapses long tool output; the user expands it in place (ctrl+o in Claude Code). So after running the command, do not re-echo the board into your reply — the copy loses the ANSI styling and doubles the content. Follow it with one or two plain sentences: the state of the latest slice (or, when the user asked about a specific one, that slice) and anything that needs the user's attention (an unresolved concern, a stalled reviewer, the grade). If the output was collapsed, say the full board sits in the tool output above.

## Read-Only Discipline

The board is display, never a routing input. Routing decisions come from `scripts/handoff.py route` per the `handoff-routing` skill; machine questions about single records use `latest`. Never parse board output — it is formatted for humans and its layout may change. For raw record inspection, `show` pretty-prints records as JSON.
