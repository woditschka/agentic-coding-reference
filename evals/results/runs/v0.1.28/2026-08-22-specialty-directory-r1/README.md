# specialty-directory r1 — v0.1.28

Specialty directory page (feature) · started 2026-08-22T19:46:44+00:00 · exec `claude-dev` · status **complete**

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
| 3 (±0) | 3 (±0) | 3 (±0) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.55. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 5

> Naming and placement follow the catalog (SpecialtyController/SpecialtyRepository in the vet module), but buildDirectory() puts a real join-and-sort rule in the entry point, wiring a second repository (VetRepository) and cross-aggregate grouping into a controller — the checklist calls a new controller rule a fresh violation, and an Available domain service was the sanctioned seam. Tests are BDD-named, phase-structured, and use factories, but stub both repositories with @MockitoBean, assert on the model map rather than rendered output, and carry narration comments in setup; the untested template concatenates '${vet.firstName + ' ' + vet.lastName + ' '}' with a trailing-space hack and introduces #{specialties}/#{vets}/#{none} keys no visible file defines. Docs are thorough: PRD requirement, acceptance criteria, open questions, and updated contract rows.

**Sample 2** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 5

> SpecialtyController.buildDirectory() puts the grouping/join/ordering rule in the web layer — a fresh violation of the Web controller row, when the sanctioned Domain service (or a repository query) would make it unit-testable without booting MVC. SpecialtyRepository extends JpaRepository, exposing save/delete on a read-only, explicitly out-of-scope surface. Tests are BDD-named, use factories and collection assertions, but stub both repositories with @MockitoBean rather than real or hand-written doubles, assert on the model map instead of rendered output, and carry bare id literals (createASpecialty(1, "dentistry")). specialtyList.html references #{specialties}, #{name}, #{vets}, #{none} with no message-bundle entries added and no test covering rendering. Docs are thorough: REQ-SPC-001, open questions, and contracts rows all current.

**Sample 3** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 5

> SpecialtyController.buildDirectory() puts the inverse-index join and holder sorting inside a web controller, a fresh rule in the entry point that Application/Domain service (catalog, Available) covers — the anchor-3 'logic that belongs lower'. Tests are BDD-named (theSpecialtyDirectoryShouldShowSpecialtyWithNoVets) and use factories, but stub two internal repositories with @MockitoBean rather than real or hand-written doubles, carry Tier-3 literals (createASpecialty(1, "dentistry")), rely on a @BeforeEach mystery-guest fixture, narrate in comments, and assert only the model map — never the rendered page. That gap hides a real risk: specialtyList.html introduces #{specialties}, #{vets}, #{none} with no message-bundle change in the patch. Docs are thorough: REQ-SPC-001, done-when, edge case, two open questions, and contract rows for both new types.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $10.76 | 32m | 4 | 89% | 6 file(s) +312/−3 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.43 | 1m 15s | 83% |

## Change

<details>
<summary>Diff (rendered from <code>change.patch</code>)</summary>

```diff
diff --git a/docs/prd.md b/docs/prd.md
index 06398de..62a3eb1 100644
--- a/docs/prd.md
+++ b/docs/prd.md
@@ -130,6 +130,23 @@ The clinic publishes the veterinarians it employs with the specialties each hold
 
 **Design:** [system-design.md#contracts](system-design.md#contracts)
 
+### Specialty directory
+
+<a id="req-spc-001"></a>
+
+The clinic also publishes the specialties it knows, viewed the other way round from the veterinarian directory. Each specialty is named as it is stored and shown with the veterinarians who hold it `[REQ-SPC-001]`. Every specialty appears, and each veterinarian under one is named in full, given name before family name. A veterinarian holding no specialty appears nowhere on the page — this is a directory of specialties, not the full veterinarian roster. The whole directory renders on one page, without pagination. The page is reached directly at its own address; it carries no navigation entry, and nothing links to it.
+
+**Done when:**
+- `[REQ-SPC-001]` given the clinic's specialties, when the specialty directory is opened, then every specialty is listed by its stored name on a single page with no pagination.
+- `[REQ-SPC-001]` given a specialty held by one or more veterinarians, when the directory is opened, then each holding veterinarian is listed under it by full name, given name before family name.
+- `[REQ-SPC-001]` given a veterinarian who holds no specialty, when the directory is opened, then that veterinarian appears nowhere on the page.
+- `[REQ-SPC-001]` given a specialty held by no veterinarian, when the directory is opened, then the specialty still appears, shown with no veterinarians under it.
+
+**Edge cases:**
+1. Specialties, and the veterinarians under each, are presented in a stable order rather than an arbitrary one.
+
+**Design:** [system-design.md#contracts](system-design.md#contracts)
+
 ### Language
 
 <a id="req-lang-001"></a><a id="req-lang-002"></a>
@@ -179,3 +196,5 @@ The system opens on a landing page, and every page carries navigation to the own
 - **Is a visit really unrelated to a veterinarian?** Nothing connects the two, which makes the veterinarian directory a standalone page rather than part of the clinical workflow.
 - **Are the seeded pet types and specialties the real lists,** or placeholders?
 - **Does the project hold goals beyond being a reference sample?** G-2 is unfilled.
+- **What order should the specialty directory use?** `REQ-SPC-001` fixes the content but not the sort. Specialties, and the veterinarians under each, are shown in a stable order (edge case 1), but whether that order is alphabetical, by insertion, or another is unspecified; the narrowest reading takes any stable order.
+- **Will the specialty directory get a visible entry point?** `REQ-SPC-001` leaves the page reachable only at its own address, with no navigation entry and nothing linking to it. A visible entry point may follow as separate work.
diff --git a/docs/system-design.md b/docs/system-design.md
index 9d58a3a..c309912 100644
--- a/docs/system-design.md
+++ b/docs/system-design.md
@@ -97,11 +97,13 @@ An `Implements` value of `—` marks a contract serving no single requirement. T
 | `VisitController` | Server-rendered visit booking for a pet, rejecting non-future dates | `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` | REQ-VIS-001, REQ-VIS-002 |
 | `PetTypeFormatter` | Spring MVC formatter translating between a pet type and its display name during form binding | `src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java` | REQ-PET-001 |
 | `PetValidator` | Spring `Validator` enforcing the required-field rules for pet forms that bean validation does not cover | `src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java` | REQ-PET-001 |
-| `Vet` | Persisted veterinarian; exposes specialties sorted by name | `src/main/java/org/springframework/samples/petclinic/vet/Vet.java` | REQ-VET-001 |
-| `Specialty` | Persisted lookup value naming a veterinary specialty | `src/main/java/org/springframework/samples/petclinic/vet/Specialty.java` | REQ-VET-001 |
+| `Vet` | Persisted veterinarian; exposes specialties sorted by name | `src/main/java/org/springframework/samples/petclinic/vet/Vet.java` | REQ-VET-001, REQ-SPC-001 |
+| `Specialty` | Persisted lookup value naming a veterinary specialty | `src/main/java/org/springframework/samples/petclinic/vet/Specialty.java` | REQ-VET-001, REQ-SPC-001 |
 | `Vets` | Serialization wrapper giving the vet collection a single root element for the non-HTML representation | `src/main/java/org/springframework/samples/petclinic/vet/Vets.java` | — |
-| `VetRepository` | Spring Data repository for veterinarians; results are cached | `src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java` | REQ-VET-001 |
+| `VetRepository` | Spring Data repository for veterinarians; results are cached | `src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java` | REQ-VET-001, REQ-SPC-001 |
+| `SpecialtyRepository` | Spring Data JPA repository for specialties, returning every specialty in stored-name order, including specialties held by no veterinarian | `src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java` | REQ-SPC-001 |
 | `VetController` | Serves the paged HTML vet list and a serialized vet collection from a second route | `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` | REQ-VET-001 |
+| `SpecialtyController` | Serves the read-only HTML specialty directory at a single unpaged route, listing every specialty in stored-name order with the veterinarians holding it. Each holding veterinarian appears by full name, given-then-family, in last-name then first-name order; a specialty held by no veterinarian still appears | `src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java` | REQ-SPC-001 |
 | `CacheConfiguration` | Enables caching and declares the vet cache through the JCache API | `src/main/java/org/springframework/samples/petclinic/system/CacheConfiguration.java` | REQ-VET-001 |
 | `WebConfiguration` | Session-scoped locale resolution plus a request-parameter locale switch | `src/main/java/org/springframework/samples/petclinic/system/WebConfiguration.java` | REQ-LANG-001 |
 | `WelcomeController` | Serves the landing page | `src/main/java/org/springframework/samples/petclinic/system/WelcomeController.java` | REQ-SYS-001 |
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java
new file mode 100644
index 0000000..57b5657
--- /dev/null
+++ b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java
@@ -0,0 +1,82 @@
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
+package org.springframework.samples.petclinic.vet;
+
+import java.util.ArrayList;
+import java.util.Comparator;
+import java.util.HashMap;
+import java.util.LinkedHashMap;
+import java.util.List;
+import java.util.Map;
+
+import org.springframework.stereotype.Controller;
+import org.springframework.ui.Model;
+import org.springframework.web.bind.annotation.GetMapping;
+
+/**
+ * Serves the read-only specialty directory: every stored specialty with the veterinarians
+ * holding it.
+ */
+@Controller
+class SpecialtyController {
+
+	private static final Comparator<Vet> BY_FAMILY_THEN_GIVEN_NAME = Comparator.comparing(Vet::getLastName)
+		.thenComparing(Vet::getFirstName);
+
+	private final SpecialtyRepository specialtyRepository;
+
+	private final VetRepository vetRepository;
+
+	public SpecialtyController(SpecialtyRepository specialtyRepository, VetRepository vetRepository) {
+		this.specialtyRepository = specialtyRepository;
+		this.vetRepository = vetRepository;
+	}
+
+	@GetMapping("/specialties.html")
+	public String showSpecialtyList(Model model) {
+		model.addAttribute("specialties", buildDirectory());
+		return "vets/specialtyList";
+	}
+
+	/**
+	 * Builds an ordered directory keyed by the {@link Specialty} entity: specialties in
+	 * stored-name order, each mapped to its holding veterinarians in
+	 * family-then-given-name order, or an empty list when no veterinarian holds the
+	 * specialty. The complete set comes from {@link SpecialtyRepository} — a specialty
+	 * held by no vet is absent from the vet graph — and holders are joined by specialty
+	 * id, since the separately cached vet and specialty reads yield distinct instances.
+	 */
+	private Map<Specialty, List<Vet>> buildDirectory() {
+		Map<Specialty, List<Vet>> directory = new LinkedHashMap<>();
+		Map<Integer, List<Vet>> holdersBySpecialtyId = new HashMap<>();
+		for (Specialty specialty : this.specialtyRepository.findSpecialties()) {
+			List<Vet> holders = new ArrayList<>();
+			directory.put(specialty, holders);
+			holdersBySpecialtyId.put(specialty.getId(), holders);
+		}
+		for (Vet vet : this.vetRepository.findAll()) {
+			for (Specialty held : vet.getSpecialties()) {
+				List<Vet> holders = holdersBySpecialtyId.get(held.getId());
+				if (holders != null) {
+					holders.add(vet);
+				}
+			}
+		}
+		directory.values().forEach(holders -> holders.sort(BY_FAMILY_THEN_GIVEN_NAME));
+		return directory;
+	}
+
+}
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java
new file mode 100644
index 0000000..898e905
--- /dev/null
+++ b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java
@@ -0,0 +1,36 @@
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
+	 * Retrieve all {@link Specialty Specialties} from the data store, ordered by name.
+	 * @return a list of {@link Specialty Specialties}
+	 */
+	@Query("SELECT s FROM Specialty s ORDER BY s.name")
+	List<Specialty> findSpecialties();
+
+}
diff --git a/src/main/resources/templates/vets/specialtyList.html b/src/main/resources/templates/vets/specialtyList.html
new file mode 100644
index 0000000..058ffb7
--- /dev/null
+++ b/src/main/resources/templates/vets/specialtyList.html
@@ -0,0 +1,28 @@
+<!DOCTYPE html>
+
+<html xmlns:th="https://www.thymeleaf.org" th:replace="~{fragments/layout :: layout (~{::body},'vets')}">
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
+      <tr th:each="entry : ${specialties}">
+        <td th:text="${entry.key.name}"></td>
+        <td>
+          <span th:each="vet : ${entry.value}" th:text="${vet.firstName + ' ' + vet.lastName + ' '}" /> <span
+            th:if="${entry.value.isEmpty()}" th:text="#{none}">none</span>
+        </td>
+      </tr>
+    </tbody>
+  </table>
+</body>
+
+</html>
diff --git a/src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java b/src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java
new file mode 100644
index 0000000..537ae5f
--- /dev/null
+++ b/src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java
@@ -0,0 +1,142 @@
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
+import static org.assertj.core.api.Assertions.assertThat;
+import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.model;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.view;
+
+import java.util.List;
+import java.util.Map;
+
+import org.junit.jupiter.api.BeforeEach;
+import org.junit.jupiter.api.Test;
+import org.junit.jupiter.api.condition.DisabledInNativeImage;
+import org.springframework.beans.factory.annotation.Autowired;
+import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
+import org.springframework.test.context.aot.DisabledInAotMode;
+import org.springframework.test.context.bean.override.mockito.MockitoBean;
+import org.springframework.test.web.servlet.MockMvc;
+import org.springframework.test.web.servlet.MvcResult;
+
+import static org.mockito.BDDMockito.given;
+
+/**
+ * Test class for the {@link SpecialtyController}.
+ */
+@WebMvcTest(SpecialtyController.class)
+@DisabledInNativeImage
+@DisabledInAotMode
+class SpecialtyControllerTests {
+
+	@Autowired
+	private MockMvc mockMvc;
+
+	@MockitoBean
+	private SpecialtyRepository specialties;
+
+	@MockitoBean
+	private VetRepository vets;
+
+	private Specialty createASpecialty(int id, String name) {
+		Specialty specialty = new Specialty();
+		specialty.setId(id);
+		specialty.setName(name);
+		return specialty;
+	}
+
+	private Vet createAVet(int id, String firstName, String lastName, Specialty... held) {
+		Vet vet = new Vet();
+		vet.setId(id);
+		vet.setFirstName(firstName);
+		vet.setLastName(lastName);
+		for (Specialty specialty : held) {
+			vet.addSpecialty(specialty);
+		}
+		return vet;
+	}
+
+	@BeforeEach
+	void setup() {
+		// Directory keys: distinct instances from the vets' specialties, mirroring the
+		// separately cached findSpecialties()/findAll() reads in production. Name order.
+		given(this.specialties.findSpecialties()).willReturn(List.of(createASpecialty(1, "dentistry"),
+				createASpecialty(2, "radiology"), createASpecialty(3, "surgery")));
+
+		// radiology (id 2) is held by two vets; James Carter holds nothing; surgery and
+		// dentistry are held by nobody. Vet specialties are fresh instances joined by id.
+		Vet james = createAVet(1, "James", "Carter");
+		Vet helen = createAVet(2, "Helen", "Leary", createASpecialty(2, "radiology"));
+		Vet linda = createAVet(3, "Linda", "Douglas", createASpecialty(2, "radiology"));
+		given(this.vets.findAll()).willReturn(List.of(james, helen, linda));
+	}
+
+	@SuppressWarnings("unchecked")
+	private Map<Specialty, List<Vet>> directoryFor(String path) throws Exception {
+		MvcResult result = mockMvc.perform(get(path))
+			.andExpect(status().isOk())
+			.andExpect(view().name("vets/specialtyList"))
+			.andExpect(model().attributeExists("specialties"))
+			.andReturn();
+		return (Map<Specialty, List<Vet>>) result.getModelAndView().getModel().get("specialties");
+	}
+
+	private List<Vet> holdersOf(Map<Specialty, List<Vet>> directory, String specialtyName) {
+		return directory.entrySet()
+			.stream()
+			.filter(entry -> specialtyName.equals(entry.getKey().getName()))
+			.map(Map.Entry::getValue)
+			.findFirst()
+			.orElseThrow();
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldListEverySpecialtyByStoredName() throws Exception {
+		Map<Specialty, List<Vet>> directory = directoryFor("/specialties.html");
+
+		assertThat(directory.keySet()).extracting(Specialty::getName)
+			.containsExactly("dentistry", "radiology", "surgery");
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldListHoldingVetsByFullName() throws Exception {
+		Map<Specialty, List<Vet>> directory = directoryFor("/specialties.html");
+
+		// Full name is given-then-family; deterministic order is family-then-given, so
+		// Douglas precedes Leary.
+		assertThat(holdersOf(directory, "radiology")).extracting(vet -> vet.getFirstName() + " " + vet.getLastName())
+			.containsExactly("Linda Douglas", "Helen Leary");
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldOmitVetWithoutSpecialty() throws Exception {
+		Map<Specialty, List<Vet>> directory = directoryFor("/specialties.html");
+
+		assertThat(directory.values())
+			.allSatisfy(holders -> assertThat(holders).noneMatch(vet -> "Carter".equals(vet.getLastName())));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldShowSpecialtyWithNoVets() throws Exception {
+		Map<Specialty, List<Vet>> directory = directoryFor("/specialties.html");
+
+		assertThat(holdersOf(directory, "surgery")).isEmpty();
+	}
+
+}
```

</details>

## Pipeline

### REQ-SPC-001 — Reader can browse the clinic's specialties and the veterinarians holding each

2 review rounds · 2 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (2) | **✔** |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | ✎ (4) | **✔** |

- ◇ **prd-entry** Reader can browse the clinic's specialties and the veterinarians holding each · (prd-expert) · ***◷ 31s***
- ◈ **design-block** **new** · (design) · ***◷ 46s***
- ◆ **implement** (implementer) · ***◷ 6m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 25s***
- ◆ **implement** (implementer) · ***◷ 36s***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 21s***
- ✎ **review code-quality** · **changes_requested** · (2 findings) · ***◷ 3m***
  - [autofix] `SpecialtyControllerTests.java:111,119,` All four test methods are named `specialtyDirectoryShould*` but the project's BDD naming school (testing-principles.md § Test Naming) requires the `the` prefix: `the{Subject}Should{Outcome}`. These tests are new (written from 2026-07-31 onward) so the convention applies. All four instances confirmed by sweep.
    - fix: Rename each method: `theSpecialtyDirectoryShouldListEverySpecialtyByStoredName`, `theSpecialtyDirectoryShouldListHoldingVetsByFullName`, `theSpecialtyDirectoryShouldOmitVetWithoutSpecialty`, `theSpecialtyDirectoryShouldShowSpecialtyWithNoVets`.
  - [autofix] `SpecialtyControllerTests.java:81,88` `org.assertj.core.util.Lists.newArrayList` is imported and used to build fixture data in `setup()`. This is an internal AssertJ utility class repurposed outside of assertions. Idiomatic Java 9+ is `List.of(...)`, which also satisfies Mockito's `willReturn`. Both call sites confirmed by sweep.
    - fix: Replace both `Lists.newArrayList(...)` calls with `List.of(...)` and remove the `import org.assertj.core.util.Lists;` import.
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 3m***
  - [autofix] `SpecialtyControllerTests.java:111,119,` All four test method names are missing the mandatory `the` prefix required by the brief's BDD naming school (`the{Subject}Should{Outcome}`). Current names: `specialtyDirectoryShouldList...`, `specialtyDirectoryShouldOmit...`, `specialtyDirectoryShouldShow...`. Each should begin with `the`.
    - fix: Rename all four methods: `theSpecialtyDirectoryShouldListEverySpecialtyByStoredName`, `theSpecialtyDirectoryShouldListHoldingVetsByFullName`, `theSpecialtyDirectoryShouldOmitVetWithoutSpecialty`, `theSpecialtyDirectoryShouldShowSpecialtyWithNoVets`.
  - [autofix] `SpecialtyControllerTests.java:58,65` Factory helper methods `specialty()` and `vet()` do not use the `createA/An` prefix mandated by the brief's factory method naming convention (§ Test Data Construction). The brief applies this to tests written from 2026-07-31 onward; this file is new.
    - fix: Rename `specialty(int id, String name)` to `createASpecialty(int id, String name)` and `vet(int id, String firstName, String lastName, Specialty... held)` to `createAVet(int id, String firstName, String lastName, Specialty... held)`. Update all call sites in the same file.
- ✎ **review doc** · **changes_requested** · (4 findings) · ***◷ 7m***
  - **[blocked]** `prd.md:147` Edge case 2 in the Specialty directory section is a non-goal restatement, not a behavioral scenario. The prd-authoring skill defines numbered edge cases as citable items each with a dedicated test; the test-reviewer checks each number has a corresponding test. The content—'The directory has no navigation entry and no page links to it; it is reached only at its own address. A visible entry point is out of scope here and may follow separately.'—is already stated in the narrative prose (line 137) and further discussed in the Open Questions (lines 200-201). No controller test can assert 'no page links to this URL.' Per review-checks.md, edge-case items are never autofix-eligible on the PRD path; this routes to the product-requirements-expert. Fix: remove item 2 from the Edge cases list. Edge case 1 (stable order) is correct and unaffected.
  - **[blocked]** `prd.md:137` The first sentence of the REQ-SPC-001 narrative is approximately 33 words, exceeding the 30-word writing standard (review-checks.md §4). Sentence: 'The clinic also publishes the specialties it knows, viewed the other way round from the veterinarian directory: each specialty is named as it is stored and shown with the veterinarians who hold it [REQ-SPC-001].' The replacement text exceeds the 200-character autofix bound for the PRD path, so this routes to the product-requirements-expert. Fix: split at the colon into two sentences, each under 30 words.
  - **[blocked]** `system-design.md:106` The SpecialtyController Contracts row Purpose column is a single sentence of approximately 38 words, exceeding the 30-word writing standard (review-checks.md §4). Comparable rows use shorter descriptions or two sentences (e.g., OwnerRepository). The replacement text exceeds the 200-character autofix bound for design-doc paths, so this routes to the system-design-expert (review-checks.md §Autofix on Design-Doc Paths). Fix: restructure into two sentences, each under 30 words, preserving the behavioral content.
  - **[blocked]** `system-design.md:104` The SpecialtyRepository Contracts row Purpose column contains an inline rationale clause: 'which the vet graph alone cannot supply.' This clause explains why the repository is necessary (the vet graph cannot supply unheld specialties), not what the repository does. Per review-checks.md Prohibited Patterns, why-explanations in system-design.md are prohibited; the Contracts table carries behavioral descriptions, not design rationale. The fix is not autofix-eligible on design-doc paths (prohibited-pattern category). Routes to system-design-expert. Fix: remove the clause; the behavioral description 'returning every specialty in stored-name order, including specialties held by no veterinarian' stands on its own.
- ↻ **implement** (implementer) ← code-quality, test · (4 findings)
- ↻ **fix design** ← doc · (4 findings)
- ↻ **fix prd-expert** ← doc · (4 findings)
- ◈ **design-block** **new** · (design) · supersedes L8 · ***◷ 47s***
- ◇ **prd-entry** Reader can browse the clinic's specialties and the veterinarians holding each · (prd-expert) · ***◷ 57s***
- ▲ **build-pass** 20:15 · build, test, format, handoff-log, autofix-audit
- • review-plan (review-plan-engine)
- ↻ **fix code-quality** ← doc · (4 findings)
- ↻ **fix doc** ← doc · (4 findings)
- ✔ **review doc** · **approved** · ***◷ 57s***
- ✔ **review security** · **approved** · ***◷ 6s***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ✔ **review test** · **approved** · ***◷ 1m***
- ◆ **grade CLEAR** · add read-only specialty directory page
  - blast_radius — **clear** — Additive change contained in the vet module: one new controller, repository, template, and test, plus two doc rows. No sensitive paths, 9 hunks, no deletions to existing production code.
  - semantic_surprise — **clear** — Controller joins vets to specialties by specialty id (guarding for distinct cached instances), sorts specialties by JPQL ORDER BY name and holders family-then-given; display is given-then-family. Behavior matches the requirement with no hidden surprise.
  - test_adequacy — **clear** — Four WebMvcTest cases assert real outcomes (containsExactly name order, Douglas-before-Leary holder order, Carter omitted, empty surgery) exercising the real buildDirectory join; mocks sit only at the repository boundary, a sanctioned web-harness exception. Build green.
  - reviewer_hedging — **clear** — Full four-reviewer battery (code-quality, test, security, doc) all approved in R2 with empty findings lists; no escalate, no reworked bar clause, no lingering caveat.
  - scope_deviation — **clear** — design_revisions=2 with zero retries and zero consultations; diff stays on the specialty-directory surface. Implementation used dedicated SpecialtyController/Repository instead of the PRD's tentative VetController targets — a reasonable in-scope structural choice.
  - why — Contained, additive feature; the controller's cache-safe id join and deterministic sorting read exactly as the requirement states, tests assert real outcomes, and the full reviewer battery approved cleanly. Safe to confirm and merge with a fast read of SpecialtyController.buildDirectory.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- No user input on any code path: GET /specialties.html takes no request parameters or path variables; the controller only reads repositories and assembles a LinkedHashMap\<Specialty,List\<Vet>> — no injection, path-traversal, or deserialization surface
- SpecialtyRepository uses a parameterless JPQL @Query (SELECT s FROM Specialty s ORDER BY s.name) with no user-derived input — no SQL/JPQL injection
- Template vets/specialtyList.html renders all dynamic content (specialty name, vet full names) via auto-escaping th:text; no th:utext, no JS/attribute inlining — no XSS
- Data exposure limited to specialty and veterinarian names, already public via the existing vet directory; no PII or secret escalation
- No hardcoded secrets introduced
- No supply-chain surface: no build.gradle change and no new or updated dependencies in the change set

**code-quality-reviewer**

- Format checks pass ( checkFormatMain ,  checkFormatTest  both green)
- SpecialtyRepository: clean parameterless JPQL with no user input or injection surface
- SpecialtyController: package-private, constructor injection without @Autowired, single responsibility
- buildDirectory() Javadoc explains the two-pass shared-reference design and id-based join — non-obvious structure is well-documented for the next reader
- All Thymeleaf output uses th:text (auto-escaping) throughout the template
- All four message keys used in specialtyList.html (specialties, name, vets, none) are present in messages.properties
- Template correctly delegates charset to the layout fragment
- Test factory methods specialty() and vet() follow the construction-behind-factory-methods principle
- Four-phase test structure is clean with blank-line separators and no phase comments

**test-reviewer**

- All four acceptance criteria from REQ-SPC-001 are covered by dedicated tests that map 1-to-1 to the Done-When clauses
- Edge case 1 (stable order of specialties and holding vets) is exercised via containsExactly in both name-order and vet-order assertions
- AssertJ used fluently throughout; no JUnit-style assertions; collection assertions use containsExactly and isEmpty correctly
- SpecialtyController achieves 100% line coverage and 87% branch coverage (above the 80% line target); the one missed branch is the defensive null guard in buildDirectory() for a data-inconsistency scenario not documented in system-design.md
- Mocking policy: @MockitoBean on SpecialtyRepository and VetRepository follows the pre-existing VetControllerTests pattern in the same package; the brief explicitly tolerates existing mock-framework usage; @WebMvcTest cannot load real JPA infrastructure so real implementations do not fit here — the follow-for-consistency reading holds and this is not a new introduction of the mock pattern
- Four-phase structure is clean; @BeforeEach carries Arrange, test bodies are straight-line Act+Assert separated by a blank line
- No JUnit assertEquals/assertTrue present; no branching or loops in test bodies; tests are independent

**doc-reviewer**

- HTML anchor \<a id="req-spc-001">\</a> is present and correctly placed before the narrative
- PRD narrative uses behavioral prose only; no Java constructs, pseudocode, or code references
- Done when bullets follow given/when/then form, are bounded, and cover all four acceptance criteria
- Edge case 1 (stable order) is a legitimate behavioral scenario implying a testable ordering constraint
- Cross-reference system-design.md#contracts resolves to the Contracts heading at line 72
- All five REQ-SPC-001 Implements mappings in system-design.md (Vet, Specialty, VetRepository, SpecialtyRepository, SpecialtyController) are internally coherent and match the PRD
- Source paths in both new Contracts rows match the primary_paths in the covering design-block (line 8)
- Domain terms Specialty and Veterinarian match ubiquitous-language.md canonical spellings
- Two new Open Questions entries are appropriately placed and correctly reference REQ-SPC-001
- No prohibited rationale prose in PRD; no mechanism leaking into PRD narrative

**doc-reviewer**

- R1 finding 1 resolved: edge case 2 (non-goal restatement) removed from prd.md Specialty directory Edge cases list; only the testable stable-order item remains
- R1 finding 2 resolved: narrative first sentence split at the colon into two sentences of 18 and 17 words respectively, both under the 30-word limit; [REQ-SPC-001] tag retained in the second sentence
- R1 finding 3 resolved: SpecialtyController Contracts Purpose split into two sentences of 22 and 21 words, both under 30 words, behavioral content preserved
- R1 finding 4 resolved: prohibited rationale clause 'which the vet graph alone cannot supply' removed from SpecialtyRepository Purpose; behavioral description stands alone
- No new word-count violations introduced in either document
- Cross-reference system-design.md#contracts in prd.md still resolves
- REQ-SPC-001 Implements mappings updated to include Vet, Specialty, VetRepository, SpecialtyRepository, SpecialtyController — all coherent with PRD acceptance criteria
- No inline rationale or prohibited how-explanation introduced in the revised rows

**security-reviewer**

- R2 fix delta since R1 touches only SpecialtyControllerTests.java (test rename/refactor) and docs/prd.md, docs/system-design.md — no production code or dependency changes, so no new attack surface
- SpecialtyRepository.findSpecialties uses a static parameterless JPQL query (SELECT s FROM Specialty s ORDER BY s.name) — no user input, no injection surface
- SpecialtyController.showSpecialtyList maps GET /specialties.html with only a Model argument and no request parameters; no user-controlled input reaches any repository, view, or sink
- specialtyList.html renders all dynamic values (specialty name, vet names) through auto-escaping th:text with no th:utext — no stored/reflected XSS
- No secrets, deserialization sinks, path/file I/O, or auth-boundary changes introduced; read-only public directory consistent with the existing vets listing
- No dependency or framework-version changes since R1 — supply-chain posture unchanged

**code-quality-reviewer**

- R1 finding 1 resolved: all four test methods now carry the mandatory 'the' BDD prefix — theSpecialtyDirectoryShouldListEverySpecialtyByStoredName, theSpecialtyDirectoryShouldListHoldingVetsByFullName, theSpecialtyDirectoryShouldOmitVetWithoutSpecialty, theSpecialtyDirectoryShouldShowSpecialtyWithNoVets
- R1 finding 2 resolved: org.assertj.core.util.Lists import dropped; all data construction in @BeforeEach uses List.of
- Factory helpers correctly renamed to createASpecialty / createAVet per testing-principles factory-method naming convention; all call sites updated
- No regressions introduced in the fix delta; production code (SpecialtyController, SpecialtyRepository, specialtyList.html) unchanged and passes prior code-quality bar

**test-reviewer**

- R1 finding 1 resolved: all four test methods now carry the mandatory 'the' BDD prefix (theSpecialtyDirectoryShouldListEverySpecialtyByStoredName, theSpecialtyDirectoryShouldListHoldingVetsByFullName, theSpecialtyDirectoryShouldOmitVetWithoutSpecialty, theSpecialtyDirectoryShouldShowSpecialtyWithNoVets)
- R1 finding 2 resolved: factory helpers renamed from specialty()/vet() to createASpecialty()/createAVet() with all call sites updated
- All four acceptance criteria have a dedicated test: AC1 stored-name listing, AC2 full-name holder display, AC3 no-specialty vet omission, AC4 unheld specialty appears with empty holder list
- Deterministic ordering (AC5) asserted via containsExactly in both the stored-name and holder-order tests
- AssertJ fluent assertions used throughout; no JUnit assertEquals or assertTrue
- Four-phase structure observed in each test method with phases separated by blank lines
- Factory method discipline maintained: createASpecialty and createAVet wrap all object construction
- @WebMvcTest with @MockitoBean for repositories is within the brief's tolerated mock-framework exception for the in-process web test harness
- All four tests pass: BUILD SUCCESSFUL

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 3 | opus-4-8 | $2.63 | 10m 10s | 93% |
| `(parent)` | 1 | opus-4-8 | $1.79 | 32m 49s | 96% |
| `spring-boot-claude:system-design-expert` | 3 | opus-4-8 | $1.76 | 4m 58s | 83% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $1.16 | 3m 50s | 86% |
| `spring-boot-claude:security-reviewer` | 2 | opus-4-8 | $0.96 | 1m 43s | 76% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $0.89 | 8m 19s | 84% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $0.71 | 4m 56s | 89% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $0.65 | 5m 10s | 83% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $0.43 | 1m 15s | 83% |
| `spring-boot-claude:pipeline-coordinator` | 2 | sonnet-4-6 | $0.17 | 32s | 56% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-4-8 | $1.79 | 32m 49s | 96% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.56 | 6m 49s | 94% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $0.90 | 2m 50s | 86% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.69 | 7m 14s | 85% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.64 | 2m 22s | 87% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $0.63 | 2m 13s | 90% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.51 | 1m 28s | 85% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.49 | 1m 3s | 81% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.47 | 39s | 70% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $0.46 | 1m 6s | 77% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.46 | 3m 16s | 91% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $0.43 | 1m 7s | 91% |
| `spring-boot-claude:change-grader` | opus-4-8 | $0.43 | 1m 15s | 83% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.41 | 3m 10s | 84% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $0.40 | 1m 1s | 81% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.25 | 1m 39s | 84% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.25 | 1m 59s | 81% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.20 | 1m 4s | 82% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.10 | 19s | 60% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.07 | 13s | 50% |

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

- plugin `spring-boot-claude` at `v0.1.28` (tag)
- model requested `claude-opus-4-8`; models used: opus-4-8 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
