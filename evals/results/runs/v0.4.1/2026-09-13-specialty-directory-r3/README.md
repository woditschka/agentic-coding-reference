# specialty-directory r3 — v0.4.1

Specialty directory page (feature) · started 2026-09-13T00:35:59+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±1) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.96. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Placement is right: SpecialtyController is a thin binding-free controller, the join lives in an immutable record (SpecialtyHolders.of, with List.copyOf in the compact constructor), both new types are package-scoped except the record whose public visibility is justified by template reflection, and the runtime hint is registered. Two小 frictions: the catalog says one Repository per aggregate root, and Specialty is a lookup value held by Vet, so SpecialtyRepository is an unremarked deviation; SpecialtyHolders is not a canonical-vocabulary noun. Tests are BDD-named, factory-built, mock-framework-free (hand-written InMemory*Repository), and split unit/web sensibly, but createASpecialty/createAVet are duplicated across both test classes and specialtyDirectoryOn's indexOf-plus-XPath table slicing is brittle infrastructure. prd.md and system-design.md are updated completely, with open questions recorded.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Layering is sound. SpecialtyController.showSpecialtyList only binds and delegates, and the matching rule lives in the SpecialtyHolders record, whose static of()/holdsOf() can be unit-tested without the framework. There is one repository per root, and the names follow the catalog. A minor cost: every Vet is loaded and matched in memory rather than queried. Tests follow the the{Subject}Should{Outcome} naming, use hand-written InMemory*Repository doubles, keep construction behind factories and use named constants. The weak spots are the fragile substring-plus-XML parse in specialtyDirectoryOn, a second doesNotContain assertion, and no test for the empty case. Docs are thorough: the PRD adds REQ-VET-003 with its open questions, and system-design updates the package tree, the invariants and the contract rows.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The pairing logic sits in the immutable record  SpecialtyHolders.of , not in the controller.  showSpecialtyList  only delegates to it, and the unit tests cover it without booting the framework. The new  SpecialtyRepository  follows the existing  VetRepository  style, and the Javadoc names the template as the caller that needs  SpecialtyHolders  to be public. Tests use BDD names, factories and hand-written in-memory repositories instead of a mock framework. However, the Spring-bean repositories are shared mutable fixtures reset through  holdOnly . The test also pulls the table out with substring slicing plus XPath, and it reads the message bundles from the relative path  src/main/resources/messages , both of which are brittle. The docs are updated throughout:  REQ-VET-003 , its Done-when bullets, the Context text, the package tree, the contract rows and the open questions.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $9.26 | 27m | 4 | 92% | 10 file(s) +676/−8 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.71 | 1m 41s | 77% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

1 review round · 1 build-pass · grade **SCRUTINIZE**

| reviewer | R1 |
| --- | --- |
| **code-quality** | **✔** |
| **test** | **✔** |
| **security** | **✔** |
| **doc** | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **minor** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 12m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 11s***
- ✔ **review test** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ◆ **grade SCRUTINIZE** · add read-only specialty directory page
  - blast_radius — **skim** — The change is additive and stays in one module: three new vet-package types, one new template, a one-line reflection hint in PetClinicRuntimeHints, and doc rows. No sensitive paths, and no existing behavior is edited. The one new unauthenticated route, GET /specialties.html, shows the same names /vets.html already exposes, and layout.html is untouched.
  - semantic_surprise — **skim** — Reading the hunks turned up nothing unexpected. SpecialtyHolders.holds matches with Objects.equals on the ids, not == or instance equality, and it never mutates the cached vet collection because Vet.getSpecialties returns a sorted copy. Vet.specialties is EAGER and Specialty has no lazy fields, so the template is safe with open-in-view=false. Every value renders through th:text. The one theoretical edge, null ids matching each other, cannot arise from persisted rows.
  - test_adequacy — **skim** — The tests check real outcomes. The controller tests parse the rendered table as strict XML and compare whole specialty-to-holders maps, including an ampersand name that would break the parse if escaping failed. SpecialtyHoldersTests catches the design's main risk by using a separately built specialty with id 1000, beyond the Integer cache. The hint test uses RuntimeHintsPredicates. Minor gap: no test runs SpecialtyRepository.findAll or the page against the real database.
  - reviewer_hedging — **scrutinize** — All four planned reviewers approved with no findings. But the security-reviewer's file:line citations do not match the files they name: SpecialtyController.java:170 is a 45-line file (the mapping is at line 38), SpecialtyRepository.java:279 is a 37-line file (line 35), PetClinicRuntimeHints.java:123 is actually line 39, and specialtyList.html:305/:308 are actually lines 18 and 21. The quoted snippets exist and the claims hold on my read, but that approval's evidence trail is broken. The Dependency-Check gap is a standing project gap and counts only as context.
  - scope_deviation — **skim** — The change stays inside the intake decisions and the design-block. It adds no navigation entry or link (layout.html unchanged), no write path, and no paging. The runtime-hint edit and its test are the mitigation the design-block named. The PRD and system-design provenance headers gain one clause each to cover requested requirements, which the prd-entry and design-block both record. There were zero consultations, design revisions, and build retries.
  - why — The code is additive, contained, and well tested, and my read found no behavioral surprise. The one flag is the security-reviewer's approval: none of its file:line citations resolve in the files it names. Spot-check the security claims directly (th:text only, no request binding, the new route) before merging. The rest can be skimmed.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Widening the exposed surface: the one new route, GET /specialties.html (SpecialtyController.java:170  @GetMapping("/specialties.html") ), is read-only and shows veterinarian names and specialty names. That data is already public unauthenticated through /vets.html and /vets (VetController.java  @GetMapping("/vets.html") ,  @GetMapping({ "/vets" }) ), so no new data class is exposed and management-endpoint exposure is unchanged.
- Input handling: the handler binds no request input.  grep -n -E '@ModelAttribute @RequestBody @RequestParam @PathVariable'  over SpecialtyController.java, SpecialtyHolders.java, SpecialtyRepository.java and specialtyList.html returns no match, so there is nothing to validate, no mass-assignment target, and no need for an @InitBinder disallow list. The only request parameter that reaches the page is the global  lang  locale switch, which is baseline.
- Data access: SpecialtyRepository.findAll() is a Spring Data derived query with no arguments (SpecialtyRepository.java:279  Collection\<Specialty> findAll() throws DataAccessException; ). No query text is concatenated.
- XSS: every value in specialtyList.html is rendered through escaping  th:text  (specialtyList.html:305  th:text="${entry.specialty.name}" , :308  th:text="${holder.firstName + ' ' + holder.lastName}" ). A grep for  th:utext  finds nothing in the template. SpecialtyControllerTests uses the stored name  Oral & Maxillofacial Surgery  so that a missing escape would fail the XML parse. The template adds no  __${...}__  preprocessing: the layout's existing  th:href="@{__${link}__}"  (layout.html:31) receives only literal menu links, and the new 'specialties' menu argument is only compared for equality (layout.html:31  ${active==menu ? ...} ).
- Unbounded allocation: the page loads every specialty and every vet with no paging, as the PRD requires ("Every specialty appears on the one page, with no paging"). The PRD does not state the size of these tables. Callers cannot grow them: no write path exists in the vet package ( grep -rn -F -e 'save(' src/main/java/.../vet/  and a grep for @Post/@Put/@Delete/@PatchMapping both return nothing). The existing /vets route already returns the full vet collection unpaged, and VetRepository.findAll() is @Cacheable("vets").
- Deserialization and native hints: PetClinicRuntimeHints.java:123 grants SpecialtyHolders only  MemberCategory.INVOKE_PUBLIC_METHODS  reflection, so Thymeleaf can read the record's accessors. It adds no Java-serialization hint, unlike the three existing entity hints. SpecialtyHolders defensively copies its holder list ( holders = List.copyOf(holders); ).
- Secrets and shell execution: a grep of the diff's added lines for password secret token apikey api_key credential private.?key returns no match. The only hits for the shell-execution pattern are the  RuntimeHints  class names in PetClinicRuntimeHints.java, which are not process execution. No logging, file I/O, or /tmp use was added. The test's XML parser enables FEATURE_SECURE_PROCESSING.
- Supply chain:  scripts/changeset.sh --name-only  lists no build.gradle, pom.xml, settings.gradle or .properties file, so no dependency changed. The resolved runtimeClasspath shows spring-boot 4.1.1, spring-webmvc 7.0.9, thymeleaf 3.1.5.RELEASE and tools.jackson.core:jackson-databind 3.1.5. OWASP Dependency-Check is not configured ( grep -n -F dependencyCheck build.gradle  returns nothing), so no NVD match ran in this review.

**doc-reviewer**

- docs/prd.md:123-141 adds REQ-VET-003 with an \<a id="req-vet-003">\</a> anchor, behavioral (no code/framework) narrative, three tagged Done-when bullets, and edge cases 3-5, matching the prd-entry acceptance criteria (handoff.jsonl:3)
- docs/prd.md:125 'requested 2026-09-13' provenance marker is consistent with the amended provenance header at docs/prd.md:8, not rationale prose or amendment-framing prose elsewhere in the document
- docs/system-design.md:100-107 Contracts rows for Vet, Specialty, VetRepository, SpecialtyRepository, SpecialtyHolders, SpecialtyController are one-line purpose+source+Implements rows with no field/parameter tables or constant literals, verified against src/main/java/.../vet/SpecialtyController.java, SpecialtyHolders.java, SpecialtyRepository.java (row text matches source Javadoc and behavior)
- docs/system-design.md:80 new invariant sentences (Specialty carries no back-association; SpecialtyHolders matches by identifier) match SpecialtyHolders.java's Objects.equals(held.getId(), specialty.getId()) matching and Specialty.java's unchanged mapping
- docs/prd.md#req-vet-003 -> docs/system-design.md#contracts anchor resolves (docs/system-design.md:72 '## Contracts')
- No new domain terms: docs/ubiquitous-language.md:50,52 Veterinarian/Specialty relationship definitions already cover 'holds'/'held by'; PRD and system-design usage matches canonical spelling
- grep -F 'specialties=' src/main/resources/messages/*.properties confirms the reused message key exists in all 11 bundles, matching the system-design claim of reusing existing keys (no new-key I18n gap)
- git diff docs/system-design.md and docs/prd.md contain no imperative (Do/Don't/Always/Never/Require) lines requiring an ADR back-link
- New PRD prose sentences (docs/prd.md:125) are all under 30 words with no prohibited words or hedging adjectives

**test-reviewer**

- All 7 declared test names present and passing (python3 scripts/grading.py coverage-map --feature REQ-VET-003 confirms 7 of 7); Done-when bullets and Veterinarian-directory edge cases 3-5 each have a matching test
- Test placement matches the design-block assignment: the specialty-to-holder pairing rule lives in SpecialtyHolders.of and is unit-tested in SpecialtyHoldersTests.java with no Spring context; the web-layer/i18n/rendering concerns are exercised at the boundary in SpecialtyControllerTests.java via @WebMvcTest+MockMvc (sanctioned per CLAUDE.md)
- Mocking policy followed exactly as the design-block specified: hand-written InMemorySpecialtyRepository/InMemoryVetRepository doubles supplied via @TestConfiguration, no @MockitoBean, no Mockito anywhere in the new tests (grep -F 'Mockito' over the two new test files: no matches)
- SpecialtyHoldersTests.java:36-42 pins the identity-matching risk the design-block called out (aSeparatelyLoadedCopyOf with IDENTIFIER_BEYOND_THE_INTEGER_CACHE=1000, comment at line 29-30 explaining why); confirms SpecialtyHolders.holds (SpecialtyHolders.java:51-53) matches by Objects.equals(id) not instance/==
- XSS coverage: SpecialtyControllerTests.java:73 STORED_NAME embeds an unescaped '&' and the assertion parses the response as strict XML (FEATURE_SECURE_PROCESSING true, SpecialtyControllerTests.java:230-232); an th:utext regression would break the XML parse, giving a real behavioral check rather than a source-text grep
- Native-image reflection hint pinned by PetClinicRuntimeHintsTests.java:30-38 using RuntimeHintsPredicates, matching the SpecialtyHolders.java:26 reflective-access note and PetClinicRuntimeHints.java:38-39
- Test Data Construction (testing-principles.md Factory Methods, applies to tests added from 2026-07-31 onward): both new test files wrap all production-entity construction in named factory methods (createASpecialty, createAVet, createSpecialtyHolders/holdersOf) rather than calling constructors/setters inline in test bodies, going beyond the pre-existing VetTests.java precedent (grep -F 'new Vet' src/test/java/.../VetTests.java: one direct call, pre-dating the rule)
- Three-tier data naming followed: RADIOLOGY/SURGERY/DENTISTRY/STORED_NAME/HOLDER_FIRST_NAME etc. are role-named (Tier 1); ANY_IDENTIFIER/ANY_SEQUENCE and the generated 'any specialty N' strings are irrelevant-value generators (Tier 2); no bare mystery literals found in either new test file
- AssertJ used throughout with whole-object/whole-map comparison (isEqualTo(Map.of(...)), containsExactly, containsOnlyKeys) rather than field-by-field picking; four-phase structure with blank-line separation and no phase comments in every test method reviewed
- ./gradlew test (scoped to *Specialty* and *PetClinicRuntimeHints*) passed with BUILD SUCCESSFUL; no skipped tests

**code-quality-reviewer**

- Pairing logic (SpecialtyHolders.of, holdersOf, holds) lives in the value object, not the controller — SpecialtyController.showSpecialtyList (src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java:38-43) only fetches from both repositories and delegates, matching the design-block's Web-controller placement rule and architecture-principles.md Layer respect (grep -F 'model.addAttribute' src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java confirms the one model call carries no branching).
- SpecialtyHolders (src/main/java/org/springframework/samples/petclinic/vet/SpecialtyHolders.java) is a record with a compact constructor defensive-copying holders via List.copyOf, matching architecture-principles.md Domain Core immutability/defensive-copy rule.
- Identifier-based matching (holds(), line 51-53) avoids the boxed-Integer/separate-load equality trap the design-block flagged; SpecialtyHoldersTests pins it with IDENTIFIER_BEYOND_THE_INTEGER_CACHE and a separately constructed copy (src/test/java/org/springframework/samples/petclinic/vet/SpecialtyHoldersTests.java:29-42).
- Template uses th:text exclusively (grep -F 'th:text' src/main/resources/templates/vets/specialtyList.html matches all four data-bearing lines, no th:utext present), avoiding unescaped markup output for stored names.
- Reused existing message keys (specialties, name, vets all present in src/main/resources/messages/messages.properties:21-23) rather than adding new ones, keeping I18nPropertiesSyncTest coverage intact.
- conventions-map shows every added comment block explains WHY (boxed-Integer cache boundary, separate-load re-boxing, markup-bearing test name, reflective template access) and none restates a signature or is a rename candidate.
- ./gradlew checkFormat passed clean on the change set.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 1 | opus-5 | $3.62 | 13m 1s | 96% |
| `agent-team:system-design-expert` | 1 | opus-5 | $1.60 | 5m 25s | 89% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.25 | 4m 6s | 88% |
| `(parent)` | 1 | opus-5 | $0.90 | 28m 12s | 95% |
| `agent-team:change-grader` | 1 | opus-5 | $0.71 | 1m 41s | 77% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.69 | 1m 12s | 85% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.45 | 1m 49s | 94% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.40 | 1m 32s | 93% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.35 | 1m 43s | 90% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.62 | 13m 1s | 96% |
| `agent-team:system-design-expert` | opus-5 | $1.60 | 5m 25s | 89% |
| `agent-team:product-requirements-expert` | opus-5 | $1.25 | 4m 6s | 88% |
| `(parent)` | opus-5 | $0.90 | 28m 12s | 95% |
| `agent-team:change-grader` | opus-5 | $0.71 | 1m 41s | 77% |
| `agent-team:security-reviewer` | opus-5 | $0.69 | 1m 12s | 85% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.45 | 1m 49s | 94% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.40 | 1m 32s | 93% |
| `agent-team:test-reviewer` | sonnet-5 | $0.35 | 1m 43s | 90% |

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
