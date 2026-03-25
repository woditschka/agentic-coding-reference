# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

reference: Agentic coding reference implementation in Go.

**Documentation:**
- Requirements and goals: [`docs/prd.md`](docs/prd.md)
- Architecture, patterns, guardrails: [`docs/system-design.md`](docs/system-design.md)
- Architectural decisions: [`docs/adr/`](docs/adr/)
- Documentation structure: [`docs/documentation.md`](docs/documentation.md)

## Agent Usage (Mandatory)

**Rule:** Always use specialized agents for feature development. Do not implement features directly.

### Pipeline Coordinator

For new features or when unsure which agent to invoke, use the `pipeline-coordinator` agent. It reads `.scratch/` state and routes to the correct specialist.

For direct invocation when the target agent is known, use the agent selection table in the `pipeline-handoff` skill.

**Skip agents for:** git operations, answering questions about the codebase, running one-off commands.

**Use review agents for:** formal code reviews (code quality, tests, security, documentation). "Review changes" or "review code" triggers the review agents, not direct implementation. Reading code to answer a question does not require agents.

### Skills (Portable Workflow Knowledge)

Pipeline logic lives in skills (`.claude/skills/`), not in agent definitions. All three tools (Claude Code, OpenCode, GitHub Copilot) read skills from this location.

| Skill | Purpose |
|-------|---------|
| `pipeline-handoff` | Routing table, handoff conditions, blocking rules, state files |
| `prd-authoring` | PRD format, boundary rules, requirement template |
| `tdd-workflow` | TDD cycle process, design-check decision tree, document ownership |
| `code-quality-gate` | Build/test/lint requirements, completion criteria |
| `review-checklist` | Reviewer output format, feedback tags, review process |
| `code-quality-review` | Go code quality checklist (Google Go Style Guide) |
| `test-review` | Test quality checklist, security testing, dynamic analysis |
| `security-review` | Security checklists, threat model, severity, supply chain |
| `design-validation` | Architectural validation checklist for feature approval |
| `new-feature` | Clear scratch directory, start fresh feature context |
| `adr-template` | ADR format, naming conventions, when to create |
| `audit-agents` | Audit agent config for consistency and cross-tool parity |
| `feature-eval` | Score completed features: tests, reviews, retry count |
| `doc-review` | Documentation review checklist, validation categories, review process |
| `doc-sync` | Synchronize documentation with codebase after implementation |

### Reference

See [`.claude/agents/README.md`](.claude/agents/README.md) for agent roles, model assignments, and scratch directory lifecycle.

## Toolchain

| Tool | Version | Install |
|------|---------|---------|
| Go | 1.26 | System package (supports `range int`, `t.Context()`, `strings.SplitSeq`) |
| golangci-lint | v2.7.2 | Binary install: `curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/HEAD/install.sh \| sh` |

golangci-lint binary lives at `$(go env GOPATH)/bin/golangci-lint`. Do not use `go run` — upstream discourages it (Go version mismatch, untested builds).

## Build Commands

```bash
go build -o bin/reference             # Build binary
go test ./...                         # Run all tests
go test -race ./...                   # Run tests with race detector (requires CGO)
go fmt ./...                          # Format code
```

Or use Make targets:

```bash
make test        # Run all tests
make test-race   # Run tests with race detector (requires gcc)
make lint        # Run golangci-lint
make lint-fix    # Run golangci-lint with auto-fix
make deps-check  # Verify no prohibited dependencies
make ci          # Full CI pipeline: tidy, fmt, vet, lint, deps-check, test, build
```

## Lint Troubleshooting

`make lint-fix` auto-fixes: modernize (range int, any, t.Context), perfsprint, errorlint, godot.

| Lint Rule | Fix |
|-----------|-----|
| revive `unused-parameter` | Use `_` for required-by-interface params (HTTP handlers, etc.) |
| revive `unused-receiver` | Use `*TypeName` (drop receiver name) for methods not using receiver |
| revive `redefines-builtin-id` | Rename `min`/`max` params to `lo`/`hi` (Go 1.21+ builtins) |

## Architecture

See [`docs/system-design.md`](docs/system-design.md) for package structure, patterns, guardrails, and dependency policy.

Errors flow through `run()` to `main()`. Wrap errors with context: `fmt.Errorf("context: %w", err)`.

**Dependencies:** Prefer the standard library. New external dependencies require justification. See [`docs/system-design.md#dependency-policy`](docs/system-design.md#dependency-policy) for the approved sources list and prohibited libraries.

## Writing Standards

All documentation, comments, and PRDs must follow the writing standards in [`docs/documentation.md`](docs/documentation.md#writing-standards).

## Testing Strategy

Follow [Google Go Testing Best Practices](https://google.github.io/styleguide/go/best-practices#test-structure).

- **Table-driven tests**: Use explicit field names and `t.Run()` for subtests
- **Useful failure messages**: `t.Errorf("Func(%v) = %v, want %v", input, got, want)`
- **Struct comparison**: Use `github.com/google/go-cmp/cmp` for diff output
- **Test helpers**: Mark with `t.Helper()`, use `t.Cleanup()` for teardown
- **No assertion libraries**: Use standard comparisons, not testify/assert
- **Mocking policy**: Real implementations > stubs > mocks; mock only at system boundaries
- **Coverage target**: 80% line coverage for `internal/` packages

## Scratch Directory

Agents collaborate through `.scratch/` (git-ignored). One feature at a time. Never use system `/tmp` — use `.scratch/tmp/`.

See [`.claude/agents/README.md`](.claude/agents/README.md) for structure, file lifecycle, templates, and rules.

## Quality Gate

Before code review, run `make ci`. All checks (tidy, fmt, vet, lint, deps-check, test, build) must pass before invoking reviewers. If your project uses containers, also run `make podman-build`.

## Documentation Updates

When changing the codebase, follow the maintenance rules and prohibited patterns in [`docs/documentation.md`](docs/documentation.md#maintenance-rules).

## Commit Convention

Format: `<type>(<scope>): <subject>`

### Types

| Type | Use When |
|------|----------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only (README, comments, ADRs) |
| `style` | Formatting, whitespace, no code change |
| `refactor` | Code change that neither fixes bug nor adds feature |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `build` | Build system, dependencies (go.mod) |
| `ci` | CI/CD configuration |
| `chore` | Maintenance tasks, tooling |

### Scopes

Use the package or component name. Examples:

| Scope | Area |
|-------|------|
| `config` | Configuration loading |
| `server` | HTTP server, endpoints |
| `cli` | Command-line flags |

Omit scope for cross-cutting changes: `refactor: rename FooType to BarType`

### Subject Line Rules

- Imperative mood: "add feature" not "added feature" or "adds feature"
- Lowercase first letter
- No period at end
- Maximum 50 characters
- Complete the sentence: "This commit will ___"

### Examples

```
feat(server): add health check endpoint
fix(config): handle missing config file gracefully
docs: add ADR for database selection
test(server): add handler test cases
refactor(config): extract validation into separate file
chore: update .gitignore for IDE files
build: add go-cmp dependency for test comparisons
```

### Breaking Changes

Add `!` after type for breaking changes:

```
feat(config)!: change poll_interval from seconds to duration string
```

Include `BREAKING CHANGE:` footer in body explaining migration.
