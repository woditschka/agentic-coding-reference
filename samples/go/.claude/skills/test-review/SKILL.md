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

The brief's pyramid section is a placement rule, not a ratio to eyeball. For every new or changed rule in the diff, ask its question — could this have been exercised at a lower level? — and check where the tests landed:

- [ ] A rule that is pure logic (a clamp, a validation, a computation with no framework dependency) has a unit test at the seam that holds it. Covering it only through a framework-booted test (a web-layer slice, a container-backed integration test) when a unit seam exists is a `blocked` finding, severity per impact, carrying `bar_clause: "tested-as-spec"`. Green coverage does not excuse it.
- [ ] A rule the design doc assigns to the web layer — request normalization, binding, response shaping — is correctly exercised at the web level. The check applies only where a lower seam exists or the design doc assigns one.
- [ ] When no unit seam exists because the rule landed in a handler, controller, or adapter, the cause is placement, not testing. Raise the finding against the test location and name the placement cause; the code-quality-reviewer's Design Placement check owns the landing layer.
- [ ] A production helper widened so a framework test can reach the rule (package-private, exported-for-tests) is the same placement smell seen from the test side: a `blocked` finding naming the seam the design doc assigns.

Judge placement against `docs/testing-principles.md` § Test Pyramid and the components `docs/system-design.md` assigns, never a remembered ratio. Every placement finding cites the brief section it enforces.

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
- [ ] Edge cases included in test table
- [ ] Beyond the table loop, test bodies are straight-line — no per-case `if`/`switch` branching (`tested-as-spec`)
- [ ] Test data names meaningful values by role and marks irrelevant ones; no bare literals (`tested-as-spec`)
- [ ] Comments explain WHY; none narrate what the code or the data already shows (`legible-cold`)

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
