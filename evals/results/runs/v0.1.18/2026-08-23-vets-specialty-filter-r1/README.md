# vets-specialty-filter r1 — v0.1.18

Filter the vet list by specialty (feature) · started 2026-08-23T03:45:40+00:00 · exec `claude-dev` · status **complete**

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
| 3 (±1) | 3 (±0) | 3 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.61. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 5

> Repository-derived queries sit at the right layer and Thymeleaf link rewriting is idiomatic, but the blank/null rule is copy-pasted three times in VetController (addPaginationModel's specialtyForModel, findPaginated, showResourcesVetList) — a new normalization rule in a controller with no extracted seam, and the identical @Cacheable justification comment is duplicated verbatim on both new repository methods. The wrapped comments ("// Normalise" / "// must // never surface") read as mangled noise the four-phase principle forbids. Tests use the BDD naming school correctly, but ClinicServiceTests' new cases carry bare literals ("radiology", "Leary", "Douglas") with no meaningful/irrelevant tiering and pack two act-assert pairs per method; controller tests assert hasSize rather than whole objects. Documentation is thorough: ADR, index, NG-9 narrowing, REQ-VET-003/004, superseded note, and the retired known-defect row all move.

**Sample 2** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 5

> The derived query  findBySpecialtiesNameIgnoreCase  is the right seam, but the blank-normalisation rule is triplicated in the controller ( findPaginated ,  showResourcesVetList ,  addPaginationModel 's  specialtyForModel ) — a new rule added to a web controller, which the catalog calls a fresh violation, and copy-paste variance rather than one normalising point. The mangled wrapped comment above  specialtyForModel  and the duplicated cache-key rationale are reviewer-flag noise. Tests are well-named and cover case, prefix, empty, blank and pagination boundaries, but  theVetRepositoryShouldMatchSpecialtyCaseInsensitively  and  ...NotAPrefix  each run two act/assert cycles, literals like "radiology", "Leary", "Stevens" are unnamed Tier-3 values, and the blank-leak test narrates what the code says. Documentation is thorough: ADR, index, PRD non-goal, requirements, superseded note, and the retired defect row all move.

**Sample 3** — design-fit 4 · test-quality 3 · maintainability 3 · doc-fit 5

> Filtering lands in the repository as a derived query and the controller only binds and delegates, with the template switched to proper  @{/vets.html(page=...,specialty=...)}  URL building — right seams. The blank-check is copy-pasted three times (findPaginated, addPaginationModel, showResourcesVetList), and the  @Cacheable("vets")  comment claiming "per-key growth is bounded" is wrong: the key is the caller-supplied specialty string, so arbitrary query values grow the cache. The controller comment is line-broken mid-word ("// Normalise"). Tests are behavior-named and cover case, prefix, empty, blank and pagination, but ClinicServiceTests packs two arrange-act-assert cycles per test, uses bare literals ("radiology", "Leary", 6, hasSize(2)) with no factories or derived expectations, and the leak test carries a comment restating the code. Documentation is thorough: ADR, index, NG-9 narrowing, REQ-VET-003/004, Superseded note, contracts table, and the now-false defect row removed.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $10.58 | 38m | 27 | 92% | 9 file(s) +235/−26 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.91 | 3m 51s | 89% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Veterinarian directory filtered by specialty (browser page)

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | · | · |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** (1) | · |

- ◇ **prd-entry** Veterinarian directory filtered by specialty (browser page) · (prd-expert) · ***◷ 0s***
- ◈ **design-block** **minor** · (design) · ***◷ 6m***
- ◆ **implement** (implementer)
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- ✔ **review security** · **approved** · ***◷ 5m***
- ✔ **review doc** · **approved** · (1 finding) · ***◷ 15m***
  - [autofix] `CLAUDE.md#build-commands` The Build Commands section documents `./gradlew formatJava` and `./gradlew checkJavaFormat`, neither of which exists. The `io.spring.javaformat` plugin registers `format` (apply formatting) and `checkFormat` (fail if unformatted). Running the documented commands will produce a task-not-found error. The stale names predate this slice — the changeset did not touch CLAUDE.md — but the implementer's report is confirmed correct.
    - fix: Replace `./gradlew formatJava` with `./gradlew format` and `./gradlew checkJavaFormat` with `./gradlew checkFormat` in the Build Commands table. Update the inline comments accordingly.
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 5m***
  - [autofix] `ClinicServiceTests.java:218,227,236` All three new repository-layer test methods use the pre-existing `should*` naming convention rather than the project's BDD school (`the{Subject}Should{Outcome}`) mandated for tests written from 2026-07-31 onward (testing-principles.md § Test Naming). `shouldFindVetsBySpecialtyIgnoringCase`, `shouldMatchVetSpecialtyOnWholeNameNotPrefix`, and `shouldFindVetsBySpecialtyUnpaged` should be renamed to follow the pattern, e.g. `theVetRepositoryShouldMatchSpecialtyCaseInsensitively`, `theVetRepositoryShouldRequireWholeSpecialtyNameNotAPrefix`, `theVetRepositoryShouldReturnUnpagedCollectionBySpecialty`.
    - fix: Rename the three methods to `the{Subject}Should{Outcome}` form per testing-principles.md § Test Naming.
  - [autofix] `VetControllerTests.java:97,109,119,126` All seven new controller-layer test methods use verb-first or noun-first names (`showVetListHtmlFilteredBySpecialtyListsOnlyMatchingVets`, `vetListSpecialtyMatchingNoVetShowsEmptyPage`, `blankSpecialtyShowsFullVetList`, `filteredVetListPaginationLinksCarrySpecialty`, `showResourcesVetListFilteredBySpecialtyReturnsOnlyMatchingVets`, `resourcesVetListSpecialtyMatchingNoVetReturnsEmptyList`, `blankSpecialtyReturnsAllResourcesVets`) rather than the project BDD school `the{Subject}Should{Outcome}`. Testing-principles.md applies this to all tests written from 2026-07-31 onward.
    - fix: Rename the seven methods to `the{Subject}Should{Outcome}` form, e.g. `theVetListHtmlShouldShowOnlyVetsMatchingTheRequestedSpecialty`, `theVetListHtmlShouldShowEmptyPageWhenNoVetHoldsTheSpecialty`, `theVetListHtmlShouldShowAllVetsWhenSpecialtyIsBlank`, `theVetListHtmlPaginationLinksShouldCarryTheSpecialtyParam`, `theVetListJsonShouldReturnOnlyVetsMatchingTheRequestedSpecialty`, `theVetListJsonShouldReturnEmptyListWhenNoVetHoldsTheSpecialty`, `theVetListJsonShouldReturnAllVetsWhenSpecialtyIsBlank`.
- ↻ **implement** (implementer) ← code-quality, test · (4 findings) · ***◷ 20m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- ✔ **review test** · **approved** · ***◷ 5m***
- ◆ **grade CLEAR** · filter vet list (HTML + JSON) by held specialty
  - blast_radius — **clear** — Contained to the vet slice: two derived-query overloads in VetRepository, optional param plumbing in VetController, and repetitive pagination-link edits in vetList.html, plus tests and docs. No sensitive paths; the 31 hunks are mostly template repetition and prose, not scattered logic.
  - semantic_surprise — **clear** — Behaviors match the requirement. Read the two wrinkles anyway: a non-blank specialty is matched as-given with no trim (documented open question, unlike owner search), and the shared vets cache is safe (String vs Pageable vs SimpleKey keys never collide) though its inline differ-by-arity rationale is slightly imprecise. Neither is a hidden or inverted behavior.
  - test_adequacy — **clear** — Tests assert real outcomes at the boundaries: DataJpaTest confirms case-insensitive whole-name match, prefix and unknown-specialty yield empty, and the unpaged collection; WebMvcTest checks blank-to-unfiltered, empty page, the pagination link carrying specialty=radiology, and the negative guard that whitespace never leaks as an encoded specialty value.
  - reviewer_hedging — **clear** — Final roster is clean unanimous approval: security and doc approved, code-quality and test approved with empty findings after one autofix round each. The row null for code-quality is stale; log line 23 shows approved. The one parked item (CLAUDE.md stale gradle tasks) is pre-existing, change-orthogonal, and already escalated to human.
  - scope_deviation — **clear** — design_revisions=0, consultations=0, build_retries=0. Diff maps exactly to REQ-VET-003 and REQ-VET-004, with prd, ADR and system-design minted for the narrowed NG-9. No wandering beyond the stated surface; the no-trim choice is a recorded narrowest-reading scope decision, not scope creep.
  - why — All five facets clear after reading the hunks: a contained, well-tested vet-slice feature with clean final approvals. Confirm and merge. Two things a fast human read should still eyeball: the deliberate no-trim asymmetry vs owner search, and the shared-cache comment loose arity wording (behavior is correct). Note the features row understates code-quality approval; the log is clean.

---

### REQ-VET-004 — Machine-readable veterinarian list reinstated and filtered by specialty

2 review rounds · 2 build-passes · no grade yet

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (2) | **✔** |
| **test** | · | · |
| **security** | · | · |
| **doc** | · | · |

- ◇ **prd-entry** Machine-readable veterinarian list reinstated and filtered by specialty · (prd-expert)
- ◈ **design-block** **minor** · (design)
- ▲ **build-pass** 04:07 · build, test, format, check, handoff-log, autofix-audit
- ✎ **review code-quality** · **changes_requested** · (2 findings) · ***◷ 5m***
  - [autofix] `VetRepository.java:69,82` Both filter methods carry @Cacheable("vets") with no explanation. The design-block records the reasoning (SimpleKeyGenerator keys differ by arity so no collision with findAll variants; vet/specialty data is static seed data so cache growth is bounded), but none of that reaches the code. A reader who later adds dynamic specialty management will not know whether the shared-cache annotation was a deliberate, reasoned choice or an accidental copy. A brief inline why-comment on each filter method restores the intent.
    - fix: Add a comment above each @Cacheable("vets") on the filter overloads, e.g.: // Shares the 'vets' cache deliberately: SimpleKeyGenerator keys differ by arity from findAll variants (no collision); specialty data is static seed data so per-key growth is bounded.
  - [autofix] `VetController.java:58` addPaginationModel stores the raw specialty value in the model regardless of whether it is null or blank. Null is correct (Thymeleaf omits it from pagination URLs), but a blank value (e.g., specialty=   from a browser) propagates as-is and produces specialty=%20%20%20 in every pagination link. The controller already treats blank as unfiltered in findPaginated; the model should reflect the same normalisation so pagination URLs are clean.
    - fix: Before model.addAttribute("specialty", specialty), normalise: String specialtyForModel = (specialty == null || specialty.isBlank()) ? null : specialty; model.addAttribute("specialty", specialtyForModel);
- ▲ **build-pass** 08:20 · build, test, format, check, handoff-log, autofix-audit
- ✔ **review code-quality** · **approved** · ***◷ 1m***

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Specialty filter uses Spring Data derived query (findBySpecialtiesNameIgnoreCase) with bound parameters — no JPQL/SQL string concatenation, not injectable
- Reflected specialty value reaches only Thymeleaf @{...} URL expressions, which URL-encode query-parameter values; no th:utext or unescaped attribute sink, so no reflected XSS
- Pagination links target the fixed /vets.html path with specialty as a query-param value only — no host/path/protocol control, so no open redirect
- Both controller methods branch null/blank specialty to unfiltered findAll; only non-blank values reach the bound query — no trust-boundary bypass
- JSON /vets route reuses the same bound query and relies on Jackson output escaping

**code-quality-reviewer**

- Blank-vs-null branch (isBlank() guard) correctly prevents empty-string from reaching the filter query
- findPaginated private helper cleanly centralises the paged filter logic with single responsibility
- showResourcesVetList branch mirrors findPaginated intent consistently for the unpaged surface
- vetList.html Thymeleaf param syntax correctly carries specialty through all five pagination link sites
- @Cacheable SimpleKeyGenerator key analysis is sound: filter keys are distinct from findAll keys so no cache collision
- IgnoreCase derived-query keyword gives vendor-neutral case-insensitive match without collation dependency
- DataAccessException declared on new methods consistent with pre-existing interface style
- Javadoc on both new repository methods is specific and accurate

**doc-reviewer**

- NG-9 narrowing prose is correctly scoped: free-text vet search stays out, specialty-directory filter moves in; the rationale is stated once and the ADR link carries the decision trail without embedding it
- REQ-VET-003 and REQ-VET-004 are properly minted — HTML anchors present at first mention, Done-when bullets tagged correctly, behavioral language throughout, no mechanism leaking into the PRD
- REQ-VET-002 remains on the Superseded list with its ID held; the reinstatement note correctly attributes the machine-readable surface to REQ-VET-004 and makes the non-reuse explicit
- ADR follows the non-goal convention: filename carries the non-goal- infix, Implementation section uses **Non-goal:** NG-9, three targeted PRD deep-links resolve via explicit anchors
- ADR README index entry is present and consistent with the ADR filename and title
- system-design.md Implements column is fully coherent: Vets maps to REQ-VET-004, VetRepository and VetController map to REQ-VET-001/REQ-VET-003/REQ-VET-004; no withdrawn REQ-VET-002 reference remains; the Known Defects table no longer carries a /vets route row
- VetRepository and VetController purpose descriptions stay at behavioral altitude — no field enumerations, no parameter tables, no constant literals
- Cross-document coherence: every req-id in system-design Implements exists in prd.md; the NG-9 ADR back-links to prd.md Non-Goals, Veterinarian directory, and Superseded sections, all of which resolve

**test-reviewer**

- Repository-layer tests use @DataJpaTest with real seed data and no mocks — correctly exercises the derived-query whole-name case-insensitive semantics against real I/O
- shouldFindVetsBySpecialtyIgnoringCase correctly tests both exact-case and mixed-case inputs against real seed data, verifying Leary and Stevens for radiology
- shouldMatchVetSpecialtyOnWholeNameNotPrefix verifies the prefix case (radio returns empty) and a non-existent specialty (cardiology returns empty) with real data — covers the whole-name-not-prefix acceptance criterion
- shouldFindVetsBySpecialtyUnpaged exercises the Collection-returning overload used by the JSON endpoint, covering the unpaged surface with real I/O
- @WebMvcTest with MockitoBean is the sanctioned web-layer slice pattern; its use of the pre-existing MockitoBean VetRepository is consistent with the mocking policy's tolerated-stubs clause
- All seven controller-layer tests exercise distinct behaviors: filtered HTML, no-match HTML (200 empty), blank/whitespace HTML, pagination-link carry, filtered JSON, no-match JSON, blank/whitespace JSON — achieving full acceptance-criterion coverage for REQ-VET-003 and REQ-VET-004
- Whitespace-only specialty (param value of three spaces) is explicitly tested for both the HTML and JSON surfaces, satisfying the blank/whitespace acceptance criterion
- Pagination-link test uses containsString on the rendered HTML to confirm the specialty param survives page transitions
- AssertJ is used throughout: containsExactlyInAnyOrder, isEmpty, hasSize, jsonPath value matchers — no JUnit assertEquals
- Four-phase structure observed; blank-line separation between paired sub-scenarios in the repository tests
- All 10 tests pass (BUILD SUCCESSFUL, verified via ./gradlew test --tests)

**code-quality-reviewer**

- Fix 1 confirmed — VetRepository.java: both findBySpecialtiesNameIgnoreCase overloads carry an inline why-comment above @Cacheable("vets") (lines 69-72 and 85-88) explaining the deliberate shared cache, SimpleKeyGenerator arity-based key separation, and bounded growth from static seed data; the comment text is accurate and sufficient
- Fix 2 confirmed — VetController.java addPaginationModel: specialtyForModel normalises blank/whitespace to null before model.addAttribute (line 61-62); the accompanying comment (lines 57-60) states both the intent (avoid %20%20%20 leaking into URLs) and the invariant mirror (matches the unfiltered branch in findPaginated)
- Readability pass: findPaginated and showResourcesVetList both use the same null-or-blank guard (specialty == null   specialty.isBlank()), keeping the three-site whitespace policy consistent and easy to grep
- Constructor injection used, no @Autowired; single-constructor implicit wiring is idiomatic for Spring Boot
- No naming issues, no abbreviations, no mutable state; interface is clean and minimal
- Format check passed (./gradlew checkFormat: BUILD SUCCESSFUL)

**test-reviewer**

- All three ClinicServiceTests renames follow the{Subject}Should{Outcome} school: theVetRepositoryShouldMatchSpecialtyCaseInsensitively, theVetRepositoryShouldRequireWholeSpecialtyNameNotAPrefix, theVetRepositoryShouldReturnUnpagedCollectionBySpecialty — exact form mandated by testing-principles.md § Test Naming
- All seven VetControllerTests renames follow the theVetListHtml.../theVetListJson... form of the{Subject}Should{Outcome} school: theVetListHtmlShouldShowOnlyVetsMatchingTheRequestedSpecialty, theVetListHtmlShouldShowEmptyPageWhenNoVetHoldsTheSpecialty, theVetListHtmlShouldShowAllVetsWhenSpecialtyIsBlank, theVetListHtmlPaginationLinksShouldCarryTheSpecialtyParam, theVetListJsonShouldReturnOnlyVetsMatchingTheRequestedSpecialty, theVetListJsonShouldReturnEmptyListWhenNoVetHoldsTheSpecialty, theVetListJsonShouldReturnAllVetsWhenSpecialtyIsBlank
- New test theVetListHtmlPaginationLinksShouldNotLeakABlankSpecialty correctly names and asserts the blank->null normalization behavioral contract: whitespace specialty must not appear as encoded percent or plus signs in pagination link URLs
- Behavior coverage remains intact: whole-name case-insensitive match at repository layer (real I/O), prefix-negative at repository layer, blank/whitespace-unfiltered at controller layer (both HTML and JSON surfaces), no-match HTTP 200 empty at controller layer (both surfaces), pagination-link specialty carry, blank specialty pagination-link non-leak
- All renamed tests and the new test pass: BUILD SUCCESSFUL via ./gradlew test targeting theVetRepository* and theVetList* methods

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $4.53 | 15m 52s | 96% |
| `(parent)` | 1 | opus-4-8 | $1.51 | 41m 15s | 95% |
| `spring-boot-claude:product-requirements-expert` | 1 | opus-4-8 | $1.27 | 4m 18s | 92% |
| `spring-boot-claude:system-design-expert` | 1 | opus-4-8 | $1.21 | 3m 40s | 89% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $0.91 | 3m 51s | 89% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $0.54 | 3m 52s | 80% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $0.52 | 3m 14s | 86% |
| `spring-boot-claude:security-reviewer` | 1 | opus-4-8 | $0.46 | 38s | 78% |
| `spring-boot-claude:doc-reviewer` | 1 | sonnet-4-6 | $0.33 | 2m 2s | 89% |
| `spring-boot-claude:pipeline-coordinator` | 2 | sonnet-4-6 | $0.18 | 45s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-4-8 | $2.75 | 9m 41s | 96% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.78 | 6m 11s | 94% |
| `(parent)` | opus-4-8 | $1.51 | 41m 15s | 95% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.27 | 4m 18s | 92% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.21 | 3m 40s | 89% |
| `spring-boot-claude:change-grader` | opus-4-8 | $0.91 | 3m 51s | 89% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.46 | 38s | 78% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.35 | 2m 52s | 80% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.33 | 2m 2s | 89% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.31 | 2m 13s | 86% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.21 | 1m 0s | 85% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.19 | 1m 0s | 81% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.09 | 21s | 50% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.09 | 23s | 50% |

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
