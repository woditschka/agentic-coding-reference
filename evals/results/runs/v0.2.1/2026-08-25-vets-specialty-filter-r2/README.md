# vets-specialty-filter r2 — v0.2.1

Filter the vet list by specialty (feature) · started 2026-08-25T00:36:42+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 4 (±1) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.74. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in the repository via derived finders (VetRepository.findDistinctBySpecialtiesNameIgnoreCase), leaving VetController thin — only normalize() and a branch; but the same  specialty.isEmpty() ? findAll : findDistinct...  decision is duplicated in showVetList/showResourcesVetList, and the null-vs-empty model attribute is a subtle seam. Tests are behavior-named and cover case-insensitivity, prefix non-match, blank, empty result, and paging; they lose points for bare literals ("radiology", "Leary", "cardiology") that the three-tier convention would name, and for pinning raw href/class strings in theVetDirectoryPagingShouldKeepTheRequestedSpecialtyOnEveryDirectionalLink. The template repeats the same ternary across six links. Documentation is complete: NG-9 narrowed with ADR, fresh REQ-VET-003, superseded note, contracts table, security rows, obsolete defect row removed, vocabulary entry.

**Sample 2** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> Matching lands in the repository as a derived  findDistinctBySpecialtiesNameIgnoreCase  finder, the right layer, and the cache decision is reasoned in an ADR. But  VetController.normalize  plus the repeated  specialty.isEmpty() ? findAll : findDistinct...  ternary puts a new blank-means-all rule inside a controller and behind a private method, unreachable without booting the web layer — the checklist bars new controller rules. Tests are BDD-named and phase-clean, yet  theVetDirectoryPagingShouldKeepTheRequestedSpecialtyOnEveryDirectionalLink  pins raw markup including  class="fa fa-fast-backward"  and attribute order, mixes Hamcrest  assertThat  with AssertJ, and seeded expectations ( "Leary", "Stevens" ) are bare literals. Docs are thorough: NG-9 narrowed, REQ-VET-003 minted, the obsolete known-defect row and the "no JSON API" overview claim both removed.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Narrowing lives in derived repository finders (VetRepository.findDistinctBySpecialtiesNameIgnoreCase), leaving the controller to bind, trim, and delegate — the Web controller row is respected, and the cache decision is reasoned in the ADR and javadoc. Costs: the controller now branches on blank vs. present in two places, and vetList.html repeats the same filtered/unfiltered ternary five times, which a template variable or always-passing the parameter would have collapsed. Tests are behavior-named and cover case-insensitivity, prefix non-match, blank, empty result, paging, and URL encoding, but ClinicServiceTests asserts bare seeded literals ("radiology", "Leary", "Stevens") with no named constants or derivation, VetControllerTests pins exact rendered anchor markup, and Hamcrest assertThat is mixed into an AssertJ suite. Documentation is complete: NG-9 narrowed, REQ-VET-003 minted, superseded note, defect row retired, threat model and glossary updated.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $14.82 | 45m | 32 | 93% | 11 file(s) +378/−33 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.22 | 3m 39s | 89% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-001 — Veterinarian directory narrows to one specialty on both surfaces

2 review rounds · 2 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | · |
| **doc** | ✎ (2) | **✔** |

- ◇ **prd-entry** Veterinarian directory narrows to one specialty on both surfaces · (prd-expert) · ***◷ 4m***
- ◈ **design-block** **new** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 11m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · format · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 50s***
- ✔ **review security** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `VetControllerTests.java:theVetDirector` vetList.html carries five pagination links (numbered pages, first, previous, next, last), each with its own filtered/unfiltered ternary. Every paging test in VetControllerTests that supplies a specialty (theVetDirectoryPagingShouldKeepTheRequestedSpecialty, theVetDirectoryPagingShouldUrlEncodeTheRequestedSpecialty) requests page=1 of a 2-page result, so currentPage>1 is always false and the 'first' and 'previous' anchors never render (th:if="${currentPage > 1}"). Those two ternaries are template logic Jacoco does not instrument, so nothing in the suite proves they carry the specialty parameter; a regression there (e.g. someone pastes the old '?page=1' form onto just those two links) would pass the whole gate.
    - fix: Add a paging case with a 3-page narrowed result and page=2 (e.g. stub findDistinctBySpecialtiesNameIgnoreCase to return a PageImpl with PageRequest.of(1,1) and total 3), asserting the rendered content contains the 'first' (page=1) and 'previous' (page=1) hrefs with '&amp;specialty=\<value>' alongside the already-covered 'next'/'last' links.
- ✎ **review doc** · **changes_requested** · (2 findings) · ***◷ 3m***
  - [autofix] `prd.md:145` The **ADR:** citation under Veterinarian directory reads '[ADR: Narrowing the Veterinarian Directory Is In Scope]', truncating the ADR's actual title, which continues '; Free-Text Veterinarian Search Is Not'. The project's established convention (see Pet records: '[ADR: Database-Enforced Pet Name Uniqueness Within an Owner]') is for this link's text to match the ADR's H1 verbatim, and the truncated form drops the half of the decision that bars free-text search.
    - fix: Change the link text to the ADR's full title: '[ADR: Narrowing the Veterinarian Directory Is In Scope; Free-Text Veterinarian Search Is Not](adr/2026-08-25-non-goal-vet-directory-filtering.md)'.
  - [autofix] `2026-08-25-non-goal-vet-directory-filt` The second sentence of the Context section ('Read as written, it bars search — typing free text and getting ranked or prefix-matched entities back — which is a different capability from narrowing a published list to a value it already prints in every row.') runs 35 words, over the 30-word sentence-length standard.
    - fix: Split into two sentences, e.g. break after 'entities back' into its own clause describing the narrowing contrast.
- ↻ **implement** (implementer) ← test · (1 finding)
- ↻ **fix prd-expert** ← doc · (2 findings)
- ↻ **fix design** ← doc · (2 findings)
- ◈ **design-block** **new** · (design) · ***◷ 39s***
- ◇ **prd-entry** Veterinarian directory narrows to one specialty on both surfaces · (prd-expert) · ***◷ 44s***
- ▲ **build-pass** 01:15 · build, test, format, handoff-log, autofix-audit
- ✔ **review test** · **approved** · ***◷ 35s***
- ✔ **review doc** · **approved** · ***◷ 32s***
- ◆ **grade CLEAR** · narrow the vet directory by specialty on both surfaces
  - blast_radius — **clear** — Eleven files but shallow reach: three production files all inside the vet feature package, two test files, and six docs recording this same slice. No sensitive paths, no schema, build, or dependency changes, and both route signatures gain only an optional parameter that defaults to today's behavior.
  - semantic_surprise — **clear** — Read all 43 hunks and found nothing the description would not predict. normalize() is a plain strip() that cannot NPE behind an empty-string request-param default; the blank branch still calls the cached findAll, so the no-parameter path is unchanged; the narrowing is applied by the query rather than by filtering an already-fetched page, so totals and page counts stay correct; and the model carries null rather than an empty string, so unfiltered pagination links render exactly as before.
  - test_adequacy — **clear** — Matching semantics are proven against real H2 in ClinicServiceTests - mixed-case match, prefix non-match, no-match empty, and totals on a narrowed page - rather than through the controller stub, which could not prove them. The blank-equals-absent branch uses the deliberately unstubbed narrowed finder as a negative control, and the round-1 gap where page=1 hid the first and previous ternaries is closed by a page-2-of-3 case asserting whole anchors: href plus title plus class.
  - reviewer_hedging — **clear** — All four rostered reviewers reached approved with empty findings. Code-quality and security approved in round one; test and doc each raised one bar_clause-flagged fixable finding and each re-verified its own fix in round two, the doc-reviewer diffing the superseding prd-entry field by field and the test-reviewer confirming the mutation kill. No escalate tag and no reservation carried into an approval.
  - scope_deviation — **clear** — Zero build retries and zero consultations; the single design revision was bookkeeping, superseding the line-4 record only to name two doc paths the autofix audit could not see, with no source rework. Changed files match the intake prd-entry targets, and the two genuinely open product questions (a visible control, the surrounding-space convention) were recorded as PRD Open Questions rather than decided in code.
  - why — An additive optional parameter on two vet routes: the no-parameter path stays byte-identical and cached, narrowing happens in the query so paging counts the narrowed list, and reflected caller input reaches only URL-encoded named link parameters. Confirm and merge; revisit the five duplicated template ternaries only if pagination markup changes again.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- checkFormat passes clean (task is named checkFormat, not checkJavaFormat, in this project's build.gradle)
- normalize()'s javadoc claim of following the owner-search blank-is-absent convention checked out against OwnerController.java:98-103
- VetRepository javadoc explains the deliberate absence of @Cacheable on the narrowed queries with concrete reasoning (unbounded cache key from caller input)
- vetList.html's filtered-link comment explains why the named-parameter URL form is required over the old page=__${i}__ preprocessing form, preventing a plausible future regression
- normalize()/model attribute null-vs-empty distinction is commented with its rationale (Thymeleaf renders a null parameter as absent, an empty one as a trailing '?specialty=')
- Naming, method length, and control flow all follow the existing codebase's conventions with no new violations introduced
- Minor non-blocking observation: the empty-vs-narrowed dispatch (findAll vs findDistinctBySpecialtiesNameIgnoreCase) is duplicated in two shapes across findPaginated (VetController.java:64-70) and showResourcesVetList (VetController.java:73-81); Page and Collection return types make a shared helper awkward so this is not flagged as a defect

**security-reviewer**

- Injection: the specialty narrowing uses the Spring Data derived finder findDistinctBySpecialtiesNameIgnoreCase(String, Pageable) — the caller value is bound as a JPA query parameter, never concatenated into JPQL or native SQL. No @Query, no EntityManager string building, no Criteria literal anywhere in the diff. No SQL-injection exposure.
- Cache decision held as designed: @Cacheable("vets") remains on both unfiltered finders (VetRepository findAll() and findAll(Pageable)); neither filtered finder carries it, and the omission is documented in the Javadoc. The unbounded 'vets' cache (CacheConfiguration.java:37, no size limit) is therefore never keyed on caller-supplied text arriving on an unauthenticated route.
- Reflected XSS: swept every branch of vetList.html. All eight pagination hrefs use the named-parameter form @{/vets.html(page=..., specialty=${specialty})}; no '__${...}__' preprocessing remains in the file (grep -F '__${' matches only the warning comment at line 29). Thymeleaf URL-encodes the parameter value and HTML-escapes the attribute, so '&', '=', '"' and '\<' cannot break out of the href. The value reaches the page through no other sink — no th:text, th:utext, th:attr or inlining of ${specialty} exists in the template, and grep -F 'th:utext' finds none anywhere under templates/. Encoding is regression-covered by theVetDirectoryPagingShouldUrlEncodeTheRequestedSpecialty.
- Parameter-splitting / open-redirect: the encoded value cannot inject an extra query parameter, and the link path is a fixed literal, so no attacker-controlled destination.
- JSON surface: /vets returns the unchanged Vets/Vet/Specialty shape (id, first name, last name, specialty names). The reinstated filter narrows the result set; it adds no field and widens no projection, so it introduces no new data exposure. Vet names are already public directory data under the system-design threat model.
- Blank/whitespace handling is a strip() on a String parameter — no path, file, command, deserialization or reflection sink is reached by the caller value on either route.
- Secrets: swept the added lines for password/secret/token/api-key/credential/private-key/Authorization. The only hit is prose in docs/system-design.md restating that datasource credentials come from environment variables. No credential material introduced.
- Supply chain: build.gradle, settings.gradle and gradle/ are untouched by the change set, so the dependency graph and its CVE surface are unchanged by this slice.

**test-reviewer**

- Matching semantics (case-insensitivity, whole-name/no-prefix match, no-match empty result, query-level pagination of the narrowed list) are proven against real H2 in ClinicServiceTests per the design's mocking-policy split; VetControllerTests correctly restricts itself to parameter binding, the blank-equals-absent branch, the model attribute, and pagination-link construction, never asserting matching behavior through the @MockitoBean stub
- Every acceptance criterion in the prd-entry (both surfaces, case-insensitive whole-name match, no-prefix-match, surrounding-space stripping, no-match-yields-200-empty-list, blank-equals-absent, unchanged no-parameter behavior, paging-carries-parameter, URL-encoding of the parameter) has a dedicated test naming the outcome, matching the prd-entry's test_names list
- Seeded fixture data (radiology -> Leary/Stevens, surgery -> Douglas/Ortega) is used correctly and verifiably against src/main/resources/db/h2/data.sql, not invented
- BDD naming school (the{Subject}Should{Outcome}) followed throughout the new tests; AssertJ used in ClinicServiceTests, hamcrest/MockMvc idiom in VetControllerTests matches the file's pre-existing convention
- ./gradlew test is green (30 tests across the two files, 0 failures) and Jacoco reports 100% line/branch coverage on VetController and VetRepository

**doc-reviewer**

- NG-9 is narrowed rather than removed, following the same Non-Goals-table + ADR-link convention established for NG-4/NG-5 on 2026-08-08, with an appropriately different verb ('Narrowed' vs 'Confirmed deliberate') reflecting the different action taken
- REQ-VET-002 stays withdrawn with its id explicitly marked never-reused, and REQ-VET-003 is correctly framed as a fresh requirement rather than a successor, consistently across prd.md's Requirements, Superseded, and Open Questions sections
- The visible specialty control is correctly recorded as an Open Question rather than as scoped work, and the surrounding-spaces convention is likewise flagged as pending confirmation
- PRD and system-design.md both correctly omit concrete route/URL strings, consistent with the project's existing convention that routing details (view-name constants, etc.) are deliberately excluded from both documents; the concrete URL contract living only in the handoff record holds up against this register
- The stale 'pending removal' Known Defects row and the stale 'no JSON API' Overview claim are both fully retired with no leftover references found elsewhere in the reviewed docs
- Both new ADRs conform to the template (Status, Context, Options Considered, Decision, Consequences, Implementation, References with em-dashes), and the non-goal ADR correctly uses **Non-goal:** NG-9 while the matching ADR uses **Requirements:**
- docs/adr/README.md index rows match each ADR's H1 exactly and sit correctly ordered under the index table
- docs/ubiquitous-language.md gains a properly formatted 'Veterinarian directory' entry with a provenance date, consistent with how prd.md and system-design.md now both use that term
- All new and changed cross-references (PRD anchors, ADR sibling links, system-design.md section links) resolve to real anchors and files

**test-reviewer**

- theVetDirectoryPagingShouldKeepTheRequestedSpecialtyOnEveryDirectionalLink stands at page=2 of a 3-page narrowed result, the one vantage point where first/previous/next/last all render, closing the round-1 gap where page=1 hid the first/previous ternaries from ever executing
- Whole-anchor matching (href+title+class) is strictly more precise than an href-only assertion: the numbered page-one link at vetList.html:38 renders the identical href with no title/class, so href-only would not have distinguished a regressed first/previous ternary from the numbered link
- Mutation kill verified by the implementer's own account and consistent with the assertion's exact-match shape: rewriting the first-link ternary to the unfiltered form would drop 'specialty=radiology' from that anchor and fail the containsString check
- Whitespace normalization (replaceAll on rendered output) targets Thymeleaf's template-preserved line break between attributes, not the assertion's semantic content, and does not loosen what is being verified
- gradle test run confirms 13 tests in VetControllerTests, 0 failures

**doc-reviewer**

- docs/prd.md:145 now carries the ADR's H1 verbatim, '[ADR: Narrowing the Veterinarian Directory Is In Scope; Free-Text Veterinarian Search Is Not]', resolving the round-1 truncation finding; a sweep of every '[ADR:' link in docs/prd.md and docs/adr/ finds no other truncated title
- docs/adr/2026-08-25-non-goal-vet-directory-filtering.md:9 is split into a 16-word sentence ('Read as written, it bars search — typing free text and getting ranked or prefix-matched entities back.') and a 19-word sentence ('That is a different capability from narrowing a published list to a value it already prints in every row.'), both under the 30-word standard; a re-scan of the whole ADR finds no sentence over 30 words
- the split preserves the decision's meaning verbatim: NG-9 still bars free-text search and narrowing a published list is still stated as a different capability, matching the Decision section's own framing at line 21
- the superseding prd-entry at handoff.jsonl line 24 carries title, summary, acceptance_criteria, non_goals, and test_names byte-identical to line 2 (diffed programmatically); the only change is file_targets gaining docs/prd.md, which is the correct consequence of this dispatch having edited that file, and notes correctly attributes the ADR sentence-length fix to system-design-expert and the test finding to feature-implementer rather than claiming it

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $5.09 | 17m 11s | 96% |
| `agent-team:system-design-expert` | 3 | opus-5 | $3.13 | 8m 49s | 92% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $1.94 | 6m 4s | 92% |
| `(parent)` | 1 | opus-5 | $1.85 | 48m 14s | 96% |
| `agent-team:change-grader` | 1 | opus-5 | $1.22 | 3m 39s | 89% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.72 | 4m 27s | 86% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.58 | 3m 3s | 90% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.56 | 1m 13s | 88% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.19 | 57s | 86% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.06 | 12s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.20 | 11m 44s | 97% |
| `agent-team:system-design-expert` | opus-5 | $1.94 | 5m 48s | 95% |
| `(parent)` | opus-5 | $1.85 | 48m 14s | 96% |
| `agent-team:product-requirements-expert` | opus-5 | $1.48 | 5m 3s | 93% |
| `agent-team:change-grader` | opus-5 | $1.22 | 3m 39s | 89% |
| `agent-team:feature-implementer` | opus-5 | $1.21 | 3m 47s | 95% |
| `agent-team:system-design-expert` | opus-5 | $0.74 | 2m 8s | 88% |
| `agent-team:feature-implementer` | opus-5 | $0.68 | 1m 39s | 93% |
| `agent-team:security-reviewer` | opus-5 | $0.56 | 1m 13s | 88% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.56 | 3m 48s | 85% |
| `agent-team:product-requirements-expert` | opus-5 | $0.46 | 1m 1s | 88% |
| `agent-team:test-reviewer` | sonnet-5 | $0.44 | 2m 23s | 92% |
| `agent-team:system-design-expert` | opus-5 | $0.44 | 52s | 79% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.19 | 57s | 86% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.16 | 38s | 86% |
| `agent-team:test-reviewer` | sonnet-5 | $0.14 | 40s | 80% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.06 | 12s | 50% |

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

- plugin `agent-team-spring-boot` at `v0.2.1` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `064d588523591361` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
