#!/usr/bin/env bash
# Stack-agnostic bootstrap: materialize the harness runtime into each target.
#
#   harness/bootstrap.sh [target-dir ...]
#
# With no arguments, bootstraps the monorepo samples (go, java-spring-boot).
# For each target it detects the stack from a build marker — exactly the
# detection /seed uses — then delegates to the stack-agnostic materialize.sh.
# This is the manifest-channel "install" step: run it once after a fresh
# checkout, before building. The build systems stay free of harness wiring.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

targets=("$@")
if [ ${#targets[@]} -eq 0 ]; then
  targets=("$here/../samples/go" "$here/../samples/java-spring-boot")
fi

for target in "${targets[@]}"; do
  target="$(cd "$target" && pwd)"
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
