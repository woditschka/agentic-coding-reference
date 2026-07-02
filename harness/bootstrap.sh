#!/usr/bin/env bash
# Stack-agnostic bootstrap: materialize the harness runtime into each target.
#
#   harness/bootstrap.sh [target-dir ...]
#
# With no arguments, bootstraps every monorepo sample in the STACKS roster
# (harness/helpers.sh).
# For each target it detects the stack from a build marker — exactly the
# detection /materialize uses — then delegates to the stack-agnostic materialize.sh.
# A target with no recognized marker falls back to the generic stack.
# It re-installs the runtime into each sample (committed under the copy channel);
# run it after changing /harness to refresh the samples. Build systems stay free
# of harness wiring.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

# shellcheck source=harness/helpers.sh
. "$here/helpers.sh"

targets=("$@")
if [ ${#targets[@]} -eq 0 ]; then
  for s in "${STACKS[@]}"; do targets+=("$here/../samples/$s"); done
fi

for target in "${targets[@]}"; do
  if ! resolved="$(cd "$target" 2>/dev/null && pwd)"; then
    echo "bootstrap: skip $target (not a directory)" >&2
    continue
  fi
  target="$resolved"
  stack="$(detect_stack "$target")"
  if [ "$stack" = "generic" ]; then
    echo "bootstrap: $target has no stack marker — defaulting to the generic stack (fill scripts/stack.sh)" >&2
  fi
  "$here/materialize.sh" "$stack" "$target"
done
