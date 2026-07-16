#!/usr/bin/env bash
# install.sh — install claude-pod centrally.
#   install.sh check   show drift between the repo copies and the installed targets
#   install.sh apply   install/update the targets (default when run with no argument)
#   command -> ~/.local/bin/claude-pod        (override: BIN=/usr/local/bin, may need sudo)
#   data    -> ~/.config/claude-pod/{Dockerfile,claude-pod.cfg,ide_preflight.py,ide_relay.py}
#             (override: CLAUDE_POD_HOME)
# An existing claude-pod.cfg is never overwritten — your policy stays yours.
# The two .py files are the IDE-oracle preflight and relay; without them the
# preflight silently no-ops and --ide cannot bridge (see the check-sync guard).
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd -P)"
BIN="${BIN:-$HOME/.local/bin}"
DATA="${CLAUDE_POD_HOME:-$HOME/.config/claude-pod}"
MODE="${1:-apply}"

status(){ # <repo-copy> <installed-target>
  if [ ! -e "$2" ]; then echo "missing"
  elif cmp -s "$1" "$2"; then echo "identical"
  else echo "drift ($(diff "$1" "$2" | grep -c '^[<>]') lines)"; fi
}

case "$MODE" in
  check)
    printf '%-40s %s\n' "$BIN/claude-pod"      "$(status "$SRC/claude-pod" "$BIN/claude-pod")"
    printf '%-40s %s\n' "$DATA/Dockerfile"     "$(status "$SRC/Dockerfile" "$DATA/Dockerfile")"
    printf '%-40s %s\n' "$DATA/ide_preflight.py" "$(status "$SRC/ide_preflight.py" "$DATA/ide_preflight.py")"
    printf '%-40s %s\n' "$DATA/ide_relay.py"     "$(status "$SRC/ide_relay.py" "$DATA/ide_relay.py")"
    # the cfg is your policy: apply installs it only when absent, and never overwrites an existing one
    cfg_status="$(status "$SRC/claude-pod.cfg" "$DATA/claude-pod.cfg")"
    case "$cfg_status" in
      missing) printf '%-40s %s\n' "$DATA/claude-pod.cfg" "missing (installed on apply)";;
      *)       printf '%-40s %s\n' "$DATA/claude-pod.cfg" "$cfg_status (kept on apply — your policy)";;
    esac
    ;;
  apply)
    mkdir -p "$BIN" "$DATA"
    install -m 0755 "$SRC/claude-pod" "$BIN/claude-pod"
    install -m 0644 "$SRC/Dockerfile" "$DATA/Dockerfile"
    # The IDE-oracle scripts: preflight runs on the host, the relay is mounted
    # into the pod. Both must land beside the Dockerfile so the installed
    # claude-pod finds them at $CLAUDE_POD_HOME (its $SELF_DIR is ~/.local/bin).
    install -m 0644 "$SRC/ide_preflight.py" "$DATA/ide_preflight.py"
    install -m 0644 "$SRC/ide_relay.py"     "$DATA/ide_relay.py"
    if [ -f "$DATA/claude-pod.cfg" ]; then
      echo "kept existing config: $DATA/claude-pod.cfg"
    else
      install -m 0644 "$SRC/claude-pod.cfg" "$DATA/claude-pod.cfg"
    fi
    "$BIN/claude-pod" help >/dev/null || { echo "smoke test failed: $BIN/claude-pod help" >&2; exit 1; }
    echo "installed command: $BIN/claude-pod"
    echo "installed data:    $DATA/Dockerfile, $DATA/claude-pod.cfg, $DATA/ide_preflight.py, $DATA/ide_relay.py"
    case ":$PATH:" in *":$BIN:"*) ;; *) echo "NOTE: $BIN is not on your PATH — add it to use 'claude-pod' directly";; esac
    ;;
  *) echo "usage: install.sh [check|apply]" >&2; exit 2;;
esac
