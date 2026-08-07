# vets-specialty-filter r5 — v0.1.29

Filter the vet list by specialty (feature) · started 2026-08-07T01:04:13+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Feature request: filter the vet list by specialty. Two product decisions come
> with it, made here as the product owner:
> 
> - Non-goal NG-9 is narrowed: free-text veterinarian search stays out of
>   scope, but filtering the directory by an attribute it already shows is in.
>   Record the narrowing the way the project records non-goal changes.
> - The JSON endpoint at /vets is reinstated as a supported surface — this
>   filter is its first requested capability. Mint a fresh requirement for it;
>   the withdrawn REQ-VET-002 stays withdrawn and its id is not reused.
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

## Verdict

| check | result |
|---|---|
| oracle | ✔ 5/5 passed |
| suite (post-agent) | ✔ |
| suite (pristine baseline) | ✔ |
| checkpoints | 8/8 |
| review attention (pipeline grade) | concern |

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
| 4 (±0) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.77. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Repository-derived  findBySpecialtiesNameIgnoreCase  keeps matching in persistence, but  narrowingSpecialty  plus the null-branching in  findPaginated / findVets  adds a fresh rule to a controller the catalog says holds none, and it is unit-testable without the web layer. Tests are a clear upgrade: Mockito replaced by a hand-written  InMemoryVetRepository , BDD names, factories, named constants. Deductions:  ALL_VETS  is a shared mutable static fixture; index-based assertions ( RADIOLOGISTS.get(size-1) ,  $.vetList[3] ); a guard assertion mid-Act in  theVetDirectoryShouldPageOverTheNarrowedList ; bare  "cardiology" / "radio" ;  dentistry  means unheld in one file, held in the other; no JSON blank-value or empty-result case. Template repeats the narrowed/unnarrowed ternary five times. Docs are thorough and leave no visible stale claim.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Repository gains idiomatic derived finders ( findBySpecialtiesNameIgnoreCase , paged twin) and the controller reuses both existing routes, matching the catalog. But  narrowingSpecialty()  plus the null-branching in  findPaginated / findVets  puts a fresh rule in a controller — the checklist says the recorded deviation does not extend to new rules, and *Application service* was available without an ADR; it is also only reachable by booting MVC, widening the pyramid gap. The template repeats the same  ${narrowed} ? ... : ...  ternary five times. Tests are a real improvement: MockitoBean replaced by a hand-written  InMemoryVetRepository ,  the{Subject}Should{Outcome}  names,  createVet / createSpecialty  factories, real-DB query semantics; weakened by index-based  jsonPath("$.vetList[3].specialties[1].name") , raw HTML substring matching, and shared static  ALL_VETS . Documentation is complete: NG-9 narrowed, REQ-VET-003/004 minted, REQ-VET-002 withdrawal amended, contracts, threat-model row, and the retired known-defect all moved.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Matching lives in derived repository finders (findBySpecialtiesNameIgnoreCase), keeping the rule out of the controller; the controller only normalizes blank input and selects a query, a thin but real slice of logic added to a controller the catalog already flags. Tests are the strongest part: MockitoBean is replaced by a hand-written InMemoryVetRepository, names read as specifications (theVetDirectoryShouldPageOverTheNarrowedList), and construction sits behind createVet/createSpecialty. Deductions: shared static Vet fixtures are mutable entities, and index-based reads (RADIOLOGISTS.get(size-1), jsonPath $.vetList[3]) plus bare literals "cardiology"/"radio" violate the collection-assertion and no-mystery-value rules. vetList.html repeats a near-identical narrowed/unnarrowed ternary five times where Thymeleaf omits null parameters anyway. Documentation is complete: NG-9 narrowed, REQ-VET-003/004 minted, REQ-VET-002 kept withdrawn, contracts, threat model, defects and open questions all moved.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $10.89 | 31m | 24 | 91% | 11 file(s) +490/−68 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.23 | 4m 11s | 89% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-004 — Reader narrows the veterinarian directory to one specialty

1 review round · 1 build-pass · **1 build-failure** · grade **CONCERN**

| reviewer | R1 |
| --- | --- |
| **code-quality** | **✔** |
| **test** | **✔** (1) |
| **security** | **✔** |
| **doc** | **✔** |

- ◇ **prd-entry** Reader narrows the veterinarian directory to one specialty · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **new** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 12m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · (1 finding) · ***◷ 1m***
  - [clarify] `VetController.java:95` testing-principles.md § Test Pyramid directs a reviewer to ask, of each new rule added to a controller, whether it could be tested without booting the framework. narrowingSpecialty (strip + blank-means-absent) is exactly such a rule, added by this slice, and it is exercised only indirectly through MockMvc in theVetDirectoryShouldIgnoreABlankSpecialtyName - no unit test drives it directly. It mirrors the pre-existing, equally untested OwnerController normalization the design-block cites as precedent, so this is not a regression the slice introduced alone, but the brief's checklist item applies to it as written. Not blocking: the rule is a two-line normalization with no branching left uncovered (JaCoCo shows narrowingSpecialty at 100% instruction and branch coverage via the integration path), and extracting it to a directly-unit-testable form is a design change outside this reviewer's remit.
- ◆ **grade CONCERN** · narrow the vet directory by specialty
  - blast_radius — **clear** — Eleven files but only one feature package: two prod Java files plus the vet-list template, two test files, and six documentation files (three new ADRs, PRD, system-design, ADR index). No sensitive paths, no schema or seed-data change, no shared type touched. The 53 hunks are inflated by the five pagination-link rewrites in vetList.html, each the same mechanical change. The widest real reach is documentary rather than executable: the PRD narrows non-goal NG-9, reinstates the machine-readable list as REQ-VET-003, and retires a Known Defects row in system-design.
  - semantic_surprise — **clear** — I read every prod hunk for behavior the size would not predict and found none. Both handlers keep their existing signatures with an optional parameter, so unnarrowed callers hit the identical cached findAll paths; narrowingSpecialty strips and maps blank to null, and both call sites branch on that same null. The narrowed finders deliberately omit the cache annotation, which is the non-obvious decision here and it is the safe direction (reader input never becomes a key in an unbounded cache). The template ternary per link exists so an absent specialty omits the parameter rather than rendering it empty, and paging on the narrowed list would silently drop the filter without it. Derived-query risks I checked and cleared: the join on specialties yields at most one row per vet for a given name, so the Page count is a vet count, and the name-sorted specialty order is untouched. The value reaches the view only inside Thymeleaf URL builder syntax, so it is encoded and escaped, never echoed raw.
  - test_adequacy — **clear** — The tests would fail against a broken implementation rather than restate it. The query semantics the code cannot control - whole-name matching, case insensitivity expressed in the query rather than delegated to collation - are pinned in a new DataJpaTest against real seeded H2, including the prefix non-match and a real two-specialty vet. The controller tests drop the Mockito stub for a hand-written in-memory repository doing real subList paging arithmetic, so the six-radiologist page-2 assertion exercises genuine offsets, and the rendered-content assertions check the actual page-1 link carries the escaped specialty parameter while the unnarrowed page carries no specialty parameter at all. Expected values are derived from the fixture rather than hard-coded.
  - reviewer_hedging — **concern** — Three of the four dispatched reviewers approved with empty findings, but test-reviewer approved carrying one clarify finding addressed to system-design-expert: narrowingSpecialty is a new controller rule that testing-principles says should be answerable without booting the framework, and it is covered only indirectly through MockMvc. The reviewer marked it non-blocking and noted full branch coverage via the integration path, but the clarify was routed to another agent and no record answers it, so it merges as an open item rather than a settled one.
  - scope_deviation — **clear** — The diff matches the triaged surface exactly. Every file changed appears in the design-block primary or supporting paths, and the REQ-VET-003 work that widens this beyond a pure filter was named in the original prd-entry as a deliberate combined slice, not picked up mid-flight. Zero consultations. The one design revision was bookkeeping - a superseding design-block adding three documentation paths the first record failed to list - and the single gate failure was that same autofix-audit path-coverage miss, with no production code implicated.
  - why — The code reads clean on every axis I could test by reading: contained, no surprising behavior, and tests that pin the query semantics against a real database. The one thing to look at is the test-reviewer unanswered clarify on narrowingSpecialty - a design question about unit-testability, not a defect. Read it, decide, merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Injection into data access: the narrowing goes through Spring Data derived query methods (findBySpecialtiesNameIgnoreCase(String) and its Pageable overload) in VetRepository; the reader value is bound as a JPA parameter, no string-concatenated query text is introduced anywhere in the diff
- Cache-key reasoning in docs/adr/2026-08-07-reader-supplied-values-are-not-cache-keys.md holds in the code as written: a sweep of @Cacheable across src/main/java returns only the two pre-existing VetRepository.findAll declarations; neither narrowed finder carries the annotation, so the eviction-free, size-unlimited 'vets' cache (system/CacheConfiguration.java) keeps a fixed, enumerable key space and the reader-supplied specialty never mints an entry
- Cross-site scripting: the reader-supplied specialty reaches the page only inside th:href link expressions built with the Thymeleaf URL builder (@{/vets.html(page=...,specialty=${specialty})}), which URL-encodes the parameter value and then HTML-escapes the attribute; the value is rendered as text nowhere in vetList.html or any other template, and no th:utext, inlining, or escaping-disabling construct is added
- Boundary normalization is at the boundary and fail-safe: VetController.narrowingSpecialty maps null, empty, and all-whitespace to null, and the null branch selects the unnarrowed finder, so no degenerate value reaches persistence and the absent-parameter case is spelled by omitting the parameter rather than by an empty one
- Exposed surface is not widened: no new route is added; the change adds one optional query parameter to the two existing vet routes, both read-only GETs, and management-endpoint exposure is untouched
- No secrets: the diff introduces no credential-shaped value; the only new literals are the specialty names in the test fixtures and the seeded specialty names in VetRepositoryTests
- Mass assignment and identifier tampering are not in scope: the parameter binds to a String method argument, not to a command object, so no data binder or disallow list is involved
- No path composition, no deserialization entry point, and no new error message carrying the reader value outward
- Supply chain: build.gradle, settings.gradle, gradle.properties, and gradle/ are unchanged in the change set, so no new or upgraded dependency enters and the four dependency checks in system-design.md have nothing to clear
- docs/system-design.md threat model gains the 'Unbounded cache growth from request input' row naming the uncached narrowed reads as the mitigation, so the constraint is recorded where a future change would read it before adding @Cacheable

**code-quality-reviewer**

- VetRepository's two new finders follow the OwnerRepository derived-finder precedent, and the uncached-for-a-stated-reason javadoc on each (with @link to avoid repeating the rationale) makes the cache-key risk visible to the next reader without re-deriving it from the ADR
- VetController.narrowingSpecialty centralizes null/blank normalization in one small, well-documented private helper reused by both handlers, keeping the request-adaptation logic out of the business path
- vetList.html pagination links use Thymeleaf's URL builder (not string concatenation) so the narrowing value is encoded and preserved across pages, matching the risk the design-block flagged
- Javadoc, package structure, and naming all match existing conventions in the vet package; no prohibited suffixes or business logic introduced into the controller
- ./gradlew checkFormat passes clean

**doc-reviewer**

- prd.md stays behaviorally scoped: REQ-VET-003/004 Done-when bullets and edge cases carry no mechanism, no rationale prose, and correct anchors; REQ-VET-002 stays withdrawn with a dated amendment pointing at REQ-VET-003
- All three new ADRs follow the template (Context/Options/Decision/Consequences/Implementation/References), stay under the 60-line guideline, and correctly place the external contract (parameter name, matching rule) and the cache-key decision in ADRs rather than the PRD
- docs/adr/README.md index gains all three rows with titles matching the ADR headings; non-goal ADR filename and Non-goal: NG-9 Implementation line follow the documented convention
- system-design.md Contracts table rewired for Vets/VetRepository/VetController against REQ-VET-003/004 resolves the prior em-dash-preamble inconsistency (Vets no longer carries an unclaimed '—'); the stale 'pending removal' Known Defects row is retired with a note rather than silently dropped
- New system-design.md prose (external-contract paragraph, vendor-independent case-insensitive matching, Threat Model row, Open Question 5 narrowing) matches the shipped VetController/VetRepository/vetList.html code and carries no field/parameter tables or literal constants
- All cross-references resolve: system-design.md#contracts, #known-defects, #threat-model, #persistence, #open-questions-from-the-survey and the adr/2026-08-07-*.md links all hit real anchors/files; no imperative system-design.md line lacks an ADR back-link

**test-reviewer**

- Mocking policy followed precisely: VetControllerTests replaces the prior MockitoBean stub with a hand-written InMemoryVetRepository record wired via @TestConfiguration - the brief's 'hand-write mocks' preference over a mock framework, and it exercises real paging arithmetic (Math.min/subList) rather than stubbed page objects
- VetRepositoryTests is a real @DataJpaTest against seeded H2, and explicitly targets the vendor-independent case-insensitive query the design-block's risk log calls out (IgnoreCase expressed in the query, not delegated to collation) - correctly split from the controller tests per the module's own doc comment
- All nine PRD test names are present, matched at the layer that owns the behavior: the seven controller-level names in VetControllerTests, and the case-insensitive-match / no-prefix-match names in VetRepositoryTests where the query semantics actually live; two names appear at both layers by design (paging, empty-result)
- All four PRD edge cases covered: stable specialty order (RAFAEL_HOLDING_BOTH specialties[0]/[1] assertion), blank-name-as-absent, prefix non-match, and multi-specialty vets listed under each specialty they hold (theVetDirectoryShouldListAVetUnderEachSpecialtyItHolds uses real seeded data - Linda Douglas holding surgery and dentistry - not invented fixtures)
- Pagination-link encoding verified end to end: theVetDirectoryShouldPageOverTheNarrowedList asserts the rendered page-2 link carries '&amp;specialty=radiology' (Thymeleaf URL builder, addressing the design-block's injection/encoding risk), and theVetDirectoryShouldListEveryVetWhenNoSpecialtyIsNamed asserts the parameter is omitted entirely when absent
- Three-tier data naming and factory-method construction followed throughout (createVet/createSpecialty factories, named RADIOLOGY/SURGERY/UNHELD_SPECIALTY/DENTISTRY constants, zero mystery literals); expected values (RADIOLOGISTS list, totalItems counts) derived from ALL_VETS rather than hard-coded
- BDD test naming (the{Subject}Should{Outcome}) applied consistently across both new/modified files
- ./gradlew test and ./gradlew check pass; JaCoCo reports 100% instruction/branch coverage for VetController and the vet package, well above the brief's 80% target

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-5 | $5.80 | 14m 46s | 96% |
| `spring-boot-claude:system-design-expert` | 2 | opus-5 | $4.09 | 6m 56s | 89% |
| `(parent)` | 1 | opus-5 | $2.59 | 34m 51s | 94% |
| `spring-boot-claude:change-grader` | 1 | opus-5 | $2.23 | 4m 11s | 89% |
| `spring-boot-claude:product-requirements-expert` | 1 | opus-5 | $1.92 | 3m 47s | 88% |
| `spring-boot-claude:doc-reviewer` | 1 | sonnet-5 | $1.14 | 1m 47s | 91% |
| `spring-boot-claude:security-reviewer` | 1 | opus-5 | $1.14 | 1m 10s | 80% |
| `spring-boot-claude:test-reviewer` | 1 | sonnet-5 | $0.84 | 2m 3s | 85% |
| `spring-boot-claude:code-quality-reviewer` | 1 | sonnet-5 | $0.67 | 1m 40s | 88% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-5 | $0.07 | 6s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-5 | $4.78 | 13m 2s | 97% |
| `spring-boot-claude:system-design-expert` | opus-5 | $2.66 | 5m 2s | 91% |
| `(parent)` | opus-5 | $2.59 | 34m 51s | 94% |
| `spring-boot-claude:change-grader` | opus-5 | $2.23 | 4m 11s | 89% |
| `spring-boot-claude:product-requirements-expert` | opus-5 | $1.92 | 3m 47s | 88% |
| `spring-boot-claude:system-design-expert` | opus-5 | $1.43 | 1m 53s | 83% |
| `spring-boot-claude:doc-reviewer` | sonnet-5 | $1.14 | 1m 47s | 91% |
| `spring-boot-claude:security-reviewer` | opus-5 | $1.14 | 1m 10s | 80% |
| `spring-boot-claude:feature-implementer` | opus-5 | $1.02 | 1m 43s | 89% |
| `spring-boot-claude:test-reviewer` | sonnet-5 | $0.84 | 2m 3s | 85% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-5 | $0.67 | 1m 40s | 88% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-5 | $0.07 | 6s | 50% |

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
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `610c2c59194e4044` · `2.1.222 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
