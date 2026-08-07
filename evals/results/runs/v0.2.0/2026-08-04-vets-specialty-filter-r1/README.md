# vets-specialty-filter r1 — v0.2.0

Filter the vet list by specialty (feature) · started 2026-08-04T13:12:50+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Feature request: filter the vet list by specialty. Two product decisions come
> with it, made here as the product owner:
> 
> - Non-goal NG-9 is narrowed: free-text veterinarian search stays out of
>   scope, but filtering the directory by an attribute it already shows is in.
>   Record the narrowing the way the project records non-goal changes.
> - The JSON endpoint at /vets is reinstated as a supported surface — this
>   filter is its first requested capability. Mint a fresh requirement for it;
>   the withdrawn REQ-VET-002 stays withdrawn and its id is not reused.
> 
> Both vet list surfaces accept an optional  specialty  query parameter:
> 
> - /vets.html?specialty=<name> — the HTML page shows only vets holding that
>   specialty; pagination applies to the filtered list.
> - /vets?specialty=<name> — the JSON endpoint returns only those vets.
> 
> Matching is on the whole specialty name, case-insensitive — not a prefix. A
> specialty matching no vet yields the normal page or JSON document with an
> empty vet list (HTTP 200). An empty or whitespace-only value behaves as if
> the parameter were absent, like the empty owner search. Without the parameter
> both endpoints behave as today. Cover the new behavior with tests.

## Verdict

| check | result |
|---|---|
| oracle | ✔ 5/5 passed |
| suite (post-agent) | ✔ |
| suite (pristine baseline) | ✔ |
| checkpoints | 8/8 |
| review attention (pipeline grade) | clear |

The pipeline grade estimates how much human review the change deserves before merge — advisory context from the harness's change grader (read from the ledger's `grader-verdict` record), never part of the bar.

- ✔ `theSpecialtyFilterShouldMatchCaseInsensitively` — passed
- ✔ `theSpecialtyFilterShouldNarrowTheHtmlVetList` — passed
- ✔ `theSpecialtyFilterShouldNarrowTheJsonVetList` — passed
- ✔ `theUnknownSpecialtyShouldYieldAnEmptyVetList` — passed
- ✔ `theVetListShouldShowTheFirstPageWithoutAFilter` — passed

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 4 (±0) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $1.03. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in the repository as derived queries (VetRepository findDistinctBySpecialties_NameIgnoreCase), keeping the controller thin, though narrowedTo() adds a blank-equals-absent rule to a controller the catalog already flags, and no ADR names that placement. Tests are behavior-named and constant-driven (SPECIALTY_HELD_BY_HELEN, SURNAMES_OF_THE_VETS_HOLDING_IT), but theVetListShouldPageOverTheFilteredVets hardcodes 6 and PageRequest.of(0,5) as mystery values, "   "/"" stay bare literals, and the '// one vet to a page' comment restates the assertion. The template repeats the same ternary five times — verbose, though the ADR acknowledges it. Documentation is thorough: NG-9 narrowed, REQ-VET-003/004 minted, REQ-VET-002 amended without reuse, contracts table, known-defect retirement, open question 5, and four indexed ADRs; no visible stale claim survives.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands at the right seam: derived repository finders ( findDistinctBySpecialties_NameIgnoreCase ) carry matching and case folding, the controller only binds and delegates, and the uncached-filtered-read choice is reasoned rather than copied. The blank-to-null  narrowedTo  helper is a small rule sitting in the controller, and the five-way ternary duplication in vetList.html is real verbosity the ADR itself calls unscalable. Tests are behavior-named and use meaningful constants (SPECIALTY_HELD_BY_TWO_VETS), but reach for Mockito stubs without the conscious-exception justification the policy asks for, carry narration comments ("one vet to a page..."), and leave bare literals ( PageRequest.of(0, 5) ,  6L ) undeclared. Documentation is thorough: NG-9 narrowed, REQ-VET-003/004 minted, superseded entry amended, defect row retired, contracts and open questions refreshed.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Derived-query keyword on VetRepository keeps case folding out of the schema and the unbounded  vets  cache off caller input — both catalog-consistent and ADR-recorded. Deduction: the blank-to-null rule lives as  narrowedTo()  private to VetController and is exercisable only through MockMvc, widening the pyramid gap the testing brief warns about; the five duplicated ternaries in vetList.html are admitted debt. Tests are strong specifications —  theSpecialtyFilterShouldNotMatchAPartialSpecialtyName , empty/blank/no-match/paging on both surfaces — but  PageRequest.of(0, 5), 6  with  totalItems 6L / totalPages 2  are mystery literals with underived expectations, and the  // one vet to a page  comment narrates code. Documentation is complete: NG-9 narrowed, REQ-VET-003/004 minted, REQ-VET-002 left withdrawn, defect row retired, contracts table current.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $20.37 | 58m | 48 | 92% | 12 file(s) +420/−32 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.20 | 3m 45s | 89% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-004 — Veterinarian directory can be narrowed to one specialty

3 review rounds · 2 build-passes · **2 build-failures** · grade **CLEAR**

| reviewer | R1 | R2 | R3 |
| --- | --- | --- | --- |
| **code-quality** | **✔** | **✔** | · |
| **test** | ✎ (3) | **✔** | · |
| **security** | **✔** | **✔** | · |
| **doc** | **✖** (1) | ✎ (1) | **✔** |

- ◇ **prd-entry** Veterinarian directory can be narrowed to one specialty · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 13m***
  - ▲ **build ✗ build failed** · retry 1
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 3m***
  - ▲ **build ✓ clean** · build · test · check · format · autofix-audit · handoff-log
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 2m***
- ✎ **review test** · **changes_requested** · (3 findings) · ***◷ 3m***
  - [autofix] `ClinicServiceTests.java:218-245` Naming inconsistency within the same slice: of the four new tests, two follow the BDD school (theSpecialtyFilterShouldIgnoreLetterCase, theSpecialtyFilterShouldNotMatchAPartialSpecialtyName) and two still use the pre-2026-07-31 should{Verb} form (shouldFindVetsHoldingASpecialty, shouldPageOverTheVetsHoldingASpecialty). testing-principles.md Test Naming states the the{Subject}Should{Outcome} school applies to tests written from 2026-07-31 onward - all four are new this slice, so they should be uniform.
    - fix: Rename shouldFindVetsHoldingASpecialty to theSpecialtyFilterShouldReturnOnlyVetsHoldingIt and shouldPageOverTheVetsHoldingASpecialty to theSpecialtyFilterShouldPageOverTheMatchingVets (or equivalent behavior-stated names).
  - [autofix] `VetControllerTests.java:92-93,117,125` The specialty name "radiology" (and its case-scrambled and near-miss variants "RaDiOlOgY", "radio", "radiologyy") is a Tier-1 meaningful value under the Three-Tier Data Naming Convention - it is exactly what drives each test's expected outcome - yet it appears as a bare repeated string literal across both files rather than a role-named constant (e.g. SPECIALTY_HELD_BY_MULTIPLE_VETS). Same class for the expected vet surnames "Leary"/"Stevens" repeated across three ClinicServiceTests methods.
    - fix: Introduce named constants (class-level, since the values are shared by multiple tests) for the specialty under test and the expected vet surnames, and reference them from every test method instead of the bare literals.
  - [autofix] `VetControllerTests.java:142-152,154-16` Three test methods bundle two independent Act+Assert pairs against two different inputs or two different endpoints in one method body: theSpecialtyFilterShouldNotMatchAPartialSpecialtyName exercises both a strict-prefix miss ("radio") and a superset miss ("radiologyy"); theBlankSpecialtyFilterShouldListEveryVet and theSpecialtyFilterShouldYieldAnEmptyDirectoryWhenNoVetHoldsIt each call mockMvc.perform twice, once per surface. This is the repetitive-case shape testing-principles.md's Parameterized Tests checklist item exists for, and violates the one-logical-assertion/one-concern-per-test structure rule - a failure in the first perform/call masks whether the second would also have failed.
    - fix: Convert the repository-level near-miss cases to a single @ParameterizedTest with @CsvSource (one row per PRD edge case 3 example, each row commented with the case it covers); split the two controller tests that bundle both HTML and JSON surfaces into one test per surface, matching this file's existing one-test-per-surface convention (showVetListHtml vs showResourcesVetList).
- ✖ **review doc** · **blocked** · (1 finding) · ***◷ 5m***
  - **[blocked]** `system-design.md:103-104` This diff edits both the VetRepository and VetController Contracts rows to add REQ-VET-003 to their Implements column, but leaves REQ-VET-004 out of both even though the same diff adds VetRepository.findDistinctBySpecialties_NameIgnoreCase(String) and its paged overload (src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java) and VetController.showVetList/showResourcesVetList now branch on an optional specialty parameter to call them (src/main/java/org/springframework/samples/petclinic/vet/VetController.java). The Contracts section states its own contract: 'Implements cites the requirements in docs/prd.md that the type serves' (system-design.md:74). A reader who greps the Contracts table for what implements REQ-VET-004 finds nothing, even though two of its rows now serve it. This is not a pre-existing gap the slice inherited — the rows were touched by this diff and REQ-VET-003 was added to them in the same edit, so REQ-VET-004 was omitted by choice, not oversight; the design-block record (line 9) confirms the omission and defers the fix to a future doc-sync pass. Fixing it now is a judgment call on wording, not a mechanical edit, so it is not autofix-eligible under review-checks.md's Autofix on Design-Doc Paths (coherence findings on design-doc paths are never autofix-eligible).
- ↻ **implement** (implementer) ← test · (3 findings)
- ↻ **fix design** ← doc · (1 finding)
- ◈ **design-block** **new** · (design) · supersedes L9 · ***◷ 2m***
- ▲ **build-pass** 14:04 · build, test, check, format, autofix-audit, handoff-log
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `system-design.md:104` The reworded VetController Purpose cell is 31 words in one semicolon-joined sentence, over the 30-word maximum (documentation-standards.md Writing Standards, and review-checks.md §4 'Sentences under 30 words'). It is new prose this pass, introduced by the correction at line 23 superseding line 9. A sweep of every Contracts-table Purpose cell for a word count over 30 found no other instance; the VetRepository cell's reworded Purpose (line 103, 21 words) is within bounds.
    - fix: Serves the paged HTML vet list and a serialized vet collection from a second route, either whole or narrowed to one specialty; a blank specialty counts as none
- ✚ **doc-autofix** `docs/system-design.md` · writing-standards · (root)
- ✔ **review doc** · **approved** · ***◷ 8s***
- ◆ **grade CLEAR** · narrow the vet directory by specialty
  - blast_radius — **clear** — Twelve files, but the executable reach is one feature package: two additive repository methods, an optional request parameter on the two VetController routes, and the vetList paging block. Seven of the twelve files are docs and ADRs, no sensitive path is touched, and the 46-hunk count is the zero-context convention over 96 production lines.
  - semantic_surprise — **clear** — Read every production hunk. The unnarrowed path is preserved by construction: a null, empty, or spaces-only specialty is normalized to null and routes through the original findAll calls, and the template ternary picks the plain URL. The one non-obvious detail, a Thymeleaf parser-level comment carrying the literal specialty parameter text, is stripped from the render, which the unfiltered paging-link assertion proves. The derived query binds the name as a parameter and case-folds in the query rather than in string manipulation.
  - test_adequacy — **clear** — Query semantics are proven against real H2 in ClinicServiceTests: whole-name match, scrambled case, prefix and superset near-misses, and a page-size-one paging test pinning totalElements and totalPages, which is the assertion that would catch paging over the unnarrowed list. The controller tests drive real MVC binding and Thymeleaf rendering, and each fails against a plausible break: dropping the strip normalization fails the spaces-alone test, dropping the parameter from links fails the paging-link test, emitting it unconditionally fails the unfiltered-link test.
  - reviewer_hedging — **clear** — The review plan dispatched the full four-reviewer roster at high risk over the full diff, and all four approved on the final pass with empty findings lists. The only carried item is code-quality's explicitly cosmetic recommendation about three assertions on one page object, restated to show it was seen again rather than as a reservation.
  - scope_deviation — **clear** — The diff matches the surfaces triaged in the PRD entry and the design block, ClinicServiceTests included by the superseding record. The two design revisions were process corrections, an undeclared docs/adr/README.md path and a wrong Thymeleaf assumption a test disproved, not scope drift. The unrelated owner-paging defect found on the way was recorded in Known Defects and deliberately left unfixed; no file outside the vet feature changed.
  - why — Read every production hunk: the narrowing is purely additive and the unnarrowed surface, its URLs included, is preserved and test-pinned. Confirm one product call at merge, that the /vets JSON route, previously documented as pending removal, is now a supported surface (REQ-VET-003) and gained the filter.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Injection: the specialty value reaches the database only through Spring Data derived queries (findDistinctBySpecialties_NameIgnoreCase, Collection and Page overloads). No string-concatenated SQL, no @Query, no EntityManager use is introduced; parameters are bound. Consistent with the system-design threat model's SQL-injection row.
- Reflected XSS: the caller-supplied specialty is placed in the model but never rendered as page text. Its only render site is the Thymeleaf link-expression parameter (@{/vets.html(page=..., specialty=${specialty})}), which URL-encodes the value, and the resulting th:href attribute is HTML-escaped by Thymeleaf's default output escaping (not disabled anywhere). A sweep of src/main/resources/templates for th:utext and for every 'specialty' occurrence in vets/vetList.html found no unescaped sink.
- Cache key space: ADR 2026-08-04-uncached-filtered-vet-reads holds in the code as built. A grep of src/main/java for @Cacheable confirms the annotation appears only on the two pre-existing unfiltered VetRepository.findAll methods; neither caller-string-keyed filtered read carries it, so the unbounded, unevicted 'vets' cache is not opened to attacker-chosen keys on this unauthenticated app.
- Conditional paging links: ADR 2026-08-04-filter-preserving-paging-links holds. All five link sites render the plain URL when the model attribute is null, so an unnarrowed list emits the pre-existing URLs and no empty specialty= parameter; regression test theUnfilteredVetListPagingLinksShouldCarryNoSpecialty asserts it.
- Input normalization: narrowedTo() treats absent, empty, and whitespace-only values as no filter and strips the value before it reaches the query, so no blank-string filter path exists. No new authorization, redirect, file-I/O, deserialization, or logging sink is introduced; the JSON route returns the same Vet shape as before, narrowed.
- Secrets: the diff introduces no credential, token, key, or connection-string literal. The only new strings are specialty names in tests and fixtures.
- Supply chain: no dependency delta. build.gradle, settings.gradle, and gradle/ are unmodified in the change set, so no new or upgraded coordinate enters the graph; the OWASP dependency-check plugin is not configured in this project, and the review adds no dependency requiring it.

**code-quality-reviewer**

- VetRepository's two new derived-query methods follow the existing Spring Data declarative style, use IgnoreCase/Distinct exactly as the design-block prescribes, and each carries javadoc explaining the deliberate absence of @Cacheable with a pointer to the backing ADR
- VetController.narrowedTo mirrors OwnerController's established blank-normalization idiom, keeps the branch out of the query layer, and is documented with a clear javadoc explaining the null-routing contract
- vetList.html's two-form paging-link selection is a direct, well-commented fix for the corrected Thymeleaf null-parameter behavior, confined to the paging block with no new message key or user-facing text
- Test names in VetControllerTests and ClinicServiceTests match the PRD's test_names list; edge cases 2 and 3 (case-fold, whole-name match) are proven against the real H2-backed repository rather than a Mockito stub, consistent with the minimal-mocking policy
- ./gradlew checkFormat passes clean; no formatting issues in the diff
- No naming, package-structure, logging, or error-handling issues found in the changed production files

**test-reviewer**

- Edge-case placement matches the design-block ruling: case-folding and whole-name-only matching are proven against real H2 I/O in ClinicServiceTests, not against a MockitoBean stub that would only assert its own argument matcher
- All five prd.md REQ-VET-004 edge cases have coverage: stable specialty order (pre-existing shouldFindVets), case-fold (theSpecialtyFilterShouldIgnoreLetterCase), whole-name-only match (theSpecialtyFilterShouldNotMatchAPartialSpecialtyName), no-match-returns-empty-not-error (theSpecialtyFilterShouldYieldAnEmptyDirectoryWhenNoVetHoldsIt, asserting 200/normal view rather than an error page), and blank/absent-as-none (theBlankSpecialtyFilterShouldListEveryVet)
- Both public surfaces (HTML and JSON) and both paging-link states (narrowed vs unnarrowed) are exercised at the controller layer with MockMvc, the project's one sanctioned mock boundary
- AssertJ fluent assertions used throughout the new tests (extracting/containsExactlyInAnyOrder, isEmpty); no JUnit assertEquals/assertTrue introduced
- ./gradlew test passes for both changed test classes; build-pass gate record confirms full gate (build, test, check, format, autofix-audit, handoff-log) is green

**doc-reviewer**

- docs/prd.md: REQ-VET-003 and REQ-VET-004 carry anchors at first mention, Done-when bullets, and edge cases matching the acceptance criteria; NG-9 narrowing and the REQ-VET-002/REQ-VET-003 Superseded amendment read coherently and preserve the withdrawn id
- All four new ADRs follow the template (Status, Context, Options Considered, Decision, Consequences, Implementation with Requirements/Non-goal, References), stay under the length guideline, and every 2026-08-04 index row in docs/adr/README.md resolves to its file
- docs/system-design.md Persistence and the new Presentation subsection state each rule once with an ADR back-link, matching the implemented behavior in VetRepository, VetController, and vetList.html
- The new Known Defects row (owner paging widening past page 1) and the Known Defects preamble edit are corroborated by src/main/resources/templates/owners/ownersList.html and OwnerController.processFindForm, and the retired machine-readable-route row is removed consistently with REQ-VET-003
- All cross-document links introduced in this diff (prd.md#req-vet-004, prd.md#non-goals, system-design.md#persistence/#presentation/#known-defects) resolve to real anchors/headings, and specialty/veterinarian terminology matches docs/ubiquitous-language.md

**code-quality-reviewer**

- ClinicServiceTests and VetControllerTests test-only changes this round: renamed tests now follow the{Subject}Should{Outcome}; new class-level constants (SPECIALTY_HELD_BY_TWO_VETS, SPECIALTY_HELD_BY_TWO_VETS_IN_SCRAMBLED_CASE, SURNAMES_OF_THE_VETS_HOLDING_IT, VETS_IN_THE_DIRECTORY, VETS_HOLDING_HELENS_SPECIALTY, SPECIALTY_HELD_BY_HELEN, SPECIALTY_HELD_BY_NO_VET, SPECIALTY_SPANNING_TWO_PAGES) replace the Tier-1 literals they were flagged for and are used consistently at every call site, including the helen().getId() swap for bare vet ids
- theSpecialtyFilterShouldNotMatchAPartialSpecialtyName's @ParameterizedTest + @CsvSource conversion keeps a one-line comment per row explaining what each near-miss value tests (strict prefix, strict superset), matching the file's existing comment style
- The one-test-per-surface split (HTML vs JSON pairs for the spaces/empty-specialty and no-vet-holds-it cases) leaves each test naming exactly one behavior and one response surface, consistent with the rest of the file
- ./gradlew checkFormat passes clean; import blocks in both files stay alphabetically ordered after the new imports (List, ParameterizedTest, CsvSource, PageRequest, additional hamcrest/mockito static imports)
- docs/system-design.md Contracts rows for VetRepository and VetController now cite REQ-VET-004 with Purpose cells describing the narrowing; no production code changed this round to review against them

**test-reviewer**

- All three pass-1 findings verified fixed: the four new ClinicServiceTests methods now use a single uniform the{Subject}Should{Outcome} naming school (theSpecialtyFilterShouldReturnOnlyVetsHoldingIt, theSpecialtyFilterShouldPageOverTheMatchingVets, theSpecialtyFilterShouldIgnoreLetterCase, theSpecialtyFilterShouldNotMatchAPartialSpecialtyName)
- Tier-1 constants introduced and referenced consistently: ClinicServiceTests (SPECIALTY_HELD_BY_TWO_VETS, SPECIALTY_HELD_BY_TWO_VETS_IN_SCRAMBLED_CASE, SURNAMES_OF_THE_VETS_HOLDING_IT) and VetControllerTests (SPECIALTY_HELD_BY_HELEN, SPECIALTY_HELD_BY_NO_VET, SPECIALTY_SPANNING_TWO_PAGES, VETS_IN_THE_DIRECTORY, VETS_HOLDING_HELENS_SPECIALTY); no bare repeated literals remain for the specialty name or expected surnames in the new tests
- Repository near-miss test converted to @ParameterizedTest with @CsvSource, one commented row per prd.md edge case 3 example (opening-letters prefix miss and trailing-letter superset miss), both rows asserting the same isEmpty() outcome
- The two bundled controller tests split one-per-surface (theVetListShouldShowEveryVetWhenTheSpecialtyIsSpacesAlone / theVetJsonShouldCarryEveryVetWhenTheSpecialtyIsEmpty and theVetListShouldBeEmptyWhenNoVetHoldsTheSpecialty / theVetJsonShouldBeEmptyWhenNoVetHoldsTheSpecialty), matching the file's pre-existing one-test-per-surface convention (showVetListHtml vs showResourcesVetList)
- Both PRD edge-case-5 blank-value variants (spaces-alone and empty-string) remain independently exercised after the split -  spaces-alone against the HTML surface, empty-string against the JSON surface - broadening rather than narrowing input diversity versus the prior bundled test, which drove one blank value through both surfaces in a single method
- All five prd.md REQ-VET-004 edge cases still proven; no coverage regression from the restructuring
- ./gradlew test passes for both changed test classes with no failures; fresh build-pass (line 24) confirms the full gate is green

**security-reviewer**

- Re-verified against the pass-1 approval (line 17): no production Java, template, or build file changed this round. git diff over src/main/java and src/main/resources/templates is byte-identical to the surface approved in pass 1; the only code-side delta is in the two test files, and docs/system-design.md.
- Uncached filtered reads still hold: VetRepository.findDistinctBySpecialties_NameIgnoreCase(String) and its paged overload carry @Transactional(readOnly = true) and no @Cacheable. Only findAll()/findAll(Pageable) remain @Cacheable("vets"), so no caller-supplied string ever becomes a key in the unbounded, unevicted vets cache on this unauthenticated app.
- Reflected specialty still escaped: vetList.html renders the value only inside Thymeleaf link expressions (@{/vets.html(page=..., specialty=${specialty})}) in th:href attributes, which URL-encode the parameter and HTML-escape the attribute. Swept the whole templates tree for unescaped output — no th:utext occurs anywhere, and specialty is never emitted as page text via [[...]]. The null-vs-blank branch (th:with narrowed) selects the plain URL when nothing is narrowed, so no attacker-supplied value reaches the unnarrowed link form either.
- Injection: the filter reaches the database through a Spring Data derived query method, which binds the name as a JPA parameter. No JPQL/SQL string is built from the request; case folding is done by the query (IgnoreCase), not by string manipulation. VetController.narrowedTo only strips and null-checks, adding no unsafe transformation.
- Doc change is contract-only and now matches the code: the system-design Contracts rows cite REQ-VET-004 and the VetRepository row states "only the unfiltered results are cached", which is the property verified in the source. The Persistence and Presentation rules and their ADR back-links state the two security-relevant decisions once each, consistent with the implementation.
- Tests introduce no security surface: no hardcoded credentials or secrets (swept the test diff for password/secret/token/api-key/credential/private-key patterns — no hits), no new I/O, no disabled escaping. The new assertions exercise the specialty parameter through MockMvc only.
- Supply chain unchanged: no build.gradle, pom, or dependency-declaring file appears in the change set, so the dependency graph verified in pass 1 is untouched and no new CVE surface was introduced.

**doc-reviewer**

- The critical finding from the prior pass (line 20: VetRepository and VetController Contracts rows omitting REQ-VET-004) is resolved. Both rows now cite REQ-VET-001, REQ-VET-003, REQ-VET-004, matching the derived-query methods and the optional-parameter branching the diff adds to each type.
- The reworded Purpose cells state the narrowing behaviorally (matched whole and case-insensitively; blank counts as none) rather than citing REQ-VET-004 as a bare id, so the citation is legible against the Contracts section's own stated contract at system-design.md:74.
- The deliberate boundary of not widening Vet, Specialty, or Vets is correct: none of the three types' guarantees changed under this diff (Vet still exposes specialties sorted by name; Specialty is still a plain lookup value; Vets is still a root-element wrapper reused as-is), and the two rows that do carry the new behavior are the ones a reader greps for REQ-VET-004.
- All four new 2026-08-04 ADRs follow the template (Status, Context, Options Considered, Decision, Consequences, Implementation with Requirements or Non-goal, References) and are indexed correctly in docs/adr/README.md.
- Every cross-reference touched or introduced by this pass's correction resolves: system-design.md#contracts, the four ADR back-links, and prd.md#req-vet-004 all point at real headings or anchors.
- No PRD-boundary violation, no mechanism leak into the PRD, and no field/parameter table introduced in system-design.md by this correction.

**doc-reviewer**

- docs/system-design.md:104 (VetController Contracts Purpose cell): the root-applied autofix at line 34 matches the fix proposed in the pass-2 finding (line 33) verbatim, byte-for-byte against the string on disk.
- git diff against the pass-2 review-plan basis tree (5a1733bddf23d5789c26d8859b6c0d591712b379) for docs/system-design.md shows exactly one changed line: the VetController row. The path column and the REQ-ID column (REQ-VET-001, REQ-VET-003, REQ-VET-004) are byte-identical before and after; only the Purpose cell text changed, staying within the § Root-Applied Autofix on Doc Paths bounds (one Edit, one line, Purpose cell only).
- The new Purpose cell reads 28 words in one semicolon-joined sentence, under the 30-word maximum that triggered the pass-2 finding; no new writing-standards violation introduced by the substitution.
- No other file in the changeset differs from the pass-2 basis: the fix did not touch any surface the other three floor reviewers (code-quality-reviewer, test-reviewer, security-reviewer) already hold approved against, so their pass-2 approvals stand undisturbed.
- audit-autofix (1 record validated, 6 dirty design-doc paths covered) and validate (34 records valid at time of audit) both confirm the log-side bookkeeping for the autofix record is sound.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $10.31 | 23m 30s | 95% |
| `agent-team:system-design-expert` | 3 | opus-5 | $7.10 | 12m 6s | 93% |
| `(parent)` | 1 | opus-5 | $6.70 | 62m 8s | 96% |
| `agent-team:doc-reviewer` | 3 | sonnet-5 | $3.03 | 9m 19s | 91% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $2.30 | 3m 50s | 90% |
| `agent-team:change-grader` | 1 | opus-5 | $2.20 | 3m 45s | 89% |
| `agent-team:security-reviewer` | 2 | opus-5 | $2.03 | 2m 38s | 82% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $1.66 | 3m 23s | 86% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.58 | 5m 27s | 86% |
| `agent-team:pipeline-coordinator` | 2 | sonnet-5 | $0.25 | 22s | 20% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $6.70 | 62m 8s | 96% |
| `agent-team:feature-implementer` | opus-5 | $5.96 | 13m 46s | 97% |
| `agent-team:feature-implementer` | opus-5 | $3.03 | 6m 1s | 94% |
| `agent-team:system-design-expert` | opus-5 | $2.50 | 5m 15s | 93% |
| `agent-team:system-design-expert` | opus-5 | $2.49 | 4m 14s | 94% |
| `agent-team:product-requirements-expert` | opus-5 | $2.30 | 3m 50s | 90% |
| `agent-team:change-grader` | opus-5 | $2.20 | 3m 45s | 89% |
| `agent-team:system-design-expert` | opus-5 | $2.12 | 2m 36s | 91% |
| `agent-team:doc-reviewer` | sonnet-5 | $1.44 | 5m 32s | 93% |
| `agent-team:feature-implementer` | opus-5 | $1.32 | 3m 42s | 91% |
| `agent-team:security-reviewer` | opus-5 | $1.15 | 1m 21s | 86% |
| `agent-team:doc-reviewer` | sonnet-5 | $1.10 | 2m 32s | 90% |
| `agent-team:test-reviewer` | sonnet-5 | $0.95 | 3m 51s | 88% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.93 | 2m 9s | 88% |
| `agent-team:security-reviewer` | opus-5 | $0.88 | 1m 16s | 75% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.74 | 1m 14s | 83% |
| `agent-team:test-reviewer` | sonnet-5 | $0.63 | 1m 36s | 83% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.49 | 1m 14s | 88% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.13 | 14s | 33% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.12 | 7s | 0% |

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
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `610c2c59194e4044` · `2.1.220 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
