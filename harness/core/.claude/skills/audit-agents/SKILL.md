---
name: audit-agents
description: >-
  Audit the agentic configuration for consistency, coherence, and conciseness.
  Load when modifying agent definitions, skills, or pipeline structure,
  or to verify cross-tool parity.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
metadata:
  version: "2.0"
  author: team
---

## Channel Scope

This skill audits a committed harness runtime and applies to the **copy channel** only. On the marketplace channel the runtime ships inside the plugin, so install hygiene is the plugin repository's CI concern, not the consumer project's. Doc-form validation is owned elsewhere: the `doctor` skill (blocking, deterministic), `audit-docs` (advisory judgment), and `document-writing` (review-time form checks).

## When to Run

Run this audit after any change to:
- Agent definitions (`.claude/agents/`, `.github/agents/`, `.opencode/agents/`, `.junie/agents/`)
- Skills (`.claude/skills/`)
- Pipeline state files or templates (`.claude/templates/`)
- CLAUDE.md agent-related sections
- `.claude/agents/README.md`

## Audit Checklist

### 1. Skills Coverage

- [ ] CLAUDE.md skills table lists every skill in `.claude/skills/` — no missing, no extras.
- [ ] `.claude/agents/README.md` skills table matches CLAUDE.md.
- [ ] Every skill referenced in an agent file (`Load the X skill`) resolves to an existing `.claude/skills/X/SKILL.md`.

### 2. Agent Thinness

An agent file is the agent's job description; a skill is reusable mechanics. They overlap by design. The audit must distinguish *real duplication* (drift hazard) from *parallel description* (different audience, different level of detail) before flagging anything.

**Positive shape of a thin agent file.** A well-shaped agent body contains, in roughly this order: persona statement, skill/doc references, write scope (which files the agent may modify), a short process overview (≤7 lines naming what the agent does, not how the skill works), and any agent-specific conduct rules. Anything beyond this is a candidate for the drift test.

**The drift test.** For each candidate finding, run this test before tagging it a violation:

> If the skill changes, must the agent file also change to keep the system correct? If yes, it's duplication. If no, it's parallel description — leave it.

Concretely, this means:

- A skill's **checklist body, scoring table, output schema, or step-by-step process** is reusable mechanics. Copying any of these into an agent body fails the drift test → duplication. Replace with a one-line pointer.
- An agent's **list of its own responsibilities, judgement criteria, or the transitions/gates/stages it operates on** describes the agent's surface area. The underlying skill may detail *how* each item works; the agent's list signals *what* the agent does. This passes the drift test (the skill can evolve its mechanics without changing the agent's job description) → not duplication.

**Mandatory false-positive examples** — these have been wrongly flagged as duplication; do NOT flag them:

- `pipeline-coordinator.md` Step 5 enumerating which schema gates which transition (product-requirements-expert→system-design-expert, system-design-expert→implementer, etc.). The list is the coordinator's surface area, not the skill's content.
- `system-design-expert.md` Responsibilities listing architectural validation, security/reliability, understandability, defense in depth, integration analysis. These are the system-design-expert's judgement criteria; `design-validation` § Design Principles details *how* to apply them.
- A reviewer agent's brief Review Process overview (≤7 lines) when the matching `*-review` skill carries a parallel section. The agent overview signals *what* the reviewer does first; the skill section is the full mechanics.

**Real-duplication checklist:**
- [ ] No verbatim copy of a skill's checklist body, scoring table, or step list (drift test fails).
- [ ] No agent inlines a process that another agent already follows from the same skill (drift fans out across files).
- [ ] Every reviewer agent has a dedicated domain skill (mechanics live in the skill).

**Grep patterns — candidates only, run the drift test before flagging:**

| Pattern | Where to Search | Likely violation when… |
|---|---|---|
| `- \[ \]` (3+ rows) | Agent body | The checkbox list mirrors a skill's checklist body. Single-row reminders are fine. |
| `\*\*Red\*\*.*failing test` | Agent body | Restates TDD cycle mechanics from `tdd-workflow`. |
| `## Review Focus` with criteria | Agent body | Restates a review skill's checklist. |
| `## PRD Boundary` with rules | Agent body | Restates `prd-authoring` validation rules. |
| `## Output Format` with full template | Agent body | Restates a template that exists in `.claude/templates/` or a skill's output contract. |
| Numbered process 5+ steps mirroring a skill | Agent body | The agent's process is the skill's process verbatim. |

Patterns that look like duplication but routinely pass the drift test (do not flag without confirming):
- A short `## Responsibilities` or `## Process` list naming what the agent does.
- An at-a-glance map of transitions/gates/stages keyed by schema name.
- A pointer phrase like "see `<skill>` § X" followed by a 1-2 sentence summary of why the agent invokes that section.

### 3. Cross-Tool Parity

For each agent, compare all four tool versions (`.claude/`, `.github/`, `.opencode/`, `.junie/`):
- [ ] Same persona text (first paragraph after frontmatter).
- [ ] Same skill references (identical skill names in body).
- [ ] Same document references (same files and sections).
- [ ] Same write scope (if defined in any version, must be in all).
- [ ] Same review process steps (same numbered list).
- [ ] Client-specific tools are expected, not parity gaps: an MCP server or skill wired to only one runtime (declared in that client's `tools:` or skill set) is correct by design. Its absence from `.opencode/`, `.github/`, or `.junie/` is not a finding.
- [ ] Correct model mapping. Each tier maps across tools as follows; flag only deviations from this table:

  | Tier | Claude Code | GitHub Copilot | OpenCode | Junie |
  |------|-------------|----------------|----------|-------|
  | Sonnet | `claude-sonnet-4-6` | `Claude Sonnet 4.6 (copilot)` | `openrouter/anthropic/claude-sonnet-4.6` | `sonnet` |
  | Opus | `claude-opus-4-8` | `Claude Opus 4.7 (copilot)` | `openrouter/anthropic/claude-opus-4.8` | `opus` |

  The Opus tier is asymmetric across tools: Anthropic's current latest is 4.8, available on Claude Code and OpenRouter today; GitHub Copilot's catalog tops out at 4.7. Junie still uses the alias form (`opus`/`sonnet`) because its docs do not document a pinned-ID format. Run `deps-upgrade` to bump pins when upstream catalogs advance.
- [ ] Tool permissions match intent (reviewers need write for output file).

### 4. Reference Integrity

The rule is uniform: **every path-shaped string in agent and skill files must resolve to an existing file or directory.** Path-shaped means a token containing `/` and ending in a known extension (`.md`, `.yaml`, `.yml`, `.json`, `.jsonl`, `.sh`, or a source-file extension) or referring to a known directory (`docs/`, `.claude/`, `.github/`, `.opencode/`, `.scratch/`, `schemas/`, or a source root declared in `scripts/layout.toml`).

- [ ] Every path-shaped reference in `.claude/agents/`, `.claude/skills/`, `.claude/templates/`, `.github/agents/`, `.opencode/agents/`, `.junie/agents/`, `CLAUDE.md`, and `docs/` resolves to a real file or directory. The check includes — but is not limited to — `docs/X.md`, `docs/X.md#anchor`, `.claude/templates/X.md`, `.scratch/*`, source files, `schemas/scratch/X.schema.json`.
- [ ] Every `docs/X.md#anchor` reference points to an existing heading or `<a id="...">` anchor.
- [ ] **Self-audit:** apply the same check to this skill (`.claude/skills/audit-agents/SKILL.md`). Stale references in the audit skill itself propagate into every audit run.

Use grep to find candidates. The alternation below covers the universal doc and config extensions; append your stack's source-file extension(s) — a Go project adds `go`, a Java project adds `java` — so source references are caught too:

```
grep -rohE '[A-Za-z0-9_./-]+\.(md|ya?ml|json|jsonl|sh)' \
  .claude/ .github/ .opencode/ .junie/ CLAUDE.md docs/ | sort -u
```

Then check each against the filesystem. Same for directory references.

### 5. Review Output Records

Verify the floor `author` values match across all locations:
- Reviewer agent files (all four tools — each names its own `author` value)
- `review-workflow` skill reviewer table
- `.claude/agents/README.md` agent table

The roster is the floor plus any `extra_reviewers` declared in `scripts/layout.toml [harness]`. `schemas/scratch/review-feedback.schema.json` validates `author` by the `*-reviewer` shape pattern, not a closed enum — the roster's authority is the floor (harness-owned) plus the declared extras (doctor-enforced), not the schema.

Expected floor `author` values for `review-feedback` records:
- `code-quality-reviewer`
- `test-reviewer`
- `security-reviewer`
- `doc-reviewer`

Each reviewer appends one `review-feedback` record per dispatch to `.scratch/handoff.jsonl`. There is no per-reviewer markdown file.

### 6. No Duplication

- [ ] No skill duplicates content from another skill.
- [ ] No agent inlines content that exists in a skill it references.
- [ ] CLAUDE.md does not duplicate skill content (pointers only).
- [ ] No enforcer or reviewer skill (`design-validation`, `code-quality-review`, …) copies a tactical rule the brief owns as **adaptable** (Pattern Catalog realizations, persistence/mapping/ACL strategy, naming/suffix conventions). Enforcers carry only the closed-kernel checks, may state the stack's realization of them, and defer the rest to the brief with one "as written" line. Bounded-module structure and the inward-dependency check are kernel, not findings. Language idioms the brief does not own — line length, package-name hygiene, framework wiring — stay with the reviewer. A brief-owned adaptable rule copied verbatim into an enforcer is a finding. The closed kernel is:
  - the four kernel properties: ubiquitous language, bounded modules, isolated testable core, state-vs-history split;
  - the five closed protections: immutability and equality by value, invariants at construction, infra-free core with inward dependencies, aggregate-root entry, anti-corruption at uncontrolled boundaries.

### 7. State File Consistency

Verify state file references match across:
- `handoff-routing` skill state files table
- `.claude/agents/README.md` scratch directory structure
- `.claude/templates/` directory (markdown helpers only)
- `schemas/scratch/*.json` (record schemas)

Expected state files:
- `.scratch/handoff.jsonl` (append-only; record types: `prd-entry`, `design-block`, `consultation-request`, `consultation-response`, `dispatch-start`, `build-failure`, `build-pass`, `review-feedback`, `design-doc-autofix`, `grader-features`, `grader-verdict`)
- `.scratch/implementation-plan.md` (feature-implementer self-tracking)
- `.scratch/escalations.md` (feature-implementer on escalate-tag findings; root on the router's `blocked` decision for prerequisite-missing aborts, reviewer stalls, and escalate findings on an `approved` verdict; never the coordinator itself)

The change-grader writes no separate state files (both records live in `.scratch/handoff.jsonl`).

Expected schema files (one per record type):
- `schemas/scratch/prd-entry.schema.json`
- `schemas/scratch/design-block.schema.json`
- `schemas/scratch/consultation-request.schema.json`
- `schemas/scratch/consultation-response.schema.json`
- `schemas/scratch/dispatch-start.schema.json`
- `schemas/scratch/review-feedback.schema.json`
- `schemas/scratch/build-failure.schema.json`
- `schemas/scratch/build-pass.schema.json`
- `schemas/scratch/design-doc-autofix.schema.json`
- `schemas/scratch/grader-features.schema.json`
- `schemas/scratch/grader-verdict.schema.json`

Expected `design-block.verdict` enum: `covered`, `minor`, `new`, `refactor-first`, `foundational`, `conflicting`. Flag any occurrence of the old enum values (`approved`, `needs_changes`, `blocked`, `revised`, `escalated`) in this project's docs, skills, agents, or schemas — they are stale and must not leak.

Expected `review-feedback.verdict` enum (distinct from design-block): `approved`, `changes_requested`, `blocked`. Do not confuse the two enums when auditing. Other project domains may reuse some of these tokens (e.g. as work-unit outcome values in their PRD or system-design) — those are unrelated to the design-block verdict.

### 8. Quality Gate Consistency

Verify the quality gate matches across all locations:
- [ ] CLAUDE.md "Quality Gate" section lists all required checks.
- [ ] `.claude/skills/code-quality-gate/SKILL.md` required checks table matches CLAUDE.md.
- [ ] Code-quality-reviewer agent permitted commands include the gate's format check. Reviewers trust the `build-pass` record for the rest of the gate; they do not re-run `build`/`test`.
- [ ] The quality-gate pipeline (see CLAUDE.md) includes all required checks.
- [ ] Gate-command pre-approval stays user-local: the committed `.claude/settings.json` registers the hooks; format-command permissions belong in the uncommitted `.claude/settings.local.json` or the tool's allowlist, never a committed file.

### 9. Pipeline Philosophy Enforcement

Verify the handoff-routing skill contains:
- [ ] Coordinator output format (structured recommendation template).
- [ ] Coordinator rules (no skipping stages, stale state detection, escalation reporting).
- [ ] State detection logic (file existence + status → next agent).

Verify agents do NOT contain:
- [ ] Coordinator output format (belongs in handoff-routing skill).
- [ ] Routing rules or state detection tables (belongs in handoff-routing skill).
- [ ] TDD cycle steps (belongs in tdd-workflow skill).

### 10. Reviewer Conduct

For each reviewer agent in all four tool directories — the four-reviewer floor (code-quality, test, security, doc) plus any `extra_reviewers` declared in `scripts/layout.toml [harness]`:
- [ ] Reviewer Conduct section present.
- [ ] Includes `/tmp` prohibition: "Never use system `/tmp`; use `.scratch/tmp/`".
- [ ] Lists permitted commands explicitly.
- [ ] Specifies write-only output file.

### 11. Skill Cross-References

- [ ] Every path in a skill's `reads:` frontmatter exists and appears in the doctor manifest (`scripts/brief-expectations.toml`) roster — skills may only bind to documents the harness-project API guarantees.

- [ ] `doc-reviewer` agent references `document-writing` skill (for validation categories and review process).
- [ ] `doc-reviewer` agent references `prd-authoring` skill (for PRD boundary enforcement).
- [ ] `doc-reviewer` agent references `review-workflow` skill (for output format).
- [ ] `feature-implementer` agent references `tdd-workflow` skill.
- [ ] `feature-implementer` agent references `code-quality-gate` skill.
- [ ] `feature-implementer` agent references `review-workflow` skill.
- [ ] `pipeline-coordinator` agent references `handoff-routing` skill.
- [ ] Every record-writing agent — all project-defined agents except `pipeline-coordinator` — references the `handoff-append` skill.
- [ ] `change-grader` agent references `change-grading` skill.
- [ ] `system-design-expert` agent references `design-validation` skill (for triage modes, verdicts, and consultation handling).

### 12. Consultation Routing Semantics

The consultation roundtrip is the mechanism by which an in-flight specialist (typically `feature-implementer`) gets a focused answer from another specialist (typically `system-design-expert`) without advancing the pipeline. Verify the semantics are consistently described:

- [ ] `handoff-routing` skill: documents Gate 2b for consultation records; states that after a `consultation-response` the router returns control **back to the requesting specialist**, not forward to the next pipeline stage.
- [ ] `pipeline-coordinator` agent: defers consultation transitions to `route` (which executes both hops) and never re-decides them; any consultation prose it keeps follows the back-route semantics above.
- [ ] `tdd-workflow` skill: the design-check decision tree directs the implementer to append a `consultation-request` rather than block waiting; the inner loop resumes when the matching `consultation-response` arrives.
- [ ] `design-validation` skill: describes both triage mode (returns one of the six `design-block` verdicts) and consultation mode (returns a `consultation-response`); the agent reads the input record type and acts accordingly.
- [ ] `system-design-expert` agent: write scope includes appending `consultation-response` records to `.scratch/handoff.jsonl`; `docs/ubiquitous-language.md` is in scope **only** during the `foundational` triage path.
- [ ] `feature-implementer` agent: write scope includes appending `consultation-request` records; agent does not modify `docs/` directly.

### 13. system-design-expert Modes and Verdict Coverage

The `system-design-expert` operates in two demand-driven modes; verify each is documented consistently:

- [ ] `system-design-expert` agent (all four tool versions) names triage + consultation as the two modes and lists the six verdicts.
- [ ] `design-validation` skill enumerates the six verdicts with content guidance per verdict.
- [ ] `.claude/skills/handoff-routing/agentic-harness.md` § The system-design-expert role in depth lists the same six verdicts.
- [ ] `design-block.schema.json` enum exactly matches the six verdict names.
- [ ] The `foundational` path covers both greenfield projects and adoption (extracting candidate vocabulary from existing docs and source); same description across the system-design-expert agent, `design-validation`, and `agentic-harness.md`.

### 14. Principle Taxonomy (Judgment vs Hard Contract)

Per [`agentic-harness.md`](../handoff-routing/agentic-harness.md) § Principles Over Rigid Rules, every instruction in an agent or skill is a hard contract or a judgment instruction, written differently. This check keeps the split from decaying into a flat rule list. As with the drift test, flag only a clear miss, not every terse line.

- **Hard contract** — schema field, routing rule, write scope, dispatch step, record shape. Stays a bare imperative.
- **Judgment instruction** — a classification, sizing test, verdict, or escalate-or-proceed call where no enumeration is complete. Carries one compact rationale clause: the *why* an agent generalizes from on an unlisted case.

- [ ] Each canonical judgment surface states its *why*, not only its *what*. The surfaces: the six triage verdicts (`design-validation`), the design-check decision tree (`tdd-workflow`), the review-feedback tags (`review-workflow`), slice-sizing (`prd-authoring`), severity classification (`security-review`), and the consult-vs-escalate call (`handoff-routing`).
- [ ] No hard contract is padded with rationale prose — a schema field, routing row, or write-scope line stays bare; the *why* belongs in an ADR.
- [ ] Each agent persona states the spirit of the role (what it protects, the judgment it owns), not a restatement of its mechanical steps.
- [ ] A newly added judgment surface ships with its clause; a newly added contract does not grow prose.

### 15. Truncation Detection Semantics

Truncation recovery fires on a deterministic signal read from `.scratch/handoff.jsonl` alone — a `dispatch-start` with no subsequent substantive record from the same `(req_id, author)`. An earlier design gated recovery on an out-of-band signal from root; that trigger is superseded. Verify every description of the mechanism agrees:

- [ ] `handoff-routing` skill § Dispatch Truncation Detection states the deterministic, state-only rule and marks the old root-signal trigger as superseded.
- [ ] The router fires truncation recovery the moment the state rule is satisfied: `route` executes the implementer's recovery rows; the `pipeline-coordinator` (all four tool versions) fires recovery for escalated states. The test is behavioral, not lexical. Flag any router or coordinator prose that makes recovery wait on, depend on, or defer to anything outside `.scratch/handoff.jsonl` — a root or parent signal, external confirmation, human notification. Also flag prose that calls the state-only signal insufficient, ambiguous, or unreliable. If recovery could stall while the truncation signal already sits in state, it is a finding regardless of wording.
- [ ] `.claude/skills/handoff-routing/agentic-harness.md` § Dispatch-Event Contract and Recovery Paths describes the same deterministic, filesystem-only detection.
- [ ] The substantive-record enum (the records that satisfy the implicit stop) matches between the `handoff-routing` skill and `.claude/skills/handoff-routing/agentic-harness.md` — the two sources that enumerate it. The coordinator must reference the term, not restate the enum.

The check is on the detection *mechanism*, not a single stale phrase: flag any file that describes truncation as undetectable from state or dependent on an out-of-band trigger.

## Output Format

Report each item as:
- `[OK]` — checked and correct
- `[ISSUE]` file:line — description and fix
- `[DUPLICATION]` file:line — what is duplicated and where
- `[TAXONOMY]` file:line — judgment surface missing its rationale clause, or a hard contract padded with prose

## Fix Hygiene

When applying fixes for the issues this audit surfaces, three anti-patterns recur and have to be resisted explicitly — otherwise the fix re-creates the same class of problem the audit caught.

**Prefer pattern phrasing over instance enumeration.** When a finding cites a stale list of paths, the replacement should name the *pattern*, not enumerate current instances:

- Bad: `config/foo/defaults, config/bar/defaults` — silently rots when a third config module is added.
- Good: `the relevant defaults file in config/<config-domain>/ (currently foo, bar)` — survives module additions.

The rule: if the list might grow, name the shape and parenthesize the current members.

**Spread-check every stale reference.** A stale string almost never appears in one file. Before declaring a fix done, grep the entire harness corpus (`.claude/`, `.github/`, `.opencode/`, `.junie/`, `docs/`, `CLAUDE.md`) for the original token and fix every occurrence in one pass. Piecemeal fixing across audit runs is how zombie references accumulate.

**Redundancy check on new content.** When a finding's fix adds a checklist item, process step, or section, verify no sibling item already covers it. If step 1 says "read every Go file under `internal/`", a step 2 enumerating four files under `internal/` is dead weight — fold or delete.
