# vets-specialty-filter r1 — v0.3.10

Filter the vet list by specialty (feature) · started 2026-09-08T19:00:53+00:00 · exec `claude-dev` · status **complete**

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
| 5 (±1) | 4 (±0) | 4 (±1) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.67. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 5 · doc-fit 5

> The change stays in the layers the design assigns: binding and normalization in  VetController.normalizeSpecialty , matching pushed into two derived  VetRepository.findDistinctBySpecialtiesNameIgnoreCase  finders, no new type or business rule in the controller, and the cache omission is justified by an ADR that the  VetRepository  contracts row now cites. Template links move to the parameterized  @{/vets.html(page=..., specialty=...)}  form, closing an expression-preprocessing hole, and a test pins the encoding. Docs move together: NG-9 narrowed, REQ-VET-003 minted with done-when rows, REQ-VET-002 left withdrawn, the defect row retired, open questions recorded. Tests are behavior-named with tiered constants, but  helen() / james()  still call production setters, new Mockito stubbing widens, and  SECOND_PAGE_LINK  asserts on raw rendered HTML.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in the right layers: derived queries on  VetRepository  ( findDistinctBySpecialtiesNameIgnoreCase ), request normalization in  VetController.normalizeSpecialty , and pagination links moved to the parameterized  @{/vets.html(page=..., specialty=...)}  form, which the encoding test guards. No new type, no rule pushed into the controller beyond binding/normalization. Tests are BDD-named, blank-line phased, and use named tiers ( AN_OPENING_OF_RADIOLOGY ,  A_SPECIALTY_NO_VET_HOLDS ); deductions for duplicating the retained  showResourcesVetList  with  theVetResourceShouldCarryEachVetWithTheirSpecialties , and for  assertThat(firstPage.getTotalPages()).isEqualTo(RADIOLOGISTS.size())  deriving pages from a coincidence. The two mirrored ternaries in  findPaginated / findVets  and the literal  SECOND_PAGE_LINK  markup are minor roughness. Docs are complete: NG-9 narrowed, REQ-VET-003 minted, REQ-VET-002 kept withdrawn, defect row retired, contracts table and two ADRs updated.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The change stays in the existing seams: derived query methods on  VetRepository  ( findDistinctBySpecialtiesNameIgnoreCase ), controller-level binding/normalization, and pagination links rewritten to the parameterized  @{/vets.html(page=..., specialty=${specialty})}  form with a comment explaining the encoding rationale; the deliberate omission of  @Cacheable  is justified in code and an ADR. The empty-vs-filter ternary is duplicated across  findPaginated  and  findVets , and  normalizeSpecialty 's javadoc partly restates  strip() . Tests are behavior-named and phase-separated, but lean on Mockito stubs and shared  @BeforeEach  fixtures, assert on a raw HTML link literal ( SECOND_PAGE_LINK ), and  theVetSearchShouldCountItsPagesOverTheNarrowedListAlone  derives  getTotalPages()  from  RADIOLOGISTS.size()  only because page size is 1. Documentation is thorough: NG-9 narrowed, REQ-VET-003 minted, superseded entry, defect row retired, contracts table and ADR index updated, open questions recorded.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.55 | 52m | 41 | 94% | 10 file(s) +373/−29 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.86 | 2m 44s | 83% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Reader can narrow the veterinarian directory to one specialty on either form

2 review rounds · 2 build-passes · **1 build-failure** · grade **SCRUTINIZE**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- • intake-decision (human)
- ◇ **prd-entry** Reader can narrow the veterinarian directory to one specialty on either form · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 15m***
  - ▲ **build ✗ test failed** · retry 1
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- • review-plan (review-planner)
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply-chain check not run and therefore not clean: the project configures no OWASP Dependency-Check plugin (no dependencyCheck in build.gradle), and this reviewer has no network access, so nothing in this slice was matched against the NVD. Declared versions read from build.gradle: Spring Boot 4.1.1, dependency-management 1.1.7, GraalVM buildtools 1.1.2, CycloneDX 3.4.1. Jackson and Thymeleaf resolve transitively through the Boot BOM. The dependency set is unchanged by this slice, so this is a standing CI/human item rather than a property of the change.
  - ▹ rec: Name shadowing with a latent security edge in src/main/resources/templates/vets/vetList.html: the table body binds a loop variable also called specialty (th:each="specialty : ${vet.specialties}"), which shadows the model attribute of the same name inside that span. Today the five pagination links sit outside that scope, so they resolve the model attribute as intended and the rendered output is correct. The hazard is for the next editor: a link added inside the table that writes specialty=${specialty} would silently bind the Specialty entity instead of the filter value. Renaming the loop variable (for example to held) would remove the ambiguity. Not a defect in this change; raised so the code-quality reviewer and a future editor see it.
  - ▹ rec: The specialty parameter carries no explicit maximum length. Reach is limited: the value is matched by equality in a bound parameter, the servlet container already caps request-line and header size, and the neighbouring owner last-name search accepts unbounded text the same way, so this change is consistent with the codebase's existing boundary handling rather than weaker than it. Noted only as the one input-validation dimension the change leaves open.
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [autofix] `VetControllerTests.java` Done-when bullet 'given a specialty no veterinarian holds, when either form is requested, then the listing comes back with no veterinarian in it' has no controller-level test. ClinicServiceTests covers the repository query returning empty, but the controller's own pass-through of a zero-match result (rendered HTML model attributes and the JSON `/vets` body) is never exercised — coverage-map lists this Done-when bullet as unmet. Add a controller test (e.g. mock `findDistinctBySpecialtiesNameIgnoreCase` to return an empty page/collection for an unmatched specialty) asserting `listVets` is empty for `/vets.html` and `$.vetList` is empty for `/vets`.
    - fix: Add theVetListShouldComeBackEmptyWhenNoVetHoldsTheSpecialty (mocking an empty PageImpl) and theVetResourceShouldComeBackEmptyWhenNoVetHoldsTheSpecialty (mocking an empty collection) to VetControllerTests.java, following the existing RADIOLOGY-matched tests' pattern.
- ↻ **implement** (implementer · routine) ← test · (1 finding) · ***◷ 2m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved**
- ◆ **grade SCRUTINIZE** · narrow both vet-directory surfaces by an optional specialty parameter
  - blast_radius — **skim** — Ten files but one module: the whole code delta sits in the vet package (VetController, VetRepository, vetList.html) with no sensitive path, no config, no build or dependency change, and nothing touched in owner, pet, or visit code. The five doc files carry real reach — the PRD narrows non-goal NG-9 and reinstates the machine-readable listing as a supported surface — but each edit transcribes the owner's recorded intake decision rather than a scope claim the slice invented.
  - semantic_surprise — **skim** — Read every hunk: normalizeSpecialty only strips, the repository does the case folding through IgnoreCase, and both dispatches branch on isEmpty() so a blank value takes the identical unfiltered path as before — no boundary flipped, no operator inverted. One ripple the requirement does not mention and no test pins: the pagination links moved to the parameterized link form, so an unfiltered page now renders a trailing empty specialty= in all five links where it previously rendered none. Cosmetic only, since the controller reads an empty value as absent, and the same rewrite is what takes the reader-supplied value out of Thymeleaf's expression-preprocessing form.
  - test_adequacy — **skim** — The tests are real rather than tautological and split at the right seam: query semantics (whole-name case-insensitive match, a prefix matching nothing, an empty result, page count over the narrowed list, page two staying narrowed) run against a real VetRepository on H2 in ClinicServiceTests, while blank-value normalization, link carry-over, and encoding of a specialty carrying URL syntax run through MockMvc. Each would fail against a broken implementation. One blemish to see: VetControllerTests names a constant A_SPECIALTY_NO_VET_HOLDS with the value dentistry, but the H2 seed gives dentistry to Douglas — the test still holds because the repository is stubbed there, yet the name encodes a false premise about the fixture.
  - reviewer_hedging — **scrutinize** — All four planned reviewers approved, but two approvals carry residue. The security reviewer approved with three recommendations, one of them a latent trap in a file this change edits: vetList.html binds a loop variable also named specialty over vet.specialties in the table body, so a page link ever added inside that scope would silently bind the Specialty entity instead of the filter value — correct today only because the five links sit outside the loop. Its other two notes are that no supply-chain scan was run and that the parameter carries no maximum length. Separately, the test-reviewer's round-two approval justifies the fix by stating that dentistry is a specialty no vet holds in the seed data, which the seed contradicts.
  - scope_deviation — **skim** — Zero design revisions, zero consultations, one build retry, and every changed path was named in advance by the design-block's primary or supporting paths. The change stops where the intake pinned it: a URL contract with no form or dropdown, the machine-readable listing left unpaged, and the three genuinely open choices recorded as PRD open questions rather than decided in code.
  - why — Two approvals carry residue worth a human's eyes before merge: the security reviewer's template-shadowing hazard on the specialty name inside vetList.html, and the test-reviewer's round-two justification that dentistry is held by no vet, which the H2 seed contradicts. Read those two spots; the code itself is clean and well tested.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**doc-reviewer**

- docs/prd.md REQ-VET-003 entry stays behaviorally worded throughout — no query-parameter, endpoint, route, or other mechanism language leaked into the requirement, Done-when bullets, or edge cases (boundary-rules.md litmus test)
- NG-9 narrowing in docs/prd.md is a one-line scope edit with the rationale properly deferred to docs/adr/2026-09-08-non-goal-veterinarian-search.md via an ADR link, not inlined as rationale prose
- Both new ADRs (non-goal-veterinarian-search.md, uncached-specialty-filtered-vet-reads.md) carry Context/Options Considered/Decision/Consequences/Implementation sections, em-dash reference lists, and Implementation sections with Non-goal: / Requirements: fields per the required ADR shape
- docs/adr/README.md index gained both new ADR rows with correct dates and status
- docs/system-design.md Contracts rows for Vet, Specialty, Vets, VetRepository, VetController all carry REQ-VET-003 alongside REQ-VET-001 where applicable, and the VetRepository row's cache-behavior note back-links the new ADR
- Known Defects table correctly drops the retired 'machine-readable route serves no requirement' row and replaces it with a sentence back-linking the non-goal ADR, matching the design-block's retraction instruction
- REQ-VET-002 Superseded entry and the matching Open Questions answer are both updated in place (append-style, not rewritten history) to record that the surface returned under REQ-VET-003 while the withdrawn id stays withdrawn and unreused
- New req-vet-003 HTML anchor is present and every internal cross-reference (prd.md#req-vet-003, prd.md#non-goals, system-design.md#contracts, system-design.md#open-questions-from-the-survey, system-design.md#security-context) resolves to a real heading/anchor
- VetRepository.java and VetController.java source match the system-design.md and ADR claims exactly: two uncached findDistinctBySpecialtiesNameIgnoreCase overloads with a WHY comment citing the ADR, and normalizeSpecialty/findPaginated/findVets dispatch matching the documented behavior
- 'Specialty' and 'Veterinarian' usage in the new PRD/system-design text matches docs/ubiquitous-language.md's canonical definitions

**code-quality-reviewer**

- VetController.normalizeSpecialty mirrors the recorded OwnerController:98-105 blank-as-absent precedent instead of inventing a second convention
- The two derived-query overloads sit on VetRepository per the Contracts catalog row, and the WHY comment above them (caller-supplied cache key, unbounded vets cache) cites the governing ADR rather than restating it
- vetList.html's pagination links move to the parameterized @{...} form with an inline comment explaining the injection rationale, not just the change
- New comments and javadoc all explain WHY and pass the conventions-map sweep with no flagged instances
- No new business rule lands outside the layer the Contracts table assigns it; the controller's filtered/unfiltered dispatch mirrors the sanctioned owner-search pattern
- New domain-facing names (specialty, findDistinctBySpecialtiesNameIgnoreCase) match docs/ubiquitous-language.md with no coined synonyms
- checkFormat passes clean

**security-reviewer**

- Injection into data access: the specialty reaches persistence only as a bound parameter of the Spring Data derived query VetRepository.findDistinctBySpecialtiesNameIgnoreCase (Collection and Page forms). No string-concatenated query text, no @Query, no JPQL fragment built from request-derived text. Grep over src/main/java for concatenation into query text and for Runtime/ProcessBuilder/exec returns nothing new.
- Cross-site scripting: the request-derived value is rendered nowhere as text. Its only appearance in vets/vetList.html is as a query-parameter value inside five th:href link expressions of the form @{/vets.html(page=..., specialty=${specialty})}, which URL-encodes the value and then HTML-escapes the attribute. Grep for th:utext, th:inline, and javascript: across src/main/resources/templates returns nothing.
- Template-expression injection improved over baseline: all five pagination links moved off the @{'...__${x}__'} preprocessing form. Preprocessing evaluates its content as expression source, so carrying a reader-supplied specialty through it would have been an SpEL-evaluation surface; the parameterized form has no such property. This is a net reduction of the change's own surface, not merely a neutral rewrite.
- Cache poisoning / unbounded cache growth avoided by construction: neither filtered read carries @Cacheable, and the reason (a cache key derived from caller-supplied text against a 'vets' cache with no size limit or expiry) is recorded both inline in VetRepository and in docs/adr/2026-09-08-uncached-specialty-filtered-vet-reads.md. Adding @Cacheable there would have been a reachable memory-exhaustion vector for any anonymous caller.
- Mass assignment: no new request-bound type or WebDataBinder. Both handlers take a scalar @RequestParam String, so the identifier-binding disallow rule in docs/security-principles.md is not engaged.
- Concurrency: VetController stays a stateless singleton. normalizeSpecialty is static and pure; no mutable field, collection, or non-thread-safe formatter is introduced.
- Null and error handling: @RequestParam(defaultValue = "") makes the parameter non-null before strip(), so no unchecked dereference. No new exception message, log line, or rendered value carries request-derived or internal detail, so the error-disclosure row of the threat model is untouched.
- No new endpoint, no broadened actuator exposure, no credential, secret, file, path, shell, XML, or deserialization surface introduced. Grep for hardcoded-secret names over the diff returns only the test constants RADIOLOGY/RADIOLOGISTS naming domain data.
- Supply chain: scripts/changeset.sh --name-only shows no build.gradle or lockfile change, so the resolved dependency set is unchanged by this slice and no new artifact needed the four checks in system-design.md.

**test-reviewer**

- Repository-level rules (case-insensitive whole-name match, no-partial-match, empty-result, narrowed page count over the filtered set alone, unpaged full-holder listing) are correctly unit-tested at the VetRepository seam in ClinicServiceTests against a real DB, not duplicated through the mocked controller — correct pyramid placement per system-design.md's assignment of query semantics to the repository.
- Controller-level rules (blank/whitespace specialty treated as no filter, specialty carried across pagination links, URL-unsafe specialty characters encoded rather than injected raw into the link) are correctly tested at the web layer via MockMvc with VetRepository mocked, matching CLAUDE.md's sanctioned MockMvc boundary-mock policy.
- theVetListShouldEncodeTheSpecialtyItPutsIntoPageLinks is a genuine boundary/security test: it proves a specialty value carrying '&page=9' cannot smuggle extra query parameters into the rendered pagination link.
- Test data follows the three-tier naming convention throughout (RADIOLOGY, RADIOLOGIST, A_SPECIALTY_NO_VET_HOLDS, etc.) with derived expectations (RADIOLOGISTS.size()) rather than magic numbers.
- @ParameterizedTest with @ValueSource covers the blank/whitespace-variants case without copy-paste duplication in both VetControllerTests methods.
- ./gradlew test passes for both changed test classes.

**test-reviewer**

- The round-1 autofix (missing controller-level coverage for the zero-match specialty case) is fully resolved: theVetListShouldComeBackEmptyWhenNoVetHoldsTheSpecialty and theVetResourceShouldComeBackEmptyWhenNoVetHoldsTheSpecialty exercise the empty-result pass-through on both /vets.html (model attribute listVets) and /vets (jsonPath $.vetList), matching the finding's prescribed fix.
- A_SPECIALTY_NO_VET_HOLDS ("dentistry") is verified against the seed data (src/main/resources/db/h2/data.sql) as a real specialty held by no vet in the fixture, not an invented value — Tier 1 naming with a value that actually exercises the described condition.
- New tests follow the host file's existing conventions exactly: given(...)/mockMvc.perform(...).andExpect(...) shape, blank-line separation matching sibling tests, hamcrest empty() matcher consistent with the file's existing hamcrest/jsonPath idiom rather than introducing a new assertion style.
- coverage-map --feature REQ-VET-003 now reports 7 of 7 Done-when bullets covered (previously 6 of 7, missing exactly this case).
- No new raw literal or unnamed-constant issue in the fix delta (conventions-map sweep clean).
- ./gradlew test passes for VetControllerTests and ClinicServiceTests with no regressions; the round-1 approved placement of the repository-seam tests in ClinicServiceTests is untouched by this fix and remains correct.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $5.24 | 18m 38s | 97% |
| `(parent)` | 1 | opus-5 | $1.60 | 54m 25s | 97% |
| `agent-team:system-design-expert` | 1 | opus-5 | $1.37 | 3m 54s | 92% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.23 | 3m 54s | 92% |
| `agent-team:change-grader` | 1 | opus-5 | $0.86 | 2m 44s | 83% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.66 | 1m 40s | 87% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.62 | 3m 10s | 87% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.37 | 1m 35s | 90% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.30 | 1m 18s | 90% |
| `agent-team:review-planner` | 1 | sonnet-5 | $0.16 | 24s | 83% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.37 | 15m 41s | 97% |
| `(parent)` | opus-5 | $1.60 | 54m 25s | 97% |
| `agent-team:system-design-expert` | opus-5 | $1.37 | 3m 54s | 92% |
| `agent-team:product-requirements-expert` | opus-5 | $1.23 | 3m 54s | 92% |
| `agent-team:feature-implementer-routine` | opus-5 | $0.87 | 2m 57s | 94% |
| `agent-team:change-grader` | opus-5 | $0.86 | 2m 44s | 83% |
| `agent-team:security-reviewer` | opus-5 | $0.66 | 1m 40s | 87% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.37 | 1m 35s | 90% |
| `agent-team:test-reviewer` | sonnet-5 | $0.37 | 2m 5s | 87% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.30 | 1m 18s | 90% |
| `agent-team:test-reviewer` | sonnet-5 | $0.25 | 1m 4s | 86% |
| `agent-team:review-planner` | sonnet-5 | $0.16 | 24s | 83% |

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

- plugin `agent-team-spring-boot` at `v0.3.10` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `6cbb44ce4c9a` (branch `agent-team`)
- task fingerprint `8a2138a7610e1d3e` · `2.1.263 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
