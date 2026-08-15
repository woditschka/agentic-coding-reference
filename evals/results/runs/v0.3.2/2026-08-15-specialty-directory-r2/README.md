# specialty-directory r2 — v0.3.2

Specialty directory page (feature) · started 2026-08-15T15:15:29+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 4 (±0) | 3 (±1) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.92. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 3 · doc-fit 5

> Pairing logic sits in an immutable, framework-free  SpecialtyDirectory  (SpecialtyDirectory.java:47-90) rather than the controller, and the catalog departure is recorded in the new ADR; minor tension is the third route bolted onto  VetController  (VetController.java:68-74) instead of a controller for the specialty surface, and a  Repository  for  Specialty , a lookup inside the Vet aggregate. Unit tests are behavior-named, four-phase, factory-built, no mocks (SpecialtyDirectoryTests.java:38-140). Controller tests scrape raw HTML ( containsSubsequence ,  doesNotContain("page=") ) and re-test ordering the unit already owns. Biggest gap: the template's  #{specialties}  and  #{none}  keys (specialtyList.html:7,20) have no bundle entries in the patch, yet a test asserts "Fachgebiete"/"keine". Docs — ADR, README, prd, system-design — are all current.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The pairing rule sits in SpecialtyDirectory, not VetController.showSpecialtyDirectory, so no new rule lands in the controller, and the new type is justified by an ADR as the catalog requires. Ordering is stated twice — SpecialtyRepository's  ORDER BY specialty.name  and BY_NAME in  of()  — a small redundancy. specialtyList.html introduces  #{specialties} ,  #{vets} ,  #{none}  yet no message bundle is touched, and VetControllerTests asserts German "Fachgebiete"/"keine"; on the visible evidence those keys are unresolved. SpecialtyDirectoryTests is exemplary: behavior names, blank-line phases, real Vet/Specialty via factories, named ids. Controller tests assert over the whole rendered HTML ( doesNotContain("page=") ), a brittle proxy. Documentation moves everywhere it should: ADR, index, PRD requirement plus open question, contracts table.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 3 · doc-fit 5

> Pairing lives in an immutable  SpecialtyDirectory  (SpecialtyDirectory.java:47) rather than the controller, and a read-only  SpecialtyRepository  matches the Repository pattern; the departure from the catalog is recorded in an ADR. Cost: the route lands in  VetController  (now three surfaces) and ordering is done twice —  ORDER BY specialty.name  in the query plus  orderedSpecialties.sort(BY_NAME) . Unit tests are behavior-named, four-phase, real objects, with empty/held-by-none/unsaved-id boundaries; but  new Specialty()  bypasses the factory,  @MockitoBean SpecialtyRepository  adds a fresh framework stub, and slice tests assert on raw HTML substrings. Chiefly, specialtyList.html uses  #{specialties} / #{none}  and a test asserts "Fachgebiete", "Tierärzte", "keine" while no message bundle is added. Docs (PRD, ADR, contracts) are fully current.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $12.51 | 38m | 37 | 92% | 10 file(s) +552/−8 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.24 | 3m 19s | 87% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPECIALTYDIRECTORY-001 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · **1 build-failure** · grade **CONCERN**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- • intake-decision (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 10m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · checkstyleTest · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain: not verified against the NVD in this review. The OWASP dependency-check plugin is not configured in build.gradle (only cyclonedx-bom 3.2.4 is present), and this reviewer has no network access, so no CVE match ran. The change adds no dependency at all — build.gradle and gradle/ are untouched — so it introduces no new supply-chain surface. For the record, the resolved framework floor is Spring Boot 4.1.0 via the Boot plugin. Closing the NVD check is a human or CI task, not a defect in this slice.
  - ▹ rec: Performance/DoS note (informational, not a finding at this baseline): showSpecialtyDirectory pairs the full specialty and veterinarian tables per request with a nested scan, and SpecialtyRepository.findAll() is uncached while VetRepository.findAll() is cached. Both tables are seed-sized and bounded by stored data rather than by caller input, and the unpaginated /vets route is the existing baseline, so this is not a widening. Worth revisiting only if the clinic data grows.
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `SpecialtyDirectoryTests.java` PRD edge case 2 for REQ-SPECIALTYDIRECTORY-001 ('A clinic that knows no specialties yields an empty directory rather than a failure') has no dedicated test. SpecialtyDirectoryTests covers a specialty held by none, ordering, defensive copying, and the missing-id guard, but never calls SpecialtyDirectory.of with an empty specialties collection, and VetControllerTests never stubs specialtyRepository.findAll() to return an empty collection either. Nothing in the suite would catch a regression that throws or NPEs on an empty specialty list.
    - fix: Add a unit test in SpecialtyDirectoryTests, e.g. `theSpecialtyDirectoryShouldBeEmptyWhenTheClinicKnowsNoSpecialties`, asserting `SpecialtyDirectory.of(List.of(), List.of(veterinarian(...))).getEntries()` is empty; optionally add a matching controller-level test stubbing `specialtyRepository.findAll()` to `List.of()` and asserting the page renders with status 200 and an empty table body.
  - [autofix] `SpecialtyDirectoryTests.java` Test method names in this new file (shouldPairASpecialtyWithTheVeterinariansHoldingTheSameStoredSpecialty, shouldOrderSpecialtiesByNameAndTheirVeterinariansByLastName, shouldListASpecialtyNoVeterinarianHoldsWithNoVeterinarians, shouldPlaceAVeterinarianHoldingNoSpecialtyUnderNoEntry, shouldLeaveTheGivenCollectionsInTheOrderTheyArrivedIn, shouldRefuseASpecialtyThatCarriesNoStoredIdentity) drop the 'the{Subject}' portion of the brief's naming school (testing-principles.md SS Test Naming: `the{Subject}Should{Outcome}`, e.g. `theOwnerSearchShouldMatchOnLastNamePrefix`). The sibling file added in the same change, VetControllerTests, follows the full pattern correctly (e.g. theSpecialtyDirectoryShouldListEverySpecialtyWithItsVeterinarians), so the two new test files in this slice use inconsistent naming for the same feature.
    - fix: Prefix each SpecialtyDirectoryTests method name with 'theDirectory' or 'theSpecialtyDirectory' to match the school, e.g. rename shouldPairASpecialtyWithTheVeterinariansHoldingTheSameStoredSpecialty to theSpecialtyDirectoryShouldPairASpecialtyWithTheVeterinariansHoldingTheSameStoredSpecialty, and likewise for the other five methods.
- ↻ **implement** (implementer) ← test · (2 findings) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyle · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 16s***
- ✔ **review test** · **approved** · ***◷ 29s***
- ◆ **grade CONCERN** · add the specialty directory page
  - blast_radius — **clear** — Ten files but one module and almost entirely additive: two new classes, one new template, one new GET route in the vet package. The only edit to existing runtime code is VetController gaining a second repository in its constructor plus one handler; no config, schema, dependency or sensitive path is touched, and the four doc files are prose.
  - semantic_surprise — **clear** — Read all 23 hunks and nothing behaves other than advertised. The one non-obvious choice, pairing on stored id rather than object equality, is documented in the ADR and design doc and pinned by tests that deliberately feed distinct instances from two reads. SpecialtyDirectory.of copies before sorting so the shared cached vet collection is never reordered, and that is tested directly. The template mirrors vetList.html and escapes every value through th:text, and all four message keys already exist in every bundle, so no i18n gap opens.
  - test_adequacy — **clear** — Not tautological: the unit tests use real Vet and Specialty objects with no mocking, and the controller tests render the real template through MockMvc and assert on produced HTML. Each of the six done-when clauses and both PRD edge cases has a matching assertion, and the tests would fail against a broken implementation, since dropping either sort breaks the containsSubsequence assertions and pairing by object identity breaks the controller tests. No pre-existing assertion was weakened by the enlarged fixture; both prior tests are byte-identical.
  - reviewer_hedging — **concern** — Round two is clean, both dispatched reviewers approved with empty findings, and the two reviewers the fix-delta plan scoped out had already approved. But the security approval carries two unclosed recommendations: no NVD check ran because the reviewer has no network access, and the per-request nested pairing over an uncached full-table specialty read on a public unauthenticated route. The reviewer bounded both as informational and not a widening of the existing unpaginated vet route baseline, and nobody closed them, so they reach the human here.
  - scope_deviation — **clear** — The one design revision is administrative rather than a redesign: the first design-block omitted two doc paths it had itself edited, failed the autofix audit, and was re-appended with the same design and corrected supporting_paths. Zero build retries on code, zero consultations. The diff matches the requirement's stated surface, and the implementation narrowed rather than wandered, reusing four existing message keys instead of adding the ones the first design anticipated.
  - why — The diff read is clean on every axis: contained, additive, honestly tested, no behavioral surprise. The only residual is the security reviewer's parked performance note, an uncached full-table read with a nested scan on a public route, which the reviewer bounded as seed-sized. Confirm you accept that bound, then merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyDirectory.of documents and enforces the copy-before-sort rule that protects the shared VetRepository cache from mutation, with a test (SpecialtyDirectoryTests.shouldLeaveTheGivenCollectionsInTheOrderTheyArrivedIn) covering it directly
- Naming and structure (SpecialtyRepository, SpecialtyDirectory, VetController wiring) match the ADR's documented rationale and the existing VetRepository/vetList.html idioms in the same package, including the trailing-space span pattern in specialtyList.html mirroring vetList.html
- Javadoc on SpecialtyDirectory.of documents preconditions (@throws IllegalArgumentException) and the identity-based pairing rationale; requireStoredIdentity gives a clear, contextual error message
- checkFormat passes cleanly; no formatting issues found
- Entry as a static nested class (not a record) is consistent with the codebase's existing convention of avoiding records for domain/data holders

**doc-reviewer**

- PRD entry for REQ-SPECIALTYDIRECTORY-001 stays behavioral: routes, pairing mechanism, and rationale correctly deferred to system-design.md and the new ADR via links
- Requirement ID and anchor (req-specialtydirectory-001) consistent and unique across prd.md, system-design.md, and the ADR
- system-design.md contracts table and route-count prose updated coherently (second route -> third route) with no stale references left elsewhere
- New ADR follows the template: Status, Context, Options Considered, Decision, Consequences, Implementation with Requirements link, References with em-dashes
- docs/adr/README.md index row added and resolves
- Design-doc claims (SpecialtyRepository uncached, VetRepository cached) verified against source
- No prohibited PRD patterns: no mechanism tables, code identifiers, rationale prose, or hardcoded constants

**security-reviewer**

- XSS: specialtyList.html renders every request-visible value through th:text (entry.specialty.name, vet.firstName/lastName) and the i18n keys through #{...}. No th:utext, no inline JavaScript, no external resource loading, and no request-derived value in Thymeleaf preprocessing (__${...}__) — the layout fragment call passes the literal 'specialties'. Default output escaping stays on, matching the control in docs/security-principles.md.
- Injection into data access: SpecialtyRepository.findAll() uses a fixed JPQL string ('SELECT specialty FROM Specialty specialty ORDER BY specialty.name') with no parameters and no concatenation. The ORDER BY is a compile-time literal, not caller-supplied, so no sort-column injection path exists.
- Least privilege at the repository: SpecialtyRepository extends the bare Repository marker and exposes exactly one read method and no write, so specialties cannot be mutated through the application. This is a narrower surface than the derived-CRUD alternative.
- Exposed surface: /specialties.html is a GET with no request parameters, no path variables, and no request body. It exposes specialty names and veterinarian names, both already public on /vets.html and the /vets JSON route, so it discloses nothing beyond the recorded baseline in system-design.md § Security Context. No mass-assignment surface is added (no form, no WebDataBinder).
- Path traversal / resource resolution: no request-derived value composes a filesystem or classpath path. The view name 'vets/specialtyList' is a fixed literal.
- Shared-state safety: SpecialtyDirectory.of copies the incoming collections before sorting (new ArrayList\<>(specialties), holdersOf builds its own list), so the @Cacheable("vets") collection shared across requests is never reordered or mutated. SpecialtyDirectory and Entry are final, hold List.copyOf snapshots, and expose only immutable views — no unsynchronized mutable state reachable from the singleton controller. SpecialtyDirectoryTests.shouldLeaveTheGivenCollectionsInTheOrderTheyArrivedIn pins this.
- Error handling: the IllegalArgumentException from requireStoredIdentity carries a specialty name only — no credential, connection string, or identifier beyond data already rendered on the page — and error.html renders ${message} through th:text, so even that value is escaped. The path is also unreachable from the web route, since persisted specialties always carry a generated id.
- Resource management: no file handles, streams, executors, regex, XML/JSON/YAML parsing, deserialization, shell execution, or network I/O introduced. No SecureRandom-relevant code. No System.out/System.err and no logging added, so no log-injection or secret-in-log surface.
- Secrets: no hardcoded credential, token, key, or connection string in the diff. build.gradle and gradle/ are unchanged.

**test-reviewer**

- SpecialtyDirectoryTests uses real Vet/Specialty instances throughout with no mocking, matching the brief's real-objects-first policy
- Defensive-copy test (shouldLeaveTheGivenCollectionsInTheOrderTheyArrivedIn) directly verifies the ADR's stated cache-corruption concern with real mutable lists rather than a mock verifying a call
- VetControllerTests reuses MockMvc as the sanctioned transport boundary and stubs only the two repositories at the seam, consistent with the existing file's established pattern
- AssertJ used throughout with no JUnit assertEquals/assertTrue
- Every Done-when acceptance criterion and PRD edge case 1 (specialty held by none) has a dedicated test; jacoco reports 100% instruction and branch coverage on SpecialtyDirectory, SpecialtyRepository, and VetController
- Four-phase structure with blank-line separation, no phase comments, and only load-bearing why-comments (e.g. why ordering happens on copies)

**code-quality-reviewer**

- Both round-1 findings resolved correctly: theSpecialtyDirectoryShouldBeEmptyWhenTheClinicKnowsNoSpecialties covers the empty-specialty-collection edge case, and all six pre-existing test methods now carry the the{Subject}Should{Outcome} prefix, matching the sibling VetControllerTests naming school
- No production code touched by the fix delta; SpecialtyDirectory, SpecialtyRepository, VetController, and specialtyList.html are unchanged from the already-approved round 1
- checkFormat passes cleanly on the fix delta

**test-reviewer**

- Round-1 finding 1 (missing PRD edge case 2 coverage) resolved: theSpecialtyDirectoryShouldBeEmptyWhenTheClinicKnowsNoSpecialties calls SpecialtyDirectory.of(List.of(), List.of(...)) and asserts getEntries() isEmpty(), closing the gap for an empty specialty collection.
- Round-1 finding 2 (naming-school inconsistency) resolved: all six pre-existing SpecialtyDirectoryTests methods and the new one now carry the 'the{Subject}Should{Outcome}' prefix (theSpecialtyDirectoryShould...), matching the sibling VetControllerTests naming in the same slice.
- Fix delta touches only the test file; ./gradlew test (SpecialtyDirectoryTests, VetControllerTests) passes cleanly with no regressions.
- No new mocking, structure, or assertion-style issues introduced by the renames or the new test.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $6.95 | 16m 3s | 95% |
| `agent-team:system-design-expert` | 2 | opus-5 | $4.97 | 8m 46s | 92% |
| `(parent)` | 1 | opus-5 | $3.61 | 41m 19s | 96% |
| `agent-team:change-grader` | 1 | opus-5 | $2.24 | 3m 19s | 87% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $2.02 | 3m 41s | 89% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $1.19 | 1m 43s | 85% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.11 | 2m 51s | 85% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.98 | 1m 30s | 87% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.74 | 1m 25s | 91% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.99 | 11m 23s | 96% |
| `(parent)` | opus-5 | $3.61 | 41m 19s | 96% |
| `agent-team:system-design-expert` | opus-5 | $2.89 | 5m 12s | 93% |
| `agent-team:change-grader` | opus-5 | $2.24 | 3m 19s | 87% |
| `agent-team:system-design-expert` | opus-5 | $2.08 | 3m 33s | 91% |
| `agent-team:product-requirements-expert` | opus-5 | $2.02 | 3m 41s | 89% |
| `agent-team:feature-implementer` | opus-5 | $1.12 | 2m 21s | 91% |
| `agent-team:security-reviewer` | opus-5 | $0.98 | 1m 30s | 87% |
| `agent-team:feature-implementer` | opus-5 | $0.84 | 2m 18s | 92% |
| `agent-team:test-reviewer` | sonnet-5 | $0.82 | 2m 12s | 85% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.74 | 1m 25s | 91% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.71 | 1m 20s | 90% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.48 | 22s | 73% |
| `agent-team:test-reviewer` | sonnet-5 | $0.29 | 39s | 84% |

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

- plugin `agent-team-spring-boot` at `v0.3.2` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.232 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
