# vets-specialty-filter r3 — v0.4.4

Filter the vet list by specialty (feature) · started 2026-09-18T04:46:19+00:00 · exec `claude-dev` · status **complete**

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
| reading depth (pipeline grade) | skim |

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
| 4 (±1) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.58. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The filter sits in the right layer.  VetRepository  gains two derived queries,  findDistinctBySpecialtiesNameIgnoreCase , paged in the database, and the controller only normalizes the blank value in  namedSpecialty() , which counts as binding under the Web controller row. The template's shared  pageLink  fragment removes five nearly identical links. Tests use BDD names and named constants, derive expectations such as  RADIOLOGY_VET_LAST_NAMES.size() / oneVetPerPage , and cover whole-name matching, letter case, prefixes, empty results, blank values, and paging. Weaknesses: the  @ValueSource  literals ("%", "radiolog_") have no names, a comment explains the six expected link matches,  SECOND_PAGE  and  MIDDLE_PAGE  duplicate the value 2, and the private  findAll  reuses the repository method's name. On docs, the PRD's NG-9 row, the Superseded entry, the contracts table, the threat model and Known Defects are all updated, with no stale claim left.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The change fits the existing structure. VetController only normalizes the blank parameter (namedSpecialty via StringUtils.hasText), which the catalog classes as binding. Matching is done by derived queries in VetRepository (findDistinctBySpecialtiesNameIgnoreCase), and the ADR explains why those reads skip the cache. The Thymeleaf pageLink fragment removes repeated links, though its null branch adds some complexity. Tests follow the BDD naming style, derive expected values (RADIOLOGY_VET_LAST_NAMES.size()) and cover case, prefix, wildcard and blank edge cases. However, the new controller tests still use Mockito stubs, some tests check both surfaces at once, a comment explains the six-link count, and "everyFilteredVetDirectoryPageLink..." breaks the naming pattern. The docs are complete: NG-9 narrowed with its ADR, REQ-VET-004 added while REQ-VET-002 stays withdrawn, the known-defect row removed, and the contracts, threat model and open questions updated.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The design is sound. The filter lives in derived  VetRepository  queries ( findDistinctBySpecialtiesNameIgnoreCase ), paged in the database and deliberately uncached, with an ADR explaining why. The controller only normalizes blank values through  namedSpecialty , which the catalog counts as binding. The main weakness is that each handler now branches between  findAll  and the filtered query. The  pageLink  template fragment removes duplicated link markup but is fairly intricate. Tests use behavior names and cover case-insensitivity, the prefix case, empty results, blank values and page-link preservation. However,  @ValueSource  literals such as "%" and "radiolog_" are unnamed, several tests assert on both surfaces at once, and one test carries a narrating comment. The docs are thorough: NG-9 is narrowed with its own ADR, REQ-VET-004 is minted, the superseded REQ-VET-002 entry is annotated, the obsolete known-defect row is removed, and the contracts and threat model are updated.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $13.84 | 26m | 4 | 93% | 10 file(s) +377/−31 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.59 | 51s | 85% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Reader narrows the veterinarian directory to one specialty

2 review rounds · 2 build-passes · **1 build-failure** · grade **SKIM**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (1) | **✔** |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (2) | **✔** |

- ◇ **intake** Feature request: filter the vet list by specialty. Three product decisions come with it, made here as the product owner: - Non-goal NG-9 is narrowed: free-text veterinarian search stays out of   scope, but filtering the directory by an attribute it already shows is in.   Record the narrowing the way the project records non-goal changes. - The JSON endpoint at /vets is reinstated as a supported surface — this   filter is its first requested capability. Mint a fresh requirement for it;   the withdrawn REQ-VET-002 stays withdrawn and its id is not reused. - The filter is a URL contract only. Neither surface gains a form, dropdown,   or other page control in this request; pagination links carry the   parameter so filtered pages stay navigable. A visible control may come as   a follow-up request. Both vet list surfaces accept an optional `specialty` query parameter: - /vets.html?specialty=\<name> — the HTML page shows only vets holding that   specialty; pagination applies to the filtered list. - /vets?specialty=\<name> — the JSON endpoint returns only those vets. Matching is on the whole specialty name, case-insensitive — not a prefix. A specialty matching no vet yields the normal page or JSON document with an empty vet list (HTTP 200). An empty or whitespace-only value behaves as if the parameter were absent, like the empty owner search. Without the parameter both endpoints behave as today. Cover the new behavior with tests. These are all the product decisions; no further product answer will come during the work. Where a choice still seems open, take the narrowest reading consistent with this request and record the open question rather than waiting. · (3 decisions) · (human)
- ◇ **prd-entry** Reader narrows the veterinarian directory to one specialty · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **new** · (design) · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 8m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 27s***
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [autofix] `vetList.html:30,35,40,45,50` The same conditional expression `${specialty == null} ? @{/vets.html(page=X)} : @{/vets.html(page=X,specialty=${specialty})}` is repeated at all five page-link sites (first/prev/next/last plus the page-number loop), differing only in the page number. Thymeleaf's `@{...}` syntax does not omit a null-valued parameter on its own (renders `?specialty=` instead of dropping it), so the conditional itself is necessary, but five copies of the same branching logic is the duplication the checklist's Control Flow bullet names ("A conditional repeated across sibling sites ... is duplication: compute it once and reference it").
    - fix: Compute the specialty query-parameter fragment once with `th:with` (e.g. bind a single reusable expression or a small local variable holding whether specialty is present) and reference it at all five sites, or factor the five links into a Thymeleaf fragment parameterized by page number.
- ✎ **review doc** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `prd.md:196` Prohibited word "several" used without supporting data: "`REQ-VET-003` names one Specialty; naming several is undecided." (documentation-standards.md Prohibited Words list).
    - fix: Rephrase without the vague quantifier, e.g. "naming more than one Specialty at once is undecided."
  - [autofix] `2026-09-18-caller-named-vet-filters-by` The **Requirements:** field cites `REQ-VET-003` as bare text. Every other ADR's Requirements field that names a specific requirement links it to its PRD anchor, e.g. 2026-07-31-database-enforced-pet-name-uniqueness.md:36 uses `[`REQ-PET-002`](../prd.md#req-pet-002)`.
    - fix: Link the ID: `[`REQ-VET-003`](../prd.md#req-vet-003)`.
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `vetList.html:29-45` The specialty-carrying ternary (`${specialty == null} ? @{/vets.html(page=…)} : @{/vets.html(page=…,specialty=${specialty})}`) is duplicated across five link locations (the numbered page list, first, previous, next, last). `theFilteredVetDirectoryPageLinksShouldKeepTheSpecialty` exercises only the numbered-page-list branch (with `firstOfTwoPages()`, currentPage=1, so `first`/`previous` never even render). A copy-paste slip in the `next`, `last`, `first`, or `previous` branch (e.g. dropping the specialty clause) would ship undetected — no test would fail. This is a missing-test finding, not a defect found: extend the page-link fixture to a currentPage in the middle of >=3 pages so first/previous/next/last all render, and assert each carries the specialty parameter (or add a case per remaining link).
- ✚ **prd-autofix** `docs/prd.md` · writing-standards · (root)
- ✚ **doc-autofix** `docs/adr/2026-09-18-caller-named-vet-filters-bypass-the-cache.md` · writing-standards · (root)
- ↻ **implement** (implementer · routine) ← code-quality, test · (2 findings) · ***◷ 3m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 25s***
- ◇ **prd-entry** Reader narrows the veterinarian directory to one specialty · (prd-expert) · ***◷ 26s***
- ◈ **design-block** **new** · (design) · ***◷ 20s***
- ◆ **implement** (implementer) · ***◷ 40s***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ↻ **fix code-quality** ← doc · (2 findings)
- ✔ **review security** · **approved** · ***◷ 35s***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 1m***
- ◆ **grade SKIM** · filter the vet directory by one named specialty
  - blast_radius — **skim** — Code reach is the vet package only: two new uncached derived queries on VetRepository, an optional parameter on both VetController routes, and a vetList.html page-link refactor. No sensitive paths are touched. Most of the 47 hunks are PRD, system-design, and ADR prose. The unfiltered paths still call the same cached findAll methods.
  - semantic_surprise — **skim** — Reading the hunks turned up nothing unexpected. The blank check uses StringUtils.hasText and falls back to the old calls. The IgnoreCase query is an equality match, so the % and radiolog_ wildcard tests correctly return empty. The specialty only reaches the page through URL-encoding @{} links. The one unusual construct is a pageLink fragment defined inside a th:remove="all" span, which rewrites the existing unfiltered links too. Rendering tests pin both the filtered and unfiltered href forms.
  - test_adequacy — **skim** — build_passed is true. The repository tests run the real derived queries on H2 and check whole-name versus prefix matching, case folding, LIKE wildcards, the "none" word, distinct page totals, and that a match keeps all its specialties. The MockMvc tests check blank and whitespace fallback on both routes, the empty-match 200, and that all six rendered page links on a middle page keep an encoded specialty. These tests would fail against a broken implementation.
  - reviewer_hedging — **skim** — All four dispatched reviewers approved in round 2 with no findings and no recommendations. The round-1 changes_requested were three autofix-level items: template duplication, a link-coverage test gap, and doc wording. Each was addressed in the working tree.
  - scope_deviation — **skim** — The owner's intake decisions explicitly cover narrowing NG-9, minting REQ-VET-004 for the reinstated /vets surface, and dropping its known-defect row. design_revisions=1 and the single build-failure came from an autofix-audit process loop, not a design mismatch. Open questions such as surrounding spaces and multiple specialties are recorded, not implemented.
  - why — A contained, well-tested filter: unfiltered paths keep their cached calls, filtered reads use equality and are not cached, and every page link is checked to keep the encoded specialty. Reviewers approved cleanly and the scope shifts are owner-decided. A glance at VetController and the vetList.html fragment is enough.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Injection into data access: the request-supplied specialty reaches only Spring Data derived queries (VetRepository.java:  Collection\<Vet> findDistinctBySpecialtiesNameIgnoreCase(String specialtyName)  and the Pageable overload), which bind it as a parameter. No query text is built from it. ClinicServiceTests pins that LIKE metacharacters do not act as wildcards ( @ValueSource(strings = { "cardiology", "none", "%", "radiolog_" })  expects empty results).
- XSS and URL injection in vetList.html: the echoed specialty goes only into Thymeleaf link-expression parameters ( @{/vets.html(page=${i},specialty=${specialty})} ), which URL-encode the value and HTML-escape the attribute. VetControllerTests pins this with  SPECIALTY_NEEDING_URL_ENCODING = "oral & dental"  rendered as  oral%20%26%20dental  behind  &amp;specialty= . The change also removes the  __${...}__  preprocessing from the vet pagination links.  grep -F -e '__$' src/main/resources/templates/  no longer matches vetList.html; the remaining preprocessing sites (ownersList.html, ownerDetails.html, layout.html, the field fragments) are outside this change and carry no request text from this slice.
- Resource exhaustion: filtered reads carry no @Cacheable, so a caller who sends many different specialty names cannot grow the unbounded  vets  cache. The DB-side paged read keeps the HTML route bounded. The unpaged JSON route returns only the vets holding one specialty. The threat-model row and the ADR record this choice.
- Input handling: a blank specialty falls back to the unfiltered path ( StringUtils.hasText(specialty) ? specialty : null ). The parameter is a plain String @RequestParam with no @ModelAttribute or @RequestBody binding target, so mass assignment does not apply. No logging, file I/O, shell, or deserialization code is added.
- Credentials:  grep -E -i  over the added diff lines for password, secret, token, and api key returned no matches. build.gradle is not in the change set, so dependencies are unchanged.
- Supply chain:  ./gradlew dependencies  resolves Spring Boot 4.1.1, Thymeleaf 3.1.5.RELEASE, and tools.jackson jackson-databind 3.1.5. dependencyCheckAnalyze is not configured ( grep -F -e dependencyCheck build.gradle  gives no match), so this review ran no NVD match.

**code-quality-reviewer**

- VetController.java:64-88 — findPaginated/findAll delegate the null-vs-named branch cleanly to the repository, matching the design-block's derived-query plan (VetRepository.java:58-82, findDistinctBySpecialtiesNameIgnoreCase with IgnoreCase, no Containing/StartingWith/Like, confirmed by reading both files in full)
- VetRepository.java has no @Cacheable on either new findDistinctBySpecialtiesNameIgnoreCase method (grep -F -e "@Cacheable" src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java matches only the two existing findAll methods at lines 41 and 54), matching the ADR's caller-named-filter-bypasses-cache rule
- vetList.html page links use Thymeleaf @{...} parameter syntax exclusively (no __${...}__ preprocessing) for the specialty value, avoiding the template-injection pattern the design-block flagged

**doc-reviewer**

- All new requirement IDs (REQ-VET-003, REQ-VET-004) have HTML anchors in docs/prd.md:118 and are cited consistently in docs/system-design.md's Contracts, Scale and Load, and Threat Model rows (grep -F "REQ-VET-003" and "REQ-VET-004" across docs/prd.md and docs/system-design.md — every system-design.md occurrence has a matching prd.md requirement)
- Every new cross-reference resolves: docs/adr/2026-09-18-non-goal-narrow-veterinarian-search.md's links to ../prd.md#non-goals and ../prd.md#req-vet-003, and docs/adr/2026-09-18-caller-named-vet-filters-bypass-the-cache.md's links to ../system-design.md#contracts, #scale-and-load, and #threat-model, all resolve to headings/anchors present in the target files (grep -n "^## " docs/system-design.md and grep -n "id=\"req-vet-003\"" docs/prd.md)
- docs/adr/README.md's table gained exactly the two new ADR rows matching the two new ADR files, dated and titled consistently with the existing table format
- PRD additions stay behavioral: no framework/mechanism terms (e.g. "query parameter", "URL") leak into docs/prd.md's new Veterinarian directory prose; mechanism (StringUtils.hasText, findDistinctBySpecialtiesNameIgnoreCase) is confined to docs/system-design.md and the ADRs
- REQ-VET-002's withdrawal note in docs/prd.md:180 correctly records that REQ-VET-004 is a fresh ID rather than a reuse of the withdrawn REQ-VET-002, matching the PRD's ID-reuse rule
- docs/ubiquitous-language.md already defines "Specialty" (line 52); no new domain term was introduced without a definition
- New sentences in the added PRD paragraph (docs/prd.md:123) each run under 20 words (checked by splitting on sentence boundaries), meeting the sentence-length standard

**test-reviewer**

- Repository-boundary match semantics (whole-name, case-insensitive, no-prefix, unknown-name/'none'/wildcard-character non-match, distinct count, multi-specialty listing) are pinned once in ClinicServiceTests against the real Spring Data implementation and embedded H2 seed data (src/test/java/org/springframework/samples/petclinic/service/ClinicServiceTests.java:239-285), matching the design-block's repository-boundary assignment.
- VetControllerTests stubs VetRepository only to verify controller wiring (routing, blank-means-absent branch, model attributes, JSON shape, HTTP 200 on empty result) and never re-asserts match semantics through the mock, avoiding a repeated case table across the two suites.
- All 7 PRD Done-when bullets and both edge cases (2 'none'-as-name, 4 matching vet keeps every specialty) map to named, passing tests per  scripts/grading.py coverage-map --feature REQ-VET-003 .
- New tests reuse the suite's existing  james() / helen()  factories and named Tier-1/Tier-2 constants (RADIOLOGY, SPECIALTY_NO_VET_HOLDS, ANY_PAGE_SIZE, etc.) rather than raw literals or new constructors.
- ./gradlew test -q --tests "*VetControllerTests*" --tests "*ClinicServiceTests*" passed with no failures.

**security-reviewer**

- Injection into data access: the request-supplied specialty reaches the database only through the Spring Data derived queries  findDistinctBySpecialtiesNameIgnoreCase(String)  and  (String, Pageable)  (VetRepository.java, diff hunk @@ -55,4 +55,28 @@). These are bound parameters with no string-built query text. IgnoreCase derives an equality match, not LIKE, so the ClinicServiceTests cases  "%"  and  "radiolog_"  in theSpecialtyFilterShouldYieldAnEmptyListWhenNoVetHoldsIt show that wildcard characters get no special meaning.
- Output escaping: the only place the specialty is rendered is vetList.html:30  th:href="${specialty == null} ? @{/vets.html(page=${target})} : @{/vets.html(page=${target},specialty=${specialty})}" . The value is a link-expression parameter, which Thymeleaf URL-encodes and then attribute-escapes. everyFilteredVetDirectoryPageLinkShouldKeepTheSpecialty checks this with  oral & dental  rendering as  oral%20%26%20dental  behind  &amp; .  grep -rnF -e 'th:utext' src/main/resources/templates/  returned no hits.
- The change weakens no existing control and actually removes Thymeleaf preprocessing: the old vetList.html page links  @{'/vets.html?page=__${i}__'}  are replaced with parameterized link expressions.  grep -rnF -e '__${' src/main/resources/templates/  finds no remaining hit in vets/vetList.html. The hits that remain (ownersList.html, ownerDetails.html, the fragments) predate this change and render integers or template-fixed names, not request text.
- Cache-growth DoS is closed: the filtered reads carry no @Cacheable (VetRepository.java diff:  @Transactional(readOnly = true)  only), so caller-chosen names cannot grow the unbounded  vets  cache. This matches the system-design.md:194 threat-model row and the new ADR.
- Binding and mass assignment: the only new input is a scalar  @RequestParam(required = false) String specialty  on the two existing GET routes. No new @ModelAttribute or @RequestBody target is added, and no endpoint is added. Blank input becomes null through StringUtils.hasText (VetController.namedSpecialty), which keeps the unfiltered path. The filtered JSON route returns a subset of the already-unpaged unfiltered collection, so it adds no new unbounded read.
- No secrets are introduced: build.gradle and application*.properties are unchanged ( git diff --stat HEAD -- build.gradle pom.xml src/main/resources/application*.properties  is empty), and the diff adds no credential-like literals. Supply chain: this change touches no dependency. No NVD match ran in this review because dependencyCheckAnalyze is not configured ( grep -nF -e dependencyCheck build.gradle  returned no hits). Resolved versions from  ./gradlew dependencies --configuration runtimeClasspath : Spring Boot plugin 4.1.1 (build.gradle:5), jackson-databind 3.1.5 (tools.jackson.core), thymeleaf 3.1.5.RELEASE, hibernate-core 7.4.5.Final.

**code-quality-reviewer**

- VetController.namedSpecialty and its javadoc (VetController.java:90-96) centralize the blank-counts-as-absent normalization in one place, keeping showVetList and showResourcesVetList symmetric
- VetRepository derived query findDistinctBySpecialtiesNameIgnoreCase (VetRepository.java:58-80) follows Spring Data query-method naming, with javadoc explaining the deliberate no-cache decision (matches docs/adr/2026-09-18-caller-named-vet-filters-bypass-the-cache.md) rather than restating the code
- vetList.html's pageLink fragment (vetList.html:29-31) computes the specialty-preserving link once and is reused across all five pagination call sites, avoiding the repeated-conditional smell the checklist flags
- Naming (specialty, namedSpecialty, findDistinctBySpecialtiesNameIgnoreCase) matches docs/ubiquitous-language.md's Specialty/Veterinarian entries and none of its avoid-list terms
- Scope matches docs/prd.md REQ-VET-003 acceptance bullets exactly: whole-name case-insensitive match, blank-as-absent, no page control added, pagination preserves the filter — verified by reading prd.md lines 119-142
- ./gradlew checkFormat passed clean on the change set
- python3 scripts/grading.py conventions-map shows all 3 added production comment blocks (VetController.java:90-93, VetRepository.java:58-65,69-77) explain WHY (cache-bypass rationale, blank-as-absent rule), none restate the code

**doc-reviewer**

- Both round-1 doc-reviewer findings (line 15) are resolved: docs/prd.md:196 no longer uses "several" (now "naming two or more Specialty at once is undecided"), and the ADR's Requirements field links the requirement ( docs/adr/2026-09-18-caller-named-vet-filters-bypass-the-cache.md:35  reads  **Requirements:** [ REQ-VET-003 ](../prd.md#req-vet-003) ), matching the pattern in 2026-07-31-database-enforced-pet-name-uniqueness.md:36.
- New requirement IDs REQ-VET-003 and REQ-VET-004 both carry HTML anchors at docs/prd.md:119 ( \<a id="req-vet-001">\</a>\<a id="req-vet-003">\</a>\<a id="req-vet-004">\</a> ) and every occurrence in docs/system-design.md's Contracts (lines 102-104) and Scale and Load (line 127) rows matches a requirement defined in docs/prd.md (grep -n "REQ-VET-00[34]" across both files).
- Every new cross-reference resolves to a real heading or anchor: both new ADRs link ../system-design.md#contracts, #scale-and-load, #threat-model, and ../prd.md#req-vet-003/#non-goals, and  grep -n '^#' docs/system-design.md  confirms  ## Contracts  (line 72),  ## Scale and Load  (line 120), and  ## Threat Model  (line 180) all exist; docs/adr/README.md's table gained exactly the two new rows matching the two new ADR files, in the existing date/decision/status format.
- The withdrawn REQ-VET-002 entry (docs/prd.md:180) correctly states REQ-VET-004 is a fresh id, never a reuse, matching the PRD's id-reuse rule; the two Known Defects rows this slice resolves (the machine-readable route serving no requirement, and the old edge-case-2 'known defect' text) are both removed rather than left stale.
- The new PRD prose (docs/prd.md:121-136) stays behavioral: no framework or code term (query parameter binding, controller/repository names, Thymeleaf) leaks into the PRD; those terms are confined to docs/system-design.md and the ADRs. "Specialty" and "Veterinarian" are already defined in docs/ubiquitous-language.md (lines 50, 52), so no new undefined domain term was introduced.
- The new docs/system-design.md § Scale and Load section (line 120) opens with a Level-1-appropriate scoping paragraph before its table, consistent with the Structure Within a Document rules; no struct-field or parameter tables were added, and the new Contracts-row prose (VetRepository, VetController) stays at purpose-plus-source-pointer altitude rather than restating field/parameter shapes.
- No prohibited word or hard-wrapped line was introduced in either new ADR or in the changed PRD/system-design paragraphs (checked by line-length scan of both new ADR files and by rereading the diff hunks in docs/prd.md and docs/system-design.md).

**test-reviewer**

- Controller normalization rule (namedSpecialty blank-to-null) is tested at VetController, matching system-design.md line 104's explicit assignment of that rule to the boundary layer — not extracted or duplicated in ClinicServiceTests
- Query-behavior rules (whole-name case-insensitive match, prefix non-match, paging count over matches only, multi-specialty listing) are exercised at the repository seam in ClinicServiceTests via @DataJpaTest with the real database, not through the web layer
- VetControllerTests keeps one representative no-match case (SPECIALTY_NO_VET_HOLDS) while ClinicServiceTests carries the full @ValueSource case table (cardiology, none, %, radiolog_) for the same rule — correct client/collaborator split per testing-principles.md's tested-as-spec guidance, avoiding a repeated case table
- coverage-map --feature REQ-VET-003 shows 7/7 Done-when bullets covered (the one flagged missing, theFilteredVetDirectoryPageLinksShouldKeepTheSpecialty, is present under the name everyFilteredVetDirectoryPageLinkShouldKeepTheSpecialty in VetControllerTests.java:178 and asserts the page-link behavior the bullet names)
- All 5 prd.md edge cases for the veterinarian directory are covered: stable specialty order (pre-existing test at ClinicServiceTests.java:221-222, reused pattern at :283), name-not-a-specialty behaves as no-match (ValueSource case 'none' in theSpecialtyFilterShouldYieldAnEmptyListWhenNoVetHoldsIt matches the PRD's literal 'none' example), vet holding no specialty never matches (implicit via containsExactlyInAnyOrderElementsOf exhaustive assertion against the full DB), matching vet listed with every specialty held (theSpecialtyFilterShouldListAMatchingVetWithEverySpecialtyTheyHold), machine-readable directory stays unpaged (Vets is a bare list wrapper with no page fields, a structural guarantee)
- AssertJ fluent assertions used throughout with no JUnit assertEquals/assertTrue and no verify() calls (grep -F confirmed no matches in either changed test file); all new literals are named constants or locally-named variables (firstPageIndex, oneVetPerPage), and expected values (totalPages, page-link ordering) are derived from inputs rather than hard-coded
- ./gradlew test --tests "*VetControllerTests*" --tests "*ClinicServiceTests*" passes: BUILD SUCCESSFUL

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $4.05 | 13m 9s | 94% |
| `(parent)` | 1 | opus-5 | $2.57 | 27m 4s | 97% |
| `agent-team:system-design-expert` | 3 | opus-5 | $2.05 | 3m 23s | 88% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $1.43 | 2m 24s | 88% |
| `agent-team:security-reviewer` | 2 | opus-5 | $1.08 | 1m 19s | 86% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.07 | 4m 23s | 95% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.90 | 4m 54s | 92% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.65 | 2m 58s | 92% |
| `agent-team:change-grader` | 1 | opus-5 | $0.59 | 51s | 85% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $2.57 | 27m 4s | 97% |
| `agent-team:feature-implementer` | opus-5 | $2.57 | 8m 33s | 96% |
| `agent-team:system-design-expert` | opus-5 | $1.21 | 2m 21s | 91% |
| `agent-team:feature-implementer-routine` | opus-5 | $1.11 | 3m 45s | 93% |
| `agent-team:product-requirements-expert` | opus-5 | $0.95 | 1m 46s | 89% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.60 | 2m 39s | 96% |
| `agent-team:change-grader` | opus-5 | $0.59 | 51s | 85% |
| `agent-team:security-reviewer` | opus-5 | $0.56 | 43s | 86% |
| `agent-team:test-reviewer` | sonnet-5 | $0.52 | 2m 51s | 92% |
| `agent-team:security-reviewer` | opus-5 | $0.51 | 35s | 86% |
| `agent-team:product-requirements-expert` | opus-5 | $0.48 | 37s | 86% |
| `agent-team:system-design-expert` | opus-5 | $0.47 | 33s | 83% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.47 | 1m 43s | 94% |
| `agent-team:test-reviewer` | sonnet-5 | $0.38 | 2m 3s | 92% |
| `agent-team:feature-implementer` | opus-5 | $0.38 | 50s | 84% |
| `agent-team:system-design-expert` | opus-5 | $0.37 | 29s | 81% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.35 | 1m 33s | 93% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.31 | 1m 24s | 91% |

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

- plugin `agent-team-spring-boot` at `v0.4.4` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `0aff9592719d` (branch `agent-team`)
- task fingerprint `c3ceae64cf968297` · `2.1.274 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
