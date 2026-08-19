# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

<!-- Template placeholder: `init` replaces the next line with <project-name>: <project-description>. -->
{{PROJECT_NAME}}: {{PROJECT_DESCRIPTION}}

**Documentation:**
- Requirements and goals: [`docs/prd.md`](docs/prd.md)
- Architecture, patterns, guardrails: [`docs/system-design.md`](docs/system-design.md)
- Architectural decisions: [`docs/adr/`](docs/adr/)
- Testing principles: [`docs/testing-principles.md`](docs/testing-principles.md)
- Architecture principles: [`docs/architecture-principles.md`](docs/architecture-principles.md)
- Security principles: [`docs/security-principles.md`](docs/security-principles.md)
- Domain vocabulary: [`docs/ubiquitous-language.md`](docs/ubiquitous-language.md)

## Memory

## Agent Usage (Mandatory)

## Stack-specific skills

Installed for this stack, beyond the harness core catalogued in the Agent Usage chapter:

| Skill | Purpose |
|-------|---------|
| `intellij-idea` | Use IntelliJ MCP tools as a read-only semantic oracle when connected; native tools handle read/edit/search |
| `intellij-idea-doctor` | One-command health check for the IntelliJ MCP oracle: connected? right project? model loaded? |

## Toolchain

| Tool | Version | Notes |
|------|---------|-------|
| Java | 25 | Toolchain managed via Gradle |
| Gradle | 9.7.1 | Groovy DSL; Spring Boot plugin |
| Spring Boot | 4.1.0 | |

## Build Commands

```bash
./gradlew build                       # Build project
./gradlew test                        # Run all tests
./gradlew formatJava                  # Format all Java files (google-java-format)
./gradlew checkJavaFormat             # Check formatting (fails if unformatted)
./gradlew bootRun                     # Run the application
./gradlew bootJar                     # Build fat JAR
```

## Architecture

See [`docs/system-design.md`](docs/system-design.md) for package structure, patterns, guardrails, and implementation details.

## Writing Standards

## Testing Strategy

- **TDD**: Write failing tests before production code. Bug fixes start with a reproducing test.
- **No mocks**: All tests use real value objects and real I/O. No Mockito or mock libraries.
- **Testing principles**: See [`docs/testing-principles.md`](docs/testing-principles.md) for the test pyramid, coverage target, BDD naming conventions, mocking policy, assertion patterns, data naming, and the agent decision checklist.

## Scratch Directory

## Quality Gate

Before code review, run `./gradlew build && ./gradlew test && ./gradlew checkJavaFormat`. All checks wired into `check` must pass: build, test, and format. The design-doc sync (`python3 scripts/grading.py contracts-sync --feature <req_id>`), the autofix audit (`python3 scripts/handoff.py audit-autofix`) and the handoff-log validation (`python3 scripts/handoff.py validate`) must also pass before invoking reviewers — the `code-quality-gate` skill owns the procedure.

## Documentation Updates

## Commit Convention

Format: `<type>(<scope>): <subject>`

### Types

| Type | Use When |
|------|----------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only (PRD, system-design, ADRs, README) |
| `style` | Formatting, whitespace, no code change |
| `refactor` | Code change that neither fixes bug nor adds feature |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `build` | Build system, dependencies (build.gradle) |
| `ci` | CI/CD configuration |
| `chore` | Maintenance tasks, tooling |

### Scopes

Use the package or component name. Omit scope for cross-cutting changes.

### Subject Line Rules

- Imperative mood: "add feature" not "added feature" or "adds feature"
- Lowercase first letter
- No period at end
- Maximum 50 characters
- Complete the sentence: "This commit will ___"

### Examples

```text
feat(parser): handle edge case X
docs: add ADR for strategy decision
build: add dependency X
```

### Breaking Changes

Add `!` after type: `feat(data)!: change data file format from flat list to map`. Explain the migration in a `BREAKING CHANGE:` footer in the body.
