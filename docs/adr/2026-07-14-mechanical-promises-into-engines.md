# Mechanical Promises Move Into Engines

**Status:** Accepted

## Context

A boundary review of the whole reference asked where the principles-over-rules doctrine ([2026-06-03](2026-06-03-principles-over-rigid-rules.md)) is applied and where it is misapplied. Four parallel reviews covered agent/skill prose, engines and schemas, the docs layer, and the root maintainer skills. Nearly every finding pointed one direction: a mechanical, safety-relevant promise still enforced by prose recall where an engine could enforce it deterministically. Three findings pointed the other way — enumerations choking judgment surfaces. Three restatement channels were drifting live. The Gradle pin: skeleton 9.5.1 vs sample 9.6.1. The system-design "Why" severity: Medium vs Critical across three homes. The feature-complete definition: skills said "ever dispatched for the slice"; the engine scopes to the latest `design-block`.

## Options Considered

1. **Record the findings; fix opportunistically.** Rejected: two of the drifts were already live, and prose-only backstops on gate checks fail exactly when unattended.
2. **One batch: demote every confirmed mechanical promise into its engine; promote the three over-ruled spots into principles; gate the drifting restatements.** Chosen.

## Decision

**A promise whose application is mechanical, repeated, or gate-relevant lives in an engine, a schema, or the battery — prose states the why and points at the command.** The batch:

- **The autofix audit is a command.** `handoff.py audit-autofix` executes both audit steps the gate previously asked the implementer to perform by hand, byte-for-byte comparisons included. Step 1 statically re-validates records; step 2 detects direct edits, tracked and untracked. The audit is log-global, so a record under another slice cannot whitewash a path. The four prose homes now point at it.
- **`severity` is required on routable findings.** Gate 4 bounces an `autofix`/`blocked` finding without it. The field feeds the next review-plan's `prior-critical` trigger; omission previously read as non-critical and narrowed the fix round. `_plan_context` additionally treats a blocked finding with no severity as critical — fail closed on logs Gate 4 never saw.
- **`build-pass` carries evidence.** `gate_checks_run` is now required (min one item): the record that gates the reviewer fan-out names the verbs that ran, as `build-failure` already named its `failed_check`.
- **`validate` audits dispatch discipline.** A substantive record whose author never appended a `dispatch-start` for the same slice draws a deterministic warning. Truncation detection and the stall ladder are blind to that dispatch.
- **`append` bounds `responding_to`.** A dispatch-start pointer past the end of the log is rejected at the one moment the referent set is known.
- **The surface-to-roster map is configurable.** `[review] surface_reviewers` lands the knob [2026-07-09](2026-07-09-risk-proportional-review.md) promised; an extra named in the map becomes surface-scoped, an unmapped extra keeps the fail-closed always-join. Malformed `[review]`/`[harness]` values now raise at load — no plan is appended, so `route` falls closed to the full battery, matching `route`'s own loud `layout-invalid`.
- **The battery gains two gates.** The link-integrity step resolves `#fragment` anchors against heading slugs and `<a id>` anchors (retired from `/audit-harness` check 5). A shared-test-pins step byte-compares the engine-pin classes across the three stack suites — the hand-owned-parallel class [2026-07-12](2026-07-12-parity-gates-for-hand-owned-parallels.md) gates.
- **Maintainer mechanics become scripts.** `deps-report.py` collects every tracked pin (init skeletons included) and fails on intra-item drift; `--resolve-shas` verifies each workflow `# vX.Y.Z` comment against its pinned SHA. `review-survey.sh` emits the measurements `/review-harness` anchors on. `init.py` self-verifies its fills and fails on an unmapped leftover token. `materialize.py record-extension` encodes the extension-recording file surgery, including the `.gitignore` slash rule.
- **Three over-ruled spots become principles.** The security reviewer's four-literal secret grep becomes a starting set with its rationale. The doc-review closed checklist carries its why — an improvised style opinion erodes the standards — and routes off-list defects to the standards they violate. The diagram skill's research-arc prose drops the coordinates and hex values its own rule assigns to the `.drawio` source.

## Implementation

- `harness/core/scripts/handoff.py` — `audit-autofix`, the Gate 4 severity bounce, the validate warning, the append bounds check, `RETRY_CAP`.
- `harness/core/scripts/score-change.py` — `surface_reviewers`, loud `[review]`/`[harness]` validation, the blocked-without-severity guard.
- `harness/check-sync.py` — anchor resolution in the link step; the shared-test-pins step.
- `harness/deps-report.py`, `harness/review-survey.sh`, `harness/init.py`, `harness/materialize.py` — the maintainer-script demotions.
- Schemas: `review-feedback` (severity description), stack `build-pass` (required `gate_checks_run`).
- Prose: the four autofix-audit homes, `review-workflow`, `handoff-routing`, `handoff-board`, and the three skeleton/sample `CLAUDE.md` pairs. Docs-layer trims: the handbook slice-sizing and grading sections now point at their skills; the delta re-pinned.
- Ride-alongs in the same batch. The `next` skill extracts `## Superseded` REQ IDs mechanically; only the first ID per line retires — the successor stays a candidate. `_plan_context` reads each reviewer's latest record, so a bounced-then-corrected record no longer widens fix rounds. Two accuracy edits: the `specialist-agent-workflow.md` status line and the `ddd-principles.md` audit-docs row.
- Hardening from the pre-commit adversarial review. `audit-autofix` diffs cwd-relative (`--relative`) and baselines on the last commit touching the audited docs — a nested checkout or an unrelated commit cannot false-block. An unreadable baseline timestamp fails closed. `record-extension` rejects commas, backslashes, and degenerate paths, and verifies the `.gitignore` re-include took effect (`git check-ignore`); the runtime ignore block moves to the re-includable `dir/*` form. `[review.surface_reviewers]` rejects the dead `prod` key, which marked a mapped extra and silently narrowed its always-join. `deps-report.py` fails on any workflow `uses:` line that is not a commented full-SHA pin, and tracks the two Gradle homes (root `README.md`, the sample `system-design.md`) earlier bumps missed. `review-survey.sh` excludes pre-move sample paths from churn; `init.py`'s leak regex covers digits and hyphens.

## Consequences

**Positive:**
- Every gate-relevant promise in the batch now fails loud and mechanically; the three live drifts are fixed and their channels gated or collapsed.
- `deps-report.py` makes the skeleton-pin drift class structurally impossible to miss — the check that would have caught Gradle 9.5.1 now runs in one command.

**Negative:**
- Requiring `severity` and `gate_checks_run` tightens the reviewer and implementer protocols; older hand-written records fail the gate until corrected. Accepted: the defaults are mechanical (the Issue Classification table; the gate verb list).
- The battery grows two steps; both are static and add no toolchain dependency.
- The doctor does not yet validate `[review]` keys. A typo surfaces at the first `review-plan` run — loud, fail-closed to the full battery — not at onboarding. Doctor coverage is future work.

**Dispositions (reviewed, deliberately not changed):**
- `_BAR_CLAUSE_REVIEWER` stays engine-owned and closed to the floor. The `bar_clause` enum is closed in the schema; an extra re-enters fix rounds through its own dissent, so a clause→extra mapping has no referent.
- The deps-upgrade verify commands stay prose: build-failure verification interleaves with judgment (bisecting, revert-or-fix-forward) a script would flatten.
- The harvest overlay-diff enumeration stays prose: the skill runs rarely and its diff feeds classification judgment, not a gate.
- The commit-convention chapters stay hand-parallel across the three init skeletons; the accidental `docs`-row divergence is aligned, the stack-specific rows are the variation the parallel exists for.
- The one-clause four-reviewer-floor mantras in `glossary.md` and `adoption-guide.md` stay: mantra-grade restatements of a rule whose canonical homes (`agentic-harness.md` § Specialist Agents, the API spec) are one hop away.
- The [2026-06-03](2026-06-03-principles-over-rigid-rules.md) "revisit if behavior does not improve" item closes. This review's findings pointed almost entirely at missed demotions; three rule-bloat findings were the whole reverse direction. The taxonomy holds; the pressure is on demotion cadence, not the doctrine.

## References

- [Principles Over Rigid Rules](2026-06-03-principles-over-rigid-rules.md) — the doctrine this batch applies; its revisit item closes here.
- [Risk-Proportional Review Dispatch](2026-07-09-risk-proportional-review.md) — promised the `surface_reviewers` knob this batch lands.
- [Delta-Sized Fix Cycles](2026-07-14-delta-sized-fix-cycles.md) — the severity requirement hardens its `prior-critical` trigger.
- [Parity Gates for Hand-Owned Parallels](2026-07-12-parity-gates-for-hand-owned-parallels.md) — the shared-test-pins step extends its class.
- [Resilience-First Doctrine](2026-07-12-resilience-first-improvement-doctrine.md) — the bar applied: every demoted check fails loud, never silently narrows.
