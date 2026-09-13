# specialty-directory r1 — v0.4.1

Specialty directory page (feature) · started 2026-09-12T12:10:49+00:00 · exec `claude-dev` · status **complete**

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
| 5 (±1) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.60. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The rules for grouping and ordering live in the immutable  SpecialtyDirectory  record. Its compact constructors do the sorting, and  holds  pairs vets with specialties by id. That leaves  SpecialtyController.showSpecialtyDirectory  doing only read, delegate and render, which matches the Web controller and Value object patterns. The tests use BDD names, blank-line phases, named constants, whole-object  isEqualTo  comparisons and hand-written in-memory repositories with no mock framework. Two things cost points.  createASpecialty  and  createAVet  are duplicated across both test classes instead of shared. The  renderedSpecialty  helpers are tied to  \<td> / \<li>  markup. The nested  Veterinarian  record sitting next to  Vet  is a naming risk. The docs are thorough: REQ-VET-003 with acceptance criteria, an open question, contract rows, an invariants note, the package tree, and a narrowed claim in the threat table.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController only reads the two repositories and renders the page. The immutable SpecialtyDirectory record owns the grouping and both orderings in its compact constructors, and holds() pairs vets to specialties by persisted id, so the rule is unit-testable without booting the framework. Two costs: the nested record  Veterinarian  sits beside the  Vet  entity, giving one concept two names, and the new SpecialtyRepository widens the vet package's surface. The tests use  the...Should...  names, hand-written in-memory repositories, named constants, and whole-object comparisons in SpecialtyDirectoryTests. However, createASpecialty and createAVet are copied into both test classes, the controller tests match raw  \<td> / \<li>  markup, and nothing covers an empty specialty list. The docs are fully current: the PRD adds REQ-VET-003, the Contracts table and package tree are updated, the security row now reads 'owner-feature controller', and the open question about an entry point is recorded.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The layering is clean.  SpecialtyController  only reads and renders. Grouping, id-based pairing and both orderings live in the immutable  SpecialtyDirectory  record, whose compact constructors do the sorting. The new  SpecialtyRepository  follows the repository pattern and stays package-private. The tests use the required BDD names and factory methods. They also use hand-written in-memory repositories ( InMemoryRepositories ) instead of mocks, and  directoryOf / holdersOf  compare whole objects. Weaknesses:  createASpecialty / createAVet  are copied into both test classes instead of shared. The controller tests re-check ordering the unit test already owns, and they depend on exact markup ( "\<td>" + name + "\</td>" ). The  page=2  test proves little with three specialties. Docs are thorough: REQ-VET-003 with done-when criteria and edge cases, an open question about the entry point, new contract rows, the package tree, and the threat-model wording narrowed to 'owner-feature controller'.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $10.14 | 31m | 9 | 91% | 8 file(s) +595/−8 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.76 | 1m 42s | 82% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · grade **SCRUTINIZE**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (1) | **✔** |
| **test** | **✔** | · |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- • intake-decision (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **minor** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 13m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 58s***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `SpecialtyController.java:40-45` showSpecialtyDirectory(Model model) binds no request field at all (no @ModelAttribute, no @RequestParam) — grep -F -e 'InitBinder' src/main/java/org/springframework/samples/petclinic/vet/VetController.java confirms VetController, the other GET-only/Model-only controller in this package, carries no InitBinder either. The disallow-list InitBinder here guards a binding path the current page never has; it is speculative generality for a scenario the slice does not name, and it also diverges from the sibling controller's shape without a stated reason (consistency over novelty, docs/architecture-principles.md Design Principle 2).
    - fix: Remove the setAllowedFields InitBinder method, its WebDataBinder/InitBinder imports, and its comment. If a future change adds a bound parameter, add the disallow list with it then.
- ✔ **review test** · **approved** · ***◷ 2m***
  - ▹ rec: createASpecialty/createAVet are defined identically in both new test files (verified by reading both: SpecialtyDirectoryTests.java:137-150 and SpecialtyControllerTests.java:158-171). testing-principles.md § Testing Vocabulary asks recurring factory patterns be extracted into a shared test utility rather than duplicated per file. Not a defect worth blocking merge; worth extracting on the next touch of either file.
- ↻ **implement** (implementer · routine) ← code-quality · (1 finding) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 21s***
- ◆ **grade SCRUTINIZE** · add the read-only specialty directory page
  - blast_radius — **skim** — Additive and contained: three new package-private types in the vet package, one new template, and two new test files. No existing production file is edited, and the doc edits add rows plus one narrowed threat-model sentence. SpecialtyController is flagged as security surface, but it is a GET that shows specialty and veterinarian names /vets.html already serves.
  - semantic_surprise — **skim** — Read in full, the code does what the PRD says. SpecialtyDirectory pairs specialties by persisted id, not by instance (the cache-versus-query trap the design named). It copies names out of the cached Vet entities and never mutates them (Vet.getSpecialties returns a fresh sorted list). Both orderings live in the record constructors. The template passes a menu key no nav item carries and uses th:text only. Residual edges that do not bite on seeded data: the name sort is case-sensitive, and two null ids would pair.
  - test_adequacy — **skim** — The tests assert real outcomes. Whole-record equality covers multi-holder, non-holder, unheld-specialty, ordering, input non-mutation, and the distinct-instance id pairing. The web test's hand doubles build fresh instances on every call, and its paged findAll throws, which proves the page is unpaged. It also checks the held-by-none marker and that the nav has no entry or active item. A broken grouping or ordering would fail.
  - reviewer_hedging — **scrutinize** — The security reviewer's approval rests on SpecialtyController.java:44 carrying setDisallowedFields("id", "*.id"). The fix round removed that binder, and the citation no longer resolves: the file is 45 lines, and grep finds no InitBinder in the vet package. The round-2 plan re-dispatched only code-quality, so no one re-reviewed the security aspect the approval cited. The test-reviewer's duplicated-factory recommendation is minor polish.
  - scope_deviation — **scrutinize** — The feature surface matches the PRD, but the fix round reversed a recorded design decision. The design block required the id disallow-list binder on this controller, citing docs/security-principles.md:34 ('A new controller or binder that omits the disallow list fails'). A code-quality autofix removed it as speculative generality. No consultation-response or revised design-block records that override of a written security rule.
  - why — The feature code is correct, contained, and genuinely tested. But the fix round removed the id disallow-list binder that security-principles.md:34 and the design block both require, with no recorded override, and the security approval still cites the deleted line. Decide whether the rule or the removal stands before merging.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- XSS: every record-derived value in templates/vets/specialtyDirectory.html goes out through escaped th:text (line 18  th:text="${specialty.specialtyName}" , line 21  th:text="${vet.firstName + ' ' + vet.lastName}" ). A grep of the four changed production files for  utext __\$\{ href \<script  found nothing (exit 1). So there is no unescaped output, no Thymeleaf preprocessing and no inline script or link.
- Mass assignment: the new controller follows the project default from security-principles.md. SpecialtyController.java:44 reads  dataBinder.setDisallowedFields("id", "*.id"); , the same as OwnerController.java:61, VisitController.java:53 and PetController.java:91/97 (grep -F setDisallowedFields). The handler binds no request input: the same grep for  @ModelAttribute @RequestBody @RequestParam @PathVariable  found nothing.
- Injection: data access goes only through a derived Spring Data method (SpecialtyRepository.java:35  Collection\<Specialty> findAll() throws DataAccessException; ,  @Transactional(readOnly = true) ) and the existing cached VetRepository.findAll. The grep for  @Query createQuery nativeQuery Runtime ProcessBuilder exec( Files.  found nothing in the changed files.
- Least privilege and cache integrity: the repository only reads, and the handler is GET-only (SpecialtyController.java:47  @GetMapping("/specialties.html") ). The model carries immutable name-only records (SpecialtyDirectory.java:31/68/84), never the cached Vet entities, so rendering cannot mutate the shared  vets  cache.
- Exposed surface: the new route exposes only specialty names and veterinarian first and last names, which the existing /vets.html and /vets routes already serve to any caller, so it is no weaker than the baseline. The unpaged findAll reads a lookup table that no route writes, plus the cached vet collection /vets already returns whole. The PRD (REQ-VET-003) and system-design Contracts row state what the route exposes. The layout's  __${link}__  preprocessing (fragments/layout.html:31) takes only fixed menu literals, and the new page passes the fixed menu name 'specialties', not request text.
- Threat-model edit: the mass-assignment row now scopes its claim to 'Every owner-feature controller's data binder'. That corrects an overstatement, because VetController.java has no @InitBinder (grep -F setDisallowedFields lists no VetController hit). The new controller carries the disallow list anyway.
- Secrets: the grep of the changed production files for  password secret token  found nothing. There are no log statements or System.out calls, and the change adds no new exception message that could reach the error page.
- Supply chain: build.gradle and pom.xml are unchanged (git status --short shows nothing).  ./gradlew dependencies --configuration runtimeClasspath  resolves spring-boot-starter-webmvc 4.1.1, spring-webmvc 7.0.9, thymeleaf 3.1.5.RELEASE and jackson-databind (tools.jackson.core) 3.1.5. No dependencyCheckAnalyze task is configured (a grep of  ./gradlew tasks --all  found none), so no NVD match ran in this review.

**doc-reviewer**

- REQ-VET-003 anchor \<a id="req-vet-003">\</a> present at first mention in docs/prd.md:125, and the ID correctly takes the next number under the VET prefix after REQ-VET-002's supersession (docs/prd.md:179) — verified via grep -F -e "REQ-VET" -- docs/prd.md docs/system-design.md
- PRD REQ-VET-003 prose (docs/prd.md:126,131-134,139-141) stays behavioral: no class/method names, no framework constructs; matches the boundary-rules.md litmus tests
- docs/system-design.md Contracts rows for SpecialtyRepository, SpecialtyDirectory, SpecialtyController (lines 107-109) are one-sentence purpose plus source pointer, no field/parameter tables, passing the source-rename self-test
- Contract-table Implements symmetry: every row naming REQ-VET-003 in docs/system-design.md (Vet, Specialty, VetRepository, SpecialtyRepository, SpecialtyDirectory, SpecialtyController, CacheConfiguration, lines 102-110) has REQ-VET-003 present in docs/prd.md, and no deprecated requirement (REQ-VET-002) appears in system-design.md — confirmed via grep -F -e "REQ-VET" -- docs/system-design.md
- Design-doc claim 'SpecialtyDirectory alone decides ... its controller only reads and renders' (docs/system-design.md invariants paragraph) matches source: SpecialtyController.java has no loop/sort/filter, only calls SpecialtyDirectory.of(...) and returns the view name
- Design-doc claim 'no navigation entry leads to it' (docs/system-design.md:109, SpecialtyController row) verified: grep -F -e "specialt" -- src/main/resources/templates/fragments/layout.html returns no match, so no nav item carries the 'specialties' menu key the template passes
- Threat Model mass-assignment row narrowed to 'owner-feature controller' (docs/system-design.md:184) stays accurate after this change: grep -F -e "InitBinder" -- src/main/java/org/springframework/samples/petclinic/vet/VetController.java returns no match, so the claim's scope still excludes the vet package correctly
- SpecialtyRepository row ('read-only and uncached', docs/system-design.md:107) matches source: SpecialtyRepository.java declares only @Transactional(readOnly = true) findAll() with no @Cacheable and no ORDER BY
- provenance-exception paragraphs added to both docs/prd.md:12 and docs/system-design.md:10 follow the existing exception-callout convention and correctly scope only REQ-VET-003 statements as designed rather than derived

**code-quality-reviewer**

- SpecialtyDirectory and SpecialtyController match the Value object and Web controller rows in docs/architecture-principles.md's Pattern Catalog (checked against the catalog's Naming table: domain noun with no suffix for the record, Controller suffix prefixed by the domain noun); the controller only reads and delegates, adding no business rule (docs/system-design.md 'Invariants the rows cannot carry' row, confirmed by reading SpecialtyController.java in full)
- Domain-facing names (Specialty, Veterinarian, specialty directory) match docs/ubiquitous-language.md's Veterinarian and Specialty entries; 'Veterinarian' as the nested record name is not on that entry's Avoid list (Doctor, Clinician, Surgeon)
- New template reuses existing message keys (specialties, name, vets, none) already present for vetList.html — no untranslated user-facing text introduced (grep -F -e 'specialties' -e 'none' src/main/resources/templates/vets/vetList.html confirms both keys already render there)
- checkFormat (the project's format-check task; checkJavaFormat is not a registered task in this build) passes clean on the change set

**test-reviewer**

- Pyramid placement matches the design-block assignment: the grouping/ordering rule lives in SpecialtyDirectory (a pure value object, no I/O) and is unit-tested in SpecialtyDirectoryTests; SpecialtyController holds no loop/sort/filter and is exercised only through SpecialtyControllerTests's @WebMvcTest (system-design.md line 82 and 108; SpecialtyController.java:47-52 read directly).
- Mocking policy fully honored: grep -F for 'Mockito', 'mock(' and 'verify(' across both new test files returned zero hits; SpecialtyControllerTests.InMemoryRepositories supplies hand-written real doubles (a lambda for SpecialtyRepository, an anonymous VetRepository) per testing-principles.md § Mocking Policy's 'hand-write mocks' rule, and MockMvc is the one sanctioned boundary mock.
- Whole-object comparison used throughout SpecialtyDirectoryTests (assertThat(directory).isEqualTo(directoryOf(...))) rather than field-by-field picking, matching testing-principles.md § Assertions.
- BDD naming (the{Subject}Should{Outcome}) applied consistently in both new test files, and all 8 test_names declared in the REQ-VET-003 prd-entry are present (python3 scripts/grading.py coverage-map --feature REQ-VET-003: 'Declared tests: 8 of 8 present').
- Three-tier data naming honored: every literal in SpecialtyDirectoryTests/SpecialtyControllerTests is a named constant (DENTISTRY, RADIOLOGY_ID, EARLIER_FIRST_NAME, ANY_FIRST_NAME, etc.); conventions-map's 'literal-bearing lines' for SpecialtyControllerTests are inside the renderedX helper methods themselves, not bare literals in test bodies.
- 100% line coverage on all new production classes per build/reports/jacoco/test/jacocoTestReport.xml (SpecialtyDirectory 11/11, SpecialtyDirectory$Veterinarian 1/1, SpecialtyDirectory$SpecialtyHolders 5/5, Specialty 1/1, SpecialtyController 9/9), exceeding the 80% domain-package target in testing-principles.md § Coverage.
- ./gradlew test and ./gradlew jacocoTestReport both pass clean (BUILD SUCCESSFUL, no failures).

**code-quality-reviewer**

- Round-1 finding resolved cleanly: SpecialtyController.java's setAllowedFields @InitBinder method, its WebDataBinder/InitBinder imports, and its justifying comment are all removed (diff vs. base tree 9a087358: -org.springframework.web.bind.WebDataBinder, -org.springframework.web.bind.annotation.InitBinder, -the InitBinder method and comment block). No replacement binding logic was added, matching the fix's stated scope.
- No other InitBinder/WebDataBinder instance exists in the vet package to sweep: grep -rF -e 'InitBinder' --include=*.java src/main/java/org/springframework/samples/petclinic/vet returned no matches after the removal.
- The file's remaining shape is now record-for-record like VetController.java's GET-only, Model-only handler that the round-1 finding cited as the sibling to match (constructor injection of two repositories, single @GetMapping method, no @InitBinder) — read in full, SpecialtyController.java:16-45.
- ./gradlew checkFormat passes clean (checkFormatMain, checkFormatTest, checkFormat all UP-TO-DATE/BUILD SUCCESSFUL) on the current tree.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $3.70 | 15m 23s | 92% |
| `agent-team:system-design-expert` | 1 | opus-5 | $1.80 | 5m 43s | 91% |
| `(parent)` | 1 | opus-5 | $1.35 | 32m 12s | 95% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.07 | 3m 31s | 87% |
| `agent-team:change-grader` | 1 | opus-5 | $0.76 | 1m 42s | 82% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.68 | 3m 16s | 93% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.64 | 1m 8s | 87% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.46 | 2m 33s | 92% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.44 | 2m 7s | 89% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.26 | 13m 58s | 93% |
| `agent-team:system-design-expert` | opus-5 | $1.80 | 5m 43s | 91% |
| `(parent)` | opus-5 | $1.35 | 32m 12s | 95% |
| `agent-team:product-requirements-expert` | opus-5 | $1.07 | 3m 31s | 87% |
| `agent-team:change-grader` | opus-5 | $0.76 | 1m 42s | 82% |
| `agent-team:security-reviewer` | opus-5 | $0.64 | 1m 8s | 87% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.46 | 2m 21s | 93% |
| `agent-team:test-reviewer` | sonnet-5 | $0.46 | 2m 33s | 92% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.44 | 2m 7s | 89% |
| `agent-team:feature-implementer-routine` | opus-5 | $0.44 | 1m 24s | 91% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.22 | 54s | 93% |

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

- plugin `agent-team-spring-boot` at `v0.4.1` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `0aff9592719d` (branch `agent-team`)
- task fingerprint `dfad163fa162236e` · `2.1.269 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
