# Harness Stats

User-level tooling for measuring whether the specialist constellation is using prompt caching efficiently. Two artifacts:

| Artifact | Purpose | Where it lives once installed |
|---|---|---|
| `statusline.sh` | Live statusline showing project, branch, session-wide token totals, aggregate cache hit %, last fired agent, and active-agent count. | `~/.claude/statusline.sh` |
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

```
agentic-coding-reference ⎇ main │ ▲277.4M ▼875k │ cache 98% ⊖272.2M ⊕5.1M │ last: main +272 │ 0 active
```

| Section | Meaning |
|---|---|
| `agentic-coding-reference ⎇ main` | Project (cwd basename) and current git branch. |
| `▲277.4M ▼875k` | Session-wide input (▲, sent to API) and output (▼, received from API) token totals, summed across the parent transcript and every subagent transcript. |
| `cache 98% ⊖272.2M ⊕5.1M` | Aggregate cache hit %, total tokens read from cache (`⊖`), total tokens written to cache (`⊕`). Hit % is color-coded: green ≥90%, yellow ≥75%, red <75%. |
| `last: main +272` | Most recent assistant turn — `main` for the parent, otherwise the `agentType` of the subagent. `+N` is the `cache_creation_input_tokens` in that turn; the `⚠` marker appears when this exceeds 5k (signal of prefix invalidation). |
| `0 active` | Distinct agent types whose `meta.json` was modified in the last 5 minutes. |

The statusline caches its aggregates per session keyed by transcript mtimes, so the hot path is 7ms warm (about 120ms cold on a 4.8 MB transcript).

## Cache Report Output

```
$ ~/.claude/cache-report.sh
Cache report session c6e96b49…

Session
  Tokens:     uncached-in 95.8k  cache-create 2.9M  cache-read 106.0M  out 361.5k
  Hit ratio:  97%   Net savings vs no-cache: +87%

Per-agent breakdown
  Agent                           Runs  Median   Warm-start       In-run  Net savings
                                         turns            %      reuse %            %
  ───────────────────────────────────────────────────────────────────────────────────
  main                               1   254.0    49%             99%          +89%
  feature-implementer                3    96.0    10%             98%          +87%
  system-design-expert               2    38.5    13%             95%          +84%
  test-reviewer                      2    40.5    19%             91%          +80%
  product-requirements-expert        1    46.0     0%             92%          +81%
  code-quality-reviewer              1    61.0     0%             95%          +84%
  security-reviewer                  1    57.0     0%             95%          +83%

Findings
  • feature-implementer fired 3× with only 10% warm-start — fires too spread out to amortize
  • system-design-expert fired 2× with only 13% warm-start — fires too spread out to amortize
  • 3 single-fire agents (product-requirements-expert, code-quality-reviewer, security-reviewer) paid the write premium with no follow-up fire to read from cache
```

The output is structured as three sections answering distinct questions:

| Section | Question it answers |
|---|---|
| **Session** | Is the cache paying off this session overall? |
| **Per-agent breakdown** | Which agents pay off and which don't? |
| **Findings** | What's actionable? — auto-generated from the rules in the "When to act" table below. Empty findings means everything is amortizing as expected. |

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
