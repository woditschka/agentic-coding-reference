package org.springframework.samples.petclinic;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;

import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Held-out acceptance oracle for the specialty-directory eval task, exercised
 * against the seeded H2 data. The eval runner copies it into the project after the
 * agent run; the agent never sees it.
 *
 * Seeded rows this oracle relies on: the specialties radiology, surgery, and
 * dentistry; Helen Leary holds radiology, Rafael Ortega holds surgery, and Linda
 * Douglas holds surgery and dentistry.
 */
@SpringBootTest
@AutoConfigureMockMvc
class SpecialtyDirectoryOracleTest {

	private static final String A_RADIOLOGIST = "Helen Leary";

	private static final String A_SURGEON = "Rafael Ortega";

	private static final String A_DENTIST = "Linda Douglas";

	@Autowired
	private MockMvc mockMvc;

	// Control: green on the unmodified base.
	@Test
	void theVetDirectoryShouldRenderTheSeededVets() throws Exception {
		mockMvc.perform(get("/vets.html"))
			.andExpect(status().isOk())
			.andExpect(content().string(containsString("radiology")));
	}

	@Test
	void theSpecialtyDirectoryShouldRender() throws Exception {
		mockMvc.perform(get("/specialties.html")).andExpect(status().isOk());
	}

	@Test
	void theSpecialtyDirectoryShouldListEverySeededSpecialty() throws Exception {
		mockMvc.perform(get("/specialties.html"))
			.andExpect(status().isOk())
			.andExpect(content().string(containsString("radiology")))
			.andExpect(content().string(containsString("surgery")))
			.andExpect(content().string(containsString("dentistry")));
	}

	@Test
	void theSpecialtyDirectoryShouldNameTheVetsHoldingEachSpecialty() throws Exception {
		mockMvc.perform(get("/specialties.html"))
			.andExpect(status().isOk())
			.andExpect(content().string(containsString(A_RADIOLOGIST)))
			.andExpect(content().string(containsString(A_SURGEON)))
			.andExpect(content().string(containsString(A_DENTIST)));
	}

}
