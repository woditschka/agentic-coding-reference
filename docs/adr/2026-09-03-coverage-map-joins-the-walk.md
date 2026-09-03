# The Coverage Map Joins the Test-Conventions Walk

**Status:** Accepted

## Context

The v0.3.3 to v0.3.8 eval rows carry 35 fix-routable first-pass findings
from the test reviewer. By description keyword, 19 name a PRD edge case
or a Done-when bullet that has no test. Each buys a fix round: an
implementer dispatch plus the dissenter's re-review. The Test-Conventions
Walk already names both classes as write-time decisions, and the
implementer still misses them in roughly one feature run in three.

The precedent for a recurring mechanical class is to move it to write
time, as the contracts-sync gate check did for the doc-reviewer's
dominant critical. This class has no gate-shaped floor. Over the last
`prd-entry` of each of those rows' runs with a recorded patch, 181 of
195 declared test names appear in the patch. The 14 misses are renamed
tests in runs that cleared the bar. A presence gate would therefore
create fix rounds, not remove them. Edge cases are numbered per
capability group, not per requirement, so an edge-case gate would bounce
a slice for its group's pre-existing debt. Whether a test covers a bullet
is judgment.

## Options Considered

1. **A gate check on declared test names** — rejected: 7% false positives
   on renamed tests, each one a fix round the check exists to prevent.
2. **A gate check on edge-case citations per group** — rejected: charges
   the slice for the group's debt; the walk rule is per requirement.
3. **A map the walk works from, cited by the reviewer** (chosen).

## Decision

**The walk gains a deterministic coverage map; nothing gates on it.**
`grading.py coverage-map --feature <req_id>` renders the requirement's
Done-when bullets, its declared test names beside the test files that
define them, and the capability group's numbered edge cases as a list.
Edge cases are listed, never matched: the first dev rep showed that a
citation comment in a test is narration the testing brief bans, and the
judge scored it as such. Exit is always zero, nothing
is recorded in `gate_checks_run`, and no `layout.toml` verb is added, so
the eval's subject project needs no change. The Test-Conventions Walk
runs the map and resolves each absent row with a test, a rename note, or
a note naming why the case is outside the slice. The test reviewer runs
the same map and cites it; a listed case is a prompt to read the tests,
never a finding by itself.

## Consequences

**Positive:** the two dominant test-reviewer finding classes become
write-time rows the implementer sees before declaring gate-pass, at the
cost of one script run. The measure is the count of those two classes in
the next three-rep row against the 19 recorded.

**Negative:** only declared names are string-checked. Whether a listed
edge case has a test is the walk's judgment and the reviewer's read, and
a group's pre-existing debt shows as listed cases the slice may note
rather than fix.

## Implementation

`scripts/grading/coverage.py`, pure functions over text; the CLI in
`scripts/grading.py`; wiring in the `tdd-workflow` walk and the three
`test-review` checklists.

## References

- [`2026-08-15-contracts-sync-joins-the-gate.md`](2026-08-15-contracts-sync-joins-the-gate.md) — the precedent this map deliberately stops short of
- [`2026-07-14-mechanical-promises-into-engines.md`](2026-07-14-mechanical-promises-into-engines.md) — the line this decision extends
- [`tdd-workflow` § Test-Conventions Walk](../../harness/core/.claude/skills/tdd-workflow/SKILL.md#test-conventions-walk) — the walk the map serves
