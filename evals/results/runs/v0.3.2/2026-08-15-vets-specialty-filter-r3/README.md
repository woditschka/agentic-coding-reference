# vets-specialty-filter r3 — v0.3.2

Filter the vet list by specialty (feature) · started 2026-08-15T19:05:07+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $1.05. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The rule lands in the repository ( findDistinctBySpecialtiesNameIgnoreCase ) rather than the controller, matching the Web controller and Repository rows, with the caching and case-normalization choices recorded in an ADR; the controller keeps only binding ( selectedSpecialty ) and a null dispatch. Blemishes: the same null/filtered ternary appears in both  findPaginated  and  findVets , and vetList.html repeats a five-way  ${narrowed} ? ... : ...  link expression, adding real view duplication for a Thymeleaf null-param quirk. Tests are behavior-named, phase-separated, and use named constants and helpers, but new web tests still reach for Mockito stubs ( given(...) ) and lean on shared  @BeforeEach  counts ( hasSize(2) ). Documentation is complete: NG-9 narrowed, REQ-VET-003/004 minted, REQ-VET-002 left withdrawn, defect row retired, ADR index updated.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The rule lands in  VetRepository.findDistinctBySpecialtiesNameIgnoreCase  rather than the controller, so the *Web controller* row is respected;  selectedSpecialty / findVets  keep binding thin, and the uncached, case-normalized choice is reasoned in an ADR. Cost is the template: each of five pagination links is duplicated behind a  ${narrowed} ? ... : ...  ternary (vetList.html), copy-paste variance a helper or param map would avoid. Tests are behavior-named, phase-separated, parameterized for blank values, and cover matching, prefix, empty result, encoding, and paging. But new controller tests stub the internal repository with Mockito,  hasSize(2)  leans on the shared  @BeforeEach  fixture,  containsExactlyInAnyOrder("Leary","Stevens") / isEqualTo(2)  are seed-derived literals, and the duplicate-specialty test asserts two acts. Docs are complete: NG-9 narrowed, REQ-VET-003/004 minted, defect row retired, two ADRs indexed.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in VetRepository.findDistinctBySpecialtiesNameIgnoreCase rather than the controller, which only maps blank to null (VetController.selectedSpecialty) — the Web controller row holds, and both ADRs record the case-normalization and no-cache rules. Deduction: the pagination ternary is copy-pasted across five links in vetList.html, five places to edit for the next parameter. Tests are behavior-named and four-phase, cover partial-name, no-match, encoding, blank via @ValueSource, and duplicate specialty rows behind persistVetHoldingTwoSpecialtyRowsNamed; but new controller tests extend the Mockito stubs the principles call a conscious exception, and "Ada"/"Nakamura", "Leary", "Stevens" are bare Tier-3 literals. Javadoc on the private selectedSpecialty largely restates the code. Docs: NG-9 narrowed, REQ-VET-003/004 minted, the withdrawn defect row retired, contracts updated — nothing visible left stale.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $15.79 | 48m | 39 | 95% | 10 file(s) +379/−32 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.13 | 2m 54s | 89% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VETSSPECIALTYFILTER-001

0 review rounds · 0 build-passes · no grade yet

- • intake-decision (human)

---

### REQ-VET-003 — Reader narrows the veterinarian directory to one specialty from the address

2 review rounds · 2 build-passes · **1 build-failure** · grade **CONCERN**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (2) | **✔** (1) |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- • intake-decision (human)
- ◇ **prd-entry** Reader narrows the veterinarian directory to one specialty from the address · (prd-expert) · ***◷ 4m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 13m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L6 · ***◷ 41s***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · checkFormat · handoff-validate · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain: build.gradle is unchanged by this slice and adds no dependency, so there is no supply-chain delta to verify. Note for the record that no NVD matching ran in this review — the OWASP dependency-check plugin is not configured in build.gradle (plugins declare java, checkstyle, jacoco, spring-boot 4.1.0, dependency-management 1.1.7, graalvm native 1.1.2, cyclonedx 3.2.4, javaformat 0.0.47, nohttp 0.0.11) and this reviewer has no network access. The declared framework version is Spring Boot 4.1.0; a human or CI should close the CVE check against the NVD. The CycloneDX SBOM task and the nohttp plain-HTTP check remain enabled.
  - ▹ rec: The specialty value has no length bound before it reaches the query and the rendered links. Reach is limited — a value long enough to be interesting matches no specialty, so totalPages stays 0 and no link renders — so this is a note, not a finding. If a visible control follows in a later slice, a @Size bound on the parameter would be the cheap place to cap it.
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 2m***
  - [autofix] `ClinicServiceTests.java:236-244` The design-block (line 10) names a specific risk this repository query was written to guard against: 'specialties.name carries no uniqueness constraint on any vendor schema, so a veterinarian linked to two identically named specialty rows would be listed twice and counted twice', mitigated by 'a distinct query so both the result and the derived count query count distinct veterinarians' — the reason findDistinctBySpecialtiesNameIgnoreCase is named with Distinct rather than plain findBySpecialtiesNameIgnoreCase. No test in ClinicServiceTests persists a vet with two specialty rows sharing one name and asserts it is returned/counted once. If Distinct were dropped from the query in a later edit, no test would fail — the fixture data (src/main/resources/db/h2/data.sql) never gives one vet two same-named specialties, so the two existing new tests (theVetListShouldMatchTheSpecialtyNameIgnoringLetterCase, theVetListPagingShouldCountOnlyVeterinariansHoldingTheSpecialty) pass regardless of whether the query deduplicates.
    - fix: Add a @Transactional test in ClinicServiceTests that persists (via the injected VetRepository/EntityManager or a @Sql script) a vet linked to two specialty rows with the same name (e.g. two 'radiology' rows with different ids), then asserts findDistinctBySpecialtiesNameIgnoreCase("radiology") returns that vet exactly once and the paged variant's getTotalElements() counts it once.
  - [autofix] `VetControllerTests.java:171-176` Acceptance criterion 4 (prd-entry, line 4) and the intake decision (line 2) both state the parameter is ignored when it is 'empty or whitespace-only'. Both new tests exercise only the whitespace-only case (WHITESPACE_ONLY_SPECIALTY = "   "); no test sends specialty="" (a genuinely empty value, e.g. from an empty form field or a bare '?specialty=' in the URL). The code path (StringUtils.hasText) covers both, but the empty-string case is a documented edge case with no dedicated test case per the brief's Edge Case Coverage checklist.
    - fix: Turn theVetListShouldIgnoreABlankSpecialtyValue (and its JSON-surface counterpart) into a @ParameterizedTest with @ValueSource(strings = {"", "   "}) or @CsvSource covering both the empty and whitespace-only values, per testing-principles.md's Parameterized Tests guidance for repetitive edge-case coverage.
- ↻ **implement** (implementer) ← test · (2 findings) · ***◷ 8m***
  - ▲ **build ✓ clean** · build · test · check · format · checkFormat · checkstyle · handoff-validate · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved** · (1 finding) · ***◷ 3m***
  - [clarify] `ClinicServiceTests.java:258-280` Accepting the implementer's measured caveat that dropping Distinct from findDistinctBySpecialtiesNameIgnoreCase does not fail this test: the test correctly pins the observable requirement (a vet linked to two identically-named specialty rows is returned/counted once), which is the right thing to assert per the brief's tested-as-spec principle — asserting outcome, not keyword. But the project has a standing, documented precedent for exactly this shape of gap: the design-block (line 6/10) itself flags 'relying on H2's default matching would let the case-insensitivity criterion pass under the H2 test suite while failing under PostgreSQL, repeating the recorded owner-search defect.' The theory that best explains the caveat is that the paged assertion never exercises the derived count query at all — the H2 --info log for this test shows a single content query with 'fetch first ? rows only' and one matching row, so Spring Data's no-count-query-needed optimization (content size \< page size) short-circuits getTotalElements() to content.size() without ever running the separate count query DISTINCT would otherwise correct. If that is the mechanism, the keyword remains load-bearing for a page-filling result set (specialty match count >= page size) on any vendor, and this test's H2 run cannot see its absence — the same shape of vendor-invisible pass the design-block already named as a recorded risk on this exact query.
- ◆ **grade CONCERN** · narrow the vet directory to one specialty
  - blast_radius — **clear** — Ten files but one code package: two Java files and one Thymeleaf template in vet/, two test files, five docs. One module, no sensitive paths, no new route, no dependency or build change; the unfiltered read paths and the vets cache annotations are untouched.
  - semantic_surprise — **clear** — Read every production hunk and found no behavior the description would not predict: blank normalizes to null at the boundary, the unfiltered paging links still render /vets.html?page=N after the link-builder rewrite, the specialty is URL-encoded rather than concatenated, and Vet.specialties is EAGER so the new query path cannot fail on lazy init outside the view session. The discarded-and-reconstructed VetController and VetRepository are byte-identical to the round-1 approved tree (git diff 9d8799c 9a8733d touches only the two test files), so the reconstruction introduced nothing.
  - test_adequacy — **concern** — Coverage is broad and behavioral, but the test-reviewer's own round-2 finding says the Distinct guard is not pinned: the paged duplicate-specialty assertion short-circuits getTotalElements to content.size() because the result never fills the page, so the derived count query never runs and dropping Distinct would fail no test while double-counting a page-filling narrowed list on any vendor. Case-insensitivity is likewise proven only against H2, the vendor-invisible shape the design record named as a recorded risk on this exact query.
  - reviewer_hedging — **concern** — The round-2 approval that closed the roster carries an open clarify finding routed to the system-design-expert about the untested Distinct keyword, unaddressed at grading time; the security approval adds two recommendations, that no NVD/CVE matching ran in this review and that the specialty parameter carries no length bound before reaching the query and the rendered links.
  - scope_deviation — **clear** — The doc surface is wider than a filter — NG-9 narrowed, REQ-VET-004 minted, a Known Defects row retired, two ADRs added — but each widening traces to a quoted owner decision in the intake record, and the single design revision was a path-coverage correction to the design-block, not a design change. Two genuinely open choices (trimming a non-empty specialty, a visible control) are recorded as PRD open questions per the owner's no-further-answer instruction rather than decided in code.
  - why — No behavioral surprise survived a full read of the production diff, and the reconstructed files match the approved tree byte for byte. What is left for a human is one test gap the approving reviewer named and left open: the Distinct keyword is load-bearing for a page-filling narrowed list yet no test would fail without it. Read that finding and the repository query before merging.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**doc-reviewer**

- PRD Veterinarian directory section stays behavioral: no mechanism, code identifiers, or constants; every sentence under 30 words
- Both new ADRs stay under the 60-line guideline, carry Context/Options/Decision/Consequences/Implementation, and use the correct Non-goal vs Requirements Implementation line per their kind
- docs/adr/README.md index gained rows for both new ADRs in date order
- system-design.md Persistence section states the two new repository-read rules as contract prose (no field/parameter tables, no literal constants) and links the deciding ADR
- Contracts table rows for Vets, VetRepository, VetController correctly cite REQ-VET-003/REQ-VET-004; the retired Known Defects row for the machine-readable route is removed with a one-line note explaining the retirement
- Cross-references resolve: docs/prd.md#req-vet-003 anchor exists (explicit \<a id> at line 119), docs/prd.md#veterinarian-directory and docs/system-design.md#persistence resolve via heading slugs, and Specialty/Veterinarian terms are defined in ubiquitous-language.md
- Non-Goals table NG-9 narrowing and the PRD Superseded/Open Questions entries for REQ-VET-002/REQ-VET-004 are mutually consistent across prd.md, both ADRs, and system-design.md

**security-reviewer**

- Data-access injection: the filter reaches the database only through the Spring Data derived query findDistinctBySpecialtiesNameIgnoreCase(String[, Pageable]) on VetRepository. No query text is concatenated and no request-derived value reaches JPQL/SQL as literal text, satisfying docs/security-principles.md Realization row 'Injection into data access'.
- Cross-site scripting: the caller-supplied specialty is reflected into every paging href in src/main/resources/templates/vets/vetList.html, and each link is built with Thymeleaf's parameterized link expression @{/vets.html(page=..., specialty=${specialty})}. The link builder URL-encodes the value and th:href escapes the attribute; a test asserts '&' arrives as %26 and never raw. Output escaping is nowhere disabled (no th:utext, no unescaped inlining).
- Template-expression injection: the change removes the last expression-preprocessing hrefs (@{'/vets.html?page=__${i}__'}) from the file; a repository-wide grep for __${ in src/main/resources/templates/ now returns nothing, so no request-derived text can reach a preprocessed expression on this surface. This closes the risk the design record flagged rather than repeating it.
- Cache-key poisoning / unbounded memory: the two filtered reads carry no @Cacheable, so an unauthenticated caller cannot mint entries keyed on arbitrary text in the size- and eviction-unbounded 'vets' JCache. The unfiltered reads keep their existing annotations, so the pre-existing caching posture is unchanged.
- Request binding and mass assignment: the parameter binds as a plain @RequestParam String on both handlers; no new @InitBinder, no new bound command type, no identifier exposure. Blank normalization (StringUtils.hasText) happens at the controller boundary and cannot produce a wildcard or catch-all query.
- Exposed surface: no route is added. Both handlers are the existing /vets.html and /vets mappings gaining an optional parameter, so exposure is not broadened beyond the baseline in docs/system-design.md Security Context.
- Secrets, logging, and errors: the diff introduces no credential-like literal (grep over the diff for password/secret/token/key/credential returns nothing), no logging statement, no System.out/err, and no new exception message, so nothing new can reach the error page that renders exception text.
- Other classes checked and absent from the change: no file, path, or classpath resource is selected from request input; no deserialization entry point, @JsonTypeInfo, or polymorphic typing; no shell execution, reflection, regex, or network call; no new mutable state on the singleton controller (selectedSpecialty and findVets are stateless private helpers).

**code-quality-reviewer**

- ./gradlew checkFormat passes with no findings
- VetRepository's two new findDistinctBySpecialtiesNameIgnoreCase overloads mirror the existing findAll()/findAll(Pageable) split and carry precise Javadoc explaining the deliberate absence of @Cacheable and the reason for  Distinct , matching the ADR's stated rules
- VetController's selectedSpecialty/findPaginated/findVets helpers keep the null-means-unfiltered normalization localized and documented, delegate the actual filtering rule to the repository query rather than narrowing in-memory, and stay well under the ~30-line guideline
- vetList.html's narrowed/unnarrowed ternary per paging link is explained by an inline comment tying it to a verified Thymeleaf null-parameter rendering quirk, and uses the parameterized link expression (not string concatenation) so the specialty value is encoded
- No dead code, no swallowed exceptions, no logging concerns, no UTF-8 or mutable-record issues in the changed surface

**test-reviewer**

- Test names follow the BDD the{Subject}Should{Outcome} school and match the prd-entry's test_names list exactly
- Three-tier data naming is clean: RADIOLOGY, SPECIALTY_NO_VETERINARIAN_HOLDS, WHITESPACE_ONLY_SPECIALTY are named by role; no bare mystery literals introduced
- VetControllerTests continues the host file's existing @MockitoBean/MockMvc convention consistently, per the brief's tolerated-not-encouraged mock policy for pre-existing web-layer tests
- ClinicServiceTests additions use the real @DataJpaTest repository and real H2 fixture data rather than mocks, matching the brief's real-I/O-for-integration rule
- theVetListPagingLinksShouldEncodeTheSpecialty gives dedicated test coverage to the ADR-flagged URL-encoding risk (unescaped specialty text reflected into paging hrefs), and theVetListPagingLinksShouldOmitTheSpecialtyWhenNoneApplies guards the ADR-flagged risk of the unfiltered link format changing
- Case-insensitive and non-prefix matching are tested once at the repository layer (ClinicServiceTests) rather than duplicated at the controller layer, per the brief's Stop Re-Testing Other Units rule
- ./gradlew test passes for both changed test files; jacoco reports VetController fully covered (0 missed lines/branches)

**test-reviewer**

- Both round-1 findings are addressed at their cited locations: theVetListShouldShowOnlyOnceAVeterinarianHoldingTwoIdenticallyNamedSpecialties persists a vet with two same-named specialty rows via a real EntityManager and @Transactional fixture (no mocking) and asserts both the collection and paged reads return/count it exactly once; theVetListShouldIgnoreABlankSpecialtyValue and its JSON-surface counterpart are now @ParameterizedTest @ValueSource({EMPTY_SPECIALTY, WHITESPACE_ONLY_SPECIALTY}), covering the empty-string edge case the prd-entry names alongside whitespace-only
- New test follows four-phase structure with blank-line separation, straight-line code, no phase comments, and BDD naming consistent with the host file's the{Subject}Should{Outcome} school
- Hardcoded 'Ada'/'Nakamura' identity values in the new fixture helper match the host file's existing convention for irrelevant-identity literals (e.g. 'Sam'/'Schultz' at line 124-125), not a new mystery-literal pattern
- ./gradlew test passes for the full suite; both fix-delta test files build and run clean

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $6.63 | 24m 4s | 97% |
| `agent-team:system-design-expert` | 2 | opus-5 | $2.19 | 6m 2s | 92% |
| `(parent)` | 1 | opus-5 | $1.83 | 51m 15s | 96% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.71 | 5m 8s | 94% |
| `agent-team:change-grader` | 1 | opus-5 | $1.13 | 2m 54s | 89% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.08 | 6m 54s | 93% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.62 | 1m 17s | 87% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.46 | 1m 18s | 95% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.37 | 1m 34s | 89% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.86 | 13m 52s | 98% |
| `agent-team:feature-implementer` | opus-5 | $2.36 | 8m 54s | 97% |
| `(parent)` | opus-5 | $1.83 | 51m 15s | 96% |
| `agent-team:product-requirements-expert` | opus-5 | $1.71 | 5m 8s | 94% |
| `agent-team:system-design-expert` | opus-5 | $1.69 | 5m 5s | 93% |
| `agent-team:change-grader` | opus-5 | $1.13 | 2m 54s | 89% |
| `agent-team:security-reviewer` | opus-5 | $0.62 | 1m 17s | 87% |
| `agent-team:test-reviewer` | sonnet-5 | $0.55 | 4m 21s | 93% |
| `agent-team:test-reviewer` | sonnet-5 | $0.53 | 2m 32s | 93% |
| `agent-team:system-design-expert` | opus-5 | $0.50 | 57s | 86% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.46 | 1m 18s | 95% |
| `agent-team:feature-implementer` | opus-5 | $0.40 | 1m 17s | 90% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.37 | 1m 34s | 89% |

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

- plugin `agent-team-spring-boot` at `v0.3.2` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `064d588523591361` · `2.1.232 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
