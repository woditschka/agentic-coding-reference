---
name: test-review
description: >-
  Test quality checklist, security testing requirements, and
  test organization conventions for Java/Spring Boot applications.
  Load when conducting test reviews.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## Testing Pyramid

| Level | Proportion | Scope | Speed |
|-------|------------|-------|-------|
| Unit tests | ~80% | Single class in isolation | Fast (<100ms) |
| Integration tests | ~15% | Multi-class with real I/O | Medium (<5s) |
| E2E tests | ~5% | Full pipeline | Slow (<30s) |

## Test Quality Checklist

### Mocking Policy: No Mocks
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

## Test File Organization

### Naming Conventions (BDD)
- Unit test classes: `WhenYou{Action}` (e.g., `WhenYouParseInput`)
- Integration test classes: `{Feature}IT` (e.g., `FullPipelineIT`)
- Test methods: `the{Subject}Should{Outcome}()` (e.g., `theResultShouldContainAllFields()`)
- Test data: `test-data/` directory at project root

## Common Issues to Flag

### [AUTOFIX] Issues
- Missing `@ParameterizedTest` for repetitive cases
- Wrong assertion style (JUnit instead of AssertJ)
- Non-descriptive test name
- Missing edge case in table-driven test

### [ESCALATE] Issues
- No integration test for external service
- Test coverage below 80%
- No concurrent access testing for shared state

### [CLARIFY:security-reviewer] Issues
- Test exposes sensitive data handling patterns
- Error message content needs security review
