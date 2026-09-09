# vets-specialty-filter r2 — v0.3.10

Filter the vet list by specialty (feature) · started 2026-09-08T21:36:32+00:00 · exec `claude-dev` · status **complete**

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

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.62. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Matching lives in the derived query ( findBySpecialtiesNameIgnoreCase ), leaving VetController.java:46-95 with binding, normalization and response shaping — the layer the design assigns those. Debt is small: an empty-string sentinel from  requestedSpecialty  plus the same emptiness branch duplicated in  findPaginated  and  findVets . Tests read as specifications ( theVetDirectoryShouldNotMatchPartOfASpecialtyName ), use named tiers ( A_SPECIALTY_NO_VET_HOLDS ), and place the matching rule in a real-database VetRepositoryTests; the controller tests still stub through the mock framework and assert on rendered  &amp;specialty=  markup, and  ONE_VET_PER_PAGE  doubles as an expected size. Docs are complete: NG-9 narrowed, REQ-VET-003 minted with REQ-VET-002 amended-but-withdrawn, the obsolete known-defect row removed, cache open question updated, two ADRs indexed.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in the right layers: a Spring Data derived query on VetRepository, with VetController only binding, normalizing, and delegating — no new business rule in the controller. Minor debt: the empty-string sentinel from requestedSpecialty() and the near-identical branch in findPaginated()/findVets() duplicate the same decision twice. VetRepositoryTests exercises the matching rule against real seeded data with behavior names and three-tier constants (A_SPECIALTY_NO_VET_HOLDS, ONE_VET_PER_PAGE); controller tests still stub the repository via Mockito and assert on rendered markup ('&amp;specialty='), and no blank-value case covers /vets. Documentation is thorough: NG-9 narrowed, REQ-VET-003 minted, REQ-VET-002 amended but not reused, the obsolete known-defect row removed, contracts table and open questions updated, two ADRs indexed.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Matching lives in the repository as a derived query ( findBySpecialtiesNameIgnoreCase , VetRepository.java), leaving the controller only binding/normalization — the layer the catalog assigns it — so no new business rule lands in  VetController ; the uncached choice is reasoned in an ADR. Docs are unusually complete: NG-9 narrowed, fresh REQ-VET-003, REQ-VET-002 amended but not reused, contracts table, the retired defect row, and open questions all move, with no surviving stale claim. Tests are behavior-named, phase-separated, and the repository suite exercises real seeded data. Deductions: the empty-string sentinel from  requestedSpecialty  plus the template's  {specialty}  list trick need a paragraph of comment to be legible, and  EVERY_VET_IN_THE_DIRECTORY = 2  is reused as the total of a *narrowed* page, misnaming the value.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $14.42 | 36m | 38 | 94% | 10 file(s) +410/−28 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.80 | 2m 12s | 88% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Reader narrows the veterinarian directory to one specialty

2 review rounds · 2 build-passes · grade **SCRUTINIZE**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | **✔** | · |
| **security** | **✔** | · |
| **doc** | ✎ (1) | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Reader narrows the veterinarian directory to one specialty · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 13m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain not verified against the NVD in this review: build.gradle declares no OWASP dependencyCheck plugin, so dependencyCheckAnalyze could not run and this reviewer has no network access. The change itself alters no dependency (build.gradle is not in the change set), so the surface is unchanged; a human or CI should close the standing NVD check for Spring Boot 4.1.1 separately from this slice.
  - ▹ rec: The specialty parameter has no explicit length bound before it reaches the derived query. Harm is limited (the value is parameterized, uncached, and bounded by the container's request-line limit), so this is not a defect on this change; if a future slice caches or logs the value, add an explicit bound at the boundary first.
  - ▹ rec: Neither /vets.html nor /vets gained a filter form or an allowlist of known specialty names. Matching arbitrary caller text against Specialty.name is safe as written, but an allowlist drawn from the specialties table would narrow the boundary further if the filter later feeds anything beyond the query.
- ✔ **review code-quality** · **approved** · ***◷ 1m***
  - ▹ rec: VetController.java:63-70,81-86 — findPaginated(page, specialty) and findVets(specialty) both branch on specialty.isEmpty() to choose between vetRepository.findAll(...) and findBySpecialtiesNameIgnoreCase(...), the same two-line decision duplicated once per route. Not blocking since each method also does route-specific pagination work, but a reader hitting the second copy will wonder if the two are meant to diverge; worth collapsing into one private dispatch helper if a third caller ever appears.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [autofix] `prd.md:145` The requirement footer link line uses two spaces around the middot separator ("  ·  ") and reverses the established Design/ADR order versus every other requirement footer in the document (e.g. line 99: `**Design:** ... · **ADR:** ...`, single spaces, Design first). This is the only requirement section in the file with this inconsistency.
    - fix: Rewrite line 145 as `**Design:** [system-design.md#contracts](system-design.md#contracts) · **ADR:** [ADR: Narrowing a Veterinarian Directory by Specialty](adr/2026-09-08-non-goal-veterinarian-specialty-filter.md)` to match the single-space, Design-then-ADR convention used elsewhere (e.g. Pet records section).
- ✔ **review test** · **approved** · ***◷ 2m***
  - ▹ rec: src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java: theVetDirectoryShouldIgnoreABlankSpecialtyValue exercises the blank/all-spaces branch of requestedSpecialty() only through /vets.html. showResourcesVetList (/vets) calls the same private helper and its own isEmpty() branch in findVets(), but no test drives a blank specialty value through that endpoint directly. Low risk since the helper is shared and unit-identical, but a dedicated case would close the gap for the machine-readable surface's own code path.
  - ▹ rec: No test exercises a specialty value containing characters that need query-string escaping (e.g. an ampersand or space-plus-plus) through either endpoint. The derived query is parameterized (no injection risk) and Thymeleaf link building auto-escapes, so this is polish, not a defect.
- ↻ **fix prd-expert** ← doc · (1 finding)
- ◇ **prd-entry** Reader narrows the veterinarian directory to one specialty · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **new** · (design) · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 24s***
- ✔ **review doc** · **approved** · ***◷ 5s***
- ◆ **grade SCRUTINIZE** · narrow the veterinarian directory to one specialty
  - blast_radius — **skim** — Contained to the vet package in one module: two controller routes, two derived repository methods, and the vetList paging links, plus documentation. No sensitive or security-surface paths, and the 41 hunks are almost all small and local to the vet slice.
  - semantic_surprise — **skim** — I read every production hunk and found no hidden behavior change: the no-filter path still calls findAll, the empty-string sentinel from requestedSpecialty is set on the model before the template dereferences it, and the paging links were rewritten from string preprocessing to a link expression whose empty-list idiom drops the parameter entirely, so unfiltered URLs keep their old shape. The join-on-specialties paging count, the classic trap here, is pinned against the real database.
  - test_adequacy — **skim** — The matching rule is tested against a real repository and the seeded database rather than a double, asserting real outcomes on the boundaries that matter: whole-name-only, case folding, padded values, a specialty nobody holds, a vet under each of several specialties, and the paged total counting only holders. Controller tests drive the rendered page and assert the paging link carries the filter and drops it when none was asked for.
  - reviewer_hedging — **scrutinize** — Three of the four round-1 approvals carry a recommendations list rather than approving bare. The security reviewer's is the one worth reading: the caller-supplied specialty reaches the derived query with no explicit length bound, judged safe only because the value is parameterized, uncached and unlogged, and the standing NVD supply-chain check could not be run here. Test review flagged that the blank-value branch is never driven through the machine-readable route, and code quality flagged the two-line filter branch duplicated once per route.
  - scope_deviation — **skim** — Zero build retries, zero consultations, zero design revisions, and the diff matches the triaged surface. The documentation reach beyond the file targets, two ADRs plus the NG-9 narrowing and the withdrawn REQ-VET-002 amendment, is how the recorded scope override was required to be recorded.
  - why — The code reads clean and the tests are real, including the join-paging count against a live database. What earns a closer look is the reviewers' fine print, not the diff: an unbounded caller-supplied string reaching the query, an unrun supply-chain check, and an untested blank-value path on the JSON route. Read those three notes, then merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Data-access injection: the specialty filter reaches the database only through Spring Data derived queries (VetRepository.findBySpecialtiesNameIgnoreCase, both overloads). No string-concatenated query text, no @Query, no createQuery/createNativeQuery anywhere in the vet package. Satisfies security-principles.md 'Injection into data access'.
- XSS: the request-derived specialty is never rendered as text or markup. Its only template use is as a link-expression parameter (@{/vets.html(page=..., specialty=${filter})}), which URL-encodes the value and HTML-escapes the rendered href; th:with only calls String.isEmpty() on it. Default output escaping is untouched, no th:utext added.
- Template-expression injection: the change replaces the pre-existing preprocessing links (@{'/vets.html?page=__${i}__'}) with link expressions. Request-derived text therefore never enters a __${...}__ preprocessing slot. Swept the rest of src/main/resources/templates/: the remaining preprocessing sites (layout.html:31, inputField/selectField fragments, ownerDetails, ownersList) are pre-existing and interpolate fragment-local names and entity identifiers, not request-supplied text.
- Caching: VetRepository documents the deliberate omission of @Cacheable on both new finders, so caller-supplied text never becomes an unbounded cache key. The divergence from the @Cacheable("vets") neighbour carries its inline justification, meeting the Pattern Consistency clause.
- Exposed surface unchanged: no new endpoint. /vets.html and /vets each gain one optional scalar @RequestParam; both were already unauthenticated in the recorded demonstration baseline (system-design.md Security Context), and neither mutates state. No management-endpoint exposure change.
- Mass assignment: specialty binds as a scalar @RequestParam, not into a command object, so no new binder and no identifier-binding surface.
- Null and type safety: requestedSpecialty() handles the absent and blank parameter at the boundary and returns a non-null empty string, so the downstream isEmpty() calls and the template's specialty.isEmpty() cannot NPE. No raw types, no unguarded casts, no Optional.get().
- Controller and repository remain stateless singletons; no mutable shared state, no SimpleDateFormat, no executors, no file or network I/O, no logging added, no secrets in the diff (grepped the change set for password/secret/token/key/credential: zero hits).
- No new or changed dependency: build.gradle is outside the change set, so this change adds no supply-chain surface.

**code-quality-reviewer**

- VetController.requestedSpecialty() mirrors OwnerController's existing empty-string-signifies-no-filter idiom (processFindForm), so the sentinel is consistent with the codebase rather than a new convention
- VetRepository placement is correct per system-design.md: the whole-name, case-folded matching rule is expressed as a Spring Data derived query rather than duplicated logic in the controller, and the two new ADRs correctly record the non-goal narrowing and the deliberate no-caching decision with sound rationale (unbounded cache keyed by caller text)
- Javadoc on the new repository methods and the private requestedSpecialty() helper explains WHY (padding/case/caching rationale) rather than restating the signature
- Test naming and data-naming conventions are followed throughout (VETS_HOLDING_RADIOLOGY-style named fixtures, BDD-style method names), and VetRepositoryTests correctly exercises the derived query against the real database rather than a double
- Thymeleaf template change correctly threads the filter through pagination links using the empty-list/single-element-list trick, with a comment explaining why (avoids rendering a bare 'specialty=' parameter), and checkFormat passes clean

**doc-reviewer**

- NG-9 narrowing is recorded with the correct ADR link and the Non-Goals table row states the new scope without leaking rationale beyond the existing one-line-per-row convention already used by other rows
- REQ-VET-003 anchors, Done-when bullets, and edge cases stay in behavioral language with no class, method, or query-parameter-name leakage; the PRD deliberately avoids naming the parameter, describing it as "asked for in the address a reader opens"
- Superseded entry for REQ-VET-002 is amended in place (never renumbered/reused) and cross-references the fresh REQ-VET-003 id correctly
- Both new ADRs follow the template exactly: non-goal ADR uses the  non-goal-  filename infix and **Non-goal:** NG-9 in Implementation; the caching ADR uses **Requirements:** REQ-VET-003 and a References section with em-dashes; both are under 60 lines and in present tense
- docs/adr/README.md index gains both new rows with correct dates and accepted status
- system-design.md Contracts rows for Vet, Vets, VetRepository, VetController are updated to carry REQ-VET-003 and stay at the correct abstraction level (purpose + source pointer, no parameter/field tables, no method signatures)
- The stale Known Defects row calling the machine-readable route 'pending removal' is correctly removed now that the route is a supported surface, and REQ-VET-002 is correctly absent from system-design.md as a deprecated id
- The new Persistence paragraph and the Open Questions item 5 update accurately describe the code's actual caching behavior (verified against VetRepository.java and VetController.java) — no drift between the docs and the implementation
- All new cross-references (PRD anchors, ADR links, system-design section links) resolve to existing anchors/headings

**test-reviewer**

- REQ-VET-003's matching rule (whole-name, case-insensitive) is tested at the repository seam with a real database via @DataJpaTest, per the design doc's assignment of the rule to the derived query — not widened into a framework-booted test.
- Request normalization (blank vs. present vs. absent specialty) is correctly tested at the controller/web boundary via MockMvc, matching the design doc's assignment of that branch to request adaptation.
- All 8 Done-when bullets and 3 of 4 listed edge cases (padded value, multi-specialty vet, letter-case matching) have dedicated tests per coverage-map; the 4th (stable specialty ordering) predates this slice and touches unchanged code.
- BDD naming (the{Subject}Should{Outcome}) used throughout new tests; three-tier data naming followed (RADIOLOGY, EVERY_VET_IN_THE_DIRECTORY, ONE_VET_PER_PAGE, etc.) with no mystery literals.
- Mocking stays within policy: VetRepositoryTests uses the real repository against a real seeded database; VetControllerTests uses MockMvc (the sanctioned HTTP-boundary double) plus the pre-existing MockitoBean pattern for VetRepository, consistent with the host file's established convention.
- VetController reaches 100% line and branch coverage per Jacoco; ./gradlew test passes clean.

**code-quality-reviewer**

- Fix delta (docs/prd.md:145) reorders the footer to Design-then-ADR with single spaces around the middot, matching the file's own established convention (line 99, the only other multi-link footer) and resolving the round-1 doc-reviewer finding exactly as described
- No production code, test, or other doc file changed in this fix round; the round-1 design and code-quality approval stand unaffected
- ./gradlew checkFormat passes clean

**doc-reviewer**

- docs/prd.md:145 footer link line now reads Design first, then ADR, with single spaces around the middot, matching the convention at line 99 (the only other multi-link footer in the file) — round-1 finding resolved.
- Fix delta is confined to the one line named in the round-1 finding: no requirement text, Done-when bullet, edge case, anchor, or Non-Goals row changed.
- Swept the file for other footer lines (grep for **Design:**/**ADR:**): only lines 76, 99, 145 exist, and 145 now matches 99's form — no further instances of the class remain.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $5.19 | 15m 9s | 97% |
| `agent-team:system-design-expert` | 2 | opus-5 | $2.63 | 7m 7s | 93% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $2.53 | 6m 11s | 94% |
| `(parent)` | 1 | opus-5 | $1.68 | 37m 57s | 96% |
| `agent-team:change-grader` | 1 | opus-5 | $0.80 | 2m 12s | 88% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.69 | 2m 50s | 91% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.68 | 1m 37s | 89% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.55 | 2m 25s | 89% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.45 | 2m 25s | 93% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.53 | 13m 54s | 97% |
| `agent-team:system-design-expert` | opus-5 | $1.88 | 5m 8s | 94% |
| `(parent)` | opus-5 | $1.68 | 37m 57s | 96% |
| `agent-team:product-requirements-expert` | opus-5 | $1.61 | 3m 56s | 95% |
| `agent-team:product-requirements-expert` | opus-5 | $0.92 | 2m 14s | 92% |
| `agent-team:change-grader` | opus-5 | $0.80 | 2m 12s | 88% |
| `agent-team:system-design-expert` | opus-5 | $0.76 | 1m 58s | 89% |
| `agent-team:security-reviewer` | opus-5 | $0.68 | 1m 37s | 89% |
| `agent-team:feature-implementer` | opus-5 | $0.65 | 1m 15s | 90% |
| `agent-team:test-reviewer` | sonnet-5 | $0.45 | 2m 25s | 93% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.43 | 2m 3s | 91% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.39 | 1m 56s | 90% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.25 | 47s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.16 | 29s | 84% |

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

- plugin `agent-team-spring-boot` at `v0.3.10` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `6cbb44ce4c9a` (branch `agent-team`)
- task fingerprint `8a2138a7610e1d3e` · `2.1.263 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
