# vets-specialty-filter r2 — v0.3.9

Filter the vet list by specialty (feature) · started 2026-09-06T21:00:03+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±1) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.67. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Normalization stays in the controller ( activeSpecialty ), where system-design places request binding, and the filter is a derived  findBySpecialties_NameIgnoreCase  on the existing Repository — no new rule leaks into the web layer, and the uncached choice is argued in an ADR. The cost is  vetList.html : the same  ${specialty == null} ? ... : ...  ternary is spelled out five times, an accepted but real duplication. Tests read as specifications ( theVetListPagingShouldKeepTheNamedSpecialty ,  theVetSearchShouldNotMatchAPartialSpecialtyName ), use named tiers ( HELD_SPECIALTY ,  UNHELD_SPECIALTY ) and a factory ( aPageOfATwoPageListing );  theVetSearchShouldMatchASpecialtyNameIgnoringCase  runs two acts before asserting, and new Mockito stubs continue tolerated rather than preferred practice. Documentation is complete: NG-9 narrowed, REQ-VET-003 minted, the superseded and known-defect rows corrected.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Normalization sits in the controller where system-design assigns request binding, and the repository gains two derived finders with the cache omission explained in an ADR — right layers, no new business rule. The template pays for it: five paging links each spell out both link forms (vetList.html), a ten-expression duplication the ADR accepts but a fragment or th:with would have removed. Tests are behavior-named (theVetListPagingShouldEncodeASpecialtyNameCarryingAUrlDelimiter), phase-separated, with tiered constants (HELD_SPECIALTY, VETS_HOLDING_SEEDED_SPECIALTY) and derived expectations; they reach for Mockito stubs rather than a hand-written double, which the mocking policy tolerates but does not prefer. Documentation is complete: NG-9 narrowed, REQ-VET-003 minted with REQ-VET-002 left withdrawn, contracts table, caching note, and the retired defect row all moved.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in the repository as two derived finders (VetRepository findBySpecialties_NameIgnoreCase), while the controller only binds and normalizes (activeSpecialty), which system-design assigns to the web layer; no new business rule enters the controller, and the cache and paging-link departures each carry an ADR. Tests are behavior-named and phase-separated, cover blank, unmatched, case, partial-prefix, delimiter-encoding and unfiltered-link cases, and add the aPageOfATwoPageListing factory; they lose a point for Mockito stubs on the new finders without the conscious-exception reasoning the principles ask, and theVetSearchShouldMatchASpecialtyNameIgnoringCase folds two acts into one test. vetList.html repeats the null branch across five links (accepted in ADR) — workable but rough. PRD NG-9, REQ-VET-003, superseded note, contracts table and Known Defects all move; no stale claim visible survives.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $13.91 | 38m | 4 | 94% | 11 file(s) +413/−30 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.97 | 2m 27s | 89% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Filter the veterinarian directory by specialty

1 review round · 1 build-pass · **1 build-failure** · grade **SCRUTINIZE**

| reviewer | R1 |
| --- | --- |
| **code-quality** | **✔** |
| **test** | **✔** (1) |
| **security** | **✔** (1) |
| **doc** | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Filter the veterinarian directory by specialty · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **minor** · (design) · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 13m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **minor** · (design) · supersedes L5 · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 2m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · (1 finding) · ***◷ 2m***
  - [clarify] `security-principles.md` This slice introduces the first instance in the codebase of a request-derived string composed into a URL the application emits, and the Realization table has no row for that class. The XSS row covers HTML escaping of rendered markup, which is a different control from URL-encoding a query-parameter value: a concatenated href would pass the XSS row while still letting a caller-supplied value inject an extra query parameter into the emitted link. The code here does the right thing (Thymeleaf link expressions with parameters on both branches, verified by the encoding test at VetControllerTests.theVetListPagingShouldEncodeASpecialtyNameCarryingAUrlDelimiter), and the ADR records the decision, but the durable bar the next implementer designs against still has no row. Ask whether the brief should gain one, worded so the control is 'link expression with parameters, never string concatenation'.
  - ▹ rec: Supply chain: no NVD matching ran in this review. The project configures no OWASP dependency-check plugin, and the change set does not touch build.gradle (Spring Boot 4.1.1 via the plugin, unchanged), so there is no dependency delta to verify. Treat the framework versions as not verified against the NVD in this pass; a CI or human check closes it.
  - ▹ rec: vetList.html line 20 binds a th:each local variable also named 'specialty' (the Specialty entity), while the pagination block below reads the model attribute 'specialty' (the request-derived filter string). The scopes do not overlap today, so there is no defect, but two different values under one name in one template is the shape in which an encoding assumption later changes meaning unnoticed. Renaming the loop variable would remove the ambiguity.
  - ▹ rec: Every filtered request reaches the database, by design. That matches the existing uncached owner-search surface and is strictly better than the unbounded-cache alternative, so it is not a regression against the recorded baseline; it is worth knowing as the accepted trade-off if this application is ever deployed outside the demonstration framing.
- ✔ **review test** · **approved** · (1 finding) · ***◷ 2m***
  - [clarify] `prd.md#req-vet-003` The PRD's suggested test names theVetListShouldMatchTheSpecialtyNameIgnoringCase and theVetListShouldNotMatchAPartialSpecialtyName implied controller-level placement. The design-block (line 9) correctly reassigns whole-name/case-fold matching semantics to the repository query, and the implementer relocated the equivalent tests to ClinicServiceTests as theVetSearchShouldMatchASpecialtyNameIgnoringCase / theVetSearchShouldNotMatchAPartialSpecialtyName. This is the right placement under testing-principles.md's pyramid rule and the design doc's explicit assignment (a mocked-repository controller test could only verify a stub call, which the mocking policy disfavors). Not a defect in this slice, but the PRD's test_names field should not imply file/layer placement, since the design doc's assignment governs and the two can diverge as they did here.
- ◆ **grade SCRUTINIZE** · filter both vet list surfaces by specialty
  - blast_radius — **skim** — One module and three production files: two new derived finders on VetRepository, an optional parameter plus a shared normalizer on VetController, and the five pagination links in vets/vetList.html. No sensitive paths, no new route, no build or config change; the remaining hunks are docs and tests.
  - semantic_surprise — **skim** — Reading the hunks, the code does what its size suggests: strip-then-blank-to-null in activeSpecialty, finder selection on null, and paged links that select between a one-parameter and a two-parameter link expression so an unfiltered page keeps the exact links it had. The template's th:each variable named specialty scopes to the table cell and cannot reach the pagination block; case folding sits in the query rather than the column collation; the filtered finders skip the cache deliberately. Two values for the parameter bind to a comma-joined string and match nothing, which the design record states as the intended narrowest reading.
  - test_adequacy — **skim** — Twelve new tests that would fail against a broken implementation rather than restate it: the repository seam runs against real H2 seed data and pins whole-name matching, case folding, no partial match, and database paging with one row of two total; the controller tests pin the rendered link text, including URL-encoding of a name holding a delimiter and the regression that unfiltered links carry no specialty parameter at all.
  - reviewer_hedging — **scrutinize** — All four dispatched reviewers approved, but two approvals carry caveats: security filed a clarify tagged bar_clause secure-by-design, since the security brief has no row for composing a request-derived value into an emitted URL, plus three recommendations - no NVD check ran this pass, the template binds two different values to the name specialty, and every filtered request reaches the database uncached - and test-reviewer filed a clarify that the PRD's test_names implied a layer the design doc overrode.
  - scope_deviation — **skim** — The diff matches the intake record's three owner decisions exactly: NG-9 narrowed, the machine-readable surface reinstated under a fresh id, and no page control added. The single design revision was a records-coverage repair plus a corrected Thymeleaf assumption, not a scope wander. Note that the row's build_retries of 0 undercounts one aborted gate at log line 7, which failed the autofix audit on design-doc coverage with no code defect implicated.
  - why — Nothing in the diff surprised me and the tests are real. The residual is reviewer caveats worth a human minute: the security brief has no rule for request-derived values composed into emitted URLs, and vetList.html now binds two different meanings to the name specialty.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**doc-reviewer**

- PRD stays behavioral: REQ-VET-003 prose and acceptance criteria carry no code identifiers, and the anchor req-vet-003 is present at first mention
- All three verbatim intake decisions are faithfully recorded: NG-9 narrowed with dated ADR link, REQ-VET-002 remains in Superseded with explicit id-not-reused language and reinstatement note, and the address-only/no-control constraint is stated as both a requirement sentence and an edge case
- system-design.md Contracts and Persistence rows stay at purpose-plus-source-pointer altitude - no field or parameter tables, no constant literals, and the VetController/VetRepository/Vets rows accurately describe the landed code (verified against VetController.java, VetRepository.java, vetList.html)
- The three new ADRs follow the template, use correct Non-goal:/Requirements: Implementation sections, and cross-reference each other and the PRD/system-design sections they serve; docs/adr/README.md indexes all three
- The new Known Defects row about owner-search paging dropping the search term is verified accurate against ownersList.html, and is correctly marked derived/unconfirmed
- Cross-document coherence holds: REQ-VET-003 appears consistently in prd.md, system-design.md Contracts table, and both non-goal and paging ADRs; no dangling links found

**code-quality-reviewer**

- Controller stays request-adaptation only (parameter strip/blank-to-null, finder selection); matching semantics (whole-name, case-insensitive) live in the derived repository query, per architecture-principles.md Web controller row
- activeSpecialty() is a small, well-documented, single-purpose helper reused across both surfaces rather than duplicated
- VetRepository derived finders and their Javadoc clearly explain the uncached decision and cite the backing ADR
- vetList.html paging links use Thymeleaf link expressions with parameters (not string concatenation), correctly URL-encoding caller-supplied specialty names, matching the design-block's risk-1 mitigation and the paging-links ADR
- New domain-facing vocabulary (specialty, vet) matches docs/ubiquitous-language.md; no coined synonyms introduced
- checkFormat and checkstyleMain both pass clean on the diff
- docs/system-design.md and docs/prd.md updates are consistent with the shipped code (Contracts rows, Known Defects, ADR cross-links)

**security-reviewer**

- Data access: both new finders are Spring Data derived queries (findBySpecialties_NameIgnoreCase), so the caller-supplied name binds as a query parameter. No @Query string, no concatenated JPQL or SQL anywhere in the change. The 'Injection into data access' row passes.
- URL composition and XSS: every one of the five pagination links in vetList.html uses the link-expression-with-parameters form on both branches, so the specialty is URL-encoded and then attribute-escaped. The previous __${...}__ preprocessing form was removed rather than extended, which also removes the template-expression-evaluation surface from this file; the specialty never reaches a preprocessed expression. The '&' and blank-value tests pin the encoding behavior.
- Class sweep for request-derived values composed into URLs: swept every th:href / th:src / th:action in src/main/resources/templates/. The remaining preprocessing sites (layout.html menu link, ownersList.html and ownerDetails.html paging and id links) interpolate an int page number, an entity id, or a fixed constant, none request-derived as text. vetList.html is the only instance of the class and it is handled correctly.
- Cache key space: the omission of @Cacheable on both filtered finders is the right call and is justified in place. Caching them would key the JCache-backed 'vets' cache on caller-supplied text with no eviction bound, which is an unauthenticated memory-growth primitive on a route that needs no credentials. The whole-directory reads keep their existing caching, so the change removes nothing.
- Input handling at the boundary: activeSpecialty normalizes null / blank / padded to a single null 'no filter' state before any use, and both surfaces share the one helper, so the HTML and JSON routes cannot diverge on how a hostile value is read.
- Exposed surface: no new route. /vets and /vets.html both existed and both already published the full specialty list publicly, so the filter discloses nothing a caller could not already read, and no enumeration oracle is created.
- No secrets, no credentials, no logging, no file or process or network I/O, no deserialization configuration, and no serialization annotations in the change. build.gradle is untouched, so the change adds no dependency and no supply-chain delta.

**test-reviewer**

- Case-insensitive whole-name matching and partial-name non-matching are tested at the repository seam (ClinicServiceTests, real H2 via @DataJpaTest) rather than through a mocked-repository controller test, correctly following system-design.md's assignment of matching semantics to the derived query rather than the controller
- Every PRD Done-when bullet for REQ-VET-003 has a corresponding test (coverage-map: 6/8 declared names match by literal string, the other 2 are the relocated repository-seam tests discussed above, which cover the same bullets)
- URL-encoding of a specialty name containing a delimiter is tested (theVetListPagingShouldEncodeASpecialtyNameCarryingAUrlDelimiter), matching the design-block's XSS/link-corruption risk mitigation
- Unfiltered paging links are asserted unchanged (theVetListPagingShouldNameNoSpecialtyWhenTheListingIsUnfiltered), guarding the PRD's 'without the parameter both surfaces behave exactly as today' criterion
- Blank/whitespace-only and padded specialty values are each covered on both surfaces
- Tests follow the BDD the{Subject}Should{Outcome} naming school, use AssertJ fluent assertions, real H2 I/O for repository tests, Tier-1 named constants (HELD_SPECIALTY, SEEDED_SPECIALTY, etc.), and reuse existing factory methods (helen(), james(), pageable) with one new factory (aPageOfATwoPageListing()) rather than raw construction
- ./gradlew test passes for both changed test classes

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $5.25 | 16m 53s | 97% |
| `agent-team:system-design-expert` | 2 | opus-5 | $3.73 | 10m 53s | 94% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.47 | 3m 55s | 94% |
| `(parent)` | 1 | opus-5 | $1.42 | 40m 36s | 96% |
| `agent-team:change-grader` | 1 | opus-5 | $0.97 | 2m 27s | 89% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.85 | 2m 14s | 89% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.46 | 2m 27s | 91% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.40 | 1m 28s | 93% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.33 | 1m 10s | 90% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.47 | 14m 29s | 97% |
| `agent-team:system-design-expert` | opus-5 | $1.94 | 5m 25s | 94% |
| `agent-team:system-design-expert` | opus-5 | $1.80 | 5m 28s | 94% |
| `agent-team:product-requirements-expert` | opus-5 | $1.47 | 3m 55s | 94% |
| `(parent)` | opus-5 | $1.42 | 40m 36s | 96% |
| `agent-team:change-grader` | opus-5 | $0.97 | 2m 27s | 89% |
| `agent-team:security-reviewer` | opus-5 | $0.85 | 2m 14s | 89% |
| `agent-team:feature-implementer` | opus-5 | $0.78 | 2m 23s | 91% |
| `agent-team:test-reviewer` | sonnet-5 | $0.46 | 2m 27s | 91% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.40 | 1m 28s | 93% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.33 | 1m 10s | 90% |

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
