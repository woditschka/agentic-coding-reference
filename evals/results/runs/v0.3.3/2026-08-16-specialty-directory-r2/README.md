# specialty-directory r2 — v0.3.3

Specialty directory page (feature) · started 2026-08-15T23:05:23+00:00 · exec `claude-dev` · status **complete**

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
| review attention (pipeline grade) | concern |

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
| 4 (±0) | 4 (±0) | 4 (±1) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.97. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyDirectory.java keeps the join and ordering out of SpecialtyController.java, which stays bind-delegate-select, and the ADR records why the inverse JPA mapping was rejected; the record is immutable with List.copyOf in both compact constructors. Two gaps: specialtyList.html introduces #{specialties}, #{name}, #{vets}, #{none} with no messages properties in the patch, so headers likely render ??name_en??, and SpecialtyControllerTests only asserts data strings ("dentistry", "Helen Leary"), never the labels; SpecialtyRepository's ORDER BY specialty.name duplicates the read model's own sort. templatesLinkingTo walks src/main/resources/templates from the CWD inside a @WebMvcTest class — fragile and misplaced. SpecialtyDirectoryTests otherwise reads as specification: behavior names, factories, whole-entry comparison. PRD, system-design, and ADR index all move.

**Sample 2** — design-fit 4 · test-quality 4 · maintainability 3 · doc-fit 5

> SpecialtyController stays a thin adapter (showSpecialtyDirectory delegates to SpecialtyDirectory.of), the join and ordering live in an immutable record with defensive List.copyOf, and dependencies are constructor-injected — good layering. Minor tension: the ADR rejects option 1 partly because it 'turns a lookup value into a second aggregate root', yet SpecialtyRepository does the same, where the read could have joined VetRepository (cf. findPetTypes precedent). specialtyList.html introduces #{specialties}, #{name}, #{vets}, #{none} but no messages bundle changes accompany them, so the page renders ??specialty_en?? placeholders and the tests (containsString("dentistry")) can't catch it. Unit tests read as specifications with factories and behavior names; the factories are duplicated across both test classes, and theSpecialtyDirectoryShouldNotBeLinkedFromAnyPage greps template files rather than exercising behavior. Docs are thorough and current.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Placement is right: SpecialtyDirectory holds the join/order rule as an immutable record, SpecialtyController only binds and delegates (showSpecialtyDirectory), and SpecialtyRepository follows the naming rule — no new rule in a controller. The gap is i18n: specialtyList.html references #{specialties}, #{name}, #{vets}, #{none} and the layout key 'specialtyDirectory', yet no messages_*.properties hunk defines them, so the page renders ??specialties?? — and the controller test only asserts on 'dentistry'/'Helen Leary', so it passes anyway. Unit tests are exemplary: behavior names, factory methods, NO_VETERINARIANS, whole-entry comparison via anEntryFor, separate-read join case. Weaker: theSpecialtyDirectoryShouldNotBeLinkedFromAnyPage walks the filesystem inside a @WebMvcTest slice, and attributeDoesNotExist("totalPages") asserts another page's detail. Docs (ADR, README index, prd, system-design) are fully current.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.27 | 27m | 26 | 94% | 10 file(s) +562/−2 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.64 | 1m 48s | 82% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPECIALTYDIRECTORY-001 — Staff can see which veterinarians hold each specialty

1 review round · 1 build-pass · **1 build-failure** · grade **CONCERN**

| reviewer | R1 |
| --- | --- |
| **code-quality** | **✔** |
| **test** | **✔** |
| **security** | **✔** |
| **doc** | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Staff can see which veterinarians hold each specialty · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 9m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · checkFormat · checkstyleMain · validate · audit-autofix · contracts-sync
- ✔ **review test** · **approved** · ***◷ 47s***
- ✔ **review code-quality** · **approved** · ***◷ 54s***
  - ▹ rec: src/main/resources/templates/vets/specialtyList.html:20 - veterinarian names within a specialty are joined by an inline space per th:each iteration (veterinarianName + ' ') rather than a proper separator such as comma-space, leaving a stray trailing space after the last name. Cosmetic only; does not block merge.
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: Supply chain: no dependency was added or changed by this diff, so it widens no supply-chain surface. Recorded for completeness - the OWASP dependency-check plugin is not configured in build.gradle, so no NVD match ran in this review. Resolved versions read from ./gradlew dependencies: Spring Boot 4.1.0, spring-webmvc 7.0.8, tools.jackson.core:jackson-databind 3.1.4, thymeleaf-spring6 3.1.5.RELEASE, h2 2.4.240. These are not verified against the NVD here - a human or CI should close that check.
  - ▹ rec: Not a finding against the recorded baseline, noted for future load characteristics only: the page reads all specialties uncached and all veterinarians per request with no paging, which the ADR records as deliberate. The specialty and veterinarian tables are clinic-managed rather than caller-grown, and /vets.html's serialized route already performs the same unpaged findAll(), so the change adds no new unbounded-allocation vector.
- ◆ **grade CONCERN** · add the specialty directory read model and page
  - blast_radius — **clear** — Purely additive within the vet package: three new production types, one new template, and doc updates. No existing production file is edited, no route or serialized representation changes, no sensitive path is touched, and the only shared resource reused is the existing vets cache.
  - semantic_surprise — **clear** — Read every hunk: the join keys on Specialty.getId() through a HashMap rather than object equality (correct given BaseEntity overrides neither equals nor hashCode), ordering is specialty name then holder last-name-then-first, veterinarians holding nothing never enter the index, and the template is a line-for-line mirror of the existing vetList.html. Nothing behaves differently from what the diff reads as.
  - test_adequacy — **clear** — The unit tests assert real outcomes, not the implementation: aSeparatelyLoadedCopyOf would fail an equality-based join, the stable-order test compares two independently-ordered assemblies, and the held-by-none and holds-nothing cases are both covered. The controller test renders the real template through MockMvc and asserts the rendered names, so the view is exercised rather than assumed.
  - reviewer_hedging — **concern** — All four reviewers approved with empty findings, but two parked residuals in recommendations: veterinarian names in a cell are joined by a bare trailing space, so two holders render as the ambiguous run 'Helen Leary Linda Douglas'; and the security reviewer recorded that no NVD or dependency-check scan ran in this project and asked a human or CI to close it.
  - scope_deviation — **clear** — Zero build retries and zero consultations; the one design revision was a record correction adding docs/adr/README.md to supporting_paths, not a change of design. The diff matches the requirement's stated surface exactly: one new GET page, no navigation entry, and a test that asserts no template links to it.
  - why — Contained, additive, and genuinely tested; the semantic read found no surprise. Before merging, decide on the one real residual the reviewer declined to block on: multiple veterinarians in a cell are space-joined, so names run together. Cosmetic, one template line.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**test-reviewer**

- SpecialtyDirectoryTests exercises every PRD acceptance criterion with real objects and no framework context: every-specialty-by-name, first+last name display, a specialty held by no veterinarian, a veterinarian holding no specialty omitted, and stable ordering via an equality check across two independently-ordered inputs
- theSpecialtyDirectoryShouldGroupHoldersWhenTheSpecialtyCameFromASeparateRead directly tests the design's flagged risk (BaseEntity has no equals/hashCode, so the join must be by stored id, not object identity) with a purpose-built aSeparatelyLoadedCopyOf helper
- Test data uses the PRD's own example (Helen Leary) and named factory methods (createASpecialty, createAVeterinarian) instead of raw constructors or mystery literals, per the three-tier naming convention
- SpecialtyControllerTests follows the existing VetControllerTests precedent for @WebMvcTest + @MockitoBean on repositories, consistent with the brief's mocking policy (MockMvc is the sanctioned boundary mock; repository stubs are tolerated existing-pattern, not a new deviation)
- theSpecialtyDirectoryShouldNotBeLinkedFromAnyPage and theSpecialtyDirectoryShouldCarryTheNavigationEveryPageCarries give durable, executable coverage of the two PRD decisions (URL-only reachability, but full inherited nav) that are easy to silently regress
- No new message keys were introduced (the template reuses specialties/name/vets/none), so REQ-LANG-002 stays covered by the existing I18nPropertiesSyncTest without needing a new test
- All method names follow the the{Subject}Should{Outcome} BDD school, four-phase structure is clean with blank-line separation and no phase comments, and assertions are fluent AssertJ throughout (extracting, flatExtracting, containsExactly)
- ./gradlew test passes for both new test classes

**code-quality-reviewer**

- SpecialtyDirectory is a clean, well-documented immutable value object: defensive List.copyOf on both records, Objects.requireNonNull guards on the factory's collection parameters, and a Javadoc-explained join-by-identifier that correctly sidesteps BaseEntity's missing equals/hashCode
- SpecialtyRepository mirrors the cited PetTypeRepository pattern (Repository interface, @Query with ORDER BY, single-purpose findSpecialties()), verified by direct comparison of both files
- SpecialtyController stays a thin, package-private @Controller matching VetController's shape, with no business logic leaking into the web layer
- Naming throughout is descriptive and free of get/set-prefixed record accessors, type-name repetition, or abbreviations (indexHoldersBySpecialtyId, displayNamesOf, holdersBySpecialtyId)
- Message keys (specialties, name, vets, none) are reused from the existing bundle rather than adding new i18n surface, confirmed present in messages.properties
- checkFormat passes clean; no formatting issues found

**doc-reviewer**

- PRD entry for REQ-SPECIALTYDIRECTORY-001 stays behavioral: no mechanism, code names, or constants leak in; the 'Done when' bullets and edge cases match the intake-decision's owner scope (read-only, no nav entry) verbatim
- Anchor req-specialtydirectory-001 present at first mention in the correct lowercase-hyphenated form; ADR link and system-design.md#contracts link both resolve
- ADR 2026-08-15-specialty-directory-read-model.md follows the template: Status, Context, Options Considered, Decision, Consequences, Implementation with Requirements: REQ-SPECIALTYDIRECTORY-001, and a References section using em-dashes; docs/adr/README.md index row added for it
- system-design.md additions (package-structure line, invariants paragraph, three new Contracts rows for SpecialtyRepository/SpecialtyDirectory/SpecialtyController) sit at the right abstraction level: purpose prose plus source pointers, no field or parameter tables, no literal constants
- Cross-document coherence holds: the join-on-identifier, ordering (specialty by name, veterinarian by last-then-first), and no-navigation-entry decisions are stated once at design altitude and consistently reflected in the delivered SpecialtyDirectory/SpecialtyController/template, with no restatement or drift in the PRD
- Provenance marks preserved: the derived-PRD and derived-system-design headers each gained a clause noting this capability is owner-stated/designed rather than derived, consistent with document-writing's provenance-mark rule

**security-reviewer**

- Data access: SpecialtyRepository.findSpecialties() is a static JPQL string with no request-derived value concatenated in; the only other read is the derived VetRepository.findAll(). No injection-into-data-access surface.
- XSS: specialtyList.html renders every dynamic value through th:text (default escaping on). Swept the new template for th:utext and Thymeleaf preprocessing (__${...}__) - neither is present, and the only preprocessing in the render path is the pre-existing literal menu link in fragments/layout.html, not a request-derived value.
- Exposed surface: /specialties.html is a new GET-only endpoint, documented in prd.md, system-design.md Contracts, and the ADR. It exposes specialty names and veterinarian display names, both already published by /vets.html - no new data class reaches an unauthenticated caller, and management exposure is untouched.
- Mass assignment / cross-request trust: the handler takes no request parameter, path variable, or bound command object, so there is no binder to constrain and no identifier carried across requests.
- Concurrency: SpecialtyController is a stateless singleton holding only repository references; SpecialtyDirectory and SpecialtyEntry are records whose compact constructors List.copyOf their collections, so the per-request read model is deeply immutable and safe to share with the view.
- Type safety and fail-secure joining: the join keys on the stored identifier via HashMap (null-key tolerant for a transient Specialty) rather than object equality, and Objects.requireNonNull guards the factory boundary with parameter-name-only messages that leak nothing into the exception-rendering error page.
- Resource management: the template-walk helper in SpecialtyControllerTests wraps Files.walk in try-with-resources; no production file, stream, or process handling is introduced.
- Pattern consistency: specialtyList.html mirrors the existing vetList.html escaping and #{none} fallback structure, and SpecialtyRepository mirrors VetRepository's @Transactional(readOnly = true) read-only shape - the same concern is secured the same way as its neighbour.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $4.25 | 13m 8s | 97% |
| `agent-team:system-design-expert` | 2 | opus-5 | $2.82 | 6m 41s | 94% |
| `(parent)` | 1 | opus-5 | $1.19 | 28m 6s | 95% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.04 | 2m 57s | 92% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.70 | 1m 25s | 88% |
| `agent-team:change-grader` | 1 | opus-5 | $0.64 | 1m 48s | 82% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.32 | 1m 19s | 92% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.29 | 1m 5s | 92% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.24 | 57s | 87% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.46 | 10m 52s | 97% |
| `agent-team:system-design-expert` | opus-5 | $2.02 | 4m 52s | 95% |
| `(parent)` | opus-5 | $1.19 | 28m 6s | 95% |
| `agent-team:product-requirements-expert` | opus-5 | $1.04 | 2m 57s | 92% |
| `agent-team:system-design-expert` | opus-5 | $0.79 | 1m 49s | 91% |
| `agent-team:feature-implementer` | opus-5 | $0.79 | 2m 15s | 94% |
| `agent-team:security-reviewer` | opus-5 | $0.70 | 1m 25s | 88% |
| `agent-team:change-grader` | opus-5 | $0.64 | 1m 48s | 82% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.32 | 1m 19s | 92% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.29 | 1m 5s | 92% |
| `agent-team:test-reviewer` | sonnet-5 | $0.24 | 57s | 87% |

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
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.233 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
