# vets-specialty-filter r2 — v0.2.1

Filter the vet list by specialty (feature) · started 2026-08-08T15:40:25+00:00 · exec `claude-dev` · status **complete**

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

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.68. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in VetRepository as derived queries (findDistinctBySpecialtiesNameIgnoreCase) rather than in the web layer, keeping the controller thin; the uncached-lookup choice is reasoned in an ADR. Minor demerit: normalizeSpecialty puts a blank-equals-absent rule in the controller, and vetList.html repeats the narrowed ? @{...} : @{...} ternary five times. Tests are behavior-named throughout (theVetRepositoryShouldNotMatchAPartialSpecialtyName) and cover case, partial, empty, paging, encoding and unchanged-default paths, but literals like "radiology", "Leary", isEqualTo(2) and PageRequest.of(0, 1) are Tier-3 mystery values, and theMachineReadableVetListShouldBeUnchangedWhenNoSpecialtyIsNamed holds two act/assert cycles. Documentation is exhaustive: NG-9 narrowed, REQ-VET-003 minted, superseded REQ-VET-002 reconciled, contracts/threat/defect/open-question rows and vocabulary all updated.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in VetRepository as a derived query, leaving VetController thin (findPaginated dispatch, showResourcesVetList ternary); the uncached-lookup ADR and the security-posture row are the kind of reasoning the architecture brief asks for. Deduction: normalizeSpecialty is a blank-handling rule living in the controller, testable only through MockMvc, so it widens the pyramid gap the testing brief names. Tests are BDD-named and cover case, partial, empty-match, blank and pagination-carry, plus XSS encoding, but data is bare literals ("radiology", "Leary", "Stevens") rather than named tiers, theVetDirectoryShouldIgnoreABlankSpecialtyValue leans on an unnamed shared stub, and theMachineReadableVetListShouldBeUnchangedWhenNoSpecialtyIsNamed runs two act/assert cycles. Template repeats the narrowed ternary across five links. Docs (PRD, NG-9, superseded, system-design, vocabulary, ADR index) are all current.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering is pushed into VetRepository as derived queries (findDistinctBySpecialtiesNameIgnoreCase) rather than filtered in the controller, with the cache asymmetry justified by an ADR; the controller only binds and delegates. Two dings: blank-to-absent normalization is a rule sitting in VetController, and vetList.html repeats the same narrowed/unnarrowed ternary five times instead of building the link parameters once. Tests are BDD-named and behavior-focused, but ClinicServiceTests uses bare literals ("radiology", "Leary", isEqualTo(2)) against seed data with no factories or named constants, and theMachineReadableVetListShouldBeUnchangedWhenNoSpecialtyIsNamed packs two act/assert cycles into one test. Documentation is exhaustive: NG-9 narrowed, REQ-VET-003 minted, REQ-VET-002 reconciled, defect row and Open Question 5 corrected, threat table and glossary updated.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $14.90 | 46m | 39 | 91% | 11 file(s) +341/−32 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.78 | 2m 46s | 83% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Veterinarian directory narrowed by specialty

2 review rounds · 2 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | · |
| **doc** | ✎ (1) | **✔** |

- ◇ **prd-entry** Veterinarian directory narrowed by specialty · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 9m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 46s***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · autofix-audit · handoff-log
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 55s***
- ✔ **review security** · **approved** · ***◷ 52s***
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `ubiquitous-language.md:54` The new 'Veterinarian directory' entry (added 2026-08-08) ends with 'the serialization wrapper recorded below,' a relative reference to the 'Naming collisions' section further down the same file. The Writing Standards checklist prohibits relative references ('above', 'below', 'previous').
    - fix: Replace 'recorded below' with a direct reference, e.g. 'recorded under Naming collisions' or a link to that section's heading.
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `ClinicServiceTests.java:219-248` The five new specialty-matching tests (shouldFindVetsHoldingTheNamedSpecialty, shouldFindVetsBySpecialtyNameIgnoringCase, shouldNotFindVetsByAPartialSpecialtyName, shouldFindNoVetsForASpecialtyNobodyHolds, shouldPageVetsHoldingTheNamedSpecialty) use the pre-2026-07-31 should{Verb} naming instead of the brief's the{Subject}Should{Outcome} BDD school (testing-principles.md Test Naming), which applies to any test written or modified from 2026-07-31 onward. The new VetControllerTests methods in the same slice correctly follow the school (e.g. theVetDirectoryShouldNotMatchAPartialSpecialtyName), so the split is inconsistent within one feature slice, not a pre-existing-file exemption - these are brand-new methods, not renamed old ones.
    - fix: Rename the five methods to the school, e.g. theVetRepositoryShouldFindVetsHoldingTheNamedSpecialty, theVetRepositoryShouldMatchTheSpecialtyNameIgnoringCase, theVetRepositoryShouldNotMatchAPartialSpecialtyName, theVetRepositoryShouldFindNoVetsForASpecialtyNobodyHolds, theVetRepositoryShouldPageVetsHoldingTheNamedSpecialty.
- ↻ **implement** (implementer) ← test · (1 finding) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · autofix-audit · handoff-log
- ↻ **fix prd-expert** ← doc · (1 finding)
- • review-plan (review-plan-engine)
- ↻ **fix test** ← test · (1 finding)
- ✔ **review code-quality** · **approved** · ***◷ 18s***
- ✔ **review test** · **approved** · ***◷ 12s***
- ✔ **review doc** · **approved** · ***◷ 44s***
- ◆ **grade CLEAR** · narrow the veterinarian directory by specialty
  - blast_radius — **clear** — Code reach is confined to the vet package and its one template: two derived repository lookups, one controller parameter with a shared normalizer, and the five pagination links in vetList.html. No sensitive paths, no build, schema, config, or cache-configuration edits, and both routes stay backward compatible with the parameter absent. The 40 hunks are inflated by six documentation files and by rewriting each pagination link individually.
  - semantic_surprise — **clear** — The one hunk that could hide a silent behavior change is the pagination rewrite from literal substitution (@{'/vets.html?page=__${i}__'}) to parameterized link expressions, and it is pinned: the unnarrowed branch renders the original shape and a test asserts the string /vets.html?page=2 with no 'specialty' substring. normalizeSpecialty collapses null, empty, and whitespace to null, which selects the unfiltered listing rather than a query that would match nothing, and both surfaces share it so they cannot drift. Distinct paging over the specialties join reports totals for the narrowed set, proven against the real database rather than asserted against a stub.
  - test_adequacy — **clear** — The split is real, not tautological: matching semantics (whole name, case-insensitive, partial matches nothing, narrowed paging totals) are pinned in ClinicServiceTests against H2 with real seed data, while VetControllerTests drives the MVC stack for wiring, model attributes, and rendered link markup. Assertions are outcome-based and would fail against a broken implementation, and two of them guard regressions rather than the new path: unchanged link shape when no specialty is named, and no \<script> in the rendered page for a markup-injection value. The only untested composite is issuing the page-2 request itself, which is the same binding code path the link test already covers.
  - reviewer_hedging — **clear** — Round one ran the full battery; the two changes_requested verdicts were both fixable autofix findings (a prohibited relative reference in one glossary line, and five test method names off the BDD school), and both are closed with the fix-delta round confirming rename-only and link-only edits. No approval lists a lingering worry. Security is silent in round two because the low-risk fix-delta plan scoped it out after its clean round-one approval of an unchanged production surface, which is expected rather than a hedge.
  - scope_deviation — **clear** — The diff stays inside the requirement's declared file targets plus the documentation paths the PRD entry itself enumerated; the added repository tests in ClinicServiceTests are the natural home for real-database matching assertions. The single design revision was bookkeeping, not a rethink: the superseding design-block only widened supporting_paths to cover two ADR files the autofix audit flagged, with the implementation already green. The one doc edit without an autofix audit record (ubiquitous-language.md:54) was re-reviewed and explicitly approved in the fix-delta doc round.
  - why — Every facet reads clear and the code residual is small. What deserves the human's eye is not the code but the durable product commitment the slice carries: NG-9 narrowed and the previously withdrawn JSON /vets route reinstated as a supported surface. Read the two ADRs, then merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- normalizeSpecialty is factored once and shared by both directory surfaces (HTML and JSON), so matching semantics for absent/blank specialty cannot drift between them
- VetRepository additions follow existing Spring Data naming and Javadoc conventions, and correctly omit @Cacheable with a Javadoc pointer to the ADR explaining why
- vetList.html computes narrowed=${specialty != null} once via th:with and reuses it across all five pagination links instead of repeating the null check
- checkFormat and compileJava both pass cleanly; no prohibited suffixes, no swallowed exceptions, no System.out usage, no magic-string duplication introduced

**security-reviewer**

- Specialty reaches the database only through Spring Data derived queries (findDistinctBySpecialtiesNameIgnoreCase), which bind the value as a JPA parameter; no string-concatenated SQL or JPQL is introduced, so the SQL-injection threat-model row still holds
- Both new repository methods carry no @Cacheable, matching docs/adr/2026-08-08-uncached-specialty-filtered-vet-lookup.md and the new system-design Threat Model row: the unbounded, evictionless vets cache keeps only code-supplied keys
- Pagination links reflect the caller's value through Thymeleaf link expressions (@{/vets.html(page=..., specialty=${specialty})}), which URL-encode the parameter and escape the attribute; output escaping is never disabled (no th:utext, no th:inline) and a controller test asserts a markup-injection payload does not render as \<script>
- The unnarrowed branch keeps the original link shape, so no null-valued parameter leaks into the rendered URL
- normalizeSpecialty applies one shared normalization to both surfaces, so HTML and JSON matching semantics cannot drift; blank and whitespace-only values collapse to the unfiltered listing rather than to an unexpected query
- JSON path is unaffected: /vets serializes only Vet/Specialty entities through Jackson and never echoes the caller's specialty value back, so no reflected-content or content-type confusion surface is added
- No credentials, tokens, or other secret-shaped literals appear anywhere in the change set
- Supply chain unchanged: no build.gradle, pom.xml, or lockfile appears in the change set, so no new dependency or version surface was introduced

**doc-reviewer**

- REQ-VET-003 anchors, 'Done when' bullets, and edge cases in docs/prd.md read as pure behavior with no leaked mechanism (URL/query-parameter language is avoided)
- The REQ-VET-002 withdrawal is reconciled coherently across the Superseded entry, the Open Questions answer, and the new REQ-VET-003 narrative — the id is never reused and is explicitly called out as not a successor
- NG-9's narrowing in the Non-Goals table, its preamble note, and the new non-goal ADR agree on the same boundary (specialty filtering in scope, free-text search still out)
- The stale Known Defects row for the machine-readable vet route is removed from system-design.md, and the document's defect-count provenance note is updated from four to three to match
- system-design.md's Contracts table (Vets, VetRepository, VetController, their Implements columns) and the new Threat Model and Security Context rows are internally consistent with the two new ADRs
- Both new ADRs are correctly named and scoped per docs/adr/README.md's non-goal-ADR convention, use the right Implementation heading (Non-goal: vs Requirements:), and are indexed in the ADR README with resolvable links
- All cross-document links checked (PRD to ADRs, ADRs to PRD/system-design anchors, system-design to ADRs) resolve to existing anchors or headings

**test-reviewer**

- theVetDirectoryShouldBeUnchangedWhenNoSpecialtyIsNamed's tightened not(containsString("specialty")) assertion is verified sound: the template now branches on a  narrowed  boolean so the unnarrowed link path never emits the parameter at all, and no localized #{specialties} header string collides with the lowercase substring, so the assertion both guards the null-parameter defect and is not brittle for the wrong reason.
- The controller/repository test split holds as designed: VetControllerTests mocks VetRepository and asserts wiring only (specialty passed through, model attributes, view name), while ClinicServiceTests exercises findDistinctBySpecialtiesNameIgnoreCase against the real H2 database to pin whole-name, case-insensitive, partial-matches-nothing semantics - matching semantics are proven once against real I/O rather than re-asserted against a stub.
- All ten PRD-named acceptance-criterion test names are present and each exercises the behavior it names; jacoco reports 100% instruction and branch coverage on VetController for this pass.
- theVetDirectoryShouldEncodeTheSpecialtyItPutsOnPaginationLinks is a welcome, non-required addition covering XSS-safe encoding of the specialty value on pagination links.
- No mocking-policy violation: VetRepository is stubbed only behind the sanctioned MockMvc web-boundary tests; the real-database ClinicServiceTests carries the actual matching-logic assertions.

**code-quality-reviewer**

- ClinicServiceTests fix is rename-only: the five method names now follow the the{Subject}Should{Outcome} BDD school and the bodies are byte-identical to the prior pass, so no new behavior or assertion risk was introduced by the rename
- docs/ubiquitous-language.md:54 now links directly to the Naming collisions section heading instead of the prohibited relative reference 'recorded below', and the anchor resolves to the correct heading
- checkFormat passes cleanly on the fix delta

**test-reviewer**

- The five specialty-matching test methods in ClinicServiceTests.java were renamed exactly as specified in the prior autofix finding (theVetRepositoryShouldFindVetsHoldingTheNamedSpecialty, theVetRepositoryShouldMatchTheSpecialtyNameIgnoringCase, theVetRepositoryShouldNotMatchAPartialSpecialtyName, theVetRepositoryShouldFindNoVetsForASpecialtyNobodyHolds, theVetRepositoryShouldPageVetsHoldingTheNamedSpecialty), now consistent with the the{Subject}Should{Outcome} BDD school and with VetControllerTests in the same slice
- Diff confirms rename only: no assertion, body, or setup change in any of the five methods
- Prior tested-as-spec finding is closed

**doc-reviewer**

- docs/ubiquitous-language.md:54 now links to the actual heading anchor #naming-collisions-recorded-during-the-survey, which resolves against the '### Naming collisions recorded during the survey' heading; prior finding (bar_clause legible-cold) is closed
- diff confirms no other content in docs/ubiquitous-language.md changed alongside the finding fix
- five renamed test methods in ClinicServiceTests.java follow the the{Subject}Should{Outcome} BDD school from docs/testing-principles.md and match the VetControllerTests naming from the same slice; prior finding (bar_clause tested-as-spec) is closed
- the relative-reference line at docs/ubiquitous-language.md:36 ('recorded at the end') is a same-class violation but predates this slice, sits outside the fix-delta review surface (scripts/changeset.sh --base-tree shows it unchanged), and is a confirmed provenance line — it belongs in a later full doc pass, not this fix-delta review, and is not raised as a finding here

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `(parent)` | 1 | opus-5 | $5.47 | 48m 57s | 95% |
| `agent-team:feature-implementer` | 3 | opus-5 | $5.36 | 14m 41s | 94% |
| `agent-team:system-design-expert` | 2 | opus-5 | $5.22 | 9m 24s | 93% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $4.97 | 8m 3s | 93% |
| `agent-team:change-grader` | 1 | opus-5 | $1.78 | 2m 46s | 83% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.64 | 3m 14s | 86% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.21 | 3m 33s | 92% |
| `agent-team:security-reviewer` | 1 | opus-5 | $1.20 | 1m 0s | 80% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.94 | 1m 32s | 84% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.07 | 0s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $5.47 | 48m 57s | 95% |
| `agent-team:feature-implementer` | opus-5 | $3.72 | 10m 0s | 96% |
| `agent-team:system-design-expert` | opus-5 | $3.00 | 5m 9s | 92% |
| `agent-team:product-requirements-expert` | opus-5 | $2.58 | 4m 36s | 93% |
| `agent-team:product-requirements-expert` | opus-5 | $2.39 | 3m 27s | 92% |
| `agent-team:system-design-expert` | opus-5 | $2.22 | 4m 15s | 93% |
| `agent-team:change-grader` | opus-5 | $1.78 | 2m 46s | 83% |
| `agent-team:security-reviewer` | opus-5 | $1.20 | 1m 0s | 80% |
| `agent-team:doc-reviewer` | sonnet-5 | $1.19 | 2m 23s | 88% |
| `agent-team:test-reviewer` | sonnet-5 | $0.97 | 3m 10s | 94% |
| `agent-team:feature-implementer` | opus-5 | $0.92 | 2m 24s | 85% |
| `agent-team:feature-implementer` | opus-5 | $0.73 | 2m 15s | 88% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.67 | 1m 2s | 84% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.45 | 51s | 80% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.27 | 29s | 84% |
| `agent-team:test-reviewer` | sonnet-5 | $0.25 | 23s | 79% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.07 | 0s | 0% |

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
- task fingerprint `064d588523591361` · `2.1.226 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
