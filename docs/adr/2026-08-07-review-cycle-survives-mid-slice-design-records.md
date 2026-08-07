# The Review Cycle Survives Mid-Slice Design Records

**Status:** Accepted

## Context

[Delta-sized fix cycles](2026-07-14-delta-sized-fix-cycles.md) made fix rounds cheap: dissenters plus implicated reviewers read the fix delta, and the full battery returns only on delta-level risk. The eval bench's v0.2.0 sweep showed the design being defeated on the bench's cheapest task. `owners-page-param` cost per pass rose from $5.56 (v0.1.29, 3 reps) to $10.59 (v0.2.0, 3 reps) with the same model pin, base commit, and prompt.

The ledgers name the mechanism. [Provenance-marked briefs](2026-07-31-derived-briefs-carry-provenance.md) make fix rounds edit the PRD and `docs/system-design.md` routinely, so the middle loop's brief stages now run mid-slice. That collided with three rules written when design records only opened a slice:

1. **Any `design-block` reset the review cycle.** A fix-round `prd-entry` landing after the implementer's build-pass dispatches the designer. The designer's `design-block` — an initial record, not a re-triage — made the next pass read as `first`. The first-pass ladder then re-ran the full battery cold (`multi-module` trips on any prod-plus-test change under the maven/gradle source-set module rule). Whether this fired depended on append order — a race, not a decision.
2. **Dissent lived in the last inter-build-pass window.** A round interrupted before its reviews ran (the design record and a fresh build-pass landed between rounds) dropped the earlier dissent from the plan context. The pass fell back to the first-pass ladder.
3. **Any surface escape re-ran the full battery cold.** A fix round that adds a PRD bullet or a design-doc note escapes the reviewed surface by definition. The v0.2.0 ledgers show no escape trigger — the reset fired first — so this cost is inferred, not recorded. It binds all the same: with rule 1 alone, those same brief edits would trip the escape rule into the cold battery the reset used to cause.

Recorded effect in `evals/results/runs/v0.2.0/*owners-page-param*`: three build-passes and up to four review rounds per rep, against a uniform two-and-two in every prior version. Reviewers note the production diff "byte-identical to the pass-1 diff already approved".

## Options Considered

1. **Suppress the mid-slice design triage.** Route a fix-round `prd-entry` straight back to review. Rejected: the middle loop's triage of a changed requirement is deliberate; the cost sits in the reset, not the triage.
2. **Accept the cost as the price of provenance.** Rejected: the overhead is fixed per slice, so it lands hardest on the small slices the bench prices — +90% on a one-line clamp. The extra rounds re-approve unchanged bytes.
3. **Make the review cycle a first-class boundary** (chosen): only a true re-triage resets it, dissent is cycle-wide, and a docs/test/config escape widens the pass instead of re-running the battery.

## Decision

**The review cycle starts at the latest `design-block` carrying `supersedes_record_at`. Everything else — initial design records, `prd-entry` records, interrupted rounds — leaves review history live.**

- **Reset on supersede only.** `plan_context` and `route`'s completion invariant bound the cycle by the latest *superseding* design-block. A re-triage still voids prior review history, and its `design-revision` trigger still re-runs the full battery on the next first pass. An initial `design-block` landing mid-slice no longer resets either side.
- **The reset pointer is validated where it is honored.** Gate 2 checks `supersedes_record_at` only when the design-block is the latest record, so both boundary scans re-check it — integer, earlier line, target a design-block of the slice. A forged pointer could otherwise void outstanding dissent, the exact state the completion invariant protects.
- **Dissent is cycle-wide.** The plan context reads the latest `review-feedback` per reviewer across the cycle, mirroring the completion invariant, instead of the last inter-build-pass window. An interrupted round can no longer orphan dissent. `prior-critical` decays with its reviewer's next verdict rather than with the next closed round — a refinement of the window-scoped decay [delta-sized fix cycles](2026-07-14-delta-sized-fix-cycles.md) recorded.
- **The fix basis is what the dissent reviewed.** `prev_tree_sha` comes from the plan governing the round of the oldest outstanding dissent, so a dissenter's `fix-delta` read covers everything since it last spoke. A dissent no plan precedes leaves the basis null and fails closed (`delta-unavailable`).
- **A docs/test/config escape widens; a prod, unknown, or runtime escape stays cold.** An escape confined to docs/test/config surface adds that surface's reviewers (`surface_reviewers` map) to the fix roster at `low` risk over `fix-delta`. Any escaped path classifying as prod or unknown keeps `delta-escaped-surface`: full roster, `full-diff`, as before. So does any escape into the harness runtime (`.claude/`, the mirror directories, `schemas/`, `scripts/`) — agent instructions and gate config are trust surface whatever their file extension.
- **Build retries are untouched.** The retry cap and the grader's `build_retries` still count from the latest design-block of either kind — a fresh design statement resets implementer attempts. Only the *review* cycle definition changed.

## Implementation

- `harness/core/scripts/grading/planner.py` — `plan_context` (supersede boundary with pointer validation, cycle-wide latest-per-reviewer dissent, oldest-dissent basis), `_derive_fix_plan` (escape-kind fork, runtime-prefix guard, surface widening, rationale).
- `harness/core/scripts/handoff/routing.py` — the completion invariant's cycle boundary in `_review_state`, with the same pointer validation.
- `harness/core/schemas/scratch/review-plan.schema.json` — `pass` and `prev_tree_sha` descriptions.
- `harness/core/scripts/tests/grading/test_planner.py`, `harness/core/scripts/tests/handoff/test_routing.py` — pins for all three rules, both directions.
- `harness/core/.claude/skills/handoff-routing/route-spec.md` § Gate 5, `harness/core/.claude/skills/review-workflow/SKILL.md` § Risk-Proportional Roster — the prose contract.

The companion prompt change lands beside this: `design-validation` (all stacks) and `prd-authoring` gain a pre-handoff self-check naming the three doc rules their prose was bouncing off the doc-reviewer. The design variant checks state statements in `system-design.md`; the PRD variant checks behavioral language across the brief set; both check the 30-word standard and mark preservation. It removes the review round the pipeline's own writing stages were buying.

## Consequences

**Positive:**

- A fix round following a mid-slice brief edit costs the dissenters plus the doc surface's reviewer, not four cold re-reads. On the v0.2.0 `owners-page-param` ledgers this removes the whole-battery round and the interrupted-round fallback in every rep.
- Roster resolution no longer depends on whether the prd-expert or the implementer appended last — the race is gone.

**Negative / accepted:**

- A docs-only escape is now reviewed by the doc surface's reviewers instead of the full battery. Accepted: the first pass already paid the cold read, the escaped files are in the delta those reviewers read, and prod/unknown/runtime escapes keep the fail-closed path.
- A widened escape round is a `low` plan, so production bytes contained in the reviewed surface are re-read by dissenters only. That is [delta-sized fix cycles](2026-07-14-delta-sized-fix-cycles.md)' designed contained-fix bar — but it is newly reachable from two states that used to fail closed by accident (the reset, the docs escape). `prior-critical`, `delta-sensitive`, sensitive-slice retention, and bar-clause widening still force the battery.
- An unresolved critical finding now holds `prior-critical` across rounds until its reviewer re-verdicts, where the window let it decay after one closed round. Wider, fail-closed.
- The retry cycle stays any-design-block (a fresh design statement resets implementer attempts), so "cycle" now names two boundaries. The route-spec distinguishes them explicitly: retry cycle versus review cycle.

**Deferred, recorded:**

- The maven/gradle module rule derives `src/main/<lang>` and `src/test/<lang>` as distinct modules, so `multi-module` fires on every prod-plus-test first pass and the `gray` planner path never runs there. Pre-existing, out of this decision's scope; worth its own decision with bench evidence.

## References

- [Risk-proportional review](2026-07-09-risk-proportional-review.md) — introduced the plan engine this decision refines.
- [Delta-sized fix cycles](2026-07-14-delta-sized-fix-cycles.md) — the fix-round ladder whose cycle boundary, `prior-critical` decay, and escape scope this decision amends.
- [Derived briefs carry provenance](2026-07-31-derived-briefs-carry-provenance.md) — made fix rounds edit briefs routinely, exposing the reset race this decision closes.
- [The eval bench measures cost per pass](2026-08-02-eval-bench-cost-per-pass.md) — the measurement that surfaced the regression.
