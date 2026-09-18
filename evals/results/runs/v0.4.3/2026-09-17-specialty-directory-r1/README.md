# specialty-directory r1 — v0.4.3

Specialty directory page (feature) · started 2026-09-17T19:53:09+00:00 · exec `claude-dev` · status **complete**

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

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.70. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController stays a thin adapter (showSpecialtyDirectory binds nothing, delegates to SpecialtyDirectory.of), the inversion lives in an immutable record with List.copyOf defensive copies, and the new non-catalog type is justified by an ADR that weighs four options — exactly what the Design Validation Checklist demands. SpecialtyDirectoryTests are exemplary: behavior names, factories, named constants, whole-object comparison via entryFor, boundary cases (empty, unheld, duplicate stored name, identifier matching). Deductions: StoredSpecialties/StoredVeterinarians are Spring-bean shared mutable fixtures reset by emptyTheClinic(), against 'Never Share Mutable Fixtures'; createASpecialty/createAVeterinarian are duplicated verbatim across both test classes instead of extracted; theSpecialtyDirectoryShouldBeLinkedFromNoPage walks a working-directory-relative TEMPLATE_ROOT and grep-matches 'href', brittle and needing no web context. Docs (prd, system-design contracts, ADR index) all move together.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Inversion lives in an immutable  SpecialtyDirectory  record with a pure static  of(...)  factory and defensive  List.copyOf , leaving  SpecialtyController.showSpecialtyDirectory  as pure binding/delegation — no new controller rule; the unlisted read-model pattern is justified by a dated ADR, and naming/visibility match the catalog. Unit tests are behavior-named ( theSpecialtyDirectoryShouldOmitAVeterinarianHoldingNoSpecialty ), four-phase, factory-built, mystery-value-free, and use hand-written  StoredSpecialties / StoredVeterinarians  doubles rather than a mock framework. Weaknesses:  createASpecialty / createAVeterinarian  are duplicated verbatim across both test files instead of a shared vocabulary, and  theSpecialtyDirectoryShouldBeLinkedFromNoPage  greps template files under a CWD-relative  TEMPLATE_ROOT  for  href  — brittle and out of place in a  @WebMvcTest . PRD, system-design contracts, provenance banners, and ADR index all move with the change.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The inversion lands in an immutable read model ( SpecialtyDirectory.of ) rather than the controller, so  SpecialtyController.showSpecialtyDirectory  only reads repositories and selects a view — matching the Web controller row — and the novel type is justified by a new ADR indexed in  docs/adr/README.md , with  prd.md  REQ-VET-003, its Done-when bullets, the NG-9 open question, and the  system-design.md  contracts table and package line all updated. Unit tests are behavior-named, factory-built, hand-doubled, and cover ordering, identity matching, and empty cases. Weaknesses:  theSpecialtyDirectoryShouldBeLinkedFromNoPage  greps template lines for  href , passing on any reformatted or split link; the  StoredSpecialties / StoredVeterinarians  beans are shared mutable fixtures cleared per test; and  specialtyList.html  uses  #{specialties} / #{vets}  with no message-bundle additions.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $9.11 | 23m | 21 | 94% | 10 file(s) +660/−5 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.76 | 2m 5s | 85% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

1 review round · 1 build-pass · grade **SKIM**

| reviewer | R1 |
| --- | --- |
| **code-quality** | **✔** |
| **test** | **✔** |
| **security** | **✔** |
| **doc** | **✔** |

- ◇ **intake** Feature request: the vet list answers "which specialties does this vet hold", but staff also ask the inverse — "which vets hold this specialty". Two product decisions come with it, made here as the product owner: - A read-only specialty view of the existing directory is in scope; managing   veterinarians or specialties stays out of scope as before (non-goal NG-2   is unchanged). - The page is reachable by its URL alone: no navigation entry and no link   from another page is part of this request. A visible entry point may come   as a follow-up request. Add a specialty directory page: - GET /specialties.html lists every specialty the clinic knows by its stored   name, each with the veterinarians holding it. - Each veterinarian is shown by full name: first name, then last name (for   example "Helen Leary"). - A veterinarian holding no specialty appears under no specialty; the page   lists specialties, not the full vet roster. - All specialties render on one page — no pagination. Cover the new behavior with tests. These are all the product decisions; no further product answer will come during the work. Where a choice still seems open, take the narrowest reading consistent with this request and record the open question rather than waiting. · (2 decisions) · (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 10m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 59s***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ◆ **grade SKIM** · add read-only specialty directory page
  - blast_radius — **skim** — Purely additive inside one module: four new files under the vet package plus a template, zero deletions and no edit to any existing production Java file, no build, config, schema, or sensitive path touched; the only new surface is one GET route that reads two repositories.
  - semantic_surprise — **skim** — Read the whole of SpecialtyDirectory, the controller, the repository, and the template: the inversion keys on Specialty::getId rather than equals (deliberate, since BaseEntity overrides neither), holders are sorted once by last-then-first name before distribution so per-entry order is stable, an unheld specialty keeps an empty list, and every template value renders through th:text with no utext and no preprocessed expression.
  - test_adequacy — **skim** — Nine unit tests over the real record assert whole-object equality and would fail on wrong order, a missed multi-specialty holder, an omitted unheld specialty, or name-collided specialties; the controller slice uses hand-written repository doubles and asserts rendered content, and the no-link criterion is a file walk over every template. The one untested branch is the template's none fallback for an unheld specialty, which mirrors the equally untested existing branch in vetList.html and resolves against a key present in the default bundle.
  - reviewer_hedging — **skim** — All four dispatched reviewers approved with empty findings and empty recommendations, and every aspect names concrete evidence; I resolved four cited coordinates (SpecialtyController.java:39-40, SpecialtyDirectory.java:34/53/68, SpecialtyDirectoryTests.java:118/128, SpecialtyControllerTests.java:106) and each landed exactly where claimed. The security reviewer's note that OWASP Dependency-Check is unconfigured is a standing project gap on a change that touches no dependency, not a reservation.
  - scope_deviation — **skim** — Zero build retries, zero consultations, zero design revisions; the diff matches the design-block's primary paths, the page carries no navigation entry as the owner decided, and the NG-9 tension was recorded as a PRD open question rather than resolved, exactly as the intake instructed.
  - why — Additive slice: one new route, one new read model, no existing production file changed. The inversion reads correctly by identifier with stable ordering, tests assert real outcomes at both levels, and four clean approvals cite coordinates that resolve. A glance at the read model confirms it.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- No request input crosses the new boundary: SpecialtyController's only handler parameter is the framework-supplied Model (SpecialtyController.java:39-40, '@GetMapping("/specialties.html")' / 'public String showSpecialtyDirectory(Model model)'). A grep -F sweep of the vet package for '@ModelAttribute', '@RequestBody', '@RequestParam', '@PathVariable', 'InitBinder' returned only the pre-existing VetController.java:45 '@RequestParam(defaultValue = "1") int page', so the new endpoint binds no persisted type and the mass-assignment row of docs/security-principles.md is not engaged.
- Data access is a fixed JPQL string with no request-derived value: SpecialtyRepository.java:32 '@Query("SELECT specialty FROM Specialty specialty ORDER BY specialty.name")', annotated '@Transactional(readOnly = true)' (line 31) and exposing no write method, matching PetTypeRepository's shape. No concatenation, no parameter.
- Output escaping stays on the framework default. Every value in src/main/resources/templates/vets/specialtyList.html renders through th:text ('${entry.specialty.name}' line 20, '${veterinarian.firstName + \u0027 \u0027 + veterinarian.lastName}' line 23); the file contains no th:utext and no Thymeleaf preprocessing '__${...}__' expression (read in full, 30 lines). The menu argument passed to the layout fragment is the literal 'specialties' (line 4), not a model value, so the fragment's preprocessed th:href="@{__${link}__}" (fragments/layout.html:31) is still fed only literals from the call sites.
- No new dependency and no build change: 'git status --porcelain build.gradle gradle*' returned empty, so the dependency-policy checks in docs/system-design.md are not engaged by this change. OWASP Dependency-Check is not configured in build.gradle (plugins block lists java, checkstyle, jacoco, spring boot 4.1.1, dependency-management, native, cyclonedx, javaformat, nohttp), so no NVD match ran in this review — that check is not run, not clean.
- No credential, token, or unsafe randomness added: a case-insensitive grep -E over the three new main sources and both new test sources for 'password secret token apikey api_key System.out System.err Random(' returned no match. No logging statement is added at all.
- No shell, file, deserialization, or resource-path surface added: grep over the vet package for 'Runtime', 'ProcessBuilder', 'exec(', 'FileWriter', 'FileOutputStream', '/tmp/', 'JsonTypeInfo', 'enableDefaultTyping' returned no match. SpecialtyDirectory is a pure in-memory record built from the two repository results (SpecialtyDirectory.java:47-53) with no I/O.
- The new read-only endpoint discloses nothing beyond the existing baseline: specialty names and veterinarian full names are already served by GET /vets.html and the GET /vets JSON resource (VetController.java:44, 64-70). Result size is bounded by table cardinality, not by caller input, matching the pre-existing unpaged findAll() at VetController.java:70 — no new unbounded-allocation path under attacker control.

**code-quality-reviewer**

- Design placement matches the design-block and ADR: SpecialtyDirectory.of is a pure static factory holding the veterinarian-to-specialty inversion, and SpecialtyController (src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java:39-45) only delegates to the repositories and the factory, holding no business rule, per architecture-principles.md Pattern Catalog's Web controller row and docs/system-design.md:82's Cross-entity page assembly entry
- Identity-based matching risk called out in the design-block is implemented and tested: SpecialtyDirectory.holdersBySpecialtyIdentifier keys on Specialty::getId (SpecialtyDirectory.java:53-61), and SpecialtyDirectoryTests covers both a copy sharing an id (theSpecialtyDirectoryShouldMatchVeterinariansToSpecialtiesByIdentifier, line 118) and two specialties sharing a stored name (theSpecialtyDirectoryShouldKeepApartSpecialtiesSharingAStoredName, line 128)
- Vocabulary matches docs/ubiquitous-language.md: prose/tests use 'veterinarian', code and page text use the accepted short form 'Vet' (grep of ubiquitous-language.md:50, 58); no coined synonym for Specialty or Veterinarian introduced
- Construction follows the Pattern Catalog's value-object rule: SpecialtyDirectory and its nested Entry are records with compact constructors performing List.copyOf defensive copies (SpecialtyDirectory.java:34-36, 68-70), one static entry point (of), no builder, no test-only construction path
- No hard-coded page text: specialties, name, vets, none keys already exist in all eleven message bundles (verified by grep -c across src/main/resources/messages/messages*.properties, each non-en bundle returns 4; messages_en.properties is intentionally empty by pre-existing convention, falling back to the default bundle)
- Naming follows docs/architecture-principles.md § Naming: SpecialtyRepository (Repository suffix), SpecialtyController (Controller suffix prefixed by the noun it serves) comply; no prohibited suffix (Manager/Helper/Utility/Handler/Processor/Base/Info/Data) appears
- checkFormat passes clean (./gradlew checkFormat)
- conventions-map comment sweep: every added comment block is a purpose-explaining Javadoc with no restated signature, no requirement ids, and no handoff vocabulary (python3 scripts/grading.py conventions-map output for all 5 changed code files)
- No-link acceptance criterion is proven by a file-walking test (SpecialtyControllerTests.theSpecialtyDirectoryShouldBeLinkedFromNoPage, line 106) following the I18nPropertiesSyncTest precedent named in the design-block

**test-reviewer**

- SpecialtyDirectoryTests exercises the inversion rule as a pure unit with no framework context, matching the design doc's assignment of the rule below the boundary (SpecialtyDirectory is a static factory over List/Collection, no Spring context in the test)
- SpecialtyControllerTests uses hand-written stand-ins (StoredSpecialties, StoredVeterinarians) implementing the real repository interfaces rather than Mockito, per design-block's explicit instruction not to copy VetControllerTests' @MockitoBean (docs/testing-principles.md Mocking Policy: hand-written doubles preferred, mock framework a last resort); MockMvc is the one sanctioned mock for the web boundary
- Identity-matching risk named in the design-block (BaseEntity has no equals/hashCode override) is directly covered: theSpecialtyDirectoryShouldMatchVeterinariansToSpecialtiesByIdentifier (distinct Specialty instance, same id) and theSpecialtyDirectoryShouldKeepApartSpecialtiesSharingAStoredName (two Specialty rows sharing a name) both in SpecialtyDirectoryTests.java
- All 6 declared test names and all 5 PRD acceptance-criteria bullets for REQ-VET-003 are present, verified via python3 scripts/grading.py coverage-map --feature REQ-VET-003 (6 of 6 declared tests present; the 5 listed 'Veterinarian directory' edge cases affecting REQ-VET-003 -- stable specialty order, unheld specialty still listed, empty clinic, stable holder order -- each map to a test; the one 'Known defect' edge case is a pre-existing unrelated route)
- theSpecialtyDirectoryShouldBeLinkedFromNoPage (SpecialtyControllerTests.java:106-110) walks all of src/main/resources/templates and asserts no line contains both 'href' and '/specialties.html'; verified against src/main/resources/templates/fragments/layout.html:41,46,51,57 where all four menu entries are hardcoded literal th:replace calls (no dynamic href list), so the static text-walk test has no dynamic-list blind spot for this codebase
- Assertions use whole-object comparison (containsExactly(entryFor(...)) building real SpecialtyDirectory.Entry records) rather than field-by-field or captor chains, per testing-principles.md's whole-object comparison rule
- Three-tier data naming followed: SOME_FIRST_NAME/SOME_LAST_NAME for irrelevant values, EARLIER_/LATER_ prefixes naming the ordering role for the one test that needs distinguishable names, no bare mystery literals
- ./gradlew test passed for the full suite including SpecialtyDirectoryTests and SpecialtyControllerTests (BUILD SUCCESSFUL)

**doc-reviewer**

- prd.md § Veterinarian directory (lines 122-140) stays behavioral: no code identifiers, no mechanism, matches the boundary-rules.md what/how litmus test
- docs/adr/2026-09-17-read-model-for-cross-entity-pages.md carries Requirements: REQ-VET-003 in Implementation and uses em-dashes in both References entries (lines 38-39), matching adr-template
- system-design.md § Contracts (lines 82-84, 105-111) states the read-model and unlinked-page invariants in prose plus source pointers, no field/parameter tables, consistent with the existing rows' abstraction level
- every cross-reference added resolves: adr/README.md row points at the new ADR file (confirmed present via ls), the ADR's system-design.md#contracts and 2026-07-31-feature-package-organization.md links resolve (file exists, heading present), and system-design.md's adr/2026-09-17-read-model-for-cross-entity-pages.md link resolves
- REQ-VET-003 appears in both prd.md (anchor req-vet-003, line 122) and system-design.md Contracts table (Specialty, VetRepository, SpecialtyRepository, SpecialtyDirectory, SpecialtyController rows), satisfying the system-design-ID-must-exist-in-prd coherence check
- no prohibited-word or wordy-phrase hits in the new prose (checked simply/obviously/clearly/easy/easily/very/just/leverage/utilize/seamless/robust/powerful/comprehensive via grep -iE against all three changed docs, no match)

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 1 | opus-5 | $3.73 | 11m 16s | 97% |
| `agent-team:system-design-expert` | 1 | opus-5 | $1.80 | 4m 56s | 94% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.01 | 3m 2s | 91% |
| `(parent)` | 1 | opus-5 | $0.93 | 25m 10s | 94% |
| `agent-team:change-grader` | 1 | opus-5 | $0.76 | 2m 5s | 85% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.51 | 1m 2s | 85% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.39 | 2m 1s | 94% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.38 | 1m 34s | 93% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.33 | 1m 52s | 88% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.73 | 11m 16s | 97% |
| `agent-team:system-design-expert` | opus-5 | $1.80 | 4m 56s | 94% |
| `agent-team:product-requirements-expert` | opus-5 | $1.01 | 3m 2s | 91% |
| `(parent)` | opus-5 | $0.93 | 25m 10s | 94% |
| `agent-team:change-grader` | opus-5 | $0.76 | 2m 5s | 85% |
| `agent-team:security-reviewer` | opus-5 | $0.51 | 1m 2s | 85% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.39 | 2m 1s | 94% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.38 | 1m 34s | 93% |
| `agent-team:test-reviewer` | sonnet-5 | $0.33 | 1m 52s | 88% |

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
