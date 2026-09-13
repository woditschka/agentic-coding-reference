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

_unimplemented() {
  # $1 = verb name. Prints the standard message and fails honestly.
  printf 'stack.sh: verb %q not implemented yet — edit scripts/stack.sh\n' "$1" >&2
  return 1
}

# Dependency hygiene: lockfile/manifest tidy, no prohibited or unused deps
# (check mode, do not rewrite — read-only reviewers run this verb).
verb_deps() { _unimplemented deps; }

# Formatting: assert the tree is formatted (check mode, do not rewrite).
verb_format() { _unimplemented format; }

# Lint and static analysis: run the project's linters and static checks.
verb_lint() { _unimplemented lint; }

# Tests: run the full test suite the gate requires green.
verb_test() { _unimplemented test; }

# Build: compile or assemble the project's artifact.
verb_build() { _unimplemented build; }
