# specialty-directory r3 — v0.1.28

Specialty directory page (feature) · started 2026-08-24T03:00:22+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Feature request: the vet list answers "which specialties does this vet hold",
> but staff also ask the inverse — "which vets hold this specialty". Two
> product decisions come with it, made here as the product owner:
> 
> - A read-only specialty view of the existing directory is in scope; managing
>   veterinarians or specialties stays out of scope as before (non-goal NG-2
>   is unchanged).
> - The page is reachable by its URL alone: no navigation entry and no link
>   from another page is part of this request. A visible entry point may come
>   as a follow-up request.
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
| 2 (±1) | 3 (±0) | 3 (±0) | 4 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.54. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 2 · test-quality 3 · maintainability 3 · doc-fit 4

> VetController.showSpecialtyList adds ~25 lines of grouping, comparator, and no-specialty logic directly in a controller, which the architecture's Web controller row and the checklist item 'No business rule added to a web controller' forbid; a Domain service is sanctioned and unused. Keying the map by specialty name string is lossy coupling, and the template repeats  ${vet.firstName + ' ' + vet.lastName + ' '}  with a trailing-space hack and always renders the no-specialty row. Tests are well named and now behind vet()/specialty() factories, but stub SpecialtyRepository with the mock framework, assert via content.indexOf ordering, and theSpecialtyDirectoryShouldListASpecialtyHeldByNoVeterinarian only re-asserts contains("surgery"). Docs: prd REQ-VET-003 and open questions added, contracts updated, though VetRepository/Vet rows still claim REQ-VET-001 only.

**Sample 2** — design-fit 2 · test-quality 3 · maintainability 3 · doc-fit 4

> The inversion rule — seeding a LinkedHashMap from findSpecialties(), bucketing vets, sorting by last-then-first name — lives entirely in VetController.showSpecialtyList, a fresh business rule in a web controller that the checklist explicitly bars and that Application/Domain service patterns were available for; it is also unit-untestable without MockMvc. SpecialtyRepository and the naming are otherwise idiomatic. Tests are BDD-named and introduce vet()/specialty() factories, but stub the new collaborator with @MockitoBean, carry bare literals ("radiology", "Helen"), assert pagination absence via model().attributeDoesNotExist (implementation detail), order via content.indexOf, and theSpecialtyDirectoryShouldListASpecialtyHeldByNoVeterinarian only checks containsString("surgery") without verifying an empty holder list. Template concatenates names with a trailing space. PRD/system-design updated well; the principles' enumeration of controller-resident rules now understates reality.

**Sample 3** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 3

> The inversion, grouping, and ordering logic sits entirely in VetController.showSpecialtyList (comparator, LinkedHashMap seeding, sort) — exactly the 'logic in the controller that belongs lower' anchor; a domain service was available and would have made it unit-testable without MockMvc, which the pyramid section demands of new rules. SpecialtyRepository, naming, template, and the ten locale message keys otherwise match existing structure. Tests are behavior-named and use vet()/specialty() factories, but carry Tier-3 mystery literals (specialty(1, "radiology")), index-based ordering assertions (content.indexOf(...)), a near-tautological 'held by no veterinarian' test asserting only containsString("surgery"), and attributeDoesNotExist("currentPage") asserts implementation detail. Model attribute "specialties" actually holds vetsBySpecialty; equal names collapse. PRD and contracts table updated, but system-design's controller-deviation note now understates a fresh violation.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $16.12 | 50m | 59 | 92% | 17 file(s) +302/−18 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.70 | 1m 48s | 86% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Specialty directory lists each specialty with the veterinarians holding it

4 review rounds · 2 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 | R3 | R4 |
| --- | --- | --- | --- | --- |
| **code-quality** | **✔** (1) | **✔** (1) | · | · |
| **test** | ✎ (4) | **✔** | · | · |
| **security** | **✔** | **✔** | · | · |
| **doc** | ✎ (3) | ✎ (3) | ✎ (1) | **✔** |

- ◇ **prd-entry** Specialty directory lists each specialty with the veterinarians holding it · (prd-expert) · ***◷ 34s***
- ◈ **design-block** **minor** · (design) · ***◷ 43s***
- ◆ **implement** (implementer) · ***◷ 7m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **minor** · (design) · supersedes L4 · ***◷ 17s***
- ◆ **implement** (implementer) · ***◷ 38s***
  - ▲ **build ✓ clean** · build · test · format · autofix-audit · handoff-log
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 23s***
- ✎ **review test** · **changes_requested** · (4 findings) · ***◷ 2m***
  - [autofix] `VetControllerTests.java:111,121,128,13` All five new test methods lack the `the{Subject}` prefix required by the project BDD naming school (docs/testing-principles.md § Test Naming, effective 2026-07-31). `shouldListEverySpecialtyWithTheVeterinariansHoldingIt`, `shouldShowVeterinariansByFullName`, `shouldGroupVeterinariansHoldingNoSpecialty`, `shouldRenderAllSpecialtiesOnOnePageWithoutPagination`, `shouldListASpecialtyHeldByNoVeterinarian` all follow the `should{Outcome}` pattern rather than the required `the{Subject}Should{Outcome}` school. A subject is missing from every name; the reader cannot tell what component is under test without reading the body.
    - fix: Rename all five to lead with `the{Subject}`: e.g. `theSpecialtyDirectoryShouldListEverySpecialtyWithTheVeterinariansHoldingIt`, `theSpecialtyDirectoryShouldShowVeterinariansByFullName`, `theSpecialtyDirectoryShouldGroupVeterinariansHoldingNoSpecialty`, `theSpecialtyDirectoryShouldRenderAllOnOnePageWithoutPagination`, `theSpecialtyDirectoryShouldListASpecialtyHeldByNoVeterinarian`.
  - [autofix] `VetControllerTests.java:121-125` `shouldShowVeterinariansByFullName` asserts only `content().string(containsString("Helen Leary"))`. The identical assertion already appears at line 117 inside `shouldListEverySpecialtyWithTheVeterinariansHoldingIt`. Both tests would fail on exactly the same defect — a missing full-name render — so the second test adds no independent behavioral signal and is pure duplication. The intent (first name precedes last name) is not separately verified; both tests only check that the concatenated string appears somewhere in the page.
    - fix: Delete `shouldShowVeterinariansByFullName`. If first-before-last ordering must be independently tested, replace it with an assertion that checks the rendered order — e.g. verify the HTML position of the first-name token relative to the last-name token, or that 'Helen Leary' appears and 'Leary Helen' does not.
  - **[blocked]** `VetControllerTests.java` PRD § Specialty directory edge case 2 is an explicit acceptance criterion: 'Specialties, and the veterinarians within each specialty, are presented in a stable order rather than an arbitrary one, and the no-specialty grouping holds a stable position among them.' No test exercises this. The controller sorts specialties by name (via SpecialtyRepository ORDER BY s.name) and sorts vets within each group by lastName then firstName, but neither ordering guarantee has a test. A regression that removes the sort — returning specialties in JPA iteration order or omitting the byFullName comparator — would pass the entire test suite undetected.
  - [autofix] `VetControllerTests.java:87` Inline comment `// radiology is held by Helen; surgery is held by no veterinarian.` narrates the test data relationship that the factory methods already express. docs/testing-principles.md § Four-Phase Test Structure prohibits inline comments that restate what the code says. The `helen()` factory at line 73-80 explicitly shows Helen holds radiology; surgery's absence from both factories conveys that it is unheld. The comment is redundant noise.
    - fix: Remove the comment at line 87.
- ✎ **review doc** · **changes_requested** · (3 findings) · ***◷ 3m***
  - [autofix] `prd.md:137` Two sentences in the Specialty directory narrative paragraph exceed the 30-word limit. (1) 'It lists every specialty the clinic knows by its stored name, and under each specialty the veterinarians who hold it, each shown by full name with the first name before the last name.' is approximately 35 words. (2) 'The page is reachable by its own address alone; no navigation entry and no link from another page belongs to this requirement — a visible entry point is deferred to a possible follow-up.' is approximately 35 words. Both violate the writing standard of sentences under 30 words.
    - fix: Split each sentence at its natural clause boundary. For (1): 'It lists every specialty the clinic knows by its stored name. Under each specialty it shows the veterinarians who hold it, each by full name with the first name before the last.' For (2): 'The page is reachable by its own address. No navigation entry and no inbound link from another page belongs to this requirement — a visible entry point is deferred to a possible follow-up.'
  - [autofix] `prd.md:140` The first Done-when bullet exceeds 30 words. 'given the clinic's specialties, when the specialty directory is opened, then every specialty is listed by its stored name, and under each the veterinarians who hold it are shown by full name with the first name before the last name.' is approximately 38 words. Existing Done-when bullets throughout the PRD stay under 30 words; this is an outlier.
    - fix: Tighten the then-clause: 'given the clinic's specialties, when the specialty directory is opened, then every specialty is listed by its stored name, and under each the veterinarians who hold it are shown by full name, first name first.'
  - [autofix] `system-design.md:104` The Description cell for SpecialtyRepository ends with 'Mirrors `PetTypeRepository`'. This is a code-symbol cross-reference in the Description column and fails the abstraction self-test: renaming PetTypeRepository would silently invalidate the description. No other Description cell in the Contracts table cross-references a sibling component by name. The Component and Source Path columns already anchor the table entries; the Description column should state the contract behavior, not name a peer.
    - fix: Remove the code-symbol reference and state the pattern in behavioral terms, for example: 'Spring Data JPA repository for specialties, returning them in name order; surfaces every specialty including those held by no veterinarian, which the vet graph alone cannot reach. Follows the same name-ordered lookup pattern as the pet-type repository.'
- ✔ **review code-quality** · **approved** · (1 finding) · ***◷ 4m***
  - [clarify] `specialtyList.html:23-28` The 'No specialty' table row is rendered unconditionally: when noSpecialtyVets is empty (every vet holds at least one specialty), the row still appears with just the label and an empty second cell. PRD edge case 1 explicitly states that a named specialty held by no vet still shows with no vets beneath it, making the analogous always-visible policy for named specialties clear. The PRD is silent on whether the same policy applies to the 'No specialty' grouping when all vets have specialties — the parallel behaviour may be deliberate, but the next reader cannot tell. A th:if guard or a code comment naming the chosen policy would eliminate the ambiguity.
- ↻ **implement** (implementer) ← test · (4 findings)
- ✎ **review doc** · **changes_requested** · (3 findings) · ***◷ 15s***
  - [autofix] `prd.md:137` The sentence 'It lists every specialty the clinic knows by its stored name, and under each specialty the veterinarians who hold it, each shown by full name with the first name before the last name.' runs 33 words, exceeding the 30-word limit. Replace the original substring ' with the first name before the last name' (the sentence-final clause, starting at the space before 'with') with the shorter equivalent to bring the sentence to 28 words.
    - fix: , first before last
  - [autofix] `prd.md:137` The sentence 'The page is reachable by its own address alone; no navigation entry and no link from another page belongs to this requirement — a visible entry point is deferred to a possible follow-up.' runs 32 words, exceeding the 30-word limit. Replace the original substring 'alone; no navigation' to split at the semicolon into two sentences of 9 and 23 words.
    - fix: alone. No navigation
  - [autofix] `system-design.md:104` The Description cell for the SpecialtyRepository row ends with 'Mirrors `PetTypeRepository`', a code-symbol cross-reference to a sibling component. No other Description cell in the Contracts table names a peer by code symbol; renaming PetTypeRepository would silently invalidate this cell. Replace the original substring 'cannot reach. Mirrors `PetTypeRepository`' with 'cannot reach.' to remove the code-symbol reference.
    - fix: cannot reach.
- ▲ **build-pass** 03:39 · build, test, format, autofix-audit, handoff-log
- • review-plan (review-plan-engine)
- ✚ **prd-autofix** `docs/prd.md` · writing-standards · (root)
- ✚ **doc-autofix** `docs/system-design.md` · writing-standards · (root)
- ✔ **review security** · **approved** · ***◷ 23s***
- ✔ **review code-quality** · **approved** · (1 finding) · ***◷ 1m***
  - [clarify] `specialtyList.html:23-28` The 'No specialty' table row renders unconditionally even when noSpecialtyVets is empty — no th:if guards it. This is a product question: when every vet holds at least one specialty, an empty 'No specialty' row still appears in the table. The current behavior is the narrowest reading of the requirement (parallel to an unheld specialty still rendering an empty row under a named specialty). Reaffirmed from prior review as non-blocking.
- ✔ **review test** · **approved** · ***◷ 2m***
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `prd.md:137` Narrative sentence 'It lists every specialty ... the last name.' is ~33 words, exceeding the 30-word limit. Span 'each shown by full name with the first name before the last name' is unique to line 137 — confirmed by grep: line 140 uses 'are shown', not 'each shown'. Replacement reduces the sentence to ~28 words. Span occurs exactly once in docs/prd.md.
    - fix: each shown by full name (first name first)
- ✚ **prd-autofix** `docs/prd.md` · writing-standards · (root)
- ✔ **review doc** · **approved** · ***◷ 23s***
- ◆ **grade CLEAR** · add read-only specialty directory page
  - blast_radius — **clear** — 17 files but all within the vet feature package plus 10 one-line message-bundle additions and docs; no sensitive paths, one module of prod code. The VetController constructor gains a SpecialtyRepository param, a Spring-DI change with no other production caller.
  - semantic_surprise — **clear** — Controller seeds a name-ordered LinkedHashMap from findSpecialties(), buckets vets by nrOfSpecialties==0, and sorts holders by lastName-then-firstName; the display renders firstName+lastName while the sort key is last-then-first, which is intentional and matches the ordering test. computeIfAbsent is a documented defensive fallback. The unconditional No-specialty row is the deliberate narrowest reading.
  - test_adequacy — **clear** — Tests have real teeth: SpecialtyRepositoryTests (DataJpaTest, real I/O) seeds out-of-alphabetical order and asserts isSorted, so dropping ORDER BY fails; controller tests assert indexOf ordering (Douglas before Leary, surgery before No specialty) rather than mere containment. build_passed true and the prior critical stable-order gap is resolved.
  - reviewer_hedging — **clear** — All four rostered reviewers approved on the final pass. The one lingering item is a non-blocking clarify routed to product about the always-visible empty No-specialty row, explicitly reaffirmed as non-blocking; not an escalation, bar_clause, or reservation about the code.
  - scope_deviation — **clear** — design_revisions is 1 but that revision only added docs/system-design.md to path coverage for the autofix audit, not a substantive scope change; consultations and build_retries are both 0. Introducing SpecialtyRepository instead of extending VetRepository was a documented deliberate design decision within scope.
  - why — All five facets clear on a diff read. Contained read-only view in the vet package, ordering logic verified by index-based tests with real teeth, and clean unanimous approval. Human can confirm and merge fast; optionally glance at the always-rendered empty No-specialty row, a known non-blocking product question.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- JPQL query SELECT s FROM Specialty s ORDER BY s.name is static with no parameters or concatenation — no injection surface
- specialtyList.html renders all dynamic content (specialty names, vet full names, message keys) via auto-escaping th:text; no th:utext, no inline JS, no attribute injection — XSS covered
- GET /specialties.html takes no user-controlled request parameters; no path traversal or file I/O
- Data exposure limited to specialty names and vet full names, identical to the existing public /vets.html directory; no new PII or trust boundary
- No new dependencies or build changes — no supply-chain surface; no hardcoded secrets in the diff
- Read-only handler with no writes — no data-integrity concern

**test-reviewer**

- @MockitoBean usage for VetRepository and SpecialtyRepository is consistent with the pre-existing VetControllerTests convention and is within the tolerated pattern for @WebMvcTest slices per docs/testing-principles.md § Mocking Policy
- Factory methods specialty(), james(), and helen() correctly wrap production-type construction behind named factories as required by the brief
- JaCoCo coverage for the vet package is 97-100%, well above the 80% target
- PRD acceptance criteria 1 (every specialty listed with holders), 2 (no-specialty grouping), and 3 (no pagination) each have a dedicated test with meaningful assertions
- Edge case 1 (specialty held by no vet) has explicit coverage via shouldListASpecialtyHeldByNoVeterinarian
- shouldRenderAllSpecialtiesOnOnePageWithoutPagination uses model().attributeDoesNotExist() to negatively assert pagination model attributes — a strong, behavior-specific assertion
- All 5 REQ-VET-003 test_names from the prd-entry pass and are present in the suite
- No JUnit raw assertions; MockMvc result matchers are the correct idiom for this test layer

**doc-reviewer**

- PRD boundary respected: no implementation mechanism, framework constructs, or code references appear in the new PRD narrative or Done-when bullets
- REQ-VET-003 anchor present on its own line in the correct lowercase-hyphenated form
- Every Done-when bullet carries the [REQ-VET-003] tag; the three bullets collectively cover each acceptance contract stated in the narrative
- Edge cases are numbered and citable; edge case 2 covers both specialty ordering and no-specialty bucket position as a stable-order requirement consistent with REQ-VET-001 edge case 1
- Navigation deferral is correctly recorded as a deferral in Open Questions ('Deferred, not declined; it will return as its own request if pursued') rather than as a non-goal entry — the Non-Goals table and NG-2 are unchanged
- The four new Open Questions entries give narrowest-reading resolutions with explicit cross-references back to their edge-case anchors, consistent with the answered-question pattern used throughout the PRD
- Cross-document coherence: REQ-VET-003 cited in system-design.md Contracts table (SpecialtyRepository, VetController, Specialty rows) matches the active req_id in prd.md; no orphan IDs introduced
- Design link in the Specialty directory section resolves to system-design.md#contracts, the same target used by every other capability section
- NG-2 ('Managing veterinarians or their specialties through the application') is unchanged and correctly scopes out write flows, consistent with the read-only specialty view in REQ-VET-003

**code-quality-reviewer**

- Format check passes (./gradlew checkFormat UP-TO-DATE)
- SpecialtyRepository mirrors PetTypeRepository exactly: JpaRepository\<Specialty,Integer>, single @Query('SELECT s FROM Specialty s ORDER BY s.name') method, correct package placement
- Constructor injection used correctly in VetController; no @Autowired annotation; both dependencies injected via the single constructor, satisfying architecture-principles.md § Explicit dependencies
- showSpecialtyList is 28 lines, single-responsibility, and the seeding-then-inversion pattern (seed map from specialty list, then distribute vets) is clear and well-commented
- computeIfAbsent used as a defensive fallback for data-inconsistency cases where a vet holds a specialty absent from findSpecialties(); this avoids a NullPointerException rather than silently hiding the inconsistency
- Both vetRepository.findAll() overloads are @Cacheable('vets'); the specialty directory reuses the cached vet collection, no extra database round-trip
- specialtyList.html correctly reuses the layout fragment with the 'vets' active tab, mirrors vetList.html structure, and uses only message keys present in all 11 bundles
- noSpecialty key added consistently to all 10 locale bundles in the same position (after 'none'), verified in full diff
- Naming is correct throughout: SpecialtyRepository (suffix Repository, Specialty-rooted), findSpecialties(), showSpecialtyList(), noSpecialtyVets — all follow architecture-principles.md § Naming and the ubiquitous-language vocabulary
- Test factory method specialty(int,int) eliminates the inline Specialty construction that previously duplicated across helen() and setup()

**doc-reviewer**

- PRD boundary respected: no implementation mechanism, framework constructs, or code references appear in the new PRD narrative or Done-when bullets
- REQ-VET-003 anchor present on its own line in the correct lowercase-hyphenated form
- Every Done-when bullet carries the [REQ-VET-003] tag; the three bullets collectively cover each acceptance contract stated in the narrative
- Edge cases are numbered and citable; edge case 2 covers both specialty ordering and no-specialty bucket position as a stable-order requirement
- Navigation deferral is correctly recorded as a deferral in Open Questions rather than as a non-goal entry
- Cross-document coherence: REQ-VET-003 cited in system-design.md Contracts table matches the active req_id in prd.md; no orphan IDs introduced
- Design link in the Specialty directory section resolves to system-design.md#contracts

**security-reviewer**

- JPQL query SELECT s FROM Specialty s ORDER BY s.name is static with no parameters or concatenation — no JPQL/SQL injection
- showSpecialtyList accepts no request parameters; read-only page over repository data — no user-controlled input reaches any sink
- specialtyList.html renders all dynamic values (specialty names, vet full names) via auto-escaping th:text with no th:utext, inline JS, or attribute injection — no XSS
- Data exposure bounded to specialty names plus vet full names, within PRD scope
- Message-bundle additions are static labels with no interpolation; no secrets or new dependencies in the delta
- Delta since prior approval is test-only plus unchanged production code; re-reviewed full diff confirms no new security surface

**code-quality-reviewer**

- Format check passes (checkFormat UP-TO-DATE, no violations)
- SpecialtyRepository.findSpecialties() JPQL ORDER BY clause cleanly enforces name order; SpecialtyRepositoryTests @DataJpaTest proves the clause matters by seeding out-of-alphabetical-order data
- All five VetController REQ-VET-003 tests follow the the{Subject}Should... naming school consistently
- Shared vet() and specialty() factory methods eliminate construction boilerplate without mystery literals
- Ordering test verifies Douglas renders before Leary by position in rendered HTML, giving the comparator real teeth
- Stable-position test for 'No specialty' grouping verifies the unconditional row appears after named specialties
- Constructor injection used throughout; no @Autowired
- AssertJ assertThat() used exclusively; no JUnit-era assertEquals
- No System.out/err in production code
- Message bundle additions are complete across all 10 locale files

**test-reviewer**

- All five REQ-VET-003 tests renamed to the BDD school (the{Subject}Should{Outcome}), leading with theSpecialtyDirectory; SpecialtyRepositoryTests follows the same school
- Duplicate byFullName test replaced with theSpecialtyDirectoryShouldShowVeterinariansByFullName asserting contains('Helen Leary').doesNotContain('Leary Helen') — independently verifies first-then-last ordering, not a clone of any other test
- Stable-order coverage (prior CRITICAL) is genuinely resolved with teeth: theSpecialtyDirectoryShouldOrderVeterinariansWithinASpecialtyByLastNameThenFirstName inserts Leary-then-Douglas and asserts indexOf('Linda Douglas') \< indexOf('Helen Leary'); removing the Comparator.comparing(Vet::getLastName).thenComparing(Vet::getFirstName) sort at VetController.java:100 would invert insertion order and fail this assertion
- SpecialtyRepositoryTests (@DataJpaTest, real I/O, Replace.NONE): theSpecialtyRepositoryShouldReturnSpecialtiesInNameOrder calls findSpecialties() against the seeded store and asserts isSorted() — dropping the ORDER BY s.name clause from the @Query would return insertion order (radiology, surgery, dentistry) which is not alphabetical, failing the assertion; test has genuine teeth
- theSpecialtyDirectoryShouldHoldTheNoSpecialtyGroupingAfterTheSpecialties asserts indexOf('surgery') \< indexOf('No specialty') — exercises the structural guarantee that the no-specialty bucket follows all named-specialty sections
- Redundant inline comment at prior line 87 is gone; setup() is comment-free
- No JUnit assertEquals/assertTrue usage anywhere in either test file; all assertions are fluent AssertJ
- No phase comments (// Arrange, // Act, // Assert) in any new test
- Factory methods specialty(int,String) and vet(int,String,String,Specialty...) used for all object construction; no raw constructor calls in test bodies
- No mystery literals; helenLeary, lindaDouglas, radiology are meaningfully named local variables
- No Mockito in SpecialtyRepositoryTests; @DataJpaTest drives real JPA I/O cleanly
- vet package line coverage: 51/51 = 100%, well above the 80% target
- All nine VetControllerTests and the one SpecialtyRepositoryTests pass on ./gradlew test

**doc-reviewer**

- docs/prd.md:137 sentence split at 'its own address alone. No navigation entry...' confirmed applied (prior prd-autofix record).
- docs/system-design.md:104 'Mirrors PetTypeRepository' cross-reference removed from SpecialtyRepository Description cell confirmed applied (prior design-doc-autofix record).
- docs/prd.md:140 Done-when bullet (~38 words) — judged exempt from the 30-word narrative sentence limit. The given/when/then format is mandated acceptance-criteria structure (prd-authoring skill § Requirement Format), not narrative prose. Forcing this criterion under 30 words would require dropping either the stored-name condition or the first-name-ordering condition, each of which is a distinct testable acceptance condition. Bullet approved as written.
- docs/prd.md:141-142 Done-when bullets are well-formed and within acceptable length.
- docs/prd.md edge cases 1 and 2 are precise, bounded, and citable.
- docs/system-design.md REQ-VET-003 rows (Specialty, SpecialtyRepository, VetController) are coherent and at the correct abstraction level with no prohibited patterns.

**doc-reviewer**

- docs/prd.md:137 autofix confirmed applied: 'each shown by full name with the first name before the last name' replaced by 'each shown by full name (first name first)', reducing sentence to ~28 words (within 30-word limit); semantic meaning preserved.
- docs/prd.md:140 Done-when bullet retains full acceptance-criteria precision with given/when/then structure; exempt status reaffirmed.
- No new prohibited patterns, structural violations, or cross-document coherence issues introduced by the autofix.
- All aspects approved in prior pass (line 34) remain valid; no production code, tests, or other doc files changed.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `(parent)` | 1 | opus-4-8 | $5.27 | 51m 50s | 97% |
| `spring-boot-claude:feature-implementer` | 3 | opus-4-8 | $5.02 | 16m 28s | 95% |
| `spring-boot-claude:doc-reviewer` | 4 | sonnet-4-6 | $1.31 | 10m 46s | 81% |
| `spring-boot-claude:system-design-expert` | 2 | opus-4-8 | $1.26 | 4m 29s | 83% |
| `spring-boot-claude:security-reviewer` | 2 | opus-4-8 | $0.88 | 1m 17s | 70% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $0.80 | 5m 53s | 87% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $0.78 | 6m 2s | 87% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $0.70 | 1m 48s | 86% |
| `spring-boot-claude:product-requirements-expert` | 1 | opus-4-8 | $0.64 | 2m 7s | 88% |
| `spring-boot-claude:pipeline-coordinator` | 2 | sonnet-4-6 | $0.15 | 29s | 47% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-4-8 | $5.27 | 51m 50s | 97% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $2.88 | 9m 52s | 96% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.75 | 5m 32s | 95% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $0.88 | 3m 28s | 82% |
| `spring-boot-claude:change-grader` | opus-4-8 | $0.70 | 1m 48s | 86% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.64 | 2m 7s | 88% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.52 | 4m 20s | 88% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.46 | 40s | 70% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.45 | 3m 52s | 84% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.42 | 36s | 70% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.41 | 3m 26s | 73% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.41 | 3m 6s | 83% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $0.39 | 1m 3s | 89% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $0.39 | 1m 1s | 84% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.39 | 2m 46s | 90% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.32 | 2m 57s | 84% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.26 | 1m 41s | 85% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.12 | 29s | 78% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.08 | 12s | 45% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.07 | 17s | 50% |

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

- plugin `spring-boot-claude` at `v0.1.28` (tag)
- model requested `claude-opus-4-8`; models used: opus-4-8 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
