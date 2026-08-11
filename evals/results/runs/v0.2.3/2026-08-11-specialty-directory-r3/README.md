# specialty-directory r3 — v0.2.3

Specialty directory page (feature) · started 2026-08-11T16:19:44+00:00 · exec `claude-dev` · status **complete**

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
| review attention (pipeline grade) | clear |

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

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.01 | 35m | 26 | 91% | 18 file(s) +447/−4 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.58 | 4m 32s | 91% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Specialty directory

2 review rounds · 3 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (1) | **✔** |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** | **✔** |

- ◇ **prd-entry** Specialty directory · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **minor** · (design) · ***◷ 37s***
- ◆ **implement** (implementer) · ***◷ 10m***
  - ▲ **build ✓ clean** · build · test · format · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 56s***
  - [autofix] `SpecialtyListingTests.java:104` IntStream is imported (line 19) but theSpecialtyDirectoryShouldListEverySpecialtyOnOnePage references it via the fully-qualified name java.util.stream.IntStream.rangeClosed(...) instead of the imported simple name, leaving the import unused and the call needlessly verbose.
    - fix: Replace java.util.stream.IntStream.rangeClosed(1, 12) with IntStream.rangeClosed(1, 12), using the existing import.
- ✔ **review security** · **approved** · ***◷ 49s***
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `SpecialtyRepository.java:185` SpecialtyRepository.findSpecialties() carries a custom JPQL query (`SELECT specialty FROM Specialty specialty ORDER BY specialty.name`) that is exercised in the test suite only through a Mockito stub in VetControllerTests — no test runs it against a real database. The project's established seam for exactly this (ClinicServiceTests, @DataJpaTest, e.g. shouldFindVets against VetRepository.findAll()) is untouched by this slice. A typo'd JPQL property, a wrong ORDER BY direction, or a broken mapping would pass every test in this change set and still break at runtime — jacoco shows the repository interface at 100% only because a declarative Spring Data interface has no bytecode to instrument, which is exactly the gap testing-principles.md flags: coverage is judged by behavior exercised, not lines touched.
    - fix: Add a @DataJpaTest-backed test to ClinicServiceTests (or a same-shape SpecialtyRepository test) that calls specialties.findSpecialties() against the real seeded H2 test database and asserts the returned specialties are present and ordered by name.
  - [autofix] `SpecialtyListingTests.java:104` theSpecialtyDirectoryShouldListEverySpecialtyOnOnePage calls the fully-qualified java.util.stream.IntStream.rangeClosed(...) even though IntStream is already imported at the top of the file (line 19) — inconsistent with the rest of the file's style.
    - fix: Replace `java.util.stream.IntStream.rangeClosed(1, 12)` with `IntStream.rangeClosed(1, 12)`.
- ✔ **review doc** · **approved** · ***◷ 2m***
- ✔ **review doc** · **approved**
- ↻ **implement** (implementer) ← code-quality, test · (3 findings) · ***◷ 2m***
  - ▲ **build ✓ clean** · build · test · format · handoff-log · autofix-autofix
- ▲ **build-pass** 16:50 · build, test, format, handoff-log, autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 30s***
- ✔ **review test** · **approved** · ***◷ 35s***
- ◆ **grade CLEAR** · add read-only specialty directory page
  - blast_radius — **clear** — Eighteen files look wide but nine of them are translation bundles gaining the same three appended keys; the only edit to existing production code is VetController taking a second constructor argument and a new handler, and everything else is new files inside the vet feature package. No sensitive path, no build, schema, dependency or configuration change, and no existing route, query or template is altered.
  - semantic_surprise — **clear** — Every hunk reads as its description promises. The one non-obvious choice, matching veterinarians to specialties by id rather than by name or instance identity, is deliberate, documented in the Javadoc, and pinned by a test with two same-named specialties; the layout fragment is invoked with a menu argument that matches no navbar item, which I confirmed against fragments/layout.html yields no navigation entry and no highlight; Vet.specialties is EAGER, so assembling outside a session is safe; all dynamic values render through th:text with default escaping. The only latent sharp edge is Objects.equals on ids treating two null-id entities as the same specialty, which the controller path cannot reach because both collections come from the database.
  - test_adequacy — **clear** — The tests assert real outcomes at each layer rather than restating the implementation: eight plain-JUnit tests on the pure factory using real Vet and Specialty objects cover no-holder specialties, multi-specialty veterinarians, total ordering and the same-name-different-id case; the MockMvc test renders actual HTML and asserts Helen Leary appears while the unspecialized James Carter does not, which is the omission rule and the first-then-last name order at once; and a real DataJpaTest exercises the JPQL against seeded H2, closing the gap the test-reviewer flagged. The only line no assertion covers is the cosmetic no-veterinarians placeholder, which no acceptance criterion names.
  - reviewer_hedging — **clear** — The first pass ran the full battery: security and doc approved with empty findings lists, and code-quality and test raised only fixable autofix items, an unused-import style call and the missing real-database test. Both were fixed and both reviewers re-approved with empty findings. The fix pass dispatched only code-quality and test, so the silence of security and doc in that pass is the scoped review plan working as designed, not a hedge.
  - scope_deviation — **clear** — Zero design revisions, zero consultations and zero build retries; the design-block cleared the slice as minor and the delivered file set matches its primary paths, with ClinicServiceTests added only because a reviewer asked for it. The PRD edit is the slice's own requirement entry, and its incidental correction of the stale open-question count from ten to five matches the five unresolved bullets I counted in the file.
  - why — Additive read-only page confined to the vet package; the only edit to existing code is a constructor argument. Deliberate id-based matching is documented and tested, escaping and eager fetch check out, and all four reviewers approved with no residual findings. Confirm and merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyListing and SpecialtyRepository follow the naming rules in docs/architecture-principles.md (no prohibited suffixes, domain-noun value object)
- SpecialtyListing.directoryOf is a pure static factory with a well-documented, deliberate id-based matching strategy (Javadoc explains why identity/name matching would be wrong), matching the design-block's stated risk mitigation
- Comparators (BY_STORED_NAME, BY_VETERINARIAN_NAME) give the directory a total, stable order as required by the PRD, with clear Javadoc explaining the tie-break rationale
- SpecialtyListing is an immutable record with a defensive List.copyOf in its compact constructor
- VetController.showSpecialtyDirectory follows the existing bind-delegate-select shape and constructor injection, consistent with the rest of the controller
- SpecialtyRepository mirrors PetTypeRepository's lookup-repository shape (JpaRepository + explicit ORDER BY query) as the design-block specified
- specialtyList.html follows vetList.html's layout-fragment and table conventions; message keys are correctly reused (vets) or newly added and applied consistently across messages.properties and all nine translated bundles
- No mutable state, no null returns (empty lists instead), no swallowed exceptions, no logging concerns applicable to this pure, read-only slice

**security-reviewer**

- No injection surface added: SpecialtyRepository.findSpecialties() is a static JPQL string with no parameters and no concatenation, matching PetTypeRepository:36; the handler takes no path variable, query parameter, or body, so GET /specialties.html has strictly less request-derived input than /vets.html.
- Output escaping intact: specialtyList.html renders every dynamic value through th:text (listing.name, the vet full-name expression) and message keys through #{}; no th:utext, th:inline, or other escaping bypass appears anywhere under src/main/resources/templates. Thymeleaf default escaping stays on, per security-principles.md Cross-site scripting row.
- No new exposure beyond the recorded baseline: the page discloses veterinarian first and last names and specialty names, exactly the data already served unauthenticated by the existing /vets.html page and the /vets JSON route. The absence of authentication is the demonstration's recorded posture (system-design.md Security Context) and is explicitly not a finding; the change does not leave the application weaker than that baseline. The endpoint and what it exposes are stated in prd.md REQ-VET-003 and in the design-block trust-boundary note.
- No mass-assignment surface: the handler is read-only, binds nothing, and adds no WebDataBinder, so the identifier-disallow rule has nothing to apply to. No file, classpath, or resource path is composed from caller input; the view name is a literal.
- No secrets introduced: a search of the new Java sources, the new template, and the message bundles for credential-shaped names (token, password, secret, apikey) returns nothing; the ten bundle additions are three display labels each.
- No serialization or deserialization entry point added; SpecialtyListing is an immutable record assembled server-side and never bound from a request.
- Supply chain unchanged: build.gradle, the Gradle wrapper, and settings.gradle are absent from the change set (git status confirms), so no dependency, repository, or checksum surface moved and the four dependency checks have nothing to clear.
- No error path added that could carry internal detail outward: the handler has no exception handling and produces no message from data-store state.

**test-reviewer**

- SpecialtyListing.directoryOf has 8 dedicated plain-JUnit unit tests built on real Vet/Specialty objects (no mocks), matching the brief's mocking policy and correctly placing the assembly logic at the base of the pyramid while VetControllerTests stays a thin wiring check — exactly the shape testing-principles.md's 'ratio moves when logic moves' calls for
- The two acceptance criteria most likely to hide behind seed data are both directly tested: theSpecialtyDirectoryShouldListASpecialtyNoVeterinarianHolds (a specialty with zero holders still appears) and theSpecialtyDirectoryShouldGroupVeterinariansBySpecialtyIdRatherThanName (two same-named specialties with different ids are kept separate and a holder is attributed by id, not name or instance identity)
- All four prd.md edge cases for REQ-VET-003 have dedicated tests: no-holder specialty, multi-specialty veterinarian, stable ordering (by name/id then last/first/id), and an empty specialty list
- Test data construction goes through factory methods (specialty(id,name), vet(id,first,last,held...)) with SOME_ID marking the one irrelevant value and no bare mystery literals in assertions; test names follow the the{Subject}Should{Outcome} BDD school
- Four-phase structure (arrange/act/assert separated by blank lines, no phase comments) is followed throughout both test classes
- jacoco reports 100% instruction and line coverage for VetController and SpecialtyListing, clearing the brief's 80% domain-package target

**doc-reviewer**

- New REQ-VET-003 section stays at the PRD's what-altitude: behavioral language throughout, no URL/HTTP verb, no code or type names, no mechanism leak
- All 10 prd-entry acceptance_criteria map onto the Done-when bullets and the four numbered edge cases with no gap or duplication
- Anchor \<a id="req-vet-003">\</a> placed per convention; Design link resolves to the existing #contracts anchor in system-design.md
- Provenance banner correctly marks REQ-VET-003 as the one owner-stated exception and the open-question count (five) matches the five unresolved (non-struck-through) Open Questions bullets
- Two genuinely unresolved questions (entry point, sort order) correctly left as Open Questions rather than false Non-Goals rows, consistent with the section header's 'declined scope' definition; REQ-SYS-001 (outbound nav) and REQ-VET-003 bullet 5 (no inbound link) coexist without contradiction
- docs/system-design.md deliberately left unedited this pass (design verdict: minor, no new pattern); no dangling or broken cross-reference results

**doc-reviewer**

- New  ### Specialty directory  section (docs/prd.md:133-146) follows the narrative + tagged Done-when + Edge-cases + Design-link format exactly, with  \<a id="req-vet-003">\</a>  placed at first mention consistent with every other requirement heading
- No PRD-boundary violations: no mechanism, code identifier, URL literal, algorithm, or rationale prose in the new section; behavioral language throughout ('the page lists specialties rather than the whole roster', not a route or template name)
- Non-Goals table untouched by this change (grep confirms no   NG-n   line in the diff), correctly matching the prd-entry's absent  scope_overrides  field
- Provenance banner correctly amended: REQ-VET-003 is flagged as the one exception to the derived-provenance disclaimer, dated and attributed to the product owner, and the surrounding derived-item language ('Each derived item') is adjusted to keep the disclaimer accurate for the mixed provenance now in the document
- Open Questions count corrected from a stale 'ten' to 'five', matching the five actually-unanswered (non-struck-through) bullets in the Open Questions section, including the two new questions the section itself introduces
- The two new Open Questions bullets (visible entry point, sort order) are properly scoped as open questions, not smuggled-in design decisions or rationale prose
- **Design:** [system-design.md#contracts](system-design.md#contracts)  link resolves to an existing anchor; system-design.md is correctly left unedited for this pass per the design-block's deferred doc-sync plan, so no stale or premature Contracts-table entry was introduced
- All sentences in the new section are under 30 words; no second-person address, vague adjectives, or prohibited relative references ('above'/'below'/'previous')
- 'Specialty directory' and 'veterinarian directory' are page names, not domain vocabulary, consistent with the existing unlisted 'veterinarian directory' precedent in docs/ubiquitous-language.md — no missing term

**code-quality-reviewer**

- src/test/java/org/springframework/samples/petclinic/vet/SpecialtyListingTests.java:104 now uses the imported IntStream.rangeClosed simple name instead of the fully-qualified call, resolving the prior autofix finding
- ClinicServiceTests gained shouldFindSpecialtiesOrderedByName, injecting SpecialtyRepository and asserting containsExactly("dentistry", "radiology", "surgery") against findSpecialties(), giving SpecialtyRepository's ORDER BY query direct test coverage
- the new test's local variable  specialties  shadows the field  this.specialties  but disambiguates correctly, matching the file's existing shadowing convention (e.g.  Collection\<Vet> vets = this.vets.findAll()  at line 214)
- ./gradlew checkFormat passes on the fix delta

**test-reviewer**

- The fully-qualified java.util.stream.IntStream.rangeClosed at SpecialtyListingTests.java:104 now uses the existing IntStream import, matching the rest of the file's style.
- ClinicServiceTests gained an @Autowired SpecialtyRepository specialties field and a real @DataJpaTest test shouldFindSpecialtiesOrderedByName that calls specialties.findSpecialties() against the actual seeded H2 database and asserts containsExactly("dentistry","radiology","surgery") — verified this matches the literal seed order in src/main/resources/db/h2/data.sql (radiology, surgery, dentistry inserted) sorted alphabetically, so the assertion exercises the real ORDER BY name JPQL clause rather than restating insertion order. Confirmed via gradlew test --info that the test executes 'select s1_0.id,s1_0.name from specialties s1_0 order by s1_0.name' against H2 and passes, closing the coverage gap flagged in the prior review (SpecialtyRepository.findSpecialties was previously exercised only through a Mockito stub).
- No new mocking, structure, or naming issues introduced by the fix delta; ran gradlew test on both changed test classes and both are green.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $6.61 | 14m 38s | 94% |
| `(parent)` | 1 | opus-5 | $2.58 | 38m 57s | 95% |
| `agent-team:change-grader` | 1 | opus-5 | $2.58 | 4m 32s | 91% |
| `agent-team:system-design-expert` | 1 | opus-5 | $2.35 | 4m 50s | 88% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $2.33 | 4m 1s | 91% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.50 | 4m 12s | 92% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.22 | 2m 49s | 87% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $1.12 | 1m 41s | 84% |
| `agent-team:security-reviewer` | 1 | opus-5 | $1.11 | 1m 3s | 78% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.07 | 0s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $5.03 | 11m 35s | 94% |
| `(parent)` | opus-5 | $2.58 | 38m 57s | 95% |
| `agent-team:change-grader` | opus-5 | $2.58 | 4m 32s | 91% |
| `agent-team:system-design-expert` | opus-5 | $2.35 | 4m 50s | 88% |
| `agent-team:product-requirements-expert` | opus-5 | $2.33 | 4m 1s | 91% |
| `agent-team:feature-implementer` | opus-5 | $1.58 | 3m 2s | 94% |
| `agent-team:security-reviewer` | opus-5 | $1.11 | 1m 3s | 78% |
| `agent-team:test-reviewer` | sonnet-5 | $0.83 | 2m 9s | 89% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.83 | 2m 39s | 89% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.68 | 1m 33s | 95% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.67 | 1m 4s | 85% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.45 | 36s | 81% |
| `agent-team:test-reviewer` | sonnet-5 | $0.39 | 40s | 82% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.07 | 0s | 0% |

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

- plugin `agent-team-spring-boot` at `v0.2.3` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.227 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
