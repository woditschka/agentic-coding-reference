# specialty-directory r1 — v0.3.10

Specialty directory page (feature) · started 2026-09-08T18:22:32+00:00 · exec `claude-dev` · status **complete**

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
| reading depth (pipeline grade) | scrutinize |

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
| 4 (±1) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.62. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Placement is right: the inversion lives in the immutable  SpecialtyDirectory  record, leaving  SpecialtyController.showSpecialtyDirectory  to bind, delegate, and select a view, so no rule lands in the controller;  SpecialtyRepository  follows the existing repository idiom. Formatting holders into display strings ( getFirstName() + " " + getLastName() ) pushes response shaping below the web layer, a minor layering smudge.  specialtyList.html  references  #{none}  (and  #{specialties} ) with no messages bundle addition in the patch, and the tests only assert  contains(RADIOLOGY, ...) , so a missing key would ship unnoticed across eleven locales. Tests are exemplary in naming, factories, and hand-written stubs, but the stub beans are shared mutable state reset in  emptyTheClinic() . Docs (PRD REQ-VET-003, contracts table, package line, open questions) are fully current.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Inversion, ordering and full-name formatting live in the immutable SpecialtyDirectory record (defensive List.copyOf in both compact constructors), leaving SpecialtyController.showSpecialtyDirectory a bind-delegate-select method with no rule — the catalog's Web controller bar. SpecialtyRepository mirrors VetRepository's style; naming and the design-doc contract rows match. Tests are behavior-named (theSpecialtyDirectoryShouldListASpecialtyHeldByNoVeterinarian), phase-separated, factory-built, hand-stubbed rather than mock-framework, and push logic into unit tests. Weaknesses: the factory helpers createASpecialty/createAVeterinarian are duplicated verbatim across both test classes instead of a shared vocabulary, and the singleton stub beans are shared mutable fixtures reset by emptyTheClinic. specialtyList.html adds #{none} with no messages entry, and SpecialtyRepository's ORDER BY duplicates BY_STORED_NAME. Docs updated fully.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Inversion logic sits in an immutable  SpecialtyDirectory  record with defensive copies, leaving  SpecialtyController.showSpecialtyDirectory  to bind, delegate, and select a view — no new rule in the controller, and naming matches the catalog. The repository's  ORDER BY specialty.name  is immediately re-sorted by  BY_STORED_NAME , redundancy the javadoc excuses rather than removes, and display-name concatenation in the value object is arguably response shaping. Tests are behavior-named, factory-built, hand-written stubs over a mock framework, and cover empty/unheld/no-specialty edges; but the  createASpecialty / createAVeterinarian  factories are duplicated verbatim across both test classes, and assertions construct  new SpecialtyListing(...)  directly.  specialtyList.html  references  #{specialties} ,  #{vets} ,  #{none}  with no message keys added and no test catching that. Docs are fully current.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $10.02 | 32m | 29 | 94% | 8 file(s) +584/−5 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.89 | 2m 12s | 90% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

1 review round · 1 build-pass · **1 build-failure** · grade **SCRUTINIZE**

| reviewer | R1 |
| --- | --- |
| **code-quality** | **✔** |
| **test** | **✔** |
| **security** | **✔** |
| **doc** | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **minor** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 13m***
  - ▲ **build ✗ build failed** · retry 1
  - ▲ **build ✓ clean** · handoff-log · build · test · format · check · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved** · ***◷ 48s***
- ✔ **review code-quality** · **approved** · ***◷ 50s***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Not verified against the NVD: this project configures no OWASP Dependency-Check plugin (no dependencyCheck in build.gradle), and the reviewer has no network access, so no CVE match ran in this review. The change set adds no dependency and changes no version, so the supply-chain surface is identical to the last pass; the resolved framework versions to close the check against elsewhere (CI or a human) are Spring Boot 4.1.1 and the io.spring.dependency-management 1.1.7 BOM, per build.gradle:5-6. Reported as not run, not as clean.
  - ▹ rec: Robustness, not a security defect -- SpecialtyDirectory.java:183-188 dereferences three nullable columns without a guard: Comparator.comparing(Specialty::getName) at :183, and .comparing(Vet::getLastName).thenComparing(Vet::getFirstName) at :185-187. src/main/resources/db/h2/schema.sql:12-13 and :19 declare vets.first_name, vets.last_name, and specialties.name all nullable, so a row seeded with a null name makes the request throw NullPointerException and land on the error page, which renders the exception message (system-design.md Known Defects). The NPE text carries no sensitive value, and there is no application write path for vets or specialties (NG-2), so the attacker path is conjectural and the severity does not support a fix-routable finding. Worth noting as pattern divergence rather than exposure: getId at :188 is already nullsLast-guarded in the same comparator chain, and the neighboring vetList.html renders a null name as the text "null" instead of failing. Consider nullsLast on the two name comparators if the class is revisited.
- ◆ **grade SCRUTINIZE** · add the specialty directory page
  - blast_radius — **skim** — Purely additive: three new classes, one new template, two new test classes, all inside the vet package, plus doc rows; no existing source file is modified, one new read-only GET route is added, and the only shared state touched is the cached vet collection, which is read and stream-copied rather than sorted in place.
  - semantic_surprise — **scrutinize** — The comparators in SpecialtyDirectory are where the surprises sit: specialties are ordered by name alone, so two specialties sharing a name fall back to the query row order, which is weaker than the collation-independence the new system-design paragraph claims; and the name accessors are unguarded while getId is nullsLast-guarded in the same chain, so a null name throws where the neighboring vet list renders the text null.
  - test_adequacy — **skim** — Seven unit tests over real Vet and Specialty instances cover every acceptance criterion and all three PRD edge cases, and the two controller tests render the real template through MockMvc against hand-written repository stubs, asserting page content plus the negative that a specialty-less vet never appears; the ordering tests feed deliberately arbitrary input, so they would fail against an implementation that merely passed the input order through.
  - reviewer_hedging — **scrutinize** — All four planned reviewers approved with zero findings, but the security approval carries two recommendations: the dependency CVE check is reported as not run rather than clean because the project configures no dependency-check plugin and the reviewer had no network, and the null-name NPE path is logged as robustness divergence deliberately left unfixed.
  - scope_deviation — **skim** — No consultations, no design revisions, and the single build retry is a planned partial-artifact checkpoint at the end of TDD cycle 2 rather than a failing gate; the diff matches the requirement stated surface, including the recorded non-goal that the page gets no navigation entry.
  - why — Additive, well-tested, and unanimously approved, so read narrowly. Open the two comparators in SpecialtyDirectory: name-only specialty ordering does not fully deliver the collation-independence the design paragraph now claims, and the name accessors are unguarded where getId is not. The security approval also reports the CVE check as not run.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**test-reviewer**

- SpecialtyDirectoryTests exercises the inversion, ordering, and full-name formatting as pure unit tests over real Vet/Specialty instances — no framework boot, matching the design's assignment of these rules to the SpecialtyDirectory value object
- SpecialtyControllerTests uses hand-written SpecialtyRepositoryStub/VetRepositoryStub via @TestConfiguration rather than a mock framework, matching the design-block's named integration-point doubles and the brief's mocking policy
- MockMvc used correctly as the one sanctioned framework stub for the HTTP transport boundary
- BDD test naming (the{Subject}Should{Outcome}) applied consistently across both new test classes
- Three-tier data naming observed: role-named constants (RADIOLOGY, HELEN_FIRST_NAME), test-owned factories (createASpecialty, createAVeterinarian, createAVeterinarianHoldingNoSpecialty) with counter-generated identities, no mystery literals
- All 5 declared test names present and passing per coverage-map; all 3 PRD edge cases (unheld specialty listed, stable order, empty clinic) covered with dedicated tests at the correct (unit) layer
- Stable-order tests for both specialty order and holder order guard the exact risk the design-block flagged (vendor-dependent DB collation)
- One-page/no-pagination behavior correctly tested at the controller (boundary) layer via a 6-specialty fixture, matching where the design assigns that concern
- ./gradlew test green for both new test classes; four-phase structure with blank-line separation and no phase comments observed throughout

**code-quality-reviewer**

- SpecialtyDirectory.of is the single static-creator entry point; both records use compact constructors with List.copyOf defensive copies (value-object pattern)
- Ordering is applied in-memory via explicit Comparators rather than trusted from the query, matching the documented risk mitigation against database-collation drift
- SpecialtyController stays a thin binder: it reads both repositories and delegates the inversion, ordering, and full-name formatting entirely to SpecialtyDirectory, matching the Web controller row in the pattern catalog
- SpecialtyRepository mirrors the existing PetTypeRepository lookup-repository shape and is read via a hand-written stub in the @WebMvcTest slice, consistent with the mocking policy
- specialtyList.html reuses existing message keys (specialties, name, vets, none) and adds no new key, avoiding an eleven-bundle sync burden; no nav entry was added to fragments/layout.html, matching the recorded non-goal
- Naming (SpecialtyDirectory, SpecialtyListing, SpecialtyRepository, SpecialtyController) matches docs/ubiquitous-language.md and the Contracts rows added to docs/system-design.md
- Comments are WHY-only (render-order rationale) or purpose javadoc; conventions-map shows no restated-signature or requirement-id comments
- Test naming and data setup follow the project's BDD/builder-method conventions already in force

**doc-reviewer**

- PRD requirement req-vet-003 uses behavioral language only, no class/method names, and correctly delegates the route address to system-design.md per house style
- New requirement ID reuses the vet capability prefix and takes the number after the highest existing one under it (REQ-VET-002), consistent with prd-authoring rules
- system-design.md Contracts rows for SpecialtyRepository, SpecialtyDirectory, SpecialtyController stay at contract-level abstraction: no field or parameter tables, no literal constants, purpose prose plus source pointer only
- Every requirement ID added to system-design.md (REQ-VET-003) exists in prd.md; no deprecated requirement (REQ-VET-002) referenced in system-design.md
- Domain terms used (Veterinarian, Specialty) are already defined in ubiquitous-language.md; no new term introduced that needs a definition
- Non-goal (no navigation entry to the new page) is recorded in the requirement prose and Open Questions rather than misstated as a formal Non-Goals table row, matching the intake decision that NG-2 is unchanged
- Cross-reference docs/prd.md -> system-design.md#contracts resolves; anchor req-vet-003 present and unique
- New page reuses the shared layout fragment, so it still satisfies REQ-SYS-001's site-wide navigation acceptance criterion despite carrying no menu entry pointing to itself

**security-reviewer**

- Cross-site scripting (security-principles.md Realization, XSS row): every value the new page renders goes through Thymeleaf's escaping th:text -- specialtyList.html:11 (${listing.specialtyName}), :13 (${holderName + ' '}), and the #{} message keys. No th:utext, no __${...}__ preprocessing, no inline script, no external resource, no href anywhere in the template (grep for utext, __${, javascript:, onclick, \<script>, http:// over specialtyList.html returns nothing). Holder names are formatted in Java and rendered as text, never as markup.
- Injection into data access: SpecialtyRepository's one @Query is a fixed JPQL literal with no parameter and no concatenation; no request-derived value reaches it. The route takes no path variable, no query parameter, and no request body, so no untrusted string enters the persistence layer at all.
- Widening the exposed surface (Realization row): one GET route, read-only, no mutation, no management endpoint touched. What it exposes -- the specialty names and veterinarian full names already published by /vets.html -- is stated in the new docs/system-design.md Contracts row for SpecialtyController. No actuator exposure change. The absent authentication is the recorded demonstration baseline (system-design.md Security Context) and is not a finding here.
- Mass assignment: SpecialtyController binds nothing -- no @ModelAttribute, no form-backed type, no identifier from the request -- so the disallow-list requirement has no surface to apply to.
- Least privilege at the data boundary: the new read carries @Transactional(readOnly = true), matching VetRepository and PetTypeRepository.
- Concurrency: SpecialtyController is a stateless singleton holding only two repository references. SpecialtyDirectory and SpecialtyListing are records that List.copyOf both lists at construction, so the model attribute handed to the view is deeply immutable. SpecialtyDirectory.of only reads the @Cacheable("vets") collection -- stream().sorted() copies rather than sorts in place -- so the shared cached list is never mutated by the new path.
- Resource use: no unbounded growth introduced. The vet roster read is the existing cached VetRepository.findAll(); the specialty read is a small unpaged lookup table, and the unpaged page is the product decision recorded in the prd-entry. No file handle, no stream, no executor, no network call is opened.
- Credentials and logging: the diff adds no credential, no connection string, no URL, and no log statement; grep over the new vet sources for Runtime/ProcessBuilder/exec(, enableDefaultTyping/JsonTypeInfo, FileWriter, new Random, System.out/System.err, and /tmp/ returns nothing. No new exception message is constructed, so nothing new can reach the error page that renders exception text.
- Supply chain: build.gradle is not in the change set -- no dependency added, removed, or version-bumped, and the nohttp plain-HTTP check is untouched. Test doubles are hand-written stubs, adding no test-scope dependency either.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 1 | opus-5 | $4.78 | 14m 17s | 97% |
| `agent-team:system-design-expert` | 1 | opus-5 | $1.30 | 4m 13s | 89% |
| `(parent)` | 1 | opus-5 | $1.23 | 34m 19s | 95% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.90 | 2m 1s | 89% |
| `agent-team:change-grader` | 1 | opus-5 | $0.89 | 2m 12s | 90% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $0.81 | 2m 27s | 88% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.41 | 1m 54s | 94% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.31 | 1m 4s | 91% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.27 | 58s | 88% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.78 | 14m 17s | 97% |
| `agent-team:system-design-expert` | opus-5 | $1.30 | 4m 13s | 89% |
| `(parent)` | opus-5 | $1.23 | 34m 19s | 95% |
| `agent-team:security-reviewer` | opus-5 | $0.90 | 2m 1s | 89% |
| `agent-team:change-grader` | opus-5 | $0.89 | 2m 12s | 90% |
| `agent-team:product-requirements-expert` | opus-5 | $0.81 | 2m 27s | 88% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.41 | 1m 54s | 94% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.31 | 1m 4s | 91% |
| `agent-team:test-reviewer` | sonnet-5 | $0.27 | 58s | 88% |

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
- task fingerprint `dc643d9216b8dc0b` · `2.1.263 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
