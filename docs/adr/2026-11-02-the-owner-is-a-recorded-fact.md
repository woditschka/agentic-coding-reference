# The Owner's Reach Is a Recorded Fact, and a Split Slice Routes Its Own Continuation

**Status:** Accepted

## Context

The 2026-10-30 sweeps measured v0.4.10 and v0.4.12 on the same fixture base and found the runtimes level on cost while the base change doubled it. The ledgers exposed four places where an unattended run paid for a decision the harness leaves to a human who is not there, or to the root's improvisation.

A human-targeted `consultation-request` halts the pipeline (`human-consultation`, [the root-conversation decision](2026-06-19-the-product-expert-and-the-root-conversation.md)). The halt is right when an owner can answer. The eval prompt states that no further product answer will come and asks for the narrowest reading. That sentence lives in the intake's `request`, which the schema makes context, never authority. On visit-edit the security reviewer blocked on an unbounded description length. The implementer consulted the design expert, the product expert, the design expert again, and then the human. The run ended there on both runtimes, with the grader never run. The agents read the gap as a security call rather than a product one, because nothing told them the owner's absence covered every question.

A `wrong-shape-slice` abort re-splits a requirement into slices under one `req_id`. After the first slice graded, `route` returned `feature-complete`, a blocked decision, and the skill text says blocked halts for a human. The root searched the installed skills for a continuation rule, found none, and dispatched the product expert for slice 2 on its own judgment. The decision was sound and the rep cleared, but the engine never made it and the ledger does not name it.

The ten-cycle cap lives in the implementer's Scoping Pre-Check. On vets-specialty-filter the product expert wrote 14 to 18 owed test names, the implementer spent a dispatch discovering the overflow, and the re-split followed. The PRD skill's own "too big" test said nothing about the count.

The security brief template told reviewers that an unlisted gap is "raised once, as a `clarify` finding to the owner". That sentence is routing written into a project-owned brief, and the reviewer read "owner" as the human. A doc-reviewer autofix finding that named two files failed root's static check. It redispatched the owner for a two-sentence edit, twice in one sweep.

## Options Considered

1. **Put the standing instruction in the briefs.** A Standing Gaps entry or a PRD open question would carry the owner's absence. Rejected: the briefs feed agents and the ledger feeds engines ([docs as the API](2026-06-12-docs-as-harness-project-api.md)). Nothing in `route` can read a brief, so `human-consultation` would still block whatever the brief said.
2. **Have root compose the `consultation-response` from the recorded decisions.** Rejected: the response transcribes a human's reply or does not exist; a root-authored answer is the shortcut the root-conversation decision forbids.
3. **Make the implementer continue past a human question whenever it judges the run unattended.** Rejected: a judgment call per agent, invisible in the log, and wrong the moment an owner is present.
4. **Record the owner's reach on the intake record and a split's position on the entry, and let `route` act on both.** The cap and the gap rule move to their authoring surfaces. Chosen.

## Decision

**The owner's reach and a slice's place in a split are facts in the ledger, and the engine routes on them.**

- **`intake-decision` carries `owner_present`.** Absent or `true` keeps the pause. `false` records the owner's standing instruction that no further answer will come. The interactive intake records it when the owner says so; the headless seed records it on every unattended run.
- **`route` resumes the requester when the owner is absent.** A human-targeted request on such a slice is a `dispatch` of its author (rule `owner-absent`, `resume: true`). The dispatch carries the intake's `decisions` as `standing_decisions`, text root relays and never executes. Presence is read from the slice's latest intake *before* the request: an intake appended afterwards never releases a pause, so the sticky-pause contract stands. The requester proceeds at the narrowest reading consistent with the decisions and records the open question in its own record: the implementer in `.scratch/escalations.md`, an expert in the `notes` of what it appends. No `consultation-response` exists, because nobody composed one. The resume runs once; a second human-targeted request on the slice halts (`owner-absent-repeat`), so the loop has the ceiling every other cycle in the engine has. That halt is also the refusal path: a pushback the decisions cannot lift is re-raised once and the run ends without a change. The owner-present consultation path is unchanged, and an owner-absent slice never masks another slice's pause.
- **`prd-entry` carries `slice_of`.** Every entry of a split under one `req_id` names its `index` and the planned `of`. After a slice closes, by its grader verdict or by the roster's approval with grading off, `route` dispatches the product expert for the next (rule `next-slice`) until the last, which closes the feature as before. The plan is honored only while it is well formed: product-expert authored, indexes climbing by one from 1, `of` never growing and at most 9. An index repeats only while its slice is open, the PRD fix round; after the slice closed the next index is due. Gate 1 bounces an entry that breaks the sequence, judging it against the entries it accepted so a bounce never binds the correction; a verdict with no build behind it continues nothing. This cycle therefore has a ceiling an agent cannot raise, like every other cycle in the engine. `refactor-resume` keeps precedence. A later slice scopes against the working tree the earlier ones left, and its review cycle counts from its own entry. The attended owner's merge point moves to the last slice: an owner who wants to merge between slices interrupts the run, where before the pipeline halted after every slice.
- **The size cap applies at authoring, counted in owed test names.** The PRD skill's "too big" test names it: more than twelve owed `test_names` entries splits before the entry is appended. A split that would leave a sibling of one or two cycles is not made. The implementer's abort stays the backstop for a slice that spans two behaviors. The first arm showed why the measure matters. Counted in cycles with the criteria added, an eight-name request split into eight cycles plus one; the one-cycle sibling cost $4.70 of pipeline overhead.
- **Routing leaves the brief.** The Standing Gaps template holds the list. The stack `security-checks` skills say an unlisted gap is named once in the review record, a `blocked` finding or an `approved_aspects` clause, and listed by the brief's owner after the run, never a question to the human. The autofix protocol admits one file per finding.

## Consequences

**Positive:**
- An unattended run no longer ends on a question the standing decisions can answer, and never asks the root to decide a continuation the engine can decide. Both facts are in the ledger: the intake line and the entry's `slice_of`. A question the decisions cannot answer still ends the run, now under a named rule.
- The owner-present path is byte-for-byte what it was. A project that never records `owner_present` or `slice_of` routes exactly as before; the replay oracle shows no difference on the recorded ledgers.
- The eval bench stops depending on agents reading a prompt sentence as authority.

**Negative:**
- An attended owner loses the halt between slices: the merge point moves to the last slice, and an owner who wants to merge earlier interrupts the run.
- An absent owner's open questions accumulate in the requesters' records with no gate on their count. The design expert's own re-split path, a `conflicting` verdict that halts for fresh scoping, is not a consultation and still ends an unattended run.
- Append authority stays schema-only: any process can write an `intake-decision` with `author: "human"`. The order-aware read keeps that from releasing a pause; it does not keep a forged first intake from declaring the owner absent, which is the same trust the `decisions` list already extends to the record.
- The cap at authoring moves a dispatch's worth of discovery into the product expert's judgment, which the engine does not check. An entry that still overflows reaches the implementer's abort as before.
- Two new rules join the inventory, and the handbook, the glossary, and the design doc's state table all gained a clause.

### Acceptance arm

Several teams run the harness, so the decision ships behind a measured `--version dev` sweep on the current fixture base. The sweep runs all five tasks at three reps per task; `release-version` refuses the cut until the result is recorded here. The readings, every one required:

- The bar at 15 of 15, the refusal reps ending on two recorded requests and `owner-absent-repeat` with no source change.
- No `human-consultation` halt and no root-side pause on any feature rep: the second-review-failure pause stands down under an absent owner.
- Every re-split continuing through `next-slice`, slice 2 reviewed from round 1 and graded, with no root-authored dispatch.
- No `wrong-shape-slice` abort where the entry's owed count was over the cap at authoring, and no split that leaves a sibling under three cycles.
- A rep-set within 10 percent of the old base's $18.90, and the judge's test-quality median at 4 on owners-page-param.

**First reading, 2026-11-02.** Arm `dev-3e227fb3-dirty`, two reps per task before the chapter pause stood down. 9 of 10 on the bar, no consultation on any feature rep, both refusals on two requests, owed names back to 1 to 8. A rep-set of $19.73 against v0.4.12's $30.87 on the same base. The one failure was the split rep: slice 1 failed review twice, the root paused under the chapter rule, and slice 2 never ran. The arm proper runs after that pause is gated.

**Second reading, 2026-11-03.** Arm `dev-ca769f87-dirty`, stopped after six reps: 6 of 6 on the bar. The first split carried through `next-slice` with no root hop, both grader runs, slice 2 reviewed from round one. The split itself was the finding: eight cycles plus one, $10.21 and 35 minutes against $5.84 for the same request batched. The cap is therefore re-measured in owed names, and the batching test outranks it, before the arm resumes.

**Third reading, 2026-11-03.** Arm `dev-49e1032a-dirty`, three reps per task, complete. 15 of 15 on the bar; a rep-set of $19.41 against the old base's $18.90; test-quality 4 on every owners-page-param rep; no split, no overflow abort; every refusal on two requests. Four readings hold. The fifth failed on one rep. A design-expert question to the owner about a brief wording was superseded by the implementer's unrelated request on the same slice, so the owner-absent resume never fired. The brief finding then routed to the implementer, and the root paused on a `docs/` edit outside the slice's target. Two fixes follow. A later specialist request supersedes only its own author's pending human question. The architecture and vocabulary briefs route to their stewards, who record the proposal as an open point a reviewer states in one clause. The arm reruns on that tree.

## Implementation

The managed `CLAUDE.md` chapter's Confirmation Discipline (the review-failure and pipeline-verdict pauses wait for a present owner). `harness/core/scripts/handoff/records.py` (`IntakeDecision.owner_present`, `PrdEntry.slice_of`, `SliceOf`), `ledger.py` (`owner_present_for`, `pending_human_requests`, the slice reset in `cycle_start`), `routing.py` (`_owner_absent` with `owner-absent-repeat`, `_slice_closed`, `_slice_plan` over the accepted entries, `_slice_continuity_errors`, the invalid-response bounce to its author), `findings.py` (the brief stewards), the intake-decision, prd-entry and consultation-request schemas, and their tests. `route-rules.md` regenerated. `handoff-routing` (`SKILL.md`, `route-spec.md`), `intake`, `prd-authoring`, `tdd-workflow`, `document-writing/autofix-protocol.md`, `review-workflow/reference.md`, the security template, the three stacks' `security-checks` and `design-validation` skills, the three stacks' `feature-implementer` and `system-design-expert` agents, the product expert agent, the `next`, `change-grading`, `audit-agents` and `handoff-append` skills, the managed `CLAUDE.md` chapter, `docs/harness-project-api.md`, `docs/project-history.md`, and `evals/README.md`. `evals/run_eval.py` seeds `owner_present: false` when the version's schema declares the field. The handbook, the glossary, and `docs/harness-system-design.md`.

## References

- [The Product Expert and the Root Conversation](2026-06-19-the-product-expert-and-the-root-conversation.md) — the human target and the pause this decision keeps for a present owner.
- [Docs as the Harness–Project API](2026-06-12-docs-as-harness-project-api.md) — why the fact lives in the ledger, not in a brief.
- [Slice Sizing and the Checkpoint](2026-10-20-slice-sizing-and-the-checkpoint.md) — the size cap this decision moves to authoring and re-measures in owed names.
- [Deterministic Routing Engines](2026-07-02-deterministic-routing-engines.md) — the line that a decision the engine can make, it makes.
- [The Gate Vocabulary Is Checked](2026-10-30-the-gate-vocabulary-is-checked.md) — the sweep whose ledgers surfaced the four cases.
