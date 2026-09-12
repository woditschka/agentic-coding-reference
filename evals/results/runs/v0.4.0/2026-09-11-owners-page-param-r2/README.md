# owners-page-param r2 — v0.4.0

Owner listing crashes on page values below 1 (bugfix) · started 2026-09-11T19:56:55+00:00 · exec `claude-dev` · status **complete**

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
| reading depth (pipeline grade) | scrutinize |

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
| 5 (±0) | 4 (±1) | 5 (±0) | 4 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.48. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 5 · test-quality 4 · maintainability 5 · doc-fit 4

> The fix clamps once at handler entry ( int pageToShow = Math.max(page, FIRST_PAGE) ). The query, redirect and  addPaginationModel  all share the clamped value, which is the controller-level normalization the testing principles assign to the web layer. The why-comment about  Integer.MIN_VALUE  overflow earns its place. The tests use BDD names ( theOwnerListShouldShowTheFirstPageForAPageBelowOne ), anonymous factories ( anOwner ,  someOwners ) and derived expectations ( SEVERAL_PAGES * OWNER_LIST_PAGE_SIZE ). They lose a point for leaning on Mockito stubs where the principles prefer hand-written doubles, and for repeating bare view-name literals. The PRD, system-design contract table, ADR and index all move. However, the edited provenance note still says "ten further questions stay open" in the same patch that adds a new Open Question, so that count is likely stale.

**Sample 2** — design-fit 5 · test-quality 4 · maintainability 5 · doc-fit 4

> The fix clamps once, at handler entry, with  Math.max(page, FIRST_PAGE) , and  pageToShow  feeds both the query and  addPaginationModel . The testing principles assign request normalization to the web controller, so this is the right layer. The comment is justified because it explains the Integer.MIN_VALUE overflow. The tests use BDD names ( theOwnerListShouldShowTheFirstPageForAPageBelowOne ) and parameterized sources, including MIN_VALUE. They use named constants and  anOwner / someOwners  factories, and have no phase comments. Minor issues: view-name literals like "owners/ownersList" repeat, the second test asserts only the view, and the new tests rely on Mockito stubs. On docs, the PRD, the system-design contract row and the indexed ADR are all updated. But the PRD still says "ten further questions stay open" while adding another Open Question, so that count is likely stale.

**Sample 3** — design-fit 5 · test-quality 5 · maintainability 5 · doc-fit 4

> The fix is a single  Math.max(page, FIRST_PAGE)  at handler entry in  OwnerController .  pageToShow  then feeds the query, the redirect path and  addPaginationModel . This is request binding at the web layer, which testing-principles assigns to the controller. The comment explains a real overflow risk, not obvious logic. Test names follow  the{Subject}Should{Outcome} . Data sits behind factories ( anOwner ,  someOwners ,  firstPageOf ), values are named ( SEVERAL_PAGES ,  SEARCHED_LAST_NAME ), and  totalPages  is derived from inputs. Labelled  argumentSet  cases read as specifications. The PRD, system-design contract row, ADR index and open questions are all updated. One stale claim remains: the PRD still says "ten further questions stay open" after the patch adds another open-question bullet.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $8.41 | 23m | 4 | 91% | 6 file(s) +141/−6 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.59 | 1m 40s | 82% |

## Change

<details>
<summary>Diff (rendered from <code>change.patch</code>)</summary>

```diff
diff --git a/docs/adr/2026-09-11-request-parameter-normalization-is-request-binding.md b/docs/adr/2026-09-11-request-parameter-normalization-is-request-binding.md
new file mode 100644
index 0000000..0d8e39e
--- /dev/null
+++ b/docs/adr/2026-09-11-request-parameter-normalization-is-request-binding.md
@@ -0,0 +1,43 @@
+# Request-Parameter Normalization Is Request Binding
+
+**Status:** Accepted
+
+## Context
+
+`REQ-OWN-005` answers an owner-list page numbered below 1 as the first page. The *Web controller* row of the pattern catalog admits no business rule in a controller. The recorded controller-rule breach does not extend to new rules.
+
+The first review of the fix read the page clamp in `OwnerController` as a new business rule. The catalog names no other seam, and no service layer sits between controller and repository. Without a recorded classification, every paging or sorting fix re-opens the same placement question. The veterinarian list builds its page index the same way and would face it next.
+
+## Options Considered
+
+1. **Normalize in the controller at handler entry** — the controller maps the bound parameter into the range the repository's paging accepts, as part of binding the request.
+2. **A page-number value object** — an immutable type owning the clamp, unit-testable. It models a transport concern as a domain type the ubiquitous language does not contain, and adds a public name for one comparison.
+3. **A static normalizer outside the controller** — no catalog pattern fits it. It moves a boundary check away from the boundary it guards.
+4. **Framework pageable resolution** — the framework's paging argument resolver with one-based parameters. It moves the answer into global configuration and changes the handler signature. It also changes non-numeric handling, which the PRD leaves open.
+
+## Decision
+
+We use option 1. Mapping a request parameter into the range its delegate accepts is request binding under the *Web controller* row, not a business rule.
+
+Two conditions bound the classification. The PRD states the answer for the out-of-range value. The mapping reads the request alone, never clinic records. Where the PRD is silent, the value is rejected at the boundary, per [security-principles.md § Trust Boundaries](../security-principles.md#trust-boundaries).
+
+A page number describes the listing's transport shape, not the clinic's records. The security brief places range handling of external input at the boundary, and code past the boundary trusts its contracts. A check against clinic records — a duplicate name, a birth or visit date, a record's existence — remains a business rule. A new one in a controller is still a fresh violation.
+
+## Consequences
+
+- The check sits at the boundary it guards. The query, the single-match redirect, and the rendered current page share one normalized value.
+- A later paging fix takes the same placement without a new ADR, provided the PRD states the answer. The veterinarian list and a page past the last are the likely cases.
+- The normalization is tested through the web test harness, not a unit test. [testing-principles.md § Test Pyramid](../testing-principles.md#test-pyramid) already assigns web-level tests to controller normalization.
+- A reviewer must apply the two conditions to tell binding from a rule. A mapping that reads domain state fails them and is a business rule.
+
+## Implementation
+
+**Requirements:** REQ-OWN-005
+
+- `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` — the owner search handler normalizes the page at entry.
+
+## References
+
+- [system-design.md § Package Structure](../system-design.md#package-structure) — the current-state rule and the recorded controller-rule breach
+- [architecture-principles.md § Pattern Catalog](../architecture-principles.md#pattern-catalog) — the *Web controller* row
+- [Feature-Package Organization Without a Service Layer](2026-07-31-feature-package-organization.md) — the organization that leaves the controller as the only seam
diff --git a/docs/adr/README.md b/docs/adr/README.md
index 04c6442..641b2e5 100644
--- a/docs/adr/README.md
+++ b/docs/adr/README.md
@@ -70,3 +70,4 @@ A non-goal ADR records a *product* decision not to build something — distinct
 | 2026-07-31 | [Database-Enforced Pet Name Uniqueness Within an Owner](2026-07-31-database-enforced-pet-name-uniqueness.md) | Accepted |
 | 2026-07-31 | [Dual Gradle and Maven Build Definitions](2026-07-31-dual-gradle-and-maven-builds.md) | Accepted |
 | 2026-08-08 | [Deleting Records and Amending Booked Visits Are Deliberately Out of Scope](2026-08-08-non-goal-deletion-and-visit-amendment.md) | Accepted |
+| 2026-09-11 | [Request-Parameter Normalization Is Request Binding](2026-09-11-request-parameter-normalization-is-request-binding.md) | Accepted |
diff --git a/docs/prd.md b/docs/prd.md
index 06398de..e77aad3 100644
--- a/docs/prd.md
+++ b/docs/prd.md
@@ -7,7 +7,7 @@
 
 > **Provenance: derived from observed behavior, largely unconfirmed.** Every requirement in this document was reconstructed from the running system's boundary surface during a bootstrap survey — not from any statement of intent. **Observed behavior is not an intended requirement.** Each item may be a deliberate requirement, an accident of implementation, or a shipped bug, and the code cannot tell which.
 >
-> One thing has since been confirmed: this is a demonstration rather than a product (2026-07-31), which settles the Context and Non-Goals framing. Every individual requirement remains provisional, and ten further questions stay open — see [Open Questions](#open-questions).
+> One thing has since been confirmed: this is a demonstration rather than a product (2026-07-31), which settles the Context and Non-Goals framing. Every individual requirement remains provisional, and ten further questions stay open — see [Open Questions](#open-questions). `REQ-OWN-005` is the exception: the owner stated it directly (2026-09-11), so it is not derived.
 
 ## Context
 
@@ -50,9 +50,9 @@ What the framing does not settle is whether each individual behavior was intende
 
 ### Owner records
 
-<a id="req-own-001"></a><a id="req-own-002"></a><a id="req-own-003"></a><a id="req-own-004"></a>
+<a id="req-own-001"></a><a id="req-own-002"></a><a id="req-own-003"></a><a id="req-own-004"></a><a id="req-own-005"></a>
 
-The clinic records each owner it deals with, holding the person's name, where they live, and a telephone number to reach them on `[REQ-OWN-001]`. Staff find an owner by last name, matching the beginning of the name and disregarding letter case. A partial name is enough, and searching for nothing brings back every owner `[REQ-OWN-002]`. An owner's record shows their contact details, every pet they own, and every visit each pet has made. One page answers "what has happened with this household" `[REQ-OWN-003]`. Contact details can be corrected at any time `[REQ-OWN-004]`.
+The clinic records each owner it deals with, holding the person's name, where they live, and a telephone number to reach them on `[REQ-OWN-001]`. Staff find an owner by last name, matching the beginning of the name and disregarding letter case. A partial name is enough, and searching for nothing brings back every owner `[REQ-OWN-002]`. A request for a page numbered below 1 is answered as the first page of the owner list, never with the error page (confirmed 2026-09-11) `[REQ-OWN-005]`. An owner's record shows their contact details, every pet they own, and every visit each pet has made. One page answers "what has happened with this household" `[REQ-OWN-003]`. Contact details can be corrected at any time `[REQ-OWN-004]`.
 
 **Done when:**
 - `[REQ-OWN-001]` given a new owner with every detail supplied, when it is submitted, then the owner is recorded and their record is shown.
@@ -64,6 +64,8 @@ The clinic records each owner it deals with, holding the person's name, where th
 - `[REQ-OWN-002]` given an empty search, when it runs, then every owner is listed.
 - `[REQ-OWN-002]` given a search with leading or trailing spaces, when it runs, then the result matches the same search without them.
 - `[REQ-OWN-002]` given a last name differing from the stored name only by letter case, when the search runs, then it matches.
+- `[REQ-OWN-005]` given several pages of owners, when the owner list is requested at a page numbered below 1, then the first page is shown, not the error page.
+- `[REQ-OWN-005]` given any search, when it runs at a page numbered below 1, then the result is the same as that search on the first page.
 - `[REQ-OWN-003]` given an existing owner, when their record is opened, then their contact details are shown.
 - `[REQ-OWN-003]` given an owner with pets, when their record is opened, then each pet is shown with its type and birth date, and each pet's visits with date and description.
 - `[REQ-OWN-004]` given an existing owner, when a detail is changed and validation passes, then the record is updated and the change is confirmed.
@@ -72,6 +74,7 @@ The clinic records each owner it deals with, holding the person's name, where th
 1. A search whose text is entirely spaces behaves as an empty search and returns every owner.
 2. A request for an owner that does not exist is refused rather than showing an empty record.
 3. **Known defect.** Case-insensitive matching holds under H2 and MySQL but not under PostgreSQL, whose schema stores the last name case-sensitively. The PostgreSQL schema is the defect; the requirement is the bar.
+4. A page number far below 1, down to the lowest a request can carry, is also answered as the first page.
 
 **Design:** [system-design.md#contracts](system-design.md#contracts)
 
@@ -179,3 +182,4 @@ The system opens on a landing page, and every page carries navigation to the own
 - **Is a visit really unrelated to a veterinarian?** Nothing connects the two, which makes the veterinarian directory a standalone page rather than part of the clinical workflow.
 - **Are the seeded pet types and specialties the real lists,** or placeholders?
 - **Does the project hold goals beyond being a reference sample?** G-2 is unfilled.
+- **What should the owner list show for a page past the last one, or a page that is not a number?** `REQ-OWN-005` settles only pages numbered below 1.
diff --git a/docs/system-design.md b/docs/system-design.md
index 9d58a3a..e9832b4 100644
--- a/docs/system-design.md
+++ b/docs/system-design.md
@@ -58,6 +58,8 @@ The mutable-entity gap is **resolved by a scoped exception**, granted 2026-07-31
 
 Two gaps remain, and the exception covers **neither**. No modularity test enforces the package boundaries, so the acyclic dependency graph holds by fact rather than by construction. Business rules sit in controllers rather than in an independently testable core. That breaches the *Web controller* row of the pattern catalog, which admits no business rule. [testing-principles.md](testing-principles.md#test-pyramid) records the same gap as the reason the test-shape target is not met. Both are listed under [Open Questions from the Survey](#open-questions-from-the-survey).
 
+**Request normalization is binding, not a business rule** ([ADR](adr/2026-09-11-request-parameter-normalization-is-request-binding.md)). Mapping a request parameter into the range its delegate accepts is request binding under the *Web controller* row. It qualifies only when the PRD states the answer for the out-of-range value and the mapping reads the request alone. Where the PRD is silent, the value is rejected at the boundary, per [security-principles.md](security-principles.md#trust-boundaries). A check against clinic records, such as a duplicate name or a visit date, remains a business rule. `OwnerController` normalizes an owner-list page below 1 to the first page, once, at handler entry `[REQ-OWN-005]`. The query, the single-match redirect, and the rendered current page all use the normalized value. The controller-rule breach recorded above does not cover this normalization, and this normalization does not widen that breach.
+
 ## Constants
 
 <!-- Name each constant and cite the source file that owns its value; do not copy the value (source is authoritative). -->
@@ -92,7 +94,7 @@ An `Implements` value of `—` marks a contract serving no single requirement. T
 | `Visit` | Persisted appointment record against a pet; defaults its date forward on construction | `src/main/java/org/springframework/samples/petclinic/owner/Visit.java` | REQ-VIS-001 |
 | `OwnerRepository` | Spring Data JPA repository for owners; the sole write path for the owner–pet–visit graph. Supports prefix search by last name with paging | `src/main/java/org/springframework/samples/petclinic/owner/OwnerRepository.java` | REQ-OWN-001, REQ-OWN-002, REQ-OWN-003, REQ-OWN-004, REQ-PET-001, REQ-VIS-001 |
 | `PetTypeRepository` | Spring Data JPA repository for pet types, returning them in name order | `src/main/java/org/springframework/samples/petclinic/owner/PetTypeRepository.java` | REQ-PET-001 |
-| `OwnerController` | Server-rendered owner workflows: create, edit, search with paging, and detail | `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` | REQ-OWN-001, REQ-OWN-002, REQ-OWN-003, REQ-OWN-004 |
+| `OwnerController` | Server-rendered owner workflows: create, edit, search with paging, and detail | `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` | REQ-OWN-001, REQ-OWN-002, REQ-OWN-003, REQ-OWN-004, REQ-OWN-005 |
 | `PetController` | Server-rendered pet workflows nested under an owner: create and edit, including duplicate-name and future-birth-date rejection | `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` | REQ-PET-001, REQ-PET-002, REQ-PET-003, REQ-PET-004 |
 | `VisitController` | Server-rendered visit booking for a pet, rejecting non-future dates | `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` | REQ-VIS-001, REQ-VIS-002 |
 | `PetTypeFormatter` | Spring MVC formatter translating between a pet type and its display name during form binding | `src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java` | REQ-PET-001 |
diff --git a/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java b/src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java
index b4b6145..4467535 100644
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
+		// Clamp before any arithmetic: the zero-based conversion below would overflow
+		// for Integer.MIN_VALUE, and the rendered current page must match the query.
+		int pageToShow = Math.max(page, FIRST_PAGE);
+
 		// allow parameterless GET request for /owners to return all records
 		String lastName = owner.getLastName();
 		if (lastName == null) {
@@ -104,7 +110,7 @@ class OwnerController {
 		}
 
 		// find owners by last name
-		Page<Owner> ownersResults = findPaginatedForOwnersLastName(page, lastName);
+		Page<Owner> ownersResults = findPaginatedForOwnersLastName(pageToShow, lastName);
 		if (ownersResults.isEmpty()) {
 			// no owners found
 			result.rejectValue("lastName", "notFound", "not found");
@@ -118,7 +124,7 @@ class OwnerController {
 		}
 
 		// multiple owners found
-		return addPaginationModel(page, model, ownersResults);
+		return addPaginationModel(pageToShow, model, ownersResults);
 	}
 
 	private String addPaginationModel(int page, Model model, Page<Owner> paginated) {
diff --git a/src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java b/src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java
index dd379a5..a776da6 100644
--- a/src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java
+++ b/src/test/java/org/springframework/samples/petclinic/owner/OwnerControllerTests.java
@@ -19,10 +19,15 @@ package org.springframework.samples.petclinic.owner;
 import org.junit.jupiter.api.BeforeEach;
 import org.junit.jupiter.api.Test;
 import org.junit.jupiter.api.condition.DisabledInNativeImage;
+import org.junit.jupiter.params.ParameterizedTest;
+import org.junit.jupiter.params.provider.Arguments;
+import org.junit.jupiter.params.provider.MethodSource;
+import org.junit.jupiter.params.provider.ValueSource;
 import org.springframework.beans.factory.annotation.Autowired;
 import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
 import org.springframework.data.domain.Page;
 import org.springframework.data.domain.PageImpl;
+import org.springframework.data.domain.PageRequest;
 import org.springframework.data.domain.Pageable;
 import org.springframework.test.context.aot.DisabledInAotMode;
 import org.springframework.test.context.bean.override.mockito.MockitoBean;
@@ -32,6 +37,8 @@ import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
 import java.time.LocalDate;
 import java.util.List;
 import java.util.Optional;
+import java.util.concurrent.atomic.AtomicInteger;
+import java.util.stream.Stream;
 
 import static org.hamcrest.Matchers.empty;
 import static org.hamcrest.Matchers.greaterThan;
@@ -40,6 +47,7 @@ import static org.hamcrest.Matchers.hasProperty;
 import static org.hamcrest.Matchers.hasSize;
 import static org.hamcrest.Matchers.is;
 import static org.hamcrest.Matchers.not;
+import static org.junit.jupiter.params.provider.Arguments.argumentSet;
 import static org.mockito.ArgumentMatchers.any;
 import static org.mockito.ArgumentMatchers.anyString;
 import static org.mockito.ArgumentMatchers.eq;
@@ -64,6 +72,22 @@ class OwnerControllerTests {
 
 	private static final int TEST_OWNER_ID = 1;
 
+	private static final int OWNER_LIST_PAGE_SIZE = 5;
+
+	private static final int FIRST_PAGE_NUMBER = 1;
+
+	private static final Pageable FIRST_PAGE_REQUEST = PageRequest.of(FIRST_PAGE_NUMBER - 1, OWNER_LIST_PAGE_SIZE);
+
+	private static final int SEVERAL_PAGES = 3;
+
+	private static final String UNFILTERED_SEARCH = "";
+
+	private static final String SEARCHED_LAST_NAME = "Davis";
+
+	private static final String PAGE_BELOW_ONE = "0";
+
+	private static final AtomicInteger GENERATED_OWNER_IDS = new AtomicInteger(TEST_OWNER_ID);
+
 	@Autowired
 	private MockMvc mockMvc;
 
@@ -89,6 +113,24 @@ class OwnerControllerTests {
 		return george;
 	}
 
+	private static Owner anOwner() {
+		Owner owner = new Owner();
+		owner.setId(GENERATED_OWNER_IDS.incrementAndGet());
+		return owner;
+	}
+
+	private static List<Owner> someOwners(int count) {
+		return Stream.generate(OwnerControllerTests::anOwner).limit(count).toList();
+	}
+
+	private static Page<Owner> firstPageOf(List<Owner> matches, long totalMatches) {
+		return new PageImpl<>(matches, FIRST_PAGE_REQUEST, totalMatches);
+	}
+
+	private static Page<Owner> onlyPageOf(List<Owner> matches) {
+		return firstPageOf(matches, matches.size());
+	}
+
 	@BeforeEach
 	void setup() {
 
@@ -195,6 +237,43 @@ class OwnerControllerTests {
 
 	}
 
+	@ParameterizedTest
+	@ValueSource(ints = { 0, -1, Integer.MIN_VALUE })
+	void theOwnerListShouldShowTheFirstPageForAPageBelowOne(int pageBelowOne) throws Exception {
+		List<Owner> firstPageOwners = someOwners(OWNER_LIST_PAGE_SIZE);
+		given(this.owners.findByLastNameStartingWith(eq(UNFILTERED_SEARCH), eq(FIRST_PAGE_REQUEST)))
+			.willReturn(firstPageOf(firstPageOwners, SEVERAL_PAGES * OWNER_LIST_PAGE_SIZE));
+
+		mockMvc.perform(get("/owners").param("page", String.valueOf(pageBelowOne)))
+			.andExpect(status().isOk())
+			.andExpect(view().name("owners/ownersList"))
+			.andExpect(model().attribute("currentPage", FIRST_PAGE_NUMBER))
+			.andExpect(model().attribute("totalPages", SEVERAL_PAGES))
+			.andExpect(model().attribute("listOwners", firstPageOwners));
+	}
+
+	@ParameterizedTest
+	@MethodSource("searchOutcomesOnTheFirstPage")
+	void theOwnerSearchShouldAnswerAPageBelowOneAsTheFirstPage(Page<Owner> firstPageOfMatches, String expectedView)
+			throws Exception {
+		given(this.owners.findByLastNameStartingWith(eq(SEARCHED_LAST_NAME), eq(FIRST_PAGE_REQUEST)))
+			.willReturn(firstPageOfMatches);
+
+		mockMvc.perform(get("/owners").param("page", PAGE_BELOW_ONE).param("lastName", SEARCHED_LAST_NAME))
+			.andExpect(view().name(expectedView));
+	}
+
+	static Stream<Arguments> searchOutcomesOnTheFirstPage() {
+		Owner onlyMatch = anOwner();
+		return Stream.of(
+				argumentSet("one match opens that owner's record", onlyPageOf(List.of(onlyMatch)),
+						"redirect:/owners/" + onlyMatch.getId()),
+				argumentSet("several matches list the first page",
+						firstPageOf(someOwners(OWNER_LIST_PAGE_SIZE), SEVERAL_PAGES * OWNER_LIST_PAGE_SIZE),
+						"owners/ownersList"),
+				argumentSet("no match reports that no owner was found", onlyPageOf(List.of()), "owners/findOwners"));
+	}
+
 	@Test
 	void initUpdateOwnerForm() throws Exception {
 		mockMvc.perform(get("/owners/{ownerId}/edit", TEST_OWNER_ID))
```

</details>

## Pipeline

### REQ-OWN-005 — Owner list answers a page below 1 with the first page

2 review rounds · 2 build-passes · grade **SCRUTINIZE**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (1) | **✔** |
| **test** | **✔** | · |
| **security** | · | · |
| **doc** | **✔** | **✔** |

- • intake-decision (human)
- ◇ **prd-entry** Owner list answers a page below 1 with the first page · (prd-expert) · ***◷ 2m***
- ◈ **design-block** **covered** · (design) · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 6m***
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- • review-plan (review-planner)
- ✔ **review test** · **approved** · ***◷ 1m***
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 1m***
  - [clarify] `OwnerController.java:96-101` processFindForm now clamps `page` to FIRST_PAGE with `Math.max(page, FIRST_PAGE)` — this is the new REQ-OWN-005 business rule (page-below-1 answered as page 1), and it lands directly in the controller method body. docs/architecture-principles.md's Web controller catalog row (line 85) states a controller 'Holds no business rule', and its own review checklist (line 144) reads: 'No business rule added to a web controller — the Web controller row is the bar, and the existing deviation does not extend to new rules... A new rule added to a controller is a fresh violation, not covered by the existing one.' The existing page-1-to-zero-index conversion in `findPaginatedForOwnersLastName` is the recorded pre-existing deviation; clamping a below-1 page to 1 is new logic, not a continuation of that conversion. Neither the catalog nor architecture-principles.md names an alternative seam for this rule in a codebase with no service layer between OwnerController and OwnerRepository, so per code-quality-review's own routing rule this is a placement question for the system-design-expert rather than a fix I can prescribe: should the clamp move to a small value type/static helper (e.g., a page-number normalizer) outside the controller, or does the recorded controller deviation need to be extended to cover this rule explicitly in system-design.md?
- ✔ **review doc** · **approved** · ***◷ 1m***
- ↻ **implement** (implementer) ← code-quality · (1 finding) · ***◷ 4m***
  - ↳ consult → **design** · Does the page-below-1 clamp stay in OwnerController.processFindForm as request binding (boundary range normalization under the Web controller row), as the line-5 design-block states? Or should it move to a seam outside the controller, such as a small immutable page-number value type or static normalizer, and if so, which catalog pattern and package does that type take? If it stays, should durable memory (docs/system-design.md or architecture-principles.md) state explicitly that boundary range normalization of a bound parameter counts as binding and not as a business rule, so the next review does not re-raise this?
  - ↲ consult ← **design** · Keep the clamp where it is. Math.max(page, FIRST_PAGE) at the top of OwnerController.processFindForm is request binding under the Web controller row, not a business rule, and the line-5 design-block stands unchanged. No code change this round: re-run the gate and re-invoke code-quality-reviewer with this answer. Classification (now durable memory): mapping a request parameter into the range its delegate accepts counts as binding when two conditions hold. (1) The PRD states the answer for the out-of-range value; REQ-OWN-005 does for a page below 1. (2) The mapping reads the request alone, never clinic records. Where the PRD is silent, the boundary rejects the value (security-principles.md § Trust Boundaries: validate range before use, reject what the contract does not allow; checks belong at the boundary, not in the core). A check against clinic records (duplicate pet name, birth or visit date, whether a record exists) stays a business rule, and a new one in a controller is still a fresh violation. The reviewer's reading of the checklist is right for that class. The page clamp falls outside it. Alternatives rejected: a page-number value object would put a transport concern into the domain as a type the ubiquitous language does not contain, and it would add a public name for one comparison (architecture-principles.md Design Principles 2 and 5). A static normalizer matches no catalog pattern and moves the check away from the boundary it guards. The framework's Pageable resolver would change binding globally, change the handler signature, and change non-numeric handling, which the PRD leaves open. testing-principles.md § Test Pyramid already names normalization as a web-controller duty tested at the web level. It says extracting such a rule for a unit test is placement drift, so the existing MockMvc tests are the correct tests. On your third question: yes, and it is now recorded. docs/system-design.md § Package Structure carries the classification as a current-state rule with REQ-OWN-005, backed by a new ADR. That supplies the system-design.md assignment testing-principles.md line 54 already assumed. Cite both in the re-review.
  - ▲ **build ✓ clean** · build · test · check · format · handoff-log · autofix-audit · contracts-sync
- • review-plan (review-plan-engine)
- ✔ **review code-quality** · **approved** · ***◷ 35s***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ◆ **grade SCRUTINIZE** · answer owner-list pages below 1 as the first page
  - blast_radius — **skim** — One production file changes by ten lines, all inside the OwnerController.processFindForm handler. No sensitive or security-surface paths are touched, VetController's identical page - 1 construction is left alone, and the remaining files are tests and docs.
  - semantic_surprise — **skim** — Math.max(page, FIRST_PAGE) at OwnerController.java:101 runs before the page - 1 subtraction at :141, so Integer.MIN_VALUE cannot wrap. For any page of 1 or more it returns the same value, so existing behavior holds. The query, the single-match redirect, the not-found branch and currentPage all receive the clamped value. Non-numeric pages (still a 400) and pages past the last are unchanged, as the non-goals require.
  - test_adequacy — **skim** — The repository stub matches PageRequest.of(0, 5) exactly rather than any(Pageable), so an unclamped controller throws or misses the stub. The list test covers 0, -1 and Integer.MIN_VALUE and asserts currentPage 1, totalPages and the full owner list. The search test covers the redirect, list and not-found outcomes, though it asserts only the view name. The implementer reports the tests failed on the pre-fix code.
  - reviewer_hedging — **scrutinize** — The final approvals are unanimous across the planned roster, and security-reviewer was scoped out by the plan, so its silence is expected. But code-quality's round-1 consistent-with-codebase clarify was not settled by changing code. It was settled by a classification rule the design expert wrote during the fix round, and the re-approval rests on that rule. doc-reviewer's approval also notes a gap in the architecture-principles.md Web controller row that it left for the human to close. One citation is slightly off: the approval puts Math.max at line 99, but it is at line 101.
  - scope_deviation — **scrutinize** — The code stays within the triaged surface. The docs do not: the design-block named the Contracts row as the only design write, but one consultation added a new Accepted ADR and a general policy paragraph to system-design.md Package Structure. That paragraph classifies request-parameter normalization as binding and lets later paging fixes skip a new ADR, which is durable architecture policy beyond a bug fix.
  - why — The code is a safe, well-tested one-line clamp placed before the subtraction, so a glance confirms it. Before merging, read the new ADR and the system-design.md paragraph. They were written during the fix round to settle a reviewer's placement objection, they set a precedent for future controller normalization, and they leave the architecture-principles.md clause open for you.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**test-reviewer**

- Placement matches design-block assignment: the page clamp is boundary normalization (system-design.md OwnerController row), and both new tests exercise it through @WebMvcTest/MockMvc rather than widening a lower seam for framework reach (src/test/.../OwnerControllerTests.java:240-274)
- Mocking follows the design-block's sanctioned exception: @MockitoBean OwnerRepository stubbed with eq(FIRST_PAGE_REQUEST) (PageRequest.of(0,5)) rather than any(Pageable), proving the controller normalized to page 1 before querying (OwnerControllerTests.java:78,244-246,262-264)
- Data construction follows testing-principles.md Three-Tier Convention and Factory Methods: anOwner()/someOwners()/firstPageOf()/onlyPageOf() factories, named constants (OWNER_LIST_PAGE_SIZE, FIRST_PAGE_NUMBER, SEARCHED_LAST_NAME, PAGE_BELOW_ONE), no bare literals; OWNER_LIST_PAGE_SIZE=5 matches the production pageSize at OwnerController.java:140 (verified by grep)
- Naming follows the BDD school (testing-principles.md Test Naming): theOwnerListShouldShowTheFirstPageForAPageBelowOne, theOwnerSearchShouldAnswerAPageBelowOneAsTheFirstPage
- python3 scripts/grading.py coverage-map --feature REQ-OWN-005 shows both Done-when bullets and edge case 4 (page far below 1, down to Integer.MIN_VALUE) covered by the two declared tests
- Integer.MIN_VALUE case included per the design-block's overflow risk (Math.max applied before the page-1 subtraction), verified by ./gradlew test passing clean with the new parameterized cases
- Redirect-case assertion (view name only, no status) matches the existing suite's convention at OwnerControllerTests.java:199,210 for the single-match redirect — consistent-with-codebase, not a gap
- Four-phase structure, whole-object model assertions (listOwners compared to the full generated list), and derived expectations (redirect URL built from the generated owner id, totalPages implied by SEVERAL_PAGES*OWNER_LIST_PAGE_SIZE) all hold

**code-quality-reviewer**

- FIRST_PAGE constant and the clamp comment explain the overflow reasoning (why, not what) without narrating requirement IDs
- Math.max(page, FIRST_PAGE) avoids the Integer.MIN_VALUE overflow that a page-1 subtraction would hit, verified by reading findPaginatedForOwnersLastName at OwnerController.java:139-142
- Clamped value (pageToShow) is threaded consistently into both the query call and the currentPage model attribute, so the rendered page matches the query
- No stray second instance of the new clamp rule elsewhere: grep -F -e 'Math.max' -e 'FIRST_PAGE' across src/main confirms VetController.java is untouched, consistent with the non-goal
- checkFormat passed with no formatting violations
- No new/coined vocabulary; docs/ubiquitous-language.md has no 'page' entry to diverge from and PRD acceptance bullets match the shipped behavior with no scope creep

**doc-reviewer**

- docs/prd.md:53,55,67-68,185 — REQ-OWN-005 anchor, narrative clause, Done-when bullets, and Open Question use behavioral language with no code/type/language-specific references (checked against prd-authoring/boundary-rules.md Prohibited Patterns table)
- docs/prd.md:74 edge case 4 states the Integer.MIN_VALUE boundary behaviorally ('the lowest a request can carry') without naming a Java type, respecting the PRD what/how boundary
- docs/prd.md:10 provenance note correctly marks REQ-OWN-005 as owner-stated (2026-09-11) rather than derived, matching the intake-decision record
- docs/system-design.md:95 OwnerController Contracts row Implements cell now cites REQ-OWN-005, satisfying the row-fidelity coherence check; no other system-design.md section was touched, matching the design-block's stated scope
- docs/prd.md:76 Design link resolves to a valid docs/system-design.md#contracts anchor (## Contracts heading at system-design.md:72)
- Every requirement ID added to system-design.md (REQ-OWN-005) exists in docs/prd.md, and no deprecated requirement ID appears
- New source constant OwnerController.FIRST_PAGE is single-file-scoped like the existing undocumented view-name constants, so its absence from the Constants table is consistent with that section's stated documentation policy (system-design.md:70), not a gap
- No new domain term was introduced that requires a docs/ubiquitous-language.md entry ('page'/'first page' are generic pagination vocabulary, not redefined domain terms)

**code-quality-reviewer**

- The round-1 clarify finding (line 15) on OwnerController.java:96-101 is resolved: the system-design-expert's consultation-response (line 20) classifies the page clamp as request binding, not a business rule, under a two-condition test (PRD states the out-of-range answer; the mapping reads the request alone, never clinic records)
- The classification is now durable memory in docs/system-design.md § Package Structure (line 61) and docs/adr/2026-09-11-request-parameter-normalization-is-request-binding.md (Accepted), which follows the same Status/Context/Options/Decision/Consequences/Implementation/References shape as the existing ADRs (verified against docs/adr/2026-07-31-feature-package-organization.md)
- docs/adr/README.md index row added in the existing table format, dated and linked correctly
- OwnerController.java:96-101 (read this round, unchanged from round 1) matches the ADR/system-design description exactly: Math.max(page, FIRST_PAGE) at handler entry, threaded to the query, redirect, and currentPage model attribute; no requirement id or handoff vocabulary in the code comment
- This round's diff (base-tree 0ee704617102e143d24173c3c4b0831a4942fb17) touches only docs/adr/2026-09-11-request-parameter-normalization-is-request-binding.md, docs/adr/README.md, and docs/system-design.md — no production or test code changed, so no new code-quality surface to review
- ./gradlew checkFormat passes clean

**doc-reviewer**

- docs/adr/2026-09-11-request-parameter-normalization-is-request-binding.md follows the README template exactly: Status, Context, Options Considered (4, with trade-offs), Decision, Consequences, Implementation (**Requirements:** REQ-OWN-005), References — 43 lines, under the 60-line guideline
- Filename matches YYYY-MM-DD-title-in-kebab-case.md convention (adr-template skill) and is owned by system-design-expert per the non-goal-infix ownership split (no non-goal- prefix, standard ADR)
- docs/adr/README.md:73 index row added with correct date, title-linked filename, and Accepted status, matching the file's own Status field
- All three References/cross-references in the new ADR resolve: system-design.md#package-structure (system-design.md:26), architecture-principles.md#pattern-catalog (architecture-principles.md:74), and the sibling 2026-07-31-feature-package-organization.md file, verified present on disk
- docs/system-design.md:61 new paragraph links the ADR, states the two-condition classification (PRD states the out-of-range answer; mapping reads the request alone), and cites security-principles.md#trust-boundaries (security-principles.md:6) and REQ-OWN-005, which exists in docs/prd.md:53
- No struct-field or parameter table added; no literal constant value copied — the new system-design.md paragraph and the ADR describe behavior only, verified by re-reading system-design.md:61 against the self-test (a field rename or constant change in OwnerController would not invalidate the claim)
- New paragraph's claim that OwnerController normalizes the page 'once, at handler entry' and threads it to the query and the rendered current page is accurate against src/main/java/.../OwnerController.java:96-124 (Math.max at line 99, pageToShow passed to findPaginatedForOwnersLastName and addPaginationModel)
- docs/architecture-principles.md's Web controller row ('binds the request ... Holds no business rule', line 85) is not contradicted: the new classification interprets binding to include boundary range normalization under the stated two conditions, and does not edit architecture-principles.md itself (correctly left to the human per the design expert's out-of-write-scope note)
- No new domain term requiring a docs/ubiquitous-language.md entry; grep confirms no 'page' vocabulary entry exists to diverge from
- No prohibited words (simply/easily/obviously/just/very/leverage/utilize), no second-person address, and no sentence over 30 words in the new ADR or the new system-design.md paragraph (checked by word-count script over every sentence)
- docs/prd.md is unchanged since the round-1 approval (line 16) — confirmed via changeset diff against the fix-delta basis tree, so that approval still holds and needed no re-review

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `agent-team:feature-implementer` | 3 | opus-5 | $2.40 | 8m 43s | 91% |
| `agent-team:system-design-expert` | 2 | opus-5 | $1.85 | 4m 21s | 87% |
| `(parent)` | 1 | opus-5 | $1.46 | 24m 2s | 96% |
| `agent-team:product-requirements-expert` | 1 | opus-5 | $0.94 | 2m 44s | 90% |
| `agent-team:doc-reviewer` | 2 | sonnet-5 | $0.72 | 3m 14s | 93% |
| `agent-team:change-grader` | 1 | opus-5 | $0.59 | 1m 40s | 82% |
| `agent-team:code-quality-reviewer` | 2 | sonnet-5 | $0.58 | 2m 24s | 92% |
| `agent-team:test-reviewer` | 1 | sonnet-5 | $0.26 | 1m 11s | 82% |
| `agent-team:review-planner` | 1 | sonnet-5 | $0.14 | 18s | 81% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `agent-team:feature-implementer` | opus-5 | $1.47 | 6m 42s | 92% |
| `(parent)` | opus-5 | $1.46 | 24m 2s | 96% |
| `agent-team:system-design-expert` | opus-5 | $1.13 | 2m 36s | 89% |
| `agent-team:product-requirements-expert` | opus-5 | $0.94 | 2m 44s | 90% |
| `agent-team:system-design-expert` | opus-5 | $0.73 | 1m 45s | 83% |
| `agent-team:change-grader` | opus-5 | $0.59 | 1m 40s | 82% |
| `agent-team:feature-implementer` | opus-5 | $0.57 | 1m 5s | 91% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.41 | 1m 35s | 94% |
| `agent-team:feature-implementer` | opus-5 | $0.36 | 55s | 81% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.31 | 1m 26s | 91% |
| `agent-team:doc-reviewer` | sonnet-5 | $0.31 | 1m 38s | 91% |
| `agent-team:code-quality-reviewer` | sonnet-5 | $0.26 | 58s | 93% |
| `agent-team:test-reviewer` | sonnet-5 | $0.26 | 1m 11s | 82% |
| `agent-team:review-planner` | sonnet-5 | $0.14 | 18s | 81% |

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
- task fingerprint `f9cab5f4787e5bda` · `2.1.268 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
