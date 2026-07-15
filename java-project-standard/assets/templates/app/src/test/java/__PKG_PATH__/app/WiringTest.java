package __PKG__.app;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import __PKG__.kernel.AppConfig;
import org.junit.jupiter.api.Test;

class WiringTest {
  @Test
  void wiresMockProvidersFromDefaultConfig() {
    Wiring.Components components = Wiring.wire(AppConfig.defaults());
    assertEquals("mock", components.config().llmProvider());
    assertNotNull(components.llm());
    assertNotNull(components.embedder());
  }
}
