# specialty-directory r2 — v0.3.1

Specialty directory page (feature) · started 2026-08-15T00:52:04+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 4 (±0) | 4 (±1) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.99. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController is thin (delegates to SpecialtyDirectory.of, no rule), and SpecialtyDirectory is immutable, defensively copied, equal by value, and free of framework types — a good fit. Two frictions: it matches no catalog pattern ("derived read model") yet no ADR accompanies it, and ordering is stated twice (SpecialtyRepository's ORDER BY specialty.name plus BY_SPECIALTY_NAME). specialtyList.html introduces #{none} (and #{specialties}) with no message-bundle change, leaving the PRD's own language done-when unmet. Tests are behavior-named, four-phase, factory-built, and use hand-written stubs (StubVetRepository) over a mock framework — strong; but theSiteNavigationShouldNotLeadToTheSpecialtyDirectory only inspects the directory page itself, so it cannot detect a link elsewhere, and the static Vet/Specialty fixtures are shared mutable entities. Docs: prd.md NG-10, requirement, open question, and three system-design rows all land.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Grouping sits in an immutable read model (SpecialtyDirectory.of), leaving SpecialtyController.showSpecialtyDirectory thin and framework-free to unit test — right layer, no controller rule. But ordering is enforced twice (SpecialtyRepository's ORDER BY specialty.name plus BY_SPECIALTY_NAME), and Entry's hand-rolled equals/hashCode is exercised only by its own tests; a record would remove ~30 lines. Tests are behavior-named, four-phase, factory-built, with hand-written stubs and no mock framework. Two weaknesses: theSiteNavigationShouldNotLeadToTheSpecialtyDirectory inspects only the directory page, overclaiming the PRD's 'any page' clause; SpecialtyControllerTests' static Specialty/Vet fixtures are shared mutable entities. Docs move fully: PRD context, NG-10, REQ-SPECIALTYDIRECTORY-001, the ordering open question, and three system-design contract rows.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 3 · doc-fit 5

> Layering is right: SpecialtyController.showSpecialtyDirectory only binds and delegates, grouping lives in the immutable SpecialtyDirectory read model, and SpecialtyRepository follows the repository pattern — so the rule is unit-testable (SpecialtyDirectoryTests) rather than added to a controller. Tests are behavior-named, four-phase, use test-owned factories and hand-written stub repositories instead of a mock framework; deductions: SpecialtyControllerTests shares mutable static Vet/Specialty fixtures, and theSiteNavigationShouldNotLeadToTheSpecialtyDirectory only inspects the specialty page itself. Maintainability suffers from equals/hashCode over Specialty/Vet, which define no value equality, making the contract near-useless dead weight, and specialtyList.html introduces #{specialties}/#{none} keys with no message bundle in the patch — NONE_WORDING="none" still matches a "??none_en??" fallback. Docs are fully current.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $12.03 | 32m | 28 | 94% | 8 file(s) +658/−3 |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPECIALTYDIRECTORY-001 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · no grade yet

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (1) | **✔** |
| **test** | **✔** | ✎ (1) |
| **security** | **✔** | **✔** |
| **doc** | **✔** | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **new** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 9m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [autofix] `SpecialtyDirectory.java:38-119` SpecialtyDirectory and its nested Entry are the codebase's first non-persisted value objects and are explicitly outside the persistence-entity exception (per the design-block's own risk note: 'the new non-entity type is not covered by it and must meet the value-object row in full'). architecture-principles.md's Value object row requires 'equality by value'. Neither class overrides equals()/hashCode(), so two directories or entries built from the same data compare unequal by reference identity — a trap for the next reader who asserts on a returned SpecialtyDirectory/Entry directly (the existing tests avoid it only by extracting names/lists first) or who reuses either class as a map/set key.
    - fix: Add value-based equals()/hashCode() to SpecialtyDirectory (over entries) and to Entry (over specialty and veterinarians), or convert both to records if their fields can be exposed as canonical record components without breaking the Javadoc-documented immutability guarantees already in place.
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain not verified against the NVD in this review: build.gradle is unchanged (the diff adds no dependency and no repository), the OWASP dependency-check plugin is not configured in this project, and the reviewer has no network access. The resolved Spring Boot 4.1.0 / Jackson set should be closed out by CI or a human against the NVD — this is a standing gap in the project's tooling, not a defect introduced by this change.
- ✔ **review test** · **approved** · ***◷ 2m***
- ✔ **review doc** · **approved** · ***◷ 2m***
- ↻ **implement** (implementer) ← code-quality · (1 finding) · ***◷ 3m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit
- ✔ **review security** · **approved** · ***◷ 28s***
  - ▹ rec: Supply chain remains unverified against the NVD in this round, as in round 1: build.gradle is unchanged (the delta adds no dependency and no repository), the OWASP dependency-check plugin is not configured, and this reviewer has no network access. Treat the Spring Boot 4.1.0 / Jackson CVE check as not run, to be closed by CI or a human rather than assumed clean.
- ✔ **review code-quality** · **approved** · ***◷ 37s***
- ✔ **review doc** · **approved**
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [autofix] `SpecialtyDirectoryTests.java:121-155` The round-1 fix added equals()/hashCode() to SpecialtyDirectory and Entry (the value-object finding), but the new tests only cover the equal-and-unequal-content cases for SpecialtyDirectory and the equal case for Entry. Jacoco confirms the gap: SpecialtyDirectory.java lines 100 (`this == other` self-equality branch) and 103 (`!(other instanceof SpecialtyDirectory)` type-mismatch/null branch) are both fully uncovered (nc), and the same two branches in Entry.equals (lines 148, 151) are uncovered too. Nothing exercises equals(null), equals(an object of another type), or the reflexive `x.equals(x)` case for either class, and Entry has no not-equal counterpart to the Directory-level theSpecialtyDirectoryShouldNotEqualADirectoryOverAnotherSpecialty test. A future edit that breaks null-safety or drops the reflexive shortcut in either equals() would pass every test in this file.
    - fix: Add, for both SpecialtyDirectory and Entry: a self-equality assertion (assertThat(x).isEqualTo(x)), an assertThat(x).isNotEqualTo(null), an assertThat(x).isNotEqualTo(anUnrelatedObject) (e.g. a String), and — mirroring the existing Directory-level negative test — an Entry-level not-equal case (e.g. same specialty, different veterinarians, or a different specialty).

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyController, SpecialtyRepository, and SpecialtyDirectory closely mirror the codebase's existing VisitController/PetTypeRepository/Vet.getSpecialties() idioms cited in the design-block, including Javadoc style, defensive copies, and Comparator construction
- specialtyList.html reuses the existing #{specialties}/#{name}/#{vets}/#{none} message keys verbatim, avoiding the I18nPropertiesSyncTest risk the design-block flagged
- No System.out/err, no swallowed exceptions, no blanket catch, no logging needed in this slice, and checkFormat passes clean
- Stable ordering (specialty name, then veterinarian last/first name) is implemented once in SpecialtyDirectory rather than duplicated in the template

**security-reviewer**

- XSS: every user-derived value on src/main/resources/templates/vets/specialtyList.html renders through th:text (escaped by default). No th:utext anywhere in templates, no inline JavaScript, no external resource loading, and no Thymeleaf preprocessing (__${...}__) on any request-derived value — the new page takes no request input at all. Matches the vetList.html precedent line for line (Pattern Consistency).
- Injection into data access: SpecialtyRepository.findAll uses a static JPQL @Query with no parameters and no concatenation ('SELECT specialty FROM Specialty specialty ORDER BY specialty.name'); VetRepository.findAll is the existing derived query. No request-derived value reaches any query.
- Widening the exposed surface: GET /specialties.html is read-only, takes no path variable, query parameter, or body, and mutates nothing. No management-endpoint exposure changed, no application*.properties touched. The route is no weaker than the documented baseline in docs/system-design.md § Security Context.
- Mass assignment: SpecialtyController binds no request data — no @ModelAttribute, no form-backed type, no @InitBinder needed. Nothing new is request-bound, so the identifier-disallow rule has no surface here.
- Secrets: no credential, token, key, or connection string in the diff; a case-insensitive sweep for password/secret/token/apikey/credential over the new production, template, and test files returns nothing. No new committed default of any kind.
- Path traversal / resource resolution: no filesystem or classpath path is composed anywhere in the change; the view name 'vets/specialtyList' is a compile-time constant.
- Deserialization: no Jackson polymorphic typing, no @JsonTypeInfo, no Java serialization, no new PetClinicRuntimeHints entry. The page renders server-side HTML only.
- Concurrency: SpecialtyController is a singleton holding only two final repository references. SpecialtyDirectory is built per request and structurally immutable (private constructor, stream .toList() and List.copyOf, no setters), so the shared-mutable-state class is absent. It reads the @Cacheable("vets") collection without mutating it — .stream().sorted() leaves the cached instance untouched, so no request can corrupt the shared cache for later ones.
- Error handling and disclosure: no new catch block, no exception message, no logging statement, so nothing new can leak internal detail into the error page that renders exception messages.
- Resource allocation: the unpaged full-collection read matches the existing unauthenticated baseline (VetController.java:70 already calls the unpaged vetRepository.findAll()), the result size is bounded by clinic data with no request-controlled multiplier, and no file handle or stream is opened.
- Null-safety at the boundary: SpecialtyDirectory.of applies Objects.requireNonNull to both collections and null-safe comparators, so malformed data degrades to an ordering rather than an NPE reaching the error page.

**test-reviewer**

- SpecialtyDirectoryTests is a genuine unit test (no Spring context) covering the grouping logic in isolation, moving the pyramid toward the brief's ~80% unit target as testing-principles.md asks when logic moves
- SpecialtyControllerTests uses a hand-written stub VetRepository/SpecialtyRepository instead of Mockito, matching the brief's real-implementation-first mocking policy and the design's stated risk mitigation
- Every PRD acceptance criterion for REQ-SPECIALTYDIRECTORY-001 has a dedicated test: one-page listing, full-name ordering (first then last), omission of specialty-less vets, multi-specialty membership, specialty-held-by-none, stable ordering (verified via a reverse-input test), and no-navigation-link (correctly caught through the shared layout fragment rendered inside the specialties page itself, since layout.html is common to every page)
- Defensive-copy immutability of SpecialtyDirectory is explicitly tested (theSpecialtyDirectoryShouldNotChangeWhenTheCollectionsItWasBuiltFromChange), covering the design's noted value-object risk
- 100% instruction coverage on SpecialtyController, SpecialtyDirectory, and SpecialtyDirectory.Entry per the jacoco report; all new production code is exercised by real behavior, not just touched
- Three-tier data naming is followed throughout: role-named constants (DENTISTRY, HELEN_LEARY) for meaningful data, no bare mystery literals, factory methods (createASpecialty, createAVet) wrap construction instead of raw constructors
- AssertJ used in the pure unit test class; MockMvc/Hamcrest matchers used idiomatically in the web-slice test, consistent with the existing VetControllerTests convention
- BDD test naming (the{Subject}Should{Outcome}) followed consistently across both new files
- All 13 new/changed tests pass under ./gradlew test with no skips

**doc-reviewer**

- New REQ-SPECIALTYDIRECTORY-001 section in docs/prd.md stays behavioral throughout — no mechanism, code element, or constant leaks in; the paragraph and every Done-when bullet read as pure outcome statements
- Anchor \<a id="req-specialtydirectory-001">\</a> present and correctly hyphenated; REQ-SPECIALTYDIRECTORY-001 tag usage is consistent across prd.md and system-design.md, and the #contracts Design link resolves
- New NG-10 Non-Goals row follows the existing table's Rationale-column precedent and needed no scope_overrides entry, correctly, since it adds a row rather than changing one
- docs/system-design.md Contracts table additions (SpecialtyRepository, SpecialtyDirectory, SpecialtyController) stay at purpose-plus-source-pointer altitude, matching the existing table rows with no field/parameter tables or constant literals introduced
- Verified system-design.md's factual claims against source: SpecialtyRepository.findAll() carries no @Cacheable annotation, matching the documented 'results are not cached'; SpecialtyController's route and template reuse existing message keys (#{specialties}, #{name}, #{vets}, #{none}) as the design's i18n risk mitigation specified, avoiding a new key needing sync across locale bundles
- 'Specialty directory' and 'veterinarian directory' are both used as page-descriptive phrases rather than new domain nouns; the precedent term 'veterinarian directory' also carries no ubiquitous-language.md entry, so the absence of one for 'specialty directory' is consistent with existing project practice, not drift

**security-reviewer**

- Fix delta since basis 8b39262 touches only SpecialtyDirectory.java (equals/hashCode on the read model and its Entry) and its unit test; no new input handling, file I/O, serialization, logging, reflection, or process execution enters the change
- SpecialtyDirectory.equals/hashCode delegate to the entries list, and Entry compares specialty plus an immutable List.copyOf of veterinarians; the value object stays immutable after construction, so the added methods introduce no shared mutable state in a request-scoped read model
- Entry.hashCode via Objects.hash over persistence entities resolves to identity hash codes (Specialty/Vet define no equals/hashCode); the values are never used as keys for request-supplied lookup, so no hash-collision DoS path exists, and equality is documented as identity-based rather than silently assumed
- Pattern consistency holds: equality is expressed the same way as elsewhere in the change (instanceof pattern match, null-safe Objects.equals for the possibly-null entity field, direct List.equals for the non-null copied list), with the identity-equality semantics justified inline in the Javadoc
- No new secrets, credentials, URLs, or environment reads appear in the delta; grep over the delta for Runtime/ProcessBuilder/exec, Files/FileWriter/FileOutputStream, JsonTypeInfo/enableDefaultTyping, and /tmp/ returns nothing
- Escaping and output-safety surface (SpecialtyController, specialtyList.html) is unchanged since the round-1 approval and required no re-verification under fix-delta scope

**code-quality-reviewer**

- SpecialtyDirectory.equals/hashCode and Entry.equals/hashCode resolve the round-1 finding directly: both classes now compare by value (entries.equals(that.entries); specialty+veterinarians via Objects.equals/List.equals), satisfying architecture-principles.md's value-object equality-by-value rule
- The new Javadoc is honest rather than overselling the fix: it states plainly that the wrapped persistence entities (Specialty, Vet) define no equality of their own, so two directories built from two separate reads of the same row are not equal — this is the correct scope boundary (fixing Specialty/Vet equality is outside this slice) and the reader is told rather than left to discover it by surprise
- Three new unit tests in SpecialtyDirectoryTests directly exercise the added equality contract: reordered-but-equal directories, directories over different specialties, and Entry equality — each uses AssertJ's isEqualTo/hasSameHashCodeAs pairing so a hashCode-only regression would also be caught
- checkFormat and compileJava both pass clean on the current tree; no new style or compilation issue introduced by the fix

**doc-reviewer**

- Fix-round delta (SpecialtyDirectory/Entry equals()/hashCode()) is a production-code-only change with no accompanying doc edit needed: docs/prd.md and docs/system-design.md are byte-identical to the round-1 tree this reviewer already approved (line 16) — re-verified req anchor req-specialtydirectory-001, all seven Done-when REQ-SPECIALTYDIRECTORY-001 bullets, the NG-10 non-goals row, and the three system-design.md Contracts rows (SpecialtyRepository, SpecialtyDirectory, SpecialtyController) still resolve and stay at purpose-plus-source-pointer altitude
- The added value-equality behavior needs no system-design.md update: the Contracts row for SpecialtyDirectory already states the design-level fact ('immutable grouping') without enumerating methods, and architecture-principles.md's value-object equality rule is a code-level contract, not a documented interface — adding equals()/hashCode() does not change any claim the docs make about the type

**test-reviewer**

- Round-1 finding on SpecialtyDirectory/Entry value-object equality is otherwise well covered: equal-content, order-independence of specialty input (built in reverse order), and unequal-specialty cases are all tested with AssertJ's isEqualTo/isNotEqualTo/hasSameHashCodeAs
- All prior review-round approvals still hold: real hand-written repository stubs (no Mockito), BDD naming, three-tier data naming, four-phase test structure, and full PRD acceptance-criteria coverage are unchanged by the fix delta
- ./gradlew test passes with no failures or skips across the full suite; SpecialtyDirectory instruction coverage is 96% and Entry 93%, both above the brief's 80% line-coverage target even with the branch gap noted above

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $3.84 | 14m 19s | 96% |
| `(parent)` | 1 | opus-5 | $1.34 | 31m 31s | 95% |
| `agent-team:system-design-expert` | 1 | opus-5 | $1.30 | 3m 39s | 91% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.17 | 3m 36s | 93% |
| `agent-team:security-reviewer` | 2 | opus-5 | $1.00 | 1m 57s | 87% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.88 | 4m 23s | 93% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.73 | 3m 21s | 94% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.65 | 2m 27s | 92% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $2.92 | 10m 9s | 96% |
| `(parent)` | opus-5 | $1.34 | 31m 31s | 95% |
| `agent-team:system-design-expert` | opus-5 | $1.30 | 3m 39s | 91% |
| `agent-team:product-requirements-expert` | opus-5 | $1.17 | 3m 36s | 93% |
| `agent-team:feature-implementer` | opus-5 | $0.92 | 4m 10s | 95% |
| `agent-team:security-reviewer` | opus-5 | $0.62 | 1m 17s | 89% |
| `agent-team:test-reviewer` | sonnet-5 | $0.47 | 2m 8s | 93% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.44 | 2m 15s | 94% |
| `agent-team:test-reviewer` | sonnet-5 | $0.41 | 2m 15s | 92% |
| `agent-team:security-reviewer` | opus-5 | $0.37 | 39s | 85% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.34 | 1m 25s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.31 | 1m 2s | 92% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.28 | 1m 5s | 93% |

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

- plugin `agent-team-spring-boot` at `v0.3.1` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.232 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
