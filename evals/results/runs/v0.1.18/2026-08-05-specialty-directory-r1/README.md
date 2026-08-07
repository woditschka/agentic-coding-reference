# specialty-directory r1 — v0.1.18

Specialty directory page (feature) · started 2026-08-05T11:59:04+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Feature request: the vet list answers "which specialties does this vet hold",
> but staff also ask the inverse — "which vets hold this specialty". One
> product decision comes with it, made here as the product owner: a read-only
> specialty view of the existing directory is in scope; managing veterinarians
> or specialties stays out of scope as before (non-goal NG-2 is unchanged).
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

## Verdict

| check | result |
|---|---|
| oracle | ✔ 4/4 passed |
| suite (post-agent) | ✔ |
| suite (pristine baseline) | ✔ |
| checkpoints | 7/7 |
| review attention (pipeline grade) | — |

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
| 3 (±0) | 3 (±1) | 3 (±1) | 4 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.52. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 4

> SpecialtyRepository and the controller naming fit the catalog, but SpecialtyController.buildDirectory/veterinariansHolding/holds puts the whole inversion-and-ordering rule in the web layer — a fresh violation of the 'no business rule in a controller' checklist item, with Domain service sanctioned and unused; the last-name/first-name ordering is also invented beyond the spec. Tests are behavior-named and use factory helpers, but rely on @MockitoBean stubs by default, a shared @BeforeEach fixture whose data (James Carter, surgery) is a mystery guest, bare Tier-3 ids (specialty(1, "dentistry")), and narration comments the principles forbid; no empty-directory case and the repository's ORDER BY name query is untested. specialtyList.html uses #{specialties} with no message key added and no nav entry, so the page is unreachable and renders untranslated. PRD and contracts table are updated.

**Sample 2** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 4

> Naming, package placement, and the new Repository row fit the catalog, but  buildDirectory / veterinariansHolding / holds  in SpecialtyController put the whole inversion-and-ordering rule in the web layer — the sanctioned Domain service was available and needed no ADR, and the architecture brief says a new controller rule is a fresh violation; it also forces the behaviour to be tested through MockMvc rather than as a unit. Tests are BDD-named and cover the stated edge cases, but stub both repositories with @MockitoBean, share a mutable @BeforeEach fixture, carry narrating comments ("James Carter holds no specialty..."), and use bare literals ( specialty(1, "dentistry") ). The template's  #{specialties} / #{vets}  keys are never added to any messages bundle, and no test would catch that. PRD and contracts table are updated.

**Sample 3** — design-fit 3 · test-quality 4 · maintainability 4 · doc-fit 4

> SpecialtyController lands in the right package with catalog-conformant names and constructor-injected repositories, but buildDirectory/veterinariansHolding/holds put the whole inversion and ordering rule inside a web controller — a fresh violation of the 'no business rule in a controller' checklist item, when the sanctioned Domain service pattern would make it unit-testable without MockMvc. Tests are strong: BDD names (theSpecialtyDirectoryShouldOmitVeterinariansHoldingNoSpecialty), factory methods, the no-holder and no-specialty edge cases. Deductions: narration comments restating code ('// James Carter holds no specialty and must not appear anywhere'), a loop in assertRenderedInOrder, model().attributeDoesNotExist("totalPages") asserting absence of implementation detail, and Mockito stubs where a hand-written double was preferred. PRD and contracts table both updated; specialtyList.html adds #{specialties}/#{vets} keys with no message bundle visible.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $9.12 | 25m | 27 | 84% | 6 file(s) +355/−2 |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPEC-001 — Specialty directory lists each specialty with the veterinarians holding it

2 review rounds · 2 build-passes · no grade yet

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (1) | ✎ (1) |
| **test** | ✎ (3) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (1) | **✔** |

- ◇ **prd-entry** Specialty directory lists each specialty with the veterinarians holding it · (prd-expert) · ***◷ 25s***
- ◈ **design-block** **minor** · (design) · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 5m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- ✔ **review security** · **approved** · ***◷ 10m***
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 1m***
  - **[blocked]** `system-design.md:100-105` The Contracts table does not reference SpecialtyController or SpecialtyRepository, both of which exist in the codebase after build-pass. The Specialty and Vet rows list only REQ-VET-001 in the Implements column; REQ-SPEC-001 should be added to both since the new code makes both types serve that requirement. The PRD carries a Design link pointing to system-design.md#contracts (prd.md line 148), but that section is incomplete with respect to REQ-SPEC-001. Cross-document coherence requires the Contracts table to reflect the landed code. The design-block deferral to doc-sync was appropriate at triage time; now that build-pass is recorded the gap is a coherence failure. Fix: add rows for SpecialtyController and SpecialtyRepository (mirroring the VetController and VetRepository row shapes), and add REQ-SPEC-001 to the Implements column on the Specialty and Vet rows.
- ✎ **review test** · **changes_requested** · (3 findings) · ***◷ 5m***
  - **[blocked]** `SpecialtyControllerTests.java` Stable order (prd.md Edge case 1) has no assertion. The mock for findSpecialties() happens to return [dentistry, radiology, surgery] in alphabetical order, but no test asserts the rendered order of specialties in the HTML response. An ORDER BY regression in SpecialtyRepository would pass all four tests undetected because containsString assertions are order-agnostic. A test must assert the relative position of specialty names in the response body, or seed the mock in non-alphabetical order and verify sorting was applied.
  - **[blocked]** `SpecialtyControllerTests.java:101-105` Vet-to-specialty grouping is not asserted. theSpecialtyDirectoryShouldShowVeterinariansByFullName checks that 'Helen Leary' and 'Linda Douglas' appear anywhere on the page, but not that Helen Leary appears under radiology and Linda Douglas under dentistry. If the controller grouped both vets under the wrong specialty, all four tests would still pass. An assertion on content ordering (radiology header before 'Helen Leary', dentistry header before 'Linda Douglas') would close the gap without complex DOM parsing.
  - **[blocked]** `SpecialtyControllerTests.java:78-86` The within-specialty vet sort (Comparator by last/first name in SpecialtyController line 69) is never exercised. Each specialty in the test fixture holds at most one vet, so the Comparator is never invoked. Adding a second vet under one specialty and asserting their rendered order would cover this code path and pin the sort contract.
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 10m***
  - [autofix] `SpecialtyController.java:74` holds() compares specialties by name rather than by canonical ID. The vets arrive via the @Cacheable("vets") variant of VetRepository, so their Specialty instances are JPA objects from a previous session — not the same references as the Specialty objects returned by specialtyRepository.findSpecialties(). Name equality works only because specialty names happen to be unique; there is no unique constraint enforcing that invariant, and the comparison surprises anyone who knows that entity identity is the ID. A reader who sees held.getName().equals(specialty.getName()) must reason about why an entity field, not the entity's identity, is the matching key.
    - fix: Replace held.getName().equals(specialty.getName()) with held.getId().equals(specialty.getId()). This makes the intent (same stored specialty row) explicit and works correctly whether or not the vet collection is served from the second-level cache.
- ↻ **fix design** ← doc · (1 finding)
- ◈ **design-block** **minor** · (design) · supersedes L4 · ***◷ 5m***
- ▲ **build-pass** 15:20 · build, test, format, check, handoff-log, autofix-audit
- ✔ **review security** · **approved** · ***◷ 5m***
- ✔ **review test** · **approved** · ***◷ 5m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 5m***
  - [autofix] `SpecialtyControllerTests.java:174-181` assertRenderedInOrder() calls body.indexOf(fragment) starting from index 0 on every iteration, using `previous` only for the comparison — not as the search start. The Javadoc says 'each strictly after the previous one', but the implementation finds each fragment's first occurrence in the entire string. If a fragment appeared at two positions in the body (one before and one after the preceding fragment), indexOf would return the earlier position and the assertion would fail even though the order is actually correct. The method happens to be correct for all current fixtures because each fragment appears exactly once, but it does not match its documented contract.
    - fix: Change `int index = body.indexOf(fragment);` to `int index = body.indexOf(fragment, previous + 1);`. When `previous` is -1 (initial value), `previous + 1` is 0, so the first search still starts at the beginning.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- No trust boundary crossed by new input: showSpecialtyList(Model) takes no request params, path variables, or form binding, so no injection or mass-assignment surface is introduced
- XSS controlled: specialtyList.html renders specialty.name and vet full name exclusively through Thymeleaf th:text (default output-escaping on); no th:utext or DOM injection, and rendered values are DB-sourced, not request-derived
- SQL injection controlled: SpecialtyRepository.findSpecialties() is a static parameterless JPQL query via the JpaRepository abstraction with no string concatenation
- Exposed-surface delta is safe: new GET /specialties.html exposes only vet and specialty names already public through the existing vet directory; read-only, no state mutation, no broadened management-endpoint exposure
- No new dependency and no secret handling introduced; supply-chain and credential posture unchanged from baseline

**doc-reviewer**

- REQ-SPEC-001 anchor is present and correctly formatted (prd.md line 135)
- Narrative prose is free of Java/Spring constructs, rationale, pseudocode, mechanism tables, and per-requirement scaffolding
- Done when bullets are given/when/then, bounded, and each carries the REQ-SPEC-001 tag
- Edge cases 1 (stable order) and 2 (stored specialty listed regardless of vet count) are testable and coherent with the prd-entry acceptance criteria
- Reference to NG-2 is a cross-reference, not rationale prose — the prohibition on management is stated behaviorally
- Coherent with REQ-VET-001: the inverse relationship is described accurately and the stable-order edge case parallels REQ-VET-001 edge case 1
- Domain terms Specialty and Veterinarian match ubiquitous-language.md canonical spellings
- Design link resolves to an existing anchor (system-design.md#contracts at line 72)

**test-reviewer**

- BDD naming (the{Subject}Should{Outcome}) applied consistently across all four tests, matching the brief's naming school
- Both edge cases called out in the dispatch are genuinely asserted: 'surgery' (held by no vet) checked via containsString('surgery') with the fixture wired as unheld; 'James Carter' (no specialty) checked via not(containsString('James')) and not(containsString('Carter'))
- @WebMvcTest + @MockitoBean for repositories is the tolerated pattern consistent with the existing suite; MockMvc is the sanctioned in-process web harness
- Factory helpers specialty() and vet() satisfy the brief's factory-method rule; no raw constructor calls in test bodies
- Test data uses meaningful names throughout (dentistry, radiology, surgery, Helen Leary, Linda Douglas, James Carter); no mystery literals
- Linear test bodies, no branching or loops
- @BeforeEach shared setup is immutable reference data, not shared mutable state
- theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage uses model().attributeDoesNotExist('totalPages') to assert the no-pagination requirement mechanically

**code-quality-reviewer**

- SpecialtyController is package-private and uses constructor injection with no @Autowired — consistent with VetController
- SpecialtyDirectoryEntry record is correctly scoped as a package-private nested member; record accessors (name(), veterinarians()) are used without get/set prefixes
- Stream pipelines with sorted Comparator.comparing(Person::getLastName).thenComparing(Person::getFirstName) are clean and idiomatic
- SpecialtyRepository mirrors PetTypeRepository: public JpaRepository extension with a custom @Query carrying ORDER BY — ordering intent is explicit in the query, not left to the caller
- buildDirectory() private-method decomposition (one method per concern) keeps the handler under 10 lines; private helpers are named for what they do, not how
- @WebMvcTest + @MockitoBean for repository dependencies is the correct sanctioned pattern; MockMvc is used for the HTTP transport, not for the internal logic
- Test names read as plain-English acceptance criteria exactly as listed in the PRD; the surgery-with-no-holders edge case (acceptance criterion 2 and the design-block risk) is exercised by the shared @BeforeEach fixture
- checkFormat passed with no violations

**security-reviewer**

- holds() name->ID change is an internal equality over already-loaded Vet/Specialty entities; no user input crosses a trust boundary and no new attack surface is introduced
- SpecialtyRepository.findSpecialties() uses a static JPQL literal with no parameter interpolation - no injection vector
- /specialties.html accepts no request parameters; the round-2 delta adds no input-handling path
- Template renders all user-derived content (specialty.name, vet first/last name) via Thymeleaf th:text, which HTML-escapes by default - no XSS
- renderDirectory() helper and the two added tests are test-only and touch no production trust boundary
- No authentication or authorization surface changed by the round-2 delta

**test-reviewer**

- Finding 1 (stable-order assertion) closed: theSpecialtyDirectoryShouldRenderSpecialtiesInTheOrderTheRepositoryReturns re-stubs findSpecialties() in the deliberate non-alphabetical order [radiology, surgery, dentistry] and calls assertRenderedInOrder(body, 'radiology', 'surgery', 'dentistry'), so an alphabetical regression in the repository layer would fail this test rather than coincidentally pass it
- Finding 2 (grouping assertion) closed: theSpecialtyDirectoryShouldShowVeterinariansByFullName uses assertRenderedInOrder(body, 'dentistry', 'Linda Douglas', 'radiology', 'Helen Leary', 'surgery'), which pins Linda Douglas to the dentistry section and Helen Leary to the radiology section by relative position; wrong-specialty placement cannot produce a false pass
- Finding 3 (within-specialty sort) closed: @BeforeEach now seeds two vets under radiology in reverse alphabetical order (Ortega before Leary); theSpecialtyDirectoryShouldSortVeterinariansWithinASpecialtyByName asserts assertRenderedInOrder(body, 'Helen Leary', 'Rafael Ortega'), exercising the Comparator.comparing(Person::getLastName).thenComparing(Person::getFirstName) path in SpecialtyController.veterinariansHolding()
- Code-quality autofix (holds() ID comparison) applied in production: SpecialtyController.java:74 uses held.getId().equals(specialty.getId()), not name equality; ID path now exercised by the multi-vet radiology fixture
- assertRenderedInOrder private helper uses indexOf strictly-greater-than chaining and is called from straight-line test bodies — the loop is inside a helper method, not a test body, and is semantically a custom assertion rather than test logic
- All six tests pass under ./gradlew test; BUILD SUCCESSFUL with jacocoTestReport generated
- BDD naming school applied consistently across all six tests; factory helpers specialty() and vet() in use throughout; no mystery literals
- The enlarged @BeforeEach fixture (4 vets) is backward-compatible with all pre-existing tests: omission, no-pagination, and full-listing assertions remain valid

**doc-reviewer**

- Round-1 blocked finding resolved: SpecialtyRepository row present at system-design.md line 104, immediately after VetRepository row (line 103), with source pointer and REQ-SPEC-001 in Implements column
- Round-1 blocked finding resolved: SpecialtyController row present at system-design.md line 106, immediately after VetController row (line 105), with source pointer and REQ-SPEC-001 in Implements column
- Round-1 blocked finding resolved: REQ-SPEC-001 added to Vet row Implements column (system-design.md line 100, now REQ-VET-001, REQ-SPEC-001)
- Round-1 blocked finding resolved: REQ-SPEC-001 added to Specialty row Implements column (system-design.md line 101, now REQ-VET-001, REQ-SPEC-001)
- New rows obey the abstraction-level rules: each names its type once, describes the behavioral guarantee in prose, and points at the source file — no field tables, parameter tables, or constant literals
- SpecialtyRepository row description is behavioral: describes ordering and the authoritative-source invariant without transcribing the @Query or any SQL literal
- SpecialtyController row description is behavioral: describes the HTTP surface and the inversion relationship without referencing internal methods or the SpecialtyDirectoryEntry implementation detail
- Cross-document coherence holds: prd.md line 148 Design link (system-design.md#contracts) now resolves to a section complete with respect to REQ-SPEC-001
- PRD REQ-SPEC-001 unchanged and still coherent: anchor at line 135, narrative prose free of prohibited patterns, Done-when bullets testable and tagged, edge cases present, Design link resolves
- All REQ-IDs in system-design.md Implements column trace back to active requirements in prd.md

**code-quality-reviewer**

- Round-1 autofix confirmed applied: holds() at line 74 now compares held.getId().equals(specialty.getId()) rather than name strings — ID-based entity matching is explicit and correct regardless of cache topology
- checkFormat passed with no violations
- buildDirectory() / veterinariansHolding() / holds() decomposition is clean: three single-responsibility private methods, each under 10 lines, named for what they do
- SpecialtyDirectoryEntry record uses record accessors name() and veterinarians() with no get/set prefixes; the List\<Vet> is constructed via .toList() (unmodifiable) so mutability is not a concern
- SpecialtyRepository mirrors PetTypeRepository exactly: public JpaRepository extension, @Query with explicit ORDER BY, no business logic
- renderDirectory() helper eliminates repeated MockMvc boilerplate across four tests; the extraction is complete and idiomatic
- assertRenderedInOrder() now correctly covers (a) specialty-order regression via non-alphabetical re-stub in theSpecialtyDirectoryShouldRenderSpecialtiesInTheOrderTheRepositoryReturns, (b) vet-under-specialty grouping via assertRenderedInOrder(body, 'dentistry', 'Linda Douglas', 'radiology', 'Helen Leary', 'surgery') in theSpecialtyDirectoryShouldShowVeterinariansByFullName, and (c) within-specialty sort via Ortega-before-Leary seeding in @BeforeEach and assertRenderedInOrder(body, 'Helen Leary', 'Rafael Ortega') in theSpecialtyDirectoryShouldSortVeterinariansWithinASpecialtyByName — all three test-reviewer blocked findings from round 1 are addressed
- system-design.md Contracts table now carries SpecialtyController and SpecialtyRepository rows (mirroring the VetController and VetRepository row shapes) and REQ-SPEC-001 added to Implements on both Vet and Specialty — doc-reviewer blocked finding closed
- Test BDD names follow the{Subject}Should{Outcome} convention throughout; two new tests are correctly named
- specialtyList.html uses th:text exclusively (no th:utext), layout fragment via th:replace, and standard Thymeleaf iteration — consistent with vetList.html

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $6.93 | 10m 7s | 91% |
| `spring-boot-claude:system-design-expert` | 2 | opus-4-8 | $4.98 | 3m 49s | 72% |
| `(parent)` | 1 | opus-5 | $2.95 | 25m 15s | 94% |
| `spring-boot-claude:security-reviewer` | 2 | opus-4-8 | $2.60 | 1m 23s | 79% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $1.56 | 4m 32s | 79% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $1.52 | 7m 0s | 87% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $1.48 | 4m 42s | 79% |
| `spring-boot-claude:product-requirements-expert` | 1 | opus-4-8 | $1.46 | 2m 23s | 77% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.25 | 20s | 25% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-4-8 | $4.10 | 6m 2s | 91% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $3.21 | 2m 33s | 69% |
| `(parent)` | opus-5 | $2.95 | 25m 15s | 94% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $2.83 | 4m 4s | 90% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.77 | 1m 16s | 77% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.46 | 2m 23s | 77% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $1.38 | 49s | 79% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $1.22 | 33s | 78% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.96 | 3m 8s | 80% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.85 | 1m 56s | 72% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.76 | 3m 41s | 84% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.76 | 3m 18s | 88% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.72 | 2m 35s | 85% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.52 | 1m 33s | 78% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.25 | 20s | 25% |

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
- model requested `claude-opus-5`; models used: opus-4-8 · opus-5 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `9c6fd220a549ce32` · `2.1.222 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
