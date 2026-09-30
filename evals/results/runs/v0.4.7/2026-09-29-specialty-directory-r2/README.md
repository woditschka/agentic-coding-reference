# specialty-directory r2 — v0.4.7

Specialty directory page (feature) · started 2026-09-29T18:00:12+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±1) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $1.00. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Inversion logic sits in an immutable value record (SpecialtyDirectory.of, defensive List.copyOf) rather than the controller, which only binds nothing, delegates and selects a view — right layer, catalog-conformant naming, correct constructor injection. The @InitBinder/setAllowedFields block in SpecialtyController is speculative dead weight on a page that binds no form, and its own comment admits it guards a hypothetical future form. Tests are behavior-named, factory-built, mock-framework-free (FakeVetRepository, lambda SpecialtyRepository) and cover empty-holder, multi-specialty and omitted-vet boundaries; however createASpecialty/createAVet are copy-pasted between SpecialtyDirectoryTests and SpecialtyControllerTests instead of shared vocabulary, and the stream-built matcher list plus not(containsString("page=")) asserts markup shape. New template keys #{specialties}/#{vets} have no bundle change visible. Docs, vocabulary, contracts, scale and open questions all move.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Inversion logic sits in the immutable  SpecialtyDirectory  record rather than the controller, so  SpecialtyController.showSpecialtyDirectory  only binds, delegates, and selects a view — right layer, catalog-conforming names, no new controller rule. The  @InitBinder  disallow list is speculative dead weight on a page that binds no form; the sibling  VetController  declares none, and the patch's own threat-table edit records that. Tests are a genuine strength: behavior names, factory methods, named constants, hand-written  FakeVetRepository  instead of a mock framework, and real unit tests at the pyramid base. But  createASpecialty / createAVet  are copy-pasted verbatim into both test classes, violating the shared-vocabulary rule, and  not(containsString("page="))  couples the no-pagination assertion to template link syntax. Documentation is thorough and leaves nothing visibly stale.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The inversion lives in an immutable record (SpecialtyDirectory.java:40-54, id-matched with the reason documented), so the rule is unit-testable and SpecialtyController.java:49-53 only delegates and selects a view — the catalog's Web controller row and naming rules, no duplication. Docs move everywhere they go stale: PRD REQ-VET-003 with done-when and edge cases, three recorded open questions, the Specialty directory vocabulary entry, contracts rows for all three new types, the mass-assignment row, a new Scale and Load table. Tests are BDD-named, four-phase, factory-built, and use hand-written fakes over a mock framework. Deductions: createASpecialty/createAVet duplicated verbatim in SpecialtyControllerTests.java:88-100 and SpecialtyDirectoryTests.java:128-140 rather than shared vocabulary; the web tests' arrange phase hides in FakeRepositories; ClinicServiceTests.java:229 shadows the autowired field; the @InitBinder guards a form that does not exist.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $6.75 | 21m | 4 | 91% | 10 file(s) +535/−7 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.50 | 1m 24s | 83% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · grade **SKIM**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | **✔** | · |
| **security** | **✔** | · |
| **doc** | ✎ (1) | **✔** |

- ◇ **intake** Feature request: the vet list answers "which specialties does this vet hold", but staff also ask the inverse — "which vets hold this specialty". Two product decisions come with it, made here as the product owner: - A read-only specialty view of the existing directory is in scope; managing   veterinarians or specialties stays out of scope as before (non-goal NG-2   is unchanged). - The page is reachable by its URL alone: no navigation entry and no link   from another page is part of this request. A visible entry point may come   as a follow-up request. Add a specialty directory page: - GET /specialties.html lists every specialty the clinic knows by its stored   name, each with the veterinarians holding it. - Each veterinarian is shown by full name: first name, then last name (for   example "Helen Leary"). - A veterinarian holding no specialty appears under no specialty; the page   lists specialties, not the full vet roster. - All specialties render on one page — no pagination. Cover the new behavior with tests. These are all the product decisions; no further product answer will come during the work. Where a choice still seems open, take the narrowest reading consistent with this request and record the open question rather than waiting. · (2 decisions) · (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 1m***
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert)
- ◈ **design-block** **minor** · (design) · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 8m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 15s***
  - ▹ rec: SpecialtyController.java:44 declares an @InitBinder disallowing id fields although the page binds no request input; the javadoc justifies it only by a future form. It mirrors every other controller and system-design.md documents it, so it is left as is, but it is speculative and could be dropped until a form exists.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 31s***
  - [autofix] `prd.md:132-133` The change deleted the blank line between the last Done-when bullet (line 132, '- `[REQ-VET-003]` given a veterinarian holding no specialty ...') and '**Edge cases:**' (line 133), shown as a removed blank line in `git diff docs/prd.md`. Without it, Markdown renders '**Edge cases:**' as a lazy continuation of the last list item. The new requirement paragraph also puts the anchor at line 123 (`\<a id="req-vet-003">\</a>`) directly above its text, while REQ-VET-001 in the same section leaves a blank line after its anchor.
    - fix: Restore the blank line before '**Edge cases:**' and add a blank line between the req-vet-003 anchor and its paragraph, matching the req-vet-001 layout.
- ✔ **review security** · **approved** · ***◷ 31s***
- ✔ **review test** · **approved** · ***◷ 51s***
  - ▹ rec: Edge case 1 (stable presentation order) has no ordering assertion for this page. SpecialtyDirectoryTests uses containsExactlyInAnyOrder, and SpecialtyDirectory's javadoc says listings follow the order the specialties were given, but SpecialtyRepository.findAll declares no ORDER BY (SpecialtyRepository.java:36 `List\<Specialty> findAll() throws DataAccessException;`). Whether edge case 1 binds the directory or only the vet list (Vet sorts its own specialties) is not verified in this review. If it binds the directory, an ordering rule and a containsExactly test are missing. Worth asking the product-requirements-expert.
  - ▹ rec: createASpecialty and createAVet are duplicated verbatim in SpecialtyControllerTests.java:101-114 and SpecialtyDirectoryTests.java:121-134. Lifting them into one shared test-data helper would follow the brief's testing-vocabulary section. No shared helper exists yet (grep -F for createAVet outside the new files found none), so this is polish, not a defect.
  - ▹ rec: ClinicServiceTests.theSpecialtyRepositoryShouldReturnEverySeededSpecialty declares a local `Collection\<Specialty> specialties` that shadows the new `specialties` field. This is harmless, but renaming the local to `found` would read cleaner.
- ↻ **fix prd-expert** ← doc · (1 finding)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 42s***
- ◈ **design-block** **minor** · (design) · ***◷ 45s***
- ◆ **implement** (implementer) · ***◷ 46s***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 8s***
- ✔ **review doc** · **approved** · ***◷ 3s***
- ◆ **grade SKIM** · add read-only specialty directory page at /specialties.html
  - blast_radius — **skim** — Additive and contained to the vet package: three new production files, one new template, two new test classes, one appended repository test, and the three briefs. No existing production line changes, nothing under a sensitive path, and the one security-surface path is a new read-only GET that binds no request input and shows names /vets.html already makes public.
  - semantic_surprise — **skim** — The hunks do what the description says. SpecialtyDirectory.of groups holders by Integer id through a HashMap (value equality, not instance identity), lists every specialty from its own repository so an unheld one still appears, and skips vets with no specialty by construction. The template escapes output with th:text, and the layout menu argument 'specialties' matches no nav item, so no entry point appears. The one quiet property is ordering: specialties follow the repository's unordered findAll and holders follow the cached vet list, so display order depends on the database. The PRD records this as an open question rather than a commitment.
  - test_adequacy — **skim** — The tests exercise real outcomes and would fail against plausible broken versions. Fresh Specialty instances per call catch a regression to instance matching. Exact listing equality catches a holder filed under the wrong specialty or a wrong name format. The omit and unheld-specialty cases each have a test. The MockMvc test renders 31 specialties and asserts no page= link, and the seeded-DB test proves findAll returns all three rows. Ordering is not asserted, which matches the PRD's decision not to commit to an order.
  - reviewer_hedging — **skim** — All four round-1 reviewers approved with cited evidence, and the citations I checked resolve (SpecialtyController.java:44 and :49, SpecialtyRepository.java:36, messages.properties:21-23). The round-2 fix delta touched only blank lines in prd.md and was re-approved by the planned roster. The test reviewer left a recommendation asking whether edge case 1's stable order binds this page. Reading the PRD settles it: edge case 1 covers a veterinarian's own specialty list, and the new open question records that REQ-VET-003 commits to no order. The other recommendations are polish.
  - scope_deviation — **skim** — The diff delivers exactly the intake's bullets: GET /specialties.html, recorded names, first-then-last holder names, vets with no specialty omitted, one unpaged page, read-only, and no navigation link. It had zero retries, consultations, or design revisions. The doc edits beyond the new entry are a new Scale and Load row for the page and a threat-model row that now correctly lists which controllers declare the id disallow list. Both describe this slice's surface.
  - why — A contained, additive read-only page whose inversion logic, tests, and docs match the intake. The approvals are well cited, and the only residual question, display order, is recorded in the PRD as an open question. A glance at SpecialtyDirectory.of and the template confirms it.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- checkFormat passes (the agent's named task checkJavaFormat does not exist in this Gradle build, so ./gradlew checkFormat was run instead: BUILD SUCCESSFUL)
- Grouping logic lives in the SpecialtyDirectory value record, not the controller; SpecialtyController.java only composes the two repositories and the model, matching the system-design.md Contracts rows for SpecialtyDirectory and SpecialtyController
- Complexity fits the Scale and Load row: one specialty read, plus the cached vet list, grouped by a HashMap keyed on id (SpecialtyDirectory.java holderNamesBySpecialtyId), linear as the row states
- Names use the vocabulary: 'Specialty directory' is defined in docs/ubiquitous-language.md and the code uses Specialty, Veterinarian holders; no listed avoid-term appears
- Template keys #{specialties}, #{vets} and #{name} resolve in src/main/resources/messages/messages.properties (lines 21-23: vets=Veterinarians, name=Name, specialties=Specialties), so no hard-coded text; conventions-map comment blocks in the three new production files each explain why and none restates code
- Delivers the REQ-VET-003 bullets with no navigation entry, search input or ordering, respecting the PRD's stated boundaries

**doc-reviewer**

- Every REQ-VET-003 mention in docs/system-design.md resolves to the new anchor at docs/prd.md:123.
- Seed counts in the Scale and Load row (3 specialties, 6 veterinarians) match src/main/resources/db/h2/data.sql: three 'INSERT INTO specialties' rows and six 'INSERT INTO vets' rows.
- The claim that no navigation entry leads to the page holds:  grep -n specialties src/main/resources/templates/fragments/layout.html  returned no match. The claim that the data binder disallows id holds: SpecialtyController.java declares an @InitBinder calling setDisallowedFields("id", "*.id").
- The PRD entry stays behavioral: it names no class, method or field. Design detail sits in system-design.md contract rows as source pointers, with no field tables or constants.
- The new term 'Specialty directory' is defined in docs/ubiquitous-language.md with relationships and an Avoid list. Not verified in this review: whether the doctor's section and slot checks pass, since I did not run it.

**security-reviewer**

- Cross-site scripting: every model value in src/main/resources/templates/vets/specialtyDirectory.html renders through escaping th:text ( \<td th:text="${listing.specialtyName}">\</td> ,  th:text="${holderName}" );  grep -rn -F "utext" src/main/resources/templates  returned no match, and the new template uses no  __${...}__  preprocessing (the same grep over templates lists hits only in pre-existing files)
- Request input: SpecialtyController.showSpecialtyDirectory takes only a Model, with no @RequestParam, @PathVariable or @ModelAttribute, so no request-derived value reaches a query, a resource path or a template expression
- Mass assignment: the new controller keeps the project's identifier disallow list ( dataBinder.setDisallowedFields("id", "*.id");  in SpecialtyController.java), matching the brief's rule that the safe default must be present on every new controller
- Injection into data access: SpecialtyRepository declares only a derived  List\<Specialty> findAll()  marked @Transactional(readOnly = true), with no query text built from strings
- Exposed surface: the one new route is a read-only GET /specialties.html exposing specialty names and veterinarian first and last names, both already public on /vets.html. build.gradle is unchanged ( git status --short build.gradle  printed nothing) and  grep -n -i data-rest build.gradle  found no match, so the new public repository is not auto-exported over REST
- Resource bounds: the page is unpaged over the specialties lookup table and the cached VetRepository.findAll(). The neighbouring /vets JSON endpoint already reads the same unpaged collection (VetController.java:70  vets.getVetList().addAll(this.vetRepository.findAll()); ), so the change adds no new reach
- Secrets and errors: the diff adds no credential, logging or exception message; the change set is 3 docs, 3 main Java files, 1 template and 3 test files
- Supply chain: no dependency changed. No NVD match ran because build.gradle configures no dependency-check plugin ( grep -n -i dependencycheck build.gradle  found no match). Resolved versions from  ./gradlew dependencies : Spring Boot 4.1.1, tools.jackson.core:jackson-databind 3.1.5

**test-reviewer**

- ./gradlew test ran green (BUILD SUCCESSFUL, jacocoTestReport ran). coverage-map --feature REQ-VET-003 reports 6 of 6 declared tests present and the 4 Done-when bullets are each covered by a named test.
- Placement follows system-design.md: the inversion rule (SpecialtyDirectory.of) is a unit at SpecialtyDirectoryTests with no framework; the page render, one-page behavior and view name sit at the boundary in SpecialtyControllerTests via MockMvc; SpecialtyRepository.findAll is proven against the seeded DB in ClinicServiceTests.theSpecialtyRepositoryShouldReturnEverySeededSpecialty.
- Mocking policy met: no Mockito in the new tests (grep of the new test files shows only hand-written FakeVetRepository, a lambda SpecialtyRepository, and MockMvc, the one sanctioned mock).
- Edge case 3 (unheld specialty listed) is covered by theSpecialtyDirectoryShouldListASpecialtyNoVetHolds. Edge case 4 (every specialty on one page) is covered by theSpecialtyDirectoryShouldShowEverySpecialtyOnOnePage with 31 specialties and an assertion that no page= link renders.
- The SpecialtyDirectoryTests class javadoc explains why each factory call builds a fresh Specialty instance, and the tests do build fresh instances, so a regression to instance-matching would fail them.
- Naming follows the brief's the{Subject}Should{Outcome} school, AssertJ is used in the unit suite, and the test bodies are straight-line with no phase comments.

**code-quality-reviewer**

- Fix delta since the round-1 tree (python3 scripts/changeset.py --base-tree 1f7d730232b3409d6dba9d0d7e77d9c9d5bd92eb) touches only docs/prd.md: two blank lines added, one after the req-vet-003 anchor and one before '**Edge cases:**'. No Java or template file changed, so the round-1 approval of the code stands.
- ./gradlew checkFormat ran and printed no failure (output was only the JAVA_TOOL_OPTIONS notice); the named task checkJavaFormat does not exist in this build.

**doc-reviewer**

- The round-1 layout finding is resolved: docs/prd.md:123-125 has a blank line after the  \<a id="req-vet-003">\</a>  anchor, and docs/prd.md:134 is blank before  **Edge cases:**  at line 135.
- The route named in the PRD Done-when bullet resolves to the code: SpecialtyController.java:49  @GetMapping("/specialties.html") .
- The new ubiquitous-language term  Specialty directory  (docs/ubiquitous-language.md:54) matches its use in the PRD and system-design contract rows.
- The PRD entry stays behavioral, with no class, method, or field names. The design detail sits in system-design.md as source pointers, with no field tables.
- Not verified in this review: the doctor's section and slot checks, which I did not run.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5-5 | $1.73 | 9m 27s | 93% |
| `agent-team:system-design-expert` | 2 | opus-5-5 | $1.40 | 4m 8s | 89% |
| `agent-team:product-requirements-expert` | 2 | opus-5-5 | $1.21 | 3m 16s | 91% |
| `(parent)` | 1 | opus-5-5 | $1.08 | 22m 25s | 97% |
| `agent-team:change-grader` | 1 | opus-5-5 | $0.50 | 1m 24s | 83% |
| `agent-team:doc-reviewer` | 2 | sonnet-5-5 | $0.37 | 1m 0s | 88% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5-5 | $0.33 | 44s | 85% |
| `agent-team:security-reviewer` | 1 | opus-5-5 | $0.32 | 39s | 85% |
| `agent-team:test-reviewer` | 1 | sonnet-5-5 | $0.23 | 59s | 80% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5-5 | $0.07 | 6s | 49% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5-5 | $1.41 | 8m 28s | 94% |
| `(parent)` | opus-5-5 | $1.08 | 22m 25s | 97% |
| `agent-team:system-design-expert` | opus-5-5 | $0.93 | 3m 5s | 90% |
| `agent-team:product-requirements-expert` | opus-5-5 | $0.72 | 2m 14s | 91% |
| `agent-team:change-grader` | opus-5-5 | $0.50 | 1m 24s | 83% |
| `agent-team:product-requirements-expert` | opus-5-5 | $0.49 | 1m 1s | 91% |
| `agent-team:system-design-expert` | opus-5-5 | $0.47 | 1m 2s | 88% |
| `agent-team:feature-implementer` | opus-5-5 | $0.33 | 59s | 88% |
| `agent-team:security-reviewer` | opus-5-5 | $0.32 | 39s | 85% |
| `agent-team:test-reviewer` | sonnet-5-5 | $0.23 | 59s | 80% |
| `agent-team:doc-reviewer` | sonnet-5-5 | $0.19 | 37s | 87% |
| `agent-team:code-quality-reviewer` | sonnet-5-5 | $0.18 | 25s | 84% |
| `agent-team:doc-reviewer` | sonnet-5-5 | $0.17 | 22s | 88% |
| `agent-team:code-quality-reviewer` | sonnet-5-5 | $0.14 | 19s | 86% |
| `agent-team:pipeline-coordinator` | sonnet-5-5 | $0.07 | 6s | 49% |

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
