#!/usr/bin/env bash
# Stack-agnostic: materialize the harness runtime into each target.
#
#   harness/materialize-samples.sh [target-dir ...]
#
# Named per ADR 2026-07-18 producer-script-naming: a tree-builder names its tree.
#
# With no arguments, materializes every monorepo sample in the STACKS roster
# (harness/registry.py).
# For each target it detects the stack from a build marker — exactly the
# detection /materialize uses — then delegates to the stack-agnostic materialize.py.
# A target with no recognized marker falls back to the generic stack.
# It re-installs the runtime into each sample (committed under the copy channel);
# run it after changing /harness to refresh the samples. Build systems stay free
# of harness wiring.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

targets=("$@")
if [ ${#targets[@]} -eq 0 ]; then
  # The stack roster lives ONLY in registry.py — read it there rather than
  # keeping a bash mirror that needs its own parity gate. -P keeps the
  # caller's cwd off sys.path (same rationale as the detect_stack call below).
  # A read loop, not mapfile: mapfile is a bash 4 builtin and stock macOS ships
  # bash 3.2, where it is silently absent — the roster would come back empty.
  stacks=()
  while IFS= read -r s; do stacks+=("$s"); done < <(python3 -P -c 'import sys; sys.path.insert(0, sys.argv[1])
from registry import STACKS
print("\n".join(STACKS))' "$here")
  # The loop cannot see the subshell's exit status. A failed read yields zero
  # elements; an empty STACKS tuple yields one blank element (the blank line
  # print emits). Both mean no roster — fail loud rather than exit 0 having
  # materialized nothing (or worse, the samples/ parent itself).
  if [ -z "${stacks[*]-}" ]; then
    echo "materialize-samples: could not read STACKS from registry.py" >&2
    exit 1
  fi
  for s in "${stacks[@]}"; do targets+=("$here/../samples/$s"); done
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
