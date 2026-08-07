# vets-specialty-filter r2 — v0.2.0

Filter the vet list by specialty (feature) · started 2026-08-05T06:32:14+00:00 · exec `claude-dev` · status **complete**

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

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 5 (±1) | 4 (±1) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $1.02. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Matching lives in  VetRepository.findBySpecialtiesNameIgnoreCase  (paged and unpaged), not the controller, honoring the Web-controller row;  namedSpecialty()  only normalizes binding, mirroring owner search's blank-means-all, and the uncached choice is justified in an ADR. Tests are BDD-named ( theVetDirectoryShouldShowAnEmptyListWhenNoVeterinarianHoldsTheSpecialty ), reuse  james() / helen()  factories, and cover case-insensitivity, prefix non-match, empty result, blank value, and paging. But bare literals ("radiology", "hippiatrics",  PageRequest.of(0, 5), 7 ,  totalPages  2) are Tier-3 mystery values with undermined expectations, and  verify(..., never()).findBySpecialtiesNameIgnoreCase(...)  asserts a call, not behavior. Thymeleaf  specialty=${specialty}  emits an empty  specialty=  when unset — harmless but untidy. Docs are complete: NG-9 narrowed, REQ-VET-003/004 minted, REQ-VET-002 kept retired, stale defect row and removal note deleted, contracts table rewired.

**Sample 2** — design-fit 5 · test-quality 3 · maintainability 4 · doc-fit 5

> Matching lives in  VetRepository.findBySpecialtiesNameIgnoreCase , not the controller, so the catalog's Web controller row holds and both surfaces share one rule; the uncached choice is argued in an ADR and mirrored in the repository Javadoc. Docs move everywhere the change touches: NG-9 narrowed, REQ-VET-003/004 minted, the withdrawn REQ-VET-002 note corrected, the contracts table and the stale 'pending removal' defect row retired. Tests are behavior-named and cover case, prefix, empty, paging and blank, but three assert interactions ( verify(this.vets, never()) ) rather than behavior, literals like  "radiology" ,  "Leary" ,  7  and  totalPages 2  are undeclared mystery values with no derived expectation, and  named()  carries a comment restating its own signature.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Matching lives in  VetRepository.findBySpecialtiesNameIgnoreCase  (paged + collection overloads), keeping the rule out of the controller per the Web controller row;  VetController  only normalizes and selects, and the uncached choice is reasoned in an ADR. Minor debt: the null-check/query-selection branch is duplicated across  showVetList / showResourcesVetList , styled once as if/return and once as an inline ternary. Tests are exemplary in BDD naming and phase structure and cover case, prefix, empty, paging and URL encoding, but  verify(this.vets, never()).findBySpecialtiesNameIgnoreCase(...)  asserts interaction rather than behavior, new tests reach for the Mockito stub without recording the exception, and literals like "radiology", "hippiatrics", "Leary" are unnamed Tier-3 values. The  /** Matches a veterinarian... */  helper comment restates code. Docs are complete: NG-9 narrowed, REQ-VET-003/004 minted, superseded note, contracts table, and the removed known-defect row.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $10.12 | 30m | 25 | 90% | 10 file(s) +305/−25 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.37 | 3m 54s | 86% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-004 — Staff and programs can narrow the veterinarian directory to one specialty

1 review round · 1 build-pass · **1 build-failure** · grade **CONCERN**

| reviewer | R1 |
| --- | --- |
| **code-quality** | **✔** |
| **test** | **✔** (1) |
| **security** | **✔** |
| **doc** | **✔** |

- ◇ **prd-entry** Staff and programs can narrow the veterinarian directory to one specialty · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 10m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 45s***
- ✔ **review security** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · (1 finding) · ***◷ 2m***
  - [autofix] `VetControllerTests.java:150-155` theFilteredVetDirectoryShouldStillListOnePageAtATime and theFilteredPaginationLinksShouldEncodeTheSpecialty hard-code PageRequest.of(0, 5) and a total of 7 as bare literals, then assert the derived totalPages(2)/totalItems(7L) as separate literals rather than expressions of the inputs — a Tier-3 mystery-literal / Derived-Expectations gap under testing-principles.md for tests written in this slice (2026-08-05).
    - fix: Name the page size and total as constants (e.g. PAGE_SIZE, TOTAL_VETS_HOLDING_SPECIALTY) and derive the expected totalPages via a small computation (e.g. Math.ceilDiv) so the assertion documents where 2 comes from instead of restating it.
- ◆ **grade CONCERN** · narrow the veterinarian directory by specialty
  - blast_radius — **clear** — 78 prod lines in one feature package (VetController, VetRepository) plus vets/vetList.html; no sensitive paths, no build files, no dependency change. The five doc files are wide but inert at runtime, and the one shared runtime artifact is the vetList template, whose five pagination links all changed in the same way.
  - semantic_surprise — **concern** — The template moved from concatenated hrefs to the parameterized link form, and Thymeleaf's StandardLinkBuilder appends a null-valued parameter as a bare name with no equals sign (verified in StandardLinkBuilder.processAllRemainingParametersAsQueryParams). So the UNFILTERED vet list now emits /vets.html?page=2&specialty on every pagination link, a visible URL change on a pre-existing page that no assertion pins and that the diff's framing does not lead you to expect. Harmless in behavior (a name-only parameter binds as empty string, strips to null, stays unfiltered), cosmetic in the address bar.
  - test_adequacy — **concern** — Matching semantics are genuinely proven against seeded H2 (case-insensitive whole-name match, prefix rejection, both overloads), and blank-as-absent is proven by verify never on both routes. But no test ever issues a PAGED filtered query against a real database: ClinicServiceTests passes Pageable.unpaged(), and the pagination test stubs VetRepository and asserts a hand-built PageImpl. Vet.specialties is FetchType.EAGER ManyToMany, so filtered paging over that association is exactly where a count-query or in-memory-pagination surprise (HHH000104) would live, and the suite cannot observe it.
  - reviewer_hedging — **concern** — All four planned reviewers ran and approved, the roster matches the full battery, and the security and doc approvals are unqualified with substantive evidence. The test-reviewer's approval, however, ships one open fixable finding (mystery literals: PageRequest.of(0, 5) and a total of 7, with totalPages 2 and totalItems 7 restated rather than computed, at VetControllerTests.java:150-155) - approval with a caveat, low weight but unresolved.
  - scope_deviation — **clear** — Every changed path is claimed: the nine code, template, test and design-doc paths sit in the superseding design-block's lists, and docs/prd.md is the PRD author's own surface. The one design revision was path bookkeeping with no code change and zero build retries after it; no consultations. Folding REQ-VET-003 and the NG-9 narrowing into this slice was the product owner's decision and is recorded in two ADRs.
  - why — Correct and well-tested where it counts, but two residuals deserve a look: unfiltered pagination links now render a bare specialty suffix (Thymeleaf's null-parameter form) on an existing page nothing asserts, and filtered paging is never exercised against a real database over the eager specialties association. Read the template and the paging path.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**doc-reviewer**

- REQ-VET-002 stays in Superseded, is never renumbered/reused, and its successor mapping to REQ-VET-003 is stated once and consistently in prd.md, the non-goal ADR, and the revisited Open Question
- NG-9's narrowed row still states what it declines (free-text veterinarian/pet/visit search) and does not contradict REQ-VET-003/004 or any other non-goal; NG-2 (no vet management) is untouched by the filter
- no leftover text describes /vets as unsupported, defective, or pending removal — the Known Defects row was fully removed from system-design.md, the Vets contract's Implements moved off "—" (repairing the "three kinds" count above the table), and the only remaining pending-removal/no-consumer phrasing is historical context inside past-tense sentences that then state the current resolution
- the PRD boundary rule holds: REQ-VET-004's prose and Done-when bullets name behavior only (whole-name case-insensitive matching, blank-as-absent, empty-list-at-200, pagination preserved); no /vets.html, /vets, or ?specialty= route/parameter text appears in docs/prd.md — that contract is confined to the prd-entry handoff record as intended
- adr/README.md carries both 2026-08-05 index rows, both new ADRs are Accepted with Requirements/Non-goal Implementation sections and em-dash References, and cross-links between prd.md, both ADRs, and system-design.md#contracts all resolve

**security-reviewer**

- SQL injection: the specialty reaches the database only through the Spring Data derived queries findBySpecialtiesNameIgnoreCase(String, Pageable) and (String). Derived queries bind the parameter; no string-concatenated JPQL or SQL is introduced. Consistent with the SQL-injection row of the system-design threat model.
- XSS: all five pagination links in vets/vetList.html now use the parameterized link form @{/vets.html(page=...,specialty=${specialty})}. Thymeleaf URL-encodes link-expression query values and HTML-escapes th:href output, so the caller-derived value can neither break out of the href nor inject a further parameter. The migration is complete: a grep of src/main/resources/templates for the preprocessed __${...}__ href form finds no remaining instance in vetList.html, and the surviving instances (ownersList.html, layout.html, fragments) interpolate integers or fixed fragment names, not this parameter. The ampersand test (specialty=rad%26ology) pins the encoding.
- No second sink for the parameter: ${specialty} appears in vetList.html only inside the five link expressions. No th:utext, no th:inline script block, no attribute-level raw interpolation anywhere in templates/. The JSON route does not echo the parameter back into its response.
- Cache decision holds. Keying an unbounded JCache 'vets' cache on caller-supplied text over an unauthenticated route would let any caller grow the cache without limit; leaving the two filtered queries uncached removes that vector rather than mitigating it. The ADR states the reasoning and the repository Javadoc carries it at the point of use, so a later @Cacheable addition is a visible regression rather than a silent one.
- Unbounded-input assessment: the absence of a length cap on the specialty parameter leaves no material risk on this path. The value is normalized (strip, blank-to-null), never persisted, never cached, never logged, never written to a filesystem path, and never rendered unencoded; it is bound as a query parameter against an indexed lookup over a bounded reference table. An oversize value costs one bounded query, with nothing accumulating across requests.
- REQ-VET-003 exposure profile: reinstating /vets adds no data. It serves the same Vet and Specialty fields the already-public /vets.html page renders, under the same absence of authentication that the system-design Security Context records for every route. Making an already-public dataset filterable narrows a response rather than widening the disclosed field set, and the filter accepts no operator, wildcard, or projection a caller could use to reach other columns.
- Supply chain: the change set touches no build file and adds no dependency, so it introduces no new third-party code. Spring Boot stays at 4.1.0 per the committed build.gradle.
- No credential-shaped material in the diff: no token, password, secret, or key literal in the production, template, or test hunks.

**code-quality-reviewer**

- VetRepository's two new derived-query overloads mirror the existing findAll()/findAll(Pageable) overload pair and stay uncached per the accepted ADR, each with a javadoc note pointing at the ADR file
- VetController's namedSpecialty helper centralizes the blank-is-absent normalization in one place and is documented with a clear javadoc; both routes reuse it rather than duplicating the strip/blank check
- vetList.html's move to the parameterized @{...(page=...,specialty=...)} link form is applied consistently across all five pagination links
- checkFormat, compileJava, and checkstyleMain all pass cleanly (verified with a fresh --rerun-tasks run, not just UP-TO-DATE)
- Tests use AssertJ/Hamcrest fluent assertions, real DataJpaTest-backed repository calls in ClinicServiceTests, and MockMvc (the sanctioned mock) in VetControllerTests; the reused pageable field in ClinicServiceTests matches the existing owner-search test convention
- BDD-style test names read as full behavior statements and each covers a single scenario (case-insensitivity, partial-match rejection, blank-is-unfiltered, empty-result, pagination-preserved, specialty-URL-encoding)

**test-reviewer**

- All 8 prd-entry acceptance criteria have a real assertion behind them: whole-name case-insensitive matching and prefix-non-match are proven against seeded H2 data in ClinicServiceTests.theSpecialtyFilterShouldDisregardLetterCase / theSpecialtyFilterShouldNotMatchAPartialSpecialtyName / theUnpagedSpecialtyFilterShouldListOnlyVeterinariansHoldingTheSpecialty, not against a mocked repository
- All 8 test_names from the prd-entry are present and exercise the described behavior (verified by name and by content)
- The design-block's placement decision held: VetControllerTests only asserts binding/normalization/pagination/link-encoding through the mocked VetRepository (with verify(...,never()) proving blank/absent skip the filtered query), while matching semantics live in ClinicServiceTests against the real autowired repository — a stub could not have verified case-insensitivity or prefix-rejection
- Both published forms (/vets.html and /vets) are covered for filtered, blank-as-absent, no-parameter, and empty-result cases, discharging REQ-VET-003's requirement that the machine-readable list be exercised as a supported surface
- theFilteredPaginationLinksShouldEncodeTheSpecialty pins percent-encoding of an ampersand-bearing specialty in the pagination href, closing the injection/encoding risk the design-block flagged
- ./gradlew test passes for both files; VetController.java sits at 100% line coverage per the jacoco report, comfortably clearing the 80% domain/core target
- Mocking stays within the brief's policy: MockMvc plus a Mockito stub on VetRepository at the web-layer boundary in a @WebMvcTest slice, real H2 I/O in the @DataJpaTest integration test — no internal domain logic is mocked

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $4.91 | 12m 26s | 96% |
| `agent-team:system-design-expert` | 2 | opus-5 | $4.30 | 7m 8s | 90% |
| `(parent)` | 1 | opus-5 | $2.55 | 33m 33s | 94% |
| `agent-team:change-grader` | 1 | opus-5 | $2.37 | 3m 54s | 86% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $2.14 | 4m 3s | 89% |
| `agent-team:security-reviewer` | 1 | opus-5 | $1.32 | 1m 13s | 76% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.90 | 1m 57s | 86% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.81 | 57s | 85% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.77 | 2m 23s | 85% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.07 | 12s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.24 | 10m 44s | 97% |
| `agent-team:system-design-expert` | opus-5 | $2.75 | 5m 12s | 92% |
| `(parent)` | opus-5 | $2.55 | 33m 33s | 94% |
| `agent-team:change-grader` | opus-5 | $2.37 | 3m 54s | 86% |
| `agent-team:product-requirements-expert` | opus-5 | $2.14 | 4m 3s | 89% |
| `agent-team:system-design-expert` | opus-5 | $1.55 | 1m 56s | 83% |
| `agent-team:security-reviewer` | opus-5 | $1.32 | 1m 13s | 76% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.90 | 1m 57s | 86% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.81 | 57s | 85% |
| `agent-team:test-reviewer` | sonnet-5 | $0.77 | 2m 23s | 85% |
| `agent-team:feature-implementer` | opus-5 | $0.67 | 1m 41s | 90% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.07 | 12s | 50% |

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
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `610c2c59194e4044` · `2.1.222 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
