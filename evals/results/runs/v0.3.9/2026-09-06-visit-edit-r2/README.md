# visit-edit r2 — v0.3.9

Edit a booked visit (feature) · started 2026-09-06T21:47:34+00:00 · exec `claude-dev` · status **complete**

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
| reading depth (pipeline grade) | scrutinize |

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
| 4 (±1) | 4 (±0) | 4 (±1) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.61. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> VisitController reuses the existing seam:  loadPetWithVisit  gains an optional  visitId  and resolves the visit through the pet, so an in-place correction saves via the aggregate root ( this.owners.save(owner) ) and the pet gains no second visit;  rejectDateNotInFuture  expresses the existing rule once rather than adding a new controller rule.  Pet.getVisit  mirrors  getPet . Deducted a point because the model-attribute method now branches on two routes and carries a long narrative javadoc. Tests are behavior-named, phase-separated, constants named ( BOOKED_DATE ,  BLANK_DESCRIPTION ), and  PetTests  adds genuine unit coverage;  verify(this.owners).save(owner)  asserts an interaction and the helper constructs  new Visit() / new Pet()  inline. Documentation is complete: new ADR, amended predecessor, ADR index, NG-5 row, REQ-VIS-003 with done-when, edge case and open questions, plus system-design contract rows.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 5 · doc-fit 5

> Placement mirrors the existing codebase: Pet.getVisit resolves within the aggregate so a foreign visitId is simply absent, the VIEWS_VISIT_CREATE_OR_UPDATE_FORM constant matches PetController, and owners.save(owner) keeps the repository the sole write path. The date rule still sits in VisitController, extracted only to the private rejectDateNotInFuture helper and now serving a second route, where the catalog's Form validator row was available — that stretches the recorded controller deviation. Tests are behavior-named (thePetShouldFindABookedVisitByItsId, theVisitCorrectionShouldNotAddASecondVisitToThePet), phase-separated, factory-built, with no mystery literals; they lose a point for hasProperty field-picking instead of whole-object comparison and the interaction assertion verify(this.owners).save(owner). Docs move everywhere visible: new ADR, amendment banner on the 2026-08-08 ADR, ADR index, narrowed NG-5 row, REQ-VIS-003 with acceptance criteria, system-design contract rows, and two recorded open questions.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The edit route reuses the existing  loadPetWithVisit  seam, resolves the visit through the aggregate root ( Pet.getVisit ), and factors the shared date rule into  rejectDateNotInFuture  rather than duplicating or inventing a rule, so no fresh controller logic appears. Tests are behavior-named ( theVisitCorrectionShouldUpdateTheVisitInPlace ), phase-separated, built behind  givenAnOwnerWhosePetHasABookedVisit / createABookedVisit , and free of mystery literals; deductions for mixing  verify(this.owners).save(owner)  interaction checking with state assertions, an extra  getVisits()).hasSize(1)  concern inside the GET-form test, and  TEST_VISIT_ID = 1  colliding with  TEST_PET_ID . The edited  loadPetWithVisit  javadoc still claims  @return Pet  while returning a Visit. Docs are thorough: new ADR, README index, amended prior ADR, narrowed NG-5, REQ-VIS-003 criteria, open questions, and system-design contract rows.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $14.46 | 37m | 51 | 93% | 9 file(s) +336/−17 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.94 | 2m 50s | 88% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VIS-003 — Staff can correct a booked visit's date and description

2 review rounds · 2 build-passes · **1 build-failure** · grade **SCRUTINIZE**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | **✔** | · |
| **security** | **✔** | · |
| **doc** | ✎ (1) | **✔** |

- • intake-decision (human)
- • intake-decision (human)
- ◇ **prd-entry** Staff can correct a booked visit's date and description · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **minor** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 11m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **minor** · (design) · supersedes L6 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 1m***
  - ▹ rec: The controller's not-found path when a visitId does not belong to the resolved pet (loadPetWithVisit's IllegalArgumentException) has no MockMvc-level test; only the underlying Pet.getVisit(id)==null case is unit-covered. This mirrors PetController's identical untested not-found path for petId, so it is pre-existing debt this slice extends rather than a new gap, and the PRD explicitly leaves 'visit belongs to a different pet or owner' as an open question — not a blocking finding, but worth a dedicated controller test if that question is ever resolved.
  - ▹ rec: VisitControllerTests's @BeforeEach still constructs Owner/Pet via bare `new` rather than a factory; testing-principles.md's factory-method rule only binds tests written or modified from 2026-07-31, and this method was not touched by the diff, so no action is required here.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 9s***
  - [autofix] `prd.md:105` The Visits section states 'a corrected visit cannot be cancelled or removed — NG-5 keeps cancellation out of scope,' attributing both 'cancelled' and 'removed' to NG-5. NG-5 covers only cancellation; deletion of a visit is NG-4's row ('Deleting an owner, a pet, or a visit'). A reader tracing the non-goal citation to verify scope is misdirected to the wrong row for half the sentence.
    - fix: Attribute each clause to its own non-goal, e.g.: "A correction is held to the same rules as a booking; a corrected visit cannot be cancelled (NG-5) or deleted (NG-4)."
- ✔ **review security** · **approved** · ***◷ 3m***
  - ▹ rec: Supply chain: not verified against the NVD in this review. No OWASP Dependency-Check plugin is configured in build.gradle, and the reviewer has no network access, so no CVE match ran — treat the dependency check as not run rather than clean. The change itself adds no supply-chain surface (build.gradle unchanged, no new or upgraded artifact), so this is for CI or a human to close, not a defect in this slice.
  - ▹ rec: docs/system-design.md § Security Context now understates the request-derived input inventory: 'Path variables carrying owner and pet identifiers' predates the visitId path variable this slice adds. Worth extending to name the visit identifier the next time that section is revised, so the next reviewer's first read of the security profile matches the routes.
  - ▹ rec: Defense in depth on the authorization control is tested at the unit level (PetTests.thePetShouldNotFindAVisitItDoesNotHold) but not at the HTTP boundary. A VisitControllerTests case posting a visitId the pet does not hold, asserting the correction is refused and no visit is mutated, would pin the refusal at the layer an attacker actually reaches. Not a defect — the control is present and the two halves are each covered.
- ↻ **fix prd-expert** ← doc · (1 finding)
- ↻ **fix prd-expert** ← doc · (1 finding)
- ◇ **prd-entry** Staff can correct a booked visit's date and description · (prd-expert) · ***◷ 27s***
- ◈ **design-block** **minor** · (design) · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 47s***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 17s***
- ◆ **grade SCRUTINIZE** · add in-place correction of a booked visit
  - blast_radius — **skim** — Two production files in one module: a null-returning by-identity accessor on Pet and a second route pair plus a nullable-visitId branch on VisitController. No template, schema, config, dependency or sensitive path changes; the booking route's behavior is byte-identical because a null visitId takes the old path.
  - semantic_surprise — **skim** — Read all 30 hunks and found no behavior the diff's shape would not predict: the constant and rejectDateNotInFuture extractions are literal-for-literal, the corrected visit is the instance the pet already holds so the set cannot grow, the controller-wide InitBinder disallowing id and star-dot-id blocks a forged id retargeting the mutation, and the visit is resolved only inside the pet resolved from the path owner so no cross-owner reach exists. Two visible residuals follow directly from the intake's reuse-the-template-unchanged instruction rather than from a surprise: the correction screen's submit button still reads Add Visit, and the visit being corrected also lists itself under Previous Visits.
  - test_adequacy — **scrutinize** — The happy paths are genuinely exercised, not tautological: real Owner, Pet and Visit objects through real MVC binding, asserting the mutated instance carries the new values, the pet still holds exactly one visit, a forged id parameter is ignored, and both the date and description boundaries reject on the correction route including a past-dated visit. The gap is one new production branch: loadPetWithVisit's throw when the pet does not hold the visitId has no test at any level, since PetTests covers only getVisit returning null underneath it. That branch is the authorization refusal, and both the test and security reviewers named it independently.
  - reviewer_hedging — **scrutinize** — All four roster reviewers approved with empty findings, but two approvals park residual work in recommendations: the security reviewer flags the untested refusal at the HTTP boundary, that system-design's Security Context input inventory still omits the visitId path variable, and that no dependency CVE check ran; the test reviewer flags the same missing controller-level not-found test. The doc-reviewer's round-1 changes_requested was a single spec-grounded PRD misattribution, repaired and cleanly re-approved in round 2.
  - scope_deviation — **skim** — The diff matches the intake request clause by clause: the two routes at the stated URL, the existing template reused, no edit link on the owner detail page, and the NG-5 narrowing recorded as an ADR with the PRD row rewritten. The one design revision and the single build retry were bookkeeping, claiming the docs/adr paths for the autofix audit and re-triaging a superseded prd-entry, with the design itself carried forward unchanged.
  - why — No behavioral surprise survived reading the hunks, and the authorization control is correct and fail-secure. Two reviewers nonetheless park the same residual: the new not-found branch that enforces that control has no test at the HTTP boundary. Read those recommendations, then merge knowing the route ships with no link to it.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- Pet.getVisit(Integer) mirrors Owner.getPet(Integer) exactly in shape, javadoc, and null-return convention (Owner.java:126), so the new accessor introduces no new pattern
- VisitController extracts the shared future-date rule into one private rejectDateNotInFuture method called by both the booking and correction handlers, avoiding a second controller-resident copy of the rule per the design-block's risk note
- VIEWS_VISIT_CREATE_OR_UPDATE_FORM constant follows the same naming as PetController's VIEWS_PETS_CREATE_OR_UPDATE_FORM
- The @ModelAttribute("visit") loader's branch on a nullable visitId path variable mirrors PetController.findPet's established nullable-path-variable pattern (PetController.java:76), and the javadoc addition clearly documents the new branch
- Visit resolution is scoped to the pet already resolved from ownerId, so a mismatched visitId is refused the same way an unknown petId is today, with no new resolution path introduced
- Flash message text and IllegalArgumentException-on-not-found style are consistent with sibling controllers (PetController, OwnerController); no vocabulary drift against docs/ubiquitous-language.md
- Change stays within REQ-VIS-003's acceptance bullets and the narrowed NG-5 boundary; no cancellation or lifecycle-state behavior added
- checkFormat passes clean

**test-reviewer**

- All 6 PRD-declared test names present and each maps to a Done-when bullet or the Visits edge-case-3 row (coverage-map confirms 6 of 6)
- Pet.getVisit(Integer) — the design-assigned below-boundary by-identity lookup — is unit tested directly in the new PetTests.java (thePetShouldFindABookedVisitByItsId, thePetShouldNotFindAVisitItDoesNotHold, thePetShouldNotFindAVisitThatIsNotBookedYet), matching system-design.md's assignment of the rule to Pet rather than testing it only through the web layer
- The date-not-in-future rule stays at the controller boundary where system-design.md places it, tested via MockMvc for both the pre-existing booking route and the new correction route, sharing one assertion path (rejectDateNotInFuture)
- Test names follow the BDD the{Subject}Should{Outcome} school (testing-principles.md sect. Test Naming) for every new test in both files
- No new raw-mock usage beyond the sanctioned MockMvc/MockitoBean(OwnerRepository) pair already established in this file; real Owner/Pet/Visit value objects are constructed and mutated for real, no interaction is mocked/verified except owners.save(owner), which mirrors the existing verify(...).findByLastNameStartingWith precedent in OwnerControllerTests.java and asserts an effect (persistence trigger) the state assertion on the same object reference cannot otherwise distinguish
- Three-tier data naming is clean: BOOKED_DATE/CORRECTED_DATE/ALREADY_PASSED_DATE/BLANK_DESCRIPTION/VISIT_ID_SUPPLIED_BY_AN_ATTACKER are all role-named, no mystery literals introduced
- All domain-object construction in the new tests sits behind factory/given-helper methods (createABookedVisit, createAnUnbookedVisit, createAPetHolding, givenAnOwnerWhosePetHasABookedVisit) rather than bare constructor calls scattered through test bodies
- theVisitCorrectionShouldIgnoreAnIdentifierSuppliedByTheForm adds mass-assignment coverage beyond the PRD's declared list, matching the design-block's identifier-binding risk and the controller-wide @InitBinder
- ./gradlew test green for both changed test files; PetTests and VisitControllerTests pass

**doc-reviewer**

- REQ-VIS-003 anchors, Done-when bullets, and edge cases are added consistently with the existing Visits section structure and stay behavioral (no class/method names, no template names)
- The NG-5 non-goal row and both ADRs (2026-08-08 amendment note, 2026-09-06 narrowing ADR) correctly cross-reference each other and the PRD, and the ADR index row is inserted in chronological order
- system-design.md's Owner/Pet/Visit/OwnerRepository/VisitController Implements columns and purpose prose were updated consistently for REQ-VIS-003, matching the actual VisitController and Pet.getVisit(Integer) behavior without transcribing signatures or fields
- The two new Open Questions (visible entry point deferred; cross-owner/pet visit-id mismatch) are correctly scoped as open questions rather than silently resolved
- No PRD boundary violations: no code identifiers, template names, or mechanism tables introduced

**security-reviewer**

- Object-level authorization on the new correction routes is correct and is the security-load-bearing part of the change: VisitController.loadPetWithVisit resolves the visit only inside the pet already resolved from the path owner (VisitController.java:79-98), via the new Pet.getVisit(Integer) (Pet.java:86-96). A visitId belonging to another pet or owner is not found and the request is refused, so there is no IDOR path from /owners/{ownerId}/pets/{petId}/visits/{visitId}/edit to another owner's data. Note for downstream: PRD Open Questions now records 'Whether a correction must match is undecided' — the implemented refusal is the fail-secure answer, and loosening it later would introduce the IDOR this review found absent. Basis: direct reads of VisitController.java, Pet.java and the changeset diff; the IDE oracle is not connected in this run, so this is the weaker (non-symbol-resolved) basis.
- Mass assignment (security-principles.md § Realization, Mass assignment row) is covered on both new routes: the controller-wide unnamed @InitBinder disallowing 'id' and '*.id' (VisitController.java:53-56) applies to every model attribute on the added handlers, matching the codebase-wide binder pattern in OwnerController and PetController. VisitControllerTests.theVisitCorrectionShouldIgnoreAnIdentifierSuppliedByTheForm asserts a form-supplied id does not retarget the correction. The corrected visit is the pre-resolved instance from the path, so no form/URL identifier mismatch is reachable.
- Validate-at-the-boundary holds on the correction route: the non-future-date rule is enforced server-side by the shared rejectDateNotInFuture (VisitController.java:159-163) called from both handlers, and bean validation still runs via @Valid. The date input's client-side min attribute is a hint only, and thePastDatedVisitCorrectionShouldStillRequireAFutureDate pins the server-side rule for an already-passed visit.
- No persistence on the rejected path: spring.jpa.open-in-view=false and the per-request owners.findById mean a correction that binds onto the pet's live Visit instance and then fails validation is never flushed — the handler returns the form without calling owners.save.
- Error-message safety (security-principles.md § Realization, secret-disclosure row): the new IllegalArgumentException message (VisitController.java:95-97) interpolates only the caller's own numeric path identifiers, mirroring the existing owner-not-found and pet-not-found messages. Both values are typed int/Integer path variables, so non-numeric input never reaches the string. error.html renders ${message} with th:text, and no template in src/main/resources/templates uses th:utext, so escaping stays on — no XSS from the new message and none from the reused createOrUpdateVisitForm, which is unchanged.
- Attack surface otherwise unchanged: the diff adds no dependency (build.gradle untouched), no logging, no shell or process execution, no file or path handling, no serialization or Jackson configuration, no reflection, no new randomness, and no credential-shaped literal. The two added routes are server-rendered MVC handlers under the existing open-by-design baseline in system-design.md § Security Context; actuator exposure is untouched.

**doc-reviewer**

- docs/prd.md:105 now attributes each declined clause to its own non-goal row: cancellation to NG-5, deletion to NG-4, matching the NG-4/NG-5 table rows (docs/prd.md:42-43) and closing the round-1 finding at handoff line 20.
- The fix-delta is confined to the one repaired sentence; no other prose, requirement, or cross-reference in docs/prd.md changed, and no new instance of the NG-5/NG-4 misattribution pattern exists elsewhere in the document (swept via grep).

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $4.10 | 15m 7s | 95% |
| `agent-team:system-design-expert` | 3 | opus-5 | $2.73 | 7m 23s | 89% |
| `(parent)` | 1 | opus-5 | $2.53 | 39m 36s | 97% |
| `agent-team:product-requirements-expert` | 3 | opus-5 | $2.33 | 5m 45s | 92% |
| `agent-team:security-reviewer` | 1 | opus-5 | $1.18 | 3m 7s | 93% |
| `agent-team:change-grader` | 1 | opus-5 | $0.94 | 2m 50s | 88% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.57 | 2m 27s | 90% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.46 | 1m 59s | 90% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.40 | 1m 46s | 90% |
| `agent-team:pipeline-coordinator` | 2 | sonnet-5 | $0.16 | 13s | 42% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.25 | 12m 40s | 97% |
| `(parent)` | opus-5 | $2.53 | 39m 36s | 97% |
| `agent-team:system-design-expert` | opus-5 | $1.31 | 3m 35s | 92% |
| `agent-team:security-reviewer` | opus-5 | $1.18 | 3m 7s | 93% |
| `agent-team:product-requirements-expert` | opus-5 | $1.08 | 3m 7s | 93% |
| `agent-team:change-grader` | opus-5 | $0.94 | 2m 50s | 88% |
| `agent-team:system-design-expert` | opus-5 | $0.71 | 2m 3s | 87% |
| `agent-team:system-design-expert` | opus-5 | $0.71 | 1m 44s | 86% |
| `agent-team:product-requirements-expert` | opus-5 | $0.69 | 1m 25s | 91% |
| `agent-team:product-requirements-expert` | opus-5 | $0.56 | 1m 12s | 92% |
| `agent-team:test-reviewer` | sonnet-5 | $0.46 | 1m 59s | 90% |
| `agent-team:feature-implementer` | opus-5 | $0.43 | 1m 5s | 87% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.42 | 2m 0s | 91% |
| `agent-team:feature-implementer` | opus-5 | $0.41 | 1m 22s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.40 | 1m 46s | 90% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.15 | 26s | 84% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.09 | 13s | 48% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.07 | 0s | 30% |

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

- plugin `agent-team-spring-boot` at `v0.3.9` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `6cbb44ce4c9a` (branch `agent-team`)
- task fingerprint `159121960b2e019a` · `2.1.263 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
