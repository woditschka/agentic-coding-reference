# vets-specialty-filter r1 — v0.1.1

Filter the vet list by specialty (feature) · started 2026-08-05T12:37:00+00:00 · exec `claude-dev` · status **complete**

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
| 2 (±0) | 3 (±0) | 4 (±1) | 3 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.69. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 2 · test-quality 3 · maintainability 4 · doc-fit 3

> The whole-name, case-insensitive, trimmed matching rule and a hand-rolled paginate() land in VetController.filterBySpecialty/paginate — a new business rule in a web controller, which the checklist bars outright and which the available-but-unused Domain service or a repository query would have carried; no ADR records that departure, and paginate() duplicates findPaginated(). Tests are BDD-named and cover case, prefix, blank, unknown, and filter-before-page, but every value is a Tier-3 literal (hasSize(6), hasProperty("id", is(7))) with comments compensating, and all nine boot MockMvc, widening the pyramid gap. Docs move broadly (ADR, index, NG-9, REQ-VET-003/004, defect row), yet the hunk deletes the REQ-VET-001 prose paragraph entirely, and the new provenance claim about inline "(confirmed \<date>)" markers is contradicted — no requirement carries one.

**Sample 2** — design-fit 2 · test-quality 3 · maintainability 4 · doc-fit 3

> The matching rule (trim, whole-name, case-insensitive) plus hand-rolled paging land in VetController.filterBySpecialty/paginate — a fresh business rule in a controller, which the checklist calls a violation the existing deviation does not excuse; the sanctioned Domain service was available without an ADR, and the rule is now only testable through MockMvc. Tests are well-named BDD specifications with broad coverage (case, partial, blank, trim, page-2), but carry Tier-3 literals ("radiology", hasSize(6), id 8/9) with no named constants or derived expectations, and assert field-by-field via hasProperty. Docs are otherwise thorough, but the PRD hunk deletes the REQ-VET-001 narrative outright, leaving three anchors with no requirement prose, and rewrites "ten further questions" to "three" without answering seven.

**Sample 3** — design-fit 2 · test-quality 3 · maintainability 3 · doc-fit 2

> VetController now owns the matching rule ( filterBySpecialty , whole-name case-insensitive fold) plus hand-rolled paging ( paginate , subList index math) — a fresh business rule in a web controller, which the Design Validation Checklist bars outright while Domain service is sanctioned without an ADR; system-design.md records the deviation instead of avoiding it. Tests are behavior-named and cover case, prefix, blank, unknown, and filter-before-page, but lean on mystery literals ( hasSize(6) ,  hasProperty("id", is(8)) , bare "radiology") with no named constants and carry narration comments. Docs move widely, yet the REQ-VET-001 prose paragraph is deleted leaving an empty section, the provenance note promises inline  (confirmed \<date>)  markers that appear nowhere, and "ten further questions" becomes "three" though none closed.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.61 | 42m | 36 | 87% | 7 file(s) +227/−41 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.35 | 4m 28s | 78% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-004 — Filter the veterinarian directory by specialty

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (2) | **✔** |
| **test** | ✎ (4) | **✔** |
| **security** | **✔** | · |
| **doc** | ✎ (1) | **✔** |

- ◇ **prd-entry** Filter the veterinarian directory by specialty · (prd-expert) · ***◷ 0s***
- ◈ **design-block** **minor** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 1h 5m***
  - ▲ **build ✓ clean** · build · test · format · check
- ✔ **review security** · **approved**
- ✎ **review code-quality** · **changes_requested** · (2 findings) · ***◷ 5m***
  - [autofix] `VetController.java:75,81` The literal 5 appears as a separate local variable int pageSize = 5 in both findPaginated (line 75) and paginate (line 81). A future reader changing the page size must find both occurrences; one missed site silently pages the filtered and unfiltered routes at different sizes.
    - fix: Extract private static final int PAGE_SIZE = 5; at the top of the class and replace both local int pageSize = 5; declarations with PAGE_SIZE.
  - [clarify] `VetController.java:109` filterBySpecialty passes specialty as-is to equalsIgnoreCase without trimming it first. StringUtils.hasText accepts " radiology " (whitespace around a real name) as non-blank, so the value reaches the match but fails to equal "radiology". Owner search (OwnerController) trims its input before comparing. The PRD specifies only that a blank or spaces-only value behaves as absent; it does not say whether leading/trailing whitespace surrounding a real name should be stripped. Clarify whether specialty must be trimmed before matching (consistent with owner search) or whether the caller-supplied literal value is canonical.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 4m***
  - **[blocked]** `prd.md:10` The provenance banner says 'Every individual requirement remains provisional' but the body now marks REQ-VET-003 and REQ-VET-004 as '(confirmed 2026-08-05)' — a product-owner statement, not a derived observation. The banner's blanket claim contradicts the in-line confirmation markers. A reader who reads the banner first will incorrectly treat two explicitly confirmed requirements as provisional. The banner must be updated to acknowledge that some requirements have since been product-owner confirmed.
- ✎ **review test** · **changes_requested** · (4 findings) · ***◷ 5m***
  - **[blocked]** `VetControllerTests.java` No test can distinguish filter-before-page from filter-after-page. The fixture has 3 total vets and a page size of 5, so the full directory fits on one page — paginate(page, filtered) and a hypothetical filter(findPaginated(page)) return identical results. The design-block explicitly requires filter-before-page: filtering the full cached collection first, then paging the filtered list. A bug that reverses the order would leave every new test green. A non-vacuous test needs a fixture with more than 5 total vets, at least two matching the filter specialty, and a page request that would overflow if the wrong collection were paged — so that a filter-after-page implementation returns a wrong page count or a wrong element that the assertion catches.
  - **[blocked]** `VetControllerTests.java:htmlDirectoryS` The test asserts model().attribute("specialty", is("radiology")), which verifies the specialty value is in the model, but no test checks that the rendered HTML pagination hrefs include specialty=radiology. The design-block requirement is explicit: pagination links must carry the active specialty param. If the Thymeleaf expressions in vetList.html omitted specialty=${specialty} from every th:href, every existing test would still pass. An assertion on the response body (e.g. content().string(containsString("specialty=radiology"))) or a second page navigation that verifies the specialty is preserved would close this gap.
  - [clarify] `VetControllerTests.java` All 7 new test method names omit the "the" prefix required by the BDD naming school (the{Subject}Should{Outcome} per docs/testing-principles.md § Test Naming, e.g. theOwnerSearchShouldMatchOnLastNamePrefix). The prd-entry test_names field specifies the same names without "the", creating a conflict between the naming convention and the gate-check values. Both the prd-entry test_names and the test method names need updating together. Raising to product-requirements-expert to revise test_names; feature-implementer then renames the test methods to match.
  - [autofix] `VetControllerTests.java:showVetListHtm` The acceptance criterion "Given no specialty, both surfaces behave as before this requirement" is count-verified only for the JSON surface (absentSpecialtyShouldReturnTheFullDirectory asserts jsonPath("$.vetList", hasSize(3))). The HTML surface test showVetListHtml asserts model existence and view name but not vet count. Adding model().attribute("listVets", hasSize(3)) to showVetListHtml closes the backward-compatibility gap for the HTML surface.
    - fix: Add .andExpect(model().attribute("listVets", hasSize(3))) to the showVetListHtml test after the existing model().attributeExists("listVets") expectation.
- ↻ **fix prd-expert** ← code-quality, doc, test · (7 findings)
- ◇ **prd-entry** Filter the veterinarian directory by specialty · (prd-expert) · ***◷ 1m***
- ↻ **implement** (implementer) ← code-quality, test · (6 findings) · ***◷ 20m***
  - ▲ **build ✓ clean** · build · test · format · check
- ✔ **review code-quality** · **approved** · ***◷ 5m***
- ✔ **review doc** · **approved** · ***◷ 10m***
- ✔ **review test** · **approved** · ***◷ 5m***
- ◆ **grade CLEAR** · filter the vet directory by specialty
  - blast_radius — **clear** — Contained to the vet feature: VetController, its Thymeleaf template, and its test, plus the docs recording the product decision (prd, system-design, adr index, one new ADR). One prod module, no sensitive paths (no auth/security/db/properties). Structural facts hand-derived from git status/diff because the extractor could not run.
  - semantic_surprise — **clear** — Read the filter-before-page arithmetic closely: paginate() computes start/end over the filtered list with a start>=size empty guard and a PageImpl whose total is the filtered size; filterBySpecialty does trimmed whole-name equalsIgnoreCase, not prefix. Behavior matches the description exactly with no hidden change.
  - test_adequacy — **clear** — The two originally-blocked gaps are now non-vacuous: a 9-vet/6-radiology fixture at page=2 asserts element id 7 and totalPages=2, which fails under a filter-after-page bug, and a response-body assertion pins specialty=radiology into the hrefs. Every acceptance criterion, including trim and case-folding, is covered.
  - reviewer_hedging — **clear** — Second pass is a clean unanimous approval with empty findings from code-quality, doc, and test reviewers. Security approved on pass one and was not re-run, but the only post-approval delta -- specialty.trim() and a PAGE_SIZE constant -- adds no injection sink or output surface, so the stale approval is immaterial.
  - scope_deviation — **clear** — Stays within REQ-VET-004's two-surface filter scope; the PRD/ADR edits are the recorded product-owner decisions for this slice (NG-9 narrowing, REQ-VET-003 reinstatement, REQ-VET-002 kept retired). One re-work cycle, no consultations; VetRepository was intentionally left untouched per the in-memory design.
  - why — All five facets clear on a close read of the hunks: the filter-before-page arithmetic is correct and now non-vacuously tested, reach is contained to the vet feature and its docs, and the post-approval security delta is inert. Confirm and merge. Note: the deterministic extractor could not run (layout.toml declares an unsupported 'gradle' module strategy), so the structural row is hand-derived from git -- a broken install unrelated to this change.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Reflected XSS at the specialty->pagination-href boundary is mitigated: the template uses the Thymeleaf @{/vets.html(specialty=${specialty})} URL-expression builder, which URL-encodes query-parameter values and HTML-escapes the resulting href attribute; the value is never placed in an unescaped output sink
- No injection path in the filter: specialty is matched by an in-memory case-insensitive String equalsIgnoreCase over Vet.getSpecialties() names, not a SQL/JPQL/regex query
- Unbounded cache-key growth forbidden by the design-block was not introduced: the filter reads through the already-cached findAll() and no @Cacheable method is keyed on the user-supplied specialty
- JSON surface (/vets) applies the identical filterBySpecialty helper and returns the same Vet data as the HTML page, exposing nothing extra
- Full-collection in-memory load per filtered request is acceptable for this cached sample-app scale and consistent with recorded security baseline NG-1 (DoS out of scope)

**code-quality-reviewer**

- checkFormat passes cleanly — no formatting issues
- Thymeleaf pagination hrefs correctly migrated from string-literal preprocessing syntax to the URL builder form, which omits null specialty from generated links without producing specialty=null in URLs
- Filtered vs. unfiltered HTML path divergence is documented with an inline comment explaining why filter-before-page is required; the design rationale is preserved for cold readers
- filterBySpecialty Javadoc accurately describes the contract and records the vendor-invariant rationale
- showResourcesVetList ternary on line 95 keeps the JSON handler concise and visually parallel to the HTML handler logic

**doc-reviewer**

- NG-9 row narrowed correctly: free-text stays out, filter-over-closed-set admitted; Design Rationale link to the new ADR is present
- New ADR 2026-08-05-non-goal-vet-directory-filter.md follows the non-goal ADR convention: non-goal- filename infix, Implementation section uses **Non-goal: NG-9**, all required sections present
- ADR README index row added with correct date, title, filename, and Accepted status
- REQ-VET-003 is a genuinely fresh ID; nothing reads as an un-withdrawal of REQ-VET-002; the Superseded entry explicitly states the ID stays withdrawn and is not reused
- No contradiction survives: the 'route pending removal' language and the 'Known defect — serves no requirement' row in system-design are both removed; Edge case 2 is updated to describe the route as a supported surface under REQ-VET-003
- PRD stays free of mechanism: no query-parameter names, no HTTP status codes, no controller names; mechanism correctly lives in system-design
- system-design Contracts table updated: Vets implements REQ-VET-003, VetController implements REQ-VET-001/REQ-VET-003/REQ-VET-004; the Veterinarian directory filtering paragraph names the specialty query parameter and in-memory matching approach correctly
- ADR cross-reference to ../prd.md#non-goals resolves (## Non-Goals generates the non-goals anchor in GFM); REQ-VET-004 anchor exists at prd.md:119
- All three anchors (req-vet-001, req-vet-003, req-vet-004) placed before the Veterinarian directory section; inline [REQ-...] tags used consistently throughout

**test-reviewer**

- All 7 test_names from the prd-entry exist as method names in VetControllerTests
- The rafael() fixture with surgery specialty makes hasSize(1) on a radiology filter non-vacuous: a no-op filter returning all 3 vets would fail the assertion
- The whitespace-only case is tested with .param("specialty", "   ") via MockMvc param API (not URL-encoded whitespace), correctly exercising StringUtils.hasText behavior
- MockMvc is used as the sanctioned web-layer harness; @MockitoBean of VetRepository follows the tolerated pre-existing pattern per the mocking policy
- Four-phase structure is maintained; no phase comments or narration in new tests
- All 9 tests pass cleanly

**code-quality-reviewer**

- PAGE_SIZE constant extracted as private static final int PAGE_SIZE = 5 at VetController.java:41; both findPaginated (line 77) and paginate (lines 82, 84) reference it — the duplicated literal 5 is gone
- filterBySpecialty trims the specialty argument before matching (line 110: String target = specialty.trim()); the Javadoc accurately records this and cites consistency with owner search
- Thymeleaf URL-builder specialty=${specialty} threads through all five pagination href expressions (numbered pages, first, prev, next, last) in vetList.html — null specialty is correctly omitted from generated links
- checkFormat passes cleanly; no formatting issues introduced by the re-work
- Stream pipeline in filterBySpecialty is idiomatic; single-responsibility, early trim before the stream, no side effects

**doc-reviewer**

- Original blocked finding resolved: provenance banner now correctly scopes provisionality to bootstrap-survey-derived requirements, explicitly carving out product-owner-confirmed ones via the (confirmed \<date>) marker — no requirement is incorrectly treated as provisional or confirmed
- Open Questions count accurate: three non-struck-through questions remain in the Open Questions section, matching the banner claim of three further open questions
- Banner claim holds document-wide: every requirement without a marker is from the bootstrap survey and remains provisional; REQ-VET-003 and REQ-VET-004 carry (confirmed 2026-08-05); no requirement falsely implied confirmed or provisional
- Trimming addition stays free of mechanism: Done-when bullet and prose both use behavioral language only — no query parameter, method, or framework construct named
- REQ-VET-002 stays withdrawn with ID unreused: Superseded entry explicitly states the ID stays withdrawn, and the fresh requirement uses REQ-VET-003
- No contradiction on /vets route: pending-removal Known Defect removed from system-design.md, Superseded entry updated to no longer pending removal, Edge case 2 replaced with supported-surface language — no reader encounters both descriptions simultaneously
- ADR README index row correctly added: date 2026-08-05, title, filename, and Accepted status all match the ADR
- system-design.md Contracts table updated: Vets implements REQ-VET-003; VetController implements REQ-VET-001/REQ-VET-003/REQ-VET-004; new Veterinarian directory filtering paragraph is appropriate mechanism-level prose with no imperatives missing ADR back-links

**test-reviewer**

- filter-before-page blocked resolved: theFilteredDirectoryShouldPageTheMatchesNotTheWholeDirectory requests specialty=radiology&page=2 and asserts totalPages=2 and listVets=[id7] (hasSize 1); a filter-after-page bug that calls findAll(pageable) first would get PageImpl(all 9, 1 total page) from the mock, making totalPages=1 rather than 2, so the is(2) assertion on totalPages catches the defect — the test is non-vacuous
- href-preservation blocked resolved: theFilteredPaginationLinksShouldCarryTheSpecialty renders specialty=radiology&page=1, where the 6-vet filtered result yields totalPages=2 so the pagination div is rendered; the template generates hrefs via @{/vets.html(page=${i},specialty=${specialty})} which embeds specialty=radiology in each link; removing specialty from the th:href expression would drop the substring from the response body and fail containsString(specialty=radiology)
- naming clarify resolved: all ten test methods (8 from the line-15 prd-entry plus theFilteredDirectoryShouldPageTheMatchesNotTheWholeDirectory and theFilteredPaginationLinksShouldCarryTheSpecialty) use the the{Subject}Should{Outcome} BDD school; names read as executable specifications with no ambiguity
- autofix resolved: showVetListHtml now asserts model().attribute(listVets, hasSize(9)), closing the backward-compatibility gap for the HTML surface
- fixture data-naming is sound: vet(...) factory eliminates raw constructor calls and anonymous vets; directory() has a Javadoc comment naming the design intent (nine vets, six radiology, filter-before-page distinguishability); no mystery literals
- enlarged fixture did not weaken pre-existing assertions: showResourcesVetListByDefault still asserts vetList[0].id=1 (James Carter, id 1, first in directory() list); showVetListHtml upgraded from existence check to hasSize(9), strictly stronger
- trim requirement covered by theSpecialtyFilterShouldIgnoreSurroundingSpaces: controller trims via specialty.trim() in filterBySpecialty before equalsIgnoreCase; StringUtils.hasText passes whitespace-padded real names to the filter, trim corrects them; test exercises the shared helper via the JSON surface which is sufficient given the single filterBySpecialty code path
- MockMvc used as the sanctioned web-layer harness; @MockitoBean VetRepository follows the tolerated pre-existing pattern; no new mock libraries introduced
- four-phase structure maintained in all ten new tests; no phase comments, no control flow in test bodies
- all tests pass (build-pass at handoff line 17)

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $6.76 | 15m 4s | 93% |
| `(parent)` | 1 | opus-5 | $6.20 | 46m 34s | 95% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $4.62 | 6m 44s | 84% |
| `spring-boot-claude:system-design-expert` | 1 | opus-4-8 | $3.18 | 4m 47s | 84% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $2.35 | 4m 28s | 78% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $1.75 | 3m 51s | 74% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $1.68 | 7m 38s | 78% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $1.48 | 6m 10s | 80% |
| `spring-boot-claude:security-reviewer` | 1 | opus-4-8 | $1.11 | 52s | 64% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.15 | 11s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $6.20 | 46m 34s | 95% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $3.42 | 8m 16s | 93% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $3.34 | 6m 47s | 92% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $3.18 | 4m 47s | 84% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $2.84 | 4m 21s | 83% |
| `spring-boot-claude:change-grader` | opus-4-8 | $2.35 | 4m 28s | 78% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.79 | 2m 22s | 85% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $1.11 | 52s | 64% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.93 | 2m 39s | 75% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.87 | 3m 49s | 77% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.84 | 2m 58s | 71% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.83 | 1m 11s | 73% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.81 | 3m 48s | 80% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.64 | 3m 11s | 86% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.15 | 11s | 0% |

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

- plugin `spring-boot-claude` at `v0.1.1` (tag)
- model requested `claude-opus-5`; models used: opus-4-8 · opus-5 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `610c2c59194e4044` · `2.1.222 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
