# specialty-directory r2 — v0.3.8

Specialty directory page (feature) · started 2026-08-21T13:11:18+00:00 · exec `claude-dev` · status **complete**

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
| 5 (±0) | 4 (±0) | 4 (±1) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.66. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Derivation sits in an immutable  SpecialtyDirectory  record with a static factory, leaving  SpecialtyController.showSpecialtyList  to bind, delegate, select — the *Web controller* row honored rather than widened, and justified by an ADR naming the option set. Naming, package placement, and the narrow  SpecialtyRepository  (single declared read, no CRUD base) match the catalog. Tests are behavior-named, four-phase, factory-built via  VetTestFixtures , and unit-testable without Spring; deductions for bare literals ( "Helen" ,  "radiology" ,  "Helen Leary" ) that the three-tier convention would name, and for Mockito stubbing of internal repositories.  specialtyList.html  introduces  #{specialties} / #{none}  with no bundle change in the patch, and ordering is enforced twice (query  ORDER BY  plus  sorted() ). Documentation is thorough: PRD, ADR index, contracts, package tree, open questions, vocabulary.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 3 · doc-fit 5

> SpecialtyDirectory.java lands the inversion in an immutable record with defensive copies (List.copyOf) and a static factory, leaving SpecialtyController.showSpecialtyList to bind, delegate, and pick a view — the Web controller row honoured, with an ADR recording it. Tests are behavior-named (theSpecialtyDirectoryShouldListASpecialtyNoVeterinarianHolds), phase-structured, and built behind VetTestFixtures factories; gaps are the untested empty-clinic edge case the PRD itself lists and the CSS-coupled 'nav-link active' assertion. The real weakness: specialtyList.html introduces #{specialties} and #{none} but no messages bundle is touched, so the page renders ??specialties?? and the REQ-LANG-002 key-parity test breaks. Docs move thoroughly — PRD, ADR index, contracts table, package line, vocabulary.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyDirectory is an immutable record with List.copyOf defensive copies, deriving page content outside the controller; SpecialtyController only binds, delegates and selects a view, so no new rule lands in the web layer, and SpecialtyRepository follows the existing narrow-read repository shape. Tests are behavior-named (theSpecialtyDirectoryShouldListASpecialtyNoVeterinarianHolds), phase-separated, built through VetTestFixtures factories, and put the derivation rules in a framework-free unit test with the slice test covering only web concerns. Deductions: SpecialtyControllerTests still stubs both repositories with @MockitoBean where a hand-written double would fit a one-method interface, and SpecialtyDirectoryTests uses bare literals ("radiology", "Helen Leary") rather than named meaningful values; ordering is applied twice (@Query ORDER BY plus .sorted()). Docs are fully current: ADR, PRD REQ-SPEC-001, contracts table, package tree, vocabulary.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $16.64 | 34m | 54 | 92% | 13 file(s) +592/−3 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.37 | 3m 29s | 90% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPECIALTYDIRECTORY-001

0 review rounds · 0 build-passes · no grade yet

- • intake-decision (human)

---

### REQ-SPEC-001 — Specialty directory

2 review rounds · 2 build-passes · **3 build-failures** · grade **CONCERN**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | · |
| **doc** | ✎ (2) | **✔** |

- ◇ **prd-entry** Specialty directory · (prd-expert)
- ◈ **design-block** **new** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 10m***
  - ▲ **build ✗ build failed** · retry 1
  - ▲ **build ✗ autofix-audit failed** · retry 2
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 1m***
- ▲ **build-pass** 13:35 · build, test, checkFormat, checkstyleMain, handoff-validate, audit-autofix, contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain was not verified against the NVD in this review, and this is a gap in coverage rather than a clean result: the change touches no build file (build.gradle is not in the change set) and adds no dependency, and the OWASP dependency-check plugin is not configured in this project, so no `dependencyCheckAnalyze` run was possible. A human or CI closes the standing framework-CVE check for Spring Boot 4.1.0 and its managed Jackson version; nothing in this slice widens that surface.
  - ▹ rec: Optional documentation follow-up, not a defect: docs/system-design.md records the new route in the Contracts table but its Security Context bullets (Inputs it processes / Outputs it produces) and Threat Model table were not extended. Both already cover the route generically (server-rendered Thymeleaf HTML, escaped output), so the security-principles requirement that a new endpoint state what it exposes is met; naming the specialty directory alongside the vet routes in Security Context would keep the derived posture description complete as read-side pages accumulate.
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `SpecialtyControllerTests.java:110-124` createSpecialty(String) and createVeterinarian(String,String,Specialty...) are copy-pasted verbatim, private, in both new test classes in the same package. testing-principles.md 'Testing Vocabulary' calls the factory vocabulary a project-wide asset ('Extract shared test utilities into a common base class or utility module'), and the Agent Decision Checklist item 14 asks for zero duplication of reusable patterns. Both files are freshly authored in this slice, so this is new duplication, not pre-existing debt the brief exempts.
    - fix: Extract createSpecialty and createVeterinarian into a shared package-private test helper (e.g. a VetTestFixtures utility class or a shared base) in org.springframework.samples.petclinic.vet, and have both SpecialtyControllerTests and SpecialtyDirectoryTests use it instead of their own private copies.
- ✎ **review doc** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `prd.md:12` New provenance-note sentence added by this slice uses a relative reference ("the derivation above") instead of naming what it points to, violating the "no relative references" structural rule.
    - fix: `REQ-SPEC-001` is the one exception to that observed-behavior derivation. The product owner stated it on 2026-08-21; it was not reconstructed from observed behavior.
  - [autofix] `prd.md:150` The new Specialty directory section is the only requirement section with a dedicated ADR that omits the sibling sections' trailing cross-reference line (Owner records, Pet records, and Veterinarian directory each close with a **Design:** and/or **ADR:** link). A reader following the section pattern has no pointer from this requirement to the mechanism and the decision that realize it.
    - fix: \**Design:** [system-design.md#contracts](system-design.md#contracts) · **ADR:** [Read-Side View Model for the Specialty Directory](adr/2026-08-21-read-side-view-model-for-the-specialty-directory.md)
- ✚ **prd-autofix** `docs/prd.md` · structural · (root)
- ↻ **fix prd-expert** ← doc · (2 findings)
- ↻ **implement** (implementer) ← test · (1 finding)
- ◇ **prd-entry** Specialty directory · (prd-expert) · ***◷ 1m***
- ▲ **build-pass** 13:43 · build, test, checkFormat, checkstyleMain, handoff-validate, audit-autofix, contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 28s***
- ✔ **review test** · **approved** · ***◷ 22s***
- ✔ **review doc** · **approved**
- ◆ **grade CONCERN** · publish the specialty directory page
  - blast_radius — **clear** — Thirteen files in one module, twenty-one hunks, and every production hunk is a new file: SpecialtyController, SpecialtyRepository, SpecialtyDirectory, and specialtyList.html add a route with zero deletions from existing production code. The only edits to existing files are an additive test in ClinicServiceTests and four docs. No sensitive paths, no build files, no dependency change, no shared code modified, so nothing already shipping can regress.
  - semantic_surprise — **clear** — Read the derivation, the template, and the repository query line by line and nothing does more than it claims. SpecialtyDirectory inverts the one-way Vet-to-Specialty mapping by grouping holder display names under specialty names, keeps an entry for an unheld specialty via getOrDefault, and drops a veterinarian holding nothing because the flatMap starts from the vet's specialty set. The apparent first-name/last-name mismatch is not one: display is first-then-last, sort is last-then-first, deliberately. distinct() was removed on purpose so a duplicate stored name is not silently collapsed. The template passes a layout menu argument matching no menuItem, so no navigation entry is marked active, uses th:text only with no th:utext, and the eager Vet-to-Specialty fetch means the open-in-view=false setting cannot bite. One cosmetic residual: an unheld specialty renders the reused none message key rather than an empty cell, where the PRD open question describes listing it with nothing under it. It mirrors vetList.html exactly and satisfies the criterion as written.
  - test_adequacy — **clear** — The tests are real, not tautological. Seven unit tests drive SpecialtyDirectory with real domain objects and no Spring context, asserting containsExactly on ordering including a last-name tie-break, so a broken sort fails them. Six MockMvc tests carry genuine negative assertions that would catch the likely regressions: a veterinarian holding no specialty absent from the rendered page, no active navigation entry, and no link to the route in the shared navigation. ClinicServiceTests adds a real-I/O test proving the JPQL ORDER BY against seeded data. All four message keys the template uses already exist in all ten populated bundles, verified directly, so the build-time i18n sync test genuinely covers the language criterion. The one gap is small: no test asserts what renders in the cell for an unheld specialty, only that the row exists.
  - reviewer_hedging — **concern** — Round 2 is clean for all three reviewers the risk-proportional plan dispatched, with empty findings. The hedge is in the security reviewer's round-1 approval, which is the only round it ran and which carries two parked recommendations: it states plainly that supply chain was not verified against the NVD and calls that a gap in coverage rather than a clean result, leaving the standing Spring Boot 4.1.0 framework-CVE check to a human or CI; and it notes that system-design.md Security Context and Threat Model were not extended to name the new route, even though this slice edits that document. Neither reached a finding, so nobody closed either, and this facet is where they reach the human.
  - scope_deviation — **clear** — Zero consultations, zero build retries, and the single design revision was bookkeeping: a superseding design-block adding two doc paths the first record's prose described but its path list omitted, which is what tripped the autofix audit. The change departs from the prd-entry file targets by adding a separate SpecialtyController rather than extending VetController and by touching no message bundle, but the design-block decided both explicitly and for stated reasons. Every non-goal holds: no navigation entry, no link from another page, no pagination, no search, no management surface.
  - why — Read every hunk; the derivation, template, and query are contained, additive, and behave as described, with unusually real tests. Nothing here needs a careful correctness read. What does need a human is the security reviewer's parked pair: the supply-chain check was never run, and the new route is absent from the Security Context and Threat Model this slice already edits.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyDirectory is an immutable record with defensive List.copyOf on both the outer record and nested Listing, and equality by value (verified by an explicit equality test)
- Derivation logic (inverting the Vet-to-Specialty association) lives in the read-side model rather than the controller, matching the ADR it cites
- SpecialtyController and VetController are consistently package-private with public constructor injection and no @Autowired, matching the existing controller in the same package
- SpecialtyRepository declares only the one query it needs (findSpecialties) rather than extending a CRUD base interface, with a Javadoc explaining why
- Stream pipelines used throughout for the specialty/veterinarian derivation instead of manual loops; no raw loops or mutable accumulators
- Template's 'no navigation entry' behavior is documented inline with a rationale comment tied to the requirement ID
- checkFormat and checkstyleMain both pass clean on the change set

**security-reviewer**

- No request-derived input anywhere on the new surface: GET /specialties.html binds no parameter, path variable, header, or body, so the boundary rows for validation, mass assignment, and path traversal in docs/security-principles.md are not engaged. The controller declares no @InitBinder because it binds no command object.
- Data access is a constant JPQL string in SpecialtyRepository.findSpecialties() with no interpolation and no request-derived value, matching the SQL-injection mitigation recorded in docs/system-design.md Threat Model. VetRepository.findAll() is an unchanged derived query.
- Output escaping stays on and matches the neighboring templates: specialtyList.html uses th:text only (specialtyName, veterinarianName, and #{} message keys). Swept src/main/resources/templates/ for th:utext, Thymeleaf preprocessing (__${...}__), inline \<script>, javascript:/data: URIs, and inline event handlers on the new file: none present. Stored specialty and veterinarian names therefore reach the page escaped, so the XSS row holds.
- Exposed-surface delta is a read-only GET returning data already public at the unchanged /vets.html and /vets routes (veterinarian names and their specialties). No new data class is disclosed, no mutating route is added, and no actuator or management exposure changes. The endpoint and what it serves are stated in docs/system-design.md (Contracts table) and the controller Javadoc.
- No new resource-exhaustion vector relative to the baseline: the unpaginated vetRepository.findAll() read is @Cacheable("vets") and is already reached unauthenticated by VetController.showResourcesVetList(); findSpecialties() reads a three-row seeded lookup table. Both results are copied into immutable lists, so no unbounded per-request allocation is introduced.
- Thread safety holds for the singleton scope: SpecialtyController is stateless with final injected fields, SpecialtyDirectory and Listing are records whose compact constructors defensively List.copyOf their collections, and the static Comparator is immutable. The derivation reads the cached Vet graph without mutating it.
- No secrets, credentials, tokens, or connection strings introduced in any changed file; no new committed configuration or property values at all.
- Swept the vet package for the skill's detection patterns: no Runtime/ProcessBuilder/exec, no FileWriter/FileOutputStream/Files IO, no system /tmp usage, no @JsonTypeInfo or enableDefaultTyping, no java.util.Random, no logging (so no log-injection or sensitive-value log path), and no exception message that could carry internal detail to the error page.

**test-reviewer**

- SpecialtyDirectoryTests is a true unit test (no Spring context, real value objects only) per the mocking policy's real-objects-first rule and the ADR's stated intent; SpecialtyControllerTests mocks only the repositories behind @WebMvcTest, matching the existing VetControllerTests convention (mocking policy's system-boundary exception, consistent-with-codebase)
- Edge cases from the PRD acceptance criteria are each covered by a dedicated, correctly-named test: specialty with no holder, vet with no specialty, stable ordering including a last-name tie-break, one-page listing, standard navigation present, no active nav entry, no inbound link
- New SpecialtyDirectory/SpecialtyController/Listing/Specialty classes are at 100% line and branch coverage per jacocoTestReport, well above the 80% domain-package target
- ClinicServiceTests adds a real-I/O integration test (theSpecialtyRepositoryShouldReturnEverySpecialtyInNameOrder) against actual test fixture data, exercising the JPQL ORDER BY clause end to end
- All test names follow the brief's BDD naming school (the{Subject}Should{Outcome}); AssertJ used throughout with no JUnit assertEquals/assertTrue; no phase comments or narration; four-phase structure observed with blank-line separation
- Test data naming is clean: HELD_SPECIALTY/UNHELD_SPECIALTY constants are role-named (Tier 1), and specialty-name literals used as ordering-test inputs are the meaningful values under test, not mystery literals
- ./gradlew test passes with all specialty-related and ClinicServiceTests tests green

**doc-reviewer**

- prd.md, system-design.md, the new ADR, adr/README.md, and ubiquitous-language.md stay coherent: REQ-SPEC-001 exists in both prd.md and system-design.md's Contracts table, the ADR's Requirements line matches, the ADR is indexed in adr/README.md, and "Specialty directory" is defined in ubiquitous-language.md
- PRD's Specialty directory section stays behavioral prose with no code, mechanism, or rationale leakage — clean boundary
- the apparent order conflict between the PRD ("first name then last name") and the ADR/code (last-name-then-first-name sort) is not a contradiction: the PRD phrase describes display format, the ADR/code passage describes sort order, and both are confirmed against SpecialtyDirectory.java and its tests
- the ADR's claim that SpecialtyController holds no rule and that the page carries no navigation entry both check out against the actual controller and template

**code-quality-reviewer**

- Fix delta correctly resolves the round-1 duplication finding: createSpecialty/createVeterinarian are extracted into a new package-private VetTestFixtures with a private constructor and static factory methods; both SpecialtyControllerTests and SpecialtyDirectoryTests now static-import them, and a sweep of src/ confirms no remaining duplicate definitions.
- VetTestFixtures carries a class-level Javadoc explaining its role as shared factory vocabulary for the vet package's tests, consistent with testing-principles.md's shared-utility guidance.
- docs/prd.md fix-delta edits (relative-reference rewording and the added Design/ADR cross-reference line) are structurally sound and match the sibling sections' pattern.
- checkFormat and checkstyleMain both pass clean on the fix delta.

**test-reviewer**

- Round-1 autofix finding fully resolved: createSpecialty/createVeterinarian are extracted into a new package-private VetTestFixtures utility class in org.springframework.samples.petclinic.vet, and both SpecialtyControllerTests and SpecialtyDirectoryTests now static-import them instead of holding private copies
- Class-exhaustive sweep: no remaining private createSpecialty/createVeterinarian (or similar) duplicates anywhere under src/test/java/org/springframework/samples/petclinic/vet/
- VetTestFixtures follows existing test-helper conventions (final class, private constructor, package-private static factory methods, real domain objects, no mocking)
- ./gradlew test (vet package and ClinicServiceTests) passes; jacocoTestReport regenerates cleanly with no coverage regression
- Test-only refactor; no behavioral change to the specialty directory tests themselves, so the previously-approved edge-case and pyramid coverage from round 1 still holds

**doc-reviewer**

- docs/prd.md:12 no longer uses a relative reference ("the derivation above") — it names the antecedent directly ("that observed-behavior derivation")
- docs/prd.md:150 now carries the Design/ADR cross-reference line, matching the exact format of the sibling Owner records, Pet records, and Veterinarian directory sections
- the new ADR link and system-design.md#contracts anchor both resolve to real targets
- swept the whole doc set for the relative-reference class ("above", "below", "previous section", "earlier in this", "as explained") — no remaining instances
- cross-document coherence holds: REQ-SPEC-001 still appears consistently in prd.md, system-design.md's Contracts table, the ADR, and adr/README.md; the test-only VetTestFixtures refactor in this fix delta touches no documentation surface

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $11.76 | 16m 36s | 91% |
| `(parent)` | 1 | opus-5 | $5.41 | 37m 6s | 96% |
| `agent-team:system-design-expert` | 2 | opus-5 | $4.49 | 6m 26s | 90% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $3.76 | 5m 45s | 91% |
| `agent-team:change-grader` | 1 | opus-5 | $2.37 | 3m 29s | 90% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.40 | 3m 31s | 95% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.36 | 2m 55s | 91% |
| `agent-team:security-reviewer` | 1 | opus-5 | $1.26 | 1m 43s | 85% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $1.00 | 1m 53s | 90% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $10.73 | 14m 40s | 91% |
| `(parent)` | opus-5 | $5.41 | 37m 6s | 96% |
| `agent-team:system-design-expert` | opus-5 | $2.66 | 4m 13s | 90% |
| `agent-team:change-grader` | opus-5 | $2.37 | 3m 29s | 90% |
| `agent-team:product-requirements-expert` | opus-5 | $2.18 | 4m 6s | 93% |
| `agent-team:system-design-expert` | opus-5 | $1.83 | 2m 12s | 89% |
| `agent-team:product-requirements-expert` | opus-5 | $1.58 | 1m 38s | 86% |
| `agent-team:security-reviewer` | opus-5 | $1.26 | 1m 43s | 85% |
| `agent-team:test-reviewer` | sonnet-5 | $1.09 | 2m 13s | 92% |
| `agent-team:feature-implementer` | opus-5 | $1.03 | 1m 55s | 91% |
| `agent-team:doc-reviewer` | sonnet-5 | $1.02 | 2m 24s | 95% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.55 | 1m 19s | 93% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.45 | 34s | 85% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.38 | 1m 6s | 92% |
| `agent-team:test-reviewer` | sonnet-5 | $0.27 | 42s | 89% |

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
