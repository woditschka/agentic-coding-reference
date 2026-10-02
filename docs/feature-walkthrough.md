# One Feature Through the Agent Team

Everything on this page happened on 2026-09-30, between 22:01 and 22:14 UTC. The eval bench handed **agent-team**, the specialist team this reference ships, a one-paragraph bug report against Spring PetClinic. Ten minutes and $3.90 later, grading included, a reviewed, documented, merge-ready fix stood at the end of a 29-record ledger. One paging regression, invisible to a green test suite, was caught and corrected on the way. The run is committed in full as rep r2 of the [`owners-page-param` eval task](../evals/results/runs/v0.4.8/2026-10-01-owners-page-param-r2/README.md), harness v0.4.8, on Claude Opus 5.5 and Sonnet 5.5. The folder name carries the bench host's local date. Nothing here is schematic; every claim links the committed artifact it stands on. Quoted passages reproduce agent-authored ledger content verbatim (untrusted text), with elisions marked […].

**The run is committed:** [run folder](../evals/results/runs/v0.4.8/2026-10-01-owners-page-param-r2/) — every artifact linked in [Reading the Run](#reading-the-run).

## The Run

Line numbers refer to [`handoff.jsonl`](../evals/results/runs/v0.4.8/2026-10-01-owners-page-param-r2/handoff.jsonl), the append-only log the team coordinates through; timestamps are the records' own.

**22:02 — intake.** The bench submits the frozen task prompt, the run's entire human input:

> Bug report: opening /owners?page=0 — or any page value below 1 — renders the error page instead of the owner list. Expected behavior: the owner listing treats any page value below 1 as the first page and responds with the normal listing (HTTP 200). Find the cause, fix it, and cover the fix with a test.

It lands verbatim as the ledger's first record, an `intake-decision`. Every scope judgment that follows traces back to this quoted text; no human is consulted again until the end.

**22:03 — requirements.** The product-requirements-expert records `REQ-OWN-005` (line 3): three given/when/then acceptance criteria, one named test, three non-goals. The third criterion holds the existing behavior in place: a request for page 1 or above "behaves as it does today". The non-goals are open questions (a page beyond the last, a non-numeric page value, page size and the veterinarian directory's paging), "left open deliberately rather than declined".

**22:04 — design triage.** The system-design-expert answers `covered` (line 5): no new design needed. `architecture-principles.md` already classes range normalization of a request parameter as binding, so the clamp belongs in `OwnerController`. The durable documents carried the design, so the run did not have to. The design block names the cause, `PageRequest.of(page - 1, pageSize)` throwing for an index below zero, and three risks. The sharpest one: clamp only the query argument, and `currentPage` stays at 0 and breaks the pagination links. The block also rates the code work `routine`. Its notes record the identical fault in `VetController` as a candidate follow-up slice, because the requirement declares vet paging a non-goal.

**22:06 — implementation.** The `routine` rating selects the implementer's routine tier ([model-tier ADR, third amendment](adr/2026-06-11-model-tier-assignment.md#amendment-2026-09-30-the-effort-pins-move-and-routine-implementation-joins-the-checklist-tier)). The first pass runs on Sonnet 5.5 through the TDD inner loop: 2 minutes 20 seconds, $0.24, 5 production lines, 22 test lines. The `build-pass` record (line 7) lists seven green gate checks. One of the five production lines carries a slip: the handler parameter `page` is now named `requestedPage`.

**22:06 — review sizing.** The review-plan engine, a script, plans the review in the same second (line 8). `OwnerController` is a declared security surface, so the plan rates the risk `high` and draws all four reviewers. No model is consulted.

**22:07 — the catch.** Four reviewers run in parallel. The doc-reviewer approves. The other three land on `OwnerController.java:95` independently, within 28 seconds. The code-quality-reviewer states the defect (line 13, severity `critical`):

> Renaming the handler parameter to `requestedPage` changes the bound query parameter. `@RequestParam(defaultValue = "1")` carries no explicit name, so Spring binds by the Java parameter name, now `requestedPage`. Every `?page=N` link in owners/ownersList.html […] stops binding and silently falls back to page 1, so REQ-OWN-002 paging is broken for pages 2 and up.

The test-reviewer records why the suite stayed green (line 15): "Every page= test in the suite uses page=1 […] and the new test only sends 0 and -1, so all of them pass despite the regression." The security-reviewer adds that the new test proves nothing (line 16): it "passes only because the value never reaches the handler and the default of 1 applies, not because the clamp ran."

The build compiled, every test passed, and the page from the bug report rendered. The regression broke existing behavior, the paging of `REQ-OWN-002`, on every page above 1, and no test requested one. The catch exists because the reviewers read the diff against the templates that send `?page=N`, not against the suite.

**22:07 — one fix, the full tier.** Findings route by the artifact they touch. None touches `prd.md` or `system-design.md`, so one dispatch goes to the feature-implementer (line 17). The round mixes `blocked` and `autofix` findings, which routes it to the full implementer on Opus 5.5: 2 minutes 37 seconds, $0.49. The fix names the request parameter explicitly, `@RequestParam(name = "page", defaultValue = "1")`, and adds a `page=2` test that would fail under the round-1 binding. It also closes the test-reviewer's two `autofix` findings: a behavior-style test name and a named default in place of a bare `new Owner()`. At 22:10 the second `build-pass` (line 18) shows the same seven checks green; the plan that follows sizes the change at 44 test lines.

**22:10 — escalation.** The review-plan engine plans the re-review with all six round-1 findings in its recorded basis (line 19). Three of them are `critical`, so the `prior-critical` trigger draws the full four-reviewer roster on the fix delta. The plan's author field reads `review-plan-engine`: a script escalated, not a model.

**22:11 — approval, residuals on the record.** All four reviewers approve within 18 seconds. The security-reviewer sweeps the source tree for other unnamed `@RequestParam` declarations (line 26). It finds one, in `VetController`, whose Java parameter name already equals the query name. Its approval also records the scan that did not happen: "dependencyCheckAnalyze was not run, so no NVD match was performed." The test-reviewer's approval attaches two recommendations (line 27). The coverage map still lists the test under its pre-rename name, and one assertion checks a single field of the page request. Neither blocks; both stay on the record so they are not lost.

**22:11 — the grade.** The change-grader scores five facets from the diff and the ledger (line 29). Four score `skim`; `reviewer_hedging` scores `scrutinize`, and the worst facet sets the verdict:

> The code change is small, contained and well tested; the round-1 page-binding regression is fixed and pinned by a page=2 test. The flag comes only from the test-reviewer's late-round recommendations: before merging, confirm that the stale declared test name in the coverage map gets updated, then a quick read of the controller hunk is enough.

The verdict routes nothing and merges nothing. The ledger ends here; the merge click belongs to the human.

**22:14 — the bench's verdict.** Outside the team, the bench verifies the change independently: the held-out oracle passes 3/3 and the full suite stays green. A blind three-sample judge scores design-fit 5, test-quality 4, maintainability 4, doc-fit 5, with each sample's rationale on the run page. Methodology: [`evals/README.md`](../evals/README.md); the cost series across harness versions: [`TREND.md`](../evals/results/TREND.md). The series lists this rep at its delivery figures, $3.65 and 9 minutes, with the grader's $0.24 netted out.

The bar would not have caught the round-1 slip. The oracle requests pages 1, 0, and -3, each of which the broken binding served as page 1. The bar is a floor under the change; the review loop is what read the paging links. The slip is also one rep's: the sweep's sibling reps, [r1](../evals/results/runs/v0.4.8/2026-09-30-owners-page-param-r1/README.md) and [r3](../evals/results/runs/v0.4.8/2026-10-01-owners-page-param-r3/README.md), cleared the same task for $2.38 and $3.08, grading included, without it. It is not the series' first: [v0.2.2 r3](../evals/results/runs/v0.2.2/2026-08-30-owners-page-param-r3/README.md) shipped the same unnamed rename and cleared the bar.

Four mechanisms stayed idle in this run. No consultation fired; the bench's `visit-cancel` task shows a request, ending after three records in a recorded [consultation pause](../evals/results/runs/v0.4.8/2026-09-30-visit-cancel-r1/README.md) instead of a guessed answer. The review-planner was never dispatched: the engine sized both review passes itself. No dispatch was cut off mid-work, so [truncation recovery](agentic-harness.md#dispatch-event-contract-and-recovery-paths) stayed unused. And review converged after one fix round, inside the three-round ladder of [ADR 2026-08-11](adr/2026-08-11-bounded-review-convergence.md).

## The Ledger

All 29 committed records of `handoff.jsonl`, in append order. Line number is identity in the append-only log. The ledger names both implementer passes `feature-implementer`; the tier each one ran on is recorded per window in `agent-costs.json`. The log is reproduced as recorded, blemishes included. The code-quality-reviewer's round-1 `dispatch-start` carries a sentinel `responding_to` value. Its feedback also records that the review procedure names a Gradle format task the project does not define.

| # | Record | Author | What it carries |
|---|--------|--------|-----------------|
| 1 | `intake-decision` | human | The bug report, quoted verbatim |
| 2 | `dispatch-start` | product-requirements-expert | Woken on line 1 |
| 3 | `prd-entry` | product-requirements-expert | `REQ-OWN-005`: 3 acceptance criteria, 1 named test, 3 open non-goals |
| 4 | `dispatch-start` | system-design-expert | Woken on line 3 |
| 5 | `design-block` | system-design-expert | Verdict `covered`; effort `routine`; names the cause and the pagination-link risk |
| 6 | `dispatch-start` | feature-implementer | Woken on line 5; the routine tier |
| 7 | `build-pass` | feature-implementer | Seven gate checks green |
| 8 | `review-plan` | review-plan-engine | First pass; trigger `security-surface`; risk `high`; full roster |
| 9–12 | `dispatch-start` ×4 | reviewers | Parallel fan-out |
| 13 | `review-feedback` | code-quality-reviewer | `changes_requested` — `blocked`/`critical`: the rename drops the `page` binding; one `autofix` on the review's own format command |
| 14 | `review-feedback` | doc-reviewer | `approved` |
| 15 | `review-feedback` | test-reviewer | `changes_requested` — `blocked`/`critical`: no test requests a page above 1; two `autofix` findings |
| 16 | `review-feedback` | security-reviewer | `changes_requested` — `autofix`/`critical`: the same regression; the new test passes on the default |
| 17 | `dispatch-start` | feature-implementer | Fix dispatch, responding to 13, 15, and 16; the full tier |
| 18 | `build-pass` | feature-implementer | Seven gate checks green |
| 19 | `review-plan` | review-plan-engine | Fix pass; six open findings in the basis; trigger `prior-critical`; full roster on the fix delta |
| 20–23 | `dispatch-start` ×4 | reviewers | The full battery, in parallel |
| 24–27 | `review-feedback` ×4 | reviewers | All `approved`; the test-reviewer's approval carries two recommendations |
| 28 | `grader-features` | change-grader | Deterministic diff facts: 5 prod lines, 44 test lines, ratio 8.8 |
| 29 | `grader-verdict` | change-grader | `scrutinize` on reviewer hedging; the merge stays human |

## Reading the Run

The [run folder](../evals/results/runs/v0.4.8/2026-10-01-owners-page-param-r2/) commits every artifact:

- [`handoff.jsonl`](../evals/results/runs/v0.4.8/2026-10-01-owners-page-param-r2/handoff.jsonl) — the 29-record ledger this page narrates
- [`change.patch`](../evals/results/runs/v0.4.8/2026-10-01-owners-page-param-r2/change.patch) — the full diff the team produced
- [`agent-costs.json`](../evals/results/runs/v0.4.8/2026-10-01-owners-page-param-r2/agent-costs.json) — per-agent cost, model, and wall-clock breakdown
- [`result.json`](../evals/results/runs/v0.4.8/2026-10-01-owners-page-param-r2/result.json) — the bench's machine-verified verdict
- [`README.md`](../evals/results/runs/v0.4.8/2026-10-01-owners-page-param-r2/README.md) — the run page: oracle results, checkpoints, judge scores

This page narrates; it defines nothing. The canonical statements live in their owning documents:

- the loop model, slices, and handoff contract — [`agentic-harness.md`](agentic-harness.md)
- routing rules, gates, and the implementer tier ladder — the [`handoff-routing` skill](../harness/core/.claude/skills/handoff-routing/SKILL.md)
- review tags, severities, and verdicts — the [`review-workflow` skill](../harness/core/.claude/skills/review-workflow/SKILL.md)
- the five grading facets — the [`change-grading` skill](../harness/core/.claude/skills/change-grading/SKILL.md)
- the documentation bar the doc-reviewer enforced — the [`document-writing` skill](../harness/core/.claude/skills/document-writing/documentation-standards.md)
- the bench methodology — [`evals/README.md`](../evals/README.md)
- the working vocabulary — the [glossary](glossary.md)
