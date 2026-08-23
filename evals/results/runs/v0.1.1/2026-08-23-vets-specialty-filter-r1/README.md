# vets-specialty-filter r1 — v0.1.1

Filter the vet list by specialty (feature) · started 2026-08-23T03:12:57+00:00 · exec `claude-dev` · status **complete**

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
| 2 (±0) | 4 (±0) | 3 (±0) | 5 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.56. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 2 · test-quality 4 · maintainability 3 · doc-fit 5

> The whole-name case-insensitive match and hand-rolled paging (filterBySpecialty, the subList/PageImpl block in findPaginated) are a new business rule inside VetController — precisely what the checklist bars ("A new rule added to a controller is a fresh violation"), with Repository or Domain service available and no ADR or open question recording the deviation; the trim/hasText normalization is also duplicated across both handlers. Tests improve markedly: the Mockito bean is replaced by a hand-written InMemoryVetRepository, names follow the{Subject}Should{Outcome}, and aVetHolding is a real factory — but several tests exercise both surfaces in one method, and PAGE_SIZE=5 silently mirrors the controller. Docs are complete: ADR, index, NG-9 narrowing, REQ-VET-003, superseded note, contracts row, defect row removed. The "see design-block" comment points nowhere visible.

**Sample 2** — design-fit 2 · test-quality 4 · maintainability 3 · doc-fit 5

> The filter rule lands squarely in the web controller: VetController.filterBySpecialty plus hand-rolled paging (subList/PageImpl in findPaginated) is business logic and query mechanics in an entry point, exactly the fresh-controller-rule violation the checklist bars, when Repository is an in-force pattern. It also loads every vet per filtered request and duplicates the  hasText(...) ? trim() : null  normalization in both handlers; the comment citing a "design-block for REQ-VET-003" points at nothing in the patch. Tests improve markedly: hand-written InMemoryVetRepository replaces Mockito, aVetHolding factory, named counts, BDD names. But most tests perform two requests (HTML and JSON) in one method, breaking four-phase structure and one-concern. Documentation is thorough and consistent throughout.

**Sample 3** — design-fit 2 · test-quality 4 · maintainability 3 · doc-fit 4

> The filter is a new business rule placed in a web controller, which the architecture brief bars explicitly ("a new rule added to a controller is a fresh violation"): VetController.filterBySpecialty plus hand-rolled paging (start/subList/PageImpl in findPaginated) belongs in the repository or a domain service, and the normalization  StringUtils.hasText(specialty) ? specialty.trim() : null  is duplicated across both handlers. The comment citing a "design-block for REQ-VET-003" points at nothing in the patch. Tests are strong: the mock framework is replaced by a hand-written InMemoryVetRepository, names read as specifications, aVetHolding is a factory, RADIOLOGY_PAGES is derived — though several tests exercise two surfaces in one method and "cardiology" is a bare literal. Documentation is thorough: ADR, index, NG-9 narrowing, REQ-VET-003, superseded note, retired defect row, open question.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $10.04 | 27m | 1 | 90% | 7 file(s) +255/−58 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.81 | 2m 31s | 91% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Filter the veterinarian directory by specialty on both surfaces

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (2) | **✔** |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | · |
| **doc** | ✎ (3) | **✔** |

- ◇ **prd-entry** Filter the veterinarian directory by specialty on both surfaces · (prd-expert) · ***◷ 18s***
- ◈ **design-block** **minor** · (design) · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 20m***
  - ▲ **build ✓ clean** · build · test · format · check
- ✔ **review security** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 10m***
  - **[blocked]** `VetControllerTests.java:theSpecialtyFi` The test only exercises /vets.html?specialty=RADIOLOGY. PRD acceptance criterion 3 explicitly says the case-insensitive match must hold on both the page and the machine-readable list ("when the page or the machine-readable list is filtered by it, then it matches"). The /vets?specialty=RADIOLOGY JSON surface is untested. The implementation uses a shared filterBySpecialty helper, so the risk of divergence is low, but a future refactor that introduces a surface-specific code path would break the contract silently — no test would catch it.
    - fix: Add a second mockMvc.perform call for get("/vets").param("specialty", RADIOLOGY.toUpperCase()).accept(MediaType.APPLICATION_JSON) and assert jsonPath("$.vetList.length()").value(RADIOLOGY_VET_COUNT) in theSpecialtyFilterShouldMatchCaseInsensitively, mirroring the pattern already used in theBlankSpecialtyShouldBehaveAsAbsent.
  - **[blocked]** `VetControllerTests.java:theSpecialtyFi` The test only exercises /vets.html?specialty=radio. PRD acceptance criterion 4 says the prefix must match no veterinarian on either form ("when either form is filtered by it, then it matches no veterinarian"). The /vets JSON surface is untested for prefix non-match. Same refactor-risk argument applies as finding 1.
    - fix: Add a second mockMvc.perform call for get("/vets").param("specialty", RADIOLOGY.substring(0, 5)).accept(MediaType.APPLICATION_JSON) and assert jsonPath("$.vetList.length()").value(0) in theSpecialtyFilterShouldNotMatchOnPrefix.
- ✎ **review code-quality** · **changes_requested** · (2 findings) · ***◷ 5m***
  - [autofix] `VetController.java:70` The in-memory filter path (filterBySpecialty over findAll()) is not self-evidently correct. A cold reader will reasonably ask why a repository query was not added instead. The design-block for REQ-VET-003 records the reasons: a per-value repository query would create unbounded cache entries keyed by user-supplied specialty values and case variants; a vendor-level query would reproduce the PostgreSQL case-sensitivity collation defect on a new surface. Neither reason is visible in the code.
    - fix: Add a one-line comment immediately before the filterBySpecialty call: // Filter in memory: avoids unbounded per-value cache entries and vendor collation divergence (see design-block for REQ-VET-003).
  - [autofix] `VetController.java:51` The specialty value stored in the model, and thereby carried in all paging link URLs, is the raw (untrimmed) parameter string. filterBySpecialty trims internally, so filtering is correct, but paging URLs will contain encoded leading/trailing whitespace in the edge case where the caller supplied them. Trimming once at the handler entry point and using the trimmed value for both the model attribute and findPaginated would consolidate the concern in one place and make filterBySpecialty trivially correct without its own trim.
    - fix: Replace lines 50-52 with: String activeSpecialty = StringUtils.hasText(specialty) ? specialty.trim() : null; Page\<Vet> paginated = findPaginated(page, activeSpecialty); model.addAttribute("specialty", activeSpecialty);
- ✎ **review doc** · **changes_requested** · (3 findings) · ***◷ 7m***
  - **[blocked]** `prd.md lines 123-143` REQ-VET-003 is missing a mandatory Design Rationale link. The prd-authoring skill states Design Rationale is mandatory whenever an ADR records the decision behind the requirement. The non-goal ADR (2026-08-23-non-goal-veterinarian-search.md) records the boundary decision that admits specialty filtering into scope. A reader who navigates directly to REQ-VET-003 via a cross-reference from system-design.md finds no path to that decision document. The NG-9 preamble references the ADR but is not a substitute for a per-requirement link where the format spec requires one.
  - [autofix] `2026-08-23-non-goal-veterinarian-searc` One sentence in the Context section exceeds the 30-word limit (37 words). Writing standards require sentences under 30 words: Filtering a list by a value it already displays is not the same capability as free-text search: it demonstrates a query the directory does not yet show, without reintroducing the paged prefix-search pattern owner search already teaches.
    - fix: Filtering a list by a value it already displays is not the same capability as free-text search. It demonstrates a query the directory does not yet show, without reintroducing the paged prefix-search pattern owner search already teaches.
  - **[escalate]** `CLAUDE.md` CLAUDE.md documents Gradle task names formatJava and checkJavaFormat, but the build-pass record for this slice (handoff.jsonl line 6) shows the actual gate task names as format and check. If the discrepancy is real, CLAUDE.md carries stale task names that will mislead any agent running the quality gate. CLAUDE.md is outside the doc-reviewer scope (which covers docs/ only) so this escalates rather than routing to a named agent. A human should verify the actual Gradle task names and update CLAUDE.md if needed.
- ↻ **fix prd-expert** ← doc · (3 findings)
- ↻ **implement** (implementer) ← test, code-quality · (4 findings) · ***◷ 15m***
  - ▲ **build ✓ clean**
- ✔ **review test** · **approved** · ***◷ 5m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ◆ **grade CLEAR** · filter vet list by specialty on /vets.html and /vets
  - blast_radius — **clear** — True slice is one controller, one Thymeleaf template, one test, plus four docs; code stays inside the vet module with no sensitive paths. The row overcounts (11 files/98 hunks) only because base b67f301 pulls in the unrelated harness-install commit a7d7cb6 (settings.json, .gitignore, CLAUDE.md, layout.toml); those are not this slice.
  - semantic_surprise — **clear** — Read every hunk: filterBySpecialty uses equalsIgnoreCase for whole-name case-insensitive non-prefix matching; the in-memory paging path guards subList bounds (start>=size to empty, Math.min for end) and builds PageImpl with filtered.size() so page counts reflect matches; blank/whitespace resolves to null via hasText and takes the unchanged early-return path. No inverted operator, off-by-one, or hidden behavior change.
  - test_adequacy — **clear** — Tests replace MockitoBean with a real seeded InMemoryVetRepository (no-mocks compliant) and assert discriminating outcomes: totalItems counts, jsonPath lengths, both HTML and JSON surfaces for case-insensitive and prefix-non-match, blank-as-absent, and the paging link carrying specialty=radiology. They would fail on a filter regression.
  - reviewer_hedging — **clear** — Final round is clean unanimous approval with empty findings from all four reviewers; round-1 changes were fixable/autofix and re-approved. The lone escalate tag concerns CLAUDE.md gradle task-name drift (formatJava/checkJavaFormat vs format/check) in a harness-install file outside this slice, explicitly parked for a human, not a reservation about the slice.
  - scope_deviation — **clear** — design_revisions=0, consultations=0, build_retries=0. Change matches the requirement surface; VetRepository was listed in file_targets but correctly left unchanged under the in-memory design (a within-scope narrowing, not a wander).
  - why — Read all hunks: a contained, correct-shaped specialty filter over the cached collection with discriminating tests on both surfaces and clean final approvals. One caveat for the human, not against the slice: the extractor base included harness-install commit a7d7cb6, inflating the row (11 files/98 hunks) and surfacing a real-but-out-of-slice CLAUDE.md task-name discrepancy worth a separate look. Confirm and merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- No SQL injection: filterBySpecialty compares the user-supplied specialty in-memory via equalsIgnoreCase over vetRepository.findAll() (no-arg); the value reaches no query on either surface
- No unbounded/user-controlled cache keys: @Cacheable is keyed on the no-arg findAll(); filtering is in-memory so no per-value/case/page cache entries are created
- No reflected XSS in paging links: specialty flows only into Thymeleaf @{...(specialty=${specialty})} URL expressions, which URL-encode query params and auto-escape attribute output; blank/whitespace maps to null and the param is omitted
- Machine-readable /vets does not reflect the specialty into its JSON output
- No dependency delta: build.gradle unchanged in the diff, so no new supply-chain surface

**test-reviewer**

- No mock framework used; @MockitoBean replaced with hand-written InMemoryVetRepository via @TestConfiguration — compliant with the no-mocks policy
- All 8 test method names follow the project BDD school (the{Subject}Should{Outcome})
- Meaningful constants RADIOLOGY, SURGERY, RADIOLOGY_VET_COUNT, SURGERY_VET_COUNT, TOTAL_VET_COUNT named by role; RADIOLOGY_PAGES is correctly derived from inputs rather than hard-coded
- Factory methods seededVets() and aVetHolding() wrap production constructors per the testing principles
- Each test would fail on a filter regression: totalItems and vetList.length() assertions are discriminating against the seeded counts
- The blank/whitespace-as-absent and no-match-returns-200 tests both cover HTML and JSON surfaces
- InMemoryVetRepository correctly implements both findAll() and findAll(Pageable) with immutable internal state (List.copyOf)
- Tests are straight-line, no branching or loops in test bodies
- Pyramid fit: @WebMvcTest integration tests are appropriate given business logic lives in the controller (noted gap in testing-principles.md)

**code-quality-reviewer**

- filterBySpecialty uses a stream pipeline with equalsIgnoreCase — correct whole-name case-insensitive match per PRD
- PageImpl constructed with filtered.size() as total-element count — page count correctly reflects only matching vets
- StringUtils.hasText used consistently at both handler entry points to treat null, empty, and whitespace-only as absent
- Math.min(start + pageSize, filtered.size()) and start >= filtered.size() guards are correct subList bounds
- Early return for the no-specialty path preserves the pre-existing paginated repository query unchanged
- filterBySpecialty accepts Collection\<Vet> rather than List\<Vet> — correctly widened for both call sites
- vetList.html paging links use Thymeleaf @{/vets.html(page=${i},specialty=${specialty})} URL expressions that omit null params — correct approach for the no-specialty case
- Constructor injection, no @Autowired — follows Spring Boot idiom
- No prohibited naming suffixes, no abbreviations, no type-name repetition in method names

**doc-reviewer**

- REQ-VET-003 HTML anchor present and correct
- NG-9 row narrowed correctly with dated update, ADR reference, and behavioral boundary stated
- REQ-VET-002 Superseded entry carries correct forward-pointer to REQ-VET-003 with withdrawal rationale preserved
- Open Question about a possible visible specialty control recorded as unresolved
- New ADR satisfies all required sections: Status, Context, Options Considered, Decision, Consequences, Implementation with Non-goal: NG-9
- ADR uses non-goal filename convention and Implementation section uses Non-goal: NG-9 as required
- adr/README.md index row added in correct table format
- system-design.md Contracts table updated: Vets row Implements now REQ-VET-003; VetController now REQ-VET-001 plus REQ-VET-003 with filter noted
- Stale Known Defects row removed for /vets
- No PRD boundary violations: no code blocks, no Java-specific constructs, no internal type or method references in prd.md
- Cross-document coherence: every REQ-ID in system-design.md exists in prd.md; no withdrawn REQ-VET-002 reference remains in system-design.md
- All cross-reference links checked and resolve to valid anchors
- REQ-VET-003 behavioral prose correctly states whole-name case-insensitive matching, blank-equals-absent, paging carries specialty, no on-screen control added
- system-design.md VetController Purpose stays at behavioral level with no parameter tables or constant literals

**test-reviewer**

- Finding 1 resolved: theSpecialtyFilterShouldMatchCaseInsensitively now includes a second mockMvc.perform on GET /vets with Accept: application/json, asserting $.vetList.length() equals RADIOLOGY_VET_COUNT — both surfaces are exercised
- Finding 2 resolved: theSpecialtyFilterShouldNotMatchOnPrefix now includes a second mockMvc.perform on GET /vets with Accept: application/json, asserting $.vetList.length() equals 0 — both surfaces are exercised for prefix non-match
- No mocks introduced: InMemoryVetRepository via @TestConfiguration remains the sole repository implementation; no Mockito or mock library usage
- No new test-quality issues: both additions follow the existing straight-line pattern, no branching, assertion style and naming unchanged
- All 8 VetControllerTests tests pass (./gradlew test --tests VetControllerTests BUILD SUCCESSFUL)

**doc-reviewer**

- Finding 1 resolved: REQ-VET-003 now carries mandatory Design Rationale link (docs/prd.md line 127) pointing to the non-goal ADR, placed after the behavioral prose and before the Done-when block, per prd-authoring lightweight-variant format
- Finding 2 resolved: the 37-word sentence in docs/adr/2026-08-23-non-goal-veterinarian-search.md Context section (line 9) is split into two sentences (17 words and 20 words), both under the 30-word limit
- CLAUDE.md Gradle task-name discrepancy treated as escalated-to-human per prior escalate finding; not re-raised as a blocker on this slice
- No new documentation issues introduced by the fix

**code-quality-reviewer**

- Design-rationale comment present before filterBySpecialty call (lines 71-72) explaining in-memory filter choice
- Trim consolidated at handler entry in both showVetList and showResourcesVetList; model attribute and findPaginated both receive pre-trimmed value
- Blank/whitespace specialty correctly resolves to null via StringUtils.hasText, routing to the all-vets early-return path
- filterBySpecialty simplified correctly; no internal trim needed given pre-trimmed callers
- No new quality issues introduced: methods are single-responsibility, stream pipeline idiomatic, early return pattern clean

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $2.67 | 9m 31s | 92% |
| `(parent)` | 1 | opus-4-8 | $1.82 | 29m 18s | 95% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $1.69 | 5m 7s | 87% |
| `spring-boot-claude:system-design-expert` | 1 | opus-4-8 | $1.29 | 3m 47s | 89% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $0.81 | 2m 31s | 91% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $0.72 | 4m 45s | 88% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $0.63 | 4m 25s | 91% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $0.60 | 3m 36s | 83% |
| `spring-boot-claude:security-reviewer` | 1 | opus-4-8 | $0.49 | 50s | 82% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.09 | 18s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-4-8 | $1.82 | 29m 18s | 95% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.81 | 7m 11s | 93% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.29 | 3m 47s | 89% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.20 | 3m 51s | 91% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $0.86 | 2m 20s | 91% |
| `spring-boot-claude:change-grader` | opus-4-8 | $0.81 | 2m 31s | 91% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.51 | 3m 59s | 89% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.49 | 1m 16s | 72% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.49 | 50s | 82% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.43 | 2m 50s | 82% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.39 | 3m 0s | 88% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.24 | 1m 25s | 94% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.21 | 46s | 86% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.18 | 46s | 85% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.09 | 18s | 50% |

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
