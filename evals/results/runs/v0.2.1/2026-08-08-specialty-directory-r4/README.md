# specialty-directory r4 — v0.2.1

Specialty directory page (feature) · started 2026-08-08T21:13:52+00:00 · exec `claude-dev` · status **complete**

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
| review attention (pipeline grade) | clear |

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
| 5 (±0) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.71. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Grouping lives in an immutable read model (SpecialtyDirectory.of, defensive List.copyOf) rather than the controller, which only binds and selects a view; SpecialtyRepository exposes one read, naming matches the catalog, and the ADR covers the new type — this reads like the original authors. Unit tests are behavior-named, four-phase, factory-built and assertion-rich. Deductions: SpecialtyControllerTests uses @MockitoBean stubs, which the principles tolerate but do not encourage for new tests, and asserts on markup detail (class=\"specialty-without-holders\", id=\"no-specialties\", not containsString("?page=")); the radiology()/surgery()/vetHolding() factories are duplicated verbatim across both test classes instead of shared vocabulary; messages_hi.properties adds literal Devanagari into a file otherwise fully \u-escaped. Docs move everywhere the change touches: ADR plus index, prd REQ-VET-003 with done-when and open questions, system-design package tree, contracts, invariants and outputs.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> Grouping is lifted out of the controller into an immutable  SpecialtyDirectory  record (List.copyOf in both compact constructors), so the new rule is unit-testable without the web layer;  SpecialtyController  only binds, delegates, and selects a view, dependencies are constructor-injected, names follow the Controller/Repository suffix rules, and the non-catalog read model is justified by an ADR. Unit tests are exemplary: behavior names, factory methods, named ids, no phase comments, empty/unheld/tie edge cases. Weaker:  @MockitoBean  stubs for a one-method repository where a hand-written double was trivial (principles call framework stubs a last resort); factories ( radiology() ,  vetHolding ) duplicated verbatim across both test classes instead of a shared vocabulary; controller tests assert markup detail ( class="specialty-without-holders" ,  not(containsString("?page=")) ). Template joins names via a trailing-space concatenation hack;  messages_hi  mixes raw Devanagari into an escaped file. Docs (ADR, prd REQ-VET-003, contracts table, package structure, security outputs, all bundles) leave nothing stale.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController.showSpecialtyDirectory only reads, delegates, and selects a view; the grouping and ordering sit in the immutable SpecialtyDirectory record with defensive List.copyOf, and the new-type choice is justified by the ADR — layering and catalog rules hold. SpecialtyDirectoryTests is exemplary: BDD names, factory methods, named ids (RADIOLOGY_ID), no phase comments. But SpecialtyControllerTests duplicates ~30 lines of the same factories instead of sharing vocabulary, restates unit-owned behavior (theSpecialtyDirectoryShouldListEverySpecialtyByItsStoredName appears in both), stubs internal repositories with @MockitoBean rather than a hand-written double, and asserts on markup detail (class=\"specialty-without-holders\", not containsString("?page=")). messages_hi.properties adds raw Devanagari amid \u-escaped neighbors. PRD, system-design contracts, package structure, security outputs, and the ADR index all move together.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $15.22 | 38m | 37 | 91% | 20 file(s) +665/−9 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $3.10 | 5m 21s | 93% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · **2 build-failures** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (1) | **✔** |

- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 2m***
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert)
- ◈ **design-block** **new** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 12m***
  - ▲ **build ✗ build failed** · retry 1
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 34s***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 40s***
- ✔ **review security** · **approved** · ***◷ 57s***
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 1m***
  - **[blocked]** `system-design.md:72-108` system-design.md was not updated for this slice, but the code it should describe already exists (build-pass at line 15 covers SpecialtyController, SpecialtyDirectory, SpecialtyRepository, and specialtyList.html). The Contracts table has no rows for the three new vet-package types, so a reader following REQ-VET-003's `**Design:** [system-design.md#contracts](system-design.md#contracts)` link finds no trace of the feature. The new ADR's own References section points at the same section for the same reason. The Security Context 'Outputs it produces' list and the route inventory implied by VetController's row are also silent on the new /specialties.html route. Deferring this to a later doc-sync pass is not correct: the doc-sync skill's Maintenance Rules table requires system-design.md updates (summaries, patterns, constants reference) when adding a feature, and the code triggering that requirement is already merged in this same slice — there is no future point at which 'once code exists' becomes true that isn't now.
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `SpecialtyControllerTests.java:73-118` testing-principles.md's Three-Tier Data Naming convention requires irrelevant (Tier 2) values to carry a SOME_/ANY_ prefix or come from an anonymous factory that auto-generates them, and meaningful (Tier 1) values to be named by role. Every vetHolding(...) call in both files passes a bare integer literal for the vet id. In most tests the id is irrelevant scaffolding (e.g. vetHolding("Helen", "Leary", 2, radiology)) and should not require the caller to invent a number. In theSpecialtyDirectoryShouldOrderHoldersSharingANameByTheirIdentifier (SpecialtyDirectoryTests.java:110-119) the ids 9 and 2 are Tier 1 — they are exactly what the test's outcome (ordering) depends on — yet appear as unnamed literals rather than role-named constants (e.g. LOWER_ID/HIGHER_ID).
    - fix: Change the vetHolding(...) factory in both test files to auto-generate the id (e.g. an incrementing counter or a fixed default) and drop the id parameter from call sites where it is irrelevant, keeping an explicit-id overload only for tests where the id is the value under test (the identifier tie-break case), and name those meaningful ids by role instead of using bare literals.
- ↻ **implement** (implementer) ← test · (1 finding)
- ↻ **fix design** ← doc · (1 finding)
- ◈ **design-block** **new** · (design) · ***◷ 3m***
- ▲ **build-pass** 21:49 · build, test, check, checkFormat, handoff-log, autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review test** · **approved** · ***◷ 27s***
- ✔ **review code-quality** · **approved** · ***◷ 44s***
- ✔ **review security** · **approved** · ***◷ 32s***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ◆ **grade CLEAR** · add the read-only specialty directory page
  - blast_radius — **clear** — Purely additive: three new files in the vet package, one new template, and a one-line message key in each of the ten populated bundles. Not one existing production Java file, template, or build file is modified, so no existing request path changes behavior. No sensitive path is touched, and the new route serves specialty and veterinarian names already published unauthenticated at /vets.html and /vets.
  - semantic_surprise — **clear** — The read model does exactly what its size and prose suggest, and its three non-obvious choices are deliberate and each pinned by a test: holders are grouped on Specialty.getId() rather than on the entity (which inherits identity equality, so the naive map keyed by Specialty would split one row into two), both comparators carry an id tie-break, and SpecialtyRepository.findAll deliberately omits the cache annotation because a second no-argument cached read under the vets cache would collide on the shared empty key. Defensive copies in both compact constructors and fresh lists in the grouping mean the shared vet cache is never mutated. No inverted condition, no off-by-one, no flipped boundary anywhere in the 31 hunks. The Hindi bundle stores its new line as raw Devanagari while its older lines use unicode escapes, which is cosmetic only: the bundle set is already read as UTF-8 and four other locale files already carry raw UTF-8.
  - test_adequacy — **clear** — The tests would fail against a broken implementation rather than merely restating it. SpecialtyDirectoryTests drives the identity trap directly by passing two distinct Specialty instances of the same row, and separately pins name order, last-then-first holder order, the id tie-break, an unheld specialty, and the empty clinic. SpecialtyControllerTests renders the real Thymeleaf template through MockMvc and asserts on rendered content, including two negatives that matter: no paging markup and no link to the page's own address. Every done-when bullet in the requirement has a matching assertion.
  - reviewer_hedging — **clear** — The full four-reviewer battery was dispatched and all four returned approved with zero findings in the second round. Round one produced one blocked doc finding (system-design.md not updated for code that already existed) and one fixable test-data-naming finding; both were reworked and each reviewer named the specific fix delta in its re-approval. No escalate tag, no approval-with-caveats, and no lingering worry is recorded anywhere in the log.
  - scope_deviation — **clear** — The diff matches the triaged surface with nothing extra: no navigation link was added (the requirement forbids one), no write path to specialties exists, and no unrelated refactor rode along. The single design revision was a superseding design-block that added docs/adr/README.md to supporting_paths for the autofix audit, not an architectural rethink. The row's build_retries of 0 understates the slice's history, and reading the log rather than the counter resolves it: the two build-failure records are a planned mid-dispatch checkpoint and that same audit-coverage gap, neither a code defect.
  - why — Additive change in one package that modifies no existing code path, with the three genuinely tricky decisions (entity-identity grouping, Java-side ordering, the deliberately uncached read) each documented and pinned by a test a broken implementation would fail. Confirm and merge; if you read one file, read SpecialtyDirectory.of.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyDirectory.of documents the identity-equality hazard (grouping by specialty id, not the Specialty instance) and both comparators explain their tie-break rationale — javadoc carries real design context, not restatement
- SpecialtyRepository javadoc explains why the read carries no @Cacheable (would collide with the shared 'vets' cache key), matching the ADR's stated constraint
- Records used correctly for the read model: SpecialtyDirectory and the nested SpecialtyHolders are immutable with List.copyOf defensive copies in compact constructors
- SpecialtyController mirrors VetController's shape (constructor injection, @Controller, single @GetMapping returning a view name) so the new controller reads as familiar to anyone who has seen the existing one
- Test suites in both SpecialtyControllerTests and SpecialtyDirectoryTests use AssertJ, BDD-style names, and factory methods (radiology()/vetHolding()) for construction; no magic literals
- checkFormat passes clean; messages.properties additions are present and consistent across all locale files

**security-reviewer**

- New endpoint GET /specialties.html is read-only: no request parameters, no path variables, no request body, so the change opens no new input boundary and needs no binder disallow list
- Data access uses Spring Data repository derived reads only (SpecialtyRepository.findAll, VetRepository.findAll) with @Transactional(readOnly = true); no string-concatenated or native query text is introduced
- Output escaping holds: specialtyList.html renders every stored value through th:text (specialty name, holder first/last name) and every literal through message keys; no th:utext, inline JavaScript, or DOM injection anywhere in the new template
- No widening of the exposed data surface: specialty names and veterinarian names are already served unauthenticated by GET /vets.html and GET /vets; the directory is a re-projection of data already public at the baseline
- No new endpoint that mutates state and no change to management-endpoint exposure; the controller documents what the page exposes
- No secrets introduced: the ten message-bundle additions are UI strings only, and no credential, connection string, or key literal appears anywhere in the diff
- No file, path, resource-name, or deserialization operation is introduced; the view name is a compile-time constant, not request-derived
- Supply chain unchanged: build.gradle, settings.gradle, and the gradle/ directory are absent from the change set, so no new or upgraded dependency enters and no CVE surface is added
- SpecialtyDirectory.of treats both reads as read-only inputs and copies collections defensively in the record constructors, so the shared vets cache cannot be mutated through the directory

**doc-reviewer**

- docs/prd.md: REQ-VET-003 narrative stays behavioral — no mechanism, no route string, no code identifier; the 'reachable by address alone' phrasing correctly avoids naming /specialties.html
- docs/prd.md: anchor \<a id="req-vet-003">\</a> present at first mention; every Done-when bullet and edge case ties to a REQ-ID; REQ-VET-002 withdrawal correctly moved to Superseded with a resolvable mapping and no dangling anchor
- docs/adr/2026-08-08-specialty-directory-read-model.md: Implementation section carries Requirements: REQ-VET-003; Options Considered uses em-dashes; decision rationale (identity-equality pitfall, Java-side ordering, cache key collision) stays out of system-design.md and PRD as it should
- docs/adr/README.md: new index row added in date order with a resolving link and correct Status
- docs/ubiquitous-language.md: Specialty and Veterinarian terms used in the new PRD prose already match the canonical definitions, no drift

**test-reviewer**

- Both PRD-named test files exist in the vet package with the exact five PRD test names present, plus additional edge-case tests (empty clinic, navigation/no-link, identifier tie-break, grouping by stored identity) matching the design-block's called-out risks
- SpecialtyDirectoryTests is a true unit test (no I/O, no Spring context) that widens the pyramid's unit tier per testing-principles.md's guidance to test logic without booting the framework
- SpecialtyControllerTests uses @WebMvcTest + MockMvc (the sanctioned mock) against the real Thymeleaf template and real message bundle content, exercising genuine rendering behavior rather than a mocked view
- New production classes (SpecialtyDirectory, SpecialtyController, SpecialtyHolders) sit at 100% line coverage, well above the 80% brief target
- AssertJ used throughout the unit test file; four-phase structure with blank-line separation and no narration comments in both files; construction wrapped in factory methods, never raw constructors; BDD the{Subject}Should{Outcome} naming followed consistently
- Grouping-by-identifier and case-sensitive-ordering risks flagged in the design-block are each pinned by a dedicated test (theSpecialtyDirectoryShouldGroupOnTheStoredIdentityRatherThanTheSpecialtyInstance, theSpecialtyDirectoryShouldOrderHoldersSharingANameByTheirIdentifier)
- Full ./gradlew test run (Specialty* filter) passes with no failures

**test-reviewer**

- vetHolding(...) in both SpecialtyDirectoryTests and SpecialtyControllerTests now auto-generates the vet id via a static nextVetId counter, eliminating the invented Tier 2 literal at every call site that does not care about identity
- theSpecialtyDirectoryShouldOrderHoldersSharingANameByTheirIdentifier now uses a dedicated explicit-id overload (vetHolding(int id, ...)) reserved for the one test where the id is Tier 1 (the outcome under test), with role-named constants LOWER_VET_ID/HIGHER_VET_ID and locals renamed higherIdHelenLeary/lowerIdHelenLeary matching their meaning
- SpecialtyControllerTests dropped the id parameter from vetHolding(...) entirely since no caller in that file needed an explicit id, keeping the factory signature minimal
- Swept the fix-delta diff for further bare-id-literal instances in vetHolding(...) call sites across both files: none remain
- ./gradlew test --tests "*Specialty*" passes with no failures

**code-quality-reviewer**

- vetHolding(...) factories in both SpecialtyDirectoryTests and SpecialtyControllerTests now auto-generate the vet id via a static incrementing counter, dropping the id parameter entirely from call sites where it is irrelevant scaffolding (Tier 2) — no more caller-invented literals
- SpecialtyDirectoryTests keeps an explicit-id overload (vetHolding(int id, String, String, Specialty...)) used only in theSpecialtyDirectoryShouldOrderHoldersSharingANameByTheirIdentifier, where the id is the value under test; the ids are now named by role via LOWER_VET_ID/HIGHER_VET_ID constants and the local variables (lowerIdHelenLeary/higherIdHelenLeary) instead of bare literals
- Swept both files (grep for vetHolding(") call sites): no remaining bare-literal id arguments anywhere in the delta
- checkFormat passes clean on the reworked test files
- docs/system-design.md fix delta: Contracts table gains rows for SpecialtyDirectory, SpecialtyRepository, and SpecialtyController with source-file and Implements citations; Implements cells for Vet, Specialty, and VetRepository extended with REQ-VET-003; Invariants paragraph documents SpecialtyDirectory's unpersisted nature and the Java-side ordering with an ADR back-link; package-structure line and Security Context outputs updated to mention the new route and its unlinked-but-unguarded reachability — closes the doc-reviewer's blocked finding with no code-identifier drift from the actual source

**security-reviewer**

- Fix delta touches only two test classes and docs/system-design.md; no production code, template, message bundle, build file, or dependency changed since the round-1 approval, so no new attack surface is introduced and no supply-chain re-verification applies.
- Test-factory rework substitutes a monotonic static id counter for hand-passed ids and adds a two-arg overload for the id-ordering case. It affects only in-memory fixture construction under src/test/java; no test seeds untrusted data into a real store, weakens a security assertion, or introduces a credential.
- No hardcoded secret in the delta. The only matches for password/secret/credential are pre-existing Security Context prose in docs/system-design.md restating the already-documented plaintext datasource defaults, unchanged by this delta.
- The new Security Context 'Outputs it produces' entry accurately records the reachability of /specialties.html: it states the route is unlinked and that nothing restricts who may open it, and explicitly declines to treat the absence of a link as access control. That is the honest posture statement for an application with no authentication layer anywhere, and it makes the exposure legible to the next reader rather than implying a guard that does not exist.
- Output escaping on the reviewed surface still holds: src/main/resources/templates/vets/specialtyList.html renders every stored specialty name and holder name through th:text with no th:utext, so Thymeleaf escapes all database-derived content.

**doc-reviewer**

- docs/system-design.md Contracts table now carries SpecialtyDirectory, SpecialtyRepository, and SpecialtyController rows, each citing its source file and REQ-VET-003, closing the round-1 blocked finding
- REQ-VET-003 added to the Implements cells of Vet, Specialty, and VetRepository, matching the code's actual read paths
- 'Invariants the rows cannot carry' now states SpecialtyDirectory is unpersisted, names the missing inverse association and Java-side ordering, and back-links the ADR for the reasoning without duplicating it
- Package Structure line for vet/ widened to two repositories, a read model, and controllers, matching the package's actual contents
- Security Context 'Outputs it produces' lists the specialty directory at /specialties.html and states the unlinked-but-unguarded reachability, matching the ADR and PRD framing
- Provenance banner amended in the same edit to cover statements added after the bootstrap survey, so the document does not claim a false provenance for the new material
- docs/prd.md's existing **Design:** [system-design.md#contracts](system-design.md#contracts) link and the ADR's References entry to the same anchor both now resolve to a section that documents the feature
- No other doc surface (prd.md, ubiquitous-language.md, adr/README.md) changed in this delta, and none needed to â€” the round-1 approved_aspects on those files still hold

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $9.00 | 21m 17s | 96% |
| `agent-team:system-design-expert` | 3 | opus-5 | $5.17 | 8m 32s | 87% |
| `(parent)` | 1 | opus-5 | $4.22 | 43m 46s | 95% |
| `agent-team:change-grader` | 1 | opus-5 | $3.10 | 5m 21s | 93% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $2.47 | 4m 12s | 92% |
| `agent-team:security-reviewer` | 2 | opus-5 | $2.02 | 1m 51s | 80% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.56 | 3m 32s | 90% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.47 | 3m 28s | 86% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $1.19 | 1m 38s | 79% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.13 | 7s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $5.92 | 13m 2s | 96% |
| `(parent)` | opus-5 | $4.22 | 43m 46s | 95% |
| `agent-team:change-grader` | opus-5 | $3.10 | 5m 21s | 93% |
| `agent-team:product-requirements-expert` | opus-5 | $2.47 | 4m 12s | 92% |
| `agent-team:system-design-expert` | opus-5 | $2.11 | 3m 45s | 91% |
| `agent-team:system-design-expert` | opus-5 | $2.07 | 3m 43s | 85% |
| `agent-team:feature-implementer` | opus-5 | $1.91 | 5m 56s | 96% |
| `agent-team:security-reviewer` | opus-5 | $1.21 | 1m 6s | 84% |
| `agent-team:feature-implementer` | opus-5 | $1.16 | 2m 18s | 90% |
| `agent-team:test-reviewer` | sonnet-5 | $1.05 | 2m 54s | 90% |
| `agent-team:system-design-expert` | opus-5 | $0.99 | 1m 3s | 76% |
| `agent-team:security-reviewer` | opus-5 | $0.81 | 45s | 71% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.78 | 1m 55s | 89% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.77 | 1m 36s | 91% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.66 | 47s | 80% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.54 | 51s | 79% |
| `agent-team:test-reviewer` | sonnet-5 | $0.43 | 33s | 66% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.13 | 7s | 0% |

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
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.226 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
