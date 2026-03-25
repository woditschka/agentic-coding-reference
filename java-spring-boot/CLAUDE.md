# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Agentic coding reference implementation in Java Spring Boot.

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
| `code-quality-review` | Java code quality checklist |
| `test-review` | Test quality checklist, security testing |
| `security-review` | Security checklists, threat model, severity, dependencies |
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

| Tool | Version | Notes |
|------|---------|-------|
| Java | 25 | Toolchain managed via Gradle |
| Gradle | 9.4.1 | Groovy DSL; Spring Boot plugin |
| Spring Boot | 4.0.4 | |

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

All documentation, comments, and PRDs must follow the writing standards in [`docs/documentation.md`](docs/documentation.md#writing-standards).

## Testing Strategy

- **TDD**: Write failing tests before production code. Bug fixes start with a reproducing test.
- **No mocks**: All tests use real value objects and real I/O. No Mockito or mock libraries.
- **Test philosophy**: See [`docs/test-philosophy.md`](docs/test-philosophy.md) for test structure, refactoring patterns, data naming conventions, and the agent decision checklist.
- **Full details**: See [`docs/system-design.md`](docs/system-design.md) for test pyramid, naming conventions, assertion patterns, and test data.

## Scratch Directory

Agents collaborate through `.scratch/` (git-ignored). One feature at a time. Never use system `/tmp` — use `.scratch/tmp/`.

See [`.claude/agents/README.md`](.claude/agents/README.md) for structure, file lifecycle, templates, and rules.

## Quality Gate

Before code review, run `./gradlew build && ./gradlew test && ./gradlew checkJavaFormat`. All checks (build, test, format) must pass before invoking reviewers.

## Documentation Updates

When changing the codebase, follow the maintenance rules and prohibited patterns in [`docs/documentation.md`](docs/documentation.md#maintenance-rules).

## Commit Convention

Format: `<type>(<scope>): <subject>`

### Types

| Type | Use When |
|------|----------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only (PRD, system-design, ADRs) |
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
fix(data): detect removed files when state exists
docs: add ADR for strategy decision
test(parser): add parameterized tests for edge cases
refactor(config): extract properties to record
chore: update .gitignore for IDE files
build: add dependency X
```

### Breaking Changes

Add `!` after type for breaking changes:

```text
feat(data)!: change data file format from flat list to map
```

Include `BREAKING CHANGE:` footer in body explaining migration.
