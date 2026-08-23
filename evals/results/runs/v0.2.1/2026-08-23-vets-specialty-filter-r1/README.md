# vets-specialty-filter r1 — v0.2.1

Filter the vet list by specialty (feature) · started 2026-08-23T08:01:37+00:00 · exec `claude-dev` · status **complete**

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
| review attention (pipeline grade) | — |

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
| 4 (±0) | 4 (±0) | 4 (±1) | 5 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.75. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in a derived repository query ( findBySpecialtiesNameIgnoreCase ) with the controller only binding and delegating, matching the Repository/Web-controller rows; the deliberate omission of  @Cacheable  is reasoned in the ADR. The blank-to-null rule in  specialtyFilter  is a small new rule sitting in the controller and untestable without the framework, widening the pyramid gap the principles name. The template repeats the same  ${filtered} ? @{...} : @{...}  ternary across five links — Thymeleaf drops null URL params, so one parameterized expression would do; that fivefold copy is the main reviewer flag. Tests are behavior-named, constant-driven, and exercise real dispatch and seeded data, though the HTML-substring link assertions are brittle. Documentation is comprehensively current: PRD, ADRs, contracts, defects, vocabulary all move.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in the repository as a derived case-folding query (VetRepository.findBySpecialtiesNameIgnoreCase), with the controller only binding and delegating — the right seams, no new type, no cache key on caller text (documented in the uncached-query ADR). The blank/strip rule in VetController.specialtyFilter is still a new rule decided in a controller and only reachable by booting the web layer, which the pyramid and Web-controller checklist both flag. Tests are behavior-named, constant-named, and cover case, padding, prefix, empty-match, blank, and URL-encoding of markup characters; but new VetControllerTests cases extend Mockito stubbing and assert raw href substrings, and listedVetLastNames casts the 'listVets' model attribute. The template repeats the same filtered/unfiltered ternary five times. Docs are thorough and consistent.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 3 · doc-fit 4

> Repository-level derived queries (VetRepository.findBySpecialtiesNameIgnoreCase) keep filtering out of the controller and match the catalog's Repository row; the controller adds only blank-to-null binding normalization, mirroring owner search, and both ADRs justify the uncached path. Tests read as specifications (theVetPageShouldNotMatchAPartialSpecialtyName) and cover case, padding, prefix, empty-match, blank, and both surfaces against the real seeded DB; weaker points are asserting on model internals via an unchecked cast to List\<Vet> (listedVetLastNames) and on totalItems, and page-2 filtering proven only through rendered links with a Mockito stub. vetList.html repeats a five-way  filtered ? ... : ...  ternary that Thymeleaf's null-parameter omission makes unnecessary, plus a narrating comment block. Docs are thorough, but "ten further questions" reduced to "six" while system-design keeps seven open items.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $14.06 | 40m | 7 | 95% | 11 file(s) +445/−31 |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Veterinarian directory can be narrowed to one specialty

1 review round · 2 build-passes · **1 build-failure** · no grade yet

| reviewer | R1 |
| --- | --- |
| **code-quality** | **✔** |
| **test** | ✎ (1) |
| **security** | **✔** (1) |
| **doc** | ✎ (1) |

- ◇ **prd-entry** Veterinarian directory can be narrowed to one specialty · (prd-expert) · ***◷ 4m***
- ◈ **design-block** **new** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 13m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · format · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · (1 finding) · ***◷ 1m***
  - [clarify] `VetControllerTests.java:123-131` The link-encoding regression test asserts only a space (specialty=internal%20medicine). The characters that would matter if the URL-expression encoding were ever replaced by string concatenation - double quote, angle bracket, and ampersand - are unasserted, so the escaping guarantee is only pinned for the benign case. Behavior itself is safe today: @{/vets.html(page=..., specialty=${specialty})} URL-encodes the value and th:href HTML-escapes the attribute, so a payload like " onmouseover=alert(1) x=" renders percent-encoded inside the href and cannot break out of the attribute. This is a coverage question for the test reviewer, not a defect.
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `VetControllerTests.java:133-140` The implementer's stated reason for keeping all three new pagination-link tests on the VetRepository stub is that the seeded H2 schema holds at most two vets per specialty against a page size of five, so a filtered multi-page result cannot arise from real rows. That reasoning is verified correct for the two filtered cases (surgery: 2 vets; the unseeded 'internal medicine' specialty: 0 vets) - VetRepository is read-only (extends plain Repository, no save method), so an integration test cannot seed extra rows to force a filtered multi-page result, and stubbing is a legitimate exception under the brief's mocking policy (docs/testing-principles.md SS Mocking Policy) for those two. It does not hold for theVetPagePaginationShouldOmitTheSpecialtyWhenTheListIsUnfiltered: this case has no specialty filter at all, and the seeded db/h2/data.sql already ships 6 vets against the controller's page size of 5, so an UNFILTERED /vets.html request against the real seeded database already spans two pages today, with zero setup. A new test should reach for a real implementation first per the brief; here one fit and was not used. Recommend moving this one case into VetSpecialtyFilterIntegrationTests (or a sibling real-data test) asserting the page-2 link omits the specialty parameter against the real 6-vet seed, leaving the two genuinely-constrained filtered cases on the stub.
    - fix: Move theVetPagePaginationShouldOmitTheSpecialtyWhenTheListIsUnfiltered out of VetControllerTests into the real-seeded VetSpecialtyFilterIntegrationTests, asserting the page-2 pagination link on an unfiltered GET /vets.html omits the specialty parameter, using the real 6-vet/page-size-5 seed instead of a MockitoBean stub.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 2m***
  - **[escalate]** `CLAUDE.md:Build Commands` CLAUDE.md's Build Commands table names `./gradlew formatJava` and `./gradlew checkJavaFormat`, but this project's `build.gradle` applies `io.spring.javaformat` and declares tasks `format` and `checkFormat` (confirmed via `./gradlew tasks --all`). The documented task names do not exist, so any agent following CLAUDE.md verbatim hits a task-not-found failure. The system-design-expert's design-block for this slice already flagged this as outside its write scope; CLAUDE.md has no owning agent in the review-workflow Artifact Ownership table, so it needs a human or root decision on who corrects it, not an autofix.
- ◆ **implement** (implementer) · ***◷ 3m***
  - ▲ **build ✓ clean** · build · test · format · handoff-log · autofix-audit
- • review-plan (review-plan-engine)

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- VetRepository.findBySpecialtiesNameIgnoreCase folds case in the query (both Collection and Page overloads) and carries no @Cacheable, matching the ADR and design-block risk mitigation exactly; Javadoc explains why the annotation is absent instead of just noting it
- VetController.specialtyFilter mirrors the existing OwnerController strip-then-treat-blank-as-absent idiom (null check, strip(), empty-to-null) rather than introducing a new convention or an unwarranted Optional wrapper
- vetList.html selects between two whole @{...} expressions on a th:with="filtered=${specialty != null}" local exactly as the superseding design-block specifies, so an unfiltered link stays byte-identical to today's and no parameter is emitted empty; the inline Thymeleaf comment documents why
- Derived query method name resolves correctly against Vet.specialties (Set\<Specialty>) and Specialty.name, confirmed by reading Vet.java's field mapping
- Test naming (VetControllerTests and the new VetSpecialtyFilterIntegrationTests) follows the BDD-style convention already in the roster's test_names, and the integration test exercises real MockMvc dispatch, real Thymeleaf rendering and the real seeded H2 data with no stubbing
- ./gradlew checkFormat passes with no reformatting needed

**security-reviewer**

- Injection: both new repository reads are Spring Data derived queries (findBySpecialtiesNameIgnoreCase / +Pageable) with no @Query and no string-concatenated SQL or JPQL; the caller value binds as a JDBC parameter. Consistent with the SQL-injection row of the system-design threat model.
- Cache growth: the ADR's central decision holds in the code. VetRepository lines 71-83 carry @Transactional(readOnly=true) only - no @Cacheable on either filtered method. @Cacheable("vets") remains solely on the two unfiltered findAll methods (lines 45, 55), whose keys carry no caller-supplied text. CacheConfiguration is untouched, so no anonymous caller can grow the unevictable, size-unlimited vets cache by varying the specialty parameter.
- Rendered-link injection: every pagination link in vetList.html (lines 33-60) uses Thymeleaf URL-expression parameter syntax, never concatenation; the value is URL-encoded and then HTML-escaped as an attribute. Grep for th:utext across src/main/resources/templates returns nothing, so the specialty value reaches no unescaped sink. The unfiltered branch omits the parameter entirely rather than emitting an empty one.
- Reflected-value scope: the model attribute specialty is set only when a filter is in effect (VetController:49-52) and is consumed solely by the href expressions - it is not echoed into page text, a title, or a script block.
- JSON endpoint: /vets reinstated with an optional specialty parameter returns the same Vets projection over the same entity graph as before; the parameter narrows rows and adds no field, so no data becomes reachable that an unfiltered call did not already return. Jackson serialization path is unchanged.
- Input handling: specialtyFilter strips and treats blank as no filter (VetController:89-95); no value is interpolated into a path, a file operation, a command, or a deserialization sink. Whole-name matching means no wildcard or LIKE metacharacter reaches the query.
- Supply chain: the change set touches no build.gradle, dependency lock, or properties file - no new or upgraded dependency is introduced, so the slice adds no third-party attack surface.
- No hardcoded credential, token, or key appears anywhere in the diff; the only literals added are specialty names and test fixtures.

**test-reviewer**

- All 8 test_names from the prd-entry are present and passing, plus 7 additional cases (padded-specialty, empty-JSON-result, blank-JSON, encode-value) - full acceptance-criteria coverage confirmed against docs/prd.md's REQ-VET-003 Done-When and Edge-Case list
- VetSpecialtyFilterIntegrationTests is a genuine @SpringBootTest + @AutoConfigureMockMvc integration test against the real seeded H2 schema with no stubs, correctly exercising real dispatch, real Thymeleaf rendering, and the real specialties join
- VetController.java shows 100% instruction and 100% branch coverage in the jacocoTestReport for this slice, and the tests are behavior-asserting rather than coverage padding
- Test naming follows the brief's the{Subject}Should{Outcome} BDD school; test data uses named Tier-1/Tier-2 constants with no bare mystery literals; four-phase structure with blank-line separation is observed throughout both files
- ./gradlew test passes cleanly for the vet package (15/15 tests green)

**doc-reviewer**

- PRD REQ-VET-003 narrative, anchor, and six "Done when" bullets are behavioral, terms resolve against ubiquitous-language.md, and no mechanism or code identifiers leak into the PRD
- NG-9 is narrowed rather than withdrawn in both the Non-Goals table and its preamble, consistent with the product-owner constraint and the new non-goal ADR
- REQ-VET-002 stays withdrawn and its ID is never reused, stated consistently in prd.md Superseded, the Open Questions answer, and the non-goal ADR
- The stale JSON-route known-defect edge case is fully removed with no dangling references left in prd.md or system-design.md
- The corrected banner count (six open questions) matches the actual unstruck-question count after the three new questions are added
- The three new open questions (paging, repeated specialty parameters, visible control) are recorded as open/deferred, not declined, matching the product-owner constraint on the visible control
- Both new ADRs follow the non-goal/decision ADR conventions (em-dashes, Non-goal/Requirements Implementation fields) and are indexed correctly in adr/README.md
- docs/system-design.md Request Contracts, the Vets/VetRepository/VetController rows, the retired known defect, the extended open question 5, the Threat Model rendered-link row, and the Security Context input all agree with each other and with VetController.java, VetRepository.java, and vetList.html
- docs/ubiquitous-language.md's new Specialty filter entry is consistent with the Specialty and Veterinarian entries and correctly scopes NG-9 via its Avoid line
- All new cross-references (PRD anchors, ADR links, system-design anchors) resolve

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $5.39 | 19m 54s | 97% |
| `agent-team:system-design-expert` | 2 | opus-5 | $2.55 | 7m 14s | 94% |
| `(parent)` | 1 | opus-5 | $1.75 | 39m 55s | 96% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.47 | 4m 50s | 93% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.65 | 1m 20s | 88% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.60 | 2m 40s | 95% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.47 | 2m 37s | 92% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.35 | 1m 27s | 89% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.07 | 14s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.87 | 14m 8s | 97% |
| `agent-team:system-design-expert` | opus-5 | $1.84 | 5m 21s | 95% |
| `(parent)` | opus-5 | $1.75 | 39m 55s | 96% |
| `agent-team:product-requirements-expert` | opus-5 | $1.47 | 4m 50s | 93% |
| `agent-team:feature-implementer` | opus-5 | $1.16 | 4m 21s | 96% |
| `agent-team:system-design-expert` | opus-5 | $0.71 | 1m 53s | 91% |
| `agent-team:security-reviewer` | opus-5 | $0.65 | 1m 20s | 88% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.60 | 2m 40s | 95% |
| `agent-team:test-reviewer` | sonnet-5 | $0.47 | 2m 37s | 92% |
| `agent-team:feature-implementer` | opus-5 | $0.36 | 1m 24s | 93% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.35 | 1m 27s | 89% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.07 | 14s | 50% |

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
- task fingerprint `064d588523591361` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
