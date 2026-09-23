# Agentic Coding Primer

The vocabulary a reader needs before the rest of this reference makes sense. It covers what an agent tool is, the pieces it is configured from, the two limits that shape the harness's design, and the engineering disciplines the harness builds on. Two words come first. **Agent-team** is the product: the specialist team a project installs, runs, and converses with. The **harness** is the machinery inside it: the agents, skills, hooks, engines, and schemas, and the rules for how they work together. Each entry below ends with where the harness uses the concept. The harness's own terms (slice, handoff, triage, brief) are in the [glossary](glossary.md); this page covers the layer underneath them.

## The Tool

An **agent tool** (Claude Code, GitHub Copilot CLI, OpenCode) is a program that runs a language model in a loop against a repository. The model reads files, runs commands, edits code, and decides its own next step until the task is done or it needs a person. The person types goals; the tool does the legwork. This reference supports all three; the [cross-tool strategy](cross-tool-strategy.md) compares them.

A **model** is the language model behind the tool. Models differ in capability and in price per token, and a tool can run different models for different roles. The harness pins two tiers. The judgment tier carries requirements, design, implementation, security review, and grading; the standard tier carries checklist review and routing. [ADR 2026-06-11](adr/2026-06-11-model-tier-assignment.md) holds the split and the cost math; [`open-weight-models.md`](open-weight-models.md) maps the tiers to a provider that serves open-weight models.

## Two Limits

A **context window** is the amount of text a model can see at once: the conversation so far, the files it read, the command output it saw. It is finite, and it is emptied when the session ends. Everything the harness calls *memory* exists because of this limit. Durable specs in `docs/` and the handoff log in `.scratch/` carry decisions from one session to the next ([`agentic-harness.md` § What the Harness Is For](agentic-harness.md#what-the-harness-is-for)).

A **token** is the unit the model reads and writes, roughly three quarters of an English word, and the unit it is billed in. Every file an agent reads and every line it writes costs tokens. The harness measures this two ways: [Harness Stats](adoption-guide.md#harness-stats) reports a live session, and the [eval bench](../evals/README.md) prices whole harness versions.

## The Pieces a Tool Is Configured From

A **rules file** is the markdown file the tool reads at the start of every session: build commands, conventions, what to do and not do. Claude Code and Copilot CLI read `CLAUDE.md` natively; OpenCode reads it when no `AGENTS.md` exists. One file serves all three. In the harness, `CLAUDE.md` is project-owned with harness-managed chapters inside it ([`harness-project-api.md` § The CLAUDE.md Managed Chapters](harness-project-api.md#the-claudemd-managed-chapters)).

A **skill** is a folder holding a markdown instruction file plus any scripts it needs, loaded on demand when its description matches the task. Skills are portable: all three tools discover them in `.claude/skills/`. The harness ships its methods as skills: the TDD workflow, handoff routing, document writing, and the review checklists ([`specialist-agent-workflow.md` § Reference Implementations](specialist-agent-workflow.md#4-reference-implementations)).

An **agent** (also **subagent**) is a named role with its own instructions, its own tool permissions, and its own model, which the tool runs in a fresh context window. The parent session hands it a task and gets a report back; the subagent's reading never crowds the parent's window. The harness keeps its agents **thin** and its skills **thick**: an agent is the personality, its write scope, its model, and the skills it loads. The method lives in the skills. A method change then edits one skill, and the same agent body serves all three tools. Agent definitions are per-tool (`.claude/agents/`, `.github/agents/`, `.opencode/agents/`), identical apart from the frontmatter. The principle is in [`cross-tool-strategy.md` § Agents / Subagents](cross-tool-strategy.md#agents--subagents); the specialist roster is in [`agentic-harness.md` § Specialist Agents](agentic-harness.md#specialist-agents).

A **hook** is a script the tool runs at a fixed point in a session, such as before a tool call or when the agent tries to stop. Hooks execute outside the model, so they enforce what instructions can only request. Hooks are a Claude Code feature, registered in `.claude/settings.json`; the other two tools carry no equivalent. The harness ships four. Two guard the handoff log: one pre-approves its append command, one refuses a raw write to it. One holds the intake conversation open until its exit is confirmed. One limits teammate messaging to a single word ([Adoption Guide § Handoff Append Pre-Approval](adoption-guide.md#handoff-append-pre-approval-one-time-per-tool)).

An **MCP server** speaks the Model Context Protocol: a standard by which a tool calls an external program's functions, such as querying a database or a running IDE. The harness optionally consults a JetBrains IDE's MCP server as a read-only semantic oracle for type-aware questions ([Adoption Guide § JetBrains Semantic Oracle](adoption-guide.md#jetbrains-semantic-oracle)).

A **plugin** bundles skills, agents, and hooks for installation from a **marketplace**, a catalog a tool can subscribe to. This reference publishes itself as the `agent-team` marketplace, one of three channels a project can receive the harness through ([Adoption Guide § Distribution channels](adoption-guide.md#distribution-channels)).

## The Disciplines the Harness Builds On

**TDD**, test-driven development, writes a failing test before the code that passes it, then refactors with the test as the safety net. Each cycle takes seconds to minutes. In the harness it is the innermost loop, and the one no project can switch off ([`tdd-principles.md`](../harness/core/.claude/skills/tdd-workflow/tdd-principles.md)).

**DDD**, domain-driven design, models software around the business domain and its language. Its strategic side, bounded contexts, decides where one model ends and another begins; the harness uses that partition to keep slices apart ([`ddd-principles.md`](ddd-principles.md)).

A **ubiquitous language** is the one vocabulary the domain experts, the code, and the docs share, with the terms to avoid listed beside the terms to use. Agents drift on vocabulary between sessions faster than people do, so the harness records it in `docs/ubiquitous-language.md` and challenges misuse inline.

An **ADR**, architecture decision record, is a short dated document stating one decision, the options considered, and why one won. It is history, never edited after the fact; a later decision supersedes it with a new record. The harness keeps them in `docs/adr/`, and its own decision log is [`docs/adr/`](adr/) in this repository.

A **slice** is the harness's unit of work: one vertical, independently usable behavior cutting through every layer it touches ([`agentic-harness.md` § What a Slice Is](agentic-harness.md#what-a-slice-is)).

## Putting It Together

The tool runs a model in a loop. The rules file sets the ground rules. Skills carry the methods, agents carry the roles, hooks enforce the invariants, and MCP servers reach outside the repository. The context window forgets, so the harness writes what matters to files. Tokens cost money, so the harness measures what each run spends.

Where each piece lives in a project that runs the harness:

```text
my-service/
├── CLAUDE.md              # the rules file; all three tools read it
├── .claude/
│   ├── skills/            # the skills; all three tools read this one tree
│   ├── agents/            # the agents, Claude Code form
│   ├── hooks/             # the hooks; Claude Code only
│   └── settings.json      # Claude Code settings: hook registration, permissions
├── .github/agents/        # the same agents, Copilot CLI form
├── .opencode/agents/      # the same agents, OpenCode form
├── docs/                  # the durable specs: long-term memory (prd, system design, adr/, briefs)
├── .scratch/              # the handoff log: working memory, gitignored
├── schemas/               # one schema per handoff record type
├── scripts/               # the engines the skills call, plus the project's layout.toml
└── src/                   # the application
```

The full layout, with which tool reads which path, is in [`specialist-agent-workflow.md` § Project Structure](specialist-agent-workflow.md#3-project-structure). What the harness builds on top of these pieces, and why, starts at [`agentic-harness.md`](agentic-harness.md).
