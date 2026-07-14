# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

{{PROJECT_NAME}}: {{PROJECT_DESCRIPTION}}

**Documentation:**
- Requirements and goals: [`docs/prd.md`](docs/prd.md)
- Architecture, patterns, guardrails: [`docs/system-design.md`](docs/system-design.md)
- Architectural decisions: [`docs/adr/`](docs/adr/)
- Testing principles: [`docs/testing-principles.md`](docs/testing-principles.md)
- Architecture principles: [`docs/architecture-principles.md`](docs/architecture-principles.md)
- Security principles: [`docs/security-principles.md`](docs/security-principles.md)
- Domain vocabulary: [`docs/ubiquitous-language.md`](docs/ubiquitous-language.md)

## This is the generic stack

This project was scaffolded from the harness's **generic stack** — the technology-free template installed when no specific stack (Go, Java/Spring Boot, …) is detected. The pipeline, agents, and skills are complete and stack-agnostic. To make them drive this project's technology, fill in the binding surface — and nothing else:

1. **Bind the lifecycle verbs.** Implement the verb functions in [`scripts/stack.sh`](scripts/stack.sh) — `verb_deps`, `verb_format`, `verb_lint`, `verb_test`, `verb_build`. Until a verb is bound it fails the gate by design.
2. **Specialize the briefs.** Fill the realization sections of `docs/testing-principles.md`, `docs/architecture-principles.md`, `docs/security-principles.md`, and the `docs/prd.md`, `docs/system-design.md`, `docs/ubiquitous-language.md` scaffolds.
3. **Fill the toolchain and layout.** Complete the Toolchain table below and the classification rules in [`scripts/layout.toml`](scripts/layout.toml).

Agents speak only in the verbs above, never in tool names. That is what lets the unchanged pipeline drive any technology.

## Memory

## Agent Usage (Mandatory)

## Toolchain

Fill in the tools, versions, and install steps this stack depends on. The pipeline does not read this table; reviewers and the implementer do.

| Tool | Version | Install |
|------|---------|---------|
| {{FILL: language/runtime}} | {{FILL}} | {{FILL}} |
| {{FILL: build tool}} | {{FILL}} | {{FILL}} |
| {{FILL: linter}} | {{FILL}} | {{FILL}} |

## Build Commands

The quality gate runs through one project API — the lifecycle verbs, never a tool name:

```bash
scripts/gate.sh verify    # run the whole gate: deps, format, lint, test, build
scripts/gate.sh test      # run a single verb
scripts/gate.sh list      # print the canonical verb surface
```

Bind each verb to this stack's real commands by editing the `verb_*` functions in [`scripts/stack.sh`](scripts/stack.sh). `scripts/gate.sh` is harness-owned and replaced on upgrade; do not edit it.

## Architecture

See [`docs/system-design.md`](docs/system-design.md) for module structure, patterns, guardrails, and dependency policy.

**Dependencies:** Minimize external dependencies; each is an attack surface and a maintenance burden. New dependencies require justification. See [`docs/system-design.md#dependency-policy`](docs/system-design.md#dependency-policy) for the approved sources list and prohibited libraries.

## Writing Standards

## Testing Strategy

See [`docs/testing-principles.md`](docs/testing-principles.md) for test structure, the test pyramid, mocking policy, and coverage. Specialize the language-specific conventions there and in this file as the stack is bound.

## Scratch Directory

## Quality Gate

Before code review, run `scripts/gate.sh verify`. Every lifecycle verb must pass, plus the autofix audit (`python3 scripts/handoff.py audit-autofix`) and the handoff-log validation (`python3 scripts/handoff.py validate`), before invoking reviewers — the `code-quality-gate` skill owns the procedure. An unbound verb fails the gate by design — bind it in `scripts/stack.sh`.

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
| `build` | Build system, dependencies |
| `ci` | CI/CD configuration |
| `chore` | Maintenance tasks, tooling |

### Scopes

Use the module or component name. Omit scope for cross-cutting changes: `refactor: rename FooType to BarType`.

### Subject Line Rules

- Imperative mood: "add feature" not "added feature" or "adds feature"
- Lowercase first letter
- No period at end
- Maximum 50 characters
- Complete the sentence: "This commit will ___"

### Breaking Changes

Add `!` after type: `feat(config)!: change poll_interval to a duration string`. Explain the migration in a `BREAKING CHANGE:` footer in the body.
