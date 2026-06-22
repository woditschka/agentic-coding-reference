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

Durable knowledge lives in this repo — `CLAUDE.md`, `docs/`, `.claude/skills/`, `.claude/agents/`. Do not write to the auto-memory store at `~/.claude/projects/.../memory/`. If a fact is worth remembering across sessions, it is worth committing. If the user asks to "remember" something, edit the right file in the repo instead of saving a memory.

## Agent Usage (Mandatory)

**Rule:** Always use specialized agents for feature development. Do not implement features directly.

For the harness shape — the four nested loops, the slice definition, agent roles, and the handoff contract — see [`.claude/skills/pipeline-handoff/agentic-harness.md`](.claude/skills/pipeline-handoff/agentic-harness.md). For the portability rules every harness edit must respect (no ADR/REQ references in harness prose; no runtime-specific numbers in harness text), see [`.claude/skills/pipeline-handoff/agentic-harness.md#harness-invariants`](.claude/skills/pipeline-handoff/agentic-harness.md#harness-invariants).

### Pipeline Coordinator

For new features or when unsure which agent to invoke, use the `pipeline-coordinator` agent. It reads `.scratch/` state and routes to the correct specialist.

For direct invocation when the target agent is known, use the agent selection table in the `pipeline-handoff` skill.

**Skip agents for** work that leaves no pipeline artifact to audit: git operations, one-off commands, answering questions about the codebase.

**Use review agents for:** formal code reviews (code quality, tests, security, documentation). "Review changes" or "review code" triggers the review agents, not direct implementation. Reading code to answer a question does not require agents.

### Surfacing reviewer and grader output

A subagent's final message returns to the orchestrator as a tool result; it is never printed to the terminal. The user sees only what the orchestrator writes. So any agent output meant for the human must be relayed up, not paraphrased away.

Surface each reviewer's verdict the same way: report whether each returned `approved`, `changes_requested`, or `blocked`, and relay the findings behind anything short of approval. Summaries of the pipeline's other internal hops are fine; the reviewer verdicts are the human-facing surface and pass through intact.

The `change-grader` is the same case: it runs as the terminal advisory hop, and its verdict, rationale, and per-facet notes are what the human reads at the merge decision point. Relay the change-grade report verbatim — nothing downstream acts on it, so paraphrase would only erode the one signal it exists to deliver.

### Confirmation Discipline

The system-prompt "executing actions with care" rule says to confirm before risky or hard-to-reverse actions. CLAUDE.md is the legitimate channel for pre-authorizing routine activity. Pipeline work is routine; confirming each hop wastes tokens and wall-clock. Authorization granted for a slice covers every routine hop inside that slice until the user scope-limits. The `pipeline-coordinator` already plays the routing-judge role; second-guessing its clean recommendation by re-asking the user adds latency without adding safety.

**Pause and confirm before:**

- Any action visible outside the local working tree: `git push`, `gh pr create`, `gh pr merge`, `gh issue comment`, Slack/email sends, uploads to third-party services.
- Destructive git: `reset --hard`, `branch -D`, `push --force`, `clean -fd`, history rewrites on shared branches, `--no-verify` / `--no-gpg-sign`.
- A pipeline verdict that pushes the slice past its PRD scope, shortcuts a stage, or escalates a block — the owning skills (`design-validation`, `review-checklist`, `pipeline-handoff`) define these verdicts and when they fire.
- A second consecutive review failure on the same slice.
- Edits to durable instructions (`CLAUDE.md`, `docs/`, `.claude/agents/`, `.claude/skills/`) that are *not* the active slice's declared implementation target.
- The user's previous message contains a question, doubt, or disagreement — answer it before proceeding.

**Do not pause for:**

- The next named agent recommended by `pipeline-coordinator` when its verdict was clean and the user has already authorized the slice.
- Re-dispatching `pipeline-coordinator` to triage a fresh handoff record.
- File reads, greps, builds, `make ci`, `make test`, and other reversible local operations already covered by the system-prompt's "freely take local, reversible actions" clause.
- The exact hop the user just authorized with a forward-motion verb.

**Scope cues from the user.** A forward verb at slice start — "go ahead", "drive the slice", "ship it", "yes", "continue" — authorizes routine hops through the rest of the slice. To scope-limit, the user says "stop after \<stage\>" or "show me before \<action\>", or asks an open question. Slash commands (`/ship`, `/next`) carry the scope defined in their skill prose; do not re-confirm steps the skill itself prescribes.

### Tool-call budget

The Claude Code SDK caps assistant messages at 60 tool calls. A dispatch that reaches the cap **truncates and stops** — it does not auto-continue past the cap. A cap-hit is a length signal, not a scope verdict: recovery continues the same slice. Recovery, cheapest first:

- A bare `continue` resume of the stopped subagent (§ Agent teams and the continue hook) — context intact, no re-derivation. The fast-path when the runtime offers it.
- A fresh re-dispatch from the partial-artifact checkpoint — portable everywhere, but it re-bills the cached prefix and re-establishes state.
- A fresh re-dispatch with no checkpoint — the dispatch re-derives progress from the working tree and the inbound records; the slowest path, avoidable via the Scoping Pre-Check's planned checkpoint.

Re-split is reserved for a slice that spans more than one behavior (caught by the Scoping Pre-Check); non-convergent continuation escalates to re-triage, where re-split is one outcome.

**Rule:** When a task plausibly needs more than ~20 tool calls in one turn, dispatch a subagent up front. Prefer the most specific persona that fits: `Explore` for code search beyond a couple of targeted lookups, or a specialist from the `pipeline-handoff` table for recognizable shapes.

`general-purpose` is dispatched only when **both** of these hold:

1. **No named persona fits.** Walk every named persona in the top-of-prompt agent list — the built-ins (`Explore`, `Plan`, `claude-code-guide`) and the project agents (roles and model assignments: `.claude/agents/README.md`). If any one fits the task shape, dispatch *that*. If the same `general-purpose` shape recurs, that is the signal to extract a dedicated agent rather than re-use it.
2. **The Scoping Pre-Check has been written into the dispatch prompt.** Write the tool-call estimate and one named checkpoint milestone into the prompt before invoking.

If you do reach the cap, the dispatch truncates. Do not narrate "Truncated at N tool calls. Continuing." and carry on as if narration could resume it. Recovery runs through the mechanisms above — bare `continue` resume, else fresh re-dispatch — not through prose. Both continue the same slice.

Per-role budgets and the Scoping Pre-Check / Partial-Artifact Contract are owned elsewhere — do not restate the numbers or record shapes here. Each agent's `toolCallBudget` front-matter sets its own ceiling, and the `tdd-workflow` and `review-checklist` skills define the Scoping Pre-Check and the Partial-Artifact Contract.

### Agent teams and the continue hook

The project turns on Claude Code's experimental agent-teams capability (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `.claude/settings.json`). A truncated dispatch can then be resumed in place with a bare `continue` — the cheap continuation path for the recovery above. A `PreToolUse` hook (`.claude/hooks/sendmessage-continue-only.sh`, registered in the same settings file) constrains that channel: it allows only the literal `continue` and denies everything else, failing closed. The invariant it protects: a resume may not carry new instructions. All new work is a fresh, schema-validated dispatch on `.scratch/handoff.jsonl`, so the resume channel can never bypass the auditable handoff log. Commit the hook and `settings.json` together; a missing hook file fails the guard open.

`SendMessage` is used only for the bare-`continue` resume — never for peer-to-peer coordination (or the agent-teams `TeamCreate`/teammate model) that bypasses `.scratch/handoff.jsonl`. The handoff log is the single inspectable source of truth the pipeline reconstructs from; off-ledger messaging blinds it. The flag is project-scoped: it lives in this repo's `.claude/settings.json` `env` block, not in `~/.claude/settings.json`. Adopting agent teams more broadly is a deliberate decision, not a default.

### Skills (Portable Workflow Knowledge)

Pipeline logic lives in skills (`.claude/skills/`), not in agent definitions. All four tools (Claude Code, Copilot CLI, OpenCode, Junie CLI) read skills from this location.

| Skill | Purpose |
|-------|---------|
| `pipeline-handoff` | Routing table, handoff conditions, blocking rules, state files |
| `prd-authoring` | PRD format, boundary rules, requirement template |
| `tdd-workflow` | TDD cycle process, design-check decision tree, document ownership |
| `code-quality-gate` | Build/test/lint requirements, completion criteria |
| `review-checklist` | Feedback tags, issue classification, review output format, review process, partial-artifact contract |
| `code-quality-review` | Go code quality checklist (Google Go Style Guide) |
| `test-review` | Test quality checklist, security testing, dynamic analysis |
| `security-review` | Security checklists, threat model, severity, supply chain |
| `design-validation` | Architectural validation checklist for feature approval |
| `new-feature` | Clear scratch directory, start fresh feature context |
| `adr-template` | ADR format, naming conventions, when to create |
| `audit-agents` | Audit agent config for consistency, coherence, cross-tool parity |
| `change-grading` | Grade a passing change for how much human attention it deserves before merge (advisory) |
| `document-writing` | Writing standards every author follows; review checklist, validation categories, and prohibited patterns the doc-reviewer enforces |
| `doc-sync` | Synchronize documentation with codebase after implementation |
| `doctor` | Deterministic blocking validation of `docs/` against the harness-project API (roster, sections, slots, channel invariants) |
| `audit-docs` | Audit `docs/` against the high bar — runs the doctor (structure) then the advisory judgment review, each doc individually and cross-document |
| `goland` | Use GoLand MCP tools as a read-only semantic oracle and verifier when connected; native tools handle read/edit/search |
| `goland-doctor` | One-command health check for the GoLand MCP oracle: connected? right project? model loaded? |
| `ship` | Run quality gate, commit, and push in one step |
| `next` | Reset scratch and recommend the next PRD requirement to tackle |

### Reference

See [`.claude/agents/README.md`](.claude/agents/README.md) for agent roles, model assignments, and scratch directory lifecycle.

## Toolchain

| Tool | Version | Install |
|------|---------|---------|
| Go | 1.26 | System package (supports `range int`, `t.Context()`, `strings.SplitSeq`) |
| golangci-lint | v2.12.2 | Binary install: `curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/HEAD/install.sh \| sh` |

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
make ci          # Full CI pipeline: tidy, fmt, vet, lint, deps-check, test, test-scripts, build
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

All documentation, comments, and PRDs must follow the writing standards of the `document-writing` skill ([`.claude/skills/document-writing/documentation-standards.md`](.claude/skills/document-writing/documentation-standards.md)).

## Testing Strategy

Follow [Google Go Testing Best Practices](https://google.github.io/styleguide/go/best-practices#test-structure).

- **Table-driven tests**: Use explicit field names and `t.Run()` for subtests
- **Useful failure messages**: `t.Errorf("Func(%v) = %v, want %v", input, got, want)`
- **Struct comparison**: Use `github.com/google/go-cmp/cmp` for diff output
- **Test helpers**: Mark with `t.Helper()`, use `t.Cleanup()` for teardown
- **No assertion libraries**: Use standard comparisons, not testify/assert
- **Mocking policy**: Real implementations > stubs > mocks; mock only at system boundaries
- **Coverage**: target and scope defined in [`docs/testing-principles.md`](docs/testing-principles.md#coverage)

## Scratch Directory

Agents collaborate through `.scratch/` (git-ignored). One feature at a time. Never use system `/tmp` — use `.scratch/tmp/`.

See [`.claude/agents/README.md`](.claude/agents/README.md) for structure, file lifecycle, templates, and rules.

## Quality Gate

Before code review, run `make ci`. All checks (tidy, fmt, vet, lint, deps-check, test, test-scripts, build) plus the autofix-audit procedure (see the `code-quality-gate` skill) must pass before invoking reviewers. If your project uses containers, also run `make podman-build`.

## Documentation Updates

When changing the codebase, follow the Maintenance Rules in the `doc-sync` skill and the Prohibited Patterns in the `document-writing` skill.

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
docs: add ADR for database selection
build: add go-cmp dependency for test comparisons
```

### Breaking Changes

Add `!` after type: `feat(config)!: change poll_interval from seconds to duration string`. Explain the migration in a `BREAKING CHANGE:` footer in the body.
