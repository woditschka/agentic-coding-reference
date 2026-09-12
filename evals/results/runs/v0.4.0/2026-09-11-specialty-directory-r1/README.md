# specialty-directory r1 — v0.4.0

Specialty directory page (feature) · started 2026-09-11T18:08:19+00:00 · exec `claude-dev` · status **complete**

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
| 5 (±0) | 4 (±0) | 4 (±0) | 4 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.57. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> The grouping and ordering logic lives in an immutable  SpecialtyDirectory  record ( of(...) ,  List.copyOf ), so  SpecialtyController.showSpecialtyDirectory  only binds and delegates. That fits the Web controller and Value object patterns, and  SpecialtyRepository  follows the  VetRepository  idiom. The tests follow the stated principles: BDD names, hand-written in-memory doubles instead of a mock framework, and plain unit tests for the directory logic. They fall short in three places.  aSpecialty  and  aVet  are copied between both test classes. The  InMemoryRepositories  doubles are mutable and shared across tests.  theSpecialtyDirectoryShouldOpenWhenNoSpecialtyIsRecorded  never checks that the list is empty.  renderedExactly  matches the text between  >  and  \< , so it depends on the exact HTML markup. Docs are kept current: PRD Context, REQ-VET-003 done-when items, edge cases, open questions, package tree, contracts table and invariants.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 4

> The design puts the grouping and ordering rule in the immutable SpecialtyDirectory record, with defensive copies and a pure static of(). SpecialtyController only binds and delegates, and SpecialtyRepository follows the existing Repository idiom, so the rule is unit-testable. The tests use the BDD the{Subject}Should{Outcome} names, separate phases with blank lines, use hand-written in-memory repository doubles instead of a mock framework, and build data through factories and named constants. The deductions: aSpecialty and aVet are duplicated across both test classes instead of shared. The controller test shares mutable doubles across tests, reset by replaceWith. The empty-page test checks only status and view. renderedExactly depends on the exact markup. The docs are thorough, but the PRD's 'ten further questions stay open' is stale now that three open questions were added.

**Sample 3** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 4

> The grouping rule sits in the immutable record  SpecialtyDirectory.of , which is unit-tested without the framework.  SpecialtyController  only delegates to it, and the new types follow the catalog's naming. The tests use BDD names and blank-line phases. They use hand-written in-memory repositories instead of mocks, factory methods, and named constants.  assertThat(reopened).isEqualTo(opened)  derives its expected value from the inputs. Two things detract. The  @TestConfiguration  doubles are shared mutable fixtures reset through  replaceWith .  renderedExactly  depends on the  >text\<  markup shape. The docs are thorough: the PRD requirement, edge cases and open questions, plus the package tree, invariants and contract rows in system-design. But three open questions were added while the PRD provenance line still says "ten further questions stay open", so that count is now stale.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $9.37 | 27m | 4 | 92% | 8 file(s) +578/−5 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.73 | 1m 56s | 86% |

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
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 3m***
- ◈ **design-block** **minor** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 14m***
  - ▲ **build ✗ build failed** · retry 1
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review doc** · **approved** · ***◷ 51s***
- ✔ **review security** · **approved** · ***◷ 59s***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 1m***
  - ▹ rec: src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java and specialtyList.html render specialty and vet names via th:text (auto-escaping), which is the correct control per security-principles, but no test in this slice exercises a specialty or holder name containing HTML-special characters to pin that escaping behavior down against regression. Non-blocking: the control is structural (th:text vs th:utext), not data-dependent, so no defect ships without it.
- ◆ **grade SCRUTINIZE** · add read-only specialty directory page
  - blast_radius — **skim** — Additive and contained: four new production files in the vet package plus the two doc edits, no existing production code modified. The one new surface is a GET route that binds no input. It reuses the existing cached VetRepository.findAll() without changing it, and the layout menu value matches no nav item, so no other page changes.
  - semantic_surprise — **skim** — Read SpecialtyDirectory.of end to end. Holders are grouped by specialty id rather than instance equality, which is correct because BaseEntity has no equals. Holderless specialties map to List.of(), vets with no specialty never enter the map, and both comparators are total (specialties by name then id, holders by last name, first name, then id). The template uses th:text only. One residual edge: the name columns are nullable in all three schemas and the comparators are not null-safe, so a null name row would 500 the page. Vet.getSpecialties() already has the same exposure, and the app has no write path.
  - test_adequacy — **skim** — The tests assert real outcomes. The stable-order test compares a build from reversed inputs against the original, using two same-named specialties with different holders, so dropping the id tie-break would fail it. The vet factory attaches id-only copies of specialties, so instance matching would fail. The controller tests match exact rendered element text in all ten locales. Gaps that do not block: the holder id tie-break is never exercised, the no-specialty-vet omission is tested only below the web layer, and HTML escaping is not pinned.
  - reviewer_hedging — **scrutinize** — All four reviewers in the full-battery roster approved with no findings. But the security approval cites SpecialtyController.java:145-146 and SpecialtyRepository.java:279-280, and those files are 46 and 38 lines long. The numbers are scripts/changeset.sh output offsets, not file lines. The quoted code is accurate, but the citations do not resolve to the files they name. The test-reviewer also left a recommendation that no test pins escaping. The missing OWASP scanner is a standing gap, context rather than a hedge.
  - scope_deviation — **skim** — The diff matches the design-block primary_paths exactly, and the page is address-only, as the owner deferred navigation. Design revisions 0, consultations 0. The single build retry was the implementer's planned partial checkpoint after cycle 2, not a gate failure.
  - why — The code stays contained, and the hunks read as specified: identity-keyed inversion, total ordering, escaped output. Scrutinize only because two line citations in the security approval point at changeset offsets rather than file lines. Before merging, read the 46-line controller and 27-line template yourself to confirm no input binding and th:text only.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**doc-reviewer**

- prd.md REQ-VET-003 prose (docs/prd.md:127) and Done-when/Edge-case bullets (docs/prd.md:132-135,140-143) use only behavioral language, no class/method/variable names, matching the PRD boundary rule
- docs/prd.md:125 anchor \<a id="req-vet-003">\</a> resolves; docs/prd.md:78,145 link system-design.md#contracts, which resolves to the '## Contracts' heading at docs/system-design.md:74
- system-design.md Contracts table rows for SpecialtyRepository/SpecialtyDirectory/SpecialtyController (docs/system-design.md:109-111) carry REQ-VET-003, and REQ-VET-003 is defined in docs/prd.md:125-127, satisfying the every-system-design-requirement-ID-exists-in-prd.md check
- grep -F -e 'REQ-VET-002' docs/system-design.md found no match, confirming the withdrawn requirement (docs/prd.md:181) is absent from system-design.md
- New table rows (docs/system-design.md:109-111) and the 'Specialty directory invariants' paragraph (docs/system-design.md:84) stay at purpose/invariant level with a source-file pointer, no struct-field or parameter tables, no constant literals
- REQ-VET-003 correctly continues the REQ-VET numbering after the withdrawn REQ-VET-002 (docs/prd.md:181) rather than reusing or skipping unnecessarily
- The two-requirement grouping under '### Veterinarian directory' (docs/prd.md:119-145) follows the same established pattern as the '### Language' section (REQ-LANG-001/002), so no structural deviation

**security-reviewer**

- No request input is bound. SpecialtyController.java:145-146 reads  @GetMapping("/specialties.html")  /  String showSpecialtyDirectory(Model model) . A grep for  @ModelAttribute @RequestBody @RequestParam @PathVariable  across vet/Specialty*.java found nothing (exit 1), so the mass-assignment, cross-request-state and path-traversal rows of docs/security-principles.md do not apply.
- Output escaping is preserved. specialtyList.html renders stored values only through  th:text  ( th:text="${entry.specialtyName()}" ,  th:text="${holder.firstName() + ' ' + holder.lastName()}" ). That matches vetList.html:18  th:text="${vet.firstName + ' ' + vet.lastName}" . A grep of templates/vets/ for  th:utext  and  __${  found no utext anywhere and no preprocessing in the new template; the only preprocessing hits are the pre-existing, server-computed page numbers in vetList.html:30-50.
- Data access is safe from injection. SpecialtyRepository.java:279-280 is a derived  @Transactional(readOnly = true) List\<Specialty> findAll()  with no query text. VetRepository.java:44-46  findAll()  is the existing cached read. Nothing in the change writes data, which is consistent with PRD NG-2.
- The exposed surface does not widen beyond the baseline. The new GET route publishes vet names and specialty names that /vets.html and the machine-readable vet route already expose. PRD REQ-VET-003 mandates the unpaged single-page view. Specialties and vets have no write path (NG-2), so an attacker cannot grow the list. It also adds no management endpoint.
- Rendered errors cannot leak sensitive data. SpecialtyDirectory only sorts and groups entity fields; it throws no custom exception message. Specialty.name carries  @NotBlank  (NamedEntity.java:34), so the name comparator gets no null from valid seed data.
- There are no shell, file, deserialization, logging or secret patterns in the new production code. A grep for  Runtime ProcessBuilder exec( JsonTypeInfo enableDefaultTyping Files. /tmp/ System.out log.  over vet/Specialty*.java found nothing. The diff adds no credentials, and build.gradle and application properties are not in scripts/changeset.sh --name-only.
- Supply chain: the change adds no dependency. build.gradle does not configure OWASP Dependency-Check (a grep for  dependencycheck / owasp  found nothing), so no NVD match ran in this review.  ./gradlew dependencies  resolves Spring Boot 4.1.1, spring-webmvc 7.0.9, Jackson (tools.jackson.core:jackson-databind) 3.1.5 and Thymeleaf 3.1.5.RELEASE.

**code-quality-reviewer**

- SpecialtyController (src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java:39-44) stays a thin delegator: fetches both collections, calls SpecialtyDirectory.of, adds one model attribute, returns the view name — no inversion/ordering/identity-matching logic lands in the controller, matching architecture-principles Pattern Catalog's Web controller row and the design-block's risk mitigation.
- SpecialtyDirectory (src/main/java/org/springframework/samples/petclinic/vet/SpecialtyDirectory.java) realizes the value-object rule: a single static factory entry point ( of ), compact constructors applying List.copyOf defensive copies on both SpecialtyDirectory and the nested Entry record, no setters, no mutable state.
- Identity matching (getId, not object/value equality) is used to group holders under specialties (SpecialtyDirectory.java:56,63), correctly avoiding the design-block's flagged pitfall of distinct Specialty instances between the two repositories.
- SpecialtyRepository (src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java) mirrors the VetRepository/PetTypeRepository precedent: narrow Repository\<Specialty, Integer> base, @Transactional(readOnly = true), Javadoc noting it is intentionally uncached and unordered.
- specialtyList.html uses th:text exclusively for stored specialty and vet names (verified by grep -F -e 'th:utext' -- src/main/resources/templates/vets/specialtyList.html returning no matches), avoiding unescaped HTML output per security-principles' Cross-site scripting row.
- The heading key #{specialties} is the pre-existing key (grep -F -e 'specialties=' -- src/main/resources/messages/messages.properties:23 'specialties=Specialties'), so no new message key was introduced and none of the 11 locale bundles needed a sync entry.
- New domain-facing names (Specialty, Vet, SpecialtyDirectory) align with docs/ubiquitous-language.md's Specialty and Veterinarian/Vet entries; no coined synonym introduced.
- Added Javadoc/comments (verified via python3 scripts/grading.py conventions-map) each explain a WHY not evident from the code — the fixed total order, the identity-matching rationale, the uncached/unordered contract — none restates the signature or is a candidate for a rename instead.

**test-reviewer**

- Test placement matches the design-block's assignment exactly (system-design.md Contracts / Specialty directory invariants, design-block line 5 integration_points): inversion, omission, holderless-specialty, and stable-order rules are unit-tested in SpecialtyDirectoryTests (pure SpecialtyDirectory.of(...), no Spring context); rendering, routing, i18n, and empty-state rules are tested at the web layer in SpecialtyControllerTests (@WebMvcTest) — verified by reading both files (src/test/java/org/springframework/samples/petclinic/vet/SpecialtyDirectoryTests.java, src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java) against docs/testing-principles.md § Test Pyramid.
- Mocking policy honored: SpecialtyControllerTests.java:169-202 hand-writes InMemorySpecialtyRepository/InMemoryVetRepository as @TestConfiguration beans (no Mockito/@MockitoBean introduced); MockMvc is the one sanctioned transport mock; SpecialtyDirectoryTests builds only real Specialty/Vet instances (testing-principles.md § Mocking Policy).
- The design-block's silent-defect risk (BaseEntity has no equals/hashCode, so specialties read from SpecialtyRepository are distinct instances from those on cached Vet objects) is directly covered: SpecialtyDirectoryTests.java:126-144 aVet(...) attaches a copy of each held Specialty sharing only the id, and a code comment (lines 131-132) states why — matching design-block risk 1's named mitigation.
- The stable-order risk (design-block risk 2) is tested by permutation: theSpecialtyDirectoryShouldListSpecialtiesAndHoldersInAStableOrder (SpecialtyDirectoryTests.java:97-111) builds the same directory from reversed specialty and vet lists and asserts isEqualTo, committing to stability without over-asserting an unspecified order — consistent with the PRD's stable-only commitment.
- python3 scripts/grading.py coverage-map confirms all 8 declared test_names from the prd-entry are present and all 4 Done-when bullets are covered by name; edge cases 1, 3, 4, 5, 6 of the Veterinarian directory group each map to a present test (edge case 2 is a recorded known-defect/non-goal, not a gap in this slice).
- AssertJ used fluently throughout (containsExactlyInAnyOrder, containsExactly, contains, isEqualTo); no JUnit assertEquals/assertTrue found by inspection. Four-phase structure (blank-line-separated Arrange/Act/Assert) held in every test read, with no phase comments or narration. Test names follow the the{Subject}Should{Outcome} school in both files.
- Construction goes through file-local factory methods (aSpecialty, aVet, entry, holder) per testing-principles.md § Test Data Construction; python3 scripts/grading.py conventions-map shows the only 'new Specialty()'/'new Vet()' raw constructions are inside those factory methods themselves, not scattered through test bodies.
- ./gradlew test passes (SpecialtyDirectoryTests and SpecialtyControllerTests all green, verified by direct run).

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $3.97 | 13m 58s | 93% |
| `agent-team:system-design-expert` | 1 | opus-5 | $1.35 | 4m 47s | 85% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.17 | 3m 37s | 89% |
| `(parent)` | 1 | opus-5 | $1.16 | 28m 56s | 95% |
| `agent-team:change-grader` | 1 | opus-5 | $0.73 | 1m 56s | 86% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.64 | 1m 8s | 90% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.43 | 2m 7s | 92% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.38 | 1m 32s | 94% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.28 | 1m 5s | 89% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $2.05 | 7m 5s | 94% |
| `agent-team:feature-implementer` | opus-5 | $1.91 | 6m 53s | 92% |
| `agent-team:system-design-expert` | opus-5 | $1.35 | 4m 47s | 85% |
| `agent-team:product-requirements-expert` | opus-5 | $1.17 | 3m 37s | 89% |
| `(parent)` | opus-5 | $1.16 | 28m 56s | 95% |
| `agent-team:change-grader` | opus-5 | $0.73 | 1m 56s | 86% |
| `agent-team:security-reviewer` | opus-5 | $0.64 | 1m 8s | 90% |
| `agent-team:test-reviewer` | sonnet-5 | $0.43 | 2m 7s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.38 | 1m 32s | 94% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.28 | 1m 5s | 89% |

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

- plugin `agent-team-spring-boot` at `v0.4.0` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `6cbb44ce4c9a` (branch `agent-team`)
- task fingerprint `dc643d9216b8dc0b` · `2.1.268 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
