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

Runs `~/.claude/cache-report.sh` and analyzes the result. The script emits two sections of pure measurement:

- **Session** — total tokens by category (▼ input, ▲ output, ⊕ cache create, ⊖ cache read), hit %, and net savings vs no-cache baseline.
- **Per-agent breakdown** — runs, median turns, warm-start %, in-run reuse %, net savings %, plus token volume per agent (▼ ⊕ ⊖), one row per `agentType`.

The script does no interpretation; the analysis happens in this skill, which weighs the metrics against each other and against pipeline context to surface what's actually actionable.

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

### 2. Always show the script output verbatim

**Every invocation of this skill must include the full script output inside a fenced code block — Session + Per-agent breakdown, exactly as the script produced it.** Do not summarize, paraphrase, or skip rows. The user wants to read the raw table; your interpretation goes *on top of* the table, not instead of it.

The script auto-detects whether stdout is a TTY — when invoked through a tool wrapper (non-TTY), it emits plain text so the columns stay aligned; in an interactive terminal it adds ANSI bold/dim/color. Either way, no post-processing is needed.

### 3. Add a Findings section beneath the table

After the verbatim table, append a `**Findings**` heading followed by a short list of bullets (2-4 items, sometimes zero). Each finding names the agent(s), states what's wrong, and points at the actionable next step. Weigh metrics against each other and against pipeline context — don't mechanically restate the columns.

**Signals to look for** (treat as guidance, not a checklist — combine them where it makes sense):

| Signal | What it usually means | Suggested next step |
|---|---|---|
| Multi-run agent (`Runs ≥ 2`) with `warm-start < 40%` | Fires of that agent were too spread out within the 5-minute TTL to share cache across invocations. | Cluster fires more tightly, or accept the cost as inherent to that agent's role. |
| Single-run agent (`Runs == 1`) at `0% warm-start` | The agent fired once and paid the write premium with no follow-up to read from. If it runs once per feature by design (PRD authoring, gated quality reviews), this is structural and not actionable. Otherwise it points at an agent that should have fired earlier or more often. | Distinguish "by design" from "by accident" — most one-shot agents are intentional. Only flag if the agent type is one you'd expect to fire repeatedly. |
| Negative `Net savings %` on any row | Cache cost more than it saved — the 1.25× write premium exceeded the 0.10× read savings on that agent. | Stop using that agent for one-shot work, or batch its invocations. |
| Multi-turn agent (`median turns > 1`) with `in-run reuse < 70%` | The prefix is being invalidated within a single fire — file re-reads with changed content, tool result ordering, or `/compact` events mid-run. | Investigate what's churning the prefix mid-fire. |
| Session-wide `hit ratio < 75%` | Many session tokens missed the cache. If session is short, this is just warmup; if long, structural. | Note context (early session vs. long-running). |
| `⊕ ≈ ⊖` (cache writes ≈ cache reads on an agent) | The agent wrote roughly as much as it read — almost no amortization, even if warm-start % looks OK in aggregate. | Often pairs with low warm-start or single-fire pattern; flag as a volume-weighted concern. |

**How to weigh findings:**

- **Volume matters.** A low warm-start % on an agent with `▼50M` is far more important than the same % on an agent with `▼500k`. Don't list every threshold-crossing row — list the ones whose volume × inefficiency adds up to real cost.
- **Compress redundancy.** If three agents trip the same rule for the same reason (e.g., wide TDD cycle spacing causes warm-start ≤ 20% across implementer/sde/reviewer), emit one finding about the underlying cause, not three near-identical lines.
- **Use pipeline context.** Pin which one-shot agents are structural (run once per feature by design — e.g., PRD authoring, gated reviewers, security review) and don't flag those as anomalies even if their warm-start is 0%.
- **Stay short.** A debug command should produce insight, not prose. If everything looks healthy, say "All agents amortize their writes — nothing actionable" in one line and stop.

Format each finding as a bullet under a `**Findings**` heading. Don't fabricate concerns the data doesn't support.

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
