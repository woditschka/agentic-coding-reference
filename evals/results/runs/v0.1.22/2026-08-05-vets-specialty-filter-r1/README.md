# vets-specialty-filter r1 — v0.1.22

Filter the vet list by specialty (feature) · started 2026-08-05T14:23:44+00:00 · exec `claude-dev` · status **complete**

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

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 4 (±0) | 3 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.71. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> Filtering lands in the right seam: a derived  findDistinctBySpecialtiesNameIgnoreCase  on VetRepository, a thin controller that only normalizes the parameter, and pagination links rebuilt as  @{/vets.html(page=..., specialty=${specialty})} . Two design smells:  @Cacheable("vets")  now keys on an arbitrary user-supplied string, and  showResourcesVetList  duplicates the addAll branch. Tests cover every stated behavior but violate several principles: names are  shouldFilterVetJsonBySpecialty , not  the{Subject}Should{Outcome} ;  verify(this.vets, never()).findAll(...)  asserts which query ran, an implementation detail; comments narrate the code ("the filtered query is never issued"); literals  8 ,  2 ,  PageRequest.of(0,5)  are unnamed;  shouldReturnEmptyVetListForUnmatchedSpecialtyWithSuccess  bundles two act/assert cycles. Documentation is complete: ADR, README index, NG-9 narrowing, REQ-VET-003, REQ-VET-002 supersession, contracts table, and the removed defect row.

**Sample 2** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> Repository derived queries and the Thymeleaf  @{/vets.html(page=..., specialty=${specialty})}  propagation fit the catalog, but  normalize()  plus null-branching duplicated in  findPaginated  and  showResourcesVetList  puts a new rule in a controller — the checklist's explicit fail — and both new queries reuse the shared  @Cacheable("vets")  region. Tests cover every stated behavior, including a real-DB paging/count check, yet miss the stated school: names read  shouldFilter...  not  the{Subject}Should{Outcome} ;  new PageImpl\<>(filtered, PageRequest.of(0,5), 8) ,  value(2) , and repeated  "radiology"  are mystery values;  verify(this.vets, never()).findAll(...)  asserts which query ran; the blank-filter and unmatched-specialty tests each act twice; comments restate the verify. Docs are complete: NG-9 narrowed via ADR, REQ-VET-003 minted, REQ-VET-002 left withdrawn, defect row removed, contracts table current.

**Sample 3** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> Filtering lands in the repository as derived queries (VetRepository.findDistinctBySpecialtiesNameIgnoreCase, both overloads) with a thin controller and null-safe Thymeleaf link params — right layer, no duplication; only the private normalize() rule sits in the controller and is unreachable without booting the web layer. Docs are thorough: NG-9 narrowed, REQ-VET-003 minted with done-when clauses, REQ-VET-002 kept withdrawn, ADR plus index row, system-design contracts updated and the stale defect row removed; no visible claim survives stale. Tests cover the behavior well but breach the stated school: names lack the{Subject}Should form, narration comments ("// The filtered set is paged...", "// 'rad' is only the start...") restate code, verify(never()) asserts which query ran, and bare literals (8, PageRequest.of(0,5)) are mystery values; two tests exercise both surfaces at once.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $9.10 | 33m | 24 | 86% | 9 file(s) +231/−21 |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Filter the veterinarian directory by specialty on both surfaces

1 review round · 1 build-pass · no grade yet

| reviewer | R1 |
| --- | --- |
| **code-quality** | **✔** |
| **test** | ✎ (4) |
| **security** | ✎ (1) |
| **doc** | ✎ (1) |

- ◇ **prd-entry** Filter the veterinarian directory by specialty on both surfaces · (prd-expert) · ***◷ 0s***
- ◈ **design-block** **minor** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 1h 50m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit
- ✎ **review security** · **changes_requested** · (1 finding) · ***◷ 14h 52m***
  - **[escalate]** `VetRepository.java:66-81` Both new specialty-filter query overloads are @Cacheable("vets"), and the SimpleKeyGenerator keys them on the raw user-supplied specialty string. The "vets" cache is configured with an unbounded MutableConfiguration (no size limit, no TTL; the config comment itself notes the size limit is left unset). VetController.normalize() only trims whitespace and nulls empties -- it does not bound length, cardinality, or validate the value against known specialties. Because the endpoints have no authentication (NG-1), any caller can issue GET /vets.html?specialty=\<distinct> or GET /vets?specialty=\<distinct> with unlimited distinct values, each inserting a permanent entry into the unbounded cache and growing the heap without limit (memory-exhaustion / availability). Remediation is a policy decision (escalate): either (a) drop @Cacheable from the two user-keyed overloads -- the existing findAll() caching is unaffected, or (b) bound the "vets" cache with a Caffeine size/TTL spec, or (c) validate specialty against the finite set of known specialty names before querying/caching.
- ✔ **review code-quality** · **approved** · ***◷ 10m***
- ✎ **review test** · **changes_requested** · (4 findings) · ***◷ 16h 0m***
  - [autofix] `VetControllerTests.java:116` Test name `shouldFilterVetListPageByWholeSpecialtyNameIgnoringCase` promises case-insensitive matching, but the specialty parameter passed is already lowercase `"radiology"`. The test exercises filtered paging and model attributes — correct and valuable — but it does not demonstrate the case-insensitivity it advertises. A future reader relying on the name as specification would be misled. Either rename to `shouldFilterVetListPageByWholeSpecialtyName` and let the integration test own the case-insensitivity proof, or replace `"radiology"` with a mixed-case value (e.g. `"RaDiOlOgY"`) and add a corresponding stub for that exact string.
    - fix: Rename to `shouldFilterVetListPageByWholeSpecialtyName`, removing the `IgnoringCase` claim the test body does not support. If the case-insensitive controller-layer path is wanted here, change the specialty param to `"RaDiOlOgY"` and stub `eq("RaDiOlOgY")` instead.
  - [autofix] `VetControllerTests.java:121` Bare literals `8` (total element count) and `5` (page size) in `new PageImpl\<>(filtered, PageRequest.of(0, 5), 8)` make the derivation `ceil(8/5) = 2 pages` invisible. The assertions that follow (`totalItems: 8L`, `totalPages: 2`) appear as magic numbers; a reader cannot verify them without mental arithmetic. Extract to named locals such as `int FILTERED_TOTAL = 8; int PAGE_SIZE = 5;` and derive `expectedPages = (int) Math.ceil((double) FILTERED_TOTAL / PAGE_SIZE)` or simply inline the derivation in the assertion.
    - fix: Replace bare `8` and `5` with named locals that make the page-count derivation self-evident.
  - [autofix] `VetControllerTests.java:131` The comment `// The filtered set is paged, so the unfiltered directory query is never used.` restates exactly what the immediately following `verify(this.vets, never()).findAll(any(Pageable.class))` already says. The testing-principles brief prohibits inline prose that narrates obvious logic. Remove it.
    - fix: Delete the comment on line 131.
  - [autofix] `VetControllerTests.java:177` The comment `// A blank filter takes the unfiltered path; the filtered query is never issued.` restates the two `verify(this.vets, never())` assertions that follow. Same prohibition as above. Remove it.
    - fix: Delete the comment on line 177.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 10m***
  - **[blocked]** `prd.md:138` Edge case 2 under the 'Veterinarian directory' section is not a behavioral edge case. Its first sentence ('The directory is also published in a machine-readable form at a second route.') duplicates the requirement narrative at lines 121–123. Its second sentence adds historical orientation about REQ-VET-002 — content already present in the Superseded section (line 176) and the Open Questions update (line 185). Every other edge case in the document states a behavioral exception; this item states history and navigational context. Remove edge case 2 in full; the machine-readable surface's supported status and the REQ-VET-002 transition are covered elsewhere in the document.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- No SQL/JPQL injection: findDistinctBySpecialtiesNameIgnoreCase is a Spring Data derived query, fully parameterized (no string concatenation)
- No reflected XSS / URL injection: specialty is rendered only inside Thymeleaf @{/vets.html(...)} link expressions, which URL-encode parameter values and HTML-escape the href attribute; it is never emitted as body text or via th:utext
- No cache key collision or poisoning across the four @Cacheable("vets") methods: SimpleKeyGenerator yields distinct key types (SimpleKey.EMPTY, Pageable, String, SimpleKey(String,Pageable)); empties normalize to null so filtered calls cannot overwrite unfiltered findAll() entries
- Reinstated JSON /vets endpoint exposes no data beyond the HTML vet list (same Vet/specialty fields)
- NG-1 no-auth posture judged as recorded in docs/system-design.md#security-context, not re-litigated

**code-quality-reviewer**

- Format check passes cleanly (checkFormat UP-TO-DATE, no violations)
- VetRepository new overloads mirror the existing findAll pair exactly — same @Transactional(readOnly=true) and @Cacheable("vets") annotations, same throws DataAccessException clause, same Javadoc style; cache key collisions are impossible because Spring's default key generator distinguishes type and arity across all four methods
- normalize() is a single-responsibility private helper with a clear Javadoc that explains the null-as-absent contract; early return, no side effects, uses String.strip() (Unicode-safe, Java 17 appropriate)
- findPaginated(int, String) follows the early-return-for-no-filter pattern with the happy path last — consistent with the existing owner search structure
- vetList.html pagination links correctly replaced from string-interpolation hrefs to Thymeleaf @{} URL expressions carrying specialty=${specialty}; Thymeleaf omits the parameter when the model value is null, so unfiltered pages produce clean /vets.html?page=N links without a spurious specialty= fragment
- model.addAttribute("specialty", filter) placed before addPaginationModel ensures the attribute is in scope for the template on the same model object
- showResourcesVetList uses this.vetRepository consistently within the method for both the filtered and unfiltered branch — the pre-existing this. discrepancy between methods is not introduced by this change

**test-reviewer**

- All nine Done-when criteria for REQ-VET-003 are covered: machine-readable surface as supported route (shouldServeMachineReadableVetDirectoryAsSupportedSurface), filtered HTML paging (shouldFilterVetListPageByWholeSpecialtyNameIgnoringCase), filtered JSON (shouldFilterVetJsonBySpecialty), unmatched specialty → empty + 200 on both surfaces (shouldReturnEmptyVetListForUnmatchedSpecialtyWithSuccess), blank/whitespace filter treated as absent on both surfaces (shouldTreatBlankSpecialtyFilterAsAbsent), and no-filter behavior covered by pre-existing tests
- Layering call for PetClinicIntegrationTests is correct: case-insensitive whole-name matching and prefix rejection are Spring Data derived-query semantics compiled by the JPA provider; a controller test with a stubbed repo cannot prove the DB-level contract. shouldMatchWholeSpecialtyNameIgnoringCase and shouldNotMatchSpecialtyByPrefix belong in a real-I/O integration test
- Multi-page count test (shouldReflectFilteredCountWhenPagingFilteredVets) genuinely exercises more than one page: PageRequest.of(0,1) against two seeded radiology vets forces firstPage.totalPages==2, firstPage.content.size==1, secondPage.content.size==1, and distinct IDs across pages. The HHH000104 risk is non-vacuously addressed
- Mocking policy is compliant: @MockitoBean VetRepository under @WebMvcTest is the sanctioned web-layer boundary mock; PetClinicIntegrationTests injects the real repository against real H2
- AssertJ fluent assertions used throughout; MockMvc matchers used correctly for the web layer
- verify(never()) guards correctly prevent silent fallback to the unfiltered query path in every filtered-path test

**doc-reviewer**

- NG-9 narrowing recorded as coherent history-plus-current-state: PRD NG-9 row, Superseded section, and Open Questions all tell a consistent timeline with no self-contradiction; the Open Questions update explicitly resolves the apparent contradiction
- REQ-VET-002 id correctly retired and not reused; REQ-VET-003 is a fresh id throughout all changed documents
- PRD behavior-only / system-design mechanism-only boundary holds: specialty query parameter name appears only in system-design.md VetController purpose row, not in the PRD; route paths and status codes absent from the PRD
- REQ-VET-003 HTML anchor present at docs/prd.md:119
- New ADR follows non-goal ADR convention: filename carries non-goal- infix, Implementation section uses the **Non-goal:** tag, ADR link present in the NG-9 row with **ADR:** prefix
- ADR README index entry correct: filename, title, date, and status all consistent with the ADR file
- Known Defects row for the machine-readable route removed from system-design.md with no residue
- VetController, VetRepository, and Vets contract rows in system-design.md correctly scoped to REQ-VET-001 and/or REQ-VET-003; REQ-VET-002 absent from all Implements cells

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:product-requirements-expert` | 1 | opus-4-8 | $1.95 | 3m 51s | 89% |
| `(parent)` | 1 | opus-5 | $1.08 | 5m 38s | 83% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.15 | 15s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.95 | 3m 51s | 89% |
| `(parent)` | opus-5 | $1.08 | 5m 38s | 83% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.15 | 15s | 0% |

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

- plugin `spring-boot-claude` at `v0.1.22` (tag)
- model requested `claude-opus-5`; models used: opus-4-8 · opus-5 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `610c2c59194e4044` · `2.1.222 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
