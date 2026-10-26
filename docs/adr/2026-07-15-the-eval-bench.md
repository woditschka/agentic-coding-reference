# The Eval Bench Measures Cost per Pass, Attributed per Transcript File, on One Task Fingerprint

**Status:** Accepted

## Context

Claims about the harness rested on statusline session snapshots: real numbers with no controlled comparison. A release needed one answer: does version X beat version Y on the same work, at what cost? The answer must survive agent-influenced artifacts, since the pipeline under test writes the ledger, the docs, and the patch the measurement reads.

Spend attribution had a bias. The board priced a step by summing transcript messages inside its window, `dispatch-start` to the closing record. A dispatch's first message carries the system prompt and the whole inbound context. It lands before the agent's first tool call appends `dispatch-start`, so every step under-reported, by a factor that varies per agent type. A number wrong by a different factor per agent misranks the agents within a slice.

The trend blended run conditions. In the 2026-08-07 `owners-page-param` cell, r1 to r3 ran Claude Code 2.1.220/.221 without prep-injected bash timeouts and r4 to r6 ran 2.1.222 with them; a +90% delta read as +41%. Fourteen of 30 committed cells spanned an instrument condition, and `TREND.md` is generated, never hand-edited, with no channel for operator commentary.

The three feature prompts were clarified on 2026-08-07 after a discarded run stalled on an undecided control question. Seven versions, v0.1.1 through v0.2.1, were swept only under the earlier prompts, so half the headline series measured prompt ambiguity. Versions are swept once, so the flaw could not age out.

## Options Considered

1. **Composite quality score.** Rejected: hides which tier moved and mixes verified facts with judge opinion.
2. **LLM judge inside the pass bar.** Rejected: the cost series would inherit judge noise.
3. **Partition the trend by SUT epoch.** Rejected: the operator never re-runs versions when the base moves; the epoch is recorded per run and called out instead.
4. **Discard obviously broken runs by judgment.** Rejected: a thumb on the scale. Two pre-commit exceptions exist: a run that never engaged the harness and a task later shown defective.
5. **Cost per pass over a binary machine-verified bar, disaggregated tiers** (chosen).
6. **Treat under-attributed cost as directional.** Rejected: the bias varies by agent type.
7. **Anchor the cost window at the preceding record.** Rejected: in a parallel fan-out the preceding record belongs to another agent.
8. **Append `dispatch-start` at true dispatch time.** Rejected: no agent can stamp a moment before its own first message.
9. **Whole-file attribution** (chosen).
10. **Per-row condition callouts.** Rejected: they fire on 14 of 30 cells and read as background.
11. **Operator notes alone, or hand-editing `TREND.md`.** Rejected: forgetting is the failure mode, and hand edits break the derivation gate.
12. **A mechanical condition line plus a notes file as derivation input** (chosen).
13. **Leave the old-prompt rows, top them up, or delete them.** Rejected: ambiguity across half the span, mixed fingerprints inside one row, or erased provenance.
14. **Re-sweep the old-prompt versions under the current tasks** (chosen).

## Decision

**The bench measures cost per pass: agent spend per repetition clearing a binary, machine-verified bar, on frozen tasks against one fixed SUT, per harness version. The transcript file is the unit of cost attribution. The trend carries a mechanical condition callout and operator notes. Every row holds one task fingerprint.**

- **The bar and the tiers.** Frozen tasks with held-out oracles run against spring-petclinic; each version installs from its own tag via the marketplace channel. Pass is oracle-pass plus suite-green plus run-complete, never a judge score. Tier A is machine-verified and carries claims; Tier B is deterministic proxies for context. Tier C is a blind LLM judge, advisory, on a sanitized patch with a pinned rubric and model, median of independent samples. Run folders are the ground truth; `TREND.md` is derived and every rendered field is scrubbed.
- **Whole-file attribution.** Claude Code writes one subagent transcript per dispatch, so a file is a dispatch. A step's window selects the files it overlaps and sums each in full. The scope is the step lines; the header roll-up pairs no dispatch and stays message-windowed. Duration keeps its `dispatch-start` anchor. A step's figure is exact only while no two dispatches of one agent type overlap, a property of the roster, not the attribution. `since_secs` prunes on file mtime.
- **The condition callout is mechanical.** A record spanning several executing Claude Code versions or prep conditions gets one page-level line with counts and range, mirroring the multi-base callout.
- **Notes are input data.** `evals/results/notes.toml` holds dated prose with an optional `task` or `task` plus `version` scope, rendered under the task's table. Note text meets the documentation standards. A malformed note or one naming an absent task or cell aborts the render. Figures never come from notes.
- **One fingerprint per row.** v0.1.1, v0.1.18, v0.1.22, v0.1.28, v0.1.29, v0.2.0, and v0.2.1 were re-measured under the current tasks, three reps per cell, judge on, one epoch. The superseded folders and their notes left the tree with the campaign commit; git history is the citable form.
- **Era arms gate on engagement, not convergence.** `--era-contract` swaps the workspace rules file and `layout.toml` for the version's own skeletons. It appends a channel chapter and a pipeline-entry instruction to the rules file and the system prompt, and roots the arm on the version's era model pin. The judge model stays pinned bench-wide. A run whose ledger holds no record is `no-pipeline`; one ending on an unanswered `dispatch-start` is `truncated-pipeline`; both quarantine. Convergence is a measurand recorded in `result.pipeline.incomplete`, never a gate. The refusal task is exempt from the no-pipeline gate. The campaign runs as one version-interleaved invocation, since the marketplace registration is a single user-scope writer.

## Consequences

**Positive**
- Version comparisons share tasks, bar, and recorded spend; measurement spend never enters the metric.
- A step's figure is its dispatch's real cost; a slice resumed in a later session attributes.
- An instrument boundary marks itself, and the regression story lives beside the figures, versioned. A note edit without a regenerate fails `--check`.
- Cost deltas across the 2026-08-07 boundary attribute to the harness, not the prompt wording.

**Negative**
- Statistical power is low: few tasks, three reps per cell. A cross-version delta can include SUT drift; the manifests attribute it.
- The header and the lines price a dispatch by different rules and do not reconcile. The `change-grader` is dispatch-exempt and attributes to no line.
- A single corrupt transcript timestamp widens a span into windows the dispatch never ran in; nothing bounds it.
- The page-level line does not localize reps; note figures are not validated against derived figures; a dev-only cell cannot carry a note.
- The re-baseline cost about $750 to $1,100 for about 105 reps at about $53 per version rep-set.
- A v0.1.1 rep under two executor generations stopped at the same unconverged doc-reviewer verdict: prose-enforced routing failing, recorded as measured behavior.

## Implementation

`evals/run_eval.py`, `evals/summarize.py` (`Note`, `validate_notes`, `conditions_line`), `evals/results/notes.toml`, `evals/results/runs/`, `evals/README.md`; `tools/harness-stats/accounting.py` (`WindowIndex`, `_overlapping`, `slice_totals`) with its battery-gated vendored copy at `harness/core/scripts/accounting.py`.

## References

- [Resilience-first improvement doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — the bench supplies the measured evidence the doctrine's demotion bar demands.
- [Review convergence](2026-07-14-review-convergence.md) — the dropped finding, the regression split, and the refusal flakiness this instrument surfaced.
- [The change-grader](2026-06-05-the-change-grader.md) — the dispatch-exempt node that attributes to no step line, and the vocabulary the eval reader maps.
- [Confined agent tools](2026-07-16-confined-agent-tools.md) — the claude-dev confinement the bench runs agents and the judge inside.
- [The handoff ledger](2026-05-08-the-handoff-ledger.md) — append-stamped timestamps, which place a cost window mid-dispatch.
- [Documentation standards](2026-06-13-documentation-standards.md) — the bar note prose meets.
- [`evals/README.md`](../../evals/README.md) — methodology, tiers, epoch rules, and the single-invocation doctrine.
