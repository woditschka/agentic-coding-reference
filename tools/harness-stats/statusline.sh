#!/usr/bin/env bash
# Statusline: project, branch, parent model + context %, session-wide token
# totals across parent + subagents, aggregate cache hit %, conditional
# parallel-fan-out indicator (⇉N), last-finished agent (with its cumulative
# tool count — bare for main, vs the SDK ceiling for subagents), and a
# conditional hot-agent cell for parallel subagents approaching the ceiling.
#
# Reads Claude Code JSON from stdin. Caches aggregates per-session keyed by
# transcript mtimes so the hot path is fast even on multi-MB transcripts.

# `set -e` deliberately omitted: the script degrades gracefully when jq, git,
# or transcript files are missing. A failed component yields a minimal
# statusline (e.g. branch "-", agent "?"), never a blank one.
set -uo pipefail

# Subagent meta files modified within this window count toward the parallel
# fan-out count (⇉ N cell, always shown — even at 0 — for layout stability).
ACTIVE_WINDOW_SEC=300

# Cache-hit thresholds. Mature Claude Code sessions with a stable prefix sit
# ≥90%; 75–90% is normal early-session ramp-up or moderate prefix churn;
# <75% signals real cache misses.
HIT_GREEN=90
HIT_YELLOW=75

# Cache-savings thresholds (% reduction in cache-eligible spend vs no-cache
# baseline). Computed against the pricing ratio cache_read=0.10×input,
# cache_write=1.25×input on the cache-eligible token volume only — regular
# input is excluded from the baseline so the metric reflects cache-decision
# quality, not overall session spend. Below 0 fires red — writes are
# outpacing reads, the cache is costing money (usually means heavy
# invalidation: model switch, prompt churn, hitting cache limits).
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
# update the parent dir's mtime, so without this we'd serve stale data during
# a multi-turn subagent run.
PARENT_MT=$(mtime "$TRANSCRIPT")
SUB_DIR_MT=$(mtime "$SUB_DIR")
if [[ -d "$SUB_DIR" ]]; then
    SUB_FILES_MT=$(max_mtime "$SUB_DIR" -maxdepth 1 -name "agent-*.jsonl" -type f)
else
    SUB_FILES_MT=0
fi

# Strip anything but alphanumerics and dashes from SESSION_ID before joining
# it into a /tmp path. SESSION_ID comes from JSON input; a hostile value
# containing `/` or `..` would otherwise let the cache escape /tmp.
SAFE_SID="${SESSION_ID//[^a-zA-Z0-9-]/_}"
CACHE_FILE="/tmp/claude-statusline-${SAFE_SID}.cache"
CACHE_KEY="v10:${PARENT_MT}:${SUB_DIR_MT}:${SUB_FILES_MT}"

if [[ -f "$CACHE_FILE" ]] && [[ "$(head -1 "$CACHE_FILE")" == "$CACHE_KEY" ]]; then
    tail -n +2 "$CACHE_FILE"
    exit 0
fi

# Display the agent name, truncated to fit the statusline. Generic across projects.
short_agent() {
    local name="$1"
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
# so we match Claude Code's "Opus 4.7" display name as well as raw "claude-opus-4-7".
short_model() {
    local lower
    lower=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    case "$lower" in
        *opus*)   echo "opus" ;;
        *sonnet*) echo "sonnet" ;;
        *haiku*)  echo "haiku" ;;
        *)        echo "?" ;;
    esac
}

# Collect transcript files: parent + all subagents in the matching session dir.
TRANSCRIPTS=()
[[ -f "$TRANSCRIPT" ]] && TRANSCRIPTS+=("$TRANSCRIPT")
if [[ -d "$SUB_DIR" ]]; then
    while IFS= read -r f; do
        TRANSCRIPTS+=("$f")
    done < <(find "$SUB_DIR" -maxdepth 1 -name "agent-*.jsonl" -type f 2>/dev/null)
fi

# Sum usage across all transcripts.
if (( ${#TRANSCRIPTS[@]} > 0 )); then
    TOTALS=$(
        for f in "${TRANSCRIPTS[@]}"; do
            jq -c 'select(.type=="assistant") | .message.usage // empty' "$f" 2>/dev/null
        done | jq -s '
            reduce .[] as $u (
                {in:0, out:0, cr:0, cc:0};
                .in += ($u.input_tokens // 0)
                | .out += ($u.output_tokens // 0)
                | .cr += ($u.cache_read_input_tokens // 0)
                | .cc += ($u.cache_creation_input_tokens // 0)
            ) | "\(.in) \(.out) \(.cr) \(.cc)"
        '
    )
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

# Cache savings vs no-cache baseline on the cache-eligible token volume.
# baseline = (cr + cc) × 1.0  ;  actual = cr × 0.10 + cc × 1.25.
# Closed form: (0.9 × cr − 0.25 × cc) / (cr + cc) × 100. Suppressed when no
# cache activity (denominator 0) — nothing to evaluate.
CACHE_TOTAL=$((CR_TOK + CC_TOK))
if (( CACHE_TOTAL > 0 )); then
    SAVINGS_PCT=$(awk -v cr="$CR_TOK" -v cc="$CC_TOK" 'BEGIN {
        printf "%.0f", (0.9 * cr - 0.25 * cc) * 100 / (cr + cc)
    }')
else
    SAVINGS_PCT=""
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

# Cumulative tool count for the last-fired agent (the one named in `last:`).
LAST_TOOL_COUNT=0
[[ -n "$LATEST_FILE" ]] && LAST_TOOL_COUNT=$(invocation_tool_count "$LATEST_FILE")

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
    done
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

# Count distinct agent types active within the active window. Uses a regular
# array + sort -u instead of an associative array so it runs on bash 3.2
# (macOS system bash).
ACTIVE=0
if [[ -d "$SUB_DIR" ]]; then
    ACTIVE_TYPES=()
    while IFS= read -r meta; do
        MT=$(mtime "$meta")
        (( NOW - MT < ACTIVE_WINDOW_SEC )) || continue
        TYPE=$(jq -r '.agentType // ""' "$meta" 2>/dev/null)
        [[ -n "$TYPE" ]] && ACTIVE_TYPES+=("$TYPE")
    done < <(find "$SUB_DIR" -maxdepth 1 -name "agent-*.meta.json" -type f 2>/dev/null)
    if (( ${#ACTIVE_TYPES[@]} > 0 )); then
        ACTIVE=$(printf '%s\n' "${ACTIVE_TYPES[@]}" | sort -u | wc -l | tr -d ' ')
    fi
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

# The SDK ceiling applies to subagent invocations, not to the main session.
# Main routinely runs hundreds of cumulative tool calls across many turns
# without ever being capped — colouring it against the cap would paint it red
# permanently. Branch on the transcript file (not the agent name) so the
# no-session-yet case (LATEST_FILE empty) also takes the dim-cumulative form.
# Display is always bare (⚒N); the cap value lives in TOOLS_PER_RESPONSE_CAP
# and drives the color thresholds, so the runtime-specific number stays out of
# the user-visible text — same drift-resistance reasoning as the harness docs.
LAST_TOOL_DISPLAY="⚒${LAST_TOOL_COUNT}"
if [[ -n "$LATEST_FILE" && "$LATEST_FILE" != "$TRANSCRIPT" ]]; then
    LAST_TOOL_COLOR=$(tool_color "$LAST_TOOL_COUNT")
    LAST_TOOL_WARN=$(tool_warn "$LAST_TOOL_COUNT")
else
    LAST_TOOL_COLOR="$DIM"
    LAST_TOOL_WARN=""
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

# Compose the line as labeled sections. Easier to read and change than a single
# 30-arg printf. Empty sections are skipped at join time so suppressed cells
# don't leave dangling separators.
# Each cell that introduces a value leads with an icon and one space, so the
# line reads as a row of labeled pieces: ⎇ branch, ▤ context, Σ tokens,
# ⛁ cache, ⇉ parallel-count, ↺ last-turn, ↗ hot-agent. Mid-cell totals
# (▲▼⊖⊕) stay glued to their numbers — they're inline metrics, not leading
# markers. Inside the ↺ and ↗ cells, ⊕ and ⚒ inherit the urgency color of
# the value they precede so the whole chunk turns yellow/red when the metric
# does.
section_project="${BOLD}${PROJECT}${RESET} ${DIM}⎇${RESET} ${CYAN}${BRANCH}${RESET}"
section_model="${MODEL_SHORT} ${DIM}▤${RESET} ${CTX_COLOR}${CTX_PCT}%${RESET}${CTX_WARN}"
section_scale="${DIM}Σ ▲${IN_FMT} ▼${OUT_FMT}${RESET}"
section_cache="${DIM}⛁ ${HIT_COLOR}${HIT_PCT}%${RESET} ${DIM}⊖${SESS_CR_FMT} ⊕${SESS_CC_FMT}${RESET}${SAVINGS_DISPLAY}"

# Parallel-agents indicator. Always shown (even at 0) so the line's layout
# stays stable across solo and fan-out states — eye doesn't need to re-locate
# the per-agent cells when parallel work starts or ends.
section_active="${DIM}⇉ ${ACTIVE}${RESET}"

# `last:` cell — leads with ↺ (previous turn), then agent name, then ⊕ for
# creation tokens and ⚒ for cumulative tool count across the invocation
# (matches the number Claude reports at agent finish). Reusing ⊕ from the
# cache cell makes the metric relationship explicit: same data, same glyph.
section_last="${DIM}↺${RESET} ${BOLD}${LAST_AGENT}${RESET} ${LAST_CC_COLOR}⊕${LAST_CC_FMT}${RESET} ${LAST_TOOL_COLOR}${LAST_TOOL_DISPLAY}${RESET}${LAST_TOOL_WARN}"

# `hot:` only appears when a different parallel agent is at risk. Leads with
# ↗ (trending up toward the cap) — quieter than a spike/alert glyph, with
# the yellow color carrying the urgency signal. Slots into the line's icon
# rhythm; fitting the pattern makes the alert easier to spot than breaking
# it with a text label would.
section_hot=""
if [[ -n "$HOT_AGENT" ]]; then
    HOT_COLOR=$(tool_color "$HOT_TOOL_COUNT")
    HOT_WARN=$(tool_warn "$HOT_TOOL_COUNT")
    section_hot="${YELLOW}↗${RESET} ${BOLD}${HOT_AGENT}${RESET} ${HOT_COLOR}⚒${HOT_TOOL_COUNT}${RESET}${HOT_WARN}"
fi

# Join non-empty sections with the separator. Order: scene-setter cells first
# (project, model, scale, cache, ⇉ N), then per-agent detail (↺ last, ↗ hot).
OUTPUT=""
for s in "$section_project" "$section_model" "$section_scale" "$section_cache" \
         "$section_active" "$section_last" "$section_hot"; do
    [[ -z "$s" ]] && continue
    if [[ -z "$OUTPUT" ]]; then OUTPUT="$s"; else OUTPUT="${OUTPUT}${SEP}${s}"; fi
done

# Write cache and emit.
{ echo "$CACHE_KEY"; echo "$OUTPUT"; } > "$CACHE_FILE"
echo "$OUTPUT"

# Opportunistically sweep cache files older than CACHE_TTL_MIN. Runs only on
# cache miss (cache hits exit before reaching here), so amortized cost is one
# find call per new transcript turn. `-mmin +N -delete` is portable to GNU
# and BSD find. Errors silenced so a transient permissions issue can't break
# the statusline render that already emitted above.
find /tmp -maxdepth 1 -name 'claude-statusline-*.cache' -mmin "+${CACHE_TTL_MIN}" -type f -delete 2>/dev/null || true
