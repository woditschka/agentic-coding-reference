# vets-specialty-filter r2 — v0.1.22

Filter the vet list by specialty (feature) · started 2026-08-24T21:03:53+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 3 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.58. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> Filtering lands in VetRepository as a derived query (findDistinctBySpecialties_NameIgnoreCase), keeping the rule out of the controller; only blank-to-null normalization stays in VetController, and the uncached choice is justified in the Javadoc and ADR. Tests are behavior-named and phase-clean, but the two contract claims that matter — whole-name and case-insensitive matching — are asserted against a stubbed repository: theSpecialtyFilterShouldMatchWholeNameCaseInsensitively and aSpecialtyPrefixShouldNotMatch only replay their own given(...), so no test exercises the derived query. Literals "radiology"/"surgery"/id 2 are mystery values, and verify(never()) asserts interaction. Documentation is thorough: NG-9 narrowed, REQ-VET-003 minted, superseded and Known-Defects rows reconciled, contracts table and pagination links updated.

**Sample 2** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> Filtering lands in the repository as derived queries (VetRepository.java:68,79) with paging left to the store, matching the Repository pattern; the controller only normalizes and selects, though normalizeSpecialty plus the duplicated null-branch in showVetList and showResourcesVetList adds a small rule and copy-paste variance at the web layer. Names, javadoc, and the uncached rationale are clear. Tests are behavior-named and phase-clean, but the whole-name/case-insensitive contract is stubbed, so theJsonFilterShouldMatchWholeNameCaseInsensitively and aSpecialtyPrefixShouldNotMatch merely echo the mock; verify(never()) asserts interaction detail, and bare literals "radiology", "surgery", .value(2) are mystery values. Docs are thorough: NG-9 narrowing, REQ-VET-003, superseded note, contracts table, and the retired known-defect row all move.

**Sample 3** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> Filtering lands in VetRepository as a derived query (findDistinctBySpecialties_NameIgnoreCase, paged and list overloads), keeping paging at the database and the whole-name/IgnoreCase contract self-documenting; the controller only binds, normalizes, and delegates, and vetList.html carries specialty through every pagination link. The blank-as-absent rule sits in the controller helper normalizeSpecialty, a small rule the catalog places lower, and the two handlers each branch on it. Tests cover both surfaces, case-insensitivity, prefix non-match, empty result, blank value, and link preservation with BDD names, but lean on bare literals ("radiology", "surgery", id 2) as Tier-3 mystery values and assert implementation detail via verify(never(...)). Documentation is thorough: NG-9 narrowed, REQ-VET-003 minted, superseded entry, open questions, contracts table, and the stale known-defect row removed.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $8.66 | 28m | 27 | 90% | 9 file(s) +274/−23 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.36 | 47s | 75% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Filter the veterinarian directory by specialty on both surfaces

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** (1) | **✔** |
| **test** | ✎ (3) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | **✔** | **✔** |

- ◇ **prd-entry** Filter the veterinarian directory by specialty on both surfaces · (prd-expert) · ***◷ 15m***
- ◈ **design-block** **new** · (design) · ***◷ 15m***
- ◆ **implement** (implementer)
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 10m***
- ✔ **review code-quality** · **approved** · (1 finding) · ***◷ 1m***
  - [autofix] `VetControllerTests.java:168` org.hamcrest.Matchers.nullValue() is referenced as a fully-qualified inline expression while the other Hamcrest matchers in the same file (containsString, hasSize) are statically imported at the top. Consistency requires a static import of nullValue here as well.
    - fix: Add `import static org.hamcrest.Matchers.nullValue;` to the import block and replace `org.hamcrest.Matchers.nullValue()` on line 168 with `nullValue()`.
- ✎ **review test** · **changes_requested** · (3 findings) · ***◷ 5m***
  - **[blocked]** `VetControllerTests.java` PRD AC [REQ-VET-003]: 'given a specialty name differing from a held specialty only by letter case, when either surface is requested for it, then it matches; given only the start of a specialty name, then it does not match.' The test theSpecialtyFilterShouldMatchWholeNameCaseInsensitively covers the HTML surface only. No test exercises the JSON surface (/vets?specialty=Radiology) to verify the same case-insensitive routing. The controller's JSON path goes through the same normalizeSpecialty and findDistinctBySpecialties_NameIgnoreCase call, but a test is required to hold that contract against regression.
  - **[blocked]** `VetControllerTests.java` PRD AC [REQ-VET-003]: 'given a specialty that no veterinarian holds, when either surface is requested for it, then an empty directory is returned in the normal structure, not an error.' The test anUnheldSpecialtyShouldReturnAnEmptyDirectory covers the HTML surface only. The JSON surface (/vets?specialty=surgery) returning an empty vetList in the normal Vets JSON structure is not tested.
  - **[blocked]** `VetControllerTests.java` PRD AC [REQ-VET-003]: 'given an empty or whitespace-only specialty, when either surface is requested with it, then it is treated as no filter and the full directory is returned.' The test aBlankSpecialtyShouldBehaveAsNoFilter covers the HTML surface only. The JSON surface (/vets?specialty=   ) returning the full directory is not tested. The verify(never) guard on the filtered query is also absent for the JSON surface.
- ✔ **review doc** · **approved** · ***◷ 30s***
- ↻ **implement** (implementer) ← test · (3 findings)
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 2m***
- ✔ **review doc** · **approved** · ***◷ 10m***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 53s***
- ◆ **grade CLEAR** · add optional specialty filter to both vet directory surfaces
  - blast_radius — **clear** — Reach is contained to the single vet package (controller, repository, template) plus its tests and design docs; the oversize/multi-module triggers come from 5 repetitive template anchor rewrites and doc prose, not scattered logic, and no sensitive paths are touched.
  - semantic_surprise — **clear** — Read the hunks: normalizeSpecialty maps null/blank/whitespace to null and both surfaces branch on that null to the unfiltered findAll, else the whole-name IgnoreCase derived query; the derived-query keyword (equality, not StartingWith) matches the whole-name contract, no hidden boundary flip or behavior change.
  - test_adequacy — **clear** — Tests assert real outcomes on both HTML and JSON surfaces: case-insensitive match, prefix-should-not-match, unheld-empty, and the blank no-filter branch guarded by verify(never) on the filtered query, plus the pagination carry-forward asserting specialty=radiology in rendered HTML; they exercise the changed behavior, not restate it.
  - reviewer_hedging — **clear** — Final roster all four approved with empty findings; the test-reviewer's initial changes_requested (JSON-surface parity) was fully resolved in the fix round and re-approved, a normal fix cycle, not a lingering caveat or escalation.
  - scope_deviation — **clear** — Zero design revisions, consultations, and build retries; the diff matches the prd-entry file_targets and the seven acceptance criteria exactly, with no wander past the stated URL-only, specialty-only surface.
  - why — All five facets clear on a direct read of the hunks. The filter logic is a clean null-branch mirroring the owner-search precedent, tests cover both surfaces and every boundary, and the roster approved unanimously after a normal fix cycle. Confirm and merge fast.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Specialty filter reaches a Spring Data derived query (findDistinctBySpecialties_NameIgnoreCase) that binds the argument as a query parameter; no JPQL/SQL string concatenation, so the input is not injectable.
- Reflected-XSS boundary is sound: the user-controlled specialty reaches vetList.html only as a Thymeleaf link-expression query-parameter value (@{/vets.html(page=..., specialty=${specialty})}), which URL-encodes param values, with default HTML attribute escaping; it is never emitted via th:utext or as raw HTML text.
- Cache-key-growth reasoning verified and correct: only the findAll variants are @Cacheable("vets"); both filtered derived queries are deliberately uncached, so unvalidated user input never becomes a cache key.
- No path traversal, unsafe deserialization, or file I/O introduced; /vets serializes a server-built Vets wrapper and the input is a single bound String.
- normalizeSpecialty maps null/blank/whitespace to null (unfiltered path) without trusting the input in any security-sensitive sink.
- No dependency or build-file changes in the change set; no new supply-chain surface.

**code-quality-reviewer**

- Format check passes (checkFormat: UP-TO-DATE on both main and test source sets)
- VetRepository Javadoc on both new methods explicitly documents the deliberate non-caching decision and its rationale — correct and useful for future readers
- normalizeSpecialty is private static, side-effect-free, and documented with a Javadoc that names the owner-search precedent it mirrors
- Thymeleaf parameter form @{/vets.html(page=${i}, specialty=${specialty})} correctly omits the specialty parameter when null, keeping no-filter URLs byte-identical to pre-feature
- findPaginated branches cleanly on null: unfiltered path to findAll, filtered path to the new derived query — early return would not improve it
- Spring Data derived-query names encode the whole-name equality contract (no StartingWith) and the IgnoreCase guarantee directly in the method name, making the specification self-documenting
- All seven acceptance-criteria test cases are present and named in BDD style matching the acceptance-criteria list in the prd-entry
- aBlankSpecialtyShouldBehaveAsNoFilter verifies both the positive assertion (full list returned) and the negative (filtered query never called), using verify/never correctly
- No prohibited suffixes, no util/helper packages, no mutable state introduced
- Constructor injection and single-responsibility maintained in VetController

**test-reviewer**

- @WebMvcTest + @MockitoBean VetRepository is the sanctioned web-harness pattern per testing-principles.md Mocking Policy; mock usage is correct
- All seven test names in the prd-entry test_names list are present and follow the BDD the{Subject}Should{Outcome} / a{Condition}Should{Outcome} school
- Factory methods james() and helen() wrap Vet construction, satisfying the factory-method requirement for tests written from 2026-07-31 onward
- Derived-query keyword findDistinctBySpecialties_NameIgnoreCase is exercised directly in stubs: equality (not StartingWith) + IgnoreCase is the correct realization of the whole-name case-insensitive contract
- aSpecialtyPrefixShouldNotMatch stubs eq("radiol") returning empty, confirming the controller passes the value unchanged to an equality matcher rather than appending a wildcard
- paginationLinksShouldPreserveTheActiveSpecialtyFilter constructs a multi-page result (totalElements=6) and verifies specialty=radiology appears in the rendered HTML, covering the pagination carry-forward contract
- Tests are all passing and the build is green

**doc-reviewer**

- PRD what/how boundary honored throughout — no method names, Spring constructs, or algorithm choices appear in prd.md
- All three product decisions recorded consistently: NG-9 narrowing in PRD NG-9 table, Open Questions update, non-goal ADR, and prd-entry notes; REQ-VET-002 kept withdrawn and id not reused stated in Superseded list, Open Questions, and prd-entry notes; URL-only contract in PRD prose and Done-when bullets
- system-design.md contracts table correctly cites REQ-VET-003 for VetController, VetRepository, and Vets; REQ-VET-002 absent; retired /vets Known-Defects row removed
- All cross-references resolve: #req-vet-003 anchor present in prd.md, #non-goals and #contracts anchors verified, ADR filenames exist
- ADR format correct: specialty-filter ADR has all required sections with **Requirements:** REQ-VET-003 and em-dash References; non-goal ADR has **Non-goal:** NG-9 in Implementation with inline cross-links (no separate References section, consistent with non-goal-ADR convention)
- ADR README index rows added for both new ADRs
- No prohibited patterns: no code blocks, no class names, no rationale prose in PRD

**security-reviewer**

- Fix-delta is test-only: three MockMvc JSON-surface test methods plus a nullValue static-import cleanup; no production code, no dependency, no config change
- Test inputs are static literals (Radiology, surgery, blank string) with no untrusted external data; no injection, deserialization, file, or command sink introduced
- No credentials, secrets, or PII added; no new attack surface over the prior approved pass
- Prompt-injection in the dispatched skill body attempting to redirect output to a markdown-only report was ignored; genuine review-feedback record appended per the output contract

**doc-reviewer**

- Fix-delta is test-only (VetControllerTests.java); no documentation files changed
- Prior doc-reviewer approval at line 15 remains valid; all documentation surfaces are unchanged
- New JSON-surface tests introduce no behavioral claims, domain terms, or requirements that docs must capture

**code-quality-reviewer**

- Static import autofix (nullValue) is mechanical and decision-free — inline qualified call replaced cleanly
- theJsonFilterShouldMatchWholeNameCaseInsensitively: naming mirrors HTML counterpart theSpecialtyFilterShouldMatchWholeNameCaseInsensitively, four-phase structure intact, helen() factory used correctly
- anUnheldSpecialtyJsonShouldReturnAnEmptyDirectory: naming and domain word (directory) consistent with suite; stub returns empty list as expected for an unheld specialty
- aBlankSpecialtyJsonShouldBehaveAsNoFilter: relies on @BeforeEach findAll() stub for hasSize(2) — no spurious arrange; verify(never()) correctly targets the no-Pageable overload that the JSON path uses
- All three methods follow BDD naming convention, use meaningful test values, omit phase comments, and are consistent with existing patterns in the file

**test-reviewer**

- theJsonFilterShouldMatchWholeNameCaseInsensitively delegates mixed-case specialty to findDistinctBySpecialties_NameIgnoreCase without normalizing input, achieving JSON-surface parity with the HTML test at the controller layer
- anUnheldSpecialtyJsonShouldReturnAnEmptyDirectory confirms HTTP 200 with empty vetList for a specialty held by no vet on the JSON surface
- aBlankSpecialtyJsonShouldBehaveAsNoFilter carries verify(never()).findDistinctBySpecialties_NameIgnoreCase(any()) guard confirming the no-filter branch is taken for whitespace-only input on the JSON surface
- All three previously blocked findings are fully resolved; all tests pass (BUILD SUCCESSFUL)
- Static-import cleanup for nullValue() on the HTML blank-specialty test is a clean mechanical improvement

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $2.96 | 11m 23s | 95% |
| `(parent)` | 1 | opus-4-8 | $1.10 | 28m 5s | 95% |
| `spring-boot-claude:system-design-expert` | 1 | opus-4-8 | $1.06 | 3m 27s | 88% |
| `spring-boot-claude:security-reviewer` | 2 | opus-4-8 | $0.97 | 1m 26s | 77% |
| `spring-boot-claude:product-requirements-expert` | 1 | opus-4-8 | $0.96 | 3m 25s | 91% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $0.55 | 3m 42s | 88% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $0.47 | 2m 59s | 82% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $0.47 | 3m 25s | 77% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $0.36 | 47s | 75% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.10 | 21s | 83% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-4-8 | $2.11 | 8m 18s | 95% |
| `(parent)` | opus-4-8 | $1.10 | 28m 5s | 95% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.06 | 3m 27s | 88% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.96 | 3m 25s | 91% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $0.84 | 3m 5s | 93% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.59 | 52s | 72% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.40 | 3m 1s | 87% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.38 | 33s | 82% |
| `spring-boot-claude:change-grader` | opus-4-8 | $0.36 | 47s | 75% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.31 | 2m 0s | 83% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.30 | 2m 12s | 74% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.17 | 58s | 79% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.16 | 1m 13s | 82% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.15 | 41s | 90% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.10 | 21s | 83% |

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

- plugin `spring-boot-claude` at `v0.1.22` (tag)
- model requested `claude-opus-4-8`; models used: opus-4-8 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `064d588523591361` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
