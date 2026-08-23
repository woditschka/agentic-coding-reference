# specialty-directory r1 — v0.1.1

Specialty directory page (feature) · started 2026-08-22T17:52:52+00:00 · exec `claude-dev` · status **complete**

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
| 3 (±1) | 4 (±0) | 4 (±1) | 4 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.57. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 3 · doc-fit 4

> SpecialtyController lands in the vet package, is package-private with constructor injection, and adds no repository (ADR justifies deriving from cached findAll); SpecialtyView is immutable via List.copyOf. The pure grouping/sorting in directory() is unit-testable yet sits in the controller and is exercised only through MockMvc, widening the pyramid gap. Tests use behavior names, a hand-written InMemoryVetRepository instead of a mock framework, and cover empty roster, tie-break, and the no-specialty vet; but arrangement hides in @BeforeEach (shared fixture), store() silently clears rather than adds, and model().attributeDoesNotExist("totalPages") asserts another controller's detail. specialtyList.html references #{specialties} with no message bundle entry added and no rendering test, so it likely renders ??specialties??. PRD, contracts table, and ADR index all move; SpecialtyView is absent from the contracts table.

**Sample 2** — design-fit 3 · test-quality 4 · maintainability 4 · doc-fit 4

> SpecialtyController fits the vet package with constructor injection and reuses VetRepository, but directory() puts grouping, full-name formatting and ordering in the controller — pure logic the checklist says must not land there and that the ADR merely notes ('imposed in the handler'); a stateless domain service is a sanctioned unused pattern. SpecialtyView matches no catalog pattern and the ADR does not cover it, nor does the contracts table list it. Tests are strong: behavior names, four phases, a hand-written InMemoryVetRepository instead of Mockito, empty-roster and tie-break cases. Weaknesses: expectations are bare literals (containsExactly("dentistry", "radiology", "surgery")) rather than derived or named; attributeDoesNotExist("totalPages") tests an implementation detail; store() silently clears, so setup()'s roster vanishes; all coverage sits at the web slice.

**Sample 3** — design-fit 3 · test-quality 4 · maintainability 4 · doc-fit 4

> Placement, package-private visibility, constructor injection and the immutable SpecialtyView record fit well, but SpecialtyController.directory() puts the grouping and stable-ordering rule in the controller — the checklist forbids new rules there, and the sanctioned Domain service needs no ADR; the ADR records the choice without justifying the departure, and SpecialtyView matches no catalog pattern. Because the rule sits in a private controller method, all six tests boot MockMvc where a unit was possible. Tests are otherwise strong: behavior names, hand-written InMemoryVetRepository over Mockito, aVet factory, whole-object assertions, empty and tie-break cases; dings are bare literals ("radiology", "James"), store() that silently clears, and the attributeDoesNotExist("totalPages") absence check. Docs move well; SpecialtyView is missing from the contracts table.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $10.03 | 28m | 19 | 89% | 8 file(s) +339/−0 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.49 | 1m 14s | 84% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPC-001 — Specialty directory lists each specialty with the veterinarians holding it

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (1) | **✔** |
| **test** | ✎ (5) | **✔** |
| **security** | **✔** | · |
| **doc** | ✎ (3) | **✔** |

- ◇ **prd-entry** Specialty directory lists each specialty with the veterinarians holding it · (prd-expert) · ***◷ 30s***
- ◈ **design-block** **new** · (design) · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 10m***
  - ▲ **build ✓ clean** · build · test · format · check
- ✔ **review security** · **approved** · ***◷ 40s***
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 5m***
  - [clarify] `SpecialtyControllerTests.java:46-65` SpecialtyControllerTests uses @MockitoBean on VetRepository and Mockito BDD-style given() stubs. CLAUDE.md and the code-quality-review checklist state no mocks and no Mockito. The identical pattern exists in VetControllerTests (grep-confirmed), making this consistent-with-codebase, but the no-mocks principle predates both. Whether @WebMvcTest + @MockitoBean is an accepted narrow exception for MVC slice tests — or whether the slice tests should be replaced with full-context integration tests — is a test-design question the test-reviewer should rule on.
- ✎ **review test** · **changes_requested** · (5 findings) · ***◷ 2m***
  - **[blocked]** `SpecialtyControllerTests.java:46-47` @MockitoBean on VetRepository stubs an internal Spring Data JPA interface in a new test file. The testing brief (§ Mocking Policy) states new tests must prefer real implementations; a framework stub is a conscious exception only when neither a real implementation nor a hand-written double fits. VetRepository can be served by the real H2 in-memory database via @SpringBootTest, making the exception unjustified for this new class. The existing VetControllerTests.java uses the same pattern but is grandfathered; SpecialtyControllerTests is not.
  - [autofix] `SpecialtyControllerTests.java:80,87,94` All four test method names are missing the required the prefix. The testing brief (§ Test Naming) specifies the school as the{Subject}Should{Outcome}. Methods should be theSpecialtyDirectoryShouldListEverySpecialtyByStoredName, theSpecialtyDirectoryShouldShowHoldersByFullNameGivenNameFirst, theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage, and theSpecialtyDirectoryShouldOmitVeterinariansHoldingNoSpecialty.
    - fix: Rename each method by prepending the: theSpecialtyDirectoryShouldListEverySpecialtyByStoredName, theSpecialtyDirectoryShouldShowHoldersByFullNameGivenNameFirst, theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage, theSpecialtyDirectoryShouldOmitVeterinariansHoldingNoSpecialty.
  - **[blocked]** `SpecialtyControllerTests.java:62-66` No test covers the empty-vet-list boundary: when findAll() returns an empty list the page should render with zero specialty rows without error. The testing brief (§ Boundary Testing) requires an empty-input case. Without it a NullPointerException or template rendering error on an empty collection would go undetected.
  - **[blocked]** `SpecialtyControllerTests.java:62-66` No test exercises the holder tie-break ordering (lastName then firstName). The setup has no two vets sharing the same last name, so a regression from lastName+firstName ordering to lastName-only sorting would leave all existing tests passing. Add two holders with the same last name to one specialty in the setup and assert their relative order to pin the tiebreak. PRD edge case 1 requires stable order.
  - [autofix] `SpecialtyControllerTests.java:94-101` specialtyDirectoryShouldRenderAllSpecialtiesOnOnePage fires two HTTP requests in one test body (mockMvc.perform at line 95, then renderDirectory() at line 101) and asserts two unrelated concerns: absence of the pagination model attribute and the specialty count. This is two acts in one test, violating the four-phase structure. The count assertion also uses a bare literal 3 rather than a value derived from the setup data. Recommended fix: assert only attributeDoesNotExist(totalPages) in this test; the three-specialty count is already pinned by containsExactly in specialtyDirectoryShouldListEverySpecialtyByStoredName.
- ✎ **review doc** · **changes_requested** · (3 findings) · ***◷ 1m***
  - **[blocked]** `prd.md#req-spc-001` REQ-SPC-001 section in the PRD has no Design Rationale link to the new ADR. The prd-authoring skill states that Design Rationale is mandatory whenever an ADR records the decision behind the requirement. ADR 2026-08-22-specialty-directory-derived-from-veterinarians.md records the source-of-truth choice (derive from veterinarians vs. read the specialties store) for REQ-SPC-001, but no **Design Rationale:** reference appears in the requirement section. Comparable requirements with ADRs carry this link (e.g., REQ-PET-001). Add: **Design Rationale:** See [ADR: Specialty Directory Derived From Veterinarians](adr/2026-08-22-specialty-directory-derived-from-veterinarians.md) to the REQ-SPC-001 section.
  - **[blocked]** `system-design.md#contracts` REQ-SPC-001 is implemented (build-pass recorded) but no SpecialtyController row exists in the system-design.md Contracts table. The design-block record explicitly deferred this update to post-implementation (doc-sync follow-up). The doc-sync maintenance rules require system-design.md to be updated when a feature is added. A reader following the Contracts table cannot discover the new controller or the requirement it implements. system-design-expert should add a SpecialtyController row implementing REQ-SPC-001, with a note that the specialty directory is derived from the vet aggregate rather than a SpecialtyRepository, back-linked to ADR 2026-08-22-specialty-directory-derived-from-veterinarians.md.
  - [autofix] `2026-08-22-specialty-directory-derived` The Consequences section references system-design.md Open Question 5 as plain text rather than a markdown link. Cross-reference rules require all cross-references to use full paths with anchors.
    - fix: ([system-design.md § Open Questions](../system-design.md#open-questions-from-the-survey))
- ↻ **implement** (implementer) ← code-quality, test · (6 findings)
- ↻ **fix prd-expert** ← doc · (3 findings)
- ◇ **prd-entry** Specialty directory lists each specialty with the veterinarians holding it · (prd-expert) · ***◷ 1m***
- ↻ **fix design** ← doc · (3 findings)
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 0s***
- ▲ **build-pass** 18:17
- ↻ **fix doc** ← doc · (3 findings)
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 2m***
- ◆ **grade CLEAR** · add read-only specialty directory derived from veterinarians
  - blast_radius — **clear** — Purely additive (zero deletions): two new prod files plus a template in the vet package, one test file, and four doc updates. No sensitive paths, no shared code touched, one new read-only GET endpoint.
  - semantic_surprise — **clear** — Diff does exactly what described. TreeMap gives alphabetical specialty order, holders sorted lastName-then-firstName and rendered firstName-lastName; vets with no specialty never enter the inner loop so they are omitted; empty roster yields empty list. No inverted operator, boundary, or hidden behavior found.
  - test_adequacy — **clear** — Six tests assert real outcomes (containsExactly, full SpecialtyView equality) and cover the empty-roster and same-last-name tie-break boundaries the first-round test review demanded; a lastName-only regression would fail the tie-break test. Hand-written in-memory double, no Mockito.
  - reviewer_hedging — **clear** — All four reviewers approve with empty findings in the final round. Round-1 changes_requested items (Mockito, missing boundaries, PRD/system-design links) were all resolved and re-approved cleanly; no lingering caveat, escalate, or unresolved bar_clause remains.
  - scope_deviation — **clear** — Stays within the requirement surface. The primary-paths divergence from file_targets (no SpecialtyRepository, new SpecialtyController) is a documented design decision resolving the PRD-flagged source-of-truth open question, recorded in an ADR. build_retries=0, consultations=0, one design revision that is the deferred doc-sync.
  - why — Contained, purely additive read-only page whose code matches its description exactly; the boundary logic (omission, alphabetical and tie-break ordering) is directly pinned by real tests, and all four reviewers approved cleanly after resolving round-1 findings. Confirm and merge; a fast read of SpecialtyController.directory() is sufficient.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- No user input reaches SpecialtyController: fixed /specialties.html GET mapping with a Model-only handler, no request params or path variables to inject through
- All template output rendered via th:text (Thymeleaf auto-escaping); no th:utext and no user-controlled SpEL, so no stored/reflected XSS on specialty names or holder names
- Data source is the cached VetRepository.findAll() read path; SpecialtyView is an immutable record with a defensive List.copyOf, no state mutation and no serialization sink
- No new data exposure: specialty names and veterinarian full names are already public on the existing vet list page; no PII or credentials surfaced
- No dependencies added or changed by this slice; no new supply-chain surface

**code-quality-reviewer**

- SpecialtyController is package-private and uses constructor injection without @Autowired, mirroring VetController exactly
- SpecialtyView is a correctly shaped immutable record with a defensive List.copyOf() in its compact constructor and no mutable state
- TreeMap keying on specialty name gives free alphabetical ordering without an explicit sort step; the Comparator for holders by last-then-first name is named and scoped correctly
- directory() is a pure query method under 20 lines; holdersBySpecialtyName is a descriptive local variable name
- @GetMapping path /specialties.html matches the acceptance criterion; the model attribute name specialties and the view name specialties/specialtyList are consistent
- specialtyList.html reuses existing message keys #{specialties}, #{name}, #{vets} — no new i18n keys introduced, mitigating the REQ-LANG-002 build risk named in the design-block
- Test names follow the BDD should-convention; aVet() is a readable factory method; @SuppressWarnings(unchecked) is scoped precisely to the one method that requires it
- The format check task (checkJavaFormat) is not present in this Gradle build — verified by ./gradlew tasks — so no format findings; build-pass record confirms the check gate passed

**test-reviewer**

- All four PRD acceptance criteria have dedicated test cases with targeted assertions
- Specialty ordering verified via containsExactly with alphabetical expectation, pinning the TreeMap sort key
- Holder full-name format verified with a concrete SpecialtyView record comparison confirming given-name-first layout
- The omit-no-specialty-holder criterion is verified via flatExtracting and doesNotContain — a regression adding James Carter to the directory would fail the test
- URL reachability confirmed: every test performs GET /specialties.html and expects status 200
- 100% line coverage on SpecialtyController, SpecialtyView, and Specialty
- aVet() factory method used throughout — construction is not scattered as raw constructor calls
- AssertJ fluent assertions used correctly throughout: containsExactly, contains, flatExtracting, doesNotContain, hasSize, attributeDoesNotExist
- No phase comments or narration comments in test bodies

**doc-reviewer**

- REQ-SPC-001 HTML anchor present and correctly placed
- PRD section is behavioral: no Java code, no implementation constructs, no rationale prose
- Done when bullets map directly to acceptance criteria in the prd-entry record
- Edge case 2 correctly notes the navigation non-commitment without leaking implementation
- ADR structure follows the template: Context, Options Considered, Decision, Consequences, Implementation, References all present
- ADR Implementation section carries **Requirements:** REQ-SPC-001
- ADR References section uses em-dashes throughout
- ADR is written in present tense
- ADR README index entry is correctly placed and links to the new file
- ADR cross-references to system-design.md#contracts and both linked ADR files resolve
- Open question embedded in REQ-SPC-001 is a product data-semantics question, not rationale prose — placement is acceptable

**doc-reviewer**

- Finding 1 resolved: docs/prd.md line 151 carries the inline **ADR:** link to adr/2026-08-22-specialty-directory-derived-from-veterinarians.md, matching the REQ-PET-001 lightweight convention; mandatory-ADR-reference rule is satisfied
- Finding 2 resolved: docs/system-design.md Contracts table now has a SpecialtyController row (REQ-SPC-001) at line 107 and a current-state note at line 82 that the directory derives from the vet aggregate rather than a SpecialtyRepository, back-linked to the ADR
- Finding 3 resolved: docs/adr/2026-08-22-specialty-directory-derived-from-veterinarians.md line 24 cross-reference to system-design.md Open Questions is now a markdown link with full path and anchor

**code-quality-reviewer**

- Prior finding resolved: @MockitoBean removed; InMemoryVetRepository is a hand-written static nested double implementing VetRepository directly, registered via @Import — no Mockito in imports or usage
- store(Vet...) clears and repopulates the backing list; @BeforeEach resets state between tests; the double is correctly scoped as a singleton under @WebMvcTest control
- findAll() returns List.copyOf(vets) — defensive copy consistent with SpecialtyView compact constructor pattern in production code
- findAll(Pageable) throws UnsupportedOperationException with an explanatory message documenting the intentional gap; no silent swallow
- All six test methods carry the- prefix: theSpecialtyDirectoryShouldListEverySpecialtyByStoredName, theSpecialtyDirectoryShouldShowHoldersByFullNameGivenNameFirst, theSpecialtyDirectoryShouldOrderTiedHoldersByGivenName, theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage, theSpecialtyDirectoryShouldRenderNoRowsGivenAnEmptyRoster, theSpecialtyDirectoryShouldOmitVeterinariansHoldingNoSpecialty
- theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage now asserts only attributeDoesNotExist(totalPages) — the two-act split finding is resolved
- Empty-roster boundary test added: vets.store() with no args clears the list, assertThat(directory).isEmpty() is the correct assertion
- Tie-break test added: two holders with the same last name Leary in one specialty, containsExactly in insertion-indifferent order via contains(new SpecialtyView(..., List.of(Anna Leary, Helen Leary))) pins the firstName tiebreak
- @SuppressWarnings(unchecked) remains scoped precisely to renderDirectory(); aVet() factory remains the sole construction site
- Javadoc on InMemoryVetRepository explains its purpose in terms a future reader can act on — no agent-addressed comments

**test-reviewer**

- Finding 1 resolved: @MockitoBean replaced by hand-written InMemoryVetRepository static nested class implementing VetRepository, backed by a mutable List, registered via @Import. No Mockito imports in the file. The store(Vet...) method gives each test full control over the roster. This satisfies the Mocking Policy (testing-principles.md § Mocking Policy: prefer hand-written simple implementations); the WebMvcTest/@MockMvc stack is the one sanctioned framework boundary stand-in per the brief.
- Finding 2 resolved: all six test methods carry the required the prefix — theSpecialtyDirectoryShouldListEverySpecialtyByStoredName, theSpecialtyDirectoryShouldShowHoldersByFullNameGivenNameFirst, theSpecialtyDirectoryShouldOrderTiedHoldersByGivenName, theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage, theSpecialtyDirectoryShouldRenderNoRowsGivenAnEmptyRoster, theSpecialtyDirectoryShouldOmitVeterinariansHoldingNoSpecialty — consistent with the BDD the{Subject}Should{Outcome} school.
- Finding 3 resolved: theSpecialtyDirectoryShouldRenderNoRowsGivenAnEmptyRoster calls vets.store() (empty) and asserts assertThat(directory).isEmpty(). A regression that throws NPE or returns a non-empty model on an empty roster fails this test.
- Finding 4 resolved: theSpecialtyDirectoryShouldOrderTiedHoldersByGivenName stores Helen Leary then Anna Leary under radiology and asserts containsExactly ordering [Anna Leary, Helen Leary]. A regression from lastName+firstName sort to lastName-only sort would leave the order nondeterministic and fail this assertion.
- Finding 5 resolved: theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage asserts only model().attributeDoesNotExist(totalPages) — single concern, no bare literal 3, no second HTTP request.
- InMemoryVetRepository.findAll(Pageable) throws UnsupportedOperationException with a descriptive message, documenting the no-paging contract at the seam rather than silently returning null.
- Six tests pass: 6/6, 0 failures, 0 skipped (XML report verified).
- AssertJ fluent assertions used throughout; aVet() factory method covers all construction; no phase comments.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $3.07 | 9m 56s | 94% |
| `spring-boot-claude:system-design-expert` | 2 | opus-4-8 | $1.97 | 5m 59s | 85% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $1.27 | 3m 28s | 81% |
| `(parent)` | 1 | opus-4-8 | $1.10 | 28m 33s | 91% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $0.90 | 5m 55s | 90% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $0.65 | 4m 31s | 86% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $0.57 | 3m 42s | 84% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $0.49 | 1m 14s | 84% |
| `spring-boot-claude:security-reviewer` | 1 | opus-4-8 | $0.40 | 40s | 82% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.09 | 12s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.89 | 6m 45s | 95% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.18 | 3m 10s | 92% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.15 | 4m 7s | 85% |
| `(parent)` | opus-4-8 | $1.10 | 28m 33s | 91% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $0.82 | 1m 52s | 86% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.77 | 2m 23s | 86% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.52 | 3m 45s | 90% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.50 | 1m 5s | 71% |
| `spring-boot-claude:change-grader` | opus-4-8 | $0.49 | 1m 14s | 84% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.47 | 3m 51s | 88% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.40 | 40s | 82% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.38 | 2m 10s | 91% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.34 | 2m 33s | 86% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.23 | 1m 9s | 81% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.18 | 40s | 80% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.09 | 12s | 50% |

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

- plugin `spring-boot-claude` at `v0.1.1` (tag)
- model requested `claude-opus-4-8`; models used: opus-4-8 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
