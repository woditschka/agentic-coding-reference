## Agent Usage (Mandatory)

**Rule:** Always use specialized agents for feature development. Do not implement features directly.

For the harness shape — the four nested loops, the slice definition, agent roles, and the handoff contract — see [`.claude/skills/handoff-routing/agentic-harness.md`](.claude/skills/handoff-routing/agentic-harness.md). For the portability rules every harness edit must respect (no ADR/REQ references in harness prose; no runtime-specific numbers in harness text), see [`.claude/skills/handoff-routing/agentic-harness.md#harness-invariants`](.claude/skills/handoff-routing/agentic-harness.md#harness-invariants).

### Pipeline Routing

Mid-slice, run `python3 scripts/handoff.py route` after each dispatch returns and follow its decision. The JSON names the decision kind (`dispatch`, `blocked`, `escalate`), the next agent(s), the matched `rule`, and the context to relay; `blocked` always halts for a human. Dispatch the `pipeline-coordinator` only for `escalate` decisions and for classifying an untriaged fresh request — never for a transition `route` already decided. A pick the `next` skill already triaged — `route`'s `no-active-slice` escalate included — records its `intake-decision` and follows the `intake-ready` dispatch. A recovery dispatch assembles its prompt from the section the `handoff-routing` skill § Handoff Conditions maps to the decision's `rule`; a reviewer dispatch carries a paste-ready `prompt_note` — append it verbatim as the prompt's final sentence, composing no round context. A `process-findings` decision with `halt_after: true` halts after the dispatch returns (`handoff-routing` § Blocking). For direct invocation when the target agent is known, use the agent selection table in the `handoff-routing` skill.

**Discussions run in root.** A feature or architecture discussion is a conversation, and subagents cannot converse — root conducts it per [`agentic-harness.md` § Conversations Stay in Root](.claude/skills/handoff-routing/agentic-harness.md). Slice intake runs under the `intake` skill and exits by recording an `intake-decision` — the owner's request and decisions, quoted verbatim. `route` then dispatches the product expert on the record, even when recorded non-goals make the outcome look foregone. Root relays and quotes; it never authors a product or design statement. A specialist can open one mid-dispatch: a `consultation-request` targeting `human` halts the pipeline (`human-consultation`) until root records the human's answer as the `consultation-response`. A scope question never ends the session in prose. When no reply can arrive — or when unsure — record and proceed: fresh intake seeds an `intake-decision` from the request as stated; a mid-slice question dispatches the owning expert with the question as stated. A conflict pauses as its recorded `consultation-request`, never an unrecorded refusal. The shortcut covers questions, never answers: root never authors a `consultation-response`, and `author: "human"` marks a human's actual words. Absent a reply, the recorded pause is the session's correct end. The seed license lapses while a `consultation-request` targeting `human` is pending: that pause resolves only through the human's reply, never through a re-seeded intake. An answer that only restates the request decides nothing — the request is never the override.

**Skip agents for** work that leaves no pipeline artifact to audit: git operations, one-off commands, answering questions about the codebase. A scope decline is never artifact-less: the expert's `consultation-request` is the deliverable, so the conflict dispatches rather than ends the session. **Use review agents for** formal code reviews: "review changes" or "review code" triggers the review agents, never direct implementation.

### Surfacing reviewer and grader output

A subagent's final message returns as a tool result; the user sees only what the orchestrator relays. Report each reviewer's verdict — `approved`, `changes_requested`, or `blocked` — and relay the findings behind anything short of approval. Relay the change-grade report (verdict, rationale, per-facet notes) verbatim: it is the human's merge-decision signal, and nothing downstream acts on it. Summaries suffice for the pipeline's other internal hops. The `change-grader` runs as the terminal advisory hop unless `auto_grade = false` disables it.

### Orchestrator economy

Orchestrator prose is cache-written once, then cache-read on every later turn — keep root turns thin.

- **Relay, don't restate.** A relayed verdict or report needs no preceding paraphrase.
- **One line per routine hop.** Name the dispatch and its reason, take it, report the result.
- **Drop the filler.** Cut preambles ("Now let me…") and recaps of state already visible in the transcript.

Trimming covers connective prose, never content a hop exists to deliver. The human-facing surface stays in full: every non-`approved` verdict with its findings, the verbatim change-grade relay, the implementation plan, decision rationale, and `AskUserQuestion` gates.

### Confirmation Discipline

CLAUDE.md is the legitimate channel for pre-authorizing routine activity, and pipeline work is routine. Authorization granted for a slice covers every routine hop inside that slice until the user scope-limits. Do not re-ask the user to second-guess a clean `route` or `pipeline-coordinator` decision.

**Pause and confirm before:**

- Any action visible outside the local working tree: `git push`, `gh pr create`, `gh pr merge`, `gh issue comment`, Slack/email sends, uploads to third-party services.
- Destructive git: `reset --hard`, `branch -D`, `push --force`, `clean -fd`, history rewrites on shared branches, `--no-verify` / `--no-gpg-sign`.
- A pipeline verdict that pushes the slice past its PRD scope, shortcuts a stage, or escalates a block — the owning skills (`design-validation`, `review-workflow`, `handoff-routing`) define these verdicts and when they fire.
- A second consecutive review failure on the same slice.
- Edits to durable instructions (`CLAUDE.md`, `docs/`, `.claude/agents/`, `.claude/skills/`) that are *not* the active slice's declared implementation target.
- The user's previous message contains a question, doubt, or disagreement — answer it before proceeding.

**Do not pause for:**

- The agent(s) named by a `route` `dispatch` decision — or a clean `pipeline-coordinator` recommendation — when the user has already authorized the slice.
- Re-running `route` on a fresh handoff record, or dispatching `pipeline-coordinator` on its `escalate`.
- File reads, greps, builds, the project's quality gate, and other reversible local operations.
- The exact hop the user just authorized with a forward-motion verb.

**Scope cues from the user.** A forward verb at slice start — "go ahead", "drive the slice", "ship it", "yes", "continue" — authorizes routine hops through the rest of the slice. To scope-limit, the user says "stop after \<stage\>" or "show me before \<action\>", or asks an open question. Slash commands (`/ship`, `/next`) carry the scope defined in their skill prose; do not re-confirm steps the skill itself prescribes.

### Tool-call budget

The Claude Code SDK caps assistant messages at a fixed number of tool calls per dispatch. A dispatch that reaches the cap **truncates and stops**. A cap-hit is a length signal, not a scope verdict: recovery continues the same slice, cheapest first:

- A bare `continue` resume of the stopped subagent (§ Agent teams and the continue hook) — context intact; the fast-path when the runtime offers it.
- A fresh re-dispatch from the partial-artifact checkpoint.
- A fresh re-dispatch with no checkpoint — the dispatch re-derives progress from the working tree and the inbound records.

Do not narrate "Truncated at N tool calls. Continuing." — recovery runs through these mechanisms, not prose. Re-split is reserved for a slice that spans more than one behavior; non-convergent continuation escalates to re-triage.

**Rule:** When a task plausibly needs many tool calls in one turn, dispatch a subagent up front. Prefer the most specific persona that fits: `Explore` for code search beyond a couple of targeted lookups, or a specialist from the `handoff-routing` table. `general-purpose` is dispatched only when **both** hold:

1. **No named persona fits.** Walk the built-ins and the project agents (`.claude/agents/README.md`). A recurring `general-purpose` shape signals extracting a dedicated agent, not re-use.
2. **The Scoping Pre-Check is written into the dispatch prompt** — the tool-call estimate and one named checkpoint milestone.

Per-role budgets and the Scoping Pre-Check / Partial-Artifact Contract are owned elsewhere: each agent's `toolCallBudget` front-matter, and the `tdd-workflow` and `review-workflow` skills. Do not restate the numbers or record shapes here.

### Agent teams and the continue hook

The project turns on Claude Code's experimental agent-teams capability (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `.claude/settings.json`), so a truncated dispatch can resume in place with a bare `continue`. A `PreToolUse` hook (`.claude/hooks/sendmessage-continue-only.py`, registered in the same settings file) allows only the literal `continue` and denies everything else, failing closed. The invariant: a resume may not carry new instructions — all new work is a fresh, schema-validated dispatch on `.scratch/handoff.jsonl`, so the resume channel can never bypass the auditable handoff log. Use `SendMessage` only for the bare-`continue` resume — never for peer-to-peer coordination (or the agent-teams `TeamCreate`/teammate model) that bypasses the log. Commit the hook and `settings.json` together; a missing hook file fails the guard open. The flag is project-scoped (`.claude/settings.json` `env` block), not a user-level default.

### Skills (Portable Workflow Knowledge)

Pipeline logic lives in skills (`.claude/skills/`), not in agent definitions. All four tools (Claude Code, Copilot CLI, OpenCode, Junie CLI) read skills from this location.

| Skill | Purpose |
|-------|---------|
| `handoff-routing` | Routing table, handoff conditions, gates, recovery, root-applied procedures, state files |
| `handoff-append` | The writer contract for the handoff log: sanctioned append form, append-only discipline, permission setup |
| `handoff-board` | The reader board for the handoff log: render each slice to the terminal (header, review matrix, timeline) |
| `prd-authoring` | PRD format, boundary rules, requirement template |
| `tdd-workflow` | TDD cycle process, design-check decision tree, document ownership |
| `code-quality-gate` | The quality gate: required checks, autofix audit, completion criteria |
| `review-workflow` | Review process, feedback tags, output format, partial-artifact contract; reference tables in its `reference.md` |
| `code-quality-review` | Code quality checklist (specialize per stack) |
| `test-review` | Test quality checklist, security testing, dynamic analysis |
| `security-checks` | Security checklists, threat model, severity, supply chain verification |
| `design-validation` | Architectural validation checklist for feature approval |
| `new-feature` | Clear scratch directory, start fresh feature context |
| `intake` | Slice intake as a live discussion under the product expert's contract; exits by recording the owner's decisions verbatim (`intake-decision`) |
| `adr-template` | ADR format, naming conventions, when to create |
| `audit-agents` | Audit agent config for consistency, coherence, cross-tool parity |
| `change-grading` | Grade a passing change for how much human attention it deserves before merge (advisory) |
| `document-writing` | Writing standards every author follows; review checklist, validation categories, and prohibited patterns the doc-reviewer enforces |
| `doc-sync` | Synchronize documentation with codebase after implementation |
| `doctor` | Deterministic blocking validation of `docs/` against the harness-project API (roster, sections, slots, channel invariants) |
| `derive-briefs` | Draft the `docs/` briefs by surveying an existing codebase, marking every statement derived, confirmed, or not recoverable |
| `audit-docs` | Audit `docs/` against the high bar — runs the doctor (structure) then the advisory judgment review, each doc individually and cross-document |
| `ship` | Run quality gate, commit, and push in one step |
| `next` | Reset scratch and recommend the next PRD requirement to tackle |

This table is the stack-agnostic core. When a stack ships its own skills (for example an IDE oracle), the project CLAUDE.md catalogues them in a **Stack-specific skills** chapter; they are always discoverable in `.claude/skills/`.

### Reference

See [`.claude/agents/README.md`](.claude/agents/README.md) for agent roles and model assignments, and [`.claude/agents/README-cross-tool.md`](.claude/agents/README-cross-tool.md) for the scratch directory lifecycle.

## Memory

Durable knowledge lives in this repo — `CLAUDE.md`, `docs/`, `.claude/skills/`, `.claude/agents/`. Do not write to the auto-memory store at `~/.claude/projects/.../memory/`. If a fact is worth remembering across sessions, it is worth committing. If the user asks to "remember" something, edit the right file in the repo instead of saving a memory.

## Writing Standards

All documentation, comments, and PRDs must follow the writing standards of the `document-writing` skill ([`.claude/skills/document-writing/documentation-standards.md`](.claude/skills/document-writing/documentation-standards.md)).

## Scratch Directory

Agents collaborate through `.scratch/` (git-ignored). One feature at a time. Never use system `/tmp` — use `.scratch/tmp/`.

See [`.claude/agents/README-cross-tool.md`](.claude/agents/README-cross-tool.md) for structure, file lifecycle, templates, and rules.

## Documentation Updates

When changing the codebase, follow the Maintenance Rules in the `doc-sync` skill and the Prohibited Patterns in the `document-writing` skill.
