package org.springframework.samples.petclinic;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Held-out acceptance oracle for the vets-specialty-filter eval task, exercised
 * against the seeded H2 data. The eval runner copies it into the project after the
 * agent run; the agent never sees it.
 *
 * Seeded rows this oracle relies on: Douglas and Ortega hold "surgery"; Carter
 * holds no specialty; Leary, Stevens, and Jenkins hold none of "surgery".
 */
@SpringBootTest
@AutoConfigureMockMvc
class VetsSpecialtyFilterOracleTest {

	private static final String A_SURGEON = "Ortega";

	private static final String ANOTHER_SURGEON = "Douglas";

	private static final String A_VET_WITHOUT_SURGERY = "Carter";

	private static final String AN_UNKNOWN_SPECIALTY = "astrology";

	@Autowired
	private MockMvc mockMvc;

	// Control: green on the unmodified base.
	@Test
	void theVetListShouldShowTheFirstPageWithoutAFilter() throws Exception {
		mockMvc.perform(get("/vets.html"))
			.andExpect(status().isOk())
			.andExpect(content().string(containsString(A_VET_WITHOUT_SURGERY)))
			.andExpect(content().string(containsString(A_SURGEON)));
	}

	@Test
	void theSpecialtyFilterShouldNarrowTheHtmlVetList() throws Exception {
		mockMvc.perform(get("/vets.html?specialty=surgery"))
			.andExpect(status().isOk())
			.andExpect(content().string(containsString(A_SURGEON)))
			.andExpect(content().string(containsString(ANOTHER_SURGEON)))
			.andExpect(content().string(not(containsString(A_VET_WITHOUT_SURGERY))));
	}

	@Test
	void theSpecialtyFilterShouldMatchCaseInsensitively() throws Exception {
		mockMvc.perform(get("/vets.html?specialty=SURGERY"))
			.andExpect(status().isOk())
			.andExpect(content().string(containsString(A_SURGEON)))
			.andExpect(content().string(not(containsString(A_VET_WITHOUT_SURGERY))));
	}

	@Test
	void theUnknownSpecialtyShouldYieldAnEmptyVetList() throws Exception {
		mockMvc.perform(get("/vets.html?specialty=" + AN_UNKNOWN_SPECIALTY))
			.andExpect(status().isOk())
			.andExpect(content().string(not(containsString("Carter"))))
			.andExpect(content().string(not(containsString("Leary"))))
			.andExpect(content().string(not(containsString("Douglas"))))
			.andExpect(content().string(not(containsString("Ortega"))))
			.andExpect(content().string(not(containsString("Stevens"))))
			.andExpect(content().string(not(containsString("Jenkins"))));
	}

	@Test
	void theSpecialtyFilterShouldNarrowTheJsonVetList() throws Exception {
		mockMvc.perform(get("/vets?specialty=surgery").accept(MediaType.APPLICATION_JSON))
			.andExpect(status().isOk())
			.andExpect(content().string(containsString(A_SURGEON)))
			.andExpect(content().string(not(containsString(A_VET_WITHOUT_SURGERY))));
	}

}
