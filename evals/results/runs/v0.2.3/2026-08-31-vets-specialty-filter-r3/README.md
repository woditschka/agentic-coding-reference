# vets-specialty-filter r3 — v0.2.3

Filter the vet list by specialty (feature) · started 2026-08-31T16:17:11+00:00 · exec `claude-dev` · status **complete**

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

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.63. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in the right seams: derived finders on VetRepository (findBySpecialtiesNameIgnoreCase, both overloads) keep the query in the persistence gateway, and the controller only binds and delegates. The blank-value normalization in specialtyInForce is a small rule sitting in a controller, which the catalog's Web controller row disallows for new rules, and the pagination ternary is copy-pasted across five links in vetList.html. Tests are behavior-named and cover full-name matching, case, partial, no-match, blank, and paging, but carry bare literals ("radiology", "Leary", "Stevens") the three-tier convention forbids, and theVetListShouldIgnoreABlankSpecialty asserts a mock interaction rather than behavior. Documentation is thorough: NG-9 narrowed, REQ-VET-003 minted, the withdrawn defect row removed, two ADRs recorded.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Repository-derived finders ( findBySpecialtiesNameIgnoreCase ) keep matching in the persistence layer and the uncached-read choice is justified by ADR; the deduction is that  specialtyInForce  puts a new normalization rule in  VetController , which the catalog's Web controller row calls a fresh violation, and the controller now branches on it. Tests are broad and spec-named ( theSpecialtyLookupShouldDisregardLetterCase ,  theVetListShouldPageWithinTheNarrowedListing ), four-phase and factory-based, but carry Tier-3 literals ("radiology", "Leary",  isEqualTo(2)  from seed data), narration comments ("two values bind to one comma-joined name"), and interaction verification via  then(vets).should(never()) . The template repeats the same  specialty == null ?  ternary in five links. Docs are fully current: NG-9 narrowed, REQ-VET-003 minted, superseded note, contracts rows, defect row removed, open questions added.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Repository derived queries (findBySpecialtiesNameIgnoreCase) put matching where the persistence pattern expects it, and the uncached-read asymmetry is justified by an ADR; the controller gains only request normalization (specialtyInForce), though that null-vs-blank rule plus the branch in findPaginated is one more rule tested only through the web layer, widening the pyramid gap. Tests are BDD-named and cover case, partial, empty, blank, and paging, but lean on bare literals ("radiology", "Leary", "Stevens") the three-tier convention calls mystery values, and then(...).should(never()) asserts a collaborator interaction rather than behavior. The five duplicated ternaries in vetList.html are repetitive noise. Documentation is exemplary: NG-9 narrowed, REQ-VET-003 minted, superseded entry, defect row removed, contracts table and open questions updated.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $12.17 | 35m | 8 | 93% | 10 file(s) +345/−30 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.96 | 2m 50s | 91% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Reader narrows the veterinarian directory to one specialty on either published form

2 review rounds · 2 build-passes · **3 build-failures** · grade **CONCERN**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** | · |

- ◇ **prd-entry** Reader narrows the veterinarian directory to one specialty on either published form · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 11m***
  - ▲ **build ✗ build failed** · retry 1
  - ▲ **build ✗ autofix-audit failed** · retry 2
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · handoff-validate · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 59s***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `ClinicServiceTests.java:220,229,236,24` All five new tests for the specialty-filter matching semantics (shouldFindOnlyVetsHoldingTheGivenSpecialty, shouldFindVetsBySpecialtyNameDisregardingCase, shouldFindNoVetsForASpecialtyNameGivenOnlyInPart, shouldFindNoVetsForASpecialtyNobodyHolds, shouldPageVetsWithinTheNarrowedSpecialty) use the pre-2026-07-31 `should{Verb}...` naming instead of the mandated BDD school `the{Subject}Should{Outcome}` (testing-principles.md 'Test Naming': 'Applies to tests written or modified from 2026-07-31 onward... a slice adding a test writes it behind one from the start'). The sibling file VetControllerTests.java gets this right (theVetListShouldShowOnlyVetsHoldingTheRequestedSpecialty etc.) so the mismatch is avoidable, not a pre-existing-file constraint -- these are wholly new methods, not renames of old ones, so the exemption for pre-existing tests does not apply. layout.toml's mechanical pattern accepts the current names, but the naming-school clause reviewers apply is stricter than that floor.
    - fix: Rename the five new methods to the school's form, e.g. theVetRepositoryShouldFindOnlyVetsHoldingTheGivenSpecialty, theSpecialtyMatchShouldDisregardLetterCase, theSpecialtyMatchShouldRejectAPartialName, theSpecialtyMatchShouldYieldNoVetsWhenNobodyHoldsIt, theNarrowedListingShouldPageWithinItself (or equivalent subject/outcome names) -- no behavior change.
- ↻ **implement** (implementer) ← test · (1 finding) · ***◷ 1m***
  - ▲ **build ✓ clean** · ./gradlew build · ./gradlew test · ./gradlew check · ./gradlew checkFormat · python3 scripts/handoff.py audit-autofix · python3 scripts/handoff.py validate
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved** · ***◷ 50s***
- ◆ **grade CONCERN** · filter both vet list surfaces by specialty
  - blast_radius — **clear** — Ten files but a contained reach: two finders on VetRepository, two handlers plus one private helper in VetController, one template, and five product-doc files. One module of production code, no sensitive paths, no build or dependency change. The widest reach is that the template edit rewrites all five pagination links on the existing unfiltered page, not only the new narrowed one.
  - semantic_surprise — **clear** — Read every production hunk and found no hidden behavior change. The unnarrowed paths are preserved exactly: findPaginated and showResourcesVetList both fall through to the original findAll, and specialtyInForce maps null, empty and whitespace-only alike to null so a blank value never reaches the narrowed query. Two deliberate departures are loudly documented rather than silent: the new finders omit the cache annotation their two neighbours carry, because the key would be caller-authored against a size-unlimited JCache, recorded in the ADR and in the javadoc on each method; and stripping means a name with a trailing space still narrows.
  - test_adequacy — **concern** — The tests are real, not tautological: matching semantics are pinned against a real H2 database in ClinicServiceTests with the seeded holders named explicitly, case folding and prefix refusal are things a stub could not have evidenced, the blank-value branch is proved by a never() assertion on the narrowed finder, and URL encoding is proved by a specialty carrying a space with a matching negative assertion. The gap is narrow and specific: no test requests page 2 or beyond, so of the five rewritten link expressions the first and previous links are never rendered in either branch, including the arithmetic page form. A defect there surfaces as a template failure on page 2 of any listing, narrowed or not.
  - reviewer_hedging — **clear** — Four approvals with zero open findings and no escalate tag. The single changes_requested was a fixable BDD-naming finding applied as a pure rename, and the re-review confirmed it assertion- and behavior-neutral against the pre-fix tree. The second-pass roster was scoped to test-reviewer alone, so the other three reviewers being silent on that pass is the plan working, not a hedge.
  - scope_deviation — **clear** — The diff matches the stated surface exactly: an optional query parameter on both listings and no specialty control on either page. Zero consultations and zero build retries after the abort. The one design revision was bookkeeping rather than a change of direction: the first design-block failed to name two of the design expert's own doc edits in its supporting paths, the autofix audit caught it, and the superseding record named them with no code change. The product-doc moves are the ones the requirement itself entails.
  - why — No semantic surprise, and the matching semantics are pinned against a real database rather than mocks. One thing to check by hand: no test renders page 2, so the rewritten first and previous pagination links are unexercised. Open /vets.html?page=2 with and without a specialty, then merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Cache exposure verified absent: the two new finders in VetRepository.java carry no @Cacheable; grep over src/main confirms @Cacheable("vets") appears only on the two pre-existing unfiltered reads (lines 45, 55), whose keys carry no caller-supplied string. CacheConfiguration.java creates only the 'vets' cache and adds no new path that could key on the caller's specialty, so the ADR's decision holds in the code.
- XSS on the reflected specialty: every pagination link in vetList.html now uses the parameterized @{/vets.html(page=...,specialty=${specialty})} form; the unencoded __${...}__ preprocessing form is gone from the file. Thymeleaf URL-encodes link parameter values and HTML-escapes th:href output, so a caller value carrying quotes, angle brackets, or & cannot break out of the attribute or inject a further parameter. The null branch omits the parameter entirely rather than emitting an empty one. VetControllerTests asserts both halves (specialty=small%20mammal present, raw 'specialty=small mammal' absent).
- Expression injection: the specialty never reaches Thymeleaf's __${...}__ preprocessing or any th:utext sink; it is a model variable consumed as a link parameter, not concatenated into an evaluated expression. The model attribute is used nowhere else in the template.
- SQL injection: both finders are Spring Data derived queries (findBySpecialtiesNameIgnoreCase), parameterized by the framework, matching the system-design threat-model row that no string-concatenated SQL exists in production code. Multi-valued binding of the parameter collapses to one comma-joined string that matches nothing, with no injection surface.
- Input normalization in VetController.specialtyInForce is null/blank-safe and routes a blank value to the unnarrowed read rather than to an empty-string query.
- Reinstated /vets JSON endpoint exposes the same veterinarian names and specialty names already published on /vets.html; no PII or new data class crosses the boundary, and the specialty is not echoed into the JSON response.
- Supply chain: build.gradle and lockfiles are outside the change set, so no dependency was added, upgraded, or re-sourced in this slice; no new CVE surface.
- No hardcoded credentials, tokens, or other secret-shaped values appear anywhere in the diff.

**code-quality-reviewer**

- VetRepository's new finders carry precise Javadoc explaining the whole-name/case-insensitive match contract and cross-link the ADR justifying the deliberate absence of @Cacheable, matching the doc-comment depth of the pre-existing methods
- VetController.specialtyInForce is a small, well-named, single-purpose helper with an early return for the null case, reused identically by both handlers rather than duplicated
- vetList.html's two-parameterized-form pagination links are the correct mitigation, not a smell: Thymeleaf's @{} link expression renders a null-valued query parameter as a dangling  specialty=  rather than omitting it, so interpolating a possibly-null value would have altered the unnarrowed page's links; the duplication is contained to one block and explained by an inline comment
- checkFormat and checkstyleMain both pass clean on the change set; no formatting or style-rule violations

**doc-reviewer**

- NG-9 narrowing recorded via a scope_overrides-backed prd-entry, PRD prose, and a dedicated non-goal ADR, with the owner's decision quoted verbatim in each place it appears
- REQ-VET-003 minted fresh; the REQ-VET-002 Superseded entry states plainly that its id is never reused and is not a successor, matching the owner's second decision
- URL-only contract (no page control) stated behaviorally in the PRD narrative, Done-when bullets, non_goals, and Open Questions, with no route or parameter literal transcribed into system-design.md, respecting that file's own no-transcription author note
- system-design.md Contracts rows for Vet, Specialty, Vets, VetRepository, VetController all remapped to REQ-VET-003; the uncached-lookups ADR is correctly linked from the VetRepository row; the machine-readable-route Known Defects row is removed exactly as the design-block described
- Both new ADRs indexed in adr/README.md, correctly typed (non-goal vs. architectural) per the Implementation section convention, and cross-linking cleanly to prd.md anchors that resolve
- Ubiquitous-language entries for Veterinarian and Specialty already cover this slice's vocabulary; no drift or missing term
- PRD open questions (visible control, multi-specialty) recorded as unresolved narrative rather than silently decided, consistent with the owner's stated deferral

**test-reviewer**

- Splitting matching semantics (case-insensitivity, prefix refusal, paged totals) into real-database ClinicServiceTests while keeping VetControllerTests' mocked repository limited to wiring/selection is the right seam: a stub can only echo what it is told, so it cannot evidence case folding or prefix refusal, and the real-DB tests do (seeded 'radiology' held by Leary and Stevens, verified via containsExactlyInAnyOrder)
- theVetListShouldPageWithinTheNarrowedListing correctly pins the risk the design-block flagged: 'small mammal' proves the pagination link is built through Thymeleaf's URL-encoding form (asserts the %20-encoded, &amp;-escaped link) and a matching negative assertion rules out a raw-space link, so a regression to the unencoded __${...}__ form would fail this test
- theVetListShouldLeavePaginationLinksUnchangedWhenNoSpecialtyIsRequested and theVetListShouldIgnoreABlankSpecialty/theJsonVetListShouldIgnoreABlankSpecialty each assert  never()  on the narrowed finder, which is the one way a mock can prove the blank/absent branch never reaches the narrowing query
- All eight PRD-mandated BDD test names from the prd-entry are present verbatim in VetControllerTests, and every numbered edge case (1-5) in prd.md's Veterinarian directory section has covering assertions across the two files
- AssertJ used throughout ClinicServiceTests' new tests (fluent, chained assertj), consistent four-phase structure with blank-line separation, no phase comments; the two inline comments present (on theVetListShouldNameOneSpecialtyOnly and theVetListShouldPageWithinTheNarrowedListing) explain non-obvious Spring binding/encoding facts rather than narrating obvious code

**test-reviewer**

- Five ClinicServiceTests methods renamed to the{Subject}Should{Outcome} form per docs/testing-principles.md § Test Naming, resolving the prior tested-as-spec autofix finding
- Rename is assertion- and behavior-neutral (verified by diff against pre-fix tree and a targeted ClinicServiceTests run); no other change in the fix delta

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $4.56 | 16m 42s | 95% |
| `agent-team:system-design-expert` | 2 | opus-5 | $2.52 | 6m 46s | 91% |
| `(parent)` | 1 | opus-5 | $2.01 | 38m 5s | 96% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.19 | 3m 34s | 92% |
| `agent-team:change-grader` | 1 | opus-5 | $0.96 | 2m 50s | 91% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.56 | 3m 24s | 89% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.49 | 1m 6s | 83% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.40 | 1m 25s | 92% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.29 | 1m 35s | 91% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.08 | 10s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.45 | 12m 13s | 95% |
| `(parent)` | opus-5 | $2.01 | 38m 5s | 96% |
| `agent-team:system-design-expert` | opus-5 | $1.70 | 4m 57s | 92% |
| `agent-team:product-requirements-expert` | opus-5 | $1.19 | 3m 34s | 92% |
| `agent-team:change-grader` | opus-5 | $0.96 | 2m 50s | 91% |
| `agent-team:system-design-expert` | opus-5 | $0.81 | 1m 49s | 88% |
| `agent-team:feature-implementer` | opus-5 | $0.64 | 2m 21s | 95% |
| `agent-team:security-reviewer` | opus-5 | $0.49 | 1m 6s | 83% |
| `agent-team:feature-implementer` | opus-5 | $0.47 | 2m 7s | 92% |
| `agent-team:test-reviewer` | sonnet-5 | $0.42 | 2m 27s | 89% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.40 | 1m 25s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.29 | 1m 35s | 91% |
| `agent-team:test-reviewer` | sonnet-5 | $0.14 | 56s | 87% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.08 | 10s | 50% |

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
