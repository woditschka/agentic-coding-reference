# owners-page-param r1 — v0.2.1

Owner listing crashes on page values below 1 (bugfix) · started 2026-08-07T16:01:02+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Bug report: opening /owners?page=0 — or any page value below 1 — renders the
> error page instead of the owner list. Expected behavior: the owner listing
> treats any page value below 1 as the first page and responds with the normal
> listing (HTTP 200). Find the cause, fix it, and cover the fix with a test.

## Verdict

| check | result |
|---|---|
| oracle | ✔ 3/3 passed |
| suite (post-agent) | ✔ |
| suite (pristine baseline) | ✔ |
| checkpoints | 6/6 |
| review attention (pipeline grade) | clear |

The pipeline grade estimates how much human review the change deserves before merge — advisory context from the harness's change grader (read from the ledger's `grader-verdict` record), never part of the bar.

- ✔ `theNegativePageRequestShouldRenderTheFirstListingPage` — passed
- ✔ `theOwnerListingShouldRenderForARegularPageRequest` — passed
- ✔ `thePageZeroRequestShouldRenderTheFirstListingPage` — passed

## Checkpoints

The kind's graded ladder, derived from the recorded facts — context only, outside the quality bar (bench README § Checkpoints).

- ✔ `agent complete`
- ✔ `change produced`
- ✔ `suite green`
- ✔ `theNegativePageRequestShouldRenderTheFirstListingPage`
- ✔ `theOwnerListingShouldRenderForARegularPageRequest`
- ✔ `thePageZeroRequestShouldRenderTheFirstListingPage`

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 4 (±1) | 3 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.37. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> The clamp sits where the request is bound ( int currentPage = Math.max(page, FIRST_PAGE) ), which the Web controller pattern permits as normalization rather than a new business rule, and  FIRST_PAGE  is named — though it now duplicates the literal in  @RequestParam(defaultValue = "1") , and the clamp could have lived in  findPaginatedForOwnersLastName  for a single seam. The comment above the clamp restates what  Math.max  already says, the kind of narration the principles ask to remove. The test name is properly BDD and the  @ValueSource(ints = {0, -1})  boundary pair is well chosen, but  new Owner()  bypasses a factory and is an unexplained filler value, and the  ArgumentCaptor / getPageNumber()).isZero()  assertion tests Spring Data's zero-based indexing — implementation detail beyond the behavior this test owns.

**Sample 2** — design-fit 3 · test-quality 3 · maintainability 4 · doc-fit 5

> The clamp is minimal and lands where the paging already lives, but  int currentPage = Math.max(page, FIRST_PAGE)  (OwnerController:99) is a new rule inside a controller — exactly what the catalog's Web controller row calls a fresh violation — and it was liftable into a unit-testable seam, so the fix and its test both stay in the slice layer the pyramid says to shrink. The redundant comment above it restates the code. The test name  theOwnerSearchShouldTreatPageBelowOneAsFirstPage  and the  pageBelowOne  parameter are exemplary, but  new Owner()  bypasses a factory, and the ArgumentCaptor/ verify  block asserts the repository interaction — implementation detail already covered by the  currentPage  model assertion. No visible documentation is invalidated.

**Sample 3** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> The clamp is placed in the controller's request-binding role, not as a new business rule, and both downstream uses are updated (OwnerController.java:113, 127), with FIRST_PAGE naming the boundary. It stops short of 5: the actual failing seam, findPaginatedForOwnersLastName's page-1 into PageRequest, stays unguarded for future callers, and @RequestParam(defaultValue = "1") still repeats the literal. The test name and @ValueSource({0,-1}) follow the BDD and parameterized conventions, but the ArgumentCaptor/verify block asserts the repository call shape — implementation detail already covered by the currentPage model assertion — new Owner() bypasses the factory-method rule, and act/assert interleave rather than forming clean phases. No documentation visible in the patch is left stale.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $5.31 | 16m | 4 | 85% | 2 file(s) +28/−2 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.18 | 2m 22s | 88% |

## Change

<details>
<summary>Diff (rendered from <code>change.patch</code>)</summary>

```diff
diff --git a/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java b/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
index b4b6145..385fc80 100644
--- a/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
@@ -50,6 +50,8 @@ class OwnerController {
 
 	private static final String VIEWS_OWNER_CREATE_OR_UPDATE_FORM = "owners/createOrUpdateOwnerForm";
 
+	private static final int FIRST_PAGE = 1;
+
 	private final OwnerRepository owners;
 
 	public OwnerController(OwnerRepository owners) {
@@ -94,6 +96,10 @@ class OwnerController {
 	@GetMapping("/owners")
 	public String processFindForm(@RequestParam(defaultValue = "1") int page, Owner owner, BindingResult result,
 			Model model) {
+		// a page below the first one is not addressable: show the first page instead of
+		// failing the request
+		int currentPage = Math.max(page, FIRST_PAGE);
+
 		// allow parameterless GET request for /owners to return all records
 		String lastName = owner.getLastName();
 		if (lastName == null) {
@@ -104,7 +110,7 @@ class OwnerController {
 		}
 
 		// find owners by last name
-		Page<Owner> ownersResults = findPaginatedForOwnersLastName(page, lastName);
+		Page<Owner> ownersResults = findPaginatedForOwnersLastName(currentPage, lastName);
 		if (ownersResults.isEmpty()) {
 			// no owners found
 			result.rejectValue("lastName", "notFound", "not found");
@@ -118,7 +124,7 @@ class OwnerController {
 		}
 
 		// multiple owners found
-		return addPaginationModel(page, model, ownersResults);
+		return addPaginationModel(currentPage, model, ownersResults);
 	}
 
 	private String addPaginationModel(int page, Model model, Page<Owner> paginated) {
diff --git a/src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java b/src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java
index dd379a5..b701c77 100644
--- a/src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java
+++ b/src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java
@@ -19,6 +19,9 @@ package org.springframework.samples.petclinic.owner;
 import org.junit.jupiter.api.BeforeEach;
 import org.junit.jupiter.api.Test;
 import org.junit.jupiter.api.condition.DisabledInNativeImage;
+import org.junit.jupiter.params.ParameterizedTest;
+import org.junit.jupiter.params.provider.ValueSource;
+import org.mockito.ArgumentCaptor;
 import org.springframework.beans.factory.annotation.Autowired;
 import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
 import org.springframework.data.domain.Page;
@@ -33,6 +36,7 @@ import java.time.LocalDate;
 import java.util.List;
 import java.util.Optional;
 
+import static org.assertj.core.api.Assertions.assertThat;
 import static org.hamcrest.Matchers.empty;
 import static org.hamcrest.Matchers.greaterThan;
 import static org.hamcrest.Matchers.hasItem;
@@ -148,6 +152,22 @@ class OwnerControllerTests {
 		mockMvc.perform(get("/owners?page=1")).andExpect(status().isOk()).andExpect(view().name("owners/ownersList"));
 	}
 
+	@ParameterizedTest
+	@ValueSource(ints = { 0, -1 })
+	void theOwnerSearchShouldTreatPageBelowOneAsFirstPage(int pageBelowOne) throws Exception {
+		Page<Owner> firstPage = new PageImpl<>(List.of(george(), new Owner()));
+		when(this.owners.findByLastNameStartingWith(anyString(), any(Pageable.class))).thenReturn(firstPage);
+
+		mockMvc.perform(get("/owners").param("page", String.valueOf(pageBelowOne)))
+			.andExpect(status().isOk())
+			.andExpect(view().name("owners/ownersList"))
+			.andExpect(model().attribute("currentPage", 1));
+
+		ArgumentCaptor<Pageable> pageable = ArgumentCaptor.forClass(Pageable.class);
+		verify(this.owners).findByLastNameStartingWith(anyString(), pageable.capture());
+		assertThat(pageable.getValue().getPageNumber()).isZero();
+	}
+
 	@Test
 	void processFindFormByLastName() throws Exception {
 		Page<Owner> tasks = new PageImpl<>(List.of(george()));
```

</details>

## Pipeline

### REQ-OWNER-001

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (1) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (1) | **✔** |

- ◆ **implement** (implementer) · ***◷ 4m***
  - ▲ **build ✓ clean** · build · test · check · format · audit-autofix · handoff-validate
- ✔ **review code-quality** · **approved** · ***◷ 33s***
- ✎ **review doc** · **changes_requested** · (1 finding)
  - [autofix] `OwnerControllerTests.java:157` New parameterized test method is named `processFindFormTreatsPageBelowOneAsFirstPage`, mirroring the production method under test. `docs/testing-principles.md` § Test Naming mandates the `the{Subject}Should{Outcome}` BDD school for tests written or modified from 2026-07-31 onward (today is 2026-08-07), and names `processFindFormByLastName` verbatim as the counter-example of an implementation name this rule prohibits — the new test repeats exactly that anti-pattern.
    - fix: Rename the test method to a behavior name, e.g. `theOwnerSearchShouldTreatPageBelowOneAsFirstPage`.
- ✔ **review security** · **approved** · ***◷ 1m***
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 3m***
  - [autofix] `OwnerControllerTests.java:157` New test method `processFindFormTreatsPageBelowOneAsFirstPage` (added 2026-08-07, after the 2026-07-31 naming-school cutoff in testing-principles.md § Test Naming) is named after the production method under test (`processFindForm...`) rather than the behavior it pins. The brief requires `the{Subject}Should{Outcome}` for tests written from that date onward — a name that would survive renaming `processFindForm` is the bar, and this one would not survive it.
    - fix: Rename to a behavior-describing name, e.g. `theOwnerSearchShouldTreatPageBelowOneAsFirstPage`.
- ↻ **implement** (implementer) ← doc, test · (2 findings) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · checkFormat · checkstyleMain · audit-autofix · handoff-validate
- ✔ **review test** · **approved** · ***◷ 8s***
- ✔ **review doc** · **approved** · ***◷ 7s***
- ✔ **review code-quality** · **approved** · ***◷ 9s***
- ✔ **review security** · **approved** · ***◷ 24s***
- ◆ **grade CLEAR** · clamp the owners page parameter at the first page
  - blast_radius — **clear** — Two files, one production and one test, both in the owner package: the edit is confined to OwnerController.processFindForm plus a new private constant, with no sensitive paths, no build or config files, and no shared helper touched.
  - semantic_surprise — **clear** — The hunks do exactly what the description says: currentPage = Math.max(page, FIRST_PAGE) replaces every downstream use of the raw parameter (the query at line 113 and the pagination model at line 127, with no stale reference to page left in the method body), so page of 1 or more behaves identically and only the previously-throwing sub-1 path changes.
  - test_adequacy — **clear** — The parameterized test over 0 and -1 would fail against the pre-fix code (PageRequest.of(-1) throws) and against a half-fix: it captures the Pageable and asserts a zero-based page number of 0 as well as a currentPage model attribute of 1, so clamping only the query or only the model would break it, and the pre-existing page=1 test remains the positive control.
  - reviewer_hedging — **clear** — Second-round approvals from all four roster reviewers carry empty findings lists and no escalate tag; the single first-round finding was a test-method naming-school violation raised identically by doc-reviewer and test-reviewer, fixed by a rename that changed no assertion, and the security reviewer explicitly re-verified that the delta since its first approval was that rename alone.
  - scope_deviation — **clear** — Zero design revisions, consultations, and build retries; the diff touches exactly the two files the implementation plan named, and the identical defect at VetController.java:61 was recorded in the plan's feedback log and deferred rather than silently swept into this slice.
  - why — The clamp is applied once at method entry and threaded to both the query and the model, so query and displayed page cannot diverge; the test pins both halves and fails against the old code. Merge after confirming the deferred VetController.java:61 twin gets its own slice.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**code-quality-reviewer**

- FIRST_PAGE named constant replaces a magic literal and documents intent, with a comment explaining why sub-1 pages are clamped rather than rejected
- Local variable currentPage is threaded consistently into both findPaginatedForOwnersLastName and addPaginationModel, avoiding a stale unclamped page reference
- Parameterized MockMvc test covers both boundary values (0 and -1), asserts the model's currentPage attribute and the zero-based Pageable page number via ArgumentCaptor, following the existing AssertJ/four-phase test style in the file
- ./gradlew checkFormat passes; no formatting violations introduced

**doc-reviewer**

- No docs/ update is required for this slice: docs/testing-principles.md's Maintenance Rules (doc-sync skill) call for a PRD update only when acceptance criteria were wrong, not merely silent on an edge case, and REQ-OWN-002's acceptance criteria ("listed a page at a time") is not contradicted by clamping an out-of-range page to the first page.
- No PRD or system-design.md drift: no existing Known Defects entry references this behavior, so none needs updating or removing.
- The added source comment in OwnerController.java is concise, behavioral, and under the sentence-length standard.
- Cross-reference and PRD-boundary checks pass: the change touches no docs/ files and introduces no mechanism into a doc.

**security-reviewer**

- Input normalization sits at the correct trust boundary:  Math.max(page, FIRST_PAGE)  runs in  OwnerController.processFindForm  before any value crosses into the data-access layer, and both downstream consumers ( findPaginatedForOwnersLastName ,  addPaginationModel ) receive the clamped  currentPage . No path in the method still reads the raw  page .
- Error-surface change is a net reduction, not an expansion. Previously a below-one  page  reached  PageRequest.of(page - 1, 5)  and surfaced as an unhandled  IllegalArgumentException  (HTTP 500 error page) driven purely by an attacker-supplied query parameter; the clamp converts that into a normal 200 first-page render. No exception message, stack frame, or internal type name is newly exposed to the client. Non-numeric  page  still fails binding to a 400 before controller entry, unchanged.
- Residual unbounded values on this path assessed and found non-exploitable. A very large  page  (up to  Integer.MAX_VALUE ) yields  PageRequest.of(page - 1, 5) , whose  getOffset()  widens to  long  before multiplying, so no integer overflow into a negative offset occurs; the query returns an empty page and the method takes the existing  ownersResults.isEmpty()  branch to  owners/findOwners . The remaining cost is a large-OFFSET scan, which is a resource-consumption concern rather than an access-control or integrity one, and it is unchanged by this diff.  Integer.MIN_VALUE  and  0  are absorbed by the clamp.
- No injection surface introduced.  currentPage  is a primitive  int  and reaches only  PageRequest  and the model;  lastName  continues to flow through the Spring Data derived query  findByLastNameStartingWith  as a bound parameter, matching the SQL-injection mitigation recorded in the system-design threat model. No string-concatenated SQL, no reflection, no deserialization, no file or process I/O in the diff.
- Rendered output stays safe.  currentPage  and  totalPages  are integers rendered by Thymeleaf with default escaping in  templates/owners/ownersList.html . Notably, that template feeds  currentPage  into Thymeleaf preprocessing blocks ( @{'/owners?page=__${currentPage - 1}__'} ); the clamp narrows the substituted value to the >= 1 integer range, so the change strictly reduces what an attacker can push into that preprocessing path rather than widening it.
- Class sweep for the same defect class (unvalidated numeric request parameter reaching persistence) across all of  src/main/java : the only other instance is  VetController.java:45 , explicitly carved out of this slice by the dispatch. Every remaining  @PathVariable  ( OwnerController  67/151/176,  PetController  68/76-77,  VisitController  64/98) is an entity identifier resolved through a repository lookup, not a pagination offset, and is untouched by this diff.
- Supply chain unaffected: the change set is exactly two source files ( scripts/changeset.sh --name-only ); no build script, dependency declaration, lockfile, or plugin coordinate changed, so no new third-party code or version enters the graph with this pass.
- No secrets introduced. Scanned both changed files for credential-shaped material (token, password, secret, key, connection strings, base64 blobs); the only added literals are the constant  FIRST_PAGE = 1  and the test's  page  values  0  and  -1 .
- Test file adds no security-relevant surface:  OwnerControllerTests  is test-scope only, drives the real MVC binding and dispatch through  MockMvc , and asserts the normalized value at both boundaries (model attribute  currentPage  = 1 and captured  Pageable.getPageNumber()  = 0), which pins the clamp against silent regression.

**test-reviewer**

- Test genuinely pins the fix: PageRequest.of(page-1, pageSize) throws IllegalArgumentException for page\<=0 before the clamp, so the test would fail (500 status) against the pre-fix controller — confirmed by reading findPaginatedForOwnersLastName
- Parameterized @ValueSource(ints={0,-1}) covers both documented failing inputs without copy-paste
- Assertions check both model-visible behavior (currentPage=1) and the actual repository call (zero-based page number via ArgumentCaptor), closing the gap between view state and query state
- Four-phase structure with blank-line separation, no phase comments, straight-line test body
- Test data naming is clean: pageBelowOne and firstPage are meaningful, role-describing names with no mystery literals
- ./gradlew test passes; no regression in the existing OwnerControllerTests suite
- VetController.java:61 identical defect correctly left out of scope per the dispatch instructions

**test-reviewer**

- Test method renamed to describe behavior (theOwnerSearchShouldTreatPageBelowOneAsFirstPage) instead of mirroring the production method name, resolving the prior autofix finding
- @ParameterizedTest with @ValueSource(ints = {0, -1}) correctly covers both boundary and below-boundary page values from the edge case
- Assertions use AssertJ (assertThat) and MockMvc result matchers appropriately; MockMvc is the sanctioned mock per the brief
- Test verifies both the model attribute and the underlying repository call argument, confirming the clamp-to-first-page behavior end-to-end

**doc-reviewer**

- Prior autofix finding resolved: the parameterized test at OwnerControllerTests.java:157 is now named theOwnerSearchShouldTreatPageBelowOneAsFirstPage, conforming to the the{Subject}Should{Outcome} school in docs/testing-principles.md § Test Naming; no residual implementation-mirroring test names on this surface.
- No docs/ files touched by the fix delta; PRD-boundary and cross-document coherence checks are unaffected and remain satisfied per the prior pass.
- The added source comment in OwnerController.java stays behavioral and within the sentence-length standard.

**code-quality-reviewer**

- Production code unchanged since prior approved pass; FIRST_PAGE constant and Math.max clamp remain clear and well-commented
- Test rename to theOwnerSearchShouldTreatPageBelowOneAsFirstPage reads as a clear BDD-style behavioral description, addressing the prior naming finding
- ./gradlew checkFormat passes clean

**security-reviewer**

- Fix delta since the approved first pass is a single test-method rename at OwnerControllerTests.java:157; no production code, no build/dependency files, and no configuration changed, so the first-pass approval stands unregressed
- Untrusted request parameter  page  is still clamped with Math.max(page, FIRST_PAGE) before reaching findPaginatedForOwnersLastName, preventing a negative page index from reaching PageRequest.of and turning attacker-controlled input into an unhandled 500
- Search input remains bound through Spring MVC type-safe binding and reaches the repository only via Spring Data derived query findByLastNameStartingWith with a Pageable — no string-concatenated JPQL/SQL, no injection surface added
- No secrets, credentials, or sensitive values introduced; grep over the changed production file for password/secret/token/api-key patterns is clean
- No new output rendering path: currentPage and totalPages are integers written to the model and rendered by Thymeleaf with default escaping, so no new XSS surface
- Supply chain unchanged — no build.gradle, lockfile, or plugin edits in the change set, so the dependency posture verified on the first pass is unaltered
- Test-only additions (ParameterizedTest, ArgumentCaptor) carry no production attack surface
- VetController.java:61 confirmed outside the change set and excluded from this review per dispatch scope

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `(parent)` | 1 | opus-5 | $3.50 | 17m 48s | 93% |
| `agent-team:feature-implementer` | 2 | opus-5 | $2.03 | 7m 32s | 93% |
| `agent-team:security-reviewer` | 2 | opus-5 | $1.60 | 2m 7s | 77% |
| `agent-team:change-grader` | 1 | opus-5 | $1.18 | 2m 22s | 88% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.93 | 1m 30s | 82% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.82 | 59s | 67% |
| `agent-team:test-reviewer` | 2 | sonnet-5 | $0.81 | 4m 10s | 81% |
| `agent-team:pipeline-coordinator` | 1 | sonnet-5 | $0.14 | 12s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $3.50 | 17m 48s | 93% |
| `agent-team:feature-implementer` | opus-5 | $1.32 | 5m 11s | 94% |
| `agent-team:change-grader` | opus-5 | $1.18 | 2m 22s | 88% |
| `agent-team:security-reviewer` | opus-5 | $0.93 | 1m 20s | 79% |
| `agent-team:feature-implementer` | opus-5 | $0.71 | 2m 20s | 91% |
| `agent-team:security-reviewer` | opus-5 | $0.67 | 47s | 74% |
| `agent-team:test-reviewer` | sonnet-5 | $0.57 | 3m 55s | 84% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.56 | 1m 13s | 87% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.48 | 38s | 62% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.37 | 17s | 70% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.35 | 20s | 72% |
| `agent-team:test-reviewer` | sonnet-5 | $0.24 | 15s | 69% |
| `agent-team:pipeline-coordinator` | sonnet-5 | $0.14 | 12s | 50% |

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
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `23a96bf93f32bf96` · `2.1.224 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
