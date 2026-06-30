---
name: test-review
description: >-
  Test quality checklist, security testing requirements, and
  test organization conventions for Java/Spring Boot applications.
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

The policy values this review enforces are project-owned and live in [`docs/testing-principles.md`](../../../docs/testing-principles.md): the test pyramid ratios (§ Test Pyramid), the coverage target and scope (§ Coverage), the mocking policy (§ Mocking Policy), and the BDD naming school (§ Test Naming). Read them before reviewing and enforce what the brief says, not remembered defaults — the brief is the contract that survives harness upgrades. If the brief contradicts itself or the code under review reveals a gap in it, raise a `clarify` finding against the brief instead of silently substituting your own values.

## Test Quality Checklist

### Mocking Policy
Per the brief (§ Mocking Policy), this project allows no mock libraries at all:
- [ ] No Mockito, EasyMock, or any mock/stub library usage
- [ ] Real value objects used in all tests (no mocked records)
- [ ] Real I/O used in integration tests (via test fixtures or `@TempDir`)
- [ ] If a test requires complex setup, that signals the production code needs a simpler interface

### AssertJ Assertions
- [ ] Fluent AssertJ used (`assertThat(...).isEqualTo(...)`)
- [ ] No JUnit `assertEquals` / `assertTrue` (use AssertJ equivalents)
- [ ] Chained assertions on same object preferred over separate `assertThat()` calls
- [ ] Collection assertions use `containsExactly`, `containsExactlyInAnyOrder`, `hasSize`
- [ ] String assertions use `startsWith`, `contains`, `matches` where appropriate
- [ ] Custom failure messages added for non-obvious assertions

### Test Structure (see testing-principles.md)
- [ ] Four-phase structure (Arrange/Act/Assert/Cleanup) separated by blank lines
- [ ] No phase comments (`// Arrange`), `.as()` messages restating the obvious, or narration comments
- [ ] One logical assertion per test (multiple `assertThat` calls on same result are fine)
- [ ] Tests are straight-line code: no `if/else`, `switch`, or loops in test bodies
- [ ] Test method names describe behavior (`theResultShouldContainNewItems`, not `test1`)
- [ ] No test logic in production code (`@VisibleForTesting` is a code smell)
- [ ] Tests are independent (no shared mutable state, no ordering dependencies)

### Test Data Naming (see testing-principles.md, Three-Tier Convention)
- [ ] Meaningful values named by role (`QUANTITY`, `DISCOUNT_RATE`) — Tier 1
- [ ] Irrelevant values use `SOME_`/`ANY_` prefix or anonymous factories (`createAnX()`) — Tier 2
- [ ] No mystery literals (bare `42`, `"hello@x.com"`) — Tier 3 eliminated
- [ ] Expected values derived from inputs, not hard-coded magic numbers
- [ ] Object construction wrapped in factory methods, not raw constructor calls

### Edge Case Coverage
- [ ] All documented edge cases from prd.md have dedicated test cases
- [ ] Edge case tests use actual examples (not invented data)
- [ ] `@ParameterizedTest` with `@CsvSource` covers all edge cases
- [ ] Edge case numbers in test comments match prd.md numbering
- [ ] Integration test exercises all inputs without exceptions

### Test Coverage
- [ ] All public methods have tests
- [ ] All code paths exercised (happy path + error cases)
- [ ] Coverage target from the brief (§ Coverage) met
- [ ] Critical paths have higher coverage
- [ ] Error handling scenarios from system-design.md have test coverage

### Parameterized Tests
- [ ] `@ParameterizedTest` used for repetitive test cases (not copy-paste tests)
- [ ] `@CsvSource` entries have comments explaining which case they cover
- [ ] Test method name describes the behavior being verified
- [ ] Each parameter combination is independently meaningful

### Boundary Testing
- [ ] Empty input
- [ ] Single item
- [ ] Missing data/state file (first run)
- [ ] Corrupted data/state file (invalid content)
- [ ] Empty data/state file (zero bytes)
- [ ] Special characters in input
- [ ] Unicode edge cases (null bytes, RTL characters)

### Error Path Testing
- [ ] All error scenarios from system-design.md have test coverage
- [ ] Corrupted data triggers recovery (not crash)
- [ ] Missing configuration produces non-zero exit code
- [ ] I/O errors are caught and logged
- [ ] Unparseable input produces warning, not exception

### State and Idempotency Testing
- [ ] First run creates output
- [ ] Second run with no changes produces identical output
- [ ] New items are detected and processed
- [ ] Changed items are detected
- [ ] Removed items are detected and removed from state
- [ ] State file round-trips correctly through serialization
- [ ] No partial writes leave state broken: writes are atomic (temp-then-rename or equivalent)
- [ ] Older state files still load, or a migration path is defined (schema backward-compatibility)

## Test File Organization

### Naming Conventions
The naming school is the brief's (§ Test Naming: `WhenYou{Action}` classes, `the{Subject}Should{Outcome}()` methods); the machine floor is `test_name_pattern` in `scripts/layout.toml`. Test data lives in `test-data/` at the project root.

## Common Issues to Flag

### [AUTOFIX] Issues
- Missing `@ParameterizedTest` for repetitive cases
- Wrong assertion style (JUnit instead of AssertJ)
- Non-descriptive test name
- Missing edge case in table-driven test

### [ESCALATE] Issues
- No integration test for external service
- Test coverage below the brief's target (§ Coverage)
- No concurrent access testing for shared state

### [CLARIFY:security-reviewer] Issues
- Test exposes sensitive data handling patterns
- Error message content needs security review
