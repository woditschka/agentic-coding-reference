<!-- harness: 2026-06-27 -->
# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Generic Stack Template: Materialized starting point for the technology-free generic stack — copy it, bind the verbs in scripts/stack.sh, and fill the briefs.

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

### Orchestrator economy

You run on the most expensive context in the pipeline. Your output is cache-written once, then cache-read on every later turn — so prose you emit is paid for many times over. Keep your turns thin.

- **Relay, don't restate.** When the section above has you relay a reviewer's verdict and findings, or the change-grade report verbatim, do not summarize it first. The relay already carries it; a preceding paraphrase emits the same content twice.
- **One line per hop — unless the hop has something to surface.** A pass, a no-op, or a routing hop is one sentence: name the dispatch and its reason, take it, report the result. A reviewer that returns `changes_requested` or `blocked` is not a one-liner — relay its findings in full, and pass the change-grade report verbatim. Trimming covers connective prose, never the content a hop exists to deliver.
- **Drop the filler.** Cut preambles ("Now let me…") and recaps of state already visible in the transcript.

This trims connective prose only. The human-facing surface stays in full: every non-`approved` verdict with its findings, the verbatim change-grade relay, the implementation plan, decision rationale, and `AskUserQuestion` gates.

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
- File reads, greps, builds, the project's quality gate, and other reversible local operations already covered by the system-prompt's "freely take local, reversible actions" clause.
- The exact hop the user just authorized with a forward-motion verb.

**Scope cues from the user.** A forward verb at slice start — "go ahead", "drive the slice", "ship it", "yes", "continue" — authorizes routine hops through the rest of the slice. To scope-limit, the user says "stop after \<stage\>" or "show me before \<action\>", or asks an open question. Slash commands (`/ship`, `/next`) carry the scope defined in their skill prose; do not re-confirm steps the skill itself prescribes.

### Tool-call budget

The Claude Code SDK caps assistant messages at a fixed number of tool calls per dispatch. A dispatch that reaches the cap **truncates and stops** — it does not auto-continue past the cap. A cap-hit is a length signal, not a scope verdict: recovery continues the same slice. Recovery, cheapest first:

- A bare `continue` resume of the stopped subagent (§ Agent teams and the continue hook) — context intact, no re-derivation. The fast-path when the runtime offers it.
- A fresh re-dispatch from the partial-artifact checkpoint — portable everywhere, but it re-bills the cached prefix and re-establishes state.
- A fresh re-dispatch with no checkpoint — the dispatch re-derives progress from the working tree and the inbound records; the slowest path, avoidable via the Scoping Pre-Check's planned checkpoint.

Re-split is reserved for a slice that spans more than one behavior (caught by the Scoping Pre-Check); non-convergent continuation escalates to re-triage, where re-split is one outcome.

**Rule:** When a task plausibly needs many tool calls in one turn, dispatch a subagent up front. Prefer the most specific persona that fits: `Explore` for code search beyond a couple of targeted lookups, or a specialist from the `pipeline-handoff` table for recognizable shapes.

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
| `code-quality-gate` | Lifecycle verbs, the quality gate, completion criteria |
| `review-checklist` | Feedback tags, issue classification, review output format, review process, partial-artifact contract |
| `code-quality-review` | Code quality checklist (specialize per stack) |
| `test-review` | Test quality checklist, security testing, dynamic analysis |
| `security-review` | Security checklists, threat model, severity, dependency verification |
| `design-validation` | Architectural validation checklist for feature approval |
| `new-feature` | Clear scratch directory, start fresh feature context |
| `adr-template` | ADR format, naming conventions, when to create |
| `audit-agents` | Audit agent config for consistency, coherence, cross-tool parity |
| `change-grading` | Grade a passing change for how much human attention it deserves before merge (advisory) |
| `document-writing` | Writing standards every author follows; review checklist, validation categories, and prohibited patterns the doc-reviewer enforces |
| `doc-sync` | Synchronize documentation with codebase after implementation |
| `doctor` | Deterministic blocking validation of `docs/` against the harness-project API (roster, sections, slots, channel invariants) |
| `audit-docs` | Audit `docs/` against the high bar — runs the doctor (structure) then the advisory judgment review, each doc individually and cross-document |
| `ship` | Run quality gate, commit, and push in one step |
| `next` | Reset scratch and recommend the next PRD requirement to tackle |

This table is the stack-agnostic core. When a stack ships its own skills (for example an IDE oracle), they are catalogued in the **Stack-specific skills** chapter below, and are always discoverable in `.claude/skills/`.

### Reference

See [`.claude/agents/README.md`](.claude/agents/README.md) for agent roles, model assignments, and scratch directory lifecycle.

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

All documentation, comments, and PRDs must follow the writing standards of the `document-writing` skill ([`.claude/skills/document-writing/documentation-standards.md`](.claude/skills/document-writing/documentation-standards.md)).

## Testing Strategy

See [`docs/testing-principles.md`](docs/testing-principles.md) for test structure, the test pyramid, mocking policy, and coverage. Specialize the language-specific conventions there and in this file as the stack is bound.

## Scratch Directory

Agents collaborate through `.scratch/` (git-ignored). One feature at a time. Never use system `/tmp` — use `.scratch/tmp/`.

See [`.claude/agents/README.md`](.claude/agents/README.md) for structure, file lifecycle, templates, and rules.

## Quality Gate

Before code review, run `scripts/gate.sh verify`. Every lifecycle verb must pass, plus the autofix-audit procedure (see the `code-quality-gate` skill), before invoking reviewers. An unbound verb fails the gate by design — bind it in `scripts/stack.sh`.

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
