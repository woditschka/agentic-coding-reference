# specialty-directory r2 — v0.4.3

Specialty directory page (feature) · started 2026-09-18T01:09:23+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.51. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The grouping rule sits in an immutable  SpecialtyDirectory  record with defensive  List.copyOf  calls.  SpecialtyController  stays thin, and  SpecialtyRepository  follows the existing repository pattern. One piece of duplication costs design and maintainability: the  ORDER BY specialty.name  query and the in-memory  SPECIALTY_ORDER  sort both order specialties. The unit tests use BDD names, factories, hand-written doubles (the lambda repository and  FixedVetRepository ) and whole-object  containsExactly  comparisons. The controller tests check rendered text with  containsString , and  ">" + heldByNone + "\<"  depends on the markup. The identity-matching comment explains a non-obvious choice.  prd.md  and the  system-design.md  contracts table are both updated, and the two open questions are recorded.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The grouping rule sits in the immutable  SpecialtyDirectory  record rather than the controller.  SpecialtyController.showSpecialtyDirectory  only delegates, which matches the Web controller row. Ordering is defined twice, once in  findSpecialties  ( ORDER BY specialty.name ) and again in  SPECIALTY_ORDER , which is minor duplication.  SpecialtyDirectoryTests  has behavior-named, phase-separated unit tests with factories and whole-object  containsExactly  comparisons. It covers the unheld, multi-holder, ordering and separate-instance cases. The web tests use hand-written doubles ( FixedVetRepository , a lambda repository), but the  ">" + heldByNone + "\<"  markup match is brittle. The comment on  holds  explains a non-obvious identity match. The PRD requirement text, open questions and system-design contract rows all move with the change, and no stale claim remains.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> The design fits well. SpecialtyController only binds, delegates to SpecialtyDirectory.of and picks the view, so the grouping rule lives in an immutable record that can be unit-tested. SpecialtyRepository follows the VetRepository style. One redundancy: the query already orders by name ( ORDER BY specialty.name ), and SPECIALTY_ORDER sorts again. SpecialtyDirectoryTests are BDD-named and use factories with derived expectations and whole-object containsExactly. The controller test uses hand-written doubles (a lambda repository and FixedVetRepository) instead of a mock framework. Weak spots: the  ">" + heldByNone + "\<"  markup check is fragile, and the 'OnOnePage' test never checks pagination. The identity-match comment explains a real problem. The PRD, the edge cases, the open questions and the system-design contract rows were all updated together.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $7.31 | 15m | 4 | 92% | 8 file(s) +529/−6 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.57 | 43s | 83% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-003 — Staff can see which veterinarians hold each specialty

2 review rounds · 2 build-passes · grade **SKIM**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (2) | **✔** |
| **test** | **✔** | · |
| **security** | **✔** | **✔** |
| **doc** | **✔** | · |

- ◇ **intake** Feature request: the vet list answers "which specialties does this vet hold", but staff also ask the inverse — "which vets hold this specialty". Two product decisions come with it, made here as the product owner: - A read-only specialty view of the existing directory is in scope; managing   veterinarians or specialties stays out of scope as before (non-goal NG-2   is unchanged). - The page is reachable by its URL alone: no navigation entry and no link   from another page is part of this request. A visible entry point may come   as a follow-up request. Add a specialty directory page: - GET /specialties.html lists every specialty the clinic knows by its stored   name, each with the veterinarians holding it. - Each veterinarian is shown by full name: first name, then last name (for   example "Helen Leary"). - A veterinarian holding no specialty appears under no specialty; the page   lists specialties, not the full vet roster. - All specialties render on one page — no pagination. Cover the new behavior with tests. These are all the product decisions; no further product answer will come during the work. Where a choice still seems open, take the narrowest reading consistent with this request and record the open question rather than waiting. · (2 decisions) · (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 52s***
- ◈ **design-block** **minor** · (design) · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 7m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 24s***
- ✔ **review doc** · **approved** · ***◷ 59s***
- ✔ **review test** · **approved** · ***◷ 1m***
- ✎ **review code-quality** · **changes_requested** · (2 findings) · ***◷ 1m***
  - [autofix] `SpecialtyController.java:29-41` Fields `specialties` and `vets` hold a `SpecialtyRepository` and a `VetRepository`, not a collection of specialties or veterinarians. The call site `this.specialties.findSpecialties()` (line 41) reads as invoking a lookup method on a collection named `specialties`, which is misleading to a future reader. `VetController` (the neighboring, unmodified controller in the same package) names its field `vetRepository` for exactly this reason.
    - fix: Rename the fields to `specialtyRepository` and `vetRepository`, matching `VetController`'s convention.
  - [autofix] `SpecialtyDirectory.java:68` The nested record is named `Entry`, a generic placeholder name. `docs/architecture-principles.md` § Naming states the rule this violates directly: "Names come from the project's canonical vocabulary... if the PRD calls it a 'feed item', the code says FeedItem, never Entry or Record." `docs/ubiquitous-language.md` has no term for this specialty-with-holders pairing, so a domain-grounded name (e.g. `SpecialtyHolders`, or inlining the pair as two directory-level accessors) should replace the generic one.
    - fix: Rename `Entry` to a name grounded in the domain vocabulary, e.g. `SpecialtyHolders`, updating the two use sites in `SpecialtyDirectory.of` and the template model access (`entry.specialty`, `entry.holders` in specialtyList.html) accordingly.
- ↻ **implement** (implementer · routine) ← code-quality · (2 findings) · ***◷ 58s***
  - ▲ **build ✓ clean** · format · build · test · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 12s***
- ✔ **review code-quality** · **approved** · ***◷ 21s***
- ◆ **grade SKIM** · add read-only specialty directory page
  - blast_radius — **skim** — Every code file is new and sits in the vet package: a controller, a value record, a repository, and a template. No existing production file is modified, no sensitive path is touched, and the only doc edits are additive PRD and Contracts rows. The new security-surface route is one parameterless GET.
  - semantic_surprise — **skim** — Reading the hunks, the code does what its size suggests. Holders are matched by specialty id, which is needed because the cached vets and separately loaded specialties are distinct instances with no value equality; the comment explains this and a unit test pins it. The comparators are name then id, and last name then first name then id. The JPQL takes no parameters, the template escapes with th:text, and every message key it uses exists in all bundles. Passing menu key 'vets' to the layout highlights the Veterinarians nav entry without adding a link, as designed.
  - test_adequacy — **skim** — The SpecialtyDirectoryTests assertions check real outcomes with exact containsExactly: vets holding nothing are omitted, a multi-holder vet is listed under each specialty, an unheld specialty keeps empty holders, both orderings, separate-instance id matching, and immutability. The MockMvc tests use hand-written doubles and check each Done-when bullet end to end. Two assertions are loose: '>none\<' is not tied to the unheld row, and the no-link check matches only the literal '/specialties.html'. The unit layer covers the rule, so these gaps are minor.
  - reviewer_hedging — **skim** — All four roster reviewers approved round 1 except code-quality, which asked for two renames. The fix delta was rename-only, and both dispatched round-2 reviewers approved it cleanly with no recommendations. The citations are backed by greps and file:line references. The one I checked, VetRepository.java:46 findAll, resolves. The missing OWASP plugin is a standing project gap, not a hedge.
  - scope_deviation — **skim** — The change matches the intake exactly: GET /specialties.html, full names, no pagination, holderless vets omitted, and no navigation link. Open choices, entry point and ordering, are recorded as PRD open questions rather than decided. There were zero consultations, design revisions, and build retries, and the fix round changed no behavior.
  - why — A contained, additive read-only page in one package with no modified existing code. The diff shows no behavioral surprise, and the id-based matching is deliberate and tested. The tests assert real outcomes, the fix round only renamed things, and approvals are clean. A glance at SpecialtyDirectory.java and the template confirms it.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Injection into data access: SpecialtyRepository.java uses a fixed JPQL literal with no parameters ( @Query("SELECT specialty FROM Specialty specialty ORDER BY specialty.name") ) and SpecialtyController.java binds no request input (its only handler is  String showSpecialtyDirectory(Model model) ), so no request-derived value reaches a query.
- Cross-site scripting: specialtyList.html renders every stored value through escaping  th:text  ( th:text="${entry.specialty.name}" ,  th:text="${holder.firstName + ' ' + holder.lastName}" ).  grep -F -e utext  on the template returned no match, and the template has no  __${...}__  preprocessing, inline script, or remote resource.
- Mass assignment: the new handler has no  @ModelAttribute  or  @RequestBody  target, so it adds no binding surface and needs no  @InitBinder  disallow list.
- Widening the exposed surface: the new route is a single GET ( @GetMapping("/specialties.html") ) that is read-only ( @Transactional(readOnly = true)  on findSpecialties). It exposes only veterinarian and specialty names that /vets.html already publishes, and it mutates nothing. docs/prd.md REQ-VET-003 and the system-design Contracts row state what it exposes. It stays within the open-route demonstration baseline recorded in docs/security-principles.md.
- Resource bounds: the page loads every specialty (a small lookup table) and every vet through the existing cached  Collection\<Vet> findAll()  (VetRepository.java:46), the same unpaged read the existing VetController.java:70 performs. The page adds no new unbounded surface beyond the single page PRD REQ-VET-003 requires.
- Concurrency and immutability: SpecialtyController holds only final injected repositories, and SpecialtyDirectory and Entry defensively copy their lists with List.copyOf, so the singleton bean holds no shared mutable state.
- Credentials: the diff adds no secrets. The added lines contain no token, password, secret, or key literals (read in the full changeset output).
- Supply chain: the diff changes no dependency.  ./gradlew dependencies  resolves Spring Boot 4.1.1 and tools.jackson.core:jackson-databind 3.1.5. No OWASP dependency-check plugin is configured in build.gradle ( grep -i 'dependencycheck owasp' build.gradle  returned nothing), so no NVD match ran in this review.

**doc-reviewer**

- docs/prd.md line 117-119: REQ-VET-003 reuses the REQ-VET prefix and takes 003 as the next number after withdrawn REQ-VET-002 (docs/prd.md:176), per prd-authoring numbering rule
- docs/prd.md new prose (lines 119-136) stays behavioral: grep -F -e 'SpecialtyDirectory' -- docs/prd.md and grep -F -e '.java' -- docs/prd.md both return no matches, so no class/file names leaked into the PRD
- docs/system-design.md:100-107: new Contracts rows (SpecialtyRepository, SpecialtyDirectory, SpecialtyController) are purpose-paragraph prose with a source-file pointer, no field/parameter tables or literal constants, consistent with the Abstraction Level checks
- docs/prd.md:140 and :76 both link system-design.md#contracts, which resolves to the existing '## Contracts' heading (docs/system-design.md:72) — same pattern already used by REQ-VET-001
- Domain terms Specialty and Veterinarian used in the new PRD/design prose are already defined in docs/ubiquitous-language.md:50,52
- docs/prd.md Open Questions (lines 191-192) record the two owner-deferred decisions (visible entry point, ordering) verbatim, consistent with the intake-decision at handoff line 1
- New sentences in docs/prd.md:121-127 are all under 20 words except one 19-word sentence, meeting the sentence-length standard

**test-reviewer**

- SpecialtyDirectoryTests.java exercises the domain rule (matching, ordering, immutability, cross-instance identity match) at the unit seam system-design.md:103 assigns it to, with zero mocking and real Specialty/Vet value objects (src/test/java/org/springframework/samples/petclinic/vet/SpecialtyDirectoryTests.java:29-100)
- SpecialtyControllerTests.java uses only hand-written test doubles (FixedVetRepository record, a lambda SpecialtyRepository) and MockMvc — no Mockito anywhere in either new test file (verified via read of both files), matching docs/testing-principles.md § Mocking Policy's real-implementation-first rule and CLAUDE.md's MockMvc-only-mock rule
- All 4 Done-when bullets and the 3 slice-relevant edge cases (3,4,5 of the Veterinarian directory section; edge case 1 belongs to REQ-VET-001 and 2 is a recorded known defect) of REQ-VET-003 map to a named test per  python3 scripts/grading.py coverage-map --feature REQ-VET-003 , 6 of 6 declared tests present
- ./gradlew test --tests "*Specialty*" passes; jacocoTestReport shows 100% line coverage on SpecialtyDirectory, SpecialtyDirectory.Entry, SpecialtyController, and Specialty (build/reports/jacoco/test/html/org.springframework.samples.petclinic.vet/index.html)
- Test data construction follows the brief's factory pattern: all  new Specialty() / new Vet()  calls are confined to the suites' own createASpecialty/createAVet factory methods (grep -n 'new [A-Z][A-Za-z]*(' on both test files), no raw production-constructor calls at test-body level
- Navigation-absence requirement (no link to /specialties.html from other pages) is verified via a real MockMvc GET against the WelcomeController and VetController views (SpecialtyControllerTests.java:105-110), not asserted by omission

**code-quality-reviewer**

- SpecialtyController is package-private, uses constructor injection, and holds no business rule, matching the Web controller row in docs/architecture-principles.md (grep -n "class SpecialtyController" confirms no conditional/validation logic beyond delegation)
- SpecialtyDirectory.of uses a static creator as its one public entry point beside the canonical (compact) constructor, per the Construction pattern row; List.copyOf defensive copies in both SpecialtyDirectory and nested Entry (lines 175-176, 205-207 of SpecialtyDirectory.java)
- The identity-matching comment on holds() (SpecialtyDirectory.java:189-191) explains why (separately-loaded entities, no value equality) rather than restating what, and matches the invariant recorded in docs/system-design.md's Invariants paragraph and confirmed absent any equals/hashCode override in Specialty.java or Vet.java (grep -n "equals\ hashCode" on both files: no output)
- Message bundle keys #{specialties}, #{name}, #{vets}, #{none} used in specialtyList.html are all pre-existing keys reused from messages.properties (grep -n confirms lines 21-24), not new hard-coded text
- No navigation link or entry point was added anywhere in the diff (grep -n "specialt" fragments/layout.html returns nothing), matching the PRD's REQ-VET-003 bullet that the page is reachable by address alone

**security-reviewer**

- Fix-delta scope (changeset --base-tree 2a6c05eb): the delta only renames things. It renames the controller fields specialties/vets to specialtyRepository/vetRepository, renames the record SpecialtyDirectory.Entry to SpecialtyHolders, and renames the template loop variable entry to specialtyHolders. The delta has no new input, sink, route, or dependency, and it removes or weakens no check.
- Cross-site scripting after the rename: specialtyList.html still renders every stored value through escaping th:text ( th:text="${specialtyHolders.specialty.name}" ,  th:text="${holder.firstName + ' ' + holder.lastName}" ).  grep -n -F -e utext -e '__$' -e '\<script'  on the template returned no match.
- Binding and injection surface unchanged: SpecialtyController.java still has one handler (line 38  @GetMapping("/specialties.html") ).  grep -F  for @ModelAttribute, @RequestBody, @RequestParam, and @PathVariable returned no match. SpecialtyRepository.java:36 still uses the fixed, parameterless  @Query("SELECT specialty FROM Specialty specialty ORDER BY specialty.name") .
- Immutability preserved: the renamed SpecialtyHolders compact constructor still defensively copies  holders = List.copyOf(holders); , and the controller fields stay final.
- Credentials and supply chain: the delta adds no secret literals and changes no dependency or build file. The round-1 dependency result stands: Spring Boot 4.1.1 and jackson-databind 3.1.5, with no OWASP dependency-check plugin configured, so no NVD match ran.

**code-quality-reviewer**

- Round-1 finding on SpecialtyController.java:29-41 (misleading  specialties / vets  field names) is fixed: fields renamed to  specialtyRepository  and  vetRepository , constructor parameters and call sites updated to match (SpecialtyController.java:29-41)
- Round-1 finding on SpecialtyDirectory.java:68 (generic  Entry  name) is fixed: the nested record is renamed  SpecialtyHolders , a domain-grounded name pairing Specialty with its Veterinarian holders; every use site is updated in the same commit — SpecialtyDirectory.java:30,46,68,70 (declaration,  of , compact constructor), specialtyList.html:17-21 ( specialtyHolders  loop variable replacing  entry ), and SpecialtyDirectoryTests.java (all  entryOf(...)  calls and the  entry ->  lambda renamed to  specialtyHoldersOf(...) / specialtyHolders -> ) — confirmed via full fix-delta diff (python3 scripts/changeset.py --base-tree 2a6c05e) showing no remaining  Entry  token in src/main or src/test for this package (grep -F -e "Entry" on the three changed non-doc files returns no matches)
- No new naming, placement, or vocabulary issues introduced by the fix; SpecialtyRepository.java (unchanged this round) was not re-reviewed per fix-delta scope

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $2.48 | 8m 51s | 94% |
| `(parent)` | 1 | opus-5 | $1.16 | 15m 54s | 96% |
| `agent-team:security-reviewer` | 2 | opus-5 | $0.84 | 51s | 86% |
| `agent-team:system-design-expert` | 1 | opus-5 | $0.84 | 1m 32s | 88% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.67 | 2m 19s | 92% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $0.58 | 1m 7s | 79% |
| `agent-team:change-grader` | 1 | opus-5 | $0.57 | 43s | 83% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.42 | 1m 35s | 93% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.32 | 1m 6s | 93% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $2.08 | 7m 37s | 94% |
| `(parent)` | opus-5 | $1.16 | 15m 54s | 96% |
| `agent-team:system-design-expert` | opus-5 | $0.84 | 1m 32s | 88% |
| `agent-team:product-requirements-expert` | opus-5 | $0.58 | 1m 7s | 79% |
| `agent-team:change-grader` | opus-5 | $0.57 | 43s | 83% |
| `agent-team:security-reviewer` | opus-5 | $0.48 | 31s | 86% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.47 | 1m 46s | 93% |
| `agent-team:test-reviewer` | sonnet-5 | $0.42 | 1m 35s | 93% |
| `agent-team:feature-implementer-routine` | opus-5 | $0.40 | 1m 14s | 88% |
| `agent-team:security-reviewer` | opus-5 | $0.36 | 19s | 86% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.32 | 1m 6s | 93% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.20 | 33s | 89% |

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

- plugin `agent-team-spring-boot` at `v0.4.3` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `0aff9592719d` (branch `agent-team`)
- task fingerprint `dfad163fa162236e` · `2.1.274 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
