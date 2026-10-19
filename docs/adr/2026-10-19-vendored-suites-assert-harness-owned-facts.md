# A Vendored Suite Asserts Harness-Owned Facts, Never a Project's Own

**Status:** Accepted

## Context

Every install verifies the suites it copies: materialize and the marketplace setup run the installed test modules in the consumer's tree and fail the install when one fails. Each stack slice ships two of those suites, `test_config_layout.py` and `test_features_layout.py`, and all three slices read the consumer's `scripts/layout.toml`. The Go and Java Spring Boot suites asserted its content: `src/main/java/` as a production root, `src/test/**` as a test glob, the `gradle` rule on the main tree. A 13-row classification table ran over paths under those roots. The generic suite asserted that the merged `security_surface` probe is empty.

`scripts/layout.toml` is a project-owned file whose header says to edit it to match the project's layout. A Spring Boot consumer with a multi-module tree moves its roots and rules under the module, `app/src/main/java/` and `app/src/main/java/**`, as the file's named-layout comment describes. In a copy of the Java sample with that edit, the two suites ran 14 tests and failed 21 times, so every later materialize of that project failed verification. A Go project without a `pkg/` tree fails the same way. A generic project that declares a `security_surface`, which its skeleton's own comment invites, fails the probe assertion.

The runtime-package-layout decision placed these suites per stack because they were "entangled with a stack's real `layout.toml`". The entanglement was with the sample's copy, which equals the stack's init skeleton. A consumer's copy is a different file. Those suites were also the one place where the sample's layout was held to the skeleton: no step compared the two files.

## Options Considered

1. **Skip the classification table when the project's layout differs from the skeleton.** Rejected: a test that skips when it would fail asserts nothing in the tree it ships to. The skip condition restates the skeleton anyway.
2. **Let the project own the two suites.** Rejected: the runtime is replaced whole on every upgrade, and a project-owned test under the harness-owned tree is the orphan case materialize prunes.
3. **Restate the skeleton as a record inside the vendored suite and gate the restatement on the producer side.** Rejected: the runtime-package-layout decision retired the last byte-identity gate over a hand-owned parallel with the rule that such a parallel is deleted, not guarded. A vendored table that no longer reads the consumer's file tells the consumer nothing about their tree.
4. **Pin the skeleton on the producer side over the skeleton file itself; leave the vendored suites with the facts the harness owns** (chosen).

## Decision

**A vendored suite asserts only what the harness owns.** In a stack slice that is two things: the engine's module strategies, exercised on synthetic layouts, and the stack's `layout-defaults.toml`. The consumer's `scripts/layout.toml` is asserted only through the loader: it loads, its `[review]` and `[conventions]` tables validate, and its roster starts at the four-reviewer floor. The three slices hold one rule.

**The skeleton is classified where it lives.** `harness/tests/test_stack_layouts.py` loads each stack's `harness/init/stacks/<stack>/scripts/layout.toml` through the runtime's own loader and classifies a representative tree against it. A glob deleted from a skeleton fails battery step 6. Nothing restates the skeleton.

**The sample's layout is held to its skeleton byte for byte.** `scripts/layout.toml` joins the verbatim project-owned files the faithfulness step compares between each stack sample and its init skeleton.

**The config suite reads the defaults file directly.** `test_config_layout.py` loads `layout-defaults.toml` through `load_stack_defaults` and validates it as a layout with no project tables. A project's own `security_surface` or `[conventions]` override never reaches the assertion.

## Consequences

- A consumer may reshape its layout; the install stays green. The doctor validates the layout's shape, and the classification the layout produces is observed through the change grader's records, not through a shipped test.
- The vendored `test_features_layout.py` shrinks to the module-strategy pins. The classification table moves once, to the producer suite, and gains the generic skeleton.
- Sample-versus-skeleton drift, previously observable only through the removed assertions, is a battery failure in its own right.
- The suite layout rows in the testing principles, the change-grading skill, and the harvest skill follow this decision.

## Implementation

`harness/stacks/<stack>/scripts/tests/grading/` carries the rewritten suites for all three stacks; `harness/tests/test_stack_layouts.py` carries the skeleton table; `harness/verify_harness/checks/sync.py` carries the verbatim set.

## References

- [2026-07-17 runtime package layout](2026-07-17-runtime-package-layout.md) — placed the layout suites per stack and retired the last hand-owned parallel; this ADR narrows what the suites may assert and follows that rule.
- [2026-08-10 a prod-test pair is one module](2026-08-10-a-prod-test-pair-is-one-module.md) — the module-root ids the Java table pins.
- [2026-09-07 security review follows the surface](2026-09-07-security-review-follows-the-surface.md) — the stack-defaults file the config suite reads directly.
