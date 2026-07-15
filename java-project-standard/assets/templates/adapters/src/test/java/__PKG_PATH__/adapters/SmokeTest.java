package __PKG__.adapters;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import __PKG__.domain.Embedder;
import __PKG__.domain.Llm;
import __PKG__.domain.ProviderException;
import __PKG__.domain.TopK;
import __PKG__.kernel.AppConfig;
import __PKG__.kernel.PromptException;
import __PKG__.kernel.Prompts;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** Offline smoke: the whole path runs with no key -- default config + mocks + strict rendering. */
class SmokeTest {
  @Test
  void mockProvidersRunEndToEndWithoutKey() throws ProviderException {
    AppConfig config = AppConfig.load("/nonexistent.json", Map.of());
    Llm llm = ProviderFactory.makeLlm(config.llmProvider());
    Embedder embedder = ProviderFactory.makeEmbedder(config.llmProvider());

    List<double[]> vectors = embedder.embed(List.of("a", "b", "c"));
    assertEquals(3, vectors.size());
    assertTrue(vectors.stream().allMatch(vector -> vector.length > 0));

    assertTrue(llm.complete("ping").startsWith("[mock]"));
  }

  @Test
  void unknownProviderThrowsNoSilentFallback() {
    assertThrows(IllegalArgumentException.class, () -> ProviderFactory.makeLlm("does-not-exist"));
  }

  @Test
  void strictPromptRenderingThrowsOnMissingVariable() {
    assertThrows(
        PromptException.MissingVariable.class, () -> Prompts.render("Hello {{ name }}", Map.of()));
    assertEquals("Hello world", Prompts.render("Hello {{ name }}", Map.of("name", "world")));
  }

  @Test
  void topKRejectsOutOfRangeValues() {
    assertThrows(IllegalArgumentException.class, () -> new TopK(0));
    assertThrows(IllegalArgumentException.class, () -> new TopK(101));
    assertEquals(10, new TopK(10).value());
  }
}
