#!/usr/bin/env bash
# Statusline: project, branch, parent model + context %, session-wide token
# totals across parent + subagents, aggregate cache hit %, a conditional
# MCP-usage cell (session-wide total calls + busiest server), an always-on
# parallel-fan-out indicator (⇉N), a global SendMessage-continuation total
# (⟳N, shown when agent teams is on), last-finished agent (with its cumulative
# tool count — bare for main, vs the SDK ceiling for subagents), and a
# conditional hot-agent cell for parallel subagents approaching the ceiling.
#
# Reads Claude Code JSON from stdin. Caches aggregates per-session keyed by
# transcript mtimes so the hot path is fast even on multi-MB transcripts.

# `set -e` deliberately omitted: the script degrades gracefully when jq, git,
# or transcript files are missing. A failed component yields a minimal
# statusline (e.g. branch "-", agent "?"), never a blank one.
set -uo pipefail

# Force a period decimal separator for awk/printf number formatting (the $ cost
# cell's %.2f and fmt_tokens' %.1f). On comma-radix locales (e.g. de_DE.UTF-8)
# they would otherwise render "10,43" / "1,2M". Only LC_NUMERIC is pinned — not
# LC_CTYPE — so multibyte agent-name truncation (${#name}) still counts
# characters, not bytes. (A user who exports LC_ALL overrides this; rare.)
export LC_NUMERIC=C

# Subagent meta files modified within this window count toward the parallel
# fan-out count (⇉ N cell, always shown — even at 0 — for layout stability).
ACTIVE_WINDOW_SEC=300

# Cache-hit thresholds. Mature Claude Code sessions with a stable prefix sit
# ≥90%; 75–90% is normal early-session ramp-up or moderate prefix churn;
# <75% signals real cache misses.
HIT_GREEN=90
HIT_YELLOW=75

# Cache-savings thresholds — color bands for the $N% savings cell (% reduction
# in cache-eligible spend vs a no-cache baseline). The figure itself is computed
# by accounting.py (the single pricing source); these bands only color it.
# Positive = saved; below 0 fires red — writes are outpacing reads, the cache is
# costing money (usually heavy invalidation: model switch, prompt churn, limits).
SAVINGS_GREEN=30
SAVINGS_YELLOW=10

# Parent-context-usage thresholds. Below CTX_GREEN: comfortable (Anthropic
# team's "compact proactively" zone). CTX_GREEN to CTX_YELLOW: plan to compact.
# Above CTX_YELLOW: act now (autocompact imminent on 200K models). Defaults
# track Anthropic team guidance for 200K models; 1M-context users may want
# tighter values since quality degrades on absolute tokens, not %.
CTX_GREEN=50
CTX_YELLOW=75

# Per-model autocompact triggers. The ⚠ marker fires when context crosses
# these thresholds. 200K models autocompact at ~83.5%; 1M models at ~95%.
CTX_AUTOCOMPACT_200K=83
CTX_AUTOCOMPACT_1M=95

# Creation-tokens-in-last-turn thresholds for the ⊕ cell in the ↺ section.
# Yellow (≥25k) clears the typical subagent startup floor (tool schemas +
# system prompt + agent definition), so it doesn't fire on every fan-out and
# instead flags a likely mid-session prefix invalidation. Red (≥100k) is
# severe — a single turn just rebuilt a chunk comparable to a full session
# prefix (large file re-read, /compact aftermath, tool-list mutation).
CREATION_YELLOW=25000
CREATION_RED=100000

# SDK ceiling — cumulative tool-use cap per subagent invocation. Claude Code
# auto-continues an assistant message past the per-message limit by chaining
# small messages, so the practical limit is on the sum across all assistant
# messages in one invocation, not on any single message. The statusline colors
# the cumulative count against this cap and fires ⚠ on hit. Thresholds are
# percentages of the cap so they auto-scale if Anthropic changes it — bump
# only TOOLS_PER_RESPONSE_CAP.
TOOLS_PER_RESPONSE_CAP=60
TOOLS_YELLOW_PCT=67   # substantial run; agent has done real work
TOOLS_RED_PCT=90      # approaching the SDK auto-continuation point

# Continuation thresholds for the ⟳ cells — accepted (non-blocked) SendMessage
# continues: coordinator-driven re-engagements, not the SDK's intra-turn
# auto-continuation. Bands are absolute (continues are sparse). The per-agent
# cells (↺/↗) use CONT_YELLOW/RED; the global aggregate carries its own higher
# bands — a session sum crosses the per-agent thresholds trivially.
CONT_YELLOW=5
CONT_RED=10
CONT_GLOBAL_YELLOW=15
CONT_GLOBAL_RED=30

# Agent name truncation length for the ↺ (last) and ↗ (hot) cells.
AGENT_NAME_MAX=18

# Cache files older than this many minutes are swept on the next cache miss.
# Default is 7 days. Inactive sessions get a 120ms cold render on resume,
# active sessions never expire (each cache write refreshes the mtime).
CACHE_TTL_MIN=10080

INPUT=$(cat)

CWD=$(jq -r '.workspace.current_dir // .cwd // ""' <<<"$INPUT")
SESSION_ID=$(jq -r '.session_id // ""' <<<"$INPUT")
TRANSCRIPT=$(jq -r '.transcript_path // ""' <<<"$INPUT")

PROJECT=$(basename "$CWD")
BRANCH=$(git -C "$CWD" branch --show-current 2>/dev/null || true)
# Strip control characters: BRANCH is echoed straight to the terminal, and git
# ref names can carry bytes that would inject terminal escapes. Deletes C0/DEL
# control codes (incl. ESC) only — multibyte UTF-8 branch names survive intact.
BRANCH=$(printf '%s' "$BRANCH" | tr -d '[:cntrl:]')
[[ -z "$BRANCH" ]] && BRANCH="-"

SUB_DIR=""
if [[ -n "$TRANSCRIPT" && -n "$SESSION_ID" ]]; then
    SUB_DIR="$(dirname "$TRANSCRIPT")/$SESSION_ID/subagents"
fi

# Cross-platform mtime: GNU stat uses -c %Y, BSD/macOS uses -f %m.
mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0; }

# Cross-platform "max mtime among files matching find criteria". GNU find has
# -printf %T@ which is missing on BSD/macOS, so iterate and pick the max.
max_mtime() {
    local max=0 mt
    while IFS= read -r f; do
        mt=$(mtime "$f")
        (( mt > max )) && max=$mt
    done < <(find "$@" 2>/dev/null)
    echo "$max"
}

# Track parent mtime plus the latest subagent jsonl mtime. The dir mtime alone
# is insufficient: file-content appends to existing subagent transcripts don't
# update the parent dir's mtime, so the dir mtime alone would serve stale
# data during a multi-turn subagent run.
PARENT_MT=$(mtime "$TRANSCRIPT")
SUB_DIR_MT=$(mtime "$SUB_DIR")
if [[ -d "$SUB_DIR" ]]; then
    SUB_FILES_MT=$(max_mtime "$SUB_DIR" -maxdepth 1 -name "agent-*.jsonl" -type f)
else
    SUB_FILES_MT=0
fi

# Strip anything but alphanumerics and dashes from SESSION_ID before joining
# it into the cache path. SESSION_ID comes from JSON input; a hostile value
# containing `/` or `..` would otherwise let the cache escape the cache dir.
SAFE_SID="${SESSION_ID//[^a-zA-Z0-9-]/_}"
# The cache lives in the user's private cache dir, never a shared /tmp: a
# world-writable root with predictable names would let another local user
# pre-create the file (its body is echoed to the terminal — escape-sequence
# injection) or plant a symlink for the write below to follow.
# Resolution: XDG_CACHE_HOME when set to an absolute path (the XDG spec says
# to ignore relative values), else ~/.cache, else — when HOME is unset (some
# Git Bash setups on Windows) — a subdir of $TMPDIR, per-user on the
# platforms where that happens. The dir itself is created on the write path
# below, which refuses to cache at all when it cannot own the dir at mode
# 700 — the cache never lands flat in a shared temp root.
TMPROOT="${TMPDIR:-/tmp}"; TMPROOT="${TMPROOT%/}"
case "${XDG_CACHE_HOME:-}" in
    /*) CACHE_ROOT="$XDG_CACHE_HOME" ;;
    *)  CACHE_ROOT="${HOME:+${HOME}/.cache}"; CACHE_ROOT="${CACHE_ROOT:-$TMPROOT}" ;;
esac
CACHE_DIR="${CACHE_ROOT}/claude-statusline"
CACHE_FILE="${CACHE_DIR}/claude-statusline-${SAFE_SID}.cache"
# v16: cost/savings moved to the accounting module and the $ cell can be absent —
# the version bump invalidates lines rendered by the pre-module format.
CACHE_KEY="v16:${PARENT_MT}:${SUB_DIR_MT}:${SUB_FILES_MT}"

# Trust the cache only when this user owns both the dir and the file (-O is
# a builtin, so the hot path stays fork-free). The write gate further down
# proves ownership before writing; this check extends the same guarantee to
# the read, whose bytes go straight to the terminal. A pre-planted file is
# possible only when HOME and XDG_CACHE_HOME are both unset and the temp
# root is shared.
if [[ -f "$CACHE_FILE" && -O "$CACHE_FILE" && -O "$CACHE_DIR" ]] \
    && [[ "$(head -1 "$CACHE_FILE")" == "$CACHE_KEY" ]]; then
    tail -n +2 "$CACHE_FILE"
    exit 0
fi

# Agent-teams detection — gates the ⟳ cells and the continuation scan. Placed
# below the cache check so the hot path never pays for its settings.json reads.
# The env var is the documented toggle, but whether Claude Code forwards a
# settings.json `env` block into the statusline subprocess is undocumented, so
# fall back to reading the block straight out of settings.json (project then
# user scope) — deterministic regardless of forwarding. ${HOME:-} keeps the
# user-scope path safe under `set -u` when HOME is unset.
agent_teams_on() {
    case "${CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS:-}" in 1|true|TRUE) return 0 ;; esac
    local f val
    for f in "$CWD/.claude/settings.json" "$CWD/.claude/settings.local.json" "${HOME:-}/.claude/settings.json"; do
        [[ -f "$f" ]] || continue
        val=$(jq -r '.env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS // empty' "$f" 2>/dev/null)
        case "$val" in 1|true|TRUE) return 0 ;; esac
    done
    return 1
}
AGENT_TEAMS=0
agent_teams_on && AGENT_TEAMS=1

# Display the agent name, truncated to fit the statusline. Generic across projects.
# Strips control characters first: names derive from meta.json and MCP tool
# names and are echoed to the terminal, so unsanitized bytes could inject
# terminal escapes. Deletes C0/DEL only — multibyte UTF-8 names survive.
short_agent() {
    local name="$1"
    name=$(printf '%s' "$name" | tr -d '[:cntrl:]')
    [[ -z "$name" ]] && { echo "?"; return; }
    if (( ${#name} > AGENT_NAME_MAX )); then
        echo "${name:0:$((AGENT_NAME_MAX - 1))}…"
    else
        echo "$name"
    fi
}

# Format an integer token count as 1.2M / 34k / 567. awk -v keeps shell values
# out of the awk source, avoiding any chance of interpolation issues.
fmt_tokens() {
    awk -v n="$1" 'BEGIN {
        if (n >= 1e6)      printf "%.1fM", n/1e6
        else if (n >= 1e3) printf "%.0fk", n/1e3
        else               printf "%d", n
    }'
}

# Map a model display_name or ID to a short statusline label. Lowercase first
# to match Claude Code's "Opus 4.7" display name as well as raw "claude-opus-4-7".
short_model() {
    local lower
    lower=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    case "$lower" in
        *fable*)  echo "fable" ;;
        *opus*)   echo "opus" ;;
        *sonnet*) echo "sonnet" ;;
        *haiku*)  echo "haiku" ;;
        *)        echo "?" ;;
    esac
}

# The accounting module sits beside this script (install.sh copies both into
# ~/.claude/). It is the single source of the pricing table and the usage→cost
# math the handoff board also uses. Resolved here, invoked only on the miss path.
ACCT_MODULE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)/accounting.py"

# Collect transcript files: parent + all subagents in the matching session dir.
TRANSCRIPTS=()
[[ -f "$TRANSCRIPT" ]] && TRANSCRIPTS+=("$TRANSCRIPT")
if [[ -d "$SUB_DIR" ]]; then
    while IFS= read -r f; do
        TRANSCRIPTS+=("$f")
    done < <(find "$SUB_DIR" -maxdepth 1 -name "agent-*.jsonl" -type f 2>/dev/null)
fi

# ── Usage accounting: tokens, list-price cost, cache ───────────────────────
# Single source of truth: accounting.py owns the pricing table and the
# usage→cost/hit%/savings% math, so the statusline and the handoff board price
# identically. It runs ONLY here on the cache-miss path — the cache-hit path
# above never forks it — and does the whole usage aggregation in one process.
#
# Degradation: when python3 or the module is absent (or it errors), a
# pricing-free bash aggregation still fills the token + hit% cells; only cost ($)
# and savings (%), the two pricing-dependent cells, drop out. No pricing constant
# lives in this script — the portability invariant the board shares.
SESSION_COST=""
SAVINGS_PCT=""
ACCT=""
if [[ -n "$TRANSCRIPT" ]] && [[ -f "$ACCT_MODULE" ]] && command -v python3 >/dev/null 2>&1; then
    # -S skips site initialization (the module is pure stdlib), trimming
    # interpreter startup on this once-per-miss call.
    ACCT=$(python3 -S "$ACCT_MODULE" session --parent "$TRANSCRIPT" --session-id "$SESSION_ID" 2>/dev/null || true)
fi
ACCT_ROW=""
if [[ -n "$ACCT" ]]; then
    ACCT_ROW=$(jq -r '
        if type == "object" then
            [ (.total_input // 0), (.output // 0), (.cache_read // 0),
              (.cache_creation // 0), (.cost // 0), (.hit_pct // 0),
              (.savings_pct // "") ] | @tsv
        else empty end' <<<"$ACCT" 2>/dev/null || true)
fi
if [[ -n "$ACCT_ROW" ]]; then
    IFS=$'\t' read -r TOTAL_INPUT OUT_TOK CR_TOK CC_TOK _COST HIT_PCT SAVINGS_PCT <<<"$ACCT_ROW"
    # Format cost to the cent here; the module emits full precision.
    SESSION_COST=$(awk -v c="$_COST" 'BEGIN { printf "%.2f", c + 0 }')
else
    # Pricing-free fallback: sum the token counts across the transcript set and
    # compute the hit %. Cost and savings stay empty (no pricing in this script).
    if (( ${#TRANSCRIPTS[@]} > 0 )); then
        TOTALS=$(
            for f in "${TRANSCRIPTS[@]}"; do
                jq -c 'select(.type=="assistant") | .message.usage // empty' "$f" 2>/dev/null
            done | jq -s '
                reduce .[] as $u ({in:0, out:0, cr:0, cc:0};
                    .in += ($u.input_tokens // 0)
                    | .out += ($u.output_tokens // 0)
                    | .cr += ($u.cache_read_input_tokens // 0)
                    | .cc += ($u.cache_creation_input_tokens // 0))
                | "\(.in) \(.out) \(.cr) \(.cc)"
            ' 2>/dev/null
        )
        [[ -z "${TOTALS//[[:space:]\"]/}" ]] && TOTALS='"0 0 0 0"'
    else
        TOTALS='"0 0 0 0"'
    fi
    read -r IN_TOK OUT_TOK CR_TOK CC_TOK <<<"${TOTALS//\"/}"
    TOTAL_INPUT=$((IN_TOK + CR_TOK + CC_TOK))
    if (( TOTAL_INPUT > 0 )); then
        HIT_PCT=$(awk -v cr="$CR_TOK" -v total="$TOTAL_INPUT" 'BEGIN { printf "%.0f", cr * 100 / total }')
    else
        HIT_PCT=0
    fi
fi

# Find the most recent assistant turn across parent + subagents. The empty-array
# guard is necessary for bash 3.2 (macOS default): "${arr[@]}" on an empty
# array errors under `set -u`. Bash 4.4+ silently expands to nothing, but the
# script needs to render correctly on stock macOS too.
LAST_AGENT="-"
LAST_CREATION=0
LATEST_TS=""
LATEST_FILE=""
if (( ${#TRANSCRIPTS[@]} > 0 )); then
    for f in "${TRANSCRIPTS[@]}"; do
        TS=$(jq -r 'select(.type=="assistant") | .timestamp' "$f" 2>/dev/null | tail -1)
        [[ -z "$TS" ]] && continue
        if [[ -z "$LATEST_TS" || "$TS" > "$LATEST_TS" ]]; then
            LATEST_TS="$TS"
            LATEST_FILE="$f"
        fi
    done
fi

if [[ -n "$LATEST_FILE" ]]; then
    LAST_CREATION=$(jq -s '
        [.[] | select(.type=="assistant") | .message.usage.cache_creation_input_tokens // 0]
        | last // 0
    ' "$LATEST_FILE")
    if [[ "$LATEST_FILE" == "$TRANSCRIPT" ]]; then
        LAST_AGENT="main"
    else
        META="${LATEST_FILE%.jsonl}.meta.json"
        if [[ -f "$META" ]]; then
            TYPE=$(jq -r '.agentType // ""' "$META")
            LAST_AGENT=$(short_agent "$TYPE")
        fi
    fi
fi

# Sum tool_use blocks across every assistant message in a transcript — the
# invocation-cumulative tool count, matching Claude Code's done-report number.
# The SDK ceiling is enforced on this sum, not on any single message, so this
# is the value that needs to be coloured against TOOLS_PER_RESPONSE_CAP.
invocation_tool_count() {
    local f="$1"
    [[ -f "$f" ]] || { echo 0; return; }
    jq -s '
        [.[] | select(.type=="assistant") | (.message.content // []) | map(select(.type=="tool_use")) | length] | add // 0
    ' "$f" 2>/dev/null || echo 0
}

# Extract the agentId from a subagent transcript path. Subagent transcripts are
# named agent-<agentId>.jsonl; SendMessage.input.to carries that same id, so the
# id is the join key between a transcript file and the continues sent to it.
# Returns empty for the parent transcript (not named agent-*), which correctly
# yields a zero continuation count for the main session.
agent_id_of() {
    local base; base=$(basename "$1")
    case "$base" in
        agent-*.jsonl) base="${base#agent-}"; echo "${base%.jsonl}" ;;
        *) echo "" ;;
    esac
}

# Accepted SendMessage continues, tallied per recipient agentId in ONE pass over
# the parent transcript. Continues are recorded there as tool_use blocks named
# SendMessage with input.to == the target agentId. A send can be rejected (target
# already exited, unknown recipient) — that surfaces as an is_error tool_result
# keyed on the same tool_use id, so those ids are subtracted before grouping;
# counting raw sends would inflate the figure with blocked attempts. Both the ↺
# and ↗ cells read this map, so the multi-MB parent is parsed once per render,
# not once per cell. Built only when teams is on and a parent transcript exists;
# otherwise empty, and every lookup returns 0. Lines are "agentId<TAB>count".
CONT_MAP=""
if [[ "$AGENT_TEAMS" == 1 && -f "$TRANSCRIPT" ]]; then
    CONT_MAP=$(jq -rs '
        ([.[] | select(.type=="user") | (.message.content // [])[]?
            | select(.type=="tool_result" and .is_error==true) | .tool_use_id]) as $err
        | [.[] | select(.type=="assistant") | (.message.content // [])[]?
            | select(.type=="tool_use" and .name=="SendMessage") | {to: .input.to, id: .id}]
        | map(select(.id as $id | ($err | index($id)) | not))
        | group_by(.to)[]
        | "\(.[0].to)\t\(length)"
    ' "$TRANSCRIPT" 2>/dev/null)
fi

# Look up one agent's accepted-continue count in the precomputed CONT_MAP.
continuation_count() {
    local aid="$1"
    [[ -n "$aid" && -n "$CONT_MAP" ]] || { echo 0; return; }
    awk -F'\t' -v a="$aid" '$1==a {print $2; f=1} END {if (!f) print 0}' <<<"$CONT_MAP"
}

# Session-wide accepted-continue total — sum of the per-agent counts in CONT_MAP.
# Drives the always-on global ⟳ aggregate cell. Zero when teams is off (CONT_MAP
# empty) or no continues have landed; reuses the single CONT_MAP parse, so the
# global view costs no extra transcript reads.
GLOBAL_CONT=0
if [[ -n "$CONT_MAP" ]]; then
    GLOBAL_CONT=$(awk -F'\t' '{s += $2} END {print s + 0}' <<<"$CONT_MAP")
fi

# Cumulative tool count for the last-fired agent (the one named in `last:`).
LAST_TOOL_COUNT=0
[[ -n "$LATEST_FILE" ]] && LAST_TOOL_COUNT=$(invocation_tool_count "$LATEST_FILE")

# Accepted continues sent to that agent (0 for the main session — no agentId).
# Skipped entirely unless agent teams is on — no continues exist otherwise.
LAST_CONT=0
[[ "$AGENT_TEAMS" == 1 && -n "$LATEST_FILE" ]] && LAST_CONT=$(continuation_count "$(agent_id_of "$LATEST_FILE")")

# Hot agent: the non-last-fired subagent whose cumulative tool count is
# highest, only if it crosses the yellow threshold AND has touched its
# meta.json within ACTIVE_WINDOW_SEC. Surfaces a parallel subagent approaching
# the cap while a different one was last to finish. The active-window filter
# matches the ⇉ cell so a finished hot agent drops out of view on the same
# cadence as the parallel count — without it, a long-since-finished subagent
# whose final cumulative count was high would stay flagged indefinitely.
# Parent transcript is excluded — the main session is not subject to the SDK
# ceiling and routinely exceeds the cap.
NOW=$(date +%s)
HOT_THRESHOLD=$((TOOLS_PER_RESPONSE_CAP * TOOLS_YELLOW_PCT / 100))
HOT_AGENT=""
HOT_TOOL_COUNT=0
HOT_FILE=""
if (( ${#TRANSCRIPTS[@]} > 0 )); then
    for f in "${TRANSCRIPTS[@]}"; do
        [[ "$f" == "$LATEST_FILE" ]] && continue
        [[ "$f" == "$TRANSCRIPT" ]] && continue
        CNT=$(invocation_tool_count "$f")
        (( CNT >= HOT_THRESHOLD )) || continue
        (( CNT > HOT_TOOL_COUNT )) || continue
        # Only commit count + name together — otherwise a higher-count candidate
        # with missing meta.json would leave the previous (lower-count) agent
        # name paired with the new count.
        HOT_META="${f%.jsonl}.meta.json"
        [[ -f "$HOT_META" ]] || continue
        HOT_MT=$(mtime "$HOT_META")
        (( NOW - HOT_MT < ACTIVE_WINDOW_SEC )) || continue
        HOT_TYPE=$(jq -r '.agentType // ""' "$HOT_META")
        [[ -n "$HOT_TYPE" ]] || continue
        HOT_TOOL_COUNT=$CNT
        HOT_AGENT=$(short_agent "$HOT_TYPE")
        HOT_FILE=$f
    done
fi

# Accepted continues sent to the hot agent, joined on its transcript's agentId.
HOT_CONT=0
[[ "$AGENT_TEAMS" == 1 && -n "$HOT_FILE" ]] && HOT_CONT=$(continuation_count "$(agent_id_of "$HOT_FILE")")

# MCP usage across the whole session tree (parent + subagents). MCP tool calls
# surface in the transcript as tool_use blocks named mcp__<server>__<tool>, so a
# grep over the same blocks the tool counter reads gives the total, and the
# second __-delimited field is the server. Reports the session total plus the
# busiest server. Aggregated session-wide (not per-invocation) to match the
# cache cell — it answers "how much MCP did this session use", not "is an agent
# about to hit a cap". The cell drops out entirely when no MCP calls were made,
# so MCP-free sessions are unaffected.
MCP_TOTAL=0
MCP_TOP_SERVER=""
MCP_TOP_COUNT=0
if (( ${#TRANSCRIPTS[@]} > 0 )); then
    MCP_NAMES=$(
        for f in "${TRANSCRIPTS[@]}"; do
            jq -r 'select(.type=="assistant") | (.message.content // [])[] | select(.type=="tool_use") | .name' "$f" 2>/dev/null
        done | grep '^mcp__'
    )
    if [[ -n "$MCP_NAMES" ]]; then
        MCP_TOTAL=$(printf '%s\n' "$MCP_NAMES" | wc -l | tr -d ' ')
        # Busiest server = most frequent second __-field. uniq -c needs sorted
        # input; the trailing sort -rn ranks by count. Single underscores within
        # a server name (e.g. claude_ai_Gmail) survive the __ split.
        read -r MCP_TOP_COUNT MCP_TOP_SERVER < <(
            printf '%s\n' "$MCP_NAMES" | awk -F'__' '{print $2}' \
                | sort | uniq -c | sort -rn | head -1 | awk '{print $1, $2}'
        )
    fi
fi

# Model + context: read straight from the Claude Code stdin payload — avoids
# re-parsing the transcript and gets the same numbers Claude Code itself sees.
# `used_percentage` may be null early in the session or after /compact. These
# parses live below the cache check so the cache-hit path stays minimal.
MODEL_DISPLAY=$(jq -r '.model.display_name // ""' <<<"$INPUT")
CTX_PCT=$(jq -r '.context_window.used_percentage // 0' <<<"$INPUT" | awk '{printf "%.0f", $0}')
CTX_SIZE=$(jq -r '.context_window.context_window_size // 200000' <<<"$INPUT")
MODEL_SHORT=$(short_model "$MODEL_DISPLAY")

# Pick the autocompact threshold based on the model's context window size.
if (( CTX_SIZE >= 1000000 )); then
    AUTOCOMPACT_PCT=$CTX_AUTOCOMPACT_1M
else
    AUTOCOMPACT_PCT=$CTX_AUTOCOMPACT_200K
fi

# Count agents active within the active window — the raw fan-out width, so a
# 3-wide parallel burst of the same agent type reads as ⇉ 3 (matching the
# selector list), not ⇉ 1. Each meta file is one live agent.
ACTIVE=0
if [[ -d "$SUB_DIR" ]]; then
    while IFS= read -r meta; do
        MT=$(mtime "$meta")
        (( NOW - MT < ACTIVE_WINDOW_SEC )) || continue
        TYPE=$(jq -r '.agentType // ""' "$meta" 2>/dev/null)
        [[ -n "$TYPE" ]] && ACTIVE=$((ACTIVE + 1))
    done < <(find "$SUB_DIR" -maxdepth 1 -name "agent-*.meta.json" -type f 2>/dev/null)
fi

IN_FMT=$(fmt_tokens "$TOTAL_INPUT")
OUT_FMT=$(fmt_tokens "$OUT_TOK")
LAST_CC_FMT=$(fmt_tokens "$LAST_CREATION")
SESS_CC_FMT=$(fmt_tokens "$CC_TOK")
SESS_CR_FMT=$(fmt_tokens "$CR_TOK")

# ANSI codes
DIM=$'\e[90m'
BOLD=$'\e[1m'
CYAN=$'\e[36m'
GREEN=$'\e[32m'
YELLOW=$'\e[33m'
RED=$'\e[31m'
RESET=$'\e[0m'
SEP=" ${DIM}│${RESET} "

if   (( HIT_PCT >= HIT_GREEN ));  then HIT_COLOR="$GREEN"
elif (( HIT_PCT >= HIT_YELLOW )); then HIT_COLOR="$YELLOW"
else                                    HIT_COLOR="$RED"
fi

# Savings cell. Suppressed entirely when no cache activity — an empty SAVINGS
# section drops cleanly out of the cache cell at composition time.
#
# Framed as savings, positive = good (matches intuition: "I saved money"):
#   $N%  = cut N% of cache-eligible spend vs no-cache baseline (paying off)
#   $-N% = added N% — cache is costing money (heavy invalidation)
#   $0%  = break-even
# SAVINGS_PCT already carries this sign internally, so it's displayed as-is —
# no leading + on the good case. Color carries the magnitude band.
if [[ -z "$SAVINGS_PCT" ]]; then
    SAVINGS_DISPLAY=""
else
    if   (( SAVINGS_PCT >= SAVINGS_GREEN ));  then SAVINGS_COLOR="$GREEN"
    elif (( SAVINGS_PCT >= SAVINGS_YELLOW )); then SAVINGS_COLOR="$YELLOW"
    elif (( SAVINGS_PCT >= 0 ));              then SAVINGS_COLOR="$DIM"
    else                                           SAVINGS_COLOR="$RED"
    fi
    SAVINGS_DISPLAY=" ${SAVINGS_COLOR}\$${SAVINGS_PCT}%${RESET}"
fi

if   (( CTX_PCT < CTX_GREEN ));  then CTX_COLOR="$GREEN"
elif (( CTX_PCT < CTX_YELLOW )); then CTX_COLOR="$YELLOW"
else                                  CTX_COLOR="$RED"
fi

# Color a tool count against the cap, using percentage thresholds so the
# bands shift automatically when TOOLS_PER_RESPONSE_CAP changes.
tool_color() {
    local count=$1
    local pct=$((count * 100 / TOOLS_PER_RESPONSE_CAP))
    if   (( pct < TOOLS_YELLOW_PCT )); then echo "$DIM"
    elif (( pct < TOOLS_RED_PCT ));    then echo "$YELLOW"
    else                                    echo "$RED"
    fi
}

# ⚠ when cumulative tool count reaches the SDK ceiling — the subagent was
# almost certainly truncated mid-loop. Same severity as the autocompact
# marker on the ▤ cell.
tool_warn() {
    local count=$1
    if (( count >= TOOLS_PER_RESPONSE_CAP )); then echo " ${YELLOW}⚠${RESET}"; fi
}

# Color the per-agent ⟳ count. Sparse, so bands are absolute, not cap-relative:
# dim through CONT_YELLOW, yellow above it, red above CONT_RED.
cont_color() {
    local count=$1
    if   (( count > CONT_RED ));    then echo "$RED"
    elif (( count > CONT_YELLOW )); then echo "$YELLOW"
    else                                 echo "$DIM"
    fi
}

# Color the global ⟳ session total. Same shape as cont_color but with the higher
# global bands — a session-wide sum crosses the per-agent thresholds trivially,
# so it carries its own. At 0 this returns DIM, so the always-on cell sits quiet.
cont_color_global() {
    local count=$1
    if   (( count > CONT_GLOBAL_RED ));    then echo "$RED"
    elif (( count > CONT_GLOBAL_YELLOW )); then echo "$YELLOW"
    else                                        echo "$DIM"
    fi
}

# The SDK ceiling applies to subagent invocations, not the main session —
# coloring main against the cap would paint it red permanently. Branch on the
# transcript file (not the agent name) so the no-session-yet case also takes
# the dim form. Display is always bare (⚒N): the cap value stays out of the
# user-visible text, so a cap change never leaves stale numbers on screen.
LAST_TOOL_DISPLAY="⚒${LAST_TOOL_COUNT}"
if [[ -n "$LATEST_FILE" && "$LATEST_FILE" != "$TRANSCRIPT" ]]; then
    LAST_TOOL_COLOR=$(tool_color "$LAST_TOOL_COUNT")
    LAST_TOOL_WARN=$(tool_warn "$LAST_TOOL_COUNT")
else
    LAST_TOOL_COLOR="$DIM"
    LAST_TOOL_WARN=""
fi

# A continued agent is being actively re-engaged, so a high tool count is no
# longer a stuck-mid-loop signal — the coordinator is driving it. Drop the cap
# color and ⚠ to dim, letting the ⟳ cell carry the state instead of double-
# alarming. The bare count still shows for reference.
LAST_CONT_CELL=""
if (( LAST_CONT >= 1 )); then
    LAST_TOOL_COLOR="$DIM"
    LAST_TOOL_WARN=""
    LAST_CONT_CELL=" $(cont_color "$LAST_CONT")⟳${LAST_CONT}${RESET}"
fi

# Mark the moment context crosses the model-specific autocompact threshold.
CTX_WARN=""
if (( CTX_PCT >= AUTOCOMPACT_PCT )); then
    CTX_WARN=" ${YELLOW}⚠${RESET}"
fi

# Color the ⊕ cell against the creation-spike bands. No separate ⚠ marker —
# the color carries the signal, matching the pattern of the cache-hit cell.
if   (( LAST_CREATION >= CREATION_RED ));    then LAST_CC_COLOR="$RED"
elif (( LAST_CREATION >= CREATION_YELLOW )); then LAST_CC_COLOR="$YELLOW"
else                                              LAST_CC_COLOR="$DIM"
fi

# Compose the line as labeled sections — easier to read and change than one
# 30-arg printf. Empty sections are skipped at join time so suppressed cells
# leave no dangling separators. The cell vocabulary, icon rhythm, and color
# semantics are documented in the README's Statusline Format table.
section_project="${BOLD}${PROJECT}${RESET} ${DIM}⎇${RESET} ${CYAN}${BRANCH}${RESET}"
section_model="${MODEL_SHORT} ${DIM}▤${RESET} ${CTX_COLOR}${CTX_PCT}%${RESET}${CTX_WARN}"
# The $ figure is the list-price API cost of this session's token volume,
# computed by accounting.py. Dropped when unavailable (no python3 / other
# tool) so no dangling $ shows. It sits in the Σ cell because cost is the money
# view of the same token totals; distinct from the cache cell's $N% savings.
COST_CELL=""
[[ -n "$SESSION_COST" ]] && COST_CELL=" \$${SESSION_COST}"
section_scale="${DIM}Σ ▲${IN_FMT} ▼${OUT_FMT}${COST_CELL}${RESET}"
section_cache="${DIM}⛁ ${HIT_COLOR}${HIT_PCT}%${RESET} ${DIM}⊖${SESS_CR_FMT} ⊕${SESS_CC_FMT}${RESET}${SAVINGS_DISPLAY}"

# MCP-usage cell: total calls, then busiest server (server·N). Suppressed
# entirely when the session made no MCP calls.
section_mcp=""
if (( MCP_TOTAL > 0 )); then
    MCP_SERVER_SHORT=$(short_agent "$MCP_TOP_SERVER")
    section_mcp="${DIM}⇲ ${MCP_TOTAL}${RESET} ${MCP_SERVER_SHORT}${DIM}·${MCP_TOP_COUNT}${RESET}"
fi

# Parallel-agents indicator. Always shown (even at 0) so the line's layout
# stays stable across solo and fan-out states — eye doesn't need to re-locate
# the per-agent cells when parallel work starts or ends.
section_active="${DIM}⇉ ${ACTIVE}${RESET}"

# Global continuation cell — session-wide accepted-continue total. Always shown
# (even at 0) when agent teams is on, so the line stays layout-stable and
# tracking is visibly live; suppressed when teams is off (no continues exist).
section_cont=""
if [[ "$AGENT_TEAMS" == 1 ]]; then
    section_cont="$(cont_color_global "$GLOBAL_CONT")⟳ ${GLOBAL_CONT}${RESET}"
fi

# ↺ last-turn cell: agent name, ⊕ creation tokens, ⚒ cumulative tool count
# (matches the number Claude reports at agent finish).
section_last="${DIM}↺${RESET} ${BOLD}${LAST_AGENT}${RESET} ${LAST_CC_COLOR}⊕${LAST_CC_FMT}${RESET} ${LAST_TOOL_COLOR}${LAST_TOOL_DISPLAY}${RESET}${LAST_TOOL_WARN}${LAST_CONT_CELL}"

# ↗ hot cell — only when a different parallel agent is at risk of the cap.
section_hot=""
if [[ -n "$HOT_AGENT" ]]; then
    HOT_COLOR=$(tool_color "$HOT_TOOL_COUNT")
    HOT_WARN=$(tool_warn "$HOT_TOOL_COUNT")
    HOT_CONT_CELL=""
    if (( HOT_CONT >= 1 )); then
        HOT_COLOR="$DIM"
        HOT_WARN=""
        HOT_CONT_CELL=" $(cont_color "$HOT_CONT")⟳${HOT_CONT}${RESET}"
    fi
    section_hot="${YELLOW}↗${RESET} ${BOLD}${HOT_AGENT}${RESET} ${HOT_COLOR}⚒${HOT_TOOL_COUNT}${RESET}${HOT_WARN}${HOT_CONT_CELL}"
fi

# Join non-empty sections with the separator. Order: scene-setter cells first
# (project, model, scale, cache, ⇲ mcp, ⇉ N, ⟳ N), then per-agent detail (↺ last, ↗ hot).
OUTPUT=""
for s in "$section_project" "$section_model" "$section_scale" "$section_cache" \
         "$section_mcp" "$section_active" "$section_cont" "$section_last" "$section_hot"; do
    [[ -z "$s" ]] && continue
    if [[ -z "$OUTPUT" ]]; then OUTPUT="$s"; else OUTPUT="${OUTPUT}${SEP}${s}"; fi
done

# Create the cache dir on the miss path only — the hit path reads without
# forking for it. chmod separately from mkdir -p (SC2174); running it per
# miss also re-tightens a dir that pre-existed with looser permissions.
# chmod succeeds only for the dir's owner, so a pass proves ownership: if
# another user pre-created the path (a shared temp root with HOME unset),
# the gate fails and this render skips caching rather than write anything
# an attacker can reach. The write itself is atomic (temp file + rename in
# the same directory) so a concurrent render never reads a half-written
# cache. `2>/dev/null` sits before the `>` redirect so a failed open of
# CACHE_TMP is silenced too — redirections apply left to right. A
# symlinked CACHE_DIR is refused outright: chmod would follow the link and
# prove ownership of the target, not the path — a pre-planted symlink in a
# shared temp root could redirect the chmod/sweep onto a victim-owned dir.
if [ ! -L "$CACHE_DIR" ] && { mkdir -p "$CACHE_DIR" && chmod 700 "$CACHE_DIR"; } 2>/dev/null; then
    CACHE_TMP="${CACHE_FILE}.$$"
    { echo "$CACHE_KEY"; echo "$OUTPUT"; } 2>/dev/null > "$CACHE_TMP" \
        && mv -f "$CACHE_TMP" "$CACHE_FILE" 2>/dev/null \
        || rm -f "$CACHE_TMP" 2>/dev/null
fi
echo "$OUTPUT"

# Opportunistically sweep cache files older than CACHE_TTL_MIN. Runs only on
# cache miss (cache hits exit before reaching here), so amortized cost is one
# find call per new transcript turn. `-mmin +N -delete` is portable to GNU
# and BSD find. Errors silenced so a transient permissions issue can't break
# the statusline render that already emitted above. Sweeps the same directory
# the cache is written to (see CACHE_DIR); the pattern has no .cache suffix so
# it also collects temp files orphaned by a crash between write and rename.
find "$CACHE_DIR" -maxdepth 1 -name 'claude-statusline-*' -mmin "+${CACHE_TTL_MIN}" -type f -delete 2>/dev/null || true
