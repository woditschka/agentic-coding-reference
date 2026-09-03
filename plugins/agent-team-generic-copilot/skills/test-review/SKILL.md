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
  - docs/system-design.md
metadata:
  version: "1.0"
  author: team
---

## Project Testing Policy (read from the brief)

The policy values this review enforces are project-owned and live in [`docs/testing-principles.md`](../../../docs/testing-principles.md): the test pyramid ratios (§ Test Pyramid), the coverage target and scope (§ Coverage), the mocking policy (§ Mocking Policy), and the naming school (§ Test Naming). Read them before reviewing and enforce what the brief says, not remembered defaults — the brief is the contract that survives harness upgrades. If the brief contradicts itself or the code under review reveals a gap in it, raise a `clarify` finding against the brief instead of silently substituting your own values.

## Test Placement

The brief's pyramid section is a placement rule, not a ratio to eyeball. The design doc's assignment governs. For every new or changed rule in the diff, find the component `docs/system-design.md` assigns it to, then check where its tests landed:

- [ ] A rule the design doc assigns below the boundary (a domain or service seam) has a unit test at that seam. Covering it only through a framework-booted test (a web-layer slice, a container-backed integration test) is a `blocked` finding, severity per impact, carrying `bar_clause: "tested-as-spec"`. Green coverage does not excuse it.
- [ ] A rule the design doc assigns to the boundary layer — request binding, normalization, response shaping — is correctly exercised at that layer. That its arithmetic could be extracted is never a finding by itself; the pyramid's question applies to rules the design assigns below the boundary.
- [ ] When the design doc assigns a lower seam and the rule landed in a handler, controller, or adapter instead, the cause is placement, not testing. Raise the finding against the test location and name the placement cause; the code-quality-reviewer's Design Placement check owns the landing layer.
- [ ] A production helper widened so a framework test can reach a rule the design assigns to the boundary is a `blocked` finding. The rule is tested where the design places it, never widened for the test.

Judge placement against the components `docs/system-design.md` assigns first and `docs/testing-principles.md` § Test Pyramid second, never a remembered ratio. A brief sentence that reads unconditionally yields to the design doc's assignment; a conflict between the two briefs is a `clarify` to the system-design-expert. Every placement finding cites the assignment it enforces.

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
- [ ] Edge cases are included alongside the nominal case — `python3 scripts/grading.py coverage-map --feature <req_id>` lists the PRD group's numbered cases and the declared tests; cite the map in the finding. A listed case is a prompt to read the tests, never a finding by itself; the finding is a case the slice's requirement owns that no test covers
- [ ] Every Done-when bullet of the slice's requirement has a test whose name states it; the map lists the bullets
- [ ] Test bodies are straight-line — no branches or loops beyond the data-driven mechanism (`tested-as-spec`)
- [ ] Test data names meaningful values by role and marks irrelevant ones; no bare literals (`tested-as-spec`)
- [ ] Comments explain WHY; none narrate what the code or the data already shows (`legible-cold`)
- [ ] New tests reuse the suite's existing factories, helpers, and fixtures before adding new ones. List raw constructions of domain types in the changed test files with the stack's constructor syntax; each outside a factory is an `autofix` finding, severity `fixable`; conventions match the host file, and copied setup is renamed to its actual role (`consistent-with-codebase`)
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

The governing principle is `tested-as-spec`: a test asserts observable outcomes, and a mock interaction is asserted only where the interaction itself is the contract.

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

Run the test verb through the gate (`scripts/gate.sh test`); static analysis rides the gate's lint verb, which the reviewer never re-runs. Where the stack offers stronger dynamic tools, bind them into the relevant verb and require them:

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
