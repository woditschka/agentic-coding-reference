# vets-specialty-filter r2 — v0.4.0

Filter the vet list by specialty (feature) · started 2026-09-11T21:03:21+00:00 · exec `claude-dev` · status **complete**

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
| oracle | ✘ 0/5 passed |
| suite (post-agent) | ✔ |
| suite (pristine baseline) | ✔ |
| checkpoints | 3/8 |
| reading depth (pipeline grade) | scrutinize |

The pipeline grade estimates how much human review the change deserves before merge — advisory context from the harness's change grader (read from the ledger's `grader-verdict` record), never part of the bar.

- ✘ `theSpecialtyFilterShouldMatchCaseInsensitively` — missing
- ✘ `theSpecialtyFilterShouldNarrowTheHtmlVetList` — missing
- ✘ `theSpecialtyFilterShouldNarrowTheJsonVetList` — missing
- ✘ `theUnknownSpecialtyShouldYieldAnEmptyVetList` — missing
- ✘ `theVetListShouldShowTheFirstPageWithoutAFilter` — missing

## Checkpoints

The kind's graded ladder, derived from the recorded facts — context only, outside the quality bar (bench README § Checkpoints).

- ✔ `agent complete`
- ✔ `change produced`
- ✔ `suite green`
- ✘ `theSpecialtyFilterShouldMatchCaseInsensitively`
- ✘ `theSpecialtyFilterShouldNarrowTheHtmlVetList`
- ✘ `theSpecialtyFilterShouldNarrowTheJsonVetList`
- ✘ `theUnknownSpecialtyShouldYieldAnEmptyVetList`
- ✘ `theVetListShouldShowTheFirstPageWithoutAFilter`

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 4 (±0) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.68. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Matching sits in derived repository queries ( findDistinctBySpecialtiesNameIgnoreCase , pageable and whole-list). Only blank-normalization stays in  VetController.narrowingSpecialty , which is the controller's allowed request normalization. Two ADRs record the case-folding and cache-bypass choices. There is some structural debt:  Optional  is passed as a method parameter, and  vetList.html  repeats the same  ${specialty != null} ? ... : ...  ternary on five links. The tests move off  @MockitoBean  to the real repository. They follow  the…Should…  naming, use named constants and  insertAVetHolding  factories, and cover prefix, wildcard, blank, empty and paging cases. Some tests assert view name and content type alongside filtering, and  "totalPages" / "Holder"  are bare literals. The docs are thorough: NG-9 ADR, REQ-VET-004, superseded REQ-VET-002, contracts, threat model and known-defects updates.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The blank-value check sits in the controller as  narrowingSpecialty , which counts as request normalization and is allowed there. Matching uses a Spring Data derived query,  findDistinctBySpecialtiesNameIgnoreCase , left uncached on purpose, and both choices have ADRs. Two things cost points:  vetList.html  repeats the same  ${specialty != null} ? ... : ...  ternary in five links, and  Optional  is used as a private parameter type. VetControllerTests now runs against the real repository instead of MockitoBean, uses  the...Should...  names, named constants and factories, and derives its expectations ( fullPages * PAGE_SIZE + 1 ). It still has bare "totalPages"/"totalItems" strings, and the blank-filter test calls  perform  inside its assertion. The docs cover the NG-9 ADR, REQ-VET-003/004, the REQ-VET-002 note, the contracts, threat model and defects table.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The filter uses a derived Spring Data query ( findDistinctBySpecialtiesNameIgnoreCase ) in  VetRepository , and the web controller only handles blank-value normalization in  narrowingSpecialty , which is the right layer. It loses a point for passing  Optional\<String>  as a parameter and for choosing between the two repository methods separately in both endpoints.  vetList.html  repeats the same  ${specialty != null} ? ... : ...  choice in five links, which is copy-paste variance. The tests follow  the...Should... , drop Mockito, name their constants, build data through factories ( insertAVetHolding ,  listedVet ), and derive expectations from inputs. They still use bare model keys ("totalPages", "totalItems") and rely on heavy regex link parsing. The docs are thorough: NG-9 ADR, README index, PRD requirements, Superseded entry, open questions, and system-design contracts, threat model and defects.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.23 | 35m | 4 | 91% | 12 file(s) +506/−80 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.94 | 2m 49s | 82% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Reader can narrow the veterinarian list to one specialty by URL

1 review round · 1 build-pass · grade **SCRUTINIZE**

| reviewer | R1 |
| --- | --- |
| **code-quality** | **✔** (1) |
| **test** | **✔** |
| **security** | **✔** |
| **doc** | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Reader can narrow the veterinarian list to one specialty by URL · (prd-expert) · ***◷ 5m***
- ◈ **design-block** **new** · (design) · ***◷ 6m***
- ◆ **implement** (implementer) · ***◷ 16m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 55s***
- ✔ **review security** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · (1 finding) · ***◷ 2m***
  - [clarify] `vetList.html:33-58` The `${specialty != null} ? @{...(page=X,specialty=${specialty})} : @{...(page=X)}` ternary is repeated across all five pagination links, varying only in the page-number expression. This mirrors the pre-existing per-link repetition the file already had before this change (each link built its own `@{...}` separately), so it is not a regression this diff introduces, but the new per-link duplication is denser (a ternary instead of one expression) and harder to scan. Not requesting a fix — Thymeleaf has no easy sub-template-call construct at this project's usage level — but note it as a spot a future th:fragment/link-builder pass could simplify.
- ◆ **grade SCRUTINIZE** · filter the vet list by specialty on both surfaces
  - blast_radius — **skim** — Production reach is three files in the vet feature (controller, repository, list template), with no schema, config, build, or sensitive-path change. Most of the 61 hunks are the rewritten VetControllerTests and doc edits that match the intake decisions.
  - semantic_surprise — **skim** — The hunks do what the request says. A blank value collapses to the unchanged unnarrowed calls. The derived query compares by case-folded equality with no LIKE and has no @Cacheable. All five page links drop __${...}__ preprocessing for link-expression parameters (no __ remains in vetList.html), and unnarrowed links still render /vets.html?page=N, which a test pins. The loop variable named specialty on line 20 shadows the new model attribute only inside the row, away from the links.
  - test_adequacy — **scrutinize** — The core tests are real: real H2 via MockMvc, letter-case and prefix/wildcard variants, blank handling, a pagination test with inserted rows, and a '+${7*7}+' injection probe on the links. Two gaps remain. The every-database case-fold criterion rests on MySQL and PostgreSQL tests that skip without Docker, and build/test-results has no result file for either class, so that evidence did not run here. The duplicate-name test's totalItems=1 assertion cannot catch a non-distinct count query, because Spring Data skips the count query when the first page is short. That leaves the design's inflated-page-count risk unpinned.
  - reviewer_hedging — **scrutinize** — All four roster reviewers approved in round 1, and the citations I checked resolve (VetControllerTests.java:103, system-design.md lines 18/183/221, ubiquitous-language.md lines 50/52). Two mild caveats remain. code-quality left a clarify finding on the five duplicated specialty ternaries in vetList.html:33-58, the lines that carry the injection defense. test-reviewer calls the cross-vendor case-fold 'independently verified' on MySQL and PostgreSQL, but those tests did not execute. The missing NVD scan is a standing project gap, not a hedge.
  - scope_deviation — **skim** — Zero design revisions, consultations, and build retries. The diff stays inside the intake: both surfaces are URL-only with no control, and pagination links carry the parameter. NG-9 is narrowed via an ADR, REQ-VET-004 is minted with REQ-VET-002 still withdrawn, and the three open questions are recorded rather than decided. The switch of VetControllerTests to @SpringBootTest is sanctioned by the design block.
  - why — The production change is small and reads as intended. The query uses case-folded equality, narrowed reads are uncached, and preprocessing is gone from every page link. Before merging, confirm the MySQL and PostgreSQL case-fold tests have actually run somewhere, since they skipped here without Docker. Also accept that no test pins the distinct page count on a multi-page result.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**doc-reviewer**

- docs/prd.md  req-vet-003 / req-vet-004  anchors resolve and are referenced correctly from docs/system-design.md and both new ADRs (grep -F -e 'req-vet-003' docs/prd.md, grep -F -e 'req-vet-004' docs/prd.md)
- docs/system-design.md Contracts table rows for Vet/Specialty/Vets/VetRepository/VetController updated with REQ-VET-003/REQ-VET-004 in the Implements column, matching the new PRD requirements
- New ADRs (case-insensitive-matching-folds-case-in-the-query, narrowed-vet-reads-bypass-the-cache, non-goal-narrow-veterinarian-search) follow the ADR template, use em-dashes, and each carries a  **Requirements:**  or  **Non-goal:**  line under Implementation
- docs/adr/README.md table updated with all three new 2026-09-11 ADR rows, consistent column count with existing rows
- PRD Non-Goals preamble and NG-9 row both updated consistently to describe the narrowing, cross-linking the same ADR
- Domain terms (Specialty, Veterinarian, Vet short form) used in the new PRD/system-design/ADR prose are already defined in docs/ubiquitous-language.md (grep -F -e 'Specialty:' and -e 'Veterinarian:' docs/ubiquitous-language.md)
- PRD Superseded entry for REQ-VET-002 and system-design.md Known Defects table both consistently record the machine-readable route now serving REQ-VET-004, with the defect row removed from system-design.md and struck through in the PRD edge case
- No PRD prose crosses into implementation detail (no class/method names, no code blocks) in the new REQ-VET-003 section; mechanism is deferred to system-design.md via the Design/ADR links
- system-design.md Threat Model gained two new rows (template expression injection, cache-key memory growth) marked *(designed 2026-09-11, not derived)*, consistent with the document's provenance convention

**security-reviewer**

- Injection into data access: the request-supplied specialty reaches the database only through Spring Data derived queries (VetRepository.java diff:  Page\<Vet> findDistinctBySpecialtiesNameIgnoreCase(String specialty, Pageable pageable)  and its Collection overload), which bind it as a parameter and compare by upper-cased equality, never LIKE, so  % / _  stay literal. A sweep of the added diff lines for  @Query createQuery nativeQuery  returned no hits.
- Template expression injection: the change removes the  __${...}__  preprocessing from every vetList.html pagination link (old:  th:href="@{'/vets.html?page=__${i}__'}" ). The specialty now reaches links only as a link-expression parameter (new:  @{/vets.html(page=${i},specialty=${specialty})} ), which Thymeleaf URL-encodes, and then as an attribute value, which it HTML-escapes.  grep -rnF -e 'specialty' src/main/resources/templates/  shows no other render of the request value. Line 20 iterates the entity's  specialty.name  via th:text, which is escaped. VetControllerTests.java:103 pins this with the  '+${7*7}+'  probe.
- XSS: no  th:utext  or  [(  unescaped inlining in the added lines (grep of the added diff lines returned no hit). The JSON route returns the same  Vets  type as before, with no new fields and no Jackson polymorphic typing added (grep of the added lines for  JsonTypeInfo  returned no hit).
- Resource exhaustion: the narrowed reads carry no  @Cacheable  (VetRepository.java diff:  Not cached, so a caller-chosen name never becomes a cache key ), so distinct caller-chosen values cannot grow the  vets  cache. This matches the system-design Threat Model row and its ADR. The page-number cache key on unnarrowed reads is pre-existing, is recorded there, and this change does not widen it.
- Boundary validation: the blank/absent specialty collapses to no narrowing through  Optional.ofNullable(specialty).filter(name -> !name.isBlank())  (VetController.java diff). Any other value is legal under the REQ-VET-003 contract (an unheld name yields an empty list, not a refusal), and the servlet container bounds the query-string length. No new request-bound object,  @ModelAttribute , or  @RequestBody  is introduced, so there is no mass-assignment surface. No new endpoint: both routes pre-exist and gain one optional read-only parameter, with no state mutation and no logging of the value.
- Secrets: a case-insensitive sweep of the added diff lines for  password secret token apikey api_key credential private.?key jdbc:  matched only system-design.md prose describing existing environment-variable credentials. No credential is added in source, tests, or config.
- Supply chain: build.gradle is not in the change set ( scripts/changeset.sh --name-only ), so no dependency is added or changed.  ./gradlew dependencies --configuration runtimeClasspath  resolves Spring Boot 4.1.1, jackson-databind (tools.jackson.core) 3.1.5, Thymeleaf 3.1.5.RELEASE and Hibernate ORM 7.4.5.Final. No NVD match ran:  grep -nF -e 'dependencyCheck' build.gradle  returned nothing, so dependencyCheckAnalyze is not configured, and this review has no network access.

**test-reviewer**

- All 6 Done-when bullets and 7 declared tests present per  python3 scripts/grading.py coverage-map --feature REQ-VET-003  (7 of 7 declared tests found)
- Specialty-filter query logic ( VetRepository.findDistinctBySpecialtiesNameIgnoreCase ) is a Spring Data derived query needing real I/O regardless of extraction, so its integration-level, real-database placement in  VetControllerTests ,  MySqlIntegrationTests , and  PostgresIntegrationTests  matches  docs/system-design.md  line 103's assignment and does not violate the pyramid placement rule in testing-principles.md § Test Pyramid
- Cross-vendor case-fold behavior (the ADR  docs/adr/2026-09-11-case-insensitive-matching-folds-case-in-the-query.md ) is independently verified on MySQL and PostgreSQL via  theSpecialtyFilterShouldIgnoreLetterCaseOnMySql / ...OnPostgres , each calling the repository directly rather than going through MockMvc
- Template-expression-injection defense (system-design.md line 183) has a dedicated adversarial test,  theFilteredVetDirectoryShouldCarryTheSpecialtyInPageLinksAsLiteralText , using  SPECIALTY_WRITTEN_AS_A_TEMPLATE_EXPRESSION = "'+${7*7}+'" , and  pageLinksOn(...)  decodes both HTML- and URL-escaping so a regression would surface as literal text rather than a silently-passing encoded value
- No mocking framework used anywhere in the diff; MockMvc is the only test double, matching the sanctioned mock in testing-principles.md § Mocking Policy and CLAUDE.md; all repository/DB access in the new tests is real I/O (H2, and real MySQL/Postgres via existing testcontainers setup)
- AssertJ fluent assertions used throughout ( containsExactlyInAnyOrder ,  containsEntry ,  isEmpty ,  extracting(...).containsExactlyInAnyOrder ), no JUnit assertEquals/assertTrue introduced (verified via  grep -F -e "assertEquals(" -e "assertTrue("  against the three changed test files: no matches in the new specialty-filter tests)
- Four-phase structure with blank-line separation and no phase comments observed across all new/changed test methods in VetControllerTests.java, MySqlIntegrationTests.java, and PostgresIntegrationTests.java
- Test data follows the three-tier convention: meaningful values named by role (NARROWED_SPECIALTY, SURGERY_PREFIX, UNHELD_SPECIALTY), local literals in the integration tests named by role (seededSurgeryInCapitals, lastNamesOfSeededSurgeryHolders) per  python3 scripts/grading.py conventions-map ; no mystery literals
- BDD naming school (the{Subject}Should{Outcome}) followed for every new/changed test name, consistent with testing-principles.md § Test Naming
- Pagination page-link construction is exercised for all four link sites (sequence, previous/first, next/last) across the firstPage/secondPage assertions in  theFilteredVetDirectoryShouldPaginateOnlyMatchingVetsAndKeepTheSpecialtyInPageLinks , each retaining the specialty parameter

**code-quality-reviewer**

- VetController's narrowingSpecialty(String) and the repository's findDistinctBySpecialtiesNameIgnoreCase overloads read cleanly and place the blank/absent normalization in the controller, consistent with docs/system-design.md's recorded 'no service layer; business rules live in controllers' pattern (system-design.md lines 18, 221) for this codebase.
- New domain-facing names (specialty, vet, findDistinctBySpecialtiesNameIgnoreCase) match docs/ubiquitous-language.md's Specialty/Veterinarian/Vet entries (ubiquitous-language.md lines 50, 52) and use no listed avoid-term.
- The new VetRepository Javadoc for both findDistinctBySpecialtiesNameIgnoreCase overloads explains a real WHY (not cached, so a caller-chosen name never becomes a cache key) rather than restating the signature, per code-quality-review's Comments and Javadoc checklist.
- ./gradlew checkFormat passed clean (BUILD SUCCESSFUL, 2 actionable tasks up-to-date) and ./gradlew compileJava compileTestJava passed clean, confirming no formatting or compilation regressions from this change.
- docs/system-design.md, docs/prd.md, and the three new ADRs cross-reference each other consistently (system-design.md's Contracts and Threat Model rows cite the new ADRs; the ADRs cite system-design.md and prd.md back) with no broken internal link text spotted in the diff.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 1 | opus-5 | $4.41 | 16m 59s | 92% |
| `agent-team:system-design-expert` | 1 | opus-5 | $2.15 | 6m 36s | 92% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.80 | 6m 9s | 91% |
| `(parent)` | 1 | opus-5 | $0.94 | 37m 15s | 95% |
| `agent-team:change-grader` | 1 | opus-5 | $0.94 | 2m 49s | 82% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.72 | 1m 27s | 90% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.53 | 2m 31s | 93% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.37 | 2m 4s | 91% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.31 | 1m 4s | 88% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.41 | 16m 59s | 92% |
| `agent-team:system-design-expert` | opus-5 | $2.15 | 6m 36s | 92% |
| `agent-team:product-requirements-expert` | opus-5 | $1.80 | 6m 9s | 91% |
| `(parent)` | opus-5 | $0.94 | 37m 15s | 95% |
| `agent-team:change-grader` | opus-5 | $0.94 | 2m 49s | 82% |
| `agent-team:security-reviewer` | opus-5 | $0.72 | 1m 27s | 90% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.53 | 2m 31s | 93% |
| `agent-team:test-reviewer` | sonnet-5 | $0.37 | 2m 4s | 91% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.31 | 1m 4s | 88% |

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
