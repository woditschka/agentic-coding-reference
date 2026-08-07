# specialty-directory r3 — v0.1.1

Specialty directory page (feature) · started 2026-08-06T14:52:37+00:00 · exec `claude-dev` · status **timeout**

## Prompt

> Feature request: the vet list answers "which specialties does this vet hold",
> but staff also ask the inverse — "which vets hold this specialty". One
> product decision comes with it, made here as the product owner: a read-only
> specialty view of the existing directory is in scope; managing veterinarians
> or specialties stays out of scope as before (non-goal NG-2 is unchanged).
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

## Verdict

| check | result |
|---|---|
| oracle | ✔ 4/4 passed |
| suite (post-agent) | ✔ |
| suite (pristine baseline) | ✔ |
| checkpoints | 6/7 |
| review attention (pipeline grade) | — |

- ✔ `theSpecialtyDirectoryShouldListEverySeededSpecialty` — passed
- ✔ `theSpecialtyDirectoryShouldNameTheVetsHoldingEachSpecialty` — passed
- ✔ `theSpecialtyDirectoryShouldRender` — passed
- ✔ `theVetDirectoryShouldRenderTheSeededVets` — passed

## Checkpoints

The kind's graded ladder, derived from the recorded facts — context only, outside the quality bar (bench README § Checkpoints).

- ✘ `agent complete`
- ✔ `change produced`
- ✔ `suite green`
- ✔ `theSpecialtyDirectoryShouldListEverySeededSpecialty`
- ✔ `theSpecialtyDirectoryShouldNameTheVetsHoldingEachSpecialty`
- ✔ `theSpecialtyDirectoryShouldRender`
- ✔ `theVetDirectoryShouldRenderTheSeededVets`

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 2 (±0) | 3 (±0) | 3 (±0) | 4 (±0) |

Median (spread) over 2 sample(s) (3 requested) · rubric `rubric-v1.md` · `claude-opus-5` · $0.46. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 2 · test-quality 3 · maintainability 3 · doc-fit 4

> buildSpecialtyDirectory() puts the whole inversion rule — grouping, full-name formatting, ordering — inside VetController, which the catalog's Web controller row forbids and which the brief explicitly says is 'a fresh violation, not covered by the existing one'; a stateless domain service (Available, not currently used) fits, and the /specialties.html surface arguably belongs in its own Controller rather than bolted onto VetController. The nested SpecialtyDirectoryEntry record leaks to tests. holdersBySpecialtyId.get(specialty.getId()).add(vet) NPEs for any specialty not returned by findSpecialties, and the manual sort duplicates the query's ORDER BY. Tests are behavior-named and use factories, but rely on Mockito stubs, raw literals ("radiology", "Helen Leary"), substring HTML matching, narration comments, and no unit-level test.

**Sample 2** — design-fit 2 · test-quality 3 · maintainability 3 · doc-fit 4

> VetController.buildSpecialtyDirectory embeds the whole inversion rule — seeding entries, filing vets, full-name formatting, dual ordering — in a web controller, a fresh violation of the 'no business rule in a controller' bar when the sanctioned Domain service pattern was available without an ADR; the logic is also unit-testable but every test boots MockMvc. It re-sorts a list the @Query already orders by name, and holdersBySpecialtyId.get(...).add(vet) NPEs on any specialty absent from findSpecialties(). The template's #{specialties} key ships with no message bundle. Tests are well named and factory-built, but narrate setup in comments ('// The mock returns...'), assert order via raw HTML substrings, and prove 'one page' only by attributeDoesNotExist("totalPages"). PRD and contracts table are updated.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| ? | 127m | None | 83% | 6 file(s) +211/−8 |

## Change

<details>
<summary>Diff (rendered from <code>change.patch</code>)</summary>

```diff
diff --git a/docs/prd.md b/docs/prd.md
index 0cb7f37..ed379be 100644
--- a/docs/prd.md
+++ b/docs/prd.md
@@ -120,13 +120,24 @@ A visit is booked against a particular pet and carries the date it is for and a
 
 The clinic publishes the veterinarians it employs with the specialties each holds, listed a page at a time. A veterinarian holding no specialty is shown as having none rather than left blank `[REQ-VET-001]`.
 
+<a id="req-vet-003"></a>
+
+The directory reads the other way too. A specialty directory answers "which veterinarians hold this specialty", the inverse of the veterinarian view (`[REQ-VET-001]`). It lists every specialty the clinic knows, each by its stored name. Under each specialty it shows the holding veterinarians, each by full name with the first name before the last name (for example "Helen Leary"). A specialty that no veterinarian holds is still listed, with no veterinarian beneath it. The page indexes specialties, not veterinarians: a veterinarian holding no specialty appears under no specialty and so does not appear on the page at all. Every specialty is shown on a single page, with no paging `[REQ-VET-003]`.
+
 **Done when:**
 - `[REQ-VET-001]` given the clinic's veterinarians, when the directory is opened, then each name and its specialties are listed a page at a time.
 - `[REQ-VET-001]` given a veterinarian holding no specialty, when the directory is opened, then that veterinarian is shown as having none.
+- `[REQ-VET-003]` given the clinic's specialties, when the specialty directory is opened, then every specialty is listed by its stored name.
+- `[REQ-VET-003]` given a specialty held by one or more veterinarians, when the specialty directory is opened, then each holding veterinarian is shown by full name with the first name before the last name.
+- `[REQ-VET-003]` given a specialty that no veterinarian holds, when the specialty directory is opened, then that specialty is still listed with no veterinarian beneath it.
+- `[REQ-VET-003]` given a veterinarian holding no specialty, when the specialty directory is opened, then that veterinarian does not appear on the page.
+- `[REQ-VET-003]` given the clinic's specialties, when the specialty directory is opened, then all of them appear on a single page with no paging.
 
 **Edge cases:**
 1. A veterinarian's specialties are presented in a stable order rather than an arbitrary one.
 2. **Known defect.** A second route returns the same list in a machine-readable form. Nothing consumes it, and it carries no requirement — see the Superseded list.
+3. The specialties, and the veterinarians beneath each, are presented in a stable order rather than an arbitrary one.
+4. The specialty directory reads the existing records only; it neither adds, changes, nor removes a veterinarian or a specialty (NG-2).
 
 **Design:** [system-design.md#contracts](system-design.md#contracts)
 
diff --git a/docs/system-design.md b/docs/system-design.md
index 9d58a3a..23d8287 100644
--- a/docs/system-design.md
+++ b/docs/system-design.md
@@ -98,10 +98,11 @@ An `Implements` value of `—` marks a contract serving no single requirement. T
 | `PetTypeFormatter` | Spring MVC formatter translating between a pet type and its display name during form binding | `src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java` | REQ-PET-001 |
 | `PetValidator` | Spring `Validator` enforcing the required-field rules for pet forms that bean validation does not cover | `src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java` | REQ-PET-001 |
 | `Vet` | Persisted veterinarian; exposes specialties sorted by name | `src/main/java/org/springframework/samples/petclinic/vet/Vet.java` | REQ-VET-001 |
-| `Specialty` | Persisted lookup value naming a veterinary specialty | `src/main/java/org/springframework/samples/petclinic/vet/Specialty.java` | REQ-VET-001 |
+| `Specialty` | Persisted lookup value naming a veterinary specialty | `src/main/java/org/springframework/samples/petclinic/vet/Specialty.java` | REQ-VET-001, REQ-VET-003 |
 | `Vets` | Serialization wrapper giving the vet collection a single root element for the non-HTML representation | `src/main/java/org/springframework/samples/petclinic/vet/Vets.java` | — |
 | `VetRepository` | Spring Data repository for veterinarians; results are cached | `src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java` | REQ-VET-001 |
-| `VetController` | Serves the paged HTML vet list and a serialized vet collection from a second route | `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` | REQ-VET-001 |
+| `SpecialtyRepository` | Spring Data repository for specialties, returning all of them in name order | `src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java` | REQ-VET-003 |
+| `VetController` | Serves the paged HTML vet list, a serialized vet collection from a second route, and the single-page specialty directory that inverts the vet→specialty view into specialty→holding-vets | `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` | REQ-VET-001, REQ-VET-003 |
 | `CacheConfiguration` | Enables caching and declares the vet cache through the JCache API | `src/main/java/org/springframework/samples/petclinic/system/CacheConfiguration.java` | REQ-VET-001 |
 | `WebConfiguration` | Session-scoped locale resolution plus a request-parameter locale switch | `src/main/java/org/springframework/samples/petclinic/system/WebConfiguration.java` | REQ-LANG-001 |
 | `WelcomeController` | Serves the landing page | `src/main/java/org/springframework/samples/petclinic/system/WelcomeController.java` | REQ-SYS-001 |
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java
new file mode 100644
index 0000000..8723fe0
--- /dev/null
+++ b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java
@@ -0,0 +1,37 @@
+/*
+ * Copyright 2012-2025 the original author or authors.
+ *
+ * Licensed under the Apache License, Version 2.0 (the "License");
+ * you may not use this file except in compliance with the License.
+ * You may obtain a copy of the License at
+ *
+ *      https://www.apache.org/licenses/LICENSE-2.0
+ *
+ * Unless required by applicable law or agreed to in writing, software
+ * distributed under the License is distributed on an "AS IS" BASIS,
+ * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
+ * See the License for the specific language governing permissions and
+ * limitations under the License.
+ */
+
+package org.springframework.samples.petclinic.vet;
+
+import java.util.List;
+
+import org.springframework.data.jpa.repository.JpaRepository;
+import org.springframework.data.jpa.repository.Query;
+
+/**
+ * Repository class for <code>Specialty</code> domain objects.
+ */
+public interface SpecialtyRepository extends JpaRepository<Specialty, Integer> {
+
+	/**
+	 * Retrieve all {@link Specialty}s from the data store, ordered by name. Every stored
+	 * specialty is returned, including those held by no veterinarian.
+	 * @return a List of {@link Specialty}s.
+	 */
+	@Query("SELECT specialty FROM Specialty specialty ORDER BY specialty.name")
+	List<Specialty> findSpecialties();
+
+}
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/VetController.java b/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
index 867d0b5..3f97ed9 100644
--- a/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
+++ b/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
@@ -15,7 +15,11 @@
  */
 package org.springframework.samples.petclinic.vet;
 
+import java.util.ArrayList;
+import java.util.Comparator;
+import java.util.HashMap;
 import java.util.List;
+import java.util.Map;
 
 import org.springframework.data.domain.Page;
 import org.springframework.data.domain.PageRequest;
@@ -37,8 +41,11 @@ class VetController {
 
 	private final VetRepository vetRepository;
 
-	public VetController(VetRepository vetRepository) {
+	private final SpecialtyRepository specialtyRepository;
+
+	public VetController(VetRepository vetRepository, SpecialtyRepository specialtyRepository) {
 		this.vetRepository = vetRepository;
+		this.specialtyRepository = specialtyRepository;
 	}
 
 	@GetMapping("/vets.html")
@@ -71,4 +78,49 @@ class VetController {
 		return vets;
 	}
 
+	@GetMapping("/specialties.html")
+	public String showSpecialtyList(Model model) {
+		model.addAttribute("specialties", buildSpecialtyDirectory());
+		return "vets/specialtyList";
+	}
+
+	/**
+	 * Builds the specialty-indexed directory. Every stored specialty seeds an entry (so a
+	 * specialty held by no vet still appears); each vet is then filed under the
+	 * specialties it holds. Vets holding no specialty are naturally excluded. Specialties
+	 * are ordered by stored name and the vets under each by last name then first name.
+	 */
+	private List<SpecialtyDirectoryEntry> buildSpecialtyDirectory() {
+		List<Specialty> specialties = new ArrayList<>(this.specialtyRepository.findSpecialties());
+		specialties.sort(Comparator.comparing(Specialty::getName));
+		Map<Integer, List<Vet>> holdersBySpecialtyId = new HashMap<>();
+		for (Specialty specialty : specialties) {
+			holdersBySpecialtyId.put(specialty.getId(), new ArrayList<>());
+		}
+		for (Vet vet : this.vetRepository.findAll()) {
+			for (Specialty specialty : vet.getSpecialties()) {
+				holdersBySpecialtyId.get(specialty.getId()).add(vet);
+			}
+		}
+
+		Comparator<Vet> byName = Comparator.comparing(Vet::getLastName).thenComparing(Vet::getFirstName);
+		List<SpecialtyDirectoryEntry> directory = new ArrayList<>();
+		for (Specialty specialty : specialties) {
+			List<String> vetNames = holdersBySpecialtyId.get(specialty.getId())
+				.stream()
+				.sorted(byName)
+				.map(vet -> vet.getFirstName() + " " + vet.getLastName())
+				.toList();
+			directory.add(new SpecialtyDirectoryEntry(specialty.getName(), vetNames));
+		}
+		return directory;
+	}
+
+	/**
+	 * View model for one row of the specialty directory: a specialty's stored name and
+	 * the full names of the veterinarians holding it, in render order.
+	 */
+	record SpecialtyDirectoryEntry(String name, List<String> vetNames) {
+	}
+
 }
diff --git a/src/main/resources/templates/vets/specialtyList.html b/src/main/resources/templates/vets/specialtyList.html
new file mode 100644
index 0000000..621a1c3
--- /dev/null
+++ b/src/main/resources/templates/vets/specialtyList.html
@@ -0,0 +1,20 @@
+<!DOCTYPE html>
+
+<html xmlns:th="https://www.thymeleaf.org" th:replace="~{fragments/layout :: layout (~{::body},'vets')}">
+
+<body>
+
+  <h2 th:text="#{specialties}">Specialties</h2>
+
+  <ul id="specialties" class="list-unstyled">
+    <li th:each="specialty : ${specialties}">
+      <strong th:text="${specialty.name}">specialty name</strong>
+      <ul>
+        <li th:each="vetName : ${specialty.vetNames}" th:text="${vetName}">vet full name</li>
+      </ul>
+    </li>
+  </ul>
+
+</body>
+
+</html>
diff --git a/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java b/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
index 208758c..12bbb57 100644
--- a/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
+++ b/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
@@ -16,6 +16,8 @@
 
 package org.springframework.samples.petclinic.vet;
 
+import java.util.List;
+
 import org.assertj.core.util.Lists;
 import org.junit.jupiter.api.BeforeEach;
 import org.junit.jupiter.api.Test;
@@ -31,6 +33,11 @@ import org.springframework.test.web.servlet.MockMvc;
 import org.springframework.test.web.servlet.ResultActions;
 import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
 
+import static org.hamcrest.Matchers.containsString;
+import static org.hamcrest.Matchers.hasItem;
+import static org.hamcrest.Matchers.hasSize;
+import static org.hamcrest.Matchers.not;
+import static org.hamcrest.Matchers.stringContainsInOrder;
 import static org.mockito.ArgumentMatchers.any;
 import static org.mockito.BDDMockito.given;
 import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
@@ -51,6 +58,23 @@ class VetControllerTests {
 	@MockitoBean
 	private VetRepository vets;
 
+	@MockitoBean
+	private SpecialtyRepository specialties;
+
+	private Specialty radiology() {
+		Specialty radiology = new Specialty();
+		radiology.setId(1);
+		radiology.setName("radiology");
+		return radiology;
+	}
+
+	private Specialty surgery() {
+		Specialty surgery = new Specialty();
+		surgery.setId(2);
+		surgery.setName("surgery");
+		return surgery;
+	}
+
 	private Vet james() {
 		Vet james = new Vet();
 		james.setFirstName("James");
@@ -64,18 +88,25 @@ class VetControllerTests {
 		helen.setFirstName("Helen");
 		helen.setLastName("Leary");
 		helen.setId(2);
-		Specialty radiology = new Specialty();
-		radiology.setId(1);
-		radiology.setName("radiology");
-		helen.addSpecialty(radiology);
+		helen.addSpecialty(radiology());
 		return helen;
 	}
 
+	private Vet linda() {
+		Vet linda = new Vet();
+		linda.setFirstName("Linda");
+		linda.setLastName("Douglas");
+		linda.setId(3);
+		linda.addSpecialty(radiology());
+		return linda;
+	}
+
 	@BeforeEach
 	void setup() {
-		given(this.vets.findAll()).willReturn(Lists.newArrayList(james(), helen()));
+		given(this.vets.findAll()).willReturn(Lists.newArrayList(james(), helen(), linda()));
 		given(this.vets.findAll(any(Pageable.class)))
 			.willReturn(new PageImpl<Vet>(Lists.newArrayList(james(), helen())));
+		given(this.specialties.findSpecialties()).willReturn(Lists.newArrayList(surgery(), radiology()));
 
 	}
 
@@ -97,4 +128,55 @@ class VetControllerTests {
 			.andExpect(jsonPath("$.vetList[0].id").value(1));
 	}
 
+	@Test
+	void theSpecialtyDirectoryShouldListEverySpecialtyByStoredName() throws Exception {
+		// The mock returns the specialties in non-alphabetical order (surgery,
+		// radiology);
+		// the rendered page must restore stored-name order (radiology before surgery).
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(view().name("vets/specialtyList"))
+			.andExpect(content().string(stringContainsInOrder("radiology", "surgery")));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldShowHoldingVetsByFullName() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(containsString("Helen Leary")));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldOrderHoldingVetsByName() throws Exception {
+		// Douglas and Leary both hold radiology; last-name order must render Douglas
+		// first,
+		// reversing the order in which the vets are filed (Leary before Douglas).
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(stringContainsInOrder("Linda Douglas", "Helen Leary")));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldListSpecialtyHeldByNoVet() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(model().attribute("specialties",
+					hasItem(new VetController.SpecialtyDirectoryEntry("surgery", List.of()))));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldOmitVetWithNoSpecialty() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(not(containsString("James Carter"))));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(model().attribute("specialties", hasSize(2)))
+			.andExpect(model().attributeDoesNotExist("totalPages"));
+	}
+
 }
```

</details>

## Pipeline

### REQ-VET-003 — Specialty directory: veterinarians grouped by specialty

1 review round · 2 build-passes · no grade yet

| reviewer | R1 |
| --- | --- |
| **code-quality** | ✎ (2) |
| **test** | ✎ (5) |
| **security** | **✔** |
| **doc** | ✎ (3) |

- ◇ **prd-entry** Specialty directory page · (prd-expert) · ***◷ 30s***
- ◈ **design-block** **minor** · (design) · ***◷ 1m***
- ◆ **implement** (implementer)
  - ▲ **build ✓ clean** · build · test · format · check
- ✔ **review security** · **approved** · ***◷ 0s***
- ✎ **review code-quality** · **changes_requested** · (2 findings) · ***◷ 5m***
  - [autofix] `VetController.java:buildSpecialtyDirec` The guard `if (holders != null)` is dead code. `holdersBySpecialtyId` is seeded from `findSpecialties()`, which returns every row in the specialty table. A `Specialty` on a `Vet` from the FK-constrained `@ManyToMany` join table can only reference a row that exists in that table, so `holdersBySpecialtyId.get(specialty.getId())` cannot return null for any specialty `vet.getSpecialties()` yields. The guard silently swallows what would be a referential-integrity violation rather than surfacing it as a NullPointerException, hiding data corruption and adding noise without benefit.
    - fix: Remove the null-guard and intermediate variable. Replace the three-line body `List\<Vet> holders = holdersBySpecialtyId.get(specialty.getId()); if (holders != null) { holders.add(vet); }` with the single statement `holdersBySpecialtyId.get(specialty.getId()).add(vet);`.
  - [autofix] `VetController.java:buildSpecialtyDirec` The final directory order is determined by re-iterating `specialties` (the list returned ordered by name from `findSpecialties()`), not by the map. `LinkedHashMap` is used only as a lookup structure keyed by specialty ID; its insertion-order guarantee is unused. Using `LinkedHashMap` over `HashMap` signals to the next reader that map iteration order matters for correctness — a false signal. Replace with `HashMap` to communicate that this is a lookup map, not an ordered structure.
    - fix: Change `new LinkedHashMap\<>()` to `new HashMap\<>()` on the map initializer line, and replace the `import java.util.LinkedHashMap;` import with `import java.util.HashMap;`.
- ✎ **review test** · **changes_requested** · (5 findings) · ***◷ 5m***
  - [autofix] `VetControllerTests.java:119,128,135,14` All five new test method names start with `specialtyDirectory...Should...` instead of `theSpecialtyDirectory...Should...`. The brief (§ Test Naming) mandates the `the{Subject}Should{Outcome}` school for tests written from 2026-07-31 onward. The `the` prefix is missing from all five.
    - fix: Rename: specialtyDirectoryShouldListEverySpecialtyByStoredName -> theSpecialtyDirectoryShouldListEverySpecialtyByStoredName; specialtyDirectoryShouldShowHoldingVetsByFullName -> theSpecialtyDirectoryShouldShowHoldingVetsByFullName; specialtyDirectoryShouldListSpecialtyHeldByNoVet -> theSpecialtyDirectoryShouldListSpecialtyHeldByNoVet; specialtyDirectoryShouldOmitVetWithNoSpecialty -> theSpecialtyDirectoryShouldOmitVetWithNoSpecialty; specialtyDirectoryShouldRenderAllSpecialtiesOnOnePage -> theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage.
  - **[blocked]** `VetControllerTests.java:135-139` AC#3 is only half-covered. `specialtyDirectoryShouldListSpecialtyHeldByNoVet` asserts `containsString("surgery")` — surgery appears on the page — which is non-vacuous and would fail if the controller dropped holder-free specialties. However the second half of the criterion, "with no veterinarian beneath it", is never asserted. If a bug incorrectly attributed Helen Leary to surgery, all five tests would still pass. A complete test must also verify that the surgery entry carries no vet names, either via `model().attribute(...)` asserting the surgery SpecialtyDirectoryEntry has empty vetNames, or via a structural HTML check.
  - **[blocked]** `VetControllerTests.java:119-125` Specialty ordering is not asserted. The design-block requires specialties ordered by stored name (repository ORDER BY s.name); the controller preserves repository order. The two mock specialties `radiology` and `surgery` happen to be listed in alphabetical order in the `willReturn` stub, so reversing the rendered order cannot be detected by `containsString` checks. A test must return specialties in a non-alphabetical order from the mock and assert the rendered output restores alphabetical order, or assert rendered position (e.g. `radiology` appears before `surgery` in the response body).
  - **[blocked]** `VetControllerTests.java:128-132` Vet ordering under a specialty is not asserted. The design-block specifies vets under each specialty are sorted last-name-then-first-name before rendering. The current fixture has only one vet (Helen Leary) holding any specialty, so ordering is structurally unobservable. A test must add a second fixture vet holding the same specialty (with a name that sorts differently) and verify the rendered order.
  - [clarify] `prd.md` AC#6 — "The page is read-only: it adds, changes, and removes nothing (NG-2 unchanged)" — has no dedicated test. The controller is `@GetMapping`-only and makes no write calls, giving structural read-only proof. Whether the PRD intends a behavioral assertion (e.g., verifying no write mock methods are invoked) or accepts the structural constraint of a GET-only handler as sufficient is a product decision.
- ✎ **review doc** · **changes_requested** · (3 findings) · ***◷ 3m***
  - [autofix] `prd.md:125` Sentence starting "It lists every specialty the clinic knows, each by its stored name, and under each specialty the veterinarians holding it" is 38 words, exceeding the 30-word writing standard.
    - fix: It lists every specialty the clinic knows, each by its stored name. Under each specialty it shows the holding veterinarians, each by full name with the first name before the last name (for example "Helen Leary").
  - [autofix] `system-design.md:104` The SpecialtyRepository contract row embeds design rationale in what should be a behavioral description: the clause "the specialty directory’s enumeration path, which the vet–specialty traversal cannot supply because a specialty held by no vet is unreachable from any vet" explains why the repository exists rather than what it does. The rationale is already captured in the VetController.buildSpecialtyDirectory() Javadoc. Trim to the behavioral description, matching the PetTypeRepository row pattern.
    - fix: Spring Data repository for specialties, returning all of them in name order
  - **[escalate]** `specialtyList.html:3` REQ-SYS-001 open item judgment: the specialty directory page uses the standard layout fragment (confirmed at specialtyList.html:3: th:replace with layout, vets active), which carries navigation to owner search and the veterinarian directory. REQ-SYS-001 acceptance criterion (every page carries navigation to owner search and to the veterinarian directory) is satisfied for the specialty directory page. No documented inconsistency with REQ-SYS-001 as written exists. However, the specialty directory has no inbound path from the site navigation menu, making it unreachable for a user who does not know the URL. This discoverability gap is outside REQ-SYS-001 wording but may be a real usability concern. Human decision: add a nav link or accept the gap as intentional given the demonstration context.
- ✚ **doc-autofix** `docs/system-design.md` · writing-standards · (root)
- ↻ **fix prd-expert** ← test, doc · (8 findings)
- ◇ **prd-entry** Specialty directory: veterinarians grouped by specialty · (prd-expert) · ***◷ 1m***
- ↻ **implement** (implementer) ← code-quality, test · (7 findings) · ***◷ 15m***
  - ▲ **build ✓ clean** · build · test · format · check

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- XSS: specialtyList.html renders specialty name and vet names via th:text (auto-escaped); no th:utext or unescaped DOM sink introduced
- Injection: SpecialtyRepository.findSpecialties() is a static parameterless JPQL @Query with no string concatenation; /specialties.html binds no request parameters
- Data exposure: SpecialtyDirectoryEntry view model exposes only specialty name and formatted vet full-name strings; specialty ids used only as internal map keys, never rendered
- DoS: unpaginated render is over an admin-curated reference table (accepted product trade-off, not attacker-controlled); no finding
- Supply chain: no *.gradle or dependency changes; no new dependency added

**code-quality-reviewer**

- SpecialtyRepository mirrors PetTypeRepository faithfully: same JpaRepository extension, same @Query + ORDER BY pattern, same findXxx() naming convention (grep-confirmed; IDE not consulted)
- Javadoc on buildSpecialtyDirectory clearly explains the seeding/filing logic and the orphan-specialty invariant
- SpecialtyDirectoryEntry record is appropriately scoped as a controller-local view model; fields are typed (String, List\<String>); no raw Object or Map
- Comparator\<Vet> by last name then first name is a correct and deterministic sort key, expressed cleanly
- Stream pipeline in the directory-building step (sorted → map → toList) is idiomatic and readable
- Template follows the layout-fragment convention from vetList.html: th:replace with vets menu active
- No get/set prefixes on record accessors; record declared without mutable state

**test-reviewer**

- specialtyDirectoryShouldOmitVetWithNoSpecialty uses not(containsString("James Carter")) — non-vacuous because test 2 proves Helen Leary is rendered, confirming the vet-name rendering machinery is active and selective
- specialtyDirectoryShouldShowHoldingVetsByFullName checks containsString("Helen Leary") against the rendered HTTP response body (not model state), and the exact substring "Helen Leary" would fail if the template emitted "Leary Helen"
- specialtyDirectoryShouldRenderAllSpecialtiesOnOnePage uses hasSize(2) + attributeDoesNotExist("totalPages") — not tautological; hasSize(2) would fail if the controller dropped any specialty, attributeDoesNotExist would fail if pagination were added
- @MockitoBean SpecialtyRepository accepted as tolerated continuity: the existing class already uses @MockitoBean VetRepository in a @WebMvcTest context; a JPA-repository hand-written double would require implementing ~30 JpaRepository methods; the brief tolerance clause explicitly covers this existing pattern
- Factory methods radiology(), surgery(), james(), helen() properly encapsulate object construction per the brief; no bare mystery literals
- All five tests pass cleanly against the real MVC dispatch and Thymeleaf rendering pipeline

**doc-reviewer**

- REQ-VET-003 prose correctly omits the route, controller name, and template name; mechanism is in system-design.md
- REQ-VET-001 is intact and correctly cross-referenced as the inverse view in the new REQ-VET-003 paragraph
- NG-2 wording is unchanged; edge case 4 references it correctly without weakening it
- Numbering: REQ-VET-002 is in the Superseded list; REQ-VET-003 is the correct next unused ID per the never-renumber rule
- Acceptance criteria follow the established Given/When/Then format; the specialty-held-by-no-vet case is explicitly stated rather than left implicit
- system-design.md SpecialtyRepository contract accurately reflects findSpecialties() returning all specialties in name order
- VetController contract row accurately reflects the three routes it now serves
- Specialty row correctly lists REQ-VET-001 and REQ-VET-003
- Anchor \<a id="req-vet-003">\</a> present and correctly placed before the introducing paragraph

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $7.47 | 13m 51s | 91% |
| `(parent)` | 1 | opus-5 | $5.12 | 62m 58s | 95% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $3.49 | 4m 14s | 71% |
| `spring-boot-claude:system-design-expert` | 1 | opus-4-8 | $3.30 | 2m 38s | 78% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $2.04 | 27m 10s | 66% |
| `spring-boot-claude:security-reviewer` | 1 | opus-4-8 | $2.03 | 52s | 62% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $1.70 | 58m 37s | 73% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $1.62 | 18m 24s | 68% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.27 | 41s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $5.12 | 62m 58s | 95% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $3.90 | 6m 58s | 90% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $3.57 | 6m 52s | 92% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $3.30 | 2m 38s | 78% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $2.03 | 52s | 62% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.80 | 1m 58s | 74% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.69 | 2m 16s | 67% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $1.14 | 22m 27s | 50% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.91 | 4m 31s | 83% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.90 | 4m 43s | 78% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.85 | 2m 47s | 81% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.78 | 54m 5s | 53% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.78 | 15m 37s | 33% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.27 | 41s | 50% |

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

- plugin `spring-boot-claude` at `v0.1.1` (tag)
- model requested `claude-opus-5`; models used: opus-4-8 · opus-5 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `9c6fd220a549ce32` · `2.1.222 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
