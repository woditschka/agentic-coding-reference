# Review Convergence: Delta-Sized Fix Rounds, Bounded at Three, Scope Locked to the Owner's Words

**Status:** Accepted

## Context

Risk-proportional dispatch sized a fix round's risk over the accumulated diff against `HEAD`. A slice that tripped `oversize` or `multi-module` stayed there while its fix deltas shrank to a few lines. A three-round slice paid three full batteries where the intent was dissenters-only re-review. Re-dispatching a reviewer over surface it already read re-samples its judgment. Each round clears the prior findings and reports new ones of the same class on unchanged surface, and every late instance buys another round.

The record contract allowed findings on an `approved` verdict while Gate 4 processed findings only from non-approved ones. The bench's first sweep recorded the result: an `autofix` finding dropped silently, then re-raised as a `changes_requested` dissent one round later.

Build failures re-triage at the third retry and truncation at the third silent dispatch, but review fix rounds had no bound. Inspection studies find each further pass removes fewer defects while fixes inject new ones; model reviewers produce plausible minor findings indefinitely, so finding supply can never be the stop signal. The bench's runs peak at 2 rounds on v0.2.2 to v0.2.4; the 3 to 4-round tail sits on v0.1.x to v0.2.1.

A loop can also converge on the wrong target. The bench's `visit-cancel` task asks for work conflicting with two recorded Non-Goals and states no owner override; the designed outcome is a consultation and no change. Refusal rates fell from 4/4 (v0.1.22) to 0/1 (v0.2.1). Every implementing rep ran the boundary check, found both rows, and narrowed them itself via a non-goal ADR, reading the request as the owner's decision. A correct refusal costs about $1.20 in 3 minutes; an implementing rep $15 to $23 in 40 to 65 minutes.

## Options Considered

1. **Round cap with human escalation alone.** Rejected: caps cost only after paying N full batteries and leaves the cause of repetition.
2. **Dissenters-only on every fix pass.** Rejected: fails open on a fix that grows the surface or follows a critical.
3. **Delta-sized escalation plus class-exhaustive findings** (chosen).
4. **Route approved-record autofix findings without flipping the verdict.** Rejected: the carrying record stays the reviewer's latest, so the router re-dispatches forever; a post-approval edit invalidates what the approval covered.
5. **Forbid all findings on approval.** Rejected: `escalate` and `clarify` cross the boundary by design.
6. **Bounce approved records carrying `autofix` or `blocked` findings** (chosen).
7. **Prose-only critical-only guidance.** Rejected: the approved-with-autofix rule was prose first and still needed a gate.
8. **Re-triage at the cap.** Rejected as the destination: a superseding `design-block` resets the cycle, so the loop recurses with no human.
9. **Adaptive stopping on estimated remaining defects.** Rejected: unreliable at this roster size and not replayable from the ledger.
10. **Gate on pass kind instead of a counter.** Rejected: bounds review at two passes and removes the deliberate unrestricted fix round.
11. **A `layout.toml` depth knob.** Rejected: the cap is a structural constant like the retry ladder.
12. **Deterministic ladder with channel escapes and per-loop ceilings** (chosen).
13. **Sharpen the scope prose only.** Rejected: silent narrowing stays representable in the ledger.
14. **Require a human response for every Non-Goals change.** Rejected: a dispatch that states the override would force a pointless round-trip.
15. **Doctrine plus a fail-closed Gate 1 with a dispatch-carried override arm** (chosen).

## Decision

**A fix round computes its escalation from the fix delta, never the accumulated slice. An approved verdict carries no fix-routable finding. A review cycle buys at most 3 fix rounds, after which dissent needs a defect that must not merge or an open channel. A recorded Non-Goals row changes only under the owner's quoted decision; the request is never the override.**

- **Delta triggers on fix passes.** The engine escalates on `delta-sensitive`, `delta-binary`, `delta-unknown-surface`, `delta-oversize` (measured against the first-pass `size_threshold`), `delta-unavailable`, `delta-escaped-surface`, `reviewed-surface-unavailable`, and `prior-critical`. Slice-level triggers govern first passes only. A dissenter-less fix pass falls to the first-pass ladder, fail-closed. A delta escaping into production or unclassifiable files gets the full roster over `full-diff`; an escape confined to docs, test, or config surface widens the pass with that surface's reviewers. A clean contained delta gets the dissenters plus `bar_clause`-implicated reviewers over `fix-delta`. A capped basis recomputes the reviewed surface from git rather than assuming an escape.
- **The review cycle starts at the latest superseding `design-block`.** Dissent is cycle-wide, judged on the latest `review-feedback` per reviewer, so an interrupted round never orphans it. `prior-critical` decays with its reviewer's next verdict.
- **`prior-critical` keys on the critical's surface.** The cold full read stays for a critical on production code or the harness runtime. It stays for one the security reviewer raised or whose clause maps there, and for one whose location cannot be placed. It stays for any critical when the fix delta touches production code. A critical confined to docs, test, or config surface keeps its raiser plus that surface's reviewers. A slice that touched sensitive paths keeps the security reviewer on every fix round.
- **Findings are class-exhaustive.** Before appending, a reviewer sweeps the remaining review surface for further instances of every finding class it recorded, searching literal strings. A planned checkpoint outranks the sweep.
- **The record gate.** Gate 4 rejects an `approved` record whose findings carry `autofix` or `blocked`; the reviewer drops the note or records `changes_requested`. `escalate` and `clarify` stay legal on approval.
- **The round ladder.** The round is 1 plus the earlier passes in the cycle that drew substantive dissent from a roster reviewer; off-roster authors and truncation-only passes never count. From round `REVIEW_ROUND_CAP` (3), a non-approved verdict needs a `critical` fix-routable finding or a `clarify`, `escalate`, or `truncation` finding. Anything else bounces once; a second below-bar record blocks. Polish rides `recommendations` on an `approved` verdict, rendered by the board and read by the grader's hedging facet. One `blocked` rule, `review-non-convergence`, with causes `round-cap`, `bounce-repeat`, `pass-churn` (a reviewer's third dissent inside one pass), and `truncation-run` (three consecutive truncation-only passes). The human overrules, applies findings by hand, or orders the re-triage. Dispatches carry `round` and `finding_bar: "critical-only"` from round 3.
- **Scope lock.** The product-requirements-expert proceeds against a recorded requirement or Non-Goals row only when the dispatch names the row and states the owner's decision. Anything less exits via a `consultation-request` targeting `human`. The `prd-entry` record carries `scope_overrides`: per changed row the `non_goal_id`, the decision quoted verbatim, and a source of `dispatch` or `consultation:<line>` pointing at a human-authored response containing the quote. Gate 1 compares the worktree's Non-Goals rows against `HEAD`: an uncovered change bounces, padding bounces, added rows pass, an unreadable baseline fails closed. A `prd-autofix` touching a Non-Goals row is rejected. Root transcribes, never composes: `author: "human"` marks a human's actual words, and absent a reply the `human-consultation` pause is the run's correct end. A response or intake `decisions` clause that only restates the request authorizes nothing; the specialist re-raises. `route` holds `human-consultation` while any human-targeted request lacks its response, across every later record and `req_id`, and the `dispatch` source lapses once any human intake-decision exists. While a `consultation-request` targeting `human` is pending, `route` holds `human-consultation`, and the `new-feature` skill's guarded removal surfaces that hold instead of clearing the scratch directory.

## Consequences

**Positive**
- A contained fix round on an oversize or multi-module slice costs the dissenters only, every round.
- The 2026-09-03 replay over 98 v0.3.x runs: 19 of 43 fix-pass plans were full roster on `prior-critical`, carrying 27 criticals, 23 on docs and 4 on tests. Scoping the trigger turned 12 into low plans, dropping 30 dispatches and $10.19 with no finding lost.
- The silent-drop-then-delayed-dissent path is closed by construction; wanting a fix costs the honest `changes_requested` round.
- Worst-case review spend per cycle is bounded on every path; only genuine critical dissent reaches round 4.
- A headless run whose dispatch states the override passes unchanged; one that does not has no compliant path to a Non-Goals edit.

**Negative**
- Escalation reads log-derived context; a fabricated record could narrow a review the old code kept wide. Records were never authenticated.
- The change-grader's cold read is the backstop for a mis-narrowed round and is skipped under `auto_grade = false`.
- The sweep has no mechanical enforcement; the engine holds the data to flag a repeat-class finding and that audit is future work.
- A mis-tagged advisory note costs one bounce round.
- A round-3 critical trips `prior-critical`, so the final round is the most expensive. The pipeline bounds by round count because no bystander watches between human decision points, a deliberate divergence from human-run review.
- The ledger cannot prove authorship: a forged human response and a mid-slice commit moving the baseline remain instruction-only barriers. A false override is a first-class record visible to reviewers and the human, where a `notes` rationalization was not. The v0.3.4 `visit-cancel` r2 rep recorded root composing such a response and implementing for $18.08 beside refusals at $0.90 and $1.07.

## Implementation

- `harness/core/scripts/grading/planner.py` — fix-plan derivation.
- `harness/core/scripts/handoff/ladder.py` and `records.py` (`REVIEW_ROUND_CAP`); `handoff/routing.py` — the Gate 4 record gate and the non-convergence block.
- `handoff/scope_lock.py` and `handoff/non_goals.py` — Gate 1; `handoff/view.py` — the ladder round and recommendations.
- `review-workflow` § Class-Exhaustive Findings and § Review-Round Convergence; `route-spec.md` § Review Non-Convergence and § Gate 1.
- `prd-authoring` § Scope Overrides; the product-requirements-expert agent § Working from a Recorded Intake.

## References

- [The reviewer roster](2026-06-18-the-reviewer-roster.md) — the first-pass ladder whose fix rounds this decision sizes.
- [Design truth mid-slice](2026-07-18-design-truth-mid-slice.md) — the cycle-start rule the round counter reuses.
- [Deterministic routing engines](2026-07-02-deterministic-routing-engines.md) — the gates these rules join; code enforcement over prose.
- [The eval bench](2026-07-15-the-eval-bench.md) — the instrument that surfaced the dropped finding and the refusal flakiness.
- [The change-grader](2026-06-05-the-change-grader.md) — the advisory cold read that backstops a narrowed round.
- [The product expert and the root conversation](2026-06-19-the-product-expert-and-the-root-conversation.md) — the root-transcribes doctrine scope lock relies on.
- [Fresh-eyes review of the changeset](2026-06-21-fresh-eyes-review-changeset.md) — the read-set discipline the delta re-review preserves.
- [Resilience-first improvement doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — every cheap path fails closed and stays auditable.
- [Google eng-practices, The Standard of Code Review](https://google.github.io/eng-practices/review/reviewer/standard.html) and [Huang et al. 2023](https://arxiv.org/abs/2310.01798) — approve-with-nits, and ungrounded re-iteration degrading correct work.
