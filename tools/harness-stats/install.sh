#!/usr/bin/env bash
# Install or update the harness-stats tooling into ~/.claude/. This directory is
# the source of truth; the harness-stats-setup skill is the interactive
# front-end (drift table -> user approval -> apply).
#
#   tools/harness-stats/install.sh check   # report per-target drift, change nothing
#   tools/harness-stats/install.sh apply   # copy files, merge settings, smoke-test
#
# apply needs jq (for the settings.json merge). Claude Code must be restarted
# afterward: settings.json and skills are read at startup.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
mode="${1:?usage: install.sh check|apply}"
dst="$HOME/.claude"

pairs=(
  "statusline.sh|$dst/statusline.sh"
  "cc_accounting.py|$dst/cc_accounting.py"
  "cache-report.sh|$dst/cache-report.sh"
  "skills/cache-report/SKILL.md|$dst/skills/cache-report/SKILL.md"
)

file_status() { # <src> <target>
  [ -f "$2" ] || { echo "missing"; return; }
  if diff -q "$1" "$2" >/dev/null 2>&1; then
    echo "identical"
  else
    echo "drift ($( (diff "$1" "$2" || true) | grep -c '^[<>]') lines)"
  fi
}

settings_status() {
  local f="$dst/settings.json" want="$dst/statusline.sh" cmd
  [ -f "$f" ] || { echo "missing (no settings.json)"; return; }
  command -v jq >/dev/null 2>&1 || { echo "unknown (jq not installed)"; return; }
  cmd="$(jq -r '.statusLine.command // empty' "$f" 2>/dev/null || true)"
  if [ "$cmd" = "$want" ]; then echo "identical"
  elif [ -z "$cmd" ]; then echo "missing (no statusLine key)"
  else echo "drift (command is $cmd)"
  fi
}

case "$mode" in
check)
  for p in "${pairs[@]}"; do
    src="$here/${p%%|*}"; tgt="${p#*|}"
    printf '%-60s %s\n' "$tgt" "$(file_status "$src" "$tgt")"
  done
  printf '%-60s %s\n' "$dst/settings.json statusLine" "$(settings_status)"
  ;;

apply)
  command -v jq >/dev/null 2>&1 || { echo "FAIL: jq is required for the settings.json merge" >&2; exit 1; }
  # Refuse before touching anything: a merge into unparseable JSON would die
  # mid-apply, leaving the files copied but settings.json unmerged.
  if [ -f "$dst/settings.json" ] && ! jq empty "$dst/settings.json" >/dev/null 2>&1; then
    echo "FAIL: $dst/settings.json is not valid JSON — fix it, then re-run (nothing installed)" >&2
    exit 1
  fi

  for p in "${pairs[@]}"; do
    src="$here/${p%%|*}"; tgt="${p#*|}"
    mkdir -p "$(dirname "$tgt")"
    cp "$src" "$tgt"
    case "$tgt" in *.sh | *.py) chmod +x "$tgt" ;; esac
    echo "installed $tgt"
  done

  prev="$(jq -r '.statusLine.command // empty' "$dst/settings.json" 2>/dev/null || true)"
  if [ -n "$prev" ] && [ "$prev" != "$dst/statusline.sh" ]; then
    echo "note: replacing statusLine.command (was: $prev)"
  fi
  mkdir -p "$dst"
  # Absolute path in settings.json — "~" is unreliable across Claude Code versions.
  tmp="$(mktemp)"
  trap 'rm -f "$tmp"' EXIT
  # Own only type and command; a user's padding (and any other statusLine key)
  # survives the merge. padding defaults to 1 when absent.
  if [ -f "$dst/settings.json" ]; then
    jq --arg cmd "$dst/statusline.sh" \
       '.statusLine = ((.statusLine // {}) + {type: "command", command: $cmd}) | .statusLine.padding //= 1' \
       "$dst/settings.json" > "$tmp"
  else
    jq -n --arg cmd "$dst/statusline.sh" \
       '{statusLine: {type: "command", command: $cmd, padding: 1}}' > "$tmp"
  fi
  mv "$tmp" "$dst/settings.json"
  echo "merged statusLine into $dst/settings.json"

  # Smoke tests — a failing install must not report success. Likely culprits on
  # failure: missing jq/awk, or a stat call that fell through GNU and BSD paths.
  # Claude Code encodes project dirs by mapping every non-alphanumeric
  # character to '-' (must match cache-report.sh resolve_project).
  proj_dir="$dst/projects/$(pwd | sed 's![^a-zA-Z0-9]!-!g')"
  latest="$(ls -t "$proj_dir"/*.jsonl 2>/dev/null | head -1 || true)"
  sid="$(basename "${latest:-none}" .jsonl)"
  # jq builds the JSON — a working directory containing a quote or backslash
  # must not break the smoke payload.
  smoke_json="$(jq -n --arg cwd "$PWD" --arg sid "$sid" --arg tp "${latest:-}" \
    '{workspace: {current_dir: $cwd}, cwd: $cwd, session_id: $sid, transcript_path: $tp}')"
  if out="$(printf '%s' "$smoke_json" | "$dst/statusline.sh" 2>&1)" && [ -n "$out" ]; then
    echo "smoke: statusline OK"
  else
    echo "FAIL: statusline smoke test — output was: $out" >&2; exit 1
  fi
  # A fresh machine may have no transcripts yet — "No transcripts" is a healthy
  # empty state, not an install failure.
  crout="$("$dst/cache-report.sh" --list 2>&1 || true)"
  if printf '%s\n' "$crout" | head -1 | grep -qE 'SESSION_ID|No transcripts'; then
    echo "smoke: cache-report OK"
  else
    echo "FAIL: cache-report smoke test — output was: $crout" >&2; exit 1
  fi
  echo "done — restart Claude Code to load the statusline and the cache-report skill"
  ;;

*)
  echo "usage: install.sh check|apply" >&2; exit 1 ;;
esac
