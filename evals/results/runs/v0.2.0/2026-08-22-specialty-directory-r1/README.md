# specialty-directory r1 — v0.2.0

Specialty directory page (feature) · started 2026-08-22T21:13:42+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 4 (±0) | 4 (±1) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.69. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 5 · doc-fit 5

> The projection lives in a pure, immutable record ( SpecialtyDirectoryEntry ,  List.copyOf , static  directory(...) ), so the new rule is unit-testable without MVC — exactly the pyramid shift the principles ask for; the controller only delegates and selects a view. The template mirrors the existing  vetList.html  idiom (message keys, trailing-space span). Main structural nit:  /specialties.html  is bolted onto  VetController  rather than a  SpecialtyController  prefixed by the surface it serves. Unit tests are exemplary — behavior names, factories, named constants, four phases, no mocks. Deductions:  radiology.setId(1)  and  "James Carter" / "dentistry", "radiology", "surgery"  are bare literals, and  @MockitoBean SpecialtyRepository  is a framework stub used without stated exception. Docs are thorough: REQ-SPC-001, contract rows, provenance, and three open questions all updated.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The projection is a real value type:  SpecialtyDirectoryEntry  is an immutable record with a defensive  List.copyOf , a pure static  directory(...)  factory, and no framework import, so  VetController.showSpecialtyDirectory  only binds, delegates, and selects a view — no new controller rule.  SpecialtyRepository  follows the Repository pattern and documents why the read stays uncached (shared  vets  key). Unit tests are behavior-named ( theSpecialtyDirectoryShouldOrderHoldersByLastNameThenFirstName ), factory-built, phase-separated, and cover empty, unsaved-id, and multi-hold edges; the MockMvc tests assert raw HTML substrings ( containsString("Helen Leary") ) and add a new  @MockitoBean SpecialtyRepository , a tolerated rather than preferred seam.  specialtyList.html  introduces  #{specialties} ,  #{vets} ,  #{none}  keys with no bundle change visible. PRD REQ-SPC-001, open questions, and the design contracts table are all updated.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The inversion rule sits in an immutable record with a pure factory (SpecialtyDirectoryEntry.directory), keeping the new rule out of the controller, and SpecialtyRepository documents why it stays uncached; deductions are that the specialty surface is bolted onto VetController.showSpecialtyDirectory rather than its own controller, and the controller sequences two reads plus the projection where the sanctioned application service would fit. Unit tests are behavior-named, four-phase, factory-built and framework-free; VetControllerTests leans on MockitoBean and raw containsString markup assertions, and bare literals "James"/"Carter" plus SOME_FIRST_NAME="Helen" used meaningfully blur the data tiers. specialtyList.html introduces #{specialties}/#{none} with no bundle entry in the patch, which the "Specialties" heading assertion depends on. Docs: PRD REQ-SPC-001, edge cases, open questions and the contracts table all move.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $14.23 | 42m | 44 | 94% | 9 file(s) +446/−12 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.04 | 3m 28s | 90% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPC-001 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (2) | **✔** |

- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **minor** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 13m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 40s***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✎ **review doc** · **changes_requested** · (2 findings) · ***◷ 1m***
  - **[blocked]** `prd.md:137` The literal route `/specialties.html` is a mechanism detail (Spring MVC view-resolution path), not a domain behavior — it fails the what/how litmus test (it would change under a different framework or language) and is exactly the class of routing detail `docs/system-design.md` exists to carry. The claim it is 'necessary because the page has no other entry point' does not hold: the same sentence already states the behavior fully without the literal path — 'reached by its own address... and by nothing else: no page carries an entry pointing to it' — and the Done-when bullet on this same requirement already says 'opened at its address' with no literal URL. The document's own established convention elsewhere avoids naming routes (e.g. the Known Defect note describes 'a second route' without naming it). The literal path adds no information the surrounding prose lacks and should be dropped, with the concrete path left to system-design.md's Contracts entry for VetController, which already documents the route.
  - [autofix] `system-design.md:82` The sentence 'SpecialtyDirectoryEntry ... is the only place in the vet package where ordering of that projection is fixed' is inaccurate. Verified against source: SpecialtyRepository.findAll() fixes specialty order via ORDER BY specialty.name (SpecialtyRepository.java:43), and SpecialtyDirectoryEntry.HOLDER_ORDER (SpecialtyDirectoryEntry.java:37-39) fixes only the order of veterinarians within one specialty. The directory's overall order is fixed in two places, not one; SpecialtyDirectoryEntry takes the specialty list in whatever order it is handed (directory(List\<Specialty> specialties, ...) iterates the given order per its javadoc 'in the given order', SpecialtyDirectoryEntry.java:49) and does not fix specialty order itself.
    - fix: Replace 'and is the only place in the vet package where ordering of that projection is fixed' with wording naming both fixed-ordering points, e.g. 'SpecialtyRepository fixes specialty order by name; SpecialtyDirectoryEntry separately fixes the order of veterinarians within one specialty.'
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `VetControllerTests.java:152` theSpecialtyDirectoryShouldRenderEmptyWhenNoSpecialtyExists asserts content().string(containsString("Specialties")) — a bare string literal that happens to match the messages.properties value for the 'specialties' key. Per testing-principles.md Three-Tier Data Naming, this is a Tier 3 mystery value: nothing in the test names it as the expected heading, and a reader can't tell whether "Specialties" is meaningful (asserting page identity) or incidental. Swept the touched test files for the same pattern (grep -F -e '"Specialties"'); this is the only instance.
    - fix: Extract a named constant (e.g. private static final String SPECIALTIES_HEADING = "Specialties";) at class or method scope, or assert against a value read from the same message bundle the template renders from, so the literal's role is explicit.
  - [clarify] `VetControllerTests.java:158-162` theSpecialtyDirectoryShouldCarryNavigationToOwnersAndVeterinarians only asserts the specialties page itself carries no href to /specialties.html — it does not check that any other existing page (vetList.html, owner pages, the layout menu) still lacks a link to the new page, which is the actual PRD acceptance criterion ('no page of the system carries an entry pointing to the specialty directory'). The design-block's mitigation (layout.html left untouched) makes this low risk today, but the test as written would not catch a future regression where a link is added elsewhere — e.g. directly in vetList.html rather than the shared layout fragment. Confirmed via grep that no template currently references specialties.html outside specialtyList.html itself.
- ↻ **fix prd-expert** ← doc, test · (4 findings)
- ◈ **design-block** **minor** · (design) · supersedes L4 · ***◷ 1m***
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 1m***
- ↲ consult **prd-expert** → **?** · The narrowest reading is correct. "No page carries an entry pointing to the specialty directory" binds this change, not the whole template tree in perpetuity. The product owner's words were: "The page is reachable by its URL alone: no navigation entry and no link from another page is part of this request. A visible entry point may come as a follow-up request." That is a statement about the scope of this request, not a standing invariant - and a system-wide assertion would actively fight the named follow-up, failing the moment the entry point everyone expects is added. The acceptance bullet overstated the criterion, so I tightened it: docs/prd.md now carries two bullets where there was one - the directory page carries navigation to owner search and to the veterinarian directory, and separately, this change adds no navigation entry and no link pointing to the specialty directory, on the directory page or on any other. theSpecialtyDirectoryShouldCarryNavigationToOwnersAndVeterinarians as written satisfies both halves for this slice; do not add a sweep over vetList.html, the owner pages, or the layout fragment. The absence of an entry point is deliberate scope, not a protected property. Related change in the same edit: the literal route was dropped from the REQ-SPC-001 prose and from the first acceptance criterion (doc-reviewer blocked finding at docs/prd.md:137, accepted). The behavior is unchanged - the page is reached by its address and nothing else - so no test needs to change on that account; the concrete path stays with VetController.
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · format · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 19s***
- ✔ **review security** · **approved** · ***◷ 25s***
- ✔ **review test** · **approved** · ***◷ 50s***
- ✔ **review doc** · **approved** · ***◷ 40s***
- ◆ **grade CLEAR** · add read-only specialty directory page
  - blast_radius — **clear** — Additive and contained in the vet package: two new prod classes, one new template, and one existing controller touched. The only edit to existing production code is VetController's constructor gaining a second repository, and grep confirms Spring DI is its sole caller. No sensitive path, no build file, no schema, no seed data, no shared layout fragment; the two non-code files are docs.
  - semantic_surprise — **clear** — Read every hunk and found no behavior the diff's shape would not predict. The uncached SpecialtyRepository.findAll is deliberate and correctly reasoned: a second no-argument Cacheable-vets method would collide on SimpleKey.EMPTY and serve veterinarians for specialties. holds() matches on store-assigned id with an explicit null guard rather than object identity, which is right because vets arrive from the cache and specialties do not. Vet.specialties is EAGER, so pulling the cached collection outside a transaction cannot lazy-init. Passing an unmatched specialties menu name to the layout leaves no nav item active, which is the intended no-entry-point behavior, not an oversight.
  - test_adequacy — **clear** — The tests assert real outcomes and would fail against a broken implementation, not restate it. Eight pure unit tests pin the inversion's boundaries with derived expectations (unheld specialty, multi-specialty holder, empty list, holder ordering, unsaved id-less specialty). Five MockMvc tests render the actual Thymeleaf template, so a broken SpEL accessor or missing message key would surface. A real-H2 ClinicServiceTests case pins the JPQL ORDER BY against seeded data, covering the one seam mocks would hide. Sole gap is cosmetic: the template's empty-holders none branch executes in the existing tests but nothing asserts on it.
  - reviewer_hedging — **clear** — All four dispatched reviewers hold round-2 approvals with empty findings lists, and each names the specific round-1 finding it verified resolved. Round 1 carried a doc blocked finding on a literal route in the PRD and a test autofix plus clarify; all three were closed by real edits, not by argument. The doc-reviewer's closing note about the handoff log's dangling cross-reference is a process observation it explicitly scoped out, not a reservation about the change.
  - scope_deviation — **clear** — The diff matches REQ-SPC-001's stated surface exactly and adds nothing beyond it. One mid-flight motion is worth a human's eye but is inward, not outward: the acceptance bullet asserting no page anywhere links to the directory was narrowed to bind this change alone, sourced to a quoted product-owner statement and approved by both the doc- and test-reviewer, and grep confirms no template links today. The row's consultations=0 understates that round because the answer was recorded without a preceding request; design_revisions=1 is the honest signal.
  - why — Additive read-only page, contained in one package, with tests that render the real template and pin the real query. The uncached repository and id-based matching are deliberate and documented. Confirm and merge; if you read one thing, read the narrowed no-entry-point acceptance bullet in docs/prd.md.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Output escaping: specialtyList.html renders every data-derived value through th:text (specialty name, and the vet first/last name concatenation), never th:utext; the fragments/layout.html it composes with adds no unescaped sink for this page. A repository-wide grep for th:utext/unescaped across src/main/resources/templates found no instances, so the stored-name XSS class has no occurrence on the reviewed surface.
- JPQL injection: SpecialtyRepository.findAll carries a constant @Query with no bind parameters, no string concatenation, no SpEL and no Sort/Pageable argument feeding ORDER BY, so there is no injectable fragment. VetController passes no user input into the query path at all.
- Route exposure: GET /specialties.html takes no request parameter or path variable, performs only reads, and is annotated @Transactional(readOnly = true) at the repository. Consistent with NG-1 (no access control by design) for this reference sample.
- Data leakage: the page discloses specialty names and vet first/last names, both already published unauthenticated by /vets.html and the /vets serialized route. The only newly reachable datum is a specialty no vet holds - non-sensitive lookup data and the explicit requirement. No identifiers, credentials, or PII beyond the existing vet directory are exposed.
- Least privilege on the new repository: SpecialtyRepository extends the bare Repository marker and declares findAll alone, so no save/delete/findById surface is inherited and nothing is exposed through Spring Data REST.
- No hardcoded secrets: the change set introduces no credential-, token-, key-, or password-shaped literal; the added Java, template, and test files carry only domain strings.
- Supply chain: the change set touches no build file (build.gradle, settings.gradle, gradle.properties, gradle/ all unchanged), so it adds no dependency and no new CVE surface; the existing dependency set is unchanged by this slice.
- Projection safety: SpecialtyDirectoryEntry matches the association on the store-assigned identity with an explicit null guard, and defensively copies the vets list in the compact constructor, so the rendered model cannot be mutated after construction.

**code-quality-reviewer**

- SpecialtyDirectoryEntry is an immutable record with a defensive List.copyOf in its compact constructor, a well-named static factory (directory), and no get/set-prefixed accessors
- SpecialtyRepository mirrors PetTypeRepository's minimal-surface Repository\<T,Integer> pattern with an explicit ORDER BY query, and its Javadoc documents the deliberate no-@Cacheable decision to avoid colliding with VetRepository's 'vets' cache key space
- VetController.showSpecialtyDirectory follows the existing controller's constructor-injection and Model-attribute conventions with no business logic leaking into the controller
- specialtyList.html matches vetList.html's established template idioms (layout fragment, #{...} for labels, th:text for data, 'none' key for empty holders)
- No swallowed exceptions, no System.out/err, no TODOs, checkFormat passes clean
- Holder ordering (last name, first name, id tiebreaker) is deterministic and covered by a dedicated unit test

**doc-reviewer**

- Provenance banner amendments in prd.md and system-design.md are mutually consistent and correctly scope the survey-era disclaimer to pre-REQ-SPC-001 statements
- New Contracts rows (SpecialtyRepository, SpecialtyDirectoryEntry, updated VetController/Vet/Specialty/VetRepository rows) stay at the source-pointer abstraction level with no field/parameter tables or transcribed constants
- REQ-SPC-001 anchor, Done-when bullets, and edge-case list follow the PRD format and all edge cases from the prd-entry are covered
- No new domain terms introduced; Specialty and Veterinarian are already defined in ubiquitous-language.md
- Open Questions additions are appropriately scoped as open rather than smuggling in resolved mechanism
- docs/system-design.md#contracts anchor referenced from prd.md resolves

**test-reviewer**

- SpecialtyDirectoryEntryTests: 8 unit tests, all pure/no I/O, real Vet/Specialty value objects (no mocks), one behavior asserted per test, BDD the{Subject}Should{Outcome} naming throughout, four-phase structure with blank-line separation and no phase comments, factory methods (createASpecialty/createAVet/createAnUnsavedSpecialty) wrap all construction, edge cases from the PRD (unheld specialty, multi-specialty holder, empty directory, stable ordering, unsaved/id-less specialty) each get a dedicated test with derived expectations (containsExactly against the actual input order)
- VetControllerTests: the added @MockitoBean SpecialtyRepository follows the pre-existing convention already established for VetRepository in the same @WebMvcTest slice — testing-principles.md explicitly tolerates continuing an existing mock-framework stub rather than introducing new debt; not a new violation
- ClinicServiceTests: theSpecialtyReadShouldReturnEverySpecialtyInNameOrder is a genuine integration test against the real H2 fixture data via the real SpecialtyRepository — correctly placed at the integration tier per the brief's mocking policy (real I/O, no mocks)
- All 8 PRD acceptance-criteria test_names are present and exercised across the unit and controller layers; ./gradlew test passes with no failures for the touched packages
- Pyramid shift is consistent with the brief's guidance: the projection logic was lifted into a pure unit (SpecialtyDirectoryEntry) and given 8 unit tests, while the controller slice added only 5 thin wiring tests — moving the ratio toward the target rather than widening the web-layer-test gap

**code-quality-reviewer**

- No production Java or template changed since round-1 approval (line 13); SpecialtyDirectoryEntry.java, SpecialtyRepository.java, VetController.java, and specialtyList.html are unchanged — round-1 findings still hold
- VetControllerTests.java's new SPECIALTIES_HEADING constant replaces a literal with a named, javadoc-documented constant consistent with the existing RADIOLOGY/DENTISTRY constant pattern in the same file
- checkFormat passes clean (task is named checkFormat, not checkJavaFormat, in this project's Spring format plugin setup)

**security-reviewer**

- Round-2 delta is test-only: SPECIALTIES_HEADING constant extraction in VetControllerTests.java (a literal 'Specialties', not a secret); no production code, template, or build-file change since the round-1 approval
- New GET /specialties.html handler takes no request parameter, path variable, header, or body — no user-controlled input reaches the read path, so injection, path traversal, and mass-assignment surfaces are absent
- SpecialtyRepository JPQL is a static @Query string with no concatenation or parameter binding; @Transactional(readOnly = true) keeps the read path non-mutating, consistent with the read-only requirement
- specialtyList.html renders every data-derived value through th:text (escaped) — no th:utext, no th:src/th:href interpolation of stored data, no inline JavaScript; stored-XSS via specialty or veterinarian names is not reachable
- SpecialtyDirectoryEntry is an immutable record with defensive List.copyOf and identity matching on the store-assigned id; no reflection, deserialization, file I/O, or external process invocation introduced
- No new dependency, plugin, or repository declaration this round — supply-chain posture unchanged from the round-1 verification; no hardcoded credential, token, or key in the diff
- Docs-only changes to prd.md and system-design.md are prose; they add no security-relevant claim that contradicts the Security Context, and the design note correctly records the specialty read as uncached (no cross-key cache confusion with the vets cache)

**test-reviewer**

- Round-1 autofix resolved: VetControllerTests.java:56 now names SPECIALTIES_HEADING with a javadoc tying it to the 'specialties' message key the template renders; the assertion at line 158 reads containsString(SPECIALTIES_HEADING). Swept the touched test files (grep -F -e '"Specialties"') for any remaining bare instance of the literal; none found. The implementer's choice to keep the constant rather than inject MessageSource is reasonable: the brief's mocking policy tolerates the existing @MockitoBean convention in this @WebMvcTest slice, and pulling in MessageSource as a real collaborator to source one string would add a dependency to the slice for no behavioral gain the test needs to assert; the javadoc making the provenance explicit satisfies the original Tier-3-mystery-value concern.
- Round-1 clarify resolved by the superseding prd-entry (line 19): the acceptance bullet is split into a navigation-carries bullet and a this-change-adds-no-entry bullet, and the PRD now records a non-goal explicitly rejecting a standing system-wide prohibition. theSpecialtyDirectoryShouldCarryNavigationToOwnersAndVeterinarians already covers both halves for this page (asserts href to /owners/find and /vets.html present, asserts no self-referential href on the specialty page itself); per the consultation-response and the narrowed PRD wording, no sweep of vetList.html/owner pages/layout fragment is required or warranted, since it would fight the named open-question follow-up. Test-to-PRD mapping verified: all 8 test_names in the prd-entry are present and green, split correctly between SpecialtyDirectoryEntryTests.java (unit-tier: listing, no-holder specialty, multi-specialty holder, stable order, holder ordering, unsaved-specialty edge case) and VetControllerTests.java (controller-tier wiring: rendering, navigation).
- ./gradlew test --tests VetControllerTests --tests SpecialtyDirectoryEntryTests --tests ClinicServiceTests passes with no failures; files_changed since round 1 is scoped to the single test file named in build-pass at line 22, matching the fix delta.

**doc-reviewer**

- docs/prd.md:137 no longer names the literal route; the sentence now scopes the no-entry constraint to this change ('confirmed 2026-08-22'), with the escape hatch for a future entry point stated inline as intent, not mechanism — matches the PRD boundary rule
- The former combined Done-when bullet is correctly split into two (lines 144-145): navigation-carried and no-entry-added, each independently testable and each covered by a named test
- docs/system-design.md:82 rewrite verified against source (SpecialtyRepository.java:43 ORDER BY; SpecialtyDirectoryEntry.java:37-39 HOLDER_ORDER; directory() javadoc 'in the given order') — the two-ordering-points claim is now accurate, and the sentence stays at contract level (no line numbers, no framework mechanics)
- The concrete route /specialties.html is absent from both docs/prd.md and docs/system-design.md; VetController's Contracts row (system-design.md:108) describes it behaviorally ('the unpaged specialty directory page') and points at VetController.java as the source of record — this is the correct resting place under the abstraction-level rule (name the constant's owner, do not restate the literal in durable memory), not a gap
- Cross-document coherence holds: REQ-SPC-001 anchor present, all system-design.md Contracts rows citing REQ-SPC-001 have a corresponding requirement in prd.md, and Specialty/Veterinarian/Clinic terms used in both docs match their ubiquitous-language.md definitions

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $4.75 | 16m 1s | 97% |
| `(parent)` | 1 | opus-5 | $2.58 | 45m 1s | 96% |
| `agent-team:system-design-expert` | 2 | opus-5 | $1.93 | 6m 7s | 90% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $1.93 | 5m 32s | 93% |
| `agent-team:change-grader` | 1 | opus-5 | $1.04 | 3m 28s | 90% |
| `agent-team:security-reviewer` | 2 | opus-5 | $0.85 | 1m 22s | 78% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.56 | 3m 9s | 91% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.50 | 2m 45s | 91% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.36 | 1m 39s | 87% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.06 | 7s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.14 | 14m 2s | 98% |
| `(parent)` | opus-5 | $2.58 | 45m 1s | 96% |
| `agent-team:system-design-expert` | opus-5 | $1.38 | 4m 47s | 91% |
| `agent-team:product-requirements-expert` | opus-5 | $1.16 | 3m 18s | 93% |
| `agent-team:change-grader` | opus-5 | $1.04 | 3m 28s | 90% |
| `agent-team:product-requirements-expert` | opus-5 | $0.77 | 2m 14s | 92% |
| `agent-team:feature-implementer` | opus-5 | $0.62 | 1m 58s | 90% |
| `agent-team:system-design-expert` | opus-5 | $0.56 | 1m 19s | 87% |
| `agent-team:security-reviewer` | opus-5 | $0.47 | 48s | 78% |
| `agent-team:test-reviewer` | sonnet-5 | $0.38 | 2m 11s | 92% |
| `agent-team:security-reviewer` | opus-5 | $0.38 | 33s | 77% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.33 | 1m 57s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.25 | 1m 12s | 89% |
| `agent-team:test-reviewer` | sonnet-5 | $0.17 | 57s | 85% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.17 | 47s | 87% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.11 | 26s | 81% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.06 | 7s | 50% |

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
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
