# vets-specialty-filter r2 — v0.2.3

Filter the vet list by specialty (feature) · started 2026-08-30T18:21:25+00:00 · exec `claude-dev` · status **complete**

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

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.65. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in the repository as derived queries ( findDistinctBySpecialtiesNameIgnoreCase , both overloads) with the cache-exclusion rationale documented, so the controller only binds and delegates; the shared  namesASpecialty  guard keeps both routes from drifting, though blank-means-absent is still a rule sitting in the web layer. Tests are behavior-named per the BDD school, use named constants over literals, and cover case-insensitivity, prefix non-match, empty result, paging, and link propagation; small lapses remain — the bare  12 / PageRequest.of(0, 5)  in  theVetDirectoryShouldKeepTheSpecialtyOnPagingLinks  are mystery values, and  theVetDirectoryShouldListEverySpecialtyOfAVetMatchedByOne  mixes two concerns. The template repeats the same  specialty == null  ternary five times — verbose, though it preserves existing URLs. Documentation is complete: ADR, PRD non-goal narrowing, REQ-VET-003, superseded entry, contracts table, and the removed known-defect row.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Derived-query overloads on VetRepository keep persistence in the repository, and the uncached-by-design javadoc reasons about the unbounded cache — a good seam. But  namesASpecialty  puts a fresh rule (blank means absent) inside VetController, exactly what the catalog's Web controller row and the pyramid section flag; it stays framework-bound rather than moving to an independently testable unit. Tests are behavior-named and use meaningful constants;  theVetDirectoryShouldPassTheSpecialtyToTheRepositoryUnstripped  names the collaborator rather than the behavior and asserts only the stub's own empty return. The five-fold  ${specialty == null} ? ... : ...  ternary in vetList.html is repetition a reviewer would flag. Docs are the strongest part: ADR, narrowed NG-9, REQ-VET-003 with REQ-VET-002 left withdrawn, stale defect row and cache open question both corrected.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Fits the existing seam: derived-query overloads on VetRepository (findDistinctBySpecialtiesNameIgnoreCase) keep the query in the persistence gateway, and the controller only binds and delegates; the deliberate non-caching is justified in Javadoc. The blank-value rule (namesASpecialty) is a small rule added in a controller, which the catalog's Web controller row disallows for new rules, and the vetList.html ternary is repeated five times — real duplication a reviewer would flag. Tests are behavior-named, phase-separated, and free of mystery values (SPECIALTY_HELD_BY_TWO_VETS, SURNAMES_OF_THOSE_TWO_VETS), but new Mockito stubs are added rather than a real/hand-written double, and theVetDirectoryShouldListEverySpecialtyOfAVetMatchedByOne mixes two concerns. Documentation is comprehensive: ADR, README index, NG-9 narrowing, REQ-VET-003, superseded list, known-defect row removed, open questions and contracts updated.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $13.49 | 33m | 4 | 93% | 9 file(s) +330/−34 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.27 | 3m 33s | 90% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Reader narrows the veterinarian directory to one specialty

2 review rounds · 2 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (3) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (1) | **✔** |

- ◇ **prd-entry** Reader narrows the veterinarian directory to one specialty · (prd-expert) · ***◷ 3m***
- ◇ **prd-entry** Reader narrows the veterinarian directory to one specialty · (prd-expert)
- ◈ **design-block** **minor** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 9m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **minor** · (design) · supersedes L5 · ***◷ 52s***
- ◆ **implement** (implementer) · ***◷ 59s***
  - ▲ **build ✓ clean** · build · test · checkFormat · checkstyleMain · handoff-validate · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 30s***
- ✔ **review security** · **approved** · ***◷ 55s***
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 1m***
  - **[blocked]** `system-design.md:103,218` VetRepository's Contracts row (line 103) still says 'results are cached' as a blanket claim, and Open Questions item 5 (line 218) still says 'the vet repository's read methods are cached with no eviction configured' as if this held for all of them. Since this slice, VetRepository has four read methods: the original findAll()/findAll(Pageable) pair stays @Cacheable("vets"), but the two new findDistinctBySpecialtiesNameIgnoreCase overloads are deliberately uncached (see VetRepository.java, and design-block at handoff.jsonl line 9's first risk/mitigation) precisely to avoid the unbounded-cache-growth risk Open Questions item 5 raises. A reader trusting either line concludes every vet query is cached, missing that the mitigation for the unbounded-growth risk is 'not cached' for the narrowed queries. Both lines need to distinguish the cached unfiltered pair from the deliberately uncached filtered pair.
- ✎ **review test** · **changes_requested** · (3 findings) · ***◷ 1m***
  - [autofix] `ClinicServiceTests.java:219-255` Edge case 2 ("a veterinarian holding several specialties appears under each of them") is untested for the narrowed query. Seeded vet Douglas (id 3) holds both surgery and dentistry, which is exactly the multi-specialty case the design block flagged as depending on Vet.specialties being FetchType.EAGER plus the Distinct keyword. None of the six new ClinicServiceTests methods filter by surgery or dentistry, and none assert on getSpecialties() of a matched vet -- only getLastName() is checked. A narrowing query could silently truncate a matched vet's specialty list (e.g. if a future refactor swapped the eager join for a projection) and no test would catch it.
    - fix: Add theVetDirectoryShouldListEverySpecialtyOfAVetMatchedByOne(): call findDistinctBySpecialtiesNameIgnoreCase("surgery"), assert it contains Douglas and Ortega, and assert Douglas's getSpecialties() still contains both surgery and dentistry (extracting(Specialty::getName).containsExactlyInAnyOrder(...)) -- proving narrowing does not prune the returned vet's own specialty list.
  - [autofix] `VetControllerTests.java:107-165` Three-Tier Data Naming (testing-principles.md § Three-Tier Data Naming Convention, which carries no grandfather clause for tests written from 2026-07-31 onward, unlike § Test Naming and § Factory Methods) is violated by every new test in both files. "radiology" is a Tier 1 meaningful value -- it directly determines the expected outcome (Leary/Stevens vs. empty) -- yet it appears as a bare string literal 12+ times across the two files with no role-describing name. Same for the expected vet surnames "Leary"/"Stevens" in the new ClinicServiceTests assertions.
    - fix: Add a SEEDED_SPECIALTY = "radiology" (or similarly named) constant at class level in both ClinicServiceTests and VetControllerTests and reference it from every new test instead of the repeated literal; likewise name the expected-surname pair used in containsExactlyInAnyOrder.
  - [clarify] `VetControllerTests.java:159-173` The "unheld specialty yields HTTP 200 with an empty list" acceptance bullet is exercised at the controller layer only incidentally: theVetDirectoryShouldPassTheSpecialtyToTheRepositoryUnstripped (html route) asserts status 200 and hasSize(0), but its stated purpose is proving the unstripped-value contract, not the unheld-specialty bullet, and there is no equivalent case for the JSON route (/vets). Confirm whether an explicit, purpose-named test for this bullet on both routes is required, or whether the incidental html coverage plus the ClinicServiceTests empty-result assertion (theVetDirectoryShouldListNoVetWhenNoVetHoldsTheNamedSpecialty) is accepted as sufficient.
- ↻ **implement** (implementer) ← test · (3 findings)
- ↻ **fix design** ← doc · (1 finding)
- ◈ **design-block** **minor** · (design) · ***◷ 1m***
- ▲ **build-pass** 18:52 · format, build, test, check, checkFormat, checkstyleMain, checkstyleTest, handoff-validate, autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 9s***
- ✔ **review security** · **approved** · ***◷ 17s***
- ✔ **review test** · **approved** · ***◷ 52s***
- ✔ **review code-quality** · **approved** · ***◷ 50s***
- ◆ **grade CLEAR** · narrow the vet directory by specialty
  - blast_radius — **clear** — Nine files but one feature package: two repository overloads, one controller, one template, two test classes, four docs. No sensitive path, no build or config file, no dependency, no schema. The widest reach is the vetList.html rewrite of all six paging anchors, and that stays inside the one template the vet list already owns.
  - semantic_surprise — **clear** — Every hunk does what the slice description says and no more. The blank decision is one isBlank helper both routes call; a non-blank value reaches the repository unstripped, which is the PRD's recorded edge case rather than a slip. The Distinct keyword guards the join against duplicate rows and the paged overload's totals describe the narrowed set. The rewritten anchors branch on a null specialty between two link expressions, so an unnarrowed page still renders /vets.html?page=2 exactly as before rather than a trailing specialty=. The filtered overloads carry no @Cacheable, which is deliberate and stated at the methods: a caller-named specialty would otherwise mint keys in a cache with no size limit and no eviction. That trade buys an uncached database read per narrowed request, bounded by page size on the HTML route and by the vets table on the JSON one.
  - test_adequacy — **clear** — The tests exercise the changed behavior rather than restate it, and the split is right: the derived query's semantics are pinned in ClinicServiceTests against real seeded H2, so case-insensitivity, non-prefix matching, surrounding spaces, the empty result, the multi-specialty vet keeping its full specialty list, and the paging totals are all proven against the database rather than a stub. The controller tests assert the model attribute, the blank fall-through with a spaces-only value, and the rendered link content including the escaped ampersand, so a template regression that dropped or unencoded the parameter would fail. Each would fail against a plausibly broken implementation.
  - reviewer_hedging — **clear** — Second pass is unanimous approval from all four reviewers the plan dispatched, each with an empty findings list and specific approved aspects naming what was re-verified. The first pass's critical doc block and two test autofixes were fixed and re-approved by the same reviewers, and the clarify was closed under the narrowest reading with the test-reviewer confirming the resolution. No escalate tag and no caveat left standing in an approval.
  - scope_deviation — **clear** — One design revision, zero build retries, zero consultations. The revision was mechanical, adding two doc paths the prior design-block had edited without listing and correcting a wrong claim about how Thymeleaf renders a null parameter; it re-decided nothing. The change reaches into product-scope documents, but the owner's dispatch quoted verbatim in the prd-entry authorized both the NG-9 narrowing and the two-surface address contract. The declared non-goals hold: no page control, no free-text search, no stripping, and the two Open Questions are left open rather than settled by an implementation choice.
  - why — Contained, well-tested, unanimously approved, and the diff matches its description at every hunk. The part worth a human's eyes is not the code but the product-scope edit: NG-9 narrowed, the withdrawn REQ-VET-002's machine-readable route reinstated under REQ-VET-003, and its Known Defects row deleted. Confirm that owner decision, then merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- VetRepository's two filtered overloads carry Javadoc explaining both the matching semantics (whole-name, case-insensitive) and the deliberate absence of @Cacheable, so a later reader does not add caching for symmetry with findAll
- VetController centralizes the blank/absent decision in one private namesASpecialty helper that both routes call, avoiding drift between /vets and /vets.html on what an unnamed specialty means
- namesASpecialty is a pure predicate (no side effects) named and used consistently with query-method conventions
- vetList.html's paging anchors use Thymeleaf's @{...} parameter form (URL-encoded) with an explicit null-check ternary per anchor plus an HTML comment explaining why, rather than silently letting a null parameter render as specialty=
- ./gradlew checkFormat passes with no formatting violations
- Naming (findDistinctBySpecialtiesNameIgnoreCase, namesASpecialty) follows existing repository/controller conventions and Spring Data naming rules; no get/set prefixes, no util/helper packages, no abbreviations

**security-reviewer**

- Injection: the filter reaches the database only through the Spring Data derived query  findDistinctBySpecialtiesNameIgnoreCase , which binds the value as a JPA criteria parameter. No string-concatenated SQL or JPQL is introduced. The derived-query property path is resolved at context startup from the method name, not from request data, so no user-supplied value can steer it. Matches the SQL-injection row of the system-design threat model.
- Reflected XSS on /vets.html: the value reaches the browser only through  th:href="@{/vets.html(page=...,specialty=${specialty})}"  on all six pagination links. The Thymeleaf link-expression parameter form URL-encodes the value and the attribute output is HTML-escaped by default in HTML template mode, so a payload such as  ">\<script>  renders inert as percent-encoded text. Swept the whole template set for the unescaped-output class ( th:utext ,  [(${...})]  unescaped inline,  th:onclick ,  javascript:  URLs) and found no instance anywhere under  src/main/resources/templates/ . VetControllerTests asserts the escaped  &amp;  separator, which pins the escaping behaviour.
- Model exposure:  specialty  is added to the model but rendered nowhere except the six href attributes; no other template reads the attribute. The controller normalizes an unnamed or blank value to null rather than echoing the raw value, which keeps the unnarrowed page's addresses byte-identical to the pre-change ones.
- Cache-key authoring (the design's stated concern) holds as shipped: both new repository methods in VetRepository carry  @Transactional(readOnly = true)  and neither carries  @Cacheable("vets") . Verified by reading the file, not the diff alone. An anonymous caller therefore cannot mint entries in the unbounded, evictionless  vets  cache.
- Resource consumption from an unbounded-length or high-cardinality value: no amplification path found. Because the filtered lookups are uncached, a distinct value creates no retained server-side state; each request is one parameterized, paged (size 5) read against a bounded vets/specialties join, and the value's length is already capped by the container's request-line limit. Cost is bounded by the same factors as the pre-existing unfiltered route.
- JSON route /vets: the value is consumed as a filter argument only and is never echoed into the response body, so the JSON surface adds no reflection sink. The response exposes no field the unfiltered route did not already expose.
- Secrets: swept the production diff for credential-shaped names (token, password, secret, key, credential) and found none. No configuration, profile, or property file is touched by this change.
- Supply chain:  build.gradle ,  settings.gradle ,  gradle.properties , and the wrapper are untouched by the change set, so the slice introduces no new dependency, no new transitive surface, and no new CVE exposure to check against the NVD.
- Attack surface delta: the change adds one optional read-only GET query parameter to two existing anonymous routes. It performs no write, no file I/O, no deserialization, no outbound call, and no privilege decision, so it crosses no trust boundary the application did not already cross. The absence of authentication on these routes is the pre-existing, documented posture recorded in the system-design Security Context, not a condition this slice introduces.

**doc-reviewer**

- PRD Veterinarian directory section, Non-Goals table, and Superseded entry stay coherent with the reinstated REQ-VET-003 and the withdrawn REQ-VET-002 id — no stale 'pending removal' language remains anywhere in the four changed docs
- New ADR docs/adr/2026-08-30-non-goal-veterinarian-search-narrowed.md follows the NG-4/NG-5 non-goal ADR precedent exactly in structure, filename convention, and Implementation section form
- docs/adr/README.md index row for the new ADR is correctly added
- Both PRD Open Questions on the visible control and space-trimming are correctly left open
- PRD stays at the behavioral abstraction level with no mechanism leakage for REQ-VET-003

**test-reviewer**

- Mocking split holds as designed: ClinicServiceTests (@DataJpaTest, real H2) proves case-insensitivity, non-prefix matching, blank-vs-space semantics, and paging totals for the derived query; VetControllerTests (MockMvc + MockitoBean VetRepository, the file's pre-existing pattern) proves parameter binding, the blank branch, the model attribute, and that paging links carry or omit the specialty -- exactly the split the design block called for, and MockMvc is the one sanctioned controller-test mock per the brief.
- New test names follow the brief's BDD school (the{Subject}Should{Outcome}) consistently.
- Four-phase structure (Act+Assert separated from setup by a blank line, no phase comments) is followed in every new test.
- theVetDirectoryShouldLeaveThePagingLinksUnnarrowedWhenNoSpecialtyIsNamed directly verifies the unnarrowed page's addresses stay free of the specialty parameter, matching the PRD's byte-identical-today requirement.
- ./gradlew test --tests ClinicServiceTests --tests VetControllerTests passes.

**doc-reviewer**

- docs/system-design.md:103 (Contracts row) now states 'the two unfiltered listings are cached, the two specialty-filtered listings are not' — matches VetRepository.java exactly: findAll()/findAll(Pageable) still carry @Cacheable("vets"), the two findDistinctBySpecialtiesNameIgnoreCase overloads carry none. Line 218 (Open Questions item 5) now scopes the no-eviction cache claim to 'the two findAll overloads' and separately records the specialty-filtered overloads as uncached, with the write-path question left open as before. Grepped every other 'cach' occurrence in the file (lines 20, 105, 130, 132) and none carries a stale blanket claim.
- State-vs-history split holds: both fixed lines state only which methods are cached, not why the filtered ones are deliberately left uncached. That causal story (cache-key-authoring risk in an unbounded, evictionless cache) is present in VetRepository.java's Javadoc on both new overloads and in the line-9 design-block, not duplicated into the durable doc.
- A two-line prose correction with no requirement or contract shift correctly took no supersedes_record_at — no re-triage was warranted, and none of my first-pass approved_aspects (PRD coherence, non-goal ADR fidelity, adr/README.md index row, PRD Open Questions, PRD abstraction level) were touched by this dispatch or need re-opening.
- Fix-delta scope (docs/system-design.md plus test-only changes in ClinicServiceTests.java and VetControllerTests.java) introduces no new cross-reference, anchor, or REQ-ID coherence issue between prd.md and system-design.md.

**security-reviewer**

- Fix delta is test-only plus two prose lines of docs/system-design.md; scripts/changeset.sh --base-tree 13532efb touches no production source, no template, no build or dependency file, so the attack surface I approved on the first pass is unchanged.
- No new trust boundary crossings: the added tests drive the same MockMvc dispatch and the same repository derived-query methods already reviewed; no new sink, no new deserialization, no new file or network I/O.
- No hardcoded secrets in the delta. Every new literal is a domain value (specialty names radiology/cardiology/surgery/dentistry, seeded vet surnames) or a page size; none names or carries a credential, token, or key.
- Output escaping unchanged and still asserted: theVetDirectoryShouldKeepTheSpecialtyOnPagingLinks continues to expect the HTML-encoded ampersand (/vets.html?page=2&amp;specialty=...), so the Thymeleaf auto-escaping of the reflected specialty parameter stays under test after the constant extraction.
- Injection posture unchanged: the specialty value still reaches only Spring Data derived query methods (findDistinctBySpecialtiesNameIgnoreCase), which bind it as a parameter; the delta adds no string-concatenated JPQL, native query, or Specification.
- The corrected docs/system-design.md cached-vs-uncached wording is a documentation accuracy fix. It matches the code as reviewed and carries no security consequence; the uncached filtered methods raise no cache-poisoning or stale-authorization concern in an application with no vet write path and no per-user vet data.

**test-reviewer**

- Edge case 2 resolved: theVetDirectoryShouldListEverySpecialtyOfAVetMatchedByOne filters by surgery, asserts the Douglas+Ortega match set, and asserts Douglas's getSpecialties() still contains both surgery and dentistry -- verified against seeded data (vet_specialties rows (3,2) and (3,3)) so the narrowing query is proven not to prune a matched vet's own specialty list.
- Three-Tier Data Naming resolved: seven javadoc'd class-level Tier 1 constants added to ClinicServiceTests and two to VetControllerTests, referenced from every new and touched test; swept both files for stray bare literals of the tier-1 values (radiology/surgery/dentistry/cardiology/surnames) and found none outside the constant declarations and one unrelated pre-existing assertion untouched by this delta. Scenario-specific values (thatSpecialtyInMixedCase, aPrefixOfThatSpecialty, onePerPage, etc.) are now named method-level locals.
- Clarify resolved via the narrowest reading: two purpose-named empty-result tests added, one per route (theVetDirectoryShouldListNoVetWhenNoVetHoldsTheNamedSpecialty for HTML, theMachineReadableVetListShouldCarryNoVetWhenNoVetHoldsTheNamedSpecialty for JSON), and theVetDirectoryShouldPassTheSpecialtyToTheRepositoryUnstripped is left proving only the unstripped-value contract.
- ./gradlew test --tests ClinicServiceTests --tests VetControllerTests passes.

**code-quality-reviewer**

- Tier 1 named constants in both ClinicServiceTests and VetControllerTests replace the repeated "radiology"/"cardiology"/surname literals the prior round flagged; each constant carries a role-describing Javadoc (e.g. SPECIALTY_HELD_BY_TWO_VETS, SURNAME_OF_THE_TWO_SPECIALTY_VET) so the intent behind the seeded value is legible without cross-referencing the H2 seed data.
- theVetDirectoryShouldListEverySpecialtyOfAVetMatchedByOne (ClinicServiceTests) reads as a single coherent assertion of the multi-specialty regression: containsExactlyInAnyOrder on surnames, then filteredOn+singleElement+extracting(list(Specialty.class)) to prove the matched vet's own specialty list survives the narrowing join, exactly the design-block-flagged risk.
- The two new unheld-specialty tests are correctly split one per route: theVetDirectoryShouldListNoVetWhenNoVetHoldsTheNamedSpecialty on /vets.html and theMachineReadableVetListShouldCarryNoVetWhenNoVetHoldsTheNamedSpecialty on /vets, each purpose-named for the bullet it proves rather than incidentally covering it.
- docs/system-design.md's two-line correction (VetRepository Contracts row and Open Questions item 5) is precise and reads standalone: it names exactly which overloads are cached and which are not, with no dangling reference to removed prose.
- ./gradlew checkFormat passes; the delta introduces no formatting violations.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $4.93 | 16m 41s | 96% |
| `agent-team:system-design-expert` | 3 | opus-5 | $2.42 | 5m 45s | 89% |
| `(parent)` | 1 | opus-5 | $2.36 | 36m 39s | 97% |
| `agent-team:change-grader` | 1 | opus-5 | $1.27 | 3m 33s | 90% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.19 | 3m 58s | 91% |
| `agent-team:security-reviewer` | 2 | opus-5 | $0.82 | 1m 29s | 80% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.69 | 1m 52s | 91% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.54 | 2m 58s | 85% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.47 | 1m 41s | 89% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $2.46 | 9m 59s | 97% |
| `(parent)` | opus-5 | $2.36 | 36m 39s | 97% |
| `agent-team:feature-implementer` | opus-5 | $1.99 | 5m 20s | 96% |
| `agent-team:change-grader` | opus-5 | $1.27 | 3m 33s | 90% |
| `agent-team:system-design-expert` | opus-5 | $1.20 | 3m 19s | 91% |
| `agent-team:product-requirements-expert` | opus-5 | $1.19 | 3m 58s | 91% |
| `agent-team:system-design-expert` | opus-5 | $0.65 | 1m 18s | 89% |
| `agent-team:system-design-expert` | opus-5 | $0.57 | 1m 7s | 84% |
| `agent-team:security-reviewer` | opus-5 | $0.50 | 1m 4s | 84% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.49 | 1m 23s | 93% |
| `agent-team:feature-implementer` | opus-5 | $0.48 | 1m 21s | 92% |
| `agent-team:test-reviewer` | sonnet-5 | $0.34 | 2m 1s | 85% |
| `agent-team:security-reviewer` | opus-5 | $0.32 | 25s | 71% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.25 | 1m 0s | 90% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.22 | 41s | 89% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.21 | 29s | 83% |
| `agent-team:test-reviewer` | sonnet-5 | $0.20 | 57s | 85% |

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

- plugin `agent-team-spring-boot` at `v0.2.3` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `064d588523591361` · `2.1.251 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
