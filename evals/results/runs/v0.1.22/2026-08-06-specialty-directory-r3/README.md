# specialty-directory r3 — v0.1.22

Specialty directory page (feature) · started 2026-08-06T08:43:45+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Feature request: the vet list answers "which specialties does this vet hold",
> but staff also ask the inverse — "which vets hold this specialty". One
> product decision comes with it, made here as the product owner: a read-only
> specialty view of the existing directory is in scope; managing veterinarians
> or specialties stays out of scope as before (non-goal NG-2 is unchanged).
> 
> Add a specialty directory page:
> 
> - GET /specialties.html lists every specialty the clinic knows by its stored
>   name, each with the veterinarians holding it.
> - Each veterinarian is shown by full name: first name, then last name (for
>   example "Helen Leary").
> - A veterinarian holding no specialty appears under no specialty; the page
>   lists specialties, not the full vet roster.
> - All specialties render on one page — no pagination.
> 
> Cover the new behavior with tests.

## Verdict

| check | result |
|---|---|
| oracle | ✔ 4/4 passed |
| suite (post-agent) | ✔ |
| suite (pristine baseline) | ✔ |
| checkpoints | 7/7 |
| review attention (pipeline grade) | clear |

The pipeline grade estimates how much human review the change deserves before merge — advisory context from the harness's change grader (read from the ledger's `grader-verdict` record), never part of the bar.

- ✔ `theSpecialtyDirectoryShouldListEverySeededSpecialty` — passed
- ✔ `theSpecialtyDirectoryShouldNameTheVetsHoldingEachSpecialty` — passed
- ✔ `theSpecialtyDirectoryShouldRender` — passed
- ✔ `theVetDirectoryShouldRenderTheSeededVets` — passed

## Checkpoints

The kind's graded ladder, derived from the recorded facts — context only, outside the quality bar (bench README § Checkpoints).

- ✔ `agent complete`
- ✔ `change produced`
- ✔ `suite green`
- ✔ `theSpecialtyDirectoryShouldListEverySeededSpecialty`
- ✔ `theSpecialtyDirectoryShouldNameTheVetsHoldingEachSpecialty`
- ✔ `theSpecialtyDirectoryShouldRender`
- ✔ `theVetDirectoryShouldRenderTheSeededVets`

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 3 (±0) | 4 (±0) | 3 (±1) | 4 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.59. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 3 · test-quality 4 · maintainability 3 · doc-fit 4

> The join and ordering rules live in VetController.findSpecialtyListings/veterinariansHolding, exactly the 'logic in the controller that belongs lower' anchor; the catalog's available Domain service (or a SpecialtyController for a distinct surface) fits better, and the brief says the existing controller deviation does not cover new rules. SpecialtyRepository and the SpecialtyListing record are otherwise idiomatic. Tests are BDD-named (theSpecialtyViewShould...), phase-separated, and built behind specialty()/vet() factories, but add a new @MockitoBean stub, extract fields instead of comparing whole objects, cast into getModelAndView().getModel() with @SuppressWarnings, and proxy 'one page' via attributeDoesNotExist("totalPages"). specialtyList.html uses #{specialties} for both heading and column and adds no message keys; vet names concatenate with a trailing space. Docs update prd.md and the contracts table but omit SpecialtyListing.

**Sample 2** — design-fit 3 · test-quality 4 · maintainability 3 · doc-fit 4

> VetController gains findSpecialtyListings/veterinariansHolding — a join by specialty id plus two orderings — which is exactly the rule-in-controller the catalog's Web controller row forbids for new rules; a domain service (Available, no ADR needed) would have made it unit-testable, so every new test boots MockMvc and widens the pyramid gap. A second surface on VetController rather than a SpecialtyController is also a stretch. Tests are well named (theSpecialtyViewShould…), use factories, and cover empty-specialty, tie-break, and no-pagination cases, but rely on unchecked model casts and a long SOME_ID javadoc that restates testing-principles prose. specialtyList.html references #{specialties}/#{vets} with no messages file in the patch, and no test would catch ??specialties_en??. Docs updated well, though SpecialtyListing is absent from the contracts table.

**Sample 3** — design-fit 3 · test-quality 4 · maintainability 4 · doc-fit 4

> The new route reuses the existing vet package, repository, and template conventions, but  findSpecialtyListings() / veterinariansHolding()  in VetController put the specialty-join and ordering rules in the controller — the checklist calls a new rule there a fresh violation, and the sanctioned Domain service was available without an ADR; the logic is framework-free yet every test boots MockMvc, widening the pyramid gap. Tests are behavior-named ( theSpecialtyViewShouldOmitVeterinariansHoldingNoSpecialty ), phase-separated, and construct through  specialty() / vet()  factories, but use index access ( listings.get(0) ) with unchecked casts of the model, and the SOME_ID javadoc narrates rather than informs. PRD REQ-VET-003 and the contracts table are updated; SpecialtyListing is absent from that table, which lists the comparable  Vets  wrapper.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $13.64 | 39m | 42 | 88% | 8 file(s) +287/−10 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.46 | 4m 11s | 90% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Specialty view of the veterinarian directory

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✖** (2) | **✔** |
| **test** | ✎ (3) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (2) | **✔** |

- ◇ **prd-entry** Specialty view of the veterinarian directory · (prd-expert) · ***◷ 1s***
- ◈ **design-block** **minor** · (design) · ***◷ 10m***
- ◈ **design-block** **minor** · (design) · supersedes L4 · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 30m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 10m***
- ✖ **review code-quality** · **blocked** · (2 findings) · ***◷ 5m***
  - [autofix] `VetController.java:96` veterinariansHolding joins specialties by name equality (held.getName().equals(specialty.getName())) rather than by ID. Names are unique today, but the correct structural join for two Specialty objects loaded from the same schema is by primary key. A future reader will not know whether name-uniqueness is a DB constraint or an assumption. Use held.getId().equals(specialty.getId()) — the IDs are populated by Spring Data from the same rows the name comes from.
    - fix: Replace held.getName().equals(specialty.getName()) with held.getId().equals(specialty.getId()) in the filter lambda of veterinariansHolding.
  - [truncation] `VetControllerTests.java` Reviewer reached planned checkpoint (3 of 5 implementation files reviewed). specialtyList.html and VetControllerTests.java not yet reviewed. Findings above cover SpecialtyRepository.java, SpecialtyListing.java, and VetController.java only.
- ✎ **review test** · **changes_requested** · (3 findings) · ***◷ 5m***
  - [autofix] `VetControllerTests.java` Bare integer literals passed as entity IDs to specialty() and vet() factory calls in all five new test bodies (values 1, 2, 3, 4). These IDs have no bearing on any assertion and are Tier 3 mystery values per the Three-Tier Data Naming Convention in docs/testing-principles.md. Irrelevant required-by-API values belong in Tier 2: declare a single SOME_ID constant (e.g. private static final int SOME_ID = 0) and use it in every factory call, or add auto-incrementing ID generation inside the factory methods themselves so callers never supply an ID.
    - fix: Declare `private static final int SOME_ID = 0;` at class level and replace every bare integer ID argument in specialty() and vet() calls with SOME_ID, or remove the id parameter from the factory methods and generate it internally.
  - **[blocked]** `VetControllerTests.java` The production code sorts veterinarians under each specialty by Comparator.comparing(Person::getLastName).thenComparing(Person::getFirstName). No test exercises the thenComparing(Person::getFirstName) leg: every test uses vets with distinct last names, so the second comparator key is never verified. PRD edge case 2 requires stable ordering of vets under each specialty. A vet pair sharing a last name but differing on first name (e.g. vet with firstName=Jane lastName=Adams before vet with firstName=Robert lastName=Adams) is needed to verify the full ordering rule.
  - [autofix] `VetControllerTests.java:101-107` The @BeforeEach setup() stubs vets.findAll() (no-arg) with james() and helen(), but every new specialty test immediately overrides that stub with its own given(this.vets.findAll()).willReturn(...). The @BeforeEach stub is silently dead code for all five new tests and misleads the next reader into believing it governs them. Move the no-arg vets.findAll() stub into the two pre-existing tests that actually use it (showVetListHtml, showResourcesVetList), leaving @BeforeEach to stub only the paged findAll(any(Pageable.class)) variant that is truly shared.
    - fix: Remove the given(this.vets.findAll()).willReturn(Lists.newArrayList(james(), helen())); line from @BeforeEach and add it directly inside showVetListHtml and showResourcesVetList.
- ✎ **review doc** · **changes_requested** · (2 findings) · ***◷ 5m***
  - **[blocked]** `prd.md:123` The opening sentence of the REQ-VET-003 paragraph is 42 words, exceeding the 30-word limit. The sentence runs from 'The clinic also publishes...' through '...first name then last name [REQ-VET-003].' The writing standards require sentences under 30 words. Split at the colon: one sentence announces the specialty view; a second sentence describes what it shows. PRD is never autofix-eligible.
  - [clarify] `system-design.md:103` The VetRepository Purpose cell references the method name '`findAll`' in 'The unpaged `findAll` supplies the vet directory and the veterinarians grouped under each specialty in the specialty view.' This fails the abstraction-level self-test: a method rename would silently invalidate the row. Every other repository row (OwnerRepository, PetTypeRepository) describes behavioral contract without naming methods. Replace the second sentence with behavioral language, for example: 'Supplies both the vet directory and the veterinarians grouped under each specialty in the specialty view.' Abstraction-level findings on design-doc paths are not autofix-eligible; this routes to system-design-expert.
- ↻ **implement** (implementer) ← code-quality, test · (5 findings)
- ↻ **fix prd-expert** ← doc · (2 findings)
- ↻ **fix design** ← doc · (2 findings)
- ◈ **design-block** **minor** · (design) · ***◷ 1m***
- ◇ **prd-entry** Specialty view of the veterinarian directory · (prd-expert) · ***◷ 10m***
- ▲ **build-pass** 10:30 · build, test, format, check, handoff-log, autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 5m***
- ✔ **review doc** · **approved** · ***◷ 5m***
- ✔ **review code-quality** · **approved** · ***◷ 15m***
- ✔ **review test** · **approved** · ***◷ 5m***
- ◆ **grade CLEAR** · add read-only specialty view of the vet directory
  - blast_radius — **clear** — 8 files contained to the vet feature package (new SpecialtyRepository, SpecialtyListing record, one route on VetController, one template) plus docs; no sensitive paths, no dependency or schema change. The lone out-of-package edit is a one-word config fix.
  - semantic_surprise — **clear** — Read the hunks: the specialty axis is the stored specialty set so unheld specialties render with an empty vet list, the vet join is by primary key via getId equals, specialties order by name and vets by last-then-first name, all matching the acceptance criteria. Template uses auto-escaping th:text only. No inverted operator, boundary flip, or hidden behavior.
  - test_adequacy — **clear** — Tests assert real outcomes at the changed boundaries: ordering via containsExactly, the thenComparing-firstName leg via a shared-last-name pair, the empty-list case for a specialty held by no vet, and omission of vets holding no specialty. Not tautological despite TDD authorship.
  - reviewer_hedging — **clear** — Full four-reviewer battery dispatched at high risk; the latest status from every reviewer is a clean approved with empty findings. First-pass findings (ID join, test-data naming, PRD sentence length, doc abstraction level) were all resolved and re-approved with no lingering caveats.
  - scope_deviation — **clear** — design_revisions=1 was a pre-implementation design correction at root's checkpoint rejecting the findAll-inversion data source, not mid-flight thrash; implementation ran with 0 build_retries and 0 consultations and stayed within the declared paths. The layout.toml gradle-to-maven edit is an acknowledged root-applied engine-config fix, outside the slice but not authored by the pipeline.
  - why — All five facets clear on a direct read of the hunks. The join is by ID, ordering and the empty-specialty edge case match the criteria, tests exercise real behavior, and the roster approves cleanly. Confirm and merge; the one out-of-slice change is the acknowledged layout.toml config fix.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- New GET /specialties.html is read-only with no path variables or query parameters — no new untrusted-input surface; consistent with the app's documented no-auth posture and introduces no new auth boundary
- specialtyList.html renders only via auto-escaping th:text (specialty.name and vet full name); no th:utext or unescaped output, so no stored/reflected XSS sink
- Data access via Spring Data derived findAll() on VetRepository and SpecialtyRepository — no string-concatenated SQL, no injection surface
- SpecialtyRepository extends the empty Repository marker interface exposing only findAll() with @Transactional(readOnly=true) — genuinely read-only, honoring non-goal NG-2
- No build.gradle/dependency changes in the change set; supply-chain surface unchanged
- layout.toml gradle->maven fix and docs edits carry no security-relevant surface

**code-quality-reviewer**

- SpecialtyRepository follows the read-only repository pattern established by VetRepository — interface extends Repository\<Specialty,Integer>, single findAll, @Transactional(readOnly=true)
- SpecialtyListing Javadoc is precise: documents the empty-list contract for a specialty held by no veterinarian
- VetController constructor injection is correct — no @Autowired, single-constructor implicit wiring
- findSpecialtyListings stream pipeline is clean: specialty axis drives the projection so empty specialties appear, then veterinarians are filtered and sorted
- Specialty ordering (NamedEntity::getName) and vet ordering (last name then first name) match the PRD acceptance criteria for stable order
- No magic literals; page size 5 pre-existing; no new magic numbers introduced

**test-reviewer**

- All five new test methods follow the BDD naming school (the{Subject}Should{Outcome}) per docs/testing-principles.md
- All four PRD acceptance criteria and PRD edge case 2 (stable ordering) have dedicated test coverage
- The design-block risk scenario (specialty held by no veterinarian renders with empty vet list) has its own dedicated test (theSpecialtyViewShouldRenderASpecialtyHeldByNoVeterinarian)
- Factory methods specialty() and vet() correctly wrap domain object construction per the factory-method rule in testing-principles.md
- MockMvc is the sanctioned mock; @MockitoBean for repositories is the only viable option under @WebMvcTest and follows the tolerated existing pattern
- AssertJ fluent assertions used throughout (containsExactly, extracting, isEmpty); no JUnit-style assertEquals or assertTrue
- theSpecialtyViewShouldListEverySpecialtyWithItsVeterinarians verifies both specialty axis ordering (alphabetical) and vet ordering within a specialty (by last name) in one coherent test
- 100% line coverage on all changed production files in the vet package (VetController, SpecialtyListing, Specialty, Vet)

**doc-reviewer**

- PRD boundary is clean: no routes, Spring annotations, method names, or implementation mechanisms appear in the REQ-VET-003 requirement text
- REQ-VET-003 reads as a natural family with REQ-VET-001 via the 'other way round' framing, sharing the same capability section, edge-case list, and Design link
- NG-2 (no write path for veterinarians or specialties) is genuinely unchanged in the PRD text
- All four Done-when bullets for REQ-VET-003 follow the given/when/then pattern and are bounded and testable; word counts are at or under 30
- The REQ-VET-003 anchor is correctly placed on line 119 alongside REQ-VET-001, consistent with the multi-anchor-per-line pattern the PRD uses throughout
- The Design cross-reference system-design.md#contracts resolves to an existing anchor
- The SpecialtyRepository new Contracts row is clean and behaviorally described without method-level detail, mirroring PetTypeRepository
- The VetController Contracts row expansion is behavioral and lists capabilities without naming routes or internal methods
- The Vet and Specialty Contracts rows are correctly updated to include REQ-VET-003
- Domain terms Veterinarian and Specialty are used consistently with their ubiquitous-language.md canonical definitions and spelling
- Edge-case renumbering is correct: old edge case 2 (Known defect) correctly becomes 3; the new specialty-view ordering requirement is correctly inserted as edge case 2

**security-reviewer**

- Fix-delta re-review since prior approval (handoff line 14): VetController specialty join moved from name equality to primary-key equality (held.getId().equals(specialty.getId())) — a purely structural join over data loaded from the same schema; no new untrusted-input surface, no injection sink, verdict unchanged
- GET /specialties.html remains read-only with no @PathVariable or query parameters — no new attack surface; consistent with the app's documented no-auth posture
- specialtyList.html output escaping unaffected: specialty.name and the vet full name render only through auto-escaping th:text; no th:utext or unescaped concatenation into markup, so no stored/reflected XSS sink
- SpecialtyRepository extends the empty Repository marker exposing only findAll() with @Transactional(readOnly=true) — genuinely read-only, honoring non-goal NG-2 (no vet/specialty write path)
- Data access via Spring Data derived findAll() on VetRepository and SpecialtyRepository — no string-concatenated SQL
- VetControllerTests delta is test-data naming (SOME_ID, factory methods) and stub placement only — no security-relevant production surface
- docs (prd, system-design) and layout.toml gradle->maven module-origin edit carry no security-relevant surface; no build.gradle/dependency change, supply-chain surface unchanged

**doc-reviewer**

- Fix 1 lands: docs/prd.md:123 — the 42-word sentence is split into four sentences of 15, 29, 21, and 12 words, all under the 30-word limit; [REQ-VET-003] tags are retained on the first, second, and fourth sentences
- Fix 2 lands: docs/system-design.md:103 — the VetRepository Purpose cell now reads 'Supplies both the vet directory and the veterinarians grouped under each specialty in the specialty view' with no method-name reference; abstraction level matches every other repository row
- REQ-VET-003 paragraph reads as one family with REQ-VET-001 under the shared Veterinarian directory heading via the 'other way round' framing; no PRD boundary violation in any new sentence
- PRD is behavioral and boundary-clean: no Java constructs, Spring annotations, method names, or mechanism language appear in the new REQ-VET-003 text
- NG-2 is unchanged; the non-goals section is untouched in the diff
- SpecialtyRepository row at system-design.md:104 is behavioral and requires no fix; confirmed consistent with PetTypeRepository style
- All Done-when bullets for REQ-VET-003 carry [REQ-VET-003] tags and follow given/when/then form with bounded outcomes

**code-quality-reviewer**

- ID join fix correctly applied: held.getId().equals(specialty.getId()) at VetController.java:96 is a primary-key join; previous name-equality finding resolved
- SOME_ID = 0 for vet ids and meaningful ids (1/2/3) for specialty ids is the correct three-tier data-naming call — specialty ids are the join key the controller matches on, so they are Tier-1 meaningful; vet ids are irrelevant to ordering assertions, so they collapse to SOME_ID; the Javadoc on the constant explains the distinction clearly
- Factory methods specialty(int, String) and vet(String, String, Specialty...) encapsulate object construction; expected values derived from inputs throughout
- BDD-style test names (theSpecialtyView...) follow naming conventions; four-phase structure with blank-line separators correctly applied across all new tests
- AssertJ extracting/containsExactly chains used for ordering assertions; MockMvc content().string(containsString()) used for rendered-output assertions; no JUnit assertEquals
- findSpecialtyListings() and veterinariansHolding() are focused single-responsibility methods with accurate Javadoc; stream pipelines with toList() used throughout
- given() stubs scoped to individual tests rather than @BeforeEach — reduces coupling between unrelated tests; showResourcesVetList correctly retains its own stub
- specialtyList.html: th:replace layout delegation, th:text auto-escaping for specialty.name and vet full name, i18n message keys for column headers — all idiomatic
- checkFormat passed; constructor injection used; no raw types, no mutable record state, no swallowed exceptions

**test-reviewer**

- All three prior findings resolved: thenComparing(firstName) coverage added via theSpecialtyViewShouldOrderVeterinariansSharingALastNameByFirstName (Jane/Robert Adams pair), vet SOME_ID applied for irrelevant vet IDs, findAll() stub moved from @BeforeEach into showResourcesVetList exclusively
- Specialty ID reasoning is correct: controller joins by held.getId().equals(specialty.getId()), so distinct specialty IDs (1, 2, 3) are load-bearing Tier-1 values; collapsing them to SOME_ID=0 would make every vet match every specialty and invalidate all grouping assertions; the class-level Javadoc comment explains the Tier-1/Tier-2 split precisely
- All four REQ-VET-003 Done-When acceptance criteria have dedicated named tests covering the expected behavior
- Risk test theSpecialtyViewShouldRenderASpecialtyHeldByNoVeterinarian is present and correct: dentistry (held by no vet) appears, sorted before radiology alphabetically, with an empty veterinarians list
- Edge-case ordering fully covered: theSpecialtyViewShouldListEverySpecialtyWithItsVeterinarians covers last-name sort; theSpecialtyViewShouldOrderVeterinariansSharingALastNameByFirstName covers thenComparing(firstName)
- MockitoBean on SpecialtyRepository is justified in a @WebMvcTest slice (no real persistence context available); follows same tolerated pattern as pre-existing VetRepository mock
- All new tests follow BDD the{Subject}Should{Outcome} naming school and use AssertJ fluent assertions throughout
- 8/8 tests pass with zero failures or skips

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $8.53 | 16m 3s | 94% |
| `spring-boot-claude:system-design-expert` | 3 | opus-4-8 | $5.72 | 6m 34s | 77% |
| `(parent)` | 1 | opus-5 | $5.50 | 43m 8s | 96% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $4.40 | 6m 51s | 86% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $2.46 | 4m 11s | 90% |
| `spring-boot-claude:security-reviewer` | 2 | opus-4-8 | $2.40 | 1m 27s | 70% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $1.75 | 6m 32s | 74% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $1.71 | 6m 57s | 84% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $1.40 | 5m 25s | 82% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.07 | 0s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $5.50 | 43m 8s | 96% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $5.45 | 10m 11s | 94% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $3.24 | 3m 15s | 73% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $3.08 | 5m 51s | 94% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $2.47 | 4m 9s | 91% |
| `spring-boot-claude:change-grader` | opus-4-8 | $2.46 | 4m 11s | 90% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.93 | 2m 42s | 74% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.47 | 2m 22s | 86% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $1.39 | 36s | 59% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $1.02 | 51s | 79% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.01 | 56s | 65% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $1.00 | 3m 47s | 71% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.92 | 3m 53s | 86% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.80 | 3m 4s | 82% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.79 | 3m 26s | 84% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.76 | 2m 45s | 77% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.61 | 1m 59s | 79% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.07 | 0s | 0% |

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

- plugin `spring-boot-claude` at `v0.1.22` (tag)
- model requested `claude-opus-5`; models used: opus-4-8 · opus-5 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `9c6fd220a549ce32` · `2.1.222 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
