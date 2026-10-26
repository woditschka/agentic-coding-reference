# Test Conventions Are Decided at Write Time and Carry Their Evidence

**Status:** Accepted

## Context

The test reviewer's findings were the pipeline's largest recurring fix-round source, and each class it found was one the written rules already covered. The v0.3.3 to v0.3.8 eval rows carry 35 fix-routable first-pass test-reviewer findings; 19 name a PRD edge case or a Done-when bullet with no test. The v0.3.9 sweep's 36 blind-judge samples never score test quality at 5. The deductions fall into classes the fixture's testing brief rules on. A comment restating the code (24 of 36), a raw domain constructor in a test (19), a framework stub or interaction assertion without a recorded exception (19). A bare literal (15), copy-paste twin tests (9), a naming breach (8).

The transcripts show why the rules did not reach the code. The implementer saw the testing brief in 8 of 27 dispatches and the architecture brief in 1 of 32. The Scoping Pre-Check named neither as durable memory. The Test-Conventions Walk told the implementer to match the host file's idiom, which in a suite that predates the brief means copying its debt. The construction rule itself, "wrap the constructor in a test-owned factory", hid the varied value and put a second construction path in the test tree.

Two later readings sharpened the doctrine. The data-driven rule rewarded compression: the plan-file arm (`dev-fa42bcbf-dirty`, 2026-10-23) merged two refusals into one `WhenInvalid` test, and reviewers had no criterion to refuse a table that hides behaviors. And the v0.4.9 and v0.4.10 sweeps record a raw `new Owner()` beside the suite's named default and a `verify(argThat(...))` beside a behavioral assertion. The judge scored test quality 3 on five of six owners-page-param reps. Every stage was told to run the conventions listing; nothing downstream depended on its output, so the step was optional in practice.

## Options Considered

1. **A gate check on declared test names.** Rejected: 181 of 195 declared names appeared in the patch. The 14 misses were renames in runs that cleared the bar, so a presence gate creates fix rounds.
2. **A gate check on edge-case citations per capability group.** Rejected: charges the slice for the group's pre-existing debt; the walk rule is per requirement.
3. **A deterministic map the walk works from, cited by the reviewer, with no verdict.** Chosen.
4. **Test-owned factories** (status quo). Rejected: a second construction API per type; `createShipment(a, b, c, d)` hides which argument the test is about.
5. **Test data builders in the test tree.** Rejected: the same second API, now one type per aggregate with withers that exist only for tests.
6. **A builder on the production type.** Rejected: a half-built mutable stage, and the mandatory parameters vanish from any signature.
7. **One construction API on the type, with copies for optional attributes.** Chosen.
8. **Keep the data-driven repetition rule.** Rejected: rewards compression and gives the reviewer no way to call a table that hides behaviors.
9. **Ban data-driven tests.** Rejected: an input table over boundaries is the form that case reads in, and Go's table-driven subtests are the stack's idiom.
10. **One sentence per table.** Chosen.
11. **Longer checklist lines.** Rejected: the lines already state the rule and the command; a restatement changes nothing about whether the step runs.
12. **A mechanical verdict on constructions.** Rejected: a regex cannot tell a value object with named arguments from a raw filler; the named default is a project convention the brief owns.
13. **Make the listing's output load-bearing at the gate and in reviewer clearances.** Chosen.

## Decision

**The implementer decides coverage, construction, and test shape at write time from two deterministic maps and the full principle briefs. The gate records the conventions map, reviewer clearances cite its rows, and neither map carries a verdict.**

- **The coverage map.** `grading.py coverage-map --feature <req_id>` lists the requirement's Done-when bullets, its declared test names beside the files that define them, and the group's numbered edge cases. Edge cases are listed, never matched; a citation comment in a test is narration the testing brief bans. Exit is always zero and nothing records it. The walk resolves each absent row with a test, a rename note, or a note naming why the case is outside the slice. The test reviewer runs the same map; a listed case is a prompt to read the tests, never a finding by itself. The map's measure is the count of those two classes, an uncovered edge case or Done-when bullet, in the next three-rep row against the 19 recorded.
- **The conventions map.** `grading.py conventions-map` lists added comment blocks, raw test constructions, and literal-bearing test lines per file. It is a required check in every stack's `code-quality-gate` skill and a verb in the `[gate]` vocabulary of `layout.toml`, recorded in `gate_checks_run`. The final gate runs it first and the self-review walk reads its rows; a walk fix re-runs the gate before `build-pass`. The checkpoint gate omits it. A non-zero exit is an environment fault and aborts `prerequisite-missing`.
- **One construction API per domain type.** The entry point is the constructor or one named creator such as `Address.of(...)`, taking every mandatory parameter and enforcing the invariants. A named creator earns its place where the name adds meaning or input is normalized first. Optional attributes are set through `with` copies routed through that entry point; attributes that belong together form a value object with one wither. Where the group is small and its order reads itself, the wither may take the parts directly as a thin overload. A change a business rule governs is a named operation, never a wither. Tests use exactly the API production uses; an irrelevant instance hides behind a one-line named default such as `anOwner()`. A value object with all-named arguments may be constructed directly. The model is a Pattern Catalog entry open to a project's brief; the kernel keeps only invariants at construction.
- **The briefs bind where they speak.** `docs/architecture-principles.md` and `docs/testing-principles.md` are mandatory full reads in the implementer's Scoping Pre-Check, outside the fewer-reads bias. Host-file idiom governs only where the brief is silent; a host file that predates the brief is debt to leave.
- **Code is self-documenting first.** A comment a better name would make redundant is a rename. A doc comment on a public type states its purpose in one sentence; none restates a signature, sits on a private member, or sits on a test. The code-quality checklists list every added comment line.
- **A data-driven test holds one sentence per table.** It is one assertion over an input table, its name states every row, and its body is straight-line. A row that differs in outcome kind, in setup, or by a branch is a distinct behavior with its own named test. Go keeps table-driven subtests under the same rule. The implementer may merge owed test names only into a table whose name states every row. Coverage is unchanged: one test per decision path, one table per decision table.
- **Clearances carry a named evidence form**, under `review-workflow` § Claims Carry Their Evidence. A test-reviewer clearance of construction or test data cites the `conventions-map` rows it walked. A code-quality-reviewer clearance of placement holds one `approved_aspects` entry per new or moved business rule, naming its landing component and the assigning catalog row or principle. When no rule moved, one entry says so. The Java test-review lists `verify(...)` calls, each cleared by naming the behavioral assertion it does not duplicate or filed `autofix`. Go and generic carry the clearance rule without a listing command. A full-pass record without the entry its change calls for is an unwalked check; the change-grader's `reviewer_hedging` facet reads it as a hedge.

The document-writing standards gained two rules with the construction decision: prose describes the current state, and unusual inputs are named by their shape rather than by attack metaphor.

## Consequences

**Positive:** the two dominant test-reviewer finding classes became write-time rows the implementer sees before declaring gate-pass. The varied value is visible at the call site; production, persistence mapping, and tests share one API. Reviewers hold a mechanical question in place of a preference, and a finding points at the row that broke the sentence. The records are checkable offline: `gate_checks_run` names the listing, and a construction or placement clearance quotes what it checked.

**Negative:** only declared names are string-checked; whether a listed edge case has a test stays the walk's judgment and the reviewer's read. One short method per free optional attribute on the type. Two more reads per implementer dispatch, about ten thousand cached tokens; one listing measures about 300 tokens. The eval fixture's briefs keep the old rules until their next epoch, so the judge series moves only after that dated condition change. A consumer whose `layout.toml` predates the `conventions-map` verb records a `build-pass` the schema rejects until the verb is added; the rejection lists the accepted verbs. The design stage, the doc-reviewer, and the security-reviewer carry no evidence form yet.

The run rates that made the listing load-bearing, dispatches that ran `conventions-map`:

| Role | v0.4.9 | v0.4.10 |
|---|---|---|
| feature-implementer | 9 of 23 | 7 of 25 |
| test-reviewer | 5 of 25 | 5 of 30 |
| code-quality-reviewer | 12 of 21 | 7 of 24 |

**Readings on the next tagged sweep**, none an acceptance arm. The listing in `gate_checks_run` on every `build-pass`, and a cited construction clearance or finding on every test-reviewer record over new tests. A placement walk appears on every code-quality-reviewer record. The owners-page-param test-quality median is back at 4. A tagged row that misses them reopens this decision.

## Implementation

`scripts/grading/coverage.py` and the `grading.py` CLI. `tdd-workflow` (pre-check, walk, test rules) and `tdd-principles.md` (`legible-cold`). Every stack's `code-quality-gate`, `test-review`, and `code-quality-review`, with the `[gate]` vocabulary in `layout.toml`. `review-workflow` § Claims Carry Their Evidence. The doctor's `testing-principles` and `architecture-principles` templates, `prd-authoring`'s `test_names` rule, and the `feature-implementer` agents' read discipline.

## References

- [Deterministic Routing Engines](2026-07-02-deterministic-routing-engines.md) — the mechanical-promises-into-engines line and the contracts-sync gate check, the precedent the coverage map stops short of and the conventions map follows
- [Module Derivation](2026-07-17-module-derivation.md) — the production-test pair as one module, whose self-review walk now runs after the final gate
- [Slice Sizing and the Checkpoint](2026-10-20-slice-sizing-and-the-checkpoint.md) — the plan-file acceptance arm whose test shapes informed the one-sentence rule; the checkpoint gate that omits the listing
- [Docs as the Harness–Project API](2026-06-12-docs-as-harness-project-api.md) — the briefs are project-owned, so the templates change now and a consumer's copy on its own schedule
- [Model Tiering](2026-06-11-model-tiering.md) — the Test Placement section and design-placement check, decided in its sixth amendment, the precedence rule's sibling
- [The Change Grader](2026-06-05-the-change-grader.md) — the `reviewer_hedging` facet that reads a missing clearance as a hedge
- [Documentation Standards](2026-06-13-documentation-standards.md) — the standard that gained the current-state and input-shape rules
