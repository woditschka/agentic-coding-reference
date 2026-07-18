#!/usr/bin/env bash
# Roll the /harness source out to every instance, then prove it green:
#   1. refresh-agent-bodies.py render the per-tool agent mirror bodies
#   2. bootstrap.sh           re-materialize the samples (extras must be 0)
#   3. package-marketplace.py re-render the plugins + marketplace.json
#   4. verify-harness.py          the full deterministic battery
# The propagate-and-verify step after a /harness edit — tier 0 of the
# maintainer loop (root CLAUDE.md). Writes the tree; never commits.
#
#   harness/release-prep.sh
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

# shellcheck source=harness/helpers.sh
. "$here/helpers.sh"

note "release-prep 1/4: render the agent mirror bodies"
"$here/refresh-agent-bodies.py"

note "release-prep 2/4: re-materialize the samples"
"$here/bootstrap.sh"

note "release-prep 3/4: re-render the marketplace"
python3 "$here/package-marketplace.py"

note "release-prep 4/4: run the battery"
python3 "$here/verify-harness.py"

echo
echo "PASS release-prep: samples and marketplace match /harness, battery green"
