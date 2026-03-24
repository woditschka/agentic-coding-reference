---
name: code-quality-gate
description: >-
  Build, test, format, and lint requirements that must pass before
  code review. Load when checking implementation completeness or
  running the quality gate.
compatibility:
  - claude-code
  - opencode
  - github-copilot
metadata:
  version: "1.0"
  author: team
---

## Quality Gate

Before invoking reviewers, all checks must pass. Run `make ci` to execute the full pipeline.

### Required Checks

| Check | Command | What It Verifies |
|---|---|---|
| Tidy | `go mod tidy` | Dependencies are clean |
| Format | `go fmt ./...` | Code is formatted |
| Vet | `go vet ./...` | Common mistakes caught |
| Lint | `make lint` | golangci-lint rules pass |
| Deps | `make deps-check` | No prohibited dependencies |
| Test | `go test ./...` | All tests pass |
| Build | `go build -o bin/reference` | Binary compiles |

### Optional Checks

| Check | Command | When Required |
|---|---|---|
| Race detector | `go test -race ./...` | When concurrency is involved (requires gcc) |
| Container build | `make podman-build` | When project uses containers |

## Completion Criteria

A feature is complete when:

- [ ] All TDD cycles finished
- [ ] All tests pass (`go test ./...`)
- [ ] Code formatted (`go fmt ./...`)
- [ ] Lint passes (`make lint`)
- [ ] Dependency policy passes (`make deps-check`)
- [ ] Config example reflects any new/changed config fields (if applicable)
- [ ] All four reviewers approve
- [ ] No pending escalations (or human approved)
