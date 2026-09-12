# vets-specialty-filter r1 — v0.4.0

Filter the vet list by specialty (feature) · started 2026-09-11T18:40:42+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 4 (±0) | 4 (±0) | 4 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.65. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The filtering is done by uncached derived queries on VetRepository (findDistinctBySpecialtiesNameIgnoreCase), and an ADR explains why. The controller only strips and blank-checks the value, which is the request normalization the design assigns to it. The template repeats the  ${specialty != null} ? @{...} : @{...}  ternary five times, which is copy-paste variance. Tests follow theXShouldY naming and phase spacing, and the repository tests run against real seed data. The new controller tests still use Mockito stubs where a real double could have served.  DIRECTORY_PAGE_SIZE  copies the controller's literal 5, flagged by a 'Mirrors' comment, which hides a coupling.  not(containsString("specialty"))  is a fragile assertion. The docs are thorough: an NG-9 ADR, the fresh REQ-VET-004, REQ-VET-002 kept withdrawn, the stale Known Defects row removed, and the Overview and threat model updated.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> The matching rule lives where it should: derived queries on VetRepository (findDistinctBySpecialtiesNameIgnoreCase), with an ADR explaining why they are uncached. The controller keeps only blank normalization.  specialty.strip()  plus the empty-check branch is duplicated across both handlers, and vetList.html repeats the same specialty ternary in five links. Tests follow the{Subject}Should{Outcome}, have clear phases, use named constants, and derive the page-count expectation. The controller tests still use Mockito stubs. DIRECTORY_PAGE_SIZE mirrors the controller's literal 5, a hidden coupling. The docs are thorough: NG-9 narrowed via ADR, REQ-VET-004 minted, REQ-VET-002 kept withdrawn, and the contracts and threat model updated. One stale count survives: the system-design provenance still says "four behaviors as defects" after the vet-route defect row was removed.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> Matching sits in  VetRepository  as the two derived queries  findDistinctBySpecialtiesNameIgnoreCase . They are uncached, and an ADR explains why. The controller only strips the value and delegates. However, the blank-check branch appears twice: once in  findPaginated  and again in the ternary in  showResourcesVetList . Tests use  theXShouldY  names, parameterized cases and named constants such as  RADIOLOGISTS . One weakness is  DIRECTORY_PAGE_SIZE : a comment says it 'mirrors the controller's page size', which is hidden coupling. The blank test also relies on the fragile  not(containsString("specialty")) . In  vetList.html , the  ${specialty != null} ? ... : ...  link ternary is copied five times. The docs are thorough: NG-9 is narrowed, REQ-VET-004 is minted, and the REQ-VET-002 entry, contracts and threat model are updated. One claim is stale: the provenance still says 'four behaviors as defects', but the vet-route defect row was removed.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $9.46 | 29m | 4 | 92% | 10 file(s) +365/−35 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.99 | 3m 11s | 83% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Veterinarian directory narrows to one named specialty

1 review round · 1 build-pass · grade **SKIM**

| reviewer | R1 |
| --- | --- |
| **code-quality** | **✔** |
| **test** | **✔** |
| **security** | **✔** |
| **doc** | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Veterinarian directory narrows to one named specialty · (prd-expert) · ***◷ 4m***
- ◈ **design-block** **minor** · (design) · ***◷ 7m***
- ◆ **implement** (implementer) · ***◷ 11m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
  - ▹ rec: vetList.html:30,35,40,45,50 repeats the same `${specialty != null} ? @{/vets.html(page=X,specialty=${specialty})} : @{/vets.html(page=X)}` ternary across all five pagination links. Pre-existing style already had one line per link, so this isn't a new duplication pattern, but it does make a future query-string change a five-site edit. Not blocking; worth a follow-up if the directory gains more query parameters.
- ✔ **review test** · **approved** · ***◷ 1m***
  - ▹ rec: Polish, non-blocking: theSpecialtyFilterShouldBeIgnoredWhenBlankOnTheDirectoryPage (VetControllerTests.java:186-189) asserts absence of the filter via content().string(not(containsString("specialty"))), a substring check over the whole rendered page rather than the more direct unfilteredLink()-based check the sibling pagination test already uses; works today only because the template's visible label is capitalized ('Specialties'), which is incidental rather than asserted.
  - ▹ rec: Polish, non-blocking: the ADR (docs/adr/2026-09-11-specialty-narrowing-as-uncached-repository-query.md) records the narrowed reads as deliberately uncached to avoid an unbounded cache-key risk; no test pins that absence (e.g. asserting repeated identical narrowed calls both reach the database/mock). Consider a follow-up test if the cache annotation is ever a plausible accidental re-addition.
- ◆ **grade SKIM** · narrow both vet list routes by a whole-name specialty
  - blast_radius — **skim** — Everything stays inside the vet feature: VetController, VetRepository, vetList.html, and their two test classes, plus owner-requested doc records. The new security-surface input reaches only bound derived-query parameters and URL-encoded Thymeleaf link parameters, which I checked in the hunks. The 45 hunks are mostly docs and test imports. The tree the reviewers saw (fa46501) is the tree graded here.
  - semantic_surprise — **skim** — The branch directions are correct: an empty name falls through to the cached findAll and a non-empty one to the narrowed read, on both routes. The query is IgnoreCase equality, never StartingWith or Like. The template adds a specialty only when the model attribute is non-null. The rewritten unfiltered links render the same /vets.html?page=N as the old __${i}__ form. The narrowed reads carry no @Cacheable, matching the ADR. One judgment call: stripping means a padded name like ' radiology ' matches. The PRD still lists this as an open question, but system-design.md records it as design.
  - test_adequacy — **skim** — Matching rules are tested against the real H2 repository and seed data: case variants, prefix rejection, no match, vets with no specialty, and the paged total counting only matches. Controller tests pin the exact PageRequest, the model attributes, the encoded filtered links, blank-means-absent on both routes, and the JSON body. Three gaps, none affecting today's behavior: no test pins that the narrowed reads stay uncached, no test checks that a padded non-blank name is stripped, and the unfiltered REQ-VET-001 links are not asserted after the template rewrite.
  - reviewer_hedging — **skim** — All four reviewers in the high-risk full-battery plan approved on the first pass with no findings. The test and code-quality recommendations are first-round polish: a brittle substring assertion, the untested uncached invariant, and a ternary repeated in five links. The missing OWASP scanner is a standing project gap. The citations I checked resolve (system-design.md:80/103/104/181, prd.md:119, the ADR at line 38, VetRepository.java:58-78); only the test reviewer's blank-test range drifts slightly.
  - scope_deviation — **skim** — The intake-decision states each doc change as the owner's decision: narrowing NG-9, reinstating /vets as REQ-VET-004 while REQ-VET-002 stays withdrawn, a URL-only contract, and pagination links carrying the parameter. The code adds no page control and no other filter attribute. Build retries, consultations, and design revisions are all 0.
  - why — The hunks match the owner's recorded contract: whole-name case-insensitive equality, blank means absent, uncached narrowed reads, and encoded pagination links. The tests exercise real outcomes. A glance is enough; to go further, confirm the NG-9 and REQ-VET-004 PRD wording and decide whether padded names should match.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**doc-reviewer**

- PRD REQ-VET-003 section (docs/prd.md:117-141) stays behavioral — no code identifiers, no mechanism tables; verified against boundary-rules.md's prohibited-pattern list
- Both new ADRs (docs/adr/2026-09-11-non-goal-veterinarian-search-narrowed.md, docs/adr/2026-09-11-specialty-narrowing-as-uncached-repository-query.md) carry the required Implementation line (Non-goal: NG-9 and Requirements: REQ-VET-003 respectively) and em-dash References sections
- docs/adr/README.md index (lines 73-74) lists both new ADRs, matching the file set on disk
- system-design.md Contracts rows for Vet, Specialty, Vets, VetRepository, VetController, CacheConfiguration (lines 100-105) cite REQ-VET-003/REQ-VET-004 consistently with docs/prd.md's anchors req-vet-001/003/004 (docs/prd.md:119), and the stale Known Defects row on the machine-readable route (grep of docs/system-design.md Known Defects table, lines 204-209) is absent, matching the design-block notes claiming its removal
- Cross-reference check: docs/prd.md#req-vet-003 anchor exists (docs/prd.md:119) and is the target of the ADR's PRD REQ-VET-003 link (docs/adr/2026-09-11-non-goal-veterinarian-search-narrowed.md:38); system-design.md's ADR links (lines 80, 103, 182) resolve to the two new ADR filenames present in docs/adr/
- Code cross-check: VetController.java and VetRepository.java (read in full) implement exactly the uncached, whole-name-ignoring-case, stripped-blank-means-absent behavior documented in system-design.md and prd.md; vetList.html pagination links (lines 30-50) carry the specialty parameter as a Thymeleaf link-expression parameter as documented
- docs/ubiquitous-language.md already defines Specialty and Veterinarian; no new domain term was introduced requiring a definition

**security-reviewer**

- Injection into data access: the request-derived specialty reaches the database only through the Spring Data derived queries findDistinctBySpecialtiesNameIgnoreCase(String) and findDistinctBySpecialtiesNameIgnoreCase(String, Pageable) (VetRepository.java diff), which bind the value as a parameter. The IgnoreCase keyword on a simple property is an equality match, not LIKE, so '%' and '_' carry no wildcard meaning (derived-query semantics, not exercised by a wildcard-specific test). The diff contains no @Query, createQuery, or nativeQuery (grep over the scripts/changeset.sh diff returned no such added line).
- Cross-site scripting on the directory page: vetList.html passes the specialty only as a link-expression parameter, e.g. line 30  @{/vets.html(page=${i},specialty=${specialty})} . Thymeleaf URL-encodes the parameter value and attribute-escapes the th:href output.  grep -F -e 'utext' -e '__$' -- src/main/resources/templates/vets/vetList.html  returns no match, so the change adds no unescaped output and no preprocessing of request text. It also removes the four old  __${...}__  preprocessing uses from the pagination links. VetControllerTests.theVetDirectoryPaginationLinksShouldNeverEchoAMarkupCarryingSpecialty sends the payload  ">\<img src=x onerror=alert(1)>  and asserts the response never contains it verbatim.
- Cache-key growth: both new repository methods carry no @Cacheable. Their Javadoc reads 'Uncached: the caller chooses the name, so it must never key the vets cache', so a caller cannot grow the unbounded vets cache by varying the specialty. The unfiltered paged read keeps its caching on page numbers, which system-design.md § Threat Model already records as Partial. The change does not extend that surface.
- Exposed surface and binding: the diff adds no route. It adds one optional @RequestParam String specialty (default "") to the two existing vet GET handlers, which only read data. It binds no @ModelAttribute or @RequestBody object, so no mass-assignment surface is added. system-design.md § Security Context (line 163) records the new input. The value is only stripped and length-bounded by the servlet container's request-line limit, which is adequate because every sink (bind parameter, encoded link) is safe for arbitrary text.
- Secrets and logging: the diff adds no credential, logger call, or System.out (grep for password secret token apikey credential log. logger System.out over the added lines of scripts/changeset.sh matched only the system-design.md prose line naming datasource credentials from environment variables). It also adds no new exception message that could reach the error page.
- Supply chain: build.gradle is not in the change set (scripts/changeset.sh --name-only), so no dependency changed. No OWASP dependencyCheckAnalyze task is configured (grep of build.gradle for dependencyCheck returned none), so no NVD match ran in this review. The resolved runtimeClasspath shows Spring Boot 4.1.1, jackson-databind (tools.jackson.core) 3.1.5, Thymeleaf 3.1.5.RELEASE, and Hibernate ORM 7.4.5.Final.

**code-quality-reviewer**

- Placement matches the catalog row: VetController.java:44-53,66-73,76-84 keeps the strip/blank-narrows-nothing rule in the controller, exactly where docs/system-design.md:104 assigns it ('The value is stripped, and a blank value narrows nothing, as in owner search')
- VetRepository.java:58-78 adds two uncached derived-query methods with javadoc explaining the uncached rationale, matching docs/system-design.md:80,103 and the ADR at docs/adr/2026-09-11-specialty-narrowing-as-uncached-repository-query.md
- vetList.html:30,35,40,45,50 pass specialty only through @{...(...)} link-expression parameters, never through template preprocessing/string concatenation, matching the XSS mitigation row in docs/system-design.md:181 and covered by VetControllerTests.java:170-177 (theVetDirectoryPaginationLinksShouldNeverEchoAMarkupCarryingSpecialty)
- Naming matches docs/ubiquitous-language.md:52 ('Specialty'); no coined synonym found via grep -F -e "specialty" -e "Specialty" across the changed production files
- Added comments (VetController.java:64-65, VetRepository.java:58-64,68-75) explain WHY (cache-safety, blank-means-absent convention) rather than restating the code, and carry no requirement ids per python3 scripts/grading.py conventions-map output
- ./gradlew checkFormat passed clean (BUILD SUCCESSFUL, both checkFormatMain and checkFormatTest UP-TO-DATE)

**test-reviewer**

- Matching semantics (whole-name, case-insensitive, prefix-excluded, no-specialty-never-matches, empty-result) are tested once at the repository seam in ClinicServiceTests against a real @DataJpaTest/H2 repository (src/test/java/org/springframework/samples/petclinic/service/ClinicServiceTests.java:232-266), matching testing-principles.md's pyramid placement rule and the design-block's assignment of matching semantics to VetRepository, not the controller.
- Controller tests (VetControllerTests.java:125-241) stay within their assigned scope — binding, stripping, blank-means-absent delegation, model attributes, pagination-link rendering, and JSON body — reusing the class's existing @MockitoBean VetRepository stub per the design-block's explicit sanction, rather than introducing a second double for the same boundary (docs/testing-principles.md Mocking Policy).
- Every PRD Done-when bullet and edge case for REQ-VET-003 has a covering test: python3 scripts/grading.py coverage-map confirms 9/10 declared test_names present; the one 'missing' name (theSpecialtyFilterShouldBeIgnoredWhenBlank) is a naming-tool artifact — the behavior is covered by two per-surface tests, theSpecialtyFilterShouldBeIgnoredWhenBlankOnTheDirectoryPage and theSpecialtyFilterShouldBeIgnoredWhenBlankOnTheVetListResource (VetControllerTests.java:213-227), each @ParameterizedTest over {"", "   "} for its own surface.
- A dynamic XSS-adversarial test exercises the threat the ADR and system-design.md Threat Model call out for the specialty value on pagination links: theVetDirectoryPaginationLinksShouldNeverEchoAMarkupCarryingSpecialty (VetControllerTests.java:168-176) asserts a markup-carrying specialty value never appears unescaped in the rendered page.
- AssertJ fluent assertions throughout, no JUnit assertEquals/assertTrue; test data follows the three-tier convention (RADIOLOGY, SPECIALTY_NO_VET_HOLDS, DIRECTORY_PAGE_SIZE named by role; RADIOLOGISTS/VETS_HOLDING_NO_SPECIALTY seed-data lists commented with a WHY note per legible-cold); expected totals in theFilteredDirectoryPageShouldCountOnlyVetsHoldingTheSpecialty are derived from RADIOLOGISTS.size() rather than hard-coded.
- ./gradlew test passes clean (BUILD SUCCESSFUL) including the full VetControllerTests and ClinicServiceTests classes.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 1 | opus-5 | $2.98 | 11m 37s | 94% |
| `agent-team:system-design-expert` | 1 | opus-5 | $2.19 | 7m 24s | 91% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.49 | 5m 17s | 87% |
| `agent-team:change-grader` | 1 | opus-5 | $0.99 | 3m 11s | 83% |
| `(parent)` | 1 | opus-5 | $0.90 | 31m 37s | 95% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.62 | 1m 14s | 86% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.47 | 2m 7s | 90% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.44 | 1m 32s | 95% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.37 | 1m 12s | 92% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $2.98 | 11m 37s | 94% |
| `agent-team:system-design-expert` | opus-5 | $2.19 | 7m 24s | 91% |
| `agent-team:product-requirements-expert` | opus-5 | $1.49 | 5m 17s | 87% |
| `agent-team:change-grader` | opus-5 | $0.99 | 3m 11s | 83% |
| `(parent)` | opus-5 | $0.90 | 31m 37s | 95% |
| `agent-team:security-reviewer` | opus-5 | $0.62 | 1m 14s | 86% |
| `agent-team:test-reviewer` | sonnet-5 | $0.47 | 2m 7s | 90% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.44 | 1m 32s | 95% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.37 | 1m 12s | 92% |

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
- task fingerprint `8a2138a7610e1d3e` · `2.1.268 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
