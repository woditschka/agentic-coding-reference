#!/usr/bin/env bash
# Local deterministic gate for the harness + samples. Runs the mechanical,
# no-judgment half of an audit-harness review: lint, syntax, the sample test suites,
# materialization faithfulness, the doctors, and the materialize self-test.
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

fail=0
note() { printf '== %s ==\n' "$1"; }

# 1. Shell lint (harness source scripts).
note "shellcheck (bash)"
if command -v shellcheck >/dev/null 2>&1; then
  while IFS= read -r f; do
    if ! shellcheck -S warning "$f"; then
      echo "FAIL: shellcheck flagged $f" >&2; fail=1
    fi
  done < <(find harness -name '*.sh')
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
note "sample test suites"
for s in go java-spring-boot generic; do
  for t in \
    "scripts/test_brief_doctor.py" \
    "scripts/test_handoff.py" \
    "scripts/test_score_change.py"; do
    if [ -f "samples/$s/$t" ]; then
      if ! ( cd "samples/$s" && python3 "$t" >/dev/null 2>&1 ); then
        echo "FAIL: samples/$s/$t" >&2; fail=1
      fi
    fi
  done
done
[ "$fail" -eq 0 ] && echo "  all suites pass"

# 4b. Sample build files reference live scripts. The battery runs the script
#     tests directly (step 4), not through each sample's own make/gradle gate, so
#     a script that moves can leave a sample's build target dangling while this
#     stays green. Grep the build files for *.py references and confirm each
#     resolves — toolchain-free, no Go/Java needed.
note "sample build-file script refs"
for s in go java-spring-boot generic; do
  for bf in "samples/$s/Makefile" "samples/$s/build.gradle"; do
    [ -f "$bf" ] || continue
    while IFS= read -r p; do
      [ -f "samples/$s/$p" ] || { echo "FAIL: $bf references missing script '$p'" >&2; fail=1; }
    done < <(grep -oE '[A-Za-z0-9_./-]+\.py' "$bf" | sort -u)
  done
done
[ "$fail" -eq 0 ] && echo "  build-file script paths resolve"

# 5. Sample doctors (the live docs contract).
note "doctors"
for s in go java-spring-boot generic; do
  if ! ( cd "samples/$s" && python3 scripts/brief_doctor.py check >/dev/null 2>&1 ); then
    echo "FAIL: doctor failed in samples/$s — run: ( cd samples/$s && python3 scripts/brief_doctor.py check )" >&2
    fail=1
  fi
done
[ "$fail" -eq 0 ] && echo "  green"

# 6. Materialize self-test (extras-scan roots and orphan/extension detection).
note "materialize self-test"
if ! bash harness/test-materialize.sh >/dev/null 2>&1; then
  echo "FAIL: harness/test-materialize.sh did not pass" >&2; fail=1
else
  echo "  pass"
fi

# 6b. Generic-stack self-test (fail-honest gate, pass-when-bound, doctor, no leaks).
note "generic-stack self-test"
if ! bash harness/test-generic-stack.sh >/dev/null 2>&1; then
  echo "FAIL: harness/test-generic-stack.sh did not pass — run: bash harness/test-generic-stack.sh" >&2; fail=1
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
  echo "PASS check-sync: lint, syntax, tests, faithfulness, doctors, marketplace all green"
else
  echo "FAIL check-sync: see failures above" >&2
  exit 1
fi
