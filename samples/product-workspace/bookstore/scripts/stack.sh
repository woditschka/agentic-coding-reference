#!/usr/bin/env bash
# Project-owned quality-gate verb bindings — THE file to fill in.
#
# Bind each lifecycle verb to the project's technology by implementing its
# function below. The harness-owned dispatcher (scripts/gate.sh) calls these;
# nothing else in the harness names the project's build tools. Run
# `scripts/gate.sh verify` to execute the whole gate, or
# `scripts/gate.sh <verb>` for one verb.
#
# Contract:
#   - One function per verb: verb_deps, verb_format, verb_lint, verb_test, verb_build.
#   - Return 0 on success, non-zero on failure. The dispatcher fails the gate on
#     any non-zero verb.
#   - A verb that genuinely does not apply to this stack: make it an explicit
#     `return 0` no-op with a one-line comment saying why. An unfilled verb is a
#     real gate failure by design; a deliberate no-op is a recorded decision.
#   - Define functions only. Do not run commands at the top level of this file;
#     gate.sh sources it.
#
# Until a verb is implemented it prints "not implemented yet" and fails, so a
# half-bound stack cannot pass the gate.
#
# Example (illustrative — replace with the real commands for this stack):
#   verb_test()  { npm test; }
#   verb_build() { npm run build; }

# The umbrella builds nothing itself: every verb runs in each present member,
# the contract member first so the two consumers read its published stubs.
here="$(cd "$(dirname "$0")/.." && pwd)"
members=("$here/../bookstore-api" "$here/../bookstore-backend" "$here/../bookstore-web")

# Run one command in every present member; fail when a member fails, and fail
# when no member ran at all, so a bare umbrella never passes a verb vacuously.
each_member() {
  local rc=0 ran=0 m
  for m in "${members[@]}"; do
    if [ ! -d "$m/.git" ]; then
      printf 'stack.sh: %s absent, skipped\n' "${m##*/}" >&2
      continue
    fi
    printf '== %s ==\n' "${m##*/}"
    ran=1
    (cd "$m" && "$@") || rc=1
  done
  if [ "$ran" -eq 0 ]; then
    printf 'stack.sh: no member is checked out beside the umbrella\n' >&2
    return 1
  fi
  return $rc
}

# The contract member has no Spring plugin and no formatter; a verb that is
# Spring-only passes it through. Every build runs spotlessApply itself, so the
# format verb asserts, never rewrites.
gradle_if_spring() {
  grep -q "org.springframework.boot" build.gradle || return 0
  ./gradlew -q "$@"
}

verb_deps() { each_member ./gradlew -q dependencies --configuration runtimeClasspath; }
verb_format() { each_member gradle_if_spring spotlessCheck; }
verb_lint() { each_member gradle_if_spring compileTestJava; }
verb_test() { each_member gradle_if_spring test; }
verb_build() {
  (cd "${members[0]}" && ./gradlew -q publishToMavenLocal) || return 1
  each_member gradle_if_spring build
}
