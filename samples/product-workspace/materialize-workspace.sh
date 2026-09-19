#!/usr/bin/env bash
# Place the bookstore's four directories side by side as four git repositories,
# the shape a product workspace runs in: the umbrella beside its members, each
# its own repository with one base commit.
#
#   samples/product-workspace/materialize-workspace.sh <target-dir>
#
# The target must not exist. Afterwards, harness sessions start in
# <target-dir>/bookstore.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
target="${1:-}"
[ -n "$target" ] || { sed -n '2,9p' "$0" >&2; exit 2; }
[ ! -e "$target" ] || { printf 'materialize-workspace: %s exists\n' "$target" >&2; exit 1; }
mkdir -p "$target"
target="$(cd "$target" && pwd)"

for name in bookstore bookstore-api bookstore-backend bookstore-web; do
  # No build output and no scratch state travel; each copy starts clean.
  rsync -a --exclude build --exclude .gradle --exclude .scratch "$here/$name/" "$target/$name/"
  git -C "$target/$name" init -q
  git -C "$target/$name" config user.name "bookstore"
  git -C "$target/$name" config user.email "bookstore@example.invalid"
  git -C "$target/$name" add -A
  git -C "$target/$name" commit -qm "base"
done
printf 'materialize-workspace: four repositories under %s; harness sessions start in %s/bookstore\n' "$target" "$target"
