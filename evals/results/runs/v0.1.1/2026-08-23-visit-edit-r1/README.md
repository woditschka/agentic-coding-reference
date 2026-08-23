# visit-edit r1 — v0.1.1

Edit a booked visit (feature) · started 2026-08-23T08:50:00+00:00 · exec `claude-dev` · status **complete**

## Prompt

> Feature request: visits can currently only be created, never corrected. Two
> product decisions come with it, made here as the product owner:
> 
> - Non-goal NG-5 is narrowed: cancelling a booked visit stays out of scope,
>   but correcting its date and description is now in. Record the narrowing
>   the way the project records non-goal changes.
> - The edit form is reachable by its URL alone: the owner detail page gains
>   no edit link in this request. A visible entry point may come as a
>   follow-up request.
> 
> Add editing for a booked visit:
> 
> - GET /owners/{ownerId}/pets/{petId}/visits/{visitId}/edit shows the visit
>   form prefilled with that visit's current date and description. Reuse the
>   existing visit form template (pets/createOrUpdateVisitForm) and its  visit
>   model attribute.
> - POST to the same URL validates like visit creation (description required,
>   date in the future). On success it updates that visit in place — the pet
>   must not gain an additional visit record — and redirects to the owner
>   detail page. On validation failure it redisplays the form.
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

- ✔ `theEditFormShouldPrefillTheExistingVisit` — passed
- ✔ `theEditSubmissionShouldUpdateTheVisitInPlace` — passed
- ✔ `theEditSubmissionWithABlankDescriptionShouldRedisplayTheForm` — passed
- ✔ `theNewVisitFormShouldRenderForTheExistingPet` — passed

## Checkpoints

The kind's graded ladder, derived from the recorded facts — context only, outside the quality bar (bench README § Checkpoints).

- ✔ `agent complete`
- ✔ `change produced`
- ✔ `suite green`
- ✔ `theEditFormShouldPrefillTheExistingVisit`
- ✔ `theEditSubmissionShouldUpdateTheVisitInPlace`
- ✔ `theEditSubmissionWithABlankDescriptionShouldRedisplayTheForm`
- ✔ `theNewVisitFormShouldRenderForTheExistingPet`

## Judge (advisory)

| design-fit | test-quality | maintainability | doc-fit |
|---|---|---|---|
| 3 (±0) | 3 (±1) | 3 (±0) | 5 (±1) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.52. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 3 · test-quality 4 · maintainability 3 · doc-fit 5

> Reusing loadPetWithVisit via an optional visitId path variable and adding Pet.getVisit fits the existing structure, but processUpdateVisitForm copy-pastes the non-future-date rule ( result.rejectValue("date", "typeMismatch.visitDate") ) into a second controller method — the catalog's Web controller row calls a new controller rule a fresh violation, and the duplicate now needs two edits to change. Comments narrating Spring's call order, plus a stray import blank line, are noise. Tests are BDD-named, use a createExistingVisit factory and SOME_/EXISTING_ constants, and cover prefill, in-place update, redirect, and both refusals; they lose points for the bare "corrected description" literal, direct  new Owner() / new Pet()  in the touched init, and asserting exception message text. Docs are complete: ADR, index row, narrowed NG-5, REQ-VIS-003 with done-when, and the deferred-link open question.

**Sample 2** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 5

> Reuses the existing template,  visit  model attribute, and the  @ModelAttribute  loader via an optional  visitId , and  Pet.getVisit  mirrors  Owner.getPet  — but  processUpdateVisitForm  copy-pastes the non-future-date rejection ( result.rejectValue("date", "typeMismatch.visitDate") ), a fresh business rule in a controller that the catalog's Web controller row forbids and that now must be changed in two places. Tests are strongly BDD-named and cover prefill, in-place update, redirect, and both refusals, but keep mystery literals ( "corrected description" , inline  LocalDate.now().plusDays(3) ), label the meaningful target id  SOME_VISIT_ID , share a mutable  owner  field, and leave  new Owner() / new Pet()  unfactoried in the touched  init . Documentation is complete: ADR, ADR index, narrowed NG-5, REQ-VIS-003 with done-when, and the deferred-link open question.

**Sample 3** — design-fit 3 · test-quality 3 · maintainability 3 · doc-fit 4

> Pet.getVisit mirrors the existing Owner.getPet seam and the optional-@PathVariable @ModelAttribute reuses the booking loader well, but processUpdateVisitForm copy-pastes the non-future-date rule ( result.rejectValue("date", "typeMismatch.visitDate") ) into a second controller method instead of extracting it to the catalog's Form validator — the brief explicitly calls a new controller rule a fresh violation, and it is now duplicated. Tests are BDD-named and cover all four done-when clauses, yet carry mystery literals ( "corrected description"  thrice, inline  plusDays(3) ), mis-tier SOME_VISIT_ID (it is meaningful), pick apart fields rather than comparing objects, and assert the exception's message text. The stray blank line after the jakarta import and the hardcoded flash string are review noise. Documentation is thorough: ADR, index row, narrowed NG-5, REQ-VIS-003, open question.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $9.03 | 22m | 16 | 90% | 6 file(s) +204/−8 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.57 | 1m 44s | 89% |

## Change

<details>
<summary>Diff (rendered from <code>change.patch</code>)</summary>

```diff
diff --git a/docs/adr/2026-08-23-non-goal-visit-correction-narrowing.md b/docs/adr/2026-08-23-non-goal-visit-correction-narrowing.md
new file mode 100644
index 0000000..7db4ec6
--- /dev/null
+++ b/docs/adr/2026-08-23-non-goal-visit-correction-narrowing.md
@@ -0,0 +1,34 @@
+# Correcting a Booked Visit's Date and Description Is In Scope; Cancellation Stays Out
+
+**Status:** Accepted
+
+## Context
+
+NG-5 was confirmed deliberate on 2026-08-08 as "Changing or cancelling a visit once booked" — the whole row out of scope. The confirming ADR anticipated this move: it records that narrowing either row later is a recorded owner decision with its own non-goal ADR.
+
+The owner has now narrowed NG-5 (2026-08-23). Correcting a booked visit — changing its date and its description — is a forward correction of the same kind the sample already demonstrates for owner and pet details. It reuses the visit form and the booking-time validation and stores no lifecycle state; it just updates the record in place. Cancellation is the part that would add delete-side lifecycle the sample carries nowhere else.
+
+## Options Considered
+
+1. **Leave NG-5 whole.** Rejected: it conflates two different operations. Correction is a forward update the sample teaches elsewhere; cancellation is a deletion the sample deliberately omits (NG-4). One row hid both.
+2. **Narrow NG-5 to cancellation only, admitting correction** (chosen).
+3. **Open NG-5 fully**, admitting cancellation too. Rejected: cancellation adds the delete-side lifecycle NG-4 keeps out; nothing about it teaches a pattern the update flows do not.
+
+## Decision
+
+NG-5 narrows to cancellation only. Correcting a booked visit's date and description is in scope, captured as REQ-VIS-003. Cancelling a booked visit stays out of scope, for the reason NG-4 keeps deletion out: it adds lifecycle the sample demonstrates nowhere.
+
+The correction capability corrects the record in place — the pet gains no additional visit — and is validated exactly as booking is.
+
+## Consequences
+
+- The Non-Goals table's NG-5 row now reads "Cancelling a booked visit"; correction moves to REQ-VIS-003 in the Visits requirements.
+- The sample continues to demonstrate forward-only correction and no deletion. Cancellation remains unplanned.
+- The correction form is reachable by URL in this slice; a visible entry point on the owner detail page is a deferred follow-up, recorded as an open question, not part of the decision here.
+
+## Implementation
+
+**Non-goal:** NG-5
+
+- [PRD Non-Goals](../prd.md#non-goals) — the narrowed NG-5 row.
+- [REQ-VIS-003](../prd.md#req-vis-003) — the correction capability admitted by this narrowing.
diff --git a/docs/adr/README.md b/docs/adr/README.md
index 04c6442..d2c58bc 100644
--- a/docs/adr/README.md
+++ b/docs/adr/README.md
@@ -70,3 +70,4 @@ A non-goal ADR records a *product* decision not to build something — distinct
 | 2026-07-31 | [Database-Enforced Pet Name Uniqueness Within an Owner](2026-07-31-database-enforced-pet-name-uniqueness.md) | Accepted |
 | 2026-07-31 | [Dual Gradle and Maven Build Definitions](2026-07-31-dual-gradle-and-maven-builds.md) | Accepted |
 | 2026-08-08 | [Deleting Records and Amending Booked Visits Are Deliberately Out of Scope](2026-08-08-non-goal-deletion-and-visit-amendment.md) | Accepted |
+| 2026-08-23 | [Correcting a Booked Visit's Date and Description Is In Scope; Cancellation Stays Out](2026-08-23-non-goal-visit-correction-narrowing.md) | Accepted |
diff --git a/docs/prd.md b/docs/prd.md
index 06398de..44f34ad 100644
--- a/docs/prd.md
+++ b/docs/prd.md
@@ -32,7 +32,7 @@ What the framing does not settle is whether each individual behavior was intende
 
 <!-- Declined scope with the reason it was declined; never silently dropped. A non-goal ADR records the path to each decision. -->
 
-> **One reason covers this table, and it is narrower than it looks.** The demonstration framing confirmed 2026-07-31 (G-1) makes scope a function of what a reader must see. A capability that would add breadth without teaching anything new about the stack is out. That reason genuinely explains each row, but it was supplied *after* the rows were derived from absence. It is therefore a framing applied to observed gaps, not a decision recorded at the time. Two rows have since been decided: NG-4 and NG-5 are confirmed deliberate (2026-08-08) — [the non-goal ADR](adr/2026-08-08-non-goal-deletion-and-visit-amendment.md) records the decision. For every other row, whether it was deliberately declined, deferred, or never considered is still unknown, and remains part of the open consultation.
+> **One reason covers this table, and it is narrower than it looks.** The demonstration framing confirmed 2026-07-31 (G-1) makes scope a function of what a reader must see. A capability that would add breadth without teaching anything new about the stack is out. That reason genuinely explains each row, but it was supplied *after* the rows were derived from absence. It is therefore a framing applied to observed gaps, not a decision recorded at the time. Two rows have since been decided: NG-4 and NG-5 are confirmed deliberate (2026-08-08) — [the non-goal ADR](adr/2026-08-08-non-goal-deletion-and-visit-amendment.md) records the decision. NG-5 was then narrowed (2026-08-23): correcting a booked visit's date and description is in scope as [REQ-VIS-003](#req-vis-003), and only cancellation stays out — [the narrowing ADR](adr/2026-08-23-non-goal-visit-correction-narrowing.md) records it. For every other row, whether it was deliberately declined, deferred, or never considered is still unknown, and remains part of the open consultation.
 
 | ID | Non-Goal | Rationale |
 |----|----------|-----------|
@@ -40,7 +40,7 @@ What the framing does not settle is whether each individual behavior was intende
 | NG-2 | Managing veterinarians or their specialties through the application | The veterinarian directory demonstrates reading and presenting a cached collection; adding write flows would repeat what the owner and pet capabilities already teach |
 | NG-3 | Managing the list of pet types through the application | Same reason as NG-2 — pet types demonstrate a constrained reference list, and a maintenance UI adds no new pattern |
 | NG-4 | Deleting an owner, a pet, or a visit | Cascading deletion across an aggregate raises questions a reference sample would have to answer at length without illustrating anything the create and update flows do not. Confirmed deliberate 2026-08-08 — [ADR](adr/2026-08-08-non-goal-deletion-and-visit-amendment.md) |
-| NG-5 | Changing or cancelling a visit once booked | Booking already demonstrates validation against a date boundary; amendment would add lifecycle state the sample deliberately has none of. Confirmed deliberate 2026-08-08 — [ADR](adr/2026-08-08-non-goal-deletion-and-visit-amendment.md) |
+| NG-5 | Cancelling a booked visit | Cancellation would add the delete-side lifecycle NG-4 keeps out, teaching nothing the update flows do not. Confirmed deliberate 2026-08-08; narrowed 2026-08-23 so that correcting a booked visit's date and description is in scope ([REQ-VIS-003](#req-vis-003)) while cancellation stays out — [ADR](adr/2026-08-23-non-goal-visit-correction-narrowing.md) |
 | NG-6 | Assigning a veterinarian to a visit, or any scheduling and availability | Scheduling is a domain of its own. Including it would make the sample about calendars rather than about the stack |
 | NG-7 | Billing, invoicing, and payment | A second bounded context, with money and its own correctness demands, in a sample sized to be read in one sitting |
 | NG-8 | Clinical records beyond a visit's one-line description | The description field demonstrates the association; richer clinical data would add domain depth without adding a pattern |
@@ -100,19 +100,27 @@ Each pet is recorded against exactly one owner, with a name, a birth date, and a
 
 ### Visits
 
-<a id="req-vis-001"></a><a id="req-vis-002"></a>
+<a id="req-vis-001"></a><a id="req-vis-002"></a><a id="req-vis-003"></a>
 
-A visit is booked against a particular pet and carries the date it is for and a short description of what it is for `[REQ-VIS-001]`. When booking, the pet's earlier visits are shown alongside, so whoever is booking can see what has already been done `[REQ-VIS-002]`.
+A visit is booked against a particular pet and carries the date it is for and a short description of what it is for `[REQ-VIS-001]`. When booking, the pet's earlier visits are shown alongside, so whoever is booking can see what has already been done `[REQ-VIS-002]`. A booked visit's date and description can be corrected later: the correction form opens showing the visit's current date and description, the same rules that govern booking govern the correction, and a successful correction updates that visit in place — the pet gains no additional visit — before the owner's record is shown again `[REQ-VIS-003]`.
 
 **Done when:**
 - `[REQ-VIS-001]` given a pet, when a description and a date later than today are supplied, then the visit is recorded and the booking is confirmed.
 - `[REQ-VIS-001]` given a blank description, when the visit is submitted, then the booking is refused and the description is named.
 - `[REQ-VIS-001]` given a date of today or earlier, when the visit is submitted, then the booking is refused and the date is named.
 - `[REQ-VIS-002]` given a pet with earlier visits, when a new visit is being booked, then those earlier visits are shown with their dates and descriptions.
+- `[REQ-VIS-003]` given a booked visit, when its correction form is opened, then the form shows that visit's current date and description.
+- `[REQ-VIS-003]` given a booked visit, when a description and a date later than today are submitted as a correction, then that visit is updated in place, the pet gains no additional visit, and the owner's record is shown.
+- `[REQ-VIS-003]` given a correction with a blank description, when it is submitted, then the correction is refused and the description is named.
+- `[REQ-VIS-003]` given a correction with a date of today or earlier, when it is submitted, then the correction is refused and the date is named.
 
 **Edge cases:**
 1. Booking a visit for a pet that does not belong to the named owner is refused.
 2. The date offered by default is the earliest date that would be accepted.
+3. Cancelling a booked visit stays out of scope (NG-5); correction changes a visit but never removes one.
+4. **Scope boundary.** The correction form is reachable by its URL only; the owner's record shows no link to it. A visible entry point is a deferred follow-up (see Open Questions), not part of `[REQ-VIS-003]`.
+
+**Design Rationale:** See [ADR: Correcting a Booked Visit's Date and Description Is In Scope; Cancellation Stays Out](adr/2026-08-23-non-goal-visit-correction-narrowing.md).
 
 ### Veterinarian directory
 
@@ -176,6 +184,7 @@ The system opens on a landing page, and every page carries navigation to the own
 - ~~**Is `REQ-VET-002` a real requirement?**~~ **Answered 2026-07-31: no.** Withdrawn to the Superseded list as an implementation artifact.
 - ~~**Should the error page show technical failure detail to readers?**~~ **Answered 2026-07-31: no.** Stated in `REQ-SYS-002`; the current behavior is recorded as a defect.
 - ~~**Are two message keys dead vocabulary?**~~ **Answered 2026-07-31: yes.** The keys for a duplicate form submission and for a non-numeric value are produced by no code and are translated into all eleven languages. They are dead vocabulary pending removal.
+- **Should the owner's record link to the visit-correction form?** REQ-VIS-003 admits correcting a booked visit, but the form is reachable by its address only, with no visible entry point on the owner's record. Whether to surface a link there is a deferred follow-up.
 - **Is a visit really unrelated to a veterinarian?** Nothing connects the two, which makes the veterinarian directory a standalone page rather than part of the clinical workflow.
 - **Are the seeded pet types and specialties the real lists,** or placeholders?
 - **Does the project hold goals beyond being a reference sample?** G-2 is unfilled.
diff --git a/src/main/java/org/springframework/samples/petclinic/owner/Pet.java b/src/main/java/org/springframework/samples/petclinic/owner/Pet.java
index 4f8409e..1145ee1 100644
--- a/src/main/java/org/springframework/samples/petclinic/owner/Pet.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/Pet.java
@@ -18,6 +18,7 @@ package org.springframework.samples.petclinic.owner;
 import java.time.LocalDate;
 import java.util.Collection;
 import java.util.LinkedHashSet;
+import java.util.Objects;
 import java.util.Set;
 
 import org.springframework.format.annotation.DateTimeFormat;
@@ -82,4 +83,18 @@ public class Pet extends NamedEntity {
 		getVisits().add(visit);
 	}
 
+	/**
+	 * Return the Visit with the given id, or null if none found for this Pet.
+	 * @param id to test
+	 * @return the Visit with the given id, or null if no such Visit exists for this Pet
+	 */
+	public Visit getVisit(Integer id) {
+		for (Visit visit : getVisits()) {
+			if (!visit.isNew() && Objects.equals(visit.getId(), id)) {
+				return visit;
+			}
+		}
+		return null;
+	}
+
 }
diff --git a/src/main/java/org/springframework/samples/petclinic/owner/VisitController.java b/src/main/java/org/springframework/samples/petclinic/owner/VisitController.java
index b8b2700..c0de6c5 100644
--- a/src/main/java/org/springframework/samples/petclinic/owner/VisitController.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/VisitController.java
@@ -29,6 +29,7 @@ import org.springframework.web.bind.annotation.PathVariable;
 import org.springframework.web.bind.annotation.PostMapping;
 
 import jakarta.validation.Valid;
+
 import org.springframework.web.servlet.mvc.support.RedirectAttributes;
 
 /**
@@ -62,7 +63,7 @@ class VisitController {
 	 */
 	@ModelAttribute("visit")
 	public Visit loadPetWithVisit(@PathVariable("ownerId") int ownerId, @PathVariable("petId") int petId,
-			Map<String, Object> model) {
+			@PathVariable(name = "visitId", required = false) Integer visitId, Map<String, Object> model) {
 		Optional<Owner> optionalOwner = owners.findById(ownerId);
 		Owner owner = optionalOwner.orElseThrow(() -> new IllegalArgumentException(
 				"Owner not found with id: " + ownerId + ". Please ensure the ID is correct "));
@@ -75,6 +76,17 @@ class VisitController {
 		model.put("pet", pet);
 		model.put("owner", owner);
 
+		// Correcting an existing visit: return the persisted instance so binding and the
+		// cascade update it in place. Booking a new visit: attach a fresh visit.
+		if (visitId != null) {
+			Visit visit = pet.getVisit(visitId);
+			if (visit == null) {
+				throw new IllegalArgumentException(
+						"Visit with id " + visitId + " not found for pet with id " + petId + ".");
+			}
+			return visit;
+		}
+
 		Visit visit = new Visit();
 		pet.addVisit(visit);
 		return visit;
@@ -111,4 +123,30 @@ class VisitController {
 		return "redirect:/owners/{ownerId}";
 	}
 
+	// Spring MVC calls method loadPetWithVisit(...) before initUpdateVisitForm is
+	// called, prefilling the form with the existing visit fetched by visitId.
+	@GetMapping("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit")
+	public String initUpdateVisitForm() {
+		return "pets/createOrUpdateVisitForm";
+	}
+
+	// Spring MVC calls method loadPetWithVisit(...) before processUpdateVisitForm is
+	// called. The visit argument is the persisted instance loaded by visitId, so
+	// binding mutates it in place and owners.save cascades an UPDATE, not an INSERT.
+	@PostMapping("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit")
+	public String processUpdateVisitForm(@ModelAttribute Owner owner, @Valid Visit visit, BindingResult result,
+			RedirectAttributes redirectAttributes) {
+		if (visit.getDate() != null && !visit.getDate().isAfter(LocalDate.now())) {
+			result.rejectValue("date", "typeMismatch.visitDate");
+		}
+
+		if (result.hasErrors()) {
+			return "pets/createOrUpdateVisitForm";
+		}
+
+		this.owners.save(owner);
+		redirectAttributes.addFlashAttribute("message", "Your visit has been updated");
+		return "redirect:/owners/{ownerId}";
+	}
+
 }
diff --git a/src/test/java/org/springframework/samples/petclinic/owner/VisitControllerTests.java b/src/test/java/org/springframework/samples/petclinic/owner/VisitControllerTests.java
index b608caa..38385c7 100644
--- a/src/test/java/org/springframework/samples/petclinic/owner/VisitControllerTests.java
+++ b/src/test/java/org/springframework/samples/petclinic/owner/VisitControllerTests.java
@@ -16,6 +16,10 @@
 
 package org.springframework.samples.petclinic.owner;
 
+import static org.assertj.core.api.Assertions.assertThat;
+import static org.assertj.core.api.Assertions.assertThatThrownBy;
+import static org.hamcrest.Matchers.hasProperty;
+import static org.hamcrest.Matchers.is;
 import static org.mockito.BDDMockito.given;
 import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
 import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
@@ -50,19 +54,38 @@ class VisitControllerTests {
 
 	private static final int TEST_PET_ID = 1;
 
+	private static final int SOME_VISIT_ID = 1;
+
+	private static final LocalDate EXISTING_VISIT_DATE = LocalDate.now().plusDays(5);
+
+	private static final String EXISTING_VISIT_DESCRIPTION = "rabies shot";
+
 	@Autowired
 	private MockMvc mockMvc;
 
 	@MockitoBean
 	private OwnerRepository owners;
 
+	private Owner owner;
+
 	@BeforeEach
 	void init() {
-		Owner owner = new Owner();
+		this.owner = new Owner();
 		Pet pet = new Pet();
-		owner.addPet(pet);
+		this.owner.addPet(pet);
 		pet.setId(TEST_PET_ID);
-		given(this.owners.findById(TEST_OWNER_ID)).willReturn(Optional.of(owner));
+
+		pet.addVisit(createExistingVisit(SOME_VISIT_ID, EXISTING_VISIT_DATE, EXISTING_VISIT_DESCRIPTION));
+
+		given(this.owners.findById(TEST_OWNER_ID)).willReturn(Optional.of(this.owner));
+	}
+
+	private static Visit createExistingVisit(int id, LocalDate date, String description) {
+		Visit visit = new Visit();
+		visit.setId(id);
+		visit.setDate(date);
+		visit.setDescription(description);
+		return visit;
 	}
 
 	@Test
@@ -106,4 +129,80 @@ class VisitControllerTests {
 			.andExpect(view().name("pets/createOrUpdateVisitForm"));
 	}
 
+	@Test
+	void theVisitCorrectionFormShouldShowCurrentDateAndDescription() throws Exception {
+		mockMvc
+			.perform(get("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit", TEST_OWNER_ID, TEST_PET_ID,
+					SOME_VISIT_ID))
+			.andExpect(status().isOk())
+			.andExpect(view().name("pets/createOrUpdateVisitForm"))
+			.andExpect(model().attribute("visit", hasProperty("date", is(EXISTING_VISIT_DATE))))
+			.andExpect(model().attribute("visit", hasProperty("description", is(EXISTING_VISIT_DESCRIPTION))));
+	}
+
+	@Test
+	void theVisitCorrectionShouldBeRejectedWhenTheVisitDoesNotExistForThePet() {
+		int nonExistentVisitId = 999;
+
+		assertThatThrownBy(() -> mockMvc.perform(get("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit",
+				TEST_OWNER_ID, TEST_PET_ID, nonExistentVisitId)))
+			.hasRootCauseInstanceOf(IllegalArgumentException.class)
+			.rootCause()
+			.hasMessageContaining("Visit with id " + nonExistentVisitId + " not found for pet with id " + TEST_PET_ID);
+	}
+
+	@Test
+	void theVisitCorrectionShouldUpdateInPlaceWithoutAddingAVisit() throws Exception {
+		LocalDate correctedDate = LocalDate.now().plusDays(3);
+
+		mockMvc
+			.perform(post("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit", TEST_OWNER_ID, TEST_PET_ID,
+					SOME_VISIT_ID)
+				.param("date", correctedDate.toString())
+				.param("description", "corrected description"))
+			.andExpect(status().is3xxRedirection());
+
+		Pet pet = this.owner.getPet(TEST_PET_ID);
+		assertThat(pet.getVisits()).hasSize(1);
+		Visit corrected = pet.getVisit(SOME_VISIT_ID);
+		assertThat(corrected.getDate()).isEqualTo(correctedDate);
+		assertThat(corrected.getDescription()).isEqualTo("corrected description");
+	}
+
+	@Test
+	void theVisitCorrectionShouldRedirectToOwnerDetail() throws Exception {
+		mockMvc
+			.perform(post("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit", TEST_OWNER_ID, TEST_PET_ID,
+					SOME_VISIT_ID)
+				.param("date", LocalDate.now().plusDays(3).toString())
+				.param("description", "corrected description"))
+			.andExpect(status().is3xxRedirection())
+			.andExpect(view().name("redirect:/owners/{ownerId}"));
+	}
+
+	@Test
+	void theVisitCorrectionShouldBeRefusedWhenDescriptionIsBlank() throws Exception {
+		mockMvc
+			.perform(post("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit", TEST_OWNER_ID, TEST_PET_ID,
+					SOME_VISIT_ID)
+				.param("date", LocalDate.now().plusDays(3).toString())
+				.param("description", ""))
+			.andExpect(model().attributeHasFieldErrors("visit", "description"))
+			.andExpect(status().isOk())
+			.andExpect(view().name("pets/createOrUpdateVisitForm"));
+	}
+
+	@Test
+	void theVisitCorrectionShouldBeRefusedWhenDateIsNotFuture() throws Exception {
+		mockMvc
+			.perform(post("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit", TEST_OWNER_ID, TEST_PET_ID,
+					SOME_VISIT_ID)
+				.param("date", LocalDate.now().toString())
+				.param("description", "corrected description"))
+			.andExpect(model().attributeHasFieldErrors("visit", "date"))
+			.andExpect(model().attributeHasFieldErrorCode("visit", "date", "typeMismatch.visitDate"))
+			.andExpect(status().isOk())
+			.andExpect(view().name("pets/createOrUpdateVisitForm"));
+	}
+
 }
```

</details>

## Pipeline

### REQ-VIS-003 — Correct a booked visit's date and description

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (2) | **✔** |
| **test** | ✎ (2) | **✔** |
| **security** | **✔** | · |
| **doc** | ✎ (3) | **✔** |

- ◇ **prd-entry** Correct a booked visit's date and description · (prd-expert) · ***◷ 1m***
- ◈ **design-block** **covered** · (design) · ***◷ 5m***
- ◆ **implement** (implementer) · ***◷ 10m***
  - ▲ **build ✓ clean** · build · test · format · check
- ✔ **review security** · **approved** · ***◷ 1m***
- ✎ **review doc** · **changes_requested** · (3 findings) · ***◷ 5m***
  - [autofix] `prd.md#visits` The prd-authoring skill requires a Design Rationale link whenever an ADR records the decision behind the requirement. REQ-VIS-003 was admitted by the 2026-08-23 narrowing ADR, but the Visits section carries no **Design Rationale:** reference to it. Every other section that has an ADR (Pet records) includes one.
    - fix: Add the following line after the Visits edge cases block and before the Veterinarian directory section: **Design Rationale:** See [ADR: Correcting a Booked Visit's Date and Description Is In Scope; Cancellation Stays Out](adr/2026-08-23-non-goal-visit-correction-narrowing.md).
  - [autofix] `prd.md:121` The phrase "In this round" is pipeline-internal language. A reader of the PRD who does not know the pipeline's concept of implementation rounds has no referent. The PRD describes what the system does; the mechanism by which a scope boundary was reached in one iteration is not part of that description.
    - fix: Replace "In this round the correction form is reachable by its address only; the owner's record shows no link to it." with "The correction form is reachable by its URL only; the owner's record shows no link to it."
  - [autofix] `prd.md:185` The phrase "this round leaves the form reachable by its address only" uses the same pipeline-internal "round" language. Same fix applies: state the current state of the system without referencing the iteration in which it was set.
    - fix: Replace "but this round leaves the form reachable by its address only, with no visible entry point on the owner's record." with "but the form is reachable by its address only, with no visible entry point on the owner's record."
- ✎ **review test** · **changes_requested** · (2 findings) · ***◷ 5m***
  - [autofix] `VisitControllerTests.java:56` New constant TEST_VISIT_ID = 1 added in this slice does not follow the three-tier naming convention. The integer value is irrelevant scaffolding (only consistency between setup and retrieval matters, not the specific value). Brief (§ Three-Tier Data Naming) requires SOME_/ANY_ prefix for values that have no bearing on test outcome.
    - fix: Rename TEST_VISIT_ID to SOME_VISIT_ID and update the four usages on lines 78, 131, 143, 151, 159, 170, 181.
  - [autofix] `VisitControllerTests.java:77-81` The existingVisit object is constructed directly in @BeforeEach without a factory method. This is new code added in this slice. Brief (§ Test Data Construction) requires: a slice adding a test writes construction behind a factory method from the start. No factory for Visit existed before; one should be introduced (e.g. createExistingVisit(int id, LocalDate date, String description)).
- ✎ **review code-quality** · **changes_requested** · (2 findings) · ***◷ 5m***
  - **[blocked]** `VisitController.java:80-82` When visitId is non-null, loadPetWithVisit returns pet.getVisit(visitId) without a null check. Pet.getVisit(Integer) documents it returns null when no matching visit exists for the pet. A stale or invalid visitId in the URL (e.g. /owners/1/pets/1/visits/999/edit) silently produces null as the visit model attribute, causing a NullPointerException in processUpdateVisitForm at visit.getDate() before any application logic runs. The pet lookup directly above (lines 71-74) correctly throws IllegalArgumentException when the pet is null — that same guard is missing for the visit. Fix: extract the return value and throw when null: Visit visit = pet.getVisit(visitId); if (visit == null) { throw new IllegalArgumentException("Visit with id " + visitId + " not found for pet with id " + petId + "."); } return visit;
  - [autofix] `VisitController.java:31-32` org.springframework.web.servlet.mvc.support.RedirectAttributes (a Spring import) is grouped with jakarta.validation.Valid without a blank line separator. PetController — the template this slice explicitly mirrors — separates each import group with its own blank line (PetController.java lines 35-39). The formatter accepts both arrangements, but the inconsistency makes RedirectAttributes read as part of the jakarta group rather than the Spring group.
    - fix: Add a blank line between line 31 (import jakarta.validation.Valid;) and line 32 (import org.springframework.web.servlet.mvc.support.RedirectAttributes;) to match PetController import grouping.
- ↻ **implement** (implementer) ← test, code-quality · (4 findings) · ***◷ 15m***
  - ▲ **build ✓ clean** · build · test · format · check
- ↻ **fix prd-expert** ← doc · (3 findings)
- ✔ **review test** · **approved** · ***◷ 1m***
- ✔ **review doc** · **approved** · ***◷ 1m***
- ✔ **review code-quality** · **approved** · ***◷ 1m***
- ◆ **grade CLEAR** · add visit-correction edit flow mirroring booking
  - blast_radius — **clear** — Contained in the owner package: Pet.java gains a getVisit lookup, VisitController.java adds the edit GET/POST pair and an optional visitId to loadPetWithVisit, plus matching tests and PRD/ADR docs. 55 prod lines, 2 modules, no sensitive paths.
  - semantic_surprise — **clear** — The correction path faithfully mirrors booking: same future-date rule (!isAfter(now)), reuses loadPetWithVisit which returns the persisted visit so binding mutates it in place and owners.save cascades an UPDATE not an INSERT. getVisit guards new/unsaved visits and null-checks the miss. No hidden behavior change.
  - test_adequacy — **clear** — Six new tests assert real outcomes at the boundaries: prefill of current date/description, not-found rejection, in-place update proving the visit count stays 1 with new values, redirect target, blank-description refusal, and non-future-date refusal with the exact error code.
  - reviewer_hedging — **clear** — Round-1 blocked finding (missing null check on getVisit) and the autofixes were resolved; round-2 shows all four reviewers approved with empty findings. No escalate or bar_clause hedges.
  - scope_deviation — **clear** — design_revisions=0, consultations=0, build_retries=0. The diff matches REQ-VIS-003 exactly; docs narrow NG-5 with a supporting ADR, and the URL-only reachability (no visible link) is a deliberately documented, deferred boundary, not creep.
  - why — A tightly-scoped edit flow that mirrors the existing booking controller with the same validation and in-place-update semantics, backed by real boundary tests and clean unanimous re-approval. Confirm and merge; a fast read of VisitController's edit POST and getVisit is enough.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- Ownership chain is enforced end-to-end in loadPetWithVisit: owner is resolved by ownerId, pet must belong to that owner (owner.getPet(petId) throws when absent), and the visit must belong to that pet (pet.getVisit(visitId) searches only that pets visit set and returns null otherwise). A visitId from another pet/owner cannot be updated, so the edit path introduces no IDOR beyond the sample apps existing no-auth design.
- InitBinder disallows id and *.id, so neither the visits identifier nor any nested id can be rebound. Combined with the absence of a visit->pet association field on the Visit side (the pet_id join column is owned by Pet.visits), a caller cannot reassign a visit to a different pet or owner via mass assignment.
- In-place update is data-integrity sound: processUpdateVisitForm binds the persisted Visit instance loaded via visitId (same object graph as owner->pet->visits), so owners.save(owner) cascades an UPDATE rather than inserting a duplicate visit. No new visit is added.
- No new injection surface: description remains user text rendered through Thymeleaf auto-escaping (pre-existing), and no SQL/command/deserialization sink is introduced.
- The Owner mass-assignment surface (binding @ModelAttribute Owner then saving) is the pre-existing processNewVisitForm pattern, not newly introduced by this change; *.id rebinding is blocked.

**doc-reviewer**

- NG-5 narrowing is recorded exactly as the 2026-08-08 ADR prescribed: the row text is narrowed to cancellation only, the preamble names the date and links the narrowing ADR, and the rationale column states both the confirmation date and the narrowing date
- New ADR follows the non-goal-ADR conventions from README.md: non-goal- infix in filename, **Non-goal:** NG-5 in Implementation, no References section (matching the 2026-08-08 precedent), Status Accepted
- ADR index row matches: date 2026-08-23, title identical to the ADR H1, status Accepted, filename correct, table format consistent with all existing rows
- REQ-VIS-003 HTML anchor is present at the Visits section anchor line alongside req-vis-001 and req-vis-002
- Acceptance criteria for REQ-VIS-003 are well-formed Given/When/Then statements covering prefill, happy-path update, blank-description refusal, and non-future-date refusal — matching the prd-entry record exactly
- Scope boundary (no owner-detail link) is recorded as edge case 4 and the open question is present — both consistent with the prd-entry notes field
- NG-5 rationale in the Non-Goals table correctly references both the 2026-08-08 confirmation and the 2026-08-23 narrowing with links to both ADRs
- Cross-document links resolve: prd.md#non-goals, prd.md#req-vis-003, and adr/2026-08-23-non-goal-visit-correction-narrowing.md all match their targets
- ADR context correctly quotes the 2026-08-08 formulation of NG-5; Options Considered has three options with the chosen one marked; Decision, Consequences, and Implementation sections are present and accurate
- No implementation code, framework constructs, or internal code references appear in the PRD requirement prose

**test-reviewer**

- All five acceptance criteria scenarios are exercised: GET prefill, POST in-place-update with size invariant, POST redirect to owner detail, POST blank-description refusal, POST non-future-date refusal
- In-place-update invariant is asserted directly: pet.getVisits().hasSize(1) catches phantom inserts; corrected.getDate() / corrected.getDescription() catch binding onto a new (unconnected) Visit instance — both checks are necessary and present
- All four new test methods follow the BDD naming school (the{Subject}Should{Outcome}) as required by the brief and the prd-entry test_names list
- OwnerRepository stubbed at the system-boundary layer (tolerated per brief § Mocking Policy); no mock of internal domain logic
- AssertJ fluent assertions used for all domain-state checks in theVisitCorrectionShouldUpdateInPlaceWithoutAddingAVisit
- EXISTING_VISIT_DATE and EXISTING_VISIT_DESCRIPTION constants follow tier-1 role-naming convention correctly
- POST failure tests verify the specific field name and error code, satisfying the prd acceptance criteria that the form names the field

**code-quality-reviewer**

- loadPetWithVisit correctly branches on visitId: null path preserves the existing booking flow (new Visit + addVisit); non-null path fetches the persisted instance, satisfying the design-block risk mitigations for phantom-visit creation and in-place-update semantics.
- processUpdateVisitForm mutates the persisted Visit in place via data binding and saves through owners.save(owner), ensuring cascade issues UPDATE not INSERT — correct mirror of the updatePetDetails pattern.
- Pet.getVisit(Integer id) mirrors Owner.getPet(Integer id) in structure (isNew guard before id comparison, Objects.equals for null-safe equality, null return for not-found) and carries the same Javadoc style — consistent-with-codebase.
- Validation logic in processUpdateVisitForm (blank description via @NotBlank, non-future date via rejectValue) is byte-for-byte identical to processNewVisitForm — no duplication of rules, no inconsistency.
- initUpdateVisitForm / processUpdateVisitForm naming follows the initNewVisitForm / processNewVisitForm convention exactly.
- Format check passed (checkFormatMain BUILD SUCCESSFUL). IDE not consulted — oracle tools not in dispatch toolset; consistent-with-codebase claim for Pet.getVisit backed by direct Read of Owner.getPet(Integer id) at Owner.java:117-127 confirming the null-return aggregate-lookup pattern.

**test-reviewer**

- Finding 1 resolved: constant renamed from TEST_VISIT_ID to SOME_VISIT_ID (line 57) and all six usages updated to SOME_VISIT_ID — lines 78, 136, 160, 167, 175, 187, 199.
- Finding 2 resolved: createExistingVisit(int id, LocalDate date, String description) factory method introduced at lines 83-89; @BeforeEach at line 78 uses it instead of inline construction.
- New guard test theVisitCorrectionShouldBeRejectedWhenTheVisitDoesNotExistForThePet (lines 144-152) is sound: follows the BDD the{Subject}Should{Outcome}When... naming school; no new mock introduced — uses the pre-existing @MockitoBean OwnerRepository boundary stub and the real MockMvc path; asserts the IllegalArgumentException root cause with a message pinning both the visitId and petId, so a future regression (null passed through, wrong exception type, or missing message content) produces a legible failure rather than an NPE trace; nonExistentVisitId = 999 is a named local variable, not a mystery literal.
- All five acceptance-criteria scenarios remain covered and the prior approved_aspects (in-place-update size invariant, BDD naming on all new methods, AssertJ fluent assertions, field-error assertions on validation failures) are unchanged.

**doc-reviewer**

- Design Rationale link to the 2026-08-23 narrowing ADR is present after the Visits edge cases block (line 123): the H1 title and link target match the ADR filename exactly
- Edge case 4 no longer contains pipeline-internal phrasing: the phrase is now 'The correction form is reachable by its URL only; the owner's record shows no link to it.' with no reference to rounds or implementation iterations
- Open Questions visit-correction entry no longer contains 'this round': the phrase is now 'but the form is reachable by its address only, with no visible entry point on the owner's record.'
- No other occurrence of 'in this round' or 'this round' remains anywhere in docs/prd.md
- All three prior autofix findings from the changes_requested record are fully resolved

**code-quality-reviewer**

- CRITICAL resolved: loadPetWithVisit now extracts pet.getVisit(visitId) into a local variable and throws IllegalArgumentException with a descriptive context message when null — symmetric with the pet guard at lines 71-75 and verified via Read of VisitController.java lines 81-88.
- Test covering the guard added: theVisitCorrectionShouldBeRejectedWhenTheVisitDoesNotExistForThePet at VisitControllerTests.java:143-152 asserts IllegalArgumentException with the expected message for a nonExistentVisitId of 999 — proves the guard fires before any handler logic runs.
- AUTOFIX resolved: a blank line now separates import jakarta.validation.Valid (line 31) from import org.springframework.web.servlet.mvc.support.RedirectAttributes (line 33), matching the PetController import-group convention. Format confirmed clean by the build-pass gate_checks_run record at handoff.jsonl line 17.
- No new quality concerns introduced by the fix round: the IllegalArgumentException message includes both visitId and petId for operator context, exception type is consistent with the existing owner and pet guards, and no new imports or structural changes were added.

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $2.86 | 8m 42s | 94% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $1.65 | 4m 12s | 90% |
| `(parent)` | 1 | opus-4-8 | $1.10 | 23m 27s | 86% |
| `spring-boot-claude:system-design-expert` | 1 | opus-4-8 | $1.06 | 3m 1s | 83% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $0.66 | 3m 56s | 89% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $0.57 | 3m 43s | 86% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $0.57 | 1m 44s | 89% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $0.54 | 3m 19s | 86% |
| `spring-boot-claude:security-reviewer` | 1 | opus-4-8 | $0.49 | 1m 29s | 82% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.09 | 15s | 50% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.72 | 5m 45s | 95% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.14 | 2m 57s | 93% |
| `(parent)` | opus-4-8 | $1.10 | 23m 27s | 86% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.06 | 3m 1s | 83% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.96 | 2m 37s | 91% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.69 | 1m 34s | 89% |
| `spring-boot-claude:change-grader` | opus-4-8 | $0.57 | 1m 44s | 89% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.49 | 1m 29s | 82% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.39 | 2m 51s | 84% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.38 | 2m 55s | 87% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.33 | 2m 33s | 84% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.27 | 1m 5s | 93% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.22 | 46s | 88% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.20 | 48s | 86% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.09 | 15s | 50% |

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
- model requested `claude-opus-4-8`; models used: opus-4-8 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `e78e3e32a55220e2` · `2.1.238 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
