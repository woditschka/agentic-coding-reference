# vets-specialty-filter r3 — v0.2.4

Filter the vet list by specialty (feature) · started 2026-08-30T19:01:23+00:00 · exec `claude-dev` · status **complete**

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
| review attention (pipeline grade) | — |

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

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.69. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in the repository as derived queries (VetRepository findDistinctBySpecialties_NameIgnoreCase), the controller only binds and delegates, and the template switches to parameterized link expressions, closing the pre-existing string-preprocessing hole; blank-to-null normalization is a small rule added in the controller, and the null-branch appears twice (findPaginated, findVets), with five near-identical ternaries in vetList.html. Tests are behavior-named, phase-separated, use factories (firstOfTwoPages, james/helen) and parameterized blank cases, but reach for new Mockito stubs, repeat the bare literal "radiology" and seed names "Leary"/"Stevens" as unnamed values, and CONTROLLER_PAGE_SIZE mirrors the hardcoded 5 in findPaginated. Docs are thorough: NG-9 narrowed, REQ-VET-003/004 minted, defect row retired, cache ADR, contracts table and open questions all updated.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The change fits the existing shape: derived query methods on VetRepository, a thin controller branch, no new types or prohibited suffixes; only the blank-normalization rule and the duplicated null-branch in findPaginated/findVets add mild controller weight the catalog places lower. Tests are behavior-named (theVetListPagingLinksShouldCarryTheNamedSpecialty), four-phase, comment-free, and cover blanks, case, prefix, empty result, paging, and the no-control decision; but Tier-3 literals persist ("radiology", containsExactlyInAnyOrder("Leary", "Stevens"), totalElements 2), and new stubs still use the mock framework. The template repeats the same specialty ternary five times, and CONTROLLER_PAGE_SIZE mirrors the controller's magic 5. Documentation is thorough: NG-9 narrowed, REQ-VET-003/004 minted, defect row retired, cache question amended, two ADRs indexed.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in derived repository queries ( findDistinctBySpecialties_NameIgnoreCase ) rather than in the controller, matching the Repository/Web controller rows, and the uncached choice is argued in an ADR. Against it:  namedSpecialtyOrNull  puts a blank/trim rule inside the controller where only MockMvc can exercise it, widening the pyramid gap, and the null-branch is duplicated in  findPaginated  and  findVets ; the template repeats the same  ${specialty == null} ? ... : ...  ternary five times. Tests are BDD-named, phase-structured, use collection assertions and a  firstOfTwoPages  factory, and cover blank, no-match, paging, encoding, and no-control cases; bare  "radiology"  literals recur unnamed and javadoc on  CONTROLLER_PAGE_SIZE  restates code. Docs move everywhere the change touches: NG-9 narrowed, REQ-VET-003/004 minted, defect row retired, contracts and open questions updated.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $13.02 | 39m | 7 | 94% | 11 file(s) +423/−33 |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-004 — Reader narrows the veterinarian directory to one specialty

2 review rounds · 2 build-passes · **1 build-failure** · no grade yet

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (2) | ✎ (1) |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- ◇ **prd-entry** Reader narrows the veterinarian directory to one specialty · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 12m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 38s***
- ✔ **review security** · **approved** · ***◷ 51s***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `PetClinicIntegrationTests.java:67` Six newly written tests do not follow the BDD naming school (`docs/testing-principles.md` § Test Naming: `the{Subject}Should{Outcome}`), which governs tests written or modified from 2026-07-31 onward regardless of the host file's pre-existing convention. `shouldFindVetsHoldingASpecialty`, `shouldFindVetsBySpecialtyRegardlessOfLetterCase`, `shouldNotFindVetsByPartOfASpecialtyName`, `shouldFindNoVetsForAnUnheldSpecialty`, and `shouldPageOverTheVetsHoldingASpecialtyAlone` in ClinicServiceTests, plus `vetListNarrowedToOneSpecialty` in PetClinicIntegrationTests, all mirror the host file's pre-2026-07-31 method-name style instead. The new tests in VetControllerTests in the same change set (e.g. `theVetListShouldShowOnlyVeterinariansHoldingTheNamedSpecialty`) correctly follow the school, showing the omission is inconsistent within the same slice.
    - fix: Rename the six methods to `the{Subject}Should{Outcome}` form, e.g. `theRadiologySearchShouldMatchRegardlessOfLetterCase`, `theVetListNarrowedBySpecialtyShouldMatchRegardlessOfLetterCase` for the integration test.
  - [autofix] `vetList.html` prd.md's REQ-VET-004 Done-when bullet "given either form of the directory, when it is presented, then it carries no control for choosing a specialty" (also acceptance criterion 11 in the prd-entry) has no dedicated test. Nothing in the diff asserts that vetList.html renders no form/input/select for specialty, on either the filtered or unfiltered page.
    - fix: Add a test (e.g. `theVetListShouldRenderNoControlForChoosingASpecialty`) that asserts the rendered HTML contains no `\<form`, `\<input`, or `\<select` tied to a specialty parameter, run against both a filtered and an unfiltered request.
- ↻ **implement** (implementer) ← test · (2 findings) · ***◷ 4m***
  - ▲ **build ✓ clean** · build · test · checkFormat · checkstyleMain · handoff-validate · autofix-audit
- • review-plan (review-plan-engine)
- ↻ **fix test** ← test · (2 findings)
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [autofix] `VetControllerTests.java:78-100` Finding 1 (BDD naming) is fully resolved: all six renamed methods (theSpecialtySearchShouldFindEveryVeterinarianHoldingIt, theSpecialtySearchShouldMatchRegardlessOfLetterCase, theSpecialtySearchShouldNotMatchPartOfAStoredName, theSpecialtySearchShouldFindNoVeterinarianForAnUnheldSpecialty, theSpecialtySearchShouldPageOverTheMatchingVeterinariansAlone, theVetListNarrowedBySpecialtyShouldShowOnlyTheHoldersRegardlessOfLetterCase) now follow the the{Subject}Should{Outcome} school and are consistent with the rest of the slice. Finding 2's new test theVetListShouldRenderNoControlForChoosingASpecialty is real, non-vacuous (verified by re-running the injected-form check myself: current vetList.html has zero \<form>/\<input>/\<select> tags, confirming clean restoration), and does close most of the gap. However PAGE_WITH_A_SPECIALTY_CONTROL = "(?is).*\<(?:form|input|select)\\b[^>]*specialty.*" requires the literal substring "specialty" inside the control tag's own opening-tag attributes ([^>]* cannot cross a >). A control that lets a caller choose a specialty but names its parameter/id something else -- e.g. \<select name="filter">\<option value="radiology">Radiology\</option>...\</select>, or a \<label>Specialty\</label>\<select id="s"> pairing -- is exactly the control shape acceptance criterion 11 forbids, yet it renders undetected because the word "specialty" never appears inside the select tag itself. The test proves 'no control literally labeled specialty' rather than the criterion's 'no control for choosing a specialty'.
    - fix: Broaden the assertion beyond a literal attribute-name match, e.g. also assert the rendered page contains no \<select>/\<input> whose enclosed \<option> values or list of values equal the known specialty names from the fixture data (radiology, surgery, dentistry), or match on the surrounding \<label>/nearby text as well as the tag attributes -- so a differently-named specialty-choosing control still fails the test.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- namedSpecialtyOrNull helper cleanly isolates blank/absent normalization and is reused across both routes
- VetRepository javadoc explains the case-insensitive, full-match semantics and cross-references the uncached-reads ADR at the point where a reader needs it
- No new types introduced; naming matches existing VetController/VetRepository conventions and architecture-principles.md's naming table
- checkFormat passes; no System.out, blanket catches, or magic-string duplication of the specialty parameter name introduced
- Template's per-link ternary duplication and the controller's inline strip() normalization match the recorded design decisions rather than being unexplained repetition

**security-reviewer**

- Injection into data access: VetRepository adds only derived finders (findDistinctBySpecialties_NameIgnoreCase, with and without Pageable). No @Query, no EntityManager.createQuery, no string-concatenated JPQL/SQL anywhere in the diff; the caller-supplied specialty reaches the database as a bound parameter. IgnoreCase is realized by the derived-query mechanism, not by concatenated SQL functions.
- Reflected XSS / parameter smuggling in paging links: all five link families in vets/vetList.html (numbered sequence, first, previous, next, last) use the parameterized link expression @{/vets.html(page=...,specialty=${specialty})} with a null branch that omits the parameter. None uses the pre-existing string-preprocessing form @{'/vets.html?page=__${i}__'}, which does not URL-encode. Grep across src/main/resources/templates confirms no remaining __${...}__ preprocessing and no th:utext; Thymeleaf's default attribute escaping stays on. The regression test asserts specialty=radiology&page=99 renders as specialty=radiology%26page%3D99 and never as the unencoded form, so neither parameter smuggling nor markup breakout of the href is reachable.
- Cache as a resource boundary: @Cacheable("vets") appears only on the two unfiltered findAll overloads; both specialty-filtered finders carry @Transactional(readOnly = true) alone. Annotation placement matches the intent recorded in docs/adr/2026-08-30-uncached-specialty-filtered-vet-reads.md - no caller-supplied text becomes a key in an unevicted cache. The uncached filtered path is a read-only, parameterized, page-limited query (page size 5) against an indexed join, so it opens no new resource boundary beyond the already-open unauthenticated read surface described in system-design.md Security Context.
- Mass assignment: VetController binds only simple request parameters (int page, String specialty) and no complex command object, so the security-principles.md rule that every request-bound *type* disallow identifier binding is not engaged. Omitting @InitBinder is correct here - adding an empty or partial binder would have been the weaker choice, since the project's disallow list ("id", "*.id") has nothing to apply to. Blank normalization via strip() in namedSpecialtyOrNull is a pure value normalization on the way in, not a security control being substituted for one.
- Failure and disclosure behavior: a no-match specialty flows through the derived finder to an empty Page, rendering HTTP 200 with an empty table - no exception, no error page, and nothing distinguishing 'unknown specialty' from 'specialty with no vets', so the endpoint leaks no information about which specialty names exist. The specialty value never reaches an exception message, a log line, or the error page. Unbounded specialty length is bounded in practice by the container's request-line limit and is carried only as a bound query parameter and a URL-encoded link parameter; it composes no filesystem path, no resource lookup, and no deserialization input.
- Exposed surface and supply chain: no new endpoint is added - both /vets.html and /vets gain an optional parameter on an already-public read route, and the JSON endpoint returns the same Vets projection as before, so no new field is exposed. build.gradle and gradle/ are untouched, so no dependency is added, removed, or repinned and the resolved dependency set is unchanged from the last verified state; the plain-HTTP repository check and TLS resolution are unaffected. Secret sweep over the added lines (password, secret, token, key, credential, and the specialty/filter vocabulary this change introduces) found no hardcoded value.

**doc-reviewer**

- Superseded section states REQ-VET-002 stays withdrawn, its ID is never reused, and REQ-VET-003 supersedes nothing — coherent in both the Superseded list entry and the matching Open Questions answer
- PRD carries no route or URL text; the concrete address contract (/vets.html, /vets, the specialty query parameter) lives only in system-design.md Contracts, holding the PRD/system-design boundary in both directions
- Cross-document coherence verified: the two new ADRs, the PRD's REQ-VET-003/004 prose and Done-when bullets, the system-design Contracts subsection and Implements-cell updates, and the actual VetController/VetRepository/vetList.html behavior all agree, including case-insensitive whole-name matching, blank-as-absent, stripped surrounding spaces, uncached filtered reads, and paging links carrying the specialty forward
- Retired Known Defects row and the Vets Implements-cell change verified against the surrounding text: the 'three kinds of em-dash Implements value' paragraph never enumerated Vets among those three kinds, so redirecting its cell to REQ-VET-003 does not contradict that paragraph; the remaining Known Defects row order and the 'final row is derived from code' claim still point at the correct (unmoved) last row
- All new prose sentences fall under the 30-word standard; anchors for req-vet-003/004, prd.md#non-goals, system-design.md#contracts/#known-defects/#open-questions-from-the-survey, and security-principles.md#realization all resolve
- NG-9 narrowing is stated consistently across the ADR, the Non-Goals table row, and the framing paragraph naming NG-4, NG-5, and NG-9 as decided rows; the ADR's quoted owner decision matches the prd-entry record's scope_overrides verbatim
- Edge case list renumbering (defect placeholder replaced by three real edge cases) is safe — no test comment or prior citation referenced the old numbering

**test-reviewer**

- The two acceptance criteria the implementer judged unprovable against a @MockitoBean repository (case-insensitive whole-name match, no partial match) were correctly relocated to ClinicServiceTests, where they run against real H2 seed data and genuinely exercise the derived query's IgnoreCase and Distinct behavior — this is judged sound, not a coverage gap
- All 9 PRD-intended test names are present (2 relocated, 7 in VetControllerTests as named), plus meaningful additions: HTML/JSON empty-result-on-no-match, blank/whitespace-as-absent on both surfaces (@ParameterizedTest), pagination over the filtered set with total counts, paging-link parameter carry-forward, and URL-encoding of a crafted value (radiology&page=99) distinguishing percent-encoding from HTML entity escaping
- shouldPageOverTheVetsHoldingASpecialtyAlone in ClinicServiceTests directly validates the EAGER @ManyToMany/Distinct paging-count risk flagged in the design-block, against real data rather than an assumption
- No verify()-only interaction tests; MockMvc used per the sanctioned mocking policy; Mockito stubbing on VetRepository matches the host file's pre-existing idiom
- ./gradlew test passed for VetControllerTests, ClinicServiceTests, and PetClinicIntegrationTests

**test-reviewer**

- Finding 1 (BDD naming) fully resolved across all six methods, verified against docs/testing-principles.md § Test Naming and consistent with the rest of the slice
- ./gradlew test passed for VetControllerTests, ClinicServiceTests, and PetClinicIntegrationTests
- vetList.html independently confirmed to contain no \<form>/\<input>/\<select> markup -- the implementer's report of restoring the template after the temporary injection is accurate, not merely taken on trust

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $5.41 | 19m 30s | 97% |
| `agent-team:system-design-expert` | 2 | opus-5 | $2.25 | 6m 10s | 93% |
| `(parent)` | 1 | opus-5 | $1.84 | 38m 26s | 96% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.56 | 4m 25s | 95% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.73 | 4m 7s | 89% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.45 | 1m 0s | 83% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.44 | 1m 51s | 92% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.25 | 48s | 86% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.08 | 11s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.53 | 13m 17s | 97% |
| `(parent)` | opus-5 | $1.84 | 38m 26s | 96% |
| `agent-team:system-design-expert` | opus-5 | $1.69 | 4m 49s | 94% |
| `agent-team:product-requirements-expert` | opus-5 | $1.56 | 4m 25s | 95% |
| `agent-team:feature-implementer` | opus-5 | $1.28 | 4m 8s | 96% |
| `agent-team:feature-implementer` | opus-5 | $0.61 | 2m 4s | 94% |
| `agent-team:system-design-expert` | opus-5 | $0.56 | 1m 20s | 85% |
| `agent-team:test-reviewer` | sonnet-5 | $0.52 | 2m 40s | 90% |
| `agent-team:security-reviewer` | opus-5 | $0.45 | 1m 0s | 83% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.44 | 1m 51s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.25 | 48s | 86% |
| `agent-team:test-reviewer` | sonnet-5 | $0.21 | 1m 26s | 84% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.08 | 11s | 50% |

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

- plugin `agent-team-spring-boot` at `v0.2.4` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `064d588523591361` · `2.1.251 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
