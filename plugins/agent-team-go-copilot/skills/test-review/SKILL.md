---
name: test-review
description: >-
  Test quality checklist, security testing requirements, dynamic analysis,
  and test organization conventions for Go applications.
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

### Test Coverage
- [ ] All public functions have tests
- [ ] All code paths exercised (happy path + error cases)
- [ ] Coverage target from the brief (§ Coverage) met
- [ ] Critical paths have higher coverage

### Table-Driven Tests
- [ ] Use explicit field names in test structs
- [ ] Use `t.Run()` for subtests
- [ ] Test names follow the brief's naming school (§ Test Naming) and the `test_name_pattern` floor in `scripts/layout.toml`
- [ ] Edge cases included in test table — `python3 scripts/grading.py coverage-map --feature <req_id>` lists the PRD group's numbered cases and the declared tests; cite the map in the finding. A listed case is a prompt to read the tests, never a finding by itself; the finding is a case the slice's requirement owns that no test covers
- [ ] Every Done-when bullet of the slice's requirement has a test whose name states it; the map lists the bullets
- [ ] Beyond the table loop, test bodies are straight-line — no per-case `if`/`switch` branching (`tested-as-spec`)
- [ ] Test data names meaningful values by role and marks irrelevant ones; no bare literals (`tested-as-spec`)
- [ ] Comments explain WHY; none narrate what the code or the data already shows (`legible-cold`)
- [ ] Construction goes through the suite's existing factories or builders. List raw composite literals of domain types in the changed test files: `grep -n '[A-Z][A-Za-z]*{' <changed test files>`; each outside a factory is an `autofix` finding, severity `fixable`

### Useful Failure Messages
- [ ] Include function name in error
- [ ] Include actual inputs
- [ ] Show got vs want: `Func(%v) = %v, want %v`
- [ ] Use `cmp.Diff` for struct comparisons

### Test Helpers
- [ ] Mark helpers with `t.Helper()`
- [ ] Use `t.Cleanup()` for teardown
- [ ] New tests reuse the suite's existing helpers, fakes, and fixtures before adding new ones; conventions match the host file, and copied setup is renamed to its actual role (`consistent-with-codebase`)
- [ ] Helpers return values, not assert
- [ ] Setup errors use `t.Fatal`, not `t.Error`

### Mocking Policy

The policy is the brief's (§ Mocking Policy). Go-specific application of its boundary rule:

| Mock Type | Acceptable | Location |
|-----------|------------|----------|
| HTTP client | Yes | System boundary |
| Internal types | No | Use real implementation |
| Time/Clock | Yes | Deterministic testing |

The governing principle is `tested-as-spec`: a test asserts observable outcomes, and a fake's call record is asserted only where the interaction itself is the contract.

## Security Testing Requirements

### Boundary Testing
- [ ] Negative inputs (negative numbers, empty strings, nil)
- [ ] Overflow conditions (max int, very long strings)
- [ ] Type mismatches (wrong JSON types)
- [ ] Special characters in string inputs
- [ ] Unicode edge cases (null bytes, RTL characters)

### Error Path Testing
- [ ] All error returns have test coverage
- [ ] Error messages don't leak sensitive data
- [ ] Timeout behavior tested
- [ ] Resource cleanup on error verified

### Concurrency Testing
- [ ] Tests run with `-race` flag
- [ ] Concurrent access patterns tested
- [ ] Goroutine cleanup verified
- [ ] Channel operations don't deadlock

### Input Validation Testing
- [ ] Malformed JSON/YAML rejected
- [ ] Invalid regex patterns handled
- [ ] Out-of-range values rejected
- [ ] Missing required fields caught

## Dynamic Analysis

### Go Race Detector
```bash
go test -race ./...
```
Detects data races at runtime. Should run on all tests in CI.

### Vet and Static Analysis
```bash
go vet ./...
```
Catches common mistakes. Should block merge on failure.

### Fuzz Testing (Go 1.18+)
For input parsing code, verify fuzz tests exist:

```go
func FuzzParseInput(f *testing.F) {
    f.Add([]byte(`{"id":"test"}`))
    f.Fuzz(func(t *testing.T, data []byte) {
        // Should not panic
        ParseInput(data)
    })
}
```

Fuzz test requirements:
- [ ] JSON parsing functions have fuzz tests
- [ ] Regex compilation has fuzz tests
- [ ] URL parsing has fuzz tests

## Test Organization

### File Naming
- `*_test.go` in same package for unit tests
- `*_integration_test.go` with build tag for integration tests

### Build Tags for Integration Tests
```go
//go:build integration

package mypackage_test
```

### Test Data
- Place fixtures in `testdata/` directory
- Use descriptive names: `valid_input.json`, `malformed_response.json`
- Include edge case fixtures: `empty.json`, `null_fields.json`

## Common Issues to Flag

### [AUTOFIX] Issues
- Missing `t.Helper()` in helper functions
- Sleep-based synchronization (use channels)
- Hardcoded test values that should be in table
- Missing error case in table-driven test

### [ESCALATE] Issues
- No concurrent access testing for shared state
- Missing integration test for external service
- Test coverage below the brief's target (§ Coverage)

### [CLARIFY:security-reviewer] Issues
- Test exposes sensitive data handling patterns
- Error message content needs security review
