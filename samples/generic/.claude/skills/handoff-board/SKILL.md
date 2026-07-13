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

1. **Header** — `req_id`, the slice title from its `prd-entry`, counts of review rounds, build-passes, and build-failures, and the grade verdict. A third line carries the whole-slice roll-up: elapsed from first record to last, and the cost aggregated across the slice's own authors over that window — untimed steps included. It renders only when the cost attributes; the roll-up can therefore exceed the sum of the visible step tails.
2. **Review convergence matrix** — rows are the reviewer roster (the floor, `layout.toml` extras, plus any other feedback author), columns are review rounds. A lane reading `✎ ✎ ✔` shows the rework.
3. **Timeline** — the slice's records in append order. The implementer's work renders as an **implement session**: a parent — `◆ implement` (fresh), or `↻ implement ← <reviewer>` (a fix) — with its build attempts and its own mid-work consults as `├`/`└` children. The session closes at its clean build, `└ ▲ build ✓ clean`; a failed attempt nests as `├ ▲ build ✗ <check> failed`. The build line names no author, so the parent is where the implementer surfaces. Reviews keep their findings nested the same way, and grader facets expand under the grade. A doc-owner's fix (a prd-expert or designer answering a reviewer, producing no build) stays a flat `↻ fix` line. A sibling's consult or doc-autofix interleaving into the session window renders flat too, naming its real author. Any other record type landing inside the window closes the session early; its later build then falls back to the flat rule. Reviewer fan-out, the designer's triage dispatch, and `grader-features` are omitted as noise.

   Each record-producing step shows its elapsed time, marked `◷`. `prd-entry`, `design-block`, the implement session, and a review are each timed from the author's dispatch-start to the record produced. The grade carries no duration: the change-grader is dispatch-exempt, so no dispatch marks its start. A doc-owner's `↻ fix` carries no duration — it emits no record, so it has no comparable work span. Any duration is omitted when a bounding timestamp is absent or out of order. A dispatch times only its first record of a type: a re-engaged author appends no fresh dispatch, so its later records show no duration rather than an inflated one.

   Each timed step also shows its Claude Code resource cost, joined after the `◷` marker in the statusline's grouped vocabulary: a `Σ` spend group (`▲` tokens in, `▼` tokens out, `$` list-price dollars) and a `⛁` cache group (hit %, then the `$N%` savings cell — suppressed when the window has no cache activity), `│`-separated. Example review tail: `◷ 2m │ Σ ▲1.2M ▼4k $0.34 │ ⛁ 88% $71%`. The cost sums the step author's subagent transcript over the same dispatch→record window the duration uses. Each subagent owns a separate transcript and the lookup keys on the author's agent type, so concurrent fan-out of distinct reviewers attributes cleanly. Same-type activity inside one window sums — an implementer's retries, the intended per-session total. The figure is a list-price notion — usage times the pricing table in `cc_accounting.py`, the single edit point — not a bill; subscription users pay no per-token charge. The overlay is Claude-Code-only and never gates the board. When the transcripts are absent — another tool, or swept history — the cost is silently omitted and the step shows its duration alone. A window that cannot be attributed unambiguously, such as a second concurrent session over the same project, degrades the same way, matching the discipline of a missing timestamp.

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
