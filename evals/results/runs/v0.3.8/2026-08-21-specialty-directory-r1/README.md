# specialty-directory r1 — v0.3.8

Specialty directory page (feature) · started 2026-08-21T11:35:15+00:00 · exec `claude-dev` · status **complete**

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

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 3 (±0) | 3 (±1) | 3 (±0) | 4 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.64. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 4

> Placement, naming, constructor injection and package-private visibility fit the vet package well, and the ADR reasons carefully about the unidirectional association. But  groupHoldersBySpecialty / holds  in SpecialtyController.java add a new rule to a controller — the sanctioned Domain service is 'available, not currently used' and the ADR never weighs it — widening the pyramid gap the testing principles call out. The template references  #{specialties}  and  #{none}  while no message bundle is touched, so REQ-LANG-002 (asserted in the new prd.md section) is unsupported;  stringContainsInOrder("dentistry","none",...)  would still pass on  ??none_en?? . Tests are BDD-named and factory-built, but default to Mockito stubs, a shared @BeforeEach fixture, HTML-substring absence assertions, and a loop/branch-laden file-scanning link test. Docs are otherwise thorough.

**Sample 2** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 4

> Placement, naming, and constructor injection fit (SpecialtyController/SpecialtyRepository in the vet package), but groupHoldersBySpecialty/holds and BY_LAST_NAME_THEN_FIRST_NAME_THEN_ID are a pure, framework-free rule living in a controller — the catalog's sanctioned Domain service needs no ADR, and the ADR argues only against inverse mapping and tuple queries. Consequently every new test boots MockMvc and stubs both repositories with @MockitoBean, widening the pyramid gap. Names are BDD-correct and factories used, but SpecialtyDirectoryLinkAbsenceTests hand-rolls a walk/loop/StringBuilder/fail() report, violating linearity and fluent assertions; assertions like not(containsString("\<form")) are brittle proxies. specialtyList.html references #{specialties}, #{vets}, #{name}, #{none} with no bundle entries added, so REQ-LANG-002 is broken and the tests pass only because "??none_en??" contains "none". Docs are otherwise thorough.

**Sample 3** — design-fit 3 · test-quality 4 · maintainability 3 · doc-fit 5

> The inverse-view assembly (groupHoldersBySpecialty, holds, BY_LAST_NAME_THEN_FIRST_NAME_THEN_ID in SpecialtyController.java) is pure logic that could live in a domain service and be unit-tested without booting MVC; placing it in a controller adds a new rule to the very deviation the catalog says does not extend, and the ADR argues store-shape options without naming the Web-controller pattern departed from. Tests are BDD-named, factory-built, and cover empty/unheld/no-specialty edges, but specialtyList.html introduces #{specialties} and #{none} with no bundle entries in the patch, which REQ-LANG-002's key-comparison test would catch; SpecialtyDirectoryLinkAbsenceTests loops and branches and depends on a CWD-relative path. Docs (PRD, contracts, ADR, index, open questions) are consistently updated.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.33 | 51m | 41 | 93% | 9 file(s) +492/−5 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.06 | 3m 22s | 92% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPECIALTYDIRECTORY-001 — Specialty directory lists each specialty with the veterinarians holding it

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | · |
| **doc** | ✎ (1) | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Specialty directory lists each specialty with the veterinarians holding it · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◈ **design-block** **new** · (design) · supersedes L5
- ◆ **implement** (implementer) · ***◷ 7m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain was not verified against the NVD in this review: no OWASP dependency-check plugin is configured and the reviewer has no network access. The diff adds no dependency and does not touch build.gradle, so the resolved artifact set is unchanged by this slice - a human or CI still owns the standing NVD check for Spring Boot 4.1.0 and its transitive Jackson.
  - ▹ rec: Availability note, not a defect today: the directory reads the whole veterinarian roster unpaged (VetRepository.findAll) and groups it in memory at O(specialties x vets). The ADR records this as holding only while the roster stays a small reference list; if the roster ever grows or becomes externally writable, the page becomes an unbounded-allocation surface and should move behind a paged or repository-side query.
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 1m***
  - [autofix] `I18nPropertiesSyncTest.java` PRD 'Done when' bullet 6 ('no page of the system carries a link to the specialty directory') is covered only by the implementer's manual diff inspection, not by a test. The implementer's stated reason -- 'a repo-wide link scan would be a brittle new test outside the slice' -- does not hold: the suite already has exactly this shape of test. I18nPropertiesSyncTest#checkNonInternationalizedStrings (src/test/java/.../system/I18nPropertiesSyncTest.java) walks every .html file under src/main with Files.walk and asserts a property text-pattern against all of them; it is not brittle and is an established, working pattern in this codebase. A same-shaped test -- walk src/main/resources/templates, assert no file contains a link/href to '/specialties.html' or 'specialties.html' as an href/th:href target -- is cheap, non-brittle by the same precedent, and turns a currently-silent regression (someone later adds a nav link) into a red test instead of a manual-inspection-only guarantee. This acceptance bullet is explicitly enumerated in prd.md and in the prd-entry's acceptance_criteria; leaving it test-free means a future violation ships silently.
    - fix: Add a repo-scanning test (new test class or a method alongside SpecialtyControllerTests / I18nPropertiesSyncTest) that walks src/main/resources/templates and fails if any template contains an href or th:href targeting '/specialties.html'.
  - [autofix] `SpecialtyControllerTests.java:192-199` PRD edge case 3 ('a clinic that knows no specialty yields a page that renders with nothing listed rather than failing') is only partially exercised. The test asserts status 200 and the view name, but never asserts that nothing is listed -- it does not check the response body at all. A regression that rendered a stray row, a null-pointer-swallowed placeholder, or leftover fixture data would still pass this test.
    - fix: Add a body assertion, e.g. content().string(not(containsString("\<td"))) or an equivalent check that the specialties table body is empty, so the test actually verifies 'nothing listed' rather than only 'did not throw'.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [autofix] `2026-08-21-unidirectional-vet-specialt` The ADR's References section lists two links with no description, unlike every sibling ADR (e.g. 2026-07-31-feature-package-organization.md, 2026-07-31-database-enforced-pet-name-uniqueness.md), which pair each link with an em-dash-separated description. documentation-standards.md § ADR References requires 'Use em-dashes to separate links from descriptions, not hyphens' and the Structural Checks item 'ADR References use em-dashes'.
    - fix: \- [system-design.md#contracts](../system-design.md#contracts) — the Vet/Specialty association invariant and the new Contracts rows - [Feature-Package Organization Without a Service Layer](2026-07-31-feature-package-organization.md) — the package this controller and repository land in
- ✚ **doc-autofix** `docs/adr/2026-08-21-unidirectional-vet-specialty-association.md` · writing-standards · (root)
- ↻ **implement** (implementer) ← test · (2 findings) · ***◷ 3m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 8s***
- ✔ **review code-quality** · **approved** · ***◷ 55s***
- ✔ **review test** · **approved**
- ◆ **grade CLEAR** · add read-only specialty directory page
  - blast_radius — **clear** — Nine files in one module, fourteen hunks, no sensitive paths, and no existing production file touched: three new Java/HTML sources plus two new test classes, with the only edits landing in docs. The one outward-facing addition is a new unauthenticated GET /specialties.html, and it exposes the same vet and specialty names already published on /vets.html, so it widens no data boundary.
  - semantic_surprise — **clear** — The controller does exactly what its size and description imply: read specialties in name order, sort vets by last-then-first-then-id, group holders per specialty into a LinkedHashMap, render. I checked the traps and none bite - the cached Vet collection is only streamed, never mutated; holds() compares specialty ids across two repository reads rather than object identity, which is correct since Specialty inherits no equals; the layout menu name specialties matches no nav item so no navigation entry appears; every text node goes through th:text with a pre-existing message key, so no new translation debt and no unescaped output.
  - test_adequacy — **clear** — Nine tests that assert real outcomes rather than restate the implementation: stringContainsInOrder pins the two-way sort tiebreak, a negative assertion pins the no-specialty vet absence, the empty-clinic case asserts an empty table body rather than only a 200, and a template-walking test guards the deliberate absence of any link, a property no request against the page could observe. The test-reviewer independently reproduced red for both of its round-1 findings before approving, which is stronger evidence than a green suite the author wrote.
  - reviewer_hedging — **clear** — All four dispatched reviewers ended at approved with empty findings; the round-2 roster of code-quality, test and doc reviewers is the plan's own, so security's silence in that round is expected rather than a gap. The security approval carries two recommendations, and neither is a parked reservation about this code: the NVD note is a standing project gap on a diff that adds no dependency, and the unpaged-roster read was accepted in the ADR's Consequences before implementation and is served by the existing cached vets read.
  - scope_deviation — **clear** — The diff matches the requirement's stated surface with nothing extra: no navigation link, no request parameter, no write path, no touch to Vet, Specialty or fragments/layout.html. Zero consultations and zero build retries; the single design revision was a bookkeeping supersede adding two missing doc paths, not a scope fight. The departure from the PRD's advisory file_targets, a new SpecialtyController instead of a second surface on VetController, was decided and reasoned in the design block and approved by the code-quality reviewer.
  - why — Purely additive slice in one package: no existing production file is modified, the new route exposes data already public elsewhere, and the tests assert ordering, absence and the empty case rather than restating the code. Confirm and merge. The one thing worth a glance is the ADR's accepted consequence that the page reads the whole vet roster unpaged.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- No untrusted input reaches the new code: GET /specialties.html takes no path variable, request parameter, header, or body, so the injection, validation, and path-traversal classes have no entry point on this surface
- All user-derived output in templates/vets/specialtyList.html goes through th:text (specialty name, vet first/last name), which HTML-escapes; no th:utext, no inline JavaScript, no external resource loading, and no Thymeleaf preprocessing (__${...}__) anywhere in the template tree
- SpecialtyRepository.findSpecialties uses a static @Query with no parameters and no string concatenation - no JPQL/SQL injection surface; @Transactional(readOnly = true) matches the neighbouring VetRepository pattern
- SpecialtyController is a stateless singleton: the only field state is two injected repositories plus a static Comparator; the cached Vet collection from VetRepository.findAll is read through stream().sorted().toList() and Vet.getSpecialties returns a fresh sorted copy, so no shared mutable state is written per request
- No new dependency, no deserialization, no file or process I/O, no logging of any value, no credentials or secrets introduced anywhere in the diff (swept for password/secret/token/key/credential across the full change set)
- Route exposes only vet names and specialty names, the same data already public on /vets.html - the new endpoint widens no data boundary; absent access control is NG-1, a recorded non-goal, not a finding

**code-quality-reviewer**

- SpecialtyController and SpecialtyRepository closely mirror the project's existing patterns (VetController's package-private @Controller with constructor injection and a private model-assembly helper; VetRepository's Repository\<T,Integer>+@Transactional(readOnly=true) shape rather than PetTypeRepository's JpaRepository base, which fits the vet package's own precedent)
- Naming follows architecture-principles.md#naming: domain noun + Controller/Repository, no prohibited suffixes
- The holds() helper compares Specialty by id rather than reference, with a javadoc explaining why (specialties are read via two separate repository calls); Specialty inherits no equals/hashCode override from NamedEntity/BaseEntity, so this is a correct and defensive choice, not a stylistic one
- groupHoldersBySpecialty keeps the controller handler short and readable via stream pipelines over manual loops, matching the Design Principles checklist
- specialtyList.html mirrors vetList.html's markup and message-key reuse (specialties, name, vets, none) exactly, satisfying REQ-LANG-002 with no new translation burden
- checkFormat and compileJava both pass clean on the change set

**test-reviewer**

- Mocking stays within the brief: @MockitoBean on SpecialtyRepository/VetRepository under @WebMvcTest is the sanctioned web-boundary mock, and no verify(...) restates an outcome already covered by content assertions.
- Test data follows the three-tier convention: RADIOLOGY_ID/SURGERY_ID/DENTISTRY_ID are named by role, vet factory methods (jamesCarter, helenLeary, lindaDouglas, carlaJenkins, alanJenkins) are meaningful named fixtures with javadoc explaining why each name was chosen (e.g. carlaJenkins/alanJenkins sharing a last name to test the last-name-then-first-name sort), no bare mystery literals.
- BDD naming school followed throughout (the{Subject}Should{Outcome}); AssertJ/Hamcrest content matchers used fluently, no JUnit assertEquals/assertTrue.
- All three prd.md edge cases have a targeted test (specialty held by no vet; stable order by last-name-then-first-name-then-id, including a two-way tiebreak case; empty-clinic renders rather than fails), and the no-write-surface assertion (no \<form>, no \<input>) is correctly page-local since the shared layout fragment itself carries neither.
- Dynamic check: ./gradlew test --tests SpecialtyControllerTests passes all 8 tests green.

**doc-reviewer**

- docs/prd.md: new Specialty directory section carries the anchor, tagged requirement, Done-when bullets, and edge cases at the correct narrative/tagged-bullet levels; no route literal, no mechanism, no rationale prose leaks into the PRD
- docs/prd.md: Context paragraph and Open Questions updated coherently with the new requirement; NG-2 correctly left untouched since it scopes management, not reading
- docs/system-design.md: two new Contracts rows (SpecialtyRepository, SpecialtyController) and the requirement id correctly joined to the Vet, Specialty, and VetRepository rows; new invariants sentence carries the ADR back-link; no field/parameter tables, no constant literals, no route literal transcribed
- docs/adr/2026-08-21-unidirectional-vet-specialty-association.md: Context/Options/Decision/Consequences follow the template; Implementation section carries the correct **Requirements:** line
- docs/adr/README.md: index row added in correct date order with matching title and Accepted status
- Cross-document coherence: Specialty and Veterinarian terms match ubiquitous-language.md; all anchors and cross-references resolve; route literal is consistently and deliberately absent from both prd.md and system-design.md per the documented rationale

**doc-reviewer**

- docs/adr/2026-08-21-unidirectional-vet-specialty-association.md: round-1 References autofix applied verbatim — both links now carry em-dash-separated descriptions matching the proposed fix exactly, resolving the sole round-1 finding
- Round-2 delta is test-only (new SpecialtyDirectoryLinkAbsenceTests, one added assertion in SpecialtyControllerTests) and needs no PRD, system-design, or ADR change: it exercises the already-documented no-link acceptance criterion rather than introducing new behavior or scope

**code-quality-reviewer**

- SpecialtyDirectoryLinkAbsenceTests follows the established template-walking test pattern (mirrors I18nPropertiesSyncTest): try-with-resources Files.walk, accumulate-then-fail reporting, descriptive Javadoc explaining why the regex is deliberately wider than an href-shaped pattern
- BDD test naming (theSpecialtyDirectoryShouldBeLinkedFromNoPage) matches docs/testing-principles.md's the{Subject}Should{Outcome} convention and the file's package-private class visibility matches its sibling SpecialtyControllerTests
- New assertions in theSpecialtyDirectoryShouldRenderWhenTheClinicKnowsNoSpecialty verify actual body content (id="specialties" present, no \<td> rows) instead of only the view name, and are correct against templates/vets/specialtyList.html
- checkFormat passes cleanly; no production code touched

**test-reviewer**

- Finding 1 (round 1) resolved with a deliberate, well-founded departure from my proposed fix: the implementer's SpecialtyDirectoryLinkAbsenceTests (src/test/java/.../vet/SpecialtyDirectoryLinkAbsenceTests.java) matches any mention of 'specialties.html' across templates rather than scoping to href/th:href. I verified this is the right call, not a weakening: fragments/layout.html's nav entries pass their route to the menuItem fragment as a plain argument (e.g. th:replace="~{::menuItem ('/vets.html','vets',...)}"), and the fragment itself carries the only th:href in the file, parameterized as @{__${link}__} -- the literal route string never appears inside an href attribute anywhere a nav link would be added. An href-scoped pattern (my original proposal) would have missed the realistic regression entirely. I reproduced red myself: inserted a menuItem('/specialties.html',...) line into layout.html, ran ./gradlew test --tests SpecialtyDirectoryLinkAbsenceTests, saw it fail with a clear message naming the offending line, then reverted (git diff --stat confirms layout.html clean) and reran green. Package placement (vet, not system beside I18nPropertiesSyncTest) is a defensible feature-ownership call; the brief states no test-package-placement rule to violate.
- Finding 2 (round 1) resolved as proposed: SpecialtyControllerTests.java:191-201 theSpecialtyDirectoryShouldRenderWhenTheClinicKnowsNoSpecialty now asserts containsString("id=\"specialties\"") and not(containsString("\<td")). I reproduced the implementer's claim myself: temporarily deleted the two empty-stub given(...) lines (so the mocks fall back to the @BeforeEach non-empty fixture), reran the single test, and it failed at line 197 as expected -- the assertion genuinely bites. Reverted cleanly (git diff --stat confirms no stray changes).
- Full vet-package test run (./gradlew test --tests org.springframework.samples.petclinic.vet.*) is green after both reverts; working tree matches the build-pass diff exactly (git status/diff --stat show only the expected new/modified files).
- No new mocking, naming, or structure issues introduced by the fix-delta: SpecialtyDirectoryLinkAbsenceTests uses no mocks (real file I/O per the brief's mocking policy), follows the BDD naming school (theSpecialtyDirectoryShouldBeLinkedFromNoPage), and SpecialtyControllerTests' existing three-tier data naming and @MockitoBean usage are unchanged by the fix.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $2.73 | 12m 4s | 95% |
| `(parent)` | 1 | opus-5 | $2.14 | 54m 31s | 96% |
| `agent-team:system-design-expert` | 1 | opus-5 | $2.04 | 6m 8s | 94% |
| `agent-team:change-grader` | 1 | opus-5 | $1.06 | 3m 22s | 92% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.06 | 2m 54s | 92% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.65 | 2m 14s | 91% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.64 | 3m 41s | 91% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.61 | 2m 34s | 91% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.54 | 1m 18s | 86% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $2.14 | 54m 31s | 96% |
| `agent-team:system-design-expert` | opus-5 | $2.04 | 6m 8s | 94% |
| `agent-team:feature-implementer` | opus-5 | $1.68 | 7m 43s | 95% |
| `agent-team:change-grader` | opus-5 | $1.06 | 3m 22s | 92% |
| `agent-team:product-requirements-expert` | opus-5 | $1.06 | 2m 54s | 92% |
| `agent-team:feature-implementer` | opus-5 | $1.05 | 4m 20s | 94% |
| `agent-team:security-reviewer` | opus-5 | $0.54 | 1m 18s | 86% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.49 | 1m 42s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.36 | 1m 33s | 89% |
| `agent-team:test-reviewer` | sonnet-5 | $0.35 | 2m 5s | 93% |
| `agent-team:test-reviewer` | sonnet-5 | $0.29 | 1m 35s | 88% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.26 | 1m 0s | 93% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.16 | 31s | 87% |

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

- plugin `agent-team-spring-boot` at `v0.3.8` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
