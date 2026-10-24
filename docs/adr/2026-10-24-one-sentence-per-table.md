# A Data-Driven Test Holds One Sentence Per Table

**Status:** Accepted

## Context

The test doctrine the harness ships asked for data-driven tests wherever cases repeat. The `tdd-workflow` test rules said related cases are data-driven. The Java `test-review` checklist listed `@ParameterizedTest` for repetitive cases, flagged a missing one as an `autofix` issue, and asked a `@CsvSource` to cover all edge cases. The generic checklist said related cases are data-driven rather than copy-pasted. The implementer agents allowed a merge of several owed test names into one data-driven test. The `testing-principles` template carried a parameterized-tests convention row.

The doctrine measured the wrong thing. Repetition of shape is not what a table is for; repetition of the sentence is. A table whose rows share one sentence reads better than three copies, and a failing row names its input. A page value below one rendering the first page, over 0 and -1, is such a table. A table whose rows stop sharing a sentence hides behaviors. The signs: an outcome column that varies in kind, setup that differs per row, or a branch in the body. The reader then runs the table in their head to learn what the unit does. Aggregates and domain units show it first: their cases are scenarios, each with a name and a body built in plain sight.

The plan-file acceptance arm (arm `dev-fa42bcbf-dirty`, 2026-10-23, local) showed the direction a test-first implementer takes without the nudge. On the visit-edit task the plan arm merged two refusals into one `WhenInvalid` test; the test-first arm wrote one named test per edge case and used no parameterized form. Parameterized tests appeared at most twice per task in either arm, and the one that merged behaviors was the plan arm's. The doctrine had been pushing toward compression the implementers did not need and the reviewers had no criterion to refuse.

## Options Considered

1. **Keep the repetition rule.** Rejected: it rewards compression and gives the reviewer no way to call a table that hides behaviors.
2. **Ban data-driven tests.** Rejected: an input table over boundaries and equivalence classes is the form that case reads in, and Go's table-driven subtests are the stack's idiom.
3. **One sentence per table.** Chosen. A data-driven test is one assertion over an input table, and its name states every row. A row that differs in outcome kind, in setup, or by a branch in the body is a distinct behavior and gets its own named test.

## Decision

**We adopt option 3. The criterion is checkable without taste: does one sentence describe every row, and is the body straight-line?**

- The `tdd-workflow` test rule, the three stacks' `test-review` checklists, and the `testing-principles` template state the same rule, each in its surface's idiom.
- The Java checklist's "missing `@ParameterizedTest` for repetitive cases" becomes "several behaviors under one `@ParameterizedTest` name"; the generic checklist gains the same finding.
- The implementer's merge clause narrows to a table whose name states every row.
- Go keeps table-driven subtests; each row is a named case under one sentence, which is the same rule.
- The coverage rule keeps its measure; its decision-table sentence gains the outcome-kind qualifier, so a table whose rows yield the same kind of outcome stays one test.

## Consequences

**Positive:**
- Reviewers gain a mechanical question in place of a preference, and the finding points at the row that broke the sentence.
- Domain and aggregate tests read as scenarios, which is what `legible-cold` asks of them.
- No coverage moves: one test per decision path and one table per decision table stand as before.

**Negative:**
- Boundary cases a single table once held may appear as several named tests when an implementer judges the sentence broken. The reviewer's "second test through the same equivalence class" finding bounds that.

## Implementation

**Non-goal:** This is test doctrine, not a feature requirement. Surfaces: `tdd-workflow` § TDD Cycle test rules, `test-review` in each stack, the `testing-principles` template, `prd-authoring`'s `test_names` rule, and the `feature-implementer` agents' feature-scope line. The samples' briefs carry the new row as project-owned edits; other consumers carry it forward through their own `docs/testing-principles.md`.

## References

- [Coverage Map Joins the Walk](2026-09-03-coverage-map-joins-the-walk.md) — the walk that reads each owed name against the tests
- [The Implementer Keeps No Plan File](2026-10-20-the-implementer-keeps-no-plan-file.md) — the acceptance arm whose test shapes informed this decision
