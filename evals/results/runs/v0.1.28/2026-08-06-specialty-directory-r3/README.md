# specialty-directory r3 — v0.1.28

Specialty directory page (feature) · started 2026-08-06T09:30:39+00:00 · exec `claude-dev` · status **complete**

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
| 3 (±0) | 3 (±0) | 3 (±1) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.58. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 3 · test-quality 3 · maintainability 4 · doc-fit 5

> The directory join lives in  VetController.groupVeterinariansBySpecialty / holdersOf ; the comment "display assembly, not a domain rule, so it lives on the controller" self-certifies a rule (unheld specialties still listed, holder sort, full-name display) that a sanctioned Domain service would hold and make unit-testable — the catalog allows adopting one without an ADR. The cache ADR and the  specialties  cache split are genuinely correct (no-arg  findAll / findSpecialties  would collide on the empty key). All six tests boot MockMvc for logic testable without it;  hasProperty("firstName"...)  picks fields apart instead of whole-object comparison,  specialty(1, "radiology")  leaves a mystery id, and comments like "dentistry is a known specialty held by no veterinarian" restate the stub. Template  #{none} / #{specialties}  keys land with no message bundle touched. PRD, contracts table, and ADR index are all current.

**Sample 2** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 5

> The directory assembly ( groupVeterinariansBySpecialty ,  holdersOf  in VetController) is a new rule placed in a controller — precisely what the checklist forbids ("a new rule added to a controller is a fresh violation"); the sanctioned Domain service pattern fits and would be unit-testable, so the pyramid gap widens. Repository placement of  findSpecialties()  on VetRepository stretches one-repository-per-aggregate-root; the separate cache name is well reasoned. Tests are behavior-named and cover the stated edge cases, but carry Tier-3 mystery literals ( specialty(1, "radiology") , ids 1–3), narration comments ("// dentistry is a known specialty…"), and brittle whole-page  not(containsString("Carter")) . The template introduces  #{none}  with no message-bundle change in the patch. Documentation is thorough: REQ-VET-003, five contract rows, ADR, index entry.

**Sample 3** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 5

> VetController.groupVeterinariansBySpecialty/holdersOf put grouping and sort logic in the web layer; the catalog's Available 'Domain service' could be adopted without an ADR, and the testing brief's own question ('could this have been tested without booting the framework?') answers yes, so the pyramid gap widens. findSpecialties on VetRepository also stretches 'one repository per aggregate root'. Tests are exemplary on BDD naming (theSpecialtyDirectoryShouldListSpecialtyWithNoVeterinarians) and edge coverage, but keep Tier-3 literals (specialty(1, "radiology")), add narration comments ('// dentistry is a known specialty...'), and stub via the mock framework. specialtyList.html uses #{specialties}/#{none} with no message bundle added, and the string-concat span with a trailing space is fragile. Docs are complete: PRD REQ-VET-003, contracts rows, cache ADR indexed.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $14.66 | 49m | 44 | 86% | 9 file(s) +222/−11 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $1.50 | 2m 18s | 85% |

## Change

<details>
<summary>Diff (rendered from <code>change.patch</code>)</summary>

```diff
diff --git a/docs/adr/2026-08-06-named-cache-per-cached-read.md b/docs/adr/2026-08-06-named-cache-per-cached-read.md
new file mode 100644
index 0000000..475ab98
--- /dev/null
+++ b/docs/adr/2026-08-06-named-cache-per-cached-read.md
@@ -0,0 +1,32 @@
+# One Named Cache Per Cached Read Method
+
+**Status:** Accepted
+
+## Context
+
+The vet feature caches two repository reads: the veterinarian list and the specialty directory. Both are no-argument methods. Spring's default key generator maps every no-argument invocation to a single shared key (`SimpleKey.EMPTY`). If both reads drew from one cache, the two calls would collide on that key, and whichever ran second would return the other's cached value — the veterinarian list served in answer to the specialty query, or the reverse.
+
+## Options Considered
+
+1. **Single shared cache for both reads** — the two no-argument reads collide on the empty key; one read returns the other's cached result.
+2. **One named cache per cached read** — each read method names its own cache, so the two reads occupy separate key namespaces.
+3. **Custom key generator disambiguating both reads within one cache** — extra machinery to solve a problem that separate cache names solve for free.
+
+## Decision
+
+Declare one named JCache cache per cached read method. Each read's `@Cacheable` names its own cache, so no two reads share a key namespace regardless of their argument shape.
+
+## Consequences
+
+- Reads cannot collide on a shared key, and the guarantee does not depend on the methods staying no-argument.
+- Each cache can be sized, tuned, or evicted independently.
+- Adding a cached read requires declaring its cache in `CacheConfiguration`; registration is not automatic.
+- Neither cache configures eviction, inherited from the pre-existing vet cache. See [Open Questions from the Survey](../system-design.md#open-questions-from-the-survey), item 5.
+
+## Implementation
+
+**Requirements:** REQ-VET-001, REQ-VET-003
+
+## References
+
+- [system-design.md Contracts — CacheConfiguration row](../system-design.md#contracts)
diff --git a/docs/adr/README.md b/docs/adr/README.md
index a94dc3a..ecee63f 100644
--- a/docs/adr/README.md
+++ b/docs/adr/README.md
@@ -69,3 +69,4 @@ A non-goal ADR records a *product* decision not to build something — distinct
 | 2026-07-31 | [Feature-Package Organization Without a Service Layer](2026-07-31-feature-package-organization.md) | Accepted |
 | 2026-07-31 | [Database-Enforced Pet Name Uniqueness Within an Owner](2026-07-31-database-enforced-pet-name-uniqueness.md) | Accepted |
 | 2026-07-31 | [Dual Gradle and Maven Build Definitions](2026-07-31-dual-gradle-and-maven-builds.md) | Accepted |
+| 2026-08-06 | [One Named Cache Per Cached Read Method](2026-08-06-named-cache-per-cached-read.md) | Accepted |
diff --git a/docs/prd.md b/docs/prd.md
index 0cb7f37..acba71b 100644
--- a/docs/prd.md
+++ b/docs/prd.md
@@ -130,6 +130,24 @@ The clinic publishes the veterinarians it employs with the specialties each hold
 
 **Design:** [system-design.md#contracts](system-design.md#contracts)
 
+### Specialty directory
+
+<a id="req-vet-003"></a>
+
+The clinic also publishes its directory the other way round, answering "which veterinarians hold this specialty" rather than "which specialties does this veterinarian hold". A specialty directory lists every specialty the clinic knows by its stored name. Under each, the veterinarians who hold it are shown by full name, listed first name then last name. A veterinarian who holds no specialty appears under none. The directory lists specialties and their holders, not the full veterinarian roster. Every specialty the clinic knows appears together on a single page `[REQ-VET-003]`.
+
+**Done when:**
+- `[REQ-VET-003]` given the clinic's specialties, when the specialty directory is opened, then every specialty is listed by its stored name, each with the veterinarians who hold it.
+- `[REQ-VET-003]` given a veterinarian who holds a specialty, when the directory is opened, then that veterinarian appears under that specialty by full name — first name then last name, such as "Helen Leary".
+- `[REQ-VET-003]` given a veterinarian who holds no specialty, when the directory is opened, then that veterinarian is not listed.
+- `[REQ-VET-003]` given the clinic's specialties, when the directory is opened, then all of them appear together on one page, with no paging.
+
+**Edge cases:**
+1. A specialty that no veterinarian holds is still listed, with no veterinarians shown under it.
+2. A veterinarian who holds more than one specialty appears under each specialty they hold.
+
+**Design:** [system-design.md#contracts](system-design.md#contracts)
+
 ### Language
 
 <a id="req-lang-001"></a><a id="req-lang-002"></a>
diff --git a/docs/system-design.md b/docs/system-design.md
index 9d58a3a..a921407 100644
--- a/docs/system-design.md
+++ b/docs/system-design.md
@@ -97,12 +97,12 @@ An `Implements` value of `—` marks a contract serving no single requirement. T
 | `VisitController` | Server-rendered visit booking for a pet, rejecting non-future dates | `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` | REQ-VIS-001, REQ-VIS-002 |
 | `PetTypeFormatter` | Spring MVC formatter translating between a pet type and its display name during form binding | `src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java` | REQ-PET-001 |
 | `PetValidator` | Spring `Validator` enforcing the required-field rules for pet forms that bean validation does not cover | `src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java` | REQ-PET-001 |
-| `Vet` | Persisted veterinarian; exposes specialties sorted by name | `src/main/java/org/springframework/samples/petclinic/vet/Vet.java` | REQ-VET-001 |
-| `Specialty` | Persisted lookup value naming a veterinary specialty | `src/main/java/org/springframework/samples/petclinic/vet/Specialty.java` | REQ-VET-001 |
+| `Vet` | Persisted veterinarian; exposes specialties sorted by name | `src/main/java/org/springframework/samples/petclinic/vet/Vet.java` | REQ-VET-001, REQ-VET-003 |
+| `Specialty` | Persisted lookup value naming a veterinary specialty | `src/main/java/org/springframework/samples/petclinic/vet/Specialty.java` | REQ-VET-001, REQ-VET-003 |
 | `Vets` | Serialization wrapper giving the vet collection a single root element for the non-HTML representation | `src/main/java/org/springframework/samples/petclinic/vet/Vets.java` | — |
-| `VetRepository` | Spring Data repository for veterinarians; results are cached | `src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java` | REQ-VET-001 |
-| `VetController` | Serves the paged HTML vet list and a serialized vet collection from a second route | `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` | REQ-VET-001 |
-| `CacheConfiguration` | Enables caching and declares the vet cache through the JCache API | `src/main/java/org/springframework/samples/petclinic/system/CacheConfiguration.java` | REQ-VET-001 |
+| `VetRepository` | Spring Data repository for veterinarians; results are cached. Also enumerates every specialty for the specialty directory, including specialties no veterinarian holds | `src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java` | REQ-VET-001, REQ-VET-003 |
+| `VetController` | Serves the paged HTML vet list, a serialized vet collection from a second route, and the unpaged specialty directory | `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` | REQ-VET-001, REQ-VET-003 |
+| `CacheConfiguration` | Enables caching and declares one named JCache cache per cached read through the JCache API: one for the veterinarian read, one for the specialty-directory read ([ADR](adr/2026-08-06-named-cache-per-cached-read.md)) | `src/main/java/org/springframework/samples/petclinic/system/CacheConfiguration.java` | REQ-VET-001, REQ-VET-003 |
 | `WebConfiguration` | Session-scoped locale resolution plus a request-parameter locale switch | `src/main/java/org/springframework/samples/petclinic/system/WebConfiguration.java` | REQ-LANG-001 |
 | `WelcomeController` | Serves the landing page | `src/main/java/org/springframework/samples/petclinic/system/WelcomeController.java` | REQ-SYS-001 |
 | `CrashController` | Deliberately throws on a fixed route to exercise the error page | `src/main/java/org/springframework/samples/petclinic/system/CrashController.java` | REQ-SYS-002 |
diff --git a/src/main/java/org/springframework/samples/petclinic/system/CacheConfiguration.java b/src/main/java/org/springframework/samples/petclinic/system/CacheConfiguration.java
index 13cb743..ef326fa 100644
--- a/src/main/java/org/springframework/samples/petclinic/system/CacheConfiguration.java
+++ b/src/main/java/org/springframework/samples/petclinic/system/CacheConfiguration.java
@@ -34,7 +34,10 @@ class CacheConfiguration {
 
 	@Bean
 	public JCacheManagerCustomizer petclinicCacheConfigurationCustomizer() {
-		return cm -> cm.createCache("vets", cacheConfiguration());
+		return cm -> {
+			cm.createCache("vets", cacheConfiguration());
+			cm.createCache("specialties", cacheConfiguration());
+		};
 	}
 
 	/**
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/VetController.java b/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
index 867d0b5..75b859b 100644
--- a/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
+++ b/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
@@ -15,7 +15,12 @@
  */
 package org.springframework.samples.petclinic.vet;
 
+import java.util.Collection;
+import java.util.Comparator;
+import java.util.LinkedHashMap;
 import java.util.List;
+import java.util.Map;
+import java.util.stream.Collectors;
 
 import org.springframework.data.domain.Page;
 import org.springframework.data.domain.PageRequest;
@@ -62,6 +67,36 @@ class VetController {
 		return vetRepository.findAll(pageable);
 	}
 
+	@GetMapping("/specialties.html")
+	public String showSpecialtyList(Model model) {
+		model.addAttribute("specialties", groupVeterinariansBySpecialty());
+		return "vets/specialtyList";
+	}
+
+	/**
+	 * Builds the specialty directory: every specialty the clinic knows, by stored name,
+	 * mapped to the veterinarians who hold it. Specialties are enumerated independently
+	 * of the roster so one held by no veterinarian still appears (with an empty holder
+	 * list). This is display assembly, not a domain rule, so it lives on the controller.
+	 */
+	private Map<String, List<Vet>> groupVeterinariansBySpecialty() {
+		Collection<Vet> allVets = this.vetRepository.findAll();
+		Map<String, List<Vet>> directory = new LinkedHashMap<>();
+		this.vetRepository.findSpecialties()
+			.stream()
+			.map(Specialty::getName)
+			.sorted()
+			.forEach(name -> directory.put(name, holdersOf(name, allVets)));
+		return directory;
+	}
+
+	private List<Vet> holdersOf(String specialtyName, Collection<Vet> allVets) {
+		return allVets.stream()
+			.filter(vet -> vet.getSpecialties().stream().anyMatch(s -> specialtyName.equals(s.getName())))
+			.sorted(Comparator.comparing(Vet::getLastName).thenComparing(Vet::getFirstName))
+			.collect(Collectors.toList());
+	}
+
 	@GetMapping({ "/vets" })
 	public @ResponseBody Vets showResourcesVetList() {
 		// Here we are returning an object of type 'Vets' rather than a collection of Vet
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java b/src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java
index dbf68d0..d26f32e 100644
--- a/src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java
+++ b/src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java
@@ -19,6 +19,7 @@ import org.springframework.cache.annotation.Cacheable;
 import org.springframework.dao.DataAccessException;
 import org.springframework.data.domain.Page;
 import org.springframework.data.domain.Pageable;
+import org.springframework.data.jpa.repository.Query;
 import org.springframework.data.repository.Repository;
 import org.springframework.transaction.annotation.Transactional;
 
@@ -55,4 +56,15 @@ public interface VetRepository extends Repository<Vet, Integer> {
 	@Cacheable("vets")
 	Page<Vet> findAll(Pageable pageable) throws DataAccessException;
 
+	/**
+	 * Retrieve every <code>Specialty</code> the clinic knows, independently of the
+	 * veterinarians who hold them, so specialties held by no veterinarian are still
+	 * returned.
+	 * @return a <code>Collection</code> of all <code>Specialty</code>s
+	 */
+	@Transactional(readOnly = true)
+	@Cacheable("specialties")
+	@Query("SELECT s FROM Specialty s")
+	Collection<Specialty> findSpecialties() throws DataAccessException;
+
 }
diff --git a/src/main/resources/templates/vets/specialtyList.html b/src/main/resources/templates/vets/specialtyList.html
new file mode 100644
index 0000000..a414a3b
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
+      <tr th:each="specialty : ${specialties}">
+        <td th:text="${specialty.key}"></td>
+        <td>
+          <span th:each="vet : ${specialty.value}" th:text="${vet.firstName + ' ' + vet.lastName + ' '}" /> <span
+            th:if="${#lists.isEmpty(specialty.value)}" th:text="#{none}">none</span>
+        </td>
+      </tr>
+    </tbody>
+  </table>
+</body>
+
+</html>
diff --git a/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java b/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
index 208758c..10e781e 100644
--- a/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
+++ b/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
@@ -31,6 +31,16 @@ import org.springframework.test.web.servlet.MockMvc;
 import org.springframework.test.web.servlet.ResultActions;
 import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
 
+import static org.hamcrest.Matchers.aMapWithSize;
+import static org.hamcrest.Matchers.allOf;
+import static org.hamcrest.Matchers.containsString;
+import static org.hamcrest.Matchers.empty;
+import static org.hamcrest.Matchers.hasEntry;
+import static org.hamcrest.Matchers.hasItem;
+import static org.hamcrest.Matchers.hasKey;
+import static org.hamcrest.Matchers.hasProperty;
+import static org.hamcrest.Matchers.is;
+import static org.hamcrest.Matchers.not;
 import static org.mockito.ArgumentMatchers.any;
 import static org.mockito.BDDMockito.given;
 import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
@@ -64,18 +74,36 @@ class VetControllerTests {
 		helen.setFirstName("Helen");
 		helen.setLastName("Leary");
 		helen.setId(2);
-		Specialty radiology = new Specialty();
-		radiology.setId(1);
-		radiology.setName("radiology");
-		helen.addSpecialty(radiology);
+		helen.addSpecialty(specialty(1, "radiology"));
 		return helen;
 	}
 
+	// Rafael holds two specialties, so he must appear under each of them.
+	private Vet rafael() {
+		Vet rafael = new Vet();
+		rafael.setFirstName("Rafael");
+		rafael.setLastName("Ortega");
+		rafael.setId(3);
+		rafael.addSpecialty(specialty(1, "radiology"));
+		rafael.addSpecialty(specialty(2, "surgery"));
+		return rafael;
+	}
+
+	private Specialty specialty(int id, String name) {
+		Specialty specialty = new Specialty();
+		specialty.setId(id);
+		specialty.setName(name);
+		return specialty;
+	}
+
 	@BeforeEach
 	void setup() {
-		given(this.vets.findAll()).willReturn(Lists.newArrayList(james(), helen()));
+		given(this.vets.findAll()).willReturn(Lists.newArrayList(james(), helen(), rafael()));
 		given(this.vets.findAll(any(Pageable.class)))
 			.willReturn(new PageImpl<Vet>(Lists.newArrayList(james(), helen())));
+		// dentistry is a known specialty held by no veterinarian.
+		given(this.vets.findSpecialties()).willReturn(
+				Lists.newArrayList(specialty(1, "radiology"), specialty(2, "surgery"), specialty(3, "dentistry")));
 
 	}
 
@@ -97,4 +125,58 @@ class VetControllerTests {
 			.andExpect(jsonPath("$.vetList[0].id").value(1));
 	}
 
+	@Test
+	void theSpecialtyDirectoryShouldListEverySpecialtyWithItsVeterinarians() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(view().name("vets/specialtyList"))
+			.andExpect(model().attribute("specialties", allOf(hasKey("radiology"), hasKey("surgery"))));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldShowVeterinarianByFullNameUnderSpecialty() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(containsString("Helen Leary")));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldOmitVeterinarianHoldingNoSpecialty() throws Exception {
+		// James Carter holds no specialty, so he never appears: the page indexes
+		// specialties and their holders, not the full veterinarian roster.
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(not(containsString("Carter"))));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePageWithoutPagination() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(model().attributeDoesNotExist("totalPages", "currentPage"))
+			.andExpect(model().attribute("specialties", aMapWithSize(3)));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldListSpecialtyWithNoVeterinarians() throws Exception {
+		// dentistry is known to the clinic but held by no veterinarian, so it is
+		// still listed with an empty set of holders.
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(model().attribute("specialties", hasEntry(is("dentistry"), empty())));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldShowVeterinarianUnderEachHeldSpecialty() throws Exception {
+		// Rafael Ortega holds radiology and surgery, so he appears under both.
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(model().attribute("specialties", allOf(
+					hasEntry(is("radiology"),
+							hasItem(allOf(hasProperty("firstName", is("Rafael")),
+									hasProperty("lastName", is("Ortega"))))),
+					hasEntry(is("surgery"), hasItem(
+							allOf(hasProperty("firstName", is("Rafael")), hasProperty("lastName", is("Ortega"))))))));
+	}
+
 }
```

</details>

## Pipeline

### REQ-VET-003 — Specialty directory: veterinarians grouped by specialty

2 review rounds · 3 build-passes · **1 build-failure** · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | **✔** | **✔** |
| **test** | ✎ (3) | **✔** |
| **security** | **✔** | **✔** |
| **doc** | **✖** (4) | **✔** |

- ◇ **prd-entry** Specialty directory: veterinarians grouped by specialty · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **minor** · (design) · ***◷ 30s***
- ◆ **implement** (implementer) · ***◷ 10m***
  - ▲ **build ✗ aborted: design-mismatch**
- ◈ **design-block** **minor** · (design) · supersedes L4 · ***◷ 58s***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · format · check · autofix-audit · handoff-log
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 26s***
- ✎ **review test** · **changes_requested** · (3 findings) · ***◷ 3m***
  - [autofix] `VetControllerTests.java:131,139,146,15` All six new test methods violate the BDD naming school mandated by testing-principles.md (§ Test Naming, effective 2026-07-31): method names start with 'should' instead of the required 'the{Subject}Should{Outcome}' form. The brief states: 'The naming school is BDD: the{Subject}Should{Outcome}.' All six methods are new tests written after the effective date and must conform.
    - fix: Prefix each method name with a subject noun. For example: shouldListEverySpecialtyWithItsVeterinarians -> theSpecialtyDirectoryShouldListEverySpecialtyWithItsVeterinarians; shouldShowVeterinarianByFullNameUnderSpecialty -> theSpecialtyDirectoryShouldShowVeterinarianByFullNameUnderSpecialty; shouldOmitVeterinarianHoldingNoSpecialty -> theSpecialtyDirectoryShouldOmitVeterinarianHoldingNoSpecialty; shouldRenderAllSpecialtiesOnOnePageWithoutPagination -> theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePageWithoutPagination; shouldListSpecialtyWithNoVeterinarians -> theSpecialtyDirectoryShouldListSpecialtyWithNoVeterinarians; shouldShowVeterinarianUnderEachHeldSpecialty -> theSpecialtyDirectoryShouldShowVeterinarianUnderEachHeldSpecialty.
  - [autofix] `VetControllerTests.java:101-103` The @BeforeEach setup() comment 'James holds no specialty; Helen holds radiology; Rafael holds radiology and surgery.' restates exactly what the three given() stubs directly below it say. testing-principles.md § Four-Phase Test Structure: 'never add prose that restates what the code already says.'
    - fix: Remove lines 101-103. The given() stubs and the factory methods james(), helen(), and rafael() are self-documenting.
  - [autofix] `VetControllerTests.java:177-178` shouldShowVeterinarianUnderEachHeldSpecialty checks only hasProperty("lastName", is("Ortega")) to confirm Rafael appears under both specialties, leaving firstName unverified. testing-principles.md § Assertions: 'Whole-object comparison — compare complete expected objects rather than picking apart fields.' A different vet sharing only the last name would satisfy this assertion; the test also fails to pin the full-name criterion the acceptance criteria state.
    - fix: Replace hasProperty("lastName", is("Ortega")) with allOf(hasProperty("firstName", is("Rafael")), hasProperty("lastName", is("Ortega"))) in both hasEntry calls (lines 177 and 178).
- ✔ **review code-quality** · **approved** · ***◷ 4m***
- ✖ **review doc** · **blocked** · (4 findings) · ***◷ 8m***
  - **[blocked]** `system-design.md:105` The CacheConfiguration row description ends with 'Each no-arg read holds its own named cache so their results never share a key'. The clause 'so their results never share a key' is rationale prose explaining the purpose of the two-cache design — a 'why' explanation prohibited in system-design.md. Rationale belongs in an ADR with a back-link; the design doc carries only the rule. The phrase 'no-arg read' additionally ties the description to the current zero-argument method signatures and silently fails the self-test: if either findAll() or findSpecialties() gains a parameter, this phrase becomes wrong without any source change touching this row. Class sweep of the other changed rows found no further 'why' clauses.
  - [clarify] `prd.md:137,142` Two inline 'because' clauses introduce rationale into the PRD. Line 137 narrative: 'Because it indexes specialties rather than people, a veterinarian who holds no specialty appears under none'. Line 142 Done-when bullet: 'then that veterinarian is not listed, because the directory indexes specialties and their holders rather than the full veterinarian roster'. The PRD boundary rule prohibits 'why' content; rationale belongs in an ADR. The prohibited-pattern table lists 'paragraphs explaining why' as Critical — these are single-sentence clauses, making severity borderline. The Done-when bullet at line 142 runs to 32 words (above the 30-word limit), with the excess being the 'because' clause. Question for product-requirements-expert: does the 'because' clause qualify as scope-defining behavioral description that can remain, or as decision rationale that should move to an ADR with a back-link?
  - [autofix] `prd.md:137` The sentence 'A specialty directory lists every specialty the clinic knows by its stored name, and under each the veterinarians who hold it, each shown by full name — first name then last name, such as "Helen Leary".' runs to 35 words, exceeding the 30-word sentence limit. The example 'Helen Leary' is preserved in the Done-when bullet at line 141.
    - fix: A specialty directory lists every specialty the clinic knows by its stored name. Under each, the veterinarians who hold it are shown by full name, listed first name then last name.
  - [clarify] `system-design.md:103-105` The compound term 'specialty directory' is introduced and used throughout the new PRD section and in three rows of the system-design.md Contracts table, but it has no entry in docs/ubiquitous-language.md, and the change set does not include an update to that file. The cross-document coherence check requires domain terms used in prd.md or system-design.md to be defined in (or added to) docs/ubiquitous-language.md in the same change.
- ✚ **prd-autofix** `docs/prd.md` · writing-standards · (root)
- ↻ **implement** (implementer) ← test · (3 findings)
- ↻ **fix design** ← doc · (4 findings)
- ◈ **design-block** **minor** · (design) · supersedes L8 · ***◷ 1m***
- ▲ **build-pass** 10:10 · build, test, format, handoff-log, autofix-audit
- • review-plan (review-plan-engine)
- ↻ **fix prd-expert** ← doc · (4 findings)
- ◇ **prd-entry** Specialty directory: veterinarians grouped by specialty · (prd-expert) · ***◷ 31s***
- ◈ **design-block** **covered** · (design) · supersedes L23 · ***◷ 23s***
- ◆ **implement** (implementer) · ***◷ 1m***
  - ▲ **build ✓ clean** · build · test · check · autofix-audit · handoff-log
- • review-plan (review-plan-engine)
- ✔ **review security** · **approved** · ***◷ 39s***
- ✔ **review code-quality** · **approved** · ***◷ 57s***
- ✔ **review doc** · **approved** · ***◷ 2m***
- ✔ **review test** · **approved** · ***◷ 3m***
- ◆ **grade CLEAR** · add read-only specialty directory view
  - blast_radius — **clear** — Additive read-only feature: one new GET route, one new cached @Query read, a second named cache alongside the existing one, plus a new template. Three modules but all within the vet feature and one cache-config bean; no sensitive paths, no modification of existing behavior.
  - semantic_surprise — **clear** — Grouping logic reads exactly as the inverse-directory description implies: specialties enumerated independently and sorted, holders filtered by name-match and sorted by last-then-first name, empty specialties preserved via LinkedHashMap. The separate specialties cache correctly avoids the SimpleKey.EMPTY collision the ADR documents. No inverted operators or hidden behavior.
  - test_adequacy — **clear** — Six MockMvc tests assert real outcomes over the changed behavior and every stated edge case: empty specialty (dentistry maps to empty), multi-specialty vet (Rafael under both), omission of specialty-less vet (Carter absent), and no-pagination. Repository mocking is the sanctioned MockMvc controller-test boundary; the grouping under test is real.
  - reviewer_hedging — **clear** — Full four-reviewer battery all approved with empty findings lists. Round-1 autofix items (test naming, redundant comment, weak assertions) were applied and round 2 approved clean. No escalate, no bar_clause, no lingering caveats.
  - scope_deviation — **clear** — design_revisions=3 (the design evolved toward the two-cache approach, captured in a new ADR) but build_retries and consultations are zero and the final diff sits squarely on REQ-VET-003 stated surface: unpaged inverse directory, empty specialties listed, multi-specialty vets under each. No wandering past the requirement.
  - why — Additive read-only inverse-directory view; grouping logic matches the spec, the separate named cache correctly dodges the no-arg key collision the ADR documents, and six tests cover every stated edge case. Full roster approved clean. Confirm and merge with a quick read.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- GET /specialties.html takes no user input (Model-only controller signature); no injection surface reaches any sink
- VetRepository.findSpecialties() uses a static parameterless JPQL query (SELECT s FROM Specialty s) with no concatenation — no SQL/JPQL injection
- specialtyList.html renders all dynamic values (specialty name, vet full name) via auto-escaping th:text; no th:utext, no [[...]] inlining, no attribute injection — no XSS
- No secrets or credentials introduced
- No new dependencies and no build.gradle change — no supply-chain exposure added
- Unauthenticated read-only route is consistent with the confirmed demonstration security posture; no new trust boundary (design-block line 8)

**test-reviewer**

- All six PRD acceptance criteria have a dedicated passing test: specialty listing (shouldListEverySpecialtyWithItsVeterinarians), full-name rendering (shouldShowVeterinarianByFullNameUnderSpecialty), vet-with-no-specialty omitted (shouldOmitVeterinarianHoldingNoSpecialty), single-page no-pagination (shouldRenderAllSpecialtiesOnOnePageWithoutPagination), specialty-held-by-no-vet still listed (shouldListSpecialtyWithNoVeterinarians), multi-specialty vet under each specialty (shouldShowVeterinarianUnderEachHeldSpecialty).
- Both product-owner edge cases are covered with realistic seed data: dentistry maps to an empty holder list; Rafael Ortega appears under both radiology and surgery in the model.
- MockMvc plus @MockitoBean VetRepository is the correct pattern for a @WebMvcTest slice — the repository is the persistence boundary, mocking it is the only practical option when the full persistence layer is not loaded, and the existing suite already uses this shape.
- Factory methods james(), helen(), rafael(), and specialty(int, String) wrap all test-object construction, satisfying testing-principles.md § Test Data Construction.
- Tests are linear (no branching or loops), independent (no shared mutable state), and all pass on ./gradlew test with jacocoTestReport completing cleanly.
- Template full-name rendering is verified via rendered response body (containsString("Helen Leary")), confirming the Thymeleaf expression produces the required first-then-last output.

**code-quality-reviewer**

- Format check passes clean (checkFormatMain and checkFormatTest both UP-TO-DATE)
- Naming compliant with architecture-principles.md: VetController, VetRepository, CacheConfiguration, showSpecialtyList, groupVeterinariansBySpecialty, holdersOf, findSpecialties all follow the naming table
- Spring Boot idioms correct: constructor injection, @GetMapping, @Cacheable with named caches, @Transactional(readOnly=true), @Query for JPQL
- Two named JCache caches correctly separate the no-arg findAll (SimpleKey.EMPTY under 'vets') from findSpecialties (SimpleKey.EMPTY under 'specialties') — no key collision
- Specialty ManyToMany is EAGER-fetched so the stream over vet.getSpecialties() inside holdersOf() triggers no N+1 queries once the vet collection is cached
- Collectors.toList() in VetController:97 mirrors the existing Vet.java:63 usage in the same package — consistent with codebase style
- groupVeterinariansBySpecialty() correctly uses LinkedHashMap to preserve insertion order after sorting, and decomposes into a focused holdersOf() helper under 30 lines
- Template inherits UTF-8 from the layout fragment; i18n keys (specialties, name, vets, none) are all pre-existing keys — no new locale keys required
- Factory methods james(), helen(), rafael(), specialty() follow the testing-principles data-naming convention; test names follow BDD shouldXxx convention
- Package placement stays within vet; CacheConfiguration in system package unchanged; no cross-module dependency introduced

**doc-reviewer**

- NG-2 unchanged and non-contradicted: REQ-VET-003 is a read-only view; it introduces no management of veterinarians or specialties
- REQ-VET-001 and REQ-VET-003 read as non-contradictory: VET-001 is vet-centric, paginated, and shows specialty-less vets as having none; VET-003 is specialty-centric, unpaged, and omits specialty-less vets — each behavior follows from its stated model, and the PRD articulates the distinction clearly
- HTML anchor \<a id="req-vet-003">\</a> is present at first mention in docs/prd.md (line 135)
- No Java code blocks, pseudocode, or Spring-specific constructs in the new PRD section
- Design links use full path system-design.md#contracts; the heading anchor resolves at docs/system-design.md:72
- REQ-VET-003 correctly wired into the Contracts table Implements column for Vet, Specialty, VetRepository, VetController, and CacheConfiguration rows
- Deprecated REQ-VET-002 is absent from all changed rows

**security-reviewer**

- Round-2 delta is test-only (VetControllerTests.java) plus docs (prd, system-design, new two-cache ADR); no new attack surface, no new dependencies, no secrets
- specialtyList.html renders all DB-derived content via Thymeleaf th:text, which HTML-escapes output by construction — no XSS sink
- Production code (VetController, VetRepository, CacheConfiguration) unchanged since round-1 approval; no injection, path-traversal, deserialization, or authz boundary introduced

**code-quality-reviewer**

- checkFormat passes with no violations
- New test method names follow the{Subject}Should{Outcome} convention
- Factory methods rafael() and specialty(int,String) are short, single-responsibility, and free of side effects
- All ten new static imports are exercised; no dead imports introduced
- Fixture comment on rafael() explains multi-specialty rationale clearly

**doc-reviewer**

- Resolution 1 (CacheConfiguration row): The rewritten row is now at rule level — describes caches by role (veterinarian read, specialty-directory read) rather than transcribing literals or coupling to argument shape. The rationale and key-collision reasoning are in the new ADR. The inline ADR link resolves correctly to docs/adr/2026-08-06-named-cache-per-cached-read.md.
- Resolution 1 (new ADR): Follows the template; Status, Context, Options Considered, Decision, Consequences, Implementation, References all present. Implementation section cites REQ-VET-001 and REQ-VET-003 correctly. References back-links to the Contracts section of system-design.md using an em-dashed link text. ADR index entry in docs/adr/README.md is present, dated 2026-08-06, title matches the ADR H1.
- Resolution 2 (prd.md line 137 autofix): Applied fix stands; current prose is clean behavioral narrative without the autofix-target flaw.
- Resolution 3 (prd.md lines 137 and 142 because-clauses): The PRD owner's ruling holds — the retained content specifies behavior (name format, worked example) rather than decision rationale. The current Done-when bullets are plain declaratives in given/when/then form.
- Resolution 4 (specialty directory not in ubiquitous-language.md): The ruling holds. The ubiquitous-language guidance restricts entries to domain concepts; specialty directory is a presentation compound (the canonical term Specialty plus the plain descriptor directory), directly parallel to the pre-existing uncatalogued veterinarian directory. Specialty and Veterinarian are both defined. The compound is compositionally unambiguous.
- NG-2 coherence: reads correctly — brief inline rationale in a designated Rationale column is the expected non-goals format across every row.
- REQ-VET-001 vs REQ-VET-003 coherence: non-contradictory. REQ-VET-001 lists vets with their specialties (paged; no-specialty shown as none). REQ-VET-003 lists specialties with their holders (unpaged; no-specialty vets omitted). The two views are orthogonal and additive.
- Class sweep (signature-coupled details across contracts table): no residual no-arg, annotation, or cache-implementation literals found in docs/system-design.md beyond the one corrected row.

**test-reviewer**

- All three round-1 autofix findings correctly applied: six test methods renamed to the{Subject}Should{Outcome} form, redundant @BeforeEach comment removed, both hasEntry calls in theSpecialtyDirectoryShouldShowVeterinarianUnderEachHeldSpecialty strengthened to allOf(hasProperty("firstName",is("Rafael")),hasProperty("lastName",is("Ortega")))
- All six REQ-VET-003 acceptance criteria and both prd.md edge cases have dedicated, passing test methods
- VetControllerTests: 8 tests, 0 failures, 0 skipped — BUILD SUCCESSFUL
- Vet package line coverage 100%; overall project line coverage 93.2%, exceeds the 80% target
- Factory methods (james(), helen(), rafael(), specialty()) encapsulate test object construction per the testing brief
- Mocking policy respected: @MockitoBean on VetRepository is tolerated pre-existing usage; MockMvc is the sanctioned web-layer harness
- Four-phase structure maintained; no phase comments in any test body

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 4 | opus-4-8 | $9.10 | 18m 16s | 92% |
| `spring-boot-claude:system-design-expert` | 4 | opus-4-8 | $7.64 | 8m 48s | 72% |
| `(parent)` | 1 | opus-5 | $5.27 | 51m 1s | 96% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $3.99 | 7m 0s | 71% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $2.24 | 12m 18s | 85% |
| `spring-boot-claude:security-reviewer` | 2 | opus-4-8 | $1.90 | 1m 37s | 67% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $1.70 | 7m 13s | 87% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $1.50 | 2m 18s | 85% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $1.44 | 6m 1s | 86% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.07 | 0s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $5.27 | 51m 1s | 96% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $5.16 | 11m 9s | 94% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $2.79 | 2m 41s | 74% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $2.17 | 3m 49s | 67% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $2.03 | 3m 3s | 75% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.83 | 3m 34s | 92% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.82 | 3m 11s | 75% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.53 | 1m 44s | 64% |
| `spring-boot-claude:change-grader` | opus-4-8 | $1.50 | 2m 18s | 85% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $1.45 | 9m 16s | 85% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.29 | 1m 18s | 72% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.10 | 2m 2s | 87% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $1.06 | 4m 53s | 89% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.00 | 1m 31s | 86% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $1.00 | 46s | 63% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.90 | 51s | 70% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.86 | 3m 32s | 86% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.84 | 3m 41s | 87% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.79 | 3m 1s | 86% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.39 | 1m 7s | 74% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.07 | 0s | 0% |

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
- model requested `claude-opus-5`; models used: opus-4-8 · opus-5 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `9c6fd220a549ce32` · `2.1.222 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
