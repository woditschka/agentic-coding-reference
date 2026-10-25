# Convention Checks Carry Their Evidence

**Status:** Accepted

## Context

The v0.4.9 and v0.4.10 sweeps record one test-quality pattern and one
design-fit pattern that the written rules already forbid. On
owners-page-param the judge scores test quality 3 on two of three v0.4.9 reps
and all three v0.4.10 reps. Each time the shapes are the same: a raw
`new Owner()` filler where the suite's named default exists, and a
`verify(argThat(...))` interaction assertion beside a behavioral one. On
specialty-directory r3 of v0.4.10 the judge scores design fit 3 for a
grouping written inside the controller, and three reviewers approved the
placement.

The rule for each shape sits at every stage. The implementer reads the
testing and architecture briefs in full, and its self-review walk names
construction through the entry point or a named default. The Java
test-review checklist lists raw constructions as an `autofix` finding and
names the listing command. The code-quality-review checklist grades a rule
landing in a controller as `blocked` when the catalog assigns a domain seam.
None of it changed the outcome.

The transcripts show why. Every stage is told to run
`python3 scripts/grading.py conventions-map`, the listing of added comments,
raw constructions, and literal-bearing lines. The dispatches that ran it:

| Role | v0.4.9 | v0.4.10 |
|---|---|---|
| feature-implementer | 9 of 23 | 7 of 25 |
| test-reviewer | 5 of 25 | 5 of 30 |
| code-quality-reviewer | 12 of 21 | 7 of 24 |

On owners-page-param the implementer ran it in no dispatch and the test
reviewer in one. Nothing downstream depends on its output, so the step is
optional in practice. The record form is the same whether the listing ran
or not.

## Options Considered

1. **Longer checklist lines** — rejected. The lines already state the rule
   and the command; a third restatement changes nothing about whether the
   step runs.
2. **A mechanical verdict on constructions** — rejected. The listing carries
   no verdict on its rows by design, the maps' shared precedent
   (ADR 2026-09-03). The named default is a
   project-specific convention the brief owns, and a regex cannot tell a
   value object with named arguments from a raw filler.
3. **Make the listing's output load-bearing at both stages** (chosen).

## Decision

**The conventions map joins the quality gate.** `conventions-map` is a
required check in every stack's `code-quality-gate` skill and a verb in the
`[gate]` vocabulary of `layout.toml`, so the gate skill records it in
`gate_checks_run`. The final gate runs it first and the self-review walk
reads its rows; a walk fix re-runs the gate before `build-pass`. The
checkpoint gate omits it, since nothing reads its rows there. A non-zero
exit is an environment fault, an unresolved base or head, a malformed
`[conventions]` table, or a git failure, and aborts `prerequisite-missing`
for the operator.

**Two reviewer clearances carry a named evidence form**, under
`review-workflow` § Claims Carry Their Evidence. A test-reviewer clearance
of construction or test data cites the `conventions-map` rows it walked. A
code-quality-reviewer clearance of placement walks the rules: one
`approved_aspects` entry per new or moved business rule, naming its landing
component and the assigning catalog row or principle. When no rule moved,
one entry says so. A full-pass record without the entry its change
calls for is an unwalked check, and the change-grader's `reviewer_hedging`
facet reads an approval missing it as a hedge.

**Interaction assertions are listed and cleared the same way.** The Java
test-review lists `verify(...)` calls in the changed tests. Each is cleared
by naming the behavioral assertion it does not duplicate, or is an
`autofix` finding. Go and generic carry the clearance rule without a
stack-specific listing command.

The briefs do not change. The rules were right; the evidence that they were
applied was missing.

## Consequences

**Positive.** The records become checkable offline: `gate_checks_run`
names the listing, and a construction or placement clearance quotes what it
checked. The eval bench counts the verb today; the clearance forms are read
from the records by hand until `summarize.py` learns them. The owners and
specialty-directory shapes now meet a mandated reader at three stages.

**Negative.** One bash call per final gate run and one or two per review,
since the Java test-reviewer also lists `verify(` calls; no additional
reads. A listing measures about 300 tokens in the v0.4.10 transcripts. A
consumer whose `layout.toml` predates the verb records a `build-pass` the
schema rejects until the verb is added. The rejection lists the accepted
verbs, and the gate row names `[gate].verbs` as their home. A marketplace
consumer makes that edit by hand.

**Scope.** The evidence forms cover the two gaps the sweeps measured. The
design stage, the doc-reviewer, and the security-reviewer carry none yet.
A `design-block` names patterns and integrations but not the landing
component of a slice's new rule; that is the next gap if the placement walk
finds rows missing.

**Readings on the next tagged sweep**, none an acceptance arm: the listing
in `gate_checks_run` on every `build-pass`, and a cited construction
clearance or finding on every test-reviewer record over new tests. A
placement walk appears on every code-quality-reviewer record. The owners-page-param test-quality
median is back at 4. A tagged row that misses them reopens this ADR.

## References

- [2026-09-07 one-construction-api-briefs-before-the-writer](2026-09-07-one-construction-api-briefs-before-the-writer.md):
  the construction rule and the conventions map this decision makes
  load-bearing.
- [2026-09-03 coverage-map-joins-the-walk](2026-09-03-coverage-map-joins-the-walk.md):
  the maps' no-verdict precedent; the conventions map now also runs in the
  gate, which that ADR's status records.
- [2026-08-15 contracts-sync-joins-the-gate](2026-08-15-contracts-sync-joins-the-gate.md):
  the last verb added to the `[gate]` vocabulary and the consumer path it
  set.
- [2026-08-10 a-prod-test-pair-is-one-module](2026-08-10-a-prod-test-pair-is-one-module.md):
  the self-review walk this decision orders after the final gate.
