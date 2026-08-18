# specialty-directory r2 — v0.3.5

Specialty directory page (feature) · started 2026-08-17T21:20:21+00:00 · exec `claude-dev` · status **complete**

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
| 5 (±1) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $1.00. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> New types match the catalog:  SpecialtyRepository  mirrors  VetRepository 's narrow  Repository  base,  SpecialtyHolders  is an immutable record with  List.copyOf  defensive copy, and  SpecialtyController.showSpecialtyDirectory  only binds, delegates, and selects a view — no rule in the controller. Deduction:  GroupVeterinariansBySpecialty  is a domain service carrying  @Component  DI wiring, which the Domain Core row forbids. Tests are behavior-named ( theSpecialtyDirectoryShouldShowASpecialtyNobodyHoldsAsHeldByNone ), factory-built, branch-free, with a real grouping service in the slice; but  createASpecialty / createAVet  are duplicated verbatim across both test classes, and  @MockitoBean  repositories are a tolerated-not-encouraged stub. specialtyList.html references  #{specialties} / #{none}  with no bundle change visible;  containsString("none")  would pass even on a missing key. Docs are complete: ADR, PRD requirement plus open questions, contracts, vocabulary.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The grouping rule is lifted out of the controller into a stateless domain service (GroupVeterinariansBySpecialty.java:group), a sanctioned catalog pattern with a verb name; SpecialtyController is a thin bind-delegate-select adapter, SpecialtyHolders is an immutable record with a defensive List.copyOf, and SpecialtyRepository extends Repository to expose one read. Docs are unusually complete: ADR, ADR index, PRD requirement with open questions, system-design contracts/overview/implementation order, and the new Holder term. Tests are behavior-named, four-phase, factory-built, whole-object compared. Deductions: createASpecialty/createAVet are duplicated verbatim across both test classes instead of shared vocabulary; @MockitoBean stubs are used without justifying the exception; specialtyList.html introduces #{specialties}/#{none} keys with no message-bundle change visible, and containsString("none") would still pass on ??none_en??.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The read model sits where the catalog wants it:  SpecialtyController  only binds, delegates, and selects a view; the grouping rule lives in a stateless, framework-free  GroupVeterinariansBySpecialty  (verb-named domain service),  SpecialtyRepository  exposes one read, and  SpecialtyHolders  is an immutable record with a defensive  List.copyOf . Unit tests are BDD-named, four-phase, factory-built, with no mystery literals. Deductions:  createASpecialty / createAVet  are duplicated verbatim across both test files instead of shared vocabulary; the controller test reaches for  @MockitoBean  rather than a hand-written double;  not(containsString("specialties.html?page"))  and the self-link check are weak proxies.  specialtyList.html  introduces  #{specialties}  and  #{none}  but the patch adds no message-bundle entries, and  containsString("none")  would still pass on  ??none_en?? . Docs are current throughout: PRD, ADR + index, contracts, vocabulary, implementation order.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $17.95 | 42m | 38 | 91% | 12 file(s) +640/−5 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.48 | 3m 28s | 88% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPECIALTYDIRECTORY-001 — Reader sees every specialty with the veterinarians holding it

2 review rounds · 2 build-passes · **3 build-failures** · grade **CONCERN**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | **✔** | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (1) | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Reader sees every specialty with the veterinarians holding it · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 10m***
  - ▲ **build ✗ build failed** · retry 1
  - ▲ **build ✗ autofix-audit failed** · retry 2
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 54s***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain not verified against the NVD in this review: the project configures no OWASP Dependency-Check plugin (build.gradle declares java, checkstyle, jacoco, spring-boot 4.1.0, dependency-management 1.1.7, graalvm native 1.1.2, cyclonedx 3.2.4, javaformat 0.0.47) and this reviewer has no network access. The change adds no dependency, so the resolved set is unchanged from the last verified state; a human or CI still owns the periodic NVD match against Spring Boot 4.1.0 and its managed Jackson.
  - ▹ rec: Both reads are unpaginated full-table scans (findSpecialties plus the cached VetRepository.findAll), and holdersOf calls Vet.getSpecialties() once per (specialty, vet) pair, each call allocating a freshly sorted list - O(specialties x vets) allocations per request. Harmless at seed-data scale and not attacker-controlled (no request parameter influences the size), but worth a note if the directory ever serves a large clinic; /vets.html already paginates for the same reason.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [clarify] `system-design.md:108` The noun "holder" is used as canonical vocabulary in both prd.md ("A holder is named in full...", and the Done-when bullet "each holder is shown by first name then last name") and system-design.md ("the holder list is empty when nobody holds it"), but docs/ubiquitous-language.md defines only the verb relationship "held by" (Veterinarian and Specialty entries) and has no "holder" entry. The document-writing checklist requires every domain term used in prd.md and system-design.md to be defined in ubiquitous-language.md, or added there in the same change. This gap was already surfaced as an open item in the design-block's notes (line 11 of the handoff log) and deliberately left unresolved as "the product expert's call" without being carried into docs/prd.md's own Open Questions list, so a reader of the durable docs alone has no record that the term is unsettled.
- ✔ **review test** · **approved** · ***◷ 2m***
  - ▹ rec: src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java: no test pins Thymeleaf's default th:text escaping for a specialty or holder name containing HTML-significant characters (e.g. "\<script>"), even though the design's risk list names 'never th:utext' as the mitigation for output escaping. A rendered-and-escaped assertion would make that guarantee regression-proof rather than implicit in the template's current markup.
  - ▹ rec: src/test/java/org/springframework/samples/petclinic/vet/GroupVeterinariansBySpecialtyTests.java: theSpecialtyDirectoryShouldListTheHoldersOfASpecialtyInAStableOrder exercises the last-name/first-name tiebreak in BY_FULL_NAME, but no case exercises two veterinarians who share both first and last name, which is the case the comparator's id-based third key exists for. Worth one more case to lock in that determinism.
- ↻ **fix prd-expert** ← doc · (1 finding)
- ◇ **prd-entry** Reader sees every specialty with the veterinarians holding it · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **new** · (design) · supersedes L11 · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 4m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 41s***
  - ▹ rec: SpecialtyRepository.findSpecialties() already orders by name in JPQL (ORDER BY specialty.name), and GroupVeterinariansBySpecialty.group then re-sorts the same collection with BY_NAME (name then id). The re-sort is necessary for the id tiebreaker and for correctness independent of the repository's order, but a reader meeting both orderings back to back may wonder if one is redundant; a one-line comment on the @Query noting that the read model does its own (tie-broken) sort regardless would save that reader a round trip through both files.
- ✔ **review test** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain was not verified against the NVD in this review: no OWASP Dependency-Check plugin is configured in build.gradle and the reviewer has no network access. The change adds no dependency, so there is no new exposure, but the framework CVE check remains un-run rather than clean — close it in CI or by a human.
  - ▹ rec: The directory reads every specialty and every veterinarian per request with no paging (required by the PRD, recorded in the ADR). Veterinarians come from the existing cache; specialties are read uncached on every request. Bounded by the clinic roster today, so no availability finding, but it is the one growth-sensitive path the change adds.
- ✔ **review doc** · **approved** · ***◷ 1m***
- ◆ **grade CONCERN** · add read-only specialty directory page
  - blast_radius — **clear** — Twelve files in one module, and every production change is purely additive: four new classes, one new template, one new GET route. No existing production file, entity mapping, schema, dependency, or sensitive path is touched; the only modified files are five docs.
  - semantic_surprise — **clear** — Read every hunk. Grouping matches holders by stored id rather than name, both comparators carry an id tiebreak, the layout menu argument 'specialties' matches no nav item so no navigation entry appears, and all four message keys already exist in every locale bundle so no i18n gap opens. Behavior is exactly the described page; the only mismatch found is documentary, in the rationale.
  - test_adequacy — **clear** — Sixteen tests assert real outcomes: the unit suite pins every ordering, the held-by-none case, the omitted specialty-free vet, and two specialties stored under one name, while the MockMvc suite drives the real grouping service and checks Thymeleaf escaping of a script-tag name and the absence of any self-link. Weakest is the page-level held-by-none test matching the bare string 'none' anywhere in the response, but the unit test pins that boundary exactly.
  - reviewer_hedging — **concern** — All four dispatched reviewers approved with zero findings, but two parked recommendations reach the human here: the security reviewer states the framework CVE check is un-run rather than clean (no dependency scanner configured, no network) and asks CI or a human to close it, and flags the unpaged per-request read of every vet and specialty as the one growth-sensitive path the change adds; code-quality asks for a comment reconciling the JPQL ORDER BY with the read model's own re-sort.
  - scope_deviation — **clear** — The two design revisions and three build-failure records were process bookkeeping (an ADR index path missing from supporting_paths, then a doc-reviewer vocabulary round), not scope fights. The diff matches the PRD surface: no navigation entry, no inbound link, no schema or message-bundle change, and the three undecided product questions are recorded in the PRD rather than answered.
  - why — Code is additive and does exactly what the requirement describes; no existing production file changes. Two things want a human eye first: the security reviewer's parked supply-chain check, un-run rather than clean, and system-design.md line 8, which still calls post-survey statements a requirement not yet built - false once this ships.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- GroupVeterinariansBySpecialty is a stateless domain service with a total, tie-broken sort key on both axes (specialty by name then id, vet by last/first/id), matching the ADR's ordering guarantee and the architecture-principles domain-service naming rule (verb phrase, no prohibited suffix)
- SpecialtyHolders record has a compact constructor with null checks and List.copyOf defensive copy, satisfying the value-object rule
- SpecialtyController follows the read-delegate-return shape with constructor injection and no grouping logic leaking into the controller, as the design-block's risk mitigation required
- SpecialtyRepository correctly narrows to Repository\<Specialty,Integer> (read-only, no write surface) rather than JpaRepository, documented in its Javadoc, and mirrors the PetTypeRepository lookup-repository shape
- specialtyList.html reuses the vetList.html rendering idiom verbatim (first-then-last name concatenation, #{none} fallback) with no navigation entry added to layout.html, matching the design-block's integration point
- All visible strings route through message keys already present in messages.properties (specialties, name, vets, none); no new key introduced, so no bundle-sync risk
- checkFormat passes clean; naming, package placement, and Javadoc are consistent with sibling classes in the vet package

**security-reviewer**

- No request-derived input anywhere on the new surface: SpecialtyController.showSpecialtyDirectory takes only Model, declares no @RequestParam/@PathVariable/@ModelAttribute, and binds no command object, so the mass-assignment and identifier-tampering rows of the threat model have no reachable path here (no data binder needed, none omitted)
- Data access is a constant JPQL string with no parameters and no concatenation (SpecialtyRepository.findSpecialties), annotated @Transactional(readOnly = true); the injection-into-data-access control holds with no request-derived value reaching the query at all
- SpecialtyRepository extends Repository\<Specialty,Integer> rather than a CRUD base, exposing exactly one read and no write, mutating, or delete operation - least privilege at the persistence boundary
- Template output escaping stays on end to end: specialtyList.html uses only th:text and #{...} message expressions; a full grep of src/main/resources/templates for th:utext and Thymeleaf preprocessing (__${...}__) returns nothing, so the new page introduces neither an unescaped sink nor a template-expression evaluation of stored text. Vet and specialty names render through the default-escaping th:text path (holder.firstName/lastName concatenation is a Java string built inside the escaped expression, not markup injection)
- New GET /specialties.html exposes only data already public at /vets.html and /vets (specialty names, vet first/last names); it adds no mutating route, no actuator exposure, and no navigation entry, so the exposed surface is not widened beyond the baseline in docs/system-design.md#security-context
- No secrets, credentials, tokens, or connection strings added; grep of the change set for token/password/secret/key matches nothing, and no configuration or property file is touched
- No file, process, or network operations introduced: no Files/FileWriter/Runtime/ProcessBuilder/exec and no /tmp usage in the vet package; no deserialization surface, no XML/YAML/JSON parsing of untrusted bytes, no regex
- Concurrency-safe under singleton scope: GroupVeterinariansBySpecialty holds only static final Comparators and no mutable field; SpecialtyHolders is a record with null checks and a List.copyOf defensive copy, so entries handed to the view cannot be mutated by a caller
- No exception is caught, rethrown, or reworded on the new path, so no internal detail is added to the error page the security brief flags as rendering exception messages
- Supply chain unchanged: build.gradle and gradle.properties are not in the change set and no dependency, repository, or plugin is added, so the four dependency checks in system-design.md have nothing to clear

**doc-reviewer**

- PRD Specialty Directory section stays behavioral prose with no mechanism, no code-element names, and a bounded Done-when contract; the literal address /specialties.html is user-observable behavior, not implementation mechanism
- New ADR follows the template exactly: em-dash references, three options considered with rejection rationale, Consequences section, and an Implementation section carrying Requirements: REQ-SPECIALTYDIRECTORY-001
- docs/adr/README.md's new index row (date, title, link, status) matches the ADR file's H1, filename, and status exactly, verified against the file
- system-design.md's four new Contracts rows are prose purpose statements with no field/parameter enumeration, each correctly cites REQ-SPECIALTYDIRECTORY-001 and its source file, and the narrowed-to-Repository claim, the uncached-reads claim, and the no-navigation-entry claim all verified true against the source (SpecialtyRepository, SpecialtyController, layout.html menu values)
- All cross-references (PRD Design: links, ADR References section, ADR index links) resolve to existing anchors and files
- No new message keys or template text bypass the existing message bundle, matching both docs' claims

**test-reviewer**

- All six PRD acceptance-criteria test names present and behavior-accurate in both GroupVeterinariansBySpecialtyTests (pure unit, no I/O) and SpecialtyControllerTests (@WebMvcTest with the real GroupVeterinariansBySpecialty imported rather than mocked)
- Mocking stays within policy: only SpecialtyRepository and VetRepository (system-boundary JPA repositories) are @MockitoBean; the grouping domain service is real, and no verify(...) restates an outcome already covered by a state assertion
- Three-tier data naming followed throughout: ANY_FIRST_NAME/ANY_LAST_NAME for irrelevant values, named specialty/vet variables for meaningful ones (radiology, surgery, Helen Leary), zero mystery literals
- Construction wrapped behind factory methods (createASpecialty, createAVet, createHoldersOf) in both files; no raw production constructors called directly, consistent with the post-2026-07-31 rule
- Whole-object comparison used throughout (containsExactly(createHoldersOf(...))) rather than field-by-field picking, matching the 'Stop Re-Testing Other Units' principle
- BDD test naming (the{Subject}Should{Outcome}) applied consistently across both new files, correctly diverging from the older VetControllerTests convention it sits beside
- Deliberate edge-case coverage for the two design-flagged ordering risks: two specialties stored under one name stay two entries, and two holders sharing a last name are tie-broken by first name
- 100% instruction coverage on all four new/changed classes per jacocoTestReport (GroupVeterinariansBySpecialty, SpecialtyController, SpecialtyHolders, Specialty), comfortably clearing the 80% domain/core target
- ./gradlew test passes clean; no flaky or order-dependent tests observed

**code-quality-reviewer**

- GroupVeterinariansBySpecialty class Javadoc explains why inversion is needed (the Vet-to-Specialty association is mapped one way) and cites the ADR, giving a future reader the why, not just the what
- Both sort comparators (BY_NAME, BY_FULL_NAME) are documented in place with the reason for their stored-identity tiebreaker, directly addressing the two-specialties/two-vets-sharing-a-name risk called out in the design block
- SpecialtyController stays a thin adapter: two repository calls, one delegation to the grouping service, one model attribute, one view name — no grouping or sorting logic leaks into it
- SpecialtyHolders is a proper immutable value object: canonical constructor validates non-null, defensive List.copyOf() on the holders list
- SpecialtyRepository extends the narrow Repository interface (not a CRUD base), exposing exactly the one read the directory needs, mirroring PetTypeRepository's shape as the design block specified
- specialtyList.html reuses the exact rendering idiom from vetList.html (first-name-then-last-name concatenation, #{none} fallback for an empty list) instead of inventing a new one, and passes a menu argument ('specialties') that matches no entry in fragments/layout.html, satisfying the no-navigation-entry acceptance criterion without touching the shared layout
- All visible strings route through Thymeleaf message keys (#{specialties}, #{name}, #{vets}, #{none}); no hard-coded page text
- checkFormat passes with no violations on the changed Java files

**test-reviewer**

- GroupVeterinariansBySpecialtyTests covers every acceptance criterion as a pure unit test with no framework context (stable specialty order, stable holder order with identity tiebreak, held-by-none, omission of a specialty-free vet, empty-directory case, and two specialties sharing one stored name kept apart) — logic lives in the domain service so the bulk of coverage sits at the base of the pyramid per testing-principles.md
- SpecialtyControllerTests exercises the real GroupVeterinariansBySpecialty (@Import, not mocked) with @MockitoBean only on the two repositories at the persistence boundary and MockMvc as the sanctioned HTTP-transport double — no verify() restates a behavioral assertion
- Tests follow the the{Subject}Should{Outcome} naming school, four-phase structure with blank-line separation, AssertJ fluent assertions (containsExactly, flatExtracting, extracting), and the three-tier data naming convention (ANY_FIRST_NAME/ANY_LAST_NAME, createASpecialty/createAVet/createHoldersOf factories, zero mystery literals)
- Extra test beyond the PRD's named list adds real value: theSpecialtyDirectoryShouldRenderAStoredNameAsTextRatherThanMarkup verifies Thymeleaf output escaping for a specialty name and a holder name containing \<script> tags
- All nine SPECIALTYDIRECTORY-001 acceptance criteria map to a dedicated test in one of the two files; ./gradlew test passes cleanly with no new i18n keys introduced (page reuses existing specialties/name/vets/none keys), avoiding any I18nPropertiesSyncTest risk

**security-reviewer**

- No request-derived input anywhere in the new surface: GET /specialties.html takes no path variable, query parameter, or request body, so no boundary validation is owed and no mass-assignment binder is applicable (no command object is bound).
- Data access is a constant JPQL string in SpecialtyRepository.findSpecialties with no interpolation of any value; the repository extends Repository rather than a CRUD base, exposing one read and no write operation (least privilege).
- specialtyList.html renders every dynamic value through th:text, so Thymeleaf's default escaping applies to specialty names and holder names; the template contains no th:utext, no inlined [( )] output, no __${...}__ preprocessing, no inline JavaScript, and no remote resource or href.
- The template's escaping and 'none' fallback mirror the neighbouring vets/vetList.html implementation of the same concern, so no divergent second way to render user-derived text is introduced (pattern consistency).
- GroupVeterinariansBySpecialty is a stateless singleton with static final comparators and no mutable field, so the shared bean carries no per-request state; SpecialtyHolders defensively copies its holder list in the compact constructor.
- No new dependency, repository, or build configuration: build.gradle is outside the change set, so the change carries no supply-chain delta.
- No logging, no exception construction, no file or process operation, no serialization endpoint, and no credential-shaped literal in the change set; the added endpoint exposes only veterinarian and specialty names already published by /vets.html, so the exposed surface is not widened past the baseline in system-design.md#security-context.

**doc-reviewer**

- Round-1 clarify finding (line 21) on the undefined 'holder' term is fully resolved: docs/ubiquitous-language.md now carries a Holder entry (role, not a second kind of person, with Relationships and Avoid lines) and a dated naming-collision bullet separating the SpecialtyHolders code symbol from the domain plural
- docs/prd.md's Context vocabulary sentence now lists Holder, and the 'Is the vocabulary right?' answered question carries a dated note that the term joined afterward, so a reader of the durable docs alone finds the term settled with no dangling open item
- All cross-references resolve: prd.md#req-specialtydirectory-001 anchor present, both Design: links point at system-design.md#contracts (verified as a real heading), the ADR's References use the ADR-index-verified path and its system-design.md#open-questions-from-the-survey link resolves, and docs/adr/README.md's new row matches the ADR file's title, filename, and status exactly
- system-design.md's four new Contracts rows stay at purpose-and-source-pointer altitude with no field/parameter enumeration; the new Overview sentence and Invariants paragraph correctly describe the one-exception domain-service shape and the uncached-specialty/cached-vet asymmetry without transcribing code
- PRD stays behavioral: no mechanism, code-element name, or rationale prose; the literal address /specialties.html is user-observable behavior consistent with round 1's approved-aspect finding on the same text
- All new prose sentences across prd.md, system-design.md, and ubiquitous-language.md are under the 30-word standard
- Implementation Order table gained its REQ-SPECIALTYDIRECTORY-001 row with correct Depends On (REQ-VET-001, REQ-LANG-002), matching the prd-entry's dependencies field

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $10.18 | 17m 44s | 93% |
| `agent-team:system-design-expert` | 3 | opus-5 | $6.64 | 9m 11s | 89% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $4.25 | 6m 53s | 92% |
| `(parent)` | 1 | opus-5 | $3.87 | 45m 28s | 97% |
| `agent-team:change-grader` | 1 | opus-5 | $2.48 | 3m 28s | 88% |
| `agent-team:security-reviewer` | 2 | opus-5 | $2.15 | 2m 29s | 81% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.71 | 3m 34s | 93% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.71 | 3m 31s | 86% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $1.23 | 1m 54s | 88% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $7.11 | 11m 6s | 93% |
| `(parent)` | opus-5 | $3.87 | 45m 28s | 97% |
| `agent-team:system-design-expert` | opus-5 | $3.01 | 4m 44s | 91% |
| `agent-team:change-grader` | opus-5 | $2.48 | 3m 28s | 88% |
| `agent-team:product-requirements-expert` | opus-5 | $2.39 | 3m 46s | 94% |
| `agent-team:system-design-expert` | opus-5 | $2.34 | 2m 41s | 88% |
| `agent-team:feature-implementer` | opus-5 | $2.19 | 4m 45s | 94% |
| `agent-team:product-requirements-expert` | opus-5 | $1.86 | 3m 7s | 90% |
| `agent-team:system-design-expert` | opus-5 | $1.28 | 1m 45s | 85% |
| `agent-team:security-reviewer` | opus-5 | $1.10 | 1m 10s | 83% |
| `agent-team:doc-reviewer` | sonnet-5 | $1.05 | 2m 12s | 93% |
| `agent-team:security-reviewer` | opus-5 | $1.05 | 1m 19s | 79% |
| `agent-team:test-reviewer` | sonnet-5 | $1.02 | 2m 18s | 88% |
| `agent-team:feature-implementer` | opus-5 | $0.89 | 1m 52s | 93% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.69 | 1m 0s | 87% |
| `agent-team:test-reviewer` | sonnet-5 | $0.68 | 1m 12s | 83% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.66 | 1m 22s | 91% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.53 | 54s | 90% |

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

- plugin `agent-team-spring-boot` at `v0.3.5` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.233 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
