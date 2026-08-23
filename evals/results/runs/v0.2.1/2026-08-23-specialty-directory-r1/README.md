# specialty-directory r1 — v0.2.1

Specialty directory page (feature) · started 2026-08-22T22:02:52+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 4 (±0) | 4 (±0) | 4 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.59. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> The inversion is lifted out of the controller into an immutable record with a pure static factory (SpecialtyHolders.java:47), so VetController.java:69 stays a thin bind-delegate-select adapter and the new rule is unit-testable — exactly the pyramid shift the principles ask for. SpecialtyRepository follows the Repository pattern and documents why it is uncached. SpecialtyHoldersTests is near-exemplary: behavior names, factories, named constants, real objects, blank-line phases; only theSpecialtyDirectoryShouldShowAHoldingVetWhoseSpecialtyIsASeparateInstance asserts identifier-grouping implementation detail. The controller tests regress: directoryRowFor scrapes HTML with a regex and reintroduces bare literals ("radiology", setId(1)). The template concatenates names with a trailing-space hack and renders #{none}, which the PRD's own open question says was not required.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> Inversion logic sits in SpecialtyHolders.directory rather than VetController.showSpecialtyDirectory, so the controller stays a thin adapter and the rule is unit-testable; SpecialtyRepository follows the Repository row and the uncached-cache reasoning is documented. Weaknesses: specialtyList.html introduces #{specialties}, #{vets}, #{none} but no message-bundle entry is visible, despite the PRD asserting the page falls under REQ-LANG-002; and #{none} decides the 'mark unheld specialties' question the PRD records as still open. The template's  vet.firstName + ' ' + vet.lastName + ' '  trailing-space concatenation is a rendering hack. SpecialtyHoldersTests are exemplary (factories, behavior names, phases), but directoryRowFor regex-scrapes \<tr> markup — brittle structural coupling — and isNotSameAs asserts the arrange.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> The inversion lives in  SpecialtyHolders.directory , a record in the vet package, so  VetController.showSpecialtyDirectory  stays a bind-delegate-select adapter with no new rule — right layer, and unit-testable without the framework. Reusing  VetController  rather than a  SpecialtyController  is defensible but slightly stretches the one-surface-per-controller row.  SpecialtyHoldersTests  is exemplary:  the{Subject}Should{Outcome}  names,  createASpecialty / createAVet  factories, named constants, real objects, blank-line phases;  assertThat(heldRadiology).isNotSameAs(listedRadiology)  asserts setup, and  directoryRowFor 's  \<tr>  regex scrape is fragile. Main gap:  specialtyList.html  introduces  #{specialties}  and  #{none} , but no message bundle is added, while the new REQ-SPC-001 text asserts the page's wording falls under REQ-LANG-002 — a claim the patch leaves unbacked. Docs otherwise thorough.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $10.91 | 29m | 25 | 92% | 9 file(s) +399/−11 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.16 | 3m 31s | 93% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPC-001 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | · |
| **doc** | ✎ (2) | **✔** |

- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **minor** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 6m***
  - ▲ **build ✓ clean** · build · test · format · autofix-audit · handoff-log
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 56s***
- ✔ **review security** · **approved** · ***◷ 50s***
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 1m***
  - [autofix] `SpecialtyHoldersTests.java:29-121` The suite's own docstring says SpecialtyHolders.directory() 'inverts a complete specialty list' and the production code keys its grouping map by Specialty id specifically because 'BaseEntity defines no equals/hashCode, so two instances of one specialty are never equal.' Every existing unit test, however, passes the *same* Specialty object reference into both the specialties collection and the vet's addSpecialty(...) call (e.g. theSpecialtyDirectoryShouldShowEachHoldingVetByFullName: `Specialty radiology = createASpecialty(RADIOLOGY); Vet helen = createAVet("Helen", "Leary", radiology);` then `SpecialtyHolders.directory(List.of(radiology), List.of(helen))`). Reference equality would pass every one of these tests just as well as id-based equality, so the hazard the production comment calls out — two detached instances of the same specialty, as happens when a vet's cached specialty and the repository's specialty list are loaded independently — is claimed but not exercised. A regression that swapped the map key from `held.getId()` to `held` (or to the Specialty object itself) would not be caught by this file.
    - fix: Add a test that constructs two distinct Specialty instances sharing one id (e.g. two separate `createASpecialty(...)` calls followed by manually setting the same id, or a factory overload `createASpecialty(id, name)`), passes one instance in the specialties list and the other instance (attached to a vet) in the veterinarians list, and asserts the vet is grouped under that specialty — proving the grouping is by id, not object identity.
  - [autofix] `VetControllerTests.java:123-129` theSpecialtyDirectoryPageShouldShowEachHoldingVetByFullName only asserts content().string(containsString("Helen Leary")) anywhere on the page. It does not verify Helen is listed under radiology specifically (vs. surgery, or floating outside any specialty block), so a bug that put her name in the wrong section, or duplicated her under every specialty, would not be caught. This test also happens to be the only place in the diff where two distinct Specialty instances sharing id=1 flow through directory() (helen() calls radiology() internally for her held specialty, and setup() separately calls radiology() for specialties.findAll()), which is the detached-instance scenario the unit suite is missing — but the weak assertion here means this incidental coverage does not actually prove correct-section placement, only presence somewhere on the page.
    - fix: Scope the assertion to the specialty section, e.g. assert the rendered HTML fragment under the radiology heading contains "Helen Leary" and the surgery section does not, using a targeted content().string(matchesPattern(...)) or an HtmlUnit/Jsoup-based structural assertion instead of a page-wide containsString.
- ✎ **review doc** · **changes_requested** · (2 findings) · ***◷ 1m***
  - **[blocked]** `prd.md:139` The new Specialty directory prose states the literal route "/specialties.html" ("The page is reached at its own address, `/specialties.html`, and nothing links to it"). This is a PRD-boundary violation: a hardcoded HTTP route is mechanism, not behavior. It also breaks the established convention in this same PRD — the sibling Veterinarian directory section (REQ-VET-001) never states its literal path "/vets.html" in prose, and even docs/system-design.md avoids stating literal route strings for either page (it says "a second vet route", "a third route", never the literal path). The "Done when" bullet for this same requirement already gets it right ("opens the directory's address directly", no literal string). Rewrite the narrative sentence to match: state that the page is reachable at an address of its own with no inbound link, without the literal path. If the literal path needs to be on record, it belongs in system-design.md, matching how the Vet route is (not) recorded there.
  - **[blocked]** `system-design.md:35,82` "Specialty directory" is introduced and used repeatedly as a named capability (prd.md heading, narrative, three Done-when bullets, an Open Question — 5+ uses; system-design.md package-structure line and the new state paragraph above the Contracts table) but has no entry in docs/ubiquitous-language.md. The sibling term "veterinarian directory" has the same gap, but this change compounds it by minting a second undefined "X directory" term rather than resolving it. Per the Cross-Document Coherence checklist, a domain term used in prd.md and system-design.md must be defined in ubiquitous-language.md in the same change. Add a "Specialty directory" (and ideally "Veterinarian directory") entry to docs/ubiquitous-language.md.
- ↻ **implement** (implementer) ← test · (2 findings)
- ↻ **fix prd-expert** ← doc · (2 findings)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 44s***
- ↻ **fix design** ← doc · (2 findings)
- ◈ **design-block** **minor** · (design) · ***◷ 31s***
- ▲ **build-pass** 22:27 · build, test, format, handoff-log, autofix-audit
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 1m***
- ◆ **grade CLEAR** · add the read-only specialty directory page
  - blast_radius — **clear** — Nine files but a contained landing: one new GET route, one new repository, one new pure value object, all inside the existing vet feature package, plus three docs and one template. The only edit to existing production code is VetController gaining a second constructor argument, and VetController is package-private with no other construction site in the tree. No schema, dependency, config, or sensitive-path change; the extractor reports zero sensitive paths.
  - semantic_surprise — **clear** — The hunks do exactly what the description implies. SpecialtyHolders.directory keys its grouping map on held.getId() with a comment explaining why (BaseEntity defines no equals/hashCode, specialties.name has no unique constraint), reads Vet.getSpecialties() without mutating cached detached instances, and List.copyOf in the compact constructor makes the record genuinely immutable. The template renders every dynamic value through th:text, so escaping stays on. Existing vet-list behavior is untouched. The one plan-versus-diff discrepancy is benign and I checked it by hand: the design named messages.properties and nine translated bundles as targets, yet no bundle changed, because the template mints no new key and specialties, name, vets, and none already exist in all ten non-English bundles.
  - test_adequacy — **clear** — Tests assert real outcomes rather than restating the implementation. SpecialtyHoldersTests is framework-free over real Vet and Specialty objects and covers each acceptance criterion, including the unheld specialty and the multi-specialty vet. The round-two addition is the load-bearing one: theSpecialtyDirectoryShouldShowAHoldingVetWhoseSpecialtyIsASeparateInstance builds two distinct Specialty instances sharing an id, so reverting the map key from held.getId() to the object would fail it. The web test now scopes its assertion to the specialty's table row, proving section placement rather than page-wide presence.
  - reviewer_hedging — **clear** — The risk plan dispatched the full battery and all four reviewers ended approved with empty findings lists, no escalate tag and no residual caveat. The four round-one bar_clause findings were substantively re-verified rather than waved through, the test-reviewer by a hand mutation check and the doc-reviewer by greps against the document's own convention. One process note surfaced inside an approval, system-design-expert writing docs/ubiquitous-language.md outside its normal write scope, which the author flagged openly and the reviewer judged not to affect correctness.
  - scope_deviation — **clear** — Zero build retries, zero consultations, zero design revisions: the slice never fought its triage. The diff stays on the requirement's stated surface, read-only with no nav entry, no inbound link and no paging, and NG-2 is untouched since the new repository declares findAll alone and the only new mapping is a GetMapping. The two departures from the planned file list both narrow or follow review: no message bundle needed changing, and ubiquitous-language.md was added at the doc-reviewer's explicit direction.
  - why — Read every hunk including the four untracked files. The inversion is id-keyed and mutation-checked by a test, the new route is parameterless and read-only, and no message bundle needed touching because all four template keys already exist in all ten locales. Confirm and merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- Inversion/grouping logic fully isolated in SpecialtyHolders.directory(), keyed by specialty.getId() per the design constraint (getId() comment explains why, since BaseEntity defines no equals/hashCode)
- VetController.showSpecialtyDirectory is a thin delegator with no business rules, consistent with the rest of the controller
- SpecialtyRepository extends the narrow Repository\<Specialty, Integer>, declares no @Cacheable, and its javadoc explains why (JCache does not autocreate unknown caches)
- Vet.specialties EAGER fetch left untouched
- specialtyList.html mirrors the existing vetList.html idiom (th:each span + none fallback) and uses only th:text (auto-escaped), no nav entry added per the no-nav constraint
- Naming (SpecialtyHolders, 'holds'/'holders') matches docs/ubiquitous-language.md's Specialty/Veterinarian relationship wording
- checkFormat task passes clean on the changed files

**security-reviewer**

- Output escaping: src/main/resources/templates/vets/specialtyList.html renders every dynamic value through th:text (specialty.name, vet.firstName/lastName) and message keys through #{}; a repo-wide sweep of src/main/resources/templates/ for th:utext returns no hits, so Thymeleaf default escaping stays on (security-principles.md 'Cross-site scripting' row, system-design.md Threat Model XSS row).
- Injection surface: GET /specialties.html is parameterless — no request parameter, path variable, header, or body reaches any code path. Data access is the Spring Data derived query SpecialtyRepository.findAll() plus the existing VetRepository.findAll(); no string-concatenated query text is introduced (security-principles.md 'Injection into data access').
- No write path: the only new mapping is @GetMapping; SpecialtyRepository declares findAll() alone under @Transactional(readOnly = true) and exposes no save/delete; a grep of the vet package confirms no mutating annotation or persistence call is added. NG-2 is unchanged.
- No mutation of cached detached entities: SpecialtyHolders.directory only reads Vet.getSpecialties(), which returns a fresh sorted list copy, and accumulates references into new local ArrayLists defensively copied by the record's compact constructor (List.copyOf). Cached Vet instances shared across requests are never modified.
- Mass assignment: no request-bound type and no data binder are introduced, so the identifier-disallow requirement does not apply to this change.
- Information disclosure: the page renders only specialty names and veterinarian full names, both already public through the existing /vets.html and /vets routes. No credential, connection string, identifier, or PII beyond that baseline reaches the rendered page or any error path.
- Supply chain: no dependency change — build.gradle, settings.gradle, gradle/, and pom.xml are outside the change set, so no new artifact widens the attack surface and no version needs CVE review.
- Exposed surface: one new unauthenticated read-only HTML route on the same open surface as the existing directory pages; no management endpoint exposure is broadened. The application is not left weaker than the system-design.md Security Context baseline.
- Unbounded result set: the page is deliberately unpaginated per REQ-SPC-001 and reads two small lookup tables (specialties, vets). Availability-only, matching a PRD-stated requirement — no security finding.

**test-reviewer**

- SpecialtyHoldersTests.java is framework-free, uses real Vet/Specialty objects with no mocking, follows four-phase structure with blank-line separation, uses AssertJ fluent assertions throughout (extracting/flatExtracting/containsExactlyInAnyOrder), and avoids asserting any fixed order on the top-level directory list per the PRD's non-goal
- All PRD acceptance criteria (unheld specialty listed, no-specialty vet omitted, multi-specialty vet appears under each, full-name first-then-last, single page/no paging) have a dedicated test each, matching the planned test_names from the prd-entry
- Test pyramid shape is good for this slice: the new domain rule (specialty inversion) lives in a pure unit test class (SpecialtyHoldersTests, no I/O), with only the two necessary web-layer checks added to the existing MockMvc-based VetControllerTests, consistent with testing-principles.md's guidance to push logic-heavy tests to the base of the pyramid
- Coverage is 100% line/branch on SpecialtyHolders.java and VetController.java per jacocoTestReport, well above the 80% domain-package target
- VetControllerTests' continued use of @MockitoBean on VetRepository/SpecialtyRepository is consistent with the brief's pre-existing-suite exemption (mocking only at the pre-existing pattern, not a new violation introduced by this slice)
- ./gradlew test passes cleanly for both changed test files

**doc-reviewer**

- Provenance banner accurately scoped: the added exception sentence correctly names REQ-SPC-001 as specified rather than derived, matching the prd-entry notes
- REQ-VET-002 withdrawal untouched by this slice; the new REQ-SPC-001 id is freshly minted rather than reusing a withdrawn id, per the never-reuse rule
- All cross-references resolve: req-spc-001 anchor exists, system-design.md#contracts heading exists, and every REQ-ID added to system-design.md's Contracts table exists in prd.md
- New system-design.md Contracts rows and state paragraph stay at the correct abstraction level: no field/parameter tables, no literal constants, and each paragraph survives the source-rename self-test
- Structure of the new PRD section (heading, anchor, narrative, Done when, Edge cases, Design link) matches the sibling Veterinarian directory section's shape

**doc-reviewer**

- docs/prd.md:139 rewritten to "The page is reached at an address of its own, and nothing links to it" — literal route /specialties.html removed; matches the sibling REQ-VET-001 section's convention and the already-correct Done-when bullet
- Superseding prd-entry (handoff line 18) is byte-identical to line 2 on id, title, summary, acceptance_criteria, file_targets, test_names, non_goals, and dependencies; only the narrative sentence changed
- docs/ubiquitous-language.md gains well-formed "Veterinarian directory" and "Specialty directory" entries (definition, Relationships:, Avoid:), closing both the flagged gap and its sibling, placed in the file's existing concept order
- Both new terms are now used consistently and only where defined across docs/prd.md and docs/system-design.md (:82, :108); no dangling undefined usage remains
- ubiquitous-language.md provenance banner correctly scoped: the added exception sentence names exactly the two new entries and REQ-SPC-001 as the resolution path, mirroring the PRD banner's approved exception pattern
- Avoid: lines correctly omit "vet list"/"vet listing" — a grep confirms docs/system-design.md:70,80,108 use those short forms, and the entry instead sanctions them consistent with the existing Veterinarian entry's short-form rule
- Literal-route judgement verified: a grep for .html across docs/system-design.md returns no hits; every route in that document is named by role, never by literal path, so keeping /specialties.html out of it is consistent with the document's standing convention and its source-is-authoritative-for-constants directive
- Write-scope tension (system-design-expert writing ubiquitous-language.md outside the foundational-triage path) does not affect document correctness: content, format, and placement all meet the checklist regardless of author

**test-reviewer**

- SpecialtyHoldersTests.theSpecialtyDirectoryShouldShowAHoldingVetWhoseSpecialtyIsASeparateInstance now constructs two distinct Specialty instances sharing one id via the new createASpecialty(int id, String name) overload and asserts isNotSameAs plus id-based grouping; verified by hand that keying holdersBySpecialtyId by the Specialty object instead of held.getId() would make holdersBySpecialtyId.getOrDefault(listedRadiology, ...) miss the entry stored under heldRadiology, failing this test as claimed
- All five original SpecialtyHoldersTests cases are untouched and still pass; no ordering is asserted on the top-level directory list
- SpecialtyHolders.java is unchanged from its original id-keyed form (holdersBySpecialtyId.computeIfAbsent(held.getId(), ...)) confirming the reported mutation-check revert; the file remains untracked/new for this feature slice with no production code touched in this fix round
- VetControllerTests.theSpecialtyDirectoryPageShouldShowEachHoldingVetByFullName now scopes its assertion via a new directoryRowFor(page, specialtyName) helper (regex \<tr[^>]*>(.*?)\</tr> with DOTALL) and asserts the radiology row contains "Helen Leary" while the surgery row does not; the specialtyList.html template has a single non-nested \<tbody>\<tr> structure per specialty so the non-greedy row regex is safe here and not falsely passing
- helen() and setup() in VetControllerTests each call radiology() independently, producing two distinct Specialty instances sharing id=1, so this MockMvc test incidentally exercises the same detached-instance scenario at the web layer, and the tightened row-scoped assertion now actually proves correct-section placement rather than page-wide presence
- No new test dependency was introduced; the fix reuses AssertJ, java.util.regex, and the pre-existing org.hamcrest.Matchers import
- ./gradlew test passes cleanly for the full suite including both changed test files

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $3.01 | 10m 53s | 95% |
| `agent-team:system-design-expert` | 2 | opus-5 | $2.52 | 7m 31s | 91% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $1.49 | 3m 59s | 91% |
| `(parent)` | 1 | opus-5 | $1.26 | 32m 16s | 94% |
| `agent-team:change-grader` | 1 | opus-5 | $1.16 | 3m 31s | 93% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.64 | 3m 10s | 92% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.54 | 53s | 83% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.48 | 2m 59s | 87% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.23 | 1m 2s | 91% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.08 | 11s | 74% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $2.03 | 6m 55s | 96% |
| `agent-team:system-design-expert` | opus-5 | $1.54 | 4m 23s | 91% |
| `(parent)` | opus-5 | $1.26 | 32m 16s | 94% |
| `agent-team:change-grader` | opus-5 | $1.16 | 3m 31s | 93% |
| `agent-team:product-requirements-expert` | opus-5 | $0.99 | 2m 59s | 92% |
| `agent-team:feature-implementer` | opus-5 | $0.98 | 3m 58s | 95% |
| `agent-team:system-design-expert` | opus-5 | $0.98 | 3m 8s | 91% |
| `agent-team:security-reviewer` | opus-5 | $0.54 | 53s | 83% |
| `agent-team:product-requirements-expert` | opus-5 | $0.50 | 1m 0s | 88% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.39 | 2m 0s | 92% |
| `agent-team:test-reviewer` | sonnet-5 | $0.27 | 1m 39s | 87% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.25 | 1m 9s | 93% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.23 | 1m 2s | 91% |
| `agent-team:test-reviewer` | sonnet-5 | $0.21 | 1m 20s | 87% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.08 | 11s | 74% |

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
