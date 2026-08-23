# specialty-directory r1 — v0.2.4

Specialty directory page (feature) · started 2026-08-10T22:44:14+00:00 · exec `claude-dev` · status **complete**

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
| review attention (pipeline grade) | — |

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
| 5 (±0) | 4 (±0) | 4 (±1) | 5 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.68. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController delegates the fold to SpecialtyDirectory.of, keeping the controller free of rules (Web controller row); SpecialtyDirectory is an immutable record with List.copyOf defensive copies, and SpecialtyRepository follows the Repository pattern and naming rules. SpecialtyDirectoryTests are framework-free unit tests, behavior-named (theSpecialtyDirectoryShouldOrderHoldersByLastNameThenFirstName), behind createSpecialty/createVetHolding factories with named IDs. Deductions: ClinicServiceTests.shouldFindAllSpecialtiesInNameOrder breaks the the{Subject}Should{Outcome} school and shadows the field with a local  specialties ; controller tests stub internals with @MockitoBean and assert raw markup (">none\<") and English message prose. noSpecialties lands in base plus nine locales, short of the eleven languages prd.md cites. Docs move fully: REQ-SPEC-001, three contract rows, provenance note, two open questions.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 5 · doc-fit 5

> The fold lives in  SpecialtyDirectory.of  rather than the controller, so  SpecialtyController.showSpecialtyDirectory  only binds and selects a view — no new controller rule; constructor injection, package-private controller, repository read-only with a documented reason for skipping the  vets  cache. Tests are strong:  SpecialtyDirectoryTests  is framework-free, BDD-named, uses  createSpecialty / createVetHolding  factories and named ids, and its copy-making factory guards identity matching. Two deviations:  SpecialtyControllerTests  stubs both repositories with  @MockitoBean  where the policy wants a real or hand-written double first, and  shouldFindAllSpecialtiesInNameOrder  drops the  the{Subject}Should  form;  containsString(">none\<")  also asserts markup. Docs move fully: PRD REQ-SPEC-001 with done-when list, open questions, and three *(designed)* contract rows.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 4

> The fold lives in  SpecialtyDirectory.of  (an immutable record with defensive copies), leaving  SpecialtyController.showSpecialtyDirectory  to bind, delegate, select a view — the Web controller row honored, and the rule unit-testable without the framework.  SpecialtyRepository  is read-only and its uncached choice is explained against the shared  vets  key. Tests are behavior-named, factory-built, phase-separated, and cover empty/unheld/multi-hold/order. Deductions:  shouldFindAllSpecialtiesInNameOrder  mirrors the method rather than a behavior and asserts bare seeded literals "dentistry"/"radiology";  createSpecialty  is duplicated in both new test classes instead of shared vocabulary;  containsString("There are no specialties on record")  hardcodes a message value. system-design marks the three new contracts *(designed)* "until the implementing code lands" — the code lands in this same patch, so those markers arrive stale.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $12.64 | 34m | 29 | 93% | 19 file(s) +517/−2 |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPEC-001 — Specialty directory

2 review rounds · 2 build-passes · no grade yet

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | **✔** | ✎ (1) |

- ◇ **prd-entry** Specialty directory · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 9m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · validate · audit-autofix
- ✔ **review code-quality** · **approved** · ***◷ 55s***
- ✔ **review security** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 2m***
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 3m***
  - [autofix] `SpecialtyDirectoryTests.java:38-49` The input list List.of(dentistry, radiology, surgery) is already in alphabetical order, and the assertion checks the same order back out. This cannot distinguish 'SpecialtyDirectory.of preserves the given order' (the documented contract: 'in the order the specialties were given') from 'SpecialtyDirectory.of resorts by name' — a regression that added an internal sort would still pass this test. theSpecialtyDirectoryShouldOrderHoldersByLastNameThenFirstName already uses a non-alphabetical input (Sharon, Zack, Amy) specifically so the assertion has discriminating power; this test should do the same for the specialty-level order, e.g. List.of(surgery, dentistry, radiology) asserted back in that order.
    - fix: Reorder the input specialties to a non-alphabetical sequence (e.g. surgery, dentistry, radiology) and assert entries come back in that same given order, so the test actually exercises order preservation rather than coinciding with alphabetical sort.
  - [autofix] `SpecialtyRepository.java:34-37` SpecialtyRepository.findSpecialties() — the slice's one new persistence query, including its 'ORDER BY specialty.name' clause — has no integration-level test exercising it against a real database. Both new test classes construct Specialty/Vet objects directly and never touch the repository. The design-block named PetTypeRepository.findPetTypes() as this repository's precedent, and that method is exercised by ClinicServiceTests (@DataJpaTest, real seeded H2 data, asserting name order) — SpecialtyRepository has no equivalent. A typo in the JPQL, wrong ordering column, or wrong entity mapping would pass every currently-existing test.
    - fix: Add a @DataJpaTest case exercising SpecialtyRepository.findSpecialties() against the seeded data (ClinicServiceTests already wires @DataJpaTest with PetTypeRepository as the pattern to copy for a lookup-entity repository), asserting the seeded specialties come back in name order.
- ↻ **implement** (implementer) ← test · (2 findings) · ***◷ 4m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · handoff-log · autofix-audit
- ✔ **review code-quality** · **approved** · ***◷ 44s***
- ✔ **review security** · **approved** · ***◷ 46s***
- ✔ **review test** · **approved** · ***◷ 1m***
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 13s***
  - [autofix] `ClinicServiceTests.java:163-169` The javadoc claims the order assertion is 'the weaker half of that guard against H2 specifically' because 'a query that lost its ORDER BY would read through that index and return the same sequence anyway.' This is inaccurate: the seed data (src/main/resources/db/h2/data.sql) inserts specialties as radiology, surgery, dentistry — not name order. A plain SELECT with no ORDER BY has no defined row order and, absent a predicate on the indexed column, typically returns rows in table/insertion order rather than via the secondary index, i.e. radiology, surgery, dentistry — which would fail the containsExactly("dentistry", "radiology", "surgery") assertion. The comment tells a future reader the ORDER BY clause is unguarded by this test, when the non-alphabetical seed order means it actually is guarded. Left uncorrected, this misleads maintainers about what regression protection exists here.
    - fix: Exercises the specialty query against the seeded schema: JPQL validity, entity  * mapping, and the name order the directory page depends on. The seed data inserts  * specialties as radiology, surgery, dentistry — not name order — so this assertion  * fails if the query's \<code>ORDER BY\</code> clause is lost or wrong.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyDirectory.of documents and correctly implements identifier-based matching, working around BaseEntity's lack of value equality (verified: Vet/Specialty inherit no equals/hashCode override)
- SpecialtyRepository's uncached read is justified with a clear comment explaining the ClassCastException risk from reusing the shared 'vets' Cacheable key, and matches VetRepository's existing Repository\<T,Integer> + @Transactional(readOnly=true) style
- SpecialtyController mirrors VetController's package-private class, constructor-injection, and /*.html GetMapping conventions
- specialtyList.html mirrors vetList.html's existing markup idioms (th:each, holder-none fallback via #{none}) and documents in an HTML comment why the shared nav's menu argument matches no item, per REQ-SPEC-001's explicit no-inbound-link requirement
- noSpecialties key is present and appropriately translated (not just copied English) across all ten message bundles
- Records (SpecialtyDirectory, Entry) are immutable with List.copyOf defensive copies; Javadoc is precise about fold ordering and rationale
- checkFormat passes clean

**security-reviewer**

- No injection surface added: SpecialtyRepository.findSpecialties() is a static, parameterless JPQL string (SELECT specialty FROM Specialty specialty ORDER BY specialty.name) with no concatenation and no nativeQuery; SpecialtyController takes no request parameters, path variables, or form binding, so no attacker-controlled value reaches the data access layer.
- Output escaping holds: specialtyList.html renders every dynamic value through th:text (specialty name, holder first/last name) with Thymeleaf's default escaping intact. Swept the whole new template for the unescaped-output class - no th:utext, no [[...]] inlining, no th:attr sink carrying model data. Consistent with the existing vetList.html pattern and with the system-design Threat Model row on cross-site scripting.
- Data exposure weighed and judged not a new disclosure: /specialties.html publishes veterinarian full names grouped by specialty, which is the same data set already served unauthenticated at /vets.html (HTML) and /vets (serialized). The slice re-projects public data rather than exposing a new PII class, so it introduces no new row in the system-design Threat Model. The absent navigation entry is a product decision (PRD open question), not a security control - it is not obscurity being relied on, since the underlying data is already linked and reachable.
- No new authentication or authorization boundary is crossed: the endpoint is read-only GET with no mutating path, and it inherits the project-wide no-auth posture already recorded in system-design Security Context. The design's read-only intent is enforced structurally - SpecialtyRepository extends the bare Repository marker and declares only @Transactional(readOnly = true) reads, exposing no save or delete.
- Supply chain unchanged: build.gradle, settings.gradle, and gradle/ carry no diff, so no dependency was added, upgraded, or repinned and no new CVE surface enters with this slice.
- No secrets introduced: swept the full change set for credential-shaped material (password, secret, token, api key, credential) and for dangerous execution or deserialization sinks (Runtime.exec, ProcessBuilder, readObject, createQuery, nativeQuery, string-concatenated queries) - zero hits. The ten message-bundle additions are a single plain-text noSpecialties value per locale, rendered through an escaped th:text.
- Model exposure is bounded: the controller publishes a SpecialtyDirectory value type built before rendering, with defensive List.copyOf in both record constructors, so the view holds no repository handle and no lazily loaded association that could widen what the page reads.

**doc-reviewer**

- PRD boundary held: docs/prd.md#req-spec-001 states the specialty directory behaviorally (single page, stored name, full-name holders, held-by-none, no navigation entry) and never names the GET /specialties.html address; the route lives only in docs/system-design.md#contracts (SpecialtyController row), correctly deferred as mechanism per the what/how litmus test.
- New REQ-SPEC-001 anchor, Done-when bullets (each opening with the REQ-ID), and numbered Edge cases follow the prd-authoring format exactly, matching the sibling Veterinarian directory section's shape; the two new Open Questions entries are genuinely open (order, entry point) and do not silently resolve a scope question.
- Minting REQ-SPEC- as a new prefix rather than extending REQ-VET is consistent with this PRD's existing convention of one prefix per capability-area section (OWN, PET, VIS, VET, LANG, SYS) - the specialty directory is a distinct page/capability from the veterinarian directory, not a VET sub-case.
- docs/system-design.md#contracts additions verified against source: SpecialtyRepository, SpecialtyDirectory, and SpecialtyController rows' class names, the /specialties.html route, the name-ordered uncached query, and the identifier-based fold all match the landed code exactly (spot-checked SpecialtyController.java, SpecialtyRepository.java, SpecialtyDirectory.java, specialtyList.html).
- The rescoped provenance banner and the new 'assembled outside its controller' invariant paragraph correctly carry the (designed) marker for post-survey design statements not yet re-derived from code; per the design-block notes this is doc-sync's job to drop once implemented, out of scope for this review.
- Cross-references resolve: both **Design:** links target system-design.md#contracts, which exists; the req-spec-001 anchor is well-formed and matches the doctor's anchor pattern; no orphaned or broken intra-file links introduced.
- No PRD-prohibited patterns found: no code blocks, no Java constructs, no field/parameter tables, no rationale prose, no hardcoded route or constant; system-design.md additions carry no field/parameter tables and no transcribed constant literals, and no new imperative line lacking an ADR back-link.

**test-reviewer**

- Unit/MockMvc split matches testing-principles' pyramid guidance: fold behavior lives in plain-object SpecialtyDirectoryTests with no Spring context, HTTP/view concerns stay in the MockMvc slice — no logic duplicated between the two layers.
- createVetHolding's deliberate per-vet Specialty copies (SpecialtyDirectoryTests) are a real regression guard for BaseEntity's missing equals/hashCode, with a javadoc that explains why rather than narrating what — confirmed by reading SpecialtyDirectory.of, which matches holders to specialties by getId(), not object identity.
- BDD test names throughout (the{Subject}Should{Outcome}) read as specifications and match the PRD's test_names list plus one justified addition for the multi-specialty criterion.
- Four-phase structure held cleanly (blank-line-separated arrange/act/assert, no phase comments) in every test read.
- Three-tier data naming observed: RADIOLOGY_ID/SURGERY_ID/DENTISTRY_ID name meaningful values by role; no bare mystery literals.
- AssertJ used fluently throughout (extracting/tuple/flatExtracting); MockMvc's content().string(containsString(...)) is the correct idiom for that API and is not a violation of the no-JUnit-assertEquals rule.
- On the implementer's flagged trade-off (asserting the rendered English 'There are no specialties on record' vs. an id-based selector): the content-string assertion is judged acceptable. It verifies the actual behavior an acceptance criterion names ('reports that there are none rather than failing') at the one layer that renders it, is internally consistent with the file's other three content assertions including the sibling '>none\<' check, and no existing controller test in this codebase establishes a competing convention to prefer. The trade-off is real (a wording-only edit to the base bundle breaks this test), but content assertions on rendered MockMvc output are an accepted pattern here and the alternative (an id/CSS selector) would only prove an empty block rendered, not that the required message text is present.
- New classes carry 100% line coverage per jacocoTestReport (SpecialtyDirectory, SpecialtyDirectory.Entry, SpecialtyController, Specialty), exceeding the 80% domain-package target in testing-principles.md.

**code-quality-reviewer**

- Production code verified byte-identical to the prior approved pass (no  M /staged diff against SpecialtyController.java, SpecialtyDirectory.java, SpecialtyRepository.java; only docs, message properties, and two test files changed)
- SpecialtyDirectoryTests's reordered input (surgery, dentistry, radiology) now actually discriminates SpecialtyDirectory.of() preserving caller order rather than re-sorting, unlike the prior alphabetical fixture
- ClinicServiceTests.shouldFindAllSpecialtiesInNameOrder's javadoc claim about H2's specialties_name index verified against src/main/resources/db/h2/schema.sql:21
- checkFormat and compileJava/compileTestJava pass clean

**security-reviewer**

- Production-code identity claim verified rather than trusted: re-read all four production artifacts under review (SpecialtyController, SpecialtyRepository, SpecialtyDirectory, specialtyList.html) and confirmed they carry exactly the shapes the prior round approved - a parameterless static JPQL query with no concatenation and no nativeQuery, a controller with no request parameter, path variable, or form binding, defensive List.copyOf in both record constructors, and a template whose every dynamic value renders through th:text. The untracked production files carry an mtime later than the prior review, but the co-touched tracked file (Specialty.java) shows no git diff at the same timestamp, identifying the touch as a content-neutral bulk formatter rewrite; content inspection confirms it for the untracked files.
- Delta is test-side plus comments and crosses no trust boundary: the non-alphabetical input in SpecialtyDirectoryTests is in-test literal data, and the new ClinicServiceTests.shouldFindAllSpecialtiesInNameOrder autowires the existing read-only SpecialtyRepository inside the existing @DataJpaTest context. No production API was added or widened, no new endpoint, no new binding, and no new data reaches a rendered page - the exposure surface assessed last round is unchanged.
- Class sweep over the delta surface for the unescaped-output, dangerous-sink, and injection classes found zero instances: no th:utext, no [[...]] Thymeleaf inlining, no Runtime.exec, no ProcessBuilder, no nativeQuery, no EntityManager.createQuery, no readObject.
- Secret sweep over the delta clean: the ClinicServiceTests diff carries no credential-shaped material (password, secret, token, api key, credential); the added literals are the three seeded specialty names asserted in name order.
- Supply chain unchanged on this pass: build.gradle, settings.gradle, and gradle/ carry no diff, so no dependency was added, upgraded, or repinned and no new CVE surface enters with the fix round.
- The new javadoc on SpecialtyRepository documenting why the specialty reads stay uncached is prose only - it names a correctness hazard in cache-key reuse, states no credential or internal address, and leaks nothing an attacker could use.

**test-reviewer**

- Finding 1 resolved: theSpecialtyDirectoryShouldListEverySpecialtyOnOnePage now feeds List.of(surgery, dentistry, radiology) — a non-alphabetical input — and asserts containsExactly("surgery", "dentistry", "radiology") back in that same given order, giving the assertion real discriminating power against an internal-sort regression, matching the sibling holder-order test's pattern.
- Finding 2's substance is resolved, and the Red-check discipline behind it is sound. shouldFindAllSpecialtiesInNameOrder exercises SpecialtyRepository.findSpecialties() against real seeded H2 data via the ClinicServiceTests @DataJpaTest-equivalent harness, following the shouldFindAllPetTypes precedent named in the original finding. It closes the JPQL-validity and entity-mapping gaps the finding raised (a typo or wrong entity mapping now fails this test) and catches an ORDER BY on the wrong column: verified against src/main/resources/db/h2/data.sql, which seeds specialties as (radiology, surgery, dentistry) — not alphabetical — so an ORDER BY id or insertion-order regression would produce a different sequence than the asserted (dentistry, radiology, surgery) and fail.
- The one honestly-scoped residual gap — an entirely deleted ORDER BY clause coincidentally still returning name order on this H2 fixture — is empirically grounded, not asserted from theory: the implementer ran the Red check by deleting the clause and observing the test still pass, and cross-checked the schema (src/main/resources/db/h2/schema.sql:21, CREATE INDEX specialties_name ON specialties (name)) as the mechanism. Given the seed order is not already alphabetical, this is a real, non-obvious H2 optimizer behavior rather than a coincidence of insertion order, so the empirical claim is credible.
- The javadoc replacing the comment states the limit plainly and accurately: it says the order assertion is 'the weaker half of that guard against H2 specifically' for the lost-ORDER-BY case, without overclaiming general ORDER BY coverage. This is the right resolution under tested-as-spec — restoring production code unchanged (correct, since the test cannot force a Red state here) and documenting the honest limit beats deleting a test that still earns its keep on JPQL validity, entity mapping, and wrong-column ordering.
- Re-ran the two affected test classes (SpecialtyDirectoryTests, ClinicServiceTests) via ./gradlew test — both pass cleanly, and production code (SpecialtyRepository.java) is byte-identical to the version already reviewed and approved by security-reviewer and code-quality-reviewer.

**doc-reviewer**

- The other test-reviewer autofix (SpecialtyDirectoryTests.theSpecialtyDirectoryShouldListEverySpecialtyOnOnePage) is correctly applied: input specialties are now given in the non-alphabetical order surgery, dentistry, radiology and asserted back in that same order, giving the assertion real discriminating power against an internal re-sort — matches the pattern already used by theSpecialtyDirectoryShouldOrderHoldersByLastNameThenFirstName.
- shouldFindAllSpecialtiesInNameOrder correctly closes the integration-test gap the test-reviewer identified: it exercises SpecialtyRepository.findSpecialties() through @DataJpaTest against real seeded H2 data, following the ClinicServiceTests/PetTypeRepository precedent named in the design-block.
- No docs/ changes in this delta (confirmed via scripts/changeset.sh and the handoff timeline); docs/prd.md and docs/system-design.md content approved in the prior review round still matches the landed code — no re-review needed for those files.
- No new PRD-boundary, cross-document coherence, or structural issues introduced by this delta.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $3.92 | 14m 52s | 96% |
| `agent-team:system-design-expert` | 1 | opus-5 | $1.76 | 6m 0s | 93% |
| `(parent)` | 1 | opus-5 | $1.47 | 34m 0s | 95% |
| `agent-team:security-reviewer` | 2 | opus-5 | $1.08 | 2m 18s | 87% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $1.01 | 4m 52s | 95% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $0.92 | 2m 44s | 91% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.70 | 4m 42s | 91% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.44 | 1m 57s | 91% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.07 | 0s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $2.82 | 10m 18s | 97% |
| `agent-team:system-design-expert` | opus-5 | $1.76 | 6m 0s | 93% |
| `(parent)` | opus-5 | $1.47 | 34m 0s | 95% |
| `agent-team:feature-implementer` | opus-5 | $1.10 | 4m 33s | 95% |
| `agent-team:product-requirements-expert` | opus-5 | $0.92 | 2m 44s | 91% |
| `agent-team:security-reviewer` | opus-5 | $0.55 | 1m 16s | 86% |
| `agent-team:security-reviewer` | opus-5 | $0.53 | 1m 1s | 88% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.53 | 2m 22s | 95% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.48 | 2m 30s | 94% |
| `agent-team:test-reviewer` | sonnet-5 | $0.47 | 3m 10s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.23 | 1m 3s | 90% |
| `agent-team:test-reviewer` | sonnet-5 | $0.23 | 1m 32s | 86% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.21 | 54s | 92% |
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

- plugin `agent-team-spring-boot` at `v0.2.4` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.226 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
