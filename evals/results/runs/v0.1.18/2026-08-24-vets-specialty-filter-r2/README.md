# vets-specialty-filter r2 — v0.1.18

Filter the vet list by specialty (feature) · started 2026-08-24T20:28:53+00:00 · exec `claude-dev` · status **complete**

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
| review attention (pipeline grade) | clear |

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
| 3 (±0) | 3 (±1) | 4 (±0) | 4 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.60. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 3 · test-quality 4 · maintainability 4 · doc-fit 4

> The filter predicate and hand-rolled paging ( filterBySpecialty ,  start/end/subList ,  new PageImpl\<> ) add a new business rule to  VetController , which the checklist calls a fresh violation not covered by the recorded deviation; the ADR names the departure and its vendor-case-folding reason, which mitigates but does not erase it. Tests are BDD-named ( theVetListJsonShouldNotMatchASpecialtyPrefix ) and cover case, prefix, blank, whitespace, unknown, and paging-link carryover, but rely on bare literals ("radiology",  setId(2) ) and undervived counts ( hasSize(1) ), and  sixSurgeons()  re-stubs the shared  setup()  fixture. Docs are unusually complete: NG-9 narrowed, REQ-VET-003/004 minted, superseded note updated, defect row removed, vocabulary and two ADRs added; the  Vets  contract row still reads Implements  — .

**Sample 2** — design-fit 3 · test-quality 3 · maintainability 4 · doc-fit 4

> The filter and in-memory paging land entirely in VetController (findPaginated/filterBySpecialty), adding a new business rule to a layer the catalog forbids it in; the available Domain service pattern would have satisfied the vendor-uniformity argument the ADR makes, so the recorded departure is documented but avoidable — hence the pyramid gap widens with no unit test. Tests are well named (theVetListHtmlShouldNotMatchASpecialtyPrefix) and phase-clean, but expectations are bare counts (hasSize(1)) whose meaning hides in setup()'s james()/helen(), specialty literals like "radiology"/"rad" are mystery values, and surgeon() hard-codes setId(2). Documentation is thorough — NG-9 narrowing, REQ-VET-003/004, superseded note, two ADRs, vocabulary entry — but system-design still marks Vets as serving no requirement.

**Sample 3** — design-fit 3 · test-quality 3 · maintainability 4 · doc-fit 4

> The filter predicate and in-memory paging land in VetController.findPaginated/filterBySpecialty — a new business rule in a controller, which the checklist calls a fresh violation not covered by the existing deviation. An ADR exists, but it weighs only 'repository query vs controller' and never considers the sanctioned Domain service, nor names the Web controller pattern departed from. Implementation itself is clean: one shared helper, both surfaces normalized identically, pagination links carry the parameter. Tests are well-named BDD specs covering every stated behavior, but rely on bare literals ('radiology', 'rad', setId(2), sixSurgeons) with no named constants, and HTML cases assert only hasSize(1) — a wrong-but-same-count result would pass. Documentation is thorough: PRD, superseded entry, contracts row, defect removal, vocabulary, two ADRs.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $9.11 | 31m | 23 | 91% | 9 file(s) +261/−20 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.38 | 1m 8s | 78% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-004 — Filter the veterinarian directory by specialty on both the page and the machine-readable route

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** (1) | · |
| **test** | ✎ (6) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- ◇ **prd-entry** Filter the veterinarian directory by specialty on both the page and the machine-readable route · (prd-expert) · ***◷ 0s***
- ◈ **design-block** **new** · (design) · ***◷ 10m***
- ◆ **implement** (implementer) · ***◷ 20m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit
- ✔ **review security** · **approved** · ***◷ 5m***
- ✔ **review code-quality** · **approved** · (1 finding) · ***◷ 5m***
  - [autofix] `VetController.java:105` Lambda variable `s` in the `anyMatch` predicate refers to a `Specialty` object. The single-character name is too terse when the outer parameter is already called `specialty` — a reader must deduce the type from the stream source. Rename to `sp` or `spec` to make the element type visible without a type lookup.
    - fix: Replace `s -> s.getName()` with `sp -> sp.getName()` in the `filterBySpecialty` stream pipeline.
- ✎ **review test** · **changes_requested** · (6 findings) · ***◷ 5m***
  - **[blocked]** `VetControllerTests.java` AC 3 ('given a specialty supplied in a different letter case, when either surface is requested, it matches') is only tested on the HTML surface. There is no test for the JSON/machine-readable surface asserting case-insensitive match (e.g. GET /vets?specialty=RADIOLOGY). The PRD acceptance criterion explicitly says 'either surface'.
  - **[blocked]** `VetControllerTests.java` AC 4 ('given a value that is part of a specialty name but not the whole name, when either surface is requested, no veterinarian matches') is only tested on the HTML surface via showVetListHtmlWithSpecialtyPrefixShouldNotMatch. There is no test asserting prefix-no-match on the JSON surface (GET /vets?specialty=rad). The PRD acceptance criterion explicitly says 'either surface'.
  - **[blocked]** `VetControllerTests.java` AC 6 ('given a specialty that is blank or only spaces, when either surface is requested, result is the same as without the parameter') is only tested on the HTML surface via showVetListHtmlWithBlankSpecialtyShouldReturnAllVets. There is no test asserting blank/whitespace-only behavior on the JSON surface (GET /vets?specialty=   ). The PRD acceptance criterion explicitly says 'either surface'.
  - **[blocked]** `VetControllerTests.java` PRD Veterinarian directory edge case 3 ('A specialty value carrying leading or trailing spaces around a real name matches the same as the name without them') has no test on either surface. No test exercises GET /vets.html?page=1&specialty=%20radiology%20 or GET /vets?specialty=%20radiology%20.
  - **[blocked]** `VetControllerTests.java:147-149` The showVetListHtmlFilteredPaginationLinksShouldCarrySpecialty test contains a for-loop ('for (int id = 10; id \< 16; id++) { surgeons.add(surgeon(id)); }') in the test body. testing-principles.md § Four-Phase Test Structure states 'Tests are straight-line code: no if/else, switch, or loops in test bodies.' The loop should be replaced by calling surgeon() six times inline or by extracting a named list-building factory method.
  - [autofix] `VetControllerTests.java:110-180` The eight new test method names do not follow the BDD naming school mandated by testing-principles.md § Test Naming (applies to tests written from 2026-07-31 onward): 'the{Subject}Should{Outcome}'. Examples: 'showVetListHtmlFilteredBySpecialtyShowsOnlyMatchingVets' should be 'theVetListHtmlShouldShowOnlyVetsMatchingTheSpecialty'; 'showVetListHtmlWithSpecialtyPrefixShouldNotMatch' could be 'theVetListHtmlShouldNotMatchASpecialtyPrefix'. None of the eight new names begins with 'the' or follows the school.
    - fix: Rename all eight new test methods to the 'the{Subject}Should{Outcome}' form. Pre-existing tests (showVetListHtml, showResourcesVetList) predate the school and are exempt per the brief — rename only the new ones added in this slice.
- ✔ **review doc** · **approved** · ***◷ 3m***
- ↻ **implement** (implementer) ← test · (6 findings) · ***◷ 20m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit
- ✔ **review test** · **approved** · ***◷ 3m***
- ◆ **grade CLEAR** · add optional specialty filter to vet list surfaces
  - blast_radius — **clear** — Prod change confined to VetController and one Thymeleaf template, both in the vet module; 32 hunks are mostly docs and tests; no sensitive paths touched.
  - semantic_surprise — **clear** — Read the filter, normalize, and paging hunks: normalizeSpecialty maps null/blank/stripped to null, filterBySpecialty is whole-name equalsIgnoreCase, and PageImpl sublist paging is bounds-checked (start\<size guard, Math.min end); no off-by-one, inverted predicate, or hidden behavior change; unfiltered and JSON paths preserve prior behavior.
  - test_adequacy — **clear** — 13 new tests hit both surfaces with real outcome assertions on list size and vet id across case-insensitive match, prefix no-match, whitespace strip, blank-means-all, unknown-yields-empty, and pagination-carries-param; fixtures (helen id2 radiology, james id1 none) make the size/id assertions discriminating, not tautological.
  - reviewer_hedging — **clear** — Final roster records are unanimous clean approvals; the code-quality autofix nit (rename s to sp) is applied in the diff, and the test-reviewer's R1 critical findings were all resolved and re-approved in R2 with empty findings; no escalate tags or lingering worries.
  - scope_deviation — **clear** — Zero design revisions, consultations, and build retries; the diff matches the REQ-VET-003/004 surface exactly (both routes, in-memory filter per ADR, pagination param, docs) with no wandering past triage.
  - why — Read every prod and test hunk: contained vet-package change, bounds-checked in-memory filter with no semantic surprise, discriminating both-surface tests, unanimous clean approvals, no scope drift. Confirm and merge; a quick confirmatory glance at findPaginated paging suffices.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- No injection sink: the specialty filter is an in-memory equalsIgnoreCase over the cached VetRepository.findAll() collection; no DB query or JPQL is built from the request parameter, so the equalsIgnoreCase/whole-name design avoids the owner-search vendor case-folding class and introduces no SQLi surface.
- No reflected XSS: the request-derived specialty reaches the template only as the 'specialty' model attribute inside Thymeleaf @{/vets.html(page=...,specialty=${specialty})} URL-builder expressions on the pagination hrefs; the link-expression query parameter is URL-encoded and the th:href attribute output is HTML-escaped, and the value is never rendered into HTML text or an unquoted/JS/CSS context. The vetList.html loop variable 'specialty' on line 20 iterates vet.specialties and is unrelated to the request parameter.
- Error handling is fail-safe: normalizeSpecialty treats null/blank/whitespace-only as absent (no filter), an unmatched specialty yields an empty list with HTTP 200, and no exception text or internal detail is exposed on the filter path.
- Data integrity: the path is read-only over a cached, seeded collection; PageImpl sublist paging is bounds-checked (start\<size guard, Math.min end), no writes, no state mutation, no privilege boundary crossed.
- In-memory filter+paging DoS surface is negligible: the veterinarian directory is a small seeded, cached collection, so the stream filter and subList carry no attacker-amplifiable cost.

**code-quality-reviewer**

- normalizeSpecialty correctly mirrors OwnerController.processFindForm normalization (null/blank/strip → null) — verified by direct Read of OwnerController lines 98-104; oracle N/A (IntelliJ MCP not connected), claim grounded by Read
- filterBySpecialty uses equalsIgnoreCase on the whole specialty name, not startsWith/contains, satisfying the whole-name match requirement
- findPaginated routes null specialty to vetRepository.findAll(Pageable) (pre-existing cached paged path) and non-null specialty to vetRepository.findAll() (single cached collection entry) then PageImpl — consistent with the ADR
- model.addAttribute("specialty", filter) with filter=null causes Thymeleaf URL builder to omit the parameter on unfiltered pages, which is the correct behaviour
- Template pagination links all switched to @{/vets.html(page=${i},specialty=${specialty})} URL-builder form — cleaner than the prior preprocessed string literals and handles URL-encoding and null omission correctly; all five link positions updated consistently
- Javadoc on normalizeSpecialty explains the cross-reference to the OwnerController pattern, giving a future reader the why without having to grep
- ADR back-link comment in findPaginated steers a future maintainer away from replacing the in-memory filter with a repository query
- Method lengths are all well under 30 lines; single-responsibility throughout

**test-reviewer**

- All 10 tests pass on a clean build-pass run
- Mocking usage stays within the 'tolerated' band: @MockitoBean on VetRepository is a pre-existing pattern in this @WebMvcTest class; the new tests extend it rather than introducing fresh mocking policy violations
- surgeon(int id) fixture is a proper private factory method following the factory-method convention
- AC 1 (HTML filter), AC 2 (JSON filter), AC 5 (unknown specialty + HTTP 200 on both surfaces), AC 7 (no-param behaves as today on both surfaces via pre-existing tests), and AC 8 (pagination carries specialty) all have direct, focused test coverage
- showVetListHtmlFilteredBySpecialtyShowsOnlyMatchingVets verifies list size (1), confirming the filter excludes non-matching vets
- showResourcesVetListFilteredBySpecialtyReturnsOnlyMatchingVets verifies both size and the specific matched vet id — strong identity assertion
- Empty specialty assertions use model().attribute(..., hasSize(0)) — clearly communicates the empty-list expectation
- Pagination test confirms both totalPages=2 and the presence of 'specialty=surgery' in the rendered HTML — both concerns tested

**doc-reviewer**

- PRD boundary respected throughout: no mechanism, pseudocode, Java constructs, or internal code references entered prd.md
- REQ-VET-002 correctly kept in the Superseded list with an update note; its ID is not reused; existing links still resolve
- REQ-VET-003 and REQ-VET-004 anchors are present in prd.md (consolidated on one line, consistent with the file's existing pattern for other multi-requirement sections)
- All Done-when bullets follow given/when/then BDD form and every new REQ-ID has at least one acceptance bullet
- NG-9 narrowing conveyed in the preamble blockquote and in the table row, both carrying the ADR link; pattern matches the established NG-4/NG-5 precedent
- Both new ADRs carry the correct Implementation section: non-goal ADR has **Non-goal:** NG-9; specialty-filter ADR has **Requirements:** REQ-VET-003, REQ-VET-004
- ADR README index rows added with correct dates, titles, and status
- system-design.md VetController row updated with Implements REQ-VET-001, REQ-VET-003, REQ-VET-004 and ADR back-link in the description; no why-reasoning inline
- Stale Known Defect row ('machine-readable veterinarian route serves no requirement') correctly removed now that REQ-VET-003 makes it a supported surface
- Cross-document coherence maintained: every requirement ID in system-design.md Implements column exists in prd.md; withdrawn REQ-VET-002 absent from system-design.md
- ubiquitous-language.md Filter entry precisely distinguishes whole-value case-insensitive filter from owner free-text prefix search; Avoid line canonically reserves 'search' for the owner pattern
- All document cross-references checked and resolve: prd.md#req-vet-003, prd.md#req-vet-004, prd.md#non-goals, system-design.md#contracts all exist; ADR back-links point to existing files
- Open Questions entries for visible-control follow-up and repeated-parameter handling are correctly scoped as non-blocking questions, not requirements

**test-reviewer**

- R1 finding 1 resolved: theVetListJsonShouldMatchTheWholeSpecialtyNameCaseInsensitively (line 182) covers AC3 on the JSON surface — GET /vets?specialty=RADIOLOGY asserts 1 vet with id=2
- R1 finding 2 resolved: theVetListJsonShouldNotMatchASpecialtyPrefix (line 190) covers AC4 on the JSON surface — GET /vets?specialty=rad asserts empty list with HTTP 200
- R1 finding 3 resolved: theVetListJsonShouldReturnAllVetsForABlankSpecialty (line 197) covers AC6 on the JSON surface — .param("specialty","   ") asserts full list of 2 returned
- R1 finding 4 resolved: PRD edge case 3 (surrounding whitespace) covered on both surfaces — theVetListHtmlShouldMatchASpecialtyWithSurroundingWhitespace (line 142) and theVetListJsonShouldMatchASpecialtyWithSurroundingWhitespace (line 204) both use .param("specialty"," radiology ") with literal spaces; MockMvc .param() passes the value directly to Spring parameter binding, faithfully exercising the controller strip() path
- R1 finding 5 resolved: loop removed from pagination test body — sixSurgeons() factory method (line 90) is a straight-line list of six inline constructor calls; theVetListHtmlPaginationLinksShouldCarryTheSpecialty (line 156) calls it with no loop in the test body
- R1 finding 6 resolved: all 13 new test methods follow the the{Subject}Should{Outcome} BDD naming school; pre-existing showVetListHtml and showResourcesVetList are correctly left exempt
- Suite coherence: all 15 tests pass on a clean build; no mocks added beyond the pre-existing @MockitoBean VetRepository pattern; all test bodies are straight-line; AC 1-9 each have direct coverage on both surfaces where the PRD says 'either surface'; no phase comments; all assertions are standard MockMvc/jsonPath/Hamcrest matchers appropriate to the @WebMvcTest slice

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $3.61 | 13m 59s | 96% |
| `(parent)` | 1 | opus-4-8 | $1.27 | 31m 31s | 95% |
| `spring-boot-claude:system-design-expert` | 1 | opus-4-8 | $1.18 | 3m 37s | 89% |
| `spring-boot-claude:product-requirements-expert` | 1 | opus-4-8 | $1.18 | 3m 53s | 91% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $0.54 | 3m 4s | 78% |
| `spring-boot-claude:security-reviewer` | 1 | opus-4-8 | $0.53 | 43s | 78% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $0.38 | 1m 8s | 78% |
| `spring-boot-claude:doc-reviewer` | 1 | sonnet-4-6 | $0.37 | 2m 36s | 82% |
| `spring-boot-claude:code-quality-reviewer` | 1 | sonnet-4-6 | $0.33 | 2m 7s | 87% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.09 | 26s | 49% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.89 | 7m 32s | 96% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.72 | 6m 26s | 96% |
| `(parent)` | opus-4-8 | $1.27 | 31m 31s | 95% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.18 | 3m 37s | 89% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.18 | 3m 53s | 91% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.53 | 43s | 78% |
| `spring-boot-claude:change-grader` | opus-4-8 | $0.38 | 1m 8s | 78% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.37 | 2m 36s | 82% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.33 | 2m 7s | 87% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.30 | 1m 55s | 76% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.24 | 1m 9s | 80% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.09 | 26s | 49% |

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
- model requested `claude-opus-4-8`; models used: opus-4-8 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `064d588523591361` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
