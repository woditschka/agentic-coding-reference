# vets-specialty-filter r2 — v0.1.18

Filter the vet list by specialty (feature) · started 2026-08-07T21:19:17+00:00 · exec `claude-dev` · status **complete**

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
| 4 (±0) | 3 (±0) | 4 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.57. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> Filtering lands in the repository as derived queries (VetRepository.findBySpecialtiesNameIgnoreCase, paged and unpaged), keeping the match in the query and both surfaces on one matcher; the controller only binds and delegates, and vetList.html moves to @{/vets.html(page=..., specialty=${specialty})} so the parameter survives paging. Against that, normalizeSpecialty adds a blank-means-absent rule inside the controller — a fresh rule in a layer the catalog says holds none — and its null sentinel is duplicated in both handlers. Docs move together: NG-9 narrowed, REQ-VET-003 minted, REQ-VET-002 held withdrawn, ADR indexed, open question recorded. Tests are behavior-named but lean on Mockito interaction checks (then(vets).should(never())), narrate themselves with comments ("// the match is on the whole name"), and carry mystery literals (hasSize(2), value(2), PageRequest.of(0,5), 6).

**Sample 2** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> Repository gains two derived finders mirroring the existing paged/unpaged findAll pair, so matching happens in the query and both surfaces share one matcher — right layer, no duplication; the controller's normalizeSpecialty is a small new rule in a controller, which the checklist calls a fresh violation. Tests are BDD-named and cover filtering, case-insensitivity, non-prefix, unmatched, blank, and pagination carry-over, but they narrate what the code says ('// the match is on the whole name...'), assert implementation detail via then(vets).should(never()).findAll(...), and use bare literals ('radiology', 'rad', hasSize(2)) with no factories or named constants. Docs move together: NG-9 narrowed, REQ-VET-003 minted, REQ-VET-002 kept withdrawn, stale known-defect edge case deleted, ADR and index added, control question recorded.

**Sample 3** — design-fit 4 · test-quality 3 · maintainability 4 · doc-fit 5

> The repository seam is right:  findBySpecialtiesNameIgnoreCase  pushes whole-name matching into the query (VetRepository), and both surfaces share one matcher and one  normalizeSpecialty  helper rather than duplicating it. The blank-means-absent rule and the null-branch still sit in VetController, which the checklist's 'no new rule in a web controller' bar flags, and it widens the pyramid gap. Tests are BDD-named and cover paging, case, prefix, unmatched, and blank on both surfaces, but they assert implementation detail via  then(this.vets).should(never()).findAll(...) , carry narration comments ('// whole specialty name matched case-insensitively'), use bare literals  "radiology" / hasSize(2)  with no constants or factories, and pack two act/assert pairs into one test. Docs move together: ADR, ADR README, NG-9, REQ-VET-001, fresh REQ-VET-003, superseded entry, and the removed known-defect edge case; the open control question is recorded.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.80 | 36m | 30 | 88% | 8 file(s) +227/−20 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.73 | 4m 31s | 87% |

## Change

<details>
<summary>Diff (rendered from <code>change.patch</code>)</summary>

```diff
diff --git a/docs/adr/2026-08-07-non-goal-veterinarian-search.md b/docs/adr/2026-08-07-non-goal-veterinarian-search.md
new file mode 100644
index 0000000..e592fef
--- /dev/null
+++ b/docs/adr/2026-08-07-non-goal-veterinarian-search.md
@@ -0,0 +1,36 @@
+# Narrowing the Veterinarian-Search Non-Goal to Allow Specialty Filtering
+
+**Status:** Accepted
+
+## Context
+
+NG-9 declared search for pets, visits, and veterinarians out of scope, leaving only owners searchable. A product request on 2026-08-07 asked for the veterinarian directory to be narrowable to a single specialty on both the HTML page and a machine-readable surface. This sits against NG-9 and against REQ-VET-002, the machine-readable veterinarian list withdrawn on 2026-07-31 as an implementation artifact. The boundary between search (out) and filtering an already-shown attribute (requested) needed re-drawing, and the requirement ids needed settling.
+
+## Options Considered
+
+1. **Hold NG-9 whole** — refuse the filter as veterinarian search. Rejected: it conflates free-text search with narrowing by an attribute the directory already displays.
+2. **Drop NG-9 entirely** — treat all veterinarian search as in scope. Rejected: free-text veterinarian search still teaches nothing owner search does not.
+3. **Narrow NG-9** — keep free-text veterinarian search out, carve specialty filtering in. Chosen.
+
+## Decision
+
+Narrow NG-9: free-text search for pets, visits, and veterinarians stays a non-goal; narrowing the veterinarian directory by specialty — an attribute the directory already shows — is in scope.
+
+The HTML filter folds into REQ-VET-001: it refines the same surface's same list, has no product value without the directory it narrows, and does not warrant a separate id.
+
+The machine-readable surface is reinstated as first-class under a fresh id, REQ-VET-003, with the specialty filter as its first capability. REQ-VET-002 stays withdrawn and its id is not reused; REQ-VET-003 is a new requirement, not a revival.
+
+The filter is a URL contract on both surfaces. No visible page control ships in this request; a control is left as an open question.
+
+## Consequences
+
+The Non-Goals table, REQ-VET-001, the new REQ-VET-003, and the REQ-VET-002 Superseded entry move together, so the search/filter boundary reads consistently. A future free-text veterinarian search would still need its own decision. Adding a visible filter control remains open.
+
+## Implementation
+
+**Non-goal:** NG-9
+
+## References
+
+- [prd.md#req-vet-001](../prd.md#req-vet-001)
+- [prd.md#req-vet-003](../prd.md#req-vet-003)
diff --git a/docs/adr/README.md b/docs/adr/README.md
index a94dc3a..aa3b116 100644
--- a/docs/adr/README.md
+++ b/docs/adr/README.md
@@ -69,3 +69,4 @@ A non-goal ADR records a *product* decision not to build something — distinct
 | 2026-07-31 | [Feature-Package Organization Without a Service Layer](2026-07-31-feature-package-organization.md) | Accepted |
 | 2026-07-31 | [Database-Enforced Pet Name Uniqueness Within an Owner](2026-07-31-database-enforced-pet-name-uniqueness.md) | Accepted |
 | 2026-07-31 | [Dual Gradle and Maven Build Definitions](2026-07-31-dual-gradle-and-maven-builds.md) | Accepted |
+| 2026-08-07 | [Narrowing the Veterinarian-Search Non-Goal to Allow Specialty Filtering](2026-08-07-non-goal-veterinarian-search.md) | Accepted |
diff --git a/docs/prd.md b/docs/prd.md
index 0cb7f37..009d8b6 100644
--- a/docs/prd.md
+++ b/docs/prd.md
@@ -44,7 +44,7 @@ What the framing does not settle is whether each individual behavior was intende
 | NG-6 | Assigning a veterinarian to a visit, or any scheduling and availability | Scheduling is a domain of its own. Including it would make the sample about calendars rather than about the stack |
 | NG-7 | Billing, invoicing, and payment | A second bounded context, with money and its own correctness demands, in a sample sized to be read in one sitting |
 | NG-8 | Clinical records beyond a visit's one-line description | The description field demonstrates the association; richer clinical data would add domain depth without adding a pattern |
-| NG-9 | Searching for a pet, a visit, or a veterinarian — only owners are searchable | Owner search demonstrates paged prefix search once; repeating it for other entities would add surface, not understanding |
+| NG-9 | Free-text search for a pet, a visit, or a veterinarian — only owners are searchable by typed name. Narrowing the veterinarian directory to an attribute it already displays (specialty) is not search and is in scope — see `REQ-VET-001` and `REQ-VET-003` | Owner search demonstrates paged prefix search once; repeating free-text search for other entities would add surface, not understanding. Filtering an already-shown attribute is a different capability, narrowed in on 2026-08-07 — see [ADR](adr/2026-08-07-non-goal-veterinarian-search.md) |
 
 ## Requirements
 
@@ -117,18 +117,29 @@ A visit is booked against a particular pet and carries the date it is for and a
 ### Veterinarian directory
 
 <a id="req-vet-001"></a>
+<a id="req-vet-003"></a>
 
-The clinic publishes the veterinarians it employs with the specialties each holds, listed a page at a time. A veterinarian holding no specialty is shown as having none rather than left blank `[REQ-VET-001]`.
+The clinic publishes the veterinarians it employs with the specialties each holds, listed a page at a time. A veterinarian holding no specialty is shown as having none rather than left blank `[REQ-VET-001]`. The directory can optionally be narrowed to the veterinarians holding one named specialty. The name is matched in full and without regard to letter case — a partial name does not match, unlike owner search. Moving between pages keeps the narrowing applied, so a filtered directory stays navigable. A narrowing naming no held specialty yields the directory with no veterinarians rather than an error `[REQ-VET-001]`. A blank or all-spaces value is treated as no narrowing, matching the rule owner search uses.
+
+The same directory is also published in a machine-readable form for programmatic consumers, carrying the same veterinarians and specialties as the page `[REQ-VET-003]`. It accepts the same optional specialty narrowing with the same whole-name, case-insensitive matching `[REQ-VET-003]`. An unmatched value returns the document with no veterinarians rather than an error; a blank or all-spaces value is treated as no narrowing `[REQ-VET-003]`. Without a narrowing, both surfaces behave as they did before this capability.
 
 **Done when:**
 - `[REQ-VET-001]` given the clinic's veterinarians, when the directory is opened, then each name and its specialties are listed a page at a time.
 - `[REQ-VET-001]` given a veterinarian holding no specialty, when the directory is opened, then that veterinarian is shown as having none.
+- `[REQ-VET-001]` given a named specialty that some veterinarians hold, when the directory is narrowed to it, then only those veterinarians are listed and paging applies to that narrowed list.
+- `[REQ-VET-001]` given a narrowing whose name matches a held specialty only in letter case or only in part, when the directory is narrowed, then the case-differing name matches and the partial name does not.
+- `[REQ-VET-001]` given a narrowing naming no held specialty, when the directory is narrowed, then the directory is shown with no veterinarians and a normal, non-error response.
+- `[REQ-VET-001]` given a blank or all-spaces narrowing, when the directory is opened, then it behaves as though no narrowing were given.
+- `[REQ-VET-001]` given a filtered directory spanning more than one page, when a later page is opened, then the narrowing stays applied.
+- `[REQ-VET-003]` given the clinic's veterinarians, when the machine-readable directory is requested, then it carries the same veterinarians and specialties as the page.
+- `[REQ-VET-003]` given a named specialty that some veterinarians hold, when the machine-readable directory is narrowed to it, then only those veterinarians are returned, matched whole-name and case-insensitively.
+- `[REQ-VET-003]` given a narrowing naming no held specialty, when the machine-readable directory is requested, then it returns no veterinarians and a normal, non-error response.
+- `[REQ-VET-003]` given a blank or all-spaces narrowing, when the machine-readable directory is requested, then it behaves as though no narrowing were given.
 
 **Edge cases:**
 1. A veterinarian's specialties are presented in a stable order rather than an arbitrary one.
-2. **Known defect.** A second route returns the same list in a machine-readable form. Nothing consumes it, and it carries no requirement — see the Superseded list.
 
-**Design:** [system-design.md#contracts](system-design.md#contracts)
+**Design:** [system-design.md#contracts](system-design.md#contracts) · **ADR:** [ADR: Narrowing the veterinarian-search non-goal to allow specialty filtering](adr/2026-08-07-non-goal-veterinarian-search.md)
 
 ### Language
 
@@ -164,7 +175,7 @@ The system opens on a landing page, and every page carries navigation to the own
 
 <!-- Retired requirements: each ID maps to its successor (or to the reason it was withdrawn) so existing links still resolve. Keep this a list, so every retired ID stays in a list item. -->
 
-- `REQ-VET-002` (machine-readable veterinarian list) — **withdrawn 2026-07-31.** The endpoint exists but no consumer does, in this repository or any named client. It was derived from observed behavior and confirmed to be an implementation artifact, not a capability anyone asked for. No successor. The route remains in the code pending removal.
+- `REQ-VET-002` (machine-readable veterinarian list) — **withdrawn 2026-07-31; stays withdrawn.** As observed during the bootstrap survey the endpoint had no consumer, in this repository or any named client, and was confirmed to be an implementation artifact rather than a capability anyone asked for. On 2026-08-07 the machine-readable directory was requested as a first-class surface and is now specified fresh under `REQ-VET-003`; that is a new requirement, not a revival of `REQ-VET-002`, and `REQ-VET-002`'s id is not reused.
 
 ## Open Questions
 
@@ -173,7 +184,8 @@ The system opens on a landing page, and every page carries navigation to the own
 - ~~**Is this a demonstration or a product?**~~ **Answered 2026-07-31: a demonstration / reference sample.** Recorded in Context and G-1, and it supplies the framing reason across the Non-Goals table. It does not settle whether any individual behavior was intended.
 - ~~**Is the vocabulary right?**~~ **Answered 2026-07-31: correct as-is.** For a reference sample the codebase's own terms are canonical; there is no external domain expert to defer to. [`ubiquitous-language.md`](ubiquitous-language.md) is confirmed, and its recorded naming collisions stand.
 - ~~**Is owner search meant to be case-insensitive?**~~ **Answered 2026-07-31: yes.** Stated in `REQ-OWN-002`. The PostgreSQL schema stores the last name case-sensitively and is the defect — recorded as edge case 3 of Owner records.
-- ~~**Is `REQ-VET-002` a real requirement?**~~ **Answered 2026-07-31: no.** Withdrawn to the Superseded list as an implementation artifact.
+- ~~**Is `REQ-VET-002` a real requirement?**~~ **Answered 2026-07-31: no.** Withdrawn to the Superseded list as an implementation artifact. The machine-readable directory was later requested as a first-class surface (2026-08-07) and specified fresh under `REQ-VET-003`; `REQ-VET-002` stays withdrawn and its id is not reused.
+- **Should the veterinarian directory filter get a visible page control?** The specialty filter ships as a URL contract only (2026-08-07); neither surface gains a form, dropdown, or other control in this request. Whether to add a visible control on the directory page is deferred to a follow-up request.
 - ~~**Should the error page show technical failure detail to readers?**~~ **Answered 2026-07-31: no.** Stated in `REQ-SYS-002`; the current behavior is recorded as a defect.
 - ~~**Are two message keys dead vocabulary?**~~ **Answered 2026-07-31: yes.** The keys for a duplicate form submission and for a non-numeric value are produced by no code and are translated into all eleven languages. They are dead vocabulary pending removal.
 - **Is a visit really unrelated to a veterinarian?** Nothing connects the two, which makes the veterinarian directory a standalone page rather than part of the clinical workflow.
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/VetController.java b/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
index 867d0b5..0ac02a8 100644
--- a/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
+++ b/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
@@ -42,8 +42,12 @@ class VetController {
 	}
 
 	@GetMapping("/vets.html")
-	public String showVetList(@RequestParam(defaultValue = "1") int page, Model model) {
-		Page<Vet> paginated = findPaginated(page);
+	public String showVetList(@RequestParam(defaultValue = "1") int page,
+			@RequestParam(required = false) String specialty, Model model) {
+		String narrowing = normalizeSpecialty(specialty);
+		Page<Vet> paginated = findPaginated(page, narrowing);
+		// echo the normalized narrowing so vetList.html can carry it on every page link
+		model.addAttribute("specialty", narrowing);
 		return addPaginationModel(page, paginated, model);
 	}
 
@@ -56,19 +60,40 @@ class VetController {
 		return "vets/vetList";
 	}
 
-	private Page<Vet> findPaginated(int page) {
+	private Page<Vet> findPaginated(int page, String specialty) {
 		int pageSize = 5;
 		Pageable pageable = PageRequest.of(page - 1, pageSize);
-		return vetRepository.findAll(pageable);
+		if (specialty == null) {
+			return vetRepository.findAll(pageable);
+		}
+		return vetRepository.findBySpecialtiesNameIgnoreCase(specialty, pageable);
 	}
 
 	@GetMapping({ "/vets" })
-	public @ResponseBody Vets showResourcesVetList() {
+	public @ResponseBody Vets showResourcesVetList(@RequestParam(required = false) String specialty) {
 		// Here we are returning an object of type 'Vets' rather than a collection of Vet
 		// objects so it is simpler for JSon/Object mapping
 		Vets vets = new Vets();
-		vets.getVetList().addAll(this.vetRepository.findAll());
+		String narrowing = normalizeSpecialty(specialty);
+		if (narrowing == null) {
+			vets.getVetList().addAll(this.vetRepository.findAll());
+		}
+		else {
+			vets.getVetList().addAll(this.vetRepository.findBySpecialtiesNameIgnoreCase(narrowing));
+		}
 		return vets;
 	}
 
+	/**
+	 * Normalize the optional specialty narrowing: a null, blank, or all-spaces value
+	 * means no narrowing (mirrors {@code OwnerController.processFindForm}), signalled by
+	 * null; otherwise the stripped whole name to match.
+	 */
+	private String normalizeSpecialty(String specialty) {
+		if (specialty == null || specialty.isBlank()) {
+			return null;
+		}
+		return specialty.strip();
+	}
+
 }
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java b/src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java
index dbf68d0..ddd8629 100644
--- a/src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java
+++ b/src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java
@@ -55,4 +55,28 @@ public interface VetRepository extends Repository<Vet, Integer> {
 	@Cacheable("vets")
 	Page<Vet> findAll(Pageable pageable) throws DataAccessException;
 
+	/**
+	 * Retrieve the <code>Vet</code>s holding the named specialty, matched on the whole
+	 * specialty name case-insensitively (not a prefix). This is the shared matcher for
+	 * both vet directory surfaces; the join traverses the {@link Vet#getSpecialties()}
+	 * many-to-many so the match happens in the query rather than in memory.
+	 * @param name the whole specialty name to match, case-insensitively
+	 * @param pageable the requested page
+	 * @return a page of matching <code>Vet</code>s (empty when none hold the specialty)
+	 */
+	@Transactional(readOnly = true)
+	Page<Vet> findBySpecialtiesNameIgnoreCase(String name, Pageable pageable) throws DataAccessException;
+
+	/**
+	 * Retrieve the <code>Vet</code>s holding the named specialty, matched on the whole
+	 * specialty name case-insensitively (not a prefix). Unpaged companion to
+	 * {@link #findBySpecialtiesNameIgnoreCase(String, Pageable)} for the machine-readable
+	 * surface.
+	 * @param name the whole specialty name to match, case-insensitively
+	 * @return a <code>Collection</code> of matching <code>Vet</code>s (empty when none
+	 * hold the specialty)
+	 */
+	@Transactional(readOnly = true)
+	Collection<Vet> findBySpecialtiesNameIgnoreCase(String name) throws DataAccessException;
+
 }
diff --git a/src/main/resources/templates/vets/vetList.html b/src/main/resources/templates/vets/vetList.html
index e40fd65..87b74b4 100644
--- a/src/main/resources/templates/vets/vetList.html
+++ b/src/main/resources/templates/vets/vetList.html
@@ -27,28 +27,28 @@
     <span th:text="#{pages}">Pages:</span>
     <span>[</span>
     <span th:each="i: ${#numbers.sequence(1, totalPages)}">
-      <a th:if="${currentPage != i}" th:href="@{'/vets.html?page=__${i}__'}">[[${i}]]</a>
+      <a th:if="${currentPage != i}" th:href="@{/vets.html(page=${i}, specialty=${specialty})}">[[${i}]]</a>
       <span th:unless="${currentPage != i}">[[${i}]]</span>
     </span>
     <span>]&nbsp;</span>
     <span>
-      <a th:if="${currentPage > 1}" th:href="@{'/vets.html?page=1'}" th:title="#{first}"
+      <a th:if="${currentPage > 1}" th:href="@{/vets.html(page=1, specialty=${specialty})}" th:title="#{first}"
         class="fa fa-fast-backward"></a>
       <span th:unless="${currentPage > 1}" th:title="#{first}" class="fa fa-fast-backward"></span>
     </span>
     <span>
-      <a th:if="${currentPage > 1}" th:href="@{'/vets.html?page=__${currentPage - 1}__'}" th:title="#{previous}"
-        class="fa fa-step-backward"></a>
+      <a th:if="${currentPage > 1}" th:href="@{/vets.html(page=${currentPage - 1}, specialty=${specialty})}"
+        th:title="#{previous}" class="fa fa-step-backward"></a>
       <span th:unless="${currentPage > 1}" th:title="#{previous}" class="fa fa-step-backward"></span>
     </span>
     <span>
-      <a th:if="${currentPage < totalPages}" th:href="@{'/vets.html?page=__${currentPage + 1}__'}" th:title="#{next}"
-        class="fa fa-step-forward"></a>
+      <a th:if="${currentPage < totalPages}" th:href="@{/vets.html(page=${currentPage + 1}, specialty=${specialty})}"
+        th:title="#{next}" class="fa fa-step-forward"></a>
       <span th:unless="${currentPage < totalPages}" th:title="#{next}" class="fa fa-step-forward"></span>
     </span>
     <span>
-      <a th:if="${currentPage < totalPages}" th:href="@{'/vets.html?page=__${totalPages}__'}" th:title="#{last}"
-        class="fa fa-fast-forward"></a>
+      <a th:if="${currentPage < totalPages}" th:href="@{/vets.html(page=${totalPages}, specialty=${specialty})}"
+        th:title="#{last}" class="fa fa-fast-forward"></a>
       <span th:unless="${currentPage < totalPages}" th:title="#{last}" class="fa fa-fast-forward"></span>
     </span>
   </div>
diff --git a/src/test/java/org/springframework/samples/petclinic/service/ClinicServiceTests.java b/src/test/java/org/springframework/samples/petclinic/service/ClinicServiceTests.java
index 96f90df..3a325f2 100644
--- a/src/test/java/org/springframework/samples/petclinic/service/ClinicServiceTests.java
+++ b/src/test/java/org/springframework/samples/petclinic/service/ClinicServiceTests.java
@@ -214,6 +214,29 @@ class ClinicServiceTests {
 		assertThat(vet.getSpecialties().get(1).getName()).isEqualTo("surgery");
 	}
 
+	@Test
+	void theVetRepositoryShouldFindBySpecialtyWholeNameCaseInsensitively() {
+		Page<Vet> radiology = this.vets.findBySpecialtiesNameIgnoreCase("radiology", pageable);
+		assertThat(radiology).hasSize(2);
+
+		// whole specialty name matched case-insensitively
+		Page<Vet> upperCase = this.vets.findBySpecialtiesNameIgnoreCase("RADIOLOGY", pageable);
+		assertThat(upperCase).hasSize(2);
+	}
+
+	@Test
+	void theVetRepositoryShouldNotMatchSpecialtyByPrefix() {
+		// the match is on the whole name, so a prefix must not match
+		Page<Vet> prefix = this.vets.findBySpecialtiesNameIgnoreCase("rad", pageable);
+		assertThat(prefix).isEmpty();
+	}
+
+	@Test
+	void theVetRepositoryShouldReturnNoVetsForUnheldSpecialty() {
+		Page<Vet> unmatched = this.vets.findBySpecialtiesNameIgnoreCase("cardiology", pageable);
+		assertThat(unmatched).isEmpty();
+	}
+
 	@Test
 	@Transactional
 	void shouldAddNewVisitForPet() {
diff --git a/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java b/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
index 208758c..23381fe 100644
--- a/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
+++ b/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
@@ -23,6 +23,7 @@ import org.junit.jupiter.api.condition.DisabledInNativeImage;
 import org.springframework.beans.factory.annotation.Autowired;
 import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
 import org.springframework.data.domain.PageImpl;
+import org.springframework.data.domain.PageRequest;
 import org.springframework.data.domain.Pageable;
 import org.springframework.http.MediaType;
 import org.springframework.test.context.aot.DisabledInAotMode;
@@ -31,8 +32,15 @@ import org.springframework.test.web.servlet.MockMvc;
 import org.springframework.test.web.servlet.ResultActions;
 import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
 
+import java.util.Collections;
+
+import static org.hamcrest.Matchers.containsString;
+import static org.hamcrest.Matchers.hasSize;
 import static org.mockito.ArgumentMatchers.any;
+import static org.mockito.ArgumentMatchers.eq;
 import static org.mockito.BDDMockito.given;
+import static org.mockito.BDDMockito.then;
+import static org.mockito.Mockito.never;
 import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
 import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
 
@@ -97,4 +105,82 @@ class VetControllerTests {
 			.andExpect(jsonPath("$.vetList[0].id").value(1));
 	}
 
+	@Test
+	void theHtmlDirectoryNarrowedToSpecialtyShouldListOnlyMatchingVets() throws Exception {
+		given(this.vets.findBySpecialtiesNameIgnoreCase(eq("radiology"), any(Pageable.class)))
+			.willReturn(new PageImpl<Vet>(Lists.newArrayList(helen())));
+
+		mockMvc.perform(get("/vets.html?specialty=radiology"))
+			.andExpect(status().isOk())
+			.andExpect(model().attribute("specialty", "radiology"))
+			.andExpect(model().attribute("listVets", hasSize(1)))
+			.andExpect(view().name("vets/vetList"));
+
+		then(this.vets).should(never()).findAll(any(Pageable.class));
+	}
+
+	@Test
+	void theUnmatchedSpecialtyShouldYieldEmptyDirectoryWithNormalResponse() throws Exception {
+		given(this.vets.findBySpecialtiesNameIgnoreCase(eq("cardiology"), any(Pageable.class)))
+			.willReturn(new PageImpl<Vet>(Collections.emptyList()));
+
+		mockMvc.perform(get("/vets.html?specialty=cardiology"))
+			.andExpect(status().isOk())
+			.andExpect(model().attribute("listVets", hasSize(0)))
+			.andExpect(view().name("vets/vetList"));
+	}
+
+	@Test
+	void theBlankSpecialtyShouldBeTreatedAsNoNarrowing() throws Exception {
+		mockMvc.perform(get("/vets.html").param("specialty", "   "))
+			.andExpect(status().isOk())
+			.andExpect(model().attribute("specialty", (Object) null))
+			.andExpect(view().name("vets/vetList"));
+
+		then(this.vets).should().findAll(any(Pageable.class));
+		then(this.vets).should(never()).findBySpecialtiesNameIgnoreCase(any(String.class), any(Pageable.class));
+	}
+
+	@Test
+	void theLaterPageOfFilteredDirectoryShouldKeepNarrowing() throws Exception {
+		given(this.vets.findBySpecialtiesNameIgnoreCase(eq("radiology"), any(Pageable.class)))
+			.willReturn(new PageImpl<Vet>(Lists.newArrayList(helen()), PageRequest.of(0, 5), 6));
+
+		mockMvc.perform(get("/vets.html?specialty=radiology"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(containsString("specialty=radiology")));
+	}
+
+	@Test
+	void theMachineReadableDirectoryNarrowedToSpecialtyShouldReturnOnlyMatchingVets() throws Exception {
+		given(this.vets.findBySpecialtiesNameIgnoreCase("radiology")).willReturn(Lists.newArrayList(helen()));
+
+		mockMvc.perform(get("/vets?specialty=radiology").accept(MediaType.APPLICATION_JSON))
+			.andExpect(status().isOk())
+			.andExpect(content().contentType(MediaType.APPLICATION_JSON))
+			.andExpect(jsonPath("$.vetList.length()").value(1))
+			.andExpect(jsonPath("$.vetList[0].id").value(2));
+	}
+
+	@Test
+	void theMachineReadableUnmatchedSpecialtyShouldReturnEmptyDirectory() throws Exception {
+		given(this.vets.findBySpecialtiesNameIgnoreCase("cardiology")).willReturn(Collections.emptyList());
+
+		mockMvc.perform(get("/vets?specialty=cardiology").accept(MediaType.APPLICATION_JSON))
+			.andExpect(status().isOk())
+			.andExpect(content().contentType(MediaType.APPLICATION_JSON))
+			.andExpect(jsonPath("$.vetList.length()").value(0));
+	}
+
+	@Test
+	void theMachineReadableBlankSpecialtyShouldBeTreatedAsNoNarrowing() throws Exception {
+		mockMvc.perform(get("/vets").param("specialty", "   ").accept(MediaType.APPLICATION_JSON))
+			.andExpect(status().isOk())
+			.andExpect(content().contentType(MediaType.APPLICATION_JSON))
+			.andExpect(jsonPath("$.vetList.length()").value(2));
+
+		then(this.vets).should().findAll();
+		then(this.vets).should(never()).findBySpecialtiesNameIgnoreCase(any(String.class));
+	}
+
 }
```

</details>

## Pipeline

### REQ-VET-001 — Filter the veterinarian directory by specialty on both surfaces

3 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 | R3 |
| --- | --- | --- | --- |
| **code-quality** | **✖** (1) | **✔** | **✔** |
| **test** | ✎ (4) | · | **✔** |
| **security** | **✔** | **✔** | · |
| **doc** | ✎ (3) | **✔** | · |

- ◇ **prd-entry** Filter the veterinarian directory by specialty on both surfaces · (prd-expert) · ***◷ 0s***
- ◈ **design-block** **minor** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 45m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- ✔ **review security** · **approved** · ***◷ 15m***
- ✖ **review code-quality** · **blocked** · (1 finding) · ***◷ 15m***
  - [truncation] `ClinicServiceTests.java` Reviewer reached planned checkpoint after reviewing VetRepository.java and VetController.java. vetList.html and the two test files have not yet been reviewed. Findings above (none) cover VetRepository.java and VetController.java only.
- ✎ **review test** · **changes_requested** · (4 findings) · ***◷ 21h 45m***
  - **[blocked]** `VetControllerTests.java` REQ-VET-003 acceptance criterion 'given a blank or all-spaces narrowing, when the machine-readable directory is requested, then it behaves as though no narrowing were given' has no test. blankSpecialtyIsTreatedAsNoNarrowing covers only the HTML surface (/vets.html); the JSON surface (/vets) is untested for this case. The controller may or may not normalise the parameter consistently between both surfaces — the gap leaves a defect path open.
  - [autofix] `VetControllerTests.java:109,123,134,14` New test methods do not follow the BDD naming school required for tests written from 2026-07-31 onward (testing-principles.md § Test Naming: the{Subject}Should{Outcome}). Names like htmlDirectoryNarrowedToSpecialtyListsOnlyMatchingVets, unmatchedSpecialtyYieldsEmptyDirectoryWithNormalResponse, blankSpecialtyIsTreatedAsNoNarrowing, laterPageOfFilteredDirectoryKeepsNarrowing, machineReadableDirectoryNarrowedToSpecialtyReturnsOnlyMatchingVets, machineReadableUnmatchedSpecialtyReturnsEmptyDirectory describe what the system does rather than stating what must be true. Each should be renamed to the the{Subject}Should{Outcome} form, e.g. theHtmlDirectoryNarrowedToSpecialtyShouldListOnlyMatchingVets.
    - fix: Rename each new test method to follow the{Subject}Should{Outcome}: theHtmlDirectoryNarrowedToSpecialtyShouldListOnlyMatchingVets, theUnmatchedSpecialtyShouldYieldEmptyDirectoryWithNormalResponse, theBlankSpecialtyShouldBeTreatedAsNoNarrowing, theLaterPageOfFilteredDirectoryShouldKeepNarrowing, theMachineReadableDirectoryNarrowedToSpecialtyShouldReturnOnlyMatchingVets, theMachineReadableUnmatchedSpecialtyShouldReturnEmptyDirectory.
  - [autofix] `ClinicServiceTests.java:218,228,235` New test methods in ClinicServiceTests also do not follow the BDD naming school: shouldFindVetsBySpecialtyWholeNameCaseInsensitively, shouldNotMatchSpecialtyByPrefix, shouldReturnNoVetsForUnheldSpecialty start with 'should' but omit the 'the{Subject}' prefix. They should follow the the{Subject}Should{Outcome} form.
    - fix: Rename to theVetRepositoryShouldFindBySpecialtyWholeNameCaseInsensitively, theVetRepositoryShouldNotMatchSpecialtyByPrefix, theVetRepositoryShouldReturnNoVetsForUnheldSpecialty (or equivalent).
  - [autofix] `VetControllerTests.java:146-148` Narration comment inside laterPageOfFilteredDirectoryKeepsNarrowing violates testing-principles.md § Four-Phase Test Structure ('never add prose that restates what the code already says'). The comment 'six matches over a page size of five yields a second page whose links must carry the narrowing' narrates the intent already readable from the PageRequest.of(0, 5) and the 6-total constructor argument.
    - fix: Remove the comment block.
- ✎ **review doc** · **changes_requested** · (3 findings) · ***◷ 10m***
  - [autofix] `prd.md:119` The anchor for REQ-VET-003 is concatenated on the same line as the anchor for REQ-VET-001. The prd-authoring skill requires each anchor on its own line so deep-links resolve unambiguously.
    - fix: \<a id="req-vet-001">\</a> \<a id="req-vet-003">\</a>
  - [autofix] `prd.md:121` Sentence of 40 words exceeds the 30-word maximum: 'A narrowing that names no held specialty yields the directory with no veterinarians rather than an error, and a blank or all-spaces value is treated as no narrowing — the same emptiness rule owner search uses [REQ-VET-001].'
    - fix: A narrowing naming no held specialty yields the directory with no veterinarians rather than an error `[REQ-VET-001]`. A blank or all-spaces value is treated as no narrowing, matching the rule owner search uses.
  - [autofix] `prd.md:123` Sentence of 39 words exceeds the 30-word maximum: 'It accepts the same optional specialty narrowing, with the same whole-name, case-insensitive matching and the same treatment of an unmatched or blank value — an unmatched value returns the document with no veterinarians rather than an error [REQ-VET-003].'
    - fix: It accepts the same optional specialty narrowing with the same whole-name, case-insensitive matching `[REQ-VET-003]`. An unmatched value returns the document with no veterinarians rather than an error; a blank or all-spaces value is treated as no narrowing `[REQ-VET-003]`.
- ↻ **implement** (implementer) ← test · (4 findings)
- ↻ **fix prd-expert** ← doc · (3 findings)
- ✔ **review code-quality** · **approved**
- ▲ **build-pass** 22:20 · build, test, format, check, handoff-log, autofix-audit
- ✔ **review security** · **approved** · ***◷ 5m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 5m***
- ✔ **review test** · **approved** · ***◷ 15m***
- ◆ **grade CLEAR** · filter both vet directory surfaces by an optional specialty query parameter
  - blast_radius — **clear** — Contained to the vet feature: two prod Java files plus one template in the vet package, two test files, and three docs; two prod modules, no sensitive paths, 191 tracked insertions. Reach is narrow and read-only (public GET over already-public vet data).
  - semantic_surprise — **clear** — Read every hunk. normalizeSpecialty returns null on null/blank/all-spaces and strips otherwise; both handlers branch null to findAll, else to findBySpecialtiesNameIgnoreCase, with no inverted conditional or off-by-one. The template swap from the old string-concatenated page link to the Thymeleaf URL builder that appends specialty is a correct hardening, not a hidden behavior change; a null specialty is omitted from the link.
  - test_adequacy — **clear** — Tests assert real outcomes, not the implementation. H2 repository tests prove whole-name case-insensitivity (radiology and RADIOLOGY both size 2), prefix non-match (rad returns empty), and unheld-empty; controller tests cover filtered, unmatched, and blank on both HTML and JSON surfaces and assert the pagination link carries specialty=radiology. The round-1 critical JSON-blank gap was closed and re-verified.
  - reviewer_hedging — **clear** — Final round is a clean unanimous approval from all four reviewers with empty findings. The round-1 critical (untested JSON blank-narrowing) and the code-quality truncation were resolved and explicitly re-verified in round 2; the design-block was minor with no revisions. No lingering caveats or escalate tags remain.
  - scope_deviation — **clear** — Zero design revisions, consultations, and build retries. The diff matches the triaged surface exactly: optional specialty on both surfaces, one shared matcher, the parameter carried on every page link, URL-contract-only. The REQ-VET-001 plus REQ-VET-003 span is the designed scope, not a wander; the three product-owner decisions are recorded in docs.
  - why — All five facets clear on a direct read of every hunk: a contained, read-only vet-directory filter with a correct shared matcher, real boundary-covering tests, and a clean unanimous final approval. Confirm and merge. Note: the deterministic extractor could not run (a layout.toml gradle module-strategy versus a validator accepting only dir, maven, or first-segment-after, a harness version skew in scripts/ outside my write scope), so the structural row was hand-computed from the same worktree-vs-HEAD diff; it did not blind the semantic read.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- specialty flows only into Spring Data derived finders (findBySpecialtiesNameIgnoreCase) — bound-parameter queries, no SQLi surface
- pagination links use Thymeleaf URL-expression param syntax @{/vets.html(page=..., specialty=${specialty})}: query-param values are URL-encoded and th:href output HTML-attribute-escaped, so the reflected specialty cannot break out for XSS
- new finders are not @Cacheable (only @Transactional readOnly); attacker-controlled specialty values never enter the vets cache key-space, so no cache poisoning or unbounded-cache-growth path; blank/absent routes to the existing cached findAll unchanged
- read-only public GET over already-public vet/specialty data — no trust boundary or authz change; blank/all-spaces normalized to absent before reaching the query

**code-quality-reviewer**

- VetRepository: new derived finders follow Spring Data naming conventions exactly; Javadoc is accurate and explains the shared-matcher design rationale
- VetRepository: intentional omission of @Cacheable on filtered finders is correct — default key would differ from unfiltered key but filtering through the existing findAll methods for blank/absent preserves cached entries
- VetController: normalizeSpecialty private method is single-responsibility, well-commented, and consistent with OwnerController.processFindForm blank-as-absent pattern
- VetController: null-as-absent sentinel for narrowing is documented in the method Javadoc and in the inline comment on model.addAttribute; the why-comment is present
- VetController: constructor injection used correctly; no @Autowired
- checkFormat: spring-javaformat check passed clean

**test-reviewer**

- All seven new tests pass with zero failures
- vet package achieves 100% instruction and branch coverage; overall 89%, above the 80% target
- Case-insensitive whole-name match is exercised at the repository layer with both lowercase and uppercase inputs (shouldFindVetsBySpecialtyWholeNameCaseInsensitively)
- Partial-name non-match is covered in a dedicated test at the repository layer (shouldNotMatchSpecialtyByPrefix)
- Unmatched specialty yields HTTP 200 with empty list on both HTML and JSON surfaces
- Later-page pagination link carries the specialty parameter, verified with containsString
- No-narrowing path exercises the existing findAll paths, preserving prior behavior
- @MockitoBean usage for VetRepository in @WebMvcTest slice is the pre-existing pattern — the tolerance clause in testing-principles.md § Mocking Policy applies
- Factory methods james() and helen() satisfy the factory-method requirement for test data construction
- Four-phase structure is clear in new controller tests; MockMvc fluent chaining is standard for this layer

**doc-reviewer**

- NG-9 narrowing correctly scopes specialty filtering as in-scope while keeping free-text veterinarian search out
- REQ-VET-002 stays withdrawn and its id is not reused; REQ-VET-003 is introduced as a fresh requirement
- ADR Implementation section carries **Non-goal:** NG-9 satisfying the section-presence check
- ADR References link to both prd.md#req-vet-001 and prd.md#req-vet-003, both anchors exist in prd.md
- adr/README.md index row added for the new ADR with correct date, title, and status
- Done-when bullets in prd.md cover all seven acceptance criteria from the prd-entry record for both surfaces
- Superseded REQ-VET-002 entry reconciled with stays-withdrawn note and explicit statement that REQ-VET-003 is a new requirement
- Open Questions updated with the deferred visible page control, correctly distinguishing the URL-contract-only scope of this slice
- No prohibited PRD patterns introduced: no Java code, no mechanism tables, no per-requirement scaffolding, no internal code references
- Cross-document invariant satisfied: filter is URL-contract-only, stated in both non_goals and the open question

**code-quality-reviewer**

- VetRepository: new derived finders follow Spring Data naming conventions exactly; Javadoc explains the shared-matcher design rationale and the whole-name-not-prefix contract
- VetRepository: intentional omission of @Cacheable on filtered finders is correct — default key would differ from unfiltered key; blank/absent routes to existing cached findAll methods so unfiltered cache entries are preserved unchanged
- VetController: normalizeSpecialty private method is single-responsibility, well-documented, and consistent with OwnerController.processFindForm blank-as-absent pattern (grep-confirmed, IDE not consulted)
- VetController: null-as-absent sentinel for narrowing is documented in the method Javadoc and in the inline why-comment on model.addAttribute; constructor injection is correct with no @Autowired
- VetController: findPaginated branches correctly on null specialty; no null check on the paged return path required since the repository returns an empty Page rather than null
- vetList.html: specialty carried on all five pagination link types (numbered pages, first, prev, next, last); Thymeleaf URL builder omits null specialty parameter automatically, producing clean URLs when no filter is active — this is the correct resolution of the design-block risk about copying the owner template as-is
- VetControllerTests: factory methods james() and helen() produce fresh instances per call with meaningful names; @BeforeEach stubs only the unfiltered finders, forcing each filtered test to declare its own stub — clean separation
- VetControllerTests: blankSpecialtyIsTreatedAsNoNarrowing verifies both the positive path (findAll is called) and the negative path (filtered finder is never called), covering the routing branch fully
- VetControllerTests: laterPageOfFilteredDirectoryKeepsNarrowing sets up a two-page result and asserts the rendered HTML contains specialty=radiology, catching dropped-parameter regressions in the template
- ClinicServiceTests: shouldFindVetsBySpecialtyWholeNameCaseInsensitively and shouldNotMatchSpecialtyByPrefix together verify the whole-name case-insensitive requirement at the database level using Pageable.unpaged() consistent with the existing class field
- checkFormat: spring-javaformat check passed clean

**security-reviewer**

- Production sources (VetRepository.java, VetController.java, vetList.html) confirmed unchanged in content since round-1 approval — working-tree changes confined to test sources, docs/prd.md, and ADR docs; git status shows no other production paths
- Injection: findBySpecialtiesNameIgnoreCase is a Spring Data derived query — parameterized, no string concatenation of the specialty value into query text
- Reflected XSS: pagination links use the Thymeleaf @{/vets.html(page=..., specialty=${specialty})} URL-expression builder, which URL-encodes the query parameter and auto-escapes the attribute; the prior unsafe string-concatenation link form is gone
- Unbounded input: specialty is stripped and passed only to a parameterized query; no injection path (length is an out-of-scope DoS concern, not a security defect here)
- Cache poisoning / unbounded growth: filtered finders intentionally omit @Cacheable; attacker-controlled specialty never becomes a key on the @Cacheable("vets") surface

**doc-reviewer**

- Finding 1 resolved: anchors for REQ-VET-001 and REQ-VET-003 are now on separate lines (lines 119 and 120 of docs/prd.md)
- Finding 2 resolved: 40-word sentence split into two sentences of 16 words each; no word count violations in the result
- Finding 3 resolved: 39-word sentence split across two sentences (13 words and 23 words); the added closing sentence 'Without a narrowing, both surfaces behave as they did before this capability.' is 12 words; all under 30-word ceiling
- No new sentence-length violations introduced anywhere in the edited paragraph
- Requirement meaning preserved: NG-9 narrowing stays intact; blank-as-no-narrowing behavior retains its REQ-VET-001 Done-when bullet coverage even without an inline prose tag on the split sentence
- REQ-VET-002 Superseded entry correctly states stays-withdrawn, id-not-reused, and REQ-VET-003-is-new
- ADR references prd.md#req-vet-001 and prd.md#req-vet-003 — both anchors now resolve unambiguously on their own lines
- ADR Implementation section carries Non-goal: NG-9 satisfying the section-presence check
- ADR README index row for 2026-08-07 has correct title and Accepted status
- NG-9 table entry references REQ-VET-001, REQ-VET-003, and the ADR consistently with the PRD narrative
- Open Questions section records the deferred visible filter control, consistent with the ADR Consequences section
- URL-contract-only boundary is stated consistently across PRD narrative, Done-when bullets, NG-9, and ADR Decision

**code-quality-reviewer**

- checkFormat passed clean — spring-javaformat check green on both test files
- VetControllerTests: six renamed methods follow the the{Subject}Should{Outcome} BDD form and read unambiguously as specifications; pre-existing non-feature tests (showVetListHtml, showResourcesVetList) correctly left unrenamed
- VetControllerTests: new theMachineReadableBlankSpecialtyShouldBeTreatedAsNoNarrowing is symmetric to theBlankSpecialtyShouldBeTreatedAsNoNarrowing; blank line before the then() verification block respects four-phase structure; count assertion plus never-call verification is sufficient to prove routing correctness without over-specifying
- VetControllerTests: narration comment block removed from theLaterPageOfFilteredDirectoryShouldKeepNarrowing — no agent-addressed narration remains in the file
- ClinicServiceTests: three renamed repository tests follow the{Subject}Should{Outcome} form; inline why-comments on the case-insensitive and prefix-rejection tests are reader-facing explanations, not agent narration — correctly retained
- Production sources (VetController.java, VetRepository.java, vetList.html) confirmed unchanged from round-1 approval

**test-reviewer**

- Round-1 finding 1 resolved: theMachineReadableBlankSpecialtyShouldBeTreatedAsNoNarrowing present at VetControllerTests:176; drives /vets with all-spaces specialty, asserts HTTP 200, asserts vetList length 2, verifies findAll() is called and findBySpecialtiesNameIgnoreCase is never called
- Implementer claim verified: normalizeSpecialty() (VetController:92-97) converts blank/null to null; showResourcesVetList() (VetController:78) branches on null narrowing to findAll() — no separate controller fix was needed
- Round-1 finding 2 resolved: six VetControllerTests specialty tests renamed to the{Subject}Should{Outcome} form — theHtmlDirectoryNarrowedToSpecialtyShouldListOnlyMatchingVets, theUnmatchedSpecialtyShouldYieldEmptyDirectoryWithNormalResponse, theBlankSpecialtyShouldBeTreatedAsNoNarrowing, theLaterPageOfFilteredDirectoryShouldKeepNarrowing, theMachineReadableDirectoryNarrowedToSpecialtyShouldReturnOnlyMatchingVets, theMachineReadableUnmatchedSpecialtyShouldReturnEmptyDirectory
- Round-1 finding 3 resolved: three ClinicServiceTests renames applied — theVetRepositoryShouldFindBySpecialtyWholeNameCaseInsensitively, theVetRepositoryShouldNotMatchSpecialtyByPrefix, theVetRepositoryShouldReturnNoVetsForUnheldSpecialty
- Round-1 finding 4 resolved: narration comment removed from theLaterPageOfFilteredDirectoryShouldKeepNarrowing
- Slice contract: filtered HTML (theHtmlDirectoryNarrowedToSpecialtyShouldListOnlyMatchingVets), filtered JSON (theMachineReadableDirectoryNarrowedToSpecialtyShouldReturnOnlyMatchingVets), case-insensitive whole-name match (theVetRepositoryShouldFindBySpecialtyWholeNameCaseInsensitively), partial-name non-match (theVetRepositoryShouldNotMatchSpecialtyByPrefix), unmatched-200-empty on HTML (theUnmatchedSpecialtyShouldYieldEmptyDirectoryWithNormalResponse), unmatched-200-empty on JSON (theMachineReadableUnmatchedSpecialtyShouldReturnEmptyDirectory), blank-as-absent on HTML (theBlankSpecialtyShouldBeTreatedAsNoNarrowing), blank-as-absent on JSON (theMachineReadableBlankSpecialtyShouldBeTreatedAsNoNarrowing), no-parameter unchanged on both surfaces (showVetListHtml, showResourcesVetList), pagination links carry parameter (theLaterPageOfFilteredDirectoryShouldKeepNarrowing) — all criteria satisfied
- Four-phase structure: blank line separates response assertions from interaction verifications in both blank-specialty tests; no narration comments in any new or renamed test
- Test data construction: james() and helen() factory methods produce fresh instances per call; new test theMachineReadableBlankSpecialtyShouldBeTreatedAsNoNarrowing relies on @BeforeEach stub for findAll() producing the expected two-item list, consistent with jsonPath vetList.length() assertion value 2
- All tests pass: ./gradlew test BUILD SUCCESSFUL; jacocoTestReport ran clean

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $8.26 | 15m 1s | 94% |
| `(parent)` | 1 | opus-5 | $4.04 | 40m 19s | 94% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $3.92 | 6m 3s | 81% |
| `spring-boot-claude:system-design-expert` | 1 | opus-4-8 | $3.35 | 2m 47s | 72% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $2.73 | 4m 31s | 87% |
| `spring-boot-claude:security-reviewer` | 2 | opus-4-8 | $2.50 | 1m 47s | 79% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $1.93 | 6m 17s | 85% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $1.68 | 7m 1s | 82% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $1.61 | 9m 58s | 86% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.23 | 39s | 46% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-4-8 | $5.76 | 11m 41s | 95% |
| `(parent)` | opus-5 | $4.04 | 40m 19s | 94% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $3.35 | 2m 47s | 72% |
| `spring-boot-claude:change-grader` | opus-4-8 | $2.73 | 4m 31s | 87% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $2.50 | 3m 20s | 89% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $2.35 | 4m 31s | 82% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.57 | 1m 32s | 81% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $1.34 | 1m 1s | 82% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $1.16 | 46s | 74% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $1.02 | 3m 49s | 88% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $1.00 | 7m 40s | 85% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.96 | 4m 47s | 84% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.92 | 2m 27s | 81% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.71 | 2m 13s | 81% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.61 | 2m 17s | 87% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.23 | 39s | 46% |

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

- plugin `spring-boot-claude` at `v0.1.18` (tag)
- model requested `claude-opus-5`; models used: opus-4-8 · opus-5 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `064d588523591361` · `2.1.224 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
