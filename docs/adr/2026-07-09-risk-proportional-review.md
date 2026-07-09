# Risk-Proportional Review Dispatch

**Status:** Accepted

## Context

Gate 3 dispatches the full reviewer roster — the four-reviewer floor plus extras — after every `build-pass`. Gate 4 re-runs the whole roster on every fix cycle. A slice therefore costs `cycles × (4 + extras)` reviewer dispatches, each re-reading the full slice diff plus the durable docs. A docs-only typo pays the same four dispatches as a cross-module change; a two-cycle fix pays eight.

The parallel dispatch keeps wall-clock near one reviewer; tokens are the multiplier. And the inputs for a cheaper decision already exist deterministically. `score-change.py` classifies the changeset — file kinds, modules, sensitive paths, line deltas, tree SHA. `.scratch/handoff.jsonl` records what was approved, what was not, each finding's `location` and `bar_clause`, and the slice's retry history. A human reviewer estimates risk from exactly these facts before deciding how much review to buy. The pipeline never did.

## Options Considered

1. **Focused loop with an unconditional final full battery.** Iterate against one focused reviewer; run the full roster once after it approves. Rejected: the final battery is a fixed four-dispatch tax paid at the slice's cleanest state. A clean docs typo rises from 4 dispatches to 5; a two-cycle fix from 8 to 10.
2. **LLM triage on every pass.** An agent reads each diff and picks the roster. Rejected: pays one dispatch to re-derive decisions the changeset features settle deterministically, on every pass.
3. **Pipeline-coordinator as the risk judge.** Rejected on three pinned contracts: the coordinator never writes records, never reads source, and carries a 14-tool-call budget sized for table lookups. Risk judgment is diff-reading judgment — a different agent.
4. **Risk-proportional dispatch** (chosen): a deterministic engine decides the clear cases and pre-extracts the facts; a budget-bounded planner agent judges only the gray zone; fix cycles re-dispatch from the log's approval data; correction paths are additive-only.

## Decision

**Review investment is proportional to a logged risk estimate. A `review-plan` record — authored by a deterministic engine for clear cases and by a `review-planner` agent for the gray zone — names each pass's roster and read scope. `route` dispatches exactly that roster. The full battery is the fail-closed default whenever no plan exists, any input is unclassifiable, or any estimate errs.**

- **The engine decides for free.** `score-change.py review-plan` computes the changeset features and the log history, applies the risk ladder, and appends one `review-plan` record (author `review-plan-engine`). Clear-low emits a surface-matched roster: a reviewer joins a pass only when the changeset contains surface that its dimension judges. Clear-high — sensitive paths, multiple modules, unclassified paths, binary files, over-threshold size, or noisy slice history (build retries, superseded designs, prior critical findings) — emits the full roster. Any null feature is high.
- **The gray zone buys one small judgment.** When the ladder cannot decide, the engine emits `risk: "gray"` with no roster, and `route` dispatches the `review-planner`: a coordinator-shaped agent (low effort, tight `toolCallBudget`) that reads the hunks via `scripts/changeset.sh` and appends the final plan with a rationale. Only the engine may emit `gray`, so triage terminates in one hop.
- **The record carries its own facts.** The plan's `basis` holds the tree SHA, the per-file classification, the history facts, and each dissenter's open findings — the `grader-features` pattern repeated. The planner judges pre-extracted facts plus the diff; it never mines the log or the implementer's narrative. For high-risk plans the basis carries trigger counts, not file rosters, keeping records proportional to the decision.
- **Fix cycles re-review the delta.** Successive plans' tree SHAs define the fix delta deterministically. Dissenting reviewers re-run; a reviewer whose open finding's `bar_clause` implicates another dimension pulls that reviewer back in; approvals stand while the fix delta stays inside the open findings' files or the reviewed surface. A fix that escapes both re-runs the full roster. Re-dispatched reviewers receive their own open findings and the fix hunks, not the whole slice diff.
- **Routing stays log-pure and pinned.** The feature-implementer runs the engine as the final step of gate-pass — right after `build-pass` — so `route` never touches the worktree; it only reads the resulting record. `route` then resolves the pass roster: a rostered `low`/`high` plan dispatches its roster, a `gray` plan dispatches the planner (with a stall ladder), and a missing or invalid plan fails closed to the full battery — the pre-plan behavior, so old logs and non-adopting projects are unaffected. Gate 4 waits on the resolved roster; feature-complete requires the latest verdict of every reviewer dispatched since the current `design-block` to read `approved`, enforced by `route` re-dispatching any prior dissenter a plan dropped. A re-triage re-runs the full battery through the `design-revision` trigger, so a superseded-cycle dissent is re-covered by that escalation rather than this gate. `test_handoff.py` pins each rule.
- **Correction is additive-only.** A dispatched reviewer widens the roster via `clarify` naming another reviewer. The `change-grader` is plan-aware: its `review_roster` feature names the reviewers a pass dispatched, so a floor reviewer silent under a focused plan is expected, not a hedge. Its advisory `concern` on a passing focused slice surfaces to the human as the terminal backstop. No path removes a reviewer from a pass already planned. (Automatic escalation from a `concern` verdict into a full-battery round is future work — see Consequences.)
- **The floor's membership is untouched; its dispatch clause is amended.** The four reviewers stay harness-owned, doctor-enforced, and non-subtractable per [the additive reviewer roster](2026-06-18-additive-reviewer-roster.md). What changes is when each runs: the full battery becomes the fail-closed default rather than the unconditional rule. `layout.toml [review]` declares the `docs`/`config` kind globs, the size threshold, the surface-to-roster map, and `mode = "always-full"` as the opt-out reproducing prior behavior.

## Consequences

**Positive:**
- A docs-only change costs 1 reviewer dispatch instead of 4. A gray-zone two-cycle fix costs about 5–6 dispatches (planner included) instead of 8. A risky slice costs exactly what it costs today.
- Every cheap path is auditable: the plan's `basis` shows the facts behind each roster, and the planner's rationale is one logged line.
- Re-review reads shrink from the whole slice diff to the fix delta plus the reviewer's own open findings.
- The troubled cases self-escalate: retry-laden or design-churned slices classify high before any judgment runs.

**Negative:**
- A dimension can be affected without owning changed surface — a code fix can stale the docs no diff line touches. Accepted with four named bounds: the size threshold, history escalation, additive widening, and the plan-aware grader's advisory `concern` on a passing focused slice.
- The planner can under-estimate gray-zone risk. Accepted: its facts are pre-extracted and logged, correction paths are additive-only, and the grader's cold read runs on every passing slice.
- One new record type, one new agent, and the Gate 5 route rules widen the machinery. Accepted: each rule is fixture-pinned, and the engine reuses `score-change.py`'s existing snapshot, classifier, and log reader.
- A fix cycle on a slice whose *whole* accumulated diff exceeds the size threshold (or spans modules) trips `high` and re-runs the full roster, because the engine sizes risk over the diff against `HEAD`, not the fix delta. This under-delivers the dissenters-only saving on large slices — but it fails closed, and the `fix-delta` read scope still shrinks each reviewer's input. Sizing fix-cycle risk over the delta is a future refinement.

## References

- [Additive Reviewer Roster](2026-06-18-additive-reviewer-roster.md) — the membership floor this decision keeps; its unconditional-dispatch clause is what this ADR amends.
- [Deterministic Mid-Slice Routing](2026-07-06-deterministic-mid-slice-routing.md) — the two-part router this extends: tables decide, agents judge only what tables cannot.
- [Change-Grade Extractor Reads the Worktree](2026-06-05-change-grade-extractor-worktree.md) and [The Change-Grader](2026-06-05-change-grader.md) — the facts-extracted-for-judgment pattern the `review-plan` record repeats, and the terminal cold read that, now plan-aware, is the backstop for a focused pass.
- [Fresh-Eyes Review of the Changeset](2026-06-21-fresh-eyes-review-changeset.md) — the read-set discipline the planner and delta re-reviews preserve.
- [Append-Only JSONL Handoffs](2026-05-08-append-only-jsonl-handoffs.md) — the ledger every risk estimate enters as one validated record.
