# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

<!-- Template placeholder: `/seed` replaces the next line with <project-name>: <project-description>. In this reference repo, the project is "Agentic Coding Reference — Go implementation". -->
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

For the harness shape — the four nested loops, the slice definition, agent roles, and the handoff contract — see [`docs/agentic-harness.md`](docs/agentic-harness.md). For the portability rules every harness edit must respect (no ADR/REQ references in harness prose; no runtime-specific numbers in harness text), see [`docs/agentic-harness.md#harness-invariants`](docs/agentic-harness.md#harness-invariants).

### Pipeline Coordinator

For new features or when unsure which agent to invoke, use the `pipeline-coordinator` agent. It reads `.scratch/` state and routes to the correct specialist.

For direct invocation when the target agent is known, use the agent selection table in the `pipeline-handoff` skill.

**Skip agents for:** git operations, answering questions about the codebase, running one-off commands.

**Use review agents for:** formal code reviews (code quality, tests, security, documentation). "Review changes" or "review code" triggers the review agents, not direct implementation. Reading code to answer a question does not require agents.

### Confirmation Discipline

The system-prompt "executing actions with care" rule says to confirm before risky or hard-to-reverse actions. CLAUDE.md is the legitimate channel for pre-authorizing routine activity. Pipeline work is routine; confirming each hop wastes tokens and wall-clock. Authorization granted for a slice covers every routine hop inside that slice until the user scope-limits. The `pipeline-coordinator` already plays the routing-judge role; second-guessing its clean recommendation by re-asking the user adds latency without adding safety.

**Pause and confirm before:**

- Any action visible outside the local working tree: `git push`, `gh pr create`, `gh pr merge`, `gh issue comment`, Slack/email sends, uploads to third-party services.
- Destructive git: `reset --hard`, `branch -D`, `push --force`, `clean -fd`, history rewrites on shared branches, `--no-verify` / `--no-gpg-sign`.
- A `system-design-expert` verdict of `refactor-first`, `conflicting`, or `foundational` — these branch the slice past the original PRD scope.
- A `pipeline-coordinator` recommendation that *shortcuts* a normal pipeline stage.
- A reviewer verdict of `blocked` carrying an `escalate` tag, or a second consecutive review failure on the same slice.
- Edits to durable instructions (`CLAUDE.md`, `docs/`, `.claude/agents/`, `.claude/skills/`) that are *not* the active slice's declared implementation target.
- The user's previous message contains a question, doubt, or disagreement — answer it before proceeding.

**Do not pause for:**

- The next named agent recommended by `pipeline-coordinator` when its verdict was clean and the user has already authorized the slice.
- Re-dispatching `pipeline-coordinator` to triage a fresh handoff record.
- File reads, greps, builds, `make ci`, `make test`, and other reversible local operations already covered by the system-prompt's "freely take local, reversible actions" clause.
- The exact hop the user just authorized with a forward-motion verb.

**Scope cues from the user.** A forward verb at slice start — "go ahead", "drive the slice", "ship it", "yes", "continue" — authorizes routine hops through the rest of the slice. To scope-limit, the user says "stop after \<stage\>" or "show me before \<action\>", or asks an open question. Slash commands (`/ship`, `/next`) carry the scope defined in their skill prose; do not re-confirm steps the skill itself prescribes.

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
| `seed` | Push template into a downstream project (init + upgrade modes) |
| `harvest` | Pull generalizable improvements from a downstream project back into the template |
| `lint-docs` | On-demand documentation validation |
| `ship` | Run quality gate, commit, and push in one step |
| `next` | Reset scratch and recommend the next PRD requirement to tackle |

### Reference

See [`.claude/agents/README.md`](.claude/agents/README.md) for agent roles, model assignments, and scratch directory lifecycle.

## Toolchain

| Tool | Version | Install |
|------|---------|---------|
| Go | 1.26 | System package (supports `range int`, `t.Context()`, `strings.SplitSeq`) |
| golangci-lint | v2.11.4 | Binary install: `curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/HEAD/install.sh \| sh` |

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

All documentation, comments, and PRDs must follow the writing standards in [`docs/documentation-standards.md`](docs/documentation-standards.md#writing-standards).

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

Before code review, run `make ci`. All checks (tidy, fmt, vet, lint, deps-check, test, build) must pass before invoking reviewers. The coordinator also runs the autofix audit on `.scratch/handoff.jsonl` and the design-doc paths — see the `code-quality-gate` skill § Autofix Audit Procedure. If your project uses containers, also run `make podman-build`.

## Documentation Updates

When changing the codebase, follow the maintenance rules and prohibited patterns in [`docs/documentation-standards.md`](docs/documentation-standards.md#maintenance-rules).

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
