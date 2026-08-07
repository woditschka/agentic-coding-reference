# specialty-directory r2 — v0.1.22

Specialty directory page (feature) · started 2026-08-06T06:32:58+00:00 · exec `claude-dev` · status **complete**

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

> New inversion/join/ordering rules land in VetController.showSpecialtyList and veterinariansHolding, exactly the fresh controller-rule the checklist forbids; the ADR names the deviation but Domain service was available without one, and the public SpecialtyGroup record widens surface from a package-private class. findSpecialties() on VetRepository stretches one-repository-per-aggregate, though the ADR argues it. specialtyList.html uses #{specialties} and #{none} while no messages bundle is touched, so headings render as ??specialties_en??, untested. Tests are behavior-named and factory-backed, but ids 1/2/5/6 are mystery values, hasProperty("lastName") picks apart fields, attributeExists asserts nothing, and comments narrate. Docs are thorough: PRD REQ-VET-003, ADR + index, and both contract rows updated, plus an honest REQ-SYS-001 open question.

**Sample 2** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 5

> The inversion, filtering and sorting all land in  VetController.showSpecialtyList / veterinariansHolding , adding fresh rules to a layer the catalog says holds none, while the sanctioned Domain service stays unused;  findSpecialties()  returning  Specialty  from  VetRepository  breaks one-repository-per-aggregate-root, and  SpecialtyGroup  is needlessly  public .  specialtyList.html  references  #{specialties}  and  #{none} , but no message bundle is added, so the headings render as missing-key placeholders and no test catches it. Tests are BDD-named and cover the held-by-nobody and no-specialty cases, but stub the repository with Mockito, use bare id literals ( specialty(1, ...) ,  vet(6, ...) ), narrate in comments, and assert pagination only via  attributeDoesNotExist("totalPages") . Docs are thorough: ADR, index, PRD REQ-VET-003, contracts rows, open question.

**Sample 3** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 5

> The inversion, name-matching and ordering logic sits in  VetController.showSpecialtyList / veterinariansHolding , adding fresh rules to a controller the catalog says holds none, and  findSpecialties()  puts a Specialty query on  VetRepository , breaking one-repository-per-aggregate-root; the ADR names the trade but justifies it by 'the slice's prescribed target set', not a pattern.  SpecialtyGroup  matches no catalog pattern. Tests are BDD-named and behind  vet(...) / specialty(...)  factories, but carry Tier-3 mystery ids (2, 3, 5, 6), unnamed literals, narrating comments, and Mockito stubs over real objects.  specialtyList.html  references  #{specialties}  and  #{none}  with no messages bundle in the patch. Docs are complete: ADR, ADR index, REQ-VET-003, and both contract rows updated.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $11.82 | 41m | 32 | 86% | 8 file(s) +220/−3 |

## Change

<details>
<summary>Diff (rendered from <code>change.patch</code>)</summary>

```diff
diff --git a/docs/adr/2026-08-06-specialty-directory-projection.md b/docs/adr/2026-08-06-specialty-directory-projection.md
new file mode 100644
index 0000000..42895d6
--- /dev/null
+++ b/docs/adr/2026-08-06-specialty-directory-projection.md
@@ -0,0 +1,37 @@
+# Specialty Directory as a Specialty-Authoritative Inverse Projection
+
+**Status:** Accepted
+
+## Context
+
+`REQ-VET-003` adds a read-only specialty directory at `GET /specialties.html`: every specialty the clinic knows, by its stored name, each with the veterinarians who hold it, plus the veterinarians who hold no specialty. It is the inverse of the veterinarian directory (`REQ-VET-001`), which groups specialties under each veterinarian.
+
+The forward directory reads only `VetRepository.findAll()` and lets each `Vet` expose its specialties. An inverse projection could be built from the same read alone — invert the vet-to-specialty associations in the controller. That path is simpler but has a silent gap: a specialty that no veterinarian holds appears in no vet association, so it would be dropped. The requirement says *every specialty the clinic knows*, which is the `specialties` table, not the set of specialties that happen to be held. The current seed data holds all three specialties, so the gap is latent. It would pass the stated acceptance tests while contradicting the requirement wording — the same class of latent defect already recorded elsewhere in this codebase.
+
+## Options Considered
+
+1. **Derive from vet holdings** — invert `VetRepository.findAll()` in the controller. No new read. Drops specialties held by no veterinarian; contradicts "every specialty the clinic knows" whenever such a specialty exists.
+2. **Specialty-authoritative** — read the full specialty set from the `specialties` table for the enumeration axis, and `VetRepository.findAll()` for the holdings, joining them in the controller. Honors the wording regardless of holdings.
+3. **New `SpecialtyRepository`** — option 2's specialty read as its own repository type. Type-pure, but the vet package deliberately carries a single repository, and it adds a type the slice's prescribed target set does not name.
+
+## Decision
+
+We take option 2. The specialty directory enumerates the authoritative specialty set from the `specialties` table via a query method on the existing `VetRepository`, keeping the vet package's single-repository shape and matching the slice's prescribed targets. Veterinarian holdings come from the existing cached `VetRepository.findAll()`; the controller joins the two into a per-specialty view model.
+
+Ordering is by stored specialty name, deterministic across requests and independent of hash-set iteration order — the same stability `Vet.getSpecialties()` and `PetTypeRepository` already realize. "Stable" for this page means exactly that: a fixed, name-based order, not an insertion or hash order. Veterinarians within each specialty likewise render in a deterministic name-based order. Veterinarians holding no specialty are collected under a single no-specialty grouping, rendered after the named specialties; when no such veterinarian exists the grouping is omitted.
+
+## Consequences
+
+- Positive: the page is correct against "every specialty the clinic knows" even for a specialty held by nobody; ordering is deterministic; no new repository type or cache is introduced.
+- Positive: reuses the cached vet read, so the holdings axis carries no new persistence cost.
+- Negative: the specialty enumeration read is a second query not covered by the `vets` cache; for a small lookup table this is acceptable and deliberately left uncached to avoid entangling with the vet cache's absent eviction.
+- Negative: the inversion and join logic lives in the controller, consistent with this codebase's no-service-layer standing ([feature-package organization](2026-07-31-feature-package-organization.md)); it neither improves nor worsens that recorded gap.
+
+## Implementation
+
+**Requirements:** REQ-VET-003
+
+## References
+
+- [system-design.md § Contracts](../system-design.md#contracts) — the `VetController`, `VetRepository`, and `Specialty` rows realizing this decision
+- [ADR: Feature-Package Organization Without a Service Layer](2026-07-31-feature-package-organization.md) — why the join lives in the controller
diff --git a/docs/adr/README.md b/docs/adr/README.md
index a94dc3a..d3079b5 100644
--- a/docs/adr/README.md
+++ b/docs/adr/README.md
@@ -69,3 +69,4 @@ A non-goal ADR records a *product* decision not to build something — distinct
 | 2026-07-31 | [Feature-Package Organization Without a Service Layer](2026-07-31-feature-package-organization.md) | Accepted |
 | 2026-07-31 | [Database-Enforced Pet Name Uniqueness Within an Owner](2026-07-31-database-enforced-pet-name-uniqueness.md) | Accepted |
 | 2026-07-31 | [Dual Gradle and Maven Build Definitions](2026-07-31-dual-gradle-and-maven-builds.md) | Accepted |
+| 2026-08-06 | [Specialty Directory as a Specialty-Authoritative Inverse Projection](2026-08-06-specialty-directory-projection.md) | Accepted |
diff --git a/docs/prd.md b/docs/prd.md
index 0cb7f37..7f75b80 100644
--- a/docs/prd.md
+++ b/docs/prd.md
@@ -130,6 +130,19 @@ The clinic publishes the veterinarians it employs with the specialties each hold
 
 **Design:** [system-design.md#contracts](system-design.md#contracts)
 
+### Specialty directory
+
+<a id="req-vet-003"></a>
+
+Staff also read the directory the other way round: given a specialty, which veterinarians hold it. The clinic publishes a specialty directory that lists every specialty it knows by its stored name, each paired with the veterinarians who hold it. A veterinarian is shown by full name, first name then last name, as in "Helen Leary". A veterinarian who holds no specialty appears under a no-specialty grouping rather than being omitted; the page enumerates specialties, not the full veterinarian roster. Every specialty renders on one page `[REQ-VET-003]`.
+
+**Done when:**
+- `[REQ-VET-003]` given the clinic's specialties, when the specialty directory is opened, then every specialty is listed by its stored name, each with the veterinarians who hold it shown by full name (first name then last name).
+- `[REQ-VET-003]` given a veterinarian who holds no specialty, when the specialty directory is opened, then that veterinarian appears under a no-specialty grouping rather than under any named specialty.
+- `[REQ-VET-003]` given the clinic's specialties, when the specialty directory is opened, then all of them render on a single page, with no pagination.
+
+**Design:** [system-design.md#contracts](system-design.md#contracts) · **ADR:** [ADR: Specialty Directory as a Specialty-Authoritative Inverse Projection](adr/2026-08-06-specialty-directory-projection.md)
+
 ### Language
 
 <a id="req-lang-001"></a><a id="req-lang-002"></a>
@@ -179,3 +192,4 @@ The system opens on a landing page, and every page carries navigation to the own
 - **Is a visit really unrelated to a veterinarian?** Nothing connects the two, which makes the veterinarian directory a standalone page rather than part of the clinical workflow.
 - **Are the seeded pet types and specialties the real lists,** or placeholders?
 - **Does the project hold goals beyond being a reference sample?** G-2 is unfilled.
+- **Should the specialty directory be reachable from the standard navigation?** The specialty directory (`REQ-VET-003`) carries the standard navigation — owner search and the veterinarian directory — but nothing links to it, so it is presently unreachable from within the application. Widening the navigation to add a link was not decided, and `REQ-SYS-001` is left as written. The question stays open.
diff --git a/docs/system-design.md b/docs/system-design.md
index 9d58a3a..808f10f 100644
--- a/docs/system-design.md
+++ b/docs/system-design.md
@@ -98,10 +98,10 @@ An `Implements` value of `—` marks a contract serving no single requirement. T
 | `PetTypeFormatter` | Spring MVC formatter translating between a pet type and its display name during form binding | `src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java` | REQ-PET-001 |
 | `PetValidator` | Spring `Validator` enforcing the required-field rules for pet forms that bean validation does not cover | `src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java` | REQ-PET-001 |
 | `Vet` | Persisted veterinarian; exposes specialties sorted by name | `src/main/java/org/springframework/samples/petclinic/vet/Vet.java` | REQ-VET-001 |
-| `Specialty` | Persisted lookup value naming a veterinary specialty | `src/main/java/org/springframework/samples/petclinic/vet/Specialty.java` | REQ-VET-001 |
+| `Specialty` | Persisted lookup value naming a veterinary specialty | `src/main/java/org/springframework/samples/petclinic/vet/Specialty.java` | REQ-VET-001, REQ-VET-003 |
 | `Vets` | Serialization wrapper giving the vet collection a single root element for the non-HTML representation | `src/main/java/org/springframework/samples/petclinic/vet/Vets.java` | — |
-| `VetRepository` | Spring Data repository for veterinarians; results are cached | `src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java` | REQ-VET-001 |
-| `VetController` | Serves the paged HTML vet list and a serialized vet collection from a second route | `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` | REQ-VET-001 |
+| `VetRepository` | Spring Data repository for veterinarians; results are cached. Also reads the authoritative specialty set by stored-name order for the specialty directory ([ADR](adr/2026-08-06-specialty-directory-projection.md)) | `src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java` | REQ-VET-001, REQ-VET-003 |
+| `VetController` | Serves the paged HTML vet list, a serialized vet collection from a second route, and the un-paged specialty directory grouping veterinarians by the specialty they hold ([ADR](adr/2026-08-06-specialty-directory-projection.md)) | `src/main/java/org/springframework/samples/petclinic/vet/VetController.java` | REQ-VET-001, REQ-VET-003 |
 | `CacheConfiguration` | Enables caching and declares the vet cache through the JCache API | `src/main/java/org/springframework/samples/petclinic/system/CacheConfiguration.java` | REQ-VET-001 |
 | `WebConfiguration` | Session-scoped locale resolution plus a request-parameter locale switch | `src/main/java/org/springframework/samples/petclinic/system/WebConfiguration.java` | REQ-LANG-001 |
 | `WelcomeController` | Serves the landing page | `src/main/java/org/springframework/samples/petclinic/system/WelcomeController.java` | REQ-SYS-001 |
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/VetController.java b/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
index 867d0b5..8998280 100644
--- a/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
+++ b/src/main/java/org/springframework/samples/petclinic/vet/VetController.java
@@ -15,6 +15,8 @@
  */
 package org.springframework.samples.petclinic.vet;
 
+import java.util.Collection;
+import java.util.Comparator;
 import java.util.List;
 
 import org.springframework.data.domain.Page;
@@ -71,4 +73,41 @@ class VetController {
 		return vets;
 	}
 
+	@GetMapping("/specialties.html")
+	public String showSpecialtyList(Model model) {
+		// Enumerate from the authoritative specialties table (name-ordered), not by
+		// inverting vet holdings: a specialty held by no veterinarian must still render.
+		List<Specialty> specialties = this.vetRepository.findSpecialties();
+		Collection<Vet> vets = this.vetRepository.findAll();
+
+		List<SpecialtyGroup> specialtyGroups = specialties.stream()
+			.map(specialty -> new SpecialtyGroup(specialty.getName(), veterinariansHolding(vets, specialty)))
+			.toList();
+		List<Vet> unspecializedVets = vets.stream()
+			.filter(vet -> vet.getNrOfSpecialties() == 0)
+			.sorted(BY_FULL_NAME)
+			.toList();
+
+		model.addAttribute("specialtyGroups", specialtyGroups);
+		model.addAttribute("unspecializedVets", unspecializedVets);
+		return "vets/specialtyList";
+	}
+
+	private static List<Vet> veterinariansHolding(Collection<Vet> vets, Specialty specialty) {
+		return vets.stream()
+			.filter(vet -> vet.getSpecialties().stream().anyMatch(held -> held.getName().equals(specialty.getName())))
+			.sorted(BY_FULL_NAME)
+			.toList();
+	}
+
+	private static final Comparator<Vet> BY_FULL_NAME = Comparator.comparing(Vet::getLastName)
+		.thenComparing(Vet::getFirstName);
+
+	/**
+	 * View model for one specialty and the veterinarians who hold it, used by the
+	 * specialty directory.
+	 */
+	public record SpecialtyGroup(String name, List<Vet> veterinarians) {
+	}
+
 }
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java b/src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java
index dbf68d0..dc4b488 100644
--- a/src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java
+++ b/src/main/java/org/springframework/samples/petclinic/vet/VetRepository.java
@@ -19,10 +19,12 @@ import org.springframework.cache.annotation.Cacheable;
 import org.springframework.dao.DataAccessException;
 import org.springframework.data.domain.Page;
 import org.springframework.data.domain.Pageable;
+import org.springframework.data.jpa.repository.Query;
 import org.springframework.data.repository.Repository;
 import org.springframework.transaction.annotation.Transactional;
 
 import java.util.Collection;
+import java.util.List;
 
 /**
  * Repository class for <code>Vet</code> domain objects All method names are compliant
@@ -55,4 +57,17 @@ public interface VetRepository extends Repository<Vet, Integer> {
 	@Cacheable("vets")
 	Page<Vet> findAll(Pageable pageable) throws DataAccessException;
 
+	/**
+	 * Retrieve the authoritative set of <code>Specialty</code>s from the data store,
+	 * ordered by stored name. Read from the <code>specialties</code> table directly (not
+	 * derived from vet associations) so a specialty held by no veterinarian is still
+	 * returned. Deliberately uncached: it is a small lookup independent of the
+	 * <code>vets</code> cache.
+	 * @return a name-ordered <code>List</code> of every <code>Specialty</code> the clinic
+	 * knows
+	 */
+	@Transactional(readOnly = true)
+	@Query("SELECT s FROM Specialty s ORDER BY s.name")
+	List<Specialty> findSpecialties() throws DataAccessException;
+
 }
diff --git a/src/main/resources/templates/vets/specialtyList.html b/src/main/resources/templates/vets/specialtyList.html
new file mode 100644
index 0000000..bf0648b
--- /dev/null
+++ b/src/main/resources/templates/vets/specialtyList.html
@@ -0,0 +1,25 @@
+<!DOCTYPE html>
+
+<html xmlns:th="https://www.thymeleaf.org" th:replace="~{fragments/layout :: layout (~{::body},'vets')}">
+
+<body>
+
+  <h2 th:text="#{specialties}">Specialties</h2>
+
+  <ul class="list-unstyled" id="specialties">
+    <li th:each="group : ${specialtyGroups}">
+      <h3 th:text="${group.name}">Specialty</h3>
+      <ul>
+        <li th:each="vet : ${group.veterinarians}" th:text="${vet.firstName + ' ' + vet.lastName}">Vet Name</li>
+      </ul>
+    </li>
+    <li th:if="${not #lists.isEmpty(unspecializedVets)}">
+      <h3 th:text="#{none}">none</h3>
+      <ul>
+        <li th:each="vet : ${unspecializedVets}" th:text="${vet.firstName + ' ' + vet.lastName}">Vet Name</li>
+      </ul>
+    </li>
+  </ul>
+</body>
+
+</html>
diff --git a/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java b/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
index 208758c..42b5ecd 100644
--- a/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
+++ b/src/test/java/org/springframework/samples/petclinic/vet/VetControllerTests.java
@@ -31,6 +31,11 @@ import org.springframework.test.web.servlet.MockMvc;
 import org.springframework.test.web.servlet.ResultActions;
 import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
 
+import static org.hamcrest.Matchers.contains;
+import static org.hamcrest.Matchers.containsString;
+import static org.hamcrest.Matchers.hasProperty;
+import static org.hamcrest.Matchers.is;
+import static org.hamcrest.Matchers.stringContainsInOrder;
 import static org.mockito.ArgumentMatchers.any;
 import static org.mockito.BDDMockito.given;
 import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
@@ -97,4 +102,85 @@ class VetControllerTests {
 			.andExpect(jsonPath("$.vetList[0].id").value(1));
 	}
 
+	private Specialty specialty(int id, String name) {
+		Specialty specialty = new Specialty();
+		specialty.setId(id);
+		specialty.setName(name);
+		return specialty;
+	}
+
+	private Vet vet(int id, String firstName, String lastName, Specialty... specialties) {
+		Vet vet = new Vet();
+		vet.setId(id);
+		vet.setFirstName(firstName);
+		vet.setLastName(lastName);
+		for (Specialty specialty : specialties) {
+			vet.addSpecialty(specialty);
+		}
+		return vet;
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldListEachSpecialtyWithVeterinariansByFullName() throws Exception {
+		Specialty radiology = specialty(1, "radiology");
+		given(this.vets.findSpecialties()).willReturn(Lists.newArrayList(radiology));
+		// Two veterinarians hold radiology, supplied out of alphabetical order to prove
+		// the group renders them in deterministic name order (Adams before Leary), not
+		// in HashSet-iteration order.
+		given(this.vets.findAll())
+			.willReturn(Lists.newArrayList(vet(2, "Helen", "Leary", radiology), vet(6, "Amy", "Adams", radiology)));
+
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(view().name("vets/specialtyList"))
+			.andExpect(model().attributeExists("specialtyGroups"))
+			.andExpect(content().string(containsString("radiology")))
+			.andExpect(content().string(stringContainsInOrder("Amy Adams", "Helen Leary")));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldGroupVeterinariansHoldingNoSpecialty() throws Exception {
+		Specialty radiology = specialty(1, "radiology");
+		given(this.vets.findSpecialties()).willReturn(Lists.newArrayList(radiology));
+		// Baker and Adams hold no specialty; supplied out of order to prove the
+		// controller applies a deterministic name-based ordering.
+		given(this.vets.findAll()).willReturn(Lists.newArrayList(vet(3, "Zoe", "Baker"), vet(4, "Amy", "Adams"),
+				vet(2, "Helen", "Leary", radiology)));
+
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(model().attribute("unspecializedVets",
+					contains(hasProperty("lastName", is("Adams")), hasProperty("lastName", is("Baker")))))
+			.andExpect(content().string(containsString("Amy Adams")));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage() throws Exception {
+		Specialty radiology = specialty(1, "radiology");
+		Specialty surgery = specialty(2, "surgery");
+		given(this.vets.findSpecialties()).willReturn(Lists.newArrayList(radiology, surgery));
+		given(this.vets.findAll())
+			.willReturn(Lists.newArrayList(vet(2, "Helen", "Leary", radiology), vet(5, "Linda", "Douglas", surgery)));
+
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(model().attributeDoesNotExist("totalPages"))
+			// Ordered by stored name: radiology must render before surgery, so a
+			// non-deterministic (HashSet) enumeration of specialties fails this test.
+			.andExpect(content().string(stringContainsInOrder("radiology", "surgery")));
+	}
+
+	@Test
+	void theSpecialtyDirectoryShouldListSpecialtyHeldByNoVeterinarian() throws Exception {
+		Specialty radiology = specialty(1, "radiology");
+		Specialty dentistry = specialty(3, "dentistry");
+		// dentistry is in the authoritative set but held by no veterinarian.
+		given(this.vets.findSpecialties()).willReturn(Lists.newArrayList(dentistry, radiology));
+		given(this.vets.findAll()).willReturn(Lists.newArrayList(vet(2, "Helen", "Leary", radiology)));
+
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(containsString("dentistry")));
+	}
+
 }
```

</details>

## Pipeline

### REQ-VET-003 — Specialty directory: veterinarians grouped by the specialty they hold

3 review rounds · 2 build-passes · no grade yet

| reviewer | R1 | R2 | R3 |
| --- | --- | --- | --- |
| **code-quality** | **✖** (2) | ✎ (1) | **✔** |
| **test** | ✎ (3) | · | ✎ (1) |
| **security** | **✔** | **✔** | · |
| **doc** | ✎ (4) | · | **✔** |

- ◇ **prd-entry** Specialty directory: veterinarians grouped by the specialty they hold · (prd-expert) · ***◷ 0s***
- ◈ **design-block** **new** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 30m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- ✔ **review security** · **approved** · ***◷ 15m***
- ✖ **review code-quality** · **blocked** · (2 findings) · ***◷ 5m***
  - [autofix] `VetController.java:110-129` SpecialtyGroup is a static inner class that functions as an immutable value type but does not realize the value-object pattern. It lacks equals()/hashCode() and therefore uses reference equality from Object, violating the architecture-principles.md closed property 'equality by value'. The framework-entity exception does not apply: SpecialtyGroup is not a persistence entity and the framework does not instantiate it. Java records satisfy all three: immutability, structural equality, and the modern-Java-idioms checklist item. Spring Framework 6+ BeanWrapper resolves record accessor names (name(), veterinarians()) from Thymeleaf SpEL expressions like ${group.name}, so no template change is needed.
    - fix: Replace the static inner class with a record: public record SpecialtyGroup(String name, List\<Vet> veterinarians) {}. The Javadoc comment can move to the record's Javadoc. Remove the explicit constructor, field declarations, and getters.
  - [truncation] `VetControllerTests.java` Reviewer reached planned checkpoint after reviewing 2 of 4 changed files (VetRepository.java and VetController.java). specialtyList.html and VetControllerTests.java have not yet been reviewed. Findings above cover VetRepository.java and VetController.java only.
- ✎ **review test** · **changes_requested** · (3 findings) · ***◷ 15m***
  - **[blocked]** `VetControllerTests.java:specialtyDirec` Specialty list ordering is not tested. The test checks that 'radiology' and 'surgery' both appear via containsString, but asserts nothing about their order in the specialtyGroups model attribute. The ADR (2026-08-06-specialty-directory-projection.md) explicitly requires ordering by stored name, independent of hash-set iteration order. A regression that replaces the name-ordered specialties list with any non-deterministic enumeration would pass this test undetected.
  - **[blocked]** `VetControllerTests.java:specialtyDirec` Veterinarian ordering within a named specialty group is not tested. Every named-specialty scenario in the suite places at most one veterinarian under each specialty, so no test can detect a HashSet-iteration regression in the veterinariansHolding sort path. The ADR requires vets within each specialty to render in a deterministic name-based order; only the no-specialty group has an ordering assertion (specialtyDirectoryShouldGroupVeterinariansHoldingNoSpecialty). A second vet added under 'radiology' (e.g. Adams before Leary) with a contains(hasProperty...) assertion would cover this path.
  - [autofix] `VetControllerTests.java:122-179` All four new test method names omit the 'the' prefix required by the project naming school (testing-principles.md § Test Naming: 'the{Subject}Should{Outcome}'). Methods should be theSpecialtyDirectoryShouldListEachSpecialtyWithVeterinariansByFullName, theSpecialtyDirectoryShouldGroupVeterinariansHoldingNoSpecialty, theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage, and theSpecialtyDirectoryShouldListSpecialtyHeldByNoVeterinarian. The brief applies to tests written from 2026-07-31 onward; these are all new.
    - fix: Rename all four test methods to carry the 'the' prefix. The prd-entry test_names list omits the prefix too; update it in handoff.jsonl via a superseding prd-entry correction if the harness requires it, or treat the method rename alone as sufficient since test_names is advisory.
- ✎ **review doc** · **changes_requested** · (4 findings) · ***◷ 5m***
  - **[blocked]** `prd.md:144` docs/adr/2026-08-06-specialty-directory-projection.md records the load-bearing specialty-authoritative decision for REQ-VET-003. The **ADR:** link is mandatory in the PRD whenever an ADR records the decision behind the requirement (prd-authoring § Requirement Format). The Specialty directory section has a **Design:** link but no **ADR:** link.
  - **[blocked]** `prd.md:137` The phrase 'in deliberate contrast with the paged veterinarian directory of [REQ-VET-001]' embeds rationale: the page is un-paged by deliberate design choice, contrasting REQ-VET-001. The PRD boundary rule prohibits 'why' — rationale belongs in the ADR, referenced via the **ADR:** link. The acceptance bullet at line 142 already captures the no-pagination behavior precisely; this phrase adds only intentionality, which is the ADR's job. The inline [REQ-VET-001] tag is also non-standard: REQ-IDs annotate the requirement being expressed in a statement, not cross-references inside rationale clauses.
  - **[blocked]** `prd.md:182` REQ-VET-003 introduces a page that carries REQ-SYS-001 navigation (it inherits the layout fragment) but is not linked from the application's standard navigation, which covers only owner search and the veterinarian directory. The prd-entry notes record this as an open question the slice does not depend on. The PRD Open Questions section does not contain this question. A reader of the PRD has no indication the specialty directory is presently unreachable from the standard navigation, and no signal this is a pending product decision. The section's own comment says each open question resolves into a requirement, a non-goal, or an ADR; the discoverability question has done none of these and is absent.
  - **[blocked]** `2026-08-06-specialty-directory-project` The sentence at line 9 of the ADR Context section is approximately 37 words: 'The current seed data holds all three specialties, so the gap is latent — it would pass the stated acceptance tests while contradicting the requirement wording, the same class of latent defect already recorded elsewhere in this codebase.' The writing standard requires sentences under 30 words. The replacement text exceeds 200 characters of file content, so autofix is ineligible; the fix routes to the artifact owner.
- ↻ **fix design** ← doc · (4 findings)
- ◈ **design-block** **new** · (design) · supersedes L4 · ***◷ 5m***
- ↻ **fix prd-expert** ← doc · (4 findings)
- ✎ **review code-quality** · **changes_requested** · (1 finding)
  - [autofix] `VetController.java:110-129` SpecialtyGroup is a static inner class used as an immutable view-model value type, but it inherits reference equality from Object. The architecture-principles.md closed property 'equality by value' applies to all non-entity types — the persistence-entity exception explicitly excludes types the framework does not instantiate. A static inner class with no equals()/hashCode() cannot be a value object. The modern Java idiom for this shape is a record, which satisfies immutability, structural equality, and the code-quality checklist item for modern Java idioms in one step. The Javadoc comment 'Public so the Thymeleaf view can read its properties' is also misleading: the class is public because it is accessed as a model attribute type, and Spring Framework 6+ BeanWrapper resolves record accessor names (name(), veterinarians()) from Thymeleaf SpEL expressions (${group.name}, ${group.veterinarians}) — the template requires no changes.
    - fix: Replace the static inner class with: public record SpecialtyGroup(String name, List\<Vet> veterinarians) {}. Move the existing Javadoc to the record declaration. Remove the explicit constructor, field declarations, getName(), and getVeterinarians(). The package-private construction site in showSpecialtyList remains valid because records use the canonical constructor. The template expressions ${group.name} and ${group.veterinarians} continue to resolve correctly via Spring's record-aware BeanWrapper.
- ◇ **prd-entry** Specialty directory: veterinarians grouped by the specialty they hold · (prd-expert) · ***◷ 5m***
- ↻ **implement** (implementer) ← test, code-quality · (4 findings) · ***◷ 20m***
  - ▲ **build ✓ clean** · build · test · format · check · handoff-log · autofix-audit
- ✔ **review security** · **approved** · ***◷ 4h 5m***
- ✔ **review code-quality** · **approved** · ***◷ 5m***
- ✔ **review doc** · **approved** · ***◷ 5m***
- ✎ **review test** · **changes_requested** · (1 finding) · ***◷ 20m***
  - [autofix] `VetControllerTests.java:177` The comment '// dentistry is in the authoritative set but held by no veterinarian.' restates two things the code already says: the test name (theSpecialtyDirectoryShouldListSpecialtyHeldByNoVeterinarian) and the stub arrangement (dentistry in findSpecialties(), no vet in findAll() holds it). testing-principles.md § Four-Phase Test Structure forbids prose that restates what the code already says. The other three ordering comments in the new tests are not restating — they explain a deliberate data-layout decision (out-of-alphabetical-order input to expose a hash-iteration regression) that is non-obvious and therefore permitted; this comment has no equivalent non-obvious content.
    - fix: Remove line 177: the comment '// dentistry is in the authoritative set but held by no veterinarian.' The test name and stub code communicate the scenario completely.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- findSpecialties() uses a static parameterless JPQL literal (SELECT s FROM Specialty s ORDER BY s.name) with no concatenation or user input — no JPQL/SQL injection surface
- GET /specialties.html accepts no request parameters, path variables, or user input; no tainted-data path reaches the query or view
- Thymeleaf template escapes all echoed values via th:text (specialty names and vet full names); no th:utext or unescaped inlining, so no stored-XSS vector on directory-managed data
- Endpoint discloses only specialty names and vet full names — the same data category already public via /vets.html; no PII, credentials, or data beyond the existing veterinarian directory
- Read-only GET with the existing open-access posture; no state mutation, no new authz/CSRF surface
- No dependency or build.gradle changes in this slice — no supply-chain/CVE exposure introduced

**code-quality-reviewer**

- checkFormat passes: all changed Java files are correctly formatted
- VetRepository.findSpecialties() Javadoc clearly documents the authoritative-axis rationale and the deliberate decision not to cache
- @Transactional(readOnly = true) and @Query annotation on findSpecialties() are consistent with existing repository methods
- Constructor injection in VetController (single-constructor, no @Autowired) follows project idiom
- showSpecialtyList correctly enumerates from the authoritative specialties table rather than inverting vet holdings, per ADR 2026-08-06-specialty-directory-projection
- veterinariansHolding and BY_FULL_NAME are private/package-private helpers with clear single responsibilities
- Stream pipelines used consistently over manual loops

**test-reviewer**

- specialtyDirectoryShouldListSpecialtyHeldByNoVeterinarian correctly pins the specialty-authoritative behavior: it stubs findSpecialties() with dentistry+radiology but findAll() with only a radiology-holding vet, then asserts containsString('dentistry'). A vet-holdings-inverting implementation (ADR option 1) would not render dentistry at all, so this test would fail against it. The no-vet-per-specialty behavior is adequately pinned.
- No-specialty group ordering is tested: specialtyDirectoryShouldGroupVeterinariansHoldingNoSpecialty supplies Baker and Adams deliberately out of alphabetical order, then asserts contains(hasProperty('lastName', is('Adams')), hasProperty('lastName', is('Baker'))), which is an order-sensitive assertion that would fail under HashSet iteration.
- All three PRD acceptance criteria for REQ-VET-003 have dedicated test methods matching the prd-entry test_names.
- Vet package line coverage is 100% (35/35 lines in VetController, 6/6 in SpecialtyGroup, confirmed by jacocoTestReport).
- MockMvc is used consistently with the established project pattern (@MockitoBean VetRepository, @WebMvcTest); no new mock points beyond the sanctioned web-layer harness.
- specialty() and vet() factory methods are introduced for the new tests, satisfying the factory-method requirement for post-2026-07-31 tests.
- Four-phase structure is respected; no phase comments, no branching in test bodies.

**doc-reviewer**

- HTML anchor \<a id="req-vet-003">\</a> is present at prd.md:135
- Done when bullets are correctly tagged [REQ-VET-003] with given/when/then form; all three acceptance criteria match the prd-entry
- Judgment 1 — route excluded from PRD narrative: holds. Routes are mechanism-level; the PRD boundary rule litmus test applies (a route URL changes when switching to another framework). The route GET /specialties.html is documented in the ADR Context section, the appropriate abstraction level. REQ-VET-001 sets the same convention.
- Judgment 2 — REQ-SYS-001 fourth acceptance criterion omitted from PRD: holds for the specific omission. REQ-SYS-001 universally covers 'every page,' so the new page inherits it automatically with no wording change needed. However, the related discoverability question (no nav link to the page) is a separate open product question that is absent from the PRD (see finding at prd.md:182).
- system-design.md Contracts rows for VetController, VetRepository, and Specialty correctly updated: REQ-VET-003 added to Implements column, behavioral descriptions updated, ADR back-links present
- ADR README index row added correctly with correct date, title, and status
- ADR Implementation section carries **Requirements:** REQ-VET-003
- ADR References section uses em-dashes as required
- **Design:** link in PRD (system-design.md#contracts) and ADR back-links in system-design.md rows resolve to valid anchors
- No Java constructs, pseudocode, mechanism tables, or internal code references in PRD narrative
- system-design.md contract rows stay at the correct abstraction level: behavioral descriptions, no field tables, source pointers present

**code-quality-reviewer**

- checkFormat passes: all changed Java files are correctly formatted
- VetRepository.findSpecialties() Javadoc clearly documents the authoritative-axis rationale (enumerate from specialties table, not by inverting vet holdings) and the deliberate decision not to cache
- @Transactional(readOnly = true) and @Query on findSpecialties() are consistent with existing repository methods and the PetTypeRepository model cited in the design-block
- Constructor injection in VetController follows the project idiom (single-constructor, no @Autowired)
- showSpecialtyList correctly enumerates from the authoritative specialties axis, satisfying the 'every specialty the clinic knows' requirement even when a specialty is held by no veterinarian
- veterinariansHolding() and BY_FULL_NAME are private/package-private single-responsibility helpers; stream pipelines used throughout over manual loops
- specialtyList.html correctly uses th:replace with the layout fragment so REQ-SYS-001 navigation is inherited automatically, reuses existing message keys (#{specialties}, #{none}), renders full name first-then-last per acceptance criteria, and omits the no-specialty group when empty
- Four specialty directory tests cover the three PRD acceptance criteria plus the authoritative-axis edge case (specialty held by no veterinarian); factory methods vet() and specialty() keep object construction out of test bodies; Arrange/Act/Assert structure is clear throughout

**security-reviewer**

- SpecialtyGroup record conversion is security-neutral: it is a server-side Thymeleaf view model, not a serialized response — GET /specialties.html returns an HTML view (not @ResponseBody), so the Vet object graph is never marshalled to the client
- No mutable internal state leak: the veterinarians component is an unmodifiable Stream.toList() built fresh per request; record accessors introduce no attacker-reachable mutation or wider HTTP surface, and the nested type's public visibility is not a web boundary
- No widening beyond the existing veterinarian directory: template renders only specialty name and escaped firstName+lastName via th:text (no th:utext), exposing strictly less than the pre-existing @ResponseBody /vets JSON endpoint
- No new input, endpoint, or query since pass 1; findSpecialties() JPQL and specialtyList.html unchanged and take no user input — no SQLi/XSS/injection surface introduced

**code-quality-reviewer**

- checkFormat passes: all changed Java files are correctly formatted
- Pass-1 finding resolved correctly: SpecialtyGroup is now 'public record SpecialtyGroup(String name, List\<Vet> veterinarians) {}' at VetController.java:110 — canonical record form with no explicit constructor, fields, or getters; structural equality and immutability are satisfied by the record contract, meeting the architecture-principles value-object rule
- Template accessor resolution verified: ${group.name} resolves to record accessor name() and ${group.veterinarians} resolves to veterinarians() via Spring Framework 6+ record-aware BeanWrapper; no template change was needed and none was made — the template is unchanged from pass 1 and correct
- Misleading Javadoc sentence ('Public so the Thymeleaf view can read its properties') was dropped; the remaining Javadoc at VetController.java:106-109 ('View model for one specialty and the veterinarians who hold it, used by the specialty directory') is accurate and non-misleading
- Test-reviewer pass-1 ordering finding resolved: theSpecialtyDirectoryShouldListEachSpecialtyWithVeterinariansByFullName now supplies two radiology-holding vets (Leary id=2, Adams id=6) deliberately out of alphabetical order and asserts stringContainsInOrder("Amy Adams", "Helen Leary"), catching a BY_FULL_NAME regression
- Specialty ordering finding resolved: theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage asserts stringContainsInOrder("radiology", "surgery") — the in-order comment explicitly notes that a HashSet-enumeration implementation fails this test
- All four new test methods carry the 'the' prefix per testing-principles.md naming school: theSpecialtyDirectoryShouldListEachSpecialtyWithVeterinariansByFullName, theSpecialtyDirectoryShouldGroupVeterinariansHoldingNoSpecialty, theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage, theSpecialtyDirectoryShouldListSpecialtyHeldByNoVeterinarian
- factory methods specialty() and vet() keep object construction out of test bodies; four-phase structure with blank-line separation is maintained throughout all four new tests
- veterinariansHolding() and BY_FULL_NAME remain private/package-private single-responsibility helpers; stream pipelines used throughout; constructor injection holds

**doc-reviewer**

- Fix 1 — ADR link: docs/prd.md line 144 now carries **ADR:** [ADR: Specialty Directory as a Specialty-Authoritative Inverse Projection](adr/2026-08-06-specialty-directory-projection.md) beside the existing **Design:** link, using the · separator consistent with the Pet records section. No new problem introduced.
- Fix 2 — narrative trimmed: the rationale clause ('in deliberate contrast with the paged veterinarian directory of [REQ-VET-001]') and its non-standard inline [REQ-VET-001] cross-reference are gone. 'Every specialty renders on one page [REQ-VET-003].' is a complete behavioral statement; the Done-when bullet ('all of them render on a single page, with no pagination') provides the bounded contract. No behavior lost.
- Fix 3 — Open Questions bullet: the new bullet at prd.md line 195 opens with a genuine yes/no product question ('Should the specialty directory be reachable from the standard navigation?'). It names the observable state (unreachable from within the application), notes the undecided navigation change, and leaves REQ-SYS-001 as written. It can resolve into a requirement (widen nav), a non-goal (explicitly decline linking it), or an ADR (record either decision) — all three resolution paths are open, satisfying the section's own contract. Sentence lengths: the longest sentence in the bullet is approximately 28 words, within the 30-word standard. No new problem introduced.
- Fix 4 — ADR sentence split: docs/adr/2026-08-06-specialty-directory-projection.md line 9 is now two sentences of 13 and 24 words respectively. The load-bearing latency-of-gap justification ('so the gap is latent … the same class of latent defect already recorded elsewhere') is fully preserved across both sentences. Both are within the 30-word standard.
- docs/adr/README.md index entry for 2026-08-06 matches the ADR's actual title and links to the correct file; the row carries Accepted status consistent with the ADR frontmatter.
- system-design.md Contracts rows for VetController, VetRepository, and Specialty carry REQ-VET-003 in the Implements column, updated behavioral descriptions, and ADR back-links to adr/2026-08-06-specialty-directory-projection.md — correct from pass 1 and unchanged.
- PRD HTML anchor \<a id="req-vet-003">\</a> present at line 135; Done-when bullets correctly tagged [REQ-VET-003] with given/when/then form covering all three acceptance criteria; no Java constructs, pseudocode, or internal code references in the narrative.

**test-reviewer**

- All six tests pass; BUILD SUCCESSFUL; VetController line coverage 100% (35/35)
- stringContainsInOrder is genuinely order-sensitive: asserting 'Amy Adams' before 'Helen Leary' when the input supplies them in reverse order (Leary id=2, Adams id=6) means a non-deterministic sort (HashSet iteration) would fail the assertion. The rendered-output assertion tests the full controller-to-template pipeline, which is the right scope for a @WebMvcTest. The implementer's rationale is sound: Hamcrest hasProperty uses java.beans.Introspector which does not resolve record component accessors (name(), veterinarians()) because records expose them without a get prefix, so hasProperty on SpecialtyGroup would silently fail to find any property. Rendered-order via stringContainsInOrder is not weaker in any way that matters for this test's regression-detection goal.
- Legacy tests showVetListHtml and showResourcesVetList correctly kept under the pre-2026-07-31 naming convention. testing-principles.md § Test Naming reads: 'Applies to tests written or modified from 2026-07-31 onward. The existing suite predates this school and largely mirrors production method names; renaming it wholesale is not required, and a slice that touches a test renames only that test.' The two legacy tests were not touched by this slice, so renaming is not required. The implementer's reading is correct.
- All three PRD Done-when bullets for REQ-VET-003 are covered by dedicated tests: AC1 (specialties listed with vets by full name) by theSpecialtyDirectoryShouldListEachSpecialtyWithVeterinariansByFullName; AC2 (no-specialty grouping) by theSpecialtyDirectoryShouldGroupVeterinariansHoldingNoSpecialty; AC3 (single page, no pagination) by theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage. The ADR authoritative-axis edge case (specialty held by no vet) is covered by theSpecialtyDirectoryShouldListSpecialtyHeldByNoVeterinarian.
- All four new tests follow the the{Subject}Should{Outcome} school.
- theSpecialtyDirectoryShouldGroupVeterinariansHoldingNoSpecialty asserts the model attribute unspecializedVets using contains(hasProperty('lastName', is('Adams')), hasProperty('lastName', is('Baker'))). This works correctly: Vet is a JPA entity with getLastName(), so Introspector finds it. The assertion is order-sensitive and confirms the controller's BY_FULL_NAME sort applies to unspecialized vets.
- Factory methods specialty(int, String) and vet(int, String, String, Specialty...) wrap all object construction in the new tests per testing-principles.md § Test Data Construction. No raw constructors in test bodies.
- Four-phase structure is maintained: blank lines separate the Arrange stubs from the Act (mockMvc.perform) in all four new tests.
- @MockitoBean for VetRepository is pre-existing class infrastructure from before the slice. The new tests extend that class and their stubs are the appropriate tool within a @WebMvcTest context. The brief designates MockMvc as the sanctioned mock (web transport boundary); the repository stub is tolerated per testing-principles.md § Mocking Policy: 'the existing suite stubs collaborators with a mock framework, and that usage may stay.'
- The ordering rationale comments in theSpecialtyDirectoryShouldListEachSpecialtyWithVeterinariansByFullName (lines 127-130), theSpecialtyDirectoryShouldGroupVeterinariansHoldingNoSpecialty (lines 146-148), and theSpecialtyDirectoryShouldRenderAllSpecialtiesOnOnePage (lines 168-170) explain a non-obvious test design decision — deliberately out-of-order input to expose a hash-iteration regression — and are not mere restatement. They comply with testing-principles.md.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $7.28 | 15m 25s | 92% |
| `(parent)` | 1 | opus-5 | $4.92 | 40m 48s | 94% |
| `spring-boot-claude:system-design-expert` | 2 | opus-4-8 | $4.49 | 4m 53s | 79% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $3.08 | 4m 11s | 83% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $2.58 | 9m 1s | 70% |
| `spring-boot-claude:security-reviewer` | 2 | opus-4-8 | $1.98 | 2m 15s | 80% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $1.82 | 8m 30s | 85% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $1.64 | 11m 57s | 84% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.06 | 0s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `(parent)` | opus-5 | $4.92 | 40m 48s | 94% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $3.82 | 8m 10s | 91% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $3.46 | 4m 14s | 82% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $3.46 | 7m 15s | 93% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $1.88 | 6m 41s | 63% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.59 | 2m 4s | 87% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $1.49 | 2m 7s | 76% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $1.18 | 1m 14s | 83% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.03 | 39s | 62% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.95 | 9m 24s | 84% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.92 | 3m 46s | 86% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.90 | 4m 44s | 85% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.80 | 1m 0s | 75% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.70 | 2m 19s | 81% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.69 | 2m 33s | 84% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.06 | 0s | 0% |

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
- model requested `claude-opus-5`; models used: opus-4-8 · opus-5 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `14296e2bd575` (branch `agent-team`)
- task fingerprint `9c6fd220a549ce32` · `2.1.222 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
