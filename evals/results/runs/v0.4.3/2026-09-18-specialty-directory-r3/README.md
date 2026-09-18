# specialty-directory r3 — v0.4.3

Specialty directory page (feature) · started 2026-09-18T03:42:26+00:00 · exec `claude-dev` · status **complete**

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

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.48. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The inversion logic sits in  SpecialtyDirectory , an immutable record that does no I/O and can be unit-tested.  SpecialtyController.showSpecialtyDirectory  only delegates and selects the view, and  SpecialtyRepository  follows the existing repository style. Two points cost design-fit:  Listing  holds mutable  Vet  entities, and the template uses  #{specialties}  with no message-bundle change visible in the patch.  SpecialtyDirectoryTests  uses BDD names, factories, whole-object  containsExactly  comparisons, and covers edge cases.  SpecialtyControllerTests  is weaker: it relies on seeded data and bare  containsString  checks, which never show that Helen Leary appears under radiology. The docs are thorough: the PRD adds REQ-VET-003 and open questions, and system-design updates the package tree, contracts, and invariants.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The inversion logic lives in the immutable value object SpecialtyDirectory (List.copyOf in both record constructors), and it is unit-testable without the framework. SpecialtyController only binds, delegates and returns the view. The one-per-root SpecialtyRepository and the package-private types follow the catalog and naming rules. The SpecialtyDirectoryTests are good: they use BDD names, factories (createASpecialty, createAVet, createAListing), whole-object containsExactly checks, and they cover both edge cases and matching by id. The SpecialtyControllerTests are weaker. Their containsString checks on seeded data barely constrain the page, and they never check that a vet with no specialty is left out. The template joins first and last names with inline concatenation instead of a named accessor. The PRD, the contracts table, the invariants and the open questions (order, entry point) are all updated consistently.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The inversion logic is in a small immutable  SpecialtyDirectory  value object, so the rule can be tested without booting the web layer.  SpecialtyController.showSpecialtyDirectory  stays thin: it asks two repositories for data, delegates, and returns the view. The new  SpecialtyRepository  follows the style of the existing repositories. The unit tests use BDD names, factory methods, and whole-object  containsExactly  comparisons, and they cover a vet holding several specialties, a vet holding none, a specialty nobody holds, and matching by id. The controller tests are weaker. They depend on seeded data from outside the test, and  containsString("Helen Leary")  never checks that she appears under radiology.  Listing  also exposes mutable  Vet  entities. The docs are current:  prd.md  adds REQ-VET-003 and records the open questions, and the rows and package tree in  system-design.md  are updated.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $8.21 | 16m | 15 | 91% | 8 file(s) +392/−6 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.65 | 1m 5s | 83% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · **1 build-failure** · grade **SCRUTINIZE**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | **✔** | · |
| **security** | **✔** | · |
| **doc** | ✎ (2) | **✔** |

- ◇ **intake** Feature request: the vet list answers "which specialties does this vet hold", but staff also ask the inverse — "which vets hold this specialty". Two product decisions come with it, made here as the product owner: - A read-only specialty view of the existing directory is in scope; managing   veterinarians or specialties stays out of scope as before (non-goal NG-2   is unchanged). - The page is reachable by its URL alone: no navigation entry and no link   from another page is part of this request. A visible entry point may come   as a follow-up request. Add a specialty directory page: - GET /specialties.html lists every specialty the clinic knows by its stored   name, each with the veterinarians holding it. - Each veterinarian is shown by full name: first name, then last name (for   example "Helen Leary"). - A veterinarian holding no specialty appears under no specialty; the page   lists specialties, not the full vet roster. - All specialties render on one page — no pagination. Cover the new behavior with tests. These are all the product decisions; no further product answer will come during the work. Where a choice still seems open, take the narrowest reading consistent with this request and record the open question rather than waiting. · (2 decisions) · (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **minor** · (design) · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 5m***
  - ▲ **build ✗ build failed** · retry 1
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 26s***
- ✔ **review test** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✎ **review doc** · **changes_requested** · (2 findings) · ***◷ 2m***
  - **[blocked]** `prd.md:138` The REQ-VET-003 "Done when" bullet embeds the literal route `/specialties.html` ("when the specialty directory at `/specialties.html` is opened"). This is mechanism, not behavior: system-design.md's own Constants section states "The controllers' view-name constants are private routing details and are deliberately not listed here" (docs/system-design.md:68) — the project's own convention treats the exact route as an implementation detail excluded even from system-design.md, let alone the PRD. The sibling requirement REQ-VET-001 (docs/prd.md:121-129) names no route at all, describing reachability purely behaviorally ("when the directory is opened"). REQ-VET-003 can state that the directory is reachable by a stable address with no navigation entry (already covered in the narrative prose at docs/prd.md:135) without naming the literal path.
  - [autofix] `prd.md:144` REQ-VET-003 is missing the `**Design:**` cross-reference that its sibling REQ-VET-001 carries (docs/prd.md:130, `**Design:** [system-design.md#contracts](system-design.md#contracts)`), even though docs/system-design.md now documents SpecialtyRepository, SpecialtyDirectory, and SpecialtyController under REQ-VET-003 (docs/system-design.md:102-107). The `prd-authoring` requirement format adds a `**Design:**` link "where they exist"; one exists here.
    - fix: \**Design:** [system-design.md#contracts](system-design.md#contracts)
- ↻ **fix prd-expert** ← doc · (2 findings)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 14s***
- ◈ **design-block** **covered** · (design) · ***◷ 20s***
- ◆ **implement** (implementer) · ***◷ 29s***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 7s***
- ◆ **grade SCRUTINIZE** · add read-only specialty directory page
  - blast_radius — **skim** — Six new files, all in the vet package, plus prose edits to prd.md and system-design.md; no existing Java or template is modified, no sensitive paths, and the two security-surface files are a parameterless read-only GET and a constant JPQL query.
  - semantic_surprise — **skim** — Read every hunk: SpecialtyDirectory.of maps each repository specialty to the vets whose specialties match by id, so unheld specialties still list and specialty-less vets appear nowhere; the template escapes via th:text and reuses existing, fully translated keys; the unknown 'specialties' menu name only leaves no nav item active. The one latent edge (null specialty id would NPE) cannot arise for persisted rows.
  - test_adequacy — **skim** — Unit tests assert exact listings with containsExactly, covering several-specialty, no-specialty, unheld-specialty and id-not-identity matching, and each would fail against a broken inversion; the MockMvc tests only check that seed names appear somewhere on the page, not under which row, but the template's iteration is trivial and was read directly.
  - reviewer_hedging — **scrutinize** — All four reviewers approved with no findings or recommendations and most citations resolve (SpecialtyController.java:38, SpecialtyRepository.java:37, SpecialtyDirectory.java:49 checked), but the code-quality approval cites SpecialtyRepository.java:22,28-29,32,35 for the annotations and interface, which actually sit at lines 30, 36-38; the claim itself is true in the diff, yet the citation does not resolve.
  - scope_deviation — **skim** — The change matches the intake and prd-entry surface: one unpaged GET page, no navigation link, no management operations, no new message keys; the only fix round changed docs/prd.md prose after a doc-reviewer finding, with no code or behavior delta, and the earlier build-failure was a planned partial checkpoint, not a failed build.
  - why — The code is a small, contained read-only feature whose inversion logic reads correctly and is well unit-tested. The only flag is a code-quality citation with line numbers that do not resolve; the claim it backs holds. A human can skim the diff and spot-check SpecialtyRepository.java against VetRepository.java.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Exposed surface: the one new endpoint is a read-only GET (SpecialtyController.java:38  @GetMapping("/specialties.html") ) that binds no request parameter, path variable, @ModelAttribute or @RequestBody, so it adds no mass-assignment or input-validation surface. It exposes specialty names and veterinarian names, the same data the existing /vets.html already publishes. No new management exposure.
- Data access: SpecialtyRepository.java:37  @Query("SELECT specialty FROM Specialty specialty ORDER BY specialty.name")  is a constant JPQL string with no concatenated or request-derived value. It is read-only ( @Transactional(readOnly = true) , line 36), so it adds no injection path.
- Output escaping: specialtyList.html renders every data value through escaping  th:text  (line 18  th:text="${listing.specialtyName}" , line 21  th:text="${vet.firstName + ' ' + vet.lastName + ...}" ).  grep -rn -F 'th:utext' src/main/resources/templates/  returned nothing. The layout's  __${link}__  preprocessing (fragments/layout.html:31) receives only literal menu links, and the new template passes only the literal menu name 'specialties'. No request text reaches expression evaluation.
- Unbounded page: listing every specialty with no paging is the PRD's stated requirement (REQ-VET-003 edge case 3). The lookup table is bounded by staff-entered data, not by caller input. VetRepository.findAll is  @Cacheable("vets") , and Vet specialties load eagerly (Vet.java:47  @ManyToMany(fetch = FetchType.EAGER) ), so a request triggers at most one uncached specialty query. No caller-controlled amplification.
- SpecialtyDirectory is an immutable value (List.copyOf on both record components). It performs no I/O, logging, reflection or deserialization, and the singleton controller holds no mutable state.
- Secrets sweep: I read the full diff and found no credential, token, key or connection string. There are no new log statements and no exception messages.
- Supply chain: the diff changes no dependency ( git status --short build.gradle pom.xml  is empty). OWASP Dependency-Check is not configured ( grep -n -F 'dependencyCheck' build.gradle  found nothing), so no NVD match ran in this review. From  ./gradlew dependencies --configuration runtimeClasspath , the resolved versions are Spring Boot 4.1.1, Thymeleaf 3.1.5.RELEASE and tools.jackson.core:jackson-databind 3.1.5.

**test-reviewer**

- SpecialtyDirectoryTests exercises the id-matching business rule (SpecialtyDirectory.of, src/main/java/.../vet/SpecialtyDirectory.java:39-50) at the unit seam the design-block assigns it to (line 5 architectural_fit), never through the web layer; SpecialtyControllerTests (src/test/java/.../vet/SpecialtyControllerTests.java) then covers only request binding and response shaping, matching testing-principles.md's pyramid placement rule ('rules the design doc assigns below the boundary')
- All five Done-when/edge-case behaviors from the prd.md REQ-VET-003 entry have a named test matching them, confirmed via  python3 scripts/grading.py coverage-map  ('Declared tests: 5 of 5 present')
- No mock framework used anywhere in the new suite; SpecialtyDirectoryTests builds real Vet and Specialty entities and MockMvc (the sanctioned transport double per testing-principles.md § Mocking Policy) drives real repositories over the H2 seed data in SpecialtyControllerTests, matching design-block's integration_points guidance (line 5)
- Test data follows the three-tier naming convention: RADIOLOGY_ID/RADIOLOGY are Tier-1 meaningful constants, ANY_VET_ID/ANY_FIRST_NAME are Tier-2 irrelevant values, and no bare literals appear in either test file (SpecialtyDirectoryTests.java:31-45, SpecialtyControllerTests.java:39-49)
- Construction goes through suite-owned factories (createASpecialty, createAVet, createAListing in SpecialtyDirectoryTests.java:93-113) with no raw  new Specialty() / new Vet()  calls outside them, confirmed via  python3 scripts/grading.py conventions-map  which flags zero raw-construction findings for the changed test files
- Test names follow the theSubjectShouldOutcome BDD school (testing-principles.md § Test Naming) in both new test files, e.g. theSpecialtyDirectoryShouldListASpecialtyNoVeterinarianHolds
- SpecialtyDirectoryTests.theSpecialtyDirectoryShouldMatchAHeldSpecialtyToTheListedOneByItsId (lines 82-91) directly covers the identity-vs-value-equality risk the design-block's risks[0] names (distinct Specialty instances sharing an id), preventing the silent-drop-to-empty-directory failure mode
- ./gradlew test (including jacocoTestReport) passes clean; no skips or failures in the Specialty* suite

**code-quality-reviewer**

- Business-rule placement matches the design-block: the specialty-to-vet inversion lives in SpecialtyDirectory.of/listingFor/holds (src/main/java/.../vet/SpecialtyDirectory.java:39-50), and SpecialtyController only calls SpecialtyDirectory.of(...) and returns a view name (src/main/java/.../vet/SpecialtyController.java:38-42) — no business rule in the controller.
- SpecialtyRepository mirrors VetRepository's precedent exactly:  public interface VetRepository extends Repository\<Vet, Integer>  (src/main/java/.../vet/VetRepository.java:38) with a custom @Transactional(readOnly=true) findAll(); SpecialtyRepository follows the same shape (src/main/java/.../vet/SpecialtyRepository.java:22,28-29,32,35).
- SpecialtyDirectory and Listing are immutable records using List.copyOf in their compact constructors (src/main/java/.../vet/SpecialtyDirectory.java:30-32,60-62), matching the value-object rule.
- The id-based matching risk the design-block flagged is implemented ( held.getId().equals(specialty.getId()) , SpecialtyDirectory.java:49) and covered by a dedicated unit test using distinct Specialty instances sharing an id (SpecialtyDirectoryTests.java: theSpecialtyDirectoryShouldMatchAHeldSpecialtyToTheListedOneByItsId).
- conventions-map (base 2e53972) shows every added comment block is a WHY-comment (rationale for id-matching, repository purpose, class purpose) with no restated code and no requirement-id or handoff vocabulary leaking into comments.
- No navigation entry or link was added to fragments/layout.html or any other template (absent from  python3 scripts/changeset.py --name-only ), matching the PRD non-goal that the page is reachable by URL alone.
- ./gradlew checkFormat passes (checkFormatMain, checkFormatTest, checkFormat all UP-TO-DATE/BUILD SUCCESSFUL).

**doc-reviewer**

- Every REQ-VET-003 reference in docs/system-design.md (lines 100-107) traces back to a corresponding requirement in docs/prd.md (anchor req-vet-003 at docs/prd.md:132) — no dangling requirement ID
- docs/system-design.md's Contracts-table additions for SpecialtyRepository and SpecialtyDirectory (lines 102-103) stay at contract-purpose altitude — no field/parameter table, no enumerated rule listing
- All six new/changed code and test paths named in the diff (SpecialtyController.java, SpecialtyDirectory.java, SpecialtyRepository.java, specialtyList.html, SpecialtyControllerTests.java, SpecialtyDirectoryTests.java) resolve in the working tree (grep -F/ls confirmed)

**doc-reviewer**

- docs/prd.md:138 no longer names the literal route; it now reads "when the specialty directory is opened", matching REQ-VET-001's behavioral phrasing (docs/prd.md:121-129) and system-design.md's own convention that routes are private routing details (docs/system-design.md:68)
- docs/prd.md:147 adds  **Design:** [system-design.md#contracts](system-design.md#contracts) ; the  ## Contracts  heading at docs/system-design.md:72 resolves the anchor, and that section lists SpecialtyRepository, SpecialtyDirectory, and SpecialtyController under REQ-VET-003 (docs/system-design.md:100-107)
- Fix delta is confined to docs/prd.md; no other file in the base-tree diff ( python3 scripts/changeset.py --base-tree e75810889367588c7433eaca3b4b9173bd5bc3ae --name-only  showed only docs/prd.md)

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $1.82 | 6m 30s | 93% |
| `(parent)` | 1 | opus-5 | $1.66 | 16m 52s | 96% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $1.44 | 2m 13s | 89% |
| `agent-team:system-design-expert` | 2 | opus-5 | $1.37 | 2m 12s | 85% |
| `agent-team:change-grader` | 1 | opus-5 | $0.65 | 1m 5s | 83% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.63 | 3m 8s | 93% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.49 | 35s | 82% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.37 | 1m 49s | 91% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.34 | 1m 51s | 88% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $1.66 | 16m 52s | 96% |
| `agent-team:feature-implementer` | opus-5 | $1.51 | 5m 46s | 94% |
| `agent-team:system-design-expert` | opus-5 | $0.91 | 1m 40s | 87% |
| `agent-team:product-requirements-expert` | opus-5 | $0.79 | 1m 22s | 88% |
| `agent-team:product-requirements-expert` | opus-5 | $0.65 | 50s | 89% |
| `agent-team:change-grader` | opus-5 | $0.65 | 1m 5s | 83% |
| `agent-team:security-reviewer` | opus-5 | $0.49 | 35s | 82% |
| `agent-team:system-design-expert` | opus-5 | $0.45 | 31s | 82% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.45 | 2m 34s | 94% |
| `agent-team:test-reviewer` | sonnet-5 | $0.37 | 1m 49s | 91% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.34 | 1m 51s | 88% |
| `agent-team:feature-implementer` | opus-5 | $0.31 | 43s | 82% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.18 | 33s | 88% |

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

- plugin `agent-team-spring-boot` at `v0.4.3` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `0aff9592719d` (branch `agent-team`)
- task fingerprint `dfad163fa162236e` · `2.1.274 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
