---
name: test-review
description: >-
  Test quality checklist, security testing requirements, dynamic analysis,
  and test organization conventions for Java/Spring Boot applications.
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

### Mocking Policy
The policy is the brief's (§ Mocking Policy) — enforce what it declares, not remembered defaults. The governing principle is `tested-as-spec`: a test asserts observable outcomes, and an interaction is asserted only where the interaction itself is the contract (events, notifications). Java-specific application:
- [ ] Mock/stub library usage (Mockito, EasyMock) stays within what the brief permits
- [ ] Value objects and records stay real unless the brief permits mocking them
- [ ] Integration tests use real I/O where the brief requires it (test fixtures or `@TempDir`)
- [ ] No `verify(...)` restating an outcome a behavioral assertion already covers
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
- [ ] New tests follow the host file's conventions (`consistent-with-codebase`): stubbing idiom (`given(...)` vs `when(...)`), helpers, assertion patterns; copied setup renamed to its actual role

### Test Data Naming (see testing-principles.md, Three-Tier Convention)
- [ ] Meaningful values named by role (`QUANTITY`, `DISCOUNT_RATE`) — Tier 1
- [ ] Irrelevant values use `SOME_`/`ANY_` prefix or anonymous factories (`createAnX()`) — Tier 2
- [ ] No mystery literals (bare `42`, `"hello@x.com"`) — Tier 3 eliminated
- [ ] Expected values derived from inputs, not hard-coded magic numbers
- [ ] Object construction wrapped in factory methods, not raw constructor calls — reuse the suite's existing factories before adding new ones. List them: `grep -n 'new [A-Z][A-Za-z]*(' <changed test files>`; each raw construction of a domain type outside a factory is an `autofix` finding, severity `fixable`

### Edge Case Coverage
- [ ] All documented edge cases from prd.md have dedicated test cases — `python3 scripts/grading.py coverage-map --feature <req_id>` lists the PRD group's numbered cases and the declared tests; cite the map in the finding. A listed case is a prompt to read the tests, never a finding by itself; the finding is a case the slice's requirement owns that no test covers
- [ ] Every Done-when bullet of the slice's requirement has a test whose name states it; the map lists the bullets
- [ ] Edge case tests use actual examples (not invented data)
- [ ] `@ParameterizedTest` with `@CsvSource` covers all edge cases
- [ ] Integration test exercises all inputs without exceptions

### Test Coverage
- [ ] All public methods have tests
- [ ] All code paths exercised (happy path + error cases)
- [ ] Coverage target from the brief (§ Coverage) met
- [ ] Critical paths have higher coverage
- [ ] Error handling scenarios from system-design.md have test coverage

### Parameterized Tests
- [ ] `@ParameterizedTest` used for repetitive test cases (not copy-paste tests)
- [ ] `@CsvSource` entries carry a comment only where the covered case is not evident from the values — comments explain WHY, not WHAT (`legible-cold`)
- [ ] Test method name describes the behavior being verified
- [ ] Each parameter combination is independently meaningful

### State and Idempotency Testing
- [ ] First run creates output
- [ ] Second run with no changes produces identical output
- [ ] New items are detected and processed
- [ ] Changed items are detected
- [ ] Removed items are detected and removed from state
- [ ] State file round-trips correctly through serialization
- [ ] No partial writes leave state broken: writes are atomic (temp-then-rename or equivalent)
- [ ] Older state files still load, or a migration path is defined (schema backward-compatibility)

## Security Testing Requirements

### Boundary Testing
- [ ] Empty input
- [ ] Single item
- [ ] Missing data/state file (first run)
- [ ] Corrupted data/state file (invalid content)
- [ ] Empty data/state file (zero bytes)
- [ ] Overflow conditions (max int, very long strings)
- [ ] Type mismatches (wrong JSON types)
- [ ] Special characters in input
- [ ] Unicode edge cases (null bytes, RTL characters)

### Error Path Testing
- [ ] All error scenarios from system-design.md have test coverage
- [ ] Error messages don't leak sensitive data
- [ ] Corrupted data triggers recovery (not crash)
- [ ] Missing configuration produces non-zero exit code
- [ ] I/O errors are caught and logged
- [ ] Unparseable input produces warning, not exception

### Concurrency Testing
- [ ] Concurrent access patterns tested with real threads (`ExecutorService`, `CompletableFuture`)
- [ ] Race windows lined up deterministically (`CountDownLatch`), not with `Thread.sleep`
- [ ] Executors and threads shut down in cleanup; no leaked threads between tests
- [ ] Blocking operations carry timeouts (`future.get(timeout)`, `awaitTermination`) so a deadlock fails fast

### Input Validation Testing
- [ ] Malformed JSON/YAML rejected (parse errors handled, not propagated raw)
- [ ] Invalid regex patterns handled, not crashed on
- [ ] Out-of-range values rejected at the boundary
- [ ] Missing required fields caught

## Dynamic Analysis

### Build-Gate Analysis
```bash
./gradlew test
```
The test task is the reviewer's dynamic hook (Reviewer Conduct's permitted variants). The bound static checks (Spotless format among them) ride the quality gate: `./gradlew build` runs `check`, so a failure blocks merge without the reviewer re-running it.

### Concurrency
The JVM ships no race detector. Confidence comes from tests: repeated racy scenarios, `CountDownLatch`-choreographed interleavings, and review attention on shared mutable state. Escalate untested shared state; never assume safety.

### Fuzz and Adversarial Testing
For input-parsing code, adversarial coverage is required. Bind a JVM fuzzer where the build declares the Jazzer dependency (`com.code-intelligence:jazzer-junit`); the floor is `@ParameterizedTest` over adversarial fixtures (malformed, truncated, oversized input).

- [ ] JSON deserialization paths have adversarial-input tests
- [ ] Regex compilation has adversarial-input tests
- [ ] Any decoder of untrusted input has adversarial-input tests

## Test Organization

### Naming Conventions
The naming school is the brief's (§ Test Naming); the machine floor is `test_name_pattern` in `scripts/layout.toml`. Test data lives in `test-data/` at the project root.

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
