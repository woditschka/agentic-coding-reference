#!/usr/bin/env bash
# Guards for harness/materialize.sh:
#   1. RUNTIME_DIRS in materialize.sh stays in sync with the directory entries of
#      RUNTIME_PATHS in brief_doctor.py — the extras-scan must cover exactly the
#      harness-owned runtime trees, no more, no less.
#   2. A clean re-install reports zero extras; a planted orphan (stray file in a
#      harness-managed unit) and a planted extension (a new skill dir) are both
#      reported as extras.
#
#   harness/test-materialize.sh        # exits non-zero on any failure
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
doctor="$here/core/.claude/skills/doctor/scripts/brief_doctor.py"
fail=0

extras_of() { # parse the extras block from a materialize run's stdout
  sed -n '/^--- extras:/,/^--- end extras ---$/p' | grep -vE '^--- '
}

# --- 1. parity: materialize RUNTIME_DIRS == brief_doctor RUNTIME_PATHS dirs ---
mat_dirs="$(sed -n '/RUNTIME_DIRS=(/,/^)/p' "$here/materialize.sh" \
  | grep -oE '[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+' | sort -u)"
doc_dirs="$(python3 - "$doctor" <<'PY'
import re, sys
src = open(sys.argv[1]).read()
block = re.search(r'RUNTIME_PATHS\s*=\s*\[(.*?)\]', src, re.S).group(1)
paths = re.findall(r'"([^"]+)"', block)
dirs = [p for p in paths if '.' not in p.split('/')[-1]]  # no extension => directory
print('\n'.join(sorted(set(dirs))))
PY
)"
if [ "$mat_dirs" = "$doc_dirs" ]; then
  echo "ok   parity: RUNTIME_DIRS matches brief_doctor RUNTIME_PATHS dirs"
else
  echo "FAIL parity: materialize RUNTIME_DIRS != brief_doctor RUNTIME_PATHS dirs"
  echo "--- materialize ---"; echo "$mat_dirs"
  echo "--- doctor ---";      echo "$doc_dirs"
  fail=1
fi

# --- 2. extras detection ---
stack=go
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
"$here/materialize.sh" "$stack" "$tmp" >/dev/null

clean="$("$here/materialize.sh" "$stack" "$tmp" | extras_of || true)"
if [ -z "$clean" ]; then
  echo "ok   clean re-install reports no extras"
else
  echo "FAIL clean re-install reported extras:"; echo "$clean"; fail=1
fi

# plant an orphan (stray file inside a harness-managed skill) and an extension
mkdir -p "$tmp/.claude/skills/tdd-workflow"
echo stale > "$tmp/.claude/skills/tdd-workflow/STALE.md"
mkdir -p "$tmp/.claude/skills/custom-x"
echo custom > "$tmp/.claude/skills/custom-x/SKILL.md"

reported="$("$here/materialize.sh" "$stack" "$tmp" | extras_of || true)"
for p in ".claude/skills/tdd-workflow/STALE.md" ".claude/skills/custom-x/SKILL.md"; do
  if printf '%s\n' "$reported" | grep -qxF "$p"; then
    echo "ok   extra reported: $p"
  else
    echo "FAIL extra not reported: $p"; fail=1
  fi
done

if [ "$fail" -eq 0 ]; then
  echo "PASS test-materialize"
else
  echo "FAIL test-materialize"; exit 1
fi
