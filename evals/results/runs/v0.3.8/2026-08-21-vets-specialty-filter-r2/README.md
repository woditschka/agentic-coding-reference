# vets-specialty-filter r2 — v0.3.8

Filter the vet list by specialty (feature) · started 2026-08-21T16:04:08+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±1) | 4 (±0) | 4 (±0) | 5 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.81. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The narrowing rule lands in a package-private immutable record ( RequestedSpecialty ) plus two derived  findBySpecialtiesNameIgnoreCase  repository methods, so no new business rule enters  VetController  — the catalog's Web controller bar is met and the rule is unit-testable without the framework. Deductions:  Optional  as a method parameter in  findPaginated(int, Optional\<RequestedSpecialty>) , and the same null-test ternary repeated across five  vetList.html  links (justified in the ADR, still duplication). Tests are behavior-named and use factories, but  theVetDirectoryShouldHoldAVetWithSeveralSpecialtiesUnderEachOfThem  fuses act/assert with a narration comment,  "RaDiOlOgY" / "Leary" / isEqualTo(2)  are undeclared literals, and  aPaginationLinkTo  regex-matches raw markup and CSS classes — brittle. Docs are thorough: PRD NG-9, REQ-VET-003/004, three ADRs, threat-model and open-question rows, and the now-false Known Defect removed.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The blank/trim rule is lifted out of the controller into an immutable  RequestedSpecialty  record, so no new business rule lands in  VetController ; the repository gains two derived queries left uncached with a recorded reason. Structural roughness: the same null-test ternary is copied across five  vetList.html  links, and  findPaginated(int, Optional\<...>)  passes an Optional as a parameter. Tests are behavior-named ( theVetListShouldKeepTheSpecialtyInItsPaginationLinks ), add a true unit test, and cover blank, prefix, no-match, and an escaping case; but  ClinicServiceTests  narrates with  // Douglas holds both surgery and dentistry , skips phase separation, and asserts bare literals ("Leary", "Stevens"), while  aPaginationLinkTo 's regex over rendered HTML is fragile. Docs are thorough: NG-9 narrowed, REQ-VET-003/004 minted, contracts, threat model, and the withdrawn defect row all updated consistently.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 4

> Placement is right: the parsing rule lands in an immutable, package-private  RequestedSpecialty  record, the whole-name case-insensitive match becomes derived queries on  VetRepository  (uncached, with the key-space reason on the method), and  VetController  gains no rule beyond binding and delegation — matching the catalog's Value object/Repository/Web controller rows. Tests are behavior-named and use factories and named constants ( createRequestFor ,  givenTheVetsHolding ,  aPaginationLinkTo ), but  ClinicServiceTests  carries a narration comment ("// Douglas holds both surgery and dentistry"), bare literals "Leary"/"Stevens", and undeprived expectations ( isEqualTo(2) ). The five repeated null-test ternaries in  vetList.html  are load-bearing yet costly. Docs are near-complete;  prd.md 's "ten further questions stay open" survives while an eleventh is added.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $17.42 | 44m | 9 | 95% | 13 file(s) +578/−32 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.51 | 4m 16s | 93% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VETSSPECIALTYFILTER-001

0 review rounds · 0 build-passes · no grade yet

- • intake-decision (human)

---

### REQ-VET-003 — Veterinarian directory can be narrowed to one specialty

2 review rounds · 2 build-passes · **1 build-failure** · grade **CONCERN**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- • intake-decision (human)
- ◇ **prd-entry** Veterinarian directory can be narrowed to one specialty · (prd-expert) · ***◷ 5m***
- ◈ **design-block** **new** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 11m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L6 · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · audit-autofix · validate · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: `RequestedSpecialty.from` applies no length bound, so an arbitrarily long `specialty` value reaches a DB bind parameter on every request, and (by the uncached-narrowing ADR) each distinct value is an uncached query. Harm is bounded by the database and by a baseline that already has no rate limiting, so this is not a regression against the recorded posture - but a maximum-length guard in `RequestedSpecialty` would cap the amplification at the boundary where the rest of the contract already lives.
  - ▹ rec: Supply chain was not verified against the NVD in this review: `build.gradle` configures no OWASP Dependency-Check plugin (`dependencyCheckAnalyze` is unavailable), and the reviewer has no network access. The change set touches no build file, so the resolved surface is unchanged from the merge base (Spring Boot 4.1.0 via the BOM, `mavenCentral()` over TLS with the nohttp check active). Treat the CVE check as not run rather than clean, and close it in CI or by a human.
- ✔ **review doc** · **approved** · ***◷ 2m***
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 3m***
  - [autofix] `VetControllerTests.java:167-190` vetList.html renders five independently-conditioned pagination links (numbered, first, previous, next, last), each choosing between a plain and a specialty-carrying link expression on a null test - the design-block (line 10) calls this five-way repetition a named risk and claims 'the unnarrowed-URL assertion in VetControllerTests catches the regression.' Every existing test (narrowed and unnarrowed) requests page=1 against a 2-page result, so currentPage is never > 1: the 'previous' and 'first' links are never rendered as active \<a> elements in any test, narrowed or not. A regression that drops the specialty from just those two link forms (or breaks the unnarrowed case for them) would pass the full suite. The numbered/next/last links happen to coincide on the same href in the current fixtures ('page=2'), so the coverage looks broader than it is.
    - fix: Add a case that requests a narrowed and/or unnarrowed page 2 of a multi-page result (e.g. PageRequest.of(1, PAGE_SIZE) with totalPages >= 3) and asserts the 'previous'/'first' link hrefs carry (or omit) the specialty parameter, closing the gap the design-block's mitigation claims is already closed.
- ↻ **implement** (implementer) ← test · (1 finding) · ***◷ 4m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · audit-autofix · validate · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved** · ***◷ 1m***
- ◆ **grade CONCERN** · narrow the vet directory by specialty
  - blast_radius — **clear** — Thirteen files but one module: the whole production change is the vet feature package - a new RequestedSpecialty record, two derived repository methods, both VetController handlers - plus its own vetList.html. No sensitive paths, and six of the thirteen files are docs. The widest reach is the rewrite of all five pagination links in vetList.html, which touches every render of that page including unnarrowed ones, but it is confined to that single template.
  - semantic_surprise — **clear** — The hunks do what the description says, and the one non-obvious mechanism change is deliberate and pinned: all five pagination links move from Thymeleaf preprocessing to parameterized link expressions chosen on a null test, and tests assert the unnarrowed hrefs come out byte-identical, including page=1 for the first and previous forms at page 2 of 3. The strip-then-validate order in the record compact constructor is safe because the factory guards blank values before construction, and the new specialty model attribute shadows the table body loop variable of the same name only in a disjoint element scope, so it changes nothing today.
  - test_adequacy — **clear** — The tests exercise the changed behavior rather than restating it: ignore-case, prefix-no-match, multi-specialty and narrowed page counts run against real H2 in ClinicServiceTests, a derived-query semantic no mock could verify; RequestedSpecialtyTests covers null, empty and whitespace values plus the surrounding-space strip; and the MockMvc tests drive real Thymeleaf rendering, including an attribute-breakout payload and both narrowed and unnarrowed backward links at page 2 of 3. build_passed is true across build, test, check, checkFormat and checkstyleMain.
  - reviewer_hedging — **concern** — Three of four reviewers approved with no findings, but the security approval carries two standing recommendations: RequestedSpecialty applies no length bound, so an arbitrarily long caller value reaches a bind parameter on an uncached query on every request, with amplification bounded only by a baseline that already has no rate limiting; and the supply-chain CVE check was explicitly recorded as not run rather than clean, left for CI or a human to close. The test-reviewer also requested changes in round one on a real pagination-coverage gap, which the fix-delta closed before a clean re-approval.
  - scope_deviation — **clear** — The change tracks the three recorded owner decisions exactly: a URL contract only with no page control, NG-9 narrowed through a non-goal ADR, and REQ-VET-004 minted for the reinstated machine-readable surface with REQ-VET-002 left withdrawn. build_retries is 0 and consultations 0; the single design revision was bookkeeping over uncommitted doc paths plus a corrected Thymeleaf assumption about null link parameters, not a scope move, and the visible-control question was parked in Open Questions rather than built.
  - why — Code and tests read clean: the narrowing is contained to the vet package, unnarrowed URLs are pinned byte-for-byte, and matching semantics are proven against real H2. The residual is the security review's two open recommendations - no length bound on an uncached, caller-keyed query, and an unrun dependency CVE check. Decide both before merging.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- RequestedSpecialty is an immutable, equal-by-value record with the narrowing rule enforced in its compact constructor (Assert.hasText + strip()), matching the naming rule (domain noun, no suffix) and keeping the business rule out of VetController
- Both VetController handlers read the parameter through the same RequestedSpecialty.from(), so the two surfaces cannot drift, and findPaginated/findVets stay small, single-responsibility, side-effect-free query helpers using Optional.map/orElseGet instead of imperative branching
- VetRepository's two new derived queries follow the existing declarative style (Repository, not JpaRepository; explicit @Transactional(readOnly = true)) and are deliberately left off @Cacheable with javadoc pointing at the governing ADR, avoiding an unbounded cache keyed on caller text
- vetList.html builds every pagination link via parameterized link expressions (@{...}(page=...,specialty=...)), never Thymeleaf preprocessing, so no caller-supplied specialty reaches the expression parser; a template comment records why the null-test repeats across all five links, matching the ADR's documented trade-off
- ./gradlew checkFormat and checkstyleMain both pass clean on the changed sources

**security-reviewer**

- Injection into data access: the narrowing goes through the Spring Data derived query  findBySpecialtiesNameIgnoreCase(String[, Pageable])  on VetRepository. No JPQL/SQL text is composed from the request parameter anywhere in the change set; the whole-name, case-insensitive match is expressed by the method name, so the caller's text arrives only as a bind parameter.
- Cross-site scripting / template-expression injection: every vet pagination link in  src/main/resources/templates/vets/vetList.html  passes the specialty as a link-expression parameter ( @{/vets.html(page=...,specialty=${specialty})} ), never as preprocessed expression text. Thymeleaf URL-encodes the parameter and HTML-escapes the attribute, so caller text can neither reach the expression parser nor break out of the href. A grep for  __${  across  src/main/resources/templates/  finds no preprocessing on this page; the surviving instances in  owners/ownersList.html  take integers and template-supplied values only, and this slice adds none.  VetControllerTests.theVetListPaginationLinksShouldEscapeTheRequestedSpecialty  pins the escaping with an attribute-breakout payload. The divergence from the neighbouring owners-list pagination pattern is the safer direction and carries both an inline template comment and an ADR, satisfying the Pattern Consistency clause.
- Boundary validation is single-sourced:  RequestedSpecialty.from  is the one reader of the raw parameter for both surfaces, so the HTML and JSON routes cannot drift on what caller text means. Absent, empty, and whitespace-only all narrow nothing; surrounding space is stripped. The record is immutable and the controller holds no per-request mutable state, so the singleton bean stays thread-safe.
- Fail-secure error handling: the record's  Assert.hasText  message is a fixed literal and is unreachable from the controller (guarded by  from ), so no caller-supplied text can reach the error page that renders exception messages (system-design.md Known Defects). No new exception message carries request data.
- Cache key space: the narrowed lookups are deliberately left off  @Cacheable("vets") , keeping caller-supplied text out of the unbounded, unevicted  vets  cache. This is the correct call against the pre-existing unbounded-cache-growth threat row and is documented on the repository methods and in the ADR.
- No exposed-surface widening beyond the recorded baseline:  /vets  and  /vets.html  already existed and both remain read-only  GET s. No new endpoint, no management-endpoint change, no new dependency, no binder or mass-assignment surface, no file or resource path composed from request input, no shell execution, no deserialization entry point, no logging of request values, and no secret added anywhere in the diff.
- Threat model updated with the change: system-design.md gains a template-expression-injection row for the echoed specialty and extends the cache-growth row to record the narrowing's exclusion, so the durable security memory matches the code that shipped.

**doc-reviewer**

- REQ-VET-003 and REQ-VET-004 anchors, Done-when bullets, and edge cases stay behavioral with no mechanism or rationale leaking into prd.md
- NG-9 narrowing correctly cross-links its non-goal ADR and the Superseded entry for REQ-VET-002 is updated coherently with REQ-VET-004's reinstatement
- system-design.md Contracts rows for Vet, Specialty, RequestedSpecialty, Vets, VetRepository, and VetController all carry REQ-VET-003/REQ-VET-004 and stay at purpose-plus-source-pointer abstraction with no field/parameter tables
- The stale Known Defects row for the unconsumed machine-readable route was removed now that REQ-VET-004 supersedes it, and no dangling REQ-VET-002 reference remains in system-design.md
- All three new ADRs follow the template (Status, Context, Options Considered, Decision, Consequences, Implementation with Requirements:/Non-goal:), and the non-goal ADR's filename carries the required non-goal- infix
- Every new cross-reference (prd.md\<->system-design.md\<->adr/) and the three adr/README.md index rows resolve to existing anchors and files; the pagination-links ADR's description of the five null-tested link expressions matches the shipped vetList.html exactly
- Threat Model gained a coherent new row for template expression injection, backed by the pagination-links ADR, and the vet-cache open question was updated to name the key-space concern the uncached-narrowing ADR addresses

**test-reviewer**

- RequestedSpecialtyTests: real value-object unit tests, no mocks, @NullSource/@ValueSource parameterized test covers the blank/whitespace edge case from prd.md with real factory methods (readFromRequest/createRequestFor), BDD the{Subject}Should{Outcome} naming throughout, and a genuine equals/hashCode contract test
- VetControllerTests additions follow the host file's existing MockMvc + @MockitoBean convention (the project's one sanctioned mock plus a tolerated pre-existing Mockito stub), stay four-phase, and add theVetListPaginationLinksShouldEscapeTheRequestedSpecialty - a real regression test for the expression-injection risk the design-block flags, driving the actual Thymeleaf rendering rather than asserting an interaction
- Ignore-case and prefix-no-match criteria are tested as real-H2 repository behavior in ClinicServiceTests (theVetDirectoryShouldMatchTheSpecialtyNameIgnoringCase, theVetDirectoryShouldMatchNoVetWhenTheSpecialtyNameIsOnlyAPrefix, theVetDirectoryShouldHoldAVetWithSeveralSpecialtiesUnderEachOfThem, aPageOfTheNarrowedVetDirectoryShouldCountOnlyVetsWithThatSpecialty) exactly as the governing design-block (line 10) blesses, exercising the derived-query matching semantics no mock could verify, including that pagination counts are narrowed too
- ./gradlew test is green (BUILD SUCCESSFUL) and jacoco reports 100% instruction and branch coverage on RequestedSpecialty, VetController, and Vets - the coverage target (docs/testing-principles.md Coverage, 80% domain/core) is comfortably met
- All eight prd-entry.test_names acceptance behaviors for REQ-VET-003/REQ-VET-004 are exercised, either under their original names or the two blessed relocations, plus edge cases 2-4 from prd.md's edge-case table (multi-specialty vet, whitespace matching, unpaged JSON form)

**test-reviewer**

- The fix-delta adds theVetListShouldKeepTheSpecialtyInItsBackwardPaginationLinks and theVetListBackwardPaginationLinksShouldCarryNoSpecialtyWhenNoneWasRequested, both requesting page 2 of a 3-page result (VETS_FILLING_THREE_PAGES = 2*PAGE_SIZE+1), closing the exact gap from round 1: the 'previous'/'first' links are now exercised at currentPage > 1 in both the narrowed and unnarrowed cases, where they render as active \<a> elements instead of the disabled \<span> fallback.
- The new aPaginationLinkTo(href, iconClass) helper disambiguates the five link forms by their fa-* icon class since their hrefs otherwise coincide (page=1) in this fixture - a real gap the round-1 finding also named ('the numbered/next/last links happen to coincide on the same href') - and its javadoc explains why the icon class, not the href alone, is the discriminator.
- Verified against src/main/resources/templates/vets/vetList.html: the 'first' and 'previous' anchors both compute page=1 when currentPage=2 in a 3-page result, so the new tests' expected hrefs are derived from the real template logic, not invented data, and a regression dropping the specialty from just these two link forms would now fail one of the new tests.
- Both new tests keep four-phase structure (arrange: Page/given/href-variable stanza, blank line, act+assert: chained mockMvc.andExpect calls), reuse existing helpers/constants (RADIOLOGY, helen(), james(), PAGE_SIZE) and the host file's given(...)/MockMvc idiom, and follow the BDD the{Subject}Should{Outcome} naming already used throughout the file.
- ./gradlew test --tests VetControllerTests is green; swept the changed file for further instances of the disambiguation-gap class and found none beyond the two new tests - no remaining pagination-link form is asserted only through a coincidental-href, ambiguous match.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $5.72 | 18m 58s | 97% |
| `agent-team:system-design-expert` | 2 | opus-5 | $3.83 | 9m 55s | 95% |
| `(parent)` | 1 | opus-5 | $2.19 | 48m 32s | 97% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $2.17 | 5m 37s | 96% |
| `agent-team:change-grader` | 1 | opus-5 | $1.51 | 4m 16s | 93% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.82 | 4m 47s | 93% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.76 | 1m 47s | 92% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.62 | 3m 7s | 92% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.40 | 1m 18s | 90% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.83 | 12m 35s | 97% |
| `(parent)` | opus-5 | $2.19 | 48m 32s | 97% |
| `agent-team:product-requirements-expert` | opus-5 | $2.17 | 5m 37s | 96% |
| `agent-team:system-design-expert` | opus-5 | $1.98 | 4m 2s | 96% |
| `agent-team:system-design-expert` | opus-5 | $1.86 | 5m 52s | 94% |
| `agent-team:change-grader` | opus-5 | $1.51 | 4m 16s | 93% |
| `agent-team:feature-implementer` | opus-5 | $1.16 | 4m 42s | 96% |
| `agent-team:security-reviewer` | opus-5 | $0.76 | 1m 47s | 92% |
| `agent-team:feature-implementer` | opus-5 | $0.72 | 1m 41s | 91% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.62 | 3m 7s | 92% |
| `agent-team:test-reviewer` | sonnet-5 | $0.52 | 3m 21s | 93% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.40 | 1m 18s | 90% |
| `agent-team:test-reviewer` | sonnet-5 | $0.30 | 1m 26s | 93% |

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
