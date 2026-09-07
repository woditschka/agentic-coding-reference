# vets-specialty-filter r1 — v0.3.9

Filter the vet list by specialty (feature) · started 2026-09-06T18:30:27+00:00 · exec `claude-dev` · status **complete**

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
| reading depth (pipeline grade) | skim |

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
| 4 (±1) | 4 (±0) | 4 (±0) | 5 (±2) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.74. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 3

> Normalization stays in the controller where system-design assigns binding, matching lives in derived repository queries ( findDistinctBySpecialtiesNameIgnoreCase ), and the uncached choice is reasoned in an ADR rather than copied from the neighbouring  @Cacheable  reads. Controller tests are behavior-named specifications covering blank, unmatched, encoded, and pagination-carry cases. Weaker spots:  ClinicServiceTests  new tests use bare literals ("radiology", "Leary", "Stevens", 2) with no constants or factory, plus the narration comment "// Douglas is seeded holding both surgery and dentistry"; the template repeats every page link twice through a  narrowed  ternary, and  pageOfSix()  returns one element. Documentation is broad and mostly current, but the PRD preamble now claims "six further questions stay open" after adding three and answering none — the prior count was ten.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> VetController.specialtyNamedBy is request normalization the design doc assigns to the web layer, and matching stays in derived repository finders (findDistinctBySpecialtiesNameIgnoreCase), so no new business rule lands in the controller; the uncached choice is reasoned in its own ADR. Docs move thoroughly: NG-9 narrowed, REQ-VET-003 minted with REQ-VET-002 left withdrawn, contracts/threat/known-defect rows and open questions all updated. Tests are behavior-named and phase-structured, but ClinicServiceTests leans on bare seed literals ("Leary", "Stevens", "Douglas") and carries a narrating comment, and no JSON-surface test covers an unheld or blank specialty. pageOfSix() returns one vet with total 6 under a doc saying "five out of six" — a misleading fixture name; template links duplicate every href in two ternary forms.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Matching stays in derived repository queries (findDistinctBySpecialtiesNameIgnoreCase); the controller only binds, normalizes via specialtyNamedBy, and shapes the model — the placement system-design assigns the web layer, so no new controller rule appears. The uncached-filtered-read asymmetry is decided in an ADR and mirrored in the repository javadoc, the Contracts row, the threat table, and open question 5. Tests are behavior-named and reuse james()/helen(); page-link encoding is asserted directly. Weaknesses: ClinicServiceTests carries bare literals ("radiology", "Leary", expected 2 pages) and a narrating comment above the Douglas assertions, with two act/assert pairs in one test; no blank-specialty test for /vets; and vetList.html repeats the narrowed/unnarrowed ternary five times.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $13.75 | 37m | 34 | 94% | 10 file(s) +363/−33 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.99 | 2m 45s | 91% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Narrowing the veterinarian directory to one named specialty

2 review rounds · 2 build-passes · **1 build-failure** · grade **SKIM**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | **✔** | · |
| **security** | **✔** | · |
| **doc** | ✎ (1) | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Narrowing the veterinarian directory to one named specialty · (prd-expert) · ***◷ 4m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 12m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 1m***
  - ▹ rec: findPaginated and findVets (VetController.java:65-72,99-104) each repeat the same 'specialty == null ? unfiltered-read : filtered-read' branch. Small enough to leave as-is at this scope, but a shared private helper would remove the duplication if a third surface is ever added.
  - ▹ rec: Pre-existing inconsistency this change extends rather than introduces: findPaginated (VetController.java:69) calls vetRepository.findAll(pageable) with no `this.`, while the new findVets (lines 101,103) and the untouched showResourcesVetList body use `this.vetRepository...`. Not worth a fix-only commit, but worth normalizing next time the file is touched.
- ✔ **review test** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain check NOT RUN — no OWASP Dependency-Check plugin is configured in build.gradle, and this reviewer has no network access, so no NVD match was performed in this pass. Resolved framework versions from build.gradle: Spring Boot 4.1.1, io.spring.dependency-management 1.1.7, spring-javaformat 0.0.48, checkstyle 12.3.1, jacoco 0.8.15, graalvm native 1.1.2, cyclonedx 3.4.1. The change adds no dependency, so this is a standing project gap rather than a defect of this slice; a human or CI should close it (the CycloneDX SBOM task already produces the input an external scanner needs).
  - ▹ rec: The specialty parameter is length-unbounded before it reaches the IgnoreCase join query. Practically capped by the container's request-line limit and matched against a tiny lookup table, so the demonstrated reach does not support a finding; noted only because the same absence in a larger dataset would be a cheap scan amplifier.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 2m***
  - **[blocked]** `system-design.md:171-186` The specialty query parameter is a new caller-supplied value reflected into rendered HTML: vetList.html builds every page-link href from it (src/main/resources/templates/vets/vetList.html:29-61), mitigated only by Thymeleaf link-expression encoding instead of the __${...}__ concatenation the numeric page uses. The governing design-block (line 9) named this exact risk and its mitigation. Security Context's 'Inputs it processes' bullet was updated to list the new specialty parameter, but the Threat Model table's Cross-site scripting row still reads 'Owner, pet, and visit fields are echoed into HTML pages' — it does not mention the vet specialty parameter or the link-expression-encoding mitigation that makes it safe. A reader of the Threat Model alone (including the security-reviewer, per this doc's own instruction to read Security Context before reviewing) cannot see that this new input reaches rendered HTML at all.
    - fix: Add the specialty parameter to the Cross-site scripting row's Attack Vector (or add a new row) naming the page-link hrefs as the reflection point, and state the link-expression-encoding mitigation, mirroring how the Unbounded cache growth row already documents the caching ADR's risk and mitigation.
- ↻ **fix design** ← doc · (1 finding)
- ◈ **design-block** **new** · (design) · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 25s***
- ◆ **grade SKIM** · narrow the vet directory by specialty
  - blast_radius — **skim** — Three production files in the single vet package plus its template; no sensitive path, no new type, module, or dependency, and the 46-hunk count is dominated by the five doc files and the mechanical rewrite of six pagination links.
  - semantic_surprise — **skim** — Reading every hunk, the code does what the diff advertises: one null-sentinel branch reused identically on both routes, isBlank/strip handling that matches the stated blank-names-none rule, and page links rewritten from the old preprocessed literal URL to link-expression parameters with byte-identical unfiltered output, asserted by a test.
  - test_adequacy — **skim** — Tests would fail against a broken implementation rather than restate it: the H2-backed repository tests pin whole-name matching (a partial name returns empty), case-insensitivity, and a distinct page count of 2 over 2 matches at page size 1, while MockMvc drives real rendering to assert the specialty is URL-encoded into page links and absent when none is named.
  - reviewer_hedging — **skim** — Four round-1 approvals with no findings from code-quality, test, and security; the doc-reviewer's one blocking Threat Model gap was fixed and re-approved in round 2 with an empty findings list. The parked recommendations are round-1, not late-round, and each is explicitly scoped out of this slice: two style notes left as-is, and a standing disclosure that no supply-chain scan is configured on a change that adds no dependency.
  - scope_deviation — **skim** — The diff lands exactly on the owner's three recorded decisions: NG-9 narrowed by ADR, the JSON route reinstated under a fresh id with REQ-VET-002 left withdrawn, and a URL-only contract with no page control, with zero consultations, zero build retries, and design revisions that corrected path lists and a doc finding rather than the design.
  - why — Clean single-package change matching the recorded intake decisions hunk for hunk, with tests that pin the whole-match, case-insensitive, and distinct-page-count behavior against a real database. Confirm and merge; the only open item is the project's standing lack of a supply-chain scan, which this change does not touch.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- Matching logic stays in the derived query (findDistinctBySpecialtiesNameIgnoreCase), not in the controller — controller only normalizes/strips and selects which repository read to call, per the design-block's Web-controller-row mitigation
- Case folding and Distinct are expressed in the query itself, avoiding the PostgreSQL collation defect and duplicate-row inflation the design-block flagged
- Filtered VetRepository reads are deliberately left uncached, with Javadoc pointing at the ADR, closing the unbounded-cache-key risk the design-block raised
- vetList.html builds narrowed page links with Thymeleaf link-expression parameters (@{...}) rather than string concatenation, so the specialty is URL-encoded — verified against the XSS risk the design-block called out, and covered by theVetDirectoryPageLinksShouldEncodeTheNamedSpecialty
- specialtyNamedBy mirrors OwnerController's established blank-means-broadest/strip() pattern (owner/OwnerController.java:94-104), keeping the new branch consistent with the existing codebase idiom
- New domain vocabulary (specialty, veterinarian, vet) matches docs/ubiquitous-language.md; no coined synonyms introduced
- Javadoc on the two new VetRepository methods is precise about matching semantics, distinctness, and the caching decision

**test-reviewer**

- Every Done-when bullet and PRD test_names entry has a matching test (coverage-map: 8/8 declared, 7/7 bullets covered)
- Matching rule (case-insensitive whole-name match, partial-match rejection, distinct-per-specialty listing) is tested at the repository/query seam via ClinicServiceTests against the real seeded H2 database, matching the design-block's assignment of matching logic to VetRepository rather than the controller
- Boundary-layer concerns (blank/whitespace normalization, page-link construction and encoding, page-count reflection) are tested at the controller via VetControllerTests, matching the design-block's assignment of normalization and response shaping to VetController
- XSS mitigation (Thymeleaf link-expression parameters replacing string concatenation) is explicitly covered by theVetDirectoryPageLinksShouldEncodeTheNamedSpecialty, verifying both the encoded form is present and the raw unencoded value is absent
- Test data uses named constants with role comments (RADIOLOGY, SPECIALTY_NOBODY_HOLDS, CROWDED_SPECIALTY, SPECIALTY_NEEDING_ENCODING) and local variables (openingLettersOfRadiology) instead of mystery literals
- Test names follow the theSubjectShouldOutcome BDD school consistently across both files
- ./gradlew test green for both changed test classes; no regression in existing showVetListHtml/showResourcesVetList tests
- Mocking stays within policy: VetControllerTests continues the file's pre-existing MockitoBean-on-VetRepository pattern for the sanctioned MockMvc web-layer boundary; ClinicServiceTests uses the real repository against a real seeded database, no mocking

**security-reviewer**

- Data-access injection: the specialty name reaches persistence only through the Spring Data derived queries VetRepository.findDistinctBySpecialtiesNameIgnoreCase(String) and (String, Pageable). Both are parameterized by construction; no query text is concatenated anywhere in the diff. Meets security-principles.md 'Injection into data access'.
- XSS / output escaping: the caller-supplied specialty is never rendered as page text. It reaches the view only as a link-expression parameter (@{/vets.html(page=...,specialty=${specialty})}), which URL-encodes the value and HTML-escapes the resulting href. No th:utext, no inline JS, no remote resource, and all hrefs stay context-relative literals — no javascript:/data: URI is reachable.
- Thymeleaf preprocessing removed: the four pre-existing th:href='@{'/vets.html?page=__${i}__'}' expressions were replaced with link-expression parameters. grep for '__${' across src/main/resources/templates/ now returns zero hits, so the change eliminates the last instances of the preprocessing pattern rather than extending it with request-derived text.
- Cache-key poisoning / unbounded memory: the two filtered reads are deliberately not @Cacheable. Verified independently — CacheConfiguration creates the 'vets' JCache with only setStatisticsEnabled(true), and no caffeine spec or maximumSize is configured in any application*.properties, so the cache genuinely has no eviction and no size bound. Admitting a caller-chosen key there would have been a reachable unbounded-allocation DoS on an open route; the ADR and the repository Javadoc record the reason.
- Boundary handling matches the neighboring implementation of the same concern: specialtyNamedBy() null/blank-checks and strips, exactly as OwnerController.processFindForm does for the lastName search parameter (OwnerController:98-103). No unjustified pattern divergence.
- Exposed surface: no new endpoint. Two existing GET routes gain one optional read-only query parameter, and docs/system-design.md Security Context was updated to name it. No management-endpoint exposure changed, no state mutated, no new dependency added (build.gradle is not in the change set).
- No credentials, tokens, connection strings, or other secrets appear in the diff (case-insensitive sweep for password/secret/token/api-key over the full change set returned no added lines). No logging was added, so no log-injection or secret-disclosure path.
- Error handling: no new exception is constructed or caught; nothing new can carry internal detail into the error page that already renders exception messages (REQ-SYS-002 known defect). @Transactional(readOnly = true) on both new reads keeps the query at least privilege.

**doc-reviewer**

- PRD REQ-VET-003 prose and Done-when bullets stay strictly behavioral: no code, class, or method names, no mechanism, non-goal narrowing (NG-9) recorded with a link-only ADR reference per the boundary rule
- Both 2026-09-06 ADRs follow the template, use em-dashes in References, and carry the required Non-goal/Requirements Implementation line
- docs/adr/README.md indexes both new ADRs with correct dates and titles
- system-design.md Contracts rows for Vet, Specialty, Vets, VetRepository, VetController correctly carry REQ-VET-003 and match the actual repository/controller/template code read during this review
- REQ-VET-002 stays absent from system-design.md and is correctly described as withdrawn-not-reused in both prd.md and the non-goal ADR
- the PRD's 'six further questions' count matches the actual unanswered bullets in Open Questions after the three new ones were added
- 'Specialty' terminology matches its ubiquitous-language.md definition throughout the changed docs
- all cross-reference links in the diff (system-design.md#contracts, #security-context, #open-questions-from-the-survey, prd.md#non-goals, prd.md#req-vet-003) resolve to real anchors/headings

**doc-reviewer**

- Threat Model gains a distinct 'Cross-site scripting through a reflected query parameter' row rather than overloading the existing rendered-user-data row, naming the veterinarian page links as the reflection point and matching src/main/resources/templates/vets/vetList.html:29-61, where every page link is a th:href link expression carrying specialty as a named parameter (@{/vets.html(page=...,specialty=${specialty})}) and none is string-concatenated, so the row's mitigation claim holds against the current template
- New row keeps the table's 3-column header and existing row shape, stays within sentence-length and prohibited-word standards, and needs no new ubiquitous-language entry (descriptive phrase, not a domain term)
- Fix is scoped entirely to docs/system-design.md; no other file in the fix-delta changed, so no cross-document reference needed updating
- Round-1 finding at line 20 is fully resolved: a reader of the Threat Model section alone now sees the specialty parameter reaching rendered HTML and the mitigation that covers it

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $4.94 | 16m 44s | 96% |
| `agent-team:system-design-expert` | 3 | opus-5 | $3.30 | 8m 14s | 92% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.62 | 4m 45s | 95% |
| `(parent)` | 1 | opus-5 | $1.37 | 39m 12s | 96% |
| `agent-team:change-grader` | 1 | opus-5 | $0.99 | 2m 45s | 91% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.82 | 3m 18s | 95% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.76 | 1m 44s | 90% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.39 | 1m 31s | 90% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.39 | 1m 37s | 86% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.69 | 13m 20s | 97% |
| `agent-team:system-design-expert` | opus-5 | $1.96 | 5m 20s | 94% |
| `agent-team:product-requirements-expert` | opus-5 | $1.62 | 4m 45s | 95% |
| `(parent)` | opus-5 | $1.37 | 39m 12s | 96% |
| `agent-team:change-grader` | opus-5 | $0.99 | 2m 45s | 91% |
| `agent-team:security-reviewer` | opus-5 | $0.76 | 1m 44s | 90% |
| `agent-team:system-design-expert` | opus-5 | $0.68 | 1m 17s | 86% |
| `agent-team:system-design-expert` | opus-5 | $0.66 | 1m 36s | 90% |
| `agent-team:feature-implementer` | opus-5 | $0.65 | 2m 1s | 92% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.65 | 2m 39s | 95% |
| `agent-team:feature-implementer` | opus-5 | $0.59 | 1m 23s | 91% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.39 | 1m 31s | 90% |
| `agent-team:test-reviewer` | sonnet-5 | $0.39 | 1m 37s | 86% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.17 | 38s | 90% |

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
