# specialty-directory r4 — v0.4.7

Specialty directory page (feature) · started 2026-09-30T17:53:08+00:00 · exec `claude-dev` · status **complete**

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
| reading depth (pipeline grade) | skim |

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
| 4 (±1) | 4 (±1) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.73. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Placement is idiomatic: grouping lives in an immutable  SpecialtyDirectory  record (defensive  List.copyOf , names copied so no entity escapes), the read is a bare- Repository   SpecialtyRepository , and  VetController.showSpecialtyDirectory  only binds, delegates, and selects the view, reusing the cached  vetRepository.findAll() . Unit tests are exemplary — behavior names, four phases, factories ( aVetHolding ,  specialty ), whole-object  isEqualTo(directoryOf(...)) , empty/duplicate/tie cases, and a hand-written lambda repository bean instead of a framework stub. Deductions:  theSpecialtyDirectoryShouldCarryTheStandardNavigation  asserts the layout's  id="main-navbar"  markup, re-testing another unit on an implementation detail; ordering is stated twice ( ORDER BY specialty.name  plus  SPECIALTY_ORDER ), and  Entry.specialty  is a  String  name. Docs are current: PRD REQ-VET-003, contracts rows, package line, open questions.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Grouping and ordering live in the immutable  SpecialtyDirectory  record, leaving  VetController.showSpecialtyDirectory  to bind, delegate and select a view — no new controller rule;  SpecialtyRepository  extends bare  Repository  for a read-only surface. Design nit: a third, unrelated HTTP surface is bolted onto  VetController  rather than a  SpecialtyController , and name ordering is stated twice (the  ORDER BY specialty.name  query plus  SPECIALTY_ORDER ).  SpecialtyDirectoryTests  is exemplary: behavior names, factories ( aVetHolding ,  specialty ), named constants, whole-record equality, no mocks;  VetControllerTests  uses a hand-written lambda double. Weaker:  theSpecialtyDirectoryShouldCarryTheStandardNavigation  asserts  id="main-navbar" , an unrequested implementation detail owned by the layout.  Entry.specialty  holds a String name, slightly misleading. PRD REQ-VET-003, contracts, package structure and open questions all move.

**Sample 3** — design-fit 4 · test-quality 5 · maintainability 4 · doc-fit 5

> Grouping and ordering live in an immutable record ( SpecialtyDirectory.of ,  holdersBySpecialtyId ), leaving  showSpecialtyDirectory  as pure binding/delegation, and  SpecialtyRepository  extends bare  Repository  so no write leaks — clean layering. Minor debt: a second HTTP surface is bolted onto  VetController  rather than its own controller, and the template passes  'specialties'  to the layout's active-menu slot though no nav entry was requested. Tests are exemplary:  theSpecialtyDirectoryShould...  names, blank-line phases, test-owned factories ( specialty ,  aVetHolding ,  entry ), whole-object  isEqualTo  comparisons, a hand-written  SpecialtyRepository  lambda instead of a mock framework; only  STANDARD_NAVIGATION = "id=\"main-navbar\""  asserts markup detail. New keys  #{specialties} ,  #{name} ,  #{vets}  arrive with no bundle entries, risking the REQ-LANG-002 gate. PRD and system-design (contracts, package line, scale table, open questions) are fully current.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $5.03 | 16m | 4 | 91% | 9 file(s) +479/−13 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.55 | 1m 33s | 87% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

1 review round · 1 build-pass · **1 build-failure** · grade **SKIM**

| reviewer | R1 |
| --- | --- |
| **code-quality** | **✔** |
| **test** | **✔** |
| **security** | **✔** |
| **doc** | **✔** |

- ◇ **intake** Feature request: the vet list answers "which specialties does this vet hold", but staff also ask the inverse — "which vets hold this specialty". Two product decisions come with it, made here as the product owner: - A read-only specialty view of the existing directory is in scope; managing   veterinarians or specialties stays out of scope as before (non-goal NG-2   is unchanged). - The page is reachable by its URL alone: no navigation entry and no link   from another page is part of this request. A visible entry point may come   as a follow-up request. Add a specialty directory page: - GET /specialties.html lists every specialty the clinic knows by its stored   name, each with the veterinarians holding it. - Each veterinarian is shown by full name: first name, then last name (for   example "Helen Leary"). - A veterinarian holding no specialty appears under no specialty; the page   lists specialties, not the full vet roster. - All specialties render on one page — no pagination. Cover the new behavior with tests. These are all the product decisions; no further product answer will come during the work. Where a choice still seems open, take the narrowest reading consistent with this request and record the open question rather than waiting. · (2 decisions) · (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **minor** · (design) · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 7m***
  - ▲ **build ✗ build failed** · retry 1
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 20s***
  - ▹ rec: SpecialtyDirectory.Entry component 'specialty' holds a String name while Specialty is also an entity type; 'specialtyName' would read unambiguously (the template reference entry.specialty would change with it). Polish only.
  - ▹ rec: SpecialtyRepository.findSpecialties orders by name in the query and SpecialtyDirectory.of sorts again with an id tie-break; the repository javadoc '@return all specialties in name order' restates the query. One owner of the order (the directory sort, which the id tie-break needs) would remove the question of which order is authoritative.
- ✔ **review doc** · **approved** · ***◷ 25s***
  - ▹ rec: Not verified as required: 'specialty directory' is used in docs/prd.md and docs/system-design.md but has no entry in docs/ubiquitous-language.md (`grep -n -i -F 'directory' docs/ubiquitous-language.md` returned no match). The existing 'veterinarian directory' term is equally undefined there, so this follows precedent; a glossary entry could come with a later doc-sync.
- ✔ **review security** · **approved** · ***◷ 31s***
- ✔ **review test** · **approved** · ***◷ 39s***
  - ▹ rec: Non-blocking: SpecialtyDirectory.HOLDER_ORDER ends with thenComparing(Vet::getId) but no test has two holders with identical first and last names. Removing that comparator would not fail any test in SpecialtyDirectoryTests (checked by reading all six tests; only the specialty-id tie-break is covered). Add a case if the holder tie-break is meant to be a contract.
  - ▹ rec: Non-blocking: no test builds a directory from an empty specialty list (the brief's empty-input boundary); SpecialtyDirectory.of(List.of(), ...) is untested. Low risk given the stream shape, one test would close it.
  - ▹ rec: Non-blocking: VetControllerTests.theSpecialtyDirectoryShouldListEverySpecialtyByItsStoredNameOnOnePage asserts dentistry before radiology while its stub returns radiology first, so it re-asserts the ordering rule already owned by SpecialtyDirectoryTests.theSpecialtyDirectoryShouldPresentSpecialtiesAndHoldersInAStableOrder. The client suite could keep only containment (as the brief's 'Stop Re-Testing Other Units' suggests). The 'on one page' half of the name is not exercised by two specialties.
- ◆ **grade SKIM** · add read-only specialty directory page
  - blast_radius — **skim** — Nine files, all in the vet package plus its template and the two briefs. No sensitive paths are touched. The only change to existing code is VetController gaining a SpecialtyRepository constructor argument and one GET /specialties.html handler, and nothing else constructs VetController. The flagged security surface is a parameterless static JPQL query and a route that binds no input and shows only names that /vets.html already shows.
  - semantic_surprise — **skim** — The hunks do what the description says. Holders are grouped by specialty id in one pass over the cached roster. Specialties come from a fresh name-ordered query, and both sorts end in an id tie-break. The template escapes every value with th:text and renders the existing none key under an unheld specialty. No existing behavior changes: the paged vet list, the JSON route, the cache and the layout nav are untouched. The one residual, documented in the design, is that holders come from the vet cache while specialties are read fresh. A null name in out-of-band data would make the comparators throw, and Vet.getSpecialties already has that exposure.
  - test_adequacy — **skim** — SpecialtyDirectoryTests compare whole expected directories against real entities, and six tests each fail if their rule is removed: multi-holding, omission, held-by-none, match by id rather than instance, name ordering, and the same-name specialty tie-break. The MockMvc tests check rendering and the none text, which the layout does not otherwise contain. The integration test drives the seeded data end to end, including the absence of James Carter and Sharon Jenkins. The one surviving mutant is the holder id tie-break, which only matters for two vets with identical full names.
  - reviewer_hedging — **skim** — All four dispatched reviewers approved in round 1 with no findings. Their recommendations are polish: renaming Entry.specialty, the ordering being done in both the query and the directory, a glossary entry, and two small test gaps. Citations I checked resolve (messages.properties 21-24, SpecialtyDirectoryTests 136/147/156/160, VetControllerTests 107). The unconfigured OWASP scan and the format task the reviewer could not run are standing gaps that build-pass covers.
  - scope_deviation — **skim** — The diff matches the intake: a read-only GET /specialties.html, one unpaginated page, first-then-last names, vets without specialties omitted, and no nav link (layout.html is unchanged). The order was left open by the owner and was fixed by the design-block. It is recorded as an open question. There were no design revisions and no consultations. The single build retry was a planned mid-cycle checkpoint, not a failure the slice fought.
  - why — A contained, additive, read-only page in the vet package that behaves exactly as described. It changes no existing behavior, and its tests would catch removal of every rule except the identical-name holder tie-break. A glance at VetController's new handler and specialtyList.html confirms it.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- Design placement: ordering and grouping live in the SpecialtyDirectory value object, matching its docs/system-design.md Contracts row; VetController only assembles and renders (VetController.java showSpecialtyDirectory)
- Scope: the diff adds one GET /specialties.html route and no nav link, matching the PRD line 'It is reached by its address alone, and no page links to it'; the four code comments from conventions-map (SpecialtyDirectory.java 25-31, 45-50, 69-71, 84-86; SpecialtyRepository.java 24-27, 30-33) each explain WHY or one-sentence purpose
- Vocabulary: Specialty, Veterinarian ('vet' short form), holder, directory match docs/ubiquitous-language.md; none of the Avoid terms (Skill, Qualification, Discipline) appear
- Workload fit: the Scale and Load rows in docs/system-design.md give 'simplest readable form' for bounded rows; the code is one HashMap grouping pass plus sorts, with no N+1 (single findSpecialties query, vet roster from the cache)
- Construction: SpecialtyDirectory, Entry and Holder are records with defensive List.copyOf in compact constructors and private static 'of' creators; no builders or withers
- Template: no hard-coded text; the message keys vets, name, specialties and none exist in messages.properties (lines 21-24, verified with grep)
- Not verified: ./gradlew checkJavaFormat fails because the task does not exist in this project (only checkFormat is wired), and checkFormat is outside my permitted commands; the build-pass records the format gate as run

**doc-reviewer**

- PRD boundary: the REQ-VET-003 paragraph in docs/prd.md states behavior only, with no type names, code blocks or rationale prose; the anchor  \<a id="req-vet-003">\</a>  is present and the Design link to system-design.md#contracts is kept
- Every Contracts row the slice touched carries REQ-VET-003 in docs/system-design.md (Vet, Specialty, SpecialtyRepository, SpecialtyDirectory, VetRepository, VetController, CacheConfiguration); the SpecialtyDirectory row's 'last-then-first-name order, ties by stored identifier' matches HOLDER_ORDER in SpecialtyDirectory.java (Comparator.comparing(Vet::getLastName).thenComparing(Vet::getFirstName).thenComparing(Vet::getId))
- Scale and Load seed figures match the seed data:  grep -n -F 'INSERT INTO specialties' src/main/resources/db/h2/data.sql  returns 3 rows (lines 8-10) and  grep -c -i -F 'INSERT INTO vets'  returns 6
- Package tree line for vet/ now names specialty directory, matching the two new files under src/main/java/.../vet/
- The system-design.md additions carry no field tables, constant literals or imperative lines lacking an ADR link; the new Contracts text survives the rename self-test
- Template messages keys specialties, vets, name, none exist in src/main/resources/messages/messages.properties (lines 21-24), consistent with the design's 'no new key' claim

**security-reviewer**

- No request input reaches the new route: VetController.showSpecialtyDirectory(Model model) binds no @RequestParam, @PathVariable, @ModelAttribute or @RequestBody, so it adds no injection, mass-assignment or path-resolution surface. A grep -E 'Runtime ProcessBuilder JsonTypeInfo Files\. @ModelAttribute @RequestBody createQuery nativeQuery' over src/main/java/.../vet/ matched nothing
- The data-access query is static and parameterless: SpecialtyRepository.java carries @Query("SELECT specialty FROM Specialty specialty ORDER BY specialty.name") with no concatenation. The repository extends the bare Repository and is @Transactional(readOnly = true), so it exposes no write method (least privilege)
- XSS control holds: every DB-derived value in templates/vets/specialtyList.html is rendered with escaping th:text (${entry.specialty}, ${holder.firstName + ' ' + holder.lastName}). A grep -E 'utext __\$\{' on that template matched nothing, which matches the escaping pattern of the neighbouring vet list
- Surface widening is stated. The new GET /specialties.html is read-only, unauthenticated like every route in the recorded baseline (system-design.md Security Context), and exposes only specialty names and vet first/last names, which the existing /vets and /vets.html routes already serve. It changes no management or actuator exposure
- SpecialtyDirectory copies names into immutable records (List.copyOf), so no mutable JPA entity reaches the view. The controller holds only final repository fields, with no shared mutable state in the singleton
- The unpaginated whole-table read is sized in the new system-design.md Scale and Load rows as bounded, out-of-band-only data (NG-2). No request can grow it, so it adds no request-driven unbounded allocation
- Null names are not attacker-reachable. db/h2/schema.sql declares specialties.name VARCHAR(80) and vets first_name/last_name VARCHAR(30) as nullable, so a null would make the comparators throw. But no route writes specialties or vets (NG-2), so there is no attacker path. This is noted for robustness only and is not a security finding
- No secrets were added: the diff adds no token, password, secret, key or credential-like literal, and git diff shows no change to build.gradle or pom.xml, so there is no new dependency
- Supply chain: OWASP dependencyCheckAnalyze is not configured, so no NVD match ran in this review. The resolved runtimeClasspath from ./gradlew dependencies shows spring-boot-thymeleaf 4.1.1, thymeleaf 3.1.5.RELEASE and tools.jackson.core:jackson-databind 3.1.5, all unchanged by this slice

**test-reviewer**

- Placement follows docs/system-design.md: the ordering, holder-matching and empty-holder rules live in SpecialtyDirectory and are unit-tested in SpecialtyDirectoryTests (SpecialtyDirectory.of called directly, no framework). The binding/view/message rendering, which the design assigns to the boundary, is tested through MockMvc in VetControllerTests.
- grading.py coverage-map --feature REQ-VET-003 reports 6 of 6 declared tests present; all 4 Done-when bullets and edge cases 3, 4, 5 map to a named test (bullet 3 and 4 in SpecialtyDirectoryTests, bullets 1 and 2 and edge case 3 in VetControllerTests, plus the seeded end-to-end path in PetClinicIntegrationTests).
- Mocking stays within the brief: the new SpecialtyRepository double is a hand-written lambda in a @TestConfiguration (VetControllerTests StoredSpecialties), not a Mockito stub; the existing @MockitoBean VetRepository is pre-existing. Unit tests use real Specialty/Vet entities and compare one whole expected SpecialtyDirectory via isEqualTo.
- Naming follows the the{Subject}Should{Outcome} school; no phase comments; tests are straight-line; construction of Specialty/Vet sits behind specialty(...)/vet(...)/aVetHolding(...) factories and Tier 2 values use ANY_ prefixes. conventions-map rows: the raw new Specialty()/new Vet()/new Entry lines at SpecialtyDirectoryTests:136,147,156,160 and VetControllerTests:107 are all inside those factory helpers.
- The same-name specialty tie-break (theSpecialtyDirectoryShouldOrderSameNamedSpecialtiesByStoredIdentifier) and the identifier-not-equality holder match (...MatchHoldersToSpecialtiesByStoredIdentifier) each have a dedicated test that fails if the production rule is removed.
- ./gradlew test: BUILD SUCCESSFUL (test and jacocoTestReport tasks reported UP-TO-DATE from the build-pass run, no failures or skips shown).

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 1 | opus-5-5 | $1.61 | 8m 18s | 95% |
| `agent-team:system-design-expert` | 1 | opus-5-5 | $1.03 | 2m 59s | 91% |
| `agent-team:product-requirements-expert` | 1 | opus-5-5 | $0.72 | 2m 21s | 90% |
| `(parent)` | 1 | opus-5-5 | $0.67 | 17m 8s | 95% |
| `agent-team:change-grader` | 1 | opus-5-5 | $0.55 | 1m 33s | 87% |
| `agent-team:security-reviewer` | 1 | opus-5-5 | $0.35 | 41s | 84% |
| `agent-team:test-reviewer` | 1 | sonnet-5-5 | $0.24 | 45s | 80% |
| `agent-team:doc-reviewer` | 1 | sonnet-5-5 | $0.21 | 31s | 82% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5-5 | $0.20 | 27s | 83% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5-5 | $1.61 | 8m 18s | 95% |
| `agent-team:system-design-expert` | opus-5-5 | $1.03 | 2m 59s | 91% |
| `agent-team:product-requirements-expert` | opus-5-5 | $0.72 | 2m 21s | 90% |
| `(parent)` | opus-5-5 | $0.67 | 17m 8s | 95% |
| `agent-team:change-grader` | opus-5-5 | $0.55 | 1m 33s | 87% |
| `agent-team:security-reviewer` | opus-5-5 | $0.35 | 41s | 84% |
| `agent-team:test-reviewer` | sonnet-5-5 | $0.24 | 45s | 80% |
| `agent-team:doc-reviewer` | sonnet-5-5 | $0.21 | 31s | 82% |
| `agent-team:code-quality-reviewer` | sonnet-5-5 | $0.20 | 27s | 83% |

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

- plugin `agent-team-spring-boot` at `v0.4.7` (tag)
- model requested `claude-opus-5-5`; models used: opus-5-5 · sonnet-5-5
- SUT `woditschka/spring-petclinic` at `0aff9592719d` (branch `agent-team`)
- task fingerprint `dfad163fa162236e` · `2.1.284 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
