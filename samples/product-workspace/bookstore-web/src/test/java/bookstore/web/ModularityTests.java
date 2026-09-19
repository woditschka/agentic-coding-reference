package bookstore.web;

import org.junit.jupiter.api.Test;
import org.springframework.modulith.core.ApplicationModules;

class ModularityTests {

  @Test
  void verifyModularity() {
    ApplicationModules.of(WebApplication.class).verify();
  }
}
