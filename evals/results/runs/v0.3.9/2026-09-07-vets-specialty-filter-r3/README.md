# vets-specialty-filter r3 — v0.3.9

Filter the vet list by specialty (feature) · started 2026-09-06T23:39:54+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Feature request: filter the vet list by specialty. Three product decisions
> come with it, made here as the product owner:
> 
> - Non-goal NG-9 is narrowed: free-text veterinarian search stays out of
>   scope, but filtering the directory by an attribute it already shows is in.
>   Record the narrowing the way the project records non-goal changes.
> - The JSON endpoint at /vets is reinstated as a supported surface — this
>   filter is its first requested capability. Mint a fresh requirement for it;
>   the withdrawn REQ-VET-002 stays withdrawn and its id is not reused.
> - The filter is a URL contract only. Neither surface gains a form, dropdown,
>   or other page control in this request; pagination links carry the
>   parameter so filtered pages stay navigable. A visible control may come as
>   a follow-up request.
> 
> Both vet list surfaces accept an optional  specialty  query parameter:
> 
> - /vets.html?specialty=<name> — the HTML page shows only vets holding that
>   specialty; pagination applies to the filtered list.
> - /vets?specialty=<name> — the JSON endpoint returns only those vets.
> 
> Matching is on the whole specialty name, case-insensitive — not a prefix. A
> specialty matching no vet yields the normal page or JSON document with an
> empty vet list (HTTP 200). An empty or whitespace-only value behaves as if
> the parameter were absent, like the empty owner search. Without the parameter
> both endpoints behave as today. Cover the new behavior with tests.
> 
> These are all the product decisions; no further product answer will come
> during the work. Where a choice still seems open, take the narrowest reading
> consistent with this request and record the open question rather than
> waiting.

## Verdict

| check | result |
|---|---|
| oracle | ✔ 5/5 passed |
| suite (post-agent) | ✔ |
| suite (pristine baseline) | ✔ |
| checkpoints | 8/8 |
| reading depth (pipeline grade) | scrutinize |

The pipeline grade estimates how much human review the change deserves before merge — advisory context from the harness's change grader (read from the ledger's `grader-verdict` record), never part of the bar.

- ✔ `theSpecialtyFilterShouldMatchCaseInsensitively` — passed
- ✔ `theSpecialtyFilterShouldNarrowTheHtmlVetList` — passed
- ✔ `theSpecialtyFilterShouldNarrowTheJsonVetList` — passed
- ✔ `theUnknownSpecialtyShouldYieldAnEmptyVetList` — passed
- ✔ `theVetListShouldShowTheFirstPageWithoutAFilter` — passed

## Checkpoints

The kind's graded ladder, derived from the recorded facts — context only, outside the quality bar (bench README § Checkpoints).

- ✔ `agent complete`
- ✔ `change produced`
- ✔ `suite green`
- ✔ `theSpecialtyFilterShouldMatchCaseInsensitively`
- ✔ `theSpecialtyFilterShouldNarrowTheHtmlVetList`
- ✔ `theSpecialtyFilterShouldNarrowTheJsonVetList`
- ✔ `theUnknownSpecialtyShouldYieldAnEmptyVetList`
- ✔ `theVetListShouldShowTheFirstPageWithoutAFilter`

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 4 (±1) | 4 (±0) | 4 (±0) | 5 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.70. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering is delegated to derived repository finders ( findBySpecialtiesNameIgnoreCase ); the controller only normalizes blank input ( namedSpecialtyOrNull ) and picks a call, which stays inside the Web controller row, though the null-branch ternary is duplicated in  findPaginated  and  findVets . The uncached-narrowed-read Javadoc justifies a real design choice. Tests are behavior-named and cover case-folding, partial names, empty results, multi-page parameter carry, and link encoding; weaker points are two acts inside assertions ( theVetDirectoryShouldNotMatchPartOfASpecialtyName ), an assertion in the arrange phase of  theVetDirectoryShouldOmitAVetHoldingNoSpecialty , bare expected literals ("Leary", "Stevens"), and  pageSize = 5  duplicated from the controller. Documentation is complete: ADR, ADR index, NG-9 narrowing, REQ-VET-003, superseded note, contracts table, and the removed known-defect row.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Controller stays a binder/delegator:  namedSpecialtyOrNull  normalizes blank input once and  findPaginated / findVets  only dispatch, while matching lives in derived repository queries whose Javadoc explains why  @Cacheable("vets")  is withheld — a genuine reasoned constraint. Minor debt: the null-sentinel ternary is duplicated across both routes. The template switch to  @{/vets.html(page=...,specialty=${specialty})}  fixes encoding and is covered by the markup-carrying-specialty test. Tests are behavior-named, phase-separated, and cover case, prefix, empty, multi-page, and JSON paths; but  EntityUtils.getById(..., 1)  and bare  "Leary" / "Stevens"  are mystery values,  theVetDirectoryShouldNotMatchPartOfASpecialtyName  acts twice, and an assertion sits in the arrange phase. Docs move everywhere the change touches: new ADR, ADR index, NG-9 narrowing, REQ-VET-003 with done-whens, the superseded REQ-VET-002 note, the retired known-defect row, and the cache open question.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 4

> Filtering is delegated to a derived repository finder ( findBySpecialtiesNameIgnoreCase ), leaving VetController with binding/normalization only ( namedSpecialtyOrNull ), which system-design assigns to the web layer; the cache exclusion is reasoned in the repository javadoc. Tests are BDD-named and mostly four-phase, but ClinicServiceTests leans on bare literals ("Leary", "Stevens", "Douglas",  getById(..., 1) ), asserts inside arrange in theVetDirectoryShouldOmitAVetHoldingNoSpecialty, and theVetDirectoryShouldNotMatchPartOfASpecialtyName fuses two acts.  aPageOfHoldersSpanningTwoPages  re-hardcodes the controller's private pageSize 5, a quiet coupling. Docs move thoroughly — ADR, NG-9 narrowing, REQ-VET-003, contracts table, defect row removal — but the PRD preamble now claims "twelve further questions" after adding three to ten.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.77 | 35m | 30 | 94% | 9 file(s) +338/−24 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.93 | 2m 33s | 88% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Veterinarian directory narrows to one named specialty on both surfaces

2 review rounds · 2 build-passes · **1 build-failure** · grade **SCRUTINIZE**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- • intake-decision (human)
- ◇ **prd-entry** Veterinarian directory narrows to one named specialty on both surfaces · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **minor** · (design) · ***◷ 23s***
- ◆ **implement** (implementer) · ***◷ 13m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **minor** · (design) · supersedes L5 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply-chain check not run: the project configures no OWASP Dependency-Check plugin (no dependencyCheckAnalyze task in build.gradle), and this reviewer has no network access, so no NVD match was performed. Spring Boot 4.1.1 (build.gradle:5) with managed transitive versions was read but NOT verified against the NVD. The change set adds no dependency, so this is a standing gap for CI or a human to close, not a regression this slice introduces.
  - ▹ rec: Vet.specialties is @ManyToMany(fetch = EAGER), so the new paged derived query joins a fetched collection; Hibernate may apply the page limit in memory for such queries. The pre-existing findAll(Pageable) has the same shape and the row count is not attacker-influenced (specialty assignment is not a public write path), so this is a scale note rather than a reachable denial-of-service. Worth an integration-level check only if the vets table is ever expected to grow.
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `ClinicServiceTests.java:274` The specialty value passed to findBySpecialtiesNameIgnoreCase is the bare literal "radiology" instead of a named variable. Every sibling test in the same method added by this slice names the identical value by role (specialtyHeldByTwoVets, heldSpecialtyInAnotherCase, heldSpecialtyWithSurroundingSpaces) per testing-principles.md's Three-Tier Data Naming Convention (Tier 1: meaningful value, role-describing name). This one instance is the only mystery literal found in the diff; the rest of the new test code already follows the convention.
    - fix: Introduce a local variable, e.g. `String aSpecialtyHeldByAVet = "radiology";`, and pass it to findBySpecialtiesNameIgnoreCase in place of the bare literal.
- ✔ **review code-quality** · **approved** · ***◷ 2m***
- ↻ **implement** (implementer · routine) ← test · (1 finding) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved** · ***◷ 55s***
- ◆ **grade SCRUTINIZE** · narrow the vet directory by a named specialty
  - blast_radius — **skim** — Nine files in one module, no sensitive paths; production reach is the vet controller, its repository interface, and its template. Both existing routes gain one optional parameter whose absent or blank value takes the pre-change code path, so every existing caller's default behavior is untouched.
  - semantic_surprise — **skim** — The narrowing is a Spring Data derived query with case folding expressed in the query rather than left to schema collation, which sidesteps the shape of the known PostgreSQL owner-search defect; the blank-to-null normalization is one helper shared by both routes; the template's pagination links move from string preprocessing to link expressions that URL-encode. No inverted condition, boundary shift, or silent change to the unfiltered path.
  - test_adequacy — **skim** — Matching semantics (whole name, case-insensitive, no prefix match, surrounding spaces, multi-specialty vet, specialty-less vet, no-holder specialty) are asserted against the real H2 database, so the derived-query resolution is proven rather than assumed. The controller tests extract and follow the actually rendered pagination link and would fail on an unstubbed repository call, so they discriminate; a markup-carrying payload pins the link encoding.
  - reviewer_hedging — **scrutinize** — The full battery approved in round one and the test-reviewer's single autofix was cleanly re-approved in round two on a scoped roster, but the security approval parks two caveats in recommendations: no dependency-check ran (a standing project gap, no dependency added here), and the eager specialties collection means Hibernate may apply the page limit in memory for the new paged derived query. The second is a live property of code this slice adds.
  - scope_deviation — **skim** — Intake authorized exactly this surface: both routes, the NG-9 narrowing recorded as an ADR, a fresh requirement id with REQ-VET-002 left withdrawn, and a URL-only contract with no page control. The one design revision was a bookkeeping supersede adding the docs paths to the design-block path list so the autofix audit covered them, not a change of design.
  - why — Reviewers approved unanimously and the code reads as it advertises. Before merging, glance at the security reviewer's parked note: the eager specialties collection means the new paged query may apply its page limit in memory. Harmless at fixture scale, worth knowing if the vets table ever grows.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Data-access injection: the specialty filter reaches the database only through Spring Data derived queries (VetRepository.findBySpecialtiesNameIgnoreCase, paged and unpaged). No query text is concatenated and no request-derived value composes JPQL/SQL. Case folding is in the query, not in a hand-built predicate.
- XSS / template escaping: the request-derived specialty reaches the page only as a link-expression parameter (@{/vets.html(page=...,specialty=${specialty})}), which URL-encodes it. Thymeleaf default escaping stays on, no th:utext or inline JavaScript is introduced, and VetControllerTests.theVetDirectoryShouldEncodeTheNamedSpecialtyItPutsInPageLinks pins the behavior with a markup-carrying payload.
- Template-expression injection: the change removes the pre-existing __${...}__ preprocessing from every vetList.html pagination link and replaces it with link expressions, so no request-derived text can reach Thymeleaf preprocessing on this page. The remaining __${...}__ occurrences (fragments/layout.html, fragments/inputField.html, fragments/selectField.html, owners/ownerDetails.html, owners/ownersList.html) are outside the change set and carry only entity identifiers, fragment-fixed field names, and computed page numbers.
- Cache poisoning / unbounded key space: the two new reads are deliberately not @Cacheable, so a request-supplied name cannot grow the eviction-less "vets" cache. The rationale is recorded inline in VetRepository.
- Exposed surface: no new endpoint or management exposure. Both existing routes (/vets.html, /vets) gain one optional request parameter; an absent, empty, or whitespace-only value falls back to the pre-change unfiltered behavior (VetController.namedSpecialtyOrNull), so the default state is the prior state.
- Mass assignment: the parameter binds as a plain @RequestParam String, not through a command object, so no binder allowlist is at stake and no identifier becomes bindable.
- Credentials and logging: no secret-shaped literal, no new logging, no System.out/System.err, no error message carrying the request value outward. Both new repository methods are @Transactional(readOnly = true) — least privilege on the data access.
- Path traversal, deserialization, shell execution, file I/O, network calls, randomness: the diff introduces none of these. No Runtime/ProcessBuilder, no Files/FileWriter, no Jackson polymorphic typing, no XML parsing.
- Supply chain: build.gradle and the dependency set are untouched by this change set, so no new artifact enters the build.

**doc-reviewer**

- PRD REQ-VET-003 prose stays behavioral (no class/method names, no code) and pairs each behavior with a tagged Done-when bullet, per document-writing boundary rules
- system-design.md Contracts rows for Vets/VetRepository/VetController updated to carry REQ-VET-003 alongside REQ-VET-001, matching the actual Implements-column requirement for changed types
- New ADR (2026-09-06-non-goal-veterinarian-search.md) correctly narrows NG-9, is indexed in adr/README.md, and cross-links resolve (prd.md#non-goals, prd.md#req-vet-003)
- Removed the now-stale Known Defects row ('machine-readable route serves no requirement') and updated the cache Open Question wording ('whole-directory reads' vs 'read methods') to stay accurate against the new VetRepository code
- Verified against source (VetController.java, VetRepository.java, vetList.html): case-insensitive full-name matching, uncached narrowed queries, and specialty-preserving pagination links all match the PRD/system-design claims
- No new domain terms introduced; 'Specialty' is already defined in ubiquitous-language.md and used consistently
- No prohibited patterns found: no field/parameter tables, no constant literals, no imperative lines lacking an ADR back-link, no hard-wrapped prose

**test-reviewer**

- Test placement matches the design-block's assignment: whole-name/case-insensitive/no-partial-match matching semantics are asserted against a real database in ClinicServiceTests, while VetControllerTests (MockMvc, the one sanctioned mock boundary) covers routing, pagination, and blank-value handling only — exactly the split the design-block's risk section called for
- All 8 PRD Done-when bullets and both new edge cases (vet holding no specialty, vet holding several specialties) have dedicated, correctly named tests per the coverage-map
- New tests use AssertJ fluent assertions throughout (extracting, containsExactlyInAnyOrder, isEmpty, doesNotContain), no JUnit assertEquals/assertTrue
- Test names follow the the{Subject}Should{Outcome} BDD school from testing-principles.md
- No raw production-type construction in the new test code; EntityUtils.getById and the existing helen()/james() factories are reused instead of new Vet()/new Specialty()
- theVetDirectoryShouldEncodeTheNamedSpecialtyItPutsInPageLinks gives the Thymeleaf-encoding security mitigation named in the design-block's risk list its own adversarial test, asserting the rendered pagination links neither carry raw markup nor break out of the href attribute
- @ParameterizedTest with @ValueSource covers the blank/whitespace-only specialty case on both surfaces instead of copy-pasted tests
- ./gradlew test passes; the whole suite is green

**code-quality-reviewer**

- VetController's namedSpecialtyOrNull mirrors the existing OwnerController blank-parameter pattern (src/main/java/.../owner/OwnerController.java:95-104) rather than inventing a new one; the request-presence check (blank vs. named) is HTTP-adapter normalization, distinct from the domain-level whole-name, case-insensitive match, which correctly lives in VetRepository's derived query rather than in the controller.
- VetRepository's Javadoc explains two non-obvious decisions inline (why case folding is expressed in the query rather than left to schema collation, and why the narrowed reads are deliberately left off @Cacheable) — a future reader gets the reasoning without needing to consult the handoff log.
- Pagination links use the Thymeleaf link-expression form (@{/vets.html(page=...,specialty=...)}) for the request-supplied specialty rather than string concatenation, so the value is encoded rather than injected verbatim.
- docs/system-design.md, docs/adr/README.md, and docs/prd.md updates are consistent with the landed code: the VetRepository/VetController/Vets contract rows, the Known Defects removal, and the NG-9 narrowing all match what the diff actually does.
- New domain-facing names (specialty request parameter and model attribute, namedSpecialty local/parameter naming) use the terms docs/ubiquitous-language.md defines; no coined synonyms.
- ./gradlew checkFormat passes; no formatting findings.

**test-reviewer**

- Round-1 autofix applied exactly as specified: the bare literal "radiology" in theVetDirectoryShouldOmitAVetHoldingNoSpecialty is now the role-named local aSpecialtyHeldByAVet, matching the naming pattern of every sibling test in the method (heldSpecialtyInAnotherCase, prefixOfAHeldSpecialty, heldSpecialtyWithSurroundingSpaces, oneSpecialtyOfATwoSpecialtyVet, specialtyNoVetHolds)
- Fix is test-only, confined to the single flagged line plus the declaration; no production code touched, no new mystery literals introduced elsewhere in the fix delta
- Four-phase structure preserved: the new declaration sits in the arrange phase, blank line still separates arrange from act
- ./gradlew test (ClinicServiceTests) passes; whole suite green per the build-pass record

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $5.06 | 17m 17s | 97% |
| `agent-team:system-design-expert` | 2 | opus-5 | $2.21 | 5m 25s | 93% |
| `(parent)` | 1 | opus-5 | $1.22 | 37m 1s | 96% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.19 | 3m 42s | 90% |
| `agent-team:change-grader` | 1 | opus-5 | $0.93 | 2m 33s | 88% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.63 | 1m 28s | 87% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.61 | 3m 23s | 89% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.44 | 2m 45s | 91% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.41 | 2m 11s | 92% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.17 | 14m 25s | 98% |
| `agent-team:system-design-expert` | opus-5 | $1.42 | 3m 40s | 93% |
| `(parent)` | opus-5 | $1.22 | 37m 1s | 96% |
| `agent-team:product-requirements-expert` | opus-5 | $1.19 | 3m 42s | 90% |
| `agent-team:change-grader` | opus-5 | $0.93 | 2m 33s | 88% |
| `agent-team:system-design-expert` | opus-5 | $0.79 | 1m 45s | 91% |
| `agent-team:security-reviewer` | opus-5 | $0.63 | 1m 28s | 87% |
| `agent-team:feature-implementer` | opus-5 | $0.47 | 1m 17s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.44 | 2m 45s | 91% |
| `agent-team:test-reviewer` | sonnet-5 | $0.42 | 2m 21s | 90% |
| `agent-team:feature-implementer-routine` | opus-5 | $0.42 | 1m 35s | 89% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.41 | 2m 11s | 92% |
| `agent-team:test-reviewer` | sonnet-5 | $0.19 | 1m 1s | 87% |

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

- plugin `agent-team-spring-boot` at `v0.3.9` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `6cbb44ce4c9a` (branch `agent-team`)
- task fingerprint `8a2138a7610e1d3e` · `2.1.263 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
