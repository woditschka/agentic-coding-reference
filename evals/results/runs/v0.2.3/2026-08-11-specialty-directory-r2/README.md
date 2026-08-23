# specialty-directory r2 — v0.2.3

Specialty directory page (feature) · started 2026-08-11T14:40:13+00:00 · exec `claude-dev` · status **complete**

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

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $14.56 | 47m | 36 | 93% | 11 file(s) +609/−4 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.06 | 3m 28s | 90% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPC-001 — Reader opens a specialty directory listing every specialty with the veterinarians holding it

2 review rounds · 2 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | **✔** | · |
| **security** | **✔** | · |
| **doc** | ✎ (2) | **✔** |

- ◇ **prd-entry** Reader opens a specialty directory listing every specialty with the veterinarians holding it · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 11m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · audit-autofix · handoff-validate
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 20s***
- ✎ **review doc** · **changes_requested** · (2 findings) · ***◷ 3m***
  - [autofix] `prd.md:12` New provenance sentence uses a relative reference ("the provenance above"), prohibited under the Structural Checks ("No relative references — above, below, previous").
    - fix: \> `REQ-SPC-001` is the one exception to this note's default provenance. The product owner stated it on 2026-08-11, so it records intent rather than reconstruction.
  - [clarify] `system-design.md:109` The new `SpecialtyController` contract row states the literal route ("GET /specialties.html") in the Purpose column. No other controller row in the table states its literal mapping path — `VetController` (line 106) and `OwnerController` (line 97) describe behavior only, leaving the route to source. This is the kind of constant-literal-value mirroring the Abstraction-Level self-test flags (a route rename would silently invalidate the row), and it is the only row in the table doing it, breaking the established convention. The requirement's "reached by its address alone" acceptance criterion arguably justifies recording the address once for discoverability, but that reasoning would apply to VetController's route too and it does not carry one. Confirm whether stating the literal route here is a deliberate exception (and if so, note why elsewhere on the page or apply the same treatment to sibling controllers) or whether this row should follow the existing convention and drop the literal path.
- ✚ **prd-autofix** `docs/prd.md` · writing-standards · (root)
- ↻ **fix design** ← doc · (2 findings)
- ◈ **design-block** **new** · (design) · ***◷ 2m***
- ↻ **implement** (implementer) ← doc · (2 findings) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · audit-autofix · handoff-validate
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 30s***
- ✔ **review doc** · **approved** · ***◷ 2m***
- ◆ **grade CLEAR** · add read-only specialty directory page
  - blast_radius — **clear** — Eleven files but nothing existing is edited outside docs: all four production files and all three test files are new, confined to the vet feature package plus one new template directory. No schema, build, config, message-bundle, or layout-fragment change, no sensitive path, and the new GET /specialties.html route collides with nothing. The only shared surfaces touched are three documentation files.
  - semantic_surprise — **clear** — The hunks do what their size and description promise. I checked the traps this shape invites and each is clean: vets arrive from a cached repository but Vet maps specialties EAGER, so getSpecialties() on detached instances cannot throw; pairing goes through persisted id rather than reference or name, which is the correct choice given the cached-versus-uncached read; the template renders every dynamic value through escaping th:text with no unescaped inlining; the layout is invoked with a menu name matching no existing entry, so no navigation link appears; and the three message keys the page uses already exist in the default bundle and in every non-empty locale bundle, so REQ-LANG-002 holds without new keys. Two residuals, both deliberate and disclosed in the ADR: two unsaved entities would pair with each other since Objects.equals of two nulls is true, unreachable from repository reads; and veterinarians sort by last name while rendering first-then-last.
  - test_adequacy — **clear** — Eight tests that would fail against a broken implementation rather than restate it. The ordering test feeds an unordered list and asserts an exact sorted sequence; the per-specialty test feeds veterinarians in reverse and asserts the corrected order, so it pins the comparator rather than input order; the omission test asserts exactly the holding veterinarian; the empty-clinic case asserts empty entries. The link-absence test walks every template for the literal route with a non-empty guard against a vacuous pass. Directory tests use real Specialty and Vet objects with no mocks; only the repository seams at the controller are stubbed. Minor gaps: no two-veterinarians-same-last-name case exercising the first-name tiebreak, and the no-paging assertion is a proxy on absent page markup.
  - reviewer_hedging — **clear** — All four latest verdicts are approved with empty findings lists. The first round carried one doc changes_requested holding an autofix and one clarify tagged with a consistent-with-codebase bar clause about a literal route in the contracts table; it was resolved on the merits by moving the address into the Constants table, and the doc reviewer's second approval endorses that reasoning specifically rather than merely accepting it. Security and test reviewers are silent in the fix round because the risk-proportional plan scoped a docs-only fix delta, which the code-quality reviewer independently verified by diffing trees; that silence is expected, not a hedge.
  - scope_deviation — **clear** — Zero build retries and zero consultations. The one design revision was the recorded design-mismatch abort, which the record itself diagnoses as a bookkeeping gap in the design block's declared doc paths with no code defect, and the superseding block closed it. Reading the diff against the requirement, every file serves the stated surface: the page, its read model, its repository, its tests, the PRD entry, the ADR, and the design rows. The only edit reaching past the slice is a general provenance convention in system-design.md for marking designed-but-unlanded statements, which is small and was doc-reviewed.
  - why — A self-contained additive feature: new files only, no existing production code touched, escaped output, no request-derived input, and tests that pin ordering and filtering rather than restate them. The eager-fetch and identity-pairing traps I checked are all handled. Confirm and merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyDirectory is a well-documented immutable read model: private constructor, static factory  of , final class, javadoc explains the why (inverted association, Java-side ordering, identity-based pairing) rather than restating the what
- The BY_VETERINARIAN_NAME comparator's explicit  (Vet veterinarian) -> veterinarian.getLastName()  lambda instead of a  Person::getLastName  method reference is not a style regression: verified by compiling both forms — the method-reference chain fails javac type inference (Comparator\<Person> is not assignable to Comparator\<Vet>) while the explicit-parameter lambda fixes the target type; the current code is the necessary form
- Pairing by persisted id (not reference or name) is judged sound: VetRepository.findAll() is @Cacheable("vets") while SpecialtyRepository's read is uncached, so the same row arrives as two distinct instances and reference-equality pairing would silently yield no holders; Specialty.name carries an index but no uniqueness constraint (checked db/h2/schema.sql), so name-based pairing risks merging distinct rows. The one-line javadoc on  holds()  states this rationale in the code itself, not only the ADR
- SpecialtyDirectory declaring no equals/hashCode is judged sound and properly bounded: its contents are persisted JPA entities with identity-only equality, so a field-wise equals would present a value-equality contract the type cannot honor; the divergence from the architecture-principles Value-object row is stated in both the class javadoc and the ADR's Consequences section, scoped to this one type only
- SpecialtyController and SpecialtyRepository mirror the established VetController/VetRepository and PetTypeRepository precedents (package-private controller, constructor injection, \<code> javadoc tag style, GET-only mapping resolving templates/\<feature>/) with no unjustified deviation
- checkFormat passes clean on the change set; no checkstyle or format issues in the four new production files or the template

**security-reviewer**

- No new attack surface class: GET /specialties.html takes no path variable, query parameter, request body, or @ModelAttribute, so there is no request-derived value anywhere in the new code. Nothing to validate at the boundary because nothing crosses it.
- Data access is a Spring Data derived findAll() on SpecialtyRepository plus the existing cached VetRepository.findAll(). No @Query, no createQuery, no string-concatenated query text. The injection-into-data-access row of security-principles.md passes.
- Output escaping is intact. specialtyList.html renders every dynamic value through th:text (entry.specialty.name, veterinarian.firstName/lastName) with Thymeleaf default escaping on. Swept the template for the whole XSS class: no th:utext, no [( )] unescaped inlining, no th:inline, no th:onclick/th:href/th:src, no script block. Stored specialty and veterinarian names therefore cannot break out as markup.
- Exposure judgment: the new unauthenticated route publishes veterinarian full names and specialty names, which the baseline already publishes unauthenticated at /vets.html and, unpaged and in full, at the /vets @ResponseBody route. The change discloses no data class not already reachable at the same trust level and adds no PII beyond it, so it does not leave the application weaker than the Security Context baseline in system-design.md. The exposure is stated in the PRD and in system-design.md #contracts, satisfying the 'a change that adds an endpoint states what it exposes and to whom' row.
- Unbounded render judged and cleared as a security matter: the whole specialty set plus the vet set render on one page by product decision, and the pairing is an in-memory nested scan. The vet side is served from the declared cache; only the specialty read reaches the database per request, over a lookup-scale table. The pre-existing /vets route already performs an unpaged full-collection read, so this is not a new class and not a regression against baseline. Recorded as an accepted characteristic, not a finding; the ADR already names the large-roster case as needing a different read path.
- No new endpoint mutates state and none accepts serialized input. The controller returns a fixed view name (no request-derived view or resource path, so no path-traversal or template-injection vector) and carries no @ResponseBody, so no content-negotiated representation is added. Mass-assignment and identifier-tampering rows do not apply: no request-bound type is introduced, hence no @InitBinder disallow list is owed.
- No secret material introduced. Swept the three new Java files, the template, and the three test classes for password/secret/token/key/credential names: no hits. No new logging and no new exception message, so nothing new can reach the error page that renders exception text.
- Supply chain clean: the change set touches no build.gradle, pom.xml, gradle wrapper, or settings file, and adds no dependency. dependencyCheckAnalyze and a dependencies diff would report against an unchanged graph, so neither was run.
- The unlinked address is correctly framed as a product decision in the PRD and ADR, not claimed anywhere as a security control, so nothing in the docs teaches a reader that reachability-by-address-only protects the page.

**test-reviewer**

- All seven test_names from the prd-entry are present and pass: theSpecialtyDirectoryShouldListEverySpecialtyByItsStoredName, theSpecialtyDirectoryShouldListEachHoldingVeterinarianByFirstThenLastName, theSpecialtyDirectoryShouldOmitAVeterinarianHoldingNoSpecialty, theSpecialtyDirectoryShouldShowEverySpecialtyAtOnceWithoutPaging, theSpecialtyDirectoryShouldListASpecialtyHeldByNoVeterinarian, theSpecialtyDirectoryShouldListAVeterinarianUnderEachSpecialtyTheyHold, theSpecialtyDirectoryShouldRenderEmptyWhenTheClinicKnowsNoSpecialty. The design's eighth test, noPageShouldLinkToTheSpecialtyDirectory, covers the negative-link acceptance criterion. jacoco confirms 100% instruction coverage on SpecialtyDirectory, SpecialtyDirectory.Entry, and SpecialtyController, well past the brief's 80% domain-package target
- Verified the implementer's claim in design-block line 8: every Specialty and Vet fixture in SpecialtyDirectoryTests (specialty() and vet() factories) and SpecialtyControllerTests explicitly calls setId() with distinct integers (1,2,3), so holds()'s Objects.equals(id,id) pairing is genuinely exercised in theSpecialtyDirectoryShouldListASpecialtyHeldByNoVeterinarian rather than vacuously true from two null ids -- claim confirmed against the actual test code, not just the design narrative
- SpecialtyDirectoryLinkAbsenceTests is a sound pin for the negative criterion for this codebase: cross-checked fragments/layout.html and vetList.html and every th:href in this app's templates is a literal path string ('/vets.html', '/owners/find', etc.), not a computed/variable expression, so the literal-substring sweep across every *.html under templates/ cannot be evaded by a link this codebase's own conventions would produce; Files.walk plus the isNotEmpty() guard also protects against a silently-empty template set masking a false pass
- Edge cases from the prd-entry are all covered with real, distinguishable fixtures rather than invented or degenerate data: edge case 1 (specialty held by no vet) and edge case 2 (vet holding two specialties, listed under each) both use named AssertJ satisfiesExactly/singleElement chains, not loops or branching; edge case 4 (empty clinic) is covered at the controller layer via hasProperty("entries", empty())
- Mocking stays within the brief's policy: SpecialtyDirectoryTests uses only real Specialty/Vet value objects with zero mocks; SpecialtyControllerTests uses @WebMvcTest+MockMvc (the one sanctioned mock, standing in for HTTP transport) with @MockitoBean repositories, mirroring the existing VetControllerTests precedent for the same layer boundary
- AssertJ used throughout with no JUnit assertEquals/assertTrue; three-tier data naming is respected (DENTISTRY/RADIOLOGY/SURGERY named by role, vet()/specialty() factories keep construction out of raw  new ); four-phase structure held with blank-line separation and no phase-comment narration; test names follow the the{Subject}Should{Outcome} BDD school
- I18n acceptance criterion (AC7) needs no new test: SpecialtyController and specialtyList.html use only pre-existing message keys (specialties, name, vets), verified present in all eleven locale bundles under src/main/resources/messages/, so the existing I18nPropertiesSyncTest already covers it without modification

**doc-reviewer**

- PRD boundary holds: REQ-SPC-001's narrative and Done-when bullets stay behavioral; the owner-stated route lives only in system-design.md#contracts, not in the PRD, matching the prd-authoring what/how boundary
- The three new Open Questions (visible entry point, entry order, unheld-specialty marking) are each a real, undecided product question stated at PRD altitude, not a restatement of a design decision already made
- The ADR reads as a decision record: Context/Options/Decision/Consequences/Implementation/References, no patch-log language ("was revised", "previously") despite being edited mid-slice; the Objects.equals-on-null-ids bound is stated plainly in Consequences as a scope bound, not hedged
- docs/system-design.md contract rows for SpecialtyRepository, SpecialtyDirectory, and SpecialtyController plus the invariants paragraph match the landed code: uncached read, Java-side ordering, identity-based pairing, no equals/hashCode, GET /specialties.html mapping, no menuItem/th:href added
- docs/adr/README.md index row is correctly added, in date order, with the standard em-dash-free table format matching sibling rows
- Cross-document coherence holds: REQ-SPC-001 appears in prd.md, all three system-design.md Implements cells, and the ADR's Implementation section; the *(designed)* marks were correctly dropped now that the code has landed
- No sentence added by this change exceeds the 30-word bar; no code blocks, Java constructs, or internal references leaked into the PRD

**code-quality-reviewer**

- Independently verified via scripts/changeset.sh --base-tree \<basis.prev_tree_sha> that the fix-delta touches only docs/prd.md and docs/system-design.md; no src/ file differs from the prior approved build (confirmed by diff content, not by report), so the code-quality approval at line 13 stands unchanged
- ./gradlew checkFormat passes on the current tree

**doc-reviewer**

- docs/prd.md:12 provenance sentence now reads "this note's default provenance" — matches the proposed fix verbatim, no relative reference, edit stayed in bounds (single sentence, no other content touched)
- docs/system-design.md Contracts row for SpecialtyController is behavior-only ("Serves the read-only specialty directory page from a single GET route"), matching the VetController and OwnerController rows and restoring the table's no-literal-route convention
- The address moved to Constants, following the unique_owner_pet_name row's form: value, Source citing the owning file, Description stating load-bearing status beyond the mapping with REQ-SPC-001 cited — reasoning is on the page, not left implicit
- Invariants paragraph's "reached by its address alone" sentence now links to #constants, keeping the property and the address connected
- Constants prose answers the VetController counter-question directly: other routes are reachable through navigation so no requirement pins them, while REQ-SPC-001 pins this one and the PRD names no address, matching the Constants table's established pattern of citing identifiers that are load-bearing in their own right (paralleling unique_owner_pet_name, whose name is itself the operative matched value)
- No other files changed in this fix delta beyond docs/prd.md, docs/adr/README.md, docs/system-design.md; adr/README.md and the ADR file are unchanged from the prior approved round

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $3.84 | 16m 12s | 96% |
| `agent-team:system-design-expert` | 3 | opus-5 | $3.61 | 11m 37s | 92% |
| `(parent)` | 1 | opus-5 | $2.05 | 50m 19s | 96% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.26 | 4m 17s | 92% |
| `agent-team:change-grader` | 1 | opus-5 | $1.06 | 3m 28s | 90% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.05 | 6m 37s | 93% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.60 | 1m 38s | 85% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.49 | 2m 39s | 89% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.40 | 1m 56s | 93% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.07 | 8s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $2.97 | 11m 59s | 97% |
| `(parent)` | opus-5 | $2.05 | 50m 19s | 96% |
| `agent-team:system-design-expert` | opus-5 | $1.57 | 4m 37s | 93% |
| `agent-team:product-requirements-expert` | opus-5 | $1.26 | 4m 17s | 92% |
| `agent-team:change-grader` | opus-5 | $1.06 | 3m 28s | 90% |
| `agent-team:system-design-expert` | opus-5 | $1.05 | 3m 54s | 92% |
| `agent-team:system-design-expert` | opus-5 | $0.99 | 3m 5s | 89% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.64 | 3m 46s | 95% |
| `agent-team:security-reviewer` | opus-5 | $0.60 | 1m 38s | 85% |
| `agent-team:feature-implementer` | opus-5 | $0.44 | 2m 7s | 91% |
| `agent-team:feature-implementer` | opus-5 | $0.42 | 2m 5s | 90% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.42 | 2m 51s | 91% |
| `agent-team:test-reviewer` | sonnet-5 | $0.40 | 1m 56s | 93% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.33 | 2m 1s | 91% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.16 | 37s | 86% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.07 | 8s | 50% |

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

- plugin `agent-team-spring-boot` at `v0.2.3` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.226 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
