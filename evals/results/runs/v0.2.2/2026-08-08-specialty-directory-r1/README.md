# specialty-directory r1 — v0.2.2

Specialty directory page (feature) · started 2026-08-08T14:57:51+00:00 · exec `claude-dev` · status **complete**

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
| review attention (pipeline grade) | — |

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
| 4 (±1) | 4 (±0) | 4 (±1) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.72. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 3 · doc-fit 5

> Placement is strong:  SpecialtyDirectory.of  keeps grouping out of  SpecialtyController , which only binds, delegates and selects a view, so the recorded controller deviation does not grow; the record is immutable with  List.copyOf  defensive copies, and an ADR covers the read-model type the catalog lacks. But  specialtyDirectory.html  uses  #{specialties}  and  #{none}  while no message bundle is touched anywhere in the patch, against REQ-LANG-002 and the key-comparison test system-design.md names. Tests are behavior-named and add a genuine framework-free unit suite behind  VetFixtures , yet  new Specialty()  in theSpecialtyDirectoryShouldRefuseASpecialtyThatWasNeverStored bypasses the factory rule,  entries().get(2)  is index-based access, and the template scan hardcodes a working-directory-relative path. Documentation (PRD, NG-10, two ADRs, contracts, vocabulary) is current throughout.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyDirectory keeps assembly out of the controller as a pure, immutable record factory (SpecialtyDirectory.of), so SpecialtyController only binds, delegates, and selects a view — the Web controller rule holds and the pyramid gains a real unit test. Naming, package placement, and the uncached-repository choice all fit. Gap: specialtyDirectory.html introduces #{specialties} and #{none} yet no message bundle is touched, which risks REQ-LANG-002's 'no hard-coded or partly translated text' claim. Tests are behavior-named, factory-backed (VetFixtures), and assertion-rich, but theSpecialtyDirectoryShouldOrderSpecialtiesAndHoldersStably uses entries().get(2) index access, specialty(1,...) ids are bare literals, and TEMPLATE_DIR's relative path makes the NG-10 guard working-directory fragile. Docs (PRD, system-design, vocabulary, two ADRs, ADR index) are fully current.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyDirectory.of() lifts the inversion into an immutable, framework-free record (defensive List.copyOf, comparator constants), leaving SpecialtyController.showSpecialtyDirectory as bind-delegate-select with no rule — right layer, catalog-conformant naming, and an ADR for the new read-model precedent. Docs move completely: REQ-SPEC-001, NG-10, both ADRs plus index, system-design contracts/package-structure rows, ubiquitous-language, and two recorded open questions; no visible claim goes stale. Tests are behavior-named, phase-structured, and built on the new VetFixtures factories. Deductions: SpecialtyDirectoryTests asserts via entries().get(2), the index-based access the principles bar; SpecialtyControllerTests re-tests the unit through a booted context and casts the model attribute out of MvcResult; @MockitoBean stubs are taken as default; and the template adds #{none} with no bundle entry visible.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $14.06 | 39m | 33 | 91% | 13 file(s) +700/−4 |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPEC-001 — Staff can see which veterinarians hold a given specialty

2 review rounds · 2 build-passes · no grade yet

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (1) | **✔** |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (1) | ✎ (3) |

- ◇ **prd-entry** Staff can see which veterinarians hold a given specialty · (prd-expert) · ***◷ 4m***
- ◈ **design-block** **new** · (design) · ***◷ 5m***
- ◈ **design-block** **new** · (design) · supersedes L4
- ◆ **implement** (implementer) · ***◷ 11m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 1m***
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [autofix] `SpecialtyDirectory.java:50-56` The `of(...)` factory's Javadoc does not document that it throws `IllegalArgumentException` when a specialty in the `specialties` collection has a null id (see `entryFor`, line 77-80). A caller reading only the method's contract has no signal that an unsaved specialty aborts the whole call; the class-level Javadoc mentions the general read-model shape but not this specific failure mode either.
    - fix: Add an `@throws IllegalArgumentException` tag to the `of(...)` Javadoc describing that a specialty without a stored id fails the whole call.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 1m***
  - **[blocked]** `system-design.md:80` The Contracts read-model paragraph reads: "(designed 2026-08-08 for `REQ-SPEC-001`; the last three rows below are not yet in the working tree)". Both are now false: SpecialtyRepository.java, SpecialtyDirectory.java, and SpecialtyController.java exist in the working tree (build-pass shipped them), and the three Contracts rows for them are present at lines 111-113 of this same document. The parenthetical also uses the prohibited relative reference "below" (Structural Checks: No relative references). This is drift left over from the design-triage dispatch, which wrote the sentence before the code existed; a reader of system-design.md today is told code is missing when it is shipped. Not autofix-eligible: this is a coherence/factual-state finding, not a writing-standards or enumerated-structural fix, so it is never autofix-eligible on a design-doc path per the document-writing skill. Route to system-design-expert to reword the parenthetical to reflect current state (or drop it, since the rows now speak for themselves) without introducing a new relative reference.
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `SpecialtyControllerTests.java:135-150` The test body itself contains a Files.walk().filter().forEach() with a nested for-loop and an if-statement scanning template lines. testing-principles.md's Agent Decision Checklist item 4 ('Linearity: No branching or loops in the test body') and the Assertions section ('No branching in assertions... Use collection-aware assertions instead') both forbid this. The scan is legitimate (it is what makes the test able to fail — confirmed: it reads templates from disk and is not vacuous), but the iteration belongs in a helper, not inline in the test method.
    - fix: Extract the Files.walk/filter/forEach/for-loop into a private static method, e.g. `referencesToSpecialtyDirectory()` returning List\<String>, so the test body reduces to `List\<String> references = referencesToSpecialtyDirectory(); assertThat(references).isEmpty();` — straight-line, matching the pattern already used by readLines().
  - [autofix] `SpecialtyControllerTests.java:170-185` The private helpers `specialty(int id, String name)` and `vet(String firstName, String lastName, Specialty... specialties)` are byte-for-byte duplicated across the two test classes. testing-principles.md's Testing Vocabulary section calls for shared vocabulary extraction ('Extract shared test utilities into a common base class or utility module') and Agent Decision Checklist item 14 ('Zero duplication: Reusable patterns in the shared vocabulary?').
    - fix: Move the two factory methods into a shared test-support class in the vet test package (e.g. VetFixtures) and have both test classes call it, instead of maintaining two copies.
- ↻ **implement** (implementer) ← code-quality, test · (3 findings)
- ↻ **fix design** ← doc · (1 finding)
- ◈ **design-block** **new** · (design) · ***◷ 1m***
- ▲ **build-pass** 15:31 · build, test, check, checkFormat, handoff-log, autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 36s***
- ✔ **review code-quality** · **approved** · ***◷ 54s***
- ✔ **review test** · **approved** · ***◷ 57s***
- ✎ **review doc** · **changes_requested** · (3 findings) · ***◷ 3m***
  - [autofix] `system-design.md:121` Sentence exceeds the 30-word maximum (37 words by strict count): "H2 and PostgreSQL name the constraint `unique_owner_pet_name`; MySQL declares it unnamed and is auto-assigned a name derived from its first column, so the match fails and the violation is rethrown rather than converted to a field error." Pre-existing bootstrap-survey prose, untouched by this slice and not caught in the prior review round — that round's writing-standards sweep of this document was incomplete; a fresh full-document sweep for sentences over 30 words found this instance plus two more (below).
    - fix: Replace "`unique_owner_pet_name`; MySQL declares" with "`unique_owner_pet_name`. MySQL declares" (splits the sentence at the semicolon into two sentences of 8 and 30 words).
  - [autofix] `system-design.md:206` Sentence exceeds the 30-word maximum (32 words by strict count): "The final row is derived from code and has not been put to a human — it is listed because the contradiction is demonstrable in the source, not because intent was established." Same pre-existing, previously-uncaught class as the line-121 finding.
    - fix: Replace "a human — it is listed" with "a human. It is listed" (splits the sentence at the em-dash into two sentences of 14 and 16 words).
  - [autofix] `system-design.md:222` Sentence exceeds the 30-word maximum (45 words by strict count, not 31-44): "Whether to repair it by naming the MySQL constraint, or to remove the coupling by detecting the violation without reference to a schema identifier, is undetermined — as is whether the H2-only default test suite should be able to catch a divergence of this kind." Same pre-existing, previously-uncaught class as the line-121 finding.
    - fix: Replace "is undetermined — as is whether" with "is undetermined. So is whether" (splits the sentence at the em-dash into two sentences of 26 and 18 words).

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Output escaping: specialtyDirectory.html renders every data-derived value through th:text (entry.name, holder.firstName + ' ' + holder.lastName) with Thymeleaf's default HTML escaping on. No th:utext, no th:inline, no expression preprocessing, no request-derived value in an href or attribute. Class sweep across src/main/resources/templates/vets/ found no unsafe construct.
- Exposed surface: the one new endpoint is GET /specialties.html, read-only, no request parameters, no path variables, no binder. It re-projects exactly the data /vets.html already publishes unauthenticated (veterinarian first and last name, specialty name) with no new field or data class. Against system-design.md's Security Context baseline (demonstration app, no authn/authz by design) the change adds no new exposure category and leaves the application no weaker; NG-10's no-navigation-entry decision is a product choice, correctly not relied on as a control. Judged acceptable.
- Data access: SpecialtyRepository is a Spring Data derived findAll() with no query text; no string concatenation reaches a query. Read path is @Transactional(readOnly = true). No mass-assignment surface (no @ModelAttribute, no request-bound type, no identifier binding).
- Error disclosure: the IllegalArgumentException from SpecialtyDirectory.entryFor carries a stored specialty name, which is clinical taxonomy data, not a credential, connection string, session identifier, or PII, so it does not violate the secret-disclosure row of security-principles.md. server.error.include-message is unset, so Boot's default 'never' leaves error.html's ${message} empty; even were it enabled, the disclosed value is already public on this very page. The branch is additionally unreachable from findAll(), which returns persisted rows only.
- Unbounded findAll() with no pagination or cache: the exposure is availability only, matching the pre-existing unbounded, uncached read pattern elsewhere in the app, and specialty cardinality is bounded by clinic taxonomy rather than by any request. No new attacker-controlled amplification (the response size is independent of the request). Not a security finding under the project's threat model.
- Supply chain: no build.gradle, settings.gradle, or dependency change in the change set, and no new runtime hint or configuration property. Nothing to verify against NVD for this pass.
- Secrets: full change-set scan for credential-shaped literals returned nothing; no configuration or properties file is touched.

**code-quality-reviewer**

- Naming follows docs/architecture-principles.md (SpecialtyDirectory as a plain domain-noun record, SpecialtyRepository/SpecialtyController suffixes correct, no prohibited suffixes)
- Records are immutable with List.copyOf defensive copies on all three levels (SpecialtyDirectory, Entry, Holder)
- Stream pipelines used for the transformation; no manual index loops
- Controller stays thin: binds route, calls factory, selects view, no business rule (matches the ADR's stated deviation boundary)
- IllegalArgumentException for the null-id case includes context (the specialty name) in the message, matching the class's documented contract and covered by a dedicated test
- Templates and message keys (specialties, name, vets, none) reuse the existing vetList.html idiom and default messages.properties, keeping the two directory pages visually and structurally consistent
- checkFormat and compileJava/compileTestJava pass clean

**doc-reviewer**

- docs/prd.md's Specialty directory section stays within the PRD boundary: behavioral language throughout, no mechanism, no code-element names, ADR link present, both open questions correctly left open rather than silently resolved
- docs/adr/2026-08-08-non-goal-specialty-directory-entry-point.md and docs/adr/2026-08-08-specialty-directory-read-model.md both follow the ADR template, stay under the line guideline, cite verbatim owner language, use em-dashes in reference lists, and carry the correct Implementation section (Non-goal: NG-10 / Requirements: REQ-SPEC-001)
- docs/adr/README.md index rows match the template's Non-Goal ADR convention and both new files
- docs/ubiquitous-language.md's Specialty directory entry follows the entry format, is marked with its own provenance note distinct from the survey-derived terms, and correctly lists Avoid terms per the design notes
- docs/system-design.md's Contracts rows for SpecialtyRepository, SpecialtyDirectory, and SpecialtyController accurately describe the shipped source (verified against SpecialtyDirectory.java, SpecialtyRepository.java, SpecialtyController.java, specialtyDirectory.html); the vet/ package-structure line and the provenance-banner sentence are accurate; no field/parameter tables or constant literals were introduced
- Cross-references resolve: PRD-to-ADR links, ADR-to-PRD anchors, ADR-to-system-design links, and the adr/README.md index entries all point at existing anchors and files

**test-reviewer**

- All 8 PRD-named tests (prd-entry line 2 test_names) are present; the 2 additional tests are justified — theSpecialtyDirectoryShouldCarryTheStandardNavigation covers the explicit REQ-SYS-001 acceptance criterion and theSpecialtyDirectoryShouldRefuseASpecialtyThatWasNeverStored covers a real defensive branch in SpecialtyDirectory.of
- The unheld-specialty case is genuinely exercised: seed data (db/h2/data.sql rows 8-16) holds every specialty, so both SpecialtyDirectoryTests (pure unit, no seed data at all) and SpecialtyControllerTests (stubbed repositories via @MockitoBean) construct the case directly rather than relying on unreachable seed state — verified by reading data.sql
- theNavigationShouldNotLinkToTheSpecialtyDirectory is not vacuous: it walks every .html under src/main/resources/templates from disk and would fail if any template linked to specialties.html; confirmed non-self-referential against the new template
- New classes (SpecialtyDirectory, SpecialtyController, Entry, Holder) are at 100% line and branch coverage per jacocoTestReport, well above the brief's 80% domain-package target
- AssertJ used throughout with whole-object comparisons (new Holder(...) equality) rather than field-by-field picking; ordering assertions use containsExactly correctly
- ./gradlew test --tests "*Specialty*" --info: 14/14 green

**security-reviewer**

- Fix delta re-checked against the posture approved at handoff line 13; nothing in it changes that posture. The delta is five files: a Javadoc-only addition to SpecialtyDirectory.of, a test-method extraction in SpecialtyControllerTests, the matching helper removals in SpecialtyDirectoryTests, the new test-only VetFixtures, and two prose lines in docs/system-design.md.
- No production behavior changed. SpecialtyDirectory.java gains only an @throws tag on of(...); the null-id guard in entryFor, the stream pipeline, the List.copyOf defensive copies, and the exception message are byte-identical. SpecialtyController, SpecialtyRepository, and specialtyDirectory.html are untouched by the delta, so the escaping, exposed-surface, data-access, and error-disclosure judgments from the prior pass carry over unexamined-by-necessity only where the bytes are unchanged — verified via the name-only delta listing.
- The new @throws text discloses no more than the prior pass already cleared: it names the failure condition (specialty without a stored identifier), not a credential, connection string, or PII. Javadoc is compile-time only and reaches no HTTP response.
- Path handling in the extracted test helper is safe. referencesToSpecialtyDirectory() walks TEMPLATE_DIR, a private static final Path.of("src/main/resources/templates") literal (SpecialtyControllerTests:60) — a build-time constant with no request, environment, system-property, or argument-derived component. The extraction moved the identical Files.walk/filter/readLines body into the helper; no path is concatenated, resolved against user input, or normalized from an outside string, so there is no traversal sink. Class sweep for filesystem sinks across the whole delta (Files., Path.of, Paths.get, getenv, getProperty) found this one construct and no other.
- VetFixtures is package-private test-only support with no reflection, no deserialization, no I/O, and no randomness — two entity builders calling setters. It is not on any production classpath (src/test/java) and introduces no attack surface. The two removed private helper pairs were byte-for-byte the same code, so the move is behavior-preserving.
- Secrets: scanned the full delta for credential-shaped literals (token, password, secret, key, passwd, credential, api, bearer, plus the fixture string literals). The only literals introduced are the relative template directory path, veterinarian and specialty names in test fixtures, and the Apache license header URL. No configuration or properties file is in the delta.
- Supply chain: the delta touches no build.gradle, settings.gradle, gradle/ wrapper file, or dependency declaration, and adds no runtime hint or configuration property. No new coordinate to check against NVD for this pass; the framework versions carried over from the approved pass are unchanged.
- docs/system-design.md changes are two prose sentences (the provenance-banner rescope and the read-model parenthetical). No Security Context, threat-model, or Known Defects statement was altered, so the security profile the review is judged against is the same document it was on the prior pass.

**code-quality-reviewer**

- Prior finding resolved: SpecialtyDirectory.java's of(...) Javadoc now carries @throws IllegalArgumentException documenting that a specialty with no stored id fails the whole call, matching entryFor's actual behavior
- SpecialtyControllerTests.theNavigationShouldNotLinkToTheSpecialtyDirectory now reduces to a straight-line body; the Files.walk/filter/forEach scan is extracted into private static referencesToSpecialtyDirectory(), carrying its own Javadoc explaining what it returns and when
- New VetFixtures.java (src/test/java/.../vet/) is a proper package-private test-support class: final, private no-arg constructor, static factory methods specialty(...)/vet(...) with parameter Javadoc, eliminating the byte-for-byte duplication between SpecialtyDirectoryTests and SpecialtyControllerTests; both classes now static-import it cleanly with no leftover unused imports
- docs/system-design.md:80 prose fix (doc-reviewer's finding, out of this reviewer's checklist but scanned for regressions) introduces no new relative reference and reads as a plain state statement
- checkFormat (./gradlew checkFormat) passes clean on the full delta; no unused imports, no dead code left behind by the extraction

**test-reviewer**

- Finding 1 resolved: theNavigationShouldNotLinkToTheSpecialtyDirectory's body is now two straight-line statements (call + assertThat(...).isEmpty()); the Files.walk/filter/forEach/for-loop scan moved intact into private static List\<String> referencesToSpecialtyDirectory() throws IOException. Confirmed the scan kept its full reach: TEMPLATE_DIR is src/main/resources/templates (unchanged), the filter still matches every .html file, readLines() still reads from disk via Files.readAllLines, and each match is recorded as '\<path> line \<n>: \<trimmed line>' so a failure names the offending template. Not vacuous: same disk read as before, no change to the matching logic.
- Finding 2 resolved: specialty(int,String) and vet(String,String,Specialty...) are no longer duplicated. Both now live once in the new package-private final src/test/java/.../vet/VetFixtures.java (private constructor, static factory methods, javadoc on each), static-imported by both SpecialtyControllerTests and SpecialtyDirectoryTests. SpecialtyDirectoryTests keeps its named radiology()/surgery()/dentistry() wrappers, each delegating to the shared specialty(id, name) — Tier-1 named roles preserved on top of the shared vocabulary.
- Class sweep: grep -F for other 'specialty(int' definitions and other Files.walk usages in src/test/java found none outside VetFixtures.java / SpecialtyControllerTests.java (the one other Files.walk user, I18nPropertiesSyncTest, is unrelated pre-existing code, not part of this delta) — no further instances of either finding's class remain.
- The @throws IllegalArgumentException javadoc addition on SpecialtyDirectory.of(...) is an accurate, welcome doc improvement matching the existing test theSpecialtyDirectoryShouldRefuseASpecialtyThatWasNeverStored; no test changes needed for it.
- ./gradlew test --tests "*Specialty*" --info: green; ./gradlew test build successful with jacocoTestReport generated.

**doc-reviewer**

- docs/system-design.md:80 resolved: the parenthetical now reads "added 2026-08-08 for  REQ-SPEC-001 " — both the stale "not yet in the working tree" claim and the relative reference "below" are gone, and the date/requirement-ID mark matches the rescoped banner convention. Verified against the working tree: SpecialtyRepository.java, SpecialtyDirectory.java, SpecialtyController.java all exist under vet/.
- docs/system-design.md:8 banner sentence rescope is accurate document-wide: repo-wide scan for other date/REQ-ID-stamped or otherwise-flaggable post-survey prose in this document found only line 80 (marked) and the Contracts table rows at 111-113 (table entries, not prose, already covered by the Implements column per the design-block's stated rationale); the vet/ package-structure line at line 36 is a code-block tree annotation, not prose, so it does not contradict the rescoped sentence's narrower 'Prose introducing material' scope. The self-found defect is correctly resolved and stayed true under a fresh check.
- Sentence-length re-audit: lines 82 and 174, both named in the system-design-expert's report as 31-44-word instances, are not actually over the 30-word maximum by strict per-sentence count (max 26 and 30 words respectively) — no finding raised against them.
- Source-drift check: VetFixtures.java (new shared test vocabulary), SpecialtyControllerTests.java's extracted referencesToSpecialtyDirectory() helper, and SpecialtyDirectory.of(...)'s new @throws tag are all test-support or javadoc-only changes with no corresponding claim in docs/system-design.md to go stale — the document correctly says nothing about test helpers, and the @throws tag matches entryFor's null-id branch already implied by the shipped contract. No doc drift.
- Repo-wide relative-reference sweep (above/below/previous) of docs/system-design.md returns nothing.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:system-design-expert` | 2 | opus-5 | $5.17 | 9m 7s | 92% |
| `agent-team:feature-implementer` | 2 | opus-5 | $5.09 | 14m 44s | 94% |
| `(parent)` | 1 | opus-5 | $4.40 | 38m 28s | 95% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $2.82 | 5m 17s | 93% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $2.07 | 5m 35s | 91% |
| `agent-team:security-reviewer` | 2 | opus-5 | $1.81 | 2m 20s | 80% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $1.38 | 2m 54s | 88% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.37 | 3m 47s | 85% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.07 | 0s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $4.40 | 38m 28s | 95% |
| `agent-team:system-design-expert` | opus-5 | $3.90 | 6m 55s | 93% |
| `agent-team:feature-implementer` | opus-5 | $3.85 | 11m 41s | 94% |
| `agent-team:product-requirements-expert` | opus-5 | $2.82 | 5m 17s | 93% |
| `agent-team:system-design-expert` | opus-5 | $1.27 | 2m 11s | 90% |
| `agent-team:feature-implementer` | opus-5 | $1.23 | 3m 3s | 93% |
| `agent-team:doc-reviewer` | sonnet-5 | $1.12 | 1m 53s | 87% |
| `agent-team:security-reviewer` | opus-5 | $1.02 | 1m 33s | 81% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.95 | 3m 42s | 94% |
| `agent-team:test-reviewer` | sonnet-5 | $0.91 | 2m 43s | 86% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.86 | 1m 53s | 89% |
| `agent-team:security-reviewer` | opus-5 | $0.79 | 46s | 77% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.52 | 1m 0s | 86% |
| `agent-team:test-reviewer` | sonnet-5 | $0.45 | 1m 4s | 82% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.07 | 0s | 0% |

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

- plugin `agent-team-spring-boot` at `v0.2.2` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.226 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
