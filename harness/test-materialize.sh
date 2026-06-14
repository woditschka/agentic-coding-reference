#!/usr/bin/env bash
# Guards for harness/materialize.sh:
#   1. RUNTIME_DIRS in materialize.sh stays in sync with the directory entries of
#      RUNTIME_PATHS in brief_doctor.py — the extras-scan must cover exactly the
#      harness-owned runtime trees, no more, no less.
#   2. A clean re-install reports zero extras; a planted orphan (stray file in a
#      harness-managed unit) and a planted extension (a new skill dir) are both
#      reported as extras.
#   3. The marketplace channel installs only the engine sliver (scripts, schemas,
#      templates, tool config), never the plugin-delivered tool surfaces.
#
#   harness/test-materialize.sh        # exits non-zero on any failure
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
doctor="$here/core/scripts/brief_doctor.py"
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

# --- 3. marketplace channel: engine sliver only, no tool surfaces ---
# The plugin delivers skills/agents/hooks; materialize keeps only the
# non-discovered runtime (scripts, schemas, templates, tool config).
mkt="$(mktemp -d)"
mkdir -p "$mkt/scripts"
cat > "$mkt/scripts/layout.toml" <<'EOF'
[harness]
channel = "marketplace"
spec_version = "0.1.0"
tools = ["claude", "copilot", "junie"]
extensions = []
EOF
"$here/materialize.sh" "$stack" "$mkt" >/dev/null
surfaced=0
for d in .claude/skills .claude/agents .claude/hooks .github/agents .opencode/agents .junie/agents; do
  if [ -n "$(find "$mkt/$d" -type f 2>/dev/null)" ]; then
    echo "FAIL marketplace installed tool surface $d (the plugin delivers it)"; fail=1; surfaced=1
  fi
done
[ "$surfaced" -eq 0 ] && echo "ok   marketplace omits tool surfaces (skills/agents/hooks)"
for f in scripts/handoff.py scripts/brief_doctor.py scripts/brief-expectations.toml \
         schemas/scratch/prd-entry.schema.json \
         .claude/templates/implementation-plan.md .junie/config.json; do
  if [ -f "$mkt/$f" ]; then
    echo "ok   marketplace keeps engine sliver: $f"
  else
    echo "FAIL marketplace omitted engine sliver: $f"; fail=1
  fi
done
rm -rf "$mkt"

if [ "$fail" -eq 0 ]; then
  echo "PASS test-materialize"
else
  echo "FAIL test-materialize"; exit 1
fi
