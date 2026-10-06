#!/usr/bin/env bash
# install.sh — install one agent-dev command centrally. Each tool installs on
# its own: one command and its own copy of the engine files, no other tool's.
#   install.sh <tool> check         show drift between the repo copies and the installed targets
#   install.sh <tool> apply         install/update the targets (default when no mode is given)
#   install.sh <tool> reset-config  restore the shipped policy file (keeps the old one as .bak)
# <tool> is claude (the claude-dev command).
#   command -> ~/.local/bin/<command>             (override: BIN=/usr/local/bin, may need sudo)
#   data    -> ~/.config/<command>/{agent-dev, agent_dev.py, agent_dev_config.py,
#                                   agent_dev_profiles.py, Dockerfile, open_weight_preflight.py,
#                                   <command>.toml, and the tool's own helpers}
#             (override: <COMMAND>_HOME, e.g. CLAUDE_DEV_HOME)
#
# The policy file is the operator's: an existing <command>.toml is never overwritten by
# apply. agent_dev.py parses that policy and the tool's profile and generates the proxy's
# rules; open_weight_preflight.py checks the [open-weight] model map against the peer
# before a --ow launch. claude-dev adds claude_dev_scrub.py, which builds the
# container-private ~/.claude.json replica, and ide_preflight.py, the IDE-oracle preflight.
#
# No migration path: this installs the current tool and nothing else. Coming
# from the claude-pod predecessor, carry its data dir (saved login, container
# state) by hand ONCE, before installing, or the cost is a fresh /login:
#     mv ~/.config/claude-pod ~/.config/claude-dev
#     rm -f ~/.local/bin/claude-pod
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd -P)"
BIN="${BIN:-$HOME/.local/bin}"
TOOL="${1:-}"
MODE="${2:-apply}"

# Files every command's install carries: the engine, its modules and the image.
engine=(agent-dev agent_dev.py agent_dev_config.py agent_dev_profiles.py Dockerfile open_weight_preflight.py)
case "$TOOL" in
  claude)
    CMD=claude-dev
    tool_files=(claude_dev_scrub.py ide_preflight.py);;
  *) echo "usage: install.sh <claude> [check|apply|reset-config]" >&2; exit 2;;
esac
# The data dir's override variable is the command's name, upper-cased with
# underscores and _HOME appended (claude-dev -> CLAUDE_DEV_HOME).
HOME_VAR="$(printf '%s' "$CMD" | tr 'a-z-' 'A-Z_')_HOME"
DATA="${!HOME_VAR:-$HOME/.config/$CMD}"
POLICY="$CMD.toml"

# Files whose content this tool owns: apply always overwrites them.
managed=("${engine[@]}" ${tool_files[@]+"${tool_files[@]}"})

status(){ # <repo-copy> <installed-target>
  if [ ! -e "$2" ]; then echo "missing"
  elif cmp -s "$1" "$2"; then echo "identical"
  else echo "drift ($(diff "$1" "$2" | grep -c '^[<>]') lines)"; fi
}

# The statusline lives in ~/.claude, which is not shared wholesale — so a
# config this script CREATES shares exactly the harness-stats files present
# at that moment. Written into the [mounts] ro array as the file is generated;
# an existing config is never rewritten. Claude Code's tree only: another
# tool's policy starts from the shipped file unchanged.
write_config(){ # <dest>
  local found=() f
  if [ "$TOOL" = claude ]; then
    for f in harness-statusline.sh accounting.py cache-report.sh; do
      [ -f "$HOME/.claude/$f" ] && found+=("  \"\$HOME/.claude/$f\",")
    done
  fi
  if [ ${#found[@]} -eq 0 ]; then
    install -m 0644 "$SRC/$POLICY" "$1"
    return 0
  fi
  # Replace the empty `ro = []` with the discovered entries; only that one line
  # changes. The entries pass via the ENVIRONMENT, not `awk -v`: a -v value may
  # not contain a newline, and BWK awk (macOS) refuses one — which once aborted
  # after `>` had truncated the target, leaving a zero-byte policy. Write to a
  # temp beside the destination (same filesystem, atomic mv), so a failure can
  # never leave a partial config either.
  local tmp="$1.tmp.$$"
  if ! entries="$(printf '%s\n' "${found[@]}")" awk '
    /^ro = \[\]$/ && !seen {
      print "# Written by install.sh: the harness-stats files found in ~/.claude"
      print "# at install time. ~/.claude is not shared wholesale, so the"
      print "# statusline needs these entries to work inside."
      print "ro = ["
      print ENVIRON["entries"]
      print "]"
      seen = 1
      next
    }
    { print }
  ' "$SRC/$POLICY" > "$tmp"; then
    rm -f "$tmp"; echo "could not generate $1" >&2; return 1
  fi
  mv "$tmp" "$1"
  chmod 644 "$1"
}

case "$MODE" in
  check)
    printf '%-46s %s\n' "$BIN/$CMD" "$(status "$SRC/$CMD" "$BIN/$CMD")"
    for f in "${managed[@]}"; do
      printf '%-46s %s\n' "$DATA/$f" "$(status "$SRC/$f" "$DATA/$f")"
    done
    s="$(status "$SRC/$POLICY" "$DATA/$POLICY")"
    case "$s" in
      missing) printf '%-46s %s\n' "$DATA/$POLICY" "missing (installed on apply)";;
      *)       printf '%-46s %s\n' "$DATA/$POLICY" "$s (kept on apply — operator policy; reset-config replaces it)";;
    esac
    # An installed config apply would KEEP but the launcher now refuses (a
    # retired table, a typo) makes apply's own smoke test fail after the managed
    # files are already overwritten. Say so here, while it is still a report.
    if [ -f "$DATA/$POLICY" ] && ! err="$(python3 "$SRC/agent_dev.py" --tool "$TOOL" settings "$DATA/$POLICY" 2>&1 >/dev/null)"; then
      printf '%-46s %s\n' "$DATA/$POLICY" "REFUSED by this version — fix it before apply, or reset-config"
      printf '%-46s %s\n' "" "${err#"$CMD": }"
    fi
    : # check reports; a clean report is a zero exit, not the last test's verdict
    ;;
  apply)
    mkdir -p "$BIN" "$DATA"
    install -m 0755 "$SRC/$CMD" "$BIN/$CMD"
    for f in "${managed[@]}"; do
      case "$f" in agent-dev) install -m 0755 "$SRC/$f" "$DATA/$f";; *) install -m 0644 "$SRC/$f" "$DATA/$f";; esac
    done
    if [ -f "$DATA/$POLICY" ]; then
      echo "kept existing: $DATA/$POLICY"
    else
      write_config "$DATA/$POLICY"
    fi
    "$BIN/$CMD" help >/dev/null || { echo "smoke test failed: $BIN/$CMD help" >&2; exit 1; }
    echo "installed command: $BIN/$CMD"
    echo "installed data:    $DATA/{$(IFS=,; echo "${managed[*]}"),$POLICY}"
    case ":$PATH:" in *":$BIN:"*) ;; *) echo "NOTE: $BIN is not on PATH — add it to use '$CMD' directly";; esac
    ;;
  reset-config)
    mkdir -p "$DATA"
    [ -f "$DATA/$POLICY" ] && cp "$DATA/$POLICY" "$DATA/$POLICY.bak" && echo "kept old: $DATA/$POLICY.bak"
    write_config "$DATA/$POLICY"
    echo "restored: $DATA/$POLICY"
    ;;
  *) echo "usage: install.sh <claude> [check|apply|reset-config]" >&2; exit 2;;
esac
