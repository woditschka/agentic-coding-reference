# specialty-directory r2 — v0.4.0

Specialty directory page (feature) · started 2026-09-11T20:24:13+00:00 · exec `claude-dev` · status **complete**

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
| reading depth (pipeline grade) | scrutinize |

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
| 4 (±0) | 4 (±0) | 4 (±0) | 4 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.55. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> The inclusion, ordering and match-by-identifier rules sit in  SpecialtyListing.of / holds , which are framework-free, and the unit test covers them.  showSpecialtyList  stays a thin controller method and  SpecialtyRepository  is a minimal package-private interface. Weaknesses:  SpecialtyListing  fits no catalog pattern cleanly. Its public  equals / hashCode  mainly serve tests, and it wraps mutable  Vet  entities.  SpecialtyListingTests  uses BDD names, anonymous factories ( aSpecialty ,  aVetHolding ), whole-object  containsExactly  assertions and a hand-written repository lambda. The controller tests rely on loose  containsString  checks, and  HIGHLIGHTED_NAV_ENTRY  asserts layout markup. The PRD and system-design rows are updated thoroughly. However, the PRD header still says "ten further questions stay open" after the patch adds two new open questions.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The inclusion, ordering and match-by-identifier rules live in SpecialtyListing, which is framework-free and has its own unit tests. That moves the test pyramid in the right direction. VetController.showSpecialtyList only binds, delegates and returns a view, and SpecialtyRepository is thin. Minor debt: SpecialtyListing is public only because of the runtime hints, and its equals/hashCode have no production caller. SpecialtyListingTests has BDD names, anonymous factories (aSpecialty, aVetHolding) and whole-object containsExactly checks. The controller tests use a hand-written lambda double for SpecialtyRepository. Weak spots: HTML substring checks such as PAGE_SELECTOR_QUERY and HIGHLIGHTED_NAV_ENTRY are brittle, and james()/helen() keep bare ids. The PRD, the contracts table, the invariants and the open questions are all updated consistently.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> SpecialtyListing.of holds the inclusion, ordering and match-by-identifier rules outside the controller, and showSpecialtyList only binds, delegates and selects the view. That fits the Web controller row and the pyramid guidance. equals/hashCode on SpecialtyListing is unused in production and relies on entity identity, so it adds surface. SpecialtyListingTests follow the principles: BDD names, anonymous factories and whole-object containsExactly. The controller tests use a hand-written SpecialtyRepository lambda instead of Mockito. The one-page test only checks that 'page=' is absent, and the nav test asserts on layout CSS ('nav-link active'). The PRD and system-design contracts are updated, but the PRD provenance line still says 'ten further questions stay open' after this patch adds two.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.63 | 33m | 4 | 93% | 9 file(s) +441/−17 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.90 | 2m 41s | 87% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · grade **SCRUTINIZE**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (1) | **✔** |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- • intake-decision (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **minor** · (design) · ***◷ 6m***
- ◆ **implement** (implementer) · ***◷ 12m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `SpecialtyListing.java:39-87` The nested type SpecialtyListing.Entry uses the exact generic name architecture-principles.md's Naming section names as prohibited: 'Names come from the project's canonical vocabulary (ubiquitous-language.md): if the PRD calls it a "feed item", the code says FeedItem, never Entry or Record' (docs/architecture-principles.md:115). The type pairs one Specialty with its holding veterinarians; ubiquitous-language.md defines no term for this pairing, so a domain-facing name should be coined instead of the placeholder 'Entry' (e.g. SpecialtyHolding, or SpecialtyListing.Row naming the specialty+holders pair by role). The generic name is used throughout: the field/method in SpecialtyListing.java (lines 39, 41, 46, 48, 53, 81, 83), the constructor and factory helper in SpecialtyListingTests.java:113-114, and the model variable 'entry' in specialtyList.html:17-20.
    - fix: Rename SpecialtyListing.Entry (and the 'entries'/'entry' variables that reference it) to a domain-facing name that is not a bare structural placeholder, updating SpecialtyListing.java, SpecialtyListingTests.java, and specialtyList.html together.
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 3m***
  - [autofix] `SpecialtyListing.java:70` SpecialtyListing.equals() is never invoked by any test. JaCoCo (build/reports/jacoco/test/html/org.springframework.samples.petclinic.vet/SpecialtyListing.java.html, line 70, class="nc bnc", "All 4 branches missed") shows 0% branch coverage and the class-level report (org.springframework.samples.petclinic.vet/index.html) lists SpecialtyListing at 1 of 11 methods missed. Every SpecialtyListingTests assertion unwraps via listing.getEntries() and compares the entry list, so the equals()/hashCode() pair the type ships for whole-object comparison (testing-principles.md § Assertions, "Whole-object comparison") is dead from the test suite's perspective. Coverage is judged by behavior exercised, not lines touched (testing-principles.md § Coverage), so the passing line-coverage number does not excuse this.
    - fix: Add one case (e.g. in theSpecialtyListingShould... form) that builds two SpecialtyListing instances over equal and over differing input and asserts assertThat(listing).isEqualTo(...)/isNotEqualTo(...), exercising equals()/hashCode() directly per the brief's whole-object comparison guidance.
- ↻ **implement** (implementer · routine) ← code-quality, test · (2 findings) · ***◷ 2m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved** · ***◷ 40s***
- ✔ **review code-quality** · **approved** · ***◷ 58s***
- ◆ **grade SCRUTINIZE** · add read-only specialty listing page
  - blast_radius — **skim** — Contained to the vet package: one new read-only GET handler, a package-private read-only repository, a pure value object, one template, and two reflection-only native hints. It publishes the same vet and specialty names /vets.html already shows. Most of the 32 hunks are doc lines and test constants pulled out of VetControllerTests.
  - semantic_surprise — **skim** — I read every hunk. The comparators, the matching by identifier in holds(), the empty-list case, and the List.copyOf copy all do what the PRD says. The existing /vets.html and /vets handlers are unchanged apart from a new constructor argument. The 'specialties' menu argument matches no layout nav entry, so nothing is highlighted, and every value renders through escaped th:text. One minor edge: name ordering is case-sensitive and would throw on a null name, but the seeded data is safe.
  - test_adequacy — **skim** — The tests exercise real behavior. Unit tests cover multi-specialty listing, ordering on last then first name, the unheld specialty, identifier-versus-instance matching, and equals/hashCode. MockMvc tests render the real template for order, full name, omission, one page, 'none', and nav. Residual gap: no test runs SpecialtyRepository.findAll against the seeded database, which is the same derived pattern as VetRepository.findAll.
  - reviewer_hedging — **scrutinize** — All four reviewers approved and none left recommendations. But the doc-reviewer's approval cites line numbers that do not resolve. It puts the system-design.md provenance note at :58-59 and the invariants sentence at :68, but both at review time and now they are at :10 and :82. Its prd.md ranges are off by two. The docs did not change between rounds, so these citations are simply wrong. The security reviewer's unrun dependency check is a standing project gap, not a hedge.
  - scope_deviation — **skim** — No build retries, consultations, or design revisions. The diff stays inside the owner's request: read-only, one page, no nav entry or link, no management actions. PRD edge cases 4 and 5 (unheld specialty shown as none, alphabetical order) were scoping choices and are recorded as open questions. The design-block justifies adding SpecialtyRepository and leaving VetRepository untouched.
  - why — The code is small, contained, and matches the requirement. I read every hunk and found no behavioral surprise. The only flag is the doc-reviewer's approval, whose system-design.md and prd.md line citations do not resolve. Read the two doc hunks yourself rather than trusting that approval; the code can be skimmed.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Binding and mass assignment: the new handler binds no request data. A grep over the diff's added lines for @RequestParam @PathVariable @ModelAttribute @RequestBody setAllowedFields matched nothing; the only hits of the combined pattern were the word Runtime at diff lines 93 and 151 (PetClinicRuntimeHints). VetController.java handler  public String showSpecialtyList(Model model)  takes only the Model, so no request-bound type exists and the security-principles mass-assignment row is not engaged. Basis is grep (IntelliJ oracle not connected), the weaker basis.
- XSS: every value in the new template renders through escaped th:text. specialtyList.html has  th:text="${entry.specialty.name}"  and  th:text="${vet.firstName + ' ' + vet.lastName}" .  grep -nE 'utext \[\( __\$\{' src/main/resources/templates/vets/specialtyList.html  returned no match (exit 1), so there is no unescaped output, no unescaped inline, and no preprocessing in the new template. That matches the escaping already used for the same fields in vets/vetList.html:18  th:text="${vet.firstName + ' ' + vet.lastName}" .
- Template preprocessing: the page passes the literal 'specialties' as the layout's menu argument. fragments/layout.html:31 uses menu only in the equality  ${active==menu ? 'nav-link active' : 'nav-link'} , and its  __${link}__  preprocessing is fed only by the fixed literals at layout.html:41-57. No request-derived text reaches expression evaluation.
- Injection into data access: SpecialtyRepository adds only the derived query  Collection\<Specialty> findAll()  under @Transactional(readOnly = true). No @Query, createQuery, or nativeQuery appears in the added lines (same grep, no hit). The repository is package-private and read-only, and it adds no write path (least privilege; NG-2 respected).
- Widened surface: GET /specialties.html exposes, read-only and to any caller, veterinarian and specialty names that /vets.html and /vets already publish. It has no form, no mutation, and no new actuator or management exposure, and the change leaves the application no weaker than the system-design Security Context baseline.
- Resource use and concurrency: the listing is bounded by the stored vet and specialty tables, not by any request input, so query parameters such as ?page=2 are ignored. It is built fresh per request. Entry copies its vet list with List.copyOf and the factory returns Stream.toList() results, so no mutable state reaches the cached Vet entities or the singleton controller, which holds only final repository fields.
- Native-image hints: PetClinicRuntimeHints registers SpecialtyListing and SpecialtyListing.Entry with MemberCategory.INVOKE_PUBLIC_METHODS only. It adds no withJavaSerialization, so the unsafe-deserialization surface stays at the three existing types.
- Secrets and logging: a case-insensitive grep of the diff's added lines for password secret token apikey api_key credential private.?key jdbc: matched nothing (exit 1). The same pattern grep found no System.out or System.err in added lines, and the new handler builds no new exception messages that could reach the error page.
- Supply chain: no build file is in the change set ( scripts/changeset.sh --name-only   grep -F -e build.gradle -e pom.xml -e libs.versions  exit 1). The resolved runtimeClasspath from  ./gradlew dependencies  shows Spring Boot 4.1.1, spring-webmvc 7.0.9, Thymeleaf 3.1.5.RELEASE, and tools.jackson.core:jackson-databind 3.1.5. dependencyCheckAnalyze is not configured ( grep -i 'dependencycheck owasp' build.gradle  exit 1), so no NVD match ran in this review. ./gradlew test was not run by this reviewer; the build-pass record carries the gate.

**doc-reviewer**

- docs/prd.md:123-125 adds the  \<a id="req-vet-003">\</a>  anchor and REQ-VET-003 narrative in behavioral language only, with no URL literal, no Java construct, and no internal code reference (grep -F -e 'specialties.html' docs/prd.md returns no match)
- docs/prd.md Done-when bullets (lines 130-133) and edge cases 3-5 (lines 138-140) match the prd-entry's acceptance criteria for grouping, ordering, and the unheld-specialty case, phrased as given/when/then and behavioral list items, not mechanism
- docs/prd.md numbering: REQ-VET-003 correctly follows REQ-VET-002, which is already in the Superseded list (docs/prd.md:180), so no ID is skipped or reused
- docs/system-design.md Contracts rows for SpecialtyListing (line 104) and SpecialtyRepository (line 107) are purpose-plus-source-pointer prose with no field/parameter table and no constant literal, matching the source (SpecialtyListing.java: static factory, no framework import; SpecialtyRepository.java:  @Transactional(readOnly = true) , no  @Cacheable )
- docs/system-design.md invariants sentence (line 68, 'Specialty carries no association... by identifier, never by instance') matches the source comment in SpecialtyListing.java's  holds  method verbatim in substance
- docs/system-design.md VetController row (line 108) claim of a third route is verified against VetController.java:  /vets.html ,  /specialties.html ,  /vets  (3  @GetMapping  handlers)
- No new domain term introduced; 'Specialty' and 'Veterinarian' are already defined in docs/ubiquitous-language.md and used with matching spelling
- No imperative (Do/Don't/Always/Never/Require) lines were added to docs/system-design.md, so no missing-ADR-backlink finding applies (grep -n over the diff hunks for those lead words returns no match)
- Both documents' new provenance notes (prd.md:9-10, system-design.md:58-59) follow the existing exception-marking convention and cross-reference each other's owner-stated/designed status
- No hard-wrapped prose or mid-word hyphen breaks in the added lines; each paragraph is one logical line

**code-quality-reviewer**

- ./gradlew checkFormat passes clean on the change set (google-java-format/spring-javaformat compliant)
- SpecialtyListing keeps the grouping/ordering/matching-by-identifier rules out of VetController per the Web controller catalog row (architecture-principles.md:85); VetController.showSpecialtyList (VetController.java:68-74) only reads both repositories, builds the view, and returns the view name — verified by reading the method body
- Full-name rendering in specialtyList.html:20 (${vet.firstName + ' ' + vet.lastName}) matches the existing pattern in vetList.html:18, confirmed by reading both templates side by side
- No new message-bundle keys were added; specialtyList.html reuses the existing specialties, name, vets, and none keys already present in messages.properties (grep -F confirms all four keys pre-exist at messages.properties:21-24), satisfying REQ-LANG-002 without new translation work
- python3 scripts/grading.py conventions-map shows every added comment block explains WHY (e.g. SpecialtyRepository.java:23-27 on why specialties absent from VetRepository are needed, SpecialtyListing.java:61-63 on matching by identifier) rather than restating the code
- New types stay within the vet package and match In-force catalog patterns (Repository, Value object) per architecture-principles.md's Pattern Catalog; no prohibited suffix (Manager/Helper/Utility/Handler/Processor/Base/Info/Data) is used

**test-reviewer**

- Test placement matches the design-block's assignment: the two rules the design doc assigns below the boundary (multi-specialty grouping, alphabetical ordering) are unit-tested in SpecialtyListingTests with real Vet/Specialty instances and no Spring context, and the six rules assigned to the web/template boundary are exercised through the existing @WebMvcTest(VetController.class) MockMvc slice in VetControllerTests (system-design-expert design-block, integration_points list) - src/test/java/org/springframework/samples/petclinic/vet/SpecialtyListingTests.java and VetControllerTests.java
- All 8 prd-entry test_names are present and passing:  python3 scripts/grading.py coverage-map --feature REQ-VET-003  reports 'Declared tests: 8 of 8 present' and  ./gradlew test --tests org.springframework.samples.petclinic.vet.*  completed BUILD SUCCESSFUL
- Mocking policy honored: SpecialtyRepository is a hand-written fixed lambda double registered via a nested @TestConfiguration (VetControllerTests.java:117-124), not a Mockito stub, matching the design-block's integration_points direction; the existing @MockitoBean VetRepository stub is reused unchanged with no new given(...) stubbing added
- Identifier-vs-instance matching risk from the design-block's risks list is directly covered: SpecialtyListingTests.theSpecialtyListingShouldMatchAHeldSpecialtyByIdentifierRatherThanInstance (lines 70-77) builds a separate Specialty instance sharing only the id, verifying SpecialtyListing.of matches by identifier not reference
- Test data naming follows the three-tier convention with no mystery literals:  python3 scripts/grading.py conventions-map  shows every literal-bearing line in the changed test files named by role (RADIOLOGY, HELEN_FIRST_NAME, etc.) or carrying an any-/aSpecialty-style irrelevant-value factory, and all Specialty/Vet construction happens through file-owned factory methods (specialty(...), aVetNamed(...), aVetHolding(...))

**test-reviewer**

- Prior finding resolved: SpecialtyListing.equals()/hashCode() are now directly exercised by two new tests, theSpecialtyListingShouldEqualAListingOfTheSameSpecialtiesAndHolders and theSpecialtyListingShouldDifferFromAListingWhereTheSpecialtyHasDifferentHolders (SpecialtyListingTests.java:80-98), asserting assertThat(listing).isEqualTo(...).hasSameHashCodeAs(...) and isNotEqualTo(...); JaCoCo now reports 'L70 pc bpc, 1 of 4 branches missed' on the equals() line versus the prior 'All 4 branches missed' (build/reports/jacoco/test/html/org.springframework.samples.petclinic.vet/SpecialtyListing.java.html)
- Both new tests follow four-phase structure with blank-line separation, use the suite's existing named factories (aSpecialty(), aVetHolding()) rather than raw construction, and use fluent AssertJ chaining consistent with the rest of the file
- The Entry-to-ListedSpecialty rename (code-quality-reviewer's prior finding) is applied consistently across production (SpecialtyListing.java, PetClinicRuntimeHints.java, specialtyList.html) and test code (SpecialtyListingTests.java) with no leftover 'Entry' references: grep -F -e 'Entry' -- src/ found no remaining SpecialtyListing.Entry usages
- ./gradlew test --tests org.springframework.samples.petclinic.vet.SpecialtyListingTests --tests org.springframework.samples.petclinic.vet.VetControllerTests completed BUILD SUCCESSFUL, confirming the rename did not break VetControllerTests

**code-quality-reviewer**

- The prior finding's naming issue is fixed: SpecialtyListing.Entry is renamed to SpecialtyListing.ListedSpecialty throughout production code, tests, and the template together (SpecialtyListing.java, PetClinicRuntimeHints.java, specialtyList.html, SpecialtyListingTests.java); grep -F -e Entry -e .entries -e getEntries across src/ and docs/ finds no residual reference to the old name outside unrelated java.util.Map.Entry usages in I18nPropertiesSyncTest.java and CrashControllerIntegrationTests.java, and an unrelated 'Entry point' heading in docs/prd.md:161
- No ubiquitous-language.md term exists for the specialty-plus-holders pairing, so the coined name ListedSpecialty is a legitimate domain-facing choice rather than a rejected synonym (docs/ubiquitous-language.md defines Veterinarian and Specialty but no pairing term)
- The test-reviewer's coverage finding is addressed: two new tests (theSpecialtyListingShouldEqualAListingOfTheSameSpecialtiesAndHolders, theSpecialtyListingShouldDifferFromAListingWhereTheSpecialtyHasDifferentHolders in SpecialtyListingTests.java:79-97) exercise SpecialtyListing.equals()/hashCode() directly via assertThat(...).isEqualTo/isNotEqualTo/hasSameHashCodeAs, per testing-principles.md's whole-object comparison guidance
- ./gradlew checkFormat passes clean on the current tree (BUILD SUCCESSFUL)
- python3 scripts/grading.py conventions-map shows every comment block in the fix-delta files still explains WHY, with no restated-signature or narration comments introduced by the rename

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $4.26 | 15m 42s | 94% |
| `agent-team:system-design-expert` | 1 | opus-5 | $2.07 | 6m 19s | 93% |
| `(parent)` | 1 | opus-5 | $1.29 | 35m 59s | 96% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.14 | 3m 37s | 89% |
| `agent-team:change-grader` | 1 | opus-5 | $0.90 | 2m 41s | 87% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.86 | 4m 49s | 94% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.77 | 4m 3s | 93% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.74 | 1m 13s | 87% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.50 | 2m 34s | 94% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.23 | 12m 54s | 95% |
| `agent-team:system-design-expert` | opus-5 | $2.07 | 6m 19s | 93% |
| `(parent)` | opus-5 | $1.29 | 35m 59s | 96% |
| `agent-team:product-requirements-expert` | opus-5 | $1.14 | 3m 37s | 89% |
| `agent-team:feature-implementer-routine` | opus-5 | $1.03 | 2m 48s | 94% |
| `agent-team:change-grader` | opus-5 | $0.90 | 2m 41s | 87% |
| `agent-team:security-reviewer` | opus-5 | $0.74 | 1m 13s | 87% |
| `agent-team:test-reviewer` | sonnet-5 | $0.66 | 3m 50s | 95% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.50 | 2m 43s | 93% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.50 | 2m 34s | 94% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.27 | 1m 20s | 94% |
| `agent-team:test-reviewer` | sonnet-5 | $0.20 | 58s | 89% |

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

- plugin `agent-team-spring-boot` at `v0.4.0` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `6cbb44ce4c9a` (branch `agent-team`)
- task fingerprint `dc643d9216b8dc0b` · `2.1.268 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
