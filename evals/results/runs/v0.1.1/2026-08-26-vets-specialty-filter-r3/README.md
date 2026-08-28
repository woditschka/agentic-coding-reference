# vets-specialty-filter r3 — v0.1.1

Filter the vet list by specialty (feature) · started 2026-08-26T17:06:44+00:00 · exec `claude-dev` · status **complete**

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

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.63. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> Matching is pushed into VetRepository.findBySpecialtiesNameIgnoreCase rather than the controller, which keeps the rule out of the web layer; the controller only normalizes binding (filterSpecialty), mirroring blank owner search. Minor debt: the null/filter branch is duplicated in showVetList and showResourcesVetList, and reordering addPaginationModel's parameters is gratuitous churn. Tests are behavior-named and use factories, but theVetListPageShouldFilterBySpecialtyCaseInsensitively and theVetListPageShouldNotMatchSpecialtyPrefix assert against the hand-rolled holdingSpecialty stub, so the derived query's actual case-insensitive, non-prefix semantics are never exercised; literals "RaDiOlOgY", "rad", hasSize(3) are mystery values, and the blank-specialty tests each perform two acts. Documentation is complete: ADR, narrowed NG-9, REQ-VET-003, superseded note, contracts table, and retired defect row.

**Sample 2** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> Derived repository queries (VetRepository.findBySpecialtiesNameIgnoreCase) put matching at the right seam, and the template switches to proper Thymeleaf URL building; but the blank-value rule lands as new controller logic (filterSpecialty), and reordering addPaginationModel(page, model, paginated) is churn with no benefit. filterSpecialty normalizes rather than filters — a misleading name — and the two-sentence comment above model.addAttribute("specialty", filter) restates the code. Tests are BDD-named and broad, but holdingSpecialty() reimplements equalsIgnoreCase in the stub, so theVetListPageShouldFilterBySpecialtyCaseInsensitively and ...ShouldNotMatchSpecialtyPrefix assert the fake, not production; blank-value tests bundle two act/assert cycles, and "RaDiOlOgY"/hasSize(3) are unnamed literals. Docs: ADR, NG-9, REQ-VET-003, superseded entry, contracts table, and the retired defect row all move together.

**Sample 3** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> Filtering lands in the repository as a derived query (VetRepository.findBySpecialtiesNameIgnoreCase), mirroring owner search; the controller only normalizes and delegates, though the blank-is-absent rule and the null-branch are duplicated across showVetList and showResourcesVetList, the addPaginationModel parameter reorder is churn, and the 'Thread the specialty through the model' comment restates the code. Tests are behavior-named and cover both surfaces, but holdingSpecialty() re-implements the matching contract in the test, so theVetListPageShouldNotMatchSpecialtyPrefix and the case-insensitive test verify the stub rather than the query; literals like 'radiology', hasSize(3) and id 3 are unnamed Tier-3 values; two tests perform two act/assert cycles. Documentation is thorough: NG-9 narrowed, REQ-VET-003 minted, REQ-VET-002 kept withdrawn, defect row retired, open questions recorded.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $9.55 | 25m | 17 | 88% | 8 file(s) +236/−28 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.57 | 2m 24s | 86% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Filter the veterinarian directory by specialty

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (2) | **✔** |
| **test** | ✎ (4) | **✔** |
| **security** | **✔** | · |
| **doc** | **✖** (2) | **✔** |

- ◇ **prd-entry** Filter the veterinarian directory by specialty · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **minor** · (design) · ***◷ 7m***
- ◆ **implement** (implementer) · ***◷ 15m***
  - ▲ **build ✓ clean** · build · test · format · check
- ✔ **review security** · **approved** · ***◷ 1m***
- ✎ **review code-quality** · **changes_requested** · (2 findings) · ***◷ 5m***
  - [autofix] `VetController.java:64` Private method `findPaginated` does not convey the domain entity being retrieved. The OwnerController counterpart is named `findPaginatedForOwnersLastName`, which tells a cold reader both the entity and the filter dimension. `findPaginated` could be any entity; rename to `findVetsPaginated` (or `findPaginatedVets`) so the pattern symmetry is explicit.
    - fix: Rename method from `findPaginated` to `findVetsPaginated` and update the two call sites in `showVetList` (line 48).
  - [autofix] `VetController.java:55` The parameter order in `addPaginationModel` is (int page, Page\<Vet> paginated, Model model), but the OwnerController counterpart at line 124 declares (int page, Model model, Page\<Owner> paginated) — Model and Page are swapped. Both methods are private so there is no API-compatibility concern, but the reversal breaks the symmetry a reader expects when comparing the two controllers side-by-side. Grep/Read confirmed (IDE not consulted).
    - fix: Swap the second and third parameters: change the signature to `private String addPaginationModel(int page, Model model, Page\<Vet> paginated)` and update the internal usage order accordingly.
- ✖ **review doc** · **blocked** · (2 findings) · ***◷ 1m***
  - **[blocked]** `system-design.md#known-defects` Three Implements columns and one Known-Defects row are stale after REQ-VET-003 implementation. VetController (line 104), Vets (line 102), and VetRepository (line 103) still list only REQ-VET-001 or — in Implements; REQ-VET-003 must be added to all three. The Known-Defects row (line 207) still states the machine-readable veterinarian route serves no requirement, which is factually false now that REQ-VET-003 is implemented — this row must be retired. The design-block record (handoff.jsonl line 5) explicitly called for both updates; the feature-implementer left system-design.md untouched. Cross-document coherence violation.
  - [autofix] `prd.md — Veterinarian directory sectio` The REQ-VET-003 entry is missing a mandatory Design Rationale link. The prd-authoring skill requires this link whenever an ADR records the decision behind the requirement. ADR 2026-08-26-non-goal-vet-specialty-filter.md is exactly that ADR — it records the owner decision that enables REQ-VET-003.
    - fix: Add **Design Rationale:** See [ADR: Filtering the Veterinarian Directory by Specialty Is In Scope; Free-Text Veterinarian Search Stays Out](adr/2026-08-26-non-goal-vet-specialty-filter.md). to the Veterinarian directory section, adjacent to the existing **Design:** line at the section end.
- ✎ **review test** · **changes_requested** · (4 findings) · ***◷ 30s***
  - **[blocked]** `VetControllerTests.java:158-162` theVetListPageShouldTreatBlankSpecialtyAsNoFilter tests whitespace ("   ") but not an empty string (""). PRD acceptance criterion 4 says "empty or whitespace-only specialty" — both are required. A controller that trims then checks isEmpty passes whitespace but could fail empty if the trim logic is applied differently. The empty case must have its own assertion.
  - **[blocked]** `VetControllerTests.java:191-195` theVetsJsonEndpointShouldReturnAllVetsWhenSpecialtyAbsent covers the absent-parameter case but PRD acceptance criterion 9 says "empty, whitespace-only, or absent specialty returns every veterinarian". No test exercises GET /vets?specialty= (empty string) or GET /vets with a whitespace specialty for the JSON endpoint. These are distinct code paths from the absent case and must be covered.
  - [autofix] `VetControllerTests.java:165-172` theVetListPageShouldCarrySpecialtyAcrossPagination has no blank line between the stub-override Arrange phase (given(...)) and the Act phase (mockMvc.perform(...)). The testing brief requires phases separated by blank lines.
    - fix: Add one blank line between the given(...).willReturn(...) statement and the mockMvc.perform(...) call.
  - [autofix] `VetControllerTests.java:171` The pagination-carry assertion checks containsString("specialty=radiology") against the full rendered HTML body. This passes even if the string appears in non-link content. A narrower check — for example, asserting the string appears inside an href attribute (e.g., containsString("href") along with containsString("specialty=radiology"), or an xpath/css selector on anchor elements) — would fail precisely when pagination links lose the specialty rather than passing on incidental occurrences.
    - fix: Replace the full-body containsString check with a targeted assertion on an anchor element href, e.g. content().string(containsString("href")) and content().string(containsString("?page=2&specialty=radiology")), or use xpath("//@href", hasItem(containsString("specialty=radiology"))).
- ↻ **implement** (implementer) ← code-quality, test · (6 findings)
- ↻ **fix prd-expert** ← doc · (2 findings)
- ↻ **fix design** ← doc · (2 findings)
- ◇ **prd-entry** Filter the veterinarian directory by specialty · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **covered** · (design) · supersedes L4 · ***◷ 2m***
- ▲ **build-pass** 20:15
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ↻ **fix test** ← test · (4 findings)
- ✔ **review test** · **approved** · ***◷ 1m***
- ◆ **grade CLEAR** · filter vet directory by specialty on /vets.html and reinstated JSON /vets
  - blast_radius — **clear** — Feature reach is contained to the vet feature package: three prod files (~64 lines) plus one test file and doc sync, no sensitive paths. The row shows 12 files / 85 hunks only because the base ref b67f301 predates the harness-install commit, folding .claude/settings.json, CLAUDE.md, scripts/layout.toml and .gitignore into the range; those are infrastructure, not this feature.
  - semantic_surprise — **clear** — Read every hunk: filterSpecialty normalizes null and strip-empty to null; findVetsPaginated and the JSON branch call findAll when null else findBySpecialtiesNameIgnoreCase; the derived-query name (IgnoreCase, no StartingWith/Containing) gives exactly whole-name case-insensitive non-prefix matching; template threads specialty through the Thymeleaf URL builder so null is omitted. Behavior matches the diff and the acceptance criteria with no hidden turn.
  - test_adequacy — **clear** — Beyond the green suite, the tests use a hand-written holdingSpecialty fake that faithfully models the derived-query contract and assert real boundary outcomes: case-insensitive match, prefix rejection, no-match empty, empty-string and whitespace both treated as no-filter on both surfaces, and pagination carry via the escaped page-2 href. These would fail a broken implementation.
  - reviewer_hedging — **clear** — All four reviewers approved cleanly in the second round with empty findings lists. The first-round criticals (missing empty-string/blank JSON coverage, stale system-design Implements columns) and the naming/param-order autofixes were all resolved, not waived; no lingering caveat, escalate, or reworked-under-pressure clause survives into the final approvals.
  - scope_deviation — **clear** — Change stays within the four triaged file_targets plus the prescribed doc sync. The single design_revision was the covered doc-state-sync (adding REQ-VET-003 to the Implements columns and retiring the machine-readable-route known-defect row) that the original design-block already called for, not a scope expansion; zero consultations, zero build retries.
  - why — All five facets read clear against the diff, not just the row. The vet-package change mirrors the established owner-search filter pattern, the matching semantics are exactly right, and tests exercise every boundary. Confirm and merge; the inflated 12-file/85-hunk row is a base-ref artifact (harness-install commit), not feature reach.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- specialty parameter flows into Spring Data derived query findBySpecialtiesNameIgnoreCase, generating a parameterized query with the name bound as a JDBC parameter; no string concatenation, no SQL/JPA injection surface
- pagination links echo the specialty via Thymeleaf URL-expression builder @{/vets.html(page=..,specialty=${specialty})}, which URL-encodes the parameter value and HTML-escapes the th:href attribute output; no reflected XSS
- controller normalizes null/blank specialty before the repository call and filters at the repository so pagination totals reflect matches only; no data-integrity drift
- no new dependencies introduced; no unsafe operations, deserialization, or file/network I/O added by this change

**code-quality-reviewer**

- VetRepository derived-query methods use the correct Spring Data IgnoreCase/whole-name semantics with no StartingWith suffix — matches the acceptance criteria for non-prefix matching
- New VetRepository methods annotated @Cacheable(vets) consistent with existing findAll methods as required by the design-block
- filterSpecialty helper correctly normalizes null and whitespace-only values to null, matching the blank-as-no-filter contract from the PRD
- Repository-level paging ensures getTotalPages/getTotalElements reflect the filtered set — avoids the controller-after-paging antipattern flagged in design risks
- vetList.html uses Thymeleaf @{...(specialty=${specialty})} URL builder correctly — null specialty is omitted from links automatically, keeping no-filter URLs clean
- Format check passes clean

**doc-reviewer**

- NG-9 narrowing correctly recorded in the Non-Goals table with inline ADR link and prose distinguishing attribute-filtering from free-text search
- REQ-VET-002 stays withdrawn; its ID is not reused; the Superseded entry documents the reinstatement under the fresh REQ-VET-003 id
- REQ-VET-003 ID is well-formed and carries a valid HTML anchor at line 119 of prd.md
- Both open questions (multi-specialty filter and on-page indicator) are recorded in the Open Questions section rather than left as blocking gaps
- ADR 2026-08-26-non-goal-vet-specialty-filter.md follows the non-goal ADR conventions: non-goal-infix filename, Status: Accepted, Implementation section uses **Non-goal:** NG-9, three options considered including the chosen one, cross-links to PRD anchors that resolve
- ADR README index row matches the ADR title and status, consistent with existing rows
- All cross-references inside the new ADR resolve to valid anchors (#non-goals and #req-vet-003 both exist in prd.md)

**test-reviewer**

- All eight test names declared in the prd-entry are present and correctly spelled
- The holdingSpecialty fake faithfully models the derived-query contract: equalsIgnoreCase gives case-insensitive whole-name matching, and absence of StartingWith/Containing gives the non-prefix guarantee — the fake will detect any divergence between the controller logic and the repository contract
- @MockitoBean VetRepository in @WebMvcTest is consistent with the existing VetControllerTests convention; the brief explicitly permits existing mock-framework stubs to stay, and the database is a recognised system boundary for the web-layer slice
- willAnswer delegation to the hand-written holdingSpecialty helper is the right hybrid pattern: the fake captures the behavioral contract while the stub provides the @WebMvcTest seam
- BDD test naming (the{Subject}Should{Outcome}) followed consistently across all eight new tests
- Case-insensitive and non-prefix behaviors tested with realistic values (RaDiOlOgY vs radiology; rad vs radiology)
- JSON endpoint tested for both match and no-match cases with correct HTTP 200 and empty-list semantics
- No JUnit assertEquals/assertTrue; MockMvc result matchers are used throughout, consistent with the existing class style

**code-quality-reviewer**

- findPaginated renamed to findVetsPaginated (line 64) and call site at line 48 updated — resolves prior finding 1
- addPaginationModel parameter order is now (int page, Model model, Page\<Vet> paginated) at line 55 matching OwnerController pattern — resolves prior finding 2
- checkFormatMain passes clean
- filterSpecialty normalization, @Cacheable consistency, and repository-level paging carry forward from prior approved aspects

**doc-reviewer**

- system-design.md Implements columns for VetController, Vets, and VetRepository now include REQ-VET-003 (lines 102-104), resolving the prior blocked finding
- The Known-Defects table contains no stale row for the machine-readable veterinarian route; the Settled note at line 222 records its retirement explicitly
- docs/prd.md Veterinarian directory section carries the mandatory Design Rationale link at line 140, pointing at the correct ADR path and title
- All REQ-IDs appearing in system-design.md Implements columns resolve to requirements in prd.md; no orphan references introduced
- Cross-document coherence is restored: the three contracts, the PRD entry, and the known-defects section all now agree on REQ-VET-003 as the implemented requirement for the specialty filter and the reinstated machine-readable surface

**test-reviewer**

- Finding 1 resolved: theVetListPageShouldTreatBlankSpecialtyAsNoFilter now contains two mockMvc.perform blocks covering whitespace ("   ") and empty-string ("") separately, both asserting model hasSize(3) — PRD criterion 4 fully exercised on the HTML surface
- Finding 2 resolved: new test theVetsJsonEndpointShouldReturnAllVetsWhenSpecialtyBlank covers both empty-string (specialty=) and whitespace-only (specialty=   ) on GET /vets JSON endpoint, asserting vetList.length() 3 in both cases — PRD criterion 9 fully exercised
- Finding 3 resolved: theVetListPageShouldCarrySpecialtyAcrossPagination now has a blank line between the given(...).willReturn(...) Arrange phase and the mockMvc.perform(...) Act phase — four-phase blank-line separation satisfied
- Finding 4 resolved: pagination-carry assertion uses containsString("?page=2&amp;specialty=radiology"), the HTML-escaped href value, narrowing from the generic specialty=radiology match to the specific page-2 link — a spurious match on non-href body text is excluded because &amp; escaping is href-specific in this template
- All 10 VetControllerTests pass (BUILD SUCCESSFUL, verified via ./gradlew test --tests VetControllerTests)
- No mocking-policy violation introduced: @MockitoBean VetRepository is the existing @WebMvcTest seam; the hand-written holdingSpecialty fake continues to model the derived-query behavioral contract faithfully
- BDD naming consistent across all 10 tests (the{Subject}Should{Outcome} method naming school)

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $2.83 | 10m 17s | 92% |
| `spring-boot-claude:system-design-expert` | 2 | opus-4-8 | $1.67 | 4m 16s | 83% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $1.66 | 4m 58s | 86% |
| `(parent)` | 1 | opus-4-8 | $1.10 | 26m 56s | 86% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $0.60 | 3m 34s | 88% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $0.58 | 4m 16s | 84% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $0.57 | 2m 24s | 86% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $0.56 | 2m 59s | 91% |
| `spring-boot-claude:security-reviewer` | 1 | opus-4-8 | $0.42 | 41s | 82% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.09 | 23s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-4-8 | $2.04 | 7m 59s | 94% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.13 | 3m 53s | 90% |
| `(parent)` | opus-4-8 | $1.10 | 26m 56s | 86% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $0.88 | 2m 22s | 83% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $0.79 | 1m 54s | 84% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $0.79 | 2m 18s | 87% |
| `spring-boot-claude:change-grader` | opus-4-8 | $0.57 | 2m 24s | 86% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.53 | 1m 5s | 77% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.42 | 41s | 82% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.37 | 2m 28s | 88% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.35 | 2m 50s | 84% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.30 | 1m 51s | 88% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.26 | 1m 7s | 93% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.23 | 1m 26s | 83% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.23 | 1m 5s | 89% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.09 | 23s | 50% |

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
- task fingerprint `064d588523591361` · `2.1.246 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
