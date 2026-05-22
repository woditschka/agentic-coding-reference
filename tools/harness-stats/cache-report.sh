#!/usr/bin/env bash
# cache-report: per-agent cache-efficiency breakdown for a Claude Code session.
#
# Usage:
#   cache-report.sh                   # current cwd, most recent session
#   cache-report.sh <session_id>      # current cwd, named session
#   cache-report.sh <session_id> <project_dir>
#   cache-report.sh --list            # list sessions in current project
#
# Reads parent transcript + all subagent transcripts for the session, groups by
# agentType, and reports per-agent: Runs, Median turns, Warm-start %, In-run
# reuse %, Net savings %, plus token volume (▼ total input, ⊕ cache create,
# ⊖ cache read). The script emits measurement only; the cache-report skill
# layers the LLM analysis on top.

set -uo pipefail

# Force UTF-8 character semantics in this script's locale. pad_to uses ${#var}
# to size cells around the multibyte symbols (▼ ⊕ ⊖); under a byte-counting
# locale (LC_ALL=C and similar) that returns 3 instead of 1 and the token
# columns drift. Detect first, override only if needed, and warn (but continue)
# if no UTF-8 locale is available on the system.
_locale_probe=$'\xe2\x96\xbc'
if (( ${#_locale_probe} != 1 )); then
    for _loc in en_US.UTF-8 C.UTF-8 en_US.utf8 C.utf8; do
        export LC_ALL="$_loc"
        _locale_probe=$'\xe2\x96\xbc'
        (( ${#_locale_probe} == 1 )) && break
    done
    if (( ${#_locale_probe} != 1 )); then
        echo "Warning: no UTF-8 locale available; token column alignment may drift" >&2
    fi
fi
unset _locale_probe _loc

# Anthropic input-token pricing multipliers (relative to base input price).
# Used only to compute the savings-vs-no-cache ratio; absolute $ not needed.
CREATE_MULT="1.25"
READ_MULT="0.10"

# Session-level hit-% thresholds (must match statusline.sh: HIT_GREEN/HIT_YELLOW).
SESS_HIT_GREEN=90
SESS_HIT_YELLOW=75

# Per-agent warm-start / in-run reuse thresholds. These measure something
# different from the aggregate hit % (per-fire reuse rather than session-wide),
# so the looser scale is intentional.
AGENT_PCT_GREEN=70
AGENT_PCT_YELLOW=40

# Net-savings-% color threshold. Positive savings below this are yellow; at or
# above are green. Negative is always red (with no threshold).
SAVE_GREEN=30

# Column widths for the per-agent table. Each width fits its full header label
# on one line. The trailing three "tokens" columns (▼ total input, ⊕ cache
# create, ⊖ cache read) carry multibyte symbol headers and data; bash printf
# %Ns counts bytes not display columns, so those three are padded via pad_to
# (which uses ${#var} character count in UTF-8 locales) rather than printf
# width. The horizontal rule covers all nine columns.
COL_AGENT=30
COL_RUNS=5
COL_MEDIAN=12
COL_WARM=12
COL_INRUN=14
COL_SAVE=13
COL_TIN=8
COL_CC=8
COL_CR=8

# --- Cross-platform helpers (Linux + macOS) ----------------------------------

# Resolve a path to an absolute form. Tries `realpath`, then a cd/pwd fallback
# that works on every shell. Returns the input unchanged if neither works.
resolve_path() {
    local p="$1"
    if command -v realpath >/dev/null 2>&1; then
        realpath "$p" 2>/dev/null && return
    fi
    if [[ -d "$p" ]]; then
        (cd "$p" 2>/dev/null && pwd) && return
    fi
    echo "$p"
}

# File mtime as ISO-ish "YYYY-MM-DD HH:MM:SS". GNU vs BSD/macOS stat differ.
stat_mtime_human() {
    stat -c '%y' "$1" 2>/dev/null | cut -d. -f1 && return
    stat -f '%Sm' -t '%Y-%m-%d %H:%M:%S' "$1" 2>/dev/null && return
    echo "?"
}

# File size in bytes.
stat_size() {
    stat -c %s "$1" 2>/dev/null || stat -f %z "$1" 2>/dev/null || echo 0
}

# Format a byte count as 12B / 3.4K / 1.2M / 4.5G — replaces `numfmt --to=iec`.
human_size() {
    awk -v n="$1" 'BEGIN {
        u="BKMGT"; i=1
        while (n >= 1024 && i < 5) { n /= 1024; i++ }
        if (i == 1) printf "%d%s", n, substr(u, i, 1)
        else        printf "%.1f%s", n, substr(u, i, 1)
    }'
}

# -----------------------------------------------------------------------------

usage() {
    cat <<EOF
Usage: $(basename "$0") [<session_id> [<project_dir>]]
       $(basename "$0") --list

Reports per-agent cache efficiency for the named session (defaults to most
recent session in the current working directory).
EOF
    exit 1
}

# Resolve project directory and its transcript directory.
resolve_project() {
    local dir="${1:-$(pwd)}"
    dir=$(resolve_path "$dir")
    local encoded=${dir//\//-}
    echo "$HOME/.claude/projects/$encoded"
}

list_sessions() {
    local tdir="$1"
    if [[ ! -d "$tdir" ]]; then
        echo "No transcripts at $tdir" >&2
        return 1
    fi
    printf "%-40s  %-20s  %s\n" "SESSION_ID" "LAST_MODIFIED" "SIZE"
    while IFS= read -r f; do
        local sid mt size
        sid=$(basename "$f" .jsonl)
        mt=$(stat_mtime_human "$f")
        size=$(stat_size "$f")
        printf "%-40s  %-20s  %s\n" "$sid" "$mt" "$(human_size "$size")"
    done < <(ls -t "$tdir"/*.jsonl 2>/dev/null)
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
fi

if [[ "${1:-}" == "--list" ]]; then
    TDIR=$(resolve_project "${2:-}")
    list_sessions "$TDIR"
    exit $?
fi

PROJECT_DIR="${2:-$(pwd)}"
TDIR=$(resolve_project "$PROJECT_DIR")

SESSION_ID="${1:-}"
if [[ -z "$SESSION_ID" ]]; then
    LATEST=$(ls -t "$TDIR"/*.jsonl 2>/dev/null | head -1 || true)
    if [[ -z "$LATEST" ]]; then
        echo "No sessions found in $TDIR" >&2
        exit 1
    fi
    SESSION_ID=$(basename "$LATEST" .jsonl)
fi

# Session IDs are UUIDs (8-4-4-4-12 hex). Reject anything else so a malformed
# argument can't traverse out of the transcript directory or accidentally point
# at an unrelated file.
if [[ ! "$SESSION_ID" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then
    echo "Invalid session ID: $SESSION_ID (expected UUID format)" >&2
    exit 1
fi

PARENT_JSONL="$TDIR/$SESSION_ID.jsonl"
SUB_DIR="$TDIR/$SESSION_ID/subagents"

if [[ ! -f "$PARENT_JSONL" ]]; then
    echo "Parent transcript not found: $PARENT_JSONL" >&2
    exit 1
fi

# Build a JSON array of per-run records:
#   [{agent_type, turns: [{in, cc, cr, out}]}, ...]
# The parent transcript is treated as a single run of agent_type "main".
build_runs() {
    local first=1
    echo "["

    # Parent as one synthetic run. `-nR | inputs | fromjson?` reads JSONL line
    # by line so a single malformed line skips itself instead of failing the
    # whole transcript (the prior `-s` slurp returned 0 turns on any parse
    # error anywhere in the file).
    local turns
    turns=$(jq -ncR '[inputs | fromjson? | select(.type=="assistant") | .message.usage | {
        in:  (.input_tokens // 0),
        cc:  (.cache_creation_input_tokens // 0),
        cr:  (.cache_read_input_tokens // 0),
        out: (.output_tokens // 0)
    }]' "$PARENT_JSONL" 2>/dev/null || echo "[]")
    printf '{"agent_type":"main","turns":%s}' "$turns"
    first=0

    if [[ -d "$SUB_DIR" ]]; then
        while IFS= read -r meta; do
            local jsonl agent_type t
            jsonl="${meta%.meta.json}.jsonl"
            [[ -f "$jsonl" ]] || continue
            agent_type=$(jq -r '.agentType // "unknown"' "$meta")
            t=$(jq -ncR '[inputs | fromjson? | select(.type=="assistant") | .message.usage | {
                in:  (.input_tokens // 0),
                cc:  (.cache_creation_input_tokens // 0),
                cr:  (.cache_read_input_tokens // 0),
                out: (.output_tokens // 0)
            }]' "$jsonl" 2>/dev/null || echo "[]")
            (( first == 0 )) && printf ","
            printf '{"agent_type":%s,"turns":%s}' "$(jq -nc --arg s "$agent_type" '$s')" "$t"
            first=0
        done < <(find "$SUB_DIR" -maxdepth 1 -name "agent-*.meta.json" -type f 2>/dev/null | sort)
    fi
    echo "]"
}

RUNS=$(build_runs)

# Aggregate by agent type. Emit a JSON object with rows and session totals.
REPORT=$(jq -n --argjson runs "$RUNS" --argjson create_mult "$CREATE_MULT" --argjson read_mult "$READ_MULT" '
    def median:
        sort as $s
        | length as $n
        | if $n == 0 then 0
          elif $n % 2 == 1 then ($s[($n - 1) / 2] | tonumber)
          else (($s[$n / 2 - 1] + $s[$n / 2]) / 2)
          end;

    def sum_field(f): map(f) | add // 0;

    # For one run, compute per-run stats.
    def run_stats:
        .turns as $t
        | ($t | length) as $n_turns
        | {
            n_turns: $n_turns,
            first_cr:    ($t[0].cr // 0),
            first_total: (($t[0].in // 0) + ($t[0].cc // 0) + ($t[0].cr // 0)),
            rest_cr:     ($t[1:] | sum_field(.cr)),
            rest_total:  ($t[1:] | (sum_field(.in) + sum_field(.cc) + sum_field(.cr))),
            tot_in:      ($t | sum_field(.in)),
            tot_cc:      ($t | sum_field(.cc)),
            tot_cr:      ($t | sum_field(.cr)),
            tot_out:     ($t | sum_field(.out))
        };

    # Group by agent_type, compute aggregates.
    ($runs | map(. + {stats: run_stats}) | group_by(.agent_type) | map(
        .[0].agent_type as $type
        | map(.stats) as $s
        | ($s | map(.n_turns)) as $turn_counts
        | ($s | map(select(.first_total > 0)) | map(.first_cr / .first_total)) as $warm_ratios
        | (($s | sum_field(.rest_cr))) as $rest_cr
        | (($s | sum_field(.rest_total))) as $rest_total
        | (($s | sum_field(.tot_in))) as $tot_in
        | (($s | sum_field(.tot_cc))) as $tot_cc
        | (($s | sum_field(.tot_cr))) as $tot_cr
        | (($s | sum_field(.tot_out))) as $tot_out
        | ($tot_in + ($tot_cc * $create_mult) + ($tot_cr * $read_mult)) as $actual
        | ($tot_in + $tot_cc + $tot_cr) as $baseline
        | {
            agent_type: $type,
            runs: ($s | length),
            median_turns: ($turn_counts | median),
            warm_start_pct: (if ($warm_ratios | length) > 0 then ($warm_ratios | add / length * 100) else null end),
            in_run_reuse_pct: (if $rest_total > 0 then ($rest_cr / $rest_total * 100) else null end),
            net_savings_pct: (if $baseline > 0 then ((1 - $actual / $baseline) * 100) else 0 end),
            tot_in: $tot_in, tot_cc: $tot_cc, tot_cr: $tot_cr, tot_out: $tot_out
        }
    ) | sort_by(- (.tot_in + .tot_cc + .tot_cr))) as $rows

    | ($rows | sum_field(.tot_in))  as $sess_in
    | ($rows | sum_field(.tot_cc))  as $sess_cc
    | ($rows | sum_field(.tot_cr))  as $sess_cr
    | ($rows | sum_field(.tot_out)) as $sess_out
    | ($sess_in + ($sess_cc * $create_mult) + ($sess_cr * $read_mult)) as $sess_actual
    | ($sess_in + $sess_cc + $sess_cr) as $sess_baseline

    | {
        rows: $rows,
        session: {
            total_input_tokens:    $sess_in,
            cache_creation_tokens: $sess_cc,
            cache_read_tokens:     $sess_cr,
            total_output_tokens:   $sess_out,
            hit_pct: (if ($sess_in + $sess_cc + $sess_cr) > 0 then ($sess_cr / ($sess_in + $sess_cc + $sess_cr) * 100) else 0 end),
            net_savings_pct: (if $sess_baseline > 0 then ((1 - $sess_actual / $sess_baseline) * 100) else 0 end)
        }
    }
')

# ANSI escapes — emitted only when stdout is a TTY and NO_COLOR is unset, so
# piped output (skill invocations, redirects, CI logs) is plain text and the
# table stays readable. https://no-color.org/ for the env-var convention.
if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]]; then
    BOLD=$'\e[1m'; DIM=$'\e[2m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'; RED=$'\e[31m'; RESET=$'\e[0m'
else
    BOLD=''; DIM=''; GREEN=''; YELLOW=''; RED=''; RESET=''
fi

fmt_tokens() {
    awk -v n="$1" 'BEGIN {
        if (n >= 1e6)     printf "%.1fM", n/1e6;
        else if (n >= 1e3) printf "%.1fk", n/1e3;
        else               printf "%d", n;
    }'
}

color_pct() {
    # Color a percentage value: green high, yellow mid, red low. Pass thresholds.
    local val="$1" high="$2" mid="$3"
    local c
    if   awk "BEGIN{exit !($val >= $high)}"; then c="$GREEN"
    elif awk "BEGIN{exit !($val >= $mid)}";  then c="$YELLOW"
    else c="$RED"
    fi
    printf "%s%s%s" "$c" "$val" "$RESET"
}

color_signed() {
    # For savings: positive green, near-zero yellow, negative red.
    local val="$1"
    if   awk "BEGIN{exit !($val >= $SAVE_GREEN)}"; then printf "%s+%.0f%%%s" "$GREEN"  "$val" "$RESET"
    elif awk "BEGIN{exit !($val >= 0)}";            then printf "%s+%.0f%%%s" "$YELLOW" "$val" "$RESET"
    else printf "%s%.0f%%%s ⚠" "$RED" "$val" "$RESET"
    fi
}

# Right-align content to a visible-width target. Strips ANSI escapes to compute
# width, then prints leading spaces followed by the content. Used for any cell
# whose visible width can't be measured by printf %Ns — ANSI-colored cells, or
# cells containing multibyte symbols (▼ ⊕ ⊖). Relies on ${#var} returning char
# count, which requires a UTF-8 locale for multibyte input.
pad_to() {
    local content="$1" target="$2"
    local visible visible_len pad
    visible=$(sed -E $'s/\033\\[[0-9;]*m//g' <<<"$content")
    visible_len=${#visible}
    pad=$((target - visible_len))
    (( pad > 0 )) && printf "%*s" "$pad" ""
    printf "%s" "$content"
}

echo
printf "${BOLD}Cache report${RESET} ${DIM}session ${SESSION_ID:0:8}…${RESET}\n"
echo

# Session section
SESS=$(jq -c '.session' <<<"$REPORT")
read -r S_IN S_CC S_CR S_OUT S_HIT S_SAVE <<<"$(jq -r '"\(.total_input_tokens) \(.cache_creation_tokens) \(.cache_read_tokens) \(.total_output_tokens) \(.hit_pct) \(.net_savings_pct)"' <<<"$SESS")"

printf "${BOLD}Session${RESET}\n"
S_TOTAL_IN=$((S_IN + S_CC + S_CR))
printf "  ${DIM}Tokens:${RESET}     ▼%s ▲%s  ${DIM}cache${RESET} ⊕%s ⊖%s\n" \
    "$(fmt_tokens "$S_TOTAL_IN")" "$(fmt_tokens "$S_OUT")" \
    "$(fmt_tokens "$S_CC")" "$(fmt_tokens "$S_CR")"
printf "  ${DIM}Hit ratio:${RESET}  %s%%   ${DIM}Net savings vs no-cache:${RESET} %s\n" \
    "$(color_pct "$(printf "%.0f" "$S_HIT")" "$SESS_HIT_GREEN" "$SESS_HIT_YELLOW")" \
    "$(color_signed "$S_SAVE")"
echo

# Per-agent breakdown header. First six columns are ASCII so they use printf
# %Ns; the three token columns carry multibyte symbol headers and need pad_to.
printf "${BOLD}Per-agent breakdown${RESET}\n"
HEADER_FMT="${BOLD}  %-${COL_AGENT}s %${COL_RUNS}s %${COL_MEDIAN}s %${COL_WARM}s %${COL_INRUN}s %${COL_SAVE}s${RESET}"
printf "$HEADER_FMT" "Agent" "Runs" "Median turns" "Warm-start %" "In-run reuse %" "Net savings %"
printf " "; pad_to "${BOLD}▼${RESET}" "$COL_TIN"
printf " "; pad_to "${BOLD}⊕${RESET}" "$COL_CC"
printf " "; pad_to "${BOLD}⊖${RESET}" "$COL_CR"
printf "\n"
# Rule spans all nine columns + 8 single-space separators.
RULE_WIDTH=$(( COL_AGENT + COL_RUNS + COL_MEDIAN + COL_WARM + COL_INRUN + COL_SAVE + COL_TIN + COL_CC + COL_CR + 8 ))
printf "  ${DIM}"; printf '─%.0s' $(seq 1 "$RULE_WIDTH"); printf "${RESET}\n"

while IFS= read -r row; do
    AGENT=$(jq -r '.agent_type' <<<"$row")
    RUNS=$(jq -r '.runs' <<<"$row")
    MEDTURNS=$(jq -r '.median_turns' <<<"$row")
    WARM=$(jq -r '.warm_start_pct' <<<"$row")
    INRUN=$(jq -r '.in_run_reuse_pct' <<<"$row")
    SAVE=$(jq -r '.net_savings_pct' <<<"$row")
    TOT_IN=$(jq -r '.tot_in' <<<"$row")
    TOT_CC=$(jq -r '.tot_cc' <<<"$row")
    TOT_CR=$(jq -r '.tot_cr' <<<"$row")
    tin_disp="▼$(fmt_tokens $((TOT_IN + TOT_CC + TOT_CR)))"
    cc_disp="⊕$(fmt_tokens "$TOT_CC")"
    cr_disp="⊖$(fmt_tokens "$TOT_CR")"

    DISP_AGENT="$AGENT"
    if (( ${#DISP_AGENT} > COL_AGENT - 2 )); then
        DISP_AGENT="${DISP_AGENT:0:$((COL_AGENT - 3))}…"
    fi

    fmt_med=$(awk -v n="$MEDTURNS" 'BEGIN{printf "%.1f", n}')
    if [[ "$WARM" == "null" ]]; then
        warm_disp="${DIM}n/a${RESET}"
    else
        warm_int=$(printf "%.0f" "$WARM")
        warm_disp=$(color_pct "$warm_int" "$AGENT_PCT_GREEN" "$AGENT_PCT_YELLOW")"%"
    fi
    if [[ "$INRUN" == "null" ]]; then
        inrun_disp="${DIM}n/a${RESET}"
    else
        inrun_int=$(printf "%.0f" "$INRUN")
        inrun_disp=$(color_pct "$inrun_int" "$AGENT_PCT_GREEN" "$AGENT_PCT_YELLOW")"%"
    fi
    save_disp=$(color_signed "$SAVE")

    # The plain cells use printf widths; the colored cells use pad_to so the
    # ANSI escapes don't throw off the visible width.
    printf "  %-${COL_AGENT}s %${COL_RUNS}d %${COL_MEDIAN}s " "$DISP_AGENT" "$RUNS" "$fmt_med"
    pad_to "$warm_disp"  "$COL_WARM"
    printf " "
    pad_to "$inrun_disp" "$COL_INRUN"
    printf " "
    pad_to "$save_disp"  "$COL_SAVE"
    printf " "; pad_to "$tin_disp" "$COL_TIN"
    printf " "; pad_to "$cc_disp"  "$COL_CC"
    printf " "; pad_to "$cr_disp"  "$COL_CR"
    printf "\n"
done < <(jq -c '.rows[]' <<<"$REPORT")

echo
