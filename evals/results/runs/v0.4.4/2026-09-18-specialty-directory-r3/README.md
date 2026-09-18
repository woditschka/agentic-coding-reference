# specialty-directory r3 — v0.4.4

Specialty directory page (feature) · started 2026-09-18T04:01:47+00:00 · exec `claude-dev` · status **complete**

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
| 5 (±0) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.55. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The grouping and ordering logic is in  SpecialtyDirectory , a pure, immutable record with named  SPECIALTY_ORDER / HOLDER_ORDER  comparators. It is unit-tested without the framework, and  SpecialtyController  only delegates. That fits the web-controller pattern and moves the test pyramid in the right direction. The tests use BDD names, phase spacing, factories, and hand-written  InMemorySpecialties / InMemoryVets  doubles, and they compare whole objects. Problems:  SpecialtyControllerTests  repeats the factories  aVet ,  entry  and  directoryOf  from  SpecialtyDirectoryTests . It uses a fixed  ANY_VET_ID = 10 , and the  ANY_FORM  name misstates its role. It also mixes a filesystem template scan into a web test, and  ...OfferNoWayToChange...  has two act/assert pairs. The docs are fully current: the PRD adds REQ-VET-003 and three open questions, and the contracts table and package tree are updated.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The new  SpecialtyDirectory  is an immutable record that groups vets purely, with defensive  List.copyOf . It lives in  vet/  next to a read-only  SpecialtyRepository , and  showSpecialtyDirectory  only delegates, so no business rule sits in the controller. The tests use  the{Subject}Should{Outcome}  names,  aSpecialty / aVet  factories, hand-written  InMemorySpecialties / InMemoryVets  doubles, named constants and whole-object  isEqualTo(directoryOf(...)) . They lose a point on three counts:  theSpecialtyDirectoryShouldOfferNoWayToChange...  sends two requests and asserts two concerns; the template-walking navigation test sits in the controller test class; every vet shares a fixed  ANY_VET_ID = 10 . For maintainability, the copied  \<!-- PROJECT: ... -->  template comment in the new Scale and Load section is noise. For docs, the PRD requirement, the open questions, the package tree and the contract rows (including  Vet  and  VetRepository  Implements) all move with the change.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The grouping and ordering rules sit in  SpecialtyDirectory.of , an immutable record with defensive  List.copyOf  and no I/O, so the unit can be tested without the framework.  SpecialtyController  only delegates, and  SpecialtyRepository  follows the read-only repository pattern. Tests use BDD names, hand-written in-memory repositories instead of mocks, named constants and factories, and derived expectations such as  HELEN + " " + LEARY . Weaknesses:  aVet ,  entry  and  directoryOf  are duplicated across both test classes. The template-scanning filesystem test sits inside  SpecialtyControllerTests .  theSpecialtyDirectoryShouldOfferNoWay...  has two act steps. The new Scale and Load section keeps a leftover  \<!-- PROJECT: -->  template comment. The PRD, package tree and contracts table are all updated consistently.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $7.80 | 17m | 4 | 92% | 9 file(s) +670/−6 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.64 | 45s | 82% |

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
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **minor** · (design) · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 8m***
  - ▲ **build ✗ build failed** · retry 1
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 32s***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 2m***
- ✔ **review test** · **approved** · ***◷ 2m***
- ◆ **grade SKIM** · add read-only specialty directory page
  - blast_radius — **skim** — Purely additive and contained to the vet package: three new package-private classes, one new template, one new GET route, and no edits to existing production code; the security-surface flag is a parameter-free read of data /vets already exposes in full.
  - semantic_surprise — **skim** — Read SpecialtyDirectory.of end to end: grouping keys on specialty id (safe across the fresh specialty read and the cached vet instances), specialties sort by name then id, holders by last name, first name, then id, full name is first plus last, and unheld specialties fall back to an empty list; the template uses escaped th:text only, and the unmatched 'specialties' menu key simply highlights no nav item, which is the stated intent.
  - test_adequacy — **skim** — Tests assert whole-value equality on real Specialty and Vet objects and cover every edge case that could break: several specialties per vet, unheld specialty, same id on a different instance, and tie-breaking order; controller tests use hand-written doubles plus escaping, 405-on-POST, and no-link checks, and an end-to-end test checks seeded order and that vets without a specialty are left out.
  - reviewer_hedging — **skim** — All four dispatched reviewers approved with no findings or recommendations and cited evidence that checks out (layout.html:31 preprocessing, Vet.java:60-63 sorted copy); the only caveat, that no NVD scan ran, is a standing project gap and not a reservation about this change.
  - scope_deviation — **skim** — The diff matches the intake and PRD surface exactly (GET /specialties.html, read-only, no link from any page), with zero consultations and zero design revisions; the one build-failure record is a truncation progress checkpoint, not a failed attempt, and the new Scale and Load doc row belongs to the design block.
  - why — A contained, additive read-only page whose grouping and ordering logic reads correctly and is covered by real-object unit, MockMvc, and end-to-end tests, with clean approvals and no scope drift. A glance at SpecialtyDirectory.java and the template confirms it.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- No request input reaches the new endpoint: SpecialtyController.java:37-38  @GetMapping("/specialties.html")  /  String showSpecialtyDirectory(Model model)  binds no parameter, path variable, or model attribute. A grep of the diff's added lines for  @RequestParam @ModelAttribute @PathVariable  returned no match, so mass assignment, cross-request state, and injection rows of docs/security-principles.md do not apply.
- Output escaping holds: specialtyList.html:18  th:text="${entry.specialtyName}"  and :21  th:text="${holderName}"  use escaped th:text. A grep of the added lines for  utext  and  __${  (preprocessing) returned no match. The menu key 'specialties' passed at specialtyList.html:3 is a template literal, so the layout's existing  @{__${link}__}  preprocessing (layout.html:31) sees no request-derived text.
- Data access is read-only and parameter-free: SpecialtyRepository.java:34-35  @Transactional(readOnly = true)  /  Collection\<Specialty> findAll()  is a derived Spring Data query with no concatenated query text and no write method.
- Shared cached state is not mutated: SpecialtyDirectory.of reads the cached VetRepository.findAll() collection and Vet.getSpecialties() (Vet.java:60-63 returns a freshly collected sorted list). Grouping happens in a request-local HashMap, and records copy via List.copyOf. The singleton controller holds only final repository references.
- Surface widening is stated and bounded: one new read-only GET page with no pagination, sized in system-design.md § Scale and Load as bounded, over data the /vets route already exposes in full. It exposes no new data class and does not change management exposure.
- No secrets or dangerous sinks added: a case-insensitive grep of the diff's added lines for password secret token apikey credential Runtime ProcessBuilder JsonTypeInfo /tmp/ System.out returned no match.
- Supply chain: build.gradle is unchanged in this diff ( git diff --stat build.gradle  was empty), so no dependency was added. No NVD match ran: the project configures no OWASP dependency-check plugin (grep of build.gradle for dependencycheck owasp returned no match), and the reviewer has no network access. The  ./gradlew dependencies  runtimeClasspath output resolved Spring Boot 4.1.1, Jackson databind (tools.jackson.core) 3.1.5, and Thymeleaf 3.1.5.RELEASE. ./gradlew test was not re-run in this review; the build-pass gate at handoff line 9 records it.

**doc-reviewer**

- docs/prd.md  ### Specialty directory  section (lines 133-144) uses only behavioral language, no code/class/method names, has the  \<a id="req-vet-003">\</a>  anchor, and links  **Design:** [system-design.md#contracts](system-design.md#contracts)  which resolves to the  ## Contracts  heading at docs/system-design.md:72.
- Every  REQ-VET-003  reference added to docs/system-design.md (Contracts rows for  Vet ,  Specialty ,  SpecialtyRepository ,  SpecialtyDirectory ,  VetRepository ,  SpecialtyController ) has a matching requirement id in docs/prd.md ( req-vet-003  anchor at prd.md:135) — no orphaned requirement id introduced.
- The 'no page links to it' claim in both prd.md:137/143 and system-design.md's invariants paragraph is verified:  grep -rl 'specialties.html' src/main/resources/templates  returns no matches, and src/main/resources/templates/vets/specialtyList.html itself contains no such reference.
- The message keys reused by the new template ('specialties', 'name', 'vets') already exist in src/main/resources/messages/messages.properties (lines 21-23), matching the design doc's claim that no new key is needed.
- SpecialtyController.java matches the system-design.md Contracts row and invariants paragraph exactly: GET /specialties.html, constructor-injects SpecialtyRepository and VetRepository, binds no request parameter, adds model attribute and returns view name only.
- New PRD prose (docs/prd.md:137-144) stays within the writing standards: short sentences, answer-first, no relative references, no version numbers.
- The new '## Scale and Load' section (docs/system-design.md:123-131) omits an opening Level-1 prose paragraph before its comment+table, but this mirrors the pre-existing '## Constants' section's same structure (docs/system-design.md:61-68), which is the document's established house style for tabular reference sections rather than a deviation introduced by this slice.

**code-quality-reviewer**

- SpecialtyDirectory (src/main/java/org/springframework/samples/petclinic/vet/SpecialtyDirectory.java:35-85) is a pure value object built through one static creator SpecialtyDirectory.of(...); the compact constructors defensively copy with List.copyOf, and grouping keys on Specialty::getId (not instance) per the design-block's stated risk, verified by SpecialtyDirectoryTests.theSpecialtyDirectoryShouldGroupHoldersBySpecialtyIdentityNotInstance.
- SpecialtyController (SpecialtyController.java:26-44) binds nothing, delegates to the two repositories, and contains no business rule — grouping, ordering, and full-name composition all live in SpecialtyDirectory, matching architecture-principles' Web controller row cited in the design-block.
- SpecialtyRepository (SpecialtyRepository.java:28-37) mirrors PetTypeRepository's shape (extends Repository\<Specialty,Integer>, @Transactional(readOnly = true) findAll), read-only with no save/delete method, satisfying NG-2.
- specialtyList.html uses th:text exclusively for specialty names and holder names (verified: no th:utext in the file via grep) and passes menu key 'specialties', which matches none of layout.html's menuItem keys (home, owners, vets, error at lines 41/46/51/57), so no navigation entry highlights and none was added, matching REQ-SYS-001 and the no-link acceptance bullet.
- No template under src/main/resources/templates references /specialties.html other than specialtyList.html itself (checked via SpecialtyControllerTests.theSpecialtyDirectoryShouldNotBeLinkedFromNavigation, which walks the same directory) — the no-link criterion holds.
- The Scale and Load row added to docs/system-design.md is delivered as specified: one HashMap-keyed pass (SpecialtyDirectory.holdersBySpecialtyId) then standard-library Comparator sorts, no hand-written data structure, no pagination.
- ./gradlew checkFormat passes with no formatting violations across the changed files.

**test-reviewer**

- SpecialtyDirectoryTests (src/test/java/org/springframework/samples/petclinic/vet/SpecialtyDirectoryTests.java) unit-tests the grouping/ordering rule with real Specialty and Vet instances, no doubles, correctly placed below the boundary per the design-block's assignment to the SpecialtyDirectory value object; it covers several-specialties-per-vet (line 82), unheld specialty (line 93), same-id distinct-instance grouping (line 104), and stable order with tie-breaking (line 114) — matching the design-block's named risks.
- SpecialtyControllerTests (src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java) uses @WebMvcTest (the sanctioned MockMvc transport double) with hand-written InMemorySpecialties/InMemoryVets doubles registered via @TestConfiguration (lines 200-233) instead of @MockitoBean, matching testing-principles.md's Mocking Policy ('hand-write mocks... a mock framework is a last resort') and the design-block's integration_points note; grep for MockitoBean/Mockito/mock( across the three new/changed test files returned no matches.
- theSpecialtyDirectoryShouldRenderStoredNamesAsText (SpecialtyControllerTests.java:122) asserts stored-name markup is HTML-escaped in the rendered page (ESCAPED_MARKUP_IN_STORED_NAME present, MARKUP_IN_STORED_NAME absent), directly covering the design-block's cross-site-scripting risk.
- theSpecialtyDirectoryShouldOfferNoWayToChangeVeterinariansOrSpecialties (SpecialtyControllerTests.java:132) exercises the real MVC dispatch for a POST to the route and asserts 405, verifying edge case 5 / NG-2 (read-only) behaviorally rather than by inspection.
- PetClinicIntegrationTests.theSpecialtyDirectoryShouldListTheSeededSpecialtiesWithTheirHolders (src/test/java/org/springframework/samples/petclinic/PetClinicIntegrationTests.java:87) is a real end-to-end test over the actual H2 seed and vet cache (RestTemplate against a running server, no doubles), asserting ordering via AssertJ containsSubsequence and the vets-without-specialty omission via doesNotContain — real I/O per the Mocking Policy's 'Real I/O for integration' rule.
- coverage-map --feature REQ-VET-003 shows 7 of 7 declared test names present and all 4 Done-when bullets covered; conventions-map shows no unnamed/mystery-literal constructions outside the sanctioned aSpecialty/aVet/entry/directoryOf factory wrappers.
- ./gradlew test --tests "*Specialty*" --tests "*PetClinicIntegrationTests*" --info passed (BUILD SUCCESSFUL), confirming all new tests are green.
- Edge case 4 (i18n) needs no new test: grep confirms the 'specialties'/'vets'/'name' message keys used by specialtyList.html already exist in messages.properties and all locale bundles (messages_de/pt/ko/fa/ja/es/ru/hi/tr.properties), so the existing I18nPropertiesSyncTest continues to cover it without a widened production surface.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $2.92 | 8m 56s | 92% |
| `agent-team:system-design-expert` | 1 | opus-5 | $1.23 | 2m 15s | 90% |
| `(parent)` | 1 | opus-5 | $1.17 | 17m 16s | 96% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $0.83 | 1m 30s | 90% |
| `agent-team:change-grader` | 1 | opus-5 | $0.64 | 45s | 82% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.55 | 40s | 87% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.42 | 2m 17s | 93% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.38 | 2m 27s | 91% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.29 | 1m 47s | 93% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $1.54 | 4m 56s | 93% |
| `agent-team:feature-implementer` | opus-5 | $1.38 | 4m 0s | 90% |
| `agent-team:system-design-expert` | opus-5 | $1.23 | 2m 15s | 90% |
| `(parent)` | opus-5 | $1.17 | 17m 16s | 96% |
| `agent-team:product-requirements-expert` | opus-5 | $0.83 | 1m 30s | 90% |
| `agent-team:change-grader` | opus-5 | $0.64 | 45s | 82% |
| `agent-team:security-reviewer` | opus-5 | $0.55 | 40s | 87% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.42 | 2m 17s | 93% |
| `agent-team:test-reviewer` | sonnet-5 | $0.38 | 2m 27s | 91% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.29 | 1m 47s | 93% |

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

- plugin `agent-team-spring-boot` at `v0.4.4` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `0aff9592719d` (branch `agent-team`)
- task fingerprint `dfad163fa162236e` · `2.1.274 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
