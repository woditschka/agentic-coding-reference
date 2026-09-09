# specialty-directory r3 — v0.3.10

Specialty directory page (feature) · started 2026-09-08T23:25:43+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Feature request: the vet list answers "which specialties does this vet hold",
> but staff also ask the inverse — "which vets hold this specialty". Two
> product decisions come with it, made here as the product owner:
> 
> - A read-only specialty view of the existing directory is in scope; managing
>   veterinarians or specialties stays out of scope as before (non-goal NG-2
>   is unchanged).
> - The page is reachable by its URL alone: no navigation entry and no link
>   from another page is part of this request. A visible entry point may come
>   as a follow-up request.
> 
> Add a specialty directory page:
> 
> - GET /specialties.html lists every specialty the clinic knows by its stored
>   name, each with the veterinarians holding it.
> - Each veterinarian is shown by full name: first name, then last name (for
>   example "Helen Leary").
> - A veterinarian holding no specialty appears under no specialty; the page
>   lists specialties, not the full vet roster.
> - All specialties render on one page — no pagination.
> 
> Cover the new behavior with tests.
> 
> These are all the product decisions; no further product answer will come
> during the work. Where a choice still seems open, take the narrowest reading
> consistent with this request and record the open question rather than
> waiting.

## Verdict

| check | result |
|---|---|
| oracle | ✔ 4/4 passed |
| suite (post-agent) | ✔ |
| suite (pristine baseline) | ✔ |
| checkpoints | 7/7 |
| reading depth (pipeline grade) | scrutinize |

The pipeline grade estimates how much human review the change deserves before merge — advisory context from the harness's change grader (read from the ledger's `grader-verdict` record), never part of the bar.

- ✔ `theSpecialtyDirectoryShouldListEverySeededSpecialty` — passed
- ✔ `theSpecialtyDirectoryShouldNameTheVetsHoldingEachSpecialty` — passed
- ✔ `theSpecialtyDirectoryShouldRender` — passed
- ✔ `theVetDirectoryShouldRenderTheSeededVets` — passed

## Checkpoints

The kind's graded ladder, derived from the recorded facts — context only, outside the quality bar (bench README § Checkpoints).

- ✔ `agent complete`
- ✔ `change produced`
- ✔ `suite green`
- ✔ `theSpecialtyDirectoryShouldListEverySeededSpecialty`
- ✔ `theSpecialtyDirectoryShouldNameTheVetsHoldingEachSpecialty`
- ✔ `theSpecialtyDirectoryShouldRender`
- ✔ `theVetDirectoryShouldRenderTheSeededVets`

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 5 (±0) | 4 (±0) | 4 (±1) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $1.01. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyDirectory sits in the vet package as an immutable record with defensive List.copyOf, SpecialtyController only reads repositories and selects a view, and SpecialtyRepository follows the naming and repository rows; the ADR names the pattern departed from, so the controller-rule prohibition is respected rather than widened. Docs move in step: PRD REQ-VET-003 with done-when rows and two open questions, the Contracts table, and the system-design § Package Structure sentence. Tests use factories (VetFixtures), BDD names, and hand-written doubles instead of a mock framework. Deductions: the web tests re-verify grouping already covered by SpecialtyDirectoryTests via weak HTML proxies (doesNotContain("page="), contains("none")), and the isNew() rejection in listingFor is an invented error path the ADR never records.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 5 · doc-fit 5

> SpecialtyDirectory is an immutable record built from both collections, keeping the projection out of SpecialtyController, which only reads repositories and selects the view — matching the catalog's Value object/Repository/Web controller rows, with the departure recorded in an ADR and in system-design.md's controller-gap paragraph. VetFixtures gives real-object factories with generated ids and no mock framework; StoredVeterinarians is a hand-written double; unit tests in SpecialtyDirectoryTests are behavior-named, four-phase, and compare whole Listing records. Weaker: SpecialtyControllerTests asserts on raw HTML substrings — contains("none") and doesNotContain("page=") could pass or fail for reasons unrelated to the listing row, unlike a model-attribute assertion. PRD REQ-VET-003, contracts table, open questions all updated.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController delegates only (builds the directory, selects the view), while the grouping rule sits in the immutable SpecialtyDirectory record with defensive List.copyOf — the Web controller row honoured, the departure recorded in a new ADR and in system-design.md's Contracts table, PRD gaining REQ-VET-003, done-whens, edge cases and both open questions. Unit tests read as specifications (theSpecialtyDirectoryShouldListASpecialtyNoVeterinarianHolds), use VetFixtures factories with generated ids and a hand-written StoredVeterinarians double instead of a mock framework. Weaker: specialtyList.html references #{specialties} and #{none}, but no message bundle is touched anywhere in the patch, so theSpecialtyPageShouldPresentItsWordingInTheRequestedLanguage's "Fachgebiete" assertion rests on keys with no visible source; controller tests also assert raw HTML substrings, and the trailing-space th:text span is a layout hack.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $10.82 | 29m | 8 | 94% | 11 file(s) +627/−5 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.17 | 3m 38s | 92% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Specialty directory lists every specialty with the veterinarians holding it

2 review rounds · 2 build-passes · grade **SCRUTINIZE**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- • intake-decision (human)
- ◇ **prd-entry** Specialty directory lists every specialty with the veterinarians holding it · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 13m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 48s***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain not verified against the NVD in this review: the OWASP dependency-check plugin is not configured in build.gradle, and this reviewer has no network access. The change adds no dependency, so nothing new entered the resolved set; the standing versions are Spring Boot 4.1.1 with the io.spring.dependency-management BOM. A human or CI should close the NVD check separately.
  - ▹ rec: Low-severity resource note: each request to /specialties.html reads the full specialty table (SpecialtyRepository is uncached) and projects it against the full veterinarian set. The vet read is @Cacheable("vets") and the page is unpaged by requirement, so this is bounded by the clinic's data volume and carries no attacker-controlled amplification — worth caching if the specialty table ever grows.
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `SpecialtyControllerTests.java:91-137` All six MockMvc assertions in this file use Hamcrest matchers (`containsString`, `not`) via `content().string(...)` instead of the project's fluent AssertJ style (testing-principles.md § Assertions; test-review checklist 'Fluent AssertJ used'). No other @WebMvcTest in the suite (VetControllerTests, OwnerControllerTests, PetControllerTests, VisitControllerTests, WelcomeControllerTests) uses `content().string(Matcher)` or imports org.hamcrest — so there is no host-file precedent this file is being 'consistent-with-codebase' with; it introduces a new assertion idiom into the suite.
    - fix: Capture the response body once via `MvcResult result = mockMvc.perform(get(...)).andReturn();` (or `.andReturn().getResponse().getContentAsString()`) and assert with `assertThat(body).contains(...)` / `.doesNotContain(...)`, matching the AssertJ style used elsewhere (e.g. VetControllerTests). Drop the `org.hamcrest.Matchers` imports.
- ↻ **implement** (implementer · routine) ← test · (1 finding) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved** · ***◷ 26s***
- ◆ **grade SCRUTINIZE** · add the specialty directory page
  - blast_radius — **skim** — Purely additive and contained: four new files in the vet package plus one template, one module, no deletions under src, no sensitive paths, and no existing production file modified - the only edits to existing artifacts are docs. The reach beyond the new page is architectural rather than behavioral: SpecialtyDirectory is the first domain-core type in a codebase whose rules otherwise live in controllers, and the ADR states it sets a precedent for later read-model pages.
  - semantic_surprise — **skim** — Reading all 18 hunks turned up nothing the change's description would not lead you to expect. The grouping in SpecialtyDirectory.of is a straightforward two-collection projection; the holds() identity comparison is null-safe in the one direction that can be null (a vet holding an unsaved specialty yields false, not an NPE) because the isNew() guard fires first on the outer specialty; the compact constructors defensively copy; the projection sorts a fresh stream rather than mutating the cached vet collection shared across requests. The template mirrors vetList.html line for line and reuses only message keys that already exist in all eleven bundles, so no i18n gap opens. Vets are ordered by last-then-first name while the page displays first-then-last - deliberate and documented, not a bug.
  - test_adequacy — **skim** — Tests are real, not tautological: SpecialtyDirectoryTests drives the projection with real Vet and Specialty instances and uses containsExactly to pin ordering, given-order preservation, multi-specialty membership, the unheld specialty, the omitted non-holder, and the unsaved-specialty rejection; SpecialtyControllerTests asserts against the actual rendered body with hand-written stub repositories, and its doesNotContain assertions would fail against a broken implementation (the word none appears nowhere in the layout fragment, so that assertion is load-bearing rather than incidental). One narrow gap worth knowing: SpecialtyRepository's ORDER BY specialty.name is exercised by no assertion because both controller tests stub the repository, so the system-design claim of name order rests on the JPQL text alone - ordering carries no requirement, so this does not rise to missing coverage of changed behavior.
  - reviewer_hedging — **scrutinize** — The roster approved unanimously and the test-reviewer's round-1 autofix finding was fixed and cleanly re-approved on the fix-delta, but the security-reviewer's approval carries two recommendations that nothing downstream closes. The first is addressed to the human in so many words: the NVD supply-chain check was not verified because no dependency-check plugin is configured and the reviewer had no network, so a human or CI should close the NVD check separately - the change adds no dependency, which bounds it, but it stays open. The second is a low-severity resource note that every request to /specialties.html reads the full specialty table uncached and projects it against the full vet set. Neither is a correctness doubt; both are residue parked where only this facet reaches the merge decision.
  - scope_deviation — **skim** — Zero build retries, zero consultations, zero design revisions - the slice never fought its triage. Read against the requirement's stated surface, every Done-when bullet and both new edge cases have a corresponding behavior in the diff, and nothing wanders past them: no nav link, no paging, no second route, no change to the Vet-to-Specialty mapping. The one choice beyond the stated requirement is fixing an order the PRD explicitly leaves open, and the change declares it rather than smuggling it - the ADR names ordering a determinism choice and not a product requirement, and the PRD records the open question.
  - why — Nothing in the diff surprises: purely additive, one module, real tests, no existing production file touched. The residual is reviewer residue, not code. Before merging, read the security-reviewer's two recommendations at handoff line 14 - the unclosed NVD supply-chain check and the uncached full-table read per request - and decide whether either needs an owner.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyDirectory correctly placed as an immutable value object per the ADR, keeping the grouping rule out of the controller (architecture-principles.md Pattern Catalog)
- SpecialtyController stays a thin read-build-return seam with constructor injection and no business logic
- SpecialtyRepository follows the vet package's narrow Repository style, read-only, matching PetTypeRepository/VetRepository conventions
- Records use compact-constructor defensive copies (List.copyOf) with no mutable state
- Naming uses defined ubiquitous-language terms (Specialty, Veterinarian/Vet, Listing) with no coined synonyms
- Comments explain why (unidirectional association, stable ordering rationale) rather than restating code
- docs/system-design.md Contracts and the ADR are updated consistently with the new types
- checkFormat passes cleanly

**security-reviewer**

- Output escaping: specialtyList.html renders every request-reachable value through th:text (specialty name, vet first/last name) with Thymeleaf's default escaping on. No th:utext, no fragment-expression preprocessing (__${...}__), no inline JavaScript, no remote resource loading, no href built from model data. A sweep of src/main/resources/templates/ found preprocessing only in pre-existing files (layout.html, inputField.html, selectField.html, vetList.html), none touched by this change.
- Data access: SpecialtyRepository.findSpecialties() is a static @Query constant with no parameters and no string concatenation; nothing request-derived reaches query text. Reads are @Transactional(readOnly = true), matching least privilege for a read-only page.
- Exposed surface: the new GET /specialties.html takes no request parameter, binds no request body, and exposes only specialty names and vet names already published by /vets.html and /vets. The addition is stated in docs/prd.md and the system-design component table per security-principles.md 'Widening the exposed surface'; no management endpoint exposure changes.
- Concurrency: SpecialtyController is a singleton holding only final repository references. SpecialtyDirectory and its nested Listing are records with List.copyOf defensive copies in their compact constructors, and the projection sorts a fresh stream rather than mutating the @Cacheable("vets") collection shared across requests.
- Error handling: the only thrown exception (IllegalArgumentException for a Specialty with no stored identity) is unreachable from the controller path, since repository-loaded specialties always carry an id. Its message carries a specialty name — public data, no credential or connection detail — so the error page cannot leak sensitive values.
- No new dependency, no build.gradle change, no serialization or Jackson configuration, no file or path handling, no shell execution, no logging, no /tmp use, and no credential-shaped string anywhere in the change set.

**doc-reviewer**

- PRD REQ-VET-003 entry stays behavioral (no class/method names, no mechanism table) and its acceptance criteria and edge cases match the intake-decision and prd-entry record verbatim in substance
- New anchor \<a id="req-vet-003">\</a> present; all REQ-VET-003 references in prd.md and system-design.md resolve and are mutually consistent
- system-design.md Contracts rows for SpecialtyRepository, SpecialtyDirectory, SpecialtyController verified against source: no @Cacheable on SpecialtyRepository, GET /specialties.html matches SpecialtyController, SpecialtyDirectory is an immutable record matching its stated behavior (unheld specialty keeps an empty list, holder lookup via Vet->Specialty direction)
- ADR 2026-09-08-specialty-directory-projection-in-a-value-object.md carries Requirements: REQ-VET-003, em-dash reference list, and is correctly indexed in docs/adr/README.md
- Layout-fragment integration point (menu key 'specialties' matching no menuItem) verified directly against fragments/layout.html and specialtyList.html, confirming the documented no-nav-link claim
- Non-Goals table (NG-2, NG-9) confirmed untouched as the design-block claimed

**test-reviewer**

- Test placement matches the design's assignment: the specialty-to-veterinarian grouping and its ordering, omission, and IllegalArgumentException rules are unit-tested directly against SpecialtyDirectory with real Vet/Specialty instances (no framework boot), while request routing, full-name rendering, navigation, and i18n are exercised at the @WebMvcTest boundary — correct per testing-principles.md § Test Pyramid.
- Mocking policy followed precisely: SpecialtyControllerTests uses hand-written stub repositories (lambda SpecialtyRepository, StoredVeterinarians record) instead of @MockitoBean, exactly as the design-block instructed ('Do not copy VetControllerTests' @MockitoBean shape'); MockMvc is the only framework double.
- All PRD Done-when bullets and edge cases for REQ-VET-003 have dedicated, correctly named tests (coverage-map: 4/4 declared tests present; edge cases 1, 3, 4 covered by theSpecialtyDirectoryShouldOrderTheVeterinariansUnderASpecialtyByName, theSpecialtyDirectoryShouldListAVeterinarianUnderEverySpecialtyTheyHold, theSpecialtyDirectoryShouldListASpecialtyNoVeterinarianHolds; edge case 2 is an unrelated known defect per prd.md).
- Test data follows the three-tier convention throughout: VetFixtures factory methods (aSpecialtyNamed, aVeterinarian, aVeterinarianHolding, anUnsavedSpecialtyNamed) generate unique irrelevant data, no raw  new Specialty() / new Vet()  calls in the test bodies, and named constants replace all literals used in assertions.
- BDD naming school followed correctly (the{Subject}Should{Outcome}) across both new test classes.
- ./gradlew test passes green with the new tests included.

**test-reviewer**

- Round-1 autofix resolved cleanly: all six MockMvc assertions in SpecialtyControllerTests.java now use fluent AssertJ (assertThat(...).contains(...)/.doesNotContain(...)) instead of Hamcrest matchers; org.hamcrest imports removed entirely (grep sweep of SpecialtyControllerTests.java, SpecialtyDirectoryTests.java, VetFixtures.java confirms no residual org.hamcrest, assertEquals, assertTrue, or assertFalse usage)
- New private helper renderedPageAt(String url) factors out the repeated status().isOk() + getContentAsString() pattern without hiding assertion logic or introducing branching in test bodies; straight-line code preserved
- Fix stayed confined to the reviewed surface (only SpecialtyControllerTests.java changed) with no regression to the placement, mocking-policy, naming, or edge-case coverage approved in round 1
- ./gradlew test green, including the six re-written SpecialtyControllerTests cases

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $5.13 | 15m 57s | 97% |
| `agent-team:system-design-expert` | 1 | opus-5 | $1.66 | 4m 38s | 93% |
| `agent-team:change-grader` | 1 | opus-5 | $1.17 | 3m 38s | 92% |
| `(parent)` | 1 | opus-5 | $1.16 | 31m 53s | 96% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $0.89 | 2m 24s | 90% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.68 | 1m 30s | 90% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.63 | 3m 14s | 91% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.40 | 2m 3s | 93% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.26 | 55s | 87% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.47 | 14m 4s | 97% |
| `agent-team:system-design-expert` | opus-5 | $1.66 | 4m 38s | 93% |
| `agent-team:change-grader` | opus-5 | $1.17 | 3m 38s | 92% |
| `(parent)` | opus-5 | $1.16 | 31m 53s | 96% |
| `agent-team:product-requirements-expert` | opus-5 | $0.89 | 2m 24s | 90% |
| `agent-team:security-reviewer` | opus-5 | $0.68 | 1m 30s | 90% |
| `agent-team:feature-implementer-routine` | opus-5 | $0.67 | 1m 53s | 89% |
| `agent-team:test-reviewer` | sonnet-5 | $0.45 | 2m 29s | 92% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.40 | 2m 3s | 93% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.26 | 55s | 87% |
| `agent-team:test-reviewer` | sonnet-5 | $0.19 | 45s | 90% |

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

- plugin `agent-team-spring-boot` at `v0.3.10` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `6cbb44ce4c9a` (branch `agent-team`)
- task fingerprint `dc643d9216b8dc0b` · `2.1.263 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
