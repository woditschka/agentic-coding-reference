# specialty-directory r3 — v0.3.1

Specialty directory page (feature) · started 2026-08-15T03:29:29+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±1) | 4 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.95. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> Placement is idiomatic:  SpecialtyController  is package-private, takes both repositories by constructor, and holds no rule — the grouping/ordering lives in  SpecialtyDirectory.of , an immutable record unit-testable without the framework, which moves the pyramid the right way.  SpecialtyRepository  follows the existing repository pattern; naming avoids prohibited suffixes. Risk:  specialtyList.html  introduces  #{specialties} / #{vets} / #{name}  with no bundle entries in the patch, which REQ-LANG-002's key-comparison test would catch; the  holder.firstName + ' ' + holder.lastName + ' '  trailing-space separator is crude. Tests are behavior-named, four-phase, hand-written doubles over mock frameworks, factories used; but the controller test shares mutable repository beans ( emptyTheClinic ), asserts raw HTML containment including  not(containsString("?page=")) , leaves literals like "Helen"/"radiology" unnamed, and never covers an empty clinic. PRD and system-design contracts, package line, and invariants are all updated.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController is package-private, takes both repositories by constructor, and delegates all grouping/ordering to SpecialtyDirectory, so no new rule lands in the web layer; SpecialtyRepository mirrors VetRepository's Spring Data shape and the record is immutable with defensive List.copyOf. Tests are BDD-named (theSpecialtyDirectoryShouldOrderHoldersByLastNameThenFirstName), four-phase, factory-constructed, and use hand-written InMemorySpecialties/InMemoryVets instead of a mock framework. Deductions: the createSpecialty/createVeterinarian factories are duplicated verbatim across both test classes rather than extracted into shared vocabulary; InMemory beans are shared mutable fixtures cleared in emptyTheClinic; not(containsString("?page=")) is a hollow proxy for no-pagination; the template's holder.lastName + ' ' trailing-space concatenation is a rendering hack. PRD and system-design contracts, package structure, and invariants all move with the change.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController is a thin adapter (two repository reads, delegate, view name), keeping ordering and grouping in the immutable SpecialtyDirectory record, so no new rule lands in a controller and the logic is unit-testable without the framework; SpecialtyRepository follows the Repository/naming rules, though Specialty is not an aggregate root and SpecialtyDirectory matches no catalog pattern exactly without an ADR. Tests are BDD-named, four-phase, factory-built, and use hand-written InMemorySpecialties/InMemoryVets rather than a mock framework; deductions for the shared mutable repository beans reset by emptyTheClinic(), the near-duplicate ShouldShowEverySpecialtyOnOnePage test, and the brittle not(containsString("?page=")). specialtyList.html introduces #{specialties}/#{name}/#{vets} with no bundle change visible, a REQ-LANG-002 risk; docs are updated thoroughly.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $9.17 | 31m | 29 | 94% | 8 file(s) +545/−6 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.91 | 2m 46s | 88% |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPECIALTYDIRECTORY-001 — Specialty directory

1 review round · 1 build-pass · **1 build-failure** · grade **CONCERN**

| reviewer | R1 |
| --- | --- |
| **code-quality** | **✔** |
| **test** | **✔** |
| **security** | **✔** |
| **doc** | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Specialty directory · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **minor** · (design) · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 10m***
  - ▲ **build ✗ build failed** · retry 1
  - ▲ **build ✓ clean** · build · test · checkFormat · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 34s***
- ✔ **review doc** · **approved** · ***◷ 59s***
- ✔ **review security** · **approved** · ***◷ 1m***
  - ▹ rec: No NVD verification ran in this review: the OWASP dependency-check plugin is not configured in build.gradle and the reviewer has no network access. Treat the dependency posture as not verified rather than clean. The change set adds no artifact (build.gradle unchanged, Spring Boot pinned at 4.1.0 via the plugin), so the supply-chain delta for this slice is zero; closing the standing NVD check belongs to CI or a human.
  - ▹ rec: Response size on /specialties.html grows with the whole specialty x vet_specialties join, unpaged by requirement, while the neighbouring /vets.html pages at 5. This is not attacker-controllable in this application — no route writes vets or specialties, so the row count is fixed by the seed data — which is why it is a note rather than a finding. Should a specialty or veterinarian write path ever land, this page becomes the amplification target and should be revisited.
  - ▹ rec: SpecialtyController issues the specialty read and the veterinarian read as two separate transactions (the @Transactional(readOnly = true) sits on each repository method), so a concurrent write could produce a page assembled from two snapshots. Harmless for a read-only demonstration with no writer; worth knowing if the directory ever assembles under concurrent writes.
- ✔ **review test** · **approved** · ***◷ 1m***
  - ▹ rec: SpecialtyDirectory.BY_HOLDER_NAME breaks ties on identical (lastName, firstName) pairs by Vet::getId (SpecialtyDirectory.java:42), but no test in SpecialtyDirectoryTests exercises two holders sharing both first and last name. This is real, non-trivial branch logic backing the PRD's 'stable order' edge case (edge case 2) and is currently untested. Add a case with two same-named holders (different ids) asserting the id-ascending tie-break, e.g. extend theSpecialtyDirectoryShouldOrderHoldersByLastNameThenFirstName or add a dedicated test.
- ◆ **grade CONCERN** · add read-only specialty directory page
  - blast_radius — **clear** — Eight files in one module, six of them new and none deleted: the change adds a route, a lookup repository, a projection, a template and two test classes, editing no existing production file. It reads the shared cached veterinarian collection but only streams and sorts it into fresh lists, so the cached state it borrows is never mutated. No sensitive paths.
  - semantic_surprise — **clear** — Reading every hunk, the code does what the PRD entry describes. Holders are matched to specialties by Specialty id rather than instance identity, which is the right call given the specialty read and the veterinarian read come from separate repository calls; getOrDefault yields an empty holder list for an unheld specialty, matching edge case 1. Ordering is decided in Java by two named comparators rather than by database collation. The template concatenates each holder as first name, last name and a trailing space with no delimiter between holders, which is the same rendering convention vetList.html already uses for its specialty column.
  - test_adequacy — **clear** — The tests assert real outcomes and would fail against a broken implementation. Unit tests pin grouping, the unheld specialty, both ordering rules and the defensive copy; controller tests drive real Thymeleaf rendering through MockMvc with hand-written in-memory repository doubles and cover all four Done-when criteria plus the unheld-specialty edge case. The one untested comparator branch, the id tie-break, fires only between veterinarians sharing both names, whose rendered output is identical either way.
  - reviewer_hedging — **concern** — All four reviewers the full-battery plan dispatched approved with zero findings, but two attached recommendations. The security reviewer states the dependency posture is not verified rather than clean, since no NVD check could run, and flags that the unpaged page grows with the whole specialty-to-veterinarian join and that the two repository reads sit in separate transactions. The test reviewer asks for a case covering the untested id tie-break.
  - scope_deviation — **clear** — Zero design revisions and zero consultations; the single build-retry record is a planned partial-artifact checkpoint that says so in its own text, not a gate failure. The changed paths match the design-block declared primary paths exactly, no navigation entry was added in line with the owner recorded decision, and the three new Open Questions record the choices the request left open rather than deciding them.
  - why — An additive, read-only page contained in the vet package, with tests covering every stated criterion. The residual is reviewer notes rather than defects: the supply-chain check never ran, so treat the dependency posture as unverified, and the page is unpaged over the full join. Read those before merging.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyController matches the package's existing controller shape exactly (package-private class, public constructor injection, no @Autowired) — verified against VetController and OwnerController.
- SpecialtyRepository mirrors VetRepository's minimal Repository\<T,Integer> surface and PetTypeRepository's lookup-repository precedent, deliberately omitting @Cacheable per the design-block rationale.
- SpecialtyDirectory and SpecialtyEntry are proper immutable value objects: compact constructors defensively copy with List.copyOf, static factory keeps construction always-valid, no mutable state.
- Grouping and ordering logic lives in SpecialtyDirectory rather than the controller, keeping the Web controller free of business rules per architecture-principles.md.
- Named comparators (BY_STORED_NAME, BY_HOLDER_NAME) make the ordering rule self-documenting and independently unit-tested rather than relying on database collation.
- Template uses th:text exclusively (never th:utext) for stored names, consistent with vetList.html's escaping discipline, and reuses existing message keys with no new bundle edits needed.
- checkFormat passes clean.

**doc-reviewer**

- docs/prd.md's new Specialty directory section is narrative prose at the right altitude: no mechanism, no code-element names, no rationale prose; the ADR/Design link pattern is used correctly with no inline rationale after it
- Every REQ-SPECIALTYDIRECTORY-001 Done-when bullet is present and the two Edge cases are recorded distinctly from the Done-when contract
- All sentences in the new PRD paragraph are under 30 words
- The three new Open Questions entries follow the existing format and correctly reflect the intake-decision's recorded scope (no entry point, unheld-specialty narrowest reading, stable-order-only)
- docs/system-design.md additions (SpecialtyController, SpecialtyRepository, SpecialtyDirectory rows and the Invariants sentence) stay at purpose-plus-source-pointer altitude with no field/parameter tables or literal constants
- Cross-references resolve: docs/prd.md#req-specialtydirectory-001 anchor exists, system-design.md#contracts anchor exists, both Design links target it correctly
- Terminology (Specialty, Veterinarian, Vet short form) matches docs/ubiquitous-language.md; no new undefined domain terms introduced
- No Non-Goals table row was touched, consistent with the prd-entry's declared absence of scope_overrides
- The template's menu argument ('specialties') matches no existing nav item in fragments/layout.html, consistent with the PRD's no-entry-point requirement and the system-design notes

**security-reviewer**

- XSS: every DB-derived value in src/main/resources/templates/vets/specialtyList.html renders through th:text, so Thymeleaf's default escaping stays on. No th:utext anywhere in templates/ (swept with grep -F), and the new template introduces no __${...}__ preprocessing — the pre-existing preprocessing sites (layout.html, inputField.html, selectField.html, vetList.html) all take fragment-local literals or numeric page values, never request text. The concatenation inside th:text="${holder.firstName + ' ' + holder.lastName + ' '}" is an expression-level join whose result is still escaped on output.
- Data access: SpecialtyRepository.findAll() is a Spring Data derived query with no string-built query text and no request-derived parameter. Injection-into-data-access row of docs/security-principles.md passes.
- Least privilege at the repository: SpecialtyRepository extends the bare Repository marker and declares only findAll() with @Transactional(readOnly = true) — no write or delete method is exposed to reach a specialty row.
- Mass assignment: SpecialtyController.showSpecialtyDirectory binds nothing from the request (Model only), so no identifier-binding surface exists and no @InitBinder disallow list is required. No @RequestParam, no @PathVariable, no command object.
- Exposed-surface widening: the one new route GET /specialties.html is a read-only HTML page over specialty names and veterinarian full names — data already public through the existing /vets.html page and /vets representation. It mutates no state, touches no management endpoint, and leaves the baseline in docs/system-design.md § Security Context unchanged. PRD and system-design both state what it exposes, per the security-principles requirement that a new endpoint say so.
- Path/resource resolution: the view name "vets/specialtyList" is a compile-time constant; no request-derived value composes a path or resource name.
- Secrets and logging: the change adds no logging, no exception message, no credential, and no System.out/System.err. Nothing new can reach the error page, which renders exception messages.
- Deserialization: no Jackson polymorphic typing, no @JsonTypeInfo, no XML parsing, no Java serialization introduced. SpecialtyDirectory and SpecialtyEntry are HTML-model-only types, not bound to any request or wire format.
- Shell and process execution: none — grep for Runtime/ProcessBuilder/exec( over the vet package is empty.
- Concurrency: the singleton SpecialtyController holds only final repository references; SpecialtyDirectory's two static Comparators are stateless, and both record components are defensively copied with List.copyOf. Reading the shared @Cacheable("vets") collection is non-mutating — sorted() and the grouping map build new structures rather than reordering the cached list in place.
- Supply chain: build.gradle is untouched by this change set — no new dependency, no repository change, no version move.

**test-reviewer**

- New tests (SpecialtyDirectoryTests, SpecialtyControllerTests) follow the BDD naming school (theSpecialtyDirectoryShould...) and four-phase structure with blank-line separation, no phase comments
- Controller test uses hand-written in-memory SpecialtyRepository/VetRepository doubles instead of Mockito, correctly applying the brief's 'hand-written double first' rule for new tests even though the sibling VetControllerTests uses @MockitoBean
- AssertJ used throughout with extracting/tuple/containsExactly/flatExtracting; no JUnit assertEquals/assertTrue; isUnmodifiable used to verify the record's defensive List.copyOf
- All four PRD acceptance criteria and both documented edge cases (unheld specialty listed with no holders; stable ordering) have dedicated tests at both the unit (SpecialtyDirectory) and controller (MockMvc) level
- Construction routed through local factory methods (createSpecialty/createVeterinarian, clinicKnows/clinicEmploys) per the three-tier data naming convention; no mystery literals
- New classes (SpecialtyController, SpecialtyDirectory) show 100% instruction coverage per jacocoTestReport; full ./gradlew test suite passes

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 1 | opus-5 | $3.23 | 11m 3s | 97% |
| `agent-team:system-design-expert` | 1 | opus-5 | $1.40 | 4m 8s | 92% |
| `(parent)` | 1 | opus-5 | $1.27 | 33m 28s | 96% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.00 | 2m 42s | 92% |
| `agent-team:change-grader` | 1 | opus-5 | $0.91 | 2m 46s | 88% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.76 | 1m 51s | 89% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.49 | 2m 11s | 95% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.30 | 1m 12s | 94% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.22 | 46s | 87% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $3.23 | 11m 3s | 97% |
| `agent-team:system-design-expert` | opus-5 | $1.40 | 4m 8s | 92% |
| `(parent)` | opus-5 | $1.27 | 33m 28s | 96% |
| `agent-team:product-requirements-expert` | opus-5 | $1.00 | 2m 42s | 92% |
| `agent-team:change-grader` | opus-5 | $0.91 | 2m 46s | 88% |
| `agent-team:security-reviewer` | opus-5 | $0.76 | 1m 51s | 89% |
| `agent-team:test-reviewer` | sonnet-5 | $0.49 | 2m 11s | 95% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.30 | 1m 12s | 94% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.22 | 46s | 87% |

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

- plugin `agent-team-spring-boot` at `v0.3.1` (tag)
- model requested `claude-opus-5`; models used: opus-5 · sonnet-5
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.232 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
