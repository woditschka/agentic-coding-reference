#!/usr/bin/env bash
# Render the per-tool agent mirror bodies from their .claude base, in place.
#
#   harness/refresh-agent-bodies.sh [layer-dir ...]
#
# With no arguments, renders every source layer: harness/core and each
# harness/stacks/<stack> (STACKS roster in helpers.sh).
#
# Each agent exists four times per layer: the base in .claude/agents/<name>.md
# and three mirrors — .junie/agents/<name>.md, .opencode/agents/<name>.md,
# .github/agents/<name>.agent.md. The body below the frontmatter is shared
# doctrine and must be byte-identical (check-sync step 2b gates it); the
# frontmatter is hand-owned per tool because it encodes per-tool decisions:
# Copilot's handoffs blocks, OpenCode's mcp-deny permissions, Junie dropping
# the IDE oracle.
#
# This script makes the shared half mechanical — the same split managed
# chapters use for CLAUDE.md (claude-md/refresh-chapters.sh): keep each
# mirror's frontmatter, replace everything below its closing fence with the
# base body. Skill links are rewritten to the mirror-relative form on the way
# (../skills/ → ../../.claude/skills/), the one documented body difference
# step 2b normalizes.
#
# The .claude base is the source of truth for the roster, in both directions.
# Adding an agent means authoring its three mirror frontmatters once — a
# per-tool policy decision that stays an explicitly reviewed human step, so a
# missing mirror fails loud, never auto-created. Removing an agent is one base
# deletion: the render prunes any mirror whose base is gone — but never on a
# layer with failures, so a rename (missing mirrors plus orphans) keeps its
# authored frontmatter for a git mv. After that, every body edit is one file:
# the base.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

# shellcheck source=harness/helpers.sh
. "$here/helpers.sh"

# Body: everything below the frontmatter's closing fence. Only the fence pair
# is stripped — a "---" rule inside the body is content (same rule as 2b).
body_of() { awk '/^---[ \t]*$/ && n<2 {n++; next} n>=2 {print}' "$1"; }

# Frontmatter: line 1 through the closing fence, verbatim.
frontmatter_of() { awk '{print} /^---[ \t]*$/ && ++n==2 {exit}' "$1"; }

# Line 1 must open a fence and a second fence must close it somewhere below.
well_formed() {
  awk 'NR==1 && $0 !~ /^---[ \t]*$/ {bad=1}
       /^---[ \t]*$/ {n++}
       END {exit (bad || n < 2) ? 1 : 0}' "$1"
}

# Base link form → mirror link form (inverse of check-sync's norm_links).
mirror_links() { sed 's:\.\./skills/:../../.claude/skills/:g'; }

layers=("$@")
if [ ${#layers[@]} -eq 0 ]; then
  layers=("$here/core")
  for s in "${STACKS[@]}"; do layers+=("$here/stacks/$s"); done
fi

tmp=''
trap '[ -n "$tmp" ] && rm -f "$tmp"' EXIT

fail=0 rendered=0 current=0 pruned=0
for layer in "${layers[@]}"; do
  if [ ! -d "$layer/.claude/agents" ]; then
    echo "FAIL: no .claude/agents under $layer" >&2; fail=1; continue
  fi
  fail_before=$fail
  bases=0
  for base in "$layer/.claude/agents/"*.md; do
    [ -f "$base" ] || continue
    a="$(basename "$base" .md)"; [ "$a" = "README" ] && continue
    bases=$((bases + 1))
    if ! well_formed "$base"; then
      echo "FAIL: $base has no frontmatter fence pair" >&2; fail=1; continue
    fi
    # grep pat >/dev/null, not grep -q: -q exits at the first match, awk takes
    # SIGPIPE on a long body, and pipefail turns that into a phantom failure.
    if ! body_of "$base" | grep . >/dev/null; then
      echo "FAIL: $base has an empty body" >&2; fail=1; continue
    fi
    if body_of "$base" | grep '\.\./\.\./\.claude/skills/' >/dev/null; then
      echo "FAIL: $base uses the mirror link form (../../.claude/skills/) — a base uses ../skills/" >&2
      fail=1; continue
    fi
    # ../../skills/ is broken from .claude/agents/ AND would be over-rewritten
    # to ../../../.claude/skills/ by the render — refuse rather than propagate.
    if body_of "$base" | grep '\.\./\.\./skills/' >/dev/null; then
      echo "FAIL: $base links ../../skills/ — broken from .claude/agents/; use ../skills/" >&2
      fail=1; continue
    fi
    for mirror in "$layer/.junie/agents/$a.md" \
                  "$layer/.opencode/agents/$a.md" \
                  "$layer/.github/agents/$a.agent.md"; do
      if [ ! -f "$mirror" ]; then
        echo "FAIL: missing mirror $mirror — author its frontmatter once, then re-run" >&2
        fail=1; continue
      fi
      if ! well_formed "$mirror"; then
        echo "FAIL: $mirror has no frontmatter fence pair" >&2; fail=1; continue
      fi
      # Temp file in the mirror's own directory: the mv is a same-filesystem
      # atomic rename, never a cross-device copy an interruption could truncate.
      tmp="$(mktemp "$(dirname "$mirror")/.agent-body.XXXXXX")"
      { frontmatter_of "$mirror"; body_of "$base" | mirror_links; } > "$tmp"
      if cmp -s "$tmp" "$mirror"; then
        rm -f "$tmp"; current=$((current + 1))
      else
        mv "$tmp" "$mirror"; rendered=$((rendered + 1))
        echo "  rendered ${mirror#"$here/"}"
      fi
      tmp=''
    done
  done
  # An empty roster is a renamed path or a gutted layer, not a no-op — same
  # verdict check-sync 2b reaches on the committed tree.
  if [ "$bases" -eq 0 ]; then
    echo "FAIL: no agent bases under $layer/.claude/agents — roster empty or path renamed" >&2
    fail=1; continue
  fi
  # Prune: removal follows the base. A mirror whose base is gone is deleted;
  # only files matching the tool's agent-file pattern are touched — READMEs are
  # never pruned; wrong-suffix strays are left for 2b's reverse sweep to flag. Never prune a
  # layer that just failed: a renamed base looks like missing mirrors PLUS
  # orphans, and deleting the orphans would destroy the authored frontmatter a
  # git mv could have kept. Resolve the failures, re-run, then prune fires.
  if [ "$fail" -ne "$fail_before" ]; then
    echo "  prune skipped under $layer: resolve the failures above, then re-run" >&2
    continue
  fi
  for d in .junie/agents .opencode/agents .github/agents; do
    for f in "$layer/$d/"*; do
      [ -f "$f" ] || continue
      n="$(basename "$f")"
      case "$d" in
        .github/agents) case "$n" in *.agent.md) a="${n%.agent.md}" ;; *) continue ;; esac ;;
        *)              case "$n" in *.md)       a="${n%.md}"       ;; *) continue ;; esac ;;
      esac
      [ "$a" = "README" ] && continue
      if [ ! -f "$layer/.claude/agents/$a.md" ]; then
        rm "$f"; pruned=$((pruned + 1))
        echo "  pruned ${f#"$here/"}"
      fi
    done
  done
done

echo "$rendered rendered, $current already current, $pruned pruned"
exit "$fail"
