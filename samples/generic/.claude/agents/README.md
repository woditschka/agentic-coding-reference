# Agent Team

Agent definitions for reference. Each agent has a specific role in the feature development pipeline.

## Goals

**Primary: code meets the bar.** The bar is the conjunction of nine clauses defined across the project's principles docs. The canonical slug list and reviewer-to-clause mapping lives in the `review-workflow` skill's [`reference.md`](../skills/review-workflow/reference.md) § Quality-Bar Clause Mapping. The clauses themselves are defined here:

| Slug | Defined in |
|---|---|
| `fit-for-purpose`, `spec-grounded`, `consistent-with-codebase` | [`tdd-principles.md`](../skills/tdd-workflow/tdd-principles.md) § Scope Discipline |
| `legible-cold`, `tested-as-spec`, `correct` | [`tdd-principles.md`](../skills/tdd-workflow/tdd-principles.md) § Code That Reads Cold |
| `operationally-honest`, `human-maintainable` | [`tdd-principles.md`](../skills/tdd-workflow/tdd-principles.md) § Operationally Honest |
| `secure-by-design` | [`tdd-principles.md`](../skills/tdd-workflow/tdd-principles.md) § Secure by Design |

A change is not done until all nine hold; a passing test suite is necessary but not sufficient. Every pipeline change is judged first on whether it sustains or raises adherence.

**Secondary: token economy and wall-clock.** Subject to meeting the bar, prefer the cheaper and faster path. Tokens and wall-clock are sister concerns — most of the practices below shorten both. When they conflict, the harness favors wall-clock for interactive work and tokens for batch.

| Practice | What it means |
|---|---|
| **Read narrowly** | Load specific files, symbols, or ranges. Don't enumerate directories or read whole files when a targeted lookup suffices. Re-read only when state has changed. |
| **Think proportionally** | Match deliberation to task risk. Routine changes don't need extensive planning; novel or cross-cutting changes do. Don't pad reasoning. |
| **Draft to ship, not to impress** | No commentary explaining what the code obviously does. No restating the spec back. No preambles. Output is the artifact set, not narration about producing it. |
| **Iterate where it pays** | Self-review passes are cheap and high-value — run them. Re-running the full task to fix something a targeted edit would handle is wasteful — don't. |
| **Parallelize independent work** | Reviewer dispatches, independent agent calls, and independent tool calls go in a single message. |
| **Stop at done** | Once the bar is met, stop. Polish past the bar spends tokens and wall-clock without raising quality. |

When interpreting evaluation findings, fix in this order: (1) gaps that let code below the bar through, (2) waste at constant bar adherence, (3) cosmetic report quality.

## Architecture

**Agents own behavior.** Each agent is a thin wrapper: persona, tool permissions, model selection. Domain mechanics live in the skills the agent references.

**Skills own knowledge.** Portable workflow logic lives in `.claude/skills/`. All four tools (Claude Code, GitHub Copilot, OpenCode, Junie CLI) read skills from this location.

**Project docs own truth.** Requirements (`docs/prd.md`), architecture (`docs/system-design.md`), and decisions (`docs/adr/`) are the authoritative sources.

## Agents

| Agent | Role | Model | Outputs |
|-------|------|-------|---------|
| **pipeline-coordinator** | Classify fresh intake, resolve `route` escalations | Sonnet | Routing recommendations |
| **product-requirements-expert** | Define and clarify feature requirements | Opus | `docs/prd.md`, `docs/ubiquitous-language.md`, non-goal ADRs, `.scratch/handoff.jsonl` (`prd-entry`, `consultation-response`, `consultation-request` records) |
| **system-design-expert** | Validate architectural fit | Opus | `docs/system-design.md`, `docs/adr/`, `docs/ubiquitous-language.md` (foundational triage only), `.scratch/handoff.jsonl` (`design-block`, `consultation-response`, `consultation-request` records; `prd-entry` only as the refactor-first sibling entry) |
| **feature-implementer** | TDD/DDD implementation | Opus | Code, tests, `.scratch/handoff.jsonl` (`build-failure`, `build-pass`, `consultation-request` records), `.scratch/implementation-plan.md`, `.scratch/escalations.md` |
| **feature-implementer-routine** | Rendered effort-medium variant of feature-implementer for all-autofix fix rounds, selected by the router's tier derivation | Opus | Same as feature-implementer — the shared body records `author: "feature-implementer"` |
| **review-planner** | Resolve a gray `review-plan` into a reviewer roster (dispatched only when the engine defers a small, clean production change) | Sonnet | `.scratch/handoff.jsonl` (`review-plan` record, `author: "review-planner"`) |
| **code-quality-reviewer** | Readability, code-quality conventions | Sonnet | `.scratch/handoff.jsonl` (`review-feedback` record, `author: "code-quality-reviewer"`) |
| **test-reviewer** | Test pyramid, coverage | Sonnet | `.scratch/handoff.jsonl` (`review-feedback` record, `author: "test-reviewer"`) |
| **security-reviewer** | OWASP, vulnerabilities | Opus | `.scratch/handoff.jsonl` (`review-feedback` record, `author: "security-reviewer"`) |
| **doc-reviewer** | Doc coherence, structure, writing | Sonnet | `.scratch/handoff.jsonl` (`review-feedback` record, `author: "doc-reviewer"`) |
| **change-grader** | Grade passing changes for how much human attention they deserve before merge (terminal, advisory) | Opus | `.scratch/handoff.jsonl` (`grader-features`, `grader-verdict` records) |

## Skills

Pipeline routing, quality gates, and templates live in portable skills.

**Universal harness skills** (lift to any project adopting this harness):

| Skill | Purpose | Used By |
|-------|---------|---------|
| `handoff-routing` | Routing table, handoff conditions, blocking rules, root-applied procedures | pipeline-coordinator, root |
| `handoff-append` | Writer contract for the handoff log: sanctioned append form, append-only discipline | every record-writing agent |
| `handoff-board` | Reader board for the handoff log: renders each slice — header, review-convergence matrix, timeline — to the terminal | Human / any agent |
| `prd-authoring` | PRD format, boundary rules, requirement template | product-requirements-expert |
| `tdd-workflow` | TDD cycle process, design-check decision tree, document ownership | feature-implementer |
| `code-quality-gate` | Build/test/lint requirements, completion criteria | feature-implementer, reviewers |
| `review-workflow` | Review process, feedback tags, output format, partial-artifact contract; reference tables in its `reference.md` | All reviewers, feature-implementer |
| `code-quality-review` | Code quality checklist (specialize per stack), design placement, scope and vocabulary | code-quality-reviewer |
| `test-review` | Test placement and quality checklist, security testing, dynamic analysis | test-reviewer |
| `security-checks` | Security checklists, threat model, severity, supply chain verification | security-reviewer |
| `design-validation` | Architectural validation checklist for feature approval | system-design-expert |
| `adr-template` | ADR format, naming conventions | system-design-expert |
| `new-feature` | Clear scratch directory, start fresh context | root (user-invoked) |
| `intake` | Slice intake discussion under the product expert's contract; exits by recording the owner's decisions verbatim | root (user-invoked) |
| `audit-agents` | Audit agent config for consistency, coherence, cross-tool parity | Human / any agent |
| `change-grading` | Grade a passing change for how much human attention it deserves (facets, worst-facet aggregation, advisory verdict) | change-grader |
| `document-writing` | Writing standards (authoring) + review checklist, validation categories, prohibited patterns | doc-reviewer (enforces); every doc-authoring agent follows it |
| `doc-sync` | Synchronize documentation with codebase after implementation | Human / any agent |
| `doctor` | Deterministic blocking validation of `docs/` against the harness-project API | Human / any agent / CI |
| `derive-briefs` | Draft the `docs/` briefs by surveying an existing codebase, marking every statement derived, confirmed, or not recoverable | Human / any agent |
| `audit-docs` | Audit `docs/` against the high bar — the doctor (structure) then the advisory judgment review, individually and cross-document | Human / any agent |
| `ship` | Run quality gate, commit, and push in one step | Human / any agent |
| `next` | Reset scratch, recommend next PRD requirement to implement | Human / any agent |

**Project-specific extensions** (this project only; not harvested into the universal harness):

A downstream project lists its domain-specific skills here, separating them from the portable harness skills above. The template ships only universal skills, so this section is an empty placeholder.

| Skill | Purpose | Used By |
|-------|---------|---------|
| _(none in the template)_ | | |

## When to Use Each Agent

| Scenario | Agent | Why |
|----------|-------|-----|
| "Add user authentication" | **product-requirements-expert** | New feature — full pipeline; the `intake` skill records the discussion's exit and `route` dispatches (`intake-ready`) |
| "Does REQ-XX-003 cover edge cases?" | **root** | Requirement clarification — root converses; product-requirements-expert records the PRD change |
| "Where should the retry logic live?" | **root** | Architecture question — root converses; system-design-expert records durable-memory changes |
| "Implement REQ-XX-001" | **feature-implementer** | Clear requirement, ready to build |
| "Fix the connection timeout bug" | **feature-implementer** | Bug with known location (shortcut) |
| "Review my PR" | All reviewers in the roster | Parallel review invocation |

For the full routing table, see the `handoff-routing` skill.
