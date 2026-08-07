package org.springframework.samples.petclinic;

import java.time.LocalDate;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasProperty;
import static org.hamcrest.Matchers.is;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.model;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.view;

/**
 * Held-out acceptance oracle for the visit-edit eval task, exercised against the
 * seeded H2 data. The eval runner copies it into the project after the agent run;
 * the agent never sees it.
 *
 * Seeded rows this oracle relies on: owner 6 (Jean Coleman) owns pet 7 (Samantha)
 * and pet 8 (Max); visit 3 is Max's "neutered", visit 4 is Samantha's "spayed".
 * Each test targets its own visit, so the tests stay order-independent.
 */
@SpringBootTest
@AutoConfigureMockMvc
class VisitEditOracleTest {

	private static final int JEAN_COLEMAN_ID = 6;

	private static final int SAMANTHA_PET_ID = 7;

	private static final int MAX_PET_ID = 8;

	private static final int NEUTERED_VISIT_ID = 3;

	private static final int SPAYED_VISIT_ID = 4;

	private static final String VISIT_FORM_VIEW = "pets/createOrUpdateVisitForm";

	private static final String A_FUTURE_DATE = LocalDate.now().plusDays(9).toString();

	@Autowired
	private MockMvc mockMvc;

	// Control: green on the unmodified base.
	@Test
	void theNewVisitFormShouldRenderForTheExistingPet() throws Exception {
		mockMvc.perform(get("/owners/{ownerId}/pets/{petId}/visits/new", JEAN_COLEMAN_ID, SAMANTHA_PET_ID))
			.andExpect(status().isOk())
			.andExpect(view().name(VISIT_FORM_VIEW));
	}

	@Test
	void theEditFormShouldPrefillTheExistingVisit() throws Exception {
		mockMvc
			.perform(get("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit", JEAN_COLEMAN_ID, SAMANTHA_PET_ID,
					SPAYED_VISIT_ID))
			.andExpect(status().isOk())
			.andExpect(view().name(VISIT_FORM_VIEW))
			.andExpect(model().attribute("visit", hasProperty("description", is("spayed"))));
	}

	@Test
	void theEditSubmissionShouldUpdateTheVisitInPlace() throws Exception {
		mockMvc
			.perform(post("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit", JEAN_COLEMAN_ID, MAX_PET_ID,
					NEUTERED_VISIT_ID)
				.param("date", A_FUTURE_DATE)
				.param("description", "updated checkup"))
			.andExpect(status().is3xxRedirection());

		mockMvc.perform(get("/owners/{ownerId}", JEAN_COLEMAN_ID))
			.andExpect(status().isOk())
			.andExpect(content().string(containsString("updated checkup")))
			.andExpect(content().string(not(containsString("neutered"))));
	}

	@Test
	void theEditSubmissionWithABlankDescriptionShouldRedisplayTheForm() throws Exception {
		mockMvc
			.perform(post("/owners/{ownerId}/pets/{petId}/visits/{visitId}/edit", JEAN_COLEMAN_ID, SAMANTHA_PET_ID,
					SPAYED_VISIT_ID)
				.param("date", A_FUTURE_DATE)
				.param("description", ""))
			.andExpect(status().isOk())
			.andExpect(view().name(VISIT_FORM_VIEW));

		mockMvc.perform(get("/owners/{ownerId}", JEAN_COLEMAN_ID))
			.andExpect(status().isOk())
			.andExpect(content().string(containsString("spayed")));
	}

}
