#!/usr/bin/env bash
# Local deterministic gate for the harness + samples: the mechanical,
# no-judgment half of an audit-harness review. This header is the authoritative
# step list — docs reference it rather than re-enumerating:
#   1  shellcheck (harness/ + tools/)      5   sample doctors
#   2  python syntax                       6   materialize self-test
#   2b agent body parity (per-tool copies) 6b  generic-stack self-test
#   3  materialization faithfulness        7   marketplace faithfulness
#   4  sample test suites                  8   marketplace acceptance
#   4b sample build-file script refs       9   real plugin install (claude CLI)
# Aggregates failures (does not stop at the first) and exits non-zero if any
# check fails. Run it before committing a /harness edit, or as a git pre-push
# hook. This project is local-only — there is no server-side CI.
#
#   harness/check-sync.sh
#
# Needs bash, git, python3; shellcheck if present (skipped with a note if not).
# No Go/Java toolchain required. The faithfulness step re-materializes the
# samples in place: it is dirty-tree-safe — it flags only changes the
# re-materialize *introduces* (a /harness edit you forgot to materialize, or a
# hand-edited sample), never your already-pending work.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/.." && pwd)"
cd "$root"

# shellcheck source=harness/helpers.sh
. "$here/helpers.sh"

fail=0

# 1. Shell lint (harness source scripts + the shipped user-level tooling).
note "shellcheck (bash)"
if command -v shellcheck >/dev/null 2>&1; then
  while IFS= read -r f; do
    if ! shellcheck -S warning "$f"; then
      echo "FAIL: shellcheck flagged $f" >&2; fail=1
    fi
  done < <(find harness tools -name '*.sh')
  [ "$fail" -eq 0 ] && echo "  clean"
else
  echo "  SKIP: shellcheck not installed (brew install shellcheck)"
fi

# 2. Python syntax (compile in memory — no __pycache__ left behind).
note "python syntax"
while IFS= read -r f; do
  if ! python3 -c "import sys; compile(open(sys.argv[1]).read(), sys.argv[1], 'exec')" "$f" 2>&1; then
    echo "FAIL: python syntax error in $f" >&2; fail=1
  fi
done < <(find harness -name '*.py')
echo "  ok"

# 2b. Agent body parity — every agent's four per-tool source copies (.claude/,
#     .junie/, .opencode/, .github/) must carry byte-identical bodies; only the
#     frontmatter differs. One documented exception is normalized away: skill
#     links are location-correct per directory (../skills/ from .claude/agents/,
#     ../../.claude/skills/ from the other three). Faithfulness (step 3) cannot
#     see this — an edit that misses a sibling copy sits identically in source
#     and sample — so a drifted copy ships a weaker agent to that tool's users.
note "agent body parity (per-tool copies)"
# Strip only the frontmatter fence — a body's own "---" rules stay compared.
# A file with no fence yields an empty body; the empty-base guard below fails it.
strip_fm() { awk '/^---[ \t]*$/ && n<2 {n++; next} n>=2 {print}' "$1"; }
norm_links() { sed 's:\.\./\.\./\.claude/skills/:../skills/:g'; }
layers=("$here/core")
for s in "${STACKS[@]}"; do layers+=("$here/stacks/$s"); done
parity_bad=0
for layer in "${layers[@]}"; do
  bases=0
  for base in "$layer/.claude/agents/"*.md; do
    [ -f "$base" ] || continue
    a="$(basename "$base" .md)"; [ "$a" = "README" ] && continue
    bases=$((bases + 1))
    if ! strip_fm "$base" | grep -q .; then
      echo "FAIL: empty body (or missing frontmatter fence) in ${base#"$root"/}" >&2
      fail=1; parity_bad=1
    fi
    # Each link form is asserted, not just normalized: the claude copy uses the
    # local form (../skills/), siblings the rewritten one (../../.claude/skills/).
    # Without this, a sibling whose link was never rewritten is byte-equal to the
    # base and would pass while shipping a link broken from its directory. The
    # assertion scans the whole body, code fences included — a body that ever
    # needs to *document* the other form must move that example into a skill.
    if strip_fm "$base" | grep -q '\.\./\.\./\.claude/skills/'; then
      echo "FAIL: sibling link form (../../.claude/skills/) in ${base#"$root"/} — the claude copy uses ../skills/" >&2
      fail=1; parity_bad=1
    fi
    for f in "$layer/.junie/agents/$a.md" \
             "$layer/.opencode/agents/$a.md" \
             "$layer/.github/agents/$a.agent.md"; do
      if [ ! -f "$f" ]; then
        echo "FAIL: missing per-tool agent copy ${f#"$root"/}" >&2; fail=1; parity_bad=1
        continue
      fi
      if strip_fm "$f" | sed 's:\.\./\.\./\.claude/skills/::g' | grep -q '\.\./skills/'; then
        echo "FAIL: un-rewritten skill link (../skills/) in ${f#"$root"/} — broken from this directory" >&2
        fail=1; parity_bad=1
      fi
      if ! diff -q <(strip_fm "$base") <(strip_fm "$f" | norm_links) >/dev/null; then
        echo "FAIL: agent body drift (frontmatter aside): ${f#"$root"/} != ${base#"$root"/}" >&2
        fail=1; parity_bad=1
      fi
    done
  done
  if [ "$bases" -eq 0 ]; then
    echo "FAIL: no agent bases under ${layer#"$root"/}/.claude/agents/ — roster empty or path renamed" >&2
    fail=1; parity_bad=1
  fi
  # Reverse sweep: an agent file present only in a sibling dir has no base above
  # and would otherwise never be compared — it would ship to that tool unchecked.
  # It also enforces each tool's file suffix: a wrong-suffix stray (foo.md in
  # .github, or any non-.md file) would dodge the forward pass the same way.
  for d in .junie/agents .opencode/agents .github/agents; do
    for f in "$layer/$d/"*; do
      [ -f "$f" ] || continue
      n="$(basename "$f")"
      case "$d" in
        .github/agents)
          case "$n" in
            *.agent.md) a="${n%.agent.md}" ;;
            README.md)  continue ;;
            *) echo "FAIL: ${f#"$root"/} — copilot agents must be <name>.agent.md" >&2
               fail=1; parity_bad=1; continue ;;
          esac ;;
        *)
          case "$n" in
            *.md) a="${n%.md}" ;;
            *) echo "FAIL: ${f#"$root"/} — unexpected non-.md file in a tool agents dir" >&2
               fail=1; parity_bad=1; continue ;;
          esac ;;
      esac
      [ "$a" = "README" ] && continue
      if [ ! -f "$layer/.claude/agents/$a.md" ]; then
        echo "FAIL: ${f#"$root"/} has no .claude/agents/$a.md base — sibling-only agent, never parity-checked" >&2
        fail=1; parity_bad=1
      fi
    done
  done
done
[ "$parity_bad" -eq 0 ] && echo "  all per-tool bodies identical"

# 3. Materialization faithfulness — dirty-tree-safe. Snapshot the working tree,
#    re-materialize, and flag only what the re-materialize *changes* (forgotten
#    materialize or a drifted hand-edit), plus any orphan extra.
note "materialization faithfulness"
before="$(git status --porcelain -- samples/)"
if ! out="$(bash harness/bootstrap.sh 2>&1)"; then
  echo "FAIL: harness/bootstrap.sh failed:" >&2; printf '%s\n' "$out" >&2; exit 1
fi
extras_seen=0
while IFS= read -r n; do
  extras_seen=$((extras_seen + 1))
  if [ "$n" != "0" ]; then
    echo "FAIL: materialize reported $n orphan extra(s) — a committed file /harness no longer produces. git rm it." >&2
    fail=1
  fi
done < <(printf '%s\n' "$out" | sed -n 's/.*extras: \([0-9][0-9]*\) file.*/\1/p')
# Committed orphans are invisible to the porcelain diff (bootstrap never deletes
# them) — the extras count is their only guard. If the parse found no extras line,
# the bootstrap output format changed; fail loud rather than pass an unchecked tree.
if [ "$extras_seen" -eq 0 ]; then
  echo "FAIL: no 'extras:' line parsed from bootstrap output — output format changed; orphan detection is not running." >&2
  printf '%s\n' "$out" >&2
  fail=1
fi
after="$(git status --porcelain -- samples/)"
if [ "$before" != "$after" ]; then
  echo "FAIL: re-materialize changed the samples — a /harness edit was not materialized, or a sample was hand-edited:" >&2
  diff <(printf '%s\n' "$before") <(printf '%s\n' "$after") | grep '^>' | sed 's/^> /  /' >&2
  echo "Fix: review the change, then commit the re-materialized samples with the /harness edit." >&2
  fail=1
else
  echo "  samples == materialize(/harness)"
fi

# 4. Sample test suites (run from each sample, where layout.toml + schemas colocate).
#    Every sample ships every suite — a missing file is a FAIL, not a skip. The
#    old [ -f ]-guard silently skipped a suite a stack never shipped; that is how
#    the generic stack ran without test_score_change.py while this stayed green.
note "sample test suites"
suites_bad=0
for s in "${STACKS[@]}"; do
  for t in \
    "scripts/test_brief_doctor.py" \
    "scripts/test_handoff.py" \
    "scripts/test_score_change.py"; do
    if [ ! -f "samples/$s/$t" ]; then
      echo "FAIL: samples/$s/$t missing — every sample ships all three suites" >&2
      fail=1; suites_bad=1
    elif ! out="$(cd "samples/$s" && python3 "$t" 2>&1)"; then
      echo "FAIL: samples/$s/$t" >&2
      printf '%s\n' "$out" | tail -20 | sed 's/^/    /' >&2
      fail=1; suites_bad=1
    fi
  done
done
[ "$suites_bad" -eq 0 ] && echo "  all suites pass"

# 4b. Sample build files reference live scripts. The battery runs the script
#     tests directly (step 4), not through each sample's own make/gradle gate, so
#     a script that moves can leave a sample's build target dangling while this
#     stays green. Each stack declares its build-binding file — a missing one is
#     a FAIL, not a skip (step 4's philosophy). Grep it for *.py references and
#     confirm each resolves — toolchain-free, no Go/Java needed.
note "sample build-file script refs"
refs_bad=0
for s in "${STACKS[@]}"; do
  case "$s" in
    go)               bf="samples/$s/Makefile" ;;
    java-spring-boot) bf="samples/$s/build.gradle" ;;
    generic)          bf="samples/$s/scripts/stack.sh" ;;
    *) echo "FAIL: stack '$s' has no build-binding file declared — extend the case in step 4b" >&2
       fail=1; refs_bad=1; continue ;;
  esac
  if [ ! -f "$bf" ]; then
    echo "FAIL: $bf missing — the stack's declared build-binding file" >&2
    fail=1; refs_bad=1; continue
  fi
  while IFS= read -r p; do
    [ -f "samples/$s/$p" ] || { echo "FAIL: $bf references missing script '$p'" >&2; fail=1; refs_bad=1; }
  done < <(grep -oE '[A-Za-z0-9_./-]+\.py' "$bf" | sort -u)
done
[ "$refs_bad" -eq 0 ] && echo "  build-file script paths resolve"

# 5. Sample doctors (the live docs contract).
note "doctors"
doctors_bad=0
for s in "${STACKS[@]}"; do
  if ! out="$(cd "samples/$s" && python3 scripts/brief_doctor.py check 2>&1)"; then
    echo "FAIL: doctor failed in samples/$s:" >&2
    printf '%s\n' "$out" | tail -20 | sed 's/^/    /' >&2
    fail=1; doctors_bad=1
  fi
done
[ "$doctors_bad" -eq 0 ] && echo "  green"

# 6. Materialize self-test (extras-scan roots and orphan/extension detection).
note "materialize self-test"
if ! out="$(bash harness/test-materialize.sh 2>&1)"; then
  echo "FAIL: harness/test-materialize.sh did not pass:" >&2
  printf '%s\n' "$out" | tail -20 | sed 's/^/    /' >&2
  fail=1
else
  echo "  pass"
fi

# 6b. Generic-stack self-test (fail-honest gate, pass-when-bound, doctor, no leaks).
note "generic-stack self-test"
if ! out="$(bash harness/test-generic-stack.sh 2>&1)"; then
  echo "FAIL: harness/test-generic-stack.sh did not pass:" >&2
  printf '%s\n' "$out" | tail -20 | sed 's/^/    /' >&2
  fail=1
else
  echo "  pass"
fi

# 7. Marketplace faithfulness — dirty-tree-safe. Re-render the plugin marketplace
#    in place and flag only what the re-render *changes* (a /harness edit that was
#    not repackaged). The render is deterministic, so an in-sync tree is unchanged.
note "marketplace faithfulness"
mkt_before="$(git status --porcelain -- plugins/ .claude-plugin/marketplace.json)"
if ! mkt_out="$(bash harness/package-marketplace.sh 2>&1)"; then
  echo "FAIL: harness/package-marketplace.sh failed:" >&2; printf '%s\n' "$mkt_out" >&2; fail=1
fi
mkt_after="$(git status --porcelain -- plugins/ .claude-plugin/marketplace.json)"
if [ "$mkt_before" != "$mkt_after" ]; then
  echo "FAIL: re-render changed the marketplace — a /harness edit was not repackaged:" >&2
  diff <(printf '%s\n' "$mkt_before") <(printf '%s\n' "$mkt_after") | grep '^>' | sed 's/^> /  /' >&2
  echo "Fix: run harness/package-marketplace.sh and commit the result with the /harness edit." >&2
  fail=1
else
  echo "  marketplace == package-marketplace(/harness)"
fi

# 8. Marketplace acceptance — manifest + plugin.json integrity, the namespace-safety
#    invariant (no plugin prefix baked into a shared skill/agent body), and an
#    install simulation (init + setup.sh + doctor + handoff) for a Go and a Spring
#    plugin. The live model-invocation run stays a manual release step.
note "marketplace acceptance"
if ! mkt_acc="$(bash harness/test-marketplace.sh 2>&1)"; then
  echo "FAIL: harness/test-marketplace.sh did not pass:" >&2; printf '%s\n' "$mkt_acc" >&2; fail=1
else
  echo "  pass"
fi

# 9. Real-CLI install — drives the actual `claude plugin` CLI against the repo as a
#    local marketplace, isolated under a throwaway HOME. Skips when the CLI is absent.
note "real plugin install (claude CLI)"
if ! mkt_inst="$(bash harness/test-plugin-install.sh 2>&1)"; then
  echo "FAIL: harness/test-plugin-install.sh did not pass:" >&2; printf '%s\n' "$mkt_inst" >&2; fail=1
else
  printf '%s\n' "$mkt_inst" | grep -q '^SKIP' && echo "  skip (no claude CLI)" || echo "  pass"
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "PASS check-sync: lint, syntax, parity, tests, faithfulness, doctors, marketplace all green"
else
  echo "FAIL check-sync: see failures above" >&2
  exit 1
fi
