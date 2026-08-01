---
name: review-workflow
description: >-
  Review process overview, feedback tag definitions, and output format.
  Load when conducting or processing code reviews.
compatibility:
  - claude-code
  - github-copilot
  - opencode
  - junie-cli
reads:
  - docs/testing-principles.md
  - docs/architecture-principles.md
  - docs/security-principles.md
metadata:
  version: "1.0"
  author: team
---

## Review Phase

The roster is the mandatory four-reviewer floor below plus any `extra_reviewers` declared in `scripts/layout.toml [harness]`:

| Reviewer | `author` value | Focus |
|---|---|---|
| code-quality-reviewer | `"code-quality-reviewer"` | Readability, project style guide |
| test-reviewer | `"test-reviewer"` | Test pyramid, coverage, edge cases |
| security-reviewer | `"security-reviewer"` | OWASP, vulnerabilities, supply chain |
| doc-reviewer | `"doc-reviewer"` | Documentation coherence, structure |

The floor cannot be dropped; a project only adds reviewers. A declared extra reviewer is named `*-reviewer` and focuses on the dimension it is built for. It joins the gate exactly like a floor reviewer: when a pass dispatches it, its `review-feedback` record must read `approved` before the feature is complete. Each reviewer appends one `review-feedback` record. Schema: [`schemas/scratch/review-feedback.schema.json`](../../../schemas/scratch/review-feedback.schema.json).

### Risk-Proportional Roster (the review-plan)

Which of the roster reviews a given pass is proportional to a logged risk estimate, not always the whole battery. As the **final step of gate-pass**, right after appending `build-pass`, the feature-implementer runs:

```bash
python3 scripts/grading.py review-plan --feature <req_id>
```

This appends a `review-plan` record (schema: [`schemas/scratch/review-plan.schema.json`](../../../schemas/scratch/review-plan.schema.json)) naming the roster and read scope for the pass. The engine decides the clear cases. On the first pass, a docs/test/config change gets a surface-matched subset. Anything sensitive, multi-module, oversize, unclassifiable, or on a noisy slice gets the full battery. A small, clean production change defers to the `review-planner` (`risk: "gray"`). A fix pass sizes risk over the fix delta alone: a contained, clean delta re-dispatches only the dissenters plus bar-clause-implicated reviewers. A sensitive, oversize, unclassifiable, or escaped delta — or one following a critical finding — re-runs the full battery. A slice that touched sensitive paths keeps the security reviewer on every fix round. `route` then dispatches exactly the plan's roster in parallel; a gray plan dispatches the planner first to resolve it. If the engine is not run, `route` fails closed to the full battery, so review is never *less* than today by accident. The floor is never subtracted — a plan only narrows which floor reviewers a pass dispatches.

**Read scope.** The plan's `scope` tells each dispatched reviewer what to read:

- `full-diff` — the whole change set: `scripts/changeset.sh` (hunks), `scripts/changeset.sh --name-only` (scope).
- `fix-delta` — only the fix hunks since the previous pass, plus your own open findings: `scripts/changeset.sh --base-tree <basis.prev_tree_sha>`. A re-review reads what changed since it last spoke, not the whole slice again.

A reviewer dispatched on a fix cycle receives its own prior open findings in the dispatch prompt (its record, never the implementer's narrative — fresh eyes hold). Feature-complete requires every reviewer dispatched since the latest `design-block` to hold a latest `approved` (`route` computes it from the plan trail; `route-spec.md` § Gate 5). A reviewer the current pass did not dispatch keeps its prior `approved`; a superseded cycle's dissent is re-covered by the `design-revision` full battery, not by this gate.

## Reviewer Read-Set (Fresh Eyes)

A reviewer judges the **change set** under review against **long-term memory** (`docs/` — PRD, system-design, ubiquitous-language, ADRs, and the principles briefs), reading the wider project on demand. It does not take the implementer's plan (`.scratch/implementation-plan.md`) as review input. It reads `.scratch/handoff.jsonl` only to anchor its dispatch — the `build-pass` line it responds to — not to mine the design triage or the implementer's reasoning.

The reviewer is the first proxy for every future reader who will see this code with only the durable docs and the diff — never the author's plan. Reading the implementer's narrative forfeits exactly the cold read that review exists to perform.

## Class-Exhaustive Findings

One finding is evidence of a class. Before appending your record, sweep the rest of the review surface for further instances of every class you found — search, never trust recall. Treat the searched-for pattern as a literal, fixed string (`grep -F -e <pattern> --`), never as a shell or regex input. A class is the finding's `bar_clause` or its checklist category. One record naming every instance converges in one fix cycle; instances surfaced one per round each buy a full re-review round.

The sweep also holds on a fix-delta re-review: a new finding there means sweeping its class across the whole delta before appending. A finding on surface unchanged since your last review signals an incomplete earlier sweep — record it, then sweep its class once more.

The planned checkpoint (§ Partial-Artifact Contract) outranks the sweep. At a checkpoint, sweep only the surface you already reviewed; the truncation record routes the rest to the re-run.

Obtain the change set through `scripts/changeset.sh` — the single definition the change-grader also resolves, so a reviewer's view and the grader's row agree. `scripts/changeset.sh --name-only` lists the changed files (the review scope); `scripts/changeset.sh` emits the unified diff (the hunks). Read full files from the working tree on demand for context the diff omits.

## Output Protocol (Reviewers)

Your sole deliverable is the appended `review-feedback` record. The pipeline cannot proceed without it.

1. **Read** `.scratch/handoff.jsonl` first. If the file does not exist, the implementer has not signalled gate-pass — abort and report the missing precondition.
2. **Append one line** to `.scratch/handoff.jsonl`: a single JSON object conforming to the `review-feedback` schema. Feed it to `append` through a quoted heredoc placed **directly on the `python3` command**, per the `handoff-append` skill:

   ```bash
   python3 scripts/handoff.py append review-feedback <<'EOF'
   {"type":"review-feedback","req_id":"<req-id>","author":"<your-reviewer-name>","verdict":"<approved|changes_requested|blocked>","findings":[…]}
   EOF
   ```

   Required fields: `type` (`"review-feedback"`), `req_id`, `author` (your reviewer name), `verdict` (`approved` | `changes_requested` | `blocked`), `findings` (array, possibly empty when `verdict: "approved"`).
3. Each finding requires `tag`, `location`, `description`. Add `fix` for `tag: "autofix"`. Add `clarify_target` for `tag: "clarify"`. `severity` (`critical` | `fixable`) is required on `autofix` and `blocked` findings — the next fix round's escalation reads it. The Issue Classification table in [`reference.md`](reference.md) gives the default per category.
4. **Append-only is non-negotiable** — never edit, reorder, or delete prior records.
5. **Verify**: `append` prints the new record's line number on success; a non-zero exit means the record was rejected — fix the record, never the file.
6. Your reply to the caller MUST be exactly one line: `Appended review-feedback (<verdict>) for <req_id>`.
7. Do NOT include review content, summaries, or analysis in your reply. The caller reads the record.

**Why:** when review content lands in the reply instead of the file, the dispatcher cannot route fixes, artifact-owner agents cannot read findings, and the audit trail is lost. Stopping before the append forces the user to re-run the review — this is a recurring reviewer failure mode.

### Example Record

```json
{"type":"review-feedback","req_id":"REQ-XX-099","author":"code-quality-reviewer","verdict":"changes_requested","findings":[{"tag":"autofix","location":"report/summary:142","description":"Loop variable `r` shadows an outer binding of the same name.","fix":"Rename loop variable to `row`.","severity":"fixable"},{"tag":"blocked","location":"report/summary:160","description":"Possible divide-by-zero when the denominator (cache-eligible token count) is 0.","severity":"critical"}],"approved_aspects":["Test naming follows conventions","Errors wrapped with context"]}
```

## Feedback Tags

| Tag | Meaning | Action |
|---|---|---|
| `autofix` | Clear fix, no decision needed | Route to artifact owner |
| `blocked` | Critical issue, must fix before merge | Route to artifact owner; escalate if unclear |
| `escalate` | Needs human decision | Append to `.scratch/escalations.md` |
| `clarify` (with `clarify_target`) | Requirement, design, or review question | Route to the named agent |
| `truncation` | Reviewer reached its planned checkpoint mid-review | Nothing to fix — the record's `blocked` verdict routes the partial findings to the implementer; the re-run cycle re-invokes the reviewer for the unreviewed surface |

Choose the tag by what the finding needs next, not by its severity. `autofix` when the fix is mechanical and decision-free; `blocked` when merging would ship a defect; `escalate` when only a human can decide; `clarify` when the finding is really a question for another agent. The tag is a routing decision — pick the one that moves the finding to whoever can resolve it. `truncation` is reserved for the partial-record checkpoint below — a progress marker, not an escalation; it needs no human and never halts the pipeline.

## Reference Tables

[`reference.md`](reference.md) in this skill directory holds the consult-on-demand tables; read the section you need when the case arises:

- **Quality-Bar Clause Mapping** — the canonical `bar_clause` slug list. Set the optional `bar_clause` on every finding that violates a bar clause; look the slug up there.
- **Artifact Ownership** — which agent owns the fix for each artifact.
- **Root-Applied Autofix Eligibility** — when doc-reviewer may tag `autofix` on the root-applied doc paths (design docs and the PRD).
- **Issue Classification** — default severity and tag per checklist category.
- **Processing Reviews** — the feature-implementer's steps for processing the roster's findings.

## Partial-Artifact Contract

Reviewers carry the verifier half of the partial-artifact contract. Two halves: a Scoping Pre-Check before the first tool call, and a planned checkpoint named in that pre-check.

### Scoping Pre-Check (reviewer)

Before the first tool call, run the three-step pre-check defined in the `tdd-workflow` skill § Scoping Pre-Check — including writing the estimate sentences into the transcript — with three review-surface adaptations:

1. **Read-set:** the latest `build-pass` record for the active `req_id`, then the change set under review — `scripts/changeset.sh --name-only` for the changed files, `scripts/changeset.sh` for their diff (§ Reviewer Read-Set). Do not read the implementer's working memory.
2. **Estimate:** reads (one per changed file plus the durable memory the review checklist points at), the bash commands your review process lists, and the single `review-feedback` append. Add the class sweeps findings will trigger (§ Class-Exhaustive Findings). Each checklist is bounded; single-digit precision suffices.
3. **Decide:** run the two independent checks. **Scope** is semantic and budget-free — does the change span more than one behavior or bounded context? If yes, stop and append a `consultation-request` (`product-requirements-expert` when the slice itself is too big; `system-design-expert` when the diff surface is too broad) without starting the review. **Length** is the only check that reads `toolCallBudget`: an estimate that fits proceeds; one that exceeds it on mechanical surface never re-scopes — proceed with the planned checkpoint below, where a partial `review-feedback` carries the findings so far so the review completes on re-invocation.

### Planned-checkpoint trigger

The model cannot count its own tool calls precisely. The trigger is therefore a **planned checkpoint** named at Pre-Check time, not a running count.

**Choosing the checkpoint.** For a review of K changed files, set the checkpoint at "after reviewing ⌈K/2⌉ files." For a checklist-driven review (security threat model, dynamic-analysis run), set it at "after completing the first half of the checklist steps." Write the checkpoint as one of the Pre-Check sentences before the first tool call.

**At the checkpoint, the decision is unconditional.** If the review is complete, write the final `review-feedback` as normal. If not, **append a partial `review-feedback` record now** with the findings collected so far, then stop. Do not assess "am I close to done" — that assessment is the introspection the contract rejects.

**Partial-record shape.** The `review-feedback` carries:

- `verdict: "blocked"`
- `findings`: every finding collected so far, in their normal shape
- One additional `truncation` finding naming the checkpoint:

```json
{"tag":"truncation","location":"<review surface, e.g. internal/report/>","description":"Reviewer reached planned checkpoint with <unreviewed surface> not yet reviewed. Findings above cover <reviewed surface> only."}
```

The downstream loop (feature-implementer processing findings) sees a real record with inspectable partial progress instead of a missing reviewer. The `truncation` tag is a progress marker, not an escalation: it never touches `.scratch/escalations.md`. § Blocking in `handoff-routing` does not apply to it; that halt is for `escalate` findings — human decisions.

The contract complement to an `approved` `review-feedback` is this `blocked` + truncation finding. Both are first-class outputs of a dispatch; neither is a failure mode. The review-feedback routing (`handoff-routing` Gate 4) already handles `blocked` verdicts by dispatching the feature-implementer for findings processing — no new routing is needed.
