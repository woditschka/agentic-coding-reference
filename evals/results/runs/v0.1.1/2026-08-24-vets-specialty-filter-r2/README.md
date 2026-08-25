# vets-specialty-filter r2 — v0.1.1

Filter the vet list by specialty (feature) · started 2026-08-24T19:51:50+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 3 (±0) | 4 (±0) | 4 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.62. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 4

> Filtering is pushed into VetRepository as derived queries (findBySpecialtiesNameIgnoreCase) and the controller only binds, delegates, and selects — the Web controller row holds; normalizeSpecialty is request adaptation mirroring empty owner search, not a new business rule. Minor debt: the null-branch is duplicated in findPaginated and showResourcesVetList, and both new methods reuse the shared @Cacheable("vets") region across differently-shaped results and case-variant keys. Tests are behavior-named and cover every done-when clause, but ClinicServiceTests.theSpecialtyNarrowingShouldMatchIgnoringCase packs two act/assert cycles into one test, and "radiology", hasSize(2), and vetList[0].id == 2 are mystery values tied to seed data, with no factories or named constants. Docs move broadly (ADR, index, NG-9, REQ-VET-003, contracts, defect row retired); the Vets row still reads Implements "—".

**Sample 2** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 4

> Repository-derived  findBySpecialtiesNameIgnoreCase  keeps matching in the persistence layer, and the controller only binds, normalizes, and delegates — a good layer fit; the blank-is-absent  normalizeSpecialty  is arguably binding, not a domain rule, though the null-branch is duplicated across both handlers and both new queries reuse the single  @Cacheable("vets")  region without stated key semantics. Tests are well-named BDD specifications covering empty, blank, absent, no-match, and pagination-carry, but rely on Mockito stubs and bare literals ( "radiology" ,  hasSize(2) ,  jsonPath(...id).value(2) ), and  theSpecialtyNarrowingShouldMatchIgnoringCase  bundles two act/assert cycles. Docs are unusually complete (ADR, NG-9 narrowing, REQ-VET-003, defect row retired), but the  Vets  contract row still shows  Implements: —  after the JSON surface was reinstated.

**Sample 3** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 4

> Filtering lands in VetRepository as derived queries ( findBySpecialtiesNameIgnoreCase ), with VetController only binding, normalizing blank input and delegating — right layer, matching the existing Vet* seams; the null-branch is duplicated across  findPaginated  and  showResourcesVetList , and both new repository methods reuse the shared  @Cacheable("vets")  region without comment. Controller tests are behavior-named ( theVetDirectoryPageShouldListOnlyVetsHoldingTheSpecialty ) and phase-clean, but new tests reach for Mockito  given  rather than a real or hand-written double, and literals are mysteries:  hasSize(2) ,  PageRequest.of(0, 5), 7 ,  vetList[0].id = 2 ;  theSpecialtyNarrowingShouldMatchIgnoringCase  packs two act/assert pairs into one test on shared seed data. Docs are thorough — NG-9 narrowed, REQ-VET-003 minted, defect row retired, ADR added — but the  Vets  contract row still reads  Implements: —  though it now serves REQ-VET-003.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.06 | 32m | 17 | 90% | 9 file(s) +230/−22 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.50 | 1m 19s | 85% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Filter the veterinarian directory by specialty

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | · |
| **doc** | ✎ (3) | **✔** |

- ◇ **prd-entry** Filter the veterinarian directory by specialty · (prd-expert) · ***◷ 0s***
- ◈ **design-block** **minor** · (design) · ***◷ 1m***
- ◆ **implement** (implementer)
  - ▲ **build ✓ clean** · build · test · format · check
- ✔ **review security** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 9m***
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 5m***
  - [clarify] `ClinicServiceTests.java — all 8 new te` All 8 new test method names were copied verbatim from the prd-entry test_names field (e.g., specialtyNarrowingIsCaseInsensitive, blankSpecialtyIsTreatedAsAbsent), but testing-principles.md § Test Naming requires the the{Subject}Should{Outcome} school for tests written from 2026-07-31 onward. The PRD-specified names are behavior-descriptive noun phrases rather than subject-outcome pairs. Either the PRD test_names should be updated to follow the convention, or an explicit exception for PRD-mandated test names should be added to the testing brief. The feature-implementer correctly followed what the PRD specified; resolution belongs with the PRD author.
  - [clarify] `VetControllerTests.java:128-155, :157-` Three tests (unknownSpecialtyReturnsEmptyDirectoryWithOkStatus, blankSpecialtyIsTreatedAsAbsent, noSpecialtyParamPreservesExistingBehavior) each make two separate mockMvc.perform() calls exercising the HTML and JSON surfaces independently. testing-principles.md § Tests Are Specifications says one logical assertion per test. The prd-entry mapped a single test_name to each acceptance criterion that explicitly covers both surfaces, creating structural pressure to combine two distinct HTTP interactions in one method. A failure in such a test does not immediately indicate which surface is broken. The appropriate fix — splitting each dual-surface test into two surface-specific methods — requires the PRD to accept two test_names per criterion, which is a PRD-granularity decision.
- ✎ **review doc** · **changes_requested** · (3 findings)
  - [autofix] `prd.md:123` Compound sentence with two semicolons runs approximately 60 words, exceeding the 30-word limit. Breaks into three sentences by splitting at the semicolons.
    - fix: A name that no veterinarian holds narrows the directory to nothing, returned as a normal, empty directory rather than as a failure. A blank or whitespace-only name is treated as no narrowing, exactly as an empty owner search is. A request that names no specialty behaves as the directory did before it could be narrowed.
  - [clarify] `prd.md:47` NG-9 narrowing clause uses a dated marker and a REQ link but no ADR link. NG-4 and NG-5 set the convention: each confirmed scope decision carries a dated marker plus an ADR back-link. The narrowing of NG-9 is a scope-change decision of comparable weight — admitting part of a non-goal into scope — and would benefit from the same ADR anchor. Does the NG-9 narrowing warrant a dedicated ADR, or is the REQ-VET-003 prd-entry record considered sufficient?
  - [clarify] `system-design.md:103-104,207` Now that build-pass exists for REQ-VET-003, three cells in system-design.md are stale: VetController Implements lists only REQ-VET-001 (line 104), VetRepository Implements lists only REQ-VET-001 (line 103), and the Known Defects row (line 207) still says the /vets route serves no requirement and is pending removal. The design-block record flagged these as post-implementation doc-sync work. Implementation is now done; these cells should be updated via the doc-sync pass before merge.
- ◈ **design-block** **minor** · (design) · supersedes L4
- ↻ **fix prd-expert** ← test, doc · (5 findings)
- ◇ **prd-entry** Filter the veterinarian directory by specialty · (prd-expert) · ***◷ 1m***
- ◆ **implement** (implementer)
  - ▲ **build ✓ clean** · build · test · format · check
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 6m***
- ◆ **grade CLEAR** · add specialty filter to the vet directory
  - blast_radius — **clear** — Contained to the vet module (controller, repository, one template) plus docs; no sensitive paths; the 30-hunk count is inflated by per-link template edits and docs, and the reach is a single read-only public feature surface.
  - semantic_surprise — **clear** — The diff does exactly what it advertises: normalizeSpecialty strips blank-to-null, findPaginated and the JSON route branch null->findAll else the IgnoreCase filter, and the template threads specialty through pagination links via URL-encoding link expressions; no inverted branch, off-by-one, or hidden behavior change.
  - test_adequacy — **clear** — The whole-name and case-insensitive boundary the code changed is exercised against real H2 in ClinicServiceTests (prefix 'radiolog' -> empty, 'RADIOLOGY' -> 2), and the controller tests assert real outcomes including the pagination-carry response body containing specialty=radiology and eq('radiology') confirming normalization; not tautological.
  - reviewer_hedging — **clear** — All four final approvals carry empty findings lists; the first-round test and doc changes_requested (naming convention, dual-surface split, doc-sync) were fully resolved by a PRD supersede plus doc-sync and re-approved clean, leaving no lingering caveat on the approving verdicts.
  - scope_deviation — **clear** — consultations=0, build_retries=0; the single design_revision is the doc-sync second design-block the first one explicitly anticipated, not a triage fight, and the diff stays on the PRD file_targets plus the anticipated ADR and doc-sync cells.
  - why — Read every hunk: a textbook extension of the owner-search filter+pagination pattern, contained to the vet module, with real boundary tests against H2 and unhedged unanimous approval. Confirm and merge; the pagination-carry template threading is the only line worth a glance.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Specialty flows into a Spring Data derived query (findBySpecialtiesNameIgnoreCase) bound as a JPA parameter (upper(name)=upper(?)); no string concatenation, no SQL/JPQL injection surface.
- Specialty is emitted only into pagination URLs via Thymeleaf @{/vets.html(...,specialty=${specialty})} link expressions, which URL-encode query-parameter values and auto-escape the href attribute context; specialty is never rendered as raw HTML text, so no reflected XSS.
- normalizeSpecialty strips input and treats blank/whitespace as absent, mirroring the owner-search pattern; untrusted request input is handled safely with no unsafe sinks.
- No auth/authz change: the vet directory and machine-readable list remain the same public read-only surface as before; no secrets, deserialization, or path/command sinks introduced.

**code-quality-reviewer**

- normalizeSpecialty helper extracted to a named private method and called from both routes — no logic duplication, Javadoc is accurate and complete
- VetRepository new methods carry correct Spring Data derived-query names (IgnoreCase suffix), matching Javadoc, and the same @Transactional/@Cacheable annotations as the existing findAll siblings
- findPaginated branches on null specialty cleanly with an early return; single responsibility preserved
- vetList.html threads specialty=${specialty} through every pagination link; Thymeleaf null-param-dropping correctly handles the no-filter case without additional template branching
- normalizeSpecialty null-to-null and whitespace-to-null normalization mirrors the intent of OwnerController processFindForm (grep-confirmed, IDE oracle not connected); deviation from inline to extracted helper is justified by dual call sites
- No prohibited naming suffixes, no abbreviations, no type-name repetition in method names

**test-reviewer**

- All 8 PRD-specified test_names are present and match exactly
- Both HTTP surfaces (HTML and JSON) are covered for all applicable behaviors
- Case-insensitive matching and whole-name-not-prefix behaviors tested against real H2 via ClinicServiceTests @DataJpaTest
- Factory methods james() and helen() wrap Vet construction, meeting the testing brief factory-method requirement
- AssertJ fluent assertions used in ClinicServiceTests; Spring MVC result matchers appropriate for controller tests
- No new mock infrastructure introduced — the 6 new controller tests rely on the existing @MockitoBean VetRepository that the brief classifies as tolerated pre-existing usage
- All 8 new tests pass with 0 failures and 0 skips; build green

**doc-reviewer**

- REQ-VET-003 requirement entry follows the established lightweight PRD variant correctly — narrative prose with tagged Done-when bullets
- Both anchors (\<a id="req-vet-001">\</a>\<a id="req-vet-003">\</a>) are present at the Veterinarian directory section head
- REQ-VET-002 withdrawn-ID discipline is correctly maintained: superseded entry updated to explain reinstatement as a surface under REQ-VET-003 without reusing the id
- NG-9 narrowing includes a dated clause and links to REQ-VET-003, and the residual non-goal (free-text vet search) is explicit
- Two open questions for deferred scope (visible control, multi-specialty) are correctly appended in the Open Questions section
- All REQ-VET-003 cross-references in NG-9, Superseded, and Open Questions sections resolve to the anchor at line 119
- No Java code, pseudocode, algorithm formulas, or implementation constructs appear in the PRD
- Acceptance criteria in the Done-when list match the prd-entry acceptance_criteria verbatim

**doc-reviewer**

- Resolution 1 (autofix docs/prd.md:123): the compound sentence is now three sentences matching the fix field verbatim; each sentence is under 30 words and the paragraph remains coherent
- Resolution 2 (clarify docs/prd.md:47): docs/adr/2026-08-24-non-goal-vet-directory-specialty-filter.md is present, well-formed (Context / Options / Decision / Consequences / Implementation with **Non-goal:** NG-9), and listed in docs/adr/README.md; the NG-9 row back-link uses em-dash + ADR link matching the NG-4/NG-5 convention exactly
- Resolution 3 (clarify docs/system-design.md stale cells): VetController and VetRepository Implements cells now carry REQ-VET-001, REQ-VET-003; the Known Defects row asserting /vets serves no requirement and is pending removal is retired
- brief_doctor.py check: 0 failures, 39 checks — structural validation passes; new ADR conforms; 16 REQ-ID citations all defined

**test-reviewer**

- All 9 VetControllerTests and 2 ClinicServiceTests methods follow the{Subject}Should{Outcome} naming school, resolving the prior clarify findings
- Three dual-surface behaviors (empty result, blank specialty, no specialty) are each split into one test per surface (HTML page and machine-readable list), resolving the prior dual-surface granularity clarify finding
- All 11 PRD acceptance criteria have dedicated test coverage; AC12 (no on-screen control) is a non-goal check correctly omitted
- Mocking usage in VetControllerTests is the tolerated existing-suite pattern in a @WebMvcTest context, per testing-principles.md § Mocking Policy; ClinicServiceTests uses real @DataJpaTest JPA with no mocks
- Test gate is green: BUILD SUCCESSFUL, all tests pass

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $3.87 | 11m 30s | 95% |
| `spring-boot-claude:system-design-expert` | 2 | opus-4-8 | $1.91 | 4m 36s | 86% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $1.71 | 4m 45s | 87% |
| `(parent)` | 1 | opus-4-8 | $1.40 | 33m 0s | 89% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $0.71 | 5m 5s | 84% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $0.57 | 4m 27s | 86% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $0.50 | 1m 19s | 85% |
| `spring-boot-claude:security-reviewer` | 1 | opus-4-8 | $0.45 | 1m 1s | 82% |
| `spring-boot-claude:code-quality-reviewer` | 1 | sonnet-4-6 | $0.32 | 2m 40s | 86% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.09 | 21s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-4-8 | $2.44 | 8m 33s | 96% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.44 | 2m 57s | 94% |
| `(parent)` | opus-4-8 | $1.40 | 33m 0s | 89% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.12 | 2m 17s | 91% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.86 | 2m 9s | 86% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.85 | 2m 36s | 89% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $0.79 | 2m 19s | 69% |
| `spring-boot-claude:change-grader` | opus-4-8 | $0.50 | 1m 19s | 85% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.45 | 1m 1s | 82% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.40 | 3m 14s | 84% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.35 | 3m 13s | 84% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.32 | 2m 40s | 86% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.31 | 1m 50s | 84% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.23 | 1m 14s | 87% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.09 | 21s | 50% |

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

- plugin `spring-boot-claude` at `v0.1.1` (tag)
- model requested `claude-opus-4-8`; models used: opus-4-8 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `064d588523591361` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
