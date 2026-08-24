# specialty-directory r3 — v0.2.1

Specialty directory page (feature) · started 2026-08-24T19:08:37+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 4 (±0) | 4 (±1) | 4 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.60. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> SpecialtyDirectory keeps pairing and ordering out of the controller — showSpecialtyDirectory only delegates — and the ADR justifies the derived read model. But SpecialtyRepository adds a repository for a non-aggregate-root, and its @Query ORDER BY duplicates BY_NAME_THEN_ID in the record. No message-bundle entries accompany #{specialties} and #{none} in specialtyList.html, yet the new REQ-VET-003 done-when asserts every piece of wording exists in each language; the controller test's containsString("none") would pass even on an unresolved key, as would the trailing-space concatenation in the vet span go unchecked. Unit tests are behavior-named and factory-built with generated ids, but repeatedly index entries().get(0)/get(1) rather than using collection-aware assertions, and SpecialtyRepository is stubbed via @MockitoBean without a stated exception.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> SpecialtyDirectory.of pulls the pairing into an immutable, framework-free record with a narrow read-only SpecialtyRepository (Repository base, single @Query findAll), so the controller method showSpecialtyDirectory only binds and delegates — the right seams, and the unit tests sit at the pyramid base. Two structural quibbles: the new route hangs off VetController rather than a specialty-named controller, and specialtyList.html references #{specialties}, #{name}, #{vets}, #{none} while no message bundle is added — the containsString("none") assertion still passes against Thymeleaf's ??none_en?? placeholder, so the gap is untested despite the PRD done-when claiming every wording exists in each language. Tests are behavior-named with anonymous factories, but repeatedly index via entries().get(0) instead of collection-aware assertions.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 3 · doc-fit 5

> SpecialtyDirectory keeps the pairing out of the controller and unit-testable, matching layer respect; the narrow Repository base honors NG-2. Two quibbles: /specialties.html hangs off VetController rather than a specialty-prefixed controller, and ordering is specified twice (SpecialtyRepository's ORDER BY plus BY_NAME_THEN_ID). Tests are behavior-named, factory-built, mock-free and phase-separated, but lean on index access (entries().get(0), get(1)) instead of collection-aware assertions, and use bare literals ('radiology', 'Helen Leary'). specialtyList.html introduces #{specialties} and #{none} with no message-bundle entry in the patch, so wording may render as ??none_en??; the containsString("none") assertion would still pass. The trailing-space span concatenation is fragile. Documentation — PRD, ubiquitous-language, system-design, ADR and index — is fully current.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.46 | 32m | 31 | 92% | 11 file(s) +495/−8 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.97 | 2m 56s | 91% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · **1 build-failure** · grade **CONCERN**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** (1) | · |

- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 9m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · ***◷ 44s***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · format · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 52s***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · (1 finding) · ***◷ 1m***
  - **[escalate]** `CLAUDE.md:45-46,67` CLAUDE.md's Build Commands table and Quality Gate paragraph name `./gradlew formatJava` and `./gradlew checkJavaFormat`; the real Gradle tasks are `format` and `checkFormat` (confirmed by the build-failure record at handoff.jsonl line 6 and by scripts/layout.toml:122, which also invokes `checkJavaFormat`). This is pre-existing drift untouched by the REQ-VET-003 diff — CLAUDE.md is not in this changeset — so it does not block this slice. It belongs in a separate slice: a doc/tooling fix touching CLAUDE.md and scripts/layout.toml together, since layout.toml's quality-gate command carries the same wrong task name.
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `SpecialtyDirectoryTests.java:59-136` The `specialty(id, name)` and `vet(id, first, last, specialties...)` factories require an explicit id at every call site. In five of the seven tests (everything but theSpecialtyDirectoryShouldOrderSpecialtiesByNameThenIdentity and theSpecialtyDirectoryShouldOrderVeterinariansByLastNameThenFirstName) the id has no bearing on the assertion made — it exists only to give the entity a unique identity — yet it is a bare int literal with no SOME_/ANY_ naming and no auto-generation. This is a new file (2026-08-24), so testing-principles.md's Three-Tier Data Naming and Anonymous Factories sections apply in full; the id is Tier 2 (irrelevant) in those five tests but is named/constructed like a Tier 1 value.
    - fix: Add anonymous-factory overloads that auto-generate a unique id via an internal counter (e.g. specialty(String name), vet(String first, String last, Specialty... specialties)) and use them wherever the id does not drive the assertion; keep the explicit-id overload only for the two ordering tests, where the id is genuinely meaningful.
  - [clarify] `VetControllerTests.java:58-59` VetControllerTests adds @MockitoBean SpecialtyRepository alongside the pre-existing @MockitoBean VetRepository. Judged on the merits: this is defensible, not a defect. testing-principles.md sanctions exactly one mock point (the in-process web test harness standing in for HTTP transport) and treats Mockito stubs of internal collaborators as tolerated-not-encouraged debt that 'may stay' on existing tests, while directing new tests to reach for a real implementation or hand-written double first. VetControllerTests is a @WebMvcTest slice with no persistence context wired, so no real SpecialtyRepository is available, and while a hand-written fake was feasible (the interface exposes one findAll() method), matching the neighboring, already-grandfathered VetRepository mock keeps this test class internally consistent rather than mixing a real fake with a Mockito stub on the same slice. This slice should make no change here. The brief itself is silent on whether a @WebMvcTest's sliced-out repository beans count as the sanctioned web-harness boundary or as 'internal code' a new test must fake by hand -- that gap should be closed in testing-principles.md so the next @WebMvcTest addition has a documented answer instead of a per-slice judgment call.
- ↻ **implement** (implementer) ← test · (2 findings) · ***◷ 2m***
  - ▲ **build ✓ clean** · build · test · format · handoff-log · autofix-audit
- ↻ **fix design** ← test · (2 findings)
- ↳ consult **design** → **human** · Please apply the amendment below to docs/testing-principles.md, and confirm the CLAUDE.md follow-up. DECISION. A framework slice test's excluded beans are boundary substitutions, not internal mocks. Grounding: docs/architecture-principles.md names the repository 'the default persistence boundary' (Building Blocks table), so a repository sits on the sanctioned side of the brief's mock-only-at-system-boundaries rule. The rule does not rest on how wide the interface is -- SpecialtyRepository exposes one findAll(), so a hand-written fake was feasible here, and the rule still permits the stub. What it rests on is where the boundary sits. PROPOSED TEXT for docs/testing-principles.md, section 'Mocking Policy'. Insert after the paragraph beginning 'Mock-framework stubs are tolerated, not encouraged.' and before the paragraph beginning 'If a test needs more lines of setup than assertion': ----- begin ----- **A framework slice test's excluded beans are boundary substitutions, not internal mocks.** A web-slice test loads the web layer alone, so the persistence gateways its subject depends on cannot be real. `architecture-principles.md` names the repository the default persistence boundary, which puts those beans on the sanctioned side of the mock-only-at-boundaries rule. A new slice test may stand them in with the framework's bean-override stub, and owes no exception rationale for doing so. Two bounds hold: | Bound | Rule | |-------|------| | **Supply data, never behavior** | A stub returns fixture data. A stub that encodes a rule the production code owns -- ordering, filtering, derivation -- moves the specification into the test. That rule gets a unit test on the type that owns it. | | **One style per class** | A test class substitutes all of its excluded beans the same way. Mixing a hand-written fake and a framework stub across one slice costs more than either choice saves. | Outside a slice test the hierarchy is unchanged: real implementation first, hand-written double next, framework stub as a conscious exception. The project's `CLAUDE.md` names the concrete slice annotation and stub mechanism for this stack. ----- end ----- The text is deliberately stack-neutral, matching the brief's opening rule that the principles are language-agnostic and the concrete harness is named in CLAUDE.md (the same delegation the existing 'one sanctioned mock' paragraph uses). Applied to the finding: VetControllerTests's @MockitoBean SpecialtyRepository is permitted outright under this rule, not a tolerated exception. Both bounds hold there -- the stub returns fixture specialties and encodes no ordering (SpecialtyDirectory owns ordering and is unit-tested for it), and the class now substitutes both excluded repositories the same way. CLAUDE.md: YES, a correction is required, and NO, it does not belong in this slice. Why required: CLAUDE.md:60 reads '**No mocks**: All tests use real value objects and real I/O. No Mockito or mock libraries.' That is already false today -- VetControllerTests has carried @MockitoBean VetRepository since before this slice, and testing-principles.md sanctions the web harness and tolerates existing framework stubs. My rule widens the contradiction from tolerating old stubs to permitting new ones, which CLAUDE.md:60 flatly forbids. Two edits: (1) replace the flat 'No mocks' claim with a pointer to the brief's hierarchy (real first, hand-written double next, framework stub at a boundary or as a conscious exception); (2) name the concrete mechanisms for this stack -- MockMvc/@WebMvcTest as the sanctioned harness and @MockitoBean as the bean-override stub -- which testing-principles.md explicitly delegates to CLAUDE.md and which is missing there today. Why a separate slice: CLAUDE.md is outside my write scope and outside the REQ-VET-003 changeset. The doc-reviewer already routed a CLAUDE.md drift finding to a separate slice on identical reasoning (handoff.jsonl line 18: the Build Commands table and Quality Gate name formatJava/checkJavaFormat where the real tasks are format/checkFormat, shared with scripts/layout.toml:122). Fold both into one CLAUDE.md-accuracy slice, sequenced after the brief amendment lands so the stack-specific text has a brief rule to point at.
- ✔ **review test** · **approved** · ***◷ 39s***
- ◆ **grade CONCERN** · add the read-only specialty directory
  - blast_radius — **clear** — Eleven files but almost entirely additive: two new prod classes, one new template, one new test class, and docs. The only edit to existing production code is VetController gaining a SpecialtyRepository constructor argument and a third GET handler; the class is package-private with exactly one Spring construction site and one slice test, no sensitive paths, and no existing route or query is touched.
  - semantic_surprise — **clear** — Read every prod hunk against the documented behavior and found no divergence: specialties are matched to vets by getId() through a locally built HashMap rather than by name or object identity, which is what keeps two same-named specialties separate; both record constructors List.copyOf their component; sorting goes through stream().sorted() so the shared cached vets collection is never sorted in place; the JPQL is a constant with no parameters; and the template mirrors vetList.html with th:text on every value. The one footnote is pre-existing rather than new: vets come from the eviction-less vets cache while specialties come from a fresh query, so the new page inherits the same staleness window /vets.html already has.
  - test_adequacy — **clear** — Tests are real rather than tautological, and build_passed is true. SpecialtyDirectoryTests drives the model with real Specialty and Vet objects across every PRD edge case and both ordering rules, and VetControllerTests renders the actual page and asserts on its content, including a negative assertion that a specialty-less vet appears nowhere. Notably helen() holds a radiology instance distinct from the one the specialty repository returns but sharing its id, so the cross-source identity-matching risk the design flagged is genuinely exercised rather than assumed. JPQL validity is covered by the full-context SpringBootTest bootstraps, though no end-to-end test walks /specialties.html against a real database.
  - reviewer_hedging — **concern** — All four dispatched reviewers approved, but two approvals carry caveats the protocol counts as hedges. The doc-reviewer's approval carries an escalate-tagged finding on stale Gradle task names in CLAUDE.md and scripts/layout.toml, and the test-reviewer approved only in round 2 after a bar_clause-flagged autofix finding was reworked, a rework that traded a positional assertion for containsExactlyInAnyOrder in theSpecialtyDirectoryShouldKeepSameNamedSpecialtiesAsSeparateEntries. Separately, an unanswered human consultation asks to amend docs/testing-principles.md to sanction the MockitoBean SpecialtyRepository this diff adds, and until it lands CLAUDE.md's literal no-mocks rule stands contradicted by merged test code.
  - scope_deviation — **clear** — Zero design revisions, zero build retries, and one consultation that is about a brief gap rather than the requirement. The diff stays inside the PRD surface exactly: no navigation entry, no link from another page, no page parameter, no write path, and no new message keys, with the three unresolved product questions parked in PRD Open Questions rather than decided in code. The docs widen slightly past the slice with a general post-survey provenance rule and a Veterinarian directory vocabulary term for the pre-existing page, both of which the doc-reviewer approved as needed to name the inverse view.
  - why — The code reads clean and the tests genuinely exercise the id-matching and ordering boundaries. What deserves your eye is not the diff but the paperwork around it: confirm the testing-principles amendment before this mock-bean test lands under a CLAUDE.md that still forbids mocks, and note the escalated stale Gradle task names.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Output escaping: specialtyList.html renders every data-derived value through th:text (entry.specialty.name, vet.firstName/lastName) and static labels through th:text=#{...}; no th:utext, th:inline, th:onclick, javascript: URL, or th:href/th:src carrying user data anywhere in the new template. A grep sweep of the whole templates tree confirms no unescaped-output construct was introduced by this slice, so the Thymeleaf-default escaping mitigation in docs/system-design.md#threat-model still holds unbroken.
- JPQL construction: SpecialtyRepository.findAll uses a single compile-time constant @Query string with no parameters, no bind variables, no SPEL and no concatenation; the ORDER BY targets fixed entity properties, not a caller-supplied sort key. No injection sink exists on the new read path, and the handler takes no request parameters at all (no @RequestParam, @PathVariable, @RequestBody, or Model attribute binding), so there is no attacker-controlled input reaching the query.
- Cache safety: SpecialtyDirectory.of only reads the @Cacheable("vets") collection. It iterates the collection and each Vet.getSpecialties() without calling any mutator, accumulates into locally allocated HashMap/ArrayList, and both record constructors defensively List.copyOf their component. No sort-in-place on the shared list (stream().sorted() copies), no add/remove/clear against the cached collection or against any Specialty/Vet entity, so no cross-request poisoning of the shared cache entry is reachable through this path.
- Exposure surface: GET /specialties.html serves the identical vet-and-specialty dataset already published unauthenticated by the existing /vets.html and /vets routes. It adds no new class of data to the unauthenticated surface and no new mutating route. The absence of authentication is a pre-existing, documented posture (docs/system-design.md#security-context), not something this change alters; per the review contract, pre-existing concerns are not re-raised here.
- Supply chain and configuration: the change set touches no build file, no properties file, no actuator or datasource configuration, and adds no dependency, so no new CVE surface enters the tree and no dependency-resolution check applies to this slice. A sweep of the added lines for credential-shaped material (password, secret, token, api key, credential) returns nothing; the new code holds no literal values beyond JPQL identifiers and message-bundle keys.

**code-quality-reviewer**

- SpecialtyDirectory and its nested Entry record are immutable value objects with defensive List.copyOf() in their compact constructors, matching the value-object rule in docs/architecture-principles.md
- Naming matches docs/ubiquitous-language.md: 'Specialty directory' and per-specialty 'entry' are the recorded terms; no prohibited suffixes (Manager/Helper/Utility/Handler/Processor/Base/Info/Data) appear on any new type
- SpecialtyRepository correctly extends the narrow Repository base (not JpaRepository) with rationale documented in its Javadoc, matching PetTypeRepository's lookup-entity pattern and NG-2
- Matching is by getId() throughout (holdersBySpecialtyId keyed by Integer id), never by object identity or name, avoiding the BaseEntity equals/hashCode pitfall flagged in the design-block risks
- VetController's new handler follows the established handler shape: binds nothing, delegates to the read model, selects a view, no business rule added to the controller
- specialtyList.html mirrors vetList.html's structure (layout fragment call, th:text on every visible string, #{none} for empty holders, shared message keys) with no new i18n keys introduced, avoiding the eleven-bundle sync risk
- checkFormat (google-java-format equivalent; checkJavaFormat task does not exist under this Gradle config, checkFormat is) passes clean on the full change set
- Javadoc throughout is accurate, contextual, and cross-references the ADR rather than duplicating its reasoning
- No mutation of the shared vets cache or its Vet instances anywhere in SpecialtyDirectory.of

**doc-reviewer**

- PRD/system-design boundary honored: the /specialties.html route, ordering mechanism, and identity-matching detail live only in system-design.md; docs/prd.md states the capability behaviorally ("reached by its own address alone") with no literal route or mechanism leak
- REQ-VET-003 anchor, Done-when bullets, and edge cases are present and each ID appears in a bullet
- Deferred entry-point question correctly recorded in PRD Open Questions rather than smuggled into the Non-Goals table as a new NG row, matching the settled decision that it stays an open question
- docs/ubiquitous-language.md gains Specialty directory, Veterinarian directory, and Full name with correct (added 2026-08-24) provenance marks, one-sentence definitions, and Relationships/Avoid lines
- docs/system-design.md Contracts table and prose are consistent: new SpecialtyRepository and SpecialtyDirectory rows, updated VetController row listing all three routes, and an explicit ordering-guarantee paragraph, all citing REQ-VET-003
- New ADR is well-formed: em-dash references, Requirements: REQ-VET-003 in Implementation, Status Accepted, and correctly indexed in docs/adr/README.md's table
- All cross-document links checked resolve: prd.md#req-vet-003 anchor exists, system-design.md#contracts anchor exists, ADR links to system-design.md#contracts and to testing-principles.md#test-pyramid and architecture-principles.md#scoped-exception-framework-mapped-persistence-entities all resolve to real headings
- PRD provenance amendment cleanly distinguishes the new (decided \<date>) mark from the bootstrap-survey provisional framing, and REQ-VET-003's prose carries the (decided 2026-08-24) mark consistently with that amendment

**test-reviewer**

- All six PRD-mandated test_names present and correctly split across the pyramid: the four pure data-shape behaviors sit in SpecialtyDirectoryTests (no mocks, real Specialty/Vet objects), the two rendering behaviors sit in VetControllerTests against the actual rendered page
- SpecialtyDirectoryTests also covers same-named-specialties-stay-separate and both stated ordering rules (specialty by name-then-id, vet by last-then-first-then-id), exceeding the required minimum
- ./gradlew test passes clean; JaCoCo reports 100% instruction and branch coverage on SpecialtyDirectory, SpecialtyDirectory.Entry, and VetController
- AssertJ used throughout with chained fluent assertions; BDD the{Subject}Should{Outcome} naming followed exactly; four-phase structure with blank-line separation and no phase comments or narration
- Derived-expectation discipline honored: fullNamesOf/specialtyNamesOf helpers build expected shapes from the same inputs the test constructs, no hard-coded magic strings for computed output
- Construction wrapped in specialty()/vet() factory methods rather than raw constructors, satisfying the Factory Methods rule

**test-reviewer**

- Autofix finding resolved: specialty(String) and vet(String,String,Specialty...) anonymous-factory overloads auto-generate ids via a shared AtomicInteger; explicit-id overloads survive with javadoc restricting them to tests where identity drives the assertion, and are used only in the two ordering tests (theSpecialtyDirectoryShouldOrderSpecialtiesByNameThenIdentity: ids 3/4/2; theSpecialtyDirectoryShouldOrderVeterinariansByLastNameThenFirstName: vet ids 1/2/3) where the ids are genuinely Tier-1 meaningful
- Deviation on theSpecialtyDirectoryShouldKeepSameNamedSpecialtiesAsSeparateEntries is the right call: the prior positional assertion (entries().get(0)==Helen) was silently riding the id tie-break rather than testing 'separate entries', so handing it generated ids without changing the assertion would have made the test flaky-by-accident; the new containsExactlyInAnyOrder assertion still proves two distinct un-merged entries (via specialtyNamesOf containsExactly("dentistry","dentistry")) each holding exactly one vet, which is the full content of the 'stay separate' claim, and correctly drops only the ordering claim that theSpecialtyDirectoryShouldOrderSpecialtiesByNameThenIdentity already owns and pins with explicit ids 2/4/3 -- no coverage gap opened
- Swept the full file for remaining anonymous-id/positional-assertion coupling: theSpecialtyDirectoryShouldListEverySpecialtyByStoredName and theSpecialtyDirectoryShouldListASpecialtyNoVeterinarianHolds differentiate their two entries by specialty name (radiology vs surgery), not id, so anonymous ids there are safe; no other instances of the class found
- clarify finding on VetControllerTests's @MockitoBean SpecialtyRepository correctly left unactioned in this slice per my round-1 conclusion, and routed to system-design-expert for the brief gap -- not reopened here
- ./gradlew test green for SpecialtyDirectoryTests and VetControllerTests; no production code touched in the fix round

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $3.52 | 14m 15s | 96% |
| `agent-team:system-design-expert` | 3 | opus-5 | $3.07 | 9m 34s | 91% |
| `(parent)` | 1 | opus-5 | $1.59 | 35m 10s | 95% |
| `agent-team:change-grader` | 1 | opus-5 | $0.97 | 2m 56s | 91% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $0.96 | 3m 29s | 91% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.55 | 3m 20s | 90% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.46 | 1m 0s | 83% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.37 | 1m 53s | 92% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.29 | 1m 23s | 91% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.06 | 8s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $2.17 | 9m 16s | 97% |
| `(parent)` | opus-5 | $1.59 | 35m 10s | 95% |
| `agent-team:system-design-expert` | opus-5 | $1.55 | 4m 35s | 93% |
| `agent-team:system-design-expert` | opus-5 | $1.04 | 3m 32s | 88% |
| `agent-team:change-grader` | opus-5 | $0.97 | 2m 56s | 91% |
| `agent-team:product-requirements-expert` | opus-5 | $0.96 | 3m 29s | 91% |
| `agent-team:feature-implementer` | opus-5 | $0.79 | 3m 8s | 94% |
| `agent-team:feature-implementer` | opus-5 | $0.55 | 1m 50s | 93% |
| `agent-team:system-design-expert` | opus-5 | $0.49 | 1m 26s | 86% |
| `agent-team:security-reviewer` | opus-5 | $0.46 | 1m 0s | 83% |
| `agent-team:test-reviewer` | sonnet-5 | $0.43 | 2m 33s | 91% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.37 | 1m 53s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.29 | 1m 23s | 91% |
| `agent-team:test-reviewer` | sonnet-5 | $0.12 | 47s | 88% |
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

- plugin `agent-team-spring-boot` at `v0.2.1` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
