---
name: cache-report
description: >-
  Generate a per-agent cache-efficiency report for the current Claude Code
  session. Use when the user asks about cache stats, cache efficiency,
  prompt-cache performance, token savings, or whether subagents are using
  cache effectively. Examples: "show cache report", "how's the cache doing",
  "cache stats", "are subagents efficient", "which agents are wasting cache",
  "session token breakdown".
metadata:
  version: "1.0"
---

## What this does

Runs `~/.claude/cache-report.sh` and presents the result. The script emits three sections:

- **Session** — total tokens by category, hit %, and net savings vs no-cache baseline.
- **Per-agent breakdown** — runs, median turns, warm-start %, in-run reuse %, net savings %, one row per `agentType`.
- **Findings** — auto-generated bullets flagging multi-run agents with low warm-start, single-fire agents that never amortized their write premium, negative net savings, low in-run reuse, or a session-wide hit rate below 75%. Empty means everything amortizes as expected.

Companion to the statusline (`~/.claude/statusline.sh`), which shows live aggregates; this skill is for deeper per-agent analysis on demand.

## Process

### 1. Run the script

Default — current cwd, most recent session (usually the active session):

```bash
~/.claude/cache-report.sh
```

Variants:

| User asks for… | Command |
|---|---|
| A specific session | `~/.claude/cache-report.sh <session_id>` |
| A session in another project | `~/.claude/cache-report.sh <session_id> <project_dir>` |
| List of available sessions | `~/.claude/cache-report.sh --list` |

### 2. Present the output

Show the script's output verbatim inside a fenced code block. The script auto-detects whether stdout is a TTY — when invoked through a tool wrapper (non-TTY), it emits plain text so the columns stay aligned; in an interactive terminal it adds ANSI bold/dim/color. Either way, no post-processing is needed.

### 3. Interpret the Findings section

The script auto-flags anomalies in its own `Findings` section. Read each bullet and add a one-sentence interpretation pointing at the actionable next step. Don't restate the bullet — explain what to do about it.

| Finding pattern | Suggested next step |
|---|---|
| `<agent> fired N× with only X% warm-start` | Cluster fires more tightly within the 5-minute TTL, or accept the cost as inherent to that agent's role. |
| `N single-fire agents … paid the write premium with no follow-up` | If those agents are run once per feature by design, the write premium is unavoidable; otherwise invoke them earlier so a second fire can read from cache. |
| `<agent> has negative net savings` | Stop using that agent for one-shot work, or batch its invocations. |
| `<agent> has only X% in-run reuse` | Prefix is being invalidated mid-run — check for file re-reads with changed content, tool result ordering, or `/compact` events. |
| `Session hit rate X%` | If mid-session, let the cache warm; if long-running and still flagged, investigate structural prefix invalidation. |

If the Findings section reads `All agents amortize the cache-write premium — nothing actionable`, say so in one sentence and stop. Do not fabricate findings the script didn't surface.

## Output interpretation reference

- **Warm-start %** — share of an agent's invocations whose first turn was served from cache (i.e., a prior fire's cache was still alive in the 5-minute TTL).
- **In-run reuse %** — share of turns 2+ within a single fire whose input was served from cache (i.e., the conversation prefix is stable across the fire's turns).
- **Net savings %** — `1 − actual_cost / no_cache_baseline_cost`. Positive = cache saved money. Negative = cache cost more than no caching at all.

Pricing multipliers used (relative to base input price): cache write = 1.25×, cache read = 0.10×, uncached input = 1.00×.

## Dependencies

- `~/.claude/cache-report.sh` — the underlying script.
- `jq` — JSON processing.
- `numfmt` (GNU coreutils) — token-count formatting; present by default on Linux, may need install on macOS.

## What this skill does NOT do

- Modify or "fix" cache settings — there's nothing to tune; the report is diagnostic only.
- Compare across sessions — one session at a time. Run multiple times for different sessions.
- Compute absolute dollar costs — only relative savings vs the no-cache baseline.
