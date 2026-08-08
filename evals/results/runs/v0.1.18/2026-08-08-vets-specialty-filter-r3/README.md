# vets-specialty-filter r3 — v0.1.18

Filter the vet list by specialty (feature) · started 2026-08-07T23:24:35+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Feature request: filter the vet list by specialty. Three product decisions
> come with it, made here as the product owner:
> 
> - Non-goal NG-9 is narrowed: free-text veterinarian search stays out of
>   scope, but filtering the directory by an attribute it already shows is in.
>   Record the narrowing the way the project records non-goal changes.
> - The JSON endpoint at /vets is reinstated as a supported surface — this
>   filter is its first requested capability. Mint a fresh requirement for it;
>   the withdrawn REQ-VET-002 stays withdrawn and its id is not reused.
> - The filter is a URL contract only. Neither surface gains a form, dropdown,
>   or other page control in this request; pagination links carry the
>   parameter so filtered pages stay navigable. A visible control may come as
>   a follow-up request.
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
> 
> These are all the product decisions; no further product answer will come
> during the work. Where a choice still seems open, take the narrowest reading
> consistent with this request and record the open question rather than
> waiting.

## Verdict

| check | result |
|---|---|
| oracle | ✔ 5/5 passed |
| suite (post-agent) | ✔ |
| suite (pristine baseline) | ✔ |
| checkpoints | 8/8 |
| review attention (pipeline grade) | — |

- ✔ `theSpecialtyFilterShouldMatchCaseInsensitively` — passed
- ✔ `theSpecialtyFilterShouldNarrowTheHtmlVetList` — passed
- ✔ `theSpecialtyFilterShouldNarrowTheJsonVetList` — passed
- ✔ `theUnknownSpecialtyShouldYieldAnEmptyVetList` — passed
- ✔ `theVetListShouldShowTheFirstPageWithoutAFilter` — passed

## Checkpoints

The kind's graded ladder, derived from the recorded facts — context only, outside the quality bar (bench README § Checkpoints).

- ✔ `agent complete`
- ✔ `change produced`
- ✔ `suite green`
- ✔ `theSpecialtyFilterShouldMatchCaseInsensitively`
- ✔ `theSpecialtyFilterShouldNarrowTheHtmlVetList`
- ✔ `theSpecialtyFilterShouldNarrowTheJsonVetList`
- ✔ `theUnknownSpecialtyShouldYieldAnEmptyVetList`
- ✔ `theVetListShouldShowTheFirstPageWithoutAFilter`

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 4 (±0) | 4 (±1) | 4 (±0) | 4 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.59. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 4

> The match rule lives on the aggregate (Vet.hasSpecialty), so both surfaces share one definition and no business rule lands in the controller; the in-memory paging (findPaginated's subList/PageImpl block) is orchestration debt the ADR names and accepts. Tests are BDD-named and the predicate is unit-tested in VetTests, but three-tier data naming is ignored: bare "radiology", "   ", setId(100 + i), setId(1) are mystery values, and theFilteredBrowserPaginationShouldKeepTheSpecialtyAcrossPages asserts model attributes twice rather than that the rendered pagination links carry specialty — the behavior its name and REQ-VET-003 claim. Docs are thorough (NG-9 narrowing, REQ-VET-003, superseded note, open question, two ADRs), but system-design's Vets row still implements "—" though /vets is now a supported surface.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> Matching lives on the aggregate ( Vet.hasSpecialty , whole-name/ignore-case), so no business rule lands in the controller, and both ADRs plus the contracts-table rows justify skipping a repository query; the cost is manual  PageImpl / subList  paging assembly inside  VetController.findPaginated , orchestration a controller should not really own. Tests follow the BDD naming school and route construction through  radiologistsOf / vetWithSpecialty  factories, but carry mystery literals ( setId(100 + i) ,  radiology.setId(1) ) and undreived expectations —  radiologistsOf(7)  against  hasSize(5) / totalPages 2  hides the page size — and  theFilteredBrowserPaginationShouldKeepTheSpecialtyAcrossPages  runs two act/assert cycles. Docs are thorough (NG-9 narrowing, REQ-VET-003, defect row removed, open question), but the  Vets  contract row still reads  — , now stale under REQ-VET-003.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> Matching lives on the aggregate ( Vet.hasSpecialty , Vet.java:76) so both surfaces share one definition and no business rule lands in the controller; the Repository departure is recorded in a proper ADR. Cost:  VetController.findPaginated  now hand-assembles pages via  subList / PageImpl , orchestration a service would carry better. Test names follow  the{Subject}Should{Outcome}  and construction sits behind  radiologistsOf / vetWithSpecialty , but data naming regresses:  hasSize(1) ,  .value(2) ,  radiologistsOf(7)  with the hidden pageSize 5 are Tier-3 literals, expectations are not derived, and the pagination test performs two Act phases while asserting model attributes rather than the changed template links. Docs are thorough (NG-9 narrowing, REQ-VET-003, defect row removed, open question), but the  Vets  contract row still implements "—".

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $14.65 | 48m | 39 | 87% | 10 file(s) +316/−23 |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Filter the veterinarian directory by specialty on both surfaces

3 review rounds · 2 build-passes · no grade yet

| reviewer | R1 | R2 | R3 |
| --- | --- | --- | --- |
| **code-quality** | ✎ (1) | **✔** | · |
| **test** | ✎ (5) | **✔** | · |
| **security** | **✔** | **✔** | · |
| **doc** | ✎ (1) | **✖** (1) | **✔** |

- ◇ **prd-entry** Filter the veterinarian directory by specialty on both surfaces · (prd-expert) · ***◷ 5m***
- ◈ **design-block** **new** · (design) · ***◷ 0s***
- ◆ **implement** (implementer) · ***◷ 5m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- ✔ **review security** · **approved** · ***◷ 15m***
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 5m***
  - [autofix] `VetController.java:103-105` filterBySpecialty calls vetRepository.findAll() (the full-collection, cache-backed variant) rather than a specialty-parameterized repository query. This is the correct and intentional design — the EAGER @ManyToMany means a DB-paged join would trigger Hibernate in-memory pagination — but there is no why-comment at the call site. A future reader with no ADR context will treat this as an oversight and refactor it to a @Query method, reintroducing the HHH90003004 warning. The ADR at docs/adr/2026-08-07-vet-directory-filter-in-memory.md records the rationale; the code should point to it.
    - fix: Add a single-line comment above the findAll() call inside filterBySpecialty: '// Full-collection fetch: cached by VetRepository; see docs/adr/2026-08-07-vet-directory-filter-in-memory.md for why a DB query is not used here.'
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 1h 30m***
  - **[blocked]** `system-design.md:110` The 'Veterinarian directory filtering' paragraph names the `specialty` request parameter and the `findAll` repository method in prose. Per the system-design abstraction rules, parameter and method names must not appear in the document — in a table or in prose — because a rename silently invalidates the claim without any compile-time signal. The Contracts table row for VetController (line 104) already states the behavior correctly without the parameter name: 'both surfaces accept an optional specialty filter'. The paragraph should describe the realization in terms of types and behaviors already named in the Contracts table, replacing '`specialty` request parameter' with 'a specialty filter query parameter' and 'reads its cached `findAll`' with 'reads the cached vet collection', so no internal identifier appears that could rot on rename.
- ✎ **review test** · **changes_requested** · (5 findings) · ***◷ 4m***
  - **[blocked]** `VetControllerTests.java` The PRD acceptance criterion 'given a specialty that no veterinarian holds, when either surface is filtered by it, then that surface returns successfully with an empty veterinarian list' covers both surfaces. unknownSpecialtyShouldReturnEmptyDirectoryWithSuccess tests only the HTML surface (GET /vets.html?specialty=nutrition). No test covers GET /vets?specialty=\<unknown> returning HTTP 200 with an empty vetList on the JSON surface. A defect on the JSON empty-list path would be undetected.
  - **[blocked]** `VetControllerTests.java` The PRD acceptance criterion 'given a filter value that is empty or only spaces, when either surface is filtered by it, then the surface behaves as though no filter were given' covers both surfaces. blankSpecialtyValueShouldBehaveAsNoFilter tests only the HTML surface (GET /vets.html with param specialty='   '). No test covers GET /vets with a blank specialty parameter on the JSON surface.
  - [autofix] `VetControllerTests.java:149-173` filteredBrowserPaginationShouldKeepTheSpecialtyAcrossPages contains a for-loop constructing 7 radiologist vets. The testing brief requires test bodies to be straight-line code with no loops. Extract the list construction to a factory method such as radiologistsOf(int count) in the test class body, then call it from the test.
    - fix: Extract the for-loop into a private List\<Vet> radiologistsOf(int count) factory method and replace the loop with a single radiologistsOf(7) call.
  - [autofix] `VetTests.java:50-55` specialtyFilterShouldMatchWholeNameCaseInsensitively repeats three identical assertThat(vet.hasSpecialty(...)).isTrue() calls for 'radiology', 'Radiology', and 'RADIOLOGY'. The testing brief requires @ParameterizedTest with @CsvSource for repetitive test cases. Converting this removes the duplication and makes it trivial to add further case variants.
    - fix: Convert to @ParameterizedTest @MethodSource (or @CsvSource) supplying ["radiology", "Radiology", "RADIOLOGY"] as inputs, with a single assertThat(vet.hasSpecialty(input)).isTrue() assertion.
  - [clarify] `handoff.jsonl line 2` All 8 test names declared in the prd-entry test_names field follow the pattern {Subject}Should{Outcome} but omit the 'the' prefix required by the brief's naming school (the{Subject}Should{Outcome}). The implementer used the exact declared names, so this is a defect in the prd-entry. Future prd-entry records should declare test names with the 'the' prefix, e.g. theHtmlDirectoryShouldListOnlyVetsHoldingTheFilteredSpecialty. Whether the current test method names should be renamed (decoupling from the prd-entry's declared names) needs a decision from the product-requirements-expert.
- ↻ **fix prd-expert** ← test · (5 findings)
- ↻ **fix design** ← doc · (1 finding)
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 44s***
- ↲ consult **prd-expert** → **?** · Decision: rename all 8 test methods on this slice to add the 'the' prefix. Verified: docs/testing-principles.md line 86 defines the naming school as 'the{Subject}Should{Outcome}' (prefix is load-bearing, per the theOwnerSearchShouldMatchOnLastNamePrefix example); line 96 scopes the school to tests written or modified from 2026-07-31 onward, so these new tests (written this slice) are bound by it; scripts/layout.toml test_name_pattern '^[a-z][A-Za-z0-9_]*$' is only the looser machine floor (line 88) and does not enforce the prefix. The declared names omit it, so the prd-entry (line 2) was defective and the implementer correctly used the declared names. Rename is a pure identifier change, no behavior change, in scope for the slice that created these tests. Exact final names: (1) VetControllerTests: htmlDirectoryShouldListOnlyVetsHoldingTheFilteredSpecialty -> theHtmlDirectoryShouldListOnlyVetsHoldingTheFilteredSpecialty; (2) VetControllerTests: jsonDirectoryShouldReturnOnlyVetsHoldingTheFilteredSpecialty -> theJsonDirectoryShouldReturnOnlyVetsHoldingTheFilteredSpecialty; (3) VetTests: specialtyFilterShouldMatchWholeNameCaseInsensitively -> theSpecialtyFilterShouldMatchWholeNameCaseInsensitively (keep this exact name when converting it to @ParameterizedTest per the separate autofix finding — parameterized tests keep one method name, testing-principles line 94); (4) VetTests: prefixSpecialtyValueShouldNotMatchAnyVet -> thePrefixSpecialtyValueShouldNotMatchAnyVet; (5) VetControllerTests: unknownSpecialtyShouldReturnEmptyDirectoryWithSuccess -> theUnknownSpecialtyShouldReturnEmptyDirectoryWithSuccess; (6) VetControllerTests: blankSpecialtyValueShouldBehaveAsNoFilter -> theBlankSpecialtyValueShouldBehaveAsNoFilter; (7) VetControllerTests: filteredBrowserPaginationShouldKeepTheSpecialtyAcrossPages -> theFilteredBrowserPaginationShouldKeepTheSpecialtyAcrossPages; (8) VetControllerTests: absentSpecialtyShouldListDirectoryAsToday -> theAbsentSpecialtyShouldListDirectoryAsToday. Scope limit: rename only these 8, prefix-only, change nothing else; do not touch the pre-existing suite (line 96 exempts it). The feature-implementer owns the test files and applies the renames. Going forward I will declare prd-entry test_names with the 'the' prefix; I am not superseding the line-2 prd-entry, since this response is the authoritative correction and a re-issue would risk re-triggering upstream stages.
- ↻ **implement** (implementer) ← test · (5 findings) · ***◷ 15m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- ✔ **review security** · **approved** · ***◷ 30m***
- ✖ **review doc** · **blocked** · (1 finding) · ***◷ 1m***
  - [truncation] `2026-08-07-vet-directory-filter-in-mem` Reviewer reached planned checkpoint after reviewing docs/prd.md and docs/system-design.md. The two new ADRs and docs/adr/README.md have not yet been reviewed. Findings above cover prd.md and system-design.md only.
- ✔ **review code-quality** · **approved** · ***◷ 12h 30m***
- ✔ **review test** · **approved** · ***◷ 24h 5m***
- ↻ **fix doc** ← doc · (1 finding)
- ✔ **review doc** · **approved** · ***◷ 2m***

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Reflected specialty parameter flows only into Thymeleaf @{...} link expressions, which URL-encode query values and HTML-escape attribute output; no th:text reflection of the value, so no reflected XSS.
- Filtering is in-memory via Java equalsIgnoreCase over the cached collection with no query built from the parameter, so no SQL/injection sink.
- JSON /vets surface does not echo the parameter into the response body; only matching Vet objects are serialized by Jackson, and the endpoint exposes only already-public directory data.
- Untrusted input is normalized to null at the controller boundary before use.

**code-quality-reviewer**

- Vet.hasSpecialty Javadoc accurately describes the whole-name, case-insensitive contract and is precise about what does not match (prefix-only values)
- hasSpecialty uses getSpecialtiesInternal() rather than getSpecialties() — avoids creating a sorted defensive copy for a read that does not require order
- normalizeSpecialty is a focused, well-commented private method that mirrors the OwnerController blank-is-no-filter precedent and uses isBlank() for Unicode-correct whitespace handling
- findPaginated cleanly separates the two branches: DB-paged findAll(pageable) when unfiltered, in-memory PageImpl when filtered; the subList boundary guard (start >= filtered.size()) is correct
- All five pagination link templates (numbered, first, prev, next, last) carry specialty=${specialty}, satisfying the filter-persistence acceptance criterion
- No business rule logic was introduced into VetController — the case-insensitive match lives on the Vet aggregate where it belongs

**doc-reviewer**

- REQ-VET-002 stays withdrawn and its id is correctly marked retired and not reused — the Superseded entry is clear, distinct from REQ-VET-003, and the route's change of status is explained without implying a revival of the id
- NG-9 narrowing is recorded through the project's non-goal ADR convention: filename carries the non-goal- infix, Implementation section uses **Non-goal: NG-9**, and the PRD Non-Goals cell links to the ADR
- No document still asserts the machine-readable /vets route is unsupported or pending removal — the Known Defect row is gone, the Superseded entry is updated, and both the PRD narrative and the VetController Contracts row reflect the route as a supported surface under REQ-VET-003
- Both new ADRs have all required sections (Status, Context, Options Considered, Decision, Consequences, Implementation, References) and the Implementation section uses the correct tag for their type
- ADR README index carries rows for both new ADRs in the correct date order and consistent with the existing row format
- REQ-VET-003 anchor is present in prd.md; all Done-when bullets carry the REQ-VET-003 tag; the Open Question on whitespace trimming is correctly scoped and deferred
- PRD prose is behavioral throughout — no request parameter names, no method names, no mechanism constructs appear in any of the changed PRD sections
- Contracts table correctly adds REQ-VET-003 to both the Vet and VetController rows; VetRepository correctly retains only REQ-VET-001, matching the design decision that the repository is unchanged

**test-reviewer**

- VetTests.java vetWithSpecialty() factory method correctly wraps Vet and Specialty construction — test bodies call no production constructors directly
- AssertJ fluent assertions used throughout VetTests.java unit tests
- MockMvc is the only new mock introduced; @MockitoBean VetRepository is pre-existing tolerated infrastructure for the @WebMvcTest slice — no new internal code is mocked
- blankSpecialtyValueShouldBehaveAsNoFilter correctly uses .param('specialty', '   ') rather than URL-encoded whitespace in the path string; MockMvc's param() API delivers the literal whitespace value to Spring MVC binding, exercising the real @RequestParam blank-check path the product owner's rule depends on
- Both HTML and JSON surfaces have dedicated tests for the positive filter case (htmlDirectoryShouldListOnlyVetsHoldingTheFilteredSpecialty, jsonDirectoryShouldReturnOnlyVetsHoldingTheFilteredSpecialty)
- Case-insensitive matching and prefix non-matching are tested at the domain predicate level (VetTests.java) where the rule lives; the controller tests confirm the predicate is wired — this decomposition is sound
- filteredBrowserPaginationShouldKeepTheSpecialtyAcrossPages verifies both page 1 (totalPages=2, hasSize(5)) and page 2 (currentPage=2, hasSize(2)) and that specialty travels with both — the multi-perform structure is justified by the single pagination-continuity behavior being proven
- All 8 prd-entry test_names are present and accounted for in the implemented test files

**security-reviewer**

- Delta since prior approval (line 11) is non-functional: an ADR-referencing why-comment above the cached findAll() call in filterBySpecialty, plus test-only and doc-only changes — no security-relevant logic changed
- specialty @RequestParam is normalized (null/blank->null) and used only for in-memory stream filtering via vet.hasSpecialty(specialty), a plain string comparison — no SQL/query construction, so no injection surface
- Reflected value model.addAttribute('specialty', filter) reaches the template only through Thymeleaf URL link expressions @{/vets.html(page=...,specialty=${specialty})}, which URL-encode query-parameter values; no th:utext/unescaped sink — reflected XSS mitigated
- Pagination subList bounds are guarded (Math.min, start>=size -> empty content) — no out-of-bounds exposure
- No secrets, deserialization, authentication/authorization, or file/network trust-boundary changes introduced by this slice

**doc-reviewer**

- NG-9 narrowing follows project convention: annotated with date, references REQ-VET-003, carries ADR link
- REQ-VET-002 stays withdrawn in Superseded list with ID explicitly retired and not reused; the route is re-characterized as supported under REQ-VET-003, not pending removal
- REQ-VET-001 and REQ-VET-003 both carry HTML anchors; no anchor for the withdrawn REQ-VET-002
- REQ-VET-003 prose uses behavioral language throughout — no internal code references
- Design and ADR links present on the Veterinarian directory section
- system-design.md paragraph 110: all four reported changes confirmed applied
- Remaining type names (Vet, VetController, VetRepository) in paragraph 110 are Contracts-table rows — legitimate cross-references
- REQ-VET-002 absent from all Contracts-table Implements cells

**code-quality-reviewer**

- ADR-referencing why-comment on filterBySpecialty resolves prior changes_requested finding; the comment correctly names the caching rationale without over-explaining
- checkFormat passes clean — the long comment line wrapping is accepted by spring-javaformat
- All 8 test renames apply the the{Subject}Should{Outcome} school exactly as directed by the consultation-response at line 18
- radiologistsOf(int) factory eliminates the repeated inline vet-construction from the pagination test and introduces meaningful field values (100+i IDs, Vet+i first names)
- @ParameterizedTest @CsvSource conversion in VetTests covers lower/title/upper case variants under a single method name, matching testing-principles line 94 guidance on parameterized test naming
- hasSpecialty Javadoc accurately captures the whole-name, case-insensitive contract and the non-matching prefix behaviour — no implementation detail leaks
- normalizeSpecialty Javadoc is accurate; the null-return convention is local to the controller and the two call sites are adjacent, so null as sentinel is legible without further ceremony
- Stream + anyMatch in hasSpecialty and toList() in filterBySpecialty follow the checklist's modern-Java-idioms item
- Four-phase test structure is maintained across all new tests; blank lines separate phases without phase comments

**test-reviewer**

- All four prior findings resolved correctly: theUnknownSpecialtyShouldReturnEmptyJsonDirectoryWithSuccess covers GET /vets?specialty=nutrition → 200 JSON empty vetList; theBlankSpecialtyValueShouldBehaveAsNoFilterOnJsonDirectory covers GET /vets with blank specialty → 200 JSON full vetList; radiologistsOf(int count) factory removes the for-loop from the pagination test body; @ParameterizedTest @CsvSource converts the three-variant case-insensitivity assertion to a single parameterized method
- All 10 new or modified test methods carry the the{Subject}Should{Outcome} prefix per testing-principles.md line 86; pre-existing showVetListHtml and showResourcesVetList are correctly left untouched per the line-96 scope limit
- Every PRD Done-when bullet for REQ-VET-003 has at least one dedicated test; both surfaces (HTML and JSON) are covered for the unknown-specialty and blank-value edge cases that were previously missing
- No loops remain in test bodies; factory methods (james(), helen(), radiologistsOf(count), vetWithSpecialty()) wrap all production construction; no production constructors called directly in test bodies
- @MockitoBean VetRepository is the pre-existing tolerated boundary stub for the @WebMvcTest slice; no new internal code is mocked
- AssertJ and MockMvc result matchers used throughout; no raw JUnit assertEquals or assertTrue
- Tests are independent, straight-line, and free of phase comments or narration
- BUILD SUCCESSFUL with jacocoTestReport; zero test failures

**doc-reviewer**

- docs/prd.md: NG-9 narrowing annotated with date and ADR link; REQ-VET-002 stays in Superseded list with ID retired and not reused; REQ-VET-001 and REQ-VET-003 carry HTML anchors; REQ-VET-003 prose uses behavioral language throughout; the /vets route re-characterized as supported under REQ-VET-003, not pending removal
- docs/system-design.md: Contracts table Implements cells reference REQ-VET-003 correctly; REQ-VET-002 absent from all Implements cells; no struct field tables or parameter tables introduced; Design and ADR links present
- docs/adr/2026-08-07-non-goal-free-text-vet-search.md: filename carries non-goal- infix per project convention; Implementation section uses **Non-goal:** NG-9; all required template sections present; Decision and Consequences in present tense; reference to ../prd.md#req-vet-003 is a full path
- docs/adr/2026-08-07-vet-directory-filter-in-memory.md: all required template sections present; Implementation section uses **Requirements:** REQ-VET-003; the serialized /vets surface described as active (line 8); references ../system-design.md#contracts and ../prd.md#req-vet-003 as full paths; cross-ADR reference to the non-goal ADR present; no REQ-VET-002 reference
- docs/adr/README.md: two new index rows added with correct titles, filenames, date, and Accepted status matching the ADR files; rows appear in chronological order after the 2026-07-31 entries; column count consistent

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $7.62 | 13m 25s | 93% |
| `spring-boot-claude:system-design-expert` | 2 | opus-4-8 | $5.87 | 6m 47s | 84% |
| `(parent)` | 1 | opus-5 | $5.20 | 48m 17s | 96% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $4.25 | 5m 58s | 84% |
| `spring-boot-claude:security-reviewer` | 2 | opus-4-8 | $2.72 | 1m 43s | 75% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $2.38 | 5m 17s | 81% |
| `spring-boot-claude:doc-reviewer` | 3 | sonnet-4-6 | $1.95 | 6m 36s | 81% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $1.89 | 7m 2s | 79% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $1.48 | 4m 59s | 83% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.17 | 13s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $5.20 | 48m 17s | 96% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $4.54 | 5m 38s | 86% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $4.37 | 8m 28s | 95% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $3.25 | 4m 57s | 91% |
| `spring-boot-claude:change-grader` | opus-4-8 | $2.38 | 5m 17s | 81% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $2.16 | 3m 22s | 88% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $2.10 | 2m 36s | 77% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $1.44 | 45s | 69% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.33 | 1m 8s | 75% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $1.28 | 58s | 80% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $1.01 | 4m 27s | 76% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.89 | 2m 35s | 81% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.84 | 3m 4s | 81% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.76 | 2m 26s | 78% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.72 | 2m 33s | 87% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.68 | 1m 47s | 83% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.43 | 1m 44s | 77% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.17 | 13s | 0% |

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

- plugin `spring-boot-claude` at `v0.1.18` (tag)
- model requested `claude-opus-5`; models used: opus-4-8 · opus-5 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `064d588523591361` · `2.1.224 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
