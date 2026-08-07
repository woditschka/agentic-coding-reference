# specialty-directory r2 — v0.1.1

Specialty directory page (feature) · started 2026-08-06T13:38:54+00:00 · exec `claude-dev` · status **complete**

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
| checkpoints | 7/7 |
| review attention (pipeline grade) | clear |

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
| 3 (±1) | 3 (±0) | 3 (±0) | 4 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.50. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 4

> New grouping/sorting logic lives in  VetController.groupVetsBySpecialty / holdsSpecialty , a fresh business rule in a web controller that the catalog places in a domain service — the recorded deviation explicitly does not extend to new rules, and it also blocks a unit test, widening the pyramid gap.  SpecialtyRepository  and the docs updates (prd.md REQ-VET-003, contracts rows) fit cleanly. Matching by  held.getName().equals(specialty.getName())  instead of identity is fragile, the template's  vet.firstName + ' ' + vet.lastName + ' '  trailing-space hack is rough, and no message bundle gains  specialties / none  keys the layout and template now reference. Tests use behavior names and factories, but rely on a shared  @BeforeEach  fixture, add a second Mockito stub, assert on raw HTML substrings, and carry narration comments the principles forbid.

**Sample 2** — design-fit 2 · test-quality 3 · maintainability 3 · doc-fit 4

> The join lives in  VetController.groupVetsBySpecialty() / holdsSpecialty()  — a new rule in a controller, which the brief calls a fresh violation not covered by the existing deviation; a *Domain service* was available without an ADR.  SpecialtyRepository  is a repository over a non-root lookup type, and  record SpecialtyVets  is a view model nested in the web layer. Matching by  held.getName().equals(specialty.getName())  rather than identity is fragile.  specialtyList.html  uses  #{specialties} / #{none}  with no message-bundle change in the patch. Tests are well-named ( theSpecialtyDirectoryShould… ) and use factories, but carry narration comments ( // James Carter holds no specialty… , setup comments) the principles forbid, lean on a shared  @BeforeEach  mystery guest, and never assert dentistry renders with no vets. Docs: PRD REQ-VET-003 and the contracts table both updated.

**Sample 3** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 4

> The grouping rule lands in  VetController.groupVetsBySpecialty / holdsSpecialty  — a fresh Web-controller violation the catalog explicitly says the recorded deviation does not cover; a domain service (Available, no ADR needed) or a repository join would have kept it unit-testable, and the nested  SpecialtyVets  record matches no catalog pattern.  SpecialtyRepository  itself is well-placed and named. Tests use BDD names and factories, but arrange lives in a shared mutable  @BeforeEach  (mystery guest), the narration comments ("// James holds no specialty...") restate code, and every new test boots MockMvc, widening the pyramid gap.  holdsSpecialty  compares by name rather than identity; the template's  firstName + ' ' + lastName + ' '  trailing-space join is crude;  #{specialties}  and  #{none}  are introduced with no message bundle entries in the patch. Docs: PRD REQ-VET-003 and the contracts table are current.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $10.58 | 31m | 3 | 85% | 7 file(s) +219/−17 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $2.03 | 4m 0s | 91% |

## Change

<details>
<summary>Diff (rendered from <code>change.patch</code>)</summary>

```diff
diff --git a/docs/prd.md b/docs/prd.md
index 0cb7f37..b36cc9e 100644
--- a/docs/prd.md
+++ b/docs/prd.md
@@ -130,6 +130,23 @@ The clinic publishes the veterinarians it employs with the specialties each hold
 
 **Design:** [system-design.md#contracts](system-design.md#contracts)
 
+### Specialty directory
+
+<a id="req-vet-003"></a>
+
+The clinic also publishes its specialties the other way round. Staff can answer which veterinarians hold a given specialty as readily as the veterinarian directory answers the reverse. Every specialty the clinic knows is listed by name on a single page, with no pagination. Each specialty shows the veterinarians who hold it, named in full: first name then last name. The page lists specialties, not the veterinarian roster. A veterinarian holding no specialty is absent from the page. A specialty held by no veterinarian is still listed, with no veterinarians beneath it. Managing veterinarians or specialties stays out of scope (NG-2); this is a read-only view of the directory the clinic already holds `[REQ-VET-003]`.
+
+**Done when:**
+- `[REQ-VET-003]` given the clinic's specialties, when the specialty directory is opened, then every specialty is listed by its stored name on one page with no pagination.
+- `[REQ-VET-003]` given a specialty held by one or more veterinarians, when the directory is opened, then each holding veterinarian is named by first name followed by last name.
+- `[REQ-VET-003]` given a specialty held by no veterinarian, when the directory is opened, then that specialty is still listed with no veterinarians beneath it.
+- `[REQ-VET-003]` given a veterinarian holding no specialty, when the directory is opened, then that veterinarian is absent from the page, because the page lists specialties rather than veterinarians.
+
+**Edge cases:**
+1. A specialty's veterinarians are presented in a stable order rather than an arbitrary one, mirroring the veterinarian directory.
+
+**Design:** [system-design.md#contracts](system-design.md#contracts)
+
 ### Language
 
 <a id="req-lang-001"></a><a id="req-lang-002"></a>
diff --git a/docs/system-design.md b/docs/system-design.md
index 9d58a3a..b7a6bd1 100644
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
+| `SpecialtyRepository` | Spring Data repository for specialties; returns every stored specialty in name order, mirroring `PetTypeRepository`; not cached | `src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java` | REQ-VET-003 |
+| `VetController` | Serves the paged HTML vet list, a serialized vet collection from a second route, and the unpaginated specialty directory at `/specialties.html` grouping every stored specialty with the veterinarians holding it | `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` | REQ-VET-001, REQ-VET-003 |
 | `CacheConfiguration` | Enables caching and declares the vet cache through the JCache API | `src/main/java/org/springframework/samples/petclinic/system/CacheConfiguration.java` | REQ-VET-001 |
 | `WebConfiguration` | Session-scoped locale resolution plus a request-parameter locale switch | `src/main/java/org/springframework/samples/petclinic/system/WebConfiguration.java` | REQ-LANG-001 |
 | `WelcomeController` | Serves the landing page | `src/main/java/org/springframework/samples/petclinic/system/WelcomeController.java` | REQ-SYS-001 |
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java
new file mode 100644
index 0000000..0bfc8c9
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
+
+public interface SpecialtyRepository extends JpaRepository<Specialty, Integer> {
+
+	/**
+	 * Retrieve all {@link Specialty Specialties} from the data store, ordered by name.
+	 * @return a Collection of {@link Specialty Specialties}.
+	 */
+	@Query("SELECT s FROM Specialty s ORDER BY s.name")
+	List<Specialty> findSpecialties();
+
+}
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/VetController.java b/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
index 867d0b5..49a7343 100644
--- a/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
+++ b/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
@@ -15,6 +15,9 @@
  */
 package org.springframework.samples.petclinic.vet;
 
+import java.util.ArrayList;
+import java.util.Collection;
+import java.util.Comparator;
 import java.util.List;
 
 import org.springframework.data.domain.Page;
@@ -37,8 +40,11 @@ class VetController {
 
 	private final VetRepository vetRepository;
 
-	public VetController(VetRepository vetRepository) {
+	private final SpecialtyRepository specialtyRepository;
+
+	public VetController(VetRepository vetRepository, SpecialtyRepository specialtyRepository) {
 		this.vetRepository = vetRepository;
+		this.specialtyRepository = specialtyRepository;
 	}
 
 	@GetMapping("/vets.html")
@@ -71,4 +77,40 @@ class VetController {
 		return vets;
 	}
 
+	@GetMapping("/specialties.html")
+	public String showSpecialtyList(Model model) {
+		model.addAttribute("specialties", groupVetsBySpecialty());
+		return "vets/specialtyList";
+	}
+
+	/**
+	 * Assemble every specialty the clinic knows, each paired with the veterinarians
+	 * holding it. Specialties come from the store name-ordered; the veterinarians under
+	 * each are ordered deterministically by last name then first name so the page never
+	 * depends on {@code Set} iteration order. A specialty held by no veterinarian keeps
+	 * an empty list; a veterinarian holding no specialty is absent because the page lists
+	 * specialties rather than the veterinarian roster.
+	 */
+	private List<SpecialtyVets> groupVetsBySpecialty() {
+		Collection<Vet> allVets = this.vetRepository.findAll();
+		Comparator<Vet> byName = Comparator.comparing(Vet::getLastName).thenComparing(Vet::getFirstName);
+		List<SpecialtyVets> grouped = new ArrayList<>();
+		for (Specialty specialty : this.specialtyRepository.findSpecialties()) {
+			List<Vet> holders = allVets.stream().filter(vet -> holdsSpecialty(vet, specialty)).sorted(byName).toList();
+			grouped.add(new SpecialtyVets(specialty, holders));
+		}
+		return grouped;
+	}
+
+	private boolean holdsSpecialty(Vet vet, Specialty specialty) {
+		return vet.getSpecialties().stream().anyMatch(held -> held.getName().equals(specialty.getName()));
+	}
+
+	/**
+	 * A specialty paired with the veterinarians holding it, for display on the specialty
+	 * directory page.
+	 */
+	record SpecialtyVets(Specialty specialty, List<Vet> vets) {
+	}
+
 }
diff --git a/src/main/resources/templates/fragments/layout.html b/src/main/resources/templates/fragments/layout.html
index 7c5cd0d..99f4929 100644
--- a/src/main/resources/templates/fragments/layout.html
+++ b/src/main/resources/templates/fragments/layout.html
@@ -53,6 +53,11 @@
             <span th:text="#{vets}">Veterinarians</span>
           </li>
 
+          <li th:replace="~{::menuItem ('/specialties.html','specialties','specialties','list-alt',#{specialties})}">
+            <span class="fa fa-list-alt" aria-hidden="true"></span>
+            <span th:text="#{specialties}">Specialties</span>
+          </li>
+
           <li
             th:replace="~{::menuItem ('/oups','error','trigger a RuntimeException to see how it is handled','exclamation-triangle',#{error})}">
             <span class="fa exclamation-triangle" aria-hidden="true"></span>
diff --git a/src/main/resources/templates/vets/specialtyList.html b/src/main/resources/templates/vets/specialtyList.html
new file mode 100644
index 0000000..ce3b21d
--- /dev/null
+++ b/src/main/resources/templates/vets/specialtyList.html
@@ -0,0 +1,28 @@
+<!DOCTYPE html>
+
+<html xmlns:th="https://www.thymeleaf.org" th:replace="~{fragments/layout :: layout (~{::body},'specialties')}">
+
+<body>
+
+  <h2 th:text="#{specialties}">Specialties</h2>
+
+  <table id="specialties" class="table table-striped">
+    <thead>
+      <tr>
+        <th th:text="#{name}">Name</th>
+        <th th:text="#{vets}">Veterinarians</th>
+      </tr>
+    </thead>
+    <tbody>
+      <tr th:each="group : ${specialties}">
+        <td th:text="${group.specialty.name}"></td>
+        <td>
+          <span th:each="vet : ${group.vets}" th:text="${vet.firstName + ' ' + vet.lastName + ' '}" /> <span
+            th:if="${#lists.isEmpty(group.vets)}" th:text="#{none}">none</span>
+        </td>
+      </tr>
+    </tbody>
+  </table>
+</body>
+
+</html>
diff --git a/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java b/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
index 208758c..f19a94a 100644
--- a/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
+++ b/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
@@ -29,8 +29,12 @@ import org.springframework.test.context.aot.DisabledInAotMode;
 import org.springframework.test.context.bean.override.mockito.MockitoBean;
 import org.springframework.test.web.servlet.MockMvc;
 import org.springframework.test.web.servlet.ResultActions;
-import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
 
+import java.util.List;
+
+import static org.hamcrest.Matchers.containsString;
+import static org.hamcrest.Matchers.not;
+import static org.hamcrest.Matchers.stringContainsInOrder;
 import static org.mockito.ArgumentMatchers.any;
 import static org.mockito.BDDMockito.given;
 import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
@@ -51,38 +55,64 @@ class VetControllerTests {
 	@MockitoBean
 	private VetRepository vets;
 
+	@MockitoBean
+	private SpecialtyRepository specialties;
+
+	private Specialty specialty(String name) {
+		Specialty specialty = new Specialty();
+		specialty.setName(name);
+		return specialty;
+	}
+
+	private Vet vet(String firstName, String lastName, String... specialtyNames) {
+		Vet vet = new Vet();
+		vet.setFirstName(firstName);
+		vet.setLastName(lastName);
+		for (String specialtyName : specialtyNames) {
+			vet.addSpecialty(specialty(specialtyName));
+		}
+		return vet;
+	}
+
 	private Vet james() {
-		Vet james = new Vet();
-		james.setFirstName("James");
-		james.setLastName("Carter");
+		Vet james = vet("James", "Carter");
 		james.setId(1);
 		return james;
 	}
 
 	private Vet helen() {
-		Vet helen = new Vet();
-		helen.setFirstName("Helen");
-		helen.setLastName("Leary");
+		Vet helen = vet("Helen", "Leary", "radiology");
 		helen.setId(2);
-		Specialty radiology = new Specialty();
-		radiology.setId(1);
-		radiology.setName("radiology");
-		helen.addSpecialty(radiology);
 		return helen;
 	}
 
+	private Vet rafael() {
+		Vet rafael = vet("Rafael", "Ortega", "radiology");
+		rafael.setId(3);
+		return rafael;
+	}
+
+	private Vet linda() {
+		Vet linda = vet("Linda", "Douglas", "surgery");
+		linda.setId(4);
+		return linda;
+	}
+
 	@BeforeEach
 	void setup() {
-		given(this.vets.findAll()).willReturn(Lists.newArrayList(james(), helen()));
+		// James holds no specialty; Helen and Rafael hold radiology; Linda holds surgery.
+		given(this.vets.findAll()).willReturn(Lists.newArrayList(james(), rafael(), helen(), linda()));
 		given(this.vets.findAll(any(Pageable.class)))
 			.willReturn(new PageImpl<Vet>(Lists.newArrayList(james(), helen())));
-
+		// dentistry is a known specialty held by no veterinarian; returned name-ordered.
+		given(this.specialties.findSpecialties())
+			.willReturn(List.of(specialty("dentistry"), specialty("radiology"), specialty("surgery")));
 	}
 
 	@Test
 	void showVetListHtml() throws Exception {
 
-		mockMvc.perform(MockMvcRequestBuilders.get("/vets.html?page=1"))
+		mockMvc.perform(get("/vets.html?page=1"))
 			.andExpect(status().isOk())
 			.andExpect(model().attributeExists("listVets"))
 			.andExpect(view().name("vets/vetList"));
@@ -97,4 +127,46 @@ class VetControllerTests {
 			.andExpect(jsonPath("$.vetList[0].id").value(1));
 	}
 
+	@Test
+	void theSpecialtyDirectoryShouldReturnHtml() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(model().attributeExists("specialties"))
+			.andExpect(view().name("vets/specialtyList"));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldGroupVeterinariansBySpecialty() throws Exception {
+		// Helen Leary and Rafael Ortega both hold radiology; they render under it in a
+		// stable last-name-then-first-name order (Leary before Ortega), regardless of the
+		// order the repository returns them in.
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(containsString("surgery")))
+			.andExpect(content().string(stringContainsInOrder("surgery", "Linda Douglas")))
+			.andExpect(content().string(stringContainsInOrder("radiology", "Helen Leary", "Rafael Ortega")));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldNameEachVeterinarianByFullName() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(containsString("Helen Leary")));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldIncludeSpecialtiesHeldByNoVeterinarian() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(stringContainsInOrder("dentistry", "radiology")));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldOmitVeterinariansHoldingNoSpecialty() throws Exception {
+		// James Carter holds no specialty, so he is absent from the specialty directory.
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(not(containsString("James Carter"))));
+	}
+
 }
```

</details>

## Pipeline

### REQ-VET-003 — Specialty directory page

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (1) | **✔** |
| **test** | ✎ (3) | **✔** |
| **security** | **✔** | · |
| **doc** | ✎ (1) | **✔** |

- ◇ **prd-entry** Specialty directory page · (prd-expert) · ***◷ 31s***
- ◈ **design-block** **minor** · (design) · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 5m***
  - ▲ **build ✓ clean** · build · test · format · check
- ✔ **review security** · **approved** · ***◷ 20s***
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 5m***
  - [autofix] `VetControllerTests.java:116` showVetListHtml uses the qualified form MockMvcRequestBuilders.get(...) while the new specialty tests introduced a static import of get and use it unqualified. The file now contains both call styles, which is a style deviation internal to the file.
    - fix: Change MockMvcRequestBuilders.get("/vets.html?page=1") to get("/vets.html?page=1") to use the static import already declared on line 41 consistently throughout the file.
- ✎ **review test** · **changes_requested** · (3 findings) · ***◷ 5m***
  - [autofix] `VetControllerTests.java:132-171` All five new test method names do not follow the `the{Subject}Should{Outcome}` BDD naming school mandated by docs/testing-principles.md § Test Naming for tests written from 2026-07-31 onward. Names like `showSpecialtyListHtml` and `showSpecialtyListGroupsVeterinariansBySpecialty` mirror the controller method name rather than stating what must be true. A future rename of the production method would break the test-as-specification link.
    - fix: Rename the five methods: showSpecialtyListHtml -> theSpecialtyDirectoryShouldReturnHtml; showSpecialtyListGroupsVeterinariansBySpecialty -> theSpecialtyDirectoryShouldGroupVeterinariansBySpecialty; showSpecialtyListNamesVeterinarianInFull -> theSpecialtyDirectoryShouldNameEachVeterinarianByFullName; showSpecialtyListIncludesSpecialtyWithNoVeterinarian -> theSpecialtyDirectoryShouldIncludeSpecialtiesHeldByNoVeterinarian; showSpecialtyListOmitsVeterinarianWithNoSpecialty -> theSpecialtyDirectoryShouldOmitVeterinariansHoldingNoSpecialty
  - [autofix] `VetControllerTests.java:59-60` @MockitoBean SpecialtyRepository is a new mock of an internal repository. docs/testing-principles.md § Mocking Policy states that new tests must reach for a real implementation or a hand-written double first; a framework stub is a conscious exception chosen only when neither fits. In @WebMvcTest context a @TestConfiguration providing a hand-written double (an anonymous implementation of SpecialtyRepository returning fixed data) is feasible and is the preferred approach for new code.
    - fix: Replace @MockitoBean SpecialtyRepository with a @TestConfiguration static inner class that provides a @Bean returning an anonymous SpecialtyRepository implementation whose findSpecialties() returns List.of(specialty("dentistry"), specialty("radiology"), specialty("surgery")). Remove the `given(this.specialties.findSpecialties())...` stub in @BeforeEach.
  - [autofix] `VetControllerTests.java:146-147` The assertion `content().string(containsString("Linda Douglas"))` in showSpecialtyListGroupsVeterinariansBySpecialty verifies that Linda Douglas appears somewhere on the page but does not verify that she appears under the `surgery` heading. If the template emitted all vets in a flat header and then specialty sections, the assertion would pass incorrectly. Using stringContainsInOrder would anchor her name to its specialty context.
    - fix: Replace `content().string(containsString("Linda Douglas"))` with `content().string(stringContainsInOrder("surgery", "Linda Douglas"))`.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 10m***
  - [autofix] `prd.md:137` Three sentences in the REQ-VET-003 prose paragraph exceed the 30-word limit, violating the writing standard (sentences under 30 words; 70% under 20 words). Sentence 1 (~32 words): "The clinic also publishes its specialties the other way round, so staff can answer which veterinarians hold this specialty as readily as the veterinarian directory answers which specialties does this veterinarian hold.". Sentence 2 (~38 words): "Every specialty the clinic knows is listed by its stored name on a single page — no pagination — each shown with the veterinarians who hold it, and each such veterinarian named in full, first name then last name.". Sentence 3 (~38 words): "The page lists specialties, not the veterinarian roster: a veterinarian holding no specialty appears under no specialty, and so is absent from the page; a specialty held by no veterinarian is still listed, with no veterinarians beneath it.".
    - fix: Replace the three sentences with: "The clinic also publishes its specialties the other way round. Staff can answer which veterinarians hold a given specialty as readily as the veterinarian directory answers the reverse. Every specialty the clinic knows is listed by name on a single page, with no pagination. Each specialty shows the veterinarians who hold it, named in full: first name then last name. The page lists specialties, not the veterinarian roster. A veterinarian holding no specialty is absent from the page. A specialty held by no veterinarian is still listed, with no veterinarians beneath it."
- ↻ **implement** (implementer) ← code-quality, test · (4 findings) · ***◷ 2h 6m***
  - ▲ **build ✓ clean**
- ↻ **fix prd-expert** ← doc · (1 finding)
- ✔ **review code-quality** · **approved** · ***◷ 5m***
- ✔ **review test** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ◆ **grade CLEAR** · add read-only specialty directory page
  - blast_radius — **clear** — Contained to the vet package plus its templates and docs: a new SpecialtyRepository, one grouping method and a nested SpecialtyVets record in VetController, a new /specialties.html route, a menu item, and a template. No sensitive paths; the added constructor parameter is Spring-injected and existing wiring is unaffected.
  - semantic_surprise — **clear** — Read the controller: specialties come name-ordered from the query, holders are matched by specialty name and sorted deterministically by last-then-first name, an empty specialty is still emitted and a vet with no specialty is never matched. Behavior matches the diff's description exactly; no inverted operator or hidden effect. Template reuses message keys (specialties, none, name, vets) that already exist in the bundle.
  - test_adequacy — **clear** — Five new MockMvc tests drive the real /specialties.html render and assert on HTML output: stringContainsInOrder anchors the last-then-first grouping order, dentistry (held by nobody) is asserted present, and James Carter (no specialty) is asserted absent. They fail against a broken grouping or ordering, and the by-name matching is forced because test fixtures build fresh Specialty instances per vet.
  - reviewer_hedging — **clear** — All four reviewers approved. The one declined tested-as-spec finding (keep @MockitoBean SpecialtyRepository rather than a hand-written double) was accepted on the merits by the test-reviewer on re-review: the JpaRepository surface makes a double heavier not lighter, and it stays consistent with the sibling @MockitoBean VetRepository. Security's round-1 approval stands because round 2 touched only test and doc files.
  - scope_deviation — **clear** — Zero design revisions, zero consultations, zero build retries. The change delivers exactly the REQ-VET-003 surface — a read-only specialty directory — and explicitly excludes managing vets or specialties per NG-2. No wandering past the triaged scope.
  - why — All five facets clear on a direct read of the hunks. A cohesive, read-only single-feature change whose controller logic and edge cases match the spec and whose tests exercise them. Confirm and merge; a quick read of VetController.groupVetsBySpecialty suffices.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- JPQL query findSpecialties() is parameterless with no user input - no injection surface
- Controller handler showSpecialtyList takes no request input; reads existing repositories only
- specialtyList.html renders all vet/specialty data via th:text (HTML-escaped by default) - full-name concatenation stays inside the escaped expression, no XSS sink
- No new data exposure: only specialty names and vet first/last names, already public via /vets.html and /vets JSON; consistent with the app existing public-read model

**code-quality-reviewer**

- SpecialtyRepository mirrors PetTypeRepository cleanly: uncached, name-ordered @Query, JpaRepository over Specialty, correct license header
- VetController: constructor injection, package-private record, groupVetsBySpecialty method comment explains all four behavioral contracts (name-order, deterministic vet sort, empty specialty, absent-vet)
- SpecialtyVets record: immutable, typed fields, toList() returns unmodifiable list so no defensive copy needed
- holdsSpecialty compares by name, which is correct given the test fixture uses name-only Specialty objects and the production domain enforces name uniqueness
- specialtyList.html reuses existing message keys (#{specialties} #{name} #{vets} #{none}) per the implementation plan; #{none} guard for empty specialties is present
- layout.html navbar entry follows the exact menuItem fragment pattern; active marker specialties matches the second layout argument in specialtyList.html
- Six test methods cover the full behavioral surface: HTTP 200 + model attribute + view name, grouping with deterministic vet order, full-name rendering, specialty-with-no-vet included, vet-with-no-specialty omitted
- checkFormat: BUILD SUCCESSFUL (format gate already confirmed in build-pass; independently re-verified)

**test-reviewer**

- All five new tests drive the real Thymeleaf rendering via MockMvc rather than asserting only model attributes — the tests verify rendered HTML behavior as specified
- Ordering acceptance criterion (last-name then first-name) is correctly verified with stringContainsInOrder("radiology", "Helen Leary", "Rafael Ortega") — Leary before Ortega proves deterministic ordering
- AC3 (specialty with no vet still renders): dentistry covered by showSpecialtyListIncludesSpecialtyWithNoVeterinarian using a named specialty fixture absent from the vet roster
- AC4 (vet with no specialty absent): James Carter covered by showSpecialtyListOmitsVeterinarianWithNoSpecialty using not(containsString(...)) against real rendered content
- Factory methods specialty(), vet(), james(), helen(), rafael(), linda() properly encapsulate object construction behind named roles — no bare constructor calls in test bodies
- JaCoCo: vet package at 100% line and branch coverage; project total at 90% — exceeds the 80% domain-package target from docs/testing-principles.md § Coverage
- SpecialtyVets record in production code carries typed grouping rather than a raw Map, making the model attribute self-documenting and the assertions trustworthy

**doc-reviewer**

- \<a id="req-vet-003">\</a> anchor present at correct location in prd.md
- No code blocks, Java constructs, or internal class names in PRD entry
- PRD cross-reference system-design.md#contracts resolves to the Contracts section
- REQ-VET-003 in system-design.md Implements column has a matching prd.md entry
- SpecialtyRepository source path verified against working tree
- SpecialtyRepository not-cached claim is accurate (no @Cacheable in source)
- VetController description accurately matches the three-route implementation and /specialties.html grouping behavior
- Specialty Implements field correctly cites both REQ-VET-001 and REQ-VET-003
- No prohibited PRD patterns found in either document
- Domain terms Specialty and Veterinarian match ubiquitous-language.md canonical spellings
- Acceptance criteria follow given/when/then format throughout

**code-quality-reviewer**

- Static import fix applied: line 115 now uses unqualified get("/vets.html?page=1") consistent with the static import on line 40; no qualified MockMvcRequestBuilders.get(...) calls remain
- Unused MockMvcRequestBuilders import removed as a clean collateral consequence
- BDD renames applied correctly: all five new test methods follow the{Subject}Should{Outcome} convention (theSpecialtyDirectoryShouldReturnHtml, theSpecialtyDirectoryShouldGroupVeterinariansBySpecialty, theSpecialtyDirectoryShouldNameEachVeterinarianByFullName, theSpecialtyDirectoryShouldIncludeSpecialtiesHeldByNoVeterinarian, theSpecialtyDirectoryShouldOmitVeterinariansHoldingNoSpecialty)
- stringContainsInOrder("surgery", "Linda Douglas") assertion at line 146 anchors Linda Douglas to the surgery specialty heading, closing the false-positive gap
- @MockitoBean SpecialtyRepository is consistent with the pre-existing @MockitoBean VetRepository in the same file; implementer documented rationale for declining the hand-written-double upgrade (JpaRepository ~20 inherited methods; file-level consistency with VetRepository)
- checkFormat: BUILD SUCCESSFUL (format gate clean)

**test-reviewer**

- BDD renames applied verbatim: all five methods follow the{Subject}Should{Outcome} school and read as specifications independent of the production method names
- stringContainsInOrder("surgery","Linda Douglas") applied: Linda Douglas is now anchored to her specialty context rather than asserted as a free occurrence
- @MockitoBean SpecialtyRepository declination accepted on the merits: (1) a real implementation is unavailable in @WebMvcTest context (no JPA runtime); (2) JpaRepository carries ~20 inherited abstract methods so an anonymous hand-written double would be dominated by UnsupportedOperationException stubs with no specification content -- heavier and less legible than the one-line mock, not lighter, meaning the hand-written-double path does not fit; (3) VetRepository is also @MockitoBean in the same file for the same structural reason -- both are JpaRepository-extending collaborators in the same @WebMvcTest slice, so consistent doubling style within the file is correct; the policy conscious-exception clause (neither real implementation nor hand-written double fits) applies and was invoked with explicit reasoning
- All five new tests verify rendered HTML via MockMvc, covering all five acceptance criteria: HTTP 200 + model attribute + view name, grouping with deterministic vet order, full-name rendering, unheld specialty included, unspecialised vet absent
- Coverage: vet package 100% line and branch; project total 90% -- exceeds 80% domain-package target from docs/testing-principles.md
- Factory methods specialty(), vet(), james(), helen(), rafael(), linda() encapsulate all object construction -- no bare constructor calls in test bodies

**doc-reviewer**

- Applied fix verified: three over-length sentences at docs/prd.md:137 replaced by seven sentences, all under 30 words (range 8-18 words); 87.5% under 20 words, exceeding the 70% threshold
- \<a id="req-vet-003">\</a> anchor still present at docs/prd.md:135
- Design link system-design.md#contracts resolves to the ## Contracts heading (line 72 in system-design.md)
- REQ-VET-003 cross-document coherence intact: SpecialtyRepository, VetController, and Specialty rows in system-design.md Contracts table all reference REQ-VET-003
- All Done-when acceptance bullets under 30 words
- Edge case sentence (18 words) and NG-2 out-of-scope sentence (~22 words) both under 30 words
- No prohibited PRD patterns: no implementation code, no framework constructs, no internal code references
- Domain terms Specialty and Veterinarian match ubiquitous-language.md canonical spellings

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $7.61 | 13m 12s | 91% |
| `(parent)` | 1 | opus-5 | $5.67 | 34m 33s | 89% |
| `spring-boot-claude:system-design-expert` | 1 | opus-4-8 | $3.62 | 3m 55s | 76% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $3.60 | 2m 38s | 64% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $2.03 | 4m 0s | 91% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $1.75 | 6m 42s | 84% |
| `spring-boot-claude:security-reviewer` | 1 | opus-4-8 | $1.60 | 1m 3s | 73% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $1.58 | 5m 57s | 80% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $1.52 | 5m 32s | 81% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.14 | 11s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $5.67 | 34m 33s | 89% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $5.18 | 7m 28s | 92% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $3.62 | 3m 55s | 76% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $2.63 | 2m 7s | 65% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $2.42 | 5m 43s | 88% |
| `spring-boot-claude:change-grader` | opus-4-8 | $2.03 | 4m 0s | 91% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $1.60 | 1m 3s | 73% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.97 | 31s | 60% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.96 | 3m 44s | 80% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.92 | 3m 42s | 79% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.86 | 3m 44s | 80% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.79 | 2m 57s | 87% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.72 | 2m 13s | 80% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.60 | 1m 49s | 83% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.14 | 11s | 0% |

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
