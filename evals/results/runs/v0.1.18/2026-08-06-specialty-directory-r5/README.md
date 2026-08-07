# specialty-directory r5 — v0.1.18

Specialty directory page (feature) · started 2026-08-06T17:56:13+00:00 · exec `claude-dev` · status **timeout**

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
| suite (post-agent) | ✘ |
| suite (pristine baseline) | ✔ |
| checkpoints | 5/7 |
| review attention (pipeline grade) | — |

- ✔ `theSpecialtyDirectoryShouldListEverySeededSpecialty` — passed
- ✔ `theSpecialtyDirectoryShouldNameTheVetsHoldingEachSpecialty` — passed
- ✔ `theSpecialtyDirectoryShouldRender` — passed
- ✔ `theVetDirectoryShouldRenderTheSeededVets` — passed

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 2 (±0) | 2.5 (±1) | 2 (±0) | 3 (±0) |

Median (spread) over 2 sample(s) (3 requested) · rubric `rubric-v1.md` · `claude-opus-5` · $0.39. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 2 · test-quality 3 · maintainability 2 · doc-fit 3

> No  SpecialtyController  or  vets/specialtyList  template appears in the patch, yet  SpecialtyControllerTests  declares  @WebMvcTest(SpecialtyController.class)  and asserts  view().name("vets/specialtyList")  — the web layer the feature needs is absent, so the change cannot compile or be judged for layering.  SpecialtyRepository  mirrors the existing vet repository style but adds a repository for a non-aggregate-root child of Vet and copies an unrelated  @author Juergen Hoeller  tag. Tests use  @MockitoBean  (tolerated, not preferred), a shared mutable  @BeforeEach  fixture, mystery ids ( specialty(3, "dentistry") ), names missing the  the{Subject}Should  form, and narration comments ( // Specialties in name order. ). The PRD gains REQ-SPEC-001 but its  system-design.md#contracts  link covers no added contract.

**Sample 2** — design-fit 2 · test-quality 2 · maintainability 2 · doc-fit 3

> The patch ships no SpecialtyController and no vets/specialtyList template, yet SpecialtyControllerTests declares @WebMvcTest(SpecialtyController.class) and asserts view().name("vets/specialtyList") — the feature's HTTP surface is absent and the tests cannot compile. SpecialtyRepository itself fits the catalog (Repository suffix, @Query ordering by name), but carries a copy-pasted "@author Juergen Hoeller". Tests stub both repositories with @MockitoBean rather than real objects; names drop the required 'the' prefix; ids 3/1/2 and "dentistry" are mystery values with no SOME_/ANY_ tier; comments like "// Specialties in name order." narrate the assertions below them; xpath td[1]/td[2]/span[1] and attributeDoesNotExist("totalPages") assert markup and model internals. PRD gains REQ-SPEC-001 with done-when clauses, but links to system-design.md#contracts, which no hunk updates.

</details>

## Figures

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| ? | 131m | None | 73% | 3 file(s) +196/−0 |

## Change

<details>
<summary>Diff (rendered from <code>change.patch</code>)</summary>

```diff
diff --git a/docs/prd.md b/docs/prd.md
index 0cb7f37..ec86288 100644
--- a/docs/prd.md
+++ b/docs/prd.md
@@ -130,6 +130,23 @@ The clinic publishes the veterinarians it employs with the specialties each hold
 
 **Design:** [system-design.md#contracts](system-design.md#contracts)
 
+### Specialty directory
+
+<a id="req-spec-001"></a>
+
+The clinic also publishes the inverse of the veterinarian directory: a specialty directory that lists every specialty the clinic knows by its stored name, and under each the veterinarians who hold it, each shown by full name — first name then last name, so "Helen Leary" reads as it would be spoken `[REQ-SPEC-001]`. The page is driven by the clinic's specialties, not its veterinarians: a specialty no veterinarian holds is still listed, with no veterinarians under it, and a veterinarian holding no specialty does not appear at all — the page lists specialties, not the full veterinarian roster. Every specialty is shown on a single page, without pagination.
+
+**Done when:**
+- `[REQ-SPEC-001]` given the clinic's specialties, when the specialty directory is opened, then every specialty is listed by its stored name, each with the veterinarians holding it shown by full name in first-name-then-last-name order.
+- `[REQ-SPEC-001]` given a specialty no veterinarian holds, when the specialty directory is opened, then that specialty is still listed, with no veterinarians under it.
+- `[REQ-SPEC-001]` given a veterinarian holding no specialty, when the specialty directory is opened, then that veterinarian does not appear anywhere on the page.
+- `[REQ-SPEC-001]` given the clinic's specialties, when the specialty directory is opened, then all specialties render on one page with no pagination.
+
+**Edge cases:**
+1. Specialties, and the veterinarians listed under each, are presented in a stable order rather than an arbitrary one.
+
+**Design:** [system-design.md#contracts](system-design.md#contracts)
+
 ### Language
 
 <a id="req-lang-001"></a><a id="req-lang-002"></a>
diff --git a/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java
new file mode 100644
index 0000000..1440924
--- /dev/null
+++ b/src/main/java/org/springframework/samples/petclinic/vet/SpecialtyRepository.java
@@ -0,0 +1,40 @@
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
+import org.springframework.data.jpa.repository.Query;
+import org.springframework.data.repository.Repository;
+
+/**
+ * Repository class for <code>Specialty</code> domain objects. Read-only: the specialty
+ * directory reads specialties directly from the specialties table so that a specialty
+ * held by no veterinarian still surfaces, which the vet-side join cannot express.
+ *
+ * @author Juergen Hoeller
+ */
+public interface SpecialtyRepository extends Repository<Specialty, Integer> {
+
+	/**
+	 * Retrieve all {@link Specialty} objects from the data store, ordered by name so the
+	 * directory has a stable presentation order.
+	 * @return a name-ordered list of {@link Specialty} objects
+	 */
+	@Query("SELECT specialty FROM Specialty specialty ORDER BY specialty.name")
+	List<Specialty> findSpecialties();
+
+}
diff --git a/src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java b/src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java
new file mode 100644
index 0000000..4a6334d
--- /dev/null
+++ b/src/test/java/org/springframework/samples/petclinic/vet/SpecialtyControllerTests.java
@@ -0,0 +1,139 @@
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
+import org.assertj.core.util.Lists;
+import org.junit.jupiter.api.BeforeEach;
+import org.junit.jupiter.api.Test;
+import org.junit.jupiter.api.condition.DisabledInNativeImage;
+import org.springframework.beans.factory.annotation.Autowired;
+import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
+import org.springframework.test.context.aot.DisabledInAotMode;
+import org.springframework.test.context.bean.override.mockito.MockitoBean;
+import org.springframework.test.web.servlet.MockMvc;
+
+import static org.hamcrest.Matchers.containsString;
+import static org.hamcrest.Matchers.not;
+import static org.mockito.BDDMockito.given;
+import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.model;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.view;
+import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.xpath;
+
+/**
+ * Test class for the {@link SpecialtyController}.
+ */
+@WebMvcTest(SpecialtyController.class)
+@DisabledInNativeImage
+@DisabledInAotMode
+class SpecialtyControllerTests {
+
+	private static final String SPECIALTY_ROWS = "//table[@id='specialties']/tbody/tr";
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
+	private Specialty specialty(int id, String name) {
+		Specialty specialty = new Specialty();
+		specialty.setId(id);
+		specialty.setName(name);
+		return specialty;
+	}
+
+	private Vet vet(int id, String firstName, String lastName, Specialty... held) {
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
+		Specialty dentistry = specialty(3, "dentistry");
+		Specialty radiology = specialty(1, "radiology");
+		Specialty surgery = specialty(2, "surgery");
+
+		// findSpecialties() returns rows already ordered by name at the data layer.
+		given(this.specialties.findSpecialties()).willReturn(List.of(dentistry, radiology, surgery));
+
+		// James and Helen both hold radiology; James also holds surgery. Linda holds none.
+		given(this.vets.findAll()).willReturn(Lists.newArrayList(vet(1, "James", "Carter", radiology, surgery),
+				vet(2, "Helen", "Leary", radiology), vet(3, "Linda", "Douglas")));
+	}
+
+	@Test
+	void specialtyDirectoryShouldListEverySpecialtyWithItsVeterinarians() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(view().name("vets/specialtyList"))
+			.andExpect(model().attributeExists("specialties"))
+			.andExpect(xpath(SPECIALTY_ROWS + "[td[1]='radiology']/td[2]/span[1]").string("Helen Leary"))
+			.andExpect(xpath(SPECIALTY_ROWS + "[td[1]='radiology']/td[2]/span[2]").string("James Carter"))
+			.andExpect(xpath(SPECIALTY_ROWS + "[td[1]='surgery']/td[2]/span[1]").string("James Carter"));
+	}
+
+	@Test
+	void specialtyDirectoryShouldListASpecialtyHeldByNoVeterinarianWithNoVets() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(xpath(SPECIALTY_ROWS + "[td[1]='dentistry']").exists())
+			.andExpect(xpath(SPECIALTY_ROWS + "[td[1]='dentistry']/td[2]/span").string("none"));
+	}
+
+	@Test
+	void specialtyDirectoryShouldOmitAVeterinarianHoldingNoSpecialty() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(content().string(not(containsString("Linda"))));
+	}
+
+	@Test
+	void specialtyDirectoryShouldRenderAllSpecialtiesOnOnePage() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			.andExpect(model().attributeDoesNotExist("totalPages"))
+			.andExpect(xpath(SPECIALTY_ROWS).nodeCount(3));
+	}
+
+	@Test
+	void specialtyDirectoryShouldPresentSpecialtiesAndVeterinariansInStableOrder() throws Exception {
+		mockMvc.perform(get("/specialties.html"))
+			.andExpect(status().isOk())
+			// Specialties in name order.
+			.andExpect(xpath(SPECIALTY_ROWS + "[1]/td[1]").string("dentistry"))
+			.andExpect(xpath(SPECIALTY_ROWS + "[2]/td[1]").string("radiology"))
+			.andExpect(xpath(SPECIALTY_ROWS + "[3]/td[1]").string("surgery"))
+			// Vets under radiology in first-name-then-last-name order.
+			.andExpect(xpath(SPECIALTY_ROWS + "[2]/td[2]/span[1]").string("Helen Leary"))
+			.andExpect(xpath(SPECIALTY_ROWS + "[2]/td[2]/span[2]").string("James Carter"));
+	}
+
+}
```

</details>

## Pipeline

### REQ-SPEC-001 — Staff can view which veterinarians hold each specialty

0 review rounds · 0 build-passes · no grade yet

- ◇ **prd-entry** Staff can view which veterinarians hold each specialty · (prd-expert) · ***◷ 0s***
- ◈ **design-block** **minor** · (design) · ***◷ 0s***
- ◆ **implement** (implementer)

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:system-design-expert` | 1 | opus-4-8 | $4.24 | 4m 19s | 72% |
| `spring-boot-claude:feature-implementer` | 1 | opus-4-8 | $3.57 | 18m 26s | 72% |
| `spring-boot-claude:product-requirements-expert` | 1 | opus-4-8 | $3.48 | 46m 39s | 48% |
| `(parent)` | 1 | opus-5 | $1.48 | 81m 57s | 96% |
| `spring-boot-claude:pipeline-coordinator` | 2 | sonnet-4-6 | $0.24 | 28m 39s | 0% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:system-design-expert` | opus-4-8 | $4.24 | 4m 19s | 72% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $3.57 | 18m 26s | 72% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $3.48 | 46m 39s | 48% |
| `(parent)` | opus-5 | $1.48 | 81m 57s | 96% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.16 | 6s | 0% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.08 | 28m 32s | 0% |

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
- task fingerprint `9c6fd220a549ce32` · `2.1.222 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
