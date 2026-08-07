package org.springframework.samples.petclinic;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.view;

/**
 * Held-out acceptance oracle for the owners-page-param eval task, exercised against
 * the seeded H2 data (ten owners, so the listing branch renders). The eval runner
 * copies it into the project after the agent run; the agent never sees it.
 */
@SpringBootTest
@AutoConfigureMockMvc
class OwnersPageParamOracleTest {

	private static final String OWNER_LISTING_VIEW = "owners/ownersList";

	@Autowired
	private MockMvc mockMvc;

	// Control: green on the unmodified base.
	@Test
	void theOwnerListingShouldRenderForARegularPageRequest() throws Exception {
		mockMvc.perform(get("/owners?page=1"))
			.andExpect(status().isOk())
			.andExpect(view().name(OWNER_LISTING_VIEW));
	}

	@Test
	void thePageZeroRequestShouldRenderTheFirstListingPage() throws Exception {
		mockMvc.perform(get("/owners?page=0"))
			.andExpect(status().isOk())
			.andExpect(view().name(OWNER_LISTING_VIEW));
	}

	@Test
	void theNegativePageRequestShouldRenderTheFirstListingPage() throws Exception {
		mockMvc.perform(get("/owners?page=-3"))
			.andExpect(status().isOk())
			.andExpect(view().name(OWNER_LISTING_VIEW));
	}

}
