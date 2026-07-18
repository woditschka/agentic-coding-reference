#!/usr/bin/env bash
# Stack-agnostic: materialize the harness runtime into each target.
#
#   harness/materialize-samples.sh [target-dir ...]
#
# Named per ADR 2026-07-18 producer-script-naming: a tree-builder names its tree.
#
# With no arguments, materializes every monorepo sample in the STACKS roster
# (harness/registry.sh).
# For each target it detects the stack from a build marker — exactly the
# detection /materialize uses — then delegates to the stack-agnostic materialize.py.
# A target with no recognized marker falls back to the generic stack.
# It re-installs the runtime into each sample (committed under the copy channel);
# run it after changing /harness to refresh the samples. Build systems stay free
# of harness wiring.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

# shellcheck source=harness/registry.sh
. "$here/registry.sh"

targets=("$@")
if [ ${#targets[@]} -eq 0 ]; then
  for s in "${STACKS[@]}"; do targets+=("$here/../samples/$s"); done
fi

skipped=0
for target in "${targets[@]}"; do
  if ! resolved="$(cd "$target" 2>/dev/null && pwd)"; then
    echo "materialize-samples: skip $target (not a directory)" >&2
    skipped=1
    continue
  fi
  target="$resolved"
  # Stack detection lives ONLY in registry.py (STACK_MARKERS) — the same code
  # /init and /materialize run; a second shell copy could silently disagree.
  # -P keeps the caller's cwd off sys.path, so an untrusted working directory
  # cannot shadow a stdlib module during the import.
  stack="$(python3 -P -c 'import sys; sys.path.insert(0, sys.argv[1])
from registry import detect_stack
print(detect_stack(sys.argv[2]))' "$here" "$target")"
  if [ "$stack" = "generic" ]; then
    echo "materialize-samples: $target has no stack marker — defaulting to the generic stack (fill scripts/stack.sh)" >&2
  fi
  # --no-verify: the battery runs every sample suite in its own step; the
  # install-time verification is for consumers, not the reference's samples.
  python3 "$here/materialize.py" "$stack" "$target" --no-verify
done

# A skipped target fails the run: a typo'd explicit target must not exit 0 as
# if every requested materialization ran.
exit "$skipped"
