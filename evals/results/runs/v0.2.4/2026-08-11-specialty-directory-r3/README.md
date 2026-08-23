# specialty-directory r3 — v0.2.4

Specialty directory page (feature) · started 2026-08-11T17:00:22+00:00 · exec `claude-dev` · status **complete**

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

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.70 | 36m | 23 | 95% | 18 file(s) +460/−8 |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-SPC-001 — Reader can see every specialty and the veterinarians holding it on one page

1 review round · 2 build-passes · no grade yet

| reviewer | R1 |
| --- | --- |
| **code-quality** | ✎ (3) |
| **test** | **✔** |
| **security** | **✔** (1) |
| **doc** | **✔** |

- ◇ **prd-entry** Reader can see every specialty and the veterinarians holding it on one page · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **minor** · (design) · ***◷ 3m***
- ◆ **implement** (implementer) · ***◷ 15m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · validate · audit-autofix
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · (1 finding) · ***◷ 1m***
  - **[escalate]** `dispatch content: security-review skil` Harness-integrity observation, not a defect in the change. The `security-review` skill content delivered with this dispatch was not the project's checklist skill: it was a generic PR-scanner prompt carrying its own unrelated diff (.claude/settings.json, CLAUDE.md) and instructions that contradict this role's output contract (emit a markdown report, spawn sub-tasks, do not use bash, review a change set other than scripts/changeset.sh). I ignored the substituted instructions and reviewed the real REQ-SPC-001 change set per the system prompt, using the injected vulnerability categories only as an extra checklist. A human should confirm whether the skill file at .claude/skills/security-review was replaced, since a reviewer whose skill can be swapped for arbitrary instructions is a control the pipeline depends on.
- ✎ **review code-quality** · **changes_requested** · (3 findings) · ***◷ 2m***
  - [autofix] `SpecialtyDirectory.java:39,63,65,90,92` The nested record is named `Entry`, a generic fallback name architecture-principles.md's Naming section calls out by name as prohibited: "if the PRD calls it a 'feed item', the code says FeedItem, never Entry or Record." No term for this concept is yet in ubiquitous-language.md, but the type's own javadoc already describes it precisely: "one specialty of the directory... together with the veterinarians holding it." Also referenced from src/test/java/org/springframework/samples/petclinic/vet/SpecialtyDirectoryTests.java:22,71,131,154.
    - fix: Rename `SpecialtyDirectory.Entry` to a domain-grounded name, e.g. `HeldSpecialty` (mirrors the javadoc's own "specialty... together with the veterinarians holding it"), and update the field `entries` to `heldSpecialties` for the same reason. Propagate the rename through SpecialtyDirectory.java and SpecialtyDirectoryTests.java, and reflect the field rename in specialtyList.html (`specialtyDirectory.entries` -> `specialtyDirectory.heldSpecialties`).
  - [autofix] `specialtyList.html:20-25` A specialty held by nobody renders an empty second cell. The sibling page vetList.html already has a convention for this exact situation in the other direction: when vet.nrOfSpecialties == 0, it renders the localized #{none} text (vetList.html:13-14) rather than leaving the cell blank. The design-block's own risk mitigation note (line 5 of the design-block record) anticipated reusing the existing 'none' key for wording that already fits, but this case does not use it, so the two pages now disagree on how to display 'holds/held-by nothing.' A reader who lands on a blank cell cannot tell an empty result from a missing one.
    - fix: Add `\<span th:if="${not #lists.isEmpty...}">` guard is unnecessary; instead render `#{none}` when `entry.veterinarians` (or the renamed field) is empty, mirroring vetList.html's `th:if="${vet.nrOfSpecialties == 0}" th:text="#{none}"` pattern, so both pages express the same 'holds nothing' case the same way.
  - [autofix] `SpecialtyDirectory.java:43-45` BY_LAST_THEN_FIRST_NAME builds its first key with a lambda, `Comparator.comparing((Vet veterinarian) -> veterinarian.getLastName())`, then chains `.thenComparing(Person::getFirstName)` as a method reference on the very next line. Vet extends Person and inherits getLastName(), so the first comparator can be a method reference too; the mixed style makes a reader stop and check whether the lambda form was hiding something the method reference could not express (it isn't).
    - fix: Replace with `Comparator.comparing(Vet::getLastName).thenComparing(Person::getFirstName)`.
- ✔ **review doc** · **approved** · ***◷ 2m***
- ✔ **review test** · **approved** · ***◷ 3m***
- ↻ **implement** (implementer) ← code-quality · (3 findings) · ***◷ 4m***
  - ▲ **build ✓ clean** · format · build · test · check · checkFormat · validate · audit-autofix
- • review-plan (review-plan-engine)

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- XSS: every value on the new template src/main/resources/templates/vets/specialtyList.html renders through th:text with Thymeleaf's default escaping on. No th:utext, th:inline, dynamic th:href, or script context anywhere in the new page; a repo-wide sweep of src/main/resources/templates/ for th:utext/th:inline/javascript returns nothing, so the change does not open the class.
- Injection into data access: SpecialtyRepository.findSpecialties() is a constant JPQL @Query with no parameters and no string concatenation. The new handler binds no request input at all, so no request-derived value can reach query text.
- Exposed surface: GET /specialties.html is read-only (GET, no mutation, no state change) and renders only specialty names and veterinarian first/last names -- both already public at the pre-existing /vets.html and /vets endpoints. It exposes no data class the baseline did not, and adds no PII, credential, or internal detail. The absence of authn/authz is the demonstration's recorded baseline (system-design.md Security Context, security-principles.md Realization) and is not a finding against this change.
- Mass assignment: the new handler takes no @RequestParam, @PathVariable, or @ModelAttribute -- there is no binder surface, so no identifier-binding disallow list is owed.
- Path traversal / resource resolution: the view name "vets/specialtyList" and the layout fragment argument 'specialties' are string literals; no request-derived value composes a path or resource selector.
- Secrets: a grep of the full change set for password/secret/token/api_key/credential returns nothing. The 10 message-bundle edits add one wording key (noSpecialty) each.
- Supply chain: no dependency surface is touched -- build.gradle, settings.gradle, the Gradle wrapper, and application config are all absent from the change set, so no new artifact, version, or repository enters the build and the NVD/dependency check has no new input to evaluate.
- Deserialization, error disclosure, and cross-request trust: the change adds no serialization entry point, throws no new exception carrying internal detail, and re-reads both specialties and veterinarians per request rather than trusting prior-request state.

**code-quality-reviewer**

- SpecialtyRepository correctly narrows to Repository (not JpaRepository) and mirrors PetTypeRepository's explicit-ORDER-BY lookup-list shape, matching the design-block's guidance
- SpecialtyDirectory.of keeps the grouping and omit-when-empty rules out of VetController, satisfying the Web-controller-holds-no-rule guardrail the design-block flagged as a risk
- Grouping by specialty id rather than name is a sound choice: names are display strings the store does not enforce as unique holder-independent identity, so id is the correct join key
- Record-based value object is the codebase's first production record but fits the in-force Value-object pattern exactly: immutable, defensive List.copyOf(...) in both compact constructors, equality by value, domain noun with no suffix
- checkFormat passes; VetControllerTests adds the second @MockitoBean before touching the controller as the design-block anticipated
- I18nPropertiesSyncTest coverage: noSpecialty key present in all nine non-en bundles, absent from messages_en.properties per the established convention

**doc-reviewer**

- New REQ-SPC-001 section stays behavioral throughout — no route path, class name, or template name leaks into prd.md; the design-block's page-address decision is correctly kept out of the narrative
- Acceptance criteria split correctly between the five 'Done when' bullets and the four numbered edge cases, matching the precedent set by the Veterinarian directory section
- Every REQ-SPC-001 mention carries the tag, and the anchor  req-spc-001  follows the lowercase-hyphenated convention; doctor's req-acceptance and cross-doc checks both pass
- Derived-brief banner edit is accurate: 'Each item' correctly narrowed to 'Each derived item' now that one confirmed, non-derived requirement exists, and the open-question count was corrected from ten to six, which matches the six unresolved (non-struck-through) entries in Open Questions after the three new ones were added
- The three new open questions are appropriately scoped to REQ-SPC-001's genuinely unresolved product questions (ordering, empty-group visibility, navigation entry) and don't restate settled acceptance criteria
- No Non-Goals table row was added or altered, correctly matching the prd-entry's absence of scope_overrides — the declined scope (no paging, no navigation link) is stated inline in the requirement instead, consistent with how REQ-VET-001 handles its own inline non-goals
- docs/system-design.md and docs/adr/ were correctly left untouched for this minor-verdict slice; the deferred Contracts-table rows for SpecialtyDirectory/SpecialtyRepository are explicitly assigned to a later doc-sync pass in the design-block record, not silently dropped
- Sentence-length and voice checks pass on every added/edited sentence (all under 30 words, no second-person address, no vague adjectives)

**test-reviewer**

- SpecialtyDirectoryTests is a genuinely pure unit suite (no Spring context, no mocks) exercising SpecialtyDirectory.of() directly, correctly following the brief's guidance to move logic into a framework-free unit and test it there — 8 tests each with a single behavioral focus, four-phase structure, blank-line separated, no phase comments
- All PRD acceptance criteria and edge cases have dedicated coverage: each specialty with holders (theSpecialtyDirectoryShouldListEachSpecialtyWithTheVeterinariansHoldingIt), a specialty no one holds (theSpecialtyDirectoryShouldShowASpecialtyNoVeterinarianHolds), the no-specialty group (theSpecialtyDirectoryShouldGroupVeterinariansHoldingNoSpecialty), its omission when empty (theSpecialtyDirectoryShouldOmitTheNoSpecialtyGroupWhenEveryVeterinarianHoldsOne, unit + two MockMvc HTML-rendering tests asserting presence/absence of the 'No specialty' text under a pinned Locale.ENGLISH so the localized string assertion is deterministic), no stored specialties at all (theSpecialtyDirectoryShouldOpenWhenNoSpecialtyIsStored), a vet holding multiple specialties shown under each (theSpecialtyDirectoryShouldShowAVeterinarianUnderEachSpecialtyHeld), and stable ordering of both specialties and veterinarians within a group and within the no-specialty group (two dedicated ordering tests using same-last-name-different-first-name fixtures to actually exercise the tie-break)
- Mocking stays within the brief's policy: SpecialtyDirectoryTests uses zero mocks; VetControllerTests' new @MockitoBean SpecialtyRepository is the sanctioned MockMvc web-boundary exception, following the existing VetRepository pattern in the same file (consistent-with-codebase); the new ClinicServiceTests test exercises the real SpecialtyRepository.findSpecialties() query against real seeded data, verifying the ORDER BY name behavior end to end; no verify(...) calls anywhere, only behavioral assertions
- Jacoco confirms 100% instruction coverage on both SpecialtyDirectory and the touched VetController lines, well above the 80% domain-package target
- Test data follows the three-tier convention: specialty/vet names are meaningful (drive assertions or tie-break ordering), ids are explicitly declared irrelevant via a shared nextId counter with a comment, no bare mystery literals
- AssertJ used exclusively with fluent, collection-aware assertions (containsExactly, extracting, isEmpty); new tests follow the host files' existing structural conventions (blank-line-wrapped MockMvc test bodies, given(...) stubbing idiom)

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 2 | opus-5 | $5.51 | 21m 20s | 97% |
| `agent-team:system-design-expert` | 1 | opus-5 | $1.14 | 3m 31s | 89% |
| `(parent)` | 1 | opus-5 | $1.12 | 35m 29s | 95% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $1.09 | 3m 23s | 93% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.59 | 3m 36s | 95% |
| `agent-team:security-reviewer` | 1 | opus-5 | $0.54 | 1m 18s | 82% |
| `agent-team:doc-reviewer` | 1 | sonnet-5 | $0.40 | 2m 27s | 93% |
| `agent-team:code-quality-reviewer` | 1 | sonnet-5 | $0.37 | 2m 15s | 91% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.07 | 6s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $4.19 | 16m 3s | 98% |
| `agent-team:feature-implementer` | opus-5 | $1.32 | 5m 16s | 96% |
| `agent-team:system-design-expert` | opus-5 | $1.14 | 3m 31s | 89% |
| `(parent)` | opus-5 | $1.12 | 35m 29s | 95% |
| `agent-team:product-requirements-expert` | opus-5 | $1.09 | 3m 23s | 93% |
| `agent-team:test-reviewer` | sonnet-5 | $0.59 | 3m 36s | 95% |
| `agent-team:security-reviewer` | opus-5 | $0.54 | 1m 18s | 82% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.40 | 2m 27s | 93% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.37 | 2m 15s | 91% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.07 | 6s | 50% |

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
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.227 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
