# vets-specialty-filter r2 — v0.4.1

Filter the vet list by specialty (feature) · started 2026-09-12T22:50:26+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.67. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The filtering uses derived  VetRepository  queries ( findDistinctBySpecialtiesNameIgnoreCase ), left uncached on purpose. The controller's  isNarrowing  only normalizes the parameter, which the catalog counts as binding, not a business rule. The template's weak spot is copy-paste: five  ${narrowed} ? @{...specialty...} : @{...}  ternaries. Tests drop  @MockitoBean  for the real repository and use  the{Subject}Should{Outcome}  names with named constants. They cover case, prefix, blank, no-match, pagination and link encoding. Minor issues: narration comments (the seed-data note, the 'appears three times' note), the hard-coded  SECOND_PAGE_AS_LINKED_TODAY , a bare  1  in  rangeClosed , and heavy regex/JSON parsing helpers. The docs are fully current: the NG-9 row, the ADR and its index, REQ-VET-004 in the Superseded list, the Overview, the contracts table, the threat model, and the removed Known Defects row.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The change sits in the right layers. VetController normalizes the blank value with StringUtils.hasText, which counts as binding. The matching lives in the derived VetRepository.findDistinctBySpecialtiesNameIgnoreCase methods, which are uncached on purpose. It has some duplication: isNarrowing is checked in both showVetList and findPaginated, and vetList.html repeats a narrowed ternary on all five links. The tests use the real repository instead of Mockito, follow the{Subject}Should{Outcome} naming, and use named constants. They also depend on seed-data vets (DOUGLAS, ORTEGA), parse HTML with a regex, and hard-code PAGE_SIZE=5. The documentation is thorough: an NG-9 ADR, the README index, REQ-VET-003/004, the superseded list, and system-design contracts and threats. The stale known-defect row was removed.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The filter uses Spring Data derived queries ( findDistinctBySpecialtiesNameIgnoreCase , paged and unpaged, both uncached) in VetRepository. The controller only treats a blank value as absent via  isNarrowing , which the catalog counts as binding. That is the right layer. Two weaknesses: the private  findAll(String)  in the controller shadows the repository method name, and the template repeats the same ternary href five times. The tests now run against the real repository instead of MockitoBean stubs. They use BDD names, named constants, the  createAVetHolding  factory and whole-record  VetListing  comparisons. They lean on regex parsing of the HTML and bare JSON key literals in helpers. The docs stay current throughout: the NG-9 ADR and its index row, REQ-VET-003/004, the superseded REQ-VET-002 entry, the contracts table, the threat model and the removed known defect.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $12.22 | 38m | 9 | 92% | 8 file(s) +458/−88 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.10 | 2m 52s | 85% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can narrow the veterinarian list to one specialty

2 review rounds · 2 build-passes · grade **SKIM**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (2) | **✔** |
| **test** | **✔** | · |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- ◇ **intake** Feature request: filter the vet list by specialty. Three product decisions come with it, made here as the product owner: - Non-goal NG-9 is narrowed: free-text veterinarian search stays out of   scope, but filtering the directory by an attribute it already shows is in.   Record the narrowing the way the project records non-goal changes. - The JSON endpoint at /vets is reinstated as a supported surface — this   filter is its first requested capability. Mint a fresh requirement for it;   the withdrawn REQ-VET-002 stays withdrawn and its id is not reused. - The filter is a URL contract only. Neither surface gains a form, dropdown,   or other page control in this request; pagination links carry the   parameter so filtered pages stay navigable. A visible control may come as   a follow-up request. Both vet list surfaces accept an optional `specialty` query parameter: - /vets.html?specialty=\<name> — the HTML page shows only vets holding that   specialty; pagination applies to the filtered list. - /vets?specialty=\<name> — the JSON endpoint returns only those vets. Matching is on the whole specialty name, case-insensitive — not a prefix. A specialty matching no vet yields the normal page or JSON document with an empty vet list (HTTP 200). An empty or whitespace-only value behaves as if the parameter were absent, like the empty owner search. Without the parameter both endpoints behave as today. Cover the new behavior with tests. These are all the product decisions; no further product answer will come during the work. Where a choice still seems open, take the narrowest reading consistent with this request and record the open question rather than waiting. · (3 decisions) · (human)
- ◇ **prd-entry** Staff can narrow the veterinarian list to one specialty · (prd-expert) · ***◷ 5m***
- ◈ **design-block** **minor** · (design) · ***◷ 6m***
- ◆ **implement** (implementer) · ***◷ 15m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 2m***
- ✎ **review code-quality** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `VetController.java:40` `PAGE_SIZE` was widened from a private local variable in `findPaginated` to a package-private static field solely so `VetControllerTests` can read `VetController.PAGE_SIZE` (the only other reference, at VetControllerTests.java:123,125). This is the placement smell the code-quality-review skill names directly: a helper widened for test access instead of testing through the sanctioned seam.
    - fix: Revert `PAGE_SIZE` to a private (or local) constant in `VetController`, and give `VetControllerTests` its own local constant for the expected page size (e.g. a private `PAGE_SIZE = 5`) instead of reaching into `VetController.PAGE_SIZE`.
  - [autofix] `vetList.html:32,38,44,50,56` The `${specialty == null} ? @{...} : @{...}` conditional is repeated identically at all five pagination-link sites added by this diff (the page-number loop plus first/previous/next/last), each differing only in the page value. Confirmed necessary in principle — Thymeleaf renders a null `@{}` parameter as a bare `specialty=` rather than omitting it (thymeleaf/thymeleaf#846), which is why the ternary exists — but its boolean condition is duplicated across all five sibling sites rather than computed once, the exact case the code-quality-review checklist's Control Flow section calls out.
    - fix: Compute the condition once with `th:with="narrowed=${specialty != null}"` on the enclosing `\<div th:if="${totalPages > 1}">` and reference `${narrowed}` at each of the five link sites instead of repeating `${specialty == null}` inline.
- ↻ **implement** (implementer · routine) ← code-quality · (2 findings) · ***◷ 2m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 5s***
- ◆ **grade SKIM** · narrow the vet list surfaces by an optional specialty parameter
  - blast_radius — **skim** — Contained to the vet feature package: two optional request parameters in VetController, two uncached derived reads in VetRepository, the pagination block of vetList.html, and the slice's own docs. No sensitive paths. The two security-surface files carry a new caller-supplied value, but it reaches SQL only as a bound derived-query parameter and HTML only as a URL-encoded link-expression parameter. The 52 hunks sit mostly in the test rewrite and the docs.
  - semantic_surprise — **skim** — Read every prod hunk. The blank check (StringUtils.hasText) gates both the query choice and the model attribute. The derived query is an upper-equality match, so it covers the whole name and never acts as a prefix. Distinct also applies to the page count. The fix-round th:with keeps the right polarity (narrowed = specialty != null selects the specialty-bearing link). The unnarrowed hrefs switch from __${}__ preprocessing to link expressions but render the same, and a test pins that. The known asymmetries are recorded as PRD open questions, not hidden: surrounding spaces are not stripped, and a repeated parameter binds comma-joined.
  - test_adequacy — **skim** — The tests drive the real repository on seeded H2 through MockMvc. They assert outcomes: case variants, a prefix that must miss, empty and unknown names, blank and whitespace pages byte-identical to absent, narrowed totalPages and totalItems over persisted rows, links round-tripping 'ear, nose & throat', and unnarrowed links unchanged. One small gap: containsOnlyOnce(DOUGLAS) cannot tell whether Distinct is present, because duplicates would need case-variant specialty rows that no app path creates.
  - reviewer_hedging — **skim** — All four reviewers approved. Code-quality's round-1 findings were two autofix polish items, and it re-approved them on the fix delta. The focused fix-delta roster left the other three reviewers out as expected. The cited lines I checked resolve (VetRepository.java:45/55, VetControllerTests.java:123, vetList.html:32). Round 2 listed line 26 among the link sites instead of 56, which is a harmless miscount. The security reviewer's note that the NVD check did not run restates a standing unconfigured-scanner gap, so it is context.
  - scope_deviation — **skim** — Zero retries, consultations, and design revisions. The diff stays within the prd-entry file targets plus the three documentation outcomes the owner asked for: the NG-9 narrowing ADR and its index row, the REQ-VET-004 requirement for the reinstated JSON route, and the successor text for REQ-VET-002. No page control was added, no search beyond specialty was added, and the unnarrowed behavior is pinned.
  - why — Every prod hunk is contained and I checked it against the request. The new input is parameterized into SQL and URL-encoded into links, blank handling matches absent byte-for-byte, and the fix-round template polarity is correct. The tests hit the real repository. A glance at the PRD wording that records the owner's decisions is enough.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Injection into data access: the request-supplied specialty reaches the database only through Spring Data derived queries (VetRepository.java:  Collection\<Vet> findDistinctBySpecialtiesNameIgnoreCase(String specialtyName)  and its Pageable overload). These are bound parameters with no string-concatenated query text, which matches the security-principles.md injection control.
- Cross-site scripting / output escaping: the specialty is echoed only in the pagination links, as a link-expression parameter (vetList.html:32  @{/vets.html(page=${i},specialty=${specialty})} , and lines 38/44/50/56 likewise). Thymeleaf URL-encodes the value and attribute-escapes the th:href output. The path stays fixed, so no javascript:/data: scheme can be injected. A grep for  th:utext  across src/main/ found nothing, and VetControllerTests round-trips the value 'ear, nose & throat' through the links.
- Template-expression evaluation: the change removes the  __${...}__  preprocessing from every vetList.html pagination link.  grep -rn -F '__${' src/main/  now lists only owner/layout fragments that the change did not touch, all over server-side values. No request-supplied text enters preprocessing.
- Resource exhaustion via caller-chosen cache keys: the new narrowed reads carry only  @Transactional(readOnly = true)  and no  @Cacheable . VetRepository.java:45/55 shows  @Cacheable("vets")  only on the two pre-existing findAll methods. So a caller cannot grow the unbounded 'vets' cache (CacheConfiguration.java:37) with arbitrary specialty names. The page-number keying that remains was already there and is recorded in system-design.md's threat model.
- Exposed surface: no new route. The optional  specialty  parameter narrows the existing /vets.html and /vets responses to a subset of data those routes already return. No request binding target (@ModelAttribute/@RequestBody) is added, so mass assignment does not apply.
- Blank or absent specialty handling fails safe to the unfiltered read ( StringUtils.hasText ). A non-matching or over-long name produces an empty list, not an error, so no exception message carrying the value reaches the error page.
- No secrets, logging, file I/O, shell execution, or deserialization in the diff. A grep for  JsonTypeInfo / enableDefaultTyping  in src/main/ found nothing.
- Supply chain: the change set has no build files ( git status --short -- build.gradle settings.gradle gradle/  is empty).  ./gradlew dependencies --configuration runtimeClasspath  resolves Spring Boot 4.1.1 (spring-boot-thymeleaf), jackson-databind 3.1.5, Thymeleaf 3.1.5.RELEASE and Hibernate 7.4.5.Final. No NVD match was run, because dependencyCheckAnalyze is not configured and this review has no network access.

**doc-reviewer**

- docs/adr/2026-09-12-non-goal-veterinarian-search-narrowed.md follows the non-goal ADR template (Non-goal: NG-9 in Implementation, em-dash References-equivalent PRD links) and docs/adr/README.md's index row links it correctly (README.md:73)
- PRD (docs/prd.md:119-142) stays behavioral: no code/type/method names, no framework constructs, rationale kept out and linked via the ADR only; anchors req-vet-001/003/004 all present and all REQ-VET-003/004 citations in system-design.md resolve to prd.md entries (grep confirmed)
- REQ-VET-002 withdrawal entry and Open Questions entry both updated consistently to name REQ-VET-004 as successor, and no stray REQ-VET-002 reference remains in system-design.md (grep -n "REQ-VET-002" docs/system-design.md docs/prd.md: only prd.md:178 and prd.md:187, both Superseded/Open-Questions entries)
- system-design.md Contracts, Persistence, Security Context, and Threat Model updates match the shipped code: VetRepository.java's findDistinctBySpecialtiesNameIgnoreCase overloads are uncached IgnoreCase derived queries as claimed; VetController.java's isNarrowing/blank-as-absent behavior matches the Contracts row; vetList.html builds every pagination link via th:href link-expression parameters (@{/vets.html(page=...,specialty=${specialty})}), matching the XSS-mitigation claim
- Known Defects row for 'the machine-readable veterinarian route serves no requirement' was removed now that REQ-VET-004 covers it (system-design.md diff hunk at Known Defects), and the Overview/Inputs/Outputs prose was updated to match
- docs/ubiquitous-language.md already defines Specialty and Veterinarian; no new domain term was introduced needing a definition
- python3 scripts/doctor.py check: 0 failure(s), 61 check(s), including cross-doc REQ-ID citation and field-table checks

**test-reviewer**

- VetControllerTests.java moved off Mockito/@WebMvcTest to a real @SpringBootTest + real VetRepository on the embedded H2 seed data, with MockMvc as the sole (sanctioned) transport double — verified by grep -n "Mockito\ mock(\ MockitoBean\ @Mock" over the file returning no matches (testing-principles.md § Mocking Policy).
- Matching logic (whole-name, case-insensitive, distinct) lives in VetRepository derived queries, not the controller; VetController.java:51/69/85/95 shows only blank-to-absent normalization at the boundary, consistent with system-design-expert's design-block placement call and architecture-principles.md § Pattern Catalog Web-controller row — no repository-level unit test exists anywhere in this codebase (find src/test -iname '*Repository*' returns nothing), so testing the derived query only through the controller/MockMvc seam is consistent-with-codebase, not a placement gap.
- python3 scripts/grading.py coverage-map --feature REQ-VET-003 reports 8 of 8 declared Done-when tests present covering all 7 Done-when bullets, and all 3 group edge cases are covered or pre-existing (edge case 1, stable specialty order, predates this slice and is untouched by the diff).
- jacoco HTML report (build/reports/jacoco/test/html/org.springframework.samples.petclinic.vet/index.html) shows 100% instruction and branch coverage for VetController, Vet, Vets, and Specialty after this slice's tests, exceeding testing-principles.md § Coverage's 80% target.
- theVetDirectoryPageLinksShouldCarryTheSpecialty exercises all five pagination-link Thymeleaf expressions changed in vetList.html (page-number, first, previous, next, last) in one assertion, using a specialty value containing comma and ampersand (SPECIALTY_NAME_NEEDING_ENCODING = "ear, nose & throat") to guard against the injection/XSS risk the design-block named for link-expression construction; theUnnarrowedVetDirectoryPageLinksShouldCarryOnlyThePageNumber guards the REQ-VET-001 'behave as today' bullet by asserting no specialty leaks into unfiltered links.
- All assertions are AssertJ fluent style (grep -n 'assertEquals\ assertTrue\ assertFalse\ Assertions.assert' over the file matches only the assertThat import); test data follows the three-tier convention (SURGERY/DENTISTRY as meaningful, ANY_FIRST_NAME/UNSEEDED_SPECIALTY as irrelevant-but-named, DOUGLAS/ORTEGA as derived whole-object expectations built from the same seed-data constants used elsewhere in the file); object construction goes through factory methods (persistASpecialtyNamed, createAVetHolding) per python3 scripts/grading.py conventions-map, whose only direct 'new Vet()'/'new Specialty()' calls are inside those factories.
- Four-phase structure (arrange/act/assert, blank-line separated, no phase comments) and BDD naming (the{Subject}Should{Outcome}) hold across every test in the file, including the two pre-existing tests renamed because this slice touched them.

**code-quality-reviewer**

- VetController.isNarrowing and the two findDistinctBySpecialtiesNameIgnoreCase overloads land in the layers docs/system-design.md assigns them (VetController.java:95-97; VetRepository.java:65-66,73-75), matching the catalog row 'The reads narrowed to one specialty match its whole name regardless of letter case, return each veterinarian once, and are uncached' (docs/system-design.md:103)
- New naming ('specialty', 'Vet', 'Veterinarian') matches docs/ubiquitous-language.md:50,52 with no coined synonyms
- The change stays within the REQ-VET-003 acceptance bullets in docs/prd.md:129-135 and the narrowed NG-9 non-goal (docs/adr/2026-09-12-non-goal-veterinarian-search-narrowed.md) — no free-text veterinarian search or UI control was added
- ./gradlew checkFormat passes clean

**code-quality-reviewer**

- PAGE_SIZE reverted to a local constant in VetController.findPaginated (VetController.java, fix delta) and VetControllerTests now defines its own local PAGE_SIZE=5 constant (VetControllerTests.java:123) instead of reaching into VetController -- the widened-for-test-access smell from round 1 is gone
- vetList.html now computes the narrowing condition once via th:with="narrowed=${specialty != null}" on the enclosing div and references ${narrowed} at all five pagination-link sites (lines 26,32,38,44,50) instead of repeating ${specialty == null} inline -- the round-1 duplication finding is resolved
- ./gradlew checkFormat passes clean

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $4.92 | 18m 32s | 92% |
| `agent-team:system-design-expert` | 1 | opus-5 | $2.02 | 6m 55s | 91% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.76 | 5m 51s | 91% |
| `(parent)` | 1 | opus-5 | $1.13 | 40m 33s | 96% |
| `agent-team:change-grader` | 1 | opus-5 | $1.10 | 2m 52s | 85% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.70 | 3m 32s | 94% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.68 | 1m 22s | 81% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.51 | 2m 27s | 93% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.45 | 1m 43s | 95% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.15 | 15m 45s | 92% |
| `agent-team:system-design-expert` | opus-5 | $2.02 | 6m 55s | 91% |
| `agent-team:product-requirements-expert` | opus-5 | $1.76 | 5m 51s | 91% |
| `(parent)` | opus-5 | $1.13 | 40m 33s | 96% |
| `agent-team:change-grader` | opus-5 | $1.10 | 2m 52s | 85% |
| `agent-team:feature-implementer-routine` | opus-5 | $0.77 | 2m 47s | 92% |
| `agent-team:security-reviewer` | opus-5 | $0.68 | 1m 22s | 81% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.54 | 3m 1s | 94% |
| `agent-team:test-reviewer` | sonnet-5 | $0.51 | 2m 27s | 93% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.45 | 1m 43s | 95% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.16 | 31s | 91% |

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

- plugin `agent-team-spring-boot` at `v0.4.1` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `0aff9592719d` (branch `agent-team`)
- task fingerprint `c3ceae64cf968297` · `2.1.269 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
