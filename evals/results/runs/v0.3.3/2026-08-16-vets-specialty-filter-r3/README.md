# vets-specialty-filter r3 — v0.3.3

Filter the vet list by specialty (feature) · started 2026-08-16T02:46:37+00:00 · exec `claude-dev` · status **complete**

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

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.98. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The filter sits where the catalog puts it: a derived query on VetRepository (findDistinctBySpecialtiesNameIgnoreCase) with the controller only binding, normalizing blanks, and selecting the read — no new business rule in the controller. Deductions: findPaginated/findVets duplicate the null-branch, and vetList.html repeats the same narrowed ternary five times, so any link change must be made five ways. Tests are behavior-named (theVetListShouldNotMatchAPartialSpecialtyName) and phase-separated, and firstOfTwoPages is a real factory, but "radiology"/"surgery"/"Douglas"/"Ortega" stay bare Tier-3 literals and new stubs reach for Mockito rather than a hand-written double. Documentation is complete: NG-9 narrowed, REQ-VET-003/004 minted, the defect row retired, threat model and open questions updated, two ADRs indexed.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Filtering lands in the repository as a derived query ( findDistinctBySpecialtiesNameIgnoreCase ), leaving the controller as an adapter that only normalizes blank input, mirroring owner search; the cache departure is recorded in an ADR. Minor debt: the null-branch is duplicated in  findPaginated  and  findVets , and the template repeats the same  narrowed ? ... : ...  ternary five times. Tests follow the  the{Subject}Should{Outcome}  school, reuse  james() / helen()  and add  firstOfTwoPages , and cover case-insensitivity, prefix non-match, blank value, empty result, paging and encoding; but ClinicServiceTests leaves mystery literals ("surgery", "Douglas",  getById(..., 3) ), and new controller tests extend mock-framework stubbing. Documentation is comprehensive: NG-9 narrowing, REQ-VET-003/004, superseded note, contracts, threat-model row, defect row removed, open questions.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The filter lands where it belongs: matching is a derived query ( findDistinctBySpecialtiesNameIgnoreCase ), the controller only normalizes the parameter and selects a read, mirroring the empty owner search; the cache departure is recorded in an ADR naming the principle departed from. Two near-identical branch helpers ( findPaginated ,  findVets ) and five copies of the  ${narrowed} ? ... : ...  ternary in vetList.html are avoidable duplication a reviewer would flag. Tests are behavior-named and phase-structured, cover blank, padded, no-match, case, paging and encoding on both surfaces, but carry Tier-3 literals: bare "radiology"/"surgery" alongside named  specialtyNoVetHolds , and  getById(surgeons, Vet.class, 3) ,  isEqualTo(2)  undeclared. Documentation is complete: NG-9 narrowed, REQ-VET-003/004 minted, defect row retired, threat model and open questions current.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $15.42 | 61m | 43 | 94% | 10 file(s) +382/−29 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.22 | 3m 47s | 89% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VETSSPECIALTYFILTER-001 — Reader narrows the veterinarian directory to one specialty by address

2 review rounds · 2 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | · |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | · |
| **doc** | **✔** | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Reader narrows the veterinarian directory to one specialty by address · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **new** · (design) · ***◷ 6m***
- ◆ **implement** (implementer) · ***◷ 13m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyle · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 34s***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply-chain check not run against the NVD: the OWASP dependency-check plugin is not configured in build.gradle, and this reviewer has no network access, so no CVE match was performed. Resolved versions read from ./gradlew dependencies for the record: Spring Boot 4.1.0, spring-core 7.0.8, thymeleaf 3.1.5.RELEASE, tomcat-embed-core 11.0.22, hibernate-core 7.4.1.Final, tools.jackson.core:jackson-databind 3.1.4. Treat the check as not run, not as clean. Since the change set touches no build file, this is a standing project gap for CI to close, not a defect of this slice.
  - ▹ rec: Follow-up outside this change set: ownersList.html still builds its paging hrefs with __${...}__ preprocessing. It is safe today (only integers are interpolated), but vetList.html now demonstrates the safer link-expression form; converting the owner list would make one pattern hold across both directories.
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `ClinicServiceTests.java` docs/system-design.md § Contracts now states as durable behavior that surrounding whitespace is stripped before specialty matching (a padded, non-blank value like " radiology " still matches). No test in the suite exercises this: VetControllerTests only covers a whitespace-only (fully blank) specialty (theVetListShouldIgnoreABlankSpecialty, theVetJsonShouldIgnoreABlankSpecialty), and ClinicServiceTests' new findDistinctBySpecialtiesNameIgnoreCase tests use unpadded values only ("surgery", "SuRgErY", "surg"). A now-documented behavior with zero coverage is exactly the gap this checklist exists to catch.
    - fix: Add a ClinicServiceTests case, e.g. theVetListShouldMatchASpecialtyNameWithSurroundingWhitespace, asserting findDistinctBySpecialtiesNameIgnoreCase(" surgery ") still returns Douglas and Ortega.
- ↻ **implement** (implementer) ← test · (1 finding) · ***◷ 2m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyle · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 49s***
- ✔ **review test** · **approved** · ***◷ 56s***
- ◆ **grade CLEAR** · narrow both vet directory surfaces to one specialty
  - blast_radius — **clear** — Contained to the vet feature package: three production files (VetController, VetRepository, vetList.html) in one module, no sensitive path, no build file, schema, configuration or dependency change, and no new endpoint - two existing routes each gain one optional read-only query parameter. The 43-hunk count is inflated by five docs files and the mechanical rewrite of five paging links; the reachable production surface is small.
  - semantic_surprise — **clear** — Read every production hunk. normalized() maps null, empty and whitespace-only to no filter and strips otherwise; both handlers branch to the derived findDistinctBySpecialtiesNameIgnoreCase only when a specialty survives normalization, so the unfiltered paths behave exactly as before. The template rewrite preserves each paging expression verbatim (page i, 1, currentPage minus 1, currentPage plus 1, totalPages) while replacing the old preprocessing form with link-expression parameters, so no off-by-one hides in the new ternaries. The one genuinely new semantic - DISTINCT paging across the eager Vet-Specialty many-to-many - is pinned by real-database tests asserting totalElements 2, totalPages 2, one row per page, and each matched vet still carrying its full specialty set. Filtered paging inherits the unfiltered page's absence of an explicit sort, unchanged in kind. The th:each loop variable named specialty inside the table shares a name with the new model attribute but sits in a scope disjoint from the paging div, so nothing shadows.
  - test_adequacy — **clear** — 197 test lines against 97 production lines, and the tests exercise the changed behavior rather than restate it: ClinicServiceTests drives the real derived query through DataJpaTest for whole-name matching, case-insensitivity, prefix non-match, an unheld specialty, distinct paging totals and specialty-set retention, while VetControllerTests covers both surfaces through MockMvc for filtering, blank and padded values, empty results, paging-link carry and omission, and percent-encoding of URL syntax. The padded-whitespace test discriminates by stubbing only the unpadded value, so deleting the strip call fails it rather than passing vacuously. Residual: the first and previous paging branches are never rendered by a test, but their expressions are preserved character-for-character from the pre-change template.
  - reviewer_hedging — **clear** — Final state carries zero open findings. The round-1 test-reviewer finding was resolved and both round-2 reviewers (test-reviewer, doc-reviewer - the fix-delta roster) approved with substantive verification and no recommendations; code-quality and security approved in round 1 and were correctly not re-dispatched, since the fix delta was a single added test method with no production change. The security-reviewer's two round-1 recommendations are not reservations about this change: the un-run NVD scan is a standing project gap (no dependency-check plugin configured) that a zero-dependency-delta change cannot conceal anything behind, and the ownersList.html note is an explicitly out-of-changeset follow-up.
  - scope_deviation — **clear** — The diff matches the intake's stated surface exactly - one optional specialty parameter on two existing routes, no form or dropdown on either surface, pagination carrying the parameter. The two PRD moves that look like scope growth (narrowing NG-9, minting REQ-VET-003 for the machine-readable route) are verbatim owner decisions from the intake record, each landed with the ADR the project's convention requires. build_retries 0 and consultations 0; the single design revision was a superseding design-block correcting its own supporting_paths list after the autofix audit, with no design or production change implied.
  - why — A contained, well-tested feature that does exactly what its record describes: normalization, query branching and paging expressions all read as stated, and the one real risk - distinct paging over the eager many-to-many - is pinned by real-database assertions. Confirm and merge.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- VetController.normalized() mirrors OwnerController's existing blank-search convention (null->broadest, strip whitespace), keeping the two endpoints' null-handling consistent with codebase precedent
- VetRepository javadoc explains the uncached findDistinctBySpecialtiesNameIgnoreCase methods and cross-references the ADR, giving future readers the rationale without re-deriving it
- Private helper methods (normalized, findPaginated, findVets) keep each method single-responsibility and under 15 lines
- vetList.html pagination-link comment explains the percent-encoding and null-omission behavior, which is non-obvious Thymeleaf behavior
- checkFormat passes; no System.out/printStackTrace/TODO left in the changed production files

**doc-reviewer**

- Both new ADRs (non-goal narrowing, uncached specialty reads) carry Options Considered, a Decision, Consequences, and an Implementation section with Non-goal/Requirements fields and em-dash references, per format
- docs/adr/README.md index gains both new rows with correct dates and titles
- docs/prd.md: NG-9 row narrowed with an inline ADR link, the narrowing also recorded in the standing Non-Goals framing paragraph; REQ-VET-003 and REQ-VET-004 anchors added alongside REQ-VET-001; new Done-when bullets and renumbered edge cases (no external citations to the old numbering exist) are behavioral, no mechanism leakage; Superseded entry for REQ-VET-002 correctly points to the new REQ-VET-003 without reusing the withdrawn id; three residual Open Questions recorded rather than silently decided
- docs/system-design.md: new Contracts prose paragraph and updated Implements columns correctly cite REQ-VET-003/004; Known Defects row for the machine-readable route removed with an explanatory note rather than silently deleted; Threat Model gains a cache-growth row citing the ADR; Open Questions item 5 amended in place; all new prose stays at the right abstraction level (states the matching/caching/URL-encoding behavior, not field-by-field tables)
- Cross-document coherence verified: PRD links the non-goal ADR (product decision), system-design links the caching ADR (mechanism decision) — correct split; ADR back-links to prd.md#non-goals and prd.md#req-vet-004 resolve against the added anchors; production code diff (VetController, VetRepository, vetList.html) matches every claim made in the docs (IgnoreCase query, no @Cacheable, whitespace-stripping, link-expression percent-encoded paging hrefs); 'Specialty' domain term already defined in ubiquitous-language.md, no new domain term introduced

**security-reviewer**

- Injection into data access: the specialty filter uses Spring Data derived queries (findDistinctBySpecialtiesNameIgnoreCase) with a bound parameter. No string-concatenated query text anywhere in the change set; grep over src/main for Runtime/ProcessBuilder/exec, @Query concatenation, and manual SQL returned nothing new.
- Cross-site scripting: the request-derived specialty is never rendered as text. It reaches the template only as a link-expression parameter (@{/vets.html(page=..., specialty=${specialty})}), which URL-encodes the value, on top of Thymeleaf's default attribute escaping. VetControllerTests.thePaginationLinksShouldEncodeASpecialtyCarryingUrlSyntax proves '\<' and '&' emerge as %3C/%26 and the raw text never appears. Sweep of src/main/resources/templates found no th:utext and no new unescaped sink.
- Template-expression injection: the change removes the pre-existing __${...}__ preprocessing from every paging link in vetList.html in favour of parameterized link expressions. No request-derived value enters preprocessing. The remaining __${...}__ uses elsewhere (ownersList.html, ownerDetails.html, fragments/layout.html) are outside this change set and interpolate integers and fixed link names only.
- Cache poisoning / unbounded cache growth: the two filtered reads are deliberately not @Cacheable, with the reason (caller-supplied key of unbounded cardinality in an unevicted, unbounded cache) stated at the declaration and in docs/adr/2026-08-16-uncached-specialty-filtered-vet-reads.md. This is the fail-secure choice and avoids a real memory-exhaustion vector.
- Boundary validation: normalized() handles null, empty, and whitespace-only at the controller boundary and strips surrounding whitespace, matching how the owner search normalizes an absent last name (pattern consistency held). Both entry points share the one normalizer.
- Exposed surface: no new endpoint. Two existing routes gain one optional read-only query parameter; no mutating path, no management endpoint, no broader actuator exposure. Both surfaces are documented in docs/system-design.md.
- Mass assignment: the parameter binds to a String method argument, not to a command object, so no identifier binding is reachable.
- Concurrency and resource handling: the controller stays stateless (no new fields), the repository methods are @Transactional(readOnly = true), Vet.specialties is FetchType.EAGER so no serialization-time lazy-init leak on the JSON route, and no streams or handles are opened.
- Secrets and logging: no credential-shaped literal added, no logging added, no exception message constructed, no System.out/System.err. Change set contains no build.gradle, no properties, and no configuration file.
- Supply chain: no dependency added, removed, or version-changed in the change set.

**test-reviewer**

- Case-insensitive and whole-name (non-prefix) matching are tested at the repository/integration layer (ClinicServiceTests), matching where the logic actually lives per testing-principles.md's pyramid guidance, rather than duplicated as controller mocks
- Blank/whitespace-only specialty normalization is tested on both surfaces (HTML and JSON)
- Pagination link carrying/omitting the specialty is tested, including URL-encoding of a specialty containing HTML/URL-syntax characters (cat & \<dog>), which doubles as reflected-XSS coverage for the templated href
- 'No vet holds this specialty' returns HTTP 200 with an empty list on both surfaces, matching the PRD acceptance criterion
- New test names follow the the{Subject}Should{Outcome} BDD school from testing-principles.md § Test Naming
- New tests reuse existing factories (james()/helen()) and real repository/DB integration (@DataJpaTest) rather than adding new mocks; no verify()-based interaction testing was introduced
- ./gradlew test passes cleanly; VetController shows 100% instruction coverage (0 of 113 missed) per the jacoco report; generated SQL confirms the distinct/IgnoreCase derived query matches the design record

**doc-reviewer**

- Fix-delta since basis touches only src/test/java/.../VetControllerTests.java (new test theVetListShouldMatchASpecialtyPaddedWithWhitespace); no docs/ file in this round's delta, confirmed via scripts/changeset.sh --base-tree --name-only
- The new test verifies controller-level whitespace stripping (normalized() in VetController.java), which is the code path docs/system-design.md § Contracts already documents ('Surrounding whitespace is stripped before matching'); no drift between doc claim and verified behavior introduced by this fix
- No PRD edge case governs padded (non-blank) whitespace specifically (edge case 3 covers empty/whitespace-only only), so no PRD change was expected or needed for this fix
- Round-1 doc-reviewer approval (cross-document coherence, ADR format, anchors, PRD/system-design boundary) stands unchanged by this delta

**test-reviewer**

- Round-1 finding (line 20) resolved: theVetListShouldMatchASpecialtyPaddedWithWhitespace covers the now-documented whitespace-stripping behavior, and the implementer's round-1 response (implementation-plan.md) correctly redirected the fix from ClinicServiceTests to VetControllerTests — stripping happens in VetController.normalized(), not in the derived repository query, so a padded value never reaches SQL; a repository-level test as originally requested would not have exercised the real behavior
- The new test discriminates: it stubs the repository on the unpadded value only, so removing .strip() from normalized() would fail the test (unstubbed mock miss) rather than passing vacuously
- Test follows the host file's established conventions: given()/BDDMockito stubbing idiom, MockMvc against a @MockitoBean VetRepository (the file's existing pattern for controller-layer tests), BDD test name, meaningful variable naming (paddedSpecialty)
- Scope of the fix (HTML surface only, not duplicated on JSON) is reasoned and correct: both handlers share the same private normalized() method, so a second case would re-exercise one code path without adding coverage
- ./gradlew test passes cleanly with the new test included

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $5.41 | 19m 30s | 97% |
| `agent-team:system-design-expert` | 2 | opus-5 | $3.27 | 8m 51s | 95% |
| `(parent)` | 1 | opus-5 | $2.19 | 64m 37s | 97% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.56 | 4m 15s | 94% |
| `agent-team:change-grader` | 1 | opus-5 | $1.22 | 3m 47s | 89% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.73 | 1m 53s | 90% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.68 | 3m 18s | 89% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.66 | 2m 29s | 93% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.19 | 45s | 87% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.96 | 14m 15s | 97% |
| `agent-team:system-design-expert` | opus-5 | $2.33 | 6m 34s | 96% |
| `(parent)` | opus-5 | $2.19 | 64m 37s | 97% |
| `agent-team:product-requirements-expert` | opus-5 | $1.56 | 4m 15s | 94% |
| `agent-team:change-grader` | opus-5 | $1.22 | 3m 47s | 89% |
| `agent-team:feature-implementer` | opus-5 | $0.94 | 3m 40s | 94% |
| `agent-team:system-design-expert` | opus-5 | $0.93 | 2m 17s | 89% |
| `agent-team:security-reviewer` | opus-5 | $0.73 | 1m 53s | 90% |
| `agent-team:feature-implementer` | opus-5 | $0.51 | 1m 34s | 91% |
| `agent-team:test-reviewer` | sonnet-5 | $0.43 | 2m 13s | 90% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.42 | 1m 25s | 94% |
| `agent-team:test-reviewer` | sonnet-5 | $0.24 | 1m 5s | 85% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.24 | 1m 4s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.19 | 45s | 87% |

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

- plugin `agent-team-spring-boot` at `v0.3.3` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `064d588523591361` · `2.1.233 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
