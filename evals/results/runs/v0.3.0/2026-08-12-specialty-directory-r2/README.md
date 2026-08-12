# specialty-directory r2 — v0.3.0

Specialty directory page (feature) · started 2026-08-11T22:52:55+00:00 · exec `claude-dev` · status **complete**

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
| 5 (±1) | 4 (±0) | 5 (±1) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.69. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 5 · doc-fit 5

> SpecialtyDirectory.of (SpecialtyDirectory.java:64) keeps grouping, ordering and name formatting out of SpecialtyController, whose mapping only delegates and selects a view (SpecialtyController.java:38-42); SpecialtyRepository mirrors the existing read-only repository style, and the template reuses the vetList span idiom. Tests are behavior-named, use hand-written stubs rather than a mock framework (ClinicRecords, SpecialtyControllerTests.java:129-155), name every value (RADIOLOGY_ID, HELEN_ID), and push most coverage into framework-free unit tests. Knock: createSpecialty/createVet and the whole constant block are duplicated verbatim in both test classes instead of extracted into shared vocabulary, and doesNotContain("page=") over full HTML is a brittle assertion. Docs move fully: REQ-VET-003, three contract rows, and the new vocabulary term.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 5 · doc-fit 5

> SpecialtyDirectory holds the grouping/ordering rule outside the controller, so SpecialtyController.showSpecialtyDirectory only binds, delegates and selects a view — the Web controller row is respected and the rule is unit-testable. Repositories are constructor-injected; the read model is final, immutable, and its identifier join is justified by BaseEntity's missing equals. The template reuses existing #{specialties}/#{name}/#{vets} keys and the vetList span idiom. Tests are behavior-named, four-phase, and use hand-written stubs (ClinicRecords) rather than a mock framework. Test quality falls short of 5: createSpecialty/createVet plus RADIOLOGY_ID..LINDA_ID are copy-pasted verbatim into both test classes instead of a shared vocabulary, and no test covers the stated "no link leads to the page" criterion. Docs (PRD REQ-VET-003, contracts table, vocabulary) are fully current.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The join logic sits in an immutable, framework-free  SpecialtyDirectory.of(...) , leaving  SpecialtyController.showSpecialtyDirectory  a pure bind-delegate-select controller — right layer, unit-testable, no new rule in the web layer. Two catalog frictions:  SpecialtyDirectory  matches no In-force or Available pattern (a read model, not a value object — no value equality) and  SpecialtyRepository  is a repository for a non-aggregate-root lookup type, neither carrying an ADR.  specialtyDirectory.html  introduces  #{specialties} / #{name} / #{vets}  but the patch adds no message-bundle entries, risking the REQ-LANG-002 bundle-key test. Tests are behavior-named, phase-structured, hand-written stubs, no mock framework; but  createSpecialty / createVet  and the ID constants are duplicated verbatim across both test classes, and  doesNotContain("page=")  is a brittle whole-page assertion. Docs (PRD REQ-VET-003, contracts rows, vocabulary) are current.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.37 | 34m | 28 | 89% | 9 file(s) +595/−4 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.00 | 3m 10s | 88% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · grade **CONCERN**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | **✔** | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (1) | **✔** |

- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **minor** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 11m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain not verified against the NVD in this review: the project configures no OWASP Dependency-Check plugin (build.gradle declares java, checkstyle, jacoco, spring-boot 4.1.0, dependency-management, native, cyclonedx, javaformat), and this reviewer has no network access. The change introduces no dependency delta, so nothing here is newly unverified - but a human or CI should close the standing CVE check against the resolved Spring Boot 4.1.0 tree. A CycloneDX SBOM task is already available for that.
  - ▹ rec: The directory reads the entire vet roster and the entire specialty table per request (SpecialtyController:128), where /vets.html paginates at 5. This matches the existing unpaged /vets JSON endpoint and the seeded data is tiny, so it is parity rather than a regression; if the roster ever grows, both unpaged readers should be revisited together.
- ✔ **review test** · **approved** · ***◷ 1m***
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 1m***
  - **[blocked]** `system-design.md#contracts` docs/prd.md's new REQ-VET-003 section links **Design:** to system-design.md#contracts, but the Contracts table carries no rows for SpecialtyRepository, SpecialtyController, or SpecialtyDirectory (src/main/java/org/springframework/samples/petclinic/vet/{SpecialtyRepository,SpecialtyController,SpecialtyDirectory}.java), the three new public types this slice ships. The design-block (handoff line 4) deferred this as a doc-sync follow-up on the premise the contracts 'do not exist yet.' The code now exists and is merged (build-pass at line 6), so that premise no longer holds: system-design.md's own header mandates 'current state only,' and a reader following the PRD's Design link finds none of the mechanism it promises. Add one Contracts row per new type (Purpose, Source, Implements REQ-VET-003), matching the existing Vet/VetRepository/VetController row shape.
- ◈ **design-block** **minor** · (design) · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved** · ***◷ 16s***
- ✔ **review code-quality** · **approved** · ***◷ 20s***
- ✔ **review doc** · **approved** · ***◷ 34s***
- ✔ **review security** · **approved** · ***◷ 31s***
  - ▹ rec: The SpecialtyDirectory row's phrase 'one nested Entry per specialty carries that specialty's holders' reads as though Entry carried Vet objects; the adjacent Invariants sentence ('holds no persisted state') is what pins down that holders are formatted names. If the row is ever edited alone, keeping the string-payload property explicit preserves the security-relevant reading. No change needed now.
  - ▹ rec: Supply chain was not re-run this round: the delta touches no dependency declaration, so the round-1 dependency posture is unchanged and carries forward as recorded rather than re-verified against the NVD.
- ◆ **grade CONCERN** · add the read-only specialty directory page
  - blast_radius — **clear** — Nine files in one module, fifteen hunks, no sensitive paths, and zero deletions in production code: three new types and one new template that no existing class references, plus three doc files. The only touch on shared state is calling the pre-existing @Cacheable vets VetRepository.findAll, which is read-only and returns the same data /vets.html already serves, so no existing request path changes behavior.
  - semantic_surprise — **clear** — Reading the hunks against the two risks the design flagged, both are actually handled rather than merely claimed: grouping keys on held.getId() through a HashMap (equals-based lookup, not reference identity), and both comparators are total with an id tie-break, so ordering is stable over Vet's HashSet and the unordered findAll. The trap I expected here does not fire either, since Vet.specialties is FetchType.EAGER, so the read model touching getSpecialties() outside the repository transaction cannot raise LazyInitializationException. The template mirrors vetList.html, escapes through th:text with no th:utext, and passes a layout menu argument matching no menuItem, which is exactly the deliberate no-nav-entry decision.
  - test_adequacy — **clear** — The tests would fail against a broken implementation rather than restate it. SpecialtyDirectoryTests builds two distinct Specialty instances sharing an id, which fails outright under identity or equals-based grouping, and asserts the shared-name case that a non-total comparator would leave arbitrary. SpecialtyControllerTests renders the real Thymeleaf template through MockMvc against hand-written stubs and asserts on the returned HTML, with the VetRepository stub throwing on findAll(Pageable) to pin that the page never pages. The only mild brittleness is doesNotContain page= asserting against the whole rendered layout.
  - reviewer_hedging — **concern** — Round two is unanimous approval, but the security reviewer parked two recommendations on that late-round approval rather than closing them: the doc row wording that reads as though Entry carried Vet objects (self-marked no change needed), and the supply-chain check, which was never verified against the NVD in round one for lack of network access and was explicitly not re-run in round two, carrying forward as recorded rather than verified. Round one also cost a full cycle on a doc-reviewer critical/blocked finding tagged bar_clause legible-cold, and its fix left a pre-existing Contracts preamble imprecision (public type against package-private controllers) open as a separate doc-sync item.
  - scope_deviation — **clear** — Zero design revisions, zero consultations, zero build retries, and the diff maps one-to-one onto the requirement's five Done-when clauses and four edge cases with nothing beyond them. The second review cycle added Contracts table rows in response to a doc finding, which is a documentation gap closing rather than scope drift, and the three unresolved product questions are recorded in the PRD's Open Questions rather than silently decided in code.
  - why — Additive, contained, and the two load-bearing risks the design named are genuinely handled in the code, not just asserted. What deserves a look is not the diff but the residue around it: the supply-chain CVE check was never run for this slice in either round, and the Contracts preamble imprecision stays open. Confirm both are acceptable to carry, then merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyRepository, SpecialtyController, and package placement mirror the existing per-noun controller/repository pattern (VetController, PetTypeRepository) precisely, including javadoc style and constructor-injection form
- SpecialtyDirectory is a well-documented immutable read model: static factory, private constructor, explicit total-order comparators with id tie-breaks for both specialty name and holder last/first name, defensive via Stream.toList() so no mutable state escapes
- Grouping algorithm (holdersBySpecialtyId) correctly joins Vet-held Specialty instances to stored Specialty instances by identifier only, matching the documented rationale (BaseEntity has no equals/hashCode, separate persistence contexts)
- Template reuses the exact ${name + ' '} span-per-item idiom already established in vetList.html, and reuses existing translated message keys (specialties/name/vets) rather than adding English-only synonyms, per the design-block's decision
- checkFormat, compileJava, and compileTestJava all pass clean; no format or compile issues introduced
- Tests (read as context, not graded here) exercise ordering, tie-breaking, and empty-holder/no-specialty edge cases directly against the read model, keeping the controller test focused on HTTP wiring

**security-reviewer**

- Output encoding: every dynamic value in src/main/resources/templates/vets/specialtyDirectory.html renders through th:text (entry.specialtyName, and each veterinarian name inside the th:each span). No th:utext, no th:attr/th:href carrying a model value, no inline script, no external resource reference, no Thymeleaf preprocessing (__${...}__) of any model-derived value. The one preprocessing site in the codebase (fragments/layout.html:31) takes literal fragment arguments and is untouched by this change. Thymeleaf default escaping stays on, satisfying security-principles.md 'Cross-site scripting'.
- No new attack surface at the request boundary: SpecialtyController.showSpecialtyDirectory takes only Model - no @RequestParam, @PathVariable, @RequestBody, form binding, or @InitBinder. With nothing request-derived entering the handler, the mass-assignment, path-traversal, and injection rows of security-principles.md have no reachable instance here. The absent navigation entry was judged as the product decision it is, not as an access control; the endpoint is rated as public, and at that rating it exposes nothing new.
- Data access: SpecialtyRepository is a Spring Data derived findAll() over the existing specialties table with no query text at all, so no string-concatenated query exists to attack. The interface extends the narrow Repository base (not JpaRepository) and declares one read method annotated @Transactional(readOnly = true) - least privilege at the persistence boundary, and no write path is opened. No schema, seed-data, or configuration change.
- Data exposure parity: the page renders specialty names and vet full names, which the pre-existing /vets.html and the /vets JSON endpoint (VetController.showResourcesVetList, an unpaged findAll of the whole roster with specialties) already expose to the same anonymous caller. SpecialtyDirectory.Entry deliberately holds holder names as Strings rather than Vet entities, so no detached entity, identifier, or unrelated field reaches the view - the read model narrows the exposed surface relative to the vet list rather than widening it.
- Concurrency and resource handling: SpecialtyController is a stateless singleton holding only final repository references; SpecialtyDirectory and its Entry are final classes with private constructors whose lists come from Stream.toList() (unmodifiable), and both comparators are stateless statics. No mutable shared state, no file handle, no stream, no executor, no SimpleDateFormat. The unpaged reads mirror the existing cached VetRepository.findAll() path and add no new unbounded allocation class.
- No secrets, logging, or error-surface change: the diff adds no credential-shaped literal (swept for token/password/secret/key/credential/passwd/apikey across the change set), no logger call, no System.out/err, no exception construction, and no message that could carry internal detail outward. No deserialization, reflection, XML/YAML parsing, Runtime/ProcessBuilder, file I/O, or java.util.Random appears in the new code.
- Supply chain: build.gradle is not in the change set and the diff adds no dependency, so the 'new dependency' checks in system-design.md are not triggered by this change.

**test-reviewer**

- theSpecialtyDirectoryShouldGroupHoldersUnderTheSpecialtyTheyShareAnIdentifierWith is genuinely load-bearing: it constructs the stored Specialty and the vet-held Specialty as distinct instances sharing only an id, and neither BaseEntity, NamedEntity, nor Specialty overrides equals/hashCode (verified by reading all three), so a name- or equality-keyed grouping implementation would leave the holder list empty while the id-keyed SpecialtyDirectory.of implementation passes - the test discriminates the real defect class the design-block flagged
- Order tests (theSpecialtyDirectoryShouldOrderSpecialtiesByName, ...SharingANameByIdentifier, ...OrderHoldersByLastNameThenFirstName) feed out-of-order/HashSet-backed input and assert an exact expected sequence via containsExactly, so they would catch a regression to HashMap/HashSet iteration order rather than passing incidentally on a lucky hash layout
- All five prd-entry test_names carried over verbatim into SpecialtyControllerTests and each maps to a genuine PRD acceptance criterion or edge case (edge case 1 no-holder specialty, edge case 2 empty directory via the unit suite, edge case 3 stable order via the unit suite, single-page/no-paging via an explicit ?page=2 probe compared against the unpaged render)
- Mocking policy honored: SpecialtyRepository and VetRepository are hand-written stubs (lambda and anonymous class), no new Mockito usage introduced; MockMvc is the one sanctioned mock for the controller test
- 100% line coverage on SpecialtyDirectory, SpecialtyController, and Specialty per jacocoTestReport, well above the docs/testing-principles.md 80% target
- BDD naming (the{Subject}Should{Outcome}), four-phase structure without narration comments, AssertJ fluent chained assertions, role-named Tier-1 constants (RADIOLOGY_ID, HELEN_ID, etc.) with no mystery literals, and factory methods (createSpecialty/createVet) wrapping all construction - all consistent with docs/testing-principles.md

**doc-reviewer**

- REQ-VET-003 prose and Done-when bullets stay behavioral - no route, no code element, no mechanism leaked into the PRD
- GET /specialties.html correctly kept out of prd.md and confined to the handoff record's acceptance criteria
- Edge cases and Open Questions additions are consistent with the acceptance criteria and with each other
- REQ-VET-002 remains correctly withdrawn to the Superseded list; REQ-VET-003 is a fresh id, not a reuse
- Specialty directory term added to ubiquitous-language.md with correct provenance date and no collision with the existing Specialty entry
- All new sentences in docs/prd.md and docs/ubiquitous-language.md are under the 30-word standard
- Anchors and cross-references in the changed prose resolve (req-vet-003 anchor present, ubiquitous-language.md link intact)

**test-reviewer**

- The new Invariants sentence (Vet→Specialty unidirectional, SpecialtyDirectory joins on identifier) matches production code: Specialty extends NamedEntity with no Vet back-reference
- theSpecialtyDirectoryShouldGroupHoldersUnderTheSpecialtyTheyShareAnIdentifierWith already pins the documented invariant exactly: it constructs the stored Specialty and the vet-held Specialty as distinct instances sharing only an id, then asserts SpecialtyDirectory.of joins them — no coverage gap between the newly documented invariant and the existing test
- Round-1 approval stands unchanged; the docs-only delta records a property already verified by tests, it introduces no new untested behavior

**code-quality-reviewer**

- New Contracts rows for SpecialtyRepository, SpecialtyDirectory, and SpecialtyController accurately describe the shipped code: SpecialtyRepository extends Repository (not JpaRepository) with a single read-only findAll(); SpecialtyDirectory.Entry carries pre-formatted holder names in a stable order; SpecialtyController is package-private with one no-parameter @GetMapping, verified against source
- Added invariants sentence on the unidirectional Vet-to-Specialty mapping matches SpecialtyDirectory's class javadoc
- checkFormat passes; delta is docs-only, round-1 code-quality approval unaffected

**doc-reviewer**

- Contracts table now carries SpecialtyRepository, SpecialtyController, and SpecialtyDirectory rows, each read off the shipped source with matching Purpose/Source/Implements shape to the existing Vet row family - the PRD's Design link to #contracts resolves to the mechanism it promises
- Added Invariants sentence correctly records the Vet-to-Specialty mapping as unidirectional and SpecialtyDirectory as joining on identifier with no persisted state, closing the round-1 blocked finding
- Omission of supersedes_record_at is correct: the design-validation skill reserves the field for a true re-triage and states a prose fix never carries it; this fix changed no verdict, design, or primary path
- Deferring the Contracts preamble's public-type imprecision (OwnerController, VetController, SpecialtyController are package-private) as a separate doc-sync item is sound scoping - confirmed pre-existing as of commit 4ba2937, predates this slice, spans three controllers, and the fix is prose-only, never a code-visibility change; folding it into this blocked-finding fix would smuggle an unrelated edit into a critical-fix delta

**security-reviewer**

- Delta is documentation-only (docs/system-design.md, 4 lines); no src/, build.gradle, template, or config surface changed, so the round-1 threat-model walk and supply-chain result stand unchanged
- Contracts row for SpecialtyRepository ('Read-only Spring Data repository') matches the shipped type: extends the bare Repository\<Specialty, Integer> marker rather than CrudRepository, exposes only findAll() under @Transactional(readOnly = true), and surfaces no save/delete — the doc does not overstate a write path that is absent, nor understate one that exists
- Contracts row for SpecialtyController ('the mapping takes no request parameter') matches SpecialtyController.showSpecialtyDirectory(Model): a single @GetMapping("/specialties.html") with no @RequestParam, @PathVariable, or command-object binding — the documented zero-request-input attack surface is the real one
- Contracts row for SpecialtyDirectory ('Immutable read model', nested Entry per specialty) matches the shipped type: Entry holds String specialtyName and List\<String> veterinarianNames — pre-formatted strings, not detached Vet/Specialty entities — so the doc does not invite a future reader to expose entity graphs or lazy associations through the view model
- New Invariants sentence ('reads the two sides separately, joins them on the identifier, and holds no persisted state') is accurate against SpecialtyDirectory.of and holdersBySpecialtyId, and correctly documents the identifier join forced by BaseEntity declaring neither equals nor hashCode — it does not describe a state-holding or request-scoped-mutable-singleton shape that the code contradicts

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $5.50 | 14m 0s | 94% |
| `(parent)` | 1 | opus-5 | $4.14 | 37m 1s | 95% |
| `agent-team:system-design-expert` | 2 | opus-5 | $3.60 | 6m 57s | 90% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $2.12 | 3m 56s | 90% |
| `agent-team:change-grader` | 1 | opus-5 | $2.00 | 3m 10s | 88% |
| `agent-team:security-reviewer` | 2 | opus-5 | $2.00 | 2m 8s | 76% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.43 | 2m 35s | 87% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.18 | 2m 17s | 83% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.94 | 1m 38s | 82% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.07 | 0s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.45 | 11m 38s | 95% |
| `(parent)` | opus-5 | $4.14 | 37m 1s | 95% |
| `agent-team:system-design-expert` | opus-5 | $2.13 | 4m 29s | 90% |
| `agent-team:product-requirements-expert` | opus-5 | $2.12 | 3m 56s | 90% |
| `agent-team:change-grader` | opus-5 | $2.00 | 3m 10s | 88% |
| `agent-team:system-design-expert` | opus-5 | $1.47 | 2m 28s | 91% |
| `agent-team:security-reviewer` | opus-5 | $1.31 | 1m 27s | 79% |
| `agent-team:feature-implementer` | opus-5 | $1.04 | 2m 22s | 92% |
| `agent-team:doc-reviewer` | sonnet-5 | $1.01 | 1m 47s | 84% |
| `agent-team:test-reviewer` | sonnet-5 | $0.86 | 1m 54s | 86% |
| `agent-team:security-reviewer` | opus-5 | $0.69 | 41s | 68% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.56 | 1m 11s | 87% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.43 | 48s | 91% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.38 | 27s | 70% |
| `agent-team:test-reviewer` | sonnet-5 | $0.32 | 23s | 75% |
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

- plugin `agent-team-spring-boot` at `v0.3.0` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.227 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
