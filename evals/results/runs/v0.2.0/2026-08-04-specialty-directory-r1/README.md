# specialty-directory r1 — v0.2.0

Specialty directory page (feature) · started 2026-08-04T11:46:00+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Feature request: the vet list answers "which specialties does this vet hold",
> but staff also ask the inverse — "which vets hold this specialty". One
> product decision comes with it, made here as the product owner: a read-only
> specialty view of the existing directory is in scope; managing veterinarians
> or specialties stays out of scope as before (non-goal NG-2 is unchanged).
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

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 4 (±0) | 4 (±0) | 4 (±0) | 4 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $1.00. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> SpecialtyDirectory keeps the rules out of the controller (VetController.showSpecialtyDirectory is a three-line delegate), the new SpecialtyRepository matches the Repository pattern, and an ADR covers the read-model type the catalog lacks — good layering. Unit tests are BDD-named, four-phase, and built behind specialty()/vet() factories. Gaps: specialtyList.html references #{specialties} but no message properties are added, so the label and REQ-LANG-002's 'page labels are wording' claim are unbacked; th:text="${vet.firstName + ' ' + vet.lastName + ' '}" concatenates with a trailing-space separator; static RADIOLOGY/SURGERY/DENTISTRY are shared mutable entity fixtures; controller assertions like not(containsString("/edit")) are brittle whole-page string checks; REQ-VET-003 has no narrative prose or the '(confirmed \<date>)' mark the edited provenance banner promises.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> SpecialtyDirectory keeps the pairing logic out of the controller and is justified by an ADR; VetController.showSpecialtyDirectory only binds and delegates. Docked one point because the new /specialties.html surface is bolted onto VetController rather than its own controller, against the catalog's one-surface-per-controller row. Unit tests are behavior-named, phase-separated, factory-built, and mock-free; the controller tests rely on brittle negative content assertions (not(containsString("\<form")), "page="), bundle two concerns in one method, and share mutable static fixtures RADIOLOGY/SURGERY/DENTISTRY against the stated rule. Template concatenation with a trailing space is a small rendering hack. Docs are broad (ADR, index, PRD, system-design, vocabulary), but REQ-VET-003 has no narrative prose and no "(confirmed \<date>)" mark the patch's own amended provenance note requires.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> The read model keeps the pairing out of the controller (VetController.showSpecialtyDirectory delegates to SpecialtyDirectory.of), SpecialtyRepository mirrors VetRepository, and the ADR justifies a type the catalog does not list. Gap: specialtyList.html uses #{specialties}/#{name} but no message keys are added, despite the PRD edge case the patch itself adds asserting labels follow REQ-LANG-002; the new PRD section also lacks the '(confirmed \<date>)' mark its own revised provenance banner promises. Unit tests are behavior-named and phase-structured, but ids (specialty(1,...), vet(7,...)) are mystery literals, RADIOLOGY/SURGERY are shared mutable entities, firstSurgery=10 sorts second, and the not(containsString("\<form"))/"page=" assertions pass trivially.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $15.49 | 36m | 46 | 91% | 11 file(s) +515/−11 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.92 | 2m 47s | 90% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Reader sees every specialty with the veterinarians holding it

2 review rounds · 2 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (4) | **✔** |

- ◇ **prd-entry** Reader sees every specialty with the veterinarians holding it · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 7m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · format · autofix-audit · handoff-log
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `VetControllerTests.java:112-129` Two prd.md "Done when" bullets for REQ-VET-003 are satisfied only by omission in production code (specialtyList.html carries no pagination block and no mutation form/link) and have no regression test guarding them: 'all of them appear on the one page, with no paging offered' and 'it offers no action to create, change, or remove a specialty or a veterinarian'. If a future change reintroduced a paging control or an edit/delete action, no test in this suite would fail. SpecialtyDirectoryTests covers the read-model side of 'all appear' (hasSameSizeAs) but nothing exercises the rendered page for absence of paging controls or mutation actions.
    - fix: Add assertions to the two new VetControllerTests route tests (or one more test) asserting the rendered /specialties.html body contains no pagination markers (e.g. no currentPage/totalPages model attributes, no page= link) and no create/edit/delete affordance (no \<form>, no href to a mutation route).
- ✎ **review doc** · **changes_requested** · (4 findings) · ***◷ 3m***
  - [autofix] `prd.md:137` The Specialty directory narrative's second sentence runs 37 words (documentation-standards Writing Standards: sentences under 30 words). Split it at the comma-and-conjunction joining the two clauses.
    - fix: Replace "for it, and under each specialty stand" with "for it. Under each specialty stand" on docs/prd.md:137.
  - [autofix] `2026-08-04-specialty-directory-read-mo` The ADR Decision paragraph's second sentence (on Option 1) runs 41 words, exceeding the 30-word sentence-length standard. Split it at the comma before the consequence clause.
    - fix: Replace "rendering, so the inverse side must be eager too" with "rendering. The inverse side must therefore be eager too" on docs/adr/2026-08-04-specialty-directory-read-model.md:21.
  - [autofix] `2026-08-04-specialty-directory-read-mo` The Option 3 sentence runs 32 words, exceeding the 30-word sentence-length standard. Split it at the comma before the second clause.
    - fix: Replace "does not admit, and leaves five" with "does not admit. It also leaves five" on docs/adr/2026-08-04-specialty-directory-read-model.md:23.
  - [autofix] `system-design.md:82` The new 'Invariants the rows cannot carry' paragraph's opening sentence on SpecialtyDirectory runs 40 words, exceeding the 30-word sentence-length standard. Split it at the colon.
    - fix: Replace "aggregate: it is built" with "aggregate. It is built" on docs/system-design.md:82.
- ↻ **implement** (implementer) ← test · (1 finding)
- ↻ **fix design** ← doc · (4 findings)
- ↻ **fix prd-expert** ← doc · (4 findings)
- ◇ **prd-entry** Reader sees every specialty with the veterinarians holding it · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **new** · (design) · supersedes L8 · ***◷ 1m***
- ▲ **build-pass** 12:17 · build, test, check, format, handoff-log, autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 40s***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 2m***
- ◆ **grade CLEAR** · add read-only specialty directory page
  - blast_radius — **clear** — Six code and template files, all inside the single vet feature package; the only edit to existing production code is VetController gaining a constructor parameter and one additive GET /specialties.html route, and no other site constructs that controller, so the two existing vet routes are untouched. No sensitive paths, no build or dependency change, no schema change.
  - semantic_surprise — **clear** — The diff does exactly what its description says. Pairing is keyed on specialty id rather than object identity, which is right because the two whole reads return distinct object graphs; both comparators fall through name to entity id so the order is total; the entries and holder lists are toList-immutable; the template escapes every dynamic value through th:text with no th:utext. The one behavioral asymmetry, the veterinarian read being cached while the specialty read is not, is stated in the ADR consequences rather than left latent.
  - test_adequacy — **clear** — Ten read-model unit tests drive real Vet and Specialty instances with no mocks and assert real outcomes, including the two rules that make this a specialty listing rather than a veterinarian listing, multi-specialty holders, namesake tiebreaks, and immutability. The two negative MockMvc guards are non-vacuous, as the test reviewer verified the asserted markers against the real paging block in vetList.html and the shared layout fragment. Residual gap is minor and matches the sibling page: no test exercises the new repository against seeded data, though the full-context boot test would fail on a repository that does not resolve.
  - reviewer_hedging — **clear** — All four reviewers on the dispatched roster returned approved with empty findings lists, no escalate tag and no bar_clause. Round two explicitly re-verified that production code is byte-identical to the round-one code-quality and security approvals, so the earlier approvals carry forward on unchanged code rather than being restated over a moved target.
  - scope_deviation — **clear** — Zero build retries and zero consultations. The two design revisions were not scope fights: the second design-block states its verdict and path set are unchanged and the revision only closed sentence-length findings on doc paths. Every shipped file appears in the design path set, and the reachability question the page leaves open is recorded as an explicit PRD open question rather than silently answered.
  - why — Read every hunk. A contained additive feature in one package: the read model's pairing, ordering and immutability are correct, tests exercise real objects and the negative guards were verified non-vacuous, and four reviewers approved with no findings. Confirm and merge; note the page has no navigation link by design.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyDirectory is a well-documented immutable read model: private constructor, static factory, unmodifiable lists (verified by SpecialtyDirectoryTests' structural-change-rejection test), single responsibility per method (holdersBySpecialtyId, holdersOf, of)
- Pairing by specialty id rather than object identity is correctly justified in a doc comment given the two independent read-only transactions return distinct object graphs and BaseEntity overrides no equals
- The Comparator\<Specialty,String>/\<Vet,String> type witnesses are a necessary, narrowly-scoped workaround for a real javac inference limitation with NamedEntity::getName/Person::getLastName method references, and Comparator.nullsLast(naturalOrder()) correctly guards the nullable Integer id; both are explained in adjacent Javadoc
- SpecialtyRepository mirrors VetRepository's shape (plain Spring Data Repository\<T,Integer>, @Transactional(readOnly = true), Javadoc style) - confirmed by reading both files side by side; no IDE symbol-resolution oracle was available this session so this consistency check rests on a file read/grep, the weaker basis per the code-quality-review skill
- VetController's new route stays a thin delegate (read both repositories, call the static factory, add one model attribute, return the view name), keeping controller logic out per the pattern catalog's Web controller row cited in the design-block and ADR
- specialtyList.html's space-separated th:each span for multiple veterinarians under one specialty mirrors the existing pattern in vetList.html:20 for multiple specialties under one vet - consistent with the established template convention, not a new defect
- SpecialtyDirectoryTests uses real Specialty/Vet instances (no mocks), BDD-style test names matching the PRD's acceptance criteria and edge cases, factory methods for object construction, and chained AssertJ assertions
- ./gradlew checkFormat passed clean on the changed files

**security-reviewer**

- No new attack surface from input: GET /specialties.html takes no path variable, query parameter, or request body, so the new route carries no user-controlled input into the application at all; the view name returned is the hardcoded literal 'vets/specialtyList', so there is no user-controlled view resolution or template-injection path.
- XSS: every value in src/main/resources/templates/vets/specialtyList.html renders through escaped th:text (specialty name, and the ${vet.firstName + ' ' + vet.lastName + ' '} concatenation); no th:utext, th:inline, th:src/th:href over model data, inline event handler, or __${...}__ preprocessing appears in the new template. A repo-wide sweep of src/main/resources/templates/ for th:utext returns nothing, so the class has no other instance. Thymeleaf's default escaping is not disabled, matching the system-design threat-model row for rendered user data.
- SQL injection: SpecialtyRepository exposes only the Spring Data derived findAll() with @Transactional(readOnly = true); no JPQL, no native query, no string concatenation. Data access stays inside the pattern the threat model records as the SQL-injection mitigation.
- Data exposure: the page discloses specialty names and veterinarian first/last names, exactly the data already published unauthenticated by /vets.html and /vets. It adds no PII class, no identifier, and no operational detail. The absence of authentication and CSRF configuration is the pre-existing project-wide posture recorded in system-design.md Security Context, not a regression introduced here; the route is read-only GET with no state change, so CSRF is not applicable to it.
- Secrets: a case-insensitive sweep of the full change set for token, password, secret, passwd, credential, api key, private key, bearer, and authorization returns no additions. No configuration, property file, or profile default is touched.
- Supply chain: scripts/changeset.sh --name-only lists no build.gradle, pom.xml, settings.gradle, or gradle wrapper change, and git status shows those paths clean, so the dependency set and framework versions are untouched by this change and no new CVE surface is introduced. The project configures no dependencyCheck/OWASP task, so no analyzer run applies to this diff.
- No deserialization, reflection, file I/O, process execution, outbound network call, or logging of user-derived data is introduced. SpecialtyDirectory is an in-memory immutable read model over two whole reads, pairing on entity id, with unmodifiable lists returned to the view.

**test-reviewer**

- SpecialtyDirectoryTests.java exercises the read model with real Vet/Specialty instances only, no Spring context, matching the ADR's stated goal and the brief's mocking policy (real objects first)
- All nine SpecialtyDirectoryTests cases use AssertJ fluent assertions, four-phase structure with blank-line separation, BDD the{Subject}Should{Outcome} naming, and named factory methods (specialty(), vet()) rather than raw constructors, with no mystery literals
- Edge case 1 (holder of several specialties) and edge case 2 (stable order for specialties and for veterinarians, including a same-name entity-id tiebreak) each have dedicated, correctly targeted tests: theSpecialtyDirectoryShouldNameAVeterinarianBeneathEverySpecialtyTheyHold, theSpecialtyDirectoryShouldOrderVeterinariansByLastThenFirstName, theSpecialtyDirectoryShouldOrderNamesakesByEntityId
- Both PRD 'a specialty no veterinarian holds' and 'a veterinarian holding no specialty' rules are covered at both the unit level (SpecialtyDirectoryTests) and the route level (VetControllerTests), matching the ADR's stated separation of concerns rather than duplicating logic through MockMvc
- Edge case 3 (stored specialty names render as data, not translated wording) is covered by the existing project-wide I18nPropertiesSyncTest, which scans the new template and would fail on a hard-coded literal or a missing translation key; the new template introduces no message key, so no new coverage gap was created
- VetControllerTests' new @MockitoBean SpecialtyRepository and MockMvc usage mirror the existing sanctioned pattern (MockMvc as the one sanctioned mock, Mockito tolerated for existing-style route tests) rather than introducing a new mocking departure
- ./gradlew test passed clean for both files (SpecialtyDirectoryTests, VetControllerTests), and the full gate reported in build-pass at line 10 was green

**doc-reviewer**

- REQ-VET-003 anchor, Done-when bullets, and edge cases are present and each edge case is covered by a numbered item
- PRD Specialty directory entry stays behavioral throughout — no mechanism, code reference, or rationale prose leaked in; the read-model rationale correctly lives only in the ADR
- Specialty directory and Veterinarian directory are both now defined in ubiquitous-language.md, consistent with their PRD usage, and neither collides with an existing entry
- The new ADR follows the template (Context/Options/Decision/Consequences/Implementation/References), uses em-dashes in the options list, and its Implementation section carries a Requirements: line
- docs/adr/README.md carries the one mechanical index row for the new ADR, matching the ADR's own date and title
- system-design.md's amended Contracts rows (Vet, Specialty, VetRepository, VetController) and new rows (SpecialtyRepository, SpecialtyDirectory) stay at purpose-plus-source-pointer abstraction, with no field/parameter tables or constant literals, and correctly extend the Implements column to REQ-VET-003
- All cross-references checked resolve: prd.md's system-design.md#contracts anchor, the ADR's relative links to system-design.md and the two sibling ADRs, and the REQ-VET-003 anchor itself
- The new open-question bullet on inbound navigation is scoped and behavioral, with no mechanism or rationale leaked

**security-reviewer**

- No production-code delta since the round-one approval: SpecialtyDirectory, SpecialtyRepository, VetController, and vets/specialtyList.html are byte-identical to the reviewed round-one state, so the round-one threat-model conclusions carry forward unchanged
- New GET /specialties.html takes no request parameter, no path variable, and no request body; there is no user-controlled input reaching the read model, the repositories, or the view
- Repository access stays on Spring Data derived queries (SpecialtyRepository.findAll, VetRepository.findAll) with no JPQL/SQL string construction, so no injection sink is introduced
- Template renders every dynamic value through Thymeleaf th:text, which HTML-escapes; no th:utext, no inline JavaScript, no unescaped attribute interpolation on the new page
- The two new regression tests are test-only surface and add no attack surface; the read-only assertion (no \<form>, no /new, /edit, /delete reference) is a net security gain, pinning the unauthenticated directory page as non-mutating so a later change cannot silently add a state-changing action
- No secrets in the delta: sweep for password/secret/token/api-key/credential across the whole change set returned no hits
- Supply chain unchanged: no build.gradle, dependency, or lockfile entry in the change set, so no new or upgraded dependency to verify against the NVD this round
- Doc-only edits to docs/prd.md, docs/system-design.md, and the ADR are sentence-length splits with no changed claim and no security-relevant content

**code-quality-reviewer**

- Re-review confirms production code is byte-identical to the round-1 approved state (SpecialtyDirectory.java, SpecialtyRepository.java, VetController.java, specialtyList.html unchanged in this pass's full diff against the pre-feature base); the only code delta this round is two new @Test methods in VetControllerTests.java addressing the round-1 test-reviewer autofix finding.
- The two new tests (theSpecialtyDirectoryPageShouldShowEverySpecialtyOnOnePageWithNoPagingOffered, theSpecialtyDirectoryPageShouldOfferNoActionToCreateChangeOrRemoveASpecialtyOrVeterinarian) each carry a short doc comment explaining the rule they guard, matching the file's existing convention for the two prior specialty-directory tests.
- model().attributeDoesNotExist("currentPage","totalPages","totalItems") asserts against the exact attribute names VetController.java:55-57 publishes for the paginated /vets.html route, so the assertion is grounded in the real sibling route rather than a guessed name.
- BDD the{Subject}Should{Outcome} naming, single chained MockMvc call per test (consistent with the file's existing route-test shape), and Hamcrest containsString/not matchers already established in this file (not a new AssertJ departure - MockMvc's andExpect takes a Matcher, not an AssertJ assertion) are all followed.
- ./gradlew checkFormat passed clean on the full change set, including the modified test file.
- docs/prd.md, docs/system-design.md, and the ADR sentence-length splits (lines 23-24) carry no claim change per their owning experts' notes; re-read confirms no new code reference, mechanism, or rationale leaked into the PRD, and the design-doc splits preserve the original meaning.

**test-reviewer**

- The round-one finding is resolved: VetControllerTests.java now carries two named regression guards, one per previously-unguarded 'Done when' bullet, rather than assertions bolted onto the existing route tests - theSpecialtyDirectoryPageShouldShowEverySpecialtyOnOnePageWithNoPagingOffered and theSpecialtyDirectoryPageShouldOfferNoActionToCreateChangeOrRemoveASpecialtyOrVeterinarian, each with a doc comment stating the rule it guards
- The paging guard's markers are independently verified against the real regression shape, not invented: vetList.html's actual paging block emits '/vets.html?page=__${i}__' (matching the asserted absence of the literal 'page=') and VetController.java:55-57 publishes exactly the three model attributes asserted absent (currentPage, totalPages, totalItems) - a reintroduced paging block on this page would trip the guard
- The mutation-affordance guard's markers (\<form, /new, /edit, /delete) are checked against fragments/layout.html, which the specialtyList.html page renders through: a repo-side grep for those four literals in layout.html returns nothing, so the not(containsString(...)) assertions are not vacuously true against shared chrome and would catch a mutation link added to either the page body or the shared navbar, matching the implementer's stated rationale for asserting against the full body
- Both new tests pass under ./gradlew test --tests VetControllerTests, and the full six-test class is green
- The two guards read the rendered HTML body directly via MockMvc content().string(...), keeping the sanctioned mock (MockMvc as HTTP transport) as the only mock in play, consistent with the brief's mocking policy
- Four-phase structure, AssertJ/Hamcrest idiomatic assertions, and BDD the{Subject}Should{Outcome} naming are consistent with the rest of the file and the brief's naming school

**doc-reviewer**

- All four round-1 autofix findings verified as correctly applied: docs/prd.md:137, docs/adr/2026-08-04-specialty-directory-read-model.md:21, and docs/system-design.md:82 match the proposed splits verbatim; each resulting sentence is under 30 words
- Deviation on docs/adr/2026-08-04-specialty-directory-read-model.md:23 verified correct: after the line-21 split, 'It' would nearest-antecedent to the pattern catalog's Web controller row rather than Option 3, so the applied 'Option 3 also leaves five' preserves the sentence's original claim where the proposed 'It also leaves five' would have inverted it
- Consequential edit beyond the original findings verified correct: the sentence following the line-21 split ('Option 1 also promotes a lookup value...') restores the pronoun's antecedent (Option 1) that the split pushed one sentence further away
- No new sentence-length or pronoun-ambiguity instances found sweeping the full doc diff (docs/prd.md, docs/adr/2026-08-04-specialty-directory-read-model.md, docs/adr/README.md, docs/system-design.md, docs/ubiquitous-language.md)
- The two edits beyond the four findings — the PRD provenance-note rewording and the 'companion page' sentence in Context — are legitimate scope for the new (confirmed 2026-08-04) requirement, not leaked mechanism or rationale; PRD boundary rules hold throughout
- All cross-references resolve: the ADR's links to system-design.md#contracts and to both sibling 2026-07-31 ADRs, and the docs/adr/README.md index row

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `(parent)` | 1 | opus-5 | $6.25 | 38m 19s | 96% |
| `agent-team:feature-implementer` | 3 | opus-5 | $6.23 | 13m 20s | 94% |
| `agent-team:system-design-expert` | 3 | opus-5 | $5.20 | 9m 7s | 90% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $3.54 | 5m 20s | 88% |
| `agent-team:security-reviewer` | 2 | opus-5 | $2.11 | 2m 28s | 86% |
| `agent-team:change-grader` | 1 | opus-5 | $1.92 | 2m 47s | 90% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.86 | 6m 13s | 88% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.63 | 4m 19s | 90% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $1.38 | 3m 22s | 85% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.12 | 6s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $6.25 | 38m 19s | 96% |
| `agent-team:feature-implementer` | opus-5 | $3.67 | 7m 59s | 96% |
| `agent-team:system-design-expert` | opus-5 | $2.33 | 4m 11s | 91% |
| `agent-team:change-grader` | opus-5 | $1.92 | 2m 47s | 90% |
| `agent-team:product-requirements-expert` | opus-5 | $1.80 | 2m 9s | 88% |
| `agent-team:feature-implementer` | opus-5 | $1.78 | 3m 40s | 92% |
| `agent-team:product-requirements-expert` | opus-5 | $1.74 | 3m 11s | 88% |
| `agent-team:system-design-expert` | opus-5 | $1.55 | 2m 16s | 87% |
| `agent-team:system-design-expert` | opus-5 | $1.32 | 2m 39s | 91% |
| `agent-team:security-reviewer` | opus-5 | $1.26 | 1m 41s | 88% |
| `agent-team:doc-reviewer` | sonnet-5 | $1.13 | 3m 36s | 85% |
| `agent-team:security-reviewer` | opus-5 | $0.85 | 46s | 81% |
| `agent-team:test-reviewer` | sonnet-5 | $0.84 | 2m 36s | 86% |
| `agent-team:test-reviewer` | sonnet-5 | $0.80 | 1m 42s | 92% |
| `agent-team:feature-implementer` | opus-5 | $0.78 | 1m 40s | 89% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.73 | 2m 36s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.72 | 1m 52s | 85% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.66 | 1m 29s | 86% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.12 | 6s | 0% |

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
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `9c6fd220a549ce32` · `2.1.220 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
