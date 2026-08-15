# The Design-Doc Sync Check Joins the Quality Gate

**Status:** Accepted

## Context

The v0.3.1 and v0.3.2 eval sweeps expose one finding class as the dominant
critical across tasks: the slice lands with its requirement id absent from
`docs/system-design.md`. The doc-reviewer states it the same way each time:
"REQ-VET-003 appears nowhere in docs/system-design.md", "the Contracts
table's Implements column is stale". Each instance buys a fix round at
roughly the cost of two reviewer dispatches. Round-1 oracles pass in every
recorded rep; the code is right the first time, the doc-sync duty is not.

The recorded remedy for a recurring mechanical class is to move it to write
time. The 2026-08-10 change did that with a self-review walk for test
conventions; the judge's test-quality facet rose from 3 to 4. The
"appears nowhere" half of this class is stronger than walk material: id
presence is string-checkable, so prose need not carry it at all.

## Options Considered

1. **A self-review walk clause only** — rejected as the sole fix: the class
   is deterministic, and a prose obligation for a grep-checkable fact leaves
   the failure mode the sweeps measured (the duty skipped under budget
   pressure at dispatch end).
2. **Parse the Contracts table and verify the touched types' rows** —
   rejected for the first cut: row-level verification needs the table's
   Source column to resolve against diff paths, a brittle parse for a
   judgment the doc-reviewer already renders well. Presence first; row
   fidelity stays reviewer work.
3. **A presence check in the gate, plus coverage-trace walk clauses**
   (chosen).

## Decision

**Gate-pass gains a deterministic design-doc sync check.**
`python3 scripts/grading.py contracts-sync --feature <req_id>` fails the
gate when the slice's req_id is absent from `docs/prd.md` or
`docs/system-design.md`; it passes vacuously when the design brief does not
exist, matching the gate's absent-log convention. Presence is the floor —
whether the *right* Contracts rows carry the id stays doc-reviewer
judgment, and the reviewer checklists lose nothing. The two sweeps' doc
criticals split near evenly between absence and stale rows; the check
removes the absence half deterministically and leaves staleness to review.

**The red path routes to the design doc's writer, never the gate runner.**
`contracts-sync` joins the `[gate]` verbs vocabulary in `layout.toml` — the
declared home `gate_checks_run` and `failed_check` validate against — and a
failure appends a `build-failure` with `abort_reason: "design-mismatch"`.
Build-Failure Recovery's abort short-circuit routes it to the
`system-design-expert`, whose superseding `design-block` places the
requirement; the implementer never edits `docs/system-design.md`.

**The self-review walk gains the two coverage-trace classes** the ledgers
show buying test-reviewer fix rounds: every recorded "Done when" bullet and
PRD edge case for the slice's requirement has a matching test (multi-part
cases part by part), and every risk the slice's `design-block` names has a
test exercising it. As with the 2026-08-10 walk, this narrows what
reviewers find, never what they check.

## Consequences

Positive:

- The dominant critical review class becomes a gate failure resolved before
  reviewers dispatch: the triage duty places the id, and a miss aborts to
  the `system-design-expert` — saving on the order of one doc-reviewer fix
  round on most feature reps.
- The gate's check table grows by one stack-agnostic row in all three
  stacks; the `CLAUDE.md` Quality Gate chapters, the init skeletons, and
  the `layout.toml` gate-verbs vocabulary move together, keeping every
  gate home in agreement. An existing consumer inherits the verb through
  materialize's advisory `layout.toml` reconcile.
Negative:

- A req_id present in the design doc for the wrong reason (a stray mention,
  a stale row) passes the check; the doc-reviewer remains the judge of row
  fidelity. The check can tighten to row-level verification later if the
  presence floor proves too permissive.
- Front-door slices write richer PRD prose per requirement. The
  coverage-trace walk therefore reads more "Done when" bullets than the
  pre-intake era — the intended surface, traced at write time instead of
  found in round 2.

## References

- [Risk-Proportional Review Dispatch](2026-07-09-risk-proportional-review.md) — the gate/review economy this check protects.
- `harness/core/scripts/grading/contracts.py` — the check; `tests/grading/test_contracts.py` pins it.
- `harness/core/.claude/skills/tdd-workflow/SKILL.md` § the self-review walk — the coverage-trace clauses.
