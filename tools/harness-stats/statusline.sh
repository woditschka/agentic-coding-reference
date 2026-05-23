#!/usr/bin/env bash
# Statusline: project, branch, parent model + context %, session-wide token
# totals across parent + subagents, aggregate cache hit %, last fired agent +
# its creation tokens, count of active agents.
#
# Reads Claude Code JSON from stdin. Caches aggregates per-session keyed by
# transcript mtimes so the hot path is fast even on multi-MB transcripts.

# `set -e` deliberately omitted: the script degrades gracefully when jq, git,
# or transcript files are missing. A failed component yields a minimal
# statusline (e.g. branch "-", agent "?"), never a blank one.
set -uo pipefail

# Subagent meta files modified within this window count as "active" for the
# trailing "N active" indicator.
ACTIVE_WINDOW_SEC=300

# Cache-hit thresholds. Mature Claude Code sessions with a stable prefix sit
# ≥90%; 75–90% is normal early-session ramp-up or moderate prefix churn;
# <75% signals real cache misses.
HIT_GREEN=90
HIT_YELLOW=75

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

# Creation-tokens-in-last-turn threshold for the ⚠ marker.
CREATION_WARN=5000

# Agent name truncation length for the "last:" cell.
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
CACHE_KEY="v4:${PARENT_MT}:${SUB_DIR_MT}:${SUB_FILES_MT}"

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

# Find the most recent assistant turn across parent + subagents.
LAST_AGENT="-"
LAST_CREATION=0
LATEST_TS=""
LATEST_FILE=""
for f in "${TRANSCRIPTS[@]}"; do
    TS=$(jq -r 'select(.type=="assistant") | .timestamp' "$f" 2>/dev/null | tail -1)
    [[ -z "$TS" ]] && continue
    if [[ -z "$LATEST_TS" || "$TS" > "$LATEST_TS" ]]; then
        LATEST_TS="$TS"
        LATEST_FILE="$f"
    fi
done

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
    NOW=$(date +%s)
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

if   (( CTX_PCT < CTX_GREEN ));  then CTX_COLOR="$GREEN"
elif (( CTX_PCT < CTX_YELLOW )); then CTX_COLOR="$YELLOW"
else                                  CTX_COLOR="$RED"
fi

# Mark the moment context crosses the model-specific autocompact threshold.
CTX_WARN=""
if (( CTX_PCT >= AUTOCOMPACT_PCT )); then
    CTX_WARN=" ${YELLOW}⚠${RESET}"
fi

# Warn on a creation spike in the last turn.
WARN=""
LAST_CC_COLOR="$DIM"
if (( LAST_CREATION > CREATION_WARN )); then
    WARN=" ${YELLOW}⚠${RESET}"
    LAST_CC_COLOR="$YELLOW"
fi

# Compose the line as labeled sections. Easier to read and change than a single
# 30-arg printf.
section_project="${BOLD}${PROJECT}${RESET} ${DIM}⎇${RESET} ${CYAN}${BRANCH}${RESET}"
section_model="${MODEL_SHORT}${DIM}·${RESET}${CTX_COLOR}${CTX_PCT}%${RESET}${CTX_WARN}"
section_scale="${DIM}▲${IN_FMT} ▼${OUT_FMT}${RESET}"
section_cache="${DIM}cache ${HIT_COLOR}${HIT_PCT}%${RESET} ${DIM}⊖${SESS_CR_FMT} ⊕${SESS_CC_FMT}${RESET}"
section_last="last: ${BOLD}${LAST_AGENT}${RESET} ${LAST_CC_COLOR}+${LAST_CC_FMT}${RESET}${WARN}"
section_active="${DIM}${ACTIVE} active${RESET}"

OUTPUT="${section_project}${SEP}${section_model}${SEP}${section_scale}${SEP}${section_cache}${SEP}${section_last}${SEP}${section_active}"

# Write cache and emit.
{ echo "$CACHE_KEY"; echo "$OUTPUT"; } > "$CACHE_FILE"
echo "$OUTPUT"

# Opportunistically sweep cache files older than CACHE_TTL_MIN. Runs only on
# cache miss (cache hits exit before reaching here), so amortized cost is one
# find call per new transcript turn. `-mmin +N -delete` is portable to GNU
# and BSD find. Errors silenced so a transient permissions issue can't break
# the statusline render that already emitted above.
find /tmp -maxdepth 1 -name 'claude-statusline-*.cache' -mmin "+${CACHE_TTL_MIN}" -type f -delete 2>/dev/null || true
