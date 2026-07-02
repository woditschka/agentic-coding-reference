#!/usr/bin/env bash
# Roll the /harness source out to every instance, then prove it green:
#   1. bootstrap.sh           re-materialize the samples (extras must be 0)
#   2. package-marketplace.sh re-render the plugins + marketplace.json
#   3. check-sync.sh          the full deterministic battery
# The propagate-and-verify step after a /harness edit. Writes the tree; never
# commits. The /release-prep skill is the interactive front-end.
#
#   harness/release-prep.sh
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

# shellcheck source=harness/helpers.sh
. "$here/helpers.sh"

note "release-prep 1/3: re-materialize the samples"
"$here/bootstrap.sh"

note "release-prep 2/3: re-render the marketplace"
"$here/package-marketplace.sh"

note "release-prep 3/3: run the battery"
"$here/check-sync.sh"

echo
echo "PASS release-prep: samples and marketplace match /harness, battery green"
