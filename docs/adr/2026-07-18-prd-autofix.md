# PRD Autofix: In-Round Root-Applied Fixes on docs/prd.md

**Status:** Accepted

## Context

The harness gives design-doc paths an in-place autofix path: root applies a reviewer's `tag: "autofix"` finding verbatim, appends a `design-doc-autofix` record, `handoff.py audit-autofix` re-validates the bounds at gate time, and system-design-expert audits the trail on its next dispatch. The slice stays in the current review round.

`docs/prd.md` had no equivalent — a deliberate exclusion ("no autofix exception"). An autofix-tagged PRD finding could only route to product-requirements-expert, whose sole substantive record is a `prd-entry`. A fresh `prd-entry` matches `prd-approved` and re-enters the pipeline at Gate 1: design re-triage, a fresh build-pass, and a full new review battery — discarding banked approvals. A live run measured the cost of one sentence-split finding: 5 extra dispatches (re-triage, re-validate, a 4-reviewer second round). The identical-nature code autofix in the same round resolved in place.

The asymmetry is structural, not judgmental: the eligibility conditions that make a design-doc autofix safe (writing-standards/structural category, literal fix string, 5-line/200-char caps, no heading/anchor/REQ-ID/fence/link change) apply unchanged to a PRD writing-standards finding.

## Options Considered

1. **Status quo** — rejected: a zero-semantic doc fix costs a full slice re-flow; the re-flow signal (a `prd-entry`) stops distinguishing semantic changes from typo repair.
2. **Generalize `design-doc-autofix` into one `doc-autofix` record covering both path classes** — rejected: existing consumer logs carry `design-doc-autofix` records; a rename forces log migration or dual-name handling, and one record type would blur which expert audits which path.
3. **Additive `prd-autofix` record mirroring `design-doc-autofix`** (chosen) — same bounds, same two-stage audit, new type string; existing logs stay valid and each record names its auditing owner.

## Decision

**Root may apply autofix-tagged findings on `docs/prd.md`, recording a `prd-autofix` audit record; the pipeline re-flow is reserved for `prd-entry` records whose semantics changed.**

Load-bearing details:

- **Exact symmetry.** `prd-autofix` pins `author: "root"` and `file: "docs/prd.md"`, carries the same category enum (`writing-standards`/`structural`), the same caps, and the verbatim source finding. Root's apply procedure is unchanged — one section (`handoff-routing` § Root-Applied Autofix on Doc Paths) now covers both path classes.
- **Per-type supersession.** The audit closes a slice's loop at the owning expert's record: `design-doc-autofix` at the latest `design-block`, `prd-autofix` at the latest `prd-entry`. Neither expert's record closes the other's loop.
- **The failure handler is the old default.** product-requirements-expert judges every `prd-autofix` record on its next dispatch (`prd-authoring` § Autofix Audit). An illegitimate record gets a corrective edit plus a superseding `prd-entry` — which re-flows from design triage, deliberately. A failed mechanical audit aborts with the new `abort_reason: "prd-mismatch"`, routing to the PRD owner (the `design-mismatch` twin; system-design-expert cannot write `docs/prd.md`, and its `design-block` would never supersede the PRD record).
- **Direct-edit detection stays design-doc-scoped.** `audit-autofix` step 2 does not scan `docs/prd.md` for uncovered edits. Extending it would newly gate-fail human PRD edits mid-slice — a behavior change for existing consumers, deferred until wanted on its own merits. A test pins the deferral.
- **Routing is one branch.** `_finding_owner` treats an autofix-tagged `docs/prd.md` finding as root-applied instead of dispatching product-requirements-expert; every other tag on that path routes to the owner unchanged. `prd-autofix` is not substantive — it cannot mask a truncated dispatch or advance the pipeline.

## Consequences

- Positive: a doc-only PRD fix resolves in the current review round; the `prd-entry` record regains its meaning as a semantic-change signal; the reviewer eligibility rules and audit machinery are shared, not duplicated.
- Negative: a fourth `abort_reason` value and a thirteenth record type widen the closed enums consumers learn; an uncovered direct edit to `docs/prd.md` remains undetected until direct-edit detection is extended.

## References

- [Deterministic Mid-Slice Routing via handoff.py route](2026-07-06-deterministic-mid-slice-routing.md) — the routing table this adds one owner-split branch to.
- [Mechanical Promises Move Into Engines](2026-07-14-mechanical-promises-into-engines.md) — precedent: the eligibility bounds are engine-checked at gate time, not reviewer memory.
- [Resilience-First Doctrine for Harness Improvements](2026-07-12-resilience-first-improvement-doctrine.md) — why the dirty-scan extension is deferred rather than shipped half-considered.
