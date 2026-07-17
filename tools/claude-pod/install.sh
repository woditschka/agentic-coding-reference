#!/usr/bin/env bash
# install.sh — install claude-pod centrally.
#   install.sh check   show drift between the repo copies and the installed targets
#   install.sh apply   install/update the targets (default when run with no argument)
#   command -> ~/.local/bin/claude-pod        (override: BIN=/usr/local/bin, may need sudo)
#   data    -> ~/.config/claude-pod/{Dockerfile,claude-pod.cfg,ide_preflight.py,egress_rules.py,egress_init.sh}
#             (override: CLAUDE_POD_HOME)
# An existing claude-pod.cfg is never overwritten — your policy stays yours.
# ide_preflight.py is the IDE-oracle preflight; egress_rules.py + egress_init.sh
# are the default-deny host-egress pair (ADR 2026-07-17). Without them the
# preflight silently no-ops and the egress filter warns instead of installing.
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
    printf '%-40s %s\n' "$DATA/egress_rules.py"  "$(status "$SRC/egress_rules.py" "$DATA/egress_rules.py")"
    printf '%-40s %s\n' "$DATA/egress_init.sh"   "$(status "$SRC/egress_init.sh" "$DATA/egress_init.sh")"
    # A leftover of the retired in-pod relay is drift too: apply removes it.
    [ -e "$DATA/ide_relay.py" ] && printf '%-40s %s\n' "$DATA/ide_relay.py" "stale (retired 2026-07-17; removed on apply)"
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
    # The preflight runs on the host; the egress pair is mounted into the
    # one-shot init container. All must land beside the Dockerfile so the
    # installed claude-pod finds them at $CLAUDE_POD_HOME (its $SELF_DIR is
    # ~/.local/bin). The retired in-pod relay is removed where present.
    install -m 0644 "$SRC/ide_preflight.py" "$DATA/ide_preflight.py"
    install -m 0644 "$SRC/egress_rules.py"  "$DATA/egress_rules.py"
    install -m 0644 "$SRC/egress_init.sh"   "$DATA/egress_init.sh"
    rm -f "$DATA/ide_relay.py"
    if [ -f "$DATA/claude-pod.cfg" ]; then
      echo "kept existing config: $DATA/claude-pod.cfg"
    else
      install -m 0644 "$SRC/claude-pod.cfg" "$DATA/claude-pod.cfg"
    fi
    "$BIN/claude-pod" help >/dev/null || { echo "smoke test failed: $BIN/claude-pod help" >&2; exit 1; }
    echo "installed command: $BIN/claude-pod"
    echo "installed data:    $DATA/Dockerfile, $DATA/claude-pod.cfg, $DATA/ide_preflight.py, $DATA/egress_rules.py, $DATA/egress_init.sh"
    case ":$PATH:" in *":$BIN:"*) ;; *) echo "NOTE: $BIN is not on your PATH — add it to use 'claude-pod' directly";; esac
    ;;
  *) echo "usage: install.sh [check|apply]" >&2; exit 2;;
esac
