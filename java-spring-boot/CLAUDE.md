# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

<!-- Template placeholder: `/seed` replaces the next line with <project-name>: <project-description>. In this reference repo, the project is "Agentic Coding Reference — Java Spring Boot implementation". -->
{{PROJECT_NAME}}: {{PROJECT_DESCRIPTION}}

**Documentation:**
- Requirements and goals: [`docs/prd.md`](docs/prd.md)
- Architecture, patterns, guardrails: [`docs/system-design.md`](docs/system-design.md)
- Architectural decisions: [`docs/adr/`](docs/adr/)
- Documentation structure: [`docs/documentation-standards.md`](docs/documentation-standards.md)

## Memory

Durable knowledge lives in this repo — `CLAUDE.md`, `docs/`, `.claude/skills/`, `.claude/agents/`. Do not write to the auto-memory store at `~/.claude/projects/.../memory/`. If a fact is worth remembering across sessions, it is worth committing. If the user asks to "remember" something, edit the right file in the repo instead of saving a memory.

## Agent Usage (Mandatory)

**Rule:** Always use specialized agents for feature development. Do not implement features directly.

For the harness shape — the four nested loops, the slice definition, agent roles, and the handoff contract — see [`docs/agentic-harness.md`](docs/agentic-harness.md).

### Pipeline Coordinator

For new features or when unsure which agent to invoke, use the `pipeline-coordinator` agent. It reads `.scratch/` state and routes to the correct specialist.

For direct invocation when the target agent is known, use the agent selection table in the `pipeline-handoff` skill.

**Skip agents for:** git operations, answering questions about the codebase, running one-off commands.

**Use review agents for:** formal code reviews (code quality, tests, security, documentation). "Review changes" or "review code" triggers the review agents, not direct implementation. Reading code to answer a question does not require agents.

### Tool-call budget

The Claude Code SDK caps assistant messages at 60 tool calls and auto-continues past the cap. Auto-continuation is expensive and lossy:

- Cached content can be re-billed across the continuation boundary, raising token cost.
- The model re-establishes state on resumption, producing redundant reads and oscillation.
- There is no clean checkpoint to retry from if the continuation derails.

**Rule:** When a task plausibly needs more than ~20 tool calls in one turn, dispatch a subagent up front. Prefer the most specific persona that fits: `Explore` for code search beyond a couple of targeted lookups, or a specialist from the `pipeline-handoff` table for recognizable shapes.

`general-purpose` is dispatched only when **both** of these hold:

1. **No named persona fits.** Walk every named persona in the top-of-prompt agent list — `Explore` (code search), `Plan` (implementation planning), `claude-code-guide` (Claude Code / Anthropic API / Agent SDK questions), `feature-implementer` (TDD-driven feature work), the four reviewers (`code-quality-`, `doc-`, `security-`, `test-`), `pipeline-coordinator` (slice routing), `product-requirements-expert` (PRD scoping), `system-design-expert` (architecture). If any one fits the task shape, dispatch *that*. If the same `general-purpose` shape recurs, that is the signal to extract a dedicated agent rather than re-use it.
2. **The Scoping Pre-Check has been written into the dispatch prompt.** Before invoking, estimate the tool calls the task plausibly needs (SDK cap is 60), name one structural checkpoint milestone (e.g., "after the first half of the candidate list is searched," "after the headline finding is verified"), and write both into the prompt so the dispatch carries the same planned-checkpoint discipline the named agents do.

If you do reach the cap, stop and reassess scope. Do not narrate "Truncated at N tool calls. Continuing." and resume — that pattern is the visible symptom of a scoping failure, not a recovery strategy.

Per-role budgets and the partial-artifact contract live in two places. The `toolCallBudget` front-matter on each agent sets the ceiling: 40 for `feature-implementer`, 27 for the four reviewers and the two creator specialists, 14 for `pipeline-coordinator`. The `tdd-workflow` and `review-checklist` skills carry the Scoping Pre-Check and Partial-Artifact Contract sections.

Each creator and verifier dispatch runs a Scoping Pre-Check before its first tool call. The pre-check names a structural checkpoint milestone — end of cycle ⌈N/2⌉ for an N-cycle plan, or "after reviewing ⌈K/2⌉ files" for a K-file review. At that milestone the agent either writes the final artifact (work complete) or appends a partial-artifact record so the next dispatch starts from inspectable progress. Partial-artifact records take one of two shapes: `build-failure` with `partial: true`, or `review-feedback` with `verdict: "blocked"` plus a truncation `tag: "escalate"` finding.

### Skills (Portable Workflow Knowledge)

Pipeline logic lives in skills (`.claude/skills/`), not in agent definitions. All four tools (Claude Code, Copilot CLI, OpenCode, Junie CLI) read skills from this location.

| Skill | Purpose |
|-------|---------|
| `pipeline-handoff` | Routing table, handoff conditions, blocking rules, state files |
| `prd-authoring` | PRD format, boundary rules, requirement template |
| `tdd-workflow` | TDD cycle process, design-check decision tree, document ownership |
| `code-quality-gate` | Build/test/lint requirements, completion criteria |
| `review-checklist` | Feedback tags, issue classification, review output format, review process |
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
| `seed` | Push template into a downstream project (init + upgrade modes) |
| `harvest` | Pull generalizable improvements from a downstream project back into the template |
| `lint-docs` | On-demand documentation validation |
| `ship` | Run quality gate, commit, and push in one step |
| `next` | Reset scratch and recommend the next PRD requirement to tackle |

### Reference

See [`.claude/agents/README.md`](.claude/agents/README.md) for agent roles, model assignments, and scratch directory lifecycle.

## Toolchain

| Tool | Version | Notes |
|------|---------|-------|
| Java | 25 | Toolchain managed via Gradle |
| Gradle | 9.5.0 | Groovy DSL; Spring Boot plugin |
| Spring Boot | 4.0.6 | |

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

All documentation, comments, and PRDs must follow the writing standards in [`docs/documentation-standards.md`](docs/documentation-standards.md#writing-standards).

## Testing Strategy

- **TDD**: Write failing tests before production code. Bug fixes start with a reproducing test.
- **No mocks**: All tests use real value objects and real I/O. No Mockito or mock libraries.
- **Testing principles**: See [`docs/testing-principles.md`](docs/testing-principles.md) for test structure, refactoring patterns, data naming conventions, and the agent decision checklist.
- **Full details**: See [`docs/system-design.md`](docs/system-design.md) for test pyramid, naming conventions, assertion patterns, and test data.

## Scratch Directory

Agents collaborate through `.scratch/` (git-ignored). One feature at a time. Never use system `/tmp` — use `.scratch/tmp/`.

See [`.claude/agents/README.md`](.claude/agents/README.md) for structure, file lifecycle, templates, and rules.

## Quality Gate

Before code review, run `./gradlew build && ./gradlew test && ./gradlew checkJavaFormat`. All checks (build, test, format) must pass before invoking reviewers. The coordinator also runs the autofix audit on `.scratch/handoff.jsonl` and the design-doc paths — see the `code-quality-gate` skill § Autofix Audit Procedure.

## Documentation Updates

When changing the codebase, follow the maintenance rules and prohibited patterns in [`docs/documentation-standards.md`](docs/documentation-standards.md#maintenance-rules).

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
