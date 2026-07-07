# Harness Stats

User-level tooling for measuring whether the specialist constellation is using prompt caching efficiently. Two artifacts:

| Artifact | Purpose | Where it lives once installed |
|---|---|---|
| `statusline.sh` | Live statusline showing project, branch, parent model + context %, session-wide token totals and list-price API cost, aggregate cache hit %, last-finished agent (with its cumulative tool count vs the SDK ceiling on subagents), conditional hot-agent and parallel-fan-out indicators. | `~/.claude/statusline.sh` |
| `cache-report.sh` | On-demand per-agent breakdown: runs, median turns, warm-start %, in-run reuse %, net savings vs no-cache baseline. | `~/.claude/cache-report.sh` |
| `skills/cache-report/SKILL.md` | Skill that invokes `cache-report.sh` and interprets the output. | `~/.claude/skills/cache-report/SKILL.md` |

Both scripts read Claude Code transcripts from `~/.claude/projects/<encoded-cwd>/<session>.jsonl` and the per-session subagent transcripts in `<session>/subagents/`. They aggregate across the parent transcript plus every subagent transcript for one session.

## Why This Exists

The harness fires specialist agents (`pipeline-coordinator`, `feature-implementer`, the four reviewers, etc.) many times per feature. Each fire writes its system prompt and instructions to cache at the TTL-split write premium (Claude Code writes at 1-hour TTL, 2.0×); subsequent fires within that TTL serve the prefix from cache at the 0.10× read price. The constellation is cache-efficient when fires are clustered tightly enough that the write premium gets amortized across many reads.

The tooling answers two questions that aren't visible from the chat UI:

- **Is the cache actually paying off this session?** Net savings vs no-cache baseline, hit %, total tokens by category.
- **Which agents are paying off and which aren't?** Per-agent warm-start %, in-run reuse %, net savings %. An agent firing sporadically with a low warm-start % may be costing more than it saves.

## Dependencies

Both scripts assume a POSIX shell environment with: **bash 3.2+** (macOS system bash works), **jq**, **git**, **awk**, **find** (GNU or BSD), and a working **stat** (GNU `-c` or BSD `-f`, the script falls back automatically). On Windows the scripts target **WSL** or **Git Bash / MSYS2**; native cmd.exe and PowerShell cannot run them. Install `jq` if it's missing — every metric is computed from JSON via jq, and the statusline degrades to mostly-empty output without it.

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

Each cell that introduces a value leads with an icon and one space, so the line reads as a row of labeled pieces. Mid-cell totals (▲▼⊖⊕) stay glued to their numbers. Read left to right:

- `⎇` — project and git branch
- `▤` — parent model and context-window %
- `Σ` — session tokens (`▲` in, `▼` out) and `$` API cost
- `⛁` — cache hit %, tokens read (`⊖`) / written (`⊕`), and `$%` savings
- `⇲` — MCP calls and busiest server (only when MCP is used)
- `⇉` — agents running in parallel
- `⟳` — session-wide continuation total (only when agent teams is on)
- `↺` — last-finished agent: `⊕` creation tokens, `⚒` tool count, `⟳` continues
- `↗` — a parallel agent nearing the tool cap (only when one is at risk)

The cells below carry color bands and conditional behavior; the table after the examples gives the detail.

Solo work, normal turn (main session — no SDK ceiling applies):

```
sample ⎇ main │ opus ▤ 32% │ Σ ▲277.4M ▼875k $168.20 │ ⛁ 98% ⊖272.2M ⊕5.1M $91% │ ⇉ 0 │ ↺ main ⊕272 ⚒85
```

Parallel fan-out with one subagent approaching the SDK ceiling:

```
sample ⎇ main │ opus ▤ 42% │ Σ ▲1.2M ▼34k $3.84 │ ⛁ 92% ⊖800k ⊕400k $27% │ ⇉ 3 │ ↺ Plan ⊕12k ⚒22 │ ↗ Explore ⚒58 ⚠
```

Full harness on a sample project (agent teams enabled) — every cell in play: MCP calls in flight (`⇲`), a session-wide continuation total (`⟳ 9` beside `⇉`), a reviewer re-engaged twice (`↺ doc-reviewer … ⟳2`, dim — under the threshold), and the hot implementer re-engaged seven times (`↗ … ⟳7`, yellow) with its `⚒54` cap color dimmed because the continues are driving it, not a stuck loop:

```
sample ⎇ main │ opus ▤ 47% │ Σ ▲4.2M ▼91k $11.40 │ ⛁ 95% ⊖3.9M ⊕210k $84% │ ⇲ 12 context7·8 │ ⇉ 3 │ ⟳ 9 │ ↺ doc-reviewer ⊕9k ⚒18 ⟳2 │ ↗ feature-implementer ⚒54 ⟳7
```

The `⟳` cells appear only when agent teams is enabled (it is in all three samples, via `.claude/settings.json`); on a non-team session the global `⟳` cell is suppressed, and the `↺`/`↗` cells render without their trailing `⟳` and with the `⚒` cap color/`⚠` alarm normally.

| Section | Meaning |
|---|---|
| `sample ⎇ main` | Project (cwd basename) and current git branch. |
| `opus ▤ 32%` | Parent model + context-window usage %, read straight from the Claude Code stdin payload (`model.display_name`, `context_window.used_percentage`). `▤` marks the cell as "context window." Color-coded: green <50% (comfortable), yellow 50–75% (plan to compact), red ≥75% (act now). A trailing `⚠` fires when context crosses the model-specific autocompact threshold (~83% on 200K models, ~95% on 1M). |
| `Σ ▲277.4M ▼875k $168.20` | `Σ` = session-wide aggregate. Input (▲, sent to API) and output (▼, received from API) token totals, summed across the parent transcript and every subagent transcript. `$N.NN` is the list-price API cost of that token volume, priced per assistant turn by model **family** (Fable 5 $10/$50, every served Opus tier $5/$25, Sonnet 4.x $3/$15, Haiku 4.5 $1/$5 per MTok) so a mixed fleet (Opus main + Haiku subagents) is costed correctly. Sonnet 5 is the one per-model override: its introductory $2/$10 (through 2026-08-31) is matched ahead of the generic Sonnet rate, and reverts to $3/$15 on 2026-09-01 (a manual edit flagged in `statusline.sh`). Cache reads are billed at 0.10× input, 5-minute cache writes at 1.25×, 1-hour writes at 2.0×, read from the `cache_creation` 5m/1h split when present. These are list API prices — for Max/Pro subscription users the figure is a notional "what this would cost on the API," not a bill. Prices live in the `PRICE_*` / `CACHE_*_MULT` constants at the top of `statusline.sh`; update them when Anthropic changes pricing. Distinct from the cache cell's `$ ±N%` (a savings *ratio*, always `%`-suffixed) — this `$` is absolute spend with a decimal. |
| `⛁ 98% ⊖272.2M ⊕5.1M $87%` | `⛁` = cache. Aggregate hit %, total tokens read from cache (`⊖`), total tokens written to cache (`⊕`), and cache savings vs a no-cache baseline (`$`). Hit % is color-coded: green ≥90%, yellow ≥75%, red <75%. The `$N%` savings metric evaluates the cache-eligible portion only (regular input excluded): `(baseline − actual) / baseline × 100`, where baseline is the read + write tokens priced as plain input, and actual prices reads at 0.10×, **5-minute** writes at 1.25×, and **1-hour** writes at 2.0×. Writes are split by TTL because they price differently — Claude Code writes its prefix cache at **1h** (2.0×), so the cell reads the real `cache_creation` 5m/1h split rather than assuming all writes are 1.25× (which overstated savings, and on write-heavy turns could show green while the cache was actually costing money). **Positive = good:** `$N%` cut N% of cache-eligible spend (paying off), `$-N%` added N% (cache costing money — writes outpacing reads, typically a fresh prefix or heavy invalidation), `$0%` break-even. Color carries the magnitude band: green ≥30% / yellow 10–29% / dim 0–9% / red <0%. Suppressed entirely when there's no cache activity. A drop from `$87%` to a negative value turn-over-turn is the cleanest cache-bust signal. The multipliers live in the `CACHE_*_MULT` constants at the top of `statusline.sh`; the `$` glyph is a topic anchor (savings ratio), not a locale assertion. |
| `⇲ 12 context7·8` | `⇲` = MCP usage. Conditional cell — shown only when the session made at least one MCP tool call. Leads with the session-wide total MCP calls (parent + every subagent, counted from `tool_use` blocks named `mcp__<server>__<tool>`), then the busiest server and its share as `server·N`. Server name truncated with the same helper as the agent cells. Suppressed entirely on MCP-free sessions, so it never shows for projects that don't call MCP servers. |
| `⇉ 3` | `⇉` = parallel fan-out. Count of subagents whose `meta.json` was modified in the last 5 minutes — the raw fan-out width, so three concurrent agents of the same type read as `⇉ 3`, matching the agent selector. Always shown (even at 0) so the line's layout stays stable across solo and fan-out states. |
| `⟳ 9` | Global continuation total — the session-wide sum of accepted `SendMessage` continues across all agents (same accepted-only counting as the per-agent `⟳` below; reuses the same single parent-transcript parse). Sits in the aggregate row beside `⇉`, styled icon-space-value like the other aggregates. Always shown (even at 0) when agent teams is on — layout stability, and a visible confirmation that continuation tracking is live; suppressed entirely when teams is off, where no continues can exist. A session sum runs higher than any single agent's, so it carries its own bands: dim ≤15 / yellow >15 / red >30 (`CONT_GLOBAL_YELLOW` / `CONT_GLOBAL_RED`). |
| `↺ main ⊕272 ⚒85` | `↺` = previous turn. `main` for the parent, otherwise the `agentType` of the subagent. `⊕N` is `cache_creation_input_tokens` in that turn (reuses the cache-creation glyph), color-coded dim <25k / yellow ≥25k (likely mid-session prefix invalidation) / red ≥100k (a single turn rebuilt a chunk comparable to a full prefix). `⚒N` is the *cumulative* tool-use count across the invocation, matching Claude's done-report number — rises monotonically while the agent works. For subagents the count is color-coded against `TOOLS_PER_RESPONSE_CAP` (the SDK ceiling on cumulative tool calls per subagent invocation): dim <67% / yellow <90% / red ≥90% of cap, with ⚠ when the cap was hit (subagent truncated). The cap value lives in the script, not the display, so the runtime-specific number doesn't leak into user-visible text. For the main session the color stays dim and the ⚠ is suppressed — main isn't subject to the ceiling and routinely runs hundreds of cumulative tool calls. When the agent has landed continues (see `⟳` below), the `⚒` cap color and `⚠` drop to dim — an actively-continued agent's tool count is coordinator-driven, not a stuck-mid-loop signal. |
| `↗ Explore ⚒58 ⚠` | `↗` = trending up toward the cap. Conditional cell — appears only when a *different* parallel subagent's cumulative tool count crosses the yellow threshold *and* its meta.json was touched within the active window (same 5-minute filter as `⇉`). Names the at-risk agent so you know who to redirect. Suppressed in solo work, when the last-fired agent IS the hottest, when the candidate finished more than the active window ago, and for the main session (which isn't capped). Carries the same `⟳` cell and cap-suppression as `↺`. |
| `⟳3` | `⟳` = accepted continues (per-agent). Trails the `↺` and `↗` cells: the count of **non-blocked** `SendMessage` continues the coordinator sent to that agent this session — re-engagements for review remediation or consultation routing, *not* the SDK's intra-turn auto-continuation. Counted from the parent transcript's `SendMessage` tool-use blocks joined to the agent's `agentId` (the `agent-<agentId>.jsonl` filename); sends that were rejected (target exited, unknown recipient) carry an `is_error` tool-result and are subtracted, so the figure reflects landed re-engagements only. Bands are absolute counts (continues are sparse): dim ≤5 / yellow >5 / red >10. Hidden at 0, so it lights up only during sustained back-and-forth — a high count flags a slice grinding through repeated rounds. Thresholds live in the `CONT_YELLOW` / `CONT_RED` constants. **Gated on agent teams:** the whole `⟳` path — including the parent-transcript scan it requires — is active only when Claude Code's experimental agent-teams capability is on, since `SendMessage` continues exist only then. Detection checks the `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` env var, then falls back to the `env` block of `.claude/settings.json` (project, then `settings.local.json`, then `~/.claude/`) — so the cell works whether teams is enabled by shell export or by a settings file, without depending on the env var being forwarded into the statusline subprocess. Sessions with teams off skip the scan entirely. |

Context thresholds track Anthropic team guidance for 200K models (proactive-compact at 50–60%, autocompact at ~83%). Tool-count thresholds are percentages of the cap so they auto-scale if Anthropic changes it. The constants `CTX_GREEN`, `CTX_YELLOW`, `CTX_AUTOCOMPACT_200K`, `CTX_AUTOCOMPACT_1M`, `CREATION_YELLOW`, `CREATION_RED`, `SAVINGS_GREEN`, `SAVINGS_YELLOW`, `TOOLS_PER_RESPONSE_CAP`, `TOOLS_YELLOW_PCT`, `TOOLS_RED_PCT`, `CONT_YELLOW`, `CONT_RED`, `CONT_GLOBAL_YELLOW`, `CONT_GLOBAL_RED`, the `PRICE_*` per-family rates, and the `CACHE_*_MULT` cache multipliers all live at the top of `statusline.sh`. 1M-context users may want to tighten the CTX values, since quality degrades on absolute tokens, not percentage.

The statusline caches its aggregates per session keyed by transcript mtimes, so the hot path is 7ms warm (about 120ms cold on a 4.8 MB transcript). Cache files live at `${XDG_CACHE_HOME:-~/.cache}/claude-statusline/claude-statusline-<session>.cache` — one per session, in a mode-700 directory. A private cache dir (not a shared `/tmp`) keeps other local users from planting or poisoning a predictable-name cache file whose body is echoed to the terminal. Files older than `CACHE_TTL_MIN` (default 7 days) are auto-swept on the next cache miss in any session, so no manual cleanup is required. Active sessions never expire (each cache write refreshes the mtime); resuming a long-idle session costs one 120ms cold render before it's warm again.

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
| **Warm-start %** | Avg of `cache_read / total_input` on each fire's first turn, across all fires of an agent type | Are fires clustered within the cache TTL (1 hour for Claude Code's writes) so the system prompt + instructions get reused across invocations? |
| **In-run reuse %** | `sum(cache_read on turns 2+) / sum(total_input on turns 2+)`, per agent type | Is the prefix stable across turns within a single fire? |
| **Net savings %** | `1 − actual_cost / no_cache_baseline_cost`, where `actual = uncached×1.00 + write_5m×1.25 + write_1h×2.0 + read×0.10` and `baseline = (uncached + writes + read) × 1.00` | Did the cache save money for this agent, or did the TTL-split write premium exceed the 0.10× read savings? Negative = waste. |

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

If you smoke-test on macOS and find friction, the most likely culprits are `jq` not being installed (`brew install jq`) or a `stat`/`find` call that needs a different fallback. Paste the error; the helpers at the top of each script are the place to patch.

## Pricing Multipliers

Both the statusline `$` savings cell and the cache-report Net savings % use these input-token price ratios (relative to base uncached input):

- Cache write, 5-minute TTL: **1.25×**
- Cache write, 1-hour TTL: **2.00×**
- Cache read: **0.10×**
- Uncached input: **1.00×**

These are Anthropic's published multipliers as of 2026-07. The absolute base price is not needed because only the ratio against the no-cache baseline matters — but the **write multiplier depends on TTL**, and Claude Code writes its prefix cache at 1-hour TTL (verified from transcripts: 100% of cache writes carry `ephemeral_1h_input_tokens`, zero 5-minute). Both tools read the real per-turn 5m/1h split from `usage.cache_creation` and price each accordingly; collapsing all writes to 1.25× overstated savings and, on write-heavy turns, could show a positive savings figure while the cache was actually costing money. The multipliers live in `CACHE_WRITE_5M_MULT` / `CACHE_WRITE_1H_MULT` / `CACHE_READ_MULT` (`statusline.sh`) and `CREATE_MULT_5M` / `CREATE_MULT_1H` / `READ_MULT` (`cache-report.sh`) — keep the two sets in sync.

## Related

- [`docs/agentic-harness.md`](../../docs/agentic-harness.md) — how the constellation is structured and why repeated specialist fires are expected.
- The `cache-report` skill — once installed, ask Claude "show cache report" or "how's the cache doing" to invoke it.
