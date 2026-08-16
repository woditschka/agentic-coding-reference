# specialty-directory r3 — v0.3.3

Specialty directory page (feature) · started 2026-08-16T02:06:43+00:00 · exec `claude-dev` · status **complete**

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
| 5 (±0) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.66. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController holds no rule — it reads, delegates to the pure factory SpecialtyDirectory.of, and names a view; SpecialtyRepository extends the bare Repository marker, keeping the read-only surface minimal, and the new record is immutable with List.copyOf in both compact constructors. Naming and package placement match the catalog. Tests are BDD-named, four-phase, factory-built, with named constants and whole-Entry comparisons, but the aSpecialty/aVeterinarianNamed factories are duplicated verbatim across SpecialtyDirectoryTests and SpecialtyControllerTests, and theSiteNavigationShouldNotNameTheSpecialtyDirectory only inspects the specialty page's own HTML for href="/specialties.html", so it cannot support the PRD's "any other page" bullet. The template's th:text="${veterinarianName + ' '}" on a self-closing span is a fragile separator. PRD, system-design, vocabulary, ADR index, and all ten bundles move together.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyDirectory.of() keeps the grouping a pure, framework-free function; SpecialtyController only reads, delegates and names a view (package-private, constructor-injected), and SpecialtyRepository follows the repository pattern with a read-only marker interface — an ADR records the choice. Unit tests are behavior-named, factory-built, phase-separated and compare whole Entry records (SpecialtyDirectoryTests). Three dings: aSpecialty/aVeterinarianNamed are duplicated verbatim across SpecialtyControllerTests and SpecialtyDirectoryTests instead of extracted into shared vocabulary; theSiteNavigationShouldNotNameTheSpecialtyDirectory only inspects the directory page itself, so it does not verify the PRD bullet about other pages; and NO_VETERINARIANS_PLACEHOLDER hard-codes bundle text, making the assertion locale-fragile. Documentation (PRD, ADR index, system-design contracts, ubiquitous-language, all message bundles) is current.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Grouping lives in the immutable  SpecialtyDirectory  record with a pure static  of(...) , so  SpecialtyController.showSpecialtyDirectory  only reads, delegates and names a view — no new controller rule; naming, the read-only  SpecialtyRepository  marker interface and the vet-package placement match the catalog, and an ADR records the two-reads choice. Unit tests are exemplary: BDD names, factories, named constants, anonymous  someVeterinarianHolding , defensive-copy coverage. Deductions:  aSpecialty / aVeterinarianNamed  are duplicated verbatim in both test classes against the shared-vocabulary rule;  theSpecialtyDirectoryShouldRenderEverySpecialtyOnOnePage  mixes view name,  attributeDoesNotExist("currentPage","totalPages")  and content concerns;  theSiteNavigationShouldNotNameTheSpecialtyDirectory  only inspects the specialty page itself, not "any other page" as the PRD bullet states. Docs (PRD, system-design, vocabulary, ADR index, ten message bundles) are fully current.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $12.83 | 35m | 35 | 92% | 21 file(s) +591/−7 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.69 | 1m 56s | 84% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPECIALTYDIRECTORY-001 — Specialty directory lists every specialty with the veterinarians holding it

2 review rounds · 2 build-passes · **1 build-failure** · grade **CONCERN**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | **✔** | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Specialty directory lists every specialty with the veterinarians holding it · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 9m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · handoff-validate · audit-autofix · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 45s***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain: no OWASP Dependency-Check plugin is configured in build.gradle and this reviewer has no network access, so no NVD match ran — that check is not run, not clean. The change set touches no dependency declaration (build.gradle, settings.gradle, and gradle/ are unmodified), so it adds no supply-chain surface; closing the NVD gap is a repository-level task for CI or a human, not a defect of this slice.
  - ▹ rec: Defensive, non-blocking: SpecialtyDirectory.fullName concatenates getFirstName() and getLastName() without a null guard, so a row with a null name would render the literal "null". Bean validation on Vet makes this unreachable through the application's own write paths, and the values are HTML-escaped either way, so this is cosmetic rather than a security defect.
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [autofix] `SpecialtyControllerTests.java:84-96` The template's empty-holder branch (`th:if="${entry.veterinarianNames.empty}"`, rendering the `noVeterinarians` message key) is never exercised at the rendering layer. `theSpecialtyDirectoryShouldRenderEverySpecialtyOnOnePage` already stubs SURGERY with no holder but only asserts the page contains the specialty and holder names — it never asserts the 'no veterinarians' placeholder text actually renders for that row. The unit test `SpecialtyDirectoryTests.theSpecialtyDirectoryShouldListASpecialtyNoVeterinarianHolds` covers the data model producing an empty holder list, but that leaves the template's conditional branch — the part that actually satisfies PRD edge case 1 ('A specialty that no veterinarian holds is still listed, with no veterinarian named under it') for a real reader — unverified end to end.
    - fix: Add `.andExpect(content().string(containsString("no veterinarians")))` (or resolve the message via MessageSource) to `theSpecialtyDirectoryShouldRenderEverySpecialtyOnOnePage`, or add a dedicated controller test asserting the placeholder text renders for a specialty with no holder.
- ↻ **implement** (implementer) ← test · (1 finding) · ***◷ 2m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · handoff-validate · audit-autofix · contracts-sync
- ✔ **review test** · **approved** · ***◷ 42s***
- ✔ **review security** · **approved** · ***◷ 46s***
  - ▹ rec: Supply chain: unchanged from round 1 and still not verified. No OWASP Dependency-Check plugin is configured in build.gradle and this reviewer has no network access, so no NVD match ran — that check is not run, not clean. The fix delta touches no dependency declaration, so it adds no supply-chain surface; closing the NVD gap is a repository-level task for CI or a human, not a defect of this slice.
  - ▹ rec: Carried forward from round 1, still non-blocking: SpecialtyDirectory.fullName concatenates getFirstName() and getLastName() with no null guard, so a row with a null name would render the literal "null". Bean validation on Vet makes this unreachable through the application's own write paths and the values are HTML-escaped either way, so it is cosmetic rather than a security defect.
- ✔ **review doc** · **approved** · ***◷ 10s***
- ✔ **review code-quality** · **approved** · ***◷ 50s***
- ◆ **grade CONCERN** · add read-only specialty directory page
  - blast_radius — **clear** — 21 files but one module and no existing Java touched: three new types plus a template under vet/, and a three-key append to the end of ten message bundles. Zero deletions in src, no sensitive paths, no dependency or config change.
  - semantic_surprise — **clear** — Read every hunk. SpecialtyDirectory.of is a pure static factory with explicit ordering and defensive List.copyOf at both record boundaries; both edge cases fall out of iterating the specialty list rather than a branch; the template mirrors the existing vet-list span pattern and escapes every value through th:text. The two residuals are documented and benign: grouping keys on specialty name so two rows sharing a name would share holders, and fullName would render the literal null for a null name, which bean validation makes unreachable.
  - test_adequacy — **clear** — Tests use real Vet and Specialty objects and drive real Thymeleaf rendering through MockMvc, asserting outcomes rather than restating the implementation: stored names, full-name ordering by last then first, a specialty nobody holds, an empty clinic, the vet holding nothing being absent from the page, and no link to the route. The round-1 gap on the noVeterinarians branch was closed with a rendering-level assertion, and the full-context integration test validates the new @Query and controller bean at bootstrap.
  - reviewer_hedging — **concern** — Three of four reviewers approved with empty findings, but the security-reviewer's round-2 approval carries a recommendations list: the supply-chain check is explicitly not run rather than clean (no Dependency-Check plugin, no NVD access), and the null-name concatenation note is carried forward from round 1 as non-blocking.
  - scope_deviation — **clear** — Zero build retries and zero consultations; the single design revision was a re-triage that restated the same new verdict only to add the ADR index row to supporting_paths. The diff matches the PRD surface exactly and honors both owner decisions: read-only, and no navigation entry, which a test asserts.
  - why — The code itself is clean on a full read: additive, contained, well-tested, no behavioral surprise. The one hedge is the security reviewer's own caveat that the supply-chain check was never run, plus a carried-forward null-name note. Skim the diff, then decide whether an unverified NVD gate blocks merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyController stays a thin delegator (constructor injection, package-private, one model attribute) mirroring VetController's shape exactly
- SpecialtyDirectory is an immutable record with a pure static factory; grouping/formatting logic is fully contained there per the design's controller-purity risk mitigation, and both edge cases (unheld specialty, holder of nothing) fall out of the loop structure with no branch
- SpecialtyRepository extends the plain Repository marker (not JpaRepository/CrudRepository), correctly encoding the read-only, uncached scope as a property of the type, matching PetTypeRepository's @Query ORDER BY shape
- specialtyDirectory.html mirrors vetList.html's existing space-separated th:each list pattern (including the empty-case span) rather than inventing a new rendering idiom
- All user-facing strings route through message keys (specialty, specialtyDirectory, noVeterinarians) present in messages.properties and all nine non-English bundles, with messages_en.properties correctly left empty per the fallback convention
- checkFormat passes; no System.out/println, no swallowed exceptions, no abbreviations or get/set-prefixed record accessors

**doc-reviewer**

- PRD entry stays behavioral: no mechanism, code-element name, or rationale prose; Design and requirement links resolve
- New ubiquitous-language entries (Specialty directory) match the term used in prd.md, system-design.md, and file/template naming, with an Avoid list covering rejected synonyms
- ADR follows the template: em-dash References, Requirements line under Implementation, options-considered structure
- system-design.md Contracts rows for the four new types cite REQ-SPECIALTYDIRECTORY-001 consistently with prd.md; the new SpecialtyDirectory invariant sentence and Open Question 5 update stay under the 30-word sentence limit and read at the correct abstraction level (no field/parameter tables)
- docs/adr/README.md carries the index row for the new ADR
- No prohibited words, second-person address, or unmeasured vague adjectives in the added prose

**security-reviewer**

- No injection into data access: SpecialtyRepository.findSpecialties() is a static JPQL string with no parameters and no request-derived value; the read is @Transactional(readOnly = true) and the interface extends the plain Repository marker, so no write path is exposed (least privilege).
- No XSS surface introduced: specialtyDirectory.html renders every dynamic value through th:text (entry.specialtyName, veterinarianName, and the #{...} message keys). No th:utext, no inline script, no external resource load, no Thymeleaf preprocessing (__${...}__), no href. Default escaping stays on.
- Endpoint exposure is not widened beyond baseline: GET /specialties.html takes no request parameter, no path variable, and no request body. The data it renders (specialty names, veterinarian full names) is already served by /vets.html and /vets, so no new information class reaches an unauthenticated caller.
- Mass assignment not applicable and pattern-consistent: the handler binds only Model, so there is no request-bound type to disallow an identifier on. The absence of @InitBinder matches the neighbouring read-only VetController; the binding controllers (Owner, Pet, Visit) keep their disallow lists untouched.
- No path traversal: the view name is the private static final constant VIEW_SPECIALTY_DIRECTORY, never composed from caller input.
- Thread safety under singleton scope: SpecialtyController holds only final repository references; SpecialtyDirectory and its Entry are records whose compact constructors run List.copyOf, and the shared Comparator is static final and stateless. Nothing mutates the @Cacheable("vets") instances returned by VetRepository.findAll() — SpecialtyDirectory.of only reads them into fresh collections.
- No secrets, credentials, or sensitive data added: a diff-wide search for password/secret/token/key/credential material returns nothing in the change set; the eleven message bundles add only display strings.
- No unsafe deserialization, shell execution, file I/O, system-tmp use, logging, System.out/System.err, or regex added anywhere in the change set.
- Resource footprint unchanged in kind: both reads are unpaged full-table reads, but VetRepository.findAll() is the pre-existing cached read already used by /vets, and Specialty is a small reference table with an EAGER association, so no new unbounded-allocation path is introduced.

**test-reviewer**

- SpecialtyDirectoryTests covers every REQ-SPECIALTYDIRECTORY-001 acceptance criterion at the unit level: stable specialty order, full-name holder listing, omission of unheld specialties from holder lists, a specialty nobody holds still listed, empty-specialty-catalog produces no entries, deterministic last-name-then-first-name holder ordering, and defensive copying against later mutation of the source collections
- Three-tier data naming is clean throughout both test files: RADIOLOGY/SURGERY/DENTISTRY and HOLDER_FIRST_NAME/HOLDER_LAST_NAME are role-named constants, factory methods (aSpecialty, aVeterinarianNamed, someVeterinarianHolding) eliminate constructor calls and mystery literals, and the distinct names used in the sort-order test (Rafael Ortega, Linda Douglas, Ada Douglas) are meaningful data driving that assertion, not filler
- Mocking stays within the brief's policy: SpecialtyDirectoryTests uses only real Vet/Specialty value objects with no mocking; SpecialtyControllerTests mocks only the repositories behind the sanctioned MockMvc web-layer boundary, consistent with the existing VetControllerTests idiom (BDDMockito given(), MockMvcResultMatchers/Hamcrest assertions)
- Navigation requirement (no link to the specialty directory from any other page) is verified both structurally (no other template references specialties.html) and by an explicit negative-content assertion on the specialty page itself
- REQ-LANG-002 (reader's-language rendering) is covered by the project-wide I18nPropertiesSyncTest key-parity check rather than needing a per-feature duplicate
- All new tests follow the the{Subject}Should{Outcome} BDD naming school and four-phase structure with no phase comments
- ./gradlew test passes cleanly for the full Specialty* suite

**test-reviewer**

- The round-1 autofix finding (empty-holder template branch unverified end to end) is resolved precisely: theSpecialtyDirectoryShouldNameNoVeterinarianUnderASpecialtyNobodyHolds asserts the rendered noVeterinarians placeholder text via MockMvc, closing the gap between the unit-level empty-list coverage and the template's th:if branch
- New test reuses the file's existing factories (aSpecialty, aVeterinarianNamed, givenTheClinicKnows) and RADIOLOGY/SURGERY constants rather than introducing parallel setup, and follows the the{Subject}Should{Outcome} naming already established in the file
- NO_VETERINARIANS_PLACEHOLDER constant is introduced with a doc comment tying it to the noVeterinarians message key, avoiding a mystery literal
- ./gradlew test passes cleanly for the full Specialty* suite; no regressions introduced by the fix delta

**security-reviewer**

- Fix delta is test-only and adds no attack surface: the sole change since the round-1 basis tree (b3e53ae) is one added MockMvc test plus a private static final String constant in SpecialtyControllerTests. No production source, template, message bundle, build file, or dependency declaration moved.
- No new input reaches a sensitive operation: the added test drives the existing parameterless GET /specialties.html through MockMvc with hard-coded fixture values (RADIOLOGY, SURGERY, "Helen", "Leary"). No request parameter, path variable, or body is introduced.
- No secrets in the delta: the added constant NO_VETERINARIANS_PLACEHOLDER holds the default-locale rendering of the noVeterinarians message key, a UI string, not a credential. No token, password, key, or connection string appears in the delta.
- Escaping unchanged and still correct: the assertion exercises the #{noVeterinarians} message path in specialtyDirectory.html, which renders through th:text. No th:utext, inline script, external resource load, or Thymeleaf preprocessing (__${...}__) was added.
- Round-1 approved aspects re-confirmed as still standing on the unchanged production surface: static parameterless JPQL in SpecialtyRepository under @Transactional(readOnly = true) on the plain Repository marker (no write path), constant view name (no path traversal), and immutable records with defensive List.copyOf under singleton controller scope (no shared mutable state).

**doc-reviewer**

- Fix-delta since the round-1 basis (b3e53ae) touches only src/test/java/.../SpecialtyControllerTests.java (one new test plus a named constant) — no documentation file changed, so the round-1 documentation approval (line 18) stands unmodified.
- The new test's name and its NO_VETERINARIANS_PLACEHOLDER constant read as plain test-data naming, not a new domain term; nothing here requires a docs/ubiquitous-language.md entry.
- docs/prd.md, docs/system-design.md, docs/adr/2026-08-16-specialty-directory-read-model.md, docs/adr/README.md, and docs/ubiquitous-language.md remain unchanged from the previously reviewed tree; cross-references and requirement anchors still resolve as verified in round 1.

**code-quality-reviewer**

- The fix delta (SpecialtyControllerTests.java only) directly closes the round-1 test-reviewer finding: theSpecialtyDirectoryShouldNameNoVeterinarianUnderASpecialtyNobodyHolds asserts the noVeterinarians placeholder actually renders at the MockMvc layer, not just in the unit-level data model.
- The new NO_VETERINARIANS_PLACEHOLDER constant's value ("no veterinarians") matches messages.properties' noVeterinarians key and the template's default text exactly, and carries a doc comment naming the key it renders.
- The new test follows the existing the{Subject}Should{Outcome} naming convention and reuses the file's existing aSpecialty/aVeterinarianNamed/givenTheClinicKnows fixtures rather than duplicating construction logic.
- checkFormat and compileJava both pass on the current tree; no formatting or compilation regressions introduced by the fix.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $7.25 | 15m 51s | 94% |
| `agent-team:system-design-expert` | 2 | opus-5 | $4.60 | 6m 29s | 91% |
| `(parent)` | 1 | opus-5 | $3.71 | 36m 36s | 95% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $2.08 | 3m 40s | 88% |
| `agent-team:security-reviewer` | 2 | opus-5 | $1.72 | 2m 17s | 88% |
| `agent-team:change-grader` | 1 | opus-5 | $1.69 | 1m 56s | 84% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.22 | 2m 17s | 93% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.16 | 2m 42s | 87% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $1.16 | 2m 7s | 92% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.54 | 10m 32s | 95% |
| `(parent)` | opus-5 | $3.71 | 36m 36s | 95% |
| `agent-team:system-design-expert` | opus-5 | $3.46 | 4m 48s | 91% |
| `agent-team:product-requirements-expert` | opus-5 | $2.08 | 3m 40s | 88% |
| `agent-team:change-grader` | opus-5 | $1.69 | 1m 56s | 84% |
| `agent-team:feature-implementer` | opus-5 | $1.69 | 2m 25s | 90% |
| `agent-team:system-design-expert` | opus-5 | $1.13 | 1m 41s | 89% |
| `agent-team:feature-implementer` | opus-5 | $1.01 | 2m 54s | 94% |
| `agent-team:security-reviewer` | opus-5 | $0.99 | 1m 26s | 88% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.80 | 1m 22s | 94% |
| `agent-team:test-reviewer` | sonnet-5 | $0.79 | 1m 53s | 89% |
| `agent-team:security-reviewer` | opus-5 | $0.73 | 51s | 88% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.64 | 1m 2s | 91% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.52 | 1m 4s | 93% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.42 | 54s | 91% |
| `agent-team:test-reviewer` | sonnet-5 | $0.38 | 49s | 83% |

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
