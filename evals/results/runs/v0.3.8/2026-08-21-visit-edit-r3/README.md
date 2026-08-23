# visit-edit r3 — v0.3.8

Edit a booked visit (feature) · started 2026-08-21T21:51:46+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Feature request: visits can currently only be created, never corrected. Two
> product decisions come with it, made here as the product owner:
> 
> - Non-goal NG-5 is narrowed: cancelling a booked visit stays out of scope,
>   but correcting its date and description is now in. Record the narrowing
>   the way the project records non-goal changes.
> - The edit form is reachable by its URL alone: the owner detail page gains
>   no edit link in this request. A visible entry point may come as a
>   follow-up request.
> 
> Add editing for a booked visit:
> 
> - GET /owners/{ownerId}/pets/{petId}/visits/{visitId}/edit shows the visit
>   form prefilled with that visit's current date and description. Reuse the
>   existing visit form template (pets/createOrUpdateVisitForm) and its  visit
>   model attribute.
> - POST to the same URL validates like visit creation (description required,
>   date in the future). On success it updates that visit in place — the pet
>   must not gain an additional visit record — and redirects to the owner
>   detail page. On validation failure it redisplays the form.
> 
> Cover the new behavior with tests.
> 
> These are all the product decisions; no further product answer will come
> during the work. Where a choice still seems open, take the narrowest reading
> consistent with this request and record the open question rather than
> waiting.

## Verdict

| check | result |
|---|---|
| oracle | ✔ 4/4 passed |
| suite (post-agent) | ✔ |
| suite (pristine baseline) | ✔ |
| checkpoints | 7/7 |
| review attention (pipeline grade) | concern |

The pipeline grade estimates how much human review the change deserves before merge — advisory context from the harness's change grader (read from the ledger's `grader-verdict` record), never part of the bar.

- ✔ `theEditFormShouldPrefillTheExistingVisit` — passed
- ✔ `theEditSubmissionShouldUpdateTheVisitInPlace` — passed
- ✔ `theEditSubmissionWithABlankDescriptionShouldRedisplayTheForm` — passed
- ✔ `theNewVisitFormShouldRenderForTheExistingPet` — passed

## Checkpoints

The kind's graded ladder, derived from the recorded facts — context only, outside the quality bar (bench README § Checkpoints).

- ✔ `agent complete`
- ✔ `change produced`
- ✔ `suite green`
- ✔ `theEditFormShouldPrefillTheExistingVisit`
- ✔ `theEditSubmissionShouldUpdateTheVisitInPlace`
- ✔ `theEditSubmissionWithABlankDescriptionShouldRedisplayTheForm`
- ✔ `theNewVisitFormShouldRenderForTheExistingPet`

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 5 (±1) | 4 (±0) | 4 (±1) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.92. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> VisitController reuses loadPetWithVisit via an optional {visitId} path variable and folds the date rule into rejectDateNotLaterThanToday, so booking and correction share one rule and one view constant; findVisit resolves strictly by owner-pet-visit traversal. The rule stays in the controller rather than adopting the available Form validator pattern - reuse, not a fresh rule, but a missed seam. Tests are behavior-named (theCorrectedVisitShouldLeaveThePetWithNoAdditionalVisit), constants tiered, construction behind createOwnerWithABookedVisit/createVisit; deductions for narration comments ('// Nothing reaches the repository...') and ArgumentCaptor/never() verification where a hand-written double was the stated first choice. Docs move everywhere the change touches: narrowed NG-5, new ADR plus index row, REQ-VISITEDIT-001 with done-when, contracts table, threat row, glossary.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The controller extends the existing  loadPetWithVisit  seam with an optional  visitId  and resolves by owner→pet→visit traversal, so correction saves through the  Owner  aggregate root and adds no visit ( this.owners.save(owner) ); the shared  rejectDateNotLaterThanToday  helper and  VIEWS_VISITS_CREATE_OR_UPDATE_FORM  constant remove the duplication the second flow would have created, and no new type or rule is introduced. Tests are behavior-named ( theCorrectedVisitShouldLeaveThePetWithNoAdditionalVisit ), use tiered constants and factories, but lean on  ArgumentCaptor / then(...).should(never())  interaction checks and duplicate the blank-description case across two tests. Comments like "// Nothing is saved, so the stored visit keeps the values..." restate the code. Docs are complete: ADR, README index, narrowed NG-5, REQ-VISITEDIT-001, contracts, threat row, vocabulary, open questions.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 5 · doc-fit 5

> The edit path reuses the existing  loadPetWithVisit  @ModelAttribute with an optional  visitId , and  findVisit  mirrors the controller's existing owner→pet traversal and  IllegalArgumentException  style; the date rule is extracted into  rejectDateNotLaterThanToday  rather than copy-pasted, and the view name becomes a shared constant — no new rule enters the controller. Tests are behavior-named ( theCorrectedVisitShouldLeaveThePetWithNoAdditionalVisit ), use factories ( createOwnerWithABookedVisit ,  createVisit ) and named constants with zero bare literals; they lose a point for interaction-level assertions ( then(owners).should(never()).save(...) , ArgumentCaptor), a narration comment ("Nothing reaches the repository..."), and adding only web-layer tests. Documentation is complete: new non-goal ADR, ADR index row, narrowed NG-5, REQ-VISITEDIT-001 with done-when and edge cases, open questions, contracts and threat-model rows, and a  Visit correction  vocabulary entry.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $12.64 | 29m | 4 | 93% | 7 file(s) +269/−19 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.06 | 3m 32s | 90% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VISITEDIT-001 — Staff can correct a booked visit's date and description

2 review rounds · 2 build-passes · **1 build-failure** · grade **CONCERN**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (1) | **✔** |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Staff can correct a booked visit's date and description · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **minor** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 7m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **minor** · (design) · supersedes L5 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · checkFormat · checkstyleMain · handoff-validate · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 57s***
  - [autofix] `VisitController.java:59-70` The `loadPetWithVisit` Javadoc was expanded with a new paragraph explaining booking vs. correction traversal, but the newly added `visitId` parameter has no `@param visitId` tag, and the pre-existing `@param ownerId`/`@param model` gaps were left untouched while the block was being edited. The `@return Pet` tag is also stale (the method returns `Visit`, not `Pet`) — since this comment block was touched by this change, it is the right moment to bring the tags in line with the signature.
    - fix: Add `@param visitId` documenting that a null value books a new visit and a non-null value names the visit to correct; add the missing `@param ownerId` and `@param model` tags; correct `@return Pet` to `@return Visit`.
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [autofix] `VisitControllerTests.java:219` PRD edge case 3 for REQ-VISITEDIT-001 names two refusal scenarios: 'Correcting a visit that does not belong to the named pet, or a pet that does not belong to the named owner, is refused.' Only the first half is tested (theVisitCorrectionShouldBeRefusedWhenTheVisitDoesNotBelongToThePet, using VISIT_ID_OF_ANOTHER_PET). The second half — a petId that does not belong to the owner named in the URL — has no dedicated test for the correction flow, even though loadPetWithVisit's owner.getPet(petId) null-check (VisitController.java:78-82) is the code path that enforces it.
    - fix: Add a test asserting the correction POST (or GET) is refused with an IllegalArgumentException-rooted ServletException when petId does not belong to TEST_OWNER_ID's owner, mirroring the existing 'visit does not belong to pet' test. Consider a @ParameterizedTest over the two edge-case halves (mismatched visitId, mismatched petId) sharing one assertion body per the naming-school and DRY guidance in testing-principles.md.
- ✔ **review security** · **approved** · ***◷ 2m***
  - ▹ rec: Supply-chain check not run: the OWASP dependency-check plugin is not configured in build.gradle (plugins are java, checkstyle, jacoco, spring-boot 4.1.0, dependency-management 1.1.7, graalvm native 1.1.2, cyclonedx 3.2.4, javaformat 0.0.47, nohttp 0.0.11), and this reviewer has no network access, so no NVD match was performed. The resolved versions in this diff are unchanged from the base tree, so the gap is not introduced by REQ-VISITEDIT-001; closing it (CI dependency-check over the published CycloneDX SBOM) is a project-level follow-up, not a finding against this slice.
  - ▹ rec: processVisitCorrectionForm takes @ModelAttribute Owner owner and then saves it, so request parameters bind onto non-identifier Owner fields (firstName, lastName, address, city, telephone) on the correction POST, unvalidated. This is copied verbatim from the pre-existing processNewVisitForm, reaches nothing an attacker cannot already reach at /visits/new, and identifier binding stays disallowed, so it does not leave the application weaker than the recorded baseline. Worth noting only because a demonstration app is read and copied: a future round could take the visit alone and re-read the owner from the repository before saving.
- ↻ **implement** (implementer) ← code-quality, test · (2 findings) · ***◷ 3m***
  - ▲ **build ✓ clean** · build · test · checkFormat · checkstyleMain · handoff-validate · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 28s***
- ✔ **review doc** · **approved** · ***◷ 24s***
- ✔ **review test** · **approved** · ***◷ 38s***
- ◆ **grade CONCERN** · add visit correction alongside booking
  - blast_radius — **clear** — Two code files in one module: VisitController and its test. The only shared surface touched is loadPetWithVisit, which every VisitController handler runs through, but the booking path is preserved by construction (a null visitId keeps the old fresh-visit branch) and the pre-existing booking tests still cover it. No sensitive paths, no templates, no other controllers, no schema or dependency change; the five doc files are additive records of the same decision.
  - semantic_surprise — **concern** — The Java is honest and does what it says, but the correction reuses pets/createOrUpdateVisitForm.html unchanged and the diff gives no hint of what that renders. The submit button on the correction page resolves the addVisit message key and reads 'Add Visit'; the 'Previous Visits' table below it iterates the pet's visits filtered to non-new, so the visit being corrected now lists itself there. Because MVC binds form input straight onto that same managed Visit instance, a refused correction re-renders with the rejected date and description showing in the 'Previous Visits' row as if stored. The code comment 'Nothing is saved, so the stored visit keeps the values it was booked with' is true of the database and misleading about the page, and no test asserts rendered HTML for the correction screen.
  - test_adequacy — **clear** — Eight new tests drive the real MVC dispatch, binding, and validation stack through MockMvc rather than restating the implementation, and they would genuinely fail against a broken version: the single-visit assertion on the captured saved owner catches a findVisit that created instead of resolved, the two refusal cases catch a traversal check that stopped enforcing owner then pet then visit, and the never-save assertion catches a refusal path that persisted. Assertions run against the real Owner-Pet-Visit graph captured off the repository, with Mockito confined to the repository seam the existing suite already mocks.
  - reviewer_hedging — **concern** — Round two is unanimous with empty findings, and the two round-one changes_requested findings were closed cleanly. The hedge is the security-reviewer's round-one approval, which carried two recommendations and was correctly not re-dispatched against the fix delta, so they were parked rather than resolved: processVisitCorrectionForm takes the Owner as a model attribute and then saves it, so request parameters bind onto the owner's firstName, lastName, address, city, and telephone on a correction POST, unvalidated. The reviewer judged it baseline-equivalent to the existing booking handler, which it is, but this change adds a second route carrying the property and the suggested fix (re-read the owner from the repository before saving) was not taken. The second recommendation records that no supply-chain check ran at all.
  - scope_deviation — **clear** — The diff lands exactly on the triaged surface: two routes, no entry-point link, date and description only, cancellation untouched. The single design revision was bookkeeping rather than a fought decision - the later design-block supersedes the earlier one only to name the untracked ADR path in its path arrays, explicitly a coverage correction and not a changed verdict, with no review round voided. Zero consultations, zero build retries. The NG-5 narrowing is recorded through the project's own non-goal-ADR convention, quoting the owner's decision verbatim, and both unresolved questions were parked in the PRD's Open Questions rather than answered by the implementation.
  - why — Logic is sound: resolution by owner-pet-visit traversal closes IDOR and the binder still blocks id tampering. Open the reused template - the correction page's button reads 'Add Visit' and lists its own target under 'Previous Visits' with the rejected values after a refusal. Security's parked owner mass-assignment note also wants a call.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- VIEWS_VISITS_CREATE_OR_UPDATE_FORM constant removes the three duplicated string literals cleanly
- rejectDateNotLaterThanToday extraction removes duplication between booking and correction without changing behavior
- findVisit uses a clear stream/filter/orElseThrow idiom consistent with the project's existing not-found pattern (IllegalArgumentException via orElseThrow, matching OwnerController/PetController)
- Correction reuses the same Owner-graph traversal and cascade-save pattern as booking, so no new persistence path or lifecycle state was introduced, matching the ADR's stated invariant
- New private helper methods (findVisit, rejectDateNotLaterThanToday) are appropriately scoped and under 30 lines
- checkFormat and checkstyleMain both pass clean on the current tree

**doc-reviewer**

- REQ-VISITEDIT-001 anchor added and referenced consistently across prd.md, system-design.md, and the new ADR
- NG-5 narrowing recorded with a dedicated non-goal ADR, ADR README table updated, PRD Non-Goals preamble and row updated to match
- PRD Visits section stays behavioral: no rationale prose, no code identifiers, no mechanism tables; rationale correctly deferred to the ADR link
- system-design.md additions stay at invariant level (graph traversal, in-place update, visit count unchanged) with no field/parameter tables or literal constants
- ubiquitous-language.md gains a Visit correction entry with Relationships and Avoid guidance, consistent with the existing entry format
- Security considerations table updated to cover the new identifier-tampering surface (visit correction via the owner-pet-visit graph), consistent with the existing mass-assignment row
- Cross-document coherence verified: every REQ-VISITEDIT-001 reference in system-design.md's Contracts table has a matching PRD requirement, and vice versa
- No prohibited words, relative references, or second-person address found in the new prose

**test-reviewer**

- Four-phase structure, BDD test names (the{Subject}Should{Outcome}), and factory methods (createOwnerWithABookedVisit, createVisit) all follow testing-principles.md
- Tier-1/Tier-2 data naming is clean: BOOKED_VISIT_ID/DATE/DESCRIPTION and CORRECTED_VISIT_DATE/DESCRIPTION are meaningful and role-named, no mystery literals
- Expected values in theCorrectedVisitShouldCarryTheNewDateAndDescription are asserted against the named CORRECTED_* constants rather than duplicated literals
- AssertJ used throughout for new assertions (assertThat, assertThatExceptionOfType), consistent with the brief's fluent-assertion preference
- Refusal path (blank description, non-future date) and the no-extra-visit / no-save-on-error invariants are each given a dedicated, independent test
- MockitoBean use on OwnerRepository is the pre-existing host-file idiom, not new mocking of internal domain objects; Visit and Owner remain real objects throughout
- ./gradlew test passes for the full suite including the new VisitControllerTests cases

**security-reviewer**

- IDOR / identifier tampering closed by construction: loadPetWithVisit resolves the target strictly by graph traversal (owner.findById -> owner.getPet(petId) -> pet.getVisits() filtered by id) in VisitController.java:72-102, so a visitId naming a visit outside the addressed pet is refused rather than loaded. This matches the pattern PetController already uses (owner.getPet(petId)); a regression test covers it (theVisitCorrectionShouldBeRefusedWhenTheVisitDoesNotBelongToThePet).
- Mass assignment (security-principles row 3): the class-level @InitBinder disallowing 'id' and '*.id' covers the two new handlers, and the correction target comes from the path rather than a bound identifier, so no identifier is attacker-selectable past the traversal check. system-design.md threat-model row updated to state this.
- Trusting cross-request state (security-principles row 10): every correction request re-resolves owner, pet, and visit from the repository and re-applies the full booking validation (rejectDateNotLaterThanToday plus @Valid), so no earlier request's validation is trusted.
- Fail-secure on refusal: the validation-failure branch returns the form without calling owners.save; with spring.jpa.open-in-view=false the bound entity is detached, so an unvalidated in-place mutation cannot be flushed. Asserted by then(owners).should(never()).save(...).
- Injection surface unchanged: no query text, shell, file, XML, or deserialization path is touched. Grep over src/main/java for Runtime/ProcessBuilder/exec, enableDefaultTyping/@JsonTypeInfo, /tmp/, System.out err.print, and java.util.Random returned no production hits.
- XSS: no template changed. createOrUpdateVisitForm.html renders every value through th:text/th:object with Thymeleaf's default escaping on, and the actionless form posts back to the current URL, so the edit page needs no new markup.
- Secret disclosure: no credential, token, connection string, or log statement is introduced. The new IllegalArgumentException message carries only visitId and petId, both int-typed path variables, so the error page reflects no attacker-controlled text.
- Widening the exposed surface: the two new routes are documented in system-design.md (VisitController row, threat-model mass-assignment row) and the PRD, and they sit at the recorded no-auth/no-CSRF demonstration baseline rather than below it.
- Supply chain: build.gradle and gradle/ are unchanged in the change set, so the diff adds no dependency and no new artifact source.

**code-quality-reviewer**

- loadPetWithVisit Javadoc now carries @param for ownerId, petId, visitId, and model, and @return is corrected to Visit — fully resolves the prior legible-cold finding with no remaining stale tags on this method
- New assertCorrectionIsRefused(petId, visitId) helper covers both edge-case halves (visit not belonging to pet, pet not belonging to owner) via theVisitCorrectionShouldBeRefusedWhenTheVisitDoesNotBelongToThePet and theVisitCorrectionShouldBeRefusedWhenThePetDoesNotBelongToTheOwner, removing the prior duplication while keeping one assertion body — resolves the prior spec-grounded finding
- PET_ID_OF_ANOTHER_OWNER constant is documented and named consistently with the existing VISIT_ID_OF_ANOTHER_PET convention
- ./gradlew checkFormat passes clean on the current tree; no new formatting or checkstyle issues introduced by the fix delta

**doc-reviewer**

- Fix-delta touches only VisitController.java and VisitControllerTests.java; docs/prd.md, docs/system-design.md, docs/ubiquitous-language.md, and the ADR remain unchanged and still coherent with the code: PRD edge case 3 already names both refusal scenarios (visit-not-of-pet and pet-not-of-owner) that the new test method exercises, and system-design's owner-pet-visit traversal description matches the expanded loadPetWithVisit Javadoc.

**test-reviewer**

- Prior finding (PRD edge case 3, second half - petId not belonging to owner) is now fully covered: theVisitCorrectionShouldBeRefusedWhenThePetDoesNotBelongToTheOwner exercises PET_ID_OF_ANOTHER_OWNER against loadPetWithVisit's owner.getPet(petId) null-check
- Shared refusal assertion extracted into assertCorrectionIsRefused(petId, visitId), removing duplication between the two refusal tests rather than copy-pasting
- New constant PET_ID_OF_ANOTHER_OWNER carries the same role-naming and explanatory javadoc style as the existing VISIT_ID_OF_ANOTHER_PET constant
- ./gradlew test passes for the full suite including both refusal tests
- Javadoc update on loadPetWithVisit documents all four parameters, consistent with the code-quality-reviewer's fix-delta scope

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $3.64 | 12m 35s | 95% |
| `agent-team:system-design-expert` | 2 | opus-5 | $2.24 | 5m 14s | 92% |
| `(parent)` | 1 | opus-5 | $1.82 | 31m 59s | 97% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.70 | 3m 54s | 95% |
| `agent-team:change-grader` | 1 | opus-5 | $1.06 | 3m 32s | 90% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.91 | 2m 36s | 91% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.57 | 2m 46s | 91% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.52 | 2m 29s | 92% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.50 | 1m 45s | 88% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $2.21 | 7m 57s | 95% |
| `(parent)` | opus-5 | $1.82 | 31m 59s | 97% |
| `agent-team:product-requirements-expert` | opus-5 | $1.70 | 3m 54s | 95% |
| `agent-team:system-design-expert` | opus-5 | $1.56 | 3m 57s | 94% |
| `agent-team:change-grader` | opus-5 | $1.06 | 3m 32s | 90% |
| `agent-team:feature-implementer` | opus-5 | $0.92 | 3m 6s | 95% |
| `agent-team:security-reviewer` | opus-5 | $0.91 | 2m 36s | 91% |
| `agent-team:system-design-expert` | opus-5 | $0.67 | 1m 17s | 84% |
| `agent-team:feature-implementer` | opus-5 | $0.51 | 1m 31s | 93% |
| `agent-team:test-reviewer` | sonnet-5 | $0.41 | 2m 2s | 92% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.38 | 1m 55s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.28 | 1m 9s | 89% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.22 | 35s | 88% |
| `agent-team:test-reviewer` | sonnet-5 | $0.15 | 43s | 88% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.14 | 34s | 90% |

</details>

## Artifacts

- [`change.patch`](change.patch) — the agent's diff against the baseline commit
- [`handoff.jsonl`](handoff.jsonl) — the pipeline's handoff ledger, one record per line
- [`agent-costs.json`](agent-costs.json) — per-agent and per-stage token and dollar figures
- [`run.log`](run.log) — prep, gradle, and diagnostic tails
- [`egress.log`](egress.log) — the confinement proxy's per-request access records
- [`manifest.json`](manifest.json) — pre-run coordinates: prompt, fingerprint, prep steps
- [`result.json`](result.json) — the raw measurement record this page derives from

## Provenance

- plugin `agent-team-spring-boot` at `v0.3.8` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `e78e3e32a55220e2` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
