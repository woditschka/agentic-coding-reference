# visit-edit r3 — v0.1.18

Edit a booked visit (feature) · started 2026-08-27T23:52:45+00:00 · exec `claude-dev` · status **complete**

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
| 3 (±0) | 4 (±0) | 3 (±1) | 5 (±0) |

Median (spread) over 3 sample(s) · rubric `rubric-v1.md` · `claude-opus-5` · $0.57. Advisory context, never part of the quality bar; rationales below.

<details>
<summary>Per-sample rationales (judge-authored, untrusted text)</summary>

**Sample 1** — design-fit 3 · test-quality 4 · maintainability 4 · doc-fit 5

> The Pet.getVisit navigation-by-identity helper fits the aggregate pattern, but processEditVisitForm copy-pastes the non-future-date rule ( result.rejectValue("date", "typeMismatch.visitDate") ) into a second controller method rather than extracting it — the catalog's 'a new rule added to a controller is a fresh violation' bar. loadPetWithVisit now multiplexes two flows on a nullable visitId, and binding mutates the loaded entity before validation, so the PRD's 'the visit is left unchanged' on rejection holds only because no save occurs. Tests are BDD-named, factory-backed, and assert in-place update via hasSize(1); but  LocalDate.now().plusDays(3)  is an unnamed mystery value repeated three times, and the new visit-not-found throw is untested. Documentation (ADR, NG-5 narrowing, REQ-VISITEDIT-001, contracts, open question) is complete.

**Sample 2** — design-fit 3 · test-quality 4 · maintainability 3 · doc-fit 5

> Placement is sensible — the pet-scoped  Pet.getVisit  lookup mirrors the aggregate-by-identity navigation the design records, and reusing the  @ModelAttribute  loader keeps one seam. But  processEditVisitForm  copy-pastes the non-future-date rule ( result.rejectValue("date", "typeMismatch.visitDate") ) into the controller: the architecture brief states plainly that a new rule in a controller is a fresh violation, and the rule now lives in two places that must change together. Tests are behavior-named and phase-structured with factories, but  LocalDate.now().plusDays(3)  is an unnamed literal repeated across act and assert, and the in-place check picks apart  getVisits().iterator().next()  instead of a collection assertion. Documentation is complete: narrowing ADR, PRD NG-5 row, REQ-VISITEDIT-001 done-when clauses, contracts table, and the deferred-link open question.

**Sample 3** — design-fit 3 · test-quality 4 · maintainability 3 · doc-fit 5

> The @ModelAttribute seam is reused well and Pet.getVisit mirrors existing graph navigation, but processEditVisitForm copy-pastes the non-future-date rule ( result.rejectValue("date", "typeMismatch.visitDate") ) into the controller — a fresh Web-controller violation the catalog's in-force Form validator row covers, with no ADR recording the departure, and now two places to change the rule. Tests are behavior-named (theVisitCorrectionShouldRejectABlankDescription), phase-separated, and behind factories, but  LocalDate.now().plusDays(3)  is an unnamed literal repeated across three tests while ORIGINAL_VISIT_DATE is named, assertions pick apart id/description/date instead of comparing whole objects, and the new pet-scoped not-found throw is untested. Documentation is complete: ADR, index, NG-5 narrowing, REQ-VISITEDIT-001 done-when rows, open question, and contracts table.

</details>

## Figures

Delivery — the change grader's share below excluded from spend and wall:

| agent spend | wall | turns | cache hit | diff |
|---|---|---|---|---|
| $9.11 | 26m | 23 | 89% | 7 file(s) +224/−19 |

The change grader — optional support for the human merge decision, transcript-accounted like the Agents table:

| spend | wall | cache hit |
|---|---|---|
| $0.44 | 1m 20s | 79% |

## Change

<details>
<summary>Diff (rendered from <code>change.patch</code>)</summary>

```diff
diff --git a/docs/adr/2026-08-27-non-goal-visit-correction-narrowing.md b/docs/adr/2026-08-27-non-goal-visit-correction-narrowing.md
new file mode 100644
index 0000000..35736cc
--- /dev/null
+++ b/docs/adr/2026-08-27-non-goal-visit-correction-narrowing.md
@@ -0,0 +1,34 @@
+# Correcting a Booked Visit's Date and Description Is Now In Scope; Cancelling Stays Out
+
+**Status:** Accepted
+
+## Context
+
+The [2026-08-08 non-goal ADR](2026-08-08-non-goal-deletion-and-visit-amendment.md) confirmed NG-5 — changing or cancelling a visit once booked — as a deliberate product decision, and set the convention that narrowing the row later is a recorded owner decision with its own non-goal ADR. The owner has now made that decision (2026-08-27).
+
+## Options Considered
+
+1. **Leave NG-5 whole.** Rejected: the owner wants forward correction of a mistaken visit date or description, the same forward-only correction the sample already demonstrates for owner and pet details.
+2. **Open the whole row** — correction and cancellation both. Rejected: cancellation introduces a visit lifecycle state (a cancelled-but-retained record, or a deletion) the sample carries nowhere else, which is the cost NG-4 and the prior NG-5 decision named.
+3. **Narrow the row: correction in, cancellation out** (chosen).
+
+## Decision
+
+A booked visit's date and description may now be corrected in place. Cancelling a booked visit remains out of scope. The correction updates the existing visit record; it does not add a second visit to the pet, and it removes nothing. This extends the sample's forward-only correction pattern from owner and pet details to a booked visit.
+
+## Consequences
+
+- NG-5 is narrowed rather than withdrawn: correction is in scope (REQ-VISITEDIT-001), cancellation is still declined.
+- The sample continues to demonstrate forward-only correction and to delete nothing, consistent with NG-4.
+- No visit lifecycle state is introduced. A corrected visit is the same record with different values.
+
+## Implementation
+
+**Non-goal:** NG-5
+
+## References
+
+- [2026-08-08 non-goal ADR](2026-08-08-non-goal-deletion-and-visit-amendment.md) — the deletion-and-visit-amendment decision this ADR narrows.
+- [PRD Non-Goals](../prd.md#non-goals) — the narrowed NG-5 row.
+- [PRD Visits](../prd.md#req-visitedit-001) — REQ-VISITEDIT-001, the correction capability the narrowing admits.
+- [system-design.md Contracts](../system-design.md#contracts) — the VisitController correction contract realizing the decision.
diff --git a/docs/adr/README.md b/docs/adr/README.md
index 04c6442..32fe508 100644
--- a/docs/adr/README.md
+++ b/docs/adr/README.md
@@ -70,3 +70,4 @@ A non-goal ADR records a *product* decision not to build something — distinct
 | 2026-07-31 | [Database-Enforced Pet Name Uniqueness Within an Owner](2026-07-31-database-enforced-pet-name-uniqueness.md) | Accepted |
 | 2026-07-31 | [Dual Gradle and Maven Build Definitions](2026-07-31-dual-gradle-and-maven-builds.md) | Accepted |
 | 2026-08-08 | [Deleting Records and Amending Booked Visits Are Deliberately Out of Scope](2026-08-08-non-goal-deletion-and-visit-amendment.md) | Accepted |
+| 2026-08-27 | [Correcting a Booked Visit's Date and Description Is Now In Scope; Cancelling Stays Out](2026-08-27-non-goal-visit-correction-narrowing.md) | Accepted |
diff --git a/docs/prd.md b/docs/prd.md
index 06398de..f0f4297 100644
--- a/docs/prd.md
+++ b/docs/prd.md
@@ -32,7 +32,7 @@ What the framing does not settle is whether each individual behavior was intende
 
 <!-- Declined scope with the reason it was declined; never silently dropped. A non-goal ADR records the path to each decision. -->
 
-> **One reason covers this table, and it is narrower than it looks.** The demonstration framing confirmed 2026-07-31 (G-1) makes scope a function of what a reader must see. A capability that would add breadth without teaching anything new about the stack is out. That reason genuinely explains each row, but it was supplied *after* the rows were derived from absence. It is therefore a framing applied to observed gaps, not a decision recorded at the time. Two rows have since been decided: NG-4 and NG-5 are confirmed deliberate (2026-08-08) — [the non-goal ADR](adr/2026-08-08-non-goal-deletion-and-visit-amendment.md) records the decision. For every other row, whether it was deliberately declined, deferred, or never considered is still unknown, and remains part of the open consultation.
+> **One reason covers this table, and it is narrower than it looks.** The demonstration framing confirmed 2026-07-31 (G-1) makes scope a function of what a reader must see. A capability that would add breadth without teaching anything new about the stack is out. That reason genuinely explains each row, but it was supplied *after* the rows were derived from absence. It is therefore a framing applied to observed gaps, not a decision recorded at the time. Two rows have since been decided: NG-4 and NG-5 are confirmed deliberate (2026-08-08) — [the non-goal ADR](adr/2026-08-08-non-goal-deletion-and-visit-amendment.md) records the decision. NG-5 was later narrowed (2026-08-27): correcting a booked visit's date and description is now in scope as REQ-VISITEDIT-001, and only cancellation stays out — [the narrowing ADR](adr/2026-08-27-non-goal-visit-correction-narrowing.md) records it. For every other row, whether it was deliberately declined, deferred, or never considered is still unknown, and remains part of the open consultation.
 
 | ID | Non-Goal | Rationale |
 |----|----------|-----------|
@@ -40,7 +40,7 @@ What the framing does not settle is whether each individual behavior was intende
 | NG-2 | Managing veterinarians or their specialties through the application | The veterinarian directory demonstrates reading and presenting a cached collection; adding write flows would repeat what the owner and pet capabilities already teach |
 | NG-3 | Managing the list of pet types through the application | Same reason as NG-2 — pet types demonstrate a constrained reference list, and a maintenance UI adds no new pattern |
 | NG-4 | Deleting an owner, a pet, or a visit | Cascading deletion across an aggregate raises questions a reference sample would have to answer at length without illustrating anything the create and update flows do not. Confirmed deliberate 2026-08-08 — [ADR](adr/2026-08-08-non-goal-deletion-and-visit-amendment.md) |
-| NG-5 | Changing or cancelling a visit once booked | Booking already demonstrates validation against a date boundary; amendment would add lifecycle state the sample deliberately has none of. Confirmed deliberate 2026-08-08 — [ADR](adr/2026-08-08-non-goal-deletion-and-visit-amendment.md) |
+| NG-5 | Cancelling a visit once booked | Cancellation would add lifecycle state — a cancelled-but-retained record or a deletion — the sample deliberately has none of. Confirmed deliberate 2026-08-08, then narrowed 2026-08-27 to admit correcting a booked visit's date and description (REQ-VISITEDIT-001); only cancellation stays out — [ADR](adr/2026-08-27-non-goal-visit-correction-narrowing.md) |
 | NG-6 | Assigning a veterinarian to a visit, or any scheduling and availability | Scheduling is a domain of its own. Including it would make the sample about calendars rather than about the stack |
 | NG-7 | Billing, invoicing, and payment | A second bounded context, with money and its own correctness demands, in a sample sized to be read in one sitting |
 | NG-8 | Clinical records beyond a visit's one-line description | The description field demonstrates the association; richer clinical data would add domain depth without adding a pattern |
@@ -100,19 +100,25 @@ Each pet is recorded against exactly one owner, with a name, a birth date, and a
 
 ### Visits
 
-<a id="req-vis-001"></a><a id="req-vis-002"></a>
+<a id="req-vis-001"></a><a id="req-vis-002"></a><a id="req-visitedit-001"></a>
 
-A visit is booked against a particular pet and carries the date it is for and a short description of what it is for `[REQ-VIS-001]`. When booking, the pet's earlier visits are shown alongside, so whoever is booking can see what has already been done `[REQ-VIS-002]`.
+A visit is booked against a particular pet and carries the date it is for and a short description of what it is for `[REQ-VIS-001]`. When booking, the pet's earlier visits are shown alongside, so whoever is booking can see what has already been done `[REQ-VIS-002]`. A booked visit's date and description can be corrected later. Reopening the visit shows its current date and description, and a valid change updates that same visit in place rather than booking another `[REQ-VISITEDIT-001]`. Correction reuses booking's rules — the description must be present and the date must be later than today — and a rejected change redisplays the visit without altering it. Cancelling a visit stays out of scope (NG-5).
 
 **Done when:**
 - `[REQ-VIS-001]` given a pet, when a description and a date later than today are supplied, then the visit is recorded and the booking is confirmed.
 - `[REQ-VIS-001]` given a blank description, when the visit is submitted, then the booking is refused and the description is named.
 - `[REQ-VIS-001]` given a date of today or earlier, when the visit is submitted, then the booking is refused and the date is named.
 - `[REQ-VIS-002]` given a pet with earlier visits, when a new visit is being booked, then those earlier visits are shown with their dates and descriptions.
+- `[REQ-VISITEDIT-001]` given a booked visit, when it is reopened for correction, then the visit form is shown prefilled with the visit's current date and description.
+- `[REQ-VISITEDIT-001]` given a reopened visit, when a valid description and a date later than today are submitted, then that same visit's date and description are updated in place, no further visit is added to the pet, and the owner's record is shown.
+- `[REQ-VISITEDIT-001]` given a reopened visit, when a blank description or a date of today or earlier is submitted, then the correction is refused, the offending field is named, and the visit is left unchanged.
 
 **Edge cases:**
 1. Booking a visit for a pet that does not belong to the named owner is refused.
 2. The date offered by default is the earliest date that would be accepted.
+3. Correcting a visit is reachable only by its own address; no link to it is placed on the owner's record. Surfacing such a link is a possible follow-up (see Open Questions).
+
+**ADR:** [ADR: Correcting a Booked Visit's Date and Description Is Now In Scope](adr/2026-08-27-non-goal-visit-correction-narrowing.md)
 
 ### Veterinarian directory
 
@@ -176,6 +182,7 @@ The system opens on a landing page, and every page carries navigation to the own
 - ~~**Is `REQ-VET-002` a real requirement?**~~ **Answered 2026-07-31: no.** Withdrawn to the Superseded list as an implementation artifact.
 - ~~**Should the error page show technical failure detail to readers?**~~ **Answered 2026-07-31: no.** Stated in `REQ-SYS-002`; the current behavior is recorded as a defect.
 - ~~**Are two message keys dead vocabulary?**~~ **Answered 2026-07-31: yes.** The keys for a duplicate form submission and for a non-numeric value are produced by no code and are translated into all eleven languages. They are dead vocabulary pending removal.
+- **Should the owner's record link to visit correction?** Correcting a booked visit (REQ-VISITEDIT-001) is reachable only by its own address today; whether to surface a link from the owner's record is a deliberate follow-up, deferred.
 - **Is a visit really unrelated to a veterinarian?** Nothing connects the two, which makes the veterinarian directory a standalone page rather than part of the clinical workflow.
 - **Are the seeded pet types and specialties the real lists,** or placeholders?
 - **Does the project hold goals beyond being a reference sample?** G-2 is unfilled.
diff --git a/docs/system-design.md b/docs/system-design.md
index 9d58a3a..c8ef309 100644
--- a/docs/system-design.md
+++ b/docs/system-design.md
@@ -77,7 +77,7 @@ An `Implements` value of `—` marks a contract serving no single requirement. T
 
 **One requirement has no contract.** `REQ-LANG-002` — no hard-coded user-facing text, and no partly translated language — is a property of the message bundles and templates, not of any type. It is enforced at build time by a test that walks the templates and compares every bundle's keys. The guarantee lives in the test and the resources; nothing in the Contracts table can carry it.
 
-**Invariants the rows cannot carry.** `Owner` is the aggregate entry point for the owner feature: `Pet` and `Visit` are persisted only through cascade from `Owner`, and no repository exists for either. `Vets` is a serialization wrapper that exists to give the vet list a single root element for content negotiation; it is not a persisted entity. `PetTypeFormatter` and `PetValidator` are Spring MVC binding and validation extension points, not domain services — `PetValidator` is instantiated directly per data binder rather than injected.
+**Invariants the rows cannot carry.** `Owner` is the aggregate entry point for the owner feature: `Pet` and `Visit` are persisted only through cascade from `Owner`, and no repository exists for either. Navigation into the graph is by identity through the owning entity — a pet is reached through its owner, and a visit through its pet — which scopes visit correction to a visit that belongs to the pet in the request path. `Vets` is a serialization wrapper that exists to give the vet list a single root element for content negotiation; it is not a persisted entity. `PetTypeFormatter` and `PetValidator` are Spring MVC binding and validation extension points, not domain services — `PetValidator` is instantiated directly per data binder rather than injected.
 
 | Contract | Purpose | Source | Implements |
 |----------|---------|--------|------------|
@@ -86,15 +86,15 @@ An `Implements` value of `—` marks a contract serving no single requirement. T
 | `BaseEntity` | Mapped superclass giving every persisted type a generated identity and a "not yet persisted" test | `src/main/java/org/springframework/samples/petclinic/model/BaseEntity.java` | — |
 | `NamedEntity` | Mapped superclass adding a validated name to `BaseEntity` | `src/main/java/org/springframework/samples/petclinic/model/NamedEntity.java` | — |
 | `Person` | Mapped superclass adding validated first and last names to `BaseEntity` | `src/main/java/org/springframework/samples/petclinic/model/Person.java` | — |
-| `Owner` | Persisted owner; owns its pets by cascade and is the entry point for adding a visit to one of them | `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` | REQ-OWN-001, REQ-OWN-003, REQ-PET-002, REQ-VIS-001 |
-| `Pet` | Persisted pet; owns its visits by cascade and references its type | `src/main/java/org/springframework/samples/petclinic/owner/Pet.java` | REQ-PET-001, REQ-OWN-003, REQ-VIS-002 |
+| `Owner` | Persisted owner; owns its pets by cascade and is the entry point for adding a visit to one of them and for saving a corrected visit | `src/main/java/org/springframework/samples/petclinic/owner/Owner.java` | REQ-OWN-001, REQ-OWN-003, REQ-PET-002, REQ-VIS-001, REQ-VISITEDIT-001 |
+| `Pet` | Persisted pet; owns its visits by cascade, references its type, and is the access point for reaching one of its visits by identity | `src/main/java/org/springframework/samples/petclinic/owner/Pet.java` | REQ-PET-001, REQ-OWN-003, REQ-VIS-002, REQ-VISITEDIT-001 |
 | `PetType` | Persisted lookup value naming a species | `src/main/java/org/springframework/samples/petclinic/owner/PetType.java` | REQ-PET-001 |
-| `Visit` | Persisted appointment record against a pet; defaults its date forward on construction | `src/main/java/org/springframework/samples/petclinic/owner/Visit.java` | REQ-VIS-001 |
-| `OwnerRepository` | Spring Data JPA repository for owners; the sole write path for the owner–pet–visit graph. Supports prefix search by last name with paging | `src/main/java/org/springframework/samples/petclinic/owner/OwnerRepository.java` | REQ-OWN-001, REQ-OWN-002, REQ-OWN-003, REQ-OWN-004, REQ-PET-001, REQ-VIS-001 |
+| `Visit` | Persisted appointment record against a pet; defaults its date forward on construction and is corrected in place rather than replaced | `src/main/java/org/springframework/samples/petclinic/owner/Visit.java` | REQ-VIS-001, REQ-VISITEDIT-001 |
+| `OwnerRepository` | Spring Data JPA repository for owners; the sole write path for the owner–pet–visit graph. Supports prefix search by last name with paging | `src/main/java/org/springframework/samples/petclinic/owner/OwnerRepository.java` | REQ-OWN-001, REQ-OWN-002, REQ-OWN-003, REQ-OWN-004, REQ-PET-001, REQ-VIS-001, REQ-VISITEDIT-001 |
 | `PetTypeRepository` | Spring Data JPA repository for pet types, returning them in name order | `src/main/java/org/springframework/samples/petclinic/owner/PetTypeRepository.java` | REQ-PET-001 |
 | `OwnerController` | Server-rendered owner workflows: create, edit, search with paging, and detail | `src/main/java/org/springframework/samples/petclinic/owner/OwnerController.java` | REQ-OWN-001, REQ-OWN-002, REQ-OWN-003, REQ-OWN-004 |
 | `PetController` | Server-rendered pet workflows nested under an owner: create and edit, including duplicate-name and future-birth-date rejection | `src/main/java/org/springframework/samples/petclinic/owner/PetController.java` | REQ-PET-001, REQ-PET-002, REQ-PET-003, REQ-PET-004 |
-| `VisitController` | Server-rendered visit booking for a pet, rejecting non-future dates | `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` | REQ-VIS-001, REQ-VIS-002 |
+| `VisitController` | Server-rendered visit booking for a pet, and in-place correction of a booked visit's date and description at the visit's own dedicated address, rejecting non-future dates on both | `src/main/java/org/springframework/samples/petclinic/owner/VisitController.java` | REQ-VIS-001, REQ-VIS-002, REQ-VISITEDIT-001 |
 | `PetTypeFormatter` | Spring MVC formatter translating between a pet type and its display name during form binding | `src/main/java/org/springframework/samples/petclinic/owner/PetTypeFormatter.java` | REQ-PET-001 |
 | `PetValidator` | Spring `Validator` enforcing the required-field rules for pet forms that bean validation does not cover | `src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java` | REQ-PET-001 |
 | `Vet` | Persisted veterinarian; exposes specialties sorted by name | `src/main/java/org/springframework/samples/petclinic/vet/Vet.java` | REQ-VET-001 |
diff --git a/src/main/java/org/springframework/samples/petclinic/owner/Pet.java b/src/main/java/org/springframework/samples/petclinic/owner/Pet.java
index 4f8409e..0092c22 100644
--- a/src/main/java/org/springframework/samples/petclinic/owner/Pet.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/Pet.java
@@ -18,6 +18,7 @@ package org.springframework.samples.petclinic.owner;
 import java.time.LocalDate;
 import java.util.Collection;
 import java.util.LinkedHashSet;
+import java.util.Objects;
 import java.util.Set;
 
 import org.springframework.format.annotation.DateTimeFormat;
@@ -82,4 +83,21 @@ public class Pet extends NamedEntity {
 		getVisits().add(visit);
 	}
 
+	/**
+	 * Return the Visit with the given id, or null if none found for this Pet.
+	 * @param id to test
+	 * @return the Visit with the given id, or null if no such Visit exists for this Pet
+	 */
+	public Visit getVisit(Integer id) {
+		for (Visit visit : getVisits()) {
+			if (!visit.isNew()) {
+				Integer compId = visit.getId();
+				if (Objects.equals(compId, id)) {
+					return visit;
+				}
+			}
+		}
+		return null;
+	}
+
 }
diff --git a/src/main/java/org/springframework/samples/petclinic/owner/VisitController.java b/src/main/java/org/springframework/samples/petclinic/owner/VisitController.java
index b8b2700..15cd748 100644
--- a/src/main/java/org/springframework/samples/petclinic/owner/VisitController.java
+++ b/src/main/java/org/springframework/samples/petclinic/owner/VisitController.java
@@ -54,15 +54,19 @@ class VisitController {
 	}
 
 	/**
-	 * Called before each and every @RequestMapping annotated method. 2 goals: - Make sure
-	 * we always have fresh data - Since we do not use the session scope, make sure that
-	 * Pet object always has an id (Even though id is not part of the form fields)
+	 * Called before each and every @RequestMapping annotated method. 3 goals: - Make sure
+	 * we always have fresh data reloaded from the database - Since we do not use the
+	 * session scope, make sure that the Pet object always has an id (even though id is
+	 * not part of the form fields) - Supply the "visit" model attribute: for the
+	 * correction (/edit) path, return the existing Visit resolved pet-scoped by visitId
+	 * without attaching another; for the booking (/new) path, create and attach a fresh
+	 * Visit.
 	 * @param petId
-	 * @return Pet
+	 * @return Visit
 	 */
 	@ModelAttribute("visit")
 	public Visit loadPetWithVisit(@PathVariable("ownerId") int ownerId, @PathVariable("petId") int petId,
-			Map<String, Object> model) {
+			@PathVariable(name = "visitId", required = false) Integer visitId, Map<String, Object> model) {
 		Optional<Owner> optionalOwner = owners.findById(ownerId);
 		Owner owner = optionalOwner.orElseThrow(() -> new IllegalArgumentException(
 				"Owner not found with id: " + ownerId + ". Please ensure the ID is correct "));
@@ -75,6 +79,18 @@ class VisitController {
 		model.put("pet", pet);
 		model.put("owner", owner);
 
+		// Correcting an existing visit: return that visit (resolved pet-scoped so a
+		// correction can only touch a visit owned by the pet in the path) without adding
+		// another. Booking a new visit: create and attach a fresh one.
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
@@ -111,4 +127,30 @@ class VisitController {
 		return "redirect:/owners/{ownerId}";
 	}
 
+	// Spring MVC calls method loadPetWithVisit(...) before initEditVisitForm is
+	// called
+	@GetMapping("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit")
+	public String initEditVisitForm() {
+		return "pets/createOrUpdateVisitForm";
+	}
+
+	// Spring MVC calls method loadPetWithVisit(...) before processEditVisitForm is
+	// called; the bound visit is the existing one resolved by visitId, so binding
+	// mutates that same record in place.
+	@PostMapping("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit")
+	public String processEditVisitForm(@ModelAttribute Owner owner, @Valid Visit visit, BindingResult result,
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
index b608caa..17644fd 100644
--- a/src/test/java/org/springframework/samples/petclinic/owner/VisitControllerTests.java
+++ b/src/test/java/org/springframework/samples/petclinic/owner/VisitControllerTests.java
@@ -16,7 +16,13 @@
 
 package org.springframework.samples.petclinic.owner;
 
+import static org.assertj.core.api.Assertions.assertThat;
+import static org.hamcrest.Matchers.hasProperty;
+import static org.hamcrest.Matchers.is;
+import static org.mockito.ArgumentMatchers.any;
 import static org.mockito.BDDMockito.given;
+import static org.mockito.Mockito.never;
+import static org.mockito.Mockito.verify;
 import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
 import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
 import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.model;
@@ -50,21 +56,51 @@ class VisitControllerTests {
 
 	private static final int TEST_PET_ID = 1;
 
+	private static final int TEST_VISIT_ID = 1;
+
+	private static final LocalDate ORIGINAL_VISIT_DATE = LocalDate.now().plusDays(5);
+
+	private static final String ORIGINAL_VISIT_DESCRIPTION = "Original checkup";
+
+	private static final String CORRECTED_VISIT_DESCRIPTION = "Corrected checkup";
+
 	@Autowired
 	private MockMvc mockMvc;
 
 	@MockitoBean
 	private OwnerRepository owners;
 
+	private Pet pet;
+
 	@BeforeEach
 	void init() {
-		Owner owner = new Owner();
-		Pet pet = new Pet();
-		owner.addPet(pet);
-		pet.setId(TEST_PET_ID);
+		Owner owner = createAnOwner();
+		this.pet = createAPet();
+		// Owner.addPet only attaches a pet while it is still new (no id), so add first,
+		// then assign the id.
+		owner.addPet(this.pet);
+		this.pet.setId(TEST_PET_ID);
+		this.pet.addVisit(createAVisit(TEST_VISIT_ID, ORIGINAL_VISIT_DATE, ORIGINAL_VISIT_DESCRIPTION));
+
 		given(this.owners.findById(TEST_OWNER_ID)).willReturn(Optional.of(owner));
 	}
 
+	private static Owner createAnOwner() {
+		return new Owner();
+	}
+
+	private static Pet createAPet() {
+		return new Pet();
+	}
+
+	private static Visit createAVisit(int id, LocalDate date, String description) {
+		Visit visit = new Visit();
+		visit.setId(id);
+		visit.setDate(date);
+		visit.setDescription(description);
+		return visit;
+	}
+
 	@Test
 	void initNewVisitForm() throws Exception {
 		mockMvc.perform(get("/owners/{ownerId}/pets/{petId}/visits/new", TEST_OWNER_ID, TEST_PET_ID))
@@ -106,4 +142,71 @@ class VisitControllerTests {
 			.andExpect(view().name("pets/createOrUpdateVisitForm"));
 	}
 
+	@Test
+	void theVisitFormShouldBePrefilledWithCurrentDataWhenCorrectingAnExistingVisit() throws Exception {
+		mockMvc
+			.perform(get("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit", TEST_OWNER_ID, TEST_PET_ID,
+					TEST_VISIT_ID))
+			.andExpect(status().isOk())
+			.andExpect(view().name("pets/createOrUpdateVisitForm"))
+			.andExpect(model().attribute("visit", hasProperty("description", is(ORIGINAL_VISIT_DESCRIPTION))))
+			.andExpect(model().attribute("visit", hasProperty("date", is(ORIGINAL_VISIT_DATE))));
+	}
+
+	@Test
+	void theVisitCorrectionShouldUpdateTheVisitInPlaceWhenValid() throws Exception {
+		mockMvc
+			.perform(post("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit", TEST_OWNER_ID, TEST_PET_ID,
+					TEST_VISIT_ID)
+				.param("date", LocalDate.now().plusDays(3).toString())
+				.param("description", CORRECTED_VISIT_DESCRIPTION))
+			.andExpect(status().is3xxRedirection());
+
+		assertThat(this.pet.getVisits()).hasSize(1);
+		Visit updated = this.pet.getVisits().iterator().next();
+		assertThat(updated.getId()).isEqualTo(TEST_VISIT_ID);
+		assertThat(updated.getDescription()).isEqualTo(CORRECTED_VISIT_DESCRIPTION);
+		assertThat(updated.getDate()).isEqualTo(LocalDate.now().plusDays(3));
+	}
+
+	@Test
+	void theVisitCorrectionShouldRedirectToOwnerRecordAfterSuccess() throws Exception {
+		mockMvc
+			.perform(post("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit", TEST_OWNER_ID, TEST_PET_ID,
+					TEST_VISIT_ID)
+				.param("date", LocalDate.now().plusDays(3).toString())
+				.param("description", CORRECTED_VISIT_DESCRIPTION))
+			.andExpect(status().is3xxRedirection())
+			.andExpect(view().name("redirect:/owners/{ownerId}"));
+	}
+
+	@Test
+	void theVisitCorrectionShouldRejectABlankDescription() throws Exception {
+		mockMvc
+			.perform(post("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit", TEST_OWNER_ID, TEST_PET_ID,
+					TEST_VISIT_ID)
+				.param("date", LocalDate.now().plusDays(3).toString())
+				.param("description", ""))
+			.andExpect(model().attributeHasFieldErrors("visit", "description"))
+			.andExpect(status().isOk())
+			.andExpect(view().name("pets/createOrUpdateVisitForm"));
+
+		verify(this.owners, never()).save(any());
+	}
+
+	@Test
+	void theVisitCorrectionShouldRejectADateThatIsNotInTheFuture() throws Exception {
+		mockMvc
+			.perform(post("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit", TEST_OWNER_ID, TEST_PET_ID,
+					TEST_VISIT_ID)
+				.param("date", LocalDate.now().toString())
+				.param("description", CORRECTED_VISIT_DESCRIPTION))
+			.andExpect(model().attributeHasFieldErrors("visit", "date"))
+			.andExpect(model().attributeHasFieldErrorCode("visit", "date", "typeMismatch.visitDate"))
+			.andExpect(status().isOk())
+			.andExpect(view().name("pets/createOrUpdateVisitForm"));
+
+		verify(this.owners, never()).save(any());
+	}
+
 }
```

</details>

## Pipeline

### REQ-VISITEDIT-001 — Correct a booked visit's date and description

2 review rounds · 2 build-passes · grade **CLEAR**

| reviewer | R1 | R2 |
| --- | --- | --- |
| **code-quality** | ✎ (2) | **✔** |
| **test** | ✎ (3) | **✔** |
| **security** | **✔** | · |
| **doc** | ✎ (5) | **✔** |

- ◇ **prd-entry** Correct a booked visit's date and description · (prd-expert) · ***◷ 0s***
- ◈ **design-block** **minor** · (design) · ***◷ 10m***
- ◆ **implement** (implementer) · ***◷ 7m***
  - ▲ **build ✓ clean** · build · test · format · handoff-log · autofix-audit
- ✔ **review security** · **approved** · ***◷ 10m***
- ✎ **review code-quality** · **changes_requested** · (2 findings) · ***◷ 15m***
  - [autofix] `VisitController.java:56-61` The Javadoc on loadPetWithVisit still reads '2 goals' and lists only the original two (fresh data, Pet has an id). The method now has a third responsibility — branching on visitId to either resolve an existing Visit for the edit path or create and attach a new one for the booking path. A cold reader will see the branching at lines 81-92 without any Javadoc cover. Update the comment to enumerate all three goals and summarise the edit-path contract (returns existing visit, never calls addVisit).
    - fix: Replace the '2 goals' sentence block with prose that covers all three responsibilities: (1) reload owner/pet from DB, (2) ensure Pet always carries its id, (3) for /edit return the existing Visit resolved pet-scoped by visitId; for /new create and attach a fresh Visit.
  - [autofix] `VisitControllerTests.java:147,153` The corrected description string 'Corrected checkup' is a magic literal used as both the submitted param value (line 147) and the expected value in the assertion (line 153). Per the three-tier naming convention the test description value should be a named constant alongside ORIGINAL_VISIT_DESCRIPTION so a reader immediately knows the two occurrences must match and why the value differs from the original.
    - fix: Add 'private static final String CORRECTED_VISIT_DESCRIPTION = "Corrected checkup";' next to the other class-level constants and replace both literal occurrences in shouldUpdateExistingVisitInPlaceWhenCorrectionIsValid.
- ✎ **review test** · **changes_requested** · (3 findings) · ***◷ 5m***
  - [autofix] `VisitControllerTests.java:131,142,158,` All five new test methods use the `should{Outcome}` prefix instead of the brief-required `the{Subject}Should{Outcome}` school (testing-principles.md § Test Naming, effective 2026-07-31). Examples: `shouldShowVisitFormPrefilledWhenCorrectingAnExistingVisit` → `theVisitFormShouldBePrefillledWithCurrentDataWhenCorrectingAnExistingVisit`; `shouldUpdateExistingVisitInPlaceWhenCorrectionIsValid` → `theVisitCorrectionShouldUpdateTheVisitInPlaceWhenValid`; `shouldRedirectToOwnerRecordAfterSuccessfulCorrection` → `theVisitCorrectionShouldRedirectToOwnerRecordAfterSuccess`; `shouldRejectCorrectionWithBlankDescription` → `theVisitCorrectionShouldRejectABlankDescription`; `shouldRejectCorrectionWithDateNotInTheFuture` → `theVisitCorrectionShouldRejectADateThatIsNotInTheFuture`. The prd-entry `test_names` list also recorded the `should` form, which produced a prd/brief disagreement followed downstream — both the prd-entry and the implementation need the `the{Subject}Should{Outcome}` form.
    - fix: Rename all five methods to the `the{Subject}Should{Outcome}` pattern. Update the prd-entry `test_names` field to match so the handoff ledger agrees with the brief.
  - [autofix] `VisitControllerTests.java:74-87` The `@BeforeEach` setUp constructs `new Owner()`, `new Pet()`, and `new Visit()` directly. Testing-principles.md § Test Data Construction requires factory methods for all tests written or modified from 2026-07-31 onward, and this `@BeforeEach` was modified (adding the visit fixture) as part of this slice. Three factory calls are needed: `createAnOwner()`, `createAPet()`, and a `createAVisitWithIdDateAndDescription(TEST_VISIT_ID, ORIGINAL_VISIT_DATE, ORIGINAL_VISIT_DESCRIPTION)` (or equivalent anonymous factory with named overrides). The existing pre-2026-07-31 construction in the class is pre-existing debt, but the additions in this slice require factory wrapping from the start.
    - fix: Introduce `createAnOwner()`, `createAPet()`, and `createAVisit(int id, LocalDate date, String description)` static factory methods in the test class. Replace the direct constructor calls added in this slice's `@BeforeEach` with the factories.
  - [autofix] `VisitControllerTests.java:147,153` The string literal `"Corrected checkup"` appears twice in `shouldUpdateExistingVisitInPlaceWhenCorrectionIsValid` — once as a POST param and once as an assertion expected value — without being named as a constant. Testing-principles.md § Three-Tier Data Naming Convention requires Tier-1 meaningful values to be named by role; `"Corrected checkup"` drives the outcome being asserted and qualifies as a meaningful value. `ORIGINAL_VISIT_DESCRIPTION` at line 63 sets the right precedent for this class.
    - fix: Extract `private static final String CORRECTED_VISIT_DESCRIPTION = "Corrected checkup";` at the class level and use it in both `.param("description", CORRECTED_VISIT_DESCRIPTION)` and the assertion.
  - ▹ rec: The verify(never()).save() assertion couples the rejection tests to the persistence method name rather than to the observable outcome (visit unchanged). A future slice could replace this with a real in-memory repository double (no Mockito) and assert the stored state directly — the brief's preferred direction (testing-principles.md § Mocking Policy). Not a blocker in this slice because OwnerRepository is already mocked class-wide and the prd-entry specified this approach.
  - ▹ rec: The date constant LocalDate.now().plusDays(3) used in shouldUpdateExistingVisitInPlaceWhenCorrectionIsValid as both the POST param and the assertion expected value is correct (derived, not a magic number) but could be extracted to a local CORRECTED_VISIT_DATE variable for symmetry with ORIGINAL_VISIT_DATE.
- ✎ **review doc** · **changes_requested** · (5 findings) · ***◷ 5m***
  - [autofix] `prd.md:105` The sentence introducing REQ-VISITEDIT-001 is approximately 33 words, exceeding the 30-word sentence limit in the writing standards.
    - fix: Split at the colon: 'A booked visit's date and description can be corrected later. Reopening the visit shows its current date and description, and a valid change updates that same visit in place rather than booking another [REQ-VISITEDIT-001].'
  - [autofix] `prd.md:119` Edge case 3 uses 'in this slice', which is ephemeral slice-level jargon in a durable PRD requirement. The PRD must not be segmented by slices; current system state is expressed without slice references.
    - fix: Change 'no link to it is placed on the owner's record in this slice' to 'no link to it is placed on the owner's record'. The Open Questions item already records the deferred follow-up.
  - [autofix] `prd.md:185` The Open Questions entry for the owner-record link uses 'not a decision made in this slice', introducing slice terminology into the durable PRD.
    - fix: Replace 'not a decision made in this slice' with 'deferred'.
  - [autofix] `2026-08-27-non-goal-visit-correction-n` The ADR has no '## References' section. The ADR template in docs/adr/README.md includes a References section. The Implementation section currently carries the links, but the template separates them.
    - fix: Add a '## References' section after Implementation listing: the 2026-08-08 ADR this decision narrows, and the relevant PRD and system-design sections.
  - [autofix] `system-design.md:97` The VisitController Purpose entry names the literal URL path segment '/edit'. This is inconsistent with the other controller rows (OwnerController, PetController) which describe capabilities without naming routes, and would silently rot if the path changes. The abstraction-level self-test: a URL rename would silently invalidate the row.
    - fix: Remove the '/edit' path literal and describe the capability behaviorally, e.g. 'Server-rendered visit booking for a pet, and in-place correction of a booked visit's date and description at the visit's own dedicated address, rejecting non-future dates on both'.
- ↻ **implement** (implementer) ← code-quality, test · (5 findings)
- ↻ **fix design** ← doc · (5 findings)
- ↻ **fix prd-expert** ← doc · (5 findings)
- ◈ **design-block** **minor** · (design) · supersedes L4 · ***◷ 5m***
- ▲ **build-pass** 04:20 · build, test, format, handoff-log, autofix-audit
- ✔ **review code-quality** · **approved** · ***◷ 5m***
- ✔ **review test** · **approved** · ***◷ 10m***
- ✔ **review doc** · **approved** · ***◷ 5m***
- ◆ **grade CLEAR** · add in-place correction of a booked visit's date and description
  - blast_radius — **clear** — Two prod files in the single owner module (Pet.getVisit lookup, VisitController edit handlers) plus its test class and docs/ADR; no sensitive paths, and the 27 hunks are mostly documentation and tests.
  - semantic_surprise — **clear** — The edit path mirrors booking: loadPetWithVisit resolves the existing visit pet-scoped by visitId (throwing if not owned by the pet), returns it as the bound model attribute so form binding mutates it in place, id stays disallowed from binding, and the same non-future-date rejection applies; nothing behaves beyond what the diff and description imply.
  - test_adequacy — **clear** — Tests assert real outcomes rather than restating code: GET prefills current date/description, valid POST leaves the pet with one visit of the same id but updated fields, and blank-description and non-future-date cases reject with field errors and verify owners.save is never called.
  - reviewer_hedging — **clear** — All four rosters end at approved with empty findings; the first-round changes_requested from code-quality, test, and doc were resolved in the second round and security approved outright, leaving no lingering caveats or escalations.
  - scope_deviation — **clear** — One design revision, zero build retries and zero consultations; the change stays inside the NG-5 narrowing (correction in, cancellation out), and prd/system-design/ADR were updated to match the exact surface implemented.
  - why — All five facets read clear against the diff: a contained, well-tested edit-visit feature whose correction path faithfully mirrors booking, resolves visits pet-scoped to prevent cross-pet tampering, and updates in place. Confirm and merge; a quick read of VisitController.loadPetWithVisit suffices.

<details>
<summary>What the reviewers approved (from <code>handoff.jsonl</code>)</summary>

**security-reviewer**

- IDOR confined: the edit visit is resolved only through the pet-scoped chain owners.findById(ownerId) -> owner.getPet(petId) -> pet.getVisit(visitId); each miss throws IllegalArgumentException, and no global visit lookup exists, so a visitId belonging to another pet or owner cannot be reached or mutated
- Mass-assignment guard retained: setDisallowedFields("id","*.id") blocks rebinding the visit/nested identity, so binding cannot redirect the persisted record
- In-place update binds onto the pet-scoped existing Visit instance returned by @ModelAttribute("visit"); owners.save cascades on the owner aggregate, no foreign entity touched
- No injection or path-traversal surface: visitId is a typed Integer path variable used only for an in-memory scan; exception messages concatenate numeric ids only; description/date render through the unchanged auto-escaping Thymeleaf template
- Validation-failure path returns the view without owners.save, leaving the persisted visit unchanged

**code-quality-reviewer**

- Pet.getVisit mirrors Owner.getPet correctly — same isNew() guard, same Objects.equals(compId,id) shape, same null return (grep-confirmed at Owner.java:117-121; IDE not consulted this run)
- loadPetWithVisit branching on optional visitId is clean; the inline comment at lines 78-80 explains the pet-scoped IDOR mitigation clearly
- Both POST handlers gate owners.save on validation success and skip it on error — correct AC-3 semantics; no flush on the error path
- processEditVisitForm does not call addVisit — same-record invariant (AC-2) preserved
- Test names match PRD test_names verbatim
- shouldRejectCorrectionWithBlankDescription and shouldRejectCorrectionWithDateNotInTheFuture both call verify(owners, never()).save(any()) — directly tests the no-save-on-rejection requirement
- shouldUpdateExistingVisitInPlaceWhenCorrectionIsValid asserts pet.getVisits().size() == 1 after a successful edit — directly tests AC-2 'adds no further visit to the pet'

**test-reviewer**

- All five REQ-VISITEDIT-001 acceptance criteria have dedicated, passing tests: GET prefill (AC-1), in-place update with no extra visit and same visit ID (AC-2), owner-record redirect (AC-2), blank-description rejection (AC-3), past-date rejection (AC-3)
- shouldUpdateExistingVisitInPlaceWhenCorrectionIsValid correctly asserts hasSize(1) on pet.getVisits(), getId().isEqualTo(TEST_VISIT_ID), and the updated fields — directly verifying the aggregate root carries the corrected state rather than a new record
- ORIGINAL_VISIT_DATE and ORIGINAL_VISIT_DESCRIPTION named constants follow the Tier-1 convention for the prefill assertion
- Rejection tests assert the correct error field, error code (typeMismatch.visitDate), HTTP 200, and correct view name — matching the booking path's validation pattern
- verify(never()).save() on OwnerRepository is within the brief's tolerated boundary: OwnerRepository is a system boundary mock already present in the class, and the prd-entry explicitly specified this assertion shape for both rejection tests
- Tests are all green (BUILD SUCCESSFUL)

**doc-reviewer**

- REQ-VISITEDIT-001 HTML anchor is present and correctly formed at docs/prd.md:103
- All three Done-when bullets carry [REQ-VISITEDIT-001] tags and are expressed in given/when/then language
- No PRD boundary violations: no code blocks, no language-specific constructs, no mechanism tables, no internal type or method references
- NG-5 narrowing is represented consistently across the Non-Goals preamble, the NG-5 table row, and the new ADR
- Cross-document coherence is sound: REQ-VISITEDIT-001 appears in both prd.md and system-design.md; all five Contracts rows updated for Owner, Pet, Visit, OwnerRepository, and VisitController carry the new requirement
- system-design.md invariant paragraph correctly captures the aggregate-navigation security property without enumerating fields or parameters
- ADR README.md index row title exactly matches the ADR file title and status is Accepted
- ADR Context, Options Considered, Decision, Consequences, and Implementation sections are all present
- ADR Implementation section correctly uses Non-goal: NG-5 per the non-goal ADR convention
- ADR links in prd.md resolve: the narrowing ADR file exists and the #non-goals and #req-visitedit-001 anchors in the PRD are present
- Open Questions item for the deferred owner-record link is recorded and correctly framed as a deliberate follow-up

**code-quality-reviewer**

- Finding 1 resolved: loadPetWithVisit Javadoc now reads '3 goals' and correctly enumerates the third goal — edit path returns the existing pet-scoped Visit without attaching another; booking path creates and attaches a fresh Visit; @return corrected to Visit (VisitController.java:56-66)
- Finding 2 resolved: CORRECTED_VISIT_DESCRIPTION private static final String constant extracted at VisitControllerTests.java:65 and both former literal occurrences replaced at lines 162 and 168
- Format: checkJavaFormat task not registered in this Gradle project; build-pass record (line 19) confirms format gate passed during the feature-implementer quality gate run
- Test factory methods createAnOwner(), createAPet(), createAVisit() are present (lines 88-102); @BeforeEach uses them consistently
- Test method names follow the{Subject}Should{Outcome} pattern for all five new methods

**test-reviewer**

- R1 finding 1 resolved: all five new test methods use the brief-mandated the{Subject}Should{Outcome} school — theVisitFormShouldBePrefilledWithCurrentDataWhenCorrectingAnExistingVisit, theVisitCorrectionShouldUpdateTheVisitInPlaceWhenValid, theVisitCorrectionShouldRedirectToOwnerRecordAfterSuccess, theVisitCorrectionShouldRejectABlankDescription, theVisitCorrectionShouldRejectADateThatIsNotInTheFuture
- R1 finding 2 resolved: @BeforeEach no longer constructs raw Owner/Pet/Visit; createAnOwner(), createAPet(), and createAVisit(int, LocalDate, String) static factory methods are present and used throughout the setup block
- R1 finding 3 resolved: CORRECTED_VISIT_DESCRIPTION constant extracted at class level (line 65) and used in all four occurrences — two param values and two assertion expected values across theVisitCorrectionShouldUpdateTheVisitInPlaceWhenValid, theVisitCorrectionShouldRedirectToOwnerRecordAfterSuccess, and theVisitCorrectionShouldRejectADateThatIsNotInTheFuture
- All five REQ-VISITEDIT-001 acceptance criteria tests pass (BUILD SUCCESSFUL, VisitControllerTests, jacocoTestReport generated)
- prd-entry.test_names ledger field: the ledger is append-only and product-requirements-expert-owned; the test file itself now carries the correct names matching the brief — no blocking concern on the test-reviewer side; the ledger record is historical and does not affect the production test suite
- R1 recommendation carried forward (non-blocking): LocalDate.now().plusDays(3) is evaluated twice in theVisitCorrectionShouldUpdateTheVisitInPlaceWhenValid — once as POST param and once as assertion expected value; could be extracted to a local CORRECTED_VISIT_DATE variable for symmetry with ORIGINAL_VISIT_DATE, but timing skew between the two evaluations is negligible in unit scope and the duplication is minor

**doc-reviewer**

- R1 finding 1 resolved: prd.md:105 sentence split into two; both under 30 words, [REQ-VISITEDIT-001] tag retained on the second sentence
- R1 finding 2 resolved: prd.md:119 edge case 3 no longer carries 'in this slice'; now reads 'no link to it is placed on the owner's record' with a durable forward pointer to Open Questions
- R1 finding 3 resolved: prd.md:185 Open Questions entry ends 'a deliberate follow-up, deferred' — slice language gone
- R1 finding 4 resolved: ADR 2026-08-27-non-goal-visit-correction-narrowing.md now has a ## References section with four entries covering the narrowed ADR, PRD Non-Goals, PRD Visits anchor, and system-design.md Contracts
- R1 finding 5 resolved: system-design.md:97 VisitController Purpose row replaced literal '/edit' with 'the visit's own dedicated address'; consistent with OwnerController and PetController row style
- No new coherence or contradiction issues introduced by the fixes

</details>

## Agents

Totals per agent type, spend-heaviest first. Spend is the accounted (transcript-derived) figure. Wall sums compute time across transcripts; parallel agents make it exceed elapsed time. Cache hit re-derives from summed tokens, never averaged percentages.

| agent | runs | models | spend | wall | cache hit |
|---|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | 2 | opus-4-8 | $2.93 | 10m 31s | 95% |
| `spring-boot-claude:system-design-expert` | 2 | opus-4-8 | $1.66 | 4m 26s | 89% |
| `spring-boot-claude:product-requirements-expert` | 2 | opus-4-8 | $1.16 | 2m 59s | 87% |
| `(parent)` | 1 | opus-4-8 | $1.04 | 27m 18s | 93% |
| `spring-boot-claude:doc-reviewer` | 2 | sonnet-4-6 | $0.62 | 4m 51s | 78% |
| `spring-boot-claude:test-reviewer` | 2 | sonnet-4-6 | $0.55 | 3m 57s | 77% |
| `spring-boot-claude:security-reviewer` | 1 | opus-4-8 | $0.53 | 54s | 71% |
| `spring-boot-claude:code-quality-reviewer` | 2 | sonnet-4-6 | $0.52 | 3m 33s | 81% |
| `spring-boot-claude:change-grader` | 1 | opus-4-8 | $0.44 | 1m 20s | 79% |
| `spring-boot-claude:pipeline-coordinator` | 1 | sonnet-4-6 | $0.11 | 20s | 79% |

<details>
<summary>Per-transcript breakdown</summary>

One row per agent transcript, spend-heaviest first. Full token and per-stage figures: `agent-costs.json`.

| agent | models | spend | wall | cache hit |
|---|---|---|---|---|
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.47 | 5m 45s | 94% |
| `spring-boot-claude:feature-implementer` | opus-4-8 | $1.46 | 4m 45s | 95% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $1.25 | 3m 47s | 91% |
| `(parent)` | opus-4-8 | $1.04 | 27m 18s | 93% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.70 | 2m 10s | 90% |
| `spring-boot-claude:security-reviewer` | opus-4-8 | $0.53 | 54s | 71% |
| `spring-boot-claude:product-requirements-expert` | opus-4-8 | $0.46 | 48s | 81% |
| `spring-boot-claude:change-grader` | opus-4-8 | $0.44 | 1m 20s | 79% |
| `spring-boot-claude:system-design-expert` | opus-4-8 | $0.41 | 39s | 82% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.39 | 3m 40s | 75% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.35 | 3m 0s | 71% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.32 | 2m 41s | 83% |
| `spring-boot-claude:doc-reviewer` | sonnet-4-6 | $0.22 | 1m 10s | 82% |
| `spring-boot-claude:code-quality-reviewer` | sonnet-4-6 | $0.20 | 51s | 79% |
| `spring-boot-claude:test-reviewer` | sonnet-4-6 | $0.20 | 56s | 83% |
| `spring-boot-claude:pipeline-coordinator` | sonnet-4-6 | $0.11 | 20s | 79% |

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
- model requested `claude-opus-4-8`; models used: opus-4-8 · sonnet-4-6
- SUT `woditschka/spring-petclinic` at `b67f301cbaa3` (branch `agent-team`)
- task fingerprint `e78e3e32a55220e2` · `2.1.247 (Claude Code)`

Generated by `evals/summarize.py` from this folder's records — regenerate rather than edit.
