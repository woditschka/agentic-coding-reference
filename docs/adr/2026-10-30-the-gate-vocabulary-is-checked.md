# A Required Gate Check Is Checked Where the Project Declares It

**Status:** Accepted

## Context

The test-conventions decision ([2026-09-03](2026-09-03-test-conventions-at-write-time.md)) made the conventions map a self-review walk aid in v0.3.10. Its 2026-10-25 amendment made the map a required check in every stack's `code-quality-gate` skill and a verb in the `[gate]` vocabulary of `scripts/layout.toml`, shipped in v0.4.11. The build-pass schema enumerates `gate_checks_run` from that project-owned list (`enumFrom`), so the append rejects a verb the project never declared. That is fail-closed in one direction only. A consumer whose layout predates v0.4.11 cannot record the new verb; the implementer drops it to get the record accepted, the check leaves the ledger unseen, and nothing fails. The doctor's `layout-gate` check validated only that `verbs` is a non-empty list of strings. Neither the marketplace setup nor `/materialize` touches the layout's vocabulary, since the file is project-owned. The battery pinned the skeletons' vocabulary to a shape, never to the manifest.

The eval fixture is such a consumer. Its layout carried the v0.3.8 vocabulary, and the first v0.4.11 cells ran the gate with the map unrecordable: both completed reps listed seven verbs on their build-pass and not `conventions-map`. The amendment named the listing on every build-pass as its reading on the next tagged sweep. That sweep would have returned the reading empty for a reason the harness could not see. The nine tagged rows from v0.3.10 to v0.4.10 ran the map as the walk aid their version shipped, so they measure what they claim. The gap is the release that made the map load-bearing without a check that a consumer can record it.

## Options Considered

1. **Run the version's doctor at eval prep and fail the cell on any failure.** Rejected: an older version's doctor fails the current fixture on expectations the fixture has since outgrown, so re-sweeps of old versions would break on unrelated drift.
2. **Make the required verbs a harness-owned list inside the build-pass schema, bypassing the layout.** Rejected: the layout is the single home for the gate facts ([2026-06-14](2026-06-14-layout-declares-the-project.md)); a second vocabulary source reintroduces the drift the one-home rule removed.
3. **Have setup and materialize edit `[gate].verbs` in place.** Rejected: the layout is project-owned, and a silent edit to a project file is the pattern the harness refuses everywhere else.
4. **Render every version's recorded gate verbs as a trend column.** Rejected after a first cut: the column overloads the sweep table, and a verb no version ever recorded is invisible in a union of recorded verbs. The signal belongs where the requirement is known, at the doctor and at eval prep.
5. **A doctor check against a manifest-declared required set, a prep gate on the bench, a materialize proposal and a setup warning, and the recorded verbs in the machine-readable series.** Chosen.

## Decision

**The engine-provided checks every stack's gate skill runs are declared once, in the doctor manifest's `[gate] required_verbs`, and every surface that judges a project's layout checks them there.**

- **The manifest declares.** `doctor-expectations.toml` `[gate] required_verbs` lists the engine-provided checks every stack's `code-quality-gate` skill runs: `handoff-log`, `autofix-audit`, `contracts-sync`, `conventions-map`. The stack's build verbs stay the project's to name. The list is stack-agnostic by construction; a verb only one stack runs never joins it. The manifest is the one home; shipped prose names the manifest, never the list.
- **The doctor fails.** `layout-gate-verbs` fails a present `[gate]` table whose `verbs` lacks a required verb, naming the verb and the mechanism. It skips when the optional table is absent, and when `verbs` is not a list, the shape failure `layout-gate` reports.
- **The bench refuses to measure the gap.** Once the engine sliver lands and any era swap is done, eval prep compares the installed manifest's required verbs with the layout the cell runs under. An undeclared verb fails the cell. When nothing can be checked, the prep line names why, so a re-sweep of a version with no requirement stands and reads as such.
- **Install surfaces say it.** `setup.sh` warns at install time with the missing verbs; `/materialize` proposes the insertion. Neither edits the layout.
- **The battery pins the producers.** Every stack's layout skeleton carries the required verbs, and the engine rows of every stack's gate table name exactly the required set. A verb added to a table without joining the manifest fails the battery. The build-pass append's enum miss names the layout key the vocabulary lives in.
- **The series records what ran.** Each rep's `gate_verbs`, the union of its build-pass records' `gate_checks_run`, lands in `trend-data.json`. The page tables are unchanged.

## Consequences

**Positive:**
- A required check that a project cannot record is a doctor failure and an eval prep failure, never a silent drop. The fixture's gap would have failed the first v0.4.11 cell at prep.
- The requirement has one home, and every reader of the layout checks against it with the same list.

**Negative:**
- Every pre-v0.4.11 consumer fails the doctor on its next run until it adds one verb. The failure names the verb and the fix is one line.
- No tagged row measures the map as a gate check yet. The partial v0.4.11 sweep ran it unrecordable and was discarded before recording. The dated note in `notes.toml` says so; the next sweep on the corrected fixture is the first measurement.
- A reading an ADR names without an arm still has no gate. This decision renders the fact into the series; whether readings become release checks is open.

## Implementation

`harness/core/scripts/doctor-expectations.toml` (`[gate]`), `harness/core/scripts/doctor.py` (`check_layout_gate_verbs`) and its tests. The `doctor` skill's check list and `docs/harness-project-api.md`. `harness/marketplace/setup.sh` and the root `materialize` skill. `evals/run_eval.py` (`gate_vocabulary`, the prep gate after the era swap; an `--era-contract` arm runs the version's own skeleton, so only the SUT-layout arm can fail), `evals/summarize.py` (`gate_verbs`), `evals/trend-data.schema.json`, and their tests. `harness/verify_harness/checks/sync.py` (the skeletons and the gate tables against the manifest). `harness/core/scripts/handoff/schema.py` (the enum miss names the layout key). `evals/README.md` § Run lifecycle and `evals/results/notes.toml`.

## References

- [Test Conventions at Write Time](2026-09-03-test-conventions-at-write-time.md) — the decision whose required check this one makes checkable, amended there with the finding.
- [Layout Declares the Project](2026-06-14-layout-declares-the-project.md) — the one-home rule for the gate facts that option 2 would have broken.
- [Deterministic Routing Engines](2026-07-02-deterministic-routing-engines.md) — the line that a mechanical promise becomes an engine check; the doctor check is that line applied to the vocabulary.
- [The Eval Bench](2026-07-15-the-eval-bench.md) — the prep gates this one joins and the series the void evidence sits in.
- [Docs as the Harness–Project API](2026-06-12-docs-as-harness-project-api.md) — why the layout stays project-owned and the surfaces propose rather than edit.
