# One Feature Through the Agent Team

Everything on this page happened on 2026-08-15, between 20:22 and 20:42 UTC. The eval bench handed **agent-team**, the specialist team this reference ships, a one-paragraph bug report against Spring PetClinic. Seventeen minutes of agent time and $8.21 later, a reviewed, documented, merge-ready fix stood at the end of a 30-record ledger. One critical specification defect was caught and corrected on the way. The run is committed in full as rep r1 of the [`owners-page-param` eval task](../evals/results/runs/v0.3.3/2026-08-15-owners-page-param-r1/README.md), harness v0.3.3. Nothing here is schematic; every claim links the committed artifact it stands on. Quoted passages reproduce agent-authored ledger content verbatim (untrusted text), with elisions marked […].

**The run is committed:** [run folder](../evals/results/runs/v0.3.3/2026-08-15-owners-page-param-r1/) — every artifact linked in [Reading the Run](#reading-the-run).

## The Run

Line numbers refer to [`handoff.jsonl`](../evals/results/runs/v0.3.3/2026-08-15-owners-page-param-r1/handoff.jsonl), the append-only log the team coordinates through; timestamps are the records' own.

**20:22 — intake.** The bench submits the frozen task prompt, the run's entire human input:

> Bug report: opening /owners?page=0 — or any page value below 1 — renders the error page instead of the owner list. Expected behavior: the owner listing treats any page value below 1 as the first page and responds with the normal listing (HTTP 200). Find the cause, fix it, and cover the fix with a test.

It lands verbatim as the ledger's first record, an `intake-decision`. Every scope judgment that follows traces back to this quoted text; no human is consulted again until the end.

**20:24 — requirements.** The product-requirements-expert records `REQ-OWNERSPAGEPARAM-001` (line 3): four given/when/then acceptance criteria, three named tests, three non-goals. Two of the non-goals are open questions (non-integer page values, the veterinarian directory's paging), parked as undecided rather than silently decided.

**20:26 — design triage.** The system-design-expert answers `covered` (line 5): no new design needed. The paging contract already lives in `system-design.md`, and `security-principles.md` already places range checks at the trust boundary. The durable documents carried the design, so the run did not have to. The design block names the exact helper to change (`OwnerController.java:133`) and two risks. The sharper one: clamp the query but not the model, and the page renders a "previous" link to page 0.

**20:31 — implementation.** The feature-implementer lands the fix through the TDD inner loop: 10 production lines (a `FIRST_PAGE` constant and one clamp) and 55 test lines. The `build-pass` record (line 7) lists six green gate checks.

**20:32 — review sizing.** A script classifies the change `gray` and defers to the review-planner. The planner sizes it `low` in 17.5 seconds for $0.14 (line 10) and names three reviewers. The security-reviewer is excluded for a recorded reason: the clamp opens no new input path.

**20:34 — the catch.** Three reviewers run in parallel. The code-quality-reviewer approves. The test-reviewer requests changes: two copy-paste tests, differing only in the page value, should be one parameterized test. The doc-reviewer finds the defect of the round (line 14, severity `critical`). The PRD, written before implementation and never retracted, still records the bug as current fact inside the diff that fixes it:

> Edge case 5 states as current fact: "A page below the first one renders the error page today instead of the listing." This directly contradicts edge case 4 on the line above it and the three new REQ-OWNERSPAGEPARAM-001 'Done when' bullets […] — and it contradicts the shipped code and passing tests in this same diff […]. A reader relying on this document to understand current behavior is misled.

No compiler or test suite detects a specification that contradicts its own change. The catch exists because `prd.md` is an owned artifact a reviewer holds to a written bar.

**20:35 — two fixes, routed by ownership.** Each finding goes to the owner of the touched artifact. The doc finding goes to the product-requirements-expert, who owns `prd.md`; the test finding to the feature-implementer. Both run in parallel. The superseding `prd-entry` (line 18) deletes the stale edge case and records the reason in its notes: "Edge case 5 is deleted; no other doc cites the Owner records edge-case numbering […] Requirement scope, acceptance criteria, and non-goals are unchanged." The implementer merges the twin tests; by 20:37 the second `build-pass` shows eight green checks.

**20:37 — escalation.** The review-plan engine plans the re-review with the open `critical` finding in its recorded basis and draws the full four-reviewer roster on the fix delta (line 20). The plan's author field reads `review-plan-engine`: a script escalated, not a model.

**20:38 — approval, residuals on the record.** All four reviewers approve. The security-reviewer's approval still attaches two recommendations (line 28). No dependency scan ran: the project carries no scan tooling, recorded as "not run, not clean" rather than silently skipped. The page parameter also has no upper clamp, so `/owners?page=2147483647` reaches the database unclamped. Both predate the change; both stay on the record so they are not lost.

**20:39 — the grade.** The change-grader scores five facets from the diff and the ledger (line 30). Four score `clear`; `reviewer_hedging` scores `concern`:

> The fix itself reads clean: one clamp, threaded to both consumers, with tests that fail without it. What deserves a look is the security reviewer's parked residual on its approval - no dependency scan ran, and the page parameter is still unbounded above. Both are pre-existing, neither blocks; decide whether to log them.

The verdict routes nothing and merges nothing. The ledger ends here; the merge click belongs to the human.

**20:42 — the bench's verdict.** Outside the team, the bench verifies the change independently: the held-out oracle passes 3/3 and the full suite stays green. A blind three-sample judge scores design-fit 4, test-quality 4, maintainability 4, doc-fit 5, with dissents recorded per sample. Methodology: [`evals/README.md`](../evals/README.md); the cost series across harness versions: [`TREND.md`](../evals/results/TREND.md).

Three mechanisms stayed idle in this run. No consultation roundtrip fired; the bench's `visit-cancel` task shows that path, ending after three records in a recorded [consultation pause](../evals/results/runs/v0.3.3/2026-08-15-visit-cancel-r1/README.md) instead of a guessed answer. No dispatch hit its tool-call cap, so [truncation recovery](agentic-harness.md#dispatch-event-contract-and-recovery-paths) stayed unused. And review converged in two rounds, inside the three-round ladder of [ADR 2026-08-11](adr/2026-08-11-bounded-review-convergence.md).

## The Ledger

All 30 committed records of `handoff.jsonl`, in append order. Line number is identity in the append-only log. The log is reproduced as recorded, blemishes included: the doc-reviewer's round-1 `dispatch-start` is absent, and three reviewer dispatch-starts carry sentinel `responding_to` values.

| # | Record | Author | What it carries |
|---|--------|--------|-----------------|
| 1 | `intake-decision` | human | The bug report, quoted verbatim |
| 2 | `dispatch-start` | product-requirements-expert | Woken on line 1 |
| 3 | `prd-entry` | product-requirements-expert | `REQ-OWNERSPAGEPARAM-001`: 4 acceptance criteria, 3 non-goals, 2 open questions |
| 4 | `dispatch-start` | system-design-expert | Woken on line 3 |
| 5 | `design-block` | system-design-expert | Verdict `covered`; names the helper and the pager risk |
| 6 | `dispatch-start` | feature-implementer | Woken on line 5 |
| 7 | `build-pass` | feature-implementer | Six gate checks green |
| 8 | `review-plan` | review-plan-engine | Risk `gray`; roster deferred to the planner |
| 9 | `dispatch-start` | review-planner | Woken on line 8 |
| 10 | `review-plan` | review-planner | Risk `low`; 3 reviewers; security-reviewer excluded with rationale |
| 11–12 | `dispatch-start` ×2 | reviewers | Parallel fan-out; the doc-reviewer's start is missing from the log |
| 13 | `review-feedback` | code-quality-reviewer | `approved` |
| 14 | `review-feedback` | doc-reviewer | `changes_requested` — `blocked`/`critical`: the PRD records the fixed bug as current fact |
| 15 | `review-feedback` | test-reviewer | `changes_requested` — `autofix`: copy-paste twin tests |
| 16 | `dispatch-start` | feature-implementer | Fix dispatch, responding to 13 and 15 |
| 17 | `dispatch-start` | product-requirements-expert | Fix dispatch, responding to 14 |
| 18 | `prd-entry` | product-requirements-expert | Supersedes line 3; deletes the stale edge case; notes record the reason |
| 19 | `build-pass` | feature-implementer | Eight gate checks green |
| 20 | `review-plan` | review-plan-engine | Fix pass; open `critical` finding in the basis; risk `high`; full roster |
| 21–24 | `dispatch-start` ×4 | reviewers | The full battery, in parallel |
| 25–28 | `review-feedback` ×4 | reviewers | All `approved`; the security approval carries two recorded residuals |
| 29 | `grader-features` | change-grader | Deterministic diff facts: 10 prod lines, 48 test lines, ratio 4.8 |
| 30 | `grader-verdict` | change-grader | `concern` on reviewer hedging; the merge stays human |

## Reading the Run

The [run folder](../evals/results/runs/v0.3.3/2026-08-15-owners-page-param-r1/) commits every artifact:

- [`handoff.jsonl`](../evals/results/runs/v0.3.3/2026-08-15-owners-page-param-r1/handoff.jsonl) — the 30-record ledger this page narrates
- [`change.patch`](../evals/results/runs/v0.3.3/2026-08-15-owners-page-param-r1/change.patch) — the full diff the team produced
- [`agent-costs.json`](../evals/results/runs/v0.3.3/2026-08-15-owners-page-param-r1/agent-costs.json) — per-agent cost, model, and wall-clock breakdown
- [`result.json`](../evals/results/runs/v0.3.3/2026-08-15-owners-page-param-r1/result.json) — the bench's machine-verified verdict
- [`README.md`](../evals/results/runs/v0.3.3/2026-08-15-owners-page-param-r1/README.md) — the run page: oracle results, checkpoints, judge scores

This page narrates; it defines nothing. The canonical statements live in their owning documents:

- the loop model, slices, and handoff contract — [`agentic-harness.md`](agentic-harness.md)
- routing rules and gates — the [`handoff-routing` skill](../harness/core/.claude/skills/handoff-routing/SKILL.md)
- review tags, severities, and verdicts — the [`review-workflow` skill](../harness/core/.claude/skills/review-workflow/SKILL.md)
- the five grading facets — the [`change-grading` skill](../harness/core/.claude/skills/change-grading/SKILL.md)
- the documentation bar the doc-reviewer enforced — the [`document-writing` skill](../harness/core/.claude/skills/document-writing/documentation-standards.md)
- the bench methodology — [`evals/README.md`](../evals/README.md)
- the working vocabulary — the [glossary](glossary.md)
