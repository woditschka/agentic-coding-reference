# Harness Stats

User-level tooling for measuring whether the specialist constellation is using prompt caching efficiently. Two artifacts:

| Artifact | Purpose | Where it lives once installed |
|---|---|---|
| `statusline.sh` | Live statusline showing project, branch, parent model + context %, session-wide token totals, aggregate cache hit %, last-finished agent (with its tool count vs the per-response cap), conditional hot-agent and parallel-fan-out indicators. | `~/.claude/statusline.sh` |
| `cache-report.sh` | On-demand per-agent breakdown: runs, median turns, warm-start %, in-run reuse %, net savings vs no-cache baseline. | `~/.claude/cache-report.sh` |
| `skills/cache-report/SKILL.md` | Skill that invokes `cache-report.sh` and interprets the output. | `~/.claude/skills/cache-report/SKILL.md` |

Both scripts read Claude Code transcripts from `~/.claude/projects/<encoded-cwd>/<session>.jsonl` and the per-session subagent transcripts in `<session>/subagents/`. They aggregate across the parent transcript plus every subagent transcript for one session.

## Why This Exists

The harness fires specialist agents (`pipeline-coordinator`, `feature-implementer`, the four reviewers, etc.) many times per feature. Each fire writes its system prompt and instructions to cache at the 1.25× write premium; subsequent fires within the 5-minute TTL serve that prefix from cache at the 0.10× read price. The constellation is cache-efficient when fires are clustered tightly enough that the write premium gets amortized across many reads.

The tooling answers two questions that aren't visible from the chat UI:

- **Is the cache actually paying off this session?** Net savings vs no-cache baseline, hit %, total tokens by category.
- **Which agents are paying off and which aren't?** Per-agent warm-start %, in-run reuse %, net savings %. An agent firing sporadically with a low warm-start % may be costing more than it saves.

## Installation

### Recommended: via the setup skill

If you're working inside this repo, run the project skill:

```
/harness-stats-setup
```

The skill detects drift between the repo's copies and any existing `~/.claude/` installation, shows what would change, and applies the install on approval. It also merges the `statusLine` block into `~/.claude/settings.json` without touching other keys.

### Manual

```bash
cp tools/harness-stats/statusline.sh   ~/.claude/statusline.sh
cp tools/harness-stats/cache-report.sh ~/.claude/cache-report.sh
mkdir -p ~/.claude/skills/cache-report
cp tools/harness-stats/skills/cache-report/SKILL.md ~/.claude/skills/cache-report/SKILL.md
chmod +x ~/.claude/statusline.sh ~/.claude/cache-report.sh
```

Then add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "/home/<you>/.claude/statusline.sh",
    "padding": 1
  }
}
```

Restart Claude Code for the statusline and skill to load.

## Statusline Format

Each cell that introduces a value leads with an icon and one space, so the line reads as a row of labeled pieces. Mid-cell totals (▲▼⊖⊕) stay glued to their numbers.

Solo work, normal turn:

```
agentic-coding-reference ⎇ main │ opus ▤ 32% │ Σ ▲277.4M ▼875k │ ⛁ 98% ⊖272.2M ⊕5.1M │ ⇉ 0 │ ↺ main ⊕272 ⚒1/60
```

Parallel fan-out with one subagent approaching the per-response tool cap:

```
agentic-coding-reference ⎇ main │ opus ▤ 42% │ Σ ▲1.2M ▼34k │ ⛁ 92% ⊖800k ⊕400k │ ⇉ 3 │ ↺ Plan ⊕12k ⚒22/60 │ ⚡ Explore ⚒58/60 ⚠
```

| Section | Meaning |
|---|---|
| `agentic-coding-reference ⎇ main` | Project (cwd basename) and current git branch. |
| `opus ▤ 32%` | Parent model + context-window usage %, read straight from the Claude Code stdin payload (`model.display_name`, `context_window.used_percentage`). `▤` marks the cell as "context window." Color-coded: green <50% (comfortable), yellow 50–75% (plan to compact), red ≥75% (act now). A trailing `⚠` fires when context crosses the model-specific autocompact threshold (~83% on 200K models, ~95% on 1M). |
| `Σ ▲277.4M ▼875k` | `Σ` = session-wide aggregate. Input (▲, sent to API) and output (▼, received from API) token totals, summed across the parent transcript and every subagent transcript. |
| `⛁ 98% ⊖272.2M ⊕5.1M` | `⛁` = cache. Aggregate hit %, total tokens read from cache (`⊖`), total tokens written to cache (`⊕`). Hit % is color-coded: green ≥90%, yellow ≥75%, red <75%. |
| `⇉ 3` | `⇉` = parallel fan-out. Count of distinct agent types whose `meta.json` was modified in the last 5 minutes. Always shown (even at 0) so the line's layout stays stable across solo and fan-out states. |
| `↺ main ⊕272 ⚒1/60` | `↺` = previous turn. `main` for the parent, otherwise the `agentType` of the subagent. `⊕N` is `cache_creation_input_tokens` in that turn (reuses the cache-creation glyph; ⚠ fires when >5k — prefix invalidation). `⚒N/60` is the tool-use count vs `TOOLS_PER_RESPONSE_CAP`, color-coded green <67% / yellow <90% / red ≥90% of cap, with ⚠ when the cap was hit (response truncated). |
| `⚡ Explore ⚒58/60 ⚠` | `⚡` = spike/alert. Conditional cell — appears only when a *different* parallel agent's most-recent turn crosses the yellow tool-count threshold. Names the at-risk agent so you know who to redirect. Suppressed in solo work and when the last-fired agent IS the hottest. |

Context thresholds track Anthropic team guidance for 200K models (proactive-compact at 50–60%, autocompact at ~83%). Tool-count thresholds are percentages of the cap so they auto-scale if Anthropic changes it. The constants `CTX_GREEN`, `CTX_YELLOW`, `CTX_AUTOCOMPACT_200K`, `CTX_AUTOCOMPACT_1M`, `TOOLS_PER_RESPONSE_CAP`, `TOOLS_YELLOW_PCT`, and `TOOLS_RED_PCT` all live at the top of `statusline.sh` — 1M-context users may want to tighten the CTX values since quality degrades on absolute tokens, not %.

The statusline caches its aggregates per session keyed by transcript mtimes, so the hot path is 7ms warm (about 120ms cold on a 4.8 MB transcript). Cache files live at `/tmp/claude-statusline-<session>.cache` — one per session. Files older than `CACHE_TTL_MIN` (default 7 days) are auto-swept on the next cache miss in any session, so no manual cleanup is required. Active sessions never expire (each cache write refreshes the mtime); resuming a long-idle session costs one 120ms cold render before it's warm again.

## Cache Report Output

```
$ ~/.claude/cache-report.sh
Cache report session c6e96b49…

Session
  Tokens:     ▼114.7M ▲376.3k  cache ⊕2.9M ⊖111.7M
  Hit ratio:  97%   Net savings vs no-cache: +87%

Per-agent breakdown
  Agent                           Runs Median turns Warm-start % In-run reuse % Net savings %        ▼        ⊕        ⊖
  ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  main                               1        274.0          49%            99%          +89%   ▼49.7M  ⊕550.1k   ⊖49.1M
  feature-implementer                3         96.0          10%            98%          +87%   ▼38.7M  ⊕869.8k   ⊖37.9M
  system-design-expert               2         38.5          13%            95%          +84%    ▼8.1M  ⊕443.3k    ⊖7.7M
  doc-reviewer                       1         76.0          26%            96%          +85%    ▼6.3M  ⊕260.2k    ⊖6.0M
  test-reviewer                      2         40.5          19%            91%          +80%    ▼3.9M  ⊕299.3k    ⊖3.6M
  product-requirements-expert        1         46.0           0%            92%          +81%    ▼3.1M  ⊕244.0k    ⊖2.9M
  code-quality-reviewer              1         61.0           0%            95%          +84%    ▼2.8M  ⊕135.7k    ⊖2.6M
  security-reviewer                  1         57.0           0%            95%          +83%    ▼2.1M  ⊕112.6k    ⊖2.0M
```

The trailing three columns mirror the statusline's compact vocabulary: ▼ total input the agent processed, ⊕ tokens it wrote to cache, ⊖ tokens it read from cache. ⊖ ≫ ⊕ means the writes amortized (each `⊕1` was read back ⊖N times); ⊕ ≈ ⊖ means writes barely paid for themselves.

The script emits measurement only — no interpretation. When invoked through the [`cache-report` skill](skills/cache-report/SKILL.md), the LLM reads the table and adds a `Findings` section that weighs the metrics against each other (volume × efficiency) and against pipeline context (which agents are one-shot by design). Running the script directly gives you the raw table; running the skill gives you the table plus analysis.

The output is structured as two measurement sections; the skill adds a third on top:

| Section | Source | Question it answers |
|---|---|---|
| **Session** | script | Is the cache paying off this session overall? |
| **Per-agent breakdown** | script | Which agents pay off and which don't? |
| **Findings** | skill (LLM) | What's actionable? — weighs the signals below by volume and pipeline context. |

### Metric definitions

| Metric | Formula | What it tells you |
|---|---|---|
| **Warm-start %** | Avg of `cache_read / total_input` on each fire's first turn, across all fires of an agent type | Are fires clustered within the 5-minute TTL so the system prompt + instructions get reused across invocations? |
| **In-run reuse %** | `sum(cache_read on turns 2+) / sum(total_input on turns 2+)`, per agent type | Is the prefix stable across turns within a single fire? |
| **Net savings %** | `1 − actual_cost / no_cache_baseline_cost`, where `actual = uncached×1.00 + write×1.25 + read×0.10` and `baseline = (uncached + write + read) × 1.00` | Did the cache save money for this agent, or did the 1.25× write premium exceed the 0.10× read savings? Negative = waste. |

### When to act

| Signal | What it means | Action |
|---|---|---|
| Negative Net savings % on any row | Cache cost more than it saved for that agent — wrote more than the reads recouped | Cluster fires more tightly, or stop using that agent for one-shot work |
| Warm-start % < 40% on a multi-run agent | Fires are too spread out; cache expires between them | Increase fire frequency or accept the cost as inherent |
| In-run reuse % < 70% | Prefix is being invalidated mid-fire | Investigate file re-reads with changed content, tool result ordering, or `/compact` events |
| Aggregate hit % < 75% | Session-wide cache misses are significant | If mid-session, may just be warming up; if long-running, structural issue |

## Coverage

What's included in the aggregation for a given parent session:

- The parent transcript (`<session_id>.jsonl`).
- Every subagent transcript in `<session_id>/subagents/agent-*.jsonl`. Verified across all local sessions: Claude Code stores subagent transcripts flat regardless of nesting depth in the spawn tree, so a single `find -maxdepth 1` catches them all.

What's not (intentionally):

- Skill invocations — they run inline; their usage is already attributed to the calling agent.
- `tool-results/` records — they're tool-call outputs, not assistant turns; the usage of consuming them lives on the assistant message that processed them.
- Other parent sessions — each parent session is its own scope.

## Dependencies

| Tool | Notes |
|---|---|
| `bash` | 3.2+ (macOS system bash supported; no associative arrays used) |
| `jq` | All JSON parsing |
| `awk` | Token formatting; standard on both BSD and GNU |
| `find`, `stat` | Cross-platform shims included for GNU/BSD differences |

## Platform Support

| Platform | Status |
|---|---|
| Linux | Tested |
| macOS | Should work (bash 3.2 path is exercised; GNU/BSD stat shims in place); not yet smoke-tested upstream |
| Windows WSL | Should work (Linux underneath) |
| Windows Git Bash | Should work (MSYS2 ships GNU coreutils) |
| Windows native (cmd/PowerShell) | Not supported |

If you smoke-test on macOS and find friction, the most likely culprits are `jq` not being installed (`brew install jq`) or a `stat`/`find` call that needs a different fallback — paste the error and the helpers at the top of each script are the place to patch.

## Pricing Multipliers

The Net savings % calculation uses these input-token price ratios (relative to base uncached input):

- Cache write: **1.25×**
- Cache read: **0.10×**
- Uncached input: **1.00×**

These are Anthropic's published multipliers as of 2026-05. The absolute base price is not needed because only the ratio against the no-cache baseline matters.

## Related

- [`docs/agentic-harness.md`](../../docs/agentic-harness.md) — how the constellation is structured and why repeated specialist fires are expected.
- The `cache-report` skill — once installed, ask Claude "show cache report" or "how's the cache doing" to invoke it.
