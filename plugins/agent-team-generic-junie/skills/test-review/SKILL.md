---
name: test-review
description: >-
  Test quality checklist, security-testing requirements, and dynamic-analysis
  expectations — language-agnostic, with per-section slots a stack fills in.
  Load when conducting test reviews.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/testing-principles.md
metadata:
  version: "1.0"
  author: team
---

## Project Testing Policy (read from the brief)

The policy values this review enforces are project-owned and live in [`docs/testing-principles.md`](../../../docs/testing-principles.md): the test pyramid ratios (§ Test Pyramid), the coverage target and scope (§ Coverage), the mocking policy (§ Mocking Policy), and the naming school (§ Test Naming). Read them before reviewing and enforce what the brief says, not remembered defaults — the brief is the contract that survives harness upgrades. If the brief contradicts itself or the code under review reveals a gap in it, raise a `clarify` finding against the brief instead of silently substituting your own values.

## Test Quality Checklist

The principles below are language-agnostic. Each **Stack-specific rules** slot is where this project records the test conventions its framework imposes.

### Test Coverage
- [ ] All public behavior has tests
- [ ] All code paths exercised (happy path and error cases)
- [ ] Coverage target from the brief (§ Coverage) met
- [ ] Critical paths have higher coverage

### Test Structure
- [ ] Each test reads as Arrange / Act / Assert with one behavior under test
- [ ] Related cases are data-driven rather than copy-pasted
- [ ] Test names follow the brief's naming school (§ Test Naming) and the `test_name_pattern` floor in `scripts/layout.toml`
- [ ] Edge cases are included alongside the nominal case
- [ ] **Stack-specific rules:** {{FILL: parameterized-test idiom, subtest mechanism}}

### Useful Failure Messages
- [ ] The failure names the operation under test
- [ ] The failure shows actual inputs and got-versus-want
- [ ] Composite values are compared with a structural diff, not field-by-field prose
- [ ] **Stack-specific rules:** {{FILL: assertion/diff helper for this stack}}

### Test Helpers
- [ ] Helpers are marked so a failure points at the calling test, not the helper
- [ ] Teardown is registered to run automatically, not left to manual cleanup
- [ ] Helpers return values for the test to assert on; they do not assert themselves
- [ ] Setup failures abort the test; only behavior failures are soft failures
- [ ] **Stack-specific rules:** {{FILL: helper/teardown mechanism}}

### Mocking Policy

The policy is the brief's (§ Mocking Policy). Apply its boundary rule: mock at system boundaries, use real implementations within them.

| Collaborator | Mock? | Why |
|---|---|---|
| External service / network client | Yes | System boundary |
| Internal types | No | Use the real implementation |
| Clock / time / randomness | Yes | Deterministic testing |

- [ ] **Stack-specific rules:** {{FILL: mocking/faking tools, boundary seams}}

## Security Testing Requirements

### Boundary Testing
- [ ] Negative and empty inputs (negative numbers, empty strings, null/absent)
- [ ] Overflow conditions (maximum values, very long inputs)
- [ ] Type mismatches (wrong types in structured input)
- [ ] Special characters in string inputs
- [ ] Unicode edge cases (null bytes, right-to-left characters)

### Error Path Testing
- [ ] All error paths have test coverage
- [ ] Error messages do not leak sensitive data
- [ ] Timeout behavior is tested
- [ ] Resource cleanup on error is verified

### Concurrency Testing
- [ ] Concurrent access patterns are tested
- [ ] Concurrent-unit cleanup is verified
- [ ] Shared-state operations cannot deadlock or race
- [ ] **Stack-specific rules:** {{FILL: race/concurrency tooling, if any}}

### Input Validation Testing
- [ ] Malformed structured input is rejected
- [ ] Invalid patterns are handled, not crashed on
- [ ] Out-of-range values are rejected
- [ ] Missing required fields are caught

## Dynamic Analysis

Run the test and lint verbs through the gate (`scripts/gate.sh test`, `scripts/gate.sh lint`). Where the stack offers stronger dynamic tools, bind them into the relevant verb and require them:

- [ ] Race / data-race detection, if the stack provides it
- [ ] Static analysis blocks merge on failure (via `scripts/gate.sh lint`)
- [ ] Fuzzing for input-parsing code, if the stack provides it — parsers, pattern compilation, and untrusted-input decoders are the priority targets
- [ ] **Stack-specific rules:** {{FILL: race detector, fuzzer, static analyzer commands}}

## Test Organization

- [ ] Test files follow the location and naming declared in `scripts/layout.toml`
- [ ] Integration tests are separated from unit tests by the stack's mechanism
- [ ] Fixtures live in a dedicated test-data directory with descriptive names (`valid_input`, `malformed_response`, `empty`)
- [ ] **Stack-specific rules:** {{FILL: test-file layout, integration-test separation}}

## Common Issues to Flag

### [AUTOFIX] Issues
- Helper not marked, so failures point at the helper instead of the test
- Sleep-based synchronization instead of a deterministic wait
- Hardcoded values that belong in a data-driven case
- Missing error case in a data-driven test

### [ESCALATE] Issues
- No concurrent-access testing for shared state
- Missing integration test for an external service
- Test coverage below the brief's target (§ Coverage)

### [CLARIFY:security-reviewer] Issues
- Test exposes sensitive-data handling patterns
- Error-message content needs security review
