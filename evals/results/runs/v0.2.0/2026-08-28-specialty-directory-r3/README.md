# specialty-directory r3 — v0.2.0

Specialty directory page (feature) · started 2026-08-28T10:22:18+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±1) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.77. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Placement is sound: SpecialtyController.java:37-41 binds and delegates only, grouping and ordering live in the immutable SpecialtyDirectoryEntry record (defensive List.copyOf, named comparators), and dependencies are constructor-injected. Two nits: directoryOf is a domain-service-shaped operation hung on an entry type, and SpecialtyRepository gives a non-root lookup type its own repository without an ADR. Tests are the strongest part — behavior names throughout, hand-written stubs instead of a mock framework, and a framework-free unit test for the read model. But specialty(...)/vet(...) factories are duplicated verbatim in both test classes, StubSpecialtyRepository is a shared mutable bean restored in @BeforeEach, and containsExactly(3, 1, 2) is bare-id scaffolding. specialtyList.html:24 concatenates a trailing space to separate holders — a display hack. Docs (PRD, contracts, persistence, security, open questions, ADR index) are all current.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Ordering and grouping sit in  SpecialtyDirectoryEntry.directoryOf , unit-testable without the framework, leaving  SpecialtyController.showSpecialtyDirectory  rule-free — the pyramid and Web-controller rows are respected; the  @Cacheable  key-collision note on  findAllHoldingASpecialty  is exactly the reasoning a reviewer wants. Minor:  directoryOf  returning the whole directory from an entry type reads as a missing  SpecialtyDirectory , and  SpecialtyRepository  assumes Specialty is an aggregate root. Tests use hand-written stubs over mocks and BDD names, but  specialty(...) / vet(...)  factories are copy-pasted across both test classes against the shared-vocabulary rule, and  doesNotContain("page=")  and  stringContainsInOrder("navbar", ...)  are brittle proxies.  specialtyList.html  uses  #{specialties} / #{none}  yet no bundle file changes, so the German assertion looks unsatisfiable. Docs are current throughout.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Placement and layering are right: SpecialtyController delegates only, grouping and ordering live in the immutable SpecialtyDirectoryEntry record (List.copyOf in the compact constructor), and SpecialtyRepository exposes one read. The findAllHoldingASpecialty javadoc explaining the SimpleKey.EMPTY cache-key collision shows real care. Tests avoid mock frameworks (StubVetRepository, StubSpecialtyRepository), use BDD names, and split framework-free unit tests from the @WebMvcTest and @DataJpaTest slices. Deductions: the specialty()/vet() factories are duplicated verbatim in SpecialtyControllerTests and SpecialtyDirectoryEntryTests instead of shared vocabulary; bare id literals (containsExactly(3, 1, 2)) read as mystery values; the navigation test hardcodes a relative path and a bare substring match. Docs — PRD REQ-VET-003, contracts table, persistence rule, ADR + index, open question 5 — are all current.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $14.78 | 44m | 38 | 92% | 13 file(s) +812/−6 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.84 | 2m 24s | 90% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Specialty directory

2 review rounds · 2 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** (1) | **✔** |
| **doc** | **✖** (2) | **✔** |

- ◇ **prd-entry** Specialty directory · (prd-expert) · ***◷ 41s***
- ◈ **design-block** **minor** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 10m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **minor** · (design) · supersedes L4 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 53s***
  - ▲ **build ✓ clean** · build · test · format · check · autofix-audit · handoff-log
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 50s***
- ✔ **review security** · **approved** · (1 finding) · ***◷ 1m***
  - [autofix] `system-design.md:182` The threat-model row still reads "one parameterized JPQL query" as the mitigation inventory. This change adds a second @Query (VetRepository.findAllHoldingASpecialty), so the count is now stale: production holds two literal JPQL queries (VetRepository:73 and owner/PetTypeRepository:36), and neither takes a bind parameter at all. The security property the row asserts is unchanged and still true (no string-concatenated SQL, no user input reaching a query string) -- only the count and the word "parameterized" drift. Swept all of src/main/java for @Query: these two are the complete set, so this is the only instance of the class.
    - fix: Update the mitigation cell to: "Data access is exclusively through Spring Data JPA derived queries and two static JPQL queries, neither of which takes user input; no string-concatenated SQL exists in production code."
- ✖ **review doc** · **blocked** · (2 findings) · ***◷ 2m***
  - **[blocked]** `system-design.md:82-109` The Contracts table was not updated for this slice even though three new production types exist (SpecialtyController, SpecialtyDirectoryEntry, SpecialtyRepository — all `--- /dev/null` in the diff) and VetRepository gained a new method. None of SpecialtyController, SpecialtyDirectoryEntry, or SpecialtyRepository has a Contracts row, so a reader following the PRD's `[system-design.md#contracts]` link from the Specialty directory section (prd.md:153) finds no trace of REQ-VET-003's contracts. VetRepository's existing row (system-design.md:103, 'Spring Data repository for veterinarians; results are cached') is now stale on two counts: its Implements column still reads only REQ-VET-001 though `findAllHoldingASpecialty` implements REQ-VET-003, and the blanket 'results are cached' description no longer holds — the new method is deliberately not `@Cacheable`. This is one class (production surface added/changed by the slice, not reflected in the Contracts table); all four instances above belong to it.
  - **[blocked]** `prd.md:133-153` The section carries a **Design:** link but no **ADR:** link to docs/adr/2026-08-28-in-memory-ordering-for-unpaged-listings.md, even though that ADR's own Implementation section states '**Requirements:** REQ-VET-003' — the prd-authoring convention makes the ADR link mandatory whenever an ADR records the decision behind the requirement (see NG-4/NG-5 rows in this same file, which link their governing ADR). Edge case 3 ('Specialties are presented in a stable order...') is exactly the decision the ADR records, so a reader of prd.md has no path to the rationale for that edge case.
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `SpecialtyDirectoryEntry.java:49-52` The holder comparator is a three-level tiebreak (last name, then first name, then id), mirroring the specialty comparator's two-level tiebreak (name, then id). The specialty side has a dedicated test pinning its id tiebreak (theSpecialtyDirectoryShouldListTwoSpecialtiesSharingOneNameSeparately, ids 2 and 9 both named "surgery"), but no test exercises the holder side's final id tiebreak: theSpecialtyDirectoryShouldPresentHoldersInAStableOrder only pins the last-name-tie -> first-name-tiebreak level (Ada Douglas before Linda Douglas). Two holders with the same last name AND first name (a realistic clinic scenario, e.g. two vets literally named "Linda Douglas") would exercise Vet::getId as the deciding comparator level, and nothing today would catch a regression there. This is the same ordering-stability property the ADR (docs/adr/2026-08-28-in-memory-ordering-for-unpaged-listings.md) calls out for specialties, left half-pinned for holders.
    - fix: Add a test (e.g. theSpecialtyDirectoryShouldBreakATieOnMatchingHolderNamesByIdentifier) with two Vet instances sharing both first and last name but distinct ids, asserting the lower id sorts first, mirroring theSpecialtyDirectoryShouldListTwoSpecialtiesSharingOneNameSeparately's shape.
  - [autofix] `SpecialtyControllerTests.java:159-169` This test walks the filesystem and greps template text; it never touches MockMvc, the injected stub repositories, or any Spring-managed bean. Per testing-principles.md's pyramid guidance ("could this have been tested without booting the framework? If yes, it belongs in a unit and the test belongs in the base of the pyramid"), this is pure JVM logic riding inside a @WebMvcTest class for no structural reason — it could run as a plain JUnit test with zero Spring context, which would also decouple it from ever being skipped by @DisabledInNativeImage/@DisabledInAotMode on the class.
    - fix: Move this test (and its mentionsTheSpecialtyDirectoryAddress helper) to a plain, non-Spring JUnit test class alongside or in SpecialtyDirectoryEntryTests's package, so it counts toward the unit tier rather than riding on the web-layer test's context.
- ↻ **fix prd-expert** ← doc · (2 findings)
- ↻ **fix design** ← doc · (2 findings)
- ◇ **prd-entry** Specialty directory · (prd-expert) · ***◷ 49s***
- ◈ **design-block** **minor** · (design) · supersedes L8 · ***◷ 1m***
- ↻ **implement** (implementer) ← test · (2 findings) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · format · autofix-audit · handoff-log
- • review-plan (review-plan-engine)
- ↻ **fix test** ← test · (2 findings)
- ✔ **review code-quality** · **approved** · ***◷ 23s***
- ↻ **fix doc** ← doc · (2 findings)
- ✔ **review doc** · **approved** · ***◷ 46s***
- ✔ **review security** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 1m***
- ◆ **grade CLEAR** · add the specialty directory page
  - blast_radius — **clear** — Thirteen files but one production module: the vet package gains a controller, a read model, a repository, and a template, all new files, and the only edit to existing production code is an additive VetRepository query method. No sensitive paths, no binary files, and no existing route, entity, or template changes behavior.
  - semantic_surprise — **clear** — Read every hunk and nothing behaves unlike its description. The template mirrors vetList.html's idiom key for key, the join fetch is exactly the holds-at-least-one restriction its javadoc claims, the holder query is deliberately left out of the vets cache because a second no-argument method would share SimpleKey.EMPTY with findAll, and the grouping keys on specialty id rather than object identity, which is what lets it survive the two separate read transactions the controller opens.
  - test_adequacy — **clear** — Tests assert outcomes rather than restate the implementation: the read model's unit tests cover the empty directory, a specialty no one holds, a vet holding none, two specialties sharing a name, and both identifier tiebreaks; a DataJpaTest pins the join-fetch restriction and the no-duplicate-holder property against a real database; the WebMvcTest renders the page and checks the German bundle and the absence of pagination markup. The test-reviewer mutation-checked the tiebreak comparator.
  - reviewer_hedging — **clear** — The full four-reviewer roster was dispatched at high risk and round two returned four approvals with empty findings lists; the approved aspects read as independent re-verification, the security reviewer re-grepping every query annotation himself, rather than as reservations attached to an approval.
  - scope_deviation — **clear** — Two design revisions, but the second explicitly supersedes the first as records bookkeeping, the Contracts rows withheld while the types did not yet exist, which is also what the earlier design-mismatch build-failure was. Zero build retries, zero consultations, and every changed file maps onto the requirement's stated surface.
  - why — Additive throughout: a new route, read model, repository, and template in one package, plus one purely additive repository method. Nothing existing changes behavior. The subtle calls, uncached holder query, id-keyed grouping, Java-side ordering, are deliberate and documented. Confirm and merge; skim the ADR for the code-point ordering consequence.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyDirectoryEntry is a well-documented immutable record with defensive List.copyOf() on the compact constructor, and directoryOf() groups holders by specialty identifier via a HashMap keyed on getId(), matching the documented never-key-on-name rule
- Comparators are named constants (BY_NAME_THEN_ID, BY_LAST_NAME_THEN_FIRST_NAME_THEN_ID) with javadoc explaining the tiebreak rationale, keeping directoryOf() readable and under 20 lines
- SpecialtyRepository is scoped to the single read method the directory needs, with javadoc pointing to the in-memory-ordering ADR for why findAll() makes no ordering guarantee
- VetRepository.findAllHoldingASpecialty() carries clear javadoc explaining both the inner-join restriction and the deliberate omission of @Cacheable("vets") to avoid the SimpleKey.EMPTY collision with findAll()
- SpecialtyController is a minimal, single-responsibility @Controller matching the package-private/final-field style of the existing VetController
- specialtyList.html's th:text firstName + ' ' + lastName concatenation pattern is consistent with the existing vetList.html template, not a new deviation
- Test naming (BDD-style methods), AssertJ fluent assertions, and factory-method-backed test data (specialty(), vet()) follow testing-principles.md across all three new test classes
- ./gradlew checkFormat and compileJava/compileTestJava both pass clean

**security-reviewer**

- JPQL construction is safe: findAllHoldingASpecialty (VetRepository:73) is a compile-time string constant in the @Query annotation with no parameters, no concatenation, no SpEL, and no Sort/Pageable argument that could inject an order-by fragment. No injection sink exists.
- No untrusted input enters the slice: showSpecialtyDirectory (SpecialtyController:40) binds no @RequestParam, @PathVariable, @RequestBody, or form object, and declares no @InitBinder surface. The only argument is the framework-supplied Model, so there is no mass-assignment or identifier-tampering vector and no need for the id-disallow binder pattern the other controllers carry.
- Read-only end to end: SpecialtyRepository exposes findAll only (deliberately narrow), both repository methods are @Transactional(readOnly = true), and SpecialtyDirectoryEntry is an immutable record whose compact constructor defensively copies holders via List.copyOf. No write path is reachable from the new route, so the unauthenticated-modification threat-model row is not widened.
- Output escaping is correct in templates/vets/specialtyList.html: stored specialty names (line 19) and veterinarian first/last names (line 22) render through th:text, which HTML-escapes by default. There is no th:utext, no th:inline='javascript', no attribute-context or URL-context interpolation of stored data, and no th:href preprocessing (__${...}__) on user-derived values anywhere in the new template. Swept all of src/main/resources/templates for th:utext and th:inline: zero hits repository-wide, so stored-XSS via this page is not reachable. The literal 'specialtyDirectory' passed to the layout fragment is a static menu-name argument compared for equality, not rendered as markup.
- No new data exposure relative to the existing directory: /vets.html already renders every vet's first and last name with their specialty names to unauthenticated callers, and /vets serializes the same graph as JSON. The new page presents the identical fields under an inverted grouping. The only increment is specialty rows held by no veterinarian -- clinic reference data, not PII, and not a new data class. Judged on its merits rather than on the absent nav link, the exposure of this route equals that of /vets.html, so reachability by URL alone adds no attack surface the existing pages do not already carry.
- No secrets in the diff: swept the new Java sources, the template, and the touched docs for token/password/secret/key/credential/apikey. The only hit is docs/prd.md:18, pre-existing prose that cross-references the committed development credentials already recorded in system-design.md#security-context. Nothing new is introduced.
- Supply chain is a null delta: build.gradle, settings.gradle, and gradle/ are untouched by the change set (git diff --stat empty), so no new or upgraded dependency enters the tree and no CVE surface changes. The project configures no dependencyCheck plugin, so dependencyCheckAnalyze was not available to run; version-pinned Spring Boot 4.1.0 is unchanged by this slice.
- Deliberate cache-poisoning avoidance is correct and worth keeping: the Javadoc at VetRepository:66 explains that findAllHoldingASpecialty is not @Cacheable('vets') because, taking no argument, it would collide with findAll() on SimpleKey.EMPTY and the two could serve each other's results. That collision would have been a real integrity defect (the restricted inner-join result silently answering the unrestricted vet listing, or vice versa); the omission prevents it.

**doc-reviewer**

- docs/adr/2026-08-28-in-memory-ordering-for-unpaged-listings.md follows the project's ADR shape: Status, Context, Options Considered, Decision, Consequences, Implementation with a Requirements line, References with em-dashes
- docs/adr/README.md index row added correctly, chronologically placed, format matches neighboring rows
- docs/prd.md new section stays at the PRD altitude: behavioral prose, tagged Done-when bullets, numbered edge cases, no mechanism or rationale leakage; NG-2 is referenced rather than restated
- The three new Open Questions entries are appropriately scoped and match the narrowing decisions the ADR and prose state
- REQ-VET-003 anchor present at first mention; REQ-SYS-001 cross-reference in the new section resolves to an existing requirement

**test-reviewer**

- All 22 new tests pass (./gradlew test); SpecialtyDirectoryEntry and SpecialtyController sit at 100% line coverage per jacocoTestReport, well above the brief's 80% domain-package target
- The vet-holding-no-specialty exclusion (the inner JOIN FETCH restriction) is correctly pinned at the only layer that can observe it: SpecialtyDirectoryRepositoryTests (@DataJpaTest) verifies holder count against a real H2 database seeded from the project's actual data.sql fixture, not an invented one
- Two stored specialties sharing one name are proven to stay two entries and to order by identifier (theSpecialtyDirectoryShouldListTwoSpecialtiesSharingOneNameSeparately), at both the pure-unit and, indirectly through the same grouping-by-id code path, the rendering level
- Full-name ("first last") rendering is asserted at the actual rendered HTML via MockMvc content, not just at the read-model level, so a template regression concatenating the fields wrong would be caught
- The no-inbound-link acceptance criterion is verified by scanning every real template under src/main/resources/templates for the literal route string, which is a materially stronger check than asserting against a hand-picked list of pages
- No mock framework used anywhere in the new tests; StubSpecialtyRepository/StubVetRepository are hand-written real implementations per the brief's mocking policy, and SpecialtyDirectoryRepositoryTests exercises the real Spring Data query against a real database
- All 4 prd.md edge cases for REQ-VET-003 and all 9 named test_names in the prd-entry are present and use the project's the{Subject}Should{Outcome} naming school
- Test data construction goes through specialty()/vet() factory methods rather than raw constructors, and named constants (RADIOLOGY, JAMES_CARTER, etc.) carry role-describing names per the three-tier convention; no mystery literals found
- i18n wording test (theSpecialtyDirectoryWordingShouldComeFromTheMessageBundles) checks a non-default bundle's actual localized strings rather than the default, catching a hard-coded-string regression that a default-locale-only test would miss

**code-quality-reviewer**

- New tie-break test theSpecialtyDirectoryShouldBreakATieOnMatchingHolderNamesByIdentifier follows the existing AssertJ/four-phase/derived-value conventions of SpecialtyDirectoryEntryTests
- SpecialtyDirectoryNavigationTests is a well-scoped plain-JUnit class: no Spring context for a filesystem check, IOException wrapped with template-path context, class javadoc explains why it reads templates from disk rather than a rendered response
- Import cleanup in SpecialtyControllerTests leaves no unused imports and no other quality regressions
- checkFormatTest passes on the touched test sources; no production code changed since round 1

**doc-reviewer**

- Contracts table now carries SpecialtyDirectoryEntry, SpecialtyRepository, and SpecialtyController rows in the vet block's existing entity-then-repository-then-controller order; VetRepository's row is corrected on both counts named in round 1 (Implements now includes REQ-VET-003, and the cache description now states the specialty-holder read is deliberately uncached)
- prd.md's Specialty directory section now carries the ADR link in the combined Design/ADR line matching the docs/prd.md:99 precedent; verified against the ADR's own Requirements: REQ-VET-003 line, so the link direction is correct
- product-requirements-expert's decision to withhold the ADR link from REQ-VET-001 is correct under the PRD boundary rule: the ADR's Implementation section names REQ-VET-003 alone, and linking it from REQ-VET-001 would assert governance the ADR does not claim
- the three past-scope design-block additions all stay at the right altitude and are accurate: Vet/Specialty gaining REQ-VET-003 in Implements reflects real usage by the new read surface, the SpecialtyDirectoryEntry sentence in the Invariants paragraph is purpose prose (not a field table) consistent with prd.md edge case 4, and Open Questions item 5's narrowing to 'the two unrestricted read methods' is verified accurate against VetRepository.java's actual @Cacheable placement
- security-reviewer's SQL-injection Threat Model rewording ('two literal JPQL queries that take no argument at all') is verified accurate: exactly two @Query annotations exist in src/main/java (VetRepository.findAllHoldingASpecialty, PetTypeRepository), both argument-free
- cross-references resolve: system-design.md#contracts, the ADR file path, and the ADR README index entry all check out

**security-reviewer**

- Round-1 autofix finding is resolved, and the landed wording is better than the wording I proposed. My cell said "Spring Data JPA derived queries and two static JPQL queries, neither of which takes user input", which asserted the safety of the derived queries without saying what makes them safe. The Attack Vector column names user-supplied search text, and the derived query methods are the half of the mitigation that carries it, so leaving their mechanism implicit left the row's central claim unsupported. The landed cell (docs/system-design.md:185) states the mechanism explicitly -- derived query methods "bind their arguments as parameters" -- and then separates the two literal JPQL queries as taking no argument at all. That is what I meant and states it more completely; no correction needed.
- Re-verified every factual claim in the landed cell rather than accepting it on the system-design-expert's word. grep -rn '@Query' src/main/java returns exactly two hits (VetRepository:73, owner/PetTypeRepository:36); both annotation values are literal strings with no bind placeholder, no concatenation, and no SpEL, matching "two literal JPQL queries that take no argument at all". The claim "exclusively through Spring Data JPA" also holds: grep for nativeQuery, createQuery, createNativeQuery, EntityManager, JdbcTemplate, Criteria, and SpEL ('#{') across src/main/java returns zero hits, so no second data-access path exists that the row would have to account for. The row is now accurate and complete for the SQL-injection threat.
- Production code is unchanged since the round-1 approval, confirmed against the change set rather than against the dispatch narrative: scripts/changeset.sh --name-only lists the same four production files (SpecialtyController, SpecialtyDirectoryEntry, SpecialtyRepository, VetRepository) plus specialtyList.html, and their content still matches what round 1 cleared -- no request-bound parameters on showSpecialtyDirectory, findAll-only repository surface, immutable record with List.copyOf, and th:text-only rendering. The round-1 approved_aspects therefore carry forward unchanged.
- Test-only delta carries no security surface. The new comparator tiebreak in SpecialtyDirectoryEntryTests exercises ordering, not a trust boundary. SpecialtyDirectoryNavigationTests reads templates from a hardcoded relative constant Path.of("src/main/resources/templates") and walks it with Files.walk; the only path values it opens come from that walk, so no user- or environment-supplied component enters the path and there is no traversal vector. It is test scope in any case and ships in no artifact.
- Re-ran both round-1 class sweeps against the current tree rather than trusting the earlier result. Templates: grep for th:utext, th:inline, and the __${...}__ preprocessing form across src/main/resources/templates returns zero hits repository-wide, so the escaping guarantee the XSS threat-model row asserts still holds with the new page in the tree. Secrets: grep -i for password, secret, token, api-key/apikey, and credential across the new vet sources and specialtyList.html returns zero hits.
- Supply chain is again a null delta: git diff --stat over build.gradle, settings.gradle, and gradle/ is empty, so no dependency was added, upgraded, or repinned since round 1 and no new CVE surface enters the tree. dependencyCheckAnalyze remains unconfigured in this project, so the NVD scan was not available to run; the finding stands on the unchanged-manifest evidence instead.
- Doc rows added since round 1 introduce no security claim that outruns the code. The Contracts-table additions in docs/system-design.md and the ADR cross-reference at docs/prd.md:153 describe ordering and route reachability, not a mitigation, so nothing in them asserts a protection the code does not implement.

**test-reviewer**

- Finding 1 (holder id tiebreak untested) is genuinely fixed: theSpecialtyDirectoryShouldBreakATieOnMatchingHolderNamesByIdentifier passes two vets with matching last+first name in reverse-id order; verified by mutation testing (removing .thenComparing(Vet::getId) from BY_LAST_NAME_THEN_FIRST_NAME_THEN_ID and rerunning) that this is the only test in the suite that fails against that regression -- the fix genuinely pins the third comparator level
- Finding 2 (framework test doing pure JVM work) is fixed: theSiteNavigationShouldCarryNoLinkToTheSpecialtyDirectory and its mentionsTheSpecialtyDirectoryAddress helper now live in SpecialtyDirectoryNavigationTests, a plain class with no Spring annotations and no @DisabledInNativeImage/@DisabledInAotMode gating -- it runs unconditionally rather than riding on the web-layer test's context skip conditions. The test still checks the same thing (grep every real template under src/main/resources/templates for the address literal) and the address/template-root literals are now named constants
- SpecialtyControllerTests.java's four now-unused imports (java.io.IOException, java.nio.file.Files, java.nio.file.Path, java.util.stream.Stream) are confirmed removed with no other references remaining; the class's remaining test (theSpecialtyDirectoryShouldCarryTheStandardSiteNavigation) is a distinct, still-Spring-appropriate check (the specialty page itself renders the navbar) and was left in place correctly
- Full test run (./gradlew test) is green: 0 failures, 0 skips, across SpecialtyDirectoryEntryTests (10), SpecialtyDirectoryNavigationTests (1), and SpecialtyControllerTests (9)
- Class sweep: no other pure-JVM-logic test remains riding inside a @WebMvcTest/@DataJpaTest class in the vet test package (grep for Files.walk/Files.readString across src/test/java/.../vet/ returns only the new plain class)

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $4.70 | 14m 33s | 96% |
| `agent-team:system-design-expert` | 3 | opus-5 | $2.74 | 7m 27s | 90% |
| `(parent)` | 1 | opus-5 | $2.38 | 45m 43s | 95% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $1.60 | 4m 22s | 90% |
| `agent-team:security-reviewer` | 2 | opus-5 | $1.37 | 3m 18s | 89% |
| `agent-team:change-grader` | 1 | opus-5 | $0.84 | 2m 24s | 90% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.78 | 4m 27s | 93% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.63 | 3m 19s | 91% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.35 | 1m 26s | 84% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.06 | 10s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.42 | 11m 8s | 97% |
| `(parent)` | opus-5 | $2.38 | 45m 43s | 95% |
| `agent-team:system-design-expert` | opus-5 | $1.23 | 3m 50s | 92% |
| `agent-team:product-requirements-expert` | opus-5 | $1.04 | 3m 17s | 91% |
| `agent-team:system-design-expert` | opus-5 | $0.96 | 2m 17s | 91% |
| `agent-team:change-grader` | opus-5 | $0.84 | 2m 24s | 90% |
| `agent-team:feature-implementer` | opus-5 | $0.82 | 2m 4s | 92% |
| `agent-team:security-reviewer` | opus-5 | $0.76 | 1m 52s | 89% |
| `agent-team:security-reviewer` | opus-5 | $0.61 | 1m 26s | 89% |
| `agent-team:product-requirements-expert` | opus-5 | $0.56 | 1m 4s | 89% |
| `agent-team:system-design-expert` | opus-5 | $0.55 | 1m 20s | 84% |
| `agent-team:test-reviewer` | sonnet-5 | $0.49 | 2m 38s | 93% |
| `agent-team:feature-implementer` | opus-5 | $0.46 | 1m 21s | 90% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.39 | 2m 21s | 92% |
| `agent-team:test-reviewer` | sonnet-5 | $0.29 | 1m 48s | 93% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.24 | 57s | 90% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.21 | 56s | 87% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.14 | 30s | 79% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.06 | 10s | 50% |

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

- plugin `agent-team-spring-boot` at `v0.2.0` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.247 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
