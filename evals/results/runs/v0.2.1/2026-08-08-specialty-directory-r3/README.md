# specialty-directory r3 — v0.2.1

Specialty directory page (feature) · started 2026-08-08T19:34:00+00:00 · exec `claude-dev` · status **complete**

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
| 5 (±1) | 4 (±0) | 4 (±0) | 4 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.87. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 4

> SpecialtyController is a thin package-private controller holding no rule; SpecialtyRepository extends the narrow Repository with a fixed ORDER BY; SpecialtyDirectory is an immutable value object with List.copyOf and value equality, and an ADR records why the projection beats a bidirectional mapping — a clean catalog match. Tests are behavior-named (theSpecialtyDirectoryShouldListASpecialtyNoVeterinarianHolds), phase-separated, factory-built, and use hand-written stubs (StoredSpecialties, EmployedVets) over a mock framework, but createASpecialty/createAVetHolding are duplicated verbatim across SpecialtyControllerTests and SpecialtyDirectoryTests instead of shared vocabulary, and several equals/hashCode cases (theSpecialtyDirectoryShouldNotEqualAValueOfAnotherType) are low-signal. Docs are updated broadly, yet prd.md now claims "seven further questions stay open" while the patch adds four questions and removes none.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 4 · doc-fit 4

> Placement is idiomatic: SpecialtyController stays package-private and only sequences two reads, all grouping lives in the immutable SpecialtyDirectory value object, SpecialtyRepository narrows to Repository rather than JpaRepository, and an ADR plus a vocabulary entry ("Listed specialty") back the projection choice. Tests are BDD-named, four-phase, factory-built, and use hand-written stubs over a mock framework; deductions for index access (getListedSpecialties().get(0)), several equals/hashCode boilerplate tests, stub beans shared across methods and reset in emptyTheRecords(), and no case for the held.getId() != null branch. Docs move widely, but prd.md now says "seven further questions stay open" after adding four bullets to a list previously counted as ten; messages_hi.properties also breaks its \u-escape convention.

**Sample 3** — design-fit 4 · test-quality 4 · maintainability 4 · doc-fit 4

> Placement fits:  SpecialtyRepository  uses the narrow  Repository  interface,  SpecialtyController  binds/delegates/selects with no rule, and grouping sits in an immutable  SpecialtyDirectory  unit-testable without a context, with an ADR recording the choice. Deductions:  ListedSpecialty.equals  delegates to  Specialty , which overrides no equality, so the declared value-object equality is really reference equality; the equals/hashCode surface exists mostly for tests, and six of fourteen  SpecialtyDirectoryTests  cases exercise it.  getListedSpecialties().get(0)  (two tests) is index-based access the checklist forbids, and the  @Import ed stubs are shared mutable fixtures reset in  emptyTheRecords() . Naming, factories, hand-written stubs and four-phase structure are otherwise exemplary. Docs are near-complete, but prd.md now claims "seven further questions stay open" after replacing "ten" while adding four.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $18.93 | 53m | 33 | 92% | 22 file(s) +895/−9 |

## Change

Patch over 400 lines — too large to embed; see [`change.patch`](change.patch).

## Pipeline

### REQ-VET-002

0 review rounds · 0 build-passes · no grade yet


---

### REQ-VET-003 — Specialty directory: which veterinarians hold this specialty

2 review rounds · 2 build-passes · **1 build-failure** · no grade yet

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (1) | **✔** |
| **test** | ✎ (2) | ✎ (1) |
| **security** | **✔** | **✔** |
| **doc** | ✎ (1) | ✎ (2) |

- ◇ **prd-entry** Specialty directory: which veterinarians hold this specialty · (prd-expert) · ***◷ 20s***
- ◈ **design-block** **new** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 13m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L5 · ***◷ 2m***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [clarify] `SpecialtyDirectory.java:130` Nested type `SpecialtyDirectory.Entry` violates the explicit naming rule in docs/architecture-principles.md § Naming: 'the code says FeedItem, never Entry or Record.' The implementer's argument (no ubiquitous-language term exists for 'one specialty plus its holders', so inventing one oversteps implementer scope) is procedurally sound, but the conclusion does not follow: the rule is unconditional on the word `Entry`, and the system-design-expert flagged rather than resolved it at design-block line 9. This is a naming/vocabulary decision for the domain owner, not a judgment call for the reviewer or a mechanical rename for the implementer.
- ✔ **review security** · **approved** · ***◷ 50s***
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 2m***
  - **[blocked]** `SpecialtyControllerTests.java:98-146` Every test in both files constructs one Specialty instance and passes that same object reference into both the specialties collection and vet.addSpecialty(...) (via createASpecialty/createAVetHolding + Vet::addSpecialty). SpecialtyDirectory.identityOf/holdersBySpecialtyId match holders by Specialty.getId(), precisely because the ADR (docs/adr/2026-08-08-specialty-directory-projected-in-application-code.md) states the two reads return separate Specialty instances under the real cached VetRepository, and Specialty inherits no equals(). None of the 11 tests exercise that scenario: because the same instance is shared, a regression from id-based matching to reference matching (held == specialty) would still pass every test in the suite. This is the exact bug the design re-triage flagged as a risk, and the suite as written would not catch it. Add at least one SpecialtyDirectoryTests case that builds two distinct Specialty objects carrying the same id (one placed in the specialties list, a different instance with the same id attached to the vet via addSpecialty) and asserts the vet still appears as a holder — proving id-based matching rather than accidentally passing via shared reference.
  - [autofix] `hashCode` JaCoCo shows SpecialtyDirectory.hashCode() at 0% and equals() at 50% branch coverage, and Entry.equals()/hashCode() at 0% coverage — Entry.class overall sits at 38% instruction / 0% branch coverage, below the domain-package 80% line-coverage target in docs/testing-principles.md § Coverage. No test in SpecialtyDirectoryTests constructs two directories/entries to compare for equality; the one equals-based assertion in SpecialtyControllerTests (model().attribute with an empty SpecialtyDirectory) only exercises the trivial empty-list case. The two-distinct-Specialty-instances-same-id test requested above would also close most of this gap (its assertion path runs through Entry.equals for holder membership); add a small direct SpecialtyDirectoryTests case for the equals/hashCode contract itself (equal-by-content but different instance, unequal entries, wrong type) so the value object's identity contract is verified, not just incidentally exercised.
    - fix: Add unit tests in SpecialtyDirectoryTests for SpecialtyDirectory/Entry equals() and hashCode(): reflexivity (self-equals), two directories built from equal-content-but-distinct entries are equal, a directory with a different entry is not, and equals(nonSpecialtyDirectoryObject) is false.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 2m***
  - **[blocked]** `prd.md: Non-Goals table` No PRD non-goal records that a machine-readable specialty listing is out of scope. REQ-VET-002 (machine-readable veterinarian list) was withdrawn as an implementation artifact and its ID is correctly kept unreused (Superseded list, line 190), but the new Specialty directory requirement is the inverse of that same data and carries the identical regrowth risk — the system-design-expert's own risk log names it explicitly ("REQ-VET-002 regrows") and the design/ADR treat single-HTML-route-only as a deliberate constraint. Nothing in docs/prd.md states this as a non-goal: the Non-Goals table (NG-1..NG-9) has no row for it, and the Specialty directory prose/edge cases are silent. A reader of the PRD alone cannot tell that a machine-readable specialty representation was considered and excluded.
- ↻ **fix design** ← code-quality · (1 finding)
- ◇ **prd-entry** Specialty directory: which veterinarians hold this specialty · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **new** · (design) · ***◷ 4m***
- ◆ **implement** (implementer) · ***◷ 4m***
  - ▲ **build ✓ clean** · build · test · check · format · checkFormat · checkstyleMain · audit-autofix · handoff-validate
- ✔ **review code-quality** · **approved** · ***◷ 39s***
- ✔ **review security** · **approved** · ***◷ 49s***
- ✎ **review doc** · **changes_requested** · (2 findings) · ***◷ 2m***
  - **[escalate]** `architecture-principles.md:115` The naming-rule sentence 'the code says FeedItem, never Entry or Record' is genuinely ambiguous, as the system-design-expert's design-block at line 24 surfaced without fixing. Read as provenance guidance it binds only when the vocabulary names a concept; read as an outright ban it forbids two words unconditionally — and the brief's separate Prohibited-suffixes mechanism at :134 lists Manager/Helper/Utility/Handler/Processor/Base/Info/Data but omits Entry, which is evidence for the narrower reading. No agent in the roster holds write scope for docs/architecture-principles.md (absent from the review-workflow Artifact Ownership table; system-design-expert's own role text commits it to 'surface the defect rather than overriding it'), so this is a durable-doc self-contradiction with no owner to route a clarify to. It cost nothing this round only because the rename happened to satisfy both readings; the next naming dispute over a container word with no vocabulary term will not be so lucky.
  - [clarify] `prd.md Non-Goals table, NG-10` NG-10 declines the same alternative REQ-VET-002 already built and withdrew — a textbook 'rejecting a reasonable alternative' case under the adr-template skill's When-to-Create list, and the same table's NG-4/NG-5 rows record materially similar-weight non-goal decisions with a linked ADR. NG-10 has none; the preamble states this plainly rather than papering over it, so the PRD itself stays internally honest and no cross-reference is broken — this is not a blocking coherence defect. But the precedent set by NG-4/NG-5 in the same table, plus the adr-template criterion, both point toward writing the non-goal ADR the product-requirements-expert chose to skip. Confirm the omission is a deliberate scope call, not an oversight, and record an ADR at docs/adr/2026-08-08-non-goal-machine-readable-specialty-listing.md if not.
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 2m***
  - [autofix] `SpecialtyDirectory.java:88` JaCoCo (./gradlew test jacocoTestReport, verified both on the vet-package subset and the full suite) shows this branch at 1-of-2 missed: no test ever gives a held Specialty a null id, so the false path — a veterinarian holding a specialty the store never assigned an identity to, silently excluded from the holder map — is never exercised. This is the held-side twin of theSpecialtyDirectoryShouldRejectASpecialtyThatCarriesNoIdentity, which covers only the listed-side null-id case; the held side has no equivalent. Consequence: SpecialtyDirectory overall sits at 93% branch coverage, not the 94% the implementer's report claimed — confirmed by direct read of the tfoot row in build/reports/jacoco/test/html/.../SpecialtyDirectory.html (0 of 161 instructions, 1 of 16 branches missed). Line coverage is 100% and clears the brief's 80% line-coverage target regardless, so this is not a gate failure, but it is a real untested branch in code central to this round's review and the reported number does not match the artifact.
    - fix: Add a SpecialtyDirectoryTests case: a vet holds a Specialty with no id (alongside a real specialty), and the directory still constructs successfully with that vet omitted from every holder list — proving the defensive null-id skip on the held side, symmetric to the existing listed-side rejection test.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- SpecialtyDirectory correctly treated as the first non-entity domain value object: both constructor inputs are defensively copied (List.copyOf) and both getEntries()/getHolders() hand out only the copied unmodifiable views; entities themselves (Specialty, Vet) are referenced not copied, matching the design rationale in the class Javadoc
- No grouping/aggregation logic leaked into SpecialtyController; it delegates entirely to SpecialtyDirectory's constructor and stays a thin GET handler
- SpecialtyRepository extends the narrow Repository (not JpaRepository) with an explicit  ORDER BY specialty.name  in the @Query, matching the confirmed design and the PetTypeRepository-style read-only shape
- HOLDER_ORDER comparator and the fixed repository ORDER BY give deterministic rendering, documented with the reasoning in Javadoc rather than left implicit
- ./gradlew checkFormat and compileJava both pass clean on the change set

**security-reviewer**

- Output escaping: specialtyDirectory.html renders every database-sourced value through th:text (entry.specialty.name, holder.firstName/lastName) with Thymeleaf's default HTML escaping on. Swept the whole template for th:utext, inlined expressions ([[${...}]] / [(${...})]), javascript: URLs, event-handler attributes, and DOM injection - none present. Page chrome uses #{} message keys only; the ten added bundle values are literal headings with no expression or format-specifier content.
- No injection surface: the single JPQL string in SpecialtyRepository.findSpecialties is a compile-time constant with no parameters and no concatenation; ORDER BY specialty.name is a fixed literal, not a caller-supplied sort key. The route takes no path variable, no request parameter, and no request body, so no request-derived value reaches the query - confirmed against SpecialtyController.showSpecialtyDirectory(Model), whose only argument is the model.
- Mass assignment / binding: no @ModelAttribute, no form-backed type, no WebDataBinder on the new controller. The GET is read-only and the repository extends the narrow Repository rather than JpaRepository, so no save or delete capability is exposed on Specialty - least privilege honoured rather than merely unused.
- Exposed surface: one new unauthenticated GET (/specialties.html) rendering specialty names and veterinarian full names. Both classes of data are already published by the existing /vets.html surface, so the change does not widen the baseline in docs/system-design.md Security Context. Per docs/security-principles.md the absence of authentication and CSRF is the demonstration's recorded shape, and URL-only reachability is correctly treated as a product decision, not a control.
- Error paths: the only new exception is IllegalArgumentException in SpecialtyDirectory.identityOf, whose message carries a specialty name - stored, non-sensitive data the page itself renders. No credential, connection string, session identifier, or internal path reaches the error page. Secret sweep over the new Java, template, and bundle files for password/secret/token/key/credential returned nothing.
- Supply chain: git diff over build.gradle, settings.gradle, gradle.properties, and gradle/ is empty - no dependency added, no version moved, no repository or plain-HTTP check altered. The four dependency checks in system-design.md are not engaged by this change.
- Unbounded result set assessed and not recorded as a finding: two full-table reads (specialties, plus the already-cached VetRepository.findAll) render on one page. At the clinic-scale data volume this feature targets, an anonymous request costs no more than the existing /vets.html read path, so no-pagination is a product decision with no denial-of-service consequence at this scale. Worth revisiting only if specialty or veterinarian counts leave clinic scale.

**test-reviewer**

- theSpecialtyDirectoryShouldOrderItsEntriesRepeatably genuinely proves the HOLDER_ORDER sort at the value-object level using non-alphabetical vet-construction order (leary, douglas, carter -> carter, douglas, leary), correctly bypassing the @Cacheable("vets") masking risk the design flagged
- Hand-written StoredSpecialties/EmployedVets stub beans are properly isolated: @BeforeEach resets both to empty records before every test, so no state leaks between methods despite the stubs being long-lived context beans
- A specialty nobody holds and a vet holding no specialty are each covered at both the unit (SpecialtyDirectoryTests) and controller (SpecialtyControllerTests) level
- AssertJ used throughout, four-phase structure with blank-line separation, BDD the{Subject}Should{Outcome} naming, and Tier-1/Tier-2 data naming (RADIOLOGY/SURGERY/DENTISTRY constants, createASpecialty/createAVetHolding factories) all followed
- SpecialtyDirectoryLinkTests genuinely proves the no-inbound-link requirement by scanning real template files rather than asserting on a mock

**doc-reviewer**

- REQ-SYS-001 is stated unambiguously both ways: the specialty page carries the shared navigation (satisfying REQ-SYS-001) while a separate Done-when bullet and prose sentence state nothing links to the page — no contradiction.
- REQ-VET-002 stays in the Superseded list, withdrawn 2026-07-31, ID unreused, and correctly distinguished from the new REQ-VET-003.
- The deliberate bare-vs-'none' inconsistency between the specialty directory and the veterinarian directory is recorded as an unresolved Open Question, naming both sides of the divergence.
- Open Questions count: banner says 'seven further questions stay open' and exactly seven unanswered (non-struck-through) items follow — count is correct.
- Provenance banner correctly marks REQ-VET-003 as stated intent (2026-08-08) against every other requirement's derived/unconfirmed provenance.
- docs/ubiquitous-language.md banner now defines the 'added' mark, and the two new terms (Veterinarian directory, Specialty directory) are dated and cross-referenced correctly.
- docs/adr/README.md carries the new ADR's index row; the ADR's Implementation section carries Requirements: REQ-VET-003 and its Consequences bullet on identity-matching matches the system-design.md invariant it backs.
- SpecialtyDirectory.Entry needs no ubiquitous-language term: neither system-design.md's Contracts table nor its prose references the nested type by name, so no undefined domain term leaks into durable docs.

**code-quality-reviewer**

- Round-one clarify finding (SpecialtyDirectory.Entry naming) is resolved by naming the vocabulary term rather than arguing around it: docs/ubiquitous-language.md now defines Listed specialty and Holder, and the rename to ListedSpecialty/listedSpecialties/getListedSpecialties() is complete and symbol-precise across SpecialtyDirectory.java, specialtyDirectory.html, and SpecialtyDirectoryTests.java — grep for Entry/getEntries/.entries across src/main and the vet test package finds no stragglers, and unrelated Map.Entry/containsEntry usages elsewhere were correctly left untouched.
- theSpecialtyDirectoryShouldOrderItsEntriesRepeatably keeping 'Entries' in its name is correct, not a gap: the name is pinned verbatim in the prd-entry test_names list, and renaming it would desync the suite from the PRD record for no benefit.
- New test factory createASeparateInstanceOf(Specialty stored) and its id-based holder-matching test read as a real behavioral case (identity match across two independent reads), not incidental churn.
- The seven new equals/hashCode tests on SpecialtyDirectory and ListedSpecialty are properly split (self-equality, equal value, unequal specialty, unequal holders, unequal type) and use AssertJ's isEqualTo/hasSameHashCodeAs consistently with the rest of the suite.
- Renaming the constructor local listed to paired to free listed for the instanceof ListedSpecialty listed pattern variable is a clean, minimal collision fix — the pattern variable name mirrors the field/parameter naming used everywhere else in the class.
- Javadoc on getListedSpecialties() and the holdersBySpecialtyId in-line comment read naturally post-rename with no leftover 'entry' vocabulary.
- ./gradlew checkFormat passes clean on the current change set (checkJavaFormat is not a task in this project; checkFormat is the correct task name).

**security-reviewer**

- Re-verified output escaping after the rename: src/main/resources/templates/vets/specialtyDirectory.html:18-21 rebinds to th:each="listed : ${specialtyDirectory.listedSpecialties}" and renders database-sourced values only through th:text (${listed.specialty.name}, and holder.firstName/lastName concatenated inside th:text). Thymeleaf HTML-escapes th:text by default; a grep over the template for th:utext, th:inline, script blocks, and event-handler attributes returned nothing, so no unescaped sink was introduced by the rebinding.
- Stored-XSS class sweep over the whole change set: the only added template is this one, and no added line anywhere in the diff contains th:utext, \<script>, innerHTML, or an inline JavaScript context. The ten message-bundle files add one developer-authored key each (specialtyDirectory=...), rendered via #{} through th:text at line 8 — no user-derived interpolation and no message argument.
- No injection surface changed: SpecialtyRepository.findSpecialties() remains a static JPQL string with no parameters and no concatenation, and SpecialtyController.showSpecialtyDirectory takes no request parameter, path variable, header, or body — the route accepts no attacker-controlled input at all. Grep for concat, createQuery, Runtime., and ProcessBuilder over added lines returned nothing.
- Trust boundary and data exposure unchanged: the page is read-only (narrow Repository extension deliberately withholds save/delete), exposes only specialty names and vet first/last names already published by the existing /vets pages, and adds no new external call, file I/O, or deserialization path. SpecialtyDirectory hands out unmodifiable copies (List.copyOf) so a rendered request cannot mutate shared entity state.
- No secrets introduced: a case-insensitive sweep of added lines for password, secret, token, api key, and credential produced no hits.
- Supply chain unchanged since the round-one verification: build.gradle and the Gradle lock/wrapper files are absent from scripts/changeset.sh --name-only, so no dependency was added, upgraded, or repinned in this round and the round-one CVE check still stands.
- Renamed identifiers and the equals/hashCode additions are behaviour-preserving with no security relevance; the new tests touch no production trust boundary.

**doc-reviewer**

- Round-one blocked finding (line 20) resolved: NG-10 is now a real Non-Goals row with rationale and decision date, the Specialty directory prose links it inline, and the preamble's 'explains each row'/'derived from absence' claims are corrected to name NG-10 as decided rather than silently left false
- REQ-VET-002 stays withdrawn, unreused, and correctly distinguished from REQ-VET-003 in the Superseded list
- Open Questions banner claims seven open questions; exactly seven non-struck-through items are present, count verified by direct listing
- docs/ubiquitous-language.md gained Listed specialty and Holder, both dated added 2026-08-08, both with Relationships and Avoid lines; Listed specialty's Avoid line (Entry, Record, Listing, Row) matches the naming-rule concern that motivated it
- Code rename from SpecialtyDirectory.Entry to SpecialtyDirectory.ListedSpecialty is complete and consistent: verified in SpecialtyDirectory.java, specialtyDirectory.html (listed/listedSpecialties bindings), and the test suite — no stale Entry reference remains, and JDK Map.Entry / AssertJ containsEntry usages elsewhere are untouched, confirming the rename was scoped by symbol as instructed
- docs/system-design.md and the ADR never named the nested type, so the rename needed no edit there and none was made; docs/adr/README.md carries the ADR's index row correctly
- Full changeset swept (scripts/changeset.sh --name-only): every changed doc path (prd.md, system-design.md, ubiquitous-language.md, adr/README.md, the ADR) is internally consistent and cross-references resolve

**test-reviewer**

- Round-1 critical finding (id- vs reference-based holder matching) verified as fixed: theSpecialtyDirectoryShouldFindAHolderCarryingASeparateInstanceOfTheSameSpecialty builds radiologyAsHeld via a new createASeparateInstanceOf(Specialty) factory that copies id and name into a fresh Specialty object, pins its own premise with isNotSameAs, and then asserts the vet is still a holder; traced against SpecialtyDirectory.holdersBySpecialtyId/identityOf, which match by getId() — a regression to reference matching (held == specialty) would leave the holder map empty for this case and the final assertion would fail. Confirms the fix.
- Round-1 autofix finding (equals/hashCode coverage) verified: 6 new SpecialtyDirectory-level tests (self-equality, equal-content-different-instance with hasSameHashCodeAs, different specialty, different holders on the same specialty — reached only because the specialty-equal check does not short-circuit past it, different type) plus 2 on the nested ListedSpecialty (self-equality, different type) drive SpecialtyDirectory to 100% instruction/100% line/93% branch and SpecialtyDirectory$ListedSpecialty to 100% across instruction/line/branch/method, both confirmed by direct JaCoCo HTML read rather than the implementer's report.
- ListedSpecialty rename (Entry -> ListedSpecialty, entries -> listedSpecialties, getEntries() -> getListedSpecialties()) is complete and consistent: grep over the production class, the template, and both test files finds no stray old symbol outside the one test name (theSpecialtyDirectoryShouldOrderItsEntriesRepeatably) the prd-entry test_names list pins verbatim — correctly left alone.
- Suite structure, naming, AssertJ usage, and Tier-1/Tier-2 data naming from round 1 remain intact; all vet-package tests pass (./gradlew test --tests 'org.springframework.samples.petclinic.vet.*').

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $9.34 | 21m 34s | 95% |
| `agent-team:system-design-expert` | 3 | opus-5 | $7.01 | 14m 35s | 94% |
| `(parent)` | 1 | opus-5 | $5.14 | 52m 23s | 95% |
| `agent-team:product-requirements-expert` | 2 | opus-5 | $3.88 | 7m 50s | 91% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $2.08 | 4m 31s | 89% |
| `agent-team:security-reviewer` | 2 | opus-5 | $1.88 | 1m 58s | 78% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $1.86 | 5m 33s | 89% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $1.25 | 2m 3s | 82% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.06 | 0s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $5.77 | 14m 12s | 96% |
| `(parent)` | opus-5 | $5.14 | 52m 23s | 95% |
| `agent-team:system-design-expert` | opus-5 | $3.09 | 6m 1s | 95% |
| `agent-team:feature-implementer` | opus-5 | $2.37 | 5m 6s | 93% |
| `agent-team:product-requirements-expert` | opus-5 | $2.27 | 5m 18s | 93% |
| `agent-team:system-design-expert` | opus-5 | $2.24 | 5m 17s | 93% |
| `agent-team:system-design-expert` | opus-5 | $1.68 | 3m 16s | 92% |
| `agent-team:product-requirements-expert` | opus-5 | $1.61 | 2m 32s | 88% |
| `agent-team:feature-implementer` | opus-5 | $1.20 | 2m 16s | 91% |
| `agent-team:doc-reviewer` | sonnet-5 | $1.14 | 2m 13s | 92% |
| `agent-team:test-reviewer` | sonnet-5 | $1.01 | 3m 4s | 90% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.94 | 2m 17s | 85% |
| `agent-team:security-reviewer` | opus-5 | $0.94 | 57s | 80% |
| `agent-team:security-reviewer` | opus-5 | $0.93 | 1m 0s | 75% |
| `agent-team:test-reviewer` | sonnet-5 | $0.86 | 2m 28s | 88% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.69 | 46s | 81% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.56 | 1m 16s | 84% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.06 | 0s | 0% |

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
