#!/usr/bin/env bash
# Guards for the generic (technology-free) fallback stack:
#   1. init + materialize produce a complete, doctor-passing project.
#   2. The quality gate fails honestly before the verbs are bound (an
#      unimplemented verb fails; a missing stack.sh fails).
#   3. Once every verb is bound, the gate passes — it fails for the right
#      reason, not because the dispatcher is broken.
#   4. The materialized generic runtime carries NO language-specific token:
#      the stack must not depend on Go, Java, or any other technology.
#
#   harness/test-generic-stack.sh      # exits non-zero on any failure
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
fail=0

T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT

# --- 1. init + materialize ---
python3 "$here/init.py" generic "$T" "Widget" "A service on an unsupported stack" >/dev/null
python3 "$here/materialize.py" generic "$T" >/dev/null

for f in scripts/gate.sh scripts/stack.sh scripts/layout.toml CLAUDE.md \
         .claude/skills/code-quality-gate/SKILL.md docs/testing-principles.md; do
  if [ -f "$T/$f" ]; then echo "ok   present: $f"; else echo "FAIL missing: $f"; fail=1; fi
done

# --- 2. fail-honest before binding ---
if ( cd "$T" && ./scripts/gate.sh verify >/dev/null 2>&1 ); then
  echo "FAIL stub gate passed — it must fail before the verbs are bound"; fail=1
else
  echo "ok   stub gate fails honestly (unbound verbs)"
fi
if ( cd "$T" && ./scripts/gate.sh test >/dev/null 2>&1 ); then
  echo "FAIL stub verb 'test' passed — it must fail before binding"; fail=1
else
  echo "ok   stub verb fails honestly"
fi
# a missing stack.sh must also fail, never pass
mv "$T/scripts/stack.sh" "$T/scripts/stack.sh.bak"
if ( cd "$T" && ./scripts/gate.sh verify >/dev/null 2>&1 ); then
  echo "FAIL gate passed with no stack.sh — an unbound stack must fail"; fail=1
else
  echo "ok   gate fails when stack.sh is absent"
fi
mv "$T/scripts/stack.sh.bak" "$T/scripts/stack.sh"

# --- 3. passes once every verb is bound ---
cat > "$T/scripts/stack.sh" <<'EOF'
#!/usr/bin/env bash
verb_deps()   { return 0; }
verb_format() { return 0; }
verb_lint()   { return 0; }
verb_test()   { return 0; }
verb_build()  { return 0; }
EOF
if ( cd "$T" && ./scripts/gate.sh verify >/dev/null 2>&1 ); then
  echo "ok   gate passes once every verb is bound"
else
  echo "FAIL gate failed with all verbs bound green — dispatcher is broken"; fail=1
fi

# --- 3b. a verb that calls `exit` (not `return`) cannot short-circuit verify ---
cat > "$T/scripts/stack.sh" <<'EOF'
#!/usr/bin/env bash
verb_deps()   { return 0; }
verb_format() { return 0; }
verb_lint()   { exit 0; }   # bad author: exit instead of return
verb_test()   { false; }    # a real failure AFTER the exit-verb
verb_build()  { return 0; }
EOF
if out="$( cd "$T" && ./scripts/gate.sh verify 2>&1 )"; then rc=0; else rc=$?; fi
if [ "$rc" -ne 0 ] && printf '%s\n' "$out" | grep -q '== test ==' && printf '%s\n' "$out" | grep -q '== build =='; then
  echo "ok   a verb's stray exit is contained; verify runs every verb"
else
  echo "FAIL a verb's exit short-circuited verify (later verbs skipped or gate passed)"; printf '%s\n' "$out"; fail=1
fi

# --- 4. doctor passes on the materialized briefs ---
if ( cd "$T" && python3 scripts/brief_doctor.py check >/dev/null 2>&1 ); then
  echo "ok   doctor passes on the generic project"
else
  echo "FAIL doctor failed on the generic project"; fail=1
fi

# --- 5. no language-specific tokens in the generic stack's own files ---
# The generic stack must bind to no language. Scan the stack layer's own files
# (the skills, agents, schemas, and gate.sh it contributes). Core is the shared
# runtime — it serves every stack and may cite Go/Java as illustrative examples;
# that is not a generic-stack dependency, so core is out of scope here. English
# words like "go" in prose are excluded; build-tool and language identifiers are not.
gen_leak=0
while IFS= read -r rel; do
  hit="$(grep -inE '\bgolang\b|gofmt|golangci|goroutine|\bgo (test|build|mod|vet|fmt)\b|google go|\bjava\b|\bgradle\b|\bspring\b|\bmaven\b|\bkotlin\b|\.go\b|\.java\b|govulncheck|make ci|make lint' \
    "$here/stacks/generic/$rel" 2>/dev/null || true)"
  if [ -n "$hit" ]; then
    echo "FAIL generic file leaks language token: $rel"; printf '%s\n' "$hit"; gen_leak=1; fail=1
  fi
done < <(cd "$here/stacks/generic" && find . -type f | sed 's#^\./##')
[ "$gen_leak" -eq 0 ] && echo "ok   generic stack files carry no language-specific token"

# --- 6. tool-surface filtering works for generic (claude-only) ---
# init args: <stack> <target> <name> <desc> [version] [tools-csv] [channel].
T2="$(mktemp -d)"
python3 "$here/init.py" generic "$T2" "Widget2" "claude-only generic" "" "claude" "copy" >/dev/null
python3 "$here/materialize.py" generic "$T2" >/dev/null
if [ -n "$(find "$T2/.claude/skills" -type f 2>/dev/null)" ] \
   && [ -z "$(find "$T2/.github/agents" "$T2/.opencode/agents" "$T2/.junie/agents" -type f 2>/dev/null)" ]; then
  echo "ok   tool filtering: claude-only installs .claude, omits the other tools"
else
  echo "FAIL tool filtering wrong for generic (claude-only): unexpected surface set"; fail=1
fi
rm -rf "$T2"

# --- 7. manifest channel: gate.sh is treated as runtime (ignored + untracked) ---
# gate.sh is the one individual runtime script that lives in the stack layer, not
# core. The core runtime lists (gitignore-runtime.txt and the doctor's
# RUNTIME_PATHS) must still cover it, or a manifest/marketplace generic consumer
# commits harness runtime while the doctor's channel invariant reports it clean.
if command -v git >/dev/null 2>&1; then
  T3="$(mktemp -d)"
  git -C "$T3" init -q
  python3 "$here/init.py" generic "$T3" "Widget3" "manifest generic" "" "claude" "manifest" >/dev/null
  python3 "$here/materialize.py" generic "$T3" >/dev/null
  git -C "$T3" add -A 2>/dev/null || true
  if git -C "$T3" check-ignore scripts/gate.sh >/dev/null 2>&1 \
     && [ -z "$(git -C "$T3" ls-files -- scripts/gate.sh)" ]; then
    echo "ok   manifest: gate.sh is gitignored and stays untracked"
  else
    echo "FAIL manifest: gate.sh is not gitignored — runtime leaks into git"; fail=1
  fi
  if ( cd "$T3" && python3 scripts/brief_doctor.py check >/dev/null 2>&1 ); then
    echo "ok   manifest: doctor channel invariant passes with no runtime tracked"
  else
    echo "FAIL manifest: doctor failed on the manifest generic project"; fail=1
  fi
  # Negative half: force-track gate.sh (as a pre-fix repo or a careless `git add
  # -f` would) and assert the doctor's channel check CATCHES it. This guards the
  # RUNTIME_PATHS entry directly — the passing case above holds with or without
  # it, because the original bug was a silent false PASS.
  git -C "$T3" add -f scripts/gate.sh 2>/dev/null || true
  # The doctor exits non-zero here by design, so capture then grep — piping into
  # grep under `set -o pipefail` would report the doctor's failure, not the match.
  dout="$( cd "$T3" && python3 scripts/brief_doctor.py check 2>&1 || true )"
  if printf '%s\n' "$dout" | grep -qi 'FAIL channel.*gate\.sh'; then
    echo "ok   manifest: doctor flags gate.sh when it is tracked (RUNTIME_PATHS covers it)"
  else
    echo "FAIL manifest: doctor did not flag a tracked gate.sh — RUNTIME_PATHS gap"; fail=1
  fi
  rm -rf "$T3"
else
  echo "ok   manifest gate.sh guard skipped (git unavailable)"
fi

if [ "$fail" -eq 0 ]; then
  echo "PASS test-generic-stack"
else
  echo "FAIL test-generic-stack"; exit 1
fi
