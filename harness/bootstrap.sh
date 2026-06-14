#!/usr/bin/env bash
# Stack-agnostic bootstrap: materialize the harness runtime into each target.
#
#   harness/bootstrap.sh [target-dir ...]
#
# With no arguments, bootstraps the monorepo samples (go, java-spring-boot).
# For each target it detects the stack from a build marker — exactly the
# detection /materialize uses — then delegates to the stack-agnostic materialize.sh.
# It re-installs the runtime into each sample (committed under the copy channel);
# run it after changing /harness to refresh the samples. Build systems stay free
# of harness wiring.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

targets=("$@")
if [ ${#targets[@]} -eq 0 ]; then
  targets=("$here/../samples/go" "$here/../samples/java-spring-boot")
fi

for target in "${targets[@]}"; do
  if ! resolved="$(cd "$target" 2>/dev/null && pwd)"; then
    echo "bootstrap: skip $target (not a directory)" >&2
    continue
  fi
  target="$resolved"
  if [ -f "$target/go.mod" ]; then
    stack=go
  elif [ -f "$target/build.gradle" ] || [ -f "$target/build.gradle.kts" ] || [ -f "$target/pom.xml" ]; then
    stack=java-spring-boot
  else
    echo "bootstrap: skip $target (no stack marker)" >&2
    continue
  fi
  "$here/materialize.sh" "$stack" "$target"
done
