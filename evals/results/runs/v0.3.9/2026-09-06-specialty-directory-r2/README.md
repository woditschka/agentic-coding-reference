# specialty-directory r2 — v0.3.9

Specialty directory page (feature) · started 2026-09-06T20:17:30+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Feature request: the vet list answers "which specialties does this vet hold",
> but staff also ask the inverse — "which vets hold this specialty". Two
> product decisions come with it, made here as the product owner:
> 
> - A read-only specialty view of the existing directory is in scope; managing
>   veterinarians or specialties stays out of scope as before (non-goal NG-2
>   is unchanged).
> - The page is reachable by its URL alone: no navigation entry and no link
>   from another page is part of this request. A visible entry point may come
>   as a follow-up request.
> 
> Add a specialty directory page:
> 
> - GET /specialties.html lists every specialty the clinic knows by its stored
>   name, each with the veterinarians holding it.
> - Each veterinarian is shown by full name: first name, then last name (for
>   example "Helen Leary").
> - A veterinarian holding no specialty appears under no specialty; the page
>   lists specialties, not the full vet roster.
> - All specialties render on one page — no pagination.
> 
> Cover the new behavior with tests.
> 
> These are all the product decisions; no further product answer will come
> during the work. Where a choice still seems open, take the narrowest reading
> consistent with this request and record the open question rather than
> waiting.

## Verdict

| check | result |
|---|---|
| oracle | ✔ 4/4 passed |
| suite (post-agent) | ✔ |
| suite (pristine baseline) | ✔ |
| checkpoints | 7/7 |
| reading depth (pipeline grade) | skim |

The pipeline grade estimates how much human review the change deserves before merge — advisory context from the harness's change grader (read from the ledger's `grader-verdict` record), never part of the bar.

- ✔ `theSpecialtyDirectoryShouldListEverySeededSpecialty` — passed
- ✔ `theSpecialtyDirectoryShouldNameTheVetsHoldingEachSpecialty` — passed
- ✔ `theSpecialtyDirectoryShouldRender` — passed
- ✔ `theVetDirectoryShouldRenderTheSeededVets` — passed

## Checkpoints

The kind's graded ladder, derived from the recorded facts — context only, outside the quality bar (bench README § Checkpoints).

- ✔ `agent complete`
- ✔ `change produced`
- ✔ `suite green`
- ✔ `theSpecialtyDirectoryShouldListEverySeededSpecialty`
- ✔ `theSpecialtyDirectoryShouldNameTheVetsHoldingEachSpecialty`
- ✔ `theSpecialtyDirectoryShouldRender`
- ✔ `theVetDirectoryShouldRenderTheSeededVets`

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 5 (±1) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.68. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Derivation sits in  SpecialtyHolders.directoryOf  as an immutable record with defensive  List.copyOf , leaving  SpecialtyController.showSpecialtyList  to bind, delegate, select a view — the Web controller row honored, no new rule in the controller;  SpecialtyRepository  mirrors VetRepository's narrow read-only style. Tests are behavior-named, framework-free at the unit level, and route construction through the new  VetTestData  factories (VetControllerTests refactored to match); the escaping and empty-input cases are welcome. Deductions: the  setup()  comment 'dentistry is the specialty nobody holds' restates code the field names already say, and the template's  #{specialties} / #{none}  keys appear in no properties file in the patch, so an unresolved key would still satisfy  contains("none") . Docs cover both prd and system-design fully.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController binds/delegates/selects only; the pairing rule lives in the immutable record SpecialtyHolders (List.copyOf in the compact constructor, id-based matching), so the new rule is unit-testable without the framework — right layer, catalog-conforming names, narrow read-only SpecialtyRepository. SpecialtyHoldersTests read as specifications: behavior names, VetTestData factories with generated ids, empty-input, multi-hold, unstored-id and duplicate-name boundaries; the controller test adds output escaping. Deductions: the setup comment 'dentistry is the specialty nobody holds…' restates jamesCarterWhoHoldsNoSpecialty, theSpecialtyPageShouldShowEachVeterinarianByFullName duplicates the subsequence assertion, and new @MockitoBean stubs are taken without justification. STORED_NAME_ORDER names a generic null-safe comparator reused for first names; the template's trailing-space concatenation is awkward. prd.md and system-design.md are fully current.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController is a thin binder/delegator with the derivation lifted into the unit-testable SpecialtyHolders record, so no new rule lands in a controller and the pyramid shifts downward. Two small frictions: SpecialtyRepository is a repository for Specialty, which is not an aggregate root (the catalog says one per root), and "holders" is not in the canonical vocabulary. Tests are behavior-named, factory-backed (VetTestData.createAVet), and cover empty, duplicate-name, and markup-escaping boundaries; but SpecialtyControllerTests still reaches for @MockitoBean stubs without naming the exception, and the setup comment ("// dentistry is the specialty nobody holds...") restates what jamesCarterWhoHoldsNoSpecialty already says. STORED_NAME_ORDER's null tolerance is untested. Both prd.md and system-design.md are updated with no stale claim left visible.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $12.23 | 36m | 32 | 93% | 10 file(s) +595/−30 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.09 | 2m 58s | 91% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · **1 build-failure** · grade **SKIM**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | **✔** | · |
| **security** | **✔** | · |
| **doc** | ✎ (1) | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **minor** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 12m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **minor** · (design) · supersedes L5 · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 2m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 59s***
  - ▹ rec: Supply-chain status, for the record: no NVD match ran in this review. The OWASP dependency-check plugin is not configured in build.gradle and this reviewer has no network access, so the resolved dependency set is not verified against the NVD. The change adds no dependency, so the un-run check reflects the pre-existing baseline rather than anything this slice introduced; closing it belongs to CI or a human.
  - ▹ rec: The page reads every specialty and every veterinarian with no pagination, unlike the paginated /vets.html. Response size is bounded by database content that no request can influence (the application exposes no write path for vets or specialties), so this is not attacker-reachable today; it is worth revisiting only if specialty or vet data ever becomes caller-writable.
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 1m***
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 2m***
  - **[blocked]** `system-design.md:82` The new "The specialty page." paragraph transcribes two literal source values into prose: the cache name `vets` ("the vet read reuses the existing `vets` cache") and the message-bundle key `none` ("the shared `none` wording"). The Abstraction Level checklist prohibits constant literal values in system-design.md — name the constant and cite the source file instead of quoting its value. Renaming the JCache cache (CacheConfiguration.java / VetRepository's @Cacheable) or the message key (messages.properties) would silently make this sentence wrong. The rest of the document follows the correct pattern elsewhere (e.g. the Contracts table row for CacheConfiguration says "the vet cache" without quoting its literal name) — reword this paragraph to match: describe behavior ("reuses the existing vet cache", "the shared no-holders wording") without the backtick-quoted literal identifiers, or add the cache name and message key to the Constants table and cite them from there.
- ↻ **fix design** ← doc · (1 finding)
- ◈ **design-block** **minor** · (design) · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved**
- ◆ **grade SKIM** · add read-only specialty directory page
  - blast_radius — **skim** — Purely additive within the existing vet package: four new production files plus a template, no sensitive path, no binary, and not one line of existing production code changed. The only edits to tracked files are the two docs and a test-data refactor of VetControllerTests, and the shared layout fragment is untouched, which is what keeps the page unlinked.
  - semantic_surprise — **skim** — Read every hunk against expectation and found no behavior the diff does not advertise: directoryOf matches holders to specialties by stored id rather than by name, which two same-named specialties would collide on; it preserves the given specialty order, sorts holders by last then first name with null-safe comparators, keeps a held-by-nobody specialty with an empty list, and lets no vet holding nothing into the output. The one hard failure path, an exception on a specialty with no stored id, is unreachable from the repository read and is covered by a test. The template escapes every value the same way the neighbouring vet list template does.
  - test_adequacy — **skim** — Tests assert real outcomes rather than restate the implementation: the SpecialtyHolders unit tests drive the derivation with real Specialty and Vet objects across ordering, empty holders, same-name identity, multi-specialty repetition and published-list immutability, and the controller tests assert against the rendered HTML including an escaped-markup case. The one thin spot is the no-link criterion, verified only against the vet list page, which the untouched layout fragment makes a reasonable proxy.
  - reviewer_hedging — **skim** — Final state is four clean approvals with zero findings. The round-one doc-reviewer block on a docs prose literal was fixed and the fix verified against source in the fix-delta round, and the security reviewer's two recommendations are scoped to the pre-existing baseline (no dependency-check plugin is configured, so no NVD match ran, and the change adds no dependency) and to a hypothetical future in which vet or specialty data becomes caller-writable, not to anything in this diff.
  - scope_deviation — **skim** — The diff lands on the requirement's stated surface exactly: one unlinked read-only route, no write method declared on the new repository, no navigation entry, no message-bundle change. The single design revision was a record-keeping fix, since the design record had not listed the design doc among its paths, not a mid-flight scope change; no consultations and no build retries.
  - why — Additive, single-module, unlinked read-only page whose derivation logic I read line by line and found matching its documented behavior, backed by tests that assert rendered output rather than restate the code. Confirm and merge. The one residual worth a glance is the unpaginated full-table read, which is data-bounded and not request-influenced.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- New route GET /specialties.html takes no request parameter, path variable, or request body: there is no request-derived value anywhere in the added code, so the injection, mass-assignment, path-traversal, and cross-request-trust rows of docs/security-principles.md are not reached by this change
- Data access uses a constant JPQL query (SpecialtyRepository.findSpecialties) and derived VetRepository.findAll; no string concatenation of caller input into query text
- Template src/main/resources/templates/vets/specialtyList.html renders every value through escaping th:text; no th:utext, no inline script, no external resource, no Thymeleaf preprocessing (__${...}__) on any value, matching the escaping pattern of the neighbouring vets/vetList.html
- SpecialtyRepository extends the narrow Repository base and declares only the one read, so the change adds no write or delete path to specialty data (least privilege)
- SpecialtyController and the SpecialtyHolders record hold no mutable state; holders are copied and published unmodifiable, so the singleton beans stay thread-safe
- No credentials, tokens, URLs, or new configuration values are introduced; no logging is added, so nothing new can reach a log line or error page except the IllegalArgumentException message, which carries only a stored specialty name
- Exposed surface is documented as required by docs/security-principles.md (widening-the-exposed-surface row): docs/system-design.md and docs/prd.md state the new read-only page, that it takes no parameter, and that no navigation links to it; the change does not broaden actuator exposure or weaken the recorded baseline
- build.gradle is unchanged: the change adds no dependency, so no new supply-chain surface

**code-quality-reviewer**

- SpecialtyHolders is a proper immutable value object: List.copyOf on construction, static factory javadoc spelling out the empty-holder and no-drop-out semantics, matching PRD acceptance bullets
- No business rule leaked into SpecialtyController; it only wires the repository reads to SpecialtyHolders.directoryOf, consistent with the Web controller placement rule in architecture-principles.md
- Naming follows the catalog: SpecialtyController/SpecialtyRepository suffixes, SpecialtyHolders as a bare domain-noun value object, showSpecialtyList mirrors the existing showVetList convention, no prohibited suffixes
- SpecialtyRepository narrows to Repository\<Specialty,Integer> with exactly the one read the page needs, matching system-design.md's read-only/uncached description
- Template reuses the existing vetList.html idiom (trailing-space concat span, none fallback) rather than inventing a new rendering pattern, and a controller test confirms stored names are HTML-escaped
- Domain vocabulary (Specialty, Veterinarian/Vet, holders) matches ubiquitous-language.md; no coined synonyms
- Test coverage on SpecialtyHolders is thorough: ordering, empty holders, stored-identity matching across same-named specialties, and immutability of the published list
- checkFormat passes clean

**test-reviewer**

- SpecialtyHolders unit tests exercise the id-based matching, ordering, and immutability rules at the seam system-design.md assigns them to, rather than only through the web-layer tests
- SpecialtyControllerTests and the added VetControllerTests case cover all 5 Done-when bullets and the navigation/several-specialties edge cases from prd.md, confirmed via coverage-map
- Mocking stays within the brief: @MockitoBean/MockMvc used only at the web boundary in controller tests; SpecialtyHoldersTests uses real Specialty/Vet objects with no mocking
- Test data construction goes through VetTestData factories (createASpecialty, createAVet, createAnUnstoredSpecialty); no raw production constructors in new/modified test bodies
- XSS-relevant case covered: a specialty name carrying markup is asserted to render escaped in the Thymeleaf view
- Tests follow BDD naming (theXShouldY), four-phase structure with blank-line separation, and AssertJ fluent assertions throughout; full ./gradlew test suite passes

**doc-reviewer**

- REQ-VET-003 anchor, Done-when bullets, and edge cases correctly added to docs/prd.md with no mechanism, code identifiers, or rationale prose leaking into the PRD
- New requirement number correctly continues the REQ-VET prefix after the withdrawn REQ-VET-002 without reuse
- system-design.md Contracts table rows for SpecialtyController, SpecialtyRepository, SpecialtyHolders, and the updated Vet/Specialty/VetRepository Implements columns correctly cross-reference REQ-VET-003, and REQ-VET-003 exists in prd.md
- Domain terms used (Specialty, Veterinarian) are already defined in ubiquitous-language.md
- Design cross-reference link docs/system-design.md#contracts resolves
- The PRD's Open Questions entries on ordering and a visible entry point are honest, unresolved, non-blocking scope notes rather than silently absorbed decisions

**doc-reviewer**

- Fix resolves the prior blocked finding (line 20) fully: docs/system-design.md:82 no longer quotes the literal cache name or message-bundle key; it now reads 'the vet read reuses the existing vet cache' and 'the shared empty-value wording', matching the behavioral-naming pattern already used in the Contracts row for CacheConfiguration ('declares the vet cache')
- The empty-value wording claim is verified against source: both src/main/resources/templates/vets/specialtyList.html and vetList.html render th:text="#{none}" for the empty case, so the added sentence 'That wording is the one the vet list already uses for a veterinarian with no specialty' is accurate and survives a message-key rename without becoming false
- No new literal values, struct/parameter tables, or other Abstraction Level violations introduced by the fix; rest of the paragraph (identity matching, ordering, rejection/omission rules, parameterless route, untouched layout fragment) is unchanged from the previously-approved substance
- Cross-document coherence unaffected: REQ-VET-003 still resolves in prd.md, Contracts table rows untouched, no new domain terms introduced

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $5.12 | 17m 20s | 96% |
| `agent-team:system-design-expert` | 3 | opus-5 | $3.19 | 8m 9s | 89% |
| `(parent)` | 1 | opus-5 | $1.38 | 38m 22s | 96% |
| `agent-team:change-grader` | 1 | opus-5 | $1.09 | 2m 58s | 91% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $0.87 | 2m 40s | 90% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.54 | 2m 44s | 87% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.54 | 1m 5s | 88% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.29 | 1m 17s | 90% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.29 | 1m 35s | 87% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.75 | 13m 2s | 97% |
| `agent-team:system-design-expert` | opus-5 | $1.42 | 4m 19s | 88% |
| `(parent)` | opus-5 | $1.38 | 38m 22s | 96% |
| `agent-team:system-design-expert` | opus-5 | $1.11 | 2m 28s | 92% |
| `agent-team:change-grader` | opus-5 | $1.09 | 2m 58s | 91% |
| `agent-team:product-requirements-expert` | opus-5 | $0.87 | 2m 40s | 90% |
| `agent-team:feature-implementer` | opus-5 | $0.83 | 2m 36s | 93% |
| `agent-team:system-design-expert` | opus-5 | $0.65 | 1m 22s | 87% |
| `agent-team:security-reviewer` | opus-5 | $0.54 | 1m 5s | 88% |
| `agent-team:feature-implementer` | opus-5 | $0.54 | 1m 41s | 90% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.41 | 2m 21s | 89% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.29 | 1m 17s | 90% |
| `agent-team:test-reviewer` | sonnet-5 | $0.29 | 1m 35s | 87% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.13 | 23s | 78% |

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
- task fingerprint `dc643d9216b8dc0b` · `2.1.263 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
