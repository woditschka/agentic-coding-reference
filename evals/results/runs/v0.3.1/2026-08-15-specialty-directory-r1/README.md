# specialty-directory r1 — v0.3.1

Specialty directory page (feature) · started 2026-08-14T22:15:13+00:00 · exec `claude-dev` · status **complete**

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
| 5 (±0) | 4 (±0) | 4 (±0) | 5 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.99. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Grouping and ordering sit in the immutable  SpecialtyDirectory  record, not the controller;  SpecialtyController.showSpecialtyDirectory  only delegates and selects a view, honoring the Web-controller row, and  SpecialtyRepository  mirrors the existing lookup-repository precedent. Docs move in step: REQ-SPEC-001 with edge cases, an indexed ADR, contracts-table rows for all three types, the package-structure line, the Holder vocabulary entry, and two recorded open questions — no visible stale claim. Unit tests read as specifications with factories and fluent assertions. Deductions: bare id literals ( createASpecialty(1, DENTISTRY) ) are Tier-3 mystery values beside the unused  SOME_SPECIALTY_ID ;  theSpecialtyDirectoryShouldBeLinkedFromNoPage  walks the filesystem from a  @WebMvcTest  class on a relative path; the template's  #{specialties} / #{none}  keys are never added to any message bundle.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Grouping and both orderings live in the immutable  SpecialtyDirectory  record (SpecialtyDirectory.java:  of ,  holdersOf ,  holds ), so the controller only delegates and selects a view (SpecialtyController.showSpecialtyDirectory) — no new controller rule; repository/controller naming and constructor injection follow the catalog. Unit tests are behavior-named, factory-built, blank-line phased, with SOME_ constants and collection assertions. Two dings:  createASpecialty / createAVet  are duplicated verbatim across both test classes instead of shared vocabulary, and the controller test stubs both repositories with  @MockitoBean  rather than a hand-written double;  theSpecialtyDirectoryShouldBeLinkedFromNoPage  walks the filesystem, coupling it to CWD. The template's  #{specialties}  and  #{none}  keys are never added to any bundle in the patch. Docs — ADR, PRD REQ-SPEC-001, contracts, vocabulary — all move together.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 4

> Layering is clean:  SpecialtyDirectory  holds the grouping and both orderings as an immutable record with defensive copies (SpecialtyDirectory.java  entries = List.copyOf(entries) ), so  SpecialtyController.showSpecialtyDirectory  only delegates and selects a view — no new controller rule; naming, the read-only  SpecialtyRepository , and the ADR justify the shape. Unit tests are behaviour-named, factory-built, and cover empty, unheld, multi-hold, and identity-vs-equality cases. Weaker points:  theSpecialtyDirectoryShouldBeLinkedFromNoPage  walks  src/main/resources/templates  from the CWD inside a  @WebMvcTest , asserting on file text rather than behaviour; the controller test's world lives in  @BeforeEach setup() , offstage from its tests; the template introduces  #{specialties} / #{none}  with no bundle hunk; and prd.md still claims "ten further questions stay open" after two were added.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $17.19 | 47m | 42 | 94% | 12 file(s) +615/−7 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.91 | 2m 40s | 88% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPECIALTYDIRECTORY-001 — Specialty directory lists every specialty with the veterinarians holding it

2 review rounds · 2 build-passes · **1 build-failure** · grade **CONCERN**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | **✔** | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (3) | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Specialty directory lists every specialty with the veterinarians holding it · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **new** · (design) · ***◷ 7m***
- ◆ **implement** (implementer) · ***◷ 11m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 41s***
- ✔ **review test** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain: no NVD match ran in this review. build.gradle declares no OWASP dependency-check plugin (plugins are java, checkstyle, jacoco, spring-boot 4.1.0, dependency-management, graalvm native, cyclonedx, javaformat), so `./gradlew dependencyCheckAnalyze` is not available and the reviewer has no network access. Treat the dependency posture as NOT VERIFIED against the NVD for this pass. The risk is bounded here because the change set adds and modifies no dependency — build.gradle is untouched by the slice — so the resolved artifact set is identical to the pre-slice baseline. Closing the check is a CI or human task, not a blocker for this change.
  - ▹ rec: Robustness note, not an attacker path: SpecialtyDirectory.holds() dereferences specialty.getId() unconditionally. Every specialty on this path comes from persistence and carries an id, and no request-supplied value reaches the comparison, so there is no reachable NPE from an attacker-controlled input. If the value object is ever reused with a transient Specialty, the guard becomes worth adding.
- ✎ **review doc** · **changes_requested** · (3 findings) · ***◷ 3m***
  - **[blocked]** `prd.md:201` The Open Questions entry for specialty-directory ordering still reads 'Whether specialties, and the veterinarians under each, sort by name or follow their stored order is unstated (2026-08-14).' The governing ADR (docs/adr/2026-08-14-specialty-directory-derived-in-memory.md, Decision section) states the opposite: 'Specialties are ordered by name, and the holders under each by last name, then first name, then identity. This settles the PRD's open ordering question at design time.' The shipped code and tests implement exactly that order. A reader of the PRD alone is told the order is unset; a reader of the ADR is told it was settled pending owner revisit. Update the Open Questions entry to state that a name-based order is in place per the ADR pending an owner decision, so the two documents agree.
  - [clarify] `prd.md:152` The Specialty directory requirement section carries only a **Design:** link (system-design.md#contracts), unlike the Pet records section, which carries both **Design:** and an **ADR:** link for the mechanism decision behind it (2026-07-31 pet-name-uniqueness ADR). ADR 2026-08-14 records the decision behind REQ-SPEC-001's grouping and ordering. Confirm whether the same **ADR:** convention should apply here, and add the link if so.
  - [clarify] `2026-08-14-specialty-directory-derived` 'Holder' (a veterinarian holding a specialty) is used as a load-bearing domain noun across the PRD prose, the PRD's Done-when bullets, and the ADR's Options/Decision sections, and it is echoed into source as the field name `holders`, the record component `Entry.holders`, and test helpers (`holderNamesUnder`, `holdersUnder`, `holderIdsUnder`). docs/ubiquitous-language.md defines Veterinarian and Specialty but has no entry for 'holder' or the holds relationship as a named concept. The system-design-expert's design-block (handoff.jsonl line 5/9) flagged this same gap and left it for the product-requirements-expert. Add a ubiquitous-language.md entry for the term, or confirm it is ordinary prose not meant as canonical vocabulary.
- ↻ **fix prd-expert** ← doc · (3 findings)
- ◇ **prd-entry** Specialty directory lists every specialty with the veterinarians holding it · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **covered** · (design) · supersedes L9 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 47s***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · handoff-log · autofix-audit
- ✔ **review code-quality** · **approved** · ***◷ 43s***
- ✔ **review doc** · **approved** · ***◷ 32s***
- ✔ **review test** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply-chain NVD match did not run and is therefore not clean, only unverified: the OWASP dependency-check plugin is not configured in build.gradle, so ./gradlew dependencyCheckAnalyze does not exist and this reviewer has no network access. Resolved framework versions on the branch are Spring Boot 4.1.0 (with its managed Jackson and Thymeleaf). Since this change adds no dependency, the unverified surface is pre-existing rather than introduced — closing it belongs to CI or a human, not to this slice.
  - ▹ rec: SpecialtyDirectory.holds dereferences specialty.getId() unguarded (line 74). Every request-reachable path reads specialties from the store, so the id is non-null there and no attacker-reachable NPE exists; a transient Specialty constructed in a future test or caller would fail with an NPE whose message the error page renders. Consider matching on the holder side first or guarding the id, if the type is ever used off the persisted path.
  - ▹ rec: IDE semantic oracle was not consulted (headless run), so the route-exposure conclusion above rests on reading the single new @GetMapping and the design doc's Contracts rows rather than on resolved-symbol references — the weaker basis, though the surface is one literal-mapped controller method.
- ◆ **grade CONCERN** · publish the specialty directory page
  - blast_radius — **clear** — Twelve files in one module: six new files confined to the vet package plus four documentation files, with the only edit to shared production code being two additive reflection-hint registrations in PetClinicRuntimeHints. No existing route, template, message key, or sensitive path is modified, and nothing is deleted.
  - semantic_surprise — **concern** — The template reuses vetList.html's span-per-item idiom, but where that page lists single-word specialty names this one lists two-word full names, so a cell with several holders renders as an undelimited run of words. The seeded data gives radiology and surgery two holders each, so the shipped application shows this on first load. Everything else matches the stated behavior, and the unguarded specialty.getId() in holds() is unreachable from the persisted path.
  - test_adequacy — **concern** — SpecialtyDirectoryTests is strong: real Specialty and Vet objects, all four PRD edge cases, and the two-level ordering including the identity tiebreak that BaseEntity's absent equals makes necessary. The gap is at the template, where every controller test stubs exactly one holder per specialty, so the multi-holder rendering path the seeded application actually takes is asserted by nothing and a template bug that dropped or ran holders together would still pass.
  - reviewer_hedging — **concern** — All four roster reviewers approved with empty findings, but the security reviewer attached three recommendations on the final round. Two are disclosed methodology limits rather than worries about this code (no OWASP dependency-check plugin and no network for an NVD match, and no IDE oracle in a headless run); the third is residual polish, guarding the specialty.getId() dereference at SpecialtyDirectory line 74 for any future caller off the persisted path.
  - scope_deviation — **clear** — The row reports two design revisions, but the log shows documentation churn rather than a scope fight: the first answered a failed autofix audit and the second answered the doc-reviewer's round-one findings, with its design-block recording the production tree as unchanged since the earlier build-pass. The diff maps onto the prd-entry file targets plus the runtime-hints file the design named as a supporting path, and nothing reaches past REQ-SPEC-001.
  - why — Grouping, identity matching, and ordering are correct and genuinely unit-tested. The one thing to look at is the holder cell: full names are joined by a single space, so the seeded page renders two holders as one run of words, and no test renders more than one holder. Confirm that separator, then merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- checkFormat passes clean
- SpecialtyController mirrors VetController's shape and visibility (package-private class, public constructor, single @GetMapping)
- SpecialtyDirectory is a proper immutable record: List.copyOf in both compact constructors, no mutable state, holder matching by persisted identity (getId()) rather than object equality, matching the design-block's called-out risk
- Naming follows architecture-principles.md: SpecialtyDirectory is a bare domain noun, SpecialtyRepository/SpecialtyController take the correct suffixes, no prohibited suffixes anywhere
- SpecialtyRepository mirrors VetRepository precedent exactly: extends Repository\<T,Integer>, @Transactional(readOnly = true), read-only surface with javadoc explaining why no write method exists
- specialtyList.html reuses vetList.html's exact span-per-holder rendering idiom for consistency with the existing template
- PetClinicRuntimeHints addition is scoped and commented, registering only the two new reflectively-read types with INVOKE_PUBLIC_METHODS

**test-reviewer**

- SpecialtyDirectoryTests.java is a pure unit suite (no Spring context, no I/O), covering every PRD acceptance criterion and edge case for REQ-SPEC-001: stored-name listing, multi-specialty holders, holder-omission for a vet with no specialty, an unheld specialty still listed, stable ordering (specialty by name, holders by last-then-first-then-id), the empty-clinic edge case, and the identity-vs-equality matching risk the design-block flagged (BaseEntity has no equals/hashCode) — each with a dedicated regression test.
- Four-phase structure with blank-line separation, BDD  the{Subject}Should{Outcome}  naming, AssertJ-only assertions, factory methods (createASpecialty/createAVet) replacing raw constructors, and correct three-tier data naming (DENTISTRY/RADIOLOGY/SURGERY as role-describing Tier-1 constants, SOME_SPECIALTY_ID/SOME_VET_ID as Tier-2) throughout both test classes.
- SpecialtyControllerTests.java correctly uses the sanctioned MockMvc boundary mock and @MockitoBean on the two repository collaborators, consistent with VetControllerTests' existing idiom (given(...) stubbing). No verify()-based interaction testing duplicates a behavioral assertion.
- theSpecialtyDirectoryShouldBeLinkedFromNoPage exercises the real filesystem/template tree rather than mocking it, directly verifying acceptance criterion 5 (no page links to the directory) with real I/O per the brief's integration-test guidance.
- All six test_names from the prd-entry are present and correctly split between SpecialtyDirectoryTests (grouping/ordering rules, no Spring context) and SpecialtyControllerTests (rendered-page assertions via MockMvc), matching the design-block's test-placement notes.
- ./gradlew test passes; no assertion-free or over-mocked tests found in a targeted sweep for verify()/Mockito.mock()/@Mock usage.

**security-reviewer**

- No request-derived input anywhere in the slice: GET /specialties.html binds no path variable, request parameter, or form type, so the mass-assignment, path-traversal, and injection rows of security-principles.md § Realization have no surface to apply to. No @InitBinder is required because nothing is bound.
- Data access stays on the repository abstraction: SpecialtyRepository declares only a derived findAll() over Spring Data, with no string-concatenated query text. It is read-only by construction (@Transactional(readOnly = true), Repository base interface with no write method), which is least privilege for the specialty lookup table.
- Template output escaping stays on: src/main/resources/templates/vets/specialtyList.html renders every dynamic value through th:text (entry.specialty.name, the holder name concatenation, and the #{none} message). No th:utext, no inline JavaScript, no remote resource reference, and no Thymeleaf preprocessing (__${...}__) of any model value. Verified by grep for th:utext and __${ across src/main/resources/templates/ — the only preprocessing hits in the tree are vetList.html's pager over server-computed page integers, which this slice does not touch.
- Escaping matches the neighboring implementation of the same concern (vetList.html renders vet and specialty names the identical way), so the Pattern Consistency check passes with no divergence to justify.
- No widening of the exposed surface: the page publishes specialty names and veterinarian names, both already published by /vets.html and /vets. No management endpoint, no mutating route, and no new data class reaches a caller.
- Native-image hints add reflection only: PetClinicRuntimeHints registers SpecialtyDirectory and SpecialtyDirectory.Entry with MemberCategory.INVOKE_PUBLIC_METHODS, not withJavaSerialization(true). The Java-serialization surface named in the threat model is unchanged, and no endpoint accepts serialized input.
- Concurrency and state: SpecialtyController is a stateless singleton holding two repository references; SpecialtyDirectory and its Entry are records that defensively copy their lists (List.copyOf) in the compact constructors, so the model object handed to the view is immutable and safe to share.
- No secrets, credentials, or connection strings introduced: a case-insensitive scan of the full change set for password/secret/token/apikey/credential returns nothing. No shell execution (Runtime/ProcessBuilder), no unsafe Jackson configuration (enableDefaultTyping/@JsonTypeInfo), no file I/O, and no system /tmp use anywhere in the diff.
- No new logging, so no log-injection or sensitive-data-in-logs surface; no exception message is constructed that could carry internal detail onto the error page.

**doc-reviewer**

- REQ-SPEC-001 anchor, Done-when bullets, and edge-case list follow the PRD format exactly, with no mechanism or code references leaking into the requirement prose
- The new ADR (docs/adr/2026-08-14-specialty-directory-derived-in-memory.md) follows the house ADR structure: Status, Context, Options Considered, Decision, Consequences, Implementation with a Requirements line, and References with em-dashes
- docs/adr/README.md gained the matching dated index row for the new ADR
- docs/system-design.md's Contracts table additions (SpecialtyRepository, SpecialtyDirectory, SpecialtyController) name each type once, point at its source file, and carry no field/parameter tables or constant literals
- The package-structure diagram and the Contracts' Implements column were both updated consistently for the new types and for Vet/Specialty/VetRepository gaining REQ-SPEC-001

**code-quality-reviewer**

- SpecialtyDirectory.of/holdersOf/holds keep single responsibility, stream pipelines over manual loops, and immutable records with List.copyOf defensive copies in both the record and its nested Entry
- Naming follows convention: no get/set prefixes on record accessors, no util/helper/common packages, comparator constants are descriptive rather than abbreviated, and SpecialtyController/SpecialtyRepository/SpecialtyDirectory carry no prohibited suffix
- SpecialtyController uses implicit constructor injection (single constructor, no @Autowired), matching VetController's existing style
- SpecialtyRepository declares only the read the specialty directory needs, with Javadoc explaining why no write method belongs on the interface
- specialtyList.html mirrors vetList.html's existing span/th:each pattern for the holder list rather than inventing a new idiom, keeping the two vet-package templates consistent
- New page strings (specialties, name, vets, none) are present in messages.properties and all ten locale variants, satisfying REQ-LANG-002
- PetClinicRuntimeHints registers reflection hints for the new SpecialtyDirectory/Entry record pair with a comment explaining why (non-persisted type read reflectively by the template)
- ./gradlew checkFormat passes with no formatting violations

**doc-reviewer**

- prd.md:152 now carries the ADR link in the exact **Design:** · **ADR:** form used at prd.md:99 for the pet-name-uniqueness precedent, title-as-link-text included, and the target file resolves
- prd.md:201 Open Questions entry now states the name-based order in place, attributes it to design, links the governing ADR, and keeps the owner's decision open, agreeing in both directions with the ADR's Decision section without promoting the sort key into REQ-SPEC-001 or its edge case 4
- docs/ubiquitous-language.md gained a Holder entry scoped as a role in the existing holds relationship (not a new concept), carrying a dated added-2026-08-14 mark, with the file's confirmation banner amended to except later dated additions from the 2026-07-31 confirmation
- All new and edited prose stays within the sentence-length standard and uses no mechanism or rationale prose leaking into the PRD

**test-reviewer**

- Both SpecialtyDirectoryTests and SpecialtyControllerTests follow the the{Subject}Should{Outcome} BDD naming school exactly, and every test name reads as a specification of observable behavior rather than a mirror of the production method under test
- Four-phase structure held throughout: each test separates a real-object arrange, a single act call, and a chained AssertJ assert with blank lines, no phase comments, and no narration comments
- Mocking policy honored: SpecialtyDirectoryTests uses only real Specialty/Vet value objects end to end; SpecialtyControllerTests uses MockitoBean solely to stub the two repositories behind MockMvc's real dispatch/binding, the one sanctioned boundary mock, with no verify() restating an outcome the content()/model() assertions already cover
- Three-tier data naming is clean: meaningful values (DENTISTRY, RADIOLOGY, SURGERY, the ordering-tiebreak vet IDs 1-4) are named or self-evident from context, irrelevant values carry SOME_ prefixes (SOME_SPECIALTY_ID, SOME_VET_ID), and construction is wrapped in createASpecialty/createAVet factories rather than raw constructors, with a locally-relevant id overload added rather than duplicating the factory
- All four PRD edge cases for REQ-SPEC-001 have dedicated tests: multi-specialty holder naming, an unheld specialty still listed, an empty clinic (theSpecialtyDirectoryShouldBeEmptyForAClinicThatKnowsNoSpecialty), and stable two-level ordering (by specialty name, then by last name/first name/identity tiebreak) — the identity-matching test (theSpecialtyDirectoryShouldMatchHoldersByStoredIdentityRatherThanObjectEquality) additionally covers the BaseEntity non-equals hazard the Javadoc calls out
- SpecialtyControllerTests.theSpecialtyDirectoryShouldBeLinkedFromNoPage walks the real template directory to verify the no-navigation-entry acceptance bullet against actual file content rather than an invented fixture, matching REQ-SPEC-001's 'no page links to it' criterion
- No test re-verifies another unit's behavior: the controller tests assert only page wiring and rendering (attribute presence, view name, absence of a paging link, holder/empty-slot text), while the ordering and grouping logic is exhaustively covered once at the SpecialtyDirectory unit level
- ./gradlew test is green for both new test classes with no skips

**security-reviewer**

- No new trust boundary: SpecialtyController.showSpecialtyDirectory(Model) binds no request-derived value at all — no @RequestParam, @PathVariable, or command object — so mass assignment, path traversal (the view name 'vets/specialtyList' is a literal), and cross-request-state rows of security-principles.md Realization are not reachable here.
- Data access is a Spring Data derived query (SpecialtyRepository.findAll(), @Transactional(readOnly = true), no write method declared) with no string-concatenated query text — the injection-into-data-access row passes, and the read-only, read-whole interface matches least privilege.
- Output escaping: specialtyList.html renders every derived value through th:text (entry.specialty.name, holder.firstName/lastName) with default escaping on; no th:utext, no inline JavaScript, no remote resource, and no Thymeleaf preprocessing (__${...}__) of any value on this template — the XSS row passes and the escaping mechanism matches the neighboring vetList.html.
- Native-image hints widen reflection minimally: SpecialtyDirectory and SpecialtyDirectory.Entry are registered with MemberCategory.INVOKE_PUBLIC_METHODS only, deliberately not withJavaSerialization as the three persisted types are — the unsafe-deserialization surface is not extended.
- Exposed surface: GET /specialties.html is read-only and publishes only specialty names and veterinarian names, both already public via /vets.html; the route, its unpaged shape, and its components are documented in docs/system-design.md (Contracts rows) and REQ-SPEC-001, satisfying the 'a change that adds an endpoint states what it exposes and to whom' rule. No management endpoint exposure changed.
- No secrets, credentials, or connection strings added anywhere in the diff (scanned production, template, and both test files for token/password/secret/key/credential); no logging added, so no log-injection or sensitive-log path.
- No shell execution, file I/O, XML/YAML/JSON parsing, regex, or randomness introduced; the derived model is immutable (record with List.copyOf in both canonical constructors) and the controller holds no mutable singleton state, so the concurrency row passes.
- Supply chain unchanged: build.gradle is not in the change set and no dependency was added or upgraded; the nohttp plain-HTTP check and mavenCentral-over-TLS resolution remain as-is.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $4.15 | 15m 10s | 96% |
| `agent-team:system-design-expert` | 3 | opus-5 | $4.05 | 11m 30s | 93% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $2.76 | 7m 13s | 94% |
| `(parent)` | 1 | opus-5 | $2.01 | 48m 53s | 96% |
| `agent-team:security-reviewer` | 2 | opus-5 | $1.23 | 2m 49s | 89% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.93 | 4m 7s | 93% |
| `agent-team:change-grader` | 1 | opus-5 | $0.91 | 2m 40s | 88% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.60 | 2m 34s | 90% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.48 | 1m 46s | 89% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.33 | 12m 14s | 97% |
| `agent-team:system-design-expert` | opus-5 | $2.63 | 8m 3s | 95% |
| `(parent)` | opus-5 | $2.01 | 48m 53s | 96% |
| `agent-team:product-requirements-expert` | opus-5 | $1.57 | 3m 40s | 95% |
| `agent-team:product-requirements-expert` | opus-5 | $1.18 | 3m 32s | 92% |
| `agent-team:change-grader` | opus-5 | $0.91 | 2m 40s | 88% |
| `agent-team:system-design-expert` | opus-5 | $0.74 | 1m 54s | 88% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.69 | 3m 18s | 93% |
| `agent-team:system-design-expert` | opus-5 | $0.68 | 1m 32s | 89% |
| `agent-team:security-reviewer` | opus-5 | $0.64 | 1m 30s | 90% |
| `agent-team:security-reviewer` | opus-5 | $0.59 | 1m 19s | 88% |
| `agent-team:feature-implementer` | opus-5 | $0.44 | 1m 51s | 92% |
| `agent-team:feature-implementer` | opus-5 | $0.38 | 1m 4s | 86% |
| `agent-team:test-reviewer` | sonnet-5 | $0.30 | 1m 11s | 91% |
| `agent-team:test-reviewer` | sonnet-5 | $0.30 | 1m 22s | 88% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.24 | 53s | 89% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.23 | 48s | 90% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.23 | 53s | 89% |

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
