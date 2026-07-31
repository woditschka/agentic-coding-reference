#!/usr/bin/env bash
# Cut one lockstep harness version: stamp VERSION (+ its release date), run
# propagate-harness.sh (propagate + full battery), then create the release commit and
# the annotated v<VERSION> tag. Stops there — it never pushes; it prints the
# push commands instead. The /release-version skill is the interactive
# front-end: it evaluates the semver bump and confirms with the user, then
# calls this with the agreed version.
#
#   harness/release-version.sh <new-version>     e.g. 0.1.14
#
# Guards: dotted-numeric format, strictly greater than harness/VERSION
# (forward-only), clean working tree (the release commit must hold only this
# run's bump and propagation).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/.." && pwd)"
cd "$root"

# shellcheck source=harness/registry.sh
. "$here/registry.sh"

new="${1:?usage: release-version.sh <new-version>  (e.g. 0.1.14)}"

if ! printf '%s\n' "$new" | grep -qE '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'; then
  echo "FAIL: '$new' is not a MAJOR.MINOR.PATCH semver (e.g. 0.1.14)" >&2; exit 1
fi

cur="$(read_stamp "$here/VERSION" release-version)"
if [ "$new" = "$cur" ] || [ "$(printf '%s\n%s\n' "$cur" "$new" | sort -V | tail -1)" != "$new" ]; then
  echo "FAIL: $new is not strictly greater than the current $cur (releases are forward-only)" >&2
  exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "FAIL: working tree not clean — commit or stash first; the release commit holds only this run's bump and propagation" >&2
  exit 1
fi

note "release-version: $cur -> $new"
# VERSION-DATE is the deterministic release date materialize stamps into every
# consumer's CLAUDE.md; a wall-clock-at-materialize value would break the
# faithfulness battery.
printf '%s\n' "$new" > "$here/VERSION"
date -u +%Y-%m-%d > "$here/VERSION-DATE"

# The tree was clean at the guard above, so a battery failure reverts the stamp
# and its propagation wholesale — fix at source, then re-run the same version.
# checkout restores tracked files; clean removes files the propagation newly
# created (untracked, so provably this run's) in the materialization targets.
if ! "$here/propagate-harness.sh"; then
  echo "FAIL: propagate-harness failed — reverting the version stamp and its propagation (tree restored to clean)" >&2
  git checkout -- .
  git clean -qfd -- samples/ plugins/ .claude-plugin/
  exit 1
fi

git add -A
git commit -m "chore(release): v$new"
git tag -a "v$new" -m "harness v$new"

branch="$(git rev-parse --abbrev-ref HEAD)"
[ "$branch" = "HEAD" ] && branch="<branch>"
echo
echo "Created: commit chore(release): v$new  +  tag v$new  (local, unpushed)"
echo "Next (run manually): git push origin $branch && git push origin v$new"
