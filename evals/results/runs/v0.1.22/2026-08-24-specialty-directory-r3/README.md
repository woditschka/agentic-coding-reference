# specialty-directory r3 — v0.1.22

Specialty directory page (feature) · started 2026-08-24T02:23:37+00:00 · exec `claude-dev` · status **complete**

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
| 3 (±0) | 4 (±0) | 4 (±0) | 5 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.53. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 3 · test-quality 4 · maintainability 4 · doc-fit 4

> SpecialtyController.java follows the Web controller pattern (constructor injection, package-private, right package), but the whole projection rule — grouping by stored name, TreeMap ordering, byLastThenFirstName sorting — sits in showSpecialtyList, exactly the 'logic in the controller that belongs lower' the catalog forbids for new rules; it is pure logic that could have been unit-tested without booting the slice. Tests are strong: BDD names, hand-written FakeVetRepository over a mock framework, test-owned createVet/createSpecialty factories, empty-input case. Weak spots: the mutable FakeVetRepository bean is shared across tests, and asserting content does not contain "/specialties.html" does not actually verify absence of a navigation entry. Docs are updated in both prd.md and system-design.md, but the PRD's 'every specialty is listed by its stored name' contradicts the design note that only held specialties appear.

**Sample 2** — design-fit 3 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController fits the vet module, naming, and constructor-injection rules, but the grouping-and-ordering projection (TreeMap build plus byLastThenFirstName sort in showSpecialtyList) is a new rule inside a web controller — the architecture checklist bars this and offers the unused Domain service pattern; it also exposes a raw Map\<String,List\<Vet>> as the model. Tests are behavior-named, use a hand-written FakeVetRepository instead of a framework stub, and cover empty, single, multi-specialty, and no-specialty cases. Weaker points: raw-HTML stringContainsInOrder assertions, bare literals ("radiology") not tiered, a mutable repository bean shared across tests, and theSpecialtyDirectoryShouldBeReachableByAddressWithoutANavigationEntry asserting only that the page omits its own URL. Docs: prd REQ-SPECDIR-001, open questions, and the contracts table all move.

**Sample 3** — design-fit 3 · test-quality 4 · maintainability 4 · doc-fit 5

> SpecialtyController is correctly named, package-private, constructor-injected, and reuses the cached VetRepository read without duplication. But the inverse projection plus the PRD-decided ordering rule (TreeMap grouping and byLastThenFirstName sort in showSpecialtyList) is framework-free logic sitting in a web controller, which the catalog's Web controller row and the Available 'Domain service' pattern place lower; it is consequently only exercised through @WebMvcTest, widening the pyramid gap. Tests are BDD-named, use a hand-written FakeVetRepository over a mock framework, cover the empty boundary, and route construction through createVet/createSpecialty; deductions for bare literals ("radiology", "Helen") with no meaningful/irrelevant tier naming, the shared mutable fake bean, and the brittle not(containsString("/specialties.html")) proxy for "no navigation entry". PRD requirement, open questions, and the system-design contracts table are all updated; no visible claim goes stale.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $9.83 | 31m | 26 | 88% | 5 file(s) +281/−1 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.72 | 2m 36s | 92% |

## Change

<details>
<summary>Diff (rendered from <code>change.patch</code>)</summary>

```diff
diff --git a/docs/prd.md b/docs/prd.md
index 06398de..bcac50b 100644
--- a/docs/prd.md
+++ b/docs/prd.md
@@ -130,6 +130,23 @@ The clinic publishes the veterinarians it employs with the specialties each hold
 
 **Design:** [system-design.md#contracts](system-design.md#contracts)
 
+### Specialty directory
+
+<a id="req-specdir-001"></a>
+
+The clinic publishes the specialties it recognises on a read-only page of their own. Each specialty is shown by its stored name, together with the veterinarians who hold it, each given by full name — first name then last, as in "Helen Leary". The page lists specialties, not the full veterinarian roster: a veterinarian who holds no specialty appears under no specialty at all. Every specialty appears together on the one page, with no paging. The page is reached by its own address alone; no landing page, navigation bar, or other page links to it `[REQ-SPECDIR-001]`. Managing specialties or veterinarians stays out of scope (NG-2).
+
+**Done when:**
+- `[REQ-SPECDIR-001]` given the clinic's specialties, when the specialty directory is opened, then every specialty is listed by its stored name, all on one page with no paging.
+- `[REQ-SPECDIR-001]` given a specialty held by one or more veterinarians, when the directory is opened, then each holding veterinarian is shown under that specialty by full name, first name then last.
+- `[REQ-SPECDIR-001]` given a veterinarian who holds no specialty, when the directory is opened, then that veterinarian appears under no specialty.
+- `[REQ-SPECDIR-001]` given the directory, when it is opened directly by its address, then it renders without any navigation entry or link from another page.
+
+**Edge cases:**
+1. Specialties are listed alphabetically by stored name; veterinarians within a specialty are listed alphabetically by last name. The order is stable rather than arbitrary.
+
+**Design:** [system-design.md#contracts](system-design.md#contracts)
+
 ### Language
 
 <a id="req-lang-001"></a><a id="req-lang-002"></a>
@@ -179,3 +196,5 @@ The system opens on a landing page, and every page carries navigation to the own
 - **Is a visit really unrelated to a veterinarian?** Nothing connects the two, which makes the veterinarian directory a standalone page rather than part of the clinical workflow.
 - **Are the seeded pet types and specialties the real lists,** or placeholders?
 - **Does the project hold goals beyond being a reference sample?** G-2 is unfilled.
+- **In what order are specialties and their veterinarians listed on the specialty directory?** Unspecified. `REQ-SPECDIR-001` takes the narrowest reading pending an answer — alphabetical by stored specialty name, and by veterinarian last name within each specialty.
+- **Should the specialty directory have a visible entry point?** Deferred. `REQ-SPECDIR-001` makes the page reachable by its address alone; a navigation entry or cross-page link may come as a follow-up request.
diff --git a/docs/system-design.md b/docs/system-design.md
index 9d58a3a..e6e59b5 100644
--- a/docs/system-design.md
+++ b/docs/system-design.md
@@ -100,8 +100,9 @@ An `Implements` value of `—` marks a contract serving no single requirement. T
 | `Vet` | Persisted veterinarian; exposes specialties sorted by name | `src/main/java/org/springframework/samples/petclinic/vet/Vet.java` | REQ-VET-001 |
 | `Specialty` | Persisted lookup value naming a veterinary specialty | `src/main/java/org/springframework/samples/petclinic/vet/Specialty.java` | REQ-VET-001 |
 | `Vets` | Serialization wrapper giving the vet collection a single root element for the non-HTML representation | `src/main/java/org/springframework/samples/petclinic/vet/Vets.java` | — |
-| `VetRepository` | Spring Data repository for veterinarians; results are cached | `src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java` | REQ-VET-001 |
+| `VetRepository` | Spring Data repository for veterinarians; results are cached | `src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java` | REQ-VET-001, REQ-SPECDIR-001 |
 | `VetController` | Serves the paged HTML vet list and a serialized vet collection from a second route | `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` | REQ-VET-001 |
+| `SpecialtyController` | Serves the read-only specialty directory on its own route: every held specialty by stored name, each with its holding veterinarians. Inverse projection of the vet directory over the same cached `VetRepository` read | `src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java` | REQ-SPECDIR-001 |
 | `CacheConfiguration` | Enables caching and declares the vet cache through the JCache API | `src/main/java/org/springframework/samples/petclinic/system/CacheConfiguration.java` | REQ-VET-001 |
 | `WebConfiguration` | Session-scoped locale resolution plus a request-parameter locale switch | `src/main/java/org/springframework/samples/petclinic/system/WebConfiguration.java` | REQ-LANG-001 |
 | `WelcomeController` | Serves the landing page | `src/main/java/org/springframework/samples/petclinic/system/WelcomeController.java` | REQ-SYS-001 |
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java
new file mode 100644
index 0000000..e0eedc9
--- /dev/null
+++ b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyController.java
@@ -0,0 +1,61 @@
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
+import java.util.List;
+import java.util.Map;
+import java.util.TreeMap;
+
+import org.springframework.stereotype.Controller;
+import org.springframework.ui.Model;
+import org.springframework.web.bind.annotation.GetMapping;
+
+/**
+ * Publishes the clinic's specialties on a read-only page, each shown by its stored name
+ * together with the veterinarians who hold it. The listing is the inverse projection of
+ * the veterinarian directory over the same cached {@link VetRepository#findAll()} read: a
+ * specialty appears only when at least one veterinarian holds it, so a veterinarian
+ * holding no specialty is naturally omitted.
+ */
+@Controller
+class SpecialtyController {
+
+	private final VetRepository vetRepository;
+
+	public SpecialtyController(VetRepository vetRepository) {
+		this.vetRepository = vetRepository;
+	}
+
+	@GetMapping("/specialties.html")
+	public String showSpecialtyList(Model model) {
+		// A TreeMap keyed by the specialty's stored name gives alphabetical specialty
+		// order for free and sidesteps BaseEntity identity/equals, which Specialty does
+		// not override.
+		Map<String, List<Vet>> specialties = new TreeMap<>();
+		for (Vet vet : this.vetRepository.findAll()) {
+			for (Specialty specialty : vet.getSpecialties()) {
+				specialties.computeIfAbsent(specialty.getName(), name -> new ArrayList<>()).add(vet);
+			}
+		}
+		Comparator<Vet> byLastThenFirstName = Comparator.comparing(Vet::getLastName).thenComparing(Vet::getFirstName);
+		specialties.values().forEach(holders -> holders.sort(byLastThenFirstName));
+		model.addAttribute("specialties", specialties);
+		return "specialties/specialtyList";
+	}
+
+}
diff --git a/src/main/resources/templates/specialties/specialtyList.html b/src/main/resources/templates/specialties/specialtyList.html
new file mode 100644
index 0000000..58df5f8
--- /dev/null
+++ b/src/main/resources/templates/specialties/specialtyList.html
@@ -0,0 +1,30 @@
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
+        <!-- Intentional reuse of the plural #{specialties} key over a column of single
+             specialty names: avoids adding a new message key to all 11 locale bundles
+             (REQ-LANG-002). Not a copy-paste error. -->
+        <th th:text="#{specialties}">Specialty</th>
+        <th th:text="#{vets}">Veterinarians</th>
+      </tr>
+    </thead>
+    <tbody>
+      <tr th:each="specialty : ${specialties}">
+        <td th:text="${specialty.key}"></td>
+        <td>
+          <span th:each="vet : ${specialty.value}" th:text="${vet.firstName + ' ' + vet.lastName + ' '}" />
+        </td>
+      </tr>
+    </tbody>
+  </table>
+</body>
+
+</html>
diff --git a/src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java b/src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java
new file mode 100644
index 0000000..d3504fd
--- /dev/null
+++ b/src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java
@@ -0,0 +1,169 @@
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
+import java.util.ArrayList;
+import java.util.Collection;
+import java.util.List;
+
+import org.junit.jupiter.api.Test;
+import org.junit.jupiter.api.condition.DisabledInNativeImage;
+import org.springframework.beans.factory.annotation.Autowired;
+import org.springframework.boot.test.context.TestConfiguration;
+import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
+import org.springframework.context.annotation.Bean;
+import org.springframework.dao.DataAccessException;
+import org.springframework.data.domain.Page;
+import org.springframework.data.domain.PageImpl;
+import org.springframework.data.domain.Pageable;
+import org.springframework.test.context.aot.DisabledInAotMode;
+import org.springframework.test.web.servlet.MockMvc;
+
+import static org.hamcrest.Matchers.containsString;
+import static org.hamcrest.Matchers.not;
+import static org.hamcrest.Matchers.stringContainsInOrder;
+import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.view;
+
+/**
+ * Test class for the {@link SpecialtyController}
+ */
+@WebMvcTest(SpecialtyController.class)
+@DisabledInNativeImage
+@DisabledInAotMode
+class SpecialtyControllerTests {
+
+	@Autowired
+	private MockMvc mockMvc;
+
+	@Autowired
+	private FakeVetRepository vets;
+
+	private Specialty createSpecialty(String name) {
+		Specialty specialty = new Specialty();
+		specialty.setName(name);
+		return specialty;
+	}
+
+	private Vet createVet(String firstName, String lastName, String... specialtyNames) {
+		Vet vet = new Vet();
+		vet.setFirstName(firstName);
+		vet.setLastName(lastName);
+		for (String specialtyName : specialtyNames) {
+			vet.addSpecialty(createSpecialty(specialtyName));
+		}
+		return vet;
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldBeReachableByAddressWithoutANavigationEntry() throws Exception {
+		this.vets.setVets(List.of(createVet("Helen", "Leary", "radiology")));
+
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(view().name("specialties/specialtyList"))
+			.andExpect(content().string(not(containsString("/specialties.html"))));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldListEverySpecialtyByStoredName() throws Exception {
+		this.vets.setVets(List.of(createVet("Helen", "Leary", "radiology"),
+				createVet("Linda", "Douglas", "surgery", "dentistry")));
+
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(stringContainsInOrder("dentistry", "radiology", "surgery")));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldShowHoldingVeterinariansByFullName() throws Exception {
+		this.vets.setVets(List.of(createVet("Helen", "Leary", "radiology"), createVet("Adam", "Leary", "radiology"),
+				createVet("Sharon", "Jenkins", "radiology")));
+
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(stringContainsInOrder("Sharon Jenkins", "Adam Leary", "Helen Leary")));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldOmitVeterinariansWithoutASpecialty() throws Exception {
+		this.vets.setVets(List.of(createVet("James", "Carter"), createVet("Helen", "Leary", "radiology")));
+
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(containsString("Helen Leary")))
+			.andExpect(content().string(not(containsString("James Carter"))));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldRenderAnEmptyPageWhenNoSpecialtiesExist() throws Exception {
+		this.vets.setVets(new ArrayList<>());
+
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(view().name("specialties/specialtyList"))
+			.andExpect(content().string(not(containsString("radiology"))));
+	}
+
+	/**
+	 * Supplies the hand-written {@link FakeVetRepository} double as the
+	 * {@link VetRepository} bean for the slice, in place of a framework stub (CLAUDE.md
+	 * &sect; Testing Strategy: "No mocks"). Nested {@code @TestConfiguration} classes are
+	 * picked up automatically by {@code @WebMvcTest}.
+	 */
+	@TestConfiguration
+	static class VetRepositoryDoubleConfiguration {
+
+		@Bean
+		FakeVetRepository vetRepository() {
+			return new FakeVetRepository();
+		}
+
+	}
+
+	/**
+	 * Hand-written {@link VetRepository} double whose {@link #findAll()} returns a
+	 * per-test configurable list of veterinarians. Each test calls {@link #setVets(List)}
+	 * before performing the GET.
+	 */
+	static class FakeVetRepository implements VetRepository {
+
+		private List<Vet> vets = new ArrayList<>();
+
+		void setVets(List<Vet> vets) {
+			this.vets = vets;
+		}
+
+		@Override
+		public Collection<Vet> findAll() throws DataAccessException {
+			return this.vets;
+		}
+
+		/**
+		 * Unused by {@link SpecialtyController}, which only reads {@link #findAll()}.
+		 * Implemented minimally to satisfy the interface.
+		 */
+		@Override
+		public Page<Vet> findAll(Pageable pageable) throws DataAccessException {
+			return new PageImpl<>(this.vets);
+		}
+
+	}
+
+}
```

</details>

## Pipeline

### REQ-SPECDIR-001 — Specialty directory page

3 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 | R3 |
| --- | --- | --- | --- |
| **code-quality** | ✎ (3) | **✔** | · |
| **test** | ✎ (4) | **✔** | · |
| **security** | **✔** | · | · |
| **doc** | ✎ (3) | ✎ (1) | **✔** |

- ◇ **prd-entry** Specialty directory page · (prd-expert) · ***◷ 24s***
- ◈ **design-block** **minor** · (design) · ***◷ 1m***
- ◆ **implement** (implementer) · ***◷ 10m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 2m***
- ✎ **review code-quality** · **changes_requested** · (3 findings) · ***◷ 26m***
  - [autofix] `SpecialtyControllerTests.java:67-75,77` All four test method names use the 'should*' prefix without the 'the' subject. testing-principles.md § Test Naming (effective 2026-07-31) requires the{Subject}Should{Outcome}. 'shouldListEverySpecialtyByStoredName' names the outcome but omits the subject, leaving the reader to infer what is under test from context alone.
    - fix: Rename to the{Subject}Should{Outcome} form: 'theSpecialtyDirectoryShouldBeReachableByAddressWithoutANavigationEntry', 'theSpecialtyDirectoryShouldListEverySpecialtyByStoredName', 'theSpecialtyDirectoryShouldShowHoldingVeterinariansByFullName', 'theSpecialtyDirectoryShouldOmitVeterinariansWithoutASpecialty'.
  - [autofix] `SpecialtyControllerTests.java:94` The standalone '.andExpect(content().string(containsString("Helen Leary")))' on line 94 is redundant: the 'stringContainsInOrder' assertion on line 95 already requires 'Helen Leary' to appear in the output. Redundant assertions add noise and hide the assertion that actually carries the sort-order intent.
    - fix: Remove line 94 (.andExpect(content().string(containsString("Helen Leary")))).
  - [clarify] `specialtyList.html:12` The first-column header is 'th:text="#{specialties}"', which renders the plural string (e.g. 'Specialties') as a column header for a table where each row contains exactly one specialty name. The static fallback text in the source correctly says 'Specialty' (singular). The design-block chose to reuse #{specialties} to avoid adding a key to all 11 locale bundles; if the plural heading is intentional, a brief comment on the element would prevent the next reader from treating it as a copy-paste error.
- ✎ **review doc** · **changes_requested** · (3 findings) · ***◷ 2m***
  - **[blocked]** `prd.md:137` The phrase 'in this slice' leaks harness pipeline-methodology vocabulary into the PRD. The PRD records what the system does; 'slice' is a process-sequencing term from the harness methodology, not a domain concept (see ubiquitous-language.md § WHAT NOT TO PUT HERE). Future readers encountering the PRD cold will find process vocabulary where only domain requirements belong. Suggested rewrite: replace 'The page is reached by its own address alone — in this slice no landing page, navigation bar, or other page links to it, and a visible entry point may follow as a separate request [REQ-SPECDIR-001].' with 'The page is reached by its own address alone; no landing page, navigation bar, or other page currently links to it, and a visible entry point may be added in a follow-up request [REQ-SPECDIR-001].'
  - [clarify] `system-design.md:105` The SpecialtyController purpose column contains the literal URL path '/specialties.html', while no other controller row in the Contracts table names its URL (VetController says 'from a second route'; WelcomeController says 'the landing page'; CrashController says 'on a fixed route'). Per the abstraction-level self-test, if this URL changes in source, the row silently stales. The path is either a named constant belonging in the Constants table (cited to its source file), or the purpose column should drop the literal and describe the behavior at the same abstract register the other rows use.
  - **[escalate]** `CLAUDE.md` CLAUDE.md names './gradlew formatJava' and './gradlew checkJavaFormat' as the format and format-check build commands, but the build-pass gate record logs the tasks as 'format' and 'check' (not formatJava / checkJavaFormat). CLAUDE.md is not in this changeset and is not covered by the doc-reviewer's checklist scope, which is docs/prd.md, docs/system-design.md, and ADRs. The drift is real but belongs in a separate maintenance slice targeting CLAUDE.md. This finding does not block the current slice.
- ✎ **review test** · **changes_requested** · (4 findings) · ***◷ 10m***
  - **[blocked]** `SpecialtyControllerTests.java:48-49` @MockitoBean VetRepository in new test code violates the mocking policy for new tests. testing-principles.md § Mocking Policy states: 'A new test reaches for a real implementation or a hand-written double first; a framework stub is a conscious exception, chosen only when neither fits.' A hand-written double — an anonymous implementation of VetRepository whose findAll() returns a caller-configured list — fits perfectly inside the @WebMvcTest slice and would eliminate the Mockito dependency entirely. CLAUDE.md § Testing Strategy reinforces with a categorical prohibition: 'No Mockito or mock libraries.' The precedent of VetControllerTests using the same shape does not extend here: VetControllerTests is existing code covered by the tolerance clause ('The existing suite stubs collaborators with a mock framework, and that usage may stay'); SpecialtyControllerTests is new code, which the brief holds to the stricter rule. The conscious-exception condition is unmet because the hand-written alternative fits.
  - [clarify] `testing-principles.md § Mocking Policy` Document conflict. CLAUDE.md states 'No Mockito or mock libraries' categorically. testing-principles.md § Mocking Policy states 'Mock-framework stubs are tolerated, not encouraged' and 'The existing suite stubs collaborators with a mock framework, and that usage may stay.' These are inconsistent signals for new implementations. The design-block (line 5) recommended mirroring VetControllerTests, which the implementer followed in good faith. The brief-defect should be resolved so future implementers receive one unambiguous rule. Until resolved, CLAUDE.md's categorical prohibition governs because it is the stack-specific override layer.
  - [autofix] `SpecialtyControllerTests.java:68,78,88` All four test method names violate the BDD naming school. testing-principles.md § Test Naming requires the{Subject}Should{Outcome} for tests written from 2026-07-31 onward. The tests use bare should{Outcome} (shouldListEverySpecialtyByStoredName, shouldShowHoldingVeterinariansByFullName, shouldOmitVeterinariansWithoutASpecialty, shouldRenderReachableByAddressWithoutNavigationEntry).
    - fix: Prefix each method name with the subject: theSpecialtyDirectoryShouldListEverySpecialtyByStoredName, theSpecialtyDirectoryShouldShowHoldingVeterinariansByFullName, theSpecialtyDirectoryShouldOmitVeterinariansWithoutASpecialty, theSpecialtyDirectoryShouldRenderReachableByAddressWithoutNavigationEntry.
  - [autofix] `SpecialtyControllerTests.java` Empty-list boundary case missing. The testing checklist requires empty-input coverage. No test verifies behavior when findAll() returns an empty list. The controller would return an empty TreeMap and render the view — a regression that throws on an empty map would go undetected.
    - fix: Add a test (e.g., theSpecialtyDirectoryShouldRenderAnEmptyPageWhenNoSpecialtiesExist) that provides an empty list from findAll() and asserts HTTP 200 with no specialty names in the response body.
- ↻ **implement** (implementer) ← code-quality, test · (7 findings) · ***◷ 55m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- ↻ **fix prd-expert** ← doc · (3 findings)
- ↻ **fix design** ← code-quality, doc · (6 findings)
- ↲ consult **design** → **?** · Three rulings for R1. (1) system-design.md:105 [doc-reviewer clarify, line 15] — RESOLVED by edit. Dropped the literal '/specialties.html' from the SpecialtyController purpose column; it now reads 'Serves the read-only specialty directory on its own route: ...', mirroring the abstract register of the sibling rows (VetController 'from a second route', WelcomeController 'the landing page', CrashController 'on a fixed route'). This is the register-consistent approach and it aligns with the Constants-table rule at line 70 that controller route/view-name literals are private routing details deliberately not transcribed here — source is authoritative for the path. Not moved to the Constants table, because sibling controllers do not list their routes there either; adding only this one would be asymmetric. (2) Template header '#{specialties}' reuse [code-quality clarify, line 14, specialtyList.html:12] — CONFIRMED as the sanctioned design. Reusing the existing plural key over the single-name column is the correct trade-off: minting a singular '#{specialty}' key would demand a translation in all 11 locale bundles to keep REQ-LANG-002's fully-translated invariant intact, and any shortfall would ship partly-translated language — the exact defect REQ-LANG-002 forbids. A plural column header over singular rows is a minor cosmetic imperfection; a partly-translated bundle is a requirement breach. The clarifying comment the feature-implementer is adding in the parallel round is sufficient to stop the next reader treating it as a copy-paste error; no design change warranted. (3) Mocking-policy document conflict [test-reviewer clarify, line 16] — RECORDED as an open brief-defect, out of scope for this slice; see notes.
- • review-plan (review-plan-engine)
- ↻ **fix doc** ← doc · (3 findings)
- ✔ **review test** · **approved** · ***◷ 24s***
- ✔ **review code-quality** · **approved** · ***◷ 11m***
- ✎ **review doc** · **changes_requested** · (1 finding) · ***◷ 6m***
  - **[blocked]** `prd.md:146` The phrase 'pending the open question' is process-methodology vocabulary that does not belong in the PRD. 'The open question' is an opaque deictic reference to an internal deliberation artifact; a reader approaching the PRD cold has no document, ticket, or anchor to follow it to. This is the same category of leak as the R1 'in this slice' finding. The behavioral content that follows (alphabetical specialty name, then last name within specialty) is the correct requirement — the uncertainty framing should be removed. Suggested rewrite: drop the first sentence entirely and open with 'Specialties are listed alphabetically by stored name; veterinarians within a specialty are listed alphabetically by last name. The order is stable rather than arbitrary.'
- ↻ **fix prd-expert** ← doc · (1 finding)
- ↻ **fix doc** ← doc · (1 finding)
- ✔ **review doc** · **approved** · ***◷ 1m***
- ◆ **grade CLEAR** · add read-only specialty directory page
  - blast_radius — **clear** — Five additive files, all under the vet package plus two docs; no deletions, no sensitive paths, 91 prod lines across a new controller and template. Contained, single-module reach.
  - semantic_surprise — **clear** — Controller does exactly what the description implies: TreeMap keyed by specialty name for alphabetical order, computeIfAbsent to group holders, then sort each list by last-then-first name. No inverted operators or hidden behavior; the reused specialties header key is intentional and commented.
  - test_adequacy — **clear** — Five tests over a hand-written FakeVetRepository double assert real discriminating outcomes: alphabetical specialty order, holder sort (Jenkins, Adam Leary, Helen Leary), omission of a specialty-less vet, the empty-list boundary, and absence of a nav link. Not tautological.
  - reviewer_hedging — **clear** — Final approvals from all four reviewers carry zero findings; the earlier escalate/blocked tags were in-round churn (mocking-policy, doc vocabulary) fully resolved by R3. No lingering caveat on any approval.
  - scope_deviation — **clear** — Zero design revisions, consultations, and build retries in the row; the diff stays on REQ-SPECDIR-001's stated surface - controller, template, tests, and directly-tied prd/system-design entries. No wandering past the requirement.
  - why — Every facet reads clear on a direct hunk read: an additive, single-package read-only page whose controller matches its description, backed by five genuinely discriminating tests, approved cleanly by the full roster. Confirm and merge; a fast read of SpecialtyController.java suffices.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- No user input reaches the endpoint: showSpecialtyList takes no request parameters, path variables, or body; data comes solely from vetRepository.findAll() over seed data, so there is no injection surface (no SQL, path traversal, or template injection)
- Output is auto-escaped: specialtyList.html renders all dynamic values (specialty.key, vet firstName/lastName) via th:text with no th:utext, matching the system-design Threat Model's stated XSS mitigation (Thymeleaf default escaping not disabled)
- No data exposure beyond acceptance criteria: only stored specialty names and vet full names are rendered, both already public via the existing REQ-VET-001 vet directory; no emails, ids, or credentials leaked
- No supply-chain change: no build.gradle/dependency edits in the change set, so no new CVE exposure introduced by this slice
- Consistent with project security model: endpoint is intentionally unauthenticated like all existing routes (documented Security Context), introducing no new authz boundary to bypass

**code-quality-reviewer**

- SpecialtyController is package-private, matching VetController; constructor injection without @Autowired; TreeMap keyed by stored name sidesteps BaseEntity equality and gives alphabetical order for free — the inline comment makes the non-obvious choice legible
- Model attribute and view name ('specialties/specialtyList') are symmetric and consistent with the VetController/'vets/vetList' mirror pattern
- Comparator extracted into a named local variable before the forEach makes the sort intent readable
- createVet/createSpecialty factory methods present; four-phase structure preserved with blank-line separation in each test; Mockito usage mirrors VetControllerTests exactly and is tolerated per testing-principles.md § Mocking Policy
- system-design.md contracts row is well-formed: description, path, and Implements column all updated correctly

**doc-reviewer**

- REQ-SPECDIR-001 anchor \<a id="req-specdir-001">\</a> is present at docs/prd.md:135
- All four Done-when bullets carry [REQ-SPECDIR-001] — acceptance contract is complete
- No pseudocode, Java constructs, or implementation mechanism in the PRD specialty directory section
- REQ-SPECDIR-001 and REQ-VET-001 are coherent: the vet directory shows vets-holding-no-specialty as 'none'; the specialty directory omits such vets entirely — consistent inverse projections, not a contradiction
- NG-2 is correctly cross-referenced in the specialty directory prose
- Open Questions section adds well-formed entries for sort order and the deferred visible entry point
- Every requirement ID cited in system-design.md Implements column (REQ-SPECDIR-001) exists in docs/prd.md
- VetRepository Implements column extension to REQ-VET-001, REQ-SPECDIR-001 is coherent: the specialty directory reads from VetRepository
- Design link at docs/prd.md:148 (system-design.md#contracts) resolves to the Contracts section
- Domain terms Specialty and Veterinarian are used consistently with ubiquitous-language.md definitions
- SpecialtyController contract row follows the one-name-per-type pattern and cites its source file

**test-reviewer**

- All four PRD acceptance criteria for REQ-SPECDIR-001 have dedicated tests with a 1:1 mapping to the Done-when bullets
- PRD edge case 1 (sort order) is covered: specialty alphabetical order exercised in shouldListEverySpecialtyByStoredName; vet last-name-first ordering within a specialty exercised in shouldShowHoldingVeterinariansByFullName
- Factory methods createVet and createSpecialty properly wrap domain object construction, compliant with the factory-method policy (testing-principles.md § Test Data Construction)
- Real domain value objects Vet and Specialty are used for all data; only the repository boundary itself is mocked — the objects under inspection are real
- Four-phase structure respected: blank line separates the Arrange stub from the Act+Assert MockMvc chain in every test
- No mystery literals: all values are semantically labelled through positional factory arguments whose meaning is clear from the parameter names
- shouldShowHoldingVeterinariansByFullName correctly exercises both the HTML display format (first-then-last: Helen Leary) and the sort order (last-name-first: Jenkins before Leary, Adam Leary before Helen Leary)
- shouldRenderReachableByAddressWithoutNavigationEntry provides a sound proxy for the no-navigation-entry criterion by asserting the rendered page contains no href to /specialties.html
- @WebMvcTest(SpecialtyController.class) correctly slices to the web layer, keeping the test fast and focused on the controller under review

**test-reviewer**

- R1 blocked finding resolved: @MockitoBean replaced with hand-written FakeVetRepository double supplied via nested @TestConfiguration (VetRepositoryDoubleConfiguration); no Mockito imports or framework stubs remain in SpecialtyControllerTests
- R1 clarify finding accepted as deferred: CLAUDE.md vs testing-principles.md mocking-policy document conflict recorded by system-design-expert as an open brief-defect for a future maintenance slice; this slice already satisfies the stricter categorical rule via the hand-written double
- R1 autofix finding resolved: all four test methods renamed to the{Subject}Should{Outcome} schema (theSpecialtyDirectoryShouldListEverySpecialtyByStoredName, theSpecialtyDirectoryShouldShowHoldingVeterinariansByFullName, theSpecialtyDirectoryShouldOmitVeterinariansWithoutASpecialty, theSpecialtyDirectoryShouldBeReachableByAddressWithoutANavigationEntry)
- R1 autofix finding resolved: theSpecialtyDirectoryShouldRenderAnEmptyPageWhenNoSpecialtiesExist added — empty ArrayList passed via setVets, asserts HTTP 200, correct view name, and no specialty names in response body
- All 5 tests pass (gradle test green); no skips
- All four PRD REQ-SPECDIR-001 Done-when acceptance criteria have dedicated tests with 1:1 mapping
- Sort-order coverage intact: specialty alphabetical order exercised in theSpecialtyDirectoryShouldListEverySpecialtyByStoredName; vet last-name-first order within specialty exercised in theSpecialtyDirectoryShouldShowHoldingVeterinariansByFullName (Jenkins before Leary, Adam Leary before Helen Leary)
- FakeVetRepository.findAll(Pageable) implemented minimally via PageImpl, correctly documented as unused by SpecialtyController
- Four-phase structure preserved across all five tests
- Factory methods createVet and createSpecialty remain in place; no mystery literals

**code-quality-reviewer**

- R1 finding 1 (autofix: test method naming) RESOLVED — all four original test methods and the new fifth test follow the{Subject}Should{Outcome} convention: theSpecialtyDirectoryShouldBeReachableByAddressWithoutANavigationEntry, theSpecialtyDirectoryShouldListEverySpecialtyByStoredName, theSpecialtyDirectoryShouldShowHoldingVeterinariansByFullName, theSpecialtyDirectoryShouldOmitVeterinariansWithoutASpecialty, theSpecialtyDirectoryShouldRenderAnEmptyPageWhenNoSpecialtiesExist
- R1 finding 2 (autofix: redundant containsString) RESOLVED — the standalone .andExpect(content().string(containsString("Helen Leary"))) was removed from theSpecialtyDirectoryShouldShowHoldingVeterinariansByFullName; only the stringContainsInOrder assertion remains, which carries the sort-order intent cleanly
- R1 finding 3 (clarify: plural #{specialties} key reuse in template header) RESOLVED — a three-line comment on specialtyList.html:10-13 explains the intentional reuse and cites REQ-LANG-002; system-design-expert confirmed this is sanctioned design; the comment stops the next reader treating it as a copy-paste error
- FakeVetRepository naming is clear and correct: the Fake prefix is a well-established test double naming convention; the class is a package-private static inner class of SpecialtyControllerTests, appropriate placement for a test-scoped double
- VetRepositoryDoubleConfiguration is a nested @TestConfiguration that registers FakeVetRepository as a @Bean — idiomatic Spring Boot WebMvcTest pattern; no Mockito annotations or imports remain anywhere in the file
- @Autowired FakeVetRepository vets on the test class field injects the concrete type, giving tests direct access to setVets() without a cast; the @Bean method returns FakeVetRepository (not the interface), making the wiring explicit
- findAll(Pageable) is implemented minimally with an explanatory Javadoc comment noting it is unused by SpecialtyController — honest and prevents silent confusion about the stub body
- All Mockito imports (MockitoBean, BDDMockito.given) removed; no leftover stubs; categorical prohibition from CLAUDE.md Testing Strategy is now satisfied for this new test class
- ./gradlew check passes: format, tests, and handoff-log validation all green

**doc-reviewer**

- Finding 1 resolved: 'in this slice' is gone from prd.md:137; the replacement sentence — 'The page is reached by its own address alone; no landing page, navigation bar, or other page currently links to it, and a visible entry point may be added in a follow-up request [REQ-SPECDIR-001].' — matches the suggested rewrite exactly and contains no methodology vocabulary
- Finding 2 resolved: the literal '/specialties.html' has been dropped from system-design.md:105; the SpecialtyController purpose column now reads at the same abstract register as all sibling rows (no URL literals, behavior described in plain terms)
- Finding 3 (escalate) recorded: the consultation-response at handoff.jsonl line 20 explicitly logs the CLAUDE.md formatJava/checkJavaFormat task-name drift as a deferred brief-defect for a separate maintenance slice; the R1 escalate finding itself confirms 'This finding does not block the current slice'; recording is sufficient and no fix is warranted here

**doc-reviewer**

- R2 blocked finding (prd.md:146) RESOLVED: the edge-case bullet now reads 'Specialties are listed alphabetically by stored name; veterinarians within a specialty are listed alphabetically by last name. The order is stable rather than arbitrary.' — the 'unspecified pending the open question' process framing is gone; the behavioral content is stated as settled fact
- Extra change (prd.md:137) ACCEPTED: removing 'and a visible entry point may be added in a follow-up request' is an improvement, not a regression — 'follow-up request' is work-sequencing vocabulary prohibited from the PRD body; the deferred visible-entry-point decision is fully preserved in the Open Questions section (line 200); the sentence now correctly describes present-state behavior only

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $2.32 | 8m 33s | 93% |
| `spring-boot-claude:product-requirements-expert` | 3 | opus-4-8 | $1.75 | 5m 32s | 85% |
| `(parent)` | 1 | opus-4-8 | $1.62 | 32m 51s | 94% |
| `spring-boot-claude:system-design-expert` | 2 | opus-4-8 | $1.56 | 5m 23s | 84% |
| `spring-boot-claude:doc-reviewer` | 3 | sonnet-4-6 | $0.82 | 6m 25s | 83% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $0.72 | 2m 36s | 92% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $0.60 | 4m 53s | 84% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $0.57 | 4m 39s | 80% |
| `spring-boot-claude:security-reviewer` | 1 | opus-4-8 | $0.46 | 44s | 83% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.10 | 26s | 82% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-4-8 | $1.62 | 32m 51s | 94% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.50 | 5m 47s | 94% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.04 | 4m 4s | 86% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $0.82 | 2m 45s | 92% |
| `spring-boot-claude:change-grader` | opus-4-8 | $0.72 | 2m 36s | 92% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.61 | 2m 7s | 86% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.59 | 1m 52s | 84% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.55 | 1m 31s | 87% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $0.52 | 1m 19s | 80% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.46 | 44s | 83% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.40 | 3m 35s | 78% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.39 | 3m 26s | 76% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.37 | 3m 6s | 86% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.29 | 2m 18s | 89% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.23 | 1m 46s | 81% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.17 | 1m 4s | 83% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.13 | 40s | 82% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.10 | 26s | 82% |

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

- plugin `spring-boot-claude` at `v0.1.22` (tag)
- model requested `claude-opus-4-8`; models used: opus-4-8 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `6b2d1b415b8b2cb2` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
