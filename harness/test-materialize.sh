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

# --- 1b. parity: gitignore-runtime.txt paths == brief_doctor RUNTIME_PATHS ---
# Check 1 compares directories only, so a runtime *file* present in one list but
# not the other slips through (the changeset.sh shape). This check compares
# every entry: gitignore paths normalized (strip trailing /* and /), .scratch/
# excluded (per-session state, deliberately absent from the doctor). A file
# missing from BOTH lists passes here — that shape is check 1c's catch.
gi_paths="$(grep -vE '^[[:space:]]*(#|$)' "$here/init/core/gitignore-runtime.txt" \
  | grep -v '^\.scratch/' | sed -e 's:/\*$::' -e 's:/$::' | LC_ALL=C sort -u)"
doc_paths="$(python3 - "$doctor" <<'PY'
import re, sys
src = open(sys.argv[1]).read()
block = re.search(r'RUNTIME_PATHS\s*=\s*\[(.*?)\]', src, re.S).group(1)
print('\n'.join(sorted(set(re.findall(r'"([^"]+)"', block)))))
PY
)"
if [ "$gi_paths" = "$doc_paths" ]; then
  echo "ok   parity: gitignore-runtime.txt matches brief_doctor RUNTIME_PATHS"
else
  echo "FAIL parity: gitignore-runtime.txt != brief_doctor RUNTIME_PATHS"
  echo "--- gitignore ---"; echo "$gi_paths"
  echo "--- doctor ---";    echo "$doc_paths"
  fail=1
fi

# --- 1c. coverage: every shipped scripts/ file appears in RUNTIME_PATHS ---
# Checks 1 and 1b prove the rosters agree with each other; this proves they
# agree with the shipped fileset. A new engine file added to core/scripts/ or
# stacks/*/scripts/ but to neither roster (the gate.sh shape, commit 08592dd)
# fails here instead of shipping tracked to manifest consumers.
# Keep the path below scripts/, not the basename: flattening would let a
# subdirectory file (scripts/sub/x.py) hide behind a same-named top-level
# roster entry (scripts/x.py) and ship unlisted.
shipped_scripts="$(find "$here/core/scripts" "$here"/stacks/*/scripts -type f \
  ! -name '*.pyc' ! -path '*/__pycache__/*' \
  | sed 's:.*/scripts/:scripts/:' | LC_ALL=C sort -u)"
doc_scripts="$(printf '%s\n' "$doc_paths" | grep '^scripts/')"
if [ "$shipped_scripts" = "$doc_scripts" ]; then
  echo "ok   coverage: shipped scripts/ files all in brief_doctor RUNTIME_PATHS"
else
  echo "FAIL coverage: shipped scripts/ files != brief_doctor RUNTIME_PATHS scripts"
  echo "--- shipped ---"; echo "$shipped_scripts"
  echo "--- doctor ---";  echo "$doc_scripts"
  fail=1
fi

# --- 1d. parity: doctor REQUIRED_CHAPTERS == managed-chapters.md headings ---
# The managed-chapter set is the `## ` headings of harness/claude-md/managed-chapters.md
# (fence-aware: a heading quoted in a code fence is not a chapter); the doctor's
# required-chapter check lists the same headings. They must match exactly, or
# refresh-chapters.sh and the doctor disagree on what is managed.
src_chapters="$(awk '/^[ \t]*```/{f=!f; next} !f && /^## /{print}' "$here/claude-md/managed-chapters.md" | sort -u)"
doc_chapters="$(python3 - "$doctor" <<'PY'
import re, sys
src = open(sys.argv[1]).read()
block = re.search(r'REQUIRED_CHAPTERS\s*=\s*\[(.*?)\]', src, re.S).group(1)
print('\n'.join(sorted(set(re.findall(r'"([^"]+)"', block)))))
PY
)"
if [ "$src_chapters" = "$doc_chapters" ]; then
  echo "ok   parity: REQUIRED_CHAPTERS matches managed-chapters.md headings"
else
  echo "FAIL parity: doctor REQUIRED_CHAPTERS != managed-chapters.md headings"
  echo "--- managed-chapters.md ---"; echo "$src_chapters"
  echo "--- doctor ---";          echo "$doc_chapters"
  fail=1
fi

# --- 1e. refresh-chapters.sh safety: never half-write or silently no-op ---
# Two invariants the writer must hold against malformed input: a duplicate
# heading in the source must fail BEFORE any write (no partial in-place edit),
# and a CRLF target must be refused loudly (exact-match would silently refresh
# nothing, and the marketplace setup.sh runs no doctor to catch it). Both must
# leave the target byte-for-byte untouched.
rc_tmp="$(mktemp -d)"
tmp='' mkt='' gi='' co='' st=''
cleanup() { rm -rf ${rc_tmp:+"$rc_tmp"} ${tmp:+"$tmp"} ${mkt:+"$mkt"} ${gi:+"$gi"} ${co:+"$co"} ${st:+"$st"}; }
trap cleanup EXIT
mkdir -p "$rc_tmp/dup/claude-md"
printf '## Memory\n\nfirst\n\n## Memory\n\ndup\n' > "$rc_tmp/dup/claude-md/managed-chapters.md"
printf '# P\n## Memory\nKEEP_ME\n' > "$rc_tmp/dup_target.md"
cp "$rc_tmp/dup_target.md" "$rc_tmp/dup_target.orig"
set +e; bash "$here/claude-md/refresh-chapters.sh" "$rc_tmp/dup_target.md" "$rc_tmp/dup" >/dev/null 2>&1; dup_rc=$?; set -e
if [ "$dup_rc" -ne 0 ] && diff -q "$rc_tmp/dup_target.orig" "$rc_tmp/dup_target.md" >/dev/null; then
  echo "ok   refresh: duplicate source heading fails before any write (target untouched)"
else
  echo "FAIL refresh: duplicate source heading rc=$dup_rc or target was mutated"; fail=1
fi
printf '# P\r\n## Memory\r\nold\r\n' > "$rc_tmp/crlf_target.md"
cp "$rc_tmp/crlf_target.md" "$rc_tmp/crlf_target.orig"
set +e; crlf_out="$(bash "$here/claude-md/refresh-chapters.sh" "$rc_tmp/crlf_target.md" "$here" 2>/dev/null)"; crlf_rc=$?; set -e
if [ "$crlf_rc" -eq 0 ] && printf '%s' "$crlf_out" | grep -qi CRLF \
   && diff -q "$rc_tmp/crlf_target.orig" "$rc_tmp/crlf_target.md" >/dev/null; then
  echo "ok   refresh: CRLF target refused loudly, left untouched"
else
  echo "FAIL refresh: CRLF target not handled (rc=$crlf_rc, out=$crlf_out)"; fail=1
fi
rm -rf "$rc_tmp"; rc_tmp=''

# --- 2. extras detection ---
stack=go
tmp="$(mktemp -d)"
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

# --- 4. deterministic gitignore refresh: ensure-present, additive, idempotent ---
gi="$(mktemp -d)"
printf '.scratch/\n.claude/skills/*\nmy-own/\n' > "$gi/.gitignore"   # one path present + a project ignore
bash "$here/refresh-gitignore.sh" "$gi/.gitignore" "$here/init/core/gitignore-runtime.txt" manifest >/dev/null
if grep -qxF 'scripts/brief_doctor.py' "$gi/.gitignore"; then
  echo "ok   gitignore: a missing runtime path is ensured present"
else
  echo "FAIL gitignore: missing runtime path not ensured"; fail=1
fi
if [ "$(grep -cxF 'my-own/' "$gi/.gitignore" || true)" = 1 ] \
   && [ "$(grep -cxF '.claude/skills/*' "$gi/.gitignore" || true)" = 1 ]; then
  echo "ok   gitignore: project ignore preserved, harness line not duplicated"
else
  echo "FAIL gitignore: project line lost or harness line duplicated"; fail=1
fi
out="$(bash "$here/refresh-gitignore.sh" "$gi/.gitignore" "$here/init/core/gitignore-runtime.txt" manifest)"
if [ "$out" = "gitignore: 0 path(s) added" ]; then
  echo "ok   gitignore: idempotent (second run adds nothing)"
else
  echo "FAIL gitignore: not idempotent ($out)"; fail=1
fi
printf 'build/\n' > "$gi/copy.gitignore"
bash "$here/refresh-gitignore.sh" "$gi/copy.gitignore" "$here/init/core/gitignore-runtime.txt" copy >/dev/null
if grep -qxF '.scratch/' "$gi/copy.gitignore" && ! grep -q '.claude/skills' "$gi/copy.gitignore"; then
  echo "ok   gitignore: copy channel ensures only the .scratch/ ledger"
else
  echo "FAIL gitignore: copy channel added runtime paths"; fail=1
fi
# no-trailing-newline target that already contains "harness runtime" must not
# merge an appended path onto the project's last line
printf '# my harness runtime notes\nmy-own/' > "$gi/nonl.gitignore"   # no final newline
bash "$here/refresh-gitignore.sh" "$gi/nonl.gitignore" "$here/init/core/gitignore-runtime.txt" manifest >/dev/null
if grep -qxF 'my-own/' "$gi/nonl.gitignore" && grep -qxF '.scratch/' "$gi/nonl.gitignore"; then
  echo "ok   gitignore: newline-less target — project line intact, path on its own line"
else
  echo "FAIL gitignore: appended path merged onto the project's final line"; fail=1
fi
# setup/init coordination: the refresh writes its terse "harness runtime" header,
# then init.sh (run second, the setup-first-then-init order) must RECOGNIZE that
# block and not re-append the whole thing. init and refresh must share one
# detection token; a mismatch double-appends every runtime path.
co="$(mktemp -d)"; git -C "$co" init -q >/dev/null 2>&1 || true
bash "$here/refresh-gitignore.sh" "$co/.gitignore" "$here/init/core/gitignore-runtime.txt" manifest >/dev/null
if bash "$here/init.sh" go "$co" coord-test "coordination" "" claude manifest >/dev/null 2>&1; then
  if [ "$(grep -cxF '.scratch/' "$co/.gitignore" || true)" = 1 ] \
     && [ "$(grep -cxF 'scripts/brief_doctor.py' "$co/.gitignore" || true)" = 1 ]; then
    echo "ok   gitignore: refresh-then-init shares one sentinel — no double block"
  else
    echo "FAIL gitignore: init re-appended the block after refresh (sentinel mismatch)"; fail=1
  fi
else
  echo "FAIL gitignore: init.sh failed in the coordination test"; fail=1
fi
rm -rf "$co" "$gi"

# --- 5. deterministic settings refresh: harness keys ensured, project keys kept ---
st="$(mktemp -d)"; mkdir -p "$st/.claude/hooks"
touch "$st/.claude/hooks/sendmessage-continue-only.sh" "$st/.claude/hooks/handoff-allow.sh"
printf '{\n  "env": { "MY_VAR": "keep" }\n}\n' > "$st/.claude/settings.json"
python3 "$here/refresh-settings.py" "$st/.claude/settings.json" "$here/init/core/.claude/settings.json" "$st" >/dev/null
if python3 - "$st/.claude/settings.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
ok = (d["env"].get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1"
      and d["env"].get("MY_VAR") == "keep"
      and {e["matcher"] for e in d["hooks"]["PreToolUse"]} == {"SendMessage", "Bash"})
sys.exit(0 if ok else 1)
PY
then
  echo "ok   settings: env flag + delivered-hook matchers ensured, project key kept"
else
  echo "FAIL settings: harness keys not ensured or project key lost"; fail=1
fi
out="$(python3 "$here/refresh-settings.py" "$st/.claude/settings.json" "$here/init/core/.claude/settings.json" "$st")"
if [ "$out" = "settings: no change" ]; then
  echo "ok   settings: idempotent (second run reports no change)"
else
  echo "FAIL settings: not idempotent ($out)"; fail=1
fi
rm -rf "$st/.claude/hooks"; printf '{}\n' > "$st/.claude/settings.json"   # marketplace-like: no local hooks
python3 "$here/refresh-settings.py" "$st/.claude/settings.json" "$here/init/core/.claude/settings.json" "$st" >/dev/null
if python3 - "$st/.claude/settings.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
sys.exit(0 if (d.get("env", {}).get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") == "1"
               and "hooks" not in d) else 1)
PY
then
  echo "ok   settings: no local hooks -> env flag only, no spurious matcher"
else
  echo "FAIL settings: registered a matcher without a delivered hook"; fail=1
fi
# a project that overrode the harness flag keeps its value (ensure-present-if-absent)
printf '{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "0" } }\n' > "$st/.claude/settings.json"
python3 "$here/refresh-settings.py" "$st/.claude/settings.json" "$here/init/core/.claude/settings.json" "$st" >/dev/null
if [ "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["env"]["CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS"])' "$st/.claude/settings.json")" = "0" ]; then
  echo "ok   settings: a project-overridden flag value is not clobbered"
else
  echo "FAIL settings: overwrote a project's env value"; fail=1
fi
# an unparseable settings.json is skipped gracefully, never a traceback / abort
printf '{ not json' > "$st/.claude/settings.json"
out="$(python3 "$here/refresh-settings.py" "$st/.claude/settings.json" "$here/init/core/.claude/settings.json" "$st" 2>&1)" && rc=0 || rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -qi 'skipped'; then
  echo "ok   settings: unparseable target is skipped gracefully (exit 0)"
else
  echo "FAIL settings: unparseable target did not skip cleanly (rc=$rc, out=$out)"; fail=1
fi
rm -rf "$st"

if [ "$fail" -eq 0 ]; then
  echo "PASS test-materialize"
else
  echo "FAIL test-materialize"; exit 1
fi
