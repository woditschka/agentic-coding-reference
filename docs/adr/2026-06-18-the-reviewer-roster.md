# The Reviewer Roster: A Doctor-Enforced Floor, Dispatched in Proportion to Risk

**Status:** Accepted

## Context

The pipeline reviews every slice along four dimensions: code quality, tests, security, documentation. Gate 4 completes only when every dispatched reviewer returns `approved`. The count "four" was once a literal in three layers: the gate prose, the `review-feedback` author enum, and the routing text. Adopters wanting a fifth dimension (idioms, performance, accessibility) had to fork all three. The opposite failure matters more: a roster a project fully owns lets it drop security or test review, the silent downgrade the harness exists to prevent.

Dispatch was unconditional. Gate 3 ran the whole roster after every `build-pass`, so a docs-only typo paid four dispatches and a two-cycle fix paid eight. The inputs for a cheaper decision already existed deterministically: the changeset classifier (file kinds, modules, sensitive paths, line deltas) and the ledger's approval history. A human estimates risk from exactly these facts before deciding how much review to buy.

Across the committed v0.3.x runs the security reviewer was dispatched 120 times and returned three fixable findings. It runs on Opus at $0.67 a dispatch, about five percent of a sweep, and sits on the critical path of every full battery. Nine of twelve v0.3.9 feature slices rated high on the 80-line size trigger alone. A change with no security surface was buying a security read.

## Options Considered

1. **Free-form `reviewers` list in `layout.toml`.** Rejected: a project can delete a floor reviewer.
2. **`/materialize` stamps `four + extras` into each project's schema enum.** Rejected: adds enum-rewriting to a step that never rewrites a project's schema.
3. **Closed floor plus additive extension** (chosen).
4. **Focused loop with an unconditional final full battery.** Rejected: a fixed four-dispatch tax paid at the slice's cleanest state.
5. **LLM triage on every pass.** Rejected: pays a dispatch to re-derive what the changeset features settle deterministically.
6. **The pipeline-coordinator as risk judge.** Rejected: it never reads source and carries a 14-tool-call budget sized for table lookups.
7. **Risk-proportional dispatch** (chosen): an engine decides clear cases, a budget-bounded planner judges the gray zone.
8. **Recalibrate the triggers on the first bench data** (prod-only size count, decay `design-revision`). Rejected 2026-08-02: recomputation left every observed classification high, and the decay would remove re-triage re-coverage.
9. **Keep the security reviewer unconditional on high plans.** Rejected: the spend bought no finding on the recorded slices.
10. **Move the security reviewer to the mid tier.** Rejected: a judgment reviewer never sits below the implementer.
11. **Gate the security dispatch on a declared surface, fail closed** (chosen).

## Decision

**The four-reviewer floor is mandatory and doctor-enforced; a project extends it additively through `extra_reviewers`. A logged `review-plan` sizes each pass's roster from the changeset and the ledger; the full battery is the fail-closed default. On a high plan the security reviewer is dispatched only when the change carries a security surface.**

- **The floor is closed, the extension open.** The four reviewers are harness-owned and named in the gate. `scripts/layout.toml [harness] extra_reviewers` appends names, default `[]`; the effective roster is floor plus extras. Reviewers are named `*-reviewer`; `review-feedback.author` validates shape, the roster list holds authority. `clarify_target` relaxes likewise, to a bounded pattern admitting the two expert agents plus any roster reviewer. The doctor asserts every floor and extra reviewer has an agent body in every declared tool surface, and that each extra is listed in `extensions` so `/materialize` preserves it. With no agent directory present in the tree, the doctor skips the body checks as runtime not materialized. Extras are project-owned bodies, so their checks run on every channel.
- **The engine decides for free.** `grading.py review-plan` runs as a child of the `build-pass` append on the default ledger, so `route` reads a record and never touches the worktree. A `--file`-redirected append never runs the engine; the manual command stays runnable. A skipped engine step fails open to a warning; `route` then fails closed to the full battery and names the gap in its reason. Clear-low emits a surface-matched roster from `[review] surface_reviewers`. Sensitive paths, multiple modules, unclassified or binary paths, over-threshold size, build retries, superseded designs, or prior criticals emit the full roster. Any null feature is high. `oversize` as the sole trigger with production lines at or under `size_threshold` emits `gray`: added tests raise no security surface.
- **The gray zone buys one judgment.** The engine emits `risk: "gray"` with no roster and `route` dispatches the `review-planner`. The planner is a low-effort agent with a tight tool budget; it reads the hunks and appends the plan with a rationale. Only the engine emits `gray`, so triage terminates in one hop.
- **The record carries its facts.** `basis` holds the tree SHA, per-file classification, history facts, each dissenter's open findings, and `security_surface` (`declared`, `paths`). High plans record trigger counts, not file rosters.
- **The security reviewer follows the surface.** A surface is a sensitive path, a config-surface file, an unclassifiable or binary path, or a prior critical. A hit of the `[review] security_surface` probe over added and removed production lines is one too. The probe is stack syntax and ships in the harness-owned `scripts/layout-defaults.toml`. A project's `layout.toml` key overrides it, an explicitly empty list keeps the reviewer on every plan, and the generic stack ships an empty probe. On a gray plan the planner leaves the reviewer off a no-hit change, with exceptions named in the rationale. The diff adds a secret, changes a dependency, weakens a check, or reaches an input or sink the probe's list misses. A null result keeps the reviewer.
- **Correction is additive-only.** A dispatched reviewer widens the roster via `clarify`. The change-grader's `review_roster` feature makes a floor reviewer silent under a focused plan expected, and its advisory verdict is the terminal backstop. Automatic escalation from a `concern` verdict into a full-battery round is recorded future work. Feature-complete requires the latest verdict of every reviewer dispatched since the current cycle start to read `approved`. `mode = "always-full"` reproduces unconditional dispatch.
- **Fix rounds** are sized by [review convergence](2026-07-14-review-convergence.md).

## Consequences

**Positive**
- Adding a review dimension is one name plus the agent bodies; deleting a floor reviewer fails the doctor.
- A docs-only change costs 1 dispatch instead of 4; a gray two-cycle fix costs about 5 or 6 instead of 8; a risky slice costs what it cost.
- Every cheap path is auditable from the plan's `basis` and the planner's one-line rationale.
- The five percent of sweep spend on security review moves to where the surface is, and a size-only high plan loses its slowest reviewer.

**Negative**
- A typo in a floor reviewer's name passes the schema; the gate then stalls waiting for the correctly named verdict, a liveness failure a human sees.
- A dimension can be affected without owning changed surface (a code fix staling docs). Bounded by the size threshold, history escalation, additive widening, and the grader's cold read.
- The planner can under-estimate; its facts are logged and every correction path widens.
- A probe is only as good as its patterns; the sensitive globs and fail-closed defaults are the floor under it. "Never subtracted" reads per plan.
- A project-owned layout that restates the old probe keeps its copy; the doctor warns.

## Implementation

`check_reviewer_roster` in `harness/core/scripts/doctor.py` and `harness/core/scripts/doctor-expectations.toml [reviewers]` (the floor and the name pattern). `harness/core/scripts/grading/planner.py` (`security_relevant`), `grading/features.py` (`security_surface_paths`), `grading/config.py` (`load_stack_defaults`, `merged_table`); `harness/stacks/*/scripts/layout-defaults.toml`; `harness/core/scripts/handoff.py` (the build-pass append spawns the engine); the review-plan schema; `review-workflow` § Risk-Proportional Roster; `route-spec.md` Gate 5.

## References

- [Review convergence](2026-07-14-review-convergence.md) — sizes the fix rounds this roster's first pass precedes.
- [The change-grader](2026-06-05-the-change-grader.md) — the plan-aware terminal cold read that backstops a focused pass.
- [Fresh-eyes review of the changeset](2026-06-21-fresh-eyes-review-changeset.md) — the read-set discipline the planner preserves.
- [Model tiering](2026-06-11-model-tiering.md) — keeps the security reviewer on the premium tier this decision leaves in place.
- [Layout declares the project](2026-06-14-layout-declares-the-project.md) — the engine/data split the roster list and the probe follow.
- [The doctor](2026-06-14-the-doctor.md) — enforces the floor and reports which probe is in effect.
- [Deterministic routing engines](2026-07-02-deterministic-routing-engines.md) — tables decide, agents judge only what tables cannot.
- [The handoff ledger](2026-05-08-the-handoff-ledger.md) — where every plan lands as one validated record.
