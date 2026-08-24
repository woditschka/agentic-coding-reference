# specialty-directory r3 — v0.1.29

Specialty directory page (feature) · started 2026-08-24T03:55:37+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±1) | 4 (±0) | 4 (±0) | 5 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.72. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController delegates entirely to SpecialtyDirectoryEntry.directoryOf, keeping the new rule out of the controller as the catalog demands, and the package-private record plus SpecialtyRepository match the value-object and repository rows; the ADR justifies the departure from local habit. One friction: ubiquitous-language.md newly lists "Specialty list" under Avoid, yet the view is named vets/specialtyList and specialtyList.html. Unit tests are exemplary — behavior names, factory methods, whole-entry comparison via anEntryFor, hand-written fakes, no mock framework. The MockMvc tests are weaker: bare "dentistry"/"James Carter" literals beside HELD_SPECIALTY constants, and brittle negative assertions (not(containsString("none")), "nav-link active")) that re-test derivation already covered. Template concatenation with a trailing space is rough. Documentation is comprehensively updated across PRD, system-design, glossary, and ADR index.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Derivation sits in an immutable record ( SpecialtyDirectoryEntry , defensive  List.copyOf , pure static  directoryOf ), leaving  SpecialtyController.showSpecialtyDirectory  to read repositories and select a view — no new controller rule, and the departure from the local habit is justified in an ADR.  SpecialtyRepository  follows the existing repository shape. Unit tests use real  Vet / Specialty  behind factories, behavior names, named constants, and whole-entry comparison via  anEntryFor ; the controller slice hand-writes doubles instead of a mock framework. Weaknesses: negative HTML-substring assertions are brittle ( not(containsString("none")) ,  "nav-link active" ,  "?page="  as proof of no paging), bare ids and a raw  "dentistry"  in the slice fixture, and  #{specialties} / #{vets}  keys are referenced but no message bundle is added.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> SpecialtyDirectoryEntry.directoryOf is a pure static factory over immutable inputs, leaving SpecialtyController:39-43 rule-free and matching the Web controller and Value object rows; the ADR records the departure. Minor wart: the whole-directory factory hangs off the entry record rather than a directory type. Unit tests are exemplary — behavior names, factories (aSpecialtyNamed), hand-written doubles, whole-object comparison via anEntryFor, plus unsaved-specialty and no-mutation cases. Weaker: SpecialtyControllerTests duplicates that coverage through raw-HTML matchers, and not(containsString("none")) / not(containsString("nav-link active")) bind tests to layout markup. specialtyList.html uses #{specialties}, #{name}, #{vets} with no message-bundle entry in the patch, contradicting the new prd.md edge case 4 that REQ-LANG-002 governs the page's wording.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $14.27 | 37m | 32 | 93% | 11 file(s) +609/−8 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.22 | 3m 42s | 94% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Reader sees every specialty with the veterinarians holding it

2 review rounds · 2 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (1) | **✔** |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (2) | **✔** |

- ◇ **prd-entry** Reader sees every specialty with the veterinarians holding it · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 6m***
- ◆ **implement** (implementer) · ***◷ 9m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 40s***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [autofix] `SpecialtyDirectoryEntry.java:33` SpecialtyDirectoryEntry is declared `public record`, but grep across the repository shows it is used only inside the `vet` package (SpecialtyController and the two test classes in the same package); no other package references it. This violates architecture-principles.md's Minimal Surface rule ("a type or member is module-internal unless another module uses it today") and breaks the visibility convention this same package already follows: SpecialtyController and VetController are both package-private. Widening SpecialtyDirectoryEntry to public makes an unused promise to future callers and is inconsistent with its sibling controller classes.
    - fix: Drop the `public` modifier so `record SpecialtyDirectoryEntry(...)` is package-private, matching SpecialtyController/VetController. Verify Thymeleaf rendering (specialtyList.html) and the test classes (same package) still work after the change — they should, since all use sites are in-package.
- ✔ **review security** · **approved** · ***◷ 1m***
- ✎ **review doc** · **changes_requested** · (2 findings) · ***◷ 1m***
  - **[blocked]** `ubiquitous-language.md` "Specialty directory" is domain vocabulary this change introduces into prd.md (heading "Specialty directory", REQ-VET-003 prose), system-design.md (SpecialtyDirectoryEntry contract row, SpecialtyController purpose text), and the test suite (SpecialtyDirectoryEntryTests, SpecialtyControllerTests method names), but it has no entry in docs/ubiquitous-language.md. The type name SpecialtyDirectoryEntry adopts the term as canonical, so the term is load-bearing, not incidental prose. prd-authoring's Ubiquitous Language Discipline forbids drafting the PRD with a term not yet in ubiquitous-language.md.
    - fix: Add a "Specialty directory" entry to docs/ubiquitous-language.md defining the page/concept, following the existing entry format (one-sentence definition, optional Relationships/Avoid lines).
  - **[blocked]** `prd.md:137` The narrative embeds the literal route address `/specialties.html` ("The page is reachable at its own address, `/specialties.html`, and nothing links to it"). This is a hardcoded constant/mechanism value in the PRD, prohibited per document-writing's Prohibited Patterns table ("Hardcoded constant values" → reference a Constants section in system-design.md) and prd-authoring's own table. The behavioral fact that matters here is reachability without navigation, which does not require citing the literal path. The review-checks.md PRD autofix rules exclude this from autofix: "mechanism moving in or out of the PRD is a boundary finding, not a style fix."
    - fix: Rephrase to state the behavior without the literal path, e.g. "The page is reachable at a fixed address, and nothing links to it—see system-design.md#contracts for the route." Add the route as a Constants-section entry (or a Contracts-table note, since it already exists there via SpecialtyController) in system-design.md if a concrete pointer is needed.
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `SpecialtyDirectoryEntryTests.java` The fail-closed guard in SpecialtyDirectoryEntry.holds() — `!held.isNew() && held.getId().equals(specialty.getId())` (SpecialtyDirectoryEntry.java:76) — has its `isNew()==true` short-circuit branch never exercised. JaCoCo confirms: 'L76 ... 1 of 4 branches missed.' Every Specialty built by the test factories (aSpecialtyNamed) is given an id, so no test ever adds an unsaved (no-id) Specialty to a Vet's held set. This branch is not incidental: the superseding design-block (line 8) names it as a deliberate, load-bearing behavior — 'the !isNew() guard fails closed rather than throwing... a directory derived over unsaved objects would silently render every specialty as unheld' — and states the constraint in terms of the tests setting ids, but the guard's actual effect (an unsaved specialty never matches) is left unverified. Line coverage reads 100% for the class, which is why this gap is invisible without a branch-level check.
    - fix: Add a unit test (e.g. theSpecialtyDirectoryShouldNotMatchAnUnsavedSpecialtyToAStoredOne) that builds a Vet holding a Specialty with the same name as a stored Specialty but with no id set (a bare `new Specialty()` with only the name set, not run through aSpecialtyNamed), calls directoryOf, and asserts the veterinarian does not appear under that stored specialty's entry — proving the fail-closed guard rather than just disciplining test data to avoid tripping it.
- ↻ **implement** (implementer) ← code-quality, test · (2 findings)
- ↻ **fix prd-expert** ← doc · (2 findings)
- ◇ **prd-entry** Reader sees every specialty with the veterinarians holding it · (prd-expert) · ***◷ 1m***
- ▲ **build-pass** 04:28 · build, test, format, handoff-log, autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 22s***
- ✔ **review security** · **approved** · ***◷ 41s***
- ✔ **review doc** · **approved** · ***◷ 38s***
- ✔ **review test** · **approved** · ***◷ 1m***
- ◆ **grade CLEAR** · add read-only specialty directory page
  - blast_radius — **clear** — Additive and contained: all four production files are new and sit in the vet package, no existing production file is modified at all (the only edited files are docs), and there is no schema, dependency, configuration, cache, or navigation change. The single new surface is one GET route, /specialties.html, and no sensitive path is touched.
  - semantic_surprise — **clear** — I read every production hunk and the template. The derivation matches by persisted identity with a fail-closed guard (!held.isNew() && held.getId().equals(specialty.getId())), so an unsaved specialty of the same name cannot match a stored one; specialty order is by stored name and holder order is last name, first name, id-nulls-last; both input collections are read through stream copies so the cached VetRepository list is never reordered. Comparator null-intolerance on names mirrors the pre-existing Vet.getSpecialties(), and the EAGER @ManyToMany rules out a lazy-initialization failure the web slice could not see. The only wrinkle is cost, not behavior: getSpecialties() is re-sorted and copied once per specialty-vet pair, irrelevant at clinic scale.
  - test_adequacy — **clear** — The tests assert outcomes, not the implementation. Nine unit tests over real Vet and Specialty objects pin the boundaries the code actually decides: an unheld specialty is present with an empty holder list, a vet holding nothing is absent, an unsaved specialty does not match a stored one, ties break by first name then id, and both source collections are unchanged afterwards. Six web-slice tests render the real Thymeleaf template and assert on produced HTML with negative assertions (no paging parameter, no reversed name order, no navigation link). No end-to-end request hits the route against the real database, but PetClinicIntegrationTests boots the full context, so the new SpecialtyRepository bean wiring is proven to resolve.
  - reviewer_hedging — **clear** — Round 2 is a clean unanimous approval: all four reviewers the plan dispatched approved with empty findings arrays, no escalate tag and no bar_clause anywhere. The round-1 findings (public visibility on a package-internal record, a missing ubiquitous-language entry, an embedded literal route in the PRD, an unexercised isNew() branch) were each fixed and named as resolved by the reviewer that raised them.
  - scope_deviation — **clear** — Zero consultations and zero build retries against the current design block, and the diff matches the requirement's stated surface with nothing extra. The one design revision was bookkeeping, not a scope fight: the autofix audit flagged the ADR index row as uncovered by the design block's file list. The PRD supersede was the doc reviewer's wording fix, and the three new open questions are honest disclosure of what the slice deliberately left undecided.
  - why — Purely additive read-only page, entirely inside the vet package, with no existing production file touched. The derivation logic reads correctly at every boundary and the tests pin those boundaries with real objects. Confirm and merge; no hunk needs a second look.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- Cache hazard avoided correctly: directoryOf/holdersOf never mutate the veterinarians collection in place — they operate via Stream.sorted()/toList(), which return new lists, so the @Cacheable("vets") instance from VetRepository.findAll() is left untouched; SpecialtyDirectoryEntryTests.theSpecialtyDirectoryShouldLeaveTheCollectionsItReadsUntouched exercises this explicitly.
- Stored-identity matching rule implemented exactly as specified: holds() uses !held.isNew() && held.getId().equals(specialty.getId()), correctly avoiding reliance on BaseEntity's absent equals/hashCode.
- Record is a proper immutable value object: compact constructor null-checks specialtyName and defensively copies veterinarians via List.copyOf.
- SpecialtyRepository and SpecialtyController match established package conventions (public repository interface, package-private controller, constructor injection, single @GetMapping).
- Javadoc on directoryOf explicitly documents the cache-aliasing hazard and why in-place mutation must be avoided, which is exactly the kind of context a future reader needs.
- ./gradlew checkFormat passes (task is named checkFormat, not checkJavaFormat, in this project's Gradle setup).
- Message keys used in specialtyList.html (specialties, name, vets) exist in messages.properties and are localized in all locale variants.
- Design matches the superseding ADR (2026-08-24-read-model-derivation-in-value-types.md) and system-design.md Contracts table: derivation and ordering live solely in the value type, controller only reads repositories and delegates.

**security-reviewer**

- Output escaping: specialtyList.html renders every user-derived value through th:text only (entry.specialtyName, veterinarian.firstName/lastName). No th:utext, no th:inline, no th:href/th:src carrying stored data, no javascript: sink. Thymeleaf's default HTML escaping applies, and the application does not disable it. Class sweep across the changed templates and the whole vet package found no unescaped-output instance, so a stored specialty or vet name containing markup renders inert.
- Injection exposure: SpecialtyRepository is a Spring Data derived-query interface (Repository\<Specialty,Integer> with a bare findAll()); no JPQL string, no native query, no concatenation, no user-supplied fragment. SpecialtyController takes no @RequestParam, @PathVariable, @RequestBody, or form binding, so there is no attacker-controlled value on the path to the data store. This matches the system-design threat-model row for SQL injection.
- Transaction scoping: findAll() is annotated @Transactional(readOnly = true), matching VetRepository. The endpoint performs no write, and GET /specialties.html is side-effect-free, so the absence of CSRF protection (a documented application-wide posture) has no bearing on this route.
- Endpoint exposure: the new route is unauthenticated, which is the application's documented pre-existing posture (docs/system-design.md Security Context: no authentication, authorization, or CSRF anywhere in the codebase). The route adds attack surface but no new privilege boundary: it is read-only, parameterless, and reachable only by GET. docs/system-design.md Security Context was updated with the endpoint-exposure sentence, so the widened surface is recorded rather than silent.
- Data exposure: the page publishes exactly specialty names and veterinarian first/last names. Both classes are already published unauthenticated by GET /vets.html and its serialized-collection sibling. SpecialtyDirectoryEntry projects only specialtyName plus the Vet list, and the template reads only firstName and lastName off each Vet, so no identifier, no telephone, no owner or pet data, and no internal field reaches the response. The one genuinely new datum is the existence of a specialty nobody holds, which is clinic-published reference data, not PII. No new class of data crosses the boundary.
- Cache integrity: directoryOf receives the @Cacheable("vets") collection from VetRepository.findAll() and never mutates it - ordering is done with stream().sorted() into fresh lists, and the record's compact constructor takes List.copyOf. A caller cannot poison the shared vet cache through this path.
- Availability: the no-pagination decision renders every specialty and its holders in one response. The data is bounded clinic reference data with no attacker-controlled growth path (specialties are seeded, and vet/specialty creation has no HTTP route), and the response carries two short strings per row. Not a practical resource-exhaustion vector; recorded as assessed, not raised as a finding.
- Secrets: no credential, token, key, or password literal in the diff; no new logging statement, so no user-derived or sensitive value reaches a log sink.
- Supply chain: build.gradle is not in the change set - no dependency added, removed, or version-bumped, so this slice introduces no new CVE surface. Spring Boot 4.1.0 and the Thymeleaf/Spring Data versions it manages are unchanged from the reviewed baseline.
- Test surface: SpecialtyControllerTests uses @WebMvcTest with a @TestConfiguration supplying in-memory repository doubles; it disables no security machinery and carries no credential fixture.

**doc-reviewer**

- REQ-VET-003 anchor present at first mention and every system-design.md REQ-VET-003 reference resolves to a PRD requirement that exists
- system-design.md new Contracts rows (SpecialtyRepository, SpecialtyDirectoryEntry, SpecialtyController) hold to the per-contract budget: one purpose sentence, source pointer, Implements column — no field/parameter tables introduced
- the new invariant paragraph in system-design.md carries an inline ADR back-link as required
- the ADR (2026-08-24-read-model-derivation-in-value-types.md) follows the template exactly — Context/Options Considered/Decision/Consequences/Implementation/References, em-dash reference separators, Requirements: line in Implementation, and is genuinely load-bearing (a real deviation from the codebase's controller-logic habit, with alternatives assessed on real trade-offs)
- docs/adr/README.md index row added correctly with matching title and Accepted status
- the navigation-entry-point decision is correctly placed as an Open Question rather than a Non-Goals row — it is an explicitly deferred product decision with a named follow-up, not a permanent decline, and the entry records the fact without inventing rationale
- the read-only-scope decision correctly reuses the existing, unmodified NG-2 row rather than re-deriving a new non-goal
- the Veterinarian entry's new full name definition is consistent with its use in prd.md ("Helen Leary") and system-design.md, and does not conflict with any other ubiquitous-language.md entry

**test-reviewer**

- All 8 PRD-driven behaviors (every specialty on one page, first-then-last vet naming, multi-specialty holding, unspecialized-vet omission, unheld specialty listed with no marker, empty-directory render, stable ordering including last-name-tie-break by first name then id, untranslated stored names) have dedicated unit and/or web-slice tests, all passing (14/14 green, 100% line coverage on SpecialtyDirectoryEntry and SpecialtyController)
- Pyramid placement matches the brief's rationale: the five pure derivation behaviors are unit-tested over real Vet/Specialty objects with no framework context; only wiring, view name, as-stored rendering, and the unlinked-navigation check use @WebMvcTest, and no rule duplicates across layers
- Mocking policy fully honored: no Mockito/mock-framework import in either test file; SpecialtyControllerTests uses hand-written @TestConfiguration doubles (a lambda SpecialtyRepository, an anonymous VetRepository) plus MockMvc as the one sanctioned boundary mock
- BDD naming (the{Subject}Should{Outcome}) used consistently across all 14 test methods; three-tier data naming honored — DENTISTRY/RADIOLOGY/SURGERY and HELD_SPECIALTY/UNHELD_SPECIALTY are role-named Tier-1 constants, no bare mystery literals, ids generated via a counter or explicit factory args
- The cache-guard test (theSpecialtyDirectoryShouldLeaveTheCollectionsItReadsUntouched) is genuine, not decorative: it passes real mutable ArrayLists (mimicking the @Cacheable vets collection) rather than List.of(), so an in-place-sort regression would actually flip this test red; verified against the current stream().sorted() implementation, which never mutates its input
- The Specialty-id constraint from the design-block is honored: aSpecialtyNamed and aVeterinarianNumbered both assign ids before use, so every held-specialty match in the existing suite exercises the !isNew()==false path correctly
- Construction wrapped in factory methods (aSpecialtyNamed, aVeterinarianNamed/aVeterinarianNumbered, anEntryFor) in both files; whole-object comparison via containsExactly(anEntryFor(...)) rather than field-picking assertions
- AssertJ used throughout with no JUnit assertEquals/assertTrue; collection-aware assertions (containsExactly, containsExactlyInAnyOrder, flatExtracting, isEmpty) used appropriately

**code-quality-reviewer**

- SpecialtyDirectoryEntry.java:33 no longer declares  public ; grep across src/main and src/test confirms the only use site outside the declaring test files is SpecialtyController.java:42, which is in the same package, so the narrowed visibility introduces no compile break and matches the Minimal Surface rule this round-1 finding cited.
- Package-private SpecialtyDirectoryEntry is now consistent with its siblings SpecialtyController and VetController, resolving the inconsistency the round-1 finding raised.
- The accompanying test-reviewer fix (theSpecialtyDirectoryShouldNotMatchAnUnsavedSpecialtyToAStoredOne plus the anUnsavedSpecialtyNamed factory in SpecialtyDirectoryEntryTests.java) follows existing conventions in the file: BDD method name, factory method with a documenting Javadoc comment mirroring aSpecialtyNamed's style, AssertJ containsExactly assertion, no new mocking.
- ./gradlew checkFormat passes with no reformatting needed on the fix-delta files.
- No new public-surface, naming, or logging issues introduced in the fix-delta (docs/prd.md, docs/ubiquitous-language.md, SpecialtyDirectoryEntry.java, SpecialtyDirectoryEntryTests.java).

**security-reviewer**

- Round-2 verdict: APPROVED. The fix delta (docs/prd.md, docs/ubiquitous-language.md, SpecialtyDirectoryEntry.java, SpecialtyDirectoryEntryTests.java against prev_tree_sha 6b0618a) introduces no new security exposure, and every round-1 approved aspect still holds: SpecialtyController, SpecialtyRepository, and templates/vets/specialtyList.html are byte-identical to the surface I approved at line 17, so the output-escaping, injection, endpoint-exposure, and data-exposure findings need no re-derivation.
- Visibility narrowing (SpecialtyDirectoryEntry.java:33, public dropped): strictly reduces reachable API surface. The type is a read-model carrier with no security-relevant behavior, and narrowing it cannot widen any trust boundary. Only in-package callers exist (SpecialtyController plus the two same-package test classes), so no reflective or cross-package consumer is broken open. Least privilege applied, not weakened.
- Fail-closed guard, now verified behaviorally (SpecialtyDirectoryEntry.java:76,  !held.isNew() && held.getId().equals(specialty.getId()) ): identity matching is the safe outcome and the new test proves it. An unsaved held Specialty carrying the same NAME as a stored one does not match, so a name string can never cause a veterinarian to be published under a specialty they do not hold - the failure mode would have been an authorization-shaped over-disclosure (wrong association rendered as clinic fact), and the guard closes it. The short-circuit also keeps a null id off the  .equals  receiver, so no NullPointerException escapes into the request path; the inverse case (a stored specialty with a null id) is safe too, since  held.getId().equals(null)  returns false rather than throwing. Fail-closed on both axes: no spurious match, no 500.
- New test surface (theSpecialtyDirectoryShouldNotMatchAnUnsavedSpecialtyToAStoredOne, anUnsavedSpecialtyNamed): pure in-memory construction of real domain objects; no mock framework, no credential fixture, no security machinery disabled, no I/O, no network. It adds coverage of a security-relevant branch without adding attack surface.
- Secret sweep over the delta: grep for password secret token api key credential across all added lines returns no hits. No new logging statement, so no user-derived or sensitive value reaches a log sink.
- Supply chain: build.gradle, gradle/, and every dependency declaration are absent from the fix delta, so no dependency was added, removed, or version-bumped since round 1. The CVE surface is unchanged from the baseline I cleared at line 17; Spring Boot 4.1.0 and its managed Thymeleaf/Spring Data versions still stand.
- Documentation-only changes (prd.md narrative rephrased to drop the literal route, ubiquitous-language.md 'Specialty directory' entry, prd.md Design/ADR link line) carry no executable content and no security claim. Removing the literal path from PRD prose is not security-by-obscurity being relied on - docs/system-design.md still records the route and its unauthenticated exposure explicitly, so the documented threat model stays accurate.
- Class sweep across the whole delta for the classes I reason about (unescaped output, injection sink, secret literal, authz-shaped matching logic, dependency change) found no further instance beyond those assessed above.

**doc-reviewer**

- docs/ubiquitous-language.md now carries a "Specialty directory" entry directly after "Specialty", in the file's canonical format (one-sentence definition, Relationships, Avoid), correctly scoped to the domain concept rather than the SpecialtyDirectoryEntry type, and its Avoid line pre-empts the drift terms (Specialty list/page/index) the type-name coupling risked
- docs/prd.md:137 no longer embeds the literal route; the rephrased sentence ("reachable only by its own address: no navigation entry and no other page links to it") states the behavior without the mechanism value, and a repo-wide check confirms no other .html literal remains in prd.md
- the new Design/ADR links line under the Specialty directory section matches the Veterinarian directory pattern and both link targets resolve (system-design.md#contracts heading exists; the ADR file is present and indexed)
- product-owner decision preserved verbatim in substance: address-only reachability, no navigation entry, no inbound link, follow-up entry point remains an Open Question (not re-cast as a Non-Goal) — the Open Question list entry is unchanged content, only shifted in line number by the earlier insertion
- the declined Constants-section edit is sound: system-design.md's Constants section already states controller view-name/routing constants are deliberately excluded, consistent with every other controller (VetController, OwnerController, etc.) having no route literal listed there either, and the SpecialtyController Contracts row already documents the no-navigation-link fact the PRD's Design link points at
- no new prohibited-pattern instances introduced by the fix delta (no new hardcoded values, no new undefined terms) across the reviewed doc surface

**test-reviewer**

- Round-1 autofix (tested-as-spec, SpecialtyDirectoryEntryTests.java) fully resolved: theSpecialtyDirectoryShouldNotMatchAnUnsavedSpecialtyToAStoredOne (line 127) builds a Vet holding a Specialty with the same name as a stored one but no id (via the new anUnsavedSpecialtyNamed factory, which never calls setId), then asserts containsExactly(anEntryFor(RADIOLOGY)) — an entry with an empty veterinarian list. This is a genuine content assertion that Helen is excluded, not merely an absence-of-exception check, directly answering the round-1 concern that the prior suite proved no NPE but never proved non-match
- Branch coverage claim verified independently: ran ./gradlew test jacocoTestReport and inspected build/reports/jacoco/test/jacocoTestReport.xml directly. The lambda at SpecialtyDirectoryEntry.java:76 (lambda$holds$0) now shows BRANCH missed="0" covered="4", and the class-level rollup shows BRANCH missed="0" covered="4", LINE missed="0" covered="20" — 100% branch and line coverage, matching the implementer's report exactly
- Test methodology sound: the implementer's mutation-testing approach (temporarily deleting the  !held.isNew() &&  guard, observing the new test become the sole failure via NPE, restoring the guard) is a legitimate way to demonstrate the new test kills a real mutant of the fail-closed guard, distinct from and complementary to the branch-coverage evidence
- public modifier removal on  record SpecialtyDirectoryEntry  (line 33) verified safe: grep -F sweep across src/ confirms the type is referenced only from SpecialtyController.java and SpecialtyDirectoryEntryTests.java, both in the same org.springframework.samples.petclinic.vet package, so package-private visibility does not break any caller; full test suite (./gradlew test) passes with this change in place, confirming tests assert against real behavior post-change, not a broken build papered over
- New test follows the suite's established conventions: four-phase structure with blank-line separation, BDD name (theSpecialtyDirectoryShouldNotMatchAnUnsavedSpecialtyToAStoredOne), reuses the anEntryFor/aSpecialtyNamed factories, adds a well-documented anUnsavedSpecialtyNamed factory (Javadoc explains why it omits the id), AssertJ containsExactly used consistent with sibling tests — no regression in test data naming or structure
- Class-exhaustive sweep for the isNew() pattern across src/main and src/test found no other untested short-circuit guard of this shape introduced by this delta; the only other isNew() call sites are pre-existing owner-package code untouched by this slice

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 3 | opus-5 | $4.16 | 14m 7s | 95% |
| `spring-boot-claude:system-design-expert` | 2 | opus-5 | $2.88 | 7m 55s | 93% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-5 | $1.64 | 4m 39s | 90% |
| `(parent)` | 1 | opus-5 | $1.63 | 40m 46s | 94% |
| `spring-boot-claude:change-grader` | 1 | opus-5 | $1.22 | 3m 42s | 94% |
| `spring-boot-claude:security-reviewer` | 2 | opus-5 | $1.03 | 2m 10s | 86% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-5 | $0.80 | 4m 38s | 92% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-5 | $0.70 | 2m 52s | 91% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-5 | $0.44 | 2m 4s | 89% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-5 | $0.06 | 9s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-5 | $2.86 | 9m 56s | 96% |
| `spring-boot-claude:system-design-expert` | opus-5 | $2.26 | 6m 20s | 95% |
| `(parent)` | opus-5 | $1.63 | 40m 46s | 94% |
| `spring-boot-claude:change-grader` | opus-5 | $1.22 | 3m 42s | 94% |
| `spring-boot-claude:feature-implementer` | opus-5 | $0.91 | 3m 1s | 94% |
| `spring-boot-claude:product-requirements-expert` | opus-5 | $0.83 | 2m 30s | 90% |
| `spring-boot-claude:product-requirements-expert` | opus-5 | $0.81 | 2m 8s | 91% |
| `spring-boot-claude:system-design-expert` | opus-5 | $0.62 | 1m 35s | 84% |
| `spring-boot-claude:security-reviewer` | opus-5 | $0.56 | 1m 21s | 88% |
| `spring-boot-claude:doc-reviewer` | sonnet-5 | $0.48 | 2m 1s | 91% |
| `spring-boot-claude:security-reviewer` | opus-5 | $0.47 | 48s | 83% |
| `spring-boot-claude:test-reviewer` | sonnet-5 | $0.46 | 2m 52s | 92% |
| `spring-boot-claude:feature-implementer` | opus-5 | $0.39 | 1m 9s | 92% |
| `spring-boot-claude:test-reviewer` | sonnet-5 | $0.34 | 1m 46s | 93% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-5 | $0.29 | 1m 35s | 92% |
| `spring-boot-claude:doc-reviewer` | sonnet-5 | $0.22 | 50s | 91% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-5 | $0.15 | 29s | 83% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-5 | $0.06 | 9s | 50% |

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

- plugin `spring-boot-claude` at `v0.1.29` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
