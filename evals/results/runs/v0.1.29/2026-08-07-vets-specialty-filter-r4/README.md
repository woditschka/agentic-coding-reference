# vets-specialty-filter r4 — v0.1.29

Filter the vet list by specialty (feature) · started 2026-08-06T23:42:47+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.64. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Repository derived queries (VetRepository findBySpecialtiesNameIgnoreCase, both overloads) put narrowing in the query, so Page totals and the reworked vetList.html link expressions stay correct; the uncached choice is reasoned in an ADR. Deduction: selectedSpecialty() is a new product rule (blank behaves as absent) added to VetController as a private method, unit-untestable without booting the framework — the checklist's 'no new rule in a controller' bar, only partly excused by owner-search precedent. Tests are strongly behavior-named and constants are tiered (RADIOLOGY, SPECIALTY_NO_VET_HOLDS), but ClinicServiceTests exercises two subjects per test (page and collection) and inlines act into assert in theVetListShouldNotMatchAPartialSpecialtyName, blurring the four phases; the link test asserts a raw HTML substring. Documentation is thorough: NG-9 narrowed, REQ-VET-003/004 minted, superseded entry, open question, ADR index, and the retired defect row all updated.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Repository-derived finders fit the Repository pattern, and the uncached choice is argued in an ADR and pinned by javadoc on VetRepository.findBySpecialtiesNameIgnoreCase, so a later contributor cannot silently reintroduce the caller-keyed cache. Cost: the blank/whitespace normalization and the findAll-vs-filtered branch both live in VetController (selectedSpecialty, findPaginated), a fresh rule in a controller that the catalog's Web controller row disallows and that could have been unit-tested without booting the web layer — every new test instead boots MockMvc or the database. Test names follow the{Subject}Should{Outcome} and constants are tiered, but expectations lean on bare "Leary"/"Stevens" literals and each ClinicServiceTests case exercises two reads in one test. Documentation is thorough: NG-9 narrowing, REQ-VET-003/004, superseded entry, and the removed known-defect row all move together.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Repository derived queries ( findBySpecialtiesNameIgnoreCase ) are idiomatic and keep narrowing in the query, so Page totals describe the filtered list. But  selectedSpecialty()  in  VetController  is a new input rule placed in a controller — the checklist bars new rules there, and it is exactly the kind of rule testable without booting the framework; the null-branch is also duplicated in  findPaginated  and  showResourcesVetList . Tests are BDD-named and cover case, prefix, blank, empty-result, pagination, and link-carrying across both surfaces, with real-DB coverage in  ClinicServiceTests ; deductions for bare literals  "Leary" / "Stevens" ,  totalPages  2 asserted rather than derived from  narrowedTotal / PAGE_SIZE , and Mockito stubs without a stated exception. Docs are fully current: NG-9 narrowed, REQ-VET-003/004 minted, superseded entry and the stale "serves no requirement" defect row removed, two ADRs indexed.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $13.09 | 35m | 32 | 89% | 10 file(s) +325/−26 |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-004 — Reader narrows the veterinarian directory to one specialty on both surfaces

2 review rounds · 3 build-passes · **1 build-failure** · no grade yet

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (1) | ✎ (2) |
| **security** | **✔** | **✔** |
| **doc** | ✎ (1) | **✔** |

- ◇ **prd-entry** Reader narrows the veterinarian directory to one specialty on both surfaces · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **minor** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 7m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **minor** · (design) · supersedes L4 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 47s***
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 1m***
  - **[blocked]** `system-design.md:103-104` The Implements column for `VetRepository` and `VetController` was updated to add REQ-VET-003 but omits REQ-VET-004, even though this slice's own code adds specialty-filtered reads to both: VetRepository gains the two derived findBySpecialtiesNameIgnoreCase methods and VetController gains the optional specialty parameter on both handlers. Per the Cross-Document Coherence checklist, a requirement's implementing contracts must be named in the Implements column; a reader relying on this table to find REQ-VET-004's implementation will not find it listed against either contract. Additionally the VetRepository row's description, "Spring Data repository for veterinarians; results are cached", is now inaccurate: per docs/adr/2026-08-06-uncached-specialty-filtered-vet-queries.md the two new specialty-filtered methods are deliberately uncached, so "results are cached" no longer holds for the whole contract.
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `VetControllerTests.java:187-195` Acceptance criterion 6 ('A specialty no veterinarian holds yields the ordinary directory response...on both forms - not a refusal, a failure, or a not-found') is verified only on the page form (theVetListShouldBeEmptyWhenNoVetHoldsTheSpecialty asserts status 200, empty listVets, no model errors). The machine-readable form has no equivalent assertion - theMachineReadableVetListShouldReturnOnlyVetsHoldingTheRequestedSpecialty only exercises the non-empty case. Unlike the matching-semantics criteria (case-insensitivity, whole-name), which are legitimately covered once at the repository layer because both surfaces share one query method, this is controller-level response-shape behavior (HTTP 200 with an empty vetList, not a 404/error) and is not exercised for the JSON endpoint by any test in the diff.
    - fix: Add a controller test (e.g. theMachineReadableVetListShouldReturnEmptyResultWhenNoVetHoldsTheSpecialty) stubbing findBySpecialtiesNameIgnoreCase(SPECIALTY_NO_VET_HOLDS) to return an empty collection and asserting GET /vets?specialty=\<that value> returns status 200 with an empty $.vetList array, mirroring the page-form empty-result test.
- ↻ **implement** (implementer) ← test · (1 finding) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ◈ **design-block** **minor** · (design) · supersedes L8 · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 54s***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 31s***
- ✔ **review doc** · **approved** · ***◷ 47s***
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 1m***
  - [autofix] `VetControllerTests.java:197-206` Verified fixed: theMachineReadableVetListShouldBeEmptyWhenNoVetHoldsTheSpecialty now asserts HTTP 200, JSON content type, and jsonPath("$.vetList").isArray()/isEmpty() — exercising the response shape the prior round's finding called out as unexercised.
  - [autofix] `VetControllerTests.java:144-151` Same class as the finding just fixed: theVetListShouldIgnoreABlankSpecialty exists only for the /vets.html form. PRD REQ-VET-004 acceptance bullet 5 and edge case 3 both say 'either form' for a blank/all-space specialty, and every other REQ-VET-004 criterion in this file is exercised as a matched pair (theVetListShould.../theMachineReadableVetListShould...). Add theMachineReadableVetListShouldIgnoreABlankSpecialty asserting GET /vets?specialty=%20%20%20 returns every vet (vets.findAll(), not findBySpecialtiesNameIgnoreCase) with $.vetList.length() == 2, mirroring the existing blank-HTML test and the RADIOLOGY/no-specialty JSON pair already present.
    - fix: Add a test in VetControllerTests.java mirroring theVetListShouldIgnoreABlankSpecialty for the /vets JSON endpoint, asserting the unfiltered vetList is returned when specialty is blank/all-space.
- ✔ **review security** · **approved** · ***◷ 1m***

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- Both VetController handlers share a private selectedSpecialty(String) helper that normalizes null/blank the same way the owner search does, avoiding duplicated stripping logic
- VetRepository's two new derived-query methods carry full Javadoc including the deliberate absence of @Cacheable, with the reasoning cross-referenced to the ADR rather than restated
- Method and variable naming is descriptive and consistent with the existing file style (selectedSpecialty, findPaginated, findBySpecialtiesNameIgnoreCase)
- vetList.html threads the specialty parameter through every page-link URL via Thymeleaf @{} link expressions rather than string concatenation, consistent with the existing paging-link pattern
- New tests (VetControllerTests, ClinicServiceTests) are additive only, use named constants instead of magic strings, and follow the file's existing structure and matcher style
- ./gradlew checkFormat and compileJava/compileTestJava pass clean on the change set

**security-reviewer**

- Injection: the specialty filter is a Spring Data derived query (findBySpecialtiesNameIgnoreCase) with no @Query, no string concatenation, and no native SQL anywhere in the change - the parameter is bound, so the caller-controlled value cannot alter query structure. Sweep of src/main/java for @Query/createQuery/createNativeQuery found only the pre-existing static PetTypeRepository query.
- Cache-key poisoning mitigation verified independently by reading the full VetRepository: both new filtered reads carry @Transactional(readOnly = true) and no @Cacheable, while the two unfiltered findAll methods keep @Cacheable("vets"). A caller-supplied specialty therefore never mints an entry in the eviction-less, size-unbounded vets cache. Matches docs/adr/2026-08-06-uncached-specialty-filtered-vet-queries.md.
- Case-insensitivity comes from Spring Data's IgnoreCase keyword in the method name, not from a schema change, collation change, or hand-rolled SQL - no DDL or persistence config is touched by the diff.
- Template injection / XSS: every new page link in vetList.html uses the link-expression parameter form @{/vets.html(page=..., specialty=${specialty})}. No __${...}__ preprocessing form is introduced (grep -F '__${' over src/main/resources/templates shows only pre-existing occurrences, all outside this change set, and none binding the new specialty). The parameter form URL-encodes the value and Thymeleaf attribute output escapes it, so a specialty such as ">\<script> is rendered inert; the value is never written into an element body or a raw th:utext.
- Input handling: VetController.selectedSpecialty normalizes null/blank/all-space to null, so a blank selector falls back to the unfiltered read rather than matching the empty string; the value is otherwise passed only as a bound query parameter and a model attribute consumed by escaped link expressions. No file path, command, deserialization, or reflection sink is reached.
- Data exposure: /vets and /vets.html return the same Vet projection as before, narrowed rather than widened. No new field, no new endpoint, no authorization boundary crossed - both routes were already public reads.
- No secrets introduced: scan of the source and docs diff for password/secret/token/api-key/credential returned nothing.
- Supply chain unchanged: build.gradle, settings.gradle, gradle.properties, and gradle/ are untouched by the change set, so no dependency or version is added or moved and no new CVE surface is introduced.

**doc-reviewer**

- docs/prd.md: REQ-VET-003 and REQ-VET-004 anchored, worded behaviorally with no mechanism leak, Done-when bullets are bounded given/when/then contracts, edge cases renumbered coherently and no stale edge-case references remain elsewhere in the repo, Superseded entry and Open Questions Revisited clause both read as history not new rationale.
- docs/adr/2026-08-06-non-goal-veterinarian-search.md and docs/adr/2026-08-06-uncached-specialty-filtered-vet-queries.md: both follow the ADR format, carry Requirements:/Non-goal: Implementation lines, options-considered/decision/consequences structure, and their cross-links (prd.md, system-design.md, security-principles.md) all resolve to real anchors.
- docs/adr/README.md: two new index rows in the established table form, em-dashes preserved.
- docs/system-design.md: stale Known Defects row about the machine-readable route correctly removed, and no other doc retains the old 'pending removal' / 'serves no requirement' framing.
- Ubiquitous-language terms (Veterinarian, Specialty, Vets) used consistently with docs/ubiquitous-language.md across all changed docs.

**test-reviewer**

- The VetControllerTests/ClinicServiceTests split holds: VetControllerTests stubs the repository and correctly restricts itself to controller-owned behavior (which read is delegated to, model attributes, view name, page-link encoding, pagination totals); ClinicServiceTests uses a real @DataJpaTest/H2 repository to assert the actual matching semantics (case-insensitivity, whole-name-vs-partial, empty-result) against both the Page and Collection query overloads, which is the right place to prove the query rather than a stub's programmed response.
- Case-insensitivity and whole-name-only matching (AC4, AC5) are each verified once against real seeded data for both the paged and unpaged repository methods, correctly treating them as shared query behavior rather than duplicating a stub-only assertion per surface.
- Test data follows the three-tier naming convention throughout (RADIOLOGY, RADIOLOGY_IN_MIXED_CASE, RADIOLOGY_PREFIX, SPECIALTY_NO_VET_HOLDS, PAGE_SIZE) with no mystery literals in the new tests, and totalPages in theVetListShouldPaginateTheNarrowedList is a value a reader can verify by hand from narrowedTotal and PAGE_SIZE.
- Pagination narrowing (AC8) is directly tested: totals come from the narrowed Page and the page-link href is asserted to carry the specialty parameter through Thymeleaf's URL-encoding parameter form.
- Mocking stays within the brief's policy - MockitoBean is used only through WebMvcTest (the sanctioned HTTP-boundary mock), and the new ClinicServiceTests reach for the real repository/database instead of a stub.
- ./gradlew test passes for both files (VetControllerTests and ClinicServiceTests), consistent with the build-pass record.

**code-quality-reviewer**

- New test theMachineReadableVetListShouldBeEmptyWhenNoVetHoldsTheSpecialty follows existing BDD naming and four-phase structure, reuses the SPECIALTY_NO_VET_HOLDS constant instead of a fresh literal, and closes the JSON empty-result shape gap by asserting content type and array emptiness
- checkFormat passes; production code (VetController, VetRepository, vetList.html) is unchanged from the previously approved pass

**doc-reviewer**

- docs/system-design.md:103-104 Contracts table: prior blocked finding fully resolved — VetRepository and VetController rows now both cite REQ-VET-004 in Implements, and the VetRepository Purpose cell now scopes the caching claim ('The unfiltered reads are cached; the specialty-filtered ones are not') with a working ADR back-link instead of the inaccurate blanket 'results are cached'.
- Class sweep (grep -F 'results are cached', 'REQ-VET-004', 'pending removal', 'serves no requirement' across docs/) found no further instance of either finding class and no other stale caching or pending-removal claim.
- docs/prd.md: REQ-VET-003/REQ-VET-004 anchored, behavioral wording, Done-when bullets bounded, edge cases numbered and referenced consistently, NG-9 narrowing, Superseded REQ-VET-002 entry, and the revisited Open Question all read as history, not new rationale.
- docs/adr/2026-08-06-non-goal-veterinarian-search.md and docs/adr/2026-08-06-uncached-specialty-filtered-vet-queries.md: both carry Requirements:/Non-goal: Implementation lines, full options-considered/decision/consequences structure, and cross-links to prd.md, system-design.md, and security-principles.md all resolve to real anchors.
- docs/adr/README.md: both 2026-08-06 rows present in the index in the established table form.
- All cross-document links checked (prd.md#req-vet-003, #req-vet-004; system-design.md#contracts; both ADR relative paths) resolve to real anchors/files.

**test-reviewer**

- ClinicServiceTests exercises the real matching semantics (whole-name, case-insensitive, no-prefix-match, empty-result) against H2 for both the Page and Collection reads — correct layer split per the design record
- Edge cases 1, 2, and 4 (stable order pre-existing, empty-result 200, pagination on narrowed totals) are covered on both surfaces where applicable
- AssertJ used throughout ClinicServiceTests; test data naming follows the three-tier convention (RADIOLOGY, SPECIALTY_NO_VET_HOLDS named by role)
- No new mocking beyond the sanctioned MockMvc/MockitoBean-repository-stub pattern already established in this file

**security-reviewer**

- Injection: the specialty selector reaches the data store only through Spring Data derived queries (VetRepository.findBySpecialtiesNameIgnoreCase, Collection and Page overloads). Parameters are bound, not concatenated; the change set adds no @Query, no createQuery/createNativeQuery, and no native SQL. Re-verified by grep across src/main/java, not by recall.
- Cache poisoning mitigation holds: the two new caller-keyed reads carry no @Cacheable. The only @Cacheable sites in the tree remain VetRepository:45 and :55, both on the unfiltered findAll overloads, so an attacker cannot mint unbounded permanent entries in the eviction-less 'vets' cache by varying the request parameter. The rationale is recorded on the method Javadoc and in docs/adr/2026-08-06-uncached-specialty-filtered-vet-queries.md.
- Case-insensitivity is delivered by Spring Data's IgnoreCase keyword in the method name, not by a schema change or a database collation change. The change set touches no .sql, no build file, and no datasource configuration, so no cross-database matching divergence or DDL surface is introduced.
- XSS mitigation holds: every page link in src/main/resources/templates/vets/vetList.html uses the @{/vets.html(page=..., specialty=${specialty})} parameter form. Thymeleaf URL-encodes link parameters and HTML-escapes the resulting attribute value; no __${...}__ preprocessing appears anywhere in this template, so the reflected selector cannot break out of the href. Swept the whole templates/ tree for __${...}__, th:utext, and th:inline: the remaining preprocessing sites (fragments/, owners/) are pre-existing, outside this change set, and interpolate framework- or entity-supplied values rather than this request parameter. VetControllerTests#theVetListShouldCarryTheSpecialtyOnThePageLinks pins the escaped rendering (page=2&amp;specialty=radiology).
- Reflection surface: VetController.selectedSpecialty normalizes null/blank to null and otherwise passes the value through unchanged. The value reaches the response only as the escaped link parameter above; the JSON route (/vets) does not echo the selector at all, and the new empty-result test asserts a bare empty vetList array with no selector echo and no error text.
- Data exposure: filtering narrows the result set and cannot widen it. No new field is serialized on Vets/Vet, no exception or stack detail is surfaced on a non-matching specialty (the read returns an empty Page/Collection, rendered as an empty list), and no PII or credential-shaped value appears in the diff. Grepped the change set for token/password/secret/key-shaped literals: the only new constants are test specialty names (RADIOLOGY, SPECIALTY_NO_VET_HOLDS).
- Supply chain: the change set contains no build.gradle, lockfile, or dependency-descriptor change (scripts/changeset.sh --name-only confirms), so no new artifact or version enters the graph this pass and the CVE surface is unchanged from the previously approved state.
- Delta since the prior approval is one added test (VetControllerTests#theMachineReadableVetListShouldBeEmptyWhenNoVetHoldsTheSpecialty) plus a docs/system-design.md Contracts-table edit. Production code is byte-identical to the reviewed state; the added test introduces no new trust boundary and asserts the safe empty-response shape.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 4 | opus-5 | $6.42 | 13m 50s | 94% |
| `spring-boot-claude:system-design-expert` | 3 | opus-5 | $4.75 | 7m 21s | 89% |
| `(parent)` | 1 | opus-5 | $4.20 | 35m 18s | 95% |
| `spring-boot-claude:product-requirements-expert` | 1 | opus-5 | $2.50 | 4m 25s | 89% |
| `spring-boot-claude:security-reviewer` | 2 | opus-5 | $1.94 | 2m 12s | 79% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-5 | $1.54 | 2m 24s | 87% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-5 | $1.32 | 3m 45s | 82% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-5 | $1.09 | 1m 52s | 81% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-5 | $0.07 | 8s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $4.20 | 35m 18s | 95% |
| `spring-boot-claude:feature-implementer` | opus-5 | $3.54 | 8m 41s | 96% |
| `spring-boot-claude:product-requirements-expert` | opus-5 | $2.50 | 4m 25s | 89% |
| `spring-boot-claude:system-design-expert` | opus-5 | $2.33 | 3m 25s | 88% |
| `spring-boot-claude:system-design-expert` | opus-5 | $1.46 | 2m 25s | 92% |
| `spring-boot-claude:feature-implementer` | opus-5 | $1.06 | 1m 35s | 92% |
| `spring-boot-claude:security-reviewer` | opus-5 | $1.04 | 1m 16s | 82% |
| `spring-boot-claude:system-design-expert` | opus-5 | $0.97 | 1m 30s | 85% |
| `spring-boot-claude:feature-implementer` | opus-5 | $0.97 | 2m 13s | 92% |
| `spring-boot-claude:security-reviewer` | opus-5 | $0.89 | 56s | 75% |
| `spring-boot-claude:feature-implementer` | opus-5 | $0.85 | 1m 19s | 89% |
| `spring-boot-claude:doc-reviewer` | sonnet-5 | $0.82 | 1m 28s | 91% |
| `spring-boot-claude:test-reviewer` | sonnet-5 | $0.73 | 2m 25s | 84% |
| `spring-boot-claude:doc-reviewer` | sonnet-5 | $0.72 | 55s | 81% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-5 | $0.65 | 1m 15s | 86% |
| `spring-boot-claude:test-reviewer` | sonnet-5 | $0.59 | 1m 20s | 78% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-5 | $0.44 | 36s | 71% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-5 | $0.07 | 8s | 50% |

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

- plugin `spring-boot-claude` at `v0.1.29` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `610c2c59194e4044` · `2.1.222 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
