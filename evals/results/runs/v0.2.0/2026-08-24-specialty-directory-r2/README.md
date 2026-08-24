# specialty-directory r2 — v0.2.0

Specialty directory page (feature) · started 2026-08-23T23:51:24+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±1) | 4 (±0) | 4 (±1) | 5 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.65. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Read model, repository, and controller sit in the right layers: SpecialtyController only reads, delegates to SpecialtyDirectory.of, and picks a view, and the catalog-gap type is covered by an ADR. Two frictions: SpecialtyRepository.findSpecialties already orders by name yet BY_SPECIALTY_NAME re-sorts, and extending JpaRepository exposes a write surface a read-only page never needs. SpecialtyDirectoryTests are exemplary — factories, whole-Entry comparisons, real objects. But theSpecialtyDirectoryShouldRenderEverySpecialtyOnOnePage asserts only view name and model attribute existence, implementation detail unrelated to its name and to the no-pagination criterion, and seeded names like "Linda Douglas" are bare literals. The template's #{specialties}/#{none} keys are added nowhere in the patch. Docs move everywhere they must: PRD, contracts table, Read models, ADR index, open questions.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 5 · doc-fit 4

> SpecialtyDirectory.java:60-88 keeps ordering and formatting in an immutable read model with defensive copies; SpecialtyController.java:38-43 only reads, delegates, selects a view — no rule in the controller, and the new type is justified by an ADR as the checklist requires. Unit tests use factories, BDD names, whole-Entry comparisons, and cover empty/unheld/stability edges. Two test weaknesses: SpecialtyControllerTests.java:92 promises "render every specialty on one page" but asserts only status, view name, and attribute existence — implementation detail; line 116 checks the specialty page does not link to itself, leaving the PRD's "no other page links here" criterion unverified. PRD, system-design contracts, Read models section, and ADR index all move; architecture-principles' In-force catalog and naming table still omit the read-model pattern now in use.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Clean layering: SpecialtyController only reads, delegates to SpecialtyDirectory.of, and selects a view; ordering and formatting sit in the immutable read model, with an ADR covering the new type as the catalog requires. Two frictions: SpecialtyRepository.findSpecialties() sorts by name in JPQL while BY_SPECIALTY_NAME re-sorts (duplicated responsibility, a repository ORDER BY change would be silently inert), and specialtyList.html introduces #{specialties}, #{vets}, #{none} with no message-bundle hunk in a project that ships eleven locales. Unit tests are exemplary — factories, derived whole-object Entry comparisons, no mocks. Controller tests are weaker: theSpecialtyDirectoryShouldRenderEverySpecialtyOnOnePage asserts only view name and attribute existence, and doesNotContain("/specialties.html\"") checks only the page itself. Docs (PRD, system-design, ADR index) are current.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $14.45 | 34m | 30 | 93% | 11 file(s) +559/−0 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.03 | 2m 32s | 89% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-002

0 review rounds · 0 build-passes · no grade yet


---

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (2) | **✔** |

- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 8m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 49s***
  - ▲ **build ✓ clean** · build · test · format · check · autofix-audit · handoff-log
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 57s***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `SpecialtyControllerTests.java:83` theSpecialtyDirectoryShouldListASpecialtyNoVeterinarianHolds constructs the entity directly (`Specialty unheldSpecialty = new Specialty(); unheldSpecialty.setName(...)`) instead of going through a factory method, breaking the Three-Tier/Factory-Methods rule in docs/testing-principles.md ("Test Data Construction > Factory Methods", applies to tests written from 2026-07-31 onward). The sibling unit-test file (SpecialtyDirectoryTests) already has the pattern to copy: createASpecialty(name). A sweep of both new test files found this as the only direct-construction instance.
    - fix: Add a private createASpecialty(String name) factory method to SpecialtyControllerTests (or a small shared test helper) and replace the direct `new Specialty()` + setter calls with it, mirroring SpecialtyDirectoryTests.createASpecialty.
  - [autofix] `SpecialtyControllerTests.java:45,89` NO_HOLDERS_CELL asserts on a literal HTML fragment (`\<span>none\</span>`) taken from the rendered response body. This couples the test to the template's exact markup shape (tag choice, absence of attributes, whitespace) rather than to the acceptance behavior ("a specialty no vet holds is shown as held by no one"). A template change that keeps the same visible text but alters markup (e.g. adds a css class, or Thymeleaf renders self-closing) breaks this test without any behavior regression -- an implementation-coupled rather than behavior-coupled assertion, contrary to testing-principles.md "Fluent Assertions > Use the most direct assertion available".
    - fix: Assert on the localized message text appearing in the row for the unheld specialty (e.g. via the message key's resolved value, or an HTML-aware query such as Jsoup/xpath scoped to the row) instead of matching a raw HTML string.
- ✎ **review doc** · **changes_requested** · (2 findings) · ***◷ 3m***
  - **[blocked]** `prd.md:137` The Specialty directory paragraph states the literal route '/specialties.html' in PRD prose: "It is reachable only at its own address, /specialties.html: no navigation entry and no link from any other page is part of this capability." This is mechanism, not behavior — the litmus test in the prd-authoring skill ("would it change when switching to another language?") is met: an HTTP route mapping is exactly the kind of fact that changes with the web framework. The bounded, testable claim is already carried behaviorally by the 'Done when' bullet ('given any other page of the system, when it is rendered, then it carries no link to the specialty directory') and by the Open Question on a visible entry point — neither needs the literal string. Nowhere in system-design.md is the concrete route documented either (the Contracts row for SpecialtyController says only 'from its own route'), so the literal address currently lives only in the PRD, the one document forbidden from carrying mechanism. Rewrite the sentence to state the behavior only (reachable solely by direct navigation, no advertised entry point) and drop the literal path; the path itself needs no restatement in system-design.md, since PRD boundary violations are never autofix-eligible on docs/prd.md (document-writing skill's review-checks.md, Autofix on the PRD Path, condition 3), this routes to product-requirements-expert rather than being applied as an autofix.
  - [autofix] `prd.md:149` The new 'Specialty directory' capability section (docs/prd.md:133-149) is the only capability section in the document with no **Design:** or **ADR:** link, even though this slice minted both: docs/system-design.md#read-models plus three new Contracts rows realize the mechanism, and docs/adr/2026-08-23-read-models-for-non-entity-page-shapes.md records the decision to use a read model instead of an inverse JPA mapping or controller-side grouping. Every sibling section that defers mechanism or rationale carries the link (see the Veterinarian directory section immediately above, docs/prd.md:131: '**Design:** [system-design.md#contracts](system-design.md#contracts)'). Per the prd-authoring skill, both links are mandatory once the corresponding doc exists. Insert a link line after the Edge cases list (after docs/prd.md:149, before the blank line preceding '### Language').
    - fix: \**Design:** [system-design.md#read-models](system-design.md#read-models)  ·  **ADR:** [ADR: Read Models for Page Shapes](adr/2026-08-23-read-models-for-non-entity-page-shapes.md)
- ↻ **implement** (implementer) ← doc · (2 findings)
- ↻ **fix prd-expert** ← doc · (2 findings)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 1m***
- ▲ **build-pass** 00:22 · build, test, format, check, autofix-audit, handoff-log
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved** · ***◷ 48s***
- ✔ **review security** · **approved** · ***◷ 40s***
- ✔ **review doc** · **approved** · ***◷ 10s***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ◆ **grade CLEAR** · add the read-only specialty directory page
  - blast_radius — **clear** — Purely additive: every one of the 11 files is added-only (0 deleted lines anywhere), the three new prod classes live in the one vet package, no existing production class, mapping, template, config, or dependency is touched, and the only edit to existing code is one appended test in ClinicServiceTests. The new GET /specialties.html route is unauthenticated like every other route in this app but exposes only specialty names and vet full names already published on /vets.html.
  - semantic_surprise — **clear** — Read all 17 hunks: SpecialtyDirectory.of inverts the Vet-owned association in memory by grouping vets under specialty id, sorts specialties by name then id and holders by last-then-first-then-id, formats First then Last, and copies both lists in the compact constructors, so no entity or live collection reaches the model and the cached vets list is never mutated. The controller is a two-line delegator, the repository is a parameterless ORDER BY query copying PetTypeRepository, and the template mirrors vetList.html's holder idiom with the layout menu argument specialties, which matches none of the fragment's menuItem values (home, owners, vets, error), so no nav entry lights up. Only latent oddity, unreachable in production: the comparators' getId tiebreaks would NPE on an unpersisted Specialty or Vet with a null id and a duplicate name, and null ids would collide as one map key - every instance here comes from a repository, so ids are always set.
  - test_adequacy — **clear** — 273 test lines against 211 prod lines, and the tests assert real outcomes rather than restating the implementation: SpecialtyDirectoryTests exercises all three PRD edge cases with real Specialty and Vet objects and whole-record containsExactly comparisons including the defensive-copy case, SpecialtyControllerTests renders through real templates against seeded H2 (the omitted vets James Carter and Sharon Jenkins genuinely hold no specialty in data.sql), and the ClinicServiceTests addition pins the repository ORDER BY separately from the in-memory sort. The unheld-specialty assertion was mutation-checked (deleting the none span fails it) after the fix round replaced its raw-markup literal with MessageSource-resolved wording. The one soft spot is the no-inbound-link test, which only inspects the specialty page's own output, but a grep across src/main templates confirms no page anywhere links to the route.
  - reviewer_hedging — **clear** — All four reviewers of the full high-risk battery approved on the second pass with zero findings and no escalate tag; the first pass's one critical bar_clause finding (a literal route in PRD prose) was fixed and re-approved by the same doc-reviewer with explicit reasoning, and the two fixable test findings were closed and re-verified by the test-reviewer. The product-requirements-expert's deliberate refusal to restate the route in system-design.md is a reasoned call the doc-reviewer independently endorsed, not a reservation left hanging.
  - scope_deviation — **clear** — The changed file set matches the design-block's primary_paths exactly, plus the docs it names and one test appended in the established ClinicServiceTests location; nothing outside the vet package moved. Zero consultations and zero build retries, and the single design revision was a record-only correction adding docs/adr/README.md to supporting_paths after the autofix audit flagged it - no design decision and no code changed. The three unanswered product questions were recorded as PRD open questions under the narrowest reading rather than being resolved unilaterally.
  - why — Additive new page in one package touching no existing production code, with the inversion, ordering, and formatting confined to an immutable read model that the tests exercise against real objects and real templates. Nothing surprising in the hunks. Confirm and merge; while reading, note that CLAUDE.md's Quality Gate names two Gradle tasks (formatJava, checkJavaFormat) that do not exist in this build.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Injection: SpecialtyRepository.findSpecialties() uses a fixed JPQL string constant in @Query with no parameters, no bind variables, and no concatenation. The route takes no request parameter, path variable, header, or form input at all, so no attacker-controlled value reaches the query builder. Swept the change set for dynamic query construction (createQuery/createNativeQuery/String concatenation into JPQL or SQL, @Query with SpEL fragments) - no other instance.
- XSS: every user-derived value in templates/vets/specialtyList.html is rendered through th:text, which HTML-escapes by default. Specialty names (${entry.name}), holder full names (${holder + ' '}), and the message-key headers are all escaped. Swept the new template for the unescaped-output class - no th:utext, no th:attr writing into a javascript: or on* handler, no th:inline='javascript' block, no th:href/th:src carrying a model value. Thymeleaf escaping is not disabled anywhere in the change set.
- Data escape into the model: the only model attribute is specialtyDirectory, a SpecialtyDirectory record holding List\<Entry> of (String name, List\<String> holders). No JPA entity, no proxy, and no repository reference reaches the model or the template, so no lazy traversal and no over-exposure of entity fields. Both record constructors defensively copy with List.copyOf, and SpecialtyDirectoryTests asserts the read model does not change when its source collections mutate.
- Serialization: SpecialtyController returns a view name with no @ResponseBody and no @RestController, so the read model is never serialized to JSON or XML - the page has no serialized representation to leak through content negotiation.
- /vets JSON graph unaffected: Specialty.java and Vet.java are not in the change set. Verified directly - Specialty still extends NamedEntity with no inverse mapping, and the sole @ManyToMany remains the owning side on Vet. No cycle was introduced into the graph the /vets route serializes, matching the ADR's stated rejection of option 1.
- Unauthenticated route: /specialties.html adds a read-only GET that inherits the application-wide absence of authentication already recorded in docs/system-design.md Threat Model row 1. It exposes no new data class - specialty names and veterinarian full names are already public on /vets.html and the /vets serialized route. No PII beyond what is already published, no identifiers, no operational detail. Pre-existing posture, not a new exposure.
- Secrets: swept the full change set for credential material by name and by shape (token, password, secret, key, credential, passwd, pwd, api, bearer, datasource). No hit in the added Java, template, or test sources. No property file, compose file, or manifest is touched.
- Supply chain: no dependency change. build.gradle, pom.xml, and gradle/ are unmodified in the change set, so no new coordinate, no version bump, and no new transitive surface enters the build. No CVE surface is introduced by this slice.

**code-quality-reviewer**

- SpecialtyController stays a thin delegator (constructor injection, one @GetMapping, no logic) matching VetController's shape.
- SpecialtyRepository.findSpecialties() mirrors PetTypeRepository.findPetTypes() exactly (name-ordered @Query) and is deliberately left uncached, per the design's caching risk note.
- SpecialtyDirectory and its nested Entry are true value objects: immutable records, List.copyOf on every constructed collection, static factory  of(...) , typed fields (no raw Object/Map\<String,Object> escaping), and no entity reference leaves the model.
- Ordering is owned entirely by the read model via two well-documented Comparator constants (BY_SPECIALTY_NAME, BY_HOLDER_NAME) with explicit id tiebreaks, keeping the three edge-case behaviors (empty holders, empty directory, stable order) provable with plain objects and no MVC or persistence stub.
- Template (specialtyList.html) follows vetList.html's existing holder-rendering idiom exactly, iterates only the prepared Entry list, and passes 'specialties' as the layout menu argument, which matches no existing menuItem (home, owners, vets, error) -- correctly leaving the Veterinarians nav unhighlighted.
- No new i18n keys were needed or added; #{specialties}, #{vets}, #{name}, #{none} are all pre-existing keys, avoiding any I18nPropertiesSyncTest risk.
- ./gradlew checkFormatMain checkFormatTest and compileJava/compileTestJava all pass clean; no formatting issues.
- The new ClinicServiceTests repository-ordering test for SpecialtyRepository follows the same convention already used there for PetTypeRepository, so the added coverage sits in an established location rather than a new one.

**test-reviewer**

- SpecialtyDirectoryTests correctly isolates the read-model as a pure unit (no I/O), matching the pyramid's unit layer, and every PRD-listed test_name for the read model is present and passing.
- Mocking policy fully honored: no Mockito anywhere in the new tests; SpecialtyControllerTests uses @SpringBootTest + real MockMvc + real seeded H2 data + real templates, which is stronger than the existing @MockitoBean-based VetControllerTests pattern it sits beside.
- All PRD edge cases are covered by dedicated tests with correct expectations verified against the actual seed data (src/main/resources/db/h2/data.sql): James Carter and Sharon Jenkins genuinely hold no specialty, so theSpecialtyDirectoryShouldOmitAVeterinarianHoldingNoSpecialty is not invented data.
- theSpecialtyDirectoryShouldOrderItsEntriesStably and the repository-ordering test in ClinicServiceTests correctly split the ordering guarantee across layers: the unit test proves the in-memory sort, the integration test proves the @Query ORDER BY -- not redundant.
- theSpecialtyDirectoryShouldCarryNoNavigationEntryOfItsOwn is a valid proxy for the PRD's "no other page links to it" criterion, because fragments/layout.html renders the identical, non-page-conditional nav list on every page that includes it -- verified by reading the fragment and vetList.html.
- jacocoTestReport shows 100% line coverage (0 missed) on SpecialtyDirectory, SpecialtyDirectory.Entry, and SpecialtyController, comfortably clearing the brief's 80% domain-package target.
- Whole-object AssertJ comparisons (containsExactly(new SpecialtyDirectory.Entry(...))) are used throughout SpecialtyDirectoryTests rather than field-by-field assertions, per testing-principles.md.
- ./gradlew test passed with all new and existing tests green.

**doc-reviewer**

- ADR is well-formed: Status, Context, Options Considered, Decision, Consequences, and an Implementation section carrying **Requirements:** REQ-VET-003, with em-dash-separated References that resolve (system-design.md#read-models, and the two prior ADRs it cites)
- docs/adr/README.md index row is correctly formatted, dated, and appended in chronological order, matching the ADR file's title and status
- docs/system-design.md's new Read models subsection and its three Contracts rows introduce no field/parameter tables or hardcoded literals, stay within the existing table's abstraction level, and every new REQ-VET-003 reference in system-design.md resolves against docs/prd.md
- REQ-VET-002's withdrawal in the Superseded list is unaffected and REQ-VET-003 does not reuse or overload the retired ID; the coincidence of adjacent numbers is not presented as a successor relationship
- No contradiction with NG-2: the new page is explicitly read-only and the PRD prose says so inline
- The three new Open Questions are correctly scoped as open (not smuggled in as settled non-goals or 'Done when' bullets) and are consistent with the prd-entry's stated non-goals

**test-reviewer**

- Finding 1 resolved: SpecialtyControllerTests now has a private createASpecialty(String) factory mirroring SpecialtyDirectoryTests.createASpecialty, replacing the direct  new Specialty()  + setter construction. Correctly omits an id since the entity is persisted via saveAndFlush and the id is database-generated.
- Finding 2 resolved: NO_HOLDERS_CELL's raw HTML literal is gone. The assertion now derives expected wording from the application's own MessageSource (messages.getMessage("none", null, READER_LOCALE)) and compares against readerTextOf(page) (tags stripped, whitespace collapsed) rather than a hardcoded markup string, decoupling the test from the template's tag shape while staying coupled to actual rendered behavior.
- Verified the adjacency claim against the template (src/main/resources/templates/vets/specialtyList.html): the name \<td> and the holders \<td> are immediate siblings in the same \<tr>, and for an empty holder list only the th:if=none span renders text in the second cell, so readerTextOf(page).contains(name + " " + noneText) is genuinely scoped to that row's rendering and not a coincidental substring match elsewhere on the page (specialty names are unique per row in the seed + test data).
- Reasoned through the claimed mutation check without re-executing it (reviewer is read-only, no template edits performed): deleting the th:if=none span would leave the holders cell empty for an unheld specialty, so readerTextOf would no longer contain "\<name> none" and the assertion would correctly fail -- the test is behavior-coupled, not vacuous.
- ./gradlew test --tests SpecialtyControllerTests passes cleanly (BUILD SUCCESSFUL), confirming the fix compiles and runs green against the real seeded H2 data and real templates.
- No new mocking, no new direct-construction, and no new markup-literal instances found sweeping the rest of the fix-delta test surface (SpecialtyDirectoryTests.java, ClinicServiceTests.java) for the same two classes.

**security-reviewer**

- Fix delta verified against the actual diff (scripts/changeset.sh --base-tree 78e75f0): only docs/prd.md and src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java changed. src/main/ and build.gradle are untouched in this delta, so no production, template, dependency, or configuration surface moved since the prior approval.
- No supply-chain change: build.gradle and the Gradle wrapper are absent from the delta, so the dependency set reviewed and approved on the prior pass still stands; no re-run of dependencyCheckAnalyze warranted.
- The markup-stripping helper readerTextOf (SpecialtyControllerTests.java:76) cannot mask an XSS regression. It is applied only to positive AssertJ contains() assertions whose expected values are ASCII literals with no markup (UNHELD_SPECIALTY_NAME 'oncology' and the MessageSource-resolved 'none' wording), so no injected tag can be stripped into a passing match. Stripping only loosens a positive containment assertion; it cannot convert a failing escaping check into a pass, and no assertion in the file depends on escaping semantics.
- Resolving the expected wording through the application MessageSource under an explicit Locale.ENGLISH, with the request locale pinned to the same value, removes a literal-HTML coupling without weakening the assertion: the build-pass record documents a mutation check (deleting the th:if none span) that fails the test.
- Output escaping in the rendered surface is unchanged and safe: src/main/resources/templates/vets/specialtyList.html uses th:text for every model-derived value (entry.name, holder) and message key; a sweep of src/main/resources/templates/ found no th:utext anywhere, so all user-derived content stays HTML-escaped by Thymeleaf.
- No secrets introduced: the delta adds no credential-shaped literal; the only new constants are a locale and a test specialty name.
- PRD change is prose only, restating REQ-VET-003 reachability and adding design/ADR cross-links; it introduces no requirement with security consequence and does not claim any security control the code lacks.

**doc-reviewer**

- Finding 1 (blocked, line 20) resolved: docs/prd.md:137 no longer states the literal route. The literal string '/specialties.html' does not appear anywhere in docs/prd.md, docs/system-design.md, or docs/adr/ (grep-verified) -- it lives only in source (SpecialtyController's @GetMapping) and three test assertions in SpecialtyControllerTests.java, including the no-link assertion, matching the product-requirements-expert's report.
- Declining to restate the route in system-design.md's Contracts row is correct and consistent with this reviewer's own prior finding, which explicitly said the path 'needs no restatement in system-design.md' (line 20). It also matches standing convention: the Constants section already states controllers' view-name routing details are deliberately excluded (system-design.md:70), and every Contracts row for a controller describes its route abstractly -- VetController 'from a second route', SpecialtyController 'from its own route', CrashController 'on a fixed route' -- with no literal path anywhere in the table. Losing the literal string from the docs is not a gap: the route is source-of-truth in the annotation and is pinned by three tests, so a prose copy would be a second source that drifts, exactly the risk the report names.
- Finding 2 (autofix, line 20) verified applied correctly: the Design/ADR link line sits after the Edge cases list at docs/prd.md:149, in the same position as every sibling capability section (e.g. the Veterinarian directory section immediately above). Both anchors resolve: system-design.md has a '### Read models' heading (system-design.md#read-models) and docs/adr/2026-08-23-read-models-for-non-entity-page-shapes.md exists on disk.
- The ubiquitous-language closure is sound: 'specialty directory' is a compound of the glossary-defined terms Specialty and Veterinarian, and the existing phrase 'veterinarian directory' is used throughout docs/prd.md and docs/system-design.md (e.g. NG-2, REQ-SYS-001, Open Questions) with no dedicated glossary entry of its own -- the new phrase gets the same treatment as its established sibling, not a deviation from it.
- Fix-delta scope (docs/prd.md and SpecialtyControllerTests.java per scripts/changeset.sh --base-tree) contains no further doc-relevant surface; no new instances of either finding's class found.

**code-quality-reviewer**

- createASpecialty(String) factory in SpecialtyControllerTests mirrors the established SpecialtyDirectoryTests.createASpecialty pattern (construction behind a factory method), correctly omitting the id since saveAndFlush generates it
- Replacing the literal-HTML NO_HOLDERS_CELL constant with MessageSource-resolved wording plus a markup-stripping readerTextOf helper decouples the assertion from template markup shape and asserts what a reader actually sees; both new helpers are small, single-purpose, and documented with Javadoc explaining intent
- Hand-rolling readerTextOf via regex rather than pulling in an HTML-parsing dependency (no Jsoup/HtmlUnit elsewhere in the test suite) is a reasonable, proportionate choice for a single test file's narrow need
- Import ordering (java.util.Locale in its own group before org.* imports) matches the convention already used in the sibling SpecialtyDirectoryTests.java in the same package

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $4.91 | 15m 4s | 96% |
| `agent-team:system-design-expert` | 2 | opus-5 | $2.13 | 6m 10s | 91% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $1.59 | 4m 7s | 91% |
| `(parent)` | 1 | opus-5 | $1.50 | 36m 35s | 95% |
| `agent-team:change-grader` | 1 | opus-5 | $1.03 | 2m 32s | 89% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.00 | 5m 6s | 94% |
| `agent-team:security-reviewer` | 2 | opus-5 | $0.94 | 1m 52s | 82% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.69 | 3m 55s | 92% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.54 | 2m 39s | 90% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.06 | 8s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.08 | 9m 10s | 97% |
| `(parent)` | opus-5 | $1.50 | 36m 35s | 95% |
| `agent-team:system-design-expert` | opus-5 | $1.47 | 4m 22s | 92% |
| `agent-team:feature-implementer` | opus-5 | $1.32 | 4m 33s | 94% |
| `agent-team:change-grader` | opus-5 | $1.03 | 2m 32s | 89% |
| `agent-team:product-requirements-expert` | opus-5 | $0.80 | 1m 51s | 91% |
| `agent-team:product-requirements-expert` | opus-5 | $0.79 | 2m 16s | 89% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.71 | 3m 55s | 94% |
| `agent-team:system-design-expert` | opus-5 | $0.66 | 1m 47s | 87% |
| `agent-team:security-reviewer` | opus-5 | $0.53 | 1m 5s | 83% |
| `agent-team:feature-implementer` | opus-5 | $0.51 | 1m 20s | 92% |
| `agent-team:test-reviewer` | sonnet-5 | $0.49 | 2m 51s | 94% |
| `agent-team:security-reviewer` | opus-5 | $0.41 | 47s | 81% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.32 | 1m 22s | 90% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.29 | 1m 10s | 94% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.22 | 1m 17s | 90% |
| `agent-team:test-reviewer` | sonnet-5 | $0.21 | 1m 4s | 87% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.06 | 8s | 50% |

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

- plugin `agent-team-spring-boot` at `v0.2.0` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
