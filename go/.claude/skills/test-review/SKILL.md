---
name: test-review
description: >-
  Test quality checklist, security testing requirements, dynamic analysis,
  and test organization conventions for Go applications.
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
| Unit tests | 80% | Single functions in isolation | Fast (<100ms) |
| Module tests | 15% | Package-level behavior | Medium (<1s) |
| Integration tests | 5% | System boundaries | Slow (>1s) |

## Test Quality Checklist

### Test Coverage
- [ ] All public functions have tests
- [ ] All code paths exercised (happy path + error cases)
- [ ] 80% line coverage target met
- [ ] Critical paths have higher coverage

### Table-Driven Tests
- [ ] Use explicit field names in test structs
- [ ] Use `t.Run()` for subtests
- [ ] Test names describe behavior, not implementation
- [ ] Edge cases included in test table

### Useful Failure Messages
- [ ] Include function name in error
- [ ] Include actual inputs
- [ ] Show got vs want: `Func(%v) = %v, want %v`
- [ ] Use `cmp.Diff` for struct comparisons

### Test Helpers
- [ ] Mark helpers with `t.Helper()`
- [ ] Use `t.Cleanup()` for teardown
- [ ] Helpers return values, not assert
- [ ] Setup errors use `t.Fatal`, not `t.Error`

### Mocking Policy
1. **Prefer real implementations** with test data
2. **Mock only at system boundaries** (HTTP, WebSocket, filesystem)
3. **Never mock internal packages**
4. **Hand-write simple mocks**; avoid mock frameworks

| Mock Type | Acceptable | Location |
|-----------|------------|----------|
| HTTP client | Yes | System boundary |
| Internal types | No | Use real implementation |
| Time/Clock | Yes | Deterministic testing |

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
- Test coverage significantly below 80%

### [CLARIFY:security-reviewer] Issues
- Test exposes sensitive data handling patterns
- Error message content needs security review
