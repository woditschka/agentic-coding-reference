#!/usr/bin/env bash
# Guards for refresh-agent-bodies.sh, on a throwaway fixture layer:
#   1. A drifted mirror body is rewritten to the base body, with skill links
#      rewritten to the mirror form; the mirror's frontmatter stays byte-exact.
#   2. A "---" rule inside the body is content, not a fence — it survives.
#   3. The render is idempotent: a second run reports 0 rendered, no byte change.
#   4. A missing mirror fails; frontmatter is authored, never generated.
#   5. A base carrying the mirror link form fails (it would double-rewrite).
#   6. README.md is exempt: never treated as an agent base.
#   7. A mirror whose base is gone is pruned; READMEs and strays survive.
#   7b. Prune never fires on a layer with failures: a renamed base must not
#       cost its mirrors' authored frontmatter in the same failing run.
#   8. A layer with an empty agent roster fails AND its mirrors survive —
#      the mass-deletion path (renamed .claude/agents) stays pinned.
#   9. A base linking ../../skills/ fails (the render would over-rewrite it).
#
#   harness/test-refresh-agent-bodies.sh   # exits non-zero on any failure
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
fail=0

T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT

L="$T/layer"
mkdir -p "$L/.claude/agents" "$L/.junie/agents" "$L/.opencode/agents" "$L/.github/agents"

cat > "$L/.claude/agents/sample.md" <<'EOF'
---
name: sample
tools:
  - Read
---
# Sample Agent

Read [the handoff rules](../skills/handoff-routing/SKILL.md) first.

---

A rule above this line is body content, not a fence.
EOF

# Mirrors: distinct frontmatter each, drifted or stale bodies.
cat > "$L/.junie/agents/sample.md" <<'EOF'
---
name: sample
model: opus
---
Stale junie body.
EOF
cat > "$L/.opencode/agents/sample.md" <<'EOF'
---
mode: subagent
permissions:
  mcp: deny
---
Stale opencode body.
EOF
cat > "$L/.github/agents/sample.agent.md" <<'EOF'
---
name: Sample
model: Claude Opus 4.7 (copilot)
---
Stale copilot body.
EOF

cat > "$L/.claude/agents/README.md" <<'EOF'
Roster notes — not an agent.
EOF

# --- 1 + 2: render fixes drift, keeps frontmatter, rewrites links ---
out="$("$here/refresh-agent-bodies.sh" "$L")"
case "$out" in
  *"3 rendered, 0 already current, 0 pruned"*) echo "ok   first render reports 3 rendered" ;;
  *) echo "FAIL unexpected first-render report: $out"; fail=1 ;;
esac

base_body="$(awk '/^---[ \t]*$/ && n<2 {n++; next} n>=2 {print}' "$L/.claude/agents/sample.md")"
for m in "$L/.junie/agents/sample.md" "$L/.opencode/agents/sample.md" "$L/.github/agents/sample.agent.md"; do
  got="$(awk '/^---[ \t]*$/ && n<2 {n++; next} n>=2 {print}' "$m")"
  want="$(printf '%s\n' "$base_body" | sed 's:\.\./skills/:../../.claude/skills/:g')"
  if [ "$got" = "$want" ]; then echo "ok   body rendered: $m"; else echo "FAIL body mismatch: $m"; fail=1; fi
  if grep '\.\./\.\./\.claude/skills/handoff-routing' "$m" >/dev/null; then
    echo "ok   link rewritten: $m"
  else
    echo "FAIL link not rewritten to mirror form: $m"; fail=1
  fi
  if grep 'body content, not a fence' "$m" >/dev/null; then
    echo "ok   in-body --- rule survived: $m"
  else
    echo "FAIL body truncated at its own --- rule: $m"; fail=1
  fi
done
if head -4 "$L/.opencode/agents/sample.md" | grep 'mcp: deny' >/dev/null; then
  echo "ok   mirror frontmatter untouched"
else
  echo "FAIL mirror frontmatter was rewritten"; fail=1
fi

# --- 3: idempotent ---
snap="$(cat "$L/.junie/agents/sample.md" "$L/.opencode/agents/sample.md" "$L/.github/agents/sample.agent.md")"
out="$("$here/refresh-agent-bodies.sh" "$L")"
case "$out" in
  *"0 rendered, 3 already current, 0 pruned"*) echo "ok   second render is a no-op" ;;
  *) echo "FAIL second render not idempotent: $out"; fail=1 ;;
esac
snap2="$(cat "$L/.junie/agents/sample.md" "$L/.opencode/agents/sample.md" "$L/.github/agents/sample.agent.md")"
if [ "$snap" = "$snap2" ]; then echo "ok   no byte change on re-run"; else echo "FAIL bytes changed on re-run"; fail=1; fi

# --- 6: README skipped (would have failed: it has no mirrors) ---
echo "ok   README.md skipped as a base"

# --- 4: missing mirror fails ---
rm "$L/.junie/agents/sample.md"
if "$here/refresh-agent-bodies.sh" "$L" >/dev/null 2>&1; then
  echo "FAIL missing mirror passed — frontmatter must be authored, never generated"; fail=1
else
  echo "ok   missing mirror fails loud"
fi
cat > "$L/.junie/agents/sample.md" <<'EOF'
---
name: sample
---
x
EOF

# --- 5: base carrying the mirror link form fails ---
cat > "$L/.claude/agents/sample.md" <<'EOF'
---
name: sample
---
Bad [link](../../.claude/skills/handoff-routing/SKILL.md).
EOF
if "$here/refresh-agent-bodies.sh" "$L" >/dev/null 2>&1; then
  echo "FAIL base with mirror link form passed"; fail=1
else
  echo "ok   base with mirror link form fails"
fi
cat > "$L/.claude/agents/sample.md" <<'EOF'
---
name: sample
---
Good [link](../skills/handoff-routing/SKILL.md).
EOF

# --- 7: mirrors whose base is gone are pruned; READMEs and strays survive ---
rm "$L/.claude/agents/README.md"   # the junie README below survives only via the prune guard
for d in .junie/agents .opencode/agents; do
  printf -- '---\nname: retired\n---\nold\n' > "$L/$d/retired.md"
done
printf -- '---\nname: Retired\n---\nold\n' > "$L/.github/agents/retired.agent.md"
printf 'roster notes\n' > "$L/.github/agents/README.md"
printf 'roster notes\n' > "$L/.junie/agents/README.md"
printf 'stray\n' > "$L/.junie/agents/notes.txt"
out="$("$here/refresh-agent-bodies.sh" "$L")"
case "$out" in
  *"3 rendered, 0 already current, 3 pruned"*) echo "ok   orphaned mirrors pruned" ;;
  *) echo "FAIL prune report unexpected: $out"; fail=1 ;;
esac
for f in .junie/agents/retired.md .opencode/agents/retired.md .github/agents/retired.agent.md; do
  if [ -e "$L/$f" ]; then echo "FAIL orphan not pruned: $f"; fail=1; fi
done
if [ -f "$L/.github/agents/README.md" ] && [ -f "$L/.junie/agents/README.md" ] \
   && [ -f "$L/.junie/agents/notes.txt" ]; then
  echo "ok   READMEs and stray files survive the prune"
else
  echo "FAIL prune deleted a README or a stray file"; fail=1
fi
rm "$L/.github/agents/README.md" "$L/.junie/agents/README.md" "$L/.junie/agents/notes.txt"

# --- 7b: prune is skipped while the layer has failures ---
printf -- '---\nname: orphan\n---\nold\n' > "$L/.junie/agents/orphan.md"
rm "$L/.junie/agents/sample.md"    # failure: missing mirror
if "$here/refresh-agent-bodies.sh" "$L" >/dev/null 2>&1; then
  echo "FAIL failing run exited 0"; fail=1
fi
if [ -f "$L/.junie/agents/orphan.md" ]; then
  echo "ok   prune skipped while the run is failing"
else
  echo "FAIL prune fired on a failing layer — authored frontmatter at risk"; fail=1
fi
cat > "$L/.junie/agents/sample.md" <<'EOF'
---
name: sample
---
x
EOF
out="$("$here/refresh-agent-bodies.sh" "$L")"
if [ ! -e "$L/.junie/agents/orphan.md" ]; then
  echo "ok   prune fires once the layer is clean again"
else
  echo "FAIL orphan survived a clean run: $out"; fail=1
fi

# --- 8: an empty agent roster fails and never reaches prune ---
E="$T/empty-layer"
mkdir -p "$E/.claude/agents" "$E/.junie/agents" "$E/.opencode/agents" "$E/.github/agents"
printf 'roster notes\n' > "$E/.claude/agents/README.md"
printf -- '---\nname: keeper\n---\nk\n' > "$E/.junie/agents/keeper.md"
if "$here/refresh-agent-bodies.sh" "$E" >/dev/null 2>&1; then
  echo "FAIL empty roster passed — a renamed path must not report success"; fail=1
else
  echo "ok   empty roster fails loud"
fi
if [ -f "$E/.junie/agents/keeper.md" ]; then
  echo "ok   empty roster prunes nothing — mirrors survive"
else
  echo "FAIL empty roster mass-deleted mirrors"; fail=1
fi

# --- 9: base linking ../../skills/ fails (would over-rewrite in mirrors) ---
cat > "$L/.claude/agents/sample.md" <<'EOF'
---
name: sample
---
Bad [link](../../skills/handoff-routing/SKILL.md).
EOF
if "$here/refresh-agent-bodies.sh" "$L" >/dev/null 2>&1; then
  echo "FAIL base with ../../skills/ link passed"; fail=1
else
  echo "ok   base with ../../skills/ link fails"
fi

exit "$fail"
