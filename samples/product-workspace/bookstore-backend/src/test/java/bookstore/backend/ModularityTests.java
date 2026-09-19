package bookstore.backend;

import org.junit.jupiter.api.Test;
import org.springframework.modulith.core.ApplicationModules;

class ModularityTests {

  @Test
  void verifyModularity() {
    ApplicationModules.of(BackendApplication.class).verify();
  }
}
