# vets-specialty-filter r1 — v0.2.4

Filter the vet list by specialty (feature) · started 2026-08-10T23:59:38+00:00 · exec `claude-dev` · status **complete**

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

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.71. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in the repository as derived finders ( findBySpecialtiesNameIgnoreCase ), leaving VetController binding-and-delegating, and both surfaces share one  requestedSpecialty  normalizer — right layer, no duplicated rule. Structural cost: vetList.html repeats the same  ${filtered} ? ... : ...  ternary across five links, copy-paste variance a reviewer would flag, and blank-to-null normalization stays a private controller rule untestable without the framework, widening the pyramid gap. Tests are BDD-named, phase-structured, and use collection assertions, but ClinicServiceTests leans on bare seed literals ( "surgery" ,  "Douglas" ,  "Ortega" ) as mystery values and carries narration comments ("Douglas holds both surgery and dentistry..."). Documentation is thorough: NG-9 narrowed, REQ-VET-003/004 minted, REQ-VET-002 left withdrawn, contracts rows, the obsolete known-defect row removed, three ADRs indexed.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in the repository as derived finders ( findBySpecialtiesNameIgnoreCase , both overloads) with the cache decision reasoned in an ADR, so the controller stays thin; the blank-to-null normalization in  VetController.requestedSpecialty  is a small new rule sitting in a controller the catalog says holds none. The template repeats the same  ${filtered} ? ... : ...  ternary across five links — a change to one link's shape can miss the others. Tests are behavior-named, phase-separated, reuse  helen() , and name  HELENS_SPECIALTY / SPECIALTY_NOBODY_HOLDS , but narrate ( // Douglas holds both surgery and dentistry... ), keep bare literals ( "surgery" ,  "dentistry" ,  specialty=radiology  in the URL assertion), and widen mock-framework stubbing. Docs move everywhere the change touches: NG-9 narrowed, REQ-VET-003/004 minted, the withdrawn-route defect row removed, vocabulary and contracts updated.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The filter lands in the right seams: derived finders on VetRepository, the controller only binding and delegating, and ADRs justifying the uncached finders and query-level case folding. Two dings. The blank-parameter rule sits in VetController.requestedSpecialty and is only exercised through MockMvc, widening the pyramid gap the testing principles ask a reviewer to check. vetList.html repeats the same  ${filtered} ? ... : ...  ternary in five links, though Thymeleaf already omits a null  specialty  from  @{/vets.html(page=...,specialty=${specialty})}  — avoidable duplication. Tests are behavior-named and reuse the helen() factory, but ClinicServiceTests asserts on bare seed literals ("surgery", "Douglas", "Ortega") and adds narrating comments. Documentation is complete: NG-9 narrowed, REQ-VET-003/004 minted, the withdrawn defect row removed, vocabulary extended.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $16.47 | 46m | 35 | 90% | 12 file(s) +391/−32 |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Filter the veterinarian directory by specialty

2 review rounds · 2 build-passes · **1 build-failure** · no grade yet

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | ✎ (1) |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | **✔** | **✔** |

- ◇ **prd-entry** Filter the veterinarian directory by specialty · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **new** · (design) · ***◷ 6m***
- ◆ **implement** (implementer) · ***◷ 8m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 2m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 42s***
- ✔ **review security** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `VetControllerTests.java:theVetDirector` No test pins that pagination links omit the `specialty` query parameter entirely when the directory is unfiltered (REQ-VET-003 'no parameter → unchanged behavior'). The controller always sets the `specialty` model attribute (null when absent/blank via `requestedSpecialty()`), and the template builds every pagination href from it (`vetList.html` th:href="@{/vets.html(page=...,specialty=${specialty})}"). Thymeleaf omits a null-valued URL parameter, so the unfiltered case is presumed correct but never asserted — only the filtered case (theVetDirectoryPaginationLinksShouldCarryTheRequestedSpecialty) checks href content; the pre-existing showVetListHtml test asserts only status/attributeExists/view name, not href text. A multi-page unfiltered scenario (mirror the filtered test's PageImpl/PageRequest setup with vets.findAll(any(Pageable.class))) asserting the rendered hrefs are exactly "/vets.html?page=1" / "/vets.html?page=3" (no trailing "&amp;specialty") would close the gap and pin the not(containsString("specialty=")) guarantee this behavior depends on.
    - fix: Add theVetDirectoryPaginationLinksShouldNotCarrySpecialtyWhenUnfiltered (or extend showVetListHtml) to a multi-page unfiltered scenario asserting rendered pagination hrefs contain no `specialty=` parameter.
  - [autofix] `ClinicServiceTests.java:theVetDirector` This test runs two independent Act+Assert pairs (one query for "surgery", one for "dentistry") in a single test body with no blank-line phase separation, splitting the four-phase structure (testing-principles.md § Four-Phase Test Structure) across two unrelated actions instead of one. It reads as two tests merged for convenience.
    - fix: Split into two tests, e.g. theVetDirectoryShouldListDouglasOnceUnderSurgery and theVetDirectoryShouldListDouglasUnderDentistry, each with its own single Act/Assert.
- ✔ **review doc** · **approved** · ***◷ 2m***
- ↻ **implement** (implementer) ← test · (2 findings) · ***◷ 9m***
  - ↳ consult → **prd-expert** · Does acceptance criterion 7 -- 'without the specialty parameter, /vets.html and /vets behave exactly as they do today, including paging' -- cover the shape of the rendered pagination URL, or only the resulting page content? If it covers the URL, this is a defect and the fix is a one-line-per-link template change in src/main/resources/templates/vets/vetList.html (already inside prd-entry file_targets) so a blank or null specialty is omitted from the link; note that changing production code invalidates the three existing approvals and needs a re-review pass. If it covers only content, the empty specialty= parameter is acceptable and I will re-point the new test at the actual behaviour and record the URL change as intended.
  - ↲ consult ← **prd-expert** · Criterion 7 covers the rendered pagination URL. The empty specialty= parameter on the unfiltered page is a defect against REQ-VET-003; change the template so a blank or absent specialty is omitted from every page link. Do not re-point the new test at the current behavior — keep it red until the template is fixed. Three grounds, each independently sufficient. 1. Criterion 3 bounds the authorization. It reads 'every pagination link on the FILTERED /vets.html page carries the specialty parameter'. The owner's decision behind it — 'pagination links carry the parameter so filtered pages stay navigable' — states the purpose and the limit in the same sentence. The mandate to touch the links extends to the filtered page and no further. An empty parameter on an unfiltered page serves no navigability need, so nothing authorizes it. 2. Criterion 7 is a regression clamp, not a content clamp. 'Behave exactly as they do today, including paging' is the broadest wording available and takes the whole observable boundary of the two endpoints. The href the directory hands the reader is the paging behavior — following it is the paging action. Reading 'behave' as 'the response body's list of veterinarians' would let the slice change status codes, headers, and links freely, which is plainly not what the owner asked for when they said 'exactly as they do today'. Narrowing here would widen the slice's licence, not narrow it. 3. The design agrees. The design-block at line 8 asserts twice, as fact, that the parameter syntax 'omits it when null' (integration_points entry 4, risks entry 2). The intended behavior at every level of the record — requirement, owner decision, design — is omission on the unfiltered page. The implementer verified the mechanism does not deliver it. That is a mechanism failing a stated intent, which is the definition of a defect, not a rediscovered requirement. On the argument that the URL is mechanism and therefore outside the PRD: the PRD does not specify the query-string shape, and it should not. It specifies that the unfiltered directory behaves as before. The URL shape is the mechanism by which that requirement is met or broken, exactly as a status code is. system-design.md#contracts carries both endpoints as boundary surface. On the content argument the request raises: correct that content is unaffected, and that a bookmarked /vets.html?page=1&specialty= would render the same list, since criterion 6 makes an empty value equivalent to an absent one. That is why this is a low-severity defect and not a broken page. It is still a defect: the unfiltered directory emits into address bars, bookmarks, and history a URL naming a filter the reader never asked for. Cost, since it falls on the implementer: the fix is in vetList.html, already in file_targets, and invalidates the three approvals. That is the correct price. A production change always re-enters review — do not weigh the re-review against the requirement. PRD clarification applied so the test has a spec anchor: docs/prd.md gains one Done-when bullet under REQ-VET-003 — 'given no specialty at all, when the directory offers a link to another page, then that link asks for no specialty, as before.' It makes criterion 7's existing meaning explicit and adds no scope; no Non-Goals row is touched and no superseding prd-entry is needed. Resume: fix the template, keep theVetDirectoryPaginationLinksShouldCarryNoSpecialtyWhenTheDirectoryIsUnfiltered asserting hrefs with no specialty= parameter, re-run the full gate, append build-pass and the review-plan.
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 52s***
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [autofix] `vetList.html:32,38,44,50,56` The unfiltered/filtered branch is now a full ternary duplicated five times, once per pagination link (`${filtered} ? @{/vets.html(page=...,specialty=${specialty})} : @{/vets.html(page=...)}`). Each line restates both URL shapes, so the five links must be read and compared expression-by-expression to confirm they agree; a future change to the URL shape (a new query param, a path change) has to be applied identically in ten places instead of one, and a single missed branch would silently regress the same bug this fix pass corrected. The pre-existing template already repeated the plain `@{...}` expression five times, so the duplication itself is not new, but this change doubles the expression each line carries.
    - fix: Hoist each link's href into a named `th:with` variable on the outer `\<div>` (e.g. `hrefFirst`, `hrefPrev`, `hrefNext`, `hrefLast`, and a per-iteration expression for the numbered links), computed once each with the `${filtered} ? ... : ...` ternary, so the five branching decisions sit together near `filtered` and each `\<a th:href="...">` reduces to referencing the precomputed value. This keeps the fix template-only (no controller change) while separating the branching logic from the repeated markup.
- ✔ **review security** · **approved** · ***◷ 39s***

---

### REQ-VET-001

0 review rounds · 0 build-passes · no grade yet

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- requestedSpecialty is the single private helper both VetController handlers call for blank/whitespace normalization, matching the design constraint
- VetRepository Javadoc explains why the filtered finders are deliberately uncached (unbounded cache-key growth from a request parameter), not just what the code does
- Filtered finders mirror the existing findAll()/findAll(Pageable) overload shape and use the derived-query IgnoreCase keyword, keeping case folding in the query rather than the column
- Thymeleaf pagination links use @{/vets.html(page=...,specialty=...)} parameter syntax consistently across all five link types
- checkFormat passes; methods stay short and single-responsibility; no dead code or leftover debug output

**security-reviewer**

- Injection into data access: the specialty value reaches the database only through Spring Data derived finders (findBySpecialtiesNameIgnoreCase, both overloads in VetRepository). No JPQL or SQL text is composed, so the value is always a bound parameter. Matches the control in security-principles.md and the SQL-injection row of the threat model.
- Reflected XSS in vetList.html: all five pagination links were rewritten from the string-preprocessing form @{'/vets.html?page=__${i}__'} to the parameterized link form @{/vets.html(page=...,specialty=${specialty})}. Thymeleaf URL-encodes link-expression query parameter values and th:href escapes the attribute output, so a payload such as specialty=">\<script>alert(1)\</script> is emitted percent-encoded inside a quoted attribute and cannot break out. The change strictly improves on the preprocessing form it replaced. Swept the whole templates/ tree: no th:utext and no remaining __${...}__ preprocessing anywhere, so no second instance of this class exists.
- Reflected value on the error path: a specialty that surfaced in an exception message would render through error.html's th:text="${message}", which escapes. No unescaped sink for the value exists on any surface.
- No allowlist and no length cap is defensible here. The value is never a cache key (see below), never composes a filesystem or classpath path, never reaches a log line or a URL the server fetches, and reaches the database as a bound parameter compared against a three-row lookup table. The residual concern is resource consumption, which is outside the reviewable class set and is not a weakening of the recorded baseline.
- Cache-key growth: the ADR at docs/adr/2026-08-11-specialty-filtered-vet-reads-uncached.md holds under inspection. @Cacheable("vets") appears only on the two unfiltered reads; both new caller-parameterized finders are unannotated, so an unauthenticated caller cannot mint entries in the unbounded vets cache. The decision is the correct one given CacheConfiguration declares no size limit or eviction.
- Boundary normalization is at the HTTP edge and shared: requestedSpecialty() strips and maps empty to null once, and both surfaces call it, so the HTML page and the JSON route cannot diverge in what they match or in when the filter is considered absent.
- Exposed surface: no new route. Both handlers are the existing /vets.html and /vets mappings gaining an optional read-only query parameter. The JSON response body is the same Vets projection as before, filtered — no field or entity becomes newly reachable, so there is no new data exposure.
- No secrets in the diff: swept the change set for credential-shaped material (token, password, secret, key, and the datasource property names). The only key-like hits are Java identifiers and ADR prose. No property file, no build file, and no configuration was touched.
- Supply chain: build.gradle, settings.gradle, and gradle/ are unchanged in the change set, so no dependency was added, upgraded, or repointed and no new CVE surface is introduced by this slice. No dependencyCheck task is configured in this project; the check reduces to the unchanged dependency declarations.

**test-reviewer**

- Test count matches the implementer's report: 4 new ClinicServiceTests (real H2 database via @DataJpaTest) + 9 new VetControllerTests (MockMvc) = 13
- Whole-name case-insensitive match and prefix-must-not-match are both pinned at the repository layer with real seeded fixture data (Douglas/Ortega, surgery/dentistry from data.sql), not invented data
- Multi-specialty vet listed once under each specialty is explicitly pinned (containsOnlyOnce) against the real join, guarding the stated join-duplication risk
- No-match → empty list with HTTP 200 (not a failure) is covered on both the HTML and JSON surfaces
- Empty/whitespace specialty treated as absent, and no-parameter unchanged behavior, are covered on both surfaces
- Filtered pagination correctly carries the specialty across page links, verified by both positive (containsString) and negative (not(containsString(...page=1\"))) assertions
- New tests use AssertJ fluent assertions, BDD the{Subject}Should{Outcome} naming, and Tier-1 named constants/locals (HELENS_SPECIALTY, SPECIALTY_NOBODY_HOLDS, surgeryInMixedCase, prefixOfSurgery, pageSize, vetsHoldingTheSpecialty) with no mystery literals
- VetRepository's two new query-derived methods are both exercised (Collection and Page overloads)
- ./gradlew test passes for both changed test classes

**doc-reviewer**

- REQ-VET-002 stays withdrawn with its id not reused; Superseded entry correctly points to REQ-VET-004 as a fresh requirement, not a reinstatement
- NG-9 narrowed in place following the NG-4/NG-5 precedent, with matching non-goal ADR (non-goal- filename infix, Non-goal: NG-9 implementation line)
- PRD stays behavioral throughout REQ-VET-003/REQ-VET-004 prose and Done when bullets; no mechanism, code symbol, or rationale prose leaked in (case-folding and cache-scope mechanism correctly deferred to system-design.md and its two new ADRs)
- system-design.md Contracts table and Known Defects row updated consistently: REQ-VET-002 fully absent, REQ-VET-003/REQ-VET-004 correctly attributed per type, the closed machine-readable-route defect row removed
- Cross-references all resolve: PRD ADR/Design links, ADR back-links to prd.md#non-goals/#req-vet-003 and system-design.md#persistence/#contracts/#known-defects/#open-questions-from-the-survey
- docs/ubiquitous-language.md gains Veterinarian directory and Specialty filter with provenance-dated entries; filter vs. search vocabulary used consistently across prd.md, the ADRs, and the Non-Goals table
- docs/adr/README.md index row order and links correct for all three new ADRs; ADR structure and em-dash reference style match existing precedent (2026-07-31 and 2026-08-08 ADRs)
- Three open questions recorded rather than escalated, consistent with the note that no further product answer would come, and each is consistent with the corresponding Done when / edge-case content

**test-reviewer**

- Finding 1 resolved: theVetDirectoryPaginationLinksShouldCarryNoSpecialtyWhenTheDirectoryIsUnfiltered pins the unfiltered pagination hrefs with not(containsString("specialty=")); the test setup (page 2 of 3) exercises all five link branches (numbered, first, previous, next, last), matching the sibling filtered-pagination test's coverage shape for the new filtered ternary in vetList.html
- Finding 2 resolved: the two-Act ClinicServiceTests test is split into theVetDirectoryShouldListAVetHoldingSeveralSpecialtiesOnlyOnceUnderSurgery and ...UnderDentistryToo, each single-assertion and four-phase
- New test follows the host file's conventions: Tier-1 named pageSize/vetsInTheDirectory locals mirror the adjacent filtered test, AssertJ/Hamcrest matcher style unchanged, comment explains why (multi-page setup) not what
- ./gradlew test green, 15 tests total (5 ClinicServiceTests, 10 VetControllerTests), no regressions

**doc-reviewer**

- The new REQ-VET-003 Done-when bullet reads as a clarification of existing acceptance criterion 7, not new scope: it uses purely behavioral language (no mechanism, no code element), stays under the 30-word sentence standard, and is consistent with criteria 3 and 7 and with the Open Questions section
- No durable document (docs/system-design.md, the three new ADRs, docs/adr/README.md) carries the false Thymeleaf 'omits the parameter when null' claim; it appears only in the append-only design-block handoff records (lines 4 and 8), not in any document a future reader relies on
- NG-9 narrowing is coherent across docs/prd.md Non-Goals table, docs/prd.md Open Questions, and the non-goal ADR
- docs/adr/README.md index carries rows for all three new 2026-08-11 ADRs
- docs/system-design.md Contracts table correctly cites REQ-VET-003 and REQ-VET-004 on Vet, Specialty, Vets, VetRepository, VetController, and Persistence section links both new ADRs
- docs/ubiquitous-language.md carries a coherent Specialty filter entry consistent with the PRD usage

**code-quality-reviewer**

- th:with="filtered=${specialty != null}" correctly hoists the branch condition once instead of repeating the null-check inline five times
- The fix is confined to the template, matching the PRD-ruled defect's scope and file_targets
- Comment above the div explains why the branch exists, giving cold-read context for the non-obvious null-parameter behavior
- Both branches are pinned by tests (theVetDirectoryPaginationLinksShouldCarryTheRequestedSpecialty, theVetDirectoryPaginationLinksShouldCarryNoSpecialtyWhenTheDirectoryIsUnfiltered)
- checkFormat and checkstyleMain/checkstyleTest pass clean on the fix delta

**security-reviewer**

- Implementer's claim verified against src/main/resources/templates/vets/vetList.html: all five pagination links choose between two whole link expressions with a ternary on the boolean  filtered ; the attacker-controlled value never leaves the (specialty=${specialty}) parameter slot of an @{...} expression. No raw concatenation, no string-built href, so Thymeleaf still owns both URL-encoding of the query parameter value and HTML-attribute escaping of the rendered attribute. The reflected-value surface the prior pass flagged for examination is clean; no reflected XSS.
- The  filtered  guard reads the same normalized value the query and the links use: VetController.requestedSpecialty (VetController.java:90-96) folds absent, empty, and whitespace-only to null before the model attribute is set, so the parameter-presence branch cannot diverge from the filter-applied branch. An unfiltered page emits no specialty= at all; a blank-only request is indistinguishable from an absent one on both surfaces.
- Class sweep over the reflected-output class across src/main/resources/templates/: no th:utext and no [(...)] unescaped inlining anywhere in the template tree, and  specialty  is reflected nowhere in vetList.html outside the five link expressions. The one instance examined was the only instance.
- Injection surface unchanged and safe: VetRepository.findBySpecialtiesNameIgnoreCase is a Spring Data derived query (VetRepository.java:71,83), so the specialty is bound as a JPA parameter, never concatenated into JPQL or SQL. The absence of an allowlist and of a length cap on the unauthenticated parameter remains acceptable at this trust boundary — the value reaches only a parameterized query and a URL-encoded link parameter, and unbounded length is a resource-consumption concern outside this review's severity bar, consistent with the prior pass's assessment.
- Filtered finders remain uncached, matching docs/adr/2026-08-11-specialty-filtered-vet-reads-uncached.md: neither findBySpecialtiesNameIgnoreCase overload carries @Cacheable, and the Javadoc records the security ground (a request-derived cache key in a size-unlimited cache). The unbounded-cache-entry-minting path stays closed.
- No secrets in the fix delta: the four changed files carry no credential-shaped literal under any naming (token, password, secret, key or otherwise); the only added constants are the test's page size and vet count.
- No dependency, build, or configuration change in the delta, so the supply-chain surface cleared by the prior pass is unmoved.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 4 | opus-5 | $7.78 | 19m 13s | 93% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $5.08 | 8m 55s | 93% |
| `agent-team:system-design-expert` | 2 | opus-5 | $5.03 | 8m 50s | 93% |
| `(parent)` | 1 | opus-5 | $4.77 | 45m 52s | 96% |
| `agent-team:security-reviewer` | 2 | opus-5 | $2.20 | 2m 32s | 81% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.97 | 3m 25s | 84% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.39 | 3m 50s | 86% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $1.18 | 2m 21s | 77% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.13 | 9s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $4.77 | 45m 52s | 96% |
| `agent-team:product-requirements-expert` | opus-5 | $3.93 | 6m 48s | 94% |
| `agent-team:system-design-expert` | opus-5 | $3.75 | 7m 11s | 94% |
| `agent-team:feature-implementer` | opus-5 | $3.58 | 8m 54s | 94% |
| `agent-team:feature-implementer` | opus-5 | $1.59 | 4m 1s | 92% |
| `agent-team:feature-implementer` | opus-5 | $1.58 | 3m 41s | 92% |
| `agent-team:system-design-expert` | opus-5 | $1.28 | 1m 39s | 87% |
| `agent-team:security-reviewer` | opus-5 | $1.23 | 1m 30s | 82% |
| `agent-team:doc-reviewer` | sonnet-5 | $1.18 | 2m 26s | 82% |
| `agent-team:product-requirements-expert` | opus-5 | $1.15 | 2m 7s | 89% |
| `agent-team:feature-implementer` | opus-5 | $1.03 | 2m 36s | 94% |
| `agent-team:security-reviewer` | opus-5 | $0.97 | 1m 1s | 79% |
| `agent-team:test-reviewer` | sonnet-5 | $0.91 | 2m 44s | 88% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.79 | 58s | 86% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.61 | 50s | 75% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.58 | 1m 31s | 79% |
| `agent-team:test-reviewer` | sonnet-5 | $0.48 | 1m 5s | 79% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.13 | 9s | 0% |

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
- task fingerprint `064d588523591361` · `2.1.226 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
