#!/usr/bin/env bash
# install.sh — install claude-dev centrally.
#   install.sh check         show drift between the repo copies and the installed targets
#   install.sh apply         install/update the targets (default when run with no argument)
#   install.sh reset-config  restore the shipped claude-dev.toml (keeps the old one as .bak)
#   command -> ~/.local/bin/claude-dev              (override: BIN=/usr/local/bin, may need sudo)
#   data    -> ~/.config/claude-dev/{Dockerfile,claude-dev.toml,
#                                   claude_dev_config.py,claude_dev_scrub.py,ide_preflight.py}
#             (override: CLAUDE_DEV_HOME)
#
# The policy file is the operator's: an existing claude-dev.toml is never overwritten by
# apply. claude_dev_config.py parses that policy and generates the proxy's
# rules; claude_dev_scrub.py builds the container-private ~/.claude.json
# replica; ide_preflight.py is the IDE-oracle preflight.
#
# No migration path: this installs the current tool and nothing else. Coming
# from the claude-pod predecessor, carry its data dir (saved login, container
# state) by hand ONCE, before installing, or the cost is a fresh /login:
#     mv ~/.config/claude-pod ~/.config/claude-dev
#     rm -f ~/.local/bin/claude-pod
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd -P)"
BIN="${BIN:-$HOME/.local/bin}"
DATA="${CLAUDE_DEV_HOME:-$HOME/.config/claude-dev}"
MODE="${1:-apply}"

# Files whose content this tool owns: apply always overwrites them.
managed=(Dockerfile claude_dev_config.py claude_dev_scrub.py ide_preflight.py)
# Files that become the operator's policy: apply installs them only when absent.
policy=(claude-dev.toml)

status(){ # <repo-copy> <installed-target>
  if [ ! -e "$2" ]; then echo "missing"
  elif cmp -s "$1" "$2"; then echo "identical"
  else echo "drift ($(diff "$1" "$2" | grep -c '^[<>]') lines)"; fi
}

# The statusline lives in ~/.claude, which is not shared wholesale — so a
# config this script CREATES shares exactly the harness-stats files present
# at that moment. Written into the [mounts] ro array as the file is generated;
# an existing config is never rewritten.
write_config(){ # <dest>
  local found=() f
  for f in harness-statusline.sh accounting.py cache-report.sh; do
    [ -f "$HOME/.claude/$f" ] && found+=("  \"\$HOME/.claude/$f\",")
  done
  if [ ${#found[@]} -eq 0 ]; then
    install -m 0644 "$SRC/claude-dev.toml" "$1"
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
  ' "$SRC/claude-dev.toml" > "$tmp"; then
    rm -f "$tmp"; echo "could not generate $1" >&2; return 1
  fi
  mv "$tmp" "$1"
  chmod 644 "$1"
}

case "$MODE" in
  check)
    printf '%-46s %s\n' "$BIN/claude-dev" "$(status "$SRC/claude-dev" "$BIN/claude-dev")"
    for f in "${managed[@]}"; do
      printf '%-46s %s\n' "$DATA/$f" "$(status "$SRC/$f" "$DATA/$f")"
    done
    for f in "${policy[@]}"; do
      s="$(status "$SRC/$f" "$DATA/$f")"
      case "$s" in
        missing) printf '%-46s %s\n' "$DATA/$f" "missing (installed on apply)";;
        *)       printf '%-46s %s\n' "$DATA/$f" "$s (kept on apply — operator policy; reset-config replaces it)";;
      esac
    done
    # An installed config apply would KEEP but the launcher now refuses (a
    # retired table, a typo) makes apply's own smoke test fail after the managed
    # files are already overwritten. Say so here, while it is still a report.
    if [ -f "$DATA/claude-dev.toml" ] && ! err="$(python3 "$SRC/claude_dev_config.py" settings "$DATA/claude-dev.toml" 2>&1 >/dev/null)"; then
      printf '%-46s %s\n' "$DATA/claude-dev.toml" "REFUSED by this version — fix it before apply, or reset-config"
      printf '%-46s %s\n' "" "${err#claude-dev: }"
    fi
    : # check reports; a clean report is a zero exit, not the last test's verdict
    ;;
  apply)
    mkdir -p "$BIN" "$DATA"
    install -m 0755 "$SRC/claude-dev" "$BIN/claude-dev"
    for f in "${managed[@]}"; do install -m 0644 "$SRC/$f" "$DATA/$f"; done
    for f in "${policy[@]}"; do
      if [ -f "$DATA/$f" ]; then
        echo "kept existing: $DATA/$f"
      else
        write_config "$DATA/$f"
      fi
    done
    "$BIN/claude-dev" help >/dev/null || { echo "smoke test failed: $BIN/claude-dev help" >&2; exit 1; }
    echo "installed command: $BIN/claude-dev"
    echo "installed data:    $DATA/{$(IFS=,; echo "${managed[*]}"),$(IFS=,; echo "${policy[*]}")}"
    case ":$PATH:" in *":$BIN:"*) ;; *) echo "NOTE: $BIN is not on PATH — add it to use 'claude-dev' directly";; esac
    ;;
  reset-config)
    mkdir -p "$DATA"
    for f in "${policy[@]}"; do
      [ -f "$DATA/$f" ] && cp "$DATA/$f" "$DATA/$f.bak" && echo "kept old: $DATA/$f.bak"
      write_config "$DATA/$f"
      echo "restored: $DATA/$f"
    done
    ;;
  *) echo "usage: install.sh [check|apply|reset-config]" >&2; exit 2;;
esac
