#!/usr/bin/env bash
# Roll the /harness source out to every instance, then prove it green:
#   1. render-agent-mirrors.py  render the per-tool agent mirror bodies
#   2. materialize-samples.sh   re-materialize the samples (extras must be 0)
#   3. package-marketplace.py   re-render the plugins + marketplace.json
#   4. verify-harness.py        the full deterministic battery
# The propagate-and-verify step after a /harness edit — tier 0 of the
# maintainer loop (root CLAUDE.md). Writes the tree; never commits.
#
#   harness/propagate-harness.sh
#
# Named per ADR 2026-07-18 producer-script-naming: -harness marks whole-reference scope.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

# shellcheck source=harness/registry.sh
. "$here/registry.sh"

note "propagate-harness 1/4: render the agent mirror bodies"
"$here/render-agent-mirrors.py"

note "propagate-harness 2/4: re-materialize the samples"
"$here/materialize-samples.sh"

note "propagate-harness 3/4: re-render the marketplace"
python3 "$here/package-marketplace.py"

note "propagate-harness 4/4: run the battery"
python3 "$here/verify-harness.py"

echo
echo "PASS propagate-harness: samples and marketplace match /harness, battery green"
