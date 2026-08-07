# specialty-directory r1 — v0.1.1

Specialty directory page (feature) · started 2026-08-05T11:35:17+00:00 · exec `claude-dev` · status **complete**

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
| review attention (pipeline grade) | — |

- ✔ `theSpecialtyDirectoryShouldListEverySeededSpecialty` — passed
- ✔ `theSpecialtyDirectoryShouldNameTheVetsHoldingEachSpecialty` — passed
- ✔ `theSpecialtyDirectoryShouldRender` — passed
- ✔ `theVetDirectoryShouldRenderTheSeededVets` — passed

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 3 (±0) | 3 (±1) | 3 (±0) | 3 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.52. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 3 · test-quality 4 · maintainability 3 · doc-fit 3

> SpecialtyController.buildDirectory/invertVetSpecialties put the inversion, sorting and full-name composition rules in the web layer — the checklist forbids new controller rules, and the sanctioned Domain service pattern was available without an ADR; SpecialtyRepository, the record view model and package placement are otherwise idiomatic. Tests name behavior well (theSpecialtyDirectoryShouldOmitVeterinariansHoldingNoSpecialty) and use factories, but @BeforeEach hides the driving data, meaningful literals ("radiology") are unnamed, comments narrate ("// Full name is \"first last\"..."), and pure inversion logic is exercised only through MockMvc. specialtyList.html references #{specialties} and #{none}, yet no messages bundle entry is added, so headings render as missing keys. The PRD gains REQ-SPEC-001 but its "Design: system-design.md#contracts" link points at a contracts section the patch never updates for /specialties.html.

**Sample 2** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 3

> SpecialtyRepository and the vet-package placement fit the catalog, but SpecialtyController.buildDirectory/invertVetSpecialties put the inversion, ordering and full-name rules in the controller — the checklist's 'no business rule added to a web controller' bar, and a sanctioned Domain service was available; the same logic is unit-testable without the framework, yet every test boots MockMvc. Tests name behavior well (theSpecialtyDirectoryShould...) and use factories, but stub two internal repositories with @MockitoBean, share one mutable @BeforeEach fixture across all five tests, narrate assertions ('so Douglas precedes Leary'), and leave literals like "radiology", "Linda Douglas", hasSize(3) unnamed and underived. specialtyList.html references #{specialties}/#{none} with no message properties added, and reuses one key for two labels; the PRD hunk points to system-design.md#contracts, which gains no entry.

**Sample 3** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 3

> SpecialtyController.buildDirectory/invertVetSpecialties put the whole inverse-view rule — association inversion, last-then-first ordering, full-name composition — in a web controller, which the catalog's Web controller row and the checklist item 'No business rule added to a web controller' forbid; an available Domain service was the sanctioned seam. Repository, record, and package placement are otherwise idiomatic. Tests are BDD-named and cover empty-holder, no-specialty, and no-pagination edges, but use @MockitoBean stubs over real/hand-written doubles, share a mutable @BeforeEach fixture, narrate with comments ('// Full name is "first last"...'), and leave literals like "radiology" unnamed. specialtyList.html references #{specialties}/#{vets}/#{none} with no message-bundle entry in the patch, plus an unchecked cast in listings(). PRD REQ-SPEC-001 is added but points at system-design.md#contracts, which never gains the new endpoint.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $6.52 | 20m | 20 | 83% | 6 file(s) +332/−0 |

## Change

<details>
<summary>Diff (rendered from <code>change.patch</code>)</summary>

```diff
diff --git a/docs/prd.md b/docs/prd.md
index 0cb7f37..e1fdcda 100644
--- a/docs/prd.md
+++ b/docs/prd.md
@@ -130,6 +130,26 @@ The clinic publishes the veterinarians it employs with the specialties each hold
 
 **Design:** [system-design.md#contracts](system-design.md#contracts)
 
+### Specialty directory
+
+<a id="req-spec-001"></a>
+
+Alongside the veterinarian directory, which answers "which specialties does this veterinarian hold", the clinic publishes the inverse view, answering "which veterinarians hold this specialty". The specialty directory lists every specialty the clinic knows by its stored name. Under each specialty it shows the veterinarians who hold it, each by full name — first name then last name. Every specialty appears on a single page. A veterinarian who holds no specialty is not listed here. The page is organised by specialty, not by veterinarian, so it lists specialties rather than the full veterinarian roster `[REQ-SPEC-001]`.
+
+**Done when:**
+- `[REQ-SPEC-001]` given the clinic's specialties, when the specialty directory is opened, then every specialty is listed by its stored name with the veterinarians holding it.
+- `[REQ-SPEC-001]` given a veterinarian who holds a specialty, when the directory is opened, then that veterinarian appears under that specialty by full name, first name then last name.
+- `[REQ-SPEC-001]` given a veterinarian who holds no specialty, when the directory is opened, then that veterinarian is not listed.
+- `[REQ-SPEC-001]` given the clinic's specialties, when the directory is opened, then all specialties appear on one page with no pagination.
+
+**Edge cases:**
+1. A specialty held by no veterinarian is still listed, with no veterinarians shown under it.
+2. Specialties, and the veterinarians within each specialty, are presented in a stable order rather than an arbitrary one.
+
+This is a read-only view of the existing directory; managing veterinarians or their specialties through the application stays out of scope (NG-2, unchanged).
+
+**Design:** [system-design.md#contracts](system-design.md#contracts)
+
 ### Language
 
 <a id="req-lang-001"></a><a id="req-lang-002"></a>
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java
new file mode 100644
index 0000000..a9a3d1e
--- /dev/null
+++ b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java
@@ -0,0 +1,85 @@
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
+import java.util.LinkedHashMap;
+import java.util.List;
+import java.util.Map;
+
+import org.springframework.stereotype.Controller;
+import org.springframework.ui.Model;
+import org.springframework.web.bind.annotation.GetMapping;
+
+/**
+ * Serves the specialty directory: the inverse of the veterinarian directory, listing
+ * every specialty with the veterinarians holding it.
+ *
+ * <p>
+ * The {@code vet_specialties} association is unidirectional — {@link Vet} owns it and
+ * {@link Specialty} has no back-reference — so the inverse view is assembled here by
+ * inverting each vet's {@link Vet#getSpecialties()} and grouping by specialty name. The
+ * complete specialty list comes from {@link SpecialtyRepository}, so a specialty held by
+ * no veterinarian is still listed.
+ */
+@Controller
+class SpecialtyController {
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
+		model.addAttribute("listSpecialties", buildDirectory());
+		return "specialties/specialtyList";
+	}
+
+	private List<SpecialtyListing> buildDirectory() {
+		Map<String, List<String>> holdersBySpecialtyName = invertVetSpecialties();
+		List<SpecialtyListing> directory = new ArrayList<>();
+		for (Specialty specialty : this.specialtyRepository.findSpecialties()) {
+			List<String> holders = holdersBySpecialtyName.getOrDefault(specialty.getName(), List.of());
+			directory.add(new SpecialtyListing(specialty.getName(), holders));
+		}
+		return directory;
+	}
+
+	/**
+	 * Invert the vet-owned associations into a specialty-name → holder-full-names map.
+	 * Vets are visited in last-then-first order, so each specialty's holder list is
+	 * ordered the same way.
+	 */
+	private Map<String, List<String>> invertVetSpecialties() {
+		List<Vet> vets = new ArrayList<>(this.vetRepository.findAll());
+		vets.sort(Comparator.comparing(Vet::getLastName).thenComparing(Vet::getFirstName));
+		Map<String, List<String>> holdersBySpecialtyName = new LinkedHashMap<>();
+		for (Vet vet : vets) {
+			String fullName = vet.getFirstName() + " " + vet.getLastName();
+			for (Specialty specialty : vet.getSpecialties()) {
+				holdersBySpecialtyName.computeIfAbsent(specialty.getName(), name -> new ArrayList<>()).add(fullName);
+			}
+		}
+		return holdersBySpecialtyName;
+	}
+
+}
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyListing.java b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyListing.java
new file mode 100644
index 0000000..c173f02
--- /dev/null
+++ b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyListing.java
@@ -0,0 +1,28 @@
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
+import java.util.List;
+
+/**
+ * View model for one row of the specialty directory: a specialty by its stored name and
+ * the full names of the veterinarians holding it (empty when no veterinarian holds it).
+ *
+ * @param name the specialty's stored name
+ * @param veterinarians the holders' full names ("first last"), ordered last-then-first
+ */
+record SpecialtyListing(String name, List<String> veterinarians) {
+}
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java
new file mode 100644
index 0000000..8c2872a
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
+	 * This is the authoritative, complete specialty list: it includes specialties held by
+	 * no veterinarian, which grouping veterinarians alone would omit.
+	 * @return a name-ordered {@link List} of {@link Specialty Specialties}.
+	 */
+	@Query("SELECT specialty FROM Specialty specialty ORDER BY specialty.name")
+	List<Specialty> findSpecialties();
+
+}
diff --git a/src/main/resources/templates/specialties/specialtyList.html b/src/main/resources/templates/specialties/specialtyList.html
new file mode 100644
index 0000000..a637048
--- /dev/null
+++ b/src/main/resources/templates/specialties/specialtyList.html
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
+        <th th:text="#{specialties}">Specialty</th>
+        <th th:text="#{vets}">Veterinarians</th>
+      </tr>
+    </thead>
+    <tbody>
+      <tr th:each="specialty : ${listSpecialties}">
+        <td th:text="${specialty.name}"></td>
+        <td>
+          <span th:each="veterinarian : ${specialty.veterinarians}" th:text="${veterinarian + ' '}" /> <span
+            th:if="${#lists.isEmpty(specialty.veterinarians)}" th:text="#{none}">none</span>
+        </td>
+      </tr>
+    </tbody>
+  </table>
+</body>
+
+</html>
diff --git a/src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java b/src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java
new file mode 100644
index 0000000..1f580c4
--- /dev/null
+++ b/src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java
@@ -0,0 +1,134 @@
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
+import static org.assertj.core.api.Assertions.assertThat;
+import static org.hamcrest.Matchers.hasSize;
+import static org.mockito.BDDMockito.given;
+import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.model;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.view;
+
+/**
+ * Test class for the {@link SpecialtyController}, the inverse-of-vets specialty
+ * directory.
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
+	@BeforeEach
+	void setup() {
+		// Authoritative, name-ordered specialty list. dentistry is held by no vet.
+		given(this.specialties.findSpecialties())
+			.willReturn(List.of(specialty("dentistry"), specialty("radiology"), specialty("surgery")));
+		// James Carter holds no specialty; radiology is held by two vets.
+		given(this.vets.findAll()).willReturn(List.of(vet("James", "Carter"), vet("Helen", "Leary", "radiology"),
+				vet("Linda", "Douglas", "radiology"), vet("Rafael", "Ortega", "surgery")));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldListEverySpecialtyByStoredName() throws Exception {
+		MvcResult result = mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(view().name("specialties/specialtyList"))
+			.andReturn();
+
+		assertThat(listings(result)).extracting(SpecialtyListing::name)
+			.containsExactly("dentistry", "radiology", "surgery");
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldShowVeterinariansByFullName() throws Exception {
+		MvcResult result = mockMvc.perform(get("/specialties.html")).andExpect(status().isOk()).andReturn();
+
+		// Full name is "first last"; within a specialty vets are ordered last-then-first,
+		// so Douglas precedes Leary.
+		assertThat(listingFor(result, "radiology").veterinarians()).containsExactly("Linda Douglas", "Helen Leary");
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldOmitVeterinariansHoldingNoSpecialty() throws Exception {
+		MvcResult result = mockMvc.perform(get("/specialties.html")).andExpect(status().isOk()).andReturn();
+
+		assertThat(listings(result)).flatExtracting(SpecialtyListing::veterinarians).doesNotContain("James Carter");
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldListSpecialtiesHeldByNoVeterinarian() throws Exception {
+		MvcResult result = mockMvc.perform(get("/specialties.html")).andExpect(status().isOk()).andReturn();
+
+		assertThat(listingFor(result, "dentistry").veterinarians()).isEmpty();
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(model().attribute("listSpecialties", hasSize(3)))
+			.andExpect(model().attributeDoesNotExist("totalPages", "currentPage", "totalItems"));
+	}
+
+	@SuppressWarnings("unchecked")
+	private List<SpecialtyListing> listings(MvcResult result) {
+		return (List<SpecialtyListing>) result.getModelAndView().getModel().get("listSpecialties");
+	}
+
+	private SpecialtyListing listingFor(MvcResult result, String name) {
+		return listings(result).stream().filter(listing -> listing.name().equals(name)).findFirst().orElseThrow();
+	}
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
+}
```

</details>

## Pipeline

### REQ-SPEC-001 — Specialty directory page

1 review round · 1 build-pass · no grade yet

| reviewer | R1 |
| --- | --- |
| **code-quality** | ✎ (1) |
| **test** | **✔** (1) |
| **security** | **✔** |
| **doc** | ✎ (1) |

- ◇ **prd-entry** Specialty directory page · (prd-expert) · ***◷ 0s***
- ◈ **design-block** **minor** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 15m***
  - ▲ **build ✓ clean** · build · test · format · check
- ✔ **review security** · **approved**
- ✎ **review code-quality** · **changes_requested** · (1 finding) · ***◷ 5m***
  - **[escalate]** `specialtyList.html:12` Column 1 header uses #{specialties} (renders "Specialties") as the label for the specialty-name column. Semantically the correct column header is "Specialty" (singular), matching the one-row-per-specialty table structure. The implementer deliberately reused the existing key to avoid adding a new key across all eleven messages_*.properties bundles (REQ-LANG-002 language-parity test). Human sign-off is needed: accept the plural label as-is, or absorb the i18n parity churn to introduce a #{specialty} singular key.
- ✔ **review test** · **approved** · (1 finding) · ***◷ 5m***
  - **[escalate]** `README.md` The test-review skill checklist opens with "Per the brief (§ Mocking Policy), this project allows no mock libraries at all" and lists "No Mockito, EasyMock, or any mock/stub library usage" as a required check. Both docs/testing-principles.md § Mocking Policy and CLAUDE.md § Testing Strategy say Mockito is "tolerated, not encouraged" and that new tests should reach for real implementations or hand-written doubles first — not that Mockito is prohibited. The skill summary overstates the restriction: it would mis-flag every @WebMvcTest controller test in the project (including the existing VetControllerTests that this slice explicitly clones). A human decision is needed: either update the skill checklist to reflect the brief ("tolerated, not encouraged; conscious exception") or tighten the brief to prohibit Mockito outright and add explicit guidance for the orphan-specialty class of test where real fixtures would require seeding a separate test DB.
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 15m***
  - [autofix] `prd.md:137` Sentence runs 31 words, one over the 30-word limit per writing standards (sentences under 30 words).
    - fix: The specialty directory lists every specialty the clinic knows by its stored name. Under each, it shows the veterinarians who hold it, each by full name — first name then last name.
- ↻ **fix prd-expert** ← doc · (1 finding)

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Output escaping: all user-derived values (specialty.name, veterinarian full names) render via th:text (HTML-escaped) with no th:utext; mirrors the existing vetList.html pattern, so no XSS.
- SQL/JPQL: SpecialtyRepository.findSpecialties() is a static parameterless JPQL query with no concatenation; no injection surface.
- New public GET /specialties.html endpoint exposes no new data class - vet and specialty names are already public via the existing vet directory, consistent with the app-wide no-auth model (no spring-security config present).
- Read-only, GET-only slice honoring NG-2: no write path, no deserialization, no file I/O, no secrets, no new dependency.
- Non-paginated result set is a product decision over admin-seeded data; DOS is out of scope and no user-controlled input reaches the query or template.

**code-quality-reviewer**

- checkFormat passes clean
- SpecialtyRepository mirrors PetTypeRepository exactly: JpaRepository, @Query JPQL name-ordered; read-confirmed PetTypeRepository.java:36-37
- SpecialtyController and VetController are both package-private; read-confirmed VetController.java:36
- Constructor injection without @Autowired, consistent with VetController pattern
- Model attribute key listSpecialties follows the list{Entity} convention established by listVets in VetController
- SpecialtyController Javadoc explains the unidirectional association inversion rationale inline — future readers have the why without digging
- Trailing-space multi-value cell rendering mirrors vetList.html:20 exactly; read-confirmed — not a deviation
- SpecialtyListing is a package-private, fully typed record with accurate @param Javadoc; no mutable state, no raw Map
- buildDirectory and invertVetSpecialties are focused private methods each under 15 lines with single responsibilities
- LinkedHashMap preserves sorted insertion order correctly; the sort-then-insert approach is sound
- All five PRD acceptance criteria exercised in tests including the orphan-specialty edge (dentistry held by no vet) and the omit-vet-with-no-specialty edge (James Carter)
- BDD method names follow the established theFeatureShouldBehavior convention
- AssertJ used throughout; containsExactly assertions verify both value and order for the last-then-first vet ordering requirement
- vet() factory method uses varargs for specialty names — elegant and readable
- No prohibited suffixes, no abbreviations, no util packages, no System.out usage

**test-reviewer**

- All five PRD test_names (theSpecialtyDirectoryShouldListEverySpecialtyByStoredName, theSpecialtyDirectoryShouldShowVeterinariansByFullName, theSpecialtyDirectoryShouldOmitVeterinariansHoldingNoSpecialty, theSpecialtyDirectoryShouldListSpecialtiesHeldByNoVeterinarian, theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage) are present and each assertion would fail on a genuine regression of the named behavior
- AssertJ containsExactly used for both specialty ordering (alphabetical) and vet ordering within specialty (last-then-first), directly verifying the stable-order acceptance criterion
- doesNotContain and isEmpty() correctly verify omission of vet-with-no-specialty and the empty-vet-list for orphan specialty respectively
- Factory methods specialty() and vet() wrap all domain object construction — no raw constructor calls in test bodies
- BDD naming convention (the{Subject}Should{Outcome}) followed on all five methods
- Four-phase structure maintained: @BeforeEach arranges, per-test perform() acts, assertThat/andExpect asserts, no cleanup needed
- @MockitoBean on SpecialtyRepository and VetRepository is a conscious exception justified by: (a) the orphan-specialty edge case is not present in H2 seed data and cannot be exercised without either a mock or additional test-fixture DB setup, (b) the design-block explicitly instructs this pattern, (c) it mirrors the established VetControllerTests shape, and (d) the brief explicitly says mock-framework stubs are tolerated
- The no-pagination test explicitly asserts totalPages/currentPage/totalItems attributes are absent from the model, making the single-page constraint machine-verifiable rather than inferred
- Hamcrest hasSize via MockMvc model().attribute() fluent chain is the standard Spring MVC test DSL integration point, not a raw JUnit assertion violation
- Straight-line test bodies with no branching or loops
- Setup comments explain test-data semantics (why dentistry is the orphan, why Douglas precedes Leary) at a level not derivable from the code alone — these are scenario annotations, not narration

**doc-reviewer**

- HTML anchor \<a id="req-spec-001">\</a> is present at line 135
- No implementation details, URLs, Java constructs, or code blocks appear in the new section
- Cross-reference system-design.md#contracts uses the full path with anchor and resolves
- NG-2 reads consistently with REQ-SPEC-001: the section is read-only and explicitly references NG-2 as unchanged
- Phrasing when the specialty directory is opened correctly omits the URL matching REQ-VET-001 abstraction level
- All domain terms Specialty and Veterinarian match canonical spelling in ubiquitous-language.md
- Doc-sync deferral of SpecialtyController and SpecialtyRepository Contracts table entries is correct per protocol: no existing system-design.md entry references REQ-SPEC-001 and doc-sync is the next scheduled step
- Requirement placement after Veterinarian directory and before Language is coherent with the narrative flow

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 1 | opus-4-8 | $3.72 | 6m 19s | 90% |
| `(parent)` | 1 | opus-5 | $3.65 | 20m 11s | 92% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $3.21 | 2m 46s | 71% |
| `spring-boot-claude:system-design-expert` | 1 | opus-4-8 | $2.99 | 3m 6s | 77% |
| `spring-boot-claude:security-reviewer` | 1 | opus-4-8 | $1.26 | 44s | 73% |
| `spring-boot-claude:doc-reviewer` | 1 | sonnet-4-6 | $1.10 | 3m 58s | 79% |
| `spring-boot-claude:code-quality-reviewer` | 1 | sonnet-4-6 | $0.84 | 3m 15s | 84% |
| `spring-boot-claude:test-reviewer` | 1 | sonnet-4-6 | $0.80 | 3m 21s | 80% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.08 | 0s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-4-8 | $3.72 | 6m 19s | 90% |
| `(parent)` | opus-5 | $3.65 | 20m 11s | 92% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $2.99 | 3m 6s | 77% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $2.05 | 1m 54s | 75% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $1.26 | 44s | 73% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.16 | 52s | 62% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $1.10 | 3m 58s | 79% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.84 | 3m 15s | 84% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.80 | 3m 21s | 80% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.08 | 0s | 0% |

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
