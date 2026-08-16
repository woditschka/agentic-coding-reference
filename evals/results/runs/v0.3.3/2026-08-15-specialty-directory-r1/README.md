# specialty-directory r1 — v0.3.3

Specialty directory page (feature) · started 2026-08-15T20:42:30+00:00 · exec `claude-dev` · status **complete**

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
| review attention (pipeline grade) | concern |

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
| 4 (±0) | 4 (±0) | 4 (±1) | 5 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.91. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 3 · doc-fit 4

> Logic sits below the web layer: SpecialtyDirectory does the grouping (SpecialtyDirectory.java groupHoldersBySpecialtyId) and VetController.showSpecialtyDirectory only binds and delegates, so no new rule enters a controller; the id-based matching is justified in Javadoc. SpecialtyDirectory matches no catalog pattern and gets no ADR, and the specialty surface hangs off VetController rather than its own controller. Unit tests are behavior-named, four-phase, factory-built, mock-free. Weaker points: specialtyList.html references #{specialties}, #{vets}, #{name}, #{none}, yet no message bundle is touched, so the page renders placeholder tokens while the new PRD edge case 4 claims REQ-LANG-002 applies; renderedDirectory() casts a model attribute and re-asserts entry ordering already owned by the unit tests.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Grouping logic sits in the immutable, framework-free SpecialtyDirectory (SpecialtyDirectory.java:groupHoldersBySpecialtyId), leaving VetController.showSpecialtyDirectory a bind-delegate-select method with constructor-injected SpecialtyRepository — catalog-conformant; hanging /specialties.html off VetController rather than a SpecialtyController is the one arguable seam. Unit tests are behavior-named, factory-constructed, phase-separated, and use named constants (SpecialtyDirectoryTests: RADIOLOGY_ID, lowerId/higherId), but RADIOLOGY/SURGERY constants and the specialty/vet factories are duplicated in VetControllerTests instead of shared vocabulary, and model().attributeDoesNotExist("currentPage"...) asserts an implementation trace. specialtyList.html references #{none}, with no message bundle entry in the patch despite the PRD's REQ-LANG-002 edge case. PRD context, REQ-SPECIALTYDIRECTORY-001, open questions, and the system-design contract rows all move together.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Grouping/ordering logic sits in the immutable SpecialtyDirectory projection rather than the controller, so VetController.showSpecialtyDirectory stays a bind-delegate-select adapter; SpecialtyRepository follows the Repository naming and query style. Minor fit debt: a third surface bolted onto VetController instead of a SpecialtyController, and the projection matches no catalog pattern outright. SpecialtyDirectoryTests are exemplary — behavior names, factory methods, named RADIOLOGY_ID/lowerId constants, defensive-copy test. Controller tests weaken this by casting the model attribute out of MvcResult and asserting absence of currentPage/totalPages, i.e. implementation detail, plus another @MockitoBean stub. specialtyList.html introduces #{specialties}/#{name}/#{vets}/#{none} with no messages bundle change visible, so keys may render unresolved. Docs update PRD, contracts table, and open questions consistently.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $12.28 | 29m | 4 | 93% | 8 file(s) +471/−9 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.09 | 3m 28s | 89% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPECIALTYDIRECTORY-001 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · grade **CONCERN**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | · |
| **doc** | ✎ (1) | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **minor** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 11m***
  - ▲ **build ✓ clean** · build · test · checkFormat · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 49s***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain not verified against the NVD in this review: the OWASP dependency-check plugin is not configured in build.gradle, and this reviewer has no network access. The slice changes no dependency, so no new exposure was introduced; closing the NVD check for the project's Spring Boot 4.1.0 / transitive stack remains a CI or human task.
  - ▹ rec: SpecialtyDirectory groups by Specialty.getId(), which is null for an unpersisted Specialty. HashMap tolerates a null key so behavior stays defined, but every unsaved specialty would collapse into one bucket. Harmless on the read path under review (all instances come from the repository); worth a guard if the projection ever accepts unpersisted input.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [autofix] `prd.md:145-146` The new Specialty directory requirement has no **Design:** link, even though docs/system-design.md now documents four contracts implementing REQ-SPECIALTYDIRECTORY-001 (SpecialtyRepository, SpecialtyDirectory, VetController, and the Vet/Specialty row updates). The sibling Veterinarian directory section immediately above it carries `**Design:** [system-design.md#contracts](system-design.md#contracts)` for the same reason; per prd-authoring's Links rule the Design link is mandatory whenever a requirement defers a mechanism to system-design.md, and it defers here.
    - fix: Add `**Design:** [system-design.md#contracts](system-design.md#contracts)` after the Edge cases list in the Specialty directory section (after line 151), matching the Veterinarian directory section's placement.
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 3m***
  - [autofix] `VetControllerTests.java:203-208` The test name promises the acceptance criterion 'no navigation entry and no link from another page points at the page', but the body only fetches GET /specialties.html and asserts its own rendered body does not contain the literal string '/specialties.html'. That never exercises another page (vets.html, the layout fragment) for an outbound link, so the criterion it names is not actually checked — the test would still pass if a nav entry linking to /specialties.html were added to vetList.html or fragments/layout.html tomorrow. Confirmed by grep: no test in the suite renders vets.html or the layout fragment and inspects it for a specialties link.
    - fix: Assert on a page that could plausibly carry the link instead of the specialties page itself, e.g. mockMvc.perform(get("/vets.html")).andExpect(content().string(not(containsString("/specialties.html")))) — extend to any other rendered page/fragment the nav could touch. Rename or keep the current name only if the assertion target actually matches it.
- ↻ **implement** (implementer) ← test · (1 finding)
- ↻ **fix prd-expert** ← doc · (1 finding)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 37s***
- ▲ **build-pass** 21:10 · build, test, checkFormat, checkstyleMain, handoff-validate, autofix-audit, contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 14s***
- ✔ **review test** · **approved**
- ◆ **grade CONCERN** · add read-only specialty directory page
  - blast_radius — **clear** — Eight files in one module: two new vet-package classes, one new template, one new unit-test file, plus additive edits to VetController and its tests and two docs. The only edit to existing prod code is VetController gaining a constructor argument and a third handler; the /vets.html and /vets routes are untouched, and the only other construction site is the one @WebMvcTest. No build, dependency, config, schema, or seed-data change, and no sensitive path.
  - semantic_surprise — **clear** — Every hunk reads as its description promises. SpecialtyDirectory groups by Specialty.getId() rather than object equality, the non-obvious right call given persisted types compare by identity and the two sides come from different reads; entry order follows the repository listing, holders sort by last name then first name then id; List.copyOf on both levels makes the projection immutable. The template resolves all four literals through message keys that already exist in every one of the ten bundles, so REQ-LANG-002 is undisturbed; data values go through th:text and are escaped; the layout menu key matches no navbar entry, so the no-navigation non-goal is honored by construction rather than by omission.
  - test_adequacy — **concern** — The projection and the route are well covered by real value objects and MockMvc, and the round-2 no-inbound-link test now asserts against /vets.html with a control assertion, so it is a real fact about the page. The gap is SpecialtyRepository: its JPQL is stubbed by Mockito in every test and never runs against seeded data, so the ORDER BY specialty.name that delivers the stated stable-order acceptance criterion would survive deletion with the suite still green. The analogous lookup repository it copies, PetTypeRepository, does have a database-level test (ClinicServiceTests.shouldFindAllPetTypes), so this is a gap against the project's own precedent rather than against an absent norm.
  - reviewer_hedging — **concern** — Both round-1 dissents (the missing Design link, and the tested-as-spec finding on the no-inbound-link test) were fixable-tagged, fixed, and explicitly re-verified by the same reviewers in round 2 with empty findings; code-quality and security were scoped out of the fix-delta plan, which is expected rather than silence. The residual is the security reviewer's approval-with-recommendations: SpecialtyDirectory buckets by Specialty.getId(), which is null for an unpersisted Specialty, so every unsaved specialty would collapse into one entry. Unreachable on this read path since all specialties come from the repository, but it is a caveat about code in this diff that no later round revisited. Its other recommendation, an unverified NVD supply-chain check, is a standing project condition and not about this change.
  - scope_deviation — **clear** — Zero build retries, zero consultations, zero design revisions. The changed paths are exactly the design-block's primary paths, and the change touches fewer files than the PRD listed rather than more: no message-bundle key was added, and Specialty and VetRepository were left alone. Both recorded non-goals hold in the code, and the two open questions the intake left unanswered were recorded in docs/prd.md rather than silently resolved.
  - why — Correct and contained: the identity-based grouping and the no-navigation handling are the right calls, and both round-1 dissents were fixed and re-verified. Before merging, look at two things: SpecialtyRepository's ordering query is never exercised against a database, and the security reviewer's null-identifier caveat on SpecialtyDirectory was never revisited.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyDirectory is an immutable, well-documented value object matching the codebase's Value-object pattern: List.copyOf on construction, no framework import, grouping by Specialty identifier rather than object equality (correctly averting the cross-repository identity risk the design-block flagged)
- SpecialtyRepository mirrors VetRepository's javadoc, \<code> tags, @Transactional(readOnly=true) and DataAccessException-throwing style exactly, and correctly omits @Cacheable since CacheConfiguration declares only the vets cache
- VetController's new handler follows the existing handler shape (populate model, return view name), keeps the controller free of the grouping logic per the Web-controller pattern's no-business-rule rule, and the specialtyList.html template mirrors vetList.html's structure with every literal resolved through #{} keys
- checkFormat passes; no System.out/err, no swallowed exceptions, no naming violations against architecture-principles.md

**security-reviewer**

- No untrusted input reaches the new route: GET /specialties.html takes no request parameter, path variable, header or body, so the slice adds no new input boundary to validate
- Output escaping matches the neighboring templates: specialtyList.html renders every data value through th:text (stored specialty name, and the SpEL-concatenated vet first/last name), so a hostile stored name is escaped; no th:utext, no inline JavaScript, no remote resource, and no expression preprocessing (__${...}__) of any request- or data-derived value
- No injection surface in persistence: SpecialtyRepository.findSpecialties uses a constant JPQL string with no parameters and no interpolation, and is annotated @Transactional(readOnly = true)
- No shell execution, file I/O, deserialization config, reflection, XML parsing, randomness, or network call is introduced; grep over the new vet sources and template found no Runtime/ProcessBuilder/exec, no Files/FileWriter, no @JsonTypeInfo or enableDefaultTyping, and no /tmp usage
- No credentials, tokens, or secrets in the diff; no logging is added, so no log-injection or sensitive-data-in-logs path exists
- Concurrency safety over shared cached state: VetRepository.findAll is @Cacheable("vets") and returns Vet instances shared across requests, but SpecialtyDirectory only reads them — it groups into freshly allocated ArrayLists and sorts only those, and Vet.getSpecialties already returns a fresh sorted list per call, so no shared collection is mutated. The controller holds no mutable field; the projection and its SpecialtyEntry are defensively copied with List.copyOf, so the singleton controller stays stateless
- Fail-secure on empty and unheld data: an empty specialty listing yields an empty entry list rather than an error, and a specialty with no holder resolves through getOrDefault(..., List.of()) rather than a null dereference
- No new exposure boundary: the page discloses veterinarian and specialty names already published by the existing /vets.html and /vets routes, and the application declares no authentication or authorization to bypass
- Resource use is bounded by clinic-managed lookup data, not by attacker input: findSpecialties returns the specialties table and findAll the cached vet collection, neither growable through the application (NG-2 excludes management), so the unpaged listing is not a practical DoS lever
- No dependency, build-script, or configuration change in the change set: build.gradle and the Gradle files are untouched, so the slice adds no supply-chain surface

**doc-reviewer**

- The new PRD section stays behavioral throughout — no URL literal, no class name, no mechanism table; only the domain-observable page contract is stated
- Every REQ-SPECIALTYDIRECTORY-001 mention in system-design.md has a matching definition in prd.md, and no deprecated requirement leaked in
- The Contracts table additions (SpecialtyRepository, SpecialtyDirectory, VetController, Vet, Specialty rows) accurately describe the code in the diff: repository query, grouping-by-identifier behavior, and the three VetController routes all match
- The new invariants paragraph documenting identity-based grouping and the absent cache annotation is a purpose statement, not a field/parameter table, and survives the field-rename self-test
- Open questions (visible entry point, stable order) are recorded rather than silently resolved or left blocking, consistent with the intake decision
- No new message-bundle key was introduced, so REQ-LANG-002's per-bundle completeness is undisturbed by this change
- 'Specialty directory' as a page name follows the same unresolved-term convention already in force for 'Veterinarian directory' (also absent from ubiquitous-language.md), so it is not a fresh coherence gap introduced by this slice

**test-reviewer**

- SpecialtyDirectory unit tests (SpecialtyDirectoryTests) use only real Vet/Specialty value objects, no mocking, and each test isolates one grouping/ordering/defensive-copy concern with BDD-style names matching the brief's naming school
- Controller tests correctly mock only the repository boundary (SpecialtyRepository via @MockitoBean), consistent with the existing VetRepository pattern in the same file
- Test data uses role-named constants (RADIOLOGY, SURGERY, RADIOLOGY_ID, SURGERY_ID) with no bare mystery literals for the meaningful values
- Edge cases from the PRD acceptance criteria are each covered by a dedicated, correctly named test: empty directory, a specialty no vet holds, omission of a vet holding no specialty, stable ordering (name, then last/first name, then id tie-break), no-paging rendering
- Full ./gradlew test suite passes; new SpecialtyDirectory and VetController code is fully or near-fully line-covered by the new tests
- Four-phase structure with blank-line separation and no phase-comment narration observed throughout both test files

**doc-reviewer**

- The Specialty directory section now carries **Design:** [system-design.md#contracts](system-design.md#contracts), placed after the Edge cases list, matching the sibling Veterinarian directory section's placement and resolving the round-1 finding
- The linked anchor #contracts exists in docs/system-design.md and the Contracts table there documents the mechanism the requirement defers to
- No other prose in the Specialty directory section changed: it remains behavioral with no mechanism, code reference, or rationale prose introduced by the fix

**test-reviewer**

- Round-1 finding resolved: theSpecialtyDirectoryShouldBeReachableByItsAddressAloneWithNoLinkPointingAtIt now asserts against /vets.html (a page that could plausibly carry a link to the directory) instead of the directory page itself, and includes a control assertion (containsString("/owners/find")) proving the shared layout/nav actually rendered into the response body — so the absent-link assertion is a fact about the page, not a false negative from an unrendered fragment
- Fix is scoped to the single flagged test method; no new mocking, assertion-style, or naming issues introduced by the delta
- ./gradlew test (VetControllerTests) passes

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $7.17 | 15m 6s | 96% |
| `(parent)` | 1 | opus-5 | $4.40 | 32m 52s | 97% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $2.53 | 3m 37s | 85% |
| `agent-team:system-design-expert` | 1 | opus-5 | $2.44 | 4m 25s | 93% |
| `agent-team:change-grader` | 1 | opus-5 | $2.09 | 3m 28s | 89% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.34 | 4m 19s | 89% |
| `agent-team:security-reviewer` | 1 | opus-5 | $1.04 | 1m 33s | 87% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.01 | 2m 18s | 92% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.72 | 54s | 86% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $5.94 | 12m 38s | 96% |
| `(parent)` | opus-5 | $4.40 | 32m 52s | 97% |
| `agent-team:system-design-expert` | opus-5 | $2.44 | 4m 25s | 93% |
| `agent-team:change-grader` | opus-5 | $2.09 | 3m 28s | 89% |
| `agent-team:product-requirements-expert` | opus-5 | $1.54 | 2m 33s | 86% |
| `agent-team:feature-implementer` | opus-5 | $1.23 | 2m 27s | 93% |
| `agent-team:test-reviewer` | sonnet-5 | $1.07 | 3m 41s | 90% |
| `agent-team:security-reviewer` | opus-5 | $1.04 | 1m 33s | 87% |
| `agent-team:product-requirements-expert` | opus-5 | $0.99 | 1m 4s | 83% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.72 | 54s | 86% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.70 | 1m 46s | 94% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.30 | 32s | 88% |
| `agent-team:test-reviewer` | sonnet-5 | $0.27 | 37s | 82% |

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

- plugin `agent-team-spring-boot` at `v0.3.3` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.233 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
