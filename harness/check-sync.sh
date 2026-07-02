#!/usr/bin/env bash
# Local deterministic gate for the harness + samples: the mechanical,
# no-judgment half of an audit-harness review. This header is the authoritative
# step list — docs reference it rather than re-enumerating:
#   1  shellcheck (harness/ + tools/)      3f  verdict-enum sync (schemas)
#   2  python syntax                       3g  stack-agnostic core
#   2b agent body parity (per-tool copies) 3h  root link integrity
#   3  materialization faithfulness        4   sample test suites
#   3b sample layout invariants            4b  sample build-file script refs
#   3c project-owned roster sync           5   sample doctors
#   3d placeholder gate                    6   materialize self-test
#   3e handbook delta + self-containment   6b  generic-stack self-test
#                                          7   marketplace faithfulness
#                                          8   marketplace acceptance
#                                          9   real plugin install (claude CLI)
# Aggregates failures (does not stop at the first) and exits non-zero if any
# check fails. Tier 0 of the maintainer loop (root CLAUDE.md): run it after
# every edit — via release-prep.sh after a /harness edit, or as a git pre-push
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

# Print a failed sub-suite's output with the passing noise dropped. The suites
# print failures first, then their "ok …" roll — a bare tail would show only
# the trailing oks and hide the reason. Guarded: an all-ok grep must not kill
# the battery under pipefail.
show_fail() { { printf '%s\n' "$1" | grep -v '^ok' | tail -40 | sed 's/^/    /' >&2; } || true; }

# 1. Shell lint (harness source scripts + the shipped user-level tooling).
note "shellcheck (harness/ + tools/)"
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
# Greps fed by strip_fm use `grep pat >/dev/null`, not `grep -q`: -q exits at
# the first match, awk takes SIGPIPE on a body past the pipe buffer, and
# pipefail turns that 141 into a phantom FAIL (or a silent false pass).
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
    if ! strip_fm "$base" | grep . >/dev/null; then
      echo "FAIL: empty body (or missing frontmatter fence) in ${base#"$root"/}" >&2
      fail=1; parity_bad=1
    fi
    # Each link form is asserted, not just normalized: the claude copy uses the
    # local form (../skills/), siblings the rewritten one (../../.claude/skills/).
    # Without this, a sibling whose link was never rewritten is byte-equal to the
    # base and would pass while shipping a link broken from its directory. The
    # assertion scans the whole body, code fences included — a body that ever
    # needs to *document* the other form must move that example into a skill.
    if strip_fm "$base" | grep '\.\./\.\./\.claude/skills/' >/dev/null; then
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
      if strip_fm "$f" | sed 's:\.\./\.\./\.claude/skills/::g' | grep '\.\./skills/' >/dev/null; then
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
  { diff <(printf '%s\n' "$before") <(printf '%s\n' "$after") | grep '^[<>]' | sed 's/^/  /' >&2; } || true
  echo "Fix: review the change, then commit the re-materialized samples with the /harness edit." >&2
  fail=1
else
  echo "  samples == materialize(/harness)"
fi

# 3b. Sample layout invariants — the cross-tool compatibility rules from
#     docs/specialist-agent-workflow.md as a gate: CLAUDE.md is the single rules
#     file, skills live in .claude/skills/ only, every tool surface is present.
note "sample layout invariants (cross-tool rules, copy channel)"
layout_bad=0
for s in "${STACKS[@]}"; do
  for p in AGENTS.md .github/copilot-instructions.md .github/skills .opencode/skills .junie/skills; do
    if [ -e "samples/$s/$p" ]; then
      echo "FAIL: samples/$s/$p exists — CLAUDE.md is the single rules file and skills live in .claude/skills/ only" >&2
      fail=1; layout_bad=1
    fi
  done
  for p in CLAUDE.md .junie/config.json .claude/agents .github/agents .opencode/agents .junie/agents .claude/skills; do
    if [ ! -e "samples/$s/$p" ]; then
      echo "FAIL: samples/$s/$p missing — required by the cross-tool compatibility rules" >&2
      fail=1; layout_bad=1
    fi
  done
  # Copy-channel rule: declared in layout.toml, no silent extension creep, the
  # runtime git-tracked, the ledger ignored but never the runtime.
  lt="samples/$s/scripts/layout.toml"
  if ! grep -qE 'channel *= *"copy"' "$lt" 2>/dev/null; then
    echo "FAIL: $lt does not declare channel = \"copy\"" >&2; fail=1; layout_bad=1
  fi
  if ! grep -qE 'extensions *= *\[\]' "$lt" 2>/dev/null; then
    echo "FAIL: $lt extensions is not [] — the samples declare none; a non-empty list weakens orphan detection" >&2
    fail=1; layout_bad=1
  fi
  if [ -z "$(git ls-files "samples/$s/.claude/skills")" ]; then
    echo "FAIL: samples/$s runtime is untracked — the copy channel commits it" >&2; fail=1; layout_bad=1
  fi
  if ! grep -q '^\.scratch/' "samples/$s/.gitignore" 2>/dev/null; then
    echo "FAIL: samples/$s/.gitignore does not ignore .scratch/" >&2; fail=1; layout_bad=1
  fi
  if grep -q '\.claude/skills' "samples/$s/.gitignore" 2>/dev/null; then
    echo "FAIL: samples/$s/.gitignore ignores the runtime — the copy channel commits it" >&2; fail=1; layout_bad=1
  fi
done
[ "$layout_bad" -eq 0 ] && echo "  cross-tool rules and channel invariants hold"

# 3c. Project-owned roster sync. Faithfulness (step 3) covers only the runtime;
#     the project-owned committed files drift silently when the shipped roster
#     changes. Gates: skills table both directions (scoped to its two chapters),
#     agents README roster, init skeleton coverage, brief roster, ADR placement.
#     Also gates the ROOT skill tables — CLAUDE.md "Root-Level Skills" and
#     README "Reference Upkeep" — against .claude/skills/, both directions.
#     Row *descriptions* stay judgment (/audit-harness Layer 2 check 5).
note "project-owned roster sync (skills tables incl. root, agents README, init coverage)"
roster_bad=0
# Skill-name rows inside the two skills chapters of a sample's CLAUDE.md:
# "Agent Usage (Mandatory)" carries the shared table, "Stack-specific skills"
# the stack's own. Scoping keeps the commit-type tables out of the reverse sweep.
skills_rows() {
  awk '/^## /{insec=0} /^## Agent Usage|^## Stack-specific skills/{insec=1} insec' "$1" \
    | sed -n 's/^| `\([a-z0-9-]*\)`.*/\1/p'
}
for s in "${STACKS[@]}"; do
  shipped=" "
  skills_seen=0
  for d in "$here/core/.claude/skills/"*/ "$here/stacks/$s/.claude/skills/"*/; do
    [ -d "$d" ] || continue
    n="$(basename "$d")"
    shipped="$shipped$n "
    skills_seen=$((skills_seen + 1))
    if ! grep -q "| \`$n\`" "samples/$s/CLAUDE.md"; then
      echo "FAIL: samples/$s/CLAUDE.md skills table has no row for shipped skill '$n'" >&2
      fail=1; roster_bad=1
    fi
  done
  # Vacuous-pass backstop, same reason as step 2b's bases counter: a renamed
  # skills root would otherwise let this loop check nothing and pass.
  if [ "$skills_seen" -eq 0 ]; then
    echo "FAIL: no shipped skills found for stack $s — roster empty or path renamed" >&2
    fail=1; roster_bad=1
  fi
  while IFS= read -r n; do
    case "$shipped" in
      *" $n "*) ;;
      *) echo "FAIL: samples/$s/CLAUDE.md skills table row '$n' names no shipped skill — ghost row" >&2
         fail=1; roster_bad=1 ;;
    esac
  done < <(skills_rows "samples/$s/CLAUDE.md")
  for f in "$here/core/.claude/agents/"*.md "$here/stacks/$s/.claude/agents/"*.md; do
    [ -f "$f" ] || continue
    a="$(basename "$f" .md)"; [ "$a" = "README" ] && continue
    if ! grep -q "\*\*$a\*\*" "samples/$s/.claude/agents/README.md"; then
      echo "FAIL: samples/$s/.claude/agents/README.md has no roster row for shipped agent '$a'" >&2
      fail=1; roster_bad=1
    fi
  done
  for pair in \
    "CLAUDE.md=$here/init/stacks/$s/CLAUDE.md" \
    ".claude/settings.json=$here/init/core/.claude/settings.json" \
    "scripts/layout.toml=$here/init/stacks/$s/scripts/layout.toml" \
    ".gitignore=$here/init/core/gitignore-runtime.txt"; do
    tgt="${pair%%=*}"; src="${pair#*=}"
    [ -f "samples/$s/$tgt" ] || { echo "FAIL: samples/$s/$tgt missing (project-owned committed file)" >&2; fail=1; roster_bad=1; }
    [ -f "$src" ] || { echo "FAIL: ${src#"$root"/} missing — no init skeleton source for $tgt" >&2; fail=1; roster_bad=1; }
  done
  for t in "$here/core/.claude/skills/doctor/templates/"*.md; do
    b="$(basename "$t")"
    case "$b" in adr-README.md) brief="docs/adr/README.md" ;; *) brief="docs/$b" ;; esac
    [ -f "samples/$s/$brief" ] || { echo "FAIL: samples/$s/$brief missing — the doctor template $b has no sample brief" >&2; fail=1; roster_bad=1; }
  done
  # ADR placement: a sample's decision log starts empty — README.md only
  # (enforces the adr-placement ADR; the reference's log lives at root docs/adr/).
  if [ "$(ls "samples/$s/docs/adr" 2>/dev/null)" != "README.md" ]; then
    echo "FAIL: samples/$s/docs/adr must contain only README.md — no harness ADR is materialized" >&2
    fail=1; roster_bad=1
  fi
done
# Root skill tables. Same drift mode as the samples' tables: a skill added or
# retired at the root must reach both tables the same session. The adoption
# trio (init, materialize, harvest) is documented in the README's "Adopt in
# Your Own Project" chapter — mention-guarded below — so the "Reference
# Upkeep" table exempts it in BOTH directions. Greps read via >/dev/null,
# not -q — same SIGPIPE/pipefail reasoning as step 2b.
root_table_rows() { # $1 = file, $2 = section-heading regex (backslash-free)
  awk -v sec="$2" '/^## /{insec=($0 ~ sec)} insec' "$1" \
    | sed -n 's/^| `\([a-z0-9-]*\)`.*/\1/p'
}
root_shipped=" "
root_seen=0
for d in .claude/skills/*/; do
  [ -d "$d" ] || continue
  n="$(basename "$d")"
  root_shipped="$root_shipped$n "
  root_seen=$((root_seen + 1))
  if ! root_table_rows CLAUDE.md '^## Root-Level Skills$' | grep -Fxe "$n" >/dev/null; then
    echo "FAIL: root CLAUDE.md Root-Level Skills table has no row for skill '$n'" >&2
    fail=1; roster_bad=1
  fi
  case "$n" in
    init|materialize|harvest)
      # The trio's documented home; without this it could vanish from the
      # README entirely while both table sweeps stay green. The chapter names
      # them as user-typed commands (`/init`) or bare (`init`) — accept both.
      if ! awk '/^## /{insec=($0 ~ /^## Adopt in Your Own Project$/)} insec' README.md \
          | grep -Fe "\`$n\`" -e "\`/$n\`" >/dev/null; then
        echo "FAIL: README.md Adopt in Your Own Project chapter never mentions '$n'" >&2
        fail=1; roster_bad=1
      fi
      ;;
    *)
      if ! root_table_rows README.md '^## Reference Upkeep$' | grep -Fxe "$n" >/dev/null; then
        echo "FAIL: README.md Reference Upkeep table has no row for root skill '$n'" >&2
        fail=1; roster_bad=1
      fi
      ;;
  esac
done
# Vacuous-pass backstop, same reason as the samples' skills_seen counter.
if [ "$root_seen" -eq 0 ]; then
  echo "FAIL: no root skills found under .claude/skills/ — roster empty or path renamed" >&2
  fail=1; roster_bad=1
fi
for pair in 'CLAUDE.md=^## Root-Level Skills$' 'README.md=^## Reference Upkeep$'; do
  file="${pair%%=*}"; sec="${pair#*=}"
  while IFS= read -r n; do
    case "$root_shipped" in
      *" $n "*)
        if [ "$file" = "README.md" ]; then
          case "$n" in
            init|materialize|harvest)
              echo "FAIL: README.md Reference Upkeep row '$n' — the adoption trio is documented in Adopt in Your Own Project, not here" >&2
              fail=1; roster_bad=1 ;;
          esac
        fi
        ;;
      *)
        echo "FAIL: $file table row '$n' names no root skill — ghost row" >&2
        fail=1; roster_bad=1 ;;
    esac
  done < <(root_table_rows "$file" "$sec")
done
[ "$roster_bad" -eq 0 ] && echo "  tables and skeleton coverage in sync"

# 3d. Placeholder gate — the PROJECT_NAME / PROJECT_DESCRIPTION template tokens
#     may appear only in the documented template locations. The go and java
#     samples stay deliberately in template state (they double as readable
#     demos); the generic sample ships init-filled — the allowlist permits both.
#     The allowlist is per-file; token *placement* inside an allowed brief stays
#     judgment. A hit anywhere else is a leak into runtime content. The tokens
#     are built by concatenation so this script never matches itself.
note "placeholder gate (template tokens outside documented locations)"
ph1='{{'PROJECT_NAME'}}'
ph2='{{'PROJECT_DESCRIPTION'}}'
ph_allow='^(\.claude/skills/(init|harvest)/SKILL\.md$|harness/init/|harness/init\.sh$|harness/core/\.claude/skills/doctor/|harness/core/scripts/test_brief_doctor\.py$|plugins/[a-z-]+/skills/doctor/|plugins/[a-z-]+/_engine/scripts/test_brief_doctor\.py$|samples/[a-z-]+/\.claude/skills/doctor/|samples/[a-z-]+/scripts/test_brief_doctor\.py$|samples/[a-z-]+/CLAUDE\.md$|samples/[a-z-]+/docs/(prd|system-design)\.md$|samples/go/Makefile$)'
ph_bad=0
while IFS= read -r f; do
  rel="${f#./}"
  if ! printf '%s\n' "$rel" | grep -qE "$ph_allow"; then
    echo "FAIL: template placeholder leaked into $rel — outside the documented template locations" >&2
    fail=1; ph_bad=1
  fi
done < <(grep -rlI --exclude-dir=.git --exclude-dir=__pycache__ -e "$ph1" -e "$ph2" . 2>/dev/null)
# Canary against a vacuous pass: the init skeletons must carry the token — if
# the token format ever changes, this fails instead of the gate scanning for
# a string nothing contains.
for s in "${STACKS[@]}"; do
  if ! grep -ql "$ph1" "$here/init/stacks/$s/CLAUDE.md" 2>/dev/null; then
    echo "FAIL: $ph1 not found in harness/init/stacks/$s/CLAUDE.md — token format changed; the placeholder gate is scanning for nothing" >&2
    fail=1; ph_bad=1
  fi
done
[ "$ph_bad" -eq 0 ] && echo "  placeholders only in documented template locations"

# 3e. Handbook delta + sample self-containment. The root handbook and its
#     installed core copy differ only by the pinned delta (links + doc-form
#     pointers) recorded in harness/handbook-delta.expected — any other
#     divergence is content drift. Sample docs must stand alone: no reference
#     to another sample or to the monorepo samples/ tree.
note "handbook delta (root vs core copy) + sample self-containment"
hb_bad=0
core_hb="$here/core/.claude/skills/pipeline-handoff/agentic-harness.md"
actual_delta="$( (diff -U0 docs/agentic-harness.md "$core_hb" || true) | grep -E '^[-+]' | grep -vE '^(---|\+\+\+)' || true)"
if [ ! -f "$here/handbook-delta.expected" ]; then
  echo "FAIL: harness/handbook-delta.expected missing — the pinned handbook delta has no reference" >&2
  fail=1; hb_bad=1
  expected_delta=""
else
  expected_delta="$(grep -v '^#' "$here/handbook-delta.expected" || true)"
fi
if [ "$hb_bad" -eq 0 ] && [ "$actual_delta" != "$expected_delta" ]; then
  echo "FAIL: docs/agentic-harness.md vs its core copy diverged beyond harness/handbook-delta.expected:" >&2
  { diff <(printf '%s\n' "$expected_delta") <(printf '%s\n' "$actual_delta") | sed 's/^/    /' >&2; } || true
  echo "Fix: reconcile the two copies (owner: docs/agentic-harness.md). Regenerating the" >&2
  echo "expected delta is an explicit decision — a diff touching it needs the same review as content drift." >&2
  fail=1; hb_bad=1
fi
sc_hits="$( { grep -rlE 'java-spring-boot' samples/go/docs samples/generic/docs 2>/dev/null
              grep -rlE '\bgo/' samples/java-spring-boot/docs samples/generic/docs 2>/dev/null
              grep -rlE '\bgeneric/' samples/go/docs samples/java-spring-boot/docs 2>/dev/null
              grep -rl 'samples/' samples/go/docs samples/java-spring-boot/docs samples/generic/docs 2>/dev/null
            } | sort -u || true)"
if [ -n "$sc_hits" ]; then
  printf '%s\n' "$sc_hits" | while IFS= read -r h; do
    echo "FAIL: $h references another sample or the samples/ tree — sample docs must be self-contained" >&2
  done
  fail=1; hb_bad=1
fi
[ "$hb_bad" -eq 0 ] && echo "  delta pinned, samples self-contained"

# 3f. Verdict-enum sync — the schema enums the routing contract depends on.
#     This pins the schemas to a literal copy of the canonical names, so a
#     schema edit cannot silently widen or narrow a verdict space. Prose drift
#     in the skills that document the sets stays judgment (/audit-harness Layer 2).
note "verdict-enum sync (design-block, review-feedback)"
if enum_out="$(python3 - <<'PY' 2>&1
import json
def verdicts(p):
    return set(json.load(open(p))['properties']['verdict']['enum'])
bad = []
db = verdicts('harness/core/schemas/scratch/design-block.schema.json')
rf = verdicts('harness/core/schemas/scratch/review-feedback.schema.json')
if db != {'covered','minor','new','refactor-first','foundational','conflicting'}:
    bad.append('design-block verdict enum is %s' % sorted(db))
if rf != {'approved','changes_requested','blocked'}:
    bad.append('review-feedback verdict enum is %s' % sorted(rf))
if bad:
    raise SystemExit('; '.join(bad))
print('ok')
PY
)"; then
  echo "  enums match the documented verdict sets"
else
  echo "FAIL: verdict-enum sync: $enum_out" >&2; fail=1
fi

# 3g. Stack-agnostic core — no stack-specific fact in harness/core/ (the
#     invariant from harness/README.md). The token list is the canonical set of
#     stack facts; a hit means the fact belongs in stacks/<stack>/, a brief, or
#     scripts/layout.toml.
note "stack-agnostic core (no stack token in harness/core)"
[ -d "$here/core" ] || { echo "FAIL: $here/core missing — cannot scan for stack tokens" >&2; fail=1; }
# grep's exit codes are handled separately: 0 = tokens found (FAIL), 1 = clean
# (pass), >=2 = the scan itself broke (FAIL, not a pass) — e.g. an unreadable
# directory would otherwise report "no stack token" without having looked.
core_rc=0
core_hits="$(grep -rnE '\bgo\.mod\b|gradlew|build\.gradle|pom\.xml|\.go\b|\.java\b|golangci|spotless|JUnit|com/example' "$here/core" 2>&1)" || core_rc=$?
if [ "$core_rc" -eq 0 ]; then
  echo "FAIL: stack-specific tokens in harness/core/ — move to stacks/<stack>/:" >&2
  printf '%s\n' "$core_hits" | head -10 | sed 's/^/    /' >&2
  fail=1
elif [ "$core_rc" -ge 2 ]; then
  echo "FAIL: could not scan harness/core/ for stack tokens (grep exit $core_rc):" >&2
  printf '%s\n' "$core_hits" | head -5 | sed 's/^/    /' >&2
  fail=1
else
  echo "  core carries no stack token"
fi

# 3h. Root link integrity — every markdown link target in the root-level files
#     (README, CLAUDE.md, docs/, root skills, tools/, harness/README.md) must
#     resolve. Fenced code blocks are skipped (they carry illustrative paths);
#     anchors are not checked (judgment work, /audit-harness Layer 2).
note "root link integrity (markdown links resolve)"
if link_out="$(python3 - <<'PY'
import glob, os, re, sys
files = ['README.md', 'CLAUDE.md', 'harness/README.md']
for pat in ('docs/**/*.md', '.claude/skills/**/*.md', 'tools/**/*.md'):
    files += glob.glob(pat, recursive=True)
link = re.compile(r'\]\(([^)\s]+)\)')
bad = []
for f in sorted(set(files)):
    if not os.path.isfile(f):
        continue
    fence = False
    for i, line in enumerate(open(f, encoding='utf-8'), 1):
        if line.lstrip().startswith('```'):
            fence = not fence
            continue
        if fence:
            continue
        for t in link.findall(line):
            if t.startswith(('http://', 'https://', 'mailto:', '#')):
                continue
            if '{{' in t or '<' in t:
                continue
            p = t.split('#')[0]
            if p and not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(f), p))):
                bad.append('%s:%d -> %s' % (f, i, t))
if bad:
    print('\n'.join(bad))
    sys.exit(1)
print('ok')
PY
)"; then
  echo "  links resolve"
else
  echo "FAIL: broken markdown links in root-level files:" >&2
  printf '%s\n' "$link_out" | sed 's/^/    /' >&2
  fail=1
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
      show_fail "$out"
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
# Each stack also declares its expected minimum .py-ref count, so the check
# cannot go vacuous: a Makefile/build.gradle that stops referencing any script
# is a FAIL, not an empty loop. Generic's stack.sh is an unfilled-by-design
# skeleton (the consumer binds it), so its zero is expected and printed loud.
refs_bad=0
for s in "${STACKS[@]}"; do
  case "$s" in
    go)               bf="samples/$s/Makefile";         min_refs=1 ;;
    java-spring-boot) bf="samples/$s/build.gradle";     min_refs=1 ;;
    generic)          bf="samples/$s/scripts/stack.sh"; min_refs=0 ;;
    *) echo "FAIL: stack '$s' has no build-binding file declared — extend the case in step 4b" >&2
       fail=1; refs_bad=1; continue ;;
  esac
  if [ ! -f "$bf" ]; then
    echo "FAIL: $bf missing — the stack's declared build-binding file" >&2
    fail=1; refs_bad=1; continue
  fi
  n_refs=0
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    n_refs=$((n_refs + 1))
    [ -f "samples/$s/$p" ] || { echo "FAIL: $bf references missing script '$p'" >&2; fail=1; refs_bad=1; }
  done < <(grep -oE '[A-Za-z0-9_./-]+\.py' "$bf" | sort -u || true)
  if [ "$n_refs" -lt "$min_refs" ]; then
    echo "FAIL: $bf references $n_refs .py scripts (expected >= $min_refs) — step 4b went vacuous for '$s'" >&2
    fail=1; refs_bad=1
  elif [ "$n_refs" -eq 0 ]; then
    echo "  $s: 0 .py refs in ${bf#samples/"$s"/} — consumer-bound stack, vacuous by design"
  fi
done
[ "$refs_bad" -eq 0 ] && echo "  build-file script paths resolve"

# 5. Sample doctors (the live docs contract).
note "sample doctors"
doctors_bad=0
for s in "${STACKS[@]}"; do
  if ! out="$(cd "samples/$s" && python3 scripts/brief_doctor.py check 2>&1)"; then
    echo "FAIL: doctor failed in samples/$s:" >&2
    show_fail "$out"
    fail=1; doctors_bad=1
  fi
done
[ "$doctors_bad" -eq 0 ] && echo "  green"

# 6. Materialize self-test (extras-scan roots and orphan/extension detection).
note "materialize self-test"
if ! out="$(bash harness/test-materialize.sh 2>&1)"; then
  echo "FAIL: harness/test-materialize.sh did not pass:" >&2
  show_fail "$out"
  fail=1
else
  echo "  pass"
fi

# 6b. Generic-stack self-test (fail-honest gate, pass-when-bound, doctor, no leaks).
note "generic-stack self-test"
if ! out="$(bash harness/test-generic-stack.sh 2>&1)"; then
  echo "FAIL: harness/test-generic-stack.sh did not pass:" >&2
  show_fail "$out"
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
  { diff <(printf '%s\n' "$mkt_before") <(printf '%s\n' "$mkt_after") | grep '^[<>]' | sed 's/^/  /' >&2; } || true
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
  echo "PASS check-sync: lint, syntax, parity, faithfulness, invariants, tests, doctors, marketplace all green"
else
  echo "FAIL check-sync: see failures above" >&2
  exit 1
fi
