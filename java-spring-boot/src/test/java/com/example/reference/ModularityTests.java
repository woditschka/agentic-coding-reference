package com.example.reference;

import org.junit.jupiter.api.Test;
import org.springframework.modulith.core.ApplicationModules;

class ModularityTests {

  @Test
  void verifyModularity() {
    ApplicationModules.of(ReferenceApplication.class).verify();
  }
}
