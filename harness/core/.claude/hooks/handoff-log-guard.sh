#!/usr/bin/env bash
# PreToolUse(Write|Edit|MultiEdit|NotebookEdit + Bash) hook — deny raw writes
# to the handoff log, defer everything else.
#
# The pipeline's only sanctioned write to .scratch/handoff.jsonl is `python3
# scripts/handoff.py append` (the handoff-allow.sh hook pre-approves exactly
# that form). This guard closes the other direction: an agent that tries to
# write the log directly — an Edit/Write tool call on the file, or a shell
# redirection / tee onto it — is DENIED with a message naming the sanctioned
# path. A raw write skips schema validation and canonical formatting; one
# missing trailing newline glues two records onto a line and the log stops
# parsing.
#
# Safety model. The guard denies ONLY unquoted redirect/tee signatures that
# target the log path, scanned outside single-line quoted strings and outside
# a quoted heredoc body (both are inert data — a command may legitimately
# *mention* the forbidden form, e.g. a commit message or a doc edit; a quote
# pair spanning a newline is NOT stripped, so a multi-line quoted mention
# still denies — a recoverable false positive, never a bypass). A sanctioned
# `python3 scripts/handoff.py` first line free of shell metacharacters is
# handoff-allow.sh's jurisdiction and is dropped from the scan — but its
# trailing lines stay scanned, so a redirect chained after the heredoc closer
# is still denied. handoff-allow.sh only ALLOWS when nothing follows the
# closer, so a deny here can never override its ALLOW. Everything else DEFERS
# (exit 0, no decision) to the normal permission rules.
#
# Fail direction: a missing jq, malformed stdin, or a signature hidden in a
# shape the scan does not parse DEFERS or is missed — the guard is a
# convenience backstop, not the sole control. The deterministic, cross-tool
# backstop is the quality gate's `python3 scripts/handoff.py validate` step,
# which fails on any corrupted log regardless of which tool or agent wrote
# it. Commit this hook together with .claude/settings.json.

defer() { exit 0; }  # no decision -> fall through to normal permission rules
deny() {
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' \
    "Raw writes to .scratch/handoff.jsonl are prohibited. Append through the logic layer instead: python3 scripts/handoff.py append <type> with the record on stdin via a quoted heredoc (see the handoff-append skill)."
  exit 0
}

command -v jq >/dev/null 2>&1 || defer

payload=$(cat)
tool=$(jq -r '.tool_name // empty' <<<"$payload" 2>/dev/null)
[ -n "$tool" ] || defer

# The log path: preceded by start-of-token or a slash (absolute and nested
# forms count; foo.scratch/... does not), followed by a hard token end.
PATH_SEG='([^[:space:]]*/)?\.scratch/handoff\.jsonl([[:space:];&|)]|$)'

case "$tool" in
  Write|Edit|MultiEdit|NotebookEdit)
    fp=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty' <<<"$payload" 2>/dev/null)
    [ -n "$fp" ] || defer
    if printf '%s' "$fp" | grep -qE '(^|/)\.scratch/handoff\.jsonl$'; then deny; fi
    defer
    ;;
  Bash)
    cmd=$(jq -r '.tool_input.command // empty' <<<"$payload" 2>/dev/null)
    [ -n "$cmd" ] || defer

    first=${cmd%%$'\n'*}
    first=${first#"${first%%[![:space:]]*}"}

    rest=""
    [ "$first" != "$cmd" ] && rest=${cmd#*$'\n'}
    # Drop a quoted heredoc body (inert data): keep only the lines after the
    # closing delimiter. An unquoted heredoc expands and stays scanned. A
    # `<<-` heredoc closes on a tab-indented delimiter, so match with leading
    # tabs stripped.
    delim=$(printf '%s' "$first" | sed -nE "s/.*<<-?['\"]([A-Za-z_][A-Za-z0-9_]*)['\"].*/\1/p")
    dash=""
    printf '%s' "$first" | grep -qE "<<-['\"]" && dash=1
    if [ -n "$delim" ] && [ -n "$rest" ]; then
      rest=$(printf '%s\n' "$rest" | awk -v d="$delim" -v dash="$dash" '
        seen { print; next }
        { line = $0; if (dash) sub(/^\t+/, "", line); if (line == d) seen = 1 }')
    fi
    scan="$first"$'\n'"$rest"
    # A sanctioned handoff.py first line free of shell metacharacters (the set
    # handoff-allow.sh vets) is that hook's jurisdiction — drop the line and
    # its inert record body from the scan. Its trailing lines stay in scan:
    # a redirect chained after the heredoc closer must still deny.
    case "$first" in
      'python3 scripts/handoff.py '*)
        if ! printf '%s' "$first" | grep -q '[;&|>()$`]'; then
          scan="$rest"
        fi
        ;;
    esac
    # Strip quoted segments: a path inside quotes is data to this scan. A
    # quoted-path redirect is therefore missed by design — the gate's
    # validate step catches it.
    scan=$(printf '%s' "$scan" | sed "s/'[^']*'//g; s/\"[^\"]*\"//g")

    if printf '%s' "$scan" | grep -qE ">{1,2}[[:space:]]*$PATH_SEG"; then deny; fi
    if printf '%s' "$scan" | grep -qE "(^|[;&|[:space:]])tee[[:space:]]+((-a|--append)[[:space:]]+)?$PATH_SEG"; then deny; fi
    defer
    ;;
  *) defer ;;
esac
