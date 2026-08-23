# vets-specialty-filter r1 — v0.3.1

Filter the vet list by specialty (feature) · started 2026-08-14T23:08:23+00:00 · exec `claude-dev` · status **complete**

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
| review attention (pipeline grade) | concern |

The pipeline grade estimates how much human review the change deserves before merge — advisory context from the harness's change grader (read from the ledger's `grader-verdict` record), never part of the bar.

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
| 4 (±0) | 4 (±0) | 4 (±0) | 3 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $1.30. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 3

> Filtering is pushed into derived repository finders ( findBySpecialtiesNameIgnoreCase ), leaving VetController binding-and-delegating per the Web controller row; the blank-means-absent rule mirrors owner search and stays a small private helper, and the uncached decision is reasoned in an ADR rather than copied blindly. Tests are BDD-named ( theSpecialtyFilterShouldIgnoreLetterCase ), parameterized for prefix/padding boundaries, with named tiers ( SPECIALTY_NO_VET_HOLDS ,  ONE_VET_PER_PAGE ) and a derived page count; weak points are two-act tests ( theBlankSpecialtyShouldListEveryVet ) and raw-HTML string assertions. The five near-identical Thymeleaf ternaries are duplication a reviewer would note. Docs are otherwise exhaustive, but system-design.md's surviving claim that vet page size "is a local variable in each controller" is falsified by the new  PAGE_SIZE  constant.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 3

> Filtering lands in the repository as derived queries ( findBySpecialtiesNameIgnoreCase , both overloads) with the controller only binding and delegating — right layer, no duplication; the uncached-read choice is reasoned in an ADR. Minor deviation: the blank-is-absent rule now lives in  VetController.activeSpecialty , a fresh (if small) rule in the web layer. Tests are behavior-named, constant-driven, and cover case, prefix, padding, empty, and paging; but  theBlankSpecialtyShouldListEveryVet  and  theAbsentSpecialtyShouldLeaveBothSurfacesUnchanged  each run two act/assert cycles, and new Mockito stubbing is added without the conscious-exception rationale the principles ask for. Five near-identical ternary link expressions in  vetList.html  are repetitive. Docs are thorough, but system-design.md's "Page size ... is a local variable in each controller" is now stale against  PAGE_SIZE .

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> Filtering lands in the repository as derived queries ( findBySpecialtiesNameIgnoreCase , VetRepository.java), leaving VetController thin — bind, delegate, select — and the uncached choice is justified by an ADR rather than left as a silent inconsistency. The blank-equals-absent rule still lands in the controller ( activeSpecialty ), a new rule in a layer the catalog bars, unrecorded. Tests are BDD-named and tier-named ( theSpecialtyFilterShouldNotTrimAPaddedValue ,  ONE_VET_PER_PAGE ), with derived expectations, but  theBlankSpecialtyShouldListEveryVet  and  theAbsentSpecialtyShouldLeaveBothSurfacesUnchanged  each exercise two surfaces in one test, and new Mockito stubs are added. Five near-identical ternary link expressions in vetList.html are the maintenance weight. Docs are near-complete; system-design.md's "page size ... is a local variable in each controller" is stale after PAGE_SIZE.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $18.95 | 47m | 44 | 94% | 10 file(s) +360/−32 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.04 | 2m 42s | 91% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VETSSPECIALTYFILTER-001

0 review rounds · 0 build-passes · no grade yet

- • intake-decision (human)

---

### REQ-VET-003 — Reader filters the veterinarian directory by specialty

2 review rounds · 3 build-passes · **1 build-failure** · grade **CONCERN**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (1) | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Reader filters the veterinarian directory by specialty · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **new** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 12m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L6 · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 1m***
  - ▹ rec: VetController.java:86 — the private activeSpecialty() javadoc cites 'REQ-VET-003' directly ('REQ-VET-003 does not trim it...'). No other production file in the codebase references a requirement ID in a code comment; the ID is only meaningful by cross-referencing docs/prd.md, and requirement IDs can be renumbered or archived. Rephrasing the sentence to describe the behavior directly (drop the ID) would keep the comment self-contained for a reader with no access to today's PRD.
  - ▹ rec: vetList.html — the pagination block repeats the same 'specialty != null ? @{...(...,specialty=...)} : @{...(...)}' ternary five times (lines ~339-372). Thymeleaf's link-expression syntax makes a shared helper awkward, so this is not a blocking finding, but a th:with-scoped variable or a Thymeleaf fragment parameter could collapse the five near-identical branches if the template gains a sixth link.
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply-chain check NOT RUN, not clean: build.gradle configures no OWASP dependency-check plugin (plugins are boot 4.1.0, dependency-management 1.1.7, graalvm 1.1.2, cyclonedx-bom 3.2.4, javaformat 0.0.47), and this reviewer has no network access, so no NVD match ran. This change adds no dependency and does not alter build.gradle, so the delta introduces no supply-chain risk; the resolved framework versions (Spring Boot 4.1.0 and its managed Jackson) remain unverified against the NVD by CI or a human. The project already emits a CycloneDX SBOM, which is the natural feed for that check.
  - ▹ rec: Readability-adjacent, no exploit path: vetList.html line 20 declares a th:each local named 'specialty' (a Specialty entity) while the model attribute 'specialty' (a String) drives the pagination links. The scopes do not overlap today — the loop is confined to the table body — so rendering is correct, but a future edit that moves a link inside the table would silently read the wrong 'specialty'. Renaming the loop variable would remove the trap.
  - ▹ rec: Request-supplied specialty length is unbounded (only the container's query-string limit applies) before it reaches the database comparison. Harmless at this scale and no worse than the existing unfiltered reads; worth a length cap if the filter ever gains a cached or indexed path.
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 1m***
  - [autofix] `ClinicServiceTests.java:theVetHoldingS` The new test asserts on bare literal last names "Douglas" and "Ortega" (twice), while every sibling test added in this same slice names its expected last-name data (RADIOLOGIST_LAST_NAMES). testing-principles.md's Three-Tier Data Naming Convention treats an expected-outcome value as Tier 1 (meaningful) and requires a role-describing name; it applies to tests written from 2026-07-31 onward, which this one is.
    - fix: Introduce named constants (e.g. SURGEON_LAST_NAMES = List.of("Douglas", "Ortega"), DENTIST_LAST_NAME = "Douglas") and assert against them with containsExactlyInAnyOrderElementsOf/isEqualTo, matching the pattern already used by theVetDirectoryShouldListOnlyVetsHoldingTheRequestedSpecialty in the same file.
  - [autofix] `ClinicServiceTests.java:theVetHoldingS` The test's two assertion blocks (SURGERY -> {Douglas, Ortega}; DENTISTRY -> {Douglas}) are structurally identical repeated cases (call findBySpecialtiesNameIgnoreCase(specialty), assert the matching last names) asserting two unrelated concerns in one @Test rather than one logical assertion per test. testing-principles.md's Agent Decision Checklist item 8 (recurring verification sequences extracted) and the Parameterized Tests checklist call for @ParameterizedTest here instead of two hand-copied blocks.
    - fix: Split into a @ParameterizedTest over specialty/expected-last-names pairs (e.g. @MethodSource or @CsvSource), one assertion per invocation, matching the file's existing @ParameterizedTest usage for theSpecialtyFilterShouldNotMatchPartOfASpecialtyName.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 2m***
  - **[blocked]** `system-design.md:100,103,104` The Contracts table's Implements column is stale for the three contracts this slice directly modifies. `VetController` (row 104) and `VetRepository` (row 103) each gain a specialty-filtered method implementing REQ-VET-003, but both rows still list only REQ-VET-001. `Vet` (row 100) is now read through both the filtered and unfiltered paths of both surfaces and is likewise still REQ-VET-001-only. Separately, `VetRepository`'s Purpose cell reads 'results are cached' (row 103) — true of the two pre-existing methods but now false as a blanket description of the type: the two new specialty-filtered methods are deliberately uncached (ADR 2026-08-14-uncached-filtered-vet-queries.md). A reader who trusts this row could reasonably re-annotate a future VetRepository method @Cacheable for 'consistency', repeating exactly the mistake the new ADR was written to prevent. This is distinct from the `Vets` row's '—' Implements, which the design-block (line 10) explicitly and correctly defers to doc-sync; these three rows were not called out as deferred and their owning source files (VetController.java, VetRepository.java) are in this diff.
- ↻ **implement** (implementer) ← test · (2 findings) · ***◷ 2m***
  - ▲ **build ✓ clean** · build · test · checkFormat · checkstyleMain · handoff-log · autofix-audit
- ↻ **fix design** ← doc · (1 finding)
- ◈ **design-block** **new** · (design) · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · checkFormat · checkstyleMain · checkstyleTest · handoff-log · autofix-audit
- ✔ **review test** · **approved** · ***◷ 39s***
- ✔ **review security** · **approved** · ***◷ 39s***
  - ▹ rec: Supply-chain check NOT RUN, not clean — unchanged from line 19 and repeated so it is not read as closed. build.gradle is untouched by this slice and configures no OWASP dependency-check plugin, and this reviewer has no network access, so no NVD match ran in either round. Spring Boot 4.1.0 and its BOM-managed Jackson remain unverified against the NVD; CI or a human must close it. The project already emits a CycloneDX SBOM, which is the natural feed.
  - ▹ rec: Carried forward from line 19, both still open and neither reachable: vetList.html line 20 declares a th:each local named 'specialty' shadowing the request-derived 'specialty' model attribute that drives the pagination links (scopes do not overlap today; a link moved inside the table body would silently read the wrong one — renaming the loop variable removes the trap), and the request-supplied specialty reaches the database comparison with no length bound beyond the container's query-string limit (harmless while the filtered reads stay uncached and unindexed; worth a cap if that changes).
- ✔ **review code-quality** · **approved** · ***◷ 49s***
  - ▹ rec: VetController.java:86 — the private activeSpecialty() javadoc still cites the requirement ID directly ('REQ-VET-003 does not trim it...'), unchanged since round 1. No other production file references a requirement ID in a code comment; rephrasing to describe the behavior without the ID would keep the comment self-contained for a reader without today's PRD open. Not blocking.
  - ▹ rec: vetList.html still repeats the same specialty-aware/absent ternary link-expression five times across the pagination block; still not blocking given Thymeleaf's syntax constraints, carried forward from round 1 as a polish note.
- ✔ **review doc** · **approved** · ***◷ 1m***
- ◆ **grade CONCERN** · filter the vet directory by specialty on both surfaces
  - blast_radius — **clear** — Contained in the vet package: two handlers, two new derived repository reads, the vet-only pagination template, plus two test files and docs. One module, no sensitive paths, no build or config files, no shared type touched; the only cross-cutting element is the published URL contract on the two vet routes, which gains an optional parameter and changes nothing when it is absent.
  - semantic_surprise — **clear** — Read every production hunk: the blank-to-null normalization in activeSpecialty matches the stated behavior exactly (blank is absent-equivalent, no trimming), both handlers select between the filtered and unfiltered read with the null test the right way round, and all five rewritten pagination links pick the with-specialty link expression only when the attribute is non-null, so the unfiltered page carries no bare parameter. The template's th:each local named specialty at line 20 shares the model attribute's name, but its scope is the table body and every pagination link sits outside it, so nothing shadows today.
  - test_adequacy — **clear** — The tests exercise real behavior rather than restate it: ClinicServiceTests drives the derived query against a real H2 dataset and pins whole-name matching, case-insensitivity, three partial-name rejections, both padded variants, the no-match empty result and paging over only the matching vets; VetControllerTests pins both surfaces, the blank and absent cases, the pagination links carrying the filter, and URL-encoding of a markup-bearing value. An inverted condition or a trimmed value would fail several of them. The one untested corner is the HTML page rendering an empty filtered list, which the JSON side covers.
  - reviewer_hedging — **concern** — All four dispatched reviewers approved with zero findings, but two attached residual recommendations to a final-round approval. Security states the supply-chain check was NOT RUN rather than clean and repeats it so it is not read as closed, and carries forward two open items: the template's shadowing-prone loop variable name and the unbounded length of the request-supplied specialty reaching the database. Code quality carries the requirement ID inside a production javadoc and the fivefold repeated link ternary as unfixed polish.
  - scope_deviation — **clear** — The diff matches the requirement's stated surface, and everything beyond the PRD's four file targets was directed by the owner: the NG-9 narrowing recorded as an ADR, the machine-readable route reinstated as supported, and the repository-level tests the design block asked for. One design revision was a documentation fix round closing a reviewer finding on the contracts table, not a wander; no consultations, no build retries against the cap.
  - why — The code reads exactly as described and its tests would catch an inversion, so the residual is not correctness but what the reviewers parked. Before merging, close the supply-chain check the security reviewer explicitly left unrun, and decide whether the template's shadowing-prone loop variable and the unbounded specialty length are worth fixing now.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- VetController's activeSpecialty() blank-to-null normalization mirrors OwnerController's established lastName pattern (null-check plus a documented sentinel), keeping the new surface consistent with the codebase's existing convention rather than introducing Optional where the rest of the package does not use it
- VetRepository's two new derived-query methods are documented with why they are deliberately not @Cacheable, with a direct pointer to the ADR, so the asymmetry with the sibling cached methods reads as a decision rather than an oversight
- Formatting (./gradlew checkFormat) passes clean; naming, method length, and control flow throughout VetController and VetRepository meet the checklist

**security-reviewer**

- Injection into data access: both new reads are Spring Data derived queries (findBySpecialtiesNameIgnoreCase) with the request value bound as a JPA parameter. No concatenated query text, no @Query, no createQuery anywhere in the vet package.
- Cross-site scripting on the reflected filter: the model attribute 'specialty' is request-derived and reaches the page only through link expressions @{/vets.html(page=...,specialty=${specialty})}, which URL-encode the value; Thymeleaf's default attribute escaping stays on. The change also removes the last __${...}__ preprocessing hrefs from vetList.html, so the file no longer builds any URL by string interpolation. thePaginationLinksShouldUrlEncodeTheSpecialty pins the encoding with a \<script> payload (specialty=%3Cscript%3E), and grep over src/main/resources/templates finds no th:utext, no param.* access, and no remaining preprocessing.
- Cache abuse avoided: the two new reads carry no @Cacheable, so request-supplied text never becomes a key in the unbounded, evictionless 'vets' cache. Deliberate per docs/adr/2026-08-14-uncached-filtered-vet-queries.md, restated in the Javadoc on both methods; the asymmetry with the sibling findAll reads is the secure choice, not an oversight.
- Exposed surface unchanged: no new route. Both handlers gain one optional @RequestParam String; no request-bound command object, so no mass-assignment or identifier-binding surface. Blank-to-absent normalization (StringUtils.hasText) happens at the controller boundary, matching the owner-search precedent.
- Transaction and pattern consistency: both new methods carry @Transactional(readOnly = true) like every existing VetRepository read — least privilege on the data access, and the same way the neighbouring concern is already secured.
- No secrets, no logging, no file or process I/O, no deserialization config, no schema or dependency change in the diff: grep over the change set for password/secret/token/api-key/credential returns nothing, and no System.out/err, Runtime, or ProcessBuilder appears in the vet package.
- Resource exposure not worsened: the paged filter joins the specialties association as a filter join rather than a fetch join, so paging stays in SQL; the unpaged JSON surface returns a filtered subset of what /vets already returned unfiltered.

**test-reviewer**

- All eight test_names from the prd-entry (line 4) are present and exercise the acceptance criteria they name, including the padded-value edge case (theSpecialtyFilterShouldNotTrimAPaddedValue) which the prd-entry did not enumerate but the PRD's edge-case #3 requires
- Query-semantics assertions (whole-name, case-insensitive, partial, padded, no-match, paged, multi-specialty) correctly moved to the H2-backed ClinicServiceTests per the superseding design-block (line 10), keeping VetControllerTests to the mocked web contract only -- Stop Re-Testing Other Units is respected, no duplicate DB-semantics assertions at the controller layer
- XSS risk flagged in the design-block's risks is covered by a real adversarial test (thePaginationLinksShouldUrlEncodeTheSpecialty, asserting the URL-encoded form of \<script>)
- theAbsentSpecialtyShouldLeaveBothSurfacesUnchanged pins the no-specialty= regression the design-block called out for the unfiltered pagination links
- AssertJ used throughout, fluent and chained; no JUnit assertEquals/assertTrue; collection assertions use containsExactly/containsExactlyInAnyOrder/isEmpty appropriately
- Derived expectations followed in theFilteredVetPageShouldPageOverOnlyTheMatchingVets (totalPages computed from RADIOLOGIST_LAST_NAMES.size() / ONE_VET_PER_PAGE rather than a hard-coded number)
- New tests in both files follow the BDD the{Subject}Should{Outcome} naming school and construct via existing/introduced factory helpers (james(), helen(), firstOfTwoPages()) rather than raw constructors
- ./gradlew test: BUILD SUCCESSFUL; jacocoTestReport shows 100% instruction/line/branch coverage for VetController, comfortably above the brief's 80% target
- Mocking stays within the brief's policy: VetControllerTests uses the sanctioned MockMvc harness plus tolerated Mockito repository stubs, consistent with the file's pre-existing idiom (given(...)/any(Pageable.class))

**doc-reviewer**

- docs/prd.md: REQ-VET-003 prose stays behavioral with no mechanism, code-element name, or rationale leak; every new sentence is under the 30-word standard; all nine new acceptance bullets and four edge cases are tagged and traceable
- docs/prd.md Non-Goals: NG-9 narrowing is recorded with a rationale-table entry and an ADR link, not inline rationale prose; the scope_overrides entry in the prd-entry (line 4) quotes the intake decision (line 2) verbatim
- docs/adr/2026-08-14-non-goal-vet-specialty-filter.md and docs/adr/2026-08-14-uncached-filtered-vet-queries.md: both follow the non-goal/decision ADR conventions (Non-goal:/Requirements: line, em-dash references), and every cross-reference (prd.md#non-goals, prd.md#req-vet-003, system-design.md#persistence, system-design.md#open-questions-from-the-survey) resolves to a real anchor
- docs/adr/README.md: both new rows added in the existing table format
- docs/system-design.md Known Defects: the resolved machine-readable-route row is correctly removed rather than left stale; Open Question 5 is updated to note the unbounded paged cache key rather than superseded wholesale
- docs/ubiquitous-language.md: 'Specialty' and 'Veterinarian' entries already cover this slice's vocabulary; no new or drifted term introduced

**test-reviewer**

- Both round-1 autofix findings on ClinicServiceTests.theVetHoldingSeveralSpecialtiesShouldMatchEachOfThem are correctly applied: bare literals "Douglas"/"Ortega" replaced with role-named SURGEON_LAST_NAMES/DENTIST_LAST_NAMES constants alongside the existing RADIOLOGIST_LAST_NAMES, matching the file's Three-Tier naming convention
- The two hand-copied assertion blocks are now one @ParameterizedTest over specialties via @MethodSource, one assertion per invocation, consistent with the file's existing @ParameterizedTest idiom (theSpecialtyFilterShouldNotMatchPartOfASpecialtyName)
- ./gradlew test green for ClinicServiceTests and VetControllerTests; full suite green per build-pass at line 27
- This fix round touched only docs/system-design.md (per design-block line 25); no new test or production code was introduced since the line 24 green build, so no new class-sweep surface exists beyond what round 1 already covered
- All eight prd-entry test_names remain present and continue to exercise their acceptance criteria unchanged from round 1's approved_aspects

**security-reviewer**

- Fix delta since the reviewed basis tree (01e167e) is docs/system-design.md plus ClinicServiceTests.java only:  scripts/changeset.sh --base-tree 01e167e --name-only  returns exactly those two paths, so no production Java, template, or build file changed since the round-1 approval at line 19. Every attacker-facing conclusion in that record still holds over the current tree.
- docs/system-design.md delta is prose-only and strictly reduces security-relevant staleness. The VetRepository Purpose cell no longer makes the blanket claim 'results are cached' — it now states the split (unfiltered cached, specialty-filtered deliberately not) and links ADR 2026-08-14-uncached-filtered-vet-queries.md. That is the correct direction: the false blanket claim was the documentation defect most likely to induce a future @Cacheable on a filtered read, which would put request-supplied specialty text into the unbounded, evictionless 'vets' cache. Open Question 5 was narrowed to 'unfiltered read methods are cached' for the same reason.
- Contracts-table Implements additions (REQ-VET-003 on VetRepository and VetController) and the em-dash preamble change are traceability metadata with no runtime or trust-boundary effect.
- Test delta in ClinicServiceTests converts theVetHoldingSeveralSpecialtiesShouldMatchEachOfThem into a @ParameterizedTest over a @MethodSource of (specialty, expected last names) pairs. Arguments are compile-time constants from the fixture data; no external, environment, or request-derived input enters the test, no new I/O, no reflection beyond JUnit's own MethodSource lookup by literal name. The assertion still pins the same specialty-to-vet mapping through the same derived query, so the coverage that backs the injection and cache-key conclusions is preserved, not weakened.
- Grep sweep over the delta for credential-shaped names (password, secret, token, api-key, credential) and for the dangerous-pattern set (Runtime, ProcessBuilder, exec(, enableDefaultTyping, JsonTypeInfo, System.out/err, /tmp/) returns nothing in either changed file.

**code-quality-reviewer**

- Both round-1 test-reviewer findings on ClinicServiceTests.theVetHoldingSeveralSpecialtiesShouldMatchEachOfThem are correctly applied: bare literals "Douglas"/"Ortega" replaced with role-named constants SURGEON_LAST_NAMES/DENTIST_LAST_NAMES alongside the existing RADIOLOGIST_LAST_NAMES, and the two hand-copied assertion blocks collapsed into a single @ParameterizedTest over specialty/expected-last-names pairs via @MethodSource, matching the file's existing @ParameterizedTest idiom
- No production code (VetController.java, VetRepository.java, vetList.html) changed since the round-1 approval at line 18; that review's findings and approved_aspects stand unchanged
- ./gradlew checkFormat and ./gradlew compileTestJava both pass clean on the current tree
- The docs/system-design.md Contracts-table fix from the round-2 design-block (line 25) is outside code-quality-reviewer scope (doc-reviewer's dimension) and is not re-litigated here

**doc-reviewer**

- docs/system-design.md Contracts table (line 103, 104): VetRepository and VetController rows now cite REQ-VET-001, REQ-VET-003, closing the round-1 finding for the two files this diff directly modifies
- docs/system-design.md Contracts table (line 103): the VetRepository Purpose cell replaces the blanket 'results are cached' with the cached/uncached split and an ADR link, removing the misleading claim that invited re-annotating a future method @Cacheable
- docs/system-design.md (line 76) and Known Defects: the em-dash preamble now names the serialization wrapper as a fourth kind, and the resolved machine-readable-route Known Defects row stays removed, both consistent with the diff
- docs/system-design.md Open Question 5: narrowed to 'unfiltered read methods are cached' and gains the unbounded paged-cache-key detail, matching the new Persistence-section sentence and the ADR
- every new or changed link in this round's delta resolves (adr/2026-08-14-uncached-filtered-vet-queries.md exists, is referenced twice, both correctly), and every new sentence stays under the 30-word standard

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 4 | opus-5 | $6.20 | 19m 57s | 96% |
| `agent-team:system-design-expert` | 3 | opus-5 | $4.19 | 12m 9s | 92% |
| `(parent)` | 1 | opus-5 | $2.38 | 49m 32s | 96% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.61 | 4m 19s | 95% |
| `agent-team:security-reviewer` | 2 | opus-5 | $1.17 | 2m 31s | 87% |
| `agent-team:change-grader` | 1 | opus-5 | $1.04 | 2m 42s | 91% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.02 | 4m 9s | 95% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.66 | 3m 3s | 91% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.62 | 2m 21s | 91% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.87 | 12m 38s | 97% |
| `(parent)` | opus-5 | $2.38 | 49m 32s | 96% |
| `agent-team:system-design-expert` | opus-5 | $1.73 | 5m 54s | 93% |
| `agent-team:product-requirements-expert` | opus-5 | $1.61 | 4m 19s | 95% |
| `agent-team:system-design-expert` | opus-5 | $1.41 | 3m 54s | 92% |
| `agent-team:system-design-expert` | opus-5 | $1.05 | 2m 21s | 91% |
| `agent-team:change-grader` | opus-5 | $1.04 | 2m 42s | 91% |
| `agent-team:feature-implementer` | opus-5 | $0.86 | 3m 24s | 95% |
| `agent-team:security-reviewer` | opus-5 | $0.76 | 1m 44s | 88% |
| `agent-team:feature-implementer` | opus-5 | $0.75 | 1m 56s | 92% |
| `agent-team:feature-implementer` | opus-5 | $0.72 | 1m 57s | 91% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.58 | 2m 30s | 96% |
| `agent-team:test-reviewer` | sonnet-5 | $0.52 | 2m 17s | 93% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.44 | 1m 39s | 93% |
| `agent-team:security-reviewer` | opus-5 | $0.41 | 47s | 85% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.35 | 1m 26s | 93% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.27 | 54s | 87% |
| `agent-team:test-reviewer` | sonnet-5 | $0.14 | 45s | 78% |

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

- plugin `agent-team-spring-boot` at `v0.3.1` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `064d588523591361` · `2.1.232 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
