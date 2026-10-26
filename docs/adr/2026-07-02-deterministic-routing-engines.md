# Pipeline Contracts Are Executed by Deterministic Engines

**Status:** Accepted

## Context

The Handoff Conditions table is deterministic: a passed gate names the next agent without judgment. Before the router existed, every mid-slice transition paid a `pipeline-coordinator` dispatch, about 10k input tokens per hop and five hops per happy-path slice, to re-derive a table lookup. Its damage handling lived in prose, untestable and occasionally misread.

A correctness sweep found five contract defects the battery could not see. A checkpoint finding tagged `escalate` halted the pipeline; a closed author enum rejected a declared extra reviewer. An audit told the coordinator to author a record its schema rejects. Three files disagreed on who writes `.scratch/escalations.md`, and the doctor crashed on a missing `scripts/layout.toml`.

Skill prose was 25–30% duplication. The 388-line `handoff-routing` skill restated the table the executor runs, and 17 agent bases carried the same dispatch-start block across about 68 rendered files. Copies had already drifted. Mechanical promises enforced by recall drifted live: a Gradle pin 9.5.1 against 9.6.1, a severity stated Medium and Critical across three homes. Of the 51 rule names the router can emit, 23 appeared in no document.

## Options Considered

1. **Keep the model coordinator on every hop.** Rejected: inference spent on decisions the table already made, with no regression test.
2. **Fully scripted routing, no coordinator.** Rejected: fresh intake and `refactor-first` sibling ordering are judgment calls.
3. **Prose carve-outs for the defects; widen schemas to admit the coordinator.** Rejected: description text is not a discriminator, and routing stays neutral only if the coordinator writes nothing.
4. **Leave the duplication, or trim each copy in place.** Rejected: N statements without a sync mechanism drift; the cost is the count, not the wording.
5. **Record mechanical-promise findings and fix opportunistically.** Rejected: prose backstops on gate checks fail exactly when unattended.
6. **Hand-maintain a route-rule table; or generate the router from a declarative table.** Rejected: a 51-row hand copy is the drift the ownership principle prohibits. A generation layer would need its own gate.
7. **A two-part router, dedicated record semantics, one statement per contract, engines for mechanical promises, and an AST-generated rule inventory.** Chosen.

## Decision

**`python3 scripts/handoff.py route` executes the Handoff Conditions table. Every mechanical, gate-relevant promise lives in an engine, a schema, or the battery. Prose states the why once and points at the command.**

- `route` prints one JSON decision: `dispatch`, `blocked`, or `escalate`. Root runs it after each dispatch returns. It is fail-closed: a dirty log or an unroutable slice yields `blocked` with the exact errors; it never repairs or guesses. A failed gate dispatches the upstream agent carrying the errors. Findings dispatch to their artifact owners; an escalate finding flags `halt_after`. The coordinator is dispatched only on `escalate` (no active slice, `refactor-first` ordering, truncation with no recovery row, any state matching no row) and for fresh intake. A deterministic `refactor-resume` re-triages the original once the refactor completes.
- A reviewer checkpoint emits a `truncation` finding, a progress marker that never halts. `dispatch-start.author` validates by pattern, three specialists plus `*-reviewer`, anchored with `\Z`; the doctor owns roster membership. `.scratch/escalations.md` has two writers, the feature-implementer and root on the coordinator's recommendation; the coordinator holds no Write grant on any tool surface.
- `handoff.py audit-autofix` runs both autofix audit steps, byte comparisons included, log-global, scoped to records after the latest `design-block`. A failure appends `build-failure` with `failed_check: "autofix-audit"` and `abort_reason: "design-mismatch"`; the system-design-expert closes it with a superseding `design-block`.
- Schemas carry the evidence: `severity` is required on `autofix` and `blocked` findings (Gate 4 bounces its absence; a blocked finding without it plans as critical); `build-pass` requires `gate_checks_run`. `validate` warns on a substantive record whose author appended no `dispatch-start` for the slice; `append` rejects a `responding_to` past the end of the log. `[review] surface_reviewers` in `layout.toml` scopes an extra reviewer; a malformed `[review]` or `[harness]` block raises at load, so `route` falls to the full battery.
- Each runtime contract is stated once, in the file its consumer loads. `route-spec.md` holds the normative table, gate field checks, and the recovery mechanics; `route` executes it, the routing tests pin it, no agent preloads it. Root reads a recovery section on demand only to shape a prompt, never a decision. Canonical homes: the dispatch-start block in `handoff-append`, slice sizing in `prd-authoring`, the roster and feedback tags in `review-workflow`. The installed `agentic-harness.md` sheds what its readers never consume there; `handbook-delta.expected` pins the divergence. A routing edit touches the spec, the router, and its tests in one change.
- `harness/render-route-rules.py` AST-walks the four decision constructors (`_dispatch`, `_bounce`, `_blocked`, `_escalate`) and renders `route-rules.md` into the `handoff-routing` skill. A non-literal rule argument is an error, so a partial inventory never renders; battery step 3j fails on drift.
- Three over-ruled spots became principles. The security reviewer's secret grep is a starting set with its rationale. The doc-review checklist carries its why and routes off-list defects to the standards. The diagram skill drops coordinates its source owns. The "revisit if behavior does not improve" item of the principles-over-rules doctrine closed on this evidence.

**Kept as prose by decision.** Five promises were reviewed on 2026-07-14 and deliberately left in prose. `_BAR_CLAUSE_REVIEWER` stays engine-owned and closed to the floor, since the `bar_clause` enum is closed and an extra re-enters fix rounds through its own dissent. The deps-upgrade verify commands stay prose, because build-failure verification interleaves with judgment. The harvest overlay-diff enumeration stays prose, since the skill runs rarely and feeds classification. The commit-convention chapters stay hand-parallel across the three init skeletons, with the stack rows as the variation. The one-clause four-reviewer-floor mantras in the glossary and the adoption guide stay, one hop from their canonical homes.

**Two body rules travel with the engines.** Every extra-reviewer body carries the First Tool Call stanza, so truncation detection keys on it. A companion file such as `route-spec.md` loads on an explicit Read only, never through a tool's skill loader.

## Consequences

**Positive:**
- Four to five model dispatches per slice became one Bash call each; the coordinator's cost dropped to its judgment cases.
- Recovery behavior (truncation continue, retry ladder, reviewer stall, abort short-circuits) is regression-tested, not prose-interpreted.
- A dispatch loading `handoff-routing` sheds about 170 lines, one loading the installed handbook about 90, each agent body about 11; roughly 8–9k tokens per clean slice.
- Every rule name the router prints is documented, or the battery fails; the skeleton-pin drift class is caught by `deps-report.py` in one command.

**Negative:**
- Routing behavior spans three files per edit; the rule extractor is coupled to the constructor idiom, and computed dispatch targets render as *(computed)*.
- Requiring `severity` and `gate_checks_run` fails older hand-written records at the gate until corrected.
- An in-flight ledger holding an old escalate-tagged checkpoint finding halts once for a human decision.

## Implementation

`harness/core/scripts/handoff/` (`routing.py`, `autofix.py`, `gates.py`, `roster.py`) with `harness/core/scripts/tests/`; `harness/core/scripts/grading/planner.py` for `surface_reviewers`; `harness/core/.claude/skills/handoff-routing/` (`SKILL.md`, `route-spec.md`, generated `route-rules.md`); `harness/render-route-rules.py` and `harness/verify_harness/checks/sync.py` (link anchors, shared-test pins, step 3j); `harness/deps-report.py`, `harness/review-survey.sh`, `harness/init.py`, `harness/materialize.py record-extension`.

## References

- [The Handoff Ledger](2026-05-08-the-handoff-ledger.md) — the ledger `route` reads as its only input.
- [Dispatch Lifecycle](2026-06-04-dispatch-lifecycle.md) — the truncation-detection and recovery rules `route` executes.
- [The Reviewer Roster](2026-06-18-the-reviewer-roster.md) — the pattern-over-enum rationale the author check extends; `surface_reviewers` scopes its extras.
- [Principles Over Rigid Rules](2026-06-03-principles-over-rigid-rules.md) — the doctrine this applies; its revisit item closed here.
- [Review Convergence](2026-07-14-review-convergence.md) — the required `severity` hardens its `prior-critical` trigger.
- [Design Truth Mid-Slice](2026-07-18-design-truth-mid-slice.md) — extends the autofix audit to the PRD and checks path coverage at append time.
- [Layout Declares the Project](2026-06-14-layout-declares-the-project.md) — `layout.toml` holds the `[review]` knob.
- [Resilience-First Improvement Doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — the bar applied: every demoted check fails loud.
- [`docs/agentic-harness.md`](../agentic-harness.md) — the human-facing handbook that keeps the long form.
