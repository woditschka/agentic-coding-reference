# Delta-Sized Fix Cycles and Class-Exhaustive Findings

**Status:** Accepted (cycle boundary, prior-critical decay, and escape scope amended by [2026-08-07 review-cycle-survives-mid-slice-design-records](2026-08-07-review-cycle-survives-mid-slice-design-records.md))

> Amendment 2026-08-07: the review cycle now resets only on a superseding design-block, dissent is cycle-wide (so `prior-critical` decays with its reviewer's next verdict, not with the next closed round), and a docs/test/config escape widens the pass instead of re-running the battery cold. Everything else here still holds.

## Context

[Risk-proportional review](2026-07-09-risk-proportional-review.md) sized fix-cycle risk over the accumulated diff against `HEAD`, not the fix delta. Its Consequences recorded the oversize and multi-module cases as accepted debt and named delta-sizing as the future refinement. The code applied the same stickiness to every slice-level trigger: sensitive paths, binary files, unclassifiable surface, build retries, design revisions. None of those decay — an oversize slice stays oversize while its fix deltas shrink to a few lines. A three-round slice therefore paid three full batteries where the design intent was dissenters-only re-review. This ADR is that refinement.

A second cost compounds the first. Re-dispatching a reviewer over surface it already reviewed re-samples its judgment. Each sample surfaces a different subset of the same defect class. Observed shape: a reviewer clears its prior findings each round, then reports new findings of the same class on unchanged surface. Every late instance buys one more full fix cycle. Roster width cannot fix this — width buys independent perspectives, not exhaustiveness within one perspective.

## Options Considered

1. **Round cap with human escalation.** Keep slice-level triggers; after N rounds, batch non-critical findings to an escalation. Rejected: caps the cost only after paying N full batteries, and does not touch why rounds repeat.
2. **Dissenters-only on every fix pass.** Drop full-roster escalation from fix rounds entirely. Rejected: fails open — a fix that grows the surface, touches sensitive paths, or follows a critical finding needs the cold full read.
3. **Delta-sized escalation plus class-exhaustive findings** (chosen): fix-round risk reads the fix delta alone; reviewer discipline makes each round's findings exhaustive per class.

## Decision

**A fix round with dissenters computes its escalation from the fix delta, never from the accumulated slice. A reviewer's findings are exhaustive per class: one instance found means the whole review surface is swept for that class before the record is appended.**

- **Delta triggers replace slice triggers on fix passes.** `_derive_fix_plan` escalates on `delta-sensitive`, `delta-binary`, `delta-unknown-surface`, `delta-oversize`, `delta-escaped-surface`, `delta-unavailable`, `reviewed-surface-unavailable`, and `prior-critical`. `delta-oversize` measures the delta's production and test lines against the first-pass `size_threshold` — one knob for both rungs of the ladder. Slice-level triggers (`oversize`, `multi-module`, `sensitive`, `binary`, `unknown-surface`, `build-retries`, `design-revision`) govern first passes only. A dissenter-less fix pass (an autofix-only round) is the one carve-out: it falls to the first-pass ladder over the accumulated slice, fail-closed.
- **The sensitive dimension is retained, not re-escalated.** A slice that touched sensitive paths keeps the security reviewer on every fix round, reading the delta. A clean fix in a non-sensitive file can still break behavior the sensitive surface depends on; retention covers that without the full battery.
- **Scope semantics are unchanged.** An escaped or unknowable surface gets the full roster over `full-diff` — the cold read. A risky-but-contained delta gets the full roster over `fix-delta`. A clean contained delta gets dissenters plus `bar_clause`-widened reviewers over `fix-delta`.
- **A capped basis recomputes, never assumes.** A prior plan over more than `_BASIS_FILE_CAP` files stores `files: null`; the fix pass recomputes the reviewed surface from git (`base..prev_tree`). Without this, every large-slice fix would false-fire `delta-escaped-surface` — reinstating the full battery for exactly the slices the change targets. An unrecomputable surface fails closed (`reviewed-surface-unavailable`, cold read).
- **History triggers drop from fix rounds; `prior-critical` stays.** `prior-critical` is window-scoped to the immediately-prior round, so it decays once a round closes without a critical finding. Dropping `build-retries` and `design-revision` removes a real escalation: post-re-triage fix rounds previously re-ran the full battery. Accepted: the first pass after a re-triage still runs it (the re-triage resets the pass to `first`), and the retry ladder re-triages at three failures.
- **Reviewers sweep class-exhaustively.** `review-workflow` § Class-Exhaustive Findings: before appending, the reviewer searches the remaining review surface for further instances of every finding class it recorded. Patterns are searched as literal fixed strings, never as shell or regex input. The planned checkpoint outranks the sweep: at a checkpoint the reviewer sweeps only the surface already reviewed.
- **Fail-closed paths widen.** A missing or invalid plan, an unresolvable tree, or `always-full` mode still yields the full battery. New: a dissent whose author maps to no roster member fails closed to the full roster instead of emitting an empty-roster low plan.

## Implementation

- `harness/core/scripts/score-change.py` — `_derive_fix_plan`, `_parse_numstat` (split from `_delta_features`), `_tree_files`, `_plan_context` (capped basis reads as `None`), `_derive_plan` (the fix branch precedes the slice ladder).
- `harness/stacks/*/scripts/test_score_change.py` — eleven new fix-pass and parsing pins, byte-identical across the three stacks.
- `harness/core/.claude/skills/review-workflow/SKILL.md` — § Class-Exhaustive Findings, the fix-pass ladder in § Risk-Proportional Roster, the sweep line in the reviewer Pre-Check estimate.
- `harness/core/.claude/skills/handoff-routing/route-spec.md` — Gate 5's fix-cycle sentence names the delta-risk escalation.

## Consequences

**Positive:**
- A contained fix round on a slice that tripped `oversize` or `multi-module` costs the dissenting reviewers only, not the full battery. The saving repeats every round the slice needs.
- Churn is addressed at its source: a class surfaced in round N is exhausted in round N, so round N+1 reviews fixes, not fresh instances.
- Every escalation remains auditable — the plan's `triggers` name the delta facts that forced width.

**Negative:**
- Escalation now reads log-derived context (prev tree, reviewed surface, dissenters) where slice facts from git previously forced width unconditionally. A fabricated record could narrow a review the old code kept wide. Accepted as a defense-in-depth loss, not a new boundary: records were never authenticated, and an agent could already append a complete `low` plan verbatim.
- The terminal backstop for a mis-narrowed round is the change-grader's cold read — advisory by design, and skipped under `layout.toml [harness] auto_grade = false`. A project that disables grading runs narrowed fix rounds with no cold backstop.
- The sweep has no mechanical enforcement — no schema field, no engine check. The engine holds the data to flag a repeat-class finding on unchanged surface (`open_findings` against the delta paths); wiring that audit is future work.
- The sweep adds search calls to each finding-bearing round. Bounded by the checklist's class count; one sweep costs less than the re-review round a missed instance buys.

## References

- [Risk-Proportional Review Dispatch](2026-07-09-risk-proportional-review.md) — the decision this refines; its Consequences pre-authorized delta-sizing as future work.
- [Fresh-Eyes Review of the Changeset](2026-06-21-fresh-eyes-review-changeset.md) — the read-set discipline the delta re-review preserves; the sweep rule bounds its re-sampling cost.
- [Additive Reviewer Roster](2026-06-18-additive-reviewer-roster.md) — the floor membership untouched by this change.
- [Resilience-First Doctrine for Harness Improvements](2026-07-12-resilience-first-improvement-doctrine.md) — the bar applied: every cheap path fails closed and stays auditable.
