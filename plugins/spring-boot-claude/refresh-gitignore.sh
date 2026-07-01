#!/usr/bin/env bash
# Ensure the harness runtime gitignore lines are present in a consumer's
# .gitignore. The deterministic, marker-free analogue of refresh-chapters.sh:
# it makes the harness-owned lines current without writing any BEGIN/END
# sentinel into the project file.
#
#   refresh-gitignore.sh <target-gitignore> <block-source> <channel>
#
# block-source is harness/init/core/gitignore-runtime.txt — the canonical set of
# harness runtime paths plus the .scratch/ ledger, one per line (comments and
# blanks ignored). Harness ownership is identified by exact match against this
# template, which is what lets the refresh stay marker-free and baseline-free:
# no sentinels, no recorded version.
#
# The operation is ENSURE-PRESENT, and only that:
#   - a template line the target lacks is appended (a new engine file that must
#     be ignored now reaches an existing project);
#   - a project's own ignores and its "!<extension>/" re-includes are never
#     touched, removed, or reordered.
# It never removes a line: a path the template dropped lingers as a harmless
# over-broad ignore, left for the advisory reconciliation or a human to prune.
#
# Channel-aware. Under "copy" the runtime is committed, so only the .scratch/
# ledger is ensured. Under manifest/marketplace the runtime is out-of-band, so
# every runtime path is ensured too. The channel is read, never changed.
set -euo pipefail

target="${1:?usage: refresh-gitignore.sh <target-gitignore> <block-source> <channel>}"
source="${2:?usage: refresh-gitignore.sh <target-gitignore> <block-source> <channel>}"
channel="${3:?usage: refresh-gitignore.sh <target-gitignore> <block-source> <channel>}"

[ -f "$source" ] || { echo "refresh-gitignore: missing block source $source" >&2; exit 1; }
touch "$target"

# Collect the harness lines the target is missing. A line is desired when it is
# .scratch/ (every channel) or — off the copy channel — a runtime path. Comments
# and blank lines in the template are skipped; the exact line is matched with -x.
missing=""
added=0
while IFS= read -r line; do
  case "$line" in ''|\#*) continue ;; esac
  if [ "$line" != ".scratch/" ] && [ "$channel" = "copy" ]; then
    continue
  fi
  if ! grep -qxF "$line" "$target"; then
    missing="${missing}${line}
"
    added=$((added + 1))
  fi
done < "$source"

if [ "$added" -gt 0 ]; then
  # Guarantee the target ends in a newline before appending, so a missing path
  # can never merge onto an unterminated final line (silent corruption of a
  # project ignore). tail -c1 is empty when the last byte already is a newline.
  if [ -s "$target" ] && [ -n "$(tail -c1 "$target")" ]; then
    printf '\n' >> "$target"
  fi
  # Append the missing lines, under a one-line comment the first time we add any
  # (so a fresh or minimal .gitignore does not gain a bare, contextless path).
  # The header decision reads $target, so resolve it before opening the append
  # redirect — never read and write the same file in one pipeline.
  header=""
  grep -qi 'harness runtime' "$target" || header=$'\n# harness runtime (harness-owned; kept current on upgrade)\n'
  printf '%s%s' "$header" "$missing" >> "$target"
fi

echo "gitignore: $added path(s) added"
