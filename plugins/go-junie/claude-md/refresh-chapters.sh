#!/usr/bin/env bash
# Refresh the harness-managed chapters of a consumer's CLAUDE.md in place.
#
#   refresh-chapters.sh <claude-md> <harness-root>
#
# CLAUDE.md is project-owned — scaffolded once, never overwritten. But several of
# its chapters are stack-agnostic harness doctrine: Agent Usage, Memory, Writing
# Standards, the Scratch Directory, Documentation Updates. They are single-sourced
# in one file, harness/claude-md/managed-chapters.md, whose chapters are the
# managed set — add a chapter by adding a `## ` section, remove one by deleting
# it. That file mirrors the shipped CLAUDE.md: what you read here, in this order,
# is what materializes. Each chapter is identified by its `## ` heading and
# replaced in the target in place: from that heading to the next `## ` heading (or
# end of file). Only the managed chapters are rewritten; every other chapter is
# the project's, including the per-stack `## Stack-specific skills` chapter and all
# build/toolchain/convention chapters. Chapters stay interleaved in the project's
# own order — each is found and replaced independently by its heading.
#
# Heading detection is fence-aware: a `## ` line inside a ```fenced``` block is
# illustrative text, not a chapter boundary, and is never matched or treated as a
# boundary — matching the doctor's check_required_chapters. Without this a
# consumer that quotes a managed heading inside an example fence would be
# corrupted by the replace.
#
# A heading that is absent in the target (a greenfield or legacy file with a
# renamed/missing chapter) is reported and left untouched for the /init fill
# (greenfield) or the /materialize migration (legacy).
#
# This tree is source-only: not under core/ or stacks/, so materialize.sh never
# copies it into a target as runtime.
set -euo pipefail

# Is $2 present as a real (non-fenced) heading line in file $1?
heading_present() { # <file> <title>
  awk -v t="$2" 'BEGIN{r=1} /^[ \t]*```/{f=!f; next} !f && $0==t {r=0; exit} END{exit r}' "$1"
}

# Print each real (non-fenced) `## ` heading of file $1, in order.
chapter_titles() { # <source>
  awk '/^[ \t]*```/{f=!f; next} !f && /^## /{print}' "$1"
}

# Print the chapter named $2 from source $1: the heading line through the line
# before the next real `## ` heading (or end of file), fence-aware. Trailing
# blank lines are trimmed so replace_chapter controls the single separating blank.
extract_chapter() { # <source> <title>
  awk -v t="$2" '
    /^[ \t]*```/ { if (started) print; fence = !fence; next }
    !fence && !started && $0 == t { started = 1; print; next }
    started && !fence && /^## / { exit }
    started { print }
  ' "$1" | awk 'NF{p=NR} {a[NR]=$0} END{for (i=1; i<=p; i++) print a[i]}'
}

# Replace one heading-bounded chapter of $claude with the contents of $src.
# Assumes the heading (first line of $src) is present as a real heading in
# $claude. Fence-aware: the title is matched and the chapter boundary (next
# `## `) is recognized only outside fenced blocks. The temp file is created in
# the target's own directory so the final mv is a same-filesystem atomic rename,
# never a cross-device copy that an interruption could leave half-written.
replace_chapter() { # <claude-md> <chapter-src> <title>
  local claude="$1" src="$2" title="$3" tmp
  tmp="$(mktemp "$(dirname "$claude")/.claude-md.XXXXXX")"
  # shellcheck disable=SC2064  # expand $tmp now, on trap setup
  trap "rm -f '$tmp'" RETURN
  awk -v sf="$src" -v title="$title" '
    /^[ \t]*```/ {                       # fence delimiter: toggle, keep unless dropping
      if (skip) { fence = !fence; next }
      fence = !fence; print; next
    }
    !fence && !done && $0 == title {     # real heading match: drop it, inject source
      while ((getline l < sf) > 0) print l; close(sf)   # source first line IS the heading
      skip = 1; done = 1; next
    }
    skip && !fence && /^## / {           # real next chapter: one blank, then the heading
      skip = 0; print ""; print; next
    }
    skip { next }                        # still inside the old chapter body — drop
    { print }                            # at EOF while skip, nothing trails the injection
  ' "$claude" > "$tmp"
  mv "$tmp" "$claude"
}

apply() { # <claude-md> <harness-root>
  local claude="$1" src="$2/claude-md/managed-chapters.md"
  [ -f "$claude" ] || { echo "refresh: no CLAUDE.md at $claude" >&2; return 1; }
  [ -f "$src" ]    || { echo "refresh: missing chapter source $src" >&2; return 1; }
  case "$(head -1 "$src")" in
    "## "*) ;;
    *) echo "refresh: $src must start with a '## ' heading" >&2; return 1 ;;
  esac
  # Resolve a symlinked target to its backing file, so the temp-then-rename below
  # updates the real file and preserves the link instead of clobbering the symlink
  # with a regular file. readlink (without -f) is portable across macOS and Linux;
  # the loop follows a chain of links.
  local link
  while [ -L "$claude" ]; do
    link="$(readlink "$claude")"
    case "$link" in
      /*) claude="$link" ;;
      *)  claude="$(dirname "$claude")/$link" ;;
    esac
  done
  # CRLF guard. Heading matching is exact, so a CRLF target (`## Memory\r`) would
  # match no managed heading and silently refresh nothing — and the marketplace
  # setup.sh runs no doctor to catch it. Refuse loudly instead. Normalizing here
  # would either still miss the match or mix line endings on write; the consumer
  # normalizes to LF (the harness convention) and re-runs.
  if LC_ALL=C grep -q $'\r' "$claude"; then
    echo "refresh: $claude has CRLF line endings — normalize to LF, then re-run" >&2
    echo "0 refreshed (CRLF — normalize to LF)"
    return 0
  fi
  # Pre-flight, before any write: the managed set is the source's `## ` headings.
  # It must be non-empty and duplicate-free. A duplicate would replace the same
  # target chapter twice; validating here (not mid-loop) means a malformed source
  # fails loud and never half-refreshes the target.
  local titles seen=" " title
  titles="$(chapter_titles "$src")"
  [ -n "$titles" ] || { echo "refresh: $src has no '## ' chapters" >&2; return 1; }
  while IFS= read -r title; do
    case "$seen" in
      *" $title "*) echo "refresh: $src has a duplicate '$title' chapter" >&2; return 1 ;;
    esac
    seen="$seen$title "
  done <<EOF
$titles
EOF
  # Apply: replace each chapter present in the target, report the absent ones.
  local refreshed=0 absent=() chap
  while IFS= read -r title; do
    if heading_present "$claude" "$title"; then
      chap="$(mktemp "$(dirname "$claude")/.chap.XXXXXX")"
      extract_chapter "$src" "$title" > "$chap"
      replace_chapter "$claude" "$chap" "$title"
      rm -f "$chap"
      refreshed=$((refreshed + 1))
    else
      absent+=("$title")
    fi
  done <<EOF
$titles
EOF
  if [ ${#absent[@]} -eq 0 ]; then
    echo "$refreshed refreshed"
  else
    echo "$refreshed refreshed, ${#absent[@]} absent: ${absent[*]}"
  fi
}

apply "$@"
