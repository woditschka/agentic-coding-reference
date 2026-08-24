# specialty-directory r2 — v0.1.29

Specialty directory page (feature) · started 2026-08-23T23:09:49+00:00 · exec `claude-dev` · status **complete**

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
| 5 (±0) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.67. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Placement and patterns fit: SpecialtyDirectory holds the grouping/ordering rule as an immutable value object (List.copyOf/Map.copyOf, value equals/hashCode), SpecialtyController only binds and delegates, and SpecialtyRepository extends bare Repository with reads only, honoring NG-2. Unit tests are behavior-named, four-phase, factory-built (createASpecialtyNamed/createAVetNamed), mock-free, and cover empty holders, multi-hold, re-read identity, and ordering. Weaknesses sit in SpecialtyControllerTests: a RANDOM_PORT server plus raw-HTML assertions (containsSubsequence("dentistry", "Linda Douglas", ...), doesNotContain("\<li")) and the substring-scanning rowFor helper couple tests to markup; @Sql string-concatenated INSERT/DELETE mutates the shared seeded database. Docs move thoroughly — prd REQ-VET-003, ubiquitous-language, system-design contracts, ADR and its index.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyDirectory holds the grouping/ordering rule as an immutable value object with defensive copies (List.copyOf/Map.copyOf), leaving SpecialtyController a three-line delegate and SpecialtyRepository a read-only bare Repository — right layer, catalog-conforming, no rule in the controller, and an ADR records the inversion choice. Unit tests are exemplary: behavior names, four phases, factories (createASpecialtyNamed, createAVetNamed), real objects, no mock framework. SpecialtyControllerTests deviates: @SpringBootTest(RANDOM_PORT)+TestRestTemplate instead of the sanctioned in-process web harness, raw-HTML containsSubsequence assertions and a hand-rolled rowFor string scraper, plus @Sql mutation of the shared seed. Maintainability nits: unused equals/hashCode over identity-equal entities, an inconsistent lambda/method-ref comparator, and a two-map build in group(). Docs (prd, system-design, vocabulary, ADR index) are fully current.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> New types match catalog patterns: SpecialtyRepository mirrors VetRepository's bare read-only Repository (NG-2 preserved), SpecialtyController only binds/delegates/selects the view, and grouping plus ordering sit in the immutable SpecialtyDirectory value object, unit-testable without framework context. SpecialtyDirectoryTests are exemplary — behavior names, four phases, factories (createAVetNamed), real objects, collection assertions. SpecialtyControllerTests weaken this: a RANDOM_PORT full-server E2E rather than the sanctioned in-process web harness, assertions over raw markup (doesNotContain("\<li"), containsSubsequence on HTML), a fragile rowFor substring helper, bare literals "/vets.html"/"/owners/find", and @Sql mutation of the shared seeded database. Docs are complete: PRD REQ-VET-003 with open questions, system-design contract rows, ubiquitous-language entry, ADR plus index row.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $12.34 | 36m | 10 | 93% | 11 file(s) +683/−4 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.90 | 2m 31s | 89% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Specialty directory: every specialty with the veterinarians holding it

2 review rounds · 2 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- ◇ **prd-entry** Specialty directory: every specialty with the veterinarians holding it · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 10m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 49s***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 47s***
- ✔ **review security** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `SpecialtyControllerTests.java` REQ-VET-003's 'specialty no veterinarian holds' Done-when criterion is proven only by the pure in-memory unit test (SpecialtyDirectoryTests.theSpecialtyDirectoryShouldListASpecialtyNoVeterinarianHolds). Nothing exercises the real repository read plus the Thymeleaf render for this case: the seeded H2 data (radiology, surgery, dentistry) has no unheld specialty, so SpecialtyRepository.findAll() and the specialtyList.html empty-\<ul> path are unverified end to end. SpecialtyRepository.java is a changed production file with zero direct test naming it.
    - fix: Add a fixture (e.g. a targeted @Sql insert or a small @DataJpaTest against real H2) that gives the seeded data an unheld specialty, and assert the full-stack response still lists it with no veterinarian shown against it — closing the loop from repository read through template render for this acceptance criterion.
  - [autofix] `SpecialtyControllerTests.java:87-92` REQ-VET-003 states 'no other page of the system carries a link to it', but theSpecialtyDirectoryShouldCarryTheStandardNavigationWithoutLinkingToItself only checks that the specialty page itself omits a self-link. It does not check that any other page (vets.html, the welcome page, owner pages) omits a link to /specialties.html, so the actual PRD criterion is untested.
    - fix: Fetch at least one other real page (e.g. /vets.html) in the same test class and assert its body does not contain href="/specialties.html", in addition to the existing self-link check.
- ↻ **implement** (implementer) ← test · (2 findings) · ***◷ 4m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved** · ***◷ 1m***
- ◆ **grade CLEAR** · add the read-only specialty directory page
  - blast_radius — **clear** — Eleven files in one feature package (vet, main plus test) with no sensitive paths, no dependency or schema change, and — read against the diff — not one existing production file modified: the four Java/template additions are new files and every tracked-file edit is under docs/, so the only runtime reach is the additive GET /specialties.html route.
  - semantic_surprise — **clear** — Read every hunk of the three new classes and the template: group() seeds the map from the specialty side first, which is exactly what makes an unheld specialty render with an empty list; the null-guard that drops a vet holding a specialty the specialty read no longer returns is deliberate, commented, ADR-recorded and tested; comparators match the documented name and last-then-first order; veterinariansHolding matches by stored id, which is correct because BaseEntity compares by object identity, and its IllegalArgumentException is unreachable from the template since every rendered specialty is a map key. The only residual is the inherited never-evicted vets cache, pre-existing and documented, not introduced here.
  - test_adequacy — **clear** — Tests assert real outcomes rather than restating the implementation: containsExactly and containsSubsequence pin both orderings, rowFor narrows the empty-veterinarian assertion to that specialty's own table row instead of the whole page, defensive-copy independence is proven by mutating the source lists after construction, and the no-link criterion is checked by fetching / and /vets.html. Full-stack against seeded H2 with no mocks; the unheld-specialty @Sql fixture is method-scoped with an AFTER_TEST_METHOD delete so it cannot leak into the shared context.
  - reviewer_hedging — **clear** — Four approvals with empty findings lists and no escalate tag; the test-reviewer's two round-one findings were both fixable/autofix, were fixed, and the round-two approval names the specific closures with no reservation carried forward. The round-two roster of test-reviewer alone is the fix-delta plan's own scoping, not silence.
  - scope_deviation — **clear** — Zero consultations and zero build retries; the single design revision was a ledger-coverage correction adding docs/system-design.md and docs/adr/README.md to the design-block supporting_paths, not a redesign of the slice. The diff matches the PRD surface exactly — no navigation entry, no write path, no new dependency — and the deferred nav-link decision is recorded as an open question rather than quietly implemented.
  - why — Additive read-only page: no existing production file is touched, the in-memory inversion reads correctly at every hunk including the deliberate unheld-specialty and withdrawn-specialty branches, and tests assert ordering and the empty-row case against real seeded data. Confirm and merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyDirectory is a true immutable value object: private constructor, List.copyOf/Map.copyOf defensive copies, value-based equals/hashCode, matching by stored identity (getId()) as the ADR requires since BaseEntity compares by object identity
- SpecialtyRepository extends the bare Repository interface with a single @Transactional(readOnly = true) findAll(), matching VetRepository's shape and honoring NG-2 (no write path)
- SpecialtyController is package-private, constructor-injected, single-responsibility, and delegates all grouping/ordering logic to SpecialtyDirectory rather than doing it inline
- Ordering comparators (BY_NAME, BY_LAST_THEN_FIRST_NAME) are documented with the collation rationale and applied in Java, not SQL
- specialtyList.html composes the full name via ${vet.firstName + ' ' + vet.lastName}, matching the existing vetList.html idiom exactly; no new i18n keys needed since 'specialties', 'name', 'vets' already exist in messages.properties
- Test suites are thorough and well-named: SpecialtyDirectoryTests covers grouping, omission of specialty-less vets, listing of vet-less specialties, ordering, defensive-copy independence, cross-read identity matching (via a readAgain() helper simulating a second DB read), and the IllegalArgumentException on an unlisted specialty; SpecialtyControllerTests verifies the page against real seeded data with no mocks, including the no-navigation-link constraint
- Javadoc throughout (SpecialtyDirectory, SpecialtyRepository, SpecialtyController) explains the why (unidirectional association, ADR reference, per-vendor collation) not just the what
- ./gradlew checkFormatMain and checkFormatTest both pass (note: the task name is checkFormatMain/checkFormatTest in this project, not checkJavaFormat)
- No @ManyToMany(mappedBy) inverse added to Specialty.java, confirmed by direct inspection - the unidirectional association constraint is honored

**security-reviewer**

- Injection surface: no SQL, JPQL, or native query is introduced. SpecialtyRepository declares a single derived findAll() on the bare Spring Data Repository interface, so no string-concatenated query text exists; consistent with the SQL-injection mitigation row in docs/system-design.md Threat Model.
- Output escaping: specialtyList.html renders every dynamic value through th:text (specialty.name, vet.firstName/lastName) with Thymeleaf's default HTML escaping. Swept all templates under src/main/resources/templates for th:utext, utext, and th:inline - zero hits, so the slice introduces no unescaped sink and no deviation from vetList.html's established pattern.
- No user input: GET /specialties.html takes no path variable, query parameter, request body, or header. There is no binder, no @RequestParam, and no attacker-controlled value reaching the model, so template/expression injection and path traversal have no entry point. The menu selector 'specialties' passed to fragments/layout is a template literal, not input.
- Write path: SpecialtyRepository extends the bare Repository interface (not CrudRepository/JpaRepository) and declares only findAll() with @Transactional(readOnly = true). No save, delete, or flush is reachable through it, and no existing entity mapping was altered, so the slice adds no state-changing surface and no CSRF-relevant route.
- Data exposure: the page renders specialty names and veterinarian first/last names, all of which /vets.html and the serialized /vets route already publish. The only value not previously reachable is the name of a specialty no veterinarian holds - a clinic lookup value, not PII and not operational detail. No identifiers, credentials, or internal state are leaked; IllegalArgumentException in veterinariansHolding is unreachable by construction (every listed specialty is a map key), so no error-path stack trace exposure.
- Access control: the route inherits the application-wide unauthenticated posture already recorded in docs/system-design.md Security Context and Threat Model. It is a read-only page over data already served anonymously on two existing routes, so it neither widens the documented gap nor creates a new trust boundary. Unlinked-but-reachable adds no exposure of its own here, since the data is public on the linked /vets pages.
- Secrets: swept the full change set for token/password/secret/key/credential/passwd/apikey. No hits in the added Java, template, or test sources; no property, compose, or manifest file is touched.
- Supply chain: scripts/changeset.sh --name-only shows no build.gradle, settings.gradle, gradle wrapper, or lockfile in the change set, and git status reports those paths clean. No dependency is added, upgraded, or pinned, so the slice introduces no new CVE surface and no framework-version change to check against NVD.

**doc-reviewer**

- PRD's Specialty directory section stays at the behavioral altitude: no route literal, no field/parameter tables, no internal type names; GET /specialties.html is correctly deferred to system-design.md's Contracts section and the route-and-reachability paragraph, confirming the notes' stated boundary reading holds
- Every REQ-VET-003 Done-when bullet and all three edge cases are testable, plain given/when/then prose with no mechanism leak
- ubiquitous-language.md's new 'Specialty directory' entry is precise, states relationships and an Avoid list, and is used consistently (same term) across prd.md and system-design.md
- system-design.md's three new Contracts rows follow the existing name/purpose/source/Implements shape with no field or parameter tables; the unidirectional-association and route-and-reachability paragraphs state invariants, not mechanism duplicated from source
- ADR 2026-08-23 follows the template: Options Considered records real rejected alternatives with reasons, Consequences records the identity-matching and cache-staleness implications added in the line-8 revision, Implementation carries the Requirements: line, References use em-dashes, and the docs/adr/README.md index line resolves to the file
- Cross-references all resolve: prd.md#req-vet-003 anchor exists and is the only anchor definition (system-design.md and the ADR link to it rather than duplicating), system-design.md#contracts and #known-defects anchors exist, the ADR's link to 2026-07-31-feature-package-organization.md resolves
- REQ-VET-002 stays correctly absent from system-design.md's Contracts table, consistent with its Superseded-list withdrawal in prd.md
- No relative references, no vague/wordy language, no version numbers introduced in the changed docs

**test-reviewer**

- No mocks: SpecialtyDirectoryTests uses only real Specialty/Vet value objects and SpecialtyControllerTests boots a real Spring context against real seeded H2 via TestRestTemplate — a deliberate, correct departure from VetControllerTests' @MockitoBean idiom
- Stable-ordering, multi-specialty-vet, no-specialty-vet-omitted, and first-name-then-last-name display criteria are all covered with derived, non-mystery test data and BDD-style theXShouldY names
- SpecialtyDirectory unit tests correctly probe the ADR'd invert-in-memory design: independent reads matched by stored id (not object identity), defensive copying against caller mutation, and rejection of a specialty absent from the directory with a message naming it
- One-page-no-pagination and standard-navigation-present criteria are covered against the real rendered page

**test-reviewer**

- theSpecialtyDirectoryShouldListASpecialtyNoVeterinarianHolds closes the prior gap: real full-stack read via TestRestTemplate against a method-scoped @Sql-inserted specialty (auto-generated identity column, no collision risk), with an AFTER_TEST_METHOD @Sql delete verified not to leak into the cached H2 context by re-running the full suite and the neighboring VetControllerTests/SpecialtyDirectoryTests green
- rowFor(body, specialtyName) narrows the empty-list assertion to the specialty's own \<tr>, correctly matching the template's per-row \<ul>\<li> structure, so the assertion is load-bearing rather than checking the whole page
- noOtherPageShouldCarryALinkToTheSpecialtyDirectory fetches real / and /vets.html pages, asserts OK status and standard navigation presence, and asserts neither body mentions /specialties.html, closing the actual PRD 'no other page links to it' criterion the prior self-link-only test missed
- getPage(path) refactor is a clean, behavior-preserving generalization with getSpecialtyDirectory delegating to it

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 3 | opus-5 | $5.15 | 17m 40s | 97% |
| `spring-boot-claude:system-design-expert` | 2 | opus-5 | $2.20 | 6m 10s | 92% |
| `(parent)` | 1 | opus-5 | $1.45 | 37m 51s | 94% |
| `spring-boot-claude:product-requirements-expert` | 1 | opus-5 | $1.19 | 3m 17s | 94% |
| `spring-boot-claude:change-grader` | 1 | opus-5 | $0.90 | 2m 31s | 89% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-5 | $0.57 | 3m 38s | 89% |
| `spring-boot-claude:security-reviewer` | 1 | opus-5 | $0.54 | 1m 11s | 86% |
| `spring-boot-claude:doc-reviewer` | 1 | sonnet-5 | $0.36 | 1m 26s | 91% |
| `spring-boot-claude:code-quality-reviewer` | 1 | sonnet-5 | $0.23 | 53s | 87% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-5 | $0.07 | 9s | 66% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-5 | $3.61 | 11m 28s | 97% |
| `spring-boot-claude:system-design-expert` | opus-5 | $1.63 | 4m 50s | 93% |
| `(parent)` | opus-5 | $1.45 | 37m 51s | 94% |
| `spring-boot-claude:feature-implementer` | opus-5 | $1.19 | 5m 8s | 95% |
| `spring-boot-claude:product-requirements-expert` | opus-5 | $1.19 | 3m 17s | 94% |
| `spring-boot-claude:change-grader` | opus-5 | $0.90 | 2m 31s | 89% |
| `spring-boot-claude:system-design-expert` | opus-5 | $0.57 | 1m 20s | 88% |
| `spring-boot-claude:security-reviewer` | opus-5 | $0.54 | 1m 11s | 86% |
| `spring-boot-claude:doc-reviewer` | sonnet-5 | $0.36 | 1m 26s | 91% |
| `spring-boot-claude:feature-implementer` | opus-5 | $0.35 | 1m 3s | 91% |
| `spring-boot-claude:test-reviewer` | sonnet-5 | $0.35 | 2m 22s | 88% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-5 | $0.23 | 53s | 87% |
| `spring-boot-claude:test-reviewer` | sonnet-5 | $0.22 | 1m 16s | 89% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-5 | $0.07 | 9s | 66% |

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
