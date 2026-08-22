# vets-specialty-filter r3 — v0.3.8

Filter the vet list by specialty (feature) · started 2026-08-21T21:05:11+00:00 · exec `claude-dev` · status **complete**

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
| review attention (pipeline grade) | clear |

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

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.71. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Matching lives in derived queries ( findBySpecialties_NameIgnoreCase ), the controller only binds and delegates, and the uncached-narrowed-read deviation is carried by an ADR plus a threat-model row rather than left implicit. Two dings:  narrowingSpecialty  puts the blank-equals-absent product rule in the controller, a fresh instance of the deviation the catalog says is not extended; and the minted id  REQ-VETSSPECIALTYFILTER-001  breaks the  REQ-XX-NNN  shape every sibling uses. Tests are behavior-named and phase-structured, cover blank/padded/no-match/encoding boundaries, and add  firstOfTwoPages , but bare  "radiology" ,  "Leary" ,  "Stevens" ,  "Douglas"  are mystery values, and new tests reach for Mockito stubs. Docs are complete: NG-9 narrowed, defect row retired, defect count corrected to three, open questions recorded.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Matching lives in Spring Data derived queries ( findBySpecialties_NameIgnoreCase ), keeping the rule out of the controller; the repository/controller seams and  @Transactional(readOnly = true)  match siblings, and the uncached-narrowed-read decision is reasoned in an ADR. Minor debt: the null-sentinel branch is duplicated across  findPaginated  and  showResourcesVetList , and the minted id  REQ-VETSSPECIALTYFILTER-001  departs from the PRD's own  REQ-XX-NNN  shape. Tests are BDD-named and reuse  helen() / james() , but bare literals  "radiology" ,  "Leary" ,  "Stevens"  remain Tier-3 mystery values,  theRepositoryShouldListAVetHoldingSeveralSpecialtiesUnderEachOfThem  carries two acts, and the seeded-count comment narrates. Docs are thorough: NG-9 narrowed, defect count 4→3, threat-model row, Known Defects row retired.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Repository-level derived queries ( findBySpecialties_NameIgnoreCase ) keep matching out of the controller, and no new type is introduced, so the catalog is respected; but blank-normalization plus null-branching is duplicated across  findPaginated  and  showResourcesVetList , and the coined id  REQ-VETSSPECIALTYFILTER-001  breaks the  REQ-XX-NNN  shape. Tests are BDD-named and phase-structured, with named values like  heldByNoVet  and  withAnAmpersand ; bare  "radiology" / "Leary"  recur as mystery literals, new stubs still use Mockito, and the blank rule is only exercised through MockMvc though it is unit-testable. Docs are thorough: NG-9 narrowed, ADRs and index, contracts, threat-model row, and the defect-count "four"→"three" fix; no visible stale claim survives.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $15.03 | 36m | 45 | 93% | 10 file(s) +369/−31 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.18 | 3m 16s | 90% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VETSSPECIALTYFILTER-001 — Reader narrows the veterinarian directory to one specialty

2 review rounds · 2 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (3) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- • intake-decision (human)
- ◇ **prd-entry** Reader narrows the veterinarian directory to one specialty · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 13m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 57s***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · checkFormat · checkstyle · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 58s***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain not verified against the NVD in this round, and this is a gap in the check rather than a clean result: build.gradle configures no OWASP dependencyCheck plugin (plugins are java, checkstyle, jacoco, spring-boot 4.1.0, dependency-management 1.1.7, native 1.1.2, cyclonedx 3.2.4, javaformat 0.0.47, nohttp 0.0.11), and this reviewer has no network access. The risk this round is nil because the change set touches no build file and adds no dependency, so the resolved artifact set is unchanged from the last verified state. Closing the gap generally needs CI or a human to run an NVD match against the CycloneDX SBOM the build already produces; it pairs with Open Question 6 (no dependency lockfile) in docs/system-design.md.
  - ▹ rec: Not a defect, just the boundary worth remembering: the specialty value is length-unbounded apart from the servlet container's query-string cap, and each narrowed request now costs an uncached database round trip where the unnarrowed page is served from cache. That is the correct trade against cache poisoning, and rate limiting is already a recorded non-control for this demonstration; no action in this slice.
- ✔ **review code-quality** · **approved** · ***◷ 1m***
  - ▹ rec: vetList.html:31-63 now repeats the same 'narrowed ? link-with-specialty : link-without' ternary five times (page-number loop, first, previous, next, last). The duplication predates this change (five separate hardcoded \<a> tags already existed), and this diff extends the existing pattern rather than introducing a new one, so it is not a merge blocker. A future pass could extract the per-page URL into one th:with-computed value or a Thymeleaf fragment to collapse the five near-identical lines into one shared expression.
- ✎ **review test** · **changes_requested** · (3 findings) · ***◷ 2m***
  - [autofix] `ClinicServiceTests.java:219,226,233,24` All seven new specialty-narrowing tests use the pre-2026-07-31 `should{Outcome}` naming (shouldFindVetsHoldingTheNamedSpecialty, shouldFindEveryVetHoldingTheNamedSpecialtyWithoutPaging, shouldListAVetHoldingSeveralSpecialtiesUnderEachOfThem, shouldMatchTheSpecialtyNameIgnoringCase, shouldMatchOnTheWholeSpecialtyNameOnly, shouldFindNoVetForASpecialtyNobodyHolds, shouldCountTheNarrowedVetsRatherThanTheWholeDirectoryWhenPaging) rather than the mandated BDD school `the{Subject}Should{Outcome}` (testing-principles.md § Test Naming: 'Applies to tests written or modified from 2026-07-31 onward... a slice that touches a test renames only that test'). The sibling file VetControllerTests.java gets this right in the same slice (theVetListShouldShowOnlyVetsHoldingTheNamedSpecialty etc.), so the inconsistency is within this change alone, not inherited debt. Matching the host file's older convention is not the applicable rule here — the naming school is a written-date rule, not a file rule.
    - fix: Rename the seven new ClinicServiceTests methods to the BDD form, e.g. shouldFindVetsHoldingTheNamedSpecialty -> theRepositoryShouldFindVetsHoldingTheNamedSpecialty, shouldMatchOnTheWholeSpecialtyNameOnly -> theRepositoryShouldMatchOnlyOnTheWholeSpecialtyName, and so on for the remaining five.
  - [autofix] `VetControllerTests.java:542` Both tests pack two independent scenarios (empty string vs. all-spaces; first-letters-only vs. padded-with-spaces) into one straight-line test body via two separate act+assert pairs, instead of a @ParameterizedTest — the checklist's named default AUTOFIX ('Missing @ParameterizedTest for repetitive cases') and testing-principles.md's edge-case guidance ('@ParameterizedTest with @CsvSource covers all edge cases').
    - fix: Convert each to a @ParameterizedTest with @CsvSource carrying the two data points (e.g. specialty value + expected-empty/expected-full flag), one assertion per invocation.
  - [autofix] `VetControllerTests.java:617` The JSON-surface blank test only exercises the all-spaces case ("   "); it never exercises the empty-string case. The HTML-surface counterpart (theVetListShouldListEveryVetWhenTheSpecialtyIsBlank) exercises both. The PRD acceptance criterion ('a specialty name that is empty or all spaces... every veterinarian is listed') is therefore only half-covered on the machine-readable surface.
    - fix: Add the empty-string case to theVetJsonShouldListEveryVetWhenTheSpecialtyIsBlank (or fold it into the @ParameterizedTest conversion above alongside the all-spaces case).
- ↻ **implement** (implementer) ← test · (3 findings) · ***◷ 2m***
  - ▲ **build ✓ clean** · build · test · checkFormat · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved** · ***◷ 24s***
- ◆ **grade CLEAR** · narrow the veterinarian directory by specialty
  - blast_radius — **clear** — Ten files, one module, no sensitive paths: two Java files in the vet package, one template, and five docs. The widest reach is vetList.html, whose five pagination links were all rewritten and so also serve the unnarrowed page every existing reader sees; that path is pinned by a test asserting the plain page-two link carries no specialty parameter.
  - semantic_surprise — **clear** — Read every prod hunk against the requirement and found nothing the diff's shape would not predict. Narrowing is a Spring Data derived query with a bound parameter, blank-vs-padded normalization sits in one helper used identically by both handlers, the two narrowed reads deliberately omit the cache annotation so caller text never keys the unevicted vets cache, and the template rewrite replaces string-preprocessed URLs with parameter syntax that URL-encodes rather than concatenates.
  - test_adequacy — **clear** — Tests assert real outcomes against the real H2 seed data (radiology is held by Leary and Stevens, Douglas holds surgery and dentistry) rather than restating the implementation, and each would fail against a plausible wrong implementation: prefix matching, trimming the padded name, a page count taken from the whole directory, an unencoded ampersand in a link, or a dropped specialty when paging onward. Both the page and the machine-readable surface are covered, including the empty and all-spaces cases the second review round closed.
  - reviewer_hedging — **clear** — The final round approved with no recommendations, and the three round-one test findings were all fixable autofixes that were made and re-verified. Two parked notes remain and neither is a reservation about this change: code quality flags the five-fold ternary duplication in vetList.html as pre-existing shape it extends rather than introduces, and security reports it could not run an NVD supply-chain match, a standing tooling and network gap whose applicability here is nil because the change set touches no build file or dependency.
  - scope_deviation — **clear** — The change matches the intake decision term for term, including the three product calls the owner made there: NG-9 narrowed rather than dropped, a fresh requirement id with REQ-VET-002 left withdrawn and unreused, and a URL contract with no page control added. The single design revision was bookkeeping (declaring two doc paths the audit caught as uncovered), not an architectural change, and the row's zero build retries is consistent with counting only failures after that revision.
  - why — Read every hunk; the code does exactly what the requirement describes, with the boundary cases pinned against real seed data. Confirm one thing that outlives the code: this slice redraws PRD non-goal NG-9 and lifts the machine-readable vet route out of Known Defects. Both are quoted owner decisions, so check the recorded wording is the boundary you meant.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**doc-reviewer**

- Both new ADRs follow the template and naming conventions: the non-goal ADR uses the non-goal- filename infix and Non-goal: NG-9 in Implementation; the standard ADR uses Requirements: REQ-VETSSPECIALTYFILTER-001
- docs/adr/README.md carries both new index rows with correct dates and statuses
- docs/prd.md's REQ-VETSSPECIALTYFILTER-001 prose, Done-when bullets, and edge cases match the intake-decision's product terms (whole-name case-insensitive match, blank-means-absent, no page control) with no code-level language
- The req-vetsspecialtyfilter-001 anchor exists at docs/prd.md:123 and every cross-reference to it (from the non-goal ADR and elsewhere) resolves
- docs/system-design.md's new Contracts prose and the cache-scope paragraph stay at the purpose+source-pointer level: no field tables, parameter tables, or literal constant values, and the described behavior (findBySpecialties_NameIgnoreCase uncached, Thymeleaf parameter-syntax links, blank-only normalization) matches the diff exactly
- The new Threat Model row and the retained Open Question 5 cross-reference the new ADR correctly, and the Known Defects/provenance counts stay internally consistent
- Specialty and Veterinarian terms used by the new requirement are already defined in docs/ubiquitous-language.md; no new domain vocabulary was introduced
- No relative references, hard-wrapped lines, or broken links found in any changed document

**security-reviewer**

- Injection into data access: the narrowing is a Spring Data derived query (VetRepository.findBySpecialties_NameIgnoreCase, paged and unpaged). No query text is concatenated anywhere in the change; the caller-supplied name reaches JPA as a bound parameter. Meets security-principles.md 'Injection into data access'.
- Cross-site scripting: vetList.html rewrites all five pagination links from the old @{'/vets.html?page=__${i}__'} string-concatenation-plus-preprocessing form to Thymeleaf parameter syntax @{/vets.html(page=...,specialty=${specialty})}. The value is URL-encoded by the link builder and attribute-escaped by the engine, so an ampersand, hash, quote, or javascript:/markup payload in ?specialty= cannot break out of the href. Class sweep: grep for '__${' and 'th:utext' across src/main/resources/templates/ now returns no hits at all, so this change removes the last template-expression-preprocessing sites rather than adding one. Default output escaping stays on; the specialty is not rendered as page text anywhere.
- Cache-key poisoning: the two narrowed reads deliberately carry no @Cacheable, unlike their findAll siblings, so caller-chosen text never becomes a key in the unbounded, evictionless 'vets' Caffeine cache. The divergence from the neighbouring cached reads is justified inline in the VetRepository javadoc and in docs/adr/2026-08-21-uncached-specialty-narrowed-vet-lookups.md, satisfying the Pattern Consistency clause. docs/system-design.md gains a matching Threat Model row that correctly scopes the residual page-keyed exposure as pre-existing and unchanged.
- Widening the exposed surface: no new route. Both handlers gain one optional scalar @RequestParam on already-public directory data; no mass-assignment surface (no command object, no binder change), no management-endpoint change, no new dependency (build.gradle is not in the change set).
- Input handling at the boundary: narrowingSpecialty() normalizes absent/empty/blank to null at the controller edge and delegates, with no defensive re-checking downstream. No filesystem or classpath resource is composed from the value, no shell or process execution, no deserialization entry point, no logging of the value (so no log-injection vector), and no regex, so no ReDoS surface. Greps for Runtime/ProcessBuilder/exec(/enableDefaultTyping/JsonTypeInfo//tmp/ across src/main/java return only pre-existing, unrelated hits.
- No secret introduced: a case-insensitive sweep of the whole change set for password/secret/token/apikey/credential/private_key matches one pre-existing docs/system-design.md Threat Model line and nothing else.

**code-quality-reviewer**

- VetController.narrowingSpecialty centralizes the blank/absent-vs-padded distinction in one place, used identically by both handlers, matching the design-block's mitigation for the blank-vs-surrounding-spaces risk
- VetRepository.findBySpecialties_NameIgnoreCase uses the underscore-disambiguated property-path form the design-block called for, and the class-level Javadoc already commits this interface to Spring Data naming conventions, so the underscore is idiomatic here rather than a stray deviation (grep of OwnerRepository found no precedent, IntelliJ oracle not connected so this is the grep-based weaker basis)
- vetList.html builds every pagination link through Thymeleaf's @{...(...)} parameter syntax rather than string concatenation, matching the design-block's XSS/link-corruption mitigation, and omits the specialty parameter entirely on the unnarrowed branch instead of emitting a dangling 'specialty='
- VetRepository's new methods carry Javadoc explaining both the matching rule and, notably, why they are deliberately uncached, cross-linking the ADR - this will save the next reader a trip to git blame
- Method lengths, control flow, and early-return shape stay well within the checklist bounds; no new mutable state, no swallowed exceptions, no logging concerns

**test-reviewer**

- Repository-level tests exercise the real H2-backed query (ClinicServiceTests), matching the brief's real-I/O-for-integration rule; VetControllerTests' MockitoBean stub of VetRepository is the pre-existing, sanctioned controller-boundary pattern already used in this file
- The Hibernate collection-fetch-join mis-paging risk the design-block flagged is directly covered: shouldCountTheNarrowedVetsRatherThanTheWholeDirectoryWhenPaging asserts totalElements, totalPages, and content size against the real database
- The unencoded-URL-punctuation risk the design-block flagged is directly covered: theVetListShouldEncodeASpecialtyCarryingUrlPunctuationIntoItsLinks asserts percent-encoding and absence of the raw ampersand
- The blank-vs-padded-spaces distinction the design-block called out as easy to conflate is covered in both directions (all-spaces narrows nothing; padded valid name matches nothing)
- Case-insensitive and whole-name-only matching are both covered at the repository layer where the matching logic actually lives
- Test data uses named locals (heldByNoVet, firstLettersOnly, paddedWithSpaces, withAnAmpersand) rather than mystery literals, and reuses the existing james()/helen() factories
- All new and existing VetControllerTests/ClinicServiceTests pass (13 and 19 tests respectively, 0 failures)

**test-reviewer**

- All seven new ClinicServiceTests methods renamed to the BDD the{Subject}Should{Outcome} school (theRepositoryShouldFindVetsHoldingTheNamedSpecialty, etc.), matching VetControllerTests' convention within the same slice
- ClinicServiceTests.theRepositoryShouldMatchOnlyOnTheWholeSpecialtyName and VetControllerTests.theVetListShouldListEveryVetWhenTheSpecialtyIsBlank converted to @ParameterizedTest with @CsvSource, each row carrying a role name (first letters only / padded with spaces; no name at all / all spaces) rather than a bare positional value
- VetControllerTests.theVetJsonShouldListEveryVetWhenTheSpecialtyIsBlank now covers both the empty-string and all-spaces cases via the same @ParameterizedTest, closing the previously half-covered PRD blank-specialty criterion on the JSON surface
- No production code changed this round; VetControllerTests (15) and ClinicServiceTests (20) pass, 0 failures, verified independently in this review

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $8.64 | 18m 42s | 96% |
| `(parent)` | 1 | opus-5 | $4.94 | 39m 7s | 96% |
| `agent-team:system-design-expert` | 2 | opus-5 | $4.37 | 6m 18s | 90% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $3.03 | 4m 59s | 94% |
| `agent-team:change-grader` | 1 | opus-5 | $2.18 | 3m 16s | 90% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.53 | 3m 26s | 89% |
| `agent-team:security-reviewer` | 1 | opus-5 | $1.41 | 1m 25s | 80% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.96 | 1m 40s | 86% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.71 | 1m 16s | 91% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $6.06 | 13m 41s | 97% |
| `(parent)` | opus-5 | $4.94 | 39m 7s | 96% |
| `agent-team:system-design-expert` | opus-5 | $3.27 | 4m 59s | 92% |
| `agent-team:product-requirements-expert` | opus-5 | $3.03 | 4m 59s | 94% |
| `agent-team:change-grader` | opus-5 | $2.18 | 3m 16s | 90% |
| `agent-team:feature-implementer` | opus-5 | $1.46 | 3m 12s | 94% |
| `agent-team:security-reviewer` | opus-5 | $1.41 | 1m 25s | 80% |
| `agent-team:test-reviewer` | sonnet-5 | $1.24 | 2m 47s | 89% |
| `agent-team:feature-implementer` | opus-5 | $1.12 | 1m 48s | 93% |
| `agent-team:system-design-expert` | opus-5 | $1.10 | 1m 19s | 82% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.96 | 1m 40s | 86% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.71 | 1m 16s | 91% |
| `agent-team:test-reviewer` | sonnet-5 | $0.29 | 39s | 89% |

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

- plugin `agent-team-spring-boot` at `v0.3.8` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `064d588523591361` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
